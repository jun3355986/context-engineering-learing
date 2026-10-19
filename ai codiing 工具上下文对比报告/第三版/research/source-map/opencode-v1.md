# opencode v1 · 源码模块地图

- **仓库**：https://github.com/anomalyco/opencode
- **提交号**：`733b2c627e5aec39cb33cc22373bdce33053ef2c`（tag `v1.19.0`）
- **核实日期**：2026-10-18
- **范围**：只映射与上下文管理 16 类相关的模块。v1 出货主体是 `packages/opencode`；`packages/core/src/v1/*` 是 v1 的配置命名空间；`packages/core/src/session/*` 带 `@opencode/v2/*` 标签，属 v2 在建路径（见 §0）。
- **Permalink 基址**：`https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/`

---

## 0. 先看边界：`packages/core` 是混合目录

| 位置 | 归属 | 处理方式 |
|---|---|---|
| `packages/opencode/src/{session,tool,agent,provider,cli}` | **v1 出货** | 正常引用 |
| `packages/core/src/v1/{config,session,...}` | **v1 命名空间**（v1 schema 与配置类型） | 正常引用 |
| `packages/core/src/session/*`（`runner/`、`compaction.ts`、`projector.ts`、`history.ts`） | **v2 在建**（服务标签 `@opencode/v2/*`） | 仅当 v1 出货代码显式 import 时，按"v1 引用的共享定义"标注 |
| `packages/core/src/util/token.ts`、`packages/core/src/fs-util`、`packages/core/src/global` | 共享底座 | 正常引用 |

v1 里对 core 的显式依赖只有两处与本主题有关：`session/compaction.ts:23` 引 `buildPrompt`（摘要模板），`session/prompt.ts:19` 引 `MAX_STEPS_PROMPT`。其余 v2 路径不参与 v1 行为。

---

## 1. `packages/opencode/src/session/`

| 文件 | 职责 | 16 类 | 关键函数 / 符号 |
|---|---|---|---|
| `prompt.ts`（1631 行） | 主循环；用户消息落盘；子任务与压缩调度；system 四块拼装；`@` 引用解析 | 1、3、4、8、10、11、14 | `runLoop`、`prompt`、`loop`、`resolvePromptParts`、`handleSubtask`、`createUserMessage` |
| `message-v2.ts`（750 行） | 消息 ↔ 模型消息转换；替代历史重建；分页读写 | 1、11 | `toModelMessagesEffect`、`filterCompacted`、`filterCompactedEffect`、`page`、`stream`、`latest` |
| `compaction.ts`（608 行） | 压缩编排：选尾、prune、摘要、建条目、续跑 | 7、8、14 | `select`、`splitTurn`、`prune`、`process`、`create`、`preserveRecentBudget`、`completedCompactions`、`serialize` |
| `overflow.ts`（34 行） | 有效窗口与溢出判定 | 5、14 | `usable`、`isOverflow` |
| `processor.ts`（732 行） | 单步 LLM 流处理；工具执行；step-finish 计量；halt；doom loop | 5、6、14 | `process`、`handleEvent`、`halt`、`cleanup`、`DOOM_LOOP_THRESHOLD` |
| `llm/request.ts`（228 行） | 请求准备：system 合成、消息拼接、工具过滤排序、参数与请求头 | 1、13 | `prepare`、`resolveTools`、`hasToolCalls` |
| `llm.ts`（LLM 流封装） | provider 流与重试接线 | 14 | `stream` |
| `system.ts`（154 行） | 系统块：环境、技能清单、MCP 指令；按模型选提示词 | 1、2、3 | `provider`、`environment`、`skills`、`mcp` |
| `instruction.ts`（237 行） | 规则文件发现/读取/合并；就近规则 | 2、4 | `systemPaths`、`system`、`find`、`resolve`、`clear` |
| `reminders.ts`（92 行） | 计划模式提醒注入 | 4 | `apply` |
| `session.ts`（1016 行） | 会话 CRUD；fork；用量换算；计划文件路径 | 11、16 | `fork`、`getUsage`、`plan`、`updateMessage`、`updatePart` |
| `retry.ts`（209 行） | 重试判定与退避 | 14 | `retryable`、`delay`、`policy` |
| `summary.ts` | 消息级摘要（UI 用，不参与上下文压缩） | 16 | `summarize` |
| `revert.ts` | 文件回退（与压缩无关） | 11 | — |
| `todo.ts` | todo 数据存取（工具侧，不注入上下文） | 4 | — |

---

## 2. `packages/opencode/src/tool/`

| 文件 | 职责 | 16 类 | 关键函数 / 符号 |
|---|---|---|---|
| `truncate.ts`（157 行） | 工具输出统一限长、落盘、清理 | 6 | `output`、`limits`、`write`、`cleanup`、`MAX_LINES`、`MAX_BYTES`、`RETENTION` |
| `read.ts` | 文件/目录读取；分页；就近规则注入 | 2、3、6、9 | `run`、`Instruction.resolve` 调用（L300）、`<system-reminder>` 拼接（L355-356） |
| `task.ts`（371 行） | 子代理：子会话、深度限制、前后台、结果信封 | 10 | `execute`、`renderOutput`、`runTask`、`injectBackgroundResult`、`notify` |
| `skill.ts` | 技能正文按需加载 | 3 | `execute` |
| `grep.ts` / `glob.ts` / `list` | 主动检索（替代"预加载全部文件"） | 3、6 | — |
| `bash` / `shell.ts` | 命令执行；输出走 `Truncate.output(direction:"tail")` | 6 | — |
| `registry.ts` | 工具注册与 `tool.definition` 钩子 | 1、15 | — |
| `tool.ts` | 工具定义与上下文类型 | 1 | `define`、`Context` |

---

## 3. 其余相关包

| 路径 | 职责 | 16 类 | 关键点 |
|---|---|---|---|
| `packages/opencode/src/agent/agent.ts`（453 行） | 内置 agent（build/plan/explore/compaction/title/summary）与权限 | 8、10 | `compaction` agent（L219-233，`hidden` + 全 deny） |
| `packages/opencode/src/provider/transform.ts` | provider 参数与缓存标记 | 5、13 | `applyCaching`（L357-404）、`prompt_cache_key` / `promptCacheKey`（L1324-1334） |
| `packages/opencode/src/server/routes/instance/httpapi/` | 手动压缩的 HTTP 入口 | 8 | `session.summarize`（groups L301-314；handlers L273-291） |
| `packages/opencode/src/cli/cmd/tui.ts` | `--continue` / `--session` / `--fork` | 11 | L123-135、L229-230 |
| `packages/app/src/pages/session/use-session-commands.tsx` | 斜杠命令 `/compact` | 8 | L479-484 |
| `packages/plugin/src/index.ts`（335 行） | 插件 `Hooks` 接口（扩展点全集） | 15 | L222-335 |
| `packages/core/src/v1/config/config.ts` | v1 配置 schema：`compaction`、`tool_output`、`subagent_depth` | 2、5、7、8、10 | L84-86、L136-145、L149-168 |
| `packages/core/src/util/token.ts` | 估算公式 | 5 | `estimate`（L3-5） |
| `packages/core/src/session/compaction.ts` | **v1 引用的共享定义**：摘要模板与 `buildPrompt` | 8 | `SUMMARY_TEMPLATE`（L16-46）、`SUMMARY_UPDATE_INSTRUCTIONS`（L47-55）、`buildPrompt`（L160-174） |
| `packages/core/src/session/runner/max-steps.ts` | **v1 引用的共享定义**：`MAX_STEPS_PROMPT` | 1 | 常量 |
| `packages/schema/` | 压缩事件 schema（`SessionCompactionEvent`） | 8、16 | `Compacted` 事件 |

---

## 4. 一次压缩的调用链（跨文件）

```text
用户 /compact  ──► HTTP session.summarize ──► handlers/session.ts:273-291
                     └─ compaction.create(auto:false)          [compaction.ts:559]
                     └─ prompt.loop                            [prompt.ts:1343]

自动触发
  prompt.ts:1161-1168  isOverflow(上一轮 tokens) ──► compaction.create(auto:true)
  processor.ts:491-496 step-finish isOverflow     ──► needsCompaction
  processor.ts:693     process() 返回 "compact"   ──► prompt.ts:1320-1328 create(auto:true)

压缩执行
  runLoop 见 task=compaction ──► compaction.process    [prompt.ts:1149-1158]
      ├─ select: turns / preserveRecentBudget / splitTurn   [compaction.ts:223-269]
      ├─ plugin "experimental.session.compacting"           [compaction.ts:373-377]
      ├─ serialize(head) + buildPrompt(previousSummary)     [compaction.ts:380-391]
      ├─ processor.process(tools:{}, system:[])             [compaction.ts:420-448]
      └─ 失败 → ContextOverflowError + stop                 [compaction.ts:450-459]

重建
  runLoop 下一步 ──► filterCompacted  ──► toModelMessages  ──► prepare
                     [message-v2.ts:534]   [message-v2.ts:131]  [request.ts:56]
```

---

## 5. 源码解读候选（4 个）

1. **`compaction.select` + `splitTurn`**（`session/compaction.ts#L223-L269`、`#L140-L163`）
   理由：v1 压缩的核心决策点——如何在"整 turn 边界""token 预算""tail_turns 上限"三者之间找切点；能自然带出 v1 与 v2（纯 token + user 边界）的对照。

2. **`filterCompacted` 的重排逻辑**（`session/message-v2.ts#L534-L585`）
   理由：v1 的"磁盘保留原文、模型只看替代历史"全靠这个函数；数组位置不再按时间排序，是理解"检查点"最容易讲错的地方。

3. **`Truncate.output` 的"先到者"与落盘分支**（`tool/truncate.ts#L85-L141`）
   理由：一次讲清"限长—落盘—提示回读"三段式，以及为什么"给路径 + 让模型自己 grep"比"直接截断"更省 token；可与 v2 的 head-only 对照。

4. **`LLMRequestPrep.prepare` 的 system 折叠**（`session/llm/request.ts#L56-L112`）
   理由：v1 把四类块压成一条 system 字符串，是缓存前缀失效的直接原因；也是 v2 改成"两段 + 指令基线"的动机来源。

---

## 6. 不在本图范围

- `packages/tui`、`packages/desktop`、`packages/web` 的渲染层。
- `packages/console`、`packages/stats` 等运营侧服务。
- `packages/core/src/session/*` 的 v2 行为（另见 `source-map/opencode-v2.md`）。
