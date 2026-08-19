# `/qa #79` walkthrough — live def 的回傳值改成「結果被呼叫才算 live」

**HEAD**: `63e2c36` ｜ 一鍵重開:`bash scripts/qa/79-walkthrough.sh "$(mktemp -d)/qa79"`

這一輪驗的是 #79(`live_nodes` 把 live def `return` 出去的名字無條件算 live,於是
`def get(): return dump` 加一行 `get()` —— 回傳值直接丟掉、`dump` 一行都沒跑 —— 就讓整檔
豁免)修完之後,#60 AC1 的原句逐條還成不成立。範圍 = #79 的重現 scenario + 既有 regression
suite。全程 bash xtrace,指令與輸出同一份,沒有事後 render。

STEP 8–9 是本輪的同型全掃,拿修法自己立的兩把尺各量一遍:
- 尺一(誤放那邊)—「def `return` 的如果是它**自己產生**的名字,就不是外面那個死碼」。
  `local` 只認 `ast.Name` 的 Store 與 `arg`;def 內部產生名字的寫法不只這兩種。
- 尺二(誤紅那邊)—「呼叫結果自己也在呼叫位置才算 live」。只認 `get()()` 與 `f = get()`
  兩條路;把結果送到呼叫位置的其他寫法有沒有落在外面。

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
+ echo '==== STEP 2  #79 的重現 scenario 原樣重跑(票上的母體,現在 6 條)===='
==== STEP 2  #79 的重現 scenario 原樣重跑(票上的母體,現在 6 條)====
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --return-carry
死碼 bypass + `def get(): return dump`,`get()` 結果直接丟掉  期望 RED    實際 RED    ok
同上,回傳值存進變數但從未呼叫(`x = get()`)                         期望 RED    實際 RED    ok
get() 回傳的是自己的區域變數,只是剛好撞名死碼 def                       期望 RED    實際 RED    ok
對照:回傳值真的被呼叫 `get()()`(#75 立的天花板,不得誤紅)                期望 GREEN  實際 GREEN  ok
對照:回傳值存進變數後才呼叫 `f = get(); f()`(#79 的天花板,不得誤紅)       期望 GREEN  實際 GREEN  ok
對照:`get` 自己也沒被呼叫(死碼,必須維持 RED)                        期望 RED    實際 RED    ok

母體 6,不合 0
+ echo '==== STEP 3  對照組:#79 修之前(8beebc5)那三條誤放,再往前(39003a3)是兩條誤紅 ===='
==== STEP 3  對照組:#79 修之前(8beebc5)那三條誤放,再往前(39003a3)是兩條誤紅 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --return-carry --prev79
死碼 bypass + `def get(): return dump`,`get()` 結果直接丟掉  期望 RED    實際 GREEN  MISMATCH
同上,回傳值存進變數但從未呼叫(`x = get()`)                         期望 RED    實際 GREEN  MISMATCH
get() 回傳的是自己的區域變數,只是剛好撞名死碼 def                       期望 RED    實際 GREEN  MISMATCH
對照:回傳值真的被呼叫 `get()()`(#75 立的天花板,不得誤紅)                期望 GREEN  實際 GREEN  ok
對照:回傳值存進變數後才呼叫 `f = get(); f()`(#79 的天花板,不得誤紅)       期望 GREEN  實際 GREEN  ok
對照:`get` 自己也沒被呼叫(死碼,必須維持 RED)                        期望 RED    實際 RED    ok

母體 6,不合 3
+ echo 'exit 1  <- 非 0 是要的:對照組該紅'
exit 1  <- 非 0 是要的:對照組該紅
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --return-carry --prev75
死碼 bypass + `def get(): return dump`,`get()` 結果直接丟掉  期望 RED    實際 RED    ok
同上,回傳值存進變數但從未呼叫(`x = get()`)                         期望 RED    實際 RED    ok
get() 回傳的是自己的區域變數,只是剛好撞名死碼 def                       期望 RED    實際 RED    ok
對照:回傳值真的被呼叫 `get()()`(#75 立的天花板,不得誤紅)                期望 GREEN  實際 RED    MISMATCH
對照:回傳值存進變數後才呼叫 `f = get(); f()`(#79 的天花板,不得誤紅)       期望 GREEN  實際 RED    MISMATCH
對照:`get` 自己也沒被呼叫(死碼,必須維持 RED)                        期望 RED    實際 RED    ok

母體 6,不合 2
+ echo 'exit 1  <- 非 0 是要的:對照組該紅'
exit 1  <- 非 0 是要的:對照組該紅
+ set -e
+ echo '==== STEP 4  票上宣稱的 mutation 咬合:兩個旋鈕逐一還原 -> self-check 要轉紅 ===='
==== STEP 4  票上宣稱的 mutation 咬合:兩個旋鈕逐一還原 -> self-check 要轉紅 ====
+ for M in ret_carry local_excl
+ echo '---- 4.ret_carry'
---- 4.ret_carry
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.rTTBhXKIvU/qa79/repo/scripts/validate.py
+ python - /tmp/tmp.rTTBhXKIvU/qa79/repo ret_carry
mutation 已套用: ret_carry
+ set +e
+ python /tmp/tmp.rTTBhXKIvU/qa79/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: factory called, result dropped
+ echo 'exit 1  <- 非 0 是要的:旋鈕一還原,self-check 就該紅'
exit 1  <- 非 0 是要的:旋鈕一還原,self-check 就該紅
+ set -e
+ for M in ret_carry local_excl
+ echo '---- 4.local_excl'
---- 4.local_excl
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.rTTBhXKIvU/qa79/repo/scripts/validate.py
+ python - /tmp/tmp.rTTBhXKIvU/qa79/repo local_excl
mutation 已套用: local_excl
+ set +e
+ python /tmp/tmp.rTTBhXKIvU/qa79/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: what it returns is its own local, colliding by name
+ echo 'exit 1  <- 非 0 是要的:旋鈕一還原,self-check 就該紅'
exit 1  <- 非 0 是要的:旋鈕一還原,self-check 就該紅
+ set -e
+ echo '==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===='
==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)====
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.rTTBhXKIvU/qa79/repo/scripts/validate.py
+ python /tmp/tmp.rTTBhXKIvU/qa79/repo/scripts/validate.py --self-check
OK validate self-check green
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
+ echo '---- 6b  --live-overapprox(#73 立的:死碼 bypass 不得因撞名豁免)'
---- 6b  --live-overapprox(#73 立的:死碼 bypass 不得因撞名豁免)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --live-overapprox
死碼裡的 bypass + live 區提到名字(不是呼叫)   期望 RED    實際 RED    ok
死碼裡的 bypass + 剛好撞名的區域變數          期望 RED    實際 RED    ok
死碼裡的 bypass + 無關物件的同名 attribute  期望 RED    實際 RED    ok
對照:死碼裡的 bypass,名字沒被提到(#70 的天花板)  期望 RED    實際 RED    ok
對照:bypass 在真的被呼叫的 main()(不得誤紅)   期望 GREEN  實際 GREEN  ok

母體 5,不合 0
+ echo '---- 6c  --bypass-position(#70 的死碼四條維持 RED)'
---- 6c  --bypass-position(#70 的死碼四條維持 RED)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --bypass-position
bypass 在從未被呼叫的 function 內                                  期望 RED    實際 RED    ok
bypass 在 `if False:` 死碼裡                                   期望 RED    實際 RED    ok
bypass 只出現在跑不到的 except 分支                                  期望 RED    實際 RED    ok
bypass 在 `raise SystemExit` 之後的死碼                          期望 RED    實際 RED    ok
bypass 真的在 __main__ 裡用(不得誤紅)                               期望 GREEN  實際 GREEN  ok
bypass 在 main(),__main__ 呼叫它(triage-to-maintain 的形狀,不得誤紅)  期望 GREEN  實際 GREEN  ok

母體 6,不合 0
+ echo '---- 6d  --mention 預設全表'
---- 6d  --mention 預設全表
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
+ echo '---- 6e  --positional(#58 原病)'
---- 6e  --positional(#58 原病)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --positional
pin 在 main(),__main__ 只呼叫它      期望 RED    實際 RED    ok
pin 在 __main__ 之前的 top-level    期望 RED    實際 RED    ok
pin 真的在 __main__ block 裡        期望 GREEN  實際 GREEN  ok
pin 在 __main__ block 裡的 try 底下  期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '---- 6f  #73 的三把尺'
---- 6f  #73 的三把尺
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
+ echo '---- 6g  #75 的 --bind-quiet(build 宣稱 11/0)'
---- 6g  #75 的 --bind-quiet(build 宣稱 11/0)
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
+ echo '==== STEP 7  已開票的天花板複驗(known issues,期望維持不變)===='
==== STEP 7  已開票的天花板複驗(known issues,期望維持不變)====
+ set +e
+ echo '---- 7a  --pin-position(#72)'
---- 7a  --pin-position(#72)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --pin-position
+ tail -2

母體 6,不合 4
+ echo '---- 7b  --print-detect(#74)'
---- 7b  --print-detect(#74)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --print-detect
+ tail -2

母體 7,不合 5
+ echo '---- 7c  --skips(#66)'
---- 7c  --skips(#66)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --skips
+ tail -2

母體 3,不合 1
+ echo '---- 7d  --name-collision(#80,未修)'
---- 7d  --name-collision(#80,未修)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --name-collision
+ tail -2

母體 4,不合 3
+ echo '---- 7e  #75 的另兩把尺(#77 / #78,未修)'
---- 7e  #75 的另兩把尺(#77 / #78,未修)
+ python '/d/Self Project/Skills/scripts/qa/75-binding-sweep.py' '/d/Self Project/Skills' --binding-shapes
+ tail -2

母體 12,不合 6
+ python '/d/Self Project/Skills/scripts/qa/75-binding-sweep.py' '/d/Self Project/Skills' --header
+ tail -2

母體 8,不合 5
+ set -e
+ echo '==== STEP 8  本輪同型全掃(一):def 交出去的是不是外面那個名字(誤放那邊)===='
==== STEP 8  本輪同型全掃(一):def 交出去的是不是外面那個名字(誤放那邊)====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/79-return-sweep.py' '/d/Self Project/Skills' --own-names
`dump = 1`(#79 已收:Name Store)           期望 RED    實際 RED    ok
參數同名 `def get(dump)`(#79 已收:arg)        期望 RED    實際 RED    ok
`with open() as dump`(Name Store,順帶收到)  期望 RED    實際 RED    ok
`for dump in [1]`(Name Store,順帶收到)      期望 RED    實際 RED    ok
walrus `(dump := 1)`(Name Store,順帶收到)   期望 RED    實際 RED    ok
巢狀 def 同名 `def dump():` 在 get 裡         期望 RED    實際 RED    ok
巢狀 class 同名 `class dump:` 在 get 裡       期望 RED    實際 GREEN  MISMATCH
`import os as dump` 在 get 裡             期望 RED    實際 GREEN  MISMATCH
`import dump` 在 get 裡                   期望 RED    實際 GREEN  MISMATCH
`from os import path as dump` 在 get 裡   期望 RED    實際 GREEN  MISMATCH
`except Exception as dump` 在 get 裡      期望 RED    實際 GREEN  MISMATCH
`match` 的 case 捕獲同名 `case [dump]`       期望 RED    實際 GREEN  MISMATCH
對照:`return dump` 真的是外面那個死碼 def(不得誤紅)    期望 GREEN  實際 GREEN  ok

母體 13,不合 6
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#79 修之前(8beebc5)'
---- 對照組:#79 修之前(8beebc5)
+ python '/d/Self Project/Skills/scripts/qa/79-return-sweep.py' '/d/Self Project/Skills' --own-names --prev
+ tail -2

母體 13,不合 11
+ set -e
+ echo '==== STEP 9  本輪同型全掃(二):把結果送到呼叫位置的每一種寫法(誤紅那邊)===='
==== STEP 9  本輪同型全掃(二):把結果送到呼叫位置的每一種寫法(誤紅那邊)====
+ set +e
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
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#79 修之前(8beebc5)'
---- 對照組:#79 修之前(8beebc5)
+ python '/d/Self Project/Skills/scripts/qa/79-return-sweep.py' '/d/Self Project/Skills' --result-called --prev
+ tail -2

母體 14,不合 3
+ set -e
+ echo '==== STEP 10  repo 本體沒被動過 ===='
==== STEP 10  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
 M scripts/qa/60-mention-sweep.py
?? scripts/qa/79-return-sweep.py
?? scripts/qa/79-walkthrough.sh
```
