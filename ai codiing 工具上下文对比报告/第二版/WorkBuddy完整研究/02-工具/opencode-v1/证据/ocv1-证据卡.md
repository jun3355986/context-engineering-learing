---
title: OpenCode v1 · 证据卡
task: T09
role: 工具研究 Agent
created: 2026-10-15
snapshot: 733b2c627e5aec39cb33cc22373bdce33053ef2c   # tag v1.19.0（只读）
spec: 08-验收/T07-后六工具样本规范.md §2
---

# OpenCode v1 · 证据卡

> 结论ID 前缀 `ocv1-*`。字段依规范 §2（**含"不能证明"必填**）。链接基址 `https://github.com/anomalyco/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/`。
> **v1/v2 分界**：除 `ocv1-version-02`（专述边界）外，所有卡仅引 `packages/opencode/src/*`（v1）与 `packages/core/src/v1/*`（v1 命名空间）。`packages/core/src/session/*` 为**混合目录**：带 `@opencode/v2/*` 标签部分仅作边界声明引用；**无标签且被 v1 实际使用**的文件（如 `compaction.ts` 的 `buildPrompt`）正常引用并标注定义位置。
> **计数**：本文件共 **25** 张卡（见文末计数核对）。

---

## 一、身份与版本

### ocv1-version-01
- **结论**：OpenCode v1 的研究快照为 tag `v1.19.0`、SHA `733b2c627e5aec39cb33cc22373bdce33053ef2c`；快照内 `packages/opencode/package.json` 与 `packages/core/package.json` 的 `version` 均为 `1.19.0`；本地可执行 `opencode --version` 自报 `1.19.0`（版本号一致）。
- **性质**：事实
- **范围**：仓库 `github.com/anomalyco/opencode` tag v1.19.0；本地 `/Users/junjielong/.opencode/bin/opencode`
- **实现状态**：默认（身份口径）
- **来源**：`00-管理/版本表.md` §1/§2；`git rev-parse HEAD`=`733b2c6…`、`git describe --tags`=`v1.19.0`；`packages/opencode/package.json:version`；`opencode --version`（`exit 0`）
- **数据走查**：—
- **运行证据**：`OBS-ocv1-token-01` 附带记录本地 `opencode --version=1.19.0`；版本三重口径见 `过程观察.md` §3
- **不能证明**：版本号一致 **不代表**"本地可执行与快照是同一份代码"；本包未在本地跑任何 v1 端到端机制
- **冲突裁决**：支持版本表 Q1（v1=`v1.19.0`）
- **核验日期**：2026-10-15

### ocv1-version-02
- **结论**：v1.19.0 快照内**同时**含 v1 出货路径（`packages/opencode/src/session/*`）与一份**带 `@opencode/v2/*` 服务标签**的在建路径（`packages/core/src/session/*`、`packages/core/src/session/runner/*`）；`packages/opencode` 对该 runner **零引用**。
- **性质**：事实
- **范围**：快照 `733b2c6`（tag v1.19.0）
- **实现状态**：默认（边界事实）
- **来源**：`packages/core/src/session/runner/index.ts:28`（`Context.Service<…>("@opencode/v2/SessionRunner")`）；`packages/core/src/session.ts:182`（`"@opencode/v2/Session"`）；`packages/core/src/session/compaction.ts:1`；`packages/opencode` 全包检索：**`SessionRunner` 零命中**（该 runner 未被引用）；但 **`core/session/runner` 1 处**（`prompt.ts:19` 导入 `MAX_STEPS_PROMPT`、`prompt.ts:1281` 使用）与 **`session/execution` 3 处**（`server.ts:67-68`、`server.ts:301`（`Layer.provide` 使用）、`session.ts:14`）；v1 服务端**实例化 v2 标签服务** `SessionV2`（`server.ts:299`）、`SessionExecution`（`server.ts:301`）、`SessionProjector`（`app-runtime.ts:80`）——**同源 ≠ 零耦合**（2026-10-15 依 T09R P1 更正）；`packages/opencode/src/session/session.ts:13-14` 的 `SessionV2`/`SessionExecutionLocal` 导入**全文件未使用**
- **数据走查**：—
- **运行证据**：NOT_RUN（静态检索；`grep` 命令见 `过程观察.md` §3）
- **不能证明**：**不能**据此判断 v1 与 v2 的完整差异（v2 属 T10）；**不能**把"零耦合"当分界结论（同源 ≠ 零耦合，耦合点已列明）；**不能**说"v1 全面采用 v2 代码"（多数为死导入/边界实例化）
- **冲突裁决**：确立本包 **v1/v2 分界硬纪律**——不得用 v2 代码填 v1 空白（任务卡 T09 核心纪律）
- **核验日期**：2026-10-15

---

## 二、CM-01 请求组装与角色

### ocv1-assembly-01
- **结论**：v1 每次模型请求的 `system` 由**一条合成字符串**构成——`agent.prompt`（无则按模型选 `SystemPrompt.provider(model)`）+ 环境块 + 规则指令 + MCP 指令 + 技能清单 + `user.system`；`messages = [system 消息, …投影消息…, (末步)MAX_STEPS_PROMPT]`；工具声明按名排序。
- **性质**：事实
- **范围**：v1 出货；provider 任意（OpenAI OAuth / GitLab workflow 例外：system 走 `instructions`/原生）
- **实现状态**：默认
- **来源**：`session/llm/request.ts:58-66`（system 合成）、`:101-112`（messages 插入）、`:184`（工具排序）、`:187-206`（请求头）；`session/system.ts:28-51`（模型提示词选择）；`session/prompt.ts:1257-1269`（system 数组来源）；`session/prompt.ts:1281`（`MAX_STEPS_PROMPT`）
- **数据走查**：DW-assembly-01
- **运行证据**：NOT_RUN（需真实 provider；见 `过程观察.md` §4 规程）
- **不能证明**：**不能**证明各 provider 服务端实际如何渲染 system（服务端 `UNOBSERVABLE`）；**不能**证明模型对四类块的相对注意力
- **冲突裁决**：支持 T02 §E"请求组装"统一语义；澄清 v1 **无** `developer` 角色（system 走 system role，非 Codex 式 developer 消息）
- **核验日期**：2026-10-15

### ocv1-assembly-02
- **结论**：v1 主循环 `runLoop` 每步**重新从持久层投影**消息并重算请求（非增量拼接）；循环退出条件为"上一轮 assistant 已 finish 且非 tool-calls/unknown 且无未决工具调用"；`agent.steps` 限制步数，末步追加 `MAX_STEPS_PROMPT`。
- **性质**：事实
- **范围**：v1 出货；`session/prompt.ts`
- **实现状态**：默认
- **来源**：`session/prompt.ts:1081-1341`（`runLoop`）；`:1092`（`filterCompactedEffect`）；`:1111-1130`（退出条件）；`:1178-1179`（`maxSteps`）；`:1281`（末步提示）；`session/reminders.ts:15-90`（轮前注入 plan/build 提醒）
- **数据走查**：DW-assembly-01
- **运行证据**：NOT_RUN（需真实 provider）
- **不能证明**：**不能**证明真实会话中步数上限与退出时机的端到端表现（未跑）
- **冲突裁决**：与 `ocv1-assembly-01` 同族；支持"每次请求是重算"的统一视角（LQ-01）
- **核验日期**：2026-10-15

---

## 三、CM-02 项目规则 / 技能加载

### ocv1-rule-01
- **结论**：v1 规则文件为 `AGENTS.md`（含 `CLAUDE.md`、废弃 `CONTEXT.md`）；全局层取**首个存在**者（不叠加祖先），项目层用 `findUp` 取**首个命中**；`config.instructions` 可追加文件与 **http(s) URL**（URL 5s 超时）；读取文件时**沿目录向上**把"就近规则"以 `<system-reminder>` 附到工具结果，**每消息只附一次**。
- **性质**：事实
- **范围**：v1 出货；`session/instruction.ts`、`tool/read.ts`
- **实现状态**：默认（可被 `OPENCODE_DISABLE_PROJECT_CONFIG` 关项目层；`disableClaudeCodePrompt` 关 `CLAUDE.md`）
- **来源**：`session/instruction.ts:60-68`（文件名）、`:110-153`（`systemPaths`：global 首个 + project `findUp` 首个 + `config.instructions`）、`:155-169`（`system`：文件 + URL）、`:179-221`（`resolve`：向上附就近规则）、`:70-77`（`claims` 每消息一次）；`tool/read.ts:300,355-357`（附加 `<system-reminder>`）
- **数据走查**：DW-rule-01
- **运行证据**：NOT_RUN（需真实目录；见 `过程观察.md` §4）
- **不能证明**：**不能**证明"就近规则"在真实多文件会话中是否真的每消息只附一次（未跑）；**不能**证明 URL 规则在离线环境的失败行为（代码为 catch→空串）
- **冲突裁决**：支持术语"发现范围 / 字节预算"存在性；v1 **未见** `AGENTS.md` 共享字节预算常量（与 Codex 32 KiB 口径**不同**，标"未发现"）
- **核验日期**：2026-10-15

### ocv1-skill-01
- **结论**：v1 技能走**渐进式披露**——从 `skills/**/SKILL.md`（含 `.claude`/`.agents` 外部目录、`opencode` 配置目录、`skills.paths`、`skills.urls` 拉取）发现技能；系统提示词**只列** `name/description/location`；正文由 `skill` 工具按需读取；内置 `customize-opencode` 技能随包附带。
- **性质**：事实
- **范围**：v1 出货；`skill/index.ts`、`session/system.ts`
- **实现状态**：默认（可被 `disableExternalSkills` / `disableClaudeCodeSkills` 关外部技能）
- **来源**：`skill/index.ts:21-25`（模式）、`:173-233`（`discoverSkills`）、`:235-246`（`loadSkills`）、`:321-346`（`fmt`：系统提示词只放 name/description/location）；`session/system.ts:107-119`（`skills` 块）；`skill/index.ts:27-35`（内置 `customize-opencode`）
- **数据走查**：DW-skill-01
- **运行证据**：NOT_RUN（需真实技能目录）
- **不能证明**：**不能**证明技能正文加载后的实际 token 收益（未测）；**不能**证明 `skills.urls` 远端索引的可用性（依赖网络）
- **冲突裁决**：支持术语"技能（渐进式披露）"（T02 §E 已转正）；与 omp/pi 的"技能"同义
- **核验日期**：2026-10-15

---

## 四、CM-03 资料选择与代码检索

### ocv1-retrieval-01
- **结论**：v1 提供 `read/grep/glob/list` 等按需检索工具；`read` 支持 `offset/limit` 分页，默认 **2000 行**、单行 **2000 字符**、总量 **50 KiB** 上限，超限给"用 `offset=<next>` 继续"提示；目录读取亦分页。
- **性质**：事实
- **范围**：v1 出货；`tool/read.ts`
- **实现状态**：默认
- **来源**：`tool/read.ts:13-18`（`DEFAULT_READ_LIMIT=2000`、`MAX_LINE_LENGTH=2000`、`MAX_BYTES=50*1024`）、`:137-180`（`lines` 分页）、`:266-297`（目录分页）、`:338-351`（续读提示）；`tool/grep.ts`、`tool/glob.ts`（存在）
- **数据走查**：DW-retrieval-01
- **运行证据**：NOT_RUN（需真实文件；见 `过程观察.md` §4）
- **不能证明**：**不能**证明真实任务中模型是否"按需"而非"全量装填"（属行为，需 T19）；**不能**证明 grep 工具内部实现细节（本包未逐行读）
- **冲突裁决**：支持术语"按需读入 / 代码检索"
- **核验日期**：2026-10-15

---

## 五、CM-04 单条工具输出治理

### ocv1-trunc-01
- **结论**：v1 工具输出经 `Truncate.output` 统一限长：**2000 行 / 51200 字节（50 KiB）先到者**；`direction` 默认 `head`（保头），可 `tail`；**超限原文落盘**到截断目录（文件名 `tool_*`），返回"预览 + 截断标记 + 提示"，落盘文件**保留 7 天**；上限可由 `tool_output.max_lines/max_bytes` 覆盖。
- **性质**：事实
- **范围**：v1 出货；`tool/truncate.ts`
- **实现状态**：默认
- **来源**：`tool/truncate.ts:12`（`RETENTION=7d`）、`:14-15`（`MAX_LINES=2000`、`MAX_BYTES=50*1024`）、`:85-141`（`output`：先到者 + head/tail + 落盘 + 提示）、`:124-125`（`removed`/`unit`）、`:143-148`（每小时清理）；`packages/core/src/v1/config/config.ts:136-148`（`tool_output`）
- **数据走查**：DW-trunc-01（含边界）
- **运行证据**：NOT_RUN（产品端到端）；函数级判据见 `OBS-ocv1-token-01` 同法可扩展（未跑）
- **不能证明**：**不能**证明落盘文件在真实会话中确实被模型通过 `read/grep` 取回（未跑）；**不能**证明 51200 字节与 2000 行的"先到者"在混合 CJK/ASCII 下的具体分布（需实测）
- **冲突裁决**：与 omp（3000 行/51200 字节）**行上限不同、字节上限相同**；v1 落盘入口是**截断目录**（非 artifact:// 协议）；支持"落盘 ≠ 摘要"边界
- **核验日期**：2026-10-15

### ocv1-trunc-02
- **结论**：压缩序列化时对工具结果**再按 2000 字符**限长（`TOOL_OUTPUT_MAX_CHARS=2000`，追加 `\n[truncated]`）；被 `prune` 擦除的工具结果序列化为 `[Old tool result content cleared]`。
- **性质**：事实
- **范围**：v1 出货；`session/compaction.ts`
- **实现状态**：默认
- **来源**：`session/compaction.ts:30`（`TOOL_OUTPUT_MAX_CHARS=2_000`）、`:51-52`（`truncate`）、`:54-85`（`serialize`：`:76-78` 的 cleared 分支）
- **数据走查**：DW-trunc-02
- **运行证据**：NOT_RUN
- **不能证明**：**不能**证明 2000 **字符**（非字节/token）在 CJK 下的实际压缩率；**不能**证明该限长对摘要保真度的影响（需 T19）
- **冲突裁决**：v1 有**两道**限长（工具入口 2000 行/51200 字节；压缩序列化 2000 字符）——须分列，勿混用单位
- **核验日期**：2026-10-15

---

## 六、CM-05 窗口计量与触发

### ocv1-trigger-01
- **结论**：v1 有效窗口 `usable = limit.input − reserved`（有 `input` 上限时）或 `context − maxOutputTokens`（否则）；`reserved = cfg.compaction.reserved ?? min(20000, maxOutputTokens)`。
- **性质**：事实
- **范围**：v1 出货；`session/overflow.ts`
- **实现状态**：默认
- **来源**：`session/overflow.ts:8-20`（`COMPACTION_BUFFER=20_000`、`usable`）；`packages/core/src/v1/config/config.ts:164-166`（`compaction.reserved`）
- **数据走查**：DW-trigger-01（含算例）
- **运行证据**：NOT_RUN（需真实 provider 的 `model.limit`）
- **不能证明**：**不能**证明真实 provider 返回的 `limit.input`/`limit.context` 具体数值（`model.limit` 来自 provider 元数据，服务端/注册表侧，未在本地核对）；**不能**证明 `reserved` 默认值在真实模型的取舍
- **冲突裁决**：v1 用**绝对预留**口径（非百分比），与 Codex"范围线/整段线"两线结构**不同**——不按层数/线数比成熟度
- **核验日期**：2026-10-15

### ocv1-trigger-02
- **结论**：`isOverflow = (tokens.total || input+output+cache.read+cache.write) ≥ usable`；`compaction.auto===false` 时**恒为 false**；`model.limit.context===0` 时恒 false。
- **性质**：事实
- **范围**：v1 出货；`session/overflow.ts`
- **实现状态**：默认（`compaction.auto` 默认 true）
- **来源**：`session/overflow.ts:22-34`；`packages/core/src/v1/config/config.ts:151-153`（`compaction.auto` 默认 true）
- **数据走查**：DW-trigger-01
- **运行证据**：NOT_RUN
- **不能证明**：**不能**证明 `tokens.total` 与四项相加在真实 provider 下是否一致（未跑）；**不能**证明"到线"与真实压缩时机的对应（需 T19）
- **冲突裁决**：支持术语"触发线（伞名）"在 v1 侧**退化为单一整段线**；限制"90%–95% 总括"（C-01/C-02）——v1 非百分比
- **核验日期**：2026-10-15

---

## 七、CM-06 自动 / 手动压缩

### ocv1-compact-01
- **结论**：v1 自动压缩有两处触发：① 主循环"上一轮已 finish 且非摘要轮且 `isOverflow`"→ `compaction.create({auto:true})`；② 处理器 `step-finish` 溢出或 `ContextOverflowError` → `needsCompaction` → `create({auto:true, overflow:!finish})`。压缩成功后**默认追加合成 continue 用户消息**（`metadata.compaction_continue`，可被插件关）。
- **性质**：事实
- **范围**：v1 出货；`session/prompt.ts`、`session/processor.ts`、`session/compaction.ts`
- **实现状态**：默认（`compaction.auto=true`）
- **来源**：`session/prompt.ts:1161-1168`（轮后）、`:1149-1159`（压缩任务分支）、`:1320-1328`（处理器 compact→create）；`session/processor.ts:491-496`（step-finish 溢出）、`:621-632`（halt）；`session/compaction.ts:468-549`（auto continue 合成，`:540` metadata）
- **数据走查**：DW-compact-01
- **运行证据**：NOT_RUN（需真实 provider 触发溢出；见 `过程观察.md` §4）
- **不能证明**：**不能**证明真实会话中压缩触发频率/时机（需 T19）；**不能**证明合成 continue 对任务延续的实际效果
- **冲突裁决**：支持 CM-06"自动压缩"有实现；与 omp 六路径/Codex 三时机**路径数不同**——不按路径数比成熟度
- **核验日期**：2026-10-15

### ocv1-compact-02
- **结论**：v1 手动压缩的用户命令名为 **`/compact`**——TUI 斜杠命令（`app/.../use-session-commands.tsx:482` `slash:"compact"`；官方文档 `tui.mdx:93`）与 ACP（`acp/service.ts:570-574` `command.name==="compact"`）均映射到 **HTTP `POST /api/session/:sessionID/summarize`**（`groups/session.ts:94,303`）；该端点以 `auto: payload.auto ?? false` 建压缩条目后调用主循环，与自动压缩**共用** `compaction.process`。
- **性质**：事实
- **范围**：v1 出货；`server/routes/instance/httpapi/handlers/session.ts`、`packages/app`、`packages/opencode/src/acp/service.ts`
- **实现状态**：默认（HTTP 接口 + UI 命令名）
- **来源**：`handlers/session.ts:273-293`（`summarize` 处理：`compactSvc.create({auto:...??false})`）；`groups/session.ts:94,303-315`（`SessionPaths.summarize = /:sessionID/summarize`）；`packages/app/src/pages/session/use-session-commands.tsx:479-486`（`slash:"compact"`）；`packages/opencode/src/acp/service.ts:570-574`；`packages/web/src/content/docs/tui.mdx:93`（`/compact`）；`session/prompt.ts:1149-1159`（loop 消费压缩任务）
- **数据走查**：DW-compact-01
- **运行证据**：NOT_RUN（需真实 server + provider）
- **不能证明**：**不能**证明 `/compact` 在真实会话中的端到端效果与自动压缩的差异（需 T19）；**不能**证明 v2 的 `/compact`（协议包 `v2.session.compact`）与 v1 一致（属 T10）
- **冲突裁决**：术语"手动压缩"在 v1 侧**有实现**且命令名已定位（`/compact`）；v1 HTTP 端点为 `summarize`（**不是** `compact` 路径——`compact` 路径属 v2 协议包）
- **核验日期**：2026-10-15

---

## 八、CM-07 摘要 / 裁剪 / 重建

### ocv1-summary-01
- **结论**：v1 摘要提示词用固定 `SUMMARY_TEMPLATE`（`Objective / Important Details / Work State{Completed/Active/Blocked} / Next Move / Relevant Files`）+ `SUMMARY_UPDATE_INSTRUCTIONS`（`<prior-summary>` **增量合并**：冲突以新对话为准，未带过来即丢失）；`compaction` agent 提示词要求"只输出结构化摘要、不续对话、用对话语言"。
- **性质**：事实
- **范围**：v1 出货（模板定义在共享模块 `packages/core/src/session/compaction.ts`，**v1 经 `import { buildPrompt }` 使用**）
- **实现状态**：默认（可被插件 `experimental.session.compacting` 替换 `prompt`）
- **来源**：`packages/core/src/session/compaction.ts:16-46`（`SUMMARY_TEMPLATE`）、`:47-55`（`SUMMARY_UPDATE_INSTRUCTIONS`）、`:160-174`（`buildPrompt`）；`packages/opencode/src/session/compaction.ts:23,381-391`（v1 调用）；`agent/prompt/compaction.txt`
- **数据走查**：DW-summary-01
- **运行证据**：NOT_RUN（需真实模型生成摘要）
- **不能证明**：**不能**证明模板在真实模型下的遵守度（需 T19）；**不能**证明增量合并的失真程度（LQ-09，需连续压缩实验）
- **冲突裁决**：**判为有损**（增量合并明说"未带过来即丢失"）；支持 C-04"旧摘要非无损"；具体失真**未决（T19）**
- **核验日期**：2026-10-15

### ocv1-summary-02
- **结论**：v1 压缩保留预算 = `cfg.compaction.preserve_recent_tokens ?? min(15000, max(2000, floor(usable×0.25)))`；`tail_turns` 可限制候选 turn 数；选尾从最新 turn 往回累加，切点**只落 turn（user 消息为界）的 message 边界**，整 turn 装不下时用 `splitTurn` 在 turn 内找切点。
- **性质**：事实
- **范围**：v1 出货；`session/compaction.ts`
- **实现状态**：默认
- **来源**：`session/compaction.ts:32-33`（`MIN/MAX_PRESERVE_RECENT_TOKENS`）、`:115-120`（`preserveRecentBudget`）、`:122-138`（`turns`）、`:140-163`（`splitTurn`）、`:223-269`（`select`）；`packages/core/src/v1/config/config.ts:157-163`（`tail_turns`/`preserve_recent_tokens`）
- **数据走查**：DW-summary-02（含算例）
- **运行证据**：NOT_RUN
- **不能证明**：**不能**证明真实 provider 下"估算 token"（chars/4）与真实 token 的偏差对切点的影响（见 `OBS-ocv1-token-01` 的 CJK 口径限制）
- **冲突裁决**：v1 保留预算**随 `usable` 浮动**（非固定 20000）——与 omp/pi 的 `keepRecentTokens=20000` **不同**
- **核验日期**：2026-10-15

### ocv1-summary-03
- **结论**：v1 有 `prune`（**默认关**）——从最新往回，**保护最近 40000 token 工具输出**；超保护部分累计，可擦量 **> 20000 token** 才真正擦；被擦部件只打 `part.state.time.compacted=Date.now()`（**原文仍在库**，不再进请求）；`skill` 工具输出受保护；遇摘要消息即停。
- **性质**：事实
- **范围**：v1 出货；`session/compaction.ts`
- **实现状态**：条件（`compaction.prune` 默认 false）
- **来源**：`session/compaction.ts:28-31`（`PRUNE_MINIMUM=20_000`、`PRUNE_PROTECT=40_000`、`PRUNE_PROTECTED_TOOLS=["skill"]`）、`:271-317`（`prune`）；`packages/core/src/v1/config/config.ts:154-156`（`compaction.prune` 默认 false）；`session/prompt.ts:1338`（循环末尾 `compaction.prune`）
- **数据走查**：DW-summary-03（含边界）
- **运行证据**：NOT_RUN
- **不能证明**：**不能**证明默认关下 `prune` 从不生效（代码为条件调用，需配置开）；**不能**证明擦除后模型是否真的"看不到"（`filterCompacted` 仍可能带出——未跑核对）
- **冲突裁决**：与 omp"压缩前工具裁剪"**同类但阈值不同**（omp 保护 40000/最小节省 20000 **同值**——v1 与 omp 数值相同，来源待核）；支持"落盘/擦除 ≠ 摘要"
- **核验日期**：2026-10-15

### ocv1-summary-04
- **结论**：v1 模型可见历史由 `filterCompacted` **重排重建**：把 `[压缩用户消息(type:"compaction"), 摘要 assistant(summary:true), tail_start_id 起的保留段, 后续消息]` 拼成；磁盘原始消息**从不删除**；压缩用户消息在转模型消息时变成文本 `"What did we do so far?"`。
- **性质**：事实
- **范围**：v1 出货；`session/message-v2.ts`
- **实现状态**：默认
- **来源**：`session/message-v2.ts:534-589`（`filterCompacted`/`filterCompactedEffect`）、`:238-243`（compaction part→"What did we do so far?"）；`session/prompt.ts:1092`（调用）
- **数据走查**：DW-summary-04
- **运行证据**：NOT_RUN
- **不能证明**：**不能**证明重排后模型对"摘要 + 保留段"的实际使用（需 T19）；**不能**证明多条压缩叠加时的重排正确性（未跑）
- **冲突裁决**：**支持 C-03"两事实并存"**——磁盘保留原文 + 模型可见层用替代历史；**支持 C-12/LQ-10 持久化断点路线（B）**
- **核验日期**：2026-10-15

---

## 九、CM-08 长期记忆

### ocv1-memory-01
- **结论**：**未发现 v1 默认长期记忆实现（推断）**——v1 出货路径（`packages/opencode/src/session`、`src/tool`、`src/agent`）与 v1 命名空间（`packages/core/src/v1`）内**无 memory 模块**，检索 `memory/longterm/long-term memory/session memory/background extraction` **零命中**。
- **性质**：推断（**非"没有"**）
- **范围**：v1 出货；快照 `733b2c6`
- **实现状态**：未证实（未见默认实现，也未见配置开关）
- **来源**：`find packages/opencode/src packages/core/src/v1 -iname "*memory*"` 零命中；`grep -rli "longterm|long-term memory|session memory|background extraction"` 零命中（命令见 `过程观察.md` §3）
- **数据走查**：—
- **运行证据**：NOT_RUN（静态检索；检索路径与命令已登记）
- **不能证明**：**"未发现"≠"没有"**——可能存在于插件生态、远端服务、或本包未覆盖的路径；判定"能力不存在"须补"官方怎么说"，本包**未取得**官方"无长期记忆"声明，故**只标推断**
- **冲突裁决**：**未裁决**（不改旧结论）；与 omp（有独立记忆五后端）、Claude（有记忆线）**形成对比点**，但 v1 侧只到"未发现默认实现（推断）"
- **核验日期**：2026-10-15

---

## 十、CM-09 子 Agent 交接

### ocv1-cm09-01
- **结论**：v1 内置 `task` 工具：为指定子 agent **新建独立会话**（自带 agent systemPrompt、独立消息列表），结果以 `<task_result>`/`<task_error>` 文本回父；`subagent_depth` 默认 **1**（禁嵌套）；后台子代理需 `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`；子会话权限由父权限派生。
- **性质**：事实
- **范围**：v1 出货；`tool/task.ts`
- **实现状态**：默认（前台）；后台为**条件/实验**
- **来源**：`tool/task.ts:24`（id）、`:92-117`（深度检查）、`:156-172`（建子会话）、`:64-79`（`renderOutput`）、`:316-358`（前台/后台）；`packages/core/src/v1/config/config.ts:84-86`（`subagent_depth` 默认 1）；`session/prompt.ts:255-449`（`handleSubtask`）
- **数据走查**：DW-cm09-01
- **运行证据**：NOT_RUN（需真实 provider）
- **不能证明**：**不能**证明子会话"不继承父对话历史"的完整边界（本包读到子会话新建 + 权限派生，未逐字段核对继承规则）；**不能**证明后台子代理的端到端行为（实验门控，未跑）
- **冲突裁决**：CM-09 在 v1 **适用**（非"不适用"）；与 pi（刻意不含子代理）形成对照
- **核验日期**：2026-10-15

---

## 十一、CM-10 保存 / fork / 恢复

### ocv1-persist-01
- **结论**：v1 会话消息/部件持久化到 **SQLite**，写入经**事件**（`MessageUpdated`/`PartUpdated`）由投影器落行；读取用 `MessageV2.page` 分页；旧 JSON 文件存储仅保留**迁移**用。
- **性质**：事实
- **范围**：v1 出货；`session/session.ts`、`session/message-v2.ts`、`storage/storage.ts`
- **实现状态**：默认
- **来源**：`session/session.ts:629-643`（`updateMessage`/`updatePart` 发事件）、`:828-851`（`messages` 分页）；`session/message-v2.ts:438-503`（`page`/`stream`）、`:80-123`（`info`/`part`/`hydrate`）；`storage/storage.ts:81-211`（`MIGRATIONS`）
- **数据走查**：DW-persist-01
- **运行证据**：NOT_RUN（需真实会话写盘）
- **不能证明**：**不能**证明 DB 文件的**原生落盘路径与 schema**（投影器在 `packages/core/src/session/projector.ts`，属 v2 命名空间文件，本包**未引用其行为**；v1 侧只证"事件 → 行"的调用面）；**不能**证明 DB 在真实运行中的具体位置（未跑）
- **冲突裁决**：支持"保存/fork/恢复"有实现；v1 持久化形态为 **DB（事件溯源）**，与 omp/pi 的**追加式 JSONL**不同——**存储形态差异**，不按形态比优劣
- **核验日期**：2026-10-15

### ocv1-recover-01
- **结论**：v1 恢复入口为 CLI `opencode run --continue` / `--session <id>`（`--fork` 先 fork 再续）；恢复走**持久化断点路线**——`runLoop` 首步 `filterCompactedEffect` 用存档的 `compaction` 条目 + `tail_start_id` 重建，**不重放全部历史重算**；`Session.fork` 复制到新会话并**重映射** `tail_start_id`。
- **性质**：事实
- **范围**：v1 出货；`cli/cmd/run.ts`、`session/session.ts`、`session/message-v2.ts`
- **实现状态**：默认
- **来源**：`cli/cmd/run.ts:147-158`（`--continue`/`--session`/`--fork`）、`:469-506`（fork 调用）；`session/session.ts:691-732`（`fork`，`:725-727` tail_start_id 重映射）；`session/message-v2.ts:534-585`（重建）
- **数据走查**：DW-recover-01
- **运行证据**：NOT_RUN（需真实会话 + provider）
- **不能证明**：**不能**证明真实重启后"恢复了什么/丢了什么"（需 T19）；**不能**证明 fork 后子会话的完整一致性（未跑）
- **冲突裁决**：**裁决 LQ-10 = 持久化断点路线（B）**；支持 C-12"默认模型可见层用替代历史"
- **核验日期**：2026-10-15

---

## 十二、CM-11 错误与副作用

### ocv1-fail-01
- **结论**：v1 通用重试：`RETRY_MAX_RETRIES=5`、初始延迟 2000ms、退避因子 2、抖动 0.25、无头时限 30s；`retry-after`/`retry-after-ms` 头优先；**`ContextOverflowError` 不重试**（转压缩）；仅 5xx / 命中可重试消息模式才重试。
- **性质**：事实
- **范围**：v1 出货；`session/retry.ts`
- **实现状态**：默认
- **来源**：`session/retry.ts:26-31`（常量）、`:47-83`（`delay`/`exponential`）、`:85-155`（`retryable`）、`:183-207`（`policy`）；`session/processor.ts:674-688`（`Effect.retry`）
- **数据走查**：DW-fail-01（含算例）
- **运行证据**：NOT_RUN（需注入 provider 错误；见 `过程观察.md` §4）
- **不能证明**：**不能**证明真实限流下重试的实际效果与耗时（需 T19）；**不能**证明各 provider 的 `retry-after` 头行为（服务端）
- **冲突裁决**：支持术语"有界重试"；v1 上限 5（与 omp `maxRetries=10` **不同**）
- **核验日期**：2026-10-15

### ocv1-fail-02
- **结论**：v1 有 `doom_loop` 防护——连续 **3** 次相同工具 + 相同输入的调用触发 `doom_loop` 权限询问（默认 `ask`）；中断/中止时未结算工具被标 `status:"error"`、`metadata.interrupted=true` 并落 `time.completed`；已写盘副作用**不回退**。
- **性质**：事实
- **范围**：v1 出货；`session/processor.ts`
- **实现状态**：默认（`doom_loop` 权限默认 `ask`）
- **来源**：`session/processor.ts:29`（`DOOM_LOOP_THRESHOLD=3`）、`:356-380`（doom loop 判定 + 询问）、`:553-611`（`cleanup` 中断标记）；`agent/agent.ts:121`（`doom_loop:"ask"` 默认）
- **数据走查**：DW-fail-02
- **运行证据**：NOT_RUN（需构造重复调用）
- **不能证明**：**不能**证明 doom_loop 在真实循环中的触发率；**不能**证明副作用回退边界（`revert` 与压缩失败的关系本包未逐行核）
- **冲突裁决**：支持术语"失败分类 / 副作用"；`doom_loop` 阈值 3 属 v1 专名（可增补术语）
- **核验日期**：2026-10-15

---

## 十三、CM-12 缓存及总成本

### ocv1-cache-01
- **结论**：v1 **CLI 侧可证**——`applyCaching` 给"**前 2 条 system + 后 2 条**非 system** 消息**"打 provider 级 ephemeral 缓存标记（anthropic/openrouter/bedrock/openaiCompatible/copilot/alibaba）；OpenAI 兼容系设 `prompt_cache_key = sessionID`；请求头带 `x-session-affinity`/`X-Session-Id`/`x-opencode-session-id`。**服务端命中率与 TTL = `UNOBSERVABLE`**。
- **性质**：事实（CLI 侧）/ 不可观测（服务端）
- **范围**：v1 出货；`provider/transform.ts`、`session/llm/request.ts`
- **实现状态**：默认（标记存在；实际命中取决于 provider）
- **来源**：`provider/transform.ts:358-381`（`applyCaching`：system 前 2 + 末 2）、`:1325`（`result["prompt_cache_key"] = input.sessionID`）；`session/llm/request.ts:187-206`（会话亲和头）；`session/session.ts:338-405`（`getUsage`：cache read/write 分列）
- **数据走查**：DW-cache-01
- **运行证据**：NOT_RUN（服务端 `UNOBSERVABLE`；需 T19 观测 usage）
- **不能证明**：**不能**证明命中率、TTL、真实节省金额（服务端）；**不能**证明前缀压缩后命中率退化（需 T19）
- **冲突裁决**：支持术语"缓存键（CLI 侧已证）"；缓存**≠摘要≠记忆**（严格分开）
- **核验日期**：2026-10-15

---

## 十四、扩展点

### ocv1-ext-01
- **结论**：v1 扩展点 = 插件 `Hooks`（`chat.message`/`chat.params`/`chat.headers`/`tool.execute.before|after`/`shell.env`/`experimental.chat.messages.transform`/`experimental.chat.system.transform`/`experimental.provider.small_model`/`experimental.session.compacting`/`experimental.compaction.autocontinue`/`experimental.text.complete`/`tool.definition`）+ `opencode.json` 配置；**均有 v1 出货调用点**（`tool.definition` 在 `tool/registry.ts:318`）。
- **性质**：事实
- **范围**：v1 出货；`packages/plugin/src/index.ts`、`session/*`、`tool/registry.ts`
- **实现状态**：默认（钩子接口存在；具体钩子是否被插件使用取决于用户装插件）
- **来源**：`packages/plugin/src/index.ts:222-335`（`Hooks`）；调用点：`session/prompt.ts:307-311,389-393,554-558,999-1009,1255`、`session/llm/request.ts:69-78,114-146`、`session/compaction.ts:373-377,379,500-517`、`session/processor.ts:530-538`、`tool/registry.ts:318`；`plugin/index.ts:284-297`（`trigger`）
- **数据走查**：DW-ext-01
- **运行证据**：NOT_RUN（需装插件）
- **不能证明**：**不能**证明插件生态的既有行为；**不能**证明各钩子在多插件下的执行顺序细节（`trigger` 顺序遍历 hooks，未跑）
- **冲突裁决**：支持"扩展点"分列（默认 vs 插件态）；为 T10 扩展点对照提供 v1 侧基线
- **核验日期**：2026-10-15

---

## 计数核对

```bash
grep -c "结论ID\|^### ocv1-" 证据/ocv1-证据卡.md   # 见 §计数实测
```

**实际**：`grep -c "^### ocv1-" 证据/ocv1-证据卡.md` = **25**（族：version 2 + assembly 2 + rule 1 + skill 1 + retrieval 1 + trunc 2 + trigger 2 + compact 2 + summary 4 + memory 1 + cm09 1 + persist 1 + recover 1 + fail 2 + cache 1 + ext 1 = **25**）。自述"25 张卡"与实际一致。

---
*配套：`工具概览.md` / `源码导读.md` / `数据走查.md` / `过程观察.md` / `问题与审查.md`。*
