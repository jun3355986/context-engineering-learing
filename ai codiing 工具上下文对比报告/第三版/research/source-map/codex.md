# Codex CLI · 源码模块地图

- 仓库：https://github.com/openai/codex
- 提交：`76ed3b484d62ccceb9fa512ff4dd139f421814c3`
- 根路径：`codex-rs/`（下表的路径都相对这里）
- 核实日期：2026-10-18
- 说明：「16 类」列用编号 1–16，对应 `research/codex.md` 的章节号。

## 1. 主链路（一次请求怎么组装、怎么触发压缩）

| 目录 / 文件 | 职责 | 类 | 关键导出 / 入口 |
|---|---|---|---|
| `core/src/session/turn.rs` | 回合循环：轮前检查、采样、工具回写、轮中/轮后触发 | 1,5,8,14 | `run_turn` 系列、`build_prompt`(L1666)、`run_pre_sampling_compact` 调用点(L193) |
| `core/src/client_common.rs` | 请求载荷定义（Responses API 形状） | 1 | `Prompt { input, tools, base_instructions, output_schema, ... }`(L22) |
| `core/src/client.rs` | 模型客户端：发请求、解析 usage、缓存键 | 5,13 | `prompt_cache_key`(L646)、`responses_session_id` |
| `core/src/context_manager/history.rs` | 活历史：写入时截断、配对不变量、删除最旧 | 1,6,7,14 | `record_items`(L507)、`remove_first_item`(L685)、`normalize_history`(L968) |
| `core/src/context_manager/normalize.rs` | 四项规范化：补输出、删孤立、剥图片、剥音频 | 1,7,9 | `ensure_call_outputs_present`、`remove_orphan_outputs`、`strip_images_when_unsupported` |
| `core/src/session/context_window.rs` | 两条阈值线与到线判定 | 5,14 | `context_window_token_status`(L55) |
| `protocol/src/openai_models.rs` | 模型元数据与阈值派生 | 5 | `resolved_context_window`、`auto_compact_token_limit`(L526)、`default_effective_context_window_percent`(L393) |

## 2. 组装件（系统指令、规则、工具、动态片段）

| 目录 / 文件 | 职责 | 类 | 关键导出 / 入口 |
|---|---|---|---|
| `core/src/agents_md.rs` | AGENTS.md 发现、拼接、按字节截断 | 2 | `discover_agents_md`(L225 附近)、`candidate_filenames`(L272) |
| `core/src/agents_md_manager.rs` | 运行时管理（宿主贡献、缓存） | 2 | 管理器结构体 |
| `core/src/context/world_state/mod.rs` | 状态分区与差分引擎 | 2,4 | `WorldState`、`WorldStateSnapshot`、`render_diff` |
| `core/src/context/world_state/agents_md.rs` | AGENTS.md 的替换/移除通知 | 2,4 | `AgentsMdState::render_diff`(L44) |
| `core/src/context/contextual_user_message.rs` | 片段识别注册表（判断某条消息是否是「隐藏上下文」） | 4 | `CONTEXTUAL_USER_FRAGMENT_MATCHERS`(L22) |
| `core/src/context/current_time_reminder.rs` | 时间提醒片段 | 4 | `CurrentTimeReminder`(L9) |
| `core/src/context/environments_instructions.rs` | 环境列表与状态说明 | 1,4 | 环境指令渲染 |
| `core/src/context/compaction_summary.rs` | 压缩摘要片段 | 8 | 摘要片段构造 |
| `core/src/context/hook_additional_context.rs` | 钩子附加上下文片段 | 4,15 | `AdditionalContextUserFragment` |
| `core/src/tools/router.rs` | 工具表：模型可见规格 | 1,3 | `model_visible_specs`(L148) |
| `core/src/tools/spec_plan.rs` | 工具规格规划：MCP 接入、延迟策略、tool_search 暴露 | 3 | `finalize_tool_router`(L368) |
| `core/src/mcp_tool_exposure.rs` | MCP 工具暴露：Deferred / Direct | 3 | `append_mcp_tools`(L63)、`search_tool_enabled` 分支(L84-L88) |
| `tools/src/tool_executor.rs` | 暴露枚举语义 | 3 | `ToolExposure`(L51)、`is_deferred`(L88) |
| `core/src/tools/registry.rs` | 工具注册、命名空间、钩子别名 | 15 | `ToolRegistry`、`spawn_agent` 别名 |
| `skills/src/lib.rs` | Skills 加载/解析/提及 | 3 | `LoadedSkills`、`collect_explicit_skill_mentions`、`detect_implicit_skill_invocation_for_command` |
| `skills/src/interface.rs` | 技能接口文件与资产策略 | 3 | `resolve_skill_interface`(L32) |
| `core/src/context/available_plugins_instructions.rs` | 插件说明与命名前缀 | 3,15 | 插件指令块 |

## 3. 减量链路

| 目录 / 文件 | 职责 | 类 | 关键导出 / 入口 |
|---|---|---|---|
| `utils/string/src/truncate.rs` | 头尾保留的 token/字节截断 | 6 | `plan_token_truncation`(L17)、`truncate_middle_with_token_budget`(L69)、`approx_token_count`(L89) |
| `utils/output-truncation/src/lib.rs` | 工具出口限长：说明头、×1.2、多块共享预算 | 6 | `formatted_truncate_text`(L22)、`truncate_function_output_items_with_policy`(L164) |
| `core/src/compact.rs` | 本地压缩：候选选择、20k 预算、失败分支、替换历史 | 8,14 | `compact` 主流程(L345 失败分支)、`COMPACT_USER_MESSAGE_MAX_TOKENS`(L64) |
| `core/src/compact_remote_v2.rs` | 远端 v2 压缩：64k/10k/2 次重试 | 8,14 | `RETAINED_MESSAGE_TOKEN_BUDGET`(L87) |
| `core/src/compact_remote_history.rs` | 远端压缩历史安装 | 8 | 历史装载函数 |
| `core/src/compact_retained_tool_outputs.rs` | 压缩后保留的工具输出 | 6,8 | `is_retained_tool_output` |
| `core/src/compact_token_budget.rs` | TokenBudget 路径下的手动压缩 | 8 | `run_manual_compact_task` |
| `core/src/tasks/compact.rs` | 手动 `/compact` 任务入口 | 8 | `CompactTask::run`(L29) |
| `core/src/context/unsupported_media.rs` | 不支持模态的占位文本 | 9 | `UnsupportedMedia::IMAGE/AUDIO`(L11) |
| `core/src/context/image_resize_notice.rs` | 图片缩放提示 | 9 | `ImageResizeNotice`(L22) |
| `core/src/compact_remote_v2_images.rs` | 压缩时的图片预算 | 8,9 | 图片预算处理 |

## 4. 隔离与延续

| 目录 / 文件 | 职责 | 类 | 关键导出 / 入口 |
|---|---|---|---|
| `core/src/agent/child_config.rs` | 子代理 Config：继承/覆盖指令 | 10 | `build_agent_spawn_config`(L59 调用点) |
| `core/src/agent/registry.rs` | 子代理注册与解析 | 10 | agent registry |
| `core/src/tools/handlers/multi_agents_spec.rs` | spawn/send/wait 工具的 schema | 10 | 多代理工具规格(L570-L610) |
| `core/src/context/inter_agent_message.rs` / `inter_agent_completion_message.rs` | 代理间消息与完成通知 | 10 | 消息片段 |
| `core/src/session/mod.rs` | 会话状态、压缩检查点写盘 | 8,11 | `replace_compacted_history`(L4321-L4376) |
| `core/src/session/rollout_reconstruction.rs` | 恢复：checkpoint + 后缀回放 | 11 | 重建入口(L485-L520) |
| `rollout/src/policy.rs` | 存档裁剪策略（分片 64 KiB） | 6,11 | 存档策略常量 |
| `memories/README.md` | 记忆管线说明 | 12 | — |
| `memories/read/` | 记忆读取：注入 + 引用解析 | 12 | `codex-memories-read` |
| `memories/write/` | 记忆写入：Phase 1/2 模板 | 12 | `codex-memories-write` |

## 5. 质量与扩展

| 目录 / 文件 | 职责 | 类 | 关键导出 / 入口 |
|---|---|---|---|
| `core/src/session/async_compaction.rs` | 后台/投机压缩：门槛、候选、丢弃计量 | 8,14 | `enabled`(L44)、`maybe_start`(L53)、`take_ready` |
| `features/src/lib.rs` | 特性开关与阶段 | 14,15 | `Feature::AsyncCompaction`(L2066)、`CompactionImageBudget` |
| `core/src/hook_runtime.rs` | 钩子生命周期 | 15 | 钩子运行时 |
| `core/src/hook_mcp_executor.rs` | 钩子触发的 MCP 调用 | 15 | 执行器 |
| `core/src/compact_model_fallback.rs` | 压缩失败后的模型回退 | 14 | 回退判定(L10-L32) |
| `otel/`、`analytics/` | 追踪与遥测（非评测） | 16 | OTEL exporter、事件上报 |

## 6. 建议做源码解读的功能（4 个）

1. **`build_prompt` + `Prompt` 结构**（`client_common.rs:22`、`turn.rs:1666`）
   理由：一屏讲清「一次请求到底装了哪四块」，并且能自然引出 `incremental_tools` 的省 token 设计。适合作为源码篇开篇。

2. **`WorldState` 差分 + AGENTS.md 替换/移除通知**（`world_state/mod.rs:380`、`agents_md.rs:44`）
   理由：这是 Codex 最有辨识度的机制——「规则只在变化时重发」。能同时讲清缓存友好与规则一致性，且代码短、无外部依赖。

3. **`truncate_middle_with_token_budget`**（`truncate.rs:69`）
   理由：20 行内包含估算、预算切分、UTF-8 边界、标记不计入预算四个教学点，是所有工具里最干净的「单次输出治理」样本。

4. **`compact` 的候选选择循环**（`compact.rs:600-L660`）
   理由：回答「压缩保留谁」这个最常被误解的问题——只收真实用户消息、20k 预算、从新到旧、遇到放不下就停。比讲摘要模板更有信息量，也便于和 Claude Code 的「重附 5 文件 + 25k 技能」做对照。
