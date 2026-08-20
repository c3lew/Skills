"""#98 QA 的修前對照 —— 同一份母體,修前(91b6b98)vs 修後的入口判準。

這張票動的是「守門看不看得到那個檔」,是判斷邏輯,所以只驗「這次要放進來的那一面」
會漏掉另一面:受檢範圍放寬會多檢,多檢出來的那批在修之前是綠的。母體因此兩面都寫 ——
**QA 照 #96/#98 驗收原句自己判該綠的 11 格、該紅的 11 格** —— 修前修後各跑一次,列差額。

差額每一筆都要對得上票面要收的形狀(`__main__.py` 進來受檢、parse 不動判 fail、
cp950 存的 .py 判 fail),才算沒有本輪引入的誤紅。期望值是 QA 讀原句寫的,不是從實作
反推的 —— 實作同意它是結論,不是前提。

外加一節「母體放在 `.` 開頭的目錄底下」:修前的過濾吃的是**絕對路徑**的 parts,repo
只要被 clone 到 `~/.local/…` 這種路徑底下,整條守門就靜靜地全綠。修後改吃相對路徑,
不受影響。這是本輪順手收掉的第四個入口缺口,票面沒列。

用法:
    python scripts/qa/98-prevdiff.py          # 母體 22,不合 0 才算過
"""
import importlib.util
import pathlib
import subprocess
import sys
import tempfile

PREV = "91b6b98"  # #98 動入口判準之前的最後一個 commit
ROOT = pathlib.Path(__file__).resolve().parents[2]
P = 'sys.stdout.reconfigure(encoding="utf-8")'
I = 'sys.stdin.reconfigure(encoding="utf-8")'

# key = 母體裡的相對路徑;開頭 g=該綠、r=該紅。value = (原始碼, 編碼)
FIXTURES = {
    # ---- 該綠的一面 ----
    "g01_pin_first_level.py": (f'import sys\nif __name__ == "__main__":\n    {P}\n    print("要開的票")\n', "utf-8"),
    "g02_stdin_both_pinned.py": (f'import sys\nif __name__ == "__main__":\n    {P}\n    {I}\n    print(sys.stdin.read())\n', "utf-8"),
    "g03_no_main.py": ("def f():\n    return 1\n", "utf-8"),
    "g04_stdin_only_prose.py": (f'import sys\nif __name__ == "__main__":\n    {P}\n    x = "sys.stdin.reconfigure"\n    print(x)\n', "utf-8"),
    "g05_reversed_spelling.py": ('import sys\nif "__main__" == __name__:\n    print("要開")\n', "utf-8"),
    "g06_main_nested_under_try.py": (f'import sys\ntry:\n    if __name__ == "__main__":\n        {P}\n        print("中文")\nexcept Exception:\n    pass\n', "utf-8"),
    "g07_two_mains_both_pinned.py": (f'import sys\nif __name__ == "__main__":\n    {P}\n    print("一")\nif __name__ == "__main__":\n    {P}\n    print("二")\n', "utf-8"),
    "g08_in_tuple_spelling.py": ('import sys\nif __name__ in ("__main__",):\n    print("要開")\n', "utf-8"),
    # #68 的反面:過濾要留下來的東西,還是得擋住
    "__pycache__/g09_cached.py": ('import sys\nif __name__ == "__main__":\n    print("中文")\n', "utf-8"),
    ".venv/g10_vendored.py": ('import sys\nif __name__ == "__main__":\n    print("中文")\n', "utf-8"),
    ".g11_hidden.py": ('import sys\nif __name__ == "__main__":\n    print("中文")\n', "utf-8"),
    # ---- 該紅的一面 ----
    "r01_pin_inside_main_func.py": (f'import sys\ndef main():\n    {P}\n    print("中文")\nif __name__ == "__main__":\n    main()\n', "utf-8"),
    "r02_pin_module_level.py": (f'import sys\n{P}\nif __name__ == "__main__":\n    print("中文")\n', "utf-8"),
    "r03_pin_nested_in_if.py": (f'import sys\nif __name__ == "__main__":\n    if True:\n        {P}\n    print("中文")\n', "utf-8"),
    "r04_buffer_only_no_pin.py": ('import sys\nif __name__ == "__main__":\n    sys.stdout.buffer.write("中文".encode("utf-8"))\n', "utf-8"),
    "r05_main_no_print.py": ('import sys\nif __name__ == "__main__":\n    pass\n', "utf-8"),
    "r06_stdin_only_stdout_pinned.py": (f'import sys\nif __name__ == "__main__":\n    {P}\n    data = sys.stdin.read()\n', "utf-8"),
    "r07_two_mains_first_only.py": (f'import sys\nif __name__ == "__main__":\n    {P}\n    print("一")\nif __name__ == "__main__":\n    print("二")\n', "utf-8"),
    "r08_pin_nested_in_try.py": (f'import sys\nif __name__ == "__main__":\n    try:\n        {P}\n    except Exception:\n        pass\n    print("中文")\n', "utf-8"),
    # ---- #98 這輪要收的三格 ----
    "pkg/__main__.py": ('import sys\nif __name__ == "__main__":\n    print("中文")\n', "utf-8"),      # #68
    "r10_syntax_error.py": ('import sys\nif __name__ == "__main__":\n    print("中文"\n', "utf-8"),   # #66
    "r11_cp950_source.py": ("x = '要開'\n", "cp950"),                                                 # #66 的 decode 那半
}
RED = {f for f in FIXTURES if f.split("/")[-1].startswith("r") or f == "pkg/__main__.py"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def plant(pop):
    for name, (src, enc) in FIXTURES.items():
        f = pop / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(src, encoding=enc)


def verdicts(mod, pop):
    """{檔名} 判紅的集合;整支掛掉回傳 None —— crash 不是判決。"""
    try:
        return {e.split(":")[0] for e in mod.stream_encoding_issues(pop)}
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def run(tmp):
    prev = tmp / "validate_prev.py"
    prev.write_bytes(subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{PREV}:scripts/validate.py"],
        capture_output=True, check=True).stdout)
    new = load("v_new", ROOT / "scripts" / "validate.py")
    old = load("v_old", prev)

    pop = tmp / "pop"
    pop.mkdir()
    plant(pop)
    vn, vo = verdicts(new, pop), verdicts(old, pop)
    print(f"母體 {len(FIXTURES)} 格,修前 = {PREV}\n")
    if isinstance(vo, str):
        print(f"修前:整支掛掉 —— {vo}")
        print("      (這本身就是 #66 的一半:沒接 UnicodeDecodeError 的話,一支 cp950 存的")
        print("       .py 不是判紅,是把整條守門 traceback 掀掉。crash 不是判決。)")
        # 掛掉的那支沒有逐格答案,拿掉 cp950 那格再跑一次,才比得出其餘各格的差額
        pop2 = tmp / "pop_nocp950"
        pop2.mkdir()
        plant(pop2)
        (pop2 / "r11_cp950_source.py").unlink()
        vo = verdicts(old, pop2)
        print(f"      拿掉 cp950 那格重跑修前 —— 其餘 {len(FIXTURES) - 1} 格才有逐格答案\n")

    bad, delta = [], []
    print(f"{'fixture':<34}{'QA 期望':<9}{'修後':<6}{'修前':<6} 判定")
    for f in sorted(FIXTURES):
        exp = "紅" if f in RED else "綠"
        n = "紅" if f in vn else "綠"
        o = "掛掉" if f == "r11_cp950_source.py" else ("紅" if f in vo else "綠")
        ok = n == exp
        if not ok:
            bad.append(f)
        if n != o:
            delta.append((f, o, n))
        print(f"{f:<34}{exp:<9}{n:<6}{o:<6} {'OK' if ok else '*** 不合 ***'}"
              f"{'' if n == o else f'  差額 修前{o}→修後{n}'}")

    print(f"\n差額 {len(delta)} 筆:")
    for f, o, n in delta:
        print(f"  {f}: 修前{o} → 修後{n}")
    print("  (每一筆都要對得上票面三條;出現「修前紅 → 修後綠」就是本輪放掉了東西)")
    loosened = [d for d in delta if d[1] == "紅" and d[2] == "綠"]
    if loosened:
        print(f"  *** 本輪引入的放行:{loosened} ***")

    # ---- 第四個入口缺口:母體整包放進 `.` 開頭的目錄 ----
    hidden = tmp / ".hidden_root" / "pop"
    hidden.mkdir(parents=True)
    plant(hidden)
    hn, ho = verdicts(new, hidden), verdicts(old, hidden)
    ho = ho if isinstance(ho, str) else f"{len(ho)} 紅"
    print(f"\n---- 母體整包放在 `.hidden_root/` 底下(repo 被 clone 到 ~/.local/… 的形狀)----")
    print(f"  修後:{len(hn)} 紅(過濾吃相對路徑,不受影響)")
    print(f"  修前:{ho}(過濾吃絕對路徑 —— 整條守門靜靜全綠)")
    same = len(hn) == len(vn)
    print(f"  修後兩處答案一致:{same}")
    if not same:
        bad.append(".hidden_root")

    print(f"\n母體 {len(FIXTURES)},不合 {len(bad)}" + (f":{bad}" if bad else ""))
    return 1 if bad or loosened else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        sys.exit(run(pathlib.Path(td)))
