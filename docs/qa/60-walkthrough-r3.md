# `/qa #60` 第三輪 — walkthrough

**HEAD**: `188c7d8`(#70 的修法已在 `main`)
**上一輪**: [`docs/qa/60-walkthrough-r2.md`](60-walkthrough-r2.md)
**一鍵重開**: `bash scripts/qa/60-walkthrough.sh "$(mktemp -d)/qa60"`

---

## 白話摘要

上一輪擋住的 #70(`sys.stdout.buffer` 豁免吃整棵 AST,死碼裡塞一行就整檔豁免)修好了 ——
同一張表這輪 6 條全對,`--old` 對照組仍 4 條不合,天花板是真的抬了。

這輪換一把尺:#70 的修法把判準從「太寬」拉過來,但**拉過頭了**。AC1 原句要的是「真的在
**會執行的位置**用 `sys.stdout.buffer.write`」—— 新的 call graph 只認名字對得上的 call site,
所以把 def 當值傳遞(alias、handler dict、callback)走到的 bypass 會被當成沒人呼叫,判紅。
那三種形狀是真的會執行的。同一句 AC 括號裡的第二支路(「或檔案裡沒有裸 `print(`」)則從頭
到尾沒實作,所以一支完全不印 console 的 script 也被誤紅。兩處都往誤紅倒,都落在 AC1 原句上,
獨立 judge 判 works-but-wrong。

(a) 那半是 **regression**:`--callgraph --old` 在 `d3cc9ed^` 4 條全綠。

順帶用同一把尺量 pin 那半:#70 只把可達性裝到 bypass,pin 仍是「`__main__` block 裡字面
出現就算數」,死碼裡的 pin 照樣豁免 —— 但那不在 AC 原句上,而且 `--old` 同樣 4 條不合
(天花板沒抬也沒退),列 known issue(#72)。

---

## Regression suite

`validate.py` + 五支 self-check(`validate` / `scripts/batch` / `build-batch/batch` /
`install` / `triage-to-maintain`)全綠,沒有一條紅。見〈終端實錄〉STEP 1。

---

## 驗收原句逐條(獨立 judge 判定)

judge 是乾淨 subagent,只拿驗收原句 + 本份 transcript,沒有實作脈絡,也沒讀 repo 原始碼。

| 條目 | 判定 |
| --- | --- |
| 重現 scenario(裸 print + 註解提到 bypass → 期望紅) | **pass** — STEP 3 判紅,STEP 4 母體 13 全中 |
| AC1 豁免改成位置/語意判準 | **fail(works-but-wrong)** — 判準比原句窄,兩種誤紅 |
| AC2 self-check 補一條咬那個 mutation | **pass**(STEP 1b 反證:病一還原就轉紅) |
| AC3 `triage-to-maintain.py` L35 仍豁免 | **pass**(該檔 error 數 = 0) |
| AC4 `python scripts/validate.py` 綠 | **pass** |

AC1 的 judge 原話,兩處各自獨立打爆:

> (a) 第一支路做出來了但**誤紅**……這三種形狀就是 AC1 原句講的「真的在會執行的位置用
> `sys.stdout.buffer.write`」,卻被判紅,判準沒對上原句。
> (b) 第二支路根本沒實作。

關於 AC1 那個「或」,judge 的推理逐字:

> 「或」在這裡是 disjunction,任一成立就該豁免,不是二選一實作。所以第二支路缺席不是
> 「換個做法達成同樣效果」,而是少了一整條豁免路徑:一支完全不印 console 的 script 現在
> 會被誤紅。……反過來,如果只有 6f 這一條,還可以爭論「第二支路是 nice-to-have」;但 6i
> 那三條誤紅是打在 AC1 **第一**支路的正中心,沒有解釋空間。

第二輪的 judge 也判過同一段 STEP 6f,但那時問的是「第二支路能不能替第一支路的 fail 補分」
(答案:不能)。這輪問的是另一件事:第二支路**缺席本身**造成誤紅。兩個判定不衝突。

---

## 同型全掃

一條 fail 當尺,掃過同一份 artifact 的所有同型 case。`scripts/qa/60-mention-sweep.py`
一次跑完六張母體表:

| 表 | 旗標 | 母體 | 不合 |
| --- | --- | --- | --- |
| 提到 vs 用到(散文能出現的每個位置 × bypass/pin + 3 條真的用到) | (無) | 13 | 0 |
| 位置判準 — pin(`main()` / `__main__` 之前 / 真的在 block 裡 / block 內的 try) | `--positional` | 4 | 0 |
| 守門靜默跳過的路(`try` 底下、`if True` 底下、`SyntaxError`) | `--skips` | 3 | 1(#66) |
| 位置判準 — bypass(死碼 4 條 + 2 條合法對照) | `--bypass-position` | 6 | **0**(上輪 4) |
| **可達性判準 — pin 那半沒裝**(`if False:` / `raise` 之後 / 沒人呼叫的 nested def / 跑不到的 except + 2 條對照) | `--pin-position` | 6 | **4** |
| **call graph 的解析度**(alias / handler dict / callback + 1 條對照) | `--callgraph` | 4 | **3** |

`--old` 對照組(`d3cc9ed^`,#60 修之前那版守門)跑同一組 case:

| 表 | 現況不合 | `--old` 不合 | 結論 |
| --- | --- | --- | --- |
| `--bypass-position` | 0 | 4 | 這輪真的抬了天花板 |
| `--pin-position` | 4 | 4 | 天花板沒抬也沒退,**不是** regression |
| `--callgraph` | 3 | 0 | **是** #70 修法引入的 regression |

---

## Blocking

- **#71** — bypass 豁免的可達性判準比 AC1 原句窄,alias / handler dict / callback 三種真的會
  執行的形狀誤紅(regression);AC1 第二支路「或檔案裡沒有裸 `print(`」完全沒實作,不印
  console 的 script 也誤紅。修完重跑 `/qa #60`。

修法的難點寫在票上:修誤紅的時候不能把 #70 的天花板放掉 —— `--bypass-position` 那 4 條死碼
案例必須維持 RED。票上給了兩個方向(認得出 def 當值傳遞 / 只要 def 名字以 `Name` 出現在 live
區就算會被呼叫),沒綁死。

---

## Known issues(非 blocking,由 client 在 demo 收尾整批確認)

- **#72** — 可達性判準只裝在 bypass 那半,`__main__` 死碼裡的 pin 照樣算數(母體 6 不合 4,
  `--old` 同樣 4 不合)。
- **#66** — 檔案 `SyntaxError` → 整檔跳過。
- **#67 / #68 / #69** — `/qa #65` 那輪挖出的三條守門天花板,不在 #60 的驗收原句上。
- `install.py --self-check` 印出的 `[fixture] FAIL skills/bad: missing SKILL.md` 是 fixture 的
  預期輸出洩到 stdout,不是失敗 —— judge 主動指出這行很容易被誤讀成真的 FAIL。噪音,沒開票。
- `from sys import stdout` 偵測不到 — 改之前也一樣。
- `sys.stdout.reconfigure("utf-8")`(位置引數)判紅 — 等價安全但寫法不同,改之前同樣判紅。
- STEP 1b 那段 traceback 中文是 mojibake — traceback 走 stderr,不在 #58 立的規矩範圍內。

---

## 未涵蓋範圍

沒有 UI、沒有 Tauri 原生殼,不適用。全部是 CLI guard,終端 transcript 即實錄
(全程 bash xtrace,指令與輸出同一份,沒有事後 render)。

---

## Demo 實錄

| 驗收項 | 實錄 |
| --- | --- |
| 全部(STEP 1–7,含 1b / 6b–6j) | 本檔〈終端實錄〉 |

---

## 終端實錄

`bash scripts/qa/60-walkthrough.sh "$(mktemp -d)/qa60"` 的完整輸出,未編輯:

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
+ echo '==== STEP 1b  self-check 真的咬得到「散文當 code」:副本裡把豁免改回 substring -> self-check 轉紅 ===='
==== STEP 1b  self-check 真的咬得到「散文當 code」:副本裡把豁免改回 substring -> self-check 轉紅 ====
+ grep -n 'norm(bypass) in live' /tmp/tmp.D7fIPlZFGz/qa60/repo/scripts/validate.py
343:            if norm(bypass) in live or norm(pin) in inside:
+ sed -i 's|if norm(bypass) in live or|if bypass in py.read_text(encoding="utf-8") or|' /tmp/tmp.D7fIPlZFGz/qa60/repo/scripts/validate.py
+ grep -n 'bypass in py.read_text' /tmp/tmp.D7fIPlZFGz/qa60/repo/scripts/validate.py
343:            if bypass in py.read_text(encoding="utf-8") or norm(pin) in inside:
+ set +e
+ python /tmp/tmp.D7fIPlZFGz/qa60/repo/scripts/validate.py --self-check
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.D7fIPlZFGz\qa60\repo\scripts\validate.py", line 938, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.D7fIPlZFGz\qa60\repo\scripts\validate.py", line 894, in self_check
    assert len(stream_encoding_issues(repo)) == 1, mention
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: if __name__ == "__main__":
    print("�n�}")
    # �o�̨S�� sys.stdout.buffer

+ echo 'exit 1  <- 非 0 是要的:#60 的病一還原,self-check 就該紅'
exit 1  <- 非 0 是要的:#60 的病一還原,self-check 就該紅
+ set -e
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.D7fIPlZFGz/qa60/repo/scripts/validate.py
+ echo '==== STEP 2  副本未動過 -> 綠(證明後面判紅的是 mutation,不是副本壞了)===='
==== STEP 2  副本未動過 -> 綠(證明後面判紅的是 mutation,不是副本壞了)====
+ python /tmp/tmp.D7fIPlZFGz/qa60/repo/scripts/validate.py
OK validate green
+ echo '==== STEP 3  票上的重現 scenario 原樣重跑:裸 print + 一行「沒走 sys.stdout.buffer」註解 ===='
==== STEP 3  票上的重現 scenario 原樣重跑:裸 print + 一行「沒走 sys.stdout.buffer」註解 ====
+ cat
+ set +e
+ python /tmp/tmp.D7fIPlZFGz/qa60/repo/scripts/validate.py
FAIL scripts/_repro60.py: runnable script does not pin stdout to UTF-8 inside its `if __name__ == "__main__"` block — its 中文 output is mojibake on a cp950 console (#58)
+ echo 'exit 1'
exit 1
+ set -e
+ rm /tmp/tmp.D7fIPlZFGz/qa60/repo/scripts/_repro60.py
+ echo '==== STEP 4  同型全掃:「提到」的所有寫法 vs 「用到」的所有寫法 ===='
==== STEP 4  同型全掃:「提到」的所有寫法 vs 「用到」的所有寫法 ====
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
+ echo '==== STEP 5  不得誤紅:真的走 buffer 的 triage-to-maintain.py 仍被豁免 ===='
==== STEP 5  不得誤紅:真的走 buffer 的 triage-to-maintain.py 仍被豁免 ====
+ grep -n sys.stdout.buffer '/d/Self Project/Skills/scripts/hooks/triage-to-maintain.py'
35:        sys.stdout.buffer.write((REMINDER + chr(10)).encode("utf-8"))
+ python - '/d/Self Project/Skills'
triage-to-maintain.py 的 error 數 -> 0
+ echo '==== STEP 6  #58 的原病沒退步:pin 放在 main() 而不是 __main__ block -> 仍判紅 ===='
==== STEP 6  #58 的原病沒退步:pin 放在 main() 而不是 __main__ block -> 仍判紅 ====
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --positional
pin 在 main(),__main__ 只呼叫它      期望 RED    實際 RED    ok
pin 在 __main__ 之前的 top-level    期望 RED    實際 RED    ok
pin 真的在 __main__ block 裡        期望 GREEN  實際 GREEN  ok
pin 在 __main__ block 裡的 try 底下  期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '==== STEP 6b  上一輪的 blocking(#65)已修:靜默跳過三條路只剩 SyntaxError(#66,known issue)===='
==== STEP 6b  上一輪的 blocking(#65)已修:靜默跳過三條路只剩 SyntaxError(#66,known issue)====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --skips
__main__ 縮排在 try 底下 -> 找不到 top-level If,整檔跳過           期望 RED    實際 RED    ok
__main__ 縮排在 if True 底下 -> 同上                          期望 RED    實際 RED    ok
檔案 parse 不過(SyntaxError)-> 整檔跳過(build 已在 code 裡註明的取捨)  期望 RED    實際 GREEN  MISMATCH

母體 3,不合 1
+ echo 'exit 1  <- 非 0 是預期的:剩下那條是 #66,已開票排期'
exit 1  <- 非 0 是預期的:剩下那條是 #66,已開票排期
+ set -e
+ echo '==== STEP 6c  對照組:同樣三個 case 在改之前(d3cc9ed^)是判紅的 ===='
==== STEP 6c  對照組:同樣三個 case 在改之前(d3cc9ed^)是判紅的 ====
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --skips --old
__main__ 縮排在 try 底下 -> 找不到 top-level If,整檔跳過           期望 RED    實際 RED    ok
__main__ 縮排在 if True 底下 -> 同上                          期望 RED    實際 RED    ok
檔案 parse 不過(SyntaxError)-> 整檔跳過(build 已在 code 裡註明的取捨)  期望 RED    實際 RED    ok

母體 3,不合 0
+ echo '==== STEP 6d  上一輪的 blocking(#70)已修:豁免的位置判準(AC1 原句的「會執行的位置」)全綠 ===='
==== STEP 6d  上一輪的 blocking(#70)已修:豁免的位置判準(AC1 原句的「會執行的位置」)全綠 ====
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --bypass-position
bypass 在從未被呼叫的 function 內                                  期望 RED    實際 RED    ok
bypass 在 `if False:` 死碼裡                                   期望 RED    實際 RED    ok
bypass 只出現在跑不到的 except 分支                                  期望 RED    實際 RED    ok
bypass 在 `raise SystemExit` 之後的死碼                          期望 RED    實際 RED    ok
bypass 真的在 __main__ 裡用(不得誤紅)                               期望 GREEN  實際 GREEN  ok
bypass 在 main(),__main__ 呼叫它(triage-to-maintain 的形狀,不得誤紅)  期望 GREEN  實際 GREEN  ok

母體 6,不合 0
+ echo '==== STEP 6e  對照組:同一組 case 在改之前(d3cc9ed^)4 條不合 -> 這輪真的抬了天花板 ===='
==== STEP 6e  對照組:同一組 case 在改之前(d3cc9ed^)4 條不合 -> 這輪真的抬了天花板 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --bypass-position --old
bypass 在從未被呼叫的 function 內                                  期望 RED    實際 GREEN  MISMATCH
bypass 在 `if False:` 死碼裡                                   期望 RED    實際 GREEN  MISMATCH
bypass 只出現在跑不到的 except 分支                                  期望 RED    實際 GREEN  MISMATCH
bypass 在 `raise SystemExit` 之後的死碼                          期望 RED    實際 GREEN  MISMATCH
bypass 真的在 __main__ 裡用(不得誤紅)                               期望 GREEN  實際 GREEN  ok
bypass 在 main(),__main__ 呼叫它(triage-to-maintain 的形狀,不得誤紅)  期望 GREEN  實際 GREEN  ok

母體 6,不合 4
+ echo 'exit 1  <- 非 0 是要的:對照組該紅'
exit 1  <- 非 0 是要的:對照組該紅
+ set -e
+ echo '==== STEP 6f  AC1 括號裡的第二支路(「或檔案裡沒有裸 print(」)有沒有實作 — 純證據,不是 finding ===='
==== STEP 6f  AC1 括號裡的第二支路(「或檔案裡沒有裸 print(」)有沒有實作 — 純證據,不是 finding ====
+ python - '/d/Self Project/Skills'
整檔沒有裸 print(,也沒 pin/bypass          第二支路會判 GREEN  實際 RED
print 只出現在 comment 裡,不是真的呼叫         第二支路會判 GREEN  實際 RED
只寫檔案、完全不印到 console                  第二支路會判 GREEN  實際 RED

三條都 RED -> 第二支路沒實作(守門不看 print,只看 pin/bypass)
+ echo '==== STEP 6g  本輪同型全掃(一):可達性判準只裝在 bypass 那半,pin 那半沒有 ===='
==== STEP 6g  本輪同型全掃(一):可達性判準只裝在 bypass 那半,pin 那半沒有 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --pin-position
pin 在 __main__ 內的 `if False:` 死碼裡          期望 RED    實際 GREEN  MISMATCH
pin 在 __main__ 內 `raise SystemExit` 之後的死碼  期望 RED    實際 GREEN  MISMATCH
pin 在 __main__ 內定義但沒人呼叫的 nested def        期望 RED    實際 GREEN  MISMATCH
pin 只出現在跑不到的 except 分支                     期望 RED    實際 GREEN  MISMATCH
pin 真的在 __main__ block 裡(不得誤紅)             期望 GREEN  實際 GREEN  ok
pin 在 block 內的 try body 裡(不得誤紅)            期望 GREEN  實際 GREEN  ok

母體 6,不合 4
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ set -e
+ echo '==== STEP 6h  對照組:同一組 case 在 d3cc9ed^ 也 4 條不合 -> 天花板沒抬,不是 regression ===='
==== STEP 6h  對照組:同一組 case 在 d3cc9ed^ 也 4 條不合 -> 天花板沒抬,不是 regression ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --pin-position --old
pin 在 __main__ 內的 `if False:` 死碼裡          期望 RED    實際 GREEN  MISMATCH
pin 在 __main__ 內 `raise SystemExit` 之後的死碼  期望 RED    實際 GREEN  MISMATCH
pin 在 __main__ 內定義但沒人呼叫的 nested def        期望 RED    實際 GREEN  MISMATCH
pin 只出現在跑不到的 except 分支                     期望 RED    實際 GREEN  MISMATCH
pin 真的在 __main__ block 裡(不得誤紅)             期望 GREEN  實際 GREEN  ok
pin 在 block 內的 try body 裡(不得誤紅)            期望 GREEN  實際 GREEN  ok

母體 6,不合 4
+ echo 'exit 1'
exit 1
+ set -e
+ echo '==== STEP 6i  本輪同型全掃(二):拿 live_exprs docstring 的字面重新推導 ===='
==== STEP 6i  本輪同型全掃(二):拿 live_exprs docstring 的字面重新推導 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --callgraph
bypass 在 handler dict 裡被呼叫的 function(docstring 說仍算 live)  期望 GREEN  實際 RED    MISMATCH
bypass 在 alias 呼叫的 function(docstring 說仍算 live)           期望 GREEN  實際 RED    MISMATCH
bypass 當 callback 傳進去被呼叫(docstring 說仍算 live)              期望 GREEN  實際 RED    MISMATCH
bypass 在 class method,__main__ 直接呼叫(對照:.attr 名字對得上)       期望 GREEN  實際 GREEN  ok

母體 4,不合 3
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ set -e
+ echo '==== STEP 6j  對照組:同一組 case 在 d3cc9ed^ 全綠 -> 這 3 條誤紅是 #70 修法引入的 ===='
==== STEP 6j  對照組:同一組 case 在 d3cc9ed^ 全綠 -> 這 3 條誤紅是 #70 修法引入的 ====
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --callgraph --old
bypass 在 handler dict 裡被呼叫的 function(docstring 說仍算 live)  期望 GREEN  實際 GREEN  ok
bypass 在 alias 呼叫的 function(docstring 說仍算 live)           期望 GREEN  實際 GREEN  ok
bypass 當 callback 傳進去被呼叫(docstring 說仍算 live)              期望 GREEN  實際 GREEN  ok
bypass 在 class method,__main__ 直接呼叫(對照:.attr 名字對得上)       期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '==== STEP 7  repo 本體沒被動過 ===='
==== STEP 7  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
 M scripts/qa/60-mention-sweep.py
 M scripts/qa/60-walkthrough.sh
```
