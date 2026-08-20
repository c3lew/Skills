"""#91 同型全掃 — 三把尺,量 `14f69f2` 自己新開的三面。

`14f69f2` 把「這個 call 算不算 event loop 驅動」從讀名字換成解 callee,靠三個新零件:
`asyncio_graph`(哪些名字真的來自 asyncio)、`from_asyncio`(receiver 認不認)、
`drives`(attribute 看 receiver、bare name 只認 `from asyncio import`)。這三個零件
各自有一組**沒被列舉完**的形狀,這支把三面的母體一次列完。

**尺一(誤放)`--graph-scope`**:`asyncio_graph` 把綁定**收在哪裡**完全不看 —— 一個
def 裡的 local import、一個永遠不會跑的 def 裡的 local 變數、class body 的 attribute,
全部當成模組層的名字;而且**名字被綁走**之後不追(`import asyncio` 之後
`asyncio = MagicMock()`)。這兩件事都是往「多算驅動」的方向偏:coroutine body 被拉進
live 區,寫在裡面的死碼 bypass 整檔豁免。ponytail 註解宣告過這條成本,但沒有列舉,
也沒有任何 fixture 釘著它。

**尺二(誤紅)`--loop-binding`**:loop 的綁定只從 `ast.Assign` 跟 `ast.withitem` 讀 ——
`loop: X = asyncio.new_event_loop()`(AnnAssign)、walrus、`for loop in [...]`、
tuple 解包、進容器再取出來,全部追不到。真的在跑的檔案整檔判 RED。

**尺三(誤紅)`--loop-source`**:`LOOP_FROM` 是四個名字的清單,不是型別判讀 ——
`asyncio.get_event_loop_policy().new_event_loop()`、`asyncio.SelectorEventLoop()`、
`Runner().get_loop()`、自己包一層的 runner,全都真的驅動得動 coroutine,但不在名單上。

判準 oracle = #60 AC1 逐字:「真的在**會執行的位置**用 `sys.stdout.buffer.write`」。
跑不到 -> 不得豁免(RED);真的跑得到 -> 不得誤紅(GREEN)。每一格的期望值不是手標的
—— `91-oracle.py` 把同一份 fixture **真的跑起來**,看那一行 bypass 到底有沒有執行。

用法:
    python scripts/qa/91-graph-sweep.py <repo> --graph-scope
    python scripts/qa/91-graph-sweep.py <repo> --loop-binding
    python scripts/qa/91-graph-sweep.py <repo> --loop-source
    ... --prev91                                # 對照組:#91 修之前(fa9d0c3)
"""
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "sweep60", str(Path(__file__).resolve().parent / "60-mention-sweep.py"))
sweep60 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep60)

DUMP = 'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\n'
AIO = 'import asyncio\n'
ADEF = 'async def adump():\n    dump()\n'
BYPASS_BODY = ('import sys\nasync def adump():\n'
               '    sys.stdout.buffer.write(b"x")\n')
MOCK = 'from unittest.mock import MagicMock\n'
MAIN = 'if __name__ == "__main__":\n'
TAIL = '    print("要開的票")\n'

# 尺一:綁定收在哪裡不看、綁走了不追 —— receiver 一律用 `MagicMock`,吃下 coroutine、
# 什麼都不做、也不炸,所以 RED 純粹來自 body 沒跑,不是「炸了」換來的。
GRAPH_SCOPE = [
    ("`import asyncio` 之後名字被綁走 `asyncio = MagicMock()`",
     BYPASS_BODY + AIO + MOCK + 'asyncio = MagicMock()\n' + MAIN
     + '    asyncio.run(adump())\n' + TAIL, "RED"),
    ("別名版:`import asyncio as aio` 之後 `aio = MagicMock()`",
     BYPASS_BODY + 'import asyncio as aio\n' + MOCK + 'aio = MagicMock()\n'
     + MAIN + '    aio.run(adump())\n' + TAIL, "RED"),
    ("永遠不會跑的 def 裡有 `loop = asyncio.new_event_loop()`,模組層的 `loop` 是別的東西",
     BYPASS_BODY + AIO + MOCK
     + 'def never():\n    loop = asyncio.new_event_loop()\n    return loop\n'
     + MAIN + '    loop = MagicMock()\n'
     + '    loop.run_until_complete(adump())\n' + TAIL, "RED"),
    ("`from asyncio import run` 寫在別的 def 裡,模組自己有 `def run(x)`",
     BYPASS_BODY
     + 'def helper():\n    from asyncio import run\n    return run\n'
     + 'def run(x):\n    return x\n' + MAIN + '    run(adump())\n'
     + TAIL, "RED"),
    ("`from asyncio import Runner` 之後 `Runner = MagicMock`,`r = Runner()`",
     BYPASS_BODY + 'from asyncio import Runner\n' + MOCK
     + 'Runner = MagicMock\n' + MAIN + '    r = Runner()\n'
     + '    r.run(adump())\n' + TAIL, "RED"),
    ("class body 裡 `loop = asyncio.new_event_loop()`,模組層的 `loop` 是別的東西",
     BYPASS_BODY + AIO + MOCK
     + 'class C:\n    loop = asyncio.new_event_loop()\n' + MAIN
     + '    loop = MagicMock()\n'
     + '    loop.run_until_complete(adump())\n' + TAIL, "RED"),
    ("對照:`from asyncio import sleep` 之後 `x = sleep`,`x.run(...)` 不是驅動(不得放掉)",
     BYPASS_BODY + 'from asyncio import sleep\nx = sleep\n' + MAIN
     + '    x.run(adump())\n' + TAIL, "RED"),
    ("對照:`ok = asyncio.iscoroutinefunction(adump)` 之後 `ok.run(...)`(不得放掉)",
     BYPASS_BODY + AIO + 'ok = asyncio.iscoroutinefunction(adump)\n' + MAIN
     + '    ok.run(adump())\n' + TAIL, "RED"),
    ("對照:沒有任何重綁,`asyncio.run(adump())` 真的驅動(不得誤紅)",
     DUMP + AIO + ADEF + MAIN + '    asyncio.run(adump())\n' + TAIL, "GREEN"),
    ("對照:`from asyncio import run` 在模組層,`run(adump())` 真的驅動(不得誤紅)",
     DUMP + 'from asyncio import run\n' + ADEF + MAIN
     + '    run(adump())\n' + TAIL, "GREEN"),
]

# 尺二:loop 真的是 asyncio 交出來的、也真的驅動了 coroutine,只是綁定的形狀不是
# `Assign` 也不是 `withitem`。期望一律 GREEN。
LOOP_BINDING = [
    ("AnnAssign `loop: object = asyncio.new_event_loop()`",
     DUMP + AIO + ADEF + MAIN
     + '    loop: object = asyncio.new_event_loop()\n'
     + '    loop.run_until_complete(adump())\n' + TAIL, "GREEN"),
    ("walrus `if (loop := asyncio.new_event_loop()):`",
     DUMP + AIO + ADEF + MAIN
     + '    if (loop := asyncio.new_event_loop()):\n'
     + '        loop.run_until_complete(adump())\n' + TAIL, "GREEN"),
    ("for target `for loop in [asyncio.new_event_loop()]:`",
     DUMP + AIO + ADEF + MAIN
     + '    for loop in [asyncio.new_event_loop()]:\n'
     + '        loop.run_until_complete(adump())\n' + TAIL, "GREEN"),
    ('tuple 解包 `loop, tag = asyncio.new_event_loop(), "x"`',
     DUMP + AIO + ADEF + MAIN
     + '    loop, tag = asyncio.new_event_loop(), "x"\n'
     + '    loop.run_until_complete(adump())\n' + TAIL, "GREEN"),
    ("進容器再取出來 `loops = [asyncio.new_event_loop()]` + `loops[0]`",
     DUMP + AIO + ADEF + MAIN
     + '    loops = [asyncio.new_event_loop()]\n'
     + '    loops[0].run_until_complete(adump())\n' + TAIL, "GREEN"),
    ("宣告過的天花板:經自己的 def 拿到 loop `loop = get_loop()`",
     DUMP + AIO + ADEF
     + 'def get_loop():\n    return asyncio.new_event_loop()\n' + MAIN
     + '    loop = get_loop()\n'
     + '    loop.run_until_complete(adump())\n' + TAIL, "GREEN"),
    ("宣告過的天花板:loop 當參數傳進來 `def drive(loop)`",
     DUMP + AIO + ADEF
     + 'def drive(loop):\n    loop.run_until_complete(adump())\n' + MAIN
     + '    drive(asyncio.new_event_loop())\n' + TAIL, "GREEN"),
    ("對照:`loop = asyncio.new_event_loop()` 直球(不得誤紅)",
     DUMP + AIO + ADEF + MAIN + '    loop = asyncio.new_event_loop()\n'
     + '    loop.run_until_complete(adump())\n' + TAIL, "GREEN"),
    ("對照:`with asyncio.Runner() as r`(不得誤紅)",
     DUMP + AIO + ADEF + MAIN + '    with asyncio.Runner() as r:\n'
     + '        r.run(adump())\n' + TAIL, "GREEN"),
]

# 尺三:receiver 真的驅動得動 coroutine,但拿到它的那個 asyncio call 不在 `LOOP_FROM`
# 的四個名字上。期望一律 GREEN(最後一格是不得放掉的對照)。
LOOP_SOURCE = [
    ("`asyncio.get_event_loop_policy().new_event_loop()`",
     DUMP + AIO + ADEF + MAIN
     + '    loop = asyncio.get_event_loop_policy().new_event_loop()\n'
     + '    loop.run_until_complete(adump())\n' + TAIL, "GREEN"),
    ("`asyncio.SelectorEventLoop()` 直接建一個 loop",
     DUMP + AIO + ADEF + MAIN
     + '    loop = asyncio.SelectorEventLoop()\n'
     + '    loop.run_until_complete(adump())\n' + TAIL, "GREEN"),
    ("`with asyncio.Runner() as r: r.get_loop()`",
     DUMP + AIO + ADEF + MAIN + '    with asyncio.Runner() as r:\n'
     + '        r.get_loop().run_until_complete(adump())\n' + TAIL, "GREEN"),
    ("宣告過的天花板:自己包一層的 runner `class Loop: def run(self, c)`",
     DUMP + AIO + ADEF
     + 'class Loop:\n    def run(self, c):\n'
     + '        return asyncio.new_event_loop().run_until_complete(c)\n'
     + MAIN + '    Loop().run(adump())\n' + TAIL, "GREEN"),
    ("對照:`asyncio.new_event_loop()` 在名單上(不得誤紅)",
     DUMP + AIO + ADEF + MAIN + '    loop = asyncio.new_event_loop()\n'
     + '    loop.run_until_complete(adump())\n' + TAIL, "GREEN"),
    ("對照:`asyncio.Runner().run(adump())` 在名單上(不得誤紅)",
     DUMP + AIO + ADEF + MAIN + '    asyncio.Runner().run(adump())\n'
     + TAIL, "GREEN"),
    ("對照:`MagicMock().run(coroutine)` 什麼都沒驅動(不得放掉)",
     BYPASS_BODY + MOCK + 'b = MagicMock()\n' + MAIN
     + '    b.run(adump())\n' + TAIL, "RED"),
]

BASELINES = {"--prev91": "fa9d0c3", "--prev87": "55fc8eb"}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cases = GRAPH_SCOPE
    if "--loop-binding" in sys.argv:
        cases = LOOP_BINDING
    elif "--loop-source" in sys.argv:
        cases = LOOP_SOURCE
    base = next((BASELINES[f] for f in BASELINES if f in sys.argv), None)
    sys.exit(1 if sweep60.run(sys.argv[1], cases, base) else 0)
