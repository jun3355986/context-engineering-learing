# Grok Build · 源码模块地图

- **仓库**：https://github.com/xai-org/grok-build
- **提交**：`2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8`（`SOURCE_REV` = `559751fdcec02d413e4c57c8832ab275e4f44980`，指向 monorepo 提交，非版本号）
- **核实日期**：2026-10-18
- **规模**：3689 个 `.rs` 文件、约 200 万行；`crates/codegen` 下 80+ crate，`crates/common` 下 8 个
- **Permalink 基址**：`https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/`
- **阅读顺序建议**：`xai-grok-agent`（提示词/规则/压缩策略）→ `xai-chat-state`（消息状态、裁剪、图片预算）→ `xai-grok-shell/session`（会话、压缩编排、注入、回退）→ `xai-grok-tools`（工具与截断）→ `xai-grok-compaction`（压缩引擎）→ `xai-grok-memory`（记忆）→ `xai-grok-pager`（`/context`、斜杠命令、渲染）

## 1. 关键目录 / 文件

| 路径 | 职责 | 对应 16 类 | 关键函数 / 符号 |
|---|---|---|---|
| `crates/codegen/xai-grok-agent/src/prompt/context.rs` | `PromptContext`：模板占位符、audience、模板变体、AGENTS.md 段落、persona | 1、2、4 | `PromptContext`、`placeholders()`、`agents_md_user_reminder()`、`TemplateOverride` |
| `crates/codegen/xai-grok-agent/src/prompt/user_message.rs` | 首条用户消息前缀：`<user_info>`、rules、skills、MCP、workflow 清单 | 1、3、4 | `UserMessageContext::render`、`USER_MESSAGE_DATE_FORMAT` |
| `crates/codegen/xai-grok-agent/src/prompt/agents_md.rs` | 规则文件发现、排序、gitignore/信任门禁、渲染 | 2 | `read_agents_config_with_roots()`、`format_agents_md_section()`、`InstructionSource` |
| `crates/codegen/xai-grok-agent/src/prompt/template.rs` | 三份模板（base/apply_patch/subagent）的 XOR 解密与压缩后固定提示词 | 1、8 | `base_template()`、`apply_patch_template()`、`COMPACT_SYSTEM_PROMPT` |
| `crates/codegen/xai-grok-agent/templates/prompt.md` | 主系统提示词模板（明文源，构建时加密） | 1、13 | 条件段：`memory_v2_enabled`、`tools.by_kind.task` |
| `crates/codegen/xai-grok-agent/src/config.rs` | 内置 agent 定义（`grok-build*` / `codex` / `opencode` / 子代理三型）、工具集 | 1、10、17 | `BuiltinAgentName`、`subagent_variants()`、`explore_toolset()`、`codex()`、`opencode()` |
| `crates/codegen/xai-grok-agent/src/compaction.rs` | `CompactionPolicy` 默认值（阈值、模型、flush、墙钟、两遍） | 5、8、14 | `CompactionPolicy::default()` |
| `crates/codegen/xai-grok-config/src/compat.rs` | Claude/Cursor 兼容：指令文件名、规则目录、skills 目录 | 2、3 | `INSTRUCTION_FILENAMES`、`agent_filenames()`、`rules_dirs()` |
| `crates/codegen/xai-chat-state/src/actor/request_builder.rs` | 请求前裁剪：50% 触发、软裁剪、硬清空、占位符 | 7 | `should_prune()`、`prune_conversation()`、`HARD_CLEAR_PLACEHOLDER` |
| `crates/codegen/xai-chat-state/src/types.rs` | `PruningConfig` 默认值 | 7 | `PruningConfig::default()` |
| `crates/codegen/xai-chat-state/src/actor/mod.rs` | 对话状态 actor：token 计数、截断、压缩检查命令 | 5、7、11 | `GetEstimatedTotalTokens`、`TruncateToPromptIndex`、`CheckAutoCompactNeeded` |
| `crates/codegen/xai-chat-state/src/image_budget.rs` | 内联图片字节预算与滞回驱逐、占位文本 | 9、13 | `IMAGE_COMPACT_TRIGGER_BYTES`、`apply_image_budget_with_limits()` |
| `crates/codegen/xai-chat-state/src/compaction_mode.rs` | 压缩产物模式：summary / transcript / segments | 8、11 | `CompactionMode::parse()`、`segment_detail()` |
| `crates/codegen/xai-grok-shell/src/session/compaction.rs` | 压缩编排：三条自动触发、抑制分类、两遍预压缩、失败引导 | 8、14 | `should_auto_compact()`、`check_auto_compact_needed()`、`check_preflight_overflow()`、`should_compact_on_error()` |
| `crates/codegen/xai-grok-shell/src/session/helpers/session_compact.rs` | 压缩 LLM 调用、错误分类、取消文案、历史准备 | 8、14 | `generate_session_compact()`、`CompactFailure`、`build_compaction_prompt()` |
| `crates/codegen/xai-grok-shell/src/session/helpers/prepared_compaction_history.rs` | 压缩请求的图片预算与输入整形 | 8、9 | `build_compaction_chat_history()`、`effective_image_budget_limits()` |
| `crates/codegen/xai-grok-shell/src/session/compaction_segments.rs` | 分段/转录落盘与摘要尾部指针 | 6、8 | `persist_compaction_segment()`、`transcript_hint()` |
| `crates/codegen/xai-grok-shell/src/session/acp_session_impl/reminders.rs` | 各类 `<system-reminder>` 注入（日期滚动、任务完成、fork、workflow） | 4、13 | `maybe_inject_date_rollover_reminder()`、`drain_between_turn_completions()` |
| `crates/codegen/xai-grok-shell/src/session/acp_session_impl/turn.rs` | 一轮的注入序列、图片转写分派、记忆首轮注入 | 4、9、12 | `handle_prompt`（注入段 `#L1123-L1140`）、`transcribe_user_images` 分派、`initial_injection` |
| `crates/codegen/xai-grok-shell/src/session/acp_session_impl/session_setup.rs` | `/context` 与 `/session-info` 的快照装配 | 5 | `build_session_info()`、`usage_categories()` |
| `crates/codegen/xai-grok-shell/src/session/acp_session_impl/context_snapshot.rs` | 会话启动时用真实分词器做上下文分类遥测 | 5、16 | `emit_session_context_snapshot()` |
| `crates/codegen/xai-grok-shell/src/session/acp_session_impl/rewind.rs` | 检查点枚举、回退执行（三模式、文件冲突检测） | 11 | `get_rewind_points()`、`handle_rewind()` |
| `crates/codegen/xai-grok-shell/src/session/acp_session_impl/image_strip.rs` | 服务端拒图后的历史剥离 | 9 | `handle_images_stripped()`、`should_defer_image_strip()` |
| `crates/codegen/xai-grok-shell/src/session/storage/mod.rs` | `updates.jsonl` 重放与 `RewindMarker` 过滤 | 11 | `filter_rewind_lines()`、`filter_rewind_updates()` |
| `crates/codegen/xai-grok-shell/src/session/acp_session_impl/model_switch.rs` | 模型/窗口切换后的阈值与即时压缩 | 5、8 | 窗口选择、family-switch compact |
| `crates/codegen/xai-grok-shell/src/util/config/resolve/compaction.rs` | 自动压缩阈值 6 级解析 | 5、8 | `resolve_auto_compact_threshold_percent()` |
| `crates/codegen/xai-grok-shell/src/session/memory/mod.rs` + `memory_observation.rs` | 记忆会话侧接线与遥测 | 12 | 记忆开关、flush/dream 触发 |
| `crates/common/xai-grok-compaction/src/code_compaction/` | full-replace 压缩引擎（prompt/config/sample/summary/assemble/failure） | 8、14 | `build_summary_prompt()`、`assemble_compacted_history()`、`is_context_length_error()` |
| `crates/common/xai-grok-compaction/src/intra_compaction/fit.rs` | Grok chat（非 build）的「逐级降级」fit 阶梯，可作对照 | 7、8、14 | `FitRung`、`ToolTruncated` |
| `crates/codegen/xai-grok-memory/src/flush.rs` | 压缩前记忆 flush 的判定与写入上限 | 8、12 | `should_flush()`、`FLUSH_SYSTEM_PROMPT` |
| `crates/codegen/xai-grok-memory/src/batch_dream.rs` | dream 合并的批量上限、租约、回滚 | 12 | `MAX_BATCH_NOTES`、`MAX_COMMIT_TEXT_BYTES`、`BatchDreamControl` |
| `crates/codegen/xai-grok-config-types/src/memory.rs` | 记忆/flush/dream/pruning 的全部默认值 | 7、12 | `MemoryFlushConfig`、`DreamConfig`、`PruningConfig` |
| `crates/codegen/xai-grok-tools/src/lib.rs` | 工具输出上限常量 | 6 | `DEFAULT_TOOL_OUTPUT_BYTES`、`DEFAULT_TOOL_OUTPUT_CHARS` |
| `crates/codegen/xai-grok-tools/src/types/context.rs` | 截断配置与工具名占位符 | 6 | `TruncationConfig::max_output_bytes_for()` |
| `crates/codegen/xai-grok-tools/src/implementations/codex/` | 移植自 openai/codex 的 4 个工具 | 6、17 | `apply_patch`、`grep_files`、`list_dir`、`read_file` |
| `crates/codegen/xai-grok-tools/src/implementations/opencode/` | 移植自 sst/opencode 的 8 个工具 | 6、17 | `bash`、`edit`、`glob`、`grep`、`read`、`skill`、`todowrite`、`write` |
| `crates/codegen/xai-grok-tools/src/implementations/search_tool/` | MCP 工具的 BM25 检索入口与描述截断 | 3 | `SEARCH_TOOL_NAME`、`MAX_MCP_DESCRIPTION_LENGTH`、`fingerprint_servers()` |
| `crates/codegen/xai-grok-tools/src/implementations/grok_build/task/` | 子代理编排：启动、配额、完成摘要、深度 | 10 | `MAX_SUBAGENT_DEPTH`、`completion_summary()`、`cap_completion_output()` |
| `crates/codegen/xai-grok-tools/src/types/skill_discovery_tracker/` | 技能清单预算、增量公告 | 3、4 | `SKILL_BUDGET_CONTEXT_PERCENT`、`listing_budget_chars` |
| `crates/codegen/xai-grok-tools/THIRD_PARTY_NOTICES.md` | 移植来源与许可证（codex / opencode） | 17 | — |
| `crates/codegen/xai-grok-token-estimation/src/lib.rs` | bytes/4、图片 765、阈值比较原语 | 5 | `estimate_tokens()`、`exceeds_threshold()`、`free_tokens()` |
| `crates/codegen/xai-grok-sampling-types/src/conversation/messages.rs` | Anthropic cache breakpoint 布置 | 13 | `apply_cache_breakpoints()`、`mark_message_cache_breakpoint()` |
| `crates/codegen/xai-grok-sampler/src/events.rs` | 图片剥离原因枚举 | 9、14 | `StripReason::ServerRejected` / `PayloadHeuristic` |
| `crates/codegen/xai-grok-pager/src/scrollback/blocks/context_info.rs` | `/context` 渲染与四段口径 | 5 | `window_tokens()`、`build_lines()` |
| `crates/codegen/xai-grok-pager/src/slash/commands/context_window.rs` | `/context-window` 解析与切换 | 5 | `supported_window()`、`format_window()` |
| `crates/codegen/xai-grok-pager/src/slash/commands/rewind.rs` | `/rewind` 入口 | 11 | `RewindCommand` |
| `crates/codegen/xai-grok-pager/src/app/effects/mod.rs` | TUI → shell 的回退请求（`conversation_only`、`force`） | 11 | `rewind_execute_params()` |
| `crates/codegen/xai-grok-hooks/src/event.rs` | 15 个 hook 事件与 trait（`Observe` / `Stop` 等） | 4、15 | `PreCompact`、`PostCompact` |
| `crates/codegen/xai-grok-telemetry/src/events/compaction.rs` | 压缩遥测字段 | 16 | `CompactionTriggered`、`CompactionCompleted` |
| `crates/codegen/xai-grok-foreign-sessions/src/codex/` | 只读导入 Codex 会话（非运行时代码移植） | 11、17 | `files.rs`、`db.rs` |
| `crates/codegen/xai-grok-pager/docs/user-guide/` | 仓库自带用户手册（行为口径的第二来源） | 全部 | `04/12/13/16/17-*.md` |

## 2. 主链路（读源码按这个顺序）

```text
启动 / 会话创建
  → discovery.rs + agents_md.rs：读 AGENTS.md / rules（信任 + gitignore 门禁）   [第 2 类]
  → prompt/template.rs + context.rs：渲染系统提示词                              [第 1 类]
  → user_message.rs：拼首条用户消息（user_info / rules / skills / MCP / workflow）[第 1、3 类]

每一轮
  → turn.rs:1123 起：注入 MCP 提醒、日期滚动、plan/fork/任务完成/workflow 提醒   [第 4 类]
  → chat_state: GetEstimatedTotalTokens = 上次 usage + 新增估算                  [第 5 类]
  → check_preflight_overflow()：估算 > 窗口 → 先压缩                            [第 14 类]
  → check_auto_compact_needed()：估算 ≥ 阈值% → 压缩                            [第 8 类]
  → request_builder: total > 50% 窗口 → prune_conversation()（副本）            [第 7 类]
  → 采样；若报上下文超限 → should_compact_on_error() → 压缩 → 重发              [第 14 类]

压缩
  → memory flush（可选，阈值−4000 token）                                        [第 12 类]
  → image budget 整形（压缩请求）                                                [第 9 类]
  → full_replace_summary_prompt + 最多 3 次 / 120s / 3s                          [第 8 类]
  → assemble_compacted_history: SP → user前缀 → AGENTS.md → 最后请求 → 最近消息 → 摘要 → reminder
  → CompactionMode: segments（默认）/ transcript / summary → checkpoint 落盘     [第 8、11 类]

回退
  → /rewind → shell handle_rewind(mode=conversation_only) → 追加 RewindMarker    [第 11 类]
  → 下次 resume：filter_rewind_lines() 按 marker 截断重放
```

## 3. 源码解读候选（4 个）

### 候选 A：`prune_conversation()` —— 不调模型的减量模板（第 7 类）
`crates/codegen/xai-chat-state/src/actor/request_builder.rs#L125-L177`
理由：三段式（最近 N 轮保护 → 软裁剪头尾 → 超龄硬清空）+ 50% 触发阈值，是全教程里最干净的一版「零成本减量」。代码短（约 50 行），依赖少（纯函数 + `PruningConfig`），适合逐行注释；且能直接引出「为什么 UI 的 `/context` 与实发 token 不一致」这个常见困惑。

### 候选 B：`filter_rewind_lines()` + `RewindMarker` —— append-only 日志如何支持回退与分支（第 11 类）
`crates/codegen/xai-grok-shell/src/session/storage/mod.rs#L1655-L1677`、`acp_session_impl/rewind.rs#L400-L410`
理由：只用「追加一条隧道标记 + 重放时截断」就实现了可回退、可重放、不可变日志三者共存；对比多数工具「删文件 / 重写 JSONL」的做法，能讲清「日志是唯一真实来源」的工程含义。可与 dsh 的 `surfaceOp: replace` 对照成一对。

### 候选 C：`window_tokens()` —— `/context` 四段口径与夹紧（第 5 类）
`crates/codegen/xai-grok-pager/src/scrollback/blocks/context_info.rs#L312-L345`、`#L495-L505`
理由：12 行代码解释了「System / Messages / Reasoning-overhead / Free」怎么算、为什么必须逐级 `min()`、为什么工具定义与 Skills 要标成「已计入上面」。非常适合做交互式演示（改 `used` 看四段怎么变）。

### 候选 D：`assemble_compacted_history()` —— 压缩后历史的 7 段顺序（第 8 类）
`crates/common/xai-grok-compaction/src/code_compaction/assemble.rs#L60-L115`
理由：顺序反直觉（最近消息在摘要**之前**）、AGENTS.md 要原文重注、摘要要带 `<conversation_summary>` 以便二次压缩继承。60 行以内、纯数据变换、无 I/O，是理想的教学级源码段；也能自然带出「压缩为什么会打断 cache」。

> 备选（若需要第 9 类）：`image_budget.rs#L9-L35` 的滞回驱逐，20 行讲清「触发阈值 ≠ 回收目标」。
