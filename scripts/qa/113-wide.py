"""#113 QA 的第二把尺 —— 刻意寫寬,不套受測物的規則。

#113 修的三條(stale `§N` 指標、自我描述跟本體打架、無界全稱詞)全都是**散文**問題。
`validate.py` 的 docstring 自己寫著 `Does NOT validate prose content` —— 也就是說這三條
修完之後,repo 裡**沒有任何機械判準看得到它們**,唯一的收據是 `/writing-for-agents`
走查 agent 說「pass」。走查 agent 跟寫修法的是同一類 reader,它綠只證明它同意自己。

這支從頭自己寫一遍那三條的機械形狀,而且刻意寫**寬**:

- **stale `§N`**:母體是 `skills/` 與 `docs/` 底下任何 `*.md`。文中每一個 `§<數字>`
  都要在**同一個檔**找得到 `## <數字>.` 開頭的標題。刻意不管上下文 —— 引用別的檔的
  `§N`(例:`close/SKILL.md` 講 `/qa` 的 §5)照樣會被算成未解析,列進差額等人判讀。
  走查 agent 是靠讀懂語意判的,這支只靠字面。

- **指錯節的 `§N`**:上面那條只抓「指到不存在的節」。#113 第 1 條是**指得到、但指錯**
  (`跑完接 §2 收尾`,而「收尾」住在 §3)—— 字面解析得開,錯的是語意。機械形狀:`§N`
  後面緊跟的 2–4 個字如果**本身就是某個標題的字**,那 §N 的標題就該含那幾個字。
  刻意寫寬:不管上下文、不管是不是引用別的檔,對不上就列出來等人判讀。

- **無界全稱詞**:關鍵詞表刻意開大(唯一/所有/全部/任何/每一/永遠/從不/絕對/一律/
  完全/必然/不可能),而且**不分辨**「這句是不是理由句」—— `written-evidence.md` 只禁
  理由句裡的無界斷言,規則陳述(「紅的每一條記為 blocking」)是合法的。寬那面會把
  合法的規則陳述一起撈出來,逐筆判讀,判成誤報也要寫進 QA 報告。

- **delta 記帳**:frontmatter + body 自稱幾個 delta,對上正文有幾個 `(delta)` 結尾的
  `##` 標題。三個數字要一致 —— 這是票上第 2 條「同一個意思兩處只改一處」的機械投影。

寬那面會撈到受測物(走查 agent)設計上就不看的東西,那多半是收窄不是 bug。

用法:
    python scripts/qa/113-wide.py .                  # 掃現況
    python scripts/qa/113-wide.py . --json           # 給 prevdiff 對照用
"""
import json
import pathlib
import re
import sys

SEC_REF = re.compile(r"§(\d+)")
SEC_HEAD = re.compile(r"^#{2,6}\s*(\d+)\.")
SEC_HEAD_FULL = re.compile(r"^#{2,6}\s*(\d+)\.\s*(.+?)\s*$")
REF_KW = re.compile(r"§(\d+)\s*([一-鿿]{2,4})")
DELTA_HEAD = re.compile(r"^#{2,6}\s*\d+\..*\(delta\)\s*$")
DELTA_COUNT = re.compile(r"(一|二|兩|三|四|五|六|七|八|九|\d+)\s*個\s*delta")
CJK_NUM = {"一": 1, "二": 2, "兩": 2, "三": 3, "四": 4,
           "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

# 刻意開大:不分辨理由句 vs 規則陳述,全撈。
UNBOUNDED = ["唯一", "所有", "全部", "任何", "每一", "永遠",
             "從不", "絕對", "一律", "完全", "必然", "不可能"]


def scan_file(path, text):
    lines = text.split("\n")
    heads = {m.group(1) for line in lines for m in [SEC_HEAD.match(line)] if m}

    stale = []
    for i, line in enumerate(lines, 1):
        if SEC_HEAD.match(line):
            continue
        for m in SEC_REF.finditer(line):
            if m.group(1) not in heads:
                stale.append({"line": i, "ref": "§" + m.group(1),
                              "text": line.strip()[:90]})

    titles = {}
    for line in lines:
        m = SEC_HEAD_FULL.match(line)
        if m:
            titles[m.group(1)] = m.group(2)
    # 標題字彙:每個標題切成 2–4 字的片段。刻意寬 —— 只要某個標題含這幾個字,
    # 指向別的節卻帶著這幾個字就算可疑,不管語意。
    vocab = set()
    for t in titles.values():
        core = re.sub(r"[((].*?[))]|\s|`|\*", "", t)
        for n in (2, 3, 4):
            for j in range(len(core) - n + 1):
                vocab.add(core[j:j + n])

    misaimed = []
    for i, line in enumerate(lines, 1):
        if SEC_HEAD.match(line):
            continue
        for m in REF_KW.finditer(line):
            num, kw = m.group(1), m.group(2)
            if num not in titles:
                continue  # 指到不存在的節,已由 stale_refs 收走
            hit = next((k for k in (kw, kw[:3], kw[:2]) if k in vocab), None)
            if hit and hit not in titles[num]:
                owner = [n for n, t in titles.items() if hit in t]
                misaimed.append({"line": i, "ref": "§" + num, "kw": hit,
                                 "owner": owner, "title": titles[num],
                                 "text": line.strip()[:90]})

    universals = []
    for i, line in enumerate(lines, 1):
        for w in UNBOUNDED:
            if w in line:
                universals.append({"line": i, "word": w,
                                   "text": line.strip()[:90]})

    delta_heads = sum(1 for line in lines if DELTA_HEAD.match(line))
    claims = []
    for i, line in enumerate(lines, 1):
        for m in DELTA_COUNT.finditer(line):
            raw = m.group(1)
            claims.append({"line": i,
                           "claim": CJK_NUM.get(raw, int(raw) if raw.isdigit() else 0)})

    return {"path": path, "stale_refs": stale, "misaimed_refs": misaimed,
            "universals": universals,
            "delta_heads": delta_heads, "delta_claims": claims}


def collect(root):
    root = pathlib.Path(root)
    out = []
    for sub in ("skills", "docs"):
        for p in sorted((root / sub).rglob("*.md")):
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue  # 讀不到就算未知,寧可漏也不假裝綠 —— 列在 unreadable
            out.append(scan_file(p.relative_to(root).as_posix(), text))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = args[0] if args else "."
    reports = collect(root)

    if "--json" in sys.argv:
        print(json.dumps(reports, ensure_ascii=False, sort_keys=True))
        return 0

    stale = [(r["path"], s) for r in reports for s in r["stale_refs"]]
    uni = [(r["path"], u) for r in reports for u in r["universals"]]
    mismatch = [r for r in reports
                if r["delta_claims"]
                and {c["claim"] for c in r["delta_claims"]} != {r["delta_heads"]}]

    print("母體:%d 份 .md(skills/ + docs/)" % len(reports))

    print("\n== 未解析的 §N(寬:不管跨檔引用)== %d 筆" % len(stale))
    for path, s in stale:
        print("  %s:%d %s  %s" % (path, s["line"], s["ref"], s["text"]))

    mis = [(r["path"], m) for r in reports for m in r["misaimed_refs"]]
    print("\n== 指得到但指錯節的 §N(寬:靠標題字比對)== %d 筆" % len(mis))
    for path, m in mis:
        print("  %s:%d %s 的標題是「%s」,但「%s」住在 §%s"
              % (path, m["line"], m["ref"], m["title"], m["kw"],
                 "/§".join(m["owner"]) or "?"))
        print("      %s" % m["text"])

    print("\n== 無界全稱詞候選(寬:不分理由句/規則陳述)== %d 筆" % len(uni))
    by_file = {}
    for path, u in uni:
        by_file.setdefault(path, []).append(u)
    for path in sorted(by_file):
        hits = by_file[path]
        print("  %s —— %d 筆" % (path, len(hits)))
        for u in hits:
            print("      :%d 「%s」 %s" % (u["line"], u["word"], u["text"]))

    print("\n== delta 記帳對不上 == %d 份" % len(mismatch))
    for r in mismatch:
        print("  %s 自稱 %s 個,正文有 %d 個 (delta) 標題"
              % (r["path"], sorted({c["claim"] for c in r["delta_claims"]}),
                 r["delta_heads"]))

    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
