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
    # #56:排隊的票在輪到之前是「完全沒被碰過」的狀態 — client 中途喊停時,
    # 這句是他唯一的保證(被貼過「開工」卻沒人在做的票,下一個人只能靠猜)。
    (re.compile(re.escape("排隊中的票在被開工前完全不動它")),
     "SKILL.md §6: 排隊的票在開工前不碰的承諾不見了(#56 驗收項)"),
    # #56:中斷之後 client 要知道自己手上剩什麼 — 哪些已經在主線、哪些還留著
    # 可以續。這句沒了,中斷就變成「不知道要不要全部重來」。
    (re.compile(re.escape("已經 merge 的留在主線,未合併的 lane 留著 worktree "
                          "與 branch")),
     "SKILL.md §7: 中斷之後留下什麼的承諾不見了(#56 驗收項)"),
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


def format_lane_start(numbers, titles, running=(), cap=CAP):
    """一張一行「開工」— client 從終端機看得到哪張在哪個工作區跑。

    開哪幾張走 `refill`,不是把 `numbers` 照單全開:`numbers` 是「要開 → 排隊」
    整份名單,`running` 是 §6.1 接續下來、已經在跑的 lane。名額扣在這裡而不是
    留給 agent 在文件上心算 —— 接續兩條、名單又是滿的 3 張時,心算的版本會開出
    5 條同時在跑,而那個畫面跟正常的一模一樣。印幾行就開幾個 worktree。
    """
    numbers = refill(running, numbers, cap)[0]

    def line(n):
        lane = lane_of(n)
        return (f"開工 {_titled(n, titles)} — 工作區 {lane['worktree']}"
                f"(branch {lane['branch']})")

    return "\n".join(line(n) for n in numbers)


def format_lane_done(numbers, titles):
    """一張一行「完成」— lane 內 build + QA 都綠才印。"""
    return "\n".join(f"完成 {_titled(n, titles)} — build + QA 綠" for n in numbers)


def refill(running, queue, cap=CAP):
    """佇列補位:哪幾張現在開得起來,開完誰在跑、誰還在排。

    回傳 `(start_now, running_after, queue_after)`。這是這片唯一真正的邏輯,
    而它守的不變量只有一條:**同時跑的 lane 數永遠 <= cap**。違反了畫面上看
    起來跟正常沒兩樣(只是多一條 lane 在跑),沒有任何東西會當場紅 —— 所以它
    是純函式,由 `self_check` 用整場模擬咬,不是留給 agent 每次現場心算。

    已經在跑的票不會被再開一次:重跑 `/build-batch` 接續既有 worktree 走的就是
    這條路(`running` 是既有 lane,`queue` 是整份名單),重複開一個 worktree 到
    同一個路徑是 git 當場失敗,但更糟的是它可能開到一半的分支上。
    """
    running = list(running)
    pending = [n for n in queue if n not in running]
    slots = max(cap - len(running), 0)
    start = pending[:slots]
    return start, running + start, pending[slots:]


def format_lane_refill(running, queue, titles, cap=CAP):
    """補位一行 — 補了誰、現在同時跑幾條、佇列還剩幾張。

    補誰是 `refill` 算的,不是呼叫端算好餵進來的:agent 手上有的是「誰還在跑、
    誰還在排」這種現場事實,「還剩幾個名額」是它每補一次就要重算一次的算術,
    算錯不會有人紅。所以這裡只收事實,名額自己算。

    「同時跑 N 條」印在同一行,因為 cap 是這片唯一會被違反的不變量,而違反的
    畫面跟正常長得一樣。印出來 client 一眼看得到 3,不用自己去數 worktree。
    """
    start, running_after, queue_after = refill(running, queue, cap)
    tail = f";同時跑 {len(running_after)} 條,佇列剩 {len(queue_after)} 張"
    if not start:
        return "不補位 — 沒有名額或佇列已空" + tail

    def line(n):
        lane = lane_of(n)
        return (f"補位 {_titled(n, titles)} — 工作區 {lane['worktree']}"
                f"(branch {lane['branch']})" + tail)

    return "\n".join(line(n) for n in start)


def format_lane_resume(numbers, titles):
    """重跑時接續既有 lane 的那幾行 — 不重開,不再 `git worktree add`。"""
    if not numbers:
        return "沒有既有 lane — 這是乾淨的一批,照 §6.2 開頭那幾條開下去"

    def line(n):
        lane = lane_of(n)
        return (f"接續 {_titled(n, titles)} — 既有工作區 {lane['worktree']}"
                f"(branch {lane['branch']})還在,不重開")

    return "\n".join(line(n) for n in numbers)


def format_lane_interrupted(numbers, titles, spec):
    """中斷時每條未合併 lane 留在票上的那一行 — 「中斷,可續」的原句。"""
    def line(n):
        lane = lane_of(n)
        return (f"中斷,可續 {_titled(n, titles)} — 未合併,工作區 "
                f"{lane['worktree']} 與 branch {lane['branch']} 都留著;"
                f"重跑 `/build-batch #{spec}`(Codex: `$build-batch #{spec}`)"
                "會接續這條 lane")

    return "\n".join(line(n) for n in numbers)


LANE_PATH_RE = re.compile(re.escape(LANE_ROOT) + r"/(\d+)(?![\w.-])")


def lane_numbers(worktrees):
    """`git worktree list --porcelain` 的輸出 -> 還活著的 lane 票號。

    解析放在這裡而不是留給 agent 讀路徑:認錯一條就是去 merge 一條根本不是
    這條線開的 branch。母體同 §9 —— 只認 LANE_ROOT 底下的,因為完整輸出還有
    主 repo 與別人開的 worktree(Claude Code 給 subagent 常駐的
    `.claude/worktrees/agent-*`)。路徑分隔符先正規化成 `/` — Windows 上這條
    輸出有時是反斜線版本的絕對路徑,不正規化就一條都認不出來,而「認不出來」
    的畫面跟「真的沒有殘留」一模一樣。
    """
    seen = []
    for m in LANE_PATH_RE.finditer(worktrees.replace("\\", "/")):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return sorted(seen)


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


def _who(numbers, titles, files):
    """「誰跟誰撞在哪個檔案」那半句。`numbers[0]` 是正在合的那張,其餘是對面。

    對面有幾張是查出來的結果,不是我們挑的(§7a):這批裡自己動過那個檔案的
    lane 就是候選。三種都要講得出來,因為三種都真的會發生 —

    - 一張:常態,講「都改到 X」。
    - 零張:那個檔案這批沒人動過(主線自己的 commit 改的)。猜一個票號貼上票
      比不講更糟,所以照實說跟主線既有的內容撞。
    - 多張:內容層級認不出唯一那張的時候(§7a 最後一步)。列出候選是誠實的,
      隨便挑一張講死才是 client 會被指去看錯票的那條路 —— 前四輪 QA 有三輪
      卡在這件事上。
    """
    if not numbers:
        raise SystemExit("conflict modes want at least the ticket being merged, "
                         "got []")
    here = _titled(numbers[0], titles)
    others = numbers[1:]
    if not others:
        return f"{here} 跟主線上既有的內容撞在 {_files(files)}"
    if len(others) == 1:
        return f"{here} 跟 {_titled(others[0], titles)} 都改到 {_files(files)}"
    listed = "、".join(_titled(n, titles) for n in others)
    return (f"{here} 跟這批裡同樣改過 {_files(files)} 的 {listed} 撞在一起"
            f"(是哪一張要打開那個檔案才分得出來)")


def format_conflict_resolved(numbers, titles, files, how):
    """撞車解掉之後,相關的票上各留的那一行白話紀錄。

    每張票貼的是同一句 — client 從哪一張票翻起來,看到的都是完整的「哪幾張撞、
    撞在哪個檔案、怎麼解的」,不用再去對面那張湊。句子由這裡組,不由 agent 現編:
    它是 client 之後回頭對帳的唯一紀錄,措辭漂掉就對不起來。
    """
    return f"撞車已解:{_who(numbers, titles, files)} — {_how(how)}。合併照常繼續,不用你處理。"


def format_conflict_stopped(numbers, titles, files, merged, pending):
    """解不掉的時候,終端機與相關的票上的同一份白話說明。

    停下來的重點不是「有 conflict」,是 client 要能不看 git 就知道現在的狀態:
    誰跟誰撞在哪個檔案、什麼已經進主線了、什麼還原地等著。所以已合/未合兩份清單
    跟撞車那句一起印 — 少了它們,client 得自己去問 git 才敢決定。
    """
    lines = [
        f"撞車停下:{_who(numbers, titles, files)},自己解不掉 — 這批合併停在這裡,等你決定。",
        "",
        f"已經合進主線的({len(merged)} 張):",
    ]
    lines += [f"  {_titled(n, titles)}" for n in merged] or ["  (無)"]
    lines += ["", f"還沒合的({len(pending)} 張),工作區與 branch 都留著:"]
    lines += [f"  {_titled(n, titles)} — {lane_of(n)['worktree']}"
              f"(branch {lane_of(n)['branch']})" for n in pending] or ["  (無)"]
    lines += ["", "沒有猜、沒有強推,也沒有把任何一邊蓋掉。"]
    return "\n".join(lines)




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


GRADE_FAST, GRADE_SLOW = "快", "慢"

# 「無 — 由後續票的驗收項間接驗證」是「這張沒有覆蓋驗收項」的寫法,不是一條驗收項。
# agent 把那段原封不動餵進來時它會變成 coverage 裡唯一一筆,於是一張純基礎工程的票
# 被判成慢 —— 方向是安全的,但快車道就等於沒有。所以在這裡認掉。
NO_COVERAGE_RE = re.compile(r"^無\s*[—–-]")


def classify_one(coverage, judgement=False, override=None):
    """一張票判快或慢,連理由一起回。

    三條規則,列出來的順序就是優先序:

    - **動到判斷邏輯 / 篩選條件 / 分類判準 / 資料寫入 -> 一律慢**。硬規則,蓋過
      `coverage`,也蓋過 client 的 override —— 驗收清單第 4 條就是它:那種改動
      表面上看不出來、錯了最慘,放行一次就是拿掉這條線唯一的防護。想改快的時候
      當場停,不靜靜忽略 override(靜靜忽略的畫面跟改成功一模一樣)。
    - **client 當場改 -> 照他改的**。否決權是驗收清單第 1 條,所以它是資料,
      不是留給 agent 在文件上記得要照做的一句話。
    - **有覆蓋驗收項 -> 慢;沒有 -> 快**。

    `judgement` 是 agent 讀 diff 判的,一定會判錯 —— 這裡不為了判準而加規則。
    判錯的代價要靠降級回路兜(spec #106 決策 3:標快的票對驗收清單有一條沒過
    就當場降級),而那個回路還沒出貨 —— `grep -rn 降級回路 skills/` 在 #120 當下
    7 個 hit 全在那句散文與這裡的註解,沒有一支 skill 在做那件事。這句沒有 pin
    守著,回路出貨那天要回來改(#123 那張票要補的就是這種形狀)。就算
    出了,它接得住的也只有 `coverage` 非空的那半:`coverage` 是空的那半一條驗收
    項都沒有,回路不會被觸發,`judgement` 就是那半唯一的一道。這是宣告過的
    天花板,不是這裡要補的規則。
    """
    items = [c for c in coverage if not NO_COVERAGE_RE.match(str(c).strip())]
    # 認不得的 override 先擋 —— 擺在硬規則前面,因為硬規則那條路的結果剛好也是慢:
    # 打錯字被靜靜吃掉跟 client 根本沒改長得一模一樣,他下次還是會那樣打。
    if override is not None and override not in (GRADE_FAST, GRADE_SLOW):
        raise SystemExit(f"override 只能是「快」或「慢」,拿到 {override!r} —— "
                         "打錯一個字就靜靜照原判寫進票,不猜")
    if judgement:
        if override == GRADE_FAST:
            raise SystemExit(
                "這張動到判斷邏輯或資料寫入,硬規則一律慢 —— 改不成快。"
                "驗收清單第 4 條就是它。要改快只有一條路:回去改票的內容,"
                "把動到判斷邏輯或資料寫入的那部分切出去,再重切一次分級。"
                "票的內容沒變就是慢,client 說了也一樣")
        return GRADE_SLOW, "動到判斷邏輯或資料寫入,硬規則一律慢"
    if override is not None:
        return override, f"你當場改成「{override}」"
    if items:
        return GRADE_SLOW, f"覆蓋 {len(items)} 條驗收項"
    return GRADE_FAST, "沒有覆蓋驗收項,不會有你看得到的行為"


def classify_tickets(tickets):
    """整批票 -> [(票號, 快/慢, 理由)],保序。"""
    return [(t["number"],
             *classify_one(t.get("coverage", []), t.get("judgement", False),
                           t.get("override")))
            for t in tickets]


def format_grade_line(grade, reason):
    """寫進票 body「覆蓋驗收項」段下方的那一行。

    格式由這裡定、由守門釘著:下游要拿這一行認車道,措辭漂掉就認不出來,而
    「認不出來」跟「這張是慢的」在票面上長得一樣。
    """
    return f"分級:{grade} — {reason}"


def format_classify(rows, titles):
    """client 看的整批分級清單 + 逐張要貼進票的那幾行。

    印在這裡而不是留給 agent 現場排版:client 是照這份清單點頭的,而他點頭的
    對象跟真的寫進票裡的那幾行必須是同一份 —— 分開排版就會有一天不一樣。
    """
    lines = [f"分級({len(rows)} 張)— 標「慢」的會演給你看,標「快」的不會:"]
    lines += [f"  {grade}  {_titled(n, titles)} — {reason}"
              for n, grade, reason in rows] or ["  (無)"]
    lines += ["", "點頭之後,這幾行逐張貼進票 body 的「覆蓋驗收項」段下方:"]
    lines += [f"  #{n}  {format_grade_line(grade, reason)}"
              for n, grade, reason in rows] or ["  (無)"]
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
    elif mode == "classify":
        # 不進 MODES:那份表咬的是 build-batch 自己的 SKILL.md,而 classify 的
        # 呼叫端是 slice-tickets。它由 classify_command_issue 對著那支檔咬。
        print(format_classify(classify_tickets(data["tickets"]), titles))
    elif mode == "start":
        print(format_lane_start(numbers, titles, data.get("running", [])))
    elif mode == "done":
        print(format_lane_done(numbers, titles))
    elif mode == "split":
        print(format_split(merged, fixing, titles))
    elif mode == "refill":
        print(format_lane_refill(data.get("running", []),
                                 data.get("queue", []), titles))
    elif mode == "resume":
        print(format_lane_resume(lane_numbers(data.get("worktrees", "")),
                                 titles))
    elif mode == "interrupted":
        print(format_lane_interrupted(numbers, titles, data["spec"]))
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
    elif mode == "conflict-resolved":
        print(format_conflict_resolved(numbers, titles, data.get("files", []),
                                       data["how"]))
    elif mode == "conflict-stopped":
        print(format_conflict_stopped(numbers, titles, data.get("files", []),
                                      data.get("merged", []),
                                      data.get("pending", [])))
    else:
        raise SystemExit(f"unknown mode: {mode!r} (want one of plan, classify, "
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


# #55:撞車處置的判準全在散文裡 — 「呼叫哪個原件解」「停下時什麼留著」都不是
# 函式,改壞了 batch.py 一條 assert 都不會紅。所以逐句咬。
CONFLICT_LINES = (
    (re.compile(re.escape("`/resolving-merge-conflicts`")),
     "SKILL.md 8b: 撞車要呼叫既有的 /resolving-merge-conflicts 解 — 這句不見了,"
     "下一個 agent 會自己發明解法"),
    (re.compile(re.escape("git merge-base")),
     "SKILL.md 8a: 認票要問「已合的那幾張裡誰自己動過這個檔案」(merge-base + "
     "git diff --name-only)— 改回讀內容認票,圖檔沒有內容可讀、第三張乾淨改過"
     "同一個檔案時還會靜靜報出錯的票號給 client(QA 第 3、4 輪各實測到一次)"),
    (re.compile(re.escape('merged="')),
     "SKILL.md 8a: 候選母體要是「這批已經合進主線的那幾張」(agent 手上的名單),"
     "不是 git branch --list 'batch/*' — 那會把還沒輪到的 lane 與上一批殘留的 branch "
     "一起撈進來,印一張跟這次 merge 無關的票號給 client(QA 第 5 輪實測)"),
    (re.compile(re.escape("--name-status -M")),
     "SKILL.md 8a: 正在合的那張把檔案改名時,對面動的是舊名字 — 少了這行 rename "
     "pre-image 的查法,候選會是空的,然後對 client 講一句假的「跟主線上既有的內容撞」"
     "(QA 第 5 輪實測)"),
    (re.compile(re.escape("git branch --list 'batch/*' --contains")),
     "SKILL.md 8a: 候選多於一條時要用 git blame 那一行 + --contains 換算成 lane"),
    (re.compile(re.escape("worktree 與 branch 都留著")),
     "SKILL.md 8c: 停下時未合的 lane 要保留 worktree 與 branch — 這句不見了,"
     "client 決定之後那些 lane 就接不回去了"),
    (re.compile(re.escape("git merge --abort")),
     "SKILL.md 8c: 停下之前要把沒合完的 merge 退掉 — 少了它,client 接手的是一個"
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


# #108 固化:分級的判準是可計算的(classify),但它旁邊有幾句只有散文講得出來的
# 東西 —— 問點頭那句、否決權怎麼兌現、那支檔不在時的退路、硬規則被 client 頂著時
# 的處置、以及這條判準的天花板蓋到哪。每一句刪掉 batch.py 照樣全綠,而 agent 會
# 回去做它出廠時的事:自己判、自己排版、判錯了也沒人有否決權。所以在 slice-tickets
# 的 SKILL.md 上逐句咬。清單長度會長,別在這裡記總數 —— 記了就會過期。
CLASSIFY_LINES = (
    (re.compile(re.escape("這批的快慢分級,有要改的嗎?")),
     "slice-tickets SKILL.md: 印完分級清單問 client 點頭的那句不見了 —— 沒有那一問"
     "就沒有否決權,而驗收清單第 1 條要的就是否決權"),
    (re.compile(re.escape("照你說的改,改完的才是寫進票裡的那個")),
     "slice-tickets SKILL.md: client 改完之後以他改的為準那句不見了 —— 少了它,"
     "agent 會問完點頭卻照自己原本判的寫進票"),
    (re.compile(re.escape("`batch.py` 不在 → 這批整批判慢車道")),
     "slice-tickets SKILL.md: batch.py 不在時的退路那句不見了 —— 借來的判斷本來"
     "就可能沒裝,而現場重寫一份比沒有更糟(兩份會各說各話)"),
    (re.compile(re.escape("判錯必然會發生")),
     "slice-tickets SKILL.md: 這條判準的天花板那句不見了 —— judgement 是 agent 讀"
     "diff 判的,不明講就變成隱含假設,下一個人會去加規則而不是把它當宣告過的邊界"),
    # #120:硬規則蓋過 client 的 override 這件事,散文裡一句都沒有 —— agent 被
    # client 頂著、batch.py 當場停,文件沒告訴他該怎麼辦,而最短的一條路是把
    # judgement 改成 false 重跑,一路綠。
    (re.compile(re.escape("不要自己去改 `judgement` 旗標讓它過")),
     "slice-tickets SKILL.md: 硬規則被 client 頂著時的處置那句不見了 —— 沒有它,"
     "agent 會把 judgement 改成 false 重跑,而拆掉的當下沒有任何東西會紅"),
    # #120:天花板原本寫「判錯的代價由降級回路關住」,對 coverage=[] 的票不成立
    # —— 那種票一條驗收項都沒有,降級回路永遠不會被觸發。網子的洞剛好就是這條
    # 判準要守的那一格,寫成「關住」就是過度宣稱。
    (re.compile(re.escape("接得住的是**有驗收項**的那半")),
     "slice-tickets SKILL.md: 降級回路只接得住一半那句不見了 —— 少了它天花板就"
     "回到「關住」那個過度宣稱,而 coverage 是空的那半根本不會觸發降級回路"),
)


def classify_lines_issue(text):
    """呼叫 classify 的那支 SKILL.md 有沒有逐句講到 CLASSIFY_LINES(#108)。"""
    for pattern, message in CLASSIFY_LINES:
        if not pattern.search(text):
            return message
    return None


def classify_command_issue(text):
    """分級清單有沒有走進這支檔(#108,跟 #58 同一種形狀)。

    `skill_command_issue` 守的是 build-batch 自己那幾段;這條守 slice-tickets ——
    分級清單同樣全是中文、同樣印在 cp950 的主控台上,而且 client 是照它點頭的。
    在文件裡 echo 一行中文就等於印在所有測試與所有 pin 的外面。
    """
    blocks = BASH_BLOCK_RE.findall(text)
    if not any("batch.py" in b and '"mode": "classify"' in b and "<<" in b
               for b in blocks):
        return ("slice-tickets SKILL.md: no bash block feeds the ticket JSON "
                "into batch.py with \"mode\": \"classify\" — 分級清單印在沒有"
                "測試、沒有 UTF-8 pin 碰得到的地方(#58 的形狀)")
    if any(INLINE_PYTHON_RE.search(b) for b in blocks):
        return ("slice-tickets SKILL.md: an inline `python -c` prints for the "
                "client — outside this self-check and outside the __main__ pin")
    return None


MODES = ("start", "done", "split", "refill", "resume", "interrupted",
         "merged", "fixing", "summary", "conflict-resolved", "conflict-stopped")


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
        ("排隊中的票在被開工前完全不動它", "§6 排隊不碰"),
        ("已經 merge 的留在主線,未合併的 lane 留著 worktree 與 branch",
         "§7 中斷留下什麼"),
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
        ({"mode": "refill", "running": [48], "queue": [47],
          "titles": {"47": "登入頁 → 🔑"}},
         format_lane_refill([48], [47], {47: "登入頁 → 🔑"})),
        ({"mode": "resume",
          "worktrees": "worktree D:/repo/.git/batch-worktrees/47",
          "titles": {"47": "登入頁 → 🔑"}},
         format_lane_resume([47], {47: "登入頁 → 🔑"})),
        ({"mode": "interrupted", "numbers": [47], "spec": 51,
          "titles": {"47": "登入頁 → 🔑"}},
         format_lane_interrupted([47], {47: "登入頁 → 🔑"}, 51)),
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

    # #54:「當場停」的訊息全是中文,而且印在 stderr。stdout 那條路釘過了,
    # stderr 沒釘的話 client 看到的是一串問號 — 停得對、看不懂,等於沒停。
    # 每一種停法各跑一次真的子行程,console 假裝成 cp950。
    for payload, want in (
        (b'{"mode": "split", "numbers": [47], "fixing": [4]}', "#4"),
        (b'{"mode": "summary", "numbers": [47, 42], "spec": 51, '
         b'"coverage": {"47": ["a"]}}', "#42"),
        (b'{"mode": "summary", "numbers": [47], "spec": 51, '
         b'"coverage": {"#47": ["a"]}}', "票號"),
        (b'{"mode": "fixing", "number": 47, "numbers": [47, 48], '
         b'"fixing": [48]}', "#47"),
    ):
        child = subprocess.run(
            [sys.executable, __file__], input=payload, capture_output=True,
            env=dict(os.environ, PYTHONIOENCODING="cp950"))
        assert child.returncode != 0 and not child.stdout.strip(), payload
        err = child.stderr.decode("utf-8")
        assert want in err, (payload, err)
        # 沒釘 stderr 的話中文會變成 cp950 的問號串 / 壞碼,decode 得出來也不是原句
        assert "?" not in err, (payload, err)

    # ---- #56 排隊補位 / 中斷續跑 --------------------------------------------
    # 整場模擬:5 張能跑、一次收掉一條 lane。要同時成立三件事 —— 開頭只開 3 條、
    # 全程同時跑的數不超過 cap、每張最後都輪到。這是 refill 存在的理由,而它壞掉
    # 的畫面(多一條 lane 在跑)跟正常長得一模一樣,沒有東西會當場紅。
    start, running, queue = refill([], [1, 2, 3, 4, 5])
    assert (start, running, queue) == ([1, 2, 3], [1, 2, 3], [4, 5])
    opened = list(start)
    while running:
        running = running[1:]  # 收掉一條(綠或紅都一樣要讓出名額)
        start, running, queue = refill(running, queue)
        assert len(running) <= CAP, running
        opened += start
    assert opened == [1, 2, 3, 4, 5], opened
    assert queue == []

    # 名額滿了不補、佇列空了不補
    assert refill([1, 2, 3], [4]) == ([], [1, 2, 3], [4])
    assert refill([1], []) == ([], [1], [])
    # 已經在跑的票不會被再開一次 — 重跑接續既有 lane 走的就是這條
    assert refill([47], [47, 48]) == ([48], [47, 48], [])
    # cap 是參數,不是硬編在函式體裡
    assert refill([], [1, 2], cap=1) == ([1], [1], [2])
    # 純函式:不改到餵進來的 list
    running_in, queue_in = [1], [2, 3]
    refill(running_in, queue_in)
    assert running_in == [1] and queue_in == [2, 3]

    # 補位一行:補了誰、在哪個工作區、同時跑幾條、佇列剩幾張
    got = format_lane_refill([48, 42], [50, 51], {50: "補位"})
    assert got == ("補位 #50 補位 — 工作區 .git/batch-worktrees/50"
                   "(branch batch/50);同時跑 3 條,佇列剩 1 張"), got
    # 一次讓出兩個名額就補兩張,兩行的數字都是補完之後的狀態
    got = format_lane_refill([48], [50, 51, 52], {}).splitlines()
    assert len(got) == 2 and all("同時跑 3 條,佇列剩 1 張" in l for l in got), got
    # 沒名額 / 沒票可補時不是靜靜印一片空白給 client
    assert format_lane_refill([1, 2, 3], [4], {}).startswith("不補位"), "沒名額"
    assert format_lane_refill([], [], {}).startswith("不補位"), "佇列空"

    # 既有 lane 的票號由路徑認,不由 agent 讀 —— 認錯一條就是去 merge 一條
    # 根本不是這條線開的 branch
    porcelain = "\n".join([
        "worktree D:/repo", "HEAD abc", "branch refs/heads/main", "",
        "worktree D:/repo/.git/batch-worktrees/48", "branch refs/heads/batch/48",
        "", "worktree D:/repo/.git/batch-worktrees/47",
        "branch refs/heads/batch/47", "",
        "worktree D:/repo/.claude/worktrees/agent-9", "",
    ])
    assert lane_numbers(porcelain) == [47, 48], lane_numbers(porcelain)
    # 主 repo 與別人開的 worktree 都不是 lane(§9 同一個母體)
    assert lane_numbers("worktree D:/repo\nworktree D:/repo/.claude/"
                        "worktrees/agent-9") == []
    # Windows 的反斜線版本一樣要認得,而且同一條只算一次
    assert lane_numbers("worktree D:\\repo\\.git\\batch-worktrees\\47\n"
                        "worktree D:/repo/.git/batch-worktrees/47") == [47]
    assert lane_numbers("") == []
    # 票號要整段對齊 — `47-old`、`47.bak` 這種殘骸不是 lane 47
    assert lane_numbers("worktree D:/repo/.git/batch-worktrees/47-old") == []
    assert lane_numbers("worktree D:/repo/.git/batch-worktrees/47/sub") == [47]

    # 接續一行:既有工作區與 branch 都指得出來,而且明說不重開
    assert format_lane_resume([47], {47: "名單"}) == (
        "接續 #47 名單 — 既有工作區 .git/batch-worktrees/47"
        "(branch batch/47)還在,不重開")
    # 沒有既有 lane 時不是印一行空白給 client
    assert format_lane_resume([], {}).startswith("沒有既有 lane")
    # 中斷一行:「中斷,可續」的原句 + 留下什麼 + 怎麼續(兩端指令都在)
    stopped = format_lane_interrupted([47], {47: "名單"}, 51)
    assert stopped.startswith("中斷,可續 #47 名單 — 未合併,"), stopped
    assert ".git/batch-worktrees/47" in stopped and "batch/47" in stopped, stopped
    assert ("`/build-batch #51`" in stopped
            and "`$build-batch #51`" in stopped), stopped

    # 開頭那幾條也扣名額:接續 2 條 + 名單 3 張,只准再開 1 張。這條是 code
    # review 抓到的洞 —— 原本 §6.2 叫 agent「自己扣掉接續的那幾條」,而算錯開出
    # 5 條同時在跑的畫面跟正常的一模一樣。
    opening = format_lane_start([47, 48, 42], {}, running=[61, 62]).splitlines()
    assert len(opening) == 1 and opening[0].startswith("開工 #47"), opening
    # 名單比 cap 長 -> 只開前 cap 張,其餘留在佇列(沒印到就是沒開)
    assert len(format_lane_start([1, 2, 3, 4, 5], {}).splitlines()) == CAP
    # 名額已經滿 -> 一行都不印,agent 就一個 worktree 都不會開
    assert format_lane_start([47], {}, running=[61, 62, 63]) == ""
    # #52/#53 的既有用法不變:沒接續、名單沒超過 cap,就是照單開
    assert format_lane_start([47, 48], {47: "名單", 48: "點頭"}).splitlines() == [
        "開工 #47 名單 — 工作區 .git/batch-worktrees/47(branch batch/47)",
        "開工 #48 點頭 — 工作區 .git/batch-worktrees/48(branch batch/48)",
    ]

    # SKILL.md §6.1:接續偵測問的母體跟 §10 清場判準是同一個(打錯就是撈不到
    # 任何既有 lane,一路綠著把同一張票重開一次)。母體字串要出現兩次 —— §6.1
    # 一次、§10 一次;只錨「有沒有這串」的話,§6.1 整段砍掉照樣綠。
    assert text.count(f"grep -F /{LANE_ROOT}/") >= 2, text.count(
        f"grep -F /{LANE_ROOT}/")
    assert "### 6.1 先接續上一次中斷的 lane" in text
    # 開工那段要收 running(接續的 lane),不然名額扣不到
    assert '"mode": "start", "numbers": [47, 48, 42, 50], "running": []' in text

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

    # ---- #55 撞車:解得掉自己解、解不掉停下來 --------------------------------
    # 相關的票貼的是同一句,而且那一句要自己講完「誰跟誰、哪個檔案、怎麼解的」—
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

    # §7a 的三種認票結果都要講得出來(對面幾張是查出來的,不是我們挑的)
    #   0 張:那個檔案這批沒人動過 -> 照實講跟主線既有的內容撞,不猜票號
    solo = _who([48], {48: "點頭"}, ["a.py"])
    assert solo == "#48 點頭 跟主線上既有的內容撞在 a.py", solo
    #   多張:內容層級分不出唯一那張 -> 列出候選,不挑一張講死
    many = _who([48, 47, 42], {48: "點頭", 47: "名單", 42: "算票"}, ["a.py"])
    assert many == ("#48 點頭 跟這批裡同樣改過 a.py 的 #47 名單、#42 算票 撞在一起"
                    "(是哪一張要打開那個檔案才分得出來)"), many
    #   連正在合的那張都沒給 -> 當場停,不要印半殘的紀錄貼上票
    for bad in ([], ()):
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

    # `how` 是 agent 現寫的自由文字,會原封不動貼上票 — 貼 diff / 衝突標記要當場停
    for bad_how in ("", "第一行\n第二行", "<<<<<<< HEAD", "a\n>>>>>>> batch/48"):
        try:
            format_conflict_resolved([48, 47], {}, ["a.py"], bad_how)
        except SystemExit:
            pass
        else:
            raise AssertionError(f"expected SystemExit for how={bad_how!r}")

    # 解不掉:誰跟誰撞在哪個檔案 + 已合的留主線 + 未合的 lane 原地留著
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
    # §7a 查不出另一張(0 候選)-> 停下那句照實講,不猜票號
    nobody = format_conflict_stopped([48], {48: "點頭"}, ["a.py"], [47], [48])
    assert nobody.splitlines()[0] == (
        "撞車停下:#48 點頭 跟主線上既有的內容撞在 a.py,自己解不掉 — "
        "這批合併停在這裡,等你決定。"), nobody
    assert "#47" not in nobody.splitlines()[0], nobody

    assert conflict_lines_issue(text) is None, conflict_lines_issue(text)
    for original, label in (
        ("`/resolving-merge-conflicts`", "§7b 呼叫原件解"),
        ("worktree 與 branch 都留著", "§7c 未合的 lane 留著"),
        ("git merge-base", "§7a 認票問的是「誰動過這個檔案」"),
        ('merged="', "§7a 候選母體是已合名單,不是所有 batch/* branch"),
        ("--name-status -M", "§7a rename 的 pre-image 也要查"),
        ("git branch --list 'batch/*' --contains", "§7a 多候選時的 blame 換算"),
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

    # 連正在合的那張都沒給 -> 子行程也要當場停,不要靜靜貼一句半殘的紀錄上票
    child = subprocess.run(
        [sys.executable, __file__],
        input=json.dumps({"mode": "conflict-resolved", "numbers": [],
                          "files": ["a.py"], "how": "x"}).encode(),
        capture_output=True)
    assert child.returncode != 0 and not child.stdout.strip(), child.stdout

    # ---- #108 分級:切票時標快/慢,整批給 client 點頭 ------------------------
    # 三條規則,優先序就是這個順序
    assert classify_one([]) == (GRADE_FAST, "沒有覆蓋驗收項,不會有你看得到的行為")
    assert classify_one(["1. 登入頁", "2. 導向"]) == (GRADE_SLOW, "覆蓋 2 條驗收項")
    # 硬規則蓋過覆蓋驗收項:沒有可看的行為也照樣慢(驗收清單第 4 條)
    assert classify_one([], judgement=True) == (
        GRADE_SLOW, "動到判斷邏輯或資料寫入,硬規則一律慢")
    assert classify_one(["1. 登入頁"], judgement=True)[0] == GRADE_SLOW

    # 「無 — 由後續票…」是「沒有覆蓋驗收項」的寫法,不是一條驗收項 —— 整段原封不動
    # 餵進來也要判快,不然快車道等於沒有
    for sentinel in ("無 — 由後續票的驗收項間接驗證",
                     "無 —— 由後續票的驗收項間接驗證",
                     "  無 - 由後續票的驗收項間接驗證  "):
        assert classify_one([sentinel])[0] == GRADE_FAST, sentinel
    # 「無」開頭但真的是一條驗收項的不誤殺(沒有破折號)
    assert classify_one(["無障礙:鍵盤走得完整個表單"])[0] == GRADE_SLOW

    # client 當場改 -> 照他改的,而且理由講明是他改的
    assert classify_one([], override=GRADE_SLOW) == (GRADE_SLOW, "你當場改成「慢」")
    assert classify_one(["1. 登入頁"], override=GRADE_FAST) == (
        GRADE_FAST, "你當場改成「快」")
    # 硬規則連 client 都蓋不過 —— 但要當場停,不是靜靜忽略(靜靜忽略的畫面跟改成功一樣)
    try:
        classify_one([], judgement=True, override=GRADE_FAST)
    except SystemExit as e:
        assert "硬規則" in str(e), e
        # #120:訊息本身不准把繞道寫出來。原本那版寫「要改請先改 judgement 旗標」
        # —— agent 被 client 頂著就照字面把 true 改成 false 重跑,一路綠,而硬規則
        # 是這條線唯一的防護。訊息只准指向真的那條路:回去改票的內容。
        assert "回去改票的內容" in str(e), e
        # 宣告過的天花板:只認「旗標」與「judgement」這兩個字面。同義改寫
        # (「把 true 改成 false」之類)擋不住 —— 方向是 fail-closed,不是全稱。
        assert "旗標" not in str(e), e
        assert "judgement" not in str(e), e
    else:
        raise AssertionError("hard rule silently overridden")
    # 硬規則票改成慢是同一個結果,不用停
    assert classify_one([], judgement=True, override=GRADE_SLOW)[0] == GRADE_SLOW
    # override 打錯字 -> 當場停,不靜靜照原判寫進票。硬規則那條路也一樣要停:
    # 它的結果剛好也是慢,吃掉之後的畫面跟「client 根本沒改」一模一樣。
    for bad in ("fast", "快車道", ""):
        for judgement in (False, True):
            try:
                classify_one([], judgement=judgement, override=bad)
            except SystemExit as e:
                assert "override" in str(e), e
            else:
                raise AssertionError(f"bad override swallowed: {bad!r} "
                                     f"(judgement={judgement})")

    # 整批保序,而且純函式
    rows = classify_tickets([
        {"number": 47, "coverage": ["1. 分級", "4. 硬規則"]},
        {"number": 48, "coverage": []},
        {"number": 49, "coverage": [], "judgement": True},
    ])
    assert rows == [(47, GRADE_SLOW, "覆蓋 2 條驗收項"),
                    (48, GRADE_FAST, "沒有覆蓋驗收項,不會有你看得到的行為"),
                    (49, GRADE_SLOW, "動到判斷邏輯或資料寫入,硬規則一律慢")], rows

    # 印給 client 的那份清單 + 逐張要貼進票的那幾行,是同一份判斷排出來的
    listed = format_classify(rows, {47: "分級", 48: "骨架", 49: "算票"})
    assert listed.splitlines() == [
        "分級(3 張)— 標「慢」的會演給你看,標「快」的不會:",
        "  慢  #47 分級 — 覆蓋 2 條驗收項",
        "  快  #48 骨架 — 沒有覆蓋驗收項,不會有你看得到的行為",
        "  慢  #49 算票 — 動到判斷邏輯或資料寫入,硬規則一律慢",
        "",
        "點頭之後,這幾行逐張貼進票 body 的「覆蓋驗收項」段下方:",
        "  #47  分級:慢 — 覆蓋 2 條驗收項",
        "  #48  分級:快 — 沒有覆蓋驗收項,不會有你看得到的行為",
        "  #49  分級:慢 — 動到判斷邏輯或資料寫入,硬規則一律慢",
    ], listed
    # 沒有 title 也印得出來;空的一批兩段都印得出「(無)」
    assert "  快  #48 — 沒有覆蓋驗收項" in format_classify(rows[1:2], {})
    assert format_classify([], {}).count("  (無)") == 2, format_classify([], {})
    # 寫進票的那一行格式固定 —— 守門(scripts/validate.py)咬的就是這個形狀
    assert format_grade_line(GRADE_FAST, "沒有覆蓋驗收項") == "分級:快 — 沒有覆蓋驗收項"

    # #108:分級清單同樣全是中文、同樣印在 cp950 的主控台上 —— 自己走一次
    payload = {"mode": "classify",
               "tickets": [{"number": 47, "coverage": ["登入頁 → 🔑"]},
                           {"number": 48, "coverage": []}],
               "titles": {"47": "登入頁 → 🔑", "48": "骨架"}}
    child = subprocess.run(
        [sys.executable, __file__],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        env=dict(os.environ, PYTHONIOENCODING="cp950"))
    assert child.returncode == 0, child.stderr.decode("utf-8", "replace")
    assert (child.stdout.decode("utf-8").splitlines()
            == format_classify(classify_tickets(payload["tickets"]),
                               {47: "登入頁 → 🔑", 48: "骨架"}).splitlines())

    # 呼叫端是 slice-tickets,不是這支 skill 自己 —— 對著那支出貨檔咬。裝單一
    # skill 的機器上它根本不在,那時候這一段沒有母體可比,跳過(宣告過的天花板)。
    sibling = Path(__file__).resolve().parent.parent / "slice-tickets" / "SKILL.md"
    if sibling.is_file():
        slicing = sibling.read_text(encoding="utf-8")
        assert classify_lines_issue(slicing) is None, classify_lines_issue(slicing)
        for pattern, _ in CLASSIFY_LINES:
            m = pattern.search(slicing)
            assert m, pattern.pattern
            assert classify_lines_issue(slicing.replace(m.group(0), "")), m.group(0)

        # 上面那個迴圈只走 CLASSIFY_LINES 現在有的項:整項被刪掉,pin 跟著它一起
        # 消失,迴圈照樣全綠 —— 守門自己少一條的那面沒有人在量(#120)。所以這份
        # 清單是第二份母體,用句子自己的字面再問一次:出貨檔裡有沒有這句、拿掉
        # 之後守門會不會紅。兩份對不上就紅,不靠下一個人記得同步。
        #
        # 宣告過的天花板,三條(#120 QA 逐項實測出來的,別把它讀成更強的保證):
        #   1. 擋的是**半套編輯** —— 只刪 CLASSIFY_LINES 那一項、或只刪這裡這一句,
        #      set 對不上就紅。兩份加散文一起刪(同一支檔的三個位置)照樣全綠。
        #   2. 擋的是**刪除**,不擋**增補** —— 原句原封留著、後面再補一句相反的話
        #      (「堅持的話把 judgement 改成 false 就好」),兩支守門都不會紅。
        #   3. 只蓋 CLASSIFY_LINES。`FAIL_LANE_LINES` 三條一條 drop-coverage 都沒有,
        #      刻意不在這張票裡改;`CLIENT_LINES` 五條各自有具名 assert,本來就有。
        pinned = ("這批的快慢分級,有要改的嗎?",
                  "照你說的改,改完的才是寫進票裡的那個",
                  "`batch.py` 不在 → 這批整批判慢車道",
                  "判錯必然會發生",
                  "不要自己去改 `judgement` 旗標讓它過",
                  "接得住的是**有驗收項**的那半")
        # CLASSIFY_LINES 每一條都是 re.escape 的字面,所以對帳是機械可導的
        assert ({p.pattern for p, _ in CLASSIFY_LINES}
                == {re.escape(s) for s in pinned}), CLASSIFY_LINES
        for sentence in pinned:
            assert sentence in slicing, sentence
            assert classify_lines_issue(slicing.replace(sentence, "")), sentence

        assert classify_command_issue(slicing) is None, classify_command_issue(slicing)
        # 改壞:那段不再把 JSON 餵進 batch.py
        for original in ('"mode": "classify"', "batch.py <<'JSON'"):
            assert original in slicing, original
            got = classify_command_issue(slicing.replace(original, "nope"))
            assert got and "classify" in got, original
        # 繞過:那段留著,另外多一段自己 inline 印
        got = classify_command_issue(slicing + fence("python3 -c 'print(1)'"))
        assert got and "python -c" in got, got
        # 文件示範的那一行分級行,跟這支檔印出來的是同一個形狀
        assert format_grade_line(GRADE_SLOW, "覆蓋 2 條驗收項") in slicing, sibling

    print("OK batch self-check green")


if __name__ == "__main__":
    # #58 — both ends of the pipe are 中文 and a Windows console is cp950 on
    # both. See AGENTS.md 「會被跑到的 python 檔要釘 UTF-8」.
    sys.stdout.reconfigure(encoding="utf-8")
    # stderr 同一條路:#54 之後「不猜、當場停」的訊息全是中文,而 SystemExit 的
    # 訊息印在 stderr。沒釘的話 client 看到的是一串問號 — 停得對、看不懂,等於
    # 沒停(QA #54 步驟 3c 抓到的就是這個)。
    sys.stderr.reconfigure(encoding="utf-8")
    if "--self-check" in sys.argv:
        self_check()
        sys.exit(0)
    # after the self-check exit: with stdin closed `sys.stdin` is None, and the
    # checks must still run in a harness that hands us no stdin at all
    sys.stdin.reconfigure(encoding="utf-8")
    main()
