#!/usr/bin/env python3
"""U01 实验：让 Codex 把完整请求体发给本机假服务器，再按块统计大小。

不联网、不用登录、不消耗账号额度。假服务器只回一句固定的话。
每次运行用全新的临时 CODEX_HOME，不碰 ~/.codex。

用法示例：
  python3 u01_capture.py --prompt '帮我看下这个报错'
  python3 u01_capture.py --prompt '帮我看下这个报错' --disable incremental_tools
  python3 u01_capture.py --no-agents --out /tmp/u01-noagents
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_AGENTS = (
    "# U01 实验用规则\n"
    "本目录是合成的实验目录，只读取本目录文件。\n"
)


def est_tokens(n_bytes: int) -> int:
    # 与 Codex 的 approx_token_count 同一算法：UTF-8 字节数 / 4 向上取整。
    # 这是估算，不是真实 tokenizer 的结果；中文通常会被低估。
    return math.ceil(n_bytes / 4)


class Handler(BaseHTTPRequestHandler):
    out_dir: Path
    seen: list
    tool_call: bool = False

    def log_message(self, *_):
        pass

    def do_GET(self):
        self.seen.append(("GET", self.path))
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.seen.append(("POST", self.path, self.headers.get("Content-Encoding")))
        if self.path.rstrip("/").endswith("/responses"):
            n = sum(1 for s in self.seen if s[0] == "POST")
            (self.out_dir / f"req-{n}.raw").write_bytes(body)
            if self.tool_call and n == 1:
                # 第一次回一个无害的工具调用（睡 1 毫秒），逼 Codex 发第二次请求
                item = {
                    "type": "function_call",
                    "id": "fc_1",
                    "call_id": "call_1",
                    "namespace": "clock",
                    "name": "sleep",
                    "arguments": json.dumps({"duration_ms": 1}),
                }
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
        else:
            self.send_response(404)
            self.end_headers()


def block_name(item: dict) -> str:
    t = item.get("type")
    if t == "message":
        texts = [p.get("text", "") for p in item.get("content", []) if isinstance(p, dict)]
        head = texts[0][:60].replace("\n", " ") if texts else ""
        return f"message/{item.get('role')}: {head}"
    if t == "additional_tools":
        names = [x.get("name") or x.get("type") for x in item.get("tools", [])]
        return f"additional_tools: {names}"
    if t == "function_call":
        return f"function_call(模型的工具调用): {item.get('namespace')}.{item.get('name')} {item.get('arguments')}"
    if t == "function_call_output":
        return f"function_call_output(工具输出): {str(item.get('output'))[:60]}"
    return str(t)


def analyze(req: dict) -> list[dict]:
    rows = []
    for key, val in req.items():
        if key == "input":
            continue
        raw = json.dumps(val, ensure_ascii=False)
        rows.append({"where": f"顶层字段 {key}", "bytes": len(raw.encode()), "note": ""})
    for i, item in enumerate(req.get("input", [])):
        if item.get("type") == "message":
            for j, p in enumerate(item.get("content", [])):
                text = p.get("text", "") if isinstance(p, dict) else ""
                rows.append(
                    {
                        "where": f"input[{i}].content[{j}]",
                        "bytes": len(text.encode()),
                        "note": block_name({**item, "content": [p]}),
                    }
                )
        else:
            raw = json.dumps(item, ensure_ascii=False)
            rows.append(
                {"where": f"input[{i}]", "bytes": len(raw.encode()), "note": block_name(item)}
            )
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--codex", default="codex")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--prompt", default="帮我看下这个报错")
    ap.add_argument("--no-agents", action="store_true", help="工作目录里不放 AGENTS.md")
    ap.add_argument("--agents-file", help="用这个文件作为 AGENTS.md")
    ap.add_argument("--disable", action="append", default=[], help="关闭某个特性，可重复")
    ap.add_argument("--enable", action="append", default=[], help="打开某个特性，可重复")
    ap.add_argument("--tool-call", action="store_true", help="第一次回一个工具调用，抓第二次请求")
    ap.add_argument("--out", help="输出目录，默认 ./out/latest")
    args = ap.parse_args()

    out = Path(args.out) if args.out else HERE / "out" / "latest"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    tmp = Path(tempfile.mkdtemp(prefix="u01-"))
    home, ws = tmp / "home", tmp / "ws"
    home.mkdir()
    ws.mkdir()
    if not args.no_agents:
        if args.agents_file:
            shutil.copy(args.agents_file, ws / "AGENTS.md")
        else:
            (ws / "AGENTS.md").write_text(DEFAULT_AGENTS)

    Handler.out_dir, Handler.seen, Handler.tool_call = out, [], args.tool_call
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

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
'''
    )

    cmd = [args.codex, "exec", "--skip-git-repo-check", "-C", str(ws)]
    for f in args.disable:
        cmd += ["--disable", f]
    for f in args.enable:
        cmd += ["--enable", f]
    cmd.append(args.prompt)
    env = {**os.environ, "CODEX_HOME": str(home)}
    print("运行：", " ".join(cmd))
    # stdin 必须指向 /dev/null：codex exec 发现 stdin 是管道时会等它关闭，
    # 在后台任务或脚本里会卡住，而假服务器一个请求也收不到。
    r = subprocess.run(
        cmd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    server.shutdown()
    print("退出码：", r.returncode)
    (out / "codex.stderr.txt").write_text(r.stderr)
    (out / "codex.stdout.txt").write_text(r.stdout)
    (out / "server-seen.json").write_text(json.dumps(Handler.seen, ensure_ascii=False, indent=1))

    raws = sorted(out.glob("req-*.raw"))
    if not raws:
        print("没有收到 /responses 请求。服务器见到的请求：", Handler.seen)
        print("stderr 末尾：", r.stderr[-600:])
        sys.exit(1)
    for raw in raws:
        body = raw.read_bytes()
        req = json.loads(body)
        (out / (raw.stem + ".json")).write_text(json.dumps(req, ensure_ascii=False, indent=1))
        rows = analyze(req)
        print(f"\n=== {raw.stem}：请求体共 {len(body):,} 字节，顶层字段 {list(req.keys())}")
        print(f"{'位置':<26}{'字节':>9}{'≈token':>9}  内容")
        for row in rows:
            print(f"{row['where']:<26}{row['bytes']:>9,}{est_tokens(row['bytes']):>9,}  {row['note']}")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
