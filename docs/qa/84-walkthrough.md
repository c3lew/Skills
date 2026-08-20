# `/qa #84` walkthrough — lambda 邊界的第三面(live 語句的 walk 停在 Lambda)

**HEAD**: `b3f95b0` ｜ 一鍵重開:`bash scripts/qa/84-walkthrough.sh "$(mktemp -d)/qa84"`

這一輪驗的是 #84(`live_nodes` 把每個 live 語句 `ast.walk` 一遍,凡 `Call` 就把 func 算成
invoked —— 連沒人呼叫的 lambda body 裡的 Call 也照收,`f = lambda: dump()` 綁著沒呼叫就讓
整檔豁免守門)修完之後,#60 AC1 的原句逐條還成不成立。範圍 = #84 的重現 scenario +
既有 regression suite。全程 bash xtrace,指令與輸出同一份,沒有事後 render。

**結論:判 fail,一條 blocking。**

- **AC1 前半(會跑到 → 得豁免)**:獨立 judge 判 **pass**。所有「真的會執行到」的形狀一格
  沒誤紅(名字呼叫、就地呼叫、`sorted(key=…)`、`return (lambda: dump())()`)。regression
  suite 六條全綠,天花板十一把尺 + 73 三尺全數維持、known issue 紅字數逐格對過一格沒動 ——
  排除「靠放寬豁免換綠」。
- **AC1 後半(跑不到 → 不得豁免)**:票宣稱的那一面 judge 判 **pass**。母體 11 從修前
  7 誤放收到 1(六格全收),七個 knob 逐一 mutation 都咬得到 self-check、還原回綠 ——
  這條線是真的被咬住,不是巧合過關。第七格(`return (lambda: dump)()` 配 `get()`)票上
  **事先宣告**留在天花板、沒假裝修好,judge 判 known issue 不是 works-but-wrong。
- **本輪同型全掃(STEP 8)**:拿 #84 自己的尺 —「deferred code 的 body 寫在那裡,被呼叫 /
  消費的時候才跑」— 量到 Python 另一種 deferred code:**generator**。`nodes_in` 只
  `isinstance(n, ast.Lambda)` 才停,`GeneratorExp` 照走進去,generator function 被呼叫也
  只是建一個 generator、body 一行沒跑。母體 12,**6 格誤放**。`--prev84`(`4c58eab`)同一組
  數字一模一樣,不是這次改出來的。誤放是危險方向,而且「bypass 直接寫在沒人消費的 genexp
  body 裡」等於多打一組括號就整檔繞過守門 —— 比 lambda 天花板還好寫。開 blocking 票。

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
+ echo '==== STEP 2  #84 的重現 scenario 原樣重跑(票上的母體 11,修前 7 誤放)===='
==== STEP 2  #84 的重現 scenario 原樣重跑(票上的母體 11,修前 7 誤放)====
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
+ echo 'exit 1  <- 非 0 是要的:第七格是票上寫死的天花板,不改成 GREEN'
exit 1  <- 非 0 是要的:第七格是票上寫死的天花板,不改成 GREEN
+ set -e
+ echo '==== STEP 3  對照組:#84 修之前(4c58eab)同一組 11 條裡 7 條誤放 ===='
==== STEP 3  對照組:#84 修之前(4c58eab)同一組 11 條裡 7 條誤放 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/83-deferred-sweep.py' '/d/Self Project/Skills' --deferred --prev83
+ tail -2

母體 11,不合 7
+ echo 'exit 1  <- 非 0 是要的:對照組該紅'
exit 1  <- 非 0 是要的:對照組該紅
+ set -e
+ echo '==== STEP 4  票上宣稱的 mutation 咬合:七個 knob 逐一改壞 -> self-check 要轉紅 ===='
==== STEP 4  票上宣稱的 mutation 咬合:七個 knob 逐一改壞 -> self-check 要轉紅 ====
+ for M in nodes_in_no_lambda_stop nodes_in_no_defaults live_nodes_walk_invoked live_nodes_walk_return no_through no_callback_arg no_bound_lambda
+ echo '---- 4.nodes_in_no_lambda_stop'
---- 4.nodes_in_no_lambda_stop
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py
+ python - /tmp/tmp.0AzUzZe9qJ/qa84/repo nodes_in_no_lambda_stop
mutation 已套用: nodes_in_no_lambda_stop
+ set +e
+ python /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: uncalled lambda in a live statement: f = lambda: dump()
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in nodes_in_no_lambda_stop nodes_in_no_defaults live_nodes_walk_invoked live_nodes_walk_return no_through no_callback_arg no_bound_lambda
+ echo '---- 4.nodes_in_no_defaults'
---- 4.nodes_in_no_defaults
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py
+ python - /tmp/tmp.0AzUzZe9qJ/qa84/repo nodes_in_no_defaults
mutation 已套用: nodes_in_no_defaults
+ set +e
+ python /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py --self-check
+ tail -3
    get()
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in nodes_in_no_lambda_stop nodes_in_no_defaults live_nodes_walk_invoked live_nodes_walk_return no_through no_callback_arg no_bound_lambda
+ echo '---- 4.live_nodes_walk_invoked'
---- 4.live_nodes_walk_invoked
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py
+ python - /tmp/tmp.0AzUzZe9qJ/qa84/repo live_nodes_walk_invoked
mutation 已套用: live_nodes_walk_invoked
+ set +e
+ python /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: uncalled lambda in a live statement: f = lambda: dump()
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in nodes_in_no_lambda_stop nodes_in_no_defaults live_nodes_walk_invoked live_nodes_walk_return no_through no_callback_arg no_bound_lambda
+ echo '---- 4.live_nodes_walk_return'
---- 4.live_nodes_walk_return
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py
+ python - /tmp/tmp.0AzUzZe9qJ/qa84/repo live_nodes_walk_return
mutation 已套用: live_nodes_walk_return
+ set +e
+ python /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py --self-check
+ tail -3
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: bypass written inside an uncalled lambda body
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in nodes_in_no_lambda_stop nodes_in_no_defaults live_nodes_walk_invoked live_nodes_walk_return no_through no_callback_arg no_bound_lambda
+ echo '---- 4.no_through'
---- 4.no_through
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py
+ python - /tmp/tmp.0AzUzZe9qJ/qa84/repo no_through
mutation 已套用: no_through
+ set +e
+ python /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py --self-check
+ tail -3
    f()
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in nodes_in_no_lambda_stop nodes_in_no_defaults live_nodes_walk_invoked live_nodes_walk_return no_through no_callback_arg no_bound_lambda
+ echo '---- 4.no_callback_arg'
---- 4.no_callback_arg
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py
+ python - /tmp/tmp.0AzUzZe9qJ/qa84/repo no_callback_arg
mutation 已套用: no_callback_arg
+ set +e
+ python /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py --self-check
+ tail -3
    sorted([1], key=lambda v: dump())
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in nodes_in_no_lambda_stop nodes_in_no_defaults live_nodes_walk_invoked live_nodes_walk_return no_through no_callback_arg no_bound_lambda
+ echo '---- 4.no_bound_lambda'
---- 4.no_bound_lambda
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py
+ python - /tmp/tmp.0AzUzZe9qJ/qa84/repo no_bound_lambda
mutation 已套用: no_bound_lambda
+ set +e
+ python /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py --self-check
+ tail -3
    f()
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ echo '==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===='
==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)====
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py
+ python /tmp/tmp.0AzUzZe9qJ/qa84/repo/scripts/validate.py --self-check
OK validate self-check green
+ echo '==== STEP 6  票上「不得放掉的天花板」逐條複驗 ===='
==== STEP 6  票上「不得放掉的天花板」逐條複驗 ====
+ echo '---- 6a  --lambda-scope(#83,9/0)'
---- 6a  --lambda-scope(#83,9/0)
+ python '/d/Self Project/Skills/scripts/qa/81-lambda-sweep.py' '/d/Self Project/Skills' --lambda-scope
+ tail -2

母體 9,不合 0
+ echo '---- 6b  --own-names(#81,13/0)'
---- 6b  --own-names(#81,13/0)
+ python '/d/Self Project/Skills/scripts/qa/79-return-sweep.py' '/d/Self Project/Skills' --own-names
+ tail -2

母體 13,不合 0
+ echo '---- 6c  --return-carry(#79,6/0)'
---- 6c  --return-carry(#79,6/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --return-carry
+ tail -2

母體 6,不合 0
+ echo '---- 6d  --callgraph(4/0)'
---- 6d  --callgraph(4/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --callgraph
+ tail -2

母體 4,不合 0
+ echo '---- 6e  --live-overapprox(5/0)'
---- 6e  --live-overapprox(5/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --live-overapprox
+ tail -2

母體 5,不合 0
+ echo '---- 6f  --bypass-position(6/0)'
---- 6f  --bypass-position(6/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --bypass-position
+ tail -2

母體 6,不合 0
+ echo '---- 6g  --mention(13/0)'
---- 6g  --mention(13/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills'
+ tail -2

母體 13,不合 0
+ echo '---- 6h  --positional(#58 原病,4/0)'
---- 6h  --positional(#58 原病,4/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --positional
+ tail -2

母體 4,不合 0
+ echo '---- 6i  #73 的三把尺(6/0 ×3)'
---- 6i  #73 的三把尺(6/0 ×3)
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --reach-shapes
+ tail -2

母體 6,不合 0
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --call-position
+ tail -2

母體 6,不合 0
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --alias
+ tail -2

母體 6,不合 0
+ echo '---- 6j  #75 的 --bind-quiet(11/0)'
---- 6j  #75 的 --bind-quiet(11/0)
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
+ echo '---- 7e  --arg-widen(未修)'
---- 7e  --arg-widen(未修)
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --arg-widen
+ tail -2

母體 7,不合 5
+ echo '---- 7f  #75 的另兩把尺(#77 / #78,未修)'
---- 7f  #75 的另兩把尺(#77 / #78,未修)
+ python '/d/Self Project/Skills/scripts/qa/75-binding-sweep.py' '/d/Self Project/Skills' --binding-shapes
+ tail -2

母體 12,不合 6
+ python '/d/Self Project/Skills/scripts/qa/75-binding-sweep.py' '/d/Self Project/Skills' --header
+ tail -2

母體 8,不合 5
+ echo '---- 7g  #79 的 --result-called(#82,未修)'
---- 7g  #79 的 --result-called(#82,未修)
+ python '/d/Self Project/Skills/scripts/qa/79-return-sweep.py' '/d/Self Project/Skills' --result-called
+ tail -2

母體 14,不合 3
+ set -e
+ echo '==== STEP 8  本輪同型全掃:generator body 也是 deferred code,nodes_in 只停在 Lambda ===='
==== STEP 8  本輪同型全掃:generator body 也是 deferred code,nodes_in 只停在 Lambda ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/84-generator-sweep.py' '/d/Self Project/Skills' --generator
genexp 綁著沒消費 `g = (dump() for _ in [1])`                   期望 RED    實際 GREEN  MISMATCH
裸 genexp 在 live 語句 `(dump() for _ in [1])`                 期望 RED    實際 GREEN  MISMATCH
genexp 進容器沒消費 `xs = [(dump() for _ in [1])]`               期望 RED    實際 GREEN  MISMATCH
genexp 交給不消費的 def `keep(dump() for _ in [1])`              期望 RED    實際 GREEN  MISMATCH
generator function 呼叫了但沒 iterate `gen()`                   期望 RED    實際 GREEN  MISMATCH
bypass 直接寫在沒人消費的 genexp body 裡                             期望 RED    實際 GREEN  MISMATCH
對照:generator function 綁著沒呼叫(現在就是 RED,不得放掉)                 期望 RED    實際 RED    ok
對照:`sum(1 for _ in (dump() for _ in [1]))` 真的消費(不得誤紅)      期望 GREEN  實際 GREEN  ok
對照:`g = (dump() for _ in [1])` 之後 `list(g)`(不得誤紅)          期望 GREEN  實際 GREEN  ok
對照:`for _ in gen(): pass` 真的 iterate(不得誤紅)                 期望 GREEN  實際 GREEN  ok
對照:listcomp 不是 deferred,真的跑 `[dump() for _ in [1]]`(不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:bypass 寫在真的被消費的 genexp body(不得誤紅)                       期望 GREEN  實際 GREEN  ok

母體 12,不合 6
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#84 修之前(4c58eab)—— 同樣 6 條,證明不是 regression'
---- 對照組:#84 修之前(4c58eab)—— 同樣 6 條,證明不是 regression
+ python '/d/Self Project/Skills/scripts/qa/84-generator-sweep.py' '/d/Self Project/Skills' --generator --prev84
+ tail -2

母體 12,不合 6
+ set -e
+ echo '==== STEP 9  repo 本體沒被動過 ===='
==== STEP 9  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
?? scripts/qa/84-generator-sweep.py
?? scripts/qa/84-walkthrough.sh
```
