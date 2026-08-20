## 狀態

**已由 #96 改寫判準，實作落在 #97 / #98。** 本票保留的是舊 AC1 的問題來源與改判準紀錄。

## 新 AC1

有 `if __name__ == "__main__":` 的 `.py`，必須在**每一個該 block 的第一層**寫
`sys.stdout.reconfigure(encoding="utf-8")`；AST 內真的有 `sys.stdin` attribute 的檔案，
同一層也必須寫 `sys.stdin.reconfigure(encoding="utf-8")`。

判準不再看 `.buffer`、裸 `print(`、可達性或實際輸出內容；沒有 bypass 豁免。

## 為什麼改

舊 AC1 要求判斷 `sys.stdout.buffer.write` 是否位於「會被執行的位置」。#60–#95 這段紀錄
累積了 31 張票、557 行可達性分析；repo 現有 12 支 `*-sweep.py`，其 fixture 數會隨旗標模式改變；#96 盤點後確認這個開放式
判準無法靠有限 AST 列舉收斂，因此改成可直接做語法比對的固定約定。

## 驗收與落地

- #97：新判準上線、舊可達性分析移除。
- #98：多個 `__main__`、parse 失敗與 `__main__.py` 三個入口缺口補齊。
- #97 / #98 均已通過 QA 並結案。

## 出處

#96（spec：#60 AC1 改判準）。
