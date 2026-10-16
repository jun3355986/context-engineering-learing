---
title: deepseek-harness · 证据卡
task: T13
role: 工具研究 Agent
created: 2026-10-15
snapshot: 571902028a75c64c1d767f4ae5fd099485f0ddf0
spec: 08-验收/T07-后六工具样本规范.md
---

# deepseek-harness · 证据卡（`dsh-*`）

> **格式**：逐卡 7+ 字段（结论ID / 结论 / 性质 / 范围 / 实现状态 / 来源 / 数据走查 / 运行证据 / **不能证明** / 冲突裁决 / 核验日期）。
> **固定 SHA 链接基址**：`https://github.com/deepseek-ai/deepseek-harness/blob/571902028a75c64c1d767f4ae5fd099485f0ddf0/<path>#L起-L止`（下表"来源"列只写 `<path>#L…`，前缀同此）。
> **三类角标**：【源码常量】= 固定快照真实常量；【演示】= 教学假设；【测试样本】= 仓库自带测试值（未运行）。
> **高风险主张**（阈值/默认开关/持久化/二次压缩/缓存）：清单见 `问题与审查.md` §8.1（7 项）；**已由 T13R 独立复核通过**（2026-10-15）。

## 附表：卡族与数量

| 族 | ID 前缀 | 数量 |
|---|---|---|
| 身份/版本/装配 | `dsh-version-*` | 3 |
| 请求组装 | `dsh-assembly-*` | 2 |
| 规则/技能 | `dsh-rule-*` | 2 |
| 检索 | `dsh-retrieval-*` | 2 |
| 工具输出治理 | `dsh-trunc-*` | 4 |
| 计量与触发 | `dsh-trigger-*` | 2 |
| 压缩入口 | `dsh-compact-*` | 2 |
| 摘要/重建 | `dsh-summary-*` | 3 |
| 长期记忆 | `dsh-memory-*` | 1 |
| 子 Agent 交接 | `dsh-cm09-*` | 2 |
| 持久化 | `dsh-persist-*` | 3 |
| 恢复 | `dsh-recover-*` | 1 |
| 错误与副作用 | `dsh-fail-*` | 3 |
| 缓存 | `dsh-cache-*` | 2 |
| 分层（harness vs 模型） | `dsh-layer-*` | 1 |
| 扩展（图像离载） | `dsh-ext-*` | 1 |
| **合计** | | **34** |

---

## 1. 身份 / 版本 / 装配

```yaml
结论ID: dsh-version-01
结论: deepseek-harness 是 DeepSeek AI 的开源 agent harness，CLI 命令名为 `dsh`，口号「AGENT = MODEL + HARNESS」；本包研究对象为 master 开发快照 571902028a75c64c1d767f4ae5fd099485f0ddf0（2026-10-14 21:15:15 +0800）。
性质: 事实
范围: 产品入口 CLI（`dsh`）；快照 `5719020…`（master）；未指定模型/provider/配置
实现状态: 默认
来源: README.md#L1-10；版本表.md §1/§2；开工 `git rev-parse HEAD` = 571902028a75c64c1d767f4ae5fd099485f0ddf0（与版本表 §2 一致）
数据走查: —
运行证据: NOT_RUN（本机未安装 dsh；版本表 §3 记「未安装」）
不能证明: 不能证明发行版（npm `@deepseek-ai/dsh`）与快照为同一份代码；不能证明端到端产品行为（未运行）。release 口径「27 个全 prerelease、无 stable」来自版本表，未在本包独立复核。
冲突裁决: 支持 T01 身份结论（`deepseek-ai/deepseek-harness` / `dsh` / 口号）；不改变版本表任何行。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-version-02
结论: dsh 的默认上下文能力由 bundle `@deepseek-ai/dsh-base` 决定——默认装配 token-meter、compaction-basic、command-compact、tool-result-pruner(8192/4096/1024)、spill-policy(maxInlineTokens:12500)、agent-instructions(maxBytes:65536)、skill/skill-filesystem/tool-skill、subagent 家族、session-persistence-jsonl、session-checkpoint-policy、compaction-image-offload。
性质: 事实
范围: `dsh-base` 装配（web/headless/sdk/acp profile 共享）；快照 `5719020…`
实现状态: 默认
来源: packages/bundle/base/cordis.patch.yml#L303-306（agent-instructions）、#L311-315（skill/tool-skill）、#L348-357（token-meter/compaction-basic/command-compact）、#L359-395（subagent 家族）、#L411-417（spill-local/spill-policy:12500）、#L420-430（session-checkpoint-policy/tool-result-pruner:8192/4096/1024）、#L434-435（image-offload）；bundle/base/README.md
数据走查: DW-rule-01、DW-trunc-02、DW-trunc-03
运行证据: NOT_RUN（未运行 dsh；仅读装配文件）
不能证明: 不能证明运行时实际生效值等于声明值（HMR/用户 profile patch 可覆盖）；不能证明 web/desktop profile 与 headless 完全一致（本包只核 base bundle 行）。**默认 vs 扩展分列**见工具概览 §4。
冲突裁决: 无旧结论冲突；为 CM-04/CM-05/CM-06/CM-10 提供"默认装配"依据。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-version-03
结论: PyPI 包 `deepseek-harness-sdk` 确实存在（**pre-release**，检索日页面为 0.1.5rc1），是**驱动 dsh 的 Python 子进程 SDK**：`pip install deepseek-harness-sdk` 会同时装同版本 `deepseek-harness-runtime-bin`（内含 `dsh` 可执行文件），通过 stdio 上的换行分隔 JSON-RPC 启动 `dsh --profile sdk`。它与 CLI 是**同一 harness 的不同入口**，非另一实现。
性质: 事实
范围: PyPI `deepseek-harness-sdk`；仓库内 `python/sdk/`（快照 `5719020…`）
实现状态: 默认（SDK 包）/ 实验（pre-release 通道）
来源: PyPI https://pypi.org/project/deepseek-harness-sdk/ （检索 2026-10-15）；快照 `python/sdk/README.md#L1-12,34-60`；`python/sdk-runtime/` 目录存在
数据走查: —
运行证据: NOT_RUN（未 pip 安装；仅官方页面 + 仓库内 README）
不能证明: 不能证明本机可安装性/平台 wheel 匹配；不能证明 SDK 的**上下文机制**与 CLI 默认装配一致（SDK 用 `--profile sdk`，其 composition 需单独核，本包未展开）；不能证明 0.1.5rc1 与快照同源（页面版本线独立）。
冲突裁决: **补核交接 §5 Q7 / 版本表 §4 Q6**——存在性=是；与 CLI 关系=同 harness 的 Python 子进程封装（`--profile sdk`）；**引用纪律**：正文引用 SDK 行为时须标「PyPI pre-release + `--profile sdk`」，不得写成「CLI 默认」。
核验日期: 2026-10-15
```

## 2. 请求组装与角色

```yaml
结论ID: dsh-assembly-01
结论: 每次请求 = `header.config` + `deriveMessages()` + `header.tools`，**不含 `system` 字段**；系统提示词由 `system/message` 节点承载，取最新非空者；工具增删通过对比前后 header 发一条 `developer/message`。
性质: 事实
范围: agent-loop 请求派生；快照 `5719020…`；默认装配
实现状态: 默认
来源: packages/core/agent-loop/README.md#L75（"sends derived history … latest non-empty system/message node as the effective prompt"）、#L120（"The request is header.config, deriveMessages(), and header.tools; it carries no system field"）、#L156（developer/message for tool additions/removals）
数据走查: DW-assembly-01
运行证据: NOT_RUN（未运行 dsh；README 与源码结构一致）
不能证明: 不能证明具体 wire 序列化细节（属适配器 `serialize.ts`，本包未逐行）；不能证明无第三方 profile patch 改变组装（本机无运行）。
冲突裁决: 无旧结论冲突；为 CM-01 主判定依据。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-assembly-02
结论: 系统提示词在能力路由/新请求序列下**合并到首个 system 节点**（后续非空 system 节点写逐节点空替换）；声明 `systemPromptUpdate: in-history` 的路由（默认 `deepseek-flash`）把**变更提示词追加在缓存历史之后**，保住前缀复用。
性质: 事实
范围: agent-loop reconciliation；适配器能力声明；快照 `5719020…`
实现状态: 默认（含条件分支：`in-history` 路由）
来源: packages/core/agent-loop/README.md#L122,164；packages/llm/llm-deepseek/README.md#L53,85,181（`systemPromptUpdate: in-history`，默认 `deepseek-flash` 声明）
数据走查: DW-assembly-01
运行证据: NOT_RUN（未运行；未做缓存命中实测）
不能证明: 不能证明服务端真的复用了前缀（KV cache 命中 = 服务端 UNOBSERVABLE）；不能证明非 `deepseek-flash` 模型的默认行为（需显式 `models` 声明）。
冲突裁决: 支持"缓存 = 前缀复用机制"的通用叙述；**限制**：dsh 侧只能保证"前缀字节不变"，命中由 provider 决定。
核验日期: 2026-10-15
```

## 3. 项目规则 / 技能加载

```yaml
结论ID: dsh-rule-01
结论: `agent-instructions` 加载用户全局（`$DSH_HOME/AGENTS.md`、`<agentsHome>/AGENTS.md`）与项目链（项目根→会话工作目录，宽→窄）的 `AGENTS.md`/`CLAUDE.md` 等文件，作为**一条 durable `user/message`**；默认装配 `maxBytes: 65536` 字节；预算内**先丢宽泛文件、再截断最具体文件**，并输出可见的 "Workspace instruction budget …" 通知；按内容摘要去重。
性质: 事实
范围: `agent-instructions`；快照 `5719020…`；`dsh-base` 默认装配
实现状态: 默认
来源: packages/context/agent-instructions/README.md#L12,30,34,38,64,74；packages/bundle/base/cordis.patch.yml#L303-306
数据走查: DW-rule-01
运行证据: NOT_RUN（未运行 dsh；未复现字节截断）
不能证明: 不能证明 `maxBytes` 截断的具体边界（"先丢宽泛/后截最具体"的多文件组合行为未实测）；不能证明符号链接/权限失败时的确切渲染（README 有描述但未运行）。
冲突裁决: 无旧结论冲突；术语表 §8"字节预算/发现范围"在 dsh 侧**成立**（有硬常量 65536）。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-rule-02
结论: 技能为**渐进式披露**：`skill-filesystem` 从 5 档根（rank 100 `project-dsh`、200 `project-agents`、300 custom、400 `user-dsh`、500 `user-agents`；可加 rank 600 bundled）发现 `<name>/SKILL.md` 或 `<name>.md`；`tool-skill` 在首个请求前发**一条 durable `user/message` 目录**（名字 + 截断描述，`catalogDescriptionMaxLength` 默认 **500**），模型用 `skill` 工具按名加载**全文**。
性质: 事实
范围: `skill`/`skill-filesystem`/`tool-skill`；快照 `5719020…`；默认装配
实现状态: 默认
来源: packages/skill/skill-filesystem/README.md#L46-56,109；packages/skill/tool-skill/README.md#L48,54-57,110-133；cordis.patch.yml#L311-315
数据走查: DW-rule-01
运行证据: NOT_RUN（未运行 dsh；未做技能目录刷新实测）
不能证明: 不能证明目录刷新在真实 IDE/Git 变更下的时延（README 述 Chokidar depth 1 + 缺失根轮询）；不能证明加载的**技能正文体量**上限（README 明示"Loaded instruction bodies have no size cap"）。
冲突裁决: 无旧结论冲突；术语表 §8"技能（渐进式披露）"在 dsh 侧成立。
核验日期: 2026-10-15
```

## 4. 资料选择与代码检索

```yaml
结论ID: dsh-retrieval-01
结论: dsh 走**按需检索**：`read`/`read_image`/`write`/`edit`（`tool-fs`）+ `grep`/`glob`（`tool-fs-search`）；`@file` 提及（`file-reference`）**只做路径补全，不附内容**——模型必须再调 fs 工具才能看内容。
性质: 事实
范围: `tool-fs`/`tool-fs-search`/`file-reference`；快照 `5719020…`
实现状态: 默认
来源: packages/fs/tool-fs/README.md#L12,48；packages/context/file-reference/README.md#L12（"Selecting a candidate never reads or attaches file contents"）
数据走查: DW-retrieval-01
运行证据: NOT_RUN（未运行 dsh）
不能证明: 不能证明模型实际检索策略（属模型行为）；不能证明全量装填路径**不存在**（仅证明官方 README 未描述全量装填）。
冲突裁决: 无旧结论冲突；为 CM-03 依据。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-retrieval-02
结论: `session-reference`（**opt-in**）支持把**其他会话**作为**有界只读快照**注入为**第二条 user 角色消息**（`## Referenced sessions`），带固定"不可信背景"警告；每源有界：`maxReferences` 默认 **3**、`referenceContextFraction` 默认 **0.2**、自动预算 `max(65536, floor(contextWindow×4×0.2))` 字节/源。
性质: 事实
范围: `session-reference`；快照 `5719020…`；**非默认装配**（opt-in）
实现状态: 条件（需 host 支持跨会话提及并挂载）
来源: packages/context/session-reference/README.md#L12,36,48-53；packages/context/README.md#L12（"Only agent-instructions ships mounted by default; the rest are opt-in"）
数据走查: DW-retrieval-02
运行证据: NOT_RUN（未运行 dsh；未做跨会话提及）
不能证明: 不能证明快照在真实多会话下的检索质量/排序效果；不能证明预算公式在非 1M 窗口下的边界（公式为 README 文本，未运行）。
冲突裁决: 无旧结论冲突；为 CM-03/CM-08 的"外部记忆"边界提供依据（跨会话引用是**显式提及**，非自动记忆）。
核验日期: 2026-10-15
```

## 5. 单条工具输出治理

```yaml
结论ID: dsh-trunc-01
结论: `read` 工具自带三重上限：`readLimit` 默认 **2000 行**、`readMaxLineLength` 默认 **2000 字符/行**、`readMaxBytes` 默认 **51200 字节/次**（超出以 capped footer 结束窗口）；`readStreamMinSize` 默认 **10485760 字节**（≥此值流式读，不整体载入内存）。
性质: 事实
范围: `tool-fs`；快照 `5719020…`；默认装配
实现状态: 默认
来源: packages/fs/tool-fs/README.md#L65-68,195
数据走查: DW-trunc-01
运行证据: NOT_RUN（未运行 dsh；未构造超限文件）
不能证明: 不能证明超限时的**确切 footer 文本**（README 未给逐字串）；不能证明这些上限在 Web/Desktop 客户端一致（本包只核包文档）。
冲突裁决: 无旧结论冲突；为 CM-04 依据（工具侧第一层限长）。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-trunc-02
结论: 持久 bash 工具（`tool-bash-persistent`）以 `maxOutputChars` 默认 **16,000 字符**保留命令输出；长输出保留**最早的前缀**加剪裁通知；固定诊断（剪裁/丢前缀/状态/超时/重置）在限额后**另加**。
性质: 事实
范围: `tool-bash-persistent`（macOS/Linux 默认 shell 栈）；快照 `5719020…`
实现状态: 默认
来源: packages/shell/tool-bash-persistent/README.md#L50,130,134
数据走查: DW-trunc-01
运行证据: NOT_RUN（未运行 dsh；未跑长输出命令）
不能证明: 不能证明 Windows（pwsh 栈）数值相同（本包只核 bash 行）；不能证明"最早前缀"在 PTY 已丢弃前缀时的确切降级文本。
冲突裁决: 无旧结论冲突；为 CM-04 依据。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-trunc-03
结论: `spill-policy`（默认装配 `maxInlineTokens: 12500`）把超预算的**文本/图像结果**替换为**有序头/尾预览 + 省略通知 + 全文落盘路径**；省略通知含被省字节数、可选整图计数、`read`/`grep` 找回指引；**存储失败则保留原文**（best-effort）。省略 `maxInlineTokens` 即**关闭**落盘。
性质: 事实
范围: `spill-policy`+`spill-local`；快照 `5719020…`；`dsh-base` 默认 `12500`
实现状态: 默认
来源: packages/spill/spill-policy/README.md#L12,43,49-57,63-65；cordis.patch.yml#L411-417
数据走查: DW-trunc-02
运行证据: NOT_RUN（未运行 dsh；未触发落盘）
不能证明: 不能证明头/尾**精确字节分配**在含省略通知时仍满足上限（README 述"each end receives half the budget remaining after omission notices"，未运行）；不能证明 `spill-local` 的磁盘路径形态（属后端实现）。
冲突裁决: 无旧结论冲突；为 CM-04 依据（第二层：落盘 + 引用）。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-trunc-04
结论: `compaction-tool-result-pruner` 仅在**压缩触发后**运行，把超 `thresholdChars`（默认 **8192**）的文本工具结果替换为 `headChars`(**4096**) + `PRUNE_MARKER`(`\n\n[... tool result middle pruned ...]\n\n`) + `tailChars`(**1024**)；按 **Unicode code point** 切（不劈代理对，但可能切字素簇）；原事件留在日志、替换事件经 `sourceEventSeqs` 引用。
性质: 事实
范围: `compaction-tool-result-pruner`；快照 `5719020…`；`dsh-base` 默认 8192/4096/1024
实现状态: 默认
来源: packages/compaction/compaction-tool-result-pruner/src/config.ts#L7,10-14,27-29,55-63；packages/compaction/compaction-tool-result-pruner/README.md#L44,48,56,60,82；cordis.patch.yml#L425-430
数据走查: DW-trunc-03
运行证据: OBS-dsh-meter-01（**不同机制**，函数级观察仅覆盖 token-meter 估算器；pruner 未运行）
不能证明: 不能证明"低于压力从不触碰"在运行时的边界（README 述，未运行）；不能证明非文本块（图像）在剪裁中的确切计费（README 述"non-text blocks cost zero"）。
冲突裁决: 无旧结论冲突；为 CM-04/CM-07 依据（第三层：压缩前剪裁）。
核验日期: 2026-10-15
```

## 6. 窗口计量与触发

```yaml
结论ID: dsh-trigger-01
结论: 【源码常量】压缩触发线 `thresholdTokens = floor(min(contextWindow × thresholdRatio, messageBudgetTokens − headroomTokens))`，其中 `messageBudgetTokens = contextWindow − reservedCompletionTokens`；默认 `thresholdRatio`=**0.8**、`headroomTokens`=**65,536**、`retainTokens = floor(messageBudgetTokens × retainRatio)` 默认 `retainRatio`=**0.16**；`auto` 默认 **true**；`compactionRetries` 默认 **1**、`maxOverflowRetries` 默认 **1**。当 `measurement.totalTokens >= thresholdTokens` 触发（`index.ts#L319`）。
性质: 事实
范围: `compaction-basic`；快照 `5719020…`；默认参数（`dsh-base` 未覆盖 config）
实现状态: 默认
来源: packages/compaction/compaction-basic/src/config.ts#L20,23,75,76,78,105,106,108,172,181,191-197；packages/compaction/compaction-basic/src/index.ts#L319
数据走查: DW-trigger-01
运行证据: NOT_RUN（未运行 dsh；未做真实到线触发）
不能证明: 不能证明**运行时实际**窗口值（`contextWindow` 由适配器声明，默认 1,000,000 属模型元数据，非 harness 常量）；不能证明 `reservedCompletionTokens` 在未显式设 `maxTokens` 时的实际取值（README 述取适配器默认）。**高风险：阈值公式** **[待另一 Agent 复核]**
冲突裁决: 支持"dsh 阈值 = 双上限口径（比例 ∧ 容量预留）"；**限制**：与 Codex `min(M,90%W)` 口径不同（术语表注①），不得混用。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-trigger-02
结论: 计量走**纯 harness 固定启发式**：`CHARS_PER_TOKEN`=**4**、`BLOCK_OVERHEAD`=**4**、`ROLE_OVERHEAD`=**4**（【源码常量】）；`estimateMessage` = `estimateContent(blocks) + ROLE_OVERHEAD`，system 角色走 `estimateSystemMessage`（无 per-block 开销）。**该启发式对 CJK 与 JSON Schema 显著低估**（官方 Dev Note 自述 "underprices CJK text and JSON Schema documents"）。
性质: 事实
范围: `token-meter`；快照 `5719020…`
实现状态: 默认
来源: packages/llm/token-meter/src/estimate.ts#L13,16,19,42-63,73-80,88-91；packages/llm/token-meter/README.md#L68,140,154
数据走查: DW-trigger-02
运行证据: **OBS-dsh-meter-01**（出货代码函数级真实执行；见 `过程观察.md`）：`estimateMessage(400 ASCII 字符)=108`、`estimateMessage(400 汉字)=108`、`estimateSystemMessage(400 字符)=104`、`estimateToolsTokens(undefined)=0`
不能证明: 不能证明**计费级** token 数（服务端真实分词不可观测）；观察为**函数级出货代码行为**，**不能外推**到端到端产品行为。
冲突裁决: **支持**"4 字符/token 对中文保守/低估"类旧争议，但**限定**：dsh 是**纯 harness 启发式**（与 Codex 用 provider usage 锚定不同）；中文低估方向与 Gemini（1.5/字符高估）**相反**。
核验日期: 2026-10-15
```

## 7. 自动 / 手动压缩

```yaml
结论ID: dsh-compact-01
结论: 自动压缩有**两条触发**：①`agent/pre-step` 的 `pressure`（请求派生前按 §6 阈值判定）；②`agent/request-error` 的 `context-overflow`（provider 确认 `CONTEXT_WINDOW_EXCEEDED` 时**绕过阈值**，做一次最大化平衡削减，仅当 `surface.replaceGeneration` 前进才重试）。
性质: 事实
范围: `compaction-basic`；快照 `5719020…`；`auto:true` 默认
实现状态: 默认
来源: packages/compaction/compaction-basic/src/index.ts#L140,158-176,190-234,294-302；docs/subsystems/compaction.md#L101
数据走查: DW-compact-01
运行证据: NOT_RUN（未运行 dsh；未注入真实溢出）
不能证明: 不能证明真实 provider 溢出措辞被归一化的**完整**覆盖（README 述"provider wording can change"，只保证两 DeepSeek 适配器归一化）；不能证明 retry 授权在并发下的时序（未运行）。
冲突裁决: 支持 docs/subsystems/compaction.md 的 `CompactionTrigger = 'pressure'|'context-overflow'`；为 CM-06 依据。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-compact-02
结论: 手动压缩 `/compact`（`command-compact`）在**空闲**会话上触发 `compactNow()`，**低于阈值**也做一次有用削减；agent 忙/压缩中 → 报"不可用"；命令生命周期（`command/run`/`command/done`）**只进日志不进模型历史**；成功报"压缩了几项、省了约多少 token"。
性质: 事实
范围: `command-compact`；快照 `5719020…`；`dsh-base` 默认装配
实现状态: 默认
来源: packages/compaction/command-compact/README.md#L12,28,34,36,69,91,123；packages/compaction/compaction-basic/src/index.ts#L383-435
数据走查: DW-compact-02
运行证据: NOT_RUN（未运行 dsh；需交互 TTY/Web 命令适配器）
不能证明: 不能证明 Web 客户端的命令适配器行为（属客户端）；不能证明"空闲注入上下文可落在 bracket 之间"的运行时表现（README 述，未运行）。
冲突裁决: 无旧结论冲突；为 CM-06 依据（手动入口）。
核验日期: 2026-10-15
```

## 8. 摘要 / 裁剪 / 重建

```yaml
结论ID: dsh-summary-01
结论: 摘要由**一次** `ctx.llm.stream()`（`purpose:'compaction'`）产出，指令要求**恰好 8 段** Markdown（Primary Request and Intent / Key Technical Concepts / Files and Code / Errors and Fixes / Pending Jobs / Current Work / Next Step / Critical Context）；回放"system 头 + 被遮蔽段消息 + 工具声明"作**真前缀**以复用 provider KV cache，只在**尾部**追加指令。
性质: 事实
范围: `compaction-basic`（`summarizer.ts`）；快照 `5719020…`
实现状态: 默认
来源: packages/compaction/compaction-basic/src/summarizer.ts#L32-67,120-181；packages/compaction/compaction-basic/src/region.ts#L544-563；README.md#L186-233
数据走查: DW-summary-01
运行证据: NOT_RUN（未运行 dsh；未发起真实摘要调用）
不能证明: 不能证明摘要**质量/保真度**（属模型侧，需 T19）；不能证明"真前缀"在服务端**真的命中**缓存（服务端 UNOBSERVABLE）。
冲突裁决: 无旧结论冲突；为 CM-07 依据。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-summary-02
结论: 摘要以 `<compacted-summary>` 包装，加固定 preamble，落为一条**替换** `user/message`（`surfaceOp:{op:'replace',startSeq,endSeq}`）；提交前做**收缩校验**——若 framed 摘要 ≥ 被遮蔽段 route 价格，则抛错（不写替换）。
性质: 事实
范围: `compaction-basic`；快照 `5719020…`
实现状态: 默认
来源: packages/compaction/compaction-basic/src/summarizer.ts#L22-23,70-71,188-194；packages/compaction/compaction-basic/src/region.ts#L417-422,470-522
数据走查: DW-summary-02
运行证据: NOT_RUN（未运行 dsh；未构造"摘要不变小"场景）
不能证明: 不能证明收缩校验在**每次**边界都拦得住（"framed 摘要 < route 价格"用的是启发式/route 价格混合，未运行）。
冲突裁决: 支持 docs/subsystems/compaction.md "The markers are lock time points, not an exclusive container"；为 CM-07 依据。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-summary-03
结论: **连续压缩为结构性增量**：摘要指令明示"若对话已含 `<compacted-summary>`，那是**上一份检查点**——保留仍真的事实、丢弃过期、把新信息**合并进同一结构**的单一摘要"；实现上每次压缩**重新选范围 + 重新摘要**（旧摘要作为历史的一部分被再次读到）。
性质: 事实
范围: `compaction-basic`；快照 `5719020…`
实现状态: 默认
来源: packages/compaction/compaction-basic/src/summarizer.ts#L66,224；README.md#L224
数据走查: DW-summary-03
运行证据: NOT_RUN（连续三次压缩属 T19；本包未运行）
不能证明: **不能证明**多次压缩后的**事实失真方向/程度**（摘要漂移 LQ-09 未实测）；不能证明"合并"是无损的（判为**有损**，但具体损失未测）。
冲突裁决: **LQ-09/C-04 未决**——dsh 有"合并旧检查点"的**指令级**结构，但保真度依赖 T19；不据此排成熟度。
核验日期: 2026-10-15
```

## 9. 长期记忆

```yaml
结论ID: dsh-memory-01
结论: **未发现 dsh 默认装配中有跨会话长期记忆实现（推断）**：全仓 `packages/` 无记忆包、无 `memoryBackend`/记忆注入符号；`docs/` 无长期记忆子系统。**唯一例外**是**实验包** `experimental/tool-ralph`（"the workspace is the long-term memory across rounds"，**默认不装配**）。跨会话能力另有 `session-reference`（显式提及，opt-in）与 `session-search`（实验，默认关）。
性质: 推断
范围: 全仓 `packages/` 出货路径 + `docs/`；快照 `5719020…`；默认装配
实现状态: 未证实（未发现默认实现）
来源: 复跑检索（`过程观察.md` §3）：S1 `grep -rniE "long.?term memory|memoryBackend|memory-backend|memoryStore|memoryInjection" packages --include=*.ts --include=*.md -l | wc -l` = **9**（全为测试文件的 in-memory store 用法 + `tool-ralph` 实验）；S2 `find packages -maxdepth 2 -type d -iname "*memor*" | wc -l` = **0**；S3 后台记忆提取 = **0**；对照 `grep -rniE "compaction|memory" packages/compaction/compaction-basic/src | wc -l` = **198**（证明命令非恒 0）。官方：`docs/architecture.md` 无记忆行；`experimental/tool-ralph/README.md#L36,163`
数据走查: —
运行证据: NOT_RUN（未运行 dsh；纯检索 + 官方 docs）
不能证明: **不能证明"不存在"**——只证明"**出货路径内未发现默认实现**"；未逐一枚举实验包语义、未检索 docs/ 之外的历史 Agent Notes；`tool-ralph` 的"workspace 即记忆"是否算长期记忆取决于定义（本包按"跨会话、可重新注入的笔记"口径判为**不属于**）。
冲突裁决: 术语表 §5"长期记忆/会话记忆/后台提取"在 dsh 侧：**未发现默认实现（推断）**；后台提取**未发现**（S3=0）。与 Gemini（有实现默认关）**不同**——dsh 连实验实现都未发现。
核验日期: 2026-10-15
```

## 10. 子 Agent 交接

```yaml
结论ID: dsh-cm09-01
结论: `subagent` 家族提供**独立上下文的子会话**：in-process `spawn`（全新）/`fork`（以父的已完成历史为种子）保留**durable 子会话**可续聊；out-of-process `acp`/`codex`/`claude-code`/`dsh-sdk` **只执行一次**。子会话继承父的 origin 元数据与权限根，但**不共享消息列表**。
性质: 事实
范围: `subagent/*`；快照 `5719020…`；`dsh-base` 默认装配 spawn/fork
实现状态: 默认（in-process）/ 条件（out-of-process 需装对应 provider bundle）
来源: packages/subagent/README.md#L12,27-33；packages/subagent/subagent/README.md#L12,61；cordis.patch.yml#L359-395
数据走查: DW-cm09-01
运行证据: NOT_RUN（未运行 dsh；未派发子 Agent）
不能证明: 不能证明子会话的实际 token 隔离程度（README 述"独立上下文"但未实测用量）；不能证明 fork 的"历史种子"边界在压缩后如何表现（未运行）。
冲突裁决: 无旧结论冲突；CM-09 对 dsh **适用**（与 pi 的"刻意不含 sub-agents"不同）。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-cm09-02
结论: 交接以**父级结算通知**回传：`delivery:'parent'` 时父收到一条 **user 角色**状态通知（含子最终文本块、可选 `Structured result: <JSON>`、provider 安全诊断；空收尾报 "It left no closing message."）。委派深度 `maxDepth` 默认 **1**（仅直属子）；并发 `maxActiveSubagents` 默认 **8**（进程内，根父不占槽）。
性质: 事实
范围: `subagent`；快照 `5719020…`
实现状态: 默认
来源: packages/subagent/subagent/README.md#L49,53,57,167-171,181-195
数据走查: DW-cm09-01
运行证据: NOT_RUN（未运行 dsh；未派发）
不能证明: 不能证明 `maxDepth`/`maxActiveSubagents` 的**运行时**用户覆盖优先级（README 述用户设置覆盖 composition，未运行）；不能证明跨进程续聊（README 明示无 durable parent mailbox）。
冲突裁决: 无旧结论冲突；为 CM-09 依据。
核验日期: 2026-10-15
```

## 11. 持久化 / 恢复

```yaml
结论ID: dsh-persist-01
结论: `session-persistence-jsonl` 每会话一个**追加式** JSONL；默认 **zstd** 校验帧（`compression:'none'` 时裸行文本）；`create(header)` **懒物化**（首条 `append` 才写 header+首批并 `fsync`）；**committed 事件永不改写**；**无删除 API**。
性质: 事实
范围: `session-persistence-jsonl`；快照 `5719020…`；`dsh-base` 默认装配（默认 zstd）
实现状态: 默认
来源: packages/session/session-persistence-jsonl/README.md#L12,46-48,55-71,77,167；cordis.patch.yml#L138-139
数据走查: DW-persist-01
运行证据: NOT_RUN（未运行 dsh；未检查真实磁盘日志）
不能证明: 不能证明磁盘上真实文件路径/命名（README 给布局但未运行）；不能证明 zstd 帧的**逐字节**布局（属实现）。
冲突裁决: 支持 LQ-04"L1 是否保留源文"：**保留**（追加式，压缩只改 surface，不删日志）。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-persist-02
结论: `session-checkpoint-policy` 在**每次模型请求前 / 顶层工具副作用前 / 下一步前**做**语义检查点**（flush），**fail-closed**：写不成功则不跑适配器/工具体；自身**无配置**、不加提示词/工具 schema。
性质: 事实
范围: `session-checkpoint-policy`；快照 `5719020…`；`dsh-base` 默认装配
实现状态: 默认
来源: packages/session/session-checkpoint-policy/README.md#L12,28-40；cordis.patch.yml#L420-421
数据走查: DW-persist-02
运行证据: NOT_RUN（未运行 dsh；未注入写失败）
不能证明: 不能证明 flush 的**确切时机粒度**在运行时的表现（README 述三处，未运行）；不能证明 fail-closed 在磁盘满等真实故障下的行为。
冲突裁决: 无旧结论冲突；为 CM-10/CM-11 依据（副作用前持久化）。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-persist-03
结论: 崩溃修复语义：committed 前缀全保留；恢复时**不完整尾行丢弃**、**撕裂 zstd 帧只取完整记录**；agent 层为未答工具调用补 `TOOL_OUTCOME_UNKNOWN`（只允许重试只读/幂等），无开始记录的调用补 `TOOL_NOT_STARTED`。
性质: 事实
范围: `session-persistence-jsonl` + `agent-loop`；快照 `5719020…`
实现状态: 默认
来源: packages/session/session-persistence-jsonl/README.md#L77,147；packages/core/agent-loop/README.md#L128-131,194-206
数据走查: DW-persist-03
运行证据: NOT_RUN（未运行 dsh；未注入崩溃）
不能证明: 不能证明真实进程被杀后的恢复结果（未运行）；不能证明"可能副作用"提示在实际模型行为上的效果。
冲突裁决: 无旧结论冲突；为 CM-11 依据（幂等与重复执行防护）。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-recover-01
结论: dsh 的压缩恢复走**持久化断点路线**（非重放全历史）：压缩是**替换**（`surfaceOp.replace`），恢复后 `deriveMessages()` 直接投影"摘要 + 保留段"；`ctx.agents.resume()` 先取写权、读物理有效日志、补中断 turn 的 closers。
性质: 事实
范围: `compaction-basic` + `agent-loop` + `session-persistence-jsonl`；快照 `5719020…`
实现状态: 默认
来源: packages/core/agent-loop/README.md#L114-116,178；packages/compaction/compaction-basic/src/region.ts#L506-509；docs/subsystems/compaction.md#L11
数据走查: DW-persist-01、DW-summary-02
运行证据: NOT_RUN（未运行 dsh；未做 resume 实测）
不能证明: 不能证明恢复后**没有重算**（"持久化断点 vs 重放"的运行时判据未跑，仅由替换语义推断）；不能证明 resume 的缓存复用（服务端 UNOBSERVABLE）。
冲突裁决: **LQ-10**：dsh = **持久化断点路线（B）**；"找不回"**限制为默认模型可见层**——原始日志仍在，可找回。
核验日期: 2026-10-15
```

## 12. 错误与副作用

```yaml
结论ID: dsh-fail-01
结论: 模型请求重试由 `llm-retry` 执行（策略归各适配器 `retryPolicy`）：**normal 模式默认 5 次**，退避 500ms–10s + 10% 抖动，覆盖 `EMPTY_RESPONSE/RATE_LIMIT/SERVER/TIMEOUT/TRANSPORT`；**always 模式无上限**。每次重试**先落 durable `llm/retry` 事件**（含 retryId/provider/mode/policy key/failure/delay）再等待；重试在**同一 open turn** 内重跑该步。
性质: 事实
范围: `llm-retry`；快照 `5719020…`；`dsh-base` 默认装配
实现状态: 默认（normal）；条件（always 需配置）
来源: packages/llm/llm-retry/README.md#L12,28,50,54,72,84；packages/llm/llm-deepseek/README.md#L74（`retryPolicy` 默认 normal, 5 retries）
数据走查: DW-fail-01
运行证据: NOT_RUN（未运行 dsh；未注入瞬时失败）
不能证明: 不能证明真实 provider 故障下的重试时序/费用（未运行）；不能证明"always 模式永不终止"在取消路径上的表现。
冲突裁决: 无旧结论冲突；为 CM-11 依据（有界重试）。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-fail-02
结论: 压缩失败被**分类**：手动路径抛 `ManualCompactionError`，码集 `busy|cancelled|changed|summary|commit|persistence`；`changed`/`summary` 会**关闭并持久化失败尝试**但不写摘要替换；`commit` 可能已部分变更；`persistence` 表示内存 bracket 已关闭但 flush 失败；取消抛精确 abort reason。自动路径失败**记 warning 并继续本轮**（不阻断）。
性质: 事实
范围: `compaction-basic` + `command-compact`；快照 `5719020…`
实现状态: 默认
来源: docs/subsystems/compaction.md#L86-99；packages/compaction/compaction-basic/src/region.ts#L278-299,240-251；packages/compaction/compaction-basic/src/index.ts#L166-173,206-227
数据走查: DW-fail-02
运行证据: NOT_RUN（未运行 dsh；未注入压缩失败）
不能证明: 不能证明各码在真实故障下的**可达性**（未运行）；不能证明"部分变更"的确切范围（README 述 commit 可能部分变更）。
冲突裁决: 无旧结论冲突；为 CM-11 依据（失败分类）。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-fail-03
结论: **副作用与并发防护**：`compaction/start`（未配对）即**durable 锁**——活跃未配对 start 阻断所有入口（`busy`），但**早于最新 `session/end-seed` 的 start 视为上一生命周期的陈旧证据**、不阻断；收尾失败**刻意留下孤儿锁**（可检测）；异步摘要后做**稳定性校验**（自动=whole-surface，手动=selected-span）。
性质: 事实
范围: `compaction-basic`；快照 `5719020…`
实现状态: 默认
来源: packages/compaction/compaction-basic/src/region.ts#L107-126,301-334,430-468；docs/subsystems/compaction.md#L19-21,125
数据走查: DW-fail-03
运行证据: NOT_RUN（未运行 dsh；未构造孤儿锁/并发）
不能证明: 不能证明并发竞态在真实多客户端下的表现（未运行）；不能证明"陈旧 seed 边界"判定在所有迁移场景下正确。
冲突裁决: 无旧结论冲突；为 CM-11 依据（副作用/锁）。
核验日期: 2026-10-15
```

## 13. 缓存及总成本

```yaml
结论ID: dsh-cache-01
结论: **CLI 侧可证**：DeepSeek 适配器把 wire 的 `cache_read_input_tokens`→`cacheReadTokens`、`cache_creation_input_tokens`→`cacheWriteTokens`，`totalTokens = inputTokens + outputTokens + cacheReadTokens + cacheWriteTokens`；`token-meter` 的 `tokenUsage` 投影输出 `uncachedInputTokens/outputTokens/cacheReadTokens/cacheWriteTokens`。**TokenUsage 计数互斥**（inputTokens 仅未缓存输入）。
性质: 事实
范围: `llm-deepseek` + `llm` + `token-meter`；快照 `5719020…`
实现状态: 默认
来源: packages/llm/llm-deepseek/src/translate.ts#L36,159；packages/llm/llm/src/types.ts#L167-188；packages/llm/token-meter/src/usage-projection.ts#L15-18,22-25；packages/llm/token-meter/README.md#L49
数据走查: DW-cache-01
运行证据: NOT_RUN（未运行 dsh；未做真实 API 调用取 usage）
不能证明: 不能证明**命中率/TTL**（服务端 UNOBSERVABLE）；不能证明字段映射在所有 provider 一致（本包只核 DeepSeek 适配器）。
冲突裁决: 术语表 §6"缓存键=已证（CLI 侧）"在 **dsh 侧不成立**——**未发现** CLI 侧缓存键/断点（见 cache-02）；dsh 只有 usage 明细字段。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-cache-02
结论: **未发现 dsh CLI 侧缓存键/断点/预热实现**（推断）：复跑 `grep -rniE "prompt_cache_key|cacheBreakpoint|cache_breakpoint" packages --include=*.ts | wc -l` = **1**（唯一命中为 `subagent-codex/tests/responses-fixture.ts` 的 Codex 响应样本，**非** dsh 自身机制）；**服务端缓存存储/命中/TTL = UNOBSERVABLE**。dsh 侧只做**前后缀策略**（压缩替换使前缀从首个被替换 token 起失效；`in-history` 路由把提示词变更**追加**在缓存历史之后以保前缀）。
性质: 推断
范围: 全仓 `packages/`（.ts）；快照 `5719020…`
实现状态: 未证实（未发现 CLI 侧实现）
来源: 复跑（`过程观察.md` §3）：S4 = **1**（`packages/subagent/subagent-codex/tests/responses-fixture.ts:71: prompt_cache_key: null`）；对照 `grep -rniE "cache" packages/llm/token-meter/src | wc -l` = **47**（非恒 0）；README.md#L180-181（KV cache effect 描述）
数据走查: DW-cache-01
运行证据: NOT_RUN（未运行 dsh；服务端不可观测）
不能证明: **不能证明"不存在"**——只证明"出货路径内未发现 CLI 侧缓存键/断点"；**服务端是否缓存、命中多少，本包完全不可观测**（不得写成"没有实现缓存"）。
冲突裁决: 与 Codex（`prompt_cache_key` = session_id，`codex-cache-01`）**不同**：dsh 侧**未发现**显式缓存键；**服务端行为待 T19**。
核验日期: 2026-10-15
```

## 14. 分层与扩展

```yaml
结论ID: dsh-layer-01
结论: **harness 实现 vs 模型/API 能力分界**：dsh **实现** = 请求组装/角色、4 字符/token 计量、阈值公式与默认、压缩事务与摘要指令、剪裁/落盘上限、重试执行、规则/技能加载、子 Agent 隔离、JSONL 持久化、usage 字段映射；**模型/API 提供** = 1,000,000 token 窗口（适配器声明）、真实分词与计费、缓存存储/命中/TTL、溢出真实判定与措辞、视觉 token 定价、推理内容。逐条 20 项见 `harness实现-vs-模型API分列表.md`。
性质: 事实
范围: 全包（综合）；快照 `5719020…`
实现状态: 默认
来源: 综合 dsh-* 各卡；任务书 FB-07；`工具概览.md §3`
数据走查: —
运行证据: NOT_RUN（未运行 dsh）
不能证明: 不能证明服务端具体行为（窗口/缓存/分词/溢出 = UNOBSERVABLE）；"适配器声明窗口"≠"服务端真实窗口"。
冲突裁决: **落实 FB-07**：凡模型侧行为**不得**当 harness 实现写入；`API 支持缓存` ≠ `dsh 默认命中`。
核验日期: 2026-10-15
```

```yaml
结论ID: dsh-ext-01
结论: `compaction-image-offload`（默认装配）在**图像路由拒绝请求（超图像预算）**时，把**最旧的图像**替换为**占位符**（`image/offload` 事件，保留节点/消息身份、无 `surfaceOp`），然后重试；被选中的出现按**占位符文本**计价。
性质: 事实
范围: `compaction-image-offload`；快照 `5719020…`；`dsh-base` 默认装配
实现状态: 默认
来源: packages/bundle/base/cordis.patch.yml#L434-435；docs/subsystems/compaction.md#L25-38；packages/llm/llm-deepseek/README.md#L64-68,95,177（图像预算与 oldest-prefix 移除量子）
数据走查: —
运行证据: NOT_RUN（未运行 dsh；未发图像请求）
不能证明: 不能证明占位符**逐字文本**与离载顺序在运行时的表现（未运行）；不能证明非 DeepSeek 图像路由行为。
冲突裁决: 无旧结论冲突；为 CM-04/CM-12 边界提供依据（图像 = 扩展路径）。
核验日期: 2026-10-15
```

---

## 15. 计数核对（命令实测）

- `grep -c "^结论ID:" 证据/dsh-证据卡.md` = **34**（族见附表；实测见 `问题与审查.md` §7）。
  > **注**：`grep -c "结论ID:"`（不带 `^`）会多算 **2**（实测 36；行首锚定 34 为准）——**自述计数须用行首锚定**，与实测一致。
- 每卡"不能证明"栏**均非空**；高风险清单见 `问题与审查.md` §8.1（7 项，已由 T13R 复核通过）。

---
*配套：`工具概览.md` / `源码导读.md` / `数据走查.md` / `过程观察.md` / `问题与审查.md`。*
