# QA walkthrough — #113

母體:`batch/113` 已推上去的最終 diff(`b11c43c..4dc10e4`)。
判定 oracle:#113「完工定義」原句。

> 三條都改完,兩份 SKILL.md 各再走一次 `/writing-for-agents` 並把結果寫進票
> (AC5 要的是可覆核的紀錄,不是自我宣稱),`python scripts/validate.py` 綠。

這片沒有 UI,walkthrough 不用 Playwright:交付物是兩份 SKILL.md 的散文,
「使用者」是下一個照著做的 agent。實測方式是把每條驗收原句翻成看得到的證據。

---

## 為什麼需要第二把尺

#113 修的三條(stale `§N` 指標、自我描述跟本體打架、無界全稱詞)全是散文問題。
`validate.py` 的 docstring 自己寫著 `Does NOT validate prose content` —— 修完之後
repo 裡沒有任何機械判準看得到這三條,唯一的收據是 `/writing-for-agents` 走查
agent 說 pass。而走查 agent 跟寫修法的是同一類 reader:它綠只證明它同意自己。

所以本輪另寫 `scripts/qa/113-wide.py` 當第二把尺 —— 從頭自己寫一遍那三條的
**機械形狀**,刻意寫寬、不套走查 agent 的判準,再拿修前那個 commit 跑同一份母體
列差額。

---

## 步驟 1 — Regression

| 指令 | 結果 |
| --- | --- |
| `python scripts/validate.py` | `OK validate green`,exit 0 |
| `python scripts/validate.py --self-check` | `OK validate self-check green`,exit 0 |
| `python scripts/qa/107-mutate.py --run` | `8/8 個 knob 被 self-check 咬住`,exit 0 |
| `python scripts/qa/97-mutate.py --run` | `15/15 個 knob 被 self-check 咬住`,exit 0 |
| `python scripts/qa/96-newrule-probe.py .` | `OK 新規則下全綠`、`不合 0`,exit 0 |

全綠,0 條 blocking。

`scripts/qa/README.md` 列的 12 支 `*-sweep.py` 是 #60–#95 那條線的歷史紀錄,
不列入目前 regression —— 照 README 原句處理,本輪沒跑。

### 這輪自己踩到的一條(已修,留紀錄)

`113-wide.py` 第一版把 UTF-8 pin 寫在 module level,`validate.py` 當場擋下來:

```
FAIL scripts/qa/113-wide.py: runnable script does not pin stdout to UTF-8 at
the first level of its `if __name__ == "__main__"` block — its 中文 output is
mojibake on a cp950 console (#58)
```

改成 `if __name__ == "__main__":` 底下第一層的 `sys.stdout.reconfigure(encoding="utf-8")`
之後綠。#58/#72/#96 那條守門在本輪對一支**新寫的** QA 腳本真的咬到了,不是只對
fixture 綠 —— 順帶當成那條規則的一次現場正向控制。

---

## 步驟 2 — 第二把尺 + 修前對照

`scripts/qa/113-wide.py`,母體 84 份 `.md`(`skills/` + `docs/`),四項掃描:

1. **未解析的 `§N`** —— 文中 `§N` 在同一個檔找不到 `## N.` 標題。
2. **指得到但指錯節的 `§N`** —— `§N` 後面緊跟的 2–4 個字如果本身是某個標題的字,
   那 §N 的標題就該含那幾個字。這條是為了抓 #113 第 1 條:`跑完接 §2 收尾` 字面
   解析得開(§2 存在),錯的是語意。
3. **無界全稱詞** —— 關鍵詞表刻意開大,且**不分辨**理由句 vs 規則陳述。
4. **delta 記帳** —— 自稱幾個 delta vs 正文有幾個 `(delta)` 標題。

修前用 `git archive b11c43c skills docs` 解到乾淨目錄,跑同一支腳本:

```
$ python scripts/qa/113-wide.py <b11c43c 的 skills+docs> --json
$ python scripts/qa/113-wide.py .                         --json
```

### 差額(兩份受測檔)

| 檔 | 項目 | 修前 b11c43c | 修後 4dc10e4 |
| --- | --- | --- | --- |
| `skills/build/SKILL.md` | 指錯節的 §N | **1** | **0** |
| `skills/build/SKILL.md` | delta 自稱 vs `(delta)` 標題數 | **`[1]` vs `3`** | `[3]` vs `3` |
| `skills/build/SKILL.md` | 未解析 §N / 無界全稱詞 | 0 / 0 | 0 / 0 |
| `skills/qa/SKILL.md` | 「唯一」 | **1** | **0** |
| `skills/qa/SKILL.md` | 無界全稱詞候選(全表) | 9 | 8 |
| `skills/qa/SKILL.md` | 未解析 §N / 指錯節 §N | 0 / 0 | 0 / 0 |

修前那筆「指錯節」腳本印出來長這樣 —— 它沒讀過票,自己撈到票上第 1 條:

```
skills/build/SKILL.md:12 §2 的標題是「code-review 的並行位置(delta)」,但「收尾」住在 §3
    呼叫 `/implement #N`(已收編,模型可叫)跑完整流程,跑完接 §2 收尾。
```

repo-wide:指錯節 2 → 1、無界全稱詞候選 324 → 323、delta 記帳對不上 7 → 6 份。
三個數字各降 1,降的都是本輪動到的那一筆,**沒有新增**。

### 寬那面撈出來的多餘項 —— 逐筆判讀

| 筆 | 判讀 |
| --- | --- |
| 未解析 §N **187 筆**(兩側同數) | **全數誤報,設計上的收窄**。絕大多數是 `docs/qa/*.md` 歷史紀錄檔引用**別的檔**的 §N(例:`49-walkthrough.md:5` 引 `build/SKILL.md` §2),以及 `close/SKILL.md:16-21` 表格裡引 `/qa`、`/maintain`、`/client-demo` 的節號。這支刻意不解析跨檔引用,所以照樣列出來。兩側同數 = 本輪沒動到這塊 |
| 指錯節 `build-batch/SKILL.md:356`(兩側都在) | **誤報**。原句是「§8 一張一張回收掉了」,`一張` 剛好也出現在 §6 的標題裡,寬規則就咬了。那是量詞,不是節指標 |
| 無界全稱詞 `qa/SKILL.md` 剩下 8 筆 | **全數合法**。`:19 任何`、`:31/:50/:77 每一`、`:53/:81 一律`、`:85 所有/全部` 都是**規則陳述**(「紅的每一條記為 blocking」「works-but-wrong 一律算 fail」),不是理由句裡的量測宣稱。`written-evidence.md:8-18` 禁的是後者 |
| 無界全稱詞 repo-wide 323 筆 | 沒逐筆判 —— 母體是全 repo,不在 #113 範圍。本輪只用它的**差額**(324→323)當證據 |
| delta 記帳對不上剩 6 份 | **全數誤報**。`maintain`、`slice-tickets`、`docs/specs/*`、`docs/qa/107-*` 的「N 個 delta」是散文敘述,那些檔根本沒有 `(delta)` 結尾的標題。這條規則只對 `build/SKILL.md` 這種「標題自己標了 (delta)」的檔有意義 |

---

## 步驟 3 — 逐條驗收原句

### A1 「三條都改完」

逐字比對 `git diff b11c43c..4dc10e4 -- skills/`:

| 票上第幾條 | 原句要求 | 現況(逐字) | 判定 |
| --- | --- | --- | --- |
| 1 | `build/SKILL.md:12` 的 `§2` 是 stale,收尾在 §3 | `跑完整流程。跑的**過程中** /code-review 的位置改照 §2(原件序列的那一步不照跑),跑完接 §3 收尾;寫交付物的當下照 §4。` | **pass** |
| 2 | `build/SKILL.md:8` 自我描述跟本體打架(「只補一個 delta」、「`/code-review` 全依原件」) | `tdd 循環、typecheck、測試、commit 全依原件,本檔只補三個 delta — **/code-review 的並行位置**、**收尾交棒**、**書面證據**。` —— `/code-review` 已從「全依原件」清單移除,delta 數 1→3 對上正文三個 `(delta)` 標題 | **pass** |
| 3 | `qa/SKILL.md:79` 「唯一一條」無界全稱詞 | 整句刪掉,現在是 `例外、每條 pass。` 直接接下一段 | **pass** |

第 3 條的副作用檢查(刪掉會不會改行為):`:75` 的「**排序約束**:獨立 judge 排在
walkthrough 之後才開,不進 §2 的並行池」還在;理由段前兩句完整;`validate.py` 的
`judge_ordering_issues` 依賴的三 lane 表與「judge 排在 walkthrough 之後」都在 ——
`107-mutate.py --run` 8/8 咬住是這條的機械證據。

### A2 「兩份 SKILL.md 各再走一次 `/writing-for-agents`」

| 母體 | 輪 | verdict |
| --- | --- | --- |
| `skills/qa/SKILL.md` | 1 | **pass**(3 minor + 2 info,無 blocking) |
| `skills/build/SKILL.md` | 1 | fail(8 條) |
| `skills/build/SKILL.md` | 2 | fail(清 5 剩 3) |
| `skills/build/SKILL.md` | 3 | **pass** |

兩份都各走過(build 走了三輪才綠),**pass**。

### A3 「結果寫進票,可覆核,不是自我宣稱」

| comment | 內容 |
| --- | --- |
| [#issuecomment-5378746317](https://github.com/c3lew/Skills/issues/113#issuecomment-5378746317) | 產出 + build 三輪走查表(逐輪 verdict 與 findings) |
| [#issuecomment-5378750420](https://github.com/c3lew/Skills/issues/113#issuecomment-5378750420) | `qa/SKILL.md` 走查結果補登 + 帶出的 out-of-scope findings |
| [#issuecomment-5378765923](https://github.com/c3lew/Skills/issues/113#issuecomment-5378765923) | code-review 處置 + scope 誠實標註(哪些是票上三條、哪些是順手修) |

寫的是**逐條 finding 與逐輪 verdict**,不是「已通過」三個字 —— 第三個人拿這些行號
可以自己重推。**pass**。

### A4 「`python scripts/validate.py` 綠」

`OK validate green`,exit 0。**pass**。

---

## 未涵蓋

| 沒蓋到什麼 | 下文 |
| --- | --- |
| `/writing-for-agents` 走查本身是 agent 判斷,不是機械判準 | 這正是本輪加第二把尺的原因。第二把尺蓋住三條中**每一條**的機械形狀,兩者對得上。走查 agent 額外看的東西(語氣、front-load、含糊祈使句)沒有機械投影 —— **接受不蓋**:那些本來就是要人讀的,把它們機械化會變成關鍵詞守門,正是 #64 修掉的形狀 |
| 兩份 SKILL.md 裝到 `~/.claude/skills/` 之後的實際觸發行為 | **接受不蓋**:本輪沒動 frontmatter 的 `name`,`description` 淨改動是最終版回到原句型(見 `4dc10e4`),觸發面與 `b11c43c` 等價 |
| `scripts/qa/113-wide.py` 沒有自己的 mutation 台 | **接受不蓋**:它是一次性的第二把尺,不進 regression suite,沒有「以後會被誤信」的風險。它的正確性由修前對照本身背書 —— 修前咬到、修後放行,兩側都是真檔 |
| repo-wide 那 323 筆無界全稱詞、187 筆未解析 §N | 不在 #113 範圍。已在 [#issuecomment-5378750420](https://github.com/c3lew/Skills/issues/113#issuecomment-5378750420) 列出建議另開票的具體條目(`qa/SKILL.md:63`、`:96`、`close/SKILL.md:17`) |

---

## 一鍵重開

```
cd .git/batch-worktrees/113
python scripts/validate.py && python scripts/validate.py --self-check
python scripts/qa/107-mutate.py --run
python scripts/qa/97-mutate.py --run
python scripts/qa/96-newrule-probe.py .
python scripts/qa/113-wide.py .
```

修前對照:

```
git archive b11c43c skills docs | tar -x -C <某個空目錄>
python scripts/qa/113-wide.py <某個空目錄>
```
