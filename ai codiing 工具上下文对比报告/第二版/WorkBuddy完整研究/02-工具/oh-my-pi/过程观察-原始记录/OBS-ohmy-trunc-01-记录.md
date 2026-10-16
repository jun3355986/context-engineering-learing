---
title: OBS-ohmy-trunc-01 · 原始记录（T08R 后补录）
task: T08（补录：T08R 复核后由 micro-fixer 代原作者执行 P5）
created: 2026-10-15
snapshot: f979f4639777858de28e6ecb99d577443abe0b7b
reused_workdir: /tmp/omp-obs（T08R 复核时的工作目录，仅存脚本与 node_modules，未存原始输出）
label: T08R 后补录、与包内记录一致
---

# OBS-ohmy-trunc-01 · 原始记录（T08R 后补录）

> **来源与性质**：本目录为 **P5（T08R 审查报告 §3）** 的证据留存补录。原观察见 `../过程观察.md §1`（OBS-ohmy-trunc-01），此前**仅有文字记录、无原始输出文件**。
> **复跑工作目录** `/tmp/omp-obs` 仍在，但其内**只有检查器脚本与 `node_modules`，未保存首轮原始 stdout/stderr**；故本次按包内方法**重跑一次**并保存原始 stdout/stderr + 退出码。
> **标注**：**T08R 后补录、与包内记录一致**——复跑输出与 `过程观察.md §1` 所载逐字一致（`outBytes=51174`、`RESULT: ALL_PASS`、`EXIT_CODE=0`）。本补录**未改变**任何结论，仅补证据文件。

## 1. 运行环境（复跑时采集）

| 项 | 值 |
|---|---|
| 日期 | 2026-10-15 01:52 CST |
| 运行时 | bun **1.3.9** |
| 被测包 | npm `@oh-my-pi/pi-tui@18.10.4`（`node_modules/@oh-my-pi/pi-tui/package.json` version=`18.10.4`） |
| 主机 | macOS 27.0.1 / arm64 |
| 工作目录 | `/tmp/omp-obs`（仓库外；未触碰只读快照 `workbuddy-sources/oh-my-pi/`） |

## 2. 命令

```bash
# 复跑（PASS 主记录）
cd /tmp/omp-obs && bun run check.ts

# 负例控制运行（证明判据能失败/返回 1）
cp <本目录>/OBS-ohmy-trunc-01-negative-control.ts /tmp/omp-obs/negative-control.ts
cd /tmp/omp-obs && bun run negative-control.ts
```

## 3. 复跑原始输出（PASS 主记录）

**文件**：`OBS-ohmy-trunc-01-run-PASS.stdout.txt`（stdout，逐字）/ `.stderr.txt`（空，0 字节）/ `.exitcode.txt`（`0`）

```text
constants: DEFAULT_MAX_LINES=3000 DEFAULT_MAX_BYTES=51200
[PASS] under-limit passthrough :: truncated=undefined contentUnchanged=true
[PASS] over-lines truncates to DEFAULT_MAX_LINES :: truncatedBy=lines outputLines=3000 totalLines=3500
[PASS] single line over byte cap -> firstLineExceedsLimit :: truncatedBy=bytes firstLineExceedsLimit=true outBytes=0
[PASS] CJK truncation keeps valid UTF-8 and within byte budget :: truncatedBy=bytes outBytes=51174 utf8Valid=true
RESULT: ALL_PASS
```

**退出码**：`0`（stderr 空）。**与包内记录一致**（`过程观察.md §1` 所载 `outBytes=51174` / `ALL_PASS` / `EXIT_CODE=0` 逐字相符）。

## 4. 负例控制运行原始输出（证明判据非"恒 0"）

> **说明**：本运行**不是**首轮真实失败那一跑的原始复现，而是对同一失败模式的**控制性重演**——首版 CJK 用例输入未到线、期望值却写成"应截断"（`过程观察.md §1` 已文字记录该首轮 `[FAIL]` / `EXIT_CODE=1`）。此处用同一 harness 复演该模式，以**留存可核验的 FAIL/退出码 1** 原始输出。

**文件**：`OBS-ohmy-trunc-01-run-FAIL.stdout.txt` / `.stderr.txt`（空）/ `.exitcode.txt`（`1`）；脚本 `OBS-ohmy-trunc-01-negative-control.ts`

```text
constants: DEFAULT_MAX_LINES=3000 DEFAULT_MAX_BYTES=51200
[FAIL] CJK under-limit but expected to truncate (deliberately wrong expectation) :: inputLines=200 inputBytes=7689 truncated=undefined truncatedBy=undefined
RESULT: 1 FAILURE(S)
```

**退出码**：`1`（stderr 空）。→ 判据非恒真：期望值与出货代码行为不符时，harness 如实报 `[FAIL]` 并返回 1。

## 5. 归因限制（沿用 `过程观察.md §1`，不扩大）

- 本观察为**函数级真实执行**（已发布 `@oh-my-pi/pi-tui@18.10.4` 的 `truncateHead` 出货代码），**不等于** oh-my-pi 产品入口 `omp` 端到端验证（`omp` 未安装）。
- **只**用于佐证 `ohmy-trunc-01` 的**出货常量与函数行为**；**不外推**到快照 `f979f46` main 的其余行号。
- 不涉及模型，故无"变化来自模型"的归因风险；也**不证明**产品侧各工具调用传入的默认参数。
- 仅合成数据；未读真实项目/凭据；未修改只读快照。

## 6. 文件清单

| 文件 | 说明 |
|---|---|
| `OBS-ohmy-trunc-01-check.ts` | 检查器脚本（4 断言 + 负例，逐字复制自 `/tmp/omp-obs/check.ts`） |
| `OBS-ohmy-trunc-01-run-PASS.stdout.txt` | 复跑 stdout（逐字） |
| `OBS-ohmy-trunc-01-run-PASS.stderr.txt` | 复跑 stderr（空） |
| `OBS-ohmy-trunc-01-run-PASS.exitcode.txt` | 复跑退出码（`0`） |
| `OBS-ohmy-trunc-01-negative-control.ts` | 负例控制脚本（复演"错误期望 → FAIL"模式） |
| `OBS-ohmy-trunc-01-run-FAIL.stdout.txt` | 负例控制 stdout（逐字） |
| `OBS-ohmy-trunc-01-run-FAIL.stderr.txt` | 负例控制 stderr（空） |
| `OBS-ohmy-trunc-01-run-FAIL.exitcode.txt` | 负例控制退出码（`1`） |
