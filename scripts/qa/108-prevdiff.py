"""#108 QA 的修前對照 —— 同一份母體,修前(8b91db1^ = e643c09)vs 修後的守門判定。

這張票在 `scripts/validate.py` 新增 `grade_line_issues`(釘分級行格式、外加「呼叫
classify 卻沒示範過那一行」),也就是**動判準**。動判準會改變守門對同一份母體的
判定,所以「新規則自己的 self-check 綠」證明不了「出貨的檔沒被新規則誤紅」——
母體兩面都跑修前 / 修後各一次,逐筆列差額。

母體兩面:
  (a) **真實母體** —— 現在 repo 裡 `skills/*/SKILL.md` 全部,加上 main() 那三支
      repo-wide 檢查(handoff / pasteable / stream encoding)。修前綠的變紅一律
      當「本輪引入」,逐筆判讀。
  (b) **fixture 母體** —— QA 讀 #108 票面與 `slice-tickets/SKILL.md` §4 原句自己
      判的該綠 / 該紅。期望值的依據是散文,不是新版 `grade_line_issues` 的實作。

期望值的唯一依據 = `skills/slice-tickets/SKILL.md` §4 的原句:
  「格式固定是『分級:<快或慢> — 一句理由』」
  「它由 batch.py 印出來、守門釘著,不要自己改寫措辭 —— 下游要拿這一行認車道,
    漂掉就認不出來」
  以及票面「呼叫了 batch.py 的 classify 卻整份文件沒示範過那一行 → agent 會現場發明」。

用法:
    python scripts/qa/108-prevdiff.py        # 母體不合 0 才算過
"""
import importlib.util
import pathlib
import subprocess
import sys
import tempfile

PREV = "8b91db1^"          # #108 動判準之前的那個 commit
ROOT = pathlib.Path(__file__).resolve().parents[2]

FM = "---\nname: {name}\ndescription: fixture for #108 prevdiff\n---\n\n"
CLASSIFY = (
    "```bash\n"
    "python batch.py <<" + "'JSON'\n"
    '{"mode": "classify", "tickets": []}\n'
    "JSON\n"
    "```\n\n"
)
GOOD = "分級:慢 — 覆蓋 2 條驗收項\n"

FIXTURES = {
    # ---------- 該綠的一面 ----------
    "g01-good-slow": GOOD,
    "g02-good-fast": "分級:快 — 沒有覆蓋驗收項,不會有你看得到的行為\n",
    "g03-no-grade-at-all": "## 做什麼\n\n這份文件跟分級這回事無關,一行都沒寫。\n",
    "g04-classify-with-demo": CLASSIFY + "貼進票 body 的那一行:\n\n" + GOOD,
    # §4 原句只釘「一句理由」非空,沒說理由要多長 / 寫什麼
    "g05-long-reason": "分級:慢 — 覆蓋 1. 切票時標快慢、2. 整批給 client 點頭,兩條都要演\n",
    # 行首 ≤3 空白仍是同一行(markdown 允許),不是格式漂掉
    "g06-indented-3-spaces": "   " + GOOD,
    # 只是散文提到「分級」兩個字,不是分級行(對照組:別把講話的散文判紅)
    "g07-prose-mentions-grade": "這關要判快慢分級,判準由 batch.py 算。\n",

    # ---------- 該紅的一面(§4 原句「格式固定」的每一種漂法)----------
    # 冒號漂成全形 / 表意變體 —— 「半形冒號」是 §4 原句釘死的形狀,寫成
    # 跳脫碼免得檔案本身被編輯器正規化回半形(第一版 fixture 就是這樣自己漂掉的)
    "r01-fullwidth-colon": "分級：慢 — 覆蓋 2 條驗收項\n",
    "r01b-presentation-colon": "分級︰慢 — 覆蓋 2 條驗收項\n",
    "r02-third-lane": "分級:中 — 說不準\n",
    "r03-no-dash": "分級:慢 覆蓋 2 條驗收項\n",
    "r04-hyphen-not-emdash": "分級:慢 - 覆蓋 2 條驗收項\n",
    "r05-no-space-around-dash": "分級:慢—覆蓋 2 條驗收項\n",
    "r06-empty-reason": "分級:慢 — \n",
    "r07-english-lane": "分級:slow — 覆蓋 2 條驗收項\n",
    "r08-classify-without-demo": CLASSIFY + "照印出來的那一行貼進票就好。\n",
    # 一份文件同時有對的與漂掉的:漂掉那行照樣要紅(不能被對的那行救掉)
    "r09-good-plus-bad": GOOD + "分級:中 — x\n",
}
RED = {f for f in FIXTURES if f.startswith("r")}

# 訊息斷言:兩個方向要指得出是哪一種,不能都吐同一句
MSG_RULES = {
    "r02-third-lane": (["分級行格式不對"], []),
    "r08-classify-without-demo": (["發明"], []),
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


def repo_wide(mod):
    """main() 那三支不吃 skills_dir 的檢查 —— 一起對照,免得差額漏在母體外。"""
    try:
        return sorted(mod.handoff_target_issues(ROOT / "skills")
                      + mod.pasteable_command_issues(ROOT)
                      + mod.stream_encoding_issues(ROOT))
    except Exception as exc:
        return [f"{type(exc).__name__}: {exc}"]


def msg_ok(name, verds):
    must, must_not = MSG_RULES[name]
    blob = " ".join(verds.get(name, []))
    return all(m in blob for m in must) and not any(m in blob for m in must_not)


def table(title, names, vn, vo, expected=None):
    bad, delta = [], []
    print(f"\n==== {title} ====")
    head = f"{'項目':<34}{'修後':<6}{'修前':<6}"
    print(head + ("  QA 期望   判定" if expected else "  判定"))
    for n in names:
        new_red, old_red = n in vn, n in vo
        a = "紅" if new_red else "綠"
        b = "紅" if old_red else "綠"
        line = f"{n:<34}{a:<6}{b:<6}"
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
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", PREV],
                         capture_output=True, check=True, text=True).stdout.strip()
    prev.write_bytes(subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{PREV}:scripts/validate.py"],
        capture_output=True, check=True).stdout)
    new = load("v_new_108", ROOT / "scripts" / "validate.py")
    old = load("v_old_108", prev)
    print(f"修前 = {PREV} = {sha}(#108 動判準之前的那個 commit)")
    print("修後 = 工作區的 scripts/validate.py")
    print(f"修前有 grade_line_issues:{hasattr(old, 'grade_line_issues')}")
    print(f"修後有 grade_line_issues:{hasattr(new, 'grade_line_issues')}")

    # ---- (a) 真實母體 ----
    real_dir = ROOT / "skills"
    real = sorted(p.name for p in real_dir.iterdir() if (p / "SKILL.md").is_file())
    rn, ro = verdicts(new, real_dir, ROOT), verdicts(old, real_dir, ROOT)
    for label, v in (("修後", rn), ("修前", ro)):
        if isinstance(v, str):
            print(f"{label}:整支掛掉 —— {v}")
            return 1
    bad_a, delta_a = table(f"(a) 真實母體 —— repo 裡 {len(real)} 支 SKILL.md", real, rn, ro)

    # ---- (a2) repo-wide 三支 ----
    wn, wo = repo_wide(new), repo_wide(old)
    print("\n==== (a2) repo-wide(handoff / pasteable / stream-encoding)====")
    print(f"修前 {len(wo)} 條、修後 {len(wn)} 條")
    for e in sorted(set(wn) - set(wo)):
        print(f"  + 新出現:{e}")
    for e in sorted(set(wo) - set(wn)):
        print(f"  - 消失:{e}")
    if not (set(wn) ^ set(wo)):
        print("  差額 0 —— 這張票沒有動到這三支")

    # ---- (b) fixture 母體 ----
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

    print("\n==== 訊息斷言(兩個方向要指得出是哪一種)====")
    for n in MSG_RULES:
        print(f"  {n}")
        print(f"      修前:{' | '.join(fo.get(n, [])) or '(綠)'}")
        print(f"      修後:{' | '.join(fn.get(n, [])) or '(綠)'}")
        print(f"      判定:{'OK' if msg_ok(n, fn) else '*** 不合 ***'}")

    print(f"\n==== 差額 {len(delta_a) + len(delta_b)} 筆(逐筆)====")
    for src, delta, v in (("真實", delta_a, rn), ("fixture", delta_b, fn)):
        for n, o, a in delta:
            print(f"  [{src}] {n}: 修前{o} → 修後{a}")
            for e in v.get(n, []):
                print(f"      {e}")
    if not (delta_a or delta_b):
        print("  (無)")
    loosened = [d for d in delta_b if d[1] == "紅" and d[2] == "綠" and d[0] in RED]
    if loosened:
        print(f"  *** 非預期的放行:{loosened} ***")
    if delta_a:
        print("  *** 真實母體出現差額 —— 出貨的 SKILL.md 被新判準改判,逐筆判讀 ***")
    unexpected = [n for n, _, a in delta_b if a == "紅" and n not in RED]
    if unexpected:
        print(f"  *** 非預期的變紅(QA 判該綠卻被新判準咬到):{unexpected} ***")

    bad = bad_b + [f"real:{n}" for n, _, a in delta_a if a == "紅"]
    total = len(real) + len(FIXTURES)
    print(f"\n母體 {total},不合 {len(bad)}" + (f":{bad}" if bad else ""))
    return 1 if bad or loosened else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        sys.exit(run(pathlib.Path(td)))
