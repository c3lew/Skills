#!/usr/bin/env python3
"""Which tickets can be opened at the same time, and the list the client sees.

`plan_batch` is the only real logic in `/build-batch`, and getting it wrong
means two tickets that block each other get opened in parallel — exactly what
the command exists to prevent. So it lives here as a pure function: no `gh`,
no git, no filesystem. SKILL.md tells the agent to fetch the issues and parse
the blocking declarations; only plain data comes in here. `format_plan` is
here for the same reason — the printed list is what the client says yes/no to,
so it is not left as prose the agent improvises.

Ships inside the skill dir because install copies only that dir.

Usage:
    python batch.py < plan.json     # print the list the client reads
    python batch.py --self-check    # run built-in assertions
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CAP = 3  # 平行上限,client 拍板寫死

# #58 固化:§3 那段指令是 client 真的貼進終端機的一行。名單印在 `python -c` 裡的
# 時候,這支檔的斷言一條都碰不到它,stdout 也沒地方釘 — 那正是 #58 的形狀。
BASH_BLOCK_RE = re.compile("```bash(.*?)```", re.S)
INLINE_PYTHON_RE = re.compile("(?:python[0-9]?|py) +-c(?![a-zA-Z0-9])")

# #52 過關固化:名單以外,client 螢幕上還會出現 §4/§5 這兩句,而且他是照著這兩句
# 點頭的。它們是 SKILL.md 的散文,一個 assert 都碰不到 — 改壞會無聲漂掉,下一個
# client 看到的東西就不是他驗過的那個。所以在這裡咬住。
CLIENT_LINES = (
    (re.compile(re.escape("沒必要開批次,用 `/build #") + r"\d+"
                + re.escape("`(Codex: `$build #") + r"\d+"
                + re.escape("`)就好")),
     "SKILL.md §4: 只有 1 張能跑時指路單張 /build 的那句不見了(client 在 #52 "
     "demo 點頭的原句)"),
    (re.compile(re.escape("這幾張要一起推嗎?")),
     "SKILL.md §5: 名單印完問點頭的那句「這幾張要一起推嗎?」不見了"),
    (re.compile(re.escape("**說不** → 乾淨結束")),
     "SKILL.md §5: 說不之後乾淨結束、沒有殘留的承諾不見了"),
)

# #54 固化:「一張沒過 QA,好的先收」這條 client 拍板的行為,有三句是散文才講得
# 清楚的處置 — 保留 fail 那張的工作區、整批驗證縮到已收的票、全部沒過就什麼都不
# 合。程式端只認得資料(誰在 fixing 裡),認不得「所以 agent 該做什麼」;這三句
# 被刪掉 batch.py 照樣全綠,而 agent 會回去做它出廠時的事:把 fail 那張一起收掉、
# 拿全批的驗收項去驗、或留下半套狀態。所以在這裡咬住原句。
FAIL_LANE_LINES = (
    (re.compile(re.escape("沒過 QA 那張的 worktree 與 branch 都留著,不 remove")),
     "SKILL.md: 沒過 QA 那張的工作區與 branch 要保留、不回收的那句不見了 — "
     "agent 會照 §7 把它一起 remove 掉,client 回頭沒東西可以接著修"),
    (re.compile(re.escape("整批驗證只涵蓋已合併那幾張的覆蓋驗收項")),
     "SKILL.md: 整批驗證要縮到已合併那幾張的那句不見了 — 含 fail 那張就必定紅,"
     "好的幾張也收不進去"),
    (re.compile(re.escape("全部 lane 都沒過 → 一張都不合")),
     "SKILL.md: 全部 lane 都沒過就不 merge 任何東西的那句不見了 — 剩下的是"
     "一個沒人看得懂的半套狀態"),
)


def plan_batch(tickets, cap=CAP):
    """Split tickets into (ready, queued, blocked).

    tickets: list of dicts with `number`, `state` ("open"/"closed") and
    `blocked_by` (list of issue numbers). Closed tickets are only there as
    blocker state — they never appear in the output.

    `ready` and `queued` are issue numbers. `blocked` carries the reason with
    it — `(number, [blockers still in the way])` — because 「還卡著」 has to
    print 卡在誰後面, and recomputing that in the agent's head would put half
    the judgement back outside the tested seam.

    A ticket is blocked while any blocker is still open. A blocker that isn't
    in the input at all counts as blocking too: we cannot see that it closed,
    and guessing "probably done" is the one mistake this function must not
    make. It shows up in the 還卡著 list where the client can overrule it.
    """
    known = {t["number"] for t in tickets}
    still_open = {t["number"] for t in tickets if t["state"] == "open"}
    ready, blocked = [], []
    for t in sorted((t for t in tickets if t["state"] == "open"),
                    key=lambda t: t["number"]):
        unresolved = [b for b in t.get("blocked_by", [])
                      if b in still_open or b not in known]
        if unresolved:
            blocked.append((t["number"], unresolved))
        else:
            ready.append(t["number"])
    return ready[:cap], ready[cap:], blocked


def format_plan(plan, titles):
    """Render (ready, queued, blocked) as the three sections the client reads."""
    ready, queued, blocked = plan
    lines = []
    for label, rows in (
        ("要開", [(n, ()) for n in ready]),
        ("排隊", [(n, ()) for n in queued]),
        ("還卡著", blocked),
    ):
        lines.append(f"{label}({len(rows)} 張):")
        if not rows:
            lines.append("  (無)")
        for number, blockers in rows:
            row = f"  #{number} {titles.get(number, '')}".rstrip()
            if blockers:
                row += " — 卡在 " + "、".join(f"#{b}" for b in blockers)
            lines.append(row)
    return "\n".join(lines)


LANE_ROOT = ".git/batch-worktrees"  # 藏在 .git 底下 -> 不進 git status,不用 gitignore


def lane_of(number):
    """One ticket's isolated lane: which branch, which working copy.

    Derived, never improvised. Two lanes landing on the same directory is the
    one failure this whole command exists to prevent, and a mistyped path in a
    shell line fails silently — it just makes a second checkout of the wrong
    thing. So the mapping lives here, and the shell lines SKILL.md hands the
    agent are asserted against it in `self_check` — change LANE_ROOT and the
    doc goes red instead of quietly disagreeing.
    """
    return {"number": number,
            "branch": f"batch/{number}",
            "worktree": f"{LANE_ROOT}/{number}"}


def _titled(number, titles):
    return f"#{number} {titles.get(number, '')}".rstrip()


def format_lane_start(numbers, titles):
    """一張一行「開工」— client 從終端機看得到哪張在哪個工作區跑。"""
    def line(n):
        lane = lane_of(n)
        return (f"開工 {_titled(n, titles)} — 工作區 {lane['worktree']}"
                f"(branch {lane['branch']})")

    return "\n".join(line(n) for n in numbers)


def format_lane_done(numbers, titles):
    """一張一行「完成」— lane 內 build + QA 都綠才印。"""
    return "\n".join(f"完成 {_titled(n, titles)} — build + QA 綠" for n in numbers)


def split_lanes(numbers, failed):
    """一批 lane 拆成「已收」與「還在修」,兩邊都保序(#54)。

    誰進合併佇列、誰留在旁邊修,是這片唯一的新判斷,所以它落在這裡而不是 agent
    心算:漏掉一張就是把沒過 QA 的東西合上主線,或把過了的那張白白留置。

    `failed` 裡的票號不在這批就當場停。那個形狀有兩種來源,壞的那種比較常見:
    `"fixing": [48]` 打成 `[4]`,沒過 QA 的 #48 就被算成已收、直接合上主線,
    而終端機還印「3 張已合併」。無聲吃掉正是這支函式存在的理由要防的事。
    """
    stray = [n for n in failed if n not in set(numbers)]
    if stray:
        raise SystemExit(
            "fixing 裡有不在這批的票號:"
            + "、".join(f"#{n}" for n in stray)
            + " — 打錯一個數字就是把沒過 QA 的那張合上主線,不猜")
    failed = set(failed)
    merged = [n for n in numbers if n not in failed]
    fixing = [n for n in numbers if n in failed]
    return merged, fixing


def format_lane_fixing(numbers, titles, label="還在修 "):
    """一張一行「還在修」— 工作區與 branch 都點名,因為它們**沒有**被回收。

    §7 對已收的 lane 是 `git worktree remove`,對這幾張正好相反。把保留下來的
    路徑印在 client 眼前,他回頭要接著修的時候不用去猜東西還在不在。

    `label` 是行首那三個字:終端機是一坨混著已收與還在修的行,要它才分得出來;
    批次總結已經有「### 還在修」的標題,再帶一次就是同一句話講兩遍。
    """
    def line(n):
        lane = lane_of(n)
        return (f"{label}{_titled(n, titles)} — QA 沒過,工作區 {lane['worktree']}"
                f"(branch {lane['branch']})保留,"
                f"下一步:`/build #{n}`(Codex: `$build #{n}`)")

    return [line(n) for n in numbers]


def format_split(merged, fixing, titles):
    """§7 進合併佇列之前先印:哪幾張要合、哪幾張留著不動(#54)。

    「好的先收」唯一的分岔點就在這裡。挑錯的兩種形狀(把沒過的合上主線、把過了的
    漏掉)在 shell 裡都是無聲的,所以這份名單由 `split_lanes` 算、印在 client 眼前,
    不是 agent 自己挑三張裡的哪兩張。
    """
    lines = [f"已收({len(merged)} 張)— 照這個順序 merge:"]
    lines += [f"  {_titled(n, titles)}" for n in merged] or ["  (無)"]
    lines.append(f"還在修({len(fixing)} 張)— worktree 與 branch 都留著,不 remove:")
    lines += [f"  {_titled(n, titles)}" for n in fixing] or ["  (無)"]
    return "\n".join(lines)


def format_batch_done(numbers, spec, fixing=(), titles=None):
    """整批驗證綠之後終端機的最後一行:合了幾張 + 下一棒。

    `fixing` 有東西 = 有 lane 沒過 QA。好的照樣收、照樣指路 demo(client 拍板的
    「好的先收」),沒過那幾張各自帶著保留下來的工作區與下一棒印在後面。全部都
    沒過就一張都不合 — 那時候連 demo 的交棒都不該出現,主線根本沒動。
    """
    titles = titles or {}
    tail = format_lane_fixing(fixing, titles)
    if not numbers:
        return "\n".join([f"{len(fixing)} 張都沒過 QA,沒有東西合併 — "
                          "主線沒動,沒有半套狀態", *tail])
    if not fixing:
        return (f"{len(numbers)} 張已合併,"
                f"下一步:`/client-demo #{spec}`(Codex: `$client-demo #{spec}`)"
                " — 一次 demo 這批")
    head = (f"{len(numbers)} 張已合併可以 demo,"
            + "、".join(f"#{n}" for n in fixing) + " 還在修")
    baton = (f"下一步:`/client-demo #{spec}`(Codex: `$client-demo #{spec}`)"
             f" — 先 demo 已收的 {len(numbers)} 張")
    return "\n".join([head, *tail, baton])


def format_fixing_comment(number, merged, titles=None):
    """沒過 QA 那張票上的留置 comment — 它沒被丟掉,只是還在修(#54)。

    寫回票而不只印在終端機:client 離開電腦回來翻票,要看得出來這張為什麼沒跟著
    另外幾張一起收,以及東西還放在哪、下一棒是什麼。
    """
    titles = titles or {}
    lane = lane_of(number)
    others = (f"另外 {len(merged)} 張已經合回主線" if merged
              else "這批沒有任何一張合回主線")
    return "\n".join([
        f"QA 沒過 — {_titled(number, titles)} 還在修,{others}。",
        "",
        f"工作區 `{lane['worktree']}`(branch `{lane['branch']}`)保留、沒有回收 "
        "— 接著在裡面繼續修。",
        "",
        f"下一步:`/build #{number}`(Codex: `$build #{number}`)",
    ])


def coverage_union(sections):
    """這批所有票的「覆蓋驗收項」聯集,保序去重。

    整批驗證要跑的就是這份聯集(spec 決策 ③)。去重是因為兩張票常覆蓋同一條
    驗收項 — 重複的那條會讓整批驗證與後面的 demo 各演兩次同一件事。
    """
    seen, out = set(), []
    for items in sections:
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
    return out


def coverage_of(numbers, coverage):
    """**已合併**那幾張的覆蓋驗收項聯集 — 沒過 QA 那張的不算(#54)。

    coverage 拿票號當 key,不是一串要跟 `numbers` 排對的 list:整批驗證只該涵蓋
    已收的票,而「哪幾條屬於哪張票」如果靠呼叫端自己把順序排對,fail 那張的驗收
    項會靜靜混進來 — 整批驗證必紅,好的那幾張也就收不進去。

    已收的票沒有 key 就當場停,不是靜靜當空的:§8 要驗的那份清單就是這裡印出來
    的,少一條沒有別人比得出來(§8 拿總結對帳等於拿自己比自己)。少一張 = 那張
    票的覆蓋驗收項整批沒人跑過,而 client 收到的總結看起來一切正常。
    """
    by_ticket = {}
    for k, v in coverage.items():
        try:
            by_ticket[int(k)] = v
        except (TypeError, ValueError):
            raise SystemExit(f"coverage 的 key 要是票號,拿到 {k!r} — "
                             "寫 47 不是 '#47'") from None
    missing = [n for n in numbers if n not in by_ticket]
    if missing:
        raise SystemExit(
            "coverage 少了這幾張已合併的票:"
            + "、".join(f"#{n}" for n in missing)
            + " — 少一張就是它的覆蓋驗收項整批沒人驗到,而總結看起來全綠")
    return coverage_union(by_ticket[n] for n in numbers)


def format_batch_summary(spec, numbers, titles, coverage, fixing=()):
    """spec 票上那則批次總結 comment(整批唯一一個看得完全批的地方)。

    有 lane 沒過 QA 時分「已收 / 還在修」兩段:client 只看這一則就要知道這批收了
    哪幾張、哪幾張還在旁邊修,不用自己去翻三張票對。
    """
    head = (f"## 批次總結({len(numbers)} 張已收 / {len(fixing)} 張還在修)"
            if fixing else f"## 批次總結({len(numbers)} 張)")
    lines = [head, ""]
    if fixing:
        lines += ["### 已收", ""]
    lines += ([f"- {_titled(n, titles)} — 已合併({lane_of(n)['branch']})"
               for n in numbers] or ["- (無)"])
    if fixing:
        lines += ["", "### 還在修", ""]
        lines += [f"- {line}"
                  for line in format_lane_fixing(fixing, titles, label="")]
    if not numbers:
        # 一張都沒收 = §8 根本沒跑(SKILL.md §7.5)。這則 comment 是 client 唯一
        # 看得到整批的地方,在這裡宣稱「整批驗證全綠」就是紙本版的半套狀態。
        lines += ["", "主線沒動,整批驗證沒有跑 — 沒有東西合上去可以驗。"]
        return "\n".join(lines)
    lines += ["",
              "整批驗證:regression + 下列覆蓋驗收項聯集(只含已收的票),全綠。",
              ""]
    lines += [f"- {item}" for item in coverage_of(numbers, coverage)]
    lines += ["",
              f"下一步:`/client-demo #{spec}`(Codex: `$client-demo #{spec}`)"]
    return "\n".join(lines)


def main():
    """stdin JSON -> the three sections the client reads.

    The printing lives here rather than in SKILL.md's command line because
    that is the only place a test can reach it — #58 was a print no test could
    see. The UTF-8 pins that fix it sit in the `__main__` block below, per
    AGENTS.md 「會被跑到的 python 檔要釘 UTF-8」.
    """
    data = json.load(sys.stdin)
    titles = {int(k): v for k, v in data.get("titles", {}).items()}
    mode = data.get("mode", "plan")
    numbers = data.get("numbers", [])
    # `numbers` 一律是整批的票號,`fixing` 是其中沒過 QA 的那幾張。誰收誰留由
    # split_lanes 算,不要求呼叫端先把兩份名單分好 — 分錯是無聲的(#54)。
    merged, fixing = split_lanes(numbers, data.get("fixing", []))
    if mode == "plan":
        print(format_plan(plan_batch(data["tickets"]), titles))
    elif mode == "start":
        print(format_lane_start(numbers, titles))
    elif mode == "done":
        print(format_lane_done(numbers, titles))
    elif mode == "split":
        print(format_split(merged, fixing, titles))
    elif mode == "merged":
        print(format_batch_done(merged, data["spec"], fixing, titles))
    elif mode == "fixing":
        # 貼錯票比不貼更糟 — 一張已經合上主線的票上寫著「QA 沒過、還在修」
        if data["number"] not in fixing:
            raise SystemExit(f"#{data['number']} 不在 fixing 裡,這則 comment "
                             "會貼到一張已收的票上")
        print(format_fixing_comment(data["number"], merged, titles))
    elif mode == "summary":
        print(format_batch_summary(data["spec"], merged, titles,
                                   data.get("coverage", {}), fixing))
    else:
        raise SystemExit(f"unknown mode: {mode!r} (want one of plan, "
                         + ", ".join(MODES) + ")")


def skill_command_issue(text):
    """SKILL.md 的指令要把 JSON 餵進這支檔,不是自己把名單印出來(#58)。

    別的 guard 守「程式有沒有釘 stream」,這條守「文件的指令還有沒有走進程式」。
    §3 換回 inline `python -c`,印就又跑到所有測試與所有 pin 的外面 —
    batch.py 照樣全綠,client 照樣看到壞碼,那就是 #58 出廠時的樣子。
    """
    blocks = BASH_BLOCK_RE.findall(text)
    if not any("batch.py" in b and "<<" in b for b in blocks):
        return ("SKILL.md: no bash block feeds the ticket JSON into batch.py "
                "— the 名單 is printed somewhere no test can reach (#58)")
    if any(INLINE_PYTHON_RE.search(b) for b in blocks):
        return ("SKILL.md: an inline `python -c` prints for the client — "
                "outside this self-check and outside the __main__ pin (#58)")
    return None


def client_lines_issue(text):
    """SKILL.md 還有沒有對 client 講 §4/§5 那兩句(#52 demo 過關的原句)。

    `skill_command_issue` 守「名單有沒有走進程式」,這條守「名單以外那兩句還在不在」。
    """
    for pattern, message in CLIENT_LINES:
        if not pattern.search(text):
            return message
    return None


def fail_lane_issue(text):
    """SKILL.md 還有沒有講「一張沒過 QA 的時候怎麼處置」那三句(#54)。

    `client_lines_issue` 守的是 client 點頭前看到的兩句;這條守的是點頭之後、
    有 lane 沒過時 agent 該做什麼 — 那三件事沒有一件是 batch.py 能自己做的。
    """
    for pattern, message in FAIL_LANE_LINES:
        if not pattern.search(text):
            return message
    return None


MODES = ("start", "done", "split", "merged", "fixing", "summary")


def skill_mode_issue(text):
    """#53 的每一段一樣要把資料餵進這支檔,不是在文件裡 echo 一行中文。

    `skill_command_issue` 守的是「名單」那一段;平行開工之後 client 螢幕上又多了
    開工 / 完成 / 已合併 / 批次總結四種中文輸出,每一種都走同一條 cp950 的路。
    有人把其中一段改回 shell 裡直接印,#58 就原封不動再來一次 — 而且 batch.py
    照樣全綠。所以逐個 mode 咬住。
    """
    blocks = "\n".join(b for b in BASH_BLOCK_RE.findall(text) if "batch.py" in b)
    missing = [m for m in MODES if f'"mode": "{m}"' not in blocks]
    if missing:
        return ("SKILL.md: these batch.py modes are never invoked from a bash "
                "block — that output is printed somewhere no test and no UTF-8 "
                f"pin can reach (#58): {', '.join(missing)}")
    return None


def _ticket(number, blocked_by=(), state="open"):
    return {"number": number, "state": state, "blocked_by": list(blocked_by)}


def self_check():
    t = _ticket
    # 全部互不相卡
    assert plan_batch([t(1), t(2)]) == ([1, 2], [], [])

    # 卡在 open 票後面 -> blocked,而且帶著「卡在誰後面」;blocker 自己照樣可以開
    assert plan_batch([t(1), t(2, [1])]) == ([1], [], [(2, [1])])

    # 卡在已關票後面 -> 放行
    assert plan_batch([t(1, state="closed"), t(2, [1])]) == ([2], [], [])
    # 混合 blocker:一開一關 -> 還是卡著,而且只報還開著的那個
    assert plan_batch([t(1, state="closed"), t(2), t(3, [1, 2])]) == (
        [2], [], [(3, [2])])

    # 鏈狀依賴:只放行鏈頭,不因為 2 卡著就連帶把 3 算成 ready
    assert plan_batch([t(1), t(2, [1]), t(3, [2])]) == ([1], [], [(2, [1]), (3, [2])])

    # 互卡:兩張都不放行
    assert plan_batch([t(1, [2]), t(2, [1])]) == ([], [], [(1, [2]), (2, [1])])

    # 超過 cap -> 其餘排隊,cap 寫死 3
    assert plan_batch([t(1), t(2), t(3), t(4), t(5)]) == ([1, 2, 3], [4, 5], [])
    assert CAP == 3
    # cap 是參數,不是硬編在函式體裡
    assert plan_batch([t(1), t(2)], cap=1) == ([1], [2], [])

    # 只有 1 張 ready(呼叫端據此指路單張 /build)
    assert plan_batch([t(1), t(2, [1]), t(3, [1])]) == ([1], [], [(2, [1]), (3, [1])])

    # 0 張 ready
    assert plan_batch([]) == ([], [], [])
    assert plan_batch([t(1, [2]), t(2, [1]), t(3, [1])])[0] == []

    # blocked_by 指向不存在的票 -> 看不到它關了,保守當成還卡著
    assert plan_batch([t(1, [999])]) == ([], [], [(1, [999])])

    # 驗收項:4 張票,3 張彼此不卡、1 張卡在別人後面
    four = [t(10), t(11), t(12), t(13, [10])]
    ready, queued, blocked = plan_batch(four)
    assert ready == [10, 11, 12] and queued == [] and blocked == [(13, [10])]
    assert 13 not in ready

    # 純函式:同一份輸入跑兩次結果一樣,而且沒被改到
    data = [t(1), t(2, [1])]
    before = [dict(x) for x in data]
    assert plan_batch(data) == plan_batch(data)
    assert data == before

    # 印出來的名單:三段都在,卡住那張寫得出卡在誰後面
    out = format_plan(plan_batch(four + [t(14), t(15)]), {10: "a", 13: "d"})
    assert out.splitlines() == [
        "要開(3 張):",
        "  #10 a",
        "  #11",
        "  #12",
        "排隊(2 張):",
        "  #14",
        "  #15",
        "還卡著(1 張):",
        "  #13 d — 卡在 #10",
    ], out
    # 空的一段也要印出來 — client 看到「排隊(0 張)」才知道沒漏
    assert "排隊(0 張):\n  (無)" in format_plan(plan_batch([t(1)]), {})
    # 多個 blocker 全部列出
    assert "卡在 #1、#2" in format_plan(
        plan_batch([t(1), t(2), t(3, [1, 2])]), {})

    # cap 寫死 3 是 client 拍板的數字,SKILL.md 也對 client 這樣講 —
    # 改了程式沒改文件(或反過來)這裡就咬,不然兩邊會各說各話
    skill = Path(__file__).with_name("SKILL.md")
    text = skill.read_text(encoding="utf-8")
    assert f"最多 {CAP} 張" in text and f"cap 寫死 {CAP}" in text, skill
    for section in ("要開", "排隊", "還卡著"):
        assert section in text, section

    # #58: whether the名單 survives the client's console is invisible to an
    # in-process assert — there stdout is a pipe or a StringIO, never cp950.
    # So shell out with both streams forced to cp950 and compare raw bytes.
    # `ensure_ascii=False` matters: escaped-to-ASCII JSON would sail through
    # an unpinned stdin and hide half the bug. The expected text comes from
    # format_plan, not a literal — this asserts on encoding, and the layout is
    # already pinned by the assertions above.
    tickets = [t(10), t(13, [10])]
    titles = {10: "登入頁 → 🔑", 13: "導向"}
    payload = json.dumps({"tickets": tickets,
                          "titles": {str(k): v for k, v in titles.items()}},
                         ensure_ascii=False)
    child = subprocess.run(
        [sys.executable, __file__],
        input=payload.encode("utf-8"), capture_output=True,
        env=dict(os.environ, PYTHONIOENCODING="cp950"),
    )
    assert child.returncode == 0, child.stderr.decode("utf-8", "replace")
    got = child.stdout.decode("utf-8").splitlines()
    assert got == format_plan(plan_batch(tickets), titles).splitlines(), got

    # #58 固化:文件裡那行指令要一直指著這支檔。先手寫案例,再拿真的 SKILL.md
    # 咬兩種 mutation — 改壞(把 batch.py 那段拿掉)與繞過(自己 inline 印)。
    def fence(body):
        return f"""```bash
{body}
```
"""

    piped = fence('''python batch.py <<'JSON'
{}
JSON''')
    assert skill_command_issue(piped) is None
    assert skill_command_issue(fence("gh issue list"))
    for variant in ("python -c 'print(1)'", "python3 -c 'print(1)'",
                    "py -c 'print(1)'"):
        got = skill_command_issue(piped + fence(variant))
        assert got and "python -c" in got, (variant, got)

    assert skill_command_issue(text) is None, skill_command_issue(text)
    # 改壞:§3 不再把 JSON 餵進來
    # 每一段都要換掉 — 只改第一段的話別段還餵得進來,咬到的會是另一條規則
    mutated = text.replace("python <skill dir>/batch.py <<'JSON'",
                           "python <skill dir>/nope.py <<'JSON'")
    assert mutated != text
    got = skill_command_issue(mutated)
    assert got and "batch.py" in got, got
    # 繞過:§3 留著,另外多一段自己印的指令
    got = skill_command_issue(text + fence("python3 -c 'print(1)'"))
    assert got and "python -c" in got, got

    # #53:SKILL.md 裡那幾行 git 指令是 client 端唯一真的會動到檔案系統的東西,
    # 而路徑打錯在 shell 裡是無聲的(它只是多 checkout 一份到錯的地方)。所以每一行
    # 都對著 lane_of 咬 — 改了 LANE_ROOT 沒改文件,這裡就紅。
    lane47 = lane_of(47)
    for command in (
        f"git worktree add {lane47['worktree']} -b {lane47['branch']}",
        f"git worktree remove {lane47['worktree']}",
        f"git merge --no-ff {lane47['branch']}",
    ):
        assert command in text, command
    assert LANE_ROOT.startswith(".git/"), LANE_ROOT  # 不進 git status,不用 gitignore

    # #53 client-demo 過關固化:§9 的清場判準問的母體也是 LANE_ROOT。它跟上面三行
    # 不同 — 打錯不是 checkout 到錯的地方,是 grep 撈不到任何東西、判成「收乾淨了」,
    # 一路綠到底(#61 修的就是母體選錯的前一版)。所以路徑也對著 lane_of 咬。
    assert f"grep -F /{LANE_ROOT}/" in text, LANE_ROOT
    assert "git branch --list 'batch/*'" in text  # 只驗 worktree 等於只驗一半(#61)

    # #52 過關固化:§4/§5 對 client 講的兩句。真的 SKILL.md 要過,拿掉任何一句要咬。
    assert client_lines_issue(text) is None, client_lines_issue(text)
    for original, label in (
        ("沒必要開批次,用 `/build #47`(Codex: `$build #47`)就好", "§4 指路單張"),
        ("這幾張要一起推嗎?", "§5 問點頭"),
        ("**說不** → 乾淨結束", "§5 說不"),
    ):
        assert original in text, label
        assert client_lines_issue(text.replace(original, "", 1)), label
    # 指路那句要帶兩端的指令,只留 Claude 端不算
    assert client_lines_issue(
        text.replace("(Codex: `$build #47`)", "", 1)), "§4 Codex 端"

    # ---- #53 平行開工 → 依序合併 → 整批驗證 ----------------------------------
    # lane 的 branch 與工作區由這裡算,不由 agent 現編:兩個 lane 拿到同一個路徑
    # 就是這片要防的事(檔案系統層級隔離),而路徑打錯在 shell 裡是無聲的。
    assert lane_of(47) == {"number": 47, "branch": "batch/47",
                           "worktree": ".git/batch-worktrees/47"}
    paths = {lane_of(n)["worktree"] for n in (47, 48, 42)}
    assert len(paths) == 3, paths
    # 工作區藏在 .git 底下 -> 不進 git status,也不用 gitignore
    assert lane_of(47)["worktree"].startswith(".git/")

    # 開工/完成:一張一行,#N 與 title 都在,而且帶得出它在哪個工作區
    start = format_lane_start([47, 48], {47: "名單", 48: "點頭"})
    assert start.splitlines() == [
        "開工 #47 名單 — 工作區 .git/batch-worktrees/47(branch batch/47)",
        "開工 #48 點頭 — 工作區 .git/batch-worktrees/48(branch batch/48)",
    ], start
    assert format_lane_done([47], {47: "名單"}) == "完成 #47 名單 — build + QA 綠"
    # 沒有 title 也要印得出來(title 抓不到不擋開工)
    assert format_lane_start([47], {}) == (
        "開工 #47 — 工作區 .git/batch-worktrees/47(branch batch/47)")

    # 整批合併完的那一行:張數 + 交棒指令兩端都在
    done = format_batch_done([47, 48, 42], 51)
    assert done.startswith("3 張已合併,"), done
    assert "`/client-demo #51`" in done and "`$client-demo #51`" in done, done
    # 「下一步:」開頭 -> validate.py 的 baton 雙寫 guard 掃得到這個形狀
    assert "下一步:`/client-demo #51`" in done, done
    assert format_batch_done([47], 51).startswith("1 張已合併,")

    # 覆蓋驗收項聯集:保序、去重(兩張票覆蓋同一條驗收項時 demo 不該演兩次)
    assert coverage_union([["a", "b"], ["b", "c"], []]) == ["a", "b", "c"]
    assert coverage_union([]) == []

    # 聯集只認已合併的票:coverage 拿票號當 key,沒合上主線那張的驗收項撿不進來
    cov = {47: ["a", "b"], 48: ["b", "c"], 42: ["d"]}
    assert coverage_of([47, 48], cov) == ["a", "b", "c"]
    assert coverage_of([47, 48], {str(k): v for k, v in cov.items()}) == [
        "a", "b", "c"]          # JSON 進來的 key 是字串
    assert "d" not in coverage_of([47, 48], cov)   # #54:fail 那張的不算
    assert coverage_of([], cov) == []
    # 已收的票沒給 coverage 要當場停 — 靜靜當空的就是「那張整批沒人驗到」
    for numbers, coverage in (([47], {}), ([47, 48], {47: ["a"]})):
        try:
            coverage_of(numbers, coverage)
        except SystemExit as e:
            assert "#48" in str(e) or "#47" in str(e), e
        else:
            raise AssertionError((numbers, coverage))
    try:
        coverage_of([47], {"#47": ["a"]})       # key 寫成 '#47'
    except SystemExit as e:
        assert "票號" in str(e), e
    else:
        raise AssertionError("'#47' key")

    # spec 票的批次總結:每張都列到、聯集列到、結尾是交棒行
    summary = format_batch_summary(
        51, [47, 48], {47: "名單", 48: "點頭"}, {47: ["a"], 48: ["a", "b"]})
    assert "#47 名單 — 已合併(batch/47)" in summary, summary
    assert "#48 點頭 — 已合併(batch/48)" in summary, summary
    assert "- a" in summary and "- b" in summary, summary
    assert summary.count("- a") == 1, summary
    assert summary.rstrip().endswith(
        "下一步:`/client-demo #51`(Codex: `$client-demo #51`)"), summary
    # 全綠的總結不長出「已收 / 還在修」兩段 — #53 驗過的形狀原封不動
    assert "### 已收" not in summary and "### 還在修" not in summary, summary

    # ---- #54 一張沒過 QA:好的先收,壞的留在旁邊修 --------------------------
    # 誰收誰留由這裡算,不由 agent 心算;兩邊都照原順序,不在這批的票號忽略
    assert split_lanes([47, 48, 42], [48]) == ([47, 42], [48])
    assert split_lanes([47, 48, 42], []) == ([47, 48, 42], [])
    assert split_lanes([47, 48, 42], [47, 48, 42]) == ([], [47, 48, 42])
    # fixing 裡有不在這批的票號 -> 當場停。無聲吃掉的另一半是「打錯一個數字,
    # 沒過 QA 的那張被算成已收」,而終端機照樣印「3 張已合併」。
    try:
        split_lanes([47, 48], [4])
    except SystemExit as e:
        assert "#4" in str(e), e
    else:
        raise AssertionError("stray fixing number swallowed")

    # 進合併佇列前印的那份名單:誰收、誰留著不動,兩段都印得出來
    picked = format_split([47, 42], [48], {47: "名單", 48: "點頭", 42: "整批"})
    assert picked.splitlines() == [
        "已收(2 張)— 照這個順序 merge:",
        "  #47 名單",
        "  #42 整批",
        "還在修(1 張)— worktree 與 branch 都留著,不 remove:",
        "  #48 點頭",
    ], picked
    # 全綠 / 全紅兩端都印得出空的那一段,client 看得到「沒漏」
    assert "還在修(0 張)— worktree 與 branch 都留著,不 remove:\n  (無)" in (
        format_split([47], [], {}))
    assert "已收(0 張)— 照這個順序 merge:\n  (無)" in format_split([], [48], {})

    # 終端機那一行:2 張收了可以 demo、#48 還在修,而且它的工作區/branch 都點名
    partial = format_batch_done([47, 42], 51, [48], {48: "點頭"})
    assert partial.splitlines()[0] == "2 張已合併可以 demo,#48 還在修", partial
    assert ("還在修 #48 點頭 — QA 沒過,工作區 .git/batch-worktrees/48"
            "(branch batch/48)保留,"
            "下一步:`/build #48`(Codex: `$build #48`)"
            in partial.splitlines()), partial
    # 好的照樣指路 demo — 「好的先收」就是這一句在兌現
    assert "下一步:`/client-demo #51`(Codex: `$client-demo #51`)" in partial
    assert "$client-demo #51" in partial and "$build #48" in partial, partial
    # 兩張沒過就兩張都列
    both = format_batch_done([47], 51, [48, 42], {})
    assert both.splitlines()[0] == "1 張已合併可以 demo,#48、#42 還在修", both
    assert len(both.splitlines()) == 4, both

    # 全部都沒過 -> 一張都不合,而且**不**指路 demo(主線根本沒動)
    none = format_batch_done([], 51, [47, 48, 42], {})
    assert none.splitlines()[0] == (
        "3 張都沒過 QA,沒有東西合併 — 主線沒動,沒有半套狀態"), none
    assert "client-demo" not in none, none
    assert len(none.splitlines()) == 4, none

    # 沒過那張票上的留置 comment:寫明沒過、工作區保留、下一棒是 /build
    note = format_fixing_comment(48, [47, 42], {48: "點頭"})
    assert note.startswith("QA 沒過 — #48 點頭 還在修,另外 2 張已經合回主線。"), note
    assert "`.git/batch-worktrees/48`" in note and "`batch/48`" in note, note
    assert "保留、沒有回收" in note, note
    assert note.rstrip().endswith(
        "下一步:`/build #48`(Codex: `$build #48`)"), note
    # 全部都沒過的時候同一則 comment 不能謊稱有別人合進去了
    assert "這批沒有任何一張合回主線" in format_fixing_comment(48, [], {}), note

    # 批次總結分「已收 / 還在修」兩段,而且聯集不含還在修那張的驗收項
    split = format_batch_summary(
        51, [47, 42], {47: "名單", 42: "整批", 48: "點頭"},
        {47: ["a"], 48: ["只有 #48 覆蓋的那條"], 42: ["b"]}, [48])
    assert split.splitlines()[0] == "## 批次總結(2 張已收 / 1 張還在修)", split
    assert "### 已收" in split and "### 還在修" in split, split
    assert split.index("### 已收") < split.index("### 還在修"), split
    assert "- #48 點頭 — QA 沒過" in split and "batch/48" in split, split
    # 「### 還在修」底下不再重複行首那三個字(標題已經講過一次)
    assert "- 還在修 #48" not in split, split
    assert "還在修 #48 點頭 — QA 沒過" in format_batch_done([47], 51, [48],
                                                          {48: "點頭"})
    assert "- a" in split and "- b" in split, split
    assert "只有 #48 覆蓋的那條" not in split, split      # #54 驗收項
    assert "只含已收的票" in split, split
    # 全部都沒過:總結收得乾淨,不指路 demo,而且**不**宣稱整批驗證跑過 —
    # §7.5 明寫那時候不跑 §8,印「全綠」就是紙本版的半套狀態
    allfail = format_batch_summary(51, [], {48: "點頭"}, {48: ["x"]}, [48])
    assert "## 批次總結(0 張已收 / 1 張還在修)" in allfail, allfail
    assert "- (無)" in allfail and "client-demo" not in allfail, allfail
    assert "全綠" not in allfail and "整批驗證:regression" not in allfail, allfail
    assert allfail.rstrip().endswith("主線沒動,整批驗證沒有跑 — "
                                    "沒有東西合上去可以驗。"), allfail
    assert "- x" not in allfail, allfail      # 沒合上主線的驗收項一條都不列

    # #53 的四種輸出同樣全是中文,同樣印在 cp950 的主控台上 — 名單走過一次的
    # 那條路,它們每一條都要自己再走一次(mode 是新的,__main__ 的 pin 不會自動
    # 蓋到沒被跑過的分支)。emoji 留著:Big5 沒有它,沒 pin 就當場炸。
    for payload, want in (
        ({"mode": "start", "numbers": [47], "titles": {"47": "登入頁 → 🔑"}},
         format_lane_start([47], {47: "登入頁 → 🔑"})),
        ({"mode": "done", "numbers": [47], "titles": {"47": "登入頁 → 🔑"}},
         format_lane_done([47], {47: "登入頁 → 🔑"})),
        ({"mode": "merged", "numbers": [47, 48], "spec": 51},
         format_batch_done([47, 48], 51)),
        ({"mode": "summary", "numbers": [47], "spec": 51,
          "titles": {"47": "登入頁 → 🔑"}, "coverage": {"47": ["導向 → 🏠"]}},
         format_batch_summary(51, [47], {47: "登入頁 → 🔑"},
                              {47: ["導向 → 🏠"]})),
        # #54 的三條新路。`numbers` 是整批、`fixing` 是沒過的那幾張 — 分開的動作
        # 在 main() 裡由 split_lanes 做,呼叫端不先分好(分錯是無聲的)。
        ({"mode": "split", "numbers": [47, 48], "fixing": [48],
          "titles": {"47": "登入頁 → 🔑", "48": "點頭 → 🔑"}},
         format_split([47], [48], {47: "登入頁 → 🔑", 48: "點頭 → 🔑"})),
        ({"mode": "fixing", "number": 48, "numbers": [47, 48], "fixing": [48],
          "titles": {"48": "點頭 → 🔑"}},
         format_fixing_comment(48, [47], {48: "點頭 → 🔑"})),
        ({"mode": "merged", "numbers": [47, 48], "spec": 51, "fixing": [48],
          "titles": {"48": "點頭 → 🔑"}},
         format_batch_done([47], 51, [48], {48: "點頭 → 🔑"})),
        ({"mode": "summary", "numbers": [47, 48], "spec": 51, "fixing": [48],
          "titles": {"47": "登入頁 → 🔑", "48": "點頭 → 🔑"},
          "coverage": {"47": ["導向 → 🏠"], "48": ["不該出現 → 🚫"]}},
         format_batch_summary(51, [47], {47: "登入頁 → 🔑", 48: "點頭 → 🔑"},
                              {47: ["導向 → 🏠"], 48: ["不該出現 → 🚫"]}, [48])),
    ):
        child = subprocess.run(
            [sys.executable, __file__],
            input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            capture_output=True,
            env=dict(os.environ, PYTHONIOENCODING="cp950"),
        )
        assert child.returncode == 0, (payload["mode"],
                                       child.stderr.decode("utf-8", "replace"))
        # splitlines():子行程在 Windows 上吐 CRLF,這裡驗的是編碼不是行尾
        assert (child.stdout.decode("utf-8").splitlines()
                == want.splitlines()), payload["mode"]

    # 沒給 mode 還是走名單 — #52 的用法整片不能被這片改掉
    child = subprocess.run(
        [sys.executable, __file__],
        input=json.dumps({"tickets": [_ticket(1), _ticket(2, [1])]}).encode(),
        capture_output=True)
    assert child.returncode == 0, child.stderr.decode("utf-8", "replace")
    assert (child.stdout.decode("utf-8").splitlines()
            == format_plan(plan_batch([_ticket(1), _ticket(2, [1])]), {}
                           ).splitlines()), child.stdout

    # 打錯 mode 要當場停,不要靜靜印出空的一片給 client
    child = subprocess.run([sys.executable, __file__], input=b'{"mode": "nope"}',
                           capture_output=True)
    assert child.returncode != 0 and not child.stdout.strip(), child.stdout

    # #53 固化:新加的每一段一樣要把資料餵進這支檔。哪天有人把「開工」改成
    # 在 SKILL.md 裡 echo 一行中文,那就是 #58 原封不動再來一次。
    assert skill_mode_issue(text) is None, skill_mode_issue(text)
    for mode in MODES:
        # 全部換掉 — 同一個 mode 在 SKILL.md 可能被呼叫不只一次
        mutated = text.replace(f'"mode": "{mode}"', '"mode": "nope"')
        assert mutated != text, mode
        got = skill_mode_issue(mutated)
        assert got and mode in got, (mode, got)

    # #54:一張沒過時那三句處置,程式端沒有任何 assert 碰得到 — 在真的 SKILL.md
    # 上咬,而且逐句拿掉都要紅(只留一句就綠 = guard 等於沒裝)。
    assert fail_lane_issue(text) is None, fail_lane_issue(text)
    for pattern, _ in FAIL_LANE_LINES:
        m = pattern.search(text)
        assert m, pattern.pattern
        assert fail_lane_issue(text.replace(m.group(0), "", 1)), m.group(0)

    print("OK batch self-check green")


if __name__ == "__main__":
    # #58 — both ends of the pipe are 中文 and a Windows console is cp950 on
    # both. See AGENTS.md 「會被跑到的 python 檔要釘 UTF-8」.
    sys.stdout.reconfigure(encoding="utf-8")
    if "--self-check" in sys.argv:
        self_check()
        sys.exit(0)
    # after the self-check exit: with stdin closed `sys.stdin` is None, and the
    # checks must still run in a harness that hands us no stdin at all
    sys.stdin.reconfigure(encoding="utf-8")
    main()
