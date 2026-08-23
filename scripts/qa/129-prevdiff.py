"""#129 QA 的修前對照 —— 同一份母體,修前(643f683^)vs 修後(工作區)。

#129 動的是判準,而且動在**入口**:`main` 讀完 JSON 就把整份 payload 的票號收成
int(`normalize_tickets` + `ticket_number` + `NUMBER_LISTS` + `number` + `titles` key
+ `blocked_by`)。入口的正規化 = **收緊**:以前靜靜跑過去的形狀,現在有一部分會
當場停。所以「修後 self-check 綠」證明不了「本來好的批次沒被改壞」——
要真的把修前那份跑起來,逐批比 stdout / stderr / exit code。

母體三面:

  (a) **該被 #129 改到的一面**(`alias`)—— 票號寫成 `"47"` / `" 47 "` 的重複批次,
      以及別的 mode 裡型別混用會靜靜少印標題的批次。修前放行、修後停(或印對),
      預期有差額。沒差額 = 修沒修到。
  (b) **不該被動到的一面**(`clean`)—— 票號本來就是裸整數的各式批次(每個 mode
      各一到數批、空批、單張批、打錯字、硬規則、plan 的 blocked_by、titles 缺 key)。
      修前修後要**逐字相同**。任何差額一律當本輪引入的誤判 -> blocking。
  (c) **收緊面**(`tighten`)—— 修前會靜靜跑過、修後預期停的形狀:`47.0` 小數、
      `number` 是 null、`blocked_by` 裡放非數字、`titles` 壞 key、別的 mode 的
      名單裡放非數字。這一面**不自動判成 OK**:腳本把每一筆「新出現的停」都列出來
      (含這裡宣告的判讀理由),沒宣告過的新停一律算本輪引入 -> blocking。

兩邊都用 subprocess 真的把檔跑起來(不是 import 純函式)—— stdout、stderr、退出碼
是三層不同的東西,只量純函式會漏掉 main() 那一層(#129 的正規化就住在 main)。

用法:
    python 129-prevdiff.py     # clean 面全部逐字相同、alias 面全部有差額、
                               # 新出現的停全部是宣告過的 -> exit 0
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="prevdiff129-"))
BEFORE = _TMP / "batch_before.py"
BEFORE.write_bytes(subprocess.run(
    ["git", "-C", str(ROOT), "show", "643f683^:skills/build-batch/batch.py"],
    check=True, stdout=subprocess.PIPE).stdout)
AFTER = ROOT / "skills" / "build-batch" / "batch.py"   # 工作區(= HEAD 643f683)

T = {"47": "登入頁", "48": "結帳流程", "49": "寄信"}
# spec 那格放的是**票號**,不是連結:它被印進 `/build-batch #{spec}` 這種要 client
# 照抄貼進終端機的下一棒指令(SKILL.md §3 / §7 的範例都給整數)。這裡本來塞的是
# 完整 URL,修前印出來是 `/build-batch #https://github.com/...` —— 那本來就貼不動,
# 只是當時沒有任何一把尺在量它。#130 把 spec 收進入口之後這格會當場停,所以 fixture
# 一起校準成票號(留 URL 的話 c17/c18/c20 三格會把「修對的收緊」誤報成新誤判)。
SPEC = 108


def C(n, cov=None, **kw):
    t = {"number": n, "coverage": cov if cov is not None else []}
    t.update(kw)
    return t


def P(n, blocked_by=(), state="open"):
    """plan 模式的一列 —— 它要的是 `number` / `state` / `blocked_by` 三格。"""
    return {"number": n, "state": state, "blocked_by": list(blocked_by)}


# 每格:(面, 判讀理由, payload)
#   "clean"   -> 修前修後必須逐字相同
#   "alias"   -> 必須有差額(#129 修的那一面)
#   "tighten" -> 宣告過的收緊:修前跑得過、修後停。理由寫在這裡,報告會逐筆印。
CASES = {
    # ---------- (b) 不該被動到的一面:票號本來就是裸整數 ----------
    "c01_classify_normal": ("clean", "", {
        "mode": "classify", "titles": T, "tickets": [C(47), C(48, ["1. x"])]}),
    "c02_classify_empty": ("clean", "", {
        "mode": "classify", "titles": T, "tickets": []}),
    "c03_classify_single": ("clean", "", {
        "mode": "classify", "titles": T, "tickets": [C(47, ["1. 登入頁"])]}),
    "c04_classify_typo": ("clean", "", {
        "mode": "classify", "titles": T,
        "tickets": [C(47, override="fast"), C(48, ["1. x"])]}),
    "c05_classify_judgement": ("clean", "", {
        "mode": "classify", "titles": T,
        "tickets": [C(47, judgement=True, override="快"), C(48, ["1. x"])]}),
    "c06_classify_dupe_int": ("clean", "", {
        "mode": "classify", "titles": T, "tickets": [C(47), C(47, ["1. x"])]}),
    "c07_classify_no_titles": ("clean", "", {
        "mode": "classify", "tickets": [C(47), C(48, ["1. x"])]}),
    "c08_classify_titles_partial": ("clean", "", {
        "mode": "classify", "titles": {"47": "登入頁"},
        "tickets": [C(47), C(99, ["1. x"])]}),
    "c09_plan_plain": ("clean", "", {
        "mode": "plan", "titles": T,
        "tickets": [P(47), P(48, [47]), P(49)]}),
    "c10_plan_blocked_chain": ("clean", "", {
        "mode": "plan", "titles": T,
        "tickets": [P(47), P(48, [47]), P(49, [48])]}),
    "c11_plan_cap_overflow": ("clean", "", {
        "mode": "plan", "titles": T,
        "tickets": [P(n) for n in (47, 48, 49, 50, 51)]}),
    "c26_plan_closed_blocker": ("clean", "", {
        "mode": "plan", "titles": T,
        "tickets": [P(47, state="closed"), P(48, [47]), P(49, [99])]}),
    "c27_titles_key_padded": ("clean",
                              "探針轉正:`titles` 的 key 修前就是 `int(k)`,而 "
                              "`int(\" 47 \")` 本來就吃得掉空白 —— #129 在這格"
                              "改的只有『壞 key 從裸 traceback 變成有聲的停』"
                              "(見 t06),好 key 的行為逐字沒動。", {
        "mode": "classify", "titles": {" 47 ": "登入頁"}, "tickets": [C(47)]}),
    "c12_split": ("clean", "", {
        "mode": "split", "numbers": [47, 48], "fixing": [48], "titles": T}),
    "c13_split_none_fixing": ("clean", "", {
        "mode": "split", "numbers": [47, 48], "fixing": [], "titles": T}),
    "c14_start": ("clean", "", {
        "mode": "start", "numbers": [47, 48], "running": [47], "titles": T}),
    "c15_done": ("clean", "", {"mode": "done", "numbers": [47], "titles": T}),
    "c16_refill": ("clean", "", {
        "mode": "refill", "running": [47], "queue": [48, 49], "titles": T}),
    "c17_interrupted": ("clean", "", {
        "mode": "interrupted", "numbers": [47, 48], "titles": T, "spec": SPEC}),
    "c18_merged": ("clean", "", {
        "mode": "merged", "numbers": [47, 48], "fixing": [48],
        "titles": T, "spec": SPEC}),
    "c19_fixing": ("clean", "", {
        "mode": "fixing", "number": 48, "numbers": [47, 48], "fixing": [48],
        "titles": T}),
    "c20_summary": ("clean", "", {
        "mode": "summary", "spec": SPEC, "numbers": [47, 48], "fixing": [],
        "titles": T, "coverage": {"47": ["1. x"]}}),
    "c21_conflict_resolved": ("clean", "", {
        "mode": "conflict-resolved", "numbers": [47], "titles": T,
        "files": ["a.py"], "how": "留兩邊"}),
    "c22_conflict_stopped": ("clean", "", {
        "mode": "conflict-stopped", "numbers": [47], "titles": T,
        "files": ["a.py"], "merged": [47], "pending": [48]}),
    "c23_resume": ("clean", "", {
        "mode": "resume", "worktrees": "wt-47\nwt-48\n", "titles": T}),
    "c24_unknown_mode": ("clean", "", {"mode": "nope", "titles": T}),
    "c25_classify_big_numbers": ("clean", "", {
        "mode": "classify", "titles": T, "tickets": [C(7), C(1234, ["1. x"])]}),

    # ---------- (a) #129 該修到的一面 ----------
    "a01_dupe_str_vs_int": ("alias", "", {
        "mode": "classify", "titles": T,
        "tickets": [C(47), C("47", ["1. x"])]}),
    "a02_dupe_spaces": ("alias", "", {
        "mode": "classify", "titles": T,
        "tickets": [C(" 47 "), C(47, ["1. x"])]}),
    "a03_dupe_all_str": ("alias", "", {
        "mode": "classify", "titles": T,
        "tickets": [C("47"), C("47", ["1. x"])]}),
    "a04_split_number_str": ("alias", "", {
        "mode": "split", "numbers": [47, "48"], "fixing": ["48"], "titles": T}),
    "a05_start_number_str": ("alias", "", {
        "mode": "start", "numbers": ["47", 48], "running": [], "titles": T}),
    # 卡關的那張要**已經收掉**才看得出差別:blocker 還開著的話兩邊都判「還卡著」,
    # 對不上的 key 被同一個答案蓋過去。收掉之後修前讀成「沒見過的票號」照樣卡,
    # 修後認得出來 -> #48 進「要開」。
    "a06_plan_blocked_by_str": ("alias", "", {
        "mode": "plan", "titles": T,
        "tickets": [P(47, state="closed"), P(48, ["47"])]}),
    "a07_start_number_padded": ("alias", "", {
        "mode": "start", "numbers": [" 47 ", 48], "running": [], "titles": T}),
    "a08_fixing_number_str": ("alias", "", {
        "mode": "fixing", "number": "48", "numbers": [47, 48], "fixing": [48],
        "titles": T}),
    "a09_refill_queue_str": ("alias", "", {
        "mode": "refill", "running": ["47"], "queue": ["48"], "titles": T}),
    "a10_conflict_stopped_str": ("alias", "", {
        "mode": "conflict-stopped", "numbers": ["47"], "titles": T,
        "files": ["a.py"], "merged": ["47"], "pending": ["48"]}),

    # ---------- (c) 收緊面:修前靜靜跑過、修後預期停 ----------
    "t01_float_47_0": ("tighten",
                       "宣告過的天花板(票上 code-review「47.0 被誤傷」那條:不收)。"
                       "放行整數值的小數就得在入口開型別特例,正是這條路要拆的。"
                       "停是有聲的,訊息講得出他填了什麼。", {
        "mode": "classify", "titles": T, "tickets": [C(47.0), C(48, ["1. x"])]}),
    "t02_float_47_9": ("tighten",
                       "修對的收緊:修前 47.9 自成一張票、靜靜印成 #47.9;"
                       "現在當場停。捨小數會靜靜換成別張票,停才是對的。", {
        "mode": "classify", "titles": T, "tickets": [C(47.9)]}),
    "t03_number_null": ("tighten",
                        "修對的收緊:修前 `null` 一路印成 `#None`(client 讀到一張"
                        "不存在的票);現在當場停並指名是第幾列。", {
        "mode": "classify", "titles": T, "tickets": [C(None), C(48, ["1. x"])]}),
    "t04_number_str_words": ("tighten",
                             "修對的收緊:修前 `'四十七'` 靜靜印成 `#四十七`;"
                             "現在停,訊息指名第幾列 + 他填了什麼,沒有 traceback。", {
        "mode": "classify", "titles": T, "tickets": [C("四十七")]}),
    "t05_blocked_by_words": ("tighten",
                             "修對的收緊:plan 模式比的就是 number / blocked_by "
                             "兩份名單,非數字的 blocked_by 修前會讓那張被讀成"
                             "「卡在一個沒見過的票號後面」,永遠排不進去。", {
        "mode": "plan", "titles": T,
        "tickets": [P(47), P(48, ["四十七"])]}),
    "t06_titles_bad_key": ("tighten",
                           "修對的收緊:`titles` 的 key 修前是裸 `int(k)`,壞 key "
                           "直接裸 traceback;現在走同一支 `ticket_number`,"
                           "有聲地停並指名。", {
        "mode": "classify", "titles": {"四七": "登入頁"}, "tickets": [C(47)]}),
    "t07_titles_float_key": ("tighten",
                             "同 t01 的天花板,換到 `titles` 這一格:'47.0' "
                             "當 key 修前一樣是裸 traceback,現在是有聲的停。", {
        "mode": "classify", "titles": {"47.0": "登入頁"}, "tickets": [C(47)]}),
    "t08_numbers_list_words": ("tighten",
                               "修對的收緊:`numbers` 名單裡的非數字修前一路帶到"
                               "查表,靜靜少印一個標題;現在停並指名是哪份名單。", {
        "mode": "split", "numbers": [47, "四八"], "fixing": [], "titles": T}),
    "t09_pending_list_words": ("tighten",
                               "同 t08,換到 `pending` 那份名單 —— `NUMBER_LISTS` "
                               "六格走同一支,這格證明不是只收了 `numbers`。", {
        "mode": "conflict-stopped", "numbers": [47], "titles": T,
        "files": ["a.py"], "merged": [47], "pending": ["四八"]}),
    "t10_number_field_words": ("tighten",
                               "同上,換到 `number` 那格(fixing 模式)。修前它會"
                               "拿去跟 fixing 名單比,比不上就報「不在 fixing 裡」"
                               "—— 訊息指錯方向。", {
        "mode": "fixing", "number": "四八", "numbers": [47, 48],
        "fixing": [48], "titles": T}),
}


_PATHNOISE = re.compile(r'File "[^"]+", line \d+')


def scrub(text):
    """把 traceback 裡的檔路徑與行號換成佔位符再比。

    修前那份住在 temp、修後住在工作區,行號又被新函式整段推移 —— 不掃掉的話
    「兩邊同樣是裸 traceback」會被誤判成本輪引入的差額。例外型別與訊息照比。
    """
    return _PATHNOISE.sub('File "<batch.py>", line <n>', text)


def run(script, payload):
    """真的把檔跑起來 —— 回傳 (exit code, stdout, stderr),crash 照實記,不吞。"""
    p = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return (p.returncode,
            scrub(p.stdout.decode("utf-8", "replace")),
            scrub(p.stderr.decode("utf-8", "replace")))


def block(label, res):
    rc, out, err = res
    lines = [f"    --- {label} exit={rc}"]
    lines += [f"    | {l}" for l in (out.rstrip("\n").splitlines() or ["(空)"])]
    if err.strip():
        lines += [f"    !err {l}" for l in err.rstrip("\n").splitlines()]
    return "\n".join(lines)


def main():
    print(f"修前 = 643f683^ 的 skills/build-batch/batch.py -> {BEFORE}")
    print(f"修後 = 工作區 {AFTER}\n")
    sides = {}
    for side, _, _ in CASES.values():
        sides[side] = sides.get(side, 0) + 1
    print(f"母體 {len(CASES)} 批("
          + "、".join(f"{k} {v}" for k, v in sorted(sides.items())) + ")\n")

    deltas, bad, new_stops = [], [], []
    print(f"{'批次':<28}{'面':<10}{'修前':<10}{'修後':<10}判定")
    for name, (side, why, payload) in CASES.items():
        old, new = run(BEFORE, payload), run(AFTER, payload)
        changed = old != new
        if changed:
            deltas.append((name, side, why, old, new))
        # 「新出現的停」= 修前 exit 0、修後非 0。不管它落在哪一面,一律列出來。
        if old[0] == 0 and new[0] != 0:
            new_stops.append((name, side, why, old, new))
        if side == "clean":
            ok = not changed
        elif side == "alias":
            ok = changed
        else:                              # tighten:宣告過會停,就要真的停
            ok = changed and new[0] != 0
        if not ok:
            bad.append(name)
        print(f"{name:<28}{side:<10}{('exit ' + str(old[0])):<10}"
              f"{('exit ' + str(new[0])):<10}"
              f"{('OK' if ok else '*** 不合 ***'):<14}"
              f"{'  [有差額]' if changed else '  [逐字相同]'}")

    print(f"\n==== 差額 {len(deltas)} 筆(逐筆原文)====")
    for name, side, why, old, new in deltas:
        verdict = {"clean": "*** 本輪引入的新誤判 —— blocking ***",
                   "alias": "預期內(#129 要修的那一面)",
                   "tighten": "收緊(宣告過)"}[side]
        print(f"\n  [{name}] {verdict}")
        if why:
            print(f"    判讀:{why}")
        print(block("修前", old))
        print(block("修後", new))
    if not deltas:
        print("  (無)")

    print(f"\n==== 本輪新出現的停(修前 exit 0 -> 修後非 0){len(new_stops)} 筆 ====")
    print("每一筆都要判讀是「修對的收緊」還是 regression:\n")
    for name, side, why, old, new in new_stops:
        tag = ("修對的收緊 / 宣告過的天花板" if side == "tighten" else
               "#129 要修的那一面(重複票號 alias)" if side == "alias" else
               "*** 沒宣告過 —— 當 regression 處理 ***")
        print(f"  [{name}] {tag}")
        print(f"    判讀:{why or '(見上面的面別)'}")
        print(f"    修後 stderr:{new[2].strip()!r}")
        if "Traceback" in new[2]:
            print("    *** 修後 stderr 有 Traceback —— 不是有聲的停 ***")
            bad.append(name + "(修後裸 traceback)")
        print()
    if not new_stops:
        print("  (無)")

    print(f"\n母體 {len(CASES)},不合 {len(bad)}" + (f":{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    sys.exit(main())
