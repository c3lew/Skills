# `/qa #86` walkthrough — deferred 邊界補上 generator 那面

**HEAD**: `de68088` ｜ 一鍵重開:`bash scripts/qa/86-walkthrough.sh "$(mktemp -d)/qa86"`

這一輪驗的是 #86(`nodes_in` 只停在 `Lambda`,`GeneratorExp` 照走進去、generator function 被
呼叫也算成 body 跑了 —— `g = (dump() for _ in [1])` 就讓整檔豁免)修完之後,#60 AC1 的原句
逐條還成不成立。範圍 = #86 的重現 scenario + 既有 regression suite。全程 bash xtrace,指令與
輸出同一份,沒有事後 render。

**結論:判 fail,兩條 blocking + 一條 known issue。**

- **AC1 後半(跑不到 → 不得豁免)**:票宣稱的那一面 judge 判 **pass**。母體 12 從修前 6 誤放
  收到 0(六格全收),十四個 knob 逐一 mutation 條條以真的 `AssertionError` 轉紅、還原回綠 ——
  這條線是真的被咬住,不是巧合過關。
- **AC1 前半(會跑到 → 得豁免)**:judge 判 **works-but-wrong**。STEP 2 那六格「不得誤紅」
  對照確實全 GREEN,但 STEP 9 證明它們過的理由是 fixture 剛好沒撞名 —— 檔案裡任何一個
  scope 冒出一個叫 `list` 的 binding(連 `if False:` 死碼分支裡的都算),同一句 `list(g)`
  就翻紅。
- **天花板**:STEP 6 十一張表、STEP 7 八張 known issue 表,**逐格**比對(不只總數)一格沒動,
  排除「靠放寬豁免換綠」與「修好一格同時弄壞一格」。
- **本輪同型全掃(STEP 8 / 9 / 10)**:拿 #86 自己的三把尺各量一遍,三面都量出東西:
  - **尺一,coroutine 也是 deferred body**(STEP 8):`gens` 只認 body 有 `yield` 的 def,
    `async def` 沒 yield 就不在名單上,`adump()` 建一個 coroutine 沒人 await 照樣算成跑過。
    母體 12,**5 格誤放**;`--prev86` 是 6,不是這次改壞的。**blocking**。
  - **尺三,`consumes` 的 method call 只認 attribute 名字**(STEP 10):不看 receiver 型別,
    `b.next(… for _ in [1])` 任何 import 進來的物件都能當開關。母體 6,**3 格誤放**;
    `--prev86` 是 4。修法自己在 docstring 宣告過這個洞、明講交給 QA 判 —— 量下去它是真的能翻
    的開關,照慣例(誤放 = blocking)開票。**blocking**。
  - **尺二,`shadowed` 走遍每一個 scope**(STEP 9):`set().union(*map(binds, ast.walk(tree)))`
    跟 docstring 寫的「the **module** binds itself」不符,別人 scope 的 local / param /
    `import as` / class attribute 撞名就把消費者名單劃掉。母體 11,**9 格誤紅**;`--prev86`
    只有 1 —— **是 `de68088` 帶進來的**。方向是誤紅(吵),照 #82 / #85 的慣例標
    **known issue**。

**兩位獨立 judge 對嚴重度有異議,列在這裡讓 client 決定**:兩輪 judge 都主張尺二(誤紅、本次
引入)要 blocking、尺一與尺三(誤放、非本次引入)降 known issue。本報告採**專案既有慣例**
—— 誤放讓守門閉嘴(危險)一律 blocking,誤紅是吵(#82 / #85 兩張都是「被驗的那顆 commit
自己引入的誤紅」,都標 known issue)。judge 沒被餵這條慣例,所以是在沒有先例的情況下判的。
要翻過來只需要在 demo 時說一聲。

**方法保留(judge 提的,沒開票)**:

- 三個 knob(`consumes_no_builtins` / `consumes_no_nested_gen` / `no_gen_fixpoint`)踩到同一條
  self-check fixture,所以「十四個 knob 條條咬合」的獨立辨識力實際是 12 個點,不是 14。
- 天花板表裡「哪一格被允許紅」的標籤是 sweep script 自己寫的字串,票上宣告的只有總數。這層
  不是獨立 oracle。

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
+ echo '==== STEP 2  #86 的重現 scenario 原樣重跑(票上的母體 12,修前 6 誤放)===='
==== STEP 2  #86 的重現 scenario 原樣重跑(票上的母體 12,修前 6 誤放)====
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
+ echo '==== STEP 3  對照組:#86 修之前(cb7e030)同一組 12 條裡 6 條誤放 ===='
==== STEP 3  對照組:#86 修之前(cb7e030)同一組 12 條裡 6 條誤放 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/84-generator-sweep.py' '/d/Self Project/Skills' --generator --prev86
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
+ echo 'exit 1  <- 非 0 是要的:對照組該紅'
exit 1  <- 非 0 是要的:對照組該紅
+ set -e
+ echo '==== STEP 4  票上宣稱的 mutation 咬合:十四個 knob 逐一改壞 -> self-check 要轉紅 ===='
==== STEP 4  票上宣稱的 mutation 咬合:十四個 knob 逐一改壞 -> self-check 要轉紅 ====
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.names_in_no_gen_stop'
---- 4.names_in_no_gen_stop
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo names_in_no_gen_stop
mutation 已套用: names_in_no_gen_stop
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1673, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1553, in self_check
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: unconsumed generator: handed to a def that does not consume it
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.names_in_no_first_iter'
---- 4.names_in_no_first_iter
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo names_in_no_first_iter
mutation 已套用: names_in_no_first_iter
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1675, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1638, in self_check
    assert stream_encoding_issues(repo) == [], alive
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: def dump():
    sys.stdout.buffer.write(b'x')


f = lambda: sum(x for x in dump())
if __name__ == "__main__":
    f()
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.nodes_in_no_gen_stop'
---- 4.nodes_in_no_gen_stop
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo nodes_in_no_gen_stop
mutation 已套用: nodes_in_no_gen_stop
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1673, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1553, in self_check
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: unconsumed generator: g = (dump() for _ in [1])
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.nodes_in_no_first_iter'
---- 4.nodes_in_no_first_iter
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo nodes_in_no_first_iter
mutation 已套用: nodes_in_no_first_iter
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1675, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1638, in self_check
    assert stream_encoding_issues(repo) == [], alive
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: def dump():
    sys.stdout.buffer.write(b'x')


g = (x for x in dump())
if __name__ == "__main__":
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.consumes_no_builtins'
---- 4.consumes_no_builtins
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo consumes_no_builtins
mutation 已套用: consumes_no_builtins
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1672, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1635, in self_check
    assert stream_encoding_issues(repo) == [], alive
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: def dump():
    sys.stdout.buffer.write(b'x')


if __name__ == "__main__":
    sum(1 for _ in (dump() for _ in [1]))
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.consumes_no_for'
---- 4.consumes_no_for
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo consumes_no_for
mutation 已套用: consumes_no_for
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1637, in self_check
    assert stream_encoding_issues(repo) == [], alive
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: def dump():
    sys.stdout.buffer.write(b'x')


def gen():
    yield dump()


if __name__ == "__main__":
    for _ in gen():
        pass
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.consumes_no_nested_gen'
---- 4.consumes_no_nested_gen
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo consumes_no_nested_gen
mutation 已套用: consumes_no_nested_gen
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1676, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1639, in self_check
    assert stream_encoding_issues(repo) == [], alive
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: def dump():
    sys.stdout.buffer.write(b'x')


if __name__ == "__main__":
    sum(1 for _ in (dump() for _ in [1]))
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.consumes_no_comp'
---- 4.consumes_no_comp
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo consumes_no_comp
mutation 已套用: consumes_no_comp
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1674, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1637, in self_check
    assert stream_encoding_issues(repo) == [], alive
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: def dump():
    sys.stdout.buffer.write(b'x')


if __name__ == "__main__":
    [y for y in (dump() for _ in [1])]
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.consumes_no_shadow'
---- 4.consumes_no_shadow
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo consumes_no_shadow
mutation 已套用: consumes_no_shadow
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1676, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1556, in self_check
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: unconsumed generator: a def shadowing a consumer does not consume
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.gens_not_subtracted'
---- 4.gens_not_subtracted
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo gens_not_subtracted
mutation 已套用: gens_not_subtracted
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1676, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1556, in self_check
    assert len(stream_encoding_issues(repo)) == 1, label
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: unconsumed generator: generator def called, never iterated
+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.no_eaten_calls'
---- 4.no_eaten_calls
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo no_eaten_calls
mutation 已套用: no_eaten_calls
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1637, in self_check
    assert stream_encoding_issues(repo) == [], alive
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: def dump():
    sys.stdout.buffer.write(b'x')


def gen():
    yield dump()


if __name__ == "__main__":
    for _ in gen():
        pass
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.no_eaten_via_name'
---- 4.no_eaten_via_name
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo no_eaten_via_name
mutation 已套用: no_eaten_via_name
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1674, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1637, in self_check
    assert stream_encoding_issues(repo) == [], alive
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: def dump():
    sys.stdout.buffer.write(b'x')


g = (dump() for _ in [1])
if __name__ == "__main__":
    list(g)
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.through_no_gens'
---- 4.through_no_gens
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo through_no_gens
mutation 已套用: through_no_gens
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1676, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1639, in self_check
    assert stream_encoding_issues(repo) == [], alive
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: if __name__ == "__main__":
    list(sys.stdout.buffer.write(b'x') for _ in [1])
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop nodes_in_no_first_iter consumes_no_builtins consumes_no_for consumes_no_nested_gen consumes_no_comp consumes_no_shadow gens_not_subtracted no_eaten_calls no_eaten_via_name through_no_gens no_gen_fixpoint
+ echo '---- 4.no_gen_fixpoint'
---- 4.no_gen_fixpoint
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python '/d/Self Project/Skills/scripts/qa/86-mutate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo no_gen_fixpoint
mutation 已套用: no_gen_fixpoint
+ set +e
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
+ tail -18
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1676, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.6oDZpUUnNq\qa86\repo\scripts\validate.py", line 1639, in self_check
    assert stream_encoding_issues(repo) == [], alive
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: def dump():
    sys.stdout.buffer.write(b'x')


if __name__ == "__main__":
    sum(1 for _ in (dump() for _ in [1]))
    print('�n�}')

+ echo 'exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅'
exit 1  <- 非 0 是要的:knob 一改壞,self-check 就該紅
+ set -e
+ echo '==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===='
==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)====
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py
+ python /tmp/tmp.6oDZpUUnNq/qa86/repo/scripts/validate.py --self-check
OK validate self-check green
+ echo '==== STEP 6  票上「不得放掉的天花板」逐條複驗 ===='
==== STEP 6  票上「不得放掉的天花板」逐條複驗 ====
+ echo '---- 6a  --deferred(#84,11/1,第七格是宣告過的天花板)'
---- 6a  --deferred(#84,11/1,第七格是宣告過的天花板)
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
+ echo '---- 6b  --lambda-scope(#83,9/0)'
---- 6b  --lambda-scope(#83,9/0)
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
+ echo '---- 6c  --own-names(#81,13/0)'
---- 6c  --own-names(#81,13/0)
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
+ echo '---- 6d  --return-carry(#79,6/0)'
---- 6d  --return-carry(#79,6/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --return-carry
死碼 bypass + `def get(): return dump`,`get()` 結果直接丟掉  期望 RED    實際 RED    ok
同上,回傳值存進變數但從未呼叫(`x = get()`)                         期望 RED    實際 RED    ok
get() 回傳的是自己的區域變數,只是剛好撞名死碼 def                       期望 RED    實際 RED    ok
對照:回傳值真的被呼叫 `get()()`(#75 立的天花板,不得誤紅)                期望 GREEN  實際 GREEN  ok
對照:回傳值存進變數後才呼叫 `f = get(); f()`(#79 的天花板,不得誤紅)       期望 GREEN  實際 GREEN  ok
對照:`get` 自己也沒被呼叫(死碼,必須維持 RED)                        期望 RED    實際 RED    ok

母體 6,不合 0
+ echo '---- 6e  --callgraph(4/0)'
---- 6e  --callgraph(4/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --callgraph
bypass 在 handler dict 裡被呼叫的 function(docstring 說仍算 live)  期望 GREEN  實際 GREEN  ok
bypass 在 alias 呼叫的 function(docstring 說仍算 live)           期望 GREEN  實際 GREEN  ok
bypass 當 callback 傳進去被呼叫(docstring 說仍算 live)              期望 GREEN  實際 GREEN  ok
bypass 在 class method,__main__ 直接呼叫(對照:.attr 名字對得上)       期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '---- 6f  --live-overapprox(5/0)'
---- 6f  --live-overapprox(5/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --live-overapprox
死碼裡的 bypass + live 區提到名字(不是呼叫)   期望 RED    實際 RED    ok
死碼裡的 bypass + 剛好撞名的區域變數          期望 RED    實際 RED    ok
死碼裡的 bypass + 無關物件的同名 attribute  期望 RED    實際 RED    ok
對照:死碼裡的 bypass,名字沒被提到(#70 的天花板)  期望 RED    實際 RED    ok
對照:bypass 在真的被呼叫的 main()(不得誤紅)   期望 GREEN  實際 GREEN  ok

母體 5,不合 0
+ echo '---- 6g  --bypass-position(6/0)'
---- 6g  --bypass-position(6/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --bypass-position
bypass 在從未被呼叫的 function 內                                  期望 RED    實際 RED    ok
bypass 在 `if False:` 死碼裡                                   期望 RED    實際 RED    ok
bypass 只出現在跑不到的 except 分支                                  期望 RED    實際 RED    ok
bypass 在 `raise SystemExit` 之後的死碼                          期望 RED    實際 RED    ok
bypass 真的在 __main__ 裡用(不得誤紅)                               期望 GREEN  實際 GREEN  ok
bypass 在 main(),__main__ 呼叫它(triage-to-maintain 的形狀,不得誤紅)  期望 GREEN  實際 GREEN  ok

母體 6,不合 0
+ echo '---- 6h  --mention(13/0)'
---- 6h  --mention(13/0)
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
+ echo '---- 6i  --positional(#58 原病,4/0)'
---- 6i  --positional(#58 原病,4/0)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --positional
pin 在 main(),__main__ 只呼叫它      期望 RED    實際 RED    ok
pin 在 __main__ 之前的 top-level    期望 RED    實際 RED    ok
pin 真的在 __main__ block 裡        期望 GREEN  實際 GREEN  ok
pin 在 __main__ block 裡的 try 底下  期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '---- 6j  #73 的三把尺(6/0 ×3)'
---- 6j  #73 的三把尺(6/0 ×3)
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
+ echo '---- 6k  #75 的 --bind-quiet(11/0)'
---- 6k  #75 的 --bind-quiet(11/0)
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
+ echo '---- 7a  --pin-position(#72,6/4)'
---- 7a  --pin-position(#72,6/4)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --pin-position
pin 在 __main__ 內的 `if False:` 死碼裡          期望 RED    實際 GREEN  MISMATCH
pin 在 __main__ 內 `raise SystemExit` 之後的死碼  期望 RED    實際 GREEN  MISMATCH
pin 在 __main__ 內定義但沒人呼叫的 nested def        期望 RED    實際 GREEN  MISMATCH
pin 只出現在跑不到的 except 分支                     期望 RED    實際 GREEN  MISMATCH
pin 真的在 __main__ block 裡(不得誤紅)             期望 GREEN  實際 GREEN  ok
pin 在 block 內的 try body 裡(不得誤紅)            期望 GREEN  實際 GREEN  ok

母體 6,不合 4
+ echo '---- 7b  --print-detect(#74,7/5)'
---- 7b  --print-detect(#74,7/5)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --print-detect
print 用 alias 呼叫(p = print; p(中文))                 期望 RED    實際 GREEN  MISMATCH
print 走 builtins(builtins.print(中文))               期望 RED    實際 GREEN  MISMATCH
print 當 callback 傳進去(run(print))                   期望 RED    實際 GREEN  MISMATCH
print 放在 handler dict 裡(H = {p: print}; H[p](中文))  期望 RED    實際 GREEN  MISMATCH
sys.stdout.write(中文)(build 已宣告的天花板)                期望 RED    實際 GREEN  MISMATCH
對照:真的裸 print(,沒 pin(不得漏放)                          期望 RED    實際 RED    ok
對照:真的完全不印 console(不得誤紅)                            期望 GREEN  實際 GREEN  ok

母體 7,不合 5
+ echo '---- 7c  --skips(#66,3/1)'
---- 7c  --skips(#66,3/1)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --skips
__main__ 縮排在 try 底下 -> 找不到 top-level If,整檔跳過           期望 RED    實際 RED    ok
__main__ 縮排在 if True 底下 -> 同上                          期望 RED    實際 RED    ok
檔案 parse 不過(SyntaxError)-> 整檔跳過(build 已在 code 裡註明的取捨)  期望 RED    實際 GREEN  MISMATCH

母體 3,不合 1
+ echo '---- 7d  --name-collision(#80,4/3)'
---- 7d  --name-collision(#80,4/3)
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --name-collision
死碼 bypass 在沒被實例化的 class method,module 同名 def 被呼叫  期望 RED    實際 GREEN  MISMATCH
死碼 bypass 在後面重新定義的同名 def,被呼叫的是前面那個                期望 RED    實際 GREEN  MISMATCH
對照:死碼 bypass 的 def 沒有同名雙胞胎(#70 的天花板)              期望 RED    實際 RED    ok
對照:同名 def 但被呼叫的就是帶 bypass 的那個(不得誤紅)               期望 GREEN  實際 RED    MISMATCH

母體 4,不合 3
+ echo '---- 7e  --arg-widen(7/5)'
---- 7e  --arg-widen(7/5)
+ python '/d/Self Project/Skills/scripts/qa/73-reach-sweep.py' '/d/Self Project/Skills' --arg-widen
對照:`run(dump)`,run 真的呼叫它(#71 的 callback,不得誤紅)  期望 GREEN  實際 GREEN  ok
對照:名字完全沒被提到(#70 的天花板)                          期望 RED    實際 RED    ok
`print(dump)` — 印出 function 物件,沒有呼叫它           期望 RED    實際 GREEN  MISMATCH
`x = str(dump)` — 引數,但 str 不會呼叫它               期望 RED    實際 GREEN  MISMATCH
`x = len([dump])` — 名字包在 list 裡當引數             期望 RED    實際 GREEN  MISMATCH
`print(f"{dump}")` — 名字在 f-string 的引數裡         期望 RED    實際 GREEN  MISMATCH
`isinstance(dump, object)` — 關鍵字/位置引數都一樣       期望 RED    實際 GREEN  MISMATCH

母體 7,不合 5
+ echo '---- 7f  #75 的另兩把尺(#77 12/6 / #78 8/5)'
---- 7f  #75 的另兩把尺(#77 12/6 / #78 8/5)
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
+ echo '---- 7g  #79 的 --result-called(#82,14/3)'
---- 7g  #79 的 --result-called(#82,14/3)
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
+ set -e
+ echo '==== STEP 8  同型全掃 尺一(誤放):coroutine 也是 deferred body,gens 只認 yield ===='
==== STEP 8  同型全掃 尺一(誤放):coroutine 也是 deferred body,gens 只認 yield ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' '/d/Self Project/Skills' --async-defer
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
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#86 修之前(cb7e030)—— 6 條,#86 收掉的是 async generator 那格,剩 5 條不是 regression'
---- 對照組:#86 修之前(cb7e030)—— 6 條,#86 收掉的是 async generator 那格,剩 5 條不是 regression
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' '/d/Self Project/Skills' --async-defer --prev86
coroutine 綁著沒 await `c = adump()`                        期望 RED    實際 GREEN  MISMATCH
裸 coroutine 在 live 語句 `adump()`                          期望 RED    實際 GREEN  MISMATCH
coroutine 進容器沒 await `xs = [adump()]`                    期望 RED    實際 GREEN  MISMATCH
coroutine 交給不 await 的 def `keep(adump())`                期望 RED    實際 GREEN  MISMATCH
bypass 直接寫在呼叫了但沒 await 的 async def body 裡                期望 RED    實際 GREEN  MISMATCH
對照:async def 綁著沒呼叫(現在就是 RED,不得放掉)                        期望 RED    實際 RED    ok
對照:async generator 呼叫了沒 iterate `agen()`(現在就是 RED,不得放掉)  期望 RED    實際 GREEN  MISMATCH
對照:`await adump()` 只在沒人跑的 outer 裡(現在就是 RED,不得放掉)         期望 RED    實際 RED    ok
對照:`asyncio.run(adump())` 真的跑(不得誤紅)                      期望 GREEN  實際 GREEN  ok
對照:`await adump()` 在被 `asyncio.run` 的 outer 裡(不得誤紅)      期望 GREEN  實際 GREEN  ok
對照:bypass 寫在真的被 run 的 coroutine body(不得誤紅)               期望 GREEN  實際 GREEN  ok
對照:`async for _ in agen()` 真的 iterate(不得誤紅)              期望 GREEN  實際 GREEN  ok

母體 12,不合 6
+ set -e
+ echo '==== STEP 9  同型全掃 尺二(誤紅):shadowed 走遍每個 scope,不只模組自己綁的 ===='
==== STEP 9  同型全掃 尺二(誤紅):shadowed 走遍每個 scope,不只模組自己綁的 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' '/d/Self Project/Skills' --shadow-scope
別的 def 裡的 local 叫 list `def u(): list = 1`               期望 GREEN  實際 RED    MISMATCH
別的 def 的 parameter 叫 list `def u(list)`                  期望 GREEN  實際 RED    MISMATCH
comprehension target 叫 list `[list for list in []]`      期望 GREEN  實際 RED    MISMATCH
`with … as list` 在別的 def 裡                               期望 GREEN  實際 RED    MISMATCH
`except … as list` 在別的 def 裡                             期望 GREEN  實際 RED    MISMATCH
class body 裡的 attribute 叫 list `class W: list = 1`       期望 GREEN  實際 RED    MISMATCH
import alias 叫 list `import json as list`                期望 GREEN  實際 RED    MISMATCH
巢狀 def 叫 list `def u(): def list(): …`                   期望 GREEN  實際 RED    MISMATCH
連死碼分支裡的 for target 都算 `if False: for list in []`         期望 GREEN  實際 RED    MISMATCH
對照:模組真的 `def sorted(g): return g`(#86 review 收的那條,不得放掉)  期望 RED    實際 RED    ok
對照:沒有任何撞名,`list(g)` 照常消費(不得誤紅)                           期望 GREEN  實際 GREEN  ok

母體 11,不合 9
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#86 修之前(cb7e030)—— 那九格全 GREEN,這九條誤紅是 de68088 帶進來的'
---- 對照組:#86 修之前(cb7e030)—— 那九格全 GREEN,這九條誤紅是 de68088 帶進來的
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' '/d/Self Project/Skills' --shadow-scope --prev86
別的 def 裡的 local 叫 list `def u(): list = 1`               期望 GREEN  實際 GREEN  ok
別的 def 的 parameter 叫 list `def u(list)`                  期望 GREEN  實際 GREEN  ok
comprehension target 叫 list `[list for list in []]`      期望 GREEN  實際 GREEN  ok
`with … as list` 在別的 def 裡                               期望 GREEN  實際 GREEN  ok
`except … as list` 在別的 def 裡                             期望 GREEN  實際 GREEN  ok
class body 裡的 attribute 叫 list `class W: list = 1`       期望 GREEN  實際 GREEN  ok
import alias 叫 list `import json as list`                期望 GREEN  實際 GREEN  ok
巢狀 def 叫 list `def u(): def list(): …`                   期望 GREEN  實際 GREEN  ok
連死碼分支裡的 for target 都算 `if False: for list in []`         期望 GREEN  實際 GREEN  ok
對照:模組真的 `def sorted(g): return g`(#86 review 收的那條,不得放掉)  期望 RED    實際 GREEN  MISMATCH
對照:沒有任何撞名,`list(g)` 照常消費(不得誤紅)                           期望 GREEN  實際 GREEN  ok

母體 11,不合 1
+ set -e
+ echo '==== STEP 10  同型全掃 尺三(誤放):consumes 的 method call 只認 attribute 名字 ===='
==== STEP 10  同型全掃 尺三(誤放):consumes 的 method call 只認 attribute 名字 ====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' '/d/Self Project/Skills' --attr-consumer
import 進來的物件 `.extend(genexp)`,它根本不抽乾                         期望 RED    實際 GREEN  MISMATCH
bypass 直接寫在交給 `.extend` 的 genexp body 裡                       期望 RED    實際 GREEN  MISMATCH
bypass 交給 `.next` —— 名單上任一個名字當 method 都行                      期望 RED    實際 GREEN  MISMATCH
對照:同模組自己 `class B: def extend`(被尺二那個過寬的 shadowed 擋掉,現在是 RED)  期望 RED    實際 RED    ok
對照:真的 `"".join(…)`(修法留下 attribute 判讀的理由,不得誤紅)                 期望 GREEN  實際 GREEN  ok
對照:真的 `list.extend(…)`(不得誤紅)                                  期望 GREEN  實際 GREEN  ok

母體 6,不合 3
+ echo 'exit 1  <- 非 0 是本輪 finding'
exit 1  <- 非 0 是本輪 finding
+ echo '---- 對照組:#86 修之前(cb7e030)—— 4 條,#86 靠尺二那個過寬的 shadowed 誤打誤撞收掉一格'
---- 對照組:#86 修之前(cb7e030)—— 4 條,#86 靠尺二那個過寬的 shadowed 誤打誤撞收掉一格
+ python '/d/Self Project/Skills/scripts/qa/86-async-sweep.py' '/d/Self Project/Skills' --attr-consumer --prev86
import 進來的物件 `.extend(genexp)`,它根本不抽乾                         期望 RED    實際 GREEN  MISMATCH
bypass 直接寫在交給 `.extend` 的 genexp body 裡                       期望 RED    實際 GREEN  MISMATCH
bypass 交給 `.next` —— 名單上任一個名字當 method 都行                      期望 RED    實際 GREEN  MISMATCH
對照:同模組自己 `class B: def extend`(被尺二那個過寬的 shadowed 擋掉,現在是 RED)  期望 RED    實際 GREEN  MISMATCH
對照:真的 `"".join(…)`(修法留下 attribute 判讀的理由,不得誤紅)                 期望 GREEN  實際 GREEN  ok
對照:真的 `list.extend(…)`(不得誤紅)                                  期望 GREEN  實際 GREEN  ok

母體 6,不合 4
+ set -e
+ echo '==== STEP 11  對照組不是模擬:--prev86 是 git show cb7e030:scripts/validate.py 真的 import 舊版 ===='
==== STEP 11  對照組不是模擬:--prev86 是 git show cb7e030:scripts/validate.py 真的 import 舊版 ====
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
+ git -C '/d/Self Project/Skills' log --oneline -1 cb7e030
cb7e030 test: #84 QA — 母體 11/1 複驗(六格全收、第七格是宣告過的天花板)+ 七個 knob 的 mutation 逐一咬合,拿修法自己的尺掃出 generator 那面六格誤放
+ echo '==== STEP 12  STEP 2 的尺沒被動到判準:84-generator-sweep.py 只多一個對照組 flag ===='
==== STEP 12  STEP 2 的尺沒被動到判準:84-generator-sweep.py 只多一個對照組 flag ====
+ git -C '/d/Self Project/Skills' diff -- scripts/qa/84-generator-sweep.py
diff --git a/scripts/qa/84-generator-sweep.py b/scripts/qa/84-generator-sweep.py
index a1cd7d2..67bac36 100644
--- a/scripts/qa/84-generator-sweep.py
+++ b/scripts/qa/84-generator-sweep.py
@@ -28,6 +28,7 @@ not run there」—— 所以 `nodes_in` 走到 `Lambda` 就停,body 裡的 `Cal
 用法:
     python scripts/qa/84-generator-sweep.py <repo> --generator
     ... --prev84                                # 對照組:#84 修之前(4c58eab)
+    ... --prev86                                # 對照組:#86 修之前(cb7e030)
 """
 import importlib.util
 import sys
@@ -72,7 +73,7 @@ GENERATOR = [
      + '    list(sys.stdout.buffer.write(b"x") for _ in [1])\n' + TAIL, "GREEN"),
 ]
 
-BASELINES = {"--prev84": "4c58eab"}
+BASELINES = {"--prev84": "4c58eab", "--prev86": "cb7e030"}
 
 if __name__ == "__main__":
     sys.stdout.reconfigure(encoding="utf-8")
+ echo '==== STEP 13  repo 本體沒被動過 ===='
==== STEP 13  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
 M scripts/qa/84-generator-sweep.py
?? scripts/qa/86-async-sweep.py
?? scripts/qa/86-mutate.py
?? scripts/qa/86-walkthrough.sh
```
