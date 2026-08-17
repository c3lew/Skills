# QA #39 — 敏感內容掃描 + repo 轉 public

票上「覆蓋驗收項」= **無 — 由 #40 的驗收項間接驗證**。無使用者可操作 UI,
不跑 Playwright walkthrough;本輪 QA = regression + 對五條驗收原句做**獨立事實核對**
(不採信建置方自陳,QA 自己重跑)。

一鍵重開指令(本 repo QA 環境 = 純 CLI):`python scripts/validate.py`

---

### Step 0 — regression suite

```
$ python scripts/validate.py
OK validate green
exit=0

$ python scripts/validate.py --self-check
OK validate self-check green
exit=0

$ git status --short
(clean)

$ git rev-list --left-right --count origin/main...HEAD
0	0
```

### Step 1 — 獨立重掃金鑰 / token(全 git history,非只有 HEAD)

```
$ git grep -nIE "sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|BEGIN [A-Z ]*PRIVATE KEY" $(git rev-list --all)
(no output)
exit=1   # git grep exit 1 = 0 命中
```

### Step 2 — 獨立重掃 email(tracked files,排除 LICENSE)

```
$ git grep -nIE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" -- . ':!LICENSE'
(no output)
```

### Step 3 — docs/pilot-quacket.md 實讀 + 對照物 visibility 查證

全文 1546 字元,內容為「Quacket A/B 試點計畫」方法論(對照形式、範圍、Desktop QA
環境選型、評量指標)。無第三方客戶名、無報價/合約/商業資料。唯一外部指向:

```
$ gh repo view c3lew/Quacket --json visibility,owner
{"owner":{"login":"c3lew"},"visibility":"PUBLIC"}
```

→ 指向的是**同一擁有者、本來就 public** 的 repo,不構成新曝光。票上「明確評估過並
標明處置」成立(處置:留,不改寫)。

### Step 4 — repo visibility

```
$ gh repo view --json visibility,licenseInfo,isPrivate
{"isPrivate":false,"visibility":"PUBLIC","licenseInfo":{"key":"mit","name":"MIT License"}}
```

### Step 5 — 匿名可達性(public 真的生效,不只是 API 欄位)

```
$ Invoke-WebRequest https://raw.githubusercontent.com/c3lew/Skills/main/LICENSE   # 未帶 auth
STATUS=200
MIT License
```

### Step 6 — 唯一 code 變更

commit `381eca4` 只新增 `LICENSE`(21 行)。逐行讀過,是未經修改的標準 MIT 樣板,
`Copyright (c) 2026 c3lew`。無邏輯可審。
