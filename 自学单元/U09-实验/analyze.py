#!/usr/bin/env python3
"""汇总 U09 实验输出：python3 -I analyze.py <out 目录>...
对每个目录：每一步的结果；每次请求的条数/估算 token/结果；压缩请求相邻两次之间消失的是哪一条。"""
import json
import sys
from pathlib import Path


def name_of(h):
    t, x = h["type"], h["text"]
    if t == "additional_tools":
        return "工具定义"
    if x.startswith("You are Codex"):
        return "系统提示词"
    if x.startswith("<skills_instructions>"):
        return "技能目录+权限"
    if x.startswith("<multi_agent_role>"):
        return "子代理角色说明"
    if x.startswith("<multi_agent_mode>"):
        return "子代理开关说明"
    if x.startswith("# AGENTS.md"):
        return "AGENTS.md"
    if x.startswith("You are performing a CONTEXT CHECKPOINT"):
        return "压缩提示词"
    if x.startswith("Another language model"):
        return "摘要"
    if x.startswith("【第"):
        return "用户:" + x[:5] + f"({h['bytes']}B)"
    if x.startswith("REPLY-"):
        return "回复:" + x.split("：")[0].replace("REPLY-", "")
    return f"{t}:{x[:12]}"


def main():
    for d in sys.argv[1:]:
        d = Path(d)
        print("=" * 20, d.name)
        steps = json.loads((d / "steps.json").read_text())
        for s in steps:
            if "status" in s:
                err = s.get("error") or {}
                print(f"  {s['label']:28s} {s['status']:10s} {s.get('seconds', ''):>5}s  {s['requests']}  "
                      f"{err.get('codexErrorInfo') or ''}")
            else:
                print("  ", {k: v for k, v in s.items() if k != "thread"})
        rows = json.loads((d / "requests.json").read_text())
        total = 0
        print("  -- 请求")
        prev = None
        for r in rows:
            total += r["est_tokens"]
            line = f"  {r['n']:>3} {r['label']:26s} {r['kind']:10s} 条数={r['items']:>3} 估算token={r['est_tokens']:>7} {r['outcome']}"
            if r["kind"] == "compact" and "head" in r:
                names = [name_of(h) for h in r["head"]]
                if prev is not None and prev["label"] == r["label"]:
                    gone = [n for n in prev["names"] if n not in names]
                    line += f"  相比上一次少了: {gone if gone else '（看不出，条数变了）' if r['items'] != prev['items'] else '（一模一样）'}"
                prev = {"label": r["label"], "names": names, "items": r["items"]}
            print(line)
        print(f"  请求合计 {len(rows)} 次，估算 token 合计 {total}")


if __name__ == "__main__":
    main()
