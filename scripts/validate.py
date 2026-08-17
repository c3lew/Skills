#!/usr/bin/env python3
"""Structural lint for skills in this repo.

Checks every skill under skills/: SKILL.md exists, frontmatter has
name + description, and path references in *every* `*.md` the skill ships
(SKILL.md, references/, anything else) resolve *inside the skill dir* —
install copies only the skill dir, so a ref that needs the repo root is a
link that breaks on every other machine. Skills in REPO_SCOPED_SKILLS are
exempt — operating this repo is their job, so repo-root refs are correct.
Bundled discipline copies (skills/*/references/<name> sharing a filename with
docs/disciplines/<name>) must byte-match the docs original — the docs file is
the source of truth; skills carry verbatim copies so they survive install.
Handoff lines (「下一步:`/x #N`」) must dual-write the Codex form on the same
line (`$x #N`) — Codex calls skills with `$name`, so a slash-only handoff is a
comment the client cannot paste there. Repo-wide (main() only, not validate()):
every baton must name a skill that exists under skills/, because that pasted
command has to resolve to an installed skill dir on the other agent.
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
# handoff baton: the 「下一步:…」 span a skill writes for the client. Any slash
# command inside that span must carry its Codex `$name` twin, so the line pastes
# into either agent. Span ends at 」 (or end of line) — a `/skill` mentioned in
# the surrounding prose is internal wording, not the baton, and stays untouched.
HANDOFF_SPAN_RE = re.compile(r"下一步[:︰:][^」\n]*")
SLASH_CMD_RE = re.compile(r"`/([A-Za-z0-9_-]+)")
# 「下一步:`/skill #N`」 is the template a skill quotes when describing the
# convention, not a command anyone pastes — there is no skills/skill.
PLACEHOLDER_SKILLS = {"skill"}
# #49 固化:a skill that tells the agent to paste commit links into a ticket must
# tell it to push *first* — an unpushed sha is a 404 on GitHub, and the comment
# is already out there when the client clicks it. Order matters, so the guard is
# positional: the push instruction has to appear before the commit-link one.
# The push side matches the literal command, not the word — a prose "push 後產出
# 寫回票" (build's frontmatter) is a summary, not a step an agent can run, and
# matching it would keep the guard green after the actual step is deleted.
COMMIT_LINK_RE = re.compile(r"commit link", re.I)
PUSH_RE = re.compile(r"git push", re.I)
# Only file refs are links an agent can follow. Bare directory refs
# (`docs/disciplines/`, `.out-of-scope/`) are prose about paths a skill
# operates on in the *target* repo — not links, so not checked. Same for
# anything *under* a dot-directory (`.out-of-scope/dark-mode.md`,
# `.claude/settings.json`): a skill never ships a dotdir, so such a path is
# always describing the target repo, never a link into the skill's own files.


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


def in_target_repo_dotdir(ref):
    """True if ref lives under a dot-directory — target-repo prose, not a link."""
    head = ref.split("/")[0]
    return head.startswith(".") and head not in (".", "..")


def find_path_refs(text):
    """Extract candidate file-path references from markdown text."""
    refs = []
    for target in LINK_RE.findall(text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        refs.append(target.split("#")[0])
    refs.extend(BACKTICK_PATH_RE.findall(text))
    return [r for r in refs if r and not in_target_repo_dotdir(r)]


def find_slash_only_handoffs(text):
    """Return skill names whose handoff baton lacks the Codex `$name` twin."""
    missing = []
    for span in HANDOFF_SPAN_RE.findall(text):
        for name in SLASH_CMD_RE.findall(span):
            if f"`${name}" not in span:
                missing.append(name)
    return missing


def unpushed_commit_link_issue(text):
    """True if the text asks for commit links without asking to push first."""
    link = COMMIT_LINK_RE.search(text)
    if not link:
        return False
    push = PUSH_RE.search(text)
    return push is None or push.start() > link.start()


def handoff_target_issues(skills_dir):
    """Every baton must name a skill that exists — repo-wide check.

    #41 proved the baton is a *command the client pastes into the other agent*:
    「下一步:`/qa #43`(Codex: `$qa #43`)」 pasted into a fresh Codex session
    resolved to ~/.agents/skills/qa/. A typo or a renamed skill dir turns that
    line into a dead command on the ticket, and validate() cannot see it — it
    lints one skill dir at a time and the target lives in a sibling.
    """
    if not skills_dir.is_dir():
        return []
    present = {p.name for p in skills_dir.iterdir() if p.is_dir()}
    errors = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        for span in HANDOFF_SPAN_RE.findall(text):
            for name in SLASH_CMD_RE.findall(span):
                if name in PLACEHOLDER_SKILLS or name in present:
                    continue
                errors.append(
                    f"skills/{skill_md.parent.name}/SKILL.md: handoff 「下一步:… "
                    f"`/{name}`」 points at skills/{name}, which does not exist "
                    f"— the client pastes that line into an agent"
                )
    return errors


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
        if unpushed_commit_link_issue(text):
            errors.append(
                f"{label}/SKILL.md: asks for commit links in a ticket comment "
                f"without asking to `git push` first — an unpushed sha is a 404"
            )
        for name in find_slash_only_handoffs(text):
            errors.append(
                f"{label}/SKILL.md: handoff 「下一步:… `/{name}`」 missing the "
                f"Codex form `${name}` inside the same 「下一步:…」 baton"
            )
        repo_scoped = skill_dir.name in REPO_SCOPED_SKILLS
        # every *.md ships with the skill, so every one of them can carry a
        # link that dies on install — references/ included, not just SKILL.md
        for md in sorted(skill_dir.rglob("*.md")):
            rel = md.relative_to(skill_dir).as_posix()
            for ref in find_path_refs(md.read_text(encoding="utf-8")):
                if resolves_in(skill_dir, ref):
                    continue
                # exists, just not inside the skill dir — install won't copy it
                if (repo / ref).exists() or (skill_dir / ref).exists():
                    if repo_scoped:
                        continue
                    errors.append(
                        f"{label}/{rel}: reference '{ref}' escapes the skill dir "
                        f"(only resolves from outside — breaks once installed)"
                    )
                else:
                    errors.append(f"{label}/{rel}: broken reference '{ref}'")
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
    errors = validate(REPO / "skills", REPO) + handoff_target_issues(REPO / "skills")
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

    # handoff dual-write: slash-only is red, dual-written is green
    assert find_slash_only_handoffs("下一步:`/qa #12`") == ["qa"]
    assert find_slash_only_handoffs("下一步:`/qa #12`(Codex: `$qa #12`)") == []
    # the twin must be inside the baton — a stray `$qa` on the next line doesn't count
    assert find_slash_only_handoffs("下一步:`/qa #12`\n`$qa #12`") == ["qa"]
    # the command doesn't have to sit right after 下一步: — words may precede it
    assert find_slash_only_handoffs("「下一步:從無 blocker 的票開始 `/build #N`」") == ["build"]
    # prose after the closing 」 is internal wording, not the baton
    assert find_slash_only_handoffs(
        "「下一步:`/build #N`(Codex: `$build #N`)」,附 scenario(`/qa` 要跑 regression)"
    ) == []
    assert find_slash_only_handoffs("跑 `/qa #12` 驗收") == []

    # the real-skill layer: the cases above feed hand-written strings, so they
    # stay green even if every baton in the repo vanished. This one takes each
    # actual skill's baton, drops the Codex half, and asserts validate reddens
    # naming the file and the missing command — the mutation demoed on #37.
    batons = []
    for src in sorted((REPO / "skills").glob("*/SKILL.md")):
        text = src.read_text(encoding="utf-8")
        for span in HANDOFF_SPAN_RE.findall(text):
            m = SLASH_CMD_RE.search(span)
            if m:
                batons.append((src, text, span, m.group(1)))
                break
    assert batons, "no skill carries a 「下一步:… `/x`」 baton — mutation has nothing to bite"

    for src, text, span, name in batons:
        label = f"skills/{src.parent.name}/SKILL.md"
        expected = (
            f"{label}: handoff 「下一步:… `/{name}`」 missing the "
            f"Codex form `${name}` inside the same 「下一步:…」 baton"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills" / src.parent.name
            skills.mkdir(parents=True)
            # unmutated copy: the baton is dual-written today, so no baton error
            (skills / "SKILL.md").write_text(text, encoding="utf-8")
            assert expected not in validate(skills.parent, Path(tmp)), label
            # drop the `$name` twin from that baton only -> must redden
            (skills / "SKILL.md").write_text(
                text.replace(span, span.replace(f"`${name}", "`", 1), 1), encoding="utf-8"
            )
            assert expected in validate(skills.parent, Path(tmp)), label

    # #49 固化:push-before-commit-links. Hand-written cases first — order is the
    # whole point, so a file with both instructions in the wrong order is red.
    assert not unpushed_commit_link_issue("no links here, `git push` optional")
    assert unpushed_commit_link_issue("貼 commit links") is True
    assert not unpushed_commit_link_issue("先 `git push`,再貼 commit links")
    assert unpushed_commit_link_issue("貼 commit links,之後 `git push`") is True
    # prose "push" is not the step — only the runnable command counts
    assert unpushed_commit_link_issue("push 後貼 commit links") is True

    # the real-skill layer: every SKILL.md that pastes commit links must carry the
    # push step *before* it, and deleting that step from the real file must redden.
    # #41 was the same shape of bug in build; close/retro paste links too.
    pasters = [
        src
        for src in sorted((REPO / "skills").glob("*/SKILL.md"))
        if COMMIT_LINK_RE.search(src.read_text(encoding="utf-8"))
    ]
    assert pasters, "no skill pastes commit links — mutation has nothing to bite"
    for src in pasters:
        label = f"skills/{src.parent.name}/SKILL.md"
        text = src.read_text(encoding="utf-8")
        expected = (
            f"{label}: asks for commit links in a ticket comment without asking "
            f"to `git push` first — an unpushed sha is a 404"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills" / src.parent.name
            skills.mkdir(parents=True)
            copy = skills / "SKILL.md"
            copy.write_text(text, encoding="utf-8")
            assert expected not in validate(skills.parent, Path(tmp)), label
            # drop the push command -> the guard must bite
            copy.write_text(PUSH_RE.sub("commit", text), encoding="utf-8")
            assert expected in validate(skills.parent, Path(tmp)), label

    # #41 固化:the baton is a command the client pastes into Codex, so the skill
    # it names has to exist. Repo-level, so it lives outside validate() — a
    # single-skill install (install.py's fixtures) legitimately has no siblings.
    assert handoff_target_issues(REPO / "skills") == [], handoff_target_issues(
        REPO / "skills"
    )

    with tempfile.TemporaryDirectory() as tmp:
        skills = Path(tmp) / "skills"
        (skills / "a").mkdir(parents=True)
        baton = skills / "a" / "SKILL.md"

        baton.write_text(
            "---\nname: a\ndescription: d\n---\n下一步:`/gone #1`(Codex: `$gone #1`)",
            encoding="utf-8",
        )
        assert handoff_target_issues(skills) == [
            "skills/a/SKILL.md: handoff 「下一步:… `/gone`」 points at skills/gone, "
            "which does not exist — the client pastes that line into an agent"
        ], handoff_target_issues(skills)

        # the placeholder baton is the convention being quoted, not a command
        baton.write_text(
            "---\nname: a\ndescription: d\n---\n下一步:`/skill #N`(Codex: `$skill #N`)",
            encoding="utf-8",
        )
        assert handoff_target_issues(skills) == [], handoff_target_issues(skills)

    # the real-skill layer: the fixtures above are hand-written, so they stay
    # green even if every baton in the repo pointed nowhere. Take an actual
    # baton naming an actual sibling, delete that sibling, and it must redden.
    real = next(
        (src, name)
        for src in sorted((REPO / "skills").glob("*/SKILL.md"))
        for span in HANDOFF_SPAN_RE.findall(src.read_text(encoding="utf-8"))
        for name in SLASH_CMD_RE.findall(span)
        if name not in PLACEHOLDER_SKILLS
    )
    src, target = real
    with tempfile.TemporaryDirectory() as tmp:
        skills = Path(tmp) / "skills"
        for d in (REPO / "skills").iterdir():
            if d.is_dir():
                (skills / d.name).mkdir(parents=True)
        (skills / src.parent.name / "SKILL.md").write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8"
        )
        assert handoff_target_issues(skills) == [], handoff_target_issues(skills)
        (skills / target).rmdir()
        got = handoff_target_issues(skills)
        assert got and all(
            f"points at skills/{target}" in e for e in got
        ), (target, got)

    # dot-directory paths are target-repo prose, never links into the skill
    assert find_path_refs("`.out-of-scope/dark-mode.md` `.claude/settings.json`") == []
    assert find_path_refs("`./local.md` `../up.md`") == ["./local.md", "../up.md"]

    # the real-file layer: #46 was a dead link inside references/, invisible because
    # the ref check only read SKILL.md. Take actual shipped non-SKILL.md files — one
    # bundled discipline (must redden when mutated) and triage/OUT-OF-SCOPE.md, which
    # documents target-repo paths in prose (must stay quiet, untouched).
    bundled = sorted((REPO / "skills").glob("*/references/*.md"))
    assert bundled, "no skill bundles a references/*.md — mutation has nothing to bite"
    src = bundled[0]
    quiet = REPO / "skills" / "triage" / "OUT-OF-SCOPE.md"
    assert quiet.is_file(), quiet
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        # a fixed name, not the real skill's — an allowlisted skill would pass vacuously
        skill = repo / "skills" / "underreview"
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: underreview\ndescription: d\n---\nbody", encoding="utf-8"
        )
        (skill / quiet.name).write_text(quiet.read_text(encoding="utf-8"), encoding="utf-8")
        (repo / "docs").mkdir()
        (repo / "docs" / "gone.md").write_text("only at repo root", encoding="utf-8")
        shipped = skill / "references" / src.name
        text = src.read_text(encoding="utf-8")
        shipped.write_text(text, encoding="utf-8")
        # verbatim shipped files, including the target-repo prose one -> silent
        got = validate(repo / "skills", repo)
        assert got == [], got
        shipped.write_text(text + "\n見 `docs/gone.md`。\n", encoding="utf-8")
        got = validate(repo / "skills", repo)
        assert got == [
            f"skills/underreview/references/{src.name}: reference 'docs/gone.md' "
            f"escapes the skill dir (only resolves from outside — breaks once installed)"
        ], got

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
