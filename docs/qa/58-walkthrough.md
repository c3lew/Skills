# QA walkthrough — #58 build-batch:名單三段標題在 Windows 主控台是壞碼(bug fix)

Bug fix ticket,範圍 = 該 bug 的重現 scenario + regression suite。

判定 oracle(票上「對應驗收原句」):

> 「有 4 張票、其中 3 張彼此不卡、1 張卡在別人後面 → 跑指令,名單**只列那 3 張**…」
> — 分段邏輯正確,但 client 讀不到那份名單,所以是 works-but-wrong。

也就是這輪要判的是同一條驗收原句,重點在「client 照文件跑,讀不讀得到那份名單」。

環境:`D:/Self Project/Skills`,HEAD = `5e9cbc5`,working tree 乾淨。
`python -c "import sys;print(sys.stdout.encoding)"` → `cp950`(跟開票時同一台、同一個 codepage)。
本票是 CLI + skill 文件,沒有 UI,不走 Playwright;本檔是終端實錄。

一鍵重開(沿用既有 CLI QA 入口):

```bash
cd "D:/Self Project/Skills"
python scripts/validate.py
python scripts/validate.py --self-check
python scripts/batch.py --self-check
python skills/build-batch/batch.py --self-check
python scripts/install.py --self-check
python scripts/hooks/triage-to-maintain.py --self-check
```

## 步驟 1 — regression suite

```text
$ python scripts/validate.py
OK validate green
exit 0

$ python scripts/validate.py --self-check
OK validate self-check green
exit 0

$ python scripts/batch.py --self-check
OK batch self-check green
exit 0

$ python skills/build-batch/batch.py --self-check
OK batch self-check green
exit 0

$ python scripts/install.py --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
exit 0

$ python scripts/hooks/triage-to-maintain.py --self-check
OK triage-to-maintain self-check green
exit 0
```

(`[fixture] FAIL` 是 install self-check 自己的 negative fixture,綠的一部分。)

同一組再用 `PYTHONIOENCODING=cp950` 跑一次,六條全綠、輸出一字不差。

既有 regression 全綠。

## 步驟 2 — 重現 scenario:照 SKILL.md §3 逐字跑

跟開票時同一份輸入(4 張票、3 張彼此不卡、#63 卡在 #60),title 裡故意留一個 Big5
沒有的字(`🔔`)咬「當場 UnicodeEncodeError」那條路。

```text
$ python skills/build-batch/batch.py <<'JSON'
{"tickets": [{"number": 60, "state": "open", "blocked_by": []},
             {"number": 61, "state": "open", "blocked_by": []},
             {"number": 62, "state": "open", "blocked_by": []},
             {"number": 63, "state": "open", "blocked_by": [60]}],
 "titles": {"60": "登入頁", "61": "設定頁", "62": "通知 🔔", "63": "登入後導向"}}
JSON
要開(3 張):
  #60 登入頁
  #61 設定頁
  #62 通知 🔔
排隊(0 張):
  (無)
還卡著(1 張):
  #63 登入後導向 — 卡在 #60
exit 0
```

沒有加任何 `PYTHONIOENCODING`,三段標題「要開 / 排隊 / 還卡著」、「張」、「(無)」、
「卡在」全部讀得出來,emoji 沒炸。分段本身也對:只列那 3 張,#63 在「還卡著」。

raw bytes 落地確認是 UTF-8,不是主控台猜的:

```text
b'\xe8\xa6\x81\xe9\x96\x8b(3 \xe5\xbc\xb5):\r\n  #60 \xe7\x99\xbb\xe5\x85\xa5\xe9\xa0\x81...'
   要      開                 張
```

`PYTHONIOENCODING=cp950` 強塞也一樣 — 輸出 bytes 與預設跑完全相同(`cmp` 無差異),
`__main__` 的 pin 蓋過環境變數。

## 步驟 3 — 對照組:同一份輸入跑修前的版本

`HEAD~1` 的 `batch.py` + 修前 SKILL.md §3 的 inline `python -c`:

```text
b'\xadn\xb6}(3 \xb1i):\r\n  #60 \xe7\x99\xbb\xe5\x85\xa5\xe9\xa0\x81...
  \xb1\xc6\xb6\xa4(0 \xb1i):\r\n  (\xb5L)\r\n\xc1\xd9\xa5d\xb5\xdb(1 \xb1i):...'
```

三段標題是 Big5 bytes(`\xadn\xb6}` = 「要開」的 Big5),就是票上那份壞碼;title 那段
反而是 UTF-8 bytes — 因為 stdin 沒釘,UTF-8 的中文被當 cp950 讀進來變成亂碼字元,
再原封不動編回去。兩個症狀在同一次跑裡同時看得到。修後全部消失。

## 步驟 4 — 真的用 cmd `chcp 950` 跑一次

不是只靠 `PYTHONIOENCODING`,直接把主控台 codepage 切到 950:

```text
> chcp
Active code page: 950
> type input.json | python skills\build-batch\batch.py
要開(3 張):
  #60 登入頁
  #61 設定頁
  #62 通知 🔔
排隊(0 張):
  (無)
還卡著(1 張):
  #63 登入後導向 — 卡在 #60
```

## 步驟 5 — 同型全掃的另外三處 + 守門

票上「同型全掃」表列的四處,現在全部釘住,且守門抓得到位置:

| 位置 | 驗法 | 結果 |
|---|---|---|
| `skills/build-batch/batch.py` | 步驟 2、4 實跑 | 綠 |
| `scripts/validate.py` | 步驟 5 的 negative probe(下面),訊息含中文 + em dash | 綠 |
| `scripts/install.py` | pin 在 `__main__`(L250),`stream_encoding_issues` 蓋到 | 綠 |
| `scripts/batch.py` | pin 在 `__main__`(L16),self-check 綠 | 綠 |
| `scripts/hooks/triage-to-maintain.py` | 走 `sys.stdout.buffer`,不受 codepage 影響 | 綠 |

守門的 negative probe — 丟一支沒釘 stdout 的 `scripts/_qa58_probe.py` 進去:

```text
$ python scripts/validate.py
FAIL scripts/_qa58_probe.py: runnable script does not pin stdout to UTF-8 inside its
`if __name__ == "__main__"` block — its 中文 output is mojibake on a cp950 console (#58)
exit 1
```

這行本身就是證據:validate 自己吐的中文 + em dash 在 cp950 下讀得出來(`PYTHONIOENCODING=cp950`
強塞跑,bytes 是 UTF-8:`\xe2\x80\x94` = `—`、`\xe4\xb8\xad\xe6\x96\x87` = 「中文」)。
把 pin 補回同一支 probe → validate 回綠,沒有 false positive。probe 已刪,working tree 乾淨。

## 未涵蓋

- **真主控台不重導向的畫面**:步驟 4 是 `chcp 950` 的 cmd,但輸出有落檔才拿得到 bytes。
  Python 對真 console handle 走 `WriteConsoleW`(不經 codepage),所以直接看畫面只會更好不會更壞;
  但這一條沒有機器證據,留給 client-demo 親眼確認。
- 本票沒碰 `/build-batch` 的其他驗收項(只有 1 張能跑、超過 3 張排隊)— 那些在 #52 已驗過,本輪未重跑 walkthrough。
