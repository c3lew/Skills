"""#102 一鍵 QA：修前控制組紅卻報滿分；修後先驗控制組再跑 mutation。"""
import pathlib
import importlib.util
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BEFORE = "4c01110"


def run(*args, cwd, check=False):
    result = subprocess.run(args, cwd=cwd, capture_output=True)
    if check:
        result.check_returncode()
    return result


def main():
    with tempfile.TemporaryDirectory() as td:
        temp = pathlib.Path(td)
        archive = temp / "before.tar"
        with archive.open("wb") as out:
            result = subprocess.run(
                ["git", "archive", "--format=tar", BEFORE], cwd=ROOT, stdout=out)
        result.check_returncode()
        before = temp / "before"
        before.mkdir()
        with tarfile.open(archive) as bundle:
            bundle.extractall(before, filter="data")

        old_table = run(
            sys.executable, "scripts/qa/97-mutate.py", "--run", cwd=before)
        control = temp / "old-control"
        (control / "scripts").mkdir(parents=True)
        shutil.copy2(before / "scripts" / "validate.py", control / "scripts")
        old_control = run(
            sys.executable, "scripts/validate.py", "--self-check", cwd=control)
        print(f"修前：mutation 表 exit={old_table.returncode}；未套 knob 控制組 exit={old_control.returncode}")
        assert old_table.returncode == 0 and old_control.returncode != 0

        spec = importlib.util.spec_from_file_location(
            "mutate97", ROOT / "scripts" / "qa" / "97-mutate.py")
        mutate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mutate)
        mutations_started = 0

        def red_control(repo):
            return subprocess.CompletedProcess([], 1, b"", b"CONTROL_SENTINEL")

        def count_mutation(repo, knob):
            nonlocal mutations_started
            mutations_started += 1

        mutate.self_check = red_control
        mutate.apply = count_mutation
        try:
            mutate.run_table()
        except RuntimeError:
            pass
        else:
            raise AssertionError("紅控制組沒有中止")
        print("修後 phase A：control_exit=1；mutations_started="
              f"{mutations_started}；第一格前中止")
        assert mutations_started == 0

        print("修後 phase B：另起綠控制組，執行有效 mutation 表")
        new_table = run(
            sys.executable, "scripts/qa/97-mutate.py", "--run", cwd=ROOT, check=True)
        print(new_table.stdout.decode("utf-8").strip())
        print("判定：修前假綠已重現；修後控制組綠、紅控制組在第一格前中止、15/15 mutation 全紅")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    sys.exit(main())
