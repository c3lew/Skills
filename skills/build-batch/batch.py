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


def _two(numbers):
    """撞車一定是兩張票 — 少一張的紀錄 client 讀不出「跟誰撞」。

    一張一張合(§7),所以衝突的參與者永遠恰好是「正在合的那張」與「先合進去
    動到同一個檔案的那張」。給不出兩張就是 §7a 沒查完,當場停,不要印一句半殘
    的紀錄出去 — 那句話會被貼到票上,client 拿它當事實讀。
    """
    if len(numbers) != 2:
        raise SystemExit("conflict modes want exactly 2 tickets (正在合的那張、"
                         f"先合進去的那張), got {list(numbers)}")
    return numbers[0], numbers[1]


def _files(files):
    if not files:
        raise SystemExit("conflict modes want at least one file — 「撞在哪個檔案」"
                         "是 client 唯一看得懂的定位")
    return "、".join(files)


def _how(how):
    """`how` 是 agent 現寫的自由文字,而它會被貼上票 — 擋掉貼 diff 這種寫法。

    紀錄是寫給非技術 client 讀的一句話。貼進衝突標記或整段 diff,那一行就從
    「白話紀錄」變成「請你自己看 git」,而這正是這片要消掉的東西。
    """
    if not how or "\n" in how or "<<<<<<<" in how or ">>>>>>>" in how:
        raise SystemExit("`how` 要是一句白話、單行、不含衝突標記 — 它會原封不動"
                         f"貼上票給 client 讀,got {how!r}")
    return how


def format_conflict_resolved(numbers, titles, files, how):
    """撞車解掉之後,兩張票上各留的那一行白話紀錄。

    兩張票貼的是同一句 — client 從哪一張票翻起來,看到的都是完整的「哪兩張撞、
    撞在哪個檔案、怎麼解的」,不用再去對面那張湊。句子由這裡組,不由 agent 現編:
    它是 client 之後回頭對帳的唯一紀錄,措辭漂掉就對不起來。
    """
    a, b = _two(numbers)
    return (f"撞車已解:{_titled(a, titles)} 跟 {_titled(b, titles)} 都改到 "
            f"{_files(files)} — {_how(how)}。合併照常繼續,不用你處理。")


def _stopped_headline(numbers, titles, files):
    """停下那句的第一行。兩張撞是常態,一張是 §7a 查不出另一張的逃生路。

    §7a 有一條「那段內容不是這批任何一條 lane 寫的」的分支 — 那時候另一張票號
    是查不到的,而猜一個貼上票比不講更糟(client 會拿它當事實)。所以那條路
    照實只講正在合的那張 + 跟主線既有內容撞,不是讓 agent 撞牆之後自己現編一句。
    """
    if len(numbers) == 2:
        a, b = numbers
        who = f"{_titled(a, titles)} 跟 {_titled(b, titles)} 都改到 {_files(files)}"
    elif len(numbers) == 1:
        who = (f"{_titled(numbers[0], titles)} 跟主線上既有的內容撞在 "
               f"{_files(files)}")
    else:
        raise SystemExit("conflict-stopped wants 1 or 2 tickets(查得出另一張就給"
                         f"兩張,查不出來就只給正在合的那張), got {list(numbers)}")
    return f"撞車停下:{who},自己解不掉 — 這批合併停在這裡,等你決定。"


def format_conflict_stopped(numbers, titles, files, merged, pending):
    """解不掉的時候,終端機與那兩張票上的同一份白話說明。

    停下來的重點不是「有 conflict」,是 client 要能不看 git 就知道現在的狀態:
    哪兩張撞在哪個檔案、什麼已經進主線了、什麼還原地等著。所以已合/未合兩份清單
    跟撞車那句一起印 — 少了它們,client 得自己去問 git 才敢決定。
    """
    lines = [
        _stopped_headline(numbers, titles, files),
        "",
        f"已經合進主線的({len(merged)} 張):",
    ]
    lines += [f"  {_titled(n, titles)}" for n in merged] or ["  (無)"]
    lines += ["", f"還沒合的({len(pending)} 張),工作區與 branch 都留著:"]
    lines += [f"  {_titled(n, titles)} — {lane_of(n)['worktree']}"
              f"(branch {lane_of(n)['branch']})" for n in pending] or ["  (無)"]
    lines += ["", "沒有猜、沒有強推,也沒有把任何一邊蓋掉。"]
    return "\n".join(lines)

def format_batch_done(numbers, spec):
    """整批驗證綠之後終端機的最後一行:合了幾張 + 下一棒。"""
    return (f"{len(numbers)} 張已合併,"
            f"下一步:`/client-demo #{spec}`(Codex: `$client-demo #{spec}`)"
            " — 一次 demo 這批")


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


def format_batch_summary(spec, numbers, titles, sections):
    """spec 票上那則批次總結 comment(整批唯一一個看得完全批的地方)。"""
    lines = [f"## 批次總結({len(numbers)} 張)", ""]
    lines += [f"- {_titled(n, titles)} — 已合併({lane_of(n)['branch']})"
              for n in numbers]
    lines += ["", "整批驗證:regression + 下列覆蓋驗收項聯集,全綠。", ""]
    lines += [f"- {item}" for item in coverage_union(sections)]
    lines += ["", f"下一步:`/client-demo #{spec}`(Codex: `$client-demo #{spec}`)"]
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
    if mode == "plan":
        print(format_plan(plan_batch(data["tickets"]), titles))
    elif mode == "start":
        print(format_lane_start(numbers, titles))
    elif mode == "done":
        print(format_lane_done(numbers, titles))
    elif mode == "merged":
        print(format_batch_done(numbers, data["spec"]))
    elif mode == "summary":
        print(format_batch_summary(data["spec"], numbers, titles,
                                   data.get("coverage", [])))
    elif mode == "conflict-resolved":
        print(format_conflict_resolved(numbers, titles, data.get("files", []),
                                       data["how"]))
    elif mode == "conflict-stopped":
        print(format_conflict_stopped(numbers, titles, data.get("files", []),
                                      data.get("merged", []),
                                      data.get("pending", [])))
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


# #55:撞車處置的判準全在散文裡 — 「呼叫哪個原件解」「停下時什麼留著」都不是
# 函式,改壞了 batch.py 一條 assert 都不會紅。所以逐句咬。
CONFLICT_LINES = (
    (re.compile(re.escape("`/resolving-merge-conflicts`")),
     "SKILL.md §7b: 撞車要呼叫既有的 `/resolving-merge-conflicts` 解 — 這句不見了,"
     "下一個 agent 會自己發明解法"),
    (re.compile(re.escape("worktree 與 branch 都留著")),
     "SKILL.md §7c: 停下時未合的 lane 要保留 worktree 與 branch — 這句不見了,"
     "client 決定之後那些 lane 就接不回去了"),
    (re.compile(re.escape("git log -S")),
     "SKILL.md §7a: 查「跟誰撞」要用 `git log -S'<那段內容>'` 問「這段文字是誰寫的」— "
     "改回問「誰動過這個檔案」會在第三張乾淨動過同檔時報出錯的票號給 client(QA 實測)"),
    (re.compile(re.escape("git branch --list 'batch/*' --contains")),
     "SKILL.md §7a: 把 commit 換算成 lane 要用 `git branch --contains` — 靠 parse merge "
     "訊息認票,訊息換個寫法就整條啞掉"),
    (re.compile(re.escape("git merge --abort")),
     "SKILL.md §7c: 停下之前要把沒合完的 merge 退掉 — 少了它,client 接手的是一個"
     "帶衝突標記的 index"),
)
# 「不強推」不能只靠散文承諾:文件裡真的貼出一行 `-X ours`,agent 照著跑就把一張票
# 的工作蓋掉了,而且蓋掉的當下沒有人看得見。所以直接禁止這些指令出現在可執行的
# bash block 裡(散文裡點名它們是「不要做」,不受影響)。
FORCE_RE = re.compile(r"--force|-X +(?:ours|theirs)|push +-f\b|reset +--hard")


def forced_merge_issue(text):
    """bash block 裡有沒有把一邊蓋過去的指令(#55)。"""
    for block in BASH_BLOCK_RE.findall(text):
        hit = FORCE_RE.search(block)
        if hit:
            return (f"SKILL.md: a bash block runs `{hit.group(0)}` — 撞車的處置只有"
                    "「解掉」與「停下」兩條,蓋過去會無聲丟掉一張票的工作(#55)")
    return None


def conflict_lines_issue(text):
    """撞車處置的那幾句還在不在(#55)。"""
    for pattern, message in CONFLICT_LINES:
        if not pattern.search(text):
            return message
    return None


MODES = ("start", "done", "merged", "summary", "conflict-resolved",
         "conflict-stopped")


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

    # spec 票的批次總結:每張都列到、聯集列到、結尾是交棒行
    summary = format_batch_summary(
        51, [47, 48], {47: "名單", 48: "點頭"}, [["a"], ["a", "b"]])
    assert "#47 名單 — 已合併(batch/47)" in summary, summary
    assert "#48 點頭 — 已合併(batch/48)" in summary, summary
    assert "- a" in summary and "- b" in summary, summary
    assert summary.count("- a") == 1, summary
    assert summary.rstrip().endswith(
        "下一步:`/client-demo #51`(Codex: `$client-demo #51`)"), summary

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
          "titles": {"47": "登入頁 → 🔑"}, "coverage": [["導向 → 🏠"]]},
         format_batch_summary(51, [47], {47: "登入頁 → 🔑"}, [["導向 → 🏠"]])),
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

    # ---- #55 撞車:解得掉自己解、解不掉停下來 --------------------------------
    # 兩張票貼的是同一句,而且那一句要自己講完「哪兩張、哪個檔案、怎麼解的」—
    # client 不需要知道什麼是 merge conflict,只需要讀得懂這一行。
    resolved = format_conflict_resolved(
        [48, 47], {48: "點頭", 47: "名單"}, ["skills/build-batch/SKILL.md"],
        "兩邊都在 §7 加段落,依序保留")
    assert resolved == (
        "撞車已解:#48 點頭 跟 #47 名單 都改到 skills/build-batch/SKILL.md — "
        "兩邊都在 §7 加段落,依序保留。合併照常繼續,不用你處理。"), resolved
    assert "conflict" not in resolved and "merge" not in resolved, resolved
    # 撞在多個檔案 -> 全部列出來,不只報第一個
    assert "a.py、b.py" in format_conflict_resolved(
        [1, 2], {}, ["a.py", "b.py"], "x"), "multi-file"

    # 少一張票 / 沒有檔案 -> 當場停,不要印半殘的紀錄貼上票
    for bad in ([48], [], [48, 47, 46]):
        try:
            format_conflict_resolved(bad, {}, ["a.py"], "x")
        except SystemExit:
            pass
        else:
            raise AssertionError(f"expected SystemExit for numbers={bad}")
    try:
        format_conflict_resolved([48, 47], {}, [], "x")
    except SystemExit:
        pass
    else:
        raise AssertionError("expected SystemExit for empty files")

    # 解不掉:哪兩張撞在哪個檔案 + 已合的留主線 + 未合的 lane 原地留著
    stopped = format_conflict_stopped(
        [48, 47], {48: "點頭", 47: "名單", 42: "算票", 49: "收尾"},
        ["skills/build-batch/SKILL.md"], [42, 47], [48, 49])
    assert stopped.splitlines() == [
        "撞車停下:#48 點頭 跟 #47 名單 都改到 skills/build-batch/SKILL.md,"
        "自己解不掉 — 這批合併停在這裡,等你決定。",
        "",
        "已經合進主線的(2 張):",
        "  #42 算票",
        "  #47 名單",
        "",
        "還沒合的(2 張),工作區與 branch 都留著:",
        "  #48 點頭 — .git/batch-worktrees/48(branch batch/48)",
        "  #49 收尾 — .git/batch-worktrees/49(branch batch/49)",
        "",
        "沒有猜、沒有強推,也沒有把任何一邊蓋掉。",
    ], stopped
    # 停下那句一樣是給非技術 client 讀的 — 第一行不准漏術語出來。後面幾行留著
    # branch 名與 lane 路徑是刻意的:那是 client(或他找來的人)要回到那個工作區
    # 唯一能貼進終端機的東西,不是術語裝飾。
    headline = stopped.splitlines()[0]
    for jargon in ("conflict", "merge", "index", "rebase", "abort"):
        assert jargon not in headline.lower(), (jargon, headline)

    # 未合 lane 的路徑同樣由 lane_of 算 — client 照著它就能回到那個工作區
    for n in (48, 49):
        assert lane_of(n)["worktree"] in stopped and lane_of(n)["branch"] in stopped
    # 第一張就撞:已合的是空的,照樣要印出來讓 client 知道主線沒被動過
    first = format_conflict_stopped([48, 47], {}, ["a.py"], [], [48])
    assert "已經合進主線的(0 張):\n  (無)" in first, first

    # §7a 查不出另一張(那段內容不是這批寫的)-> 只給一張,照實講跟主線既有內容撞。
    # 文件叫 agent 走這條路,工具就要收得下來 — 收不下來 agent 只能自己現編一句貼上票。
    solo = format_conflict_stopped([48], {48: "點頭"}, ["docs/notes.md"], [47], [48])
    assert solo.splitlines()[0] == (
        "撞車停下:#48 點頭 跟主線上既有的內容撞在 docs/notes.md,自己解不掉 — "
        "這批合併停在這裡,等你決定。"), solo
    assert "#47" not in solo.splitlines()[0], solo  # 查不出來就不猜票號
    for jargon in ("conflict", "merge", "index", "rebase", "abort"):
        assert jargon not in solo.splitlines()[0].lower(), (jargon, solo)
    # 0 張或 3 張還是當場停
    for bad in ([], [48, 47, 46]):
        try:
            format_conflict_stopped(bad, {}, ["a.py"], [], [])
        except SystemExit:
            pass
        else:
            raise AssertionError(f"expected SystemExit for numbers={bad}")

    # `how` 是 agent 現寫的自由文字,會原封不動貼上票 — 貼 diff / 衝突標記要當場停
    for bad_how in ("", "第一行\n第二行", "<<<<<<< HEAD", "a\n>>>>>>> batch/48"):
        try:
            format_conflict_resolved([48, 47], {}, ["a.py"], bad_how)
        except SystemExit:
            pass
        else:
            raise AssertionError(f"expected SystemExit for how={bad_how!r}")

    # #55 固化:撞車的處置有一半是散文(呼叫哪個原件、停下時什麼留著),
    # 函式測不到 — 拿真的 SKILL.md 咬,拿掉任何一句要紅。
    assert conflict_lines_issue(text) is None, conflict_lines_issue(text)
    for original, label in (
        ("`/resolving-merge-conflicts`", "§7b 呼叫原件解"),
        ("worktree 與 branch 都留著", "§7c 未合的 lane 留著"),
        ("git log -S", "§7a 認票問的是那段內容不是那個檔案"),
        ("git branch --list 'batch/*' --contains", "§7a 用 commit 歸屬換算 lane"),
        ("git merge --abort", "§7c 退掉沒合完的 merge"),
    ):
        assert original in text, label
        # 全部換掉 — 同一句在 SKILL.md 可能出現不只一次,只拿掉第一個等於沒 mutate
        assert conflict_lines_issue(text.replace(original, "")), label

    # 「不強推」要咬在可執行的那一面:文件裡真的貼出這些指令就是紅的
    assert forced_merge_issue(text) is None, forced_merge_issue(text)
    for command in ("git push --force", "git merge -X ours batch/47",
                    "git merge -X theirs batch/47", "git reset --hard origin/main",
                    "git push -f"):
        got = forced_merge_issue(text + fence(command))
        assert got and "#55" in got, (command, got)
    # 散文裡點名「不要做」不算 — 那正是文件該講的話
    assert forced_merge_issue("不要用 --force,也不要 -X ours") is None

    # 兩種撞車輸出同樣印在 cp950 的主控台上,而且會被 gh 貼回票 — 自己走一次
    for payload, want in (
        ({"mode": "conflict-resolved", "numbers": [48, 47],
          "titles": {"48": "登入頁 → 🔑", "47": "導向"},
          "files": ["登入.py"], "how": "兩邊的段落都留著 → 依序擺"},
         format_conflict_resolved([48, 47], {48: "登入頁 → 🔑", 47: "導向"},
                                  ["登入.py"], "兩邊的段落都留著 → 依序擺")),
        ({"mode": "conflict-stopped", "numbers": [48, 47],
          "titles": {"48": "登入頁 → 🔑", "47": "導向"},
          "files": ["登入.py"], "merged": [47], "pending": [48]},
         format_conflict_stopped([48, 47], {48: "登入頁 → 🔑", 47: "導向"},
                                 ["登入.py"], [47], [48])),
    ):
        child = subprocess.run(
            [sys.executable, __file__],
            input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            capture_output=True,
            env=dict(os.environ, PYTHONIOENCODING="cp950"),
        )
        assert child.returncode == 0, (payload["mode"],
                                       child.stderr.decode("utf-8", "replace"))
        assert (child.stdout.decode("utf-8").splitlines()
                == want.splitlines()), payload["mode"]

    # 票號給錯數量 -> 子行程也要當場停,不要靜靜貼一句半殘的紀錄上票
    child = subprocess.run(
        [sys.executable, __file__],
        input=json.dumps({"mode": "conflict-resolved", "numbers": [48],
                          "files": ["a.py"], "how": "x"}).encode(),
        capture_output=True)
    assert child.returncode != 0 and not child.stdout.strip(), child.stdout

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
