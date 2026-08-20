"""#87 QA 的獨立 oracle — 不套守門的規則,直接**把 fixture 跑起來**看 bypass 有沒有真的執行。

受測物(`validate.py`)自己就是判準,所有 sweep 都 import 它的
`stream_encoding_issues` —— 它綠只證明它同意自己,連 fixture 的「期望」欄都是人手標
的。這支當第二把尺,刻意不讀 `validate.py` 一行:每個 fixture 真的 `python probe.py`
跑一遍,把 `sys.stdout.buffer.write` 換成會記帳的 proxy,看那一行到底有沒有跑到。

#60 AC1 逐字:「真的在**會執行的位置**用 `sys.stdout.buffer.write`」。所以
ground truth 很直白 —— 真的跑到 = 期望 GREEN,沒跑到 = 期望 RED。這支列出
**fixture 的期望** vs **真的跑起來的結果**,對不上的逐筆判讀。

只掃 tail 是「裸中文 print、沒 pin」的那幾組(async / generator / deferred 家族)——
其他組(pin 位置、提到 vs 用到)期望值不是由 bypass 有沒有跑決定的,不適用這把尺。

用法:
    python scripts/qa/87-oracle.py <repo>
    python scripts/qa/87-oracle.py <repo> --all   # 連跑起來就爆的也列細節
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GROUPS = {
    "83-deferred-sweep": ["DEFERRED"],
    "84-generator-sweep": ["GENERATOR"],
    "86-async-sweep": ["ASYNC_DEFER", "SHADOW_SCOPE", "ATTR_CONSUMER"],
    "87-drive-sweep": ["DRIVEN_SHADOW", "DRIVEN_ATTR", "AWAIT_SHAPES"],
}

# 記帳用的殼:把 bypass 換成 proxy,再照 __main__ 跑 probe。守門的規則一行都沒讀。
SHELL = """import runpy
import sys

hit = []
real = sys.stdout.buffer.write


class Spy:
    def __getattr__(self, k):
        return getattr(real.__self__, k)

    def write(self, b):
        hit.append(1)
        return real(b)


class Out:
    def __getattr__(self, k):
        return getattr(sys.__stdout__, k)

    buffer = Spy()


sys.stdout = Out()
try:
    runpy.run_path(sys.argv[1], run_name="__main__")
except BaseException as e:              # 跑爆了也照樣回報「爆之前跑到沒有」
    print("BOOM", type(e).__name__, file=sys.stderr)
print("VERDICT", "HIT" if hit else "MISS", file=sys.stderr)
"""


def load(stem):
    spec = importlib.util.spec_from_file_location(
        "sweep_" + stem.split("-")[0], str(HERE / (stem + ".py")))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    tmp = Path(tempfile.mkdtemp())
    shell = tmp / "shell.py"
    shell.write_text(SHELL, encoding="utf-8")
    probe = tmp / "probe.py"
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONWARNINGS="ignore")

    rows, bad = [], 0
    for stem, names in GROUPS.items():
        mod = load(stem)
        for group in names:
            for name, src, want in getattr(mod, group):
                probe.write_text(src, encoding="utf-8")
                r = subprocess.run([sys.executable, str(shell), str(probe)],
                                   capture_output=True, text=True, env=env,
                                   encoding="utf-8", errors="replace")
                err = r.stderr or ""
                ran = "VERDICT HIT" in err
                boom = "BOOM" in err
                truth = "GREEN" if ran else "RED"
                ok = truth == want
                bad += not ok
                rows.append((f"{group} / {name}", want, truth,
                             ("ok" if ok else "MISMATCH")
                             + (" (跑爆)" if boom else "")))
    width = max(len(r[0]) for r in rows)
    for name, want, truth, verdict in rows:
        print(f"{name.ljust(width)}  fixture 期望 {want:<5} "
              f"真跑 {truth:<5}  {verdict}")
    print(f"\n母體 {len(rows)},fixture 期望與實跑不合 {bad}")
    sys.exit(1 if bad else 0)
