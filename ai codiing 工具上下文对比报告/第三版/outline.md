# 总大纲：AI Coding Agent 上下文管理（第三版）

- 依据：`spec.md` 第 4–6 节、`tutorial/assets/js/toc.js`、`tutorial/CONVENTIONS.md`、`research/` 8 份事实卡片与 8 份 source-map。
- 章节总数：60（第 0 章 1 + 入门 7 + 主线 16 + 进阶 5 + 源码 26 + 附录 5）。
- 交互演示统一放在 `tutorial/assets/js/demos/`，文件名在本文件中固定；图示统一用 `CONVENTIONS.md` 第 11 节的 `.fig` + 内联 SVG。
- 可信度与来源规则见 `spec.md` 第 8 节；Claude Code 结论一律带来源类型标签。

---

## 一、第 0 章

| 章节 ID | 标题 | 学习目标（1 句，动词开头） | 要点（3–5 条） | 交互演示 / 图示 | 预计篇幅（字） |
|---|---|---|---|---|---|
| intro-00 | 第 0 章 · 导读 | 用一张地图定位自己在 L1–L5 的哪一级，并选一条阅读路线。 | ①教程地图与四条阅读路线；②L1–L5 能力分级与自测；③版本表与核实日期；④Claude Code 非官方源码声明；⑤可信度标签与【待核实】的含义 | SVG 图：教程地图（四部分 + 附录）；无交互 | 2000 |

## 二、第一部分 入门（L1–L2，Head First 风格）

| 章节 ID | 标题 | 学习目标（1 句，动词开头） | 要点（3–5 条） | 交互演示 / 图示 | 预计篇幅（字） |
|---|---|---|---|---|---|
| intro-01 | 上下文窗口是什么 | 用自己的话解释 token、上下文窗口与输出预留的关系。 | ①token 是容量与计价单位，不是字数；②窗口由输入与输出共享；③输出预留为什么必须留；④超窗时会发生什么；⑤“装得下”只是第一关 | `demos/context-budget.js`（窗口组成拖拽器，07 号票）；SVG 窗口占用条形图 | 3000 |
| intro-02 | 一次请求里装了什么 | 拆开一次真实请求，指出系统提示、工具、规则、历史各占哪一块。 | ①请求的固定骨架；②工具定义也占大量 token；③规则文件从哪里来；④环境与权限说明的位置；⑤拼接顺序决定缓存 | SVG 请求分层图；表格：五类内容的来源与体积 | 3000 |
| intro-03 | Agent 循环中上下文如何增长 | 画出一次任务里上下文增长的曲线，并指出三个主要增长源。 | ①每轮追加 assistant 与 tool result；②工具输出是最大增量；③循环没有天然终点；④增长曲线与阈值线；⑤什么时候必须减量 | SVG 折线图 + 轮次时间线 | 2800 |
| intro-04 | 窗口装得下，不等于模型用得好 | 解释 context rot 与 lost in the middle，并判断哪些信息会“被看见却没被用”。 | ①有效上下文不等于名义窗口；②中间位置的信息召回下降；③噪声与冲突指令的干扰；④长上下文下的任务退化；⑤少而准优于多而全 | SVG 双图：位置—召回曲线、噪声干扰示意 | 3000 |
| intro-05 | Prompt cache 与成本 | 说明缓存命中的条件，并算出一次前缀变更带来的成本差。 | ①前缀缓存的工作原理；②命中要求字节级前缀一致；③缓存读写的计价差异；④哪些操作会让缓存失效；⑤把易变内容放到尾部 | `demos/cache-hit.js`（Prompt cache 命中演示，10 号票）；SVG 前缀分块与断点图 | 3200 |
| intro-06 | 用户侧怎么管理上下文：决策流程图 | 选择正确的用户动作：/clear、/compact、子代理或新会话。 | ①四种用户动作的代价；②什么时候不该压缩；③任务切换与会话切换；④规则文件的维护；⑤一张能独立看懂的决策图 | SVG 决策流程图（主图，图注复述结论） | 3000 |
| intro-07 | 总流程图 | 画出一次请求从组装到压缩的全链路，并指出 16 类能力的落点。 | ①组装→计量→减量→隔离→质量五段；②16 类在链路中的位置；③哪些环节调模型、哪些不调；④失败恢复的回边；⑤与 main-01…16 的对应 | SVG 总流程图（640 宽，分泳道） | 2800 |

## 三、第二部分 主线（16 类，L2→L3）

> 每章固定五段：① Codex 主线讲解（无能力时写明并换主例）② 7 个工具弹窗 ③ 8 工具对比表 ④ 设计取舍 ⑤ 3 道小测验。下表不再重复这五段。
> 篇幅口径（2026-10-19 作者确认）：主线单章 8,000–13,000 字，以 `main-08` 实测 12,911 字为上限参照。下表数值为写作目标，超出时先删重复解释。

| 章节 ID | 标题 | 学习目标（1 句，动词开头） | 要点（3–5 条） | 交互演示 / 图示 | 预计篇幅（字） |
|---|---|---|---|---|---|
| main-01 | 请求组装：系统提示词与工具定义 | 画出一次请求的四块拼装，并说明工具定义为什么值得单独优化。 | ①Codex 的 Prompt 四块与 incremental_tools；②系统提示的静态/动态分段；③工具定义与 MCP 的位置；④环境与权限说明的注入方式；⑤拼接顺序如何影响缓存 | SVG 请求分层图；8 工具对比表；无交互 | 9,500 |
| main-02 | 规则文件的发现与合并 | 推导给定目录结构下最终生效的规则文本与截断结果。 | ①向上查找与项目根标记；②多级拼接而非覆盖；③include 深度与循环；④体积上限与截断顺序；⑤规则差分注入 | SVG 目录树 + 合并顺序图 | 9,500 |
| main-03 | 按需加载与渐进披露 | 判断一种能力该预加载还是按需拉取，并说出各自代价。 | ①Skills 两段式；②MCP 延迟加载的三种实现；③Code Mode 与工具目录；④@ 引用的两种语义；⑤按需加载的失败模式 | SVG 时序图：先目录、后正文 | 9,500 |
| main-04 | 动态注入：提醒、状态与增量 | 区分“改系统提示”与“追加消息”两种注入，并预测缓存后果。 | ①system reminder 的位置；②todo/plan 状态注入；③日期与环境变化；④只注入变化部分的三种实现；⑤注入顺序与去重 | SVG 时间线：固定前缀 + 尾部增量 | 9,900 |
| main-05 | Token 计量与可视化 | 估算同一会话在三种口径下的占用，并解释差异来源。 | ①服务端 usage + 本地增量；②chars/4 的误差边界；③输出预留与有效窗口；④/context 的分类口径；⑤可切换窗口与阈值联动 | SVG 四段占用条；对照 intro-01 拖拽器的静态截图 | 9,500 |
| main-06 | 单次工具输出控制 | 选择一种工具输出的截断、落盘或分页策略。 | ①头/尾/中间三种截断；②落盘 + 指针 + 回读；③按消息聚合预算；④多模态输出的单独计价；⑤阈值该按字节还是 token | SVG 截断三态图（保留/丢弃/指针） | 9,100 |
| main-07 | 历史裁剪：不调用模型的减量 | 分辨裁剪与压缩的边界，并设计一条零模型成本的减量链。 | ①裁剪只改投影、不改原文；②按轮龄与按预算两种策略；③superseded 与 useless 结果；④裁剪的缓存守卫；⑤回滚与一致性 | SVG 前后对照：原文 vs 模型可见投影 | 9,500 |
| main-08 | 压缩：把历史换成摘要 | 预测给定阈值、保留量与预留空间下的切点，并解释保留与丢弃的内容。 | ①触发时机的三到六条路径；②切点必须落在合法边界；③工具调用与结果成对；④单回合过长的拆分；⑤摘要模板、多次压缩累积与压缩后重附 | `demos/compact-sim.js`、`demos/tool-pairing.js`（08 号票）；SVG 切点示意图 | 12,900 |
| main-09 | 多模态上下文 | 选择图片或 PDF 的保留、移出或转文字方案，并估算其 token。 | ①各家图片计价差异；②请求体字节预算与滞回；③历史转图片；④附件转文字；⑤压缩前剥图 | SVG 图片生命周期图（进入→保留→驱逐→占位） | 9,100 |
| main-10 | 子代理隔离 | 设计一次子代理委派，说明父会话最终多出哪些 token。 | ①独立上下文与工具池；②只读/计划子代理的裁剪；③结构化返回 vs 自由文本；④并行与 worktree 隔离；⑤深度与并发上限 | `demos/subagent-isolation.js`（13 号票）；SVG 父子上下文对照 | 9,900 |
| main-11 | 会话时间线：恢复、分叉与回退 | 还原一份会话日志对应的模型上下文，并执行一次回退。 | ①日志是唯一真实来源；②恢复 = 检查点 + 后缀；③树状分支与 fork；④回退的两种语义（对话/文件）；⑤切分支时的摘要 | `demos/session-tree.js`（13 号票）；SVG 会话树 | 10,400 |
| main-12 | 跨会话记忆 | 判断一条信息该写进规则、记忆还是会话，并设计防污染措施。 | ①写入时机与整理合并；②检索与注入预算；③按项目隔离；④过期、删除与纠错；⑤错误记忆如何污染后续会话 | SVG 记忆写入—检索—注入回路 | 9,500 |
| main-13 | 缓存友好设计 | 找出一次请求里破坏前缀缓存的改动，并给出替代方案。 | ①前缀稳定三原则；②工具定义稳定；③易变内容的位置；④压缩与缓存失效的权衡；⑤命中率怎么观测 | 复用 `demos/cache-hit.js`；SVG 前缀断点图 | 9,900 |
| main-14 | 失败恢复：溢出、压缩失败与兜底 | 设计一次上下文溢出的恢复路径，并说明每种兜底的代价。 | ①溢出识别与压缩重试；②压缩请求自身超窗；③连续失败熔断；④无法再压缩的三种情况；⑤恢复后的状态一致性 | SVG 状态机（正常/溢出/压缩/失败） | 9,500 |
| main-15 | 扩展点：hooks 与插件 | 选择正确的扩展点改上下文，而不改核心代码。 | ①hooks 能改与不能改的边界；②PreCompact/PostCompact 的能力差异；③插件与 MCP 的分工；④自定义压缩的三档做法；⑤扩展点的稳定性风险 | SVG 扩展点位置图（请求链路旁挂） | 9,100 |
| main-16 | 评估与可观测：指标与 A/B | 设计一个可复现的上下文策略评测与 A/B 方案。 | ①工具自带的可观测数据；②上下文策略的四个指标；③评测集与任务分层；④A/B 分流与配对；⑤结果解释与常见陷阱 | SVG 实验设计图；表格模板：指标与数据来源 | 10,400 |

## 四、第三部分 进阶（L4，Karpathy 四级输出）

| 章节 ID | 标题 | 学习目标（1 句，动词开头） | 要点（3–5 条） | 交互演示 / 图示 | 预计篇幅（字） |
|---|---|---|---|---|---|
| adv-01 | 设计取舍专题 | 说出六组取舍中每种选择的代价与适用场景。 | ①压缩早 vs 晚；②裁剪 vs 摘要；③预加载 vs 按需、子代理 vs 单会话；④记忆 vs 规则、服务端压缩 vs 本地压缩；⑤每组取舍的代价与适用场景 | SVG 取舍矩阵（2×2）；每组配一张小图 | 7000 |
| adv-02 | 失败案例分析 | 复盘四个失败案例，指出根因与可操作的修复。 | ①压缩后丢失关键约束；②切点切断工具对；③缓存频繁失效导致成本飙升；④子代理返回过长；⑤回退后状态不一致 | `demos/compaction-drift.js`（多次压缩信息丢失与摘要累积，15 号票）；SVG 因果链 | 6500 |
| adv-03 | 架构对比 | 对比四种以上上下文架构，并解释分叉点。 | ①单会话 + 压缩；②树 + 投影；③日志 + surface；④服务端压缩；⑤架构选择与团队约束 | SVG 四架构并排图（一张图讲清） | 6500 |
| adv-04 | 设计你自己的上下文策略 | 产出一份给定场景下可执行的上下文策略。 | ①场景建模（任务长度/工具密度/并发）；②预算分配；③减量顺序；④隔离与延续；⑤验收指标 | SVG 决策树 + 策略模板表 | 6000 |
| adv-05 | 评估方法：L5 入门 | 设计一个能证明策略优劣的 A/B 实验。 | ①指标：成功率/成本/延迟/信息保留；②评测集构造；③配对与显著性；④消融实验；⑤结果写作 | SVG 实验流程图 | 6000 |

## 五、第四部分 源码解读（固定提交，逐行中文注释）

> 每节六步：功能说明 → 固定提交链接（带行号）→ 摘录（≤60 行，Claude Code ≤20 行）→ 逐段解读 + 流程图 → 与其他工具同类实现对比 → 思考题。
> 章节 ID 规则：`src-<工具ID>-NN`；工具 ID 见 `spec.md` 第 3 节。
> 篇幅口径（2026-10-19 作者确认 Q1=A）：每节 6,000–9,000 字，26 节全部保留；低于 6,000 视为讲不透。

| 章节 ID | 标题 | 学习目标（1 句，动词开头） | 要点（3–5 条） | 交互演示 / 图示 | 预计篇幅（字） |
|---|---|---|---|---|---|
| src-codex-01 | Codex · 压缩保留谁：候选与预算 | 逐行读懂 Codex 如何挑选进入摘要的消息。 | ①只收真实用户消息；②20k 预算从新到旧累加；③放不下立即停止；④与 Claude Code 重附清单对照 | 源码块 `compact()` 的候选选择循环（`compact.rs`，≤60 行）+ SVG 候选筛选流程图 | 7,000 |
| src-codex-02 | Codex · 请求四块与增量工具 | 说明 build_prompt 的四块拼装与增量工具的省 token 逻辑。 | ①Prompt 四字段；②历史规范化四项不变量；③incremental_tools 时置空 tools；④与 pi、opencode 的 system 折叠对比 | 源码块 `build_prompt`（`session/turn.rs:1666`）与 `Prompt`（`client_common.rs:22`）+ SVG 请求拼装图 | 6,400 |
| src-codex-03 | Codex · 规则差分：只发变化 | 读懂 WorldState 如何把 AGENTS.md 变化变成替换或移除通知。 | ①section 快照比较；②未变不发；③变化发替换、删除发移除；④缓存收益 | 源码块 `AgentsMdState::render_diff`（`context/world_state/agents_md.rs:44`）+ SVG 差分时序 | 6,400 |
| src-codex-04 | Codex · 头尾保留的截断预算 | 复现一次 token 预算下的中间截断与 UTF-8 对齐。 | ①ceil(bytes/4) 估算；②左右预算分配；③标记不占保留预算；④多块共享预算 | 源码块 `truncate_middle_with_token_budget`（`utils/string/src/truncate.rs:69`）+ SVG 截断示意 | 6,000 |
| src-claude-code-01 | Claude Code · 系统提示的静态/动态分段 | 说明静态段、边界标记与动态段如何共同决定缓存命中。 | ①静态 7 段；②边界常量；③section 记忆化生命周期；④DANGEROUS_uncached 的取舍 | 源码块 `getSystemPrompt`（`constants/prompts.ts:444`）与 `systemPromptSection`（`systemPromptSections.ts:20`，≤20 行）+ SVG 分段图 | 6,400 |
| src-claude-code-02 | Claude Code · 只有一个消息级缓存断点 | 解释为什么每请求只放一个 cache_control，以及 fork 为何前移。 | ①系统提示最多 4 块；②消息层恰好 1 个标记；③fork 时移到倒数第二条；④多标记的 KV 浪费 | 源码块 `addCacheBreakpoints`（`services/api/claude.ts:3063`）+ SVG 断点位置图 | 6,000 |
| src-claude-code-03 | Claude Code · 压缩后重附清单 | 列出一轮压缩后到底恢复了哪些内容。 | ①5 个文件 / 50k 预算；②技能 5k/25k；③plan 与 delta 重播；④边界消息结构 | 源码块 `compactConversation` 的重附清单（`services/compact/compact.ts:517`）+ SVG 重附流程图 | 7,000 |
| src-claude-code-04 | Claude Code · 只注入变化的附件 delta | 读懂 agent 列表 delta 如何避免全局缓存失效。 | ①37 个附件源；②三类 delta；③从历史重建已公告集合；④10.2% cache_creation 的教训 | 源码块 `getAttachments` 与 `getAgentListingDeltaAttachment`（`utils/attachments.ts:743`、`:1490`）+ SVG delta 时序 | 6,400 |
| src-pi-01 | pi · 切点、单回合拆分与文件跟踪 | 读懂 findCutPoint 如何在预算与合法边界之间取切点。 | ①从新到旧累加；②绝不切在 toolResult；③isSplitTurn 双摘要；④读写文件清单 | 源码块 `findCutPoint`（`compaction/compaction.ts:446`）与 `computeFileLists`（`compaction/utils.ts:67`）+ SVG 切点候选图 | 7,000 |
| src-pi-02 | pi · 压缩只改投影，不删历史 | 说明 CompactionEntry 如何让历史“变短但不变少”。 | ①只追加条目；②firstKeptEntryId 决定保留段；③重建顺序；④恢复不重跑压缩 | 源码块 `buildContextEntries`（`core/session-manager.ts:476`）+ SVG 日志/投影双层图 | 6,400 |
| src-pi-03 | pi · 用 section 补丁保住前缀缓存 | 读懂 diffSystemPromptSections 的 patch 语义。 | ①提示词 section 化；②只发变化；③null 表示删除；④与整段重发对比 | 源码块 `diffSystemPromptSections`（`core/system-prompt.ts:217`）+ SVG 补丁时序 | 6,000 |
| src-omp-01 | oh-my-pi · 压缩方法链与回退 | 读懂 runAutoCompaction 如何按可用性选择压缩方法。 | ①五方法默认顺序；②不可用即跳过；③shake 不够继续下一个；④按 reason 分支 | 源码块 `runAutoCompaction`（`session/session-maintenance.ts:4612`）+ SVG 方法链决策图 | 7,000 |
| src-omp-02 | oh-my-pi · shake 的机械省略 | 说明 shake 如何在不调模型的情况下砍掉大块内容。 | ①区域检测；②占位符与 recover 指针；③三档强度；④与裁剪的分工 | 源码块 `shake()`（`packages/agent/src/compaction/shake.ts`）+ SVG 省略前后对照 | 6,000 |
| src-omp-03 | oh-my-pi · snapcompact 把历史渲成图 | 说明历史转图片的帧形状、计价与回挂。 | ①文本转 PNG 帧；②按模型选帧形状；③帧 token 估算；④重建时重新挂回 | 源码块 `compact()` 与 `resolveShape()`（`packages/snapcompact/src/snapcompact.ts:447`）+ SVG 帧生成流程 | 6,400 |
| src-opencode-v1-01 | opencode v1 · 切点：整轮边界与预算 | 读懂 select 与 splitTurn 如何兼顾整轮与 token 预算。 | ①保留预算 clamp(25%, 2k, 15k)；②tail_turns 只限候选；③整轮优先、必要时拆轮；④tail_start_id | 源码块 `select` 与 `splitTurn`（`session/compaction.ts:223`）+ SVG 切点候选 | 6,600 |
| src-opencode-v1-02 | opencode v1 · prune：默认关闭的旧结果擦除 | 说明 prune 的保护线、最小收益与异步时机。 | ①保护最近 40k；②可擦超过 20k 才落地；③只打时间戳；④skill 输出永不擦 | 源码块 `prune`（`session/compaction.ts:271`）+ SVG 擦除范围 | 6,000 |
| src-opencode-v1-03 | opencode v1 · filterCompacted 重排替代历史 | 说明磁盘原文与模型可见历史为何顺序不同。 | ①压缩条目 + 摘要 + 保留段；②按 tail_start_id 重排；③分页读；④与 v2 seq 边界对照 | 源码块 `filterCompacted`（`session/message-v2.ts:534`）+ SVG 重排前后 | 6,400 |
| src-opencode-v2-01 | opencode v2 · 三入口触发与 due 判定 | 读懂 auto、overflow、manual 的预算差异与不变量。 | ①auto 每步开头判断；②overflow 预算乘 0.7；③锚点须晚于 checkpoint；④刚压完则跳过 | 源码块 `compact` 与 `due`（`session/compaction.ts:205`）+ SVG 触发决策图 | 6,600 |
| src-opencode-v2-02 | opencode v2 · 检查点：一条消息 + seq 边界 | 说明 v2 检查点字段与历史读取方式。 | ①status/reason/summary/recent；②按 seq 取连续段；③providerContext 存原生窗口；④与 v1 两条消息对照 | 源码块 `latestCompaction`（`session/history.ts:28`）与 `entriesForRunner`（`:78`）+ SVG 检查点结构 | 7,000 |
| src-opencode-v2-03 | opencode v2 · 指令 epoch 推进 | 说明压缩后基线如何一次性覆盖旧增量。 | ①observe 与 commit；②advanceEpoch 的时机；③fork 继承最新基线；④缓存收益 | 源码块 `observe`/`commit`（`session/instruction-state.ts:21`）与 `advanceEpoch`（`projector.ts:731`）+ SVG epoch 时间线 | 6,400 |
| src-grok-build-01 | Grok Build · 自动压缩与 7 段装配 | 读懂 full-replace 的触发、摘要与历史装配顺序。 | ①五条触发路径；②摘要 9 段并继承旧摘要；③7 段装配顺序；④最近消息在摘要之前 | 源码块 `assemble_compacted_history`（`code_compaction/assemble.rs:60`）与 `check_auto_compact_needed`（`session/compaction.rs:2095`）+ SVG 装配顺序 | 7,000 |
| src-grok-build-02 | Grok Build · 零成本裁剪：软裁剪与硬清空 | 复现一次按轮龄的三段式裁剪。 | ①超过 50% 窗口触发；②最近 3 轮保护；③4000 字符软裁剪为 1500+1500；④10 轮后硬清空 | 源码块 `prune_conversation`（`xai-chat-state/src/actor/request_builder.rs:125`）+ SVG 轮龄轴 | 6,400 |
| src-grok-build-03 | Grok Build · append-only 日志如何回退 | 说明 RewindMarker 如何在不删行的前提下截断重放。 | ①日志只追加；②marker 指向 prompt index；③重放时截断；④三种回退模式 | 源码块 `filter_rewind_lines`（`session/storage/mod.rs:1655`）与 RewindMarker 追加（`rewind.rs:400`）+ SVG 日志与 marker | 6,400 |
| src-dsh-01 | DeepSeek Harness · 日志与 surface 两层结构 | 说明 append-only 日志如何派生出模型可见历史。 | ①surfaceOp 的 append 与 replace；②deriveMessages；③缓存失效收敛到 contentGeneration；④重放确定性 | 源码块 `deriveMessages`（`core/session/src/index.ts:966`）与 `surfaceOp`（`surface.ts:49`）+ SVG 双层结构 | 7,000 |
| src-dsh-02 | DeepSeek Harness · 压缩选区的三个约束 | 读懂 selectCompactableRange 如何同时满足预算、配对与 system 保护。 | ①尾部累加到 retainTokens；②退到配对平衡处；③起点不能是 system；④无解返回 null | 源码块 `selectCompactableRange`（`compaction-basic/src/region.ts:117`）+ SVG 选区搜索 | 7,000 |
| src-dsh-03 | DeepSeek Harness · 裁剪器与影子计价 | 说明 pruner 的预算、替换与影子事件。 | ①8192/4096/1024；②按码点切片；③compaction/prune 影子事件；④仅在压缩触发后运行 | 源码块 `pruneSession`（`compaction-tool-result-pruner/src/index.ts`）与配置（`config.ts:8`）+ SVG 裁剪与计价 | 6,400 |

## 六、附录

| 章节 ID | 标题 | 学习目标（1 句，动词开头） | 要点（3–5 条） | 交互演示 / 图示 | 预计篇幅（字） |
|---|---|---|---|---|---|
| appendix-glossary | 术语表（中英对照） | 查到任一术语的中文、英文与一句话定义。 | ①按主题分组；②每条给英文原词；③易混词对照；④指向首次出现章节 | 表格；无交互 | 4000 |
| appendix-params | 参数速查表 | 查到 8 个工具的关键参数、默认值与所在章节。 | ①按工具分表；②标注版本或提交；③默认值突出显示；④冲突口径单独脚注 | 表格；无交互 | 5000 |
| appendix-matrix | 16 类 × 8 工具总表 | 判断某工具在某类能力上的做法，并用一张表呈现。 | ①矩阵正文；②可信度标记；③空白与推断说明；④口径说明 | 表格（复用 `research/matrix.md`） | 3500 |
| appendix-reading | 推荐阅读 | 选到 3–5 篇可继续读的材料，并按主题分组。 | ①官方文档；②源码入口；③论文与博客；④同主题对照阅读顺序 | 列表；无交互 | 2500 |
| appendix-video | 视频分镜脚本 | 写出 3–5 个主题的 3Blue1Brown 风格分镜与旁白。 | ①主题选择；②分镜表；③旁白稿；④画面元素清单 | 分镜表 + SVG 关键帧示意 | 5000 |

---

## 七、7 个必做交互演示的落点

| # | 演示 | 文件 | 主章节 | 负责票 | 要求 |
|---|---|---|---|---|---|
| 1 | 上下文窗口组成拖拽器 | `demos/context-budget.js` | intro-01 | 07 | 拖动各段占比，实时显示占用比例与剩余空间 |
| 2 | 压缩模拟器 | `demos/compact-sim.js` | main-08 | 08 | 可调阈值、保留量、预留空间，实时移动切点 |
| 3 | 工具调用与结果成对保留 | `demos/tool-pairing.js` | main-08 | 08 | 移动切点，观察工具调用与结果被整对保留或整对丢弃 |
| 4 | Prompt cache 命中 | `demos/cache-hit.js` | intro-05 | 10 | 改前缀后标出缓存从哪一位开始失效 |
| 5 | 多次压缩信息丢失对比 | `demos/compaction-drift.js` | adv-02 | 15 | 连续压缩 N 次，对比摘要累积与事实丢失 |
| 6 | 子代理上下文隔离 | `demos/subagent-isolation.js` | main-10 | 13 | 展开/收起子会话，观察父会话只多出最终返回 |
| 7 | 会话树、分叉与回退 | `demos/session-tree.js` | main-11 | 13 | 在树上分叉、回退，观察模型可见历史变化 |

## 八、标题变更表

| 章节 ID | toc.js 原标题 | 本大纲标题 | 原因 |
|---|---|---|---|
| intro-06 | 用户侧怎么管理上下文 | 用户侧怎么管理上下文：决策流程图 | 点明本章产出是一张决策图 |
| main-04 | 动态注入 | 动态注入：提醒、状态与增量 | 补足三类注入对象，避免标题过泛 |
| main-07 | 历史裁剪 | 历史裁剪：不调用模型的减量 | 与 main-08 的“压缩（调模型）”划清边界 |
| main-11 | 会话时间线 | 会话时间线：恢复、分叉与回退 | 与本类清单的三项能力对齐 |
| main-14 | 失败恢复 | 失败恢复：溢出、压缩失败与兜底 | 点明三类失败面 |
| main-16 | 评估与可观测 | 评估与可观测：指标与 A/B | 点明 L5 导向 |
| src-codex-01…04 | Codex CLI 源码解读（1 节） | 拆为 4 节，见第五部分 | 每节只讲一个功能 |
| src-claude-code-01…04 | Claude Code 源码解读（1 节） | 拆为 4 节，见第五部分 | 每节只讲一个功能 |
| src-pi-01…03 | pi 源码解读（1 节） | 拆为 3 节，见第五部分 | 每节只讲一个功能 |
| src-omp-01…03 | oh-my-pi 源码解读（1 节） | 拆为 3 节，见第五部分 | 每节只讲一个功能 |
| src-opencode-v1-01…03 | opencode v1 源码解读（1 节） | 拆为 3 节，见第五部分 | 每节只讲一个功能 |
| src-opencode-v2-01…03 | opencode v2 源码解读（1 节） | 拆为 3 节，见第五部分 | 每节只讲一个功能 |
| src-grok-build-01…03 | Grok Build 源码解读（1 节） | 拆为 3 节，见第五部分 | 每节只讲一个功能 |
| src-dsh-01…03 | DeepSeek Harness 源码解读（1 节） | 拆为 3 节，见第五部分 | 每节只讲一个功能 |

## 九、写作顺序建议

### 必须先写（串行，定风格与模板）

1. `intro-01`（07 号票）：定 Head First 节奏与 `context-budget.js` 的写法。
2. `main-08`（08 号票）：定主线五段结构、7 弹窗、对比表、测验，以及 `compact-sim.js`、`tool-pairing.js` 两个演示。
3. `src-codex-01`（09 号票）：定源码六步格式、代码块注释与流程图；本节按票面要求写 **Codex 的压缩实现**。
4. 三个样章通过验收后，才允许并行铺开；否则返工面会扩散到 50 多页。

### 可并行（在样章定稿后）

- 入门线：`intro-02…07`（10 号票）可与主线并行；其中 `intro-05` 必须先落 `cache-hit.js`，因为 `main-13` 要复用。
- 主线 A 组：`main-01…04`（11 号票）。
- 主线 B/C 组：`main-05…07`、`main-09`（12 号票）。
- 主线 D 组：`main-10…12`（13 号票），同时交付 `subagent-isolation.js`、`session-tree.js`。
- 主线 E 组：`main-13…16`（14 号票），复用 `cache-hit.js`，不另建演示。
- 源码线：17 号票（Codex + Claude Code，8 节）与 18 号票（pi、omp、opencode v1/v2，12 节）可并行；19 号票（Grok Build + dsh，6 节）依赖 09 的模板，也可同时开。
- 附录：`appendix-matrix`、`appendix-params` 可直接从 `research/` 生成初稿；`appendix-glossary`、`appendix-reading` 需等主线术语稳定后定稿。

### 必须后写（依赖前序内容）

- `adv-01…05`（15、16 号票）依赖 `main-01…16` 全部完成；`adv-02` 另需 `compaction-drift.js`。
- `appendix-video`（20 号票）依赖正文与源码章节全部定稿，分镜要引用真实结论。
- `appendix-matrix` 的最终校对必须在所有主线章节写完后做一次，防止正文与矩阵口径分叉。

### 建议的并行批次

| 批次 | 内容 | 说明 |
|---|---|---|
| 第 1 批（串行） | intro-01 → main-08 → src-codex-01 | 三个样章，逐个验收 |
| 第 2 批（5 路并行） | intro-02…07；main-01…04；main-05…07+09；main-10…12；main-13…16 | 演示文件按第七节归属，避免多人改同一文件 |
| 第 3 批（3 路并行） | src 17；src 18；src 19 | 统一引用 `research/source-map/` 的函数与行号 |
| 第 4 批（2 路并行） | adv-01…02；adv-03…05 | 先出图，再写受控中文 |
| 第 5 批（串行） | appendix 5 项 → 集成检查 | 最后统一校对版本号、可信度标签与死链 |
