# QA walkthrough — #43 install self-check fixture 標示

驗收 oracle（bug ticket #43 原句）：

1. fixture 造成的預期輸出不會被誤讀成真的失敗（例如加 `[fixture]` 前綴，或只在最後印總結）。
2. `install.py --self-check` 仍然會在 fixture 真的沒被擋下時失敗（不是把檢查拿掉）。
3. `python scripts/validate.py` 綠。

環境：`D:/Self Project/Skills`，HEAD = `8d36435`，起始 working tree 乾淨。
本票是 CLI 顯示問題，沒有 UI，不走 Playwright；本檔是每條驗收項共用的終端實錄。

一鍵重開（沿用既有 CLI QA 入口）：

```powershell
cd "D:/Self Project/Skills"
python scripts/validate.py --self-check
python scripts/validate.py
python scripts/install.py --self-check
python scripts/install.py
```

## 步驟 1 — regression suite

```text
$ python scripts/validate.py --self-check
OK validate self-check green
exit 0

$ python scripts/validate.py
OK validate green
exit 0

$ python scripts/install.py --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
exit 0

$ python scripts/install.py
OK installed <15 skills> -> C:\Users\user\.claude\skills\...
OK installed <15 skills> -> C:\Users\user\.agents\skills\...
exit 0
```

四條既有 regression 全綠；正式 install 仍完整換裝兩個 agent roots。

## 步驟 2 — 驗收 1：fixture 訊息不再像產線真紅

`install.py --self-check` 的完整輸出只有兩行：

```text
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
```

預期失敗明確帶 `[fixture]` 前綴，與最後的綠色總結一致；沒有未標示的 `FAIL`。

## 步驟 3 — 驗收 2：test-the-test

以一次性 Python harness 只 bypass 「bad fixture 應被 install 擋下」的行為，再呼叫真實
`self_check()`；其餘 install 路徑不變。結果：

```text
Traceback (most recent call last):
  File "<stdin>", line 15, in <module>
  File "D:\Self Project\Skills\scripts\install.py", line 144, in self_check
    raise AssertionError("install should refuse on red validate")
AssertionError: install should refuse on red validate
exit 1
```

fixture 若真的沒被擋下，self-check 會紅；檢查仍在。

## 步驟 4 — 驗收 3：validate

```text
$ python scripts/validate.py --self-check
OK validate self-check green
exit 0

$ python scripts/validate.py
OK validate green
exit 0
```

## 步驟 5 — 獨立 judge

乾淨 subagent 只收到驗收原句與步驟 1–4 證據，未收到實作脈絡：

| 驗收原句 | judge | 理由 |
|---|---|---|
| fixture 預期輸出不會被誤讀成真的失敗 | **pass** | `[fixture]` 前綴清楚標示預期失敗，最後總結為 `OK`，exit 0。 |
| fixture 未被擋下時 self-check 仍失敗 | **pass** | test-the-test 觸發指定 `AssertionError`，exit 1。 |
| `python scripts/validate.py` 綠 | **pass** | 輸出 `OK validate green`，exit 0。 |

Works-but-wrong：0。

## Blocking / known issues / 未涵蓋

- Blocking：0。
- Known issues：0。
- 未涵蓋：無 UI 或原生殼；本票全部行為均為 CLI，已全數實跑。

## 步驟 7 — 固化(client-demo 過關後)

client-demo 過關前三條成立(#43 comment),指回 `qa` 固化。client-demo 點名的高價值
scenario:**`install.py --self-check` 的 fixture 失敗行必須帶 `[fixture]` 前綴,整體 exit 0**。

| 驗收項 | 固化狀態 | 在哪 |
|---|---|---|
| 1 fixture 預期輸出不會被誤讀成真的失敗 | **已固化**(本輪新增)| `install.py` self-check 末段:重跑自己一次(`--no-recurse`),斷言 child stdout 無任何未標示的 `FAIL` 行、且含 `[fixture] FAIL skills/bad: missing SKILL.md`、exit 0 |
| 2 fixture 沒被擋下時 self-check 仍失敗 | **已固化**(#43 build 時就在)| `install.py` self-check 紅 validate 區塊:`install()` 必須 `SystemExit(1)`,沒擋下就 `AssertionError("install should refuse on red validate")` |
| 3 `validate.py` 綠 | **已固化**(既有)| `validate.py --self-check` + `validate.py`,每輪 regression 都跑 |

### 為什麼要用 subprocess 重跑自己

受測對象是**終端上實際看到的那幾行**。in-process 斷言看不到 `print`,所以
以下兩種退化都會靜默通過:把 `print(f"[fixture] {failure}")` 改回 `print(failure)`、
或把 `contextlib.redirect_stdout(fixture_output)` 拆掉讓 FAIL 直接噴到真 stdout。
`--no-recurse` 讓 child 不再往下生 grandchild。

### Mutation 驗證(確認 guard 真的會咬)

```text
$ # 竄改 1:print(f"[fixture] {failure}") -> print(failure)
exit 1
AssertionError: FAIL skills/bad: missing SKILL.md
  (install.py self_check: assert unlabeled_failures(child.stdout) == [])

$ # 竄改 2:with contextlib.redirect_stdout(fixture_output): -> if True:
exit 1
AssertionError

$ # 還原後
python scripts/install.py --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
exit 0
```

### 固化後 regression 全綠

```text
$ python scripts/validate.py --self-check   -> OK validate self-check green, exit 0
$ python scripts/validate.py                -> OK validate green, exit 0
$ python scripts/install.py --self-check    -> [fixture] FAIL ... / OK install self-check green, exit 0
$ python scripts/install.py                 -> 兩個 agent roots 完整換裝, exit 0
$ git diff --check                          -> 綠
```
