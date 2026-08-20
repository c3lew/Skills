# #42 QA walkthrough

## 結論

三條驗收原句均 PASS；blocking 0，known issue 0。獨立 judge 同判三條 PASS。

## 驗收對帳

### 1. 路由表推薦雙寫有機器守門 — PASS

獨立寬掃直接讀 Markdown 表格，不呼叫 `scripts/validate.py` 的 parser：

```text
baseline: rows=15 slash_commands=16 paired_names=0 mismatches=[16 個 Codex form 缺漏]
modified: rows=15 slash_commands=16 paired_names=16 mismatches=[]
exit=0
```

修前同一母體是 0/16 配對，修後是 16/16 配對；差額為 16 個新增配對。

### 2. 拿掉任一半會紅並指名缺漏 — PASS

在 HEAD 的隔離 worktree 逐次破壞、每次先還原，再照字面執行
`python scripts/validate.py`：

```text
FAIL skills/next/SKILL.md: /next route `/qa` missing the Codex form `$qa` in the same route row
exit=1

FAIL skills/next/SKILL.md: /next route `$qa` missing the slash form `/qa` in the same route row
exit=1
```

### 3. Regression 與換裝 — PASS

```text
python scripts/validate.py
OK validate green
exit=0

python scripts/validate.py --self-check
OK validate self-check green
exit=0

python scripts/install.py
20 個 skills 分別換裝至 .claude 與 .agents，逐項 OK
exit=0
```

換裝 readback：來源、`.claude` 與 `.agents` 三份 `next/SKILL.md` 的 SHA-256 均為
`581761219A987EAE03B22BDDF3572649635BDC5A0D8883769A3165BC80D640A4`。

修前 commit `2e5f68f` 的 `validate.py` 與 `--self-check` 也都是 exit 0；這證明舊守門
對 16 個路由表缺漏未咬住，而不是本輪沿用既有保護。

## 獨立 judge

只提供三條驗收原句與上述輸出，未提供實作脈絡。判定：AC1 PASS、AC2 PASS、
AC3 PASS；blocking 0。

## Blocking / known issues

- blocking：0
- known issues：0

## 未涵蓋範圍

本票是 CLI validator 與 Markdown 路由表，沒有 Web / Desktop UI、視覺 oracle 或
Tauri 原生殼；因此沒有 Playwright 錄影。

## Demo 實錄清單

- AC1：本檔「路由表推薦雙寫有機器守門」的修前／修後獨立寬掃。
- AC2：本檔「拿掉任一半會紅」的兩方向 mutation 原始輸出。
- AC3：本檔「Regression 與換裝」的三條命令、exit status 與安裝 readback hash。

## 一鍵重跑

```powershell
python scripts/validate.py; if ($LASTEXITCODE) { exit $LASTEXITCODE }; python scripts/validate.py --self-check; if ($LASTEXITCODE) { exit $LASTEXITCODE }; python scripts/install.py
```

下一步：`/client-demo #42`(Codex: `$client-demo #42`)
