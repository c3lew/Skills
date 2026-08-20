# `/qa #98` walkthrough — 新判準的入口缺口:守門到底看到了哪些檔

**HEAD**: `4d82c78` ｜ 一鍵重開:`bash scripts/qa/98-walkthrough.sh "$(mktemp -d)/qa98"`

這一輪驗的是 #98(把新判準剩下的三個入口缺口補起來:每個 `__main__` 各自檢查、parse
不動判 fail、`__main__.py` 不被 `__` 開頭的過濾誤傷)修完之後,票上那三條驗收原句成不
成立。範圍 = 票上「覆蓋驗收項」三條 + 既有 regression suite + 全域修前對照(修前 =
`91b6b98`)+ 一把刻意寫寬、不套受測規則的第二把尺 + mutation 台**含基準線控制組**。
全程 bash xtrace,指令與輸出同一份,沒有事後 render。

**結論:判 fail,一條 blocking。**

- **三條驗收原句本身全部成立,而且每一條都有反面對照組**:兩個 `__main__` 只釘第一個
  → 吵、只釘**第二個** → 一樣吵、兩個都釘 → 綠(STEP 2);打錯字的 `.py` → 吵而且訊息
  帶檔名與原因、字打對 → 綠、cp950 存的 `.py` → 判紅不是 traceback(STEP 3);
  `pkg/__main__.py` 沒 pin → 吵、補 pin → 綠、`__pycache__` / `.venv` / `.hidden.py`
  三格沒 pin → 仍綠(STEP 4)。
- **修前對照沒有本輪引入的誤紅**:QA 照驗收原句自己寫的兩面母體 22 格,修後 22/0;
  修前修後的差額**只有 3 筆,全是「修前綠 → 修後紅」**,而且逐筆對得上票面三條
  (`pkg/__main__.py`、syntax error、cp950)。零筆「修前紅 → 修後綠」(STEP 5)。
- **順手收掉票面沒列的第四個入口缺口**:修前的過濾吃的是**絕對路徑**的 parts,repo 只要
  被 clone 到 `~/.local/…` 這種路徑底下,整條守門就靜靜全綠(修前 0 紅 vs 修後 11 紅,
  STEP 5 最後一節)。修後改吃相對路徑,不受影響 —— 但**沒有任何 fixture 或 knob 釘住
  這件事**(known issue 1)。
- **blocking:那張 mutation 台是壞掉的儀器。** `97-mutate.py --run` 印「15/15 咬住」,
  可是它做的副本裡只有 `scripts/validate.py` 一個檔,而 `self_check()` 在第 466 行就會
  因為讀不到 `skills/` 而 `AssertionError` —— 早在跑到第 913 行那些 stream fixture 之前。
  **控制組(knob 一個都不套)就已經 exit 1**,所以整張表不管改成什麼都印「咬住」,一格
  都沒在量(STEP 7b)。QA 換成完整 repo 副本重跑,15 個 knob 確實 15/15 真的被咬住 ——
  性質是對的,**但票上那個數字現在不是證據**。

## 一、票上「覆蓋驗收項」逐條

| 驗收原句 | 實測 | 判定 |
| --- | --- | --- |
| 一個檔有幾個 `__main__` 就檢查幾個,不是只看第一個 | 只釘第一個 → `exit 1`;只釘第二個 → `exit 1`;兩個都釘 → `exit 0`;第二把尺同一格 `不合 1`(修前的 probe 同一格 `不合 0`) | pass |
| 檔案 parse 不動要判 fail,不是靜靜跳過 | `def f(` → `FAIL scripts/qa/zz-case-typo.py: cannot be read as Python source — '(' was never closed …`;字打對 → `exit 0`;cp950 存的 `.py` → `exit 1`(不是 traceback) | pass |
| `__main__.py` 不得被 `__` 開頭的過濾誤傷 | `scripts/pkg/__main__.py` 沒 pin → `exit 1`;補 pin → `exit 0`;`__pycache__` / `.venv` / `.hidden.py` 沒 pin → `exit 0` | pass |

票面其餘 acceptance criteria:

| 票上要求 | 實測 | 判定 |
| --- | --- | --- |
| 三條各有 self-check fixture | 五格 inline fixture 都在,`underscore_filter` / `unreadable_skip` / `decode_error_uncaught` / `first_main_only` 四個 knob 在完整副本上逐一轉紅 | pass |
| knob 改壞要轉紅,mutation 台進 repo | 台在 repo,但**控制組不套 knob 就已經紅**,15/15 這個數字不是證據 | **fail(blocking)** |
| `validate.py` + 五支 self-check 全綠 | 全綠(STEP 1) | pass |
| `96-newrule-probe.py` 全綠 | 對 repo 本體 `不合 0`(STEP 8) | pass |
| repo 裡現在有沒有 `__main__.py`;沒有就補 fixture 釘住 | repo 28 個 `.py` 一個都沒有,fixture 已補 | pass |

## 二、修前對照(STEP 5)

母體 22 格,兩面都是 QA 照驗收原句自己判的,不是從實作反推:該綠 11 格、該紅 11 格。

- 修後 22/0,不合 0。
- 差額 3 筆,**全部是「修前綠 → 修後紅」**:`pkg/__main__.py`(#68)、`r10_syntax_error.py`
  (#66)、`r11_cp950_source.py`(#66 的 decode 那半 —— 修前不是判綠,是**整支掛掉**)。
- 「修前紅 → 修後綠」**0 筆**,本輪沒有放掉任何東西。
- 另一節:母體整包放進 `.hidden_root/` 底下 —— 修後 11 紅(跟放在一般目錄一樣),
  修前 **0 紅**。

## 三、第二把尺(STEP 6)

受測物自己就是判準,只跑它綠只證明它同意自己。`98-wide.py` 從頭寫一遍「哪些 `.py` 該
受檢、哪些讀不進來」,而且刻意寫寬:`rglob("*.py")` 一格都不過濾、`__main__` 用純文字
regex 認任何寫法、不 import 受測物的任何 helper。

對 repo 本體:寬尺母體 28、受測物受檢範圍 28(差 0)、受測物判紅 0,**差額 7 筆**。
逐筆判讀:

| 差額 | 寬尺 | 受測物 | 判讀 |
| --- | --- | --- | --- |
| `60-mention-sweep.py`、`83-deferred-sweep.py`、`84-generator-sweep.py`、`86-async-sweep.py`、`96-newrule-probe.py`、`validate.py` | 紅 | 綠 | **誤報,設計如此**。寬尺拿原始碼字串判「碰 stdin」,這六個檔的 `sys.stdin` 全是散文或規則表裡的字面值 —— AST 上的 `sys.stdin` attribute 實測 **0 個**。受測物看 AST,正是 #96 AC3 要的行為。 |
| `97-wide.py` | 紅 | 綠 | **誤報,設計如此**。寬尺的 `^\s*if .*__main__.*:$` 把第 43 行的 `if "__main__" not in src:` 也認成 main block,那個假 block 當然沒有第一層 pin。真正的 main 在第 75 行,stdin/stdout 都釘了。 |

repo 本體剛好一格都沒被過濾掉,量不到 #68 那條軸,所以另外對一份**真的有被過濾檔**的
母體再跑一次(STEP 6b):寬尺母體 33、受測物受檢範圍 30(差 3)、受測物判紅 1。多出來的
3 筆差額是 `.venv/zz.py`、`scripts/.hidden.py`、`scripts/__pycache__/zz.py` —— 受測物
按設計過濾掉沒看,寬尺一格都不過濾所以判紅。`pkg/__main__.py` 兩把尺都判紅,同意。

## 四、mutation 台與它的控制組(STEP 7)

| 跑法 | 控制組(不套 knob) | 整張表 |
| --- | --- | --- |
| `97-mutate.py --run`(只複製 `validate.py`) | **exit 1** —— `AssertionError: no skill carries a 「下一步:… `/x`」 baton` | 15/15「咬住」(無意義) |
| 完整 repo 副本 | exit 0 | **15/15 真的咬住** |

儀器壞在哪:`self_check()` 第 466 行要讀 `REPO / "skills"` 才有 baton 可咬,而副本裡只有
`scripts/validate.py`。stream 那組 fixture 住在第 913 行 —— 從來沒被執行過。`#101` 那輪
改的註解(「整張表全靠 inline fixture 咬住」)講的是一件沒發生的事。

好消息:換成完整副本之後 15 個 knob 一個不漏全被咬住,判準本身是有測試釘著的。壞消息:
repo 裡那個會被人相信的數字,量的是別的東西。

## 五、開出來的票

### blocking(修完才能 demo)

- **#102 —— mutation 台是壞掉的儀器,控制組不套 knob 就已經紅。**
  `97-mutate.py --run` 的副本裡只有 `scripts/validate.py`,`self_check()` 第 466 行讀不到
  `skills/` 就 `AssertionError`,第 913 行那些 stream fixture 從來沒被執行過。整張表不管
  改成什麼都印「咬住」。這是 #98 票面 AC 自己的驗收證據,所以是 blocking。
  修法方向:副本改成完整 repo 副本 + 加一格控制組(`98-mutate-control.py` 可直接併進去)。

## 六、known issues(帶著走,處置由 client 在 demo 收尾整批確認)

- **#103 —— 過濾吃相對路徑這件事沒被釘住。** 本輪順手把 `is_source` 從吃絕對路徑改成吃
  相對路徑,收掉「repo 被 clone 到 `.` 開頭路徑底下整條守門靜靜全綠」這個缺口(修前 0 紅
  vs 修後 11 紅)。但 `is_source(rel)` 改回 `is_source(py)`,完整副本的 self-check 照樣
  **exit 0,沒咬住** —— tmpdir 路徑裡剛好沒有 `.` 或 `__` 開頭的那一段。行為是對的,缺的
  是釘住它的測試。
- **#104 —— 第二把尺自己會被 cp950 檔掀掉,而且沒有東西守著它的判準。**
  `96-newrule-probe.py` 只接 `SyntaxError`,遇到 cp950 存的 `.py` 是整支 traceback,
  跟 `validate.py` 在 #66 的 decode 那半上不同意;而且它沒有 self-check,`all` 被改回
  `any` 沒人會知道 —— 這輪抓到純粹是因為有人手動去讀了它。

## 七、未涵蓋範圍

- **沒有 UI**,這是一條 CLI 守門規則,walkthrough 是逐條跑指令、貼指令與輸出,沒有
  Playwright / a11y snapshot 這一段。demo 實錄 = 那份 xtrace 本身。
- **repo 本體現在一個 `__main__.py` 都沒有**(28 個 `.py` 掃過),#68 那條軸在 repo 本體上
  量不到,全靠 fixture 與另一份母體釘住。哪天 repo 真的長出 package entry point,行為由
  `self_check()` 的 inline fixture 保證,不是靠這輪的實跑。
- **judge 另外點名的證據缺口**(不影響判定,但別當它已驗):完整副本那塊
  `main_body_only` 的失敗訊息字面只有 `pass`,咬到什麼沒有可讀的歸因,跟其他 14 格不同級。

## 八、demo 實錄與一鍵重開

**一鍵重開 QA 環境**(client-demo 直接抄,不用改):

```bash
bash scripts/qa/98-walkthrough.sh "$(mktemp -d)/qa98"
```

這支不碰 repo 本體 —— 每個情境都跑在拋棄式暫存目錄的 repo 副本上,跑完 `rm -rf` 就乾淨。

**每條驗收項對一段實錄**(行號指的是本文件最後一節的完整 xtrace):

| 驗收原句 | demo 實錄 | 段落 |
| --- | --- | --- |
| 一個檔有幾個 `__main__` 就檢查幾個 | STEP 2(2a / 2b / 2c / 2d / 2d2) | 「兩個 `__main__`,只釘第一個 → 吵」起 |
| 檔案 parse 不動要判 fail | STEP 3(3a / 3b / 3c) | 「一支打錯字的 `.py` → 吵」起 |
| `__main__.py` 不得被過濾誤傷 | STEP 4(4a / 4b / 4c) | 「package entry point 沒 pin → 吵」起 |
| (票面 AC)mutation 台 | STEP 7(7a / 7b) | 「repo 進 repo 的那份」與控制組 |

## 九、本輪新增的 QA artifact(不是產品改動)

| 檔 | 幹嘛的 |
| --- | --- |
| `scripts/qa/98-walkthrough.sh` | 一鍵重開的 QA 環境 + 三條覆蓋驗收項逐格實跑,每格附反面對照組 |
| `scripts/qa/98-prevdiff.py` | 修前對照,兩面母體 22 格,修前 `91b6b98` vs 修後,外加「母體放在 `.` 開頭目錄底下」那一節 |
| `scripts/qa/98-wide.py` | 第二把尺 —— 刻意寫寬、一格都不過濾、不 import 受測物 helper 的入口掃描 |
| `scripts/qa/98-mutate-control.py` | mutation 台的基準線控制組 —— #102 就是它抓出來的 |

## 獨立 judge

乾淨 subagent,只餵三條驗收原句 + 票面 AC 4 + 那份 xtrace,不餵實作脈絡、不餵本 session
的任何判斷,明講「不要去讀實作原始碼替它找理由」。逐條判 pass / fail / works-but-wrong。

> **驗收原句 1 —— 「一個檔有幾個 `__main__` 就要檢查幾個」 → pass**
>
> 三格對照成套,而且方向不同,能把「每個都檢查」跟「只看第一個 / 只看最後一個」分開:
> 2a 只釘第一個 → 紅;2b 只釘**第二個** → 一樣紅(這格是關鍵,沒它 2a 分不出是不是
> 「只看最後一個」);2c 兩個都釘 → 綠。第二把尺同答案,而且修前那把是相反語意,差異被
> 實際量到:2d 修後 probe `不合 1`、2d2 修前 probe(91b6b98,any)`不合 0`。
>
> **驗收原句 2 —— 「檔案 parse 不動要判 fail,不是靜靜跳過」 → pass**
>
> 兩種讀不進來的形態各有一格,而且都是「判紅」不是「crash」。3b 打對字 → 綠(反面成立,
> 紅不是常態紅)。修前對照證明這兩格原本真的漏掉,而且 cp950 那格修前是「掀掉整支」
> 不是判決。
>
> **驗收原句 3 —— 「`__main__.py` 不得被 `__` 開頭的過濾誤傷」 → pass**
>
> 4c 過濾沒被拆爛(這格才讓 4a 不是「乾脆不過濾」)。第二把尺量到過濾邊界剛好是那三格、
> 沒多吃。另外還多量了一條「repo 被 clone 到別的路徑」的形狀。
>
> **票面 AC 4 —— 「knob 改壞要轉紅,mutation 台進 repo」 → fail(works-but-wrong)**
>
> 進 repo 的那台在「什麼都沒改壞」的狀態下就已經是紅的。這直接把 7a 那張表作廢:判準是
> 「exit=1 就算咬住」,但 baseline 已經 exit=1 —— 所以那 15 個 `exit=1` 沒有一個能歸因到
> knob。「15/15 咬住」在這裡等於「15/15 都是同一個 baseline 失敗」,量的是儀器自己壞掉,
> 不是 fixture 的敏感度。
>
> 唯一有效的那次量測是控制組腳本自己另起的第二塊(完整 repo 副本,baseline 綠),那塊的
> 錯誤訊息各不相同,的確是真的咬到。但那塊跑的是**臨時完整副本**,不是票面要求的
> 「mutation 台進 repo」。功能會動,但不是驗收原句說的那件事。
>
> **總判定:fail**(驗收原句 1/2/3 三條 pass,票面 AC 4 fail)

judge 另外點名三處證據缺口,已收進第七節「未涵蓋範圍」。

## 交棒

blocking 一條(#102)。修完重跑 `/qa #98`。

- `/build #102`(Codex: `$build #102`)
- known issues #103 / #104 帶著走,處置在 client-demo 收尾整批確認。

## 完整 xtrace(指令與輸出同一份)

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
+ echo '==== STEP 2  覆蓋驗收項 1:一個檔有幾個 __main__ 就檢查幾個(#69)===='
==== STEP 2  覆蓋驗收項 1:一個檔有幾個 __main__ 就檢查幾個(#69)====
+ echo '---- 2a  兩個 __main__,只釘第一個 → 吵'
---- 2a  兩個 __main__,只釘第一個 → 吵
+ fresh
+ rm -rf C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cp -r C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/pristine C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cat
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/qa/zz-case-two-mains.py
import sys
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("一")
if __name__ == "__main__":
    print("二")
+ gate
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/validate.py
FAIL scripts/qa/zz-case-two-mains.py: runnable script does not pin stdout to UTF-8 at the first level of its `if __name__ == "__main__"` block — its 中文 output is mojibake on a cp950 console (#58)
+ echo 'exit 1'
exit 1
+ set -e
+ echo '---- 2b  對照組:同一份 fixture 改成只釘**第二個** → 一樣吵'
---- 2b  對照組:同一份 fixture 改成只釘**第二個** → 一樣吵
+ echo '         沒有這格,2a 的紅分不出是「每個都檢查」還是「只看最後一個」'
         沒有這格,2a 的紅分不出是「每個都檢查」還是「只看最後一個」
+ fresh
+ rm -rf C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cp -r C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/pristine C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cat
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/qa/zz-case-two-mains-second.py
import sys
if __name__ == "__main__":
    print("一")
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("二")
+ gate
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/validate.py
FAIL scripts/qa/zz-case-two-mains-second.py: runnable script does not pin stdout to UTF-8 at the first level of its `if __name__ == "__main__"` block — its 中文 output is mojibake on a cp950 console (#58)
+ echo 'exit 1'
exit 1
+ set -e
+ echo '---- 2c  兩個都釘 → 綠(2a/2b 的反面)'
---- 2c  兩個都釘 → 綠(2a/2b 的反面)
+ fresh
+ rm -rf C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cp -r C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/pristine C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cat
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/qa/zz-case-two-mains-ok.py
import sys
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("一")
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("二")
+ gate
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/validate.py
OK validate green
+ echo 'exit 0'
exit 0
+ set -e
+ echo '---- 2d  第二把尺(96-newrule-probe)對同一格要給**一樣**的答案'
---- 2d  第二把尺(96-newrule-probe)對同一格要給**一樣**的答案
+ echo '         #69 這條的實體就是兩把尺原本相反:validate 是 all、probe 是 any'
         #69 這條的實體就是兩把尺原本相反:validate 是 all、probe 是 any
+ fresh
+ rm -rf C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cp -r C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/pristine C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cat
+ probe
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/96-newrule-probe.py' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
scripts/qa/zz-case-two-mains.py: 缺 stdout pin

不合 1
+ set -e
+ echo '---- 2d2  同一格拿修前的 probe(91b6b98,寫的是 any)跑 —— 應該放行'
---- 2d2  同一格拿修前的 probe(91b6b98,寫的是 any)跑 —— 應該放行
+ git -C '/d/Self Project/Skills' show 91b6b98:scripts/qa/96-newrule-probe.py
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/probe_old.py C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
OK 新規則下全綠

不合 0
+ set -e
+ echo '==== STEP 3  覆蓋驗收項 2:檔案 parse 不動要判 fail(#66)===='
==== STEP 3  覆蓋驗收項 2:檔案 parse 不動要判 fail(#66)====
+ echo '---- 3a  一支打錯字的 .py → 吵,訊息要帶檔名 + 原因'
---- 3a  一支打錯字的 .py → 吵,訊息要帶檔名 + 原因
+ fresh
+ rm -rf C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cp -r C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/pristine C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ printf 'def f(\n'
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/qa/zz-case-typo.py
def f(
+ gate
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/validate.py
FAIL scripts/qa/zz-case-typo.py: cannot be read as Python source — '(' was never closed (<unknown>, line 1); a file this guard cannot read counts as a fail, not a skip (#66)
+ echo 'exit 1'
exit 1
+ set -e
+ echo '---- 3b  同一格把字打對 → 綠(3a 的反面)'
---- 3b  同一格把字打對 → 綠(3a 的反面)
+ fresh
+ rm -rf C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cp -r C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/pristine C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ printf 'def f():\n    return 1\n'
+ gate
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/validate.py
OK validate green
+ echo 'exit 0'
exit 0
+ set -e
+ echo '---- 3c  一支 cp950 存的 .py → 判紅,不是整支 traceback 掀掉'
---- 3c  一支 cp950 存的 .py → 判紅,不是整支 traceback 掀掉
+ fresh
+ rm -rf C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cp -r C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/pristine C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ python - C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/qa/zz-case-cp950.py
+ gate
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/validate.py
FAIL scripts/qa/zz-case-cp950.py: cannot be read as Python source — 'utf-8' codec can't decode byte 0xad in position 5: invalid start byte; a file this guard cannot read counts as a fail, not a skip (#66)
+ echo 'exit 1'
exit 1
+ set -e
+ echo '==== STEP 4  覆蓋驗收項 3:__main__.py 不被 __ 開頭的過濾誤傷(#68)===='
==== STEP 4  覆蓋驗收項 3:__main__.py 不被 __ 開頭的過濾誤傷(#68)====
+ echo '---- 4a  package entry point 沒 pin → 吵'
---- 4a  package entry point 沒 pin → 吵
+ fresh
+ rm -rf C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cp -r C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/pristine C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ mkdir -p C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/pkg
+ cat
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/pkg/__main__.py
import sys
if __name__ == "__main__":
    print("要開")
+ gate
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/validate.py
FAIL scripts/pkg/__main__.py: runnable script does not pin stdout to UTF-8 at the first level of its `if __name__ == "__main__"` block — its 中文 output is mojibake on a cp950 console (#58)
+ echo 'exit 1'
exit 1
+ set -e
+ echo '---- 4b  補上 pin → 綠(4a 的反面)'
---- 4b  補上 pin → 綠(4a 的反面)
+ fresh
+ rm -rf C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cp -r C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/pristine C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ mkdir -p C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/pkg
+ cat
+ gate
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/validate.py
OK validate green
+ echo 'exit 0'
exit 0
+ set -e
+ echo '---- 4c  過濾還是擋得住它本來要擋的:__pycache__ / .venv / .hidden.py 三格都沒 pin → 仍綠'
---- 4c  過濾還是擋得住它本來要擋的:__pycache__ / .venv / .hidden.py 三格都沒 pin → 仍綠
+ fresh
+ rm -rf C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cp -r C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/pristine C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ mkdir -p C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/__pycache__ C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/.venv
+ for f in "$QA/case/scripts/__pycache__/zz.py" "$QA/case/.venv/zz.py" "$QA/case/scripts/.hidden.py"
+ printf 'import sys\nif __name__ == "__main__":\n    print("x")\n'
+ for f in "$QA/case/scripts/__pycache__/zz.py" "$QA/case/.venv/zz.py" "$QA/case/scripts/.hidden.py"
+ printf 'import sys\nif __name__ == "__main__":\n    print("x")\n'
+ for f in "$QA/case/scripts/__pycache__/zz.py" "$QA/case/.venv/zz.py" "$QA/case/scripts/.hidden.py"
+ printf 'import sys\nif __name__ == "__main__":\n    print("x")\n'
+ gate
+ set +e
+ python C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/validate.py
OK validate green
+ echo 'exit 0'
exit 0
+ set -e
+ echo '==== STEP 5  修前對照:同一份母體 22 格,修前(91b6b98)vs 修後 ===='
==== STEP 5  修前對照:同一份母體 22 格,修前(91b6b98)vs 修後 ====
+ python '/d/Self Project/Skills/scripts/qa/98-prevdiff.py'
母體 22 格,修前 = 91b6b98

修前:整支掛掉 —— UnicodeDecodeError: 'utf-8' codec can't decode byte 0xad in position 5: invalid start byte
      (這本身就是 #66 的一半:沒接 UnicodeDecodeError 的話,一支 cp950 存的
       .py 不是判紅,是把整條守門 traceback 掀掉。crash 不是判決。)
      拿掉 cp950 那格重跑修前 —— 其餘 21 格才有逐格答案

fixture                           QA 期望    修後    修前     判定
.g11_hidden.py                    綠        綠     綠      OK
.venv/g10_vendored.py             綠        綠     綠      OK
__pycache__/g09_cached.py         綠        綠     綠      OK
g01_pin_first_level.py            綠        綠     綠      OK
g02_stdin_both_pinned.py          綠        綠     綠      OK
g03_no_main.py                    綠        綠     綠      OK
g04_stdin_only_prose.py           綠        綠     綠      OK
g05_reversed_spelling.py          綠        綠     綠      OK
g06_main_nested_under_try.py      綠        綠     綠      OK
g07_two_mains_both_pinned.py      綠        綠     綠      OK
g08_in_tuple_spelling.py          綠        綠     綠      OK
pkg/__main__.py                   紅        紅     綠      OK  差額 修前綠→修後紅
r01_pin_inside_main_func.py       紅        紅     紅      OK
r02_pin_module_level.py           紅        紅     紅      OK
r03_pin_nested_in_if.py           紅        紅     紅      OK
r04_buffer_only_no_pin.py         紅        紅     紅      OK
r05_main_no_print.py              紅        紅     紅      OK
r06_stdin_only_stdout_pinned.py   紅        紅     紅      OK
r07_two_mains_first_only.py       紅        紅     紅      OK
r08_pin_nested_in_try.py          紅        紅     紅      OK
r10_syntax_error.py               紅        紅     綠      OK  差額 修前綠→修後紅
r11_cp950_source.py               紅        紅     掛掉     OK  差額 修前掛掉→修後紅

差額 3 筆:
  pkg/__main__.py: 修前綠 → 修後紅
  r10_syntax_error.py: 修前綠 → 修後紅
  r11_cp950_source.py: 修前掛掉 → 修後紅
  (每一筆都要對得上票面三條;出現「修前紅 → 修後綠」就是本輪放掉了東西)

---- 母體整包放在 `.hidden_root/` 底下(repo 被 clone 到 ~/.local/… 的形狀)----
  修後:11 紅(過濾吃相對路徑,不受影響)
  修前:0 紅(過濾吃絕對路徑 —— 整條守門靜靜全綠)
  修後兩處答案一致:True

母體 22,不合 0
+ echo '==== STEP 6  第二把尺:刻意寫寬、不套受測規則的入口掃描 ===='
==== STEP 6  第二把尺:刻意寫寬、不套受測規則的入口掃描 ====
+ echo '---- 6a  對 repo 本體'
---- 6a  對 repo 本體
+ python '/d/Self Project/Skills/scripts/qa/98-wide.py' '/d/Self Project/Skills'
==== 寬尺看到的全部 .py ====
   scripts/batch.py:main 行 [205];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/hooks/triage-to-maintain.py:main 行 [49];第一層 pin [['stdin', 'stdout']](原始碼提到 sys.stdin:True)
   scripts/install.py:main 行 [249];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/57-guard-sweep.py:main 行 [118];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/60-mention-sweep.py:main 行 [188, 195, 204, 213, 229, 238, 248, 257, 266, 276, 322];第一層 pin [[], [], [], [], [], [], [], [], [], [], ['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/65-nesting-sweep.py:main 行 [162];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/73-reach-sweep.py:main 行 [74];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/75-binding-sweep.py:main 行 [120];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/79-return-sweep.py:main 行 [107];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/81-lambda-sweep.py:main 行 [65];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/83-deferred-sweep.py:main 行 [12, 72];第一層 pin [[], ['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/84-generator-sweep.py:main 行 [13, 78];第一層 pin [[], ['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/86-async-sweep.py:main 行 [10, 159];第一層 pin [[], ['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/86-mutate.py:main 行 [80];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/87-drive-sweep.py:main 行 [162];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/87-mutate.py:main 行 [58];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/87-oracle.py:main 行 [79];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/87-prevdiff.py:main 行 [56];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/91-graph-sweep.py:main 行 [164];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/91-mutate.py:main 行 [67];第一層 pin [['stdout']](原始碼提到 sys.stdin:False)
   scripts/qa/96-newrule-probe.py:main 行 [74];第一層 pin [['stdout']](原始碼提到 sys.stdin:True)
   scripts/qa/97-mutate.py:main 行 [147];第一層 pin [['stdin', 'stdout']](原始碼提到 sys.stdin:True)
   scripts/qa/97-prevdiff.py:main 行 [83];第一層 pin [['stdin', 'stdout']](原始碼提到 sys.stdin:True)
   scripts/qa/97-wide.py:main 行 [43, 75];第一層 pin [[], ['stdin', 'stdout']](原始碼提到 sys.stdin:True)
   scripts/qa/98-mutate-control.py:main 行 [94];第一層 pin [['stdin', 'stdout']](原始碼提到 sys.stdin:True)
   scripts/qa/98-prevdiff.py:main 行 [148];第一層 pin [['stdin', 'stdout']](原始碼提到 sys.stdin:True)
   scripts/qa/98-wide.py:main 行 [81];第一層 pin [['stdin', 'stdout']](原始碼提到 sys.stdin:True)
   scripts/validate.py:main 行 [965];第一層 pin [['stdout']](原始碼提到 sys.stdin:True)
   skills/build-batch/batch.py:main 行 [1334];第一層 pin [['stdin', 'stdout']](原始碼提到 sys.stdin:True)

寬尺母體 29 個 .py;受測物的受檢範圍 29 個(差 0 個被過濾掉);受測物判紅 0 個

==== 差額(寬尺 vs 受測物)—— 每一筆要人判讀 ====
  scripts/qa/60-mention-sweep.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  scripts/qa/83-deferred-sweep.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  scripts/qa/84-generator-sweep.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  scripts/qa/86-async-sweep.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  scripts/qa/96-newrule-probe.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  scripts/qa/97-wide.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  scripts/validate.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  差額 7 筆
+ echo '---- 6b  對一份真的有被過濾檔的母體(repo 本體剛好一格都沒過濾掉,量不到 #68 那條軸)'
---- 6b  對一份真的有被過濾檔的母體(repo 本體剛好一格都沒過濾掉,量不到 #68 那條軸)
+ fresh
+ rm -rf C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ cp -r C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/pristine C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ mkdir -p C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/__pycache__ C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/.venv C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case/scripts/pkg
+ for f in "$QA/case/scripts/__pycache__/zz.py" "$QA/case/.venv/zz.py" "$QA/case/scripts/.hidden.py"
+ printf 'import sys\nif __name__ == "__main__":\n    print("x")\n'
+ for f in "$QA/case/scripts/__pycache__/zz.py" "$QA/case/.venv/zz.py" "$QA/case/scripts/.hidden.py"
+ printf 'import sys\nif __name__ == "__main__":\n    print("x")\n'
+ for f in "$QA/case/scripts/__pycache__/zz.py" "$QA/case/.venv/zz.py" "$QA/case/scripts/.hidden.py"
+ printf 'import sys\nif __name__ == "__main__":\n    print("x")\n'
+ printf 'import sys\nif __name__ == "__main__":\n    print("x")\n'
+ python '/d/Self Project/Skills/scripts/qa/98-wide.py' C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/f5ff948a-b126-415d-9312-db0aee0db695/scratchpad/qa98/case
+ tail -20
   scripts/qa/98-mutate-control.py:main 行 [94];第一層 pin [['stdin', 'stdout']](原始碼提到 sys.stdin:True)
   scripts/qa/98-prevdiff.py:main 行 [148];第一層 pin [['stdin', 'stdout']](原始碼提到 sys.stdin:True)
   scripts/qa/98-wide.py:main 行 [81];第一層 pin [['stdin', 'stdout']](原始碼提到 sys.stdin:True)
   scripts/validate.py:main 行 [965];第一層 pin [['stdout']](原始碼提到 sys.stdin:True)
   skills/build-batch/batch.py:main 行 [1334];第一層 pin [['stdin', 'stdout']](原始碼提到 sys.stdin:True)

寬尺母體 33 個 .py;受測物的受檢範圍 30 個(差 3 個被過濾掉);受測物判紅 1 個

==== 差額(寬尺 vs 受測物)—— 每一筆要人判讀 ====
  .venv/zz.py:寬尺判紅,受測物判綠 —— 受測物過濾掉沒看
  scripts/.hidden.py:寬尺判紅,受測物判綠 —— 受測物過濾掉沒看
  scripts/__pycache__/zz.py:寬尺判紅,受測物判綠 —— 受測物過濾掉沒看
  scripts/qa/60-mention-sweep.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  scripts/qa/83-deferred-sweep.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  scripts/qa/84-generator-sweep.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  scripts/qa/86-async-sweep.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  scripts/qa/96-newrule-probe.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  scripts/qa/97-wide.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  scripts/validate.py:寬尺判紅,受測物判綠 —— 同一批檔、判準有差
  差額 10 筆
+ echo '==== STEP 7  mutation 台:15 個 knob + 基準線控制組 ===='
==== STEP 7  mutation 台:15 個 knob + 基準線控制組 ====
+ echo '---- 7a  repo 進 repo 的那份'
---- 7a  repo 進 repo 的那份
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/97-mutate.py' --run
咬住  buffer_exempt          self-check exit=1
咬住  decode_error_uncaught  self-check exit=1
咬住  filter_off             self-check exit=1
咬住  first_main_only        self-check exit=1
咬住  guard_off              self-check exit=1
咬住  main_body_only         self-check exit=1
咬住  no_norm                self-check exit=1
咬住  pin_anywhere_in_file   self-check exit=1
咬住  pin_anywhere_in_main   self-check exit=1
咬住  print_exempt           self-check exit=1
咬住  stdin_always           self-check exit=1
咬住  stdin_by_text          self-check exit=1
咬住  stdin_never            self-check exit=1
咬住  underscore_filter      self-check exit=1
咬住  unreadable_skip        self-check exit=1

15/15 個 knob 被 self-check 咬住
+ echo 'exit 0'
exit 0
+ set -e
+ echo '---- 7b  控制組:同一個 harness,knob 一個都不套 —— 應該 exit 0'
---- 7b  控制組:同一個 harness,knob 一個都不套 —— 應該 exit 0
+ set +e
+ python '/d/Self Project/Skills/scripts/qa/98-mutate-control.py'
==== 控制組:97-mutate.py 現在的副本,knob 一個都不套 ====
  exit=1  AssertionError: no skill carries a �u�U�@�B:�K `/x`�v baton �X mutation has nothing to bite
  判定:*** 控制組就已經紅 —— 整張表怎樣都印咬住,一格都沒在量 ***

==== 完整 repo 副本:同一張表重跑一次 ====
  控制組(不套 knob)exit=0  
  咬住  buffer_exempt          exit=1  AssertionError: ('writes bytes, no pin', [])
  咬住  decode_error_uncaught  exit=1  UnicodeDecodeError: 'utf-8' codec can't decode byte 0xad in position 5: invalid start byte
  咬住  filter_off             exit=1  AssertionError
  咬住  first_main_only        exit=1  AssertionError
  咬住  guard_off              exit=1  AssertionError: ('no pin at all', [])
  咬住  main_body_only         exit=1      pass
  咬住  no_norm                exit=1  AssertionError
  咬住  pin_anywhere_in_file   exit=1  AssertionError: ('pin lives in main()', [])
  咬住  pin_anywhere_in_main   exit=1  AssertionError: ('pin nested under an `if`', [])
  咬住  print_exempt           exit=1  AssertionError: ('pin lives at module level', [])
  咬住  stdin_always           exit=1  AssertionError
  咬住  stdin_by_text          exit=1  AssertionError
  咬住  stdin_never            exit=1  AssertionError
  咬住  underscore_filter      exit=1  AssertionError: []
  咬住  unreadable_skip        exit=1  AssertionError: []

  15/15 個 knob 被 self-check 咬住

總結:控制組紅(儀器壞了)、完整副本 15/15
+ echo 'exit 1'
exit 1
+ set -e
+ echo '==== STEP 8  票上其餘 AC:原型 probe 對 repo 本體全綠 ===='
==== STEP 8  票上其餘 AC:原型 probe 對 repo 本體全綠 ====
+ python '/d/Self Project/Skills/scripts/qa/96-newrule-probe.py' '/d/Self Project/Skills'
OK 新規則下全綠

不合 0
+ set +x

==== walkthrough 走完 ====
```
