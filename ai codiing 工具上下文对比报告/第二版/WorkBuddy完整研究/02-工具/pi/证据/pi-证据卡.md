---
title: pi · 证据卡（pi-*）
task: T06
role: 工具研究 Agent
created: 2026-10-15
write_scope: 02-工具/pi/证据/
snapshot: b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb
format: 任务书 §4.4
link_base: https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/
---

# pi · 证据卡

> 格式遵循任务书 §4.4。结论ID 规则 `pi-<mechanism>-<number>`。
> 链接基址：`https://github.com/earendil-works/pi/blob/b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb/`（路径后加 `#L起-L止`）。
> **性质栏**：事实 / 推断 / 建议。**实现状态栏**：默认 / 条件 / 实验 / 桩或空实现 / 未证实。
> **凡无实测处**：运行证据一律 `NOT_RUN + 原因`，不得把源码阅读写成实验通过。
> 术语统一沿用 `00-管理/术语表.md` 与 T02 §E（触发线、替代历史、持久化断点、出口限长、落盘…）。

---

## A. 请求组装与规则（assembly / rule / retrieval）

```yaml
结论ID: pi-assembly-01
结论: 一次请求由「规范化会话投影 projection.messages（compaction 已应用）+ 工具实现 tools」拼成；投影由 buildSessionProjection() 生成，不是直接用内存消息数组
性质: 事实
范围: 快照 b45e0eb；packages/coding-agent；默认
实现状态: 默认
来源: packages/coding-agent/src/core/agent-session.ts#L788-845；core/session-manager.ts#L543-573
数据走查: DW-assembly-01
运行证据: NOT_RUN + 原因：需 T03 合成任务数据 + 真实模型运行（本轮入口被陈旧锁阻塞，见 过程观察.md）
不能证明: 不证明 provider 端如何进一步加工该请求体
冲突裁决: 无旧结论；回答 CM-01
核验日期: 2026-10-15
```

```yaml
结论ID: pi-assembly-02
结论: 系统提示词按可独立替换的具名 section 组织（preamble/tools/rules/docs/project_context/skills/cwd/自定义），每段包 <同名标签>；diffSystemPromptSections() 只把变化段作为补丁追加
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/system-prompt.ts#L128-193（section 组装）、#L217-229（差分）
数据走查: DW-assembly-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明该差分在具体 provider 上的缓存命中率（属 T19）
冲突裁决: 支持"请求组装与角色"（CM-01）；为 CM-12 前缀稳定提供机制线索
核验日期: 2026-10-15
```

```yaml
结论ID: pi-rule-01
结论: 项目规则文件按候选名 AGENTS.override.md→AGENTS.md→CLAUDE.md 发现；范围=agent 目录（全局）+ cwd 祖先链逐级向上，并排除被 worktree 遮蔽的重复项
性质: 事实
范围: 快照 b45e0eb；默认（--no-context-files 可关）
实现状态: 默认
来源: packages/coding-agent/src/core/resource-loader.ts#L184-274；core/system-prompt.ts#L79-86,173
数据走查: DW-rule-01
运行证据: NOT_RUN + 原因同上
不能证明: 不证明不同项目的规则字节预算/截断策略（pi 未见类似 32KiB 共享预算常量）
冲突裁决: 无旧结论；回答 CM-02；与 Claude Code/Codex 的"字节预算"做法不同（pi 未设该常量）
核验日期: 2026-10-15
```

```yaml
结论ID: pi-rule-02
结论: 技能走渐进式披露——提示词只放技能名+一句描述；完整手册按需再读
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/skills.ts#L358；docs/how-pi-works.md（"Full skill instructions are loaded on demand."）
数据走查: DW-rule-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明"按需读"在具体模型上是否真的会触发
冲突裁决: 支持术语表"技能（渐进式披露）"；回答 CM-02
核验日期: 2026-10-15
```

```yaml
结论ID: pi-retrieval-01
结论: 资料按需检索：read/grep/find/ls 工具；read 支持 offset/limit 分页续读，不整块装填
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/tools/read.ts#L96,168-192；tools/grep.ts；tools/find.ts；tools/ls.ts
数据走查: DW-retrieval-01
运行证据: NOT_RUN + 原因同上
不能证明: 不证明检索质量或选择策略优劣
冲突裁决: 回答 CM-03（pi 侧"全量装填 vs 按需检索"选按需）
核验日期: 2026-10-15
```

## B. 工具输出治理（trunc）

```yaml
结论ID: pi-trunc-01
结论: 工具输出两条独立上限——2000 行 / 50KB，先到者胜；read/grep/find/ls 保头(truncateHead)，bash 保尾(truncateTail)；不返回半行；grep 单行上限 500 字符
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/tools/truncate.ts#L11-13,78-160,168-241
数据走查: DW-trunc-01
运行证据: NOT_RUN + 原因：需 T03（本地也可直接重放 truncate 函数，但属静态走查非模型实验）
不能证明: 不证明"对中文保守"的普适性（chars/4 类估算的范围限制）
冲突裁决: 支持术语表"出口限长/头尾裁剪"；回答 CM-04
核验日期: 2026-10-15
```

```yaml
结论ID: pi-trunc-02
结论: bash 超限时全量原文落临时文件，请求里只留尾部预览 + "[Showing lines X-Y of N (50.0KB limit). Full output: <path>]"；output-accumulator 用 maxBytes*2 滚动缓冲，超大读回保首尾各半
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/tools/bash.ts#L333-355；tools/output-accumulator.ts#L58-60,92-107,149-160
数据走查: DW-trunc-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明临时文件的存活期与清理时机在长会话中的行为
冲突裁决: 回答 CM-04 + CM-07 的"能否找回原文"（文件层可找回）
核验日期: 2026-10-15
```

## C. 窗口计量与触发（trigger）

```yaml
结论ID: pi-trigger-01
结论: 唯一阈值线 shouldCompact = contextTokens > contextWindow − reserveTokens；默认 reserveTokens=16384、keepRecentTokens=20000、enabled=true（settings 可覆盖，支持按模型 modelOverrides）
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/compaction/compaction.ts#L126-130,267-270；core/settings-defaults.ts#L9-13；core/settings-manager.ts#L861-880
数据走查: DW-trigger-01
运行证据: NOT_RUN + 原因：需 T03
不能证明: 不证明 200K 窗口下触发点"实测"值（183,616 为教学换算）
冲突裁决: 支持学习笔记 liú 0.85.1 "contextWindow − 16_384" 的说法（1.2.0 仍成立）；限制"pi 无独立硬顶/不扣有效窗口"仅就"不拆两笔预留"而言成立
核验日期: 2026-10-15
```

```yaml
结论ID: pi-trigger-02
结论: 用量优先取最近一条有效 assistant 的 usage（totalTokens 或 input+output+cacheRead+cacheWrite），其后用 ceil(chars/4) 估算；usage 早于最近一次 context_edit/compaction 时全量重估
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/compaction/compaction.ts#L140-262,298-349
数据走查: DW-trigger-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明 chars/4 对各种分词器的偏差幅度
冲突裁决: 回答 CM-05（计量口径）
核验日期: 2026-10-15
```

```yaml
结论ID: pi-trigger-03
结论: 自动触发共三处时机——轮中(prepareNextTurn)、新用户提示前(_prepareRun)、运行结束后(_handlePostAgentRun)；外加 provider 溢出/length 的一次性恢复路径
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/agent-session.ts#L777-786,905-906,1893-1896,1974,2977-3114
数据走查: DW-trigger-03
运行证据: NOT_RUN + 原因同上
不能证明: 不证明"到线"在真实长任务中的实际触发次数
冲突裁决: 支持学习笔记 pi 0.85.1 "pre-turn ✅ / mid-turn ✅"的说法；pi 未含"模型切换触发"
核验日期: 2026-10-15
```

## D. 压缩与摘要（compact / summary）

```yaml
结论ID: pi-compact-01
结论: 自动与手动两条入口都经 prepareCompaction() + session_before_compact 钩子，再调底层 compact()；手动 /compact 会先 abort 当前操作且不重试
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/agent-session.ts#L2749-2939（手动）、#L3117-3274（自动）
数据走查: DW-compact-01
运行证据: NOT_RUN + 原因同上
不能证明: 不证明手动/自动在真实会话中的效果差异
冲突裁决: 回答 CM-06
核验日期: 2026-10-15
```

```yaml
结论ID: pi-summary-01
结论: 摘要提示词为固定结构（Goal / Constraints & Preferences / Progress(Done/In Progress/Blocked) / Key Decisions / Next Steps / Critical Context + <read-files>/<modified-files>）；有旧摘要时改用 UPDATE 提示词做增量合并（PRESERVE+ADD）
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/compaction/compaction.ts#L507-538（格式）、#L540-579（增量）、#L730-733；core/compaction/utils.ts#L67-87
数据走查: DW-summary-01
运行证据: NOT_RUN + 原因同上
不能证明: 不证明增量更新"不丢事实"（连续三次压缩的实验属 T19/LQ-09、FB-11）
冲突裁决: 回答 CM-07；为 C-04（旧摘要是否无损）提供"结构性增量、但判为有损"的定位，具体失真待实验
核验日期: 2026-10-15
```

```yaml
结论ID: pi-summary-02
结论: 切点走在 user/assistant/bashExecution/custom/branchSummary 边界，绝不切在 toolResult；从最新往回累加到 keepRecentTokens(20000) 取最接近合法切点；单用户跨度超预算则 split turn 生成两份摘要再合并
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/compaction/compaction.ts#L351-364（切点判定）、#L446-501,802-870（算法）、#L994-1033（split 合并）
数据走查: DW-summary-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明"20k 保留"在真实会话中留下的具体条目数
冲突裁决: 回答 CM-07；术语表"直接保留预算"对 pi 记为 keepRecentTokens(20000)
核验日期: 2026-10-15
```

```yaml
结论ID: pi-summary-03
结论: 摘要序列化把 toolResult 截到 2000 字符、省略 thinking 块；摘要生成 maxTokens=min(floor(0.8*reserveTokens),模型上限)，split 的 turn-prefix 用 0.5*reserveTokens
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/compaction/utils.ts#L94,120-155,114-118；core/compaction/compaction.ts#L712-715,1090-1093
数据走查: DW-summary-03
运行证据: NOT_RUN + 原因同上
不能证明: 不证明"省略 thinking"对摘要保真的净影响
冲突裁决: 与样章/术语表"摘要 prompt 也会占上下文"一致（摘要本身是另一次带预算的调用）
核验日期: 2026-10-15
```

```yaml
结论ID: pi-summary-04
结论: compaction 条目在投影里表现为一条 user 消息（内容 <summary>…</summary> 包前后缀）；CompactionEntry 还保存 systemMessage（压缩边界处完整提示词/工具状态）
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/messages.ts#L11-17,62-67,148-196；core/session-manager.ts#L91-104,439-466,1270-1284
数据走查: DW-summary-04
运行证据: NOT_RUN + 原因同上
不能证明: 不证明模型对"user 角色摘要"与"system 角色摘要"的等效性
冲突裁决: 回答 CM-07/CM-01 的角色问题
核验日期: 2026-10-15
```

```yaml
结论ID: pi-summary-05
结论: 轻量替代 context_edit：append-only 的条目编辑，replacement=null 表示从模型上下文省略目标条目，值表示只替换内容；只改投影不改磁盘原始条目
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/session-manager.ts#L175-180,519-540,1360-1371；core/agent-session.ts#L1252
数据走查: DW-summary-05
运行证据: NOT_RUN + 原因同上
不能证明: 不证明哪些 UI/命令会自动产生 context_edit（除溢出恢复省略外）
冲突裁决: 回答 CM-07 的"移除"手段
核验日期: 2026-10-15
```

## E. 记忆与子 Agent（memory / cm09）

```yaml
结论ID: pi-memory-01
结论: pi 默认不含独立"长期记忆/会话记忆"机制——快照内未发现后台抽取/记忆重注入实现（性质＝推断）；跨会话信息由 AGENTS.md（静态项目规则）或扩展承担
性质: 推断（基于在原生快照内检索零命中；不写"没有实现"）
范围: 快照 b45e0eb；packages/coding-agent + packages/agent
实现状态: 未发现默认实现（推断；可由扩展实现）｜非 UNOBSERVABLE（源码可读、检索已做）
来源: 全仓检索 `long-term memory|memory re-injection|background extraction|memories` 零命中；packages/coding-agent/src + packages/agent/src；官方 docs/how-pi-works.md 未列长期记忆
数据走查: —
运行证据: NOT_RUN + 原因：该主张是"未发现"而非"运行否证"；无需模型运行
不能证明: 不能证明第三方扩展未实现类似能力（属"扩展行为"，非默认）；也不排除未来版本加入
冲突裁决: 回答 CM-08（pi 默认无）；按纪律②③给"查的路径/凭什么/官方怎么说"，见 过程观察.md §5
核验日期: 2026-10-15
```

```yaml
结论ID: pi-cm09-01
结论: CM-09（子 Agent 交接）对 pi **不适用**——pi 刻意不含 sub-agents（README 明示"skips features like sub-agents and plan mode"；**主仓**源码无内建子代理生成/交接/分叉协议，仓库**随附** `packages/coding-agent/examples/extensions/subagent/` 示例扩展，属**扩展层**）
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 不适用（刻意不含）
来源: README.md（"Pi ships with powerful defaults but skips features like sub-agents and plan mode"）；**主仓**检索无内建 subagent 实现（仅工具内部 "delegate to remote systems" 注释，与子代理无关）；仓库**随附** `packages/coding-agent/examples/extensions/subagent/` 示例扩展（README：delegate tasks to specialized subagents with isolated context windows），属**扩展层**、非默认核心
数据走查: —
运行证据: NOT_RUN + 原因：机制刻意不存在
不能证明: 不证明扩展生态里无第三方子代理（属"扩展行为"）
冲突裁决: 与 T02 §G / §C 注记一致（CM-09 pi：不适用，如实说明而非"未找到"）
核验日期: 2026-10-15
```

## F. 保存 / fork / 恢复（persist / recover）

```yaml
结论ID: pi-persist-01
结论: 会话=只追加 JSONL 树（每行一条目，按 id/parentId 成树，版本 3）；压缩只追加 CompactionEntry，不删除任何原始条目
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/session-manager.ts#L41,1172-1196,1261-1287；docs/sessions.md（"It does not delete the original session entries."）
数据走查: DW-persist-01
运行证据: NOT_RUN + 原因：需 T03（另见 过程观察.md 观察到 session 头 JSON）
不能证明: 不证明会话文件的清理/轮转策略
冲突裁决: 支持 C-03/C-12："摘要不可逆 ≠ 源记录被删除"
核验日期: 2026-10-15
```

```yaml
结论ID: pi-recover-01
结论: 恢复属"持久化断点"路线（路线 B）：压缩产物（summary + firstKeptEntryId）已持久化，恢复时按当前分支投影重建（摘要 + 保留段 + 后续条目），不重放全部历史重算
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/session-manager.ts#L476-512（buildContextEntries）、#L543-573（投影）、#L1766-1801（open/continueRecent）；docs/how-pi-works.md（"Compaction inserts a summary entry that replaces older messages in subsequent model requests."）
数据走查: DW-recover-01
运行证据: NOT_RUN + 原因：需 T03
不能证明: 不证明"被压掉细节"在模型可见层永不恢复（人工读文件除外）
冲突裁决: **裁决 LQ-10（pi 侧）= 持久化断点**；支持 C-03/C-12 部分裁决（模型可见不可逆 / 文件层可找回）
核验日期: 2026-10-15
```

## G. 失败与副作用（fail）

```yaml
结论ID: pi-fail-01
结论: 溢出恢复只允许一次 compact-and-retry（_overflowRecoveryAttempted）；摘要生成遇 stopReason=error 或 length 即失败，禁止半截摘要落盘；摘要调用尝试调工具也判失败
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/agent-session.ts#L3007-3074,3242-3266；core/compaction/compaction.ts#L585-593,755-761
数据走查: DW-fail-01
运行证据: NOT_RUN + 原因：需 T03 失败注入
不能证明: 不证明"一次恢复"对最终任务成功率的净影响
冲突裁决: 支持学习笔记 pi 0.85.1 "overflow 三态检测 + 重试一次""熔断 重试仅 1 次"
核验日期: 2026-10-15
```

```yaml
结论ID: pi-fail-02
结论: 压缩只在成功后 appendCompaction（无半提交）；失败/取消不追加 compaction、不安排内部重试，仅保留已发生的 omission 编辑；瞬时流错误走 retryAssistantCall（默认 maxRetries=3）
性质: 事实
范围: 快照 b45e0eb；默认
实现状态: 默认
来源: packages/coding-agent/src/core/agent-session.ts#L2873-2875,3207,3242-3266；core/compaction/compaction.ts#L619-639；core/settings-defaults.ts（retry.maxRetries=3）
数据走查: DW-fail-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明"成功后一次性提交"对账单的具体影响
冲突裁决: 回答 CM-11；为"幂等与重复执行"提供机制线索
核验日期: 2026-10-15
```

## H. 缓存与成本（cache）

```yaml
结论ID: pi-cache-01
结论: 摘要请求显式 cacheRetention:"none"（不写缓存）；会话侧默认 cacheWarming:"streaming"——用单 token 输出上限重发以保活缓存条目，且有成本阈值($0.05)；cache-stats 以 5 分钟 TTL 统计命中浪费；窗口用量口径含 cacheRead/cacheWrite
性质: 事实
范围: 快照 b45e0eb；会话侧缓存预热为默认；服务端缓存行为不可由源码核实
实现状态: 默认（CLI 侧）；服务端命中率/TTL 不可证
来源: packages/coding-agent/src/core/compaction/compaction.ts#L629-633；core/cache-warmer.ts#L13-21,134-160；core/cache-stats.ts#L6-8；core/settings-defaults.ts（cacheWarming:"streaming"）
数据走查: DW-cache-01
运行证据: NOT_RUN + 原因：服务端命中/TTL 不可由本地源码核实，需 T19
不能证明: ❌不证明命中率；❌不证明预热是否真的省钱（依赖服务端 TTL 与真实到达率）
冲突裁决: 回答 CM-12；pi 与 Codex 的"发缓存键"做法不同——pi 侧重"预热 + 统计"
核验日期: 2026-10-15
```

## I. 扩展点（ext）

```yaml
结论ID: pi-ext-01
结论: session_before_compact 钩子可取消压缩或提供自定义摘要（含 firstKeptEntryId/tokensBefore/usage/details），并能读到 preparation（messagesToSummarize/previousSummary/fileOps/settings）与 reason/willRetry；session_compact(_failed) 供观测
性质: 事实
范围: 快照 b45e0eb；扩展态（需装扩展）
实现状态: 条件（需装扩展）
来源: packages/coding-agent/src/core/extensions/types.ts#L785-821；docs/compaction.md（"Custom Summarization via Extensions"）
数据走查: DW-ext-01
运行证据: NOT_RUN + 原因：需真实扩展 + T03
不能证明: 不证明具体第三方扩展的实现质量
冲突裁决: 回答"扩展能改什么"（摘要层）
核验日期: 2026-10-15
```

```yaml
结论ID: pi-ext-02
结论: context / context_with_system 可在每次 LLM 调用前改写消息（后者含 system、处理器拥有 prompt 与工具声明）；before_provider_request 可替换最终 payload；before_agent_start 可改 systemPromptOptions/注入消息/切工具集；扩展还可注册 tool/command/provider/renderer
性质: 事实
范围: 快照 b45e0eb；扩展态
实现状态: 条件（需装扩展）
来源: packages/coding-agent/src/core/extensions/types.ts#L885-904,932-958；docs/how-pi-works.md（"Extensions and resources"）
数据走查: DW-ext-02
运行证据: NOT_RUN + 原因同上
不能证明: 不证明扩展改动对缓存前缀的影响
冲突裁决: 回答"扩展能改什么"（请求层）；默认不含 sub-agents/plan mode/长期记忆
核验日期: 2026-10-15
```

## J. 旧版本结论裁决（0.85.1 → 1.2.0）

```yaml
结论ID: pi-version-01
结论: 学习笔记 §5 对 pi 0.85.1 的阈值说法「响应预留 contextWindow − 16_384」在快照 1.2.0 仍成立（reserveTokens 默认 16384）；但"设置项名 reserve/keep"确认为 settings.json 的 compaction.reserveTokens / keepRecentTokens
性质: 事实
范围: 快照 b45e0eb（1.2.0）vs 学习笔记 0.85.1 说法
实现状态: 默认
来源: packages/coding-agent/src/core/compaction/compaction.ts#L126-130；core/settings-defaults.ts#L9-13；docs/compaction.md（Settings 表）
数据走查: DW-trigger-01
运行证据: NOT_RUN + 原因：需 T03
不能证明: 不证明 0.85.1 内部实现细节（未取得 0.85.1 源码，无法逐行比对）
冲突裁决: **维持**阈值常量结论；**限制**"无独立硬顶"——pi 确实不拆两笔预留，但仍有 reserve 这一"软顶"
核验日期: 2026-10-15
```

```yaml
结论ID: pi-version-02
结论: 学习笔记 §4「Pi：read 保头 / bash 保尾」在 1.2.0 仍成立（read→truncateHead，bash→truncateTail）
性质: 事实
范围: 快照 b45e0eb（1.2.0）vs 学习笔记 0.85.1 说法
实现状态: 默认
来源: packages/coding-agent/src/core/tools/read.ts#L12,177；tools/bash.ts#L20,342-353
数据走查: DW-trunc-01
运行证据: NOT_RUN + 原因：需 T03
不能证明: 不证明 0.85.1 的具体阈值（本次只核到 1.2.0 的 2000 行/50KB）
冲突裁决: **维持**该说法
核验日期: 2026-10-15
```

```yaml
结论ID: pi-version-03
结论: 学习笔记 §10「pi 属持久化断点、被压掉的细节 resume 找不回」在 1.2.0 成立（模型可见层）；但"绝不可能找回"应限制为**模型可见层**，磁盘原始条目仍在，人工可读
性质: 事实
范围: 快照 b45e0eb（1.2.0）vs 学习笔记 §10
实现状态: 默认
来源: packages/coding-agent/src/core/session-manager.ts#L476-512,1261-1287；docs/sessions.md,how-pi-works.md
数据走查: DW-recover-01
运行证据: NOT_RUN + 原因：需 T03
不能证明: 不证明 UI 是否提供"回看被压段落"的入口
冲突裁决: **维持**路线判定；**限制**"绝不可能找回"（对应 C-12）
核验日期: 2026-10-15
```

---

## 附：结论ID 一览

| 族 | 结论ID | 一句话 |
|---|---|---|
| assembly | pi-assembly-01/02 | 投影+工具拼请求；系统提示词按 section 差分 |
| rule | pi-rule-01/02 | AGENTS.md 祖先链发现；技能渐进式披露 |
| retrieval | pi-retrieval-01 | read/grep/find/ls 按需 + read 分页 |
| trunc | pi-trunc-01/02 | 2000 行/50KB 先到者；bash 超限落盘 |
| trigger | pi-trigger-01/02/03 | A>W−16384；usage 优先+chars/4；三时机触发 |
| compact | pi-compact-01 | auto/manual 共用底层 compact() |
| summary | pi-summary-01..05 | 结构化摘要+增量；切点不绝于 toolResult；序列化截断；user 角色摘要；context_edit |
| memory | pi-memory-01 | 默认无长期记忆 |
| cm09 | pi-cm09-01 | 子 Agent 不适用（刻意不含） |
| persist | pi-persist-01 | 追加式 JSONL 树，不删原条目 |
| recover | pi-recover-01 | 持久化断点路线（LQ-10 裁决） |
| fail | pi-fail-01/02 | 溢出仅一次恢复；成功才提交 |
| cache | pi-cache-01 | 摘要禁写缓存；缓存预热默认开 |
| ext | pi-ext-01/02 | 钩子改摘要/请求；默认不含扩展能力 |
| version | pi-version-01/02/03 | 旧结论逐条裁决 |
