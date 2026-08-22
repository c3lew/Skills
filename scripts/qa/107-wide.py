"""#107 QA 的第二把尺 —— 刻意寫寬,不套受測物的規則。

受測物(`validate.py` 的 `judge_ordering_issues`)自己就是判準,只跑它、看它綠,
只證明它同意自己。這支從頭自己寫一遍「哪些 SKILL.md 該受這條規則檢查、它的並行池
長什麼樣」,而且刻意寫**寬**:

- 母體:repo 底下任何 `SKILL.md`,只要正文裡出現 `judge` 就收進來 —— 不管它是不是
  **自己**開一支 judge(受測物只認「自己開一支 subagent 當 judge」的那批,#57 的教訓)。
- 並行池:標題行只要含「並行池」就算一段,吃到下一個 `#` 標題為止。
- lane 名字:那段裡**任何**表格列的第一欄都算,粗體不粗體都收、`| --- |` 那列跳掉
  (受測物只認第一欄粗體的那種)。
- 排序約束:純文字寬比對 —— 全文任何一段同時出現 judge / walkthrough / 之後 就算有,
  **不看否定**(受測物照 #64 的形狀擋反寫與否定)。

寬那面會放行受測物擋下來的東西、也會撈到受測物根本沒看的檔 —— 那多半是設計上的收窄,
不是 bug。每一筆都列在「差額」一節等人判讀,判成誤報也要寫進 QA 報告。

跟 `98-wide.py` 的差別:98 量的是**入口**(守門看得到哪些 .py),這支量的是
**並行池的形狀**(judge 有沒有被寫進池、三線齊不齊、排序有沒有寫下來)。

用法:
    python scripts/qa/107-wide.py .
    python scripts/qa/107-wide.py <某個母體目錄>
"""
import pathlib
import re
import sys

WANT = {"regression", "walkthrough", "code-review"}
HEADING = re.compile(r"^#{1,6}\s")
POOL_HEAD = re.compile(r"^#{1,6}[^\n]*並行池")
ROW = re.compile(r"^\s*\|(.+?)\|")
SEP = re.compile(r"^[\s|:-]+$")
JUDGE_TXT = re.compile(r"judge", re.I)


def pool_lanes(lines, i):
    """從第 i 行(並行池標題)往下吃到下一個標題,回傳那段裡每一列表格的第一欄。"""
    lanes, body = [], []
    for line in lines[i + 1:]:
        if HEADING.match(line):
            break
        body.append(line)
    for line in body:
        if SEP.match(line):
            continue
        m = ROW.match(line)
        if not m:
            continue
        cell = m.group(1).strip().strip("*").strip()
        if not cell or cell.lower() in ("lane", "lane 名", "名稱"):
            continue
        lanes.append(cell)
    return lanes


def loose_ordering(text):
    """寬比對:全文任一段(以句號/換行斷)同時有 judge + walkthrough + 之後。

    刻意不看否定 —— 反寫 / 否定的那兩種繞過,寬尺會放行,差額那節再判讀。
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
    """寬尺自己的判定 —— 沒池 / 三線不齊 / 全文找不到排序句 就判紅。"""
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
              f"      抓到的 lane:{r['lanes'] or '—'}\n"
              f"      排序句(寬比對):{'有' if r['ordering'] else '無'}\n"
              f"      寬尺判定:{naive_verdict(r)}")

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
