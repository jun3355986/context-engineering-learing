# oh-my-pi（omp）· 源码模块地图

- 仓库：https://github.com/can1357/oh-my-pi
- 提交：`f979f4639777858de28e6ecb99d577443abe0b7b`
- 核实日期：2026-10-18
- Permalink 基址：`https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/`
- 阅读顺序建议：`session-entries` / `session-context.ts`（数据与投影）→ `session-maintenance.ts`（编排）→ `packages/agent/src/compaction/*`（纯算法）→ `session/compaction-methods.ts`（方法链）→ `system-prompt.ts` + `discovery/`（组装）→ `memory-backend/` + `task/`（新增能力）

## 1. 关键目录 / 文件

| 路径 | 职责 | 对应 16 类 | 关键函数 / 符号 |
|---|---|---|---|
| `packages/coding-agent/src/session/session-context.ts` | 从叶子到根重建模型上下文；压缩/`/clear`/原生回放；悬挂工具调用清理；笔记注入 | 1、4、8、11 | `buildSessionContext()`、`buildSessionPath()`、`resetBoundaryIdx`、`getContextNotes()`、`renderContextNotes()` |
| `packages/coding-agent/src/session/session-manager.ts` | 只追加条目日志；压缩/分支摘要写入；fork；artifact | 1、8、11 | `appendCompaction()`、`branchWithSummary()`、`createBranchedSession()`、`saveArtifact()` |
| `packages/coding-agent/src/session/session-maintenance.ts` | 压缩编排：六条触发、方法链选择与回退、预裁剪、shake、进度守卫、死端救援 | 5、7、8、14 | `runPrePromptCompactionIfNeeded()`、`maintainContextMidRun()`、`checkCompaction()`、`runAutoCompaction()`、`compact()`、`shake()`、`#pruneToolOutputs()`、`#pruneStaleToolResults()`、`#rescueCompactionDeadEnd()` |
| `packages/coding-agent/src/session/compaction-methods.ts` | 方法枚举、默认顺序、可用性判定 | 8、14 | `DEFAULT_COMPACTION_METHOD_ORDER`、`isCompactionMethodUsable()`、`resolveMethodSettings()`、`canUseRemoteCompaction()` |
| `packages/coding-agent/src/session/context-settings.ts` | 压缩/分支摘要/snapcompact 设置默认值 | 5、8、9、11 | `cfgCompactionMethodOrder`、`cfgCompactionThresholdPercent`、`cfgBranchSummaryEnabled`、`cfgSnapcompact*` |
| `packages/agent/src/compaction/compaction.ts` | 纯压缩引擎：阈值、用量、切点、摘要、split turn、原生压缩候选 | 5、8、14 | `calculateContextTokens()`、`effectiveReserveTokens()`、`resolveThresholdTokens()`、`shouldCompact()`、`findCutPoint()`、`prepareCompaction()`、`compact()` |
| `packages/agent/src/compaction/pruning.ts` | 工具输出裁剪与 superseded/useless 省略 | 7 | `pruneToolOutputs()`、`pruneSupersededToolResults()`、`DEFAULT_PRUNE_CONFIG`、`MIN_PRUNE_TOKENS` |
| `packages/agent/src/compaction/shake.ts` | 机械省略：工具结果与大块文本换占位符 | 7、8 | `shake()` 的区域检测、`DEFAULT_SHAKE_CONFIG`、`AGGRESSIVE_SHAKE_CONFIG`、`RESCUE_SHAKE_CONFIG` |
| `packages/agent/src/compaction/utils.ts` | 摘要序列化、文件清单、边界标签转义 | 8 | `serializeConversationForSummary()`、`formatFileOperations()`、`upsertFileOperations()`、`FILE_OPERATION_SUMMARY_LIMIT` |
| `packages/agent/src/compaction/openai.ts` / `anthropic.ts` | provider 原生压缩能力判定 | 8 | `shouldUseOpenAiRemoteCompaction()`、`shouldUseAnthropicNativeCompaction()` |
| `packages/snapcompact/src/snapcompact.ts` | 历史文本 → PNG 帧；帧形状与计价 | 8、9 | `compact()`、`renderMany()`、`frames()`、`resolveShape()`、`FRAME_TOKEN_ESTIMATE` |
| `packages/tui/src/tools/streaming-output.ts` | 工具输出限长与 artifact 落盘 | 6 | `DEFAULT_MAX_LINES`、`DEFAULT_MAX_BYTES`、`DEFAULT_MAX_COLUMN`、`ARTIFACT_DEFAULT_MAX_BYTES` |
| `packages/coding-agent/src/system-prompt.ts` | 静态提示词 + `<project-context>`；规则包含去重；技能过滤 | 1、2、3、13 | `buildSystemPrompt()`、`loadProjectContextFiles()`、`dedupeContainedContextFiles()`、`prompt.render(projectPromptTemplate, …)` |
| `packages/coding-agent/src/discovery/*.ts` | 6 个上下文文件 provider（AGENTS/CLAUDE/custom/Gemini/GitHub/opencode） | 2 | `registerProvider(contextFileCapability.id, …)`、`loadStandaloneContextFiles()` |
| `packages/coding-agent/src/workspace-tree.ts` | workspace 树与 `AGENTS.md` 收集 | 2 | `AGENTS_MD_LIMIT`、`buildWorkspaceTree()` |
| `packages/coding-agent/src/session/date-cwd-reminder.ts` | 日期/cwd 提醒注入首个用户轮 | 4、13 | `renderDateCwdReminder()`、`DateCwdReminderInjector` |
| `packages/coding-agent/src/session/context-notes.ts` | 实验性上下文笔记 | 4、8 | `getContextNotes()`、`renderContextNotes()` |
| `packages/coding-agent/src/memory-backend/*`、`memories/*` | 记忆后端选择、注入、整理 | 12 | `cfgMemoryBackend`、`cfgMemoriesSummaryInjectionTokenLimit`、`startMemoryStartupTask()`、`enqueueMemoryConsolidation()` |
| `packages/coding-agent/src/task/*` | 子代理：发现、spawn、隔离、结构化返回 | 10 | `runSubprocess()`、`buildOutputValidator()`、`MAX_OUTPUT_BYTES`、`task.structured` |
| `packages/coding-agent/src/tools/checkpoint.ts` | checkpoint / rewind 工具契约 | 11 | `CheckpointTool`、`RewindTool`、`CheckpointState` |
| `packages/coding-agent/src/session/agent-session.ts` | 会话门面：checkpoint 状态、rewind 应用、手动 compact/shake | 8、11 | `getCheckpointState()`、`#extractRewindReport()`、`#applyRewind()`、`shake()`、`runIdleCompaction()` |
| `packages/coding-agent/src/extensibility/hooks/*` | hook 事件与分发 | 15 | `HookRunner.emit()`、`session_before_compact`、`session.compacting`、`tool_result` |
| `packages/coding-agent/src/session/cache-warmer.ts` | 缓存保温（自 pi 移植） | 13 | `CACHE_WARMING_MODES`、TTL × 0.9、$0.05 下限 |
| `packages/coding-agent/src/session/context-usage-runtime.ts` | 阈值/预留/推测位置的 UI 边界 | 5、16 | `getSessionCompactionBoundaries()`、`computeSessionContextBreakdown()` |
| `packages/stats/` | 本地观测面板 | 16 | `aggregator.ts`、`gain-aggregator.ts`、`parser.ts` |

## 2. 主链路（读源码时按这个顺序）

```text
用户提交 / 工具轮结束
  → runPrePromptCompactionIfNeeded / maintainContextMidRun / checkCompaction   [session-maintenance.ts:2585,2655,2828]
  → 先 promoteContextModel（有更大窗口模型则切模型）
  → #pruneStaleToolResults / #pruneToolOutputs（缓存守卫）                     [session-maintenance.ts:755,710]
  → runAutoCompaction(reason)                                                  [session-maintenance.ts:4612]
      → resolveCompactionMethodOrder → isCompactionMethodUsable
      → remote | snapcompact | handoff | shake | soft
      → shake 不够则 methodIndex+1 递归
  → #commitAutoCompactionResult → appendCompaction                             [session-manager.ts:3530]
  → buildSessionContext(): 摘要 + firstKeptEntryId + 压缩后                     [session-context.ts:238]
  → 剥离悬挂 tool_use → 丢弃 aborted/error 轮                                   [session-context.ts:673,744]
  → 请求时注入日期/cwd 提醒到首个用户轮                                          [date-cwd-reminder.ts:18]
```

## 3. 源码解读候选（4 个）

1. **`runAutoCompaction()` 的方法链**（`session/session-maintenance.ts#L4612-L4747`）
   理由：一个函数里同时有「按 reason 选方法」「跳过不可用方法」「shake 不够就递归到下一个」「复用推测压缩结果」四种决策，是 omp 压缩架构的核心；与 pi 的单函数 `compact()` 对比强烈。

2. **`buildSessionContext()` 的压缩分支**（`session/session-context.ts#L483-L638`）
   理由：能一次讲清「摘要在最前」「保留段从 firstKeptEntryId 起」「provider 原生载荷替换保留段」「snapcompact 帧重新挂回」四个层次；比 pi 的同名逻辑多出原生回放与 `/clear`。

3. **`pruneToolOutputs()` 的缓存守卫**（`agent/src/compaction/pruning.ts#L537-…` + `session-maintenance.ts#L710-L740`）
   理由：展示「裁剪也要考虑 prompt cache」这一反直觉点：为什么候选结果后面的 suffix 还在热前缀时不能改、为什么 prefix-bound thinking 时守卫要设成 0。适合作为「缓存友好设计」的进阶素材。

4. **`#applyRewind()`**（`session/agent-session.ts#L10550-L10624`）
   理由：这是 omp 独有的「用报告替换探索分支」机制，涉及 `branchWithSummary`、`rewind-report` 自定义消息、同批工具结果重挂、运行时消息重建；能讲清「checkpoint 不是压缩，而是分支回退」这一常见误解。

## 4. 不在本图范围

- `crates/pi-*`：Rust 原生加速（AST、diff、VFS、shell 等），不参与上下文策略决策。
- `packages/{ai,tui,wire,utils}`：provider 内核、渲染、协议层，仅在调用点引用。
- 第三方扩展与 MCP server 实现：只分析接口与默认边界。
- `packages/coding-agent/src/{commit,autoresearch,eval,...}`：与上下文管理无直接关系，除 `eval` / `if-bench` 在评估一节提及。
