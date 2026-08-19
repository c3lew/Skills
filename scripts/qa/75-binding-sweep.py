"""#75 同型全掃 — 「綁定」與「會跑的位置」,兩把尺三個方向各掃一遍。

#75 把 `live_nodes` 的綁定採集從「只認 `ast.Assign` + 裸 `Name` target」擴成
`bindings_in`:`Assign` / `AnnAssign` / tuple-list 解包 / `For.target`,外加 `runs`
不再砍 class body、`runs` 對 `For` 補一個「header 也會跑」的節點、`live_nodes` 帶 def
自己的 `Return`。判準改了寬度,不是一條 case:

- 尺一(`bindings_in`)—「呼叫這個名字 = 呼叫右邊那個名字」這個 claim,換任何寫法都是
  同一形狀。→ `--binding-shapes`
- 尺二(`For` header)—「header 本身會執行」。同型:`if` / `elif` / `while` 的 test、
  `with` 的 items、decorator,都是會跑的位置。→ `--header`
- 反方向 — 這次放寬有沒有讓「綁了但沒被呼叫」變成 live(守門閉嘴)。→ `--bind-quiet`

判準 oracle = #60 AC1 逐字:「真的在**會執行的位置**用 `sys.stdout.buffer.write`」。
- 真的會執行 -> 豁免(GREEN),喊住它就是誤紅。
- 跑不到 -> 不豁免(RED),放它過就是守門閉嘴。

用法:
    python scripts/qa/75-binding-sweep.py <repo> --binding-shapes  # 綁定寫法(誤紅那邊)
    python scripts/qa/75-binding-sweep.py <repo> --header          # 複合敘述的 header(誤紅那邊)
    python scripts/qa/75-binding-sweep.py <repo> --bind-quiet      # 放寬的代價(誤放那邊)
    ... --prev                                                     # 對照組:#75 修之前(39003a3)
"""
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "sweep60", str(Path(__file__).resolve().parent / "60-mention-sweep.py"))
sweep60 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep60)

DUMP = 'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\n'
CTX = 'import sys\nimport contextlib\ndef dump():\n    sys.stdout.buffer.write(b"x")\n'
TAIL = '    print("要開的票")\n'
MAIN = 'if __name__ == "__main__":\n'

# 尺一(誤紅那邊):同一個 claim「呼叫這個名字 = 呼叫右邊那個名字」,換不同寫法。
# #75 收了四種節點進 `bindings_in`,同型的其他寫法還在不在外面,一次量完。
BINDING_SHAPES = [
    ("對照:alias `f = dump; f()`(#71/#75 蓋到的形狀,不得誤紅)",
     DUMP + MAIN + '    f = dump\n    f()\n' + TAIL, "GREEN"),
    ("對照:`for f in [dump]: f()`(#75 蓋到的形狀,不得誤紅)",
     DUMP + MAIN + '    for f in [dump]:\n        f()\n' + TAIL, "GREEN"),
    ("starred 解包 `a, *rest = dump, dump; a()`",
     DUMP + MAIN + '    a, *rest = dump, dump\n    a()\n' + TAIL, "GREEN"),
    ("巢狀解包 `(a, b), c = (dump, dump), dump; a()`",
     DUMP + MAIN + '    (a, b), c = (dump, dump), dump\n    a()\n' + TAIL, "GREEN"),
    ("list target `[a, b] = [dump, dump]; a()`",
     DUMP + MAIN + '    [a, b] = [dump, dump]\n    a()\n' + TAIL, "GREEN"),
    ("多重 target `a = b = dump; a()`",
     DUMP + MAIN + '    a = b = dump\n    a()\n' + TAIL, "GREEN"),
    ("walrus `if (f := dump): f()`",
     DUMP + MAIN + '    if (f := dump):\n        f()\n' + TAIL, "GREEN"),
    ("`with nullcontext(dump) as f: f()`(票上已宣告的天花板)",
     CTX + MAIN + '    with contextlib.nullcontext(dump) as f:\n        f()\n' + TAIL, "GREEN"),
    ("attribute target `W.run = dump` + `W.run()`",
     DUMP + 'class W:\n    pass\n' + MAIN + '    W.run = dump\n    W.run()\n' + TAIL, "GREEN"),
    ("subscript target `H[\"a\"] = dump` + `H[\"a\"]()`(#71 的 handler dict 換個寫法)",
     DUMP + MAIN + '    H = {}\n    H["a"] = dump\n    H["a"]()\n' + TAIL, "GREEN"),
    ("comprehension target `[f() for f in [dump]]`",
     DUMP + MAIN + '    x = [f() for f in [dump]]\n' + TAIL, "GREEN"),
    ("預設引數 `def go(cb=dump): cb()` + `go()`",
     DUMP + 'def go(cb=dump):\n    cb()\n' + MAIN + '    go()\n' + TAIL, "GREEN"),
]

# 尺二(誤紅那邊):#75 對 `For` 補了「header 也會跑」的節點,理由是 header 本身會執行。
# 同一把尺:`if` / `elif` / `while` 的 test 與 `with` 的 items 也都是 header,也都會執行,
# `runs` 一律只回 body 就把它們丟了 —— 寫在 header 的呼叫在可達性裡等於不存在。
HEADER = [
    ("對照:top-level `dump()`(不得誤紅)",
     DUMP + MAIN + '    dump()\n' + TAIL, "GREEN"),
    ("對照:`for x in [dump()]: pass`(#75 補好的 header)",
     DUMP + MAIN + '    for x in [dump()]:\n        pass\n' + TAIL, "GREEN"),
    ("對照:`with nullcontext(): dump()` — 呼叫在 body 裡(不得誤紅)",
     CTX + MAIN + '    with contextlib.nullcontext():\n        dump()\n' + TAIL, "GREEN"),
    ("`if dump(): pass` — if 的 test",
     DUMP + MAIN + '    if dump():\n        pass\n' + TAIL, "GREEN"),
    ("`elif dump(): pass` — elif 的 test",
     DUMP + MAIN + '    if 0:\n        pass\n    elif dump():\n        pass\n' + TAIL, "GREEN"),
    ("`while dump(): break` — while 的 test",
     DUMP + MAIN + '    while dump():\n        break\n' + TAIL, "GREEN"),
    ("`with nullcontext(dump()): pass` — with 的 items",
     CTX + MAIN + '    with contextlib.nullcontext(dump()):\n        pass\n' + TAIL, "GREEN"),
    ("`@deco` — decorator 是 import 時就會跑的位置",
     DUMP + 'def deco(f):\n    dump()\n    return f\n\n\n@deco\ndef g():\n    pass\n'
     + MAIN + '    g()\n' + TAIL, "GREEN"),
]

# 反方向(誤放那邊):#75 這次把 class body、`for` header、def 的 `return` 都算進來。
# 「綁了但沒被呼叫」必須維持死 —— 閉嘴才是 #70/#73 在守的那邊。
BIND_QUIET = [
    ("`for f in [dump]: pass` — 綁了沒呼叫",
     DUMP + MAIN + '    for f in [dump]:\n        pass\n' + TAIL, "RED"),
    ("`class W: run = dump` — 沒人叫 W.run",
     DUMP + 'class W:\n    run = dump\n' + MAIN + TAIL, "RED"),
    ("`class W: run = dump` + 只提到 `W.run` 不呼叫",
     DUMP + 'class W:\n    run = dump\n' + MAIN + '    x = [W.run]\n' + TAIL, "RED"),
    ("factory 沒人叫 `def get(): return dump`",
     DUMP + 'def get():\n    return dump\n' + MAIN + TAIL, "RED"),
    ("巢狀 def 的 return,只有外層在跑",
     DUMP + 'def outer():\n    def inner():\n        return dump\n    return 1\n'
     + MAIN + '    outer()()\n' + TAIL, "RED"),
    ("死碼裡的 for 綁定 `if False: for f in [dump]: f()`",
     DUMP + MAIN + '    if False:\n        for f in [dump]:\n            f()\n' + TAIL, "RED"),
    ("死碼裡的 class body `if False: class W: run = dump` + W.run()",
     DUMP + MAIN + '    if False:\n        class W:\n            run = dump\n        W.run()\n' + TAIL, "RED"),
    ("except handler 裡的綁定(錯誤路徑,#70 的天花板)",
     DUMP + MAIN + '    try:\n        pass\n    except Exception:\n        f = dump\n        f()\n' + TAIL, "RED"),
    ("`get()` 只呼叫 factory,沒呼叫結果(票上已宣告的天花板)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    get()\n' + TAIL, "RED"),
    ("對照:factory 結果真的被呼叫 `get()()`(不得誤紅)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    get()()\n' + TAIL, "GREEN"),
    ("對照:`class W: run = dump` + `W.run()`(不得誤紅)",
     DUMP + 'class W:\n    run = dump\n' + MAIN + '    W.run()\n' + TAIL, "GREEN"),
]

BASELINES = {"--prev": "39003a3"}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cases = BINDING_SHAPES
    if "--bind-quiet" in sys.argv:
        cases = BIND_QUIET
    elif "--header" in sys.argv:
        cases = HEADER
    base = next((BASELINES[f] for f in BASELINES if f in sys.argv), None)
    sys.exit(1 if sweep60.run(sys.argv[1], cases, base) else 0)
