#!/usr/bin/env python3
"""U09 实验：窗口真满了会怎样。

做法：本机起假 Responses 服务器（自定义通道 model_provider = "mock"，HTTP），
服务器自己带一个「窗口」：把每次请求 input 里各条 JSON 的 UTF-8 字节数相加，除以 4 向上取整
（和 Codex 本地估算同一算法，不是真实分词），超过窗口就拒绝，拒绝的方式由 --overflow-mode 决定：
  sse      在流里发一个 response.failed 事件，error.code = context_length_exceeded（Codex 单元测试用的格式）
  http400  直接回 HTTP 400，body 里 error.code = context_length_exceeded
用 `codex app-server`（stdio JSON-RPC）发 thread/start、turn/start、thread/resume、thread/revert。
不联网、不登录、不消耗额度；不执行任何命令。

场景（--scenario）：
  bigmsg    进程 A：第 1、2 轮各一条 ASCII 长消息（--early-tokens），第 3 轮一条汉字消息
            （--big-chars 个汉字），第 4、5 轮各一句短话；
            进程 B：thread/resume 后再说一句；
            回退 thread/revert（beforeTurnId = 第 3 轮）后再说一句。
            --big-chars 大 → 那一条自己就比窗口大；--early-tokens 大而 --big-chars 小 → 总量超、单条装得下。
  smallwin  config.toml 里把 model_context_window 设得很小（--window-config），服务器窗口不限；
            第 1 轮（label 以 t1 开头）假服务器连发 --tool-steps 次工具调用（JS 里只 text("ok")，不执行命令），再回一句话；
            然后第 2 轮一句短话。看每一步前后 Codex 压不压。

每次请求记一行：序号、哪一步、类型（user / after-tool / compact）、input 条数、估算 token、字节、结果。
压缩请求和每步的第一次请求，另记 input 里前 12 条的类型、字节和开头。

用法：python3 -I u09_overflow.py --scenario bigmsg --out /abs/path/out/bigmsg-sse
"""
import argparse
import json
import math
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

COMPACT_MARK = "CONTEXT CHECKPOINT COMPACTION"
SUMMARY_TEXT = "SUMMARY-FROM-MOCK：用户叫 Drake；规则是不要改数据库 schema。"


def est_tokens(n_bytes: int) -> int:
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
    if isinstance(it.get("input"), str):
        return it["input"]
    return ""


def item_bytes(it: dict) -> int:
    return len(json.dumps(it, ensure_ascii=False).encode())


def kind_of(it: dict) -> str:
    return it.get("type") or ("role:" + str(it.get("role")))


class State:
    window = 272_000          # 服务器自己的窗口（估算 token）
    mode = "sse"
    label = "init"
    tool_steps = 0            # smallwin：每个 label 里最多发几次工具调用
    tool_done: dict = {}
    n = 0
    log: list = []
    out_dir: Path = Path(".")
    lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def _send(self, status, ctype, payload: bytes):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except OSError:
            pass

    def _sse(self, events):
        payload = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
        self._send(200, "text/event-stream", payload)

    def do_GET(self):
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if not self.path.rstrip("/").endswith("/responses"):
            self.send_response(404)
            self.end_headers()
            return
        req = json.loads(body)
        inp = req.get("input", [])
        last = inp[-1] if inp else {}
        sizes = [item_bytes(it) for it in inp]
        tokens = est_tokens(sum(sizes))
        if COMPACT_MARK in item_text(last):
            kind = "compact"
        elif last.get("type") in ("function_call_output", "custom_tool_call_output"):
            kind = "after-tool"
        else:
            kind = "user"
        with State.lock:
            State.n += 1
            n = State.n
            label = State.label
        row = {"n": n, "label": label, "kind": kind, "items": len(inp), "est_tokens": tokens, "bytes": len(body)}
        # 前 12 条的类型、字节、开头；压缩请求和每步第一次请求才记，其余只记总数，避免文件过大
        first_of_label = not any(r["label"] == label for r in State.log)
        if kind == "compact" or first_of_label or n <= 3:
            row["head"] = [{"i": i, "type": kind_of(it), "bytes": sizes[i], "text": item_text(it)[:40]}
                           for i, it in enumerate(inp[:12])]
            row["tail"] = [{"i": len(inp) - 3 + j, "type": kind_of(it), "bytes": sizes[len(inp) - 3 + j],
                            "text": item_text(it)[:40]} for j, it in enumerate(inp[-3:]) if len(inp) >= 3]
        over = tokens > State.window
        row["outcome"] = "overflow" if over else "ok"
        State.log.append(row)
        if over:
            msg = "Your input exceeds the context window of this model. Please adjust your input and try again."
            if State.mode == "http400":
                err = {"error": {"message": msg, "type": "invalid_request_error", "param": "input",
                                 "code": "context_length_exceeded"}}
                return self._send(400, "application/json", json.dumps(err).encode())
            ev = {"type": "response.failed", "sequence_number": 3, "response": {
                "id": f"resp_{n}", "object": "response", "status": "failed",
                "error": {"code": "context_length_exceeded", "message": msg}, "usage": None}}
            return self._sse([{"type": "response.created", "response": {"id": f"resp_{n}"}}, ev])
        rid = f"resp_{n}"
        if kind == "compact":
            items = [{"type": "message", "role": "assistant", "id": f"msg_{n}",
                      "content": [{"type": "output_text", "text": SUMMARY_TEXT}]}]
        elif kind != "compact" and State.tool_steps and label.startswith("t1") and State.tool_done.get(label, 0) < State.tool_steps:
            State.tool_done[label] = State.tool_done.get(label, 0) + 1
            k = State.tool_done[label]
            items = [{"type": "custom_tool_call", "id": f"ctc_{n}", "call_id": f"call_{n}",
                      "name": "exec", "input": f'text("ok {k}");\n'}]
        else:
            items = [{"type": "message", "role": "assistant", "id": f"msg_{n}",
                      "content": [{"type": "output_text", "text": f"REPLY-{label}：好的。"}]}]
        events = [{"type": "response.created", "response": {"id": rid}}]
        events += [{"type": "response.output_item.done", "item": it} for it in items]
        events.append({"type": "response.completed", "response": {"id": rid, "usage": {
            "input_tokens": tokens, "input_tokens_details": None, "output_tokens": 10,
            "output_tokens_details": None, "total_tokens": tokens + 10}}})
        self._sse(events)


class AppServer:
    """codex app-server 的 stdio JSON-RPC 客户端（同 U07）。"""

    def __init__(self, codex, env, cwd, log_path):
        self.proc = subprocess.Popen([codex, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, env=env, cwd=cwd, text=True, bufsize=1)
        self.next_id = 1
        self.responses = {}
        self.notifs = queue.Queue()
        self.cv = threading.Condition()
        self.log = open(log_path, "a")
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.proc.stdout:
            self.log.write(line[:4000] + ("…\n" if len(line) > 4000 else ""))
            self.log.flush()
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if "id" in msg and ("result" in msg or "error" in msg) and "method" not in msg:
                with self.cv:
                    self.responses[msg["id"]] = msg
                    self.cv.notify_all()
            else:
                self.notifs.put(msg)

    def send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def call(self, method, params, timeout=120):
        rid = self.next_id
        self.next_id += 1
        self.send({"id": rid, "method": method, "params": params})
        with self.cv:
            if not self.cv.wait_for(lambda: rid in self.responses, timeout):
                raise TimeoutError(method)
            msg = self.responses.pop(rid)
        if "error" in msg:
            raise RuntimeError(f"{method}: {msg['error']}")
        return msg["result"]

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


def snap(home: Path, label: str, store: list, markers: list):
    rows = []
    for p in sorted((home / "sessions").rglob("rollout-*.jsonl")):
        text = p.read_text()
        lines = text.splitlines()
        kinds = {}
        for l in lines:
            try:
                d = json.loads(l)
            except ValueError:
                continue
            k = d.get("type")
            if k == "event_msg":
                k += ":" + str(d.get("payload", {}).get("type"))
            kinds[k] = kinds.get(k, 0) + 1
        rows.append({"file": p.name, "lines": len(lines), "bytes": len(text.encode()),
                     "markers": [m for m in markers if m in text], "types": kinds})
    store.append({"step": label, "files": rows})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--codex", default="codex")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--scenario", choices=["bigmsg", "smallwin"], default="bigmsg")
    ap.add_argument("--overflow-mode", choices=["sse", "http400"], default="sse")
    ap.add_argument("--window", type=int, default=272_000, help="服务器窗口（估算 token）")
    ap.add_argument("--early-tokens", type=int, default=40_000, help="bigmsg：第 1、2 轮各一条 ASCII 长消息的估算 token")
    ap.add_argument("--big-chars", type=int, default=400_000, help="bigmsg：第 3 轮汉字消息的字数（上限 1,048,576）")
    ap.add_argument("--window-config", type=int, default=14_000, help="smallwin：config.toml 的 model_context_window；0 = 不设（对照）")
    ap.add_argument("--tool-steps", type=int, default=5, help="smallwin：第 1 轮发几次工具调用")
    ap.add_argument("--manual-compact", action="store_true",
                    help="bigmsg：第 5 轮之后，在同一进程里用 thread/compact/start 手动压缩一次，再说第 6 句")
    ap.add_argument("--turn-timeout", type=int, default=60)
    ap.add_argument("--out", required=True, help="输出目录（绝对路径）")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    State.out_dir, State.mode = out, args.overflow_mode
    State.window = args.window if args.scenario == "bigmsg" else 10_000_000
    State.tool_steps = args.tool_steps if args.scenario == "smallwin" else 0
    State.log, State.tool_done = [], {}

    tmp = Path(tempfile.mkdtemp(prefix="u09-"))
    home, ws = tmp / "home", tmp / "ws"
    home.mkdir()
    ws.mkdir()
    (ws / "AGENTS.md").write_text("# U09 实验用规则\n本目录是合成的实验目录。\n")
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    extra = f"model_context_window = {args.window_config}\n" if args.scenario == "smallwin" and args.window_config else ""
    (home / "config.toml").write_text(f'''model = "{args.model}"
model_reasoning_effort = "low"
model_provider = "mock"
approval_policy = "never"
sandbox_mode = "read-only"
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
''')
    env = dict(os.environ, CODEX_HOME=str(home), RUST_LOG="error")
    snaps: list = []
    steps: list = []
    markers = ["【第1轮】", "【第2轮】", "【第3轮】", "【第4轮】", "【第5轮】", "【第6轮】", "【第7轮】"]

    def start_server():
        s = AppServer(args.codex, env, str(ws), out / "rpc.log")
        s.call("initialize", {"clientInfo": {"name": "u09", "version": "0"}, "capabilities": {"experimentalApi": True}})
        s.send({"method": "initialized"})
        return s

    def say(s, tid, label, text):
        State.label = label
        n0 = State.n
        t0 = time.time()
        r = s.call("turn/start", {"threadId": tid, "input": [{"type": "text", "text": text, "text_elements": []}]})
        turn_id = r["turn"]["id"]
        notes, status, err, done = [], None, None, False
        end = time.time() + args.turn_timeout
        while time.time() < end:
            try:
                msg = s.notifs.get(timeout=1)
            except queue.Empty:
                continue
            m, p = msg.get("method"), msg.get("params", {})
            if m == "turn/completed" and p.get("turn", {}).get("id") == turn_id:
                t = p["turn"]
                status, err, done = t.get("status"), t.get("error"), True
                break
            notes.append(m)
        if not done:
            status = "timeout→interrupt"
            try:
                s.call("turn/interrupt", {"threadId": tid, "turnId": turn_id}, timeout=20)
            except Exception as e:  # noqa
                status += f" ({e})"
            time.sleep(1)
        reqs = [r for r in State.log if r["n"] > n0]
        counts = {}
        for r in reqs:
            key = f'{r["kind"]}:{r["outcome"]}'
            counts[key] = counts.get(key, 0) + 1
        notes_count = {}
        for m in notes:
            notes_count[m] = notes_count.get(m, 0) + 1
        steps.append({"label": label, "thread": tid, "turn": turn_id, "status": status, "error": err,
                      "seconds": round(time.time() - t0, 1), "requests": counts, "notifications": notes_count})
        return turn_id

    a = start_server()
    r = a.call("thread/start", {"cwd": str(ws), "model": args.model})
    T = r["thread"]["id"]
    steps.append({"label": "start", "thread": T})

    if args.scenario == "bigmsg":
        early = "EARLY-FILLER " * (args.early_tokens * 4 // 13)
        say(a, T, "t1", "【第1轮】我叫 Drake。规则：不要改数据库 schema。" + early)
        say(a, T, "t2", "【第2轮】代号是 BLUE。" + early)
        snap(home, "t2 之后", snaps, markers)
        big = "【第3轮】" + "日志行内容" * (args.big_chars // 5)
        steps.append({"label": "big-message", "chars": len(big), "utf8_bytes": len(big.encode()),
                      "est_tokens": est_tokens(len(big.encode()))})
        t3 = say(a, T, "t3-big", big)
        snap(home, "大消息那一轮之后", snaps, markers)
        say(a, T, "t4", "【第4轮】继续。")
        snap(home, "t4 之后", snaps, markers)
        say(a, T, "t5", "【第5轮】再说一句。")
        if args.manual_compact:
            State.label = "manual-compact"
            n0 = State.n
            a.call("thread/compact/start", {"threadId": T})
            end = time.time() + args.turn_timeout
            status = "timeout"
            while time.time() < end:
                try:
                    msg = a.notifs.get(timeout=1)
                except queue.Empty:
                    continue
                if msg.get("method") == "turn/completed" and msg["params"].get("threadId") == T:
                    status = msg["params"]["turn"].get("status")
                    break
            time.sleep(1)
            counts = {}
            for r in State.log:
                if r["n"] > n0:
                    key = f'{r["kind"]}:{r["outcome"]}'
                    counts[key] = counts.get(key, 0) + 1
            steps.append({"label": "manual-compact", "status": status, "requests": counts})
            snap(home, "手动压缩之后", snaps, markers)
            say(a, T, "t5b-after-manual-compact", "【第5轮后】手动压缩之后说一句。")
        a.close()
        b = start_server()
        b.call("thread/resume", {"threadId": T})
        say(b, T, "t6-resume", "【第6轮】新进程恢复后说一句。")
        snap(home, "新进程恢复并说一句之后", snaps, markers)
        try:
            b.call("thread/revert", {"threadId": T, "beforeTurnId": t3})
            steps.append({"label": "revert", "beforeTurnId": t3})
            say(b, T, "t7-after-revert", "【第7轮】回退到大消息之前，再说一句。")
        except Exception as e:  # noqa
            steps.append({"label": "revert", "error": str(e)})
        snap(home, "回退并说一句之后", snaps, markers)
        b.close()
    else:
        say(a, T, "t1-tools", "【第1轮】跑几步。")
        snap(home, "t1 之后", snaps, markers)
        say(a, T, "t2", "【第2轮】再说一句。")
        snap(home, "t2 之后", snaps, markers)
        a.close()

    (out / "snapshots.json").write_text(json.dumps(snaps, ensure_ascii=False, indent=1))
    (out / "steps.json").write_text(json.dumps(steps, ensure_ascii=False, indent=1))
    (out / "requests.json").write_text(json.dumps(State.log, ensure_ascii=False, indent=1))
    shutil.copytree(home / "sessions", out / "sessions")
    brief = [{k: r[k] for k in ("n", "label", "kind", "items", "est_tokens", "bytes", "outcome")} for r in State.log]
    print(json.dumps({"steps": steps, "requests": brief}, ensure_ascii=False, indent=1))
    server.shutdown()


if __name__ == "__main__":
    sys.exit(main())
