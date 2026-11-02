#!/usr/bin/env python3
"""U07 实验：分叉（fork）、回退（revert）、恢复（resume）各自在磁盘和请求里留下什么。

做法：本机起假 Responses 服务器（自定义通道 model_provider = "mock"，HTTP），
用 `codex app-server`（stdio JSON-RPC）直接发 thread/start、turn/start、thread/fork、
thread/revert、thread/resume；这几个请求就是 TUI 里 /fork、Esc Esc 回退、codex resume 背后用的。
每一步之后列出 CODEX_HOME/sessions 下的会话文件（行数、字节、session_meta 的关键字段）。

剧本：
  进程 A：start → 第 1、2、3 轮（每轮一句话，假服务器回一句话）
          → fork（lastTurnId = 第 2 轮）→ 在分叉线程上说一句
          → revert（beforeTurnId = 第 2 轮）→ 在原线程上说一句
  然后改工作目录里的 AGENTS.md，进程 B：resume 原线程 → 再说一句
假服务器每次请求存成 req-NN-标签.json；seen.json 是摘要。不联网、不登录、不消耗额度。
不执行任何命令，所以不需要 --sandbox danger-full-access。

用法：python3 -I u07_thread.py --out /abs/path/out/default
"""
import argparse
import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


COMPACT_MARK = "CONTEXT CHECKPOINT COMPACTION"
SUMMARY_TEXT = "SUMMARY-FROM-MOCK：用户叫 Drake；规则是不要改数据库 schema；代号 BLUE。"


class State:
    label = "init"
    n = 0
    seen: list = []
    out_dir: Path = Path(".")
    lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if not self.path.rstrip("/").endswith("/responses"):
            self.send_response(404)
            self.end_headers()
            return
        req = json.loads(body)
        inp = req.get("input", [])
        last = inp[-1] if inp else {}
        lc = last.get("content")
        last_text = "".join(p.get("text", "") for p in lc if isinstance(p, dict)) if isinstance(lc, list) else ""
        is_compact = COMPACT_MARK in last_text
        with State.lock:
            State.n += 1
            n = State.n
            label = State.label + ("-compact-request" if is_compact else "")
        (State.out_dir / f"req-{n:02d}-{label}.json").write_text(json.dumps(req, ensure_ascii=False, indent=1))
        State.seen.append({"n": n, "label": label, "input_items": len(req.get("input", [])),
                           "bytes": len(body), "prompt_cache_key": req.get("prompt_cache_key")})
        rid = f"resp_{n}"
        text = SUMMARY_TEXT if is_compact else f"REPLY-{label}：好的。"
        items = [{"type": "message", "role": "assistant", "id": f"msg_{n}",
                  "content": [{"type": "output_text", "text": text}]}]
        events = [{"type": "response.created", "response": {"id": rid}}]
        events += [{"type": "response.output_item.done", "item": it} for it in items]
        events.append({"type": "response.completed", "response": {"id": rid, "usage": {
            "input_tokens": 1000, "input_tokens_details": None, "output_tokens": 10,
            "output_tokens_details": None, "total_tokens": 1010}}})
        payload = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class AppServer:
    """codex app-server 的 stdio JSON-RPC 客户端。"""

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
            self.log.write(line)
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

    def call(self, method, params, timeout=60):
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

    def wait_notif(self, method, pred=lambda p: True, timeout=60):
        import time
        end = time.time() + timeout
        while time.time() < end:
            try:
                msg = self.notifs.get(timeout=1)
            except queue.Empty:
                continue
            if msg.get("method") == method and pred(msg.get("params", {})):
                return msg["params"]
        raise TimeoutError(method)

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


def snap(home: Path, label: str, store: list):
    """列出 sessions 下的 rollout 文件：行数、字节、session_meta 关键字段、出现过哪些标记。"""
    rows = []
    for p in sorted((home / "sessions").rglob("rollout-*.jsonl")):
        text = p.read_text()
        lines = text.splitlines()
        meta = {}
        if lines:
            try:
                meta = json.loads(lines[0]).get("payload", {})
            except ValueError:
                pass
        keys = {k: meta.get(k) for k in ("id", "forked_from_id", "forked_from_ordinal_exclusive",
                                         "history_mode", "history_base", "parent_thread_id") if k in meta}
        marks = [m for m in ("【第1轮】", "【第2轮】", "【第3轮】", "【分叉】", "【第4轮】", "【第5轮】") if m in text]
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
                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:16], "meta": keys,
                     "marks": marks, "types": kinds})
    store.append({"step": label, "files": rows})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--codex", default="codex")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--scenario", choices=["basic", "compact", "revertk"], default="basic",
                    help="basic: 分叉/回退/恢复；compact: 压缩之后再回退；revertk: 3 轮后回退到第 k 轮之前（--k）")
    ap.add_argument("--k", type=int, default=2, help="revertk：回退到第 k 轮之前（1–3）")
    ap.add_argument("--out", required=True, help="输出目录（绝对路径）")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    State.out_dir = out

    tmp = Path(tempfile.mkdtemp(prefix="u07-"))
    home, ws = tmp / "home", tmp / "ws"
    home.mkdir()
    ws.mkdir()
    (ws / "AGENTS.md").write_text("# U07 实验用规则\nOLD-RULE：本目录是合成的实验目录。\n")
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    (home / "config.toml").write_text(f'''model = "{args.model}"
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
''')
    env = dict(os.environ, CODEX_HOME=str(home), RUST_LOG="error")
    snaps: list = []
    steps: list = []

    def start_server():
        s = AppServer(args.codex, env, str(ws), out / "rpc.log")
        s.call("initialize", {"clientInfo": {"name": "u07", "version": "0"},
                              "capabilities": {"experimentalApi": True}})
        s.send({"method": "initialized"})
        return s

    def say(s, tid, label, text):
        State.label = label
        r = s.call("turn/start", {"threadId": tid, "input": [{"type": "text", "text": text, "text_elements": []}]})
        turn_id = r["turn"]["id"]
        s.wait_notif("turn/completed", lambda p: p["turn"]["id"] == turn_id)
        steps.append({"label": label, "thread": tid, "turn": turn_id, "text": text})
        return turn_id

    if args.scenario == 'basic':
        # ---- 进程 A
        a = start_server()
        r = a.call("thread/start", {"cwd": str(ws), "model": args.model})
        T = r["thread"]["id"]
        steps.append({"label": "start", "thread": T, "history_mode": r["thread"].get("historyMode")})
        t1 = say(a, T, "t1", "【第1轮】我叫 Drake。规则：不要改数据库 schema。")
        snap(home, "t1 之后", snaps)
        t2 = say(a, T, "t2", "【第2轮】代号是 BLUE。")
        t3 = say(a, T, "t3", "【第3轮】再说一句。")
        snap(home, "t3 之后（3 轮）", snaps)

        f = a.call("thread/fork", {"threadId": T, "lastTurnId": t2})
        F = f["thread"]["id"]
        steps.append({"label": "fork", "from": T, "lastTurnId": t2, "new_thread": F,
                      "turns_in_response": len(f["thread"].get("turns", []))})
        snap(home, "fork（lastTurnId=第2轮）之后", snaps)
        say(a, F, "fork-say", "【分叉】在分叉里说一句。")
        snap(home, "在分叉里说一句之后", snaps)

        rv = a.call("thread/revert", {"threadId": T, "beforeTurnId": t2})
        steps.append({"label": "revert", "thread": T, "beforeTurnId": t2,
                      "thread_id_after": rv["thread"]["id"], "path_after": rv["thread"].get("path")})
        snap(home, "revert（beforeTurnId=第2轮）之后", snaps)
        say(a, T, "after-revert", "【第4轮】我叫什么？代号是什么？")
        snap(home, "回退后在原线程上说一句", snaps)
        a.close()

        # ---- 中途改 AGENTS.md，进程 B 恢复
        (ws / "AGENTS.md").write_text("# U07 实验用规则\nNEW-RULE：这一行是恢复之前才加的。\n")
        State.label = "resume"
        b = start_server()
        b.call("thread/resume", {"threadId": T})
        say(b, T, "resume-say", "【第5轮】恢复之后说一句。")
        snap(home, "恢复并说一句之后", snaps)
        b.close()
    elif args.scenario == "revertk":
        a = start_server()
        r = a.call("thread/start", {"cwd": str(ws), "model": args.model})
        T = r["thread"]["id"]
        ids = [say(a, T, "t1", "【第1轮】我叫 Drake。规则：不要改数据库 schema。"),
               say(a, T, "t2", "【第2轮】代号是 BLUE。"),
               say(a, T, "t3", "【第3轮】再说一句。")]
        snap(home, "3 轮之后", snaps)
        a.call("thread/revert", {"threadId": T, "beforeTurnId": ids[args.k - 1]})
        steps.append({"label": "revert", "k": args.k, "beforeTurnId": ids[args.k - 1]})
        snap(home, f"回退到第 {args.k} 轮之前", snaps)
        say(a, T, f"after-revert-k{args.k}", "【第4轮】我叫什么？代号是什么？")
        snap(home, "回退后说一句", snaps)
        a.close()
    else:
        a = start_server()
        r = a.call("thread/start", {"cwd": str(ws), "model": args.model})
        T = r["thread"]["id"]
        t1 = say(a, T, "t1", "【第1轮】我叫 Drake。规则：不要改数据库 schema。")
        t2 = say(a, T, "t2", "【第2轮】代号是 BLUE。")
        t3 = say(a, T, "t3", "【第3轮】再说一句。")
        snap(home, "3 轮之后", snaps)
        State.label = "compact"
        a.call("thread/compact/start", {"threadId": T})
        a.wait_notif("turn/completed", lambda p: p.get("threadId") == T)  # 压缩本身也是一个 turn（item 类型 contextCompaction）
        import time
        time.sleep(1)
        turns = a.call("thread/turns/list", {"threadId": T, "limit": 50, "sortDirection": "asc"})
        steps.append({"label": "turns-after-compact", "turns": [
            {"id": t["id"], "status": t.get("status"), "items": [i.get("type") for i in t.get("items", [])]}
            for t in turns["data"]]})
        snap(home, "压缩之后", snaps)
        t4 = say(a, T, "after-compact-t4", "【第4轮】压缩之后说一句。")
        t5 = say(a, T, "after-compact-t5", "【第5轮】再说一句。")
        snap(home, "压缩后又说两句", snaps)
        # 回退到压缩之后的某一轮之前：压缩还在
        a.call("thread/revert", {"threadId": T, "beforeTurnId": t5})
        say(a, T, "revert-after-compact", "【第6轮】回退到第 5 轮之前，压缩还在吗？")
        # 回退到压缩之前：压缩被撤销？找压缩那一轮的 id
        comp = [t["id"] for t in turns["data"] if t["id"] not in (t1, t2, t3)]
        steps.append({"label": "compaction-turn-ids", "ids": comp})
        before = comp[0] if comp else t3
        a.call("thread/revert", {"threadId": T, "beforeTurnId": before})
        say(a, T, "revert-before-compact", "【第7轮】回退到压缩之前，原话回来了吗？")
        snap(home, "回退到压缩之前再说一句", snaps)
        a.close()

    (out / "snapshots.json").write_text(json.dumps(snaps, ensure_ascii=False, indent=1))
    (out / "steps.json").write_text(json.dumps(steps, ensure_ascii=False, indent=1))
    (out / "seen.json").write_text(json.dumps(State.seen, ensure_ascii=False, indent=1))
    # 把会话文件原样拷一份
    shutil.copytree(home / "sessions", out / "sessions")
    print(json.dumps({"steps": steps, "seen": State.seen}, ensure_ascii=False, indent=1))
    server.shutdown()


if __name__ == "__main__":
    sys.exit(main())
