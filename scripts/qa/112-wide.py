"""#112 QA 的第二把尺 —— 刻意寫寬,不套受測物的規則。

受測物就是 `validate.py` 的 `judge_ordering_issues` 本人。只跑它、看它綠,只證明它同意
自己 —— 尤其這一輪動的正是「錨點錨在哪」,拿它自己的錨點去量它自己的錨點是循環論證。
所以這支從頭自己寫一遍「哪些 SKILL.md 該受這條規則檢查、它的並行池長什麼樣」,
**不 import validate.py 做判定**,也不抄它任何一條 regex。

刻意寬在哪(每一條都是這一輪的錨點被收窄的那個方向,故意反著寫):

- **母體**:repo 底下任何 `SKILL.md`,只要正文出現 `judge` 就收 —— 不管它是不是
  **自己**開一支 judge(受測物只認「自己開一支 subagent 當 judge」的那批,#57 的教訓)。
- **並行池 section**:標題行只要含「並行池」就開一段,吃到**下一個同級或更高級**標題
  為止 —— `###` 子段留在段內(受測物 #112 之後把子段的表排除掉了,這裡故意不排)。
- **lane 表**:那段裡**任何**表格的**任何**列都算 lane,粗體不粗體都收,只跳掉
  `| --- |` 那種分隔列跟一望即知的表頭列 —— 受測物 #112 之後只認「表頭第一欄字面是
  `lane`」的那一張表,這裡故意不看表頭。
- **排序約束**:純文字寬比對 —— 全文任一段(含**標題**)同時出現 judge / walkthrough /
  之後 就算有,**不看否定**、**不管它在標題還是正文**。受測物 #112 之後剪掉標題只讀
  正文,並照 #64 的形狀擋反寫與否定。

寬那面會放行受測物擋下來的東西(否定 / 反寫 / 只寫在標題),也會撈到受測物根本沒看的
檔,還會把非 lane 表讀成 lane —— 那多半是這一輪**設計上的收窄**,不是 bug。每一筆都列
在「差額」一節等人判讀,判成誤報也要寫進 QA 報告。

跟 `107-wide.py` 的差別:107 那支量的是 #107 的主張(judge 有沒有被寫進池、三線齊不齊);
這支量的是 #112 的主張(池的宣告到底錨在哪一張表、排序約束到底寫在哪),所以段落邊界
與 lane 認定都重新推導過,不是照抄。

用法:
    python scripts/qa/112-wide.py .
    python scripts/qa/112-wide.py <某個母體目錄>
"""
import pathlib
import re
import sys

WANT = {"regression", "walkthrough", "code-review"}
HEADING = re.compile(r"^(#{1,6})\s")
POOL_HEAD = re.compile(r"^(#{1,6})[^\n]*並行池")
ROW = re.compile(r"^\s*\|(.+?)\|")
SEP = re.compile(r"^[\s|:-]+$")
JUDGE_TXT = re.compile(r"judge", re.I)
# 一望即知的表頭字,只有這幾個字才跳 —— 不是「看表頭決定這張表算不算」
HEADER_WORDS = {"lane", "lane 名", "名稱", "資源", "欄位", "項目", "#"}


def pool_lanes(lines, i):
    """從第 i 行(並行池標題)往下吃到下一個**同級或更高級**標題。

    刻意寬:`###` 子段留在段內,子段裡的表一樣被讀成 lane 宣告。
    """
    level = len(POOL_HEAD.match(lines[i]).group(1))
    lanes, body = [], []
    for line in lines[i + 1:]:
        m = HEADING.match(line)
        if m and len(m.group(1)) <= level:
            break
        body.append(line)
    for line in body:
        if SEP.match(line):
            continue
        m = ROW.match(line)
        if not m:
            continue
        cell = m.group(1).strip().strip("*").strip()
        if not cell or cell.lower() in HEADER_WORDS:
            continue
        lanes.append(cell)
    return lanes


def loose_ordering(text):
    """寬比對:全文任一段(以句號/換行斷,**含標題行**)同時有 judge + walkthrough + 之後。

    刻意不看否定、也不管它是標題還是正文 —— 那兩種收窄正是 #112 收的,
    寬尺會放行,差額那節再判讀。
    """
    for span in re.split(r"[。\n]", text):
        low = span.lower()
        if "judge" in low and "walkthrough" in low and "之後" in span:
            return True
    return False


def scan(repo):
    rows = []
    for md in sorted(pathlib.Path(repo).rglob("SKILL.md")):
        rel = md.relative_to(repo).as_posix()
        try:
            text = md.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            rows.append(dict(file=rel, unreadable=f"{type(exc).__name__}: {exc}"))
            continue
        if not JUDGE_TXT.search(text):
            continue                      # 寬母體:文字裡沒 judge 才不收
        lines = text.splitlines()
        heads = [i for i, l in enumerate(lines) if POOL_HEAD.match(l)]
        lanes = [n for i in heads for n in pool_lanes(lines, i)]
        rows.append(dict(file=rel, unreadable=None, pool=bool(heads),
                         lanes=lanes, ordering=loose_ordering(text)))
    return rows


def naive_verdict(row):
    """寬尺自己的判定 —— 沒池 / 抓到的 lane 集合不是那三支 / 全文找不到排序句 就判紅。"""
    if row.get("unreadable"):
        return "紅"
    if not row["pool"]:
        return "紅"
    if {l.lower() for l in row["lanes"]} != WANT:
        return "紅"
    return "綠" if row["ordering"] else "紅"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    repo = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    rows = scan(repo)

    # 比對那一面才碰受測物 —— 上面的掃描不 import、不抄它的 regex
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    import validate

    tight = {}
    for r in rows:
        text = (repo / r["file"]).read_text(encoding="utf-8")
        tight[r["file"]] = validate.judge_ordering_issues(text)

    print("==== 寬尺母體:正文出現 `judge` 的 SKILL.md ====")
    for r in rows:
        if r.get("unreadable"):
            print(f"  {r['file']}:讀不進來 —— {r['unreadable'][:70]}")
            continue
        print(f"  {r['file']}\n"
              f"      並行池 section:{'有' if r['pool'] else '無'}\n"
              f"      抓到的 lane(寬:段內任何表的任何列):{r['lanes'] or '—'}\n"
              f"      排序句(寬比對,含標題、不看否定):{'有' if r['ordering'] else '無'}\n"
              f"      寬尺判定:{naive_verdict(r)}\n"
              f"      受測物判定:{'紅' if tight[r['file']] else '綠'}")

    print(f"\n寬尺母體 {len(rows)} 支 SKILL.md;"
          f"寬尺判紅 {sum(1 for r in rows if naive_verdict(r) == '紅')} 支;"
          f"受測物判紅 {sum(1 for v in tight.values() if v)} 支\n")

    print("==== 差額(寬尺 vs 受測物)—— 每一筆要人判讀 ====")
    diff = []
    for r in rows:
        w = naive_verdict(r)
        t = "紅" if tight[r["file"]] else "綠"
        if w != t:
            diff.append((r, w, t))
            kind = ("寬尺抓到、守門放行" if w == "紅" else "守門抓到、寬尺沒抓")
            print(f"  {r['file']}:寬尺判{w},守門判{t} —— {kind}")
            for e in tight[r["file"]]:
                print(f"      守門說:{e}")
    print(f"  差額 {len(diff)} 筆" + ("" if diff else " —— 兩把尺對這份母體完全同意"))
    sys.exit(0)
