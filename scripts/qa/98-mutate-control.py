"""#98 QA 的基準線控制組 —— 那張 mutation 台到底有沒有在量東西。

`97-mutate.py --run` 印「15/15 咬住」。可是 mutation 台跟任何量測儀器一樣,要先有
**控制組**:knob 一個都不套的時候,它必須是綠的。不然「改壞會轉紅」跟「怎樣都紅」
長得一模一樣,而後者代表整張表一格都沒在量。

這支做兩件事:

1. **控制組** —— 照 `97-mutate.py` 的 `run_table()` 一模一樣的方式做副本(只複製
   `scripts/validate.py`),knob 一個都不套,跑 `--self-check`。應該 exit 0。
2. **改成完整 repo 副本再跑一次整張表** —— 控制組如果紅了,這支給出「知道要量什麼
   之後,15 個 knob 到底有幾個真的被咬住」。

用法:
    python scripts/qa/98-mutate-control.py           # 控制組綠才 exit 0
"""
import importlib.util
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_mutate():
    spec = importlib.util.spec_from_file_location(
        "mutate97", str(ROOT / "scripts" / "qa" / "97-mutate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def self_check(repo):
    r = subprocess.run([sys.executable, str(repo / "scripts" / "validate.py"),
                        "--self-check"], cwd=str(ROOT), capture_output=True)
    tail = r.stderr.decode("utf-8", "replace").strip().splitlines()
    return r.returncode, (tail[-1][:100] if tail else "")


def bare_copy(dst):
    """`97-mutate.py` 現在做副本的方式 —— 只有 scripts/validate.py 一個檔。"""
    shutil.rmtree(dst, ignore_errors=True)
    (dst / "scripts").mkdir(parents=True)
    shutil.copy2(ROOT / "scripts" / "validate.py", dst / "scripts")


def full_copy(dst):
    """完整 repo 副本 —— `self_check` 前面的斷言要讀 skills/ 與 docs/。"""
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))


def main():
    m = load_mutate()
    knobs = sorted(m.KNOBS)
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)

        print("==== 控制組:97-mutate.py 現在的副本,knob 一個都不套 ====")
        bare = tmp / "bare"
        bare_copy(bare)
        code, why = self_check(bare)
        print(f"  exit={code}  {why}")
        healthy = code == 0
        print(f"  判定:{'控制組綠 —— 這張表在量東西' if healthy else '*** 控制組就已經紅 —— 整張表怎樣都印咬住,一格都沒在量 ***'}\n")

        print("==== 完整 repo 副本:同一張表重跑一次 ====")
        full = tmp / "full"
        full_copy(full)
        code, why = self_check(full)
        print(f"  控制組(不套 knob)exit={code}  {why}")
        base_ok = code == 0
        case = tmp / "case"
        missed = []
        for knob in knobs:
            shutil.rmtree(case, ignore_errors=True)
            shutil.copytree(full, case)
            m.apply(case, knob)
            code, why = self_check(case)
            if code == 0:
                missed.append(knob)
            print(f"  {'咬住' if code else '沒咬住'}  {knob:<22} exit={code}  {why}")
        print(f"\n  {len(knobs) - len(missed)}/{len(knobs)} 個 knob 被 self-check 咬住"
              + (f";沒咬住:{missed}" if missed else ""))

    ok = healthy and base_ok and not missed
    print(f"\n總結:控制組{'綠' if healthy else '紅(儀器壞了)'}、"
          f"完整副本 {len(knobs) - len(missed)}/{len(knobs)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    sys.exit(main())
