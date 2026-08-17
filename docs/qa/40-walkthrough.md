# QA #40 — npx 實裝驗收(Claude Code + Codex 全域,`/next` 與 `$next`)

票上「覆蓋驗收項」= spec 驗收清單第 1–5 條(另加票面 checkbox「`npx skills update` 拉到新版」)。
本切片沒有瀏覽器 UI,不跑 Playwright;QA 環境 = 純 CLI + **乾淨 fake HOME**(全新空目錄當
`HOME`/`USERPROFILE`,不碰本機既有安裝)。所有結果 QA 自己重跑,不採信 build comment 的自陳。

**一鍵重開指令**(client-demo 直接抄):

```bash
# regression(在 repo 根)
python scripts/validate.py && python scripts/validate.py --self-check && python scripts/install.py --self-check

# 乾淨環境實裝(fake HOME,不動本機)
export HOME="$PWD/qa40home" USERPROFILE="$HOME"; mkdir -p "$HOME"
npx -y skills add c3lew/Skills -g -a claude-code -a codex -y
ls "$HOME/.claude/skills" | wc -l ; ls "$HOME/.agents/skills" | wc -l
```

---

### Step 0 — regression suite

```
$ python scripts/validate.py
OK validate green
exit=0

$ python scripts/validate.py --self-check
OK validate self-check green
exit=0

$ python scripts/install.py --self-check
FAIL skills/bad: missing SKILL.md      # 預期輸出:self-check 故意造紅 repo 驗「紅就拒裝」
OK install self-check green
exit=0

$ git status --short
(clean)
$ git rev-list --left-right --count origin/main...HEAD
0	0
```

全綠。

### Step 1 — 驗收句 1 照字面跑(不加旗標)

```
$ export HOME=<fake>; export USERPROFILE=$HOME
$ mkdir qa40proj && cd qa40proj
$ npx -y skills add c3lew/Skills -y
  ✓ .\.agents\skills\qa    universal: Amp, Antigravity, ..., Codex +14 more
                           symlinked: Claude Code, Eve
  ... (15 個)
  Done!
exit=0

$ ls -a .          # 落在當下工作目錄,不是 HOME
.agents  .claude  agent  skills-lock.json
$ ls .agents/skills | wc -l
15
$ ls -aR "$HOME"   # fake HOME 完全沒被碰
.  ..
```

→ **不加 `-g` 是 project-level**:15 個 skill 都在,但落在當下目錄的 `.agents/skills/`,
`~/.claude/skills` 從未被建立。換個專案就叫不到。驗收句照字面的「Claude Code 的全域位置」不成立。

### Step 2 — 驗收句 1 + 2,用 README 現在寫的指令

```
$ npx -y skills add c3lew/Skills -g -a claude-code -a codex -y
  Done!  exit=0

$ ls "$HOME/.claude/skills" | wc -l
15
$ ls -la "$HOME/.claude/skills"        # 全部是 symlink → .agents/skills
lrwxrwxrwx build -> <HOME>/.agents/skills/build
lrwxrwxrwx client-demo -> <HOME>/.agents/skills/client-demo
... (15 條)

$ ls "$HOME/.agents/skills"            # 實體本體
build client-demo close implement maintain next pm-intake qa retro
slice-tickets to-spec to-tickets tracking-viz triage ui-mockup   # 15

$ ls -a "$HOME/.codex"
ls: cannot access '.codex': No such file or directory
```

→ Claude Code 全域位置 15 個 ✅。Codex 那半落在 **`~/.agents/skills/`(cross-agent root)**,
`~/.codex/skills/` 從未被建立 — spec 寫的落點與 CLI 實況不同(build 已在票上回寫更正)。
Codex 讀得到 `~/.agents/skills/` 由 Step 5 實跑佐證。

### Step 3 — 驗收句 3:安裝後的引用掃描(獨立 scanner)

不用 repo 自己的 `validate.py`(它只掃 `SKILL.md`),另寫 scanner 掃安裝後每個 skill 的
**所有 `*.md`**,以 skill 目錄為基準解析 markdown link + 反引號路徑:

```
$ python refcheck.py "$HOME/.agents/skills"
skills=15 refs_checked=23 missing=9
MISSING client-demo\references\pm-interview.md -> docs/specs/maintain.md
MISSING maintain\references\pm-interview.md -> docs/specs/maintain.md
MISSING pm-intake\references\pm-interview.md -> docs/specs/maintain.md
MISSING tracking-viz\SKILL.md -> dashboard.html
MISSING triage\SKILL.md -> CONTEXT.md
MISSING triage\OUT-OF-SCOPE.md -> dark-mode.md / plugin-system.md /
                                  graphql-api.md / .out-of-scope/dark-mode.md
$ python refcheck.py "$HOME/.claude/skills"     # 走 symlink,同樣 9 筆
```

逐筆分類:

| ref | 判定 |
|-----|------|
| `tracking-viz/SKILL.md -> dashboard.html` | 誤報 — 是「寫到**目標專案** repo 根」的產出檔 |
| `triage/SKILL.md -> CONTEXT.md` | 誤報 — 目標專案的檔案 |
| `triage/OUT-OF-SCOPE.md -> dark-mode.md` 等 4 筆 | 誤報 — ``` 圍欄裡的目錄示意圖 / 範例 |
| `*/references/pm-interview.md -> docs/specs/maintain.md`(3 份 byte 相同副本) | **真斷連結** — 紀律副本裡的「mini-intake(見 `docs/specs/maintain.md`)」;該檔在來源 repo 有(2774 bytes),安裝只複製 skill 目錄,裝完讀不到 |

根因:`validate.py` 的「引用不得跑出 skill 目錄」規則只掃 `SKILL.md`,`references/` 底下
檔案的引用完全沒進掃描範圍 — 正是 spec 拍板④要堵的洞漏了一半。

`references/` 副本本身都在(`pm-interview.md`、`tech-decisions.md` 讀得到);
`tech-decisions.md` 內部無 path 引用。

### Step 4 — 驗收句 4:Claude Code 跑 `/next`

fake HOME 只有 Step 2 裝進去的 skill,沒有 CLAUDE.md、沒有自訂設定(只複製登入憑證),
工作目錄 = 本 repo:

```
$ claude -p "/next"
## 推薦
- **`/qa #40`(Codex: `$qa #40`)(Recommended)** — #40 的 build 已收尾…
- 替代:`/tracking-viz` — dashboard 還停在「開工 `/build #40`」,已經過期
**現場一句話:** #39 已結案,#40 build 完(388e810、08f6deb),現在卡在等 QA 驗收。
```

輸出完全吻合 `next` skill §3 規定的格式(推薦標 `(Recommended)` + 雙寫 + 替代 1–2 + 現場
一句話),且照 §1 先找票上交棒 comment → 推 `/qa #40`。fake HOME 沒有 CLAUDE.md,
`(Recommended)` 這個慣例只可能來自安裝的 skill 本身。

註:該 run 的 `gh` 被 permission 擋(fake HOME 沒複製權限設定),它退回讀 dashboard + git log
仍給出正確下一步 — 環境限制,非產品行為。

### Step 5 — 驗收句 5:Codex 跑 `$next`

```
$ codex exec --sandbox read-only '$next'
ERROR windows sandbox: CreateProcessAsUserW failed: 5 (存取被拒)   # shell 工具,環境限制
mcp: codex_apps/github.fetch_issue / fetch_issue_comments ...      # 改用 GitHub MCP 讀現場
- **推薦指令(Recommended)**:`/qa #40`(Codex:`$qa #40`)
- **替代選項**:`/build #42`(Codex:`$build #42`)
**現場:**主線目前停在 #40 等 QA;通過後才會解鎖 #41 的 Codex `$build → $qa` 端到端驗證。
```

同樣吻合 skill 的固定格式與「先找交棒棒」規則。這是 `$next` 只存在於 `~/.agents/skills/`
的 fake HOME 裡跑出來的 → Codex 確實讀該落點。
sandbox spawn 失敗是本機 Windows 環境限制,它 fallback 到 MCP 後照常完成。

### Step 6 — 票面 checkbox:`npx skills update` 拉到新版

不推 probe commit 汙染 repo,改讓**本地端變舊**(等價於遠端變新):把 lock 檔裡 `next` 的
`skillFolderHash` 改成假值、並把安裝樹的 `next/SKILL.md` 內容改壞,再跑 update:

```
$ npx -y skills update -g -y
Checking skills from source: c3lew/Skills
Found 1 global update(s)
Updating next…
  ✓ Updated next

$ grep -c "QA40-TAMPERED" "$HOME/.agents/skills/next/SKILL.md"
0                        # 改壞的字消失
$ grep -o "整條產線的問路亭" "$HOME/.agents/skills/next/SKILL.md"
整條產線的問路亭          # 遠端原文回來了
```

→ update 會比對遠端 folder hash、抓新版覆蓋本地。「先 push 再 update」那條路徑 build
已用 `08f6deb` 實跑過,本輪驗的是 fetch→overwrite 機制本身(差別只在哪一邊比較新)。

---

### Step 7 — 獨立 judge 判定

乾淨 subagent,只餵五條驗收原句 + 上面的證據,不餵實作脈絡與本 session 的判斷:

| # | 驗收原句 | 判定 |
|---|---------|------|
| 1 | 裸指令裝 15 個到 Claude Code 全域位置 | **fail**(works-but-wrong)|
| 2 | 加 `-a codex` 裝到 Codex 全域位置 | **fail**(works-but-wrong)|
| 3 | 裝完內部引用全部讀得到 | **fail** |
| 4 | Claude Code `/next` 讀現場給下一步 | pass |
| 5 | Codex `$next` 讀現場給下一步 | pass |
| 6 | (票面 checkbox)`npx skills update` 拉到新版 | pass |

judge 理由摘要:
- 1、2 是同一個根因 — 驗收句寫的那條裸指令預設落專案目錄,`~/.codex/` 從未被建立。E2 能達成全域,但那是「加了旗標的另一條指令」,不是原句斷言的那件事。
- 3 是獨立缺陷 — 三份紀律副本指向沒被一起安裝的 `docs/specs/maintain.md`;repo 自家 lint 綠燈不構成反證,缺陷正好在它的盲區(不掃 `references/`)。
- 4、5 的環境限制(`gh` 被擋 / Windows sandbox spawn 失敗)不影響判定,兩邊都吻合 skill 規定的格式與「先找交棒棒」規則,證明安裝的 skill 內容真的生效。
- 6 的作法有辨識力:同時驗了偵測(hash 比對)與覆寫(內容還原)。

### 開票

- **#45(blocking)** — 驗收清單第 1、2 條原句與 CLI 實況不符,需 client 追認更正。非 code bug。
- **#46(blocking)** — `references/pm-interview.md → docs/specs/maintain.md` 裝完斷連結 + `validate.py` 不掃 `references/`。

### 未涵蓋範圍

- **spec 驗收清單第 6–10 條**不在本票的「覆蓋驗收項」段(第 6 條 Codex 端到端 `$build → $qa` 屬 #41)。
- **其他 agent**(Cursor / Gemini 等)未實測 — spec 明確 out of scope。
- 兩條安裝路徑**混用**(A 的 symlink 被 B 的實體副本蓋掉)只有 build 側實測紀錄,本輪未獨立重驗。
- `claude -p` 那個 run 的 `gh` 被 permission 擋、`codex exec` 的 shell 在 Windows sandbox spawn 失敗,兩者皆為本機環境限制,非產品行為。

---

# 第二輪(blocking #45 / #46 修完後重跑)

repo HEAD = `origin/main` = `d1f9849`,working tree clean。oracle 換成 **client 在 #40
追認更正後的第 1、2 條**(舊句已作廢),第 3–5 條不變,另加票面 checkbox 第 6 條。
全程新開一個乾淨 fake HOME(安裝前只有 `.` 與 `..`),不沿用第一輪的目錄。

**一鍵重開指令**(client-demo 直接抄,取代上面那份):

```bash
# regression(在 repo 根)
python scripts/validate.py && python scripts/validate.py --self-check && python scripts/install.py --self-check

# 乾淨環境實裝(fake HOME,不動本機)
export HOME="$PWD/qa40home" USERPROFILE="$HOME"; mkdir -p "$HOME"
npx -y skills add c3lew/Skills -g -a claude-code -a codex -y
ls "$HOME/.claude/skills" | wc -l ; ls "$HOME/.agents/skills" | wc -l
```

### R2 Step 0 — regression suite

```
$ python scripts/validate.py            -> OK validate green            exit=0
$ python scripts/validate.py --self-check -> OK validate self-check green exit=0
$ python scripts/install.py --self-check
FAIL skills/bad: missing SKILL.md       # 預期輸出:self-check 內部的負面測試 fixture
OK install self-check green             exit=0
$ git status --short                    -> (clean)
$ git rev-parse HEAD origin/main        -> d1f9849 / d1f9849
```

全綠。

### R2 Step 1 — 更正後的驗收句 1 + 2

```
$ export HOME=<新空目錄>; export USERPROFILE=<同一目錄>
$ ls -a "$HOME"                          -> .  ..
$ npx -y skills add c3lew/Skills -g -a claude-code -a codex -y
  ✓ ~\.agents\skills\<name>   universal: Codex   symlinked: Claude Code   (15 個)
  Done!

$ ls "$HOME/.claude/skills" | wc -l      -> 15
$ ls -l "$HOME/.claude/skills"           # 15 行全部是 symlink,無例外
lrwxrwxrwx build       -> <HOME>/.agents/skills/build
... (15 條)
$ ls "$HOME/.agents/skills" | wc -l      -> 15
$ ls -a "$HOME"                          -> .  ..  .agents  .claude
$ ls "$HOME/.codex"                      -> No such file or directory
```

→ 兩條更正句都成立:Claude Code 全域 15 個 symlink → `~/.agents/skills/` 實體本體,
`~/.codex/` 從未被建立。

### R2 Step 2 — 驗收句 3:安裝後引用可讀性

(a) 拿 repo 的 `validate()` 對**安裝後的樹**跑,repo root 參數指到不存在的目錄
(模擬另一台機器只有安裝樹):

```
$ validate(~/.agents/skills, ~/no-such-repo)   -> errors: 0
$ validate(~/.claude/skills, ~/no-such-repo)   -> errors: 0   # 走 symlink 那棵
```

(b) 獨立於該 lint、QA 自寫的掃描器掃安裝樹所有 `*.md`:

```
unresolved markdown links: 0
unresolved backtick .md refs: 6
  triage/OUT-OF-SCOPE.md:58,75,76  dark-mode.md / graphql-api.md / plugin-system.md / .out-of-scope/dark-mode.md
  triage/SKILL.md:77               CONTEXT.md
```

這 6 筆與第一輪同一批誤報 — 講的是**使用者自己專案**的檔案 / 圍欄內示意圖,不是要一起安裝的檔案。

(c) 第一輪抓到的真斷連結(#46)重掃:

```
$ grep -rn "docs/specs/maintain.md" ~/.agents/skills/     -> 無任何 match
$ grep -rn "mini-intake" ~/.agents/skills/*/references/pm-interview.md
client-demo|maintain|pm-intake /references/pm-interview.md:3:
  「…maintain 進件時走的 mini-intake 是輕量版 — 一樣過兩軸,但只問到『夠開一張票』就收。」
```

→ 三份副本改寫成自足句子,不再指向未安裝的檔案。第 3 條清了。

### R2 Step 3 — 驗收句 4:Claude Code `/next`

fake HOME 只額外複製登入憑證 `.claude/.credentials.json`,沒有任何 skill / 設定 / hook。

```
$ claude -p "/next"    (cwd = repo)
**下一棒:`/qa #40`(Codex: `$qa #40`)** (Recommended)
#40 上一輪 QA 開了兩張 blocking(#45、#46),兩張都已結案,client 也追認了第 1、2 條新原句。
blocking 清零 …
- **代價/前提**:要在乾淨 fake HOME 重跑一次實裝…
- **接著會是**:#40 綠 → `/client-demo #40` → `/close #40`,然後才解鎖 #41。
**替代選項**:`/build #42`、`/build #43`
**現場一句話**:#35 的 6 張切片已關到剩 #40、#41…
```

吻合 `next` skill 規定的格式(推薦 `(Recommended)` + 雙寫 + 替代 + 現場一句話),
且讀到最新現場(#45/#46 已結案、client 追認)。

### R2 Step 4 — 驗收句 5:Codex `$next`

同一 fake HOME,只額外複製 `.codex/auth.json` 與 `config.toml` 供登入。

```
$ codex exec '$next'    (cwd = repo)
- **推薦指令 (Recommended):** `/qa #40`(Codex:`$qa #40`)— 兩張 blocking 票 #45、#46 已關閉,現在應重跑驗收。
- **替代:** `/build #42`(Codex:`$build #42`)
- **現場:** #40 正在等 QA;#41 仍被 #40 阻擋。
```

`$next` 只存在於 `~/.agents/skills/` → Codex 確實讀該落點。
(過程中有一段讀本機 session 摘要的 PowerShell 報 InvalidOperation,屬 codex 記憶機制,
不影響最終輸出。)

### R2 Step 5 — 票面 checkbox 第 6 條:`npx skills update`

先驗 no-op 半:

```
$ npx -y skills update -g -y   -> ✓ All global skills are up to date
```

再驗 fetch→overwrite 半(讓本地變舊,等價於遠端變新,不推 probe commit 汙染 repo):

```
$ echo "QA40R2-TAMPERED" >> ~/.agents/skills/next/SKILL.md
$ 把 ~/.agents/.skill-lock.json 的 skills.next.skillFolderHash 改成 000…0
$ npx -y skills update -g -y
Found 1 global update(s) / Updating next… / ✓ Updated next / ✓ Updated 1 skill(s)

$ grep -c "QA40R2-TAMPERED" ~/.agents/skills/next/SKILL.md   -> 0     # 竄改消失
$ head -6 ~/.agents/skills/next/SKILL.md                     -> 遠端原文回來
$ 讀 lock:next hash = 020dce7a…                              # 寫回正確值
$ npx -y skills update -g -y   -> ✓ All global skills are up to date  # 不重複報
```

只有 `next` 被更新,其餘 14 個未動 → per-skill hash 比對。

### R2 Step 6 — 獨立 judge 判定

乾淨 subagent,只餵更正後的驗收原句 + 上面證據,不餵實作脈絡:

| # | 驗收原句 | 判定 |
|---|---------|------|
| 1 | 15 個 skill 進 `~/.claude/skills/`(symlink → `~/.agents/skills/`)| pass |
| 2 | `-a codex` 那半進 `~/.agents/skills/`,非 `~/.codex/skills/` | pass |
| 3 | 裝完內部引用全部讀得到 | pass |
| 4 | Claude Code `/next` 讀現場給下一步 | pass |
| 5 | Codex `$next` 讀現場給下一步 | pass |
| 6 | (票面 checkbox)`npx skills update` 拉到新版 | pass |

judge 對第 6 條先判 fail(只有 no-op 證據),補上 R2 Step 5 後段的竄改實證後改判 pass —
理由是 `QA40R2-TAMPERED` 是本地獨有字串,消失只可能來自「真的抓遠端 bytes 覆寫」。

### blocking

無。#45(驗收句更正)、#46(斷連結 + lint 死角)兩張皆已結案且本輪重驗有效。

### known issues

無。6 筆 backtick 掃描結果逐筆判為誤報,不開票。

### 未涵蓋範圍

- **spec 驗收清單第 6–10 條**不在本票的「覆蓋驗收項」段(第 6 條 Codex 端到端屬 #41)。
- **其他 agent**(Cursor / Gemini 等)未實測 — spec 明確 out of scope。
- 兩條安裝路徑**混用**(A 的 symlink 被 B 的實體副本蓋掉)只有 build 側紀錄,本輪未重驗。
- 第 6 條的「遠端真的長出新 commit」那條路徑本輪用竄改本地等價替代;真 push 版本在第一輪
  用 `08f6deb` 驗過。
- 環境限制非產品行為:fake HOME 需另外複製 `.claude/.credentials.json`、`.codex/auth.json`
  才能登入 CLI;codex 讀本機 session 摘要那段報錯。

---

## 第三輪 — 過關後固化(client-demo 前三條成立,指回 qa)

client 在 #40 逐條點頭、blocking 清零、known issues 為零之後,把本切片的高價值
scenarios 寫進 regression suite。這一輪**不重跑安裝實測**,只動 suite。

### R3 Step 1 — 盤點:哪幾條已經在 suite 裡、哪幾條進不去

| 驗收項 | 固化狀態 | 在哪 |
|--------|---------|------|
| 1 + 2 雙落點(`~/.claude/skills/` + `~/.agents/skills/`,不是 `~/.codex/`)| **已固化**(#40 build 時寫的)| `install.py` self-check:`DEFAULT_DESTS` 兩個落點斷言 + 兩棵樹 snapshot 必須相同 |
| 3 裝完內部引用全部讀得到 | **已固化**(#46 修時寫的)| `validate.py` self-check:拿真的 `references/*.md` 竄改必須變紅;`install.py` self-check:拿一個**空的 repo root** 對安裝後的樹重跑 validate(= 別台機器只拿到 skill 目錄的情況)|
| #45 的 bug class:**文件寫的落點/指令與程式不符** | **本輪新增** | `install.py` 的 `readme_install_issues()` + self-check |
| 4 / 5 `/next`、`$next` 真的在兩個 agent 裡跑起來 | **不固化** | 要 live CLI + 登入 + 網路,不進 suite(理由見下)|
| 6 `npx skills update` 抓新版 | **不固化** | upstream CLI(vercel-labs/skills)的行為 + 網路,不是本 repo 的程式 |

### R3 Step 2 — 新增的 check(#45 bug class)

#45 不是 code bug,是**寫下來的落點跟實況不符** — 而 README 的那行指令正是使用者會
複製去乾淨機器上跑的東西。程式端有 `DEFAULT_DESTS`,文件端沒有任何東西綁住它,兩邊
可以無聲漂開。

`scripts/install.py` 新增 `readme_install_issues(text, dests)`:README 的 `npx skills add`
那行必須帶 `-g`、`-a claude-code`、`-a codex`,`DEFAULT_DESTS` 的兩個落點都要寫在 README
裡,而且 `~/.codex/skills` 不准出現(那就是 #45 講錯的那個路徑)。

跑真 README 綠,竄改必須紅:

```
$ python -c "... readme_install_issues ..."
原文  : []
去 -g : ["README.md: install command missing '-g'"]
改落點: ["README.md: landing point '~/.agents/skills/' not documented",
         'README.md: Codex reads ~/.agents/skills, not ~/.codex/skills (#45)']
```

### R3 Step 3 — suite 全綠

```
$ python scripts/validate.py && python scripts/validate.py --self-check && python scripts/install.py --self-check
OK validate green
OK validate self-check green
FAIL skills/bad: missing SKILL.md      <- 這行是「紅 repo 必須拒裝」那條斷言自己印的,不是失敗
OK install self-check green
```

### 沒固化的兩條,為什麼

- **第 4、5 條(`/next` / `$next` 真的跑)**:要起兩個 CLI、要登入憑證、要網路,一次幾十秒
  起跳,而且失敗多半來自環境不是來自 repo — 放進每次都要跑的 suite 只會製造假紅。
  它們的可測部分(skill 檔案裝到位、內容可讀、引用不斷)已經被 1/2/3 條的 check 蓋掉。
- **第 6 條(`npx skills update`)**:行為在 upstream CLI 手上,本 repo 改不動也不該替它測。
