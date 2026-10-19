# opencode v1 · 上下文管理事实卡片

- **仓库**：https://github.com/anomalyco/opencode（原 `sst/opencode`）
- **提交号**：`733b2c627e5aec39cb33cc22373bdce33053ef2c`（tag `v1.19.0`）
- **核实日期**：2026-10-18
- **分析范围**：v1 出货路径 `packages/opencode/src/{session,tool,agent,provider,cli}`、`packages/plugin/src`、`packages/core/src/v1/config`。不分析服务端（opencode.ai 后端）的缓存命中与计费行为，不分析 TUI/桌面端的渲染细节。
- **Permalink 基址**：`https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/`
- **分界说明**：本快照的 `packages/core/src/session/*` 带 `@opencode/v2/*` 服务标签，属 v2 在建路径，**不作为 v1 行为证据**。唯一例外是 v1 出货代码显式引用的两个定义：摘要模板 `buildPrompt`（`session/compaction.ts` 第 23 行 import）与 `MAX_STEPS_PROMPT`（`session/prompt.ts` 第 19 行 import）；引用时单独标注"v1 引用的共享定义"。
- **交叉引用**：v1 → v2 的变化见 `research/opencode-v2.md` 的「附：v1 → v2 变化（跨版本对照）」一节。

---

## 1. 请求组装

**做法**
每一步请求都由主循环 `runLoop` **重新从 SQLite 投影**一遍历史，而不是在内存里追加。顺序是：`filterCompacted` 取"替代历史" → `SessionReminders.apply` 插入计划模式提醒 → 插件 `experimental.chat.messages.transform` 可改写消息 → 并行取四类系统块（环境 / 规则指令 / MCP 指令 / 技能清单）→ `toModelMessages` 转成 AI SDK 消息。四类块按 `env → instructions → mcp → skills` 的固定顺序拼成 `system` 数组，交给 `LLMRequestPrep.prepare`。`prepare` 再把 `agent.prompt`（没有就用 `SystemPrompt.provider(model)` 按模型挑基座提示词）、`input.system`、`user.system` 用 `\n` 合成**一条** system 字符串，作为最前面的 system 消息插入；OpenAI OAuth 与 workflow 例外，改用 `instructions` 字段。到达 `agent.steps` 上限的最后一轮，会在消息末尾追加一条 **assistant 角色**的 `MAX_STEPS_PROMPT`。工具集先按权限与 `user.tools` 过滤，再按名字排序后发出。

**关键参数与默认值**
- system 块顺序固定为 `env, instructions, mcp, skills`；结构化输出时再 push `STRUCTURED_OUTPUT_SYSTEM_PROMPT`
- `agent.prompt` 存在时**整段替换**基座提示词；不存在时按模型 ID 选：`muse→meta`、`gpt-4/o1/o3→beast`、`gpt-6→astra`、`gpt-codex→codex`、`gpt→gpt`、`gemini-→gemini`、`claude→anthropic`、`trinity`、`kimi`，默认 `default`
- 工具排序：按工具名字典序（`toSorted(localeCompare)`）
- 末步提示：`agent.steps` 默认未设 = `Infinity`（不追加）

**来源**
- [session/prompt.ts#L1081-L1341](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/prompt.ts#L1081-L1341)（主循环）
- [session/prompt.ts#L1255-L1269](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/prompt.ts#L1255-L1269)（四类系统块）
- [session/prompt.ts#L1279-L1286](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/prompt.ts#L1279-L1286)（末步提示）
- [session/llm/request.ts#L56-L112](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/llm/request.ts#L56-L112)（system 合成与消息拼接）
- [session/llm/request.ts#L184](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/llm/request.ts#L184)（工具排序）
- [session/system.ts#L28-L51](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/system.ts#L28-L51)（按模型选提示词）

**可信度**：【已核实】

**源码解读候选**：`LLMRequestPrep.prepare` 如何把"四块 + 基座 + 用户 system"折叠成一条 system 消息，以及为什么 OpenAI OAuth 要走另一条路。

---

## 2. 规则文件的发现与合并

**做法**
全局层只取**首个存在**的文件：`~/.config/opencode/AGENTS.md`，退而 `~/.claude/CLAUDE.md`。项目层按候选名顺序 `AGENTS.md → CLAUDE.md → CONTEXT.md（已废弃）` 逐类 `findUp`，**第一个有命中的类型**生效，并把这一个类型沿目录向上找到的**所有**匹配文件都加入（不是只取最近一个）；注释明确写了"避免把每一级祖先的 AGENTS.md/CLAUDE.md 都堆进来"。`config.instructions` 可以追加文件（绝对路径、`~/`、相对 glob）和 `http(s)` URL，URL 抓取有 5 秒超时。合并方式就是**简单拼接**：每个文件渲染成 `Instructions from: <path>\n<content>`，按 Set 插入顺序连接，没有优先级覆盖、没有去重合并。另有"就近规则"：`read` 工具每读一个文件，从该文件目录向上找到项目根（不含），把沿途的规则文件以 `<system-reminder>` 追加进**这次工具输出**，并按"每条助手消息 + 每个路径"去重一次。体积上限与截断未在源码中找到。

**关键参数与默认值**
- 全局候选：`<config>/AGENTS.md`、`~/.claude/CLAUDE.md`（首个存在者生效）
- 项目候选：`AGENTS.md`、`CLAUDE.md`、`CONTEXT.md`（deprecated），按序首个命中类型生效
- 开关：`OPENCODE_DISABLE_PROJECT_CONFIG` 关闭项目层；`disableClaudeCodePrompt` 关闭 `CLAUDE.md` 候选
- URL 抓取超时：5000 ms；并发：文件 8、URL 4
- 体积上限/截断：**未在源码中找到**

**来源**
- [session/instruction.ts#L60-L68](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/instruction.ts#L60-L68)（候选清单）
- [session/instruction.ts#L110-L153](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/instruction.ts#L110-L153)（全局首个 / 项目 findUp / config.instructions）
- [session/instruction.ts#L155-L169](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/instruction.ts#L155-L169)（拼接与 URL）
- [session/instruction.ts#L179-L221](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/instruction.ts#L179-L221)（就近规则）
- [tool/read.ts#L300](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/read.ts#L300)、[tool/read.ts#L355-L356](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/read.ts#L355-L356)（就近规则注入工具输出）

**可信度**：【已核实】；"体积无上限"为【推断】（只证明未找到截断代码）

---

## 3. 按需加载（渐进披露）

**做法**
技能是标准的三段式：发现 `skills/**/SKILL.md`，系统提示词里只放 `Skill.fmt(list, {verbose:true})` 渲染的清单（名称、描述、位置），正文由 `skill` 工具按名字读取后返回 `<skill_content>` 块。MCP 这一侧默认**没有**按需加载：服务端暴露的每个工具都注册成完整工具定义进入请求，系统提示词只额外附上各 server 的 `instructions`（`<mcp_instructions>`）；只有打开实验开关 `experimentalCodeMode` 时才会多出一个 `execute` 工具，并在它的 description 里附带 MCP 工具目录。`@` 引用由 `resolvePromptParts` 在入场时解析：文本中的 `@name` 若能 stat 到文件就转成 `file` part，否则尝试当作 agent 名；解析结果直接作为用户消息的附件，不是延迟加载。因此 v1 的"按需"默认只有技能正文与 `read/grep/glob` 的主动检索两条路。

**关键参数与默认值**
- 技能清单：`Skill.fmt(..., { verbose: true })`；`skill` 工具被权限禁用时整块省略
- MCP：仅当 server 有 `instructions` 时注入；工具被权限全禁的 server 不注入
- `@` 解析：`~/` 展开为 home，其余相对 `worktree`；目录 mime 记为 `application/x-directory`

**来源**
- [session/system.ts#L107-L119](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/system.ts#L107-L119)（技能清单）
- [tool/skill.ts#L1-L50](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/skill.ts#L1-L50)（技能正文）
- [session/system.ts#L121-L137](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/system.ts#L121-L137)（MCP 指令）
- [session/prompt.ts#L157-L191](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/prompt.ts#L157-L191)（`@` 引用解析）

**可信度**：【已核实】；"默认无 MCP 延迟加载"依据 [tool/registry.ts#L291-L340](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/registry.ts#L291-L340) 与 [tool/registry.ts#L280-L289](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/registry.ts#L280-L289)（code mode 仅在 `experimentalCodeMode` 下加载）

---

## 4. 动态注入

**做法**
唯一的固定注入是"模式提醒"：`SessionReminders.apply` 在每轮请求前，把计划模式提示（`PROMPT_PLAN`）、或"计划模式 → 构建模式"的切换提示（`BUILD_SWITCH`）、或实验特性下的 `PLAN_MODE`（含计划文件路径），作为 `synthetic: true` 的 text part **追加到最近一条用户消息的 parts 末尾**，因此不改写历史消息，只改这一轮投影。规则变更没有增量机制：系统块每步从磁盘重读并整段重拼，改一个字就等于换掉整个 system。todo 状态不自动注入——v1 有 `todowrite` 工具，但本卡片范围内未找到把 todo 列表注入 system 或 reminder 的代码。插件可以在 `experimental.chat.messages.transform` 里对投影后的消息做任意改写（包括插入 synthetic 消息）。

**关键参数与默认值**
- `experimentalPlanMode` 关闭（默认）时：plan agent 追加 `PROMPT_PLAN`；plan→build 时追加 `BUILD_SWITCH`
- `experimentalPlanMode` 打开时：用 `PLAN_MODE`，内插计划文件路径（存在/不存在两种文案）
- 注入位置：最后一条 user 消息的 parts 尾部，`synthetic: true`
- 规则变更增量：**无**（每步整段重算）

**来源**
- [session/reminders.ts#L15-L90](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/reminders.ts#L15-L90)
- [session/prompt.ts#L1180-L1184](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/prompt.ts#L1180-L1184)（调用点）
- [session/prompt.ts#L1255](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/prompt.ts#L1255)（插件改写）

**可信度**：【已核实】；"todo 不注入"为【推断】（检索 `prompt.ts` / `system.ts` 未见 todo 文案）

---

## 5. Token 计量与可视化

**做法**
本地估算只有一个公式：`Token.estimate(text) = round(len / 4)`，字符数除以 4，不区分中英文、不区分代码密度。触发判定不用估算值，而用**上一轮 provider 真实回报的 usage**：`count = tokens.total || (input + output + cache.read + cache.write)`。可用窗口 `usable` 的计算是：模型有 `limit.input` 时用 `limit.input - reserved`，否则用 `limit.context - maxOutputTokens`；`reserved` 默认取 `min(20000, maxOutputTokens)`，可被 `compaction.reserved` 覆盖。因此 v1 是"**实测驱动**"的触发：没有 provider 回报之前不会自动压缩，估算只用于压缩时挑选保留尾部。可视化方面，会话与消息都带 `tokens`（input/output/reasoning/cache.read/cache.write）与 `cost`，由 `Session.getUsage` 从 provider usage 换算；未找到类似 `/context` 的分项占用视图。

**关键参数与默认值**
- `CHARS_PER_TOKEN = 4`（`round`，最小 0）
- `COMPACTION_BUFFER = 20_000`；`reserved = cfg.compaction.reserved ?? min(20000, maxOutputTokens)`
- 触发条件：`count >= usable`，且 `compaction.auto !== false`，且 `limit.context !== 0`
- token 记账字段：`input / output / reasoning / cache.read / cache.write` + `cost`

**来源**
- [util/token.ts#L3-L5](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/core/src/util/token.ts#L3-L5)（估算公式）
- [session/overflow.ts#L8-L34](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/overflow.ts#L8-L34)（usable 与 isOverflow）
- [session/session.ts#L338](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/session.ts#L338)（getUsage）
- [session/processor.ts#L452-L470](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/processor.ts#L452-L470)（step-finish 写 tokens）

**可信度**：【已核实】；"无 `/context` 视图"为【待核实】（只检索了 `packages/opencode/src`，未穷举前端命令表）

---

## 6. 单次工具输出控制

**做法**
所有工具输出走同一个入口 `Truncate.output`：先看是否同时满足"行数 ≤ maxLines 且字节 ≤ maxBytes"，满足就原样返回；不满足时按行累加字节，**行数或字节先到者**截断，支持 `head`（默认）与 `tail` 两个方向，按整行切片所以不会切断多字节字符。被截断时把**完整原文**写入截断目录（文件名 `tool_<升序 ID>`），返回"预览 + `...N lines/bytes truncated...` + 提示"，提示分两种：有 `task` 工具权限时建议交给 explore 子代理处理，否则建议用 `Grep` 或 `Read` 的 offset/limit 回读。目录保留 7 天，每小时清理一次，只删 `tool_` 前缀文件。压缩序列化时还有第二道更严的限长：工具结果按 **2000 字符** 截断并追加 `\n[truncated]`。

**关键参数与默认值**
- `MAX_LINES = 2000`、`MAX_BYTES = 50 * 1024 = 51200`、`RETENTION = 7 天`
- `direction` 默认 `"head"`（`tail` 由 bash 等调用方显式传）
- 配置覆盖：`tool_output.max_lines` / `tool_output.max_bytes`
- 压缩期二次限长：`TOOL_OUTPUT_MAX_CHARS = 2000`（按 UTF-16 长度切，可能切开代理对）

**来源**
- [tool/truncate.ts#L12-L17](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/truncate.ts#L12-L17)（常量）
- [tool/truncate.ts#L85-L141](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/truncate.ts#L85-L141)（截断与落盘）
- [tool/truncate.ts#L75-L83](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/truncate.ts#L75-L83)（配置读取）
- [session/compaction.ts#L30](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L30)、[session/compaction.ts#L51-L52](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L51-L52)（二次限长）

**可信度**：【已核实】

**源码解读候选**：`Truncate.output` 的"先到者"循环 + 落盘提示分支——为什么"卸载到文件"比"直接截断"更省上下文。

---

## 7. 历史裁剪（不调用模型）

**做法**
v1 只有一种不调模型的裁剪：`compaction.prune`，且**默认关闭**。开启后从最新消息往回扫：数到第 2 个 user turn 才开始动手；遇到已完成压缩的 assistant 摘要就停；对每个已完成工具结果累加估算 token，前 40000 token 受保护不动，超过部分才计入"可擦"，且只有可擦总量 **> 20000 token** 才真的写回。擦除方式是给 part 打 `state.time.compacted = Date.now()`，原文仍在库里，只是序列化时显示 `[Old tool result content cleared]`。`skill` 工具的输出永远不擦。调用点在主循环**退出之后**（`runLoop` 末尾 fork），不是在压缩之前同步跑。没有针对"过期文件读取""空搜索结果""思考过程"的专门裁剪。

**关键参数与默认值**
- `PRUNE_PROTECT = 40_000`、`PRUNE_MINIMUM = 20_000`、`PRUNE_PROTECTED_TOOLS = ["skill"]`
- 开关：`compaction.prune`，默认 **false**
- 触发时机：一轮任务循环结束、准备返回时异步执行；至少保留最近 2 个 user turn 内的工具输出

**来源**
- [session/compaction.ts#L28-L33](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L28-L33)（常量）
- [session/compaction.ts#L271-L317](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L271-L317)（prune 实现）
- [session/compaction.ts#L76-L78](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L76-L78)（擦除后的占位文本）
- [session/prompt.ts#L1338](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/prompt.ts#L1338)（调用点）
- [v1/config/config.ts#L149-L168](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/core/src/v1/config/config.ts#L149-L168)（配置项与默认值注释）

**可信度**：【已核实】

---

## 8. 压缩（调用模型做摘要）

**做法**
自动触发有两个入口：主循环里"上一轮已结束且 `isOverflow`"时 `compaction.create({auto:true})`；以及 `step-finish` 时 `isOverflow` 置 `needsCompaction`，由 `process()` 返回 `"compact"` 后主循环再 `create({auto:true, overflow:!finish})`。手动入口是斜杠命令 `/compact`（命令 id `session.compact`，slash 名 `compact`）；服务端的压缩入口是 `session.summarize`（`auto` 默认 false），处理器以 `auto:false` 建压缩条目再跑一次 loop。真正的压缩由 `process` 完成：先用 `select` 从最新 turn 往回挑出"保留尾部"，预算按 `preserve_recent_tokens ?? clamp(usable×0.25, 2000, 15000)`，可选 `tail_turns` 限制候选 turn 数，切点只落在消息边界（不够整 turn 时用 `splitTurn` 在 turn 内部找切点），并把起点记到压缩 part 的 `tail_start_id`。被摘要的部分序列化成文本（tool 结果再按 2000 字符限长），拼上 `buildPrompt(previousSummary, conversation)` 发给隐藏的 `compaction` agent；前一次摘要以 `<prior-summary>` 形式合并，规则是"没带过来的就丢了、冲突时以新对话为准"。插件 `experimental.session.compacting` 可以注入 context 或整体替换 prompt。压缩成功后（`auto` 时）追加一条 synthetic 的"continue"用户消息；插件 `experimental.compaction.autocontinue` 可关闭。`overflow` 模式下会先把触发溢出的那条用户消息及其媒体剥掉再压，压完把这条消息**重放**回去。

**关键参数与默认值**
- 配置：`compaction.auto`（默认 true，仅 `=== false` 时关）、`prune`（false）、`tail_turns`（未设 = 不限）、`preserve_recent_tokens`（未设 = `clamp(usable×0.25, 2000, 15000)`）、`reserved`（未设 = `min(20000, maxOutputTokens)`）
- 保留预算上下限：`MIN_PRESERVE_RECENT_TOKENS = 2000`、`MAX_PRESERVE_RECENT_TOKENS = 15000`
- 摘要模板：`Objective / Important Details / Work State{Completed,Active,Blocked} / Next Move / Relevant Files`
- 压缩 agent：`compaction`，`mode: primary`、`hidden: true`、权限 `"*": deny`
- 自动续跑文案：`"Continue if you have next steps, or stop and ask for clarification if you are unsure how to proceed."`，part 带 `metadata.compaction_continue = true`
- 多次压缩：隐藏上一对"压缩 user + 摘要 assistant"，`previousSummary` 取最近一条

**来源**
- [session/prompt.ts#L1149-L1168](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/prompt.ts#L1149-L1168)（任务分支与自动触发）
- [session/prompt.ts#L1320-L1328](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/prompt.ts#L1320-L1328)（result=compact）
- [session/processor.ts#L491-L496](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/processor.ts#L491-L496)（step-finish 溢出）
- [session/compaction.ts#L115-L120](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L115-L120)（保留预算）
- [session/compaction.ts#L223-L269](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L223-L269)（select 与 tail_turns）
- [session/compaction.ts#L319-L557](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L319-L557)（process：overflow 重放、提示词、续跑）
- [session/compaction.ts#L559-L582](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L559-L582)（create 建压缩条目）
- [core/session/compaction.ts#L16-L55](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/core/src/session/compaction.ts#L16-L55)、[core/session/compaction.ts#L160-L174](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/core/src/session/compaction.ts#L160-L174)（**v1 引用的共享定义**：模板与增量规则）
- [agent/agent.ts#L219-L233](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/agent/agent.ts#L219-L233)（compaction agent）
- [app/src/pages/session/use-session-commands.tsx#L479-L484](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/app/src/pages/session/use-session-commands.tsx#L479-L484)（`/compact`）
- [server/routes/instance/httpapi/handlers/session.ts#L273-L291](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/server/routes/instance/httpapi/handlers/session.ts#L273-L291)（summarize 处理器）

**可信度**：【已核实】

**源码解读候选**：`select` + `splitTurn` 如何在"整 turn 边界"和"预算"之间找切点；`process` 的 overflow 重放分支。

---

## 9. 多模态上下文

**做法**
图像/PDF 作为 `file` part 直接进用户消息或工具结果；工具返回的图片附件会先过 `image.normalize`（缩放/格式归一），失败则原样保留。压缩序列化时，图片变成一行文本 `[Attached <mime>: <filename>]`，不进摘要请求。真正"把图片移出上下文"的只有 overflow 路径：压缩完成后重放触发溢出的用户消息时，`isMedia(mime)` 的 file part 会被替换成 `[Attached mime: name]` 文本，并补偿一段"附件过大、请重试更小的文件"的说明。没有按字节预算主动移除历史图片的机制，也没有"把历史渲染成图片"的做法。

**关键参数与默认值**
- 支持图片 mime：`image/jpeg`、`image/png`、`image/gif`、`image/webp`（`tool/read.ts` 常量）
- 压缩序列化占位：`[Attached <mime>: <filename|file>]`
- overflow 重放占位：同上，另加一段附件过大的解释文案
- 图片字节预算：**未在源码中找到**

**来源**
- [session/compaction.ts#L61-L64](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L61-L64)（压缩序列化占位）
- [session/compaction.ts#L484-L487](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L484-L487)（overflow 重放替换媒体）
- [session/processor.ts#L390-L400](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/processor.ts#L390-L400)（工具图片归一化）
- [tool/read.ts#L19](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/read.ts#L19)（支持的图片类型）

**可信度**：【已核实】；"无字节预算"为【推断】

---

## 10. 子代理隔离

**做法**
`task` 工具为子代理新建一个**子会话**（`parentID` 指向当前会话），子会话从空上下文开始，用自己的 agent 提示词，只拿到 `subagent_type` 指定的 agent。深度按 `parentID` 链计算，默认上限 1（子代理不能再开子代理），超过直接报错。子会话默认禁用 `todowrite` 与 `task`（除非该 agent 自己显式授权），并把 `experimental.primary_tools` 里的工具一并禁掉。返回给父代理的是固定 XML：`<task sessionID="..." state="completed|running">` + `<task_result>` 或 `<task_error>`，是**自由文本包在结构化信封里**，没有字段级 schema。默认前台执行；`background: true` 需要 `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true` 才允许，否则报错。前台执行过程中如果任务被提升为后台（`waitForPromotion`），工具会提前返回 `state="running"`，完成后再由后台通知把结果以 synthetic 消息注入父会话。未见 worktree 级隔离。

**关键参数与默认值**
- `subagent_depth` 默认 **1**（顶层配置项）
- 子会话额外拒绝：`todowrite`、`task`、`experimental.primary_tools[*]`
- `background` 默认 false；为 true 时要求 `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true`
- 返回信封：`<task id state><summary><task_result|task_error>...</></task>`
- worktree 隔离：**未在源码中找到**

**来源**
- [tool/task.ts#L43-L62](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/task.ts#L43-L62)（参数）
- [tool/task.ts#L64-L79](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/task.ts#L64-L79)（返回信封）
- [tool/task.ts#L92-L117](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/task.ts#L92-L117)（背景开关与深度限制）
- [tool/task.ts#L136-L172](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/tool/task.ts#L136-L172)（子会话创建与权限）
- [v1/config/config.ts#L84-L86](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/core/src/v1/config/config.ts#L84-L86)（`subagent_depth` 默认 1）

**可信度**：【已核实】

---

## 11. 会话时间线

**做法**
磁盘上的原始消息从不在压缩时删除：消息与 part 写入 SQLite（事件溯源 + 投影），读取按 `time_created` 倒序分页再翻正序。模型可见层由 `filterCompacted` 现场重排：找到"带 `tail_start_id` 的压缩条目"，再找它对应的摘要 assistant 消息，输出顺序变成 `[压缩 user, 摘要 assistant, 从 tail_start_id 起的保留段, 之后的新消息]`。**检查点内容** = 一条 user 消息（parts 里含 `type:"compaction"`，带 `auto` / `overflow` 两个布尔）+ 一条 `summary: true` 的 assistant 消息 + 压缩 part 上的 `tail_start_id`。恢复走持久化断点路线：`--continue` / `--session <id>` 载入后第一步就 `filterCompacted`，不重放历史重算。`--fork` / `Session.fork` 新建会话逐条复制消息并重映射 ID，`tail_start_id` 一并重映射。分支只有 `parentID` 一层（子会话），没有树状分支多选；回退是独立的 `revert` 机制（文件回滚），与压缩无关。

**关键参数与默认值**
- 存储：SQLite（`MessageTable` / `PartTable`），分页游标 `time_created`
- 检查点：`CompactionPart{type:"compaction", auto:boolean, overflow?:boolean, tail_start_id?:MessageID}`
- 替代历史顺序：`压缩条目 → 摘要 → 保留段 → 后续`
- CLI：`--continue`（继续最近会话）、`--session <id>`、`--fork`（必须与 `--continue` 或 `--session` 同用）
- 树状分支：**无**（只有 `parentID` 单亲）

**来源**
- [session/message-v2.ts#L534-L585](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/message-v2.ts#L534-L585)（filterCompacted）
- [session/message-v2.ts#L438-L478](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/message-v2.ts#L438-L478)（分页读）
- [session/compaction.ts#L559-L582](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L559-L582)（压缩条目字段）
- [session/compaction.ts#L461-L466](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L461-L466)（写回 tail_start_id）
- [session/session.ts#L691-L731](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/session.ts#L691-L731)（fork 与 tail 重映射）
- [cli/cmd/tui.ts#L123-L135](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/cli/cmd/tui.ts#L123-L135)、[cli/cmd/tui.ts#L229-L230](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/cli/cmd/tui.ts#L229-L230)（CLI 参数）

**可信度**：【已核实】

---

## 12. 跨会话记忆

**无此能力。** 依据：在 v1 出货路径 `packages/opencode/src` 与 v1 命名空间 `packages/core/src/v1` 中检索 `memory`，只命中 xai 插件的模型字段、`cli/heap.ts`（堆内存）与 beast 提示词文本，没有记忆写入/检索/整理模块；也没有与 `AGENTS.md` 之外的项目级持久知识注入路径。

**可信度**：【已核实】（限定于上述两个源码树；不排除插件生态提供）

---

## 13. 缓存友好设计

**做法**
`applyCaching` 在把消息交给 provider 前，给"前 2 条 system 消息"和"后 2 条非 system 消息"打 provider 级 ephemeral 缓存标记（按 provider 映射成 `cacheControl` / `cachePoint` / `cache_control` / `copilot_cache_control`）。前缀稳定性靠两点维持：工具定义按名字排序（顺序不随 map 插入序漂移）、system 由固定顺序的块拼成；但**任何一块内容变化都会让整条 system 字符串变化**，前缀立即失效。末尾追加的 synthetic 提醒只改最后一条用户消息，属于"只在尾部追加"的友好做法。OpenAI 兼容系另设 `promptCacheKey = sessionID`，请求头带 `x-session-affinity` / `X-Session-Id`。压缩与缓存的关系：压缩会替换整个前缀，必然全额失效，v1 没有任何"围绕缓存做压缩调度"的逻辑。

**关键参数与默认值**
- 缓存点：前 2 条 system + 后 2 条非 system（去重后打标）
- 缓存类型：`ephemeral`（Anthropic/OpenRouter/OpenAI 兼容/Alibaba）、`default` cachePoint（Bedrock）、`copilot_cache_control`（Copilot）
- `promptCacheKey` / `prompt_cache_key` = `sessionID`（可按 provider 选项 `setCacheKey` 关闭或强制）
- 服务端命中率与 TTL：不可观测

**来源**
- [provider/transform.ts#L357-L404](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/provider/transform.ts#L357-L404)（applyCaching）
- [provider/transform.ts#L1324-L1334](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/provider/transform.ts#L1324-L1334)（缓存键）
- [session/llm/request.ts#L187-L206](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/llm/request.ts#L187-L206)（亲和头）

**可信度**：【已核实】（客户端侧）；服务端行为【待核实】

---

## 14. 失败恢复

**做法**
普通错误走有界重试：最多 5 次，退避 `2000ms × 2^(n-1) × (1 + 0.25·rand)`，没有 `retry-after` 头时单次间隔上限 30 s；`ContextOverflowError` **不重试**，而是转成压缩信号。溢出有两条路：`step-finish` 时时 `isOverflow` 置 `needsCompaction`，或 provider 直接抛 `ContextOverflowError` 时 `halt` 里置 `needsCompaction`。如果 `compaction.auto === false` 且当前不是摘要消息，则直接报错并置 idle，不做任何压缩。压缩自身也可能溢出：`process` 返回 `"compact"` 时写入 `ContextOverflowError`（"Session too large to compact…"）并返回 `"stop"`，此时没有第二次兜底。中断时未结算的工具被标成 `error` + `metadata.interrupted`；连续 3 次相同工具 + 相同输入触发 `doom_loop` 权限询问（默认 ask）。

**关键参数与默认值**
- `RETRY_MAX_RETRIES = 5`、`RETRY_INITIAL_DELAY = 2000`、`RETRY_BACKOFF_FACTOR = 2`、`RETRY_JITTER_FACTOR = 0.25`、`RETRY_MAX_DELAY_NO_HEADERS = 30_000`
- `DOOM_LOOP_THRESHOLD = 3`，权限动作 `doom_loop` 默认 `ask`
- 溢出 → 压缩 → 失败：`ContextOverflowError` + `finish = "error"` + `stop`，无二次兜底
- 自动压缩关闭时溢出：直接报错

**来源**
- [session/retry.ts#L26-L31](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/retry.ts#L26-L31)（重试常量）
- [session/processor.ts#L613-L639](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/processor.ts#L613-L639)（halt 与溢出分支）
- [session/processor.ts#L693-L695](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/processor.ts#L693-L695)（返回 compact/stop）
- [session/compaction.ts#L450-L459](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L450-L459)（压缩失败兜底）
- [session/processor.ts#L29](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/processor.ts#L29)、[session/processor.ts#L356-L380](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/processor.ts#L356-L380)（doom loop）

**可信度**：【已核实】

---

## 15. 扩展点

**做法**
插件接口 `Hooks` 覆盖上下文链路的多个位置。与上下文直接相关的：`chat.message`（新用户消息的 parts 可改）、`chat.params` / `chat.headers`（温度、topP、maxOutputTokens、请求头）、`experimental.chat.system.transform`（system 数组可改，且会把多段重新折成两段）、`experimental.chat.messages.transform`（投影后的消息可改，压缩序列化前也会触发一次）、`experimental.session.compacting`（注入 context 或整体替换压缩提示词）、`experimental.compaction.autocontinue`（压缩后是否加 synthetic continue）、`tool.execute.before/after`（工具参数与结果）、`tool.definition`（工具描述与参数）、`shell.env`、`experimental.text.complete`、`experimental.provider.small_model`。没有"自定义压缩算法"这类更深的钩子——压缩的选尾、裁剪、重建仍是内建逻辑，插件只能改提示词与上下文。

**关键参数与默认值**
- `experimental.compaction.autocontinue.enabled` 默认 **true**
- `experimental.session.compacting.prompt` 为 undefined 时用内置 `buildPrompt`；设置后整体替换
- `experimental.chat.system.transform` 后若数组长度 > 2 且首段未变，会合并成 `[header, rest.join("\n")]`

**来源**
- [plugin/src/index.ts#L222-L335](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/plugin/src/index.ts#L222-L335)（Hooks 全量）
- [session/llm/request.ts#L69-L78](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/llm/request.ts#L69-L78)（system.transform 调用点）
- [session/compaction.ts#L373-L391](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L373-L391)（compacting 钩子）
- [session/compaction.ts#L500-L517](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L500-L517)（autocontinue 钩子）

**可信度**：【已核实】

---

## 16. 评估与可观测

**做法**
可观测性限于"记账 + 事件"：每条 assistant 消息带 `tokens`（含 cache 读写）与 `cost`，`step-finish` 会写一条带 tokens/cost/snapshot 的 part；会话级错误通过 `Session.Event.Error` 发到事件总线；压缩成功发 `Session.Compacted` 事件。没有内置的评测集、指标定义、A/B 分流或策略对比工具——无法在源码里找到"用数据证明某种压缩策略更好"的能力。想评估只能外部采集：从 SQLite 读消息与 tokens，或用事件流自己统计压缩前后的轮次、token 曲线与失败率。

**关键参数与默认值**
- 记账粒度：per-step（tokens + cost + snapshot）
- 事件：`Session.Event.Error`、`Session.Compacted`
- 评测集 / 指标 / A/B：**未在源码中找到**

**来源**
- [session/processor.ts#L452-L470](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/processor.ts#L452-L470)
- [session/session.ts#L338](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/session.ts#L338)
- [session/compaction.ts#L552-L556](https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/session/compaction.ts#L552-L556)

**可信度**：【已核实】（记账与事件存在）；"无评测能力"为【推断】
