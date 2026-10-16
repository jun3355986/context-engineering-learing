#!/usr/bin/env python3
# 提取 HTML 中的 <script> 块并逐个语法检查（调用 node --check），同时检查重复 ID。
import re, subprocess, sys, os, tempfile, collections

html_path = sys.argv[1]
node = sys.argv[2]
html = open(html_path, encoding="utf-8").read()

# 1) 提取 script 块（内联脚本，无 src）
blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
print(f"内联 script 块：{len(blocks)}")
fails = 0
for i, b in enumerate(blocks, 1):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(b)
        p = f.name
    r = subprocess.run([node, "--check", p], capture_output=True, text=True)
    if r.returncode != 0:
        fails += 1
        print(f"  [FAIL] 块 {i}: {r.stderr.strip()[:300]}")
    else:
        print(f"  [OK]   块 {i}")
    os.unlink(p)

# 2) 重复 ID（先剔除 <script>/<style> 内容，避免命中 JS 字符串如 var id="intro"）
html_markup = re.sub(r"<script\b.*?</script>", "", html, flags=re.S)
html_markup = re.sub(r"<style\b.*?</style>", "", html_markup, flags=re.S)
ids = re.findall(r'\bid="([^"]+)"', html_markup)
dups = [k for k, v in collections.Counter(ids).items() if v > 1]
print(f"ID 总数：{len(ids)}；重复：{dups if dups else '无'}")

# 3) 标签配对粗检（div/section）
for tag in ["div", "section", "table", "details"]:
    o = len(re.findall(rf"<{tag}[\s>]", html))
    c = len(re.findall(rf"</{tag}>", html))
    print(f"<{tag}> 开 {o} / 闭 {c} {'OK' if o == c else '❌ 不匹配'}")

# 4) 外部依赖检查（离线可用）
ext = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
print(f"外部资源引用（http/https）：{len(ext)}")
for e in set(ext):
    print("   ", e)

sys.exit(1 if fails else 0)
