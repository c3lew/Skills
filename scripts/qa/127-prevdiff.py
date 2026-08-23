"""#127 QA 的修前對照 —— 同一份母體,修前(7c4754a^)vs 修後(工作區)的 classify。

#127 動的是判準:`classify_tickets` / `format_classify` / `main` 都改了。動判準
會改變同一份母體的行為,所以「新規則自己的 self-check 綠」證明不了「本來好的批次
沒被改壞」。母體兩面都寫:

  (a) **該被 #127 改到的一面** —— 有重複票號的批次。修前靜靜印兩列矛盾分級、
      exit 0;修後要當場停。
  (b) **不該被動到的一面** —— 沒有重複票號的批次(正常批、空批、單張批、
      純打錯字、純硬規則、titles 缺 key)。修前修後要**逐字相同**,
      stdout / stderr / exit code 三者都是。任何差額一律當本輪引入的誤判。

兩邊都用 subprocess 真的把檔跑起來(不是 import 純函式)—— 抬頭那句、stderr
那句、退出碼是三個不同層的東西,只量純函式會漏掉 main() 那一層。

用法:
    python 127-prevdiff.py        # 差額全部落在「有重複票號」那一面才 exit 0
"""
import json
import os
import pathlib
import tempfile
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="prevdiff127-"))
BEFORE = _TMP / "batch_before.py"
BEFORE.write_bytes(subprocess.run(
    ["git", "-C", str(ROOT), "show", "7c4754a^:skills/build-batch/batch.py"],
    check=True, stdout=subprocess.PIPE).stdout)
AFTER = ROOT / "skills" / "build-batch" / "batch.py"   # 工作區(= HEAD 7c4754a)


def C(n, cov=None, **kw):
    t = {"number": n, "coverage": cov if cov is not None else []}
    t.update(kw)
    return t


T = {"47": "登入頁", "48": "結帳流程", "49": "寄信"}

# has_dupe = QA 讀票面判「這批該不該被 #127 動到」。判準是散文,不是實作:
# #127 票面只講「同一個票號在一批裡出現兩次」,別的形狀都不該變。
CASES = {
    # ---------- (b) 不該被動到的一面 ----------
    "b01_normal_two": (False, {"mode": "classify", "titles": T, "tickets": [
        C(47), C(48, ["1. 登入頁"])]}),
    "b02_normal_five": (False, {"mode": "classify", "titles": T, "tickets": [
        C(47), C(48, ["1. x"]), C(49, ["2. y"]), C(50), C(51, ["3. z"])]}),
    "b03_empty": (False, {"mode": "classify", "titles": T, "tickets": []}),
    "b04_single_fast": (False, {"mode": "classify", "titles": T, "tickets": [C(47)]}),
    "b05_single_slow": (False, {"mode": "classify", "titles": T,
                                "tickets": [C(47, ["1. 登入頁"])]}),
    "b06_no_titles_key": (False, {"mode": "classify", "tickets": [
        C(47), C(48, ["1. x"])]}),
    "b07_titles_partial": (False, {"mode": "classify", "titles": {"47": "登入頁"},
                                   "tickets": [C(47), C(48, ["1. x"]), C(99)]}),
    "b08_titles_empty": (False, {"mode": "classify", "titles": {}, "tickets": [
        C(47, ["1. x"]), C(48)]}),
    # 純打錯字(override 不是「快」/「慢」)—— #118 那條路,#127 不該碰
    "b09_typo_only": (False, {"mode": "classify", "titles": T, "tickets": [
        C(47, override="fast"), C(48, ["1. x"])]}),
    # 純硬規則(judgement true + override)—— #120 那條路
    "b10_judgement_only": (False, {"mode": "classify", "titles": T, "tickets": [
        C(47, judgement=True, override="快"), C(48, ["1. x"])]}),
    # 打錯字 + 硬規則兩張混在同一批,仍然沒有重複票號
    "b11_typo_and_judgement": (False, {"mode": "classify", "titles": T, "tickets": [
        C(47, override="fast"), C(48, judgement=True, override="快"),
        C(49, ["1. x"])]}),
    # 合法 override(judgement false)—— 該通過那條
    "b12_legit_override": (False, {"mode": "classify", "titles": T, "tickets": [
        C(47, override="慢"), C(48)]}),
    # 票號不是連號 / 大票號 —— 排版那面的對照組
    "b13_wide_numbers": (False, {"mode": "classify", "titles": T, "tickets": [
        C(7), C(1234, ["1. x"])]}),

    # ---------- (a) 該被 #127 改到的一面 ----------
    "a01_dupe_pair": (True, {"mode": "classify", "titles": T, "tickets": [
        C(47), C(47, ["1. 登入頁"])]}),
    "a02_dupe_triple": (True, {"mode": "classify", "titles": T, "tickets": [
        C(47), C(47, ["1. x"]), C(47)]}),
    "a03_dupe_identical": (True, {"mode": "classify", "titles": T, "tickets": [
        C(47), C(47)]}),
    "a04_dupe_plus_typo": (True, {"mode": "classify", "titles": T, "tickets": [
        C(9, override="fast"), C(9, ["1. x"])]}),
    "a05_dupe_plus_judgement": (True, {"mode": "classify", "titles": T, "tickets": [
        C(47, judgement=True, override="快"), C(47, ["1. x"])]}),
    "a06_dupe_and_clean_mix": (True, {"mode": "classify", "titles": T, "tickets": [
        C(47), C(48, ["1. x"]), C(47), C(49)]}),
    "a07_two_different_dupes": (True, {"mode": "classify", "titles": T, "tickets": [
        C(47), C(48), C(47, ["1. x"]), C(48, ["2. y"])]}),
    "a08_dupe_non_adjacent": (True, {"mode": "classify", "titles": T, "tickets": [
        C(47), C(48, ["1. x"]), C(49, ["2. y"]), C(47, ["3. z"])]}),
    "a09_dupe_no_title": (True, {"mode": "classify", "titles": {}, "tickets": [
        C(88), C(88, ["1. x"])]}),
    "a10_dupe_plus_separate_typo": (True, {"mode": "classify", "titles": T, "tickets": [
        C(47), C(47), C(48, override="fast")]}),
    # 票號型別不一致(JSON 手打,"47" 跟 47 都寫得出來)—— 探針,不是票面要求的
    "a11_dupe_str_vs_int": (True, {"mode": "classify", "titles": T, "tickets": [
        C(47), C("47", ["1. x"])]}),
}
# 探針:票面沒要求、QA 想知道現況的格。判定不計入不合,只印出來。
PROBES = {"a11_dupe_str_vs_int"}


def run(script, payload):
    """真的把檔跑起來 —— 回傳 (exit code, stdout, stderr),crash 照實記,不吞。"""
    p = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def block(label, res):
    rc, out, err = res
    lines = [f"    --- {label} exit={rc}"]
    lines += [f"    | {l}" for l in (out.rstrip("\n").splitlines() or ["(空)"])]
    if err.strip():
        lines += [f"    !err {l}" for l in err.rstrip("\n").splitlines()]
    return "\n".join(lines)


def main():
    print(f"修前 = 7c4754a^ 的 skills/build-batch/batch.py -> {BEFORE}")
    print(f"修後 = 工作區 {AFTER}")
    print(f"母體 {len(CASES)} 批"
          f"(有重複票號 {sum(1 for h, _ in CASES.values() if h)}、"
          f"沒有 {sum(1 for h, _ in CASES.values() if not h)})\n")

    deltas, bad = [], []
    print(f"{'批次':<28}{'該不該變':<10}{'修前':<12}{'修後':<12}判定")
    for name, (has_dupe, payload) in CASES.items():
        old, new = run(BEFORE, payload), run(AFTER, payload)
        changed = old != new
        # 沒有重複票號的批次:三者都要逐字相同。變了就是本輪引入的誤判。
        # 有重複票號的批次:一定要變,而且修後一定要停(非 0 退出)。修前是不是
        # exit 0 分兩種:整批只有重複問題 -> 修前 exit 0(#127 講的安靜失敗);
        # 同一批裡另外還有打錯字 / 硬規則 -> 修前本來就被 #118 那條路擋下了。
        # 兩種都算預期內,下面另外列出是哪幾批。
        if has_dupe:
            ok = changed and new[0] != 0
        else:
            ok = not changed
        if changed:
            deltas.append((name, has_dupe, old, new))
        if not ok and name not in PROBES:
            bad.append(name)
        print(f"{name:<28}{'該變' if has_dupe else '不該變':<10}"
              f"{('exit ' + str(old[0])):<12}{('exit ' + str(new[0])):<12}"
              f"{('探針' if name in PROBES else ('OK' if ok else '*** 不合 ***')):<14}"
              f"{'  [有差額]' if changed else '  [逐字相同]'}")

    print(f"\n==== 差額 {len(deltas)} 筆(逐筆原文)====")
    for name, has_dupe, old, new in deltas:
        verdict = ("探針(票面沒要求,只記現況)" if name in PROBES else
                   "預期內(#127 要修的那一面)" if has_dupe else
                   "*** 本輪引入的新誤判 —— blocking ***")
        print(f"\n  [{name}] {verdict}")
        print(block("修前", old))
        print(block("修後", new))
    if not deltas:
        print("  (無)")

    silent = [n for n, h, o, _ in deltas if h and o[0] == 0 and n not in PROBES]
    noisy = [n for n, h, o, _ in deltas if h and o[0] != 0 and n not in PROBES]
    print(f"\n  修前 exit 0(#127 講的安靜失敗,這次修掉的就是這些):{silent}")
    print(f"  修前就非 0(同批另有打錯字 / 硬規則,#118 那條路本來就擋):{noisy}")
    print("\n==== 探針的現況(不計入判定)====")
    for n in sorted(PROBES):
        d = [x for x in deltas if x[0] == n]
        print(f"  {n}: "
              + ("修前修後有差額" if d else "修前修後逐字相同 —— #127 沒碰到這個形狀"))
        print(block("現況(修後)", run(AFTER, CASES[n][1])))
    print(f"\n母體 {len(CASES)},不合 {len(bad)}" + (f":{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    sys.exit(main())
