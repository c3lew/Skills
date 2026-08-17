# Skills — 像軟體公司一樣開發的 solo-agent 產線

這個 repo 是一套 Claude Code skills(**source of truth 在這裡**,安裝到 `~/.claude/skills/` 全專案共用),讓一個人 + agent 的開發流程長出軟體公司才有的東西:PM 訪談、QA、client 驗收、發佈、維護、retro。你扮演 **client**(只談看得到的行為),技術決策系統自己拍、自己留紀錄。

## 安裝:兩條路,先看你是哪一種人

### A. 使用者 — 我只想用這套產線(含未來在別台機器上的自己)

一行裝好,不用 clone、不用 Python:

```bash
npx skills add c3lew/Skills -g -a claude-code -a codex -y   # 兩個 agent 一起裝,全域
npx skills update -g -y                                     # 之後拉新版
```

- `-g` **不能省** — 不加的話 CLI 裝成 project-level(丟在你當下目錄的 `.agents/skills/`),換個專案就叫不到。
- 裝到哪:Claude Code → `~/.claude/skills/`(symlink)、Codex → `~/.agents/skills/`(本體)。兩邊指同一份,所有專案吃到同一版。
- 只要一個 agent 就砍掉另一個 `-a`(agent 名是 `claude-code` / `codex`,一個 `-a` 帶一個名字,逗號分隔會被擋)。
- 裝完直接在 Claude Code 打 `/next`,或在 Codex 打 `$next`。
- 用的是公用 CLI [vercel-labs/skills](https://github.com/vercel-labs/skills),本 repo 沒有自己的安裝器。

### B. 開發者 — 我要改這個 repo 裡的 skill

改完**立刻生效,不用 push**、不用等 npx:

```bash
python scripts/validate.py   # 結構 lint,紅就先修
python scripts/install.py    # 抄進兩個 agent 的全域目錄(它會先跑 validate,紅就拒裝)
```

先跑 `validate.py` 是為了看清楚錯在哪 — 直接跑 `install.py` 也安全,它自己會 validate,紅就拒裝。它會同時抄進 `~/.claude/skills/`(Claude Code)和 `~/.agents/skills/`(Codex),裝完馬上生效,同一個 session 重開就吃得到。這條路完全不碰 GitHub,改一行測一次的迭代速度不受影響。

> 兩條路裝到同一個位置,後裝的蓋前面的。在本 repo 開發時用 B,別把自己的 working copy 用 A 蓋掉。

## 迷路了?一個指令

```
/next
```

它會讀現場(票上的交棒 comment、ticket 狀態、repo 地基)直接告訴你「現在在哪、下一步跑什麼」。**這個 README 記不住沒關係,`/next` 記得。** 想看圖形化現況就 `/tracking-viz` 產 dashboard。

## 產線長什麼樣

```
 新 idea(大而模糊)──▶ /wayfinder 建圖 ──┐
                                          ▼
 清楚的 feature ────────────────────▶ /pm-intake 訪談出 spec(長相分岔 → /ui-mockup 給你選)
                                          │
                                          ▼
                                   /slice-tickets 切 vertical slice 票
                                          │
                            ┌─────────────▼──────────────┐
                            │  每張票的 QA loop           │
                            │  /build ──▶ /qa ──▶ 綠?    │
                            │     ▲        │ blocking     │
                            │     └────────┘ 回修         │
                            └─────────────┬──────────────┘
                                          ▼
                                   /client-demo 你看實錄逐條點頭(過關即發新版)
                                          │
                                          ▼
                                   /close 結案(核對完工定義才關票)
                                          │
                 上線後 ──▶ /maintain 進件分類 ──▶ 回產線
                 攢夠錯誤紀錄 ──▶ dashboard 提示 ──▶ 你說跑才 /retro
```

環節之間靠 **ticket 接力棒**:每個環節收尾在票上留「下一步:`/skill #N`(Codex: `$skill #N`)」comment,你複製貼上就開下一棒。

## 指令速查

| 指令 | 什麼時候用 | 它做什麼 |
|------|-----------|---------|
| `/next` | 不知道現在該幹嘛 | 讀現場推薦下一棒,只指路不執行 |
| `/wayfinder` | 大而模糊的 idea | 建圖拆成 features,成熟一個交棒 pm-intake(matt-pocock 原件) |
| `/pm-intake` | 清楚的單一 feature 需求 | 白話訪談 → 拍板驗收清單 → 產 spec |
| `/ui-mockup` | 長相/操作感有分岔(通常 pm-intake 自己叫) | 可點 HTML prototype 給你選,拍板入 spec |
| `/slice-tickets` | spec 拍板後 | 切 vertical slice 票,每張標覆蓋的驗收項 |
| `/build #N` | 票要開工 | wrap 原件 `/implement`(tdd + code-review + commit),保證留交棒 comment |
| `/qa #N` | build 完 | agent 扮演使用者拿驗收清單實測,獨立 judge 抓 works-but-wrong,順手錄 demo 實錄 |
| `/client-demo #N` | QA blocking 清零 | 逐條放 QA 實錄給你點頭;過關即發新版(build + 換裝 + release note) |
| `/close #N` | 過關 / fix 驗完 | 核對完工定義、執行票上完工動作(deploy 等)、更新 dashboard、關票 |
| `/tracking-viz` | 想看專案現況 | 產一頁全白話 HTML dashboard(現在在哪 + 下一步) |
| `/maintain` | 上線後報 bug / 丟想法 / 清 tech-debt | 分類開票指路,session 開頭順掃 error log |
| `/retro` | dashboard 提示「該 retro 了」且你說跑 | 掃錯誤紀錄找 pattern,提案改進系統本身,你逐條點頭才改 |

## 常見情境

- **「我想做一個新東西」** → 能一句話講清楚「使用者做什麼 → 得到什麼」就 `/pm-intake`;講出來像一個產品就 `/wayfinder`。選錯也會被 agent 導回正軌。
- **「這裡怪怪的 / 壞了」** → 上線後直接白話丟給 `/maintain`,它負責追問、分類、開票。你報的 bug 要你點頭才算修好。
- **「現在進度到哪?」** → `/tracking-viz`,或直接問 agent「接下來做什麼」(會觸發 `/next`)。
- **「demo 要我做一堆操作好麻煩」** → 不會了:demo 預設放 QA 實跑的錄影,你看完逐條點頭就好;想親手摸再說一聲。
- **「agent 一直提示該 retro 了」** → 說「跑 retro」就好,它全自動產報告,最後你逐條說改/不改。
- **「為什麼它自己做了某個技術決定?」** → 自動拍板的決策都有白話三行制紀錄(做了什麼選擇 / 對你的影響 / 反悔成本),dashboard「最近幫你做的決定」看得到;拍錯了在 demo 說「不對」就會走修正回路。

## 幾個要懂的詞(完整版見 [CONTEXT.md](CONTEXT.md))

- **驗收清單**:pm-intake 收斂回合你拍板的清單,之後 QA 只認它 — 它是「對不對」的唯一標準。
- **接力棒**:票上的「下一步:`/skill #N`(Codex: `$skill #N`)」comment,產線靠它串起來。
- **過關**:五條全成立才算 — 你親口 OK、blocking 清零、known issues 有處置、regression 全綠、scenarios 已固化。
- **決策投影**:每個技術決策發到 tracker 的 append-only comment,dashboard 讀這裡。
- **Retro 餵食口**:retro 的三個原料 — 拍板錯更正紀錄、tech-debt backlog、QA 漏抓。

## Repo 結構

```
docs/
  blueprint.md        整體設計藍圖(產線表、接線圖、原件去留)
  specs/              每個 skill 一份行為 spec
  disciplines/        跨 skill 共用紀律(訪談、技術決策)— 改一處全體生效
  agents/             tracker / labels / domain 慣例
skills/               自建 + 收編 skills(SKILL.md + references/)— source of truth
scripts/
  validate.py         結構 lint(frontmatter、斷連結、引用不得跑出 skill 目錄、discipline 副本同步)
  install.py          idempotent 安裝到 ~/.claude/skills/(先 validate,紅就拒裝)
CONTEXT.md            ubiquitous language 詞彙表
```

## 改這個 repo 的規矩

1. **spec 是正本**:改行為先改 `docs/specs/`,再同步 SKILL.md。
2. **disciplines 改 `docs/disciplines/`**,然後把各 skill `references/` 的副本同步成 byte 一致(validate 會抓不同步)。
3. **matt-pocock 原件分兩類**:產線會叫的四個(`to-tickets` / `to-spec` / `triage` / `implement`)已 fork 收編進本 repo(模型可叫、全權控制,upstream 更新手動 port);其餘原件不改,要加行為開薄層 wrap skill(wrap 不能跟未收編原件同名,install 會蓋掉)。
4. 每次改完:`python scripts/validate.py` 綠 → `python scripts/install.py` 換裝 → commit。
5. 系統性的流程改進走 `/retro`,不要散落在對話裡改。
