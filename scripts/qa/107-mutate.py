"""#107 的 mutation 台 —— `judge_ordering_issues` 的每個 knob 改壞,`--self-check` 要轉紅。

守的那件事是:`/qa` 的並行池剛好三線(regression / walkthrough / code-review),獨立 judge
不在池裡。judge 提早開會拿到空的 a11y snapshot,然後把每一條驗收項都判 pass —— 那份
報告跟真的全過長得一模一樣(沒有紅字、沒有例外、每條 pass),讀報告的人分不出來。
所以這條判準要有證據住在預設會跑的地方,而不是靠下一個 agent 讀散文自己推。

每個 knob 對應 `judge_ordering_issues` 裡「拿掉就會漏掉一種形狀」的那一行。

用法(與 `97-mutate.py` 同形):
    python scripts/qa/107-mutate.py --run          # 整張表跑完,每格報 exit code
    python scripts/qa/107-mutate.py --list
    python scripts/qa/107-mutate.py <repo 副本> <knob 名稱>

`--run` 不碰 repo 本體:完整 repo 複製到拋棄式暫存目錄,mutation 全跑在副本上。
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]

KNOBS = {
    # 母體整個關掉 —— 跑 judge 的 skill 一支都不用受檢
    "trigger_off": (
        "    if not JUDGE_RUNNER_RE.search(text):",
        "    if True:"),
    # 母體放寬回「光提到就上鉤」—— #57 已經記取過的假陽性形狀:散文裡提一句 judge
    # 的 skill 一支 judge 都沒跑,卻被要求宣告並行池
    "trigger_by_mention": (
        "    if not JUDGE_RUNNER_RE.search(text):",
        '    if "judge" not in text:'),
    # 並行池那一段不見了也放行 —— 三線同時開這件事沒寫下來就沒人會做
    "pool_section_optional": (
        "    if not declared:\n        issues.append(",
        "    if False:\n        issues.append("),
    # lane 表從「剛好這三支」放寬成「至少有這三支」—— 多插一支 judge lane 直接綠,
    # 這正是 #107 指名的那個失敗形狀
    "extra_lane_ok": (
        "    elif sorted(lanes) != sorted(POOL_LANES):",
        "    elif not set(POOL_LANES) <= set(lanes):"),
    # 反過來:少一支 lane 也放行 —— 並行沒做滿,報告卻照樣報綠
    "missing_lane_ok": (
        "    elif sorted(lanes) != sorted(POOL_LANES):",
        "    elif set(lanes) - set(POOL_LANES):"),
    # #112 A1:lane 名字退回「只認粗體第一欄」—— markdown 不要求粗體,散文也沒寫過
    # 那條規矩,所以插一列不粗體的 judge lane 就整個繞過去,守門一聲不吭
    "lane_cell_requires_bold": (
        'LANE_FIRST_CELL_RE = re.compile(r"^\\|([^|\\n]*)\\|", re.M)',
        'LANE_FIRST_CELL_RE = re.compile(r"^\\|\\s*\\*\\*([^*|]+)\\*\\*\\s*\\|", re.M)'),
    # #112 A4:lane 名字改成「這一段裡任何粗體」—— 散文的強調字與資源分配表都被當成
    # lane,判準失去錨點(池的宣告是表頭寫 `lane` 的那張表,不是排版)
    "lane_cell_any_bold": (
        "            lanes += [c.strip().strip(\"*\").strip()\n"
        "                      for c in LANE_FIRST_CELL_RE.findall(table.group(1))]",
        '            lanes += re.findall(r"\\*\\*([^*|]+)\\*\\*", body)'),
    # #112 review:表頭 `lane` 那個字放掉 —— 並行池那一段裡任何一張表都被讀成
    # lane 表,資源分配表的第一欄就變成 lane(A4 的假陽性回來)
    "pool_table_any_header": (
        'r"^\\|[ \\t]*lane[ \\t]*\\|',
        'r"^\\|[^\\n]*\\|'),
    # #112 A3:池的宣告退回「標題有沒有那三個字」—— 別段的標題也含「並行池」,
    # 池整段消失時會走進「lanes are []」而不是「整段不見」,訊息指錯地方
    "pool_declared_by_heading": (
        "        for table in LANE_TABLE_RE.finditer(body):",
        "        declared = True\n        for table in LANE_TABLE_RE.finditer(body):"),
    # 排序約束整條不看 —— 「judge 排在 walkthrough 之後」可以從文件裡消失
    "ordering_never_checked": (
        "    if not any(any(unnegated(JUDGE_AFTER_RE, span))\n"
        "               for span in JUDGE_SPAN_RE.findall(prose)):",
        "    if False:"),
    # 退回「關鍵詞在不在」——「不用等 walkthrough 之後,直接進並行池」照樣綠(#64 的
    # 繞過方向:關鍵詞留著,動作反過來寫)
    "ordering_by_keyword": (
        "    if not any(any(unnegated(JUDGE_AFTER_RE, span))\n"
        "               for span in JUDGE_SPAN_RE.findall(prose)):",
        "    if not JUDGE_AFTER_RE.search(prose):"),
    # #112 A2:排序約束改掃整份文件 —— §3 標題自己就同時含 judge 與「walkthrough…之後」,
    # 正文那句 load-bearing 的約束整句刪掉,單靠標題就把檢查餵飽
    "ordering_scans_headings": (
        "    prose = prose_lines(text)",
        "    prose = text"),
}


def apply(repo, knob):
    target = pathlib.Path(repo) / "scripts" / "validate.py"
    src = target.read_text(encoding="utf-8")
    old, new = KNOBS[knob]
    assert old in src, f"mutation 目標不在 — 判準被改過了:{knob}"
    target.write_text(src.replace(old, new, 1), encoding="utf-8")


def self_check(repo):
    repo = pathlib.Path(repo)
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "validate.py"), "--self-check"],
        cwd=repo, capture_output=True)


def run_table():
    """每個 knob 套上去跑 `--self-check`,回傳 (knob, exit code)。非 0 才是要的。"""
    out = []
    with tempfile.TemporaryDirectory() as td:
        copy = pathlib.Path(td) / "repo"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        control = self_check(copy)
        if control.returncode:
            why = (control.stderr or control.stdout).decode("utf-8", "replace").strip()
            raise RuntimeError("控制組未套 knob 就已經紅;儀器壞了,下面的 mutation 表不執行"
                               + (f"\n{why}" if why else ""))
        pristine = (copy / "scripts" / "validate.py").read_bytes()
        for knob in sorted(KNOBS):
            (copy / "scripts" / "validate.py").write_bytes(pristine)
            apply(copy, knob)
            r = self_check(copy)
            out.append((knob, r.returncode))
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    if "--list" in sys.argv:
        print("\n".join(sorted(KNOBS)))
        sys.exit(0)
    if "--run" in sys.argv:
        try:
            rows = run_table()
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            sys.exit(1)
        for knob, code in rows:
            print(f"{'咬住' if code else '沒咬住'}  {knob:<22} self-check exit={code}")
        missed = [k for k, c in rows if c == 0]
        print(f"\n{len(rows) - len(missed)}/{len(rows)} 個 knob 被 self-check 咬住")
        if missed:
            print("沒咬住:" + ", ".join(missed))
        sys.exit(1 if missed else 0)
    apply(sys.argv[1], sys.argv[2])
    print("mutation 已套用:", sys.argv[2])
