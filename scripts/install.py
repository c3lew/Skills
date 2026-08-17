#!/usr/bin/env python3
"""Idempotent install: copy skills/* to every agent's user-level skills dir.

Runs validate first; refuses to install on a red repo. Each skill directory
is mirrored (delete target, copy fresh), so running twice yields no diff and
stale files never linger.

Two destinations, because the line is called from two agents: Claude Code
reads ~/.claude/skills, Codex reads ~/.agents/skills (the cross-agent root
that `npx skills add -a codex` writes to). Installing to one only leaves the
other agent unable to call the line.

Usage:
    python scripts/install.py               # install to both agent roots
    python scripts/install.py --self-check  # run built-in assertions
"""
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import validate

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DESTS = (
    Path.home() / ".claude" / "skills",  # Claude Code
    Path.home() / ".agents" / "skills",  # Codex (cross-agent root)
)


def install(skills_dir, repo, dest):
    """Mirror each skill dir into dest. Returns installed skill names."""
    errors = validate(skills_dir, repo)
    if errors:
        for e in errors:
            print(f"FAIL {e}")
        raise SystemExit(1)
    if not skills_dir.is_dir():
        return []
    dest.mkdir(parents=True, exist_ok=True)
    installed = []
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        target = dest / skill_dir.name
        if target.is_symlink() or target.is_junction():
            # 收編的原件在 dest 是 symlink/junction(指向套件本體)— 拆連結即可,
            # 本體留在原處不動,反悔 = 重建連結。os.rmdir 兩種連結都能拆且不進目標。
            os.rmdir(target)
        elif target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_dir, target)
        installed.append(skill_dir.name)
    return installed


def snapshot(root):
    """Map of relative path -> file bytes, for idempotency comparison."""
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def main(dests=DEFAULT_DESTS):
    by_dest = {d: install(REPO / "skills", REPO, d) for d in dests}
    if not any(by_dest.values()):
        print("OK nothing to install (no skills/ yet)")
        return 0
    for dest, installed in by_dest.items():
        for name in installed:
            print(f"OK installed {name} -> {dest / name}")
    return 0


def self_check():
    import contextlib
    import io
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        skills = repo / "skills"
        dest = Path(tmp) / "dest"
        good = skills / "good"
        good.mkdir(parents=True)
        (good / "SKILL.md").write_text(
            "---\nname: good\ndescription: d\n---\nsee [x](extra.md)", encoding="utf-8"
        )
        (good / "extra.md").write_text("extra", encoding="utf-8")

        # install lands the skill at the destination
        assert install(skills, repo, dest) == ["good"]
        assert (dest / "good" / "SKILL.md").is_file()

        # the cross-machine check: what landed at dest still validates with a
        # repo root that holds nothing — every ref resolved from the copied
        # skill dir alone, which is what another machine actually gets.
        assert validate(dest, Path(tmp) / "no-such-repo") == [], validate(
            dest, Path(tmp) / "no-such-repo"
        )

        # idempotent: second run leaves an identical tree
        first = snapshot(dest)
        assert install(skills, repo, dest) == ["good"]
        assert snapshot(dest) == first

        # stale file in target is removed on reinstall (mirror semantics)
        (dest / "good" / "stale.md").write_text("old", encoding="utf-8")
        install(skills, repo, dest)
        assert not (dest / "good" / "stale.md").exists()
        assert snapshot(dest) == first

        # red validate blocks install
        (skills / "bad").mkdir()
        try:
            install(skills, repo, dest)
            raise AssertionError("install should refuse on red validate")
        except SystemExit as e:
            assert e.code == 1

        # empty repo installs nothing
        empty_repo = Path(tmp) / "empty"
        empty_repo.mkdir()
        assert install(empty_repo / "skills", empty_repo, dest) == []

    # the real-skill layer: the dev loop demoed on #38 — edit a skill, reinstall,
    # the edit is live at dest; revert + reinstall and it's gone again. The cases
    # above only ever install a fresh fixture, so an install that never refreshed
    # an already-present skill would have stayed green.
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        skills = repo / "skills"
        skills.mkdir(parents=True)
        real = sorted((REPO / "skills").glob("*/SKILL.md"))[0].parent
        shutil.copytree(real, skills / real.name)
        src = skills / real.name / "SKILL.md"
        original = src.read_text(encoding="utf-8")
        dest = Path(tmp) / "dest"
        landed = dest / real.name / "SKILL.md"

        install(skills, repo, dest)
        assert "QA38PROBE" not in landed.read_text(encoding="utf-8")

        src.write_text(original + "\n<!-- QA38PROBE -->\n", encoding="utf-8")
        install(skills, repo, dest)
        assert "QA38PROBE" in landed.read_text(encoding="utf-8"), real.name

        src.write_text(original, encoding="utf-8")
        install(skills, repo, dest)
        assert "QA38PROBE" not in landed.read_text(encoding="utf-8"), real.name

    # one run lands the same tree at every agent root — dropping a root is the
    # failure mode #40 found (Codex reads ~/.agents/skills, Claude Code
    # ~/.claude/skills; installing to one leaves the other agent on a stale copy)
    assert {tuple(d.parts[-2:]) for d in DEFAULT_DESTS} == {
        (".claude", "skills"),
        (".agents", "skills"),
    }, DEFAULT_DESTS
    assert all(d.parent.parent == Path.home() for d in DEFAULT_DESTS), DEFAULT_DESTS

    with tempfile.TemporaryDirectory() as tmp:
        dests = [Path(tmp) / "claude", Path(tmp) / "agents"]
        with contextlib.redirect_stdout(io.StringIO()):
            assert main(dests) == 0
        trees = [snapshot(d) for d in dests]
        assert trees[0] == trees[1], "agent roots drifted"
        assert set(trees[0]) == snapshot(REPO / "skills").keys()

    print("OK install self-check green")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        self_check()
        sys.exit(0)
    sys.exit(main())
