# QA sweeps

`56-` 到 `95-` 這批(15 支 sweep、222 格 fixture)量的是舊判準「那行 bypass 到底跑不跑
得到」。#96 拍板把判準換成約定(pin 要在 `__main__` 第一層,沒有豁免),那個判斷不存在
了,所以這批**留著當 #60–#95 這條線的紀錄,不再跑** —— 它們 import 的
`live_nodes` / `asyncio_graph` 那些 function 已經從 `validate.py` 刪掉,直接跑會炸。

還在用的三支:

- `96-newrule-probe.py` —— 新規則的原型,`python scripts/qa/96-newrule-probe.py .`
  應該跟 `validate.py` 對同一份 repo 給一樣的答案。
- `97-mutate.py` —— 新判準的 mutation 台,`python scripts/qa/97-mutate.py --run`
  要整張表全部咬住(exit 0)。
- `87-oracle.py` —— 不讀守門規則、真的把檔案跑起來的獨立尺。新規則不需要它當判準,
  但下次再有「這東西自己就是尺」的票,它是現成的第二把尺。
