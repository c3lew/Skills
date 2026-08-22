# QA sweeps

`scripts/qa/*-sweep.py` 現有 12 支。它們與同一時期的 walkthrough / mutation 腳本量的是
舊判準「那行 bypass 到底跑不跑得到」。#96 把判準換成固定約定(pin 要在 `__main__`
第一層,沒有豁免),所以這批**留著當 #60–#95 這條線的歷史紀錄,不列入目前的 regression**。

這 12 支仍跑得起來；部分會印出整片 `MISMATCH`，因為 fixture 的期望值釘的是舊判準，
不是目前 repo 壞掉。要驗現行規則，跑下面列出的工具。

還在用的四支:

- `96-newrule-probe.py` —— 新規則的原型,`python scripts/qa/96-newrule-probe.py .`
  應該跟 `validate.py` 對同一份 repo 給一樣的答案。
- `97-mutate.py` —— 新判準的 mutation 台,`python scripts/qa/97-mutate.py --run`
  要整張表全部咬住(exit 0)。
- `107-mutate.py` —— 並行池與 judge 排序約束的 mutation 台,
  `python scripts/qa/107-mutate.py --run` 要整張表全部咬住(exit 0)。
- `87-oracle.py` —— 不讀守門規則、真的把檔案跑起來的獨立尺。新規則不需要它當判準,
  但下次再有「這東西自己就是尺」的票,它是現成的第二把尺。
