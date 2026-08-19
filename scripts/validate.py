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
command has to resolve to an installed skill dir on the other agent; and every
runnable `*.py` must pin stdout (and stdin, if it reads it) to UTF-8, because a
Windows console is cp950 and everything this line prints is 中文 (#58).
Does NOT validate prose content.

Usage:
    python scripts/validate.py               # lint the repo, exit 1 on errors
    python scripts/validate.py --self-check  # run built-in assertions
"""
import ast
import re
import sys
from textwrap import indent
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
# #64 固化:這一類 guard 證明的是「某句指示存在於散文中」,而繞過它的方式從來不是刪掉
# 關鍵詞,是把關鍵詞留著、動作反過來寫 —「**不要** git push」「**不用**問 client」。
# 所以「這句指示在」只認**沒被否定**的那次出現:動作詞前面貼著否定詞的不算數。
# 清單只收**兩字以上**的否定詞:單字的 `別`/`免` 是別的詞的零件 —「個別問 client」
# 「為避免 git push 失敗」會被誤判成否定,那是把講對話的散文判紅。
NEGATORS = ("不要", "不用", "不需", "不必", "不得", "不可",
            "無需", "無須", "毋須", "切勿", "禁止")
# 否定詞和動作詞中間塞得下引號、強調記號和一兩個副詞(「不用 `git push`」「不要先
# git push」),塞不下子句邊界 — 跨過標點就是另一句話,前一句的否定管不到它。
# ponytail: 這是有界的啟發式,不是語意分析。它咬的是「關鍵詞留著、當場反過來寫」
# 這一種繞過(#64 的母體);離否定詞四個字以外的改寫(「…時直接發佈,收工後再回報
# client」)還是綠的 — 那條靠 review 擋,再往下追是無底的詞表軍備賽。
NEGATOR_RE = re.compile(
    "(?:%s)[^,。;、!?\n]{0,4}$" % "|".join(NEGATORS)
)
# 往回看多遠由清單自己決定:最長的否定詞 + 中間容得下的字數。
NEGATOR_WINDOW = max(len(n) for n in NEGATORS) + 4


def unnegated(pattern, text):
    """Yield matches of `pattern` in `text` that no adjacent negator cancels."""
    for m in pattern.finditer(text):
        if not NEGATOR_RE.search(text[max(0, m.start() - NEGATOR_WINDOW):m.start()]):
            yield m


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
    return not any(m.start() < link.start() for m in unnegated(PUSH_RE, text))


# #57 固化:批次判斷(`/build-batch` 的 plan_batch)整個吃切票那關宣告的 blocking
# 邊。一整批票一條邊都沒宣告有兩種來源,票面上長得一模一樣:真的彼此不卡(平行切片,
# 常態),或切票時漏標。漏標的那批會被算成全部能同時開 — 兩張改同一個檔案的票並排
# 跑起來,撞在 merge 階段,而 client 從頭到尾沒被問過。所以呼叫 `/to-tickets` 發佈
# 票的 skill 一定要帶「一張 blocking 邊都沒宣告就回報 client」這一步:切票那關是
# 唯一還問得到人的地方。
# 母體只認**呼叫**那個字 — 光提到 `/to-tickets`(交棒行、路由表的一列)的 skill
# 一張票都沒發佈,要它帶這句話是假陽性。
TO_TICKETS_CALL_RE = re.compile(r"呼叫 `/to-tickets")
ZERO_EDGE_AUDIT_RE = re.compile("一張 blocking 邊都沒宣告")
# 判準是「條件詞 + 動作詞出現在同一個 span 裡」,不是「條件詞在不在」— 對照組
# find_slash_only_handoffs 就是這個形狀。span 斷在句號/換行:條件在這句、動作在下
# 一句,是兩句各自成立,不是那句指示存在(#64)。
ZERO_EDGE_SPAN_RE = re.compile(r"[^。\n]*%s[^。\n]*" % ZERO_EDGE_AUDIT_RE.pattern)
ASK_CLIENT_RE = re.compile(r"(?:回報|問|請示) client", re.I)


def missing_blocking_audit_issue(text):
    """True if a ticket-publishing skill never reports a zero-edge batch."""
    if not TO_TICKETS_CALL_RE.search(text):
        return False
    return not any(
        any(unnegated(ASK_CLIENT_RE, span))
        for span in ZERO_EDGE_SPAN_RE.findall(text)
    )


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


MAIN_BLOCK = 'if __name__ == "__main__"'
MAIN_TEST = ast.unparse(ast.parse(MAIN_BLOCK + ":\n    pass").body[0].test)
# (stream, pin, bypass, symptom). Two ways to survive a cp950 console: pin the
# stream's encoding, or go around the text layer entirely via .buffer. Both
# halves are positional (see the docstring): the pin must sit in the `__main__`
# block, the bypass must sit somewhere the module actually reaches (#70).
STREAM_PINS = (
    ("stdout", 'sys.stdout.reconfigure(encoding="utf-8")', "sys.stdout.buffer",
     "its 中文 output is mojibake"),
    ("stdin", 'sys.stdin.reconfigure(encoding="utf-8")', "sys.stdin.buffer",
     "中文 input is mojibake or UnicodeDecodeError"),
)


def code_exprs(node):
    """Every attribute access and call under `node`, as normalised source.

    Reading the AST instead of the file text is the whole point: comments are
    gone before parsing and a docstring is a str constant, never an Attribute,
    so prose *about* `sys.stdout.buffer` cannot pass for a use of it (#60).
    """
    return {ast.unparse(n) for n in ast.walk(node)
            if isinstance(n, (ast.Attribute, ast.Call))}


def norm(expr):
    """`expr` written the way ast.unparse would write it — quotes and all."""
    return ast.unparse(ast.parse(expr, mode="eval").body)


DEAD_END = (ast.Raise, ast.Return, ast.Break, ast.Continue)


def runs(body):
    """The statements in `body` that actually execute, dead code cut out.

    Cut: a branch whose test is a constant the other way (`if False:`),
    everything after a `raise`/`return`, and the body of a def — a def only
    runs when something calls it, which `live_nodes` resolves separately.
    An `except` handler counts as dead too: it is the error path, not the
    path a script prints its output on.
    """
    out = []
    for stmt in body:
        if isinstance(stmt, ast.If):
            try:
                branch = bool(ast.literal_eval(stmt.test))
            except Exception:
                branch = None  # not decidable — both halves may run
            if branch is not False:
                out += runs(stmt.body)
            if branch is not True:
                out += runs(stmt.orelse)
        elif isinstance(stmt, ast.Try):
            out += runs(stmt.body) + runs(stmt.orelse) + runs(stmt.finalbody)
        elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While, ast.With,
                               ast.AsyncWith)):
            out += runs(stmt.body) + runs(getattr(stmt, "orelse", []))
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.ClassDef)):
            continue
        else:
            out.append(stmt)
        if isinstance(stmt, DEAD_END):
            break
    return out


def live_nodes(tree):
    """Every AST node the module actually reaches (#70).

    The bypass half of the guard has to be positional like the pin half: a
    `sys.stdout.buffer` sitting in a never-called function or behind
    `if False:` is not "the script writes bytes", it is a switch anyone can
    flip to silence the guard — the same failure shape #60 closed for prose.
    Reachability is a name-only call graph from the module's top level, and a
    *mention* of a def's name pulls its body in — not just a call by that
    name. An alias (`f = dump`), a handler dict (`{"a": dump}`) and a callback
    argument (`run(dump)`) all reach the body, and none of them is a `Call`
    whose func is `dump` (#71).
    ponytail: deliberately over-approximates — a local variable that happens
    to shadow a def's name pulls that def in, and two defs sharing a name are
    one node. Both err toward calling code live, which is the safe direction
    for a guard whose bad outcome is stopping a legitimate script; dead code
    is still cut by `runs`.
    """
    defs = {n.name: n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    seen, called, todo = [], set(), runs(tree.body)
    while todo:
        for node in ast.walk(todo.pop()):
            seen.append(node)
            name = getattr(node, "id", getattr(node, "attr", None))
            if name in defs and name not in called:
                called.add(name)
                todo += runs(defs[name].body)
    return seen


def stream_encoding_issues(repo):
    """Every runnable script must pin its streams to UTF-8 (#58).

    A Windows console is cp950 by default, and everything this line carries is
    中文: an unpinned stdout prints the名單 as mojibake, and an unpinned stdin
    cannot even read a heredoc of ticket titles. Worse than mojibake, any
    character Big5 lacks (an emoji, a kana in a title) raises
    UnicodeEncode/DecodeError and kills the command outright.

    Both symptoms are invisible to an in-process assert — there the streams are
    a pipe or a StringIO, never the console — so the guard is structural: a
    file with a `__main__` block pins stdout, and pins stdin too if it reads
    it. No case-by-case judgement about whether *this* script's text happens to
    be ASCII today.

    The pin must sit *inside* the `__main__` block, so the check is positional
    like `unpushed_commit_link_issue`. A pin in `main()` is the shape that
    breaks: self_check calls `main()` with stdout captured into a StringIO,
    which has no `reconfigure` — a substring-anywhere check would call that
    green, which is exactly how this guard first shipped.

    The `.buffer` bypass is positional too, but by reachability rather than by
    block: `main()` legitimately writes bytes and `__main__` calls it, while a
    `.buffer` line in dead code or in a function nobody calls is a switch that
    silences the guard without printing a single byte (#70).

    A script that never prints is exempt outright: with nothing on its way to
    the console there is no 中文 to mangle, and demanding a pin there is a red
    against a legitimate script (#71). Unlike the bypass, this half reads the
    *whole file*, not the live set — #60 AC1 says 「檔案裡沒有裸 `print(`」, and
    a print sitting in dead code still means someone wrote this script to talk
    to a console. ponytail: `print(` is the whole test — a live
    `sys.stdout.write("中文")` with no `print` slips through; tighten if that
    shape ever ships.
    """
    errors = []
    for py in sorted(repo.rglob("*.py")):
        if any(part.startswith((".", "__")) for part in py.parts):
            continue  # __pycache__, .venv — not source anyone runs
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue  # nothing runs it either — not this guard's failure
        # walk, not tree.body: a `__main__` block nested one level under a
        # try or an `if` is still what runs the script (#65)
        main = next((n for n in ast.walk(tree) if isinstance(n, ast.If)
                     and ast.unparse(n.test) == MAIN_TEST), None)
        if main is None:
            continue
        whole, inside = code_exprs(tree), code_exprs(main)
        reached = {ast.unparse(n) for n in live_nodes(tree)
                   if isinstance(n, (ast.Attribute, ast.Call))}
        prints = any(isinstance(n, ast.Call)
                     and getattr(n.func, "id", None) == "print"
                     for n in ast.walk(tree))
        label = py.relative_to(repo).as_posix()
        for stream, pin, bypass, symptom in STREAM_PINS:
            if stream == "stdin" and f"sys.{stream}" not in whole:
                continue  # a script that never reads stdin has nothing to pin
            if stream == "stdout" and not prints:
                continue  # nothing reaches the console — nothing to mangle
            if norm(bypass) in reached or norm(pin) in inside:
                continue
            errors.append(
                f"{label}: runnable script does not pin {stream} to UTF-8 "
                f"inside its `{MAIN_BLOCK}` block — {symptom} on a cp950 "
                f"console (#58)"
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
        if missing_blocking_audit_issue(text):
            errors.append(
                f"{label}/SKILL.md: publishes tickets via `/to-tickets` but never "
                f"reports 「一張 blocking 邊都沒宣告」 to the client — a batch that "
                f"lost every edge looks exactly like one that has none, and "
                f"/build-batch then opens all of them in parallel"
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
    errors = (validate(REPO / "skills", REPO)
              + handoff_target_issues(REPO / "skills")
              + stream_encoding_issues(REPO))
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
    # 繞過方向:關鍵詞留著、意思反過來。一句「不要 git push」照樣含 `git push`,
    # 位置也在前面 — 只看關鍵詞在不在的 guard 會放行它。
    assert unpushed_commit_link_issue("不要 git push,直接在票上附 commit link") is True
    assert unpushed_commit_link_issue("不用 `git push`,先貼 commit links") is True
    # 換個否定詞、或中間塞個副詞,都還是同一句反過來的話
    assert unpushed_commit_link_issue("不可 git push,直接貼 commit link") is True
    assert unpushed_commit_link_issue("切勿 git push,直接貼 commit link") is True
    assert unpushed_commit_link_issue("不要先 git push,直接貼 commit link") is True
    assert unpushed_commit_link_issue("不用「**`git push`**」,先貼 commit links") is True
    # 反過來的假陽性:`免`/`別` 是別的詞的零件,不是這句話在否定 push
    assert not unpushed_commit_link_issue("為避免 git push 失敗,先跑 lint。之後貼 commit link")
    # 否定跨過標點就管不到下一句了 —「不要慌」不是「不要 push」
    assert not unpushed_commit_link_issue("不要慌,先 git push,再貼 commit link")

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
            # 繞過方向(#64):指令一個字都沒少,只是每一次都被反過來寫
            copy.write_text(PUSH_RE.sub("不要 git push", text), encoding="utf-8")
            assert expected in validate(skills.parent, Path(tmp)), label

    # #57 固化:zero-blocking-edge audit. Hand-written cases first — only a skill
    # that publishes tickets is on the hook, and carrying the line is the fix.
    assert not missing_blocking_audit_issue("這片沒有在切票")
    assert missing_blocking_audit_issue("呼叫 `/to-tickets <spec ref>` 切票") is True
    # 只是提到那個指令(交棒、路由表)不算發佈票 — 那張 skill 沒東西可以對帳
    assert not missing_blocking_audit_issue("沒有 spec 就指回 `/to-tickets`")
    assert not missing_blocking_audit_issue(
        "呼叫 `/to-tickets`;一張 blocking 邊都沒宣告時回報 client")
    # 繞過方向:條件詞原封不動留著,動作反過來寫 — 守的是那句主張,不是那個關鍵詞
    assert missing_blocking_audit_issue(
        "呼叫 `/to-tickets` 切票。一張 blocking 邊都沒宣告的時候,直接發佈,不用問 client。"
    ) is True
    # 條件詞在某一句、動作詞在另一句:兩句各自成立不代表那句指示存在
    assert missing_blocking_audit_issue(
        "呼叫 `/to-tickets` 切票。一張 blocking 邊都沒宣告的時候,直接發佈。"
        "有疑問回報 client。"
    ) is True
    assert missing_blocking_audit_issue(
        "呼叫 `/to-tickets` 切票。一張 blocking 邊都沒宣告時,不用再問 client,直接發佈。"
    ) is True
    assert missing_blocking_audit_issue(
        "呼叫 `/to-tickets` 切票。一張 blocking 邊都沒宣告時,無須問 client,直接發佈。"
    ) is True
    # 假陽性:`別` 出現在「分別/個別」裡,那句話沒有在否定任何東西
    assert not missing_blocking_audit_issue(
        "呼叫 `/to-tickets` 切票。一張 blocking 邊都沒宣告時,分別回報 client 每一張票。")
    assert not missing_blocking_audit_issue(
        "呼叫 `/to-tickets` 切票。一張 blocking 邊都沒宣告時,個別問 client 要不要併批。")

    # the real-skill layer: the cases above are hand-written strings, so they stay
    # green even if no shipped skill ever asked the question. Take the actual
    # ticket-publishing skills, delete the audit line, and validate must redden —
    # an empty 母體 fails here rather than passing vacuously.
    slicers = [
        src
        for src in sorted((REPO / "skills").glob("*/SKILL.md"))
        if TO_TICKETS_CALL_RE.search(src.read_text(encoding="utf-8"))
    ]
    assert slicers, "no skill publishes tickets via `/to-tickets` — mutation has nothing to bite"
    for src in slicers:
        label = f"skills/{src.parent.name}/SKILL.md"
        text = src.read_text(encoding="utf-8")
        m = ZERO_EDGE_AUDIT_RE.search(text)
        assert m, label
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills" / src.parent.name
            skills.mkdir(parents=True)
            copy = skills / "SKILL.md"
            copy.write_text(text, encoding="utf-8")
            got = [e for e in validate(skills.parent, Path(tmp)) if "blocking" in e]
            assert got == [], (label, got)
            # drop the audit line -> the guard must bite, naming this file
            copy.write_text(text.replace(m.group(0), "", 1), encoding="utf-8")
            got = [e for e in validate(skills.parent, Path(tmp)) if "blocking" in e]
            assert got and all(e.startswith(label) for e in got), (label, got)
            # 繞過方向(#64):條件詞原封不動,只把動作反過來 —「回報 client」變
            # 「不用問 client」。守關鍵詞的 guard 這裡會放行,守主張的不會。
            flipped = ASK_CLIENT_RE.sub("不用問 client", text)
            assert flipped != text, label
            copy.write_text(flipped, encoding="utf-8")
            got = [e for e in validate(skills.parent, Path(tmp)) if "blocking" in e]
            assert got and all(e.startswith(label) for e in got), (label, got)

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

    # #58 guard
    (out_stream, out_pin, out_bypass, _), (_, in_pin, in_bypass, _) = STREAM_PINS
    assert out_stream == "stdout"
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / "scripts").mkdir()
        # a module nobody runs has no console to lose
        lib = repo / "scripts" / "lib.py"
        lib.write_text("print('no main block, not runnable')", encoding="utf-8")
        assert stream_encoding_issues(repo) == []
        (repo / "__pycache__").mkdir()
        (repo / "__pycache__" / "x.py").write_text(MAIN_BLOCK + ":\n    pass\n",
                                                   encoding="utf-8")
        assert stream_encoding_issues(repo) == []

        bad = repo / "scripts" / "run.py"
        runnable = MAIN_BLOCK + ":\n    "
        bad.write_text(runnable + 'print("要開")\n', encoding="utf-8")
        assert [e.split(":")[0] for e in stream_encoding_issues(repo)] == ["scripts/run.py"]
        for pin in (out_pin, out_bypass):
            bad.write_text(runnable + pin + "\n", encoding="utf-8")
            assert stream_encoding_issues(repo) == [], pin
        # the pin has to be *in* the __main__ block. A reconfigure sitting in
        # main() is the shape AGENTS.md warns about — self_check calls main()
        # with a StringIO, which has no reconfigure — so it must still be red.
        bad.write_text(f"def main():\n    {out_pin}\n    print('要開')\n\n\n"
                       f"{runnable}main()\n", encoding="utf-8")
        assert len(stream_encoding_issues(repo)) == 1, stream_encoding_issues(repo)
        # ...while .buffer in main() is fine: it carries no encoding to get wrong
        bad.write_text(f"def main():\n    {out_bypass}.write(b'x')\n"
                       f"    print('要開')\n\n\n{runnable}main()\n",
                       encoding="utf-8")
        assert stream_encoding_issues(repo) == []

        # reading stdin is its own half of #58 — a pinned stdout is not enough
        reader = runnable + out_pin + "\n    json.load(sys.stdin)\n"
        bad.write_text(reader, encoding="utf-8")
        assert len(stream_encoding_issues(repo)) == 1, stream_encoding_issues(repo)
        assert "stdin" in stream_encoding_issues(repo)[0]
        for pin in (in_pin, in_bypass):
            bad.write_text(reader + "    " + pin + "\n", encoding="utf-8")
            assert stream_encoding_issues(repo) == [], pin

        # #60: prose is not code. A comment or docstring that *mentions*
        # the bypass (or the pin) used to satisfy a substring scan, so one
        # line of 「這裡沒走 sys.stdout.buffer」 switched the guard off.
        naked = runnable + 'print("要開")\n'
        for mention in (
            naked + "    # 這裡沒走 " + out_bypass + "\n",
            '"""' + out_bypass + ' 的說明,不是呼叫"""\n' + naked,
            naked + "    # 記得補 " + out_pin + "\n",
            'x = "' + out_bypass + '"\n' + naked,
        ):
            bad.write_text(mention, encoding="utf-8")
            assert len(stream_encoding_issues(repo)) == 1, mention

        # #70: the bypass only counts where the module actually reaches it.
        # Every one of these writes bytes *somewhere* in the AST — and every
        # one of them still prints naked 中文 when you run it.
        for dead in (
            f"def dump():\n    {out_bypass}.write(b'x')\n" + naked,
            f"if False:\n    {out_bypass}.write(b'x')\n" + naked,
            f"try:\n    pass\nexcept Exception:\n"
            f"    {out_bypass}.write(b'x')\n" + naked,
            naked + f"    raise SystemExit\n    {out_bypass}.write(b'x')\n",
        ):
            bad.write_text(dead, encoding="utf-8")
            assert len(stream_encoding_issues(repo)) == 1, dead
        # ...and the two shapes that do reach it stay green
        for alive in (
            runnable + f"{out_bypass}.write('要開'.encode())\n    print('要開')\n",
            f"def main():\n    {out_bypass}.write(b'x')\n    print('要開')\n"
            + runnable + "main()\n",
        ):
            bad.write_text(alive, encoding="utf-8")
            assert stream_encoding_issues(repo) == [], alive

        # #65: the `__main__` block does not have to be top-level. Indent it
        # one level under a try or an `if True` and a `tree.body`-only scan
        # stops finding it — the file is skipped and a naked print sails past.
        for wrapper in ("try:\n{body}except Exception:\n    pass\n",
                        "if True:\n{body}"):
            nested = wrapper.format(body=indent(naked, "    "))
            bad.write_text(nested, encoding="utf-8")
            assert len(stream_encoding_issues(repo)) == 1, nested
            pinned = wrapper.format(
                body=indent(runnable + out_pin + "\n    print('要開')\n", "    "))
            bad.write_text(pinned, encoding="utf-8")
            assert stream_encoding_issues(repo) == [], pinned

        # #71(a): the call graph counts a *mention* of a def, not only a call
        # by that name. Alias, handler dict and callback all reach the body —
        # and every one of these really does write its bytes when you run it.
        for reach in ("f = dump\n    f()",
                      "H = {'a': dump}\n    H['a']()",
                      "run(dump)"):
            indirect = (f"def dump():\n    {out_bypass}.write(b'x')\n\n\n"
                        f"def run(cb):\n    cb()\n\n\n"
                        + runnable + reach + "\n    print('要開')\n")
            bad.write_text(indirect, encoding="utf-8")
            assert stream_encoding_issues(repo) == [], indirect
        # the dead-code cases above must not come back green through the new
        # mention rule: nothing names `dump`, so nothing pulls it in.
        never = f"def dump():\n    {out_bypass}.write(b'x')\n" + naked
        bad.write_text(never, encoding="utf-8")
        assert len(stream_encoding_issues(repo)) == 1, never

        # #71(b): #60 AC1's second branch — a script with no live `print(` has
        # nothing on its way to the console, so it owes no pin.
        for quiet in (
            runnable + "open('out', 'w').write('要開')\n",
            runnable + "pass  # print('要開') only in a comment\n",
        ):
            bad.write_text(quiet, encoding="utf-8")
            assert stream_encoding_issues(repo) == [], quiet
        # ...but a print anywhere in the file counts, live or not: #65 keeps a
        # `__main__` block nested in a def red, and that print is not reachable.
        parked = "def dump():\n    print('nobody calls this')\n" + runnable + "pass\n"
        bad.write_text(parked, encoding="utf-8")
        assert len(stream_encoding_issues(repo)) == 1, parked
        # ...and one live print brings the pin back
        bad.write_text(naked, encoding="utf-8")
        assert len(stream_encoding_issues(repo)) == 1, naked

    # and the live repo is clean — every script that can be run pins its streams
    assert stream_encoding_issues(REPO) == [], stream_encoding_issues(REPO)

    print("OK validate self-check green")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # #58, AGENTS.md
    if "--self-check" in sys.argv:
        self_check()
        sys.exit(0)
    sys.exit(main())
