# -*- coding: utf-8 -*-
"""#130 的第二把尺 —— 自己窮舉母體、自己寫判準,**不套 `129-wide.py` 的 N1..N8**。

為什麼要再寫一支:#130 的受測物(`batch.py` 入口的型別收斂)跟量它的那把尺
(`129-wide.py` 的 N8)是同一輪、同一個腦袋寫出來的。只跑那支綠,證明的是
「作者同意自己」。這支從**別的角度**重新問一次同一件事,而且刻意寫寬:

judge 的角度不是「票號合不合法」,是 **client 手上那一段文字貼進終端機會發生
什麼**。所以判準全部只看 stdout 的字面,用最笨最直接的方式掃:

- W1  反引號包起來、看起來像指令的那幾段(`` `/xxx ...` `` / `` `$xxx ...` ``):
      段內每一個 `#`,從 `#` 之後抓到**下一個空白為止**的那一串,必須是非空的
      純 ASCII 數字。`# 108` 抓到的是空字串 -> 違例(bash / PowerShell 都把
      `#` 之後當註解,貼上去等於沒跑);`#108.0` 抓到 `108.0` -> 違例(指到一張
      不存在的票)。
- W2  **全 stdout** 的每一個 `#`(不只反引號裡),同樣抓到下一個空白為止,不是
      純數字就撈出來。這條**故意寬到會誤報** —— markdown 的 `##` 標題、
      `#48(branch batch/48)` 這種後面黏標點的都會中。撈出來的每一筆在報告最後
      逐筆判讀,不自動當 bug。
- W3  exit 非 0 的那半:stdout 要是空的、stderr 不准有 `Traceback`、而且要講得出
      是哪一格(字面 `spec`)以及他填了什麼。
- W4  exit 0 的那半:這支自己把 spec 那格算成一個整數(自己算,不 import 受測物),
      算得出來的話 stdout 上就要看得到 `#<那個整數>`。
- W5  exit 0 -> stderr 空;exit 非 0 -> stdout 空。兩邊不准同時有話。

**寬在哪 / 天花板**:W1 的「像指令」只認 `` ` `` 開頭接 `/` 或 `$`;W2 撈出來的
是候選不是判決。母體只窮舉四個印 `spec` 的 mode(interrupted / merged 全綠 /
merged 有人還在修 / summary),`spec` 這個 key **整個缺席**的形狀不在裡面
(受測物那邊是裸 KeyError,#130 票上宣告過不在 AC 裡)。

用法:
    python 130-wide.py              # 跑工作區的 batch.py
    python 130-wide.py <path>       # 跑指定的 batch.py(130-prevdiff.py 用)
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BATCH = ROOT / "skills" / "build-batch" / "batch.py"

# 反引號裡看起來像指令的那一段:`` ` `` 之後緊接 `/` 或 `$`
CMD_SEG_RE = re.compile(r"`([/$][^`]*)`")
# `#` 之後抓到下一個空白為止 —— 最笨的抓法,標點也一起抓進來(寧可撈太多)
HASH_TOK_RE = re.compile(r"#(\S*)")

# 其他放票號的格子:刻意混用型別,證明 `spec` 那格不是靠別格順便被收掉的
OTHER_SHAPES = [
    ("純 int", {"numbers": [47, 48], "titles": {"47": "登入頁", "48": "結帳"}}),
    ("字串混 int", {"numbers": ["47", 48], "titles": {47: "登入頁", "48": "結帳"}}),
    ("帶空白", {"numbers": [" 47 ", "48"], "titles": {" 47 ": "登入頁", 48: "結帳"}}),
]

# `spec` 那格的各種寫法。前半是「應該轉得動」的,後半是「應該當場停」的 ——
# 但這支不預先宣告哪個是哪個,行為由 W3 / W4 各自量。
SPEC_RAWS = [
    108,                 # 裸整數
    "108",               # 字串
    " 108 ",             # 前後空白 —— #130 出廠時印成 `# 108`
    "\u00a0108",         # NBSP 開頭(從網頁複製貼上很常見)
    "\uff11\uff10\uff18",  # 全形數字 １０８
    "0108",              # 前導零
    108.0,               # 浮點
    "108.0",             # 字串浮點
    None,                # JSON null
    True,                # JSON true
    [],                  # JSON 空陣列
    "\u4e00\u3007\u516b",  # 「一〇八」
    "",                  # 空字串
    "#108",              # 已經自己帶了 `#`
    "https://example.invalid/issues/108",  # 連結(#129 之前的舊寫法)
]


def cases():
    """窮舉母體:4 個印 spec 的 mode x 3 種其他格子的型別 x 15 種 spec 寫法。"""
    for shape_name, shape in OTHER_SHAPES:
        numbers = shape["numbers"]
        titles = shape["titles"]
        for raw in SPEC_RAWS:
            base = {"numbers": list(numbers), "titles": dict(titles), "spec": raw}
            yield (f"interrupted / {shape_name} / spec={raw!r}",
                   dict(base, mode="interrupted"))
            yield (f"merged 全綠 / {shape_name} / spec={raw!r}",
                   dict(base, mode="merged"))
            yield (f"merged 有人還在修 / {shape_name} / spec={raw!r}",
                   dict(base, mode="merged", fixing=[list(numbers)[-1]]))
            yield (f"summary / {shape_name} / spec={raw!r}",
                   dict(base, mode="summary", fixing=[],
                        coverage={"47": ["1. 登入頁"], "48": ["2. 結帳"]}))


def my_spec_int(raw):
    """這支**自己**把 spec 算成整數的辦法 —— 不 import 受測物那支。

    比受測物寬一點:整數值的浮點(`108.0` / `"108.0"`)在 client 眼裡也還是
    #108。算不出來回 None。
    """
    if isinstance(raw, bool) or raw is None:
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        pass
    try:
        f = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return int(f) if f == int(f) else None


def run(batch, payload):
    p = subprocess.run(
        [sys.executable, str(batch)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True)
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def check(batch, name, payload):
    """回 (violations, wide_hits)。violations 是硬判準,wide_hits 是 W2 的候選。"""
    rc, out, err = run(batch, payload)
    bad, wide = [], []

    # W5
    if rc == 0 and err.strip():
        bad.append(("W5", f"exit 0 但 stderr 有話:{err.strip()[:200]!r}"))
    if rc != 0 and out.strip():
        bad.append(("W5", f"exit {rc} 但 stdout 還是印了東西:{out.strip()[:200]!r}"))

    if rc != 0:
        # W3
        if "Traceback" in err:
            bad.append(("W3", f"停下來的時候噴裸 traceback:{err.strip()[:300]!r}"))
        if "spec" not in err:
            bad.append(("W3", f"訊息裡沒有指名 `spec` 那格:{err.strip()[:300]!r}"))
        shown = repr(payload["spec"])
        if shown not in err and str(payload["spec"]) not in err:
            bad.append(("W3", f"訊息裡看不到他填的 {shown}:{err.strip()[:300]!r}"))
        return bad, wide

    # ---- 以下是 exit 0 的那半 ----
    # W1:反引號裡看起來像指令的那幾段
    for seg in CMD_SEG_RE.findall(out):
        for tok in HASH_TOK_RE.findall(seg):
            if not (tok and tok.isascii() and tok.isdigit()):
                bad.append(("W1", f"照抄貼的指令 `{seg}` 裡 `#` 後面是 {tok!r} —— "
                                  "不是純數字,貼進終端機不會跑到那張票"))

    # W2:全 stdout 的每個 `#`(寬,會誤報,逐筆判讀)
    for tok in HASH_TOK_RE.findall(out):
        if not (tok and tok.isascii() and tok.isdigit()):
            wide.append(("W2", f"stdout 上 `#{tok}` —— `#` 後面不是純數字"))

    # W4
    n = my_spec_int(payload["spec"])
    if n is not None and f"#{n}" not in out:
        bad.append(("W4", f"spec 算出來是 #{n},但 stdout 上找不到 `#{n}`"))
    return bad, wide


def resolve_batch(arg):
    """參數 -> 要跑的那支 batch.py。

    這 repo 的每一支 `*-wide.py` 都吃 repo root(`… 130-wide.py .`),而這支還要能
    被 `130-prevdiff.py` 指到修前那版的單檔,所以兩種都收:目錄就照 repo 的版面
    往下找,`.py` 就直接用。收不了的當場停 —— 之前這裡是 `python <參數>` 直接吞,
    給 `.` 會跑出 348 筆「訊息裡沒有指名 `spec`」的假違例,而真正的訊息是
    `can't find '__main__' module`,讀報告的人看不出是自己參數給錯。
    """
    p = pathlib.Path(arg)
    if p.is_dir():
        p = p / "skills" / "build-batch" / "batch.py"
    if p.suffix != ".py" or not p.is_file():
        raise SystemExit(
            f"停在這裡 —— 跑不了 {arg!r}:要嘛給 repo root(像 `.`),"
            f"要嘛給一支 batch.py 的路徑。找到的是 {p}")
    return p


def main():
    batch = resolve_batch(sys.argv[1]) if len(sys.argv) > 1 else BATCH
    total = 0
    all_bad, all_wide = [], []
    for name, payload in cases():
        total += 1
        bad, wide = check(batch, name, payload)
        for rule, msg in bad:
            all_bad.append((name, rule, msg))
        for rule, msg in wide:
            all_wide.append((name, rule, msg))

    print(f"受測物:{batch}")
    print(f"母體 {total} 批")
    print("")
    print(f"== 硬判準(W1 / W3 / W4 / W5)違例 {len(all_bad)} 筆 ==")
    for name, rule, msg in all_bad:
        print(f"  [{rule}] {name}")
        print(f"        {msg}")
    if not all_bad:
        print("  (無)")

    # W2 撈出來的是候選,按訊息去重之後逐筆列出來等人判讀
    seen = {}
    for name, rule, msg in all_wide:
        seen.setdefault(msg, []).append(name)
    print("")
    print(f"== 寬掃 W2 撈到的候選 {len(seen)} 種(共 {len(all_wide)} 次),逐筆判讀 ==")
    for msg, names in sorted(seen.items()):
        print(f"  {msg}  x{len(names)}")
        print(f"        例:{names[0]}")
    if not seen:
        print("  (無)")
    return 1 if all_bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
