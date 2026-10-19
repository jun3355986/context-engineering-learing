# pi · 上下文管理事实卡片

- **仓库**：https://github.com/earendil-works/pi（旧名 `badlogic/pi-mono`）
- **提交号**：`b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb`
- **核实日期**：2026-10-18
- **分析范围**：仅 `packages/coding-agent`（核心 `src/core`）与 `packages/evals`。不分析模型服务端行为，不分析第三方扩展的具体实现。
- **Permalink 基址**：`https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/`
- **说明**：pi 自我定位为「minimal, extensible agent harness」，README 明确「skips features like sub-agents and plan mode」（`README.md#L19`）。因此第 10 类为「无此能力」，第 12 类默认也没有独立记忆子系统。

---

## 1. 请求组装

**做法**
pi 每次发请求前不算「消息数组」，而是先让 `SessionManager` 生成一份**会话投影**（projection）：沿当前叶子回溯成树路径，应用最新 `compaction` 的 `firstKeptEntryId`，再叠加 `context_edit` 的省略/替换，得到模型真正看到的消息序列。`_installAgentRequestProjection()` 劫持 agent 内核的 `prepareRequest`，把 `projection.messages` 作为 `context.messages`，把 `agent.state.tools` 作为可执行工具实现放进 `context.tools`。两者刻意分开：消息声明「provider 可见的装载清单」，`tools` 保留「可执行实现」，避免工具实现的元数据进入请求体（源码注释原话）。系统提示词不是一整块字符串，而是**具名 section**：`preamble` 为裸文本，其余每个 section 用同名 XML 标签包裹后按声明顺序拼接。历史消息由 `convertToLlm()` 统一转换为 provider 消息；压缩摘要会被包装成**一条 user 消息**（前缀 `The conversation history before this point was compacted into the following summary:`）。

**关键参数与默认值**
- section 顺序：`preamble → tools → rules → docs → addendum → project_context → skills → cwd → 自定义 section`（`system-prompt.ts:151-186`）
- 摘要包装：`<summary>…</summary>`（`messages.ts:11-17`）
- 未在源码中找到「按 provider 动态裁剪工具定义」的逻辑

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L788-L845
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/system-prompt.ts#L128-L193
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/messages.ts#L11-L22
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/session-manager.ts#L543-L573

**可信度**：【已核实】

**源码解读候选**：`_installAgentRequestProjection` 如何把「树 + 压缩 + 编辑」压成一次请求

---

## 2. 规则文件的发现与合并

**做法**
规则文件按固定候选名查找：`AGENTS.override.md → AGENTS.md → AGENTS.MD → CLAUDE.md → CLAUDE.MD`，每个目录只取**命中顺序中的第一个**。发现范围是「全局 agent 目录 + 从 cwd 逐级向上的祖先链」，**不遍历子树**。祖先链收集时用 `unshift` 插入，因此离 cwd 越近的文件排在越后面（更靠近提示词尾部、语义上更具体）。同一物理文件用 `seenPaths` 去重；对 `git worktree` 嵌套场景，还会排除被 worktree 副本遮蔽的主仓库同名文件，避免同一份规则注入两次。命中的文件内容被渲染进 `<project_context>` section，每个文件包一层 `<project_instructions path="…">`。`--no-context-files`（`-nc`）可整体关闭发现与加载。

**关键参数与默认值**
- 候选文件名：5 个（见上）
- 开关：`--no-context-files` / `-nc`（`cli/args.ts:216-217`，帮助文本 `:336`）
- 体积上限与截断：**未在源码中找到**（通读 `resource-loader.ts` 的加载路径与 `system-prompt.ts` 的 `renderProjectContext`，未发现按字节/行截断）

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/resource-loader.ts#L184-L274
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/resource-loader.ts#L214-L230 ——（worktree 遮蔽）
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/system-prompt.ts#L173
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/cli/args.ts#L216-L217

**可信度**：【已核实】；「无体积上限」为【待核实】（只证明未找到，不证明不存在）

---

## 3. 按需加载（渐进披露）

**做法**
技能只在系统提示词里暴露「名称 + 一句描述 + 文件位置」，完整 `SKILL.md` 由模型在任务匹配时用 `read`（或 `bash`，取决于可用工具）自行读取；`formatSkillsForPrompt()` 会跳过 `disableModelInvocation` 的技能。技能描述有长度校验（上限 1024 字符），超长不会截断而是产生校验告警。MCP 不在核心内实现，而以 `packages/coding-agent/src/extensions/mcp` 扩展形式提供；扩展可注册工具、命令、provider、渲染器。`read` 工具支持 `offset/limit` 分页续读，因此「先看局部、需要再放大」是通用读取模式，而非专门的文件引用语法。

**关键参数与默认值**
- 技能名上限 64 字符、描述上限 1024 字符（`skills.ts:10-14`）
- 提示词中每技能 4 行：`name / description / location`（`skills.ts:378-384`）
- 未在源码中找到 `@` 文件引用的专门注入机制（检索 `mention` / `fileMention` 无命中；CLI 参数层有对 `@` 开头实参的处理，但不属于上下文注入）

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/skills.ts#L358-L391
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/skills.ts#L10-L14
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/system-prompt.ts#L174-L182

**可信度**：【已核实】

---

## 4. 动态注入

**做法**
pi 的动态注入不是「往对话里塞 system reminder」，而是**系统提示词的 section 级补丁**：每次新一轮请求前，`_preparePromptAndToolLoadout()` 用 `diffSystemPromptSections()` 比较「模型当前已有的 sections」与「本次期望的 sections」，只为发生变化的 section 生成一条新的 system 消息（`content` 为空、`sections` 为 patch）；未变化的 section 不重发。这既实现了「规则/工具/cwd 变化时只注入变化部分」，也保住了提示词前缀的缓存稳定性。反过来，pi **没有** todo/计划状态注入（无 plan mode）、没有日期或环境变化的周期性提醒；`cwd` 只是一个普通 section，cwd 变了才会进入 patch。

**关键参数与默认值**
- patch 语义：值变化 → 新值；section 被删除 → `null`（`system-prompt.ts:217-229`）
- 无固定注入周期（事件驱动，不是定时器）

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L1743-L1755
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/system-prompt.ts#L217-L229
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/extensions/types.ts#L932-L957（`before_agent_start` 可改提示词 options）

**可信度**：【已核实】

**源码解读候选**：`diffSystemPromptSections` —— 用「section diff」替代「整段重发」

---

## 5. Token 计量与可视化

**做法**
用量优先取**最近一条有效 assistant 的 provider usage**（跳过 `aborted`、`error`、全零 usage），并把它之后的尾随消息用本地估算累加。`calculateContextTokens()` 的口径是 `totalTokens`，缺失时用 `input + output + cacheRead + cacheWrite`——**缓存读写计入窗口占用**。本地估算用 `ceil(chars / 4)`，图片按 4800 字符计。若最近一次 `context_edit` 或 `compaction` 晚于该 usage 的来源条目，则丢弃旧 usage、对投影全量重估，避免「压缩后仍用压缩前的大 usage 误触发」。交互界面没有 `/context` 命令；footer 常驻显示 `百分比/窗口大小`，>70% 变黄、>90% 变红，压缩进行中百分比显示为 `?`。累计 token/成本与缓存命中率在 footer 与 `/session` 里看。

**关键参数与默认值**
- 估算：`Math.ceil(chars / 4)`；图片 `ESTIMATED_IMAGE_CHARS = 4800`
- 阈值：`contextTokens > contextWindow - reserveTokens`，`reserveTokens` 默认 **16384**（`compaction.ts:126-130`）
- 输出预留：与 `reserveTokens` 共用一笔，不单独扣减
- 窗口大小：直接取当前 `model.contextWindow`，未发现用户可单独切换上下文窗口的设置（换窗口只能换模型）
- 颜色阈值：70% / 90%（`footer.ts:205-209`）

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L140-L262
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L267-L270
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L276-L349
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/modes/interactive/components/footer.ts#L157-L210
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L766-L775
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/slash-commands.ts#L19-L44
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/settings-defaults.ts#L9-L13

**可信度**：【已核实】

---

## 6. 单次工具输出控制

**做法**
所有工具输出走两条**互相独立**的上限：行数 2000、字节 50KB，**先到者胜**。`read/grep/find/ls` 用 `truncateHead()` 保头；`bash` 用 `truncateTail()` 保尾。除 bash 保尾的极端情形外，不返回半行；UTF-8 多字节字符会回退到字符边界。`bash` 超限时把完整输出写入临时文件，上下文里只留尾部预览与 `Full output: <tempPath>`；`OutputAccumulator.snapshot()` 返回 `fullOutputPath`，`readFullOutput(maxBytes)` 在超大时保留首尾各半并插入省略标记，因此原文**可以重新读回**。

**关键参数与默认值**
- `DEFAULT_MAX_LINES = 2000`，`DEFAULT_MAX_BYTES = 50 * 1024`
- `GREP_MAX_LINE_LENGTH = 500`（单行匹配上限）
- bash 落盘：`persistIfTruncated: true`（`output-accumulator.ts:110-112`；`bash.ts:286/333`）

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/tools/truncate.ts#L1-L13
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/tools/truncate.ts#L78-L78
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/tools/truncate.ts#L168-L168
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/tools/output-accumulator.ts#L91-L119
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/tools/output-accumulator.ts#L144-L170
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/tools/bash.ts#L286-L286

**可信度**：【已核实】

---

## 7. 历史裁剪（不调用模型）

**做法**
pi 没有「自动把旧工具结果换成占位符」的常规裁剪器。它唯一的原地裁剪机制是 **`context_edit` 条目**：`replacement: null` 表示把目标条目从模型投影中省略，`{content}` 表示只替换内容；它**只改模型可见投影，不改磁盘原始条目**。实际使用点主要是溢出恢复：把刚失败的那次 assistant 尝试及其工具结果省略掉，然后压缩重试。扩展也可以追加 `context_edit`。另有一个用户侧的小口子：`!!` 前缀的 bash 执行消息带 `excludeFromContext`，`convertToLlm()` 会整条丢弃。因此 pi 的减量顺序是「工具输出限长 → （可选）context_edit / 排除 bash → 调模型摘要」，中间缺少 omp 那种按 token 预算批量裁剪旧工具结果的层。

**关键参数与默认值**
- 无自动裁剪阈值（没有 `protectTokens` / `minimumSavings` 一类配置）
- `ContextEditEntry` 字段：`targetId`、`replacement`（`session-manager.ts:175-180`）

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/session-manager.ts#L175-L180
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/session-manager.ts#L519-L540
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/messages.ts#L148-L196
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L1241-L1257

**可信度**：【已核实】

---

## 8. 压缩（调用模型做摘要）

**做法**
压缩入口分手动与自动。手动 `/compact [指令]` 先 `abort()` 当前操作，`prepareCompaction()` 找切点，触发 `session_before_compact` 钩子（可取消或给出自定义摘要），否则走默认摘要；成功后追加一条 `CompactionEntry{summary, firstKeptEntryId, tokensBefore, details, usage}`。自动有三条时机：轮中（每批工具结果落定、下一次 assistant 之前）、提交新提示前（用最近 assistant 复检，覆盖被中止的回复）、运行结束后（阈值或溢出）。**切点**从最新往回逐条累加 `estimateTokens`，累计 ≥ `keepRecentTokens` 时，取「≥ 当前下标的最接近合法切点」；合法切点只包括 user/assistant/bashExecution/custom/branchSummary/compactionSummary，**绝不切在 toolResult**，切在带工具调用的 assistant 时其结果会随后保留。**单个回合过长**时 `isSplitTurn=true`：把「用户消息到切点之前」的轮前缀单独摘要（预算 `0.5 × reserveTokens`），再与历史摘要用 `--- **Turn Context (split turn):**` 合并。**多次压缩**时，最新 compaction 的 `summary` 作为 `previousSummary` 传入，提示词切换为 UPDATE 版（保留旧信息、追加新进展）；文件清单也从上一份 `CompactionEntry.details` 继承后累加。**读写文件跟踪**由 `extractFileOperations()` 从 `read/write/edit` 工具调用抽取，`computeFileLists()` 把只读与已修改分开，最终以 `<read-files>` / `<modified-files>` 追加到摘要末尾。**服务端压缩**：pi 未实现。**手动附带指令**：`customInstructions` 以 `Additional focus: …` 追加到摘要提示词。

**关键参数与默认值**
- `enabled: true`、`reserveTokens: 16384`、`keepRecentTokens: 20000`（`compaction.ts:126-130`）
- 摘要输出上限：`min(floor(0.8 × reserveTokens), model.maxTokens)`（`compaction.ts:712-715`）
- split 的轮前缀上限：`min(floor(0.5 × reserveTokens), model.maxTokens)`（`compaction.ts:1090-1093`）
- 摘要序列化：toolResult 截到 2000 字符，thinking 块整体省略（`utils.ts:94,114-118,149`）
- 摘要失败判定：`stopReason=error` 或 `length` 即失败；摘要里出现 `toolCall` 也失败（`compaction.ts:585-593,755-761`）

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L126-L130
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L267-L270
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L351-L364
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L446-L501
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L507-L579
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L802-L870
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L965-L1071
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/utils.ts#L67-L87
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/utils.ts#L120-L155
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L777-L786
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L1890-L1896
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L1974-L1974
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L2794-L2914
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L2977-L3114
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/session-manager.ts#L1261-L1287

**可信度**：【已核实】

**源码解读候选**：
1. `findCutPoint()` + `isSplitTurn`：为什么「先按整轮找切点」比「按消息找」更难写
2. `compact()` 的双摘要合并（历史摘要 + 轮前缀摘要）

---

## 9. 多模态上下文

**做法**
pi 只做两件事：估算时把每个 image block 当 4800 字符计入；当当前模型不支持图片输入时，`read` 工具返回文字说明并**不附带图片**（`[Current model does not support images. The image will be omitted from this request.]`）。它**没有**「把旧图片移出上下文」「把历史渲染成图片」「把附件转成文字」的机制。图片一旦进入历史，除非整段被压缩摘要覆盖，否则会一直留在投影里。

**关键参数与默认值**
- 估算常量：`ESTIMATED_IMAGE_CHARS = 4800`（`compaction.ts:276`）
- 无图片数量预算、无图片驱逐阈值

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L276-L291
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/tools/read.ts#L80-L83

**可信度**：【已核实】（「无图片驱逐」为未找到实现，非文档声明）

---

## 10. 子代理隔离

**做法**
**无此能力**。README 明确「Pi ships with powerful defaults but skips features like sub-agents and plan mode」。在 `packages/coding-agent/src` 内检索 `subagent` / `sub-agent` / `subAgent` 无命中；也没有「独立子会话」「结构化返回」「并行 worktree」的内置实现。扩展可以自行实现委派（注册工具、起子进程），但那属于扩展行为，不计入 pi 默认能力。

**关键参数与默认值**
- 无

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/README.md#L19
- 全仓检索：`packages/coding-agent/src` 内 `subagent|sub-agent|subAgent` 无匹配（2026-10-18）

**可信度**：【已核实】

---

## 11. 会话时间线

**做法**
会话文件是**只追加的 JSONL 条目日志**，每行一个条目，靠 `id` / `parentId` 组成树（`CURRENT_SESSION_VERSION = 3`）。压缩**只追加** `CompactionEntry`，不删除任何旧条目；投影重建时取「最新 compaction + 从 `firstKeptEntryId` 起的保留段 + compaction 之后的条目」，更早的原始条目仍在文件里但不再进入模型。恢复用 `SessionManager.open()` / `continueRecent()` 读回文件后直接按持久化断点重建，**不重跑压缩**。`/tree` 在同一文件内移动叶子；离开的分支可按需生成 `BranchSummaryEntry`（`fromId` 指回跳转点），摘要预算 `contextWindow - reserveTokens(16384)`，输出上限 4096 token，格式到 `Next Steps` 止。`/fork`、`/clone` 走 `createBranchedSession()`，把选中分支复制成**新会话文件**。pi 没有 checkpoint/rewind 机制，回退靠树导航或 fork。

**关键参数与默认值**
- 版本：`CURRENT_SESSION_VERSION = 3`
- 分支摘要：`reserveTokens = 16384`，`maxTokens = min(4096, model.maxTokens)`（`branch-summarization.ts:305,345`）
- 分支摘要触发：`navigateTree(targetId, { summarize: true })`（`agent-session.ts:3996-4100`）

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/session-manager.ts#L41-L41
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/session-manager.ts#L476-L512
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/session-manager.ts#L543-L573
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/session-manager.ts#L1261-L1287
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/session-manager.ts#L1632-L1632
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/session-manager.ts#L1755-L1801
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L3996-L4140
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/branch-summarization.ts#L293-L382

**可信度**：【已核实】

**源码解读候选**：`buildContextEntries()` —— 一条 compaction 条目如何把「历史」变成「摘要 + 尾巴」

---

## 12. 跨会话记忆

**做法**
**无此能力（无独立记忆子系统）**。源码中没有 `memories/`、memory backend、记忆抽取或记忆注入相关模块；跨会话的「记忆」实际上由项目规则文件（`AGENTS.md` / `CLAUDE.md`）和扩展自行承担。没有写入时机、整理合并、检索、按项目隔离、过期删除这些机制。

**关键参数与默认值**
- 无

**来源**
- 全仓检索：`packages/coding-agent/src` 内 `memories|long-term memory|memoryBackend` 无匹配（2026-10-18）
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/README.md#L15-L19 ——（可扩展但默认最小）

**可信度**：【已核实】（未找到实现）

---

## 13. 缓存友好设计

**做法**
pi 的缓存策略有三层。第一层是**提示词 section 化**：系统提示词被拆成具名 section，变化时只追加一个 section patch，未变部分字节不变，前缀缓存得以保留。第二层是**压缩请求不写缓存**：`completeSummarization()` 显式设置 `cacheRetention: "none"`，理由是一次性摘要不太可能复用，写缓存反而污染。第三层是**缓存预热**：`CacheWarmer` 在 TTL 的 90% 处（至少留 10 秒）重放一次请求以保温，默认模式 `streaming`；只有当「预计避免的 miss 成本 − 刷新成本」≥ $0.05 时才执行，并有 60 分钟（streaming）/ 30 分钟（idle）安全上限。`cache-stats.ts` 统计「上次命中、这次未命中」的浪费，噪声下限 1024 token。压缩与缓存的权衡是明确的：压缩会重写前缀、必然造成一次缓存失效，但换来后续更小的上下文。

**关键参数与默认值**
- `cacheWarming: "streaming"`（`settings-defaults.ts:61`）
- 预热触发点：TTL × 0.9 且至少提前 10 秒（`cache-warmer.ts:28-31`）
- 节省下限：`$0.05`（`cache-warmer.ts:20`）
- 安全上限：streaming 60 分钟、idle 30 分钟（`cache-warmer.ts:16-18`）
- 摘要请求：`cacheRetention: "none"`（`compaction.ts:627-633`）

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/cache-warmer.ts#L14-L31
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/settings-defaults.ts#L61-L61
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L619-L639
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/system-prompt.ts#L212-L229

**可信度**：【已核实】

---

## 14. 失败恢复

**做法**
上下文溢出走专用路径：命中 provider 的 context overflow，或可恢复的 `length` 停止时，先 `_omitRecoveryAttempt()` 把失败的 assistant 与配对工具结果用 `context_edit` 省略，再 `_runAutoCompaction("overflow", willRetry)`；`_overflowRecoveryAttempted` 保证**只允许一次** compact-and-retry，第二次直接报「recovery failed after one compact-and-retry attempt」。摘要生成失败（`error` / `length` / 尝试调工具）直接抛错，**不写检查点**；因此失败的压缩不会留下半截摘要。瞬时流中断由 `retryAssistantCall()` 包装（默认 `maxRetries = 3`）。用户或扩展取消时保留已发生的编辑，但不追加 compaction。压缩失败会发 `compaction_end` 与 `session_compact_failed` 事件。手动压缩先 abort 当前回合，成功提交后**不会**续跑被打断的那一轮。

**关键参数与默认值**
- 溢出恢复次数：1 次（`_overflowRecoveryAttempted`）
- 摘要重试：沿用 `retry.maxRetries = 3`（`settings-defaults.ts:18-22`）
- 摘要失败不落盘：`getSummarizationFailure()` + `throw`（`compaction.ts:585-593,755-761`）
- 无「压缩无进展」守卫、无本地救援层

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L3007-L3077
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L3049-L3076
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L585-L593
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/compaction/compaction.ts#L619-L639
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/settings-defaults.ts#L18-L26

**可信度**：【已核实】

---

## 15. 扩展点

**做法**
pi 的扩展是**进程内 TypeScript 模块**，工厂函数可注册工具、命令、provider、渲染器和事件处理器。与上下文管理直接相关的事件有：`context`（每次 LLM 调用前改写不含 system 的消息，pi 之后会恢复 prompt/tool 状态）、`context_with_system`（在 `context` 之后，处理器拥有完整 prompt 与工具声明）、`before_provider_request`（替换最终 payload）、`before_agent_start`（改 `systemPromptOptions`、注入消息、切换工具集）、`session_before_compact`（取消压缩，或提供 `{summary, firstKeptEntryId, tokensBefore, usage, details}`）、`session_compact` / `session_compact_failed`（只观测）、`session_before_tree` / `session_before_switch` / `session_before_fork`（取消或自定义分支摘要）。最重的接缝是 `session_before_compact`：它把压缩产物完全交给扩展，扩展可以换模型、换格式、甚至整段替换摘要算法。但阈值本身来自 settings，扩展改不了内置阈值常量。

**关键参数与默认值**
- `session_before_compact` 的 `reason: "manual" | "threshold" | "overflow"`、`willRetry: boolean`
- `preparation` 暴露 `messagesToSummarize` / `turnPrefixMessages` / `isSplitTurn` / `tokensBefore` / `previousSummary` / `fileOps` / `settings`
- 无「注册自定义压缩方法」的注册表（只能整段替换，不能插进方法链）

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/extensions/types.ts#L770-L872
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/extensions/types.ts#L885-L904
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/extensions/types.ts#L932-L957
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/core/agent-session.ts#L2820-L2842

**可信度**：【已核实】

**源码解读候选**：`session_before_compact` —— 把「压缩」做成可替换的扩展契约

---

## 16. 评估与可观测

**做法**
pi 自带 `packages/evals`：用 `vitest-evals` 跑行为评测，支持两类。`*.docs.eval.ts` 是「文档增益」对照：同一 case 分别在 `without_docs` 与 `with_docs` 容器里跑，报告 lift；其他 `*.eval.ts` 是单臂 host eval，不做配对比较。运行器负责构建两个镜像、发现 case、按 `(case, variant, repetition)` 展开任务、配对两臂并计算差异。运行时可观测包括：footer 的累计 input/output/cacheRead/cacheWrite、缓存命中率、成本；`cache-stats.ts` 统计缓存浪费。**没有**针对「上下文策略」的内置 A/B 指标（例如压缩前后任务成功率、信息保留率）——现有评测偏向 agent 行为与文档增益，上下文策略对比需要自建。

**关键参数与默认值**
- 评测框架：`vitest-evals`；两臂目录 `without_docs` / `with_docs`
- 缓存统计噪声下限：`NOISE_FLOOR_TOKENS = 1024`（`cache-stats.ts`）
- 无上下文专项指标

**来源**
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/evals/README.md#L1-L40
- https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/packages/coding-agent/src/modes/interactive/components/footer.ts#L120-L197

**可信度**：【已核实】；「无上下文专项指标」为【推断】（基于 README 与目录结构）

---

## 附：与 oh-my-pi 的对照入口

omp 是 pi 的 fork（`README.md#L22`），16 类的逐项差异见 `research/omp.md` 第 17 节。这里只给一句话：pi 是「最小内核 + 一个强扩展缝（`session_before_compact`）」，omp 在此基础上补了**压缩方法链、预压缩裁剪、shake、snapcompact、checkpoint/rewind、记忆后端、子代理**，并把阈值从「固定预留」改成「窗口比例下限」。

---

*配套：`research/source-map/pi.md`。*
