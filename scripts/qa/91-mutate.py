"""#91 QA 的 mutation 台 — `14f69f2` 新開的九個 knob。

`/build #91` 的產出 comment 宣稱「九個 knob 逐一改壞 -> `--self-check` 全部轉紅」,
但那九個 knob **沒有一個進 repo**(`87-mutate.py` 只有 17 個,全是 #86/#87 的)。
宣稱不是證據 —— 這支把那九個補成真的跑得起來的東西,一格一格量。

每個 knob 對應 `asyncio_graph` / `from_asyncio` / `drives` 裡「拿掉就會漏掉一種
形狀」的那一行。改壞之後 `validate.py --self-check` 要轉紅;紅不了就表示那條判準
沒有證據住在預設會跑的地方。

用法(由 `91-walkthrough.sh` 呼叫):
    python scripts/qa/91-mutate.py <repo 副本> <knob 名稱>
    python scripts/qa/91-mutate.py --list
"""
import pathlib
import sys

KNOBS = {
    # `drives` 整條放行 —— 任何 call 都算驅動(誤放那面的極端)
    "drives_always_true": ("""    roots, funcs = driven
    f = node.func""",
                           """    return True
    roots, funcs = driven
    f = node.func"""),
    # 退回 name-only:receiver 不看了,`subprocess.run` 那個開關重開
    "drives_name_only": ("""    if isinstance(f, ast.Attribute):
        return f.attr in DRIVEN_BY and from_asyncio(f.value, roots, funcs)
    return isinstance(f, ast.Name) and funcs.get(f.id) in DRIVEN_BY""",
                         """    if isinstance(f, ast.Attribute):
        return f.attr in DRIVEN_BY
    return isinstance(f, ast.Name) and f.id in DRIVEN_BY"""),
    # `from asyncio import run` 進來的裸名字不算驅動 —— 誤紅那面
    "drives_no_from_import": (
        """    return isinstance(f, ast.Name) and funcs.get(f.id) in DRIVEN_BY""",
        """    return False"""),
    # `import asyncio as aio` 的 alias 不追 —— 誤紅
    "graph_no_alias": ("""                    roots.add(a.asname or a.name.split(".")[0])""",
                       """                    roots.add(a.name.split(".")[0])"""),
    # fixpoint 拿掉 —— `loop = asyncio.new_event_loop()` 追不到,誤紅
    "graph_no_fixpoint": ("""    while True:  # `loop = asyncio.new_event_loop()` is asyncio's too""",
                          """    return roots, funcs
    while True:  # `loop = asyncio.new_event_loop()` is asyncio's too"""),
    # `with asyncio.Runner() as r` 的綁定不收 —— 誤紅
    "graph_no_withitem": ("""        elif isinstance(n, ast.withitem) and n.optional_vars is not None:
            pairs.append((n.optional_vars, n.context_expr))""",
                          """        elif False:
            pass"""),
    # asyncio 交出來的「任何東西」都算 loop —— `ok.run(c)` 從檔案內部再開一次開關
    "loop_from_anything": ("""            return funcs.get(f.id) in LOOP_FROM
        return (isinstance(f, ast.Attribute) and f.attr in LOOP_FROM
                and from_asyncio(f.value, roots, funcs))""",
                           """            return f.id in funcs
        return (isinstance(f, ast.Attribute)
                and from_asyncio(f.value, roots, funcs))"""),
    # imported name 不必被 call 就算 loop —— `x = sleep` 之後 `x.run(c)` 算驅動,誤放
    "loop_from_bare_name": ("""    if isinstance(expr, ast.Name):
        return expr.id in roots""",
                            """    if isinstance(expr, ast.Name):
        return expr.id in roots or expr.id in funcs"""),
    # `consumes` 退回 #87 的 name-only 那一行 —— 兩面同時重開
    "revert_to_name_list": ("""        if ((name in CONSUMED_BY and name not in shadowed)
                or drives(node, driven)):""",
                            """        if name in CONSUMED_BY | DRIVEN_BY and name not in shadowed:"""),
}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--list" in sys.argv:
        print("\n".join(sorted(KNOBS)))
        sys.exit(0)
    path = pathlib.Path(sys.argv[1]) / "scripts" / "validate.py"
    src = path.read_text(encoding="utf-8")
    old, new = KNOBS[sys.argv[2]]
    assert old in src, "mutation 目標不在 — 判準被改過了"
    path.write_text(src.replace(old, new, 1), encoding="utf-8")
    print("mutation 已套用:", sys.argv[2])
