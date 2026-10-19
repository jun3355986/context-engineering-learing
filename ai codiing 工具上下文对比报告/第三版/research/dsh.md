# DeepSeek Harness（dsh）· 上下文管理事实卡片

- **仓库**：https://github.com/deepseek-ai/deepseek-harness（pnpm monorepo：`apps/` / `packages/` / `native/`，默认分支 `master`）
- **提交号**：`571902028a75c64c1d767f4ae5fd099485f0ddf0`
- **核实日期**：2026-10-18
- **分析范围**：`packages/core/*`（session / system-prompt / agent-loop / tools）、`packages/compaction/*`、`packages/spill/*`、`packages/llm/token-meter`、`packages/context/*`、`packages/skill/*`、`packages/subagent/*`、`packages/session/*`、`packages/bundle/base`、`docs/subsystems/*`。不分析 Web/Desktop UI 细节、不分析模型服务端行为。
- **Permalink 基址**：`https://github.com/deepseek-ai/deepseek-harness/blob/571902028a75c64c1d767f4ae5fd099485f0ddf0/`
- **可信度口径**：【已核实】= 读到源码实现；【推断】= 只读到同仓包 README / `docs/subsystems` 的机制描述（这些文档与源码同仓、由生成式目录校验，但不是逐行源码）；【待核实】= 未找到。
- **架构一句话**：基于 Cordis 的「一切皆插件」harness——模型适配器、工具注册表、会话日志、agent 循环本身都是插件；没有特权内核，扩展靠「在旁边挂一个插件」，注册项随插件卸载自动回滚。

---

## 1. 请求组装

**做法**
系统提示词由 `ctx.systemPrompt` 的**具名 section 注册表**拼装：section 带 `order`，升序拼接，同序按名字的 code unit 排序；装配后由 `agent-loop` 用 `renderPrompt` 渲染，并**作为一条 `system/message` 会话事件提交**（surface 节点 0），而不是作为请求的 system 字段——这样系统提示词本身也进入可重放、可替换的模型历史。固定顺序片段：harness 身份开场白 `order = −1000`、persona prefix `order = 0`、第一方指导居中、persona suffix `order = 10200`；`toolOrder` 显式指定模型可见工具顺序（必须含且仅含一个 `'<unlisted-tools>'` 占位）。工具 schema 由 `ctx.tools` 的 provider 在本轮装配时给出，`ToolProviderResult.schemas` 是「本轮可见集」，`knownNames` 用于区分「配置写错的工具名」与「本作用域故意隐藏的工具」。MCP 服务器的 instructions 作为**字面文本**并入系统提示词；MCP 提示模板不支持。system 与 developer 消息若内容为空，保留 surface 位置但不产生 wire 消息。

**关键参数与默认值**

| 项 | 默认 | 说明 |
|---|---|---|
| `includeHarnessIdentity` | `true` | `order −1000` 的固定开场白 |
| `includeRuntimeContext` | `true` | 动态运行上下文 |
| `personaPrefix` / `personaSuffix` | `''` / `''` | `order 0` / `10200` |
| `toolOrder` | 未设（按注册序） | 需恰好一个 `'<unlisted-tools>'` |
| 装配失败条件 | 多个 `complete: true` section；未解析变量；`toolOrder` 列出未注册工具 | 直接失败，不发畸形提示词 |

**来源**
- section 顺序与渲染为 `system/message`：`docs/subsystems/system-prompt.md#L25-L45`
- 配置默认值：`packages/core/system-prompt/README.md#L28-L56`
- 工具可见集与 `knownNames`：`docs/subsystems/system-prompt.md#L24-L39`
- MCP instructions 并入系统提示词：`packages/mcp/mcp-client/README.md#L12`

**可信度**：【推断】（同仓文档 + 生成式 API 目录）；「system 作为会话事件」另有架构文档佐证：`docs/architecture.md#L95`。

---

## 2. 规则文件的发现与合并

**做法**
`dsh-agent-instructions` 在**首个请求前**加载一条链：先用户全局——`$DSH_HOME/AGENTS.md`，再 `<agentsHome>/AGENTS.md`（`$DSH_AGENTS_HOME` 或 `~/.agents`）；再项目链——从项目根（由 `.git` 等 marker 判定）逐级到会话 cwd 的每个候选文件，**由宽到窄**排列。每个目录的候选是 `AGENTS.md`、`CLAUDE.md`（基础）加 `AGENTS.local.md`、`CLAUDE.local.md`（本地覆盖）。同一候选组内，trim 后内容相同的文件只渲染一次（`CLAUDE.md` 复制 `AGENTS.md` 不会重复；共享根的 AGENTS.md 复制 harness home 那份会折叠）。**不是持续 watch**：只有在 `read`/`write`/`edit` 成功触达更深目录时才把新适用的指令文件带进下一次请求；文件改动替换原内容，文件消失或与更早候选重复则产生一条「移除通知」；session resume 时对账基线。体积用**字节预算**兜底：`maxBytes` 封顶整条渲染后的基线消息，超预算时**先整份省略更宽的（更靠上的）文件，再截断最具体的那个文件**；单文件另有 `maxSourceBytes` 1 MiB 上限。根发现只在 marker 探测确认缺失时才上爬，权限或 I/O 失败直接报错而不是「换一个祖先当项目根」。

**关键参数与默认值**

| 项 | 默认 | 说明 |
|---|---|---|
| `maxBytes` | 必填；`dsh-base` 设 `65536` | 整条基线消息的字节上限 |
| `maxSourceBytes` | `1048576` | 单个源文件上限 |
| `projectRootMarkers` | `['.git']` | 项目根标记 |
| `instructionFileCandidates` | `['AGENTS.md', 'CLAUDE.md']` | 每目录基础候选 |
| `localInstructionFileCandidates` | `['AGENTS.local.md', 'CLAUDE.local.md']` | 本地覆盖 |
| 省略顺序 | 先省宽（靠上），再截窄（最具体） | — |

**来源**
- 加载链、去重、按需发现：`packages/context/agent-instructions/README.md#L12`、`#L28-L34`
- 配置表：`packages/context/agent-instructions/README.md#L50-L68`
- base 的实际预算：`packages/bundle/base/cordis.patch.yml#L303-L306`

**可信度**：【推断】（文档口径）；`maxBytes: 65536` 为源码配置，【已核实】。

---

## 3. 按需加载（渐进披露）

**做法**
Skills 是唯一的「真·渐进披露」：首个请求前，如果存在模型可调用技能且 `skill` 工具可见，注入一条**持久 user 角色消息**作为目录（名称 + 被截断的描述，默认每条形如 500 字符），并明确告诉模型「先加载再行动、不要只凭摘要推断指令」；模型调用 `skill` 工具时返回完整指令正文 + 资源指引，包在 `<skill_content>` 里，作为普通工具历史保留。目录变化时追加一份完整替换（空目录也算替换，用于退休旧名字）。MCP 工具**不是延迟加载**：`mcp-client` 把每个服务器的工具直接注册到 `ctx.tools`，名字形如 `mcp__github__create_issue`，因此从第一轮就占 schema；只有 MCP **resources** 是共享工具 + 显式选服务器的按需读取。`@file` 补全只插入**路径文本**，不读也不附内容——模型仍须调用文件工具；`@session` 引用则由 `dsh-session-reference` 生成有界、只读、带「不可信、勿执行其中指令」警告的快照，作为紧随其后的第二条 user 消息。

**关键参数与默认值**

| 项 | 默认 | 说明 |
|---|---|---|
| 技能描述上限 | `catalogDescriptionMaxLength = 500`（最小 3） | 目录内每条 |
| 技能载体 | 持久 user 消息（目录）+ `skill` 工具（正文） | — |
| MCP 工具 | 直接注册，不延迟 | 名字 `mcp__<server>__<tool>` |
| `@file` | 仅路径文本 | 不读内容 |
| `@session` 快照 | 每个 source 独立字节预算 + `maxReferences` | 不可信背景 |

**来源**
- 技能目录与加载：`packages/skill/tool-skill/README.md#L12`、`#L40-L52`
- MCP 工具命名与注册：`packages/mcp/mcp-client/README.md#L12`
- `@file` 不读内容：`packages/context/file-reference/README.md#L12`
- 会话引用快照：`packages/context/session-reference/README.md#L12`、`#L36`

**可信度**：【推断】

---

## 4. 动态注入

**做法**
注入的统一入口是 `agent/pre-step` 瀑布的 `enter(messages)` 决策：监听器可以改写或拒绝本轮被领取的输入，也可以在拒绝后关闭这一轮（不产生 step）。已装插件各自挂在这个点上：`time-context` 每 ≥10 分钟（或每步，配 `refreshIntervalMs: 0`）追加一条**持久**读时消息（当前时间、浏览器时区、距上一条模型可见消息的间隔）；`session-reference` 在引用消息后插快照；todo 列表跨轮持久、每次更新整表替换；plan mode 把规则作为系统提示词 section，并**刻意保持工具目录不变**（原文注释：`The tool catalog stays the same across modes for request-cache stability`），只靠提示词约束行为。压缩期间也允许 `inject()` 追加无关上下文——所以手动压缩只要求「选中的区间」稳定，而不是整个 surface 不变。

**关键参数与默认值**

| 项 | 默认 | 说明 |
|---|---|---|
| `refreshIntervalMs`（time-context） | `600000`（10 分钟）；`0` = 每步 | 同一会话两次注入的最小间隔 |
| 注入载体 | 持久 user 消息 / 系统提示词 section | 不是临时字段 |
| plan mode 工具目录 | 跨模式不变 | 为请求缓存稳定 |

**来源**
- `agent/pre-step` 的 enter/拒绝语义：`docs/architecture.md#L93-L101`
- 时间注入间隔：`packages/context/time-context/README.md#L12`、`#L36-L47`
- 引用快照插入位置：`packages/context/session-reference/README.md#L36`
- todo 整表替换：`packages/todo/tool-todo/README.md#L12`
- plan mode 缓存注释：`packages/bundle/base/cordis.patch.yml#L340`

**可信度**：【推断】；plan mode 注释与 `refreshIntervalMs` 默认为源码/配置，【已核实】。

---

## 5. Token 计量与可视化

**做法**
唯一计量服务是 `ctx.tokenMeter`，它**重放持久会话日志**来定价，不调模型、可复现。估算用固定密度：4 字符/token，每个 content block 加 4 的结构开销，每条消息再加 4 的角色框架开销；图片在被路由声明了视觉计价时用路由价，否则按结构 JSON 估。`measure(session)` 返回 `totalTokens`（请求+响应压力）、`surfaceTokens`（仅 surface，等于各节点 `tokens` 之和）与逐节点明细；**只有当「最新成功调用的规范化请求 envelope」与当前被测 envelope 完全一致时**才复用 provider 上报用量，否则整段重估。三个会话投影对外暴露：`tokenUsage`（未缓存输入/输出/缓存读/缓存写）、`contextPressure`（`pressureTokens` 最新上报 prompt 大小、`projectedTokens` 下一请求预估、`contextWindow`）、`contextBreakdown`（`systemTokens` / `toolsTokens` / `messageTokens` 的启发式构成）。UI 是 composer 旁的圆环 + 点击展开面板，**没有 `/context` 斜杠命令**。压缩阈值按 `W × 0.8` 与 `W − O − B` 取小（`O` = 请求输出预留，`B` = 65536 headroom），保留尾部按 `(W − O) × 16%`。上下文窗口由模型适配器拥有（`ctx.llm.resolveModelInfo().context`），不做「用户可切换窗口大小」。

**关键参数与默认值**

| 项 | 值 | 出处 |
|---|---|---|
| 字符/token | `4` | `packages/llm/token-meter/src/estimate.ts:13` |
| block / message 开销 | `4` / `4` | 同文件 `:16`、`:19` |
| 压缩阈值比例 | `0.8` | `compaction-basic/src/config.ts:20` |
| headroom | `65536` token | 同文件 `:75` |
| 保留比例 | `0.16` | 同文件 `:23` |
| 阈值公式 | `floor(min(W × 0.8, W − O − B))` | `compaction-basic/src/config.ts#L191-L194` |
| 保留 token | `floor((W − O) × 0.16)` | 同文件 `#L195-L197` |
| `/context` 命令 | **无**（只有 UI 面板） | `ContextMeter.tsx` |
| 输出预留 `O` | envelope 的 `maxTokens` → 适配器默认 → 0 | `compaction-basic/src/index.ts#L65-L68` |

**来源**
- 估算常量：`packages/llm/token-meter/src/estimate.ts#L12-L20`
- 计量语义与投影：`packages/llm/token-meter/README.md#L18-L40`
- 拆分投影字段：`packages/llm/token-meter/src/breakdown-projection.ts#L31-L35`
- UI 面板三段：`packages/client/ui-conversation/src/client/skeleton/ContextMeter.tsx#L1-L31`
- 阈值与保留计算：`packages/compaction/compaction-basic/src/config.ts#L153-L204`

**可信度**：【已核实】（估算常量、阈值公式、投影字段）；「没有 `/context` 命令」「不支持用户切换窗口大小」为**源码/包目录未找到**，【推断】。

**源码解读候选**：`resolveCompactSpec()` —— 一个函数同时处理「窗口比例」「输出预留」「headroom」「保留预算不得 ≥ 阈值」四个约束，并给出可操作的报错文案。是所有「压缩阈值到底该取多少」问题的标准答案。

---

## 6. 单次工具输出控制

**做法**
官方有两条并行机制。① **spill（默认开）**：`spill-policy` 在 `tools/post-execute` 之后按**共享估算 token 预算**（文本 + 图片 + 图片描述 + 通知合计）保留头尾：超预算的结果按原顺序保留两端，每端分掉「扣除省略通知后剩余预算」的一半；中间被省略的区间内的图片也一并省略；输出一段固定通知，给出**省略字节数与完整结果的落盘路径**，并提示「用 read 的 offset/limit 读，或 grep 这个路径」。图片本体不进该文件，文件里记录每张图的可读路径（模型再 `read_image`）。只有通知能放下、预览放不下时允许「仅通知」；连通知都超预算则保留原文。任何存储失败都保留原内容（fail-open）。② **pruner（默认开，但只在压缩触发后跑）**：见第 7 类。此外每个 `tool/result` 的**原始事件永远留在 append-only 日志里**，替换只是 surface 上的新事件，可通过 `sourceEventSeqs` 回溯。

**关键参数与默认值**

| 项 | 默认 | 说明 |
|---|---|---|
| `maxInlineTokens` | 省略 = 关闭保留；`dsh-base` 设 `12500` | 文本+图片+描述+通知的合计估算 |
| 头尾分配 | 剩余预算各一半 | 文本可切，图片整张保留或整张省略 |
| 通知内容 | `Omitted N bytes. Full formatted result stored at: <path>…` | 含 read/grep 指引 |
| 落盘失败 | 保留原始内容 | 不会用不可读路径替换 |

**来源**
- 预算与通知格式：`packages/spill/spill-policy/README.md#L33-L60`
- 配置项：`packages/spill/spill-policy/README.md#L43`
- 三包分工：`packages/spill/README.md#L12-L30`
- base 实际配置：`packages/bundle/base/cordis.patch.yml#L414-L417`

**可信度**：【推断】（文档口径）；`maxInlineTokens: 12500` 为源码配置，【已核实】。

---

## 7. 历史裁剪（不调模型）

**做法**
dsh 的历史裁剪只有一个正式机制：`ctx.toolResultPruner`。它把当前 surface 上**超预算的工具结果**替换成「头 + 固定省略标记 + 尾」：默认超过 8192 个 Unicode 码点触发，保留头 4096、尾 1024，中间替换为 `\n\n[... tool result middle pruned ...]\n\n`；按码点切片（不会劈开代理对），富内容块保持顺序，图片的 offload 选择原样保留。替换事件保留工具调用、step、错误与元数据，只有 `content` 变；紧邻它之前会写一条 `compaction/prune` **影子计价事件**，把被替换节点按 token meter 计价，让纯投影消费者直接做减法。关键限制：**它只在压缩触发合格后运行**（pressure 或 overflow 确认之后、选区之前），低于压力的会话一个字节都不动；目的正是「先做无模型的削峰，可能因此完全不需要摘要」。除此之外**没有**按轮龄清理旧工具结果、没有把思考过程换占位符的机制（思考内容不在 surface 上，见 `assistant/attempt` 语义）。

**关键参数与默认值**

| 项 | 默认 |
|---|---|
| `thresholdChars` | `8192` |
| `headChars` | `4096` |
| `tailChars` | `1024` |
| 触发时机 | 仅 compaction 压力/溢出确认后 |
| 约束 | `head + marker + tail ≤ threshold`，否则加载即报错 |
| 原始事件 | 永久保留在日志中 |

**来源**
- 默认值与标记：`packages/compaction/compaction-tool-result-pruner/src/config.ts#L8-L13`
- 校验与切分口径：`packages/compaction/compaction-tool-result-pruner/src/config.ts#L43-L60`
- 行为与时机：`packages/compaction/compaction-tool-result-pruner/README.md#L12`、`#L48-L52`
- 影子计价与替换：`docs/subsystems/compaction.md#L105-L133`
- base 实际配置：`packages/bundle/base/cordis.patch.yml#L425-L430`

**可信度**：【已核实】

---

## 8. 压缩（调用模型做摘要）

**做法**
压缩被拆成「接缝 + 后端 + 人工消费者」三件：`ctx.compaction`（抽象 `CompactionEngine`）、`dsh-compaction-basic`（默认后端）、`dsh-command-compact`（`/compact`）。**三种调用方式**：`compactIfNeeded(agent, trigger, signal)`（自动，`trigger ∈ {pressure, context-overflow}`）、`compactNow(agent, signal, sourceCommandId?)`（手动，空闲维护通道，`turn: null` 括号）、`compactRegion(start, end, agent, signal?)`（显式区间，按 surface 位置而非 seq 大小）。一次成功压缩的事务是：`compaction/start`（日志锁）→ 摘要 → `compaction/summary`（含被遮蔽 seq 集合、token 数、模型与用量）→ 用**一条** `user/message` + `surfaceOp: { op: 'replace', startSeq, endSeq }` 替换选区（唯一的 surface 变更）→ `compaction/end`；崩溃会留下未配对的 start（可检测的孤儿锁），而不是假的成功。选区算法：从最新节点往前累加 token 直到达到 `retainTokens`，再往前挪到**工具调用/结果配对平衡**的位置，起点永远是「第一个不是 system 的节点」（系统提示词永不被遮蔽）。摘要提示词是 8 段固定结构（Primary Request / Key Technical Concepts / Files and Code / Errors and Fixes / Pending Jobs / Current Work / Next Step / Critical Context），输出放进 `<compacted-summary>`，前置一段固定 checkpoint 前言让模型「当作既定背景、不要复述」。摘要调用复用系统提示词、当前工具定义与被遮蔽区间，**逐字节对齐**上一请求，以命中 provider 的暖前缀缓存。多次压缩时要求模型「把旧 `<compacted-summary>` 的事实合并、丢弃过时项」，而不是原样搬运。摘要拒绝「不缩小源区间」的结果；pressure 路径默认重试 1 次，overflow 路径默认重试 1 次。

**关键参数与默认值**

| 项 | 默认 | 说明 |
|---|---|---|
| `thresholdRatio` | `0.8` | 见第 5 类 |
| `headroomTokens` | `65536` | 额外余量 |
| `retainRatio` | `0.16` | 与 `retainTokens` 互斥 |
| `maxTokens`（摘要输出） | = `headroomTokens` | 上限含推理 token |
| `compactionRetries` | `1` | pressure 下额外尝试 |
| `maxOverflowRetries` | `1` | overflow 后重试次数，`0` 只关闭恢复 |
| `auto` | `true` | `false` = 仅手动 |
| `summarizationProvider/Model` | `''` | 空则用最近路由目标，再用 `AgentOptions` |
| 压缩产物 | 一条 user 摘要 + 保留尾部 | — |
| `/compact` 参数 | **不接受参数**（`Usage: /compact (no arguments)`） | — |

**来源**
- 三种调用与触发器类型：`packages/compaction/compaction/src/index.ts#L31-L41`、`#L119-L193`
- 事务与错误码：`docs/subsystems/compaction.md#L9-L23`、`#L84-L103`
- 后端默认值与配置表：`packages/compaction/compaction-basic/README.md#L60-L78`
- 选区算法：`packages/compaction/compaction-basic/src/region.ts#L117-L155`
- 触发与重试循环：`packages/compaction/compaction-basic/src/index.ts#L158-L172`、`#L186-L234`、`#L269-L347`
- 手动路径：`packages/compaction/compaction-basic/src/index.ts#L383-L424`
- 摘要提示词全文与 checkpoint 前言：`packages/compaction/compaction-basic/README.md#L166-L225`
- 暖前缀复用：`packages/compaction/compaction-basic/README.md#L108`
- `/compact` 参数限制：`packages/compaction/command-compact/README.md#L32-L38`

**可信度**：【已核实】

**源码解读候选**：`selectCompactableRange()` —— 30 行同时解决「保留尾部预算」「工具调用成对」「系统提示词不入选」三个约束，且把所有价格判断交给 token meter。是「压缩切点」这一章最好的教学代码。

---

## 9. 多模态上下文

**做法**
图片不移出上下文，而是**在路由拒绝时永久 offload**：图片适配器（DeepSeek 的 file-mode / inline-fallback 预算、pi-ai 的 base64 界）在超预算时返回 `IMAGE_OFFLOAD_REQUIRED` 并附带需要移出的张数；`dsh-compaction-image-offload` 沿模型请求顺序遍历 surface，跳过 assistant 节点与已标记图片，标记恰好那么多**最早的**图片出现位置，每条决策追加一个 `image/offload` 事件（按当前消息事件 seq + 深度优先图片索引定位），消息事件与 surface 节点身份都不变；下一次投影时这些图片变成占位文本（附件名 + 可读路径），请求重试**不消耗 provider 重试预算**、也不写 `llm/retry`。选择跨路由、resume、replay 持久；重放或换路由后仍生效。新工具读取同一附件会产生新的出现位置，但不会「恢复」旧的。token meter 对已 offload 的位置按占位文本计价，所以 `contextBreakdown` 不变、路由价下降。摘要失败时也走同一条恢复瀑布（`compaction/summary-error`），只处理摘要选区内的图片，直到没有可移的为止。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 触发码 | `IMAGE_OFFLOAD_REQUIRED`（带 `offloadImages` 计数） |
| 配置 | **无**（预算由适配器决定） |
| 选择顺序 | 模型请求顺序中的最早出现，跳过 assistant |
| 事件 | `image/offload`，`{seq, imageIndexes}`，无 `surfaceOp` |
| 占位 | 附件名 + 可读路径的文本 |
| 失败委派 | 无可移图片时交给下一个 `agent/request-error` 监听器 |

**来源**
- 行为与恢复：`packages/compaction/compaction-image-offload/README.md#L12`、`#L30-L38`
- 事件结构与类型：`docs/subsystems/compaction.md#L25-L38`
- 默认在 base 启用：`packages/bundle/base/cordis.patch.yml#L432-L435`
- token 计价口径：`packages/llm/token-meter/README.md#L30`

**可信度**：【推断】

---

## 10. 子代理隔离

**做法**
`ctx.subagents` 是委派服务的注册表，provider 决定「子会话怎么跑」：`spawn`（全新进程内子代理）、`fork`（用父会话已完成历史播种的进程内子代理）、`acp`、`codex`、`claude-code`、`dsh-sdk`（进程外）。模型侧由 `tool-subagent` 暴露一个具名工具（默认 `subagent`，每个 provider 一个实例、名字必须不同）。**关键差异**：工具**不等待**结果——调用成功立即返回 `started subagent <childId>`，子任务由 runtime 独立持有，完成时通过**完成通知**把最终答案送回父会话；本地 spawn/fork 子代理还能收后续消息、被中断、或恢复，外部后端（Codex/Claude Code/ACP/SDK）只执行一次任务、不接受追问。递归深度由 `maxDepth` 控制（默认取 Host 设置 `1`，`0` 禁止委派），到顶后工具仍可见，但每次启动都会被拒绝并返回错误结果。子代理预设（`agentPreset` / `allowedAgentPresets`）可以给子会话一套独立插件树，但只有进程内 spawn 支持。**核心包里没有 worktree 隔离**——`worktree` 只在 `packages/experimental/worktree` 里。

**关键参数与默认值**

| 项 | 默认 | 说明 |
|---|---|---|
| `provider` | 必填 | `spawn` / `fork` / `acp` / … |
| `toolName` | `subagent` | 每个实例必须不同 |
| `maxDepth` | Host 设置 `1`；`0` 禁止 | `'provider-managed'` 交给外部 |
| 返回 | `started subagent <childId>` | 不阻塞 |
| 结果 | 完成通知携带最终答案 | 本地子代理另可 `send_message` |
| worktree | 无（实验包另计） | — |

**来源**
- 包族与 provider 列表：`packages/subagent/README.md#L12-L28`
- 工具行为、返回与 `maxDepth`：`packages/subagent/tool-subagent/README.md#L12`、`#L47-L53`
- 深度语义与拒绝：同上 `#L53`

**可信度**：【推断】

---

## 11. 会话时间线

**做法**
会话是**只追加的 `SessionEvent` 日志**，模型历史由 `deriveMessages()` 从「surface」派生：surface 是「产生消息的事件」的有序视图，每个消息事件必须带 `surfaceOp`——`append`（进入尾部）或 `{ op: 'replace', startSeq, endSeq }`（遮蔽一段既有节点）。`deriveMessages()` 走 surface 节点、按 `deriveEventMessage` 投影成 `Message`；被 replace 遮蔽的原始事件仍在日志里，但不再出现在派生历史中，因此**重放是确定性的**。缓存策略：纯尾部增长 O(新增节点)，只有 replacement 或消息投影变化（`contentGeneration` 变化）才整体重建；返回数组每次是新快照，`Message` 对象共享且深冻结。恢复：持久化后端读日志、`session-checkpoint-policy` 在每个模型请求前、每个顶层工具产生外部副作用前、下一步开始前刷盘（fail-closed：写不成功就不跑），崩溃后用合成 closer 收尾未完成的 turn/step（**没有**「继续未完成 turn」的部分恢复）。分叉：`buildForkSeed(events, boundary)` 复制到边界的**前缀**，追加一条 `session/end-seed { inherited: true }`，再用 `openTurnClosers` 补齐未闭合的 step/turn（`kind: 'forked'`）。**没有 `/rewind`、没有 undo、没有树状多分支**——回退能力在本版不存在。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 日志 | 追加式 `SessionEvent`，JSONL 后端（每会话一条压缩日志） |
| 模型历史 | `deriveMessages()` 从 surface 派生 |
| 表面操作 | `append` / `{ op:'replace', startSeq, endSeq }` |
| 检查点 | 模型请求前 / 顶层工具前 / 下一步前（fail-closed） |
| 分叉 | 前缀 + `session/end-seed` + 合成 closers |
| 回退 / undo | **无** |
| 崩溃恢复 | 追加合成 closer，不续跑未完成 turn |

**来源**
- `deriveMessages()` 与缓存：`packages/core/session/src/index.ts#L966-L1005`
- surface 类型与投影：`packages/core/session/src/surface.ts#L49-L56`、`#L108-L141`
- 日志/派生/重放：`docs/architecture.md#L123-L127`
- 检查点语义：`packages/session/session-checkpoint-policy/README.md#L12`
- 分叉构造：`packages/core/session/src/fork.ts#L1-L30`
- resume 与合成 closer：`packages/session/session-persistence/README.md#L12`、`#L155`

**可信度**：【已核实】（`deriveMessages` / `fork`）；「无 rewind」为**源码未找到**，【推断】。

**源码解读候选**：`deriveMessages()` + `surfaceOp` —— 用「日志 + 可见视图」两层结构同时满足「不可变审计」与「可压缩/可替换」，并且把缓存失效收敛到 `contentGeneration` 一个变量。

---

## 12. 跨会话记忆

**做法**
**无此能力**：仓库里没有记忆服务、没有 `MEMORY.md`/topic/observation 之类的持久知识库、没有 dream/flush 一类的整理任务，`docs/architecture.md` 的核心包表里也没有记忆项。跨会话能带过去的只有三样：① `AGENTS.md` 指令链（用户级 + 项目级，见第 2 类）；② 会话日志与 resume（同一会话续跑，不是跨会话知识）；③ `@session` 引用（手动把另一个会话的有界快照拉进当前轮，一次性、不可信、只读）。如果部署需要记忆，只能自己写一个 Cordis 插件，把内容注入 `agent/pre-step` 或贡献一个系统提示词 section。

**关键参数与默认值**：不适用。

**来源**
- 核心包清单无记忆项：`docs/architecture.md#L60-L66`
- `packages/` 目录下无 memory 包（`packages/context/*` 只有 time/file/session/tmux/harness-dev 等注入类插件）
- 跨会话仅 `@session` 快照：`packages/context/session-reference/README.md#L12`

**可信度**：【已核实】（以「不存在」为结论，依据是目录与架构文档；不排除第三方插件提供）

---

## 13. 缓存友好设计

**做法**
dsh 把「前缀稳定」写进了多个设计。① **系统提示词是 surface 节点**：内容不变就不重写；变化时按路由能力选择「原地替换节点 0」或「在缓存历史之后追加非空 update」（`systemPromptUpdate: 'in-history'`），后者专门为「保住已缓存前缀」而存在。② **plan mode 不改工具目录**：切模式只换提示词约束，工具 schema 保持不变（源码注释明确写为 request-cache stability）。③ **压缩调用复用暖前缀**：摘要请求逐字节复用系统提示词、当前工具定义与被遮蔽区间，只有尾部指令与摘要输出是未缓存的。④ **替换的代价被显式记录**：压缩、prune、image offload 都会从「第一个被替换的 token」起失效；文档在每处都标注了 KV cache 影响，并强调「替换而不是追加第二份」。⑤ **spill 不改已发送前缀**：只影响下一次请求的该条结果，历史里已发出的前缀不动。⑥ **日期等易变事实用注入而非改写**：`time-context` 作为新增 user 消息，不改系统提示词。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 系统提示词更新方式 | 原地替换 / `in-history` 追加（按路由能力） |
| 压缩 cache 影响 | 从首个被替换 token 失效，之前前缀仍可复用 |
| 摘要请求 | 前缀逐字节对齐上一路由请求 |
| plan mode | 工具目录跨模式不变 |

**来源**
- 系统提示词作为 surface 节点与两种更新：`docs/subsystems/system-prompt.md#L43`
- plan mode 缓存注释：`packages/bundle/base/cordis.patch.yml#L340`
- 摘要暖前缀：`packages/compaction/compaction-basic/README.md#L108`、`#L233`
- 压缩的 KV 影响：`packages/compaction/compaction/README.md#L148-L150`
- 图片 offload 的 cache 影响：`packages/compaction/compaction-image-offload/README.md#L12`

**可信度**：【推断】（文档口径）；plan mode 注释为源码，【已核实】。

---

## 14. 失败恢复

**做法**
溢出恢复只认**一种**信号：适配器把 provider 的上下文超限规范化成 `CONTEXT_WINDOW_EXCEEDED`，`agent/request-error` 监听器接住后：跳过常规阈值与保留策略，**先跑可选 pruner**，再选一个「最大的、平衡的头部区间」压缩，然后**只有当 surface 的 `replaceGeneration` 前进时才返回 retry**（否则原样抛出原错误）。重试次数由 `maxOverflowRetries` 限制（默认 1，`0` 只关闭恢复）。压缩失败的处理分阶段：替换之前失败 → 记 warning，带完整超预算历史继续（不阻断用户请求）；pruner 已落地但摘要失败 → 从**已落地的 pruned surface** 继续重试，不丢弃已获得的削减；摘要被 `maxTokens` 截断（隐藏推理吃掉了预算）按同一规则。取消始终优先：清理后抛出原始 abort 原因。**修不了的情况**（文档明确列举）：① 系统提示词/工具/会话前缀本身逼近窗口；② 单个不可分割的非工具节点（一条超长消息）；③ 工具单元里「不可裁剪的剩余部分」仍超窗口；④ 没有可用模型写摘要且还没有任何已路由请求（报「请配置 summarization provider/model 或先路由一次请求」）。手动路径的失败有封闭错误码集合 `busy / cancelled / changed / summary / commit / persistence`：`changed`、`summary` 会关闭并持久化失败尝试但不做替换；`commit` 可能已部分变更；`persistence` 表示内存括号已关但刷盘失败。

**关键参数与默认值**

| 项 | 默认 |
|---|---|
| 溢出识别 | `CONTEXT_WINDOW_EXCEEDED` |
| `maxOverflowRetries` | `1` |
| 重试条件 | `replaceGeneration` 前进 |
| 手动错误码 | `busy` / `cancelled` / `changed` / `summary` / `commit` / `persistence` |
| 摘要失败（替换前） | 记 warning，带完整历史继续 |
| 压缩锁 | 未配对 `compaction/start` = 孤儿锁，阻塞后续 |

**来源**
- overflow 恢复逻辑：`packages/compaction/compaction-basic/src/index.ts#L186-L234`
- 失败限制清单：`packages/compaction/compaction-basic/README.md#L235-L246`
- 手动错误码语义：`docs/subsystems/compaction.md#L86-L99`
- 恢复瀑布：`docs/subsystems/compaction.md#L258-L278`

**可信度**：【已核实】

---

## 15. 扩展点

**做法**
只有一层：**Cordis 插件**。「一切皆插件」——模型适配器、工具注册表、会话日志、agent 循环都是可替换的插件，注册即副作用，卸载自动回滚；没有需要打补丁的特权核心。组合单位是 **profile**（`web` / `headless` / `sdk` / `sdk-minimal` / `acp`）＋ **bundle**（配置行 + 代码的分发格式）＋ 有序 **patch**（按行 id 替换整段 config 或插入新行）；`dsh --profile web --dump-config` 能看到实际插件树，任何一行都能被上层 patch 覆盖。对上下文管理而言，可替换的接缝很具体：`ctx.compaction`（换压缩后端）、`ctx.toolResultPruner`（换裁剪器）、`ctx.systemPrompt`（加 section）、`ctx.skills`（加技能源）、`ctx.subagents`（加子代理 provider）、`agent/pre-step` / `agent/request-error` / `compaction/summary-error` 瀑布（拦截与恢复）。**Hooks 是兼容层不是原生扩展**：`dsh-hooks-claude-code` / `dsh-hooks-codex` 读取既有 `hooks.json`，只支持 command 类型（`http`/`mcp_tool`/`prompt`/`agent` 会被跳过并告警），能力限于「阻断并给模型看消息 / 附加额外上下文 / 要求停止」。自定义压缩的正确姿势是**继承 `CompactionEngine` 实现 `compactIfNeeded` / `compactNow` / `compactRegion`**，而 `dsh-compaction-basic` 只把 `summarize()` 留作子类钩子。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 插件框架 | Cordis |
| profile | `web` / `headless` / `sdk` / `sdk-minimal` / `acp` |
| 压缩自定义 | 继承 `CompactionEngine`（3 个抽象方法）；或覆写 `summarize()` |
| hooks | 仅 command 型；Claude Code / Codex 两套方言 |
| 配置覆盖 | profile bundles → `cordis.patch.yml` → home patch → `--patch` |

**来源**
- 「一切皆插件」与 profile/bundle/patch：`docs/architecture.md#L5-L30`
- 可替换接缝（compaction/pruner 服务）：`docs/subsystems/compaction.md#L1-L5`、`#L145-L252`
- hooks 能力边界：`packages/experimental/hook-protocol/README.md#L12-L20`
- `summarize()` 唯一子类钩子：`packages/compaction/compaction-basic/src/index.ts#L237-L257`

**可信度**：【已核实】（架构文档 + 代码）；hooks 部分【推断】。

---

## 16. 评估与可观测

**做法**
可观测靠**会话投影**而不是事后日志解析：`tokenUsage`（未缓存输入、输出、缓存读、缓存写）、`contextPressure`（最新上报 prompt、下一请求预估、窗口）、`contextBreakdown`（system / tools / messages 的启发式构成）三个投影键，客户端直接订阅；卸载插件时三个键一起消失。逐轮用量由 `deriveTurnTokenUsage(events)` 折叠出「每次尝试 + 整轮」的精确值，缺证据或计数冲突时返回空而不是猜。导出侧有 `dsh-session-telemetry-otel`（OTel logs；只在用户显式反馈后导出，`DISABLED` 模式不建传输），redaction 由部署方挂接。**没有内置评测框架/评测集**：`BENCHMARK.md` 只说明「用 Python SDK 的 `jsonrpc-agent` 最小变体，每个任务用独立 workspace 与 session id」——即提供跑法，不提供指标与对照。要做 A/B，只能自己消费上述投影 + 日志，比较 `contextPressure.projectedTokens`、压缩次数、`shadowedTokenCount`、溢出恢复次数与任务成功率。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 投影键 | `tokenUsage` / `contextPressure` / `contextBreakdown` |
| 逐轮折叠 | `deriveTurnTokenUsage(events)` |
| OTEL | `dsh-session-telemetry-otel`（反馈触发；`DISABLED` 不传输） |
| 评测框架 | **无**（`BENCHMARK.md` 只给运行方式） |

**来源**
- 三个投影与逐轮折叠：`packages/llm/token-meter/README.md#L34-L44`
- OTEL 模式：`packages/session/session-telemetry-otel/README.md#L12`
- 基准运行方式：`BENCHMARK.md#L1-L5`

**可信度**：【推断】（文档口径）；「无评测框架」为仓库内未找到，【推断】。

---

## 17. 社区插件 `dsh-compressor`（本票重点）

**做法**
`dsh-compressor` 是第三方（`lifeodyssey/dsh-compressor`，npm 包名与版本 `dsh-compressor@0.1.0`）的「Headroom 精简移植」：在下一轮之前**压缩过长的工具输出**，把原文存盘，给模型一个按需取回的工具。它不替换官方 spill，而是**与 spill 并存**——README 明确「Official spill left verbatim」，即已被 spill 处理过的结果不再二次压缩。挂载点按插件目录页描述是两个：`agent/pre-step`（在派生消息前改写 surface 上符合条件的 `tool/result` 节点，使 `Session.deriveMessages()` 看到压缩形态）与 `tools/post-execute`（新工具结果被接受时就压缩）；原文落 `$DSH_HOME/dsh-compressor/`，模型用 `compressor_retrieve`（参数为裸 hash 或带前缀）取回。内置 5 个 crusher：Log / Smart / Text / Search / Diff；代码感知（tree-sitter）与 Kompress（ONNX 长文）尚未接入。**没有文档化配置**，装上即生效。效果口径：作者在 20 个脱敏真实 DSH 会话上测得 `Session.deriveMessages()` 的 JSON 体积最多下降 20%。许可证：插件 MIT，`crates/headroom-*` 保持 Apache-2.0。对教程的意义：它是「不改宿主、只在 pre-step 改写 surface」这一扩展模式的活样本，也说明 dsh 的 surface 改写接口足够稳定，第三方能在不 fork 核心的情况下做上下文压缩。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 包名 / 版本 | `dsh-compressor@0.1.0`（npm） |
| 安装 | `dsh plugin --profile web add dsh-compressor`（或 `github:lifeodyssey/dsh-compressor#path:plugins/dsh-compressor`） |
| 挂载点 | `agent/pre-step`、`tools/post-execute`（据插件目录页） |
| 原文位置 | `$DSH_HOME/dsh-compressor/` |
| 取回工具 | `compressor_retrieve`（hash） |
| Crusher | Log / Smart / Text / Search / Diff（5 个） |
| 阈值 / 配置 | **未文档化**（README 无配置项） |
| 实测收益 | 20 个会话，`deriveMessages()` JSON 最多 −20% |
| 许可证 | 插件 MIT；`crates/headroom-*` Apache-2.0 |

**来源**
- 官方仓库 README：https://github.com/lifeodyssey/dsh-compressor
- 插件目录页（含挂载点与原文路径描述）：https://dshpluginhub.ai/en/plugins/dsh-compressor
- 中文导读（同一来源的改写）：https://deepseekharness.io/zh/plugins/dsh-compressor

**可信度**：仓库/包名/版本/收益/许可证/crusher 列表【已核实】（README 原文）；**挂载点、原文目录、取回参数**来自插件目录页对 README 的转述，未能读到插件源码，标【推断】；阈值与配置【待核实】（README 声明无配置）。

---

## 18. 本文档的【待核实】清单

1. **`dsh-compressor` 的挂载点与阈值**：未拿到插件源码（不在本机快照内），pre-step / post-execute 与 `$DSH_HOME/dsh-compressor/` 来自第三方目录页转述。
2. **dsh 是否有 `/context` 类命令**：`packages/` 内未找到斜杠命令实现，UI 只有 `ContextMeter` 面板；不排除某个 profile 的客户端另注册。
3. **`contextBreakdown` 的 `systemTokens` 归类**：文档说「surface 顺序里最后一条非空 `system/message`」，但多处 system 节点并存时的取舍细节未逐行核对实现。
4. **`dsh-hooks-*` 支持的具体事件表**：只核对了能力边界（阻断/附加上下文/停止）与「仅 command 型」，未逐一列出事件名。
