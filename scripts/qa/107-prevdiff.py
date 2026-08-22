"""#107 QA 的修前對照 —— 同一份母體,修前(84ab07d)vs 修後的判斷邏輯。

這張票動的是**判斷邏輯**(新增 `judge_ordering_issues`),不是入口。新規則只會多檢,
多檢出來的那批在修之前一律是綠的 —— 所以只跑「該紅的那一面」看它紅,證明不了
「本來好好的檔沒被誤紅」。母體因此兩面都寫,而且兩面都跑修前 / 修後各一次。

母體兩面:
  (a) **真實母體** —— 現在 repo 裡 `skills/*/SKILL.md` 全部。出貨的東西不能被新規則
      誤紅;有任何一支「修前綠 → 修後紅」而它不是票面要收的形狀,就是本輪引入的 regression。
  (b) **fixture 母體** —— QA 讀 #107 驗收原句自己判的該綠 / 該紅案例。期望值是讀原句
      寫的,不是從 `judge_ordering_issues` 的實作反推的 —— 實作同意它是結論,不是前提。

驗收原句(QA 判期望值的唯一依據):
  「凡是自己開一支 subagent 當 judge 的 SKILL.md,必須有一段 `## …並行池…`,表格
   第一欄粗體的 lane 名字剛好是 regression / walkthrough / code-review 三支(順序自由),
   而且文字裡要有一句沒被否定的『judge … walkthrough …之後』。」

fixture 母體含 #57 的假陽性對照組:「只是散文提到 judge、自己沒跑 judge」的該綠 ——
#57 的教訓是關鍵詞上鉤會把沒跑 judge 的 skill 一起紅掉。

用法:
    python scripts/qa/107-prevdiff.py      # 母體不合 0 才算過
"""
import importlib.util
import pathlib
import subprocess
import sys
import tempfile

PREV = "84ab07d"  # #107 動判斷邏輯之前的最後一個 commit
ROOT = pathlib.Path(__file__).resolve().parents[2]

FM = "---\nname: {name}\ndescription: fixture for #107 prevdiff\n---\n\n"

POOL3 = (
    "## 2. 並行池\n\n"
    "| lane | 做什麼 |\n"
    "| --- | --- |\n"
    "| **regression** | 跑既有 suite |\n"
    "| **walkthrough** | 照驗收原句實測 |\n"
    "| **code-review** | 讀 diff |\n\n"
)
JUDGE_RUN = "開一個乾淨 subagent 當 judge,只餵驗收原句與證據。\n"
ORDER_OK = "獨立 judge 排在 walkthrough 之後才開,不進並行池。\n"

# key = 母體裡的 skill dir 名;開頭 g=該綠、r=該紅。value = SKILL.md 正文
FIXTURES = {
    # ---- 該綠的一面 ----
    # 完整三 lane 表 + 排序約束 —— 驗收原句正面照抄的形狀
    "g01-pool-full": POOL3 + "## 3. 獨立 judge\n\n" + ORDER_OK + JUDGE_RUN,
    # 順序自由:三支都在,表上下順序換過
    "g02-lane-order-shuffled": (
        "## 2. 並行池\n\n"
        "| lane | 做什麼 |\n"
        "| --- | --- |\n"
        "| **code-review** | 讀 diff |\n"
        "| **regression** | 跑既有 suite |\n"
        "| **walkthrough** | 照驗收原句實測 |\n\n"
        "## 3. 獨立 judge\n\n" + ORDER_OK + JUDGE_RUN
    ),
    # #57 假陽性對照組:散文提到 judge,自己一支 judge 都沒跑 —— 規則不該上鉤
    "g03-mentions-judge-only": (
        "## 收尾\n\n獨立 judge 抓 works-but-wrong 是 /qa 那關的事,這片只讀它的結論。\n"
    ),
    # 整份文件跟 judge 無關
    "g04-no-judge-at-all": "## 做什麼\n\n讀 diff,寫 review,沒有 judge 這回事。\n",
    # judge runner + 三 lane + 排序句寫法不同(「要等…之後」),還多一句散文提到 judge
    "g05-pool-plus-prose": (
        POOL3 + "## 3. 獨立 judge\n\n"
        "獨立 judge 要等 walkthrough 之後才開,不進並行池。\n" + JUDGE_RUN +
        "judge 的輸入只有驗收原句,不給它 diff。\n"
    ),
    # 並行池 heading 前後有別的字 —— 「一段 ## …並行池…」不限定標題只有那三個字
    "g06-heading-decorated": (
        "## 2. 三線並行池(同時開始)\n\n"
        "| lane | 做什麼 |\n"
        "| --- | --- |\n"
        "| **walkthrough** | 照驗收原句實測 |\n"
        "| **regression** | 跑既有 suite |\n"
        "| **code-review** | 讀 diff |\n\n"
        "## 3. 獨立 judge\n\n" + ORDER_OK + JUDGE_RUN
    ),
    # ---- 該紅的一面 ----
    # judge 混進 lane 表 —— #107 指名的那個失敗形狀
    "r01-judge-in-pool": (
        "## 2. 並行池\n\n"
        "| lane | 做什麼 |\n"
        "| --- | --- |\n"
        "| **regression** | 跑既有 suite |\n"
        "| **walkthrough** | 照驗收原句實測 |\n"
        "| **code-review** | 讀 diff |\n"
        "| **judge** | 判定 |\n\n"
        "## 3. 獨立 judge\n\n" + ORDER_OK + JUDGE_RUN
    ),
    # 少一支 lane:並行沒做滿
    "r02-missing-lane": (
        "## 2. 並行池\n\n"
        "| lane | 做什麼 |\n"
        "| --- | --- |\n"
        "| **regression** | 跑既有 suite |\n"
        "| **walkthrough** | 照驗收原句實測 |\n\n"
        "## 3. 獨立 judge\n\n" + ORDER_OK + JUDGE_RUN
    ),
    # 排序反寫:關鍵詞全在,順序倒過來
    "r03-ordering-flipped": (
        POOL3 + "## 3. 獨立 judge\n\n"
        "獨立 judge 排在 walkthrough 之前就開,不進並行池。\n" + JUDGE_RUN
    ),
    # 排序被否定
    "r04-ordering-negated": (
        POOL3 + "## 3. 獨立 judge\n\n"
        "獨立 judge 不用等 walkthrough 之後,直接進並行池。\n" + JUDGE_RUN
    ),
    # 整段池不見了 —— judge 還在跑,但沒人寫下三線同時開
    "r05-no-pool-section": "## 3. 獨立 judge\n\n" + ORDER_OK + JUDGE_RUN,
    # 三 lane 齊全,但排序約束整句不見
    "r06-no-ordering-line": (
        POOL3 + "## 3. 獨立 judge\n\n獨立 judge 逐條判定,只餵驗收原句。\n" + JUDGE_RUN
    ),
}
RED = {f for f in FIXTURES if f.startswith("r")}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def plant(skills):
    for name, body in FIXTURES.items():
        d = skills / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(FM.format(name=name) + body, encoding="utf-8")


def verdicts(mod, skills, repo):
    """{skill 名: [error 原文]};整支掛掉回傳字串 —— crash 不是判決。"""
    try:
        errs = mod.validate(skills, repo)
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    out = {}
    for e in errs:
        parts = e.split(":")[0].split("/")
        out.setdefault(parts[1] if len(parts) > 1 else e, []).append(e)
    return out


def table(title, names, vn, vo, expected=None):
    """列一張 修後/修前 對照表,回傳 (不合清單, 差額清單)。"""
    bad, delta = [], []
    print(f"\n==== {title} ====")
    head = f"{'項目':<28}{'修後':<6}{'修前':<6}"
    print(head + ("  QA 期望   判定" if expected else "  判定"))
    for n in names:
        new_red, old_red = n in vn, n in vo
        a = "紅" if new_red else "綠"
        b = "紅" if old_red else "綠"
        line = f"{n:<28}{a:<6}{b:<6}"
        if expected is not None:
            exp = "紅" if n in expected else "綠"
            ok = a == exp
            if not ok:
                bad.append(n)
            line += f"  {exp:<8}{'OK' if ok else '*** 不合 ***'}"
        if new_red != old_red:
            delta.append((n, b, a))
            line += f"  差額 修前{b}→修後{a}"
        print(line)
    return bad, delta


def run(tmp):
    prev = tmp / "validate_prev.py"
    prev.write_bytes(subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{PREV}:scripts/validate.py"],
        capture_output=True, check=True).stdout)
    new = load("v_new_107", ROOT / "scripts" / "validate.py")
    old = load("v_old_107", prev)

    print(f"修前 = {PREV}(#107 動判斷邏輯之前的最後一個 commit)")

    # ---- (a) 真實母體:現在 repo 裡的 skills/*/SKILL.md ----
    real_dir = ROOT / "skills"
    real = sorted(p.name for p in real_dir.iterdir() if (p / "SKILL.md").is_file())
    rn, ro = verdicts(new, real_dir, ROOT), verdicts(old, real_dir, ROOT)
    for label, v in (("修後", rn), ("修前", ro)):
        if isinstance(v, str):
            print(f"{label}:整支掛掉 —— {v}")
            return 1
    bad_a, delta_a = table(f"(a) 真實母體 —— repo 裡 {len(real)} 支 SKILL.md", real, rn, ro)

    # ---- (b) fixture 母體:QA 讀驗收原句自己判的期望值 ----
    skills = tmp / "skills"
    skills.mkdir()
    plant(skills)
    fn, fo = verdicts(new, skills, tmp), verdicts(old, skills, tmp)
    for label, v in (("修後", fn), ("修前", fo)):
        if isinstance(v, str):
            print(f"{label}:整支掛掉 —— {v}")
            return 1
    bad_b, delta_b = table(f"(b) fixture 母體 —— {len(FIXTURES)} 格",
                           sorted(FIXTURES), fn, fo, expected=RED)

    # ---- 差額判讀 ----
    print(f"\n==== 差額 {len(delta_a) + len(delta_b)} 筆 ====")
    for src, delta, v in (("真實", delta_a, rn), ("fixture", delta_b, fn)):
        for n, o, a in delta:
            print(f"  [{src}] {n}: 修前{o} → 修後{a}")
            for e in v.get(n, []):
                print(f"      {e}")
    loosened = [d for d in delta_a + delta_b if d[1] == "紅" and d[2] == "綠"]
    if loosened:
        print(f"  *** 本輪引入的放行(修前紅 → 修後綠):{loosened} ***")
    # 真實母體任何一支變紅都要人看:出貨的 SKILL.md 被新規則咬到就是誤紅
    if delta_a:
        print("  *** 真實母體出現差額 —— 出貨的 SKILL.md 被新規則改判,逐筆判讀 ***")
    unexpected = [n for n, _, a in delta_b if a == "紅" and n not in RED]
    if unexpected:
        print(f"  *** 非預期的變紅(QA 判該綠卻被新規則咬到):{unexpected} ***")

    bad = bad_b + [f"real:{n}" for n, _, a in delta_a if a == "紅"]
    total = len(real) + len(FIXTURES)
    print(f"\n母體 {total},不合 {len(bad)}" + (f":{bad}" if bad else ""))
    return 1 if bad or loosened else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        sys.exit(run(pathlib.Path(td)))
