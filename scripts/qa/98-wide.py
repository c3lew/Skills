"""#98 QA 的第二把尺 —— 刻意寫寬,不套受測物的規則。

受測物(`validate.py` 的 `is_source` + `stream_encoding_issues`)自己就是判準,只跑它、
看它綠,只證明它同意自己。這支從頭寫一遍「哪些 .py 該受檢、哪些讀不進來」,而且刻意寫**寬**:

- 受檢範圍:`rglob("*.py")` 全收,**一格都不過濾**(受測物擋 `__pycache__` 與 `.` 開頭)。
- `__main__`:純文字 regex 認任何 `if ... __main__ ...:` 的行,不管寫法(受測物只認正規寫法)。
- 「讀不進來」:utf-8 decode 或 `compile()` 任一失敗就算(受測物同一組,但只在受檢範圍內)。
- 不 import 受測物的任何 helper,不用 AST 判 pin —— 純文字 + 縮排。

寬的那面會撈到受測物放行的東西 —— 那是設計,不是 bug。每一筆都列在「差額」一節等人
判讀,判成誤報也要寫進 QA 報告。

這支跟 `97-wide.py` 的差別:97 量的是「pin 在不在第一層」,這支量的是**入口** ——
守門到底看到了哪些檔、哪些檔它連讀都沒讀。#98 收的三個缺口全在這條軸上。

用法:
    python scripts/qa/98-wide.py .
    python scripts/qa/98-wide.py <某個母體目錄>
"""
import pathlib
import re
import sys

MAIN_IF = re.compile(r"^(\s*)if\s+.*__main__.*:\s*$")
PIN = re.compile(r"^(\s*)sys\.(stdout|stdin)\.reconfigure\s*\(")
STDIN_TXT = re.compile(r"sys\.stdin")


def block_end(lines, start, indent):
    for j in range(start + 1, len(lines)):
        s = lines[j]
        if s.strip() and len(s) - len(s.lstrip()) <= len(indent):
            return j
    return len(lines)


def scan(repo):
    """每個 .py 一列 —— 不過濾任何路徑,讀不進來的也留一列。"""
    rows = []
    for py in sorted(pathlib.Path(repo).rglob("*.py")):
        rel = py.relative_to(repo).as_posix()
        raw = py.read_bytes()
        try:
            src = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            rows.append(dict(file=rel, unreadable=f"decode: {exc}", mains=[]))
            continue
        try:
            compile(src, rel, "exec")
        except SyntaxError as exc:
            rows.append(dict(file=rel, unreadable=f"parse: {exc}", mains=[]))
            continue
        lines = src.splitlines()
        mains = [(i, m.group(1)) for i, l in enumerate(lines) if (m := MAIN_IF.match(l))]
        pinned = []          # 每個 main 各自:第一層有沒有 stdout / stdin pin
        for mi, mind in mains:
            end = block_end(lines, mi, mind)
            body = min((len(x) - len(x.lstrip()) for x in lines[mi + 1:end] if x.strip()),
                       default=None)
            got = set()
            for j in range(mi + 1, end):
                if (m := PIN.match(lines[j])) and len(m.group(1)) == body:
                    got.add(m.group(2))
            pinned.append(got)
        rows.append(dict(file=rel, unreadable=None, mains=[i + 1 for i, _ in mains],
                         pinned=pinned, stdin_txt=bool(STDIN_TXT.search(src))))
    return rows


def naive_verdict(row):
    """寬尺自己的判定 —— 讀不進來算紅;每個 main 都要自己有 pin。"""
    if row["unreadable"]:
        return "紅"
    if not row["mains"]:
        return "綠"
    need = {"stdout"} | ({"stdin"} if row["stdin_txt"] else set())
    return "綠" if all(need <= got for got in row["pinned"]) else "紅"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    repo = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    rows = scan(repo)

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    import validate
    tight = {e.split(":")[0] for e in validate.stream_encoding_issues(repo)}
    seen = {r["file"] for r in rows
            if validate.is_source(pathlib.Path(r["file"]))}

    print("==== 寬尺看到的全部 .py ====")
    for r in rows:
        mark = "  " if r["file"] in seen else "跳"      # 「跳」= 受測物根本沒看這個檔
        if r["unreadable"]:
            print(f"{mark} {r['file']}:讀不進來 —— {r['unreadable'][:70]}")
        else:
            print(f"{mark} {r['file']}:main 行 {r['mains'] or '無'};"
                  f"第一層 pin {[sorted(g) for g in r['pinned']] or '—'}"
                  f"(原始碼提到 sys.stdin:{r['stdin_txt']})")

    print(f"\n寬尺母體 {len(rows)} 個 .py;受測物的受檢範圍 {len(seen)} 個"
          f"(差 {len(rows) - len(seen)} 個被過濾掉);受測物判紅 {len(tight)} 個\n")

    print("==== 差額(寬尺 vs 受測物)—— 每一筆要人判讀 ====")
    diff = [(r, naive_verdict(r)) for r in rows
            if naive_verdict(r) != ("紅" if r["file"] in tight else "綠")]
    for r, v in diff:
        why = "受測物過濾掉沒看" if r["file"] not in seen else "同一批檔、判準有差"
        print(f"  {r['file']}:寬尺判{v},受測物判{'紅' if r['file'] in tight else '綠'} —— {why}")
    print(f"  差額 {len(diff)} 筆" + ("" if diff else " —— 兩把尺對這份母體完全同意"))
