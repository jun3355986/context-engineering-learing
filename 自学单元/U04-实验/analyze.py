"""比较相邻两次请求：input 前多少条完全相同、序列化后前多少字节相同、其余字段有没有变。
用法：python3 -I analyze.py <目录> [<文件A> <文件B> ...]"""
import json, sys
from pathlib import Path

def load(p): return json.loads(Path(p).read_text())

def item_label(it):
    t = it.get("type"); r = it.get("role", "")
    c = it.get("content")
    txt = ""
    if isinstance(c, list):
        txt = "".join(x.get("text", "") for x in c if isinstance(x, dict))
    elif "output" in it: txt = str(it["output"])
    elif "input" in it: txt = str(it["input"])
    return f"{t}/{r} {len(json.dumps(it, ensure_ascii=False).encode())}B {txt[:60]!r}"

def compare(a, b, name):
    A, B = a["input"], b["input"]
    k = 0
    while k < min(len(A), len(B)) and A[k] == B[k]:
        k += 1
    sa = json.dumps(A, ensure_ascii=False).encode(); sb = json.dumps(B, ensure_ascii=False).encode()
    j = 0
    while j < min(len(sa), len(sb)) and sa[j] == sb[j]:
        j += 1
    other = [f for f in sorted(set(a) | set(b)) if f not in ("input", "client_metadata") and a.get(f) != b.get(f)]
    print(f"== {name}: A {len(A)} 条 {len(sa)}B -> B {len(B)} 条 {len(sb)}B；前 {k} 条相同；序列化前 {j}B 相同；其他字段变化 {other}")
    for i in range(k, len(B)):
        print(f"   B[{i}] {item_label(B[i])}")
    if k < len(A):
        print(f"   A 从第 {k} 条起不同：A[{k}] {item_label(A[k])}")

d = Path(sys.argv[1])
files = sys.argv[2:] or sorted(p.name for p in d.glob("req-*.json"))
reqs = [(f, load(d / f)) for f in files]
reqs = [(f, r) for f, r in reqs if r.get("input")]
for (fa, a), (fb, b) in zip(reqs, reqs[1:]):
    compare(a, b, f"{fa} -> {fb}")
