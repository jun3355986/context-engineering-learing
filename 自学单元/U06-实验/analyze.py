#!/usr/bin/env python3
"""U06：汇总各次运行的数字。用法：python3 -I analyze.py <out 目录>

口径（同第 2 章）：请求大小 = 每条 input 条目 json.dumps 字节数相加 + 顶层 tools 字段字节数；
token = 字节 ÷ 4 向上取整（Codex 本地估算，不是真实分词）。
"""
import json
import math
import sys
from pathlib import Path

O = Path(sys.argv[1])


def size(item):
    return len(json.dumps(item, ensure_ascii=False).encode())


def req_size(q):
    return sum(size(x) for x in q["input"]) + (size(q["tools"]) if q.get("tools") else 0)


def tok(b):
    return math.ceil(b / 4)


def load(d):
    s = json.load(open(O / d / "summary.json"))
    return [(r, json.load(open(O / d / f"req-{r['n']}.json"))) for r in s]


def common_prefix(a, b):
    n = byt = 0
    for x, y in zip(a["input"], b["input"]):
        if x != y:
            break
        n += 1
        byt += size(x)
    return n, byt


def series(rows, thread):
    return [req_size(q) for r, q in rows if r["thread"] == thread]


print("== 一、同一件事：4 次各 3 万字节的日志，自己做 vs 派子代理")
tot = {}
for d in ("s3-inline", "s1-fork-default", "s2-fork-none"):
    rows = load(d)
    threads = sorted({r["thread"] for r, _ in rows})
    allsz = [req_size(q) for _, q in rows]
    tot[d] = sum(allsz)
    print(f"\n[{d}] 请求 {len(rows)} 次，输入合计 {sum(allsz):,} 字节 ≈ {tok(sum(allsz)):,} token")
    for t in threads:
        ser = series(rows, t)
        print(f"  {t}: {len(ser)} 次请求 " + " → ".join(f"{x:,}" for x in ser) + f"  （合计 {sum(ser):,}）")
base = tot["s3-inline"]
for d in ("s1-fork-default", "s2-fork-none"):
    print(f"\n{d} 比自己做多 {tot[d] - base:,} 字节（{(tot[d] / base - 1) * 100:.1f}%）")
inline_final = series(load("s3-inline"), "P")[-1]
for d in ("s1-fork-default", "s2-fork-none"):
    rows = load(d)
    p = series(rows, "P")
    print(f"{d}: 父会话最后一次请求 {p[-1]:,}；自己做是 {inline_final:,}；少 {inline_final - p[-1]:,} 字节 ≈ {tok(inline_final - p[-1]):,} token")
    print(f"   父会话从第 1 次到最后一次只多了 {p[-1] - p[0]:,} 字节 ≈ {tok(p[-1] - p[0]):,} token")

print("\n== 二、子代理第一次请求带了什么（相同前缀 = 和父的请求逐条一致的开头）")
for d in ("s1-fork-default", "s2-fork-none"):
    rows = load(d)
    pre_spawn = [q for r, q in rows if r["thread"] == "P"][1]   # 父会话 spawn 之后的那次请求
    first_child = [(r, q) for r, q in rows if r["thread"] == "C1"][0]
    n, b = common_prefix(pre_spawn, first_child[1])
    cs = req_size(first_child[1])
    print(f"[{d}] 子的第 1 次请求 {cs:,} 字节，{len(first_child[1]['input'])} 条；与父 spawn 后那次请求的相同前缀 {n} 条 {b:,} 字节")
    for it in first_child[0]["items"]:
        print(f"   [{it['i']}] {it['type']:<20}{it['bytes']:>8,}  {(it.get('head') or it.get('call') or it.get('output') or '')[:70]}")

print("\n== 三、第一次请求（父会话）里，子代理相关的块有多大（gpt-6.1-sol，思考级别 low，无 MCP）")
names = [("b0-default", "默认"), ("b1-agents-disabled", "[agents] enabled=false"),
         ("b2-collab-false", "features.multi_agent=false"), ("b3-v2-false", "features.multi_agent_v2=false"),
         ("b4-role-empty", "root_agent_usage_hint_text=\"\""), ("b5-mode-empty", "multi_agent_mode_hint_text=\"\""),
         ("b6-both-empty", "两个都置空"), ("b7-disable-native", "disable_native_tools=true"),
         ("b8-ultra", "思考级别 ultra")]
base0 = None
for d, label in names:
    q = json.load(open(O / d / "req-1.json"))
    s = json.load(open(O / d / "summary.json"))[0]
    total = req_size(q)
    base0 = base0 or total
    collab = 0
    for x in q["input"]:
        if x.get("type") == "additional_tools":
            for ns in x["tools"]:
                if ns.get("name") == "collaboration":
                    collab = size(ns)
    role = mode = 0
    for it in s["items"]:
        h = it.get("head", "")
        if "multi_agent_role" in h:
            role = it["bytes"]
        if "multi_agent_mode" in h:
            mode = it["bytes"]
    print(f"{label:34s} 合计 {total:>7,}（{total - base0:+,}）  协作工具 {collab:>5,}  角色说明 {role:>5,}  开关说明 {mode:>4,}")

print("\n== 四、gpt-5.5（思考级别 low）")
for d, label in [("b9-gpt55", "默认"), ("b10-gpt55-v2", "features.multi_agent_v2=true"), ("b11-gpt55-agents-disabled", "[agents] enabled=false")]:
    q = json.load(open(O / d / "req-1.json"))
    s = json.load(open(O / d / "summary.json"))[0]
    print(f"{label:30s} 合计 {req_size(q):>7,}  顶层 tools {size(q['tools']):>6,}  input {len(q['input'])} 条  " +
          ("；".join(f"[{it['i']}] {it['bytes']}B {it['head'][:28]}" for it in s['items'] if 'multi_agent' in it.get('head', '')) or "无子代理说明"))

print("\n== 五、gpt-5.5 派子代理（V1，fork_context 缺省 = false）")
rows = load("v1-gpt55-big")
for r, q in rows:
    print(f"  req{r['n']} {r['thread']} {len(q['input'])} 条 {req_size(q):,} 字节  回复 {r['replied_with'][:60]}")
