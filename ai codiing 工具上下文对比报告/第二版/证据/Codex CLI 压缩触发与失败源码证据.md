---
title: Codex CLI 压缩触发与失败源码证据
date: 2026-10-12
status: 固定源码核查完成，未运行模型实验
tags:
  - AI/上下文管理
  - CodexCLI
---

# Codex CLI 压缩触发与失败源码证据

本页只核查 Codex CLI。固定官方源码提交为 [`a07c8ebd57feedc4cf5dfe854c8e9101de54186b`](https://github.com/openai/codex/commit/a07c8ebd57feedc4cf5dfe854c8e9101de54186b)，本地目录为 `/Users/junjielong/workspace/agent-context-research/sources/codex`。这是研究快照，不代表读者正在安装的 CLI 版本。本页阅读了实现与测试代码，没有执行 Rust 测试或真实模型压缩实验，也没有修改用户配置。

本机复核入口：[回合检查 turn.rs](/Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/core/src/session/turn.rs:1304)、[占用计算 context_window.rs](/Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/core/src/session/context_window.rs:60)、[模型限额 openai_models.rs](/Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/protocol/src/openai_models.rs:518)、[本地摘要重试 compact.rs](/Users/junjielong/workspace/agent-context-research/sources/codex/codex-rs/core/src/compact.rs:272)。分享给其他读者时，应使用下文的固定提交网页链接。

## 1. 什么时候整理：按占用检查，不按聊天轮数计时

| 入口 | 源码条件 | 面向普通读者的说法 |
| --- | --- | --- |
| 手动 `/compact` | 命令提交压缩任务；core handler 会停止旧任务并创建 CompactTask | 你也可以主动按“整理桌面” |
| 新一轮开始前 | `run_pre_sampling_compact` 检查当前上下文占用，达到自动压缩限额或有效窗口上限时压缩 | 开始下一步前，先检查桌上是否太满 |
| 同一轮继续工作时 | 模型请求继续或有待处理输入，并且达到限额，或有新窗口请求 | 一句话引发很多次查资料，也可能中途整理 |
| 一轮结束后（可选） | 配置的轮后比例大于 0、达到比例、没有待处理输入、未取消且未启用 TokenBudget | 可以配置“做完一步就提前整理”；本快照未配置时为关闭 |

证据：[/compact 界面入口，L332–349](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/tui/src/chatwidget/slash_dispatch.rs#L332-L349)、[手动任务，L247–254](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/handlers.rs#L247-L254)、[新轮前检查，L1304–1331](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L1304-L1331)、[同轮检查，L574–642](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L574-L642)、[轮后条件，L718–756](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L718-L756)、[轮后比例未配置时取 u8 默认值 0，L4355–4357](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/config/mod.rs#L4355-L4357)。

**不要写成：**“第十轮必压缩”“每到 95% 就压缩”“只有用户再说话才会压缩”。压缩检查不是每输入一个字都实时执行；新轮前的检查目前发生在新用户输入和上下文更新写入之前，源码留有预测这些新增内容的 TODO。因此，一次巨大输入仍可能直接导致过长错误。[顺序与 TODO，L180–184](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L180-L184)

## 2. 整理线和可用桌面上限是两条不同的线

在通常的 `total` 计数模式下，设当前模型解析后的窗口为 W：

- 自动整理基础限额：没有专门值时为 `W × 90%`；有专门值时取它与 `W × 90%` 中更小的值。
- 有效窗口上限：`W × effective_context_window_percent`；百分比字段未提供时默认 95。
- 达到自动整理限额，**或**达到有效窗口上限，都会使“限额已到”成立。TokenBudget 的后备提示可能引入缓冲；正文教学模型应明确排除此特殊配置。

证据：[两种计算，L518–539](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/protocol/src/openai_models.rs#L518-L539)、[95 的字段默认值，L393–395](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/protocol/src/openai_models.rs#L393-L395)、[两条限额的最终判断，L83–110](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/context_window.rs#L83-L110)。用户配置写入模型信息的实现见 [model_info.rs L19–31](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/models-manager/src/model_info.rs#L19-L31)。

**教学图可以用 100 格纸张作假设例子**：假设 W 为 100 格、有效比例取 95、没有更低的专门整理线，则基础整理线是 90 格，可用上限是 95 格。必须标“简化示意，不是你的固定容量或实际 token 读数”。不要把 token 直接等同于汉字，也不要把 90% 写成所有配置下的统一百分比。

展开注释可补充：默认计数范围为整个活动上下文 `total`；另有 `body_after_prefix`，只计带入前缀之后的增长，但完整窗口上限仍独立生效。[默认范围，L42–55](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/protocol/src/config_types.rs#L42-L55)、[范围计算，L60–86](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/context_window.rs#L60-L86)

## 3. 换模型，也可能先整理

源码有两类额外条件：两个回合都有压缩兼容标记且标记不同；或换到上下文更小的模型，现有占用达到相应条件。前者缺少任意一边的标记就不以此触发；后者也不是每次切模型都触发。实现优先让上一个模型整理旧窗口，再交给当前模型继续。[条件与执行，L1334–1426](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L1334-L1426)

普通读者只需理解：**换了一张更小的桌子，或者旧交接材料不兼容时，也可能先整理。** 不必在正文展示内部标记。

## 4. 整理本身失败，不代表旧记录已被删除

| 情况 | 代码实际处理 | 教学边界 |
| --- | --- | --- |
| 本地摘要请求过长 | 对本次压缩用的历史副本移除最老项，再尝试；只剩一项仍过长则失败 | 过长时，连用于写摘要的旧材料也可能被裁掉；不是删磁盘原记录 |
| 本地摘要遇到一般错误 | 按 provider 的重试上限退避重试，耗尽后返回错误；中断、取消、会话预算耗尽等直接退出 | 会重试，但不会保证总能成功 |
| 远端 v2 摘要遇到流错误 | 使用统一流错误处理；本路径每种传输的重试预算不超过 `min(provider设置, 2)` | 不要笼统说“任何情况总共只试三次”，还存在传输/模型后备路径 |
| 上一模型压缩失败 | 满足模型/访问方案差异、OpenAI 提供者与授权条件时，可用当前模型再试；取消等不走此后备 | 不是所有提供者或所有错误都能换模型补救 |

证据：[历史副本与本地重试，compact.rs L272–365](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L272-L365)、[远端 v2 上限，L78–82](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L78-L82)、[远端重试，L381–430](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L381-L430)、[换模型后备条件，L10–31](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_model_fallback.rs#L10-L31)。

新轮前的压缩失败时，代码先记录这次新输入，再报告错误并结束本轮；同轮压缩失败也会停止本轮；轮后压缩的一般失败保留已经完成的回答。[新轮前失败，L190–222](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L190-L222)、[同轮失败，L631–642](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L631-L642)、[轮后失败，L741–756](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L741-L756)

## 5. 两个容易误读的名字

**`ContextWindowExceeded` 不是“必定当场自动压缩成功”。** 普通模型请求遇到它时，会把使用量标满并返回错误，外层报告错误、让用户后续可以继续。另有 guardian 审查任务的特定条件可以同轮压缩再试，不能泛化成所有 CLI 会话的保证。[普通错误路径，L1689–1693](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L1689-L1693)、[外层报告，L818–833](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L818-L833)、[专用条件，L762–791](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L762-L791)

**测试名中的 `compact_advised` 不是已核验的“服务器提醒压缩”入口。** 在此快照的 Rust 代码中，搜索只命中测试函数名；该测试实际构造 `503 server_is_overloaded` 与 `Retry-After`，检查旧模型重试、后备模型重试及失败退出。不能根据测试名字发明独立触发机制。[实际测试输入，L3067–3115](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/tests/suite/compact.rs#L3067-L3115)

## 6. 已读的测试断言与复核方法

- `auto_compact_runs_after_token_limit_hit`：测试先配置 200,000 的限额，再模拟占用增长，断言第三个请求是压缩请求。**200,000 是测试设定，不是产品默认值。** [L1850–1943](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/tests/suite/compact.rs#L1850-L1943)
- `model_context_window_limits_preserve_their_distinct_meanings`：测试用 272,000 的窗口、250,000 的专门值和 95% 的有效比例，断言解析窗口 272,000、可用窗口 258,400、自动整理限额 244,800。**这些是测试样本，不应充当所有用户的容量说明。** [L1878–1895](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/protocol/src/openai_models.rs#L1878-L1895)

以上均为“已阅读官方测试代码”，不是“本机测试通过”。开发者可在本地源码目录运行下列只读命令核对同一版本：

```sh
git rev-parse HEAD
git show a07c8ebd57feedc4cf5dfe854c8e9101de54186b:codex-rs/core/src/session/context_window.rs | nl -ba | sed -n '60,117p'
git show a07c8ebd57feedc4cf5dfe854c8e9101de54186b:codex-rs/protocol/src/openai_models.rs | nl -ba | sed -n '518,539p'
```

本页结论来自所列实现。生活类比、100 格示意、给读者的操作建议属于教学表达，不是复现实验记录。
