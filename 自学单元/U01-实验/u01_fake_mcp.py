#!/usr/bin/env python3
"""U01 实验用的假 MCP 服务器：只通过 stdio 声明 N 个工具，不做任何事，不联网。

用法（由 u01_capture.py --mcp-tools N 自动拉起）：
  python3 u01_fake_mcp.py 40
每个工具带约 300 字节的描述和一个 3 参数的 JSON Schema，模拟一个中等大小的 MCP 服务。
"""
import json
import sys

N = int(sys.argv[1]) if len(sys.argv) > 1 else 10


def tool(i):
    return {
        "name": f"fake_tool_{i:02d}",
        "description": (
            f"Fake tool number {i} used only to measure how much room MCP tool "
            "definitions take in a Codex request. It does nothing. "
            "This sentence is padding so each description is about three hundred "
            "bytes long, which is a typical size for a real MCP tool description."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look for."},
                "limit": {"type": "integer", "description": "Maximum number of results."},
                "verbose": {"type": "boolean", "description": "Return extra detail."},
            },
            "required": ["query"],
        },
    }


def reply(msg_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    method, msg_id = msg.get("method"), msg.get("id")
    if method == "initialize":
        reply(
            msg_id,
            {
                "protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-03-26"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake", "version": "0.0.1"},
            },
        )
    elif method == "tools/list":
        reply(msg_id, {"tools": [tool(i) for i in range(N)]})
    elif msg_id is not None:
        reply(msg_id, {})
