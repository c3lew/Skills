# 技術決策紀律

技術決策怎麼拍、怎麼記、怎麼報、拍錯怎麼修。pm-intake、implement 收尾、maintain、/improve-codebase-architecture 結案儀式都引用本檔。

## 拍板 guardrail(依據型判準)

自動拍板前問一題:**「這個決策對不對,取決於我腦袋外面的事實嗎?」**

- 依據是**會過時的外部事實**(套件 API、版本相容、價格、rate limit、平台限制)→ 強制先查再拍。查證丟 `/research` subagent 跑(context smart-zone 對策),結論寫進決策紀錄;同主題不重查。
- 依據是**純設計取捨**(檔案結構、命名、內部架構)→ 直接拍。

不採主觀信心判準 — LLM 對過時知識常常很有自信。

### 查證的完工定義:實跑輸出

「查過了」不等於「讀過文件」。依據型查證要以**實跑輸出**結案:在乾淨環境跑一次,把
指令與輸出貼進決策紀錄,結論引用那段輸出、不引用文件的句子。

上游文件描述的行為與實況不一致時,文件不會報錯 — 錯的那句會原封不動流進 spec 與驗收
清單,接下來每一輪 QA 都拿它當 oracle,於是全綠。查證階段少跑的那一次,會在三輪之後
以「驗收清單本身寫錯」的形式炸出來。

跑不了(要付費帳號、要外部硬體、平台當下拿不到)就在決策紀錄寫明**沒實跑、依據是哪份
文件的哪一段**,並把它標成已知風險 — 不留「看起來查過了」的假綠。

## 紀錄分工

- **正本**:spec 的 Implementation Decisions 段,只留現況、不留歷史(focused context 原則)。
- **決策投影**:拍板當下同步發 GitHub issue comment — append-only、天生帶時間戳,dashboard 的「最近幫你做的決定」只讀這裡。
- **ADR**:夠格的決策(難逆 + 沒 context 會奇怪 + 真取捨,domain-modeling 三條件)另存 `docs/adr/`,house style:敘事體 + Considered options + Consequences。跟 grilling/wayfinder 產的 ADR 同一批,不另立系統。

## 白話三行制

每則自動拍板決策對 client 的回報格式,固定三行:

1. **做了什麼選擇**
2. **對你的影響**
3. **反悔成本**(之後想改是小事還是大工程)

技術名詞進括號當註腳。「沒影響」象限的決策不進回報清單、只留紀錄。反悔成本欄讓 client 把注意力花在難逆的決策上。

## 修正回路

- **收斂回合被否決** → 當場改拍重報。
- **事後發現拍錯**(「不對」四分類的「技術拍板錯」)→ 不回 pm-intake(client 沒被問過這題):重拍(這次過查證 guardrail、或升格成問 client 的題)→ 更新紀錄 → QA loop 驗。
- **更正紀錄**:spec 正本改寫成現況;tracker 發更正 comment,固定帶一行**「當初為什麼拍錯」**(未來 solo retro 的餵食口);ADR 更正沿 house style **原檔追加 Amendment 段**,不開 superseded 新檔。
