"""#97 QA 的修前對照 —— 同一份母體,舊判準(5e3646c)vs 新判準。

這張票動的是判斷邏輯,只驗「這次要修的那一面」會漏掉另一面:收緊會多擋,而多擋的
那批在修之前是好的。所以母體兩面都寫:**QA 照 #96 驗收原句自己判該綠的 8 格**、
**該紅的 8 格**,外加兩格宣告過的天花板(#66 parse 不動、#68 `__` 開頭檔名),
新舊兩套判準各跑一次,列出差額。

差額全部落在「舊綠 → 新紅」而且每一筆都對得上票面要收的形狀,才算沒有本輪引入的誤紅。
期望值是 QA 讀原句寫的,不是從實作反推的 —— 實作同意它是結論,不是前提。

用法:
    python scripts/qa/97-prevdiff.py          # 母體 18,不合 0 才算過
"""
import importlib.util
import pathlib
import subprocess
import sys
import tempfile

PREV = "5e3646c"  # #97 動判準之前的最後一個 commit
ROOT = pathlib.Path(__file__).resolve().parents[2]
P = 'sys.stdout.reconfigure(encoding="utf-8")'
I = 'sys.stdin.reconfigure(encoding="utf-8")'

# 檔名開頭就是 QA 的期望:g=該綠、r=該紅、c/__=宣告過的天花板(不判)
FIXTURES = {
    "g1_pin_first_level.py": f'import sys\nif __name__ == "__main__":\n    {P}\n    print("要開的票")\n',
    "g2_stdin_both_pinned.py": f'import sys\nif __name__ == "__main__":\n    {P}\n    {I}\n    print(sys.stdin.read())\n',
    "g3_no_main.py": "def f():\n    return 1\n",
    "g4_stdin_only_prose.py": f'import sys\nif __name__ == "__main__":\n    {P}\n    x = "sys.stdin.reconfigure"\n    print(x)\n',
    "g5_reversed_spelling.py": 'import sys\nif "__main__" == __name__:\n    print("要開")\n',
    "g6_main_nested_under_try.py": f'import sys\ntry:\n    if __name__ == "__main__":\n        {P}\n        print("中文")\nexcept Exception:\n    pass\n',
    "g7_two_mains_both_pinned.py": f'import sys\nif __name__ == "__main__":\n    {P}\n    print("一")\nif __name__ == "__main__":\n    {P}\n    print("二")\n',
    "g8_in_tuple_spelling.py": 'import sys\nif __name__ in ("__main__",):\n    print("要開")\n',
    "r1_pin_inside_main_func.py": f'import sys\ndef main():\n    {P}\n    print("中文")\nif __name__ == "__main__":\n    main()\n',
    "r2_pin_module_level.py": f'import sys\n{P}\nif __name__ == "__main__":\n    print("中文")\n',
    "r3_pin_nested_in_if.py": f'import sys\nif __name__ == "__main__":\n    if True:\n        {P}\n    print("中文")\n',
    "r4_buffer_only_no_pin.py": 'import sys\nif __name__ == "__main__":\n    sys.stdout.buffer.write("中文".encode("utf-8"))\n',
    "r5_main_no_print.py": 'import sys\nif __name__ == "__main__":\n    pass\n',
    "r6_stdin_only_stdout_pinned.py": f'import sys\nif __name__ == "__main__":\n    {P}\n    data = sys.stdin.read()\n',
    "r7_two_mains_first_only.py": f'import sys\nif __name__ == "__main__":\n    {P}\n    print("一")\nif __name__ == "__main__":\n    print("二")\n',
    "r8_pin_nested_in_try.py": f'import sys\nif __name__ == "__main__":\n    try:\n        {P}\n    except Exception:\n        pass\n    print("中文")\n',
    # 宣告過的天花板 —— #97 明講沒做,留在 #98
    "c1_syntax_error.py": 'import sys\nif __name__ == "__main__":\n    print("中文"\n',
    "__main__.py": 'import sys\nif __name__ == "__main__":\n    print("中文")\n',
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(tmp):
    pop = tmp / "pop"
    pop.mkdir()
    for name, src in FIXTURES.items():
        (pop / name).write_text(src, encoding="utf-8")
    prev = tmp / "validate_prev.py"
    prev.write_bytes(subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{PREV}:scripts/validate.py"],
        capture_output=True, check=True).stdout)
    new = load("v_new", ROOT / "scripts" / "validate.py")
    old = load("v_old", prev)
    vn = {e.split(":")[0] for e in new.stream_encoding_issues(pop)}
    vo = {e.split(":")[0] for e in old.stream_encoding_issues(pop)}
    bad = []
    print(f"{'fixture':<34}{'QA 期望':<9}{'新':<4}{'舊':<4} 判定")
    for f in sorted(FIXTURES):
        exp = "紅" if f.startswith("r") else ("天花板" if f.startswith(("c", "__")) else "綠")
        n, o = ("紅" if f in vn else "綠"), ("紅" if f in vo else "綠")
        ok = exp == "天花板" or n == exp
        if not ok:
            bad.append(f)
        print(f"{f:<34}{exp:<9}{n:<4}{o:<4} {'OK' if ok else '*** 不合 ***'}"
              f"{'' if n == o else f'  差額 舊{o}→新{n}'}")
    print(f"\n母體 {len(FIXTURES)},不合 {len(bad)}" + (f":{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        sys.exit(run(pathlib.Path(td)))
