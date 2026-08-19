"""#60 同型全掃 — 「提到」的每一種寫法 vs 「用到」的每一種寫法。

#60 的病是「豁免用全檔 substring 比對」,所以一條 fail 不是一條 fail:整份
STREAM_PINS 的兩個目標字串(bypass 與 pin)乘上散文能出現的每個位置(comment、
docstring、字串常數、f-string、變數名)都是同一形狀。這支把母體一次列完,
表格化跑出來當證據,而不是只重跑票上撞到的那一條。

用法:
    python scripts/qa/60-mention-sweep.py <repo>              # 提到 vs 用到 全表
    python scripts/qa/60-mention-sweep.py <repo> --positional # 位置判準(#58 原病)
    python scripts/qa/60-mention-sweep.py <repo> --skips      # 守門靜默跳過的路
    python scripts/qa/60-mention-sweep.py <repo> --bypass-position  # 豁免的位置判準
    python scripts/qa/60-mention-sweep.py <repo> --pin-position     # pin 的位置判準
    python scripts/qa/60-mention-sweep.py <repo> --callgraph        # call graph 的解析度
    python scripts/qa/60-mention-sweep.py <repo> --print-detect     # 沒-print 豁免的判準解析度
    python scripts/qa/60-mention-sweep.py <repo> --live-overapprox  # 可達性 over-approximate 的代價
    python scripts/qa/60-mention-sweep.py <repo> --name-collision   # 同名 def 塌成一個節點
    python scripts/qa/60-mention-sweep.py <repo> --return-carry     # 回傳的名字一律算 live
    ... --old                                                 # 對照組:#60 修之前那版(d3cc9ed^)
    ... --prev                                                # 對照組:上一輪 QA 的 HEAD(188c7d8)
    ... --prev73                                              # 對照組:#73 修之前(e56789c)
    ... --prev75                                              # 對照組:#75 修之前(39003a3)
"""
import subprocess
import sys
import tempfile
from pathlib import Path

RUNNABLE = 'import sys\nif __name__ == "__main__":\n    '
NAKED = RUNNABLE + 'print("要開的票")\n'
BYPASS = "sys.stdout.buffer"
PIN = 'sys.stdout.reconfigure(encoding="utf-8")'

# (情境, 原始碼, 期望) — 期望 "RED" = 守門要出聲,"GREEN" = 不得誤紅
MENTION = [
    ("對照:裸 print,什麼都沒有", NAKED, "RED"),
    ("提到 bypass — 行內 comment", NAKED + f"    # 這裡沒走 {BYPASS}\n", "RED"),
    ("提到 bypass — 檔頭 comment", f"# 說明:{BYPASS} 不適用\n" + NAKED, "RED"),
    ("提到 bypass — module docstring", f'"""{BYPASS} 的說明,不是呼叫"""\n' + NAKED, "RED"),
    ("提到 bypass — 字串常數", f'x = "{BYPASS}"\n' + NAKED, "RED"),
    ("提到 bypass — f-string", f'x = f"用 {{1}} 的 {BYPASS}"\n' + NAKED, "RED"),
    ("提到 bypass — 變數名近似", NAKED + "    sys_stdout_buffer = 1\n", "RED"),
    ("提到 pin — 行內 comment", NAKED + f"    # 記得補 {PIN}\n", "RED"),
    ("提到 pin — docstring", f'"""要記得 {PIN}"""\n' + NAKED, "RED"),
    ("提到 pin — 字串常數", "x = " + repr(PIN) + "\n" + NAKED, "RED"),
    ("用到 bypass — 真的 write", RUNNABLE + f'{BYPASS}.write(b"x")\n', "GREEN"),
    ("用到 pin — 雙引號", RUNNABLE + f'{PIN}\n    print(1)\n', "GREEN"),
    ("用到 pin — 單引號(unparse 正規化)",
     RUNNABLE + "sys.stdout.reconfigure(encoding='utf-8')\n    print(1)\n", "GREEN"),
]

# #58 的原病:pin 只要文字上在 __main__ 之後就算數。位置判準要擋住這些。
POSITIONAL = [
    ("pin 在 main(),__main__ 只呼叫它",
     f'import sys\ndef main():\n    {PIN}\n    print("要開的票")\n\n\nif __name__ == "__main__":\n    main()\n', "RED"),
    ("pin 在 __main__ 之前的 top-level",
     f'import sys\n{PIN}\nif __name__ == "__main__":\n    print("要開的票")\n', "RED"),
    ("pin 真的在 __main__ block 裡", RUNNABLE + f'{PIN}\n    print("要開的票")\n', "GREEN"),
    ("pin 在 __main__ block 裡的 try 底下",
     f'import sys\nif __name__ == "__main__":\n    try:\n        {PIN}\n    except Exception:\n        pass\n    print("要開的票")\n', "GREEN"),
]


# 這一輪 QA 抓到的第三型:守門連看都不看這個檔。AST 化之後多了兩條靜默跳過的路,
# 母體 = 2,兩條都會讓一支裸 print 的 script 無聲過關(#60 要防的正是無聲繞過)。
SKIPS = [
    ("__main__ 縮排在 try 底下 -> 找不到 top-level If,整檔跳過",
     'import sys\ntry:\n    if __name__ == "__main__":\n        print("要開的票")\nexcept Exception:\n    pass\n', "RED"),
    ("__main__ 縮排在 if True 底下 -> 同上",
     'import sys\nif True:\n    if __name__ == "__main__":\n        print("要開的票")\n', "RED"),
    ("檔案 parse 不過(SyntaxError)-> 整檔跳過(build 已在 code 裡註明的取捨)",
     'if __name__ == "__main__":\n    print("要開的票"\n', "RED"),
]


# 第四型(#65 修完重跑這輪抓到):豁免現在**認得出散文**了,但仍然是「檔案裡任何地方
# 出現一次真的 attribute access,整支檔案就豁免」。AC1 原句要的是「真的在**會執行的
# 位置**用 sys.stdout.buffer.write」— 死碼、沒人呼叫的 function 都不是會執行的位置。
# 這是 #60 那條病的下一層(判準從「文字任何地方」變成「AST 任何地方」),不是 regression:
# 改之前的 substring 版同樣全綠。
BYPASS_POSITION = [
    ("bypass 在從未被呼叫的 function 內",
     'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\nif __name__ == "__main__":\n    print("要開的票")\n', "RED"),
    ("bypass 在 `if False:` 死碼裡",
     'import sys\nif False:\n    sys.stdout.buffer.write(b"x")\nif __name__ == "__main__":\n    print("要開的票")\n', "RED"),
    ("bypass 只出現在跑不到的 except 分支",
     'import sys\ntry:\n    pass\nexcept Exception:\n    sys.stdout.buffer.write(b"x")\nif __name__ == "__main__":\n    print("要開的票")\n', "RED"),
    ("bypass 在 `raise SystemExit` 之後的死碼",
     'import sys\nif __name__ == "__main__":\n    print("要開的票")\n    raise SystemExit\n    sys.stdout.buffer.write(b"x")\n', "RED"),
    ("bypass 真的在 __main__ 裡用(不得誤紅)",
     'import sys\nif __name__ == "__main__":\n    sys.stdout.buffer.write("要開的票".encode())\n', "GREEN"),
    ("bypass 在 main(),__main__ 呼叫它(triage-to-maintain 的形狀,不得誤紅)",
     'import sys\ndef main():\n    sys.stdout.buffer.write(b"x")\nif __name__ == "__main__":\n    main()\n', "GREEN"),
]


# 第五型(#70 修完重跑這輪抓到):#70 把可達性判準裝上去了,但只裝在 bypass 那半 ——
# pin 那半仍是 `code_exprs(main)`,__main__ block 裡**任何地方**出現一次 reconfigure
# 就算 pin 到了,不管那行跑不跑得到。死碼裡的 pin 跟死碼裡的 bypass 是同一形狀:
# 一個誰都能翻的開關,守門閉嘴而 console 上一個字元都沒被 pin 到。
PIN_POSITION = [
    ("pin 在 __main__ 內的 `if False:` 死碼裡",
     f'import sys\nif __name__ == "__main__":\n    if False:\n        {PIN}\n    print("要開的票")\n', "RED"),
    ("pin 在 __main__ 內 `raise SystemExit` 之後的死碼",
     f'import sys\nif __name__ == "__main__":\n    print("要開的票")\n    raise SystemExit\n    {PIN}\n', "RED"),
    ("pin 在 __main__ 內定義但沒人呼叫的 nested def",
     f'import sys\nif __name__ == "__main__":\n    def never():\n        {PIN}\n    print("要開的票")\n', "RED"),
    ("pin 只出現在跑不到的 except 分支",
     f'import sys\nif __name__ == "__main__":\n    try:\n        pass\n    except Exception:\n        {PIN}\n    print("要開的票")\n', "RED"),
    ("pin 真的在 __main__ block 裡(不得誤紅)",
     RUNNABLE + f'{PIN}\n    print("要開的票")\n', "GREEN"),
    ("pin 在 block 內的 try body 裡(不得誤紅)",
     f'import sys\nif __name__ == "__main__":\n    try:\n        {PIN}\n    except Exception:\n        pass\n    print("要開的票")\n', "GREEN"),
]


# 第六型:call graph 的解析度。#70 的版本是 name-only,只認 `f()` 這種呼叫,
# 於是 alias / handler dict / callback 走到的 bypass 一律誤紅 —— 而 `live_exprs`
# 的 docstring 逐字寫的是相反的話。#71 改成「名字被提到就算走得到」,這張表就是拿
# 那句散文的字面重新推導(written-evidence)。每條都留一個真的 print,不然 #71(b)
# 的「沒 print 就豁免」會讓它們用另一個理由變綠,測不到 call graph。
CALLGRAPH = [
    ("bypass 在 handler dict 裡被呼叫的 function(docstring 說仍算 live)",
     'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\nH = {"a": dump}\nif __name__ == "__main__":\n    H["a"]()\n    print("要開的票")\n', "GREEN"),
    ("bypass 在 alias 呼叫的 function(docstring 說仍算 live)",
     'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\nf = dump\nif __name__ == "__main__":\n    f()\n    print("要開的票")\n', "GREEN"),
    ("bypass 當 callback 傳進去被呼叫(docstring 說仍算 live)",
     'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\ndef run(cb):\n    cb()\nif __name__ == "__main__":\n    run(dump)\n    print("要開的票")\n', "GREEN"),
    ("bypass 在 class method,__main__ 直接呼叫(對照:.attr 名字對得上)",
     'import sys\nclass W:\n    def go(self):\n        sys.stdout.buffer.write(b"x")\nif __name__ == "__main__":\n    W().go()\n    print("要開的票")\n', "GREEN"),
]


# 第七型(#71 修完重跑這輪抓到):#71 補上 AC1 的第二支路「檔案裡沒有裸 print(」,
# 判準是 AST 上 `Call.func.id == "print"`。名字對得上才算 —— 於是每一種「印到 console
# 但不寫 print(」的形狀都變成豁免:守門對一支印滿中文的 script 一聲不吭。這是 #60
# 那條病的形狀(一個誰都能翻的開關),只是開關從註解換成 `p = print`。
PRINT_DETECT = [
    ("print 用 alias 呼叫(p = print; p(中文))",
     'import sys\np = print\nif __name__ == "__main__":\n    p("要開的票")\n', "RED"),
    ("print 走 builtins(builtins.print(中文))",
     'import sys\nimport builtins\nif __name__ == "__main__":\n    builtins.print("要開的票")\n', "RED"),
    ("print 當 callback 傳進去(run(print))",
     'import sys\ndef run(cb):\n    cb("要開的票")\nif __name__ == "__main__":\n    run(print)\n', "RED"),
    ("print 放在 handler dict 裡(H = {p: print}; H[p](中文))",
     'import sys\nH = {"p": print}\nif __name__ == "__main__":\n    H["p"]("要開的票")\n', "RED"),
    ("sys.stdout.write(中文)(build 已宣告的天花板)",
     'import sys\nif __name__ == "__main__":\n    sys.stdout.write("要開的票")\n', "RED"),
    ("對照:真的裸 print(,沒 pin(不得漏放)", NAKED, "RED"),
    ("對照:真的完全不印 console(不得誤紅)",
     'import sys\nimport pathlib\nif __name__ == "__main__":\n    pathlib.Path("o.txt").write_text("要開的票", encoding="utf-8")\n', "GREEN"),
]


# 第八型(同上):#71(a) 把可達性從「呼叫」放寬成「名字被提到」,刻意 over-approximate。
# 代價是 #70 立的天花板一行就能還原 —— 死碼裡的 bypass 配上 live 區任何一個同名的
# Name/Attribute(連撞名的區域變數、無關物件的 attribute 都算),整支檔案就豁免。
# 對照組是 --bypass-position 的第一條(名字沒被提到),它仍須 RED。
LIVE_OVERAPPROX = [
    ("死碼裡的 bypass + live 區提到名字(不是呼叫)",
     'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\nif __name__ == "__main__":\n    x = [dump]\n    print("要開的票")\n', "RED"),
    ("死碼裡的 bypass + 剛好撞名的區域變數",
     'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\nif __name__ == "__main__":\n    dump = 1\n    print("要開的票")\n', "RED"),
    ("死碼裡的 bypass + 無關物件的同名 attribute",
     'import sys\nclass C:\n    pass\ndef dump():\n    sys.stdout.buffer.write(b"x")\nif __name__ == "__main__":\n    c = C()\n    c.dump\n    print("要開的票")\n', "RED"),
    ("對照:死碼裡的 bypass,名字沒被提到(#70 的天花板)",
     'import sys\ndef dump():\n    sys.stdout.buffer.write(b"x")\nif __name__ == "__main__":\n    print("要開的票")\n', "RED"),
    ("對照:bypass 在真的被呼叫的 main()(不得誤紅)",
     'import sys\ndef main():\n    sys.stdout.buffer.write(b"x")\nif __name__ == "__main__":\n    main()\n', "GREEN"),
]


# 第九型(#73 / #75 修完重跑這輪抓到):同一把尺 —— 「live 集合有哪些放寬不是真的呼叫」。
# #76 已經拿這把尺量過「名字交給任何 call 當引數」那一格。`live_nodes` 的 docstring 自己
# 列了三個 approximation,另外兩格從沒被量過,量下去兩格都在漏。
# 第一格:`defs` 是一個 `{name: node}` 平表,同名的兩個 def 塌成一個節點 —— 於是
# 「檔案裡任何地方有一個同名的 def 被呼叫」就把死碼裡那個同名 def 拉成 live。加一個撞名的
# function 就是一個誰都能翻的開關,跟 #60 原病同型(#73 收掉的是撞名的**變數 / attribute**,
# 撞名的 **def** 沒收)。
NAME_COLLISION = [
    ("死碼 bypass 在沒被實例化的 class method,module 同名 def 被呼叫", """import sys
def dump():
    pass
class W:
    def dump(self):
        sys.stdout.buffer.write(b"x")
if __name__ == "__main__":
    dump()
    print("要開的票")
""", "RED"),
    ("死碼 bypass 在後面重新定義的同名 def,被呼叫的是前面那個", """import sys
def dump():
    pass
if __name__ == "__main__":
    dump()
    print("要開的票")
def dump():
    sys.stdout.buffer.write(b"x")
""", "RED"),
    ("對照:死碼 bypass 的 def 沒有同名雙胞胎(#70 的天花板)", """import sys
def dump():
    sys.stdout.buffer.write(b"x")
if __name__ == "__main__":
    print("要開的票")
""", "RED"),
    ("對照:同名 def 但被呼叫的就是帶 bypass 的那個(不得誤紅)", """import sys
class W:
    def dump(self):
        pass
def dump():
    sys.stdout.buffer.write(b"x")
if __name__ == "__main__":
    dump()
    print("要開的票")
""", "GREEN"),
]


# 第十型(同一把尺的第三格):live 的 def `return` 出去的名字一律算 live,不管那個回傳值
# 有沒有被呼叫 —— 連 def 內部撞名的區域變數都算。`def get(): return dump` 加一行 `get()`
# (結果直接丟掉)就整檔豁免,又是一個一行能翻的開關。
RETURN_CARRY = [
    ("死碼 bypass + `def get(): return dump`,`get()` 結果直接丟掉", """import sys
def dump():
    sys.stdout.buffer.write(b"x")
def get():
    return dump
if __name__ == "__main__":
    get()
    print("要開的票")
""", "RED"),
    ("同上,回傳值存進變數但從未呼叫(`x = get()`)", """import sys
def dump():
    sys.stdout.buffer.write(b"x")
def get():
    return dump
if __name__ == "__main__":
    x = get()
    print("要開的票")
""", "RED"),
    ("get() 回傳的是自己的區域變數,只是剛好撞名死碼 def", """import sys
def dump():
    sys.stdout.buffer.write(b"x")
def get():
    dump = 1
    return dump
if __name__ == "__main__":
    get()
    print("要開的票")
""", "RED"),
    ("對照:回傳值真的被呼叫 `get()()`(#75 立的天花板,不得誤紅)", """import sys
def dump():
    sys.stdout.buffer.write(b"x")
def get():
    return dump
if __name__ == "__main__":
    get()()
    print("要開的票")
""", "GREEN"),
    ("對照:`get` 自己也沒被呼叫(死碼,必須維持 RED)", """import sys
def dump():
    sys.stdout.buffer.write(b"x")
def get():
    return dump
if __name__ == "__main__":
    print("要開的票")
""", "RED"),
]


# 對照組能指的歷史點:#60 動手前(--old),與上一輪 QA 的 HEAD(--prev,#71 修之前)。
BASELINES = {"--old": "d3cc9ed^", "--prev": "188c7d8", "--prev73": "e56789c",
             "--prev75": "39003a3"}


def guard_module(repo, old):
    """`stream_encoding_issues` 的來源:現況,或某個歷史對照點。"""
    if not old:
        sys.path.insert(0, str(Path(repo) / "scripts"))
        import validate

        return validate
    src = subprocess.run(["git", "-C", str(repo), "show", f"{old}:scripts/validate.py"],
                         capture_output=True, check=True).stdout
    box = Path(tempfile.mkdtemp())
    name = "validate_" + old.replace("^", "p")
    (box / f"{name}.py").write_bytes(src)
    sys.path.insert(0, str(box))
    return __import__(name)


def run(repo, cases, old=False):
    V = guard_module(repo, old)

    tmp = Path(tempfile.mkdtemp())
    probe = tmp / "probe.py"
    rows, bad = [], 0
    for name, src, want in cases:
        probe.write_text(src, encoding="utf-8")
        got = "RED" if V.stream_encoding_issues(tmp) else "GREEN"
        ok = got == want
        bad += not ok
        rows.append((name, want, got, "ok" if ok else "MISMATCH"))
    width = max(len(r[0]) for r in rows)
    for name, want, got, verdict in rows:
        print(f"{name.ljust(width)}  期望 {want:<5}  實際 {got:<5}  {verdict}")
    print(f"\n母體 {len(rows)},不合 {bad}")
    return bad


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cases = MENTION
    if "--positional" in sys.argv:
        cases = POSITIONAL
    elif "--skips" in sys.argv:
        cases = SKIPS
    elif "--bypass-position" in sys.argv:
        cases = BYPASS_POSITION
    elif "--pin-position" in sys.argv:
        cases = PIN_POSITION
    elif "--callgraph" in sys.argv:
        cases = CALLGRAPH
    elif "--print-detect" in sys.argv:
        cases = PRINT_DETECT
    elif "--live-overapprox" in sys.argv:
        cases = LIVE_OVERAPPROX
    elif "--name-collision" in sys.argv:
        cases = NAME_COLLISION
    elif "--return-carry" in sys.argv:
        cases = RETURN_CARRY
    base = next((BASELINES[f] for f in BASELINES if f in sys.argv), None)
    sys.exit(1 if run(sys.argv[1], cases, base) else 0)
