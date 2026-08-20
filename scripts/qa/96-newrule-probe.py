"""#96 的原型 —— #60 AC1 改判準之後,守門長什麼樣、誰會被判紅。

這支是 spec #96 那些數字的出處,不是產品程式。#96 主張把「bypass 真的出現在會被
執行的位置」換成「pin 出現在 `__main__` 的第一層」,理由是前者是 halting problem、
後者是語法比對。這支把後者寫出來跑一遍,量「照新規則,repo 裡有幾個檔要改」。

答案:22 個檔裡 **21 個一行都不用改**,只有 `scripts/hooks/triage-to-maintain.py`
缺兩行(它是 repo 裡唯一用 `.buffer` bypass 的檔)。

用法:
    python scripts/qa/96-newrule-probe.py .

寫這支的過程本身踩到兩次同一個坑,記在這裡:`ast.unparse` 吐的是單引號,拿雙引號
的字面值去比對會**靜靜地全部不 match**,而「全部不 match」在這條規則下長得跟「全部
合格」一模一樣(第一次跑出「不合 0」)。所以兩邊都要過 `norm()`。這跟 #87 QA 記過的
「baseline flag 不認得就靜默跑現況」是同一個形狀 —— 守門類的東西,不 match 要吵。

規則(全部是語法):有 `__main__` block 的檔案,必須在那個 block 的**第一層**
出現 `sys.stdout.reconfigure(encoding="utf-8")`;檔案裡提到 sys.stdin 的話,
同樣要有 stdin 那行。沒有 bypass、沒有豁免、沒有可達性。
"""
import ast
import sys
from pathlib import Path

MAIN_TEST = ast.unparse(ast.parse('__name__ == "__main__"').body[0].value)
def norm(stmt):
    """同一段程式的唯一寫法 —— 引號、空白的差別在這裡被抹平。"""
    return ast.unparse(ast.parse(stmt).body[0])


PINS = [("stdout", norm('sys.stdout.reconfigure(encoding="utf-8")')),
        ("stdin", norm('sys.stdin.reconfigure(encoding="utf-8")'))]


def issues(repo):
    out = []
    for py in sorted(Path(repo).rglob("*.py")):
        # 跟 validate.py 的 `is_source` 同步:只擋 __pycache__ 與 . 開頭的目錄。
        # 這支是第二把尺,判準要各自寫;但受檢範圍對不齊的話,兩邊的答案不同
        # 就分不出是判準有差還是根本沒看到同一批檔(#68)。
        if any(p == "__pycache__" or p.startswith(".")
               for p in py.relative_to(repo).parts):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            out.append(f"{py}: 讀不進來(SyntaxError)")
            continue
        # 「這支讀 stdin 嗎」看 AST 的 `sys.stdin`,不看原始碼字串 —— 不然
        # 守門自己的規則表裡那句字面值就會被算成「讀了 stdin」
        reads_stdin = any(
            isinstance(n, ast.Attribute) and n.attr == "stdin"
            and getattr(n.value, "id", None) == "sys" for n in ast.walk(tree))
        mains = [n for n in ast.walk(tree)
                 if isinstance(n, ast.If) and ast.unparse(n.test) == MAIN_TEST]
        if not mains:
            continue
        for stream, pin in PINS:
            if stream == "stdin" and not reads_stdin:
                continue
            # 「第一層」= block body 的直屬 statement,巢狀進 if/try 的不算。
            # 每一個 __main__ 都要自己寫到 —— 一個 block 有 pin 不會蓋過另一個
            # 沒 pin 的(#69)。這裡寫成 any 的話,兩把尺對同一份 repo 會給
            # 相反的答案,而 repo 裡剛好沒有雙 block 的檔,誰都不會發現。
            ok = all(any(isinstance(s, ast.Expr) and ast.unparse(s) == pin
                         for s in m.body)
                     for m in mains)
            if not ok:
                out.append(f"{py.relative_to(repo).as_posix()}: 缺 {stream} pin")
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    bad = issues(sys.argv[1])
    print("\n".join(bad) if bad else "OK 新規則下全綠")
    print(f"\n不合 {len(bad)}")
