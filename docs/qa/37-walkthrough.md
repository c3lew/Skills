# QA walkthrough — #37 交棒行雙寫 /xxx + $xxx

驗收 oracle:第 7 條「任何一個 skill 的交棒 comment,同一行同時看得到 `/xxx` 與 `$xxx` 兩種寫法。」

環境:`D:/Self Project/Skills`,working tree 乾淨,HEAD = `17c4534`。
本切片是 CLI/docs,沒有 UI,不走 Playwright — 證據為終端實錄 + GitHub comment 實體。

一鍵重開:

```
cd "D:/Self Project/Skills"
python scripts/validate.py --self-check && python scripts/validate.py \
  && python scripts/install.py --self-check && python scripts/install.py
```

---

## 步驟 1 — regression suite(baseline 綠)

```
$ python scripts/validate.py --self-check
OK validate self-check green
$ python scripts/validate.py
OK validate green
$ python scripts/install.py --self-check
OK install self-check green
$ python scripts/install.py
... OK installed tracking-viz -> C:\Users\user\.claude\skills\tracking-viz
... OK installed triage / ui-mockup / ...
```

全綠。

## 步驟 2 — 掃全部 skill 的交棒行,每行都雙寫

`grep -rn "下一步" skills/*/SKILL.md` 的完整原始輸出:

```
skills/build/SKILL.md:3:description: 薄層 wrap /implement:tdd、code-review、commit 全依原件,只補收尾 delta — 產出寫回票 + 固定留「下一步:/qa #N($qa #N)」交棒 comment。當 ticket 指路「/build #N」、或 ready-for-agent 的切片/bug 票要開工時使用。
skills/build/SKILL.md:19:2. **交棒 comment** 固定一行:「下一步:`/qa #N`(Codex: `$qa #N`)」— bug 票同樣交給 qa(regression + 重現 scenario)。
skills/client-demo/SKILL.md:40:分類寫進對應回流 ticket:client 原話 + 確認的分類 + 下一步指路。
skills/client-demo/SKILL.md:60:前三條成立後,comment「下一步:`/qa #N`(Codex: `$qa #N`)— 固化 scenarios」交 `qa` 把本切片高價值 scenarios 寫進 regression suite;拿到 qa 回報固化完成、suite 全綠,第 4、5 條才成立。五條全部成立才進 §7;任一條不成立就停在對應步驟。
skills/client-demo/SKILL.md:72:- 過關 → comment「下一步:`/close #N`(Codex: `$close #N`)」— 關票 + dashboard 統一走結案出口(`/close`)。
skills/client-demo/SKILL.md:73:- 有「不對」未閉環 → ticket 列出回流 tickets 與各自下一步,本票留著等 re-demo。
skills/close/SKILL.md:8:所有票的結案唯一出口。Invariant:**完工定義沒滿足的票不關** — 缺哪條就 comment 指路對應下一棒(固定一行:「下一步:`/skill #N`(Codex: `$skill #N`)」),票留著。
skills/maintain/SKILL.md:59:Client 報的即到即分類開票;agent 自撿的照 §5 攢批,client 說了才清。分類完的票進對應產線,每張票 comment 下一步指令當接力棒:
skills/maintain/SKILL.md:61:- bug → 「下一步:`/build #N`(Codex: `$build #N`)」,票上附重現 scenario(`/qa` 要跑 regression + 這個 scenario)。
skills/maintain/SKILL.md:62:- 改功能 → 輕量票同上;完整版寫「下一步:`/pm-intake`(Codex: `$pm-intake`)」。
skills/next/SKILL.md:12:產線慣例:每個環節收尾都在票上留「下一步:`/skill #N`(Codex: `$skill #N`)」comment。用 `gh` CLI 掃 open tickets,最新活動那張的最後一則交棒 comment 就是答案 — 找到就推薦它,不走路由表。
skills/next/SKILL.md:14:**Sanity check**:接力棒只回答「那張票的下一步」。指令指向**別張票**時(例:票 A 上寫「下一步:`/build #B`(Codex: `$build #B`)」),先核對票 A 自己到結案條件沒 — 到了就先推 `/close #A`,接力棒指令列第二棒。一張票只有「還在產線上」或「已結案」兩種狀態,沒有「驗完了但放著」。
skills/pm-intake/SKILL.md:39:收尾在 ticket 留 comment:產出 link +「下一步:`/slice-tickets #N`(Codex: `$slice-tickets #N`)」。
skills/qa/SKILL.md:40:- **blocking** — 驗收清單 fail,修完才能 demo。ticket comment「下一步:`/build #N`(Codex: `$build #N`)」。
skills/qa/SKILL.md:47:- blocking 清零 → 看票的「覆蓋驗收項」段分流:有可 demo 的驗收項 → comment「下一步:`/client-demo #N`(Codex: `$client-demo #N`)」;標「無 — 由後續票的驗收項間接驗證」(純基礎工程切片,沒東西給 client 看)→ comment「下一步:`/close #N`(Codex: `$close #N`)」,demo 由後續票間接把關。
skills/slice-tickets/SKILL.md:36:- 每張 ticket comment:「下一步:`/build #N`(Codex: `$build #N`)」。
skills/slice-tickets/SKILL.md:37:- Spec ticket 收尾 comment:tickets 清單 link + 覆蓋對帳結果 +「下一步:從無 blocker 的票開始 `/build #N`(Codex: `$build #N`)」。
skills/tracking-viz/SKILL.md:3:description: 讀 GitHub Issues 產一頁全白話靜態 HTML dashboard — hero「現在在哪 + 下一步指令」+ 功能進度/品質現況/最近決定/驗收點四宮格。當 client 想看專案現況、環節收尾要更新 dashboard、或 ticket/skill 指路「/tracking-viz」時使用。AFK 隨時可跑。
skills/tracking-viz/SKILL.md:16:| Hero「現在在哪 + 下一步」 | 進行中切片 ticket 的最新交棒 comment(產線慣例:收尾寫「下一步:`/skill #N`(Codex: `$skill #N`)」)。找不到交棒 comment 才自己從切片狀態推下一棒指令。 |
skills/tracking-viz/SKILL.md:42:- Hero 的「下一步」含可複製的下一棒指令,雙寫(`<code>/skill #N</code>` 與 `<code>$skill #N</code>`,Codex 用後者)— 這是產線交棒的指路牌,只指路,不自動 spawn 下一環節。
skills/tracking-viz/SKILL.md:54:回報 dashboard 檔案路徑 + hero 一句話(現在在哪 + 下一步指令)。由呼叫脈絡決定要不要寫回 ticket。
```

命中 21 行。其中**帶指令的交棒行**(baton)每一行都雙寫:build:19、client-demo:60/72、
close:8、maintain:61/62、next:12/14、pm-intake:39、qa:40/47、slice-tickets:36/37、
tracking-viz:42。殘留單寫交棒行 = 0。

其餘命中的行只是散文裡提到「下一步」三個字、沒有指令(client-demo:40/73、maintain:59、
tracking-viz:3/16/54),不在驗收原句範圍。
`build:3` frontmatter 的 `下一步:/qa #N($qa #N)` 兩種寫法都有但格式與 baton 不同 — 列為 known issue。

## 步驟 3 — 換裝後的產物同樣雙寫(runtime 真正讀的那份)

```
$ python scripts/install.py
$ grep -rn "下一步:" ~/.claude/skills/*/SKILL.md | grep -v '\$'
(no output)
```

裝到 `~/.claude/skills/` 的副本裡,沒有任何一行「下一步:」缺 `$` 那半。

## 步驟 4 — 真的產出來的交棒 comment(不是只有 SKILL.md 的字)

GitHub 上實際由 skill 產出的交棒 comment:

- #37 由 `/build` 產出 —
  `下一步:`/qa #37`(Codex: `$qa #37`)`
  <https://github.com/c3lew/Skills/issues/37#issuecomment-5311688140>
- #37 由 `/slice-tickets` 產出 —
  `下一步:`/build #37`(Codex: `$build #37`)`
  <https://github.com/c3lew/Skills/issues/37#issuecomment-5311439261>
- #36 由 `/qa` 與 `/client-demo` 產出 — `下一步:`/client-demo #36`(Codex: `$client-demo #36`)`、
  `下一步:`/qa #36` 固化(Codex: `$qa #36`)`
- 本輪 QA 收尾的交棒 comment(§6)同樣雙寫 — 見 #37 最新一則。

## 步驟 5 — mutation:拿掉一半,validate 要紅

```
$ # 把 skills/qa/SKILL.md 的「下一步:`/client-demo #N`(Codex: `$client-demo #N`)」
$ # 改成只剩「下一步:`/client-demo #N`」
$ PYTHONIOENCODING=utf-8 python scripts/validate.py
FAIL skills/qa/SKILL.md: handoff 「下一步:… `/client-demo`」 missing the Codex form
     `$client-demo` inside the same 「下一步:…」 baton
rc=1

$ # 還原
$ python scripts/validate.py
OK validate green
```

守門有效,而且訊息指名是哪個 skill、缺哪個指令的哪一半。

備註:不加 `PYTHONIOENCODING=utf-8` 時,Windows 預設 console codepage(cp950)會把訊息裡的
中文糊成亂碼,`FAIL` 與檔名仍讀得到。歸為 known issue,不影響守門行為。

## 步驟 6 — 收尾 regression 複跑

```
$ python scripts/validate.py --self-check   # OK
$ python scripts/validate.py                # OK
$ git status --short                        # clean
```
