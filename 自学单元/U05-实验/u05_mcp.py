#!/usr/bin/env python3
"""U05 实验：挂上 MCP 工具后，Codex 的请求里到底有没有这些工具的定义？

本机假 Responses 服务器 + 假 MCP 服务器（u05_fake_mcp.py）。不联网、不花额度，
每次运行用全新的临时 CODEX_HOME。传输走 HTTP（自定义通道）。

假服务器按「剧本」一步一步回答（每次请求回一步，剧本用完回一句话）：
  sleep:MS            调 clock.sleep 睡 MS 毫秒（拖时间，让 MCP 服务器启动完）
  search:QUERY[|N]    调 tool_search，查询词 QUERY，最多返回 N 个（缺省按 Codex 默认）
  call:NS:NAME:JSON   调 function_call：namespace=NS，name=NAME，参数 JSON
  exec:JS             调 exec（gpt-6.1-sol 的代码工具），JS 是脚本正文（含 ';' 时用 @文件.json）
  text                回一句话

用法示例：
  python3 -I u05_mcp.py --servers tracker,database,monitor --script "sleep:3000,text" --out /abs/out/x
  python3 -I u05_mcp.py --servers bulk:40 --model not-a-real-model --script "sleep:3000,text" --out /abs/out/y

--script2 / --phase2-config：第一个进程跑完后，再起一个 `exec resume --last` 进程，
用 --phase2-config（`-c key=value`，可重复）改配置，剧本换成 --script2。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent


class State:
    out_dir: Path
    lock = threading.Lock()
    n = 0
    phase = 1
    scripts = {1: [], 2: []}
    rows = []


def make_item(step: str, n: int) -> dict:
    kind, _, rest = step.partition(":")
    if kind == "sleep":
        return {"type": "function_call", "id": f"fc_{n}", "call_id": f"call_{n}",
                "namespace": "clock", "name": "sleep",
                "arguments": json.dumps({"duration_ms": int(rest or 1)})}
    if kind == "search":
        query, _, limit = rest.partition("|")
        args = {"query": query}
        if limit:
            args["limit"] = int(limit)
        return {"type": "tool_search_call", "call_id": f"call_{n}", "execution": "client",
                "arguments": args}
    if kind == "exec":
        return {"type": "custom_tool_call", "id": f"ctc_{n}", "call_id": f"call_{n}",
                "name": "exec", "input": rest}
    if kind == "call":
        ns, name, args = rest.split(":", 2)
        return {"type": "function_call", "id": f"fc_{n}", "call_id": f"call_{n}",
                "namespace": ns, "name": name, "arguments": args or "{}"}
    return {"type": "message", "role": "assistant", "id": f"msg_{n}",
            "content": [{"type": "output_text", "text": "MOCK_REPLY"}]}


def tool_names(tools: list) -> list:
    names = []
    for t in tools or []:
        if t.get("type") == "namespace":
            names.append(f"{t.get('name')}[{','.join(x.get('name', x.get('type', '?')) for x in t.get('tools', []))}]")
        else:
            names.append(t.get("name") or t.get("type"))
    return names


def summarize(n: int, phase: int, raw: bytes, req: dict) -> dict:
    inp = req.get("input", [])
    row = {"n": n, "phase": phase, "bytes": len(raw), "top_tools": tool_names(req.get("tools")),
           "top_tools_bytes": len(json.dumps(req.get("tools", []), ensure_ascii=False).encode())}
    items = []
    for i, it in enumerate(inp):
        t = it.get("type")
        size = len(json.dumps(it, ensure_ascii=False).encode())
        d = {"i": i, "type": t, "bytes": size}
        if t == "additional_tools":
            d["tools"] = tool_names(it.get("tools"))
        elif t == "tool_search_output":
            d["tools"] = tool_names(it.get("tools"))
        elif t in ("function_call", "tool_search_call", "custom_tool_call"):
            d["call"] = f"{it.get('namespace', '')}.{it.get('name', '')} {json.dumps(it.get('arguments'), ensure_ascii=False)[:100]}"
        elif t == "function_call_output":
            d["output"] = str(it.get("output"))[:300]
        elif t == "message":
            texts = [p.get("text", "") for p in it.get("content", []) if isinstance(p, dict)]
            d["role"] = it.get("role")
            d["head"] = (texts[0][:70].replace("\n", " ") if texts else "")
        items.append(d)
    row["items"] = items
    return row


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        if not self.path.rstrip("/").endswith("/responses"):
            self.send_response(404)
            self.end_headers()
            return
        req = json.loads(body)
        with State.lock:
            State.n += 1
            n, phase = State.n, State.phase
            queue = State.scripts[phase]
            step = queue.pop(0) if queue else "text"
        (State.out_dir / f"req-{n}.json").write_text(json.dumps(req, ensure_ascii=False, indent=1))
        row = summarize(n, phase, body, req)
        row["replied_with"] = step
        State.rows.append(row)
        item = make_item(step, n)
        events = [
            {"type": "response.created", "response": {"id": f"resp_{n}"}},
            {"type": "response.output_item.done", "item": item},
            {"type": "response.completed", "response": {"id": f"resp_{n}", "usage": {
                "input_tokens": 0, "input_tokens_details": None, "output_tokens": 0,
                "output_tokens_details": None, "total_tokens": 0}}},
        ]
        payload = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--codex", default="codex")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--servers", default="", help="如 tracker,database,monitor 或 bulk:40，空 = 不挂")
    ap.add_argument("--script", default="text")
    ap.add_argument("--script2", default="")
    ap.add_argument("--no-approve", action="store_true", help="不给 MCP 服务器写 default_tools_approval_mode = approve")
    ap.add_argument("--server-extra", action="append", default=[],
                    help='给某个 MCP 服务器多写一行配置，如 \'tracker:enabled_tools = ["list_issues"]\'，可重复')
    ap.add_argument("--config", action="append", default=[], help="-c key=value，可重复，两个进程都用")
    ap.add_argument("--phase2-config", action="append", default=[])
    ap.add_argument("--out", required=True, help="输出目录（绝对路径）")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    State.out_dir = out
    State.scripts[1] = split_script(args.script)
    State.scripts[2] = split_script(args.script2) if args.script2 else []

    tmp = Path(tempfile.mkdtemp(prefix="u05-"))
    home, ws = tmp / "home", tmp / "ws"
    home.mkdir()
    ws.mkdir()
    (ws / "AGENTS.md").write_text("# U05 实验用规则\n本目录是合成的实验目录。\n")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    mcp_toml = ""
    for spec in [s for s in args.servers.split(",") if s]:
        name, _, n = spec.partition(":")
        mcp_toml += (f'[mcp_servers.{name}]\ncommand = "{sys.executable}"\n'
                     f'args = ["{HERE / "u05_fake_mcp.py"}", "{name}"' + (f', "{n}"' if n else "") + "]\n"
                     + ('' if args.no_approve else 'default_tools_approval_mode = "approve"\n'))
        for extra in args.server_extra:
            sname, _, line = extra.partition(":")
            if sname == name:
                mcp_toml += line + "\n"
    (home / "config.toml").write_text(
        f'''model = "{args.model}"
model_reasoning_effort = "low"
model_provider = "mock"
approval_policy = "never"
sandbox_mode = "read-only"
web_search = "disabled"
check_for_update_on_startup = false
[analytics]
enabled = false
[model_providers.mock]
name = "mock"
base_url = "http://127.0.0.1:{port}/v1"
wire_api = "responses"
requires_openai_auth = false
[projects.'{ws}']
trust_level = "trusted"
''' + mcp_toml)

    env = {**os.environ, "CODEX_HOME": str(home)}
    log = []
    phases = [(1, [], args.config, "【U05】第 1 轮")]
    if args.script2:
        phases.append((2, ["resume", "--last"], args.config + args.phase2_config, "【U05】第 2 轮"))
    for phase, extra, cfgs, prompt in phases:
        State.phase = phase
        cmd = [args.codex, "exec", "--json", "--skip-git-repo-check", "-C", str(ws)]
        for c in cfgs:
            cmd += ["-c", c]
        cmd += [*extra, prompt]
        r = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=240, cwd=str(ws))
        log.append({"phase": phase, "rc": r.returncode, "stdout": r.stdout[-3000:]})
        (out / f"codex-{phase}.stderr.txt").write_text(r.stderr)
        print(f"进程 {phase} 退出码 {r.returncode}")
    server.shutdown()
    (out / "runs.json").write_text(json.dumps(log, ensure_ascii=False, indent=1))
    (out / "summary.json").write_text(json.dumps(State.rows, ensure_ascii=False, indent=1))
    for f in (home / "sessions").rglob("*.jsonl"):
        shutil.copy(f, out / f"rollout-{f.stem[-8:]}.jsonl")
    shutil.rmtree(tmp, ignore_errors=True)

    for row in State.rows:
        print(f"\n=== 请求 {row['n']}（进程 {row['phase']}）共 {row['bytes']:,} 字节；本次回复：{row['replied_with']}")
        print(f"  顶层 tools：{row['top_tools_bytes']:,} 字节 {row['top_tools']}")
        for it in row["items"]:
            extra = it.get("tools") or it.get("call") or it.get("output") or it.get("head") or ""
            print(f"  input[{it['i']}] {it['type']:<22}{it['bytes']:>8,}  {extra}")


def split_script(s: str) -> list:
    if s.startswith("@"):
        return json.loads(Path(s[1:]).read_text())
    """步骤之间用 ';' 分隔；没有 ';' 时用 ','（call: 的 JSON 参数含逗号时必须用 ';'）。"""
    sep = ";" if ";" in s else ","
    return [x for x in s.split(sep) if x]


if __name__ == "__main__":
    sys.exit(main())
