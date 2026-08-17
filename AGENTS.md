## Agent skills

### Issue tracker

Issues and specs are tracked in GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five canonical triage labels. See `docs/agents/triage-labels.md`.

### Handoff lines are dual-written

寫給 client 看的交棒行,同一行同時給兩種寫法:

```
下一步:`/qa #12`(Codex: `$qa #12`)
```

Codex 顯式呼叫 skill 用 `$name`,不是 `/name` — 只寫 slash 的交棒 comment 貼到
Codex 叫不動。skill 內部給 agent 讀的互叫措辭(「呼叫原件 `/implement`」)維持原樣,
不做全域替換。適用範圍是所有寫給 client 的下一棒指令:交棒 comment、`/next` 推薦、
dashboard hero。`scripts/validate.py` 會抓 `skills/*/SKILL.md` 裡「下一步:…」
baton 內漏寫的那一半(到 `」` 或行尾為止;baton 之外的內部措辭不管)。

### Domain docs

This repository uses a single-context layout. See `docs/agents/domain.md`.
