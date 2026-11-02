#!/usr/bin/env python3
"""U10 实验 B：只靠 Codex 自己写的会话存档（rollout *.jsonl），算每次运行的指标。

用法：python3 -I u10_metrics.py <rollout.jsonl 或含它的目录>...
每个文件输出一行汇总，再逐轮列出。不读假服务器的日志，所以换成真实服务也能用。

用到的存档记录（源码 protocol/src/protocol.rs:2366-2410、core/src/session/mod.rs:5030-5066）：
  token_usage_record   每个完成的响应一条：usage（这一次请求）、turn_token_usage（本轮累计）、
                       thread_token_usage（会话累计）。压缩请求也有。
  compacted            压缩完成后写一条；它前面最近的一条 token_usage_record 就是压缩请求。
  event_msg/token_count  info.model_context_window 是窗口。
  response_item        function_call / custom_tool_call 数工具调用。
  event_msg/task_started、task_complete   一轮的开始和结束。
"""
import json
import sys
from pathlib import Path


def load(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def summarize(rows):
    turns, cur = [], None
    window = None
    compactions = 0
    last_record_turn = None
    compact_reqs = set()  # 被当成压缩请求的 response_id
    last_resp = None
    tool_calls = 0
    for r in rows:
        t, p = r.get("type"), r.get("payload") or {}
        pt = p.get("type") if isinstance(p, dict) else None
        if t == "event_msg" and pt == "task_started":
            cur = {"turn": p.get("turn_id", "?")[-6:], "requests": 0, "input": 0, "cached": 0, "output": 0,
                   "peak": 0, "compactions": 0, "tools": 0, "compact_input": 0}
            turns.append(cur)
        elif t == "event_msg" and pt == "token_count":
            w = (p.get("info") or {}).get("model_context_window")
            if w:
                window = w
        elif t == "token_usage_record":
            u = p["usage"]
            if cur is None:
                cur = {"turn": "?", "requests": 0, "input": 0, "cached": 0, "output": 0, "peak": 0,
                       "compactions": 0, "tools": 0, "compact_input": 0}
                turns.append(cur)
            cur["requests"] += 1
            cur["input"] += u["input_tokens"]
            cur["cached"] += u["cached_input_tokens"]
            cur["output"] += u["output_tokens"]
            cur["peak"] = max(cur["peak"], u["input_tokens"])
            last_resp = (p["response_id"], u["input_tokens"])
        elif t == "compacted":
            compactions += 1
            if cur is not None:
                cur["compactions"] += 1
            if last_resp:
                compact_reqs.add(last_resp[0])
                if cur is not None:
                    cur["compact_input"] += last_resp[1]
        elif t == "response_item" and pt in ("function_call", "custom_tool_call"):
            tool_calls += 1
            if cur is not None:
                cur["tools"] += 1
    return turns, window, compactions, tool_calls


def main():
    files = []
    for a in sys.argv[1:]:
        p = Path(a)
        files += sorted(p.rglob("*.jsonl")) if p.is_dir() else [p]
    for f in files:
        rows = load(f)
        turns, window, compactions, tool_calls = summarize(rows)
        req = sum(t["requests"] for t in turns)
        inp = sum(t["input"] for t in turns)
        cached = sum(t["cached"] for t in turns)
        out = sum(t["output"] for t in turns)
        peak = max((t["peak"] for t in turns), default=0)
        cin = sum(t["compact_input"] for t in turns)
        print(f"== {f.name[:48]}")
        print(f"   请求 {req}，输入 {inp:,}（其中缓存命中 {cached:,}，{(cached / inp * 100 if inp else 0):.1f}%），输出 {out:,}；"
              f"压缩 {compactions} 次（压缩请求的输入 {cin:,}，占 {(cin / inp * 100 if inp else 0):.1f}%）；"
              f"工具调用 {tool_calls}；单次请求输入峰值 {peak:,}"
              + (f"（窗口 {window:,} 的 {peak / window * 100:.1f}%）" if window else ""))
        for t in turns:
            print(f"     轮 {t['turn']}: 请求 {t['requests']}，输入 {t['input']:,}，缓存 {t['cached']:,}，"
                  f"输出 {t['output']:,}，压缩 {t['compactions']}，工具调用 {t['tools']}，峰值 {t['peak']:,}")


if __name__ == "__main__":
    main()
