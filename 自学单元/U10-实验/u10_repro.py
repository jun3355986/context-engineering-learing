#!/usr/bin/env python3
"""U10 实验 A：同一个任务、同一份配置跑几次，请求体是不是逐字相同？不同在哪？

三次运行，全部用本机假服务器（不联网、不花额度），每次全新的 CODEX_HOME：
  run1  工作目录 <work>/armA/ws
  run2  工作目录 <work>/armB/ws   （同一任务，只换了目录路径）
  run3  工作目录 <work>/armA/ws   （run1 的路径，删掉重建）
每次让假服务器第一次回一个工具调用，所以每次运行有 2 个请求。
报告：每对运行里，哪些请求字节完全相同；不同的请求，不同的 JSON 路径和值；请求头里哪些每次都变。

用法：python3 -I u10_repro.py --out <绝对路径> [--work <绝对路径>]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    out_dir: Path
    n = 0

    def log_message(self, *_):
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
        Handler.n += 1
        n = Handler.n
        (self.out_dir / f"req-{n}.raw").write_bytes(body)
        heads = {k: v for k, v in self.headers.items()}
        (self.out_dir / f"req-{n}.headers.json").write_text(json.dumps(heads, ensure_ascii=False, indent=1))
        if n == 1:
            item = {"type": "function_call", "id": "fc_1", "call_id": "call_1", "namespace": "clock",
                    "name": "sleep", "arguments": json.dumps({"duration_ms": 1})}
        else:
            item = {"type": "message", "role": "assistant", "id": f"msg_{n}",
                    "content": [{"type": "output_text", "text": "MOCK_REPLY"}]}
        usage = {"input_tokens": 0, "input_tokens_details": None, "output_tokens": 0,
                 "output_tokens_details": None, "total_tokens": 0}
        events = [{"type": "response.created", "response": {"id": f"resp_{n}"}},
                  {"type": "response.output_item.done", "item": item},
                  {"type": "response.completed", "response": {"id": f"resp_{n}", "usage": usage}}]
        payload = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def run_once(label, ws: Path, out: Path, prompt, model, home_dir=None):
    d = out / label
    d.mkdir(parents=True)
    if home_dir:  # 固定 CODEX_HOME 路径：每次删掉重建，路径不变
        home = Path(home_dir)
        if home.exists():
            shutil.rmtree(home)
        home.mkdir(parents=True)
    else:  # 随机路径：技能目录的路径会写进请求，每次不同
        home = Path(tempfile.mkdtemp(prefix="u10-home-"))
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    (ws / "AGENTS.md").write_text("# U10 实验用规则\n本目录是合成的实验目录。\n")
    Handler.out_dir, Handler.n = d, 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    (home / "config.toml").write_text(f'''model = "{model}"
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
    cmd = ["codex", "exec", "--skip-git-repo-check", "-C", str(ws), prompt]
    r = subprocess.run(cmd, env={**os.environ, "CODEX_HOME": str(home)}, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=120)
    server.shutdown()
    if not home_dir:
        shutil.rmtree(home, ignore_errors=True)
    reqs = [json.loads(p.read_bytes()) for p in sorted(d.glob("req-*.raw"))]
    raws = [p.read_bytes() for p in sorted(d.glob("req-*.raw"))]
    heads = [json.loads(p.read_text()) for p in sorted(d.glob("req-*.headers.json"))]
    print(f"{label}: 退出码 {r.returncode}，请求 {len(reqs)} 个，字节 {[len(b) for b in raws]}")
    return reqs, raws, heads


def leaves(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, f"{path}[{i}]")
    else:
        yield path, x


def diff(a, b):
    la, lb = dict(leaves(a)), dict(leaves(b))
    out = []
    for k in sorted(set(la) | set(lb)):
        if la.get(k, "<无>") != lb.get(k, "<无>"):
            out.append((k, la.get(k, "<无>"), lb.get(k, "<无>")))
    return out


UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def mask(x):
    """把所有 UUID（会话号、轮次号、条目 id、安装号）换成 <uuid>，剩下的差别才是内容差别。"""
    return json.loads(UUID.sub("<uuid>", json.dumps(x, ensure_ascii=False)))


def middle(a, b, ctx=24):
    """两段不同的字符串：去掉相同的开头和结尾，只显示中间不同的部分。"""
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    e = 0
    while e < min(len(a), len(b)) - k and a[-1 - e] == b[-1 - e]:
        e += 1
    cut = lambda t: t[max(k - ctx, 0): len(t) - e + ctx].replace("\n", "\\n")
    return cut(a), cut(b)


def compare(name, A, B, lines):
    (ra, wa, ha), (rb, wb, hb) = A, B
    lines.append(f"\n## {name}")
    for i, (x, y) in enumerate(zip(wa, wb), 1):
        qa, qb = ra[i - 1], rb[i - 1]
        ma, mb = mask(qa), mask(qb)
        lines.append(f"请求 {i}：{len(x):,} / {len(y):,} 字节；字节完全相同：{x == y}；"
                     f"把 UUID 换成 <uuid> 之后完全相同：{ma == mb}")
        if ma == mb:
            continue
        ds = diff(ma, mb)
        lines.append(f"  换掉 UUID 之后还有 {len(ds)} 处不同：")
        for p, va, vb in ds:
            if isinstance(va, str) and isinstance(vb, str):
                va, vb = middle(va, vb)
            lines.append(f"    {p}\n      A: …{va}…\n      B: …{vb}…")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--prompt", default="帮我看下这个报错")
    ap.add_argument("--random-home", action="store_true", help="每次用随机路径的 CODEX_HOME（缺省：固定路径 <work>/home）")
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    work = Path(args.work) if args.work else Path(tempfile.mkdtemp(prefix="u10-work-"))
    hd = None if args.random_home else work / "home"
    r1 = run_once("run1-armA", work / "armA" / "ws", out, args.prompt, args.model, hd)
    r2 = run_once("run2-armB", work / "armB" / "ws", out, args.prompt, args.model, hd)
    r3 = run_once("run3-armA-again", work / "armA" / "ws", out, args.prompt, args.model, hd)
    lines = [f"工作目录：armA = {work / 'armA' / 'ws'}；armB = {work / 'armB' / 'ws'}"]
    compare("run1 vs run3：同一路径、同一任务、各自全新 CODEX_HOME", r1, r3, lines)
    compare("run1 vs run2：只换工作目录路径", r1, r2, lines)
    (out / "report.txt").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
