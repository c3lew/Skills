### Step 0 — baseline (clean repo)
OK validate green
exit=0

### Step 1 — inject a repo-root ref into skills/qa/SKILL.md

參考 `docs/blueprint.md`。
FAIL skills/qa/SKILL.md: reference 'docs/blueprint.md' escapes the skill dir (only resolves from outside �X breaks once installed)
exit=1

### Step 2 — inject a ../ escape into skills/next/SKILL.md
FAIL skills/next/SKILL.md: reference '../qa/SKILL.md' escapes the skill dir (only resolves from outside �X breaks once installed)
FAIL skills/qa/SKILL.md: reference 'docs/blueprint.md' escapes the skill dir (only resolves from outside �X breaks once installed)
exit=1

### Step 3 — same ref inside allowlisted skill retro
Updated 2 paths from the index
OK validate green
exit=0

### Step 4 — restore, back to green
Updated 1 path from the index
OK validate green
exit=0
?? docs/qa/

### Step 5 — regression: self-check + install.py
OK validate self-check green
OK installed tracking-viz -> C:\Users\user\.claude\skills\tracking-viz
OK installed triage -> C:\Users\user\.claude\skills\triage
OK installed ui-mockup -> C:\Users\user\.claude\skills\ui-mockup
(15 skills installed, exit=0)
