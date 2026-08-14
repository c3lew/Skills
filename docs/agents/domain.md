# Domain Docs

探索程式碼前，讀取：

- 根目錄的 `CONTEXT.md`；若存在 `CONTEXT-MAP.md`，則讀取其中相關 context。
- 與工作範圍相關的 `docs/adr/` 文件。

文件不存在時直接繼續；由 domain-modeling 相關 skill 在真正需要時建立。

## Layout

本倉庫採 single-context：

/
├── CONTEXT.md
├── docs/adr/
└── src/

輸出應使用 `CONTEXT.md` 定義的領域詞彙。若內容牴觸既有 ADR，必須明確指出。
