"""#102 的 mutation 台控制組 regression。

真實表要全綠；再把控制組刻意改紅，確認 `run_table()` 立刻中止、不跑任何 knob。

用法:
    python scripts/qa/98-mutate-control.py           # 控制組綠才 exit 0
"""
import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_mutate():
    spec = importlib.util.spec_from_file_location(
        "mutate97", str(ROOT / "scripts" / "qa" / "97-mutate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    m = load_mutate()
    rows = m.run_table()
    assert rows and all(code for _, code in rows), rows
    print(f"控制組綠；完整副本 {len(rows)}/{len(rows)} 個 knob 被咬住")

    calls = 0

    def broken_control(repo):
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess([], 1, b"", "CONTROL_SENTINEL".encode())

    m.self_check = broken_control
    try:
        m.run_table()
    except RuntimeError as exc:
        assert "CONTROL_SENTINEL" in str(exc), exc
    else:
        raise AssertionError("控制組紅了仍繼續跑 mutation 表")
    assert calls == 1, f"控制組紅後仍執行了 {calls - 1} 個 knob"
    print("控制組刻意改紅：表在第一格前中止")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    sys.exit(main())
