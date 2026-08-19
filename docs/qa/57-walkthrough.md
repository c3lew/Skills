# QA walkthrough — #57 快車道接進產線

拿票上的驗收條實測 `/next` 推薦、切票守門、藍圖同步。交付物是 skill 散文 + `validate.py` guard,
沒有 UI、沒有視覺 oracle,不走 Playwright、沒有錄影 — 實錄就是下面這份終端 transcript。

全程 bash xtrace(`PS4='+ '` + `set -x`),指令與輸出在同一份裡,沒有事後 render。
mutation 全部跑在拋棄式暫存目錄的副本上,repo 本體沒被動過(STEP 8 的 `git status` 是證據)。

一鍵重開(client-demo / 之後每輪 QA 直接抄):

```bash
bash scripts/qa/57-walkthrough.sh "$(mktemp -d)/qa57"
```

步驟:

| # | 驗的是 | 對應驗收條 |
| --- | --- | --- |
| 1 | regression suite:五支 self-check + `validate.py` | AC7 |
| 2 | 先印出「照表序推薦最上面的」那條規則本身(表序 = 優先序),再證明批次那列的行號小於單張 `/build` 那列;那列本身帶「`/build #N` 列替代」 | AC1 |
| 3 | 推薦行雙寫:推薦半 `/build-batch #51`(Codex: `$build-batch #51`)與替代半 `/build #47`(Codex: `$build #47`)在同一行 | AC2 |
| 4 | 4a 從 `/next` 自己那邊印出它指向 `batch.py`,那支檔存在,裡面真的有 `def plan_batch`(L74)、CLI 走的就是它(L522 `format_plan(plan_batch(...))`),而 `/build-batch` 指的是同一個路徑;4b 把 `/next` SKILL.md 裡的範例 JSON **原封不動抽出來**餵進去 → 要開 1 張;4c 換成兩張不卡 → 要開 2 張;4d 兩份的計數換算成「命中/不命中」 | AC3 |
| 5 | `slice-tickets` §4 的那一步原文(問句、不自己補邊、不靜靜發佈、有任何一張宣告了就不問) | AC4 |
| 6 | guard 的四個方向:6a 未動過 → 綠;6b 拿**真的** `slice-tickets/SKILL.md` 刪掉那句 → 紅,而且 error 指名那個檔;6c 母體點名(誰上鉤、誰只是提到);6d 母體空了 → `self_check` 自己失敗,而且擋下來的**就是** #57 那條(整份 skills 複製一份只抽掉 `slice-tickets`,其他 guard 的母體都留著) | AC5 |
| 7 | `blueprint.md` 第 4 格的實際內容 | AC6 |
| 9 | **額外,不在驗收條裡** — 同型全掃(掃描器:`scripts/qa/57-guard-sweep.py`):`validate.py` 的 11 個 errors.append 點分成 4 類,受測形狀 prose-keyword 母體 2 個,逐支驗改壞 / 繞過兩方向,外加一支兩方向都咬得到的對照組 | — |
| 8 | repo 本體 `validate.py` 全綠,`git status` 顯示只多了這輪的 QA artifacts | AC7 |

**這份驗不到的**(交給票上 QA 報告的未涵蓋清單):

- **散文的執行者是 agent,不是機器。** STEP 2/3/4a/5/7 驗的是「話寫在那裡、位置對、措辭對、指的檔真的在」,
  不是「agent 讀了真的照做」。真的要驗,得跑一次 `/next` 與一次 `/slice-tickets`,
  而 `/slice-tickets` 那一問會真的發票到 GitHub。
- **STEP 4 驗的是那支檔餵得動、答案分得開**(要開 1 張 vs 2 張),不是 `/next` 執行時真的去餵它。
  4d 的「命中/不命中」換算是這份 walkthrough 自己寫的一小段 python,不是 `/next` 跑出來的。
  L522 是不是 4b/4c 實際走的那一行,靠的是 grep + 輸出形狀吻合,沒有 trace。
- **`/next` SKILL.md 把路徑寫成 `<build-batch skill dir>/batch.py` 這個 placeholder**,
  這份 walkthrough 是人工解析成實際路徑的;沒有證據顯示 agent 會解析成同一個位置。
- **6c 的假陽性那半在這個 repo 是空的** — 母體 1 張(`slice-tickets`)、只提到不呼叫的 0 張。
  「只是提到不算」這條目前只有 `validate.py` 裡的手寫字串斷言在守,沒有真的 skill 在行使它。
- **`docs/blueprint.md` 不在 `validate.py` 的掃描範圍內**(它掃 `skills/*/SKILL.md`),
  所以 AC6 只有這份 transcript 當證據,沒有機器守門。STEP 7 的 `grep '^| 4 |'` 全檔只有一個 hit,
  所以指的是哪一列沒有歧義,但 transcript 沒有印出 Greenfield 那個表頭。
- **STEP 9 是 `echo` / print,不影響 exit status** — 它量到的缺口靠票上的 known issue 追,
  不靠這支 script 變紅。這是刻意的(它不是驗收條),但也代表跑綠不等於那個缺口被修掉。

## Transcript

```
+ echo '==== STEP 1  regression suite(五支 self-check + validate)===='
==== STEP 1  regression suite(五支 self-check + validate)====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ python '/d/Self Project/Skills/scripts/validate.py' --self-check
OK validate self-check green
+ python '/d/Self Project/Skills/scripts/batch.py' --self-check
OK batch self-check green
OK §8a/§8c conflict scenarios green
+ python '/d/Self Project/Skills/scripts/install.py' --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
+ python '/d/Self Project/Skills/scripts/hooks/triage-to-maintain.py' --self-check
OK triage-to-maintain self-check green
+ python '/d/Self Project/Skills/skills/build-batch/batch.py' --self-check
OK batch self-check green
+ echo '==== STEP 2  AC1:/next 路由表新增一列,且排在單張 /build 那列上面 ===='
==== STEP 2  AC1:/next 路由表新增一列,且排在單張 /build 那列上面 ====
+ grep -n ready-for-agent '/d/Self Project/Skills/skills/next/SKILL.md'
28:| ≥2 張 `ready-for-agent` 切片票、彼此不卡(判法見下) | `/build-batch #<spec 票號>`;`/build #N` 列替代 |
29:| 有 `ready-for-agent` 切片票沒開工 | `/build #N` |
33:| 有票但沒有交棒 comment、也沒有 `ready-for-agent`(手開的、或裸跑 `/triage` 分完類的) | `/maintain #N` 補分類 + 補交棒 |
52:餵進去的候選跟 `/build-batch` §1 同一組:**open、帶 `ready-for-agent`、`## Parent` 指向同一份 spec** 的票 — 少了標籤這關,兩張已經在等 QA 的票也會被算成「要開 2 張」,推出一個沒東西可跑的批次。closed 的票照樣餵進去,它們是「卡關解除了沒」的依據。`blocked_by` 從票 body 的 `## Blocked by` 段抓 `#<n>`(平台原生的 dependency 關係優先)。
+ echo '-- 表序就是優先序 —— 先把那條規則本身印出來,不要只用講的'
-- 表序就是優先序 —— 先把那條規則本身印出來,不要只用講的
+ grep -n 照表序推薦最上面的 '/d/Self Project/Skills/skills/next/SKILL.md'
38:同時命中多個(例:一張票在等 QA、另一個 feature 想進 spec)就照表序推薦最上面的,其餘當替代列出。
+ echo '-- 所以批次那列的行號要小於單張那列'
-- 所以批次那列的行號要小於單張那列
+ python - '/d/Self Project/Skills/skills/next/SKILL.md'
批次列 line 28 / 單張列 line 29 -> 批次在上:True
批次列原文:| ≥2 張 `ready-for-agent` 切片票、彼此不卡(判法見下) | `/build-batch #<spec 票號>`;`/build #N` 列替代 |
+ echo '==== STEP 3  AC2:推薦行雙寫 Codex 形式(推薦與替代兩半都要)===='
==== STEP 3  AC2:推薦行雙寫 Codex 形式(推薦與替代兩半都要)====
+ grep -n 'build-batch #51`(Codex: `\$build-batch #51`)' '/d/Self Project/Skills/skills/next/SKILL.md'
56:推薦行照 §3 雙寫:`/build-batch #51`(Codex: `$build-batch #51`),替代是 `/build #47`(Codex: `$build #47`)— 一次一張,慢但不用管平行合併。
+ grep -n '替代是 `/build #47`(Codex: `\$build #47`)' '/d/Self Project/Skills/skills/next/SKILL.md'
56:推薦行照 §3 雙寫:`/build-batch #51`(Codex: `$build-batch #51`),替代是 `/build #47`(Codex: `$build #47`)— 一次一張,慢但不用管平行合併。
+ echo '==== STEP 4  AC3:判斷重用 plan_batch — 不是照抄一份說法,是真的餵得動那支檔 ===='
==== STEP 4  AC3:判斷重用 plan_batch — 不是照抄一份說法,是真的餵得動那支檔 ====
+ echo '-- 4a  /next 自己指向哪支檔(這是 AC3 的主張,先印 /next 那邊)'
-- 4a  /next 自己指向哪支檔(這是 AC3 的主張,先印 /next 那邊)
+ grep -n batch.py '/d/Self Project/Skills/skills/next/SKILL.md'
42:「彼此不卡」不用眼睛看,也不要在這裡另寫一套 — 那份判斷就是 `/build-batch` §3 在跑的那支檔,`build-batch` skill 目錄底下的 `batch.py`。同一份輸入餵進去,「要開」那段 ≥2 張就是命中這一列:
45:python <build-batch skill dir>/batch.py <<'JSON'
+ echo '-- 那支檔存在'
-- 那支檔存在
+ ls -l '/d/Self Project/Skills/skills/build-batch/batch.py'
-rwxr-xr-x 1 user 197121 70838 Aug 19 16:18 /d/Self Project/Skills/skills/build-batch/batch.py
+ echo '-- 它裡面真的有 plan_batch,而且 CLI 走的就是它'
-- 它裡面真的有 plan_batch,而且 CLI 走的就是它
+ grep -n 'def plan_batch' '/d/Self Project/Skills/skills/build-batch/batch.py'
74:def plan_batch(tickets, cap=CAP):
+ grep -n 'plan_batch(data\["tickets"\])' '/d/Self Project/Skills/skills/build-batch/batch.py'
522:        print(format_plan(plan_batch(data["tickets"]), titles))
+ echo '-- 而 /build-batch §3 跑的也是同一支檔(所以「同一支」不是說法,是同一個路徑)'
-- 而 /build-batch §3 跑的也是同一支檔(所以「同一支」不是說法,是同一個路徑)
+ grep -n batch.py '/d/Self Project/Skills/skills/build-batch/SKILL.md'
+ head -3
28:把純資料餵進 [`batch.py`](batch.py),名單的算與印都在裡面,不要自己心算或自己排版:
31:python <skill dir>/batch.py <<'JSON'
79:沒有輸出(`grep` 回 exit 1,正常)就是乾淨的一批,直接往 §6.2。有輸出就把那幾行**原封不動**貼進 `worktrees`,票號由 [`batch.py`](batch.py) 從路徑認 — 別自己讀,認錯一條就是等一下去 merge 一條根本不是這條線開的 branch:
+ echo '-- 4b  /next SKILL.md 裡那段範例 JSON 原封不動抄出來餵進去(48 卡在 47 後面 -> 只開得了 1 張,不命中這一列)'
-- 4b  /next SKILL.md 裡那段範例 JSON 原封不動抄出來餵進去(48 卡在 47 後面 -> 只開得了 1 張,不命中這一列)
+ python - '/d/Self Project/Skills/skills/next/SKILL.md'
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/bac97c90-ad44-4d46-99ba-556fd07f58c1/scratchpad/qa57/example.json
{"tickets": [{"number": 47, "state": "open", "blocked_by": []},
             {"number": 48, "state": "open", "blocked_by": [47]}],
 "titles": {"47": "...", "48": "..."}}+ python '/d/Self Project/Skills/skills/build-batch/batch.py'
要開(1 張):
  #47 ...
排隊(0 張):
  (無)
還卡著(1 張):
  #48 ... — 卡在 #47
+ echo '-- 4c  同一支檔、換成兩張彼此不卡 -> 「要開」2 張,命中批次那一列'
-- 4c  同一支檔、換成兩張彼此不卡 -> 「要開」2 張,命中批次那一列
+ printf '%s\n' '{"tickets": [{"number": 47, "state": "open", "blocked_by": []}, {"number": 48, "state": "open", "blocked_by": []}], "titles": {"47": "一", "48": "二"}}'
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/bac97c90-ad44-4d46-99ba-556fd07f58c1/scratchpad/qa57/two.json
{"tickets": [{"number": 47, "state": "open", "blocked_by": []}, {"number": 48, "state": "open", "blocked_by": []}], "titles": {"47": "一", "48": "二"}}
+ python '/d/Self Project/Skills/skills/build-batch/batch.py'
要開(2 張):
  #47 一
  #48 二
排隊(0 張):
  (無)
還卡著(0 張):
  (無)
+ echo '-- 4d  「要開」只有 1 張時不命中(卡關那張不算)—— 用 4b 那份的計數'
-- 4d  「要開」只有 1 張時不命中(卡關那張不算)—— 用 4b 那份的計數
+ python - '/d/Self Project/Skills/skills/build-batch/batch.py' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/bac97c90-ad44-4d46-99ba-556fd07f58c1/scratchpad/qa57/example.json C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/bac97c90-ad44-4d46-99ba-556fd07f58c1/scratchpad/qa57/two.json
example.json: 要開 1 張 -> 命中批次列:False
two.json: 要開 2 張 -> 命中批次列:True
+ echo '==== STEP 5  AC4:slice-tickets 帶「一張 blocking 邊都沒宣告就回報 client」這一步 ===='
==== STEP 5  AC4:slice-tickets 帶「一張 blocking 邊都沒宣告就回報 client」這一步 ====
+ sed -n '/## 4. Delta:blocking 邊對帳/,/## 5\./p' '/d/Self Project/Skills/skills/slice-tickets/SKILL.md'
## 4. Delta:blocking 邊對帳

切出來的票**一張 blocking 邊都沒宣告**的時候,發佈前回報 client:「這批 N 張彼此都沒有先後關係,對嗎?」等他回答,不要自己補一條邊,也不要靜靜發佈。

真的沒有先後關係是常態(平行切片),但「漏標」跟「真的沒有」在票面上長得一模一樣,而下游 `/build-batch` 完全吃這份宣告:漏標的那批會被算成全部能同時開,兩張改同一個檔案的票就並排跑起來,撞在 merge 那關 — 那時候已經沒人問得到 client 了。切票這關是唯一還問得到的地方。

有任何一張宣告了邊就不問 — 這一問防的是整批一起漏標(切票時根本沒想過先後),不是逐張複查。

## 5. 覆蓋對帳,然後發佈
+ echo '==== STEP 6  AC5:validate.py guard + mutation-bite(拿真的 SKILL.md 咬,不是手寫字串)===='
==== STEP 6  AC5:validate.py guard + mutation-bite(拿真的 SKILL.md 咬,不是手寫字串)====
+ echo '-- 6a  未動過的 slice-tickets:綠'
-- 6a  未動過的 slice-tickets:綠
+ mkdir -p C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/bac97c90-ad44-4d46-99ba-556fd07f58c1/scratchpad/qa57/m/skills/slice-tickets
+ cp '/d/Self Project/Skills/skills/slice-tickets/SKILL.md' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/bac97c90-ad44-4d46-99ba-556fd07f58c1/scratchpad/qa57/m/skills/slice-tickets/SKILL.md
+ python - '/d/Self Project/Skills' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/bac97c90-ad44-4d46-99ba-556fd07f58c1/scratchpad/qa57/m
blocking 相關 error 0 條:[]
+ echo '-- 6b  把那一句從真的 SKILL.md 刪掉 -> guard 要紅,而且要指名 slice-tickets'
-- 6b  把那一句從真的 SKILL.md 刪掉 -> guard 要紅,而且要指名 slice-tickets
+ python - C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/bac97c90-ad44-4d46-99ba-556fd07f58c1/scratchpad/qa57/m/skills/slice-tickets/SKILL.md
已刪掉那句(只刪第一次出現)
+ python - '/d/Self Project/Skills' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/bac97c90-ad44-4d46-99ba-556fd07f58c1/scratchpad/qa57/m
RED: skills/slice-tickets/SKILL.md: publishes tickets via `/to-tickets` but never reports 「一張 blocking 邊都沒宣告」 to the client — a batch that lost every edge looks exactly like one that has none, and /build-batch then opens all of them in parallel
+ echo '-- 6c  假陽性那半:只『提到』/to-tickets(交棒行、路由表)的 skill 不上鉤'
-- 6c  假陽性那半:只『提到』/to-tickets(交棒行、路由表)的 skill 不上鉤
+ python - '/d/Self Project/Skills'
母體(呼叫 /to-tickets 發佈票)共 1 張:['slice-tickets']
只是提到、不上鉤的共 0 張:[]
+ echo '-- 6d  母體空了 -> #57 自己那條 vacuity assert 要當場失敗(不是別條先擋下來)'
-- 6d  母體空了 -> #57 自己那條 vacuity assert 要當場失敗(不是別條先擋下來)
+ echo '   做法:整份 skills 原封不動複製一份,只抽掉唯一呼叫 /to-tickets 的那張(slice-tickets),'
   做法:整份 skills 原封不動複製一份,只抽掉唯一呼叫 /to-tickets 的那張(slice-tickets),
+ echo '   其他 guard 的母體都還在 -> 擋下來的一定是 #57 那條。'
   其他 guard 的母體都還在 -> 擋下來的一定是 #57 那條。
+ python - '/d/Self Project/Skills' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/bac97c90-ad44-4d46-99ba-556fd07f58c1/scratchpad/qa57
假 repo 留下 15 張 skill,抽掉的是 slice-tickets
空母體 -> AssertionError: no skill publishes tickets via `/to-tickets` — mutation has nothing to bite
確認:擋下來的就是 #57 的 vacuity assert
+ echo '==== STEP 7  AC6:blueprint.md Greenfield 第 4 格加註快車道 ===='
==== STEP 7  AC6:blueprint.md Greenfield 第 4 格加註快車道 ====
+ grep -n '^| 4 |' '/d/Self Project/Skills/docs/blueprint.md'
50:| 4 | 實作(每張 ticket) | `build`(wrap `/implement`:tdd + code-review,補交棒);**快車道**:一份 spec 有多張彼此不卡的票時走 `build-batch` — 算名單等 client 點頭,點頭後每張各自一個 git worktree 平行跑 build + QA(最多 3 張,做完一張補一張),綠的依序合回主線、整批再驗一次 | **薄層 wrap**;快車道 **自建**(名單/點頭 HITL,跑起來 AFK) | 單張:完成 comment +「下一步:/qa #N($qa #N)」;批次:spec 票上一則批次總結 +「下一步:/client-demo #<spec>($client-demo #<spec>)」 |
+ echo '==== STEP 9(額外,不在驗收條裡)同型全掃:prose-presence guard 的繞過方向 ===='
==== STEP 9(額外,不在驗收條裡)同型全掃:prose-presence guard 的繞過方向 ====
+ echo '   判準:written-evidence 的「Mutation 要驗兩種:改壞 / 繞過」。'
   判準:written-evidence 的「Mutation 要驗兩種:改壞 / 繞過」。
+ echo '   母體用數的、不用「所有」—— 掃描器本身在 scripts/qa/57-guard-sweep.py。'
   母體用數的、不用「所有」—— 掃描器本身在 scripts/qa/57-guard-sweep.py。
+ python '/d/Self Project/Skills/scripts/qa/57-guard-sweep.py' '/d/Self Project/Skills'
validate.py 一共 11 個 errors.append 點,分成 4 類:
  prose-keyword(受測形狀):2 個 -> ['L248', 'L253']
      L248  if unpushed_commit_link_issue(text):
      L253  if missing_blocking_audit_issue(text):
  prose-span(對照組):1 個 -> ['L260']
      L260  for name in find_slash_only_handoffs(text):
  code-position:1 個 -> ['L212']
      L212  if bypass in text or text.rfind(pin) > entry:
  結構/存在性:7 個 -> ['L156', 'L237', 'L242', 'L246', 'L276', 'L281', 'L291']
      L156  if name in PLACEHOLDER_SKILLS or name in present:
      L237  if not skill_md.is_file():
      L242  if fm is None:
      L246  if not fm.get(field):
      L276  if repo_scoped:
      L281  if repo_scoped:
      L291  if (

受測形狀 = prose-keyword(用一個關鍵詞證明「某句指示存在」)。母體 2 個,下面每一個都驗兩個方向。

1) missing_blocking_audit_issue(#57 新增)
   改壞(整句刪掉)            -> True (True = 咬到)
   繞過(條件詞留著、動作反過來) -> False (True = 咬到)
2) unpushed_commit_link_issue(既有,同形狀)
   改壞(有 commit link、沒 push)       -> True (True = 咬到)
   繞過(push 出現在前面但講的是別的事)  -> False (True = 咬到)

3) find_slash_only_handoffs(對照組:span-scoped 共現,不是單一關鍵詞)
   改壞(拿掉 Codex 半)         -> ['qa'] (非空 = 咬到)
   繞過(Codex 半移到 span 外)   -> ['qa'] (非空 = 咬到)
   對照組兩個方向都咬得到 -> 驗法本身有效,上面那兩個 False 是那兩支 guard 的性質,不是這支掃描壞掉。
+ echo '==== STEP 8  AC7:python scripts/validate.py 全綠(repo 本體,未被 mutation 汙染)===='
==== STEP 8  AC7:python scripts/validate.py 全綠(repo 本體,未被 mutation 汙染)====
+ git -C '/d/Self Project/Skills' status --porcelain -- skills scripts docs
?? docs/qa/57-walkthrough.md
?? scripts/qa/57-guard-sweep.py
?? scripts/qa/57-walkthrough.sh
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ set +x
==== walkthrough 結束 ====
```
