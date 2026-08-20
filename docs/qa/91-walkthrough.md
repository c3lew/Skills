# `/qa #91` walkthrough — 認 event loop 驅動改看名字綁到什麼

**HEAD**: `14f69f2` ｜ 一鍵重開:`bash scripts/qa/91-walkthrough.sh "$(mktemp -d)/qa91"`

這一輪驗的是 #91(`DRIVEN_BY` 走 `CONSUMED_BY` 現成的 name-only 機制,而 `run` / `wait` /
`gather` 是隨便一支 script 都會撞的名字,所以同一條判準在兩個方向各開一個開關:任意物件的
`.run(coroutine)` 就算驅動、名字被任何 scope 綁走就整條放棄)修完之後,#60 AC1 的原句逐條
還成不成立。範圍 = #91 的重現 scenario + 既有 regression suite + 全域修前對照 + 獨立實跑
oracle + 拿修法自己的三把尺做的同型全掃。全程 bash xtrace,指令與輸出同一份,沒有事後
render。

**結論:判 fail,兩條 blocking。**

- **票上宣稱的數字全部複驗過,一格不差**:兩面母體 `--driven-attr` 12/0、`--driven-shadow`
  12/0(修前各 12/10,STEP 2 / STEP 3);十三張天花板表 + 十一張 known issue 表逐格比對
  一格沒動(STEP 5 / STEP 6);`87-oracle.py` 84/0;`87-prevdiff.py` 對 `55fc8eb` 的「本輪
  引入的誤判」14 → 4,剩下 4 格全在 `AWAIT_SHAPES`(#92 範圍)。
- **對這一輪自己的 baseline 做全域對照,結果是滿分**:222 格 fixture 逐格比 `fa9d0c3` vs
  `14f69f2`,翻面 20 格**全部是「修好」,本輪引入的誤判 0**(STEP 7)。
- **但那 222 格蓋不到這一輪動的地方。** 拿 `14f69f2` 自己新開的三個零件(`asyncio_graph` /
  `from_asyncio` / `drives`)各當一把尺重掃(STEP 10 / 11 / 12),三面都量出東西,合計
  **1 格誤放 + 10 格誤紅是本輪引入的**,另有 5 格誤放、1 格誤紅是舊病沒收。
- **票上第 6 項(「改完的判準要有 mutation 咬得住」)不成立**:產出說明宣稱的九個 knob
  **repo 裡一個都沒有**(STEP 13);QA 照那九個名字重建之後,8 個咬住、`loop_from_bare_name`
  沒咬住(STEP 14)。產出說明另外宣稱「`87-mutate.py` 的 17 個 knob 現在全部咬得住」,實測
  16/17,`consumes_no_await` 沒咬住(STEP 16 / 16b)。兩個沒咬住的都**不是 no-op** ——
  同一個 mutation 下 sweep 立刻掉格,所以判準是真的被拆掉了,只是沒有人會知道。

## 一、票上要求的東西:逐條複驗

| 票上要求 | 實測 | 判定 |
| --- | --- | --- |
| `--driven-attr` 母體 12 要 0 | 12/0(修前 12/10) | pass |
| `--driven-shadow` 母體 12 要 0 | 12/0(修前 12/10) | pass |
| 十三張「不得放掉的天花板」 | 逐格比對,一格沒動 | pass |
| 十一張 known issue 的紅字數 | 逐格比對,一格沒動 | pass |
| `87-prevdiff.py` 本輪引入的誤判從 14 降下來 | 14 → 4(剩下的全在 #92 範圍) | pass |
| `87-oracle.py` 維持 84/0 | 84/0(加上本輪新開的 26 格 = 110/0) | pass |
| `validate.py` + 五支 self-check 全綠 | 全綠 | pass |
| **改完的判準要有 mutation 咬得住** | 九個 knob 不在 repo;重建後 8/9;另外 `consumes_no_await` 也沒咬住 | **fail** |

天花板那兩張表的完整數字在 STEP 5 / STEP 6 的原始輸出裡,這裡不重抄。

## 二、本輪同型全掃(STEP 10 / 11 / 12)

`14f69f2` 把「這個 call 算不算 event loop 驅動」從讀名字換成解 callee,靠三個新零件:
`asyncio_graph`(哪些名字真的來自 asyncio)、`from_asyncio`(receiver 認不認)、`drives`
(呼叫算不算驅動)。這三個零件各自有一組**沒被列舉完**的形狀。每一格的期望值不是手標的
—— `87-oracle.py --91` 把同一份 fixture 真的 `python` 跑起來,把 `sys.stdout.buffer.write`
換成會記帳的 proxy,看那行到底有沒有執行,**26 格全對得上**(STEP 9,母體 110/0)。

### 尺一 `--graph-scope`(誤放)母體 10 —— 現況 6 誤放,修前 8

`asyncio_graph` 把綁定**收在哪裡**完全不看(def 裡的 local import、永遠不會跑的 def 裡的
local、class body 的 attribute,全部當成模組層的名字),而且**名字被綁走之後不追**。

| case | 期望 | 現在 | 修前 |
| --- | --- | --- | --- |
| `import asyncio` 之後 `asyncio = MagicMock()` | RED | **GREEN 誤放** | GREEN |
| 別名版 `import asyncio as aio` 之後 `aio = MagicMock()` | RED | **GREEN 誤放** | GREEN |
| 永遠不會跑的 def 裡有 `loop = asyncio.new_event_loop()`,模組層的 `loop` 是別的東西 | RED | **GREEN 誤放** | GREEN |
| `from asyncio import run` 寫在別的 def 裡,模組自己有 `def run(x)` | RED | **GREEN 誤放** | RED ← **本輪引入** |
| `from asyncio import Runner` 之後 `Runner = MagicMock`,`r = Runner()` | RED | **GREEN 誤放** | GREEN |
| class body 裡 `loop = asyncio.new_event_loop()`,模組層的 `loop` 是別的東西 | RED | **GREEN 誤放** | GREEN |
| 對照:`from asyncio import sleep` + `x = sleep` + `x.run(...)` | RED | RED ok | GREEN(本輪修好) |
| 對照:`ok = asyncio.iscoroutinefunction(f)` + `ok.run(...)` | RED | RED ok | GREEN(本輪修好) |
| 對照:沒重綁,`asyncio.run(adump())` | GREEN | GREEN ok | GREEN |
| 對照:`from asyncio import run` 在模組層,`run(adump())` | GREEN | GREEN ok | RED(本輪修好) |

修好 3 格、引入 1 格,淨 8 → 6。`ponytail` 註解宣告過「綁走了不追」這條成本,但沒有列舉,
也沒有任何 fixture 釘著它。

### 尺二 `--loop-binding`(誤紅)母體 9 —— 現況 7 誤紅,修前 **0**

loop 的綁定只從 `ast.Assign` 跟 `ast.withitem` 讀。**這七格全部是本輪引入的。**

| case | 期望 | 現在 | 修前 |
| --- | --- | --- | --- |
| AnnAssign `loop: object = asyncio.new_event_loop()` | GREEN | **RED 誤紅** | GREEN ← 本輪引入 |
| walrus `if (loop := asyncio.new_event_loop()):` | GREEN | **RED 誤紅** | GREEN ← 本輪引入 |
| for target `for loop in [asyncio.new_event_loop()]:` | GREEN | **RED 誤紅** | GREEN ← 本輪引入 |
| tuple 解包 `loop, tag = asyncio.new_event_loop(), "x"` | GREEN | **RED 誤紅** | GREEN ← 本輪引入 |
| 進容器再取出來 `loops = [asyncio.new_event_loop()]` + `loops[0]` | GREEN | **RED 誤紅** | GREEN ← 本輪引入 |
| 經自己的 def 拿到 loop `loop = get_loop()` | GREEN | **RED 誤紅** | GREEN ← 本輪引入(註解有宣告成本) |
| loop 當參數傳進來 `def drive(loop)` | GREEN | **RED 誤紅** | GREEN ← 本輪引入(註解有宣告成本) |
| 對照:`loop = asyncio.new_event_loop()` 直球 | GREEN | GREEN ok | GREEN |
| 對照:`with asyncio.Runner() as r` | GREEN | GREEN ok | GREEN |

**修前那個 0 是碰巧的,不是實力**:修前的判準只看呼叫的名字、不看 receiver,所以這九格通通
放行,剛好全對。這點必須誠實揭露,不能拿「修前 9/0」當「修前比較好」的證據。但它也只說明
**修前的 0 沒有價值**,不能說明**現在的 7 可以接受** —— 這七種寫法是每天在寫的 Python,不是
刁鑽 corner case,而其中五種(AnnAssign / walrus / for target / tuple 解包 / 容器取出)
`ponytail` 註解**沒有宣告過**。

### 尺三 `--loop-source`(誤紅)母體 7 —— 現況 4 誤紅,修前 2

`LOOP_FROM` 是四個名字的清單(`new_event_loop` / `get_event_loop` / `get_running_loop` /
`Runner`),不是型別判讀。

| case | 期望 | 現在 | 修前 |
| --- | --- | --- | --- |
| `asyncio.get_event_loop_policy().new_event_loop()` | GREEN | **RED 誤紅** | GREEN ← 本輪引入 |
| `asyncio.SelectorEventLoop()` 直接建一個 loop | GREEN | **RED 誤紅** | GREEN ← 本輪引入 |
| `with asyncio.Runner() as r: r.get_loop()` | GREEN | **RED 誤紅** | GREEN ← 本輪引入 |
| 自己包一層的 runner `class Loop: def run(self, c)` | GREEN | **RED 誤紅** | RED(舊病,註解有宣告成本) |
| 對照:`asyncio.new_event_loop()` | GREEN | GREEN ok | GREEN |
| 對照:`asyncio.Runner().run(adump())` | GREEN | GREEN ok | GREEN |
| 對照:`MagicMock().run(coroutine)` | RED | RED ok | GREEN(本輪修好) |

## 三、mutation 那半(STEP 13 / 14 / 16 / 16b)

票上第 6 項逐字:「**這次補上 self-check fixture**:改完的判準要有 mutation 咬得住」。

1. **產出說明宣稱的九個 knob(`drives_always_true` / `drives_name_only` /
   `drives_no_from_import` / `graph_no_alias` / `graph_no_fixpoint` / `graph_no_withitem` /
   `loop_from_anything` / `loop_from_bare_name` / `revert_to_name_list`)在 repo 裡一個都
   找不到** —— `grep` 整個 `scripts/` + `skills/` 全空(STEP 13),`87-mutate.py` 只有 17 個
   knob,全是 #86 / #87 的。宣稱不是證據:下一個人要重跑這九格,沒有東西可以跑。
2. QA 照那九個名字重建了 `scripts/qa/91-mutate.py`,逐一改壞(STEP 14):**8 個轉紅、
   `loop_from_bare_name` 沒轉紅**。它不是 no-op —— 同一個 mutation 下尺一的誤放從 6 格變
   7 格(`x = sleep` 那格翻成誤放)。
3. 產出說明另外宣稱「`87-mutate.py` 的 17 個 knob 現在全部對得到錨、全部咬得住
   (`gens_no_async` / `consumes_no_await` / `consumes_no_driven` 這三個在 #87 是綠的 ——
   現在紅了)」。實測 **16/17**:`consumes_no_await` 改壞之後 `--self-check` 照樣綠
   (STEP 16 / 16b),而同一個 mutation 下 `--async-defer` 從 12/0 掉到 12/1、
   `--await-shapes` 從 8/4 掉到 8/5 —— 一樣不是 no-op。

## 四、oracle 獨立性

這串 sweep 全部 import 受測物自己的 `stream_encoding_issues`,它綠只證明它同意自己。第二把
尺是 `87-oracle.py`(#87 那輪建的)—— **一行守門規則都不讀**,把同一份 fixture 真的
`python` 跑起來,把 `sys.stdout.buffer.write` 換成會記帳的 proxy,看那一行到底有沒有執行。
本輪新開的 26 格 fixture 一起掛進去(`--91`),**母體 110,期望與實跑不合 0**(STEP 9)。

**弱點誠實揭露**:尺一有兩格對照(`x = sleep` 之後 `x.run(...)`、`ok.run(...)`)的 ground
truth RED 是「跑起來就拋例外」換來的,不是純粹「那行在死碼位置」換來的 —— 這是 #87 的
judge 提過的 oracle 弱點,那兩格沒辦法換成 `MagicMock`(receiver 必須真的是從 asyncio
import 進來的東西)。結論方向不受影響(兩格都是 RED),但下一輪拿它當尺要記得這件事。
其餘各格的 receiver 都是 `MagicMock`,吃下引數、什麼都不做、也不炸,RED 純粹來自 body
沒跑。

## 五、開出來的票

**開票的切法(採 #87 judge 的 root-cause 論,不照「一把尺一張票」切)**:三把尺量的是同一
組零件(`asyncio_graph` / `from_asyncio` / `drives`)的三個面 —— 尺一是「多算驅動」,尺二
尺三是「少算驅動」。放寬綁定形狀(尺二 / 尺三)會讓更多名字進 `roots`,直接加劇尺一的誤放;
收緊 scope(尺一)會讓更多真的在跑的 loop 追不到,直接加劇尺二尺三的誤紅。**分開修一定會
左右互搏**,所以合成一張 blocking 票。這跟 #91 自己當初把兩面合成一張是同一個理由。

| 票 | 級別 | 內容 |
| --- | --- | --- |
| A | **blocking** | callee 解析的深度:尺一 6 格誤放(1 格本輪引入)+ 尺二 7 格誤紅(全本輪引入)+ 尺三 4 格誤紅(3 格本輪引入) |
| B | **blocking** | mutation 證據:九個 knob 不在 repo;`loop_from_bare_name` 與 `consumes_no_await` 沒被 self-check 咬住,且都不是 no-op |

**judge 有異議的地方(原文列出來讓 client 決定)**:專案慣例是「誤放 = blocking,誤紅 =
known issue」,本報告把尺二尺三的誤紅併進 blocking 票 A 是走 root-cause 論,沒有正式翻掉
那條慣例。judge 主張這一輪應該**正式破例**:

> 專案慣例「誤紅 = known issue」的前提是誤紅落在邊緣 shape、量少、且誤放那側有實質收斂當
> 對價。本輪三條前提全部不成立:7 格落在日常寫法、佔母體 9 格的 78%、全部本輪新造,而誤放
> 側同時還有 6 格未收 + 1 格 regression。建議這一輪破例把票 5 升為 blocking,理由不是
> 「誤紅比誤放嚴重」,而是「這個量級的誤紅會讓守門在實務上失效,等於連誤放面的價值一起
> 吃掉」。若 client 決定維持慣例,至少要標成 high-severity known issue 並排進下一輪,不要
> 進 backlog 慢慢等。

judge 對「這是不是划算的交換」的定性也一併列出:

> 「用誤紅換誤放」要成立,前提是誤放那一側真的收斂了。實際上沒有:尺一同時還有 6 格誤放,
> 而且本輪還新開一格。所以現況是**付了誤紅的代價、沒買到誤放的收斂** —— 兩面都退,只是退
> 的地方不同。

## 六、known issues(帶著走,處置由 client 在 demo 收尾確認)

- **oracle ground truth 的弱點**:尺一兩格對照的 RED 來自「跑爆」而非「死碼位置」(見第四
  節)。不影響本輪結論,但 oracle 的獨立性有缺口。
- **`--await-shapes` 8/4**:票上已宣告屬 **#92** 的範圍,本輪不重開,只複驗數字沒動。

## 七、未涵蓋範圍

- 這個專案沒有 UI 切片,不適用 Playwright walkthrough / demo 錄影 —— 交付物是守門規則本身,
  「demo 實錄」就是下面那份 xtrace(指令與輸出同一份,可以逐步重放)。
- `--await-shapes` 那四格(#92)本輪只複驗、不判。

## 八、demo 實錄與一鍵重開

**一鍵重開**(client-demo 直接抄):

```bash
bash scripts/qa/91-walkthrough.sh "$(mktemp -d)/qa91"
```

不寫任何東西到 GitHub,也不碰 repo 本體 —— mutation 全部跑在拋棄式暫存目錄的副本上,
STEP 17 用 `git status` 收尾證明。

**每條驗收項對應的實錄段落**(都在下面同一份 xtrace 裡):

| 驗收項 | 段落 |
| --- | --- |
| 跑不到 → 不得豁免(誤放面) | STEP 2、STEP 10 |
| 跑得到 → 不得誤紅(誤紅面) | STEP 2、STEP 11、STEP 12 |
| 修前對照(本輪引入了什麼) | STEP 3、STEP 7、STEP 8 |
| 天花板一格不得動 | STEP 5、STEP 6 |
| ground truth 不是手標的 | STEP 9 |
| 改完的判準要有 mutation 咬得住 | STEP 13、STEP 14、STEP 16、STEP 16b |

**單條重跑**:

```bash
python scripts/qa/87-drive-sweep.py . --driven-attr            # 票上母體一
python scripts/qa/87-drive-sweep.py . --driven-shadow          # 票上母體二
python scripts/qa/91-graph-sweep.py . --graph-scope            # 尺一(誤放)
python scripts/qa/91-graph-sweep.py . --loop-binding           # 尺二(誤紅)
python scripts/qa/91-graph-sweep.py . --loop-source            # 尺三(誤紅)
python scripts/qa/91-graph-sweep.py . --graph-scope --prev91   # 對照組:#91 修之前
python scripts/qa/87-prevdiff.py . --prev=fa9d0c3              # 全域修前對照
python scripts/qa/87-oracle.py . --91                          # 獨立實跑 oracle,110 格
python scripts/qa/91-mutate.py --list                          # QA 重建的九個 knob
```

## 九、本輪新增/改動的 QA artifact(不是產品改動)

- `scripts/qa/91-graph-sweep.py`(新)— 三把尺的 fixture 與跑法。
- `scripts/qa/91-mutate.py`(新)— 產出宣稱的九個 knob,QA 照名字重建。
- `scripts/qa/91-walkthrough.sh`(新)— 一鍵重開。
- `scripts/qa/87-oracle.py` — 加 `--91`,把本輪 26 格掛進同一把實跑 oracle(預設仍是 84 格)。
- `scripts/qa/87-prevdiff.py` — 加 `--prev=<sha>`,對照點可換(預設仍是 `55fc8eb`)。
- `scripts/qa/86-async-sweep.py` / `87-drive-sweep.py` — `BASELINES` 登記 `--prev91`
  (`fa9d0c3`)。**沒登記就靜默跑現況**這個 fallthrough 是 #87 那輪列過的 QA 工具坑,本輪
  一樣踩過一次,靠 STEP 3 的 10 vs 0 差額確認 flag 真的生效。

## 獨立 judge

以下是獨立 subagent 的判定原話。它只拿到 spec 驗收原句 + 上面的實測證據,沒有實作脈絡、
也沒有本 session 的判斷。

### 1. 驗收原句兩面

**面 A(跑不到 → 不得豁免,誤放面):fail**

票上 `--driven-attr` 12/0 是真的收乾淨了,但那只是一個窄母體。拿修法自己新開的零件當尺去掃同一件事(尺一 `--graph-scope`),母體 10 有 **6 格誤放** —— `asyncio = MagicMock()` 重綁、別名重綁、死 def 裡的 `loop = asyncio.new_event_loop()`、`Runner = MagicMock`、class body 裡的 loop……這些全部就是驗收原句要擋的那件事:名字看起來像 asyncio,實際上那條路根本跑不到 / 已經被換掉,守門照樣放行。

更難看的是其中 **1 格是本輪引入的 regression**:`from asyncio import run` 寫在別的 def 裡、模組自己有 `def run(x)` —— 修前是 RED(判對),改完變 GREEN。也就是這一輪在誤放面不只沒收乾淨,還新開了一個洞。

12/0 那個母體只能證明「這 12 個 shape 對了」,不能證明面 A 成立。判 fail,不是 works-but-wrong —— 它連功能上都沒做到,是真的漏。

**面 B(跑得到 → 不得誤紅):fail,而且是 works-but-wrong 那型**

`--driven-shadow` 12/0 也是真的,但尺二 `--loop-binding` 9 格裡 **7 格誤紅,全部本輪引入**(修前 0),尺三 `--loop-source` 7 格裡 4 格誤紅、其中 3 格本輪引入。

尺二那 7 格特別要命:`loop: object = ...`(AnnAssign)、walrus、`for loop in [...]`、tuple 解包、進 list 再取出、經自己的 helper 拿 loop、loop 當參數傳進來。這些不是刁鑽 corner case,是每天在寫的 Python。守門在這些寫法上「亂吵」,等於面 B 在最常見的路徑上直接破功。

works-but-wrong 的判法在這裡成立:修法做的是「認得出 asyncio 的名字血統」,這件事本身會動、而且做得不錯(尺一有 3 格對照從誤放修好、尺三 `MagicMock().run()` 也修好了)。但驗收原句要的是「這行 bypass 是不是真的跑得到」,修法交出來的是「這個 receiver 的名字是不是從 asyncio 來的」—— 那是一個**近似 proxy**,不是原句那件事。所以在 binding shape 一變它就整片誤紅:判準綁在名字綁定的語法形狀上,不是綁在「會不會執行」上。這就是典型的 works-but-wrong,一律算 fail。

### 2. 票上第 6 項(mutation 要咬得住):fail,而且是最嚴重的一條

兩個獨立問題疊在一起:

- **交付物根本不存在。** 產出說明宣稱「九個 knob 逐一改壞 → self-check 全紅」,實際 grep 全空,repo 裡只有前兩輪的 17 個 knob。這不是做得不夠好,是**票上明列的東西沒交、卻宣稱交了**。這條的殺傷力不只在它自己:A 段那一整排「全綠 exit 0」的證據力全部要打折,因為我們現在知道產出說明的宣稱跟 repo 現況會脫節。
- **就算照名字重建,還漏一個。** `loop_from_bare_name` 改壞之後 self-check 照樣綠,但它**不是 no-op** —— 同一個 mutation 下尺一誤放從 6 變 7。意思是這條判準可以被無聲拆掉,沒有任何一條測試會叫。這正好是第 6 項存在的理由,而它剛好漏在這裡。

### 3. 整體:不能 demo

三條理由,任一條都夠擋:
1. 誤放面還有 6 格(含 1 格本輪 regression)—— 照專案慣例,誤放 = blocking。
2. 第 6 項交付物不存在,且重建後有真漏。
3. 面 B 在常見寫法上大面積誤紅,且全是本輪造的。

票上的 12/0、天花板一格沒動、oracle 110/0、全域對照本輪誤判 0 —— 這些都是真的,也確實是紮實的工。但它們共同的問題是**量的是修法自己畫的靶**。D 段「本輪引入誤判 0」跟 F 段「本輪引入 1 格誤放 + 10 格誤紅」直接打架,差別只在 222 格 fixture 沒涵蓋這些 shape。所以 D 段那個 0 不能當免死金牌,它只說明既有 fixture 蓋不到本輪動的地方。

### 4. 該開的票(judge 原始切法,本報告採 root-cause 論合併成兩張,見第五節)

| # | 票 | 級別 | 理由 |
|---|---|---|---|
| 1 | mutation 台九個 knob 不存在,產出說明與 repo 不符 | **blocking** | 票上第 6 項的交付物缺席卻被宣稱完成。除了本身沒交,它讓所有「全綠」證據都需要重新查證。 |
| 2 | `loop_from_bare_name` 判準沒有任何測試咬住(非 no-op,拆掉會多一格誤放) | **blocking** | 第 6 項的實質失敗。一條會影響誤放面的判準可以被無聲移除。 |
| 3 | 尺一 `--graph-scope` 6 格誤放(重綁 / 別名重綁 / 死 def / class body / `Runner = MagicMock`) | **blocking** | 誤放,照慣例。且這是驗收原句面 A 的正面違反,不是週邊。 |
| 4 | 本輪 regression:`from asyncio import run` 在 def 內 + 模組自有 `def run` → 從 RED 翻成 GREEN | **blocking** | 誤放,且是本輪造的退步。獨立開票,不要跟 3 混在一起淹掉。 |
| 5 | 尺二 `--loop-binding` 7 格誤紅,全本輪引入 | 慣例是 known issue → **judge 異議,建議 blocking** | 見下方第 5 點 |
| 6 | 尺三 `--loop-source` 4 格誤紅 | known issue | 誤紅,且 shape 相對邊緣,前三格是 asyncio 的次要 API、第四格修前就有。照慣例可以帶著走。 |
| 7 | oracle ground truth 弱點:尺一兩格 RED 來自「跑起來拋例外」而非「死碼位置」 | known issue | 不影響本輪結論方向,但 oracle 的獨立性有缺口,該補純死碼版對照。 |
| 8 | `--await-shapes` 4 格誤紅 | known issue(已在 #92) | 票上已宣告範圍,不重開,只記著別忘。 |

### 5. 尺二那 7 格怎麼定性 —— 「這一輪把常見寫法弄壞了」,不是划算的交換

**先講結論:這不是「用誤紅換誤放」,因為交換根本沒成立。**

「用誤紅換誤放」要成立,前提是誤放那一側真的收斂了。實際上沒有:尺一同時還有 6 格誤放,而且本輪還新開一格。所以現況是**付了誤紅的代價、沒買到誤放的收斂** —— 兩面都退,只是退的地方不同。

再看代價本身的性質。修前尺二 9/0 是「碰巧全對」(判準只看呼叫名字、不看 receiver,所以全放行),這點誠實揭露很好,也確實不能拿它當「修前比較好」的證據 —— 修前的 0 是運氣不是實力。但這只能說明**修前的 0 沒有價值**,不能說明**現在的 7 是可接受的**。這兩件事常被混為一談。

真正決定嚴重度的是那 7 格的 shape。它們不是奇技淫巧,是 `loop: object = ...`、`for loop in [...]`、`loop, tag = ...`、`def drive(loop)` —— 每一種都是正常人會寫的 Python。守門在這些寫法上亂吵,實務後果是使用者被逼著把合法的 code 改成守門喜歡的形狀,或者直接學會無視這支守門。後者一旦發生,這支守門的誤放面做得再好都沒意義了。

而且修法的註解只宣告了其中 2 條成本(helper 回傳、參數傳入),另外 5 條(AnnAssign / walrus / for target / tuple 解包 / 容器取出)是**沒被預期到的**。已知的取捨跟沒看見的破口不一樣 —— 後者代表判準的邊界沒被想清楚,而不是被有意識地放棄。

**異議(原文帶給 client):**

> 專案慣例「誤紅 = known issue」的前提是誤紅落在邊緣 shape、量少、且誤放那側有實質收斂當對價。本輪三條前提全部不成立:7 格落在日常寫法、佔母體 9 格的 78%、全部本輪新造,而誤放側同時還有 6 格未收 + 1 格 regression。建議這一輪破例把票 5 升為 blocking,理由不是「誤紅比誤放嚴重」,而是「這個量級的誤紅會讓守門在實務上失效,等於連誤放面的價值一起吃掉」。若 client 決定維持慣例,至少要標成 high-severity known issue 並排進下一輪,不要進 backlog 慢慢等。

## 完整 xtrace(指令與輸出同一份)

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
+ echo '==== STEP 2  #91 的重現 scenario 原樣重跑(票上兩面母體各 12,要 0)===='
==== STEP 2  #91 的重現 scenario 原樣重跑(票上兩面母體各 12,要 0)====
+ python '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py' '/d/Self Project/Skills' --driven-attr
任意物件的 `.run(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                  期望 RED    實際 RED    ok
任意物件的 `.gather(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡               期望 RED    實際 RED    ok
任意物件的 `.wait(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                 期望 RED    實際 RED    ok
任意物件的 `.wait_for(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡             期望 RED    實際 RED    ok
任意物件的 `.create_task(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡          期望 RED    實際 RED    ok
任意物件的 `.ensure_future(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡        期望 RED    實際 RED    ok
任意物件的 `.run_until_complete(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡   期望 RED    實際 RED    ok
`subprocess.run(coroutine)` —— 名字撞得最兇的那個                          期望 RED    實際 RED    ok
`MagicMock().run(coroutine)` —— receiver 不炸,純粹就是沒驅動               期望 RED    實際 RED    ok
`MagicMock().create_task(coroutine)` —— 同上,換一個名字                  期望 RED    實際 RED    ok
對照:`loop.run_until_complete(adump())` 真的驅動(attribute 判讀的理由,不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:`asyncio.Runner().run(adump())` 真的驅動(不得誤紅)                     期望 GREEN  實際 GREEN  ok

母體 12,不合 0
+ python '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py' '/d/Self Project/Skills' --driven-shadow
模組自己 `def run(x)`,`asyncio.run(adump())` 真的在跑                             期望 GREEN  實際 GREEN  ok
模組自己 `def gather(x)`,`await asyncio.gather(adump())` 真的在跑                 期望 GREEN  實際 GREEN  ok
模組自己 `def wait_for(x)`,`await asyncio.wait_for(adump(), 5)` 真的在跑          期望 GREEN  實際 GREEN  ok
模組自己 `def create_task(x)`,`asyncio.create_task(adump())` 真的在跑             期望 GREEN  實際 GREEN  ok
模組自己 `def ensure_future(x)`,`await asyncio.ensure_future(adump())` 真的在跑   期望 GREEN  實際 GREEN  ok
模組自己 `def run_until_complete(x)`,`loop.run_until_complete(adump())` 真的在跑  期望 GREEN  實際 GREEN  ok
別的 def 的參數叫 run `def u(run)`                                              期望 GREEN  實際 GREEN  ok
別的 def 裡的 local 叫 wait_for `def u(): wait_for = 1`                        期望 GREEN  實際 GREEN  ok
comprehension target 叫 gather `[gather for gather in []]`                 期望 GREEN  實際 GREEN  ok
`import json as run` 撞名                                                   期望 GREEN  實際 GREEN  ok
對照:沒有任何撞名,`asyncio.run(adump())` 照常驅動(不得誤紅)                               期望 GREEN  實際 GREEN  ok
對照:自己的 `def run(x): return x` 真的沒驅動(shadowed 這半的價值,不得放掉)                  期望 RED    實際 RED    ok

母體 12,不合 0
+ echo '==== STEP 3  對照組:#91 修之前(fa9d0c3)兩面各 10 誤 ===='
==== STEP 3  對照組:#91 修之前(fa9d0c3)兩面各 10 誤 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py' '/d/Self Project/Skills' --driven-attr --prev91
任意物件的 `.run(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                  期望 RED    實際 GREEN  MISMATCH
任意物件的 `.gather(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡               期望 RED    實際 GREEN  MISMATCH
任意物件的 `.wait(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                 期望 RED    實際 GREEN  MISMATCH
任意物件的 `.wait_for(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡             期望 RED    實際 GREEN  MISMATCH
任意物件的 `.create_task(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡          期望 RED    實際 GREEN  MISMATCH
任意物件的 `.ensure_future(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡        期望 RED    實際 GREEN  MISMATCH
任意物件的 `.run_until_complete(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡   期望 RED    實際 GREEN  MISMATCH
`subprocess.run(coroutine)` —— 名字撞得最兇的那個                          期望 RED    實際 GREEN  MISMATCH
`MagicMock().run(coroutine)` —— receiver 不炸,純粹就是沒驅動               期望 RED    實際 GREEN  MISMATCH
`MagicMock().create_task(coroutine)` —— 同上,換一個名字                  期望 RED    實際 GREEN  MISMATCH
對照:`loop.run_until_complete(adump())` 真的驅動(attribute 判讀的理由,不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:`asyncio.Runner().run(adump())` 真的驅動(不得誤紅)                     期望 GREEN  實際 GREEN  ok

母體 12,不合 10
+ echo 'exit 1  <- 非 0 是要的:對照組該紅'
exit 1  <- 非 0 是要的:對照組該紅
+ python '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py' '/d/Self Project/Skills' --driven-shadow --prev91
模組自己 `def run(x)`,`asyncio.run(adump())` 真的在跑                             期望 GREEN  實際 RED    MISMATCH
模組自己 `def gather(x)`,`await asyncio.gather(adump())` 真的在跑                 期望 GREEN  實際 RED    MISMATCH
模組自己 `def wait_for(x)`,`await asyncio.wait_for(adump(), 5)` 真的在跑          期望 GREEN  實際 RED    MISMATCH
模組自己 `def create_task(x)`,`asyncio.create_task(adump())` 真的在跑             期望 GREEN  實際 RED    MISMATCH
模組自己 `def ensure_future(x)`,`await asyncio.ensure_future(adump())` 真的在跑   期望 GREEN  實際 RED    MISMATCH
模組自己 `def run_until_complete(x)`,`loop.run_until_complete(adump())` 真的在跑  期望 GREEN  實際 RED    MISMATCH
別的 def 的參數叫 run `def u(run)`                                              期望 GREEN  實際 RED    MISMATCH
別的 def 裡的 local 叫 wait_for `def u(): wait_for = 1`                        期望 GREEN  實際 RED    MISMATCH
comprehension target 叫 gather `[gather for gather in []]`                 期望 GREEN  實際 RED    MISMATCH
`import json as run` 撞名                                                   期望 GREEN  實際 RED    MISMATCH
對照:沒有任何撞名,`asyncio.run(adump())` 照常驅動(不得誤紅)                               期望 GREEN  實際 GREEN  ok
對照:自己的 `def run(x): return x` 真的沒驅動(shadowed 這半的價值,不得放掉)                  期望 RED    實際 RED    ok

母體 12,不合 10
+ echo 'exit 1  <- 非 0 是要的:對照組該紅'
exit 1  <- 非 0 是要的:對照組該紅
+ set -e
+ echo '==== STEP 4  對照組不是模擬:--prev91 是 git show fa9d0c3:scripts/validate.py 真的 import 舊版 ===='
==== STEP 4  對照組不是模擬:--prev91 是 git show fa9d0c3:scripts/validate.py 真的 import 舊版 ====
+ sed -n '/^def guard_module/,/return __import__/p' '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py'
def guard_module(repo, old):
    """`stream_encoding_issues` 的來源:現況,或某個歷史對照點。"""
    if not old:
        sys.path.insert(0, str(Path(repo) / "scripts"))
        import validate

        return validate
    src = subprocess.run(["git", "-C", str(repo), "show", f"{old}:scripts/validate.py"],
                         capture_output=True, check=True).stdout
    box = Path(tempfile.mkdtemp())
    name = "validate_" + old.replace("^", "p")
    (box / f"{name}.py").write_bytes(src)
    sys.path.insert(0, str(box))
    return __import__(name)
+ git -C '/d/Self Project/Skills' log --oneline -1 fa9d0c3
fa9d0c3 test: #87 QA — 判 fail:母體 12/0 複驗過關,但拿修法自己的三把尺掃出 attribute 十格誤放、shadow 十格誤紅、驅動位置四格誤紅,三個 knob 一個都沒被 self-check 咬住
+ sed -n '/^BASELINES/,/prev91/p' '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py'
BASELINES = {"--prev87": "55fc8eb", "--prev86": "cb7e030",
             "--prev91": "fa9d0c3"}  # #91 修之前(/qa #91 登記)
+ echo '==== STEP 5  票上「不得放掉的天花板」逐條複驗 ===='
==== STEP 5  票上「不得放掉的天花板」逐條複驗 ====
+ echo '---- 5a  --async-defer(#87,12/0)'
---- 5a  --async-defer(#87,12/0)
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' '/d/Self Project/Skills' --async-defer
coroutine 綁著沒 await `c = adump()`                        期望 RED    實際 RED    ok
裸 coroutine 在 live 語句 `adump()`                          期望 RED    實際 RED    ok
coroutine 進容器沒 await `xs = [adump()]`                    期望 RED    實際 RED    ok
coroutine 交給不 await 的 def `keep(adump())`                期望 RED    實際 RED    ok
bypass 直接寫在呼叫了但沒 await 的 async def body 裡                期望 RED    實際 RED    ok
對照:async def 綁著沒呼叫(現在就是 RED,不得放掉)                        期望 RED    實際 RED    ok
對照:async generator 呼叫了沒 iterate `agen()`(現在就是 RED,不得放掉)  期望 RED    實際 RED    ok
對照:`await adump()` 只在沒人跑的 outer 裡(現在就是 RED,不得放掉)         期望 RED    實際 RED    ok
對照:`asyncio.run(adump())` 真的跑(不得誤紅)                      期望 GREEN  實際 GREEN  ok
對照:`await adump()` 在被 `asyncio.run` 的 outer 裡(不得誤紅)      期望 GREEN  實際 GREEN  ok
對照:bypass 寫在真的被 run 的 coroutine body(不得誤紅)               期望 GREEN  實際 GREEN  ok
對照:`async for _ in agen()` 真的 iterate(不得誤紅)              期望 GREEN  實際 GREEN  ok

母體 12,不合 0
+ echo '---- 5b  --generator(#86,12/0)'
---- 5b  --generator(#86,12/0)
+ python '/d/Self Project/Skills/scripts/qa/84-generator-sweep.py' '/d/Self Project/Skills' --generator
genexp 綁著沒消費 `g = (dump() for _ in [1])`                   期望 RED    實際 RED    ok
裸 genexp 在 live 語句 `(dump() for _ in [1])`                 期望 RED    實際 RED    ok
genexp 進容器沒消費 `xs = [(dump() for _ in [1])]`               期望 RED    實際 RED    ok
genexp 交給不消費的 def `keep(dump() for _ in [1])`              期望 RED    實際 RED    ok
generator function 呼叫了但沒 iterate `gen()`                   期望 RED    實際 RED    ok
bypass 直接寫在沒人消費的 genexp body 裡                             期望 RED    實際 RED    ok
對照:generator function 綁著沒呼叫(現在就是 RED,不得放掉)                 期望 RED    實際 RED    ok
對照:`sum(1 for _ in (dump() for _ in [1]))` 真的消費(不得誤紅)      期望 GREEN  實際 GREEN  ok
對照:`g = (dump() for _ in [1])` 之後 `list(g)`(不得誤紅)          期望 GREEN  實際 GREEN  ok
對照:`for _ in gen(): pass` 真的 iterate(不得誤紅)                 期望 GREEN  實際 GREEN  ok
對照:listcomp 不是 deferred,真的跑 `[dump() for _ in [1]]`(不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:bypass 寫在真的被消費的 genexp body(不得誤紅)                       期望 GREEN  實際 GREEN  ok

母體 12,不合 0
+ echo '---- 5c  --deferred(#84,11/1,第七格是宣告過的天花板)'
---- 5c  --deferred(#84,11/1,第七格是宣告過的天花板)
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/83-deferred-sweep.py' '/d/Self Project/Skills' --deferred
綁著沒呼叫 `f = lambda: dump()`                                               期望 RED    實際 RED    ok
list 裡的 lambda 沒呼叫 `xs = [lambda: dump()]`                               期望 RED    實際 RED    ok
dict 裡的 lambda 沒呼叫 `d = {"k": lambda: dump()}`                           期望 RED    實際 RED    ok
裸 lambda literal 在 live 位置沒呼叫 `(lambda: dump())`                         期望 RED    實際 RED    ok
comprehension 裡的 lambda 沒呼叫 `[lambda: dump() for _ in []]`               期望 RED    實際 RED    ok
三元裡的 lambda 沒呼叫 `None if xs else (lambda: dump())`                       期望 RED    實際 RED    ok
天花板(#84 留,仍是誤放):def 內就地呼叫但結果丟掉 `return (lambda: dump)()` 配 `get()`       期望 RED    實際 GREEN  MISMATCH
對照:`return (lambda: dump())()` 配 `get()` —— lambda 就地被呼叫、dump 真的跑(不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:`def g(cb=lambda: dump())` 預設引數,g 沒被呼叫(現在就是 RED,不得放掉)                 期望 RED    實際 RED    ok
對照:`f = lambda: dump()` 且真的 `f()`(不得誤紅)                                  期望 GREEN  實際 GREEN  ok
對照:`(lambda: dump())()` 就地呼叫(不得誤紅)                                       期望 GREEN  實際 GREEN  ok

母體 11,不合 1
+ set -e
+ echo '---- 5d  --lambda-scope(#83,9/0)'
---- 5d  --lambda-scope(#83,9/0)
+ python '/d/Self Project/Skills/scripts/qa/81-lambda-sweep.py' '/d/Self Project/Skills' --lambda-scope
lambda 的參數撞名,馬上呼叫 `return (lambda dump: dump)(1)`              期望 RED    實際 RED    ok
lambda 存進變數再呼叫 `f = lambda dump: dump; return f(1)`            期望 RED    實際 RED    ok
交出去的就是 lambda 本身 `return lambda dump: dump`                    期望 RED    實際 RED    ok
交出去的 lambda 只是把 dump 再交出來 `return lambda: dump`                期望 RED    實際 RED    ok
dump 只當 lambda 的預設引數 `return lambda x=dump: x`                 期望 RED    實際 RED    ok
lambda 包在容器裡再取出來 `return (lambda: dump,)[0]`                   期望 RED    實際 RED    ok
巢狀 lambda `return (lambda: (lambda: dump))()`                  期望 RED    實際 RED    ok
對照:lambda 呼叫的結果真的是外面那個死碼 `f = lambda: dump; return f()`(不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:`return dump` 真的是外面那個死碼 def(不得誤紅)                           期望 GREEN  實際 GREEN  ok

母體 9,不合 0
+ echo '---- 5e  --own-names(#81,13/0)'
---- 5e  --own-names(#81,13/0)
+ python '/d/Self Project/Skills/scripts/qa/79-return-sweep.py' '/d/Self Project/Skills' --own-names
`dump = 1`(#79 已收:Name Store)           期望 RED    實際 RED    ok
參數同名 `def get(dump)`(#79 已收:arg)        期望 RED    實際 RED    ok
`with open() as dump`(Name Store,順帶收到)  期望 RED    實際 RED    ok
`for dump in [1]`(Name Store,順帶收到)      期望 RED    實際 RED    ok
walrus `(dump := 1)`(Name Store,順帶收到)   期望 RED    實際 RED    ok
巢狀 def 同名 `def dump():` 在 get 裡         期望 RED    實際 RED    ok
巢狀 class 同名 `class dump:` 在 get 裡       期望 RED    實際 RED    ok
`import os as dump` 在 get 裡             期望 RED    實際 RED    ok
`import dump` 在 get 裡                   期望 RED    實際 RED    ok
`from os import path as dump` 在 get 裡   期望 RED    實際 RED    ok
`except Exception as dump` 在 get 裡      期望 RED    實際 RED    ok
`match` 的 case 捕獲同名 `case [dump]`       期望 RED    實際 RED    ok
對照:`return dump` 真的是外面那個死碼 def(不得誤紅)    期望 GREEN  實際 GREEN  ok

母體 13,不合 0
+ echo '---- 5f  --return-carry / --callgraph / --live-overapprox / --bypass-position'
---- 5f  --return-carry / --callgraph / --live-overapprox / --bypass-position
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --return-carry
死碼 bypass + `def get(): return dump`,`get()` 結果直接丟掉  期望 RED    實際 RED    ok
同上,回傳值存進變數但從未呼叫(`x = get()`)                         期望 RED    實際 RED    ok
get() 回傳的是自己的區域變數,只是剛好撞名死碼 def                       期望 RED    實際 RED    ok
對照:回傳值真的被呼叫 `get()()`(#75 立的天花板,不得誤紅)                期望 GREEN  實際 GREEN  ok
對照:回傳值存進變數後才呼叫 `f = get(); f()`(#79 的天花板,不得誤紅)       期望 GREEN  實際 GREEN  ok
對照:`get` 自己也沒被呼叫(死碼,必須維持 RED)                        期望 RED    實際 RED    ok

母體 6,不合 0
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --callgraph
bypass 在 handler dict 裡被呼叫的 function(docstring 說仍算 live)  期望 GREEN  實際 GREEN  ok
bypass 在 alias 呼叫的 function(docstring 說仍算 live)           期望 GREEN  實際 GREEN  ok
bypass 當 callback 傳進去被呼叫(docstring 說仍算 live)              期望 GREEN  實際 GREEN  ok
bypass 在 class method,__main__ 直接呼叫(對照:.attr 名字對得上)       期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --live-overapprox
死碼裡的 bypass + live 區提到名字(不是呼叫)   期望 RED    實際 RED    ok
死碼裡的 bypass + 剛好撞名的區域變數          期望 RED    實際 RED    ok
死碼裡的 bypass + 無關物件的同名 attribute  期望 RED    實際 RED    ok
對照:死碼裡的 bypass,名字沒被提到(#70 的天花板)  期望 RED    實際 RED    ok
對照:bypass 在真的被呼叫的 main()(不得誤紅)   期望 GREEN  實際 GREEN  ok

母體 5,不合 0
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --bypass-position
bypass 在從未被呼叫的 function 內                                  期望 RED    實際 RED    ok
bypass 在 `if False:` 死碼裡                                   期望 RED    實際 RED    ok
bypass 只出現在跑不到的 except 分支                                  期望 RED    實際 RED    ok
bypass 在 `raise SystemExit` 之後的死碼                          期望 RED    實際 RED    ok
bypass 真的在 __main__ 裡用(不得誤紅)                               期望 GREEN  實際 GREEN  ok
bypass 在 main(),__main__ 呼叫它(triage-to-maintain 的形狀,不得誤紅)  期望 GREEN  實際 GREEN  ok

母體 6,不合 0
+ echo '---- 5g  --mention(13/0)與 --positional(#58 原病,4/0)'
---- 5g  --mention(13/0)與 --positional(#58 原病,4/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills'
對照:裸 print,什麼都沒有              期望 RED    實際 RED    ok
提到 bypass — 行內 comment        期望 RED    實際 RED    ok
提到 bypass — 檔頭 comment        期望 RED    實際 RED    ok
提到 bypass — module docstring  期望 RED    實際 RED    ok
提到 bypass — 字串常數              期望 RED    實際 RED    ok
提到 bypass — f-string          期望 RED    實際 RED    ok
提到 bypass — 變數名近似             期望 RED    實際 RED    ok
提到 pin — 行內 comment           期望 RED    實際 RED    ok
提到 pin — docstring            期望 RED    實際 RED    ok
提到 pin — 字串常數                 期望 RED    實際 RED    ok
用到 bypass — 真的 write          期望 GREEN  實際 GREEN  ok
用到 pin — 雙引號                  期望 GREEN  實際 GREEN  ok
用到 pin — 單引號(unparse 正規化)     期望 GREEN  實際 GREEN  ok

母體 13,不合 0
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --positional
pin 在 main(),__main__ 只呼叫它      期望 RED    實際 RED    ok
pin 在 __main__ 之前的 top-level    期望 RED    實際 RED    ok
pin 真的在 __main__ block 裡        期望 GREEN  實際 GREEN  ok
pin 在 __main__ block 裡的 try 底下  期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '---- 5h  #73 的三把尺(6/0 ×3)'
---- 5h  #73 的三把尺(6/0 ×3)
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --reach-shapes
對照:alias `f = dump; f()`(#71 修好的形狀,不得誤紅)                  期望 GREEN  實際 GREEN  ok
for 迴圈變數 `for f in [dump]: f()`                           期望 GREEN  實際 GREEN  ok
tuple 解包 `a, b = dump, dump; a()`                         期望 GREEN  實際 GREEN  ok
帶型別註記的綁定 `f: object = dump; f()`                          期望 GREEN  實際 GREEN  ok
factory 回傳 callable `def get(): return dump` + `get()()`  期望 GREEN  實際 GREEN  ok
class 屬性 `class W: run = dump` + `W.run()`                期望 GREEN  實際 GREEN  ok

母體 6,不合 0
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --call-position
對照:alias `f = dump; f()`(#71 修好的形狀,不得誤紅)                  期望 GREEN  實際 GREEN  ok
for 迴圈變數 `for f in [dump]: f()`                           期望 GREEN  實際 GREEN  ok
tuple 解包 `a, b = dump, dump; a()`                         期望 GREEN  實際 GREEN  ok
帶型別註記的綁定 `f: object = dump; f()`                          期望 GREEN  實際 GREEN  ok
factory 回傳 callable `def get(): return dump` + `get()()`  期望 GREEN  實際 GREEN  ok
class 屬性 `class W: run = dump` + `W.run()`                期望 GREEN  實際 GREEN  ok

母體 6,不合 0
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --alias
對照:alias `f = dump; f()`(#71 修好的形狀,不得誤紅)                  期望 GREEN  實際 GREEN  ok
for 迴圈變數 `for f in [dump]: f()`                           期望 GREEN  實際 GREEN  ok
tuple 解包 `a, b = dump, dump; a()`                         期望 GREEN  實際 GREEN  ok
帶型別註記的綁定 `f: object = dump; f()`                          期望 GREEN  實際 GREEN  ok
factory 回傳 callable `def get(): return dump` + `get()()`  期望 GREEN  實際 GREEN  ok
class 屬性 `class W: run = dump` + `W.run()`                期望 GREEN  實際 GREEN  ok

母體 6,不合 0
+ echo '---- 5i  #75 的 --bind-quiet(11/0)'
---- 5i  #75 的 --bind-quiet(11/0)
+ python '/d/Self Project/Skills/scripts/qa/75-binding-sweep.py' '/d/Self Project/Skills' --bind-quiet
`for f in [dump]: pass` — 綁了沒呼叫                            期望 RED    實際 RED    ok
`class W: run = dump` — 沒人叫 W.run                          期望 RED    實際 RED    ok
`class W: run = dump` + 只提到 `W.run` 不呼叫                    期望 RED    實際 RED    ok
factory 沒人叫 `def get(): return dump`                       期望 RED    實際 RED    ok
巢狀 def 的 return,只有外層在跑                                     期望 RED    實際 RED    ok
死碼裡的 for 綁定 `if False: for f in [dump]: f()`               期望 RED    實際 RED    ok
死碼裡的 class body `if False: class W: run = dump` + W.run()  期望 RED    實際 RED    ok
except handler 裡的綁定(錯誤路徑,#70 的天花板)                         期望 RED    實際 RED    ok
`get()` 只呼叫 factory,沒呼叫結果(票上已宣告的天花板)                       期望 RED    實際 RED    ok
對照:factory 結果真的被呼叫 `get()()`(不得誤紅)                         期望 GREEN  實際 GREEN  ok
對照:`class W: run = dump` + `W.run()`(不得誤紅)                 期望 GREEN  實際 GREEN  ok

母體 11,不合 0
+ echo '==== STEP 6  已開票的天花板複驗(known issues,紅字數一格不得動)===='
==== STEP 6  已開票的天花板複驗(known issues,紅字數一格不得動)====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --pin-position
pin 在 __main__ 內的 `if False:` 死碼裡          期望 RED    實際 GREEN  MISMATCH
pin 在 __main__ 內 `raise SystemExit` 之後的死碼  期望 RED    實際 GREEN  MISMATCH
pin 在 __main__ 內定義但沒人呼叫的 nested def        期望 RED    實際 GREEN  MISMATCH
pin 只出現在跑不到的 except 分支                     期望 RED    實際 GREEN  MISMATCH
pin 真的在 __main__ block 裡(不得誤紅)             期望 GREEN  實際 GREEN  ok
pin 在 block 內的 try body 裡(不得誤紅)            期望 GREEN  實際 GREEN  ok

母體 6,不合 4
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --print-detect
print 用 alias 呼叫(p = print; p(中文))                 期望 RED    實際 GREEN  MISMATCH
print 走 builtins(builtins.print(中文))               期望 RED    實際 GREEN  MISMATCH
print 當 callback 傳進去(run(print))                   期望 RED    實際 GREEN  MISMATCH
print 放在 handler dict 裡(H = {p: print}; H[p](中文))  期望 RED    實際 GREEN  MISMATCH
sys.stdout.write(中文)(build 已宣告的天花板)                期望 RED    實際 GREEN  MISMATCH
對照:真的裸 print(,沒 pin(不得漏放)                          期望 RED    實際 RED    ok
對照:真的完全不印 console(不得誤紅)                            期望 GREEN  實際 GREEN  ok

母體 7,不合 5
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --skips
__main__ 縮排在 try 底下 -> 找不到 top-level If,整檔跳過           期望 RED    實際 RED    ok
__main__ 縮排在 if True 底下 -> 同上                          期望 RED    實際 RED    ok
檔案 parse 不過(SyntaxError)-> 整檔跳過(build 已在 code 裡註明的取捨)  期望 RED    實際 GREEN  MISMATCH

母體 3,不合 1
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --name-collision
死碼 bypass 在沒被實例化的 class method,module 同名 def 被呼叫  期望 RED    實際 GREEN  MISMATCH
死碼 bypass 在後面重新定義的同名 def,被呼叫的是前面那個                期望 RED    實際 GREEN  MISMATCH
對照:死碼 bypass 的 def 沒有同名雙胞胎(#70 的天花板)              期望 RED    實際 RED    ok
對照:同名 def 但被呼叫的就是帶 bypass 的那個(不得誤紅)               期望 GREEN  實際 RED    MISMATCH

母體 4,不合 3
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --arg-widen
對照:`run(dump)`,run 真的呼叫它(#71 的 callback,不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:名字完全沒被提到(#70 的天花板)                          期望 RED    實際 RED    ok
`print(dump)` — 印出 function 物件,沒有呼叫它           期望 RED    實際 GREEN  MISMATCH
`x = str(dump)` — 引數,但 str 不會呼叫它               期望 RED    實際 GREEN  MISMATCH
`x = len([dump])` — 名字包在 list 裡當引數             期望 RED    實際 GREEN  MISMATCH
`print(f"{dump}")` — 名字在 f-string 的引數裡         期望 RED    實際 GREEN  MISMATCH
`isinstance(dump, object)` — 關鍵字/位置引數都一樣       期望 RED    實際 GREEN  MISMATCH

母體 7,不合 5
+ python '/d/Self Project/Skills/scripts/qa/75-binding-sweep.py' '/d/Self Project/Skills' --binding-shapes
對照:alias `f = dump; f()`(#71/#75 蓋到的形狀,不得誤紅)                            期望 GREEN  實際 GREEN  ok
對照:`for f in [dump]: f()`(#75 蓋到的形狀,不得誤紅)                               期望 GREEN  實際 GREEN  ok
starred 解包 `a, *rest = dump, dump; a()`                                 期望 GREEN  實際 GREEN  ok
巢狀解包 `(a, b), c = (dump, dump), dump; a()`                              期望 GREEN  實際 GREEN  ok
list target `[a, b] = [dump, dump]; a()`                                期望 GREEN  實際 GREEN  ok
多重 target `a = b = dump; a()`                                           期望 GREEN  實際 GREEN  ok
walrus `if (f := dump): f()`                                            期望 GREEN  實際 RED    MISMATCH
`with nullcontext(dump) as f: f()`(票上已宣告的天花板)                           期望 GREEN  實際 RED    MISMATCH
attribute target `W.run = dump` + `W.run()`                             期望 GREEN  實際 RED    MISMATCH
subscript target `H["a"] = dump` + `H["a"]()`(#71 的 handler dict 換個寫法)  期望 GREEN  實際 RED    MISMATCH
comprehension target `[f() for f in [dump]]`                            期望 GREEN  實際 RED    MISMATCH
預設引數 `def go(cb=dump): cb()` + `go()`                                   期望 GREEN  實際 RED    MISMATCH

母體 12,不合 6
+ python '/d/Self Project/Skills/scripts/qa/75-binding-sweep.py' '/d/Self Project/Skills' --header
對照:top-level `dump()`(不得誤紅)                         期望 GREEN  實際 GREEN  ok
對照:`for x in [dump()]: pass`(#75 補好的 header)        期望 GREEN  實際 GREEN  ok
對照:`with nullcontext(): dump()` — 呼叫在 body 裡(不得誤紅)  期望 GREEN  實際 GREEN  ok
`if dump(): pass` — if 的 test                       期望 GREEN  實際 RED    MISMATCH
`elif dump(): pass` — elif 的 test                   期望 GREEN  實際 RED    MISMATCH
`while dump(): break` — while 的 test                期望 GREEN  實際 RED    MISMATCH
`with nullcontext(dump()): pass` — with 的 items     期望 GREEN  實際 RED    MISMATCH
`@deco` — decorator 是 import 時就會跑的位置                期望 GREEN  實際 RED    MISMATCH

母體 8,不合 5
+ python '/d/Self Project/Skills/scripts/qa/79-return-sweep.py' '/d/Self Project/Skills' --result-called
`get()()`(#75 立的天花板)                    期望 GREEN  實際 GREEN  ok
`get()(1)` 帶引數                          期望 GREEN  實際 GREEN  ok
`f = get(); f()`(#79 立的天花板)             期望 GREEN  實際 GREEN  ok
`f: object = get(); f()`(AnnAssign)     期望 GREEN  實際 GREEN  ok
`a, b = get(), 1; a()`(解包)              期望 GREEN  實際 GREEN  ok
`f = get(); g = f; g()`(alias 的 alias)  期望 GREEN  實際 GREEN  ok
`M().get()()`(factory 是 method)         期望 GREEN  實際 GREEN  ok
`class W: run = get()` + `W.run()`      期望 GREEN  實際 GREEN  ok
`(f := get())()`(walrus 綁結果)            期望 GREEN  實際 RED    MISMATCH
`for f in [get()]: f()`(結果當元素)          期望 GREEN  實際 RED    MISMATCH
`f = await get(); f()`(async 版的天花板)     期望 GREEN  實際 RED    MISMATCH
反方向對照:`get()` 結果丟掉(必須維持 RED)            期望 RED    實際 RED    ok
反方向對照:`x = get()` 從未呼叫(必須維持 RED)        期望 RED    實際 RED    ok
反方向對照:`f = await get()` 從未呼叫(必須維持 RED)  期望 RED    實際 RED    ok

母體 14,不合 3
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' '/d/Self Project/Skills' --shadow-scope
別的 def 裡的 local 叫 list `def u(): list = 1`                   期望 GREEN  實際 RED    MISMATCH
別的 def 的 parameter 叫 list `def u(list)`                      期望 GREEN  實際 RED    MISMATCH
comprehension target 叫 list `[list for list in []]`          期望 GREEN  實際 RED    MISMATCH
`with … as list` 在別的 def 裡                                   期望 GREEN  實際 RED    MISMATCH
`except … as list` 在別的 def 裡                                 期望 GREEN  實際 RED    MISMATCH
class body 裡的 attribute 叫 list `class W: list = 1`           期望 GREEN  實際 RED    MISMATCH
import alias 叫 list `from collections import deque as list`  期望 GREEN  實際 RED    MISMATCH
巢狀 def 叫 list `def u(): def list(): …`                       期望 GREEN  實際 RED    MISMATCH
連死碼分支裡的 for target 都算 `if False: for list in []`             期望 GREEN  實際 RED    MISMATCH
對照:模組真的 `def sorted(g): return g`(#86 review 收的那條,不得放掉)      期望 RED    實際 RED    ok
對照:沒有任何撞名,`list(g)` 照常消費(不得誤紅)                               期望 GREEN  實際 GREEN  ok

母體 11,不合 9
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' '/d/Self Project/Skills' --attr-consumer
import 進來的物件 `.extend(genexp)`,它根本不抽乾                         期望 RED    實際 GREEN  MISMATCH
bypass 直接寫在交給 `.extend` 的 genexp body 裡                       期望 RED    實際 GREEN  MISMATCH
bypass 交給 `.next` —— 名單上任一個名字當 method 都行                      期望 RED    實際 GREEN  MISMATCH
對照:同模組自己 `class B: def extend`(被尺二那個過寬的 shadowed 擋掉,現在是 RED)  期望 RED    實際 RED    ok
對照:真的 `"".join(…)`(修法留下 attribute 判讀的理由,不得誤紅)                 期望 GREEN  實際 GREEN  ok
對照:真的 `list.extend(…)`(不得誤紅)                                  期望 GREEN  實際 GREEN  ok

母體 6,不合 3
+ python '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py' '/d/Self Project/Skills' --await-shapes
綁到名字再 await `c = adump()` + `await c`                        期望 GREEN  實際 RED    MISMATCH
綁到名字再交給 event loop `c = adump()` + `asyncio.run(c)`          期望 GREEN  實際 RED    MISMATCH
`asyncio.gather(*cs)` 的 Starred 展開                           期望 GREEN  實際 RED    MISMATCH
async comprehension 裡的 await `[await c for c in [adump()]]`  期望 GREEN  實際 RED    MISMATCH
對照:`asyncio.run(adump())` 一步到位(不得誤紅)                         期望 GREEN  實際 GREEN  ok
對照:`asyncio.run(main=adump())` 走 keyword(不得誤紅)               期望 GREEN  實際 GREEN  ok
對照:兩層 await `outer -> mid -> adump`(不得誤紅)                    期望 GREEN  實際 GREEN  ok
對照:`c = adump()` 綁著沒人驅動(#87 母體第一格,不得放掉)                      期望 RED    實際 RED    ok

母體 8,不合 4
+ set -e
+ echo '==== STEP 7  全域修前對照 a:222 格 fixture 逐格比 fa9d0c3 vs 14f69f2(本輪)===='
==== STEP 7  全域修前對照 a:222 格 fixture 逐格比 fa9d0c3 vs 14f69f2(本輪)====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/87-prevdiff.py' '/d/Self Project/Skills' --prev=fa9d0c3
對照點:fa9d0c3
DRIVEN_ATTR / 任意物件的 `.run(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                            期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.gather(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                         期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.wait(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                           期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.wait_for(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                       期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.create_task(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                    期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.ensure_future(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                  期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.run_until_complete(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡             期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / `subprocess.run(coroutine)` —— 名字撞得最兇的那個                                    期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / `MagicMock().run(coroutine)` —— receiver 不炸,純粹就是沒驅動                         期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / `MagicMock().create_task(coroutine)` —— 同上,換一個名字                            期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_SHADOW / 模組自己 `def run(x)`,`asyncio.run(adump())` 真的在跑                             期望 GREEN 修前 RED   修後 GREEN  修好
DRIVEN_SHADOW / 模組自己 `def gather(x)`,`await asyncio.gather(adump())` 真的在跑                 期望 GREEN 修前 RED   修後 GREEN  修好
DRIVEN_SHADOW / 模組自己 `def wait_for(x)`,`await asyncio.wait_for(adump(), 5)` 真的在跑          期望 GREEN 修前 RED   修後 GREEN  修好
DRIVEN_SHADOW / 模組自己 `def create_task(x)`,`asyncio.create_task(adump())` 真的在跑             期望 GREEN 修前 RED   修後 GREEN  修好
DRIVEN_SHADOW / 模組自己 `def ensure_future(x)`,`await asyncio.ensure_future(adump())` 真的在跑   期望 GREEN 修前 RED   修後 GREEN  修好
DRIVEN_SHADOW / 模組自己 `def run_until_complete(x)`,`loop.run_until_complete(adump())` 真的在跑  期望 GREEN 修前 RED   修後 GREEN  修好
DRIVEN_SHADOW / 別的 def 的參數叫 run `def u(run)`                                              期望 GREEN 修前 RED   修後 GREEN  修好
DRIVEN_SHADOW / 別的 def 裡的 local 叫 wait_for `def u(): wait_for = 1`                        期望 GREEN 修前 RED   修後 GREEN  修好
DRIVEN_SHADOW / comprehension target 叫 gather `[gather for gather in []]`                 期望 GREEN 修前 RED   修後 GREEN  修好
DRIVEN_SHADOW / `import json as run` 撞名                                                   期望 GREEN 修前 RED   修後 GREEN  修好

母體 222,翻面 20,本輪引入的誤判 0
+ echo 'exit 0  <- 非 0 是本輪引入的誤判'
exit 0  <- 非 0 是本輪引入的誤判
+ set -e
+ echo '==== STEP 8  全域修前對照 b:對 55fc8eb(票上宣稱本輪引入的誤判 14 -> 4)===='
==== STEP 8  全域修前對照 b:對 55fc8eb(票上宣稱本輪引入的誤判 14 -> 4)====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/87-prevdiff.py' '/d/Self Project/Skills'
對照點:55fc8eb
ASYNC_DEFER / coroutine 綁著沒 await `c = adump()`                                期望 RED   修前 GREEN 修後 RED    修好
ASYNC_DEFER / 裸 coroutine 在 live 語句 `adump()`                                  期望 RED   修前 GREEN 修後 RED    修好
ASYNC_DEFER / coroutine 進容器沒 await `xs = [adump()]`                            期望 RED   修前 GREEN 修後 RED    修好
ASYNC_DEFER / coroutine 交給不 await 的 def `keep(adump())`                        期望 RED   修前 GREEN 修後 RED    修好
ASYNC_DEFER / bypass 直接寫在呼叫了但沒 await 的 async def body 裡                        期望 RED   修前 GREEN 修後 RED    修好
AWAIT_SHAPES / 綁到名字再 await `c = adump()` + `await c`                           期望 GREEN 修前 GREEN 修後 RED    本輪引入
AWAIT_SHAPES / 綁到名字再交給 event loop `c = adump()` + `asyncio.run(c)`             期望 GREEN 修前 GREEN 修後 RED    本輪引入
AWAIT_SHAPES / `asyncio.gather(*cs)` 的 Starred 展開                              期望 GREEN 修前 GREEN 修後 RED    本輪引入
AWAIT_SHAPES / async comprehension 裡的 await `[await c for c in [adump()]]`     期望 GREEN 修前 GREEN 修後 RED    本輪引入
AWAIT_SHAPES / 對照:`c = adump()` 綁著沒人驅動(#87 母體第一格,不得放掉)                         期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.run(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                 期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.gather(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡              期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.wait(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.wait_for(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡            期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.create_task(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡         期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.ensure_future(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡       期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / 任意物件的 `.run_until_complete(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡  期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / `subprocess.run(coroutine)` —— 名字撞得最兇的那個                         期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / `MagicMock().run(coroutine)` —— receiver 不炸,純粹就是沒驅動              期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_ATTR / `MagicMock().create_task(coroutine)` —— 同上,換一個名字                 期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_SHADOW / 對照:自己的 `def run(x): return x` 真的沒驅動(shadowed 這半的價值,不得放掉)       期望 RED   修前 GREEN 修後 RED    修好

母體 222,翻面 21,本輪引入的誤判 4
+ echo 'exit 1  <- 剩下的 4 格全在 AWAIT_SHAPES(#92 範圍)'
exit 1  <- 剩下的 4 格全在 AWAIT_SHAPES(#92 範圍)
+ set -e
+ echo '==== STEP 9  獨立 oracle:不讀 validate.py 一行,把 fixture 真的跑起來看 bypass 有沒有執行 ===='
==== STEP 9  獨立 oracle:不讀 validate.py 一行,把 fixture 真的跑起來看 bypass 有沒有執行 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/87-oracle.py' '/d/Self Project/Skills' --91
DEFERRED / 綁著沒呼叫 `f = lambda: dump()`                                                     fixture 期望 RED   真跑 RED    ok
DEFERRED / list 裡的 lambda 沒呼叫 `xs = [lambda: dump()]`                                     fixture 期望 RED   真跑 RED    ok
DEFERRED / dict 裡的 lambda 沒呼叫 `d = {"k": lambda: dump()}`                                 fixture 期望 RED   真跑 RED    ok
DEFERRED / 裸 lambda literal 在 live 位置沒呼叫 `(lambda: dump())`                               fixture 期望 RED   真跑 RED    ok
DEFERRED / comprehension 裡的 lambda 沒呼叫 `[lambda: dump() for _ in []]`                     fixture 期望 RED   真跑 RED    ok
DEFERRED / 三元裡的 lambda 沒呼叫 `None if xs else (lambda: dump())`                             fixture 期望 RED   真跑 RED    ok (跑爆)
DEFERRED / 天花板(#84 留,仍是誤放):def 內就地呼叫但結果丟掉 `return (lambda: dump)()` 配 `get()`             fixture 期望 RED   真跑 RED    ok
DEFERRED / 對照:`return (lambda: dump())()` 配 `get()` —— lambda 就地被呼叫、dump 真的跑(不得誤紅)        fixture 期望 GREEN 真跑 GREEN  ok
DEFERRED / 對照:`def g(cb=lambda: dump())` 預設引數,g 沒被呼叫(現在就是 RED,不得放掉)                       fixture 期望 RED   真跑 RED    ok
DEFERRED / 對照:`f = lambda: dump()` 且真的 `f()`(不得誤紅)                                        fixture 期望 GREEN 真跑 GREEN  ok
DEFERRED / 對照:`(lambda: dump())()` 就地呼叫(不得誤紅)                                             fixture 期望 GREEN 真跑 GREEN  ok
GENERATOR / genexp 綁著沒消費 `g = (dump() for _ in [1])`                                      fixture 期望 RED   真跑 RED    ok
GENERATOR / 裸 genexp 在 live 語句 `(dump() for _ in [1])`                                    fixture 期望 RED   真跑 RED    ok
GENERATOR / genexp 進容器沒消費 `xs = [(dump() for _ in [1])]`                                  fixture 期望 RED   真跑 RED    ok
GENERATOR / genexp 交給不消費的 def `keep(dump() for _ in [1])`                                 fixture 期望 RED   真跑 RED    ok
GENERATOR / generator function 呼叫了但沒 iterate `gen()`                                      fixture 期望 RED   真跑 RED    ok
GENERATOR / bypass 直接寫在沒人消費的 genexp body 裡                                                fixture 期望 RED   真跑 RED    ok
GENERATOR / 對照:generator function 綁著沒呼叫(現在就是 RED,不得放掉)                                    fixture 期望 RED   真跑 RED    ok
GENERATOR / 對照:`sum(1 for _ in (dump() for _ in [1]))` 真的消費(不得誤紅)                         fixture 期望 GREEN 真跑 GREEN  ok
GENERATOR / 對照:`g = (dump() for _ in [1])` 之後 `list(g)`(不得誤紅)                             fixture 期望 GREEN 真跑 GREEN  ok
GENERATOR / 對照:`for _ in gen(): pass` 真的 iterate(不得誤紅)                                    fixture 期望 GREEN 真跑 GREEN  ok
GENERATOR / 對照:listcomp 不是 deferred,真的跑 `[dump() for _ in [1]]`(不得誤紅)                     fixture 期望 GREEN 真跑 GREEN  ok
GENERATOR / 對照:bypass 寫在真的被消費的 genexp body(不得誤紅)                                          fixture 期望 GREEN 真跑 GREEN  ok
ASYNC_DEFER / coroutine 綁著沒 await `c = adump()`                                           fixture 期望 RED   真跑 RED    ok
ASYNC_DEFER / 裸 coroutine 在 live 語句 `adump()`                                             fixture 期望 RED   真跑 RED    ok
ASYNC_DEFER / coroutine 進容器沒 await `xs = [adump()]`                                       fixture 期望 RED   真跑 RED    ok
ASYNC_DEFER / coroutine 交給不 await 的 def `keep(adump())`                                   fixture 期望 RED   真跑 RED    ok
ASYNC_DEFER / bypass 直接寫在呼叫了但沒 await 的 async def body 裡                                   fixture 期望 RED   真跑 RED    ok
ASYNC_DEFER / 對照:async def 綁著沒呼叫(現在就是 RED,不得放掉)                                           fixture 期望 RED   真跑 RED    ok
ASYNC_DEFER / 對照:async generator 呼叫了沒 iterate `agen()`(現在就是 RED,不得放掉)                     fixture 期望 RED   真跑 RED    ok
ASYNC_DEFER / 對照:`await adump()` 只在沒人跑的 outer 裡(現在就是 RED,不得放掉)                            fixture 期望 RED   真跑 RED    ok
ASYNC_DEFER / 對照:`asyncio.run(adump())` 真的跑(不得誤紅)                                         fixture 期望 GREEN 真跑 GREEN  ok
ASYNC_DEFER / 對照:`await adump()` 在被 `asyncio.run` 的 outer 裡(不得誤紅)                         fixture 期望 GREEN 真跑 GREEN  ok
ASYNC_DEFER / 對照:bypass 寫在真的被 run 的 coroutine body(不得誤紅)                                  fixture 期望 GREEN 真跑 GREEN  ok
ASYNC_DEFER / 對照:`async for _ in agen()` 真的 iterate(不得誤紅)                                 fixture 期望 GREEN 真跑 GREEN  ok
SHADOW_SCOPE / 別的 def 裡的 local 叫 list `def u(): list = 1`                                 fixture 期望 GREEN 真跑 GREEN  ok
SHADOW_SCOPE / 別的 def 的 parameter 叫 list `def u(list)`                                    fixture 期望 GREEN 真跑 GREEN  ok
SHADOW_SCOPE / comprehension target 叫 list `[list for list in []]`                        fixture 期望 GREEN 真跑 GREEN  ok
SHADOW_SCOPE / `with … as list` 在別的 def 裡                                                 fixture 期望 GREEN 真跑 GREEN  ok
SHADOW_SCOPE / `except … as list` 在別的 def 裡                                               fixture 期望 GREEN 真跑 GREEN  ok
SHADOW_SCOPE / class body 裡的 attribute 叫 list `class W: list = 1`                         fixture 期望 GREEN 真跑 GREEN  ok
SHADOW_SCOPE / import alias 叫 list `from collections import deque as list`                fixture 期望 GREEN 真跑 GREEN  ok
SHADOW_SCOPE / 巢狀 def 叫 list `def u(): def list(): …`                                     fixture 期望 GREEN 真跑 GREEN  ok
SHADOW_SCOPE / 連死碼分支裡的 for target 都算 `if False: for list in []`                           fixture 期望 GREEN 真跑 GREEN  ok
SHADOW_SCOPE / 對照:模組真的 `def sorted(g): return g`(#86 review 收的那條,不得放掉)                    fixture 期望 RED   真跑 RED    ok
SHADOW_SCOPE / 對照:沒有任何撞名,`list(g)` 照常消費(不得誤紅)                                             fixture 期望 GREEN 真跑 GREEN  ok
ATTR_CONSUMER / import 進來的物件 `.extend(genexp)`,它根本不抽乾                                     fixture 期望 RED   真跑 RED    ok (跑爆)
ATTR_CONSUMER / bypass 直接寫在交給 `.extend` 的 genexp body 裡                                   fixture 期望 RED   真跑 RED    ok (跑爆)
ATTR_CONSUMER / bypass 交給 `.next` —— 名單上任一個名字當 method 都行                                  fixture 期望 RED   真跑 RED    ok (跑爆)
ATTR_CONSUMER / 對照:同模組自己 `class B: def extend`(被尺二那個過寬的 shadowed 擋掉,現在是 RED)              fixture 期望 RED   真跑 RED    ok
ATTR_CONSUMER / 對照:真的 `"".join(…)`(修法留下 attribute 判讀的理由,不得誤紅)                             fixture 期望 GREEN 真跑 GREEN  ok
ATTR_CONSUMER / 對照:真的 `list.extend(…)`(不得誤紅)                                              fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_SHADOW / 模組自己 `def run(x)`,`asyncio.run(adump())` 真的在跑                             fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_SHADOW / 模組自己 `def gather(x)`,`await asyncio.gather(adump())` 真的在跑                 fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_SHADOW / 模組自己 `def wait_for(x)`,`await asyncio.wait_for(adump(), 5)` 真的在跑          fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_SHADOW / 模組自己 `def create_task(x)`,`asyncio.create_task(adump())` 真的在跑             fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_SHADOW / 模組自己 `def ensure_future(x)`,`await asyncio.ensure_future(adump())` 真的在跑   fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_SHADOW / 模組自己 `def run_until_complete(x)`,`loop.run_until_complete(adump())` 真的在跑  fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_SHADOW / 別的 def 的參數叫 run `def u(run)`                                              fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_SHADOW / 別的 def 裡的 local 叫 wait_for `def u(): wait_for = 1`                        fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_SHADOW / comprehension target 叫 gather `[gather for gather in []]`                 fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_SHADOW / `import json as run` 撞名                                                   fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_SHADOW / 對照:沒有任何撞名,`asyncio.run(adump())` 照常驅動(不得誤紅)                               fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_SHADOW / 對照:自己的 `def run(x): return x` 真的沒驅動(shadowed 這半的價值,不得放掉)                  fixture 期望 RED   真跑 RED    ok
DRIVEN_ATTR / 任意物件的 `.run(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                            fixture 期望 RED   真跑 RED    ok (跑爆)
DRIVEN_ATTR / 任意物件的 `.gather(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                         fixture 期望 RED   真跑 RED    ok (跑爆)
DRIVEN_ATTR / 任意物件的 `.wait(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                           fixture 期望 RED   真跑 RED    ok (跑爆)
DRIVEN_ATTR / 任意物件的 `.wait_for(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                       fixture 期望 RED   真跑 RED    ok (跑爆)
DRIVEN_ATTR / 任意物件的 `.create_task(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                    fixture 期望 RED   真跑 RED    ok (跑爆)
DRIVEN_ATTR / 任意物件的 `.ensure_future(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡                  fixture 期望 RED   真跑 RED    ok (跑爆)
DRIVEN_ATTR / 任意物件的 `.run_until_complete(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡             fixture 期望 RED   真跑 RED    ok (跑爆)
DRIVEN_ATTR / `subprocess.run(coroutine)` —— 名字撞得最兇的那個                                    fixture 期望 RED   真跑 RED    ok (跑爆)
DRIVEN_ATTR / `MagicMock().run(coroutine)` —— receiver 不炸,純粹就是沒驅動                         fixture 期望 RED   真跑 RED    ok
DRIVEN_ATTR / `MagicMock().create_task(coroutine)` —— 同上,換一個名字                            fixture 期望 RED   真跑 RED    ok
DRIVEN_ATTR / 對照:`loop.run_until_complete(adump())` 真的驅動(attribute 判讀的理由,不得誤紅)            fixture 期望 GREEN 真跑 GREEN  ok
DRIVEN_ATTR / 對照:`asyncio.Runner().run(adump())` 真的驅動(不得誤紅)                               fixture 期望 GREEN 真跑 GREEN  ok
AWAIT_SHAPES / 綁到名字再 await `c = adump()` + `await c`                                      fixture 期望 GREEN 真跑 GREEN  ok
AWAIT_SHAPES / 綁到名字再交給 event loop `c = adump()` + `asyncio.run(c)`                        fixture 期望 GREEN 真跑 GREEN  ok
AWAIT_SHAPES / `asyncio.gather(*cs)` 的 Starred 展開                                         fixture 期望 GREEN 真跑 GREEN  ok
AWAIT_SHAPES / async comprehension 裡的 await `[await c for c in [adump()]]`                fixture 期望 GREEN 真跑 GREEN  ok
AWAIT_SHAPES / 對照:`asyncio.run(adump())` 一步到位(不得誤紅)                                       fixture 期望 GREEN 真跑 GREEN  ok
AWAIT_SHAPES / 對照:`asyncio.run(main=adump())` 走 keyword(不得誤紅)                             fixture 期望 GREEN 真跑 GREEN  ok
AWAIT_SHAPES / 對照:兩層 await `outer -> mid -> adump`(不得誤紅)                                  fixture 期望 GREEN 真跑 GREEN  ok
AWAIT_SHAPES / 對照:`c = adump()` 綁著沒人驅動(#87 母體第一格,不得放掉)                                    fixture 期望 RED   真跑 RED    ok
GRAPH_SCOPE / `import asyncio` 之後名字被綁走 `asyncio = MagicMock()`                            fixture 期望 RED   真跑 RED    ok
GRAPH_SCOPE / 別名版:`import asyncio as aio` 之後 `aio = MagicMock()`                          fixture 期望 RED   真跑 RED    ok
GRAPH_SCOPE / 永遠不會跑的 def 裡有 `loop = asyncio.new_event_loop()`,模組層的 `loop` 是別的東西           fixture 期望 RED   真跑 RED    ok
GRAPH_SCOPE / `from asyncio import run` 寫在別的 def 裡,模組自己有 `def run(x)`                     fixture 期望 RED   真跑 RED    ok
GRAPH_SCOPE / `from asyncio import Runner` 之後 `Runner = MagicMock`,`r = Runner()`         fixture 期望 RED   真跑 RED    ok
GRAPH_SCOPE / class body 裡 `loop = asyncio.new_event_loop()`,模組層的 `loop` 是別的東西            fixture 期望 RED   真跑 RED    ok
GRAPH_SCOPE / 對照:`from asyncio import sleep` 之後 `x = sleep`,`x.run(...)` 不是驅動(不得放掉)       fixture 期望 RED   真跑 RED    ok (跑爆)
GRAPH_SCOPE / 對照:`ok = asyncio.iscoroutinefunction(adump)` 之後 `ok.run(...)`(不得放掉)         fixture 期望 RED   真跑 RED    ok (跑爆)
GRAPH_SCOPE / 對照:沒有任何重綁,`asyncio.run(adump())` 真的驅動(不得誤紅)                                 fixture 期望 GREEN 真跑 GREEN  ok
GRAPH_SCOPE / 對照:`from asyncio import run` 在模組層,`run(adump())` 真的驅動(不得誤紅)                 fixture 期望 GREEN 真跑 GREEN  ok
LOOP_BINDING / AnnAssign `loop: object = asyncio.new_event_loop()`                        fixture 期望 GREEN 真跑 GREEN  ok
LOOP_BINDING / walrus `if (loop := asyncio.new_event_loop()):`                            fixture 期望 GREEN 真跑 GREEN  ok
LOOP_BINDING / for target `for loop in [asyncio.new_event_loop()]:`                       fixture 期望 GREEN 真跑 GREEN  ok
LOOP_BINDING / tuple 解包 `loop, tag = asyncio.new_event_loop(), "x"`                       fixture 期望 GREEN 真跑 GREEN  ok
LOOP_BINDING / 進容器再取出來 `loops = [asyncio.new_event_loop()]` + `loops[0]`                  fixture 期望 GREEN 真跑 GREEN  ok
LOOP_BINDING / 宣告過的天花板:經自己的 def 拿到 loop `loop = get_loop()`                               fixture 期望 GREEN 真跑 GREEN  ok
LOOP_BINDING / 宣告過的天花板:loop 當參數傳進來 `def drive(loop)`                                      fixture 期望 GREEN 真跑 GREEN  ok
LOOP_BINDING / 對照:`loop = asyncio.new_event_loop()` 直球(不得誤紅)                              fixture 期望 GREEN 真跑 GREEN  ok
LOOP_BINDING / 對照:`with asyncio.Runner() as r`(不得誤紅)                                      fixture 期望 GREEN 真跑 GREEN  ok
LOOP_SOURCE / `asyncio.get_event_loop_policy().new_event_loop()`                          fixture 期望 GREEN 真跑 GREEN  ok
LOOP_SOURCE / `asyncio.SelectorEventLoop()` 直接建一個 loop                                    fixture 期望 GREEN 真跑 GREEN  ok
LOOP_SOURCE / `with asyncio.Runner() as r: r.get_loop()`                                  fixture 期望 GREEN 真跑 GREEN  ok
LOOP_SOURCE / 宣告過的天花板:自己包一層的 runner `class Loop: def run(self, c)`                        fixture 期望 GREEN 真跑 GREEN  ok
LOOP_SOURCE / 對照:`asyncio.new_event_loop()` 在名單上(不得誤紅)                                    fixture 期望 GREEN 真跑 GREEN  ok
LOOP_SOURCE / 對照:`asyncio.Runner().run(adump())` 在名單上(不得誤紅)                               fixture 期望 GREEN 真跑 GREEN  ok
LOOP_SOURCE / 對照:`MagicMock().run(coroutine)` 什麼都沒驅動(不得放掉)                                fixture 期望 RED   真跑 RED    ok

母體 110,fixture 期望與實跑不合 0
+ echo 'exit 0  <- 非 0 = 有 fixture 的期望值跟實跑對不上'
exit 0  <- 非 0 = 有 fixture 的期望值跟實跑對不上
+ set -e
+ echo '==== STEP 10  同型全掃 尺一(誤放):asyncio_graph 收綁定不看位置、綁走了不追 ===='
==== STEP 10  同型全掃 尺一(誤放):asyncio_graph 收綁定不看位置、綁走了不追 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' '/d/Self Project/Skills' --graph-scope
`import asyncio` 之後名字被綁走 `asyncio = MagicMock()`                       期望 RED    實際 GREEN  MISMATCH
別名版:`import asyncio as aio` 之後 `aio = MagicMock()`                     期望 RED    實際 GREEN  MISMATCH
永遠不會跑的 def 裡有 `loop = asyncio.new_event_loop()`,模組層的 `loop` 是別的東西      期望 RED    實際 GREEN  MISMATCH
`from asyncio import run` 寫在別的 def 裡,模組自己有 `def run(x)`                期望 RED    實際 GREEN  MISMATCH
`from asyncio import Runner` 之後 `Runner = MagicMock`,`r = Runner()`    期望 RED    實際 GREEN  MISMATCH
class body 裡 `loop = asyncio.new_event_loop()`,模組層的 `loop` 是別的東西       期望 RED    實際 GREEN  MISMATCH
對照:`from asyncio import sleep` 之後 `x = sleep`,`x.run(...)` 不是驅動(不得放掉)  期望 RED    實際 RED    ok
對照:`ok = asyncio.iscoroutinefunction(adump)` 之後 `ok.run(...)`(不得放掉)    期望 RED    實際 RED    ok
對照:沒有任何重綁,`asyncio.run(adump())` 真的驅動(不得誤紅)                            期望 GREEN  實際 GREEN  ok
對照:`from asyncio import run` 在模組層,`run(adump())` 真的驅動(不得誤紅)            期望 GREEN  實際 GREEN  ok

母體 10,不合 6
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#91 修之前(fa9d0c3)'
---- 對照組:#91 修之前(fa9d0c3)
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' '/d/Self Project/Skills' --graph-scope --prev91
`import asyncio` 之後名字被綁走 `asyncio = MagicMock()`                       期望 RED    實際 GREEN  MISMATCH
別名版:`import asyncio as aio` 之後 `aio = MagicMock()`                     期望 RED    實際 GREEN  MISMATCH
永遠不會跑的 def 裡有 `loop = asyncio.new_event_loop()`,模組層的 `loop` 是別的東西      期望 RED    實際 GREEN  MISMATCH
`from asyncio import run` 寫在別的 def 裡,模組自己有 `def run(x)`                期望 RED    實際 RED    ok
`from asyncio import Runner` 之後 `Runner = MagicMock`,`r = Runner()`    期望 RED    實際 GREEN  MISMATCH
class body 裡 `loop = asyncio.new_event_loop()`,模組層的 `loop` 是別的東西       期望 RED    實際 GREEN  MISMATCH
對照:`from asyncio import sleep` 之後 `x = sleep`,`x.run(...)` 不是驅動(不得放掉)  期望 RED    實際 GREEN  MISMATCH
對照:`ok = asyncio.iscoroutinefunction(adump)` 之後 `ok.run(...)`(不得放掉)    期望 RED    實際 GREEN  MISMATCH
對照:沒有任何重綁,`asyncio.run(adump())` 真的驅動(不得誤紅)                            期望 GREEN  實際 GREEN  ok
對照:`from asyncio import run` 在模組層,`run(adump())` 真的驅動(不得誤紅)            期望 GREEN  實際 RED    MISMATCH

母體 10,不合 8
+ set -e
+ echo '==== STEP 11  同型全掃 尺二(誤紅):loop 的綁定只從 Assign / withitem 讀 ===='
==== STEP 11  同型全掃 尺二(誤紅):loop 的綁定只從 Assign / withitem 讀 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' '/d/Self Project/Skills' --loop-binding
AnnAssign `loop: object = asyncio.new_event_loop()`        期望 GREEN  實際 RED    MISMATCH
walrus `if (loop := asyncio.new_event_loop()):`            期望 GREEN  實際 RED    MISMATCH
for target `for loop in [asyncio.new_event_loop()]:`       期望 GREEN  實際 RED    MISMATCH
tuple 解包 `loop, tag = asyncio.new_event_loop(), "x"`       期望 GREEN  實際 RED    MISMATCH
進容器再取出來 `loops = [asyncio.new_event_loop()]` + `loops[0]`  期望 GREEN  實際 RED    MISMATCH
宣告過的天花板:經自己的 def 拿到 loop `loop = get_loop()`               期望 GREEN  實際 RED    MISMATCH
宣告過的天花板:loop 當參數傳進來 `def drive(loop)`                      期望 GREEN  實際 RED    MISMATCH
對照:`loop = asyncio.new_event_loop()` 直球(不得誤紅)              期望 GREEN  實際 GREEN  ok
對照:`with asyncio.Runner() as r`(不得誤紅)                      期望 GREEN  實際 GREEN  ok

母體 9,不合 7
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#91 修之前(fa9d0c3)—— 0 不合,這七格全部是本輪引入'
---- 對照組:#91 修之前(fa9d0c3)—— 0 不合,這七格全部是本輪引入
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' '/d/Self Project/Skills' --loop-binding --prev91
AnnAssign `loop: object = asyncio.new_event_loop()`        期望 GREEN  實際 GREEN  ok
walrus `if (loop := asyncio.new_event_loop()):`            期望 GREEN  實際 GREEN  ok
for target `for loop in [asyncio.new_event_loop()]:`       期望 GREEN  實際 GREEN  ok
tuple 解包 `loop, tag = asyncio.new_event_loop(), "x"`       期望 GREEN  實際 GREEN  ok
進容器再取出來 `loops = [asyncio.new_event_loop()]` + `loops[0]`  期望 GREEN  實際 GREEN  ok
宣告過的天花板:經自己的 def 拿到 loop `loop = get_loop()`               期望 GREEN  實際 GREEN  ok
宣告過的天花板:loop 當參數傳進來 `def drive(loop)`                      期望 GREEN  實際 GREEN  ok
對照:`loop = asyncio.new_event_loop()` 直球(不得誤紅)              期望 GREEN  實際 GREEN  ok
對照:`with asyncio.Runner() as r`(不得誤紅)                      期望 GREEN  實際 GREEN  ok

母體 9,不合 0
+ set -e
+ echo '==== STEP 12  同型全掃 尺三(誤紅):LOOP_FROM 是四個名字的清單,不是型別判讀 ===='
==== STEP 12  同型全掃 尺三(誤紅):LOOP_FROM 是四個名字的清單,不是型別判讀 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' '/d/Self Project/Skills' --loop-source
`asyncio.get_event_loop_policy().new_event_loop()`    期望 GREEN  實際 RED    MISMATCH
`asyncio.SelectorEventLoop()` 直接建一個 loop              期望 GREEN  實際 RED    MISMATCH
`with asyncio.Runner() as r: r.get_loop()`            期望 GREEN  實際 RED    MISMATCH
宣告過的天花板:自己包一層的 runner `class Loop: def run(self, c)`  期望 GREEN  實際 RED    MISMATCH
對照:`asyncio.new_event_loop()` 在名單上(不得誤紅)              期望 GREEN  實際 GREEN  ok
對照:`asyncio.Runner().run(adump())` 在名單上(不得誤紅)         期望 GREEN  實際 GREEN  ok
對照:`MagicMock().run(coroutine)` 什麼都沒驅動(不得放掉)          期望 RED    實際 RED    ok

母體 7,不合 4
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#91 修之前(fa9d0c3)'
---- 對照組:#91 修之前(fa9d0c3)
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' '/d/Self Project/Skills' --loop-source --prev91
`asyncio.get_event_loop_policy().new_event_loop()`    期望 GREEN  實際 GREEN  ok
`asyncio.SelectorEventLoop()` 直接建一個 loop              期望 GREEN  實際 GREEN  ok
`with asyncio.Runner() as r: r.get_loop()`            期望 GREEN  實際 GREEN  ok
宣告過的天花板:自己包一層的 runner `class Loop: def run(self, c)`  期望 GREEN  實際 RED    MISMATCH
對照:`asyncio.new_event_loop()` 在名單上(不得誤紅)              期望 GREEN  實際 GREEN  ok
對照:`asyncio.Runner().run(adump())` 在名單上(不得誤紅)         期望 GREEN  實際 GREEN  ok
對照:`MagicMock().run(coroutine)` 什麼都沒驅動(不得放掉)          期望 RED    實際 GREEN  MISMATCH

母體 7,不合 2
+ set -e
+ echo '==== STEP 13  產出宣稱的九個 knob:repo 裡找不到(grep 全空)===='
==== STEP 13  產出宣稱的九個 knob:repo 裡找不到(grep 全空)====
+ set +e
+ grep -rn 'drives_always_true\|drives_name_only\|drives_no_from_import\|graph_no_alias\|graph_no_fixpoint\|graph_no_withitem\|loop_from_anything\|loop_from_bare_name\|revert_to_name_list' '/d/Self Project/Skills/scripts' '/d/Self Project/Skills/skills' '--include=*.py'
+ grep -v 91-mutate.py
+ echo 'exit 1  <- 非 0 = 除了 QA 這輪自己補的 91-mutate.py,一個都沒有'
exit 1  <- 非 0 = 除了 QA 這輪自己補的 91-mutate.py,一個都沒有
+ set -e
+ echo '==== STEP 14  QA 重建的九個 knob 逐一改壞 -> --self-check 要轉紅 ===='
==== STEP 14  QA 重建的九個 knob 逐一改壞 -> --self-check 要轉紅 ====
++ python '/d/Self Project/Skills/scripts/qa/91-mutate.py' --list
++ tr -d '\r'
+ for M in $(python "$ROOT/scripts/qa/91-mutate.py" --list | tr -d '\r')
+ echo '---- 14.drives_always_true'
---- 14.drives_always_true
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/91-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo drives_always_true
mutation 已套用: drives_always_true
+ set +e
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: unconsumed generator: handed to a def that does not consume it
+ echo 'exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方'
exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方
+ echo '---- 同一個 mutation 下,三把尺各掉幾格:'
---- 同一個 mutation 下,三把尺各掉幾格:
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --graph-scope
+ tail -1
母體 10,不合 8
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-binding
+ tail -1
母體 9,不合 0
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-source
+ tail -1
母體 7,不合 1
+ set -e
+ for M in $(python "$ROOT/scripts/qa/91-mutate.py" --list | tr -d '\r')
+ echo '---- 14.drives_name_only'
---- 14.drives_name_only
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/91-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo drives_name_only
mutation 已套用: drives_name_only
+ set +e
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ tail -3
    b.run(adump())
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方'
exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方
+ echo '---- 同一個 mutation 下,三把尺各掉幾格:'
---- 同一個 mutation 下,三把尺各掉幾格:
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --graph-scope
+ tail -1
母體 10,不合 8
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-binding
+ tail -1
母體 9,不合 0
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-source
+ tail -1
母體 7,不合 1
+ set -e
+ for M in $(python "$ROOT/scripts/qa/91-mutate.py" --list | tr -d '\r')
+ echo '---- 14.drives_no_from_import'
---- 14.drives_no_from_import
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/91-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo drives_no_from_import
mutation 已套用: drives_no_from_import
+ set +e
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ tail -3
    run(adump())
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方'
exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方
+ echo '---- 同一個 mutation 下,三把尺各掉幾格:'
---- 同一個 mutation 下,三把尺各掉幾格:
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --graph-scope
+ tail -1
母體 10,不合 6
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-binding
+ tail -1
母體 9,不合 7
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-source
+ tail -1
母體 7,不合 4
+ set -e
+ for M in $(python "$ROOT/scripts/qa/91-mutate.py" --list | tr -d '\r')
+ echo '---- 14.graph_no_alias'
---- 14.graph_no_alias
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/91-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo graph_no_alias
mutation 已套用: graph_no_alias
+ set +e
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ tail -3
    aio.run(adump())
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方'
exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方
+ echo '---- 同一個 mutation 下,三把尺各掉幾格:'
---- 同一個 mutation 下,三把尺各掉幾格:
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --graph-scope
+ tail -1
母體 10,不合 5
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-binding
+ tail -1
母體 9,不合 7
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-source
+ tail -1
母體 7,不合 4
+ set -e
+ for M in $(python "$ROOT/scripts/qa/91-mutate.py" --list | tr -d '\r')
+ echo '---- 14.graph_no_fixpoint'
---- 14.graph_no_fixpoint
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/91-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo graph_no_fixpoint
mutation 已套用: graph_no_fixpoint
+ set +e
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ tail -3
    loop.run_until_complete(adump())
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方'
exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方
+ echo '---- 同一個 mutation 下,三把尺各掉幾格:'
---- 同一個 mutation 下,三把尺各掉幾格:
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --graph-scope
+ tail -1
母體 10,不合 3
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-binding
+ tail -1
母體 9,不合 9
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-source
+ tail -1
母體 7,不合 5
+ set -e
+ for M in $(python "$ROOT/scripts/qa/91-mutate.py" --list | tr -d '\r')
+ echo '---- 14.graph_no_withitem'
---- 14.graph_no_withitem
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/91-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo graph_no_withitem
mutation 已套用: graph_no_withitem
+ set +e
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ tail -3
        r.run(adump())
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方'
exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方
+ echo '---- 同一個 mutation 下,三把尺各掉幾格:'
---- 同一個 mutation 下,三把尺各掉幾格:
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --graph-scope
+ tail -1
母體 10,不合 6
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-binding
+ tail -1
母體 9,不合 8
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-source
+ tail -1
母體 7,不合 4
+ set -e
+ for M in $(python "$ROOT/scripts/qa/91-mutate.py" --list | tr -d '\r')
+ echo '---- 14.loop_from_anything'
---- 14.loop_from_anything
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/91-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo loop_from_anything
mutation 已套用: loop_from_anything
+ set +e
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ tail -3
    ok.run(adump())
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方'
exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方
+ echo '---- 同一個 mutation 下,三把尺各掉幾格:'
---- 同一個 mutation 下,三把尺各掉幾格:
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --graph-scope
+ tail -1
母體 10,不合 7
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-binding
+ tail -1
母體 9,不合 7
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-source
+ tail -1
母體 7,不合 1
+ set -e
+ for M in $(python "$ROOT/scripts/qa/91-mutate.py" --list | tr -d '\r')
+ echo '---- 14.loop_from_bare_name'
---- 14.loop_from_bare_name
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/91-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo loop_from_bare_name
mutation 已套用: loop_from_bare_name
+ set +e
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ tail -3
OK validate self-check green
+ echo 'exit 0  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方'
exit 0  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方
+ echo '---- 同一個 mutation 下,三把尺各掉幾格:'
---- 同一個 mutation 下,三把尺各掉幾格:
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --graph-scope
+ tail -1
母體 10,不合 7
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-binding
+ tail -1
母體 9,不合 7
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-source
+ tail -1
母體 7,不合 4
+ set -e
+ for M in $(python "$ROOT/scripts/qa/91-mutate.py" --list | tr -d '\r')
+ echo '---- 14.revert_to_name_list'
---- 14.revert_to_name_list
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/91-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo revert_to_name_list
mutation 已套用: revert_to_name_list
+ set +e
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ tail -3
    b.run(adump())
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方'
exit 1  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方
+ echo '---- 同一個 mutation 下,三把尺各掉幾格:'
---- 同一個 mutation 下,三把尺各掉幾格:
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --graph-scope
+ tail -1
母體 10,不合 8
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-binding
+ tail -1
母體 9,不合 0
+ python '/d/Self Project/Skills/scripts/qa/91-graph-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --loop-source
+ tail -1
母體 7,不合 2
+ set -e
+ echo '==== STEP 15  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===='
==== STEP 15  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)====
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
OK validate self-check green
+ echo '==== STEP 16  87-mutate.py 的 17 個 knob 逐一改壞(產出宣稱「全部咬得住」)===='
==== STEP 16  87-mutate.py 的 17 個 knob 逐一改壞(產出宣稱「全部咬得住」)====
+ python - '/d/Self Project/Skills'
+ cat /tmp/tmp.fHsVpBy27b/qa91final/k87.txt
consumes_no_await consumes_no_builtins consumes_no_comp consumes_no_driven consumes_no_for consumes_no_nested_gen consumes_no_shadow gens_no_async gens_not_subtracted names_in_no_first_iter names_in_no_gen_stop no_eaten_calls no_eaten_via_name no_gen_fixpoint nodes_in_no_first_iter nodes_in_no_gen_stop through_no_gens
+ set +e
++ cat /tmp/tmp.fHsVpBy27b/qa91final/k87.txt
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo consumes_no_await
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'consumes_no_await self-check exit=0'
consumes_no_await self-check exit=0
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo consumes_no_builtins
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'consumes_no_builtins self-check exit=1'
consumes_no_builtins self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo consumes_no_comp
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'consumes_no_comp self-check exit=1'
consumes_no_comp self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo consumes_no_driven
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'consumes_no_driven self-check exit=1'
consumes_no_driven self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo consumes_no_for
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'consumes_no_for self-check exit=1'
consumes_no_for self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo consumes_no_nested_gen
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'consumes_no_nested_gen self-check exit=1'
consumes_no_nested_gen self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo consumes_no_shadow
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'consumes_no_shadow self-check exit=1'
consumes_no_shadow self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo gens_no_async
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'gens_no_async self-check exit=1'
gens_no_async self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo gens_not_subtracted
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'gens_not_subtracted self-check exit=1'
gens_not_subtracted self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo names_in_no_first_iter
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'names_in_no_first_iter self-check exit=1'
names_in_no_first_iter self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo names_in_no_gen_stop
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'names_in_no_gen_stop self-check exit=1'
names_in_no_gen_stop self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo no_eaten_calls
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'no_eaten_calls self-check exit=1'
no_eaten_calls self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo no_eaten_via_name
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'no_eaten_via_name self-check exit=1'
no_eaten_via_name self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo no_gen_fixpoint
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'no_gen_fixpoint self-check exit=1'
no_gen_fixpoint self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo nodes_in_no_first_iter
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'nodes_in_no_first_iter self-check exit=1'
nodes_in_no_first_iter self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo nodes_in_no_gen_stop
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'nodes_in_no_gen_stop self-check exit=1'
nodes_in_no_gen_stop self-check exit=1
+ for M in $(cat "$QA/k87.txt")
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo through_no_gens
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
+ echo 'through_no_gens self-check exit=1'
through_no_gens self-check exit=1
+ set -e
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ echo '==== STEP 16b  consumes_no_await 沒紅,但它不是 no-op ===='
==== STEP 16b  consumes_no_await 沒紅,但它不是 no-op ====
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo consumes_no_await
mutation 已套用: consumes_no_await
+ set +e
+ python /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py --self-check
OK validate self-check green
+ echo 'exit 0  <- 0 = self-check 沒咬住'
exit 0  <- 0 = self-check 沒咬住
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --async-defer
+ tail -1
母體 12,不合 1
+ echo '^ #87 的母體 12 從 0 掉到 1 —— 判準真的被拆掉了,只是沒有人會知道'
^ #87 的母體 12 從 0 掉到 1 —— 判準真的被拆掉了,只是沒有人會知道
+ python '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py' /tmp/tmp.fHsVpBy27b/qa91final/repo --await-shapes
+ tail -1
母體 8,不合 5
+ set -e
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.fHsVpBy27b/qa91final/repo/scripts/validate.py
+ echo '==== STEP 17  repo 本體沒被動過 ===='
==== STEP 17  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
 M scripts/qa/86-async-sweep.py
 M scripts/qa/87-drive-sweep.py
 M scripts/qa/87-oracle.py
 M scripts/qa/87-prevdiff.py
?? docs/qa/91-walkthrough.md
?? scripts/qa/91-graph-sweep.py
?? scripts/qa/91-mutate.py
?? scripts/qa/91-walkthrough.sh
EXIT=0
```
