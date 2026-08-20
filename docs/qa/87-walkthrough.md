# `/qa #87` walkthrough — deferred 邊界補上第三面(coroutine)

**HEAD**: `c51ba98` ｜ 一鍵重開:`bash scripts/qa/87-walkthrough.sh "$(mktemp -d)/qa87"`

這一輪驗的是 #87(`gens` 只認 body 有 `yield` 的 def,`async def` 沒 yield 就不在名單上 ——
`adump()` 建一個 coroutine 沒人 await 也算成 body 跑過了,五種形狀讓死碼 bypass 拿到豁免)
修完之後,#60 AC1 的原句逐條還成不成立。範圍 = #87 的重現 scenario + 既有 regression suite
+ 全域修前對照 + 獨立實跑 oracle + 拿修法自己的三把尺做的同型全掃。全程 bash xtrace,指令與
輸出同一份,沒有事後 render。

**結論:判 fail,兩條 blocking + 一條 known issue。**

- **AC1 後半(跑不到 → 不得豁免)**:票宣稱的那一面 **pass**。母體 12 從修前 5 誤放收到 0
  (STEP 2 / STEP 3),五格全收。
- **AC1 前半(會跑到 → 不得誤紅)**:**fail**。STEP 11 / STEP 13 量出 14 格真的在跑的
  coroutine 被判 RED,**全部是這顆 commit 帶進來的**(STEP 9 逐格對照)。
- **證據沒住在預設會跑的地方**:`c51ba98` 一條 self-check fixture 都沒補。它自己的三個
  knob(`gens_no_async` / `consumes_no_await` / `consumes_no_driven`)逐一改壞,
  `--self-check` **三個都照樣綠**(STEP 4)——同一個 mutation 下 #87 的母體立刻掉 5 / 1 / 4
  格,所以判準是真的被拆掉了,只是沒有人會知道。對照:`de68088`(#86 那顆)補了 17 條
  fixture,STEP 5 的十四個 knob 條條以真的 `AssertionError` 轉紅。
- **天花板**:STEP 7 十二張表、STEP 8 十張 known issue 表,**逐格**比對一格沒動;STEP 9
  再用 222 格 fixture 的全域對照收一次網,除了本輪三把新尺的格子以外,**沒有任何一格翻面**
  —— 排除「靠放寬豁免換綠」與「修好一格同時弄壞一格」。
- **本輪同型全掃(STEP 11 / 12 / 13)**:拿 `c51ba98` 自己的三把尺各量一遍,三面都量出東西:
  - **尺一,`DRIVEN_BY` 的名字被 `shadowed` 劃掉**(STEP 11):母體 12,**10 格誤紅**,
    `--prev87` 是 1 —— 全是本輪引入。`CONSUMED_BY` 上是 `list` / `sorted` 這種很少當變數名
    的 builtin,`DRIVEN_BY` 上是 `run` / `gather` / `wait_for` —— 隨便一支 script 有個參數叫
    `run`,整檔的 `asyncio.run(...)` 就不算驅動。方向誤紅(吵)。
  - **尺二,`DRIVEN_BY` 的 method call 只認 attribute 名字**(STEP 12):母體 12,
    **10 格誤放**,`--prev87` 也是 10 —— 不是本輪引入,但也**不是本輪修好的**:同一批檔案
    修前修後都放行,只是病因從「`async def` 沒進 `gens`」換成「`b.run(...)` 算驅動」。
    `subprocess.run(adump())` 這種一眼看不出問題的寫法就是開關。方向誤放(讓守門閉嘴)。
    跟 #88 同形狀、不同名單。
  - **尺三,驅動位置追不到**(STEP 13):母體 8,**4 格誤紅**,`--prev87` 是 1 —— 本輪引入。
    `c = adump()` 綁到名字再 `await c`(最常見的寫法)、`gather(*cs)` 的 Starred 展開、
    async comprehension 裡的 await。generator 那半有 `gen_of` / `eaten_via_name` 追名字,
    coroutine 這半沒有對應的一套。方向誤紅。

**開出來的票**:#91(blocking,尺一 + 尺二)、#92(known issue,尺三)、#93(blocking,
#87 的三個判準沒有 self-check fixture 釘著)。

**開票的切法(採 judge 的 root-cause 論,不照「一把尺一張票」切)**:judge 主張尺一與尺二
**是同一個 root cause 的兩面** —— 「一個 call 算不算 event loop 驅動」只看名字,不看那個
名字綁到什麼:名字被別人佔走就整條放棄(尺一,誤紅),名字對上就無條件相信(尺二,誤放)。
分開修會左右互搏:修緊尺二會加劇尺一的誤紅,修寬尺一會加劇尺二的誤放。所以這兩把尺合成
**一張 blocking 票**(裡面有誤放那半,照專案慣例就是 blocking),尺三另開一張 known issue。

**judge 有異議的地方(列出來讓 client 決定)**:judge 主張尺一那 10 格誤紅**不該**降成
known issue —— 理由是那 12 格裡有 6 格是最主流的寫法(`asyncio.run(adump())` 只因為模組裡
剛好有個 `def run` 就整檔誤紅),這種誤報率撐不了幾天就會有人把整條 check 關掉或加白名單,
到那時它就是全面誤放。本報告的處理是把尺一併進尺二那張 blocking 票,實質上等於採納了 judge
的結論(它會跟著 blocking 一起修),但沒有另外把「誤紅 = known issue」這條專案慣例翻掉。
要正式翻掉那條慣例,在 demo 時說一聲。

**oracle 獨立性**:這串 sweep 全部 import 受測物自己的 `stream_encoding_issues`,它綠只證明
它同意自己,連 fixture 的「期望」欄都是人手標的。本輪補了第二把尺 `scripts/qa/87-oracle.py`
——**一行守門規則都不讀**,把同一份 fixture 真的 `python` 跑起來,把 `sys.stdout.buffer.write`
換成會記帳的 proxy,看那一行到底有沒有執行(STEP 10)。84 格 fixture,期望欄與實跑**全對得上**。
這把尺在寫的過程中就砍掉了**六格假 finding**:`asyncio.gather(adump())` / `create_task` /
`ensure_future` / `run_until_complete` 直接寫在 top-level,根本沒有 event loop、coroutine
一行沒跑,守門判 RED 是對的 —— 只憑守門的表看不出這件事。

**本輪順手修掉的 QA artifact 缺陷(不是產品 bug)**:

- `--shadow-scope`(#89 那張票)那格 `import json as list`:`list(g)` 會炸,generator 沒被
  抽乾、bypass 那行根本沒跑到,ground truth 是 RED 而票上標 GREEN —— 實跑 oracle 抓到的
  唯一一格對不上就是它。已換成 `from collections import deque as list`(一樣是 import
  alias 撞名,但真的會抽乾 iterable),這格想量的東西原樣保留,#89 的 11/9 不變。
- `--driven-attr` 前八格的 receiver 收到 coroutine 會直接拋例外,ground truth 的 RED 是
  「炸了」換來的,不是「那行在死碼位置」換來的(judge 指出的 oracle 弱點)。已補兩格
  `MagicMock()` 的 receiver —— 吃下引數、什麼都不做、也不炸,RED 純粹來自 body 沒跑。
  母體 10 → 12,誤放 8 → 10。
- sweep 的 baseline flag 不認得就**靜默跑現況**:`--prev87` 一開始沒登記在
  `86-async-sweep.py` 的 `BASELINES`,第一次跑出「修前 0 誤放」的假對照,差點把 STEP 3 判成
  「這顆 commit 什麼都沒收」。本輪已補登記,但這個 fallthrough 是 QA 工具的坑,下一輪誰再加
  baseline 都會踩(沒開票,列在這裡)。

## 獨立 judge

乾淨 subagent,只餵 #60 AC1 的驗收原句 + 五張 sweep 表 + 實跑 oracle 表,沒餵實作、沒餵
本 session 的判斷、沒餵專案的 severity 慣例。以下原文引用。

---

### 逐半判定

**後半「跑不到 → 不得豁免」→ fail**

> 表 A 的 async 面:5 格死碼(綁著沒 await、裸 coroutine、進容器、交給不 await 的 def、
> 寫在沒人 await 的 async def body)全部收成 RED,這一面 pass。但表 D 是同一條後半的正面
> 違反:**8 格死碼拿到 GREEN**。只要檔案裡出現任意物件的 `.run(...)` / `.gather(...)` /
> `.wait_for(...)` / `.create_task(...)` / `.ensure_future(...)` /
> `.run_until_complete(...)` / `.wait(...)`,守門就認定 coroutine 被驅動了,body 裡的死碼
> 直接豁免。連 `subprocess.run(coroutine)` 都放行。
>
> 也就是說:#87 修掉了「用 `async def` 包死碼」這個入口,但「用一個叫 `.run` 的 method
> 當開關」這個入口是全開的。**後半整條沒過。**

**前半「會跑到 → 不得誤紅」→ fail**

> 表 C:10 格誤紅。表 E:4 格誤紅。合計 14 格「那行真的會執行」卻被判 RED。前半沒過,
> 而且不是邊角:C 裡有 6 格是**最主流的寫法**(`asyncio.run(adump())` 真的在跑,只因為
> 模組裡剛好有個 `def run`)。

**works-but-wrong**

> 表 C 那個機制要單獨標成 **works-but-wrong(算 fail)**:它確實抓到了 C 第 12 格「模組
> 自己 `def run(x): return x` 真的沒驅動」→ RED,功能會動。但它靠的是「檔案裡有沒有出現
> 這個名字」,不是驗收原句要的位置/語意。證據就在 C 的第 7–10 格:參數叫 `run`、local 叫
> `wait_for`、comprehension target 叫 `gather`、`import json as run` —— 這些 binding 根本
> 不在 module scope、也擋不到 `asyncio.run` 這個 attribute access,卻一律被當成遮蔽。
> **這就是驗收原句點名要淘汰的「全檔 substring」,只是換了個名字叫 shadow 檢查。**

### 嚴重度

> **嚴重度:D > C > E。誤放比誤紅嚴重。** 理由三條:
>
> 1. **誤放是靜音的,誤紅是有聲的。** 誤紅會被人看到、會被抱怨、會被開票;誤放不會有任何
>    人來跟你講「欸守門剛剛放過一支會亂碼的 script」。壞掉的守門看起來跟正常的守門一模一樣。
> 2. **誤放讓守門在它唯一該出手的地方價值歸零。** 這條規則存在的理由就是攔「拿死碼騙豁免」;
>    D 證明只要寫一行帶 `.run(` 的東西就能繞過,那這條規則對任何刻意繞過的人來說等於不存在
>    —— 包括不是刻意、只是剛好 import 了 `subprocess` 的人。
> 3. **誤紅的真正危險是它會退化成誤放。** C 那 10 格誤紅裡有 6 格是主流寫法,這種誤報率
>    撐不過幾天就會有人把整條 check 停用或加白名單 —— 到那時它就是全面誤放。所以 C 不能
>    因為「安全側」就緩修。
>
> 但 C 和 D 其實**是同一個 root cause 的兩面**,不要當兩張票修:「怎麼認定一個 call 是
> event loop 驅動」目前只看名字,不看這個名字綁到什麼。名字被別人佔走 → 整個放棄(C,
> 誤紅);名字對上 → 無條件相信(D,誤放)。修的時候一起修,分開修一定會左右互搏。

### 這次到底有沒有真的收掉東西(表 B)

> **這次是真的收掉了東西,不是換理由過關。** […] **關鍵是對照組沒有陪葬**:B 裡 7 格對照
> (3 格 RED + 4 格 GREEN)修前就全對,修後表 A 同樣全對。[…] 如果這次是靠「把 async
> 相關的一律判 RED」蒙混,那 4 格會翻成 RED。它們沒翻。所以修法是有分辨力的,不是一刀切。
> […] 這一點 #87 做得對,值得記一筆。它壞在別的地方,不壞在這裡。

### 期望欄與 ground truth 對不上的格子

> **點名一格:`SHADOW_SCOPE / import alias 叫 list \`import json as list\``,fixture
> 期望 GREEN,真跑 RED(跑爆)。** 這格是期望標錯,不是 oracle 錯 […] **它屬於 #86 那一輪
> 的 shadow-scope 母體。也就是說 #86 宣稱的數字裡,至少有一格是拿一個錯的期望值算出來的。**
>
> […] C 第 10 格的 `import json as run` 期望 GREEN、真跑也 GREEN,是對的 —— 因為那格的
> 驅動走 `asyncio.run(...)`,沒被 alias 撞到。跟 `import json as list` 結構長得幾乎一樣、
> ground truth 卻相反。**教訓:alias shadow 這類 fixture 的期望值必須逐格拿 oracle 決定,
> 不能套規則推。**
>
> C/D/E 三組的「期望」欄本身沒有問題 —— F 對這三段全部 ok […] 所以 C/D/E 的不合是**守門
> 判錯,不是期望標錯**,沒有推翻的空間。
>
> **順帶一個 oracle 方法論的弱點(不改變 D 的結論):** F 裡 DRIVEN_ATTR 那 8 格,ground
> truth RED 全部標著「跑爆」[…] 建議補幾個**不跑爆**的 attr fixture,讓 RED 是從「沒執行到」
> 得來的,不是從「炸了」得來的。

### 一句話判定

> **這一輪判 fail。** coroutine 那一面(表 A / B)做得對且證明有效,但驗收原句的兩半都沒過:
> 後半被 D 的 8 格誤放打穿,前半被 C 的 10 格 + E 的 4 格誤紅打穿。**最該先修的是 D**,
> 而且要**跟 C 綁在同一票修**。[…] E 排第二輪。另外**不管修不修 C/D/E,`import json as
> list` 那格的期望值要先改掉**。

---

**judge 的兩條方法建議本輪當場採納了**:那格跑爆的 fixture 已換成
`from collections import deque as list`(#89 的 11/9 不變);`--driven-attr` 補了兩格
`MagicMock()` receiver 的 fixture,RED 純粹來自「body 沒跑」而不是「炸了」,母體 10 → 12、
誤放 8 → 10。上面 judge 引文裡的 8 / 10 是它看到的那一版數字。

## 交棒

**blocking(修完才能 demo)**

- **#91** — coroutine 算不算被 event loop 驅動只看名字:任意物件的 `.run(coroutine)` 就是
  開關(`--driven-attr` 12/10,誤放);名字被任何 scope 綁走就整條放棄(`--driven-shadow`
  12/10,誤紅,本輪引入)。兩面同一個 root cause,一張票一起修。
- **#93** — #87 的三個判準沒有 self-check fixture 釘著,knob 改壞 `--self-check` 照樣綠。

**known issue(帶著 demo,處置由 client 在 demo 收尾整批確認)**

- **#92** — coroutine 的驅動位置只認字面形狀:綁到名字再驅動 / `gather(*cs)` /
  async comprehension 裡的 await 四格誤紅(`--await-shapes` 8/4,本輪引入)。

**未涵蓋範圍**

- 這張票是純 CLI / 靜態分析切片,沒有 UI,沒有 Playwright walkthrough,也沒有 Tauri 原生殼
  的部分要 client 親手操作。demo 素材就是下面那份 xtrace 實錄。
- `--async-defer` 母體只到 12 格,只列 `asyncio` 這一種 event loop —— `trio` / `anyio` /
  `uvloop` 的驅動入口沒進母體(名字碰巧撞上 `run` 的算是誤打誤撞收到)。
- `87-oracle.py` 只掃 tail 是「裸中文 print、沒 pin」的那幾組(async / generator / deferred
  家族,84 格);pin 位置、提到 vs 用到那幾組的期望值不是由 bypass 有沒有跑決定的,不適用
  這把尺,那些組的期望欄仍然是人手標的。

**demo 實錄清單**(每條驗收項對一段,都在下面的終端實錄裡)

| 驗收項 / 面 | 段落 |
| --- | --- |
| AC1 後半「跑不到 → 不得豁免」(#87 宣稱修好的那面) | STEP 2 + STEP 3 |
| 這顆 commit 的判準有沒有被釘住 | STEP 4(三個 knob 都沒咬住)+ STEP 5(#86 的十四個都咬住) |
| 既有天花板一格沒動 | STEP 7 + STEP 8 + STEP 9(222 格全域逐格) |
| 判準 oracle 的獨立性 | STEP 10(不讀守門規則,fixture 真的跑起來) |
| AC1 前半「會跑到 → 不得誤紅」 | STEP 11(#91 誤紅那半)+ STEP 13(#92) |
| 死碼還能不能拿到豁免 | STEP 12(#91 誤放那半)+ STEP 14(收 attribute 那半的代價) |

**一鍵重開**(client-demo 直接抄)

```bash
bash scripts/qa/87-walkthrough.sh "$(mktemp -d)/qa87"
```

**下一步**:`/build #91`(Codex: `$build #91`)。#91 修完重跑 `/qa #87`。


## 終端實錄

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
+ echo '==== STEP 2  #87 的重現 scenario 原樣重跑(票上的母體 12,修前 5 誤放)===='
==== STEP 2  #87 的重現 scenario 原樣重跑(票上的母體 12,修前 5 誤放)====
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
+ echo '==== STEP 3  對照組:#87 修之前(55fc8eb)同一組 12 條裡 5 條誤放 ===='
==== STEP 3  對照組:#87 修之前(55fc8eb)同一組 12 條裡 5 條誤放 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' '/d/Self Project/Skills' --async-defer --prev87
coroutine 綁著沒 await `c = adump()`                        期望 RED    實際 GREEN  MISMATCH
裸 coroutine 在 live 語句 `adump()`                          期望 RED    實際 GREEN  MISMATCH
coroutine 進容器沒 await `xs = [adump()]`                    期望 RED    實際 GREEN  MISMATCH
coroutine 交給不 await 的 def `keep(adump())`                期望 RED    實際 GREEN  MISMATCH
bypass 直接寫在呼叫了但沒 await 的 async def body 裡                期望 RED    實際 GREEN  MISMATCH
對照:async def 綁著沒呼叫(現在就是 RED,不得放掉)                        期望 RED    實際 RED    ok
對照:async generator 呼叫了沒 iterate `agen()`(現在就是 RED,不得放掉)  期望 RED    實際 RED    ok
對照:`await adump()` 只在沒人跑的 outer 裡(現在就是 RED,不得放掉)         期望 RED    實際 RED    ok
對照:`asyncio.run(adump())` 真的跑(不得誤紅)                      期望 GREEN  實際 GREEN  ok
對照:`await adump()` 在被 `asyncio.run` 的 outer 裡(不得誤紅)      期望 GREEN  實際 GREEN  ok
對照:bypass 寫在真的被 run 的 coroutine body(不得誤紅)               期望 GREEN  實際 GREEN  ok
對照:`async for _ in agen()` 真的 iterate(不得誤紅)              期望 GREEN  實際 GREEN  ok

母體 12,不合 5
+ echo 'exit 1  <- 非 0 是要的:對照組該紅'
exit 1  <- 非 0 是要的:對照組該紅
+ set -e
+ echo '==== STEP 4  c51ba98 自己的三個 knob 改壞 -> self-check 該轉紅(本輪 finding:三個都不紅)===='
==== STEP 4  c51ba98 自己的三個 knob 改壞 -> self-check 該轉紅(本輪 finding:三個都不紅)====
+ for M in gens_no_async consumes_no_await consumes_no_driven
+ echo '---- 4.gens_no_async'
---- 4.gens_no_async
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo gens_no_async
mutation 已套用: gens_no_async
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -3
OK validate self-check green
+ echo 'exit 0  <- 0 = 這條判準沒有證據住在預設會跑的地方'
exit 0  <- 0 = 這條判準沒有證據住在預設會跑的地方
+ set -e
+ echo '---- 同一個 mutation 下,#87 的母體 12 掉幾格:'
---- 同一個 mutation 下,#87 的母體 12 掉幾格:
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' /tmp/tmp.kFBACEcXPD/qa87/repo --async-defer
+ tail -2

母體 12,不合 5
+ set -e
+ for M in gens_no_async consumes_no_await consumes_no_driven
+ echo '---- 4.consumes_no_await'
---- 4.consumes_no_await
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo consumes_no_await
mutation 已套用: consumes_no_await
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -3
OK validate self-check green
+ echo 'exit 0  <- 0 = 這條判準沒有證據住在預設會跑的地方'
exit 0  <- 0 = 這條判準沒有證據住在預設會跑的地方
+ set -e
+ echo '---- 同一個 mutation 下,#87 的母體 12 掉幾格:'
---- 同一個 mutation 下,#87 的母體 12 掉幾格:
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' /tmp/tmp.kFBACEcXPD/qa87/repo --async-defer
+ tail -2

母體 12,不合 1
+ set -e
+ for M in gens_no_async consumes_no_await consumes_no_driven
+ echo '---- 4.consumes_no_driven'
---- 4.consumes_no_driven
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo consumes_no_driven
mutation 已套用: consumes_no_driven
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -3
OK validate self-check green
+ echo 'exit 0  <- 0 = 這條判準沒有證據住在預設會跑的地方'
exit 0  <- 0 = 這條判準沒有證據住在預設會跑的地方
+ set -e
+ echo '---- 同一個 mutation 下,#87 的母體 12 掉幾格:'
---- 同一個 mutation 下,#87 的母體 12 掉幾格:
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' /tmp/tmp.kFBACEcXPD/qa87/repo --async-defer
+ tail -2

母體 12,不合 4
+ set -e
+ echo '==== STEP 5  de68088 的十四個 knob(兩個錨重新對齊)逐一改壞 -> self-check 要轉紅 ===='
==== STEP 5  de68088 的十四個 knob(兩個錨重新對齊)逐一改壞 -> self-check 要轉紅 ====
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.names_in_no_gen_stop'
---- 5.names_in_no_gen_stop
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo names_in_no_gen_stop
mutation 已套用: names_in_no_gen_stop
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.kFBACEcXPD\qa87\repo\scripts\validate.py", line 1581, in self_check
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: unconsumed generator: handed to a def that does not consume it
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.names_in_no_first_iter'
---- 5.names_in_no_first_iter
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo names_in_no_first_iter
mutation 已套用: names_in_no_first_iter
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6

f = lambda: sum(x for x in dump())
if __name__ == "__main__":
    f()
    print('要開')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.nodes_in_no_gen_stop'
---- 5.nodes_in_no_gen_stop
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo nodes_in_no_gen_stop
mutation 已套用: nodes_in_no_gen_stop
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.kFBACEcXPD\qa87\repo\scripts\validate.py", line 1581, in self_check
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: unconsumed generator: g = (dump() for _ in [1])
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.nodes_in_no_first_iter'
---- 5.nodes_in_no_first_iter
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo nodes_in_no_first_iter
mutation 已套用: nodes_in_no_first_iter
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6


g = (x for x in dump())
if __name__ == "__main__":
    print('要開')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.consumes_no_builtins'
---- 5.consumes_no_builtins
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo consumes_no_builtins
mutation 已套用: consumes_no_builtins
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6


if __name__ == "__main__":
    sum(1 for _ in (dump() for _ in [1]))
    print('要開')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.consumes_no_for'
---- 5.consumes_no_for
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo consumes_no_for
mutation 已套用: consumes_no_for
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6

if __name__ == "__main__":
    for _ in gen():
        pass
    print('要開')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.consumes_no_nested_gen'
---- 5.consumes_no_nested_gen
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo consumes_no_nested_gen
mutation 已套用: consumes_no_nested_gen
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6


if __name__ == "__main__":
    sum(1 for _ in (dump() for _ in [1]))
    print('要開')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.consumes_no_comp'
---- 5.consumes_no_comp
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo consumes_no_comp
mutation 已套用: consumes_no_comp
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6


if __name__ == "__main__":
    [y for y in (dump() for _ in [1])]
    print('要開')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.consumes_no_shadow'
---- 5.consumes_no_shadow
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo consumes_no_shadow
mutation 已套用: consumes_no_shadow
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.kFBACEcXPD\qa87\repo\scripts\validate.py", line 1584, in self_check
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: unconsumed generator: a def shadowing a consumer does not consume
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.gens_not_subtracted'
---- 5.gens_not_subtracted
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo gens_not_subtracted
mutation 已套用: gens_not_subtracted
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.kFBACEcXPD\qa87\repo\scripts\validate.py", line 1584, in self_check
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: unconsumed generator: generator def called, never iterated
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.no_eaten_calls'
---- 5.no_eaten_calls
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo no_eaten_calls
mutation 已套用: no_eaten_calls
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6

if __name__ == "__main__":
    for _ in gen():
        pass
    print('要開')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.no_eaten_via_name'
---- 5.no_eaten_via_name
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo no_eaten_via_name
mutation 已套用: no_eaten_via_name
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6

g = (dump() for _ in [1])
if __name__ == "__main__":
    list(g)
    print('要開')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.through_no_gens'
---- 5.through_no_gens
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo through_no_gens
mutation 已套用: through_no_gens
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6
    assert stream_encoding_issues(repo) == [], alive
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: if __name__ == "__main__":
    list(sys.stdout.buffer.write(b'x') for _ in [1])
    print('要開')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 5.no_gen_fixpoint'
---- 5.no_gen_fixpoint
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo no_gen_fixpoint
mutation 已套用: no_gen_fixpoint
+ set +e
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
+ tail -6


if __name__ == "__main__":
    sum(1 for _ in (dump() for _ in [1]))
    print('要開')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ echo '==== STEP 6  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===='
==== STEP 6  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)====
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py --self-check
OK validate self-check green
+ echo '==== STEP 7  票上「不得放掉的天花板」逐條複驗 ===='
==== STEP 7  票上「不得放掉的天花板」逐條複驗 ====
+ echo '---- 7a  --generator(#86,12/0)'
---- 7a  --generator(#86,12/0)
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
+ echo '---- 7b  --deferred(#84,11/1,第七格是宣告過的天花板)'
---- 7b  --deferred(#84,11/1,第七格是宣告過的天花板)
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
+ echo '---- 7c  --lambda-scope(#83,9/0)'
---- 7c  --lambda-scope(#83,9/0)
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
+ echo '---- 7d  --own-names(#81,13/0)'
---- 7d  --own-names(#81,13/0)
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
+ echo '---- 7e  --return-carry(#79,6/0)'
---- 7e  --return-carry(#79,6/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --return-carry
死碼 bypass + `def get(): return dump`,`get()` 結果直接丟掉  期望 RED    實際 RED    ok
同上,回傳值存進變數但從未呼叫(`x = get()`)                         期望 RED    實際 RED    ok
get() 回傳的是自己的區域變數,只是剛好撞名死碼 def                       期望 RED    實際 RED    ok
對照:回傳值真的被呼叫 `get()()`(#75 立的天花板,不得誤紅)                期望 GREEN  實際 GREEN  ok
對照:回傳值存進變數後才呼叫 `f = get(); f()`(#79 的天花板,不得誤紅)       期望 GREEN  實際 GREEN  ok
對照:`get` 自己也沒被呼叫(死碼,必須維持 RED)                        期望 RED    實際 RED    ok

母體 6,不合 0
+ echo '---- 7f  --callgraph(4/0)'
---- 7f  --callgraph(4/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --callgraph
bypass 在 handler dict 裡被呼叫的 function(docstring 說仍算 live)  期望 GREEN  實際 GREEN  ok
bypass 在 alias 呼叫的 function(docstring 說仍算 live)           期望 GREEN  實際 GREEN  ok
bypass 當 callback 傳進去被呼叫(docstring 說仍算 live)              期望 GREEN  實際 GREEN  ok
bypass 在 class method,__main__ 直接呼叫(對照:.attr 名字對得上)       期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '---- 7g  --live-overapprox(5/0)'
---- 7g  --live-overapprox(5/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --live-overapprox
死碼裡的 bypass + live 區提到名字(不是呼叫)   期望 RED    實際 RED    ok
死碼裡的 bypass + 剛好撞名的區域變數          期望 RED    實際 RED    ok
死碼裡的 bypass + 無關物件的同名 attribute  期望 RED    實際 RED    ok
對照:死碼裡的 bypass,名字沒被提到(#70 的天花板)  期望 RED    實際 RED    ok
對照:bypass 在真的被呼叫的 main()(不得誤紅)   期望 GREEN  實際 GREEN  ok

母體 5,不合 0
+ echo '---- 7h  --bypass-position(6/0)'
---- 7h  --bypass-position(6/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --bypass-position
bypass 在從未被呼叫的 function 內                                  期望 RED    實際 RED    ok
bypass 在 `if False:` 死碼裡                                   期望 RED    實際 RED    ok
bypass 只出現在跑不到的 except 分支                                  期望 RED    實際 RED    ok
bypass 在 `raise SystemExit` 之後的死碼                          期望 RED    實際 RED    ok
bypass 真的在 __main__ 裡用(不得誤紅)                               期望 GREEN  實際 GREEN  ok
bypass 在 main(),__main__ 呼叫它(triage-to-maintain 的形狀,不得誤紅)  期望 GREEN  實際 GREEN  ok

母體 6,不合 0
+ echo '---- 7i  --mention(13/0)'
---- 7i  --mention(13/0)
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
+ echo '---- 7j  --positional(#58 原病,4/0)'
---- 7j  --positional(#58 原病,4/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --positional
pin 在 main(),__main__ 只呼叫它      期望 RED    實際 RED    ok
pin 在 __main__ 之前的 top-level    期望 RED    實際 RED    ok
pin 真的在 __main__ block 裡        期望 GREEN  實際 GREEN  ok
pin 在 __main__ block 裡的 try 底下  期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '---- 7k  #73 的三把尺(6/0 ×3)'
---- 7k  #73 的三把尺(6/0 ×3)
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
+ echo '---- 7l  #75 的 --bind-quiet(11/0)'
---- 7l  #75 的 --bind-quiet(11/0)
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
+ echo '==== STEP 8  已開票的天花板複驗(known issues,期望維持不變)===='
==== STEP 8  已開票的天花板複驗(known issues,期望維持不變)====
+ set +e
+ echo '---- 8a  --pin-position(#72,6/4)'
---- 8a  --pin-position(#72,6/4)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --pin-position
pin 在 __main__ 內的 `if False:` 死碼裡          期望 RED    實際 GREEN  MISMATCH
pin 在 __main__ 內 `raise SystemExit` 之後的死碼  期望 RED    實際 GREEN  MISMATCH
pin 在 __main__ 內定義但沒人呼叫的 nested def        期望 RED    實際 GREEN  MISMATCH
pin 只出現在跑不到的 except 分支                     期望 RED    實際 GREEN  MISMATCH
pin 真的在 __main__ block 裡(不得誤紅)             期望 GREEN  實際 GREEN  ok
pin 在 block 內的 try body 裡(不得誤紅)            期望 GREEN  實際 GREEN  ok

母體 6,不合 4
+ echo '---- 8b  --print-detect(#74,7/5)'
---- 8b  --print-detect(#74,7/5)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --print-detect
print 用 alias 呼叫(p = print; p(中文))                 期望 RED    實際 GREEN  MISMATCH
print 走 builtins(builtins.print(中文))               期望 RED    實際 GREEN  MISMATCH
print 當 callback 傳進去(run(print))                   期望 RED    實際 GREEN  MISMATCH
print 放在 handler dict 裡(H = {p: print}; H[p](中文))  期望 RED    實際 GREEN  MISMATCH
sys.stdout.write(中文)(build 已宣告的天花板)                期望 RED    實際 GREEN  MISMATCH
對照:真的裸 print(,沒 pin(不得漏放)                          期望 RED    實際 RED    ok
對照:真的完全不印 console(不得誤紅)                            期望 GREEN  實際 GREEN  ok

母體 7,不合 5
+ echo '---- 8c  --skips(#66,3/1)'
---- 8c  --skips(#66,3/1)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --skips
__main__ 縮排在 try 底下 -> 找不到 top-level If,整檔跳過           期望 RED    實際 RED    ok
__main__ 縮排在 if True 底下 -> 同上                          期望 RED    實際 RED    ok
檔案 parse 不過(SyntaxError)-> 整檔跳過(build 已在 code 裡註明的取捨)  期望 RED    實際 GREEN  MISMATCH

母體 3,不合 1
+ echo '---- 8d  --name-collision(#80,4/3)'
---- 8d  --name-collision(#80,4/3)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --name-collision
死碼 bypass 在沒被實例化的 class method,module 同名 def 被呼叫  期望 RED    實際 GREEN  MISMATCH
死碼 bypass 在後面重新定義的同名 def,被呼叫的是前面那個                期望 RED    實際 GREEN  MISMATCH
對照:死碼 bypass 的 def 沒有同名雙胞胎(#70 的天花板)              期望 RED    實際 RED    ok
對照:同名 def 但被呼叫的就是帶 bypass 的那個(不得誤紅)               期望 GREEN  實際 RED    MISMATCH

母體 4,不合 3
+ echo '---- 8e  --arg-widen(7/5)'
---- 8e  --arg-widen(7/5)
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --arg-widen
對照:`run(dump)`,run 真的呼叫它(#71 的 callback,不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:名字完全沒被提到(#70 的天花板)                          期望 RED    實際 RED    ok
`print(dump)` — 印出 function 物件,沒有呼叫它           期望 RED    實際 GREEN  MISMATCH
`x = str(dump)` — 引數,但 str 不會呼叫它               期望 RED    實際 GREEN  MISMATCH
`x = len([dump])` — 名字包在 list 裡當引數             期望 RED    實際 GREEN  MISMATCH
`print(f"{dump}")` — 名字在 f-string 的引數裡         期望 RED    實際 GREEN  MISMATCH
`isinstance(dump, object)` — 關鍵字/位置引數都一樣       期望 RED    實際 GREEN  MISMATCH

母體 7,不合 5
+ echo '---- 8f  #75 的另兩把尺(#77 12/6 / #78 8/5)'
---- 8f  #75 的另兩把尺(#77 12/6 / #78 8/5)
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
+ echo '---- 8g  #79 的 --result-called(#82,14/3)'
---- 8g  #79 的 --result-called(#82,14/3)
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
+ echo '---- 8h  #86 的 --shadow-scope(11/9)與 --attr-consumer(6/3)'
---- 8h  #86 的 --shadow-scope(11/9)與 --attr-consumer(6/3)
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
+ set -e
+ echo '==== STEP 9  全域修前對照:222 格 fixture 逐格比 55fc8eb vs c51ba98 ===='
==== STEP 9  全域修前對照:222 格 fixture 逐格比 55fc8eb vs c51ba98 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/87-prevdiff.py' '/d/Self Project/Skills'
ASYNC_DEFER / coroutine 綁著沒 await `c = adump()`                                           期望 RED   修前 GREEN 修後 RED    修好
ASYNC_DEFER / 裸 coroutine 在 live 語句 `adump()`                                             期望 RED   修前 GREEN 修後 RED    修好
ASYNC_DEFER / coroutine 進容器沒 await `xs = [adump()]`                                       期望 RED   修前 GREEN 修後 RED    修好
ASYNC_DEFER / coroutine 交給不 await 的 def `keep(adump())`                                   期望 RED   修前 GREEN 修後 RED    修好
ASYNC_DEFER / bypass 直接寫在呼叫了但沒 await 的 async def body 裡                                   期望 RED   修前 GREEN 修後 RED    修好
AWAIT_SHAPES / 綁到名字再 await `c = adump()` + `await c`                                      期望 GREEN 修前 GREEN 修後 RED    本輪引入
AWAIT_SHAPES / 綁到名字再交給 event loop `c = adump()` + `asyncio.run(c)`                        期望 GREEN 修前 GREEN 修後 RED    本輪引入
AWAIT_SHAPES / `asyncio.gather(*cs)` 的 Starred 展開                                         期望 GREEN 修前 GREEN 修後 RED    本輪引入
AWAIT_SHAPES / async comprehension 裡的 await `[await c for c in [adump()]]`                期望 GREEN 修前 GREEN 修後 RED    本輪引入
AWAIT_SHAPES / 對照:`c = adump()` 綁著沒人驅動(#87 母體第一格,不得放掉)                                    期望 RED   修前 GREEN 修後 RED    修好
DRIVEN_SHADOW / 模組自己 `def run(x)`,`asyncio.run(adump())` 真的在跑                             期望 GREEN 修前 GREEN 修後 RED    本輪引入
DRIVEN_SHADOW / 模組自己 `def gather(x)`,`await asyncio.gather(adump())` 真的在跑                 期望 GREEN 修前 GREEN 修後 RED    本輪引入
DRIVEN_SHADOW / 模組自己 `def wait_for(x)`,`await asyncio.wait_for(adump(), 5)` 真的在跑          期望 GREEN 修前 GREEN 修後 RED    本輪引入
DRIVEN_SHADOW / 模組自己 `def create_task(x)`,`asyncio.create_task(adump())` 真的在跑             期望 GREEN 修前 GREEN 修後 RED    本輪引入
DRIVEN_SHADOW / 模組自己 `def ensure_future(x)`,`await asyncio.ensure_future(adump())` 真的在跑   期望 GREEN 修前 GREEN 修後 RED    本輪引入
DRIVEN_SHADOW / 模組自己 `def run_until_complete(x)`,`loop.run_until_complete(adump())` 真的在跑  期望 GREEN 修前 GREEN 修後 RED    本輪引入
DRIVEN_SHADOW / 別的 def 的參數叫 run `def u(run)`                                              期望 GREEN 修前 GREEN 修後 RED    本輪引入
DRIVEN_SHADOW / 別的 def 裡的 local 叫 wait_for `def u(): wait_for = 1`                        期望 GREEN 修前 GREEN 修後 RED    本輪引入
DRIVEN_SHADOW / comprehension target 叫 gather `[gather for gather in []]`                 期望 GREEN 修前 GREEN 修後 RED    本輪引入
DRIVEN_SHADOW / `import json as run` 撞名                                                   期望 GREEN 修前 GREEN 修後 RED    本輪引入
DRIVEN_SHADOW / 對照:自己的 `def run(x): return x` 真的沒驅動(shadowed 這半的價值,不得放掉)                  期望 RED   修前 GREEN 修後 RED    修好

母體 222,翻面 21,本輪引入的誤判 14
+ echo 'exit 1  <- 非 0 是本輪引入的誤判'
exit 1  <- 非 0 是本輪引入的誤判
+ set -e
+ echo '==== STEP 10  獨立 oracle:不讀 validate.py 一行,把 fixture 真的跑起來看 bypass 有沒有執行 ===='
==== STEP 10  獨立 oracle:不讀 validate.py 一行,把 fixture 真的跑起來看 bypass 有沒有執行 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/87-oracle.py' '/d/Self Project/Skills'
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

母體 84,fixture 期望與實跑不合 0
+ echo 'exit 0  <- 非 0 = 有 fixture 的期望值跟實跑對不上'
exit 0  <- 非 0 = 有 fixture 的期望值跟實跑對不上
+ set -e
+ echo '==== STEP 11  同型全掃 尺一(誤紅):DRIVEN_BY 的名字被 shadowed 劃掉 ===='
==== STEP 11  同型全掃 尺一(誤紅):DRIVEN_BY 的名字被 shadowed 劃掉 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py' '/d/Self Project/Skills' --driven-shadow
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
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#87 修之前(55fc8eb)'
---- 對照組:#87 修之前(55fc8eb)
+ python '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py' '/d/Self Project/Skills' --driven-shadow --prev87
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
對照:自己的 `def run(x): return x` 真的沒驅動(shadowed 這半的價值,不得放掉)                  期望 RED    實際 GREEN  MISMATCH

母體 12,不合 1
+ set -e
+ echo '==== STEP 12  同型全掃 尺二(誤放):DRIVEN_BY 的 method call 只認 attribute 名字 ===='
==== STEP 12  同型全掃 尺二(誤放):DRIVEN_BY 的 method call 只認 attribute 名字 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py' '/d/Self Project/Skills' --driven-attr
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
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#87 修之前(55fc8eb)—— 同樣 10 格,病因換人,不是本輪引入'
---- 對照組:#87 修之前(55fc8eb)—— 同樣 10 格,病因換人,不是本輪引入
+ python '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py' '/d/Self Project/Skills' --driven-attr --prev87
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
+ set -e
+ echo '==== STEP 13  同型全掃 尺三(誤紅):真的被驅動、但驅動位置不在名單上 ===='
==== STEP 13  同型全掃 尺三(誤紅):真的被驅動、但驅動位置不在名單上 ====
+ set +e
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
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#87 修之前(55fc8eb)'
---- 對照組:#87 修之前(55fc8eb)
+ python '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py' '/d/Self Project/Skills' --await-shapes --prev87
綁到名字再 await `c = adump()` + `await c`                        期望 GREEN  實際 GREEN  ok
綁到名字再交給 event loop `c = adump()` + `asyncio.run(c)`          期望 GREEN  實際 GREEN  ok
`asyncio.gather(*cs)` 的 Starred 展開                           期望 GREEN  實際 GREEN  ok
async comprehension 裡的 await `[await c for c in [adump()]]`  期望 GREEN  實際 GREEN  ok
對照:`asyncio.run(adump())` 一步到位(不得誤紅)                         期望 GREEN  實際 GREEN  ok
對照:`asyncio.run(main=adump())` 走 keyword(不得誤紅)               期望 GREEN  實際 GREEN  ok
對照:兩層 await `outer -> mid -> adump`(不得誤紅)                    期望 GREEN  實際 GREEN  ok
對照:`c = adump()` 綁著沒人驅動(#87 母體第一格,不得放掉)                      期望 RED    實際 GREEN  MISMATCH

母體 8,不合 1
+ set -e
+ echo '==== STEP 14  尺二的證據:把 DRIVEN_BY 收成只認 Name.id,那十格翻回 RED、母體 12 掉四格 ===='
==== STEP 14  尺二的證據:把 DRIVEN_BY 收成只認 Name.id,那十格翻回 RED、母體 12 掉四格 ====
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/87-mutate.py' /tmp/tmp.kFBACEcXPD/qa87/repo driven_attr_id_only
mutation 已套用: driven_attr_id_only
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/87-drive-sweep.py' /tmp/tmp.kFBACEcXPD/qa87/repo --driven-attr
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
對照:`loop.run_until_complete(adump())` 真的驅動(attribute 判讀的理由,不得誤紅)  期望 GREEN  實際 RED    MISMATCH
對照:`asyncio.Runner().run(adump())` 真的驅動(不得誤紅)                     期望 GREEN  實際 RED    MISMATCH

母體 12,不合 2
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' /tmp/tmp.kFBACEcXPD/qa87/repo --async-defer
coroutine 綁著沒 await `c = adump()`                        期望 RED    實際 RED    ok
裸 coroutine 在 live 語句 `adump()`                          期望 RED    實際 RED    ok
coroutine 進容器沒 await `xs = [adump()]`                    期望 RED    實際 RED    ok
coroutine 交給不 await 的 def `keep(adump())`                期望 RED    實際 RED    ok
bypass 直接寫在呼叫了但沒 await 的 async def body 裡                期望 RED    實際 RED    ok
對照:async def 綁著沒呼叫(現在就是 RED,不得放掉)                        期望 RED    實際 RED    ok
對照:async generator 呼叫了沒 iterate `agen()`(現在就是 RED,不得放掉)  期望 RED    實際 RED    ok
對照:`await adump()` 只在沒人跑的 outer 裡(現在就是 RED,不得放掉)         期望 RED    實際 RED    ok
對照:`asyncio.run(adump())` 真的跑(不得誤紅)                      期望 GREEN  實際 RED    MISMATCH
對照:`await adump()` 在被 `asyncio.run` 的 outer 裡(不得誤紅)      期望 GREEN  實際 RED    MISMATCH
對照:bypass 寫在真的被 run 的 coroutine body(不得誤紅)               期望 GREEN  實際 RED    MISMATCH
對照:`async for _ in agen()` 真的 iterate(不得誤紅)              期望 GREEN  實際 RED    MISMATCH

母體 12,不合 4
+ set -e
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.kFBACEcXPD/qa87/repo/scripts/validate.py
+ echo '==== STEP 15  對照組不是模擬:--prev87 是 git show 55fc8eb:scripts/validate.py 真的 import 舊版 ===='
==== STEP 15  對照組不是模擬:--prev87 是 git show 55fc8eb:scripts/validate.py 真的 import 舊版 ====
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
+ git -C '/d/Self Project/Skills' log --oneline -1 55fc8eb
55fc8eb docs: retro #90 — 五條 amendment 落地(查證實跑、oracle 獨立、列舉窮舉、修前對照、指令即交付物)
+ echo '==== STEP 16  repo 本體沒被動過 ===='
==== STEP 16  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
 M scripts/qa/86-async-sweep.py
?? scripts/qa/87-drive-sweep.py
?? scripts/qa/87-mutate.py
?? scripts/qa/87-oracle.py
?? scripts/qa/87-prevdiff.py
?? scripts/qa/87-walkthrough.sh
```
