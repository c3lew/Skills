#!/usr/bin/env python3
"""#114 第二把尺 —— 不讀 validate.py 的判準,改問 bash 自己。

`pasteable_command_issues` 是這輪的受測物,它綠只證明它同意自己。這支刻意
不套它的規則(命令字表 SHELL_CMD_WORDS、引號配對、前面要有空白的 `#`),
改用一個獨立的判準:把反引號 span 交給真的 shell 做 word splitting,看有沒有
token 在路上被吃掉。

作法:`bash -c 'set -- <span>; printf ...'` —— `set --` 只做參數設定,span 裡
的字不會被當指令執行,但 bash 的 tokenizer 會照真的規則跑(註解、引號、
跳脫全部生效)。拿 shell 吐回來的 token 數跟「照空白硬切」的數字比,少了
就是 shell 吃掉了東西。

母體刻意寫寬:`skills/` + `docs/specs/` + `docs/agents/` + `AGENTS.md` 的
**每一個**反引號 span,不先用命令字表篩。撈出來的多餘項逐筆判讀。

輸出不是綠/紅,是一份等人看的清單。
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
# PATH 上的 `bash` 在 Windows 會解到 WSL 的 bash.exe,而它在這台是壞的
# (execvpe(/bin/bash) failed)。壞掉的 bash 會讓每個 span 都落進「沒送進去」
# 桶,而「被吃掉 0 筆」看起來就跟全綠一模一樣 —— 這把尺會安靜地說謊。
# 所以開頭先驗一次 bash 真的會跑,不會就直接死。
BASH_CANDIDATES = (
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
    "bash",
)
ROOTS = ("skills", "docs/specs", "docs/agents")
EXTRA_FILES = ("AGENTS.md",)
SPAN_RE = re.compile(r"`([^`\n]+)`")
# 這幾個字元會讓 `set --` 真的去執行東西或改動 shell 狀態 —— 不送進去,
# 單獨列成 unadjudicated,由人判。
UNSAFE = re.compile(r"[$();|&<>\\]")
PLACEHOLDER_RE = re.compile(r"<[^<>\s]+>")


def _count(bash, span):
    script = "set -- " + span + "\nprintf '%s\\n' \"$#\"\n"
    r = subprocess.run([bash, "-c", script], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return int(r.stdout.strip() or 0)
    except ValueError:
        return None


def resolve_bash():
    """Pick a bash that actually runs, and prove it can see the known bug."""
    for cand in BASH_CANDIDATES:
        if cand != "bash" and not Path(cand).is_file():
            continue
        if cand == "bash" and not shutil.which("bash"):
            continue
        # 自檢:已知壞的那條(#114 的重現 scenario)一定要被看出來少 token,
        # 已知好的那條一定不能。兩面都對才承認這支 bash 能當尺。
        if _count(cand, "gh issue view #113 --comments") == 3 and \
           _count(cand, "gh issue view 113 --comments") == 5:
            return cand
    sys.exit("FATAL: 找不到能跑的 bash —— 這把尺沒有 oracle,不要相信它的輸出")


BASH = resolve_bash()


def shell_tokens(span):
    """Ask bash how many words this span really is. None = bash refused it."""
    return _count(BASH, span)


def main():
    targets = []
    for root in ROOTS:
        base = REPO / root
        if base.is_dir():
            targets += sorted(base.rglob("*.md"))
    for name in EXTRA_FILES:
        if (REPO / name).is_file():
            targets.append(REPO / name)

    eaten, unsafe, total = [], [], 0
    for md in targets:
        rel = md.relative_to(REPO).as_posix()
        for lineno, line in enumerate(md.read_text(encoding="utf-8").split("\n"), 1):
            for span in SPAN_RE.findall(line):
                if not span.strip():
                    continue
                total += 1
                # placeholder 先代換掉,否則 `<branch>` 會被 shell 當成 redirect
                probe = PLACEHOLDER_RE.sub("PLACEHOLDER", span)
                if UNSAFE.search(probe) or "`" in probe:
                    unsafe.append((rel, lineno, span))
                    continue
                naive = len(probe.split())
                got = shell_tokens(probe)
                if got is None:
                    unsafe.append((rel, lineno, span))
                elif got < naive:
                    eaten.append((rel, lineno, span, naive, got))

    print("掃過 %d 個檔 / %d 個反引號 span" % (len(targets), total))
    print("\n== shell 吃掉 token 的 span(%d 筆)==" % len(eaten))
    for rel, lineno, span, naive, got in eaten:
        print("%s:%d: `%s` — 照空白 %d 個 token,bash 只看到 %d 個"
              % (rel, lineno, span, naive, got))
    print("\n== 沒送進 bash 的 span(%d 筆,含 shell 元字元,人工判)==" % len(unsafe))
    for rel, lineno, span in unsafe:
        print("%s:%d: `%s`" % (rel, lineno, span))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
