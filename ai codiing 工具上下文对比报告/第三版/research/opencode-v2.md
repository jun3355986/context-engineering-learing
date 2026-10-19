# opencode v2 · 上下文管理事实卡片（beta `2.0.29`）

- **仓库**：https://github.com/anomalyco/opencode（原 `sst/opencode`）
- **提交号**：`042d0832f5f3a73eaa039a58a7d565776f6d4290`（tag `v2.0.29`，**beta**）
- **版本说明**：本文所有结论只代表 **beta `v2.0.29`** 这一个快照；beta 线仍在变动，字段与默认值可能在下个版本改变。
- **核实日期**：2026-10-18
- **分析范围**：v2 出货路径 `packages/core/src/{session,tool,skill,instructions,config,database,plugin}`、`packages/cli/src`、`packages/ai/src`、`packages/plugin/src/effect`。不分析服务端行为，不分析 TUI/桌面渲染。
- **Permalink 基址**：`https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/`
- **分界说明**：`packages/core/src/v1/*` 只是 v1 配置迁移子集，不作为 v2 行为证据；v1 侧结论一律引 `research/opencode-v1.md`，不反向推断。
- **跨版本对照**：见文末「附：v1 → v2 变化（跨版本对照）」，逐条覆盖压缩配置改名、`prune`/`tail_turns` 去留、预检估算、溢出重试、检查点内容、指令 epoch、委托后台运行。

---

## 1. 请求组装

**做法**
每一步的开始是 `context.select`（固定 session / agent / 指令源 / 工具快照）再 `context.load`（解析模型 + 按 boundary 读历史 + 渲染指令基线）。`runStep` 先跑一次 `compaction.compact({reason:"auto"})`，若刚压完就重建上下文并重来；否则 `baseTranscript` 生成**至多两段** system：`[agent.system ?? 基础提示词, initial]`，其中 `initial` 是指令基线的渲染结果（环境、规则、MCP 指令、技能清单、code mode 目录等全部折叠在这里）。消息来自 `toLLMMessages(投影消息)`；到达步数上限的最后一轮，把 `MAX_STEPS_PROMPT` 作为**一条 assistant 消息**追加，并设 `toolChoice: "none"`（"保留工具定义以维持 provider 缓存前缀"）。工具由 registry 快照产出：`codemode:false` 的内置工具按名字排序进 `definitions`，`execute` 追加在末尾；插件 `session.context` 钩子可以改名、删除，凭空新增的会被丢弃。每一次请求都重新投影，不在内存里累积。

**关键参数与默认值**
- system 至多 2 段（空段会被过滤）：`agent.system`（有则整段替换基座提示词）/ 基础提示词 + `initial`
- 基础提示词渲染 `runner/prompt/system.txt`，按当前工具名注入 `${OPENCODE_TOOL_GUIDANCE}`（shell/write/edit 三组提示）
- 末步：`Message.assistant(MAX_STEPS_PROMPT)` + `toolChoice: "none"`；工具定义仍保留
- 工具顺序：直接工具按名字排序，`execute` 追加在末尾（钩子可改名/删）
- 输出上限：`min(catalog.limit.output || 32000, 256000)`，再按"窗口 − 已用 − 估算×1.15"收缩，下限 1024

**来源**
- [session/context.ts#L121-L179](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/context.ts#L121-L179)（select / load）
- [session/runner/llm.ts#L209-L247](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/llm.ts#L209-L247)（runStep 与末步）
- [session/model-request.ts#L100-L120](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/model-request.ts#L100-L120)（baseTranscript）
- [session/model-request.ts#L88-L98](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/model-request.ts#L88-L98)（输出上限）
- [session/model-request.ts#L236-L302](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/model-request.ts#L236-L302)（prepare、工具钩子、请求头）
- [session/system-prompt.ts#L5-L28](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/system-prompt.ts#L5-L28)（基础提示词）

**可信度**：【已核实】

**源码解读候选**：`baseTranscript` 的"两段 system"如何把 v1 的四类块折叠成可复用前缀；`prepare` 里工具"按对象身份匹配"的钩子协议。

---

## 2. 规则文件的发现与合并

**做法**
v2 把规则、技能、MCP 指令、参考资料、code mode 目录、内置指引统一抽象成**有序指令源**（`Instructions.List`），每个源有 `read / initial / changed / removed` 四个渲染函数，按"最共享 → 最不共享"排序合成：`codeModeCatalog → mcp → references → skills → discovery(AGENTS.md) → builtins → entries`，注释说明目的是让基线成为可复用的 prompt-cache 前缀。`AGENTS.md` 的发现由配置插件完成：全局 `<config>/AGENTS.md` 一份，项目侧从 location 目录沿祖先链一直走到 project root，**收集沿途所有** `AGENTS.md`（不再按文件名类型去重，也没有 `CLAUDE.md`/`CONTEXT.md` 候选），顺序是"全局 → 最近 → 最远"。文件被 watcher 监听，编辑后 100 ms 防抖重扫，变更以 `Instructions.diff` 计算差异，再由 `renderUpdate` 生成"新增/删除/改动 diff（补丁过长则整段替换）"的增量文本。读取文件时还会做"就近发现"：`read` 每读一个文件，从它所在目录向上找 `AGENTS.md`，命中的路径交给 `SessionInstructions.load` 以 **synthetic 消息**注入（不是塞进工具输出），并用历史里 synthetic 的 `metadata.instruction.paths` 做去重台账——如果这条 synthetic 因压缩/回退掉出可见历史，会被重新发现并重注入。体积上限与截断未在源码中找到。

**关键参数与默认值**
- 候选文件名：只有 `AGENTS.md`（全局一份 + 项目祖先链全部）
- 指令源顺序：`codeModeCatalog, mcp, references, skills, discovery, builtins, entries`
- 增量渲染：改动用 `createPatch(..., {context: 3})`；diff 文本比整段替换长时改用整段替换
- 去重：synthetic 消息的 `metadata.instruction.paths` 台账 + 进程内 in-flight claim
- watcher 防抖：100 ms
- 体积上限/截断：**未在源码中找到**

**来源**
- [session/context.ts#L144-L160](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/context.ts#L144-L160)（顺序与注释）
- [config/plugin/instruction.ts#L38-L79](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/config/plugin/instruction.ts#L38-L79)（全局 + 祖先链收集）
- [config/plugin/instruction.ts#L90-L125](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/config/plugin/instruction.ts#L90-L125)（重扫与下发）
- [instruction-discovery.ts#L123-L149](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/instruction-discovery.ts#L123-L149)（初始/增量渲染）
- [instructions/index.ts#L124-L159](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/instructions/index.ts#L124-L159)（combine / diff）
- [session/instructions.ts#L46-L112](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/instructions.ts#L46-L112)（就近注入与台账）
- [tool/plugin/read.ts#L87-L107](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool/plugin/read.ts#L87-L107)（read 侧触发）

**可信度**：【已核实】；"无体积上限"为【推断】

---

## 3. 按需加载（渐进披露）

**做法**
技能与 v1 同构：`<available_skills>` 只列 `id / name / description`，正文由 `skill` 工具读取，技能清单变化时用差分更新（新增/删除用小增量，其余整段重述）。新增一条更彻底的渐进披露通道：**Code Mode**。工具按 `codemode` 选项分流——`codemode: false` 的内置工具（read / write / edit / patch / glob / grep / shell / skill / subagent / webfetch / websearch / question）作为工具定义直接进请求；其余（**全部 MCP 工具**与 opencode 元工具）**不进工具定义**，只以"目录行"形式写进指令基线，模型必须通过 `execute` 工具写代码来调用，目录不完整时在代码里用同步的 `search(...)` 查工具名。`execute` 被权限整体禁掉时，code mode 关闭，这些工具也不再可达。`@` 引用在入场时解析为附件（`files` 物化为 file part，`skills` 直接物化成技能正文），不是延迟加载。

**关键参数与默认值**
- 技能清单字段：`id / name / description`；空列表时给"No skills are currently available."
- 技能差分：只有新增/删除时出小增量；有改动或增删同时为空时整段重述
- Code Mode：`execute` 工具 + 同步 `search`；目录可部分展示（`catalog.shown < catalog.total`）
- 工具分流：`options.codemode === false` → 直接进 `definitions`（按名字排序）；`codemode !== false` → 只进 code mode 目录
- code mode 开关：`execute` 未被权限整体禁用即启用
- `@` 引用：`files` 并发 8 物化；技能正文在入场时读取并写入用户消息

**来源**
- [skill/instructions.ts#L16-L58](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/skill/instructions.ts#L16-L58)
- [codemode/instructions.ts#L8-L46](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/codemode/instructions.ts#L8-L46)
- [tool.ts#L228-L262](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool.ts#L228-L262)（direct / codeModeTools 分流与 definitions）
- [session/prompt.ts#L29-L76](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/prompt.ts#L29-L76)（附件与技能物化）
- [tool/mcp.ts#L36-L47](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool/mcp.ts#L36-L47)（MCP 工具以 `codemode: tool.codemode !== false` 注册）

**可信度**：【已核实】

---

## 4. 动态注入

**做法**
v2 没有 v1 的 `reminders.ts`（计划模式提醒不在本卡片范围内找到等价实现），动态注入改由"指令增量"承担：`InstructionState.observe` 对比磁盘现状与库里 `current_values`，有变化就 `commit` 发 `InstructionsUpdated`，**把渲染好的增量文本冻结进持久事件**（因为事后无法重建 Location 作用域的源），模型在下一次请求里看到"规则变了/新增/删除"的增量，而不是整段重发。就近 `AGENTS.md`、技能清单变化、code mode 目录变化都走同一套差分渲染。另外两类动态消息：后台 shell 完成通知与子代理完成通知，都作为 synthetic 消息进入会话（后台 shell 的结果在 `toLLMMessages` 里被特殊处理——只通过完成通知进一次上下文，原 shell 消息长期不在请求里）。todo 状态不注入：v2 核心工具集里没有 `todowrite`（v1 有），也没有 todo 相关的 system/reminder 文案。

**关键参数与默认值**
- 增量事件：`SessionEvent.InstructionsUpdated{delta, text}`；初始同步带 `metadata.instructions.initial = true`
- 指令文本冻结：`renderUpdateText` 在提交时渲染并随事件持久化
- 被替换值的 blob 按 hash 存 `InstructionBlobTable`，读取时批量取回（500 一批）
- 后台 shell：`metadata.background === true` 的 shell 消息不投影进请求

**来源**
- [session/instruction-state.ts#L21-L78](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/instruction-state.ts#L21-L78)（observe / commit / renderUpdateText）
- [session/instruction-state.ts#L227-L250](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/instruction-state.ts#L227-L250)（blob 存取）
- [session/runner/to-llm-message.ts#L292-L302](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/to-llm-message.ts#L292-L302)（后台 shell 不投影）
- [tool/plugin/shell.ts#L157-L185](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool/plugin/shell.ts#L157-L185)（完成通知）

**可信度**：【已核实】（增量机制与后台 shell）；"无 todo 工具"为【已核实】（`tool/plugin` 目录与全 core 检索）

---

## 5. Token 计量与可视化

**做法**
v2 是"**实测锚点 + 本地估算**"的混合模型。`estimatePrompt` 找到最近一条"本 provider 回报过 usage"的 assistant 消息作锚点，锚点之后的消息用 `Token.estimate`（仍是 chars/4）逐条累加；`estimateContext = measured + estimated`，`measured = input + cache.read + cache.write + output + reasoning`。触发上限 `calculateCeiling`：`window = limit.input || limit.context`，未知（≤0）返回 `+∞`（永不自动触发）；`buffer` 显式设置时用 `window - buffer`，否则 `window - max(floor(window×0.1), window ≥ 32000 ? 16000 : 0)`。`due` 还要求"最近一次测量锚点晚于最后一个 checkpoint"——因为加密的原生窗口本地估算为 0，必须等 provider 回报一次真实用量。媒体按固定值估算：图片 1500 token、PDF 2000 token。输出预留不是独立预算，而是在请求时按"窗口 − 已用 − 估算×1.15"动态算 `maxTokens`。

**关键参数与默认值**
- 估算：`Token.estimate = round(len/4)`；`ESTIMATE_ERROR = 0.15`（估算放大 15% 后再算余量）
- 预留：`max(10%W, 16000)`；`RESERVE_MIN = 16_000`；`buffer` 可覆盖
- 未知窗口：`UNKNOWN_WINDOW = 200_000`（只用于给压缩请求定预算，不用于触发）
- 输出上限：`OUTPUT_TOKEN_FALLBACK = 32_000`、`OUTPUT_TOKEN_MAX = 256_000`、`OUTPUT_TOKEN_MIN = 1_024`、`SUMMARY_OUTPUT_MAX = 32_000`
- 媒体估算：`IMAGE_TOKEN_ESTIMATE = 1_500`、`PDF_TOKEN_ESTIMATE = 2_000`

**来源**
- [session/compaction.ts#L868-L898](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L868-L898)（estimateContext / estimatePrompt）
- [session/compaction.ts#L900-L923](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L900-L923)（ceiling 与 measured 判定）
- [session/compaction.ts#L925-L963](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L925-L963)（请求/消息/媒体估算）
- [session/model-request.ts#L28-L42](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/model-request.ts#L28-L42)（常量）
- [session/model-request.ts#L87-L98](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/model-request.ts#L87-L98)（输出上限动态计算）

**可信度**：【已核实】

**源码解读候选**：`estimatePrompt` 的"锚点 + 之后累加"为什么比 v1 的"只看上一轮 total"更稳，以及它的盲区（锚点之前的媒体、图片预算只看锚点之后）。

---

## 6. 单次工具输出控制

**做法**
通用入口 `ToolOutput.truncate`：先判"行数 ≤ 2000 且字节 ≤ 51200"，满足就标记 `truncated:false` 原样返回；超限时只保留**头部**（`lines.slice(0, maxLines)` + 逐行累加字节到 51200），把全文写入 `global.data/tool-output/tool_<hex>`，返回"保留内容 + `[showing lines 1-N of M; full output saved to <path>]`"标记。截断后的内容按原 content 数组的文本片段逐段裁剪，file 片段原样保留，标记插在裁剪点。保留 7 天、每小时清理。压缩序列化时的第二道限长收紧到 **1250 字符**，且按 **Unicode 码点**迭代，不会切断代理对。注意一个例外：`truncate` 看到 `metadata.truncated` 已存在就直接返回（`tool-output.ts:68`），shell 工具自带这个字段（`shell/result.ts` 的 `metadata`），所以 shell 输出走的是自己的捕获通道而不是通用 `ToolOutput`；shell 通道的截断方向本次未定位到，记【待核实】。

**关键参数与默认值**
- `MAX_LINES = 2_000`、`MAX_BYTES = 50 * 1024`、`RETENTION = 7 天`、`DIRECTORY = "tool-output"`
- 方向：**只有 head**，无 `direction` 参数
- 可配置：`ToolOutput.configure({maxLines, maxBytes})`（配置插件 `config/plugin/tool-output.ts`）
- 压缩期二次限长：`TOOL_OUTPUT_MAX_CHARS = 1_250`（码点安全）
- 早退条件：`result.metadata.truncated !== undefined`

**来源**
- [tool-output.ts#L13-L18](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool-output.ts#L13-L18)（常量）
- [tool-output.ts#L67-L118](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool-output.ts#L67-L118)（截断、落盘、标记）
- [tool-output.ts#L38-L48](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool-output.ts#L38-L48)（清理）
- [session/compaction.ts#L100](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L100)、[session/compaction.ts#L807-L820](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L807-L820)（二次限长）
- [session/runner/step.ts#L123-L134](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/step.ts#L123-L134)（统一入口调用点）
- [tool/read-filesystem.ts#L14-L21](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool/read-filesystem.ts#L14-L21)（read 自身分页：2000 行 / 2000 字符 / 50 KiB / 媒体 20 MiB）

**可信度**：【已核实】（通用通道）；shell 通道截断方向【待核实】

---

## 7. 历史裁剪（不调用模型）

**无独立能力。** 依据：v1 的 `prune` 在 v2 已没有实现，只在配置规范化里作为 **unsupported** 字段被拒绝（`config/normalize.ts:334`）；`packages/core/src` 内除 git 的 `prune` 外无相关代码。v2 对旧工具输出的治理只发生在**构造压缩请求**时：`flattenAndDropOldest` 把历史文本化（丢 reasoning、媒体、指令更新，切长工具输出），必要时按 exchange 整块丢最旧的，并插入 `[N older exchanges omitted]`。这一步已经是压缩流程的一部分，不存在"平时就静默擦掉旧工具结果"的通道。

**来源**
- [config/normalize.ts#L333-L334](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/config/normalize.ts#L333-L334)（`tail_turns` / `prune` 标 unsupported）
- [session/compaction.ts#L457-L504](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L457-L504)（flattenAndDropOldest）

**可信度**：【已核实】（"无 prune 实现"由配置诊断 + 全 core 检索支持）

---

## 8. 压缩（调用模型做摘要）

**做法**
三种触发：`auto`（每步开头，`due` 成立才压）、`overflow`（provider 报上下文过长且**尚未产出任何输出**）、`manual`（`/compact` 往 inbox 塞一条 `compaction` 控制项，在步边界消费）。预算：`auto`/`manual` 用 `cap = calculateCeiling`；`overflow` 用 `min(cap, floor(估算×0.7))`，因为"provider 刚拒绝，说明估算低了"。路径分两条：模型元数据 `compaction.type === "native"` 时走 `compactNatively`（请 provider 返回加密窗口，只有同一 endpoint 能重放），否则 `summarize`。`summarize` 先 `splitConversation(messages, keep)` 切成 older/recent（recent 以**文本**存进检查点），发 `buildPrompt(...)`，回复必须命中模板标题，否则追加一次 `NUDGE` 再试，两次都不合格就 `compaction.failed`。发送前的 `deliver` 负责收缩：估算装得下就原样发；装不下就文本化 + 丢最旧 exchange；provider 报"太长"后按 `[0.7, 0.5, 0.35]` 三轮把目标降到首次被拒请求估算的 70%/50%/35%，再拒就失败。插件 `session.compaction` 若直接给出摘要，`fromHook` 跳过模型调用。压缩成功后 `publish` 发 `Compaction.Ended`（summary / recent / providerContext / usage），runner 重建上下文再继续本轮。

**关键参数与默认值**
- `auto` 默认 true；`keep` 默认 **15_000**（`compaction.keep.tokens` 可改）；`buffer` 未设 → `max(10%W, 16000)`
- 收缩步进：`SHRINK_STEPS = [0.7, 0.5, 0.35]`
- 模板：`Objective / Requirements / Decisions / Work State{Completed,Active,Blocked} / Next Move / Relevant Files（最多 15 个）/ Important Context`
- 增量规则：**新历史优先**；除非明确矛盾/取代/解决/过期，否则保留旧信息
- 模板校验：回复需包含模板中的某个 `##` 标题；失败一次 `NUDGE`；再失败 `compaction.failed`
- 旧模板兼容：`## Additional Context`（`LEGACY_HEADING`）存在时走"重写一次"分支
- 手动压缩：inbox `compaction`，默认 `delivery: "steer"`
- 多次压缩：`previousCompaction` 只认历史第一条（因为历史从最近完成压缩起读）

**来源**
- [session/compaction.ts#L94-L102](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L94-L102)（常量）
- [session/compaction.ts#L104-L182](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L104-L182)（模板、规则、buildPrompt、NUDGE、旧标题）
- [session/compaction.ts#L195-L251](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L195-L251)（默认值、compact、due）
- [session/compaction.ts#L272-L310](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L272-L310)（summarize）
- [session/compaction.ts#L324-L372](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L324-L372)（原生压缩）
- [session/compaction.ts#L384-L455](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L384-L455)（deliver 收缩）
- [session/compaction.ts#L595-L608](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L595-L608)（fromHook）
- [session/compaction.ts#L702-L738](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L702-L738)（splitConversation）
- [session/runner/llm.ts#L220-L225](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/llm.ts#L220-L225)、[session/runner/llm.ts#L115-L163](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/llm.ts#L115-L163)（自动与手动入口）
- [session/session.ts#L246-L264](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/session.ts#L246-L264)（`/compact` API）
- [app/src/session/commands/use-session-commands.tsx#L349-L354](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/app/src/session/commands/use-session-commands.tsx#L349-L354)（slash `compact`）
- [plugin/agent.ts#L120-L124](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/plugin/agent.ts#L120-L124)（compaction agent）

**可信度**：【已核实】

**源码解读候选**：`deliver` 的"估算→文本化→按比例收缩→失败"四级阶梯，为什么它同时解决了"估算偏低"和"媒体撑爆请求"两类问题。

---

## 9. 多模态上下文

**做法**
请求组装阶段有两道媒体治理。第一道 `unsupportedParts`：模型能力不支持的模态（或 xAI 不支持的非 png/jpeg/webp 图片）被替换成一句 `ERROR: Cannot read ...` 文本。第二道 `boundImages`：统计所有内联图片字节，超过 **25 MiB** 就开始从**最旧**的图片删起，删到 **15 MiB** 以下，替换文本明确要求模型"不要凭记忆断言图片内容，需要时重新读取或让用户重发"。读取侧另有 20 MiB 的媒体摄取上限；超过直接报 `MediaIngestLimitError`。压缩侧的 `messageToText` 把图片压成 `[Attached mime: name]` 一行。没有"把历史渲染成图片"的能力。

**关键参数与默认值**
- 图片预算：`IMAGE_BYTES_TRIGGER = 25 MiB` → `IMAGE_BYTES_TARGET = 15 MiB`
- 移除文案：`[This image was removed to reduce the request size ...]`
- 媒体摄取上限：`MAX_MEDIA_INGEST_BYTES = 20 MiB`（read 工具）
- 不支持的模态 → 文本错误占位；xAI 仅允许 `image/png|jpeg|webp`
- 压缩序列化占位：`[Attached <mime>: <name>]`

**来源**
- [session/model-request.ts#L28-L34](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/model-request.ts#L28-L34)（常量与移除文案）
- [session/model-request.ts#L122-L216](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/model-request.ts#L122-L216)（unsupportedParts / boundImages）
- [tool/read-filesystem.ts#L14-L21](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool/read-filesystem.ts#L14-L21)（摄取上限）
- [session/compaction.ts#L752-L805](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L752-L805)（压缩文本化）

**可信度**：【已核实】

---

## 10. 子代理隔离

**做法**
`subagent` 工具新建子会话（`parentID` 指向当前会话），子会话**上下文清空**，描述里明确写"New child sessions start with fresh context, so include all relevant context"。可以传 `sessionID` 续接之前的子会话（此时会校验它确实是当前会话的子会话），也可传 `model` 覆盖模型。深度按 `parentID` 链计算，上限取 `experimental.subagent_depth`，默认 1。子代理可用列表在 `session.context` / `compaction` / `generate` 三个钩子里动态写进工具描述（按权限过滤、按 id 排序）。返回给父会话的是 `<subagent sessionID state="completed">自由文本</subagent>`（运行中则是一句"在后台跑，别轮询"）。前台调用会 `jobs.block` 等结果；若运行中被提升为后台（`result.type === "backgrounded"`），工具提前返回 running 并注册完成通知。`background: true` 是**普通参数**，不需要任何实验开关。未见 worktree 级隔离。

**关键参数与默认值**
- `experimental.subagent_depth` 默认 **1**（v1 是顶层 `subagent_depth`，v2 移到 `experimental` 下）
- `background` 默认 false（前台），无实验开关限制
- 工具名：`subagent`（v1 为 `task`）；参数 `agent / description / prompt / model? / sessionID? / background?`
- 子代理 agent 不能是 `mode: "primary"`
- 返回：`<subagent sessionID=... state="completed|running">...</subagent>`

**来源**
- [tool/plugin/subagent.ts#L29-L62](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool/plugin/subagent.ts#L29-L62)（参数与描述）
- [tool/plugin/subagent.ts#L117-L133](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool/plugin/subagent.ts#L117-L133)（深度限制）
- [tool/plugin/subagent.ts#L184-L256](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool/plugin/subagent.ts#L184-L256)（子会话、前台/后台、提升）
- [tool/plugin/subagent.ts#L282-L309](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool/plugin/subagent.ts#L282-L309)（可用子代理写进工具描述）
- [schema/src/config/experimental.ts#L11](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/schema/src/config/experimental.ts#L11)（`subagent_depth` 位置）

**可信度**：【已核实】

---

## 11. 会话时间线

**做法**
历史读取按 **seq 边界**：`SessionHistory.latestCompaction` 找最近一条 `status="completed"` 的压缩消息（并按 boundary 判定这条压缩对当前模型是否可重放），然后取 `seq >= 该条` 的所有消息按 seq 升序，原始消息一条不删。**检查点内容**是一条 `type:"compaction"` 的消息，字段为 `status`（running/completed/failed）、`reason`（auto/manual）、`model`、`summary`、`recent`、`providerContext`（原生压缩的加密窗口）、`cost`、`tokens`；投影成模型消息时包装成 `<conversation-checkpoint>`+`<summary>`+`<recent-context>`，并明确"当历史看，不要当新指令"。恢复仍是持久化断点路线：`--continue` / `--session`，`--fork` 在 v2 要求与二者之一同用；fork 用 `before`/`through` 表达边界，并**继承父会话最新的指令基线**（不是边界时刻的基线）。崩溃恢复是数据库属性：执行开始时在同一事务写 `time_suspended` claim，正常终态释放，shutdown 中断保留 claim，下次启动据此续跑；启动 drain 前先把遗留 `running` 压缩结算成 `compaction.interrupted`、把遗留 `streaming/running` 工具结算成 `aborted`。树状分支仍不存在（只有 `parentID` 单亲）。

**关键参数与默认值**
- 边界：`"latest"`（模型中立）/ `"local"`（只看本地摘要）/ `Provenance`（只认可重放的 provider 窗口）
- 检查点字段：`status, reason, model?, providerState?, summary, recent, providerContext?, cost?, tokens?`
- fork：`boundary = {type: "before" | "through", messageID}`；继承 `InstructionState.current` + `InstructionEntry.snapshot`
- CLI：`--continue` / `--session` / `--fork`；`--fork` 的帮助文本为"继续前先分叉"（未找到 v1 那样的强制校验代码）
- 崩溃恢复：`time_suspended` write-ahead claim；遗留压缩/工具结算

**来源**
- [session/history.ts#L28-L60](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/history.ts#L28-L60)（latestCompaction）
- [session/history.ts#L78-L135](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/history.ts#L78-L135)（按 seq 取段、entriesForRunner）
- [schema/src/session-message.ts#L239-L282](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/schema/src/session-message.ts#L239-L282)（检查点字段）
- [session/runner/to-llm-message.ts#L303-L325](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/to-llm-message.ts#L303-L325)（checkpoint 投影）
- [session.ts#L319-L359](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session.ts#L319-L359)（fork）
- [session/execution.ts#L76-L86](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/execution.ts#L76-L86)（claim 注释）
- [session/runner/llm.ts#L332-L385](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/llm.ts#L332-L385)（遗留结算）
- [cli/src/commands/commands.ts#L345-L370](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/cli/src/commands/commands.ts#L345-L370)、[#L388-L400](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/cli/src/commands/commands.ts#L388-L400)（CLI 参数）

**可信度**：【已核实】

---

## 12. 跨会话记忆

**无此能力。** 依据：`packages/core/src` 中检索 `memory` 只命中 `environment/memory.ts`（内存文件系统驱动）、MCP OAuth、shell、watcher 等无关模块，没有记忆写入/整理/检索/过期模块，也没有项目级持久知识注入路径。

**可信度**：【已核实】（限定于 `packages/core/src`）

---

## 13. 缓存友好设计

**做法**
`packages/ai` 的缓存策略层默认 `"auto"`：给**最后一个工具定义**、**首/末两段 system**、**尾部 1 条消息**打断点，总数上限 4；手工设在 part 上的 `CacheHint` 优先占用预算，auto 只填剩余槽位。是否真正下发取决于协议白名单（`RESPECTS_INLINE_HINTS`）：Anthropic 系、Bedrock、OpenRouter 等尊重内联标记的才注；OpenAI/Gemini 隐式缓存的不注；网关按模型 ID 特化（Anthropic → auto，Qwen → 只 system+tail，其他 → none）。请求另带 `promptCacheKey` 和亲和头，亲和 id 取 `parentID ?? fork 的源会话 ?? 自身`，让子会话/分叉尽量复用父的缓存键。压缩与缓存的关系：压缩会换掉整段历史，缓存必然失效，v2 没有围绕缓存做压缩时机调度；但把 `initial` 作为稳定前缀、把变化都放进增量消息，本身就是缓存友好设计。

**关键参数与默认值**
- `AUTO = { tools: true, system: true, messages: { tail: 1 } }`、`BREAKPOINT_CAP = 4`
- 默认值：`undefined` 等价 `"auto"`；`"none"` 关闭自动放置
- 亲和 id：`parentID ?? fork.sessionID ?? id`；`promptCacheKey` 去掉 `ses_` 前缀
- 服务端命中率 / TTL：不可观测

**来源**
- [ai/src/cache-policy.ts#L17-L47](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/ai/src/cache-policy.ts#L17-L47)（AUTO / BREAKPOINT_CAP / 协议白名单）
- [ai/src/cache-policy.ts#L61-L69](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/ai/src/cache-policy.ts#L61-L69)（网关特化）
- [session/model-request.ts#L278-L295](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/model-request.ts#L278-L295)（亲和与缓存键）
- [session/affinity.ts#L7-L8](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/affinity.ts#L7-L8)（亲和 id）

**可信度**：【已核实】（客户端侧）；服务端行为【待核实】

---

## 14. 失败恢复

**做法**
重试策略：指数退避 2 s 起、单次间隔上限 10 s、最多 **10** 次，带 jitter；provider 给的 `retry-after` 夹到 ≤15 分钟；超时类错误另有 3 次上限（因为一次超时已经等了几分钟）。上下文溢出**不进重试**，而是走 `recoverOverflow`：仅当"还没产出任何输出"时触发 `compact({reason:"overflow"})`，成功则新建 assistant 消息、重建上下文重发；同一步只允许一次 overflow 压缩（`recoverOverflow = false`）。压缩内部还有自己的收缩阶梯（见第 8 类），最后兜底是 `compaction.failed`。输出被截断（`finish === "length"`）时连续续跑，最多 2 次（查最近 3 条消息是否全是 assistant + `finish=length` 来判定），第 3 次直接 `output-limit` 失败。流中断（incomplete-stream）用 `CONTINUE_AFTER_INCOMPLETE_STREAM` 续跑一次。工具中断/用户拒绝：未结算工具标 `aborted`，assistant 标 `Step interrupted`。压缩被中断发 `compaction.interrupted`。

**关键参数与默认值**
- 重试：最多 10 次、间隔上限 10 s、jitter、`RETRY_AFTER_MAX = 15 分钟`、`MAX_TIMEOUT_RETRIES = 3`
- 溢出：`reason: "overflow"`，预算 `min(cap, floor(estimate×0.7))`；每步一次
- 输出超限续跑：最多 2 次（第 3 次 `output-limit`）
- 不完整流：续跑 1 次
- 压缩失败：`compaction.failed` / `compaction.unavailable` / `compaction.interrupted`

**来源**
- [session/runner/retry.ts#L31-L62](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/retry.ts#L31-L62)（schedule 与超时上限）
- [session/runner/retry.ts#L64-L92](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/retry.ts#L64-L92)（policy 与钩子）
- [session/runner/step.ts#L155-L167](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/step.ts#L155-L167)（溢出判定条件）
- [session/runner/llm.ts#L265-L271](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/llm.ts#L265-L271)（recoverOverflow）
- [session/runner/llm.ts#L281-L319](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/llm.ts#L281-L319)（续跑与输出上限）
- [session/compaction.ts#L403-L455](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L403-L455)（收缩与兜底）

**可信度**：【已核实】

---

## 15. 扩展点

**做法**
会话钩子 `SessionHooks` 覆盖：`prompt`（用户输入准入）、`context`（可改 `system` / `messages` / `tools`，包括按模型换系统提示词）、`compaction`（**可以直接提供摘要**，走 `fromHook` 跳过模型）、`generate`、`title`、`model.request`（改 baseURL/headers）、`http.request` / `http.response`、`experimental.ws.*`（握手/收发帧）、`retry`（改 attempt/delay），另有工具级 `execute.before` / `execute.after`。相比 v1，压缩钩子从"改提示词"升级为"可直接产出摘要"；`model.request` / `http.*` / `ws.*` / `retry` 是新增域。没有自定义切点算法、保留预算算法之类的钩子。

**关键参数与默认值**
- `session.compaction` 返回 `{summary, tokens?, providerState?, metadata?}` 时跳过模型调用
- `session.retry.decision` 可改 `{retry, delay}`；非有限值或负数回落为原 delay
- `session.context` 钩子里"凭空新增的工具定义"会被丢弃（只接受已有定义的身份或 key 改名）
- 模型专属提示词（gpt/claude/kimi/trinity/muse）就是通过 `session.context` 钩子注入的

**来源**
- [plugin/src/effect/session.ts#L138-L151](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/plugin/src/effect/session.ts#L138-L151)（钩子清单）
- [session/compaction.ts#L594-L608](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L594-L608)（fromHook）
- [session/model-request.ts#L253-L274](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/model-request.ts#L253-L274)（context 钩子塑形工具）
- [session/runner/retry.ts#L78-L91](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/retry.ts#L78-L91)（retry 钩子）

**可信度**：【已核实】

---

## 16. 评估与可观测

**做法**
可观测性同样是"记账 + 事件"：`SessionUsage.record` 把 provider usage 换算成 `{input, output, reasoning, cache.read, cache.write}` 与 `cost`（支持按上下文长度分档计价），`Step.Ended` 事件带 finish/usage/snapshot/files，压缩自身也记账（`UsageRecorded source:"compaction"`，失败与中断也计费）。没有评测集、指标定义、A/B 分流或策略对比工具。要评估上下文策略只能外部采集：读 SQLite 的消息与 `compaction` 记录、订阅事件流，自行统计压缩频率、压缩后轮次、token 曲线、`compaction.failed` 比例。

**关键参数与默认值**
- 记账粒度：per-step + per-compaction；压缩费用按该次压缩的全部模型调用累加
- 事件：`Step.Ended`、`Compaction.Started/Ended/Failed`、`UsageRecorded`、`RetryScheduled`
- 评测集 / 指标 / A/B：**未在源码中找到**

**来源**
- [session/usage.ts#L1-L40](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/usage.ts#L1-L40)
- [session/runner/step.ts#L234-L261](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/step.ts#L234-L261)
- [session/compaction.ts#L610-L621](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L610-L621)

**可信度**：【已核实】（记账与事件）；"无评测能力"为【推断】

---

## 附：v1 → v2 变化（跨版本对照）

> 对照纪律：v1 侧只引 `733b2c6`，v2 侧只引 `042d083`，同一段落不混用两份快照。以下每条都给出两侧来源。

### 1. 压缩配置字段的改名

| v1 字段 | v2 字段 | 处理方式 | 依据 |
|---|---|---|---|
| `compaction.auto` | `compaction.auto` | 保留，默认 true | [v1 config#L149-L156](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/core/src/v1/config/config.ts#L149-L156) / [v2 schema#L4-L13](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/schema/src/config/compaction.ts#L4-L13) |
| `compaction.reserved` | `compaction.buffer` | 旧名自动迁移，语义不变（窗口下预留多少 token） | [v2 normalize#L366-L378](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/config/normalize.ts#L366-L378) |
| `compaction.preserve_recent_tokens` | `compaction.keep.tokens` | 旧名自动迁移为 `keep.tokens`；两者同时出现时 `prefer(legacy, native)`（旧名优先） | [v2 normalize#L345-L365](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/config/normalize.ts#L345-L365) |
| `compaction.prune` | — | **标 unsupported**，出现即产生诊断 | [v2 normalize#L334](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/config/normalize.ts#L334) |
| `compaction.tail_turns` | — | **标 unsupported** | [v2 normalize#L333](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/config/normalize.ts#L333) |

默认值也变了：v1 的保留预算未设时按 `clamp(usable×0.25, 2000, 15000)` 浮动（[v1 compaction#L115-L120](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L115-L120)）；v2 未设时是**固定 15000**（[v2 compaction#L195-L203](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L195-L203)）。配置下发路径也从"运行时直接 `config.get()`"改成"配置插件把值写进 `SessionCompaction` 的 state"（[v2 config/plugin/compaction.ts#L9-L24](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/config/plugin/compaction.ts#L9-L24)）。

### 2. `prune` 与按回合保留（`tail_turns`）的去留

- **v1 有 `prune`**，默认关闭；从尾部数 2 个 user turn 之后才开始擦，保护最近 40000 token 的工具输出，可擦量 > 20000 才落地，`skill` 工具受保护；擦除只打 `time.compacted` 时间戳（[v1 compaction#L271-L317](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L271-L317)）。
- **v2 没有 `prune` 实现**，配置层直接判 unsupported（[v2 normalize#L334](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/config/normalize.ts#L334)）；旧工具输出的清理改由压缩请求构造时的"文本化 + 丢最旧 exchange"承担（[v2 compaction#L457-L504](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L457-L504)）。
- **v1 的 `tail_turns`** 只限制"候选 turn 数"，真正的保留量仍由 token 预算决定（[v1 compaction#L228-L233](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L228-L233)）。
- **v2 删掉 `tail_turns`**，改为纯 token 预算 `keep` + "切点必须落在 user 消息上"的规则：从最旧开始丢 entry 直到剩余 ≤ keep，再回退到最近的 user 边界，保证一次 assistant 的工具调用与结果同进退（[v2 compaction#L716-L738](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L716-L738)）。

### 3. 预检估算公式

- **v1：不估算，只看实测。** `count = tokens.total || (input + output + cache.read + cache.write)`，与 `usable = limit.input − reserved` 比大小；`reserved = min(20000, maxOutputTokens)`，可被 `reserved` 覆盖。没有 provider 回报就不会触发（[v1 overflow#L8-L34](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/overflow.ts#L8-L34)）。`Token.estimate`（chars/4）只用于挑保留尾部（[v1 compaction#L215-L221](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L215-L221)）。
- **v2：实测锚点 + 之后逐条估算。** `estimateContext = measured + estimated`，`measured` 取最近一次本 provider 回报的 `input+cache.read+cache.write+output+reasoning`，`estimated` 是锚点之后消息的 chars/4 累加（[v2 compaction#L868-L898](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L868-L898)）。上限从"绝对预留"改成"比例预留"：`window − max(10%W, 16000)`，`buffer` 可覆盖；未知窗口返回 `+∞`（永不触发）（[v2 compaction#L900-L912](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L900-L912)）。另有两条 v1 没有的判据：锚点必须晚于最后一个 checkpoint（原生窗口本地测不出大小）、最后一条是刚完成的压缩则跳过（[v2 compaction#L242-L251](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L242-L251)）。

### 4. 溢出后重试

- **v1**：`ContextOverflowError` 不重试，转 `needsCompaction`；`auto:true, overflow:!finish` 建压缩条目；`process` 在 overflow 模式下把触发溢出的用户消息剥掉（媒体退化为文本）再压，压完把这条消息**重放**回会话；压缩自身再溢出就写 `ContextOverflowError` 并 `stop`，**没有第二次尝试**（[v1 processor#L613-L639](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/processor.ts#L613-L639)、[v1 compaction#L340-L356](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L340-L356)、[#L450-L459](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L450-L459)）。
- **v2**：溢出只在"还没产出任何输出"时触发压缩（[v2 step#L155-L167](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/step.ts#L155-L167)）；预算先自降到 `估算×0.7`（[v2 compaction#L226-L228](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L226-L228)）；发送阶段遇"too long"按 `[0.7, 0.5, 0.35]` 三轮收缩，仍不行才 `compaction.failed`（[v2 compaction#L403-L455](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L403-L455)）；同一步只允许一次 overflow 压缩（`recoverOverflow = false`），压缩成功后换新 assistant 消息重发（[v2 llm#L265-L271](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/llm.ts#L265-L271)、[#L320-L323](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/llm.ts#L320-L323)）。"payload-too-large"（字节超限）单独识别：先原样重发一次文本化版本，不计入收缩次数（[v2 compaction#L428-L433](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L428-L433)）。

### 5. 检查点内容

- **v1**：检查点由**两条消息 + 一个字段**组成——user 消息的 `parts` 里有 `type:"compaction"` 的 part（`auto`、`overflow`），紧跟一条 `summary:true` 的 assistant 消息，保留起点记在该 part 的 `tail_start_id`（[v1 compaction#L559-L582](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L559-L582)、[#L461-L466](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L461-L466)）。重建靠 `filterCompacted` 按 `tail_start_id` **重排**（[v1 message-v2#L534-L585](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/message-v2.ts#L534-L585)）。
- **v2**：检查点是**一条消息**，带 `status`（running/completed/failed）、`reason`、`model`、`providerState?`、`summary`、`recent`、`providerContext?`（原生加密窗口）、`cost?`、`tokens?`（[v2 schema/session-message#L239-L282](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/schema/src/session-message.ts#L239-L282)）。保留段以**文本** `recent` 存在检查点里，重建按 **seq 边界**取连续段，不再重排（[v2 history#L78-L108](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/history.ts#L78-L108)）。投影成 `<conversation-checkpoint>` + `<summary>` + `<recent-context>`（[v2 to-llm-message#L303-L325](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/to-llm-message.ts#L303-L325)）。
- 附带变化：摘要模板多了 `Requirements / Decisions / Important Context` 三节，增量规则从"未带过来即丢失、冲突以新对话为准"改成"新历史优先、除非明确矛盾才丢旧信息"（[v1 core/compaction#L16-L55](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/core/src/session/compaction.ts#L16-L55) vs [v2 compaction#L104-L176](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L104-L176)）。

### 6. 指令版本号（epoch）

- **v1 无 epoch。** 系统块每一步从磁盘重读、整段重拼，没有"基线 + 增量"的概念，也没有版本号（[v1 prompt#L1257-L1269](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/prompt.ts#L1257-L1269)）。
- **v2 有持久化的指令状态**：`InstructionStateTable` 记 `epoch_start` / `through_seq` / `initial_values` / `current_values`；每次请求开头渲染 `initial_values` 作为基线，变化走 `InstructionsUpdated` 增量（[v2 instruction-state#L89-L154](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/instruction-state.ts#L89-L154)）。
- **推进时机**：每次 `Compaction.Ended` 都由投影器调用 `advanceEpoch(seq)`，把当前值提升为新基线、把 `epoch_start` 移到压缩事件的 seq（[v2 projector#L731-L736](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/projector.ts#L731-L736)、[v2 instruction-state#L139-L154](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/instruction-state.ts#L139-L154)）。
- **语义**：压缩后历史被截断，"压缩前批次的指令更新"不再需要按时间顺序重放，基线一次性覆盖它们；fork 也从父会话继承最新基线而不是边界时刻的基线（[v2 session.ts#L341-L357](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session.ts#L341-L357)）。

### 7. 委托命令改为后台运行

这一条**不是"默认值从同步改成后台"**，源码事实更细：

- **v1**：工具名 `task`，默认前台；`background: true` 只有在 `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true` 时才被接受，否则直接失败（[v1 task#L92-L102](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/task.ts#L92-L102)）。前台执行中任务可被"提升"为后台：`raceFirst(wait, waitForPromotion)` 命中提升就提前返回 running（[v1 task#L328-L346](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/task.ts#L328-L346)）。
- **v2**：工具名 `subagent`，`background` 是**一等参数**，没有任何实验开关；默认仍是前台，但后台运行、续接（`sessionID`）、覆盖模型（`model`）都是一句话可用的正常能力（[v2 subagent#L29-L62](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool/plugin/subagent.ts#L29-L62)、[#L200-L244](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/tool/plugin/subagent.ts#L200-L244)）。
- **共同点**：两者都支持"前台跑着跑着被提升为后台并通知"，都不是"默认后台"。
- **相关改名**：深度配置从顶层 `subagent_depth`（[v1 config#L84-L86](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/core/src/v1/config/config.ts#L84-L86)）移到 `experimental.subagent_depth`，旧的顶层写法被列进 unsupported 顶层键并迁移（[v2 normalize#L45](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/config/normalize.ts#L45)、[#L451-L458](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/config/normalize.ts#L451-L458)）。

### 8. 其他值得记录的变化

- **工具输出二次限长**：2000 → **1250 字符**，且改成码点安全（v1 按 UTF-16 切，可能切断代理对）（[v1 compaction#L30](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L30) vs [v2 compaction#L100](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/compaction.ts#L100)）。
- **工具输出方向**：v1 有 `head`/`tail` 双向参数；v2 通用通道只保头（shell 走自己的捕获通道）。
- **规则文件候选**：v1 有 `AGENTS.md / CLAUDE.md / CONTEXT.md` 且"首个类型命中、取该类型沿途全部"；v2 只有 `AGENTS.md`，全局 + 全部祖先链，并加 watcher 热更新。
- **就近规则注入位置**：v1 追加在**工具输出的 `<system-reminder>` 里**（[v1 read#L355-L356](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/read.ts#L355-L356)）；v2 作为**独立 synthetic 消息**，带路径台账去重（[v2 instructions.ts#L46-L93](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/instructions.ts#L46-L93)）。
- **末步提示的角色**：v1 也是 assistant 消息，但没有 `toolChoice:"none"`；v2 显式禁用工具并保留工具定义以维持缓存前缀（[v2 llm#L240-L244](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/runner/llm.ts#L240-L244)）。
- **重试预算**：5 次 / 30 s 上限 → 10 次 / 10 s 上限 + 15 分钟 retry-after + 超时单独 3 次。
- **崩溃恢复**：v1 只有进程内中断清理；v2 有 write-ahead claim + 遗留压缩/工具结算（[v2 execution#L76-L86](https://github.com/anomalyco/opencode/blob/042d0832f5f3a73eaa039a58a7d565776f6d4290/packages/core/src/session/execution.ts#L76-L86)）。
- **doom_loop**：v1 有 `DOOM_LOOP_THRESHOLD = 3` 的判定；v2 出货路径未见等价阈值判定（`doom_loop` 只作为 v1 迁移的权限动作名残留）【推断】。
