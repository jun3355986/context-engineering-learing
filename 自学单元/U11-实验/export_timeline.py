#!/usr/bin/env python3
"""把每组的逐请求 token 序列导出成一个 JSON，给第 12 章页面里的交互用。
用法：python3 -I export_timeline.py <out 目录>   → <out 目录>/timeline.json
每组：t = 各请求的估算 token；c = 压缩请求的下标；n = 新线程开始的下标（第一个请求不算）。"""
import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
res = {}
for arm in ["A", "B", "C", "F", "D", "G", "E"]:
    d = json.loads((out / arm / "requests.json").read_text())
    t = [r["est_tokens"] for r in d]
    c = [i for i, r in enumerate(d) if r["kind"] == "compact"]
    seen, n = set(), []
    for i, r in enumerate(d):
        if r["thread"] not in seen:
            if seen:
                n.append(i)
            seen.add(r["thread"])
    res[arm] = {"t": t, "c": c, "n": n}
(out / "timeline.json").write_text(json.dumps(res, separators=(",", ":")))
print(json.dumps(res, separators=(",", ":")))
