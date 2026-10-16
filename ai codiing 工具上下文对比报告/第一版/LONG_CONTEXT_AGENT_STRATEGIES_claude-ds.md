# 长上下文处理机制分析报告：Claude Code / Codex / pi

> 主题：三个主流 AI coding agent 如何在超长上下文下工作，以及本项目（my_ai_interviewer）该抄哪几条。
> 产出日期：2026-09-17
> 证据等级：全部结论标注来源。**A 级** = 我直接读到的源码（本机 clone 或本机源码快照）；**B 级** = 官方文档；**C 级** = 推断，未验证。

---

## 0. 结论速览

三家的共同答案只有一句话：**不要把「对话历史」当成上下文，把它当成一个需要按预算编译的产物。**

| 维度 | Claude Code | Codex | pi |
|---|---|---|---|
| 核心策略 | 六级流水线，逐级降级 | 阈值触发，整体替换 | 按 token 预算切一刀 + 增量摘要 |
| 触发条件 | 绝对 token 数（窗口 − 13K） | 绝对 token 数（窗口 × 90%） | 绝对 token 数（窗口 − 16,384） |
| 保留粒度 | 保留段 + session memory | 最近的用户消息 ≤ 20K | 最近的所有消息 ≤ 20K |
| 工具输出处理 | 单条消息总量封顶 + 落盘换预览 | head+tail 中间挖空 | 摘要输入侧截到 2000 字符 |
| 摘要 prompt | 9 段（交接单式） | 9 项 + 固定前缀 | 6 段 checkbox + 增量更新 |
| 压缩后 | 重新注水（文件/计划/skill） | 重新注入 AGENTS.md/权限 | `<read-files>` / `<modified-files>` 标签 |
| 恢复会话 | 从 compact 边界之后重建 | 从最后一个存活 checkpoint 重放 | 会话树 + 分支摘要，不重放 |
| 缓存策略 | 前缀分层 + 显式断点，TTL 分档 | —（依赖 API 隐式缓存） | 8 个 provider 统一抽象，压缩调用禁写缓存 |
| 独有设计 | 缓存编辑 / 时间触发清理 | `new_context_window` 工具 | 增量摘要 / turn 前缀摘要 / 分支摘要 / 延迟工具加载 |
| 是否开源 | 否（闭源，npm 分发） | 是（Rust） | 是（TypeScript, MIT） |

**六条可直接迁移的原则**（细节见 §5）：

1. **阈值用绝对 token 数，不用百分比**。绝对数才能表达「压缩本身也要花 token 和输出预算」。
2. **压缩是流水线，不是开关**。便宜的清理手段（清工具结果、删图、中间挖空）先跑，跑完还不够才做贵的（LLM 摘要）。
3. **压缩是有损的，所以要补偿**。摘要不带代码，压完必须把「最近碰过的文件、当前计划、待办」重新贴回去。
4. **摘要要增量更新**。对摘要再摘要会单调退化；只对新增消息做有损压缩。**这条收益最大、最容易漏。**
5. **缓存不是优化项，是约束**。它反过来决定了 prompt 怎么排序、工具定义怎么管、一次性调用怎么做。**稳定内容在前是零成本的。**
6. **渐进披露：给路径和规则，不给内容**。0.5MB 文档可以只占 prompt 里 1KB。

---

## 1. 方法与证据说明

| 对象 | 证据来源 | 等级 |
|---|---|---|
| Codex | `github.com/openai/codex` @ `ce03f22`(main, 2026-09-17) shallow clone 到本机后 grep/read | A |
| Claude Code | 官方文档（v2.1.274 基线）+ 本机社区快照 `civil-engineering-cloud-claude-code-source-v2.1.88`（由 npm 包的 source map 还原） | A/B 混合 |
| pi | `github.com/earendil-works/pi` shallow clone 到本机后 grep/read | A |

**关于 Claude Code 源码的诚实说明**：Claude Code 是闭源产品，只以压缩后的 JS 通过 npm 分发。§3.1 的机制描述基于本机一份社区从官方 npm 包 `@anthropic-ai/claude-code@2.1.88` 的 `cli.js.map` 中 `sourcesContent` 还原出的 **Anthropic 原始 TypeScript**（非仿写）—— 路径为 `.../02-claude-code-source-research/src/`。同时用 **v2.1.274** 的官方文档与 CLI bundle 字符串做了交叉验证。

**版本差已逐条核对**（v2.1.88 源码 ↔ v2.1.274 bundle）：

| 2.1.88 常量 | 2.1.274 状态 |
|---|---|
| `[Old tool result content cleared]` 占位符 | ✅ 仍在（4 处），语义未变 |
| `keepRecent` | ✅ 仍在，时间触发配置结构未变 |
| `gapThresholdMinutes` | ⚠️ 字段名被 minify 内联，**不能据此推断已移除** |
| `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES` | ⚠️ 标识符被内联，但熔断 telemetry 事件仍存在 → 逻辑仍在 |
| `POST_COMPACT_TOKEN_BUDGET`、`MAX_TOOL_RESULTS_PER_MESSAGE_CHARS` 等数值 | ⚠️ 数字被内联，**unverified in 2.1.274** |

另有证据表明压缩子系统在两个版本之间**有实质演进**（新增了「快速回填熔断」「前缀溢出」等路径）。**因此：本报告所有 v2.1.88 的数值常量都应按版本阅读**，公式与机制方向则可放心。我不会把内部实验代号、埋点事件名写进正文 —— 它们对工程决策没有增量。

**关于 Codex 的一个坑**：该仓库 main 分支的 `docs/` 已被抽空（`docs/config.md` 只剩 15 行）。网上流传的 `model_context_window` / `auto_compact_token_limit` 配置说明基本来自旧 tag 和第三方站点，**不能当权威**。本报告一律以当前源码为准。

---

## 2. 先分清三种「长」

「上下文太长」在工程上是三个不同的问题，混在一起谈必然方案错位：

| 类型 | 症状 | 主要解法 |
|---|---|---|
| **单次请求超限** | API 直接报 `prompt_too_long` | 硬截断、拒绝、报错兜底 |
| **单次会话累积超限** | 跑久了越来越慢/越来越贵/开始丢信息 | compaction、工具结果清理 |
| **成本与延迟** | 没超限，但每轮都重发全量历史 | prompt caching、前缀稳定、分级模型 |

三个工具的主战场都是**第二种**，但都同时处理了第一、三种。本项目目前是「**三种都没处理**」—— 见 §6。

---

## 3. 逐个拆解

### 3.1 Claude Code：六级降级流水线

这是三者中最完整的实现。核心文件在 `src/services/compact/`，主流程编排在 `src/query.ts:366-468`。

#### 3.1.1 每轮请求前的六级阶梯

```
每轮 query:
  0. getMessagesAfterCompactBoundary(messages)   // 只取上次压缩边界之后的消息
  1. applyToolResultBudget(...)                  // 单条 user 消息内 tool_result 总量封顶
  2. snipCompactIfNeeded(...)                    // 历史剪切
  3. microcompact(...)                           // 清老工具结果（按 tool_use_id）
  4. contextCollapse.applyCollapsesIfNeeded(...) // 读时投影，摘要存独立 store
  5. autocompact(...)                            // 全量 LLM 摘要（最贵，最后手段）
```

源码注释把设计意图写得很清楚：

> `// Runs BEFORE autocompact so that if collapse gets us under the autocompact threshold, autocompact is a no-op and we keep granular context instead of a single summary.`

**能不能用便宜手段压到阈值以下，决定了要不要做最贵的全量摘要。** 这是整份报告最值得抄的一条。

#### 3.1.2 阈值：绝对 token 数

`src/services/compact/autoCompact.ts:30-100`：

```ts
const MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000   // p99.99 的摘要输出是 17,387 tokens，取整到 20K
const AUTOCOMPACT_BUFFER_TOKENS      = 13_000
const WARNING_THRESHOLD_BUFFER_TOKENS = 20_000
const ERROR_THRESHOLD_BUFFER_TOKENS   = 20_000
const MANUAL_COMPACT_BUFFER_TOKENS    = 3_000
const MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3

getEffectiveContextWindowSize(model)
  = getContextWindowForModel(model)
  − min(getMaxOutputTokensForModel(model), MAX_OUTPUT_TOKENS_FOR_SUMMARY)

getAutoCompactThreshold(model)
  = getEffectiveContextWindowSize(model) − AUTOCOMPACT_BUFFER_TOKENS
```

三个细节值得注意：

- **先扣掉输出预算再算阈值**。上下文窗口是「输入+输出」共享的，不扣掉就会算出一个永远发不出去的阈值。
- **buffer 是绝对数不是比例**。比例阈值在小窗口模型上会留出不够一次摘要的空间。
- **失败了会熔断**：连续 3 次 autocompact 失败就停止重试。源码注释披露了动机 —— 曾有大量会话在单次会话内连续失败 50 次以上（最多 3,272 次），在全球范围每天浪费约 25 万次 API 调用。这是「上下文已经不可恢复地超限」时的必要保护。**任何自动重试机制都要有这个熔断**。
- **手动 `/compact` 有独立的硬阻塞线**：`effectiveWindow − MANUAL_COMPACT_BUFFER_TOKENS (3,000)`。手动压缩留的余量比自动小得多（3K vs 13K），因为手动压缩时用户在场，不需要留出「发现超限并自救」的空间。

可覆盖的环境变量：`CLAUDE_CODE_AUTO_COMPACT_WINDOW`（压低窗口上限）、`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`（百分比覆盖，取 `min(百分比阈值, 绝对阈值)`）、`CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE`。另有 `DISABLE_AUTO_COMPACT`（保留手动 `/compact`）与 `DISABLE_COMPACT`（连 `/compact` 一起禁用）。

**公式与官方文档的交叉验证**（B 级 + A 级互证）：

官方文档给出的触发点是**按模型分档**的 —— 200K 窗口的模型在 200K 边界压缩，原生 1M 窗口的模型在 **~967K** 压缩。用上面的公式反推 1M 的情况：

```
1,000,000 − min(maxOutput, 20,000) − 13,000
= 1,000,000 − 20,000 − 13,000
= 967,000                          ← 与文档的 ~967K 完全吻合
```

**这是本报告中最强的一条互证**：v2.1.88 的源码公式，精确预测了 v2.1.274 文档里的数值。说明这套阈值算法跨版本稳定。

**200K 档也已解释清楚（源码验证）**。`src/utils/context.ts:9` `MODEL_CONTEXT_WINDOW_DEFAULT = 200_000`，窗口解析优先级是：`CLAUDE_CODE_MAX_CONTEXT_TOKENS` → `[1m]` 后缀 → 模型能力表 `cap.max_input_tokens` → 1M beta → 兜底 200K。

```
200,000 − min(maxOutput, 20,000) − 13,000 = 167,000   ← 200K 档的真实触发点
```

所以**文档说的「200K 边界」是在标定档位（模型窗口），不是触发点**。两者量的是不同的东西：20K(输出预留) + 13K(缓冲) = 33K 属于「必须留出的头部空间」，不是压缩判定的一部分。

顺带解释了一个容易误读的常量：`MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000` 是对 `maxOutputTokens` 的**上限截断**（`Math.min(...)`）。Claude Code 实际默认 max output 是 **32,000**（`context.ts:15` `MAX_OUTPUT_TOKENS_DEFAULT`），被这个 cap 压到 20K。

还有一个副作用值得知道：`CLAUDE_CODE_DISABLE_1M_CONTEXT=1` 会把原生 1M 模型解析成 200K，压缩线也随之落到 167K。

用户侧的覆盖手段（v2.1.221+）：`/autocompact 500k` 或 `/autocompact auto`，取值域 100K–1M，接受 `200000` / `500k` / `1M` / 裸数字（100–1000 视为千）。优先级：`CLAUDE_CODE_AUTO_COMPACT_WINDOW` > `--autocompact` flag > `/autocompact` 写入的设置。

#### 3.1.3 工具结果：三级尺寸管控

`src/constants/toolLimits.ts`：

```ts
DEFAULT_MAX_RESULT_SIZE_CHARS        = 50_000    // 单条工具结果，超了落盘换预览
MAX_TOOL_RESULT_TOKENS               = 100_000   // ≈ 400KB
MAX_TOOL_RESULT_BYTES                = MAX_TOOL_RESULT_TOKENS * 4
MAX_TOOL_RESULTS_PER_MESSAGE_CHARS   = 200_000   // 单条 user 消息内所有 tool_result 的总量
```

第三条的设计意图，源码注释写得很准：

> `This prevents N parallel tools from each hitting the per-tool max and collectively producing e.g. 10 × 40K = 400K in one turn's user message.`

**单条上限防不住并行工具的总量爆炸。** 这是很容易漏掉的一层。

超限的行为是「**落盘 + 给模型一个带路径的预览**」，不是直接删。模型仍知道有这个文件，需要时可以自己去读。

#### 3.1.4 microcompact：清老工具结果，留着结构

`src/services/compact/microCompact.ts` + `timeBasedMCConfig.ts`。

microcompact 内部有**三条并行路径**（`microCompact.ts:253-293` 的调度顺序）：

**① 时间触发（time-based）** —— `evaluateTimeBasedTrigger()`，配置 `timeBasedMCConfig.ts`：

```ts
DEFAULTS = { enabled: false, gapThresholdMinutes: 60, keepRecent: 5 }
```

触发条件：主线程 + 距最后一条 assistant 消息 > 60 分钟。源码注释把设计意图写得很清楚：

> *"the server-side prompt cache has almost certainly expired, so the full prefix will be rewritten anyway. Clearing old tool results before the request shrinks what gets rewritten."*

**永远不要主动制造一次本来不会发生的缓存 miss** —— 但在缓存必然失效的时刻做清理是免费的。这是整份报告里最精妙的一条成本推理。

注意 `enabled: false` 是**默认值**，实际由服务端灰度下发 —— 这解释了为什么第三方逆向长期只能「看到清理发生」却找不到开关。

**② 缓存编辑（cached MC）** —— `feature('CACHED_MICROCOMPACT')`，仅主线程：

**不改本地消息**，而是通过 API 层的 `cache_edits` 块删除，从而保住缓存前缀。源码注释：*"Return messages unchanged - cache_reference and cache_edits are added at API layer"*。API 回传 `cache_deleted_input_tokens`，可以**精确知道省了多少 token**。仅对支持 cache editing 的模型生效。

**③ 内容替换** —— 按 `tool_use_id` 定位，保留最近 `keepRecent` 条，其余替换为占位符 `[Old tool result content cleared]`。只清**特定工具**的结果：`COMPACTABLE_TOOLS`（shell 类工具、Read 等）—— 即「内容可重复获取」的那些。

#### 3.1.5 压缩后的补偿：重新注水

摘要会丢掉具体代码。`src/services/compact/compact.ts:122-130`：

```ts
POST_COMPACT_MAX_FILES_TO_RESTORE   = 5       // 最近碰过的文件，最多恢复 5 个
POST_COMPACT_TOKEN_BUDGET           = 50_000  // 注水总预算
POST_COMPACT_MAX_TOKENS_PER_FILE    = 5_000   // 单个文件上限
POST_COMPACT_MAX_TOKENS_PER_SKILL   = 5_000
POST_COMPACT_SKILLS_TOKEN_BUDGET    = 25_000
```

注水的内容按 `buildPostCompactMessages()` 固定顺序拼装：

```
[compact 边界标记, 摘要, 保留的最近消息, 注水附件, hook 结果]
```

注水附件包括：最近文件、后台 agent 状态、当前计划、计划模式、已用过的 skill、MCP 指令。**这就是为什么 Claude Code 压完一次还能接着干活，而很多自制 agent 压完就失忆。**

官方文档补充的行为细节（v2.1.274，与源码快照互证）：

- 压缩后从磁盘**重新注入**：system prompt、output style、项目根 CLAUDE.md、auto memory、plan 文件。
- **最多重读 5 个最近修改的文件**；单个文件 **> 5,000 token 时降级为路径引用**（提示 `Referenced file`）—— 宁可不给内容，也不把预算吃光。
- 已调用的 skill 正文会重注入，**单 skill ≤ 5,000 token、总计 ≤ 25,000 token，超出按最旧优先丢弃，且截断保留文件头部**。
- 被摘要掉、不会自动恢复的：`paths:` 作用域规则、嵌套 CLAUDE.md —— 这些要等模型真的去读那个文件才会重新加载。
- SessionStart hook 可以通过匹配 `compact` source 来挂载自己的重注入逻辑。

注意这些数字与源码快照的 `POST_COMPACT_*` 常量（5 个文件 / 50K 总预算 / 5K 单文件）**完全一致** —— 又是一次跨版本互证。

同一文件里还有一条反向优化：**不重新注入完整 skill 列表**（约 4K tokens），因为那是纯粹的 cache creation 开销 —— 模型手里还有 SkillTool，已用过的 skill 内容也已经保留。**「注水」和「别注太多水」是同一个决定的 two sides。**

#### 3.1.6 摘要 prompt：固定 9 段骨架

`src/services/compact/prompt.ts`。要求输出 `<analysis>` + `<summary>` 两块，`<summary>` 固定 9 段：

```
1. Primary Request and Intent      用户的显式请求与意图
2. Key Technical Concepts          关键技术概念
3. Files and Code Sections          文件与代码段（含完整代码片段 + 为什么重要）
4. Errors and fixes                 错误与修复，尤其是用户的纠正
5. Problem Solving                  已解决的问题与仍在排查的
6. All user messages                所有非工具结果的用户消息（原文强调 "critical"）
7. Pending Tasks                    明确被要求但未完成的任务
8. Current Work                     摘要请求前正在做的事
9. Optional Next Step               下一步，且必须与最近请求直接相关
```

第 8、9 段和「Current Work / Next Step」的措辞是专门为**任务连续性**设计的 —— 摘要不只是压缩信息，是**交接班**。

**`<analysis>` 是草稿，会被丢掉。** 摘要调用强制模型先输出一个 `<analysis>` 块再输出 `<summary>` 块，而 `formatCompactSummary()`（`prompt.ts:311`）**只把 summary 装回上下文，analysis 直接丢弃**。

这是「用推理质量换结果质量」的典型手法：草稿块让模型有机会先梳理再归纳（提升摘要质量），但因为不进入上下文，**不占用后续任何一轮的预算**。

用户可自定义，源码明确支持**两种**写法：CLAUDE.md 里的 `## Compact Instructions` **和** `# Summary instructions`；另有 `/compact <自定义指令>`、`/rewind` 的「Summarize from here / up to here」。

#### 3.1.7 摘要调用本身的设计：复用当前上下文

这是最容易被忽略、但性价比极高的一条。

**摘要请求不是「另起一个干净请求」**，而是**复用当前会话的 system prompt、tools、history**，只在末尾追加一条 summarization instruction 作为最后一条 user message。源码侧的对应证据是 `query.ts:454` 把 `forkContextMessages: messagesForQuery` 传给了 autocompact —— 压缩调用是当前上下文的一个 fork。

后果：**缓存热的时候，`/compact` 的实际成本远低于「上下文有多大」给人的直觉**（前缀全部命中缓存）。这也解释了为什么 Claude Code 敢在每次接近阈值时都调一次 LLM 摘要 —— 它不是每轮重付一次全量输入的钱。

前提是**前缀要稳定**。如果每轮 prompt 前缀都在变，这条优惠完全享受不到，压缩就真的变成了一次全量重付。

摘要模型：**用会话当前的同一个模型**，且 v2.1.198+ 会继承会话的 extended thinking 配置（只影响摘要生成质量，不改会话设置）。

#### 3.1.8 保留最近消息，而不是全压

压缩边界上带一个 `preservedSegment`（`headUuid` / `anchorUuid` / `tailUuid`），记录哪些消息原样保留、以及保留段在链上的锚点。所有摘要路径都支持 `messagesToKeep`。

另外还有一条实验性的 **session memory compaction**（`sessionMemoryCompact.ts`）：

```ts
DEFAULT_SM_COMPACT_CONFIG = {
  minTokens: 10_000,          // 至少保留这么多 token
  minTextBlockMessages: 5,    // 至少保留这么多条带文本的消息
  maxTokens: 40_000,          // 硬上限
}
```

思路是**后台持续抽取「会话记忆」**，压缩时优先复用已抽好的记忆，而不是每次现场让 LLM 重新读一遍全量历史。这是把压缩从「同步阻塞的大调用」变成「异步持续的小调用」。

#### 3.1.9 其他相关机制（简述）

- **压缩后清理缓存**（`postCompactCleanup.ts`）：压缩会让大量缓存失效，所以要主动清掉 CLAUDE.md 解析缓存、权限审批缓存、会话消息缓存等。注意子 agent 压缩时**不能**清主线程的模块级状态（同进程共享）。
- **`/context` 类可视化**：把「还剩多少上下文」直接暴露给用户，而不是让用户在撞墙时才发现。
- **外部化记忆**：memory 工具把内容写到 `CLAUDE.md` / 记忆文件里，属于「写到磁盘再用检索取回」，是压缩之外的第二条路。
- **子 agent 上下文隔离**：子 agent 有独立窗口，只把结论带回主线程 —— 相当于「用进程边界做上下文预算」。

---

#### 3.1.10 API 层的 context editing（给「自己写 agent」的人看）

Claude Code 的一部分清理能力不在客户端，而在 **Claude API 服务端**。这是本报告里对第三方 agent 最有直接价值的一节。

Beta header：`context-management-2025-06-27`。请求里声明：

```json
"context_management": { "edits": [
  { "type": "clear_thinking_20251015", "keep": { "type": "thinking_turns", "value": 2 } },
  { "type": "clear_tool_uses_20250919",
    "trigger":        { "type": "input_tokens", "value": 30000 },
    "keep":           { "type": "tool_uses",  "value": 3 },
    "clear_at_least": { "type": "input_tokens", "value": 5000 },
    "exclude_tools":  ["web_search"] }
] }
```

要点：

- **客户端仍然要发完整历史**，清理发生在服务端（省的是模型侧 token，不是上传带宽）。
- 默认值：`trigger` = 100,000 input tokens，`keep` = 3 tool uses，`clear_tool_inputs` = false。
- **`clear_thinking_20251015` 必须排在数组首位**（顺序有语义）。
- 可以用 `count_tokens` 接口**预览**效果，返回 `original_input_tokens`；响应里回读 `context_management.applied_edits`（流式在最后一个 `message_delta`）。
- `clear_at_least` 要**足够大以抵消缓存失效成本** —— 官方明确说清得太少反而亏。这和 §3.1.4 的时间触发清理是同一个经济学。
- `exclude_tools` 用来保护「必须常驻」的工具。
- 官方建议配合 memory tool：**在清理发生前让模型把关键结果写进记忆文件**（API 会在接近阈值时自动给模型警告）。

另有服务端压缩 `compact_20260112`（beta header `compact-2026-01-12`），把压缩本身也搬到服务端。

**对本项目的意义**：本项目走的是 OpenAI-compatible 接口（`core/model_provider.py`），**用不了这套服务端能力**。所以下面 §5 的模式必须**在客户端自实现等价物** —— 这恰好也是 Codex 和 pi 的做法（它们在客户端做，因为要支持多家 provider）。**这反过来证明：客户端自实现不是降级方案，而是多 provider 场景下的必然选择。**

#### 3.1.11 Prompt caching：压缩的经济学前提

这一节放在最后，但**它是前面所有机制成立的前提**。没有缓存，压缩就是纯粹的损失；有了缓存，压缩才是净收益。

官方文档：<https://code.claude.com/docs/en/prompt-caching>

**① 请求按「变化频率」分层排序**（官方的 stable-content-first 指导）：

```
system prompt（含工具定义）  →  project context（CLAUDE.md / auto memory / 无作用域规则）  →  conversation
```

改 conversation 层不影响前两层；**改 system prompt 层则全量失效**。Claude Code 发送**显式 `cache_control` 断点**（[API 文档](https://platform.claude.com/docs/en/build-with-claude/prompt-caching#explicit-cache-breakpoints)）。**如果中间有网关把该标记剥掉，整个历史每轮按未缓存计费** —— 这是一个很容易在自建网关上踩到的坑。

**② 两档 TTL，按用途分配**：

| 场景 | 默认 TTL |
|---|---|
| 订阅内主对话 | **1 小时** |
| subagent / workflow / teammate / **compaction** / session title | **5 分钟** |
| API key 或云厂商接入 | 一律 5 分钟 |

控制项：`promptCacheTtl` / `CLAUDE_CODE_PROMPT_CACHE_TTL`（主对话）、`subagentPromptCacheTtl` / `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`（其余）、subagent frontmatter 的 `experimental.cacheTtl`；最高优先的是 `ENABLE_PROMPT_CACHING_1H=1` / `FORCE_PROMPT_CACHING_5M=1`。需 v2.1.242+。

**③ 成本数学（这才是压缩的核心矛盾）**：缓存读约为主线输入价的 **10%**。长会话每轮都重发全量历史 —— 但命中缓存时只付约 10%。

- **`/compact` 本身**：摘要请求复用**相同的 system prompt / tools / history**（§3.1.7），温缓存下命中前缀，**成本远低于上下文体积给人的直觉**；冷缓存（空闲超过 TTL）时全额重算 —— 这就是「恢复旧会话后立刻 `/compact` 最贵」的原因。
- **压缩之后**：对话层缓存**设计上必然失效**（新历史与旧前缀不共享）。但重建的**绝对量小**（只剩摘要 + 保留尾），所以压缩后的那一轮并不慢。
- **`/rewind` vs `/compact`**：想彻底放弃某条路径，用 `/rewind`（**截断回已缓存的前缀**），而不是 `/compact`（生成一段新历史，缓存必然重建）。

**④ 失效清单**（官方）：切模型（每模型独立缓存）、改 effort level、开 fast mode、MCP server 连/断（**仅当工具定义进前缀时**；延迟加载则不失效）、启用/禁用改变工具集的插件、把整个工具加进 deny 规则、**压缩**、堆积图片（按批移除最旧的）、升级 Claude Code。

**⑤ 保住缓存的**（官方）：编辑仓库文件、编辑 CLAUDE.md、切权限模式、切 output style、调用 skill/command、`/recap`、`/rewind`、spawn subagent。

**这一节对自建 agent 的直接启示**：缓存策略不是优化项，是**架构约束**。它反过来决定了 prompt 必须怎么拼（稳定内容在前、动态内容在后）、工具定义必须怎么管（别每轮变）、以及一次性调用（摘要、标题生成）必须**显式禁用缓存写入**，否则会污染会话的缓存键 —— pi 就明确这么做了，见 §3.3.10。

---

### 3.2 Codex：阈值触发 + 整体替换

Rust 实现。整体比 Claude Code 简单，但有几个设计点比 Claude Code 更激进。

#### 3.2.1 两条上限：软阈值 + 硬上限

`codex-rs/core/src/session/context_window.rs::context_window_token_status()`：

```rust
let full_context_window_limit = model_info.resolved_context_window()
    .map(|w| w.saturating_mul(model_info.effective_context_window_percent) / 100);
let token_limit_reached =
    buffered_auto_compact_limit.is_some_and(|l| auto_compact_scope_tokens >= l)
    || full_context_window_limit_reached;
```

软阈值来自 `codex-rs/protocol/src/openai_models.rs:521`：

```rust
pub fn auto_compact_token_limit(&self) -> Option<i64> {
    let context_limit = self.resolved_context_window().map(|w| (w * 9) / 10);
    let config_limit = self.auto_compact_token_limit;
    if let Some(context_limit) = context_limit {
        return Some(config_limit.map_or(context_limit, |l| std::cmp::min(l, context_limit)));
    }
    config_limit
}
```

关键点：**配置值只能调低，不能调高**（`min`）。用户没法把自动压缩关掉来「赌一把」。

`effective_context_window_percent` 默认 **95**，是比 90% 软阈值更靠后的硬防线。

模型目录 `codex-rs/models-manager/models.json` 里默认模型：`context_window: 272000` → 软阈值 244,800；硬上限 258,400。

配置键（`codex-rs/core/src/config/mod.rs:628-635`）：`model_context_window`、`model_auto_compact_token_limit`、`model_auto_compact_token_limit_scope`（`Total` | `BodyAfterPrefix`）、`tool_output_token_limit`。

触发时机分三个 phase：`PreTurn`（回合前）、`MidTurn`（回合中，工具结果把窗口顶爆时）、`StandaloneTurn`（手动 `/compact`）。

额外的一条：模型可以调用 **`new_context_window` 工具主动要求换新窗口**（`core/src/tools/handlers/new_context_window.rs`），**完全不经过摘要**。也就是把「我要不要清空重来」的判断权部分交给了模型自己。

#### 3.2.2 压缩 = 整体替换

`codex-rs/core/src/compact.rs::run_compact_task_inner_impl()`：

```rust
let user_messages = collect_annotated_user_messages(history_items, identity);
let mut new_history = build_compacted_history(Vec::new(), &user_messages, &summary_text);
sess.replace_compacted_history(new_history, ...);
```

**整个历史被替换掉**，而不是原地修剪：

- **保留**：摘要 + 最近的用户消息，且用户消息是「**从最新往最旧收集，总量 ≤ 20K tokens**」，不是「前 N 条」。

```rust
const COMPACT_USER_MESSAGE_MAX_TOKENS: usize = 20_000;  // codex-rs/core/src/compact.rs:60
```

- **丢弃**：所有 assistant 回复、所有 tool call 及其 output。
- **摘要位置固定在最后**（`build_compacted_history` 末尾 push `CompactionSummary`）。

有测试快照把形状钉死了（`codex-rs/core/tests/suite/snapshots/all__suite__compact__manual_compact_with_history_shapes.snap`）：

```
[user msg..., COMPACTION_SUMMARY, PERMISSIONS_INSTRUCTIONS, ENVIRONMENT_CONTEXT, 新 user turn]
```

「保留最近的用户消息」这个选择很务实：**用户的意图是整段历史里最难从别处重建的信息**，而 assistant 回复和工具输出多数可以从环境重新获取。

#### 3.2.3 三种压缩后端

手动 `/compact` 与自动压缩**共用同一实现**，只差 `CompactionTrigger` / `CompactionPhase`。但底层有三条分支：

1. `Feature::TokenBudget` 开启 → **不摘要**，直接 `start_new_context_window()` 换新窗口。
2. `RemoteCompactionSupport::V2` → 服务端压缩。
3. 都不支持 → 本地 LLM 摘要。

第 1 条很值得注意：**存在一条「不摘要、直接换窗」的路径**。当上下文里有大量可重新获取的内容时，摘要反而是在花钱生成一份更差的副本。

#### 3.2.4 摘要 prompt

`codex-rs/prompts/templates/compact/prompt.md`（`SUMMARIZATION_PROMPT`，经 `include_str!` 编译进二进制）+ `summary_prefix.md`。

前缀就是流传很广的那句 "Another language model started to solve this problem and produced a summary of its thinking process…"。**这句话本身就是一次上下文交接的显式声明** —— 让模型知道「你读到的不是原始对话，是二手摘要」，从而对摘要保持怀疑。

可覆盖：配置 `compact_prompt`（字符串）或 `experimental_compact_prompt_file`（路径）。解析优先级 `compact_prompt` > 文件 > 内置（`config/mod.rs:3880-3946`）。

#### 3.2.5 工具输出：head + tail 中间挖空

`codex-rs/utils/output-truncation/src/lib.rs` + `codex-rs/utils/string/src/truncate.rs`：

```rust
const APPROX_BYTES_PER_TOKEN: usize = 4;   // 不用 tiktoken，硬编码 4 字节/token

fn split_budget(budget: usize) -> (usize, usize) {
    let left = budget / 2;
    (left, budget - left)          // 头尾各一半，中间挖掉
}
```

标记文本：`…{N} tokens truncated…` / `…{N} chars truncated…`，带 header 的版本是：

```
Warning: truncated output (original token count: N)
Total output lines: M
```

**为什么是中间挖空而不是只留头**：编译错误、测试失败、堆栈的关键行常常在**尾部**；只留头会恰好丢掉最有用的部分。这是从工程经验里长出来的设计，不是随手写的。

其他细节：

- 默认预算 10,000 tokens（来自模型目录的 `truncation_policy.limit`），可被 `tool_output_token_limit` 覆盖。
- 序列化余量：`budget * 1.2`（+20% 给 serialization/headers）。
- 多段 content 逐条丢弃，追加 `[omitted {n} text items ...]` / `[omitted {n} audio items ...]`。

#### 3.2.6 结构完整性：孤儿清理

`codex-rs/core/src/context_manager/normalize.rs`：

- `ensure_call_outputs_present()` —— 给缺失输出的 tool call 补一个合成输出。
- `remove_orphan_outputs()` —— 删掉没有对应 call 的输出。

这是**消息级裁剪的前置条件**：只要你想删历史里的任意一条消息，就可能拆散 `tool_use` / `tool_result` 配对，而多数 API 会直接报错。**任何裁剪策略都必须先有这一步。**

另外图像有单独的估算口径：`RESIZED_IMAGE_BYTES_ESTIMATE = 7373` bytes ≈ 1844 tokens。

#### 3.2.7 压缩请求自己放不下怎么办

`compact_remote_history.rs::trim_function_call_history_to_fit_context_window()` —— 从**尾部往前**扫，把 function call/output 组重写为空占位，直到塞进 `context_window`。

**「为了压缩而构造的请求本身也可能超限」** —— 这是长上下文工程里最容易被忽略的死角。

#### 3.2.8 Token 计量

服务端优先 + 本地估算兜底（`context_manager/history.rs:759`）：

```
总用量 = 上一次服务端返回的 usage.total_tokens
       + 其后新增条目的 estimate_item_token_count()   // 按可见字节 / 4
```

即：**不为了算 token 而额外发一次请求**，用「服务端真值 + 本地增量估算」的混合口径。压缩后调 `recompute_token_usage()` 重算。

#### 3.2.9 Rollout 与 resume

会话以 JSONL 持久化，`RolloutItem` 枚举里有一项 **`Compacted(CompactedItem)`**，记录 `window_number` 和窗口 UUID 链。

resume 走 `rollout_reconstruction.rs::reconstruct_history_from_rollout()`：**从最新往最旧扫，停在最后一个存活的 compaction checkpoint，再正向重放存活尾部**。

结果：**恢复的就是压缩后的历史，被压掉的内容不会回来，resume 时也不会重新压缩。** 压缩是**不可逆的持久化操作**，不是运行时的临时视图。

#### 3.2.10 其他

- **初始上下文重注入**：压缩时 `InitialContextInjection` 两态 —— `DoNotInject`（PreTurn / 手动：清空，下一轮完整重注入）vs `BeforeLastUserMessage`（MidTurn：插到最后一条真实 user 消息之上）。这解释了 AGENTS.md / 权限 / 环境信息为什么压完还在。`AGENTS_MD_MAX_BYTES` = 32 KiB。
- **压缩后主动警告用户**（`compact.rs:400`）：长线程与多次压缩会让模型准确率下降，建议开新线程。**把「压缩是有损的」这一事实显式告诉用户**，而不是假装无损。
- **PreCompact / PostCompact hook** 可以介入甚至中断压缩。
- `comp_hash`：模型元数据里带这个，用于判断跨模型切换后旧摘要是否仍然兼容。

---

### 3.3 pi：按 token 预算切一刀 + 增量摘要

TypeScript / MIT，仓库 `github.com/earendil-works/pi`（原 `badlogic/pi-mono`，git 仍可 clone），包名 `@earendil-works/*`。核心在 `packages/coding-agent/src/core/compaction/`（`compaction.ts` 1027 行、`branch-summarization.ts` 382 行、`utils.ts` 158 行）。

> **引用陷阱**：仓库里有一套**实验性**的平行实现 `packages/agent/src/harness/compaction/`（基于 `retainedTail` + sqlite 会话层），只被 `experimental/mini/**` 使用。两者的常量一致但代码不同。**本节一律引用正式 CLI 路径 `packages/coding-agent/src/core/compaction/`。**

三家里实现最简单，但**有两个独有设计**（增量摘要、分支摘要），而且**摘要 prompt 的工程质量最高**。

#### 3.3.1 触发：同一套「窗口 − 预留」

`packages/coding-agent/src/core/compaction/compaction.ts:143-150, 250-252`：

```ts
export interface CompactionSettings {
  enabled: boolean;
  reserveTokens: number;       // 留给摘要 prompt 与输出
  keepRecentTokens: number;    // 压缩后保留的近期上下文预算
}

export const DEFAULT_COMPACTION_SETTINGS: CompactionSettings = {
  enabled: true,
  reserveTokens: 16_384,
  keepRecentTokens: 20_000,
};

export function shouldCompact(contextTokens, contextWindow, settings): boolean {
  return contextTokens > contextWindow - settings.reserveTokens;
}
```

**和 Claude Code 的 `window − 13_000` 是同一个形状。** 三家独立演化出「绝对预留量」而非百分比，这件事本身就说明了结论的稳健性。

pi 有**四个触发点**，其中一个在回合中间（`_compactBeforeNextAssistantResponse` → `agent.prepareNextTurnWithContext`，是为解决 issue #6879 引入的）。也就是说：**工具结果把窗口顶爆时，pi 会在生成下一条 assistant 回复之前插入一次压缩**，而不是等这一轮跑完。

#### 3.3.2 切点按 token 预算，不按条数

`compaction.ts:418-444` 的 `findCutPoint(entries, start, end, keepRecentTokens)`：**从尾部往前累加每条消息的估算 token，累到 `keepRecentTokens` 就停**，切点即在此（`:793` 调用）。

- 切点**之前** → 全部送进摘要器
- 切点**之后** → 原样保留在上下文里

对比：Codex 是「保留最近的用户消息 ≤ 20K」，pi 是「保留最近的**所有**消息 ≤ 20K」。pi 保留得更完整（assistant 回复和工具结果都在），代价是同样预算下能回溯的轮次更少。

#### 3.3.3 摘要 prompt：6 段 checkbox 骨架

`compaction.ts:482`，`SUMMARIZATION_PROMPT` 要求输出**固定格式**：

```markdown
## Goal
[用户想达成什么？可多项]

## Constraints & Preferences
- [用户提到的约束/偏好]（无则写 "(none)"）

## Progress
### Done
- [x] [已完成]
### In Progress
- [ ] [进行中]
### Blocked
- [问题阻塞]

## Key Decisions
- **[决策]**：[理由]

## Next Steps
1. [有序列表]

## Critical Context
- [继续工作所需的数据/示例/引用]
```

三个值得抄的点：

1. **Progress 用 checkbox 语法**，Done / In Progress / Blocked 三态。模型天然会维护这个结构，且「从 In Progress 移到 Done」是一个可验证的状态迁移。
2. **Key Decisions 强制带理由**（`**[决策]**：[理由]`）。理由比决策本身更容易在摘要里丢失，而**丢了理由，后续 agent 就会推翻已有决策**。
3. **`"(none)"` 占位**。明确要求空段也要写占位符，避免模型把空段整个省略 —— 省略之后就无法区分「没有约束」和「摘要没提」。

配套的 system prompt 只有两句，但把边界钉死了：

```
Do NOT continue the conversation. Do NOT respond to any questions in the conversation.
ONLY output the structured summary.
```

**摘要器不许接着对话** —— 这是摘要调用最常见的失败模式。

#### 3.3.4 增量摘要（三家独有）

`compaction.ts:552` 的 `UPDATE_SUMMARIZATION_PROMPT`。当已有摘要存在时（`previousSummary` 非空），不再重新总结全量历史，而是：

```
<conversation>...新消息...</conversation>
<previous-summary>...已有摘要...</previous-summary>

The messages above are NEW conversation messages to incorporate into the existing summary.
RULES:
- PRESERVE all existing information from the previous summary
- ADD new progress, decisions, and context from the new messages
- UPDATE the Progress section: move items from "In Progress" to "Done" when completed
- PRESERVE exact file paths, function names, and error messages
- If something is no longer relevant, you may remove it
```

`compaction.ts:693` 的分支：

```ts
let basePrompt = previousSummary ? UPDATE_SUMMARIZATION_PROMPT : SUMMARIZATION_PROMPT;
if (customInstructions) basePrompt = `${basePrompt}\n\nAdditional focus: ${customInstructions}`;

// 摘要输出预算：reserveTokens 的 80%
const maxTokens = Math.min(
  Math.floor(0.8 * reserveTokens),
  model.maxTokens > 0 ? model.maxTokens : Number.POSITIVE_INFINITY,
);
```

注意 `0.8 * reserveTokens`：**预留的 16,384 token 里，80% 给输出，剩下 20% 留给 prompt 本身**。这是一个很实在的细节 —— 预留量不是一个数字，是一份要拆开用的预算。

**为什么这是三者中最聪明的做法**：每次都全量重摘要，等于每压一次就把前面的信息**再丢一次**（摘要的摘要）。摘要是有损函数，反复应用会单调退化。增量更新把每次的有损操作限制在**新增的那部分消息**上，已固化的摘要只做字符串级的 merge。

配套的 `reserveTokens = 16_384` 正好覆盖「摘要 prompt + 输出」—— 因为增量模式下每次要处理的新消息是有限的一批，不是整个历史。

#### 3.3.5 文件操作结构化记录

`utils.ts` 的 `extractFileOpsFromMessage()` / `computeFileLists()` / `formatFileOperations()`：

```ts
extractFileOpsFromMessage(message, fileOps)   // 从消息里抽取 read / edited / written
computeFileLists(fileOps)                     // → { readFiles, modifiedFiles }
formatFileOperations(readFiles, modifiedFiles)
  → "<read-files>\n...\n</read-files>\n\n<modified-files>\n...\n</modified-files>"
```

这套标签会**附加在摘要后面**一起交给下一个上下文。

对比 Claude Code 的「重读最近修改的 5 个文件」：pi 的做法**读和改分开记录，且不占内容预算** —— 只给路径，模型需要时自己去读。在「文件多、每个文件大」的场景下，`<read-files>` 的信息密度远高于把 5 个文件内容硬塞回去。

#### 3.3.6 turn 级前缀摘要（三家独有）

`compaction.ts:709`：

```
This is the PREFIX of a turn that was too large to keep. The SUFFIX (recent work) is retained.
```

**单个 turn 本身就大到放不下**时（比如一个 turn 里跑了 30 个工具），pi 保留这个 turn 的后半段，把前半段摘要掉。

Codex 和 Claude Code 都在「工具结果」或「整段历史」这两个粒度上做截断，**只有 pi 处理了「单个 turn 撑爆上下文」这个中间粒度**。在长任务里（一个 turn 跑十几分钟）这是真实场景。

#### 3.3.7 分支摘要（三家独有）

`branch-summarization.ts`。pi 的会话是一棵树（支持 `/tree`、`/fork`、分支切换）。当你从某个历史节点分叉出去，**原来那条被放弃的分支会被压成一条 `branch-summary` entry**：

```ts
export interface BranchSummaryResult {
  summary: string;
  usage?: Usage;
  readFiles: string[];
  modifiedFiles: string[];
}
```

意义：分支之前的探索过程不丢失。**「我试过 A 方案，失败在 X」这类信息，在没有分支摘要的工具里是随分支一起被删掉的**，而在 pi 里它变成新分支的上下文。

这是「上下文管理」被推广到了**跨会话树的结构**，而不只是单条线性历史。

#### 3.3.8 工具输出：两层截断（活上下文 + 摘要输入）

> **修正说明**：我一开始只看到了第二层，误以为 pi 在活跃上下文里不截断。实际是**两层都有**，且第一层的数值是硬编码的。

**第一层：活上下文里按工具硬编码截断**（`packages/coding-agent/src/core/tools/truncate.ts:11-13`）：

```ts
export const DEFAULT_MAX_LINES = 2000;
export const DEFAULT_MAX_BYTES = 50 * 1024;        // 50KB
export const GREP_MAX_LINE_LENGTH = 500;           // 单条 grep 匹配行的最大字符数
```

其余上限：grep 最多 100 条匹配、find 1000 条、ls 500 条。

关键设计：**`truncateHead` 和 `truncateTail` 两个函数都存在，按工具语义选用**（`:78` / `:168`）：

- 读文件 → `truncateHead`（**留头**，因为文件开头是 import 和定义）
- 命令输出 → `truncateTail`（**留尾**，因为错误和结果是最后才打印的）

对比 Codex 一律用 head+tail 中间挖空：**pi 按「哪一端有信息」分别选择，比一律挖中间更精细**。

注意 pi **没有**中心化的「单条工具结果 token 预算」，也没有单条消息的聚合上限（Claude Code 有 200K chars 的那一层），而且这些数字**不可配置**。

**第二层：构造摘要输入时再砍一刀**（`utils.ts:89`）：

```ts
const TOOL_RESULT_MAX_CHARS = 2000;

function truncateForSummary(text: string, maxChars: number): string {
  if (text.length <= maxChars) return text;
  const truncatedChars = text.length - maxChars;
  return `${text.slice(0, maxChars)}\n\n[... ${truncatedChars} more characters truncated]`;
}
```

即使活上下文里的工具结果已经过了第一层（最大 50KB），送进摘要器之前还会再砍到 **2000 字符**。

设计取舍很务实：**摘要器需要的是「这里发生了什么」而不是「完整输出」**。压缩的是喂给摘要器的输入，保证摘要调用本身不会超限 —— 这正是 Codex 要专门写 `trim_function_call_history_to_fit_context_window()` 解决的问题，pi 用更早、更简单的一道截断规避了。

#### 3.3.9 Token 计量：又是同一套混合口径

`compaction.ts` 的 `calculateContextTokens()` / `getLastAssistantUsage()` / `estimateTokens()`：

```ts
export function calculateContextTokens(usage: Usage): number {
  return usage.totalTokens || usage.input + usage.output + usage.cacheRead + usage.cacheWrite;
}

export function getLastAssistantUsage(entries: Entry[]): Usage | undefined {
  // 从尾部往前找最后一条 stopReason 不是 aborted/error、且 usage > 0 的 assistant 消息
}

export function estimateTokens(message: AgentMessage): number {
  // ...累加文本长度，图片按 ESTIMATED_IMAGE_CHARS 计
  return Math.ceil(chars / 4);
}
```

`ContextUsageEstimate` 结构体明确区分了 `tokens`（总估算）与 `usageTokens`（最后一次 provider 真实 usage）—— 就是「服务端真值 + 其后增量估算」。

**三家在这一点上完全一致**（见 §4.4）。

#### 3.3.10 resume：不重放历史

`packages/coding-agent/src/core/session-manager.ts:429` 的 `buildContextEntries()`：

```
返回 [最新的 compaction, 从 firstKeptEntryId 开始的保留尾, 其后的所有条目]
```

**被压掉的条目在 resume 时直接被丢弃，不重放。** 这和 Codex 的 `reconstruct_history_from_rollout()`（从最后一个存活 checkpoint 重放）是同一个设计决定：**压缩是一次持久化的、不可逆的操作，不是运行时的临时视图。**

好处：压缩的代价只付一次。坏处：**压错了没法回头** —— 所以三家的压缩都是「宁可保守，不要激进」。

#### 3.3.11 provider 层的缓存策略（跨供应商）

pi 要支持 8 个 API 模块（Anthropic / OpenAI Completions / OpenAI Responses / Codex / Bedrock / Mistral 等），所以它的缓存抽象比 Claude Code 复杂 —— 这一节对**接了多家 OpenAI-compatible 供应商的项目**（比如本项目）特别有参考价值。

**统一抽象**（`packages/ai/src/types.ts`）：

```ts
type CacheRetention = "none" | "short" | "long";
```

**OpenAI 系和 Anthropic 的机制不同**：Anthropic 用显式 `cache_control` 断点；OpenAI 是**隐式缓存，用一个请求字段作为缓存键**：

```ts
prompt_cache_key: cacheRetention === "none" ? undefined : clampOpenAIPromptCacheKey(options?.sessionId)
prompt_cache_retention: "24h"   // 仅当 cacheRetention === "long"
```

即 **OpenAI 侧的缓存键就是 session id**（并按码点截断到长度上限 —— 注意是**码点不是字节**，中文 session id 不会被截坏）。

**三个厂商的 usage 口径被归一化**（同一个文件里）：OpenAI 的 `prompt_tokens_details.cached_tokens`、**DeepSeek 的 `prompt_cache_hit_tokens`**、Kimi 的顶层 `usage.cached_tokens`。

这一条对本项目有直接意义：**`calculateContextTokens()` 把 `cacheRead` 加进总量**，所以如果某家供应商的缓存读取字段没被解析，会**低估上下文 → 压缩触发得太晚**。本项目走 DeepSeek-compatible 接口（`core/model_provider.py`），`prompt_cache_hit_tokens` 必须计入。

**最关键的一条工程细节**：压缩与分支摘要调用**显式禁用缓存写入** —— 传 `cacheRetention: "none"` + 一个全新的 session id。理由：**一次性调用的 prompt 不应该污染会话的缓存键**。这和 Claude Code 把 compaction 的 TTL 单独设为 5 分钟（§3.1.11）是同一个思路的两种实现。

#### 3.3.12 渐进披露：给路径，不给内容

pi 的 system prompt 里有三处「只给路径/元信息，内容按需读取」的设计：

**① `<docs>` 路由**（`system-prompt.ts:153-160`）：注入约 **1KB** 的**绝对路径与读取规则**，指向 pi 自己的文档。实际体量：`README.md` 33,107 字节 + `docs/` 479,283 字节（30 个文件）+ `examples/` 32,836 字节 markdown。

**约 0.5MB 的文档通过 `read` 按需可达，prompt 里只占约 1KB。** 而且这有官方的 A/B 评测（`packages/evals/README.md`，`with_docs` / `without_docs` 两个变体，会在容器里删掉文件并剥掉该段）。

**② skills 只给元信息**：`formatSkillsForPrompt()` 只内联 `name` / `description` / `location`，**SKILL.md 正文不内联**，按需读取。`disable-model-invocation: true` 的 skill 直接过滤掉。注意这里**没有总量上限**，只有单条校验警告（名称 64 字符、描述 1024 字符）且不会截断 —— 一个多行长描述可以无限制地撑大这一段。

**③ 工具按需加载（两层）**：

- **账本层**：system prompt 以**增量重放协议**传输，而不是每轮重发 —— `SystemMessage` 携带 `sections` diff 以及 `toolsAdded` / `toolsRemoved`（`packages/ai/src/types.ts`）。
- **线上层（关键）**：Anthropic 侧用 `defer_loading: true` 声明后续工具，按需通过 `tool_addition` / `tool_removal` content block 引入（beta header `mid-conversation-tool-changes-2026-07-01`）；OpenAI Responses 侧用 `additional_tools` developer message 或合成的 `tool_search_call` / `tool_search_output` 对；**不支持这些能力的模型回退为每轮重发完整工具列表**。
- 有个细节很说明问题：pi 会从**第一个请求**起就声明一个占位工具 `__pi_deferred_placeholder__`（同样 `defer_loading: true`），目的纯粹是让 Anthropic 的延迟工具脚手架落进**已缓存的前缀**。注释说这是实测过的 —— 没有它会导致全量 cache miss。

**设计目标明确是「工具变化时不破坏 prompt 缓存」**，和 §3.1.11 的分层排序是同一个约束的两个侧面。

> **一条常见的错误说法**：网上流传「pi 按需从 README 加载工具描述」。**这是错的** —— pi 每个内置工具的描述都是硬编码的（8 个工具合计约 1,849 字符）。真正的渐进披露是上面三条：工具**加载**、`<docs>` 路由、skills。

#### 3.3.13 pi 明确「不做」的事

grep 验证的负面清单，同样有信息量：

- **没有 microcompaction**（不像 Claude Code 有独立的老工具结果清理路径）
- **没有图像丢弃**
- **没有 thinking block 清理**

pi 的策略是「**不逐条清理，到点整段压缩**」。代价是压缩前上下文会一直涨；好处是逻辑简单、行为可预测。

唯一的例外是跨模型切换：`transform-messages.ts` 会在换模型时处理 thinking block（redacted 的丢弃，其余降级为纯文本）。

---

## 4. 横向对比

### 4.1 触发条件

| | Claude Code | Codex | pi |
|---|---|---|---|
| 软阈值 | `effectiveWindow − 13_000` | `window × 90%` | `window − 16_384` |
| 硬上限 | 有 blocking limit（可 env 覆盖） | `window × 95%` | — |
| 警告线 | `阈值 − 20_000` | — | — |
| 可否放宽 | env 可覆盖 | 配置只能调低 | settings 可配 |
| 熔断 | 连续失败 3 次停止重试 | — | — |

**三家都是「窗口减去一个绝对预留量」**，没有一家用纯百分比。

| | 预留量 | 理由 |
|---|---|---|
| Claude Code | 13,000 | 摘要输出 p99.99 是 17,387，另扣 20,000 输出预算 |
| Codex | 10% of window | 再叠一条 95% 硬上限 |
| pi | 16,384 | 恰好覆盖摘要 prompt + 输出 |

绝对量的好处：**「压缩本身要花多少 token」是个常数，不是窗口的比例**。小窗口模型按比例留会不够用。

### 4.2 保留策略

| | Claude Code | Codex | pi |
|---|---|---|---|
| 历史结构 | 增量修剪 + 边界标记，保留段有 UUID 锚点 | 整体替换 | 整体替换 |
| 最近消息 | `preservedSegment` + session memory（`minTokens=10K`） | 最近的**用户**消息 ≤ 20K | 最近的**所有**消息 ≤ 20K |
| assistant 回复 | 摘要 + 注水替代 | 全部丢弃 | 保留最近部分 |
| 工具输出 | microcompact 分级清理 | 全部丢弃（压缩时） | 保留最近部分；摘要输入侧截 2000 字符 |
| 压缩后 | 注水文件/计划/skill（≤50K） | 重注入 AGENTS.md/权限/环境 | 附 `<read-files>`/`<modified-files>` |
| 摘要方式 | 全量重摘要 | 全量重摘要 | **增量更新已有摘要** |

三种典型取舍：

- **Claude Code 追求连续性与可恢复性**（保留段 + UUID 锚点 + 注水），代价是复杂度最高。
- **Codex 追求简单与确定性**（整体替换 + 测试快照钉死形状），代价是 assistant 回复和工具输出全丢。
- **pi 追求信息保留率**（保留所有角色的最近消息 + 增量摘要），代价是同样预算下能回溯的轮次更少。

没有一家是错的。区别在**产品形态**：Claude Code 要支持长时间连续对话与 resume 精确回放；Codex 更接近「一次任务一个线程」；pi 的会话是一棵可分支的树，所以要为跨分支的信息保留做额外设计。

### 4.3 工具输出

| | Claude Code | Codex | pi |
|---|---|---|---|
| 单条上限 | 50K chars → 落盘换预览 | 10K tokens（×1.2 余量） | — |
| 单条消息总量 | 200K chars（防并行工具爆炸） | — | — |
| 截断方式 | 落盘，模型可按需重读 | head+tail 中间挖空 | 摘要输入侧只留头 2000 字符 |
| 内容级清理 | 按 `tool_use_id` 清老结果，保留最近 N 条 | 压缩时整体丢弃 | 随切点一起进摘要 |
| 时间维度 | 缓存必然过期时顺手清理 | — | — |

**三个不同的答案**：

- Claude Code：**不删，落盘**。信息不丢，模型需要时自己读回来。
- Codex：**只留头尾**。因为关键错误信息常在尾部。
- pi：**活跃上下文不激进截断，但在喂给摘要器时截到 2000 字符**。压缩的是摘要器的输入，不是模型的工作记忆。

### 4.4 三条强趋同（三家独立收敛到同一答案）

这几点比差异更重要 —— 独立演化出的共识通常意味着约束是真实存在的：

1. **都用「窗口 − 绝对预留量」做阈值**，不用百分比。
2. **都用「服务端 usage 真值 + 本地字符估算增量」的口径计数**：
   - Codex `history.rs:759`
   - Claude Code `utils/tokens.ts:226` `tokenCountWithEstimation()`
   - pi `compaction.ts:162-215` `calculateContextTokens()` + `getLastAssistantUsage()`

   而且**三家都用 `chars / 4` 作为估算比**（Codex `APPROX_BYTES_PER_TOKEN=4`、Claude Code `bytesPerToken=4`、pi `Math.ceil(chars / 4)`）。**没有一家为了算 token 而多打一次 API。**
3. **都把「压缩是有损的」显式告知用户**：Claude Code 用状态栏显示 `% until auto-compact`，Codex 在压缩后弹 Warning 建议开新线程，pi 的摘要里保留 `<read-files>` 让模型知道哪些文件需要重读。

另有一条**方向性共识**：**用户的原始意图是最不可再生的信息**。三家都优先保住用户消息（原文或摘要），而把 assistant 回复和工具输出当作可重新获取的。Claude Code 的 9 段骨架里第 6 段就是 "All user messages"，并注明 *critical*。

### 4.5 缓存策略对比

缓存不是「优化项」，而是**约束条件** —— 它反过来决定了 prompt 怎么拼、工具定义怎么管、一次性调用怎么做。

| | Claude Code | pi |
|---|---|---|
| Anthropic 侧机制 | 显式 `cache_control` 断点 | `cache_control` 断点（3 个） |
| OpenAI 侧机制 | —（仅 Anthropic 模型） | **`prompt_cache_key` = session id**（隐式缓存） |
| TTL 分档 | 主对话 1h；subagent/压缩/标题 5m | `CacheRetention = "none" \| "short" \| "long"` |
| 长 TTL | `ENABLE_PROMPT_CACHING_1H=1` | `prompt_cache_retention: "24h"` |
| 前缀分层 | system prompt → project context → conversation | 同左（stable content first） |
| 一次性调用 | compaction 单独用 5m TTL | **显式 `cacheRetention: "none"` + 新 session id** |
| 工具定义变化 | 延迟加载则不失效 | provider 原生 `defer_loading` + 占位工具保脚手架 |

**两家都明确处理了同一个问题：一次性调用（摘要、标题生成）不能污染会话的缓存键。** 这是最容易被自建 agent 忽略的一条 —— 一次摘要调用写进缓存，会让后续每一轮的缓存命中率都受影响。

**一个网关层的坑**：Claude Code 依赖显式 `cache_control` 标记。**如果自建网关把它剥掉，整个历史每轮按未缓存计费** —— 成本可能相差 10 倍，但功能上完全正常，不会有任何报错。这类问题只能靠计量发现。

---

## 5. 可迁移的设计模式

按「性价比」排序，本项目可以逐条对照：

| # | 模式 | 一句话 | 落点 |
|---|---|---|---|
| P1 | **预算化上下文** | 每次组装 prompt 前先算预算，超了就按策略降级 | 所有 LLM 调用点 |
| P2 | **阶梯式降级** | 便宜的清理先跑，不够再上 LLM 摘要 | 组装函数 |
| P3 | **工具输出三级管控** | 单条上限 / 单消息总量上限 / 内容级清理 | 工具调用层 |
| P4 | **中间挖空截断** | 长输出保留头尾 | 截断工具函数 |
| P5 | **结构化摘要骨架** | 固定段落的交接单，不是「请总结」 | 摘要 prompt |
| P6 | **压缩后重新注水** | 摘要之外，把关键素材贴回去 | 压缩函数 |
| P7 | **保留最近 N 条** | 不全文摘要，保住最近的细节 | 压缩函数 |
| P8 | **token 计量混合口径** | 服务端真值 + 本地增量估算，不额外发请求 | 计量模块 |
| P9 | **裁剪前先修复结构** | 保证 `tool_use`/`tool_result` 成对 | 裁剪前置 |
| P10 | **把占用可视化** | 让用户/开发者看见还剩多少 | 日志 / 接口 |
| P11 | **增量摘要** | 只对新增消息做有损压缩，已有摘要只做 merge | 压缩函数 |
| P12 | **摘要器不许接着对话** | system prompt 里钉死：只输出摘要 | 摘要 prompt |
| P13 | **结构化素材清单** | 读/改分开记录，只给路径不给内容 | 压缩函数 |
| P14 | **前缀分层稳定** | 稳定内容在前、动态内容在后，让缓存能命中 | prompt 拼装 |
| P15 | **渐进披露** | 给路径和规则，不给内容 | 知识/文档注入 |
| P16 | **一次性调用禁写缓存** | 摘要、标题生成不要污染会话缓存键 | 摘要函数 |
| P17 | **摘要草稿块** | 先写 `<analysis>` 再写 `<summary>`，只把后者装回上下文 | 摘要 prompt |
| P18 | **重试熔断** | 连续失败 N 次就停，别每轮白烧一次调用 | 压缩调度 |

**P1 是前提。** 没有预算概念，后面十七条都无处安放。

**P11（增量摘要）是性价比最高的一条** —— 见 §3.3.4。

**P14 是零成本的**：不改任何策略，只改 prompt 里各段的顺序，就能让供应商的自动前缀缓存开始生效。**任何项目都应该先做这一条。**

---

## 6. 本项目现状与落地建议

### 6.1 现状诊断（源码验证）

先给一个**正面结论**：本项目的**观测层已经做到了三家里的水平**。

`services/observability/provider_usage.py` 里的 `normalize_provider_usage()` 做的正是 pi 在 `packages/ai/src` 里做的事 —— 归一化不同供应商的缓存口径：

```python
if provider.lower() == "deepseek":
    cache_hit_tokens  = raw_usage.get("prompt_cache_hit_tokens")
    cache_miss_tokens = raw_usage.get("prompt_cache_miss_tokens")
else:
    cached_tokens = raw_usage.get("prompt_tokens_details", {}).get("cached_tokens")
    ...
cache_hit_rate = cache_hit_tokens / (cache_hit_tokens + cache_miss_tokens)
```

并把 `prompt_tokens` / `completion_tokens` / `prompt_cache_hit_tokens` / `prompt_cache_hit_rate` / `cache_reported_by_provider` 全部落到 `t_ai_llm_call` 表；没有 provider usage 时还有 `token_source="estimated"` 的兜底路径。

**也就是说 §4.4 的「服务端真值 + 本地估算」这条，本项目已经有了。缺的不是度量，是「用度量做决定」。**

| 位置 | 现状 | 问题 |
|---|---|---|
| `services/observability/provider_usage.py` | ✅ 已归一化 usage + cache 命中 | **只落库，不参与任何决策** |
| `api/interviewer.py:423-470` `conclude_interview` | `qa_summary` 把**全部** Q&A 拼进 context；`resume_content[:1000]` | 唯一一处无界增长点 |
| `api/interviewer.py:148-207` `evaluate_answer` | 只有当前 Q+A + `resume_content[:1000]` | 评分器看不到历史，跨题一致性无从判断 |
| `api/interviewer.py:209-240` `generate_followup_question` | 只有原问题 + 回答 + 追问原因 | 无跨题上下文 |
| `services/mock_candidate.py:16-18` | `_HISTORY_LIMIT=3`、`_RESUME_CHAR_LIMIT=1500`、`_JOB_CHAR_LIMIT=500` | 唯一有「裁剪」的地方，但按**字符**不按 token，且按**条数**定义「最近」 |
| `services/interview_session.py` | `history` 全量存 SQLite，`add_message` 只追加 | 无上限、无清理 |
| `services/agent_runtime/langgraph_wrapper.py` | 只 checkpoint `metadata`，不 checkpoint 对话状态 | 长上下文基建不存在 |

**判断修正：本项目不是「没有度量」，而是「有度量、没策略」。** 计量数据已经在库里，但没有任何一处代码读它来做决定 —— 没有阈值、没有预算、没有降级。

按 §2 的三分法：

- **单次请求超限**：暂未发生（一场面试约 5 个项目题 + 2~4 个技术题 + 追问，量级可控）。
- **会话累积超限**：`conclude_interview` 是 O(n) 增长，随题量/追问数线性上升；一旦引入「多轮面试」「简历深挖 20 题」就会撞上。
- **成本与延迟**：**当前最大的实际损失**。每轮手工拼字符串 → 前缀不稳定 → 供应商侧的自动前缀缓存命中率低。

### 6.2 建议：按 第零步 → P1 → P2 → P3 推进

**第零步（P14 + 先读已有数据）：零成本，先做。**

两件事，都不改任何业务逻辑：

1. **用已经落库的 `prompt_cache_hit_rate` 做一次诊断。** `t_ai_llm_call` 表里已经有每一轮的真实缓存命中率 —— 先把它按 `call_type` 拉出来看看（`evaluate_answer` / `generate_followup_question` / `conclude_interview` 各自的命中率）。**如果命中率接近 0，说明前缀不稳定，这是当前最大的隐性成本**，而且改 prompt 顺序就能解决。

2. **把 prompt 改成「稳定在前、动态在后」（P14）。** 当前每一处调用都是「system prompt 字面量 + `{context}` 全塞在 human 消息里」。调整方向：

```
固定不变的部分（system 指令、评分标准）        ← 必须逐字节稳定
半固定的部分（简历摘要、JD 要点）              ← 按 session 变化，不进前缀也行
动态部分（当前题目、当前回答、最近 N 轮）      ← 放最后
```

**注意 `resume_content[:1000]` 这类截断会让前缀随简历变化** —— 这不是问题（同一场面试内简历不变），但**不要把时间戳、session_id、随机数放进前缀**。

**第一步（P1 + P8）：建立预算，让已有的计量数据参与决策。**

> 计量本身已具备（§6.1），这一步是把数据用起来。

新增 `services/context_budget.py`，提供：

- 模型上下文窗口注册表（配置驱动，按 `model_provider.py` 里已有的模型名索引；未知模型给保守默认值 + WARNING 日志）
- `estimate_tokens(text) -> int`，用 `len(utf8_bytes) / 4` 起步（和 Codex 同口径，`APPROX_BYTES_PER_TOKEN = 4`），后续可换真 tokenizer
- `build_context(sections: list[Section], budget: TokenBudget) -> str`，每个 section 声明优先级与最大占比

**验收**：对现有所有 `invoke_observable` / `stream_observable` 调用点，日志里输出 `estimated_tokens / budget`；跑一场完整面试，产出占用曲线。**这一阶段不改变任何 prompt 内容，只加观测。**

**第二步（P3 + P4 + P9）：工具与素材级清理。**

- `resume_content[:1000]` → 改为「按 token 预算 + 中间挖空（P4）」。简历的关键信息（技能栈、最近项目）在前半段，但结论性的自我评价常在尾部 —— 只留头会丢。
- 统一的 `truncate_middle(text, budget)` 工具函数，落点 `services/`。
- 若后续引入 RAG/题库检索（`question_bank.py` 已有 ChromaDB），**检索结果必须有单条上限 + 单次注入总量上限**（对应 Claude Code 的 50K / 200K 两层）。

**第三步（P2 + P5 + P6 + P7）：压缩与交接。**

- 在 `conclude_interview` 之前引入 **rolling summary**：每完成一个阶段（项目问答 / 技术问答），把该阶段压成结构化摘要；结论时用「阶段摘要 + 最近 K 条完整 Q&A」，而不是全部原文。
- **摘要必须增量更新（P11）**，不要每阶段从零重摘。本项目的面试是**天然分阶段**的（`InterviewStage` 枚举），正好是增量摘要的理想场景：`PROJECT_QNA` 结束时生成第一版摘要，`TECHNICAL_QNA` 结束时**在已有摘要上追加**，而不是把两个阶段的原文合起来重摘一遍。源码参照 pi 的 `UPDATE_SUMMARIZATION_PROMPT`（§3.3.4）。
- 摘要 prompt 用固定骨架（P5），并且**明确禁止摘要器继续对话**（P12）。对本项目的领域，9 段式可以特化为：

```
1. 候选人背景（从简历提炼，事实性）
2. 已考察的技术点（题目 + 结论）
3. 已暴露的弱项（含原话引用）
4. 未验证的存疑点（下一步该追问什么）
5. 评分依据（每项对应的原话/证据）
6. 当前阶段与下一步
```

- 压缩后重新注入（P6）：简历摘要、JD 要点、当前阶段 —— 这些每轮都要在，但可以各占用固定预算，而不是每轮重新拼全文。
- 保留最近 K 条完整 Q&A（P7），不要全压。**注意保留的应该是「所有角色」的最近若干条**（pi 的做法），而不是只留用户消息（Codex 的做法）—— 面试场景里面试官的上一句提问和上一轮评分同样不可再生。

### 6.3 明确不建议做的事

- **不要照抄 Claude Code 的六级流水线**。那是为「一个进程里跑几小时、工具是 shell + 文件读写」的形态设计的。本项目的面试会话短、工具少、历史结构规整（`QuestionAnswer` dataclass），**上两级（预算 + 阶段摘要）就够**。
- **不要为了省 token 牺牲评分质量**。本项目的核心价值是「评估准确性」，压缩是有损的；宁可多花 token 保留原文 Q&A，也不要让评分器读一份二手的摘要。
- **不要把 token 计数做成额外 API 调用**。用 Codex 的混合口径（服务端 usage + 本地估算）。本项目已经有这条了（`services/observability/provider_usage.py`）。
- **不要为了抄而引入 microcompaction**。pi 明确不做（§3.3.13），它选择「不逐条清理，到点整段压缩」。本项目的工具调用量远小于 coding agent，**没有大量老工具结果需要清**。照抄只会增加一层无处生效的复杂度。
- **不要在 prompt 前缀里塞变化的内容**。当前每轮手工拼字符串，**先保证前缀稳定**（system prompt + 简历摘要固定在前，动态问答在后），供应商的自动前缀缓存才能生效 —— 这是零成本的收益，也是 §6.2 的第零步。
- **不要在压缩策略上追求「无损」**。三家都接受有损，并且都把这一点显式告知用户。本项目也应该在结论页/日志里体现「评分基于摘要还是原文」。

### 6.4 测试与证据登记（按 CLAUDE.md 的测试资产管理要求）

落地时需要在 `tests/docs/test-cases.md` 登记的场景：

| 场景 | 断言 |
|---|---|
| 预算估算 | 给定输入文本，`estimate_tokens` 落在预期区间；空输入返回 0 |
| 中间挖空截断 | 头尾都保留；标记文本正确；短于预算时不改动 |
| 阶段摘要 | 摘要后总 token 数低于阈值；最近 K 条 Q&A 逐字保留 |
| 结论 prompt | 20 题 + 追问的极端输入下，组装结果不超预算 |
| 回归 | 相同输入两次组装 → 前缀字节完全一致（保证缓存命中） |
| 缓存命中回归 | 一场完整面试跑完，`prompt_cache_hit_rate` 不低于基线（断言 `t_ai_llm_call` 表） |

配套命令封装到 `tests/scripts/` 下。

---

## 7. 反模式清单

从三家的实现里能反推出这些坑：

1. **按字符截断当 token 预算**。本项目 `_RESUME_CHAR_LIMIT=1500` 就是。中英文 token/char 比差一个量级，字符数在跨语言时完全不可比。
2. **只留头部截断**。编译错误、测试结果的关键行在尾部。
3. **等撞到 `prompt_too_long` 才处理**。没有软阈值就没有降级空间。
4. **压缩请求自身超限**。Codex 专门写了 `trim_function_call_history_to_fit_context_window()` 来处理。
5. **裁剪后不管结构完整性**。拆散 `tool_use`/`tool_result` 会让 API 直接报错。
6. **摘要 prompt 写成「请总结一下」**。信息取舍交给模型随机决定，复现性为零。
7. **压完不注水**。摘要不带代码/文件，压完直接失忆。
8. **在缓存必然命中的时刻做清理**。主动制造 cache miss，白付一次全量重写。
9. **压缩不持久化，resume 时重放全量历史**。压缩变成一次性开销，每次恢复都要重付。
10. **把「压缩后变笨」瞒着用户**。Codex 会直接弹警告。
11. **反复全量重摘要**。摘要是有损函数，对摘要再摘要会单调退化。pi 用增量更新（`PRESERVE` 已有信息 + 只 merge 新增）正面解决了这个问题 —— 这是本报告里最容易抄、收益最大的一条。
12. **让摘要器接着对话**。摘要调用最常见的失败模式。pi 的 system prompt 用两句大写禁令钉死：`Do NOT continue the conversation... ONLY output the structured summary.`
13. **把「最近」定义成条数**。`[-3:]` 这类写法在不同长度的消息上预算完全不同。三家都用 **token 预算**定义「最近」（`keepRecentTokens = 20_000`），不是条数。
14. **摘要 prompt 里不写「空段也要留占位符」**。省略空段之后，下游无法区分「没有这个信息」和「摘要没提」。pi 强制 `(none)`。
15. **让一次性调用污染会话缓存键**。摘要、标题生成这类调用如果不显式禁用缓存写入，会拖累后续每一轮的命中率。两家都专门处理了这件事（P16）。
16. **自建网关剥掉 `cache_control`**。功能完全正常，但每轮按未缓存计费 —— **只能靠计量发现，不会有任何报错**。
17. **该丢弃的路径用压缩而不是回退**。想彻底放弃某条路径，用「截断回已缓存前缀」（Claude Code 的 `/rewind`）而不是生成一段新历史 —— 后者的缓存必然重建。
18. **prompt 里动态内容排在前面**。哪怕只把时间戳放在最前面，也会让整个前缀缓存失效。
19. **重试没有熔断**。上下文已经不可恢复地超限时，自动重试只会每轮白烧一次调用。

---

## 8. 证据索引

### Codex

| 内容 | 位置 |
|---|---|
| 阈值判定 | `codex-rs/core/src/session/context_window.rs::context_window_token_status()` |
| 软阈值公式 | `codex-rs/protocol/src/openai_models.rs:521` |
| 硬上限默认值 95 | `codex-rs/protocol/src/openai_models.rs`（`default_effective_context_window_percent`） |
| 配置键 | `codex-rs/core/src/config/mod.rs:628-635, 887` |
| 用户消息预算 | `codex-rs/core/src/compact.rs:60` |
| 压缩主流程 | `codex-rs/core/src/compact.rs::run_compact_task_inner_impl()` |
| 摘要 prompt | `codex-rs/prompts/templates/compact/prompt.md`、`summary_prefix.md` |
| 工具输出截断 | `codex-rs/utils/output-truncation/src/lib.rs`、`codex-rs/utils/string/src/truncate.rs:4` |
| 孤儿清理 | `codex-rs/core/src/context_manager/normalize.rs` |
| 压缩请求自愈 | `codex-rs/core/src/compact_remote_history.rs::trim_function_call_history_to_fit_context_window()` |
| resume 重建 | `codex-rs/core/src/session/rollout_reconstruction.rs::reconstruct_history_from_rollout()` |
| 压缩形状快照 | `codex-rs/core/tests/suite/snapshots/all__suite__compact__manual_compact_with_history_shapes.snap` |

### pi

> 仓库 `github.com/earendil-works/pi` @ HEAD `e4c75a7`。**正式 CLI 路径**为 `packages/coding-agent/src/core/compaction/`；`packages/agent/src/harness/compaction/` 是实验性平行实现，勿引用。

| 内容 | 位置 |
|---|---|
| 压缩设置与触发 | `compaction/compaction.ts:143-150, 250-252` |
| 切点计算（按 token 预算） | 同上 `:418-444` `findCutPoint()` / `:793` 调用点 |
| 摘要 prompt（6 段骨架） | 同上 `:482` `SUMMARIZATION_PROMPT` |
| 增量摘要 prompt | 同上 `:552` `UPDATE_SUMMARIZATION_PROMPT` / `:693` 分支与 0.8×reserve 输出预算 |
| turn 前缀摘要 | 同上 `:850` `TURN_PREFIX_SUMMARIZATION_PROMPT` |
| token 计量 | 同上 `calculateContextTokens()` / `getLastAssistantUsage()` / `:281-289` `estimateTokens()` |
| 文件操作抽取与格式化 | `compaction/utils.ts` `extractFileOpsFromMessage()` / `computeFileLists()` / `formatFileOperations()` |
| 摘要输入侧截断 | 同上 `:89` `TOOL_RESULT_MAX_CHARS = 2000` |
| 活上下文工具截断 | `packages/coding-agent/src/core/tools/truncate.ts:11-13` `DEFAULT_MAX_LINES` / `DEFAULT_MAX_BYTES` / `GREP_MAX_LINE_LENGTH`；`:78` `truncateHead` / `:168` `truncateTail` |
| 分支摘要 | `compaction/branch-summarization.ts` |
| resume 不重放 | `core/session-manager.ts:429` `buildContextEntries()` / `firstKeptEntryId` |
| provider 缓存抽象 | `packages/ai/src/types.ts` `CacheRetention`；`openai-prompt-cache.ts` `clampOpenAIPromptCacheKey()` |
| 渐进披露 | `system-prompt.ts:153-160`（`<docs>` 路由）、`skills.ts:355` `formatSkillsForPrompt()` |
| 延迟工具加载 | `anthropic-messages.ts` `defer_loading` / `tool_addition` / `__pi_deferred_placeholder__` |

### Claude Code（补充：官方文档与 CLI bundle）

| 内容 | 位置 |
|---|---|
| 每轮流水线 | `src/query.ts:366-468` |
| 阈值与 buffer 常量 | `src/services/compact/autoCompact.ts:30-100` |
| 工具尺寸常量 | `src/constants/toolLimits.ts` |
| 内容级清理 | `src/services/compact/microCompact.ts` |
| 时间触发清理 | `src/services/compact/timeBasedMCConfig.ts` |
| 注水常量 | `src/services/compact/compact.ts:122-130` |
| 摘要 prompt 骨架 | `src/services/compact/prompt.ts` |
| 保留段锚点 | `src/services/compact/compact.ts::annotateBoundaryWithPreservedSegment()` |
| session memory 阈值 | `src/services/compact/sessionMemoryCompact.ts` |
| 压缩后清理 | `src/services/compact/postCompactCleanup.ts` |
| 窗口解析与默认值 | `src/utils/context.ts:9, 15` `MODEL_CONTEXT_WINDOW_DEFAULT` / `MAX_OUTPUT_TOKENS_DEFAULT` |
| 摘要草稿块丢弃 | `src/services/compact/prompt.ts` `formatCompactSummary()` |
| 状态栏提示字符串 | `src/components/TokenWarning.tsx` |
| token 计量 | `src/utils/tokens.ts` `tokenCountWithEstimation()` / `src/services/tokenEstimation.ts` `bytesPerTokenForFileType()` |

**官方文档**：

| 主题 | 链接 |
|---|---|
| Prompt caching（分层、TTL、失效清单） | <https://code.claude.com/docs/en/prompt-caching> |
| 显式 cache 断点 | <https://platform.claude.com/docs/en/build-with-claude/prompt-caching> |
| 压缩与上下文管理（用户视角） | <https://code.claude.com/docs/en/how-claude-code-works#when-context-fills-up> |

> Claude Code 的路径基于本机 v2.1.88 还原快照（源：官方 npm 包 `@anthropic-ai/claude-code@2.1.88` 的 `cli.js.map` → `sourcesContent`），未加 `src/` 前缀的相对根为该快照的 `src/` 目录。**数值常量请按版本阅读**（见 §1 的版本核对表）。

---

## 附：一句话版本

**上下文管理的本质不是「怎么塞下更多」，而是「决定丢掉什么、以及丢完之后怎么让模型继续能干活」。**

三家做的都是同一件事：**给上下文定预算 → 按性价比从低到高降级 → 该丢的丢掉 → 把不可再生的（用户原话、环境信息、最近细节）重新贴回来。**
