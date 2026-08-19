"""#81 同型全掃 — `own_scope` 停在 `Lambda`,但 return 值的名字採集沒停。

#81 把 `local` 從「兩種 node」擴成 `binds` 的八個 branch,收齊「def 內部產生的
名字」整面。但那一面是靠 `own_scope` 走出來的,而 `own_scope` **停在** `Lambda`
—— 於是 lambda 綁的名字進不了 `local`。同一個 `return` 的另一半
(`names_in(n.value)`)卻**照樣鑽進 lambda 的 body**,兩邊不對稱:

    def get():
        return (lambda dump: dump)(1)   # 交出去的是 lambda 的參數,不是外面那個死碼

`names_in` 撿到 body 裡的 `dump`,`local` 撿不到 lambda 的 arg,相減之後 `dump`
留在 `RET+get` 裡 → `get()()` 一行整檔豁免,而 module 那個死碼 `dump` 一行沒跑。
這正是 #79 收掉的 `def get(): dump = 1; return dump`,只是換成 lambda 綁。

`binds` 的 docstring 直接寫了「a `Lambda`'s args are unreachable because
`own_scope` stops at one」—— 那句話是錯的:`own_scope` 停在 lambda 只讓
**綁定**看不到,**名字**還是被 `names_in` 撿走了。

同一個不對稱的第二種吃法:return 出去的**就是** lambda 本身。`get()()` 呼叫的
是那個 lambda,lambda 只是把 `dump` 交出來、沒有呼叫它 —— 一樣一行沒跑,一樣豁免。

判準 oracle = #60 AC1 逐字:「真的在**會執行的位置**用 `sys.stdout.buffer.write`」。
跑不到 -> 不得豁免(RED)。

用法:
    python scripts/qa/81-lambda-sweep.py <repo> --lambda-scope
    ... --prev81                                # 對照組:#81 修之前(b43137f)
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

LAMBDA_SCOPE = [
    ("lambda 的參數撞名,馬上呼叫 `return (lambda dump: dump)(1)`",
     DUMP + 'def get():\n    return (lambda dump: dump)(1)\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("lambda 存進變數再呼叫 `f = lambda dump: dump; return f(1)`",
     DUMP + 'def get():\n    f = lambda dump: dump\n    return f(1)\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("交出去的就是 lambda 本身 `return lambda dump: dump`",
     DUMP + 'def get():\n    return lambda dump: dump\n' + MAIN + '    get()(1)\n' + TAIL, "RED"),
    ("交出去的 lambda 只是把 dump 再交出來 `return lambda: dump`",
     DUMP + 'def get():\n    return lambda: dump\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("dump 只當 lambda 的預設引數 `return lambda x=dump: x`",
     DUMP + 'def get():\n    return lambda x=dump: x\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("lambda 包在容器裡再取出來 `return (lambda: dump,)[0]`",
     DUMP + 'def get():\n    return (lambda: dump,)[0]\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("巢狀 lambda `return (lambda: (lambda: dump))()`",
     DUMP + 'def get():\n    return (lambda: (lambda: dump))()\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("對照:lambda 呼叫的結果真的是外面那個死碼 `f = lambda: dump; return f()`(不得誤紅)",
     DUMP + 'def get():\n    f = lambda: dump\n    return f()\n' + MAIN + '    get()()\n' + TAIL, "GREEN"),
    ("對照:`return dump` 真的是外面那個死碼 def(不得誤紅)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    get()()\n' + TAIL, "GREEN"),
]

BASELINES = {"--prev81": "b43137f"}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    base = next((BASELINES[f] for f in BASELINES if f in sys.argv), None)
    sys.exit(1 if sweep60.run(sys.argv[1], LAMBDA_SCOPE, base) else 0)
