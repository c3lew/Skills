"""#97 的 mutation 台 —— 新判準的每個 knob 改壞,`--self-check` 要轉紅。

#95 那條教訓:**宣稱跑過不算數**。`/build #91` 說「九個 knob 逐一改壞全部轉紅」,
那九個 knob 一個都沒進 repo,QA 只好自己重建一份。所以這輪的 knob 跟著程式碼一起
進 repo,而且這支自己就跑得起來 —— 不用先讀 walkthrough 才知道怎麼驗。

新判準只剩語法比對,knob 因此是有限的:每一個都對應 `stream_encoding_issues` /
`main_blocks` / `reads_stdin` 裡「拿掉就會漏掉一種形狀」的那一行。改壞之後
`validate.py --self-check` 要轉紅;紅不了就表示那條判準沒有證據住在預設會跑的地方。

表上不只一支檔(#118):每個 knob 自己宣告要改哪一支,而改壞之後跑的就是**那支檔
自己的** `--self-check`。判準住在 `skills/build-batch/batch.py` 的那幾條(分級被拒
時整批照不照印)拿 `validate.py --self-check` 量不到 —— 那是在量別支檔。

用法:
    python scripts/qa/97-mutate.py --run          # 整張表跑完,每格報 exit code
    python scripts/qa/97-mutate.py --list
    python scripts/qa/97-mutate.py <repo 副本> <knob 名稱>

`--run` 不碰 repo 本體:完整 repo 複製到拋棄式暫存目錄,mutation 全跑在副本上。
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

VALIDATE = "scripts/validate.py"
BATCH = "skills/build-batch/batch.py"

VALIDATE_KNOBS = {
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
    # 檔名過濾退回「`__` 開頭一律跳過」—— `__main__.py` 這個 package entry point
    # 又變成免檢區(#68 重開)
    "underscore_filter": (
        '    return not any(part == "__pycache__" or part.startswith(".")\n'
        "                   for part in rel.parts)",
        '    return not any(part.startswith((".", "__"))\n'
        "                   for part in rel.parts)"),
    # 過濾整條關掉 —— 反面:`__pycache__` / `.venv` 裡的東西也開始受檢,誤紅那面
    "filter_off": (
        '    return not any(part == "__pycache__" or part.startswith(".")',
        "    return True\n"
        '    return not any(part == "__pycache__" or part.startswith(".")'),
    # 讀不進來退回「靜靜跳過」—— 打錯字的檔重新變成免檢區(#66 重開)
    "unreadable_skip": (
        "        except (SyntaxError, UnicodeDecodeError) as exc:",
        "        except (SyntaxError, UnicodeDecodeError) as exc:\n"
        "            continue"),
    # 只接 SyntaxError —— 非 UTF-8 的 .py 不是判紅,是整支守門 traceback 掛掉
    "decode_error_uncaught": (
        "        except (SyntaxError, UnicodeDecodeError) as exc:",
        "        except SyntaxError as exc:"),
    # ---- #108 分級行的格式 --------------------------------------------
    # 快/慢那個字不再限定 —— 「分級:中」這種寫法重新過關,而下游認不出車道
    "grade_word_any": (
        'GRADE_LINE_OK_RE = re.compile(r"^ {0,3}分級:(?:快|慢) — \\S")',
        'GRADE_LINE_OK_RE = re.compile(r"^ {0,3}分級:.+ — \\S")'),
    # 理由可以留白 —— 「分級:慢 — 」貼上票,client 看到的是一行沒講完的話
    "grade_reason_optional": (
        'GRADE_LINE_OK_RE = re.compile(r"^ {0,3}分級:(?:快|慢) — \\S")',
        'GRADE_LINE_OK_RE = re.compile(r"^ {0,3}分級:(?:快|慢) —")'),
    # 冒號全形半形都收 —— batch.py 印的是半形,收兩種就是兩種寫法並存
    "grade_colon_any": (
        'GRADE_LINE_OK_RE = re.compile(r"^ {0,3}分級:(?:快|慢)',
        'GRADE_LINE_OK_RE = re.compile(r"^ {0,3}分級[:︰：](?:快|慢)'),
    # 掃描母體只認半形冒號 —— 寫成全形的那行根本沒被看到,漏咬那面
    "grade_scan_narrow": (
        'GRADE_LINE_RE = re.compile(r"^ {0,3}分級[:︰：].*$", re.M)',
        'GRADE_LINE_RE = re.compile(r"^ {0,3}分級:.*$", re.M)'),
    # 呼叫 classify 卻沒示範過分級行的那一半關掉 —— agent 回去現場發明一個寫法
    "grade_no_example_ok": (
        "    if CLASSIFY_CALL_RE.search(text) and not lines:",
        "    if False and CLASSIFY_CALL_RE.search(text) and not lines:"),
    # 守門沒接進 validate() —— 函式自己綠,lint 跑一遍卻永遠碰不到它
    "grade_not_wired": (
        "        for issue in grade_line_issues(text):",
        "        for issue in []:"),
    # 分級行守門整條關掉 —— 對照組
    "grade_guard_off": (
        "    issues = []\n    lines = GRADE_LINE_RE.findall(text)",
        "    return []\n    issues = []\n    lines = GRADE_LINE_RE.findall(text)"),
    # 守門整條關掉 —— 對照組:確認 self-check 真的在量這支,不是在量別的
    "guard_off": (
        "    errors = []\n"
        "    for py in sorted(repo.rglob(\"*.py\")):",
        "    errors = []\n"
        "    return errors\n"
        "    for py in sorted(repo.rglob(\"*.py\")):"),
}

# ---- #118 分級被拒的那張:整批先算完再退出 -------------------------------
# 判準住在 batch.py,所以證據也要在 `batch.py --self-check` 上轉紅 —— 拿
# validate.py 的 self-check 當儀器量它,量的是別支檔。
BATCH_KNOBS = {
    # 退回「第一張被拒就把整批打死」—— #118 出廠時的形狀:client 一行分級都
    # 看不到,連他同一輪改的那幾張也一起消失
    "classify_batch_dies_on_first": (
        "        except OverrideRejected as exc:\n"
        "            rows.append((t[\"number\"], None, str(exc)))",
        "        except OverrideRejected as exc:\n"
        "            raise SystemExit(str(exc))"),
    # 被拒的那張從 client 清單上消失 —— 其餘各張照印,但他不知道少了誰
    "classify_rejected_row_hidden": (
        "    lines += [f\"  {_grade_cell(grade, width)}  {_titled(n, titles)} — {reason}\"\n"
        "              for n, grade, reason in rows] or [\"  (無)\"]",
        "    lines += [f\"  {_grade_cell(grade, width)}  {_titled(n, titles)} — {reason}\"\n"
        "              for n, grade, reason in rows if grade] or [\"  (無)\"]"),
    # 有張被拒還是把貼票那段印出來 —— agent 會照著貼進一份 client 沒點過的清單
    "classify_paste_anyway": (
        "        lines += [f\"  {_titled(n, titles)}\" for n, _ in rejected]\n"
        "        return \"\\n\".join(lines)\n",
        "        lines += [f\"  {_titled(n, titles)}\" for n, _ in rejected]\n"),
    # 退出碼變 0 —— 印歸印,但「當場停」沒了,靜靜往下走
    "classify_reject_exit_zero": (
        "        if rejected:\n            # 整批印完了才停",
        "        if False and rejected:\n            # 整批印完了才停"),
    # 訊息退回「這張」—— 停得對,但 client 手上沒有可以動作的票號(#118 第 2 條)
    "classify_reject_unnamed": (
        "                + \"\\n\".join(f\"  #{n} — {reason}\" for n, reason in rejected))",
        "                + \"\\n\".join(f\"  這張 — {reason}\" for n, reason in rejected))"),
    # 兩張同時被拒時只算第一張 —— 單張的批次上一格都看不出來(review WARN)
    "classify_reject_count_hardcoded": (
        "        head += f\",其中 {len(rejected)} 張改不了\"",
        "        head += \",其中 1 張改不了\""),
    "classify_reject_list_first_only": (
        "        lines += [f\"  {_titled(n, titles)}\" for n, _ in rejected]",
        "        lines += [f\"  {_titled(n, titles)}\" for n, _ in rejected[:1]]"),
    "classify_reject_only_first": (
        "                + \"\\n\".join(f\"  #{n} — {reason}\" for n, reason in rejected))",
        "                + \"\\n\".join(f\"  #{n} — {reason}\" for n, reason in rejected[:1]))"),
    # 左欄補寬回退成不補 —— client 那份清單左欄歪掉
    "classify_grade_cell_unpadded": (
        "    return label + \"  \" * (width - len(label))",
        "    return label"),
}

TARGETS = {VALIDATE: VALIDATE_KNOBS, BATCH: BATCH_KNOBS}
# knob 名稱 -> (要改的檔, 舊字串, 新字串)。第一欄同時決定「改壞之後跑哪一支
# `--self-check`」:判準住在哪支檔,證據就要在那支檔預設會跑的地方轉紅。
KNOBS = {name: (target, old, new)
         for target, table in TARGETS.items()
         for name, (old, new) in table.items()}
if len(KNOBS) != sum(len(t) for t in TARGETS.values()):
    # 不寫 assert:`python -O` 下 assert 整條被剝掉,而撞名是靜的
    raise SystemExit("兩張表的 knob 名字撞了 —— 後面那個會靜靜蓋掉前面那個")

ROOT = pathlib.Path(__file__).resolve().parents[2]


def apply(repo, knob):
    target, old, new = KNOBS[knob]
    path = pathlib.Path(repo) / target
    src = path.read_text(encoding="utf-8")
    assert old in src, f"mutation 目標不在 — 判準被改過了:{knob}"
    path.write_text(src.replace(old, new, 1), encoding="utf-8")


def self_check(repo, target=VALIDATE):
    return subprocess.run(
        [sys.executable, str(pathlib.Path(repo) / target), "--self-check"],
        cwd=repo, capture_output=True)


def run_table():
    """每個 knob 套上去跑 `--self-check`,回傳 (knob, exit code)。非 0 才是要的。

    跑的是**那個 knob 自己那支檔**的 self-check:判準散在兩支檔上,拿其中一支
    的 self-check 量另一支,量到的是別的東西。
    """
    out = []
    with tempfile.TemporaryDirectory() as td:
        copy = pathlib.Path(td) / "repo"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        for target in TARGETS:
            control = self_check(copy, target)
            if control.returncode:
                why = (control.stderr or control.stdout).decode("utf-8", "replace").strip()
                raise RuntimeError(f"控制組({target})未套 knob 就已經紅；儀器壞了，"
                                   "下面的 mutation 表不執行"
                                   + (f"\n{why}" if why else ""))
        pristine = {t: (copy / t).read_bytes() for t in TARGETS}
        for knob in sorted(KNOBS):
            target = KNOBS[knob][0]
            (copy / target).write_bytes(pristine[target])
            apply(copy, knob)
            r = self_check(copy, target)
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
            print(f"{'咬住' if code else '沒咬住'}  {knob:<30} "
                  f"{KNOBS[knob][0]} --self-check exit={code}")
        missed = [k for k, c in rows if c == 0]
        print(f"\n{len(rows) - len(missed)}/{len(rows)} 個 knob 被 self-check 咬住")
        if missed:
            print("沒咬住:" + ", ".join(missed))
        sys.exit(1 if missed else 0)
    apply(sys.argv[1], sys.argv[2])
    print("mutation 已套用:", sys.argv[2])
