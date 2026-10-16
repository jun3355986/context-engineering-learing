---
title: 任务卡 T13 · deepseek-harness 研究包
task: T13
role: 工具研究 Agent
status: READY（待名额派发）
issued: 2026-10-15
---

# 任务卡 T13 · deepseek-harness 研究包

## 派发单（按任务书 §6 模板）

**任务ID**：T13
**角色**：工具研究
**目标**：按《T07-后六工具样本规范》完成 deepseek-harness 研究包（六件套）；§4.1 十二机制覆盖表（dsh 列）。核心纪律：**分清 harness 实现与 DeepSeek 模型/API 能力**（任务书 FB-07）——凡模型侧行为不得当 harness 实现写入。

**前置（均已 ACCEPTED/通过）**：
- T01：身份见 `00-管理/版本表.md` §1/§5——仓库 `deepseek-ai/deepseek-harness`，CLI 命令名 **`dsh`**，口号「AGENT = MODEL + HARNESS」；快照 `workbuddy-sources/deepseek-harness/`（SHA 以版本表 §5 为准，开工先核对）；release 口径注意：**27 个全为 prerelease、无 stable**（T01 修正后口径）。
- T02：问题地图 + 术语表；**T07《后六工具样本规范》**（规范优先）。
- T08 经验 4 条；T09R 教训（同源≠零耦合）。
- T03（ACCEPTED）：`05-实验/T03/`；观察纪律 D9/D10。
- 背景补核：PyPI `deepseek-harness-sdk`（冲突表/交接 Q7——并入本包背景核实并给出结论）。

**写入（唯一授权）**：`WorkBuddy完整研究/02-工具/deepseek-harness/`；快照只读。

**产物**：六件套（结论ID `dsh-*`）+ **harness 实现 vs 模型/API 能力分列表**。

**完成条件**：
- 六件套符合样本规范（证据卡 7 字段含"不能证明"；12 机制全判定；数字带单位与角标；自述计数=实际）；
- 分列表逐条有依据（源码/官方文档各归其位）；FB-07 纪律贯穿；
- `deepseek-harness-sdk` 补核结论（存在性/与 CLI 关系/引用纪律）；
- 观察 ≤1 项（按 T03 规程；污染登记必填）或 `NOT_RUN` + 确切原因；
- 无"源码阅读冒充实验通过"；未决项登记。

**复核**：批次审查由主 Agent 调度（独立 Agent 回原始来源复核高风险主张）。

**回复**：交回模板（任务书 §6）+ 规范自检清单。
