"""#84 同型全掃 — generator body 也是 deferred code,`nodes_in` 只停在 `Lambda`。

#84 立的尺逐字:「a lambda literal parked in a live statement is *built* there,
not run there」—— 所以 `nodes_in` 走到 `Lambda` 就停,body 裡的 `Call` 不算這一行
跑到的東西。

同一把尺量下去,Python 還有另一種一模一樣的 deferred code:**generator**。

    import sys
    def dump():
        sys.stdout.buffer.write(b"x")   # 死碼,一行沒跑
    g = (dump() for _ in [1])           # 只是建了個 generator,從頭到尾沒人消費
    if __name__ == "__main__":
        print("要開的票")                 # 中文,沒 pin —— 守門卻閉嘴

`GeneratorExp` 的 body 跟 lambda body 是同一件事:寫在那裡,**被 iterate 的時候才跑**。
`nodes_in` 只 `isinstance(n, ast.Lambda)` 才停,`GeneratorExp` 照走進去 —— 裡面的
`dump()` 就被算成「這一行呼叫的」,`dump` 變 live,整檔豁免。generator function
(`def gen(): yield …`)是同一形狀的另一半:`gen()` 只是建了個 generator,body 一行沒跑,
但 `live_nodes` 把 `gen` 算成 invoked、整個 body 拉進 live 區。

判準 oracle = #60 AC1 逐字:「真的在**會執行的位置**用 `sys.stdout.buffer.write`」。
跑不到 -> 不得豁免(RED)。

**不是 #84 的 regression**:`--prev84`(`4c58eab`,#84 修之前)同一組數字一模一樣 ——
這是 #84 那把尺沒套到的另一種 deferred code,不是它改壞的。

用法:
    python scripts/qa/84-generator-sweep.py <repo> --generator
    ... --prev84                                # 對照組:#84 修之前(4c58eab)
"""
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "sweep60", str(Path(__file__).resolve().parent / "60-mention-sweep.py"))
sweep60 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep60)

DUMP = 'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\n'
GEN = 'def gen():\n    yield dump()\n'
MAIN = 'if __name__ == "__main__":\n'
TAIL = '    print("要開的票")\n'

GENERATOR = [
    ("genexp 綁著沒消費 `g = (dump() for _ in [1])`",
     DUMP + 'g = (dump() for _ in [1])\n' + MAIN + TAIL, "RED"),
    ("裸 genexp 在 live 語句 `(dump() for _ in [1])`",
     DUMP + MAIN + '    (dump() for _ in [1])\n' + TAIL, "RED"),
    ("genexp 進容器沒消費 `xs = [(dump() for _ in [1])]`",
     DUMP + 'xs = [(dump() for _ in [1])]\n' + MAIN + TAIL, "RED"),
    ("genexp 交給不消費的 def `keep(dump() for _ in [1])`",
     DUMP + 'def keep(g):\n    return g\n' + MAIN
     + '    keep(dump() for _ in [1])\n' + TAIL, "RED"),
    ("generator function 呼叫了但沒 iterate `gen()`",
     DUMP + GEN + MAIN + '    gen()\n' + TAIL, "RED"),
    ("bypass 直接寫在沒人消費的 genexp body 裡",
     'import sys\ng = (sys.stdout.buffer.write(b"x") for _ in [1])\n' + MAIN + TAIL, "RED"),
    ("對照:generator function 綁著沒呼叫(現在就是 RED,不得放掉)",
     DUMP + GEN + MAIN + TAIL, "RED"),
    ("對照:`sum(1 for _ in (dump() for _ in [1]))` 真的消費(不得誤紅)",
     DUMP + MAIN + '    sum(1 for _ in (dump() for _ in [1]))\n' + TAIL, "GREEN"),
    ("對照:`g = (dump() for _ in [1])` 之後 `list(g)`(不得誤紅)",
     DUMP + 'g = (dump() for _ in [1])\n' + MAIN + '    list(g)\n' + TAIL, "GREEN"),
    ("對照:`for _ in gen(): pass` 真的 iterate(不得誤紅)",
     DUMP + GEN + MAIN + '    for _ in gen():\n        pass\n' + TAIL, "GREEN"),
    ("對照:listcomp 不是 deferred,真的跑 `[dump() for _ in [1]]`(不得誤紅)",
     DUMP + MAIN + '    [dump() for _ in [1]]\n' + TAIL, "GREEN"),
    ("對照:bypass 寫在真的被消費的 genexp body(不得誤紅)",
     'import sys\n' + MAIN
     + '    list(sys.stdout.buffer.write(b"x") for _ in [1])\n' + TAIL, "GREEN"),
]

BASELINES = {"--prev84": "4c58eab"}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    base = next((BASELINES[f] for f in BASELINES if f in sys.argv), None)
    sys.exit(1 if sweep60.run(sys.argv[1], GENERATOR, base) else 0)
