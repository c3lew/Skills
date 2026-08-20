"""#97 QA 的第二把尺 —— 刻意寫寬,不套受測物的規則。

受測物(`validate.py` 的 `stream_encoding_issues`)自己就是判準,只跑它、看它綠,
只證明它同意自己。這支從頭寫一遍「這個檔有沒有 pin」,而且刻意寫**寬**:

- 純文字 + 縮排,不用 AST,也不 import 受測物的任何 helper。
- `__main__` 認任何 `if ... __main__ ...:` 的行,不管寫法(受測物只認正規寫法)。
- 「碰 stdin」看原始碼字串裡有沒有 `sys.stdin`(受測物看 AST 的 Attribute)。

寬的那面會撈到受測物放行的東西 —— 那是設計,不是 bug。每一筆都列在「差額」
一節裡等人判讀,判成誤報也要寫進 QA 報告。

用法:
    python scripts/qa/97-wide.py .
"""
import pathlib
import re
import sys

MAIN_IF = re.compile(r"^(\s*)if\s+.*__main__.*:\s*$")
PIN = re.compile(r"^(\s*)sys\.(stdout|stdin)\.reconfigure\s*\(")
STDIN_TXT = re.compile(r"sys\.stdin")


def block_end(lines, start, indent):
    """`lines[start]` 那個 block 的結束行 —— 回到 <= indent 縮排的第一個非空行。"""
    for j in range(start + 1, len(lines)):
        s = lines[j]
        if s.strip() and len(s) - len(s.lstrip()) <= len(indent):
            return j
    return len(lines)


def scan(repo):
    """每個提到 `__main__` 的 .py 一列:main 行、pin 行 + 它落在哪一層。"""
    rows = []
    for py in sorted(pathlib.Path(repo).rglob("*.py")):
        rel = py.relative_to(repo).as_posix()
        if "__pycache__" in rel or rel.startswith("."):
            continue
        lines = py.read_text(encoding="utf-8", errors="replace").splitlines()
        src = "\n".join(lines)
        if "__main__" not in src:
            continue
        mains = [(i, m.group(1)) for i, l in enumerate(lines) if (m := MAIN_IF.match(l))]
        pins = {}
        for i, l in enumerate(lines):
            if not (m := PIN.match(l)):
                continue
            indent, stream = m.group(1), m.group(2)
            loc = "模組層或 function 裡"
            for mi, mind in mains:
                if not (mi < i < block_end(lines, mi, mind) and len(indent) > len(mind)):
                    continue
                body = min((len(x) - len(x.lstrip())
                            for x in lines[mi + 1:block_end(lines, mi, mind)] if x.strip()),
                           default=None)
                loc = f"main@L{mi + 1} 第{'一' if len(indent) == body else '巢狀'}層"
            pins.setdefault(stream, []).append(f"L{i + 1}({loc})")
        rows.append(dict(file=rel, mains=[i + 1 for i, _ in mains],
                         stdout=pins.get("stdout", []), stdin=pins.get("stdin", []),
                         stdin_txt=bool(STDIN_TXT.search(src))))
    return rows


def naive_verdict(row):
    """寬尺自己的判定 —— 只看「第一層有沒有」,不管 AST、不管寫法。"""
    if not row["mains"]:
        return "綠"
    ok_out = any("第一層" in p for p in row["stdout"])
    ok_in = not row["stdin_txt"] or any("第一層" in p for p in row["stdin"])
    return "綠" if ok_out and ok_in else "紅"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    repo = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    rows = scan(repo)
    for r in rows:
        print(r["file"])
        print(f"   main 行:{r['mains'] or '（只在字串裡提到 __main__）'}")
        print(f"   stdout pin:{r['stdout'] or '無'}")
        print(f"   stdin  pin:{r['stdin'] or '無'}（原始碼提到 sys.stdin:{r['stdin_txt']}）")

    sys.path.insert(0, str(repo / "scripts"))
    import validate
    tight = {e.split(":")[0] for e in validate.stream_encoding_issues(repo)}
    print(f"\n共 {len(rows)} 個檔提到 __main__;受測物判紅 {len(tight)} 個\n")
    print("==== 差額(寬尺 vs 受測物)—— 每一筆要人判讀 ====")
    diff = [(r, naive_verdict(r)) for r in rows
            if naive_verdict(r) != ("紅" if r["file"] in tight else "綠")]
    for r, v in diff:
        print(f"  {r['file']}:寬尺判{v},受測物判{'紅' if r['file'] in tight else '綠'}")
    print(f"  差額 {len(diff)} 筆" + ("" if diff else " —— 兩把尺對這份 repo 完全同意"))
