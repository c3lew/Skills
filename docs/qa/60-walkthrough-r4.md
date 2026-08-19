# `/qa #60` 第四輪 walkthrough — `stream_encoding_issues` 豁免判準(#71 修完複驗)

**HEAD**: `f85b4dc` ｜ 一鍵重開:`bash scripts/qa/60-walkthrough.sh "$(mktemp -d)/qa60"`

這一輪驗的是 #71(bypass 可達性誤紅 + AC1 第二支路沒實作)修完之後,#60 的驗收原句
逐條還成不成立。全程 bash xtrace,指令與輸出同一份,沒有事後 render。

STEP 6k–6n 是本輪的同型全掃:拿 #71 新增的兩個判準當尺,量過所有同型寫法。

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
+ grep -n 'norm(bypass) in reached' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/d829d7bb-9cfd-4e67-882e-83fb149d149a/scratchpad/qa60/repo/scripts/validate.py
359:            if norm(bypass) in reached or norm(pin) in inside:
+ sed -i 's|if norm(bypass) in reached or|if bypass in py.read_text(encoding="utf-8") or|' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/d829d7bb-9cfd-4e67-882e-83fb149d149a/scratchpad/qa60/repo/scripts/validate.py
+ grep -n 'bypass in py.read_text' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/d829d7bb-9cfd-4e67-882e-83fb149d149a/scratchpad/qa60/repo/scripts/validate.py
359:            if bypass in py.read_text(encoding="utf-8") or norm(pin) in inside:
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/d829d7bb-9cfd-4e67-882e-83fb149d149a/scratchpad/qa60/repo/scripts/validate.py --self-check
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\claude\D--Self-Project-Skills\d829d7bb-9cfd-4e67-882e-83fb149d149a\scratchpad\qa60\repo\scripts\validate.py", line 990, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\claude\D--Self-Project-Skills\d829d7bb-9cfd-4e67-882e-83fb149d149a\scratchpad\qa60\repo\scripts\validate.py", line 911, in self_check
    assert len(stream_encoding_issues(repo)) == 1, mention
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: if __name__ == "__main__":
    print("�n�}")
    # �o�̨S�� sys.stdout.buffer

+ echo 'exit 1  <- 非 0 是要的:#60 的病一還原,self-check 就該紅'
exit 1  <- 非 0 是要的:#60 的病一還原,self-check 就該紅
+ set -e
+ cp '/d/Self Project/Skills/scripts/validate.py' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/d829d7bb-9cfd-4e67-882e-83fb149d149a/scratchpad/qa60/repo/scripts/validate.py
+ echo '==== STEP 2  副本未動過 -> 綠(證明後面判紅的是 mutation,不是副本壞了)===='
==== STEP 2  副本未動過 -> 綠(證明後面判紅的是 mutation,不是副本壞了)====
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/d829d7bb-9cfd-4e67-882e-83fb149d149a/scratchpad/qa60/repo/scripts/validate.py
OK validate green
+ echo '==== STEP 3  票上的重現 scenario 原樣重跑:裸 print + 一行「沒走 sys.stdout.buffer」註解 ===='
==== STEP 3  票上的重現 scenario 原樣重跑:裸 print + 一行「沒走 sys.stdout.buffer」註解 ====
+ cat
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/d829d7bb-9cfd-4e67-882e-83fb149d149a/scratchpad/qa60/repo/scripts/validate.py
FAIL scripts/_repro60.py: runnable script does not pin stdout to UTF-8 inside its `if __name__ == "__main__"` block — its 中文 output is mojibake on a cp950 console (#58)
+ echo 'exit 1'
exit 1
+ set -e
+ rm C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/d829d7bb-9cfd-4e67-882e-83fb149d149a/scratchpad/qa60/repo/scripts/_repro60.py
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
+ echo '==== STEP 6f  上一輪的 blocking(#71)已修(b):AC1 第二支路「或檔案裡沒有裸 print(」現在實作了 ===='
==== STEP 6f  上一輪的 blocking(#71)已修(b):AC1 第二支路「或檔案裡沒有裸 print(」現在實作了 ====
+ python - '/d/Self Project/Skills'
整檔沒有裸 print(,也沒 pin/bypass          期望 GREEN  實際 GREEN
print 只出現在 comment 裡,不是真的呼叫         期望 GREEN  實際 GREEN
只寫檔案、完全不印到 console                  期望 GREEN  實際 GREEN

不合 0(上一輪 3 條全 RED)
+ echo '==== STEP 6g  已知天花板(#72,known issue)複驗:可達性判準只裝在 bypass 那半,pin 那半沒有 ===='
==== STEP 6g  已知天花板(#72,known issue)複驗:可達性判準只裝在 bypass 那半,pin 那半沒有 ====
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
+ echo '==== STEP 6i  上一輪的 blocking(#71)已修(a):alias / handler dict / callback 三種形狀不再誤紅 ===='
==== STEP 6i  上一輪的 blocking(#71)已修(a):alias / handler dict / callback 三種形狀不再誤紅 ====
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --callgraph
bypass 在 handler dict 裡被呼叫的 function(docstring 說仍算 live)  期望 GREEN  實際 GREEN  ok
bypass 在 alias 呼叫的 function(docstring 說仍算 live)           期望 GREEN  實際 GREEN  ok
bypass 當 callback 傳進去被呼叫(docstring 說仍算 live)              期望 GREEN  實際 GREEN  ok
bypass 在 class method,__main__ 直接呼叫(對照:.attr 名字對得上)       期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '==== STEP 6j  對照組:同一組 case 在上一輪 HEAD(188c7d8)3 條誤紅 -> 天花板真的抬了 ===='
==== STEP 6j  對照組:同一組 case 在上一輪 HEAD(188c7d8)3 條誤紅 -> 天花板真的抬了 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --callgraph --prev
bypass 在 handler dict 裡被呼叫的 function(docstring 說仍算 live)  期望 GREEN  實際 RED    MISMATCH
bypass 在 alias 呼叫的 function(docstring 說仍算 live)           期望 GREEN  實際 RED    MISMATCH
bypass 當 callback 傳進去被呼叫(docstring 說仍算 live)              期望 GREEN  實際 RED    MISMATCH
bypass 在 class method,__main__ 直接呼叫(對照:.attr 名字對得上)       期望 GREEN  實際 GREEN  ok

母體 4,不合 3
+ echo 'exit 1  <- 非 0 是要的:對照組該紅'
exit 1  <- 非 0 是要的:對照組該紅
+ set -e
+ echo '==== STEP 6k  本輪同型全掃(一):沒-print 豁免的判準解析度 ===='
==== STEP 6k  本輪同型全掃(一):沒-print 豁免的判準解析度 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --print-detect
print 用 alias 呼叫(p = print; p(中文))                 期望 RED    實際 GREEN  MISMATCH
print 走 builtins(builtins.print(中文))               期望 RED    實際 GREEN  MISMATCH
print 當 callback 傳進去(run(print))                   期望 RED    實際 GREEN  MISMATCH
print 放在 handler dict 裡(H = {p: print}; H[p](中文))  期望 RED    實際 GREEN  MISMATCH
sys.stdout.write(中文)(build 已宣告的天花板)                期望 RED    實際 GREEN  MISMATCH
對照:真的裸 print(,沒 pin(不得漏放)                          期望 RED    實際 RED    ok
對照:真的完全不印 console(不得誤紅)                            期望 GREEN  實際 GREEN  ok

母體 7,不合 5
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ set -e
+ echo '==== STEP 6l  對照組:同一組 case 在上一輪 HEAD(188c7d8)只有 1 條不合 ===='
==== STEP 6l  對照組:同一組 case 在上一輪 HEAD(188c7d8)只有 1 條不合 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --print-detect --prev
print 用 alias 呼叫(p = print; p(中文))                 期望 RED    實際 RED    ok
print 走 builtins(builtins.print(中文))               期望 RED    實際 RED    ok
print 當 callback 傳進去(run(print))                   期望 RED    實際 RED    ok
print 放在 handler dict 裡(H = {p: print}; H[p](中文))  期望 RED    實際 RED    ok
sys.stdout.write(中文)(build 已宣告的天花板)                期望 RED    實際 RED    ok
對照:真的裸 print(,沒 pin(不得漏放)                          期望 RED    實際 RED    ok
對照:真的完全不印 console(不得誤紅)                            期望 GREEN  實際 RED    MISMATCH

母體 7,不合 1
+ echo 'exit 1'
exit 1
+ set -e
+ echo '==== STEP 6m  本輪同型全掃(二):可達性 over-approximate 的代價 ===='
==== STEP 6m  本輪同型全掃(二):可達性 over-approximate 的代價 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --live-overapprox
死碼裡的 bypass + live 區提到名字(不是呼叫)   期望 RED    實際 GREEN  MISMATCH
死碼裡的 bypass + 剛好撞名的區域變數          期望 RED    實際 GREEN  MISMATCH
死碼裡的 bypass + 無關物件的同名 attribute  期望 RED    實際 GREEN  MISMATCH
對照:死碼裡的 bypass,名字沒被提到(#70 的天花板)  期望 RED    實際 RED    ok
對照:bypass 在真的被呼叫的 main()(不得誤紅)   期望 GREEN  實際 GREEN  ok

母體 5,不合 3
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ set -e
+ echo '==== STEP 6n  對照組:同一組 case 在上一輪 HEAD(188c7d8)全綠 -> 是 #71 引入的 regression ===='
==== STEP 6n  對照組:同一組 case 在上一輪 HEAD(188c7d8)全綠 -> 是 #71 引入的 regression ====
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --live-overapprox --prev
死碼裡的 bypass + live 區提到名字(不是呼叫)   期望 RED    實際 RED    ok
死碼裡的 bypass + 剛好撞名的區域變數          期望 RED    實際 RED    ok
死碼裡的 bypass + 無關物件的同名 attribute  期望 RED    實際 RED    ok
對照:死碼裡的 bypass,名字沒被提到(#70 的天花板)  期望 RED    實際 RED    ok
對照:bypass 在真的被呼叫的 main()(不得誤紅)   期望 GREEN  實際 GREEN  ok

母體 5,不合 0
+ echo '==== STEP 7  repo 本體沒被動過 ===='
==== STEP 7  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
 M scripts/qa/60-mention-sweep.py
 M scripts/qa/60-walkthrough.sh
```
