#!/usr/bin/env python3
"""Repo entry point for the batch planner shipped inside skills/build-batch.

The planner's own assertions live in the skill dir because install copies only
that dir — a planner sitting in scripts/ would be missing on every machine that
installed the skill. This file is here so the repo's own check reads like the
others: `python scripts/batch.py --self-check`.

On top of delegating to the planner it runs the part that cannot ship inside
the skill: §8a/§8c of SKILL.md are *shell*, and until now nothing ever ran
them. `conflict_scenarios` builds a throwaway git repo, hits a real merge
conflict, and runs the snippet lifted verbatim out of SKILL.md. Every bug QA
found in #55 (rounds 3–6) lived in exactly those lines, and every one of them
was green against the substring guards in the skill's own self-check.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "build-batch" / "SKILL.md"

sys.path.insert(0, str(REPO / "skills" / "build-batch"))
from batch import self_check as planner_self_check  # noqa: E402

# §8a 那三行是佔位符,由 agent 當場填(`file=<撞到的檔案>` 照抄進 shell 還是語法
# 錯誤)。測試填的就是這三個輸入,其餘每一行逐字跑 — 抽的是文件本身,不是複本。
INPUTS_RE = re.compile(r"^(merged|current|file)=", re.M)


def attribution_snippet(text):
    """SKILL.md §8a 查「跟誰撞」的那段,原文抽出來。"""
    blocks = [b for b in re.findall("```bash(.*?)```", text, re.S)
              if "git merge-base" in b]
    if len(blocks) != 1:
        raise SystemExit("SKILL.md: expected exactly one §8a merge-base block, "
                         f"found {len(blocks)}")
    return "\n".join(l for l in blocks[0].splitlines()
                     if not INPUTS_RE.match(l))


def bash_exe():
    """§8a 要跑的是 git 那套 bash。

    Windows 上 PATH 的 `bash` 常常是 System32 的 WSL 轉接頭 — 它在另一個檔案
    系統裡,看不到這邊的 repo,跑起來是 `execvpe(/bin/bash) failed`。git 裝在
    哪就跟著它找,找不到才退回 PATH。
    """
    git = shutil.which("git")
    for parent in (Path(git).parents if git else ()):
        for rel in ("bin/bash.exe", "usr/bin/bash.exe", "bin/bash"):
            if (parent / rel).exists():
                return str(parent / rel)
    found = shutil.which("bash")
    if not found:
        raise SystemExit("bash not on PATH — §8a/§8c 是 bash,跑不了就不算驗過")
    return found


def _git(cwd, *args, check=True):
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed in {cwd}:\n{r.stderr}")
    return r


def _commit(cwd, message):
    _git(cwd, "add", "-A")
    _git(cwd, "-c", "user.email=qa@x", "-c", "user.name=qa", "commit", "-q",
         "-m", message)


def _merge(cwd, number, check=True):
    return _git(cwd, "-c", "user.email=qa@x", "-c", "user.name=qa", "merge",
                "--no-ff", "-m", f"Merge batch/{number}", f"batch/{number}",
                check=check)


def _lane(cwd, number, files, message):
    """從 base 開一條 lane branch,改幾個檔案,commit,回到主線。"""
    _git(cwd, "checkout", "-q", "-b", f"batch/{number}", "base")
    for name, body in files.items():
        path = Path(cwd, name)
        if body is None:
            path.unlink()
        else:
            path.write_text(body, encoding="utf-8")
    _commit(cwd, message)
    _git(cwd, "checkout", "-q", "main")


def _run_snippet(cwd, snippet, merged, current, file):
    """把 §8a 抽出來的那段真的跑一次,回傳它印出來的票號。"""
    script = Path(cwd).parent / "8a.sh"
    script.write_text("set -e\n"
                      f'merged="{merged}"\n'
                      f"current={current}\n"
                      f"file={file}\n" + snippet + "\n", encoding="utf-8")
    r = subprocess.run([bash_exe(), str(script)], cwd=str(cwd), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr
    return r.stdout.split()


def _conflicted_file(cwd):
    out = _git(cwd, "diff", "--name-only", "--diff-filter=U").stdout.split()
    assert len(out) == 1, out
    return out[0]


def conflict_scenarios():
    """§8a/§8c 在真的 git repo 上跑一次(#55 QA 第 3–6 輪抓到的四種形狀)。"""
    text = SKILL.read_text(encoding="utf-8")
    snippet = attribution_snippet(text)
    # 抽出來的還是 §8a 那段,而且三個輸入真的被換掉了
    assert "git merge-base" in snippet and "--name-status -M" in snippet
    assert not INPUTS_RE.search(snippet), snippet

    tmp = Path(tempfile.mkdtemp(prefix="batch-8a-"))
    repo = tmp / "repo"
    try:
        repo.mkdir()
        _git(repo, "init", "-q")
        _git(repo, "checkout", "-q", "-b", "main")
        # 十行不是隨便挑的:rename 要被 git 認出來,相似度才過得了 `-M` 的門檻。
        # 檔案太小的話同一個動作會被判成 modify/delete,撞的是舊名字,§8a 那行
        # pre-image 永遠走不到 — 那就不是這條 scenario 要驗的東西了。
        lines = [str(i) for i in range(1, 11)]

        def edit(index, what):
            return "\n".join(lines[:index] + [what] + lines[index + 1:]) + "\n"

        (repo / "shared.md").write_text("\n".join(lines) + "\n",
                                        encoding="utf-8")
        (repo / "hotfix.md").write_text("原本\n", encoding="utf-8")
        (repo / "other.md").write_text("別的\n", encoding="utf-8")
        _commit(repo, "base")
        _git(repo, "branch", "base")

        _lane(repo, 47, {"shared.md": edit(0, "47 改的")}, "lane 47")
        _lane(repo, 42, {"other.md": "42 改的\n"}, "lane 42")
        # 這條從來沒被合進主線,但它也動過 shared.md —— 候選母體要是
        # `git branch --list 'batch/*'` 就會把它撈出來,印一張跟這次 merge
        # 無關的票號給 client(QA 第 5 輪實測到的那個)
        _lane(repo, 99, {"shared.md": edit(4, "99 改的")}, "lane 99(沒合)")
        _lane(repo, 48, {"shared.md": edit(0, "48 改的")}, "lane 48")
        _lane(repo, 50, {"renamed.md": edit(0, "50 改的"), "shared.md": None},
              "lane 50(改名 + 改內容)")
        _lane(repo, 51, {"hotfix.md": "51 改的\n"}, "lane 51")

        merged = "47 42"
        for n in (47, 42):
            _merge(repo, n)
        # 未合的 lane 開著工作區 —— §8c 停下時它要原封不動留著
        _git(repo, "worktree", "add", "-q", ".git/batch-worktrees/99",
             "batch/99")
        head = _git(repo, "rev-parse", "HEAD").stdout.strip()

        # ① 兩張都改同一個檔案 -> 印出對面那張,而且只有那張
        assert _merge(repo, 48, check=False).returncode != 0
        got = _run_snippet(repo, snippet, merged, "batch/48",
                           _conflicted_file(repo))
        assert got == ["#47"], got          # 不是 #42(乾淨)、不是 #99(沒合)

        # ② §8c:停下之前 merge --abort,主線回到「上一張合完」的樣子
        _git(repo, "merge", "--abort")
        assert _git(repo, "rev-parse", "HEAD").stdout.strip() == head
        assert _git(repo, "status", "--porcelain").stdout.strip() == ""
        # 未合的 lane 的工作區與 branch 都還在 —— client 決定完接得回去
        assert (repo / ".git" / "batch-worktrees" / "99").is_dir()
        assert "batch/99" in _git(repo, "branch", "--list", "batch/*").stdout

        # ③ 正在合的那張把檔案改名了 -> 靠 pre-image 還是查得到對面(QA 第 5 輪)
        assert _merge(repo, 50, check=False).returncode != 0
        renamed = _conflicted_file(repo)
        got = _run_snippet(repo, snippet, merged, "batch/50", renamed)
        assert got == ["#47"], (renamed, got)
        # 少了 rename pre-image 那行就查不到 —— 證明它是承重的,不是裝飾
        without = "\n".join(l for l in snippet.splitlines()
                            if "--name-status -M" not in l)
        assert _run_snippet(repo, without, merged, "batch/50", renamed) == []
        _git(repo, "merge", "--abort")

        # ④ 已合的那幾張沒人動過 -> 印 0 張,不猜票號
        (repo / "hotfix.md").write_text("主線自己改的\n", encoding="utf-8")
        _commit(repo, "主線 hotfix")
        assert _merge(repo, 51, check=False).returncode != 0
        assert _run_snippet(repo, snippet, merged, "batch/51",
                            _conflicted_file(repo)) == []
        _git(repo, "merge", "--abort")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def self_check():
    planner_self_check()
    conflict_scenarios()
    print("OK §8a/§8c conflict scenarios green")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # #58, AGENTS.md
    sys.stderr.reconfigure(encoding="utf-8")
    if "--self-check" in sys.argv:
        self_check()
        sys.exit(0)
    print(__doc__)
