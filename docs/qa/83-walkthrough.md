# `/qa #83` walkthrough — lambda 那面兩半用同一個 scope 邊界

**HEAD**: `6fb6fa3` ｜ 一鍵重開:`bash scripts/qa/83-walkthrough.sh "$(mktemp -d)/qa83"`

這一輪驗的是 #83(`own_scope` 停在 `Lambda`,同一行的 `names_in(n.value)` 沒停 —— lambda 綁的
名字進不了 `local`,`get()()` 一行就讓整檔豁免)修完之後,#60 AC1 的原句逐條還成不成立。
範圍 = #83 的重現 scenario + 既有 regression suite。全程 bash xtrace,指令與輸出同一份,
沒有事後 render。

**結論:判 fail,一條 blocking。**

- **AC1 後半(跑不到 → 不得豁免)**:票上母體 9 條全綠(修前 7 條誤放),六個 knob 逐一改壞
  self-check 全咬 —— 這張票宣稱的那一面真的收乾淨了。
- **AC1 前半(會跑到 → 得豁免)**:獨立 judge 判 **fail**。#83 新引入兩格誤紅
  (`return lambda: dump` 配 `get()()()`、`return lambda x=dump: x()` 配 `get()()`),
  `d192aa9` 上兩格都是 GREEN。方向是吵不是漏,票上已寫進 `free_in` 的 ponytail 註,
  開 known issue 票。
- **本輪同型全掃(STEP 8)**:拿 #83 自己的尺 —「lambda body 是 deferred code,被呼叫才算跑」
  — 量到 `live_nodes` 那一面,**還有 7 格誤放**(母體 11)。`--prev83`(`d192aa9`)同一組
  數字一模一樣,不是這次改出來的。誤放是危險方向,開 blocking 票。

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
+ echo '==== STEP 2  #83 的重現 scenario 原樣重跑(票上的母體 9,修前 7 誤放)===='
==== STEP 2  #83 的重現 scenario 原樣重跑(票上的母體 9,修前 7 誤放)====
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
+ echo '==== STEP 3  對照組:#83 修之前(d192aa9)同一組 9 條裡 7 條誤放 ===='
==== STEP 3  對照組:#83 修之前(d192aa9)同一組 9 條裡 7 條誤放 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/81-lambda-sweep.py' '/d/Self Project/Skills' --lambda-scope --prev81
+ tail -2

母體 9,不合 7
+ echo 'exit 0  <- 非 0 是要的:對照組該紅'
exit 0  <- 非 0 是要的:對照組該紅
+ set -e
+ echo '==== STEP 4  票上宣稱的 mutation 咬合:六個 knob 逐一改壞 -> self-check 要轉紅 ===='
==== STEP 4  票上宣稱的 mutation 咬合:六個 knob 逐一改壞 -> self-check 要轉紅 ====
+ for M in names_in_walks_lambda free_in_no_shadow free_in_no_default free_in_all_defaults bindings_in_branch live_nodes_branch
+ echo '---- 4.names_in_walks_lambda'
---- 4.names_in_walks_lambda
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py
+ python - /tmp/tmp.wiAGU91cqG/qa83/repo names_in_walks_lambda
mutation 已套用: names_in_walks_lambda
+ set +e
+ python /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: lambda scope: return (lambda dump: dump)(1)
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_walks_lambda free_in_no_shadow free_in_no_default free_in_all_defaults bindings_in_branch live_nodes_branch
+ echo '---- 4.free_in_no_shadow'
---- 4.free_in_no_shadow
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py
+ python - /tmp/tmp.wiAGU91cqG/qa83/repo free_in_no_shadow
mutation 已套用: free_in_no_shadow
+ set +e
+ python /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: lambda scope: return (lambda dump: dump)(1)
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_walks_lambda free_in_no_shadow free_in_no_default free_in_all_defaults bindings_in_branch live_nodes_branch
+ echo '---- 4.free_in_no_default'
---- 4.free_in_no_default
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py
+ python - /tmp/tmp.wiAGU91cqG/qa83/repo free_in_no_default
mutation 已套用: free_in_no_default
+ set +e
+ python /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py --self-check
+ tail -3
    get()
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_walks_lambda free_in_no_shadow free_in_no_default free_in_all_defaults bindings_in_branch live_nodes_branch
+ echo '---- 4.free_in_all_defaults'
---- 4.free_in_all_defaults
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py
+ python - /tmp/tmp.wiAGU91cqG/qa83/repo free_in_all_defaults
mutation 已套用: free_in_all_defaults
+ set +e
+ python /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: lambda scope: return f()
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_walks_lambda free_in_no_shadow free_in_no_default free_in_all_defaults bindings_in_branch live_nodes_branch
+ echo '---- 4.bindings_in_branch'
---- 4.bindings_in_branch
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py
+ python - /tmp/tmp.wiAGU91cqG/qa83/repo bindings_in_branch
mutation 已套用: bindings_in_branch
+ set +e
+ python /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py --self-check
+ tail -3
    get()()
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_walks_lambda free_in_no_shadow free_in_no_default free_in_all_defaults bindings_in_branch live_nodes_branch
+ echo '---- 4.live_nodes_branch'
---- 4.live_nodes_branch
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py
+ python - /tmp/tmp.wiAGU91cqG/qa83/repo live_nodes_branch
mutation 已套用: live_nodes_branch
+ set +e
+ python /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py --self-check
+ tail -3
    get()()
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ echo '==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===='
==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)====
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py
+ python /tmp/tmp.wiAGU91cqG/qa83/repo/scripts/validate.py --self-check
OK validate self-check green
+ echo '==== STEP 6  票上「不得放掉的天花板」逐條複驗 ===='
==== STEP 6  票上「不得放掉的天花板」逐條複驗 ====
+ echo '---- 6a  --own-names(#81,13/0)'
---- 6a  --own-names(#81,13/0)
+ python '/d/Self Project/Skills/scripts/qa/79-return-sweep.py' '/d/Self Project/Skills' --own-names
+ tail -2

母體 13,不合 0
+ echo '---- 6b  --return-carry(#79,6/0)'
---- 6b  --return-carry(#79,6/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --return-carry
+ tail -2

母體 6,不合 0
+ echo '---- 6c  --callgraph(4/0)'
---- 6c  --callgraph(4/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --callgraph
+ tail -2

母體 4,不合 0
+ echo '---- 6d  --live-overapprox(5/0)'
---- 6d  --live-overapprox(5/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --live-overapprox
+ tail -2

母體 5,不合 0
+ echo '---- 6e  --bypass-position(6/0)'
---- 6e  --bypass-position(6/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --bypass-position
+ tail -2

母體 6,不合 0
+ echo '---- 6f  --mention(13/0)'
---- 6f  --mention(13/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills'
+ tail -2

母體 13,不合 0
+ echo '---- 6g  --positional(#58 原病,4/0)'
---- 6g  --positional(#58 原病,4/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --positional
+ tail -2

母體 4,不合 0
+ echo '---- 6h  #73 的三把尺(6/0 ×3)'
---- 6h  #73 的三把尺(6/0 ×3)
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --reach-shapes
+ tail -2

母體 6,不合 0
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --call-position
+ tail -2

母體 6,不合 0
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --alias
+ tail -2

母體 6,不合 0
+ echo '---- 6i  #75 的 --bind-quiet(11/0)'
---- 6i  #75 的 --bind-quiet(11/0)
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
+ echo '==== STEP 8  本輪同型全掃:lambda body 是 deferred code,live_nodes 那面沒停在 Lambda ===='
==== STEP 8  本輪同型全掃:lambda body 是 deferred code,live_nodes 那面沒停在 Lambda ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/83-deferred-sweep.py' '/d/Self Project/Skills' --deferred
綁著沒呼叫 `f = lambda: dump()`                                               期望 RED    實際 GREEN  MISMATCH
list 裡的 lambda 沒呼叫 `xs = [lambda: dump()]`                               期望 RED    實際 GREEN  MISMATCH
dict 裡的 lambda 沒呼叫 `d = {"k": lambda: dump()}`                           期望 RED    實際 GREEN  MISMATCH
裸 lambda literal 在 live 位置沒呼叫 `(lambda: dump())`                         期望 RED    實際 GREEN  MISMATCH
comprehension 裡的 lambda 沒呼叫 `[lambda: dump() for _ in []]`               期望 RED    實際 GREEN  MISMATCH
三元裡的 lambda 沒呼叫 `None if xs else (lambda: dump())`                       期望 RED    實際 GREEN  MISMATCH
def 內就地呼叫但結果丟掉 `return (lambda: dump)()` 配 `get()`                       期望 RED    實際 GREEN  MISMATCH
對照:`return (lambda: dump())()` 配 `get()` —— lambda 就地被呼叫、dump 真的跑(不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:`def g(cb=lambda: dump())` 預設引數,g 沒被呼叫(現在就是 RED,不得放掉)                 期望 RED    實際 RED    ok
對照:`f = lambda: dump()` 且真的 `f()`(不得誤紅)                                  期望 GREEN  實際 GREEN  ok
對照:`(lambda: dump())()` 就地呼叫(不得誤紅)                                       期望 GREEN  實際 GREEN  ok

母體 11,不合 7
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#83 修之前(d192aa9)—— 同樣 7 條,證明不是 regression'
---- 對照組:#83 修之前(d192aa9)—— 同樣 7 條,證明不是 regression
+ python '/d/Self Project/Skills/scripts/qa/83-deferred-sweep.py' '/d/Self Project/Skills' --deferred --prev83
+ tail -2

母體 11,不合 7
+ set -e
+ echo '==== STEP 9  repo 本體沒被動過 ===='
==== STEP 9  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
?? scripts/qa/83-deferred-sweep.py
?? scripts/qa/83-walkthrough.sh
```
