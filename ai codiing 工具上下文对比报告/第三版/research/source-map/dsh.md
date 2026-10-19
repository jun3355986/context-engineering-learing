# DeepSeek Harness（dsh）· 源码模块地图

- **仓库**：https://github.com/deepseek-ai/deepseek-harness
- **提交**：`571902028a75c64c1d767f4ae5fd099485f0ddf0`（`master`）
- **核实日期**：2026-10-18
- **Permalink 基址**：`https://github.com/deepseek-ai/deepseek-harness/blob/571902028a75c64c1d767f4ae5fd099485f0ddf0/`
- **工程形态**：pnpm monorepo，`apps/`（cli/desktop/web）＋ `packages/`（约 60 个包，按域分组：core / session / llm / compaction / spill / context / skill / subagent / mcp / todo / bundle …）＋ `native/`（系统层）。包与包之间只通过 `ctx` 服务键与类型化事件耦合。
- **阅读顺序建议**：`docs/architecture.md`（心智模型）→ `packages/core/session/src/surface.ts`（surface 与 `surfaceOp`）→ `packages/core/session/src/index.ts`（`deriveMessages`）→ `packages/llm/token-meter/src/estimate.ts`（计价）→ `packages/compaction/compaction-basic/src/{index,config,region}.ts`（压缩）→ `packages/bundle/base/cordis.patch.yml`（默认装配，最直观的「哪些机制默认开着」）

## 1. 关键目录 / 文件

| 路径 | 职责 | 对应 16 类 | 关键函数 / 符号 |
|---|---|---|---|
| `packages/core/session/src/surface.ts` | 日志之上的「模型可见视图」：哪些事件进 surface、`append` / `replace` 语义、消息投影 | 1、8、11、13 | `SURFACE_EVENT_TYPES`、`SurfaceOp`、`isAppendSurfaceEvent()`、`isReplacementSurfaceEvent()`、`deriveEventMessage()`、`foldSurface()` |
| `packages/core/session/src/index.ts` | `Session` 类：追加事件、surface 维护、`deriveMessages()`、`requestHeader()`、`toolHistory()` | 1、5、11、13 | `Session.append()`、`deriveMessages()`、`requestHeader()`、`toolHistory()` |
| `packages/core/session/src/fork.ts` | 分叉种子：前缀 + `session/end-seed` + 合成 closers | 11 | `buildForkSeed()` |
| `packages/core/session/src/repair.ts` | 崩溃后补齐未闭合的 step/turn | 11、14 | `openTurnClosers()` |
| `packages/core/agent-loop/src/agent.ts` | 一轮/一步的编排：pre-step → 组装 → 请求 → 工具 → 提交；记录 `request/header`、`request/context` | 1、4、5、8、14 | 步进循环、`agent/pre-step`、`agent/request`、`agent/request-error` |
| `packages/core/system-prompt/src/index.ts` | section 注册表、order 排序、complete 段、变量解析、工具 schema 合并 | 1、2、3、13 | `section()`、`getSectionOrder()`、`getContextOrder()`、`assemble()`、`renderPrompt()` |
| `packages/context/agent-instructions/src/*` | AGENTS.md / CLAUDE.md 链加载、字节预算、按需发现、去重与移除通知 | 2、4 | `maxBytes`、`maxSourceBytes`、候选文件常量、根 marker 探测 |
| `packages/context/time-context/src/*` | 时钟注入（时间、时区、距上条消息间隔） | 4、13 | `refreshIntervalMs`（默认 600000） |
| `packages/context/file-reference/src/*` | `@file` 补全（只插路径，不读内容） | 3 | 提及语法、候选排序 |
| `packages/context/session-reference/src/*` | `@session` 有界只读快照 + 不可信警告 | 3、12 | `prepare()`、`maxReferences`、`capturedThroughSeq` |
| `packages/skill/skill/src/*` | 技能注册表：多来源合并、重名解析、按需加载 | 3 | `ctx.skills`、`collectCacheMaxEntries` |
| `packages/skill/tool-skill/src/*` | 技能目录（持久 user 消息）+ `skill` 加载工具 | 3、4 | `catalogDescriptionMaxLength`、`<skill_content>` |
| `packages/mcp/mcp-client/src/*` | MCP 连接、工具注册（`mcp__server__tool`）、instructions 并入提示词 | 1、3 | 服务器命名、工具注册、资源操作 |
| `packages/llm/token-meter/src/estimate.ts` | 固定密度计价（4 字符/token、block/message 结构开销） | 5、8 | `CHARS_PER_TOKEN`、`BLOCK_OVERHEAD`、`ROLE_OVERHEAD`、`estimateContent()` |
| `packages/llm/token-meter/src/index.ts` | `ctx.tokenMeter.measure()`：重放日志定价、复用 provider 用量、节点明细 | 5、8、16 | `measure()`、`estimateMessage()` |
| `packages/llm/token-meter/src/breakdown-projection.ts` | `contextBreakdown` 投影（system / tools / messages） | 5、16 | `breakdownSchema`、`contextBreakdown` |
| `packages/llm/token-meter/src/projection.ts` | `tokenUsage` / `contextPressure` 投影 | 5、16 | `pressureTokens`、`projectedTokens`、`contextWindow` |
| `packages/client/ui-conversation/src/client/skeleton/ContextMeter.tsx` | composer 圆环 + 展开面板（唯一「上下文可视化」入口） | 5、16 | `ContextMeter`、`ROWS`（system/tools/messages） |
| `packages/compaction/compaction/src/index.ts` | 压缩接缝：三方法抽象、触发器类型、手动错误码、`compaction/summary-error` | 8、14、15 | `CompactionEngine.compactIfNeeded/compactNow/compactRegion`、`CompactionTrigger`、`ManualCompactionError` |
| `packages/compaction/compaction/src/tool-pairing.ts` | 切点两侧的工具调用/结果配对校验（带 per-cut 缓存） | 8 | `toolPairingBalancedBefore()`、`toolPairingBalancedAfter()` |
| `packages/compaction/compaction/src/checkpoint.ts` | 摘要 checkpoint 的来源标识与识别谓词（供 client / wire 复用） | 8、11 | `compactCheckpointSource()`、`isCompactCheckpointSource()` |
| `packages/compaction/compaction-basic/src/config.ts` | 压缩配置校验与预算换算（阈值、保留、headroom、输出预留、模型策略） | 5、8、14 | `resolveConfig()`、`resolveTargetPolicy()`、`resolveCompactSpec()` |
| `packages/compaction/compaction-basic/src/index.ts` | 默认后端：pre-step 压力触发、request-error 溢出恢复、三入口分派、重试 | 8、14 | `compactIfNeeded()`、`compactNow()`、`compactRegion()`、`summarize()` |
| `packages/compaction/compaction-basic/src/region.ts` | 选区与事务：保留尾部、平衡边界、`compaction/start…end` 括号 | 8、11、13 | `selectCompactableRange()`、`compactSurfaceRegion()` |
| `packages/compaction/compaction-basic/src/summarizer.ts` | 摘要调用（`ctx.llm.stream`）、checkpoint 包装与安全摘要投影 | 8、13 | `summarizeWithLlm()`、`frameSummary()` |
| `packages/compaction/command-compact/src/*` | `/compact` 人工命令（无参数） | 8、15 | 命令注册、错误文案映射 |
| `packages/compaction/compaction-tool-result-pruner/src/config.ts` | 裁剪预算与校验（8192/4096/1024） | 7 | `DEFAULTS`、`PRUNE_MARKER`、`resolveConfig()` |
| `packages/compaction/compaction-tool-result-pruner/src/index.ts` | `pruneSession()`：改写超预算 tool/result，写影子计价 | 7 | `pruneSession()`、`pruneContent()`、`measureContent()` |
| `packages/compaction/compaction-image-offload/src/*` | 图片 offload 决策、引用校验、占位投影、摘要恢复 | 9、14 | `image/offload`、`ImageOffloadTarget`、恢复监听 |
| `packages/spill/spill/src/*` | spill 存储服务：保存超限文本并返回 locator | 6 | `ctx.spillStore`、`SaveTextSpill`、`SpillRef` |
| `packages/spill/spill-local/src/*` | 本地文件后端（会话私有目录） | 6 | 文件写入与清理 |
| `packages/spill/spill-policy/src/*` | 工具结果保留策略：头/尾 + 省略通知 + 路径 | 6、9 | `maxInlineTokens`、保留计算、通知渲染 |
| `packages/subagent/subagent/src/*` | 委派服务注册表、一次性运行、可继续子代理、发现 | 10 | `ctx.subagents` |
| `packages/subagent/tool-subagent/src/*` | 模型侧委派工具（立即返回 childId + 完成通知） | 10 | `provider`、`toolName`、`maxDepth`、`agentPreset` |
| `packages/subagent/subagent-{spawn,fork}-in-process/src/*` | 进程内子代理（全新 / 历史播种） | 10 | provider 实现 |
| `packages/subagent/subagent-{acp,codex,claude-code,dsh-sdk}/src/*` | 进程外子代理 provider | 10 | provider 实现 |
| `packages/session/session-persistence*/src/*` | 日志持久化 API 与 JSONL 后端、resume、崩溃 closer | 11、14 | `create/open/append/flush`、`interruptedTurnClosers` |
| `packages/session/session-checkpoint-policy/src/*` | 何时必须刷盘（请求前/顶层工具前/下一步前），fail-closed | 11、14 | checkpoint 钩子 |
| `packages/session/session-projection*/src/*` | 会话投影框架与缓存（token/context 投影挂在它上面） | 5、16 | `SessionProjectionStateMap` |
| `packages/todo/tool-todo/src/*` | 任务清单（跨轮/跨 resume 持久，整表替换） | 4、11 | `todo_write` |
| `packages/bundle/base/cordis.patch.yml` | **默认装配清单**：哪些机制默认开、默认参数是多少 | 全部 | `agent-instructions(maxBytes)`、`compaction-basic`、`spill-policy(12500)`、`tool-result-pruner(8192/4096/1024)`、`image-offload` |
| `docs/architecture.md` | 架构心智模型：插件、profile/bundle、事件三分、turn flow | 1、4、11、15 | turn flow 伪代码 `#L84-L121` |
| `docs/subsystems/compaction.md` | 压缩子系统参考（事件、结果、服务签名） | 8、14 | `compaction/*` 事件表、`CompactionResult` |
| `packages/experimental/hook-protocol/src/*` | Claude Code / Codex hooks 兼容层（仅 command 型） | 4、15 | 阻断 / 附加上下文 / 停止 |
| `packages/experimental/worktree/src/*` | worktree 隔离（**实验包**，核心子代理不用） | 10 | — |

## 2. 主链路（读源码按这个顺序）

```text
Boot
  → dsh --profile web：按 profiles → bundles → patch 组装 Cordis 插件树     [第 15 类]
  → base 默认开：agent-instructions(64KiB)、token-meter、compaction-basic、
    spill-policy(12500)、tool-result-pruner(8192/4096/1024)、image-offload   [第 2/5/6/7/8/9 类]

每一步（turn flow，docs/architecture.md#L84-L121）
  → agent/pre-step 瀑布：注入/改写/拒绝本轮输入（time-context、@session）    [第 4 类]
  → 组装 prompt sections + tool schemas                                     [第 1、3 类]
  → compression-basic 的 pre-step 监听：tokenMeter.measure → 过阈值？
       → 先 pruner.pruneSession() → 重新 measure → 仍超？→ 选区 → 摘要      [第 7、8 类]
  → compaction/start → summary → compaction/summary → user/message(replace) → compaction/end
  → step/start → agent/request（解析路由）→ 提交 system/message、user/message
  → 记录 request/header、request/context
  → Session.deriveMessages()：按 surface 节点派生模型历史                    [第 11 类]
  → llm/stream → assistant/message
  → tools/* → tool/result
       → spill-policy：超 maxInlineTokens → 头尾 + 落盘路径                   [第 6 类]
  → 若 provider 报 CONTEXT_WINDOW_EXCEEDED
       → agent/request-error：pruner → 最大平衡头部压缩 → replaceGeneration
         前进才 retry（maxOverflowRetries=1）                                [第 14 类]
  → 若 provider 报 IMAGE_OFFLOAD_REQUIRED
       → 标记最早 N 张 → image/offload → 重试（不耗 provider 重试预算）        [第 9 类]

跨会话
  → session-checkpoint-policy 在请求前/工具前/下一步前 flush（fail-closed）    [第 11 类]
  → resume：读日志 + 合成 closers；fork：前缀 + session/end-seed + closers    [第 11 类]
  → 无记忆系统；跨会话只能靠 AGENTS.md / @session 快照                        [第 12 类]
```

## 3. 源码解读候选（4 个）

### 候选 A：`deriveMessages()` + `surfaceOp` —— 日志与可见视图的两层结构（第 11、8、13 类）
`packages/core/session/src/index.ts#L966-L1005`、`packages/core/session/src/surface.ts#L49-L56`、`#L95-L106`
理由：30 行左右讲清「append-only 日志是真相、surface 是模型视角、`replace` 用新节点遮蔽旧区间」。它是 dsh 所有上下文机制的地基：压缩、裁剪、图片 offload 全都是「往 surface 上追加一个 replace」。缓存失效被收敛到一个 `contentGeneration` 变量，正好用来解释「为什么压缩会打断 prompt cache，而普通追加不会」。适合配一张「日志（全部事件） vs surface（可见节点）」的双层图。

### 候选 B：`selectCompactableRange()` —— 压缩切点的三个约束（第 8 类）
`packages/compaction/compaction-basic/src/region.ts#L117-L155`
理由：39 行同时处理「从尾部累加到 retainTokens」「退到工具调用/结果配对平衡处」「起点不能是 system 节点」，并且拒绝时返回 `null` 而不是抛错（「没有可安全压缩的区间」是正常结果）。这是「压缩切点」章节最好的教学代码，也能自然引出「为什么不能按消息条数切」。

### 候选 C：`resolveCompactSpec()` —— 阈值到底怎么算（第 5 类）
`packages/compaction/compaction-basic/src/config.ts#L153-L204`
理由：52 行里同时有「窗口比例」「输出预留 O」「headroom B」「保留预算必须 < 阈值」四个约束，且每个失败分支都给出可操作的报错文案（该调哪个参数、该配多大窗口）。它把「压缩阈值」从玄学变成一个可推导的公式，适合做交互式演示（拖 W / O / B 看阈值与保留量）。

### 候选 D：`pruneSession()` + 影子计价 —— 无模型削峰（第 7、13 类）
`packages/compaction/compaction-tool-result-pruner/src/config.ts#L8-L13`、`docs/subsystems/compaction.md#L105-L133`
理由：这是「先削峰、可能就不用摘要」的完整范例：确定性切片（码点安全）、原始事件保留可回溯、替换前先写一条 `compaction/prune` 影子计价事件让下游纯投影做减法。与 Grok Build 的 `prune_conversation()`（按轮龄、软裁剪/硬清空）正好形成一对「两种裁剪哲学」的对照。

> 备选：`packages/spill/spill-policy/src/*` 的「头尾各分一半 + 落盘通知」是第 6 类最直观的代码；`packages/compaction/compaction/src/index.ts#L119-L193` 的三方法抽象适合讲「压缩为什么该做成接缝」。
