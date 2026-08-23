# -*- coding: utf-8 -*-
"""#130 QA 的修前對照 —— 同一份母體,修前(2ebbc89^)vs 修後(工作區)。

#130 動的是**判斷邏輯**:`spec` 那格併進 `NUMBER_SCALARS`,在 `main` 一次收成
int。入口的正規化 = 收緊 —— 以前靜靜跑過去、印出一段貼不動的指令的形狀,現在
有一部分會當場停。所以「修後 self-check 綠」證明不了「本來好的批次沒被改壞」,
要真的把修前那份跑起來,對**同一份母體**逐批比。

母體直接用 `130-wide.py` 的 `cases()`(4 個印 spec 的 mode x 3 種其他票號格子的
型別混用 x 15 種 `spec` 寫法 = 180 批),判準也用它的 `check()` —— 那是這條 lane
自己寫的第二把尺,不是受測物那面。

三欄差額:
  - **修前紅 / 修後綠** —— 這張票修掉的東西。這一欄空的 = 沒修到。
  - **修前綠 / 修後紅** —— 本輪引入的 regression。一律 blocking,exit 非 0。
  - 兩邊都紅 / 兩邊都綠 —— 只記數。

另外單獨列一欄「行為變了但兩邊都不算違例」的批次(stdout / exit code 有差),
讓收緊面看得見:哪些形狀從「靜靜跑過去」變成「當場停」。

用法:
    python 130-prevdiff.py
"""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import importlib.util

_spec = importlib.util.spec_from_file_location("wide130", HERE / "130-wide.py")
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)

FIX = "2ebbc89"
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="prevdiff130-"))
BEFORE = _TMP / "batch_before.py"
BEFORE.write_bytes(subprocess.run(
    ["git", "-C", str(ROOT), "show", f"{FIX}^:skills/build-batch/batch.py"],
    check=True, stdout=subprocess.PIPE).stdout)
AFTER = ROOT / "skills" / "build-batch" / "batch.py"   # 工作區(= HEAD 2ebbc89)


def main():
    fixed, introduced, both_bad, both_ok, behaviour = [], [], [], 0, []
    total = 0
    for name, payload in W.cases():
        total += 1
        b_bad, _ = W.check(BEFORE, name, payload)
        a_bad, _ = W.check(AFTER, name, payload)
        if b_bad and not a_bad:
            fixed.append((name, b_bad))
        elif a_bad and not b_bad:
            introduced.append((name, a_bad))
        elif a_bad and b_bad:
            both_bad.append((name, b_bad, a_bad))
        else:
            both_ok += 1
        rb = W.run(BEFORE, payload)
        ra = W.run(AFTER, payload)
        if (rb[0], rb[1]) != (ra[0], ra[1]):
            behaviour.append((name, rb[0], ra[0],
                              rb[1].strip().splitlines()[-1] if rb[1].strip() else "",
                              ra[1].strip().splitlines()[-1] if ra[1].strip() else ""))

    print(f"修前 = {FIX}^ 的 batch.py,修後 = 工作區")
    print(f"母體 {total} 批(= 130-wide.py 的 cases())")
    print("")
    print(f"== 修前紅 / 修後綠 —— 這張票修掉的:{len(fixed)} 批 ==")
    for name, b in fixed:
        print(f"  {name}")
        for rule, msg in b:
            print(f"        修前 [{rule}] {msg}")
    if not fixed:
        print("  (無 —— 這一欄空的表示沒修到)")
    print("")
    print(f"== 修前綠 / 修後紅 —— 本輪引入的 regression:{len(introduced)} 批 ==")
    for name, a in introduced:
        print(f"  {name}")
        for rule, msg in a:
            print(f"        修後 [{rule}] {msg}")
    if not introduced:
        print("  (無)")
    print("")
    print(f"== 兩邊都紅:{len(both_bad)} 批 ==")
    for name, b, a in both_bad:
        print(f"  {name}")
        for rule, msg in b:
            print(f"        修前 [{rule}] {msg}")
        for rule, msg in a:
            print(f"        修後 [{rule}] {msg}")
    if not both_bad:
        print("  (無)")
    print("")
    print(f"== 兩邊都綠:{both_ok} 批 ==")
    print("")
    print(f"== 行為有差(exit code 或 stdout 不逐字相同):{len(behaviour)} 批 ==")
    for name, rb, ra, lb, la in behaviour:
        print(f"  {name}")
        print(f"        修前 exit={rb} 末行={lb!r}")
        print(f"        修後 exit={ra} 末行={la!r}")
    if not behaviour:
        print("  (無)")
    return 1 if introduced else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
