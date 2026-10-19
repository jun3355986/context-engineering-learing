# opencode v2 · 源码模块地图（beta `2.0.29`）

- **仓库**：https://github.com/anomalyco/opencode
- **提交号**：`042d0832f5f3a73eaa039a58a7d565776f6d4290`（tag `v2.0.29`，**beta**）
- **核实日期**：2026-10-18
- **版本提示**：本文只映射 **beta `v2.0.29`**；beta 线模块边界与文件名可能在下个版本变化。
- **范围**：v2 出货主体 `packages/core`、`packages/cli`、`packages/ai`、`packages/plugin`、`packages/schema`。`packages/core/src/v1/*` 是 v1 配置迁移子集，不计入 v2 行为。
- **Permalink 基址**：`https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/`

---

## 0. 包结构与边界

| 包 | 职责 | 与上下文管理的关系 |
|---|---|---|
| `packages/core` | 会话、工具、指令、技能、配置、持久化、插件宿主 | **主战场**：`src/session/*` 是 v2 会话内核 |
| `packages/cli` | 运行入口、`run`/`mini` 命令、ACP | 恢复入口（`--continue`/`--session`/`--fork`） |
| `packages/ai` | LLM 协议层、消息/事件 schema、缓存策略 | 缓存断点、请求编译、compact 通道 |
| `packages/plugin` | 插件钩子类型与注册 | 扩展点全集（`effect/session.ts`、`effect/tool.ts`） |
| `packages/schema` | 消息、事件、配置的共享 schema | 检查点字段、配置字段、事件字段的唯一真源 |
| `packages/util` | 共享工具（fs、global、effect app-node） | 路径解析、文件系统抽象 |
| `packages/app` / `packages/tui` | 前端与终端界面 | 只在"斜杠命令 / 后台通知"处旁注 |
| `packages/core/src/v1/*` | v1 配置迁移子集 | **不属 v2 行为** |

---

## 1. `packages/core/src/session/`

| 文件 | 职责 | 16 类 | 关键函数 / 符号 |
|---|---|---|---|
| `compaction.ts`（963 行） | 压缩全流程：触发判定、估算、摘要、原生压缩、收缩、记账 | 5、7、8、14、16 | `compact`、`due`、`summarize`、`compactNatively`、`deliver`、`flattenAndDropOldest`、`splitConversation`、`estimateContext`、`estimatePrompt`、`calculateCeiling`、`hasMeasuredPrompt`、`buildPrompt`、`NUDGE` |
| `context.ts`（208 行） | 两阶段解析：`select`（session/agent/指令源/工具快照）→ `load`（模型 + 历史 + 基线） | 1、2 | `select`、`load`、`resolveModel`、`selectTitle` |
| `model-request.ts`（439 行） | 请求装配：system/messages、工具钩子、输出上限、图片预算、缓存键、HTTP/WS 钩子 | 1、9、13 | `baseTranscript`、`prepare`、`boundImages`、`unsupportedParts`、`outputLimit` |
| `history.ts`（181 行） | 按 seq 边界读历史；boundary 判定（latest/local/provenance） | 11 | `latestCompaction`、`messageEntries`、`load`、`entriesForRunner`、`preview` |
| `instruction-state.ts`（274 行） | 指令基线（epoch）、增量提交、blob 存取 | 2、4 | `observe`、`commit`、`prepare`、`apply`、`advanceEpoch`、`initial`、`preview` |
| `instructions.ts`（125 行） | 读取时向上发现 `AGENTS.md`，synthetic 注入 + 台账去重 | 2、4 | `load`、`previouslyInjected` |
| `instruction-entry.ts` | 指令条目快照（fork 继承用） | 2、11 | `snapshot`、`load` |
| `message.ts` | 消息类型重导出（实现见 `packages/schema/src/session-message.ts`） | 11 | — |
| `session.ts`（426 行） | 会话操作：compact / shell / skill / interrupt / revert / fork 的会话侧 | 8、11 | `compact`、`shell`、`interrupt`、`wait` |
| `store.ts`（256 行） | SQLite 读写：消息、上下文、claim/release | 11、14 | `context`、`claim`、`release` |
| `projector.ts` | 事件 → SQLite 投影；压缩完成推进 epoch | 11、4 | `projectCompaction`、`advanceEpoch` 调用（L731-736） |
| `sql.ts` | drizzle 表定义（`SessionMessageTable`、`InstructionStateTable`、`InstructionBlobTable`） | 11 | 表结构 |
| `execution.ts`（195 行） | 进程内执行：write-ahead claim、drain、生命周期 | 11、14 | `claimOnCommit`、`releaseOnCommit`、`drain` |
| `usage.ts`（56 行） | usage → tokens/cost 记账（含分档计价） | 5、16 | `tokens`、`calculateCost`、`record` |
| `affinity.ts` | 缓存亲和 id | 13 | `get`（L7-8） |
| `provider-context.ts` | 原生压缩窗口的编码、provenance、可重放校验 | 8、11 | `encode`、`decode`、`provenance`、`compatible`、`isCheckpoint` |
| `prompt.ts`（231 行） | 用户输入准入：附件物化、技能物化 | 3 | `prepare` |
| `inbox.ts` | 控制项队列（`compaction` / `move` / prompt） | 8、11 | `admitCompaction`、`nextPromotable`、`promote` |
| `subagent-job.ts` / `subagent-completion.ts` | 子代理作业与完成通知 | 10 | `start`、`background`、`notify` |
| `system-prompt.ts`（28 行） | 基础提示词渲染（按工具名注入 guidance） | 1 | `make`、`render` |
| `schema.ts` / `event.ts` / `error.ts` | 会话 id、事件、错误类型 | 11、14 | — |

### `session/runner/`

| 文件 | 职责 | 16 类 | 关键函数 |
|---|---|---|---|
| `llm.ts`（408 行） | 主循环：`drain` / `advanceToStep` / `runStep`；自动压缩调度；输出上限续跑；遗留结算 | 1、8、14 | `drain`、`advanceToStep`、`prepareContext`、`runStep`、`settleStaleCompactions`、`settleStaleToolCalls` |
| `step.ts`（321 行） | 单步流：工具执行 + 截断、溢出分类、中断结算 | 6、14 | `attempt`、`classifyToolExits`、`isInterruptedStream` |
| `retry.ts`（115 行） | 有界重试策略与钩子 | 14 | `schedule`、`policy`、`make` |
| `to-llm-message.ts` | 投影消息 → LLM 消息；checkpoint 渲染 | 1、11 | `toLLMMessages`、checkpoint 分支（L303-325） |
| `max-steps.ts` | `MAX_STEPS_PROMPT` | 1 | 常量 |
| `model.ts` | 模型解析（含小模型/变体） | 1、5 | `resolve` |
| `publish-llm-event.ts` | LLM 事件 → 会话消息 | 11、16 | `createLLMEventPublisher` |

---

## 2. `packages/core/src/` 其他目录

| 路径 | 职责 | 16 类 | 关键点 |
|---|---|---|---|
| `tool-output.ts`（150 行） | 工具输出限长、落盘、清理 | 6 | `truncate`（L67-118）、`MAX_LINES`、`MAX_BYTES`、`RETENTION` |
| `tool/plugin/read.ts`（211 行） | `read` 工具：分页、就近规则触发 | 3、9 | `execute`、就近发现（L87-107） |
| `tool/read-filesystem.ts`（402 行） | 读取实现与上限 | 6、9 | `MAX_READ_LINES`、`MAX_READ_BYTES`、`MAX_MEDIA_INGEST_BYTES`、`MAX_LINE_LENGTH` |
| `tool/plugin/subagent.ts`（311 行） | `subagent` 工具 | 10 | `execute`、深度限制（L117-133）、后台/完成（L200-256）、描述注入（L282-309） |
| `tool/plugin/shell.ts` | `shell` 工具；后台作业与完成通知 | 6、4 | `prepare`、`notifyWhenDone`（L157-185） |
| `tool/mcp.ts`（152 行） | MCP 工具注册 | 3 | `initial`（L36-47） |
| `tool/plugin/{edit,write,grep,glob,skill,webfetch,websearch}.ts` | 各工具实现 | 3、6 | — |
| `codemode/{catalog,instructions,tool}.ts` | Code Mode：工具目录 + `execute` + `search` | 3 | `render`、`update` |
| `skill/instructions.ts`（96 行） | 技能清单渲染与差分 | 3 | `render`、`update` |
| `skill.ts` | 技能发现与正文准备 | 3 | `prepare`、`get` |
| `instructions/index.ts`（256 行） | 指令源抽象：`make` / `combine` / `diff` / `renderInitial` / `renderUpdate` | 2、4 | 同名函数 |
| `instruction-discovery.ts`（149 行） | `AGENTS.md` 指令源：初始渲染 + 增删改差分 | 2 | `render`、`renderUpdate`、`load` |
| `config/normalize.ts` | 配置迁移与诊断（压缩字段改名集中在这里） | 5、8 | `normalizeCompaction`（L323-379）、`unsupportedTopLevel`（L45） |
| `config/plugin/{compaction,instruction,tool-output}.ts` | 把配置写进各服务的 state | 5、6、8 | `editor.configure`、`discovery.add` |
| `plugin/agent.ts` | 内置 agent 定义（含 `compaction`） | 8、10 | L120-124 |
| `plugin/optimize.ts` | 按模型注入专属系统提示词 | 1、15 | `session.context` / `compaction` 钩子 |
| `plugin/internal.ts` | 内置插件注册表 | 15 | 插件清单 |
| `database/` | SQLite 驱动（bun/node/workerd）、v1 数据迁移 | 11 | `sqlite.bun.ts` 等 |
| `mcp/` | MCP 客户端、instructions 拉取 | 3 | `instructions`、`tools`、`callTool` |
| `permission.ts` | 权限裁决（工具、路径、subagent） | 1、10 | `assert`、`evaluate`、`merge` |

---

## 3. 其余包

| 路径 | 职责 | 16 类 | 关键点 |
|---|---|---|---|
| `packages/ai/src/cache-policy.ts` | 缓存断点放置策略 | 13 | `AUTO`（L17-21）、`BREAKPOINT_CAP = 4`、`gatewayPolicy`（L62-68） |
| `packages/ai/src/`（schema/route/协议） | 请求编译、provider 协议、`llm.compact` | 1、8 | `LLM.request`、`LLMClient.canCompact`、`llm.compact` |
| `packages/plugin/src/effect/session.ts`（172 行） | `SessionHooks` 类型 | 15 | L138-151 |
| `packages/plugin/src/effect/tool.ts` | 工具钩子 | 15 | `execute.before/after` |
| `packages/schema/src/session-message.ts`（322 行） | 消息与检查点 schema | 11 | `Compaction{...}`（L239-282）、`Info` 联合（L297-322） |
| `packages/schema/src/config/compaction.ts` | 压缩配置 schema | 8 | `auto / keep.tokens / buffer`（L4-13） |
| `packages/schema/src/config/experimental.ts` | `subagent_depth` 等实验项 | 10 | L11 |
| `packages/cli/src/commands/commands.ts` | `--continue` / `--session` / `--fork` | 11 | L345-370、L388-400 |
| `packages/cli/src/acp/turn.ts` | ACP 触发 compact | 8 | L240 |
| `packages/app/src/session/commands/use-session-commands.tsx` | 斜杠 `/compact` | 8 | L349-354 |

---

## 4. 一次压缩的调用链（跨文件）

```text
手动 /compact
  app 斜杠命令 ──► data.session.compact ──► Session.compact      [session/session.ts:246-264]
                    └─ inbox.admitCompaction(delivery "steer")
  runner.advanceToStep 消费 inbox "compaction"                   [runner/llm.ts:115-163]
                    └─ context.select → resolveModel → History.preview
                    └─ compaction.compact({reason:"manual"})

自动
  runner.runStep 开头 ──► compaction.compact({reason:"auto"})     [runner/llm.ts:220-225]
     └─ !settings.auto → skipped
     └─ !due(context, ceiling) → skipped                          [compaction.ts:242-251]

溢出
  step.attempt 捕获 context-overflow 且未产出 ──► recoverOverflow [step.ts:155-167]
     └─ compaction.compact({reason:"overflow"})                   [runner/llm.ts:265-271]
        └─ budget = min(cap, estimate×0.7)                        [compaction.ts:226-228]

压缩内部
  compact ──► native ? compactNatively : summarize                [compaction.ts:231-233]
  summarize:
    splitConversation(messages, keep)                             [compaction.ts:278]
    buildPrompt(hasPrevious, legacy) + 模板校验 + 一次 NUDGE       [compaction.ts:281-306]
    deliver(target): 估算 → flattenAndDropOldest → 0.7/0.5/0.35   [compaction.ts:384-455]
  publish Compaction.Ended                                        [compaction.ts:643-657]
    └─ projector: 写消息 + advanceEpoch                           [projector.ts:731-736]

重建
  context.load → History.entriesForRunner（seq 边界 + initial）    [context.ts:163-179]
    └─ baseTranscript: [agent.system ?? 基础提示词, initial]       [model-request.ts:100-120]
```

---

## 5. 源码解读候选（4 个）

1. **`compaction.compact` 的三入口与 `due` 判定**（`session/compaction.ts#L205-L251`）
   理由：一屏讲清 auto/overflow/manual 的预算差异与"锚点晚于 checkpoint"这条不变量；是 v2 相对 v1 最实质的触发逻辑升级。

2. **`deliver` 的四级收缩阶梯**（`session/compaction.ts#L384-L504`）
   理由：把"估算不可靠"这件事工程化：先文本化、再按 70/50/35 收缩、最后失败；同时展示 `[N older exchanges omitted]` 的取舍。

3. **指令 epoch：`observe` → `commit` → `advanceEpoch`**（`session/instruction-state.ts#L21-L154` + `projector.ts#L731-L736`）
   理由：v2 独有的"版本号"机制，能讲透"为什么压缩后基线可以一次性覆盖旧增量"，以及 fork 为什么要继承最新基线。

4. **`context.load` + `History.entriesForRunner` 的 seq 边界**（`session/context.ts#L163-L179`、`session/history.ts#L78-L135`）
   理由：解释"磁盘保留原文、模型只看最近一次完成压缩之后"的实现，和 v1 的 `tail_start_id` 重排形成清晰对照。

---

## 6. 不在本图范围

- `packages/app`、`packages/tui`、`packages/desktop` 的界面层（除命令与通知落点）。
- `packages/console`、`packages/stats`、`packages/simulation` 等运营/仿真包。
- `packages/core/src/v1/*` 的迁移行为（属 v1，见 `research/opencode-v1.md`）。
