"""#79 同型全掃 — 「def 交出去的是不是外面那個名字」與「結果有沒有被呼叫」,兩把尺各掃一遍。

#79 把 `live_nodes` 的回傳值從「無條件 carry」改成走 `RET` key,同時把 def 內部
賦值過 / 參數的名字從 `returned` 排掉。兩個都不是一條 case,是兩個 claim:

- 尺一(誤放那邊)—「def `return` 的如果是它**自己產生**的名字,就不是外面那個死碼」。
  `local` 現在只認 `ast.Name` 的 Store 與 `arg`;def 內部產生名字的寫法不只這兩種
  (nested class / `import as` / `except as` / `match case` 捕獲…),換個寫法就撞名豁免。
  → `--own-names`
- 尺二(誤紅那邊)—「呼叫結果自己也在呼叫位置才算 live」。現在只認 `get()()`(Call 的
  func 是 Call)與 `f = get()`(Assign 右邊是 Call)兩條路;把結果送到呼叫位置的其他
  寫法(`await get()`、walrus、for 的元素)沒走到,會誤紅。→ `--result-called`

判準 oracle = #60 AC1 逐字:「真的在**會執行的位置**用 `sys.stdout.buffer.write`」。
- 真的會執行 -> 豁免(GREEN),喊住它就是誤紅。
- 跑不到 -> 不豁免(RED),放它過就是守門閉嘴(#79 要收的正是這個)。

用法:
    python scripts/qa/79-return-sweep.py <repo> --own-names       # def 自己產生的名字(誤放那邊)
    python scripts/qa/79-return-sweep.py <repo> --result-called   # 結果被呼叫的寫法(誤紅那邊)
    ... --prev                                                    # 對照組:#79 修之前(8beebc5)
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

# 尺一(誤放那邊):`def get(): <在 def 裡產生一個叫 dump 的東西>; return dump` + `get()()`。
# 每一格交出去的都是 def 自己的東西,module 那個死碼 `dump` 一行都沒跑 -> 全部該 RED。
# #79 只排掉「Name 的 Store」與「參數」兩種寫法,其餘同型的還在外面。
OWN_NAMES = [
    ("`dump = 1`(#79 已收:Name Store)",
     DUMP + 'def get():\n    dump = 1\n    return dump\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("參數同名 `def get(dump)`(#79 已收:arg)",
     DUMP + 'def get(dump):\n    return dump\n' + MAIN + '    get(1)()\n' + TAIL, "RED"),
    ("`with open() as dump`(Name Store,順帶收到)",
     DUMP + 'def get():\n    with open("x") as dump:\n        return dump\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("`for dump in [1]`(Name Store,順帶收到)",
     DUMP + 'def get():\n    for dump in [1]:\n        return dump\n    return 1\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("walrus `(dump := 1)`(Name Store,順帶收到)",
     DUMP + 'def get():\n    if (dump := 1):\n        pass\n    return dump\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("巢狀 def 同名 `def dump():` 在 get 裡",
     DUMP + 'def get():\n    def dump():\n        return 1\n    return dump\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("巢狀 class 同名 `class dump:` 在 get 裡",
     DUMP + 'def get():\n    class dump:\n        pass\n    return dump\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("`import os as dump` 在 get 裡",
     DUMP + 'def get():\n    import os as dump\n    return dump\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("`import dump` 在 get 裡",
     DUMP + 'def get():\n    import dump\n    return dump\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("`from os import path as dump` 在 get 裡",
     DUMP + 'def get():\n    from os import path as dump\n    return dump\n' + MAIN + '    get()()\n' + TAIL, "RED"),
    ("`except Exception as dump` 在 get 裡",
     DUMP + 'def get():\n    try:\n        pass\n    except Exception as dump:\n        return dump\n    return 1\n'
     + MAIN + '    get()()\n' + TAIL, "RED"),
    ("`match` 的 case 捕獲同名 `case [dump]`",
     DUMP + 'def get(v):\n    match v:\n        case [dump]:\n            return dump\n    return 1\n'
     + MAIN + '    get([1])()\n' + TAIL, "RED"),
    ("對照:`return dump` 真的是外面那個死碼 def(不得誤紅)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    get()()\n' + TAIL, "GREEN"),
]

# 尺二(誤紅那邊):`def get(): return dump` + 把**結果**送到呼叫位置的每一種寫法。
# 每一格 `dump` 都真的會跑 -> 全部該 GREEN,喊住它就是誤紅(吵的那邊)。
RESULT_CALLED = [
    ("`get()()`(#75 立的天花板)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    get()()\n' + TAIL, "GREEN"),
    ("`get()(1)` 帶引數",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    get()(1)\n' + TAIL, "GREEN"),
    ("`f = get(); f()`(#79 立的天花板)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    f = get()\n    f()\n' + TAIL, "GREEN"),
    ("`f: object = get(); f()`(AnnAssign)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    f: object = get()\n    f()\n' + TAIL, "GREEN"),
    ("`a, b = get(), 1; a()`(解包)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    a, b = get(), 1\n    a()\n' + TAIL, "GREEN"),
    ("`f = get(); g = f; g()`(alias 的 alias)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    f = get()\n    g = f\n    g()\n' + TAIL, "GREEN"),
    ("`M().get()()`(factory 是 method)",
     DUMP + 'class M:\n    def get(self):\n        return dump\n' + MAIN + '    M().get()()\n' + TAIL, "GREEN"),
    ("`class W: run = get()` + `W.run()`",
     DUMP + 'def get():\n    return dump\nclass W:\n    run = get()\n' + MAIN + '    W.run()\n' + TAIL, "GREEN"),
    ("`(f := get())()`(walrus 綁結果)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    (f := get())()\n' + TAIL, "GREEN"),
    ("`for f in [get()]: f()`(結果當元素)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    for f in [get()]:\n        f()\n' + TAIL, "GREEN"),
    ("`f = await get(); f()`(async 版的天花板)",
     DUMP + 'import asyncio\nasync def get():\n    return dump\nasync def main():\n    f = await get()\n    f()\n'
     + MAIN + '    asyncio.run(main())\n' + TAIL, "GREEN"),
    ("反方向對照:`get()` 結果丟掉(必須維持 RED)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    get()\n' + TAIL, "RED"),
    ("反方向對照:`x = get()` 從未呼叫(必須維持 RED)",
     DUMP + 'def get():\n    return dump\n' + MAIN + '    x = get()\n' + TAIL, "RED"),
    ("反方向對照:`f = await get()` 從未呼叫(必須維持 RED)",
     DUMP + 'import asyncio\nasync def get():\n    return dump\nasync def main():\n    f = await get()\n'
     + MAIN + '    asyncio.run(main())\n' + TAIL, "RED"),
]

BASELINES = {"--prev": "8beebc5"}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cases = OWN_NAMES
    if "--result-called" in sys.argv:
        cases = RESULT_CALLED
    base = next((BASELINES[f] for f in BASELINES if f in sys.argv), None)
    sys.exit(1 if sweep60.run(sys.argv[1], cases, base) else 0)
