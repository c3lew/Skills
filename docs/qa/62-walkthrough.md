# QA walkthrough — #62 build-batch:§9 貼批次總結那段沒給可直接複製的 gh 指令(bug fix)

Bug fix ticket,範圍 = 該 bug 的重現 scenario + regression suite。

判定 oracle(票上「對應驗收原句」):

> 「整批結束 → …… spec 票上留一則批次總結 + 下一步指令。」

這輪要判的重點是「client 照 §9 文件逐字跑,那則批次總結有沒有真的落到 spec 票上」——
功能本身在 `/qa #53` 已實測過,缺的是可複製性,所以本輪測的是**照抄能不能跑**。

環境:worktree `D:/Self Project/Skills/.git/batch-worktrees/62`,branch `batch/62`,
HEAD = `0da3790`,working tree 乾淨。本票是 skill 文件 + CLI,沒有 UI,不走 Playwright;
本檔是終端實錄。

一鍵重開(沿用既有 CLI QA 入口):

```bash
cd "D:/Self Project/Skills/.git/batch-worktrees/62"
python scripts/validate.py
python scripts/validate.py --self-check
python scripts/batch.py --self-check
python skills/build-batch/batch.py --self-check
python scripts/install.py --self-check
python scripts/hooks/triage-to-maintain.py --self-check
```

## 步驟 1 — regression suite

```text
$ python scripts/validate.py
OK validate green
exit 0

$ python scripts/validate.py --self-check
OK validate self-check green
exit 0

$ python scripts/batch.py --self-check
OK batch self-check green
exit 0

$ python skills/build-batch/batch.py --self-check
OK batch self-check green
exit 0

$ python scripts/install.py --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
exit 0

$ python scripts/hooks/triage-to-maintain.py --self-check
OK triage-to-maintain self-check green
exit 0
```

(`[fixture] FAIL` 是 install self-check 自己的 negative fixture,綠的一部分。)

既有 regression 全綠。

## 步驟 2 — 重現 scenario:照修後 §9 逐字抄一次

修後 §9 那段(`skills/build-batch/SKILL.md:144-150`):

```bash
python <skill dir>/batch.py <<'JSON' | gh issue comment 51 --body-file -
{"mode": "summary", "numbers": [47, 48], "spec": 51,
 "titles": {"47": "...", "48": "..."},
 "coverage": [["#47 覆蓋的驗收項原句"], ["#48 覆蓋的驗收項原句"]]}
JSON
```

整段複製,只換兩個本來就是佔位符的東西 —— `<skill dir>` → `skills/build-batch`、
票號 51 → 62(拿本票當靶,跑完刪掉)。**沒有自己拼任何東西**:

```text
$ python skills/build-batch/batch.py <<'JSON' | gh issue comment 62 --body-file -
{"mode": "summary", "numbers": [61, 62], "spec": 62,
 "titles": {"61": "QA probe A", "62": "QA probe B"},
 "coverage": [["QA probe 覆蓋句 A"], ["QA probe 覆蓋句 B"]]}
JSON
https://github.com/c3lew/Skills/issues/62#issuecomment-5338425293
```

一次就過,票上當場多一則 comment。

## 步驟 3 — 落票內容與本機 stdout 逐字元對帳

同一份輸入,本機 stdout:

```text
## 批次總結(2 張)

- #61 QA probe A — 已合併(batch/61)
- #62 QA probe B — 已合併(batch/62)

整批驗證:regression + 下列覆蓋驗收項聯集,全綠。

- QA probe 覆蓋句 A
- QA probe 覆蓋句 B

下一步:`/client-demo #62`(Codex: `$client-demo #62`)
```

從 GitHub 撈回來比對(`gh api repos/c3lew/Skills/issues/comments/5338425293 --jq .body`):

```text
local chars: 198 remote chars: 198
identical: True
lines: 11
```

「批次總結 + 下一步指令」兩件事都在,中文與反引號原樣落地。probe comment 跑完已刪
(`gh api -X DELETE …/comments/5338425293`),票上只剩正式的 build / QA comment。

## 步驟 4 — 對照組:修前那段照抄會停在哪

`HEAD~1` 的 §9:

```text
python <skill dir>/batch.py <<'JSON'
{"mode": "summary", ...}
JSON
```
> 印出來的整段當 comment body 貼上去(`gh issue comment 51 --body-file -`)。

照抄跑完只會把總結印在終端機,票上什麼都沒有 —— 要落票,讀的人得自己決定
`<<'JSON'` 跟 `|` 誰先誰後。這正是票上說的「留給 agent 自己拼」。修後那一行把這步拿掉了。

## 步驟 5 — 同型全掃:三處貼票指令一次掃完

票上點名「同一份文件、同一種動作,三處裡兩處給全、一處沒給」,所以三處全部照抄實跑
(§6 兩處把 `gh` 換成 `cat` 做 dry run,避免在票上留垃圾):

| 位置 | 指令形狀 | 照抄可跑? |
|---|---|---|
| `SKILL.md:96`(§6 開工貼票) | `echo "$lane" \| python … \| gh issue comment 47 --body-file -` | 是 — 輸出「開工 #62 … — 工作區 .git/batch-worktrees/62(branch batch/62)」 |
| `SKILL.md:106`(§6 完成貼票) | `echo "$lane" \| python … \| gh issue comment 47 --body-file -` | 是 — 輸出「完成 #62 … — build + QA 綠」 |
| `SKILL.md:145`(§9 批次總結) | `python … <<'JSON' \| gh issue comment 51 --body-file -` | 是(本輪修的) |

`grep -n "body-file -" skills/build-batch/SKILL.md` 只有這三行,沒有第四處漏網。
§9 上面那個 `merged` block(`SKILL.md:137`)不在同型內 —— 它本來就只印終端機、不貼票。

## 步驟 6 — 獨立 judge

乾淨 subagent,只餵驗收原句 + 上面的證據,不餵實作脈絡。判定 **pass**:

- 指令照抄可跑,heredoc redirect 在 pipe 之前是 POSIX 合法寫法,步驟 2 verbatim 真的 post 成功。
- 「批次總結」與「下一步指令」兩件事在落票內容裡都在。
- round-trip 198 vs 198、`identical: True` — 沒有 heredoc 吃掉縮排或 gh 改寫 body 這種 works-but-wrong。
- 貼的目標票號跟 JSON 的 `"spec"` 一致,不是隨便貼一張。
- 同型殘留掃描:§6 兩處 pass,§9 的 `merged` block pass(它散文本來就寫「終端機印最後一行」,不該有 `gh` 半段)。

judge 另外挑出兩個 nit,都判「不是 fail」:

1. `<skill dir>` 佔位符四處都要讀者自己代路徑 — 三處一致、且 §6 是本票認可的 good model,算既有 convention。
2. `gh issue comment 51` 跟 JSON 裡的 `"spec": 51` 是兩個要手動同步的票號,改一個忘另一個會把總結貼錯票(§6 的 `47` 同型)。

第 2 條開成 known issue(見票上 QA 報告),第 1 條留紀錄不開票。

## 未涵蓋

- **`gh` 沒登入 / 沒權限**:本輪是在已登入的機器上跑,指令失敗時的訊息長怎樣沒測。
- **真的整批跑完一次 `/build-batch`**:本輪只驗 §9 這一步的指令可複製性,沒有從 §1 走到 §9
  跑一次完整批次 —— 那條路在 #53 的 walkthrough 驗過。
- 本票沒碰 §9 最後那句清場檢查(`git worktree list`)—— 那段是同批 #61 的範圍。
