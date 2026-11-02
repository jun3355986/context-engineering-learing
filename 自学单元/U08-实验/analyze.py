#!/usr/bin/env python3
"""汇总 U08 实验输出：python3 -I analyze.py <U08-实验/out 目录>

读 out/read、out/write、out/write-v1、out/write-nogen，打印：
  读路径：每个用例第一次请求的大小、记忆块在第几条、记忆块自己多大（按内容分段）、摘要被截成多大
  写路径：每次请求的种类、模型、思考级别、大小；memories 目录下生成了什么；数据库里的使用次数
"""
import json
import sys
from pathlib import Path


def parts_of(req_path: Path):
    r = json.loads(req_path.read_text())
    rows = []
    for i, it in enumerate(r["input"]):
        c = it.get("content")
        if isinstance(c, list):
            rows.append((i, it.get("role"), [len(p.get("text", "").encode()) for p in c]))
    return len(json.dumps(r, ensure_ascii=False).encode()), rows, r


def main():
    out = Path(sys.argv[1])
    base = None
    print("== 读路径（codex exec，gpt-6.1-sol，low）")
    rr = json.loads((out / "read" / "read-results.json").read_text())
    seen = json.loads((out / "read" / "seen.json").read_text())
    for name, v in rr.items():
        f = v["first"]
        if not f:
            continue
        label = name
        files = sorted((out / "read").glob(f"req-*-{label}-user.json"))
        files = [p for p in files if json.loads(p.read_text())["model"] == "gpt-6.1-sol"]
        nbytes, rows, _ = parts_of(files[0]) if files else (0, [], None)
        mem = [(i, p) for i, role, p in rows if f["memory_items"] and i == f["memory_items"][0]["i"]]
        if base is None:
            base = nbytes
        print(f"{name:32s} 请求 {nbytes:>7,} 字节 (比默认 {nbytes - base:+,})  "
              f"记忆块所在条目 {mem[0] if mem else '无'}  摘要槽 {f['summary_slots']}")
    print()
    print("== 写路径")
    for d in ("write", "write-v1", "write-nogen", "exec-source"):
        p = out / d / "seen.json"
        if not p.exists():
            continue
        print(f"-- {d}")
        for s in json.loads(p.read_text()):
            print(f"  #{s['n']} {s['label']:4s} {s['kind']:7s} {s['model']:14s} {s['effort']:6s} "
                  f"{s['bytes']:>7,} 字节 {s['input_items']} 条 {s['output_format'] or ''}")
        steps = json.loads((out / d / "steps.json").read_text())
        for x in steps:
            if "tree" in x:
                print("  ", x["label"], json.dumps(x["tree"], ensure_ascii=False))
        db = out / d / "memories-db.json"
        if db.exists():
            for k, v in json.loads(db.read_text()).items():
                if v and "stage1_outputs" in k:
                    for row in v:
                        print("   ", k, {c: row[c] for c in ("usage_count", "last_usage", "selected_for_phase2")})


if __name__ == "__main__":
    main()
