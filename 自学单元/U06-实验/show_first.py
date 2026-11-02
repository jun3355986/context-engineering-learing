#!/usr/bin/env python3
"""U06：汇总若干次运行的第一次请求（父会话）的组成。用法：python3 -I show_first.py <out 目录> <运行名>…"""
import json
import sys

O = sys.argv[1]
for d in sys.argv[2:]:
    try:
        s = json.load(open(f"{O}/{d}/summary.json"))
        q = json.load(open(f"{O}/{d}/req-1.json"))
    except Exception as e:
        print(d, "无结果", e)
        continue
    r = s[0]
    items = sum(len(json.dumps(x, ensure_ascii=False).encode()) for x in q["input"])
    top = len(json.dumps(q.get("tools", []), ensure_ascii=False).encode())
    print(f"{d:28s} {r['model']:12s} 合计={items + top:>7,} input={len(q['input'])}条 顶层tools={top:,}")
    for it in r["items"]:
        h = it.get("head", "")
        tag = ""
        if "multi_agent_role" in h:
            tag = "【角色说明】"
        elif "multi_agent_mode" in h:
            tag = "【开关说明】"
        if tag or it.get("tools"):
            print("      ", it["i"], f"{it['bytes']:,}", tag, it.get("tools") or h[:70])
    if r["top_tools"]:
        print("       顶层tools:", r["top_tools"])
