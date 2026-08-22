"""#108 QA 的第二把尺 —— 刻意寫寬,不套受測物的規則。

受測物(`validate.py` 的 `grade_line_issues`、`batch.py` 的 `classify_one`)自己
就是判準。只跑它、看它綠,只證明它同意自己。這支從頭寫一遍「repo 裡哪裡有分級行的
形狀、哪裡宣稱要呼叫 classify」,而且刻意寫**寬**:

- 受檢範圍:`skills/**/*.md` 全收 —— 不只 `SKILL.md`,`references/` 底下的 `.md`
  也收(受測物只讀每個 skill 的 `SKILL.md` 一份)。
- 分級行:認任何一行裡出現「分級」後面 0–2 個字內接一個冒號類字元
  (`:` `:` `︰` `-` `—` 都算),行首縮排不限、行首不必是「分級」——
  受測物只認 `^ {0,3}分級[:︰:]`。列表符號、粗體、表格欄位裡的也照樣撈。
- classify 宣告:認任何一行提到 `classify`(不分大小寫)、`"mode"` 附近有
  classify、或中文的「分級清單 / 判快慢 / 快慢分級」—— 受測物只認
  字面 `"mode": "classify"` 這一串。
- 「好的分級行」我自己另外定一次寬鬆版:半形冒號 + 快/慢 + 中間有個破折號 +
  破折號後面有非空白字。跟受測物的 regex 不共用一行程式碼。

不 import `validate.py` / `batch.py` 的任何判斷。跟受測物對照的那一面,是把
`python scripts/validate.py` 當黑箱跑起來、讀它印出來的 `FAIL` 文字 —— 讀輸出不是
套規則。

寬的那面一定會撈到受測物放行的東西 —— 那是設計,不是 bug。每一筆都列在「差額」
一節等人判讀,判成誤報也要寫進 QA 報告。

用法:
    python scripts/qa/108-wide.py .
    python scripts/qa/108-wide.py <某個母體目錄>
"""
import pathlib
import re
import subprocess
import sys

# 寬:「分級」後面 0-2 個字內接冒號類字元。冒號類刻意連 - 和 — 都收
GRADE_WIDE = re.compile(r"分級.{0,2}?[:：︰—-]")
# 寬:我自己另外定的「好的形狀」,不引用受測物的 regex
GOOD_WIDE = re.compile(r"^\s*分級:\s*(快|慢)\s*—\s*\S")
# 寬:任何宣稱要走 classify 的說法
CLASSIFY_WIDE = re.compile(
    r"classify|分級清單|快慢分級|判快慢", re.I)
FAIL_LINE = re.compile(r"^FAIL (skills/[^/]+)/SKILL\.md: (.*)$")


def scan(repo):
    """每個 skills/**/*.md 一列 —— 不過濾,references/ 也收。"""
    rows = []
    root = pathlib.Path(repo) / "skills"
    for md in sorted(root.rglob("*.md")):
        rel = md.relative_to(repo).as_posix()
        try:
            text = md.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            rows.append(dict(file=rel, unreadable=str(exc), grades=[], calls=[]))
            continue
        grades, calls = [], []
        for i, line in enumerate(text.splitlines(), 1):
            if GRADE_WIDE.search(line):
                grades.append((i, line.rstrip(), bool(GOOD_WIDE.match(line))))
            if CLASSIFY_WIDE.search(line):
                calls.append((i, line.strip()))
        rows.append(dict(file=rel, unreadable=None, grades=grades, calls=calls))
    return rows


def guard_verdicts(repo):
    """把 validate.py 當黑箱跑,讀它印的 FAIL 文字 —— {skill 路徑: [訊息]}。"""
    p = subprocess.run([sys.executable, "scripts/validate.py"],
                       cwd=repo, capture_output=True, text=True, encoding="utf-8")
    out = {}
    for line in (p.stdout or "").splitlines():
        m = FAIL_LINE.match(line)
        if m:
            out.setdefault(m.group(1), []).append(m.group(2))
    return out, p.returncode, (p.stdout or "").strip()


def main(repo):
    repo = str(pathlib.Path(repo).resolve())
    rows = scan(repo)
    verds, rc, raw = guard_verdicts(repo)

    print(f"母體:{repo}/skills/**/*.md,共 {len(rows)} 份")
    print(f"受測物黑箱:python scripts/validate.py → exit {rc}")
    print(f"  它印的:{raw.splitlines()[-1] if raw else '(沒輸出)'}")

    print("\n==== 寬尺撈到的「分級:…」形狀的行 ====")
    grade_files = [r for r in rows if r["grades"]]
    total = sum(len(r["grades"]) for r in rows)
    print(f"{len(grade_files)} 份檔、{total} 行")
    for r in grade_files:
        for ln, txt, good in r["grades"]:
            flag = "形狀 OK " if good else "形狀可疑"
            print(f"  [{flag}] {r['file']}:{ln}: {txt}")

    print("\n==== 寬尺撈到的「宣稱要呼叫 classify」的行 ====")
    call_files = [r for r in rows if r["calls"]]
    print(f"{len(call_files)} 份檔、{sum(len(r['calls']) for r in rows)} 行")
    for r in call_files:
        for ln, txt in r["calls"]:
            print(f"  {r['file']}:{ln}: {txt}")

    print("\n==== 寬尺自己的判定(不看受測物)====")
    wide_flags = []
    for r in rows:
        if r["unreadable"]:
            wide_flags.append((r["file"], f"讀不進來:{r['unreadable']}"))
            continue
        for ln, txt, good in r["grades"]:
            if not good:
                wide_flags.append((r["file"], f":{ln} 分級行形狀可疑 — {txt}"))
        if r["calls"] and not r["grades"]:
            wide_flags.append(
                (r["file"], "提到 classify 卻整份沒有任何分級行的形狀"))
    if wide_flags:
        for f, why in wide_flags:
            print(f"  [寬] {f} {why}")
    else:
        print("  (寬尺一條都沒撈到)")

    print("\n==== 差額:寬尺撈到、受測物放行的(逐筆判讀)====")
    guard_hits = {(k, m) for k, ms in verds.items() for m in ms}
    print(f"受測物現在對這份母體的 FAIL:{len(guard_hits)} 條")
    for k, m in sorted(guard_hits):
        print(f"  [守門] {k}/SKILL.md: {m}")
    extra = []
    for f, why in wide_flags:
        skill = "/".join(f.split("/")[:2])
        if not verds.get(skill):
            extra.append((f, why))
    if extra:
        print(f"\n寬尺多撈 {len(extra)} 筆 —— 每一筆都要在報告裡判讀:")
        for f, why in extra:
            print(f"  [多撈] {f} {why}")
    else:
        print("\n寬尺多撈 0 筆 —— 兩把尺對這份母體的結論一致")

    print("\n==== 差額:受測物咬到、寬尺沒撈到的 ====")
    wide_files = {f for f, _ in wide_flags}
    missed = [(k, m) for k, ms in verds.items() for m in ms
              if not any(w.startswith(k + "/") for w in wide_files)]
    if missed:
        for k, m in missed:
            print(f"  [寬尺漏]{k}/SKILL.md: {m}")
    else:
        print("  (無)")
    # 這支的輸出不是綠/紅,是一份等人看的清單 —— 永遠 exit 0
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
