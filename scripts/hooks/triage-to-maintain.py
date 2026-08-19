#!/usr/bin/env python3
"""UserPromptSubmit hook: 打 `/triage` 時提醒改跑 `/maintain`。

原件 `/triage` 收尾不留「下一步」交棒 comment,也沒有 maintain 的四個 delta —
直接跑它,票分完類就掉出產線。這支只印一句提醒(exit 0),不擋。

Claude Code 限定:Codex 沒有 hook,那邊靠 maintain §2 與 /next 路由表兜。
"""
import json
import sys

REMINDER = (
    "這個專案的維護進件入口是 `/maintain`(它 wrap 了 `/triage`,補分級閉環、"
    "tech-debt 攢批、兩軸分流、refactor 儀式,收尾會在票上留「下一步」交棒 comment)。"
    "原件 `/triage` 不留交棒,票會掉出產線、`/next` 撿不回來。"
    "除非使用者明說要跑原件,否則改跑 `/maintain`(單張票:`/maintain #N`)。"
)


def hits(prompt):
    """True if the prompt invokes the bare `/triage` skill."""
    p = prompt.lstrip()
    return p == "/triage" or p.startswith("/triage ")


def main():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        prompt = json.loads(raw).get("prompt", "")
    except (json.JSONDecodeError, ValueError):
        return 0  # not our business — never block a prompt over a parse error
    if hits(prompt):
        # bytes, not print(): the console codepage on Windows is cp950 and a
        # UnicodeEncodeError here would kill the hook instead of the reminder
        sys.stdout.buffer.write((REMINDER + chr(10)).encode("utf-8"))
    return 0


def self_check():
    assert hits("/triage")
    assert hits("/triage #12")
    assert hits("  /triage 看一下這張票")
    assert not hits("/maintain #12")
    assert not hits("跑 /triage 之前先問一下")  # prose mention, not an invocation
    assert not hits("/triageX")
    print("OK triage-to-maintain self-check green")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        self_check()
        sys.exit(0)
    sys.exit(main())
