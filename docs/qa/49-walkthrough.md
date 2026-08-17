# QA walkthrough — #49 build 收尾要 push

驗收 oracle(bug ticket #49 原句):

1. `skills/build/SKILL.md` §2 明確要求「push 後才貼 commit link」,且完成標準涵蓋這一步
2. `python scripts/validate.py` 綠
3. 下一張走 `/build` 的票,票上 comment 的 commit link 當場點得開(不需人補 push)

環境:`D:/Self Project/Skills`,HEAD = `66fec63`,起始 working tree 乾淨,`origin` 已 fetch。
本票是 skill 文件 + 產線流程票,沒有 UI,不走 Playwright;本檔是每條驗收項共用的終端實錄。

一鍵重開(沿用既有 CLI QA 入口):

```powershell
cd "D:/Self Project/Skills"
python scripts/validate.py --self-check
python scripts/validate.py
python scripts/install.py --self-check
python scripts/install.py
```

## 步驟 1 — regression suite

```text
$ python scripts/validate.py --self-check
OK validate self-check green
exit 0

$ python scripts/validate.py
OK validate green
exit 0

$ python scripts/install.py --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
exit 0
```

既有 regression 全綠(含 #43 那輪固化進去的 `[fixture]` 標示守門)。

## 步驟 2 — 驗收 1:§2 的順序與完成標準

`skills/build/SKILL.md` §2 現況(逐字):

```text
原件跑完不算完成,票上要有兩則 comment 才算 — 但**先 push**:

1. **push**:`git push`,再用 `git rev-list --count origin/<branch>..HEAD` 確認是 `0`。
   原件只 commit 不 push,沒推上去的 sha 在 GitHub 上是 404。
2. **產出 comment**:改了什麼(commit links)+ review findings 處置。
3. **交棒 comment** 固定一行:「下一步:`/qa #N`(Codex: `$qa #N`)」…

順序是硬要求:push 沒綠不准貼 commit link — comment 一貼出去,link 就得當場點得開。

完成標準:未 push 的 commit 數是 `0`,且 `gh issue view N --comments` 看得到交棒 comment,
才結束 session。
```

push 是編號 1(在產出 comment 之前)、有可執行的驗證指令、有一行硬要求宣告,完成標準
兩個條件都在。`docs/specs/build.md` 行為第 2 條同步(spec 是行為來源)。frontmatter
description 也改成「push 後產出寫回票」。

## 步驟 3 — 驗收 2:validate

```text
$ python scripts/validate.py --self-check
OK validate self-check green
exit 0

$ python scripts/validate.py
OK validate green
exit 0
```

## 步驟 4 — 驗收 3:票上 commit link 當場點得開

#49 自己這輪就是新順序的第一次實跑(build comment 由新版 §2 產出)。現場量測:

```text
$ git fetch origin && git rev-list --count origin/main..HEAD
0

$ git merge-base --is-ancestor 66fec63 origin/main && echo yes
yes

$ gh api repos/c3lew/Skills/commits/66fec63 --jq '.sha[0:7] + " | " + .commit.message'
66fec63 | fix: push before pasting commit links in build handoff (#49)

$ git status --porcelain
(空)
```

票上 comment 貼的 `66fec63` link 現在解析得到,且本輪 QA **沒有**做任何補 push
(未 push 數在 QA 開始前就是 `0`)。

### test-the-test:確認守門真的會咬

在 throwaway branch 上造一個未 push 的 commit,看 §2 的守門指令與 GitHub 是否一致:

```text
$ git checkout -b qa-49-probe && git commit --allow-empty -m "qa probe: unpushed commit (#49)"
probe sha: 2f28450

$ git rev-list --count origin/main..HEAD
1                                   ← §2 的守門會擋(不是 0)

$ gh api repos/c3lew/Skills/commits/2f28450
{"message":"No commit found for SHA: 2f28450", ... "status":"422"}
gh: No commit found for SHA: 2f28450 (HTTP 422)   ← 這就是 #41 踩到的 404 症狀

$ git checkout main && git branch -D qa-49-probe
back on: main, unpushed=0, status=0(乾淨)
```

守門條件(`count != 0`)與「link 死掉」完全同時發生 — §2 的檢查抓的正是這個失敗模式。

## 步驟 5 — 獨立 judge

乾淨 subagent 只收到驗收原句與步驟 1–4 證據,未收到實作脈絡:

| 驗收原句 | judge | 理由 |
|---|---|---|
| §2 要求 push 後才貼 commit link,完成標準涵蓋 | **pass** | push 列為步驟 1、明寫「push 沒綠不准貼 commit link」,完成標準含「未 push 數是 `0`」。 |
| `validate.py` 綠 | **pass** | `OK validate green`、exit 0(self-check 也綠)。 |
| **下一張**走 `/build` 的票,commit link 當場點得開 | **fail** | E4 只證明守門抓得到未 push;E3 是本票自己,證據自己註明還沒有任何**後續**票跑過 `/build` — 驗收原句要的「下一張票」證據不存在。 |

Works-but-wrong:0。

judge 額外點出的未涵蓋:§2 寫的是 `origin/<branch>`,但 E4 只量了 `origin/main..HEAD`;
也沒測 push 失敗(protected branch / reject)或 branch 還沒有 upstream 時的行為。補測:

```text
$ git checkout -b qa-49-probe2
$ git rev-list --count origin/qa-49-probe2..HEAD
fatal: ambiguous argument 'origin/qa-49-probe2..HEAD': unknown revision or path not in the working tree.
exit 128
```

branch 還沒 upstream(= push 沒成功)時,守門指令是 `fatal` / exit 128,不是印出一個數字。
失敗模式是「炸掉」而不是「靜默給 0」— 不會誤放行,但 agent 看到的訊息不是「未 push 數不是 0」。

## Blocking / known issues / 未涵蓋

- **Blocking:0**(沒有可修的 defect — 見下方 known issue 1 的判定說明)。
- **Known issue 1(judge 判 fail,但不是 defect)**:驗收 3 原句的對象是「**下一張**走 `/build`
  的票」,那張票還不存在,所以這條在本票範圍內拿不到證據 — judge 據此判 fail,判得對。
  可驗的部分全綠:新版 §2 產出的 #49 comment,link 從第一秒就活、QA 期間沒人補 push;
  守門條件與 404 同時觸發(步驟 4 test-the-test)。跨票證據要等下一張 `/build` 票落地,
  屆時 comment link 若 404 就是紅。這條不開 bug ticket(沒有東西可修),處置(現在等 /
  之後補驗 / 直接收)留給 client 在 demo 收尾拍板。
- **Known issue 2(非 blocking)**:守門指令在 branch 還沒 upstream 時是 `fatal` / exit 128
  而非印出數字(步驟 5 補測)。不會誤放行,但訊息不直觀;要不要改成
  `git rev-list --count @{u}..HEAD` 之類留給 retro / client 判。
- **Known issue 3(非 blocking)**:本機安裝的 `~/.claude/skills/build/SKILL.md`
  仍是舊版(無 push 步驟)— 換裝在 `client-demo` 的「過關即發」才做。也就是說在換裝前,
  本機 agent 讀到的 build skill 還沒有這條;這是既有流程順序,不是本票的 regression。
- **未涵蓋**:無 UI、無 Tauri 原生殼;#49 的行為全在 CLI / GitHub API 上,已全數實跑。
  沒有加機器守門(build comment 自審提過:唯一能寫的是 grep string-presence 測試,
  擋不住真 regression)— 要不要補保險 grep 留給 retro 判。

## 步驟 6 — 固化(client-demo 過關後)

client 過關(前三條)後回本 skill 固化。原本判定「只能寫 string-presence 測試」的顧慮
用**順序**解掉了:守門不是問「有沒有提到 push」,而是問「`git push` 的位置有沒有在
commit link 之前」,而且 push 側只認可執行的 `git push`(不認 frontmatter 的
「push 後產出寫回票」這種摘要),所以刪掉真正那一步就會紅。

`scripts/validate.py` 新增 `unpushed_commit_link_issue()`,進 `validate()` 逐 skill 跑:

```text
$ python scripts/validate.py --self-check      # 手寫案例 + 真檔 mutation 層
OK validate self-check green
$ python scripts/validate.py
OK validate green
$ python scripts/install.py --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
```

### 守門第一次跑就抓到兩個既有offender

上線當下 repo 是紅的 — 同一個 404 失敗模式在另外兩支 skill 裡躺著沒人踩到:

```text
FAIL skills/close/SKILL.md: asks for commit links in a ticket comment without asking to `git push` first — an unpushed sha is a 404
FAIL skills/retro/SKILL.md: asks for commit links in a ticket comment without asking to `git push` first — an unpushed sha is a 404
```

`close` §3 貼結案 comment 的 commit links、還會自己產 dashboard 更新的 commit;
`retro` §6 貼每條 amendment 的 commit link。client 拍板「順手補」,兩支各補一步 push
(見決策投影)。補完 repo 回綠。

### 真檔 mutation 層(test-the-test)

self-check 掃出所有提到 commit link 的真 SKILL.md(現在是 build / close / retro),
每支都驗兩次:原檔綠、把 `git push` 抽掉就紅。所以之後任何人刪掉或搬動 push 步驟、
或新寫一支會貼 commit link 的 skill 卻忘了 push,`validate.py` 當場咬。
