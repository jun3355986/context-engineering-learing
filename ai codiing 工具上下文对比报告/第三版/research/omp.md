# oh-my-pi（omp）· 上下文管理事实卡片

- **仓库**：https://github.com/can1357/oh-my-pi
- **提交号**：`f979f4639777858de28e6ecb99d577443abe0b7b`
- **核实日期**：2026-10-18
- **分析范围**：`packages/coding-agent/src/session`、`packages/agent/src/compaction`、`packages/snapcompact`、`packages/tui/src/tools/streaming-output.ts`、`packages/coding-agent/src/{system-prompt.ts,discovery,memory-backend,memories,task,extensibility}`。不分析 Rust `crates/` 的底层加速实现，不分析模型服务端。
- **Permalink 基址**：`https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/`
- **性质**：omp 是 pi 的 fork（`README.md#L22`）。**同源代码来源 ≠ 默认行为相同**：omp 保留会话树与压缩骨架，但默认配置、压缩方法集、记忆、子代理均已实质扩写。第 17 节逐项对照。

---

## 1. 请求组装

**做法**
omp 每次请求都从**会话树叶子向根回溯**，得到当前分支路径，再按「最新 compaction / `/clear` 边界」重建模型上下文。有压缩时顺序固定为：**摘要消息在最前 → `firstKeptEntryId` 起的保留段 → 压缩之后的条目**；摘要消息会携带 `providerPayload`（OpenAI remote / Anthropic native 回放载荷）、snapcompact 图像块、`historyRewriteAt`。重建完成后统一做两道清理：**剥离悬挂的 `tool_use`**（没有配对 `tool_result` 的调用，连同其受保护推理签名一起中和），**丢弃 `stopReason` 为 `aborted` / `error` 的 assistant 轮**及其配对合成结果。系统提示词由模板渲染，静态块之后统一追加一个 `<project-context>` 块（上下文文件、workspace tree/roots、active repo、会话追加文本），这样不同目录的会话共享静态前缀，Anthropic 的缓存断点正好落在这个块之前。请求时再在**首个用户轮**前注入日期/cwd 提醒，而不是改系统提示词。

**关键参数与默认值**
- 路径遍历有环保护：遇到重复 `id` 即停（`session-context.ts:281-291`）
- 上下文笔记（实验性）插在 Anthropic 原生压缩块之后（`session-context.ts:646-671`）
- `<project-context>` 永远在静态块之后（`system-prompt.ts:1026-1036`）

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-context.ts#L238-L644
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-context.ts#L673-L734
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-context.ts#L744-L769
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/system-prompt.ts#L1021-L1046

**可信度**：【已核实】

**源码解读候选**：`buildSessionContext()` —— 一次「叶子到根」的投影如何同时处理压缩、`/clear`、原生回放与悬挂工具调用

---

## 2. 规则文件的发现与合并

**做法**
omp 的规则发现是**多生态兼容**：`discovery/` 下注册了 6 个上下文文件 provider——`AGENTS.md`（含向上查找）、`CLAUDE.md`、custom context files（`contextFiles.extra`）、Gemini、GitHub `copilot-instructions.md`、opencode。每个 provider 把自己的结果交给 capability 层合并。合并时按 `depth` 排序（离 cwd 越远越先、越近越后），并做**内容包含去重**：如果某个文件的规范化段落完全被另一个「更靠近 cwd、更权威」的文件包含，就丢掉前者；仅改写或交错的不算包含，保留。workspace 树会收集 `AGENTS.md` 文件路径，去重排序后截到 200 个。最终统一渲染进 `<project-context>`。

除了「上下文文件」，omp 还有一条独立的 **rule capability**（Cursor `.mdc`、Windsurf、Cline、Claude 插件、omp 插件、内置规则等）。规则进入会话前统一过 `bucketRules()`，按固定优先级分桶：`disabledRules` 丢弃 → `builtinRules=false` 丢弃内置 → `agents` 作用域不匹配丢弃 → 带 `condition`/`astCondition`/`question` 的进入 **TTSR**（按输出流/工具流条件匹配，命中的规则名记入 `ttsr_injection` 条目并去重）→ `alwaysApply` 直接全文注入提示词 → 其余进 **rulebook**（只暴露描述，正文按需 `rule://` 读取）。因此「规则注入」在 omp 里有三种形态：静态 `<project-context>`、条件触发 TTSR、按需 rulebook。omp 没有「全局 → 用户 → 项目 → 子目录」四层命名，而是「多 provider + depth 排序 + 包含去重 + 分桶」。

**关键参数与默认值**
- 上下文文件 provider 数：6（`discovery/` 下 `registerProvider(contextFileCapability.id, …)`）
- rule provider：至少 7 个（builtin、builtin-defaults、agents、cursor、windsurf、claude-plugins、omp-plugins）
- 规则分桶顺序：disabled → builtin toggle → agents 作用域 → TTSR → alwaysApply → rulebook（`rule-buckets.ts:8-15`）
- `AGENTS_MD_LIMIT = 200`（`workspace-tree.ts:16`）
- 额外文件名：`contextFiles.extra`，值为文件名列表而非路径（`context-settings.ts:58`）
- 未在源码中找到单个规则文件的字节上限；截断只发生在 workspace tree 渲染层

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/discovery/agents-md.ts#L15-L28
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/discovery/claude-md.ts#L24-L24
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/discovery/custom-context-files.ts#L113-L113
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/discovery/gemini.ts#L310-L310
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/discovery/github.ts#L302-L302
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/discovery/opencode.ts#L499-L499
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/system-prompt.ts#L323-L342
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/system-prompt.ts#L349-L357
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/capability/rule-buckets.ts#L1-L85
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/capability/rule.ts#L20-L60
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/workspace-tree.ts#L16-L16

**可信度**：【已核实】；「单文件无字节上限」为【待核实】（未找到截断逻辑）

---

## 3. 按需加载（渐进披露）

**做法**
技能在提示词里只放名称、描述和位置，正文通过 `skill://<name>` 内部 URL 按需读取（`read` / `grep` 都支持），`hide: true` 的技能不出现在提示词但 `skill://` 仍可访问。**rulebook** 里的规则同理：提示词只给 `description`，正文通过 `rule://` 读取；只有 `alwaysApply` 规则才全文注入。MCP 工具**全部保持启用**，但「展示位置」由 `loadMode` 决定：一部分作为顶层工具，一部分收进 `xd://` 目录（系统提示词只给目录名，模型需要时再展开）。这相当于把「工具定义」也做了渐进披露。扩展/自定义工具同样走 `discoverable` 加载模式。

**关键参数与默认值**
- `skill://` 支持三种形态：`skill://<name>`、`skill://<name>/<path>`、`skill://<namespace>/<name>[/<path>]`（`internal-urls/skill-protocol.ts:7-10`）
- MCP 展示分区：顶层 vs `xd://`，由 `loadMode` 决定（`session-tools.ts:864-869`）
- rulebook：只给 `description`，正文用 `rule://<name>` 读；`alwaysApply` 才全文注入（`rule-buckets.ts:8-15`）
- 未在源码中找到技能描述长度上限（与 pi 的 1024 不同）

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/internal-urls/skill-protocol.ts#L1-L20
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/system-prompt.ts#L918-L938
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-tools.ts#L862-L869
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/internal-urls/rule-protocol.ts#L1-L15
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/capability/rule-buckets.ts#L8-L15

**可信度**：【已核实】

---

## 4. 动态注入

**做法**
omp 有三类动态注入，都刻意避开「改系统提示词前缀」。第一类是**日期/cwd 提醒**：每次 provider 请求时渲染一次，插到该请求的**首个用户轮**前面；它按 `(date, cwd)` 确定性生成，同一会话/同一天字节稳定，午夜或换目录才变——这样系统提示词与工具数组的前缀缓存不会被目录切换打断。第二类是 **TTSR 注入**：`ttsr_injection` 条目记录注入过的规则名，重建上下文时汇总成 `injectedTtsrRules`，避免重复注入。第三类是**上下文笔记**（实验性）：`context_notes` 写入的笔记以 journal 条目形式挂在分支上，只有最新可见修订进入模型上下文；`/clear` 会清空可见笔记，单次替换上限 16,384 UTF-8 字节。todo 状态由 `syncTodoPhasesFromBranch()` 从分支同步，不属于提示词注入。

**关键参数与默认值**
- 日期/cwd 提醒：每请求一次，按 `(date, cwd)` 去重（`date-cwd-reminder.ts:1-14`）
- 笔记单次写入上限：16,384 UTF-8 字节（`docs/compaction.md:170`）
- `compaction.experimentalContextManagement` 默认 `false`（`context-settings.ts:117-127`）

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/date-cwd-reminder.ts#L1-L40
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-context.ts#L337-L348
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-context.ts#L646-L671
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/docs/compaction.md#L152-L180

**可信度**：【已核实】（笔记上限来自文档）

---

## 5. Token 计量与可视化

**做法**
`calculateContextTokens()` 优先使用 provider 显式上报的 `usage.contextTokens`；否则用 `totalTokens` 或 `input+output+cacheRead+cacheWrite`，并**减去服务端编排 token**（可计费但不会回放进对话前缀，算进去会虚高触发）。触发前再用 `compactionContextTokens(providerTokens, storedEstimate)` 取两者较大值：因为 `before_provider_request` 可能把请求压缩/混淆，provider 报的 prompt token 会偏小，若只信它，真实历史会无界增长。阈值解析优先级：`thresholdTokens > 0` → 固定值；否则 `thresholdPercent > 0` → `floor(window × clamp(pct,1,99)/100)`；否则（默认 `-1/-1`）→ `window − 有效预留`。有效预留是 `max(floor(window×0.15), reserveTokens ?? 16384)`。状态栏用 `computeCompactionBoundaries()` 画出阈值/预留/推测压缩位置。

**关键参数与默认值**
- `DEFAULT_RESERVE_TOKENS = 16384`，`MAX_SUMMARY_TOKENS = 16384`（`compaction.ts:199-211`）
- `thresholdPercent = -1`、`thresholdTokens = -1`、`keepRecentTokens = 20000`、`midTurnEnabled = true`（`compaction.ts:216-227`）
- 有效预留下限：窗口的 15%（`compaction.ts:320-322`）
- 窗口缩放：`compaction.baseWindowTokens` 只影响阈值估算，不改变真实 `contextWindow`；`compaction.modelThresholds` 可按模型覆盖阈值（`compaction.ts:172-179`，`context-settings.ts:217-233`）
- 200K 窗口默认触发点 ≈ `200000 − 30000 = 170000`（15% 大于 16384）

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/compaction.ts#L172-L179
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/compaction.ts#L199-L227
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/compaction.ts#L250-L278
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/compaction.ts#L316-L354
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/compaction.ts#L384-L414
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/context-usage-runtime.ts#L21-L47

**可信度**：【已核实】

---

## 6. 单次工具输出控制

**做法**
两条独立上限：**3000 行 / 50 KiB（51,200 字节）**，先到者胜；另有单行 512 字节上限。`read/glob/grep` 等保头（`truncateHead`），`bash` 保尾（`truncateTail`）。超限时完整输出写入 **artifact** 文件，上下文里只留预览与 `Full output: artifact://<id>`；artifact 自身有 16 MiB 上限（头 3 MiB + 滚动尾），触顶时写 `[ARTIFACT TRUNCATED: …]`。artifact 的 id 随 fork 一起复制，保留的 `artifact://` 引用仍然可解析。

**关键参数与默认值**
- `DEFAULT_MAX_LINES = 3000`、`DEFAULT_MAX_BYTES = 50 * 1024`、`DEFAULT_MAX_COLUMN = 512`
- `ARTIFACT_DEFAULT_MAX_BYTES = 16 MiB`、`ARTIFACT_DEFAULT_HEAD_BYTES = 3 MiB`
- 落盘提示格式：`Full output: artifact://<id>`（`agent-session.ts:3138-3144`）

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/tui/src/tools/streaming-output.ts#L10-L30
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/agent-session.ts#L3138-L3144
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-manager.ts#L3873-L3880

**可信度**：【已核实】

---

## 7. 历史裁剪（不调用模型）

**做法**
omp 有**两层**不调模型的裁剪，发生在压缩之前。第一层是 `pruneToolOutputs()`（阈值裁剪）：保护最近 **40,000** token 的工具输出，只有总节省 ≥ **20,000** token 才动手；小于 50 token 的结果不裁（占位符本身约 8 token，裁了反而变大）；永远保护 `skill` 结果、`skill://` 读取结果和当前 plan 参考文件。第二层是 `pruneSupersededToolResults()`（逐轮陈旧裁剪）：同一文件被更新一次 `read` 覆盖后，旧结果换成 `[Superseded by a newer read of this file]`；工具主动标记 `useless` 的结果（零命中搜索等）换成 `[Uneventful result elided]`。两层都有**缓存守卫**：候选结果之后的 suffix 仍在热缓存前缀里时不改（`cacheWarmSuffixTokens`），或按 provider 的 prompt-cache lookback 位置限制；模型有 prefix-bound thinking 时守卫更严（阈值设为 0）。裁剪是原地改写并 `rewriteEntries()` 持久化，失败会 `undo()` 恢复内存，避免内存与磁盘分叉。

**关键参数与默认值**
- `protectTokens: 40_000`、`minimumSavings: 20_000`、`MIN_PRUNE_TOKENS = 50`、`pruneUseless: true`（`pruning.ts:77-83`，`docs/compaction.md:231-242`）
- 占位符：`[Output truncated - N tokens]`、`[Superseded by a newer read of this file]`、`[Uneventful result elided]`
- 逐轮裁剪开关：`compaction.supersedeReads` / `compaction.dropUseless`

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/pruning.ts#L77-L83
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/pruning.ts#L290-L294 ——（`MIN_PRUNE_TOKENS = 50`）
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/pruning.ts#L452-L452
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/pruning.ts#L537-L537
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-maintenance.ts#L710-L790
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/docs/compaction.md#L227-L252

**可信度**：【已核实】

---

## 8. 压缩（调用模型做摘要）

**做法**
omp 的压缩是**方法链**，不是单一算法。默认顺序 `["remote","snapcompact","handoff","shake","soft"]`：`remote` 用 provider 原生服务端压缩（OpenAI Responses compact / Anthropic compaction beta），不可用或失败就逐级回退；`snapcompact` 把被丢弃历史渲染成 PNG 帧（无 LLM 调用，需要视觉模型）；`handoff` 生成交接文档，把它当作压缩摘要继续；`shake` 做机械省略；`soft` 才是普通 LLM 摘要。触发有六条：手动 `/compact [指令]`、溢出恢复、输出未完成（`length`）恢复、轮后阈值、轮中阈值（`midTurnEnabled !== false`，子代理强制开启）、空闲维护（`idleEnabled` 默认 false）。切点从最新往回**按整组累加**（assistant 与其全部 toolResult 的 token 一起计入，只在合法切点处比较预算），超过 `keepRecentTokens` 即停，取最接近的合法切点；合法切点包括 user/assistant/bashExecution/hookMessage/branchSummary/compactionSummary/custom_message/branch_summary，**绝不切在 toolResult**。切点不在轮首则 `isSplitTurn=true`，生成「历史摘要 + 轮前缀摘要」再合并为 `<history>\n\n---\n\n**Turn Context (split turn):**\n\n<prefix>`。多次压缩时旧摘要走 `<previous-summary>` 增量更新；文件清单以 `<files>` 追加，按目录树折叠，最多 20 个文件，其余写 `[…N files elided…]`。**服务端压缩**是默认第一选择（`remoteEnabled: true`），并支持 provider 原生历史回放（`providerReplayThroughEntryId`）。**手动指令**作为 `customInstructions` 追加；另有 `internalGuidance` 只给原生摘要，不给扩展钩子。

**关键参数与默认值**
- 方法顺序：`["remote","snapcompact","handoff","shake","soft"]`（`compaction-methods.ts:44-50`）
- `compaction.enabled = true`、`methodOrder` 默认上述数组、`autoContinue = true`、`midTurnEnabled = true`（`context-settings.ts:106-155`；`compaction.ts:216-227`）
- 摘要上限：`min(floor(0.8 × reserve), 16384)`；split 轮前缀：`min(floor(0.5 × reserve), 16384)`（`compaction.ts:889,2267`）
- `keepRecentTokens = 20000`，并按「provider prompt tokens / 本地估算」的比值缩放（`compaction.ts:1437-1447`）
- 文件清单上限：20（`utils.ts:163-188`）
- 溢出时跳过 `handoff`；`snapcompact` 在字节/媒体型 413 时被排除（`session-maintenance.ts:186-200`）

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/compaction-methods.ts#L24-L50
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-maintenance.ts#L4612-L4747
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/compaction.ts#L216-L227
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/compaction.ts#L350-L354
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/compaction.ts#L427-L462
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/compaction.ts#L521-L574
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/compaction.ts#L1437-L1464
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/compaction.ts#L2213-L2220
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/agent/src/compaction/utils.ts#L163-L188
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/docs/compaction.md#L66-L145
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/docs/compaction.md#L254-L316

**可信度**：【已核实】

**源码解读候选**：
1. `runAutoCompaction()` 的方法链选择与回退（含 shake 的「不够就继续下一个」）
2. `findCutPoint()` 的「按整组累加」与 `keepRecentTokens` 按实测比值缩放

---

## 9. 多模态上下文

**做法**
omp 在多模态上有三条独立机制。第一，**snapcompact**：把被压缩的历史序列化成文本、归一化后光栅化成 PNG 帧，交给视觉模型「读图」；帧形状按模型 id 选择（Claude `11on16-bw`、Gemini `8on22-bw@2048`、OpenAI `8on22-bw`），帧存在 `CompactionEntry.preserveData.snapcompact`，每次重建上下文都重新挂回摘要消息。第二，**inline snapcompact**：可把系统提示词或工具结果直接渲染成图片，默认关闭（`snapcompact.systemPrompt = "none"`、`snapcompact.toolResults = false`）。第三，**图片预算裁剪**：请求前按 provider 的图片数量预算裁剪，超限的图片替换成 `[image omitted: provider image limit]`；另有 `dropImages()` 可把整条分支的图片剥掉并持久化（破坏性）。assistant 生成的图片不计入输入图片预算。

**关键参数与默认值**
- `snapcompact.shape = "auto"`；帧计价回退常量 `FRAME_TOKEN_ESTIMATE = 5024`（`snapcompact.ts:522`）
- 默认帧上限 80 帧（`docs/compaction.md:217`）
- `snapcompact.systemPrompt = "none"`、`snapcompact.toolResults = false`（`context-settings.ts:414-443`）
- 图片超限占位：`[image omitted: provider image limit]`（`provider-image-budget.ts:22`）

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/snapcompact/src/snapcompact.ts#L2349-L2349
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/snapcompact/src/snapcompact.ts#L447-L483
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-context.ts#L524-L545
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/provider-image-budget.ts#L18-L90
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-maintenance.ts#L792-L815
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/docs/compaction.md#L206-L219

**可信度**：【已核实】（帧上限来自文档）

---

## 10. 子代理隔离

**做法**
omp 内置 `task` 工具：每个任务项按 `agent` 定义启动一个**独立子会话**，子会话有自己的 `systemPrompt` 与 `task`，默认**不继承父对话历史**。支持批量（`task.batch` 默认 true）、隔离（`task.isolation.enabled` 默认 false，开启后走 worktree/patch 合并）、递归深度上限、并发上限。**结构化返回**由 `outputSchema` 控制：每个任务项可带 `outputSchema` 与 `schemaMode`（`permissive` / `strict`）；子代理输出先按 schema 校验，`permissive` 允许从自由文本里解析兜底，`strict` 要求严格符合；`task.structured` 默认 false，即默认不强制结构化。子代理输出有硬上限 **500,000 字节 / 5,000 行**，超出截断；最终回传还会再做一次摘要（`result-summary.ts` 的 5000 字符阈值）。

**关键参数与默认值**
- `MAX_OUTPUT_BYTES = 500_000`、`MAX_OUTPUT_LINES = 5000`（`task/types.ts:28-32`）
- `task.isolation.enabled = false`、`task.batch = true`、`task.structured = false`、`task.maxRecursionDepth = 2`、`task.maxConcurrency = 32`（`task/settings.ts`）
- 输出 schema 模式默认 `permissive`（`executor.ts:708-710`）
- 子会话压缩：`createSubagentSettings` 强制 `compaction.midTurnEnabled` 开启（`docs/compaction.md:76`）

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/task/types.ts#L28-L68
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/task/settings.ts#L27-L30
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/task/settings.ts#L242-L258
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/task/settings.ts#L331-L334
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/task/executor.ts#L640-L660
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/task/executor.ts#L708-L760
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/task/result-summary.ts#L16-L60

**可信度**：【已核实】

**源码解读候选**：`outputSchema` 的 permissive/strict 两档校验与「自由文本兜底解析」

---

## 11. 会话时间线

**做法**
会话是**只追加的 JSONL 条目日志**，靠 `id`/`parentId` 成树。压缩只追加 `CompactionEntry`（含 `summary`、`shortSummary`、`firstKeptEntryId`、`tokensBefore`、`method`、`preserveData`、`providerReplayThroughEntryId`），不删除原始条目；重建时按「摘要 + 保留段 + 压缩后」投影。`/clear` 写入 `reset_boundary`：晚于最新压缩的边界会让压缩摘要与保留段一起失效，只发射 reset 之后的条目；早于压缩的边界则被压缩取代。`/tree` 是**同文件叶子移动**，离开的分支可生成 `BranchSummaryEntry`，用 `branchWithSummary()` 挂在导航目标上；`createBranchedSession()` 才另写新文件（fork/clone）。**checkpoint / rewind** 是模型可调用的两个工具：`checkpoint(goal)` 记录当前条目 id 与消息计数；后续 `rewind(report)` 把「探索过程中得到的研究报告」作为分支摘要，把叶子切回 checkpoint 位置，再追加一条 `rewind-report` 自定义消息；完成后不能对同一 checkpoint 再次 rewind。它不是上下文压缩，而是「用报告换掉整段探索历史」。

**关键参数与默认值**
- `branchSummary.enabled = false`、`branchSummary.reserveTokens = 16384`（`context-settings.ts:610-626`）
- 分支摘要输出上限 2,048 token（`docs/compaction.md:447`）
- checkpoint 记录：`checkpointMessageCount`、`checkpointEntryId`、`startedAt`（`tools/checkpoint.ts:11-18`）

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-context.ts#L350-L354
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-context.ts#L463-L482
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-manager.ts#L3530-L3560
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-manager.ts#L3854-L3871
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-manager.ts#L3880-L3896
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/tools/checkpoint.ts#L11-L131
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/agent-session.ts#L10529-L10624
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/docs/compaction.md#L392-L451

**可信度**：【已核实】

**源码解读候选**：`#applyRewind()` —— 用「分支摘要 + 自定义报告」把探索历史折叠成一条可续跑的状态

---

## 12. 跨会话记忆

**做法**
omp 有独立记忆子系统，**默认关闭**。`memory.backend` 五选一：`off`（默认）、`local`（从持久会话生成项目级摘要与经验，写入 `memory_summary.md`，启动时以 **Memory Guidance** 块注入系统提示词）、`hindsight`（远程向量记忆）、`mnemopi`（本地 SQLite，支持 `recall`/`retain`/`reflect`）、`sharpshooter`（项目决策文件，后台合并）。`local` 的摘要与经验共享 `memories.summaryInjectionTokenLimit`，默认 **5000 token**；经验部分按摘要占用后的剩余预算截断。记忆按项目隔离，可用 `memory://root`、`memory://root/MEMORY.md`、`memory://root/learned.md`、`memory://<id>` 读回；`/memory view|stats|diagnose|queue|sync|clear|reset` 管理。写入时机是会话结束后的后台 consolidation，`learn` 工具可手动捕获经验；注入内容被明确标注为「启发式上下文」，与仓库现状冲突时以仓库为准。

**关键参数与默认值**
- `memory.backend = "off"`（`memory-backend/settings.ts:14-22`）
- `memories.summaryInjectionTokenLimit = 5000`（`memories/settings.ts:89-93`）
- `memories.fallbackTokenLimit = 16000`、`memories.phase1InputTokenLimit = 4000`（`memories/settings.ts:77-87`）
- 注入块名：**Memory Guidance**

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/memory-backend/settings.ts#L14-L45
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/memories/settings.ts#L77-L93
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/memories/index.ts#L220-L240
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/docs/memory.md#L1-L60

**可信度**：【已核实】

---

## 13. 缓存友好设计

**做法**
omp 的缓存设计比 pi 更「工程化」，核心是**把易变内容移出系统提示词前缀**。静态提示词块在前，`<project-context>` 永远作为最后一个块，Anthropic 的缓存断点落在这个块之前；日期/cwd 提醒从系统提示词尾部移到「每次请求的首个用户轮」，因此系统提示词与工具数组在会话内字节稳定，只有跨天/换目录才变。历史裁剪有缓存守卫：候选结果之后的 suffix 仍在热前缀里时不改；有 prompt-cache lookback 的模型（Claude 20 个位置）还会按位置限制，给下一次请求留 6 个位置余量。`CacheWarmer` 从 pi 移植：TTL 的 90% 处刷新、节省下限 $0.05、streaming/idle 两阶段、60/30 分钟上限。`handoff` 生成复用实时 prompt-cache key 以对齐前缀。压缩本身仍会造成一次前缀失效，omp 用「方法链 + 推测压缩」把这次失效的等待成本前移。

**关键参数与默认值**
- 日期/cwd 提醒插入位置：首个用户轮（`date-cwd-reminder.ts:1-14`）
- 缓存断点：`<project-context>` 之前（`system-prompt.ts:1026-1036`）
- lookback 余量：lookback − 6（`docs/compaction.md:248`）
- 预热：TTL × 0.9、$0.05、60/30 分钟（`cache-warmer.ts:1-20`）

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/date-cwd-reminder.ts#L1-L14
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/system-prompt.ts#L1026-L1036
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/cache-warmer.ts#L1-L35
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-maintenance.ts#L710-L790
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/docs/compaction.md#L244-L252

**可信度**：【已核实】

---

## 14. 失败恢复

**做法**
omp 的恢复顺序是「**先升级模型，再压缩**」：溢出或输出未完成时，若配置了更大窗口的同族模型，先切模型重试，不压缩。溢出路径把失败的 assistant 从运行时上下文移除，然后按 `methodOrder` 走 `reason: "overflow"` 的压缩链（`handoff` 被跳过，因为它的请求会复用溢出的输入），成功后 `agent.continue()` 重试。输出未完成（`length`）有独立的连续恢复计数，**上限 3 次**；达到上限就阻止自动续跑并报错。压缩后有**进度守卫**：重写后的上下文必须降到阈值的约 **80%** 以下才允许续跑；否则尝试本地救援（重渲 snapcompact 更小帧、把重块 elide 到 artifact、丢图片），仍不行就告警并阻止自动续跑，避免在同一段超大上下文上反复空转。HTTP 413/载荷拒绝**不**自动当 token 溢出：本地估算有 ≥10% 余量时只告警、不续跑；确证 token 溢出才压缩，且排除媒体型方法。压缩失败/取消不提交；手动压缩中断会先 abort，提交后按需恢复被打断的回合。

**关键参数与默认值**
- 恢复带宽：`COMPACTION_RECOVERY_BAND = 0.8`（`session-maintenance.ts:328`）
- 输出未完成连续恢复上限：3 次
- 载荷拒绝余量：≥10%
- 通用重试：`maxRetries = 10`，退避 500→8000ms（`docs/non-compaction-retry-policy.md`）
- 溢出恢复：跳过 `handoff`（`session-maintenance.ts:186-200`）

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-maintenance.ts#L328-L328
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-maintenance.ts#L186-L200
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-maintenance.ts#L2828-L2866
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/session/session-maintenance.ts#L4118-L4145
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/docs/compaction.md#L113-L150
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/docs/compaction.md#L219-L221
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/docs/non-compaction-retry-policy.md#L106-L134

**可信度**：【已核实】（重试次数与退避来自文档）

---

## 15. 扩展点

**做法**
omp 有**两层**扩展：`extensions`（可注册工具/命令/provider/UI）与 `hooks`（事件处理器）。与上下文管理直接相关的 hook 事件：`context`（每次 LLM 调用前改写消息）、`before_agent_start`（改提示词/注入消息）、`session_before_compact`（取消压缩或给出完整自定义压缩载荷）、`session.compacting`（只改默认压缩的 prompt / 追加 `<additional-context>` / 写 `preserveData`）、`session_compact`（压缩后观测）、`session_before_tree`（分支摘要前取消或自定义）、`tool_call` / `tool_result`（改写工具输入输出）。**自定义压缩**有三档：改 `compaction.methodOrder` 增删/排序方法；用 `session.compacting` 改提示词与上下文；用 `session_before_compact` 整段替换压缩结果。`preserveData` 会存进 `CompactionEntry` 并跨重建保留，适合放扩展自己的索引/版本标记。omp 没有「注册一个全新压缩方法」的插件 API——方法集是枚举，扩展只能在既有方法上改。

**关键参数与默认值**
- hook 事件清单见 `hooks/types.ts:472-501`
- `session.compacting` 返回 `{prompt?, context?, preserveData?}`（`docs/compaction.md:466-474`）
- `session_before_compact` 返回 `{cancel:true}` 或 `{compaction: CompactionResult}`（`docs/compaction.md:455-464`）

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/extensibility/hooks/types.ts#L472-L501
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/extensibility/hooks/runner.ts#L258-L320
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/coding-agent/src/extensibility/hooks/tool-wrapper.ts#L20-L60
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/docs/compaction.md#L453-L491

**可信度**：【已核实】

---

## 16. 评估与可观测

**做法**
omp 有两套可用于「上下文策略评估」的现成设施。第一，**snapcompact 研究评测**：`packages/snapcompact/research/` 下是一组可复现的 Python 实验（`exp01…`），以 SQuAD 抽取式 QA 的 **recall / F1** 为指标，比较不同帧形状、布局、字体、颜色在真实 provider 计费下的「每 token 保留信息量」；结论直接写回 `resolveShape()` 的形状表。第二，**`packages/stats` 本地观测面板**：解析 `~/.omp/agent/sessions/` 的 JSONL，落 SQLite，按小时 rollup，跟踪 Tokens/s、Cache Rate、Cache Savings、Error Rate、平均延迟、TTFT、API 等价成本。此外 `if-bench`、`eval` 子代理提供任务级评测运行时。**没有**「压缩前后任务成功率」这类内置 A/B 指标——需要自己用 `task`/`eval` 搭配对实验。

**关键参数与默认值**
- snapcompact 指标：SQuAD QA recall/F1 + provider 计费 token
- stats 指标：Tokens/s、Cache Rate、Cache Savings、Error Rate、Latency、TTFT、API-equivalent cost（`packages/stats/README.md`）
- 无内置上下文策略 A/B 指标

**来源**
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/snapcompact/research/exp03_numhard.py#L1-L20
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/snapcompact/research/exp04_layout.py#L1-L25
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/snapcompact/README.md#L1-L20
- https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/packages/stats/README.md#L1-L25

**可信度**：【已核实】；「无上下文 A/B 指标」为【推断】（基于目录与 README）

---

## 17. omp 相对 pi 在上下文管理上新增或改动了什么

> 两者是 fork 关系。下表只列**有源码证据的差异**；「相同」项也写明，避免把所有东西都说成「增强」。

| 维度 | pi（`b45e0eb`） | omp（`f979f46`） | 差异性质 | 证据 |
|---|---|---|---|---|
| **压缩触发阈值** | `contextTokens > window − reserveTokens(16384)`，单一固定预留 | `window − max(floor(window×0.15), reserve ?? 16384)`；另支持 `thresholdTokens` / `thresholdPercent` / 按模型覆盖 | **改动**：从固定绝对值改为「窗口比例下限」，200K 窗口触发点 183,616 → 170,000 | pi `compaction.ts:267-270`；omp `compaction.ts:320-322,384-414` |
| **触发时机** | 轮中、提示前、结束后、手动（4 条） | 上述 4 条 + 输出未完成恢复 + 空闲维护（6 条） | **新增 2 条** | pi `agent-session.ts:777-786,1890-1896,1974,2794`；omp `docs/compaction.md:70-77` |
| **压缩算法** | 只有 LLM 摘要一条路 | 方法链 `remote → snapcompact → handoff → shake → soft`，按可用性回退 | **新增 4 种方法** | `compaction-methods.ts:44-50`；`session-maintenance.ts:4612-4747` |
| **服务端压缩** | 无 | `remote` 默认第一优先：OpenAI Responses compact / Anthropic compaction beta；原生载荷可回放 | **新增** | pi 全仓检索无 `remoteCompaction`；omp `compaction.ts:234-244`、`session-context.ts:484-489` |
| **压缩前裁剪** | 无自动裁剪，只有 `context_edit` 手动省略 | `pruneToolOutputs`（保护 40k / 最少省 20k）+ 逐轮 superseded/useless 裁剪 + 缓存守卫 | **新增** | pi `session-manager.ts:175-180`；omp `pruning.ts:77-83`、`session-maintenance.ts:710-790` |
| **机械省略** | 无 | `shake`：工具结果与大块 fence/XML 换成 `[shaken ~N tokens — recover: artifact://…]` | **新增** | `shake.ts:48-75`、`session-maintenance.ts:1071-1076` |
| **历史转图片** | 无 | `snapcompact`：历史渲染成 PNG 帧，无 LLM 调用，按模型选帧形状 | **新增** | `snapcompact.ts:2349`、`docs/compaction.md:206-217` |
| **切点累加单位** | 逐条消息累加，再找最近的合法切点 | **按整轮**累加（assistant + 全部 toolResult 视为一组），只在合法边界比较预算 | **改动**：避免「切在工具组中间再回退」的边界误差 | pi `compaction.ts:458-479`；omp `compaction.ts:534-549` |
| **保留预算** | 固定 `keepRecentTokens = 20000` | 同默认 20000，但按「provider prompt tokens / 本地估算」比值缩放 | **改动** | pi `compaction.ts:446-479`；omp `compaction.ts:1437-1449` |
| **单回合过长拆分** | 有：历史摘要 + 轮前缀摘要（0.5×reserve） | 有：同结构，合并标记一致 | **相同**（omp 沿用） | pi `compaction.ts:994-1033`；omp `docs/compaction.md:288-303` |
| **摘要模板** | Goal / Constraints / Progress / Key Decisions / Next Steps / Critical Context | 同结构 + `Additional Notes`，旧摘要增量更新 | **基本沿用，字段略增** | pi `compaction.ts:507-538`；omp `docs/compaction.md:305-316` |
| **文件清单** | `<read-files>` / `<modified-files>`，不设条数上限 | `<files>` 目录树折叠，`(Read)/(Write)/(RW)` 标记，**最多 20 个**，超出 elide | **改动** | pi `utils.ts:67-87`；omp `utils.ts:163-188` |
| **历史找回** | 压缩后模型看不到原文；原文仍在 JSONL，但无检索入口 | 默认同样看不到；**实验模式**下 `history://current/full` 可按条目 id 读回原文 | **新增（默认关闭）** | pi `session-manager.ts:476-512`；omp `docs/compaction.md:175-179` |
| **笔记式上下文** | 无 | `context_notes` / `new_context`，笔记跨窗口保留，16,384 字节上限 | **新增（实验，默认 false）** | `context-settings.ts:117-127`、`docs/compaction.md:152-180` |
| **checkpoint / rewind** | 无 | 模型可 `checkpoint(goal)` / `rewind(report)`：以报告替换整段探索分支 | **新增** | `tools/checkpoint.ts:53-131`、`agent-session.ts:10550-10624` |
| **/clear 边界** | 无 `reset_boundary` | 有；晚于压缩的 reset 会让摘要与保留段一起失效 | **新增** | `session-context.ts:350-354,463-482` |
| **子代理** | **无**（README 明示跳过） | 内置 `task`：独立子会话、`outputSchema`、isolation、batch、递归深度 2、输出 500KB/5000 行 | **新增** | pi `README.md:19`；omp `task/types.ts:28-68`、`task/settings.ts` |
| **跨会话记忆** | **无** | 5 种 backend（默认 off）：local / hindsight / mnemopi / sharpshooter；注入上限 5000 token | **新增** | omp `memory-backend/settings.ts:14-22`、`memories/settings.ts:89-93` |
| **规则发现** | 5 个候选名，全局 + 祖先链，worktree 去重；规则一律进 `<project_context>` | 6 个上下文文件 provider + 独立 rule capability（Cursor/Windsurf/Cline/内置等），depth 排序 + **内容包含去重**，`AGENTS.md` 上限 200；规则再分桶为 TTSR（条件触发）/ alwaysApply（全文）/ rulebook（`rule://` 按需） | **改动**：从「固定名单 + 单一注入」到「多生态 + 包含去重 + 三种注入形态」 | pi `resource-loader.ts:184-274`；omp `system-prompt.ts:323-357`、`rule-buckets.ts:8-15`、`workspace-tree.ts:16` |
| **动态注入** | section diff 补丁（只发变化 section）；无 todo/日期 | 日期/cwd 移到首个用户轮；TTSR 注入记录；笔记；section 机制不再以「补丁」为主 | **改动**：从「改提示词」转为「改首个用户轮」以保前缀 | pi `agent-session.ts:1743-1755`；omp `date-cwd-reminder.ts:1-14` |
| **工具输出上限** | 2000 行 / 50KB；bash 落临时文件 | 3000 行 / 50 KiB；单行 512 字节；落 artifact（16 MiB，头 3 MiB） | **改动**：上限与落盘形态都变 | pi `truncate.ts:11-13`；omp `streaming-output.ts:10-30` |
| **多模态** | 只估算（4800 字符/图），无驱逐 | snapcompact、inline snapcompact、provider 图片预算裁剪、可 `dropImages()` | **新增** | pi `compaction.ts:276-291`；omp `provider-image-budget.ts:18-90` |
| **缓存** | section 化 + 摘要 `cacheRetention:none` + 预热 | 静态前缀 + `<project-context>` 最后 + 日期移到首用户轮 + 裁剪缓存守卫 + lookback 余量 + 预热移植 | **改动/增强**：多一层「裁剪也要保缓存」 | pi `compaction.ts:631`、`cache-warmer.ts`；omp `system-prompt.ts:1026-1036`、`docs/compaction.md:248` |
| **失败恢复** | 溢出只允许一次 compact-and-retry；摘要失败即抛 | 先升级模型；溢出/未完成分别走链；未完成连续 3 次上限；进度守卫 80%；本地救援；413 守卫 | **改动/增强**：多了「升级」「进度」「救援」三层 | pi `agent-session.ts:3049-3076`；omp `session-maintenance.ts:328,4118-4145` |
| **扩展钩子** | `context` / `context_with_system` / `before_provider_request` / `session_before_compact` / `session_compact` / `session_before_tree` | 增加 `session.compacting`（改提示词/上下文/preserveData）、`tool_call` / `tool_result`、`agent_end` / `turn_end`；压缩方法可配置排序 | **新增/改动** | pi `extensions/types.ts:785-904`；omp `hooks/types.ts:472-501` |
| **评估设施** | `packages/evals`：docs-lift 对照 | `packages/snapcompact/research`：SQuAD recall/F1；`packages/stats`：缓存率/成本/错误率面板 | **新增**（方向不同） | pi `packages/evals/README.md`；omp `packages/stats/README.md` |

**可信度**：【已核实】（表中每一行的 pi / omp 两侧均有上文章节或源码行号支撑；「增强/新增」的判断基于代码而非文档措辞）

**一句话总结**：omp 没有改掉 pi 的「树 + 投影 + 摘要 + 保留段」骨架；它改的是**决策层**（阈值、切点累加单位、保留预算缩放）和**减量层**（预裁剪、shake、snapcompact、方法链），并新增了 pi 刻意不做的**记忆、子代理、checkpoint/rewind**。因此不能笼统说「omp 更强」：pi 的压缩路径更短、更可预测；omp 的路径更多、默认更早触发、也更依赖配置与模型能力（例如 snapcompact 需要视觉模型）。

---

*配套：`research/source-map/omp.md`。*
