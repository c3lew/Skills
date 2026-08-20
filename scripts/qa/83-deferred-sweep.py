"""#83 同型全掃 — lambda body 是 deferred code,但 `live_nodes` 走 live 語句時沒停在 `Lambda`。

#83 把「lambda body 在**被呼叫時**才跑」這條邊界套進 `names_in`(不下鑽 `Lambda`)
與 `free_in`(真的被呼叫的位置才展開)。拿同一把尺量下去,`live_nodes` 還有一面
沒套:它把 live 語句 `ast.walk` 一遍,凡是 `Call` 就把 func 的名字算成 invoked ——
**lambda body 裡的 Call 也照收**,不管那個 lambda 有沒有人呼叫:

    import sys
    def dump():
        sys.stdout.buffer.write(b"x")   # 死碼,沒人呼叫
    f = lambda: dump()                  # 只是綁著,f 從頭到尾沒被呼叫
    if __name__ == "__main__":
        print("要開的票")                 # 中文,沒 pin —— 守門卻閉嘴

`dump` 一行沒跑,守門照樣豁免整檔 —— 跟 #83 收掉的 `return lambda: dump` 是同一個
形狀,只是換成「lambda 待在 live 語句裡、沒人呼叫」。

判準 oracle = #60 AC1 逐字:「真的在**會執行的位置**用 `sys.stdout.buffer.write`」。
跑不到 -> 不得豁免(RED)。

**不是 #83 的 regression**:`--prev83`(`d192aa9`,#83 修之前)同一組數字一模一樣。

用法:
    python scripts/qa/83-deferred-sweep.py <repo> --deferred
    ... --prev83                                # 對照組:#83 修之前(d192aa9)
"""
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "sweep60", str(Path(__file__).resolve().parent / "60-mention-sweep.py"))
sweep60 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep60)

DUMP = 'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\n'
TAIL = '    print("要開的票")\n'
MAIN = 'if __name__ == "__main__":\n'

DEFERRED = [
    ("綁著沒呼叫 `f = lambda: dump()`",
     DUMP + 'f = lambda: dump()\n' + MAIN + TAIL, "RED"),
    ("list 裡的 lambda 沒呼叫 `xs = [lambda: dump()]`",
     DUMP + 'xs = [lambda: dump()]\n' + MAIN + TAIL, "RED"),
    ("dict 裡的 lambda 沒呼叫 `d = {\"k\": lambda: dump()}`",
     DUMP + 'd = {"k": lambda: dump()}\n' + MAIN + TAIL, "RED"),
    ("裸 lambda literal 在 live 位置沒呼叫 `(lambda: dump())`",
     DUMP + MAIN + '    (lambda: dump())\n' + TAIL, "RED"),
    ("comprehension 裡的 lambda 沒呼叫 `[lambda: dump() for _ in []]`",
     DUMP + 'xs = [lambda: dump() for _ in []]\n' + MAIN + TAIL, "RED"),
    ("三元裡的 lambda 沒呼叫 `None if xs else (lambda: dump())`",
     DUMP + 'f = None if xs else (lambda: dump())\n' + MAIN + TAIL, "RED"),
    ("def 內就地呼叫但結果丟掉 `return (lambda: dump)()` 配 `get()`",
     DUMP + 'def get():\n    return (lambda: dump)()\n' + MAIN + '    get()\n' + TAIL, "RED"),
    ("對照:`return (lambda: dump())()` 配 `get()` —— lambda 就地被呼叫、dump 真的跑(不得誤紅)",
     DUMP + 'def get():\n    return (lambda: dump())()\n' + MAIN + '    get()\n' + TAIL, "GREEN"),
    ("對照:`def g(cb=lambda: dump())` 預設引數,g 沒被呼叫(現在就是 RED,不得放掉)",
     DUMP + 'def g(cb=lambda: dump()):\n    pass\n' + MAIN + TAIL, "RED"),
    ("對照:`f = lambda: dump()` 且真的 `f()`(不得誤紅)",
     DUMP + 'f = lambda: dump()\n' + MAIN + '    f()\n' + TAIL, "GREEN"),
    ("對照:`(lambda: dump())()` 就地呼叫(不得誤紅)",
     DUMP + MAIN + '    (lambda: dump())()\n' + TAIL, "GREEN"),
]

BASELINES = {"--prev83": "d192aa9"}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    base = next((BASELINES[f] for f in BASELINES if f in sys.argv), None)
    sys.exit(1 if sweep60.run(sys.argv[1], DEFERRED, base) else 0)
