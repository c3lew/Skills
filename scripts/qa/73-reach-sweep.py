"""#73 同型全掃 — 「走得到」的判準,兩個方向各掃一遍。

#73 把 `live_nodes` 的可達性從「名字被**提到**」收回「名字在**呼叫位置**」。
一條判準改了方向,不是一條 case:凡是「callable 真的被執行,但名字沒有literally
出現在 `Call.func` / call 引數」的寫法都是同一形狀(誤紅那邊),凡是「名字出現在
某個 call 的引數、但那個 call 根本不呼叫它」的寫法也都是同一形狀(誤放那邊)。
這支把兩個母體一次列完。

判準 oracle = #60 AC1 逐字:「真的在**會執行的位置**用 `sys.stdout.buffer.write`」。
- 真的會執行 -> 豁免(GREEN),喊住它就是誤紅。
- 跑不到 -> 不豁免(RED),放它過就是守門閉嘴。

用法:
    python scripts/qa/73-reach-sweep.py <repo> --binding    # 綁定形狀(誤紅那邊)
    python scripts/qa/73-reach-sweep.py <repo> --arg-widen  # 引數即呼叫(誤放那邊)
    ... --prev                                              # 對照組:#73 修之前(e56789c)
    ... --prev75                                            # 對照組:#75 修之前(39003a3)
"""
import importlib.util
import sys
from pathlib import Path

# 60-mention-sweep 的檔名開頭是數字,一般 import 不了 — 直接照路徑載進來借它的 run()。

_spec = importlib.util.spec_from_file_location(
    "sweep60", str(Path(__file__).resolve().parent / "60-mention-sweep.py"))
sweep60 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep60)

DUMP = 'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\n'
TAIL = '    print("要開的票")\n'

# 第一型:callable 真的被執行,但名字沒有出現在 Call.func / call 引數。
# #73 的綁定規則只認 `t = <expr>` 且 t 是裸 Name 的形狀,同型的其他綁定寫法全落在外面。
# 每條都留一個真的 print(,不然「沒 print 就豁免」會用另一個理由讓它變綠。
BINDING = [
    ("對照:alias `f = dump; f()`(#71 修好的形狀,不得誤紅)",
     DUMP + 'f = dump\nif __name__ == "__main__":\n    f()\n' + TAIL, "GREEN"),
    ("for 迴圈變數 `for f in [dump]: f()`",
     DUMP + 'if __name__ == "__main__":\n    for f in [dump]:\n        f()\n' + TAIL, "GREEN"),
    ("tuple 解包 `a, b = dump, dump; a()`",
     DUMP + 'if __name__ == "__main__":\n    a, b = dump, dump\n    a()\n' + TAIL, "GREEN"),
    ("帶型別註記的綁定 `f: object = dump; f()`",
     DUMP + 'if __name__ == "__main__":\n    f: object = dump\n    f()\n' + TAIL, "GREEN"),
    ("factory 回傳 callable `def get(): return dump` + `get()()`",
     DUMP + 'def get():\n    return dump\nif __name__ == "__main__":\n    get()()\n' + TAIL, "GREEN"),
    ("class 屬性 `class W: run = dump` + `W.run()`",
     DUMP + 'class W:\n    run = dump\nif __name__ == "__main__":\n    W.run()\n' + TAIL, "GREEN"),
]

# 第二型:名字被交給某個 call 當引數就算「被呼叫」。#73 的 docstring 說這個
# approximation「只留在『呼叫是這段程式碼的自然讀法』的兩個形狀」,但實作認的是
# 任何 call 的任何引數 —— 於是一行 `print(dump)` 就把死碼裡的 bypass 拉成 live,
# 守門閉嘴。這正是 #73 自己列的「一行就能還原的開關」。
ARG_WIDEN = [
    ("對照:`run(dump)`,run 真的呼叫它(#71 的 callback,不得誤紅)",
     DUMP + 'def run(cb):\n    cb()\nif __name__ == "__main__":\n    run(dump)\n' + TAIL, "GREEN"),
    ("對照:名字完全沒被提到(#70 的天花板)",
     DUMP + 'if __name__ == "__main__":\n' + TAIL, "RED"),
    ("`print(dump)` — 印出 function 物件,沒有呼叫它",
     DUMP + 'if __name__ == "__main__":\n    print(dump)\n', "RED"),
    ("`x = str(dump)` — 引數,但 str 不會呼叫它",
     DUMP + 'if __name__ == "__main__":\n    x = str(dump)\n' + TAIL, "RED"),
    ("`x = len([dump])` — 名字包在 list 裡當引數",
     DUMP + 'if __name__ == "__main__":\n    x = len([dump])\n' + TAIL, "RED"),
    ("`print(f\"{dump}\")` — 名字在 f-string 的引數裡",
     DUMP + 'if __name__ == "__main__":\n    print(f"{dump}")\n', "RED"),
    ("`isinstance(dump, object)` — 關鍵字/位置引數都一樣",
     DUMP + 'if __name__ == "__main__":\n    x = isinstance(dump, object)\n' + TAIL, "RED"),
]

BASELINES = {"--prev": "e56789c", "--prev75": "39003a3"}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cases = ARG_WIDEN if "--arg-widen" in sys.argv else BINDING
    base = next((BASELINES[f] for f in BASELINES if f in sys.argv), None)
    sys.exit(1 if sweep60.run(sys.argv[1], cases, base) else 0)
