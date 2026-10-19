# Codex CLI · 上下文管理 16 类事实卡片

- **仓库**：https://github.com/openai/codex
- **提交号**：`76ed3b484d62ccceb9fa512ff4dd139f421814c3`（main，快照 2026-10-14）
- **核实日期**：2026-10-18
- **分析范围**：`codex-rs/`（Rust 主体；TS 版 `codex-cli/` 仅作入口，不含上下文逻辑）。行号均以本提交的文件为准，已用 `sed -n` 逐段核对。
- **可信度**：【已核实】= 直接读到实现；【推断】= 由实现与注释合理外推；【待核实】= 本快照内未找到确证。

> 阅读提示：Codex 的请求体是 Responses API 形状，没有独立的「system 字段」，对应物是 `base_instructions`（`instructions`）+ `input` 消息数组。本文一律按「输入项（ResponseItem）」描述。

---

## A. 装什么（组装）

### 1. 请求组装：系统提示词、工具定义、环境信息、历史

**做法**
每个采样步都调用 `build_prompt` 组装一个 `Prompt`：`input`（历史条目）、`tools`（模型可见工具规格）、`base_instructions`（岗位说明书）、`output_schema`（结构化输出）四块。`input` 由 `ContextManager` 持有的历史在写入时做过规范化（补齐/移除配对的工具输出、剥离模型不支持的模态），保证不会出现「有结果没调用」的孤立条目。当 `incremental_tools=true` 时，本次请求把 `tools` 置空、`base_instructions` 置空文本，改由历史里已写入的工具与指令增量承担，避免重复下发。环境信息不是单独字段，而是以 contextual user/developer 片段（`<environment_context>`、`<current_time_reminder>`、AGENTS.md 片段）插入 `input`。权限与沙箱说明同样来自这些片段与工具描述，而不是独立段落。

**关键参数与默认值**
- `parallel_tool_calls`：`true`（`build_prompt` 固定写入）
- `output_schema_strict`：普通会话 `true`；guardian/basic 会话为 `false`
- 历史规范化开关：无配置项，始终执行
- `incremental_tools`：由调用方传入，本文件不设默认值

**来源**
- [client_common.rs#L22-L40](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/client_common.rs#L22-L40)（Prompt 结构）
- [turn.rs#L1666-L1695](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/session/turn.rs#L1666-L1695)（build_prompt）
- [history.rs#L968-L982](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context_manager/history.rs#L968-L982)（normalize_history 四项不变量）

**可信度**：【已核实】

**源码解读候选**：`build_prompt`（turn.rs:1666）——四块拼装 + 增量工具分支，一屏可讲完。

---

### 2. 规则文件的发现与合并（AGENTS.md）

**做法**
从当前工作目录向上找到项目根（默认以 `.git` 为标记），再把「根 → 当前目录」沿途每一级的 `AGENTS.md` 按从浅到深的顺序拼接；不遍历子树，也不越过项目根。每级目录先找 `AGENTS.local.md`，再找 `AGENTS.md`，还可由 `project_doc_fallback_filenames` 追加候选名（含路径分隔符的候选会被忽略）。合并后的总字节数受 `project_doc_max_bytes` 约束，超出部分直接从尾部截掉。规则不是一次性塞进历史：它以 `WorldState` 的一个 section 参与逐轮差分，未变化不重发，变化时发「替换通知 + 新全文」，删除时发「不再适用」通知。项目根标记本身从配置层合并而来，但合并时**显式跳过 Project 层**（避免不可信项目把根目录往上挪），只取受管/用户/系统层。

**关键参数与默认值**
- `project_doc_max_bytes`：默认 `AGENTS_MD_MAX_BYTES` = `DEFAULT_PROJECT_DOC_MAX_BYTES` = 32 KiB（源码注释写明 `// 32 KiB`）
- `project_root_markers`：未设置时默认 `[".git"]`；空列表表示禁用向上遍历
- `project_doc_fallback_filenames`：默认空
- 候选文件名顺序：`AGENTS.local.md` → `AGENTS.md` → 自定义候选

**来源**
- [agents_md.rs#L1-L18](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/agents_md.rs#L1-L18)（发现规则文档注释）
- [agents_md.rs#L225-L285](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/agents_md.rs#L225-L285)（候选文件与向上收集）
- [agents_md.rs#L60-L160](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/agents_md.rs#L60-L160)（按剩余字节截断）
- [agents_md.rs#L190-L220](https://github.com/openai/codex](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/agents_md.rs#L60-L160（按剩余字节截断）
- [agents_md.rs#L190-L220](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/agents_md.rs#L190-L220)（项目根标记合并时跳过 Project 层）
- [mod.rs#L254](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/config/mod.rs#L254)、`#L4483`（32 KiB 默认）
- [agents_md.rs#L36-L80](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context/world_state/agents_md.rs#L36-L80)（差分与替换/移除通知）
- [mod.rs#L380-L395](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context/world_state/mod.rs#L380-L395)（按 section 快照比较）

**可信度**：【已核实】

**源码解读候选**：`WorldStateSection::render_diff`（world_state/agents_md.rs:44）——「只发变化部分」的最小实现。

---

### 3. 按需加载（渐进披露）

**做法**
Codex 的渐进披露有两条。其一是 Skills：`SKILL.md` 的 frontmatter 被解析成元数据，技能按根目录（含内置 `.system` 技能）加载并按显式 `@skill` 提及或命令匹配选中；配置 `skills.include_instructions` 控制是否注入 `<skills_instructions>` developer 块。其二是 **MCP 工具的延迟暴露**：当模型元数据 `supports_search_tool = true` 时，MCP 工具以 `ToolExposure::Deferred` 注册——不进首轮 `Prompt.tools`，只保留检索元数据，由 `tool_search` 工具按需拉取；为 false 时退回 `Direct`，全部工具一次性下发。`tool_search` 本身也只在「模型支持 + 至少有一个可检索的延迟工具」时才会出现在工具表里。用户侧 `@` 引用表现为结构化的工具提及（`ToolMentionKind`、`app://`、`plugin://`），本快照未见把 `@file` 内容直接展开进提示词的通用路径（【推断】）。

**关键参数与默认值**
- `skills.include_instructions`：布尔开关，注释说明控制 `<skills_instructions>` 是否注入；默认值本文件未给出（【待核实】，查 `core/src/config/mod.rs` 的 skills 配置段未找到显式 default）
- 技能根目录：用户/项目技能 + 内置 `SYSTEM_SKILLS_DIR`（`.system`）
- `supports_search_tool`：`#[serde(default)]` 布尔，缺省 **false**；由模型元数据下发
- MCP 工具暴露：`search_tool_enabled ? Deferred : Direct`
- `tool_search` 暴露条件：`supports_search_tool` 且存在 deferred + 有 `search_info` 的工具

**来源**
- [lib.rs#L1-L60](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/skills/src/lib.rs#L1-L60)（加载/解析/提及 API）
- [selection.rs#L44](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/skills/src/selection.rs#L44)（显式技能提及收集）
- [invocation.rs#L26](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/skills/src/invocation.rs#L26)（隐式技能调用识别）
- [mod.rs#L751](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/config/mod.rs#L751)（`<skills_instructions>` 开关）
- [mcp_tool_exposure.rs#L63-L90](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/mcp_tool_exposure.rs#L63-L90)（MCP 延迟/直连二选一）
- [spec_plan.rs#L368-L413](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/tools/spec_plan.rs#L368-L413)（tool_search 暴露条件）
- [tool_executor.rs#L51-L95](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/tools/src/tool_executor.rs#L51-L95)（ToolExposure 语义）
- [openai_models.rs#L481-L482](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/protocol/src/openai_models.rs#L481-L482)（`supports_search_tool` 默认）
- [router.rs#L87-L149](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/tools/router.rs#L87-L149)（模型可见工具表）

**可信度**：【已核实】（skills 开关默认值除外）

---

### 4. 动态注入（状态、提醒、只注入变化）

**做法**
`WorldState` 用稳定的 section id 维护「模型可见状态」，每次采样前逐 section 计算快照并与上次比较，只有变化的 section 才产生 `WorldStateUpdate` 片段；对应到 AGENTS.md 就是「没变不发、变了发替换、删了发移除」。时间等易变信息以独立片段注入：`CurrentTimeReminder` 以 `developer` 角色、`<current_time_reminder>` 标记写入。钩子产生的附加上下文、压缩摘要、子代理通知、图片缩放提示、不支持模态占位都是同类 contextual fragment，按事件插入 `input`，而不是改系统提示词。这种设计让前缀（指令+工具）保持稳定，变化集中在尾部。

**关键参数与默认值**
- section 粒度：`agents_md`、环境、插件等各自独立
- 时间格式：`%Y-%m-%d %H:%M:%S UTC`
- 无「变更阈值」，任何字节差异即视为变化

**来源**
- [mod.rs#L380-L395](https://github.com/openai/codex](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/tools/router.rs#L87-L149（模型可见工具表）

**可信度**：【已核实】（skills 开关默认值除外）

---

### 4. 动态注入（状态、提醒、只注入变化）

**做法**
`WorldState` 用稳定的 section id 维护「模型可见状态」，每次采样前逐 section 计算快照并与上次比较，只有变化的 section 才产生 `WorldStateUpdate` 片段；对应到 AGENTS.md 就是「没变不发、变了发替换、删了发移除」。时间等易变信息以独立片段注入：`CurrentTimeReminder` 以 `developer` 角色、`<current_time_reminder>` 标记写入。钩子产生的附加上下文、压缩摘要、子代理通知、图片缩放提示、不支持模态占位都是同类 contextual fragment，按事件插入 `input`，而不是改系统提示词。这种设计让前缀（指令+工具）保持稳定，变化集中在尾部。

**关键参数与默认值**
- section 粒度：`agents_md`、环境、插件等各自独立
- 时间格式：`%Y-%m-%d %H:%M:%S UTC`
- 无「变更阈值」，任何字节差异即视为变化

**来源**
- [mod.rs#L380-L395](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context/world_state/mod.rs#L380-L395)
- [agents_md.rs#L44-L80](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context/world_state/agents_md.rs#L44-L80)
- [current_time_reminder.rs#L9-L45](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context/current_time_reminder.rs#L9-L45)
- [contextual_user_message.rs#L1-L40](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context/contextual_user_message.rs#L1-L40)（片段注册表）
- [image_resize_notice.rs#L22-L40](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context/image_resize_notice.rs#L22-L40)

**可信度**：【已核实】

**源码解读候选**：`WorldState` 的 section 差分（world_state/mod.rs:380）——「只注入变化」的通用骨架。

---

## B. 量多少（预算）

### 5. Token 计量与阈值

**做法**
当前用量 = 上一次服务端 `usage.total_tokens` + 最后一条模型输出之后的本地估算增量（`get_total_token_usage`）。由此派生两条线：整段线 `full_context_window_limit = W × effective_context_window_percent / 100`（默认 95%），用作硬检查；范围线 `auto_compact_scope_limit = min(模型字段 auto_compact_token_limit, 90% × W)`，用作软触发。范围可按 `model_auto_compact_token_limit_scope` 取 `Total`（比全部材料）或 `BodyAfterPrefix`（只比首轮前缀之后的增长量）。到线判定为「（范围线 + TokenBudget 回退缓冲）达到」或「整段线达到」。另有轮后阈值 `model_post_turn_compact_threshold_percent`（默认 0 表示关闭）。

**关键参数与默认值**
- `effective_context_window_percent`：默认 `95`
- 范围线基数：`(W × 9) / 10`（90%），可被 `auto_compact_token_limit` 按下取 min
- `auto_compact_token_limit_scope`：`Total` / `BodyAfterPrefix`
- `model_post_turn_compact_threshold_percent`：默认 `0`
- 无 `/context` 类可视化命令；用量以事件形式上报 TUI（具体呈现方式【待核实】）

**来源**
- [openai_models.rs#L393-L395](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/protocol/src/openai_models.rs#L393-L395)（95 默认）
- [openai_models.rs#L517-L540](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/protocol/src/openai_models.rs#L517-L540)（usable/auto_compact_token_limit）
- [context_window.rs#L60-L110](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/session/context_window.rs#L60-L110)（两条线与到线判定）
- [turn.rs#L180-L200](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/session/turn.rs#L180-L200)（轮前检查）

**可信度**：【已核实】（UI 呈现除外）

---

## C. 怎么减（减量）

### 6. 单次工具输出控制（截断 + 落盘引用）

**做法**
工具输出在**写入活历史时**按 `TruncationPolicy` 限长：token 策略用 `ceil(bytes/4)` 估算，左预算取 floor、右预算取「总数 − 左」，UTF-8 边界对齐，中间替换为 `…N tokens truncated…` 标记。多块输出（文本/音频混合）共享同一预算，逐块扣减，超出部分折叠成省略计数；序列化与头部另留 20% 余量（`policy * 1.2`）。工具出口还有一层 `formatted_truncate_text`，在正文前加「原始 token 数 + 总行数」的说明头。被裁掉的中间原文仍完整保存在 rollout 存档里，需要时可从存档找回（不是重新执行工具）。

**关键参数与默认值**
- 估算比：`APPROX_BYTES_PER_TOKEN = 4`
- 序列化余量：×1.2
- 具体阈值来自模型元数据 `truncation_policy`（例如 `tokens(10_000)`），源码不写死；缺失时由调用方传入策略
- 多块共享预算；标记文本不占保留预算

**来源**
- [truncate.rs#L17-L29](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/utils/string/src/truncate.rs#L17-L29)（plan_token_truncation / marker）
- [truncate.rs#L62-L90](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/utils/string/src/truncate.rs#L62-L90)（split_budget + UTF-8 对齐）
- [lib.rs#L17-L34](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/utils/output-truncation/src/lib.rs#L17-L34)（×1.2 与说明头）
- [lib.rs#L164-L200](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/utils/output-truncation/src/lib.rs#L164-L200)（多块共享预算）
- [history.rs#L560-L580](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context_manager/history.rs#L560-L580)（写入时应用策略，注释说明只作用于 live history）

**可信度**：【已核实】

**源码解读候选**：`truncate_middle_with_token_budget`（truncate.rs:69）——20 行讲清「头尾保留 + 中间丢弃」。

---

### 7. 历史裁剪（不调用模型）

**做法**
Codex 没有「定期清空旧工具结果」的独立通道；不调用模型的减量只有三类：写入历史时的输出截断（上一类）、压缩重试时删除最旧条目（`remove_first_item`，见第 14 类）、以及规范化阶段的丢弃（移除无配对输出、剥离模型不支持的图片/音频）。`remove_first_item` 选择最旧条目并同步移除其配对的另一半，避免产生孤立调用。恢复会话时回放历史也会重新套用当前截断策略，因此同一份存档在不同策略下恢复出的活历史长度可能不同。

**关键参数与默认值**
- 无独立阈值；由截断策略与压缩失败分支驱动
- 规范化固定执行 4 项：补输出、删孤立输出、剥图片、剥音频

**来源**
- [history.rs#L685-L700](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context_manager/history.rs#L685-L700)（remove_first_item）
- [history.rs#L968-L982](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context_manager/history.rs#L968-L982)（normalize 四项）
- [rollout_reconstruction.rs#L508-L515](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/session/rollout_reconstruction.rs#L508-L515)（回放时按策略截断）
- 反证：全仓未找到类似「clear old tool results」的独立 pass（`grep -rn "clear.*tool" core/src` 无命中）

**可信度**：【已核实】

---

### 8. 压缩（调用模型做摘要）

**做法**
本地压缩只把「真实用户消息」纳入候选（排除摘要前缀、排除 FINAL_ANSWER 类代理消息），预算 20,000 token，从新到旧累加，遇到放不下就停止，再把摘要作为独立条目追加。远端 v2 由服务端完成压缩：保留消息共享 64,000 token 预算，单条 AgentMessage 上限 10,000，流重试 2 次，并要求响应里 `compaction_count` 恰好为 1。触发时机有三处：轮前（新输入写入前）、轮中（需要 follow-up 且到线）、轮后（可选阈值）；默认关的后台/投机压缩另算（第 14 类）。压缩完成后用替代历史覆盖内存历史，并向 rollout 追加一条 `CompactedItem` 检查点（含 `replacement_history`、window id、token 用量、resume 元数据）。

**关键参数与默认值**
- `COMPACT_USER_MESSAGE_MAX_TOKENS`：`20_000`
- 远端保留预算：`RETAINED_MESSAGE_TOKEN_BUDGET = 64_000`；单条上限 `10_000`；重试 `2`
- 验收：`compaction_count` 必须为 1，否则 Fatal
- 摘要模板：9 行，要求「进度与决策 / 约束与偏好 / 待办 / 关键数据」
- 手动压缩：`/compact [附加说明]`，走 `tasks/compact.rs`；附加说明拼进模板

**来源**
- [compact.rs#L63-L64](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/compact.rs#L63-L64)（20k 预算）
- [compact.rs#L622-L643](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/compact.rs#L622-L643)（候选判定：真实用户消息）
- [compact.rs#L723-L802](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/compact.rs#L723-L802)（从新到旧、预算耗尽即停）
- [compact_remote_v2.rs#L87-L91](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/compact_remote_v2.rs#L87-L91)（64k/10k/2）
- [compact_remote_v2.rs#L458-L466](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/compact_remote_v2.rs#L458-L466)（completed 与 count 校验）
- [prompt.md#L1-L9](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/prompts/templates/compact/prompt.md#L1-L9)（摘要模板）
- [compact.rs#L25-L60](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/tasks/compact.rs#L25-L60)（手动压缩入口）
- [mod.rs#L4321-L4376](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/session/mod.rs#L4321-L4376)（替换历史 + 写 CompactedItem）

**可信度**：【已核实】

**源码解读候选**：`compact.rs` 的候选选择循环（L600-L660）——「保留谁」比「怎么摘要」更值得讲。

---

### 9. 多模态上下文

**做法**
图片默认随消息直通模型；当图片被缩放时，Codex 追加一条 `<image_resize_notice>` 片段，告知原尺寸与处理后尺寸，但不重发图片。模型不支持某模态时，历史规范化把图片/音频替换为固定占位文本（「image content omitted because you do not support image input」），避免请求被拒。音频在截断预算中单独估算 token，不按字节折算；压缩时可启用 `CompactionImageBudget` 为图片保留单独预算。Codex **没有**「把历史渲染成图片」「把附件转成文字描述」这两类做法。

**关键参数与默认值**
- `Feature::CompactionImageBudget`：`Stage::Stable`、`default_enabled = true`
- 缩放提示：只报尺寸，不带图
- 无「历史转图」

**来源**
- [image_resize_notice.rs#L1-L40](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context/image_resize_notice.rs#L1-L40)
- [unsupported_media.rs#L7-L22](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context/unsupported_media.rs#L7-L22)
- [lib.rs#L2072-L2076](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/features/src/lib.rs#L2072-L2076)（CompactionImageBudget）
- [lib.rs#L160-L175](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/utils/output-truncation/src/lib.rs#L160-L175)（estimate_audio_token_count 注入）

**可信度**：【已核实】

---

## D. 怎么隔离、怎么延续

### 10. 子代理隔离

**做法**
子代理通过多代理工具（`spawn_agent` 等）创建：为子会话构造独立 `Config`，继承父会话的 `base_instructions`，再叠加 `subagent_developer_instructions`；自己的历史、token 计数、rollout 都是独立的。父子之间通过代理间消息（`InterAgentCommunication`）通信，子代理的完成消息作为一条输入项回到父会话，而不是把子代理全部上下文并回父会话。父会话可以用 `send_message`、`followup_task`、`wait_agent` 等工具追加指令或等待结果。是否提供 worktree 级文件隔离在本快照的 core 中未见明确实现（相关能力在运行环境/应用层，【待核实】）。

**关键参数与默认值**
- 继承：`base_instructions` 文本 + provenance；`developer_instructions` 可被 `subagent_developer_instructions` 覆盖
- 子会话 token 预算：独立，不与父共享
- 并发上限：未在源码中找到统一常量（【待核实】）

**来源**
- [child_config.rs#L55-L160](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/agent/child_config.rs#L55-L160)
- [spawn.rs#L37](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs#L37)（spawn_agent）
- [wait.rs#L24](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/tools/handlers/multi_agents_v2/wait.rs#L24)（wait_agent）
- `codex-rs/core/src/tools/handlers/multi_agents_v2/send_message.rs`、`followup_task.rs`（追加指令）
- [multi_agents_spec.rs#L570-L610](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/tools/handlers/multi_agents_spec.rs#L570-L610)（输入项类型与 mention）
- `codex-rs/core/src/context/inter_agent_completion_message.rs`
- [rollout_reconstruction.rs#L512-L515](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/session/rollout_reconstruction.rs#L512-L515)（回放 InterAgentCommunication）

**可信度**：【已核实】（worktree 隔离为【待核实】）

---

### 11. 会话时间线（持久化、恢复、分叉）

**做法**
会话以 rollout 追加日志为唯一真实来源：每条输入、工具调用、压缩检查点、world state 都按序追加，旧记录不删除。恢复时先找到最新的 `CompactedItem`，用它的 `replacement_history` 作为起点，再回放其后的后缀（ResponseItem、RetainedContext、InterAgentCommunication 等），即「持久化断点 + 后缀回放」，而不是从头重放整段对话。压缩只覆盖内存中的活历史，存档里的原始记录仍然保留，因此摘要不可逆不等于源记录被删。分叉（fork）在 app-server 协议层有独立参数（`ThreadForkParams`），core 侧以历史版本号与 checkpoint 支持；具体 UI 语义【待核实】。

**关键参数与默认值**
- 存档单位：JSONL rollout，追加写
- 检查点字段：`replacement_history`、`window_number`、`first/previous/window_id`、`latest_token_usage_record`、`resume_metadata`
- 恢复策略：最新 checkpoint + 后缀回放
- 无自动过期删除策略（由上层清理）

**来源**
- [mod.rs#L4321-L4376](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/session/mod.rs#L4321-L4376)（CompactedItem 写入）
- [rollout_reconstruction.rs#L485-L520](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/session/rollout_reconstruction.rs#L485-L520)（选择 checkpoint + 回放后缀）
- [history.rs#L520-L545](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context_manager/history.rs#L520-L545)（live 截断 vs rollout 原载荷的注释）
- [thread.rs#L544-L560](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/app-server-protocol/src/protocol/v2/thread.rs#L544-L560)（ThreadForkParams）

**可信度**：【已核实】（fork UI 为【待核实】）

**源码解读候选**：`rollout_reconstruction` 的「checkpoint + suffix」分支（L490-L520）。

---

### 12. 跨会话记忆

**做法**
`memories` 管线在根会话启动时触发（非临时会话、功能开启、非子代理、状态库可用），后台异步跑两阶段：Phase 1 从各线程的 rollout 提取候选记忆，Phase 2 做合并/整合并落成产物。读取路径由 `codex-memories-read` 负责：把记忆作为 developer 指令注入，并解析模型对记忆的引用（citations）做使用统计。写入与读取分属两个 crate，模板随 crate 存放，读路径有独立的引用解析与遥测分类。是否按项目隔离由状态库与工作区决定，本快照的 README 只描述触发条件与两阶段，不描述检索排序（【待核实】）。

**关键参数与默认值**
- 触发：根会话启动；`ephemeral` 会话不跑；子代理会话不跑
- 阶段：Phase 1 提取 → Phase 2 整合
- 无用户可见的「记忆条数上限」常量（【待核实】）

**来源**
- [README.md#L1-L40](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/memories/README.md#L1-L40)
- `codex-rs/memories/read/templates/memories/read_path.md`（读路径模板）
- `codex-rs/memories/write/templates/memories/stage_one_system.md`、`consolidation.md`（写路径模板）

**可信度**：【已核实】（触发与分阶段）；检索/排序细节【待核实】

---

## E. 怎么保证质量

### 13. 缓存友好设计

**做法**
CLI 侧只做两件事：发 `prompt_cache_key`，以及解析响应里的缓存明细。键的取值优先用 `prompt_cache_key_override`；内部子会话用 `{source}:{parent_thread_id}`；其余用 `session_id`。响应 usage 里的 `input_tokens_details.cached_tokens` / `cache_write_tokens` 被解析进 `TokenUsage.cached_input_tokens` / `cache_write_input_tokens`，用于计量与变更检测。命中率、TTL、断点位置都由服务端决定，源码读不出。设计上，稳定的 `base_instructions` + 工具表在前、变化片段追加在尾部，与「前缀不变、只在末尾追加」的缓存友好原则一致。

**关键参数与默认值**
- 键：`session_id`（默认）/ `{source}:{parent_thread_id}`（内部子会话）/ override
- 缓存 Token 字段：`cached_tokens`、`cache_write_tokens`
- TTL：服务端决定，CLI 无参数

**来源**
- [client.rs#L646-L665](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/client.rs#L646-L665)（prompt_cache_key）
- [responses.rs#L117-L151](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/codex-api/src/sse/responses.rs#L117-L151)（usage 解析）
- [protocol.rs#L2362-L2382](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/protocol/src/protocol.rs#L2362-L2382)（TokenUsage 字段）

**可信度**：【已核实】（仅 CLI 可证部分）

---

### 14. 失败恢复

**做法**
压缩请求自身超窗（`ContextWindowExceeded`）时，如果待压缩输入不止一条，就删掉最旧一条、重置重试计数后重试；只剩一条则把总量标记为满并返回错误。普通错误按 provider 退避重试；中断、取消、会话预算耗尽、响应不完整直接返回错误，不重试。压缩流中途的条目改为「成功后一次性提交」，避免半提交。后台/投机压缩属于开发中特性：`Feature::AsyncCompaction` 为 `UnderDevelopment` 且默认关，阈值默认 65% 全窗，失败只记日志丢弃，但已发生的用量照常计费。

**关键参数与默认值**
- 后台压缩阈值：`DEFAULT_ASYNC_COMPACTION_THRESHOLD_PERCENT = 65`
- 后台压缩门槛：feature 开 且 未启用 TokenBudget 且 provider 支持 `RemoteCompactionV2`
- 重试：远端流 2 次；本地普通错误走 provider 退避
- 本快照未见会话级「连续失败熔断」（与 Claude Code 的 3 次熔断不同，【推断】）

**来源**
- [compact.rs#L345-L380](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/compact.rs#L345-L380)（四类失败分支）
- [mod.rs#L225](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/config/mod.rs#L225)（65 默认）
- [lib.rs#L2064-L2070](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/features/src/lib.rs#L2064-L2070)（AsyncCompaction：UnderDevelopment / false）
- [async_compaction.rs#L44-L56](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/session/async_compaction.rs#L44-L56)（enabled 条件）
- [async_compaction.rs#L125-L140](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/session/async_compaction.rs#L125-L140)（丢弃但计量）

**可信度**：【已核实】

---

### 15. 扩展点

**做法**
Codex 提供四类扩展：hooks（`hook_runtime` 负责生命周期事件，`hook_mcp_executor` 负责 MCP 侧执行）、skills（`SKILL.md` + frontmatter）、plugins（打包 skills/MCP/apps，并在提示词里说明命名前缀）、MCP 服务器（工具并入统一工具表）。钩子的附加上下文以 `hook_additional_context` 片段进入历史。压缩本身**没有**用户可替换的钩子：流程写死在 `compact.rs` / `compact_remote_v2.rs`，只能通过 provider 能力与 feature 开关影响走哪条路径。

**关键参数与默认值**
- hook 事件：由 `codex_hooks` 定义；`SessionStartSource::Compact` 会在压缩后触发会话启动钩子
- 插件技能命名：`plugin_name:` 前缀
- 自定义压缩：无

**来源**
- `codex-rs/core/src/hook_runtime.rs`、`codex-rs/core/src/hook_mcp_executor.rs`
- `codex-rs/core/src/context/hook_additional_context.rs`
- [available_plugins_instructions.rs#L33-L42](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/context/available_plugins_instructions.rs#L33-L42)
- [mod.rs#L4375-L4380](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/session/mod.rs#L4375-L4380)（压缩后 SessionStart）

**可信度**：【已核实】（「无自定义压缩」为源码反证：【已核实】）

---

### 16. 评估与可观测

**做法**
Codex **没有**面向用户的评测框架或 A/B 实验入口；可观测性来自三类副产品：rollout 存档（可离线重放并统计 token/工具调用）、analytics 事件、OTEL 追踪。因此「用评测数据证明某种策略更好」需要外部脚本读 rollout 自行计算，工具本身不提供指标定义。这一点与教程 L5 的要求有差距，写作时应明确「工具不自带评测」。

**关键参数与默认值**
- 无评测集、无指标定义、无 A/B 开关
- 可用原始数据：rollout JSONL、`TokenUsage`、trace

**来源**
- 反证：`codex-rs/` 下无 `eval`/`benchmark` crate；`codex-rs/otel` 与 `codex-rs/analytics` 仅提供遥测
- [rollout_reconstruction.rs#L485-L520](https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/codex-rs/core/src/session/rollout_reconstruction.rs#L485-L520)（存档可重放）

**可信度**：【已核实】（「无内置评测」为反证结论）

---

## 附：16 类速查

| # | 类别 | Codex 是否有 | 一句话 |
|---|---|---|---|
| 1 | 请求组装 | 有 | Prompt{input,tools,base_instructions,output_schema} |
| 2 | 规则文件 | 有 | AGENTS.md 根→cwd 拼接，32 KiB 上限，差分注入 |
| 3 | 按需加载 | 有 | Skills 描述先行；MCP 工具按 `supports_search_tool` 延迟 |
| 4 | 动态注入 | 有 | WorldState section 差分 + contextual fragments |
| 5 | 计量 | 有 | 95% 硬线 / 90% 软线，无 /context |
| 6 | 单次输出 | 有 | 头尾保留 + 中间标记；原文留存档 |
| 7 | 历史裁剪 | 部分 | 仅规范化丢弃与压缩重试删最旧，无定期清理 |
| 8 | 压缩 | 有 | 本地 20k 保留 / 远端 64k；三时机触发 |
| 9 | 多模态 | 部分 | 图片直通 + 缩放提示；无历史转图 |
| 10 | 子代理 | 有 | 独立 Config/历史，消息回传 |
| 11 | 会话 | 有 | rollout 追加 + checkpoint + 后缀回放 |
| 12 | 跨会话记忆 | 有 | 两阶段后台管线 + 读路径注入 |
| 13 | 缓存 | 有（客户端侧） | 发 key、认明细，TTL 服务端定 |
| 14 | 失败恢复 | 有 | 删最旧重试；后台压缩默认关 |
| 15 | 扩展点 | 有 | hooks/skills/plugins/MCP；压缩不可替换 |
| 16 | 评估 | 无 | 无评测框架，只有遥测与存档 |
