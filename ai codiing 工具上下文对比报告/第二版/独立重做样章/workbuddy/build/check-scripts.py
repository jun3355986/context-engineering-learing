#!/usr/bin/env python3
"""提取交互教程 HTML 内全部 <script> 块并逐块做 node 语法检查。"""
import re, os, subprocess, sys, tempfile

HTML = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Codex CLI 上下文管理-交互教程.html")
NODE = "/Users/junjielong/.workbuddy/binaries/node/versions/22.22.2-6/bin/node"

html = open(HTML, encoding="utf-8").read()
scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
print(f"script 块数：{len(scripts)}")
fail = 0
with tempfile.TemporaryDirectory() as d:
    for i, s in enumerate(scripts):
        p = os.path.join(d, f"s{i}.js")
        open(p, "w", encoding="utf-8").write(s)
        r = subprocess.run([NODE, "--check", p], capture_output=True, text=True)
        ok = r.returncode == 0
        print(f"S{i}: {'OK' if ok else 'FAIL'}")
        if not ok:
            fail += 1
            print(r.stderr[:500])
print("=== 全部通过 ===" if fail == 0 else f"=== {fail} 个失败 ===")
sys.exit(1 if fail else 0)
