# QA walkthrough — #60 stream_encoding_issues 的豁免改成 AST 判準(bug fix)

Bug fix ticket,範圍 = 該 bug 的重現 scenario + regression suite。

判定 oracle(票上 `/maintain` 分流那則的重現 scenario 與完工定義原句):

> 1. 開一支新 script,裡面用裸 `print(` 輸出,**沒有**做 `sys.stdout.reconfigure`
> 2. 在檔案任一處(docstring 或註解都行)寫下字串 `sys.stdout.buffer`,例如 `# 這裡沒走 sys.stdout.buffer`
> 3. 跑 `python scripts/validate.py`
> 4. 現況:綠(豁免是全檔 substring 比對,註解就把守門關掉了)
> 5. 期望:紅 —「註解提到就豁免」不成立
>
> - [ ] AC1 豁免改成位置/語意判準(真的在會執行的位置用 `sys.stdout.buffer.write`,或檔案裡沒有裸 `print(`),不是全檔 substring
> - [ ] AC2 self-check 補一條咬上面那個 mutation
> - [ ] AC3 現況唯一走這條路的 `scripts/hooks/triage-to-maintain.py` L35 仍被正確豁免(不得誤紅)
> - [ ] AC4 `python scripts/validate.py` 綠

外加 repo 自己的紀律 `references/written-evidence.md`〈Guard 的完工定義〉三條:住在預設就會跑的
地方、兩種 mutation 都咬得到、**查不到目標時判 fail,不是靜靜略過**。這輪的 blocking finding
打在第三條。

交付物是 `scripts/validate.py` 的 guard,沒有 UI、沒有視覺 oracle,不走 Playwright、沒有錄影 —
實錄就是下面這份終端 transcript(全程 bash xtrace,指令與輸出在同一份,沒有事後 render)。
mutation 全部跑在拋棄式暫存目錄的副本或 `tempfile.mkdtemp()` 上,repo 本體沒被動過
(STEP 7 的 `git status` 是證據)。

環境:`D:/Self Project/Skills`,branch `main`,HEAD = `b5987ba`。

一鍵重開(client-demo / 之後每輪 QA 直接抄):

```bash
bash scripts/qa/60-walkthrough.sh "$(mktemp -d)/qa60"
```

步驟:

| # | 驗的是 | 對應驗收原句 |
| --- | --- | --- |
| 1 | regression suite:`validate.py` + 五支 self-check | AC4 / 既有 regression |
| 1b | **AC2 的反證**:副本裡把豁免那一行改回 #60 修之前的 substring 寫法(`bypass in py.read_text(...)`)→ `--self-check` 轉紅,爆掉的 assert 印出來的就是那條「`# 這裡沒走 sys.stdout.buffer`」mutation。self-check 綠不是因為沒加 case,是因為 case 真的咬得到 | AC2 |
| 2 | 拋棄式副本未動過 → 綠(證明後面判紅的是 mutation,不是副本壞了) | — 對照 |
| 3 | 票上的重現 scenario **原樣重跑**:丟一支裸 `print(` + 一行 `# 這裡沒走 sys.stdout.buffer` 的 script 進副本 → `validate.py` 判紅,error 指名 `scripts/_repro60.py` | 重現 scenario 第 5 點 |
| 4 | **同型全掃**:「提到」不是只有票上撞到的那一行 comment。母體 = 散文能出現的每個位置 × 兩個目標字串 = 13 條(檔頭 comment、行內 comment、module docstring、字串常數、f-string、近似變數名 × bypass / pin,加對照組與三條「真的用到」)→ 13/13 符合期望 | AC1 |
| 5 | 不得誤紅:`scripts/hooks/triage-to-maintain.py` L35 真的在跑 `sys.stdout.buffer.write`,仍豁免(該檔 error 數 = 0) | AC3 |
| 6 | #58 的原病沒退步:pin 放在 `main()`、或放在 `__main__` 之前的 top-level → 仍判紅;真的在 block 裡(含 block 內的 `try`)→ 綠。母體 4,4/4 符合 | AC1 位置那半 |
| 6b | **本輪 finding**:守門靜默跳過的三條路 — `__main__` 縮排在 `try` / `if True` 底下(找不到 top-level `If` node)、檔案 `SyntaxError`。三條都是裸 `print(`,期望紅、實際綠 | AC 之外(見下) |
| 6c | 對照組:同樣三條在 `d3cc9ed^`(#60 修之前)是判紅的 → 這是 AST 化引入的 regression,不是舊有天花板 | AC 之外 |
| 7 | repo 本體 `validate.py` 全綠,`git status` 只多這輪的 QA artifact | AC4 |

AC2 不能只靠 STEP 1 的 `--self-check` 綠 —— 沒加 case 也會綠,綠這件事跟「有沒有那條 case」
不相關,所以 STEP 1b 反著驗:把病還原,self-check 就必須紅。build 補的四條 mutation 住在
`self_check()` L806-818,是預設就會跑的地方(written-evidence〈Guard 的完工定義〉第一條)。

## 獨立 judge 判定

judge 是乾淨 subagent,只拿到上面的驗收原句 + transcript,沒有實作脈絡。

| 條目 | 判定 |
| --- | --- |
| 重現 scenario | pass |
| AC1 | pass(母體 13 全中,加碼位置判準 4/4) |
| AC2 | 第一輪判 **fail(舉證不足)**:「self-check 綠跟有沒有加 case 不相關」→ 補 STEP 1b 反證後 pass |
| AC3 | pass |
| AC4 | pass |

judge 對 STEP 6b 的意見(逐字重點):這不算某條 AC 的 fail —— 那兩條綠不是走豁免,是守門
根本沒把檔案當 runnable script。但 STEP 6c 證明它是這次改動自己造成的 regression,失效形態
跟 #60 要修的病同一類(裸 print 的 script 無聲過關),繞過成本極低(把 `if __name__` 縮進一層
`try` 就好),所以建議擋。QA 採納,列 blocking。

## Blocking

- **#65** `__main__` 縮排在 `try` / `if True` 底下 → 整檔跳過,守門不出聲(regression vs `d3cc9ed^`)。

## Known issues

- **#66** 檔案 `SyntaxError` → 整檔跳過。build 已在 code 裡註明是取捨,parse 不過的檔案本來就會在 import/執行時爆。
- `from sys import stdout` 這種 import 形式偵測不到 —— build 自己在 review findings 記過,改之前也一樣,不是這輪的 regression。
- `sys.stdout.reconfigure("utf-8")`(位置引數)判紅。等價安全但寫法不同,`norm(pin)` 是精確比對。改之前同樣判紅,不是 regression。
- STEP 1b 那段 traceback 的中文是 mojibake —— traceback 走 stderr,`STREAM_PINS` 只管 stdout / stdin。不在 #58 立的規矩範圍內。

## 未涵蓋範圍

沒有 UI、沒有 Tauri 原生殼,不適用。全部是 CLI guard,終端 transcript 即實錄。

## 終端實錄

```
+ echo '==== STEP 1  regression suite(validate + 五支 self-check)===='
==== STEP 1  regression suite(validate + 五支 self-check)====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ python '/d/Self Project/Skills/scripts/validate.py' --self-check
OK validate self-check green
+ python '/d/Self Project/Skills/scripts/batch.py' --self-check
OK batch self-check green
OK §8a/§8c conflict scenarios green
+ python '/d/Self Project/Skills/skills/build-batch/batch.py' --self-check
OK batch self-check green
+ python '/d/Self Project/Skills/scripts/install.py' --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
+ python '/d/Self Project/Skills/scripts/hooks/triage-to-maintain.py' --self-check
OK triage-to-maintain self-check green
+ echo '==== STEP 1b  self-check 真的咬得到「散文當 code」:副本裡把豁免改回 substring -> self-check 轉紅 ===='
==== STEP 1b  self-check 真的咬得到「散文當 code」:副本裡把豁免改回 substring -> self-check 轉紅 ====
+ grep -n 'norm(bypass) in whole' /tmp/tmp.D5hptrAqRR/qa60/repo/scripts/validate.py
266:            if norm(bypass) in whole or norm(pin) in inside:
+ sed -i 's|if norm(bypass) in whole or|if bypass in py.read_text(encoding="utf-8") or|' /tmp/tmp.D5hptrAqRR/qa60/repo/scripts/validate.py
+ grep -n 'bypass in py.read_text' /tmp/tmp.D5hptrAqRR/qa60/repo/scripts/validate.py
266:            if bypass in py.read_text(encoding="utf-8") or norm(pin) in inside:
+ set +e
+ python /tmp/tmp.D5hptrAqRR/qa60/repo/scripts/validate.py --self-check
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Temp\tmp.D5hptrAqRR\qa60\repo\scripts\validate.py", line 828, in <module>
    self_check()
    ~~~~~~~~~~^^
  File "C:\Users\user\AppData\Local\Temp\tmp.D5hptrAqRR\qa60\repo\scripts\validate.py", line 817, in self_check
    assert len(stream_encoding_issues(repo)) == 1, mention
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: if __name__ == "__main__":
    print("�n�}")
    # �o�̨S�� sys.stdout.buffer

+ echo 'exit 1  <- 非 0 是要的:#60 的病一還原,self-check 就該紅'
exit 1  <- 非 0 是要的:#60 的病一還原,self-check 就該紅
+ set -e
+ cp '/d/Self Project/Skills/scripts/validate.py' /tmp/tmp.D5hptrAqRR/qa60/repo/scripts/validate.py
+ echo '==== STEP 2  副本未動過 -> 綠(證明後面判紅的是 mutation,不是副本壞了)===='
==== STEP 2  副本未動過 -> 綠(證明後面判紅的是 mutation,不是副本壞了)====
+ python /tmp/tmp.D5hptrAqRR/qa60/repo/scripts/validate.py
OK validate green
+ echo '==== STEP 3  票上的重現 scenario 原樣重跑:裸 print + 一行「沒走 sys.stdout.buffer」註解 ===='
==== STEP 3  票上的重現 scenario 原樣重跑:裸 print + 一行「沒走 sys.stdout.buffer」註解 ====
+ cat
+ set +e
+ python /tmp/tmp.D5hptrAqRR/qa60/repo/scripts/validate.py
FAIL scripts/_repro60.py: runnable script does not pin stdout to UTF-8 inside its `if __name__ == "__main__"` block — its 中文 output is mojibake on a cp950 console (#58)
+ echo 'exit 1'
exit 1
+ set -e
+ rm /tmp/tmp.D5hptrAqRR/qa60/repo/scripts/_repro60.py
+ echo '==== STEP 4  同型全掃:「提到」的所有寫法 vs 「用到」的所有寫法 ===='
==== STEP 4  同型全掃:「提到」的所有寫法 vs 「用到」的所有寫法 ====
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills'
對照:裸 print,什麼都沒有              期望 RED    實際 RED    ok
提到 bypass — 行內 comment        期望 RED    實際 RED    ok
提到 bypass — 檔頭 comment        期望 RED    實際 RED    ok
提到 bypass — module docstring  期望 RED    實際 RED    ok
提到 bypass — 字串常數              期望 RED    實際 RED    ok
提到 bypass — f-string          期望 RED    實際 RED    ok
提到 bypass — 變數名近似             期望 RED    實際 RED    ok
提到 pin — 行內 comment           期望 RED    實際 RED    ok
提到 pin — docstring            期望 RED    實際 RED    ok
提到 pin — 字串常數                 期望 RED    實際 RED    ok
用到 bypass — 真的 write          期望 GREEN  實際 GREEN  ok
用到 pin — 雙引號                  期望 GREEN  實際 GREEN  ok
用到 pin — 單引號(unparse 正規化)     期望 GREEN  實際 GREEN  ok

母體 13,不合 0
+ echo '==== STEP 5  不得誤紅:真的走 buffer 的 triage-to-maintain.py 仍被豁免 ===='
==== STEP 5  不得誤紅:真的走 buffer 的 triage-to-maintain.py 仍被豁免 ====
+ grep -n sys.stdout.buffer '/d/Self Project/Skills/scripts/hooks/triage-to-maintain.py'
35:        sys.stdout.buffer.write((REMINDER + chr(10)).encode("utf-8"))
+ python - '/d/Self Project/Skills'
triage-to-maintain.py 的 error 數 -> 0
+ echo '==== STEP 6  #58 的原病沒退步:pin 放在 main() 而不是 __main__ block -> 仍判紅 ===='
==== STEP 6  #58 的原病沒退步:pin 放在 main() 而不是 __main__ block -> 仍判紅 ====
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --positional
pin 在 main(),__main__ 只呼叫它      期望 RED    實際 RED    ok
pin 在 __main__ 之前的 top-level    期望 RED    實際 RED    ok
pin 真的在 __main__ block 裡        期望 GREEN  實際 GREEN  ok
pin 在 __main__ block 裡的 try 底下  期望 GREEN  實際 GREEN  ok

母體 4,不合 0
+ echo '==== STEP 6b  本輪抓到的:守門靜默跳過的兩條路(期望紅、實際綠)===='
==== STEP 6b  本輪抓到的:守門靜默跳過的兩條路(期望紅、實際綠)====
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --skips
__main__ 縮排在 try 底下 -> 找不到 top-level If,整檔跳過           期望 RED    實際 GREEN  MISMATCH
__main__ 縮排在 if True 底下 -> 同上                          期望 RED    實際 GREEN  MISMATCH
檔案 parse 不過(SyntaxError)-> 整檔跳過(build 已在 code 裡註明的取捨)  期望 RED    實際 GREEN  MISMATCH

母體 3,不合 3
+ echo 'exit 1  <- 非 0 是預期的,這三條是本輪 QA 的 finding,不是 AC'
exit 1  <- 非 0 是預期的,這三條是本輪 QA 的 finding,不是 AC
+ set -e
+ echo '==== STEP 6c  對照組:同樣兩個 case 在改之前(d3cc9ed^)是判紅的 ===='
==== STEP 6c  對照組:同樣兩個 case 在改之前(d3cc9ed^)是判紅的 ====
+ python '/d/Self Project/Skills/scripts/qa/60-mention-sweep.py' '/d/Self Project/Skills' --skips --old
__main__ 縮排在 try 底下 -> 找不到 top-level If,整檔跳過           期望 RED    實際 RED    ok
__main__ 縮排在 if True 底下 -> 同上                          期望 RED    實際 RED    ok
檔案 parse 不過(SyntaxError)-> 整檔跳過(build 已在 code 裡註明的取捨)  期望 RED    實際 RED    ok

母體 3,不合 0
+ echo '==== STEP 7  repo 本體沒被動過 ===='
==== STEP 7  repo 本體沒被動過 ====
+ python '/d/Self Project/Skills/scripts/validate.py'
OK validate green
+ git -C '/d/Self Project/Skills' status --short
?? docs/qa/60-walkthrough.md
?? scripts/qa/60-mention-sweep.py
?? scripts/qa/60-walkthrough.sh
```
