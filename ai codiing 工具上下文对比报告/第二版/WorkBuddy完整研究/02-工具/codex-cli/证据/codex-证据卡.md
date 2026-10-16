---
title: Codex CLI · 证据卡（codex-*）
task: T04
role: 工具研究 Agent
created: 2026-10-15
write_scope: 02-工具/codex-cli/证据/
new_snapshot: 76ed3b484d62ccceb9fa512ff4dd139f421814c3
old_snapshot: a07c8ebd57feedc4cf5dfe854c8e9101de54186b
format: 任务书 §4.4
---

# Codex CLI · 证据卡

> 格式遵循任务书 §4.4。结论ID 规则 `codex-<mechanism>-<number>`。
> 链接基址：新快照 `https://github.com/openai/codex/blob/76ed3b484d62ccceb9fa512ff4dd139f421814c3/`；旧快照 `https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/`。
> **性质栏**：事实 / 推断 / 建议。**实现状态栏**：默认 / 条件 / 实验 / 桩或空实现 / 未证实。
> **凡无实测处**：运行证据一律 `NOT_RUN + 原因`，不得把源码阅读写成实验通过。

---

## A. 触发（trigger）

```yaml
结论ID: codex-trigger-01
结论: 触发判定=范围线 OR 整段线；整段线 H=W×p%（p 缺省 95），范围线=min(模型字段 M, 90% 基础线)
性质: 事实
范围: 快照 76ed3b4（main，2026-10-14）；codex-rs；默认
实现状态: 默认
来源: codex-rs/protocol/src/openai_models.rs#L518-540；codex-rs/core/src/session/context_window.rs#L60-110
数据走查: DW-trigger-01 / DW-trigger-02
运行证据: NOT_RUN + 原因：需 T03 合成任务数据与真实模型运行
不能证明: 不证明服务端如何计量 W；不证明某具体账号下 M 的实际取值
冲突裁决: 支持旧样章 codex-trigger-01/02；限制「90% 是统一压缩阈值」旧说法
核验日期: 2026-10-15
新旧对照: 两快照 context_window.rs / openai_models.rs 逐字节相同 → 成立于 76ed3b4 与 a07c8eb
```

```yaml
结论ID: codex-trigger-02
结论: 90% 是范围线原料、95% 是整段线缺省比例、20,000 是本地直接保留预算——三者互相独立
性质: 事实
范围: 快照 76ed3b4；codex-rs；默认
实现状态: 默认
来源: codex-rs/protocol/src/openai_models.rs#L529-540；codex-rs/core/src/compact.rs#L64
数据走查: DW-trigger-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明语言/分词器下 90% 的“实际行数”
冲突裁决: 裁决 C-01/C-02（Codex 部分），维持样章口径
核验日期: 2026-10-15
```

```yaml
结论ID: codex-trigger-03
结论: 【新快照新增】后台/投机压缩支路：Feature::AsyncCompaction（Stage=UnderDevelopment, default_enabled=false）+ provider 必须 V2；阈值=W全窗×async_compaction_threshold_percent（默认 65）
性质: 事实
范围: 快照 76ed3b4；codex-rs；条件（默认关、开发中）
实现状态: 条件（默认关）
来源: codex-rs/core/src/session/async_compaction.rs#L40-142（阈值实算 L74-78）；codex-rs/features/src/lib.rs#L2066-2070；codex-rs/core/src/config/mod.rs#L225,L3316-3328
数据走查: —
运行证据: NOT_RUN + 原因：依赖 T03；且该 feature 默认关，需显式开启
不能证明: 不证明开启后后台压缩的产品体验；不得写成默认行为
冲突裁决: 无旧结论；属新增机制，须并入 CM-06 覆盖
核验日期: 2026-10-15
```

## B. 保留与重建（retain / persist / recover）

```yaml
结论ID: codex-retain-01
结论: 本地摘要路径——候选只收真用户消息（排除摘要前缀）、预算 20,000、rev 从新到旧、边界后 break、摘要另加
性质: 事实
范围: 快照 76ed3b4；codex-rs；默认
实现状态: 默认
来源: codex-rs/core/src/compact.rs#L64（COMPACT_USER_MESSAGE_MAX_TOKENS=20_000）、#L85、#L622-637、#L658
数据走查: DW-retain-01
运行证据: NOT_RUN + 原因：需 T03
不能证明: 不证明中文消息 20,000 的实测保留条数
冲突裁决: 支持样章 codex-retain-01
核验日期: 2026-10-15
新旧对照: 预算常量与候选判定两快照一致（常量由 L63→L64 位移 1 行）
```

```yaml
结论ID: codex-retain-02
结论: 远端 v2 共享预算 64,000 token、单条 AgentMessage ≤ 10,000、重试 min(provider,2)、验收要求 compaction_count 恰好 1
性质: 事实
范围: 快照 76ed3b4；codex-rs；默认（provider 门控）
实现状态: 条件（provider=V2）
来源: codex-rs/core/src/compact_remote_v2.rs#L87-91（64_000/10_000/retries=2）、#L464-466
数据走查: DW-retain-02
运行证据: NOT_RUN + 原因：需 T03 + 真实 OpenAI/Azure provider
不能证明: 不证明服务端实际保留效果
冲突裁决: 支持样章 codex-retain-02；维持「64,000 token ≠ 64 KiB 字节」区分
核验日期: 2026-10-15
新旧对照: 三常量值两快照相同（行号 L78-82 → L87-91，文件被重构）
```

```yaml
结论ID: codex-persist-01
结论: 压缩完成=替换内存历史 + 追加 CompactedItem 检查点（含 replacement_history、window id、latest_token_usage_record、resume_metadata）；存档追加不删旧记录
性质: 事实
范围: 快照 76ed3b4；codex-rs；默认
实现状态: 默认
来源: codex-rs/core/src/session/mod.rs#L4321-4376
数据走查: DW-persist-01
运行证据: NOT_RUN + 原因：需 T03
不能证明: 不证明 UI 如何展示这些检查点
冲突裁决: 支持样章 codex-persist-01 与 C-03/C-12（源记录不删）
核验日期: 2026-10-15
新旧对照: CompactedItem 字段两快照相同（写入段 L4181-4222 → L4321-4376）
```

```yaml
结论ID: codex-recover-01
结论: 恢复=采用检查点替代历史 + 后缀回放（ResponseItem→replay、RetainedContext、InterAgentCommunication 等）=「持久化断点」路线，非纯重放历史
性质: 事实
范围: 快照 76ed3b4；codex-rs；默认
实现状态: 默认
来源: codex-rs/core/src/session/rollout_reconstruction.rs#L492-515
数据走查: DW-recover-01
运行证据: NOT_RUN + 原因：需 T03
不能证明: 不证明 resume 的交互提示文案
冲突裁决: 支持样章 codex-recover-01；回答 LQ-10 的 Codex 侧
核验日期: 2026-10-15
新旧对照: rollout_reconstruction.rs 逐字节相同 → 两快照均成立
```

## C. 裁剪与工具输出（trunc）

```yaml
结论ID: codex-trunc-01
结论: 头尾裁剪用 ceil(bytes/4) 估算 token；左预算=floor、右=总数−左（奇数差 1 归尾部）；UTF-8 边界对齐；标记 “…N tokens truncated…” 另占长度
性质: 事实
范围: 快照 76ed3b4；codex-rs；默认
实现状态: 默认
来源: codex-rs/utils/string/src/truncate.rs#L17-29、#L69-90、#L142-145
数据走查: DW-trunc-01
运行证据: OBSERVED（codex-run-2026-10-15-trunc-01，本地 0.152.0）：见 codex-trunc-03
不能证明: 不证明「对中文保守」的普适性（C-06 范围限制）
冲突裁决: 支持样章 codex-trunc-01；C-06 仅限该估算式
核验日期: 2026-10-15
新旧对照: 文件被重构（186→156 行，拆出 plan_token_truncation/assemble_truncated_output），**算法与边界语义逐条等价**
```

```yaml
结论ID: codex-trunc-03
结论: 【运行观测】工具输出限长的**有效阈值取自模型元数据** `truncation_policy`（本次 gpt-5.6-sol = tokens(10_000)）；超阈值时保留头+尾、中间替换为标记（`…N tokens truncated…` / `Warning: truncated output (original token count: N)`）；被裁的**中间原文仍保留在会话存档**、可找回（不需重跑工具）
性质: 事实（含边界）
范围: 本地 codex-cli 0.152.0（≠ 快照 76ed3b4）；gpt-5.6-sol；codex exec；danger-full-access；合成目录；**本机 ~/.codex 有插件/hook/自定义 provider（环境受污染，非纯净默认）**
实现状态: 默认
来源: 本地运行 + 会话存档 `$CODEX_HOME/sessions/2026/10/15/rollout-2026-10-15T00-25-32-<sid>.jsonl`（模型所见条目类型 `custom_tool_call_output`；原始留存于 `item_completed` 事件）；`$CODEX_HOME/models_cache.json`
数据走查: DW-trunc-01（估算式与实际标记比对）
运行证据: codex-run-2026-10-15-trunc-01（OBSERVED）：22,003 字节（≈5,501 token）→ 未裁；384,079 字节（≈96,020 token）→ 裁到头+尾、中间 `02000` 行不可见；完整原文留存存档
不能证明: ❌ 不外推到快照 76ed3b4；❌ 不证明阈值是源码常量（依赖服务端下发元数据）；❌ 不证明所有工具输出都留档；❌ **不代表纯净环境默认行为**（本机 ~/.codex 有插件/hook/自定义 provider，须在干净 CODEX_HOME 复现）
冲突裁决: 支持 C10（裁剪只作用 live 副本、rollout 存原载荷）；细化 codex-trunc-01/02 的“阈值来源”
核验日期: 2026-10-15
```

```yaml
结论ID: codex-trunc-02
结论: 工具出口 `formatted_truncate_text` 在正文前包说明头（原始 token 数 + 总行数）；多块输出共享预算、逐块消耗、序列化余量 ×1.2
性质: 事实
范围: 快照 76ed3b4；codex-rs；默认
实现状态: 默认
来源: codex-rs/utils/output-truncation/src/lib.rs#L17-34、#L164-251
数据走查: DW-trunc-02
运行证据: NOT_RUN + 原因：需 T03
不能证明: 不证明各工具出口阈值一律相同
冲突裁决: 支持样章 C8/C9
核验日期: 2026-10-15
新旧对照: output-truncation/src/lib.rs 逐字节相同
```

## D. 缓存（cache）

```yaml
结论ID: codex-cache-01
结论: CLI 发 prompt_cache_key（默认 = session_id；内部子会话={source}:{parent_thread_id}；可 override），并解析 cached_tokens/cache_write_tokens 进 TokenUsage；计数变更含 prompt_cache_key_changed 分支
性质: 事实（含边界）
范围: 快照 76ed3b4；codex-rs；默认（仅 CLI 侧可证）
实现状态: 默认（CLI 发键 + 认明细）
来源: codex-rs/core/src/client.rs#L646-658、#L1060；codex-rs/codex-api/src/sse/responses.rs#L117-151
数据走查: DW-cache-01
运行证据: NOT_RUN + 原因：服务端命中/TTL 不可由本地源码核实，需 T19
不能证明: ❌不证明命中率；❌不证明 30m/断点等参数已启用；❌不证明 UI 展示
冲突裁决: 限制旧说法「缓存与 CLI 无关」；维持「API 文档 ≠ CLI 默认」
核验日期: 2026-10-15
新旧对照: prompt_cache_key 函数体两快照一致（client.rs 整体有重构）
```

## E. 失败与 provider（fail / provider）

```yaml
结论ID: codex-fail-01
结论: 本地压缩失败——ContextWindowExceeded 且 turn_input_len>1 → 移除副本最早项、retries=0 重试；只剩 1 条 → set_total_tokens_full + Err；普通错误 → provider 退避；中断/取消/预算耗尽 → 直接 Err
性质: 事实
范围: 快照 76ed3b4；codex-rs；默认
实现状态: 默认
来源: codex-rs/core/src/compact.rs#L359-378
数据走查: DW-fail-01
运行证据: NOT_RUN + 原因：需 T03 失败注入
不能证明: 不证明重试对最终任务成功率的净影响
冲突裁决: 支持样章 codex-fail-01
核验日期: 2026-10-15
新旧对照: 分支结构两快照一致；**新快照额外把 ResponseIncomplete 并入「预算耗尽」同分支处理**（L350-356 新）
```

```yaml
结论ID: codex-fail-02
结论: 【新快照变化】压缩流中途的条目提交改为“成功后一次性提交”，单次尝试结果隔离；后台压缩失败被丢弃但已发生用量照计
性质: 事实
范围: 快照 76ed3b4；codex-rs；默认（后台部分为条件）
实现状态: 默认 / 条件（后台=默认关）
来源: codex-rs/core/src/compact.rs#L861-890；codex-rs/core/src/session/async_compaction.rs#L1,L133-136
数据走查: —
运行证据: NOT_RUN + 原因：需 T03
不能证明: 不证明对用户账单的具体影响额度
冲突裁决: 与样章不冲突；属细化（改善“半提交”风险）
核验日期: 2026-10-15
```

```yaml
结论ID: codex-provider-01
结论: OpenAI / Azure responses 系 provider 默认 RemoteCompactionSupport::V2；其他默认 Unsupported；可被配置覆盖
性质: 事实
范围: 快照 76ed3b4；codex-rs；默认
实现状态: 默认
来源: codex-rs/model-provider/src/capabilities.rs#L31-51；provider.rs#L713-726（测试断言）
数据走查: —
运行证据: NOT_RUN + 原因：需 T03
不能证明: 不证明某账号实际走哪条路径
冲突裁决: 支持样章 E1
核验日期: 2026-10-15
新旧对照: capabilities.rs 逐字节相同 → 两快照均成立
```

```yaml
结论ID: codex-provider-02
结论: Feature::RemoteCompactionV2 的 Stage=Removed，但在构建 x-codex-beta-features 头时被无条件加入（不再作本地开关）
性质: 事实
范围: 快照 76ed3b4；codex-rs；默认
实现状态: 默认（广告头）
来源: codex-rs/features/src/lib.rs#L2060-2062；codex-rs/core/src/session/mod.rs#L1298-1313（build_model_client_beta_features_header）
数据走查: —
运行证据: NOT_RUN + 原因：需 T03
不能证明: 不证明服务端一定启用该能力
冲突裁决: 支持样章 E2
核验日期: 2026-10-15
```

## F. 跨快照差异（diff）

```yaml
结论ID: codex-diff-01
结论: 触发/模型窗口/恢复/手动压缩/provider 能力 5 条链路的主文件在两快照中逐字节相同（context_window.rs、openai_models.rs、auto_compact_window.rs、rollout_reconstruction.rs、tasks/compact.rs、capabilities.rs、output-truncation/src/lib.rs、rollout/src/policy.rs）
性质: 事实
范围: 76ed3b4 vs a07c8eb；codex-rs
实现状态: 默认
来源: 见“新旧对照”行的逐文件 diff
数据走查: —
运行证据: NOT_RUN + 原因：静态文件比对，非实验
不能证明: 不证明“上下文管理机制整体未变”（压缩链路有实质变化，见 codex-diff-02/03/04）
冲突裁决: 说明基线结论 codex-trigger-01/02、retain-01/02、recover-01、provider-01/02、fail-01 可原样迁入新快照
核验日期: 2026-10-15
```

```yaml
结论ID: codex-diff-02
结论: 新快照新增 session/async_compaction.rs 与 Feature::AsyncCompaction（UnderDevelopment、默认关、阈值默认 65），并在 turn.rs 三时机接入
性质: 事实
范围: 76ed3b4 vs a07c8eb
实现状态: 条件（默认关）
来源: 见 codex-trigger-03
数据走查: —
运行证据: NOT_RUN + 原因：依赖 T03
不能证明: 不证明开启后的行为
冲突裁决: 新增，无旧结论
核验日期: 2026-10-15
```

```yaml
结论ID: codex-diff-03
结论: 新快照 compact.rs 引入 AutoCompactionDisabled 策略（可关闭自动压缩）、fallback_instructions 处理、ResponseIncomplete 并入预算耗尽分支、以及“成功后一次性提交”的尝试隔离
性质: 事实
范围: 76ed3b4 vs a07c8eb
实现状态: 默认
来源: codex-rs/core/src/compact.rs#L65-68（新）、#L283-292、#L350-356、#L861-890
数据走查: —
运行证据: NOT_RUN + 原因：依赖 T03
不能证明: 不证明这些改动的净收益
冲突裁决: 细化样章 codex-fail-01
核验日期: 2026-10-15
```

```yaml
结论ID: codex-diff-04
结论: 新快照把被截短内容的“来源标注”一并保留（codex_context_fragments：set_annotated_content / truncate_annotated_text），协议新增 ContentItemMetadata 字段；非 RLite 端点清空该标注
性质: 事实
范围: 76ed3b4 vs a07c8eb
实现状态: 默认
来源: codex-rs/core/src/compact.rs#L757-789；codex-rs/protocol/src/models.rs#L992-997,L1514-1528；codex-rs/core/src/client.rs#L1007-1012
数据走查: —
运行证据: NOT_RUN + 原因：依赖 T03
不能证明: 不证明对最终摘要保真的影响
冲突裁决: 与样章不冲突，属保真细节增强
核验日期: 2026-10-15
```

```yaml
结论ID: codex-diff-05
结论: utils/string/src/truncate.rs 被重构为 plan_token_truncation + assemble_truncated_output，token 截断算法与边界语义等价
性质: 事实
范围: 76ed3b4 vs a07c8eb
实现状态: 默认
来源: codex-rs/utils/string/src/truncate.rs（新 L17-100；旧 L39-100）
数据走查: DW-trunc-01
运行证据: NOT_RUN + 原因：静态比对
不能证明: 不证明字符数路径（truncate_middle_chars）在所有边界的行为差异（本次核等空串/零预算等价）
冲突裁决: 支持样章 codex-trunc-01 原样迁移
核验日期: 2026-10-15
```

```yaml
结论ID: codex-diff-06
结论: memories crate（长期记忆）在两快照中均存在（write：phase1/phase2/consolidation；read：citations/usage）；新快照仅 phase1.rs 与 rollout_input.rs 有差异
性质: 事实
范围: 76ed3b4 vs a07c8eb；codex-rs/memories
实现状态: 默认（能力存在；深层语义待专项核验）
来源: codex-rs/memories/{write,read}/src/*
数据走查: —
运行证据: NOT_RUN + 原因：需专项核验 + T03
不能证明: 本任务未逐行核验其提取/注入时序（属 CM-08 深水区）
冲突裁决: 与样章无冲突
核验日期: 2026-10-15
```

---

## 附：结论ID 与改动状态总表

| 结论ID | 新快照 76ed3b4 状态 | 基线 a07c8eb 是否仍成立 |
|---|---|---|
| codex-trigger-01/02 | 成立 | 是（文件逐字节相同） |
| codex-trigger-03 | 新增 | 否（旧快照无此机制） |
| codex-retain-01 | 成立 | 是 |
| codex-retain-02 | 成立 | 是（常量值同，行号位移） |
| codex-trunc-01 | 成立（重构等价） | 是 |
| codex-trunc-02 | 成立 | 是 |
| codex-trunc-03 | OBSERVED（本地 0.152.0，非快照行为） | 不适用（运行观测） |
| codex-persist-01 | 成立 | 是（字段同） |
| codex-recover-01 | 成立 | 是（文件相同） |
| codex-cache-01 | 成立 | 是 |
| codex-fail-01 | 成立（分支扩充） | 是 |
| codex-fail-02 | 新增细化 | 部分（旧无“成功后一次性提交”） |
| codex-provider-01/02 | 成立 | 是 |
| codex-diff-01..06 | 差异结论 | — |
