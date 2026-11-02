#!/usr/bin/env python3
"""U11 实验：给一个具体场景设计上下文策略——把「迁移 12 个包」整段回放，比较几组设置。

场景（数字是我设的，不是任何真实项目的测量）：
  一个 monorepo 里要把 12 个包的日期库从 moment 迁到 date-fns，一个包一轮。每个包假「模型」依次：
    读文件 ×2（每次输出 --read-bytes）→ 跑测试，失败（--fail-bytes）→ 再跑，通过（--pass-bytes）→ 回一句话。
  所有「工具输出」都是 exec（代码模式）里的 JS 自己生成的文本，不执行任何命令，不联网，不花额度。
  假服务器按 input 各条 json.dumps 的 UTF-8 字节数 ÷ 4 向上取整估算 token，并把它当 usage 报回去，
  所以 Codex 的压缩判断是真的在跑（和 U09 同一做法）；服务器自己不设窗口上限。

设置组（--arm）：
  A  缺省
  B  model_auto_compact_token_limit = 100000（压缩线提前）
  C  tool_output_token_limit = 4000（进入历史的每条工具输出上限 4,800 token）
  F  model_post_turn_compact_threshold_percent = 40（一轮结束后，用量 ≥ 有效窗口的 40% 就压）
  D  每个包新开一个线程（thread/start），其余缺省
  G  C + F + [agents] enabled = false，一个线程做到底
  E  D + C + [agents] enabled = false
  P1 缺省，第 5 个包的话里贴一段 100,000 字节的 CI 日志；硬规则只写在第 1 句话里（AGENTS.md 里没有）
  P2 同 P1，硬规则写在 AGENTS.md 里（第 1 句话里没有）
每次请求记：序号、线程、第几个包、类型（user / after-tool / compact）、input 条数、估算 token、规则标记所在的条目。

用法：python3 -I u11_scenario.py --arm A --out /abs/path/out/A
"""
import argparse
import atexit
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
RULE = "RULE-NO-PUBLIC-API"
FIRST = "TASK-FIRST-MSG"
SUMMARY_TEXT = "SUMMARY-FROM-MOCK：已迁移的包见 git log；规则见 AGENTS.md。" + "（摘要凑数）" * 700  # 假摘要，约 13 KB ≈ 3.3k token（长度是我设的）

ARMS = {
    "A": {},
    "B": {"extra": "model_auto_compact_token_limit = 100000\n"},
    "C": {"extra": "tool_output_token_limit = 4000\n"},
    "F": {"extra": "model_post_turn_compact_threshold_percent = 40\n"},
    "D": {"per_pkg": True},
    "G": {"extra": "tool_output_token_limit = 4000\nmodel_post_turn_compact_threshold_percent = 40\n", "agents_off": True},
    "E": {"per_pkg": True, "extra": "tool_output_token_limit = 4000\n", "agents_off": True},
    "P1": {"paste": True, "rule_in": "first"},
    "P2": {"paste": True, "rule_in": "agents"},
}


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


def gen_js(prefix: str, nbytes: int) -> str:
    """代码模式里的一行 JS：生成约 nbytes 字节的多行文本（每行约 80 字节）。"""
    pad = "const d = moment().add(1, 'day').format('YYYY-MM-DD'); // x"
    n = max(1, nbytes // (len(prefix) + 1 + 5 + 1 + len(pad) + 1))
    return ('text(Array.from({length:%d},(_,i)=>"%s "+String(i).padStart(5,"0")+" %s").join("\\n"));\n'
            % (n, prefix, pad))


class State:
    steps_spec: list = []     # [(名字, 字节)]
    tool_done: dict = {}
    n = 0
    label = "init"
    log: list = []
    last_final = True
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
        meta = req.get("client_metadata") or {}
        with State.lock:
            State.n += 1
            n = State.n
            label = State.label
            after_final = State.last_final
        texts = [item_text(it) for it in inp]
        row = {"n": n, "label": label, "kind": kind, "thread": meta.get("thread_id", ""),
               "items": len(inp), "est_tokens": tokens, "bytes": len(body),
               "rule_in": [{"i": i, "type": kind_of(inp[i])} for i, t in enumerate(texts) if RULE in t],
               "first_in": [{"i": i, "type": kind_of(inp[i])} for i, t in enumerate(texts) if FIRST in t],
               "tool_outputs": sum(1 for it in inp if it.get("type") in ("function_call_output", "custom_tool_call_output")),
               "after_final": after_final if kind == "compact" else None}
        first_of_label = not any(r["label"] == label and r["kind"] != "compact" for r in State.log)
        after_compact = bool(State.log) and State.log[-1]["kind"] == "compact"   # 压缩之后的第一个请求：看留下了哪些条
        if kind == "compact" or first_of_label or after_compact:
            row["head"] = [{"i": i, "type": kind_of(it), "bytes": sizes[i], "text": texts[i][:50].replace("\n", " ")}
                           for i, it in enumerate(inp)]
        State.log.append(row)
        rid = f"resp_{n}"
        final = False
        if kind == "compact":
            items = [{"type": "message", "role": "assistant", "id": f"msg_{n}",
                      "content": [{"type": "output_text", "text": SUMMARY_TEXT}]}]
        elif State.tool_done.get(label, 0) < len(State.steps_spec):
            k = State.tool_done.get(label, 0)
            State.tool_done[label] = k + 1
            name, nbytes = State.steps_spec[k]
            items = [{"type": "custom_tool_call", "id": f"ctc_{n}", "call_id": f"call_{n}", "name": "exec",
                      "input": gen_js(f"{label} {name}", nbytes)}]
        else:
            final = True
            items = [{"type": "message", "role": "assistant", "id": f"msg_{n}",
                      "content": [{"type": "output_text", "text": f"REPLY-{label}：这个包迁完了，测试通过。"}]}]
        if kind != "compact":
            State.last_final = final
        events = [{"type": "response.created", "response": {"id": rid}}]
        events += [{"type": "response.output_item.done", "item": it} for it in items]
        events.append({"type": "response.completed", "response": {"id": rid, "usage": {
            "input_tokens": tokens, "input_tokens_details": None, "output_tokens": 10,
            "output_tokens_details": None, "total_tokens": tokens + 10}}})
        payload = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
        self._send(200, "text/event-stream", payload)


class AppServer:
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
            self.log.write(line[:1500] + ("…\n" if len(line) > 1500 else ""))
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--codex", default="codex")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--arm", choices=sorted(ARMS), default="A")
    ap.add_argument("--packages", type=int, default=12)
    ap.add_argument("--read-bytes", type=int, default=24_000)
    ap.add_argument("--fail-bytes", type=int, default=80_000)
    ap.add_argument("--pass-bytes", type=int, default=8_000)
    ap.add_argument("--paste-at", type=int, default=5, help="P1/P2：第几个包的话里贴日志")
    ap.add_argument("--paste-bytes", type=int, default=100_000)
    ap.add_argument("--turn-timeout", type=int, default=180)
    ap.add_argument("--out", required=True, help="输出目录（绝对路径）")
    args = ap.parse_args()
    arm = ARMS[args.arm]

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    State.steps_spec = [("read-1", args.read_bytes), ("read-2", args.read_bytes),
                        ("test-fail", args.fail_bytes), ("test-pass", args.pass_bytes)]
    State.log, State.tool_done = [], {}

    # 临时目录放在 out 的上一级（/home 下），不放 /tmp：/tmp 对 ubuntu 用户有配额，第一次跑 18 组留下约 748 MiB 把它占满了
    tmp = Path(tempfile.mkdtemp(prefix=".work-", dir=out.parent))
    atexit.register(shutil.rmtree, tmp, ignore_errors=True)  # 中途报错、被打断时也清掉
    home, ws = tmp / "home", tmp / "ws"
    home.mkdir()
    ws.mkdir()
    rule_line = f"{RULE}：不要改 public API 的导出签名。\n"
    agents = "# 迁移项目规则\n" + (rule_line if arm.get("rule_in", "agents") == "agents" else "（硬规则见第 1 句话）\n") \
        + "改完一个包就跑该包的测试。\n"
    (ws / "AGENTS.md").write_text(agents)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    top = f'''model = "{args.model}"
model_reasoning_effort = "low"
model_provider = "mock"
approval_policy = "never"
sandbox_mode = "read-only"
web_search = "disabled"
check_for_update_on_startup = false
{arm.get("extra", "")}'''
    tables = ""
    if arm.get("agents_off"):
        tables += "[agents]\nenabled = false\n"
    tables += f'''[analytics]
enabled = false
[model_providers.mock]
name = "mock"
base_url = "http://127.0.0.1:{port}/v1"
wire_api = "responses"
requires_openai_auth = false
[projects.'{ws}']
trust_level = "trusted"
'''
    (home / "config.toml").write_text(top + tables)
    env = dict(os.environ, CODEX_HOME=str(home), RUST_LOG="error")

    a = AppServer(args.codex, env, str(ws), out / "rpc.log")
    a.call("initialize", {"clientInfo": {"name": "u11", "version": "0"}, "capabilities": {"experimentalApi": True}})
    a.send({"method": "initialized"})

    steps = []
    last_usage = {}

    def say(tid, label, text):
        State.label = label
        State.last_final = True
        n0 = State.n
        t0 = time.time()
        r = a.call("turn/start", {"threadId": tid, "input": [{"type": "text", "text": text, "text_elements": []}]})
        turn_id = r["turn"]["id"]
        status, err, done = None, None, False
        end = time.time() + args.turn_timeout
        while time.time() < end:
            try:
                msg = a.notifs.get(timeout=1)
            except queue.Empty:
                continue
            m, p = msg.get("method"), msg.get("params", {})
            if m == "thread/tokenUsage/updated":
                last_usage[tid] = p.get("tokenUsage")
            if m == "turn/completed" and p.get("turn", {}).get("id") == turn_id:
                t = p["turn"]
                status, err, done = t.get("status"), t.get("error"), True
                break
        if not done:
            status = "timeout→interrupt"
            try:
                a.call("turn/interrupt", {"threadId": tid, "turnId": turn_id}, timeout=20)
            except Exception as e:  # noqa
                status += f" ({e})"
            time.sleep(1)
        time.sleep(0.5)  # 一轮结束后的压缩在 turn/completed 之后可能还有一个请求在路上
        reqs = [x for x in State.log if x["n"] > n0]
        counts = {}
        for x in reqs:
            counts[x["kind"]] = counts.get(x["kind"], 0) + 1
        steps.append({"label": label, "thread": tid, "status": status, "error": err,
                      "seconds": round(time.time() - t0, 1), "requests": counts})
        return status

    def new_thread():
        r = a.call("thread/start", {"cwd": str(ws), "model": args.model})
        return r["thread"]["id"]

    T = None if arm.get("per_pkg") else new_thread()
    for k in range(1, args.packages + 1):
        label = f"pkg-{k:02d}"
        if arm.get("per_pkg"):
            T = new_thread()
        if k == 1 or arm.get("per_pkg"):
            text = f"【{FIRST}】把 monorepo 里 12 个包的日期库从 moment 迁到 date-fns，一个包一个包做。映射表见 docs/migration.md。"
            if arm.get("rule_in") == "first":
                text += rule_line
            text += f"先做 {label}。"
        else:
            text = f"继续做 {label}。"
        if arm.get("paste") and k == args.paste_at:
            log = "".join(f"CI-LOG {i:05d} FAIL packages/{label}/src/date.test.ts expected 2026-11-02\n"
                          for i in range(args.paste_bytes // 70))
            text += "\n下面是 CI 的完整日志，你看看：\n" + log
        say(T, label, text)

    a.close()
    # 最后一次请求的完整条目摘要，另存
    (out / "requests.json").write_text(json.dumps(State.log, ensure_ascii=False, indent=1))
    (out / "steps.json").write_text(json.dumps({"arm": args.arm, "config": top + tables, "steps": steps,
                                                "last_usage": last_usage}, ensure_ascii=False, indent=1))
    shutil.copytree(home / "sessions", out / "sessions")
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({"arm": args.arm, "requests": len(State.log)}))
    server.shutdown()


if __name__ == "__main__":
    sys.exit(main())
