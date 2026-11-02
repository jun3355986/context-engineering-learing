#!/usr/bin/env python3
"""U10 实验 D：做对照用的几个命令行选项，实际起什么作用？

对同一个任务跑三次 `codex exec`（本机假服务器，不联网、不花额度），固定 CODEX_HOME 和工作目录路径：
  plain      codex exec --json -o <文件> …            看 --json 输出哪些事件、-o 写了什么、会话存档有没有
  ephemeral  codex exec --ephemeral --json …          看没有存档时还能拿到什么
  override   codex exec -c model_auto_compact_token_limit=50000 …  只看加了 -c 以后命令能正常跑完；
             -c 是否改变行为不在这里验证（假服务器报的用量是 0，触发不了压缩）
用法：python3 -I u10_cmd.py --out <绝对路径>
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("u10_repro", HERE / "u10_repro.py")
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)


def run(label, extra, out: Path, model):
    d = out / label
    d.mkdir(parents=True)
    ws, home = out / "ws", out / "home"
    for p in (ws, home):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    (ws / "AGENTS.md").write_text("# U10 实验用规则\n")
    repro.Handler.out_dir, repro.Handler.n = d, 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), repro.Handler)
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
    last = d / "last-message.txt"
    cmd = ["codex", "exec", "--skip-git-repo-check", "-C", str(ws), "--json", "-o", str(last)] + extra + ["帮我看下这个报错"]
    r = subprocess.run(cmd, env={**os.environ, "CODEX_HOME": str(home)}, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=120)
    server.shutdown()
    (d / "stdout.jsonl").write_text(r.stdout)
    events = [json.loads(l) for l in r.stdout.splitlines() if l.startswith("{")]
    sessions = sorted((home / "sessions").rglob("*.jsonl")) if (home / "sessions").exists() else []
    print(f"\n== {label}: {' '.join(extra) or '（无额外选项）'}")
    print(f"退出码 {r.returncode}；--json 输出 {len(events)} 个事件，类型依次：{[e.get('type') for e in events]}")
    for e in events:
        if e.get("type") == "turn.completed":
            print(f"turn.completed: {json.dumps(e, ensure_ascii=False)}")
    print(f"-o 文件：{last.read_text()!r}" if last.exists() else "-o 文件：没写")
    print(f"会话存档文件 {len(sessions)} 个", end="")
    if sessions:
        recs = [json.loads(l) for l in sessions[0].read_text().splitlines()]
        n_rec = sum(1 for x in recs if x["type"] == "token_usage_record")
        print(f"；其中 token_usage_record {n_rec} 条")
    else:
        print()
    print(f"服务器收到请求 {repro.Handler.n} 个")
    return events


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="gpt-6.1-sol")
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    run("plain", [], out, a.model)
    run("ephemeral", ["--ephemeral"], out, a.model)
    run("override", ["-c", "model_auto_compact_token_limit=50000"], out, a.model)


if __name__ == "__main__":
    main()
