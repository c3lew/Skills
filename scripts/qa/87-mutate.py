"""#87 QA 的 mutation 台 — `c51ba98` 的三個 knob,加上 `de68088` 十四個的重錨。

每個 knob 對應修法裡「拿掉就會漏掉一種形狀」的那一行。改壞之後
`validate.py --self-check` 要轉紅;紅不了就表示那條判準**沒有證據住在預設會跑的
地方** —— 只有 QA sweep 抓得到,下一個人改壞它不會有人知道。

`c51ba98` 的三個 knob(`gens_no_async` / `consumes_no_await` / `consumes_no_driven`)
就是這種:那顆 commit 一條 self-check fixture 都沒補。第四個 `driven_attr_id_only`
不是 mutation,是 finding 的證據 —— 把 `DRIVEN_BY` 的 callee 從「名字」收成「只認
`Name.id`」,`--driven-attr` 那八格就翻回 RED。

用法(由 `87-walkthrough.sh` 呼叫):
    python scripts/qa/87-mutate.py <repo 副本> <knob 名稱>
"""
import pathlib
import sys

# #87 自己的三個
NEW = {
    # async def 不再進 gens —— 呼叫一個 coroutine 又算成 body 跑了(#87 原病)
    "gens_no_async": ("""            if isinstance(node, ast.AsyncFunctionDef)  # a coroutine — #87
            or any(isinstance(n, (ast.Yield, ast.YieldFrom))""",
                      """            if any(isinstance(n, (ast.Yield, ast.YieldFrom))"""),
    # await 的 operand 不算被驅動 —— 誤紅那面
    "consumes_no_await": ("""    if isinstance(node, (ast.YieldFrom, ast.Await)):""",
                          """    if isinstance(node, ast.YieldFrom):"""),
    # 交給 event loop 的那七個名字不算驅動 —— 誤紅那面
    "consumes_no_driven": ("""        if name in CONSUMED_BY | DRIVEN_BY and name not in shadowed:""",
                           """        if name in CONSUMED_BY and name not in shadowed:"""),
    # 不是 mutation,是 finding 的證據:DRIVEN_BY 只認 `Name.id`,不吃 attribute
    "driven_attr_id_only": ("""        name = getattr(node.func, "id", getattr(node.func, "attr", None))
        if name in CONSUMED_BY | DRIVEN_BY and name not in shadowed:""",
                            """        name = getattr(node.func, "id", getattr(node.func, "attr", None))
        if getattr(node.func, "id", None) is None and name in DRIVEN_BY:
            return []
        if name in CONSUMED_BY | DRIVEN_BY and name not in shadowed:"""),
}

# de68088 的十四個 —— `c51ba98` 動過 `consumes` 兩行,兩個 knob 的錨要跟著更新
_spec = __import__("importlib.util", fromlist=["util"]).spec_from_file_location(
    "mutate86", str(pathlib.Path(__file__).resolve().parent / "86-mutate.py"))
_m86 = __import__("importlib.util", fromlist=["util"]).module_from_spec(_spec)
_spec.loader.exec_module(_m86)

KNOBS = dict(_m86.KNOBS)
KNOBS["consumes_no_builtins"] = ("""    if isinstance(node, ast.Call):
        name = getattr(node.func, "id", getattr(node.func, "attr", None))
        if name in CONSUMED_BY | DRIVEN_BY and name not in shadowed:
            return list(node.args) + [k.value for k in node.keywords]
""", "")
KNOBS["consumes_no_shadow"] = (
    """        if name in CONSUMED_BY | DRIVEN_BY and name not in shadowed:""",
    """        if name in CONSUMED_BY | DRIVEN_BY:""")
KNOBS.update(NEW)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    path = pathlib.Path(sys.argv[1]) / "scripts" / "validate.py"
    src = path.read_text(encoding="utf-8")
    old, new = KNOBS[sys.argv[2]]
    assert old in src, "mutation 目標不在 — 判準被改過了"
    path.write_text(src.replace(old, new, 1), encoding="utf-8")
    print("mutation 已套用:", sys.argv[2])
