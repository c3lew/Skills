"""#127 的第二把尺 —— 刻意寫寬,不 import / 不套 batch.py 的任何規則。

受測物本身就是判準:它自己判自己有沒有重複票號。只跑 `--self-check` 綠,證明的
是「它同意自己」。所以這支把 `batch.py` 當黑盒子:只用 subprocess 餵 JSON、讀
stdout / stderr / exit code,重複票號**自己從 JSON 母體算**,再跟實際行為對照。

判準是驗收原句 + #127 票上的 AC,不是程式碼:

> 1. 切票的時候,每張票都標了「快」或「慢」加一句理由,整批一次列給我看,
>    我可以當場改任何一張。

「我可以當場改任何一張」的前提是**一張票在清單上只有一列** —— 兩列的時候他點的
頭指向哪一列不確定。從這裡推出來的不變量:

- W1  母體裡有票號出現不只一次 -> exit 非 0。(不能讓他在一份有兩列同票的清單上點頭)
- W2  每個重複的票號,stderr 要出現該票號、而且要出現它重複的那個次數。
- W3  分級列數 == 餵進去的列數。(整批照印,#118 那條不變)
- W4  有被擋 -> 一行貼票用的 `分級:` 都不印。(agent 不能貼一份沒被點過的清單)
- W5  「還不能貼」名單上每個票號各出現一次(講的是票,不是列)。
- W6  抬頭括號裡的「N 張」== 相異票號數;有重複時另外要有「N 列」== 列數。
- W7  沒有任何重複、也沒有被拒 -> exit 0 且貼票段行數 == 列數。(對照組:證明停的
      是重複,不是別的東西)
- W8  每一列都有非空的左欄(車道)+ 非空的理由。

**寬在哪**:重複與否這支用 `str(number).strip()` 當同一張票的 key —— 比受測物寬
(它比的是 JSON 解出來的原值)。寬的那面撈出來的多餘項不自動判成 bug,逐筆列在
報告最後由人判讀。另外附一組「看起來像同一張票但票號不同」的探針(同標題兩張票),
那是預期中的誤報,列出來當寬度的下界證明。

用法:
    python 127-wide.py                 # 全跑
    python 127-wide.py --quick         # 只跑 1~2 列的批次
"""
import itertools
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BATCH = ROOT / "skills" / "build-batch" / "batch.py"

FAST, SLOW = "快", "慢"

# 分級列 = 兩個空白 + 左欄 + 票號 + ` — ` + 理由。左欄寫寬:任何非空白字串都算,
# 不咬「快 / 慢 / 改不了」那三個字面值 —— 那是受測程式碼的用詞,不是原句的。
ROW_RE = re.compile(r"^ {2}(\S+) +#(\S+?) (?:(.*?) )?— (.*)$")
ROW_ANY_RE = re.compile(r"^ {2}(\S+) +#(\S+?)\b")
PASTE_RE = re.compile(r"^ {2}#(\S+) {2}分級")
HEAD_RE = re.compile(r"^分級\(([^)]*)\)")
# 「還不能貼」底下那份名單:兩個空白 + #票號 [+ 標題]
LIST_RE = re.compile(r"^ {2}#(\S+)(?: .*)?$")


def wide_key(number):
    """這支自己的「同一張票」判準 —— 刻意比受測物寬:字串化再去空白。

    `{"number": "47"}` 與 `{"number": 47}` 在 client 眼裡是同一張 #47(清單上兩列
    都印成 `#47`),所以這支把它們算成同一張。受測物比的是 JSON 原值。差異出來的
    那幾筆是這支的主要產出,不自動判 bug,列在報告最後判讀。
    """
    return str(number).strip()


def dupes_of(tickets):
    """母體自己算:哪些票號出現超過一次 -> 次數。不看受測程式碼。"""
    keys = [wide_key(t["number"]) for t in tickets]
    return {k: keys.count(k) for k in set(keys) if keys.count(k) > 1}


def rejected_by_prose(t):
    """client 要求的車道兌現不了 = 這張被拒。把 #108 / #118 的原句重講一遍。"""
    ovr = t.get("override")
    if ovr is None:
        return False
    if ovr not in (FAST, SLOW):
        return True                       # 他填的根本不是一個車道
    return bool(t.get("judgement")) and ovr == FAST


def run(tickets, titles=None):
    payload = json.dumps({"mode": "classify", "tickets": tickets,
                          "titles": titles or {}}, ensure_ascii=False)
    p = subprocess.run([sys.executable, str(BATCH)],
                       input=payload.encode("utf-8"), capture_output=True)
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def parse(out):
    lines = out.splitlines()
    head = HEAD_RE.match(lines[0]) if lines else None
    rows, pastes, blocked = [], [], []
    in_list = False
    for ln in lines:
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
        if " — " in ln:
            m = ROW_ANY_RE.match(ln)
            if m:
                lane, num = m.group(1), m.group(2)
                reason = ln.split(" — ", 1)[1]
                rows.append((lane, num, reason))
                continue
        if in_list:
            m = LIST_RE.match(ln)
            if m:
                blocked.append(m.group(1))
    return head.group(1) if head else "", rows, pastes, blocked


def head_numbers(head):
    """抬頭括號裡的每個數字 + 它後面那個量詞,例如 [('1','張'), ('2','列')]。"""
    return re.findall(r"(\d+)\s*([張列])", head)


def check(name, tickets, titles=None):
    """一個批次跑一次,回 (違例清單, 寬撈到的多餘項清單)。"""
    code, out, err = run(tickets, titles)
    head, rows, pastes, blocked = parse(out)
    dupes = dupes_of(tickets)
    prose_rejected = {wide_key(t["number"]) for t in tickets if rejected_by_prose(t)}
    bad, wide = [], []
    ctx = f"{name}\n    exit={code}\n    stdout={out!r}\n    stderr={err!r}"

    # W3 整批照印
    if len(rows) != len(tickets):
        bad.append(("W3 分級列數 != 餵進去的列數"
                    f"({len(rows)} vs {len(tickets)})", ctx))
    # W8 每列有左欄 + 非空理由
    for lane, num, reason in rows:
        if not lane.strip() or not reason.strip():
            bad.append((f"W8 #{num} 這一列左欄或理由是空的", ctx))

    if dupes:
        # W1 當場停
        if code == 0:
            bad.append(("W1 母體裡有重複票號 "
                        + "、".join(f"#{k}x{c}" for k, c in sorted(dupes.items()))
                        + " 但 exit=0(靜靜印出去了)", ctx))
        # W2 stderr 指名票號 + 次數
        for k, c in sorted(dupes.items()):
            if f"#{k}" not in err:
                bad.append((f"W2 stderr 沒指名重複的 #{k}", ctx))
            elif str(c) not in err:
                bad.append((f"W2 stderr 沒講 #{k} 重複 {c} 次", ctx))
        # W6 抬頭:張 = 相異票號、列 = 列數
        # 抬頭長這樣:`2 張、3 列,其中 1 張改不了` —— 「張」出現兩次,要的是
        # 第一個(總張數),不是最後那個(改不了幾張)。
        hn = {}
        for v, q in head_numbers(head):
            hn.setdefault(q, int(v))
        seats = len({wide_key(t["number"]) for t in tickets})
        if hn.get("張") != seats:
            bad.append((f"W6 抬頭的「張」是 {hn.get('張')},相異票號數是 {seats}", ctx))
        if hn.get("列") != len(tickets):
            bad.append((f"W6 抬頭沒有正確的「列」數(拿到 {hn.get('列')},"
                        f"實際 {len(tickets)} 列)", ctx))
    if dupes or prose_rejected:
        # W4 貼票段整段不印
        if pastes:
            bad.append((f"W4 被擋了卻還印了 {len(pastes)} 行貼票用的分級", ctx))
        # W5 名單去重
        for k in set(blocked):
            if blocked.count(k) > 1:
                bad.append((f"W5 還不能貼名單上 #{k} 出現 {blocked.count(k)} 次", ctx))
    else:
        # W7 對照組
        if code != 0:
            bad.append((f"W7 沒有重複也沒有被拒卻 exit={code}", ctx))
        if len(pastes) != len(tickets):
            bad.append((f"W7 貼票段 {len(pastes)} 行 != {len(tickets)} 列", ctx))

    # 寬的那面:母體算出有重複、而受測物一聲不吭 —— 逐筆判讀,不自動算 bug
    if dupes and code == 0:
        wide.append((f"{name}:寬的 key 判成重複 "
                     + "、".join(f"#{k}x{c}" for k, c in sorted(dupes.items()))
                     + f",batch.py exit=0", ctx))
    return bad, wide


# ---- 母體 --------------------------------------------------------------
# 一列的種類:coverage x judgement x override。含打錯字與空字串 —— client 手滑
# 是真的會發生的輸入。
KINDS = {
    "clean-fast": {"coverage": []},
    "clean-slow": {"coverage": ["1. 登入頁"]},
    "hard-rule":  {"coverage": [], "judgement": True, "override": FAST},
    "typo":       {"coverage": [], "override": "fast"},
    "empty-ovr":  {"coverage": [], "override": ""},
    "ovr-slow":   {"coverage": [], "override": SLOW},
}
# 票號池刻意小 —— 小到隨機組合本來就會撞號,重複因此是自然長出來的,不是硬塞的。
NUMBERS = [47, 48]


def cases(quick):
    """(名稱, tickets, titles) 的產生器。"""
    titles = {"47": "登入頁", "48": "算票", "9": "骨架"}
    sizes = [1, 2] if quick else [1, 2, 3]
    for n in sizes:
        for combo in itertools.product(
                itertools.product(NUMBERS, KINDS), repeat=n):
            tickets = [dict(KINDS[k], number=num) for num, k in combo]
            name = "size%d " % n + " | ".join(f"#{num} {k}" for num, k in combo)
            yield name, tickets, titles
    # 手寫的邊界:三重複、四重複、票號型別混用、同標題不同票號
    yield ("特例 三重複",
           [dict(KINDS["clean-fast"], number=47),
            dict(KINDS["clean-slow"], number=47),
            dict(KINDS["typo"], number=47)], titles)
    yield ("特例 四重複",
           [dict(KINDS["clean-fast"], number=47) for _ in range(4)], titles)
    yield ("特例 票號一個寫成字串 '47'、一個寫成數字 47",
           [dict(KINDS["clean-fast"], number="47"),
            dict(KINDS["clean-slow"], number=47)], titles)
    yield ("特例 票號前後有空白 ' 47 '",
           [dict(KINDS["clean-fast"], number=" 47 "),
            dict(KINDS["clean-slow"], number=47)], titles)
    yield ("特例 同一個標題兩張不同的票(預期誤報)",
           [dict(KINDS["clean-fast"], number=47),
            dict(KINDS["clean-fast"], number=48)],
           {"47": "登入頁", "48": "登入頁"})


def main():
    quick = "--quick" in sys.argv
    bad, wide, n = [], [], 0
    for name, tickets, titles in cases(quick):
        n += 1
        b, w = check(name, tickets, titles)
        bad += b
        wide += w
    print(f"跑了 {n} 個批次(quick={quick})")
    print()
    if bad:
        print(f"==== 違例 {len(bad)} 筆 ====")
        for why, ctx in bad:
            print(f"- {why}")
            print(f"    {ctx}")
            print()
    else:
        print("==== 沒有違例 ====")
    print()
    print(f"==== 寬的 key 撈出來、受測物沒當一回事的多餘項 {len(wide)} 筆 ====")
    for why, ctx in wide:
        print(f"- {why}")
        print(f"    {ctx}")
        print()
    if not wide:
        print("(無)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
