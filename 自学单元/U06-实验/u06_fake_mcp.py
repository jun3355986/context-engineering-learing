#!/usr/bin/env python3
"""U06 实验用的假 MCP 服务器：一个工具 dump_log，返回固定长度的「日志」。不联网。

用法（由 u06_subagent.py 自动拉起）：python3 u06_fake_mcp.py
dump_log 参数 lines（默认 400）：返回 lines 行，每行 75 字节左右（400 行约 3 万字节）。
"""
import json
import sys

TOOL = {
    "name": "dump_log",
    "description": "Return the last N lines of the service log.",
    "inputSchema": {"type": "object", "properties": {"lines": {"type": "string", "description": "How many lines."}}, "required": []},
}


def reply(msg_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\n")
    sys.stdout.flush()


def log_text(n, tag):
    return "\n".join(f"2026-11-02T10:{i % 60:02d}:00Z INFO  worker-{i % 7} {tag} request {i:06d} ok latency={i % 97}ms" for i in range(n))


def main():
    calls = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        method, msg_id = msg.get("method"), msg.get("id")
        if method == "initialize":
            reply(msg_id, {"protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-03-26"),
                           "capabilities": {"tools": {}}, "serverInfo": {"name": "dump", "version": "0.0.1"}})
        elif method == "tools/list":
            reply(msg_id, {"tools": [TOOL]})
        elif method == "tools/call":
            calls += 1
            args = msg.get("params", {}).get("arguments") or {}
            n = int(args.get("lines") or 400)
            reply(msg_id, {"content": [{"type": "text", "text": log_text(n, f"call{calls}")}]})
        elif msg_id is not None:
            reply(msg_id, {})


if __name__ == "__main__":
    main()
