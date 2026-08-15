#!/usr/bin/env python3
"""Idempotent install: copy skills/* to the user-level skills directory.

Runs validate first; refuses to install on a red repo. Each skill directory
is mirrored (delete target, copy fresh), so running twice yields no diff and
stale files never linger.

Usage:
    python scripts/install.py               # install to ~/.claude/skills/
    python scripts/install.py --self-check  # run built-in assertions
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import validate

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DEST = Path.home() / ".claude" / "skills"


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
        if target.exists():
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


def main():
    installed = install(REPO / "skills", REPO, DEFAULT_DEST)
    if not installed:
        print("OK nothing to install (no skills/ yet)")
    else:
        for name in installed:
            print(f"OK installed {name} -> {DEFAULT_DEST / name}")
    return 0


def self_check():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        skills = repo / "skills"
        dest = Path(tmp) / "dest"
        good = skills / "good"
        good.mkdir(parents=True)
        (good / "SKILL.md").write_text(
            "---\nname: good\ndescription: d\n---\nbody", encoding="utf-8"
        )
        (good / "extra.md").write_text("extra", encoding="utf-8")

        # install lands the skill at the destination
        assert install(skills, repo, dest) == ["good"]
        assert (dest / "good" / "SKILL.md").is_file()

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

    print("OK install self-check green")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        self_check()
        sys.exit(0)
    sys.exit(main())
