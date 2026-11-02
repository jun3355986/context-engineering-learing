#!/usr/bin/env python3
"""汇总 out/<组>/requests.json 和 steps.json：请求数、输入合计、压缩次数、峰值、规则标记在哪，
以及按第 5 章的价目规则折算的成本（gpt-6.1-sol：缓存读 0.05×，30 分钟写入 1.25×）。
折算规则（和第 5 章的计算器相同，假设每次请求之间都没超过 30 分钟）：
  同一线程里，第 k 次请求读上一次请求的全部（0.05×），新增部分写入（1.25×）；
  线程的第一次请求、压缩之后的第一次请求：能接上的只有前两条（工具定义 + 系统提示词，S token），其余整份写入。
  S 取两种假设：S = 0（条目 id 换新就接不上）、S = 11,874（id 不影响，第 5 章的值）。
  另算「每一轮开始前都停过 30 分钟以上」：缓存过期，每轮第一次请求整份按 1.25× 写入。
用法：python3 -I analyze.py <out 目录>   （输出同时写进 <out 目录>/analysis.txt、analysis.json）"""
import json
import sys
from pathlib import Path

ARMS = ["A", "B", "C", "F", "D", "G", "E", "P1", "P2"]
READ, WRITE = 0.05, 1.25
S_OPT = 11_874


def cost(reqs, s_share, gap=False):
    """gap=True：每一轮开始前都停过 30 分钟以上，缓存已过期，那一轮的第一次请求整份按写入价算（S 不再有意义）。"""
    prev = {}          # 线程 → 上一次请求的 token
    fresh = set()      # 需要「整份重写」的线程（压缩之后）
    total = 0.0
    for r in reqs:
        t, th = r["est_tokens"], r["thread"]
        if gap and r["kind"] == "user":
            total += WRITE * t
            fresh.discard(th)
        elif th not in prev or th in fresh:
            s = min(s_share, t)
            total += READ * s + WRITE * (t - s)
            fresh.discard(th)
        else:
            p = min(prev[th], t)
            total += READ * p + WRITE * (t - p)
        prev[th] = t
        if r["kind"] == "compact":
            fresh.add(th)
    return total


def main():
    out = Path(sys.argv[1])
    lines, summary = [], {}
    for arm in ARMS:
        d = out / arm
        if not (d / "requests.json").exists():
            continue
        reqs = json.loads((d / "requests.json").read_text())
        st = json.loads((d / "steps.json").read_text())
        bad = [s for s in st["steps"] if s.get("status") != "completed"]
        total = sum(r["est_tokens"] for r in reqs)
        comp = [r for r in reqs if r["kind"] == "compact"]
        ctotal = sum(r["est_tokens"] for r in comp)
        peak = max(r["est_tokens"] for r in reqs)
        threads = len({r["thread"] for r in reqs})
        first = reqs[0]["est_tokens"]
        last = reqs[-1]
        c0, c1, cg = cost(reqs, 0), cost(reqs, S_OPT), cost(reqs, 0, gap=True)
        where = [f'{c["label"]}({"轮末" if c["after_final"] else "轮中"},{c["est_tokens"]})' for c in comp]
        post = []
        for i, r in enumerate(reqs):
            if r["kind"] == "compact" and i + 1 < len(reqs):
                nxt = reqs[i + 1]
                post.append({"after": r["label"], "rule_in": [x["type"] for x in nxt["rule_in"]],
                             "first_in": [x["type"] for x in nxt["first_in"]], "tokens": nxt["est_tokens"]})
        lines.append(f"== {arm}: 请求 {len(reqs)}，输入合计 {total:,}，其中压缩请求 {len(comp)} 次 / {ctotal:,}；"
                     f"线程 {threads}；峰值 {peak:,}；首个请求 {first:,}；非 completed 轮 {len(bad)}")
        lines.append(f"   折算成本（全价 token）：S=0 → {c0:,.0f}；S=11,874 → {c1:,.0f}；每轮前都停过 30 分钟以上 → {cg:,.0f}")
        lines.append(f"   压缩位置：{', '.join(where) or '无'}")
        for p in post:
            lines.append(f"   压缩（{p['after']}）后第一个请求 {p['tokens']:,}：规则标记在 {p['rule_in'] or '没有'}；第 1 句话标记在 {p['first_in'] or '没有'}")
        lines.append(f"   最后一个请求 {last['label']}：{last['est_tokens']:,}，条数 {last['items']}，工具输出 {last['tool_outputs']} 条；规则在 {[x['type'] for x in last['rule_in']] or '没有'}；第 1 句话在 {[x['type'] for x in last['first_in']] or '没有'}")
        summary[arm] = {"requests": len(reqs), "input_total": total, "compact_n": len(comp), "compact_input": ctotal,
                        "threads": threads, "peak": peak, "first": first, "cost_s0": round(c0), "cost_s11874": round(c1), "cost_gap": round(cg)}
    (out / "analysis.txt").write_text("\n".join(lines) + "\n")
    (out / "analysis.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
