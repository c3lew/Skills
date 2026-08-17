# QA #46 — 紀律副本裝完斷連結 + `validate` 掃不到 `references/`

bug fix 票,範圍 = 該 bug 的重現 scenario + regression suite。重現 scenario 對應 spec 驗收清單
**第 3 條**(「裝完之後,skill 內部引用的檔案(紀律副本等)全部讀得到 — 沒有任何『找不到檔案』」)。
沒有瀏覽器 UI,不跑 Playwright;QA 環境 = 純 CLI + **乾淨 fake HOME**(全新空目錄當
`HOME`/`USERPROFILE`,不碰本機既有安裝)。所有結果 QA 自己重跑,不採信 build comment 的自陳。

**一鍵重開指令**(client-demo 直接抄,沿用 #40):

```bash
# regression(在 repo 根)
python scripts/validate.py && python scripts/validate.py --self-check && python scripts/install.py --self-check

# 乾淨環境實裝(fake HOME,不動本機;cwd 另開空目錄,才分得出全域/專案)
export HOME="$PWD/qa46home" USERPROFILE="$HOME"; mkdir -p "$HOME/proj"; cd "$HOME/proj"
npx -y skills add c3lew/Skills -g -a claude-code -a codex -y
ls "$HOME/.claude/skills" | wc -l ; ls "$HOME/.agents/skills" | wc -l
```

---

### Step 0 — regression suite

```
$ python scripts/validate.py
OK validate green                       exit=0
$ python scripts/validate.py --self-check
OK validate self-check green            exit=0
$ python scripts/install.py --self-check
FAIL skills/bad: missing SKILL.md       # 預期輸出:self-check 故意造紅 repo 驗「紅就拒裝」
OK install self-check green             exit=0

$ git status --short
(clean)
$ git rev-list --left-right --count origin/main...HEAD
0	0
```

全綠,且本地=遠端 → 下面 `npx` 抓到的就是修復版(c34514f)。

### Step 1 — 乾淨 fake HOME 實裝

```
$ export HOME=<fake>; export USERPROFILE=$HOME; mkdir -p $HOME/proj; cd $HOME/proj
$ npx -y skills add c3lew/Skills -g -a claude-code -a codex -y
  Done!   exit=0
$ ls -a .                       # cwd 沒被寫東西 → 確實是全域安裝
.  ..
$ ls "$HOME/.claude/skills" | wc -l   → 15
$ ls "$HOME/.agents/skills" | wc -l   → 15
```

(#40 已驗過落點語意,本輪只需要一棵「裝完的樹」來掃引用。)

### Step 2 — 驗收句 3:安裝後的引用掃描(獨立 scanner)

不用 repo 自家 `validate.py` 當 oracle — 缺陷當初正好在它的盲區裡。QA 另寫 scanner,
**刻意不套 validate 的任何豁免規則(dot-dir 等),寬到會誤報**,再逐筆判讀;這樣才驗得到
「新豁免規則有沒有順手把真斷連結也蓋掉」。掃安裝樹 15 個 skill 的全部 25 個 `*.md`:

```
$ python refcheck.py "$HOME/.agents/skills"        # markdown link + 反引號帶「/」的路徑
skills=15 refs_checked=18 missing=7
MISSING retro/SKILL.md          -> python scripts/install.py
MISSING retro/SKILL.md          -> python scripts/validate.py
MISSING to-tickets/SKILL.md     -> .scratch/<feature-slug>/issues/<NN>-<slug>.md
MISSING triage/AGENT-BRIEF.md   -> .out-of-scope/*.md
MISSING triage/AGENT-BRIEF.md   -> .out-of-scope/<concept>.md
MISSING triage/OUT-OF-SCOPE.md  -> .out-of-scope/dark-mode.md
MISSING triage/SKILL.md         -> .out-of-scope/*.md

$ 第二輪(更寬:連裸檔名也當 ref,對齊 #40 scanner 的廣度)
bare_refs_checked=8 missing=5
MISSING-bare tracking-viz/SKILL.md  -> dashboard.html
MISSING-bare triage/SKILL.md        -> CONTEXT.md
MISSING-bare triage/OUT-OF-SCOPE.md -> dark-mode.md / graphql-api.md / plugin-system.md

$ python refcheck.py "$HOME/.claude/skills"        # 走 symlink,兩輪結果相同
```

12 筆全數判為 scanner 誤報:

| ref | 判定 |
|-----|------|
| `retro/SKILL.md ->` 那兩筆 | 誤報 — shell **指令**不是檔案引用,且 retro 的工作對象本來就是本 repo |
| `.scratch/…`、`.out-of-scope/…`(4 筆) | 誤報 — 使用者**目標專案**的目錄,連 `<佔位符>` 都在 |
| `dashboard.html`、`CONTEXT.md` | 誤報 — skill 寫進目標專案 repo 根的產出檔 |
| `OUT-OF-SCOPE.md` 三個裸檔名 | 誤報 — ``` 圍欄裡的目錄示意圖 |

**關鍵對照**:#40 用同樣方法在同樣位置抓到的 3 筆真斷連結,本輪全數消失。

```
$ grep -rn "docs/specs/maintain.md" "$HOME/.agents/skills"
(none)
$ md5sum <三份 references/pm-interview.md> docs/disciplines/pm-interview.md
b3b5efde3e6a0125f6a5a1ece25c0f32   # 四份一致
```

裝完的那句話現在讀起來:「…maintain 進件時走的 mini-intake 是輕量版 — 一樣過兩軸,但只問到
『夠開一張票』就收。」不再指向任何檔案。

另驗新豁免規則的前提:`find <安裝樹> -type d -name ".*"` → **沒有任何 dot-directory 被出貨**,
所以「dot-dir 底下的路徑一律不當 link」不可能誤放一個真的能在 skill 內解析的引用。

### Step 3 — 第二條安裝路徑:repo 自家 installer

票上寫「修完:validate 綠 → `python scripts/install.py`」。用另一個乾淨 fake HOME 實跑:

```
$ HOME=<fake2> python scripts/install.py
OK installed build -> …/.claude/skills/build   … (15+15 全部 OK)   exit=0
$ python refcheck.py "<fake2>/.agents/skills"
skills=15 refs_checked=18 missing=7      # 與 npx 那棵樹逐筆相同,3 筆真斷連結同樣不存在
```

### Step 4 — 突變測試:這個洞現在會不會被自家 lint 抓到

在 repo 的**暫存複本**上跑(工作區不動)。複本未變動時 `OK validate green`。

```
突變 A — 把當初那句斷連結原句寫回 skills/pm-intake/references/pm-interview.md:
FAIL skills/pm-intake/references/pm-interview.md: reference 'docs/specs/maintain.md'
     escapes the skill dir (only resolves from outside — breaks once installed)
FAIL skills/pm-intake/references/pm-interview.md: out of sync with docs/disciplines/…
exit=1

突變 C — 在既非 SKILL.md、也不在 references/ 的檔案(skills/triage/OUT-OF-SCOPE.md)加真 escape:
FAIL skills/triage/OUT-OF-SCOPE.md: reference '../../docs/blueprint.md' escapes the skill dir …

突變 D — 在另一個 skill 的 references 副本加不存在的 ref:
FAIL skills/client-demo/references/tech-decisions.md: broken reference 'docs/nope.md'
```

A 證明原本隱形的缺陷現在紅、且錯誤訊息指名 `references/` 那個檔;C/D 證明覆蓋範圍真的是
「skill 目錄下所有 `*.md`」,不是「SKILL.md + references/」。

### Step 5 — 誤報防線是規則層,不是改文件閃 linter

```
$ git log --oneline -1 -- skills/triage/OUT-OF-SCOPE.md
c52d4c4 …(#33 收編那次)          # 不是本次修復 commit
$ git show --stat c34514f
docs/disciplines/pm-interview.md | scripts/validate.py | 三份 skills/*/references/pm-interview.md
5 files changed
```

`OUT-OF-SCOPE.md` 原文一個字沒動,而未突變的複本 lint 全綠 → 它在新規則下是靜的。

---

### Step 6 — 獨立 judge 判定

乾淨 subagent,只餵驗收原句 + 上面的證據,不餵實作脈絡與本 session 的判斷:

| # | 判準 | 判定 |
|---|------|------|
| A | 裝完內部引用全部讀得到 | **pass** |
| B | regression 三支全綠 | **pass** |
| C | 斷連結種回去 lint 要紅、訊息指名 `references/` 檔 | **pass** |
| D | `OUT-OF-SCOPE.md` 原文不動且 lint 全靜 | **pass** |

judge 理由摘要:

- A — 三筆真斷連結在兩條獨立安裝路徑上都消失,且證據來自刻意寫寬、不套受測規則的 scanner;
  12 筆殘留全是可辨識的目標專案路徑/指令/圍欄示意,不是 skill 內部引用。四份 md5 一致
  佐證副本沒漂移。
- B — 三支 exit=0;`install.py --self-check` 那行 FAIL 是它自己造紅 repo 的預期輸出。
- C — 突變 A 直接把 #46 的原句寫回去就紅,而且錯誤訊息帶 `references/` 相對路徑;C/D 兩個
  突變落在不同檔案類型與不同 skill,排除「只對 pm-interview 特判」。
- D — 修復 commit 的 --stat 不含 `OUT-OF-SCOPE.md`,git log 也顯示它最後一次變更在 #33;
  誤報是靠 dot-dir 規則消掉的,不是改措辭。dot-dir 豁免的前提(skill 不出貨 dotdir)有
  `find` 實測佐證,不是紙上推論。

### 結論

**blocking 清零。** 本票沒開新 bug ticket。

### 未涵蓋範圍

- #40 驗收清單第 1、2 條(裸指令的落點語意)不在本票範圍 — 由 **#45** 追認更正。
- #40 的第 4、5 條(`/next`、`$next` 實跑)本輪未重跑;本次改動只碰
  `validate.py` 與紀律副本文字,不影響 skill 呼叫路徑。#40 重跑時一併驗。
- 其他 agent(Cursor / Gemini 等)未實測 — spec 明確 out of scope。
- dot-dir 豁免的成立前提是「skill 不出貨 dot-directory」。今天實測成立;哪天真的要出貨一個
  `.something/` 目錄,這條規則要重看。
- judge 記的兩點證據邊界:(1)引用掃描只掃 `*.md`,非 md 檔裡的引用沒涵蓋;(2)那 12 筆
  「是誤報」是 QA 逐筆人判的,效力等同人工 review,不是自動化保證。兩點都不影響判定。
