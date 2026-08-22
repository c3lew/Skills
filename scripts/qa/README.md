# QA sweeps

`scripts/qa/*-sweep.py` 現有 12 支。它們與同一時期的 walkthrough / mutation 腳本量的是
舊判準「那行 bypass 到底跑不跑得到」。#96 把判準換成固定約定(pin 要在 `__main__`
第一層,沒有豁免),所以這批**留著當 #60–#95 這條線的歷史紀錄,不列入目前的 regression**。

這 12 支仍跑得起來；部分會印出整片 `MISMATCH`，因為 fixture 的期望值釘的是舊判準，
不是目前 repo 壞掉。要驗現行規則，跑下面列出的工具。

還在用的(數量會長,別在這裡記總數 —— 記了就會過期):

- `96-newrule-probe.py` —— 新規則的原型,`python scripts/qa/96-newrule-probe.py .`
  應該跟 `validate.py` 對同一份 repo 給一樣的答案。
- `97-mutate.py` —— 新判準的 mutation 台,`python scripts/qa/97-mutate.py --run`
  要整張表全部咬住(exit 0)。
- `107-mutate.py` —— 並行池與 judge 排序約束的 mutation 台,
  `python scripts/qa/107-mutate.py --run` 要整張表全部咬住(exit 0)。
- `107-walkthrough.sh` —— #107 過關固化進 regression 的那支:
  `bash scripts/qa/107-walkthrough.sh "$(mktemp -d)/qa107"`,exit 0 = 全格符合預期。
  它跟 `107-mutate.py` 咬的不是同一件事 —— mutation 台問「守門會不會紅」,
  這支問「出貨的 `skills/qa/SKILL.md` 現在這份,下一個 agent 照著讀會不會做對」:
  每條 AC 一段可重跑的 transcript(指令 + 真實輸出 + 引用到的散文行號),
  外加對真檔改壞的六格。散文被改到不再寫出三線並行或 judge 排序,這支就紅。
- `87-oracle.py` —— 不讀守門規則、真的把檔案跑起來的獨立尺。新規則不需要它當判準,
  但下次再有「這東西自己就是尺」的票,它是現成的第二把尺。
- `113-wide.py` —— 散文那面的第二把尺,`python scripts/qa/113-wide.py .`。
  `validate.py` 明說它不驗散文,所以 stale `§N`、指錯節的 `§N`、無界全稱詞、
  delta 記帳這四種問題在 repo 裡沒有機械判準。這支刻意寫寬,撈出來的多餘項要
  逐筆判讀,不列入 regression(它的輸出不是綠/紅,是一份等人看的清單)。
