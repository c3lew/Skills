# `/qa #81` walkthrough — live def 的「自己產生的名字」擴成整面 binding

**HEAD**: `d41b7f8` ｜ 一鍵重開:`bash scripts/qa/81-walkthrough.sh "$(mktemp -d)/qa81"`

這一輪驗的是 #81(`live_nodes` 的 `local` 只認 `ast.Name` Store 與 `ast.arg` 兩種 node,
`import as` / `except as` / `match` capture / 巢狀 `class` 撞名一個死碼 def,`get()()` 一行
就讓整檔豁免)修完之後,#60 AC1 的原句逐條還成不成立。範圍 = #81 的重現 scenario +
既有 regression suite。全程 bash xtrace,指令與輸出同一份,沒有事後 render。

STEP 8 是本輪的同型全掃,拿修法自己立的尺量下去:
- 尺 —「def 內部產生的名字整面都要收」。`local` 是靠 `own_scope` 走出來的,而
  `own_scope` **停在** `Lambda`;同一個 `return` 的另一半 `names_in(n.value)` 卻照樣
  鑽進 lambda 的 body。兩邊不對稱 → lambda 綁的名字進不了 `local`,`get()()` 一行又
  變成整檔豁免的開關。`binds` 的 docstring 直接寫了「a `Lambda`'s args are unreachable
  because `own_scope` stops at one」—— 那句話是錯的。

**結論:blocking,判 fail。** 獨立 judge 判 AC1 後半 works-but-wrong(母體 9 有 7 條誤放)。
不是 #81 的 regression —— `--prev81`(`b43137f`,#81 修之前)同一組 9 條也是 7 條誤放,
是 #81 宣稱「收齊整面」時漏掉的同一面。開票 #83。

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
+ echo '==== STEP 2  #81 的重現 scenario 原樣重跑(票上的母體 13,修前 6 不合)===='
==== STEP 2  #81 的重現 scenario 原樣重跑(票上的母體 13,修前 6 不合)====
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
+ echo '==== STEP 3  對照組:#79 修之前(8beebc5)同一組 13 條裡 11 條誤放 ===='
==== STEP 3  對照組:#79 修之前(8beebc5)同一組 13 條裡 11 條誤放 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/79-return-sweep.py' '/d/Self Project/Skills' --own-names --prev
+ tail -2

母體 13,不合 11
+ echo 'exit 0  <- 非 0 是要的:對照組該紅'
exit 0  <- 非 0 是要的:對照組該紅
+ set -e
+ echo '==== STEP 4  票上宣稱的 mutation 咬合:binds 的 branch 逐一拿掉 -> self-check 要轉紅 ===='
==== STEP 4  票上宣稱的 mutation 咬合:binds 的 branch 逐一拿掉 -> self-check 要轉紅 ====
+ for M in alias funcclass excepthandler matchmapping typevar
+ echo '---- 4.alias'
---- 4.alias
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.ut8jIyaAgY/qa81/repo/scripts/validate.py
+ python - /tmp/tmp.ut8jIyaAgY/qa81/repo alias
mutation 已套用: alias
+ set +e
+ python /tmp/tmp.ut8jIyaAgY/qa81/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: what it returns is its own `import as`, colliding by name
+ echo 'exit 1  <- 非 0 是要的:branch 一拿掉,self-check 就該紅'
exit 1  <- 非 0 是要的:branch 一拿掉,self-check 就該紅
+ set -e
+ for M in alias funcclass excepthandler matchmapping typevar
+ echo '---- 4.funcclass'
---- 4.funcclass
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.ut8jIyaAgY/qa81/repo/scripts/validate.py
+ python - /tmp/tmp.ut8jIyaAgY/qa81/repo funcclass
mutation 已套用: funcclass
+ set +e
+ python /tmp/tmp.ut8jIyaAgY/qa81/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: what it returns is its own nested class, colliding by name
+ echo 'exit 1  <- 非 0 是要的:branch 一拿掉,self-check 就該紅'
exit 1  <- 非 0 是要的:branch 一拿掉,self-check 就該紅
+ set -e
+ for M in alias funcclass excepthandler matchmapping typevar
+ echo '---- 4.excepthandler'
---- 4.excepthandler
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.ut8jIyaAgY/qa81/repo/scripts/validate.py
+ python - /tmp/tmp.ut8jIyaAgY/qa81/repo excepthandler
mutation 已套用: excepthandler
+ set +e
+ python /tmp/tmp.ut8jIyaAgY/qa81/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: what it returns is its own `except as`, colliding by name
+ echo 'exit 1  <- 非 0 是要的:branch 一拿掉,self-check 就該紅'
exit 1  <- 非 0 是要的:branch 一拿掉,self-check 就該紅
+ set -e
+ for M in alias funcclass excepthandler matchmapping typevar
+ echo '---- 4.matchmapping'
---- 4.matchmapping
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.ut8jIyaAgY/qa81/repo/scripts/validate.py
+ python - /tmp/tmp.ut8jIyaAgY/qa81/repo matchmapping
mutation 已套用: matchmapping
+ set +e
+ python /tmp/tmp.ut8jIyaAgY/qa81/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: what it returns is its own `match` mapping rest, colliding by name
+ echo 'exit 1  <- 非 0 是要的:branch 一拿掉,self-check 就該紅'
exit 1  <- 非 0 是要的:branch 一拿掉,self-check 就該紅
+ set -e
+ for M in alias funcclass excepthandler matchmapping typevar
+ echo '---- 4.typevar'
---- 4.typevar
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.ut8jIyaAgY/qa81/repo/scripts/validate.py
+ python - /tmp/tmp.ut8jIyaAgY/qa81/repo typevar
mutation 已套用: typevar
+ set +e
+ python /tmp/tmp.ut8jIyaAgY/qa81/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: what it returns is its own type parameter, colliding by name
+ echo 'exit 1  <- 非 0 是要的:branch 一拿掉,self-check 就該紅'
exit 1  <- 非 0 是要的:branch 一拿掉,self-check 就該紅
+ set -e
+ echo '==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===='
==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)====
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.ut8jIyaAgY/qa81/repo/scripts/validate.py
+ python /tmp/tmp.ut8jIyaAgY/qa81/repo/scripts/validate.py --self-check
OK validate self-check green
+ echo '==== STEP 6  票上「不得放掉的天花板」逐條複驗 ===='
==== STEP 6  票上「不得放掉的天花板」逐條複驗 ====
+ echo '---- 6a  --return-carry(#79,6/0)'
---- 6a  --return-carry(#79,6/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --return-carry
+ tail -2

母體 6,不合 0
+ echo '---- 6b  --callgraph(4/0)'
---- 6b  --callgraph(4/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --callgraph
+ tail -2

母體 4,不合 0
+ echo '---- 6c  --live-overapprox(5/0)'
---- 6c  --live-overapprox(5/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --live-overapprox
+ tail -2

母體 5,不合 0
+ echo '---- 6d  --bypass-position(6/0)'
---- 6d  --bypass-position(6/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --bypass-position
+ tail -2

母體 6,不合 0
+ echo '---- 6e  --mention(13/0)'
---- 6e  --mention(13/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills'
+ tail -2

母體 13,不合 0
+ echo '---- 6f  --positional(#58 原病,4/0)'
---- 6f  --positional(#58 原病,4/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --positional
+ tail -2

母體 4,不合 0
+ echo '---- 6g  #73 的三把尺(6/0 ×3)'
---- 6g  #73 的三把尺(6/0 ×3)
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --reach-shapes
+ tail -2

母體 6,不合 0
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --call-position
+ tail -2

母體 6,不合 0
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --alias
+ tail -2

母體 6,不合 0
+ echo '---- 6h  #75 的 --bind-quiet(11/0)'
---- 6h  #75 的 --bind-quiet(11/0)
+ python '/d/Self Project/Skills/scripts/qa/75-binding-sweep.py' '/d/Self Project/Skills' --bind-quiet
+ tail -2

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
+ echo '---- 7f  #79 的 --result-called(#82,未修)'
---- 7f  #79 的 --result-called(#82,未修)
+ python '/d/Self Project/Skills/scripts/qa/79-return-sweep.py' '/d/Self Project/Skills' --result-called
+ tail -2

母體 14,不合 3
+ set -e
+ echo '==== STEP 8  本輪同型全掃:own_scope 停在 Lambda,names_in 沒停 ===='
==== STEP 8  本輪同型全掃:own_scope 停在 Lambda,names_in 沒停 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/81-lambda-sweep.py' '/d/Self Project/Skills' --lambda-scope
lambda 的參數撞名,馬上呼叫 `return (lambda dump: dump)(1)`              期望 RED    實際 GREEN  MISMATCH
lambda 存進變數再呼叫 `f = lambda dump: dump; return f(1)`            期望 RED    實際 GREEN  MISMATCH
交出去的就是 lambda 本身 `return lambda dump: dump`                    期望 RED    實際 GREEN  MISMATCH
交出去的 lambda 只是把 dump 再交出來 `return lambda: dump`                期望 RED    實際 GREEN  MISMATCH
dump 只當 lambda 的預設引數 `return lambda x=dump: x`                 期望 RED    實際 GREEN  MISMATCH
lambda 包在容器裡再取出來 `return (lambda: dump,)[0]`                   期望 RED    實際 GREEN  MISMATCH
巢狀 lambda `return (lambda: (lambda: dump))()`                  期望 RED    實際 GREEN  MISMATCH
對照:lambda 呼叫的結果真的是外面那個死碼 `f = lambda: dump; return f()`(不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:`return dump` 真的是外面那個死碼 def(不得誤紅)                           期望 GREEN  實際 GREEN  ok

母體 9,不合 7
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#81 修之前(b43137f)—— 同樣 7 條,證明不是 regression'
---- 對照組:#81 修之前(b43137f)—— 同樣 7 條,證明不是 regression
+ python '/d/Self Project/Skills/scripts/qa/81-lambda-sweep.py' '/d/Self Project/Skills' --lambda-scope --prev81
+ tail -2

母體 9,不合 7
+ set -e
+ echo '==== STEP 9  repo 本體沒被動過 ===='
==== STEP 9  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
?? scripts/qa/81-lambda-sweep.py
?? scripts/qa/81-walkthrough.sh
```
