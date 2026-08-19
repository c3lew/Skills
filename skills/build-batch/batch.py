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


MODES = ("start", "done", "merged", "summary")


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
