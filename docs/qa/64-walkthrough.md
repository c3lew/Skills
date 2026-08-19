# QA walkthrough — #64 兩支 prose guard 改成守主張(bug fix)

Bug fix ticket,範圍 = 該 bug 的重現 scenario + regression suite。

判定 oracle(票上 `/maintain` 分流那則的重現 scenario 與完工定義原句):

> 3. 期望:修完後兩支的「繞過」欄都是 True(對照組 `find_slash_only_handoffs` 維持兩欄都 True)
>
> - [ ] 掃描器兩支的「繞過」欄都 True
> - [ ] `python scripts/validate.py` 綠(全 repo 現況不得因此變紅)
> - [ ] 兩支一起改(母體是 2,不是 1 — 只修一支等於同一個 bug 拆成兩輪)

外加 repo 自己的紀律 `references/written-evidence.md`〈Guard 的完工定義〉三條:住在預設就會跑的地方、
兩種 mutation 都咬得到、查不到目標時判 fail。這張票的**存在理由**就是第二條沒過。

交付物是 `scripts/validate.py` 的 guard + skill 散文,沒有 UI、沒有視覺 oracle,不走 Playwright、
沒有錄影 — 實錄就是下面這份終端 transcript(全程 bash xtrace,指令與輸出在同一份,沒有事後 render)。
mutation 全部跑在拋棄式暫存目錄的副本上,repo 本體沒被動過(STEP 9 的 `git status` 是證據)。

環境:`D:/Self Project/Skills`,branch `main`,HEAD = `22e274f`。

一鍵重開(client-demo / 之後每輪 QA 直接抄):

```bash
bash scripts/qa/64-walkthrough.sh "$(mktemp -d)/qa64"
```

步驟:

| # | 驗的是 | 對應驗收原句 |
| --- | --- | --- |
| 1 | regression suite:`validate.py` + 五支 self-check | AC2 / 既有 regression |
| 2 | 票上的重現 scenario 原樣重跑 — 掃描器兩支的「繞過」欄 | 重現 scenario 第 3 點 / AC1 |
| 3 | 票上那串意思相反的散文裸跑一次,現在回 `True` | 重現 scenario |
| 4 | 拋棄式副本未動過 → 綠(證明後面判紅的是 mutation,不是副本壞了) | — 對照 |
| 5 | **繞過方向打在真的 SKILL.md 上**:5a `slice-tickets` §4「回報 client」反寫成「不用問 client」;5b `build` §1「`git push`」反寫成「不要 `git push`」 → `validate.py` 兩次都紅,而且 error 指名的就是被改的那個檔 | written-evidence 第 2 條(繞過) |
| 6 | 改壞方向沒退步:把那兩行整行刪掉 → 一樣紅 | written-evidence 第 2 條(改壞) |
| 7 | 同型全掃的分類還對得上:11 個 `errors.append` 點,受測形狀 prose-assertion 母體 = 2,兩支都在受測名單 | AC3 |
| 8 | build 自己寫在 code 裡的已知天花板:離否定詞遠的改寫(「收工後再回報 client」)還是綠,`ponytail:` 註解在 L70 | — 已知天花板 |
| 9 | repo 本體 `validate.py` 全綠,`git status` 只多這輪的 QA artifact | AC2 |

STEP 5 是這輪的重點:掃描器(STEP 2)餵的是手寫字串,只證明得了「函式行為對」。
STEP 5 改的是**現役的那兩個 SKILL.md**,證明的是「有人真的把文件改成意思相反,`python scripts/validate.py` 會擋下來」—
而 #57 加這支 guard 的全部理由就是守住那一問。

**這份驗不到的**(交給票上 QA 報告的未涵蓋清單):

- **散文的執行者是 agent,不是機器。** 這輪驗的是「文件被改壞/改成相反時 guard 會紅」,
  不是「agent 讀了那句話真的照做」。真的要驗得跑一次 `/slice-tickets`,而那一問會真的發票到 GitHub。
- **離否定詞四個字以外的改寫還是綠**(STEP 8)。這是 build 拍板留下的天花板,寫在 `validate.py` L70 的
  `ponytail:` 註解裡,不是這輪新發現。往下追是無底的詞表軍備賽,那條靠 review 擋。
- **`unpushed_commit_link_issue` 沒有改成 span-scoped**,維持位置判斷(push 要在 commit link 之前)。
  真的 `build/SKILL.md` 裡 push 是第 1 步、貼 commit link 是第 2 步,本來就不同句 —— 綁進同一個 span 會把對的文件判紅。
  代價:兩句之間插進來的東西不受管。
- **母體只掃 `scripts/validate.py`**(票上寫的母體就是它)。`skills/build-batch/batch.py` 裡另有一批讀散文的
  readback guard,形狀不同(整句 `re.escape` 字面釘死,不是關鍵詞),這輪沒進母體、沒驗。

## Transcript

```
+ echo '==== STEP 1  regression suite(validate + 五支 self-check)===='
==== STEP 1  regression suite(validate + 五支 self-check)====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ python '/d/Self Project/Skills/scripts/validate.py' --self-check
OK validate self-check green
+ python '/d/Self Project/Skills/scripts/batch.py' --self-check
OK batch self-check green
OK §8a/§8c conflict scenarios green
+ python '/d/Self Project/Skills/skills/build-batch/batch.py' --self-check
OK batch self-check green
+ python '/d/Self Project/Skills/scripts/install.py' --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
+ python '/d/Self Project/Skills/scripts/hooks/triage-to-maintain.py' --self-check
OK triage-to-maintain self-check green
+ echo '==== STEP 2  票上重現 scenario:掃描器兩支的「繞過」欄要都是 True ===='
==== STEP 2  票上重現 scenario:掃描器兩支的「繞過」欄要都是 True ====
+ python '/d/Self Project/Skills/scripts/qa/57-guard-sweep.py' '/d/Self Project/Skills'
validate.py 一共 11 個 errors.append 點,分成 4 類:
  prose-assertion(受測形狀):2 個 -> ['L281', 'L286']
      L281  if unpushed_commit_link_issue(text):
      L286  if missing_blocking_audit_issue(text):
  prose-span(對照組):1 個 -> ['L293']
      L293  for name in find_slash_only_handoffs(text):
  code-position:1 個 -> ['L245']
      L245  if bypass in text or text.rfind(pin) > entry:
  結構/存在性:7 個 -> ['L189', 'L270', 'L275', 'L279', 'L309', 'L314', 'L324']
      L189  if name in PLACEHOLDER_SKILLS or name in present:
      L270  if not skill_md.is_file():
      L275  if fm is None:
      L279  if not fm.get(field):
      L309  if repo_scoped:
      L314  if repo_scoped:
      L324  if (

受測形狀 = prose-assertion(讀散文證明「某句指示存在」)。母體 2 個,下面每一個都驗兩個方向。

1) missing_blocking_audit_issue(#57 新增)
   改壞(整句刪掉)                   -> True (True = 咬到)
   繞過(條件詞留著、動作反過來)            -> True (True = 咬到)
2) unpushed_commit_link_issue(既有,同形狀)
   改壞(有 commit link、沒 push)   -> True (True = 咬到)
   繞過(push 在前面但被反過來寫)         -> True (True = 咬到)

受測母體 2 支 × 2 個方向 = 4 個格子,咬到 4 個。

3) find_slash_only_handoffs(對照組:span-scoped 共現,不是單一關鍵詞)
   改壞(拿掉 Codex 半)         -> ['qa'] (非空 = 咬到)
   繞過(Codex 半移到 span 外)   -> ['qa'] (非空 = 咬到)
   對照組 2 個方向咬到 2 個 -> 驗法本身有效:上面那 4 個格子的值是那幾支 guard 的性質,不是這支掃描壞掉。
+ echo '==== STEP 3  票上重現 scenario 的裸版:那句意思相反的散文,現在判紅 ===='
==== STEP 3  票上重現 scenario 的裸版:那句意思相反的散文,現在判紅 ====
+ python - '/d/Self Project/Skills'
票上那串 -> True
+ echo '==== STEP 4  副本未動過 -> 綠(證明下面判紅的是 mutation,不是副本壞了)===='
==== STEP 4  副本未動過 -> 綠(證明下面判紅的是 mutation,不是副本壞了)====
+ python /tmp/tmp.EML7IyMUZK/qa64/repo/scripts/validate.py
OK validate green
+ echo '==== STEP 5  繞過 mutation 打在真的 SKILL.md 上,兩支各一次 ===='
==== STEP 5  繞過 mutation 打在真的 SKILL.md 上,兩支各一次 ====
+ echo '-- 5a  slice-tickets §4:條件詞留著,動作從「發佈前回報 client」反過來寫'
-- 5a  slice-tickets §4:條件詞留著,動作從「發佈前回報 client」反過來寫
+ grep -n '一張 blocking 邊都沒宣告' /tmp/tmp.EML7IyMUZK/qa64/repo/skills/slice-tickets/SKILL.md
32:切出來的票**一張 blocking 邊都沒宣告**的時候,發佈前回報 client:「這批 N 張彼此都沒有先後關係,對嗎?」等他回答,不要自己補一條邊,也不要靜靜發佈。
+ python - /tmp/tmp.EML7IyMUZK/qa64/repo/skills/slice-tickets/SKILL.md
+ grep -n '一張 blocking 邊都沒宣告' /tmp/tmp.EML7IyMUZK/qa64/repo/skills/slice-tickets/SKILL.md
32:切出來的票**一張 blocking 邊都沒宣告**的時候,發佈前不用問 client:「這批 N 張彼此都沒有先後關係,對嗎?」等他回答,不要自己補一條邊,也不要靜靜發佈。
+ set +e
+ python /tmp/tmp.EML7IyMUZK/qa64/repo/scripts/validate.py
FAIL skills/slice-tickets/SKILL.md: publishes tickets via `/to-tickets` but never reports 「一張 blocking 邊都沒宣告」 to the client — a batch that lost every edge looks exactly like one that has none, and /build-batch then opens all of them in parallel
+ echo 'exit 1'
exit 1
+ set -e
+ echo '-- 5b  build §1:push 那句留著,動作反過來寫成「不要 git push」'
-- 5b  build §1:push 那句留著,動作反過來寫成「不要 git push」
+ python - /tmp/tmp.EML7IyMUZK/qa64/repo/skills/build/SKILL.md
+ grep -n '不要 `git push`' /tmp/tmp.EML7IyMUZK/qa64/repo/skills/build/SKILL.md
18:1. **push**:不要 `git push`,再用 `git rev-list --count origin/<branch>..HEAD` 確認是 `0`。原件只 commit 不 push,沒推上去的 sha 在 GitHub 上是 404。
+ set +e
+ python /tmp/tmp.EML7IyMUZK/qa64/repo/scripts/validate.py
FAIL skills/build/SKILL.md: asks for commit links in a ticket comment without asking to `git push` first — an unpushed sha is a 404
FAIL skills/slice-tickets/SKILL.md: publishes tickets via `/to-tickets` but never reports 「一張 blocking 邊都沒宣告」 to the client — a batch that lost every edge looks exactly like one that has none, and /build-batch then opens all of them in parallel
+ echo 'exit 1'
exit 1
+ set -e
+ echo '==== STEP 6  改壞方向沒退步:整句刪掉,一樣判紅 ===='
==== STEP 6  改壞方向沒退步:整句刪掉,一樣判紅 ====
+ cp -r '/d/Self Project/Skills/skills' /tmp/tmp.EML7IyMUZK/qa64/skills-fresh
+ rm -rf /tmp/tmp.EML7IyMUZK/qa64/repo/skills
+ cp -r /tmp/tmp.EML7IyMUZK/qa64/skills-fresh /tmp/tmp.EML7IyMUZK/qa64/repo/skills
+ python - /tmp/tmp.EML7IyMUZK/qa64/repo/skills/slice-tickets/SKILL.md /tmp/tmp.EML7IyMUZK/qa64/repo/skills/build/SKILL.md
+ set +e
+ python /tmp/tmp.EML7IyMUZK/qa64/repo/scripts/validate.py
FAIL skills/build/SKILL.md: asks for commit links in a ticket comment without asking to `git push` first — an unpushed sha is a 404
FAIL skills/slice-tickets/SKILL.md: publishes tickets via `/to-tickets` but never reports 「一張 blocking 邊都沒宣告」 to the client — a batch that lost every edge looks exactly like one that has none, and /build-batch then opens all of them in parallel
+ echo 'exit 1'
exit 1
+ set -e
+ echo '==== STEP 7  同型全掃的分類還對得上:validate.py 的 errors.append 點與受測母體 ===='
==== STEP 7  同型全掃的分類還對得上:validate.py 的 errors.append 點與受測母體 ====
+ echo '   (STEP 2 已印過完整分類 — 這裡只把「母體 = 2、兩支都在受測名單裡」再斷言一次)'
   (STEP 2 已印過完整分類 — 這裡只把「母體 = 2、兩支都在受測名單裡」再斷言一次)
+ python - '/d/Self Project/Skills'
errors.append 點共 11 個,分類:{'結構/存在性': 7, 'code-position': 1, 'prose-assertion(受測形狀)': 2, 'prose-span(對照組)': 1}
受測母體 2 支: ('unpushed_commit_link_issue', 'missing_blocking_audit_issue')
+ echo '==== STEP 8  build 自己寫在 code 裡的已知天花板:離否定詞遠的改寫還是綠 ===='
==== STEP 8  build 自己寫在 code 裡的已知天花板:離否定詞遠的改寫還是綠 ====
+ python - '/d/Self Project/Skills'
「收工後再回報 client」-> False (False = 漏掉,已知天花板)
+ grep -n ponytail: '/d/Self Project/Skills/scripts/validate.py'
+ head -3
70:# ponytail: 這是有界的啟發式,不是語意分析。它咬的是「關鍵詞留著、當場反過來寫」
+ echo '==== STEP 9  repo 本體沒被汙染:git status + validate 綠 ===='
==== STEP 9  repo 本體沒被汙染:git status + validate 綠 ====
+ git -C '/d/Self Project/Skills' status --porcelain -- skills scripts docs
?? scripts/qa/64-walkthrough.sh
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ set +x
==== walkthrough 結束 ====
```
