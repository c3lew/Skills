"""#65 同型全掃 — `__main__` block 可以被包在哪些東西底下。

#65 的病是「找 `__main__` 只掃 `tree.body`」,所以一條 fail 不是一條 fail:
Python 裡任何能包住一個 statement 的 block(try / if / with / for / while /
def / class ...)都是同一個形狀 —— 包一層,守門就看不見那個檔,一支裸 print
的 script 無聲過關。這支把母體一次列完:每個包法 × 兩個方向(裸 print 要
判紅、有 pin 不得誤紅)。

用法:
    python scripts/qa/65-nesting-sweep.py <repo>            # 包法全表
    python scripts/qa/65-nesting-sweep.py <repo> --decoy      # 一個檔有兩個 __main__
    python scripts/qa/65-nesting-sweep.py <repo> --test-form  # __main__ 判斷式的等價寫法
    python scripts/qa/65-nesting-sweep.py <repo> --filenames  # 檔名過濾誤傷 __main__.py
    ... --old                                               # 對照組:#65 修之前那版守門(3d402e9^)
"""
import subprocess
import sys
import tempfile
from textwrap import indent
from pathlib import Path

PIN = 'sys.stdout.reconfigure(encoding="utf-8")'
RUNNABLE = 'if __name__ == "__main__":\n    '
NAKED = RUNNABLE + 'print("要開的票")\n'
PINNED = RUNNABLE + PIN + '\n    print("要開的票")\n'

# 包住 __main__ 的每一種 block。每個 entry 是「由外往內」的 template list,
# 空 list = 沒包(對照組)。template 的 {body} 會塞進縮排一層的內層。
TRY = "try:\n{body}except Exception:\n    pass\n"
WRAPPERS = [
    ("top-level(對照組,沒包)", []),
    ("try / except", [TRY]),
    ("try / finally", ["try:\n{body}finally:\n    pass\n"]),
    ("if True", ["if True:\n{body}"]),
    ("if / else 的 else 半邊", ["if False:\n    pass\nelse:\n{body}"]),
    ("with", ["with open(__file__) as f:\n{body}"]),
    ("for", ["for _ in range(1):\n{body}"]),
    ("while", ["while True:\n{body}    break\n"]),
    ("包兩層(try 裡再一個 if True)", [TRY, "if True:\n{body}"]),
    ("def 裡(import 時不會跑,但守門往嚴的方向偏)", ["def main():\n{body}"]),
    ("class body 裡", ["class C:\n{body}"]),
]


def wrap(templates, body):
    """由內往外套:最內層先縮排一層塞進去,再一層層往外包。"""
    for tpl in reversed(templates):
        body = tpl.format(body=indent(body, "    "))
    return body


def cases():
    out = []
    for name, templates in WRAPPERS:
        out.append((f"{name} — 裸 print", "import sys\n" + wrap(templates, NAKED), "RED"))
        out.append((f"{name} — 有 pin(不得誤紅)",
                    "import sys\n" + wrap(templates, PINNED), "GREEN"))
    return out


# 一個檔裡有兩個 `__main__`:守門用 next() 取第一個找到的。ast.walk 是 BFS,
# 先掃淺的,所以真的那個在 top-level 時永遠贏;一樣深時比檔案順序。
DECOY = [
    ("真的在 top-level,誘餌(有 pin)在 def 裡 -> 該判紅",
     "import sys\ndef _dead():\n" + indent(PINNED, "    ") + "\n\n" + NAKED, "RED"),
    ("真的包在 try 裡,誘餌(有 pin)在後面的 def 裡 -> 該判紅",
     "import sys\n" + wrap([TRY], NAKED)
     + "\n\ndef _dead():\n" + indent(PINNED, "    "), "RED"),
    ("誘餌(有 pin)在前面的 def 裡,真的包在後面的 try 裡 -> 該判紅",
     "import sys\ndef _dead():\n" + indent(PINNED, "    ")
     + "\n\n" + wrap([TRY], NAKED), "RED"),
    ("兩個 top-level __main__:裸 print 在前 -> 該判紅",
     "import sys\n" + NAKED + PINNED, "RED"),
    ("兩個 top-level __main__:有 pin 的在前,裸 print 在後 -> 該判紅",
     "import sys\n" + PINNED + NAKED, "RED"),
]


# judge 追問出來的第三型:守門認的是 `ast.unparse(n.test) == MAIN_TEST` 這個
# 字面。包法掃完了,但「__main__ 這個判斷式本身換個寫法」是同一個形狀 ——
# 守門一樣找不到那個 node,一樣整檔無聲略過。母體 = 等價寫法的每一種。
TEST_FORM = [
    ("正規寫法(對照組)", NAKED, "RED"),
    ("左右對調 `\"__main__\" == __name__`",
     'if "__main__" == __name__:\n    print("要開的票")\n', "RED"),
    ("用 in `__name__ in (\"__main__\",)`",
     'if __name__ in ("__main__",):\n    print("要開的票")\n', "RED"),
    ("先存變數再 if",
     'is_main = __name__ == "__main__"\nif is_main:\n    print("要開的票")\n', "RED"),
    ("否定 + else",
     'if __name__ != "__main__":\n    pass\nelse:\n    print("要開的票")\n', "RED"),
    ("單引號 `__main__`",
     "if __name__ == '__main__':\n    print(\"要開的票\")\n", "RED"),
]

# judge 追問出來的第四型:檔名過濾。`any(part.startswith((\".\", \"__\")))` 是
# 為了擋 __pycache__,但 py.parts 含檔名 —— package 的 entry point
# `__main__.py`(最典型的 runnable script)也被同一條規則整個跳過。
FILENAMES = [
    ("scripts/run.py(對照組)", "scripts/run.py", "RED"),
    ("scripts/__main__.py(package entry point)", "scripts/__main__.py", "RED"),
    ("scripts/__init__.py", "scripts/__init__.py", "RED"),
    ("scripts/__pycache__/x.py(本來就該跳過)", "scripts/__pycache__/x.py", "GREEN"),
    ("scripts/.hidden/x.py(本來就該跳過)", "scripts/.hidden/x.py", "GREEN"),
]


def run_filenames(repo, old=False):
    V = guard_module(repo, old)
    rows, bad = [], 0
    for name, rel, want in FILENAMES:
        tmp = Path(tempfile.mkdtemp())
        f = tmp / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("import sys\n" + NAKED, encoding="utf-8")
        got = "RED" if V.stream_encoding_issues(tmp) else "GREEN"
        ok = got == want
        bad += not ok
        rows.append((name, want, got, "ok" if ok else "MISMATCH"))
    width = max(len(r[0]) for r in rows)
    for name, want, got, verdict in rows:
        print(f"{name.ljust(width)}  期望 {want:<5}  實際 {got:<5}  {verdict}")
    print(f"\n母體 {len(rows)},不合 {bad}")
    return bad


def guard_module(repo, old):
    """`stream_encoding_issues` 的來源:現況,或 #65 修之前那版(對照組)。"""
    if not old:
        sys.path.insert(0, str(Path(repo) / "scripts"))
        import validate

        return validate
    src = subprocess.run(["git", "-C", str(repo), "show", "3d402e9^:scripts/validate.py"],
                         capture_output=True, check=True).stdout
    box = Path(tempfile.mkdtemp())
    (box / "validate_pre65.py").write_bytes(src)
    sys.path.insert(0, str(box))
    import validate_pre65

    return validate_pre65


def run(repo, rows_in, old=False):
    V = guard_module(repo, old)
    tmp = Path(tempfile.mkdtemp())
    probe = tmp / "probe.py"
    rows, bad = [], 0
    for name, src, want in rows_in:
        probe.write_text(src, encoding="utf-8")
        got = "RED" if V.stream_encoding_issues(tmp) else "GREEN"
        ok = got == want
        bad += not ok
        rows.append((name, want, got, "ok" if ok else "MISMATCH"))
    width = max(len(r[0]) for r in rows)
    for name, want, got, verdict in rows:
        print(f"{name.ljust(width)}  期望 {want:<5}  實際 {got:<5}  {verdict}")
    print(f"\n母體 {len(rows)},不合 {bad}")
    return bad


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    old = "--old" in sys.argv
    if "--filenames" in sys.argv:
        sys.exit(1 if run_filenames(sys.argv[1], old) else 0)
    rows = cases()
    if "--decoy" in sys.argv:
        rows = DECOY
    elif "--test-form" in sys.argv:
        rows = TEST_FORM
    sys.exit(1 if run(sys.argv[1], rows, old) else 0)
