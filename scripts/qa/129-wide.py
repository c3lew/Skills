"""#129 的第二把尺 —— 刻意寫寬,不 import / 不套 batch.py 的任何規則。

受測物自己就是判準:它自己判一格票號合不合法、自己判有沒有重複。只跑
`--self-check` 綠,證明的是「它同意自己」。所以這支把 `batch.py` 當黑盒子:
只用 subprocess 餵 JSON、讀 stdout / stderr / exit code,票號怎麼算**自己從
JSON 母體算**,再跟實際行為對照。

`127-wide.py` 已經蓋掉「重複票號」那一面(它的 wide key 就是 `str(number).strip()`)。
這支蓋的是 #129 **新開出來的合約面**:票號的型別在入口收斂之後,對 client 承諾的
是什麼。判準是驗收原句 + #129 票上的 AC,不是程式碼:

- N1  `"47"` / `" 47 "` / `47` 是同一張 #47 —— 相異票號數自己算,抬頭的「N 張」要對得上;
      有重複 -> exit 非 0。
- N2  清單上印出來的票號一律是**裸整數**(`#47`,不是 `#'47'` / `# 47 ` / `#47.0`)。
- N3  左欄與貼票行不歪 —— 每一列 `#` 之前那一段的**顯示欄寬**都一樣。這支自己用
      east-asian width 算(不是數 `len()`),因為「快」「慢」是全形。
- N4  票號轉不成整數 -> exit 非 0、stderr **沒有 `Traceback`**、訊息裡出現他填的那個值。
- N5  別的 mode(split / start / refill / merged / summary…)的票號名單走同一關:
      型別混用不會靜靜少印標題 —— titles 表裡有的標題,stdout 上就要看得到。
- N6  `blocked_by` 兩邊 key 對得起來:plan 的三段(要開 / 排隊 / 還卡著)由這支自己
      照散文算一遍(blocker 還開著、或整批裡根本沒見過 -> 卡著),再跟印出來的對。
- N7  沒有重複、票號都合法 -> exit 0 且貼票段行數 == 列數。

**寬在哪**:這支認「看起來像票號的東西」比受測物寬 —— 除了 `int(str(x).strip())`
之外,整數值的小數(`47.0`、`"47.0"`)也算同一張 #47。受測物在那裡是停的(票上
code-review 明講「`47.0` 被誤傷」不收,列為宣告過的天花板)。寬的那面撈出來的
多餘項**不自動判成 bug**,逐筆列在輸出最後等人判讀。另外附兩組探針(`"+47"`、
全形 `"４７"`),它們兩把尺都認得,列出來當寬度的下界證明。

用法:
    python 129-wide.py                 # 全跑
    python 129-wide.py --quick         # 只跑 1~2 列的批次
"""
import itertools
import json
import pathlib
import re
import subprocess
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[2]
BATCH = ROOT / "skills" / "build-batch" / "batch.py"

CAP = 3          # 同時最多開幾張 —— 散文寫死的名額,這支自己記一份

HEAD_RE = re.compile(r"^分級\(([^)]*)\)")
# 一列分級:兩個空白 + 左欄(補到同寬)+ 兩個空白 + #票號 …… ` — ` 理由
ROW_RE = re.compile(r"^( *\S* *)#(\S+?)(?: (.*?))? — (.*)$")
PASTE_RE = re.compile(r"^ +#(\S+) +分級")
BLOCKED_RE = re.compile(r"^ {2}#(\S+?)(?: .*)?$")
# stdout 上一個 `#` 後面接的那一串 —— 標點與括號不算票號的一部分(輸出裡全形
# 半形都有,兩種都要斷開),N2 / N5 掃的就是這個。
HASH_RE = re.compile(r"#([^\s`()（）,，。：;；、「」]+)")


def cols(text):
    """顯示欄寬(全形算 2)。這支自己的尺 —— 不 import 受測物那支。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def strict_num(raw):
    """受測物那條路預期認得的票號:`int(str(x).strip())`,認不得回 None。"""
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def wide_num(raw):
    """**這支自己的**、刻意更寬的票號判準,認不得回 None。

    比受測物多認一種:整數值的小數(`47.0` / `"47.0"`)。在 client 眼裡那還是
    #47,受測物在那裡是停的。差異出來的那幾筆是這支的主要產出,不自動判 bug。
    """
    n = strict_num(raw)
    if n is not None:
        return n
    try:
        f = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return int(f) if f == int(f) else None


def run(payload):
    p = subprocess.run(
        [sys.executable, str(BATCH)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True)
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def parse_classify(out):
    """(抬頭括號內容, [(左欄前綴, 票號, 理由)], [貼票票號], [還不能貼的票號])"""
    lines = out.splitlines()
    head = HEAD_RE.match(lines[0]).group(1) if lines and HEAD_RE.match(lines[0]) else ""
    rows, pastes, blocked = [], [], []
    in_list = False
    for ln in lines[1:]:
        if ln.startswith("這批還不能貼"):
            in_list = True
            continue
        if ln.startswith("點頭之後"):
            in_list = False
            continue
        m = PASTE_RE.match(ln)
        if m:
            pastes.append(m.group(1))
            continue
        m = ROW_RE.match(ln)
        if m:
            rows.append((m.group(1), m.group(2), m.group(4)))
            continue
        if in_list:
            m = BLOCKED_RE.match(ln)
            if m:
                blocked.append(m.group(1))
    return head, rows, pastes, blocked


def head_counts(head):
    """抬頭括號裡的 `{量詞: 數字}`,例如 `2 張、3 列` -> {'張': 2, '列': 3}。"""
    out = {}
    for v, q in re.findall(r"(\d+)\s*([張列])", head):
        out.setdefault(q, int(v))
    return out


def my_plan(tickets):
    """散文那條規則,這支自己算一遍:(要開, 排隊, [(票號, [還卡著的 blocker])])。

    「blocker 還開著、或整批裡根本沒見過」都算卡著 —— 看不到它收掉就不能猜它收了。
    票號一律先過 `wide_num`,兩份名單因此用同一種 key 比(#129 的合約面)。
    """
    known = {wide_num(t["number"]) for t in tickets}
    still_open = {wide_num(t["number"]) for t in tickets if t["state"] == "open"}
    ready, blocked = [], []
    for t in sorted((t for t in tickets if t["state"] == "open"),
                    key=lambda t: wide_num(t["number"])):
        n = wide_num(t["number"])
        stuck = [wide_num(b) for b in t.get("blocked_by", [])
                 if wide_num(b) in still_open or wide_num(b) not in known]
        (blocked.append((n, stuck)) if stuck else ready.append(n))
    return ready[:CAP], ready[CAP:], blocked


# ---- 每個批次的檢查 ----------------------------------------------------
def numbers_in(payload):
    """這份 payload 裡所有「該是票號」的原值 —— 不管它住在哪個 mode。"""
    raws = []
    for t in payload.get("tickets", []):
        raws.append(t["number"])
        raws += list(t.get("blocked_by", []))
    for field in ("numbers", "fixing", "running", "queue", "merged", "pending"):
        raws += list(payload.get(field, []))
    if "number" in payload:
        raws.append(payload["number"])
    raws += list(payload.get("titles", {}).keys())
    return raws


def check(name, payload):
    """一個批次跑一次 -> (違例清單, 寬尺多撈清單)。"""
    code, out, err = run(payload)
    bad, wide = [], []
    ctx = f"{name}\n    exit={code}\n    stdout={out!r}\n    stderr={err!r}"
    raws = numbers_in(payload)
    illegal = [r for r in raws if strict_num(r) is None]
    wide_only = [r for r in illegal if wide_num(r) is not None]

    if illegal:
        # N4:轉不成整數 -> 有聲地停
        if code == 0:
            bad.append((f"N4 {illegal!r} 不是票號,卻 exit=0(靜靜跑過去了)", ctx))
        if "Traceback" in err:
            bad.append((f"N4 {illegal!r} 停在裸 traceback,不是講得出話的訊息", ctx))
        for r in illegal:
            # 訊息裡要出現他填的那個值(引號有無不咬,咬的是那串字本身)
            if str(r) not in err:
                bad.append((f"N4 stderr 沒講出他填的 {r!r}", ctx))
        if wide_only:
            wide.append((f"{name}:寬尺認得 {wide_only!r} 是票號"
                         f"(整數值的小數),batch.py 停在這裡 exit={code}", ctx))
        return bad, wide

    # 以下都是「票號全部合法」的批次
    # N2:stdout 上每個「該是票號」的 #xxx 都是裸整數。
    # `#<spec 連結>` 不是票號(交棒那幾行本來就這樣寫),用「有沒有 `/` 或 `:`」
    # 認出來跳過 —— 標點靠 strip 掃掉,全形半形都要,因為輸出兩種都有。
    for tok in HASH_RE.findall(out):
        if "/" in tok or ":" in tok:
            continue
        if not tok.isdigit():
            bad.append((f"N2 stdout 上印出非裸整數的票號 `#{tok}`", ctx))

    # N5:**印出來**的每個票號,titles 表裡有它就要看得到那個標題。
    # 判準訂在「印出來的」而不是「payload 裡的」:一張已收的票本來就只被算進
    # 「另外 N 張」、closed 的 blocker 本來就不進清單 —— 那不是少印。#129 那個洞
    # 的簽名正好是「`#48` 印出來了,標題查不到,靜靜印成裸票號」。
    titles = {strict_num(k): v for k, v in payload.get("titles", {}).items()}
    shown = {int(t) for t in HASH_RE.findall(out) if t.isdigit()}
    if code == 0:
        for n in shown:
            if titles.get(n) and titles[n] not in out:
                bad.append((f"N5 #{n} 印出來了,titles 表裡的「{titles[n]}」"
                            "卻在 stdout 上不見了(型別混用把它靜靜吃掉)", ctx))

    if payload.get("mode") == "plan":
        # N6:三段自己算一遍
        ready, queued, blocked = my_plan(payload["tickets"])
        got = re.findall(r"^(要開|排隊|還卡著)\((\d+) 張\):$", out, re.M)
        want = {"要開": len(ready), "排隊": len(queued), "還卡著": len(blocked)}
        for label, n in got:
            if want[label] != int(n):
                bad.append((f"N6 「{label}」印 {n} 張,這支自己算是 {want[label]} 張",
                            ctx))
        for n, stuck in blocked:
            line = [l for l in out.splitlines() if l.strip().startswith(f"#{n} ")
                    or l.strip() == f"#{n}"]
            for b in stuck:
                if not any(f"#{b}" in l for l in line):
                    bad.append((f"N6 #{n} 應該卡在 #{b} 後面,那一行沒講", ctx))
        for n in ready:
            if not re.search(rf"^  #{n}\b", out, re.M):
                bad.append((f"N6 #{n} 這支算是開得起來的,清單上找不到它", ctx))
        return bad, wide

    if payload.get("mode") != "classify":
        return bad, wide

    tickets = payload["tickets"]
    canon = [strict_num(t["number"]) for t in tickets]
    dupes = {k: canon.count(k) for k in set(canon) if canon.count(k) > 1}
    head, rows, pastes, blocked = parse_classify(out)

    # N1:相異票號數 == 抬頭的「張」
    hc = head_counts(head)
    if rows:
        if hc.get("張") != len(set(canon)):
            bad.append((f"N1 抬頭的「張」是 {hc.get('張')},相異票號數是 "
                        f"{len(set(canon))}", ctx))
        if len(set(canon)) != len(tickets) and hc.get("列") != len(tickets):
            bad.append((f"N1 抬頭沒有正確的「列」數(拿到 {hc.get('列')}、"
                        f"實際 {len(tickets)} 列)", ctx))
    # 整批照印
    if len(rows) != len(tickets):
        bad.append((f"N1 分級列數 {len(rows)} != 餵進去的 {len(tickets)} 列", ctx))
    # 印出來的票號 == 正規化後的票號(順序照原樣)
    if [r[1] for r in rows] != [str(c) for c in canon]:
        bad.append((f"N1 印出來的票號 {[r[1] for r in rows]} 不是正規化後的 "
                    f"{[str(c) for c in canon]}", ctx))
    # N3:左欄不歪 —— `#` 之前那一段顯示欄寬一致
    widths = {cols(r[0]) for r in rows}
    if len(widths) > 1:
        bad.append((f"N3 左欄欄寬不一致 {sorted(widths)} —— 清單歪了", ctx))
    if pastes:
        pw = {cols(l.split("#")[0]) for l in out.splitlines()
              if PASTE_RE.match(l)}
        if len(pw) > 1:
            bad.append((f"N3 貼票行縮排不一致 {sorted(pw)}", ctx))

    if dupes:
        # N1:有重複 -> 當場停
        if code == 0:
            bad.append(("N1 有重複票號 "
                        + "、".join(f"#{k}x{c}" for k, c in sorted(dupes.items()))
                        + f" 卻 exit=0", ctx))
        for k in sorted(dupes):
            if f"#{k}" not in err:
                bad.append((f"N1 stderr 沒指名重複的 #{k}", ctx))
        if pastes:
            bad.append((f"N1 被擋了卻還印了 {len(pastes)} 行貼票用的分級", ctx))
    elif not blocked:
        # N7:對照組
        if code != 0:
            bad.append((f"N7 沒有重複、票號也都合法,卻 exit={code}", ctx))
        if len(pastes) != len(tickets):
            bad.append((f"N7 貼票段 {len(pastes)} 行 != {len(tickets)} 列", ctx))
    return bad, wide


# ---- 母體 --------------------------------------------------------------
# 同一張票的各種寫法 —— client 手打 JSON 真的寫得出來的那幾種。
SPELLINGS_47 = [47, "47", " 47 ", "047"]
SPELLINGS_48 = [48, "48"]
KINDS = {
    "fast": {"coverage": []},
    "slow": {"coverage": ["1. 登入頁"]},
}
T = {"47": "登入頁", "48": "結帳流程", "49": "寄信"}


def cases(quick):
    pool = [(s, k) for s in SPELLINGS_47 + SPELLINGS_48 for k in KINDS]
    for n in ([1, 2] if quick else [1, 2, 3]):
        for combo in itertools.product(pool, repeat=n):
            tickets = [dict(KINDS[k], number=s) for s, k in combo]
            yield ("size%d " % n
                   + " | ".join(f"{s!r} {k}" for s, k in combo),
                   {"mode": "classify", "titles": T, "tickets": tickets})

    # ---- 轉不成整數的那一面(N4)----
    for raw in ["四十七", None, "", " ", "47a", "#47", "47.0", 47.0, 47.9,
                "1e3", True, [47], {"n": 47}]:
        yield (f"壞票號 {raw!r}",
               {"mode": "classify", "titles": T,
                "tickets": [dict(KINDS["fast"], number=raw)]})
    # 探針:兩把尺都認得的寫法 —— 寬度的下界證明
    for raw in ["+47", "４７", "\t47\n"]:
        yield (f"探針(兩把尺都認得){raw!r}",
               {"mode": "classify", "titles": T,
                "tickets": [dict(KINDS["fast"], number=raw)]})

    # ---- N5:別的 mode 的票號名單 ----
    yield ("split 型別混用", {"mode": "split", "numbers": [47, "48"],
                              "fixing": ["48"], "titles": T})
    yield ("split 全字串", {"mode": "split", "numbers": ["47", " 48 "],
                            "fixing": [], "titles": T})
    yield ("start 型別混用", {"mode": "start", "numbers": ["47", 48],
                              "running": [], "titles": T})
    yield ("done 型別混用", {"mode": "done", "numbers": [" 47 "], "titles": T})
    yield ("refill 型別混用", {"mode": "refill", "running": ["47"],
                               "queue": ["48", 49], "titles": T})
    yield ("merged 型別混用", {"mode": "merged", "numbers": ["47", 48],
                               "fixing": ["48"], "titles": T,
                               "spec": "https://example.invalid/1"})
    yield ("summary 型別混用", {"mode": "summary", "spec": "https://example.invalid/1",
                                "numbers": ["47", 48], "fixing": [], "titles": T,
                                "coverage": {}})
    yield ("interrupted 型別混用", {"mode": "interrupted", "numbers": ["47", 48],
                                    "titles": T, "spec": "https://example.invalid/1"})
    yield ("conflict-stopped 型別混用",
           {"mode": "conflict-stopped", "numbers": ["47"], "titles": T,
            "files": ["a.py"], "merged": ["47"], "pending": ["48"]})
    yield ("fixing number 寫成字串",
           {"mode": "fixing", "number": "48", "numbers": [47, "48"],
            "fixing": ["48"], "titles": T})
    yield ("titles key 帶空白", {"mode": "classify", "titles": {" 47 ": "登入頁"},
                                 "tickets": [dict(KINDS["fast"], number="47")]})
    yield ("titles key 壞掉", {"mode": "classify", "titles": {"四七": "登入頁"},
                               "tickets": [dict(KINDS["fast"], number=47)]})

    # ---- N6:blocked_by 兩邊 key 對得起來 ----
    def P(n, b=(), state="open"):
        return {"number": n, "state": state, "blocked_by": list(b)}

    yield ("plan blocked_by 字串、blocker 已收",
           {"mode": "plan", "titles": T,
            "tickets": [P(47, state="closed"), P("48", ["47"])]})
    yield ("plan blocked_by 字串、blocker 還開著",
           {"mode": "plan", "titles": T, "tickets": [P(47), P(48, ["47"])]})
    yield ("plan blocked_by 帶空白",
           {"mode": "plan", "titles": T,
            "tickets": [P("47", state="closed"), P(48, [" 47 "])]})
    yield ("plan 整批型別混用 + 名額滿",
           {"mode": "plan", "titles": T,
            "tickets": [P("47"), P(48), P(" 49 "), P("50"), P(51, ["47"])]})
    yield ("plan blocker 不在這批裡",
           {"mode": "plan", "titles": T, "tickets": [P("48", ["99"])]})
    yield ("plan blocked_by 壞掉",
           {"mode": "plan", "titles": T, "tickets": [P(47), P(48, ["四十七"])]})


def main():
    quick = "--quick" in sys.argv
    bad, wide, n = [], [], 0
    for name, payload in cases(quick):
        n += 1
        b, w = check(name, payload)
        bad += b
        wide += w
    print(f"跑了 {n} 個批次(quick={quick})\n")
    if bad:
        print(f"==== 違例 {len(bad)} 筆 ====")
        for why, ctx in bad:
            print(f"- {why}")
            print(f"    {ctx}\n")
    else:
        print("==== 沒有違例 ====")
    print(f"\n==== 寬尺撈出來、受測物沒當一回事的多餘項 {len(wide)} 筆 ====")
    print("(不自動判成 bug —— 逐筆判讀)\n")
    for why, ctx in wide:
        print(f"- {why}")
        print(f"    {ctx}\n")
    if not wide:
        print("(無)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
