# Grok Build · 上下文管理事实卡片

- **仓库**：https://github.com/xai-org/grok-build（Rust 源码，`crates/`；由 SpaceXAI 内部 monorepo 定期同步）
- **本快照提交号**：`2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8`（`main`）
- **`SOURCE_REV`**：`559751fdcec02d413e4c57c8832ab275e4f44980` —— 仓库 README 说明该文件记录「本树代码对应的 monorepo 完整提交 SHA」，即本快照对应 monorepo rev `559751f`，不是某个语义化版本号；仓库未带 tag，因此**具体发布版本号未在源码中找到**。
- **核实日期**：2026-10-18
- **分析范围**：`crates/codegen/*`（agent / shell / pager / tools / memory / compaction 接入层）、`crates/common/xai-grok-compaction`、`crates/codegen/xai-grok-pager/docs/user-guide/*`（仓库内自带用户手册）。不分析 TUI 渲染细节、不分析服务端推理行为。
- **Permalink 基址**：`https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/`
- **可信度标签口径**：【已核实】= 直接读到源码实现并核对行号；【推断】= 只读到同仓文档（README / `docs/user-guide`）或由多处源码间接推出，未逐行验证；【待核实】= 未找到。
- **与第二版的关系**：第二版只有闭源二进制的字符串/行为观测。本版首次拿到源码，**全部以源码为准**；第二版结论仅在末尾「交叉印证」小节出现，冲突时以本卡片为准。
- **官方文档**：`docs.x.ai/build/*` 只覆盖命令索引级信息（`/compact [context]`、`/context`、状态栏阈值变色），机制细节以源码与仓库内 `docs/user-guide` 为准。

---

## 1. 请求组装

**做法**
系统提示词是一份 MiniJinja 风格模板 `crates/codegen/xai-grok-agent/templates/prompt.md`，由 `PromptContext` 提供占位符、`ToolBridge::render_prompt()` → `TemplateRenderer` 渲染；模板按 `PromptMode`（`Extend` 默认 / `Full`）与 `PromptAudience`（`Primary` / `Subagent`）选择基础模板，`Extend` 时自定义 body 追加在基础模板之后。工具定义不嵌在系统提示词里，而是作为独立 `ToolDefinition` 数组随请求发送；MCP 工具**不在**该数组里（`tool_definitions.json` 明确不写 `server__tool` 条目），模型通过 `search_tool` / `use_tool` 间接调用。历史消息来自 `xai-chat-state` 的对话项序列（system / user / assistant / tool result），请求前还会做一次「按需裁剪」的副本变换（见第 7 类）。第一条用户消息不是用户原文，而是一个前缀包：`<user_info>`（OS、shell、cwd、当天日期）＋ 规则区块（AGENTS.md 等，包在 `<system-reminder>`/`<rules>` 里）＋ 技能清单 ＋ MCP 服务器清单 ＋ workflow 清单，然后才是 `<user_query>` 包裹的真实请求。系统提示词在会话内可被重新渲染：模型族切换或身份 label 变更时会重渲染并改写会话里的 system 项（`skip_prompt_rewrite` 为 false 时）；同一模型内不每轮重写，以保前缀稳定。

**关键参数与默认值**

| 项 | 值 | 说明 |
|---|---|---|
| 默认身份标签 | `"Grok"`（`DEFAULT_SYSTEM_PROMPT_LABEL`） | 模板首句 `You are <label> released by xAI` |
| `PromptMode` 默认 | `Extend` | 基础模板 + 可选 body |
| `PromptAudience` 默认 | `Primary` | 子代理用紧凑模板且不注入 persona 目录 |
| 模板变体 | `none` / `codex` / `{custom}` | `TemplateOverride`，`codex` 走 `apply_patch_prompt.md` |
| 压缩后系统提示词 | 固定常量 `COMPACT_SYSTEM_PROMPT`（两句话） | 见第 8 类 |
| 工具/MCP 分流 | MCP 工具不进入 function tools | 由 `search_tool`/`use_tool` 承接 |

**来源**
- 模板正文：`crates/codegen/xai-grok-agent/templates/prompt.md#L1-L40`
- 模板选择与占位符：`crates/codegen/xai-grok-agent/src/prompt/context.rs#L11-L40`、`#L70-L146`
- 首条用户消息构成：`crates/codegen/xai-grok-agent/src/prompt/user_message.rs#L1-L16`
- 渲染入口：`crates/codegen/xai-grok-agent/src/prompt/context.rs#L1-L9`
- MCP 工具不写入 `tool_definitions.json`：`crates/codegen/xai-grok-pager/docs/user-guide/17-sessions.md#L30-L42`
- 模板变体枚举：`crates/codegen/xai-grok-agent/src/prompt/context.rs#L12-L24`

**可信度**：【已核实】

**源码解读候选**：`prompt.md` 的条件模板（`${%- if tools.by_kind.task %}` / `memory_v2_enabled`）如何让同一份提示词在「有子代理 / 有记忆 / 无 shell」等组合下变形，而工具名来自 `ToolKind → name` 映射（`TemplateRenderer`）。

---

## 2. 规则文件的发现与合并

**做法**
每个目录按固定候选名探测，**同一目录命中的文件全部加载**（不是只取第一个）：`Agents.md`、`Claude.md`、`CLAUDE.md`、`CLAUDE.local.md`、`AGENT.md`、`AGENTS.md`；Claude 兼容开启时追加 `.claude/CLAUDE.md` 与 `.claude/CLAUDE.local.md`。除具名文件外，还扫描规则目录里的**所有 `*.md`**：`<dir>/.grok/rules/` 恒扫，`<dir>/.claude/rules/`、`<dir>/.cursor/rules/` 受兼容开关控制；每个规则目录内按字母序。home 级根先加载（`$GROK_HOME`/`~/.grok`、`~/.claude`、`~/.cursor`、`[paths] extra_rule_dirs`），随后是项目根到 cwd 的逐级目录——因此**越深的文件越靠后，冲突时后者胜出**。项目级来源受 folder trust 门禁（未信任则整段丢弃），`.gitignore` 命中则跳过（`extra_rule_dirs` 例外）。同一物理文件用 canonical path 去重；跨目录内容重复不做折叠。**每个文件全文加载，没有字符上限、没有截断**（官方用户手册明确写「no character cap and no truncation」），体积成本完全由用户承担；`grok inspect` 只展示路径与近似 token 数。另外存在 `--rules`（追加到系统提示词，包 `<human_rules>`）与 `--system-prompt-override`（替换整段）两个会话级入口。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 具名候选（按序） | `Agents.md`, `Claude.md`, `CLAUDE.md`, `CLAUDE.local.md`, `AGENT.md`, `AGENTS.md` |
| Claude 专属候选 | `.claude/CLAUDE.md`, `.claude/CLAUDE.local.md`（`compat.claude.agents` 控制） |
| 规则目录 | `.grok/rules`（恒开）、`.claude/rules`、`.cursor/rules` |
| home 规则根 | `$GROK_HOME/rules/`、`~/.claude/rules/`、`~/.cursor/rules/`、`[paths] extra_rule_dirs` |
| 体积上限 / 截断 | **未在源码中找到**（`read_agents_config_with_roots` 直接 `read_to_string`，无长度判断） |
| 去重 | canonical path |
| 目录信任 | 项目级来源需要 `--trust` 或交互授权 |

**来源**
- 候选名常量：`crates/codegen/xai-grok-config/src/compat.rs#L311-L318`
- 规则目录与文件名解析：`crates/codegen/xai-grok-config/src/compat.rs#L418-L438`
- 发现与排序（home → configured → project）：`crates/codegen/xai-grok-agent/src/prompt/agents_md.rs#L225-L362`
- 渲染为 `<system-reminder>`：`crates/codegen/xai-grok-agent/src/prompt/agents_md.rs#L364-L372`
- 无体积上限的文档表述：`crates/codegen/xai-grok-pager/docs/user-guide/12-project-rules.md#L183-L186`
- 发现顺序与「深层优先」：`crates/codegen/xai-grok-pager/docs/user-guide/12-project-rules.md#L58-L88`

**可信度**：【已核实】（「无体积上限」为**源码未发现**，不等于永远不存在）

---

## 3. 按需加载（渐进披露）

**做法**
Skills 只在首条用户消息里给出「名称 + 截断后的描述」清单，模型要用时调用 skill 工具读取 `SKILL.md` 正文；清单有硬预算：`上下文窗口 token 数 × 4 × 0.5%` 个字符（200k 窗口约 400k 字符，实际按 4 字节/token 折算），超出后按条目裁剪而不是整段丢弃。MCP 走另一条路：服务器与工具**不进入 function tools**，只注入一段「服务器公告」，模型先用 `search_tool`（BM25 关键词检索）找工具，再用 `use_tool` 调用；单个 MCP 工具/服务器描述硬截断到 2048 字符，公告用 `(tool_count, description_hash, tool_names_hash)` 指纹做变更检测，只在变化时重发。`@` 文件引用在本版源码中没有独立的「附件注入」通道，文件内容一律通过 `read_file` 工具按需读取（带 offset/limit 分页）。技能清单在会话中途发生变化时，由 `apply_pending_skill_update()` 取走 pending 变更并重新公告（`pending = BaselineChange` 时投递新清单），已公告名字集合用于增量判断。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 技能清单预算 | `context_window_tokens × 4 × 0.005` 字符；`SKILL_BUDGET_CONTEXT_PERCENT = 0.5` |
| 未知窗口时的默认预算 | `200_000 × 4 × 0.5% = 400_000` 字符 |
| MCP 描述上限 | 2048 字符 + `… [truncated]` |
| MCP 检索 | BM25（`search_tool`），工具名 `search_tool` / `use_tool` |
| 技能可调用入口 | `user-invocable: true` 的 SKILL.md 直接成为斜杠命令 |

**来源**
- 预算常量：`crates/codegen/xai-grok-tools/src/types/skill_discovery_tracker/listing.rs#L10-L16`
- 预算应用：`crates/codegen/xai-grok-tools/src/types/skill_discovery_tracker/mod.rs#L330-L340`
- 技能清单快照：`crates/codegen/xai-grok-tools/src/bridge.rs#L282-L302`
- 技能公告应用：`crates/codegen/xai-grok-tools/src/bridge.rs#L415-L427`
- MCP 描述截断：`crates/codegen/xai-grok-tools/src/implementations/search_tool/mod.rs#L13-L34`
- `search_tool` 定位：`crates/codegen/xai-grok-tools/src/implementations/search_tool/mod.rs#L1-L10`

**可信度**：【已核实】

---

## 4. 动态注入

**做法**
注入统一走「追加一条 synthetic user 消息 / system-reminder」而不是改历史。每轮用户提交前后会依次尝试：MCP 连接提醒、**跨午夜日期滚动提醒**（一次性，保留启动时缓存的 `<user_info>` 日期以不破坏 prompt cache）、plan mode 提醒、fork 提醒、恢复的后台任务提醒、workflow 状态提醒、任务/子代理完成通知、todo gate 提醒。AGENTS.md 与 persona 也是以 `<system-reminder>` 形式注入用户消息，而不是塞进系统提示词。技能清单、MCP 公告、workflow 清单各自维护「已公告集合」，变化时只发差量/替换块。记忆索引在**首轮**以 `<memory-context>` 区块注入系统提示词；若系统提示词里已存在该标记则跳过（显式为了保 prompt cache）。日期滚动这一条最能说明设计取向：宁可用一条一次性 reminder 也不重写缓存的 `<user_info>`。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 日期滚动提醒 | 跨本地午夜触发一次；不改写 `<user_info>` 启动日期 |
| 记忆首轮注入 | 见第 12 类（`[memory.initial_injection]`，默认 `enabled=true`、`min_score=0.9`） |
| 注入载体 | `<system-reminder>` / 合成 user 消息 |
| 公告去重 | 技能 `announced_names`、MCP `announcement_state.json` 指纹 |

**来源**
- 每轮注入序列：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs#L1123-L1140`
- 日期滚动实现与缓存说明：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/reminders.rs#L507-L522`
- 技能公告 pending 机制：`crates/codegen/xai-grok-tools/src/types/skill_discovery_tracker/mod.rs#L325-L355`
- MCP 公告快照：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/mcp.rs#L1510-L1521`
- 记忆首轮注入与「已有则跳过」：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs#L2243-L2277`

**可信度**：【已核实】

---

## 5. Token 计量与可视化

**做法**
估算核心是 `bytes/4` 启发式：`BYTES_PER_TOKEN = 4`，图片按 `IMAGE_TOKEN_ESTIMATE = 765` 每张计入。`total_tokens` 不是纯估算：它等于**最近一次模型响应上报的 `total_tokens` ＋ 此后新增项的字节估算**（`total_tokens + estimated_tokens_since_model`），所以工具结果在下一轮也会被算进去。`/context` 的四段口径是：`System prompt` = 系统消息的估算；`Messages` = 所有非 system 项的估算；`Reasoning/overhead` = `used − system − messages`（把推理 token、缓存差异等无法归类的一律算进 overhead）；`Free` = `total − used`，四者用 `min()` 逐级夹紧保证不越界。工具定义、Skills、MCP、workflows、AGENTS.md 单独列在「Already counted above」区，**明确标注已包含在上面四项里**，不重复计入。自动压缩阈值解析是 6 级：env `GROK_AUTO_COMPACT_THRESHOLD_PERCENT` → 用户 `[model.<id>]` → 用户 `[session]` → 远端 per-model → 远端全局 → 常量 85；但**随模型目录下发的值优先于常量**（如 `grok-4.6` 目录值 80）。`/context-window` 只在模型声明了多个窗口时出现，接受 `500k` 这类短标签或原始 token 数，会话级生效；底层复用 `SwitchModel` 并带上 `contextWindow` 选择，切换模型族时会立即触发一次压缩，单纯调小窗口则在下一次采样前的 `check_auto_compact_needed()` 触发。**源码里没有「输出预留」概念**：阈值只按 `total_tokens / context_window` 计算，不扣 max_output。

**关键参数与默认值**

| 项 | 值 | 出处 |
|---|---|---|
| 字节/token | `4` | `crates/codegen/xai-token-estimation/src/lib.rs:11` |
| 图片估算 | `765` token/张 | 同上 `:15`（`IMAGE_TOKEN_ESTIMATE`） |
| 自动压缩阈值常量 | `85`（`DEFAULT_AUTO_COMPACT_THRESHOLD_PERCENT`） | `crates/common/xai-grok-compaction/src/code_compaction/config.rs:12` |
| `grok-4.6` 目录阈值 | `80` | `crates/codegen/xai-grok-models/default_models.json:19` |
| `grok-4.6` 上下文窗口 | `500000` | `crates/codegen/xai-grok-models/default_models.json:13` |
| `/context` 行 | System prompt / Messages / Reasoning-overhead / Free | `crates/codegen/xai-grok-pager/src/scrollback/blocks/context_info.rs:312-345` |
| 输出预留 | **未在源码中找到** | — |
| `/context-window` 可见条件 | 模型可选窗口 > 1 | `crates/codegen/xai-grok-pager/src/slash/commands/context_window.rs:21-23` |

**来源**
- 估算原语：`crates/codegen/xai-token-estimation/src/lib.rs#L1-L80`
- `total_tokens` 构成：`crates/codegen/xai-chat-state/src/actor/mod.rs#L371-L374`
- `/context` 快照字段：`crates/codegen/xai-grok-shell/src/session/acp_types.rs#L463-L487`
- 快照装配（system/messages/tools/分类）：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/session_setup.rs#L613-L710`
- 四段口径计算：`crates/codegen/xai-grok-pager/src/scrollback/blocks/context_info.rs#L495-L505`
- 行与「已计入上面」标注：`crates/codegen/xai-grok-pager/src/scrollback/blocks/context_info.rs#L312-L360`、`#L396-L399`
- 阈值 6 级解析：`crates/codegen/xai-grok-shell/src/util/config/resolve/compaction.rs#L36-L89`
- 阈值触发判断：`crates/codegen/xai-grok-shell/src/session/compaction.rs#L2095-L2116`
- `/context-window` 实现：`crates/codegen/xai-grok-pager/src/slash/commands/context_window.rs#L10-L99`
- 窗口选项来源（模型 meta `contextWindows`）：`crates/codegen/xai-grok-sampling-types/src/types.rs#L1049-L1075`
- 模型族切换即时压缩：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/model_switch.rs#L176-L197`

**可信度**：【已核实】；官方文档交叉核对：状态栏文档写「context 值在 auto-compaction 阈值变琥珀色，agent 未上报阈值时按 80%」——与本快照「常量 85、目录 80」一致（【官方文档】`https://docs.x.ai/build/features/status-line`）。

**源码解读候选**：`window_tokens()` 用三级 `min()` 把「估算值可能大于实测值」的异常输入夹回自洽区间——这是所有 `/context` 类 UI 都会踩的坑。

---

## 6. 单次工具输出控制

**做法**
三类上限并存：通用工具结果 40 KB、bash/terminal 20,000 字符、`read_file` 单次最多 1000 行（可配）、MCP 内联结果 20,000 字节。bash 另有一条「落盘 + 指针」链路：前台执行时把完整输出流式写入 `<session_folder>/terminal/<tool_call_id>.log`，超过 `output_byte_limit` 只把截断后的内容交给模型；后台任务完成通知的 footer 会带上 `task.output_file` 路径，提示模型用 `read` 工具（可 offset/limit）重读全文，或调用 `task_output` 工具轮询。`read_file` 用 offset/limit 分页续读，因此「先看局部、需要再放大」是通用模式。MCP 结果有独立的字节上限与「不要与用户可见输出混用」的截断路径（`util::mcp_truncate`）。工具描述模板里会把 `{max_output_bytes}`、`{max_lines_read}` 渲染成实际数值，让模型知道边界。

**关键参数与默认值**

| 项 | 值 | 说明 |
|---|---|---|
| 通用工具结果 | `40_000` 字节（≈10k token） | `DEFAULT_TOOL_OUTPUT_BYTES` |
| bash 前台 | `20_000` 字符（≈5k token） | `DEFAULT_TOOL_OUTPUT_CHARS` |
| bash 超时 | 默认 120 s，最大 600 s | `opencode/bash/mod.rs:52-53` |
| `read_file` 行数 | `1_000` | `MAX_LINES_READ` |
| opencode `read` 行宽 | 2000（该实现自带硬编码） | `types/context.rs:66-68` 注释 |
| MCP 内联 | `20_000` 字节 | `MCP_MAX_OUTPUT_BYTES` |
| bash 全文文件 | `<session_folder>/terminal/<tool_call_id>.log` | 可在后续读取 |

**来源**
- 上限常量：`crates/codegen/xai-grok-tools/src/lib.rs#L9-L13`
- 截断配置与优先级：`crates/codegen/xai-grok-tools/src/types/context.rs#L8-L52`
- bash 上限、落盘与超时：`crates/codegen/xai-grok-tools/src/implementations/opencode/bash/mod.rs#L44-L53`、`#L355-L400`
- 后台任务 footer 指向 output_file：`crates/codegen/xai-grok-shell/src/tools/notification_bridge.rs#L63-L69`
- `read_file` 行数上限：`crates/codegen/xai-grok-tools/src/implementations/grok_build/read_file/mod.rs#L69`
- MCP 上限：`crates/codegen/xai-grok-tools/src/util/mcp_truncate.rs#L30-L40`

**可信度**：【已核实】

---

## 7. 历史裁剪（不调用模型）

**做法**
请求构建时对**副本**做一次工具结果裁剪，不改持久化历史：当 `total_tokens > context_window / 2` 时启用。从尾部往前数「用户轮次」，最近 `keep_last_n_turns = 3` 轮内的工具结果永不裁剪；更老的、且内容超过 4000 字符的结果做**软裁剪**（保留头 1500 + 分隔符 + 尾 1500）；轮龄 ≥ `hard_clear_age_turns = 10` 的直接替换为占位符 `[Tool result omitted — too old]`。轮龄用「从后往前数 `User` 项」估算，因此一轮里多次工具调用共享同一轮龄。压缩前还有第二道确定性裁剪：压缩请求本身会走 image budget（见第 9 类），把内联图片按字节预算换掉。**注意**：本类只在请求副本上生效，`/context` 的 `used` 仍按未裁剪的会话计算，所以「裁剪后实际发出去的 token」可能低于 UI 显示。

**关键参数与默认值**

| 项 | 默认 | 含义 |
|---|---|---|
| `enabled` | `true` | 总开关 |
| `keep_last_n_turns` | `3` | 最近 N 轮不裁剪 |
| `soft_trim_threshold` | `4000` | 字符阈值 |
| `soft_trim_head` | `1500` | 保留头部字符 |
| `soft_trim_tail` | `1500` | 保留尾部字符 |
| `hard_clear_age_turns` | `10` | 超过则整段替换 |
| 触发条件 | `total_tokens > context_window/2` | 硬编码在 `should_prune` |
| 占位符 | `[Tool result omitted — too old]` | `HARD_CLEAR_PLACEHOLDER` |

**来源**
- 配置默认值：`crates/codegen/xai-chat-state/src/types.rs#L68-L94`
- 触发阈值 50%：`crates/codegen/xai-chat-state/src/actor/request_builder.rs#L125-L130`
- 裁剪算法：`crates/codegen/xai-chat-state/src/actor/request_builder.rs#L132-L177`
- 占位符常量：`crates/codegen/xai-chat-state/src/actor/request_builder.rs#L14`
- 用户侧配置说明：`crates/codegen/xai-grok-pager/docs/user-guide/13-memory.md#L411-L422`

**可信度**：【已核实】

**源码解读候选**：`prune_conversation()` —— 「按 User 项数轮龄 + 软裁剪 + 硬清空」三段式，是「不调模型、可逆性最好」的减量手段模板。

---

## 8. 压缩（调用模型做摘要）

**做法**
grok-build 用**整段替换（full-replace）**：把旧历史整体换成一封摘要 + 保留最近消息。触发有 5 条路径：① 采样前 `estimated_total_tokens ≥ context_window × 阈值%`；② preflight 溢出（工具结果把估算推过 100%）；③ 采样返回上下文超限错误 → 压缩后重试；④ 手动 `/compact`；⑤ 模型族切换（立即）。切点不做「保留尾部 N 条」的精细选择——它保留系统消息、重新渲染首条用户消息前缀、**把 AGENTS.md 原文重新注入**、保留最后一条真实用户请求、保留最后一条真实用户轮之后的消息，然后才是摘要。摘要提示词是 9 段结构（Primary Request / Key Technical Concepts / Files and Code / Errors and Fixes / Problem Solving / All User Messages / Pending Tasks / Current Work / Optional Next Step），要求用 `<summary>` 包裹、禁止调用工具，并明确要求把上一次 `<conversation_summary>` 的内容**合并继承**（多次压缩不丢信息的关键）。压缩请求前会做输入整形：按 `max_request_bytes` 预算做 image budget；摘要最多 3 次尝试、每次 120 s 超时、间隔 3 s；摘要清理后短于 500 字符视为退化并重试。压缩产物有三种模式：`summary`（只有摘要）、`transcript`（摘要 + 指向完整 `updates.jsonl` 的指针）、`segments`（**默认**，摘要 + `compaction/` 目录下逐段 markdown）。压缩前可选先做 memory flush（第 12 类）。失败会按 `Size / Auth / CreditBlock / Schema / Other` 分类抑制自动重试，其中 `size` 与 `schema` 是「粘性」抑制，只有上下文预算变化才解除。

**关键参数与默认值**

| 项 | 默认 | 含义 |
|---|---|---|
| 阈值 | `85`（常量）/ `80`（grok-4.6 目录） | 见第 5 类 6 级解析 |
| `compactions_remaining` | `1`（grok-4.6 目录） | 目录声明 |
| 摘要尝试 | `max_attempts = 3` | 含首次 |
| 重试间隔 / 超时 | `3 s` / `120 s` | `FullReplaceConfig` |
| 每次压缩墙钟预算 | `300 s` | `CompactionPolicy::wall_clock_budget_secs` |
| 摘要最短有效长度 | `500` 字符 | `MIN_SUMMARY_SEED_CHARS` |
| 压缩模式 | `Segments(detail)`（默认） | `summary` / `transcript` / `segments` |
| 两遍压缩（预摘要） | `false` | `two_pass_enabled` |
| 手动 `/compact` 参数 | **TUI 拒绝任何参数**（`/compact takes no arguments.`） | 见下方差异说明 |
| 压缩模型 | 未设则用会话当前模型 | `compact_model: None` |

**来源**
- 压缩提示词模板：`crates/common/xai-grok-compaction/src/code_compaction/templates/full_replace_summary_prompt.txt#L1-L19`
- 提示词构建（含 `/compact <text>` 的 user_context 插槽）：`crates/common/xai-grok-compaction/src/code_compaction/prompt.rs#L9-L26`
- 压缩后历史装配顺序：`crates/common/xai-grok-compaction/src/code_compaction/assemble.rs#L60-L115`
- 默认值与重试参数：`crates/common/xai-grok-compaction/src/code_compaction/config.rs#L8-L41`
- `CompactionPolicy` 默认：`crates/codegen/xai-grok-agent/src/compaction.rs#L1-L34`
- 三条自动触发：`crates/codegen/xai-grok-shell/src/session/compaction.rs#L2095-L2116`、`#L2148-L2206`、`#L2207-L2230`
- 压缩失败分类与抑制：`crates/codegen/xai-grok-shell/src/session/compaction.rs#L461-L480`
- 压缩模式枚举与默认：`crates/codegen/xai-chat-state/src/compaction_mode.rs#L12-L25`
- 分段/转录指针：`crates/codegen/xai-grok-shell/src/session/compaction_segments.rs#L1-L50`
- `/compact` 拒绝参数：`crates/codegen/xai-grok-pager/src/slash/commands/compact.rs#L1-L40`
- 压缩后固定系统提示词：`crates/codegen/xai-grok-agent/src/prompt/template.rs#L50-L57`

**可信度**：【已核实】；**与官方文档的差异**：`docs.x.ai` 命令表写 `/compact [context]`（【官方文档】`https://docs.x.ai/build/modes-and-commands`），本快照 TUI 的 `submission_refusal` 明确拒绝任何参数；但压缩提示词构建器保留 `user_context` 通道，说明「带指令压缩」在协议层仍在、当前前端未开放。

**源码解读候选**：`assemble_compacted_history()` 的 7 段顺序（SP → user 前缀 → AGENTS.md → 最后真实请求 → 最近消息 → 摘要 → reminder）。注意「最近消息在摘要**之前**」这个反直觉顺序——摘要必须贴着对话尾部，否则模型会把摘要当成历史再复述一遍。

---

## 9. 多模态上下文

**做法**
图片按 765 token/张计入估算，但真正的控制是**请求体字节预算**：内联图片的 `data:` URL 是请求体主要构成，当序列化后的 body 达到「上限 − 3 MB」时开始驱逐老图片，一直回收到「上限的一半」才停——用滞回（hysteresis）避免每轮都跨过阈值反复打断 KV cache。被驱逐的图片替换为一段**明确告知模型「图已不可见、不要凭记忆描述」**的占位文本；工具结果里的图片驱逐则在该结果文本末尾追加同类说明。第二条路是**服务端拒图**：收到带 `invalid_image` 的 400 时，若整个请求里只有一个唯一图片 URL（归责明确），把该图从 `chat_history.jsonl` 中剥离并重试；只改 `chat_history.jsonl`，`updates.jsonl` 重放会恢复图片并再付一次剥离成本；写入前有备份、从磁盘回读确认。第三条路是「图片转文字」：**仅 Cursor 兼容 harness** 会把用户附图先送视觉模型生成描述，再把描述注入该轮用户消息（最多 16 张，超出打跳过标记），失败则整轮失败、绝不静默丢图；其他 harness 走「持久化图片 + 前置 `<image_files>` 清单」。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 图片估算 | 765 token/张 |
| 驱逐触发 | `max_request_bytes − 3 MiB` |
| 回收目标 | `max_request_bytes / 2` |
| 占位文本 | 固定英文句，含「不要凭记忆描述、需要请让用户重发」 |
| 服务端拒图剥离范围 | 仅 `chat_history.jsonl` |
| 剥离并发上限 | `16` 个待处理 strip |
| 图片转写上限 | `16` 张（`IMAGE_DESCRIPTION_PROCESSING_LIMIT`） |
| 转写启用条件 | `is_cursor_harness()` |

**来源**
- 图片预算常量与占位文本：`crates/codegen/xai-chat-state/src/image_budget.rs#L9-L35`
- 工具结果图片说明：`crates/codegen/xai-chat-state/src/image_budget.rs#L12-L17`
- 拒图剥离策略与范围：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/image_strip.rs#L1-L40`
- 剥离并发上限：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/image_strip.rs#L18`
- 拒图原因枚举：`crates/codegen/xai-grok-sampler/src/events.rs#L27-L34`
- 图片转文字（仅 Cursor harness）：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs#L1141-L1147`
- 转写实现与 16 张上限：`crates/codegen/xai-grok-shell/src/session/image_describe.rs#L1-L40`
- 其他 harness 的 `<image_files>` 前置：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs#L1148-L1165`

**可信度**：【已核实】

**源码解读候选**：`image_budget.rs` 的滞回设计——为什么「清到阈值以下」不够、必须「清到一半」。

---

## 10. 子代理隔离

**做法**
子代理是独立会话、独立上下文窗口，通过 `task` 工具（模型侧常称 `spawn_subagent`）启动；父会话只拿到子代理的最终输出（默认不裁剪，可配 `completion_output_cap`／缓冲上限），中间过程只进子会话的 transcript。内置类型三种：`general-purpose`（全能力）、`explore`（Read/List/Grep 三件套，**无 shell、无写入**）、`plan`（Read/List/Grep/TodoWrite，无 shell、无写入）。类型来自 `BuiltinAgentName` 枚举，`subagent_variants()` 只暴露这三种；项目/用户/插件可用同名 `.md` 覆盖或新增。嵌套深度硬上限 1（只有顶层会话能派子代理，子代理再派会报深度错误）。隔离模式 `none`（默认，共享工作区）或 `worktree`（独立 git worktree，通过 `x.ai/git/worktree/*` 扩展做 create/apply/remove）。`resume_from` 可让新子代理继承已完成子代理的 transcript、工具状态与模型，但系统提示词与工具按当前定义重渲染。MCP 继承可配 `all`（默认）/`none`/`named`/`except`；插件代理不得声明 `mcpServers`/hooks/`bypassPermissions`。还有 `send_subagent_message`（默认关闭）支持 steer/queue/interject 三种投递。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 内置类型 | `general-purpose` / `explore` / `plan` |
| 省略 `subagent_type` | `general-purpose` |
| 最大嵌套深度 | `1`（`MAX_SUBAGENT_DEPTH`） |
| `isolation` | `none`（默认）/ `worktree` |
| `run_in_background` | `true`（默认） |
| 子代理输出裁剪 | 默认不裁剪（`buffered_completion_output_cap: None`） |
| `explore` 工具集 | `read_file`、`list_dir`、`grep` |
| `plan` 工具集 | 上述三者 + `todo_write` |
| MCP 继承默认 | `all` |

**来源**
- 类型枚举与可派生子集：`crates/codegen/xai-grok-agent/src/config.rs#L646-L691`
- `explore` / `plan` / `codex` / `opencode` 定义：`crates/codegen/xai-grok-agent/src/config.rs#L1504-L1545`
- 工具集：`crates/codegen/xai-grok-agent/src/config.rs#L360-L385`
- 深度上限：`crates/codegen/xai-grok-tools/src/implementations/grok_build/task/mod.rs#L44-L50`
- 输出裁剪与摘要：`crates/codegen/xai-grok-tools/src/implementations/grok_build/task/coordinator_state.rs#L1050-L1070`
- 用户手册（类型/参数/隔离/深度）：`crates/codegen/xai-grok-pager/docs/user-guide/16-subagents.md#L59-L72`、`#L148-L158`、`#L256-L266`、`#L399-L401`

**可信度**：【已核实】；**与官方文档的差异**：`docs.x.ai` 写 `explore`「Read, list, and search only (no shell, no edits)」，仓库内 `16-subagents.md` 却写「runs shell commands」——**以源码 `explore_toolset()` 为准：无 shell**（【官方文档】`https://docs.x.ai/build/features/subagents`）。

---

## 11. 会话时间线

**做法**
会话目录是唯一真实来源，布局固定：`summary.json`（索引/标题/父会话）、`updates.jsonl`（ACP 更新流，**权威对话日志**）、`chat_history.jsonl`（实际发给模型的原始消息）、`system_prompt.txt`、`prompt_context.json`、`tool_definitions.json`、`plan.json`、`rewind_points.jsonl`、`signals.json`、`compaction_checkpoints/`、`subagents/`。恢复时重放 `updates.jsonl`，用 `RewindMarker` 做**逻辑截断**——`updates.jsonl` 永远只追加，回退不删行，而是在文件末尾追加一条 marker 指向目标 prompt index；重放器读到 marker 就把累积列表截回该位置，所以「分支」在磁盘上表现为同一文件里的多段被 marker 隔开的时间线。`/rewind`（别名 `/undo`）列出的检查点是**每个用户 prompt**（`[0..current_prompt_index)`），选中后截断对话；TUI 发出的请求固定带 `mode: "conversation_only"`、`force: true`，因此**默认不动磁盘文件**。但 shell 侧 `handle_rewind` 支持 `All` / `FilesOnly` / `ConversationOnly` 三种模式：`All`/`FilesOnly` 会按 file snapshot 回滚文件，先做只读预览、检测外部修改冲突（`modified_externally` / `deleted_externally` / `created_externally`），再写回。`/fork` 复制当前会话为同级会话（可选 worktree）；`Esc Esc`（800ms 内、空闲、空输入）等价 `/rewind`。压缩也会写 checkpoint，且 `updates.jsonl` 里保留压缩被遮蔽的原事件，因此重放可复现同一份压缩后历史。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 会话根 | `$GROK_HOME/sessions/`（默认 `~/.grok`） |
| 会话 ID | UUIDv7（客户端可用 `-s` 指定） |
| 目录分组 | 按 cwd URL 编码；>255 字节用 slug+hash，原路径写 `.cwd` |
| 回退粒度 | 每个用户 prompt 一个点 |
| TUI 回退模式 | `conversation_only`（不动文件） |
| shell 支持模式 | `all` / `files_only` / `conversation_only` |
| 双击 Esc 窗口 | 800 ms |
| `/fork --at` | 本版**不支持** |
| 恢复入口 | `/resume`、`grok --resume <id|title>`、`-c` |

**来源**
- 存储布局与权威日志：`crates/codegen/xai-grok-pager/docs/user-guide/17-sessions.md#L20-L42`
- `/rewind` 行为（不动文件）：`crates/codegen/xai-grok-pager/docs/user-guide/17-sessions.md#L140-L165`
- 检查点生成（每个 prompt 一个）：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/rewind.rs#L23-L68`
- 回退三模式与文件回滚预览：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/rewind.rs#L121-L260`
- RewindMarker 追加：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/rewind.rs#L400-L410`
- 重放时按 marker 截断：`crates/codegen/xai-grok-shell/src/session/storage/mod.rs#L1655-L1677`
- TUI 请求参数（`conversation_only`）：`crates/codegen/xai-grok-pager/src/app/effects/mod.rs#L5542-L5552`
- `/rewind` 命令入口：`crates/codegen/xai-grok-pager/src/slash/commands/rewind.rs#L1-L18`

**可信度**：【已核实】

**源码解读候选**：`filter_rewind_lines()` —— 只追加日志 + tombstone marker 如何实现「可回退、可分支、可重放」，且不破坏 append-only 不变式。这是本工具最值得讲的会话设计。

---

## 12. 跨会话记忆

**做法**
记忆是**实验性、默认关闭**（`[memory] enabled` 与 `[memory_v2] enabled` 都默认 false）。两个作用域：global（跨项目）与 workspace（按仓库，clone/worktree 共享）。v2 用 Markdown 文件：`topics/`（人工/整理后的主题）与 `observations/_inbox/`（每轮之后落的新事实），再加一份**有界的生成式 `MEMORY.md` 索引**，索引每会话注入一次系统提示词，让模型自己决定打开哪些 topic。`/flush` 是「现在就总结进记忆」：触发一次 LLM 摘要，写入带日期的会话日志；摘要写入上限 8000 字符，超长截断；还会在**压缩前**自动跑一次（阈值 = 压缩阈值 − 4000 token 余量，每个压缩周期最多一次），空闲 300 s 也可后台 flush；内容去重默认余弦相似度 0.92。`/dream` 是整理合并：把散落的 observation 折叠成 topic，有租约锁（`stale_lock_secs=3600`）、自动门控（默认间隔 ≥24 h 且累计 ≥5 个会话，每小时检查一次）、批量提交上限 256 KB、单条 note 16 KB、最多 20 条/批，失败可回滚重试。**压缩完成后还会再检索一次记忆**（用户手册「After Compaction」），把可能被摘要丢弃的相关事实补回上下文——这是「压缩前 flush + 压缩后 re-inject」的对称设计。检索默认**纯全文**（未配置 embedding 模型），配置后向量 0.7 + BM25 0.3，`min_score=0.7`，`max_results=6`，MMR `lambda=0.7` 去冗余，session 源按 30 天半衰期衰减。首轮注入用最后一条真实用户请求做查询；若查询是问候或短于 20 字符，改用固定查询 `"project conventions preferences architecture"`；已存在 `<memory-context>` 则跳过（保 cache）。防污染手段：检索结果按来源加权、session 记忆带**陈旧提示**（越老提示越强）、`/remember` 写入前有 review 面板、生成的 `MEMORY.md` 不可删不可手改。

**关键参数与默认值**

| 项 | 默认 | 出处 |
|---|---|---|
| `[memory] enabled` | `false` | `13-memory.md` |
| `session.save_on_end` | `true`（<3 条实质 prompt 或 <50 字节则跳过） | 同上 |
| `[compaction.memory_flush] enabled` | `true` | 同上 |
| `soft_threshold_tokens` | `4000` | 同上 |
| `max_flush_write_chars` | `8000` | `config-types/memory.rs:534` |
| `idle_timeout_secs` | `300` | 同上 |
| `semantic_dedup_threshold` | `0.92`（未设时） | 同上 |
| `[memory.dream] min_hours` | `24` | `config-types/memory.rs:462` |
| `[memory.dream] min_sessions` | `5` | `config-types/memory.rs:463` |
| `[memory.dream] check_interval_secs` | `3600` | `13-memory.md` |
| `[memory.search] max_results / min_score` | `6` / `0.7` | 同上 |
| `vector_weight / text_weight` | `0.7` / `0.3` | 同上 |
| `temporal_decay.half_life_days` | `30.0` | 同上 |
| `mmr.lambda` | `0.7` | 同上 |
| 首轮注入 `min_score` | `0.9` | 同上 |

**来源**
- flush 触发条件与「每压缩周期一次」：`crates/codegen/xai-grok-memory/src/flush.rs#L18-L58`
- flush 写入上限：`crates/codegen/xai-grok-memory/src/flush.rs#L145-L160`
- flush/dream 配置默认：`crates/codegen/xai-grok-config-types/src/memory.rs#L440-L470`、`#L510-L540`
- dream 批量上限：`crates/codegen/xai-grok-memory/src/batch_dream.rs#L22-L45`
- 首轮注入与固定查询：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs#L2243-L2300`
- 用户手册（作用域、/flush、/dream、检索参数）：`crates/codegen/xai-grok-pager/docs/user-guide/13-memory.md#L18-L40`、`#L99-L128`、`#L227-L318`、`#L398-L410`

**可信度**：【已核实】源码；仓库内用户手册 `crates/codegen/xai-grok-pager/docs/user-guide/13-memory.md`（473 行）已逐节核对，作用域、`/flush`、`/dream`、首轮注入与检索参数与源码一致。官方站点 `docs.x.ai/build/features/memory` 仍返回 404，属**文档入口缺失**，不影响本节结论（该条已从待核实清单移除；曾误记的 `.../13-memory.md#L18-L40` 等行号已按 473 行全文复核）。

**源码解读候选**：`should_flush()` 的「阈值 − 余量 + 每周期一次」双条件，和它为什么必须排在压缩**之前**。

---

## 13. 缓存友好设计

**做法**
缓存策略分三层。① **前缀稳定**：`<user_info>` 里的日期在会话内保持启动值，跨午夜只追加一次性 reminder；记忆索引「已有 `<memory-context>` 就跳过」；技能/MCP 公告只在变化时发增量或替换块。② **显式 cache breakpoint**（Anthropic Messages 后端）：给系统提示词最后一块、最后一条可打点的消息、以及「上一轮边界」三处打 `ephemeral`，第 4 个槽位故意留空给网关自动缓存（打第 5 个会被拒）。代码注释直接说明「只在 breakpoint 写入缓存，所以只标系统提示词等于整段 transcript 不缓存」。③ **压缩/驱逐的 cache 代价**：压缩是 replace 语义，从第一个被替换的 token 起失效；图片驱逐用滞回一次性清到一半，避免每轮反复打断。另有一条「压缩后重放暖前缀」的做法：压缩请求复用系统提示词、当前工具定义与被遮蔽区间，使摘要调用的输入尽量成为原对话的前缀。**未找到**针对 xAI 自家 Responses 后端的 cache_control 字段——那部分缓存由服务端透明处理。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| breakpoint 数量 | 3 处显式 + 1 槽留给网关（共 4 上限） |
| breakpoint 类型 | `CacheControl::ephemeral()` |
| 跳过 | `Thinking` / `RedactedThinking` 不可打点，向前找 |
| 图片驱逐 | 触发 50MB−3MB，回收到 25MB（滞回） |
| 日期 | 会话内固定，跨午夜追加 reminder |

**来源**
- breakpoint 应用（含 4 槽说明）：`crates/codegen/xai-grok-sampling-types/src/conversation/messages.rs#L3-L70`
- 日期滚动与「保 cache」注释：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/reminders.rs#L507-L511`
- 记忆注入跳过以保 cache：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs#L2266-L2270`
- 图片预算滞回：`crates/codegen/xai-chat-state/src/image_budget.rs#L19-L35`
- 压缩后「暖前缀」意图：`crates/codegen/xai-grok-shell/src/session/helpers/prepared_compaction_history.rs#L1-L5`

**可信度**：【已核实】（breakpoint）；「Responses 后端透明缓存」为【推断】。

---

## 14. 失败恢复

**做法**
三条恢复路径，优先级从低代价到高代价。① **preflight 溢出**：采样前发现估算已超窗口，先压缩再发。② **采样报上下文超限**：识别错误文本（`too long for this model` / `prompt is too long` / `maximum context length` / `context_length_exceeded` / 413 各种拼写 / `input length … exceeds the maximum allowed length` 等），判定为确定性错误（重发同样 payload 必失败，不重试原样），转压缩后重发。③ **压缩本身失败**：按 `Size / Auth / CreditBlock / Schema / Other` 分类；`size`、`schema` 为粘性抑制，只有上下文预算变化才解除；`auth` 等登录/刷新；`credit_block` 等到一次成功响应。压缩重试 3 次仍失败则向用户报错并给出「/compact 或换模型」的引导。**无法再压缩的情况**：单个不可分割单元（一条巨长的工具结果或一条超长非工具消息）超过窗口——grok-build 的 full-replace 无法拆分单元，只能靠第 7 类的软裁剪先削峰；如果系统提示词 + 工具定义本身就逼近窗口，压缩无能为力（压缩只替换对话历史）。断线/取消：`/compact` 被取消返回稳定的 `compact cancelled` 文案，与失败区分。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 溢出判定 | `estimated_total_tokens > reported context_window` |
| 上下文错误匹配 | 文本启发式，含 4 类 slug + 3 种 413 拼写 + 带锚点匹配 |
| 压缩重试 | 3 次 / 间隔 3 s / 超时 120 s |
| 抑制状态 | `sticky`（size/schema）、`until_success`（credit）、`auth`（登录清除）、`turn`（other） |
| 取消文案 | `compact cancelled` |

**来源**
- 溢出判定：`crates/codegen/xai-grok-shell/src/session/compaction.rs#L2117-L2147`
- preflight 溢出：`crates/codegen/xai-grok-shell/src/session/compaction.rs#L2207-L2230`
- 上下文错误识别表：`crates/common/xai-grok-compaction/src/code_compaction/failure.rs#L6-L59`
- 抑制分类：`crates/codegen/xai-grok-shell/src/session/compaction.rs#L461-L480`
- 取消常量：`crates/codegen/xai-grok-shell/src/session/helpers/session_compact.rs#L56-L60`

**可信度**：【已核实】

---

## 15. 扩展点

**做法**
三层扩展。① **Hooks**：兼容 Claude Code / Cursor 风格的事件钩子，事件包括 `session_start`、`user_prompt_submit`、`pre_tool_use`、`post_tool_use`、`post_tool_use_failure`、`permission_denied`、`stop`、`stop_failure`、`stop_cancelled`、`notification`、`subagent_start`、`subagent_stop`、`pre_compact`、`post_compact`、`session_end`。关键限制：`pre_compact` 与 `post_compact` 的 trait 是 **`Observe`**——只能观察、**不能改压缩内容**，也不能阻止压缩；`user_prompt_submit` 可以注入上下文。② **Plugins / Marketplace**：插件可贡献技能、agent、hooks、MCP 服务器（由插件信任模型约束），`/plugins`、`/marketplace` 管理。③ **Workflows**：`.grok/workflows/*.rhai` 脚本可编排子代理（`agent()` / `parallel()`），有 `agent_budget`（默认 128，范围 1–1024）与并发上限（默认 32）。**自定义压缩**不是公开扩展点：压缩实现绑在 `xai-grok-compaction` 与 shell 的 `CompactionPolicy` 上，没有「注册自定义 compactor」的接缝。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| hook 事件数 | 15 个（`subagent_stop` 有两个条目变体） |
| 压缩相关 hook | `pre_compact` / `post_compact`，仅 `Observe` |
| workflow 预算 | 默认 128，1–1024 |
| workflow 并发 | 默认 32 |
| workflow 位置 | `.grok/workflows/*.rhai`、`~/.grok/workflows/*.rhai` |

**来源**
- 事件枚举与 trait：`crates/codegen/xai-grok-hooks/src/event.rs#L78-L180`
- workflow 预算/并发：`crates/codegen/xai-grok-pager/docs/user-guide/04-slash-commands.md#L293-L325`
- hooks/plugins 入口：`crates/codegen/xai-grok-pager/docs/user-guide/04-slash-commands.md#L216-L239`
- 自定义压缩缺失：`crates/codegen/xai-grok-agent/src/compaction.rs#L1-L34`（`CompactionPolicy` 为具体结构体，无 trait 注入点）

**可信度**：【已核实】；「无自定义压缩接缝」为**源码未找到**，标注【推断】。

---

## 16. 评估与可观测

**做法**
产品遥测把压缩当成一等事件：`AutoCompactFired{tokens_before, percentage}`、`CompactionTriggered{trigger, tokens_used, context_window, percentage, model_id, compaction_id, compaction_mode, two_pass_enabled, is_subagent}`、`CompactionCompleted{duration_ms, tokens_before, tokens_after, degenerate_retries, input_overflow_retries, segments_queued, model_wait_ms, pre/post_compaction_ms, two_pass}`。这套字段足以直接算「压缩回收率」「压缩耗时」「退化重试率」。会话级还有 `signals.json`（token 用量、工具/轮次计数、压缩次数）与 `grok usage <session-id> [turn]`（逐轮 token 与成本 JSON，`costUsdTicks` 为 1e10 tick/USD）。OTEL 走 `xai-grok-otel`（OTLP 导出、redaction、超时、trace context）。另有 session-start 的 context snapshot：用官方 `tokenize-text` 接口对系统提示词、工具定义、技能、MCP、AGENTS.md、workflow 分别做真实分词，作为遥测对照（不是 UI 数据源）。**没有内置评测框架/评测集**：仓库里没有任何 eval harness、A/B 开关或对照实验基础设施，评估要靠外部脚本消费上述遥测。

**关键参数与默认值**

| 项 | 值 |
|---|---|
| 压缩遥测事件 | `AutoCompactFired` / `CompactionTriggered` / `CompactionCompleted` |
| 成本单位 | `1e10 ticks = 1 USD` |
| 每轮用量 | `grok usage <session-id> <turn>`（JSON） |
| OTEL | `xai-grok-otel`（OTLP） |
| 评测框架 | **无** |
| 分词校准 | `POST /tokenize-text`（仅在启用 session metrics 且有凭据时） |

**来源**
- 压缩事件字段：`crates/codegen/xai-grok-telemetry/src/events/compaction.rs#L30-L60`
- 会话信号：`crates/codegen/xai-grok-pager/docs/user-guide/17-sessions.md#L283-L300`
- context snapshot 与真实分词：`crates/codegen/xai-grok-shell/src/session/acp_session_impl/context_snapshot.rs#L1-L53`
- OTEL crate：`crates/codegen/xai-grok-otel/src/lib.rs#L1-L15`

**可信度**：【已核实】

---

## 17. 移植自 codex / opencode 的部分（本票重点）

**结论**：Grok Build 的「移植」有三条独立证据链，全部落在**工具层与提示词层**，不在压缩/记忆/会话层。

### 17.1 `xai-grok-tools` 的 `implementations/codex/` 与 `implementations/opencode/`

仓库自带 `THIRD_PARTY_NOTICES.md` 明确列出：

| 来源 | 被移植的模块 | 原仓库路径 | 许可证 |
|---|---|---|---|
| `openai/codex` | `apply_patch`、`grep_files`、`list_dir`、`read_file` | `codex-rs/core/src/tools/handlers/` | Apache-2.0 |
| `sst/opencode` | `bash`、`edit`、`glob`、`grep`、`read`、`skill`、`todowrite`、`write` | `packages/opencode/src/tool/` | MIT |

声明还写明「已翻译语言、适配本 crate 的 `Tool` trait 与运行时并扩展」，即**不是逐行照搬，是 Rust 重写**——这也是为什么 `opencode/read` 里仍保留 opencode 的 2000 字符行宽硬编码注释。

### 17.2 内置 agent profile `codex` 与 `opencode`

`BuiltinAgentName` 里除了 `grok-build` 系列，还直接有 `Codex` 与 `Opencode` 两个变体：`AgentDefinition::codex()` 使用 `codex_toolset()` + `TemplateOverride::Codex`（即 `templates/apply_patch_prompt.md` 这份 283 行的 apply-patch 风格提示词）；`AgentDefinition::opencode()` 使用 `opencode_toolset()`，描述为「opencode-style tools and parameter conventions」。这两个 profile 可被用户/项目同名文件覆盖，也可作为会话主代理或子代理使用。

### 17.3 不属于「移植」但容易被误认的部分

- `crates/codegen/xai-grok-foreign-sessions/src/codex/`：只是**读取/导入** Codex 的会话文件（`files.rs` / `db.rs`），用于迁移历史，不是运行时代码移植。
- `compat.claude` / `compat.cursor`：规则文件、hooks、skills 的**兼容读取**，与 codex/opencode 无关。
- 压缩、记忆、会话存储、子代理编排：**全部自研**，在 codex 与 opencode 中找不到对应同构实现（codex 是「按 token 预算滚动窗口 + 单次摘要」，opencode 是「按消息数切分 + 摘要」；Grok 是 full-replace + 三种压缩模式 + 记忆 flush）。

**来源**
- 移植声明全文：`crates/codegen/xai-grok-tools/THIRD_PARTY_NOTICES.md#L1-L60`
- codex 工具目录：`crates/codegen/xai-grok-tools/src/implementations/codex/`（`apply_patch/`、`grep_files/`、`list_dir/`、`read_file/`）
- opencode 工具目录：`crates/codegen/xai-grok-tools/src/implementations/opencode/`（`bash/`、`edit/`、`glob/`、`grep/`、`read/`、`skill/`、`todowrite/`、`write/`）
- 内置 agent：`crates/codegen/xai-grok-agent/src/config.rs#L646-L660`、`#L1504-L1526`
- codex 提示词模板：`crates/codegen/xai-grok-agent/templates/apply_patch_prompt.md#L1-L20`
- 外来会话只读导入：`crates/codegen/xai-grok-foreign-sessions/src/codex/mod.rs#L1-L20`

**可信度**：【已核实】

---

## 18. 与第二版二进制观测的交叉印证

| 第二版观测 | 本版源码结论 | 处理 |
|---|---|---|
| 自动压缩约在 85% 触发 | 常量 85，模型目录对 `grok-4.6` 下发 80，另有 6 级覆盖 | 以源码为准，写「默认 85，实际随目录/配置变化」 |
| `/context` 拆成系统/消息/剩余 | 实为四段（System / Messages / Reasoning-overhead / Free），工具/Skills/MCP 是「已计入」附加行 | 修正 |
| `/rewind` 不回滚文件 | TUI 默认 `conversation_only` 确实不回滚；shell 支持 `all`/`files_only` 回滚 | 补充「能力存在，当前入口未用」 |
| 子代理有 explore/plan | 源码确认，且 `explore` 无 shell（与官方文档一致、与仓库手册不一致） | 以源码为准 |
| 记忆有 `/flush`、`/dream` | 源码确认，且默认关闭、有自动 flush 与自动 dream 门控 | 补充默认值与门控 |
| 疑似借用 codex 工具 | 证实：4 个 codex 工具 + 1 套 codex 提示词模板 + 1 个 codex agent profile | 具体到文件 |

---

## 19. 本文档的【待核实】清单

1. **具体发布版本号**：`SOURCE_REV` 是 monorepo 提交 SHA，仓库无 tag，未能映射到 `grok --version` 的语义化版本。
2. **xAI Responses 后端的服务端缓存行为**：源码只处理 Anthropic Messages 的显式 breakpoint，未见 Responses 侧的缓存控制字段。
3. ~~**`docs.x.ai/build/features/memory`**：返回 404，未能与官方文档交叉核对记忆参数。~~ 已核销（2026-10-19）：仓库内用户手册 `crates/codegen/xai-grok-pager/docs/user-guide/13-memory.md` 即官方文档正文，已逐节核对；站点入口 404 属链接缺失，不是内容缺失。
4. **`/compact <text>` 的可用入口**：提示词构建器支持 `user_context`，但本快照 TUI 拒绝参数；是否有 headless/ACP 入口可传，未在源码中找到调用点。
