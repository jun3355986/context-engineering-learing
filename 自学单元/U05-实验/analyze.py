#!/usr/bin/env python3
"""U05 分析：读 out/ 下各次实验的请求，打印第 6 章用到的数字。

用法：python3 -I analyze.py        （在本目录下运行，读 ./out/）
"""
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"


def load(name, n):
    return json.loads((OUT / name / f"req-{n}.json").read_text())


def summary(name):
    return json.loads((OUT / name / "summary.json").read_text())


def jb(x):
    return len(json.dumps(x, ensure_ascii=False).encode())


def last_n(name):
    return summary(name)[-1]["n"]


def strip_ids(x):
    s = json.dumps(x, ensure_ascii=False, sort_keys=True)
    s = re.sub(r"\b(msg|at|fc|ctc|tso|rs)_[0-9a-f-]{8,}", "ID", s)
    s = re.sub(r"/tmp/u05-\w+", "TMP", s)
    return s


print("== 一、请求里有没有 MCP 工具（取每次实验的最后一次请求）")
rows = [
    ("gpt-6.1-sol 无 MCP", "e1b-gpt61-0tools"),
    ("gpt-6.1-sol 3 个服务器 30 个工具", "e1-gpt61-30tools"),
    ("gpt-5.5 无 MCP", "e2-gpt55-0tools"),
    ("gpt-5.5 3 个服务器 30 个工具", "e2-gpt55-30tools"),
    ("模型表里没有的名字 无 MCP", "e10-unknown-none"),
    ("模型表里没有的名字 30 个工具", "e10-unknown-three"),
    ("模型表里没有的名字 bulk 40 个", "e10-unknown-bulk40"),
]
# 口径同第 2 章：顶层 tools 字段和每条 input 条目各自 json.dumps 的字节数相加（比线上实际请求体略大，因为多了空格）
for label, name in rows:
    first = load(name, 1)
    tools_b = jb(first["tools"]) if first.get("tools") else 0
    inp_b = sum(jb(i) for i in first["input"])
    add = sum(jb(i) for i in first["input"] if i["type"] == "additional_tools")
    print(f"{label:<34} 合计 {tools_b + inp_b:>7,} 字节 = 顶层 tools {tools_b:>7,} + input {inp_b:>7,}（其中 additional_tools {add:>7,}）")

a = load("e1b-gpt61-0tools", 1)
b = load("e1-gpt61-30tools", 1)
same_tools = a["input"][0]["tools"] == b["input"][0]["tools"]
same_rest = all(strip_ids(x) == strip_ids(y) for x, y in zip(a["input"][1:], b["input"][1:]))
print(f"gpt-6.1-sol 第一次请求：additional_tools 逐字相同 = {same_tools}；其余 input 条目（去掉 id、临时目录名）相同 = {same_rest}")

print("\n== gpt-5.5 的差别（顶层 tools 逐个比较）")
ta = {t.get("name") or t.get("type"): t for t in load("e2-gpt55-0tools", 1)["tools"]}
tb = {t.get("name") or t.get("type"): t for t in load("e2-gpt55-30tools", 1)["tools"]}
tot = 0
for k, v in tb.items():
    d = jb(v) - (jb(ta[k]) if k in ta else 0)
    if d:
        print(f"  {k}: +{d}")
        tot += d
print(f"  合计 +{tot}")

print("\n== 二、直连时一个工具占多少（模型表里没有的名字）")
def ns_bytes(name, ns):
    r = load(name, last_n(name))
    return sum(jb(t) for t in r["tools"] if t.get("name") == ns)
res = {"list_mcp_resources", "list_mcp_resource_templates", "read_mcp_resource"}
def res_bytes(name):
    r = load(name, last_n(name))
    return sum(jb(t) for t in r["tools"] if t.get("name") in res)
for label, name, ns, n in [("tracker 10 个", "e14-unknown-tracker-all10", "mcp__tracker", 10),
                           ("tracker 只开 2 个（enabled_tools）", "e14-unknown-tracker-enabled2", "mcp__tracker", 2)]:
    b_ = ns_bytes(name, ns)
    print(f"  {label}: 命名空间 {b_:,} 字节，平均 {b_/n:,.0f} 字节/个；另有 3 个资源工具 {res_bytes(name):,} 字节")
three = sum(ns_bytes("e10-unknown-three", f"mcp__{s}") for s in ("tracker", "database", "monitor"))
print(f"  三个服务器 30 个: {three:,} 字节，平均 {three/30:,.0f} 字节/个")
bulk = ns_bytes("e10-unknown-bulk40", "mcp__bulk")
print(f"  凑数服务器 40 个: {bulk:,} 字节，平均 {bulk/40:,.0f} 字节/个")
base = summary("e10-unknown-none")[-1]["top_tools_bytes"]
for name in ("e10-unknown-three", "e10-unknown-bulk40"):
    print(f"  {name}: 顶层 tools 比无 MCP 多 {summary(name)[-1]['top_tools_bytes'] - base:,} 字节")

print("\n== 三、搜索（gpt-5.5，30 个工具）")
def outputs(name):
    r = load(name, last_n(name))
    qs, res_ = [], []
    for it in r["input"]:
        if it["type"] == "tool_search_call":
            qs.append(it["arguments"])
        if it["type"] == "tool_search_output":
            names = [ns["name"].replace("mcp__", "") + "." + t["name"] for ns in it["tools"] for t in ns.get("tools", [])]
            res_.append((qs[-1], jb(it), names))
    return res_
for name in ("e4-gpt55-8queries", "e8-gpt55-chinese-query", "e15-gpt55-limit"):
    for q, b_, names in outputs(name):
        print(f"  {json.dumps(q, ensure_ascii=False):<58}{b_:>6,} 字节 {len(names)} 个 {names}")

print("\n== 四、没搜过 / 写错名字 / 关掉的工具")
for name in ("e6-gpt55-call-without-search", "e7-gpt55-call-wrong-name", "e12-gpt61-disabled-tool-called"):
    s = summary(name)
    print(" ", name)
    for it in s[-1]["items"]:
        if it["type"] in ("function_call", "function_call_output") or (it["type"] == "message" and it.get("role") == "developer" and "no longer" in it.get("head", "")):
            print("    ", it["type"], it["bytes"], (it.get("call") or it.get("output") or it.get("head") or "")[:150].replace("\n", " "))

print("\n== 五、gpt-6.1-sol 的 exec 里查工具（e9、e13）")
r = load("e9-gpt61-exec-allt", last_n("e9-gpt61-exec-allt"))
for it in r["input"]:
    if it["type"] == "custom_tool_call_output":
        print("   输出条目", jb(it), "字节")
r = load("e13-gpt61-all-names", last_n("e13-gpt61-all-names"))
for it in r["input"]:
    if it["type"] == "custom_tool_call_output":
        print("   ", [p["text"][:200] for p in it["output"]][1:])
