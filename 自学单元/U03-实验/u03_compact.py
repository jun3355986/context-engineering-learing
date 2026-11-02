#!/usr/bin/env python3
"""U03 实验：多轮对话触发一次自动压缩，抓压缩前后的请求，看「压缩后还剩什么」。

做法：本机起假 Responses 服务器，用自定义通道（model_provider = "mock"）。
自定义通道不支持远端压缩，所以 Codex 走「本地压缩」：把整段历史 + 一段写摘要的提示词发给模型，
拿回摘要文本，再拼新历史。假服务器按脚本回复：
  第 1 轮：先让 Codex 执行一条命令（产生一条工具输出），再回一句话
  第 2 轮：用户发一条约 1.5 万 token 的长消息
  第 3 轮：用户发一条约 6 千 token 的消息；假服务器在这轮回复里报告「已用 12 万 token」
  第 4 轮：开头触发自动压缩（压缩线由 --limit 设，默认 10 万）
  第 5 轮：压缩之后再说一句，看历史怎么接着长
每轮是一次独立的 `codex exec` / `codex exec resume --last`。不联网、不登录、不消耗额度。

用法：python3 -I u03_compact.py --out /abs/path/out/default
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

COMPACT_MARK = "CONTEXT CHECKPOINT COMPACTION"
SUMMARY_TEXT = "SUMMARY-FROM-MOCK：用户叫 Drake；规则是不要改数据库 schema；已跑过一次 seq 命令。"


def est_tokens(n_bytes: int) -> int:
    # 与 Codex 的 approx_token_count 同一算法：UTF-8 字节数 / 4 向上取整（估算）
    return math.ceil(n_bytes / 4)


def item_text(it: dict) -> str:
    c = it.get("content")
    if isinstance(c, list):
        return "".join(p.get("text", "") for p in c if isinstance(p, dict))
    if isinstance(c, str):
        return c
    out = it.get("output")
    if isinstance(out, str):
        return out
    if isinstance(out, list):
        return "".join(p.get("text", "") for p in out if isinstance(p, dict))
    if "input" in it and isinstance(it["input"], str):
        return it["input"]
    return ""


class Handler(BaseHTTPRequestHandler):
    out_dir: Path
    seen: list
    usage_by_turn: dict

    def log_message(self, *_):
        pass

    def do_GET(self):
        self.seen.append(("GET", self.path))
        self.send_response(404)
        self.end_headers()

    def reply(self, n: int, items: list, total_tokens: int):
        events = [{"type": "response.created", "response": {"id": f"resp_{n}"}}]
        events += [{"type": "response.output_item.done", "item": it} for it in items]
        events.append(
            {
                "type": "response.completed",
                "response": {
                    "id": f"resp_{n}",
                    "usage": {
                        "input_tokens": total_tokens,
                        "input_tokens_details": None,
                        "output_tokens": 0,
                        "output_tokens_details": None,
                        "total_tokens": total_tokens,
                    },
                },
            }
        )
        payload = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        if not self.path.rstrip("/").endswith("/responses"):
            self.seen.append(("POST", self.path, "404"))
            self.send_response(404)
            self.end_headers()
            return
        n = sum(1 for s in self.seen if s[0] == "POST" and s[2] != "404") + 1
        req = json.loads(body)
        inp = req.get("input", [])
        last = inp[-1] if inp else {}
        last_text = item_text(last)
        # 判断这是哪种请求
        if COMPACT_MARK in last_text:
            kind = "compact"
        elif last.get("type") in ("function_call_output", "custom_tool_call_output"):
            kind = "after-tool"
        else:
            kind = "user"
        # 当前是第几轮：看最后一条用户消息里的「第N轮」标记
        turn = 0
        for it in reversed(inp):
            if it.get("role") == "user":
                t = item_text(it)
                for k in range(1, 10):
                    if f"【第{k}轮】" in t:
                        turn = k
                        break
                if turn:
                    break
        self.seen.append(("POST", self.path, kind, turn, len(body)))
        (self.out_dir / f"req-{n:02d}-{kind}-t{turn}.json").write_text(
            json.dumps(req, ensure_ascii=False, indent=1)
        )
        if kind == "compact":
            items = [{"type": "message", "role": "assistant", "id": f"msg_{n}",
                      "content": [{"type": "output_text", "text": SUMMARY_TEXT}]}]
            return self.reply(n, items, 3000)
        if kind == "user" and turn == 1:
            js = ("const r = await tools.exec_command({\"cmd\": \"seq 1 3000\"});\n"
                  "text(typeof r === 'string' ? r : r.output);\n")
            items = [{"type": "custom_tool_call", "id": "ctc_1", "call_id": "call_1",
                      "name": "exec", "input": js}]
            return self.reply(n, items, 1000)
        text = f"REPLY-T{turn}：好的。"
        items = [{"type": "message", "role": "assistant", "id": f"msg_{n}",
                  "content": [{"type": "output_text", "text": text}]}]
        return self.reply(n, items, self.usage_by_turn.get(turn, 1000))


def turn_prompts() -> list:
    t2_body = ("LONG-A " * 8600)  # 约 60,200 字节 ≈ 15,050 token
    t3_body = ("LONG-B " * 3400)  # 约 23,800 字节 ≈ 5,950 token
    return [
        "【第1轮】我叫 Drake。规则：不要改数据库 schema。先跑一下 seq 看看。",
        "【第2轮】下面是一大段日志：" + t2_body,
        "【第3轮】再补一段：" + t3_body,
        "【第4轮】继续。",
        "【第5轮】还记得我叫什么吗？",
    ]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--codex", default="codex")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--limit", type=int, default=100_000, help="model_auto_compact_token_limit")
    ap.add_argument("--t3-usage", type=int, default=120_000, help="第 3 轮回复里报告的已用 token")
    ap.add_argument("--extra-config", default="", help="追加到 config.toml 顶层的几行")
    ap.add_argument("--out", required=True, help="输出目录（绝对路径）")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    tmp = Path(tempfile.mkdtemp(prefix="u03-"))
    home, ws = tmp / "home", tmp / "ws"
    home.mkdir()
    ws.mkdir()
    (ws / "AGENTS.md").write_text("# U03 实验用规则\n本目录是合成的实验目录。\n")

    Handler.out_dir, Handler.seen = out, []
    Handler.usage_by_turn = {3: args.t3_usage}
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
model_auto_compact_token_limit = {args.limit}
{args.extra_config}
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
    env = {**os.environ, "CODEX_HOME": str(home)}
    log = []
    for i, prompt in enumerate(turn_prompts(), start=1):
        if i == 1:
            cmd = [args.codex, "exec", "--skip-git-repo-check", "-C", str(ws), prompt]
        else:
            cmd = [args.codex, "exec", "--skip-git-repo-check", "-C", str(ws), "resume", "--last", prompt]
        r = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=180, cwd=str(ws))
        log.append({"turn": i, "rc": r.returncode, "stderr_tail": r.stderr[-1500:],
                    "stdout_tail": r.stdout[-600:]})
        print(f"第 {i} 轮 退出码 {r.returncode}")
        if r.returncode != 0:
            print(r.stderr[-1500:])
    server.shutdown()
    (out / "runs.json").write_text(json.dumps(log, ensure_ascii=False, indent=1))
    (out / "server-seen.json").write_text(json.dumps(Handler.seen, ensure_ascii=False, indent=1))
    for f in (home / "sessions").rglob("*.jsonl"):
        shutil.copy(f, out / "rollout.jsonl")
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps(Handler.seen, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
