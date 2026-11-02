#!/usr/bin/env python3
"""U08 实验：新会话怎么「想起」跨会话记忆（Codex 的 memories 功能）。

两组场景，都用本机假 Responses 服务器（自定义通道 model_provider = "mock"，HTTP），
每个场景用全新的临时 CODEX_HOME，不联网、不登录、不消耗额度。

  --scenario read   读路径：预先在 CODEX_HOME 里放好 memory_summary.md，新开一个 `codex exec`，
                    抓第一次请求，看「记忆」以什么形式、放在哪、占多少字节、超长时怎么截。
                    用例：默认配置 / 打开 memories / 超长摘要 / 汉字摘要 / use_memories=false /
                    version=v2 / dedicated_tools / 换个目录再开 / 摘要改了之后 resume
  --scenario write  写路径：用 `codex app-server` 开线程（来源 vscode，才在「可被提炼」的来源里；
                    `codex exec` 的来源是 exec，不会被选中），说一句话 → 把这个线程在数据库里的
                    更新时间往前拨 2 小时（配置里 min_rollout_idle_hours 最小是 1）→ 再开第二个线程，
                    抓第一阶段（提炼）和第二阶段（合并）发给模型的请求，列 memories/ 下生成了什么。

假服务器：认出提炼请求（含 "Memory Writing Agent: Phase 1"）就回一段 JSON；认出合并请求
（含 "Memory Writing Agent: Phase 2"）回一句话（不改任何文件）；其余回 "REPLY-OK"。

  --scenario exec-source  同 write，但两个会话都用 `codex exec` 开（来源 exec）：看第二个会话开始时有没有提炼请求。

用法：python3 -I u08_memory.py --scenario read  --out /abs/path/out/read
      python3 -I u08_memory.py --scenario write --out /abs/path/out/write
"""
import argparse
import json
import os
import queue
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PHASE1_MARK = "Memory Writing Agent: Phase 1"
PHASE2_MARK = "Memory Writing Agent: Phase 2"
PHASE1_V2_MARK = "You are part of an agent memory system. Your job is to extract information"
PHASE2_V2_MARK = "Consolidate the supplied rollout summaries into `memory_summary.md`"
STAGE1_JSON = {
    "rollout_summary": "用户 Drake 说项目测试用 pnpm，不要用 npm。（假服务器写死的摘要）",
    "rollout_slug": "pnpm-rule",
    "raw_memory": "- 用户偏好：测试用 pnpm，不要用 npm。（假服务器写死的原始记忆）",
}


SEED_V2_SUMMARY = """v1

## User Profile
（实验预置）用户叫 Drake。

## User preferences
- （实验预置）测试用 pnpm，不要用 npm。

## General Tips
- （实验预置）无。

## What's in Memory
（实验预置）暂无条目。
"""


class State:
    out_dir: Path = Path(".")
    label = "init"
    n = 0
    seen: list = []
    lock = threading.Lock()
    cite_id = ""
    hold = 0.0  # 普通请求回复前先等几秒，给后台管线时间


def kind_of(body: bytes) -> str:
    text = body.decode("utf-8", "replace")
    if PHASE1_MARK in text or PHASE1_V2_MARK in text:
        return "phase1"
    if PHASE2_MARK in text or PHASE2_V2_MARK in text:
        return "phase2"
    return "user"


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
        kind = kind_of(body)
        with State.lock:
            State.n += 1
            n = State.n
            label = State.label
        (State.out_dir / f"req-{n:02d}-{label}-{kind}.json").write_text(
            json.dumps(req, ensure_ascii=False, indent=1))
        fmt = (req.get("text") or {}).get("format")
        State.seen.append({
            "n": n, "label": label, "kind": kind, "model": req.get("model"),
            "effort": (req.get("reasoning") or {}).get("effort"),
            "bytes": len(body), "input_items": len(req.get("input", [])),
            "has_instructions": bool(req.get("instructions")),
            "instructions_bytes": len(req.get("instructions") or ""),
            "output_format": fmt.get("type") if isinstance(fmt, dict) else None,
            "tools_top_level": len(req.get("tools") or []),
        })
        if kind == "user" and State.hold:
            time.sleep(State.hold)
        if kind == "phase1":
            v2 = PHASE1_V2_MARK in body.decode("utf-8", "replace")
            data = {k: v for k, v in STAGE1_JSON.items() if not (v2 and k == "raw_memory")}
            text = json.dumps(data, ensure_ascii=False)
        elif kind == "phase2":
            text = "已读完工作区差异。（假服务器：没有改任何文件）"
        elif State.cite_id and State.label == "s3":
            text = ("按记忆里的规则：测试用 pnpm。\n<oai-mem-citation>\n<citation_entries>\n"
                    "rollout_summaries/x.md:1-2|note=[测试用 pnpm]\n</citation_entries>\n<rollout_ids>\n"
                    f"{State.cite_id}\n</rollout_ids>\n</oai-mem-citation>")
        else:
            text = "REPLY-OK"
        rid = f"resp_{n}"
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


def config_text(model, port, ws_list, extra_top="", extra_tables=""):
    projects = "".join(f"[projects.'{w}']\ntrust_level = \"trusted\"\n" for w in ws_list)
    return f'''model = "{model}"
model_reasoning_effort = "low"
model_provider = "mock"
approval_policy = "never"
sandbox_mode = "read-only"
web_search = "disabled"
check_for_update_on_startup = false
{extra_top}
[analytics]
enabled = false
[model_providers.mock]
name = "mock"
base_url = "http://127.0.0.1:{port}/v1"
wire_api = "responses"
requires_openai_auth = false
{projects}{extra_tables}
'''


def start_mock(out):
    State.out_dir, State.n, State.seen, State.hold = out, 0, [], 0.0
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


# ---------------------------------------------------------------- read
def make_summary(kind: str) -> str:
    """kind: small / ascii-big / han-big。每行带行号，截断后能看出留下了哪几行。"""
    if kind == "small":
        return ("v1\n\n## User Profile\n用户叫 Drake，在学上下文管理。\n\n"
                "## User preferences\n- 测试用 pnpm，不要用 npm。\n")
    if kind == "ascii-big":  # 约 30,000 字节
        return "v1\n" + "".join(f"LINE-{i:04d} " + "x" * 51 + "\n" for i in range(1, 501))
    if kind == "han-big":  # 汉字，每个 3 字节；约 30,000 字节
        return "v1\n" + "".join(f"第{i:04d}行" + "测" * 29 + "\n" for i in range(1, 301))
    raise ValueError(kind)


def analyze_first_request(req_path: Path) -> dict:
    req = json.loads(req_path.read_text())
    body_bytes = len(json.dumps(req, ensure_ascii=False).encode())
    rows = []
    mem_items = []
    for i, it in enumerate(req.get("input", [])):
        txt = json.dumps(it, ensure_ascii=False)
        c = it.get("content")
        text = "".join(p.get("text", "") for p in c if isinstance(p, dict)) if isinstance(c, list) else ""
        has_mem = "MEMORY_SUMMARY BEGINS" in text or "## Memory" in text[:200] or "memories.instructions" in text
        rows.append({"i": i, "type": it.get("type"), "role": it.get("role"),
                     "bytes": len(txt.encode()), "head": text[:60].replace("\n", "\\n")})
        if has_mem:
            mem_items.append({"i": i, "role": it.get("role"), "text_bytes": len(text.encode()), "text": text})
    summary_lines = []
    for m in mem_items:
        t = m["text"]
        a = t.find("MEMORY_SUMMARY BEGINS")
        b = t.find("MEMORY_SUMMARY ENDS")
        if a >= 0 and b > a:
            summary_lines.append({"i": m["i"], "summary_bytes_in_block": len(t[a:b].encode())})
    whole = json.dumps(req, ensure_ascii=False)
    return {"request_bytes": body_bytes, "input_items": len(req.get("input", [])),
            "memory_items": [{k: v for k, v in m.items() if k != "text"} for m in mem_items],
            "summary_slots": summary_lines,
            "mentions_add_ad_hoc_note": "add_ad_hoc_note" in whole,
            "items": rows}


def run_read(args, out: Path):
    server, port = start_mock(out)
    cases = [
        # name, summary kind, extra_top, extra_tables, version dir, flags
        dict(name="r0-default", summary="small", features=False),
        dict(name="r1-on-small", summary="small", features=True),
        dict(name="r2-on-ascii-big", summary="ascii-big", features=True),
        dict(name="r3-on-han-big", summary="han-big", features=True),
        dict(name="r4-use-memories-false", summary="small", features=True, tables="[memories]\nuse_memories = false\n"),
        dict(name="r5-v2-small", summary="small", features=True, tables="[memories]\nversion = \"v2\"\n", vdir="memories_v2"),
        dict(name="r6-v2-han-big", summary="han-big", features=True, tables="[memories]\nversion = \"v2\"\n", vdir="memories_v2"),
        dict(name="r7-dedicated-tools", summary="small", features=True, tables="[memories]\ndedicated_tools = true\n"),
        dict(name="r8-other-cwd", summary="small", features=True, second_cwd=True),
        dict(name="r9-resume-after-edit", summary="small", features=True, resume_edit=True),
        dict(name="r10-ephemeral", summary="small", features=True, ephemeral=True),
    ]
    results = {}
    for c in cases:
        State.label = c["name"]
        tmp = Path(tempfile.mkdtemp(prefix="u08r-"))
        home, ws, ws2 = tmp / "home", tmp / "ws", tmp / "ws2"
        for d in (home, ws, ws2):
            d.mkdir()
        (ws / "AGENTS.md").write_text("# U08 实验用规则\n本目录是合成的实验目录。\n")
        vdir = c.get("vdir", "memories")
        (home / vdir).mkdir()
        (home / vdir / "memory_summary.md").write_text(make_summary(c["summary"]))
        top = ""
        tables = ("[features]\nmemories = true\n" if c["features"] else "") + c.get("tables", "")
        (home / "config.toml").write_text(config_text(args.model, port, [ws, ws2], top, tables))
        env = {**os.environ, "CODEX_HOME": str(home)}

        def run(prompt, cwd, *more, resume=False):
            cmd = [args.codex, "exec", "--skip-git-repo-check", "-C", str(cwd)]
            if c.get("ephemeral"):
                cmd.append("--ephemeral")
            cmd += ["resume", "--last"] if resume else []
            cmd.append(prompt)
            r = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                               timeout=120, cwd=str(cwd))
            if r.returncode != 0:
                print(c["name"], "退出码", r.returncode, r.stderr[-800:])
            return r

        before = State.n
        run("【R】你好，帮我看看测试怎么跑。", ws2 if c.get("second_cwd") else ws)
        first = sorted(out.glob(f"req-*-{c['name']}-user.json"))
        results[c["name"]] = {"requests": State.n - before,
                              "first": analyze_first_request(first[0]) if first else None}
        if c.get("resume_edit"):
            (home / vdir / "memory_summary.md").write_text(
                "v1\n\n## User Profile\nEDITED-AFTER-FIRST-RUN：摘要在第一次运行后被改过。\n")
            before2 = State.n
            State.label = c["name"] + "-resume"
            run("【R2】接着说。", ws, resume=True)
            second = sorted(out.glob(f"req-*-{c['name']}-resume-user.json"))
            results[c["name"] + "-resume"] = {
                "requests": State.n - before2,
                "first": analyze_first_request(second[0]) if second else None}
            # 原话里是否有旧/新摘要
            if second:
                t = second[0].read_text()
                results[c["name"] + "-resume"]["has_old_summary_text"] = "用户叫 Drake，在学上下文管理" in t
                results[c["name"] + "-resume"]["has_new_summary_text"] = "EDITED-AFTER-FIRST-RUN" in t
        shutil.rmtree(tmp, ignore_errors=True)
        print(c["name"], "done")
    server.shutdown()
    (out / "read-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    (out / "seen.json").write_text(json.dumps(State.seen, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------- write
class AppServer:
    """codex app-server 的 stdio JSON-RPC 客户端（同 U07）。"""

    def __init__(self, codex, env, cwd, log_path):
        self.proc = subprocess.Popen([codex, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=open(str(log_path) + ".err", "w"), env=env, cwd=cwd, text=True, bufsize=1)
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


def tree(root: Path):
    rows = []
    if not root.exists():
        return rows
    for p in sorted(root.rglob("*")):
        if ".git" in p.parts:
            continue
        if p.is_file():
            rows.append({"path": str(p.relative_to(root)), "bytes": p.stat().st_size})
    return rows


def run_write(args, out: Path):
    server, port = start_mock(out)
    tmp = Path(tempfile.mkdtemp(prefix="u08w-"))
    home, ws, ws2 = tmp / "home", tmp / "ws-a", tmp / "ws-b"
    for d in (home, ws, ws2):
        d.mkdir()
    (ws / "AGENTS.md").write_text("# U08 实验用规则（项目 A）\n")
    (ws2 / "AGENTS.md").write_text("# U08 实验用规则（项目 B）\n")
    tables = "[features]\nmemories = true\n[memories]\nmin_rollout_idle_hours = 1\n" + args.memories_extra
    (home / "config.toml").write_text(config_text(args.model, port, [ws, ws2], "", tables))
    env = dict(os.environ, CODEX_HOME=str(home), RUST_LOG=args.rust_log)
    steps = []
    if args.seed_v2_summary:
        # 假的合并智能体不会写文件；预先放一份合格的 v2 摘要，让第二阶段的校验能通过
        (home / "memories_v2").mkdir()
        (home / "memories_v2" / "memory_summary.md").write_text(SEED_V2_SUMMARY)

    def start_server(cwd, label):
        s = AppServer(args.codex, env, str(cwd), out / f"rpc-{label}.log")
        s.call("initialize", {"clientInfo": {"name": "u08", "version": "0"},
                              "capabilities": {"experimentalApi": True}})
        s.send({"method": "initialized"})
        return s

    def say(s, tid, label, text):
        State.label = label
        r = s.call("turn/start", {"threadId": tid, "input": [{"type": "text", "text": text, "text_elements": []}]})
        tu = r["turn"]["id"]
        s.wait_notif("turn/completed", lambda p: p["turn"]["id"] == tu, timeout=120)
        steps.append({"label": label, "thread": tid, "text": text})

    # ---- 线程 1（项目 A）
    a = start_server(ws, "a")
    t1 = a.call("thread/start", {"cwd": str(ws), "model": args.model})["thread"]["id"]
    say(a, t1, "s1", "【S1】我叫 Drake。项目规则：测试用 pnpm，不要用 npm。")
    time.sleep(3)
    a.close()
    steps.append({"label": "s1-memories-tree", "tree": {d: tree(home / d) for d in ("memories", "memories_v2")}})

    # ---- 把线程 1 的更新时间往前拨 2 小时（假装「过了两小时」）
    db = home / "state_5.sqlite"
    con = sqlite3.connect(db)
    cols = [r[1] for r in con.execute("PRAGMA table_info(threads)")]
    shift = 2 * 3600 * 1000
    sets = [f"{c} = {c} - {shift}" for c in ("updated_at_ms", "recency_at_ms") if c in cols]
    con.execute(f"UPDATE threads SET {', '.join(sets)} WHERE id = ?", (t1,))
    con.commit()
    row = con.execute("SELECT id, source, memory_mode, cwd, updated_at_ms FROM threads").fetchall()
    steps.append({"label": "threads-after-shift", "rows": [list(map(str, r)) for r in row], "shifted": sets})
    con.close()
    # 第二阶段成功后有 6 小时冷却（PHASE2_SUCCESS_COOLDOWN_SECONDS）；把第一次的完成时间也往前拨 7 小时
    for dbname in ("memories_1.sqlite", "memories_v2_1.sqlite"):
        if (home / dbname).exists():
            c2 = sqlite3.connect(home / dbname)
            n = c2.execute("UPDATE jobs SET finished_at = finished_at - ? WHERE kind = 'memory_consolidate_global' "
                           "AND finished_at IS NOT NULL", (7 * 3600,)).rowcount
            c2.commit()
            c2.close()
            steps.append({"label": "age-phase2-job", "db": dbname, "rows": n})

    # ---- 线程 2（项目 B，另一个目录）：开始一轮会触发管线；假服务器把这一轮的回复拖几秒
    State.hold = args.hold
    b = start_server(ws2, "b")
    t2 = b.call("thread/start", {"cwd": str(ws2), "model": args.model})["thread"]["id"]
    say(b, t2, "s2", "【S2】新会话，换到项目 B。")
    # 等管线跑完（看到第二阶段请求后再多等几秒让它收尾），最多 40 秒
    p1 = [s["n"] for s in State.seen if s["kind"] == "phase1"]
    end = time.time() + 60
    while time.time() < end and not any(s["kind"] == "phase2" and p1 and s["n"] > p1[0] for s in State.seen):
        time.sleep(1)
    time.sleep(8)
    # ---- 第三句：假服务器的回答里带一段 <oai-mem-citation>，引用线程 1 的 id，看数据库里的使用次数
    State.hold = 0.0
    State.cite_id = t1
    say(b, t2, "s3", "【S3】测试怎么跑？")
    time.sleep(2)
    b.close()
    steps.append({"label": "after-s2-memories-tree", "tree": {d: tree(home / d) for d in ("memories", "memories_v2")}})
    # 把生成的文件拷出来
    for d in ("memories", "memories_v2"):
        if (home / d).exists():
            shutil.copytree(home / d, out / f"{d}-dir", ignore=shutil.ignore_patterns(".git"))
    dump = {}
    for dbname in ("memories_1.sqlite", "memories_v2_1.sqlite"):
        if not (home / dbname).exists():
            continue
        con = sqlite3.connect(home / dbname)
        tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
        for tname in tabs:
            if tname.startswith("sqlite_") or tname.startswith("_"):
                continue
            cur = con.execute(f"select * from {tname} limit 20")
            names = [d[0] for d in cur.description]
            dump[f"{dbname}:{tname}"] = [dict(zip(names, map(lambda v: v if isinstance(v, (int, float, type(None))) else str(v)[:300], r)))
                                         for r in cur.fetchall()]
        con.close()
    (out / "memories-db.json").write_text(json.dumps(dump, ensure_ascii=False, indent=1))
    server.shutdown()
    (out / "steps.json").write_text(json.dumps(steps, ensure_ascii=False, indent=1))
    (out / "seen.json").write_text(json.dumps(State.seen, ensure_ascii=False, indent=1))
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps(State.seen, ensure_ascii=False, indent=1))


def run_exec_source(args, out: Path):
    """用 codex exec 开两个会话（来源 exec），中间把第一个的更新时间拨早 2 小时：第二个会话开始时有没有提炼请求。"""
    server, port = start_mock(out)
    tmp = Path(tempfile.mkdtemp(prefix="u08x-"))
    home, ws = tmp / "home", tmp / "ws"
    for d in (home, ws):
        d.mkdir()
    tables = "[features]\nmemories = true\n[memories]\nmin_rollout_idle_hours = 1\n"
    (home / "config.toml").write_text(config_text(args.model, port, [ws], "", tables))
    env = {**os.environ, "CODEX_HOME": str(home)}
    steps = []

    def run(prompt):
        return subprocess.run([args.codex, "exec", "--skip-git-repo-check", "-C", str(ws), prompt], env=env,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120, cwd=str(ws))

    State.label = "x1"
    run("【X1】我叫 Drake。项目规则：测试用 pnpm。")
    time.sleep(2)
    con = sqlite3.connect(home / "state_5.sqlite")
    con.execute("UPDATE threads SET updated_at_ms = updated_at_ms - ?, recency_at_ms = recency_at_ms - ?",
                (2 * 3600 * 1000, 2 * 3600 * 1000))
    con.commit()
    steps.append({"label": "threads", "rows": [list(map(str, r)) for r in
                                              con.execute("SELECT id, source, memory_mode FROM threads")]})
    con.close()
    State.label = "x2"
    State.hold = 8.0
    run("【X2】新会话。")
    time.sleep(5)
    server.shutdown()
    (out / "steps.json").write_text(json.dumps(steps, ensure_ascii=False, indent=1))
    (out / "seen.json").write_text(json.dumps(State.seen, ensure_ascii=False, indent=1))
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({"steps": steps, "kinds": [(x["label"], x["kind"]) for x in State.seen]}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--codex", default="codex")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--scenario", choices=["read", "write", "exec-source"], required=True)
    ap.add_argument("--hold", type=float, default=15.0, help="write：普通请求回复前等几秒")
    ap.add_argument("--rust-log", default="error", help="write：app-server 的 RUST_LOG，日志在 rpc-*.log.err")
    ap.add_argument("--seed-v2-summary", action="store_true", help="write：预先放一份合格的 v2 memory_summary.md")
    ap.add_argument("--memories-extra", default="", help="write：追加到 [memories] 表里的几行")
    ap.add_argument("--out", required=True, help="输出目录（绝对路径）")
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    {"read": run_read, "write": run_write, "exec-source": run_exec_source}[args.scenario](args, out)


if __name__ == "__main__":
    sys.exit(main())
