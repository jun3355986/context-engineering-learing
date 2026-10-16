---
title: Codex CLI 压缩与历史保存源码证据
date: 2026-10-11
tags:
  - ai-coding
  - 上下文管理
  - 源码证据
---

# Codex CLI 压缩与历史保存源码证据

研究对象：官方 `openai/codex` 仓库，固定提交 `a07c8ebd57feedc4cf5dfe854c8e9101de54186b`。只讨论 CLI 使用本地持久化的正常会话。以下为源码静态核验；官方测试只阅读、未运行，未调用真实模型，也未读取个人会话。

这是 2026-10-11 拉取的主分支快照，未宣称它与本机安装的 CLI 发布版本相同。源码位于 `/Users/junjielong/workspace/agent-context-research/sources/codex/`；本轮用 Graphify 的本地代码图定位，再回到原文件核查。未研究 Desktop、云端产品入口或其他八个工具。

> [!important] 可用于样章的结论
> **正常上下文压缩替换当前内存历史，同时向会话记录追加压缩检查点；这条路径不删除以前已经写入的记录。** 但“磁盘保存过”不等于“接下来仍全部发给模型”，也不等于“全部外部日志逐字保存”。

## 0. 为什么这些共享模块能证明 CLI 行为

**事实。** CLI 的终端界面收到 `/compact` 后，调用 `app_event_tx.compact()`，路由到 `thread_compact_start()`，向 app-server 发送 `ThreadCompactStart`；服务器提交 `Op::Compact`，core 启动 `CompactTask`。这里的 app-server 是 CLI 使用的实现组件，不能把它的名称误读成 Desktop 产品范围。

[CLI 入口](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/tui/src/chatwidget/slash_dispatch.rs#L332-L349) → [路由](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/tui/src/app/thread_routing.rs#L941-L943) → [请求](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/tui/src/app_server_session.rs#L1658-L1669) → [提交 core 操作](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/app-server/src/request_processors/thread_processor.rs#L2459-L2474) → [启动任务](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/handlers.rs#L247-L254)。

## 1. 压缩时：替换内存，追加记录

**事实。** `Session::replace_compacted_history` 复制 `replacement_history`，调用 `state.replace_annotated_history`，再构造 `CompactedItem` 并交给 `persist_rollout_items`。这里没有用摘要覆盖旧 JSONL 文件的操作。[源码 4181–4222 行](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs#L4181-L4222) · [本地](</Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/core/src/session/mod.rs:4181>)。

下面是上述原代码的删节，`…` 表示省略参数：

```rust
let replacement_history = items.clone();
state.replace_annotated_history(items, …);
CompactedItem { replacement_history: Some(replacement_history), … }
// 随后：
RolloutItem::Compacted(compacted_item)
```

## 2. 从会话到磁盘的完整写入链

**事实。** 下列函数依次连接。表内行号与本地固定提交相同；路径均相对 `/Users/junjielong/workspace/agent-context-research/sources/codex/`。

| 步骤 | 路径、函数与源码证据 |
|---|---|
| 普通消息准备后，进入历史并生成待写记录 | `codex-rs/core/src/session/mod.rs`：`record_conversation_items` [3573–3593](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs#L3573-L3593)，`record_prepared_conversation_items` [3687–3702](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs#L3687-L3702) |
| 会话交给存储层 | 同文件：`persist_rollout_items` [4596–4603](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs#L4596-L4603)；`codex-rs/thread-store/src/live_thread.rs`：`append_items`、`persist_appended_items` [220–266](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/thread-store/src/live_thread.rs#L220-L266) |
| 过滤允许持久化的内容，提交并等待 flush | `codex-rs/thread-store/src/local/live_writer.rs`：`write_and_project`、`durable_write` [327–383](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/thread-store/src/local/live_writer.rs#L327-L383) |
| 加入后台写队列 | `codex-rs/rollout/src/recorder.rs`：`record_canonical_items` [1048–1059](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/recorder.rs#L1048-L1059)，`rollout_writer` [1952–1982](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/recorder.rs#L1952-L1982) |
| 按条写出，成功后移除待写队列项 | 同文件：`write_pending_items_once` [1920–1948](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/recorder.rs#L1920-L1948)，`JsonlWriter::write_line` [2107–2112](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/recorder.rs#L2107-L2112) |

最后一步的原代码：

```rust
let mut json = serde_json::to_string(item)?;
json.push('\n');
self.file.write_all(json.as_bytes()).await?;
self.file.flush().await?;
```

**事实。** 新记录文件使用 `.append(true).create(true)`；恢复已有文件使用 `.append(true)`。因此写入位置在文件尾部。[新文件 1763–1782](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/recorder.rs#L1763-L1782) · [恢复 2033–2056](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/recorder.rs#L2033-L2056) · [本地 recorder.rs](</Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/rollout/src/recorder.rs:2033>)。

**推断。** 上述链路合起来支持“正常压缩保留先前已写记录”；它不构成磁盘故障、人工删除或其他清理机制下的永久保存保证。

## 3. 工具结果保存到什么程度

**事实。** 历史管理器先 clone 工具结果，只裁剪放进当前历史的副本；原 envelope 继续用于 rollout。因而这一层的历史裁剪不会同步裁掉原 rollout payload。[`record_annotated_items` 与 `record_item_with_metadata`，517–576](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context_manager/history.rs#L517-L576) · [本地](</Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/core/src/context_manager/history.rs:517>)。

```rust
let mut processed = ResponseItemEnvelope {
    item: item.clone(),
    metadata: metadata.cloned(),
};
// 裁剪对象是 processed.item，随后进入 live history。
```

**边界事实。** “原 payload”指进入此链路的内容。工具输出此前可以经过格式化裁剪；此外，paginated 模式的持久化命令事件输出、MCP 结果各受 64 KiB 预算约束。`CompactionTrigger`、`Other` 和部分瞬时事件不保存。不能写成“所有 stdout、所有事件、所有原文都完整保存”。[工具格式化 116–124](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/tools/mod.rs#L116-L124) · [过滤 80–99](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/policy.rs#L80-L99) · [预算 16–19](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/policy.rs#L16-L19) · [事件裁剪 250–279](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/policy.rs#L250-L279) · [本地 policy.rs](</Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/rollout/src/policy.rs:250>)。

## 4. resume：从什么材料恢复

**事实。** `codex resume` 进入交互式终端界面；对退出后重新启动的会话，服务器加载记录后进入 core 的历史重建。[CLI resume 入口](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/cli/src/main.rs#L1456-L1482) · [服务端加载](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/app-server/src/request_processors/thread_processor.rs#L4785-L4804) · [core 恢复入口](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs#L1634-L1648)。本节不把连接仍在运行的线程与冷恢复混为一谈。

选中有效检查点后，重建过程先用它的 `replacement_history` 替换消息集合，再处理检查点后缀。关键原代码删节如下：

```rust
history.replace_annotated(items.clone());
// 中间省略伴随状态恢复。
let rollout_suffix =
    history_checkpoint.map_or(rollout_items, |checkpoint| checkpoint.suffix);
for item in rollout_suffix {
    // 逐条处理后续记录。
}
```

[完整上下文 492–515](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/rollout_reconstruction.rs#L492-L515) · [本地](</Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/core/src/session/rollout_reconstruction.rs:492>)。

**边界事实。** 默认本地存储使用 Paginated 模式。它倒序扫描时，只有最新检查点同时包含 `replacement_history` 与 `window_number` 才停止；缺字段或旧格式可能读完整文件。**读取完整文件仍不等于把旧消息全部发给模型**，后面还有重建步骤。[默认模式](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/thread-store/src/local/mod.rs#L480-L482) · [扫描规则](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/thread-store/src/local/model_context.rs#L28-L35)。

**推断。** 如果约束没有进入恢复出的工作材料，仅运行 resume 不能保证把它补回来。该推断不声称模型必然出错，也不声称无法通过重新读文件补充信息。

## 5. 替代材料不等于一段可读摘要

**事实。** 普通手动压缩按 provider 的能力选择客户端编排摘要或 Remote V2。前者在消息预算内选取用户消息并加入摘要；后者保留符合规则且未超预算的消息，再加入远端压缩产物。客户端编排不代表使用离线本地模型。[路径分流](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/tasks/compact.rs#L63-L95) · [摘要路径的内容组装](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L690-L769) · [Remote V2 组装](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L499-L524)。

远端产物的数据类型包含 `ResponseItem::Compaction { encrypted_content: String, … }`。因此图中的“替代材料”不能画成保证可读的中文摘要；客户端源码也不足以证明加密块完整包含了哪些语义信息。[类型定义](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/protocol/src/models.rs#L1269-L1277)。本章未覆盖需另行启用的 TokenBudget 实验分支。

## 6. 官方测试证明范围

以下均为**测试代码证据，未在本次运行**：

- `recorder_materializes_on_flush_with_pending_items` 验证两批记录仍在、顺序正确、重复 persist 不变。[recorder_tests.rs 735–766](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/recorder_tests.rs#L735-L766) · [本地](</Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/rollout/src/recorder_tests.rs:735>)。
- `resumed_paginated_rollout_continues_after_ordinal_gap` 验证恢复追加后的序号为 `[0,4,5]`，此前记录仍在。[同文件 1029–1047](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/recorder_tests.rs#L1029-L1047)。
- `remote_compact_v2_retains_only_client_developer_messages_when_enabled` 使用模拟服务，执行压缩并从磁盘读取 `Compacted.replacement_history`。证明测试覆盖“检查点保存”；不能单独证明所有旧记录逐字保留。[compact_remote.rs 404–428](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/tests/suite/compact_remote.rs#L404-L428) · [本地](</Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/core/tests/suite/compact_remote.rs:404>)。
- `stops_at_newest_usable_compaction_and_keeps_companions` 构造两次压缩，断言加载的模型上下文从最新检查点起算；不包含此前的普通历史。[model_context_tests.rs 36–78](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/thread-store/src/local/model_context_tests.rs#L36-L78)。
- `paginated_compaction_cold_resume_from_bounded_suffix` 使用 mock server，压缩后关闭再恢复，断言恢复前后请求中的替代材料前缀相同。这覆盖冷恢复行为，不验证真实模型是否记住教学场景中的要求。[compact.rs 4563–4727](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/tests/suite/compact.rs#L4563-L4727)。

## 7. 不扩展的边界

`ephemeral` 跳过会话持久化，不能套用上述结论。[session/session.rs 1025–1028](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/session.rs#L1025-L1028) · [本地](</Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/core/src/session/session.rs:1025>)。

磁盘冷文件还有独立的 `.jsonl.zst` 压缩机制：编码、校验后发布压缩文件并删除原路径，恢复追加前再展开。不要把“原 `.jsonl` 路径不在”直接解释成“上下文压缩丢了历史”。[compression.rs 885–892](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/compression.rs#L885-L892)、[936–961](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/compression.rs#L936-L961)、[105–117](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/compression.rs#L105-L117) · [本地](</Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/rollout/src/compression.rs:885>)。

fork、回滚、保留期限与其他清理流程未做完整审计。样章中的生活故事属于教学假设，不能标成实测结果。

## 8. 在本机复核一个结论

下面命令只读固定提交的文件，不会启动模型。第一条确认仓库当前版本；第二条查看本文最关键的“替换后持久化”片段。即使以后工作区更新，`git show` 仍指定本文的完整 SHA。

```bash
git -C /Users/junjielong/workspace/agent-context-research/sources/codex rev-parse HEAD
git -C /Users/junjielong/workspace/agent-context-research/sources/codex show a07c8ebd57feedc4cf5dfe854c8e9101de54186b:codex-rs/core/src/session/mod.rs | sed -n '4181,4222p'
```

返回 [[程序猿/ai/上下文管理/ai codiing 工具上下文对比报告/第二版/样章01-压缩后旧历史到底还在不在-Codex CLI|样章：压缩后，旧历史到底还在不在？]]。
