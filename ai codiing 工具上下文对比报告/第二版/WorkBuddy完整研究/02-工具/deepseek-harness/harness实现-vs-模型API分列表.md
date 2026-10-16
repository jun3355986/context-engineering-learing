---
title: deepseek-harness · harness 实现 vs 模型/API 能力分列表
task: T13
role: 工具研究 Agent
created: 2026-10-15
snapshot: 571902028a75c64c1d767f4ae5fd099485f0ddf0
spec: 08-验收/T07-后六工具样本规范.md · 任务书 FB-07
---

# harness 实现 vs 模型/API 能力分列表（FB-07 核心纪律）

> **本文件解决什么**：把 dsh 的每一条上下文主张**归位**到「**harness 实现**」或「**模型/API 能力**」，防止"API 支持某功能"被写成"dsh 默认启用"。
> **纪律**：凡**模型侧/服务端**行为，**不得**当 harness 实现写入；凡 harness 侧行为，须有源码/文档依据。
> **列义**：A=harness 实现（源码可证）；B=模型/API 能力（harness 仅声明/透传/读取）；C=边界（两侧交界，须分述）。

## 1. 逐条分列（20 项）

| # | 主张 | 归属 | harness 侧（A）依据 | 模型/API 侧（B）说明 |
|---|---|---|---|---|
| 1 | 请求由「config + 派生消息 + 工具」拼成，**无 `system` 字段** | **A** | `agent-loop/README#L120` | — |
| 2 | 系统提示词由 `system/message` 节点承载，取**最新非空** | **A** | `agent-loop/README#L75,156` | — |
| 3 | 工具增删发 `developer/message`（**与模型能力无关**） | **A** | `agent-loop/README#L156` | — |
| 4 | 提示词变更在 `in-history` 路由下**追加**在缓存历史后 | **A**（策略） | `agent-loop/README#L122,164` | 是否**真的命中**缓存 = **B**（服务端） |
| 5 | 上下文窗口 = **1,000,000 token** | **B** | harness 仅 `resolveModelInfo().context.contextWindow` **读取**（`llm-deepseek/README#L53,61`） | **模型/适配器声明**，非 harness 常量；`defaultContextWindow` 只是兜底 |
| 6 | 计量 = **4 字符/token** + block/role 结构开销 | **A** | `estimate.ts#L13,16,19`；OBS-dsh-meter-01 | 真实分词与**计费级 token** = **B** |
| 7 | CJK/JSON Schema **被低估** | **A**（启发式后果） | `token-meter/README#L68,154`；OBS 佐证 | 低估幅度取决于 provider 分词器 = **B** |
| 8 | 触发线 `floor(min(W×0.8, W−O−65536))` | **A** | `config.ts#L20,23,75,191-197` | 代入的 `W`、`O` 来自**适配器声明/配置** = **C** |
| 9 | 保留预算 `floor((W−O)×0.16)` | **A** | `config.ts#L195-197` | 同上（W/O 来自声明） |
| 10 | `auto` 默认 true；`compactionRetries`/`maxOverflowRetries` 默认 1 | **A** | `config.ts#L105-108` | — |
| 11 | 压缩事务（start→summary→replace→end，孤儿锁可检测） | **A** | `region.ts#L173-276,301-334` | — |
| 12 | 摘要 = **一次** `ctx.llm.stream()`，8 段结构化指令 | **A**（指令与调用） | `summarizer.ts#L32-67,120-181` | **摘要文本由模型生成**；**质量/漂移 = B** |
| 13 | 收缩校验（摘要须小于被遮蔽段） | **A** | `region.ts#L417-422` | 价格含 route 价（受 provider 定价影响）= **C** |
| 14 | 替换语义（`surfaceOp.replace`），恢复走持久化断点 | **A** | `region.ts#L506-509`；`agent-loop/README#L114-116` | — |
| 15 | 工具输出上限（read 2000 行/51200 字节；bash 16000 字符） | **A** | `tool-fs/README#L65-67`；`tool-bash-persistent/README#L50` | — |
| 16 | 落盘 `spill-policy`（`maxInlineTokens` 默认 12500） | **A** | `spill-policy/README#L43`；`cordis.patch.yml#L417` | — |
| 17 | 压缩前剪裁 pruner（8192/4096/1024，按 code point） | **A** | pruner `config.ts#L7,10-14,27-29` | — |
| 18 | 缓存 usage 字段映射（`cache_read/creation_input_tokens`→`cacheRead/WriteTokens`） | **A**（映射） | `translate.ts#L36,159`；`llm/src/types.ts#L174-188` | **数值与命中/TTL = B**（服务端上报，UNOBSERVABLE） |
| 19 | 溢出分类 `CONTEXT_WINDOW_EXCEEDED` 与恢复流程 | **A**（归一化与流程） | `index.ts#L190-234` | **溢出的真实判定与措辞 = B**（"provider wording can change"） |
| 20 | 图像离载 `image/offload`（占位符 + 重试） | **A**（决策） | `docs/subsystems/compaction.md#L25-38` | **视觉 token 定价网格/上传删除 = B**（14px patch/3:1/1024 上限） |

## 2. 一句话边界

- **dsh 的上下文治理全在 harness**：组装、计量口径、阈值、事务、剪裁、落盘、持久化、交接、重试、图像离载决策。
- **模型/API 只提供**：容量（窗口）、真实分词与计费、缓存存储与命中/TTL、溢出真实判定、视觉定价、推理内容。
- **三条最易误写的边界**：
  1. **窗口 1,000,000** 是**模型/适配器声明**，不是 harness 常量；harness 只**读取**并代入公式。
  2. **缓存**：harness 只做**字段映射 + 前后缀策略**；**"API 支持缓存" ≠ "dsh 默认命中缓存"**，命中率/TTL **不可观测**。
  3. **摘要**：**事务与指令**是 harness；**摘要文本与保真度**是模型侧（须 T19）。

## 3. 与旧结论/术语表的衔接

- 术语表 §6「缓存键 = 已证（CLI 侧）」在 **dsh 侧不成立**：**未发现** CLI 侧缓存键/断点（`dsh-cache-02`，S4=1 为 Codex 测试样本）。dsh 只有 **usage 明细字段**。
- 术语表 §2「自动整理限额 = 模型元数据字段 M」是 **Codex** 口径；**dsh 无 M**——dsh 用**双上限公式**（比例 ∧ 容量预留），**不得**套用 Codex 的 M 叙事。
- 术语表 §13「模型切换触发」：dsh 侧**未专门发现**"换模型触发压缩"入口（触发仅 `pressure`/`context-overflow`）——**推断**，范围限出货路径。

---
*配套：`工具概览.md §3`（速查表）/ `证据/dsh-证据卡.md`（`dsh-layer-01`）/ `问题与审查.md`。*
