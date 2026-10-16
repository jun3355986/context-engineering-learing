---
title: Codex CLI 上下文组装、预算与裁剪源码证据
date: 2026-10-14
status: 固定源码复核完成，未运行真实模型实验
tags:
  - AI/上下文管理
  - CodexCLI
  - 源码证据
---

# Codex CLI 上下文教程：2026-10-14 追加源码证据

## 核验范围

来源为 OpenAI 官方 Codex 仓库。2026-10-14 复核 HEAD 仍为 **a07c8ebd57feedc4cf5dfe854c8e9101de54186b**，工作树干净。先定位相关模块，再逐段核对实际实现。源码仓库未更新或修改；本记录供教程修订使用，未运行模型或 Rust 测试。

下文源码路径都相对该仓库根；行号指这个固定提交。网页基址是 `https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/`，路径后加 `#L起始-L结束` 即可形成可分享的固定证据链接。不是对当前所有发布版本的描述。

## 一、先给读者真实定义，再使用比喻

| 概念 | 能讲给初学者的准确解释 | 精确证据 |
|---|---|---|
| 模型输入／上下文 | Codex 为这次模型请求准备的信息：历史条目、当前指令、工具说明等。不是“电脑里所有文件”，也不只等于聊天气泡。工具 schema 与基础指令还可以在请求结构中单独传递。 | [codex-rs/core/src/session/turn.rs · 1563–1591](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L1563-L1591)，`build_prompt` 的 `input`、`tools`、`base_instructions`、`output_schema` |
| 上下文管理 | 程序决定哪些信息进入请求、如何控制大小、何时压缩、用什么替代旧条目、如何保存和恢复。这个定义是对多条实现链的归纳，不能当成某一个类名。 | 请求组装如上；[codex-rs/core/src/context_manager/history.rs · 517–576](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context_manager/history.rs#L517-L576)、[codex-rs/core/src/context_manager/history.rs · 962–979](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context_manager/history.rs#L962-L979)；[codex-rs/core/src/session/turn.rs · 609–654](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L609-L654)；[codex-rs/core/src/session/rollout_reconstruction.rs · 492–515](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/rollout_reconstruction.rs#L492-L515) |
| 当前工作状态（源码名 WorldState） | 程序保存的一组“目前需要让模型知道的设置和环境信息”。比如工作目录、权限、已加载的项目规则、可用工具、协作模式。它不是现实世界的完整知识，也不是另一个会自动思考的大脑。 | [codex-rs/core/src/context/world_state/mod.rs · 384–395](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context/world_state/mod.rs#L384-L395) 明确注释 `Live model-visible state`；[codex-rs/core/src/session/world_state.rs · 142–202](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/world_state.rs#L142-L202)、[codex-rs/core/src/session/world_state.rs · 203–248](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/world_state.rs#L203-L248)、[codex-rs/core/src/session/world_state.rs · 267–327](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/world_state.rs#L267-L327)、[codex-rs/core/src/session/world_state.rs · 334–366](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/world_state.rs#L334-L366) |
| 当前活动历史 | 正在用于继续工作的消息集合。它可能已经被裁剪、压缩、恢复。 | [codex-rs/core/src/context_manager/history.rs · 555–576](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context_manager/history.rs#L555-L576)；[codex-rs/core/src/session/mod.rs · 4181–4190](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs#L4181-L4190) |
| 会话存档 | 已写入存储层的事件与消息。它与当前活动历史是两个视图，不能互相代替。 | [codex-rs/core/src/session/mod.rs · 4181–4222](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs#L4181-L4222)；[codex-rs/rollout/src/recorder.rs · 2033–2046](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/recorder.rs#L2033-L2046)、[codex-rs/rollout/src/recorder.rs · 2107–2112](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/rollout/src/recorder.rs#L2107-L2112) |
| 摘要压缩与机械裁剪 | 摘要压缩会请求模型生成交接材料；机械裁剪按长度移除一部分文字。后者不会先理解“中间这条限制很重要”。 | [codex-rs/core/src/compact.rs · 304–321](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L304-L321)、[codex-rs/core/src/compact.rs · 370–417](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L370-L417)；[codex-rs/utils/output-truncation/src/lib.rs · 36–40](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/output-truncation/src/lib.rs#L36-L40)；[codex-rs/utils/string/src/truncate.rs · 62–98](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/string/src/truncate.rs#L62-L98) |

推荐正文第一次出现时写：“**当前工作状态**，源码叫 `WorldState`，就是 Codex 当前需要让模型知道的环境和设置。”以后中文正文不必反复使用“世界状态”。它是源码真实术语，但直译不能充当解释。

## 二、自动压缩阈值：公式、来源与全部已定位入口

### 变量和计数口径

以下先排除实验 TokenBudget 的缓冲和重置，以免把普通摘要路径讲乱。

- `W`：解析后的模型窗口。取 `context_window`，缺少则取 `max_context_window`。用户配置窗口还会受模型最大值约束，不是任意数字都能扩大服务端真实容量。
- `p`：`effective_context_window_percent`。这个字段缺省为 95；具体模型可以给别的值。
- `H = W × p / 100`：有效窗口限制。
- `C`：明确配置的自动压缩限额。
- `M`：解析后 `ModelInfo.auto_compact_token_limit` 字段。它可以来自模型元数据；明确的用户配置 C 会覆盖该字段。**公式里的模型字段 M 与用户配置 C 不应混成一个变量。**
- `A`：程序当前计算的活动上下文用量。
- `P`：当前压缩窗口开始时的输入基线，不等于“只有系统提示词”。

| 条件／公式 | 源码如何做 | 初学者解释 | 精确证据 |
|---|---|---|---|
| `W` 来源 | `context_window.or(max_context_window)`；配置覆盖时最多取已知 max | 先确定当前模型和配置下，这个窗口按多大来算。 | [codex-rs/protocol/src/openai_models.rs · 518–525](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/protocol/src/openai_models.rs#L518-L525)；[codex-rs/models-manager/src/model_info.rs · 19–30](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/models-manager/src/model_info.rs#L19-L30) |
| 90% 来源 | 基础限额 `L_model = min(M, floor(0.9W))`；没 M 时为 `floor(0.9W)`；不知道 W 时回退 M | 90% 是这一实现的自动整理基础上限，不是模型训练原理规定的数字。只说“用户没配置就一定90%”不严谨，还要看模型元数据是否有更低 M。 | [codex-rs/protocol/src/openai_models.rs · 464](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/protocol/src/openai_models.rs#L464)、[codex-rs/protocol/src/openai_models.rs · 529–539](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/protocol/src/openai_models.rs#L529-L539)；[codex-rs/models-manager/src/model_info.rs · 29–30](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/models-manager/src/model_info.rs#L29-L30) |
| 95% 来源 | 字段缺省函数返回 95；有效窗口另行计算 | 自动整理线与最终可用窗口线不同。95%也不是所有配置永远相同。 | [codex-rs/protocol/src/openai_models.rs · 393–395](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/protocol/src/openai_models.rs#L393-L395)、[codex-rs/protocol/src/openai_models.rs · 523–525](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/protocol/src/openai_models.rs#L523-L525) |
| 默认 total | 范围用量 `S=A`，范围限额用 `L_model` | 把当前带着的全部材料一起算。 | [codex-rs/protocol/src/config_types.rs · 42–54](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/protocol/src/config_types.rs#L42-L54)；[codex-rs/core/src/session/context_window.rs · 60–67](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/context_window.rs#L60-L67) |
| body_after_prefix | `S=A.saturating_sub(P)`；明确配 C 则直接取 C，否则取 `L_model` | 主要盯住这一窗口开始后增长的部分。但所有材料加起来仍不能突破 H。明确 C 在这条路径不再套 total 的 90%钳制。 | [codex-rs/core/src/session/context_window.rs · 68–85](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/context_window.rs#L68-L85) |
| P 的实质 | 第一次服务端 usage 的 input_tokens，或恢复/重算估值；服务端值能替换估值。尚无基线时暂取 A，增长为 0 | 把这一窗口开头已经带入的材料设为起点，然后观察增加多少。不是把任何固定系统提示一律减掉。 | [codex-rs/core/src/state/auto_compact_window.rs · 38–43](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/state/auto_compact_window.rs#L38-L43)、[codex-rs/core/src/state/auto_compact_window.rs · 105–139](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/state/auto_compact_window.rs#L105-L139)；[codex-rs/core/src/session/context_window.rs · 69–78](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/context_window.rs#L69-L78) |
| 已到限额 | `(S >= 范围限额) OR (A >= H)`，存在的限制才参与；TokenBudget可给范围限额加缓冲，完整 H 不变 | 两条线有一条到了，就标为“达到限额”。 | [codex-rs/core/src/session/context_window.rs · 83–110](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/context_window.rs#L83-L110) |
| A 如何计量 | 上次模型 usage 的 total_tokens，加最近模型输出之后本地新增条目的估算；服务端未含旧推理内容时另作补计 | 不是每一次都把所有文字用真实 tokenizer 重新数一遍，也不是从会话开始累计到现在的账单总量。 | [codex-rs/core/src/context_manager/history.rs · 922–953](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context_manager/history.rs#L922-L953) |

**公式教学建议：** 先用 W=100,000、p=95、C未配置且模型也未给更低M演算 total：L=90,000，H=95,000。再用 P=60,000、A=85,000、C=30,000讲 body_after_prefix：增长 S=25,000，增长尚未到30,000，完整85,000也未到95,000。A增至95,000时，即使增长配置更大，完整窗口仍触发。例子是演算，不是用户当前实际配置。

实验缓冲 B 只有 TokenBudget 配置存在且有 `auto_compact_fallback_prompt` 时才可能非零；无后备提示时为0。范围触发使用 `S >= L+B`，完整窗口仍为 `A>=H`。见 [codex-rs/core/src/config/mod.rs · 1312–1317](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/config/mod.rs#L1312-L1317)、[codex-rs/core/src/session/context_window.rs · 97–110](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/context_window.rs#L97-L110)。

### 已定位的触发入口

| 入口 | 精确条件 | 初学者解释 | 精确证据 |
|---|---|---|---|
| 手动 `/compact` | 不先要求达到自动线；停止旧任务，创建 CompactTask | 主动要求整理。手动整理完成不能等同于原任务自动续跑。 | [codex-rs/core/src/session/handlers.rs · 247–254](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/handlers.rs#L247-L254)；[codex-rs/core/src/tasks/compact.rs · 29–95](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/tasks/compact.rs#L29-L95) |
| 新任务开始前 | `token_status.token_limit_reached` | 已有材料太多，先整理再开始。检查发生在新用户输入和上下文更新写入之前，因此巨大新输入仍可能超限。 | [codex-rs/core/src/session/turn.rs · 180–184](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L180-L184)、[codex-rs/core/src/session/turn.rs · 1304–1331](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L1304-L1331) |
| 同一任务尚需继续 | `needs_follow_up && (new_context_window_request || token_limit_reached)`；`needs_follow_up=model_needs_follow_up || pending_input` | 刚查完资料还要再问模型，且已经到线，就尝试整理；也可由新窗口请求进入。已答完且没有待处理输入不走这一处继续分支。 | [codex-rs/core/src/session/turn.rs · 548–575](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L548-L575)、[codex-rs/core/src/session/turn.rs · 609–654](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L609-L654) |
| 可选任务结束后整理 | 比例 q>0；到常规限额或 `A×100 >= H×q`；无待处理输入；未取消；未启用TokenBudget | 做完整轮以后，按配置提前整理。比例是对有效窗口 H 算，不能与90%混成一条线。未配置 q 时为0、关闭。 | [codex-rs/core/src/session/context_window.rs · 111–117](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/context_window.rs#L111-L117)；[codex-rs/core/src/session/turn.rs · 718–756](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L718-L756)；[codex-rs/core/src/config/mod.rs · 4355–4357](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/config/mod.rs#L4355-L4357) |
| 压缩兼容性变化 | 前后双方都有 comp_hash 且不同 | 交接格式有兼容性变化，也可能先整理，不要求先聊满。缺任一标记不以此触发。 | [codex-rs/core/src/session/turn.rs · 1334–1358](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L1334-L1358)、[codex-rs/core/src/session/turn.rs · 1376–1378](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L1376-L1378) |
| 切到更小模型窗口 | 模型不同且旧窗口>新窗口；total下 A>新自动线或A>=新有效窗口，after-prefix下A>=新有效窗口 | 换小桌子，已有材料可能先要收拾。不是每次切模型都压缩。 | [codex-rs/core/src/session/turn.rs · 1379–1425](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L1379-L1425) |
| Guardian专用例外 | 特定审查会话的输入预算或完整请求超限；非TokenBudget；后者每模型步骤最多补救一次 | 这是专门审查流程，不可推广成普通聊天“超限后一定当场压缩重试”。 | [codex-rs/core/src/session/turn.rs · 326–364](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L326-L364)、[codex-rs/core/src/session/turn.rs · 762–790](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L762-L790)、[codex-rs/core/src/session/turn.rs · 1443–1448](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L1443-L1448) |
| TokenBudget实验分流 | 该feature启用时运行特殊重置任务，返回；不走普通两条摘要实现 | 高级配置可能改变压缩的含义和内容；教程应显式排除，不能称“所有路径都是生成摘要”。 | [codex-rs/core/src/session/turn.rs · 1461–1470](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L1461-L1470)；[codex-rs/core/src/tasks/compact.rs · 53–60](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/tasks/compact.rs#L53-L60) |

上述是本次在普通 turn/CompactTask 中定位的入口和专用例外。不要声称已经穷尽所有扩展、内部审查实现和未来服务端行为。

## 三、保留与裁剪算法：不能只写“可能裁短”

### 文字摘要路径

| 步骤 | 实际算法／条件 | 初学者解释 | 精确证据 |
|---|---|---|---|
| 选候选 | 只收真正用户消息；排除旧压缩摘要 | 先认消息种类，不是按语义评“这条特别重要”。 | [codex-rs/core/src/compact.rs · 574–602](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L574-L602) |
| 保留预算 | `20_000`；每条用 `approx_token_count` 估算 | 这是留用户原话的共享预算，不是整窗口，也不是压缩触发线。 | [codex-rs/core/src/compact.rs · 63](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L63)、[codex-rs/core/src/compact.rs · 690–703](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L690-L703) |
| 从新到旧 | `user_messages.iter().rev()`；预算为0停止 | 最近用户消息先装。早而重要的信息仍可能只能靠摘要传递。 | [codex-rs/core/src/compact.rs · 697–703](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L697-L703) |
| 完整直接保留 | 估算tokens<=剩余，且所有content part都是文字 | 纯文字且装得下就保留原文。 | [codex-rs/core/src/compact.rs · 715–720](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L715-L720) |
| 边界消息 | 超预算或带媒体时生成文字回退，`truncate_text(...remaining)`；超预算后break | 到边界那条可能留头尾删中间；不会继续挑更早更小的消息来填缝。带图片的消息在这条路径不能保证原图保留。 | [codex-rs/core/src/compact.rs · 721–753](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L721-L753) |
| 还原时间顺序 | 选完 reverse；再追加摘要；共享逻辑重新组装当前规则 | 选取先倒着选，最后仍按时间正序交给模型，摘要另放进去。 | [codex-rs/core/src/compact.rs · 755–769](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L755-L769)、[codex-rs/core/src/compact.rs · 394–415](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L394-L415)、[codex-rs/core/src/compact.rs · 80–110](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L80-L110) |

**建议可算的演示：** 将真实20K预算缩为教学20格。旧→新用户消息 A=12、B=10、C=6。新→旧选C剩14，选B剩4，A只留4格对应的头尾，然后结束；最终顺序是A片段、B、C、新摘要。这里“选近期”是算法，“摘要能否保住A中间的限制”另需验证。

### 远端 v2 路径

| 步骤 | 实际算法／条件 | 初学者解释 | 精确证据 |
|---|---|---|---|
| 候选过滤 | 真用户消息/HookPrompt；有条件的AgentMessage；特殊client developer与独立工具结果看feature | 不是所有历史都进入“保留原文预算”。普通assistant、普通配对工具调用/结果不会直接入选。 | [codex-rs/core/src/compact_remote_v2.rs · 548–597](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L548-L597) |
| AgentMessage限制 | 排除子代理进度消息及完成通知；单条估算不超过10K | 子代理发来的信息也不是永远原样保留。不要拿这个单条预算当子代理上下文总量。 | [codex-rs/core/src/compact_remote_v2.rs · 79](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L79)、[codex-rs/core/src/compact_remote_v2.rs · 556–579](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L556-L579) |
| 特殊工具结果 | client_authored=true，FunctionCallOutput无call_id且有name；feature开启才保留 | 这是特定标记的独立结果，不代表一般“读文件”结果全留。 | [codex-rs/core/src/compact_retained_tool_outputs.rs · 1–20](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_retained_tool_outputs.rs#L1-L20)；[codex-rs/core/src/compact_remote_v2.rs · 552–554](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L552-L554) |
| 共享预算 | 筛完候选后共享 `64_000`，之后才push新压缩条目 | 64K既不包含新压缩产物本身，也不是最终整个请求大小。 | [codex-rs/core/src/compact_remote_v2.rs · 78](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L78)、[codex-rs/core/src/compact_remote_v2.rs · 499–524](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L499-L524) |
| 顺序 | 对分组倒序，从新到旧计算；最后reverse | 新消息优先，但保持消息与附带说明的成组关系。 | [codex-rs/core/src/compact_remote_v2.rs · 625–646](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L625-L646)、[codex-rs/core/src/compact_remote_v2.rs · 719–721](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L719-L721) |
| 放得下 | 整组加入，减预算 | 普通情况完整留下。 | [codex-rs/core/src/compact_remote_v2.rs · 649–665](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L649-L665) |
| 放不下的特殊工具结果 | 整条保留或整条丢弃；放不下就break，不再填入更早项 | 有些结果不能拆半份，宁可停下来。 | [codex-rs/core/src/compact_remote_v2.rs · 666–668](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L666-L668) |
| 放不下的普通消息 | 给边界消息剩余预算；截完置零。纯文字按content part从前到后处理；边界文字调用头尾裁剪 | 消息之间先新后旧，消息内部的多段文本则顺序处理。不能笼统说“每条都只保留最近一句”。 | [codex-rs/core/src/compact_remote_v2.rs · 669–717](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L669-L717)、[codex-rs/core/src/compact_remote_v2.rs · 748–788](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L748-L788) |
| continue与break区别 | `remaining==0`只是continue扫描但不再纳入；特殊工具结果放不下为break；普通消息不能形成条目、开发消息二次调整仍超限等会continue；成功截短后才置零。附带notice已挤满剩余预算且无图片扣费分支时，也可跳过该组继续 | 主线“从新到旧装，边界截短”适合普通文字；实现存在跳过当前候选的条件，不应声称远端每个分支都在第一次超预算时停止循环。 | [codex-rs/core/src/compact_remote_v2.rs · 637–638](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L637-L638)、[codex-rs/core/src/compact_remote_v2.rs · 666–717](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L666-L717) |
| 图片预算 | 受CompactionImageBudget影响；开启时走内容预算和专用图片裁剪；超大图片可能耗尽边界而不回填更早项 | 媒体不等于普通文字，不能拿64K纯文字规则保证原图完整。 | [codex-rs/core/src/compact_remote_v2.rs · 307–316](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L307-L316)、[codex-rs/core/src/compact_remote_v2.rs · 642–653](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L642-L653)、[codex-rs/core/src/compact_remote_v2.rs · 676–685](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact_remote_v2.rs#L676-L685) |

本快照 `CompactionImageBudget` 默认开启；`RetainClientDeveloperMessages` 与 `RetainClientToolOutputs` 默认关闭，见 [codex-rs/features/src/lib.rs · 2045–2062](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/features/src/lib.rs#L2045-L2062)。功能默认值仍可能被配置覆盖。

### “裁掉中间”究竟怎么做

| 实现事实 | 精确证据 |
|---|---|
| `truncate_text(Tokens(n))`调用共享`truncate_middle_with_token_budget`，不是调用模型写摘要 | [codex-rs/utils/output-truncation/src/lib.rs · 36–40](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/output-truncation/src/lib.rs#L36-L40) |
| 估算为`ceil(UTF-8字节数/4)`，token预算转换为4倍字节预算；不是调用该模型的真实tokenizer | [codex-rs/utils/string/src/truncate.rs · 4](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/string/src/truncate.rs#L4)、[codex-rs/utils/string/src/truncate.rs · 101–113](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/string/src/truncate.rs#L101-L113) |
| 可保留的字节预算一半给开头、一半给末尾；按UTF-8字符边界截取；中间插`…N tokens truncated…` | [codex-rs/utils/string/src/truncate.rs · 62–98](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/string/src/truncate.rs#L62-L98)、[codex-rs/utils/string/src/truncate.rs · 156–181](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/string/src/truncate.rs#L156-L181) |
| 截断标记是额外添加的，所以不要宣称输出含标记后一定严格等于预算token数 | [codex-rs/utils/string/src/truncate.rs · 6–10](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/string/src/truncate.rs#L6-L10)、[codex-rs/utils/string/src/truncate.rs · 79–98](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/string/src/truncate.rs#L79-L98)、[codex-rs/utils/string/src/truncate.rs · 177–181](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/string/src/truncate.rs#L177-L181) |

因此，“裁短”应在动画里真的展示**头部保留／中间移除／尾部保留／截断标记**；摘要则另外展示**让模型重写要点**。两者不是一件事。

## 四、工具输出在压缩前已可能丢信息

| 发生层 | 条件／行为 | 通俗解释 | 精确证据 |
|---|---|---|---|
| 工具格式化 | 给模型消费之前调用`formatted_truncate_text` | 命令产生10万行，不等于模型收到10万行。第一道出口已经可能限长。 | [codex-rs/core/src/tools/mod.rs · 116–124](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/tools/mod.rs#L116-L124) |
| 活动历史 | 克隆条目；对FunctionCallOutput/CustomToolCallOutput应用历史预算；优先用条目覆盖值，否则模型policy附序列化余量 | 存档与本次工作材料可以不同；不是等到整个窗口满才裁工具结果。 | [codex-rs/core/src/context_manager/history.rs · 517–576](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context_manager/history.rs#L517-L576)；[codex-rs/utils/output-truncation/src/lib.rs · 17–20](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/output-truncation/src/lib.rs#L17-L20)、[codex-rs/utils/output-truncation/src/lib.rs · 90–104](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/output-truncation/src/lib.rs#L90-L104) |
| 多块工具输出 | 文字依次消耗预算、边界块截短；耗尽后可添omitted提示；图片/加密块在这个特定函数有单独路径 | 不应把单一纯文字头尾裁剪算法说成适用于所有图片、音频和结构化结果。 | [codex-rs/utils/output-truncation/src/lib.rs · 164–251](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/utils/output-truncation/src/lib.rs#L164-L251) |
| 会话压缩 | 基于目前能交给摘要流程的材料生成替代历史 | 如果关键行早在工具输出时被截掉，之后的摘要未必有机会看到它。 | [codex-rs/core/src/compact.rs · 272–321](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L272-L321) |
| 摘要请求自己超限 | 对历史副本移除最早项重试 | “为了压缩所用的材料”也可能再被缩减；这不等于删除磁盘旧记录。 | [codex-rs/core/src/compact.rs · 338–349](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L338-L349) |

工具输出预算可由 `tool_output_token_limit` 覆盖模型截断策略，见 [codex-rs/models-manager/src/model_info.rs · 32–43](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/models-manager/src/model_info.rs#L32-L43)。应展示“每条工具结果的预算”和“整个窗口压缩线”是两种限制，不要把它们画成一个全局滑块。

## 五、当前工作状态、AGENTS与规则重组

| 事实与条件 | 初学者解释 | 精确证据 |
|---|---|---|
| WorldState按稳定section ID保存当前对模型公开的状态；Snapshot用于比较 | 程序有一份当前说明单，按“环境、权限、项目规则”等栏管理，知道哪些变化了。 | [codex-rs/core/src/context/world_state/mod.rs · 384–395](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context/world_state/mod.rs#L384-L395)、[codex-rs/core/src/context/world_state/mod.rs · 413–445](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context/world_state/mod.rs#L413-L445) |
| 包括已加载AGENTS、模型指令、权限、环境、工具、扩展与多代理模式；由配置决定哪些加入 | 不要说“所有电脑状态”或“所有已知事实”都在WorldState里。 | [codex-rs/core/src/session/world_state.rs · 142–202](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/world_state.rs#L142-L202)、[codex-rs/core/src/session/world_state.rs · 203–248](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/world_state.rs#L203-L248)、[codex-rs/core/src/session/world_state.rs · 267–327](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/world_state.rs#L267-L327)、[codex-rs/core/src/session/world_state.rs · 334–366](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/world_state.rs#L334-L366) |
| 当前AGENTS无变化不重发；有变化发替换说明；删除时发不再适用说明 | 它不是在每一轮把所有规则复制一遍，也不是旧规则无限堆叠。 | [codex-rs/core/src/context/world_state/agents_md.rs · 44–79](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context/world_state/agents_md.rs#L44-L79) |
| 普通压缩后重新构建初始上下文，并render_full当前WorldState | 摘要之外还要把当前有效设置摆回来；这不等于重新打开全部项目文件。 | [codex-rs/core/src/compact.rs · 80–110](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L80-L110)；[codex-rs/core/src/session/mod.rs · 4319–4345](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs#L4319-L4345)、[codex-rs/core/src/session/mod.rs · 4466–4469](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs#L4466-L4469) |
| AGENTS发现范围：项目根到当前目录；同目录override优先，再AGENTS，再配置fallback；不遍历整个项目子树 | “文件叫AGENTS就自动完整进模型”不成立，要看所在目录、命名、可信状态和预算。 | [codex-rs/core/src/agents_md.rs · 1–18](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/agents_md.rs#L1-L18)、[codex-rs/core/src/agents_md.rs · 232–275](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/agents_md.rs#L232-L275) |
| 项目不可信时不读取项目说明；项目说明跨环境共享字节预算；超预算截掉文件尾部 | 项目规则也可能没有加载，或只加载了一部分。规则重组不会补回最初就没读进来的尾部。 | [codex-rs/core/src/agents_md.rs · 56–115](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/agents_md.rs#L56-L115)、[codex-rs/core/src/agents_md.rs · 145–178](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/agents_md.rs#L145-L178) |
| 默认项目文档预算32KiB，但可配置 | 这与20K用户原话预算、64K保留预算、模型窗口大小不同。 | [codex-rs/core/src/config/mod.rs · 253](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/config/mod.rs#L253)、[codex-rs/core/src/config/mod.rs · 4419](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/config/mod.rs#L4419) |

“规则优先级”不能只看文本的位置。AGENTS内容在此实现中以有专门包装的用户上下文片段呈现；developer指令、基础指令又有各自构建路径。不要简单说“AGENTS都是system消息”或“规则重新注入就保证模型遵守”。

## 六、八章目前遗漏的高优先方面

以下按“达到中级专项判断能力”排列优先级，避免继续给概念换个比喻却没有补实现。

| 优先级／建议位置 | 应增加的问题 | 可核验的事实与边界 | 精确证据 |
|---|---|---|---|
| P0，第1章 | 一次请求到底装了什么？ | 展示消息列表中的role/type、工具调用ID与返回配对、当前规则、工具schema。保持输入材料与输出回答区分。 | [codex-rs/core/src/session/turn.rs · 1563–1591](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L1563-L1591)；[codex-rs/core/src/context_manager/history.rs · 962–979](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/context_manager/history.rs#L962-L979) |
| P0，第2章 | 用量从哪来？90%对谁算？ | 明确W/H/L/A/P；总量与增长两口径；服务usage与本地估算区别。 | 本文第二节 |
| P0，第3/4章 | 摘要与裁剪究竟差在哪？ | 实际展示从新到旧、最后边界头尾截取，标注大小估算；让读者看见“重要信息恰好在中间”为什么会消失。 | 本文第三、四节 |
| P0，第1/3章 | 项目规则怎样进来？为什么不是永远完整？ | 发现范围、加载预算、当前状态差分与压缩时重组。 | 本文第五节 |
| P1，第5章 | 存档、当前上下文、模型请求三者为什么不同？ | 成功压缩换当前历史、追加检查点；恢复采用replacement_history和后缀。 | [codex-rs/core/src/session/mod.rs · 4181–4222](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs#L4181-L4222)；[codex-rs/core/src/session/rollout_reconstruction.rs · 492–515](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/rollout_reconstruction.rs#L492-L515) |
| P1，第5章折叠 | fork与resume有什么区别？ | fork创建新线程身份，从选定历史边界派生；legacy与paginated存储入口不同。不能把fork说成永远重新完整读入所有早期原话。 | [codex-rs/core/src/thread_manager.rs · 1492–1537](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/thread_manager.rs#L1492-L1537)、[codex-rs/core/src/thread_manager.rs · 2666–2697](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/thread_manager.rs#L2666-L2697)；需深入paginated时再追`ThreadStore::prepare_fork` |
| P1，第5章折叠 | 回滚对话会回滚文件吗？ | 历史重建的rollback语义是丢最新N个用户轮的活动视图；该历史算法不是文件版本恢复。不要教用户把对话回滚当git撤销。 | [codex-rs/core/src/session/rollout_reconstruction.rs · 133–146](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/rollout_reconstruction.rs#L133-L146)、[codex-rs/core/src/session/rollout_reconstruction.rs · 277–279](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/rollout_reconstruction.rs#L277-L279)、[codex-rs/core/src/session/rollout_reconstruction.rs · 317–319](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/rollout_reconstruction.rs#L317-L319)、[codex-rs/core/src/session/rollout_reconstruction.rs · 547–548](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/rollout_reconstruction.rs#L547-L548)；本次只核验历史重建，不声称穷尽产品撤销入口 |
| P1，第6章 | 手动压缩和自动中途压缩，结束后会怎样？ | 手动停止旧任务并起CompactTask；自动中途成功后continue工作循环。失败替代尚未安装不代表什么记录都没增加。 | [codex-rs/core/src/session/handlers.rs · 247–254](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/handlers.rs#L247-L254)；[codex-rs/core/src/session/turn.rs · 609–654](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/turn.rs#L609-L654)；[codex-rs/core/src/compact.rs · 401–415](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L401-L415)、[codex-rs/core/src/compact.rs · 812–830](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L812-L830) |
| P1，第7/8章 | 怎样判断“代码能做到”和“模型真的做对了”？ | 客户端保留策略、测试断言、真实运行的事实保留是三种证据。黑盒压缩包不能逐句审计；应设计带否定、数字、旧决定更新的可测样本。 | [codex-rs/protocol/src/models.rs · 1269–1277](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/protocol/src/models.rs#L1269-L1277)；[codex-rs/core/src/compact.rs · 419–424](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/compact.rs#L419-L424) |
| P2，补充地图 | 长期记忆是不是自动获得所有旧聊天？ | Memories有feature与use_memories门控；read-path实际读取memory_summary.md并裁短，作为上下文贡献。它不是每次无差别读取所有会话。 | [codex-rs/ext/memories/src/extension.rs · 45–74](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/ext/memories/src/extension.rs#L45-L74)；[codex-rs/ext/memories/src/prompts.rs · 31–63](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/ext/memories/src/prompts.rs#L31-L63) |
| P2，补充地图 | 子Agent到底带什么上下文？ | fork_mode是独立选项；选择fork时prepare_forked_history写入子线程初始历史，未选不是默认复制一切；子代理创建独立thread。环境/工具继承不等于历史全部继承。 | [codex-rs/core/src/agent/types.rs · 21–39](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/agent/types.rs#L21-L39)；[codex-rs/core/src/agent/control/spawn.rs · 799–844](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/agent/control/spawn.rs#L799-L844) |
| P2，补充地图 | 缓存、检索与上下文压缩 | 缓存重复输入的计算，不等于压缩历史；检索是查出相关原文再加入请求。两者概念应讲清，但当前报告没有重新审计缓存传输实现和全部检索工具。 | 不以本报告声称缓存算法已全审计；可沿用已核实官方Prompt caching资料 |

## 七、教程实现建议与不可夸大的边界

1. **每个新术语用“定义→数据结构→例子→源码”四步，而不是只换比喻。** 比如 WorldState 先列当前工作目录、权限、已加载AGENTS，再展示对应section名称；最后才说像一份说明单。
2. **让两个预算同屏可比较。** “单条工具结果限长”与“整个活动上下文压缩线”必须分开，否则读者仍会以为所有丢失都发生在/compact。
3. **裁剪实验需真实遵循顺序。** 用A/B/C消息演示先新后旧，边界保头尾；不要模拟成按重要性任意拖选后说这就是Codex实际策略。
4. **压缩生成的语义内容仍用明确的假设样本。** 客户端的选择算法可以精确演算；真实摘要是否保住某条约束，没有跑模型就不能写“实测保留”。
5. **P0内容是本次教程应补齐；P1可放折叠或第8章路线图；P2至少有一张边界地图。** 不要说这八章已覆盖完整中级Agent工程，仅可说覆盖这条固定版本上下文流程并提供继续研读路径。



[[程序猿/ai/上下文管理/ai codiing 工具上下文对比报告/第二版/Codex CLI 上下文管理-交互教程|返回十章交互教程说明]]
