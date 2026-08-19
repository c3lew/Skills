"""#60 同型全掃 — 「提到」的每一種寫法 vs 「用到」的每一種寫法。

#60 的病是「豁免用全檔 substring 比對」,所以一條 fail 不是一條 fail:整份
STREAM_PINS 的兩個目標字串(bypass 與 pin)乘上散文能出現的每個位置(comment、
docstring、字串常數、f-string、變數名)都是同一形狀。這支把母體一次列完,
表格化跑出來當證據,而不是只重跑票上撞到的那一條。

用法:
    python scripts/qa/60-mention-sweep.py <repo>              # 提到 vs 用到 全表
    python scripts/qa/60-mention-sweep.py <repo> --positional # 位置判準(#58 原病)
    python scripts/qa/60-mention-sweep.py <repo> --skips      # 守門靜默跳過的路
    ... --old                                                 # 對照組:#60 修之前那版守門
"""
import subprocess
import sys
import tempfile
from pathlib import Path

RUNNABLE = 'import sys\nif __name__ == "__main__":\n    '
NAKED = RUNNABLE + 'print("要開的票")\n'
BYPASS = "sys.stdout.buffer"
PIN = 'sys.stdout.reconfigure(encoding="utf-8")'

# (情境, 原始碼, 期望) — 期望 "RED" = 守門要出聲,"GREEN" = 不得誤紅
MENTION = [
    ("對照:裸 print,什麼都沒有", NAKED, "RED"),
    ("提到 bypass — 行內 comment", NAKED + f"    # 這裡沒走 {BYPASS}\n", "RED"),
    ("提到 bypass — 檔頭 comment", f"# 說明:{BYPASS} 不適用\n" + NAKED, "RED"),
    ("提到 bypass — module docstring", f'"""{BYPASS} 的說明,不是呼叫"""\n' + NAKED, "RED"),
    ("提到 bypass — 字串常數", f'x = "{BYPASS}"\n' + NAKED, "RED"),
    ("提到 bypass — f-string", f'x = f"用 {{1}} 的 {BYPASS}"\n' + NAKED, "RED"),
    ("提到 bypass — 變數名近似", NAKED + "    sys_stdout_buffer = 1\n", "RED"),
    ("提到 pin — 行內 comment", NAKED + f"    # 記得補 {PIN}\n", "RED"),
    ("提到 pin — docstring", f'"""要記得 {PIN}"""\n' + NAKED, "RED"),
    ("提到 pin — 字串常數", "x = " + repr(PIN) + "\n" + NAKED, "RED"),
    ("用到 bypass — 真的 write", RUNNABLE + f'{BYPASS}.write(b"x")\n', "GREEN"),
    ("用到 pin — 雙引號", RUNNABLE + f'{PIN}\n    print(1)\n', "GREEN"),
    ("用到 pin — 單引號(unparse 正規化)",
     RUNNABLE + "sys.stdout.reconfigure(encoding='utf-8')\n    print(1)\n", "GREEN"),
]

# #58 的原病:pin 只要文字上在 __main__ 之後就算數。位置判準要擋住這些。
POSITIONAL = [
    ("pin 在 main(),__main__ 只呼叫它",
     f'import sys\ndef main():\n    {PIN}\n\n\nif __name__ == "__main__":\n    main()\n', "RED"),
    ("pin 在 __main__ 之前的 top-level",
     f'import sys\n{PIN}\nif __name__ == "__main__":\n    print("要開的票")\n', "RED"),
    ("pin 真的在 __main__ block 裡", RUNNABLE + f'{PIN}\n    print("要開的票")\n', "GREEN"),
    ("pin 在 __main__ block 裡的 try 底下",
     f'import sys\nif __name__ == "__main__":\n    try:\n        {PIN}\n    except Exception:\n        pass\n    print("要開的票")\n', "GREEN"),
]


# 這一輪 QA 抓到的第三型:守門連看都不看這個檔。AST 化之後多了兩條靜默跳過的路,
# 母體 = 2,兩條都會讓一支裸 print 的 script 無聲過關(#60 要防的正是無聲繞過)。
SKIPS = [
    ("__main__ 縮排在 try 底下 -> 找不到 top-level If,整檔跳過",
     'import sys\ntry:\n    if __name__ == "__main__":\n        print("要開的票")\nexcept Exception:\n    pass\n', "RED"),
    ("__main__ 縮排在 if True 底下 -> 同上",
     'import sys\nif True:\n    if __name__ == "__main__":\n        print("要開的票")\n', "RED"),
    ("檔案 parse 不過(SyntaxError)-> 整檔跳過(build 已在 code 裡註明的取捨)",
     'if __name__ == "__main__":\n    print("要開的票"\n', "RED"),
]


def guard_module(repo, old):
    """`stream_encoding_issues` 的來源:現況,或 #60 修之前那版(對照組)。"""
    if not old:
        sys.path.insert(0, str(Path(repo) / "scripts"))
        import validate

        return validate
    src = subprocess.run(["git", "-C", str(repo), "show", "d3cc9ed^:scripts/validate.py"],
                         capture_output=True, check=True).stdout
    box = Path(tempfile.mkdtemp())
    (box / "validate_old.py").write_bytes(src)
    sys.path.insert(0, str(box))
    import validate_old

    return validate_old


def run(repo, cases, old=False):
    V = guard_module(repo, old)

    tmp = Path(tempfile.mkdtemp())
    probe = tmp / "probe.py"
    rows, bad = [], 0
    for name, src, want in cases:
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
    cases = MENTION
    if "--positional" in sys.argv:
        cases = POSITIONAL
    elif "--skips" in sys.argv:
        cases = SKIPS
    sys.exit(1 if run(sys.argv[1], cases, "--old" in sys.argv) else 0)
