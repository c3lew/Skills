# QA walkthrough — #60 第二輪(上一輪 blocking #65 修完重跑)

第一輪報告在 [`60-walkthrough.md`](60-walkthrough.md),那輪抓到一條 blocking(#65:`__main__`
縮排一層就整檔跳過)。#65 已 build + QA + 結案,這份是照同一份 oracle 重跑的第二輪。

Bug fix ticket,範圍 = 該 bug 的重現 scenario + regression suite。

判定 oracle(票上 `/maintain` 分流那則的重現 scenario 與完工定義原句):

> 1. 開一支新 script,裡面用裸 `print(` 輸出,**沒有**做 `sys.stdout.reconfigure`
> 2. 在檔案任一處(docstring 或註解都行)寫下字串 `sys.stdout.buffer`,例如 `# 這裡沒走 sys.stdout.buffer`
> 3. 跑 `python scripts/validate.py`
> 4. 現況:綠(豁免是全檔 substring 比對,註解就把守門關掉了)
> 5. 期望:紅 —「註解提到就豁免」不成立
>
> - [ ] AC1 豁免改成位置/語意判準(真的在會執行的位置用 `sys.stdout.buffer.write`,或檔案裡沒有裸 `print(`),不是全檔 substring
> - [ ] AC2 self-check 補一條咬上面那個 mutation
> - [ ] AC3 現況唯一走這條路的 `scripts/hooks/triage-to-maintain.py` L35 仍被正確豁免(不得誤紅)
> - [ ] AC4 `python scripts/validate.py` 綠

外加 repo 自己的紀律 `references/written-evidence.md`〈Guard 的完工定義〉三條:住在預設就會跑的
地方、**兩種 mutation 都咬得到**(改壞 + 繞過)、查不到目標時判 fail 不是靜靜略過。

交付物是 `scripts/validate.py` 的 guard,沒有 UI、沒有視覺 oracle,不走 Playwright、沒有錄影 —
實錄就是下面這份終端 transcript(全程 bash xtrace,指令與輸出在同一份,沒有事後 render)。
mutation 全部跑在拋棄式暫存目錄的副本或 `tempfile.mkdtemp()` 上,repo 本體沒被動過
(STEP 7 的 `git status` 是證據)。

環境:`D:/Self Project/Skills`,branch `main`,HEAD = `411531d`。

一鍵重開(client-demo / 之後每輪 QA 直接抄):

```bash
bash scripts/qa/60-walkthrough.sh "$(mktemp -d)/qa60"
```

步驟(6d / 6e 是本輪新增,其餘與第一輪同一支 script):

| # | 驗的是 | 對應驗收原句 |
| --- | --- | --- |
| 1 | regression suite:`validate.py` + 五支 self-check | AC4 / 既有 regression |
| 1b | **AC2 的反證**:副本裡把豁免那一行改回 #60 修之前的 substring 寫法(`bypass in py.read_text(...)`)→ `--self-check` 轉紅,爆掉的 assert 印出來的就是那條「`# 這裡沒走 sys.stdout.buffer`」mutation | AC2 |
| 2 | 拋棄式副本未動過 → 綠(證明後面判紅的是 mutation,不是副本壞了) | — 對照 |
| 3 | 票上的重現 scenario **原樣重跑** → `validate.py` 判紅,error 指名 `scripts/_repro60.py` | 重現 scenario 第 5 點 |
| 4 | **同型全掃(散文位置)**:母體 = 散文能出現的每個位置 × 兩個目標字串 = 13 條 → 13/13 符合期望 | AC1 語意那半 |
| 5 | 不得誤紅:`scripts/hooks/triage-to-maintain.py` L35 真的在跑 `sys.stdout.buffer.write`,仍豁免(該檔 error 數 = 0) | AC3 |
| 6 | #58 的原病沒退步:pin 放在 `main()`、或 `__main__` 之前的 top-level → 仍判紅;真的在 block 裡(含 block 內的 `try`)→ 綠。母體 4,4/4 | AC1 pin 那半 |
| 6b | 上一輪的 blocking 已修:靜默跳過三條路,`try` / `if True` 兩條**這輪判紅**,只剩 `SyntaxError`(#66,已開票) | 上輪 blocking 複驗 |
| 6c | 對照組:三條在 `d3cc9ed^` 都判紅(第一輪用來證明 #65 是 regression 的那張表) | — |
| 6d | **本輪同型全掃(豁免的位置)**:AC1 原句要的是「真的在**會執行的位置**」。母體 6 = 死碼 / 沒人呼叫的 function / 跑不到的 except / `raise SystemExit` 之後 × bypass,加兩條合法對照 → **4 條不合** | AC1 位置那半 |
| 6e | 對照組:同一組 6 條在 `d3cc9ed^`(改之前)**也是 4 條不合** → 天花板沒抬,不是這次改動引入的 regression | — |
| 7 | repo 本體 `validate.py` 全綠,`git status` 只多這輪的 QA artifact | AC4 |

AC1 是「或」寫成的兩支實作路,擇一即可。STEP 6f 證明守門走的是第一支(bypass 的語意判準),
第二支(「檔案裡沒有裸 `print(`」)完全沒實作 —— 沒有裸 print 的檔案照樣要求 pin。所以 AC1
只能拿第一支來判,而第一支的「會執行的位置」那半就是 STEP 6d 那張表。

## 獨立 judge 判定

judge 是乾淨 subagent,只拿到上面的驗收原句 + transcript,沒有實作脈絡。

| 條目 | 判定 |
| --- | --- |
| 重現 scenario(裸 print + 註解提到 bypass → 期望紅) | **pass**(STEP 3) |
| AC1 豁免改成位置/語意判準 | **fail(works-but-wrong)** — 語意那半成立(STEP 4,13/13),位置那半沒做(STEP 6d,母體 6 不合 4) |
| AC2 self-check 補一條咬那個 mutation | **pass**(STEP 1b 反證) |
| AC3 `triage-to-maintain.py` L35 仍豁免 | **pass**(STEP 5,error 數 0) |
| AC4 `python scripts/validate.py` 綠 | **pass**(STEP 1 / STEP 7) |

judge 第一輪對 AC1 除了判 fail,還掛了一條「AC1 括號的第二支路(檔案裡沒有裸 `print(`)
沒有任何證據」的舉證不足。補跑 STEP 6f 後 judge 複判,逐字重點:

> 它是 disjunction 沒錯,但 disjunction 要救人的前提是**至少有一支真的存在**。STEP 6d 證明
> A 只做了 mention/use 語意、沒做「會執行的位置」;STEP 6f 證明 B 一行都沒有。兩支都不成立,
> or 沒有東西可以短路。而且方向反了:第二支路是**放寬**豁免,不是收緊 —— 就算它有做,也不
> 可能替 A 補上「會執行的位置」這個 A 獨有的收緊語意。

judge 也認可把 STEP 6f 記為純事實、不當 finding:少一支放寬路徑本身不製造誤紅,不是獨立
缺陷,它的意義只在「不能拿來救 AC1」。

## Blocking

- **#70** `sys.stdout.buffer` 豁免吃整棵 AST(`norm(bypass) in whole`),死碼 / 跑不到的
  分支 / 沒人呼叫的 function 裡塞一行就整檔豁免。母體 6 不合 4,`--old` 對照證明是天花板
  沒抬、不是這次改動引入的 regression。

## Known issues(非 blocking,由 client 在 demo 收尾整批確認)

- **#66** 檔案 `SyntaxError` → 整檔跳過。build 已在 code 裡註明是取捨,但違反
  written-evidence〈Guard 的完工定義〉第三條,留票排期。
- **#67 / #68 / #69** — `/qa #65` 那輪同型全掃挖出的三條守門天花板(只認一種 `__main__`
  寫法、`__main__.py` 被檔名過濾誤傷、一個檔多個 `__main__` 只看第一個)。都不在 #60 的
  驗收原句上,排期中。
- `from sys import stdout` 這種 import 形式偵測不到 —— build 自己在 review findings 記過,
  改之前也一樣,不是這輪 regression。
- `sys.stdout.reconfigure("utf-8")`(位置引數)判紅。等價安全但寫法不同,`norm(pin)` 是精確
  比對。改之前同樣判紅。
- STEP 1b 那段 traceback 的中文是 mojibake —— traceback 走 stderr,`STREAM_PINS` 只管
  stdout / stdin,不在 #58 立的規矩範圍內。

## 上一輪 blocking 複驗

- **#65**(`__main__` 縮排一層就整檔跳過)→ **已修**。STEP 6b 三條靜默跳過的路,`try` /
  `if True` 兩條這輪判紅,只剩 `SyntaxError`(#66)。`self_check()` 也補了對應的 mutation。

## 未涵蓋範圍

沒有 UI、沒有 Tauri 原生殼,不適用。全部是 CLI guard,終端 transcript 即實錄(全程 bash
xtrace,指令與輸出同一份,沒有事後 render)。

## Demo 實錄

| 驗收項 | 實錄 |
| --- | --- |
| 全部(STEP 1–7,含 1b / 6b–6f) | 本檔〈終端實錄〉 |

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
+ echo '==== STEP 1b  self-check 真的咬得到「散文當 code」:副本裡把豁免改回 substring -> self-check 轉紅 ===='
==== STEP 1b  self-check 真的咬得到「散文當 code」:副本裡把豁免改回 substring -> self-check 轉紅 ====
+ grep -n 'norm(bypass) in whole' /tmp/tmp.rMBfbewB6k/qa60/repo/scripts/validate.py
269:            if norm(bypass) in whole or norm(pin) in inside:
+ sed -i 's|if norm(bypass) in whole or|if bypass in py.read_text(encoding="utf-8") or|' /tmp/tmp.rMBfbewB6k/qa60/repo/scripts/validate.py
+ grep -n 'bypass in py.read_text' /tmp/tmp.rMBfbewB6k/qa60/repo/scripts/validate.py
269:            if bypass in py.read_text(encoding="utf-8") or norm(pin) in inside:
+ set +e
+ python /tmp/tmp.rMBfbewB6k/qa60/repo/scripts/validate.py --self-check
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.rMBfbewB6k\qa60\repo\scripts\validate.py", line 844, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.rMBfbewB6k\qa60\repo\scripts\validate.py", line 820, in self_check
    assert len(stream_encoding_issues(repo)) == 1, mention
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: if __name__ == "__main__":
    print("�n�}")
    # �o�̨S�� sys.stdout.buffer

+ echo 'exit 1  <- 非 0 是要的:#60 的病一還原,self-check 就該紅'
exit 1  <- 非 0 是要的:#60 的病一還原,self-check 就該紅
+ set -e
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.rMBfbewB6k/qa60/repo/scripts/validate.py
+ echo '==== STEP 2  副本未動過 -> 綠(證明後面判紅的是 mutation,不是副本壞了)===='
==== STEP 2  副本未動過 -> 綠(證明後面判紅的是 mutation,不是副本壞了)====
+ python /tmp/tmp.rMBfbewB6k/qa60/repo/scripts/validate.py
OK validate green
+ echo '==== STEP 3  票上的重現 scenario 原樣重跑:裸 print + 一行「沒走 sys.stdout.buffer」註解 ===='
==== STEP 3  票上的重現 scenario 原樣重跑:裸 print + 一行「沒走 sys.stdout.buffer」註解 ====
+ cat
+ set +e
+ python /tmp/tmp.rMBfbewB6k/qa60/repo/scripts/validate.py
FAIL scripts/_repro60.py: runnable script does not pin stdout to UTF-8 inside its `if __name__ == "__main__"` block — its 中文 output is mojibake on a cp950 console (#58)
+ echo 'exit 1'
exit 1
+ set -e
+ rm /tmp/tmp.rMBfbewB6k/qa60/repo/scripts/_repro60.py
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
+ echo '==== STEP 6d  本輪同型全掃:豁免的位置判準(AC1 原句的「會執行的位置」)===='
==== STEP 6d  本輪同型全掃:豁免的位置判準(AC1 原句的「會執行的位置」)====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --bypass-position
bypass 在從未被呼叫的 function 內                                  期望 RED    實際 GREEN  MISMATCH
bypass 在 `if False:` 死碼裡                                   期望 RED    實際 GREEN  MISMATCH
bypass 只出現在跑不到的 except 分支                                  期望 RED    實際 GREEN  MISMATCH
bypass 在 `raise SystemExit` 之後的死碼                          期望 RED    實際 GREEN  MISMATCH
bypass 真的在 __main__ 裡用(不得誤紅)                               期望 GREEN  實際 GREEN  ok
bypass 在 main(),__main__ 呼叫它(triage-to-maintain 的形狀,不得誤紅)  期望 GREEN  實際 GREEN  ok

母體 6,不合 4
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ set -e
+ echo '==== STEP 6e  對照組:同一組 case 在改之前也全綠 -> 是天花板沒抬,不是 regression ===='
==== STEP 6e  對照組:同一組 case 在改之前也全綠 -> 是天花板沒抬,不是 regression ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --bypass-position --old
bypass 在從未被呼叫的 function 內                                  期望 RED    實際 GREEN  MISMATCH
bypass 在 `if False:` 死碼裡                                   期望 RED    實際 GREEN  MISMATCH
bypass 只出現在跑不到的 except 分支                                  期望 RED    實際 GREEN  MISMATCH
bypass 在 `raise SystemExit` 之後的死碼                          期望 RED    實際 GREEN  MISMATCH
bypass 真的在 __main__ 裡用(不得誤紅)                               期望 GREEN  實際 GREEN  ok
bypass 在 main(),__main__ 呼叫它(triage-to-maintain 的形狀,不得誤紅)  期望 GREEN  實際 GREEN  ok

母體 6,不合 4
+ echo 'exit 1'
exit 1
+ set -e
+ echo '==== STEP 6f  AC1 括號裡的第二支路(「或檔案裡沒有裸 print(」)有沒有實作 — 純證據,不是 finding ===='
==== STEP 6f  AC1 括號裡的第二支路(「或檔案裡沒有裸 print(」)有沒有實作 — 純證據,不是 finding ====
+ python - '/d/Self Project/Skills'
整檔沒有裸 print(,也沒 pin/bypass          第二支路會判 GREEN  實際 RED
print 只出現在 comment 裡,不是真的呼叫         第二支路會判 GREEN  實際 RED
只寫檔案、完全不印到 console                  第二支路會判 GREEN  實際 RED

三條都 RED -> 第二支路沒實作(守門不看 print,只看 pin/bypass)
+ echo '==== STEP 7  repo 本體沒被動過 ===='
==== STEP 7  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
 M scripts/qa/60-mention-sweep.py
 M scripts/qa/60-walkthrough.sh
```
