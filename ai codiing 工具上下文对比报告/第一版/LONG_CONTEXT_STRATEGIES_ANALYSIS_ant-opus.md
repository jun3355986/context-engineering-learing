# AI 编码 Agent 长上下文管理策略深度分析

> **分析日期**: 2026-09-17
> **分析范围**: Pi (earendil-works)、OpenAI Codex CLI、Claude Code、Aider、Cursor、Gemini CLI
> **分析目标**: 理解主流 AI 编码 Agent 如何处理超长上下文，提炼可借鉴的设计模式

---

## 目录

- [一、核心问题：为什么长上下文需要管理](#一核心问题为什么长上下文需要管理)
- [二、Pi Agent — 会话树 + 扩展驱动的精细压缩](#二pi-agent--会话树--扩展驱动的精细压缩)
- [三、OpenAI Codex CLI — 三层 Compaction 架构](#三openai-codex-cli--三层-compaction-架构)
- [四、Claude Code — 五级渐进式压缩管道](#四claude-code--五级渐进式压缩管道)
- [五、其他工具对比：Aider / Cursor / Gemini CLI](#五其他工具对比aider--cursor--gemini-cli)
- [六、跨工具横向对比](#六跨工具横向对比)
- [七、关键设计模式总结](#七关键设计模式总结)
- [八、相关学术研究](#八相关学术研究)
- [九、2026 行业趋势](#九2026-行业趋势)
- [十、对本项目的启发](#十对本项目的启发)

---

## 一、核心问题：为什么长上下文需要管理

AI 编码 Agent 在长时间运行中面临几个关键瓶颈：

| 问题 | 表现 |
|------|------|
| **窗口溢出** | 对话 + 工具输出 + 文件内容超过模型上下文限制 → API 报错或静默丢弃信息 |
| **注意力退化** | 窗口塞满后，模型对早期信息的"记忆力"下降，准确率掉 |
| **噪声淹没信号** | 大量 grep/bash 输出挤占有价值的决策上下文 |
| **压缩信息损失** | 天真摘要可能丢失关键决策、把失败标记为成功（认知偏差） |
| **成本膨胀** | 每次 API 调用都发送完整历史 → token 费用线性增长 |

核心矛盾：**模型需要足够的上下文来做正确决策，但上下文太多反而降低质量和增加成本。**

---

## 二、Pi Agent — 会话树 + 扩展驱动的精细压缩

**仓库**: https://github.com/earendil-works/pi （MIT，TypeScript monorepo）

Pi 是一个极简终端原生编码 Agent，context 管理设计精细且可扩展。

### 2.1 Auto-Compaction 触发机制

触发公式：

```
contextTokens > model.contextWindow - reserveTokens
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `reserveTokens` | 16,384 | 预留给新生成内容的 token 空间 |
| `keepRecentTokens` | 20,000 | 从最新消息向前保留的 token 数 |

触发后：从最新消息向前回溯到 `keepRecentTokens` 阈值，对更旧的消息做**结构化 LLM 摘要**（非简单截断）。摘要保留：目标、决策、约束、文件操作等关键信息。

### 2.2 会话树架构（Session Tree） ⭐

Pi 最独特的设计——会话存储为**树结构**（类似 Git）：

```
Session Tree (Git-like)
────────────────────────

main trunk:  A ──► B ──► C ──► D ──► E
                         │
branch:                  └──► C' ──► C''
                                     │
sub-branch:                          └──► C'''
```

- 每个 entry 有 `uuid` 和 `parentUuid`，形成有向无环图
- 支持**分支/分叉**：创建"支线任务"，失败后回到主干，不丢失历史
- **非破坏性**：所有变更是 append-only 的 JSONL 文件，数据可恢复
- Compaction 是链上的标记（`firstKeptEntryUuid`），而非真正删除

**设计优势**：agent 可以放心探索不同方案。走错了？回到分叉点重来，而不是重开整个会话。

### 2.3 扩展驱动的 Context Pruning

Pi 的扩展系统可注册 "context event" 钩子，在发送 LLM 前修剪冗余：

| 扩展 | 功能 |
|------|------|
| `pi-context-prune` | 批量摘要工具结果，注入摘要替代原始数据（原始数据可通过 `context_tree_query` 查询） |
| `pi-ultra-compact` | 在会话中标记"锚点"（Checkpoint），维持关键上下文 |
| `pi-context` | Token 分布可视化仪表盘 + 缓存感知压缩（保持 prompt cache 热度） |

### 2.4 手动控制

| 命令 | 作用 |
|------|------|
| `/compact [instructions]` | 手动触发，可指导摘要重点 |
| `/autocompact` | 开关自动压缩 |

配置路径：`~/.pi/agent/settings.json` 或 `<project>/.pi/settings.json`

### 2.5 最佳实践

- 在 **20-50% 窗口** 时提前压缩（而非等到快满），反而让 agent 更 "sharp"
- 确保 `models.json` 正确定义 `contextWindow`，否则会导致"静默溢出"

---

## 三、OpenAI Codex CLI — 三层 Compaction 架构

**仓库**: https://github.com/openai/codex （MIT，Rust + TypeScript）

Codex 从 TypeScript 重写为 Rust（2025→2026），核心逻辑在 `codex-rs/` 目录。

### 3.1 Token 计数

**文件**: [`codex-rs/core/src/context_manager/history.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/context_manager/history.rs)

使用**字节启发式**：`byte_length / 4`（~4 字节 ≈ 1 token）。简单高效但对中文/CJK 不准确（每个汉字 3 字节 UTF-8 但通常 1-2 tokens）。

图像有特殊启发式：约 1,844 tokens（基于缩放后 ~7,373 bytes）。

### 3.2 上下文窗口配置

```toml
# ~/.codex/config.toml
model_context_window = 272000           # 总 token 上限
effective_context_window_percent = 95   # 有效百分比，预留系统开销
model_auto_compact_token_limit = ...    # 自动压缩触发阈值
project_doc_max_bytes = 32768           # AGENTS.md 最大 32 KiB
```

**Clamping 机制**（[`model_info.rs`](https://github.com/openai/codex/blob/main/codex-rs/models-manager/src/model_info.rs)）：即使用户配了很大的窗口，系统也会限制到服务端报告的 `max_context_window`。

### 3.3 三层压缩架构 ⭐

| 层级 | 文件 | 特点 |
|------|------|------|
| **Inline（本地）** | [`compact.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/compact.rs) | 客户端本地用 LLM 生成摘要 |
| **Remote** | [`compact_remote.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/compact_remote.rs) | 服务端压缩，调用 `/responses/compact` |
| **Remote v2** | [`compact_remote_v2.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/compact_remote_v2.rs) | 流式服务端压缩，支持加密 compaction items |

#### Inline 压缩流程

```
1. 检测触发条件（token 超限）
2. 运行 pre-compaction hooks
3. 克隆当前历史快照
4. 使用结构化 prompt 模板调用 LLM 生成 "handoff summary"
5. 构建有界替换历史（摘要 + 最近 ~20k tokens 消息）
6. 替换 live model history
7. 持久化（支持会话恢复 / forking）
```

#### 压缩 Prompt 模板

**文件**: [`codex-rs/core/templates/compact/prompt.md`](https://github.com/openai/codex/blob/main/codex-rs/core/templates/compact/prompt.md)

模板指导 LLM 必须保留：当前进度、关键决策、约束和偏好、下一步计划、关键数据引用。

支持自定义：

```toml
compact_prompt = "Prioritize architectural decisions..."
# 或外部文件
experimental_compact_prompt_file = "path/to/compact_prompt.md"
```

### 3.4 工具输出截断

**文件**: [`codex-rs/core/src/context_manager/truncate.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/context_manager/truncate.rs)

| 策略 | 说明 |
|------|------|
| **Head+Tail 截断** | 保留输出开头和结尾，中间标记 `[truncated]` |
| **字节限制** | 工具输出默认 ~50 KiB |
| **行数限制** | 旧版 256 行（正迁移到基于 token 的限制） |

### 3.5 AGENTS.md 管理

**文件**: [`codex-rs/core/src/config/mod.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/config/mod.rs)

- 从项目根到当前目录层层遍历发现 `AGENTS.md`
- 拼接后超 `PROJECT_DOC_MAX_BYTES`（默认 32 KiB）会被**静默截断**
- ⚠️ 把重要指令放文件末尾可能因截断被忽略

### 3.6 Memory — 原生无状态 + 实验性 Notes

Codex 本质上**无跨会话记忆**。`AGENTS.md` 是唯一持久化机制。

**实验性功能**（v0.153.4+）：

```toml
[features.context_management]
experimental_mode = true
```

- **Notes 系统**：模型可保存重要信息为 "notes"，不靠反复摘要
- **History 检索**：旧上下文可选择性检索
- **"New Context" 工具**：模型可启动全新上下文窗口，保留 notes 和历史访问

这代表了从"摘要驱动"到"结构化记忆"的演进。

### 3.7 Rollback — 依赖 Git

Codex **没有内置 undo/revert**（社区痛点，Issues #11626、#9618）。实际做法：

1. 频繁 `git commit`，用 `git checkout/reset` 回滚
2. 遇到 "context pollution" → 手动回滚文件 + 开新会话
3. Compaction 本身创建持久化 checkpoint，支持 session forking

### 3.8 已知问题

| 问题 | 说明 |
|------|------|
| **Compaction Loops** | Agent 反复触发压缩、重新加载文件、卡住 |
| **摘要丢近期上下文** | 压缩可能优先保留全局信息而截断最近 3-5 轮 |
| **递归摘要退化** | 摘要的摘要导致信息累积损失 |
| **CJK token 估算不准** | `bytes/4` 启发式对中文显著低估 |
| **截断无警告** | 某些路径截断工具输出但不通知 agent |

---

## 四、Claude Code — 五级渐进式压缩管道

**仓库**: https://github.com/anthropics/claude-code （非开源，GitHub 仅用于 issue 跟踪）

> 以下分析基于：官方文档、社区分析、2026 年 3 月 npm source map 泄漏后的架构分析。

### 4.1 Token 预算管理

**关键源文件**（基于架构分析）：

| 文件 | 职责 |
|------|------|
| `src/context.ts` | 系统/用户上下文收集与管理的核心 |
| `src/core/QueryEngine.ts` | Agentic loop 主协调器 |
| `src/cost-tracker.ts` | Token 使用量和费用追踪 |

- Text blocks 通过字符长度估算 token 数
- Tool-use / tool-result blocks 包含 JSON 结构额外开销
- `getEffectiveContextWindowSize()` = 总限制 - 预留 tokens
- **Prompt Caching**：利用 Anthropic 的 prompt caching 缓存系统提示和 `CLAUDE.md`

### 4.2 五级渐进式压缩管道 ⭐⭐

Claude Code 最核心的设计——**从低成本到高成本逐级执行**：

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Claude Code 五级压缩管道                          │
│                                                                     │
│  Level 1          Level 2         Level 3          Level 4          Level 5        │
│  Tool Result  →  Snip Compact  →  MicroCompact  →  Session Memory →  AutoCompact   │
│  Budgeting       (消息裁剪)       (微压缩)         Compact          (完全压缩)      │
│                                                   (会话记忆压缩)                    │
│  ⚡ 0 API 成本   ⚡ 0 API 成本   ⚡ 0 API 成本    ⚡ 0 API 成本    💰 需 LLM 调用   │
│  大输出→磁盘     裁剪旧消息      清理旧工具结果    保留近 40K       结构化摘要        │
└─────────────────────────────────────────────────────────────────────┘
```

#### Level 1: Tool Result Budgeting

- 单个工具输出超 ~50,000 字符 → 完整输出保存到磁盘，上下文只留 ~2KB 预览
- 零 API 成本

#### Level 2: Snip Compact

- 直接裁剪较老的消息，创建即时空间
- 零 API 成本

#### Level 3: MicroCompact ⭐

**文件**: `src/services/compact/microCompact.ts`

- **每次 API 调用时静默运行**，零 API 成本
- 扫描历史，将旧的 tool results 替换为占位符：`'[Old tool result content cleared]'`
- 触发方式：
  - **时间驱动**：距上次 assistant 消息超过阈值
  - **缓存驱动**：基于 `cache_edits` API 配置阈值（GrowthBook feature flags）
- 目标工具：`FileRead`、`Bash`、`Grep`、`Glob`、`WebSearch`、`WebFetch`、`FileEdit`、`FileWrite`

#### Level 4: Session Memory Compact

**文件**: `src/services/compact/sessionMemoryCompact.ts`

- 在 AutoCompact 之前运行
- 保留最近 ~40K tokens 核心消息
- **不使用 LLM 总结**，而是用压缩表示替换旧消息

#### Level 5: AutoCompact / Full Compact

**文件**: `src/services/compact/autoCompact.ts`, `src/services/compact/compact.ts`

**`shouldAutoCompact()`**：检查 token 使用是否超阈值（默认 ~95%，可配置）

**`compactConversation()`** 流程：
1. 执行 pre-compaction hooks
2. 剥离不必要数据（图片 → 占位符）
3. 按 API 轮次分组消息
4. 使用 forked agent 生成对话历史的结构化摘要

**`compact_boundary` 标记**：
- `system` 类型消息，作为对话历史中的逻辑分界线
- `annotateBoundaryWithPreservedSegment()` 记录 UUID（`headUuid`、`anchorUuid`、`tailUuid`）
- 允许会话加载器正确重建消息链

### 4.3 三层持久化记忆 ⭐

```
┌──────────────────────────────────────────┐
│          Claude Code 记忆架构             │
│                                          │
│  Layer 1: CLAUDE.md（手动）               │
│  ├── ~/.claude/CLAUDE.md   (用户级)       │
│  ├── ./CLAUDE.md           (项目级)       │
│  └── ./sub/CLAUDE.md       (子目录级)     │
│                                          │
│  Layer 2: Auto Memory（自动）             │
│  ├── 自动提取会话中的"学习要点"           │
│  ├── 追踪编码模式、bug 修复、偏好         │
│  └── 新会话启动时自动召回                 │
│                                          │
│  Layer 3: Session Memory（会话级）         │
│  ├── 结构化滚动摘要                      │
│  └── 追踪当前任务、错误、修正             │
└──────────────────────────────────────────┘
```

### 4.4 Checkpoint / Rewind

- 每个 prompt turn 创建一个 checkpoint
- 维护最近 100 个 checkpoint 的文件快照
- `/rewind` 或双击 `Esc` → 回退菜单
- 可同时回退代码和对话状态

### 4.5 工具输出管理

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | 25,000 | 工具响应最大 token 数 |
| `bashOutputMaxChars` | 128,000 字符 | Bash 输出内联显示上限 |
| `taskOutputMaxChars` | 128,000 字符 | 后台任务输出上限 |

超限 → 保存到临时文件 → 上下文只留 ~2KB 预览 → 模型可通过 `read` 工具获取完整内容。

### 4.6 文件内容管理

- `CLAUDE.md` 从当前目录向上层层加载并**拼接**（非覆盖）
- Skills 按需加载：不需要时不占 token
- **Compaction 后**自动重新读取最近修改的最多 5 个文件
- MCP 工具定义占 token → 可通过 `/mcp` 断开空闲服务器回收

### 4.7 配置

```json
// settings.json
{
  "autoCompact": true,
  "autoCompactThreshold": 80
}
```

环境变量 `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` 覆盖阈值。

---

## 五、其他工具对比：Aider / Cursor / Gemini CLI

### 5.1 Aider — 递归摘要

**策略核心**：`ChatSummary` 类监控会话长度。超阈值（默认 1024-2048 tokens）→ 自动摘要旧消息，保留近期原文。**摘要过程可递归重复**。

| 命令/变量 | 作用 |
|-----------|------|
| `/tokens` | 查看实时 token 使用 |
| `/drop <file>` | 移除不需要的文件上下文 |
| `/clear` | 清空会话历史 |
| `AIDER_MAX_CHAT_HISTORY_TOKENS` | 配置摘要触发阈值 |
| `--cache-prompts` | 启用 prompt 缓存 |

**设计哲学**：只添加当前任务需要的文件 → 大任务拆小任务 → 切换任务开新会话。

### 5.2 Cursor — 动态检索（不压缩）

Cursor 走了一条不同的路——**按需检索而非压缩**：

- 不是静态塞入大量数据，而是**按需检索**相关代码
- 基于 AST（抽象语法树）将代码拆成语义单元
- **混合搜索**：语义搜索（向量 embeddings）+ 词法搜索（Instant Grep）
- 增量更新索引
- `@file`、`@codebase`、`@Docs`、`@git` 显式引导 AI
- `.cursorrules` / `.mdc` 文件存储项目约定

### 5.3 Gemini CLI — 大窗口硬吃

Gemini CLI 采用截然不同的策略——**依赖 1M+ token 的原生巨大窗口**：

- MoE（混合专家）架构 + 高效注意力机制
- >99% 长序列检索准确率
- 最小化预裁剪 → 用模型原生能力代替复杂 context engineering
- 与 Claude Code 的积极压缩策略**完全相反**

---

## 六、跨工具横向对比

### 6.1 核心机制对比

| 特性 | Pi | Codex | Claude Code | Aider | Cursor | Gemini CLI |
|------|-----|-------|-------------|-------|--------|------------|
| **Context 窗口** | 模型决定 | 可配置 | ~200K | 模型决定 | 模型决定 | ~1M |
| **压缩策略** | LLM 结构化摘要 + 树标记 | 三层 Compaction | 五级渐进管道 | 递归 LLM 摘要 | 按需检索 | 极少压缩 |
| **触发方式** | 公式 + 手动 | 阈值 + 手动 | ~95% 自动 + 手动 | 阈值自动 | N/A | N/A |
| **零成本压缩** | ❌ | ❌ | ✅（Level 1-4） | ❌ | N/A | N/A |
| **会话持久化** | JSONL 树 | JSONL/SQLite | 会话级 | 线性历史 | IDE 集成 | 会话级 |
| **会话分叉** | ✅ 树结构 | ✅ 实验性 | ❌ | ❌ | ❌ | ❌ |
| **工具输出处理** | 扩展钩子裁剪 | Head+Tail 截断 | 溢出到磁盘 + 预览 | 文件限制 | 写文件再按需读 | 原生大窗口 |
| **外部记忆** | Checkpoint 锚点 | AGENTS.md + Notes | CLAUDE.md + Auto Memory | `.aider.*` | `.cursorrules` | `AGENTS.md` |
| **Undo/Rollback** | 树分叉回溯 | ❌ 依赖 Git | ✅ `/rewind` | ❌ | ✅ IDE 集成 | ❌ |

### 6.2 压缩触发阈值对比

```
Pi:         contextWindow - 16,384 tokens (keepRecent: 20,000)
Codex:      effective_context_window_percent = 95%
Claude Code: ~95% (可通过 CLAUDE_AUTOCOMPACT_PCT_OVERRIDE 配置)
Aider:      1,024-2,048 tokens (极低阈值，频繁触发)
```

### 6.3 设计哲学光谱

```
                    ← 积极压缩                          大窗口硬吃 →

  Aider ────── Pi ────── Claude Code ────── Codex ────── Cursor ────── Gemini CLI
  (极频繁     (结构化    (五级渐进，       (三层架构，   (按需检索，   (1M 窗口，
   摘要)      树+扩展)    零成本优先)       本地+远程)    不压缩)       不压缩)
```

---

## 七、关键设计模式总结

### 模式 1：渐进式压缩管道

Claude Code 的核心思路——**先用便宜的方法，不够再用贵的**：

```
清理旧工具输出(免费) → 裁剪旧消息(免费) → 结构化摘要(需 LLM 调用)
```

**优势**：大部分情况下不需要额外 LLM 调用，省钱省时间。

### 模式 2：结构化摘要（非简单截断）

所有工具都用 LLM 生成摘要而非简单删除最老的消息。摘要 prompt 通常要求保留：
- 当前进度和关键决策
- 约束和用户偏好
- 下一步计划
- 关键数据引用

### 模式 3：工具输出溢出到磁盘

大输出 → 保存到文件 → 上下文只留小预览 → 模型可按需读取。

Claude Code、Codex、Cursor 都采用这个模式。

### 模式 4：持久化指令文件

`CLAUDE.md` / `AGENTS.md` / `.cursorrules` — 项目规则不放在对话里，而是作为持久化系统 prompt，每次会话自动加载，不会被 compaction 丢弃。

### 模式 5：会话分叉（Session Forking）

Pi 的树结构和 Codex 的实验性 forking——允许 agent 探索不同方案而不污染主对话。

### 模式 6：按需检索替代压缩

Cursor 的路线——不压缩历史，而是动态检索相关代码。适合 IDE 集成场景但对 CLI agent 不太适用。

### 模式 7：子 Agent 委托

Claude Code 和 Antigravity（Google）的做法——将研究任务分发给子 agent，各有独立 context window。父 agent 只接收摘要结果。

---

## 八、相关学术研究

### 8.1 "Coding Agents are Effective Long-Context Processors"

> arXiv:2603.20432, 2026.03, Duke University

- 编码 Agent 通过文件系统操作处理长文本，比 SOTA 长上下文 LLM **平均高出 17.3%**
- 方法：将文本语料组织为文件系统结构，用终端命令（grep/sed/脚本）导航
- 数据集最高达 **3 万亿 token**
- **启示**：工具 + 文件系统 = 比注意力机制更可靠的"外部记忆"

### 8.2 "Parallel Context Compaction for Long-Horizon LLM Agent Serving"

> arXiv:2605.23296, Penn State

- 传统串行 compaction 造成阻塞 + 不可预测（LLM 常忽略摘要长度指令）
- **方案**：并行压缩会话块，降低推理延迟，实现细粒度可预测控制
- 测试：4 个模型骨架（8B-120B），密集和 MoE 架构

### 8.3 Compaction 的认知失败模式

> arXiv:2607.13071

- 天真摘要可能导致 Agent **"虚构"结果**——将被中断的进程记录为成功
- **教训**：Compaction 是有损的，必须设计防止认知偏差的保护机制

---

## 九、2026 行业趋势

1. **从"大窗口"到"上下文质量"** — 窗口大 ≠ 效果好，噪声过多反而降低准确率
2. **Context Engineering 成核心技能** — 精选注入哪些文件/工具定义、主动裁剪、分层记忆
3. **标准化 Context 表面** — `AGENTS.md` 成跨工具标准（Claude Code/Copilot/Cursor/Gemini CLI 通用），MCP 成外部数据源连接标准
4. **Context Drift 风险** — 长运行循环中 agent 容易遗忘文件状态或任务约束；子 agent 编排是对策
5. **Tool Output 管理三策略** — Head/Tail 截断、Spill-to-File、元数据标签替代
6. **"静默截断"陷阱** — 框架截断工具输出但不通知 agent → 基于不完整信息做决策
7. **从"摘要驱动"到"结构化记忆"** — Codex 的 Notes 系统代表新方向

---

## 十、对本项目的启发

### 10.1 直接可借鉴的策略

| 策略 | 来源 | 适用场景 |
|------|------|----------|
| **分级压缩管道** | Claude Code | Python AI 服务的面试对话管理 |
| **工具输出溢出到文件** | 通用 | 面试记录过长时的处理 |
| **持久化指令文件** | 通用 | 面试场景配置（已有 `AGENTS.md`） |
| **结构化 LLM 摘要** | 通用 | 面试中期的上下文刷新 |
| **Head+Tail 截断** | Codex | 简历解析等大文本输出 |

### 10.2 针对面试场景的特殊考虑

1. **面试对话的上下文管理** — 面试官 Agent 需要记住候选人之前的回答以追问，但不需要记住每一个 `grep` 命令的输出
2. **多轮面试的记忆传递** — 类似 Claude Code 的 Session Memory，面试结束后生成结构化摘要，下轮面试加载
3. **评估一致性** — Compaction 不能丢失评分标准和已有评分，否则会导致评估偏差

### 10.3 注意事项

- **中文 token 估算** — `bytes/4` 对中文不准确（Codex 的已知问题），需要更精准的估算或直接调用 tokenizer
- **压缩不是万能药** — 学术研究表明天真摘要可能导致 agent "虚构"结果，需要验证机制
- **频率与质量的平衡** — Pi 建议在 20-50% 时提前压缩效果更好，而非等到快满

---

## 附录：关键源码索引

### Pi Agent

| 功能 | 位置 |
|------|------|
| Auto-compaction 触发 | `settings.json` → `reserveTokens`, `keepRecentTokens` |
| 会话树结构 | Entry: `uuid` + `parentUuid`, JSONL 格式 |
| 扩展钩子 | `pi-context-prune`, `pi-ultra-compact`, `pi-context` |

### OpenAI Codex CLI

| 功能 | 文件 |
|------|------|
| 本地 Compaction | [`codex-rs/core/src/compact.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/compact.rs) |
| 远程 Compaction | [`codex-rs/core/src/compact_remote.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/compact_remote.rs) |
| Token 估算 | [`codex-rs/core/src/context_manager/history.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/context_manager/history.rs) |
| 截断逻辑 | [`codex-rs/core/src/context_manager/truncate.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/context_manager/truncate.rs) |
| 会话管理 | [`codex-rs/core/src/session/mod.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/session/mod.rs) |
| 配置定义 | [`codex-rs/core/src/config/mod.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/config/mod.rs) |
| 模型窗口 Clamping | [`codex-rs/models-manager/src/model_info.rs`](https://github.com/openai/codex/blob/main/codex-rs/models-manager/src/model_info.rs) |
| 压缩 Prompt 模板 | [`codex-rs/core/templates/compact/prompt.md`](https://github.com/openai/codex/blob/main/codex-rs/core/templates/compact/prompt.md) |

### Claude Code（基于架构分析）

| 功能 | 文件 |
|------|------|
| 上下文管理核心 | `src/context.ts` |
| Agentic Loop | `src/core/QueryEngine.ts` |
| MicroCompact | `src/services/compact/microCompact.ts` |
| Session Memory Compact | `src/services/compact/sessionMemoryCompact.ts` |
| AutoCompact | `src/services/compact/autoCompact.ts` |
| Full Compact | `src/services/compact/compact.ts` |
| 压缩 Prompt | `src/services/compact/prompt.ts` |
| 持久化记忆 | `src/memdir/`, `extractMemories.ts` |
| Session Memory | `sessionMemory.ts` |
