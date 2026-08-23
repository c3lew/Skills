"""#118 的第二把尺 —— 刻意寫寬,不套受測規則,把 batch.py 當黑盒子。

受測物自己就是判準:`batch.py --self-check` 綠只證明它同意自己。所以這支**不
import batch.py 的任何內部函式**,只用 subprocess 餵 JSON 進去、讀 stdout /
stderr / exit code,然後直接對著驗收原句判:

> 1. 切票的時候,每張票都標了「快」或「慢」加一句理由,**整批一次列給我看,
>    我可以當場改任何一張**。

從原句推出來的不變量(不是從程式碼抄的):

- V1  餵 N 張票進去,stdout 的分級列數就是 N —— 不管其中幾張被拒。
      (「每張票都標了」+「整批一次列給我看」)
- V2  被拒 >= 1 張 -> exit 非 0,且 stdout 一行貼票用的 `分級:` 都沒有。
      (「當場停」+ 不能讓 agent 貼一份 client 沒點過的清單)
- V3  被拒 == 0 張 -> exit 0,且貼票段的行數也是 N。
- V4  每一張被拒的票,票號都要在 stderr 出現過。(client 手上要有能動作的資訊)
- V5  每一行分級列都帶一句非空的理由。(「加一句理由」)
- V6  每張餵進去的票號在分級列裡恰好出現一次 —— 沒有漏、也沒有多。

「被拒」這件事這支自己算,算法是把原句 + AC4 原句重講一遍,不看受測程式碼:
client 要求的車道兌現不了就是被拒 —— (a) 他填的不是「快」也不是「慢」,
(b) 他要把一張動到判斷邏輯的票改成「快」。

用法:
    python scripts/qa/118-wide.py .            # exit 0 = 沒有違例
    python scripts/qa/118-wide.py . --quick    # 只跑 1~2 張的批次
"""
import itertools
import json
import pathlib
import re
import subprocess
import sys

BATCH = "skills/build-batch/batch.py"

FAST, SLOW = "快", "慢"

# 母體:coverage x judgement x override。故意含打錯字與空字串 —— client 手滑
# 是真的會發生的輸入。
COVERAGES = {
    "[]": [],
    "['1. 登入頁']": ["1. 登入頁"],
}
JUDGEMENTS = {"false": False, "true": True}
OVERRIDES = {"none": None, "快": FAST, "慢": SLOW, "fast": "fast"}

KINDS = [
    (f"cov={cn} judge={jn} ovr={on}", cv, jv, ov)
    for (cn, cv), (jn, jv), (on, ov) in itertools.product(
        COVERAGES.items(), JUDGEMENTS.items(), OVERRIDES.items())
]
# 3 張那層用一個小子集,不然 subprocess 數量爆掉;挑的是四種代表:乾淨快、
# 乾淨慢、硬規則被拒、override 打錯字被拒。
TRIPLE_KINDS = [k for k in KINDS if k[0] in (
    "cov=[] judge=false ovr=none",
    "cov=['1. 登入頁'] judge=false ovr=none",
    "cov=[] judge=true ovr=快",
    "cov=[] judge=false ovr=fast",
)]

# 分級列 = 兩個空白 + 車道欄 + 票號 + 理由。車道欄寫寬:任何非空白字串都算,
# 不咬「快/慢/改不了」那三個字面值 —— 那是受測程式碼的用詞,不是原句的。
ROW_RE = re.compile(r"^ {2}(\S+) +#(\d+)\b(.*)$")
# 貼票行 = agent 會照著貼進票 body 的那一行。
PASTE_RE = re.compile(r"^ {2}#(\d+) {2}分級")


def rejected_by_prose(cov, judge, ovr):
    """原句重講一遍:client 要求的車道兌現不了 = 這張被拒。不看受測程式碼。"""
    if ovr is None:
        return False
    if ovr not in (FAST, SLOW):
        return True          # 他填的根本不是一個車道
    return bool(judge) and ovr == FAST   # 動到判斷邏輯的票改不成快(AC4 原句)


def run(root, tickets):
    payload = json.dumps({"mode": "classify", "tickets": tickets,
                          "titles": {str(t["number"]): "t" for t in tickets}},
                         ensure_ascii=False)
    r = subprocess.run([sys.executable, str(pathlib.Path(root) / BATCH)],
                       input=payload, capture_output=True, text=True,
                       encoding="utf-8", cwd=str(root))
    return r.returncode, r.stdout or "", r.stderr or ""


def parse(stdout):
    """把 stdout 拆成分級列與貼票行。純結構解析,不認車道字面值。"""
    rows, pastes = [], []
    for line in stdout.splitlines():
        m = PASTE_RE.match(line)
        if m:
            pastes.append(int(m.group(1)))
            continue
        m = ROW_RE.match(line)
        if m:
            tail = m.group(3)
            _, sep, reason = tail.partition(" — ")
            rows.append((int(m.group(2)), m.group(1),
                         reason.strip() if sep else ""))
    return rows, pastes


def check(root, kinds):
    """一個批次跑一次,回傳違例 list。"""
    tickets, labels, expect_rejected = [], [], []
    for i, (label, cov, judge, ovr) in enumerate(kinds):
        t = {"number": 41 + i, "coverage": cov, "judgement": judge}
        if ovr is not None:
            t["override"] = ovr
        tickets.append(t)
        labels.append(f"#{41 + i} {label}")
        if rejected_by_prose(cov, judge, ovr):
            expect_rejected.append(41 + i)

    code, out, err = run(root, tickets)
    rows, pastes = parse(out)
    n = len(tickets)
    ctx = " | ".join(labels)
    bad = []

    def bug(v, msg):
        bad.append((v, ctx, msg, code, out, err))

    if len(rows) != n:
        bug("V1", f"餵 {n} 張,stdout 只有 {len(rows)} 行分級列")
    if expect_rejected:
        if code == 0:
            bug("V2", f"有 {len(expect_rejected)} 張被拒卻 exit 0")
        if pastes:
            bug("V2", f"有張被拒卻印了 {len(pastes)} 行貼票行 {pastes}")
        for num in expect_rejected:
            if f"#{num}" not in err:
                bug("V4", f"被拒的 #{num} 沒有在 stderr 出現:{err.strip()!r}")
    else:
        if code != 0:
            bug("V3", f"沒有張被拒卻 exit {code}:{err.strip()!r}")
        if len(pastes) != n:
            bug("V3", f"沒有張被拒,貼票行卻有 {len(pastes)} 行(該 {n} 行)")
    for num, lane, reason in rows:
        if not reason:
            bug("V5", f"#{num} 那行沒有理由:車道欄={lane!r}")
    listed = [num for num, _, _ in rows]
    for t in tickets:
        if listed.count(t["number"]) != 1:
            bug("V6", f"#{t['number']} 在分級列出現 {listed.count(t['number'])} 次")
    return bad


def main(root, quick=False):
    batches = [(k,) for k in KINDS]
    batches += list(itertools.product(KINDS, repeat=2))
    if not quick:
        batches += list(itertools.product(TRIPLE_KINDS, repeat=3))
    violations = []
    for kinds in batches:
        violations += check(root, list(kinds))
    print(f"掃過 {len(batches)} 個批次"
          f"(1 張 {len(KINDS)} / 2 張 {len(KINDS) ** 2} / 3 張 "
          f"{0 if quick else len(TRIPLE_KINDS) ** 3})")
    print(f"違例:{len(violations)}")
    for v, ctx, msg, code, out, err in violations:
        print(f"\n  {v}  {ctx}\n      {msg}")
        print("      exit:", code)
        print("      stdout:", repr(out))
        print("      stderr:", repr(err))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sys.exit(main(args[0] if args else ".", "--quick" in sys.argv))
