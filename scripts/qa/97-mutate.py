"""#97 的 mutation 台 —— 新判準的每個 knob 改壞,`--self-check` 要轉紅。

#95 那條教訓:**宣稱跑過不算數**。`/build #91` 說「九個 knob 逐一改壞全部轉紅」,
那九個 knob 一個都沒進 repo,QA 只好自己重建一份。所以這輪的 knob 跟著程式碼一起
進 repo,而且這支自己就跑得起來 —— 不用先讀 walkthrough 才知道怎麼驗。

新判準只剩語法比對,knob 因此是有限的:每一個都對應 `stream_encoding_issues` /
`main_blocks` / `reads_stdin` 裡「拿掉就會漏掉一種形狀」的那一行。改壞之後
`--self-check` 要轉紅;紅不了就表示那條判準沒有證據住在預設會跑的地方。

`--self-check` 是兩支:`scripts/validate.py --self-check` 與
`skills/build-batch/batch.py --self-check`,任一支非 0 就算咬住。knob 預設打在
`scripts/validate.py`,第三個元素填相對路徑就改打別支 —— #120 的分級散文 pin
與 #118 的「分級被拒還是整批照印」都住在 `batch.py`,那兩面 validate.py 量不到,
拿它當儀器是在量別支檔。

用法:
    python scripts/qa/97-mutate.py --run          # 整張表跑完,每格報 exit code
    python scripts/qa/97-mutate.py --attribute    # 逐 gate 歸因:誰咬住這個 knob
    python scripts/qa/97-mutate.py --list
    python scripts/qa/97-mutate.py <repo 副本> <knob 名稱>

`--run` 不碰 repo 本體:完整 repo 複製到拋棄式暫存目錄,mutation 全跑在副本上。
"""
import pathlib
import ast
import shutil
import subprocess
import sys
import tempfile

DEFAULT_TARGET = "scripts/validate.py"
BATCH = "skills/build-batch/batch.py"
# 每個 knob 是 (改壞前, 改壞後) 或 (改壞前, 改壞後, 目標檔相對路徑)。
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
    # ---- #120 硬規則的處置:錯誤訊息 + 散文 pin -----------------------
    # 錯誤訊息把繞道寫回去 —— agent 被 client 頂著就照字面把 judgement 改成
    # false 重跑,一路綠,而硬規則是這條線唯一的防護
    "hardrule_msg_signposts_flag": (
        '                "驗收清單第 4 條就是它。要改快只有一條路:回去改票的內容,"\n'
        '                "把動到判斷邏輯或資料寫入的那部分切出去,再重切一次分級。"\n'
        '                "票的內容沒變就是慢,你說了也一樣",',
        '                "驗收清單第 4 條就是它,要改請先改 judgement 旗標")',
        BATCH),
    # 「回去改票的內容」那半拿掉 —— 只說改不成,不說真的那條路長怎樣
    "hardrule_msg_no_real_path": (
        '                "驗收清單第 4 條就是它。要改快只有一條路:回去改票的內容,"\n'
        '                "把動到判斷邏輯或資料寫入的那部分切出去,再重切一次分級。"\n'
        '                "票的內容沒變就是慢,你說了也一樣",',
        '                "驗收清單第 4 條就是它。")',
        BATCH),
    # 硬規則處置那句的 pin 整項刪掉 —— 守門自己少一條的那面
    "hardrule_pin_dropped": (
        '    (re.compile(re.escape("不要自己去改 `judgement` 旗標讓它過")),\n'
        '     "slice-tickets SKILL.md: 硬規則被 client 頂著時的處置那句不見了 —— 沒有它,"\n'
        '     "agent 會把 judgement 改成 false 重跑,而拆掉的當下沒有任何東西會紅"),\n',
        "",
        BATCH),
    # 天花板那句(降級回路只接得住有驗收項的那半)的 pin 整項刪掉
    "ceiling_half_pin_dropped": (
        '    (re.compile(re.escape("接得住的是**有驗收項**的那半")),\n'
        '     "slice-tickets SKILL.md: 降級回路只接得住一半那句不見了 —— 少了它天花板就"\n'
        '     "回到「關住」那個過度宣稱,而 coverage 是空的那半根本不會觸發降級回路"),\n',
        "",
        BATCH),
    # 散文守門整條放行 —— 對照組:逐句比對真的接在跑得到的地方
    "classify_lines_never_complains": (
        "    for pattern, message in CLASSIFY_LINES:\n"
        "        if not pattern.search(text):\n"
        "            return message\n"
        "    return None",
        "    return None\n"
        "    for pattern, message in CLASSIFY_LINES:\n"
        "        if not pattern.search(text):\n"
        "            return message\n"
        "    return None",
        BATCH),
    # ---- #118 分級被拒的那張:整批先算完再退出 -----------------------
    # 判準一樣住在 batch.py,所以證據也要在 `batch.py --self-check` 上轉紅 ——
    # 拿 validate.py 的 self-check 當儀器量它,量的是別支檔。
    # 退回「第一張被拒就把整批打死」—— #118 出廠時的形狀:client 一行分級都
    # 看不到,連他同一輪改的那幾張也一起消失
    "classify_batch_dies_on_first": (
        "        except OverrideRejected as exc:\n"
        "            rows.append((t[\"number\"], exc.cell, str(exc)))",
        "        except OverrideRejected as exc:\n"
        "            raise SystemExit(str(exc))",
        BATCH),
    # 被拒的那張從 client 清單上消失 —— 其餘各張照印,但他不知道少了誰
    "classify_rejected_row_hidden": (
        "    lines += [f\"  {_grade_cell(grade, width)}  {_titled(n, titles)} — {reason}\"\n"
        "              for n, grade, reason in rows] or [\"  (無)\"]",
        "    lines += [f\"  {_grade_cell(grade, width)}  {_titled(n, titles)} — {reason}\"\n"
        "              for n, grade, reason in rows if grade in GRADES] "
        "or [\"  (無)\"]",
        BATCH),
    # 有張被拒還是把貼票那段印出來 —— agent 會照著貼進一份 client 沒點過的清單
    "classify_paste_anyway": (
        "        lines += [f\"  {_titled(n, titles)}\" for n, _ in rejected]\n"
        "        return \"\\n\".join(lines)\n",
        "        lines += [f\"  {_titled(n, titles)}\" for n, _ in rejected]\n",
        BATCH),
    # 退出碼變 0 —— 印歸印,但「當場停」沒了,靜靜往下走
    "classify_reject_exit_zero": (
        "        if rejected:\n            # 整批印完了才停",
        "        if False and rejected:\n            # 整批印完了才停",
        BATCH),
    # 訊息退回「這張」—— 停得對,但 client 手上沒有可以動作的票號(#118 第 2 條)
    "classify_reject_unnamed": (
        "                + \"、\".join(f\"#{n}\" for n, _ in rejected)",
        "                + \"、\".join(\"這張\" for n, _ in rejected)",
        BATCH),
    # 兩張同時被拒時只算第一張 —— 單張的批次上一格都看不出來(review WARN)
    "classify_reject_count_hardcoded": (
        "        head += f\",其中 {len(rejected)} 張改不了\"",
        "        head += \",其中 1 張改不了\"",
        BATCH),
    "classify_reject_list_first_only": (
        "        lines += [f\"  {_titled(n, titles)}\" for n, _ in rejected]",
        "        lines += [f\"  {_titled(n, titles)}\" for n, _ in rejected[:1]]",
        BATCH),
    "classify_reject_only_first": (
        "                + \"、\".join(f\"#{n}\" for n, _ in rejected)",
        "                + \"、\".join(f\"#{n}\" for n, _ in rejected[:1])",
        BATCH),
    # 被拒那張退回「沒有車道」的第三種標籤 —— 原句是「每張票都標了快或慢」,
    # 而硬規則那條路系統自己算得出是慢,吞掉就是 #121 那格
    "classify_rejected_lane_dropped": (
        'GRADE_REJECTED_SLOW = f"{GRADE_SLOW}(改不了)"',
        'GRADE_REJECTED_SLOW = GRADE_REJECTED',
        BATCH),
    # 打錯字那張反過來被猜了一個車道 —— #108「不猜」那條
    "classify_typo_lane_guessed": (
        '            f"你填的分級只能是「快」或「慢」,你打的是 {override!r} —— 改一下再重跑",\n'
        '            GRADE_REJECTED)',
        '            f"你填的分級只能是「快」或「慢」,你打的是 {override!r} —— 改一下再重跑",\n'
        '            GRADE_REJECTED_SLOW)',
        BATCH),
    # 左欄補寬回退成不補 —— client 那份清單左欄歪掉
    "classify_grade_cell_unpadded": (
        '    return grade + " " * (width - _cols(grade))',
        "    return grade",
        BATCH),
    # 欄寬退回「一個 char 兩欄」—— 半形括號那一格少補兩欄,而歪掉的剛好是
    # client 最需要讀的那一列(QA code-review C-1)
    "classify_cell_len_not_cols": (
        '    return grade + " " * (width - _cols(grade))',
        '    return grade + "  " * (width - len(grade))',
        BATCH),
    "classify_width_len_not_cols": (
        "    width = max([_cols(g) for _, g, _ in rows] or [2])",
        "    width = max([len(g) for _, g, _ in rows] or [2])",
        BATCH),
    # 守門整條關掉 —— 對照組:確認 self-check 真的在量這支,不是在量別的
    "guard_off": (
        "    errors = []\n"
        "    for py in sorted(repo.rglob(\"*.py\")):",
        "    errors = []\n"
        "    return errors\n"
        "    for py in sorted(repo.rglob(\"*.py\")):"),
}

def _duplicate_knob_names():
    """`KNOBS` 這張 dict literal 裡有沒有同名的 key。

    撞名是靜的:後面那個直接蓋掉前面那個,表上少一格,而 `--run` 照樣印
    「N/N 咬住」。#118 出廠時靠兩張表相加的長度擋這件事,merge 成一張表之後
    那道守門在 `len()` 上寫不出來(被蓋掉的 key 根本不在 dict 裡),所以改成
    讀自己的 source 對帳。
    """
    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and any(getattr(t, "id", None) == "KNOBS" for t in node.targets)):
            names = [k.value for k in node.value.keys]
            return sorted({n for n in names if names.count(n) > 1})
    raise SystemExit("97-mutate.py:找不到 KNOBS 這張表 —— 撞名守門自己失效了")


_DUPES = _duplicate_knob_names()
if _DUPES:
    # 不寫 assert:`python -O` 下 assert 整條被剝掉,而撞名是靜的
    raise SystemExit("KNOBS 裡有同名的 knob,後面那個會靜靜蓋掉前面那個:"
                     + "、".join(_DUPES))

ROOT = pathlib.Path(__file__).resolve().parents[2]


def target_of(knob):
    """這個 knob 打在哪一支檔(沒宣告第三個元素就是 validate.py)。"""
    spec = KNOBS[knob]
    return spec[2] if len(spec) > 2 else DEFAULT_TARGET


TARGETS = sorted({DEFAULT_TARGET} | {target_of(k) for k in KNOBS})
# 每個被打的目標檔自己就是一支守門 —— 兩份分開寫的話,新加一支的 knob 會
# 還原正確但 self-check 永遠不跑它。
GATES = tuple(TARGETS)


def apply(repo, knob):
    path = pathlib.Path(repo) / target_of(knob)
    src = path.read_text(encoding="utf-8")
    old, new = KNOBS[knob][0], KNOBS[knob][1]
    assert old in src, f"mutation 目標不在 — 判準被改過了:{knob}"
    path.write_text(src.replace(old, new, 1), encoding="utf-8")


def gate_codes(repo):
    """每一支守門各自的 exit code,`{相對路徑: returncode}`。

    分開記是因為「咬住」不分辨是誰咬的:一個 knob 打在 batch.py,卻被
    validate.py 順便咬住的話,batch.py 那條 pin 靜靜失效表上照樣印「咬住」。
    """
    return {gate: subprocess.run(
        [sys.executable, str(repo / gate), "--self-check"],
        cwd=repo, capture_output=True).returncode for gate in GATES}


def self_check(repo):
    """兩支守門各跑一次 `--self-check`,回第一支非 0 的;全綠回最後一支。

    回傳形狀維持 `subprocess.CompletedProcess` —— `run_table` 只讀 returncode
    與 stderr,而 `98-mutate-control.py` 會整支換掉它。
    """
    done = None
    for gate in GATES:
        done = subprocess.run(
            [sys.executable, str(repo / gate), "--self-check"],
            cwd=repo, capture_output=True)
        if done.returncode:
            return done
    return done


def run_table():
    """每個 knob 套上去跑 `--self-check`,回傳 (knob, exit code)。非 0 才是要的。

    `--attribute` 另外逐 gate 拆開跑一次,答「是誰咬住的」—— 表本身不拆,
    因為控制組那條路(`98-mutate-control.py`)換掉的是 `self_check`。
    """
    out = []
    with tempfile.TemporaryDirectory() as td:
        copy = pathlib.Path(td) / "repo"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        control = self_check(copy)
        if control.returncode:
            why = (control.stderr or control.stdout).decode("utf-8", "replace").strip()
            raise RuntimeError("控制組未套 knob 就已經紅；儀器壞了，下面的 mutation 表不執行"
                               + (f"\n{why}" if why else ""))
        pristine = {rel: (copy / rel).read_bytes() for rel in TARGETS}
        for knob in sorted(KNOBS):
            for rel, blob in pristine.items():
                (copy / rel).write_bytes(blob)
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
            print(f"{'咬住' if code else '沒咬住'}  {knob:<30} "
                  f"目標={target_of(knob)} self-check exit={code}")
        missed = [k for k, c in rows if c == 0]
        print(f"\n{len(rows) - len(missed)}/{len(rows)} 個 knob 被 self-check 咬住")
        if missed:
            print("沒咬住:" + ", ".join(missed))
        sys.exit(1 if missed else 0)
    if "--attribute" in sys.argv:
        # 逐 gate 歸因:knob 打在哪支檔,就該是那支檔咬住它。對不上代表那條 pin
        # 其實沒在守,只是被另一支順便判紅 —— 表上看起來一模一樣。
        bad = []
        with tempfile.TemporaryDirectory() as td:
            copy = pathlib.Path(td) / "repo"
            shutil.copytree(ROOT, copy,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            # 控制組:一支 gate 本來就紅的話,底下每個 knob 都會「對得上」,
            # 而歸因表宣稱回答的那個問題一條都沒回答(`--run` 有這道,漏了這邊)
            control = gate_codes(copy)
            if any(control.values()):
                raise SystemExit(
                    "控制組未套 knob 就已經紅,歸因表不執行:"
                    + " ".join(f"{g}={c}" for g, c in control.items()))
            pristine = {rel: (copy / rel).read_bytes() for rel in TARGETS}
            for knob in sorted(KNOBS):
                for rel, blob in pristine.items():
                    (copy / rel).write_bytes(blob)
                apply(copy, knob)
                codes = gate_codes(copy)
                want = target_of(knob)
                ok = codes.get(want, 0) != 0
                if not ok:
                    bad.append(knob)
                print(f"{'對得上' if ok else '對不上'}  {knob:<30} "
                      f"目標={want} " + " ".join(f"{g}={c}" for g, c in codes.items()))
        print()
        print(f"{len(KNOBS) - len(bad)}/{len(KNOBS)} 個 knob 由它自己的目標守門咬住")
        if bad:
            print("對不上:" + ", ".join(bad))
        sys.exit(1 if bad else 0)
    apply(sys.argv[1], sys.argv[2])
    print("mutation 已套用:", sys.argv[2])
