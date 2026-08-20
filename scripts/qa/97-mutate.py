"""#97 的 mutation 台 —— 新判準的每個 knob 改壞,`--self-check` 要轉紅。

#95 那條教訓:**宣稱跑過不算數**。`/build #91` 說「九個 knob 逐一改壞全部轉紅」,
那九個 knob 一個都沒進 repo,QA 只好自己重建一份。所以這輪的 knob 跟著程式碼一起
進 repo,而且這支自己就跑得起來 —— 不用先讀 walkthrough 才知道怎麼驗。

新判準只剩語法比對,knob 因此是有限的:每一個都對應 `stream_encoding_issues` /
`main_blocks` / `reads_stdin` 裡「拿掉就會漏掉一種形狀」的那一行。改壞之後
`validate.py --self-check` 要轉紅;紅不了就表示那條判準沒有證據住在預設會跑的地方。

用法:
    python scripts/qa/97-mutate.py --run          # 整張表跑完,每格報 exit code
    python scripts/qa/97-mutate.py --list
    python scripts/qa/97-mutate.py <repo 副本> <knob 名稱>

`--run` 不碰 repo 本體:validate.py 複製到拋棄式暫存目錄,mutation 全跑在副本上。
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

KNOBS = {
    # 「第一層」放寬成「__main__ 裡面任何地方」—— #72 的死碼 pin 重新算數
    "pin_anywhere_in_main": (
        "            if all(any(ast.unparse(s) == pin for s in m.body) for m in mains):",
        "            if all(any(ast.unparse(s) == pin for s in ast.walk(m)) for m in mains):"),
    # 位置整條不看 —— pin 寫在 main() 裡也算,這正是這支守門當初 ship 壞掉的形狀
    "pin_anywhere_in_file": (
        "            if all(any(ast.unparse(s) == pin for s in m.body) for m in mains):",
        "            if any(ast.unparse(s) == pin for s in ast.walk(tree)):"),
    # 只看找到的第一個 __main__ —— #69 重開
    "first_main_only": (
        "        mains = main_blocks(tree)",
        "        mains = main_blocks(tree)[:1]"),
    # 退回 tree.body:巢狀在 try / if 底下的 __main__ 找不到,整個檔被跳過 —— #65 重開
    "main_body_only": (
        "    return [n for n in ast.walk(tree)\n"
        "            if isinstance(n, ast.If) and ast.unparse(n.test) == MAIN_TEST]",
        "    return [n for n in tree.body\n"
        "            if isinstance(n, ast.If) and ast.unparse(n.test) == MAIN_TEST]"),
    # 「有沒有碰 stdin」退回讀字串 —— 守門自己的規則表那句字面值就會誤判
    "stdin_by_text": (
        "    return any(isinstance(n, ast.Attribute) and n.attr == \"stdin\"\n"
        "               and getattr(n.value, \"id\", None) == \"sys\"\n"
        "               for n in ast.walk(tree))",
        "    return \"sys.stdin\" in ast.dump(tree) or \"sys.stdin\" in ast.unparse(tree)"),
    # stdin 那半整條放行 —— 真的讀 stdin 的檔不用 pin stdin
    "stdin_never": (
        "    return any(isinstance(n, ast.Attribute) and n.attr == \"stdin\"",
        "    return False\n"
        "    return any(isinstance(n, ast.Attribute) and n.attr == \"stdin\""),
    # 反過來:每個檔都算有碰 stdin —— 誤紅那面
    "stdin_always": (
        "    return any(isinstance(n, ast.Attribute) and n.attr == \"stdin\"",
        "    return True\n"
        "    return any(isinstance(n, ast.Attribute) and n.attr == \"stdin\""),
    # 不過 norm():ast.unparse 吐單引號,雙引號的字面值靜靜地全部不 match。
    # 這條在這種規則下最陰 —— 「全部不 match」跟「全部合格」長得不一樣,但
    # 只要比對方向反過來就一模一樣(#96 原型踩過兩次)
    "no_norm": (
        "STREAM_PINS = (\n"
        "    (\"stdout\", norm('sys.stdout.reconfigure(encoding=\"utf-8\")'),",
        "STREAM_PINS = (\n"
        "    (\"stdout\", 'sys.stdout.reconfigure(encoding=\"utf-8\")',"),
    # `.buffer` 豁免復活 —— #96 AC7 拿掉的那條
    "buffer_exempt": (
        "            if all(any(ast.unparse(s) == pin for s in m.body) for m in mains):\n"
        "                continue",
        "            if f\"sys.{stream}.buffer\" in ast.unparse(tree):\n"
        "                continue\n"
        "            if all(any(ast.unparse(s) == pin for s in m.body) for m in mains):\n"
        "                continue"),
    # 「沒有裸 print( 就免 pin」豁免復活 —— #96 AC8 拿掉的那條
    "print_exempt": (
        "        mains = main_blocks(tree)\n"
        "        if not mains:\n"
        "            continue",
        "        mains = main_blocks(tree)\n"
        "        if not mains:\n"
        "            continue\n"
        "        if not any(isinstance(n, ast.Call)\n"
        "                   and getattr(n.func, \"id\", None) == \"print\"\n"
        "                   for n in ast.walk(tree)):\n"
        "            continue"),
    # 守門整條關掉 —— 對照組:確認 self-check 真的在量這支,不是在量別的
    "guard_off": (
        "    errors = []\n"
        "    for py in sorted(repo.rglob(\"*.py\")):",
        "    errors = []\n"
        "    return errors\n"
        "    for py in sorted(repo.rglob(\"*.py\")):"),
}

ROOT = pathlib.Path(__file__).resolve().parents[2]


def apply(repo, knob):
    path = pathlib.Path(repo) / "scripts" / "validate.py"
    src = path.read_text(encoding="utf-8")
    old, new = KNOBS[knob]
    assert old in src, f"mutation 目標不在 — 判準被改過了:{knob}"
    path.write_text(src.replace(old, new, 1), encoding="utf-8")


def run_table():
    """每個 knob 套上去跑 `--self-check`,回傳 (knob, exit code)。非 0 才是要的。"""
    out = []
    with tempfile.TemporaryDirectory() as td:
        copy = pathlib.Path(td) / "repo"
        for knob in sorted(KNOBS):
            shutil.rmtree(copy, ignore_errors=True)
            (copy / "scripts").mkdir(parents=True)
            shutil.copy2(ROOT / "scripts" / "validate.py", copy / "scripts")
            apply(copy, knob)
            # cwd=ROOT 只影響相對路徑的輸出；self_check 最後一條的 REPO 是從
            # __file__ 解的，副本跑起來打的是這份只有 validate.py 的暫存副本，
            # 不是 repo 本體 —— 11/11 全靠 inline fixture 咬住（#101）。
            r = subprocess.run([sys.executable, str(copy / "scripts" / "validate.py"),
                                "--self-check"], cwd=ROOT, capture_output=True)
            out.append((knob, r.returncode))
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    if "--list" in sys.argv:
        print("\n".join(sorted(KNOBS)))
        sys.exit(0)
    if "--run" in sys.argv:
        rows = run_table()
        for knob, code in rows:
            print(f"{'咬住' if code else '沒咬住'}  {knob:<22} self-check exit={code}")
        missed = [k for k, c in rows if c == 0]
        print(f"\n{len(rows) - len(missed)}/{len(rows)} 個 knob 被 self-check 咬住")
        if missed:
            print("沒咬住:" + ", ".join(missed))
        sys.exit(1 if missed else 0)
    apply(sys.argv[1], sys.argv[2])
    print("mutation 已套用:", sys.argv[2])
