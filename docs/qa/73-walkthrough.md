# `/qa #73` walkthrough — `live_nodes` 的可達性收回「呼叫位置」

**HEAD**: `e8e32e8` ｜ 一鍵重開:`bash scripts/qa/73-walkthrough.sh "$(mktemp -d)/qa73"`

這一輪驗的是 #73(#71 把可達性放寬成「名字被提到」,#70 的天花板一行就能還原)修完之後,
#60 AC1 的原句逐條還成不成立。範圍 = #73 的重現 scenario + 既有 regression suite。
全程 bash xtrace,指令與輸出同一份,沒有事後 render。

STEP 8–11 是本輪的同型全掃:拿 #73 新立的「名字要在呼叫位置」當尺,兩個方向各量一遍 ——
誤紅那邊(callable 真的跑,但名字不在呼叫位置)與誤放那邊(名字交給任何 call 就算 live)。

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
+ echo '==== STEP 2  票上宣稱的 mutation 咬合:把可達性放寬回「名字被提到」-> self-check 要轉紅 ===='
==== STEP 2  票上宣稱的 mutation 咬合:把可達性放寬回「名字被提到」-> self-check 要轉紅 ====
+ grep -n 'invoked |= names_in(n.func)' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/829a33f2-0474-4d7d-bad3-4c67f1932e31/scratchpad/qa73/repo/scripts/validate.py
309:                    invoked |= names_in(n.func)
+ python - C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/829a33f2-0474-4d7d-bad3-4c67f1932e31/scratchpad/qa73/repo
mutation 已套用:可達性放寬回「名字被提到」
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/829a33f2-0474-4d7d-bad3-4c67f1932e31/scratchpad/qa73/repo/scripts/validate.py --self-check
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\claude\D--Self-Project-Skills\829a33f2-0474-4d7d-bad3-4c67f1932e31\scratchpad\qa73\repo\scripts\validate.py", line 1023, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\claude\D--Self-Project-Skills\829a33f2-0474-4d7d-bad3-4c67f1932e31\scratchpad\qa73\repo\scripts\validate.py", line 995, in self_check
    assert len(stream_encoding_issues(repo)) == 1, never
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: def dump():
    sys.stdout.buffer.write(b'x')
if __name__ == "__main__":
    x = [dump]
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:#73 的病一還原,self-check 就該紅'
exit 1  <- 非 0 是要的:#73 的病一還原,self-check 就該紅
+ set -e
+ cp '/d/Self Project/Skills/scripts/validate.py' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/829a33f2-0474-4d7d-bad3-4c67f1932e31/scratchpad/qa73/repo/scripts/validate.py
+ echo '==== STEP 3  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===='
==== STEP 3  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)====
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/829a33f2-0474-4d7d-bad3-4c67f1932e31/scratchpad/qa73/repo/scripts/validate.py --self-check
OK validate self-check green
+ echo '==== STEP 4  #73 的重現 scenario 原樣重跑(票上的母體 5)===='
==== STEP 4  #73 的重現 scenario 原樣重跑(票上的母體 5)====
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --live-overapprox
死碼裡的 bypass + live 區提到名字(不是呼叫)   期望 RED    實際 RED    ok
死碼裡的 bypass + 剛好撞名的區域變數          期望 RED    實際 RED    ok
死碼裡的 bypass + 無關物件的同名 attribute  期望 RED    實際 RED    ok
對照:死碼裡的 bypass,名字沒被提到(#70 的天花板)  期望 RED    實際 RED    ok
對照:bypass 在真的被呼叫的 main()(不得誤紅)   期望 GREEN  實際 GREEN  ok

母體 5,不合 0
+ echo '==== STEP 5  對照組:同一組 case 在 #73 修之前(e56789c)3 條誤放 -> 這輪真的修好了 ===='
==== STEP 5  對照組:同一組 case 在 #73 修之前(e56789c)3 條誤放 -> 這輪真的修好了 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --live-overapprox --prev73
死碼裡的 bypass + live 區提到名字(不是呼叫)   期望 RED    實際 GREEN  MISMATCH
死碼裡的 bypass + 剛好撞名的區域變數          期望 RED    實際 GREEN  MISMATCH
死碼裡的 bypass + 無關物件的同名 attribute  期望 RED    實際 GREEN  MISMATCH
對照:死碼裡的 bypass,名字沒被提到(#70 的天花板)  期望 RED    實際 RED    ok
對照:bypass 在真的被呼叫的 main()(不得誤紅)   期望 GREEN  實際 GREEN  ok

母體 5,不合 3
+ echo 'exit 1  <- 非 0 是要的:對照組該紅'
exit 1  <- 非 0 是要的:對照組該紅
+ set -e
+ echo '==== STEP 6  票上「不得放掉的天花板」逐條複驗 ===='
==== STEP 6  票上「不得放掉的天花板」逐條複驗 ====
+ echo '---- 6a  --callgraph(alias / handler dict / callback 不得誤紅)'
---- 6a  --callgraph(alias / handler dict / callback 不得誤紅)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --callgraph
bypass 在 handler dict 裡被呼叫的 function(docstring 說仍算 live)  期望 GREEN  實際 GREEN  ok
bypass 在 alias 呼叫的 function(docstring 說仍算 live)           期望 GREEN  實際 GREEN  ok
bypass 當 callback 傳進去被呼叫(docstring 說仍算 live)              期望 GREEN  實際 GREEN  ok
bypass 在 class method,__main__ 直接呼叫(對照:.attr 名字對得上)       期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '---- 6b  --bypass-position(#70 的死碼四條維持 RED)'
---- 6b  --bypass-position(#70 的死碼四條維持 RED)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --bypass-position
bypass 在從未被呼叫的 function 內                                  期望 RED    實際 RED    ok
bypass 在 `if False:` 死碼裡                                   期望 RED    實際 RED    ok
bypass 只出現在跑不到的 except 分支                                  期望 RED    實際 RED    ok
bypass 在 `raise SystemExit` 之後的死碼                          期望 RED    實際 RED    ok
bypass 真的在 __main__ 裡用(不得誤紅)                               期望 GREEN  實際 GREEN  ok
bypass 在 main(),__main__ 呼叫它(triage-to-maintain 的形狀,不得誤紅)  期望 GREEN  實際 GREEN  ok

母體 6,不合 0
+ echo '---- 6c  --positional(#58 原病)'
---- 6c  --positional(#58 原病)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --positional
pin 在 main(),__main__ 只呼叫它      期望 RED    實際 RED    ok
pin 在 __main__ 之前的 top-level    期望 RED    實際 RED    ok
pin 真的在 __main__ block 裡        期望 GREEN  實際 GREEN  ok
pin 在 __main__ block 裡的 try 底下  期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '---- 6d  mention 預設全表'
---- 6d  mention 預設全表
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
+ echo '---- 6e  triage-to-maintain.py 的 error 數要 = 0'
---- 6e  triage-to-maintain.py 的 error 數要 = 0
+ python - '/d/Self Project/Skills'
triage-to-maintain.py 的 error 數 -> 0
+ echo '==== STEP 7  已開票的天花板複驗(known issues,期望維持不變)===='
==== STEP 7  已開票的天花板複驗(known issues,期望維持不變)====
+ echo '---- 7a  --pin-position(#72:可達性只裝在 bypass 那半)'
---- 7a  --pin-position(#72:可達性只裝在 bypass 那半)
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --pin-position
pin 在 __main__ 內的 `if False:` 死碼裡          期望 RED    實際 GREEN  MISMATCH
pin 在 __main__ 內 `raise SystemExit` 之後的死碼  期望 RED    實際 GREEN  MISMATCH
pin 在 __main__ 內定義但沒人呼叫的 nested def        期望 RED    實際 GREEN  MISMATCH
pin 只出現在跑不到的 except 分支                     期望 RED    實際 GREEN  MISMATCH
pin 真的在 __main__ block 裡(不得誤紅)             期望 GREEN  實際 GREEN  ok
pin 在 block 內的 try body 裡(不得誤紅)            期望 GREEN  實際 GREEN  ok

母體 6,不合 4
+ echo 'exit 1  <- 非 0 是預期的:#72 已開票'
exit 1  <- 非 0 是預期的:#72 已開票
+ echo '---- 7b  --print-detect(#74:沒-print 豁免是 name-only)'
---- 7b  --print-detect(#74:沒-print 豁免是 name-only)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --print-detect
print 用 alias 呼叫(p = print; p(中文))                 期望 RED    實際 GREEN  MISMATCH
print 走 builtins(builtins.print(中文))               期望 RED    實際 GREEN  MISMATCH
print 當 callback 傳進去(run(print))                   期望 RED    實際 GREEN  MISMATCH
print 放在 handler dict 裡(H = {p: print}; H[p](中文))  期望 RED    實際 GREEN  MISMATCH
sys.stdout.write(中文)(build 已宣告的天花板)                期望 RED    實際 GREEN  MISMATCH
對照:真的裸 print(,沒 pin(不得漏放)                          期望 RED    實際 RED    ok
對照:真的完全不印 console(不得誤紅)                            期望 GREEN  實際 GREEN  ok

母體 7,不合 5
+ echo 'exit 1  <- 非 0 是預期的:#74 已開票'
exit 1  <- 非 0 是預期的:#74 已開票
+ echo '---- 7c  --skips(#66:SyntaxError 靜默跳過)'
---- 7c  --skips(#66:SyntaxError 靜默跳過)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --skips
__main__ 縮排在 try 底下 -> 找不到 top-level If,整檔跳過           期望 RED    實際 RED    ok
__main__ 縮排在 if True 底下 -> 同上                          期望 RED    實際 RED    ok
檔案 parse 不過(SyntaxError)-> 整檔跳過(build 已在 code 裡註明的取捨)  期望 RED    實際 GREEN  MISMATCH

母體 3,不合 1
+ echo 'exit 1  <- 非 0 是預期的:#66 已開票'
exit 1  <- 非 0 是預期的:#66 已開票
+ set -e
+ echo '==== STEP 8  本輪同型全掃(一):綁定形狀 — callable 真的跑,但名字不在呼叫位置 ===='
==== STEP 8  本輪同型全掃(一):綁定形狀 — callable 真的跑,但名字不在呼叫位置 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --binding
對照:alias `f = dump; f()`(#71 修好的形狀,不得誤紅)                  期望 GREEN  實際 GREEN  ok
for 迴圈變數 `for f in [dump]: f()`                           期望 GREEN  實際 RED    MISMATCH
tuple 解包 `a, b = dump, dump; a()`                         期望 GREEN  實際 RED    MISMATCH
帶型別註記的綁定 `f: object = dump; f()`                          期望 GREEN  實際 RED    MISMATCH
factory 回傳 callable `def get(): return dump` + `get()()`  期望 GREEN  實際 RED    MISMATCH
class 屬性 `class W: run = dump` + `W.run()`                期望 GREEN  實際 RED    MISMATCH

母體 6,不合 5
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ set -e
+ echo '==== STEP 9  對照組:同一組 case 在 #73 修之前(e56789c)只有 2 條不合 ===='
==== STEP 9  對照組:同一組 case 在 #73 修之前(e56789c)只有 2 條不合 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --binding --prev
對照:alias `f = dump; f()`(#71 修好的形狀,不得誤紅)                  期望 GREEN  實際 GREEN  ok
for 迴圈變數 `for f in [dump]: f()`                           期望 GREEN  實際 RED    MISMATCH
tuple 解包 `a, b = dump, dump; a()`                         期望 GREEN  實際 GREEN  ok
帶型別註記的綁定 `f: object = dump; f()`                          期望 GREEN  實際 GREEN  ok
factory 回傳 callable `def get(): return dump` + `get()()`  期望 GREEN  實際 GREEN  ok
class 屬性 `class W: run = dump` + `W.run()`                期望 GREEN  實際 RED    MISMATCH

母體 6,不合 2
+ echo 'exit 1  <- 差額 = #73 引入的誤紅'
exit 1  <- 差額 = #73 引入的誤紅
+ set -e
+ echo '==== STEP 10  本輪同型全掃(二):引數即呼叫 — 名字交給任何 call 就算 live ===='
==== STEP 10  本輪同型全掃(二):引數即呼叫 — 名字交給任何 call 就算 live ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --arg-widen
對照:`run(dump)`,run 真的呼叫它(#71 的 callback,不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:名字完全沒被提到(#70 的天花板)                          期望 RED    實際 RED    ok
`print(dump)` — 印出 function 物件,沒有呼叫它           期望 RED    實際 GREEN  MISMATCH
`x = str(dump)` — 引數,但 str 不會呼叫它               期望 RED    實際 GREEN  MISMATCH
`x = len([dump])` — 名字包在 list 裡當引數             期望 RED    實際 GREEN  MISMATCH
`print(f"{dump}")` — 名字在 f-string 的引數裡         期望 RED    實際 GREEN  MISMATCH
`isinstance(dump, object)` — 關鍵字/位置引數都一樣       期望 RED    實際 GREEN  MISMATCH

母體 7,不合 5
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ set -e
+ echo '==== STEP 11  對照組:同一組 case 在 e56789c 同樣 5 條不合 -> 不是 #73 引入的 ===='
==== STEP 11  對照組:同一組 case 在 e56789c 同樣 5 條不合 -> 不是 #73 引入的 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --arg-widen --prev
對照:`run(dump)`,run 真的呼叫它(#71 的 callback,不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:名字完全沒被提到(#70 的天花板)                          期望 RED    實際 RED    ok
`print(dump)` — 印出 function 物件,沒有呼叫它           期望 RED    實際 GREEN  MISMATCH
`x = str(dump)` — 引數,但 str 不會呼叫它               期望 RED    實際 GREEN  MISMATCH
`x = len([dump])` — 名字包在 list 裡當引數             期望 RED    實際 GREEN  MISMATCH
`print(f"{dump}")` — 名字在 f-string 的引數裡         期望 RED    實際 GREEN  MISMATCH
`isinstance(dump, object)` — 關鍵字/位置引數都一樣       期望 RED    實際 GREEN  MISMATCH

母體 7,不合 5
+ echo 'exit 1'
exit 1
+ set -e
+ echo '==== STEP 12  repo 本體沒被動過 ===='
==== STEP 12  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
 M scripts/qa/60-mention-sweep.py
?? scripts/qa/73-reach-sweep.py
?? scripts/qa/73-walkthrough.sh
```
