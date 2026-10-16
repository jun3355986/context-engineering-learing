---
title: oh-my-pi · 证据卡（ohmy-*）
task: T08
role: 工具研究 Agent
created: 2026-10-15
write_scope: 02-工具/oh-my-pi/证据/
snapshot: f979f4639777858de28e6ecb99d577443abe0b7b
format: 任务书 §4.4 + 08-验收/T07-后六工具样本规范.md §2
link_base: https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/
---

# oh-my-pi · 证据卡

> 格式遵循任务书 §4.4。结论ID 规则 `ohmy-<mechanism>-<number>`。
> 链接基址：`https://github.com/can1357/oh-my-pi/blob/f979f4639777858de28e6ecb99d577443abe0b7b/`（路径后加 `#L起-L止`）。
> **性质栏**：事实 / 推断 / 建议。**实现状态栏**：默认 / 条件 / 实验 / 桩或空实现 / 未证实。
> **凡无实测处**：运行证据一律 `NOT_RUN + 原因`，不得把源码阅读写成实验通过。
> 术语统一沿用 `00-管理/术语表.md` 与 T02 §E（触发线、替代历史、持久化断点、出口限长、落盘…）。
> **高风险主张**（阈值/默认开关/持久化/二次压缩/缓存）已在卡内标注「待另一 Agent 复核」。

---

## A. 请求组装与规则（assembly / rule / retrieval）

```yaml
结论ID: ohmy-assembly-01
结论: 一次请求的会话消息由 buildSessionContext() 从 leaf→root 路径重建；有压缩时按「摘要消息在前 + firstKeptEntryId 起的保留段 + 压缩后消息」发射，并尊重 /clear 的 reset_boundary；末尾统一剥离悬挂 tool_use 与失败/中止 assistant 轮
性质: 事实
范围: 快照 f979f46；packages/coding-agent；默认
实现状态: 默认
来源: packages/coding-agent/src/session/session-context.ts#L238-644（三分支发射 #L422-644、剥离 #L673-769）；session-manager.ts#L3749-3755
数据走查: DW-assembly-01
运行证据: NOT_RUN + 原因：需 omp 产品入口 + T03 合成任务 + 真实模型（本机 omp 未安装，见 过程观察.md）
不能证明: 不证明 provider 端如何进一步加工该请求体；不证明 transcript 模式与模型上下文模式在具体模型上的等效性
冲突裁决: 无旧结论；回答 CM-01；与 pi 的「projection + tools 拼装」同源但 omp 叠加了 provider 原生载荷与 reset 边界分支
核验日期: 2026-10-15
```

```yaml
结论ID: ohmy-assembly-02
结论: 系统提示词 = [渲染后的主模板] + 各 eval prelude 的 guidance + 一个**末尾** `<project-context>` 块（含上下文文件路径、workspace 树、active repo、session 追加文本），使不同目录的会话共享**静态前缀**（Anthropic 头缓存断点落在此块之前）
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认
来源: packages/coding-agent/src/system-prompt.ts#L1004-1036
数据走查: DW-assembly-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明该前缀稳定在具体 provider 上的实际缓存命中率（属 T19）
冲突裁决: 支持 CM-01/CM-12 的「前缀稳定」机制线索；与 pi 的 section 差分不同（omp 用「模板 + 尾部 project-context 块」组织）
核验日期: 2026-10-15
```

```yaml
结论ID: ohmy-rule-01
结论: 内置上下文文件名 = AGENTS.md / CLAUDE.md / GEMINI.md / copilot-instructions.md（可再加 contextFiles.extra）；按主 cwd + 额外 workspace root 发现并去重；workspace 树里的 agentsMdFiles 有 200 个文件上限（AGENTS_MD_LIMIT=200）
性质: 事实
范围: 快照 f979f46；默认（contextFiles.extra 默认 []）
实现状态: 默认
来源: packages/coding-agent/src/session/context-settings.ts#L26-69；system-prompt.ts#L761-772,850；workspace-tree.ts#L16
数据走查: DW-rule-01
运行证据: NOT_RUN + 原因同上
不能证明: 不证明单个上下文文件的字节预算/截断策略（omp 未见类似 pi 的 32KiB 共享字节预算常量；AGENTS_MD_LIMIT 是**文件数**上限不是字节上限）
冲突裁决: 回答 CM-02；比 pi 多 GEMINI.md / copilot-instructions.md 两种候选名
核验日期: 2026-10-15
```

```yaml
结论ID: ohmy-rule-02
结论: 技能走渐进式披露——系统提示词只渲染技能名+描述（SkillDescriptionCatalog），完整手册按需经 `skill://` 读取；需存在声明 `skill://` 能力的工具才渲染
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认
来源: packages/coding-agent/src/system-prompt.ts#L919-939
数据走查: DW-rule-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明「按需读」在具体模型上是否真的会触发
冲突裁决: 支持术语表「技能（渐进式披露）」；回答 CM-02
核验日期: 2026-10-15
```

```yaml
结论ID: ohmy-retrieval-01
结论: 资料按需检索：read/grep/glob 等；read 支持行范围/分页续读，read.defaultLimit 被夹到 [1, DEFAULT_MAX_LINES(3000)]
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认
来源: packages/coding-agent/src/tools/read.ts#L1025-1027,1540；tools/grep.ts；tools/glob.ts
数据走查: DW-retrieval-01
运行证据: NOT_RUN + 原因同上
不能证明: 不证明检索质量或选择策略优劣
冲突裁决: 回答 CM-03（按需检索，非全量装填）
核验日期: 2026-10-15
```

## B. 工具输出治理（trunc）

```yaml
结论ID: ohmy-trunc-01
结论: 工具输出两条独立上限——3000 行 / 50 KiB（51200 字节），先到者胜；truncateHead 保头（不返回半行）、truncateTail 保尾（可返回半行）；单行列上限 512 字节；首行超字节上限时返回空内容 + firstLineExceedsLimit
性质: 事实
范围: 快照 f979f46；已发布 @oh-my-pi/pi-tui@18.10.4（函数级观察一致）；默认
实现状态: 默认
来源: packages/tui/src/tools/streaming-output.ts#L10-15,345-441,449-…；**观察** OBS-ohmy-trunc-01
数据走查: DW-trunc-01
运行证据: OBS-ohmy-trunc-01（bun 运行已发布包 truncateHead，4 断言含负例，退出码 0）
不能证明: 不证明 omp 产品入口端到端的默认值（未运行产品）；不证明「对中文保守」的普适性（样本仅合成 CJK）
冲突裁决: 回答 CM-04；**与 pi 差异**：pi=2000 行/50KB，omp=**3000 行/50 KiB**（行上限不同，字节上限相同）
核验日期: 2026-10-15
高风险主张: 阈值数字已标「待另一 Agent 复核」（另见 问题与审查.md §6）
```

```yaml
结论ID: ohmy-trunc-02
结论: 工具输出超限时原文落盘为 artifact（artifact://<id>），请求里只留预览 + 路径；artifact 有独立上限 16 MiB（头 3 MiB 保留 + 滚动尾），触顶写 [ARTIFACT TRUNCATED: …]
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认
来源: packages/tui/src/tools/streaming-output.ts#L17-26,74-116,961-966；packages/coding-agent/src/tools/bash.ts#L1506-1507（落盘分配 allocateOutputArtifact）、#L766,779（tail 方向）
数据走查: DW-trunc-02
运行证据: NOT_RUN + 原因：落盘路径需产品入口 + 合成大输出（未运行 omp）
不能证明: 不证明 artifact 文件在长会话中的清理/存活期；不证明 artifact 字节上限在具体部署上的实际值
冲突裁决: 回答 CM-04 + CM-07 的「能否找回原文」（文件层可找回，经 artifact:// 与 read）
核验日期: 2026-10-15
```

## C. 窗口计量与触发（trigger）

```yaml
结论ID: ohmy-trigger-01
结论: 默认阈值 = 窗口 − 有效预留；有效预留 = max(floor(window×0.15), 配置 reserve ?? 16384)；默认 thresholdPercent=-1、thresholdTokens=-1 走该预留路径。200K 窗口 → 阈值 170,000
性质: 事实
范围: 快照 f979f46；默认（**含小窗口回退与 W−1 上限**：`resolveBudgetReserveTokens` 在默认预留对小窗口不可用/超窗时改用 `max(1, floor(W×0.15))`；`promptBudgetTokens` 再取 `min(W−1, …)`；常规窗口等价于 window − 有效预留）
实现状态: 默认
来源: packages/agent/src/compaction/compaction.ts#L199,216-227,320-345,380-414；packages/coding-agent/src/session/context-settings.ts#L275-285
数据走查: DW-trigger-01
运行证据: NOT_RUN + 原因：需 T03 + 产品入口
不能证明: 不证明真实长任务中的实际触发次数；不证明 170,000 在服务端按真实 tokenizer 计费下的精确到线值
冲突裁决: 回答 CM-05；**与 pi 差异**：pi 预留固定 16384 → 200K 窗口阈值 183,616；omp 预留含 15% 下限 → **170,000**（更早触发）
核验日期: 2026-10-15
高风险主张: 阈值公式与默认开关已标「待另一 Agent 复核」
```

```yaml
结论ID: ohmy-trigger-02
结论: 用量口径 = calculateContextTokens(usage)（优先 provider 的 contextTokens，否则 totalTokens 或 input+output+cacheRead+cacheWrite，并减去服务端编排 token orchestration）；触发判定用 compactionContextTokens(providerTokens, 本地存量估算) 取大兜底
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认
来源: packages/agent/src/compaction/compaction.ts#L257-267,371-373；session-maintenance.ts#L2723-2726
数据走查: DW-trigger-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明本地存量估算与 provider 真实计费的偏差幅度
冲突裁决: 回答 CM-05（计量口径）；比 pi 的「usage 优先 + chars/4」多一层「剔除编排 token + 存量兜底」
核验日期: 2026-10-15
```

```yaml
结论ID: ohmy-trigger-03
结论: 自动压缩共六条触发路径——手动 /compact、溢出恢复、输出未完成(length)恢复、轮后阈值、轮中阈值(midTurnEnabled 默认 true)、空闲维护(idleEnabled 默认 false)
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认（idle 为条件：默认关）
来源: docs/compaction.md#L68-77；session-maintenance.ts#L2043(runIdleCompaction),#L2828(checkCompaction),#L2713-2805(轮中)
数据走查: DW-trigger-03
运行证据: NOT_RUN + 原因同上
不能证明: 不证明「到线」在真实长任务中的实际触发次数与顺序
冲突裁决: 回答 CM-06/CM-05；**比 pi 多**「输出未完成恢复」「空闲维护」两条路径
核验日期: 2026-10-15
```

## D. 压缩与摘要（compact / summary）

```yaml
结论ID: ohmy-compact-01
结论: 自动维护走 compaction.methodOrder（默认 ["remote","snapcompact","handoff","shake","soft"]），不可用/失败逐级回退；手动 /compact 与自动共用底层 compact()
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认
来源: packages/coding-agent/src/session/compaction-methods.ts#L44-50；context-settings.ts#L142-155；docs/compaction.md#L72,506-537
数据走查: DW-compact-01
运行证据: NOT_RUN + 原因同上
不能证明: 不证明各方法在真实 provider 上的成功顺序与失败率
冲突裁决: 回答 CM-06；**与 pi 差异**：pi 只有单一摘要路径；omp 是**五方法链**（含无 LLM 的 snapcompact/shake 与 provider 原生 remote）
核验日期: 2026-10-15
高风险主张: 默认方法顺序已标「待另一 Agent 复核」
```

```yaml
结论ID: ohmy-summary-01
结论: 摘要提示词为固定结构（Goal / Constraints & Preferences / Progress(Done/In Progress/Blocked) / Key Decisions / Next Steps / Critical Context / Additional Notes）+ <files> 文件清单；有旧摘要时改用 UPDATE 提示词经 <previous-summary> 增量合并（PRESERVE+ADD）
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认
来源: packages/agent/src/compaction/prompts/compaction-summary.md；prompts/compaction-update-summary.md；docs/compaction.md#L305-324,354-380
数据走查: DW-summary-01
运行证据: NOT_RUN + 原因同上
不能证明: 不证明增量更新「不丢事实」（连续压缩实验属 T19/LQ-09、FB-11）
冲突裁决: 回答 CM-07；为 C-04（旧摘要是否无损）提供「结构性增量、但判为有损」定位
核验日期: 2026-10-15
```

```yaml
结论ID: ohmy-summary-02
结论: 切点走在 user/assistant/bashExecution/hookMessage/branchSummary/compactionSummary/custom_message/branch_summary 边界，绝不切在 toolResult；从最新往回按整组累加到超过 keepRecentTokens(默认 20000) 取最近合法切点；切点非轮首则按 split-turn 生成两份摘要合并
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认
来源: packages/agent/src/compaction/compaction.ts#L427-462,521-574；context-settings.ts#L281-285；docs/compaction.md#L254-303
数据走查: DW-summary-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明「20k 保留」在真实会话中留下的具体条目数
冲突裁决: 回答 CM-07；术语表「直接保留预算」对 omp 记为 keepRecentTokens(20000)（与 pi 同值，但 omp 另有压缩前裁剪预算）
核验日期: 2026-10-15
```

```yaml
结论ID: ohmy-summary-03
结论: 压缩前先跑工具结果裁剪 pruneToolOutputs：保护最新 40000 tool-output token、要求总节省 ≥20000、绝不裁剪 <50 token 的结果；superseded read 与 useless 结果按缓存感知时机被替换为固定占位符
性质: 事实
范围: 快照 f979f46；默认（supersedeReads=true、dropUseless=true）
实现状态: 默认
来源: packages/agent/src/compaction/pruning.ts#L77-82,537-666；docs/compaction.md#L227-252
数据走查: DW-summary-03
运行证据: NOT_RUN + 原因同上
不能证明: 不证明裁剪对最终任务成功率的净影响；不证明缓存感知时机在具体 provider 上的命中效果
冲突裁决: 回答 CM-07 的「移除」手段；**omp 独有**（pi 无此压缩前裁剪预算）
核验日期: 2026-10-15
高风险主张: 裁剪阈值已标「待另一 Agent 复核」
```

```yaml
结论ID: ohmy-summary-04
结论: 除 LLM 摘要外还有两种本地方法：shake（把可回收的重块替换为 artifact:// 引用，保护近期 token 窗口 + 最小节省阈值，无 LLM 调用）；snapcompact（把被丢弃历史渲染成 PNG 位图帧，模型读图，无模型/API/网络）；实验性 compaction.experimentalContextManagement 默认 false，开启后改用持久笔记 + 可检索原文历史
性质: 事实
范围: 快照 f979f46；shake/snapcompact 为方法链成员（条件）；experimentalContextManagement 默认 false
实现状态: 默认（方法链成员）｜实验（experimentalContextManagement）
来源: docs/compaction.md#L200-217,152-198；packages/agent/src/compaction/shake.ts；packages/snapcompact/src/snapcompact.ts
数据走查: DW-summary-04
运行证据: NOT_RUN + 原因同上
不能证明: 不证明 snapcompact 的位图保真度与计费收益（属 packages/snapcompact 的 200k eval，非本机实测）
冲突裁决: 回答 CM-07；**omp 独有**（pi 无 shake/snapcompact）
核验日期: 2026-10-15
```

## E. 记忆与子 Agent（memory / cm09）

```yaml
结论ID: ohmy-memory-01
结论: oh-my-pi **有**独立长期记忆：memory.backend 默认 off，可选 local（本地 rollout 摘要管线，注入 "Memory Guidance"，注入上限 memories.summaryInjectionTokenLimit=5000 token）/ hindsight（远程向量服务）/ mnemopi（本地 SQLite）/ sharpshooter（项目决策文件）；RPC/ACP 协议主机默认 off
性质: 事实
范围: 快照 f979f46；默认 off（条件启用）
实现状态: 条件（默认关闭，需选后端）
来源: packages/coding-agent/src/memory-backend/settings.ts#L12-40；memory-backend/resolve.ts#L1-31；docs/memory.md#L1-11,113-132
数据走查: DW-memory-01
运行证据: NOT_RUN + 原因：记忆后端默认关，且产品入口未运行；主张为「有实现（条件）」而非运行否证
不能证明: 不证明各后端在真实项目上的记忆质量；不证明 hindsight 服务端行为
冲突裁决: 回答 CM-08；**与 pi 差异**：pi 默认无长期记忆（推断），omp **内置 4 后端 + off（共 5 个取值）**（默认仍 off）
核验日期: 2026-10-15
高风险主张: 默认开关(off)与注入上限已标「待另一 Agent 复核」
```

```yaml
结论ID: ohmy-cm09-01
结论: CM-09（子 Agent 交接）对 oh-my-pi **适用**——内置 task 工具按 agent 定义（自带 systemPrompt）+ task/solutionSpace 生成**独立子会话**；支持 isolation（默认 false）、batch（默认 true）、outputSchema/structured（默认 false）；单 agent 输出上限 500000 字节/5000 行；有递归深度上限
性质: 事实
范围: 快照 f979f46；默认（task 工具默认可用）
实现状态: 默认
来源: packages/coding-agent/src/task/types.ts#L28-32,193-249；packages/coding-agent/src/task/index.ts；docs/agent-hub.md
数据走查: DW-cm09-01
运行证据: NOT_RUN + 原因同上
不能证明: 不证明子代理交接材料在具体任务上的充分性；不证明自定义 agent 定义的行为
冲突裁决: 回答 CM-09；**与 pi 差异**：pi **刻意不含** sub-agents（T02 §G、T06 pi-cm09-01），omp **默认含**
核验日期: 2026-10-15
```

## F. 保存 / fork / 恢复（persist / recover / fork）

```yaml
结论ID: ohmy-persist-01
结论: 会话 = 只追加 JSONL 条目日志（每行一条目，按 id/parentId 成树，当前版本 3）；压缩只追加 CompactionEntry，不删除任何原始条目
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认
来源: docs/session-tree-plan.md#L9-14,221-228；packages/coding-agent/src/session/session-manager.ts#L3530(appendCompaction)；packages/agent/src/compaction/entries.ts#L34-54
数据走查: DW-persist-01
运行证据: NOT_RUN + 原因同上
不能证明: 不证明会话文件的清理/轮转策略
冲突裁决: 支持 C-03/C-12：「摘要不可逆 ≠ 源记录被删除」
核验日期: 2026-10-15
```

```yaml
结论ID: ohmy-recover-01
结论: 恢复/重建属「持久化断点」路线（路线 B）：压缩产物（summary + firstKeptEntryId）已持久化，恢复按当前分支投影重建（摘要 + 保留段 + 后续条目），不重放全部历史重算；并支持 provider 原生回放载荷（OpenAI remote compaction / Anthropic native）；开启实验性上下文管理后还可经 history://current/full 让模型读回原文
性质: 事实
范围: 快照 f979f46；默认（history:// 属实验态）
实现状态: 默认（持久化断点）｜实验（history://current/full 全文找回）
来源: packages/coding-agent/src/session/session-context.ts#L483-644；session-manager.ts#L3749-3755；docs/compaction.md#L152-198
数据走查: DW-recover-01
运行证据: NOT_RUN + 原因同上
不能证明: 不证明被压掉细节在**默认（未开实验）**下于模型可见层永不恢复（人工读文件/artifact 除外）
冲突裁决: **裁决 LQ-10（oh-my-pi 侧）= 持久化断点**；支持 C-03/C-12 部分裁决（模型可见不可逆 / 文件层可找回）
核验日期: 2026-10-15
高风险主张: 持久化与恢复语义已标「待另一 Agent 复核」
```

```yaml
结论ID: ohmy-fork-01
结论: /tree 与 /branch 是**同文件**叶子移动（branchWithSummary 在新导航位置挂 branch_summary）；AgentSession.branch() / createBranchedSession 才**另写新文件**（复制 root→leaf 路径）
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认
来源: docs/session-tree-plan.md#L49-113；session-manager.ts#L3880(createBranchedSession)
数据走查: DW-fork-01
运行证据: NOT_RUN + 原因同上
不能证明: 不证明分支摘要对后续任务的净收益
冲突裁决: 回答 CM-10（fork 语义）
核验日期: 2026-10-15
```

## G. 失败与副作用（fail）

```yaml
结论ID: ohmy-fail-01
结论: 上下文溢出**不进**通用重试；溢出恢复先尝试「升级更大模型」，否则走方法链压缩并重试；输出未完成(length)的连续无产出恢复上限 3 次；载荷被拒(413)不自动当 token 溢出
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认
来源: docs/compaction.md#L113-150；docs/non-compaction-retry-policy.md#L18-36
数据走查: DW-fail-01
运行证据: NOT_RUN + 原因：需 T03 失败注入
不能证明: 不证明「升级优先」对最终任务成功率的净影响
冲突裁决: 回答 CM-11；与 pi「溢出仅一次 compact-and-retry」不同（omp 先升级模型）
核验日期: 2026-10-15
```

```yaml
结论ID: ohmy-fail-02
结论: 通用重试 retry.enabled 默认 true、maxRetries 默认 10、baseDelayMs 默认 500、退避上限 8000ms（75–100% 抖动）；失败 assistant 从**运行时上下文**移除但**会话日志仍保留**，成功后标 retryRecovery（recovered/superseded）并在重建 LLM 上下文时排除
性质: 事实
范围: 快照 f979f46；默认
实现状态: 默认
来源: docs/non-compaction-retry-policy.md#L106-134,272-277
数据走查: DW-fail-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明重试对最终任务成功率的净影响
冲突裁决: 回答 CM-11；**与 pi 差异**：pi retry.maxRetries 默认 3，omp 默认 **10**
核验日期: 2026-10-15
高风险主张: 默认重试参数已标「待另一 Agent 复核」
```

## H. 缓存与成本（cache）

```yaml
结论ID: ohmy-cache-01
结论: 缓存预热器自 pi 移植（cache-warmer.ts 头注释明示 "Ported from upstream pi"）：在模型声明的 prompt-cache 生命周期 90% 处重放（至少留 10s 余量），仅当预计节省 ≥$0.05 才发；分 streaming（run 活跃）/idle 两阶段，安全窗口 60min/30min；handoff 侧请求复用实时 prompt-cache key 以对齐前缀
性质: 事实
范围: 快照 f979f46；CLI 侧可证；服务端命中率/TTL 不可证
实现状态: 默认（CLI 侧）｜服务端 UNOBSERVABLE
来源: packages/coding-agent/src/session/cache-warmer.ts#L1-77；docs/handoff-generation-pipeline.md#L56-60,84（L60 live provider cache key；L84 "routed with the same promptCacheKey the turn used"）
数据走查: DW-cache-01
运行证据: NOT_RUN + 原因：服务端命中/TTL 不可由本地源码核实，需 T19
不能证明: ❌不证明命中率；❌不证明预热是否真的省钱（依赖服务端 TTL 与真实到达率）
冲突裁决: 回答 CM-12；与 pi 的 cache-warmer 同源，属「共享代码来源」的显式例证
核验日期: 2026-10-15
```

## I. 扩展点（ext）

```yaml
结论ID: ohmy-ext-01
结论: 钩子事件含 session_start / session_before_switch / session_switch / session_before_branch / session_branch / session_before_compact / session.compacting / session_compact / session_before_tree / session_tree / context / before_agent_start / agent_start/end / turn_start/end / auto_compaction_start/end / auto_retry_start/end / tool_call / tool_result 等；session_before_compact 可取消或提供自定义压缩载荷，session.compacting 可覆盖 prompt/注入 context/写 preserveData
性质: 事实
范围: 快照 f979f46；扩展态（需装扩展/写 hook）
实现状态: 条件（需装扩展）
来源: packages/coding-agent/src/extensibility/hooks/types.ts#L472-501；docs/compaction.md#L453-491
数据走查: DW-ext-01
运行证据: NOT_RUN + 原因：需真实扩展
不能证明: 不证明具体第三方扩展的实现质量；不证明扩展改动对缓存前缀的影响
冲突裁决: 回答「扩展能改什么」；默认不含任何扩展能力
核验日期: 2026-10-15
```

## J. 旧结论 / 冲突裁决（version）

```yaml
结论ID: ohmy-version-01
结论: 对 C-03/C-12/LQ-10 的 oh-my-pi 侧裁决——omp 属「持久化断点」；压缩不删原始条目（磁盘可找回）；默认下被压细节在**模型可见层**不自动恢复，但**开启实验性上下文管理后**模型可经 history://current/full 读回原文，另有 artifact:// 与文件层可找回
性质: 事实
范围: 快照 f979f46 vs 学习笔记 §10「绝不可能找回」/ 冲突表 C-12
实现状态: 默认（持久化断点）｜实验（全文找回）
来源: 同 ohmy-recover-01 / ohmy-persist-01 / ohmy-summary-04
数据走查: DW-recover-01
运行证据: NOT_RUN + 原因：需 T03 + 产品入口
不能证明: 不证明 UI 是否提供「回看被压段落」的图形入口（默认态）
冲突裁决: **限制**「绝不可能找回」——限定为「默认、模型可见层」；**维持**「摘要不可逆 ≠ 源记录删除」；**修正**「omp 无原文找回」——实验态有 history://
核验日期: 2026-10-15
```

```yaml
结论ID: ohmy-version-02
结论: T02 §G 称 oh-my-pi「已在 pi 上叠加 LSP/DAP/子代理等」——本包逐项核实**成立**：存在 packages/coding-agent/src/lsp/、dap/、task/（子代理）；另新增记忆、压缩方法链、snapcompact 等
性质: 事实
范围: 快照 f979f46
实现状态: 默认（子代理）；LSP/DAP 为默认能力/条件能力
来源: 目录 packages/coding-agent/src/{lsp,dap,task,memory-backend,memories}/；docs/lsp-config.md、docs/memory.md
数据走查: —
运行证据: NOT_RUN + 原因：目录存在性核实，无需模型运行
不能证明: 不证明「共享代码来源」部分的具体行级继承范围（需逐文件比对 pi，超出本任务范围）
冲突裁决: **支持** T02 §G 的「叠加」表述；**限制**「共享代码来源 ≠ 默认行为相同」——默认行为差异见 工具概览 §4/§5
核验日期: 2026-10-15
```

```yaml
结论ID: ohmy-version-03
结论: 本包澄清：npm 同名包 oh-my-pi@0.2.0（作者 acidsugarx）与本项目无关；本包研究对象 can1357/oh-my-pi 的官方 npm 包为 @oh-my-pi/pi-coding-agent，workspace 成员如 @oh-my-pi/pi-tui@18.10.4
性质: 事实
范围: npm registry 核实（2026-10-15）
实现状态: 不适用（身份澄清）
来源: 00-管理/版本表.md#Q3；npm view @oh-my-pi/pi-tui version → 18.10.4（dist.tarball registry.npmjs.org）
数据走查: —
运行证据: 命令输出见 过程观察.md §2
不能证明: 不证明第三方包 oh-my-pi@0.2.0 的任何行为（不属研究对象）
冲突裁决: 支持版本表 Q3
核验日期: 2026-10-15
```

---

## 附：结论ID 一览

| 族 | 结论ID | 一句话 |
|---|---|---|
| assembly | ohmy-assembly-01/02 | 路径投影重建；模板+尾部 project-context 前缀 |
| rule | ohmy-rule-01/02 | 四种内置上下文文件+200 文件上限；技能渐进式披露 |
| retrieval | ohmy-retrieval-01 | read/grep/glob 按需 + read 分页 |
| trunc | ohmy-trunc-01/02 | 3000 行/50KiB 先到者；超限落 artifact |
| trigger | ohmy-trigger-01/02/03 | window−max(15%,16384)；usage 剔除编排+存量兜底；六路径 |
| compact | ohmy-compact-01 | 五方法链 remote→snapcompact→handoff→shake→soft |
| summary | ohmy-summary-01..04 | 结构化摘要+增量；切点不绝于 toolResult；压缩前裁剪；shake/snapcompact |
| memory | ohmy-memory-01 | 4 后端 + off（共 5 取值）长期记忆（默认 off） |
| cm09 | ohmy-cm09-01 | 子 Agent 适用（默认内置 task） |
| persist | ohmy-persist-01 | 追加式 JSONL 树，不删原条目 |
| recover | ohmy-recover-01 | 持久化断点路线（LQ-10 裁决） |
| fork | ohmy-fork-01 | /tree、/branch 同文件；branch() 另写文件 |
| fail | ohmy-fail-01/02 | 溢出先升级；重试 maxRetries=10 |
| cache | ohmy-cache-01 | 缓存预热自 pi 移植；handoff 复用 cache key |
| ext | ohmy-ext-01 | 钩子可取消/替换压缩与请求 |
| version | ohmy-version-01/02/03 | 旧结论逐条裁决 + 身份澄清 |
