---
title: OpenCode v2 · 证据卡
task: T10
role: 工具研究 Agent
created: 2026-10-15
snapshot: 042d0832f5f3a73eaa039a58a7d565776f6d4290   # tag v2.0.29（beta，只读）
spec: 08-验收/T07-后六工具样本规范.md §2
---

# OpenCode v2 · 证据卡

> 结论ID 前缀 `ocv2-*`。字段依规范 §2（**含"不能证明"必填**）。链接基址 `https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/`。
> **beta 标注（全程）**：本包研究对象 = 同仓库 tag `v2.0.29`（**beta**）；叙事为"同一工具的版本代际差异"，非第二个工具（版本表 Q1/Q2）。
> **v1/v2 分界**：v2 出货主体 = `packages/core/src/session/*`（服务标签 `@opencode/*`）、`packages/cli/*`、`packages/ai/*`、`packages/plugin/*`、`packages/schema/*`。**不得**用 v1 证据填 v2 空白；反向亦然（v1 侧只引 T09 已交付结论）。
> **计数**：本文件共 **29** 张卡（见文末计数核对）。

---

## 一、身份与版本

### ocv2-version-01
- **结论**：OpenCode v2 的研究快照为 tag `v2.0.29`（beta）、SHA `042d0832f5f3a73eaa039a58a7d565776f6d4290`；根 `package.json` 与 `packages/cli/package.json` 的 `version` 均为 `2.0.29`；CLI 包名为 **`@opencode/cli`**（非 v1 的 `opencode-ai`）；运行时为 **Node**（根 `packageManager: bun@1.4.2`，但版本表登记 v2 为 Node 运行时）。
- **性质**：事实
- **范围**：仓库 `github.com/anomalyco/opencode` tag v2.0.29（beta）
- **实现状态**：默认（身份口径）
- **来源**：`00-管理/版本表.md` §1 第 6 行 / §2；`git rev-parse HEAD`=`042d083…`、`git describe --tags`=`v2.0.29`；根 `package.json:version="2.0.29"`；`packages/cli/package.json:name="@opencode/cli"`
- **数据走查**：—
- **运行证据**：NOT_RUN（**本机 `opencode --version` = `1.19.0`（= v1），非 v2**；无 v2 可执行入口，见 `过程观察.md` §2）
- **不能证明**：**不能**证明本地存在与快照一致的 v2 可执行；**不能**证明 beta tag 与后续 stable 的差异；本包**未**在本地跑任何 v2 端到端机制
- **冲突裁决**：支持版本表 Q1/Q2（v2=`v2.0.29` beta，接受参与对比并全程标注 beta）
- **核验日期**：2026-10-15

### ocv2-version-02
- **结论**：v2 出货主体与 v1 出货路径**不同**——v2 会话/压缩/请求装配位于 `packages/core/src/session/*`（服务标签 `@opencode/SessionCompaction`、`@opencode/SessionModelRequest`、`@opencode/SessionRunner` 等），入口在 `packages/cli`；v1 的 `packages/opencode` 包在 v2 快照中**不存在**；v2 快照仍保留一份 `packages/core/src/v1/*`（v1 命名空间，**仅 `config/` 目录**，9 文件：`agent/command/error/mcp/migrate/permission/plugin/provider/provider-options`）。
- **性质**：事实
- **范围**：快照 `042d083`（tag v2.0.29）
- **实现状态**：默认（边界事实）
- **来源**：`packages/core/src/session/compaction.ts:69`（`@opencode/SessionCompaction`）；`packages/core/src/session/model-request.ts:228`（`@opencode/SessionModelRequest`）；`packages/core/src/session/runner/index.ts:42`（`@opencode/SessionRunner`）；`packages/` 下无 `opencode` 目录；`packages/core/src/v1/config/`（v1 命名空间配置子集）
- **数据走查**：—
- **运行证据**：NOT_RUN（静态目录检索）
- **分界方法（依 T09R 提醒，2026-10-15）**：**不得按目录或服务标签后缀二分**。本快照 `packages/core/src/session/*` 的服务标签统一为 **`@opencode/<Name>`**（17 个：SessionStore/SessionExecution/SessionContext/SessionCompaction/SessionModelRequest/SessionRunner/…），**仅 `packages/core/src/formatter.ts:25` 残留 `@opencode/v2/Formatter`**（**旧命名遗留、非分界标志**）——故 `/v2/` 后缀在 **v2 快照**里**不是** v1/v2 分界标志，分界判据是"**该包是否出货**"（v2 快照无 `packages/opencode`）。**交叉参考**：T09R 复核发现 **v1 快照（`733b2c6`）的 `packages/core/src/session/*` 是混合目录**（`execution.ts`/`store.ts`/`session.ts` 带 `@opencode/v2/*` 标签，`compaction.ts`/`projector.ts`/`sql.ts`/`message.ts` 无标签且被 v1 使用），且 v1 出货代码**确引用**了 v2 命名空间内容（`MAX_STEPS_PROMPT`、`SessionExecution`、`SessionV2.node`）——**这属 v1 侧结论，不改变本卡对 v2 快照的判定**；引用时**不得**据 v1 快照的"零命中/混合"表述反推 v2。
- **独立复核**：上述 v2 侧三条（无 `packages/opencode`；`session/*` 标签 17 命中含 `/v2/` 者 0；`@opencode/v2/` 全包仅 `formatter.ts:25` 1 命中）已由 **T09R 独立只读复核一致**（`08-验收/T09R-审查报告.md` §3 P2 佐证）——引用口径："v2 侧（T10 核 + T09R 独立复核，快照 `042d083`）"。
- **不能证明**：**不能**据此推断 v1 与 v2 的完整差异（v1 侧须以 T09/T09R 为准）；`packages/core/src/v1/*` 的存在**不代表** v2 默认走 v1 路径（迁移兼容层）；**不能**说 v2"用了 v1 代码"
- **冲突裁决**：确立本包 **v2 侧独立证据纪律**——v2 结论只引 `packages/core/src/session/*` 等 v2 出货路径；对照章节的 v1 侧**只**引 T09 已交付证据
- **核验日期**：2026-10-15

---

## 二、CM-01 请求组装与角色

### ocv2-assembly-01
- **结论**：v2 每次模型请求的 `system` 由 **2 条 `SystemPart`** 构成——`[ agent.system ?? SessionSystemPrompt.make(工具名列表), initial ]`；其中 `initial` = **指令基线（instruction epoch baseline）**的渲染文本（由 `InstructionState.initial` 生成，见 `ocv2-rule-02`）；`messages = toLLMMessages(投影消息)`。**v1 的"env/instructions/mcp/skills 四类块"在 v2 被折叠进 `initial` 与指令增量**，不再是独立的 system 数组项。
- **性质**：事实
- **范围**：v2 出货；`packages/core/src/session/model-request.ts`、`runner/llm.ts`
- **实现状态**：默认
- **来源**：`session/model-request.ts:100-120`（`baseTranscript`：`system=[agent.system ?? SessionSystemPrompt.make(...), input.initial].filter(len>0).map(SystemPart.make)`）；`session/runner/llm.ts:227-247`（`baseTranscript` 调用 + `context.request.primary`）；`session/system-prompt.ts:5-28`（`make`/`render`，注入 `${OPENCODE_TOOL_GUIDANCE}`）；`session/runner/prompt/system.txt:1-16`（基础提示词）
- **数据走查**：DW-assembly-01
- **运行证据**：NOT_RUN（需真实 provider）
- **不能证明**：**不能**证明各 provider 服务端如何渲染 system（服务端 `UNOBSERVABLE`）；**不能**证明模型对"基础提示词 + 指令基线"两块的实际注意力
- **冲突裁决**：支持 T02 §E"请求组装"统一语义；澄清 v2 **无** `developer` 角色（system 走 system role）；v1 的"四类 system 块"表述**不适用于 v2**（须按代际分列）
- **核验日期**：2026-10-15

### ocv2-assembly-02
- **结论**：v2 主循环 `SessionRunner.drain` → `runStep` 每步**重新** `context.load` 投影历史并重建请求（非增量拼接）；`agent.info.steps`（可选）限制步数，**末步把 `MAX_STEPS_PROMPT` 作为一条 `assistant` 消息追加**并设 `toolChoice:"none"`（工具禁用）；工具按 `Object.entries` 顺序入请求（v1 为按名排序）。
- **性质**：事实
- **范围**：v2 出货；`session/runner/llm.ts`、`session/runner/max-steps.ts`
- **实现状态**：默认
- **来源**：`session/runner/llm.ts:57-199`（`drain`/`advanceToStep`）、`:209-330`（`runStep`）、`:226`（`stepLimitReached`）、`:240-244`（末步 `Message.assistant(MAX_STEPS_PROMPT)` + `toolChoice:"none"`）；`session/runner/max-steps.ts:1-16`（`MAX_STEPS_PROMPT`）；`schema/src/agent.ts:33`（`steps: PositiveInt.optional`）；`session/model-request.ts:298`（`tools: Array.from(hooked, ...)`）
- **数据走查**：DW-assembly-01
- **运行证据**：NOT_RUN（需真实 provider）
- **不能证明**：**不能**证明真实会话中步数上限与退出时机的端到端表现（未跑）；**不能**证明 `toolChoice:"none"` 在各 provider 的实际约束力
- **冲突裁决**：与 `ocv2-assembly-01` 同族；支持"每次请求是重算"的统一视角（LQ-01）；**与 v1 差异**：v1 末步提示进 messages 数组尾部，v2 作为 assistant 消息 + 禁工具
- **核验日期**：2026-10-15

---

## 三、CM-02 项目规则 / 技能加载

### ocv2-rule-01
- **结论**：v2 项目规则（`AGENTS.md` 类）与技能、MCP、参考资料、代码模式目录、内置指令统一抽象为**有序 `Instructions.List`（指令源）**；`SessionContext.select` 按"**最共享 → 最不共享**"排序合成——`CodeModeInstructions → mcp → references → skills → discovery → builtins → entries`（注释明说这是为保持可复用的 **prompt-cache 前缀**）；每个源实现 `initial/changed/removed` 三种渲染（差分更新）。
- **性质**：事实
- **范围**：v2 出货；`session/context.ts`、`instructions/index.ts`
- **实现状态**：默认（`InstructionDiscovery` 的 `project`/`global` 可关，`instruction-discovery.ts:99-100`）
- **来源**：`session/context.ts:144-160`（`Instructions.combine([...])` 顺序与注释）；`instructions/index.ts:33-39`（`Source` 接口）、`:88-122`（`make`）、`:124-132`（`combine`）、`:161-192`（`renderInitial`/`renderUpdate`）；`instruction-discovery.ts:123-149`（`render`/`renderUpdate`：增删改 + diff 补丁）
- **数据走查**：DW-rule-01
- **运行证据**：NOT_RUN（需真实目录）
- **不能证明**：**不能**证明"最共享 → 最不共享"顺序在真实 provider 下的缓存收益（服务端 `UNOBSERVABLE`）；**不能**证明多源差分更新在真实编辑节奏下的实际 token 节省
- **冲突裁决**：支持术语"项目规则 / 技能（渐进式披露）/ 差分更新"；v1 是"全局首个 + 项目 `findUp` 首个"的**文件发现**口径，v2 是"**指令源 + 基线 + 增量**"口径——**机制形态变化**（非名称差异）
- **核验日期**：2026-10-15

### ocv2-rule-02
- **结论**：v2 指令有**纪元基线（epoch baseline）+ 增量更新**两态——`InstructionState.initial` 渲染 `initial_values`（每次请求开头的基线，`ocv2-assembly-01` 的 `initial`）；指令变化时经 `InstructionState.commit` 发 `InstructionsUpdated` 事件（增量 `delta` + 渲染文本，文本**冻结进持久事件**）；native checkpoint 完成可推进纪元（`advanceEpoch`）。读取时**沿目录向上**发现的就近 `AGENTS.md` 以 `Synthetic` 消息注入（去重台账在 synthetic 元数据里；synthetic 掉出模型可见历史会被**重新发现重注入**）。
- **性质**：事实
- **范围**：v2 出货；`session/instruction-state.ts`、`session/instructions.ts`
- **实现状态**：默认
- **来源**：`session/instruction-state.ts:38-61`（`commit`：`InstructionsUpdated` + 冻结文本）、`:63-78`（`renderUpdateText`）、`:119-154`（`initialize`/`advanceEpoch`）、`:164-174`（`initial`）；`session/instructions.ts:46-93`（`load`：claim + `previouslyInjected` 去重 + `Synthetic` 发布）、`:99-112`（`previouslyInjected` 扫 synthetic 台账）；`session/history.ts:127-131`（`entriesForRunner` 取 `initial`）
- **数据走查**：DW-rule-01
- **运行证据**：NOT_RUN（需真实目录 + 会话）
- **不能证明**：**不能**证明增量更新在真实多文件编辑下"每消息只发一次"（未跑）；**不能**证明 synthetic 掉出历史后"重注入"在真实压缩/回退序列中的正确性
- **冲突裁决**：v1 的"就近规则附到工具结果（每消息一次）"（`ocv1-rule-01`）在 v2 变为"**synthetic 消息 + 台账去重 + 可重注入**"——**机制形态变化**；两者都支持"发现范围"术语
- **核验日期**：2026-10-15

### ocv2-skill-01
- **结论**：v2 技能走**渐进式披露**——技能清单（`id/name/description`，按 id 排序）渲染为 `<available_skills>` 块进指令基线；正文由 `skill` 工具按需读；技能变化时差分更新（增/删/改：改则整表重述，增删渲染小增量）；`autoinvoke===false` 或无 description 的技能**不进**清单。
- **性质**：事实
- **范围**：v2 出货；`skill/instructions.ts`
- **实现状态**：默认（权限可 deny）
- **来源**：`skill/instructions.ts:16-33`（`entries`/`render`：`<available_skills>`）、`:35-58`（`update`：diff 渲染）、`:73-91`（`load`：过滤 `autoinvoke===false`、按 id 排序）；`tool/plugin/skill.ts`（`skill` 工具）
- **数据走查**：DW-skill-01
- **运行证据**：NOT_RUN（需真实技能目录）
- **不能证明**：**不能**证明技能正文加载后的实际 token 收益（未测）；**不能**证明差分更新在多技能频繁变化下的表现
- **冲突裁决**：与 v1（`ocv1-skill-01`：系统只列 name/description/location，`skill` 工具按需读）**语义一致**；差异在载体（v1 系统块 vs v2 指令源 + 增量）与字段（v2 用 `id`，v1 用 `location`）
- **核验日期**：2026-10-15

---

## 四、CM-03 资料选择与代码检索

### ocv2-retrieval-01
- **结论**：v2 `read` 工具支持 `offset/limit` 分页；`limit` 默认且**上限 2000 行**、单行 **2000 字符**截断（附 `... (line truncated to 2000 chars)`）、单页字节上限 **50 KiB**；目录读取亦分页（`list-page`）；媒体（image/pdf）走 base64 直读，> **20 MiB** 拒读（`MediaIngestLimitError`）。
- **性质**：事实
- **范围**：v2 出货；`tool/plugin/read.ts`、`tool/read-filesystem.ts`
- **实现状态**：默认
- **来源**：`tool/read-filesystem.ts:14-21`（`MAX_READ_LINES=2000`、`MAX_READ_BYTES=50*1024`、`MAX_LINE_LENGTH=2000`、`MAX_MEDIA_INGEST_BYTES=20*1024*1024`）、`:177`（`Math.min(page.limit || MAX_READ_LINES, MAX_READ_LINES)`）、`:304-316`（字节预算截断）、`:326-327`（`clampLine`）；`tool/plugin/read.ts:17-25`（`limit` "defaults to and capped at 2000"）、`:187-197`（目录/续读提示）
- **数据走查**：DW-retrieval-01
- **运行证据**：NOT_RUN（需真实文件）
- **不能证明**：**不能**证明真实任务中模型是否"按需"而非"全量装填"（属行为，需 T19）；**不能**证明 v2 是否还有 v1 之外的检索工具（`grep/glob` 工具在 `tool/plugin/` 中存在但本包未逐行读）
- **冲突裁决**：支持术语"按需读入 / 代码检索"；v1（`ocv1-retrieval-01`：2000 行/单行 2000 字符/50 KiB）与 v2 数值**相同**——**未变**
- **核验日期**：2026-10-15

---

## 五、CM-04 单条工具输出治理

### ocv2-trunc-01
- **结论**：v2 工具输出经 `ToolOutput.truncate` 统一限长：**2000 行 / 51200 字节（50 KiB）先到者**；超限**原文落盘**到 `global.data/tool-output/` 目录（文件名 `tool_<12位hex>`），返回"保留行 + 标记 `[showing lines 1-N of M; full output saved to <file>]`"；落盘文件**保留 7 天**（每小时清理）；上限可由 `ToolOutput.configure({maxLines,maxBytes})` 覆盖。**注意：v2 为 head-only（无 `direction` 参数）**。
- **性质**：事实
- **范围**：v2 出货；`tool-output.ts`
- **实现状态**：默认
- **来源**：`tool-output.ts:13-18`（`MAX_LINES=2_000`、`MAX_BYTES=50*1024`、`RETENTION=Duration.days(7)`、`DIRECTORY="tool-output"`、`fileName="tool_"+hex`）、`:56-65`（默认 `{maxLines,maxBytes}`）、`:67-118`（`truncate`：先到者 + 落盘 + 标记）、`:38-48`（`cleanup`）、`:129-138`（每小时清理）；调用点 `session/runner/step.ts:127`（`Effect.flatMap(toolOutput.truncate)`）
- **数据走查**：DW-trunc-01（含边界）
- **运行证据**：NOT_RUN（产品端到端；函数级判据见 `过程观察.md` §1 同法可扩展，未跑）
- **不能证明**：**不能**证明落盘文件在真实会话中确实被模型通过 `read/grep` 取回（未跑）；**不能**证明混合 CJK/ASCII 下"先到者"的具体分布；**不能**证明 `tool-output` 目录在真实运行中的绝对路径（未跑）
- **冲突裁决**：与 v1（`ocv1-trunc-01`：2000 行/51200 字节/落盘 7 天）**行/字节/保留期相同**；**差异**：v1 有 `head/tail` 双向（`bash` 等用 tail），v2 **仅 head**；落盘目录名 v2 明确为 `tool-output`（v1 侧未证目录名）

> 【T19 实测更正（2026-10-15）】产品 shell 路径实测为**纯 tail**（与 v1 同向）；「仅 head（无 tail）」**不成立于 shell 路径**；落盘实为 `shell/<hash>/sh_<id>.out`。原函数级观察（`tool-output.ts` 头向通用通道）保留——head 仅在 read 分页与通用默认（证据：`05-实验/T19/记录/08-ocv2.md` §五/§2.7；`T19-结果总表.md` §5 #14）。
- **核验日期**：2026-10-15

### ocv2-trunc-02
- **结论**：v2 压缩序列化时对工具结果**再按 1250 字符**限长（`TOOL_OUTPUT_MAX_CHARS=1_250`，追加 `\n[truncated]`）；截断**按 Unicode 码点**计（不切断代理对），非字节/token。
- **性质**：事实
- **范围**：v2 出货；`session/compaction.ts`
- **实现状态**：默认
- **来源**：`session/compaction.ts:100`（`TOOL_OUTPUT_MAX_CHARS = 1_250`）、`:807-820`（`truncateToolOutput`：`for (const char of value)` 码点安全 + `\n[truncated]`）；用于 `messageToText`（`:785`）与 `flattenMessage`（`:840`）
- **数据走查**：DW-trunc-02
- **运行证据**：NOT_RUN
- **不能证明**：**不能**证明 1250 **字符**在 CJK 下的实际压缩率；**不能**证明该限长对摘要保真度的影响（需 T19）
- **冲突裁决**：**与 v1 差异**：v1 为 **2000 字符**（`ocv1-trunc-02`），v2 收紧为 **1250 字符**；v1 用 `truncate()` 无码点保护，v2 明确码点安全。v1 有 `prune` 擦除后占位串 `[Old tool result content cleared]`，**v2 未见 `prune`**（见 `ocv2-summary-03`）
- **核验日期**：2026-10-15

---

## 六、CM-05 窗口计量与触发

### ocv2-trigger-01
- **结论**：v2 触发上限 `ceiling = window − max(floor(window×0.1), window ≥ 2×RESERVE_MIN ? RESERVE_MIN : 0)`，其中 `window = limit.input || limit.context`，`RESERVE_MIN = 16_000`；配置 `compaction.buffer` 非空时 `ceiling = window − buffer`；窗口未知（≤0）→ `ceiling = +∞`（**永不自动触发**）。
- **性质**：事实
- **范围**：v2 出货；`session/compaction.ts`
- **实现状态**：默认（`compaction.buffer` 可覆盖）
- **来源**：`session/compaction.ts:905-912`（`calculateCeiling`）、`:97`（`RESERVE_MIN = 16_000`）、`:99`（`UNKNOWN_WINDOW = 200_000`）；配置 `schema/src/config/compaction.ts:10-14`（`auto`/`keep`/`buffer`）
- **数据走查**：DW-trigger-01（含算例）
- **运行证据**：NOT_RUN（需真实 provider 的 `model.limit`）
- **不能证明**：**不能**证明真实 provider 返回的 `limit.input`/`limit.context` 具体数值（来自 provider 元数据）；**不能**证明 `buffer` 默认值在真实模型的取舍
- **冲突裁决**：**与 v1 差异**：v1（`ocv1-trigger-01`）为**绝对预留** `reserved = min(20000, maxOutputTokens)`；v2 改为**比例口径** `max(10%W, 16000)`（窗口 ≥32000 时保 10%，小窗口保 16000 下限）——**阈值口径变化**；两者都非 Codex 式"范围线/整段线"两线结构
- **核验日期**：2026-10-15

### ocv2-trigger-02
- **结论**：v2 自动触发判定 `due`：① 若最后一条消息是"已完成压缩"（`type:"compaction" && status:"completed"`）→ **false**（等 runner 先用它重建请求）；② 若无"本 provider 已测量"的 assistant 提示（`hasMeasuredPrompt`：同 provider、无 error、`tokens.input+cache.read+cache.write > 0`）晚于最后一条 checkpoint → **false**；③ 否则 `estimateContext ≥ ceiling` 即到线。`estimateContext = measured + estimated`（`measured` 取最近一次 provider 回报的 input+cache+output+reasoning；`estimated` 为锚点之后的本地估算）。
- **性质**：事实
- **范围**：v2 出货；`session/compaction.ts`
- **实现状态**：默认（`auto` 默认 true）
- **来源**：`session/compaction.ts:242-251`（`due`）、`:868-898`（`estimateContext`/`estimatePrompt`）、`:918-923`（`hasMeasuredPrompt`）、`:195-197`（默认 `{auto:true, keep:15_000}`）、`:210-212`（`auto===false` 或未到线 → `skipped`）
- **数据走查**：DW-trigger-02
- **运行证据**：NOT_RUN
- **不能证明**：**不能**证明 `measured` 与四项相加在真实 provider 下是否一致（未跑）；**不能**证明"到线"与真实压缩时机的对应（需 T19）
- **冲突裁决**：支持术语"触发线（伞名）"在 v2 侧**退化为单一上限线**（`ceiling`）；限制"90%–95% 总括"（C-01/C-02）——v2 为 10%/16000 混合口径，非 90–95%
- **核验日期**：2026-10-15

---

## 七、CM-06 自动 / 手动压缩

### ocv2-compact-01
- **结论**：v2 自动压缩在 `runStep` 每次迭代**开头**调用 `compaction.compact({reason:"auto", context})`；仅 `auto` 且 `due` 为真才执行；完成后 `runStep` **重建 assistantMessageID 并 continue**（下一轮用压缩条目重建请求）。压缩成功后发 `Compaction.Started`/`Compaction.Ended`（含 text/recent/usage）；失败发 `Compaction.Failed`。
- **性质**：事实
- **范围**：v2 出货；`session/runner/llm.ts`、`session/compaction.ts`
- **实现状态**：默认（`auto=true`）
- **来源**：`session/runner/llm.ts:220-225`（auto compact → continue）；`session/compaction.ts:205-212`（`compact` 分发：非 manual 且 `!auto` → skipped；`auto` 且 `!due` → skipped）、`:384-395`（`deliver` 发 `Compaction.Started`）、`:623-658`（`publish`：Ended/Failed）
- **数据走查**：DW-compact-01
- **运行证据**：NOT_RUN（需真实 provider 触发到线）
- **不能证明**：**不能**证明真实会话中压缩触发频率/时机（需 T19）；**不能**证明 `due` 的"测量锚点"逻辑在长会话中的稳定性
- **冲突裁决**：支持 CM-06"自动压缩"有实现；**与 v1 差异**：v1 有两处自动入口（主循环轮后 + 处理器 `step-finish` 溢出），v2 统一为"每步开头 `runStep` 判 `due`"一处 + overflow 恢复（`ocv2-compact-03`）——**入口数不同**（不按入口数比成熟度）
- **核验日期**：2026-10-15

### ocv2-compact-02
- **结论**：v2 手动压缩入口 = `/compact`——TUI/ACP 斜杠命令（`packages/cli/src/acp/catalog.ts:10` `["compact",{description:"Compact the session"}]`）产生 **inbox 项 `type:"compaction"`**；`SessionRunner.drain` 在步边界消费它，发 `InboxDelivered` + `Compaction.Started{reason:"manual"}`，随后 `compaction.compact({reason:"manual", inputID})`；**手动压缩的结算通过该 `/compact` inbox 项**（`compact` 的 `onInterrupt` 对 manual 不另发 interrupted）。
- **性质**：事实
- **范围**：v2 出货；`packages/cli/src/acp/catalog.ts`、`session/runner/llm.ts`、`session/compaction.ts`
- **实现状态**：默认（inbox 控制项）
- **来源**：`packages/cli/src/acp/catalog.ts:10`（`compact` 命令）；`session/runner/llm.ts:91-95`（`next.type==="compaction"` → `InboxDelivered` + `Compaction.Started{reason:"manual"}`）、`:115-163`（消费 → `compaction.compact({reason:"manual", inputID})`）；`session/compaction.ts:53-57`（`Trigger.manual` 带 `inputID`）、`:663-672`（manual 的 `onInterrupt` 为 void）；`session.ts:212-214,439`（`compact` API）
- **数据走查**：DW-compact-02
- **运行证据**：NOT_RUN（需真实 server + provider）
- **不能证明**：**不能**证明 `/compact` 端到端效果与自动压缩的差异（需 T19）；**不能**证明 v1 的 `/compact`（HTTP `summarize`）与 v2 的 inbox 路径**行为等价**（v2 侧只证到 inbox 机制）
- **冲突裁决**：术语"手动压缩"在 v2 侧**有实现**且命令名同为 `/compact`；**与 v1 差异**：v1 手动入口是 HTTP `POST /session/:id/summarize`（`ocv1-compact-02`），v2 是 **inbox `compaction` 控制项 + 步边界消费**——**传输路径变化**
- **核验日期**：2026-10-15

### ocv2-compact-03
- **结论**：v2 有**溢出恢复压缩**——`SessionStep.attempt` 在"provider 报 context-overflow 且尚未开始输出"时返回 `Outcome.Compacted`，`runStep` 以 `recoverOverflow` 调 `compaction.compact({reason:"overflow"})`；`overflow` 触发的首次预算按 `estimateContext × SHRINK_STEPS[0]`（0.7）收缩（因估计偏低已被证伪）；`recoverOverflow` 每步只允许一次（`Compacted` 后置 false）。
- **性质**：事实
- **范围**：v2 出货；`session/runner/step.ts`、`session/runner/llm.ts`、`session/compaction.ts`
- **实现状态**：默认
- **来源**：`session/runner/step.ts:113-120`（记录 `overflowFailure`）、`:155-167`（`recoverOverflow` 成功 → `Outcome.Compacted`）；`session/runner/llm.ts:265-271`（`recoverOverflow` → `compact({reason:"overflow"})`）、`:320-323`（`Compacted` → `recoverOverflow=false`）；`session/compaction.ts:226-228`（overflow 首预算 = `min(cap, floor(estimateContext × 0.7))`）、`:94-95`（`SHRINK_STEPS=[0.7,0.5,0.35]`）
- **数据走查**：DW-compact-03
- **运行证据**：NOT_RUN（需注入 provider overflow）
- **不能证明**：**不能**证明真实 provider 溢出后一次恢复是否足够（未跑）；**不能**证明 0.7/0.5/0.35 步进在真实模型的收敛性
- **冲突裁决**：**与 v1 差异**：v1 溢出经 `isOverflow`/`needsCompaction` 走"自动压缩"（`ocv1-compact-01`），v2 溢出是**独立的 `reason:"overflow"` 触发**且带**收缩步进**；两者都属 CM-06 自动路径，但**触发语义与预算策略不同**
- **核验日期**：2026-10-15

### ocv2-compact-04
- **结论**：v2 有**原生（provider）压缩**通道——`context.model.compaction?.type === "native"` 时走 `compactNatively`：不再让模型产文本摘要，而是请求 provider 返回**加密压缩项（replacement window）**；压缩条目存 `providerContext`（含 `provenance`：provider/modelID/route/protocol/endpoint 哈希），只在**同一 endpoint** 可重放；不满足稳定 endpoint 或 endpoint 不兼容 → `provider.unsupported-operation`。
- **性质**：事实
- **范围**：v2 出货；`session/compaction.ts`、`session/provider-context.ts`
- **实现状态**：条件（仅当模型元数据 `compaction.type === "native"`）
- **来源**：`session/compaction.ts:213-214`（`native` 判定）、`:324-372`（`compactNatively`）、`:354-368`（trigger/endpoint 两种 mechanism）、`:333-343`（provenance 兼容校验）；`session/provider-context.ts:17-45`（`provenance`/`compatible`/`isCheckpoint`）、`:51-58`（`encode`/`decode`）；`session/history.ts:23-26`（`replayable`）
- **数据走查**：DW-compact-04
- **运行证据**：NOT_RUN（需支持原生压缩的 provider，如 Anthropic/OpenAI 加密压缩）
- **不能证明**：**不能**证明哪些真实模型/endpoint 默认启用原生压缩（取决于模型元数据）；**不能**证明加密窗口的内容与保真度（本地不可解，`UNOBSERVABLE`）
- **冲突裁决**：**v1 未见原生压缩通道**（T09 包无对应卡）——v2 **新增机制**；`ocv1-summary-04` 的"替代历史 = 压缩条目 + 摘要 + 保留段"在 v2 原生路径下变为"**加密窗口 + 新增消息**"
- **核验日期**：2026-10-15

---

## 八、CM-07 摘要 / 裁剪 / 重建

### ocv2-summary-01
- **结论**：v2 摘要提示词用固定 `SUMMARY_TEMPLATE`（`Objective / Requirements / Decisions / Work State{Completed/Active/Blocked} / Next Move / Relevant Files / Important Context`）+ `SUMMARY_RULES`；`buildPrompt(update, legacy)` 无旧摘要时"新建"，有旧摘要时"**更新现有 checkpoint**"（明说"**新历史优先**于旧 checkpoint；除非新历史明确矛盾/取代/解决/过期，否则保留旧信息"）；`legacy` 时追加"旧格式重写"指令（旧模板用 `## Additional Context` 兜底标题，`LEGACY_HEADING`）。**摘要回复必须含模板标题**，否则**追加一条 `NUDGE` 重试一次**，再失败即 `compaction.failed`。
- **性质**：事实
- **范围**：v2 出货；`session/compaction.ts`
- **实现状态**：默认（可被 `session.compaction` 钩子整体替换，见 `ocv2-ext-01`）
- **来源**：`session/compaction.ts:104-143`（`SUMMARY_TEMPLATE`/`SUMMARY_RULES`）、`:145-176`（`buildPrompt`）、`:178-182`（`NUDGE`/`LEGACY_HEADING`）、`:282-306`（模板校验 + NUDGE 重试）、`:308-309`（`overhead = estimate(prompt)+estimate(NUDGE)`）
- **数据走查**：DW-summary-01
- **运行证据**：NOT_RUN（需真实模型生成摘要）
- **不能证明**：**不能**证明模板在真实模型下的遵守度（需 T19）；**不能**证明 NUDGE 重试的实际成功率
- **冲突裁决**：**判为有损**（增量合并明说"新历史优先、可移除不再相关项"）；支持 C-04"旧摘要非无损"；**与 v1 差异**：模板新增 `Requirements/Decisions/Important Context` 三节，v1 为 `Important Details`；增量规则从 v1 的"未带过来即丢失、冲突以新对话为准"变为"新历史优先、除非明确矛盾否则保留"；v2 **新增模板校验 + 一次 NUDGE**
- **核验日期**：2026-10-15

### ocv2-summary-02
- **结论**：v2 压缩保留预算 = `settings.keep`（**默认 15_000 token，固定值**，非随窗口浮动）；`splitConversation` 从最新往回按估算 token 累加，`recentStart` **在 user 消息边界切**（保证 assistant 的工具调用与结果同段）；保留段 `recent` 作为**文本**存入 checkpoint（`<recent-context>`），与摘要并列。配置 `compaction.keep.tokens` 可覆盖（v1 名 `preserve_recent_tokens` 迁移而来）。
- **性质**：事实
- **范围**：v2 出货；`session/compaction.ts`
- **实现状态**：默认
- **来源**：`session/compaction.ts:195-197`（默认 `{auto:true, keep:15_000}`）、`:702-714`（`splitConversation`）、`:716-738`（`recentStart`：user 边界）、`:740-750`（`oldestToDrop`）、`:853-866`（`recentUserMessages`）；配置 `config/normalize.ts:345-365`（`preserve_recent_tokens`→`keep.tokens`）、`config/plugin/compaction.ts:15-24`
- **数据走查**：DW-summary-02（含算例）
- **运行证据**：NOT_RUN
- **不能证明**：**不能**证明真实 provider 下"估算 token"（chars/4）与真实 token 的偏差对切点的影响（见 `OBS-ocv2-token-01` 的 CJK 口径限制）
- **冲突裁决**：**与 v1 差异**：v1 保留预算 = `usable×0.25` 夹 `[2000,15000]`（随窗口浮动，`ocv1-summary-02`），v2 为**固定 `keep=15000`**；v1 有 `tail_turns` 限制候选 turn 数，v2 **`tail_turns` 已标 unsupported**（`config/normalize.ts:333`）——**机制形态变化**
- **核验日期**：2026-10-15

### ocv2-summary-03
- **结论**：v2 **未发现 `prune`（压缩前擦旧工具输出）默认实现（推断）**——`compaction.prune` 与 `compaction.tail_turns` 在 v2 配置归一化中被显式标为 **`unsupportedIfPresent`（诊断报错）**；v2 侧改为"请求过大时把历史**文本化并丢弃最旧 exchange**"（`flattenAndDropOldest`：保留旧摘要在前、其 `recent` 变为最旧 transcript 项、按 exchange 整块丢弃、加 `[N older exchanges omitted]`；只在仍装不下时丢）。
- **性质**：事实（配置面）/ 推断（"无 prune 默认实现"）
- **范围**：v2 出货；`config/normalize.ts`、`session/compaction.ts`
- **实现状态**：v2 无 `prune` 开关（**推断**）；`flattenAndDropOldest` 为默认路径
- **来源**：`config/normalize.ts:333-334`（`unsupportedIfPresent(..., "tail_turns")` / `"prune"`，即 v2 显式标 unsupported）；`session/compaction.ts:457-504`（`flattenAndDropOldest`）、`:492-493`（`[N older exchanges omitted]`）；**复算（2026-10-15，依 T10R 复核更正）**：`grep -rn "prune" packages/core/src` = **6 命中**，其中**仅 `config/normalize.ts:334` 与 `compaction.prune` 相关**（即上句的 unsupported），其余 5 处为 `git.ts:121,297,299,1019,1023` 的 git prune（**与本机制无关**）；`packages/ai/src` = **0 命中**；旧文档 `web/src/content/docs/*/config.mdx` 仍写 `prune`/`reserved`
- **数据走查**：DW-summary-03（含边界）
- **运行证据**：NOT_RUN（静态检索；命令见 `过程观察.md` §3）
- **不能证明**：**"未发现"≠"没有"**——可能存在于插件生态或本包未覆盖路径；判定"能力不存在"须补"官方怎么说"，本包**未取得**官方"v2 移除 prune"声明，故**只标推断 + 配置面 unsupported**
- **冲突裁决**：**与 v1 差异显著**——v1 有 `prune`（默认关，保护 40000/最小节省 20000，`ocv1-summary-03`），v2 配置层明确 unsupported；**v2 的旧工具输出治理改为"文本化 + 丢 exchange"**；**文档与实现分叉**：v2 快照的 `web/.../config.mdx` 仍写 `prune`/`reserved`（v1 口径），与 v2 配置 schema 不符（FB-01 类：文档未同步）
- **核验日期**：2026-10-15

### ocv2-summary-04
- **结论**：v2 模型可见历史由 `SessionHistory.messageEntries` **按 boundary 重建**：先取**最近一条"已完成压缩"**（`latestCompaction`，SQL `type='compaction' && status='completed'`），再取 `seq ≥ compaction.seq` 的消息正序（**磁盘原始消息不删**）；文本压缩条目在转模型消息时变成一条 `user` 消息 `<conversation-checkpoint>…<summary>S</summary>…<recent-context>E</recent-context></conversation-checkpoint>`；native checkpoint 则 `decode` 回其加密窗口。boundary 分 `latest`/`local`/`Provenance` 三态（native 窗口只对"可重放"的 reader 生效）。
- **性质**：事实
- **范围**：v2 出货；`session/history.ts`、`session/runner/to-llm-message.ts`
- **实现状态**：默认
- **来源**：`session/history.ts:28-60`（`latestCompaction`）、`:78-108`（`messageEntries`：`gte(seq, compaction.seq)` + `replayable` 过滤）、`:16-26`（`Boundary`/`replayable`）；`session/runner/to-llm-message.ts:306-325`（`compaction` → `<conversation-checkpoint>`）
- **数据走查**：DW-summary-04
- **运行证据**：NOT_RUN
- **不能证明**：**不能**证明重排后模型对"摘要 + 保留段"的实际使用（需 T19）；**不能**证明多条压缩叠加时的重排正确性（未跑）
- **冲突裁决**：**支持 C-03"两事实并存"**（磁盘保留原文 + 模型可见层用替代历史）；**与 v1 差异**：v1 用 `filterCompacted` 把"压缩条目 + 摘要 + `tail_start_id` 保留段 + 后续"**重排**"（`ocv1-summary-04`），v2 改为"**取最近完成压缩起的连续段**"（无显式重排，`tail_start_id` 语义由 `recent` 文本 + seq 边界取代）——**重建机制变化**
- **核验日期**：2026-10-15

---

## 九、CM-08 长期记忆

### ocv2-memory-01
- **结论**：**未发现 v2 默认长期记忆实现（推断）**——v2 出货路径（`packages/core/src/session`、`packages/core/src/tool`、`packages/cli/src`）内**无 memory 模块**；`find ... -iname "*memory*"` 仅命中 `packages/core/src/environment/memory.ts`（**内存文件系统驱动**，非长期记忆）；检索 `longterm/long-term memory/session memory/background extraction` **零命中**。
- **性质**：推断（**非"没有"**）
- **范围**：v2 出货；快照 `042d083`
- **实现状态**：未证实（未见默认实现，也未见配置开关）
- **来源**：`find packages/core/src packages/cli/src -iname "*memory*"` → 仅 `environment/memory.ts`（`makeMemoryDriver` 内存 FS）；`grep -rlniE "longterm|long-term memory|session memory|background extraction" packages/core/src packages/cli/src` → 零命中（**用 `-E` 交替；并逐个模式复跑均为 0**，2026-10-15 更正可复现命令，命令见 `过程观察.md` §3）
- **数据走查**：DW-memory-01
- **运行证据**：NOT_RUN（静态检索；检索路径与命令已登记）
- **不能证明**：**"未发现"≠"没有"**——可能存在于插件生态、远端服务或本包未覆盖路径；本包**未取得**官方"v2 无长期记忆"声明，故**只标推断**
- **冲突裁决**：**未裁决**（不改旧结论）；与 v1（`ocv1-memory-01`：同样"未发现默认实现（推断）"）**一致**——CM-08 在 v1/v2 均为"未发现默认实现"；与 omp（有独立记忆五后端）形成对比点
- **核验日期**：2026-10-15

---

## 十、CM-09 子 Agent 交接

### ocv2-cm09-01
- **结论**：v2 内置 **`subagent` 工具**（v1 名为 `task`）：为指定子 agent **新建子会话**（"New child sessions start with fresh context"，即不继承父对话历史），可传 `sessionID` 续跑同一子会话；`experimental.subagent_depth` 默认 **1**（禁嵌套）；前台（默认）跑完返回，`background:true` 异步并通知；结果以 `<subagent sessionID="…" state="completed">…</subagent>` 文本回父；失败保留 sessionID 以便续跑；子会话的 job 可跨进程恢复（`SubagentJob` + `Job`）。
- **性质**：事实
- **范围**：v2 出货；`tool/plugin/subagent.ts`、`session/subagent-job.ts`
- **实现状态**：默认（前台）；后台为默认可用能力（非实验门控，与 v1 不同）
- **来源**：`tool/plugin/subagent.ts:17`（`name="subagent"`）、`:55-62`（`description`：fresh context / 续跑 / 前台/后台）、`:129-133`（`subagent_depth ?? 1` + 深度检查）、`:184-198`（`sessions.create({parentID})`）、`:257-266`（`<subagent>` 渲染）；`session/subagent-job.ts:44-69`（start/background/notify）；`session/subagent-completion.ts`（`deliver`/`text`/`NO_TEXT`）
- **数据走查**：DW-cm09-01
- **运行证据**：NOT_RUN（需真实 provider）
- **不能证明**：**不能**证明子会话"不继承父历史"的完整边界（本包读到 fresh context 文案 + 新建会话，未逐字段核对继承规则）；**不能**证明后台子代理的端到端行为（未跑）
- **冲突裁决**：CM-09 在 v2 **适用**（非"不适用"）；**与 v1 差异**：工具名 `task`→`subagent`；结果标记 `<task_result>`→`<subagent>`；v1 后台需实验开关 `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`（`ocv1-cm09-01`），v2 后台为默认参数——**门控变化**
- **核验日期**：2026-10-15

---

## 十一、CM-10 保存 / fork / 恢复

### ocv2-persist-01
- **结论**：v2 会话消息持久化到 **SQLite**（drizzle ORM，多运行时驱动 `sqlite.bun/node/workerd`）；消息写入经**事件**（`SessionEvent.Durable*`）由投影器 `SessionProjector` 落 `SessionMessageTable`（`session_id`/`id`/`type`/`seq`/`data`）；读取用 `SessionStore.messages`（游标分页，`seq` 排序）。会话/消息**从不物理删除**（压缩只追加条目）。
- **性质**：事实
- **范围**：v2 出货；`session/store.ts`、`session/sql.ts`、`session/projector.ts`、`database/`
- **实现状态**：默认
- **来源**：`session/store.ts:140-178`（`messages`：游标 + `seq` 排序 + `decodeMessageRow`）、`:179`（`context` → `SessionHistory.load(..., "latest")`）；`session/sql.ts`（`SessionMessageTable`）；`database/sqlite.bun.ts` / `sqlite.node.ts` / `sqlite.workerd.ts`；`session/projector.ts:45,66-67,95-110`（tokens/cache 列投影）
- **数据走查**：DW-persist-01
- **运行证据**：NOT_RUN（需真实会话写盘）
- **不能证明**：**不能**证明 DB 文件的**原生落盘路径**（未跑；`database/path.ts` 存在但本包未跑）；**不能**证明 schema 迁移在真实升级路径下的行为
- **冲突裁决**：支持"保存/fork/恢复"有实现；**与 v1 一致**：v1 亦为 SQLite + 事件溯源（`ocv1-persist-01`）——**存储形态未变**（v1/v2 同为 DB，不同于 omp/pi 的追加式 JSONL）
- **核验日期**：2026-10-15

### ocv2-recover-01
- **结论**：v2 恢复入口为 CLI `--continue` / `--session <id>`（`--fork` 需配 `--continue`/`--session`）；恢复走**持久化断点路线**——`SessionContext.load` 调 `SessionHistory.entriesForRunner`，boundary = `SessionProviderContext.provenance(model) ?? "local"`，**从最近一条已完成压缩起读**（`seq ≥ compaction.seq`），**不重放全部历史重算**；`Session.fork` 新建会话，按 `boundary: {before|through, messageID}` 复制边界内消息，并**继承父的最新指令基线**（`InstructionState.current` + `InstructionEntry.snapshot`）。
- **性质**：事实
- **范围**：v2 出货；`packages/cli/src/run/run.ts`、`session.ts`、`session/history.ts`
- **实现状态**：默认
- **来源**：`packages/cli/src/run/run.ts:72`（`--fork` 需 `--continue`/`--session`）、`:95-97`（continue/session/fork 传入 `resolveSessionTarget`）；`packages/cli/src/commands/commands.ts:344-394`（`continue`/`fork` flag）；`session.ts:319-359`（`fork`：boundary + 指令基线继承）、`:352-357`（`SessionEvent.Forked`）；`session/history.ts:118-135`（`entriesForRunner`）；`session/context.ts:163-179`（`load` → `entriesForRunner`）
- **数据走查**：DW-recover-01
- **运行证据**：NOT_RUN（需真实会话 + provider）
- **不能证明**：**不能**证明真实重启后"恢复了什么/丢了什么"（需 T19）；**不能**证明 fork 后子会话的完整一致性（未跑）
- **冲突裁决**：**裁决 LQ-10 = 持久化断点路线（B）**；支持 C-12"默认模型可见层用替代历史"；**与 v1 差异**：v1 `filterCompacted` 重排 + `tail_start_id` 重映射（`ocv1-recover-01`），v2 为 boundary 查询 + fork 继承指令基线——**断点表达变化**
- **核验日期**：2026-10-15

### ocv2-recover-02
- **结论**：v2 有**崩溃恢复（write-ahead claim）**——执行开始发 `Execution.Started` 时在**同一事务**写 `time_suspended`（claim），终态释放；**shutdown 中断保留 claim**，下次启动据此恢复该轮（"recovery 是数据库的属性，不是 shutdown hook"）；启动 drain 前先 `settleStaleCompactions`（把遗留 `status:"running"` 的压缩标 `Compaction.Failed{compaction.interrupted}`）与 `settleStaleToolCalls`（把遗留 `streaming/running` 工具标 `Tool.Failed{aborted}`）。
- **性质**：事实
- **范围**：v2 出货；`session/execution.ts`、`session/store.ts`、`session/runner/llm.ts`
- **实现状态**：默认
- **来源**：`session/execution.ts:76-86`（claim/release 注释）、`:111-148`（`started` claimOnCommit / `settled` releaseOnCommit；shutdown 保留）、`:87-110`（`drain`）；`session/store.ts:205-251`（`claim`/`release`/`releaseChildClaims`/`countResume`）、`:194-204`（`listSuspended`）；`session/runner/llm.ts:332-385`（`settleStaleCompactions`/`settleStaleToolCalls`）
- **数据走查**：DW-recover-02
- **运行证据**：NOT_RUN（需真实崩溃/重启）
- **不能证明**：**不能**证明真实崩溃恢复的端到端正确性（未跑）；**不能**证明 `resume_attempts` 上限策略（本包未读到上限常量）
- **冲突裁决**：**v1 未见等价"崩溃 claim + stale settlement"**（T09 包无对应卡）——v2 **新增机制**；`ocv1-fail-02` 的"中断清理"是**进程内**标 `interrupted`，v2 增加**跨进程**的 claim 恢复
- **核验日期**：2026-10-15

---

## 十二、CM-11 错误与副作用

### ocv2-fail-01
- **结论**：v2 通用重试 `policy`：指数退避 2s 起、**每间隔上限 10s**、`Schedule.recurs(10)`（**最多 10 次**）；`retry-after`/`retryAfterMs` 取 **`max(退避, retryAfter)`**，且 `retryAfter` 被夹到 **≤ 15 分钟**（`RETRY_AFTER_MAX`）；**超时类（Transport Timeout）额外上限 3 次**（`MAX_TIMEOUT_RETRIES`）；重试决定经插件钩子 `session.retry` 可改（`attempt`/`delay`）。
- **性质**：事实
- **范围**：v2 出货；`session/runner/retry.ts`
- **实现状态**：默认
- **来源**：`session/runner/retry.ts:31-32`（`RETRY_AFTER_MAX = 15 min`）、`:34-40`（`retryAfter`）、`:42-56`（`schedule`：`min(exponential 2s, spaced 10s)` + `max(recurs 10)` + jittered + `max(delay, retryAfter)`）、`:58-62`（`MAX_TIMEOUT_RETRIES=3`）、`:64-92`（`policy` + `session.retry` 钩子）
- **数据走查**：DW-fail-01（含算例）
- **运行证据**：NOT_RUN（需注入 provider 错误）
- **不能证明**：**不能**证明真实限流下重试的实际效果与耗时（需 T19）；**不能**证明各 provider 的 `retry-after` 头行为（服务端）
- **冲突裁决**：支持术语"有界重试"；**与 v1 差异**：v1 上限 **5** 次、退避因子 2、无头时限 30s（`ocv1-fail-01`），v2 上限 **10** 次、每间隔 10s、头时限 15 分钟——**重试预算变化**
- **核验日期**：2026-10-15

### ocv2-fail-02
- **结论**：v2 失败分类与副作用：① **输出超限**（`finish==="length"`）→ `Outcome.OutputLimit`，**最多连续 2 次**续跑（`CONTINUE_AFTER_OUTPUT_LIMIT` 合成消息），第 3 次连续 length 报 `output-limit` 失败；② **不完整流** → `Continue`（合成 `CONTINUE_AFTER_INCOMPLETE_STREAM`）；③ **工具中断/拒绝** → 未结算工具标 `aborted`、assistant 标 `Step interrupted`；④ 已写盘副作用**不回退**（本包未读到自动回滚）；⑤ 压缩中断 → `compaction.interrupted`；⑥ **未发现 `doom_loop` 阈值判定逻辑（推断）**（见冲突裁决栏）。
- **性质**：事实（①～⑤）/ 推断（⑥"未发现 doom_loop 阈值判定"）
- **范围**：v2 出货；`session/runner/llm.ts`、`session/runner/step.ts`、`session/compaction.ts`（⑥另检索 `core/src/session/*`、`core/src/tool/*`）
- **实现状态**：默认（①～⑤）；⑥=未证实（未见默认实现）
- **来源**：`session/runner/llm.ts:35-39`（`CONTINUE_AFTER_INCOMPLETE_STREAM`/`CONTINUE_AFTER_OUTPUT_LIMIT`）、`:290-319`（`OutputLimit`：查最近 3 条，连续 3 条 assistant `length` → `output-limit` 失败）、`:281-289`（`Continue`）；`session/runner/step.ts:62-64`（`TOOLS_INTERRUPTED`/`STEP_INTERRUPTED`/`RESULT_MISSING`）、`:207-232`（declines/interrupted/未结算工具）、`:282`（`finish==="length"` → `OutputLimit`）；`session/compaction.ts:666-670`（`compaction.interrupted`）；⑥检索（见冲突裁决栏）
- **数据走查**：DW-fail-02
- **运行证据**：NOT_RUN（需构造超限/中断）
- **不能证明**：**不能**证明真实会话中续跑对任务延续的实际效果；**不能**证明副作用回退边界（`revert` 与压缩失败关系本包未逐行核）；⑥**"未发现"≠"没有"**——`doom_loop` 权限动作名仍在 v1 迁移子集，且官方无"v2 移除 doom_loop"声明
- **冲突裁决**：支持术语"失败分类 / 副作用"；**与 v1 差异**：v1 有 `doom_loop`（连续 3 次相同工具+输入触发询问，`ocv1-fail-02`），**v2 出货路径（`core/src/session/*`、`core/src/tool/*`）未发现 `doom_loop` 阈值判定逻辑**（检索 `doom|consecutive|repeated` 无阈值判定，**推断**）；**注意**：`doom_loop` 作为**权限动作名**仍存在于 `core/src/v1/config/permission.ts:27,38`（v1 迁移子集），并在 `packages/app`（126）/`packages/web`（37，`content/docs/*/permissions.mdx`）/`packages/tui`（3）/`packages/console`（1）中广泛出现（**全仓 169 命中**，排除 node_modules）——故**不得**写"全仓零命中"；v2 新增"输出超限最多 2 次续跑"——**失败处理路径变化**
- **核验日期**：2026-10-15

---

## 十三、CM-12 缓存及总成本

### ocv2-cache-01
- **结论**：v2 **CLI 侧可证**——默认缓存策略 `"auto"`（`ai/src/cache-policy.ts`）：在**最后一个工具定义**、**首/末 system 段**、**会话尾部 1 条消息**注入 `CacheHint{type:"ephemeral"}`，**断点上限 4**（`BREAKPOINT_CAP`）；仅对"尊重内联缓存标记"的协议生效（anthropic/bedrock/openrouter 等白名单，OpenAI/Gemini 隐式缓存跳过）；路由按模型/协议特化（Anthropic→AUTO、Qwen→仅 system+tail、网关非 Anthropic/Qwen→NONE）。请求另带 `promptCacheKey`（= 会话亲和 id）与亲和头 `x-session-affinity`/`X-Session-Id`/`x-opencode-session-id`；亲和 id = `parentID ?? fork.sessionID ?? id`。**服务端命中率与 TTL = `UNOBSERVABLE`**。
- **性质**：事实（CLI 侧）/ 不可观测（服务端）
- **范围**：v2 出货；`packages/ai/src/cache-policy.ts`、`session/model-request.ts`、`session/affinity.ts`
- **实现状态**：默认（`cache:"auto"`；实际命中取决于 provider）
- **来源**：`ai/src/cache-policy.ts:17-21`（`AUTO={tools:true,system:true,messages:{tail:1}}`）、`:24`（`BREAKPOINT_CAP=4`）、`:40-56`（`RESPECTS_INLINE_HINTS`）、`:61-68`（`gatewayPolicy`/`QWEN`）、`:173-199`（`applyCachePolicy`/`selectPolicy`）；调用点 `ai/src/route/client.ts:563`；`session/model-request.ts:278-295`（亲和头 + `promptCacheKey`）；`session/affinity.ts:7-8`（亲和 id）；`ai/src/protocols/utils/cache.ts:16-23`（`cacheControl` 4 断点）
- **数据走查**：DW-cache-01
- **运行证据**：NOT_RUN（服务端 `UNOBSERVABLE`；需 T19 观测 usage）
- **不能证明**：**不能**证明命中率、TTL、真实节省金额（服务端）；**不能**证明前缀压缩后命中率退化（需 T19）
- **冲突裁决**：支持术语"缓存键（CLI 侧已证）"；缓存**≠摘要≠记忆**（严格分开）；**与 v1 差异**：v1 `applyCaching` 给"前 2 条 system + 末 2 条消息"打标记（`ocv1-cache-01`），v2 改为"**最后工具 + 首/末 system + 尾 1 条消息**、断点上限 4、按协议白名单"——**断点策略变化**；`prompt_cache_key`（v1）→ `promptCacheKey` + 亲和头（v2），语义相近
- **核验日期**：2026-10-15

---

## 十四、扩展点

### ocv2-ext-01
- **结论**：v2 扩展点 = **会话钩子 `SessionHooks`**（`prompt`/`context`/`compaction`/`generate`/`title`/`model.request`/`http.request`/`http.response`/`experimental.ws.handshake`/`experimental.ws.send`/`experimental.ws.receive`/`retry`）+ **工具钩子**（`execute.before`/`execute.after`）+ 插件效应（`Plugin`/`define`）+ `opencode.json` 配置；**`session.compaction` 钩子可直接提供摘要**（`SessionCompactionResult`，`fromHook` 跳过模型调用）；`session.context` 钩子可改写 `system`/`messages`/`tools`（如 `plugin/optimize.ts` 按模型覆盖/追加系统提示词）。
- **性质**：事实
- **范围**：v2 出货；`packages/plugin/src/effect/session.ts`、`packages/plugin/src/effect/tool.ts`、`session/compaction.ts`、`plugin/optimize.ts`
- **实现状态**：默认（钩子接口存在；是否被插件使用取决于用户装插件）
- **来源**：`packages/plugin/src/effect/session.ts:138-151`（`SessionHooks` 12 项）；`packages/plugin/src/effect/tool.ts:21-51`（`execute.before`/`execute.after`）；`session/compaction.ts:595-608`（`fromHook`：钩子提供 `summary`/`tokens`/`providerState`/`metadata`）；`session/model-request.ts:305-320`（`model.request` 钩子改 baseURL/headers）、`:253-274`（`shape`/`context` 钩子改 system/messages/tools）；`plugin/optimize.ts:64-93`（`context` 钩子按模型改 system）
- **数据走查**：DW-ext-01
- **运行证据**：NOT_RUN（需装插件）
- **不能证明**：**不能**证明插件生态的既有行为；**不能**证明多插件下钩子执行顺序细节（未跑）
- **冲突裁决**：支持"扩展点"分列（默认 vs 插件态）；**与 v1 差异**：v1 钩子域为 `chat.*`/`tool.execute.*`/`shell.env`/`experimental.chat.*`/`experimental.session.compacting`/`experimental.compaction.autocontinue`/`experimental.text.complete`/`tool.definition`（`ocv1-ext-01`），v2 重组为 `session.*`（`chat.*`→`session.context`/`session.prompt`；`experimental.session.compacting`→`session.compaction`；新增 `model.request`/`http.*`/`ws.*`/`retry`）——**钩子名与域变化**（迁移条件）
- **核验日期**：2026-10-15

---

## 计数核对

```bash
grep -c "^### ocv2-" 证据/ocv2-证据卡.md
```

**实际** = **29**（族：version 2 + assembly 2 + rule 2 + skill 1 + retrieval 1 + trunc 2 + trigger 2 + compact 4 + summary 4 + memory 1 + cm09 1 + persist 1 + recover 2 + fail 2 + cache 1 + ext 1 = **29**）。自述"29 张卡"与实际一致。

---

*配套：`工具概览.md` / `源码导读.md` / `数据走查.md` / `过程观察.md` / `问题与审查.md`。*
