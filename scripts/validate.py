#!/usr/bin/env python3
"""Structural lint for skills in this repo.

Checks every skill under skills/: SKILL.md exists, frontmatter has
name + description, and path references resolve *inside the skill dir* —
install copies only the skill dir, so a ref that needs the repo root is a
link that breaks on every other machine. Skills in REPO_SCOPED_SKILLS are
exempt — operating this repo is their job, so repo-root refs are correct.
Bundled discipline copies (skills/*/references/<name> sharing a filename with
docs/disciplines/<name>) must byte-match the docs original — the docs file is
the source of truth; skills carry verbatim copies so they survive install.
Does NOT validate prose content.

Usage:
    python scripts/validate.py               # lint the repo, exit 1 on errors
    python scripts/validate.py --self-check  # run built-in assertions
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# skills whose job IS operating this repo — repo-root refs are the behaviour,
# not a broken link. Everything else must stay inside its own skill dir.
REPO_SCOPED_SKILLS = {"retro"}

FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---", re.S)
# markdown link targets, plus backticked relative paths (anything slash-joined
# with a file extension, e.g. `docs/x.md`, `references/foo.html`, `./local.md`)
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
BACKTICK_PATH_RE = re.compile(
    r"`(\.{1,2}/[^`\s]+|[\w.-]+(?:/[\w.-]+)+\.[A-Za-z0-9]{1,5})`"
)
# Only file refs are links an agent can follow. Bare directory refs
# (`docs/disciplines/`, `.out-of-scope/`) are prose about paths a skill
# operates on in the *target* repo — not links, so not checked.


def parse_frontmatter(text):
    """Return frontmatter as a dict, or None if there is no frontmatter block."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def find_path_refs(text):
    """Extract candidate file-path references from markdown text."""
    refs = []
    for target in LINK_RE.findall(text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        refs.append(target.split("#")[0])
    refs.extend(BACKTICK_PATH_RE.findall(text))
    return [r for r in refs if r]


def resolves_in(skill_dir, ref):
    """True if ref points at something that exists *within* skill_dir."""
    target = (skill_dir / ref).resolve()
    if not target.exists():
        return False
    return target == skill_dir.resolve() or skill_dir.resolve() in target.parents


def validate(skills_dir, repo):
    """Return a list of error strings; empty list means green."""
    errors = []
    if not skills_dir.is_dir():
        return errors  # no skills yet — nothing to fail
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        label = f"skills/{skill_dir.name}"
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{label}: missing SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            errors.append(f"{label}/SKILL.md: missing frontmatter block (--- ... ---)")
        else:
            for field in ("name", "description"):
                if not fm.get(field):
                    errors.append(f"{label}/SKILL.md: frontmatter missing '{field}'")
        repo_scoped = skill_dir.name in REPO_SCOPED_SKILLS
        for ref in find_path_refs(text):
            if resolves_in(skill_dir, ref):
                continue
            # exists, just not inside the skill dir — install won't copy it
            if (repo / ref).exists() or (skill_dir / ref).exists():
                if repo_scoped:
                    continue
                errors.append(
                    f"{label}/SKILL.md: reference '{ref}' escapes the skill dir "
                    f"(only resolves from outside — breaks once installed)"
                )
            else:
                errors.append(f"{label}/SKILL.md: broken reference '{ref}'")
        refs_dir = skill_dir / "references"
        if refs_dir.is_dir():
            for copy in sorted(refs_dir.iterdir()):
                original = repo / "docs" / "disciplines" / copy.name
                if (
                    copy.is_file()
                    and original.is_file()
                    and copy.read_bytes() != original.read_bytes()
                ):
                    errors.append(
                        f"{label}/references/{copy.name}: out of sync with "
                        f"docs/disciplines/{copy.name} (docs is source of truth)"
                    )
    return errors


def main():
    errors = validate(REPO / "skills", REPO)
    for e in errors:
        print(f"FAIL {e}")
    if errors:
        return 1
    print("OK validate green")
    return 0


def self_check():
    import tempfile

    # frontmatter parsing
    assert parse_frontmatter("no frontmatter") is None
    assert parse_frontmatter("---\nname: x\ndescription: y\n---\nbody") == {
        "name": "x",
        "description": "y",
    }

    # ref extraction: keeps repo paths, drops urls and anchors
    refs = find_path_refs(
        "[a](docs/specs/qa.md) [b](https://x.com) [c](#anchor) "
        "`docs/blueprint.md` `./local.md` `references/foo.html` `not a path` `a/b`"
    )
    assert refs == [
        "docs/specs/qa.md",
        "docs/blueprint.md",
        "./local.md",
        "references/foo.html",
    ], refs

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        skills = repo / "skills"
        (repo / "docs").mkdir()
        (repo / "docs" / "real.md").write_text("hi", encoding="utf-8")

        # no skills dir at all -> green
        assert validate(skills, repo) == []

        # good skill -> green (refs stay inside the skill dir)
        good = skills / "good"
        good.mkdir(parents=True)
        (good / "SKILL.md").write_text(
            "---\nname: good\ndescription: a fine skill\n---\nsee [d](notes.md)",
            encoding="utf-8",
        )
        (good / "notes.md").write_text("x", encoding="utf-8")
        assert validate(skills, repo) == []

        # a ref that only resolves from the repo root is red — it breaks on
        # every machine where only the skill dir got installed
        (good / "SKILL.md").write_text(
            "---\nname: good\ndescription: a fine skill\n---\nsee [d](docs/real.md)",
            encoding="utf-8",
        )
        errs = validate(skills, repo)
        assert errs == [
            "skills/good/SKILL.md: reference 'docs/real.md' escapes the skill dir "
            "(only resolves from outside — breaks once installed)"
        ], errs

        # bare directory refs are prose, not links — never checked
        (good / "SKILL.md").write_text(
            "---\nname: good\ndescription: d\n---\n`docs/` `.out-of-scope/`",
            encoding="utf-8",
        )
        assert validate(skills, repo) == [], validate(skills, repo)

        # climbing out with ../ into a sibling skill: it exists,
        # but install won't copy it, so it reports as an escape not a break
        (skills / "sibling").mkdir()
        (skills / "sibling" / "SKILL.md").write_text(
            "---\nname: sibling\ndescription: d\n---\nbody", encoding="utf-8"
        )
        (good / "SKILL.md").write_text(
            "---\nname: good\ndescription: d\n---\n`../sibling/SKILL.md`",
            encoding="utf-8",
        )
        errs = validate(skills, repo)
        assert errs == [
            "skills/good/SKILL.md: reference '../sibling/SKILL.md' escapes the "
            "skill dir (only resolves from outside — breaks once installed)"
        ], errs
        (skills / "sibling" / "SKILL.md").unlink()
        (skills / "sibling").rmdir()
        (good / "SKILL.md").unlink()
        (good / "notes.md").unlink()
        good.rmdir()

        # retro is allowlisted: the exact refs that redden any other skill
        # stay green for it, because operating this repo is its job
        retro_body = "---\nname: retro\ndescription: d\n---\n[d](docs/real.md)"
        for name, expected in (("retro", []), ("notretro", [
            "skills/notretro/SKILL.md: reference 'docs/real.md' escapes the skill "
            "dir (only resolves from outside — breaks once installed)",
        ])):
            d = skills / name
            d.mkdir()
            (d / "SKILL.md").write_text(retro_body, encoding="utf-8")
            assert validate(skills, repo) == expected, (name, validate(skills, repo))
            (d / "SKILL.md").unlink()
            d.rmdir()
        assert "retro" in REPO_SCOPED_SKILLS

        # missing SKILL.md
        (skills / "empty").mkdir()
        errs = validate(skills, repo)
        assert errs == ["skills/empty: missing SKILL.md"], errs
        (skills / "empty").rmdir()

        # frontmatter missing description
        bad_fm = skills / "badfm"
        bad_fm.mkdir()
        (bad_fm / "SKILL.md").write_text("---\nname: badfm\n---\nbody", encoding="utf-8")
        errs = validate(skills, repo)
        assert errs == ["skills/badfm/SKILL.md: frontmatter missing 'description'"], errs

        # no frontmatter at all
        (bad_fm / "SKILL.md").write_text("just prose", encoding="utf-8")
        errs = validate(skills, repo)
        assert errs == ["skills/badfm/SKILL.md: missing frontmatter block (--- ... ---)"], errs
        (bad_fm / "SKILL.md").unlink()
        bad_fm.rmdir()

        # broken reference
        broken = skills / "broken"
        broken.mkdir()
        (broken / "SKILL.md").write_text(
            "---\nname: broken\ndescription: d\n---\n[x](docs/nope.md)", encoding="utf-8"
        )
        errs = validate(skills, repo)
        assert errs == ["skills/broken/SKILL.md: broken reference 'docs/nope.md'"], errs

        # reference relative to the skill dir also resolves
        (broken / "SKILL.md").write_text(
            "---\nname: broken\ndescription: d\n---\n`./extra.md`", encoding="utf-8"
        )
        (broken / "extra.md").write_text("x", encoding="utf-8")
        assert validate(skills, repo) == []

        # bundled discipline copy must byte-match docs/disciplines original
        (repo / "docs" / "disciplines").mkdir()
        (repo / "docs" / "disciplines" / "disc.md").write_text("v1", encoding="utf-8")
        bundle_dir = broken / "references"
        bundle_dir.mkdir()
        (bundle_dir / "disc.md").write_text("v1", encoding="utf-8")
        (bundle_dir / "unrelated.md").write_text("no docs counterpart", encoding="utf-8")
        (bundle_dir / "disc.md.d").mkdir()  # subdir must not crash the check
        assert validate(skills, repo) == []
        (bundle_dir / "disc.md").write_text("v2 drifted", encoding="utf-8")
        errs = validate(skills, repo)
        assert errs == [
            "skills/broken/references/disc.md: out of sync with "
            "docs/disciplines/disc.md (docs is source of truth)"
        ], errs

    print("OK validate self-check green")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        self_check()
        sys.exit(0)
    sys.exit(main())
