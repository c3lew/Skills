"""#112 QA 的修前對照 —— 同一份母體,修前(b11c43c)vs 修後的判斷邏輯。

這張票動的是**判斷邏輯**(`judge_ordering_issues` 的錨點從排版/關鍵字改成宣告本身),
不是入口。改判斷邏輯兩個方向都會動:本來漏抓的要開始紅(A1 / A2 / A3),本來誤紅的要
轉綠(A4)。所以只跑「該紅的那一面」證明不了「出貨的檔沒被新錨點誤紅」—— 母體兩面
都寫,兩面都跑修前 / 修後各一次。

母體兩面:
  (a) **真實母體** —— 現在 repo 裡 `skills/*/SKILL.md` 全部。修前綠的不准變紅,除非
      票面就是要收那個形狀。任何一筆差額都列出來給人判。
  (b) **fixture 母體** —— QA 讀 #112 票面自己判的該綠 / 該紅。期望值是讀票寫的,不是
      從新版 `judge_ordering_issues` 的實作反推的 —— 實作同意它是結論,不是前提。

期望值的唯一依據 = #112 票面那張表的原句:
  A1「並行池 lane 表插一列 `| judge | … |`(第一欄**不粗體**)」現況綠 → 應該紅。
  A2「正文那句排序約束整句刪掉,只留 §3 標題」現況綠 → 應該紅。
  A3「整段 `## 2. 並行池` 拿掉」現況紅但訊息是 `lanes are []` → 應該是
     `runs an 獨立 judge but declares no 並行池 section`,也就是訊息要指到「整段不見」。
  A4「§2 的 `###` 子段裡加一張非 lane 表(第一欄粗體)」現況紅 → 應該綠(假陽性)。
外加 #107 就在守的既有形狀(judge lane 在池裡、少一支 lane、排序反寫 / 被否定),
它們在這一輪不准鬆掉。
再加 #57 的假陽性對照組:「只是散文提到 judge、自己沒跑 judge」的該綠。

用法:
    python scripts/qa/112-prevdiff.py      # 母體不合 0 才算過
"""
import importlib.util
import pathlib
import subprocess
import sys
import tempfile

PREV = "b11c43c"  # #112 動判斷邏輯之前的最後一個 commit
ROOT = pathlib.Path(__file__).resolve().parents[2]

FM = "---\nname: {name}\ndescription: fixture for #112 prevdiff\n---\n\n"

POOL3 = (
    "## 2. 並行池\n\n"
    "| lane | 做什麼 |\n"
    "| --- | --- |\n"
    "| **regression** | 跑既有 suite |\n"
    "| **walkthrough** | 照驗收原句實測 |\n"
    "| **code-review** | 讀 diff |\n\n"
)
JUDGE_RUN = "開一個乾淨 subagent 當 judge,只餵驗收原句與證據。\n"
ORDER_OK = "**排序約束**:獨立 judge 排在 walkthrough 之後才開,不進並行池。\n"
JUDGE_HEAD_PLAIN = "## 3. 獨立 judge\n\n"
# #112 點名的那個「自己就把檢查餵飽」的標題
JUDGE_HEAD_LOADED = "## 3. 獨立 judge(排在 walkthrough 之後,不進並行池)\n\n"

# key 開頭 g=該綠、r=該紅;a1..a4 = #112 票面表格那四格
FIXTURES = {
    # ---------- 該綠的一面 ----------
    # 票面正面照抄的形狀:三 lane 表 + 正文寫下排序約束
    "g01-pool-full": POOL3 + JUDGE_HEAD_PLAIN + ORDER_OK + JUDGE_RUN,
    # A4:§2 的 ### 子段多一張非 lane 表(第一欄粗體)—— 票面寫明「green — 這是假陽性」
    "g02-a4-extra-non-lane-table": (
        POOL3 + "### 資源分配\n\n| 資源 | 誰用 |\n| --- | --- |\n"
        "| **port** | walkthrough |\n| **fixture** | regression |\n\n"
        + JUDGE_HEAD_PLAIN + ORDER_OK + JUDGE_RUN
    ),
    # A4 的變形:子段那張表第一欄不粗體,一樣不是 lane 宣告
    "g03-a4-non-lane-table-plain": (
        POOL3 + "### 資源分配\n\n| 資源 | 誰用 |\n| --- | --- |\n"
        "| port | walkthrough |\n| fixture | regression |\n\n"
        + JUDGE_HEAD_PLAIN + ORDER_OK + JUDGE_RUN
    ),
    # lane 名不粗體 —— markdown 不要求粗體,三支齊全就該綠
    "g04-lanes-not-bold": (
        "## 2. 並行池\n\n| lane | 做什麼 |\n| --- | --- |\n"
        "| regression | 跑既有 suite |\n| walkthrough | 照驗收原句實測 |\n"
        "| code-review | 讀 diff |\n\n" + JUDGE_HEAD_PLAIN + ORDER_OK + JUDGE_RUN
    ),
    # 順序自由
    "g05-lane-order-shuffled": (
        "## 2. 並行池\n\n| lane | 做什麼 |\n| --- | --- |\n"
        "| **code-review** | 讀 diff |\n| **regression** | 跑既有 suite |\n"
        "| **walkthrough** | 照驗收原句實測 |\n\n"
        + JUDGE_HEAD_PLAIN + ORDER_OK + JUDGE_RUN
    ),
    # #57 假陽性對照組:散文提到 judge,自己一支 judge 都沒跑
    "g06-mentions-judge-only": (
        "## 收尾\n\n獨立 judge 抓 works-but-wrong 是 /qa 那關的事,這片只讀它的結論。\n"
    ),
    # 整份跟 judge 無關
    "g07-no-judge-at-all": "## 做什麼\n\n讀 diff,寫 review,沒有 judge 這回事。\n",
    # 標題含「並行池」以外的字 —— 段落宣告不限定標題只有那三個字
    "g08-heading-decorated": (
        "## 2. 三線並行池(同時開始)\n\n| lane | 做什麼 |\n| --- | --- |\n"
        "| **walkthrough** | 照驗收原句實測 |\n| **regression** | 跑既有 suite |\n"
        "| **code-review** | 讀 diff |\n\n"
        + JUDGE_HEAD_PLAIN + ORDER_OK + JUDGE_RUN
    ),
    # 排序約束寫法不同(「要等…之後」),正文有寫就算
    "g09-ordering-worded-differently": (
        POOL3 + JUDGE_HEAD_PLAIN
        + "獨立 judge 要等 walkthrough 跑完之後才開,不進並行池。\n" + JUDGE_RUN
    ),
    # ---------- 該紅的一面 ----------
    # A1:池裡插一列 judge lane,第一欄不粗體
    "r01-a1-judge-lane-not-bold": (
        "## 2. 並行池\n\n| lane | 做什麼 |\n| --- | --- |\n"
        "| **regression** | 跑既有 suite |\n| **walkthrough** | 照驗收原句實測 |\n"
        "| **code-review** | 讀 diff |\n| judge | 逐條判定 |\n\n"
        + JUDGE_HEAD_PLAIN + ORDER_OK + JUDGE_RUN
    ),
    # A2:正文那句排序約束整句刪掉,只留把關鍵字一起帶著的 §3 標題
    "r02-a2-ordering-only-in-heading": (
        POOL3 + JUDGE_HEAD_LOADED + "judge 逐條判 pass / fail。\n" + JUDGE_RUN
    ),
    # A3:整段並行池拿掉(§3 標題含「並行池」三個字,正是票面說的那個陷阱)
    "r03-a3-no-pool-section": (
        JUDGE_HEAD_LOADED + ORDER_OK + JUDGE_RUN
    ),
    # 既有形狀:judge 混進 lane 表(粗體版)—— #107 指名的失敗形狀,不准鬆掉
    "r04-judge-in-pool-bold": (
        "## 2. 並行池\n\n| lane | 做什麼 |\n| --- | --- |\n"
        "| **regression** | 跑既有 suite |\n| **walkthrough** | 照驗收原句實測 |\n"
        "| **code-review** | 讀 diff |\n| **judge** | 判定 |\n\n"
        + JUDGE_HEAD_PLAIN + ORDER_OK + JUDGE_RUN
    ),
    # 既有形狀:少一支 lane
    "r05-missing-lane": (
        "## 2. 並行池\n\n| lane | 做什麼 |\n| --- | --- |\n"
        "| **regression** | 跑既有 suite |\n| **walkthrough** | 照驗收原句實測 |\n\n"
        + JUDGE_HEAD_PLAIN + ORDER_OK + JUDGE_RUN
    ),
    # 既有形狀:排序反寫
    "r06-ordering-flipped": (
        POOL3 + JUDGE_HEAD_PLAIN
        + "獨立 judge 排在 walkthrough 之前就開,不進並行池。\n" + JUDGE_RUN
    ),
    # 既有形狀:排序被否定
    "r07-ordering-negated": (
        POOL3 + JUDGE_HEAD_PLAIN
        + "獨立 judge 不用等 walkthrough 之後,直接進並行池。\n" + JUDGE_RUN
    ),
    # 既有形狀:三 lane 齊全,排序約束整句不見(標題也不含關鍵字)
    "r08-no-ordering-line": (
        POOL3 + JUDGE_HEAD_PLAIN + "獨立 judge 逐條判定,只餵驗收原句。\n" + JUDGE_RUN
    ),
}
RED = {f for f in FIXTURES if f.startswith("r")}

# A3 的訊息斷言:票面要求訊息指到「整段不見」,不是「lanes are []」。
# 這兩條都是讀票寫的 —— 一條 must、一條 must-not,不抄實作的字串。
MSG_RULES = {
    "r03-a3-no-pool-section": (["並行池 section"], ["lanes are []"]),
}


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


def msg_ok(name, verds):
    must, must_not = MSG_RULES[name]
    blob = " ".join(verds.get(name, []))
    return all(m in blob for m in must) and not any(m in blob for m in must_not)


def table(title, names, vn, vo, expected=None):
    """列一張 修後/修前 對照表,回傳 (不合清單, 差額清單)。"""
    bad, delta = [], []
    print(f"\n==== {title} ====")
    head = f"{'項目':<32}{'修後':<6}{'修前':<6}"
    print(head + ("  QA 期望   判定" if expected else "  判定"))
    for n in names:
        new_red, old_red = n in vn, n in vo
        a = "紅" if new_red else "綠"
        b = "紅" if old_red else "綠"
        line = f"{n:<32}{a:<6}{b:<6}"
        if expected is not None:
            exp = "紅" if n in expected else "綠"
            ok = a == exp
            if ok and n in MSG_RULES:
                ok = msg_ok(n, vn)
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
    new = load("v_new_112", ROOT / "scripts" / "validate.py")
    old = load("v_old_112", prev)

    print(f"修前 = {PREV}(#112 動判斷邏輯之前的最後一個 commit)")

    # ---- (a) 真實母體:現在 repo 裡的 skills/*/SKILL.md ----
    real_dir = ROOT / "skills"
    real = sorted(p.name for p in real_dir.iterdir() if (p / "SKILL.md").is_file())
    rn, ro = verdicts(new, real_dir, ROOT), verdicts(old, real_dir, ROOT)
    for label, v in (("修後", rn), ("修前", ro)):
        if isinstance(v, str):
            print(f"{label}:整支掛掉 —— {v}")
            return 1
    bad_a, delta_a = table(f"(a) 真實母體 —— repo 裡 {len(real)} 支 SKILL.md", real, rn, ro)

    # ---- (b) fixture 母體:QA 讀 #112 票面自己判的期望值 ----
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

    # ---- A3 的訊息:票面要的是「整段不見」,不是 lanes are [] ----
    print("\n==== A3 訊息斷言(票面原句:應該是 `no 並行池 section`,不是 `lanes are []`)====")
    for n in MSG_RULES:
        print(f"  {n}")
        print(f"      修前:{' | '.join(fo.get(n, [])) or '(綠)'}")
        print(f"      修後:{' | '.join(fn.get(n, [])) or '(綠)'}")
        print(f"      判定:{'OK' if msg_ok(n, fn) else '*** 不合 ***'}")

    # ---- 差額判讀 ----
    print(f"\n==== 差額 {len(delta_a) + len(delta_b)} 筆 ====")
    for src, delta, v in (("真實", delta_a, rn), ("fixture", delta_b, fn)):
        for n, o, a in delta:
            print(f"  [{src}] {n}: 修前{o} → 修後{a}")
            for e in v.get(n, []):
                print(f"      {e}")
    # 這張票兩個方向都會動:A4 那格是刻意的放行,其餘放行就是本輪鬆掉
    loosened = [d for d in delta_b if d[1] == "紅" and d[2] == "綠" and d[0] in RED]
    if loosened:
        print(f"  *** 非預期的放行(修前紅 → 修後綠,而 QA 判它該紅):{loosened} ***")
    if delta_a:
        print("  *** 真實母體出現差額 —— 出貨的 SKILL.md 被新錨點改判,逐筆判讀 ***")
    unexpected = [n for n, _, a in delta_b if a == "紅" and n not in RED]
    if unexpected:
        print(f"  *** 非預期的變紅(QA 判該綠卻被新錨點咬到):{unexpected} ***")

    bad = bad_b + [f"real:{n}" for n, _, a in delta_a if a == "紅"]
    total = len(real) + len(FIXTURES)
    print(f"\n母體 {total},不合 {len(bad)}" + (f":{bad}" if bad else ""))
    return 1 if bad or loosened else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        sys.exit(run(pathlib.Path(td)))
