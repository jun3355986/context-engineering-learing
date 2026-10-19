# Claude Code v2.1.88 · 源码模块地图

> **非官方源码，仅代表 v2.1.88**。仓库为泄露源码的整合存档，非 Anthropic 官方开源；函数名可能不是原始命名。

- 仓库：https://github.com/jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88
- 提交：`988438af9293b198b03b8c01f97ee5556d2c74e2`
- 分析根路径：`02-claude-code-source-research/src/`（1884 个 .ts/.tsx）
- 核实日期：2026-10-18
- 「16 类」列用编号 1–16，对应 `research/claude-code.md`。

## 0. 三个目录怎么选

| 目录 | 内容 | 本次用途 |
|---|---|---|
| `01-claude-code-source-crack/` | 原始 tgz、解包产物、source map 还原脚本 + 源码 | 只用于确认「还原方式」 |
| `02-claude-code-source-research/src/` | 纯 `src/` 快照，不含构建配置与 shims | **主分析路径**（permalink 指向这里） |
| `03-claude-code-runnable/src/` | 在 02 基础上补 `shims/`、`jobs/`、`proactive/`、`entrypoints/`，可 `bun run dev` | 交叉核对运行期入口 |

## 1. 主循环与请求

| 目录 / 文件 | 职责 | 类 | 关键导出 / 入口 |
|---|---|---|---|
| `QueryEngine.ts` | SDK/headless 侧的查询引擎：组装系统提示词、userContext、systemContext，驱动 `query()` | 1,4 | `QueryEngine.ask`（L288-L330 组装） |
| `query.ts` | 主查询循环：调用模型、跑工具、触发压缩、reactive compact | 1,5,8,14 | `query()`、`prependUserContext` 调用(L660)、413 恢复(L1150-L1183) |
| `query/` | 循环用的配置、依赖注入、stop hooks、token 预算 | 5,15 | `query/config.ts`、`query/tokenBudget.ts`、`query/stopHooks.ts` |
| `Tool.ts` | 工具类型系统（`Tool`/`Tools`/`ToolUseContext`） | 1,6 | `Tool`、`ToolUseContext` |
| `tools.ts` | 工具注册表：按权限/特性组装工具池 | 1,3 | `getTools` 等 |
| `services/api/claude.ts` | 请求构造：系统提示词分块、缓存标记、工具 schema、usage | 1,5,13 | `getCacheControl`(L358)、`addCacheBreakpoints`(L3063)、`queryModelWithStreaming` |
| `services/api/promptCacheBreakDetection.ts` | 缓存失效归因 | 13,16 | `notifyCompaction`、归因维度(L270-L290) |
| `utils/api.ts` | 系统/用户上下文的拼接与分块 | 1,2,13 | `appendSystemContext`(L437)、`prependUserContext`(L449)、`splitSysPromptPrefix`(L322) |
| `context.ts` | `getSystemContext` / `getUserContext`（gitStatus、CLAUDE.md、日期） | 1,2,4 | 两个 memoize 函数(L116、L155) |

## 2. 提示词与规则

| 目录 / 文件 | 职责 | 类 | 关键导出 / 入口 |
|---|---|---|---|
| `constants/prompts.ts` | 默认系统提示词：静态段 + 边界 + 动态段 | 1 | `getSystemPrompt`(L444)、`computeSimpleEnvInfo`(L651)、`SYSTEM_PROMPT_DYNAMIC_BOUNDARY`(L114) |
| `constants/systemPromptSections.ts` | 动态段记忆化与缓存破坏 | 1,13 | `systemPromptSection`(L20)、`DANGEROUS_uncachedSystemPromptSection`(L32)、`resolveSystemPromptSections`(L43) |
| `utils/systemPrompt.ts` | 生效提示词的优先级链 | 1 | `buildEffectiveSystemPrompt`(L41) |
| `utils/claudemd.ts` | CLAUDE.md 分层发现、@include、条件规则、拼接 | 2,3 | `getMemoryFiles`(L790)、`getClaudeMds`(L1153)、`processConditionedMdRules`(L1354) |
| `memdir/` | auto memory 路径、入口、检索、时效提示 | 12 | `getAutoMemPath`(paths.ts:223)、`findRelevantMemories`(L39)、`memoryAge.ts` |
| `bootstrap/state.ts` | 会话级全局状态（含提示词段缓存、beta latch） | 1,13 | `getSystemPromptSectionCache`、`clearSystemPromptSectionState` |

## 3. 动态注入与附件

| 目录 / 文件 | 职责 | 类 | 关键导出 / 入口 |
|---|---|---|---|
| `utils/attachments.ts` | 每轮附件管线：~40 个来源，含三种 delta | 2,3,4,15 | `getAttachments`(L743)、`getDeferredToolsDeltaAttachment`(L1455)、`getAgentListingDeltaAttachment`(L1490)、`getSkillListingAttachments`(L2661) |
| `utils/messages.ts` | 消息构造：meta 消息、边界消息、attachment → message | 4,8,11 | `createUserMessage`、`createCompactBoundaryMessage`(L4530)、`createMicrocompactBoundaryMessage`(L4557) |
| `memdir/memoryAge.ts` | 记忆时效提醒（system-reminder） | 4,12 | `memoryAgeReminder`(L45-L52) |
| `utils/messagePredicates.ts`、`utils/collapse*.ts` | 消息判定与折叠（read-search 折叠等 UI 侧） | 4 | 谓词与折叠函数 |

## 4. 预算与减量

| 目录 / 文件 | 职责 | 类 | 关键导出 / 入口 |
|---|---|---|---|
| `utils/tokens.ts` | canonical 计数：末次 usage + 增量估算 | 5 | `tokenCountWithEstimation`(L226)、`getTokenCountFromUsage`(L46) |
| `services/tokenEstimation.ts` | 粗估 chars/4、API/Haiku 计数回退 | 5 | `roughTokenCountEstimation`(L203)、`countMessagesTokensWithAPI` |
| `utils/analyzeContext.ts` | `/context` 分类统计 | 5,16 | `analyzeContextUsage`(L918)、`countToolDefinitionTokens`(L234) |
| `utils/context.ts` | 窗口大小、1M、输出上限 | 5 | `getContextWindowForModel`(L51)、`MODEL_CONTEXT_WINDOW_DEFAULT`(L9) |
| `utils/toolResultStorage.ts` | 工具结果落盘：阈值、预览、按消息预算 | 6 | `persistToolResult`(L137)、`processToolResultBlock`(L205)、`enforceToolResultBudget`(L769) |
| `constants/toolLimits.ts` | 全局与按消息上限 | 6 | `DEFAULT_MAX_RESULT_SIZE_CHARS`(L13)、`MAX_TOOL_RESULTS_PER_MESSAGE_CHARS`(L49) |
| `services/compact/microCompact.ts` | 旧工具结果清理：时间触发 + cache_edits | 7,13 | `microcompactMessages`(L253)、`evaluateTimeBasedTrigger`(L422) |
| `services/compact/timeBasedMCConfig.ts` | 时间触发默认值 | 7 | `getTimeBasedMCConfig` |
| `services/compact/autoCompact.ts` | 阈值、开关、熔断、session memory 优先 | 5,8,14 | `getEffectiveContextWindowSize`(L33)、`getAutoCompactThreshold`(L72)、`autoCompactIfNeeded`(L241) |
| `services/compact/compact.ts` | 压缩主流程：摘要请求、重附清单、失败分支 | 8,9,14 | `compactConversation`(L387)、`stripImagesFromMessages`(L145)、`createPostCompactFileAttachments`(L1415) |
| `services/compact/prompt.ts` | 摘要提示词与格式清理 | 8 | `getCompactPrompt`(L293)、`formatCompactSummary`(L311) |
| `services/compact/postCompactCleanup.ts` | 压缩后的状态清理 | 8 | `runPostCompactCleanup` |
| `services/compact/grouping.ts` | 按 API 轮次分组（PTL 截断用） | 8,14 | `groupMessagesByApiRound` |
| `services/compact/sessionMemoryCompact.ts` | 用 session memory 替代摘要 | 8,12 | `trySessionMemoryCompaction` |

## 5. 隔离与延续

| 目录 / 文件 | 职责 | 类 | 关键导出 / 入口 |
|---|---|---|---|
| `tools/AgentTool/` | 子代理：调度、运行、恢复、fork、内置定义 | 10 | `runAgent`(runAgent.ts:248)、`AgentTool`(AgentTool.tsx)、`forkSubagent.ts` |
| `tools/AgentTool/built-in/` | Explore / Plan / General / Verification 等 | 10 | `EXPLORE_AGENT`、`PLAN_AGENT`、`GENERAL_PURPOSE_AGENT` |
| `tools/AgentTool/loadAgentsDir.ts` | 从目录加载自定义 agent 定义 | 10 | `AgentDefinition`、`loadAgents` |
| `utils/forkedAgent.ts` | fork 上下文与 CacheSafeParams | 10,13 | `createSubagentContext`、`CacheSafeParams` |
| `utils/sessionStorage.ts` | 会话 JSONL、parentUuid 链、子代理 transcript | 11 | `recordTranscript`(L1408)、`getTranscriptPath`(L202) |
| `utils/sessionRestore.ts` | 恢复/续接 | 11 | 会话恢复入口 |
| `utils/fileHistory.ts` | 文件快照与回退（/rewind 的落地） | 11 | `fileHistoryMakeSnapshot`(L198)、`fileHistoryRewind`(L347) |
| `commands/rewind/` | `/rewind` 命令 | 11 | `call`（打开消息选择器） |
| `services/SessionMemory/` | 会话内记忆抽取与压缩复用 | 8,12 | `shouldExtractMemory`(sessionMemory.ts:134)、`trySessionMemoryCompaction` |
| `memdir/teamMemPaths.ts`、`services/teamMemorySync/` | 团队共享记忆（特性门控） | 12 | TEAMMEM 路径同步 |

## 6. 扩展与按需加载

| 目录 / 文件 | 职责 | 类 | 关键导出 / 入口 |
|---|---|---|---|
| `utils/toolSearch.ts` | MCP/延迟工具搜索：模式、阈值、delta | 3 | `getToolSearchMode`(L172)、`isToolSearchEnabled`(L385)、`getDeferredToolsDelta`(L646) |
| `tools/ToolSearchTool/` | 工具搜索工具本身 | 3 | `ToolSearchTool` |
| `tools/SkillTool/` | 技能调用与列表预算 | 3 | `formatCommandsWithinBudget`(prompt.ts:70)、`SkillTool` |
| `skills/` | 技能目录加载、MCP 技能构建 | 3 | `loadSkillsDir.ts`、`bundledSkills.ts` |
| `services/mcp/` | MCP 连接、工具发现、配置 | 3,15 | `connectToServer`、`fetchToolsForClient` |
| `utils/hooks.ts` | 钩子执行与输出解析 | 15 | `parseHookOutput`(L400)、各 `execute*Hooks` |
| `utils/hooks/hooksConfigManager.ts` | 事件元数据与退出码语义 | 15 | `getHookEventMetadata`(L26) |
| `utils/hooks/registerFrontmatterHooks.ts` | 技能/agent frontmatter 里声明的钩子 | 15 | 注册函数 |
| `plugins/` | 插件加载 | 15 | 插件注册表 |

## 7. 其它容易误读的目录

| 目录 | 实际职责 | 备注 |
|---|---|---|
| `context/` | **React/Ink 的 UI Context**（弹窗、通知、语音） | 不是上下文管理，别按名字误读 |
| `state/` | 应用状态存储 | 与 `bootstrap/state.ts` 的会话级状态不同 |
| `coordinator/` | 多 agent 协调模式（特性门控） | 与 AgentTool 的常规子代理不是同一条路 |
| `bridge/` | IDE 桥接（VS Code / JetBrains） | 不参与提示词组装 |
| `assistant/`、`buddy/`、`vim/`、`voice/` | 产品功能 | 与 16 类无关 |

## 8. 建议做源码解读的功能（4 个）

1. **`getSystemPrompt` 的静态/动态分段 + `systemPromptSection` 记忆化**
   （`constants/prompts.ts:444`、`constants/systemPromptSections.ts:20`）
   理由：直接回答「系统提示词为什么能稳定命中缓存」。分段边界、记忆化生命周期（/clear、/compact 才失效）、`DANGEROUS_uncached` 的取舍，三个点都很具体，且不需要读大段提示词原文。

2. **`addCacheBreakpoints` 的「每请求恰好一个消息级标记」**
   （`services/api/claude.ts:3063`）
   理由：反直觉且可验证。注释解释了多标记为什么会浪费 KV 页、fork 为什么把标记前移一位，是把「缓存友好」从口号变成工程约束的最好例子。

3. **`compactConversation` 的压缩后重附清单**
   （`services/compact/compact.ts:517-L585`）
   理由：回答「压缩后到底还记得什么」。5 个文件、50k 预算、技能 5k/25k、plan、delta 重播、SessionStart 钩子，一张清单六个分支，非常适合画流程图并做交互演示（压缩模拟器）。

4. **`getAttachments` 的 delta 三件套**
   （`utils/attachments.ts:743`、`1455`、`1490`、`1559`）
   理由：展示「只注入变化」如何同时服务正确性与缓存。agent 列表从工具描述挪到 delta 的注释里有真实数据（约 10.2% cache_creation），是难得的「设计动机有量化证据」的段落。
