# Issue tracker: GitHub

本倉庫的 issues 與規格存放於 GitHub Issues。所有操作使用 `gh` CLI。

## Conventions

- 建立：`gh issue create --title "..." --body "..."`
- 讀取：`gh issue view <number> --comments`
- 列出：`gh issue list --state open`
- 留言：`gh issue comment <number> --body "..."`
- 標籤：`gh issue edit <number> --add-label "..."` 或 `--remove-label "..."`
- 關閉：`gh issue close <number> --comment "..."`

倉庫由目前目錄的 Git remote 自動判定。

## Pull requests as a triage surface

**PRs as a request surface: no.**

## Skill conventions

- 「publish to the issue tracker」：建立 GitHub issue。
- 「fetch the relevant ticket」：執行 `gh issue view <number> --comments`。
- `/wayfinder` 使用單一 map issue，並以 GitHub sub-issues 表示子任務。
- 無法使用 sub-issues 或原生 dependencies 時，退回 task list 與 `Blocked by: #<n>`。
