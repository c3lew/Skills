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
CODEX_CMD_RE = re.compile(r"`\$([A-Za-z0-9_-]+)")
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


def has_codex_form(text, name):
    return re.search(rf"`\${re.escape(name)}(?![A-Za-z0-9_-])", text) is not None


def find_slash_only_handoffs(text):
    """Return skill names whose handoff baton lacks the Codex `$name` twin."""
    missing = []
    for span in HANDOFF_SPAN_RE.findall(text):
        for name in SLASH_CMD_RE.findall(span):
            if not has_codex_form(span, name):
                missing.append(name)
    return missing


def find_incomplete_next_routes(text):
    """Return (command, missing form) pairs from /next's route table."""
    header = "| 現場 | 下一棒 |"
    if header not in text:
        return []
    table = text.split(header, 1)[1].split("\n\n", 1)[0]
    issues = []
    for row in table.splitlines():
        if row.count("|") < 3:
            continue
        route = row.rsplit("|", 2)[-2]
        slash = set(SLASH_CMD_RE.findall(route))
        codex = set(CODEX_CMD_RE.findall(route))
        issues += [(name, "Codex") for name in sorted(slash - codex)]
        issues += [(name, "slash") for name in sorted(codex - slash)]
    return issues


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


# #107 固化:`/qa` 的並行池是三線 —— regression / walkthrough / code-review 同時開,彼此沒有
# 資料依賴。獨立 judge 不在池裡:它吃的是 walkthrough 產出的 a11y snapshot,提早開就拿到空證據,
# 然後把每一條驗收項都判 pass —— 而那份報告跟真的全過長得一模一樣(沒有紅字、沒有例外、
# 每條 pass),讀報告的人分不出來。這種靠肉眼看不出來的破壞要有守門咬著,所以判準有兩半:
# 並行池那張表列的 lane 必須**剛好**是這三支(多出一支 judge 就是有人把它丟進池裡,少
# 一支就是並行沒做滿),而且「judge 排在 walkthrough 之後」這句要在文字裡沒被否定地出現一次。
# 母體只認**自己開一支 judge** 的 skill —— 光在散文裡提到「獨立 judge」的
# (client-demo 的收尾、/next 的路由列)一支 judge 都沒跑,要它帶並行池是假陽性。
# 對照組是 TO_TICKETS_CALL_RE 的「呼叫」那個字(#57)。
JUDGE_RUNNER_RE = re.compile(r"subagent 當 judge")
POOL_LANES = ["regression", "walkthrough", "code-review"]
POOL_SECTION_RE = re.compile(r"^##[^\n]*並行池[^\n]*\n(.*?)(?=^## |\Z)", re.M | re.S)
# lane 名字只認表格第一欄的粗體 —— 那一欄就是池的宣告,散文裡提到 lane 名字不算
LANE_CELL_RE = re.compile(r"^\|\s*\*\*([^*|]+)\*\*\s*\|", re.M)
# 排序約束照 #64 的形狀:span 斷在句號/換行,條件(judge)與動作(walkthrough…之後)要在同一句
JUDGE_SPAN_RE = re.compile(r"[^。\n]*judge[^。\n]*")
JUDGE_AFTER_RE = re.compile(r"walkthrough[^。\n]{0,6}之後")


def judge_ordering_issues(text):
    """Return errors for a judge-running skill whose parallel pool lost its guard."""
    if not JUDGE_RUNNER_RE.search(text):
        return []
    issues = []
    section = POOL_SECTION_RE.search(text)
    if not section:
        issues.append(
            "runs an 獨立 judge but declares no 並行池 section — the three "
            "lanes have to be written down where the next agent reads them"
        )
    else:
        lanes = [c.strip() for c in LANE_CELL_RE.findall(section.group(1))]
        if sorted(lanes) != sorted(POOL_LANES):
            issues.append(
                f"並行池 lanes are {lanes} — must be exactly {POOL_LANES} "
                f"(order is free, the set is not); a "
                f"judge lane in that pool reads an empty a11y snapshot and "
                f"passes every criterion, which looks identical to a real pass"
            )
    if not any(any(unnegated(JUDGE_AFTER_RE, span))
               for span in JUDGE_SPAN_RE.findall(text)):
        issues.append(
            "never states that the 獨立 judge runs walkthrough…之後 — the ordering "
            "constraint is load-bearing, so it is written, not inferred"
        )
    return issues


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


def norm(stmt):
    """`stmt` written the way `ast.unparse` writes it — quotes and all.

    Both sides of the comparison go through this. `ast.unparse` emits single
    quotes, so a double-quoted literal lifted straight out of this file would
    silently never match — and under a rule like this one, "nothing matched"
    looks exactly like "everything is fine" (#96's prototype hit that twice).
    """
    return ast.unparse(ast.parse(stmt).body[0])


# (stream, pin, symptom). One way to survive a cp950 console: pin the stream.
# No `.buffer` bypass, no print detection, no exemptions — see the
# `stream_encoding_issues` docstring for why the old 557 lines went away (#96).
STREAM_PINS = (
    ("stdout", norm('sys.stdout.reconfigure(encoding="utf-8")'),
     "its 中文 output is mojibake"),
    ("stdin", norm('sys.stdin.reconfigure(encoding="utf-8")'),
     "中文 input is mojibake or UnicodeDecodeError"),
)


def main_blocks(tree):
    """Every `if __name__ == "__main__":` block in `tree`.

    walk, not tree.body: a block nested one level under a try or an `if` is
    still what runs the script (#65). And every one of them counts, not just
    the first one found (#69).

    Declared ceiling (#67): only the canonical spelling is recognised.
    `"__main__" == __name__` written the other way round, or
    `__name__ in ("__main__",)`, is not — a short and rare list that #96 chose
    to leave declared rather than enumerate.
    """
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.If) and ast.unparse(n.test) == MAIN_TEST]


def reads_stdin(tree):
    """True if `sys.stdin` is really touched — an AST attribute, not text.

    Reading the AST is the whole point: a docstring or a rule table that spells
    `sys.stdin.reconfigure(...)` out as a str constant is prose, never an
    Attribute, so this guard's own `STREAM_PINS` cannot make it believe every
    file in the repo reads stdin (#96 AC3).
    """
    return any(isinstance(n, ast.Attribute) and n.attr == "stdin"
               and getattr(n.value, "id", None) == "sys"
               for n in ast.walk(tree))


def is_source(rel):
    """True if `rel` is source someone could actually run.

    Only two things are excluded: `__pycache__` and dot-directories. The
    filter used to drop every path part starting with `__`, which swallowed
    `__main__.py` — the one filename that is *always* a package entry point,
    so package entries were permanently exempt from this guard (#68).
    """
    return not any(part == "__pycache__" or part.startswith(".")
                   for part in rel.parts)


def stream_encoding_issues(repo):
    """Every runnable script pins its streams to UTF-8, by convention (#58, #96).

    A Windows console is cp950 by default and everything these scripts carry is
    中文: an unpinned stdout prints the 名單 as mojibake, an unpinned stdin
    cannot read a heredoc of ticket titles, and any character Big5 lacks raises
    UnicodeEncode/DecodeError and kills the command outright. Both symptoms are
    invisible to an in-process assert — there the streams are a pipe or a
    StringIO, never the console — so the guard has to be structural.

    The rule is deliberately syntactic: a file with a `__main__` block writes
    the stdout pin among that block's *direct* statements, and the stdin pin
    too if it really touches `sys.stdin`. No exemption for `.buffer`, none for
    "this one never prints", and no question about whether a given line runs.

    That last question is what this used to be: 557 lines of reachability
    analysis across 12 functions and 31 tickets (#60–#95). 「這一行會不會跑」is
    the halting problem in a language with aliases, dynamic dispatch and
    getattr, so every round either widened into false reds on ordinary Python
    or narrowed into a bypass hiding in dead code. A convention has a finite
    state space, so it converges. The price is one no-op line in the one file
    that only writes bytes.

    First level, not anywhere inside: a pin under a nested `if` or `try` is the
    dead-code pin #72 filed, and a pin in `main()` is the shape this guard
    originally shipped broken — self_check calls `main()` with stdout captured
    into a StringIO, which has no `reconfigure`.
    """
    errors = []
    for py in sorted(repo.rglob("*.py")):
        rel = py.relative_to(repo)
        if not is_source(rel):
            continue
        label = rel.as_posix()
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError) as exc:
            # Not a skip (#66): "the guard cannot read this" and "this file is
            # fine" are different answers, and only one of them is safe to
            # report as green. Decoding belongs in the same breath as parsing —
            # a .py this guard cannot decode is exactly as unreadable, and left
            # uncaught it takes the whole run down with a traceback instead.
            errors.append(
                f"{label}: cannot be read as Python source — {exc}; a file this "
                f"guard cannot read counts as a fail, not a skip (#66)"
            )
            continue
        mains = main_blocks(tree)
        if not mains:
            continue
        for stream, pin, symptom in STREAM_PINS:
            if stream == "stdin" and not reads_stdin(tree):
                continue  # a script that never reads stdin has nothing to pin
            if all(any(ast.unparse(s) == pin for s in m.body) for m in mains):
                continue
            errors.append(
                f"{label}: runnable script does not pin {stream} to UTF-8 at "
                f"the first level of its `{MAIN_BLOCK}` block — {symptom} on a "
                f"cp950 console (#58)"
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
        for issue in judge_ordering_issues(text):
            errors.append(f"{label}/SKILL.md: {issue}")
        for name in find_slash_only_handoffs(text):
            errors.append(
                f"{label}/SKILL.md: handoff 「下一步:… `/{name}`」 missing the "
                f"Codex form `${name}` inside the same 「下一步:…」 baton"
            )
        for name, missing in find_incomplete_next_routes(text):
            if missing == "Codex":
                errors.append(
                    f"{label}/SKILL.md: /next route `/{name}` missing the "
                    f"Codex form `${name}` in the same route row"
                )
            else:
                errors.append(
                    f"{label}/SKILL.md: /next route `${name}` missing the "
                    f"slash form `/{name}` in the same route row"
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

    # #42: /next's fallback route table is client-facing too. Drop each Codex
    # half from the real table in turn; normal validate() must name the gap.
    next_src = REPO / "skills" / "next" / "SKILL.md"
    next_text = next_src.read_text(encoding="utf-8")
    route_table = next_text.split("| 現場 | 下一棒 |", 1)[1].split("\n\n", 1)[0]
    route_rows = [line for line in route_table.splitlines() if SLASH_CMD_RE.search(line)]
    assert route_rows, "next route table has no slash commands to verify"
    for row in route_rows:
        assert find_incomplete_next_routes("| 現場 | 下一棒 |\n" + row) == [], row
        route = row.rsplit("|", 2)[-2]
        for name in SLASH_CMD_RE.findall(route):
            expected = (
                f"skills/next/SKILL.md: /next route `/{name}` missing the "
                f"Codex form `${name}` in the same route row"
            )
            mutated_row, count = re.subn(
                rf"`\${re.escape(name)}(?![A-Za-z0-9_-])", "`", row, count=1
            )
            assert count == 1, (row, name)
            mutated = next_text.replace(row, mutated_row, 1)
            with tempfile.TemporaryDirectory() as tmp:
                skill = Path(tmp) / "skills" / "next"
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(mutated, encoding="utf-8")
                assert expected in validate(skill.parent, Path(tmp)), (row, name)

            expected = (
                f"skills/next/SKILL.md: /next route `${name}` missing the "
                f"slash form `/{name}` in the same route row"
            )
            mutated_row, count = re.subn(
                rf"`/{re.escape(name)}(?![A-Za-z0-9_-])", "`", row, count=1
            )
            assert count == 1, (row, name)
            mutated = next_text.replace(row, mutated_row, 1)
            with tempfile.TemporaryDirectory() as tmp:
                skill = Path(tmp) / "skills" / "next"
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(mutated, encoding="utf-8")
                assert expected in validate(skill.parent, Path(tmp)), (row, name)

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

    # #107 固化:並行池的 lane 表 + judge 的排序約束。judge 拿到空證據會把每一條都判
    # pass,而那份報告跟真的全過長得一模一樣 — 這條靠讀報告發現不了,只能靠守門。
    POOL_DOC = (
        "## 2. 並行池:三線同時開\n"
        "\n"
        "| lane | 做什麼 |\n"
        "| --- | --- |\n"
        "| **regression** | 跑既有 suite |\n"
        "| **walkthrough** | 照驗收原句實測 |\n"
        "| **code-review** | 讀 diff |\n"
        "\n"
        "## 3. 獨立 judge\n"
        "\n"
        "獨立 judge 排在 walkthrough 之後才開,不進並行池。\n"
        "開一個乾淨 subagent 當 judge,只餵驗收原句與證據。\n"
    )
    # 母體只認「自己開一支 judge」的 skill(#57 的教訓)—— 光提到那四個字不上鉤
    assert judge_ordering_issues("這片提到獨立 judge 抓 works-but-wrong,但自己沒跑") == []
    assert judge_ordering_issues(POOL_DOC) == []
    # 把 judge 丟進池裡 —— #107 指名的那個失敗形狀
    assert judge_ordering_issues(
        POOL_DOC.replace("| **code-review** | 讀 diff |",
                         "| **code-review** | 讀 diff |\n| **judge** | 判定 |")
    ), "judge lane in the pool must redden"
    # 少一支 lane:並行沒做滿,一樣是紅的
    assert judge_ordering_issues(
        POOL_DOC.replace("| **code-review** | 讀 diff |\n", "")
    ), "a missing lane must redden"
    # 表上下順序不算數 —— 整張票的主張就是「同時開始」,順序沒有語意
    assert judge_ordering_issues(
        POOL_DOC.replace("| **regression** | 跑既有 suite |\n", "")
        .replace("| **code-review** | 讀 diff |",
                 "| **code-review** | 讀 diff |\n| **regression** | 跑既有 suite |")
    ) == [], "lane order carries no meaning when all three start together"
    # 池整段消失:judge 還在跑,但沒人寫下三線同時開
    assert judge_ordering_issues(
        "獨立 judge 排在 walkthrough 之後才開。開一個乾淨 subagent 當 judge。")
    # 排序約束不見了
    assert judge_ordering_issues(
        POOL_DOC.replace("獨立 judge 排在 walkthrough 之後才開,不進並行池。", "獨立 judge 逐條判定。")
    ), "the ordering constraint has to be written down"
    # 繞過方向(#64):關鍵詞留著,順序反過來寫
    assert judge_ordering_issues(
        POOL_DOC.replace("排在 walkthrough 之後才開", "排在 walkthrough 之前就開")
    ), "a flipped ordering must redden"
    assert judge_ordering_issues(
        POOL_DOC.replace("獨立 judge 排在 walkthrough 之後才開,不進並行池。",
                         "獨立 judge 不用等 walkthrough 之後,直接進並行池。")
    ), "a negated ordering must redden"

    # real-skill layer:手寫字串綠不代表出貨的那支綠。拿真的 qa/SKILL.md 改壞,
    # validate 要指名那個檔 — 母體空掉的話這裡先炸,不會靜靜地 vacuously pass。
    judges = [
        src
        for src in sorted((REPO / "skills").glob("*/SKILL.md"))
        if JUDGE_RUNNER_RE.search(src.read_text(encoding="utf-8"))
    ]
    assert judges, "no skill runs its own judge — mutation has nothing to bite"
    for src in judges:
        label = f"skills/{src.parent.name}/SKILL.md"
        text = src.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills" / src.parent.name
            skills.mkdir(parents=True)
            copy = skills / "SKILL.md"

            def reds(body):
                copy.write_text(body, encoding="utf-8")
                return [e for e in validate(skills.parent, Path(tmp))
                        if "judge" in e or "並行池" in e]

            assert reds(text) == [], label
            lane = "| **code-review** |"
            assert lane in text, label
            mutated = text.replace(lane, "| **judge** | 一起跑 | 判定 |\n" + lane, 1)
            got = reds(mutated)
            assert got and all(e.startswith(label) for e in got), (label, got)
            got = reds(JUDGE_AFTER_RE.sub("walkthrough 之前", text))
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

    # #58 / #96 guard — the rule is syntactic: a `__main__` block writes the
    # pin among its own direct statements. No bypass, no exemptions.
    (out_stream, out_pin, _), (in_stream, in_pin, _) = STREAM_PINS
    assert (out_stream, in_stream) == ("stdout", "stdin")
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

        def reds(src):
            bad.write_text(src, encoding="utf-8")
            return stream_encoding_issues(repo)

        # the pin at the first level of `__main__` — that is the whole rule
        assert reds(runnable + out_pin + "\n    print('要開')\n") == []
        # ...and everything that is not that is red, however sane it looks
        for label, src in (
            ("no pin at all", runnable + "print('要開')\n"),
            # self_check calls main() with stdout captured into a StringIO,
            # which has no `reconfigure` — the shape this guard shipped broken
            ("pin lives in main()",
             f"def main():\n    {out_pin}\n    print('要開')\n\n\n"
             + runnable + "main()\n"),
            ("pin lives at module level", out_pin + "\n" + runnable + "pass\n"),
            # #72: a pin sitting in dead code does not count
            ("pin nested under an `if`",
             runnable + f"if True:\n        {out_pin}\n    print('要開')\n"),
            ("pin nested under a `try`",
             runnable + f"try:\n        {out_pin}\n    except Exception:\n"
             "        pass\n"),
            # #96 AC7: `.buffer` is no longer an exemption. Writing bytes stays
            # legal — the file just owes the same one no-op line as everyone.
            ("writes bytes, no pin", runnable
             + "sys.stdout.buffer.write('要開'.encode())\n"),
            ("writes bytes from main(), no pin",
             "def dump():\n    sys.stdout.buffer.write(b'x')\n\n\n"
             + runnable + "dump()\n"),
            # #96 AC8: the 「沒有裸 print( 就免 pin」 exemption is gone
            ("`__main__` block that prints nothing", runnable + "pass\n"),
            ("writes to a file, prints nothing",
             runnable + "open('out', 'w').write('要開')\n"),
            # #60: prose is not code, in both directions
            ("names the pin in a comment only",
             runnable + f"pass  # 記得補 {out_pin}\n"),
            ("names the pin as a str constant",
             f"x = {out_pin!r}\n" + runnable + "pass\n"),
        ):
            assert len(reds(src)) == 1, (label, reds(src))

        # #69: each block stands alone — pinning either one does not cover the
        # other, and pinning both is the positive control.
        first = runnable + out_pin + "\n    print('要開')\n"
        second = MAIN_BLOCK + ":\n    print('要開')\n"
        assert len(reds(first + second)) == 1
        assert len(reds(runnable + "print('要開')\n" + MAIN_BLOCK + ":\n"
                        + "    " + out_pin + "\n    print('要開')\n")) == 1
        assert reds(first + MAIN_BLOCK + ":\n    " + out_pin
                    + "\n    print('要開')\n") == []

        # stdin is its own half — a pinned stdout does not cover it
        reader = runnable + out_pin + "\n    json.load(sys.stdin)\n"
        assert [e.split(":")[0] for e in reds(reader)] == ["scripts/run.py"]
        assert "stdin" in reds(reader)[0]
        assert reds(reader + "    " + in_pin + "\n") == []
        # ...and 「有沒有碰 stdin」 is an AST attribute, not a text match: a file
        # that only *spells* sys.stdin owes nothing. This is what keeps
        # validate.py's own STREAM_PINS table from marking the whole repo red.
        assert reds(runnable + out_pin + "\n    x = 'sys.stdin.buffer'\n") == []

        # #65: a `__main__` block indented under a try or an `if` is still what
        # runs the script — a `tree.body`-only scan stops finding it and a
        # whole unpinned file sails past.
        for wrapper in ("try:\n{body}except Exception:\n    pass\n",
                        "if True:\n{body}"):
            naked = wrapper.format(body=indent(runnable + "print('要開')\n", "    "))
            assert len(reds(naked)) == 1, naked
            pinned = wrapper.format(body=indent(
                runnable + out_pin + "\n    print('要開')\n", "    "))
            assert reds(pinned) == [], pinned

        # declared ceiling (#67): only the canonical spelling is recognised.
        # Written the other way round this file is not seen as runnable at all,
        # so it owes nothing and gets nothing. Declared, not fixed — #96.
        assert reds('if "__main__" == __name__:\n    print("要開")\n') == []
        # ...and the same body under the canonical spelling is red. Without
        # this pair the green above cannot tell "the spelling is not
        # recognised" apart from "recognised, and this file is fine".
        assert len(reds('if __name__ == "__main__":\n    print("x")\n')) == 1
        # the other half of the same ceiling: `in (...)` is equivalent
        # Python and still not recognised.
        assert reds('if __name__ in ("__main__",):\n    print("x")\n') == []

        # #68: `__main__.py` is how a package is run, not a `__pycache__`
        # artefact — filtering every part that starts with `__` swallowed the
        # one filename that is always an entry point, so a package entry was
        # permanently exempt.
        pkg = repo / "scripts" / "pkg"
        pkg.mkdir()
        entry = pkg / "__main__.py"
        entry.write_text(runnable + "print('要開')\n", encoding="utf-8")
        assert [e.split(":")[0] for e in stream_encoding_issues(repo)] == [
            "scripts/pkg/__main__.py"], stream_encoding_issues(repo)
        entry.write_text(runnable + out_pin + "\n    print('要開')\n",
                         encoding="utf-8")
        assert stream_encoding_issues(repo) == [], stream_encoding_issues(repo)
        # ...and the filter still keeps out what it was actually for. The
        # `__pycache__` half is pinned above; this is the dot-directory half.
        (repo / ".venv").mkdir()
        (repo / ".venv" / "y.py").write_text(MAIN_BLOCK + ":\n    pass\n",
                                             encoding="utf-8")
        assert stream_encoding_issues(repo) == [], stream_encoding_issues(repo)

        # #66: a file that does not parse is a file this guard cannot clear.
        # Skipping it made "unreadable" and "fine" the same answer, so one typo
        # exempted a whole script.
        broken = repo / "scripts" / "typo.py"
        broken.write_text("def f(\n", encoding="utf-8")
        errs = stream_encoding_issues(repo)
        assert len(errs) == 1 and errs[0].startswith("scripts/typo.py: "), errs
        assert "cannot be read" in errs[0], errs
        broken.unlink()
        assert stream_encoding_issues(repo) == [], stream_encoding_issues(repo)
        # ...and 「讀不進來」 covers decoding too. Uncaught, a cp950-saved .py
        # raises UnicodeDecodeError and kills the whole run instead of failing
        # one file — a crash is not a verdict.
        latin = repo / "scripts" / "cp950.py"
        latin.write_text("x = '要開'\n", encoding="cp950")
        errs = stream_encoding_issues(repo)
        assert len(errs) == 1 and errs[0].startswith("scripts/cp950.py: "), errs
        latin.unlink()
        assert stream_encoding_issues(repo) == [], stream_encoding_issues(repo)

        # the dot half of the scope filter applies to filenames too, not just
        # directories — `.hidden.py` is not source anyone runs either.
        (repo / "scripts" / ".hidden.py").write_text(
            MAIN_BLOCK + ":\n    pass\n", encoding="utf-8")
        assert stream_encoding_issues(repo) == [], stream_encoding_issues(repo)

    # and the live repo is clean — every script that can be run pins its streams
    assert stream_encoding_issues(REPO) == [], stream_encoding_issues(REPO)

    print("OK validate self-check green")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # #58, AGENTS.md
    if "--self-check" in sys.argv:
        self_check()
        sys.exit(0)
    sys.exit(main())
