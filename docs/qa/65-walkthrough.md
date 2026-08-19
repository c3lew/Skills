# QA walkthrough — #65 stream_encoding_issues 找 `__main__` 從 `tree.body` 改成 `ast.walk`(bug fix)

Bug fix ticket,範圍 = 該 bug 的重現 scenario + regression suite。

判定 oracle(票上的重現 scenario 與完工定義原句):

> ```python
> # probe.py
> import sys
> try:
>     if __name__ == "__main__":
>         print("要開的票")
> except Exception:
>     pass
> ```
>
> `python scripts/validate.py` → 綠。期望紅(裸 print,沒 pin stdout)。
> `if True:` 底下同理。
>
> - [ ] `__main__` 縮排在 `try` / `if True` / 任何 block 底下,守門照樣抓
> - [ ] `scripts/qa/60-mention-sweep.py <repo> --skips` 前兩條變 ok
> - [ ] self-check 補上這兩條 mutation(住在預設就會跑的地方)
> - [ ] `python scripts/validate.py` 綠,全 repo 不得誤紅

外加 repo 自己的紀律 `references/written-evidence.md`〈Guard 的完工定義〉三條:住在預設就會跑的
地方、兩種 mutation 都咬得到、查不到目標時判 fail 不是靜靜略過。

交付物是 `scripts/validate.py` 的 guard,沒有 UI、沒有視覺 oracle,不走 Playwright、沒有錄影 —
實錄就是終端 transcript(全程 bash xtrace,指令與輸出在同一份,沒有事後 render)。mutation 全部
跑在拋棄式暫存目錄的副本或 `tempfile.mkdtemp()` 上,repo 本體沒被動過(STEP 8 的 `git status`
是證據)。

環境:`D:/Self Project/Skills`,branch `main`,HEAD = `f6c5245`。

一鍵重開(client-demo / 之後每輪 QA 直接抄):

```bash
bash scripts/qa/65-walkthrough.sh "$(mktemp -d)/qa65"
```

demo 實錄:沒有 UI 就沒有錄影,實錄 = 上面那個指令的終端輸出本身(xtrace,指令與輸出同一份)。
每條驗收項對應的段落見下表的 STEP 編號 —— 重跑一次就是完整重播,不用另外存檔。

## 步驟

| # | 驗的是 | 對應驗收原句 |
| --- | --- | --- |
| 1 | regression suite:`validate.py` + 五支 self-check | 完工定義第 4 條 / 既有 regression |
| 1b | **第 3 條的反證**:副本裡把 `ast.walk(tree)` 改回 `tree.body` → `--self-check` 轉紅,爆掉的 assert 印出來的就是「`__main__` 包在 `try` 底下的裸 print」那條 mutation。self-check 綠不是因為沒加 case,是因為 case 真的咬得到 | 完工定義第 3 條 |
| 2 | 拋棄式副本未動過 → 綠(證明後面判紅的是 probe,不是副本壞了) | — 對照 |
| 3 | 票上的重現 scenario **原樣重跑**:`__main__` 包在 `try` 底下的裸 print 丟進副本 → 判紅,error 指名 `scripts/_repro65.py` | 重現 scenario |
| 3b | 票上第二條:`if True:` 底下同理 → 判紅 | 重現 scenario |
| 4 | **同型全掃**:「包一層」不是只有 `try` 跟 `if True`。母體 = Python 裡能包住一個 statement 的每種 block(top-level 對照、try/except、try/finally、if True、if/else 的 else、with、for、while、包兩層、def、class)× 兩個方向(裸 print 要判紅 / 有 pin 不得誤紅)= 22 條 → 22/22 符合期望 | 完工定義第 1 條 |
| 4b | 對照組:同一份母體在 `3d402e9^`(#65 修之前)壞 10 條 —— 每一種包法的「裸 print」全部無聲過關。證明修掉的是一整族,不是票上撞到的那兩條 | 完工定義第 1 條 |
| 5 | 完工定義第 2 條:`60-mention-sweep --skips` 前兩條由 MISMATCH 變 `ok`(第三條 SyntaxError 是 #66,不在本票範圍) | 完工定義第 2 條 |
| 6 | 不得誤紅:#60 的「提到 vs 用到」全表 13/13、位置判準 4/4 都沒退步;#57 的 guard-sweep 兩個方向都還咬得到 | 完工定義第 4 條 |
| 7 | **本輪 finding**:一個檔裡有兩個 `__main__` block 時,守門的 `next()` 只看找到的第一個。誘餌(有 pin)排在真的那個前面 → 整支判綠。母體 5,壞 2 | 完工定義之外(見下) |
| 7b | 對照組:同樣 5 條在 `3d402e9^` 壞 3 條、在 `d3cc9ed^`(#60 之前的 substring 版)5 條全壞 → 這是舊天花板,#65 還修好了其中 1 條,不是這次的 regression | 完工定義之外 |
| 7c | **judge 追問的同型全掃**:守門認的是 `ast.unparse(n.test) == MAIN_TEST` 這個字面。`__main__` 判斷式換個等價寫法(左右對調 / `in` / 先存變數 / 否定+else)→ 那個 node 對不上,整檔一樣無聲略過。母體 6,壞 4;`--old` 壞同樣 4 條 | 完工定義之外 |
| 7d | **judge 追問的同型全掃**:擋 `__pycache__` 用的檔名過濾 `part.startswith(("." , "__"))` 掃的是 `py.parts`(含檔名)→ `__main__.py` 這個最典型的 entry point 永遠不受檢。母體 5,壞 2;`--old` 一樣壞 | 完工定義之外 |
| 8 | repo 本體 `validate.py` 全綠,`git status` 只多這輪的 QA artifact | 完工定義第 4 條 |

完工定義第 3 條不能只靠 STEP 1 的 `--self-check` 綠 —— 沒加 case 也會綠,綠這件事跟「有沒有那條
case」不相關,所以 STEP 1b 反著驗:把病還原,self-check 就必須紅。build 補的那兩條 mutation 住在
`self_check()` L822-833(`python scripts/validate.py --self-check` 預設就會跑),written-evidence
〈Guard 的完工定義〉第一條成立。

## 獨立 judge 判定

judge 是乾淨 subagent,只拿到上面的驗收原句 + transcript,沒有實作脈絡、沒讀 diff 也沒讀 git 歷史。

| 條目 | 判定 |
| --- | --- |
| 重現 scenario(`try` 底下的裸 print) | pass |
| 重現 scenario(`if True:` 底下同理) | pass |
| 完工定義 1 — 任何 block 底下照樣抓 | pass(母體 22 全中,對照組 `3d402e9^` 壞 10 條) |
| 完工定義 2 — `--skips` 前兩條變 ok | pass |
| 完工定義 3 — self-check 補上這兩條 mutation | pass(舉證方式正確;缺口見下) |
| 完工定義 4 — validate 綠、不得誤紅 | pass |

works-but-wrong:**無**。判紅的理由是「`__main__` block 內沒有 pin」本身,不是靠檔名或其他 proxy ——
STEP 4 的 22 條裡「有 pin」與「裸 print」只差 pin 那一行,結果就分綠紅。

judge 對舉證的兩點意見(採納,記在這裡):

- **STEP 1b 只證了兩條 mutation 裡的第一條。** sed 還原後 self-check 在第一個 `assert` 就炸,
  `if True` 那條根本沒跑到。judge 自己去讀 `validate.py` L822-833 確認兩個 wrapper 都在、
  各驗紅綠兩方向,但那是 judge 讀 source 確認的,不是 transcript 證的。要把證據做滿,
  STEP 1b 該對每條 case 各跑一次。**這是 QA 舉證的缺口,不是實作的缺口。**
- **STEP 1b 只做了「改壞」方向,沒做「繞過」方向。** 這輪補的 STEP 7c / 7d 就是照 judge 指的
  繞過方向去掃的,兩個方向都掃出東西(見 known issues)。

judge 判 STEP 7 / 7c / 7d 全部**本票範圍外**:三條的對照組都證明 `3d402e9^` 與 `d3cc9ed^`
壞得一樣或更多,不是這次引入的 regression;驗收原句四條講的都是「縮排 / 巢狀」,沒有一條
提到「多個 `__main__`」「判斷式寫法」「檔名過濾」。QA 採納,全列 known issue、各開一張票。


## Blocking

**0 條。**


## Known issues

這三條都是 **#58 就在的天花板**,不是 #65 引入的 —— 每一條都附了 `--old` 對照組。共同的
root cause 是同一句紀律沒真的做到:`references/written-evidence.md`〈Guard 的完工定義〉第三條
**「查不到目標時判 fail,不是靜靜略過」**。`stream_encoding_issues` 現在有三條無聲 `continue`
(SyntaxError、`main is None`、檔名過濾),#65 只放大了「找得到的範圍」,沒動這個病本身。

- **#67** `MAIN_TEST` 只認一種字面寫法,等價寫法整檔無聲略過(4 條)。票裡把 `main is None`
  不該 `continue` 一起寫進完工定義 —— 那是這一族的根。
- **#68** 擋 `__pycache__` 的檔名過濾誤傷 `__main__.py` / `__init__.py`,package entry point
  永遠不受檢(2 條)。repo 現況沒有這種檔,是盲點不是現行破口。
- **#69** 一個檔有多個 `__main__` 時,`next()` 只檢查第一個(2 條)。#65 反而把 5 條裡的
  1 條修好了(3 → 2)。
- **#66**(既有)檔案 SyntaxError → 整檔跳過。同一族的第四條,已在 #60 那輪開票。

judge 另外列了幾個「母體可以更完整」的格子(`elif` / `match` / `async def` / decorator /
`try-else` / 完全沒有 `__main__` 的 library 檔不得誤紅)。都不影響本票判 pass —— `ast.walk`
是無差別遞迴,不挑 node 種類 —— 屬證據完整度,沒開票。

