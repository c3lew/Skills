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
from collections import defaultdict
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

# The key for "whatever calling this name hands back". Not an identifier, so
# it cannot collide with the real names it shares a dict with (#79).
RET = "()"


def runs(body):
    """The statements in `body` that actually execute, dead code cut out.

    Cut: a branch whose test is a constant the other way (`if False:`),
    everything after a `raise`/`return`, and the body of a def — a def only
    runs when something calls it, which `live_nodes` resolves separately.
    A *class* body is not cut: unlike a def it runs the moment the `class`
    statement does, so `class W: run = dump` really does bind `run` (#75).
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
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            # the header runs too, and it is where `for f in [dump]` binds
            # its target — the body is cut separately so it is not carried
            # along here (#75). Position is copied over: callers may report
            # or unparse whatever `runs` hands back.
            out.append(ast.copy_location(
                type(stmt)(target=stmt.target, iter=stmt.iter,
                           body=[], orelse=[], type_comment=None), stmt))
            out += runs(stmt.body) + runs(stmt.orelse)
        elif isinstance(stmt, (ast.While, ast.With, ast.AsyncWith)):
            out += runs(stmt.body) + runs(getattr(stmt, "orelse", []))
        elif isinstance(stmt, ast.ClassDef):
            out += runs(stmt.body)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        else:
            out.append(stmt)
        if isinstance(stmt, DEAD_END):
            break
    return out


CONSUMED_BY = frozenset(  # names that drain the iterable handed to them
    "list tuple set frozenset dict sum min max any all sorted next join "
    "extend writelines".split())

DRIVEN_BY = frozenset(  # names that hand a coroutine to the event loop (#87)
    "run gather wait wait_for create_task ensure_future "
    "run_until_complete".split())


def names_in(expr):
    """Every identifier `expr` reads — `Name.id` and `Attribute.attr` alike.

    A `Lambda` is not descended into. Its body is deferred code: it runs when
    something *calls* the lambda, not where the literal sits — the same reason
    `runs` cuts a def's body and `own_scope` stops at one. Walking in from here
    read the lambda's own parameter as if it were the module's dead `dump`, and
    read a lambda that merely *hands `dump` on* as if calling it ran `dump` —
    either way `return lambda: dump` came back as "what `get()` gives you", and
    `get()()` exempted a file where not one line of `dump` runs (#83). What a
    lambda reaches once it really is called is `free_in`.

    A `GeneratorExp` stops it for the same reason (#86): its body runs when
    something *iterates* the generator, not where the literal sits, so
    `keep(dump() for _ in [1])` hands `keep` a generator — it does not run
    `dump`, and reading the body here counted it as run, because an argument
    is assumed called. The first `for`'s iterable is the one part evaluated
    where the literal sits, the same way a lambda's parameter default is, so
    it is pushed back; the `ifs` and any later `for` are deferred with the
    body. A `ListComp` / `SetComp` / `DictComp` is not stopped: it runs to
    completion right there.
    """
    out, stack = set(), [expr]
    while stack:
        n = stack.pop()
        if isinstance(n, ast.Lambda):
            continue
        if isinstance(n, ast.GeneratorExp):
            stack.append(n.generators[0].iter)
            continue
        out.add(getattr(n, "id", getattr(n, "attr", None)))
        stack += list(ast.iter_child_nodes(n))
    return out


def free_in(lam):
    """What a `Lambda` reaches once something calls it — its args shadowed out.

    The other half of `names_in` stopping at a lambda. `own_scope` already
    refuses to walk into one, so a lambda's args never reach the `local` set a
    def's `return` is filtered against, while `names_in` used to walk in and
    read them anyway; that asymmetry is the one #83 was opened on, and putting
    both halves on the same boundary is what closes its nine cases.

    A parameter's *default* is not shadowed away with the parameter: it is
    evaluated out here, in the enclosing scope, and reaching the parameter
    inside the body is reaching whatever the default named — `lambda x=dump:
    x()` really does run `dump`. Only the defaults of parameters the body
    actually reads carry, because widening past that is the direction that
    makes this guard go quiet.

    Recursion falls out of `names_in`: a lambda nested in the body is left
    alone, because calling the outer one only *builds* the inner one.

    ponytail: this flattens "the body reads it" into "calling the lambda runs
    it", the same over-approximation `bindings_in` makes for `f = dump; f()`,
    and it is applied only where something really does call the lambda — a
    lambda a def merely *hands back* is not walked at all, because #83's own
    cases require `def get(): return lambda: dump` to stay dead under
    `get()()`. Two false reds fall out of that, both the noisy direction: one
    call level further (`get()()()`), and a returned lambda that does call
    what it was handed (`return lambda x=dump: x()`). A third falls out of
    the same flattening at the spot-call position: `(lambda: dump)()` merely
    *hands `dump` back*, and this reads it as running it — #84 declared that
    one a ceiling rather than close it, because separating the two needs the
    lambda to carry its own `RET` key.
    """
    a = lam.args
    slots = [p.arg for p in a.posonlyargs + a.args]
    pairs = list(zip(slots[len(slots) - len(a.defaults):], a.defaults))
    pairs += [(p.arg, d) for p, d in zip(a.kwonlyargs, a.kw_defaults) if d]
    reads = names_in(lam.body)
    bound = {p.arg for p in ast.walk(a) if isinstance(p, ast.arg)}
    return (reads - bound).union(*[names_in(d) for n, d in pairs if n in reads]
                                 or [set()])


def nodes_in(stmt, through=()):
    """Every node executing `stmt` reaches — deferred code stops it (#84, #86).

    The third face of the boundary #83 drew through `names_in` and `own_scope`:
    a lambda literal parked in a live statement is *built* there, not run
    there. Walking in read the `Call` inside an uncalled lambda's body as a
    call this statement makes, so `f = lambda: dump()` — bound to a name
    nobody ever calls — marked `dump` live and exempted a file where not one
    line of it runs. Six ways to park a lambda (a name, a list, a dict, a bare
    literal, a comprehension, a conditional) all rode on that one walk.

    A parameter *default* is not deferred: it is evaluated where the literal
    sits, so `f = lambda x=dump(): 1` really does run `dump` — those keep
    going.

    A `GeneratorExp` is the other deferred body Python writes inline, and it
    stops the walk on the same rule (#86): `g = (dump() for _ in [1])` builds
    a generator nobody consumes, so not one line of `dump` runs, and walking
    in read its `dump()` as a call this statement makes. Of the 6 shapes #86
    caught, 5 ride on this one walk — bound to a name, bare in a live
    statement, parked in a container, handed to a def that does not consume
    it, and the bypass written straight into an unconsumed generator body;
    the 6th, a generator function called but never iterated, is `live_nodes`'
    half. What the first `for`'s iterable is to a genexp, a parameter default
    is to a lambda: evaluated where the literal sits, so it is pushed back.
    `ListComp` / `SetComp` / `DictComp` are not stopped.

    `through` is the set of lambdas something really does call, and their
    bodies are walked like any other live code. The name half of that answer
    is `free_in`, which carries the *names* a called lambda reaches; this
    carries the *nodes*, which is what the bypass is looked up in — a
    `sys.stdout.buffer.write` written straight into a callback body has to
    stay reachable, and `free_in` alone cannot say so.

    ponytail: `through` is only ever handed in for the node list, never for
    the scan that decides what is invoked. Walking a called lambda's body
    there would read its *arguments* as the module's names again and hand
    back the shadowed-argument shapes #83 closed (`(lambda dump: dump())(1)`).
    """
    out, stack = [], [stmt]
    while stack:
        n = stack.pop()
        out.append(n)
        if isinstance(n, ast.Lambda) and n not in through:
            stack += [d for d in n.args.defaults + n.args.kw_defaults if d]
            continue
        if isinstance(n, ast.GeneratorExp) and n not in through:
            stack.append(n.generators[0].iter)
            continue
        stack += list(ast.iter_child_nodes(n))
    return out


def consumes(node, through=(), shadowed=()):
    """The expressions this one node really *runs* (#86, #87).

    The other half of stopping at a `GeneratorExp`: a generator body does run
    once something consumes it, and the guard has to say where. Four positions
    consume — a `for`'s iterable, `yield from`, the iterables of a
    comprehension that runs where it stands, and an argument handed to one of
    the builtins that drains what it is given. A genexp's own iterables are on
    this list only when the genexp itself is being consumed: evaluating
    `for x in E` builds `E`, and only iterating the genexp iterates `E` in
    turn.

    A coroutine is the third deferred body and drains the same way (#87).
    `adump()` on an `async def` builds a coroutine with not one line of its
    body run — the same claim `gens` makes about a generator def — and what
    really runs it is being driven: `await c`, `async for` over an async
    generator (already the `AsyncFor` branch), or being handed to the event
    loop by one of the `DRIVEN_BY` names (`asyncio.run(c)`, `gather`,
    `create_task`, …). Without those positions the `gens` half alone would
    turn every awaited coroutine into a false red.

    A name the module binds itself is *not* the builtin it collides with, so
    `shadowed` takes it off the list: `def sorted(g): return g` consumes
    nothing, and reading it as the builtin would hand back the switch #86 was
    opened on — one def, and a bypass parked in a generator exempts the file.
    That is why the collision is read off `binds`, the same collector #81 had
    to complete for the same reason.

    ponytail: `CONSUMED_BY` / `DRIVEN_BY` are name lists, not type checks —
    the callee is read by the same name-only reading `live_nodes` uses
    everywhere else, so a hand-rolled `run(coro)` of one's own is read as the
    event loop's. That widens the live set (the quiet direction), but the
    upgrade — telling `asyncio.run` from any other `run` — needs the import
    graph this name-only call graph never has. The 15 names on `CONSUMED_BY`
    drain an iterable; `map` / `filter` / `zip` / `enumerate` are
    deliberately off it, because they are deferred themselves. Four
    consuming shapes are left out and each costs a false red, the noisy
    direction: unpacking (`a, b = gen()`, `*rest`), a consumer reached through
    a second name (`h = g; list(h)`), a generator handed back and consumed a
    level up (`return gen()`), and a user-defined def that iterates its
    parameter — telling one of those from `keep(g)`, which merely hands the
    generator back, is what the fourth case of #86 pins. One shape is left
    open in the *quiet* direction and `shadowed` does not reach it: a method
    call (`b.extend(g)`) is matched on the attribute alone, so an object with
    a method of that name is read as draining what it is handed. Narrowing
    that needs the receiver's type, which this name-only call graph never
    has; `"".join(...)` is the shape that keeps the attribute reading here.
    """
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return [node.iter]
    if isinstance(node, (ast.YieldFrom, ast.Await)):
        return [node.value]
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
        return [c.iter for c in node.generators]
    if isinstance(node, ast.GeneratorExp):
        return [c.iter for c in node.generators] if node in through else []
    if isinstance(node, ast.Call):
        name = getattr(node.func, "id", getattr(node.func, "attr", None))
        if name in CONSUMED_BY | DRIVEN_BY and name not in shadowed:
            return list(node.args) + [k.value for k in node.keywords]
    return []


def own_scope(node):
    """Every node under `node` that belongs to *its* scope.

    `ast.walk` would descend into a nested def, and a nested def's `return`
    is its own — attributing it to the enclosing one would let a live
    `outer()` drag in a name only `inner` ever hands back, which widens the
    live set in the direction that makes the guard go quiet (#75).
    """
    stack = list(ast.iter_child_nodes(node))
    while stack:
        n = stack.pop()
        yield n
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.Lambda, ast.ClassDef)):
            stack += list(ast.iter_child_nodes(n))


def binds(node):
    """Every name this one node introduces into the scope it sits in (#81).

    A def's `return` hands back the *outer* `dump` only when `dump` is not a
    name the def made itself, so what this collects is the node kinds that
    make one. Eight branches cover them: `Name` in a `Store` context, `arg`,
    `alias`, a nested `def` or `class`, an `except` handler, the three
    `match` captures, and a PEP 695 type parameter. Two of those shipped with
    the rule (#79) — `Name` and `arg` — and each of the rest shadows the same
    name the same way, so leaving any one out hands `get()()` back as a
    one-line switch that exempts the whole file, which is exactly what #81
    hit. Collecting the whole face of one rule is what #75 had to do to
    `bindings_in` for the same reason: patched shape by shape, the shapes not
    yet named stay open. A `with ... as` target, a comprehension target and a
    walrus need no branch of their own — each is already a `Name` in a
    `Store` context. A `Lambda`'s args get no branch either, and the reason
    once given for that — `own_scope` stops at a lambda, so they are
    unreachable — described only half the reachability: `own_scope` stopped,
    `names_in` did not, so the body's names came through while the args that
    shadow them did not. That is the asymmetry #83 was opened on. Both halves
    stop at a lambda now, and what a *called* lambda reaches, args shadowed
    out, is `free_in`.

    Evidence: `self_check` pins six of the eight — the nested `def` and
    `class` share one branch and only `class` is pinned, because a nested def
    of the same name is *also* held down by the collapsed `defs` dict (#80),
    so a pin there would pass whether this branch collects it or not. It is
    covered by `79-return-sweep.py --own-names` instead, and turns into real
    evidence once #80 stops shadowing it. Lambda args are outside that count
    of eight: they are shadowed by `free_in`, whose evidence is the eight dead
    shapes and three ceilings `self_check` pins under #83, plus
    `81-lambda-sweep.py --lambda-scope`.

    ponytail: a `global`/`nonlocal` name is *not* collected — it declares the
    binding to be someone else's, so it is not a local shadow. That costs a
    false red on a def that returns a `global dump` it rebinds, the noisy
    direction, not the quiet one.
    """
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        return {node.id}
    if isinstance(node, ast.arg):
        return {node.arg}
    if isinstance(node, ast.alias):  # `import os as dump`, `import dump.sub`
        return {node.asname or node.name.split(".")[0]}
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
    if isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)):
        return {node.name} if node.name else set()
    if isinstance(node, ast.MatchMapping):
        return {node.rest} if node.rest else set()
    if isinstance(node, (ast.TypeVar, ast.ParamSpec, ast.TypeVarTuple)):
        return {node.name}  # PEP 695 `def get[dump]()`
    return set()


def bound_pairs(target, value):
    """`(name, source expression)` for one binding target, destructured.

    A tuple or list target against a same-length tuple or list value pairs up
    positionally (`a, b = dump, other` binds `a` to `dump` alone); anything
    else hands the whole right-hand side to each name it binds, which is the
    only reading available for `a, b = pair()`.
    """
    if isinstance(target, (ast.Tuple, ast.List)):
        elts = value.elts if (isinstance(value, (ast.Tuple, ast.List))
                              and len(value.elts) == len(target.elts)) else None
        for i, elt in enumerate(target.elts):
            yield from bound_pairs(elt, elts[i] if elts else value)
    elif isinstance(target, ast.Name):
        yield target.id, value


def binding_pairs(node):
    """`(name, source expression)` for every name the statement `node` binds.

    Split out of `bindings_in` because `live_nodes` needs the *expression* as
    well as the names it reaches: a name bound to a lambda has to be able to
    say *which* lambda, so calling that name can walk the right body (#84).
    """
    if isinstance(node, ast.Assign):
        pairs = [(t, node.value) for t in node.targets]
    elif isinstance(node, ast.AnnAssign) and node.value is not None:
        pairs = [(node.target, node.value)]
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        pairs = [(node.target, node.iter)]
    else:
        return
    for target, value in pairs:
        yield from bound_pairs(target, value)


def bindings_in(node):
    """`{name: names it was bound to}` for the one statement `node` (#75).

    The claim is one claim — calling this name calls whatever the right-hand
    side named — and every statement that makes it gets the same reach:
    `f = dump`, `f: object = dump`, `a, b = dump, dump`, `for f in [dump]`,
    and `class W: run = dump` (a class body runs where it stands, so `runs`
    hands its assignments through here like any other). Reading only a bare
    `Assign` target, as #73 shipped, left the rest writing the same thing and
    getting shouted at for it.

    A call on the right-hand side binds the *result*, not the callee:
    `f = get()` makes calling `f` call whatever `get` returns, which is the
    `RET` key, not `get` itself (#79).

    ponytail: a `with ... as f` is the same claim again and is *not*
    collected. Leaving it out costs a false red — a legitimate script told to
    pin a stream it already writes — which is the direction that makes noise,
    not the direction that makes the guard go quiet. The 6 shapes that are
    covered are the `--binding` sweep's; this is not one of them.
    """
    out = defaultdict(set)
    for name, src in binding_pairs(node):
        out[name] |= names_in(src)
        if isinstance(src, ast.Lambda):  # calling the name runs the body
            out[name] |= free_in(src)
        if isinstance(src, ast.Call):
            out[name] |= {RET + f for f in names_in(src.func) if f}
    return out


def live_nodes(tree):
    """Every AST node the module actually reaches (#70).

    The bypass half of the guard has to be positional like the pin half: a
    `sys.stdout.buffer` sitting in a never-called function or behind
    `if False:` is not "the script writes bytes", it is a switch anyone can
    flip to silence the guard — the same failure shape #60 closed for prose.

    Reachability is a name-only call graph from the module's top level, and
    what pulls a def's body in is its name in a *call* position: the `func` of
    a `Call` (`dump()`, `W().go()`), or an argument handed to something that
    calls it (`run(dump)`). A name bound to another name carries the same
    reach once that binding is itself called, however that binding is
    written — `=`, an annotated `=`, a tuple unpack, a `for` target or a
    class attribute, all collected by `bindings_in` — which is how an alias
    (`f = dump; f()`) and a handler dict (`H = {"a": dump}; H["a"]()`) reach
    the body without ever naming `dump` at a call (#71, #75).

    A def that returns a name carries it the same way, but the binding it
    makes is on the *result* of calling it, under the `RET` key: a factory
    reaches `dump` when the thing it hands back is itself called
    (`get()()`, `f = get(); f()`), and not when the result is dropped
    (`get()`) or parked in a name nobody calls (`x = get()`) — there not one
    line of `dump` runs, so exempting the file would be the switch again
    (#79). A name the def makes itself is not what it hands back either:
    `def get(): dump = 1; return dump` returns its local, which merely
    collides with the def's name — and so does every other way Python binds a
    local, `import as` and `except as` and a `match` capture and a nested
    `class` alike, all collected by `binds` (#81).

    A bare mention does not count and must not: `x = [dump]`, a local
    `dump = 1` that happens to shadow the def, an unrelated `c.dump` — none of
    them runs a line of `dump`, and counting them would hand back the switch
    #70 took away, since one colliding name anywhere live would exempt the
    whole file (#73).

    A lambda literal parked in a live statement is *built* there, not run
    there, so `reaches` stops the walk at it: `f = lambda: dump()` bound to a
    name nobody calls does not make `dump` live (#84). The two positions that
    really do call one still carry — on the spot via `free_in`, through a name
    via `bindings_in`.

    A generator is the same claim on the other deferred body (#86). Building
    one runs nothing: `g = (dump() for _ in [1])`, and `gen()` on a def whose
    body yields, both hand back a generator with not one line of that body
    run — so a genexp stops the walk (`nodes_in`), and a call on a generator
    def is dropped from `invoked`. What makes either live is being
    *consumed*, and `consumes` names the positions: a genexp consumed on the
    spot or through the name it was bound to, a generator def called in a
    consumed position.

    A coroutine is the third, and the same two halves carry it (#87). An
    `async def` goes on `gens` whether or not its body yields — calling one
    only builds a coroutine — and `consumes` names where one is really
    driven: `await`, `async for`, and the event-loop entry points. An async
    generator was already on `gens` for its `yield`; the plain `async def`
    was not, which is why five shapes — a coroutine bound, bare, parked in a
    container, handed to a def that does not await it, and the bypass written
    straight into an un-awaited coroutine body — all rode on one `async`
    keyword.

    ponytail: two approximations remain here — two defs sharing a name are
    one node, and a name handed to a call is assumed called by it (the three
    the generator half leaves are counted in `consumes`). Both widen the
    live set, which is the direction that makes this guard go *silent* on a
    script printing unpinned 中文, so each is kept to a shape where a call is
    the ordinary reading of the code; the four dead-`dump` shapes `self_check`
    pins under #73 stay dead. A call result handed straight to another call
    (`run(get())`) is *not* carried — that costs a false red, the noisy
    direction. Dead code is cut by `runs`.
    """
    defs = {n.name: n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    returned = defaultdict(set)  # what calling a def hands back, by RET key
    for name, node in defs.items():
        own = list(own_scope(node))
        local = set().union(*map(binds, own))
        for n in own:
            if isinstance(n, ast.Return) and n.value is not None:
                returned[RET + name] |= names_in(n.value) - local
    gens = {name for name, node in defs.items()  # calling one runs no line
            if isinstance(node, ast.AsyncFunctionDef)  # a coroutine — #87
            or any(isinstance(n, (ast.Yield, ast.YieldFrom))
                   for n in own_scope(node))}
    shadowed = set().union(*map(binds, ast.walk(tree)) or [set()])
    live, body, eaten_gens = set(), runs(tree.body), set()
    while True:
        invoked, called, lam_of = set(), set(), defaultdict(set)
        eaten_names, eaten_calls, gen_of = set(), set(), defaultdict(set)
        before = len(eaten_gens)
        bound = defaultdict(set, {k: set(v) for k, v in returned.items()})
        for stmt in body:
            for n in nodes_in(stmt, eaten_gens):
                for e in consumes(n, eaten_gens, shadowed):  # really iterated
                    if isinstance(e, ast.GeneratorExp):
                        eaten_gens.add(e)
                    elif isinstance(e, ast.Call):
                        eaten_calls |= names_in(e.func)
                    else:
                        eaten_names |= names_in(e)
                if isinstance(n, ast.Call):
                    invoked |= names_in(n.func)
                    if isinstance(n.func, ast.Lambda):  # `(lambda: x)()` — #83
                        invoked |= free_in(n.func)
                        called.add(n.func)
                    if isinstance(n.func, ast.Call):  # `get()()` — #79
                        invoked |= {RET + f for f in names_in(n.func.func) if f}
                    for arg in list(n.args) + [k.value for k in n.keywords]:
                        invoked |= names_in(arg)
                        if isinstance(arg, ast.Lambda):  # `sorted(key=…)` — #84
                            invoked |= free_in(arg)
                            called.add(arg)
                else:
                    for name, srcs in bindings_in(n).items():
                        bound[name] |= srcs
                    for name, src in binding_pairs(n):
                        if isinstance(src, ast.Lambda):
                            lam_of[name].add(src)
                        if isinstance(src, ast.GeneratorExp):
                            gen_of[name].add(src)
        for seed in (invoked, eaten_calls):
            todo = list(seed)
            while todo:  # an invoked binding invokes whatever it was bound to
                for name in bound.get(todo.pop(), ()):
                    if name not in seed:
                        seed.add(name)
                        todo.append(name)
        for name in eaten_names & set(gen_of):  # `g = (…); list(g)` — #86
            eaten_gens |= gen_of[name]
        fresh = (((invoked - gens) | eaten_calls) & set(defs)) - live
        if not fresh and before == len(eaten_gens):
            through = called.union(*[lam_of[n] for n in invoked & set(lam_of)]
                                   or [set()]) | eaten_gens
            return [n for stmt in body for n in nodes_in(stmt, through)]
        live |= fresh
        body = runs(tree.body) + [s for name in live for s in runs(defs[name].body)]


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

        # #71(a): the call graph counts a name in a *call* position, which an
        # alias, a handler dict and a callback all reach without ever naming
        # `dump` at a call — and every one really does write its bytes.
        for reach in ("f = dump\n    f()",
                      "H = {'a': dump}\n    H['a']()",
                      "run(dump)"):
            indirect = (f"def dump():\n    {out_bypass}.write(b'x')\n\n\n"
                        f"def run(cb):\n    cb()\n\n\n"
                        + runnable + reach + "\n    print('要開')\n")
            bad.write_text(indirect, encoding="utf-8")
            assert stream_encoding_issues(repo) == [], indirect
        # #75: the same binding claim, in the other shapes it gets written
        # in — each really does run `dump`, so a red here is the guard
        # shouting at a script that already writes its bytes. Three knobs
        # carry them: `bindings_in` collects the tuple unpack, the annotated
        # assignment and the `for` target (narrow it back to a bare `Assign`
        # and those three turn red); `runs` no longer cutting a class body is
        # what makes `class W: run = dump` an `Assign` anyone can collect;
        # and the `RET` binding in `live_nodes` is what carries the factory,
        # whether the result is called on the spot or through a name (#79).
        for reach in ("a, b = dump, dump\n    a()",
                      "f: object = dump\n    f()",
                      "for f in [dump]:\n        f()",
                      "get()()",
                      "f = get()\n    f()",
                      "W.run()"):
            shape = (f"def dump():\n    {out_bypass}.write(b'x')\n\n\n"
                     f"def get():\n    return dump\n\n\n"
                     f"class W:\n    run = dump\n\n\n"
                     + runnable + reach + "\n    print('要開')\n")
            bad.write_text(shape, encoding="utf-8")
            assert stream_encoding_issues(repo) == [], shape
        # ...and each of those three knobs stops where #73 put the line: bind
        # the name and never call it and `dump` is still dead. Without this
        # half the widening is only checked in the direction that makes noise,
        # not the direction that makes the guard go silent.
        for label, tail in (
                ("`for` target bound, never called",
                 runnable + "for f in [dump]:\n        pass\n    print('要開')\n"),
                ("class attribute bound, never called",
                 "class W:\n    run = dump\n\n\n" + runnable + "print('要開')\n"),
                ("factory returns it, nothing calls the factory",
                 "def get():\n    return dump\n\n\n" + runnable + "print('要開')\n"),
                ("a *nested* def returns it, only the outer one runs",
                 "def outer():\n    def inner():\n        return dump\n"
                 "    return 1\n\n\n" + runnable + "outer()\n    print('要開')\n"),
                # #79: the factory runs, but what it hands back never does.
                # Carry a return unconditionally and one `get()` exempts the
                # file without running a line of `dump` — the switch again.
                ("factory called, result dropped",
                 "def get():\n    return dump\n\n\n"
                 + runnable + "get()\n    print('要開')\n"),
                ("factory called, result parked in a name nobody calls",
                 "def get():\n    return dump\n\n\n"
                 + runnable + "x = get()\n    print('要開')\n"),
                ("what it returns is its own local, colliding by name",
                 "def get():\n    dump = 1\n    return dump\n\n\n"
                 + runnable + "get()()\n    print('要開')\n"),
                # #81: and its own local in every other shape that binds
                # one. Collect only `Name`/`arg`, as #79 shipped, and each of
                # these hands `get()()` back as a one-line exemption switch.
                *[(f"what it returns is its own {label}, colliding by name",
                   f"{head}\n{body}    return dump\n\n\n"
                   + runnable + "get()()\n    print('要開')\n")
                  for label, head, body in (
                      ("`import as`", "def get():",
                       "    import os as dump\n"),
                      ("plain `import`", "def get():", "    import dump\n"),
                      ("`from ... import as`", "def get():",
                       "    from os import path as dump\n"),
                      ("`except as`", "def get():",
                       "    try:\n        pass\n"
                       "    except Exception as dump:\n        pass\n"),
                      ("nested class", "def get():",
                       "    class dump:\n        pass\n"),
                      ("`match` capture", "def get():", "    match []:\n"
                       "        case [dump]:\n            pass\n"),
                      ("`match` star capture", "def get():", "    match []:\n"
                       "        case [*dump]:\n            pass\n"),
                      ("`match` mapping rest", "def get():", "    match {}:\n"
                       "        case {**dump}:\n            pass\n"),
                      ("type parameter", "def get[dump]():", ""),
                  )],
                # #83: `own_scope` stops at a `Lambda`, so the names a lambda
                # binds never reach `local` — while the other half of the same
                # line walked straight *into* the lambda body. Either way the
                # module's `dump` came out as what `get()` hands back, and not
                # one of these runs a line of it.
                *[(f"lambda scope: {shape.splitlines()[-1].strip()}",
                   f"def get():\n    {shape}\n\n\n"
                   + runnable + f"{call}\n    print('要開')\n")
                  for shape, call in (
                      ("return (lambda dump: dump)(1)", "get()()"),
                      ("f = lambda dump: dump\n    return f(1)", "get()()"),
                      ("return lambda dump: dump", "get()(1)"),
                      ("return lambda: dump", "get()()"),
                      ("return lambda x=dump: x", "get()()"),
                      # the default is evaluated, but naming `dump` is not
                      # calling it — and nothing here calls `x` either
                      ("f = lambda x=dump: 1\n    return f()", "get()"),
                      ("return (lambda: dump,)[0]", "get()()"),
                      ("return (lambda: (lambda: dump))()", "get()()"),
                  )],
                # #84: the other face of #83's boundary. `live_nodes` walked
                # each live statement with `ast.walk`, so a `Call` sitting in
                # a lambda *body* counted as invoked whether or not anything
                # ever called that lambda. Park a lambda in a live statement —
                # any of the six ways an expression gets parked — and the
                # `dump()` inside it exempted the file without running a line
                # of `dump`: the one-line switch #70 took away.
                *[(f"uncalled lambda in a live statement: {label}", tail)
                  for label, tail in (
                      ("f = lambda: dump()",
                       "f = lambda: dump()\n" + runnable + "print('要開')\n"),
                      ("xs = [lambda: dump()]",
                       "xs = [lambda: dump()]\n" + runnable + "print('要開')\n"),
                      ("d = {'k': lambda: dump()}",
                       "d = {'k': lambda: dump()}\n" + runnable + "print('要開')\n"),
                      ("bare literal (lambda: dump())",
                       runnable + "(lambda: dump())\n    print('要開')\n"),
                      ("[lambda: dump() for _ in []]",
                       "xs = [lambda: dump() for _ in []]\n"
                       + runnable + "print('要開')\n"),
                      ("None if xs else (lambda: dump())",
                       "f = None if xs else (lambda: dump())\n"
                       + runnable + "print('要開')\n"),
                  )],
                # #84: the same walk hands back the node list the bypass is
                # looked up in, so the write does not even need a dead def to
                # hide behind — parking it in an uncalled lambda's body was
                # the switch on its own.
                ("bypass written inside an uncalled lambda body",
                 f"f = lambda: {out_bypass}.write(b'x')\n"
                 + runnable + "print('要開')\n"),
                # #86: a generator is the other deferred body, and the same
                # walk read it as run. Building one runs nothing — a genexp
                # nobody consumes, and a generator def called but never
                # iterated — so 7 of the 8 shapes below exempted the file
                # without running a line of `dump`, and two of those did not
                # even need the dead def to hide behind: one extra pair of
                # parentheses around the write, or one def colliding with a
                # consumer's name, was the switch on its own. The 8th, a
                # generator def bound and never called, was already dead
                # before #86 and is here so the fix cannot hand it back.
                *[(f"unconsumed generator: {label}", tail) for label, tail in (
                    ("g = (dump() for _ in [1])",
                     "g = (dump() for _ in [1])\n" + runnable + "print('要開')\n"),
                    ("bare (dump() for _ in [1])",
                     runnable + "(dump() for _ in [1])\n    print('要開')\n"),
                    ("xs = [(dump() for _ in [1])]",
                     "xs = [(dump() for _ in [1])]\n"
                     + runnable + "print('要開')\n"),
                    ("handed to a def that does not consume it",
                     "def keep(g):\n    return g\n\n\n"
                     + runnable + "keep(dump() for _ in [1])\n"
                     "    print('要開')\n"),
                    ("generator def called, never iterated",
                     "def gen():\n    yield dump()\n\n\n"
                     + runnable + "gen()\n    print('要開')\n"),
                    ("generator def bound, never called",
                     "def gen():\n    yield dump()\n\n\n"
                     + runnable + "print('要開')\n"),
                    ("a def shadowing a consumer does not consume",
                     "def sorted(g):\n    return g\n\n\n" + runnable
                     + f"sorted({out_bypass}.write(b'x') for _ in [1])\n"
                     "    print('要開')\n"),
                    ("bypass written inside an unconsumed generator body",
                     f"g = ({out_bypass}.write(b'x') for _ in [1])\n"
                     + runnable + "print('要開')\n"),
                )],
        ):
            still_dead = f"def dump():\n    {out_bypass}.write(b'x')\n\n\n" + tail
            bad.write_text(still_dead, encoding="utf-8")
            assert len(stream_encoding_issues(repo)) == 1, label

        # #83 ceiling: the lambda *is* called, what it hands back really is the
        # dead def, and the result of that is called too — every line of `dump`
        # runs, so stopping at a `Lambda` must not redden this one.
        # A parameter default is the same story from the other side: it is
        # evaluated out here, so reaching the parameter reaches what it named.
        for body, call in (
                # #84: a lambda's parameter *default* is not deferred — it
                # is evaluated where the literal sits, so this one really does
                # run `dump` even though nothing ever calls the lambda.
                ("f = lambda x=dump(): 1\n    return 1", "get()"),
                # #84: the two positions that really do call the lambda
                # right where the literal sits — stopping at a `Lambda` must
                # not touch either. `free_in` carries the spot call, and
                # `bindings_in` carries the name it was bound to.
                ("f = lambda: dump()\n    f()\n    return 1", "get()"),
                ("(lambda: dump())()\n    return 1", "get()"),
                ("f = lambda: dump\n    return f()", "get()()"),   # bound, called
                ("return (lambda: dump)()", "get()()"),        # called on the spot
                ("f = lambda x=dump: x()\n    return f()", "get()"),   # default run
        ):
            alive = (f"def dump():\n    {out_bypass}.write(b'x')\n\n\n"
                     f"def get():\n    {body}\n\n\n"
                     + runnable + f"{call}\n    print('要開')\n")
            bad.write_text(alive, encoding="utf-8")
            assert stream_encoding_issues(repo) == [], alive

        # #84 (the cost side): stopping at a `Lambda` must not take the bypass
        # away from a lambda something really does call. `free_in` carries the
        # *names* at those positions, never the *nodes*, so without `through`
        # every one of these — a name called later, a spot call, and the two
        # ordinary callback shapes — turned red on a script that writes its
        # bytes on every run.
        for alive in (
            f"f = lambda: {out_bypass}.write(b'x')\n" + runnable
            + "f()\n    print('要開')\n",
            runnable + f"(lambda: {out_bypass}.write(b'x'))()\n"
            "    print('要開')\n",
            f"def dump():\n    {out_bypass}.write(b'x')\n" + runnable
            + "sorted([1], key=lambda v: dump())\n    print('要開')\n",
            f"def dump():\n    {out_bypass}.write(b'x')\n" + runnable
            + "list(map(lambda v: dump(), [1]))\n    print('要開')\n",
        ):
            bad.write_text(alive, encoding="utf-8")
            assert stream_encoding_issues(repo) == [], alive

        # #86 (the cost side): consuming a generator really does run its body,
        # so stopping at a `GeneratorExp` must not redden these. Four
        # consuming positions carry — a builtin that drains it, on the spot or
        # through the name it was bound to; a `for` over what a generator def
        # hands back; and a comprehension, which is not deferred at all — plus
        # the bypass written into a generator body something really consumes,
        # which only the node half (`through`) can keep reachable.
        dead_def = f"def dump():\n    {out_bypass}.write(b'x')\n\n\n"
        gen_def = "def gen():\n    yield dump()\n\n\n"
        for alive in (
            dead_def + runnable + "sum(1 for _ in (dump() for _ in [1]))\n"
            "    print('要開')\n",
            dead_def + "g = (dump() for _ in [1])\n" + runnable
            + "list(g)\n    print('要開')\n",
            dead_def + gen_def + runnable
            + "for _ in gen():\n        pass\n    print('要開')\n",
            dead_def + gen_def + runnable
            + "list(gen())\n    print('要開')\n",
            # a comprehension consumes what it loops over, so a generator
            # handed to one really does run
            dead_def + runnable + "[y for y in (dump() for _ in [1])]\n"
            "    print('要開')\n",
            # `names_in` carries the same eager iterable where `nodes_in`
            # cannot reach — into the body of a lambda something calls
            dead_def + "f = lambda: sum(x for x in dump())\n" + runnable
            + "f()\n    print('要開')\n",
            # the first `for`'s iterable is evaluated where the literal sits,
            # the way a lambda's parameter default is — this one runs `dump`
            # even though nothing ever consumes the generator
            dead_def + "g = (x for x in dump())\n" + runnable
            + "print('要開')\n",
            dead_def + runnable + "[dump() for _ in [1]]\n    print('要開')\n",
            runnable + f"list({out_bypass}.write(b'x') for _ in [1])\n"
            "    print('要開')\n",
        ):
            bad.write_text(alive, encoding="utf-8")
            assert stream_encoding_issues(repo) == [], alive

        # #73: and a bare *mention* stays dead. Widen the rule back to "the
        # name appears live" and one colliding local — or an unrelated
        # attribute — exempts the whole file, which is #70's switch again.
        for mention in ("", "x = [dump]\n    ", "dump = 1\n    ", "c.dump\n    "):
            never = (f"def dump():\n    {out_bypass}.write(b'x')\n"
                     + runnable + mention + "print('要開')\n")
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
