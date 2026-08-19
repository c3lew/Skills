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

### 會被跑到的 python 檔要釘 UTF-8

有 `if __name__ == "__main__"` 的 `*.py`,進入點第一行釘 stdout;會讀 stdin 的
再釘 stdin:

```python
sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")
```

Windows 主控台預設 cp950,而這條線印給 client 的東西全是中文 — 沒釘就是壞碼,
遇到 Big5 沒有的字(emoji、假名)直接 `UnicodeEncodeError` 當場中斷(#58)。

釘在 `__main__` 不是 `main()`:self-check 會拿 StringIO 呼叫 `main()`,
StringIO 沒有 `reconfigure`。另一條合法路是整段繞過 text layer 走
`sys.stdout.buffer.write(...)` / `sys.stdin.buffer.read()`(hook 走這條,因為
hook 掛了比壞碼更慘)— 這條沒有 encoding 可以搞錯,放哪都行。

`scripts/validate.py` 的 `stream_encoding_issues` 兩條都會抓,而且抓位置:
`reconfigure` 寫在 `__main__` 之外照樣紅。

### Domain docs

This repository uses a single-context layout. See `docs/agents/domain.md`.
