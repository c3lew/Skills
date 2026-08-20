"""#86 同型全掃 — 兩把尺,各量一面。

**尺一(誤放那邊)**:「deferred code 的 body 寫在那裡,被呼叫 / 消費的時候才跑」。
#84 拿這條收了 `Lambda`,#86 拿同一條收了 `GeneratorExp` + generator function。
Python 的 deferred body 還有第三種,一模一樣的形狀:**coroutine**。

    import sys
    async def adump():
        sys.stdout.buffer.write(b"x")   # 死碼,一行沒跑
    if __name__ == "__main__":
        adump()                          # 只是建了個 coroutine,沒人 await
        print("要開的票")                  # 中文,沒 pin —— 守門卻閉嘴

`async def` 被呼叫只是**建一個 coroutine**,body 一行沒跑 —— 跟 `gen()` 建一個
generator 完全同型。但 `live_nodes` 的 `gens` 只認 body 有 `yield` 的 def
(`ast.Yield` / `ast.YieldFrom`),`async def` 沒 yield 就不在名單上,`adump()` 照樣
算成 invoked、整個 body 拉進 live 區。真的跑的位置是被 **await / 被 event loop 驅動**
(`await c`、`asyncio.run(c)`、`asyncio.gather(...)`),`consumes` 一條都沒收。

跟 #86 原病同型:一個誰都能翻的開關,只是開關從一組括號換成一個 `async` 關鍵字。

**尺二(誤紅那邊)**:`shadowed`「模組自己綁過的名字不算那個 builtin」。docstring 逐字
寫的是「A name the **module** binds itself」,但實作是
`set().union(*map(binds, ast.walk(tree)))` —— `ast.walk` 走遍**每一個 scope**,別的
function 的 local / parameter / comprehension target 撞名也照收。於是隨便哪個
function 有個叫 `list` 的參數,整個模組的 `list(g)` 就不算消費了,真的會跑的 code
被判 RED。方向是誤紅(吵),但這是 `de68088` 帶進來的 —— `--prev86` 對照組是 0。

判準 oracle = #60 AC1 逐字:「真的在**會執行的位置**用 `sys.stdout.buffer.write`」。
跑不到 -> 不得豁免(RED);真的跑得到 -> 不得誤紅(GREEN)。

用法:
    python scripts/qa/86-async-sweep.py <repo> --async-defer   # 尺一:coroutine 也是 deferred body
    python scripts/qa/86-async-sweep.py <repo> --shadow-scope  # 尺二:shadowed 走遍每個 scope
    python scripts/qa/86-async-sweep.py <repo> --attr-consumer # 尺三:method call 只認 attribute 名字
    ... --prev86                                # 對照組:#86 修之前(cb7e030)
    ... --prev87                                # 對照組:#87 修之前(55fc8eb)
"""
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "sweep60", str(Path(__file__).resolve().parent / "60-mention-sweep.py"))
sweep60 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep60)

DUMP = 'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\n'
ADEF = 'async def adump():\n    dump()\n'
AGEN = 'async def agen():\n    yield dump()\n'
MAIN = 'if __name__ == "__main__":\n'
TAIL = '    print("要開的票")\n'

ASYNC_DEFER = [
    ("coroutine 綁著沒 await `c = adump()`",
     DUMP + ADEF + MAIN + '    c = adump()\n' + TAIL, "RED"),
    ("裸 coroutine 在 live 語句 `adump()`",
     DUMP + ADEF + MAIN + '    adump()\n' + TAIL, "RED"),
    ("coroutine 進容器沒 await `xs = [adump()]`",
     DUMP + ADEF + 'xs = [adump()]\n' + MAIN + TAIL, "RED"),
    ("coroutine 交給不 await 的 def `keep(adump())`",
     DUMP + ADEF + 'def keep(c):\n    return c\n' + MAIN
     + '    keep(adump())\n' + TAIL, "RED"),
    ("bypass 直接寫在呼叫了但沒 await 的 async def body 裡",
     'import sys\nasync def adump():\n    sys.stdout.buffer.write(b"x")\n'
     + MAIN + '    adump()\n' + TAIL, "RED"),
    ("對照:async def 綁著沒呼叫(現在就是 RED,不得放掉)",
     DUMP + ADEF + MAIN + TAIL, "RED"),
    ("對照:async generator 呼叫了沒 iterate `agen()`(現在就是 RED,不得放掉)",
     DUMP + AGEN + MAIN + '    agen()\n' + TAIL, "RED"),
    ("對照:`await adump()` 只在沒人跑的 outer 裡(現在就是 RED,不得放掉)",
     DUMP + ADEF + 'async def outer():\n    await adump()\n' + MAIN + TAIL, "RED"),
    ("對照:`asyncio.run(adump())` 真的跑(不得誤紅)",
     DUMP + 'import asyncio\n' + ADEF + MAIN
     + '    asyncio.run(adump())\n' + TAIL, "GREEN"),
    ("對照:`await adump()` 在被 `asyncio.run` 的 outer 裡(不得誤紅)",
     DUMP + 'import asyncio\n' + ADEF + 'async def outer():\n    await adump()\n'
     + MAIN + '    asyncio.run(outer())\n' + TAIL, "GREEN"),
    ("對照:bypass 寫在真的被 run 的 coroutine body(不得誤紅)",
     'import sys\nimport asyncio\nasync def adump():\n'
     '    sys.stdout.buffer.write(b"x")\n' + MAIN
     + '    asyncio.run(adump())\n' + TAIL, "GREEN"),
    ("對照:`async for _ in agen()` 真的 iterate(不得誤紅)",
     DUMP + 'import asyncio\n' + AGEN
     + 'async def outer():\n    async for _ in agen():\n        pass\n'
     + MAIN + '    asyncio.run(outer())\n' + TAIL, "GREEN"),
]

# 尺二:`g = (dump() for _ in [1])` + `list(g)` —— dump 真的會跑,一律 GREEN。
# 只是在別的 scope 裡多一個叫 `list` 的名字,`shadowed` 就把 `list` 從消費者名單
# 上劃掉,整檔誤紅。八個 binding 位置各一格,`binds` 收哪種就漏哪種。
G = 'g = (dump() for _ in [1])\n'
CONS = '    list(g)\n'

SHADOW_SCOPE = [
    ("別的 def 裡的 local 叫 list `def u(): list = 1`",
     DUMP + G + 'def u():\n    list = 1\n    return list\n' + MAIN + CONS + TAIL, "GREEN"),
    ("別的 def 的 parameter 叫 list `def u(list)`",
     DUMP + G + 'def u(list):\n    return list\n' + MAIN + CONS + TAIL, "GREEN"),
    ("comprehension target 叫 list `[list for list in []]`",
     DUMP + G + 'ys = [list for list in []]\n' + MAIN + CONS + TAIL, "GREEN"),
    ("`with … as list` 在別的 def 裡",
     DUMP + G + 'def u():\n    with open("f") as list:\n        pass\n'
     + MAIN + CONS + TAIL, "GREEN"),
    ("`except … as list` 在別的 def 裡",
     DUMP + G + 'def u():\n    try:\n        pass\n'
     '    except Exception as list:\n        pass\n' + MAIN + CONS + TAIL, "GREEN"),
    ("class body 裡的 attribute 叫 list `class W: list = 1`",
     DUMP + G + 'class W:\n    list = 1\n' + MAIN + CONS + TAIL, "GREEN"),
    # `import json as list` 是 #86 原本這一格的寫法,但 `list(g)` 會炸 —— generator 沒
    # 被抽乾、bypass 那行根本沒跑到,ground truth 是 RED 不是 GREEN(`/qa #87` STEP 10
    # 的實跑 oracle 抓到的)。換成一樣是 import alias、但真的會抽乾 iterable 的 `deque`,
    # 這格想量的「alias 撞名也算 shadow」原樣保留,期望值才站得住。
    ("import alias 叫 list `from collections import deque as list`",
     DUMP + G + 'from collections import deque as list\n' + MAIN + CONS
     + TAIL, "GREEN"),
    ("巢狀 def 叫 list `def u(): def list(): …`",
     DUMP + G + 'def u():\n    def list():\n        pass\n    return list\n'
     + MAIN + CONS + TAIL, "GREEN"),
    ("連死碼分支裡的 for target 都算 `if False: for list in []`",
     DUMP + G + 'if False:\n    for list in []:\n        pass\n'
     + MAIN + CONS + TAIL, "GREEN"),
    ("對照:模組真的 `def sorted(g): return g`(#86 review 收的那條,不得放掉)",
     DUMP + 'def sorted(x):\n    return x\n' + MAIN
     + '    sorted(dump() for _ in [1])\n' + TAIL, "RED"),
    ("對照:沒有任何撞名,`list(g)` 照常消費(不得誤紅)",
     DUMP + G + MAIN + CONS + TAIL, "GREEN"),
]

# 尺三:`consumes` 的 callee 用**名字**讀,method call 只認 attribute 名字。修法自己在
# `consumes` 的 docstring 裡宣告了這個洞、方向是誤放、沒開票、交給 QA 判。量下去它是真的
# 能翻的開關:`b.next(… for _ in [1])`,`b` 隨便一個 import 進來的物件,整檔豁免。
# 同模組自己定義的 class method 剛好被尺二那個過寬的 `shadowed` 擋掉(見 `--shadow-scope`)
# —— 兩個 bug 互相蓋住對方,尺二修好之後這面會更寬。
OBJ = 'import queue\nb = queue.Queue()\n'

ATTR_CONSUMER = [
    ("import 進來的物件 `.extend(genexp)`,它根本不抽乾",
     DUMP + OBJ + MAIN + '    b.extend(dump() for _ in [1])\n' + TAIL, "RED"),
    ("bypass 直接寫在交給 `.extend` 的 genexp body 裡",
     'import sys\n' + OBJ + MAIN
     + '    b.extend(sys.stdout.buffer.write(b"x") for _ in [1])\n' + TAIL, "RED"),
    ("bypass 交給 `.next` —— 名單上任一個名字當 method 都行",
     'import sys\n' + OBJ + MAIN
     + '    b.next(sys.stdout.buffer.write(b"x") for _ in [1])\n' + TAIL, "RED"),
    ("對照:同模組自己 `class B: def extend`(被尺二那個過寬的 shadowed 擋掉,現在是 RED)",
     DUMP + 'class B:\n    def extend(self, g):\n        pass\nb = B()\n' + MAIN
     + '    b.extend(dump() for _ in [1])\n' + TAIL, "RED"),
    ('對照:真的 `"".join(…)`(修法留下 attribute 判讀的理由,不得誤紅)',
     DUMP + MAIN + '    "".join(str(dump()) for _ in [1])\n' + TAIL, "GREEN"),
    ("對照:真的 `list.extend(…)`(不得誤紅)",
     DUMP + 'b = []\n' + MAIN + '    b.extend(dump() for _ in [1])\n'
     + TAIL, "GREEN"),
]

BASELINES = {"--prev86": "cb7e030", "--prev87": "55fc8eb",
             "--prev91": "fa9d0c3"}  # #91 修之前(/qa #91 登記)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cases = SHADOW_SCOPE
    if "--async-defer" in sys.argv:
        cases = ASYNC_DEFER
    elif "--attr-consumer" in sys.argv:
        cases = ATTR_CONSUMER
    base = next((BASELINES[f] for f in BASELINES if f in sys.argv), None)
    sys.exit(1 if sweep60.run(sys.argv[1], cases, base) else 0)
