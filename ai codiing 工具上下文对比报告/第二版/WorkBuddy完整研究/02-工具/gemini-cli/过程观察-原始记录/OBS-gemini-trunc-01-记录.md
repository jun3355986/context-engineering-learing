# OBS-gemini-trunc-01 · 运行记录

| 项 | 值 |
|---|---|
| 观察 ID | OBS-gemini-trunc-01 |
| 对象 | Gemini CLI 出货源码（只读快照） |
| 快照 SHA | `42c51822084ac25cd5d97ac0023822c5235f88c8`（main，`git status` 干净） |
| 入口自报版本 | **无**（产品入口未安装；观察对象为快照源码） |
| 运行时 | bun 1.3.9 |
| 依赖 | 快照未安装 node_modules；仅相对导入 + 纯函数，无第三方包 |
| 污染登记 | 无第三方扩展/hook/provider/软链；未联网 |
| 日期 | 2026-10-15 |

## 运行 1（正向）

```
$ bun run OBS-gemini-trunc-01-check.ts
（28 条断言全 PASS）
ALL PASS
EXIT_CODE=0
```

原始输出：`OBS-gemini-trunc-01-run-PASS.stdout.txt`（stdout）、`OBS-gemini-trunc-01-run-PASS.stderr.txt`（stderr，空）、`OBS-gemini-trunc-01-run-PASS.exitcode.txt`（`0`）。

## 运行 2（负例对照）

```
$ bun run OBS-gemini-trunc-01-negative-control.ts
FAIL | 负例① est([ab]) 故意断言=1 | actual=0 expected=1
FAIL | 负例② MIN_TARGET_TOKENS 故意断言=11 | actual=10 expected=11
负例合计 FAIL 数=2（期望 2）
NEGATIVE-CONTROL OK: 判据能报错
EXIT_CODE=1
```

原始输出：`OBS-gemini-trunc-01-run-NEG.stdout.txt` / `.stderr.txt` / `.exitcode.txt`（`1`）。

## 判据结论

- 正向 `EXIT_CODE=0`（全 PASS）；负例 `EXIT_CODE=1`（判据能报错）→ **观察成立**。
- **不能证明**：产品端到端行为、服务端缓存、模型摘要保真度（详见 `../过程观察.md §1.5/§1.6`）。
