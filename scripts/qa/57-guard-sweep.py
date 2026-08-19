#!/usr/bin/env python
"""#57 QA 同型全掃:validate.py 裡「用關鍵詞證明某句指示存在」的 guard,繞過方向咬不咬得到。

判準:docs/disciplines(= skills/*/references)的 written-evidence「Mutation 要驗兩種:
改壞 / 繞過」。只驗改壞的 guard 守的是那個關鍵詞,不是那句主張。

母體用數的,不用「所有」:先把 validate.py 每個 errors.append 點列出來分類,
再對受測那一類逐支驗兩個方向,並附一支兩個方向都咬得到的對照組證明驗法有效。

用法:python scripts/qa/57-guard-sweep.py <repo root>
"""
import sys
import pathlib

NL = chr(10)

# 受測形狀:判「錯了」的依據是一個關鍵詞在不在散文裡
PROSE_KEYWORD = ("unpushed_commit_link_issue", "missing_blocking_audit_issue")
# 對照組:同樣讀散文,但判準是「兩個東西有沒有出現在同一個 span 裡」
PROSE_SPAN = ("find_slash_only_handoffs",)


def guard_sites(src):
    """每個 errors.append 點,配上它最近的那個 if/for 條件。"""
    sites = []
    needle = "errors.append("
    pos = src.find(needle)
    while pos != -1:
        line = src[:pos].count(NL) + 1
        before = src[:pos].split(NL)
        cond = "?"
        for l in reversed(before):
            s = l.strip()
            if s.startswith(("if ", "for ", "elif ")):
                cond = s
                break
        sites.append((line, cond))
        pos = src.find(needle, pos + 1)
    return sites


def classify(cond):
    if any(n in cond for n in PROSE_KEYWORD):
        return "prose-keyword(受測形狀)"
    if any(n in cond for n in PROSE_SPAN):
        return "prose-span(對照組)"
    if "bypass in text" in cond:
        return "code-position"
    return "結構/存在性"


ORDER = ["prose-keyword(受測形狀)", "prose-span(對照組)", "code-position", "結構/存在性"]


def main(root):
    root = pathlib.Path(root)
    sys.path.insert(0, str(root / "scripts"))
    import validate as V

    src = (root / "scripts" / "validate.py").read_text(encoding="utf-8")
    sites = guard_sites(src)
    buckets = {k: [] for k in ORDER}
    for line, cond in sites:
        buckets[classify(cond)].append((line, cond))

    print("validate.py 一共 %d 個 errors.append 點,分成 %d 類:" % (len(sites), len(ORDER)))
    for name in ORDER:
        rows = buckets[name]
        print("  %s:%d 個 -> %s" % (name, len(rows), [("L%d" % l) for l, _ in rows]))
        for l, c in rows:
            print("      L%d  %s" % (l, c[:80]))
    tested = buckets["prose-keyword(受測形狀)"]
    print()
    print("受測形狀 = prose-keyword(用一個關鍵詞證明「某句指示存在」)。母體 %d 個,"
          "下面每一個都驗兩個方向。" % len(tested))
    assert tested, "母體空了 — 沒有 prose-keyword guard 可掃,這支自己失敗"
    print()

    print("1) missing_blocking_audit_issue(#57 新增)")
    print("   改壞(整句刪掉)            ->",
          V.missing_blocking_audit_issue("呼叫 `/to-tickets` 切票"), "(True = 咬到)")
    print("   繞過(條件詞留著、動作反過來) ->",
          V.missing_blocking_audit_issue(
              "呼叫 `/to-tickets` 切票。一張 blocking 邊都沒宣告的時候,直接發佈,不用問 client。"),
          "(True = 咬到)")

    print("2) unpushed_commit_link_issue(既有,同形狀)")
    print("   改壞(有 commit link、沒 push)       ->",
          V.unpushed_commit_link_issue("在票上附 commit link"), "(True = 咬到)")
    print("   繞過(push 出現在前面但講的是別的事)  ->",
          V.unpushed_commit_link_issue("不要 git push,直接在票上附 commit link"), "(True = 咬到)")

    print()
    print("3) find_slash_only_handoffs(對照組:span-scoped 共現,不是單一關鍵詞)")
    print("   改壞(拿掉 Codex 半)         ->",
          V.find_slash_only_handoffs("下一步:`/qa #12`"), "(非空 = 咬到)")
    print("   繞過(Codex 半移到 span 外)   ->",
          V.find_slash_only_handoffs("下一步:`/qa #12`" + NL + "`$qa #12`"), "(非空 = 咬到)")
    print("   對照組兩個方向都咬得到 -> 驗法本身有效,上面那兩個 False 是那兩支 guard 的性質,"
          "不是這支掃描壞掉。")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1])
