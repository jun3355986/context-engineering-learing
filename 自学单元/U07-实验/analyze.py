#!/usr/bin/env python3
"""U07 分析：列出每次请求 input 的条目（角色/类型、字节、开头文字），并比较相邻请求的相同前缀。
用法：python3 -I analyze.py <out 目录>
"""
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
files = sorted(d.glob("req-*.json"))


def text_of(it):
    c = it.get("content")
    if isinstance(c, list):
        return "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return c if isinstance(c, str) else ""


def nb(o):
    return len(json.dumps(o, ensure_ascii=False).encode())


reqs = []
for f in files:
    r = json.loads(f.read_text())
    reqs.append((f.stem, r))
    print(f"=== {f.stem}  input {len(r['input'])} 条，合计 {sum(nb(i) for i in r['input']):,} 字节，prompt_cache_key={r.get('prompt_cache_key')}")
    for i, it in enumerate(r["input"]):
        t = text_of(it).replace("\n", "⏎")
        tag = it.get("role") or it.get("type")
        print(f"  [{i}] {tag:10s} {nb(it):>7,}  {t[:70]}")
print()
for (a, ra), (b, rb) in zip(reqs, reqs[1:]):
    ia, ib = ra["input"], rb["input"]
    n = 0
    while n < min(len(ia), len(ib)) and ia[n] == ib[n]:
        n += 1
    same_bytes = sum(nb(x) for x in ia[:n])
    print(f"{a} → {b}: 前 {n} 条逐字相同（{same_bytes:,} 字节）；上一次 {len(ia)} 条，这一次 {len(ib)} 条")
