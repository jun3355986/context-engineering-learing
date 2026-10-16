# 超长上下文处理机制调研：pi / Codex / Claude Code

> 调研日期：2026-09-12
> 调研动机：面试评估上下文（修复 3 原方案）采用「截取最近 2000 字符」的固定截断，追问链一长仍会丢失关键上下文。本文分析三个成熟 coding agent 的长上下文管理实现，提炼可移植的模式，最后给出本项目评估上下文的升级方案。
> 证据等级说明：pi（badlogic/pi-mono）与 Codex（openai/codex）为开源仓库，结论来自源码阅读（路径可复核）；Claude Code 不开源，结论来自官方文档、工程博客与社区记录，标注了来源层级。

> ⚠️ **2026-09-17 更正**：本文档 §6 对「本项目现状」的描述有误，请以 `LONG_CONTEXT_SOURCE_DEEP_DIVE.md` §0 为准。
> 经回源码核查（`ai_interviewer/api/interviewer.py` 全部 5 个 `context` 组装点）：
> ① 本文所称「追问链靠启发式截取最近 2000 字符」**在生产代码中不存在**；
> ② 实际的评分调用 `evaluate_answer`（`:148`）**完全不带对话历史**——是「信息缺失」，不是「截断过狠」；
> ③ 真正的长上下文风险在 `conclude_interview`（`:442`），那里**从未设过长度上限**。
> 本文档 §1–§5（三家机制调研）仍然有效，仅 §6 的现状判断与优先级需按新文档修正。

---

## 1. 问题同构性：面试评估 vs Coding Agent

三个工具面对的问题和本项目完全同构：

| | Coding Agent | 本项目面试评估 |
|---|---|---|
| 无限增长 | 对话轮次 + 工具输出无限增长 | 问答轮次 + 追问链无限增长 |
| 有限预算 | 模型 context window | 评估 prompt 的合理长度（延迟/成本/注意力） |
| 不可丢的信息 | 当前任务目标、关键决策、文件状态 | 本题追问链、候选人画像、已暴露弱项 |
| 可压缩的信息 | 陈旧的工具输出、中间过程 | 已闭环问题的完整原文 |

三家的共同答案是**分层记忆**：全量历史落盘永不丢 + 当前窗口内「结构化摘要（旧）+ 原文（近）」的投影。没有一家采用「固定 N 字符截断」——截断是三家中最不被信任的手段，只在两个场合出现：单条工具输出的源头治理、压缩 prompt 超限时的最后兜底。

---

## 2. Claude Code：多级压缩 + 外置记忆体系

**来源层级**：官方文档（code.claude.com/docs）、Anthropic 工程博客、社区记录；闭源无法核源码。

### 2.1 机制分层（轻→重）

1. **Context editing / 微压缩（轻量级）**：接近 token 上限时，自动从窗口清除**过期的工具调用与结果**，同时保留对话骨架。平台侧文档化参数支持触发阈值、保留条数（keep）、排除工具等配置。这是 Anthropic 定义的"safest lightest touch form of compaction"——工具结果早已消费完毕，agent 不再需要原始输出。
2. **Auto-compact（重量级）**：接近上下文上限时把对话交给模型自己摘要，用「摘要 + 未被摘要的近期消息」重新初始化窗口。官方现行文档按模型给出绝对阈值（如 1M 窗口模型默认约 **967K** tokens 触发、无扩展上下文的 Sonnet 4.6 在 **200K** 边界），可用 `CLAUDE_CODE_AUTO_COMPACT_WINDOW` / `--autocompact` / `autoCompactWindow` 设置在 **100K–1M** 间调整；社区广泛记录的历史行为约为窗口的 **~95%**。
3. **手动压缩**：`/compact` 支持焦点指令（`/compact focus on the auth bug fix`），还可在 CLAUDE.md 写 `# Compact instructions` 定制摘要侧重点；`/rewind` 提供"从某消息开始/截至某消息"的部分压缩。
4. **`/clear`**：任务切换时彻底清零（"costs nothing"），配合 `/resume` 按需回来。

### 2.2 压缩保留什么（what survives compaction）

官方文档给出的重载清单——这实质上是一份「不该被摘要掉的状态」白名单：

| 状态 | 压缩后的处理 |
|---|---|
| System prompt / output style | 持续生效，不走摘要 |
| 项目 CLAUDE.md、auto memory（MEMORY.md） | **从磁盘重新注入**，不依赖摘要 |
| Plan mode 的 plan 文件 | 从磁盘重新注入 |
| 最近修改的文件 | **最多重读 5 个**（按最近修改排序） |
| 已调用 skill 的正文 | 重新注入，单 skill ≤5,000 tokens、总计 ≤25,000 |
| 完整工具输出、中间推理 | **丢弃** |

摘要本身是结构化的 "Conversation summary"，保留：用户请求与意图、关键技术概念、看/改过的文件及关键代码片段、错误与修复方式、待办与当前工作。官方示意摘要约为原文的 **~12%**。

### 2.3 外置记忆（压缩丢失的细节靠它补）

- **CLAUDE.md / AGENTS.md**：每次会话固定注入的项目级记忆，压缩后从磁盘重放；
- **Memory tool（文件式记忆）**：模型在专用目录里 create/read/update/delete 记忆文件，`MEMORY.md` 作索引（只载入前 200 行/25KB），按需读全文——记忆住在窗口之外，跨会话持久；
- **TodoWrite**：任务状态外置成列表，天然免疫压缩；
- **Sub-agent 隔离**：子代理在干净窗口里消耗数万 token 做探索，只向主 agent 返回 **1,000–2,000 token** 的浓缩结论——把"读了什么"和"知道了什么"分开存储。

### 2.4 效果数据（Anthropic 官方公布）

- Context editing 单独使用：agentic search 评测 **+29%**；
- Context editing + memory tool 组合：**+39%**；
- 100 轮 web search 评测：原本因上下文耗尽而失败的流程得以完成，token 消耗 **-84%**。

---

## 3. OpenAI Codex：检查点 + 逐级降级（源码级）

**来源**：`openai/codex` 仓库 codex-rs（Rust），2026-09 HEAD `7efb0262`。以下路径均相对 `codex-rs/`。

### 3.1 触发机制：90% 阈值 + 三条实现路径

```rust
// protocol/src/openai_models.rs:521-533
let context_limit = self.resolved_context_window()
    .map(|context_window| (context_window * 9) / 10);   // 硬编码 90%
// 配置了 model_auto_compact_token_limit 时取 min(limit, 90%)
```

另有 95% 的 `effective_context_window_percent` 作硬顶（`openai_models.rs:399-401`）。触发点四类（`core/src/session/turn.rs`）：

1. **Pre-turn**：每轮开始前检查 `token_limit_reached`，达标先压缩再干活；
2. **Mid-turn**：工具循环中途每次采样后复查，达标就**就地插入压缩再继续**（长任务不断粮的关键）；
3. **CompHashChanged**：换模型且压缩协议版本（`comp_hash`）不一致，先用旧模型压缩再切换；
4. **ModelDownshift**：切到更小窗口的模型前先压缩。

实现路径三条（`core/src/tasks/compact.rs`）：TokenBudget 特性模式（直接换新窗口）、远端压缩 RemoteCompaction V2（OpenAI/Azure 专属）、本地摘要压缩（其余 provider 走这条，也是我们最该参考的）。

### 3.2 本地摘要压缩：保留什么、丢什么

```rust
// core/src/compact.rs:678-755 build_compacted_history_with_limit
// 新历史 = 用户消息(总预算 20,000 token，从新到旧收集、超限逐条截断)
//        + 摘要(user 角色, COMPACT_USER_MESSAGE_MAX_TOKENS = 20_000)
// 全部丢弃：assistant 回复、reasoning、工具调用/输出、plan
```

- 摘要 prompt（`prompts/templates/compact/prompt.md`，原文）："You are performing a CONTEXT CHECKPOINT COMPACTION. Create a handoff summary for another LLM that will resume the task."，要求包含：进度与关键决策、重要上下文/约束/用户偏好、待办与下一步、继续工作所需的关键数据；
- 摘要以 **user 消息**插回，带固定前缀（"Another language model started to solve this problem and produced a summary…"）；
- 旧摘要用 `is_summary_message` 识别并排除，**防止摘要套摘要**；
- 环境上下文（AGENTS.md、cwd、权限、工具清单等 WorldState）**不进摘要，压缩后下一轮全量重新注入**——"可从磁盘重建的东西不占摘要预算"。

### 3.3 工具输出：源头截断（保头保尾）

```rust
// core/src/context_manager/history.rs:365-376
// 记录进历史时按模型策略截断，当前目录所有模型为 {mode: tokens, limit: 10000}

// utils/string/src/truncate.rs:38-69 —— 预算对半，砍中间
fn format_truncation_marker(...) -> String {
    format!("…{removed_count} tokens truncated…")
}
```

单条工具输出 10k token 上限、保头保尾、中间插占位标记。远端压缩前若仍超窗，最老的工具输出整体替换为一句话占位（`compact_remote_history.rs:181-186`）。

### 3.4 逐级降级与失败兜底

按上下文耗尽程度依次：单条输出截断 → 剩余 token 低于阈值注入提醒消息 → 注入"先写 notes 再压缩"提示 → pre-turn 压缩 → mid-turn 压缩 → 替换最老工具输出。压缩本身失败时（`compact.rs:308-317`）：`ContextWindowExceeded` → **逐条删最老历史重试**；其他错误 → backoff 重试；远端 V2 失败可换当前模型重试一次。只有 `replace_compacted_history` 成功才替换历史，失败则原历史完好——压缩是事务性的。

压缩成功后固定提示用户："Long threads and multiple compactions can cause the model to be less accurate. Start a new thread when possible."（官方承认多轮压缩有损）。

### 3.5 持久化与 token 计数

- **Rollout JSONL**（`$CODEX_HOME/sessions/YYYY/MM/DD/rollout-*.jsonl`）：每行一个 `RolloutItem`（消息、工具调用、`Compacted` 检查点、WorldState、TokenUsage…）。压缩时写入 `Compacted + WorldState + TurnContext` 四件套；
- **Resume = 从最近的 `Compacted` 检查点回放**（`session/rollout_reconstruction.rs:107-200`）：找到最新存活的压缩检查点作基底，只重放其后的尾部——恢复的就是压缩后窗口，不是全量重放；
- Token 计数：**4 字节 ≈ 1 token** 的启发式估算（`const APPROX_BYTES_PER_TOKEN: usize = 4`）+ 服务端 usage 真值为优先，估算只补差额。

---

## 4. pi：append-only 树 + 投影式压缩（源码级）

**来源**：`badlogic/pi-mono` 仓库（TypeScript），2026-09 快照。以下路径相对仓库根。

### 4.1 触发：token 数阈值，不是百分比

```ts
// packages/coding-agent/src/core/compaction/compaction.ts:132-136
DEFAULT_COMPACTION_SETTINGS = {
  enabled: true,
  reserveTokens: 16384,      // 给响应预留 16k
  keepRecentTokens: 20000,   // 最近 20k token 原文保留
};
// compaction.ts:235-238
return contextTokens > contextWindow - settings.reserveTokens;
```

触发分三类，事件上明确标注 `"manual" | "threshold" | "overflow"`（`agent-session.ts:157`）：

- **Threshold**：正常轮次结束后 usage 越过阈值；
- **Overflow with retry**：请求报上下文溢出错误 → 删失败消息、压缩、**该轮重试一次**（`_overflowRecoveryAttempted` 守卫防循环）；
- **Overflow without retry**：响应成功但 usage 超窗（z.ai 式静默溢出，`overflow.ts:144-160`）。

溢出检测是独立的一层工程：`packages/ai/src/utils/overflow.ts:37-63` 收录 20+ 家 provider 的溢出错误正则（Anthropic "prompt is too long"、OpenAI "exceeds the context window"、DashScope…），另加静默溢出与 length 截断两类启发式检测。检查点有三处：每轮 run 结束、用户提交新 prompt 前、**多轮工具循环每批工具结果落定后**。

### 4.2 切点算法：最近 20k token 原文 + 前面全部摘要

```ts
// compaction.ts:403-461 findCutPoint：从最新往回累计 estimateTokens，
// 累计到 keepRecentTokens 即停；compaction.ts:308-321
// 切点可以在 user/assistant/bash 等条目处，绝不切在 toolResult 上
// （工具结果必须与工具调用同生共死）
```

LLM 看到的历史 = `[压缩摘要消息(user 角色, 置于最前)] + [firstKeptEntryId 起的原文] + [压缩点之后的消息]`（`session-manager.ts:441-453`）。单个 turn 超 20k 时，把该 turn 前缀也单独摘要合并（`compaction.ts:835-848`）。

### 4.3 摘要：固定结构化模板 + 增量更新

```ts
// compaction.ts:467-498（原文，要求 EXACT format）
`## Goal
## Constraints & Preferences
## Progress   (### Done / ### In Progress / ### Blocked)
## Key Decisions
## Next Steps
## Critical Context
Keep each section concise. Preserve exact file paths, function names, and error messages.`
```

- 序列化对话时**工具结果截断到 2000 字符**（`utils.ts:89`，注释点名 tool result 是上下文最大头）；
- 已有旧摘要时走**增量更新 prompt**（`compaction.ts:500-539`）：`<previous-summary>` + 新增对话，保留旧信息、只推进 Progress/Next Steps；
- 摘要请求带 `cacheRetention: "none"`，**不为一次性摘要请求污染 prompt cache**（`compaction.ts:589-599`）；
- 文件读写清单（readFiles/modifiedFiles）跨压缩**累计追加**到摘要尾部（`compaction.ts:42-70`）——被压缩掉的操作记录以清单形式幸存。

### 4.4 持久化：压缩永不删数据

会话是 **append-only JSONL 树**（`~/.pi/agent/sessions/**/*.jsonl`，条目带 `id/parentId`，支持分支）。`CompactionEntry` 只是树上的一个节点，记录 `summary + firstKeptEntryId`；"当前窗口"是 `buildContextEntries()` 对树的**投影**。resume 时流式读全量文件、应用压缩边界、得到消息列表——**恢复的天然是压缩后窗口，但历史物理上从未丢失**。重复压缩时摘要范围从上次 `firstKeptEntryId` 起算，让上次幸存的消息也进入本次摘要。

### 4.5 源头治理 + 外置状态（pi 的鲜明特色）

- 工具输出**在产生时**就截断：2000 行 / 50KB（`tools/truncate.ts:11-12`）；bash 大输出全量落盘快照文件，消息里只留 `[Showing lines X-Y of Z. Full output: /path]`，需要时 read 回来；
- Skills 渐进披露：system prompt 只注入 name/description/location，正文按需 read；
- 作者哲学（2025-11 博客）："context engineering is paramount. Exactly controlling what goes into the model's context yields better outputs"；任务追踪"make it externally stateful by writing to a file"；压缩做成可被扩展整体替换的原语（`session_before_compact` 钩子）。

### 4.6 token 计数

优先信任 provider 上报的 usage（`totalTokens || input+output+cacheRead`）；无 usage 时 `chars/4` 估算（`compaction.ts:266-306`，图片按 4800 字符折算，注释自认保守高估）；压缩前时间戳的旧 usage 不再参与阈值判断，防误触发。

---

## 5. 横向对比

| 维度 | Claude Code | Codex (codex-rs) | pi (pi-mono) |
|---|---|---|---|
| 触发方式 | 自动（按模型阈值，~95%/200K/967K，可配）+ 手动 `/compact` | 自动 90%（可配，硬顶 95%）pre/mid-turn + 手 `/compact` | 自动 `window − 16k` + overflow 重试 + 手动 |
| 轻量级清理 | ✅ context editing（清旧工具结果，+29%） | ❌（直接上摘要） | ❌（源头截断代替） |
| 摘要保留 | 结构化 summary（~12% 体积）+ 近期未摘要消息 | **只保留用户消息**（≤20k）+ 摘要 | **最近 20k token 全原文** + 摘要 |
| 摘要插入位置 | 重开窗口时携带 | user 消息 + 固定前缀 | user 消息置于历史最前 |
| 摘要结构 | requests/intent、文件、错误与修复、待办 | handoff：进度/决策/约束/下一步/关键数据 | Goal/Constraints/Progress/Decisions/Next/Critical |
| 环境上下文 | CLAUDE.md/memory/skill 从磁盘重放 | WorldState 下轮全量重注入 | system prompt 每轮原样重发 |
| 防摘要套摘要 | 重开窗口天然规避 | `is_summary_message` 排除旧摘要 | 增量更新单一摘要 |
| 大输出治理 | context editing 清理 + sub-agent 隔离 | 10k token 保头保尾 | 2000 行/50KB 截断 + 落盘留路径 |
| 全量历史 | transcript（服务端/本地）+ resume from summary | JSONL rollout + `Compacted` 检查点回放 | JSONL 树，压缩=投影 |
| token 计数 | 模型自带 context awareness | 4 bytes ≈ 1 token 估算 + usage 真值 | usage 真值 + chars/4 估算兜底 |
| 失败兜底 | 回退链覆盖压缩 | 删最老重试 / 换模型重试 / 标记满窗 | overflow 重试一次 + 静默溢出检测 |
| 明确承认的损耗 | 多轮压缩丢 subtle context（官方博客） | "multiple compactions → less accurate"（压缩后固定警告） | 摘要自包含设计即对此的回应 |

**三家惊人一致的四个决策**：

1. **全量历史落盘，压缩只是视图**——没有任何一家真的删除数据；
2. **摘要必带固定结构**（目标/决策/进度/下一步），且以 user 消息身份注入，不许模型自由发挥格式；
3. **近期内容保留原文**（Codex 只保用户消息是激进版，pi 保 20k 全文是保守版）；
4. **可重建的状态（system prompt、项目记忆、环境）不进摘要，压缩后重注入**。

---

## 6. 对本项目：评估上下文的升级方案（修复 3 v2）

### 6.1 现状映射

| 三家工具的组件 | 本项目已有 |
|---|---|
| append-only 全量历史 | ✅ SQLite `interview_records.db` 的 session history + Java Postgres 分支消息（已具备，且 durable 快照本身就是"投影"思想） |
| 每轮采样的上下文组装 | ⚠️ 现状是 `简历[:1000] + 问题 + 回答`，追问链靠"最后一题起点"启发式截 2000 字符 |
| 滚动结构化摘要 | ❌ 缺失——这是真正的 gap |
| token 预算 | ❌ 字符数硬编码 |

### 6.2 升级后的评估上下文结构（三层）

借鉴三家的"结构化摘要（旧）+ verbatim tail（近）+ 可重建状态（不占预算）"：

```
评估 prompt =
  system: 评分 rubric（可重建状态，等价 CLAUDE.md，永远原样在）      [不变]
  候选人画像摘要: 滚动结构化摘要（旧问答的压缩投影）                  [新增]
  本题追问链: 从本题首轮问题起的全部原文（verbatim tail）            [替换原 2000 字符截断]
  当前回答 + 简历关键段                                             [不变]
```

**候选人画像摘要**（等价 pi 的 SUMMARIZATION_PROMPT，按面试场景改写），每题闭环（不再追问、进入下一题）时增量更新一次：

```
## 已考察能力（题型与得分）
## 暴露的弱项（含已追问过的点，避免重复追问）
## 候选人画像（表达/深度/真实性信号）
## 待深挖的线索
```

增量更新（等价 pi 的 `<previous-summary>` 模式）：新摘要 = 旧摘要 + 本题 QA 概要，**维护单一摘要滚动前进**，而不是堆叠多份摘要（Codex 用 `is_summary_message` 防、pi 用增量模板防，本项目从设计上就只存一份，天然免疫）。

### 6.3 关键实现决策

1. **摘要存哪**：作为带标记的特殊消息追加进 `session.history`（如 `{"role":"system","type":"rolling_summary",...}`）。随快照走、分支重建自然恢复、**零 BranchSnapshot schema 变更**；评估组装时按 type 挑出来，发给 LLM 的对话历史组装逻辑不受影响（评估本就不用原始 history）。
2. **verbatim tail 按问题边界切，不按 token 切**：与 coding agent 不同，面试对话天然有"题"这个语义边界——本题追问链就是一个 turn，通常 <2k token，比 pi 的通用 findCutPoint 简单得多，这是面试场景的天然优势。
3. **token 预算替代字符数**：`len(text)//4` 估算（Codex/pi 同款，对中文略保守但安全）；追问链设上限（如 8k token），超限时**优先保留原问题 + 最近追问**、中间轮次的回答折叠为要点——这是唯一的降级路径，且降的是"中间追问"不是"本题上下文"。
4. **conclude 用摘要 + 分数表**：最终总结的输入 = 滚动摘要 + `题目/得分/评语` 结构化表格（feedback 全量保留，不受摘要压缩），长面试不再顶 context。
5. **不做**：评估路径不需要 auto-compact 式"接近上限才压"（每轮评估是独立短调用，预算固定，滚动摘要在每题闭环时增量更新即可，每次多一次轻量 LLM 调用或直接用规则模板拼装均可——先用规则模板，成本为零；摘要质量不足再升级为 LLM 增量摘要）。

### 6.4 与原修复 3 方案的兼容关系

原方案的"带上本题追问链"被 v2 完整保留并语义化（问题边界 + token 预算 + 降级策略）；原方案的"conclude 带 feedback"不变；新增的只有"滚动摘要"一层。实施顺序不变：修复 2（结构化输出）→ 修复 3 v2。

---

## 7. 参考来源

**源码（2026-09 快照）**

- pi：https://github.com/badlogic/pi-mono —— `packages/coding-agent/src/core/compaction/compaction.ts`、`core/agent-session.ts`、`core/session-manager.ts`、`packages/ai/src/utils/overflow.ts`、`docs/compaction.md`、`docs/session-format.md`
- Codex：https://github.com/openai/codex —— `codex-rs/core/src/compact.rs`、`core/src/session/turn.rs`、`core/src/session/context_window.rs`、`core/src/context_manager/history.rs`、`protocol/src/openai_models.rs`、`prompts/templates/compact/prompt.md`、`core/src/session/rollout_reconstruction.rs`

**Claude Code / Anthropic 官方**

- Context window 与 what survives compaction：https://code.claude.com/docs/en/context-window
- Model config（auto-compact 窗口配置）：https://code.claude.com/docs/en/model-config
- 成本与压缩：https://code.claude.com/docs/en/costs
- Effective Context Engineering for AI Agents（工程博客，compaction/笔记/sub-agent/JIT 检索）：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Context management（context editing + memory tool 公告与效果数据）：https://claude.com/blog/context-management

**pi 设计意图**

- What I learned building an opinionated and minimal coding agent：https://mariozechner.at/posts/2025-11-30-pi-coding-agent/
- Armin Ronacher: Pi, The Minimal Agent：https://lucumr.pocoo.org/2026/1/31/pi/

**社区记录（Claude Code auto-compact ~95% 的历史行为）**

- https://hyperdev.matsuoka.com/p/how-claude-code-got-better-by-protecting
- https://levelup.gitconnected.com/why-i-compact-my-ai-coding-agent-at-20-not-90-1a665c0c4e5d
