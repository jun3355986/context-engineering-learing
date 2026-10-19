# Claude Code · 上下文管理 16 类事实卡片

> **声明**：Claude Code 部分基于**非官方泄露源码**分析，仅供学习参考，不代表 Anthropic 的官方实现或当前版本。所有结论只代表 **v2.1.88** 这一个版本，新版本可能已改变（标注【可能已变化】）。

- **仓库**：https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88
- **提交号**：`988438af9293b198b03b8c01f97ee5556d2c74e2`
- **核实日期**：2026-10-18
- **分析路径**：`02-claude-code-source-research/src/`（纯 `src/` 快照，1884 个 .ts/.tsx；与 `03-claude-code-runnable/src` 结构一致但少了运行期 `shims/`、`jobs/` 等）。permalink 一律指向该目录。
- **命名说明**：源码由 source map 还原，函数名/变量名可能与原始命名不同；本文只引用还原后可读的符号。
- **来源类型标签**：【源码 v2.1.88】＝本次在源码中直接读到；【官方文档】＝引自第二版基线对官方文档的摘录（本次未重新抓取官网，标注「基线摘录」）；【两者一致】＝两边说法吻合。

---

## A. 装什么（组装）

### 1. 系统提示词组装（12 项重点之一）

**做法**
`getSystemPrompt` 返回的是**字符串数组**，按「静态前缀 → 边界标记 → 动态段」三段拼装。静态段固定为：身份/简介、系统通则、做事方式、行动准则、工具使用、语气风格、输出效率；随后插入一个字符串常量 `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__` 作为缓存边界，再拼接由注册表管理的动态段（会话指引、记忆、环境信息、语言、输出风格、MCP 指令、scratchpad、工具结果清理提示等）。动态段用 `systemPromptSection()` 做记忆化：**计算一次后缓存，直到 `/clear` 或 `/compact` 才清空**；只有显式声明 `DANGEROUS_uncachedSystemPromptSection` 的段（如 MCP 指令）才每轮重算，代码注释说明这是为了避免 MCP 中途连接导致整段缓存失效。最终生效的提示词还有一层优先级：`override` > coordinator > agent 定义 > `--system-prompt` > 默认，`--append-system-prompt` 永远追加在末尾。

**关键参数与默认值**
- 系统提示词块数：静态 7 段 + 动态 N 段（随功能开关变化）
- 记忆化生命周期：`/clear`、`/compact` 时通过 `clearSystemPromptSections()` 清空，并同时重置 beta header latch
- 环境信息：`computeSimpleEnvInfo`（cwd、git、平台、日期等）
- 工具定义：独立于系统提示词，走 `toolSchemas` 数组；两者在 API 层分别打缓存标记

**来源**
- [prompts.ts#L444-L577](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/constants/prompts.ts#L444-L577)（getSystemPrompt 全貌与静态段顺序）
- [prompts.ts#L572-L575](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/constants/prompts.ts#L572-L575)（边界标记位置）
- [systemPromptSections.ts#L16-L58](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/constants/systemPromptSections.ts#L16-L58)（记忆化与缓存破坏）
- [systemPrompt.ts#L41-L123](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/systemPrompt.ts#L41-L123)（优先级链）
- [claude.ts#L1358-L1379](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/api/claude.ts#L1358-L1379)（最终拼装与缓存分块）

**来源类型**：【源码 v2.1.88】；与【官方文档】的「三层（system / project context / conversation）」说法**部分一致**——源码证明存在「静态 vs 动态」的缓存边界，但 CLAUDE.md 并不在系统提示词里（见第 2 类），文档的三层是缓存视角的概括。

**可信度**：【已核实】

**源码解读候选**：`getSystemPrompt` 的静态/动态分段 + `systemPromptSection` 记忆化（systemPromptSections.ts:20）。

---

### 2. CLAUDE.md 的分层与合并（12 项重点之一）

**做法**
`getMemoryFiles()` 按固定顺序收集：受管策略文件 → 受管 `.claude/rules/*.md` → 用户 `~/.claude/CLAUDE.md` 与用户 rules → 从**项目根向下到 cwd** 的每一级（`CLAUDE.md` → `.claude/CLAUDE.md` → `.claude/rules/*.md` → `CLAUDE.local.md`）。各层是**拼接而非覆盖**：`getClaudeMds` 把每个文件渲染成「Contents of <path> (说明)」段落，最后拼成一段统一文本，并在开头加一句「这些指令覆盖默认行为」的总提示。`@path` 引用递归展开，深度上限 `MAX_INCLUDE_DEPTH = 5`；只允许文本类扩展名，避免把二进制读进上下文。带 `paths:` frontmatter 的规则**不预先加载**，只有读/写/编辑命中匹配路径时才作为嵌套记忆追加。合并结果不是放进系统提示词，而是作为一条 `isMeta` 的用户消息，用 `<system-reminder>` 包裹后**前插到消息列表头部**。

**关键参数与默认值**
- `MAX_MEMORY_CHARACTER_COUNT = 40_000`（字符）：仅用于 `doctorContextWarnings` 与状态栏提示的「大文件告警」，**不是硬截断**
- `MAX_INCLUDE_DEPTH = 5`（源码）；官方文档口径是「递归最多 4 跳」→ **不一致**，以源码为准并标注【可能已变化】
- 单文件 4 MiB 跳过：本文件未找到该逻辑（【待核实】，查 `utils/claudemd.ts` 全文未见 4 MiB 常量）
- 条件规则匹配：使用 `ignore()` 做 glob 匹配，相对 `.claude` 的父目录
- 注入位置：消息层首条 `isMeta` 用户消息，不是 system 字段

**来源**
- [claudemd.ts#L790-L950](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/claudemd.ts#L790-L950)（收集顺序与逐级遍历）
- [claudemd.ts#L1153-L1195](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/claudemd.ts#L1153-L1195)（拼装为一段文本 + 总提示）
- [claudemd.ts#L537](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/claudemd.ts#L537)、`#L618-L680`（@include 深度与递归）
- [claudemd.ts#L1354-L1390](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/claudemd.ts#L1354-L1390)（`paths:` 条件规则）
- [doctorContextWarnings.ts#L44-L66](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/doctorContextWarnings.ts#L44-L66)（40k 字符仅触发告警）
- [context.ts#L155-L189](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/context.ts#L155-L189)（userContext 生成）
- [api.ts#L449-L474](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/api.ts#L449-L474)（prependUserContext：包成 system-reminder 前插）

**来源类型**：【源码 v2.1.88】；【官方文档】的四级作用域与「互相不覆盖」与源码**一致**；「4 跳」与源码 5 层**不一致**。

**可信度**：【已核实】

**源码解读候选**：`getMemoryFiles` 的目录向上遍历（claudemd.ts:850-L930）——层级合并的最佳样本。

---

### 3. 按需加载：Skills、MCP 工具、@ 引用（12 项重点之一）

**做法**
**Skills 两段式**：启动时只把「技能名 + 描述 + whenToUse」放进 `skill_listing` 附件；完整 `SKILL.md` 只有被调用时才作为一条用户消息注入。列表有预算：按上下文窗口的 **1% 折算成字符**（×4 字符/token），每条描述硬截断 **250 字符**，内置（bundled）技能不参与截断。**MCP 工具默认延迟**：`getToolSearchMode()` 在未设置环境变量时返回 `tst`，即所有 MCP 工具与标记为 `shouldDefer` 的工具都不进首轮 schema，只暴露名字，模型需要时用 `ToolSearchTool` 拉取完整定义（`defer_loading` + `tool_reference` 块）。`ENABLE_TOOL_SEARCH=auto` 时改为按阈值判断：延迟工具定义超过窗口 **10%** 才启用延迟。`@` 引用走 `processAtMentionedFiles`，把文件内容作为附件（而非用户原文）插入。

**关键参数与默认值**
- 技能列表预算：`SKILL_BUDGET_CONTEXT_PERCENT = 0.01`、`CHARS_PER_TOKEN = 4`、`DEFAULT_CHAR_BUDGET = 8000`
- 单条描述上限：`MAX_LISTING_DESC_CHARS = 250`
- 工具搜索默认：`tst`（总是延迟 MCP + shouldDefer）；`auto` 的默认阈值 `DEFAULT_AUTO_TOOL_SEARCH_PERCENTAGE = 10`
- 网关限制：非第一方 `ANTHROPIC_BASE_URL` 且未显式设置 `ENABLE_TOOL_SEARCH` 时禁用（需要代理转发 `tool_reference`）
- 关闭实验性 beta：`CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` 强制回到 `standard`

**来源**
- [prompt.ts#L20-L50](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/tools/SkillTool/prompt.ts#L20-L50)（预算与单条上限）
- [prompt.ts#L70-L110](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/tools/SkillTool/prompt.ts#L70-L110)（超预算时的截断策略）
- [attachments.ts#L2661-L2753](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/attachments.ts#L2661-L2753)（技能列表附件）
- [toolSearch.ts#L46-L49](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/toolSearch.ts#L46-L49)、`#L154-L198`（模式与默认值）
- [toolSearch.ts#L270-L316](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/toolSearch.ts#L270-L316)（第一方 host 门槛）
- [attachments.ts#L775-L780](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/attachments.ts#L775-L780)、`#L1894-L1965`（@ 引用）

**来源类型**：【源码 v2.1.88】；【官方文档】说描述在 **1,536 字符**处截断 → 与源码 **250 字符**不一致（版本差异，标【可能已变化】）。「MCP 默认延迟 / 10% 阈值」与文档一致。

**可信度**：【已核实】

**源码解读候选**：`formatCommandsWithinBudget`（SkillTool/prompt.ts:70）——预算不足时如何逐个降级。

---

### 4. 动态注入：system reminder 与变化增量（12 项重点之一）

**做法**
每轮请求前，`getAttachments()` 并发跑 37 个 `maybe(...)` 取附件函数（部分受特性开关门控），产出带类型的 `Attachment`，再统一转成消息插入对话。附件分三档：用户输入相关（@文件、MCP 资源、agent 提及、技能发现）、全线程相关（日期变化、延迟工具增量、agent 列表增量、MCP 指令增量、changed_files、嵌套记忆、动态技能、技能列表、plan 模式、todo/task 提醒、teammate 信箱）、仅主线程（IDE 选中、诊断、token 用量、预算、验证提醒）。**增量**是这里的关键设计：agent 列表、延迟工具、MCP 指令都从历史里的旧 delta 重建「已公告集合」，只追加新增/移除项；代码注释明确指出，把 agent 列表放回工具描述曾导致约 10.2% 的全局 cache_creation。系统侧还有一条 `prependUserContext`，把 CLAUDE.md 与当前日期包成 `<system-reminder>` 前插。

**关键参数与默认值**
- 附件总超时：1000 ms（`setTimeout(..., 1000)` 后 abort）
- 关闭开关：`CLAUDE_CODE_DISABLE_ATTACHMENTS`、`CLAUDE_CODE_SIMPLE`
- delta 类型：`deferred_tools_delta`、`agent_listing_delta`、`mcp_instructions_delta`
- todo 提醒按「距上次提醒的轮数」触发（具体阈值见 `getTodoReminderTurnCounts`）

**来源**
- [attachments.ts#L743-L1003](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/attachments.ts#L743-L1003)（getAttachments 全量清单）
- [attachments.ts#L1455-L1475](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/attachments.ts#L1455-L1475)（延迟工具 delta）
- [attachments.ts#L1490-L1556](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/attachments.ts#L1490-L1556)（agent 列表 delta 与缓存解释）
- [attachments.ts#L1559-L1590](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/attachments.ts#L1559-L1590)（MCP 指令 delta）
- [api.ts#L449-L474](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/api.ts#L449-L474)（userContext 前插）
- [claude.ts#L1347-L1356](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/api/claude.ts#L1347-L1356)（把 Chrome 指令移出系统提示词的理由）

**来源类型**：【源码 v2.1.88】；【官方文档】只描述「system-reminder 是系统注入的提示」，未描述 delta 机制 → 源码更细。

**可信度**：【已核实】

**源码解读候选**：`getAgentListingDeltaAttachment`（attachments.ts:1490）——「只注入变化」与缓存保护的因果链很完整。

---

## B. 量多少（预算）

### 5. Token 计数与 /context（12 项重点之一）

**做法**
判断阈值用的是 `tokenCountWithEstimation`：先找最后一条带真实 `usage` 的助手消息，取其 `input + cache_creation + cache_read + output`，再加上此后新增消息的粗略估算（`length / 4`）。并行工具调用会把一条响应拆成多条助手记录，函数会回退到同一 `message.id` 的最早兄弟，避免漏算夹在中间的 `tool_result`。`/context` 走另一条路：`analyzeContextUsage` 用 count_tokens API 逐类计数（系统提示词、CLAUDE.md、内置工具、MCP 工具、自定义 agent、斜杠命令、技能、消息），API 不可用时回退到 Haiku 计数，最后按类别展示并留出 Autocompact buffer。窗口大小由 `getContextWindowForModel` 决定：默认 200,000；模型名带 `[1m]`、capability 声明或 beta header 可到 1,000,000。

**关键参数与默认值**
- `MODEL_CONTEXT_WINDOW_DEFAULT = 200_000`
- 粗估：`roughTokenCountEstimation = round(chars / 4)`
- 工具计数固定开销：`TOOL_TOKEN_COUNT_OVERHEAD = 500`（每次带工具的计数调用都有一次前导开销，逐工具计数时要扣掉）
- `/context` 展示项：系统提示词 / 记忆文件 / 内置工具 / MCP 工具 / Agent / 命令 / 技能 / 消息 / Autocompact buffer
- 1M 上下文：`[1m]` 后缀或 `CONTEXT_1M_BETA_HEADER`

**来源**
- [tokens.ts#L226-L261](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/tokens.ts#L226-L261)（canonical 计数）
- [tokenEstimation.ts#L203-L210](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/tokenEstimation.ts#L203-L210)（chars/4）
- [analyzeContext.ts#L75](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/analyzeContext.ts#L75)、`#L918-L1000`（/context 分类计数）
- [context.ts#L9-L98](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/context.ts#L9-L98)（窗口解析）
- [index.ts#L4-L15](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/commands/context/index.ts#L4-L15)（命令注册）

**来源类型**：【源码 v2.1.88】；【官方文档】的「/context 显示各类占用」与源码一致，但文档未给 chars/4 公式。

**可信度**：【已核实】

**源码解读候选**：`tokenCountWithEstimation`（tokens.ts:226）——「服务端真值 + 本地增量」的混合计量。

---

### 6. 工具输出落盘（12 项重点之一）

**做法**
每个工具声明自己的 `maxResultSizeChars`，实际阈值取 `min(声明值, DEFAULT_MAX_RESULT_SIZE_CHARS)`；Read 声明 `Infinity`，表示它用 token 自限、不走落盘（否则会形成「读文件→落盘→再读」的循环）。超过阈值时，`persistToolResult` 把完整内容写到 `<project>/<sessionId>/tool-results/<toolUseId>.txt|json`，消息里替换成 `<persisted-output>` 包裹的「文件路径 + 前 2000 字节预览」。同一轮并行工具的结果还有**按消息聚合预算**：单条用户消息里所有 `tool_result` 合计超过 200,000 字符时，按大小降序挑最大的块落盘，直到回到预算内。通用落盘函数只处理文本块；Bash / PowerShell 另有自己的「工作文件 → tool-results」路径（先流式写文件，结束后读回并内联，超限才落盘）。

**关键参数与默认值**
- 全局单条上限：`DEFAULT_MAX_RESULT_SIZE_CHARS = 50_000`
- 单条消息聚合上限：`MAX_TOOL_RESULTS_PER_MESSAGE_CHARS = 200_000`
- 预览：`PREVIEW_SIZE_BYTES = 2000`
- Bash：`maxResultSizeChars = 30_000`；Grep：`20_000`；Read：`Infinity`
- 目录：`~/.claude/projects/<project>/<sessionId>/tool-results/`
- 目录清理：随会话 transcript 按 `cleanupPeriodDays` 到期（官方文档，默认 30 天）

**来源**
- [toolResultStorage.ts#L27-L34](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/toolResultStorage.ts#L27-L34)、`#L55-L78`（阈值解析）
- [toolResultStorage.ts#L104-L117](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/toolResultStorage.ts#L104-L117)（落盘路径）
- [toolResultStorage.ts#L137-L199](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/toolResultStorage.ts#L137-L199)（persist + 预览消息）
- [toolResultStorage.ts#L205-L242](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/toolResultStorage.ts#L205-L242)（processToolResultBlock）
- [toolLimits.ts#L13-L49
- [BashTool.tsx#L424](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/constants/toolLimits.ts#L13-L49
- [BashTool.tsx#L424](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/tools/BashTool/BashTool.tsx#L424)；[GrepTool.ts#L164](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/tools/GrepTool/GrepTool.ts#L164)；[FileReadTool.ts#L342](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/tools/FileReadTool/FileReadTool.ts#L342)

**来源类型**：【源码 v2.1.88】；【官方文档】说「约 30,000 字符内联、超过给路径 + 前 2,000 字符」与 Bash 实现**一致**；文档另提「工具/hook 输出超过 10,000 字符落盘」——本源码的通用阈值是 **50,000**，两者口径不同（版本差异，标【可能已变化】）。

**可信度**：【已核实】

**源码解读候选**：`maybePersistLargeToolResult`（toolResultStorage.ts:272）——阈值、落盘、替换三步。

---

### 7. 旧工具结果清理（不调用模型）（12 项重点之一）

**做法**
清理入口是 `microcompactMessages`，有两条路。第一条是**时间触发**：距最后一条助手消息超过 `gapThresholdMinutes`（默认 60 分钟）时，认为服务端缓存已冷，直接把旧的可清理工具结果内容替换成 `[Old tool result content cleared]`，只保留最近 `keepRecent` 条；该配置默认 **disabled**。第二条是**缓存编辑**：只对主线程、受支持模型、且 `CACHED_MICROCOMPACT` 特性开启时生效，不修改本地消息，而是在 API 层插入 `cache_edits`（删除指定 `cache_reference`），从而在不使缓存前缀失效的前提下让服务端丢弃旧结果。源码注释明确：**旧版「直接清空旧结果」的路径已删除**，外部构建/非 ant 用户/不支持的模型上这里**什么都不做**，上下文压力完全交给 autocompact。

**关键参数与默认值**
- 可清理工具白名单：Read、Shell 系、Grep、Glob、WebSearch、WebFetch、Edit、Write
- 时间触发：`enabled=false`、`gapThresholdMinutes=60`、`keepRecent=5`
- 占位文本：`[Old tool result content cleared]`
- 缓存编辑：受 `Feature('CACHED_MICROCOMPACT')` 与模型能力双重门控

**来源**
- [microCompact.ts#L36-L50](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/microCompact.ts#L36-L50)（占位文本与白名单）
- [microCompact.ts#L253-L293](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/microCompact.ts#L253-L293)（分流与「legacy path removed」注释）
- [microCompact.ts#L305-L399](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/microCompact.ts#L305-L399)（cache_edits 路径）
- [microCompact.ts#L422-L470](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/microCompact.ts#L422-L470)（时间触发与清除）
- [timeBasedMCConfig.ts#L28-L40](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/timeBasedMCConfig.ts#L28-L40)（默认 disabled/60/5）

**来源类型**：【源码 v2.1.88】；【官方文档】说「先清理较旧工具输出，再按需摘要」——源码显示这条「先清理」在外部构建里**默认不生效**，两者**不一致**，以源码为准。

**可信度**：【已核实】

**源码解读候选**：`microcompactMessages` 的分流（microCompact.ts:253）——三种策略的优先级与门控。

---

### 8. 自动压缩与 /compact（12 项重点之一）

**做法**
阈值计算分三层：有效窗口 = 模型窗口 − `min(模型最大输出, 20_000)`；自动压缩线 = 有效窗口 − `13_000`；阻塞线 = 有效窗口 − `3_000`。触发时先尝试 **session memory 压缩**（用已积累的会话记忆做替代），失败再走经典 `compactConversation`。压缩请求是一个**独立请求**：复用主对话的系统提示词、工具和历史，末尾追加一段「不要调用工具、先写 `<analysis>` 再写 `<summary>`」的指令；发送前剥掉图片块，避免压缩请求自己超窗。压缩结果格式化时丢掉 `<analysis>` 草稿，只保留 `<summary>` 正文，并作为一条 `isCompactSummary` 用户消息插在边界标记之后。压缩完成后按固定清单**重新附带**：最近修改的最多 5 个文件（每个 ≤5,000 token，总预算 50,000）、plan 文件、plan 模式指令、本会话调用过的技能正文（每个 ≤5,000 token，总 25,000，从最近调用开始填）、延迟工具增量的全量重播、agent 列表、MCP 指令、SessionStart 钩子输出。`/compact` 手动路径额外支持附加说明，并先跑 PreCompact 钩子，钩子可以改写附加说明。

**关键参数与默认值**
- `MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000`
- `AUTOCOMPACT_BUFFER_TOKENS = 13_000`；`WARNING_THRESHOLD_BUFFER_TOKENS = 20_000`；`ERROR_THRESHOLD_BUFFER_TOKENS = 20_000`；`MANUAL_COMPACT_BUFFER_TOKENS = 3_000`
- 连续失败熔断：`MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`
- 环境变量：`CLAUDE_CODE_AUTO_COMPACT_WINDOW`（只能调小窗口）、`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`（1–100，取 min，只能调低）、`DISABLE_AUTO_COMPACT`、`DISABLE_COMPACT`
- 压缩后重附：`POST_COMPACT_MAX_FILES_TO_RESTORE = 5`、`POST_COMPACT_TOKEN_BUDGET = 50_000`、`POST_COMPACT_MAX_TOKENS_PER_FILE = 5_000`、`POST_COMPACT_MAX_TOKENS_PER_SKILL = 5_000`、`POST_COMPACT_SKILLS_TOKEN_BUDGET = 25_000`
- 压缩请求自身超窗重试：`MAX_PTL_RETRIES = 3`；流式重试：`MAX_COMPACT_STREAMING_RETRIES = 2`
- 边界标记：`compact_boundary`，记录 `trigger`、`preTokens`、`messagesSummarized`

**来源**
- [autoCompact.ts#L28-L49](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/autoCompact.ts#L28-L49)（有效窗口）
- [autoCompact.ts#L62-L91](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/autoCompact.ts#L62-L91)（三条线与 override）
- [autoCompact.ts#L93-L158](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/autoCompact.ts#L93-L158)（警告/阻塞/开关）
- [autoCompact.ts#L241-L351](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/autoCompact.ts#L241-L351)（session memory 优先 + 熔断）
- [compact.ts#L122-L131](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/compact.ts#L122-L131)（重附常量）
- [compact.ts#L387-L460](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/compact.ts#L387-L460)（PreCompact、摘要请求、PTL 重试）
- [compact.ts#L517-L585](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/compact.ts#L517-L585)（清缓存 + 重附清单）
- [compact.ts#L596-L624](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/compact.ts#L596-L624)（边界标记 + 摘要消息）
- [prompt.ts#L293-L335](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/prompt.ts#L293-L335)（提示词拼装与 `<analysis>` 剥离）
- [messages.ts#L4530-L4555](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/messages.ts#L4530-L4555)（边界消息结构）
- [compact.ts#L40-L110](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/commands/compact/compact.ts#L40-L110)（手动 /compact）

**来源类型**：【源码 v2.1.88】；【官方文档】的「先清工具输出再摘要」「压缩后重载 CLAUDE.md/技能/最近 5 文件」与源码**部分一致**：技能 5k/25k、最近 5 文件一致；「先清工具输出」在外部构建默认不生效（见第 7 类）。

**可信度**：【已核实】

**源码解读候选**：`compactConversation` 的重附清单（compact.ts:517-L585）——「压缩后留下什么」最有教学价值。

---

### 9. 多模态上下文

**做法**
图片进入上下文前先做尺寸与体积校验：最大 2000×2000，base64 后不超过 5 MB，目标原始体积 3.75 MB，超限则重缩放/降质。压缩请求发送前调用 `stripImagesFromMessages`，把图片块替换成文本标记，理由写在注释里：摘要不需要图片，而图片容易让压缩请求自己触发 prompt-too-long。通用工具结果落盘只处理文本块；本快照未见把历史图片复制到 `tool-results/` 的代码路径（【推断】）。Claude Code **没有**「把历史渲染成图片」的做法；「附件转文字描述」仅体现在图片被剥离时的占位标记，不是模型生成的描述。

**关键参数与默认值**
- `IMAGE_MAX_WIDTH = 2000`、`IMAGE_MAX_HEIGHT = 2000`
- `API_IMAGE_MAX_BASE64_SIZE = 5 MB`、`IMAGE_TARGET_RAW_SIZE = 3.75 MB`
- 压缩前剥图：始终执行

**来源**
- [apiLimits.ts#L22-L43](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/constants/apiLimits.ts#L22-L43)
- [imageResizer.ts#L192-L210](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/imageResizer.ts#L192-L210)
- [compact.ts#L133-L165](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/compact.ts#L133-L165)（stripImagesFromMessages）

**来源类型**：【源码 v2.1.88】；与【官方文档】的「图片重缩放后超 500 KB 转 JPEG」**不一致**（源码阈值是 5 MB base64 / 2000px），标【可能已变化】。

**可信度**：【已核实】

---

## C. 怎么隔离、怎么延续

### 10. 子代理（12 项重点之一）

**做法**
`AgentTool` 的 `runAgent` 为子代理建独立运行环境：默认 `contextMessages = []`（全新上下文），只有显式传 `forkContextMessages` 时才克隆父对话，并先过滤掉不完整的工具调用。子代理有自己的系统提示词（agent 定义 + 环境）、自己的工具池（`resolveAgentTools` 按定义过滤）、自己的文件状态缓存与 abort controller。两个省 token 的细节：只读代理（Explore/Plan）默认**不注入 CLAUDE.md**（注释给出每周 5–15 Gtok 的节省），Explore/Plan 还**不注入 gitStatus**（最多 40 KB 且已过期）。返回给父代理的是最终内容块（自由文本）+ `agentId` + `<usage>` 尾注；内置一次性代理（Explore/Plan）连尾注都省掉。`isolation: "worktree"` 会创建临时 git worktree，让子代理在隔离副本上工作。

**关键参数与默认值**
- 上下文：默认全新；`forkContextMessages` 才继承
- 只读代理：Explore、Plan（工具池排除写类工具，系统提示词明确禁止修改）
- `omitClaudeMd`：由 agent 定义声明，受 `tengu_slim_subagent_claudemd` 开关控制（默认 true）
- 隔离：`isolation: "worktree"`；`cwd` 与 worktree 互斥
- 并发：受 agent swarms / coordinator 开关控制

**来源**
- [runAgent.ts#L248-L330](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/tools/AgentTool/runAgent.ts#L248-L330)（参数面）
- [runAgent.ts#L370-L410](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/tools/AgentTool/runAgent.ts#L370-L410)（fork 过滤、省略 CLAUDE.md/gitStatus）
- [runAgent.ts#L500-L518](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/tools/AgentTool/runAgent.ts#L500-L518)（工具池与系统提示词）
- [exploreAgent.ts#L15-L60](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/tools/AgentTool/built-in/exploreAgent.ts#L15-L60)（只读约束）
- [AgentTool.tsx#L99-L100](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/tools/AgentTool/AgentTool.tsx#L99-L100)（isolation schema）
- [AgentTool.tsx#L1340-L1373](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/tools/AgentTool/AgentTool.tsx#L1340-L1373)（结果结构）
- [builtInAgents.ts#L30-L70](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/tools/AgentTool/builtInAgents.ts#L30-L70)（内置代理清单）

**来源类型**：【源码 v2.1.88】；【官方文档】的「子代理有独立上下文、只回传结果」与源码**一致**。

**可信度**：【已核实】

**源码解读候选**：`runAgent` 的「fork 与否」分支（runAgent.ts:368-L378）——隔离与继承的开关。

---

### 11. 会话持久化与 /rewind（12 项重点之一）

**做法**
会话以 `<projectDir>/<sessionId>.jsonl` 逐条追加，`recordTranscript` 只写「尚未记录」的消息，并用 `parentUuid` 维护消息链，因此天然支持树状分支与回退。读原始 transcript 有 50 MB 上限，超过直接放弃，避免 OOM。`/rewind` 命令本身只打开消息选择器（返回 `skip`，不追加消息），真正的回退由 `fileHistoryRewind` 执行：每轮对话前 `fileHistoryMakeSnapshot` 为被跟踪文件建版本备份，最多保留 100 个快照，回退时把文件恢复到对应版本；对话侧的截断由选择器 UI 完成（【推断】，本次未逐行读该 UI 组件）。压缩不会删存档：`/compact` 只是替换内存历史并写入边界消息，原始记录仍在 JSONL 里。

**关键参数与默认值**
- transcript：`~/.claude/projects/<project>/<sessionId>.jsonl`
- 读取上限：`MAX_TRANSCRIPT_READ_BYTES = 50 MB`
- 文件快照上限：`MAX_SNAPSHOTS = 100`
- 快照粒度：每条消息一个快照，未变化的文件复用上一版本
- `/rewind`：打开选择器 + 文件回退；不改写历史文件

**来源**
- [sessionStorage.ts#L198-L229](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/sessionStorage.ts#L198-L229)（路径与读取上限）
- [sessionStorage.ts#L1408-L1449](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/sessionStorage.ts#L1408-L1449)（追加与 parentUuid 链）
- [fileHistory.ts#L54-L57](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/fileHistory.ts#L54-L57)（快照上限）
- [fileHistory.ts#L198-L280](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/fileHistory.ts#L198-L280)（建快照/复用未变文件）
- [fileHistory.ts#L347-L398](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/fileHistory.ts#L347-L398)（回退）
- [rewind.ts#L1-L13](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/commands/rewind/rewind.ts#L1-L13)（命令只开选择器）

**来源类型**：【源码 v2.1.88】；【官方文档】的「检查点可回退代码与对话、压缩不改磁盘」与源码**一致**。

**可信度**：【已核实】

**源码解读候选**：`fileHistoryMakeSnapshot`（fileHistory.ts:198）——「每轮快照 + 未变复用」的成本控制。

---

### 12. 跨会话记忆

**做法**
有两套并存的「记忆」。**auto memory**：每个项目一个目录 `~/.claude/projects/<project>/memory/`，入口 `MEMORY.md`，限制 200 行 / 25,000 字节；模型在会话中自行读写主题文件，入口文件是索引。**session memory**：会话内后台摘要，达到初始化阈值（10,000 token）后启用，此后每增长 5,000 token 且满足工具调用条件（3 次）时抽取一次，产物用于压缩时替代整段摘要（`trySessionMemoryCompaction`）。检索侧还有 `findRelevantMemories`，按当前对话找相关记忆并作为附件注入。记忆写入/读取都走独立的工具与提示词，不直接改系统提示词。

**关键参数与默认值**
- auto memory：`ENTRYPOINT_NAME = MEMORY.md`、`MAX_ENTRYPOINT_LINES = 200`、`MAX_ENTRYPOINT_BYTES = 25_000`
- session memory：`minimumMessageTokensToInit = 10_000`、`minimumTokensBetweenUpdate = 5_000`、`toolCallsBetweenUpdates = 3`
- 目录可用 `CLAUDE_COWORK_MEMORY_PATH_OVERRIDE` / `autoMemoryDirectory` 覆盖

**来源**
- [memdir.ts#L36-L45](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/memdir/memdir.ts#L36-L45)（入口限制）
- [paths.ts#L85-L90](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/memdir/paths.ts#L85-L90)、`#L223-L235`（记忆根目录）
- [findRelevantMemories.ts#L39](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/memdir/findRelevantMemories.ts#L39)（检索入口）
- [sessionMemoryUtils.ts#L31-L36](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/SessionMemory/sessionMemoryUtils.ts#L31-L36)（阈值）
- [sessionMemory.ts#L134-L181](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/SessionMemory/sessionMemory.ts#L134-L181)（抽取条件）

**来源类型**：【源码 v2.1.88】；【官方文档】的「auto memory 由 Claude 读写、按项目隔离」与源码**一致**；文档未给 200 行/25 KB 上限。

**可信度**：【已核实】

---

## D. 怎么保证质量

### 13. 缓存断点（12 项重点之一）

**做法**
缓存标记分两层。**系统提示词层**：`splitSysPromptPrefix` 把系统提示词切成最多 4 块——计费/归属头（无 scope）、CLI 前缀、边界前的静态内容（`scope: 'global'`）、边界后的动态内容（无 scope）；第三方 provider 或缺少边界时退化为「头 + 前缀(org) + 其余(org)」三块。**消息层**：`addCacheBreakpoints` 在**每条请求里只放一个**消息级 `cache_control` 标记，位置是最后一条消息；`skipCacheWrite`（fire-and-forget fork）时移到倒数第二条，避免 fork 把自己的尾巴写进缓存。注释解释了「只放一个」的原因：多标记会让倒数第二个位置也被保护，白白多留一轮 KV 页。TTL 由 `getCacheControl` 决定：默认 `ephemeral`，满足条件时升为 `1h`；资格一次性锁存，避免会话中途 overage 翻转导致 TTL 变化、整段缓存失效。

**关键参数与默认值**
- 消息级标记数：**恰好 1 个/请求**
- 系统提示词块：最多 4 块（头 / 前缀 / 静态 / 动态）
- scope 取值：`null` / `'org'` / `'global'`
- TTL：`ephemeral` 默认；`1h` 需用户资格 + GrowthBook allowlist（或 Bedrock 显式开启）
- 关闭缓存：`DISABLE_PROMPT_CACHING_OPUS` 等环境变量

**来源**
- [claude.ts#L358-L374](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/api/claude.ts#L358-L374)（getCacheControl）
- [claude.ts#L393-L420](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/api/claude.ts#L393-L420)（1h 资格锁存）
- [claude.ts#L3063-L3106](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/api/claude.ts#L3063-L3106)（单标记规则与 fork 位移）
- [api.ts#L296-L360](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/api.ts#L296-L360)（系统提示词分块）
- [api.ts#L362-L400](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/api.ts#L362-L400)（boundary 分块）

**来源类型**：【源码 v2.1.88】；【官方文档】的「按变化频率排序以优化前缀缓存」与源码**一致**；「4 个断点」的说法在本源码里是**系统提示词块上限**，消息层只有 1 个标记——两者不要混。

**可信度**：【已核实】

**源码解读候选**：`addCacheBreakpoints`（claude.ts:3063）——20 行说明「为什么只有一个断点」。

---

### 14. 失败恢复

**做法**
上下文溢出有两条恢复路径。主动路径是 autocompact（第 8 类）；被动路径是 **reactive compact**：API 返回 413 / prompt-too-long 时，错误被「扣住」不直接抛给用户，先触发一次压缩，成功后用 `reactive_compact_retry` 状态重试本轮，并且只允许尝试一次（`hasAttemptedReactiveCompact`）。压缩请求自身超窗时，按 API 轮次分组砍掉最旧的一组再重试，最多 3 次；仍失败才抛错。连续 3 次自动压缩失败会触发熔断，本会话不再尝试，避免「每次请求都打一次注定失败的压缩」。输出侧还有一条独立恢复：默认 8,000 输出上限被截断时，同请求升级到 64,000 重试一次。

**关键参数与默认值**
- `MAX_PTL_RETRIES = 3`（压缩请求内部）
- `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`（熔断）
- reactive compact：每轮最多 1 次
- 输出升级：`CAPPED_DEFAULT_MAX_TOKENS = 8_000` → `ESCALATED_MAX_TOKENS = 64_000`
- 递归保护：`querySource === 'session_memory' | 'compact'` 时禁止自动压缩

**来源**
- [autoCompact.ts#L160-L239](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/autoCompact.ts#L160-L239)（递归保护与开关）
- [autoCompact.ts#L257-L350](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/autoCompact.ts#L257-L350)（熔断）
- [compact.ts#L225-L240,L460-L491](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/autoCompact.ts#L257-L350（熔断）
- [compact.ts#L225-L240,L460-L491](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/compact.ts#L225-L491（PTL 截断重试）
- [query.ts#L1150-L1183](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/query.ts#L1150-L1183)（reactive compact 重试与放弃）
- [context.ts#L18-L25](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/context.ts#L18-L25)（8k→64k）

**来源类型**：【源码 v2.1.88】；【官方文档】只描述「溢出时压缩并重试」，未给具体次数 → 源码更细。

**可信度**：【已核实】

---

### 15. 扩展点：hooks（12 项重点之一）

**做法**
hooks 是外部命令/HTTP 端点在生命周期事件上的回调。本轮实际读取到的语义：`PreToolUse` 退出码 0 时 stdout/stderr 不进上下文，退出码 2 把 stderr 给模型并阻断工具调用，其他退出码只给用户看；`PostToolUse` 退出码 0 的 stdout 只在 transcript 模式可见，退出码 2 的 stderr 立即给模型；`UserPromptSubmit` 的 `hookSpecificOutput.additionalContext` 是**必填**，会注入上下文；`SessionStart` 除 `additionalContext` 还可给 `initialUserMessage` 与 `watchPaths`；`PreCompact` 可以改写自定义压缩指令（`mergeHookInstructions`），从而影响摘要重点。所有 hook 的普通 stdout 默认**不**进上下文，只有 `additionalContext` 字段进。hooks 的附加上下文以 `hook_additional_context` 附件形式出现，而不是改系统提示词。

**关键参数与默认值**
- 事件：`PreToolUse`、`PostToolUse`、`PostToolUseFailure`、`UserPromptSubmit`、`SessionStart`、`SessionEnd`、`PreCompact`、`SubagentStart`、`SubagentStop`、`Stop`、`Setup` 等
- 退出码：0 / 2 / 其他（语义见上）
- JSON 字段：`continue`、`decision`、`reason`、`systemMessage`、`hookSpecificOutput.additionalContext`、`permissionDecision`、`updatedInput`、`updatedMCPToolOutput`
- 超时/异步：支持 async hook，结果以附件回传

**来源**
- [hooks.ts#L400-L451](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/hooks.ts#L400-L451)（JSON 输出 schema 与解析）
- [hooks.ts#L590-L650](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/hooks.ts#L590-L650)（各事件的 additionalContext 抽取）
- [hooksConfigManager.ts#L26-L46](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/hooks/hooksConfigManager.ts#L26-L46)（退出码语义，原文写在事件说明里）
- [compact.ts#L411-L424](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/compact/compact.ts#L411-L424)（PreCompact 改写指令）
- [attachments.ts#L964-L966](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/utils/attachments.ts#L964-L966)（async hook 响应附件）

**来源类型**：【源码 v2.1.88】；【官方文档】的「hook stdout 默认不进上下文、只有 additionalContext 进」与源码**一致**。

**可信度**：【已核实】

**源码解读候选**：`parseHookOutput` 的 JSON schema（hooks.ts:400）——扩展点如何与上下文边界交互。

---

### 16. 评估与可观测

**做法**
Claude Code **没有**面向用户的评测框架；可观测性由三部分组成：`/context` 的分类占用、`/cost` 与 cost-tracker 的成本统计、以及内部 analytics 事件（含 cache break detection：专门检测「本可命中却没命中」的原因并上报）。`promptCacheBreakDetection` 会对比系统提示词哈希、工具哈希、TTL/scope 变化，判断缓存失效归因，这对做 A/B 很有参考价值，但它是内部诊断，不是评测产品。因此教程若要讲 L5，需要外接评测集，工具本身只提供原始指标。

**关键参数与默认值**
- 无评测集 / 无 A/B 开关
- 可观测：`/context`、`/cost`、cache break 事件、OTEL
- 缓存失效归因项：system prompt 变化、工具变化、TTL/scope 变化、压缩

**来源**
- [promptCacheBreakDetection.ts#L31](https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88/blob/988438af9293b198b03b8c01f97ee5556d2c74e2/02-claude-code-source-research/src/services/api/promptCacheBreakDetection.ts#L31)、`#L270-L290`、`#L520-L540`（归因维度）
- `commands/context/index.ts`、`commands/cost`
- 反证：`src/` 下无 eval/benchmark 目录

**来源类型**：【源码 v2.1.88】；【官方文档】未承诺评测能力 → 无冲突。

**可信度**：【已核实】（「无内置评测」为反证结论）

---

## 附：12 项重点对照

| 重点项 | 落点 | 核心数字 |
|---|---|---|
| 系统提示词组装 | 第 1 类 | 静态 7 段 + 边界 + 动态段；/clear、/compact 清缓存 |
| CLAUDE.md 分层与合并 | 第 2 类 | Managed→User→逐级目录→Local；include 深度 5 |
| system reminder | 第 4 类 | 37 个 `maybe(...)` 附件源；三种 delta |
| token 计数与 /context | 第 5 类 | 末次 usage + chars/4；默认 200k |
| 工具输出落盘 | 第 6 类 | 50k 字符 / 2k 预览 / tool-results |
| 旧工具结果清理 | 第 7 类 | 时间触发默认关；cache_edits 仅主线程 |
| 自动压缩与 /compact | 第 8 类 | 有效窗口−13k；重附 5 文件 / 25k 技能 |
| 子代理 | 第 10 类 | 默认全新上下文；只读代理省 CLAUDE.md |
| 会话持久化与 /rewind | 第 11 类 | JSONL + parentUuid；100 个文件快照 |
| 缓存断点 | 第 13 类 | 消息层恰好 1 个标记 |
| Skills / MCP 按需加载 | 第 3 类 | 描述 250 字符；MCP 默认延迟，阈值 10% |
| hooks | 第 15 类 | 退出码 0/2/其他；只有 additionalContext 进上下文 |

## 附：与第二版基线的口径差异

| 项 | 第二版（闭源 2.1.299 观测） | 第三版（源码 v2.1.88） |
|---|---|---|
| 证据等级 | 官方文档 + 分发件观察 | 源码直接阅读 |
| CLAUDE.md 位置 | 描述为「project context 层」 | 实际是消息层首条 meta 用户消息 |
| 旧工具结果清理 | 文档说「先清工具输出再摘要」 | 外部构建默认不做，交给 autocompact |
| 技能描述截断 | 1,536 字符 | 250 字符（每技能条目） |
| 工具输出阈值 | 约 30,000 字符（Bash）/ 10,000（通用） | Bash 30,000；通用 50,000 |
| 压缩摘要模板 | 不可见 | 可见（不发原文，只概括结构） |
| 图片限制 | 500 KB 转 JPEG | 2000px / 5 MB base64 / 3.75 MB 目标 |
