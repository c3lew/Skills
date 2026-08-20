"""#87 QA 的修前對照台 — 全部尺、逐格比對 `c51ba98` 修前 vs 修後。

改判準的票不能只看「這次要修的那一面」:`gens` 那半放寬會多擋(誤紅),`consumes`
那半放寬會多放(誤放),而多出來的那批在修之前是好的。這支把 repo 裡**每一支
sweep 的每一組 case**(23 組 fixture,含本輪新開的尺)各跑兩次 —— 一次現況,一次
`git show 55fc8eb:scripts/validate.py` 真的 import 舊版 —— 逐格列出 RED/GREEN 翻面
的那些,再標明翻對還是翻錯。

用法:
    python scripts/qa/87-prevdiff.py <repo>              # 只列翻面的格
    python scripts/qa/87-prevdiff.py <repo> --all        # 每一格都列
    python scripts/qa/87-prevdiff.py <repo> --prev=fa9d0c3  # 換一個對照點(/qa #91 加)
"""
import importlib.util
import sys
import tempfile
from pathlib import Path

PREV = "55fc8eb"          # #87 修之前
HERE = Path(__file__).resolve().parent


def load(stem):
    spec = importlib.util.spec_from_file_location(
        "sweep_" + stem.split("-")[0], str(HERE / (stem + ".py")))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SWEEPS = ["60-mention-sweep", "73-reach-sweep", "75-binding-sweep",
          "79-return-sweep", "81-lambda-sweep", "83-deferred-sweep",
          "84-generator-sweep", "86-async-sweep", "87-drive-sweep"]


def groups(mod):
    """每支 sweep 裡的每一組 fixture —— 名字不用手抄,免得漏一組。"""
    for name in sorted(vars(mod)):
        v = getattr(mod, name)
        if (name.isupper() and isinstance(v, list) and v
                and isinstance(v[0], tuple) and len(v[0]) == 3):
            yield name, v


def verdicts(guard, cases):
    tmp = Path(tempfile.mkdtemp())
    probe = tmp / "probe.py"
    out = []
    for name, src, want in cases:
        probe.write_text(src, encoding="utf-8")
        out.append((name, want,
                    "RED" if guard.stream_encoding_issues(tmp) else "GREEN"))
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    repo = sys.argv[1]
    show_all = "--all" in sys.argv
    prev = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--prev=")),
                PREV)
    sweep60 = load("60-mention-sweep")
    now = sweep60.guard_module(repo, None)
    old = sweep60.guard_module(repo, prev)
    print(f"對照點:{prev}")

    flips, total = [], 0
    for stem in SWEEPS:
        mod = load(stem)
        for group, cases in groups(mod):
            for (name, want, got), (_, _, was) in zip(verdicts(now, cases),
                                                      verdicts(old, cases)):
                total += 1
                if got == was and not show_all:
                    continue
                tag = ("沒動" if got == was else
                       ("修好" if got == want else "本輪引入"))
                flips.append((group, name, want, was, got, tag))
    width = max((len(f"{g} / {n}") for g, n, *_ in flips), default=10)
    for group, name, want, was, got, tag in flips:
        print(f"{(group + ' / ' + name).ljust(width)}  期望 {want:<5} "
              f"修前 {was:<5} 修後 {got:<5}  {tag}")
    bad = sum(t == "本輪引入" for *_, t in flips)
    print(f"\n母體 {total},翻面 {len([f for f in flips if f[3] != f[4]])},"
          f"本輪引入的誤判 {bad}")
    sys.exit(1 if bad else 0)
