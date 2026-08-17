# QA walkthrough — #38 README 兩條安裝路徑分段

驗收 oracle(spec #35 原句):

- 第 9 條:本機開發流程不變:改完 → `validate` → `install.py` 立刻生效,不用 push。
- 第 10 條:README 講清楚兩條安裝路徑:使用者用 npx,開發用 `install.py`。

環境:`D:/Self Project/Skills`,working tree 乾淨,HEAD = `7d4d862`。
本切片是 docs/CLI,沒有 UI,不走 Playwright — 證據為終端實錄 + README 原文。

一鍵重開(沿用 #37):

```
cd "D:/Self Project/Skills"
python scripts/validate.py --self-check && python scripts/validate.py \
  && python scripts/install.py --self-check && python scripts/install.py
```

---

## 步驟 1 — regression suite(baseline)

```
$ python scripts/validate.py --self-check
OK validate self-check green            rc=0
$ python scripts/validate.py
OK validate green                       rc=0
$ python scripts/install.py --self-check
FAIL skills/bad: missing SKILL.md       <- self-check 自己的 fixture 輸出,不是真的紅
OK install self-check green             rc=0
```

全綠。(`FAIL skills/bad` 是 install self-check 故意造的 fixture,#37 那輪也一樣。)

## 步驟 2 — 第 9 條:本機開發 loop 實跑

真的改一個 skill 檔,跑完整 loop,前後量「未 push 的 commit 數」證明沒 push:

```
unpushed_before=5                       # git rev-list --count origin/main..HEAD
probe_in_home_before=0                  # grep QA38PROBE ~/.claude/skills/next/SKILL.md

$ # 在 skills/next/SKILL.md 尾端插入 "<!-- QA38PROBE -->"
$ python scripts/validate.py
OK validate green                       rc=0
$ python scripts/install.py
                                        rc=0
probe_in_home_after=1                   # 改動已生效在 ~/.claude/skills/
unpushed_after=5                        # 沒 push,數字沒動
```

還原,確認 install 是 idempotent 的雙向同步(不是只會加不會減):

```
$ git checkout -- skills/next/SKILL.md
$ python scripts/install.py             rc=0
probe_in_home_after_revert=0
$ git status --short                    # 乾淨
unpushed_final=5
```

第 9 條成立:改完 → validate 綠 → install → 新內容立刻在 `~/.claude/skills/` 生效,全程沒碰 GitHub。
#36 收緊 validate 之後這條 loop 沒被改動。

## 步驟 3 — 第 10 條:README 原文

`README.md` intro 之後、`/next` 之前的「## 安裝:兩條路,先看你是哪一種人」段,分成
`### A. 使用者` 與 `### B. 開發者` 兩個子段,各自標明服務對象:

- A 給「只想用這套產線的人(含未來別台機器上的自己)」— `npx skills add c3lew/Skills`、
  `-a codex`、`npx skills update`,並標明預設全域、裝完打 `/next` / `$next`、
  用的是 vercel-labs/skills 公用 CLI、repo 目前 private 這條路要等轉 public 才通。
- B 給「要改這個 repo 裡的 skill 的人」— `validate.py` → `install.py`,粗體寫出
  「立刻生效,不用 push」,並說明 install 自己會先 validate、紅就拒裝、完全不碰 GitHub。
- 段尾提醒兩條路裝到同一位置、後裝蓋前面,在本 repo 開發時別用 A 蓋掉 working copy。

完整原文見 `README.md`(commit `7d4d862`)。

## 步驟 4 — 獨立 judge

乾淨 subagent,只餵上面兩條驗收原句 + 步驟 2 的終端實錄 + 步驟 3 的 README 原文,
不餵實作脈絡:

- **第 9 條:pass**
- **第 10 條:pass**

judge 另外指出的觀察(非驗收原句範圍)記在下方 known issues。

## 步驟 5 — 收尾 regression 複跑

```
$ python scripts/validate.py --self-check   # OK
$ python scripts/validate.py                # OK
$ git status --short                        # clean
```

---

## Known issues(非 blocking)

- `python scripts/install.py --self-check` 會印一行 `FAIL skills/bad: missing SKILL.md` 才印
  `OK install self-check green`。那是 fixture 的預期輸出,但看起來像真的紅,client-demo
  時容易嚇到人。judge 也點到這點。純顯示問題,不影響行為。

## 未涵蓋

- **A 路徑本身沒實跑** — `npx skills add c3lew/Skills` 需要 repo 是 public(或帳號有存取權),
  目前 private,跑不了。那是驗收清單第 1、2 條的事(#39 之後),本票只驗「文件講清楚」。
  連帶地 `-a codex`、`npx skills update` 的實際行為也未經本輪驗證,只驗文件敘述。

## 步驟 7 — 固化(client-demo 過關後)

步驟 2 那條「改 skill → validate → install → 立刻生效」原本只是一次性手動實錄,
現在進 `install.py --self-check` 常駐:拿 repo 裡**真的**第一個 skill 目錄複製進
temp repo,install 一次(dest 沒有 probe)→ 在 source 塞 `<!-- QA38PROBE -->` 再 install
(dest 抓得到)→ 還原再 install(dest 又沒了)。就是 probe 0 → 1 → 0 那條 loop。

```
$ python scripts/install.py --self-check
OK install self-check green
```

test-the-test(兩次 mutation):

```
# A. install 遇到已存在的 target 就跳過  -> 舊的 stale 案例先紅(既有覆蓋),不算數
AssertionError: assert not (dest / "good" / "stale.md").exists()

# B. mirror 照做,但把「已裝在 dest 的檔案」bytes 寫回去(= 不覆蓋使用者機器上的版本)
#    -> 舊案例(stale 清除、idempotency)全綠,只有新案例紅
AssertionError: build            <- 新 case 唯一抓到
```

收尾 regression:`validate --self-check` / `validate` / `install --self-check` / `install` 全綠。

第 10 條(README 文字)沒有可固化的自動化 scenario — 是散文,不在 validate 的 lint 範圍,
不硬做關鍵字比對(README 一改字就假紅)。由 client-demo 的人眼把關。
