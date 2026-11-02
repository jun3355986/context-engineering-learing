#!/usr/bin/env python3
"""U04 实验：同一会话里连续几次请求，前缀是不是原样保留；WebSocket 下第二次请求到底发了什么。

做法：本机起一个假 Responses 服务器，同一个端口既接 HTTP（POST /v1/responses，SSE 回复），
也接 WebSocket（GET /v1/responses 升级）。自定义通道 model_provider = "mock"，
用 --transport 决定通道配置里 supports_websockets 是 true 还是 false。

剧本（每轮是一次独立的 codex exec / exec resume --last 进程）：
  第 1 轮：用户一句话 → 假服务器让模型调一次工具 → 再调一次工具 → 回一句话（同一进程里 3 次请求）
  第 2 轮：resume，用户一句话 → 回一句话
  第 3 轮：resume，同时用 -c features.sleep_tool=false 关掉一个工具 → 回一句话
假服务器在 usage 里报 cached_tokens = 4321，用来确认 Codex 把它读到哪里（不是真实缓存）。

输出：
  msg-NN.json   WebSocket 收到的原始消息（只在 ws 模式）
  req-NN.json   每次请求的完整内容（ws 模式按 previous_response_id 拼回完整 input）
  seen.json     每次请求的摘要：通道、previous_response_id、本次实际发了几条 input、多少字节
  runs.json     每个 codex 进程的退出码和输出尾部（含 --json 的 usage）
不联网、不登录、不消耗额度。

用法：python3 -I u04_cache.py --transport ws --out /abs/path/out/ws
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
FAKE_CACHED = 4321


def nbytes(obj) -> int:
    return len(json.dumps(obj, ensure_ascii=False).encode())


class State:
    lock = threading.Lock()
    n = 0
    seen: list = []
    by_resp: dict = {}  # response_id -> (完整 input, 本次回复的 output items)
    out_dir: Path = Path(".")


def plan_reply(full_input: list, generate: bool, rid: str) -> list:
    """按剧本决定回什么 output items。"""
    if not generate:
        return []
    tool_outputs = sum(1 for it in full_input
                       if it.get("type") in ("function_call_output", "custom_tool_call_output"))
    # 只看本轮：找最后一条用户消息之后有几次工具输出
    last_user = max((i for i, it in enumerate(full_input)
                     if it.get("type") == "message" and it.get("role") == "user"), default=-1)
    tool_outputs = sum(1 for it in full_input[last_user + 1:]
                       if it.get("type") in ("function_call_output", "custom_tool_call_output"))
    user_text = ""
    if last_user >= 0:
        c = full_input[last_user].get("content")
        if isinstance(c, list):
            user_text = "".join(p.get("text", "") for p in c if isinstance(p, dict))
    if "【第1轮】" in user_text and tool_outputs < 2:
        js = f"text('tool-call-{tool_outputs + 1}');\n"
        return [{"type": "custom_tool_call", "id": f"ctc_{rid}", "call_id": f"call_{rid}",
                 "name": "exec", "input": js}]
    return [{"type": "message", "role": "assistant", "id": f"msg_{rid}",
             "content": [{"type": "output_text", "text": f"REPLY-{rid}：好的。"}]}]


def events_for(rid: str, items: list) -> list:
    ev = [{"type": "response.created", "response": {"id": rid}}]
    ev += [{"type": "response.output_item.done", "item": it} for it in items]
    ev.append({"type": "response.completed", "response": {"id": rid, "usage": {
        "input_tokens": 50000, "input_tokens_details": {"cached_tokens": FAKE_CACHED},
        "output_tokens": 10, "output_tokens_details": None, "total_tokens": 50010}}})
    return ev


def record(transport: str, raw: dict) -> tuple:
    """登记一次请求，返回 (response_id, output items)。"""
    with State.lock:
        State.n += 1
        n = State.n
        rid = f"resp_{n}"
        prev = raw.get("previous_response_id")
        delta = raw.get("input", [])
        if prev:
            base_input, base_out = State.by_resp.get(prev, ([], []))
            full_input = base_input + base_out + delta
        else:
            full_input = delta
        generate = raw.get("generate", True) is not False
        items = plan_reply(full_input, generate, rid)
        State.by_resp[rid] = (full_input, items)
        full = dict(raw)
        full["input"] = full_input
        full.pop("previous_response_id", None)
        (State.out_dir / f"req-{n:02d}.json").write_text(json.dumps(full, ensure_ascii=False, indent=1))
        if transport == "ws":
            (State.out_dir / f"msg-{n:02d}.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1))
        State.seen.append({
            "n": n, "transport": transport, "type": raw.get("type"), "generate": generate,
            "previous_response_id": prev, "sent_input_items": len(delta),
            "sent_bytes": len(json.dumps(raw, ensure_ascii=False).encode()),
            "full_input_items": len(full_input), "full_input_bytes": nbytes(full_input),
            "reply": [it.get("type") for it in items],
        })
        return rid, items


def ws_recv(rfile):
    """读一条完整消息（处理分片），返回 (opcode, bytes)；连接关闭返回 (None, b"")。"""
    data, first_op = b"", None
    while True:
        hdr = rfile.read(2)
        if len(hdr) < 2:
            return None, b""
        fin, op = hdr[0] & 0x80, hdr[0] & 0x0F
        masked, ln = hdr[1] & 0x80, hdr[1] & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", rfile.read(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", rfile.read(8))[0]
        mask = rfile.read(4) if masked else b"\0\0\0\0"
        payload = bytearray(rfile.read(ln))
        for i in range(len(payload)):
            payload[i] ^= mask[i % 4]
        if op in (8, 9, 10):  # 控制帧不参与拼接
            return op, bytes(payload)
        if first_op is None:
            first_op = op
        data += payload
        if fin:
            return first_op, data


def ws_send(wfile, op: int, payload: bytes):
    hdr = bytes([0x80 | op])
    n = len(payload)
    if n < 126:
        hdr += bytes([n])
    elif n < 65536:
        hdr += bytes([126]) + struct.pack(">H", n)
    else:
        hdr += bytes([127]) + struct.pack(">Q", n)
    wfile.write(hdr + payload)
    wfile.flush()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def do_GET(self):
        if self.headers.get("Upgrade", "").lower() != "websocket":
            State.seen.append({"GET": self.path, "status": 404})
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        key = self.headers["Sec-WebSocket-Key"]
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.wfile.flush()
        with State.lock:
            State.seen.append({"ws_handshake": self.path,
                               "extensions": self.headers.get("Sec-WebSocket-Extensions")})
        while True:
            op, data = ws_recv(self.rfile)
            if op is None or op == 8:
                break
            if op == 9:
                ws_send(self.wfile, 10, data)
                continue
            if op not in (1, 2):
                continue
            raw = json.loads(data)
            rid, items = record("ws", raw)
            for e in events_for(rid, items):
                ws_send(self.wfile, 1, json.dumps(e).encode())
        self.close_connection = True

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        if self.headers.get("Content-Encoding"):
            State.seen.append({"POST": self.path, "content_encoding": self.headers["Content-Encoding"]})
        if not self.path.rstrip("/").endswith("/responses"):
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        raw = json.loads(body)
        rid, items = record("http", raw)
        payload = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n"
                          for e in events_for(rid, items)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--codex", default="codex")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--transport", choices=["ws", "http"], required=True)
    ap.add_argument("--out", required=True, help="输出目录（绝对路径）")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    State.out_dir = out

    tmp = Path(tempfile.mkdtemp(prefix="u04-"))
    home, ws = tmp / "home", tmp / "ws"
    home.mkdir()
    ws.mkdir()
    (ws / "AGENTS.md").write_text("# U04 实验用规则\n本目录是合成的实验目录。\n")

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
supports_websockets = {"true" if args.transport == "ws" else "false"}
[projects.'{ws}']
trust_level = "trusted"
'''
    )
    env = {**os.environ, "CODEX_HOME": str(home)}
    turns = [
        ([], "【第1轮】先调两次工具看看。"),
        (["resume", "--last"], "【第2轮】继续。"),
        (["resume", "--last"], "【第3轮】关掉一个工具后再继续。"),
    ]
    log = []
    for i, (extra, prompt) in enumerate(turns, start=1):
        cfg = ["-c", "features.sleep_tool=false"] if i == 3 else []
        cmd = [args.codex, "exec", "--json", "--skip-git-repo-check", "-C", str(ws), *cfg, *extra, prompt]
        with State.lock:
            State.seen.append({"process": i, "cmd_tail": " ".join(cmd[2:])[-120:]})
        r = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=180, cwd=str(ws))
        log.append({"turn": i, "rc": r.returncode, "stderr_tail": r.stderr[-1500:],
                    "stdout_tail": r.stdout[-1500:]})
        print(f"第 {i} 轮 退出码 {r.returncode}")
        if r.returncode != 0:
            print(r.stderr[-1500:])
    server.shutdown()
    (out / "runs.json").write_text(json.dumps(log, ensure_ascii=False, indent=1))
    (out / "seen.json").write_text(json.dumps(State.seen, ensure_ascii=False, indent=1))
    for f in (home / "sessions").rglob("*.jsonl"):
        shutil.copy(f, out / "rollout.jsonl")
    shutil.rmtree(tmp, ignore_errors=True)
    for s in State.seen:
        print(json.dumps(s, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
