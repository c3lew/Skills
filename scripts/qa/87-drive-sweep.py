"""#87 同型全掃 — 三把尺,量 `c51ba98` 自己新開的三面。

`c51ba98` 收 coroutine 那面用了兩個新零件:`gens` 收下每一個 `ast.AsyncFunctionDef`
(呼叫不等於 body 跑了),`consumes` 補上「真的被驅動」的位置(`ast.Await` 的 operand
+ 一組 `DRIVEN_BY` 名字)。`gens` 那半是**擋**,`consumes` 那半是**放** —— 兩半只要
對不齊,一邊多擋(誤紅)、一邊多放(誤放)。這支把三面各自的母體一次列完。

**尺一(誤紅)`--driven-shadow`**:`DRIVEN_BY` 的七個名字走 `CONSUMED_BY` 現成的
name-only 機制,連 `shadowed` 也一起沿用 —— 模組裡任何一個 scope 綁過同名的東西,
`asyncio.run(...)` 就不算驅動,真的在跑的 coroutine 整檔判 RED。差別在名字:
`CONSUMED_BY` 上是 `list` / `sorted` 這種很少當變數名的 builtin,`DRIVEN_BY` 上是
`run` / `wait` / `gather` —— 隨便一支 script 都有個參數叫 `run`。

**尺二(誤放)`--driven-attr`**:同一個 name-only 讀法不看 receiver,`b.run(adump())`
裡的 `b` 是任何 import 進來的物件都行,coroutine 就算被驅動、body 拉進 live 區,寫在
裡面的 bypass 整檔豁免。跟 `--attr-consumer`(#86 開的票)同形狀,新增七個名字的面。

**尺三(誤紅)`--await-shapes`**:coroutine 真的被驅動、但驅動的位置不在名單上 ——
綁到名字再驅動(`c = adump()` + `await c`)、`gather(*cs)` 的 Starred 展開、
async comprehension 裡的 await。generator 那半有 `gen_of` / `eaten_via_name` 追名字,
coroutine 這半沒有對應的一套。

判準 oracle = #60 AC1 逐字:「真的在**會執行的位置**用 `sys.stdout.buffer.write`」。
跑不到 -> 不得豁免(RED);真的跑得到 -> 不得誤紅(GREEN)。每一格的期望值不是手標的
——`87-oracle.py` 把同一份 fixture **真的跑起來**,看那一行 bypass 到底有沒有執行。

用法:
    python scripts/qa/87-drive-sweep.py <repo> --driven-shadow
    python scripts/qa/87-drive-sweep.py <repo> --driven-attr
    python scripts/qa/87-drive-sweep.py <repo> --await-shapes
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
AIO = 'import asyncio\n'
ADEF = 'async def adump():\n    dump()\n'
BYPASS_BODY = ('import sys\nasync def adump():\n'
               '    sys.stdout.buffer.write(b"x")\n')
OBJ = 'import queue\nb = queue.Queue()\n'
MAIN = 'if __name__ == "__main__":\n'
TAIL = '    print("要開的票")\n'
OUTER = 'async def outer():\n'
RUN_OUTER = '    asyncio.run(outer())\n'

# 尺一:七個 `DRIVEN_BY` 名字 —— 模組自己老老實實綁一個同名的東西,那個名字就從驅動者
# 名單上被 `shadowed` 劃掉,真的在跑的 coroutine 整檔判 RED。每一格的驅動位置都放在
# 真的有 event loop 的地方(`87-oracle.py` 逐格實跑確認 body 真的執行),所以期望一律
# GREEN。`wait` 那格沒有乾淨的 fixture —— Python 3.12 起 `asyncio.wait` 不收裸
# coroutine,要先 `ensure_future`,而那一步自己就驅動了,量不到 `wait` 這個名字。
DRIVEN_SHADOW = [
    ("模組自己 `def run(x)`,`asyncio.run(adump())` 真的在跑",
     DUMP + AIO + ADEF + 'def run(x):\n    return x\n' + MAIN
     + '    asyncio.run(adump())\n' + TAIL, "GREEN"),
    ("模組自己 `def gather(x)`,`await asyncio.gather(adump())` 真的在跑",
     DUMP + AIO + ADEF + 'def gather(x):\n    return x\n' + OUTER
     + '    await asyncio.gather(adump())\n' + MAIN + RUN_OUTER + TAIL, "GREEN"),
    ("模組自己 `def wait_for(x)`,`await asyncio.wait_for(adump(), 5)` 真的在跑",
     DUMP + AIO + ADEF + 'def wait_for(x):\n    return x\n' + OUTER
     + '    await asyncio.wait_for(adump(), 5)\n' + MAIN + RUN_OUTER
     + TAIL, "GREEN"),
    ("模組自己 `def create_task(x)`,`asyncio.create_task(adump())` 真的在跑",
     DUMP + AIO + ADEF + 'def create_task(x):\n    return x\n' + OUTER
     + '    t = asyncio.create_task(adump())\n    await t\n' + MAIN
     + RUN_OUTER + TAIL, "GREEN"),
    ("模組自己 `def ensure_future(x)`,`await asyncio.ensure_future(adump())` 真的在跑",
     DUMP + AIO + ADEF + 'def ensure_future(x):\n    return x\n' + OUTER
     + '    await asyncio.ensure_future(adump())\n' + MAIN + RUN_OUTER
     + TAIL, "GREEN"),
    ("模組自己 `def run_until_complete(x)`,`loop.run_until_complete(adump())` 真的在跑",
     DUMP + AIO + ADEF + 'def run_until_complete(x):\n    return x\n' + MAIN
     + '    loop = asyncio.new_event_loop()\n'
     + '    loop.run_until_complete(adump())\n' + TAIL, "GREEN"),
    ("別的 def 的參數叫 run `def u(run)`",
     DUMP + AIO + ADEF + 'def u(run):\n    return run\n' + MAIN
     + '    asyncio.run(adump())\n' + TAIL, "GREEN"),
    ("別的 def 裡的 local 叫 wait_for `def u(): wait_for = 1`",
     DUMP + AIO + ADEF + 'def u():\n    wait_for = 1\n    return wait_for\n'
     + OUTER + '    await asyncio.wait_for(adump(), 5)\n' + MAIN + RUN_OUTER
     + TAIL, "GREEN"),
    ("comprehension target 叫 gather `[gather for gather in []]`",
     DUMP + AIO + ADEF + 'ys = [gather for gather in []]\n' + OUTER
     + '    await asyncio.gather(adump())\n' + MAIN + RUN_OUTER + TAIL, "GREEN"),
    ("`import json as run` 撞名",
     DUMP + AIO + ADEF + 'import json as run\n' + MAIN
     + '    asyncio.run(adump())\n' + TAIL, "GREEN"),
    ("對照:沒有任何撞名,`asyncio.run(adump())` 照常驅動(不得誤紅)",
     DUMP + AIO + ADEF + MAIN + '    asyncio.run(adump())\n' + TAIL, "GREEN"),
    ("對照:自己的 `def run(x): return x` 真的沒驅動(shadowed 這半的價值,不得放掉)",
     DUMP + ADEF + 'def run(x):\n    return x\n' + MAIN
     + '    run(adump())\n' + TAIL, "RED"),
]

# 尺二:七個名字各一格 —— receiver 是 import 進來的 `queue.Queue()`,`.run(...)` 一行
# 都沒驅動(`87-oracle.py` 逐格實跑確認 body 沒執行),但 bypass 寫在那個 coroutine
# body 裡就整檔豁免。期望一律 RED。
DRIVEN_ATTR = [
    (f"任意物件的 `.{n}(coroutine)` 當開關,bypass 寫在沒人跑的 body 裡",
     BYPASS_BODY + OBJ + MAIN + f'    b.{n}(adump())\n' + TAIL, "RED")
    for n in "run gather wait wait_for create_task ensure_future "
             "run_until_complete".split()
] + [
    ("`subprocess.run(coroutine)` —— 名字撞得最兇的那個",
     BYPASS_BODY + 'import subprocess\n' + MAIN
     + '    subprocess.run(adump())\n' + TAIL, "RED"),
    # 上面那批的 receiver 收到 coroutine 會直接拋例外,ground truth 的 RED 是「炸了」
    # 換來的,不是「那行在死碼位置」換來的(judge 提的 oracle 弱點)。這兩格的 receiver
    # 是 `MagicMock`,吃下任何引數、什麼都不做、也不炸 —— RED 純粹來自 body 沒跑。
    ("`MagicMock().run(coroutine)` —— receiver 不炸,純粹就是沒驅動",
     BYPASS_BODY + 'from unittest.mock import MagicMock\nb = MagicMock()\n'
     + MAIN + '    b.run(adump())\n' + TAIL, "RED"),
    ("`MagicMock().create_task(coroutine)` —— 同上,換一個名字",
     BYPASS_BODY + 'from unittest.mock import MagicMock\nb = MagicMock()\n'
     + MAIN + '    b.create_task(adump())\n' + TAIL, "RED"),
    ("對照:`loop.run_until_complete(adump())` 真的驅動(attribute 判讀的理由,不得誤紅)",
     DUMP + AIO + ADEF + MAIN
     + '    loop = asyncio.new_event_loop()\n'
     + '    loop.run_until_complete(adump())\n' + TAIL, "GREEN"),
    ("對照:`asyncio.Runner().run(adump())` 真的驅動(不得誤紅)",
     DUMP + AIO + ADEF + MAIN + '    asyncio.Runner().run(adump())\n'
     + TAIL, "GREEN"),
]

# 尺三:coroutine 真的被驅動(`87-oracle.py` 逐格實跑確認),但驅動位置不在 `consumes`
# 收的四種裡 —— 綁到名字再驅動、Starred 展開、async comprehension 裡的 await。
AWAIT_SHAPES = [
    ("綁到名字再 await `c = adump()` + `await c`",
     DUMP + AIO + ADEF + OUTER + '    c = adump()\n    await c\n'
     + MAIN + RUN_OUTER + TAIL, "GREEN"),
    ("綁到名字再交給 event loop `c = adump()` + `asyncio.run(c)`",
     DUMP + AIO + ADEF + MAIN + '    c = adump()\n    asyncio.run(c)\n'
     + TAIL, "GREEN"),
    ("`asyncio.gather(*cs)` 的 Starred 展開",
     DUMP + AIO + ADEF + OUTER + '    cs = [adump()]\n'
     + '    await asyncio.gather(*cs)\n' + MAIN + RUN_OUTER + TAIL, "GREEN"),
    ("async comprehension 裡的 await `[await c for c in [adump()]]`",
     DUMP + AIO + ADEF
     + OUTER + '    return [await c for c in [adump()]]\n'
     + MAIN + RUN_OUTER + TAIL, "GREEN"),
    ("對照:`asyncio.run(adump())` 一步到位(不得誤紅)",
     DUMP + AIO + ADEF + MAIN + '    asyncio.run(adump())\n' + TAIL, "GREEN"),
    ("對照:`asyncio.run(main=adump())` 走 keyword(不得誤紅)",
     DUMP + AIO + ADEF + MAIN + '    asyncio.run(main=adump())\n'
     + TAIL, "GREEN"),
    ("對照:兩層 await `outer -> mid -> adump`(不得誤紅)",
     DUMP + AIO + ADEF + 'async def mid():\n    await adump()\n'
     + OUTER + '    await mid()\n' + MAIN + RUN_OUTER + TAIL, "GREEN"),
    ("對照:`c = adump()` 綁著沒人驅動(#87 母體第一格,不得放掉)",
     DUMP + AIO + ADEF + MAIN + '    c = adump()\n' + TAIL, "RED"),
]

BASELINES = {"--prev87": "55fc8eb", "--prev86": "cb7e030",
             "--prev91": "fa9d0c3"}  # #91 修之前(/qa #91 登記)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cases = DRIVEN_SHADOW
    if "--driven-attr" in sys.argv:
        cases = DRIVEN_ATTR
    elif "--await-shapes" in sys.argv:
        cases = AWAIT_SHAPES
    base = next((BASELINES[f] for f in BASELINES if f in sys.argv), None)
    sys.exit(1 if sweep60.run(sys.argv[1], cases, base) else 0)
