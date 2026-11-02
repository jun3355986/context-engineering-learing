#!/usr/bin/env python3
"""U02 实验：造一次「命令输出很大」的场景，量出进入第二次请求的工具输出有多大、截在哪。

做法：本机起假 Responses 服务器。第一次请求，它回「请执行这条命令」的工具调用；
Codex 真的在本机执行命令，把结果放进第二次请求；我们抓第二次请求，并把会话存档（rollout）也留下来。
不联网、不登录、不消耗额度。每次用全新的临时 CODEX_HOME，不碰 ~/.codex。

两种调用路径：
  --via exec          Lite 模型（gpt-6.1-sol 等）：模型发 exec（跑 JS），JS 里再调 tools.exec_command
  --via exec_command  非 Lite 模型：模型直接发 exec_command

用法示例：
  python3 u02_capture.py --cmd 'seq 1 50000' --out /abs/path/out/seq50000
  python3 u02_capture.py --cmd 'seq 1 50000' --via exec_command --model gpt-5.5 --out /abs/path/out/seq50000-direct
  python3 u02_capture.py --cmd 'seq 1 50000' --tool-output-token-limit 2000 --out ...
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent


def est_tokens(n_bytes: int) -> int:
    # 与 Codex 的 approx_token_count 同一算法：UTF-8 字节数 / 4 向上取整（估算，不是真实 tokenizer）
    return math.ceil(n_bytes / 4)


class Handler(BaseHTTPRequestHandler):
    out_dir: Path
    seen: list
    first_item: dict

    def log_message(self, *_):
        pass

    def do_GET(self):
        self.seen.append(("GET", self.path))
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.seen.append(("POST", self.path))
        if not self.path.rstrip("/").endswith("/responses"):
            self.send_response(404)
            self.end_headers()
            return
        n = sum(1 for s in self.seen if s[0] == "POST")
        (self.out_dir / f"req-{n}.raw").write_bytes(body)
        if n == 1:
            item = self.first_item
        else:
            item = {
                "type": "message",
                "role": "assistant",
                "id": f"msg_{n}",
                "content": [{"type": "output_text", "text": "MOCK_REPLY"}],
            }
        events = [
            {"type": "response.created", "response": {"id": f"resp_{n}"}},
            {"type": "response.output_item.done", "item": item},
            {
                "type": "response.completed",
                "response": {
                    "id": f"resp_{n}",
                    "usage": {
                        "input_tokens": 0,
                        "input_tokens_details": None,
                        "output_tokens": 0,
                        "output_tokens_details": None,
                        "total_tokens": 0,
                    },
                },
            },
        ]
        payload = "".join(
            f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def first_tool_call(
    via: str, cmd: str, max_output_tokens: int | None, exec_tokens: int | None
) -> dict:
    if via == "exec":
        arg = {"cmd": cmd}
        if max_output_tokens is not None:
            arg["max_output_tokens"] = max_output_tokens
        pragma = (
            f'// @exec: {{"max_output_tokens": {exec_tokens}}}\n' if exec_tokens else ""
        )
        js = (
            pragma
            + f"const r = await tools.exec_command({json.dumps(arg)});\n"
            "text(typeof r === 'string' ? r : r.output);\n"
        )
        return {
            "type": "custom_tool_call",
            "id": "ctc_1",
            "call_id": "call_1",
            "name": "exec",
            "input": js,
        }
    arg = {"cmd": cmd}
    if max_output_tokens is not None:
        arg["max_output_tokens"] = max_output_tokens
    return {
        "type": "function_call",
        "id": "fc_1",
        "call_id": "call_1",
        "name": "exec_command",
        "arguments": json.dumps(arg),
    }


def output_text(item: dict) -> str:
    out = item.get("output")
    if isinstance(out, str):
        return out
    if isinstance(out, list):
        return "".join(p.get("text", "") for p in out if isinstance(p, dict))
    return json.dumps(out, ensure_ascii=False)


def summarize(text: str, label: str):
    b = len(text.encode())
    print(f"\n--- {label}")
    print(f"字节 {b:,}  ≈token {est_tokens(b):,}  行数 {text.count(chr(10)) + 1:,}")
    for m in re.finditer(r"…\d+ tokens truncated…|\.\.\. \d+ bytes omitted \.\.\.", text):
        print(f"  标记 {m.group(0)!r} 位置：第 {m.start():,} 字节处（占全文 {m.start() / max(len(text), 1):.0%}）")
    print("  开头 240 字：", repr(text[:240]))
    print("  结尾 120 字：", repr(text[-120:]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--codex", default="codex")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--via", choices=["exec", "exec_command"], default="exec")
    ap.add_argument("--cmd", required=True, help="让 Codex 执行的 shell 命令")
    ap.add_argument("--max-output-tokens", type=int, help="模型在调用里自己传的 max_output_tokens")
    ap.add_argument(
        "--exec-max-output-tokens",
        type=int,
        help="仅 --via exec：在 JS 第一行写 // @exec: {max_output_tokens: N} 这行开头声明",
    )
    ap.add_argument("--tool-output-token-limit", type=int, help="config.toml 的 tool_output_token_limit")
    ap.add_argument("--sandbox", default="read-only")
    ap.add_argument("--out", required=True, help="输出目录（绝对路径）")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    tmp = Path(tempfile.mkdtemp(prefix="u02-"))
    home, ws = tmp / "home", tmp / "ws"
    home.mkdir()
    ws.mkdir()
    (ws / "AGENTS.md").write_text("# U02 实验用规则\n本目录是合成的实验目录。\n")

    Handler.out_dir, Handler.seen = out, []
    Handler.first_item = first_tool_call(
        args.via, args.cmd, args.max_output_tokens, args.exec_max_output_tokens
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    extra = (
        f"tool_output_token_limit = {args.tool_output_token_limit}\n"
        if args.tool_output_token_limit
        else ""
    )
    (home / "config.toml").write_text(
        f'''model = "{args.model}"
model_reasoning_effort = "low"
model_provider = "mock"
approval_policy = "never"
sandbox_mode = "{args.sandbox}"
web_search = "disabled"
check_for_update_on_startup = false
{extra}[analytics]
enabled = false
[model_providers.mock]
name = "mock"
base_url = "http://127.0.0.1:{port}/v1"
wire_api = "responses"
requires_openai_auth = false
[projects.'{ws}']
trust_level = "trusted"
'''
    )

    cmd = [args.codex, "exec", "--skip-git-repo-check", "-C", str(ws), "跑一下这条命令"]
    env = {**os.environ, "CODEX_HOME": str(home)}
    print("运行：", " ".join(cmd), "| 假服务器让它执行：", args.cmd)
    r = subprocess.run(
        cmd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180
    )
    server.shutdown()
    print("退出码：", r.returncode)
    (out / "codex.stderr.txt").write_text(r.stderr)
    (out / "codex.stdout.txt").write_text(r.stdout)
    (out / "server-seen.json").write_text(json.dumps(Handler.seen, ensure_ascii=False, indent=1))

    # 留下会话存档（rollout），回头查「原文还在不在」
    for f in (home / "sessions").rglob("*.jsonl"):
        shutil.copy(f, out / "rollout.jsonl")

    raws = sorted(out.glob("req-*.raw"))
    if len(raws) < 2:
        print("只收到", len(raws), "个请求。stderr 末尾：", r.stderr[-800:])
        shutil.rmtree(tmp, ignore_errors=True)
        sys.exit(1)

    body = raws[1].read_bytes()
    req = json.loads(body)
    (out / "req-2.json").write_text(json.dumps(req, ensure_ascii=False, indent=1))
    print(f"\n第二次请求体共 {len(body):,} 字节 ≈ {est_tokens(len(body)):,} token")
    outs = [
        it for it in req["input"] if it.get("type") in ("function_call_output", "custom_tool_call_output")
    ]
    for it in outs:
        text = output_text(it)
        (out / "tool-output.txt").write_text(text)
        summarize(text, f"进入请求的工具输出（{it['type']}）")

    rollout = out / "rollout.jsonl"
    if rollout.exists():
        best = 0
        for line in rollout.read_text().splitlines():
            try:
                obj = json.loads(line)
            except Exception:
                continue
            s = json.dumps(obj, ensure_ascii=False)
            if '"output"' in s and ("function_call_output" in s or "custom_tool_call_output" in s):
                best = max(best, len(s.encode()))
        print(f"\n会话存档里最大的一条工具输出记录：{best:,} 字节")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
