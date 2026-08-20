import json
import re
import sys
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CURRENT = ROOT / "dashboard.html"
BASELINE = ROOT / "docs/qa/105-build/dashboard-original.html"
ISSUES = Path(__file__).with_name("issues-live.json")
EVIDENCE = Path(__file__).with_name("dashboard-evidence.json")
KNOWN = {42, 47, 48, 50, 59, 63, 103, 104}
CLOSED_REMOVED = {60, 74, 76, 77, 78}


def text(fragment: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def known_rows(html: str) -> list[str]:
    rows = re.findall(r"<li>(.*?)</li>", html, flags=re.DOTALL)
    marker = "\u5e36\u8457\u8d70"
    return [text(row) for row in rows if text(row).startswith(marker)]


def tile_count(html: str) -> int:
    match = re.search(
        '<div class="num"[^>]*>(\\d+)</div><div class="lbl">'
        '\u5c0f\u6bdb\u75c5\\(\u5e36\u8457\u8d70\\)</div>',
        html,
    )
    assert match, "known-issue tile not found"
    return int(match.group(1))


def main() -> None:
    current = CURRENT.read_text(encoding="utf-8")
    baseline = BASELINE.read_text(encoding="utf-8")
    issues = {item["number"]: item for item in json.loads(ISSUES.read_text(encoding="utf-8-sig"))}
    current_rows = known_rows(current)
    baseline_rows = known_rows(baseline)
    removed_rows = [row for row in baseline_rows if row not in current_rows]

    assert tile_count(current) == 8
    assert len(current_rows) == 8
    assert len(baseline_rows) == 14
    assert len(removed_rows) == 6
    assert "\u7b49\u4f60\u6c7a\u5b9a\u4ec0\u9ebc\u6642\u5019\u4fee" not in current
    boundary = "\u898f\u5247\u908a\u754c"
    issue_boundary = "\u5ba3\u544a\u904e\u7684\u5929\u82b1\u677f"
    not_todo = "\u4e0d\u662f\u5f85\u8fa6"
    assert boundary in current and not_todo not in "".join(current_rows)
    assert all(issues[number]["state"] == "OPEN" for number in KNOWN)
    assert all(issues[number]["state"] == "CLOSED" for number in CLOSED_REMOVED)
    assert issues[67]["state"] == "OPEN" and issue_boundary in issues[67]["title"]

    evidence = {
        "acceptance": "dashboard rerun numbers match",
        "tile": tile_count(current),
        "baseline_known_rows": len(baseline_rows),
        "current_known_rows": current_rows,
        "removed_stale_rows": removed_rows,
        "known_issue_states": [issues[number] for number in sorted(KNOWN)],
        "closed_removed_issue_states": [issues[number] for number in sorted(CLOSED_REMOVED)],
        "boundary_issue": issues[67],
    }
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"tile={tile_count(current)}")
    print(f"baseline_known_rows={len(baseline_rows)}")
    print(f"current_known_rows={len(current_rows)}")
    print(f"removed_stale_rows={len(removed_rows)}")
    print(f"live_known_issues={','.join(f'#{number}' for number in sorted(KNOWN))}")
    print(f"closed_removed_issues={','.join(f'#{number}' for number in sorted(CLOSED_REMOVED))}")
    print("boundary=#67 OPEN, shown only as a declared rule boundary")
    print("PASS dashboard ledger matches live issue state")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
