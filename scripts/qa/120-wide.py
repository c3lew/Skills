"""#120 QA 的第二把尺 —— 刻意寫寬,不套受測物的規則。

受測物本身就是一支守門(`batch.py` 的 `CLASSIFY_LINES` / `classify_lines_issue`)。
只跑它、看它綠,證明的只有「它同意自己」。這支從頭寫一遍「repo 裡哪裡宣稱要走
batch.py 的 classify、那些地方的散文有沒有把 #120 那三件事講出來」,而且刻意寫**寬**:

- 受檢範圍:`skills/*/SKILL.md` 全收 —— 受測物只讀一支寫死的 sibling
  (`skills/slice-tickets/SKILL.md`),連「還有誰在呼叫 classify」都沒問過。
- (a) 硬規則蓋過 client 的 override:認任何一種說法 —— 「硬規則」「蓋過」
  「override」「改不成快」「當場停」附近,而不是受測物那句字面。
- (b) 不准自己翻 judgement 旗標:認「judgement」+(「不要改 / 不是放行開關 /
  不准改 / 別改」)這一族,不是單一字面。
- (c) 天花板有沒有收邊:凡是把降級回路講成「關住 / 全部 / 一律 / 都接得住 /
  兜得住」而**同一句裡沒有**收邊詞(「有驗收項 / 那半 / 還沒出貨 / 接不住」)
  的,一律當成疑似過度宣稱撈出來。受測物只認一句 `接得住的是**有驗收項**的那半`。
- 指路繞道的殘留:整個 repo(不只 skills/)grep 任何叫人去動 judgement 旗標的字。

不 import `batch.py` / `validate.py` 的任何判斷。跟受測物對照的那一面,是把兩支
守門當**黑箱**跑:讀 exit code 與它印的字,再用「把某支 SKILL.md 掏空、看守門紅
不紅」去反推它的母體到底有幾支檔 —— 讀輸出不是套規則。

寬的那面一定會撈到受測物放行的東西 —— 那是設計,不是 bug。每一筆都列在「差額」
一節等人逐筆判讀,判成誤報也要寫進 QA 報告。

用法:
    python scripts/qa/120-wide.py .
    python scripts/qa/120-wide.py <某個母體目錄>
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

# --- 寬尺自己的 pattern,一行都不跟受測物共用 ------------------------------

# 宣稱要走 batch.py 的 classify(受測物只認 `"mode": "classify"` 那一串)
CALLS_CLASSIFY = re.compile(r"batch\.py|classify|快慢分級|分級清單|判快慢", re.I)
# (a) 硬規則蓋過 client 的 override
SAYS_HARD_RULE = re.compile(
    r"硬規則.{0,40}(蓋過|override|改不成|一律慢|當場停)"
    r"|(蓋過|壓過).{0,20}(client|override)"
    r"|改不成快", re.I | re.S)
# (b) 不准自己翻 judgement 旗標
SAYS_DONT_FLIP = re.compile(
    r"judgement.{0,40}(不要|不准|別|不是放行|不能)"
    r"|(不要|不准|別).{0,40}judgement"
    r"|旗標.{0,20}(不要|不准|別|不是放行)", re.I | re.S)
# (c) 降級回路的宣稱:先撈出所有提到降級回路的句子
MENTIONS_LOOP = re.compile(r"降級回路|降級迴路|degrade|降級")
# 絕對式的動詞
ABSOLUTE = re.compile(r"關住|全部|一律|都接得住|整個接|兜得住|全都|完全")
# 收邊詞:同一句裡有這些才算「講得出真話的版本」。
# 刻意**不**收「天花板」—— 它是段落的標籤,不是對回路範圍的收邊。第一版把它算進來,
# 結果 #120 要打的那句原文(「判錯的代價由降級回路關住」,同句裡有「天花板」三個字)
# 整句被放行 —— 尺自己啞掉。FIXTURES 那組就是為了讓這種啞掉當場紅。
BOUNDED = re.compile(r"有驗收項|那半|還沒出貨|接不住|不會被觸發|只接得住|唯一的一道")
# 句子切法:中文句號 / 分號 / 換行
SENT_SPLIT = re.compile(r"[。;;\n]")
# 指路繞道:叫人去動 judgement 旗標
SIGNPOST = re.compile(
    r"要改請先改.{0,10}judgement"
    r"|改\s*judgement\s*旗標"
    r"|judgement\s*旗標\s*改"
    r"|旗標改掉"
    r"|把\s*judgement\s*改成\s*(false|False|`false`)"
    r"|judgement.{0,12}改成\s*false", re.I)
# 掃 repo 時跳過的目錄
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
TEXT_SUFFIX = {".md", ".py", ".sh", ".txt", ".json", ".yml", ".yaml", ""}

GUARD_BATCH = "skills/build-batch/batch.py"
GUARD_VALIDATE = "scripts/validate.py"


def sentences(text):
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]


# 這把尺自己的對照組:一把永遠不響的尺跟沒有尺一樣。左邊是 #120 要打的那句(#108
# 出貨的原文,必須響),右邊是修完的版本(必須不響)。main() 一開始就跑。
FIXTURES = (
    (True, "判錯的代價由降級回路關住(標「快」的票對驗收清單有任何一條沒過就當場降級)"),
    (True, "**這條判準的天花板**:判錯必然會發生,判錯的代價由降級回路關住"),
    (True, "實務上判錯的代價已經由降級回路一律接得住,不用擔心"),
    (False, "就算出了,它接得住的是**有驗收項**的那半"),
    (False, "而那個回路**還沒出貨**,repo 裡沒有任何一支 skill 實作它"),
    (False, "`coverage` 是空的那半一條驗收項都沒有,回路不會被觸發"),
)


def flags_overclaim(sentence):
    """(c) 的判定拆成一個純函式 —— 這樣 FIXTURES 咬得到它。"""
    return bool(MENTIONS_LOOP.search(sentence)
                and ABSOLUTE.search(sentence)
                and not BOUNDED.search(sentence))


def self_test():
    bad = [(want, s) for want, s in FIXTURES if flags_overclaim(s) is not want]
    print("==== 寬尺自己的對照組(過度宣稱偵測器有沒有在動)====")
    for want, s in FIXTURES:
        got = flags_overclaim(s)
        mark = "OK " if got is want else "壞了"
        print(f"  [{mark}] 預期{'響' if want else '不響'} 實際{'響' if got else '不響'}"
              f" — {s[:52]}")
    if bad:
        raise SystemExit("寬尺的過度宣稱偵測器壞了 —— 下面的掃描不算數")
    print(f"  {len(FIXTURES)}/{len(FIXTURES)} 條 fixture 對得上,尺可以用\n")


def scan_skills(repo):
    """每支 skills/*/SKILL.md 一列 —— 寬尺自己的判定,不問受測物。"""
    rows = []
    root = pathlib.Path(repo) / "skills"
    for md in sorted(root.glob("*/SKILL.md")):
        rel = md.relative_to(repo).as_posix()
        text = md.read_text(encoding="utf-8")
        calls = [(i, l.strip()) for i, l in enumerate(text.splitlines(), 1)
                 if CALLS_CLASSIFY.search(l)]
        overclaims = [s for s in sentences(text) if flags_overclaim(s)]
        rows.append(dict(
            file=rel,
            skill=md.parent.name,
            calls=calls,
            says_hard_rule=bool(SAYS_HARD_RULE.search(text)),
            says_dont_flip=bool(SAYS_DONT_FLIP.search(text)),
            overclaims=overclaims,
            bounded=bool(BOUNDED.search(text)),
        ))
    return rows


def scan_signposts(repo):
    """整個 repo 還有沒有叫人去動 judgement 旗標的字。"""
    hits, scanned = [], []
    root = pathlib.Path(repo)
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        # 只看 repo 內的相對路徑 —— 第一版拿絕對路徑的 parts 比,而這份 repo 的
        # worktree 就住在 `…/Skills/.git/batch-worktrees/120/` 底下,結果每一支檔
        # 的 parts 裡都有 `.git`,整個掃描被跳光、永遠回 0 筆。
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.suffix.lower() not in TEXT_SUFFIX:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned.append(rel.as_posix())
        for i, line in enumerate(text.splitlines(), 1):
            if SIGNPOST.search(line):
                hits.append((rel.as_posix(), i, line.strip()))
    assert len(scanned) > 20, f"只掃到 {len(scanned)} 支檔 —— 尺啞了,別信下面的 0 筆"
    return hits, scanned


def run_gate(repo, rel):
    """把一支守門當黑箱跑:回 (exit code, 它印的最後幾行)。"""
    p = subprocess.run([sys.executable, rel, "--self-check"], cwd=repo,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    out = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
    return p.returncode, out[-1] if out else "(沒輸出)"


def guard_population(repo, candidates):
    """反推受測物的母體:把某支 SKILL.md 掏空,看守門紅不紅。

    黑箱 —— 只讀 exit code。紅 = 那支檔在守門的母體裡;綠 = 它根本沒被看過。
    """
    verdict = {}
    with tempfile.TemporaryDirectory() as tmp:
        copy = pathlib.Path(tmp) / "repo"
        shutil.copytree(repo, copy,
                        ignore=shutil.ignore_patterns(*SKIP_DIRS))
        base_rc, _ = run_gate(copy, GUARD_BATCH)
        for rel in candidates:
            path = copy / rel
            pristine = path.read_text(encoding="utf-8")
            path.write_text("# gutted by 120-wide.py\n", encoding="utf-8")
            rc, msg = run_gate(copy, GUARD_BATCH)
            path.write_text(pristine, encoding="utf-8")
            verdict[rel] = (rc, msg)
    return base_rc, verdict


def main(repo):
    self_test()
    repo = str(pathlib.Path(repo).resolve())
    rows = scan_skills(repo)
    signposts, scanned = scan_signposts(repo)

    print(f"母體:{repo}/skills/*/SKILL.md,共 {len(rows)} 支")

    print("\n==== 寬尺:哪幾支宣稱要走 batch.py 的 classify ====")
    callers = [r for r in rows if r["calls"]]
    for r in callers:
        print(f"  {r['file']}  ({len(r['calls'])} 行提到)")
        for ln, txt in r["calls"][:3]:
            print(f"      :{ln}: {txt[:88]}")
        if len(r["calls"]) > 3:
            print(f"      … 另外 {len(r['calls']) - 3} 行")
    if not callers:
        print("  (一支都沒有 —— 寬尺自己壞了,先修尺)")

    print("\n==== 寬尺:那幾支的散文有沒有把 #120 三件事講出來 ====")
    print(f"  {'檔案':<34} {'(a)硬規則蓋過':<14} {'(b)不准翻旗標':<14} (c)天花板收邊")
    gaps = []
    for r in callers:
        a = "有" if r["says_hard_rule"] else "沒有"
        b = "有" if r["says_dont_flip"] else "沒有"
        c = "沒有疑似過度宣稱" if not r["overclaims"] else f"疑似 {len(r['overclaims'])} 句"
        print(f"  {r['file']:<34} {a:<16} {b:<16} {c}")
        if not r["says_hard_rule"]:
            gaps.append((r["file"], "(a) 沒有任何一句說硬規則蓋過 client 的 override"))
        if not r["says_dont_flip"]:
            gaps.append((r["file"], "(b) 沒有任何一句叫 agent 不要自己翻 judgement 旗標"))
        for s in r["overclaims"]:
            gaps.append((r["file"], f"(c) 疑似過度宣稱:{s[:70]}"))

    print("\n==== 寬尺:整個 repo 對降級回路的疑似過度宣稱(不限 caller)====")
    all_over = [(r["file"], s) for r in rows for s in r["overclaims"]]
    if all_over:
        for f, s in all_over:
            print(f"  [寬] {f}: {s[:90]}")
    else:
        print("  (一句都沒撈到)")

    print("\n==== 寬尺:整個 repo 還有沒有『去改 judgement 旗標』的指路殘留 ====")
    if signposts:
        for f, ln, txt in signposts:
            print(f"  [寬] {f}:{ln}: {txt[:100]}")
    else:
        print("  (0 筆 —— repo 裡沒有任何一行叫人去動旗標)")

    print("\n==== 受測物黑箱:兩支守門現在的臉色 ====")
    rc_batch, msg_batch = run_gate(repo, GUARD_BATCH)
    rc_val, msg_val = run_gate(repo, GUARD_VALIDATE)
    print(f"  {GUARD_BATCH} --self-check    -> exit {rc_batch}  {msg_batch}")
    print(f"  {GUARD_VALIDATE} --self-check -> exit {rc_val}  {msg_val}")

    print("\n==== 受測物黑箱:它的母體到底有幾支檔(掏空反推)====")
    cand = [r["file"] for r in rows]
    base_rc, verdict = guard_population(repo, cand)
    print(f"  對照組(沒掏空任何檔):exit {base_rc}")
    watched, unwatched = [], []
    for rel in cand:
        rc, msg = verdict[rel]
        (watched if rc else unwatched).append(rel)
        mark = "看得到" if rc else "看不到"
        print(f"  掏空 {rel:<34} -> exit {rc}  [{mark}]")
    print(f"\n  守門看得到的:{len(watched)} 支 {watched}")
    print(f"  守門看不到的:{len(unwatched)} 支")

    print("\n==== 差額 1:寬尺多撈、受測物放行的(逐筆判讀)====")
    guarded = set(watched)
    extra = []
    for f, why in gaps:
        extra.append((f, why, "守門的母體裡" if f in guarded else "守門根本沒看這支"))
    for f, ln, txt in signposts:
        extra.append((f"{f}:{ln}", f"指路殘留:{txt[:60]}", "守門沒有掃全 repo"))
    if extra:
        print(f"寬尺多撈 {len(extra)} 筆 —— 每一筆都要在報告裡判讀:")
        for f, why, where in extra:
            print(f"  [多撈] {f}  {why}   ({where})")
    else:
        print("寬尺多撈 0 筆 —— 兩把尺對這份母體的結論一致")

    print("\n==== 差額 2:受測物咬到、寬尺沒撈到的 ====")
    missed = []
    if rc_batch or rc_val:
        missed.append("守門現在就是紅的,而寬尺對出貨檔沒有抱怨 —— 逐條讀上面的訊息")
    # 寬尺對「守門看得到」的那支有沒有結論
    for rel in watched:
        row = next(r for r in rows if r["file"] == rel)
        if row["says_hard_rule"] and row["says_dont_flip"] and not row["overclaims"]:
            continue
        # 有抱怨的話上面已經列了,這裡只找「守門咬、寬尺完全沒意見」的
    if not missed:
        print("  (無 —— 守門全綠,寬尺對出貨檔也沒有抱怨)")
    else:
        for m in missed:
            print(f"  [寬尺漏] {m}")

    # 這支的輸出不是綠/紅,是一份等人看的清單 —— 永遠 exit 0
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
