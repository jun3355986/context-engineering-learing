# pi · 源码模块地图

- 仓库：https://github.com/earendil-works/pi
- 提交：`b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb`
- 核实日期：2026-10-18
- Permalink 基址：`https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/`
- 阅读顺序建议：`session-manager.ts`（数据模型）→ `agent-session.ts`（编排）→ `compaction/`（算法）→ `system-prompt.ts` + `resource-loader.ts`（组装）→ `extensions/types.ts`（接缝）

## 1. 关键目录 / 文件

| 路径 | 职责 | 对应 16 类 | 关键函数 / 符号 |
|---|---|---|---|
| `packages/coding-agent/src/core/session-manager.ts` | 只追加 JSONL 会话树；条目类型；投影重建；压缩条目与分支摘要写入；fork | 1、8、11 | `SessionEntry`、`ContextEditEntry`、`sessionEntryToContextMessages()`、`buildContextEntries()`、`buildSessionProjection()`、`appendCompaction()`、`createBranchedSession()`、`open()` / `continueRecent()` |
| `packages/coding-agent/src/core/agent-session.ts` | 会话编排：请求投影、提示词补丁、压缩触发与提交、树导航、溢出恢复、扩展事件 | 1、4、5、8、11、14、15 | `_installAgentRequestProjection()`、`_preparePromptAndToolLoadout()`、`_compactBeforeNextAssistantResponse()`、`compact()`、`_checkCompaction()`、`_runAutoCompaction()`、`navigateTree()`、`_omitRecoveryAttempt()` |
| `packages/coding-agent/src/core/compaction/compaction.ts` | 纯函数压缩引擎：阈值、用量估算、切点、摘要、split turn | 5、8、14 | `calculateContextTokens()`、`estimateProjectedContextTokens()`、`shouldCompact()`、`estimateTokens()`、`findCutPoint()`、`prepareCompaction()`、`compact()`、`generateTurnPrefixSummary()`、`completeSummarization()` |
| `packages/coding-agent/src/core/compaction/utils.ts` | 摘要输入序列化；文件操作清单 | 8 | `serializeConversation()`、`extractFileOpsFromMessage()`、`computeFileLists()`、`formatFileOperations()` |
| `packages/coding-agent/src/core/compaction/branch-summarization.ts` | 离开分支的摘要生成 | 8、11 | `generateBranchSummary()`、`prepareBranchEntries()` |
| `packages/coding-agent/src/core/system-prompt.ts` | 具名 section 组装；section diff；`<project_context>` 渲染 | 1、2、4、13 | `buildSystemPromptSections()`、`buildSystemPromptState()`、`diffSystemPromptSections()`、`renderProjectContext()` |
| `packages/coding-agent/src/core/resource-loader.ts` | 规则文件发现（全局 + 祖先链 + worktree 去重） | 2 | `loadContextFileFromDir()`、`findShadowedContextFile()`、`loadProjectContextFiles()` |
| `packages/coding-agent/src/core/skills.ts` | 技能发现、校验、提示词摘要 | 3 | `loadSkillsFromDir()`、`formatSkillsForPrompt()` |
| `packages/coding-agent/src/core/tools/truncate.ts` | 行/字节双上限、head/tail 截断、UTF-8 边界 | 6 | `truncateHead()`、`truncateTail()`、`truncateLine()`、`truncateMiddle()` |
| `packages/coding-agent/src/core/tools/output-accumulator.ts` | bash 输出滚动缓冲、临时文件、全文读取 | 6 | `OutputAccumulator.snapshot()`、`readFullOutput()` |
| `packages/coding-agent/src/core/tools/bash.ts` | bash 执行、超限落盘提示 | 6 | `persistIfTruncated` 调用点 |
| `packages/coding-agent/src/core/extensions/types.ts` | 扩展事件契约 | 4、8、11、15 | `ContextEvent`、`ContextWithSystemEvent`、`BeforeProviderRequestEvent`、`SessionBeforeCompactEvent`、`SessionBeforeTreeEvent` |
| `packages/coding-agent/src/core/extensions/runner.ts` | 事件分发；`session_before_*` 返回值合并 | 15 | `emit()`、`hasHandlers()` |
| `packages/coding-agent/src/core/cache-warmer.ts` | 缓存保温 | 13 | `CacheWarmer`、TTL × 0.9 调度 |
| `packages/coding-agent/src/core/cache-stats.ts` | 缓存命中/浪费统计 | 13、16 | `CACHE_TTL_MS`、`NOISE_FLOOR_TOKENS` |
| `packages/coding-agent/src/modes/interactive/components/footer.ts` | 上下文百分比、token 统计、成本 | 5、16 | `render()`、`getSessionStats()` |
| `packages/coding-agent/src/core/settings-defaults.ts` | 压缩/分支摘要/重试默认值 | 5、8、14 | `SETTINGS_DEFAULTS` |
| `packages/coding-agent/src/cli/args.ts` | `--no-context-files`、`--skill` 等开关 | 2、3 | 参数解析 |
| `packages/evals/` | 行为评测与 docs-lift 对照 | 16 | `cli.ts`、`docker.ts`、`report.ts` |

## 2. 主链路（读源码时按这个顺序）

```text
用户提交
  → _prepareRun(): 先 _checkCompaction(最近 assistant)   [agent-session.ts:1890]
  → _installAgentRequestProjection(): 生成投影 + 工具     [agent-session.ts:788]
  → _preparePromptAndToolLoadout(): 只发变化的 section     [agent-session.ts:1743]
  → 模型流式回复
  → 工具执行 → truncateHead/Tail（bash 落盘）             [truncate.ts:11]
  → prepareNextTurn: _compactBeforeNextAssistantResponse()  [agent-session.ts:777]
  → compact(): prepareCompaction → findCutPoint → 摘要
  → appendCompaction(): 只追加 CompactionEntry            [session-manager.ts:1261]
  → buildSessionProjection(): 摘要 + firstKeptEntryId 之后
```

## 3. 源码解读候选（4 个）

1. **`findCutPoint()` 与 `isSplitTurn`**（`core/compaction/compaction.ts#L446-L501`）
   理由：这是 pi 压缩的核心决策，能同时讲清「为什么不能切在 toolResult」「为什么切点要回退到最近的合法边界」「单回合过长时如何拆成两份摘要」。对比 omp 的「按整轮累加」有直接教学价值。

2. **`buildContextEntries()`**（`core/session-manager.ts#L476-L512`）
   理由：用不到 40 行说明「压缩不删历史，只改投影」，是理解 pi 会话模型的钥匙；可与 `CompactionEntry` 结构、`firstKeptEntryId` 一起讲。

3. **`diffSystemPromptSections()`**（`core/system-prompt.ts#L217-L229`）
   理由：把「提示词缓存友好」落到一个可逐行注释的函数：为什么 section 化、为什么只发 patch、为什么 `null` 表示删除。适合作为「缓存友好设计」章节的源码锚点。

4. **`session_before_compact` 的调用与返回处理**（`core/agent-session.ts#L2820-L2871`）
   理由：展示 pi 如何把「压缩」做成可替换契约（取消 / 自定义 summary / 自定义 firstKeptEntryId），是「扩展点」章节最好的例子；也能说明 pi 的边界：阈值不可改，只能改产物。

## 4. 不在本图范围

- `packages/ai`、`packages/agent`：更底层的 provider / agent 内核，只在被调用点引用。
- `packages/tui`：渲染层，仅 footer 与 truncate 相关处引用。
- 第三方扩展实现：只分析接口，不分析具体扩展。
