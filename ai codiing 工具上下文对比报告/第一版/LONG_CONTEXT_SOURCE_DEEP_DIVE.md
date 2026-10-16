# 长上下文处理机制：源码级深度分析（Pi / OpenAI Codex / Claude Code）

> **调研日期**：2026-09-12
> **代码版本**：Codex `openai/codex` @ 2026-09 HEAD（Rust，`codex-rs/`）；Pi `earendil-works/pi`（原 `badlogic/pi-mono`）0.85.1（TypeScript）；Claude Code v2.1.88（npm 发布版反编译还原源码）
> **证据等级**：**三家全部为源码级证据**。每一个结论都附 `文件:行号`，可逐条复核。
> **与 `LONG_CONTEXT_MANAGEMENT_RESEARCH.md` 的关系**：那份文档的 Claude Code 章节基于官方文档、工程博客与社区记录（其自身已标注「闭源无法核源码」），Codex/Pi 章节为源码级。本文档的增量价值在于——**Claude Code 换成了真实源码**，因此首次可以看到它在文档里从未披露的东西：六层压缩体系的真实分工与优先级、精确到 token 的阈值常量、被编译掉的桩函数、以及那条关于「250K 次/天 API 调用浪费」的生产事故注释。Codex / Pi 两章也比前文更深（新增远程压缩、缓存友好设计、overflow 三态检测的完整实现）。

---

## 目录

0. [背景与本项目现状（先读这节）](#0-背景与本项目现状先读这节)
1. [执行摘要](#1-执行摘要)
2. [统一分析框架：上下文压力的四个来源与三个干预层](#2-统一分析框架上下文压力的四个来源与三个干预层)
3. [Claude Code：六层压缩体系](#3-claude-code六层压缩体系)
4. [OpenAI Codex：三路径 + 四触发点](#4-openai-codex三路径--四触发点)
5. [Pi：两机制 + 一个反直觉的架构选择](#5-pi两机制--一个反直觉的架构选择)
6. [横向对比](#6-横向对比)
7. [提炼：七个可复用的工程模式](#7-提炼七个可复用的工程模式)
8. [闭环：本项目改哪里、怎么验](#8-闭环本项目改哪里怎么验)
9. [附录：数值常量总表与复核方法](#9-附录数值常量总表与复核方法)
10. [一句话总结](#10-一句话总结)

---

## 0. 背景与本项目现状（先读这节）

> 这一节是**后文的入场券**。如果不先看这一节，第 3–7 章会像一堆没有上下文的技术细节。
> ⚠️ 本节的数据是**实测**的，不是从旧文档抄的。它同时修正了本文档初版和 `LONG_CONTEXT_MANAGEMENT_RESEARCH.md` 里关于本项目现状的错误描述（见 §0.6）。

### 0.1 这份报告回答什么问题

问题只有一句话：

> **一次 Agent Run 发给模型的文字越来越长，模型装不下。别人是怎么解决的？**

本项目里，一次 `Single-Turn Agent Run` 会把「问题 + 回答 + 简历片段」拼成一段文字（本项目叫 `context`）发给 DeepSeek。对话越长、简历越长，这段文字越长。模型能接收的文字量有上限。超了，调用就失败，或者答案质量下降。

官方把这种「让窗口里的内容变少」的做法叫 **compaction（压缩）**。本文档分析 Pi、OpenAI Codex、Claude Code 三家怎么做这件事。

### 0.2 先把三个词分清

后文反复用这三个词。先把它们说清楚。

| 词 | 含义 | 本项目对应物 |
|---|---|---|
| **上下文**（context） | 一次请求里发给模型的**全部文字**：system 提示、对话历史、当前问题、当前回答、简历…… | `api/interviewer.py` 里那些 `context = f"..."` 变量 |
| **上下文窗口**（context window） | 模型**一次**能接收的最大 token 数。超出就报错，无法通过重试解决 | DeepSeek 模型的固有属性，不由本项目决定 |
| **token** | 模型切分文字的最小单位。**1 个 token ≠ 1 个字符** | 需要换算，见 §0.5 |

**为什么"窗口满了"不能靠重试解决**：这不是网络抖动，是请求本身太大。唯一出路是**让请求变小**。这正是 compaction 要干的事。

### 0.3 本项目现在到底发了什么（实测）

我在 `ai_interviewer/api/interviewer.py` 里逐个核对了**全部 5 个**会调用模型的函数。结果如下。

| 函数 | 行号 | 进 prompt 的内容 | 有没有对话历史 | 简历截断 |
|---|---|---|---|---|
| `generate_opening` | `:39`，context 在 `:50` | 简历 + 职位要求 | ❌ 无 | `[:2000]` |
| `generate_project_questions` | `:85`，context 在 `:111` | 简历 + 职位要求 + 问题计数 | ❌ 无 | `[:2000]` |
| **`evaluate_answer`** | `:148`，context 在 **`:165-167`** | **当前问题 + 当前回答** + 简历 | ❌ **无** | **`[:1000]`** |
| `generate_followup_question` | `:209`，context 在 `:217` | 原问题 + 回答 + 追问原因 | ❌ 无 | — |
| **`conclude_interview`** | `:423`，context 在 **`:439-445`** | **全部 QA（问题+回答+得分）** + 简历 | ✅ **全量** | `[:1000]` |

数据模型侧：`QuestionAnswer` 有 `is_followup` 字段（`services/interview_session.py:39`），`project_qa_list` / `technical_qa_list` **包含追问轮次**（`:74-81`）。所以 `conclude_interview` 的 `all_qa = project_qa_list + technical_qa_list` 会把追问的完整回答和得分也拼进去。

### 0.4 从这张表读出的两个结论

**结论一：评分调用看不到追问链。**

`evaluate_answer` 只收到「当前这一个问题 + 当前这一个回答 + 简历前 1000 字符」。它**完全不知道**前面已经问过什么、答得怎么样、为什么追问。

后果是评分**孤立**：
- 第 3 轮追问问的是同一个知识点的更深层。模型看不到前 2 轮，无法判断候选人是「在补充」还是「在自相矛盾」。
- 也无法判断「这个问题是不是已经问过了」。
- 这不是「上下文太长」的问题，是**信息缺失**的问题。第 3–7 章讲的所有压缩技术，**都治不了这个病**。

**结论二：总结调用才是真正的长上下文风险点。**

`conclude_interview`（`:442`）做的是：

```python
"\n\n".join(qa_summary)   # qa_summary 每项 = "问题：…\n回答：…\n得分：…"
```

这里**没有任何长度上限**——不是截断问题，是**从来没有加过限制**。一场 10 题 + 每题 2 轮追问的中文面试，每轮回答按 500 字符估，就是 30 轮 × 500 = 15,000 字符，再加上 `问题/得分` 与简历，`context` 轻松超过 2 万字符。中文约等于 2 万 token（见 §0.5）。这就是"超长上下文"在本项目的**实际发生位置**。

> **所以本项目的正确问题陈述是两句，不是一句**：
> ① 评分调用缺历史（信息缺失，要**加**）；
> ② 总结调用无上限（容量风险，要**限**）。
>
> 这两句方向相反，必须分别处理。初版报告把两者混成了一句「追问链被截断 2000 字符」，这是错的，见 §0.6。

### 0.5 token 换算：中文不是「4 字符 1 个 token」

三家的源码和文档都提到 `chars / 4` 这个估算系数（Pi `compaction.ts:266`、Codex、Claude Code 都有）。**但那是为英文设计的。**

我实测了本项目 `.venv` 里的 `tiktoken 0.12.0`（`cl100k_base` 编码，作为 DeepSeek 分词器的代理近似）：

| 样本类型 | 字符数 | 实际 token | `len/4` 估算 | 实际 token/字符 | 估算 ÷ 实际 |
|---|---|---|---|---|---|
| 中文技术回答 | 116 | **111** | 29.0 | **0.96** | **26%** |
| 中文项目描述（简历类） | 101 | **71** | 25.2 | **0.70** | **36%** |
| 英文回答 | 177 | 33 | 44.2 | 0.19 | 134% |
| Java 代码片段 | 268 | 79 | 67.0 | 0.29 | 85% |

**读法**：
- **中文：`len/4` 只估到真实值的 26%–36%，低估约 3–4 倍。**
- 英文：高估 1.34 倍（安全方向）。
- 代码：接近准确。

也就是说，**`len/4` 对英文是保守高估，对中文是危险的低估**。Pi 源码注释写的 "conservative (overestimates tokens)" 对英文成立，对中文不成立——**不能直接照搬到本项目**。

**本项目建议的安全估算**（中文为主、含英文技术词）：

```python
def estimate_tokens(text: str) -> int:
    cjk = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
    return round(cjk * 1.0 + (len(text) - cjk) * 0.35)
```

即：**CJK 字符按 1 token 计，其余按 0.35**。这个式子在上述 4 个样本上都会得到偏高的估计——对本用途是安全的。

> 想更准，就用 DeepSeek 真实分词器实测一次，替换掉系数。但**方向比精度重要**：宁可高估（多压一次），不可低估（超窗失败）。这正是 Claude Code 在 `microCompact.ts:204` 对估算值额外 ×4/3 的理由。

### 0.6 本文档初版的两个错误（已修正）

作为「读报告时要小心什么」的示范，如实记录：

| # | 初版写的 | 实际情况 | 怎么发现的 |
|---|---|---|---|
| 1 | 现状是「追问链靠启发式截取最近 2000 字符」 | **追根溯源后发现这句来自旧文档，我没有验证。**实际 `evaluate_answer` 根本不带历史；`conclude_interview` 是无上限拼接。生产代码里也不存在 `[:-2000]` 这样的截断 | 逐个读完 `api/interviewer.py` 的全部 5 个 context 组装点 |
| 2 | 「`chars/4` 对中文明显偏高（保守高估）」 | **方向写反了。**中文实际是 **0.7–0.96 token/字符**，`len/4` **低估 3–4 倍** | 用项目 venv 里的 tiktoken 实测（§0.5 表） |

教训：**引用旧文档的"现状"结论时必须回源码验证**。旧文档的 Claude Code 章节本来就标注了「闭源无法核源码」，它的现状描述同样需要复核。

### 0.7 怎么读后面几章

- **只想解决问题** → 直接跳 §8「闭环：改哪里、怎么验」。
- **想知道别人怎么做** → §3（Claude Code）、§4（Codex）、§5（Pi）各成一章，可以只读你在意的那个。
- **只想要一张对照表** → §6 横向对比 + §9 数值常量总表。
- **§1 执行摘要**是全文结论的浓缩，可以和 §0 一起先读。

---

## 1. 执行摘要

> 下面 10 条是**三家工具怎么做**的结论。**本项目的现状与行动清单在 §0 和 §8**，不在这 10 条里——因为本项目眼下最要紧的问题（评分调用缺追问链）不属于「压缩」这一类，见 §0.4。

**十条核心结论**（每条后附证据锚点）

1. **三家都不用「固定 N 字符截断」做主策略。** 截断只出现在两个位置：单条工具输出的**源头治理**，以及压缩请求本身超窗时的**最后兜底**。窗口管理的主流解法是「全量历史落盘 + 结构化摘要 + 近期原文」的投影。
2. **触发阈值高度一致，都在窗口的 90%–95% 区间**，但表达方式完全不同：Codex 用**百分比**（`context_window × 9/10`）、Claude Code 用**绝对缓冲**（`effectiveWindow − 13_000`）、Pi 用**响应预留**（`contextWindow − 16_384`）。三者数学上等价于「给模型留出一次完整回复的空间」。（§3.2 / §4.2 / §5.2）
3. **真正的分水岭是「压缩发生在一轮的哪个位置」。** Codex 有 **pre-turn 与 mid-turn 双入口**，mid-turn 能在工具循环中途就地压缩再继续——这是长任务不断粮的关键。Claude Code 和 Pi 也都在「每批工具结果落定后」复查阈值。（§4.2）
4. **压缩是分层降级的，不是单一动作。** Claude Code 六层（snip → microCompact → apiMicrocompact → contextCollapse → sessionMemory → autoCompact），按「先廉价裁剪、不够再昂贵摘要」排序；Codex 三条路径（TokenBudget 重置 / 远程摘要 / 本地摘要）；Pi 两层（源头截断 + 摘要）。
5. **摘要必须有固定结构，且以 user 消息身份注入。** 三家都禁止模型自由发挥摘要格式，都在 prompt 里写死 section 清单（Codex 4 项、Claude Code 9 项、Pi 6 项）。（§3.4 / §4.3 / §5.4）
6. **「可重建的状态」永远不进摘要，压缩后从源头重新注入。** 项目记忆（CLAUDE.md / AGENTS.md）、system prompt、skills、工具定义、权限决策——这些要么在磁盘上、要么能重算，占摘要预算是纯浪费。（§3.10 / §4.5 / §5.7）
7. **压缩后仍有重量级的状态保全工作。** Claude Code 的 `postCompactCleanup` 要重置 8 类模块级缓存；Codex 要重新注入 `WorldState` 和「已批准的命令前缀」；Pi 会把累计读改文件清单挂到摘要尾部。（§3.10 / §4.5 / §5.4）
8. **token 计量普遍是「真实 usage 锚定 + 估算补差」。** 三家都不信任纯估算：代码里普遍优先取上一次 API 响应的真实 usage，只对之后新增的消息用 `chars/4` 估算。Claude Code 甚至会对估算值 ×4/3 做保守 padding 防止低估。（§3.9 / §5.6）
9. **压缩与提示缓存（prompt caching）是一对需要显式设计的矛盾。** Codex 压缩时从**最旧项**开始删以保住前缀缓存、并用 `context_window_id` 追踪缓存连续性；Pi 直接给摘要请求标 `cacheRetention: "none"`，避免一次性请求污染缓存。（§4.6 / §5.4）
10. **生产环境的事故塑造了最终形态。** Claude Code 源码里留着一条注释：某些会话连续压缩失败 50+ 次（最高 3,272 次），全球每天浪费约 **25 万次 API 调用**——因此加了「连续失败 3 次即熔断」的断路器。（§3.10）

---

## 2. 统一分析框架：上下文压力的四个来源与三个干预层

### 2.1 压力从哪来

把三家的实现放在一起看，上下文增长只有四个来源，而**它们的治理手段完全不同**：

| 来源 | 增长特征 | 三家的治理位置 |
|---|---|---|
| **对话轮次** | 单调、缓慢、语义密度高 | 窗口层（摘要压缩） |
| **工具输出** | 突发、单次可达数十万 token、语义密度低 | 源头治理（产出时即截断/落盘） |
| **环境上下文** | 静态、可重建、每次都要重发 | 不治理（原样重发，或按需披露） |
| **系统提示与工具定义** | 固定开销、随工具数量线性增长 | 不治理（渐进披露缓解） |

**关键洞察**：工具输出是唯一「用少量语义损失换取大量 token 节省」性价比极高的目标，而它恰恰**不需要摘要**——截断就够了。三家都把它放在最前面处理（源头截断），而不是等窗口满了再压缩。这解释了为什么 Pi 的文档里直接点名「tool results (especially from `read` and `bash`) are typically the largest contributors to context size」。

### 2.2 三个干预层

三家的机制可以统一映射到一个三层架构上，层号越小越「早」、越廉价：

```
┌─────────────────────────────────────────────────────────────────┐
│  L1 源头层：产出时治理，永不进入上下文                            │
│  · 工具输出截断（保头/保尾/保两端）                                │
│  · 大输出落盘，只留路径 + 预览                                     │
│  · 图片降采样                                                      │
│  · Skills 渐进披露（只注入 name/description，正文按需 read）        │
├─────────────────────────────────────────────────────────────────┤
│  L2 传输层：消息数组不变，只在发往 API 的请求体上动手脚              │
│  · Claude Code: apiMicrocompact（cache_edits / clear_tool_uses）   │
│  · Claude Code: cached microcompact（删工具结果但不改本地消息）      │
├─────────────────────────────────────────────────────────────────┤
│  L3 窗口层：真正改写消息数组，语义有损                              │
│  · 轻量：清空旧工具结果内容，保留消息骨架（microCompact / snip）      │
│  · 重量：LLM 结构化摘要 + 保留近期原文（autoCompact / compact）      │
│  · 兜底：本地截断、逐条删最旧历史                                   │
└─────────────────────────────────────────────────────────────────┘
```

**这个分层是本报告最重要的可迁移结论**：大多数人提到「长上下文优化」只想得到 L3 摘要，而三家的工程量分配恰恰是 L1 > L3 > L2。L1 的投入产出比最高且几乎没有语义损失。

---

## 3. Claude Code：六层压缩体系

> 证据基础：`civil-engineering-cloud-claude-code-source-v2.1.88/03-claude-code-runnable/src/`（下称 `src/`）
> **重要前提**：本次拿到的是**外部发布版**（v2.1.88）的反编译源码。其中 `reactiveCompact`、`snipCompact`、`contextCollapse`、`cachedMicrocompact` 等文件**是被 tree-shaking 掉的桩（stub）**——函数体为空或恒返回原值，但注释完整保留了设计意图。下文会明确标注「已实现 / 仅桩」，因为**桩本身也是重要情报**：它揭示了官方内部版本的架构方向。

### 3.1 六层机制总览

主循环的调用顺序在 `src/query.ts:405-467`：

```
snip → microCompact → contextCollapse(桩) → autoCompact
```

`autoCompactIfNeeded`（`src/services/compact/autoCompact.ts:241`）内部再分两级：优先尝试 `sessionMemoryCompaction`（廉价），失败才落到 `compactConversation`（重量摘要）。

| # | 机制 | 文件 | v2.1.88 状态 | 解决什么 | 触发条件 |
|---|---|---|---|---|---|
| 1 | **snipCompact** | `compact/snipCompact.ts:1` | **桩**（`changed:false`） | 在 API round 边界砍掉被投影移除的消息 | 每轮调用但无效 |
| 2 | **microCompact** | `compact/microCompact.ts:253` | 部分实现 | 清空旧 tool_result 的**内容**，保留消息骨架 | 每次请求前（时间基 / 缓存编辑） |
| 3 | **apiMicrocompact** | `compact/apiMicrocompact.ts:64` | 仅内部 + env 开关 | 在 **API 请求体**上做原生 `context_editing` | env `USE_API_CLEAR_TOOL_RESULTS` |
| 4 | **contextCollapse** | `contextCollapse/index.ts:32` | **桩**（`isContextCollapseEnabled()→false`） | 「读时投影 + 提交/阻断」的归档机制 | feature 关闭 |
| 5 | **sessionMemoryCompact** | `compact/sessionMemoryCompact.ts:514` | 实验（flag 关） | 用后台维护的 memory md 文件当摘要，**零 API 调用** | `tengu_session_memory && tengu_sm_compact` |
| 6 | **autoCompact / compact** | `compact/compact.ts:387` | **主机制** | fork 子 agent 生成 9 段摘要，替换全部旧消息 | `tokenUsage ≥ 阈值` |

**分层逻辑（降级链）**：先做**轻量裁剪**（第 2 层清掉旧工具结果，消息骨架还在）→ 若仍超阈值，autocompact 先试 **sessionMemory**（不调摘要 API 的廉价路径）→ 都不行才做**重量摘要**（第 6 层）。

⚠️ **一个容易被忽略的耦合**：`autoCompact.ts:201-223` 的注释明确指出——**contextCollapse 打开时 autocompact 会被主动抑制**，因为 collapse「拥有」了 headroom 问题（其设计是 90% commit / 95% blocking）。在当前外部构建里 collapse 是桩，所以 autocompact 实际生效。

### 3.2 触发阈值：`effectiveWindow − 13_000`

真实实现（`src/services/compact/autoCompact.ts:33-49`）：

```ts
export function getEffectiveContextWindowSize(model: string): number {
  const reservedTokensForSummary = Math.min(
    getMaxOutputTokensForModel(model),
    MAX_OUTPUT_TOKENS_FOR_SUMMARY,      // = 20_000
  )
  let contextWindow = getContextWindowForModel(model, getSdkBetas())
  // env CLAUDE_CODE_AUTO_COMPACT_WINDOW 可 clamp 窗口
  return contextWindow - reservedTokensForSummary
}
```

阈值（`autoCompact.ts:72-91`）：

```ts
autoCompactThreshold = effectiveContextWindow - AUTOCOMPACT_BUFFER_TOKENS   // 13_000
// env CLAUDE_AUTOCOMPACT_PCT_OVERRIDE 可用百分比覆盖（取 min）
```

配套的三个水位（`autoCompact.ts:62-65`）：

| 常量 | 值 | 含义 |
|---|---|---|
| `AUTOCOMPACT_BUFFER_TOKENS` | **13 000** | 距上限剩这么多就自动压缩 |
| `WARNING_THRESHOLD_BUFFER_TOKENS` | 20 000 | 再低 20k → 黄色告警 |
| `ERROR_THRESHOLD_BUFFER_TOKENS` | 20 000 | 再低 20k → 红色告警 |
| `MANUAL_COMPACT_BUFFER_TOKENS` | **3 000** | 阻塞上限（`blockingLimit = effectiveWindow − 3000`） |
| `MAX_OUTPUT_TOKENS_FOR_SUMMARY` | 20 000 | 给摘要输出预留 |

**换算成实际数字**（200K 窗口模型）：`effectiveWindow = 200_000 − min(32_000, 20_000) = 180_000` → `autoCompactThreshold = 180_000 − 13_000 = 167_000`。即**在 200K 窗口下，约 83.5% 处触发自动压缩**。这和社区记录的「~95%」不同——因为社区观测的是「阻塞/失败」水位，而**主动压缩的阈值其实更保守**（167K 而非 190K）。这是本次源码分析相对前文文档最重要的修正。

模型窗口（`src/utils/context.ts`）：
- `MODEL_CONTEXT_WINDOW_DEFAULT = 200_000`（`:9`）——所有模型的默认值
- 1M 窗口需 `[1m]` 后缀或 `modelSupports1M`（sonnet-4 / opus-4-6）+ 1M beta（`:70-87`）
- `getModelMaxOutputTokens`（`:149-210`）：opus-4-6 默认 64k / 上限 128k；sonnet-4-6 默认 32k / 上限 128k；opus-4-5 / sonnet-4 / haiku-4 默认 32k / 上限 64k

### 3.3 microCompact：清内容不清消息

`src/services/compact/microCompact.ts`：

```ts
const COMPACTABLE_TOOLS = [FileRead, Shell, Grep, Glob, WebSearch, WebFetch, FileEdit, FileWrite]  // :41-50
const TIME_BASED_MC_CLEARED_MESSAGE = '[Old tool result content cleared]'   // :36
const IMAGE_MAX_TOKEN_SIZE = 2000                                            // :38
```

三级实现（`microcompactMessages` `:253-293`）：

1. **时间基触发**（`evaluateTimeBasedTrigger` `:422`，判定 `:438-443`，应用 `:454-462`）：距上次主循环 assistant 消息超过 `config.gapThresholdMinutes`（`config` 类型为 `TimeBasedMCConfig`）时，保留最近 `config.keepRecent` 个可压缩工具结果，其余内容全部替换为 `[Old tool result content cleared]`。
   ⚠️ **注意`gapThresholdMinutes` 与 `keepRecent` 不是本地硬编码常量，而是来自 GrowthBook 远端配置**（`getTimeBasedMCConfig()`；`pendingCacheEdits` 路径的注释明确写「Uses count-based trigger/keep thresholds from GrowthBook config」，`:301`）。即这两个值**可以在不发版的情况下从服务端调整**——这本身是一个值得注意的运营设计：阈值是可实验、可灰度的，而不是编译进二进制的。
   **设计理由**：服务端 prompt cache 已经过期，整段前缀本来就要重写——既然如此，先把最旧的工具结果清掉，缩小重写量。
2. **缓存编辑**（`feature('CACHED_MICROCOMPACT')`）：用 API 原生 `cache_edits` 删除工具结果，**本地消息数组不变**，只把 `pendingCacheEdits` 排队等 API 层生效（`:305-399`）。这是纯粹的 L2 层操作。
3. **legacy 路径**：本构建恒返回 `{messages}`（`:288` 注释「tengu_cache_plum_violet is always true」），实际无操作，交给 autocompact。

**值得注意的防御性设计**：`estimateMessageTokens`（`:164-205`）在估算后整体 **×4/3 向上取整**做保守 padding（`:203-204`），刻意高估以防低估导致超窗口。

### 3.4 摘要 prompt 与消息重装

`src/services/compact/prompt.ts`：
- `NO_TOOLS_PREAMBLE`（`:19`）：强制「只输出文本、禁止调用工具」
- `BASE_COMPACT_PROMPT`（`:61`）：要求先写 `<analysis>` 思考块，再写 `<summary>`
- `formatCompactSummary`（`:311-335`）：**剥离 `<analysis>`**（草稿），把 `<summary>…</summary>` 转成 `Summary:` 标题

摘要的 **9 个固定 section**（`:66-77`，原文摘录要点）：

```
1. Primary Request and Intent         用户全部显式请求与意图
2. Key Technical Concepts             重要技术概念/技术栈
3. Files and Code Sections            查看/修改/创建的文件与关键代码片段
4. Errors and fixes                   错误与修复方式，特别是用户的纠正反馈
5. Problem Solving                    已解决问题与进行中的排查
6. All user messages                  全部非工具结果的用户消息（原文要求 "List ALL"）
7. Pending Tasks                      明确被要求但未完成的任务
8. Current Work                       摘要请求前正在做的事（精确到文件名与代码片段）
9. Optional Next Step                 下一步，且要求「verbatim 引用最近对话」防止意图漂移
```

第 6 项和第 9 项是最有信息量的设计：**用户消息全量保留**（因为它承载意图），**下一步必须附原文引用**（防 drift）。这是对「摘要会丢微妙上下文」这一已知缺陷的针对性补偿。

**消息重装**（`src/services/compact/compact.ts`）：
- `streamCompactSummary`（`:1136`）默认走 **forked agent**，复用主对话的 prompt cache（`tengu_compact_cache_prefix` 默认 true，`:435`）；system 写死 `"You are a helpful AI assistant tasked with summarizing conversations."`（`:1303`），`thinking: {disabled}`（`:1305`）
- `buildPostCompactMessages`（`:330-338`）顺序：

```
boundaryMarker → summaryMessages → messagesToKeep → attachments → hookResults
```

- 重装前的清洗：`stripImagesFromMessages`（`:145`，图片替换为 `[image]`、文档替换为 `[document]`）、`stripReinjectedAttachments`（`:211`，剥离将被重注入的附件）
- 之后重注入 plan / skill / async-agent / deferred-tool 等附件（`:531-585`）

**摘要后的恢复预算**（`compact.ts:122-130`）——这组常量回答了「压缩完还剩什么」：

| 常量 | 值 | 说明 |
|---|---|---|
| `POST_COMPACT_MAX_FILES_TO_RESTORE` | **5** | 最多重读 5 个最近修改的文件 |
| `POST_COMPACT_TOKEN_BUDGET` | **50 000** | 后压缩阶段总预算 |
| `POST_COMPACT_MAX_TOKENS_PER_FILE` | 5 000 | 单文件上限 |
| `POST_COMPACT_MAX_TOKENS_PER_SKILL` | 5 000 | 单 skill 上限 |
| `POST_COMPACT_SKILLS_TOKEN_BUDGET` | 25 000 | skills 合计上限 |
| `MAX_COMPACT_STREAMING_RETRIES` | 2 | 流式摘要重试次数 |

源码里对 skills 那条留了很实在的注释：

> Skills can be large (verify=18.7KB, claude-api=20.1KB). Previously re-injected unbounded on every compact → 5-10K tok/compact. **Per-skill truncation beats dropping** — instructions at the top of a skill file are usually the critical part.

即：**每个 skill 截断比整体丢弃更好**，因为 skill 文件顶部的指令通常才是关键部分。这是一个可以直接迁移的「截断优于丢弃」判断准则。

### 3.5 apiMicrocompact：在请求体上做手脚

`src/services/compact/apiMicrocompact.ts`：

```ts
const DEFAULT_MAX_INPUT_TOKENS = 180_000      // :16  触发阈值
const DEFAULT_TARGET_INPUT_TOKENS = 40_000    // :17  保留目标
```

构造 `{edits: [...]}` 结构（`:64`），类型为 `clear_tool_uses_20250919`（`:112`）和 `clear_thinking_20251015`（`:84`）——这是 **Anthropic API 原生的 context editing 能力**。语义：输入超 180K 时，清掉约 140K token 的工具结果，保留到 40K。

**关键区别**：它改的是**发给 API 的请求体**，不是本地消息数组。这意味着本地完整历史仍然存在（可回看、可 resume），只是传输时被裁剪了。仅内部账号 + env（`USE_API_CLEAR_TOOL_RESULTS` / `USE_API_CLEAR_TOOL_USES`）开启（`:90-102`）。

### 3.6 sessionMemoryCompact：零 API 调用的压缩

机制与重量摘要的**本质区别**：后台 forked 子 agent 周期性把对话要点写进一个 **markdown 笔记文件**（`src/services/SessionMemory/sessionMemory.ts:1-5`）；压缩时**直接拿这个文件当摘要**——不调用摘要 API、不产生输出 token。

后台提取的节流参数（`SessionMemory/sessionMemoryUtils.ts:32-36`）：

| 参数 | 值 |
|---|---|
| `minimumMessageTokensToInit` | 10 000 |
| `minimumTokensBetweenUpdate` | 5 000 |
| `toolCallsBetweenUpdates` | 3 |

压缩时的保留配置（`sessionMemoryCompact.ts:57-61`）：

```ts
DEFAULT_SM_COMPACT_CONFIG = {
  minTokens: 10_000,           // 至少保留 10k token 原文
  minTextBlockMessages: 5,     // 至少保留 5 条文本消息
  maxTokens: 40_000,           // 硬上限 40k
}
```

门控 flag `tengu_session_memory && tengu_sm_compact`（`:412-420`，默认 false）。验证逻辑很关键：`sessionMemoryCompact.ts:605-614`——若压缩后仍 `≥ autoCompactThreshold`，**放弃本次结果并回退到重量摘要**。即廉价路径必须自证有效，否则不占用决策权。

### 3.7 contextCollapse：设计意图（桩）

`src/services/contextCollapse/index.ts`：`isContextCollapseEnabled()→false`（`:32`）、`applyCollapsesIfNeeded → {changed:false}`（`:38`）、`resetContextCollapse()` 空（`:36`）。

虽然在本构建中是桩，但注释与 `autoCompact.ts:201-223`、`query.ts:428-447` 保留了完整设计：把上下文做「**读时投影（read-time projection）+ 提交 collapse**」，**90% 水位提交 collapse，95% 水位阻塞**并生成子 agent 处理。归档后的消息从 REPL 的消息数组中移出，摘要存进 collapse store。

**结论**：它**确实改 prompt，不是纯 UI 机制**。它代表官方在 autocompact 之外的下一代方向——「把长历史变成可查询的归档，而不是一次性摘要成一段文本」。这个思路和 Pi 的树形投影、以及 Anthropic 博客里的 memory tool 是同一路的。

### 3.8 工具输出截断

`src/constants/toolLimits.ts`：

| 常量 | 值 | 位置 |
|---|---|---|
| `DEFAULT_MAX_RESULT_SIZE_CHARS` | **50 000** | `:13` 系统级单工具结果持久化阈值 |
| `MAX_TOOL_RESULT_TOKENS` | 100 000 → `MAX_TOOL_RESULT_BYTES = 400 000` | `:22-33` |
| `MAX_TOOL_RESULTS_PER_MESSAGE_CHARS` | **200 000** | `:49` 单条消息内所有 tool_result 的聚合预算 |

第三条尤其聪明：**按消息聚合限额**，保证即使并行发起 N 个各 15 万字符的工具调用，总量也不会失控。

**FileRead**（`tools/FileReadTool/limits.ts:18`）：`DEFAULT_MAX_OUTPUT_TOKENS = 25 000`；`utils/file.ts:48` `MAX_OUTPUT_SIZE = 0.25MB = 262 144` 字节；`prompt.ts:10` `MAX_LINES_TO_READ = 2000`。
超限行为是**抛错而非截断**（`FileReadTool.ts:178-181`）：`"File content (N tokens) exceeds maximum allowed tokens…"`，引导模型改用 `offset`/`limit` 分段读。**这是「让模型自己重新取」而非「给模型残缺数据」的范例**——正确的做法，因为模型知道怎么分段读，但不知道被截断的上下文丢了什么。

**Bash**（`tools/BashTool.tsx:424`）：`maxResultSizeChars = 30 000`。超过 30k 字符 → **持久化到磁盘**，模型只收到 2000 字节预览 + 文件路径（`toolResultStorage.ts:109` `PREVIEW_SIZE_BYTES = 2000`、`:189-198`）。提示文本：

```
Output too large (X). Full output saved to: <path> …
Preview (first 2.00 KB):
```

`getPersistenceThreshold`（`:55-78`）= `min(declaredMaxResultSizeChars, 50000)`；`generatePreview`（`:337-355`）在**换行边界**截断，保留头部，标 `hasMore`。

`EndTruncatingAccumulator`（`utils/stringUtils.ts:140`，默认 `MAX_STRING_LENGTH = 2^25 ≈ 33M`，`:88`）只是防 OOM 的安全网，正常限制是 30k 持久化阈值。

### 3.9 token 估算：三层策略

`src/services/tokenEstimation.ts`：

- **精确**：`countTokensWithAPI`（`:124`，调用官方 countTokens API）；`countTokensViaBedrock`（`:437`）；`countTokensViaHaikuFallback`（`:251`，用 Haiku 计 token 以规避主模型配额）
- **启发式**：`roughTokenCountEstimation(content, bytesPerToken = 4)`（`:203`，`length/4`）；JSON/JSONL 用 `bytesPerToken = 2`（`:215-224`，更准）；图片/文档按 **2000** token 折算（`:411`）

`src/utils/tokens.ts` 的 `tokenCountWithEstimation`（`:226-261`）是核心：**以最近一次 API 响应的真实 usage（input + output + cache）为基准**，之后新增的消息才用 rough 估算补齐。并行工具调用会回溯到同 `message.id` 的首个分片，避免漏算 interleaved 的 tool_result。

源码注释里有一句坦白（`:230-242`）：Bedrock 下精确 API 不可用只能退回启发式，**低估会让超大工具结果溜进上下文**——这是已知的残余风险。结合 §3.3 的 ×4/3 padding，可以看出官方的态度：**宁可高估（多压一次）也不低估（超窗失败）**。

### 3.10 清理、告警与熔断

**压缩后清理**（`src/services/compact/postCompactCleanup.ts:31-77`）——仅主线程 compact（非子 agent）执行，重置 8 类模块级状态：

```
resetMicrocompactState()                      :41
resetContextCollapse()                        :42-50
getUserContext.cache.clear()                  :59
resetGetMemoryFilesCache('compact')           :60   ← 重新触发 CLAUDE.md 注入
clearSystemPromptSections()                   :62
clearClassifierApprovals()                    :63
clearSpeculativeChecks()                      :64   ← Bash 权限预检
clearBetaTracingState()                       :70
sweepFileContentCache()                       :71-75
clearSessionMessagesCache()                   :76
```

**刻意不做的事**（`:65-69` 注释）：**不**重置 `resetInvokedSkills` / `sentSkillNames`。理由写得很明确——重新注入 4k 的 skill 列表是纯粹的 `cache_creation` 浪费，而且模型 schema 里本来就还有 SkillTool。**这是一个「什么不该重置」的精彩案例**：优化不只是做减法，也是拒绝做无谓的加法。

**熔断器**（`autoCompact.ts:70`）：

```ts
const MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3
// BQ 2026-03-10: 1,279 sessions had 50+ consecutive failures (up to 3,272)
// in a single session, wasting ~250K API calls/day globally.
```

同一行注释里还解释了用途：`circuit breaker to stop retrying when the context is irrecoverably over the limit (e.g., prompt_too_long)`。**这是本次源码分析中最有工程价值的一条**——它说明「压缩」本身也会失败，而且失败时会形成重试风暴；任何生产级实现都必须有熔断。

**告警抑制**（`compactWarningState.ts:4-18`）：压缩成功后**立即抑制**「距 autocompact 还剩多少」的警告，因为下一个 API 响应回来之前 token 数其实是未知的。避免给用户看一个立刻会变的假数字。

---

## 4. OpenAI Codex：三路径 + 四触发点

> 证据基础：`openai/codex` 的 `codex-rs/`（Rust）。核心入口 `codex-rs/core/src/session/turn.rs` 的 `run_auto_compact`（`:1408-1453`）。

### 4.1 三条实现路径

Codex 依据**能力开关**在运行时选择三条路径之一：

| 路径 | 条件 | 行为 |
|---|---|---|
| **Token Budget 重置** | `Feature::TokenBudget` 开启 | 纯本地、**不做 LLM 摘要**，直接安装一个全新上下文窗口（`compact_token_budget.rs:24-84`，`:73` 调 `start_new_context_window`） |
| **远程压缩 V2** | provider 能力 `RemoteCompactionSupport::V2` | 把整段历史发给**服务端**，服务端返回加密的 `ResponseItem::Compaction`（`compact_remote_v2.rs`） |
| **本地摘要**（默认） | 其余情况 | 本地用 LLM 生成摘要（`compact.rs`） |

三条路径的调度在 `turn.rs:1420-1437`。值得注意的是 **TokenBudget 路径完全不调用任何 LLM**——它是一个「重开一局」的语义，但复用了 compact hook 的完整生命周期（事件、统计）。

### 4.2 触发条件：90% 阈值 + 四类触发点

**阈值计算**（`codex-rs/protocol/src/openai_models.rs:521-533`，已实测复核）：

```rust
pub fn auto_compact_token_limit(&self) -> Option<i64> {
    let context_limit = self
        .resolved_context_window()
        .map(|context_window| (context_window * 9) / 10);   // 硬编码 90%
    let config_limit = self.auto_compact_token_limit;
    if let Some(context_limit) = context_limit {
        return Some(config_limit.map_or(context_limit, |limit| std::cmp::min(limit, context_limit)));
    }
    config_limit
}
```

**硬顶**（`openai_models.rs:389-391`，已实测复核）：`default_effective_context_window_percent() -> 95`，配合 `usable_context_window()`（`:515-519`）= `context_window × percent / 100`。

**注意两者的分工**：90% 是**自动压缩的触发线**，95% 是**可用上下文的硬上限**。配置了 `model_auto_compact_token_limit` 时取 `min(配置值, 90%)`——即**用户只能把触发点调早，不能调晚**。这是一个刻意的安全设计。

判定核心在 `core/src/session/context_window.rs:52-121`：

```rust
// :83-85  硬上限
let full_context_window_limit = model_info.resolved_context_window()
    .map(|context_window| context_window * effective_context_window_percent / 100);

// :107-109  触发
let token_limit_reached = buffered_auto_compact_limit
        .is_some_and(|limit| auto_compact_scope_tokens >= limit)
    || full_context_window_limit_reached;
```

**fallback buffer**（`context_window.rs:97-102`）：`token_budget.fallback_buffer_tokens`，无配置时为 0，模型默认（`models.json`）为 **16384**。

**四类触发点**：

1. **Pre-turn（回合前主动）**：入口 `run_pre_sampling_compact`（`turn.rs:1231-1260`），在 `run_turn` 构建采样步骤之前调用（`turn.rs:183`）：

```rust
// turn.rs:1243
if token_status.token_limit_reached {
    run_auto_compact(..., CompactionPhase::PreTurn, InitialContextInjection::DoNotInject);
}
```

2. **Mid-turn（回合中主动）**——长任务不断粮的关键。turn 主循环里每次模型步产出后重新评估（`turn.rs:600-639`）：

```rust
// turn.rs:600-601
let should_roll_over = needs_follow_up
    && (sess.take_new_context_window_request().await || token_limit_reached);

// turn.rs:612-624
if should_roll_over {
    run_auto_compact(..., InitialContextInjection::BeforeLastUserMessage{...},
                     CompactionReason::ContextLimit, CompactionPhase::MidTurn);
}
```

条件是**模型还想继续调用工具**（`needs_follow_up`）**且**已达阈值。mid-turn 用 `BeforeLastUserMessage` 注入方式，保证摘要出现在历史末尾、模型立刻能看到。

3. **CompHashChanged（模型切换）**：`turn.rs:1308-1341`。`comp_hash` 变化（压缩协议版本不一致）时，**先用旧模型压缩再切换**。
4. **ModelDownshift（降级到小窗口模型）**：`turn.rs:1343-1388`。条件为 `old_context_window > new_context_window` 且已超出新模型的阈值。

后两类触发点在别家实现里没有对应物，是**支持多模型动态切换**这一产品形态倒逼出来的设计。对本项目的启示：如果面试过程中会切换模型（如便宜模型做初筛、贵模型做深挖），**切模型前必须先压缩**。

**被动补救**（API 返回 `ContextWindowExceeded`）：
- 压缩请求自身若仍超窗，**从最旧的历史项往前删**以保留缓存前缀（`compact.rs:308-317`，注释 `"Trim from the beginning to preserve cache (prefix-based)"`）
- 普通会话：pre-turn 的 `run_pre_sampling_compact` 已主动拦截；若 API 仍报错，`turn.rs:1613-1616` 把 token 用量置满并返回错误，回合中止并提示用户
- Guardian 审查子代理专用：`turn.rs:706-738` 在 `ContextWindowExceeded` 时**重试一次 mid-turn 压缩**（每步仅一次，防死循环）

### 4.3 本地摘要算法：只保留用户消息

`codex-rs/core/src/compact.rs` 是「**LLM 生成摘要 + 本地截断保留的用户消息**」的组合：

1. 把**整段历史**连同压缩 prompt 作为 user message 发给模型（`compact.rs:121-131, 246-285`）：
```rust
let prompt = turn_context.config.compact_prompt
    .as_deref().unwrap_or(SUMMARIZATION_PROMPT).to_string();
```
2. 取模型最后一条 assistant 消息作为摘要，拼上 `SUMMARY_PREFIX`（`compact.rs:352-354`）
3. 重建历史（`compact.rs:665-755` `build_compacted_history_with_limit`）：保留**最近的用户消息**，总预算 `COMPACT_USER_MESSAGE_MAX_TOKENS = 20_000`（`compact.rs:61`），每条按剩余 budget 逐条 `truncate_text`，再追加摘要

**摘要 prompt 原文**（`codex-rs/prompts/templates/compact/prompt.md`，完整引用）：

```
You are performing a CONTEXT CHECKPOINT COMPACTION. Create a handoff summary for another LLM that will resume the task.

Include:
- Current progress and key decisions made
- Important context, constraints, or user preferences
- What remains to be done (clear next steps)
- Any critical data, examples, or references needed to continue

Be concise, structured, and focused on helping the next LLM seamlessly continue the work.
```

**摘要前缀原文**（`.../compact/summary_prefix.md`）：

```
Another language model started to solve this problem and produced a summary of its thinking process.
You also have access to the state of the tools that were used by that language model.
Use this to build on the work that has already been done and avoid duplicating work.
Here is the summary produced by the other language model, use the information in this summary to assist with your own analysis:
```

**结构极简**（`core/src/context/compaction_summary.rs`）：就是 `CompactionSummary { summary: String }`，作为 `ContextualUserFragment`，`role = "user"`、`content_kind = "compaction.summary"`。

**真实快照佐证**（`core/tests/suite/snapshots/all__suite__compact__mid_turn_compaction_shapes.snap`）——这是最能说明「压缩长什么样」的证据：

```
request 2（压缩请求）= 完整前缀 + function_call/function_call_output + <SUMMARIZATION_PROMPT>
request 3（续跑请求）= 前缀 + <COMPACTION_SUMMARY> + AUTO_SUMMARY
```

即：**整段历史喂给模型 → 摘要以 user 消息回填到历史尾部 → 续跑**。

### 4.4 远程压缩：为什么把摘要卸载到服务端

**入口**：`run_auto_compact` 检测到 `RemoteCompactionSupport::V2` 时走 `run_inline_remote_auto_compact_task_v2`（`turn.rs:1420-1437`）。该能力由 provider 声明——OpenAI Codex 后端与 Amazon Bedrock 均标 `V2`（`model-provider/src/provider.rs:220, 626, 656-687`。

**协议**（`compact_remote_v2_attempt.rs:76`）：客户端发送整段历史 + 一个 `ResponseItem::CompactionTrigger {}` **哨兵项**；服务端返回**恰好一个** `ResponseItem::Compaction { encrypted_content }`（`compact_remote_v2.rs:419-481`）。

**动机**：
1. 服务端可以用**更便宜/更合适的模型**做摘要
2. 服务端可**复用自身缓存**
3. `comp_hash` 由服务端保证跨压缩兼容（客户端版本升级不会导致摘要不可读）
4. `encrypted_content` 意味着**摘要内容对客户端不可见**——这是隐私与防篡改的考虑

**`compact_remote_trimming` 裁剪什么**：`compact_remote_history.rs:68` 的 `trim_function_call_history_to_fit_context_window` 在把历史发给服务端**之前**，把超窗的 `FunctionCallOutput` / `CustomToolCallOutput` 的 body 改写为（`:16-17, 181-186`）：

```
Output exceeded the available model context and was truncated
```

即**先修剪工具输出体积，避免压缩请求本身超窗**——否则会陷入「为了压缩而发出的请求自己就超窗」的死锁。

**保留形状**（`compact_remote_v2.rs:483-578`）：保留 user 消息、hook prompt、client-authored developer 消息；**丢弃** system、agent 进度/完成消息、function call、旧 compaction 项；随后截断到两个预算（`:73-74`）：

| 常量 | 值 |
|---|---|
| `RETAINED_MESSAGE_TOKEN_BUDGET` | **64 000** |
| `MAX_RETAINED_AGENT_MESSAGE_TOKENS` | **10 000** |

### 4.5 状态保全与 turn 对齐

- **权限决策**（`core/src/context/world_state/compact_permissions.rs`）：`CompactPermissionsState` 把「新批准的命令前缀」（`approved_command_prefixes`）渲染成 developer 片段，**跨压缩保留**。这解决了一个很实际的问题：用户刚批准的「允许执行 `npm test` 前缀命令」，不能因为压缩而要求重新批准。
- **WorldState 重注入**：mid-turn 用 `InitialContextInjection::BeforeLastUserMessage { world_state, step_context }`（`compact.rs:72-78`）把 world_state 与 reference context 重新注入到摘要之前的边界（`compact.rs:370-381`）；pre-turn / manual 用 `DoNotInject` 清空 `reference_context_item`，下一回合自动重新注入（`compact.rs:63-78`）。
- **图片**：`compact_remote_v2_images.rs` 配合 `Feature::CompactionImageBudget`，在 `RETAINED_MESSAGE_TOKEN_BUDGET` 内保留图片，超大图片走 `truncate_message_to_token_budget`（`compact_remote_v2.rs:308-314, 652-656`）。
- **turn 对齐**：压缩边界始终与 user turn 对齐，**绝不切断 `tool_call` / `tool_result` 配对**。`thread_rollout_truncation.rs` 的切分点全部落在 user message 边界上（`truncate_rollout_before_nth_user_message_from_start`、`truncate_rollout_to_last_n_fork_turns`）——注意这个文件的服务对象是**分支/fork**，不是会话内溢出，但它的边界规则与压缩一致。
- **摘要位置**：`compact.rs:597-663` 的 `insert_initial_context_before_last_real_user_or_summary` 确保「摘要作为最后一项、初始上下文插到最后一个真实 user 消息之前」；`compact.rs:69-71` 说明 mid-turn 的 `BeforeLastUserMessage` 保证模型「看到摘要作为历史最后一项」。压缩事件本身记录为 `ContextCompactionItem` 回合项（`compact.rs:243`）。

### 4.6 提示缓存配合

Codex 在这方面的设计是三家最精细的：

- **窗口标识**：每个压缩窗口带 UUID `context_window_id`，通过 `responses_metadata.rs:34`（`CONTEXT_WINDOW_ID_KEY = "context_window_id"`）写入请求（`session/mod.rs:4376-4384`、`responses_metadata.rs:404-405`），用于识别缓存连续性
- **`BodyAfterPrefix` 作用域**（`context_window.rs:67-79`）：只对「前缀之后的 body 增量」计数——**压缩只裁剪 body，不动已缓存的 initial-context 前缀**，`auto_compact_window_prefill_tokens` 作为 baseline
- **压缩自身保缓存**：超窗时**从最旧项**而非前缀删起（`compact.rs:308-317`）
- **跨窗口追踪**：`state/auto_compact_window.rs` 记录 `prefill_input_tokens`（`ServerObserved` / `Estimated` 两态），`ensure_auto_compact_window_server_prefill_from_usage` 从服务端用量回填（`session/mod.rs:4612`）
- **可观测**：压缩 analytics 同时记录 `cached_input_tokens` 与 `cache_write_input_tokens`（`compact.rs:422-424`、`compact_remote_v2.rs:301-302`）

**为什么要这么麻烦**：prompt cache 的命中依赖「前缀字节完全一致」。压缩天然会改写历史——如果改写位置太靠前，整个缓存作废，成本反而比不压缩更高。所以 Codex 的核心手法是：**压缩只动尾部增量，前期尽量保持字节稳定**。

### 4.7 工具输出截断

- **统一原语**：`codex_utils_output_truncation`（`utils/output-truncation/src/lib.rs`）。`truncate_text`（`:33-38`）按 `TruncationPolicy::Bytes | Tokens` 走 `truncate_middle_chars` / `truncate_middle_with_token_budget`——即**中间截断，保留头尾**（`utils/string/src/truncate.rs:1-68`，`split_budget` 头尾均分）
- **序列化余量**：`with_serialization_allowance` 给预算 **×1.2**（+20% 余量，`lib.rs:16-18`）
- **截断提示语**（`lib.rs:20-31`）：`"Warning: truncated output (original token count: N)\nTotal output lines: M\n\n…"`
- **exec / shell 工具**：`DEFAULT_MAX_OUTPUT_TOKENS = 10_000`（`unified_exec/mod.rs:79`），硬上限 `UNIFIED_EXEC_OUTPUT_MAX_BYTES = 1 MiB`（≈ 262 144 token，`:80-81`）
- **MCP 工具**：`MCP_TOOL_CALL_EVENT_RESULT_MAX_BYTES`（`mcp_tool_call.rs:960, 974`）
- **可配置**：`tool_output_token_limit`（`config/src/config_toml.rs:322`）会作为该工具输出的 `history_truncation_token_limit`，覆盖模型默认策略（`core/src/tools/registry.rs:206`、`context_manager/history.rs:370-372`）

**三家截断策略对比**（这是一个具体的选择差异，值得注意）：Codex 保头尾（中间截断）、Pi 的 read 保头 / bash 保尾、Claude Code 保头 + 全量落盘。**没有一家用「只保头」作为唯一策略**——因为报错信息通常在尾部，而上下文线索在头部。

### 4.8 可配置项

`config/src/config_toml.rs`：

| 配置项 | 行号 | 说明 |
|---|---|---|
| `model_context_window` | `:166` | 覆盖上下文窗口大小 |
| `model_auto_compact_token_limit` | `:169` | 自动压缩阈值（超限会被夹到 90%） |
| `model_auto_compact_token_limit_scope` | `:173` | `Total` / `BodyAfterPrefix` |
| `compact_prompt` | `:257` | 自定义摘要 prompt（`compact.rs:122-126` 运行时使用） |
| `experimental_compact_prompt_file` | `:536` | 从文件读摘要 prompt |
| `tool_output_token_limit` | `:322` | 工具输出截断 token 预算 |
| `[features.token_budget]` | `config/mod.rs:1155-1161` | 开启纯本地重置模式 + `auto_compact_fallback_prompt` / `auto_compact_fallback_buffer_tokens`（模型默认 16384） |

功能开关：`Feature::TokenBudget`、`Feature::CompactionImageBudget`、`Feature::RetainClientDeveloperMessages` 控制三条路径与保留行为。逐 step 的压缩模式选择（如 `CompactionMode::RemoteV2`）在 `core/tests/suite/step_settings_compaction.rs:38` 有验证。

---

## 5. Pi：两机制 + 一个反直觉的架构选择

> 证据基础：`earendil-works/pi` 的 `packages/coding-agent/src/`（下称 `src/`）。Pi 官方文档 `docs/compaction.md` 写得相当完整，本章**重点标注文档未写、但源码里有的细节**（标 ★）。

### 5.1 一个反直觉的架构选择 ★

**Pi 对静态上下文没有任何 token 预算，也永不压缩。**

`buildSystemPrompt()`（`src/core/system-prompt.ts:28`）与 `loadProjectContextFiles()`（`src/core/resource-loader.ts:119`）会把以下内容**完整注入、永久驻留**：

| 内容 | 位置 |
|---|---|
| system prompt 模板 + 工具列表 + guidelines + pi 文档路径 | `system-prompt.ts:127-165` |
| context files（`AGENTS.override.md` / `AGENTS.md` / `CLAUDE.md` 等） | `resource-loader.ts:72`，包进 `<project_context><project_instructions>`（`system-prompt.ts:151-158`） |
| skills（`formatSkillsForPrompt()`） | `system-prompt.ts:161` |
| 工具定义 | 走 API `tools` 字段（非 system prompt 文本） |

**只有「消息历史」会被 compaction 处理，压缩也不会去裁剪这些静态部分。**

这是一个明确的架构取舍：Pi 选择**最大化指令可见性**（模型永远看到完整的项目规则与技能清单），代价是静态开销随项目复杂度增长。相比之下 Claude Code 的 skills 是渐进披露（system prompt 只注入 name/description/location，正文按需 read）。两种路线各有道理——Pi 的作者在博客里主张「exactly controlling what goes into the model's context」，这里的「控制」指的是**不让压缩去动它**，而不是**省着用**。

对本项目的直接启示：**要明确区分「可压缩的对话历史」和「不可压缩的指令层」**。面试场景下，评分 rubric、岗位要求、简历全文属于后者（永不压缩、每次原样注入），只有问答历史属于前者。

### 5.2 触发链路：真实 usage 优先 ★

```ts
// src/core/compaction/compaction.ts:235
export function shouldCompact(contextTokens: number, contextWindow: number, settings: CompactionSettings): boolean {
	if (!settings.enabled) return false;
	return contextTokens > contextWindow - settings.reserveTokens;
}
```

**`contextTokens` 怎么算出来**（文档没说清，源码里是关键设计）：
- threshold 路径（`agent-session.ts:2230-2256`）优先取**上一条 assistant 消息的真实 usage**——`directContextTokens = calculateContextTokens(assistantMessage.usage)`（`compaction.ts:146`，即 `usage.totalTokens || input + output + cacheRead + cacheWrite`）
- 只有 `stopReason === "error"` 或 usage 为 0 时才回退到 `estimateContextTokens()`（chars/4 启发式，`compaction.ts:202`）

★ **即：正常对话里触发压缩用的是提供商返回的真实 token 数，不是估算值。** 估算只在 API 报错/零 usage 时兜底。

**`contextWindow` 从哪来**：来自 `Model` 对象的 `model.contextWindow`（`agent-session.ts:2161`），而 `Model` 来自模型元数据表（`models.json` / provider 配置 / `modelOverrides`）。`provider-composer.ts:160` 给了 **128 000** 兜底；分支摘要 `branch-summarization.ts:312` 也用 `model.contextWindow || 128000`。
★ **没有任何运行时「探测」API 来动态获取上下文窗口——完全是元数据驱动。**

**默认常量**（`compaction.ts:134-135`、`settings-manager.ts:18-21`）：

```ts
DEFAULT_COMPACTION_TOKEN_SETTINGS = {
  reserveTokens: 16_384,      // 给响应预留
  keepRecentTokens: 20_000,   // 最近 20k token 保留原文
}
```

### 5.3 overflow：三态检测 + 只重试一次

`reason` 三态 `"manual" | "threshold" | "overflow"`（`src/core/extensions/types.ts:600/612/621`），由 `_checkCompaction()`（`agent-session.ts:2154`）统一分发。

**overflow 的检测**（`packages/ai/src/utils/overflow.ts:134` `isContextOverflow`）——这是 Pi 做得最工程化的一层，覆盖三类信号：

1. **显式错误**：`stopReason === "error"` 且 errorMessage 命中 `OVERFLOW_PATTERNS`（`overflow.ts:37-63`）。该表收录 **30+ 家 provider 的溢出错误正则**（Anthropic "prompt is too long"、OpenAI "exceeds the context window"、Google、Mistral、xAI、Groq、OpenRouter、Cerebras、DashScope…），并用 `NON_OVERFLOW_PATTERNS`（`overflow.ts:74`）**排除限流/429**（误判限流为溢出会很糟）
2. **静默溢出**（z.ai 式）：`stopReason === "stop"` 且 `input + cacheRead > contextWindow`——**API 不报错，但实际已经超了**
3. **MiMo 式截断**：`stopReason === "length"` 且 `output === 0` 且 `input + cacheRead >= contextWindow * 0.99`

**处理分两种 Case**：
- **Case 1（`willRetry = true`，被中断的回复）**：移除 agent state 里最后那条失败/截断的 assistant 消息（`agent-session.ts:2219-2222`），置 `_overflowRecoveryAttempted = true`，压缩后 `agent.continue()` **重试一次**（`:2410-2420`）
- **Case 2（`willRetry = false`，正常运行完成的回复）**：仅压缩，不重试（`:2190-2192`）

**防无限循环**：`_overflowRecoveryAttempted` 保证仅重试一次，二次失败直接报错退出（`agent-session.ts:2194-2214`）。

★ 文档未强调：`isRecoverableLength()`（`overflow.ts:171`，`stopReason === "length" && output < desiredMaxOutput`）也走 overflow 压缩，但属于「输出被截断的可恢复长度」路径，与纯上下文超限区分开。

**为什么值得单独做一层检测**：如果只依赖「我算出来超了」，那么 provider 的 behavior 差异（有的报错、有的静默、有的返回空输出）会导致漏检。**溢出检测必须是多 provider 的一等公民**——这对任何用多家模型的项目都适用。

### 5.4 cut point 算法与摘要

**cut point**（`compaction.ts:403-461` `findCutPoint`）：
- 有效切点（`findValidCutPoints` `:351`，`isCutPointMessage` `:308`）：user / assistant / bashExecution / custom / branchSummary / compactionSummary 可切；**toolResult 永不可切**（避免切断 tool_call/tool_result 配对）
- 累加：从最新向最旧遍历（`:419-439`），对每条 entry 用 `sessionEntryToContextMessages(entry)` 取消息并 `estimateTokens()` 累加，**一旦 `accumulatedTokens >= keepRecentTokens` 就停止**，取该位置之后最近的合法切点
- 估算函数 `estimateTokens()`（`:266`）：**chars/4 启发式**（保守高估）。图片块按 `ESTIMATED_IMAGE_CHARS = 4800`（`:244`）折算

**split turn**（`compaction.ts:451-460`）：若切点消息不是 turn 起点（`isTurnStartMessage` 仅 user / bashExecution / custom / branchSummary / compactionSummary 为真），则置 `isSplitTurn = true`，把该 turn 的前缀单独摘要，最后合并：

```ts
// compaction.ts:925
summary = historyText + "\n\n---\n\n**Turn Context (split turn):**\n\n" + turnPrefixResult.text
```

**摘要 prompt 原文**（`compaction.ts:467-498`，完整引用）：

```
The messages above are a conversation to summarize. Create a structured context checkpoint summary that another LLM will use to continue the work.

Use this EXACT format:

## Goal
[What is the user trying to accomplish? Can be multiple items if the session covers different tasks.]

## Constraints & Preferences
- [Any constraints, preferences, or requirements mentioned by user]
- [Or "(none)" if none were mentioned]

## Progress
### Done
- [x] [Completed tasks/changes]

### In Progress
- [ ] [Current work]

### Blocked
- [Issues preventing progress, if any]

## Key Decisions
- **[Decision]**: [Brief rationale]

## Next Steps
1. [Ordered list of what should happen next]

## Critical Context
- [Any data, examples, or references needed to continue]
- [Or "(none)" if not applicable]

Keep each section concise. Preserve exact file paths, function names, and error messages.
```

**增量更新（迭代摘要）**——这是 Pi 相对另外两家最优雅的设计。`generateSummaryWithUsage()`（`compaction.ts:656`）里：

```ts
// compaction.ts:678
let basePrompt = previousSummary ? UPDATE_SUMMARIZATION_PROMPT : SUMMARIZATION_PROMPT
```

有旧摘要时，把旧摘要包进 `<previous-summary>` 标签拼到对话之后（`:690-693`）。更新 prompt（`:537`）的核心规则：

```
- PRESERVE all existing information from the previous summary
- ADD new progress, decisions, and context from the new messages
- UPDATE the Progress section: move items from "In Progress" to "Done" when completed
- PRESERVE exact file paths, function names, and error messages
- If something is no longer relevant, you may remove it
```

**为什么增量更新是对的**：朴素的「每次都把全部历史重新摘要一遍」会导致信息在多轮压缩中逐次衰减（每摘要一次都是一次有损压缩）。Pi 的做法是**维护单一滚动摘要**，新信息只做「合并」而非「重新生成」——旧摘要的字节在 prompt 里原样存在，模型的任务是**追加**而不是**复述**。

**摘要输出长度上限**：

| 场景 | 上限 | 位置 |
|---|---|---|
| 主摘要 | `min(floor(0.8 × reserveTokens), model.maxTokens)` | `compaction.ts:672` |
| split turn 前缀 | `0.5 × reserveTokens` | `compaction.ts:983` |
| 分支摘要 | `min(4096, model.maxTokens)` | `branch-summarization.ts:345` |

**摘要请求不污染缓存**（★文档提到但值得强调）：摘要请求带 `cacheRetention: "none"`，且使用**全新的 routing session id**——因为这类一次性 prompt 大概率不会被复用，写缓存是纯浪费。

**失败即拒绝落盘**（一个细节设计）：`getSummarizationFailure()` 返回错误信息的条件是——摘要响应以 `length` 停止（被截断）。注释写得很清楚：**「A length stop contains partial text and must not become a session checkpoint」**。即：**宁可不压缩，也不能让一个残缺的摘要成为后续所有对话的基础**。这是对「有损压缩必须有质量门」的正确认识。

### 5.5 序列化与截断

`serializeConversation()`（`src/core/compaction/utils.ts:109-150`）把 LLM 消息序列化成人可读文本：

```
[User]: What they said
[Assistant thinking]: Internal reasoning
[Assistant]: Response text
[Assistant tool calls]: read(path="foo.ts"); edit(path="bar.ts", ...)
[Tool result]: Output from tool
```

**目的**：防止模型把要摘要的内容当成「待继续的对话」而直接续写。

- **tool result 截断到 2000 字符**：`TOOL_RESULT_MAX_CHARS = 2000`（`utils.ts:89`），在 `:144` 调用 `truncateForSummary()`
- **截断标记**：`truncateForSummary()`（`utils.ts:95`）保留头部，尾部插 `[... ${truncatedChars} more characters truncated]`（`:98`）。注意：**只留头、丢弃尾**（与 Codex 的保头保尾不同）
- system 角色固定为 `SUMMARIZATION_SYSTEM_PROMPT`（`utils.ts:156`，含 "Do NOT continue the conversation"）

### 5.6 token 估算与校准

- 估算器 `estimateTokens()` 是 **chars/4 启发式**（无 tiktoken，无精确 tokenizer），见 `compaction.ts:266`，注释自认 "conservative (overestimates tokens)"
- ★ **校准机制（文档未点明）**：`estimateContextTokens()`（`compaction.ts:202`）采用「**真值锚定**」策略——取最后一条有效 assistant 消息的 `usage`（真实）作为 `usageTokens`，**只对它之后的新消息**用 chars/4 估算（`trailingTokens`）。换言之，**最近一次真 usage 直接覆盖其之前所有历史的估算**，无需回写
- 用于 footer/状态的 `getContextUsage()`（`agent-session.ts:3411`）同样走这条路径，并在压缩后、尚未产生新真 usage 前返回 `tokens: null`（未知，`:3442-3443`）——**宁可显示未知也不显示错数**
- ★ 偏差提示：chars/4 **只对英文是保守高估**（实测英文高估 1.34×）。**对中文方向相反——是低估**：本机实测中文为 0.70–0.96 token/字符，`len/4` 只估到真实值的 26%–36%（见 §0.5）。Pi 源码注释写的 "conservative (overestimates tokens)" 是以英文语境为前提的，**本项目不能直接照搬这个系数**。

### 5.7 工具输出截断（源头治理）

`src/core/tools/truncate.ts:11-13`：

```ts
DEFAULT_MAX_LINES = 2000
DEFAULT_MAX_BYTES = 50 * 1024      // 50KB
GREP_MAX_LINE_LENGTH = 500
```

两条独立上限，先命中者生效；各工具选择不同的保留侧：

| 工具 | 策略 | 超限提示 |
|---|---|---|
| `read`（`tools/read.ts:12`） | **保头**（`truncateHead`） | `[Truncated: showing X of Y lines]` 或指向 `offset`（`:150-175`） |
| `bash`（`tools/bash.ts:19`） | **保尾**（`truncateTail`） | 完整输出存临时文件，附 `[Showing last … Full output: <path>]`（`:234/320-330`） |
| `grep`（`tools/grep.ts:209`） | 保头 + 每行截 500 字符 | `Some lines truncated to 500 chars`（`:299`） |
| `find` / `ls` | 保头 | `find.ts:147`、`ls.ts:141` |

**为什么 read 保头而 bash 保尾**：读文件时开头是定义与 import（结构信息）；执行命令时报错在尾部（诊断信息）。**按语义选择保留侧，而不是一刀切**——这是很实用的细节。

### 5.8 图片处理

- **降采样**：`resizeImage()`（`src/utils/image-resize.ts:85`）→ `resizeImageInProcess()`（`image-resize-core.ts:59`），用 Photon（Rust/WASM）
- **默认上限**（`image-resize-core.ts:24-29`）：**2000 × 2000**、`maxBytes = 4.5MB`（base64）、`jpegQuality = 80`
- **降级梯子**（`image-resize-core.ts:95-106`）：先等比缩到 2000×2000 → PNG/JPEG 取较小者 → 仍超则降 JPEG 质量 **80 → 85 → 70 → 55 → 40** → 最后逐步缩到 1×1；放不下返回 null，工具回退为文本占位（`image-process.ts:91` `[Image omitted: could not be resized…]`）
- EXIF 方向修正（`exif-orientation.ts`）；dimension note 注入 prompt（`image-process.ts:98`）
- **数量限制**：coding-agent 自身**无显式上限**；但 CHANGELOG 记录了各提供商硬限制（Anthropic 100 图 / 5MB / 8000px，OpenAI 500，Gemini ~2500，Mistral 8 等，`packages/ai/CHANGELOG.md:1974`）

### 5.9 分支摘要：解决「上下文不是线性增长」

`/tree` 在会话树里跳到另一分支时，原分支的工作若不保留会丢失（`branch-summarization.ts:1-6`）。

- `collectEntriesForBranchSummary()`（`:108`）从旧叶子回溯到与目标的**最近公共祖先**（common ancestor，`:118-129`），只摘要「被离开的分支」
- `prepareBranchEntries()`（`:195`）同样「newest-first 预算内」收集，且对 compaction / branch_summary 摘要条目放宽到预算的 **90%**（`:233`）
- **与 compaction 共用**：`serializeConversation()`、`SUMMARIZATION_SYSTEM_PROMPT`、`estimateTokens()`、`extractFileOpsFromMessage()` / `computeFileLists()` / `formatFileOperations()`、`completeSummarization()`
- **差异**：分支摘要**不切分 recent tokens**、不写 `firstKeptEntryId`，只挂 `BranchSummaryEntry`（带 `fromId`）在导航点

**累计文件追踪**（compaction 与 branch 共有）：生成摘要时会从「被摘要消息里的工具调用」+「上一份摘要 `details` 里的文件清单」双向提取文件操作（`readFiles` / `modifiedFiles`），**跨多次压缩累积**。被压缩掉的操作记录以清单形式幸存于摘要尾部：

```
<read-files>
path/to/file1.ts
</read-files>

<modified-files>
path/to/changed.ts
</modified-files>
```

### 5.10 扩展点

`session_before_compact`（`extensions/types.ts:594`）：扩展可 `return { cancel: true }` 取消，或返回 `{ compaction: { summary, firstKeptEntryId, tokensBefore, usage?, details? } }` **完全接管压缩**（`:1171-1174`）。事件携带 `preparation`（`messagesToSummarize` / `turnPrefixMessages` / `previousSummary` / `fileOps`）、`reason`、`willRetry`、`signal`，并用 `serializeConversation(convertToLlm(...))` 把消息转文本给自定义模型。

另有 `session_compact_failed`（`:618`）与 `session_before_tree`（`:656`）。

★ **文档与源码均未给出任何实测 token 节省数字**——没有 benchmark、没有「节省 X%」的常量或注释。`tokensBefore` 与 `estimatedTokensAfter` 会被记录进 `CompactionResult`（`compaction.ts:88`、`agent-session.ts:2383/2404`），但仅用于事件/统计，没有聚合报表。

---

## 6. 横向对比

### 6.1 阈值与触发

| 维度 | Claude Code v2.1.88 | Codex (codex-rs) | Pi 0.85.1 |
|---|---|---|---|
| **阈值表达** | 绝对缓冲：`effectiveWindow − 13_000` | 百分比：`context_window × 9/10` | 响应预留：`contextWindow − 16_384` |
| **200K 窗口下的实际触发点** | **≈167K（83.5%）** | 180K（90%） | 183.6K（91.8%） |
| **硬上限** | `effectiveWindow − 3_000`（阻塞水位） | `context_window × 95%` | 无独立硬顶 |
| **有效窗口扣减** | 扣 `min(maxOutput, 20_000)` | 不扣（95% 已含余量） | 不扣 |
| **pre-turn** | ✅（每轮前） | ✅ `run_pre_sampling_compact` | ✅（新 prompt 提交前） |
| **mid-turn** | ✅（autocompact 在循环中复查） | ✅（`needs_follow_up` + 超阈值） | ✅（每批工具结果落定后） |
| **模型切换触发** | ❌ | ✅ CompHashChanged / ModelDownshift | ❌ |
| **被动补救** | ✅ reactiveCompact（**桩**） | ✅ ContextWindowExceeded 重试 | ✅ overflow 三态检测 + 重试一次 |
| **手动** | `/compact [指令]`、`/rewind` | `/compact` | `/compact [指令]` |
| **熔断** | ✅ 连续失败 3 次 | ❌（显式错误上抛用户） | ✅ 重试仅 1 次 |
| **可配阈值** | env ×2（窗口 clamp / 百分比） | 4 项 config | settings.json（reserve / keep） |

### 6.2 压缩保留策略

| 维度 | Claude Code | Codex | Pi |
|---|---|---|---|
| **摘要粒度** | 9 段结构化 | 4 项 handoff | 6 段结构化 |
| **摘要生成者** | fork 子 agent（复用主缓存） | 主模型 / 服务端 V2 | 主模型或自定义扩展 |
| **近期原文保留** | `messagesToKeep` + 重读 5 个文件 | 用户消息 ≤20k token（激进） | 最近 20k token 全原文（保守） |
| **摘要注入身份** | 重开窗口时携带 | user 消息 + 固定前缀 | user 消息置于历史最前 |
| **防摘要套摘要** | 重开窗口天然规避 | `is_summary_message` 排除 | 增量更新单一摘要 |
| **环境上下文** | 磁盘重注入（CLAUDE.md / memory / skills） | WorldState 下轮全量重注入 | system prompt 每轮原样重发 |
| **权限状态** | 重新预检 | `CompactPermissionsState` 跨压缩保留 | N/A |
| **图片** | `stripImagesFromMessages` → `[image]` 占位 | 预算内保留，超大则截断 | 保留，压缩时按 4800 字符折算 |
| **文件清单** | 重读最近 5 个 | 丢弃（靠 WorldState） | **累计追加到摘要尾部** |
| **全量历史** | transcript + 服务端/本地 | JSONL rollout + `Compacted` 检查点回放 | append-only JSONL 树，压缩=投影 |
| **失败即拒** | 熔断 3 次 | 显式报错 | length 截断的摘要拒绝落盘 |

### 6.3 摘要 prompt 对照

三家的 prompt 都极短（而**不是在 prompt 里堆砌格式要求**），但**结构约束的强度差异很大**：

| | Codex | Pi | Claude Code |
|---|---|---|---|
| **长度** | ~5 行 | ~30 行（含完整模板） | ~40 行 + `<analysis>` 草稿段 |
| **格式约束** | 「Be concise, structured」（**弱**） | 「Use this EXACT format」+ 逐 section 填法（**强**） | 9 个 section + 逐条说明 + 示例输出（**最强**） |
| **思维草稿** | 无 | 无 | ✅ `<analysis>` 块，之后被 `formatCompactSummary` 剥离 |
| **强调保留** | 关键数据/示例/参考 | 文件路径、函数名、错误信息 | 最近对话 **verbatim 引用** |
| **用户消息处理** | 由本地代码单独保留 ≤20k | 摘要里体现 | 摘要里「List ALL user messages」 |

**一个有意思的规律**：Codex 把「保留用户消息」交给**代码**（确定性强、开销可控），Claude Code 和 Pi 交给**模型**（更灵活但不可靠）。Codex 的做法在有严格预算约束时更稳——这也解释了它为什么敢把摘要 prompt 写得那么短。

### 6.4 上下文压力的分层治理对比

| 干预层 | Claude Code | Codex | Pi |
|---|---|---|---|
| **L1 源头治理** | FileRead 抛错引导分段（25k tok / 2000 行）；Bash 超 30k 字符落盘 + 2KB 预览 | 中间截断（保头尾）；exec 10k tok 上限；1MiB 硬顶；序列化 +20% 余量 | read 保头 / bash 保尾（2000 行 / 50KB）；grep 单行 500 字符；图片降采样 2000² |
| **L2 传输层** | ✅ apiMicrocompact（`cache_edits`）+ cached microcompact | ❌（`BodyAfterPrefix` 属准 L2，但通过作用域而非改请求体实现） | ❌ |
| **L3 轻量裁剪** | ✅ microCompact（清旧工具结果内容） | ❌ | ❌ |
| **L3 重量摘要** | ✅ autoCompact（fork 子 agent） | ✅ compact.rs 本地 / 远程 V2 | ✅ compaction.ts |
| **L3 兜底截断** | 逐条删最旧（未在本构建实现） | ✅ 从最旧项删以保缓存前缀 | ✅ overflow 重试一次 |

★ **Pi 是唯一没有 L2 和 L3 轻量层的**，它用「L1 做得足够狠」来替代。这是一个值得注意的架构分歧：**要么在源头掐死，要么在窗口层狠压，中间层的性价比取决于你的历史是否可重建**。

---

## 7. 提炼：七个可复用的工程模式

### 模式 1：全量历史落盘，压缩只是「视图」

三家的压缩**没有一家真的删除数据**。Pi 的会话是 append-only JSONL 树，`CompactionEntry` 只是树上的一个节点，「当前窗口」是对树的投影；Codex 写 `Compacted` 检查点后 resume 从检查点回放；Claude Code 的 transcript 保留在服务端/本地。

> **落地要求**：设计中必须有一个「原始记录」层（数据库表 / JSONL / 快照），压缩产物是**另一份**数据，不是对原始数据的覆盖。

### 模式 2：分层降级，永远有更便宜的一级

```
源头截断 → 轻量裁剪 → 廉价重建 → 重量摘要 → 逐条删最旧
```

Claude Code 是这个模式的教科书实现（6 层）。关键是**每一级都必须自证有效**才能阻止降级——`sessionMemoryCompact` 压缩后若仍超阈值就放弃、回退重量摘要（`sessionMemoryCompact.ts:605-614`）。

### 模式 3：可重建的状态永不进摘要

分类清单（三家的共识）：

| 类型 | 处理 |
|---|---|
| 磁盘上有的（项目记忆、plan 文件、skills 正文） | 压缩后从磁盘**重新注入** |
| 能重算的（system prompt、工具定义、权限前缀） | 压缩后**重新生成** |
| 需要追溯的（用户消息、文件读写清单） | **代码单独保留**，不交给摘要 |
| 只有模型知道的（推理过程、工具输出） | **摘要或丢弃** |

### 模式 4：真实 usage 锚定，估算只补差

三家统一做法：**取最近一次 API 响应的真实 usage 作为基准，之后的新增消息才用启发式估算**。未产生 usage 时宁可显示「未知」（Pi 的 `tokens: null`）。

> **反模式**：全程用 `len(text)/4` 估算阈值。误差会累积到让阈值判断完全失真。

### 模式 5：截断必须保留「有信息的那一端」

没有一家用「只保头」作为唯一策略：

| 内容类型 | 保留侧 | 理由 |
|---|---|---|
| 文件内容 | 保头 | 开头是定义与 import |
| 命令执行 | 保尾 | 报错在尾部 |
| 通用工具输出 | 保头尾 | 上下文线索在头、结论在尾 |

且**截断后必须给模型一个明确的标记**（`…N tokens truncated…` / `[Truncated: showing X of Y]`），以及**取回全量数据的路径**（落盘文件路径 / `offset` 参数）。

### 模式 6：压缩与提示缓存必须一起设计

矛盾的本质：cache 命中要求前缀字节稳定，压缩必然改写历史。三家的手法：
- 只裁剪尾部增量，不动已缓存前缀（Codex `BodyAfterPrefix`）
- 兜底删除时从最旧项删起，保护前缀（Codex `compact.rs:308-317`）
- 一次性请求标 `cacheRetention: none`，不写缓存（Pi）
- 压缩成功后**不清那些重注入成本高于收益的缓存**（Claude Code 刻意不重置 skills 缓存）

### 模式 7：质量门 + 熔断

- **质量门**：内容被截断的摘要（`stop_reason = length`）拒绝落盘（Pi `getSummarizationFailure`）
- **熔断**：连续失败 N 次停止重试（Claude Code `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`，源于每天 25 万次 API 调用的生产事故）
- **单次重试上限**：overflow 恢复只重试一次（Pi `_overflowRecoveryAttempted`）
- **压缩的事务性**：只有全部成功才替换历史，失败则原历史完好（Codex `replace_compacted_history`）

---

## 8. 闭环：本项目改哪里、怎么验

> 这一章是**唯一需要动手的章节**。它把 §0.4 的两个问题、§3–7 的机制，落到「改哪个函数、验收标准是什么」。
> 与 `docs/LONG_CONTEXT_MANAGEMENT_RESEARCH.md` §6「评估上下文的升级方案（修复 3 v2）」的关系：那份文档给的是方向（三层结构），本章给的是**可执行的改动清单 + 验收标准**，并修正了它对现状的误判。

### 8.1 两个问题，两个方向

先把 §0.4 的结论落成可执行的形式：

| # | 位置 | 问题 | 方向 | 严重度 |
|---|---|---|---|---|
| ① | `evaluate_answer` — `ai_interviewer/api/interviewer.py:148`（context 在 `:165-167`） | 评分看不到追问链，每题孤立评分 | **加**（补历史） | **高**（质量问题） |
| ② | `conclude_interview` — `api/interviewer.py:423`（context 在 `:439-442`） | 无上限拼接全部 QA，含追问轮次 | **限**（加预算） | 中（容量风险） |
| ③ | 全项目 | 用字符数而非 token 计量；且中文系数用错方向 | **换**（装计量） | 中（基础件） |
| ④ | 全项目 | 无滚动摘要 | **加**（可选） | 低（①②③稳了再说） |

**为什么不是一上来就做摘要**：最痛的是 ①，而 ① **不是容量问题，是信息缺失**。第 3–7 章讲的所有压缩/摘要技术**都治不了 ①**——你没法「摘要」一段从未被送进模型的内容。所以顺序必须是 **① → ③ → ② → ④**。

这与初版的建议（先做源头治理）不同。初版之所以排错，是因为它基于一个错误的现状描述（见 §0.6）。

### 8.2 改动 ①：给评分调用补上追问链

**改什么**：`evaluate_answer` 增加一个参数，接收**本题追问链**，拼进 `context`。

```python
# api/interviewer.py:148 evaluate_answer
# 现在（:165-167）
context = f"问题：{question}\n回答：{answer}\n"
if resume_content:
    context += f"\n简历内容（参考）：\n{resume_content[:1000]}"

# 改成
context = ""
if question_chain:                      # 新增：本题从首问起的追问链
    context += f"本题追问链（按时间顺序）：\n{question_chain}\n\n"
context += f"当前问题：{question}\n当前回答：{answer}\n"
if resume_content:
    context += f"\n简历内容（参考）：\n{resume_content[:1000]}"
```

**为什么这次可以放心加**：面试对话有 coding agent 没有的天然优势——**「题」是显式语义边界**。Codex 要用 `findCutPoint`（`compact.rs`）从最新往回累加 token 猜切点，Pi 要用 `findCutPoint`（`compaction.ts:403`）做同样的事；而本项目**不需要猜**：本题的追问链就是一个 `Interview Turn` 的追问序列，起点已知。

**数据从哪来**：`session.history` 里已经有带 `is_followup` 标记的 `Business Message`（`services/interview_session.py:67-68`），`QuestionAnswer.is_followup` 也在（`:39`）。只需在 `interview_service.py` 调用 `evaluate_answer` 的地方（`:304-307`、`:523-526`）把当前题的追问链传进去。**不需要改数据库 schema，也不需要改 `BranchSnapshot`。**

**注意边界**：只带**本题**的追问链，不带整场历史。整场历史交给 §8.5 的摘要，这是分工。

### 8.3 改动 ②：给总结调用加预算

**改什么**：`conclude_interview` 的 `"\n\n".join(qa_summary)`（`api/interviewer.py:442`）前面加一层预算控制。

```python
# api/interviewer.py:434-442 现在：无任何上限
all_qa = session.project_qa_list + session.technical_qa_list
qa_summary = [f"问题：{qa.question}\n回答：{qa.answer}\n得分：{qa.score}" for qa in all_qa]
context = "面试会话总结：\n"
context += "\n\n详细问答记录：\n" + "\n\n".join(qa_summary)
```

**降级顺序**（借鉴 §4.3 Codex「代码保留、摘要兜底」与 §5.4 Pi 的预算切分）：

1. 全部 QA 都在预算内 → 原样拼接（当前行为）。
2. 超预算 → **追问轮次的回答折叠为要点**（保留首问与最后一轮追问的原文）。
3. 仍超预算 → **按 token 预算从最旧开始丢回答正文，只留「问题 + 得分 + 评语」**——即回落到 `LONG_CONTEXT_MANAGEMENT_RESEARCH.md` 已设计的「题目/得分/评语结构化表格」。

第 3 步就是三家共用的模式：**保留结构化的结论，丢弃过程性的正文**。

### 8.4 改动 ③：装 token 计量（基础件）

①②的「预算」需要一个计量单位。按 §0.5 的实测结论：

```python
# 建议放在 ai_interviewer/core/ 下，作为一个纯函数模块（可单测）
def estimate_tokens(text: str) -> int:
    cjk = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
    return round(cjk * 1.0 + (len(text) - cjk) * 0.35)
```

**同时补真值锚定**（§0.5 末、§5.6、§7 模式 4）：`invoke_observable` 已经拿到了响应，DeepSeek 返回的 `usage.prompt_tokens` 是**真实值**。把它回写到会话状态，就得到三家的「真实 usage 锚定 + 估算补差」：

```
本轮真实 prompt_tokens（服务端给的）
  + 之后新增内容的 estimate_tokens()（本地估的）
  = 下一次判断用的值
```

**顺带收益**：`services/observability/provider_usage.py` 已经在采集 usage，这条链路是现成的，不需要新建管道。

### 8.5 改动 ④（可选）：滚动结构化摘要

只在 ①②③ 稳定后再做。按面试场景改写 §5.4 的 Pi 模板：

```
## 已考察能力
[题型 / 维度 / 得分区间]

## 暴露的弱项
[含已追问过的点，避免重复追问——这是摘要最实际的用途]

## 候选人画像
[表达清晰度 / 技术深度 / 真实性信号]

## 待深挖的线索
[有价值的追问方向]
```

两条硬约束：

1. **必须增量更新**（Pi 的 `<previous-summary>` 模式）：新摘要 = 旧摘要 + 本题 QA 概要，**维护单一滚动摘要**，不堆叠多份。理由见 §5.4——每摘要一次都是有损压缩，堆叠会加速衰减。
2. **存储位置**：作为带标记的特殊消息追加进 `session.history`（如 `{"role":"system","type":"rolling_summary"}`）。这样随 durable 快照走、分支重建（`services/branch_reconstruction.py`）自然恢复、**零 `BranchSnapshot` schema 变更**。

**先别急着上 LLM 摘要**：可以先用规则模板拼装（题目 + 得分 + 评语），成本为零。摘要质量不足再升级为 LLM 增量摘要——这与三家「先廉价、贵了才升级」的降级哲学一致（§3.6 的 `sessionMemoryCompact` 就是这个思路）。

### 8.6 验收：怎么证明改对了

本项目的约定是测试用例登记到 `tests/docs/test-cases.md`（见根 `AGENTS.md`「测试资产管理」）。建议的验收项：

| # | 验收项 | 怎么验 | 对应机制 |
|---|---|---|---|
| 1 | 追问链进入评分 prompt | 单测：构造 2 轮追问的会话，断言 `evaluate_answer` 收到的 `context` 里含首问文本 | 改动 ① |
| 2 | 总结预算生效 | 单测：构造超预算 QA 列表，断言 `context` 的 `estimate_tokens()` 在预算内，且「问题 + 得分」全部保留 | 改动 ②、§4.3 |
| 3 | 中文估算不低 | 单测：`estimate_tokens("我在项目中使用 Redis")` 与 tiktoken 实测值比值 ≥ 0.9 | 改动 ③、§0.5 |
| 4 | 真值锚定生效 | 断言第二次调用用的是 `usage.prompt_tokens` + 增量估算，不是纯字符估算 | 改动 ③、§7 模式 4 |
| 5 | 不改分支语义 | 现有 `tests/test_branch_snapshot_reconstruction.py`、`tests/test_durable_turn_processor.py` 全绿 | 回归 |

第 5 项特别重要：`Branch Delta`、`Fork Point`、`Owning Branch` 这套语义（见 `CONTEXT.md`）不能被这次改动破坏。**这是本项目的不可压缩层**——对应 §7 模式 3「能重建的状态不进摘要」。改动 ① 只读 `session.history`，不写，所以理论上安全；但要用测试锁住。

**验证的方法论**（来自本次调研的教训）：审计本项目的 prompt 组装时，**不要相信任何文档里的"现状"描述**，包括本文档。直接 grep 全部 `context = f"` 与 `context += f"` 组装点，逐个读。这次就是这么发现初版写错的。

### 8.7 明确不建议照搬的部分

| 机制 | 为什么不适用 |
|---|---|
| Codex 的 mid-turn 压缩 | 本项目每轮评估是**独立短调用**，不存在「一个回合里工具循环跑很久」的形态 |
| Claude Code 的 6 层体系 | 其复杂度来自 tool-heavy agent 的形态（工具输出占大头）；面试对话的工具输出几乎为零 |
| 分支摘要（Pi `/tree`） | 本项目已有 durable 分支快照机制，语义不同 |
| L2 传输层（apiMicrocompact） | 依赖 Anthropic API 原生 context editing，DeepSeek 无此能力 |
| 远程压缩（Codex V2） | 需要服务端配合，自建成本远高于收益 |
| 抽象 tokenizer | chars/4 + 真实 usage 锚定已足够；引入 tiktoken 会增加依赖且对中文未必更准 |

---

## 9. 附录：数值常量总表与复核方法

### 9.1 触发与阈值

| 系统 | 常量 | 值 | 位置 |
|---|---|---|---|
| CC | `AUTOCOMPACT_BUFFER_TOKENS` | 13 000 | `services/compact/autoCompact.ts:62` |
| CC | `WARNING_THRESHOLD_BUFFER_TOKENS` | 20 000 | `:63` |
| CC | `ERROR_THRESHOLD_BUFFER_TOKENS` | 20 000 | `:64` |
| CC | `MANUAL_COMPACT_BUFFER_TOKENS` | 3 000 | `:65` |
| CC | `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES` | 3 | `:70` |
| CC | `MAX_OUTPUT_TOKENS_FOR_SUMMARY` | 20 000 | `:30` |
| CC | `MODEL_CONTEXT_WINDOW_DEFAULT` | 200 000 | `utils/context.ts:9` |
| Codex | 自动压缩比例 | 90%（`× 9/10`） | `protocol/src/openai_models.rs:521-533` |
| Codex | `effective_context_window_percent` | 95 | `openai_models.rs:389-391` |
| Codex | fallback buffer | 16 384（models.json） | `core/src/session/context_window.rs:97-102` |
| Pi | `reserveTokens` | 16 384 | `compaction.ts:134` / `settings-manager.ts:19` |
| Pi | `keepRecentTokens` | 20 000 | `compaction.ts:135` / `settings-manager.ts:20` |
| Pi | contextWindow 兜底 | 128 000 | `provider-composer.ts:160` |

### 9.2 摘要与保留预算

| 系统 | 常量 | 值 | 位置 |
|---|---|---|---|
| CC | `POST_COMPACT_MAX_FILES_TO_RESTORE` | 5 | `compact.ts:122` |
| CC | `POST_COMPACT_TOKEN_BUDGET` | 50 000 | `:123` |
| CC | `POST_COMPACT_MAX_TOKENS_PER_FILE` | 5 000 | `:124` |
| CC | `POST_COMPACT_MAX_TOKENS_PER_SKILL` | 5 000 | `:126` |
| CC | `POST_COMPACT_SKILLS_TOKEN_BUDGET` | 25 000 | `:127` |
| CC | 摘要 section 数 | 9 | `compact/prompt.ts:66-77` |
| CC | SessionMemory 后台节流 | 10 000 / 5 000 / 3 次 | `SessionMemory/sessionMemoryUtils.ts:32-36` |
| CC | SessionMemory 压缩保留 | min 10 000 / max 40 000 | `sessionMemoryCompact.ts:57-61` |
| Codex | `COMPACT_USER_MESSAGE_MAX_TOKENS` | 20 000 | `core/src/compact.rs:61` |
| Codex | `RETAINED_MESSAGE_TOKEN_BUDGET` | 64 000 | `core/src/compact_remote_v2.rs:73` |
| Codex | `MAX_RETAINED_AGENT_MESSAGE_TOKENS` | 10 000 | `:74` |
| Pi | `TOOL_RESULT_MAX_CHARS`（摘要序列化） | 2 000 | `compaction/utils.ts:89` |
| Pi | 主摘要 maxTokens | `min(0.8 × reserveTokens, model.max)` | `compaction.ts:672` |
| Pi | split-turn 前缀 maxTokens | `0.5 × reserveTokens` | `compaction.ts:983` |
| Pi | 分支摘要 maxTokens | `min(4096, model.max)` | `branch-summarization.ts:345` |
| Pi | `ESTIMATED_IMAGE_CHARS` | 4 800 | `compaction.ts:244` |

### 9.3 工具输出与图片

| 系统 | 常量 | 值 | 位置 |
|---|---|---|---|
| CC | `DEFAULT_MAX_RESULT_SIZE_CHARS` | 50 000 | `constants/toolLimits.ts:13` |
| CC | `MAX_TOOL_RESULT_TOKENS` → BYTES | 100 000 → 400 000 | `:22-33` |
| CC | `MAX_TOOL_RESULTS_PER_MESSAGE_CHARS` | 200 000 | `:49` |
| CC | FileRead `DEFAULT_MAX_OUTPUT_TOKENS` | 25 000 | `tools/FileReadTool/limits.ts:18` |
| CC | FileRead `MAX_OUTPUT_SIZE` | 0.25 MB = 262 144 B | `utils/file.ts:48` |
| CC | FileRead `MAX_LINES_TO_READ` | 2 000 | `FileReadTool/prompt.ts:10` |
| CC | Bash `maxResultSizeChars` | 30 000 | `tools/BashTool/BashTool.tsx:424` |
| CC | 大结果预览字节 | 2 000 | `utils/toolResultStorage.ts:109` |
| CC | 镜像 token 折算 | 2 000 | `services/tokenEstimation.ts:411` |
| Codex | exec `DEFAULT_MAX_OUTPUT_TOKENS` | 10 000 | `unified_exec/mod.rs:79` |
| Codex | exec 硬上限 | 1 MiB (≈262 144 tok) | `:80-81` |
| Codex | 序列化余量 | ×1.2 | `utils/output-truncation/src/lib.rs:16-18` |
| Pi | `DEFAULT_MAX_LINES` / `DEFAULT_MAX_BYTES` | 2 000 / 50 KB | `core/tools/truncate.ts:11-12` |
| Pi | `GREP_MAX_LINE_LENGTH` | 500 | `:13` |
| Pi | 图片 resize 上限 | 2000×2000 / 4.5MB / q80 | `utils/image-resize-core.ts:24-29` |

### 9.4 复核方法

```bash
# Codex（Rust）
cd <codex-repo>/codex-rs
sed -n '515,535p' protocol/src/openai_models.rs          # 90% 阈值
sed -n '385,395p' protocol/src/openai_models.rs          # 95% 硬顶
cat prompts/templates/compact/prompt.md                  # 摘要 prompt 原文

# Pi（TypeScript）
cd <pi-repo>/packages/coding-agent
sed -n '230,240p' src/core/compaction/compaction.ts      # shouldCompact
sed -n '467,540p' src/core/compaction/compaction.ts      # 摘要 + 增量更新 prompt
sed -n '1,20p' src/core/tools/truncate.ts                # 工具输出截断常量

# Claude Code（反编译 TS）
cd <cc-source>/03-claude-code-runnable/src
sed -n '30,95p' services/compact/autoCompact.ts          # 阈值全套 + 熔断注释
sed -n '60,90p' services/compact/prompt.ts               # 9 段摘要 prompt
sed -n '30,80p' services/compact/postCompactCleanup.ts   # 压缩后清理清单
sed -n '10,55p' constants/toolLimits.ts                  # 工具结果限额
```

**局限声明**：
1. Claude Code 为反编译还原源码，`reactiveCompact` / `snipCompact` / `contextCollapse` / `cachedMicrocompact` 在本构建中是桩，其真实实现不可见；行号基于该还原版本，与官方内部代码不一一对应。
2. Codex 远程压缩的服务端实现不在开源仓库内，仅能从客户端协议与 `ResponseItem::Compaction { encrypted_content }` 推断。
3. Pi 的源码仓库为 `earendil-works/pi`（0.85.1），官方文档中的链接指向旧组织名 `badlogic/pi-mono`；两者为同一项目的组织迁移。

---

## 10. 一句话总结

**三家解决长上下文的方式，本质上是同一件事的三种表述：「把历史变成可重建的东西，把当前窗口变成它的投影」。** 它们从不试图「装下更多」，而是持续回答同一个问题——**「此刻模型真正需要知道什么？」** 而那些能被重新读出来的（文件、记忆、工具状态）永远不进窗口；能被压缩成结构的（对话历史）用固定格式滚动摘要；只有既不能重建、又不能损失的（用户原话、报错、文件路径）才被允许挤占预算。

工程上的启示有三条：**源头治理优先于窗口压缩**；**真实用量优先于估算**；**任何自动化都必须有质量门和熔断**。

**回到本项目**，这三条里只有第二条立刻用得上（§8.4 的真值锚定）。因为本项目眼下最痛的 `evaluate_answer`（`api/interviewer.py:148`）问题**根本不是压缩问题**——它是**该给的信息没给**。第 3–7 章那一整套压缩技术，是为「窗口塞满了」准备的；而本项目的窗口**远没塞满，只是内容不完整**。

所以这份报告最该被记住的一句是：

> **先确认问题属于哪一类。「信息缺失」要用加法，「容量不足」才用压缩。搞反了，再精妙的技术也是白费。**
