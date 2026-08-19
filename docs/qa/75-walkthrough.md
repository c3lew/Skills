# `/qa #75` walkthrough — 可達性的綁定採集擴到同型的其他寫法

**HEAD**: `0a0ec2f` ｜ 一鍵重開:`bash scripts/qa/75-walkthrough.sh "$(mktemp -d)/qa75"`

這一輪驗的是 #75(#73 把可達性收回「名字在呼叫位置」時,綁定規則只認 `ast.Assign` + 裸 `Name`
target 一種形狀,同型的其他寫法全落在外面變誤紅)修完之後,#60 AC1 的原句逐條還成不成立。
範圍 = #75 的重現 scenario + 既有 regression suite。全程 bash xtrace,指令與輸出同一份,
沒有事後 render。

STEP 8–10 是本輪的同型全掃,兩把尺各量一遍:
- 尺一 `bindings_in` —「呼叫這個名字 = 呼叫右邊那個名字」這個 claim,換任何寫法都是同一形狀。
- 尺二「header 本身會跑」—— #75 對 `for` 補了 header 節點,同型的 `if` / `elif` / `while` /
  `with` / decorator 也都是會執行的位置。
- 反方向 —— 這次放寬有沒有讓「綁了但沒被呼叫」變 live(守門閉嘴)。

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
+ echo '==== STEP 2  #75 的重現 scenario 原樣重跑(票上的母體 6)===='
==== STEP 2  #75 的重現 scenario 原樣重跑(票上的母體 6)====
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --binding
對照:alias `f = dump; f()`(#71 修好的形狀,不得誤紅)                  期望 GREEN  實際 GREEN  ok
for 迴圈變數 `for f in [dump]: f()`                           期望 GREEN  實際 GREEN  ok
tuple 解包 `a, b = dump, dump; a()`                         期望 GREEN  實際 GREEN  ok
帶型別註記的綁定 `f: object = dump; f()`                          期望 GREEN  實際 GREEN  ok
factory 回傳 callable `def get(): return dump` + `get()()`  期望 GREEN  實際 GREEN  ok
class 屬性 `class W: run = dump` + `W.run()`                期望 GREEN  實際 GREEN  ok

母體 6,不合 0
+ echo '==== STEP 3  對照組:同一組 case 在 #75 修之前(39003a3)5 條誤紅 ===='
==== STEP 3  對照組:同一組 case 在 #75 修之前(39003a3)5 條誤紅 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --binding --prev75
對照:alias `f = dump; f()`(#71 修好的形狀,不得誤紅)                  期望 GREEN  實際 GREEN  ok
for 迴圈變數 `for f in [dump]: f()`                           期望 GREEN  實際 RED    MISMATCH
tuple 解包 `a, b = dump, dump; a()`                         期望 GREEN  實際 RED    MISMATCH
帶型別註記的綁定 `f: object = dump; f()`                          期望 GREEN  實際 RED    MISMATCH
factory 回傳 callable `def get(): return dump` + `get()()`  期望 GREEN  實際 RED    MISMATCH
class 屬性 `class W: run = dump` + `W.run()`                期望 GREEN  實際 RED    MISMATCH

母體 6,不合 5
+ echo 'exit 1  <- 非 0 是要的:對照組該紅'
exit 1  <- 非 0 是要的:對照組該紅
+ set -e
+ echo '==== STEP 4  票上宣稱的 mutation 咬合:四個旋鈕逐一還原 -> self-check 要轉紅 ===='
==== STEP 4  票上宣稱的 mutation 咬合:四個旋鈕逐一還原 -> self-check 要轉紅 ====
+ for M in bindings_in classbody own_scope mention
+ echo '---- 4.bindings_in'
---- 4.bindings_in
+ cp '/d/Self Project/Skills/scripts/validate.py' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo/scripts/validate.py
+ python - C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo bindings_in
mutation 已套用: bindings_in
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo/scripts/validate.py --self-check
+ tail -3
    a()
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:旋鈕一還原,self-check 就該紅'
exit 1  <- 非 0 是要的:旋鈕一還原,self-check 就該紅
+ set -e
+ for M in bindings_in classbody own_scope mention
+ echo '---- 4.classbody'
---- 4.classbody
+ cp '/d/Self Project/Skills/scripts/validate.py' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo/scripts/validate.py
+ python - C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo classbody
mutation 已套用: classbody
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo/scripts/validate.py --self-check
+ tail -3
    W.run()
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:旋鈕一還原,self-check 就該紅'
exit 1  <- 非 0 是要的:旋鈕一還原,self-check 就該紅
+ set -e
+ for M in bindings_in classbody own_scope mention
+ echo '---- 4.own_scope'
---- 4.own_scope
+ cp '/d/Self Project/Skills/scripts/validate.py' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo/scripts/validate.py
+ python - C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo own_scope
mutation 已套用: own_scope
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: a *nested* def returns it, only the outer one runs
+ echo 'exit 1  <- 非 0 是要的:旋鈕一還原,self-check 就該紅'
exit 1  <- 非 0 是要的:旋鈕一還原,self-check 就該紅
+ set -e
+ for M in bindings_in classbody own_scope mention
+ echo '---- 4.mention'
---- 4.mention
+ cp '/d/Self Project/Skills/scripts/validate.py' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo/scripts/validate.py
+ python - C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo mention
mutation 已套用: mention
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: `for` target bound, never called
+ echo 'exit 1  <- 非 0 是要的:旋鈕一還原,self-check 就該紅'
exit 1  <- 非 0 是要的:旋鈕一還原,self-check 就該紅
+ set -e
+ echo '==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===='
==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)====
+ cp '/d/Self Project/Skills/scripts/validate.py' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo/scripts/validate.py
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/98de3901-d14d-4302-a80e-a11cc06ec081/scratchpad/qa75/repo/scripts/validate.py --self-check
OK validate self-check green
+ echo '==== STEP 6  票上「不得放掉的天花板」逐條複驗 ===='
==== STEP 6  票上「不得放掉的天花板」逐條複驗 ====
+ echo '---- 6a  --live-overapprox(#73 立的:死碼 bypass 不得因撞名豁免)'
---- 6a  --live-overapprox(#73 立的:死碼 bypass 不得因撞名豁免)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --live-overapprox
死碼裡的 bypass + live 區提到名字(不是呼叫)   期望 RED    實際 RED    ok
死碼裡的 bypass + 剛好撞名的區域變數          期望 RED    實際 RED    ok
死碼裡的 bypass + 無關物件的同名 attribute  期望 RED    實際 RED    ok
對照:死碼裡的 bypass,名字沒被提到(#70 的天花板)  期望 RED    實際 RED    ok
對照:bypass 在真的被呼叫的 main()(不得誤紅)   期望 GREEN  實際 GREEN  ok

母體 5,不合 0
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
+ echo '---- 6c  --callgraph(alias / handler dict / callback 不得誤紅)'
---- 6c  --callgraph(alias / handler dict / callback 不得誤紅)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --callgraph
bypass 在 handler dict 裡被呼叫的 function(docstring 說仍算 live)  期望 GREEN  實際 GREEN  ok
bypass 在 alias 呼叫的 function(docstring 說仍算 live)           期望 GREEN  實際 GREEN  ok
bypass 當 callback 傳進去被呼叫(docstring 說仍算 live)              期望 GREEN  實際 GREEN  ok
bypass 在 class method,__main__ 直接呼叫(對照:.attr 名字對得上)       期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '---- 6d  --positional(#58 原病)'
---- 6d  --positional(#58 原病)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --positional
pin 在 main(),__main__ 只呼叫它      期望 RED    實際 RED    ok
pin 在 __main__ 之前的 top-level    期望 RED    實際 RED    ok
pin 真的在 __main__ block 裡        期望 GREEN  實際 GREEN  ok
pin 在 __main__ block 裡的 try 底下  期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '---- 6e  mention 預設全表'
---- 6e  mention 預設全表
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
+ echo '---- 6f  triage-to-maintain.py 的 error 數要 = 0'
---- 6f  triage-to-maintain.py 的 error 數要 = 0
+ python - '/d/Self Project/Skills'
triage-to-maintain.py 的 error 數 -> 0
+ echo '==== STEP 7  已開票的天花板複驗(known issues,期望維持不變)===='
==== STEP 7  已開票的天花板複驗(known issues,期望維持不變)====
+ set +e
+ echo '---- 7a  --pin-position(#72:可達性只裝在 bypass 那半)'
---- 7a  --pin-position(#72:可達性只裝在 bypass 那半)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --pin-position
+ tail -2

母體 6,不合 4
+ echo '---- 7b  --print-detect(#74:沒-print 豁免是 name-only)'
---- 7b  --print-detect(#74:沒-print 豁免是 name-only)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --print-detect
+ tail -2

母體 7,不合 5
+ echo '---- 7c  --skips(#66:SyntaxError 靜默跳過)'
---- 7c  --skips(#66:SyntaxError 靜默跳過)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --skips
+ tail -2

母體 3,不合 1
+ echo '---- 7d  --arg-widen(#74:引數即呼叫,改前改後應一樣)'
---- 7d  --arg-widen(#74:引數即呼叫,改前改後應一樣)
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --arg-widen
+ tail -2

母體 7,不合 5
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --arg-widen --prev75
+ tail -2

母體 7,不合 5
+ set -e
+ echo '==== STEP 8  本輪同型全掃(一):綁定的其他寫法 — 同一個 claim 換個寫法 ===='
==== STEP 8  本輪同型全掃(一):綁定的其他寫法 — 同一個 claim 換個寫法 ====
+ set +e
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
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#75 修之前(39003a3)'
---- 對照組:#75 修之前(39003a3)
+ python '/d/Self Project/Skills/scripts/qa/75-binding-sweep.py' '/d/Self Project/Skills' --binding-shapes --prev
+ tail -2

母體 12,不合 10
+ set -e
+ echo '==== STEP 9  本輪同型全掃(二):複合敘述的 header — #75 對 For 補的那條尺 ===='
==== STEP 9  本輪同型全掃(二):複合敘述的 header — #75 對 For 補的那條尺 ====
+ set +e
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
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#75 修之前(39003a3)'
---- 對照組:#75 修之前(39003a3)
+ python '/d/Self Project/Skills/scripts/qa/75-binding-sweep.py' '/d/Self Project/Skills' --header --prev
+ tail -2

母體 8,不合 6
+ set -e
+ echo '==== STEP 10  本輪同型全掃(三):放寬的代價 — 綁了但沒呼叫必須維持死 ===='
==== STEP 10  本輪同型全掃(三):放寬的代價 — 綁了但沒呼叫必須維持死 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/75-binding-sweep.py' '/d/Self Project/Skills' --bind-quiet
`for f in [dump]: pass` — 綁了沒呼叫                            期望 RED    實際 RED    ok
`class W: run = dump` — 沒人叫 W.run                          期望 RED    實際 RED    ok
`class W: run = dump` + 只提到 `W.run` 不呼叫                    期望 RED    實際 RED    ok
factory 沒人叫 `def get(): return dump`                       期望 RED    實際 RED    ok
巢狀 def 的 return,只有外層在跑                                     期望 RED    實際 RED    ok
死碼裡的 for 綁定 `if False: for f in [dump]: f()`               期望 RED    實際 RED    ok
死碼裡的 class body `if False: class W: run = dump` + W.run()  期望 RED    實際 RED    ok
except handler 裡的綁定(錯誤路徑,#70 的天花板)                         期望 RED    實際 RED    ok
`get()` 只呼叫 factory,沒呼叫結果(票上已宣告的天花板)                       期望 RED    實際 GREEN  MISMATCH
對照:factory 結果真的被呼叫 `get()()`(不得誤紅)                         期望 GREEN  實際 GREEN  ok
對照:`class W: run = dump` + `W.run()`(不得誤紅)                 期望 GREEN  實際 GREEN  ok

母體 11,不合 1
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#75 修之前(39003a3)'
---- 對照組:#75 修之前(39003a3)
+ python '/d/Self Project/Skills/scripts/qa/75-binding-sweep.py' '/d/Self Project/Skills' --bind-quiet --prev
+ tail -2

母體 11,不合 2
+ set -e
+ echo '==== STEP 11  repo 本體沒被動過 ===='
==== STEP 11  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
 M scripts/qa/73-reach-sweep.py
?? scripts/qa/75-binding-sweep.py
?? scripts/qa/75-walkthrough.sh
```
