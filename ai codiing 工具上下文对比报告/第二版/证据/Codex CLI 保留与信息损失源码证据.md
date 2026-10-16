---
title: Codex CLI 保留与信息损失源码证据
date: 2026-10-12
source_commit: a07c8ebd57feedc4cf5dfe854c8e9101de54186b
status: 源码核查完成；测试代码已阅读，未执行
tags:
  - AI/上下文管理
  - CodexCLI
---

# Codex CLI 保留与信息损失源码证据

研究对象为 **Codex CLI 使用的共享核心实现**，固定官方仓库提交 `a07c8ebd57feedc4cf5dfe854c8e9101de54186b`。它是 2026-10-11 的源码快照，不代表每位读者安装的版本，也不是对未公开服务端压缩算法的验证。本轮没有更新仓库、运行模型或执行 Rust 测试。

本地源码：`/Users/junjielong/workspace/agent-context-research/sources/codex`。

## 证据卡 1：压缩后的材料不一定只是一段摘要

**已核验事实：** 文字摘要路径在客户端筛选用户消息，追加摘要，再重新组装初始规则和环境。Remote V2 路径先筛选可直接保留的条目，实施保留预算，追加服务端返回的一个新压缩条目，再重新组装规则和环境。

- 文字摘要：`compact.rs::run_compact_task_inner_impl`，[L370–415](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L370-L415)。
- Remote V2：`build_v2_compacted_history`，[L499–524](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L499-L524)；随后共同调用规则重组，[L307–326](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L307-L326)。

**大众表达：** “整理后的桌面可能有原样留下的纸条、重新摆上的规则，以及新做的交接包。”

## 证据卡 2：文字摘要路径优先保留近期用户文字，也会裁短

**已核验事实：**

1. `collect_annotated_user_messages` 只收集能解析成真正用户消息的条目，排除旧摘要（`compact.rs` L574–602）。
2. 本快照的用户消息保留预算为 **20,000 tokens**（L63），按从新到旧的顺序选取。
3. 完整、预算内的纯文字消息可以原样保留；超预算边界消息会截短，带媒体的消息会走文字回退，不保证图片原样留下。
4. 最后把选中的消息恢复时间顺序，并追加新文字摘要。

直接证据：[筛选](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L574-L602) · [预算常量](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L61-L63) · [选择与裁短](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L690-L769)。

**不要误读：** 这是该路径的“直接保留用户消息预算”，不是上下文总容量、固定字数、压缩触发阈值，或所有版本通用数字。“本地压缩”指客户端编排这条摘要路径；它仍通过模型客户端发出请求，不能理解为“在电脑上运行本地模型”。见 [`drain_to_completed` L777–802](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L777-L802)。

## 证据卡 3：Remote V2 有类型筛选和共享预算

**已核验事实：**

- 本快照直接保留条目的共享预算是 **64,000 tokens**。这是筛选后、追加新压缩条目前的预算，不是最后整个上下文的大小。
- 真正用户消息与 hook 提示可进入候选；普通 assistant 消息、工具调用和普通配对工具结果不会由这套筛选规则原样留下。
- 某些 Agent 消息可留，但排除子 Agent 进度和完成通知，并设单条大小条件。
- 特殊客户端 developer 消息、特殊客户端独立工具结果受额外开关约束。此快照两个开关默认均为 false。不能把特殊结果保留能力写成“一般工具结果都留着”。
- 候选按新到旧分配预算，预算不足时可能截短边界消息；被选中的特殊工具结果要求整条保留，否则停止继续纳入更老条目。图片也有预算逻辑。

直接证据：[预算 L78–79](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L78-L79) · [类型过滤 L548–597](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L548-L597) · [从新到旧裁剪 L625–721](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L625-L721) · [特殊工具结果定义 L1–20](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_retained_tool_outputs.rs#L1-L20) · [功能默认值 L2045–2062](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/features/src/lib.rs#L2045-L2062)。

**边界：** 新压缩条目可包含 `encrypted_content`，公开客户端代码能核验条目形状、放置和预算，不能据此逐句核实服务端究竟记住了哪些意义。测试中的 “new” 字符串只是模拟载荷，不是可读摘要。

## 证据卡 4：当前正式规则会重新组装，任意旧文件不会自动重读

**已核验事实：** 两条路径都调用 `build_compaction_replacement_history`，生成当前上下文并插入替代历史（`compact.rs` L80–110）。它调用 `build_initial_context_with_world_state`，重新渲染当前 developer 指令及当前 world state。

- [共同重组入口 L80–110](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L80-L110)。
- [当前 developer 指令 L4319–4345](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs#L4319-L4345)；[完整渲染当前状态 L4466–4469](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs#L4466-L4469)。
- 当前已加载的 AGENTS.md 内容加入状态：[world_state.rs L202](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/world_state.rs#L202)；有内容才渲染，并识别替换/移除：[agents_md.rs L28–79](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context/world_state/agents_md.rs#L28-L79)。
- 基础指令由专门状态和请求组装管理，不应仅检查旧历史中有没有某个 system 消息来判断：[world_state.rs L146–160](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/world_state.rs#L146-L160)。

**准确说法：** “当前被系统正式管理和加载的规则，会按现行状态重新准备。”这不等于“所有曾读过的文件、曾说过的要求、曾载入的全部规则都会原样回来”，也不是“每次压缩都会重新打开全部项目文件”。是否遵守规则仍需结果检验。

## 证据卡 5：信息变少有两种原因，不要都算给压缩

**已核验事实 A：工具结果进入活动历史时可先裁短。** `record_item_with_metadata` 克隆条目后对 FunctionCallOutput / CustomToolCallOutput 调用 `truncate_function_output_payload`；这一层对活动历史的裁剪与原始 rollout 载荷分开。

证据：[`history.rs` L517–576](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context_manager/history.rs#L517-L576)。

**已核验事实 B：压缩重新组织信息。** 旧原始条目可能不再直接保留，改由摘要或压缩块传递其中的信息。文字摘要提示词要求进度、关键决定、约束、偏好、下一步和关键参考，但没有逐项无损保证。

证据：[`prompts/templates/compact/prompt.md` L1–9](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/prompts/templates/compact/prompt.md#L1-L9)。

**教学推断：** 像“不能改旧名称”中的否定、特殊例外、精确数字、决定理由可能在概括中缺失或变模糊。这里是一般压缩风险分析，不是此版本已测得的遗漏清单。旧摘要如留下过期结论，后续可能沿用它；这也属于风险推断，不能写成每次必然发生。

**不能承诺：** 原始工具程序输出已完整保存。当前证据只证明这一层活动历史裁剪与 rollout 载荷分开；工具自身、捕获过程和持久化策略还可能有其他限制。

## 证据卡 6：连续压缩风险有警告，但没有可引用的保真率

文字摘要实现完成后发出警告，说明长会话和多次压缩可能使模型准确性下降，并建议可能时把会话保持简短聚焦：[compact.rs L419–424](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L419-L424)。

**事实与推断分开：** 源码警告是事实；“一轮摘要遗漏后，下一轮可能无法单凭该摘要还原”的解释是机制推断。没有运行实验，不能编造“丢失 30%”“压三次就忘光”或各路径保真率。也不能断言 Remote V2 每次同样显示此警告。

## 证据卡 7：已阅读的官方测试，未实际运行

| 测试 | 代码断言表达了什么 |
|---|---|
| [compact_tests.rs L458–505](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_tests.rs#L458-L505) | 超长用户文字会带截断标记，新摘要仍在最后 |
| [compact_remote_v2.rs L864–905](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L864-L905) | 普通 system/developer/assistant、工具调用、旧压缩条目在该筛选步骤不直接留下；用户、hook 和新压缩条目留下。后续规则重组是另一步 |
| [compact_remote_v2.rs L991–1014](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L991-L1014) | 先筛掉不参与保留的内容，再应用保留预算 |
| [compact_remote_v2.rs L1054–1088](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L1054-L1088) | 预算有限时留下较新消息，边界消息可被裁短 |

## 给零编程读者的保留矩阵

以下“留着”指**整理后当前工作材料里直接有这份内容**。它不等于磁盘上是否存着，也不等于内容一定正确或一定被遵守。

| 材料 | 可以怎么理解 | 不能怎么保证 |
|---|---|---|
| 当前正式规则与环境说明 | 重新摆上桌；按当前加载状态准备 | 所有过去提过的规则永不丢失 |
| 你最近说的话 | 优先争取原样留；空间有限时仍可裁短 | 用户说过的每句话都完整保留 |
| 更早说过的要求 | 可能原样留，也可能只进入交接包 | 越重要就一定越完整 |
| AI 过去的长篇答复 | 通常不整篇摆回桌，相关信息靠交接包带走 | AI 的旧答复永久完整可见 |
| AI 查文件、查资料得到的结果 | 普通旧结果通常不整份留下；有特殊例外 | 读过一次就永远记得全文 |
| 图片等附件 | 取决于压缩路径和预算，有些可留，有些不能原样留 | 图片内容一定完整保留 |
| 新摘要或压缩块 | 作为交接材料继续使用；有的不是人能直接读的文字 | 它是毫无遗漏的完整备份 |
| 已经成功保存的旧会话记录 | 通常仍在会话存档，恢复当前工作材料是另一回事 | 只要存着，每次回答就都会看到 |

建议 HTML 使用“原样保留 / 重新准备 / 交接概括 / 需要时重查”四种可点击标签，避免单一“保留 / 删除”二分。图示与互动数据应明确标为教学演示，不伪装成真实 CLI 运行记录。

## 本地复核

```sh
cd /Users/junjielong/workspace/agent-context-research/sources/codex
git rev-parse HEAD
git show a07c8ebd57feedc4cf5dfe854c8e9101de54186b:codex-rs/core/src/compact.rs
git show a07c8ebd57feedc4cf5dfe854c8e9101de54186b:codex-rs/core/src/compact_remote_v2.rs
```

检索过程先使用工作树隔离的 graphify-wt 定位函数，再阅读对应源码。没有改动该源码仓库。

