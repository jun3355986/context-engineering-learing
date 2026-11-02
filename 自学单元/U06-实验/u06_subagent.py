#!/usr/bin/env python3
"""U06 实验：父会话派出子代理后，两边的请求里各装了什么？

本机假 Responses 服务器 + 假 MCP 服务器（u06_fake_mcp.py，工具 dump_log 返回约 3 万字节日志）。
不联网、不花额度，每次运行用全新的临时 CODEX_HOME。传输走 HTTP（自定义通道）。

假服务器同时扮演父会话和子代理：按请求里 `client_metadata.thread_id` 分线程
（`prompt_cache_key` 是整棵代理树共用的会话 id，分不出父子），
第一个出现的是父（P），之后依次是子（C1、C2…）。每个线程各有一份「剧本」，每次请求回一步，
剧本用完回一句话。父用 --parent，所有子都用 --child（每个子各用一份拷贝）。

步骤（用 ';' 分隔，没有 ';' 时用 ','）：
  text[:内容]               回一句话（内容缺省 MOCK_REPLY）
  dump[:行数]               调 MCP 工具 dump_log（缺省 400 行，约 3 万字节）
  bigtext[:行数]            回一段长文本（每行约 70 字节），测最终回答有没有上限
  spawn:任务名|fork|消息    调 collaboration.spawn_agent；fork 为 all / none / 空（不传，用缺省）
  wait[:毫秒]               调 collaboration.wait_agent（缺省 30000）
  search:查询词[|个数]      调 tool_search（gpt-5.5 才有）
  call:命名空间:名字:JSON   通用函数调用（gpt-5.5 的 V1 工具在 multi_agent_v1 命名空间；
                            JSON 里写 @AGENT@ 会换成上一步 spawn_agent 返回的 agent_id）
  exec:JS                   调 exec（gpt-6.1-sol 的代码工具）
  sleep:毫秒                调 clock.sleep

用法示例：
  python3 -I u06_subagent.py --parent "spawn:scan|all|查日志;wait;text" \
      --child "dump;dump;dump;dump;text:结论：无异常" --out /abs/out/x
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent


class State:
    out_dir: Path
    lock = threading.Lock()
    n = 0
    keys: list = []          # 线程 key，下标 0 = 父
    queues: dict = {}        # key -> 剩余步骤
    parent_script: list = []
    child_script: list = []
    rows: list = []


def step_to_item(step: str, n: int) -> dict:
    kind, _, rest = step.partition(":")
    cid = f"call_{n}"
    if kind == "sleep":
        return fc(n, "clock", "sleep", {"duration_ms": int(rest or 1)})
    if kind == "dump":
        return fc(n, "mcp__dump", "dump_log", {"lines": rest or "400"})
    if kind == "spawn":
        task, fork, msg = (rest.split("|", 2) + ["", ""])[:3]
        args = {"task_name": task, "message": msg or "请查一下日志，只回结论。"}
        if fork:
            args["fork_turns"] = fork
        return fc(n, "collaboration", "spawn_agent", args)
    if kind == "search":
        query, _, limit = rest.partition("|")
        a = {"query": query}
        if limit:
            a["limit"] = int(limit)
        return {"type": "tool_search_call", "call_id": cid, "execution": "client", "arguments": a}
    if kind == "wait":
        return fc(n, "collaboration", "wait_agent", {"timeout_ms": int(rest or 30000)})
    if kind == "call":
        ns, name, args = rest.split(":", 2)
        return {"type": "function_call", "id": f"fc_{n}", "call_id": cid, "namespace": ns,
                "name": name, "arguments": args or "{}"}
    if kind == "exec":
        return {"type": "custom_tool_call", "id": f"ctc_{n}", "call_id": cid, "name": "exec", "input": rest}
    if kind == "bigtext":  # 回一段 N 行的长文本，用来测子代理的最终回答有没有上限
        rest = "\n".join(f"第 {i:05d} 行：这是子代理写的一行分析文字，用来凑长度。" for i in range(int(rest or 1000)))
        kind = "text"
    text = rest if kind == "text" and rest else "MOCK_REPLY"
    return {"type": "message", "role": "assistant", "id": f"msg_{n}",
            "content": [{"type": "output_text", "text": text}]}


def fc(n, ns, name, args):
    return {"type": "function_call", "id": f"fc_{n}", "call_id": f"call_{n}",
            "namespace": ns, "name": name, "arguments": json.dumps(args, ensure_ascii=False)}


def tool_names(tools: list) -> list:
    names = []
    for t in tools or []:
        if t.get("type") == "namespace":
            names.append(f"{t.get('name')}[{','.join(x.get('name', x.get('type', '?')) for x in t.get('tools', []))}]")
        else:
            names.append(t.get("name") or t.get("type"))
    return names


def summarize(n: int, label: str, raw: bytes, req: dict) -> dict:
    inp = req.get("input", [])
    meta = req.get("client_metadata") or {}
    row = {"n": n, "thread": label, "bytes": len(raw), "model": req.get("model"),
           "prompt_cache_key": req.get("prompt_cache_key"), "thread_id": meta.get("thread_id"),
           "subagent": meta.get("x-openai-subagent"), "parent_thread": meta.get("x-codex-parent-thread-id"),
           "top_tools": tool_names(req.get("tools")),
           "top_tools_bytes": len(json.dumps(req.get("tools", []), ensure_ascii=False).encode()),
           "client_metadata_keys": sorted(meta)}
    items = []
    for i, it in enumerate(inp):
        t = it.get("type")
        size = len(json.dumps(it, ensure_ascii=False).encode())
        d = {"i": i, "type": t, "bytes": size}
        if t == "additional_tools":
            d["tools"] = tool_names(it.get("tools"))
        elif t in ("function_call", "tool_search_call", "custom_tool_call"):
            d["call"] = f"{it.get('namespace', '')}.{it.get('name', '')} {json.dumps(it.get('arguments'), ensure_ascii=False)[:100]}"
        elif t in ("function_call_output", "custom_tool_call_output"):
            d["output"] = str(it.get("output"))[:240].replace("\n", " ")
        elif t == "message":
            texts = [p.get("text", "") for p in it.get("content", []) if isinstance(p, dict)]
            d["role"] = it.get("role")
            d["head"] = (texts[0][:160].replace("\n", " ") if texts else "")
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
        meta = req.get("client_metadata") or {}
        key = meta.get("thread_id") or req.get("prompt_cache_key") or "?"
        with State.lock:
            State.n += 1
            n = State.n
            if key not in State.keys:
                State.keys.append(key)
                State.queues[key] = list(State.parent_script if len(State.keys) == 1 else State.child_script)
            idx = State.keys.index(key)
            label = "P" if idx == 0 else f"C{idx}"
            queue = State.queues[key]
            step = queue.pop(0) if queue else "text"
        (State.out_dir / f"req-{n}.json").write_text(json.dumps(req, ensure_ascii=False, indent=1))
        row = summarize(n, label, body, req)
        row["replied_with"] = step
        row["t"] = round(time.time() % 10000, 2)
        State.rows.append(row)
        if "@AGENT@" in step:  # 把上一步 spawn_agent 返回的 agent_id 填进来（V1 的 wait_agent 要 id）
            for it in reversed(req.get("input", [])):
                out_text = str(it.get("output", "")) if it.get("type") == "function_call_output" else ""
                if '"agent_id"' in out_text:
                    step = step.replace("@AGENT@", json.loads(out_text)["agent_id"])
                    break
        item = step_to_item(step, n)
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


def split_script(s: str) -> list:
    if s.startswith("@"):
        return json.loads(Path(s[1:]).read_text())
    sep = ";" if ";" in s else ","
    return [x for x in s.split(sep) if x]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--codex", default="codex")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--effort", default="low", help="model_reasoning_effort，缺省 low")
    ap.add_argument("--parent", default="text")
    ap.add_argument("--child", default="text")
    ap.add_argument("--no-mcp", action="store_true")
    ap.add_argument("--prompt", default="【U06】请查一下服务日志有没有异常")
    ap.add_argument("--config", action="append", default=[], help="-c key=value，可重复")
    ap.add_argument("--toml-extra", default="", help="追加到 config.toml 末尾的原样文本")
    ap.add_argument("--out", required=True, help="输出目录（绝对路径）")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    State.out_dir = out
    State.parent_script = split_script(args.parent)
    State.child_script = split_script(args.child)

    tmp = Path(tempfile.mkdtemp(prefix="u06-"))
    home, ws = tmp / "home", tmp / "ws"
    home.mkdir()
    ws.mkdir()
    (ws / "AGENTS.md").write_text("# U06 实验用规则\n本目录是合成的实验目录。\n")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    mcp_toml = "" if args.no_mcp else (
        f'[mcp_servers.dump]\ncommand = "{sys.executable}"\nargs = ["{HERE / "u06_fake_mcp.py"}"]\n'
        'default_tools_approval_mode = "approve"\n')
    (home / "config.toml").write_text(
        f'''model = "{args.model}"
model_reasoning_effort = "{args.effort}"
model_provider = "mock"
approval_policy = "never"
sandbox_mode = "read-only"
web_search = "disabled"
check_for_update_on_startup = false
{args.toml_extra}
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
    cmd = [args.codex, "exec", "--json", "--skip-git-repo-check", "-C", str(ws)]
    for c in args.config:
        cmd += ["-c", c]
    cmd += [args.prompt]
    t0 = time.time()
    r = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=240, cwd=str(ws))
    print(f"退出码 {r.returncode}，用时 {time.time() - t0:.1f}s")
    (out / "codex.stderr.txt").write_text(r.stderr)
    (out / "codex.stdout.txt").write_text(r.stdout)
    server.shutdown()
    (out / "summary.json").write_text(json.dumps(State.rows, ensure_ascii=False, indent=1))
    for f in (home / "sessions").rglob("*.jsonl"):
        shutil.copy(f, out / f"rollout-{f.stem[-8:]}.jsonl")
    shutil.rmtree(tmp, ignore_errors=True)

    for row in State.rows:
        print(f"\n=== 请求 {row['n']}（{row['thread']}，{row['model']}）共 {row['bytes']:,} 字节；本次回复：{row['replied_with']}")
        if row["top_tools"]:
            print(f"  顶层 tools：{row['top_tools_bytes']:,} 字节 {row['top_tools']}")
        for it in row["items"]:
            extra = it.get("tools") or it.get("call") or it.get("output") or it.get("head") or ""
            print(f"  input[{it['i']}] {it['type']:<22}{it['bytes']:>8,}  {str(extra)[:150]}")


if __name__ == "__main__":
    sys.exit(main())
