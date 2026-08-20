"""#86 QA 的 mutation 台 — 把 `de68088` 的十四個 knob 逐一改壞。

每個 knob 對應修法裡「拿掉就會漏掉一種形狀」的那一行。改壞之後
`validate.py --self-check` 要轉紅;紅不了就表示那條判準沒有證據住在預設會跑的地方。

用法(由 `86-walkthrough.sh` 呼叫):
    python scripts/qa/86-mutate.py <repo 副本> <knob 名稱>
"""
import pathlib
import sys

KNOBS = {
    # names_in 不再停在 GeneratorExp —— 名字那半退回 #86 修之前
    "names_in_no_gen_stop": ("""        if isinstance(n, ast.GeneratorExp):
            stack.append(n.generators[0].iter)
            continue
""", ""),
    # 停了但第一個 for 的 iterable 不推回去 —— 它在 literal 位置就 evaluate,會誤紅
    "names_in_no_first_iter": ("""        if isinstance(n, ast.GeneratorExp):
            stack.append(n.generators[0].iter)
            continue
""", """        if isinstance(n, ast.GeneratorExp):
            continue
"""),
    # nodes_in 不再停在 GeneratorExp —— #86 的原病,退回走進 genexp body
    "nodes_in_no_gen_stop": ("""        if isinstance(n, ast.GeneratorExp) and n not in through:
            stack.append(n.generators[0].iter)
            continue
""", ""),
    # nodes_in 停了但第一個 iterable 不推回去
    "nodes_in_no_first_iter": ("""        if isinstance(n, ast.GeneratorExp) and n not in through:
            stack.append(n.generators[0].iter)
            continue
""", """        if isinstance(n, ast.GeneratorExp) and n not in through:
            continue
"""),
    # consumes 不認會抽乾 iterable 的那 15 個 builtin
    "consumes_no_builtins": ("""    if isinstance(node, ast.Call):
        name = getattr(node.func, "id", getattr(node.func, "attr", None))
        if name in CONSUMED_BY and name not in shadowed:
            return list(node.args) + [k.value for k in node.keywords]
""", ""),
    # consumes 不認 `for` 的 iterable
    "consumes_no_for": ("""    if isinstance(node, (ast.For, ast.AsyncFor)):
        return [node.iter]
""", ""),
    # 被消費的 genexp,它自己的 iterable 不再算被 iterate
    "consumes_no_nested_gen": (
        """        return [c.iter for c in node.generators] if node in through else []""",
        """        return []"""),
    # 當場跑完的 comprehension 的 iterable 不算消費
    "consumes_no_comp": ("""    if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
        return [c.iter for c in node.generators]
""", ""),
    # 模組自己綁過的名字照樣當那個 builtin —— `def sorted(g): return g` 又變開關
    "consumes_no_shadow": ("""        if name in CONSUMED_BY and name not in shadowed:""",
                           """        if name in CONSUMED_BY:"""),
    # generator def 被呼叫又算成 body 跑了
    "gens_not_subtracted": (
        """        fresh = (((invoked - gens) | eaten_calls) & set(defs)) - live""",
        """        fresh = ((invoked | eaten_calls) & set(defs)) - live"""),
    # 在消費位置被呼叫的 generator def 不算跑 —— 誤紅那面
    "no_eaten_calls": ("""                    elif isinstance(e, ast.Call):
                        eaten_calls |= names_in(e.func)
""", ""),
    # `g = (…)` 之後 `list(g)`,透過名字消費不算
    "no_eaten_via_name": (
        """        for name in eaten_names & set(gen_of):  # `g = (…); list(g)` — #86
            eaten_gens |= gen_of[name]
""", ""),
    # through 不帶被消費的 genexp —— body 裡的 bypass 查不到
    "through_no_gens": ("""                                   or [set()]) | eaten_gens""",
                        """                                   or [set()])"""),
    # 發現新的被消費 genexp 不重跑 fixpoint
    "no_gen_fixpoint": ("""        if not fresh and before == len(eaten_gens):""",
                        """        if not fresh:"""),
}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    path = pathlib.Path(sys.argv[1]) / "scripts" / "validate.py"
    src = path.read_text(encoding="utf-8")
    old, new = KNOBS[sys.argv[2]]
    assert old in src, "mutation 目標不在 — 判準被改過了"
    path.write_text(src.replace(old, new, 1), encoding="utf-8")
    print("mutation 已套用:", sys.argv[2])
