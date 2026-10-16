---
title: Gemini CLI · 证据卡
task: T11
role: 工具研究 Agent
created: 2026-10-15
snapshot: 42c51822084ac25cd5d97ac0023822c5235f88c8
spec: 08-验收/T07-后六工具样本规范.md
---

# Gemini CLI · 证据卡

> **格式**（规范 §2，逐字段强制）：`结论ID / 结论 / 性质 / 范围 / 实现状态 / 来源 / 数据走查 / 运行证据 / 不能证明 / 冲突裁决 / 核验日期`。
> **链接基址**：`https://github.com/google-gemini/gemini-cli/blob/42c51822084ac25cd5d97ac0023822c5235f88c8/`（下称 `<SHA>`）。
> **高风险主张**（阈值 / 默认开关 / 持久化 / 二次压缩 / 缓存）已标 **`[待另一 Agent 复核]`**。
> 计数：本文件共 **34** 张（脚本核对：34 卡 / 34 唯一 ID / 无缺字段）。
> **D10⑤ 纪律**：所有"零命中 / 未发现"类断言均已**复跑登记命令并贴真实输出**，见 `问题与审查.md §0`。

---

### gemini-version-01 · 身份与快照

- **结论ID**: gemini-version-01
- **结论**: Gemini CLI = `google-gemini/gemini-cli`（npm `@google/gemini-cli`），TS monorepo；研究快照 `42c5182…`（main）`git status` 干净；本机**未安装**，无入口自报版本。
- **性质**: 事实
- **范围**: 仓库/快照 SHA `42c51822084ac25cd5d97ac0023822c5235f88c8`；本机环境（2026-10-15）
- **实现状态**: 默认
- **来源**: `git rev-parse HEAD` = `42c5182…`；`版本表.md §1/§3`
- **数据走查**: —
- **运行证据**: NOT_RUN（产品入口未运行，本机 `which gemini` = not found）
- **不能证明**: 本机未安装 → **不能**据此证明任何"产品默认行为"；快照 main 与官方 release v0.64.0 是否同一代码**未核对**
- **冲突裁决**: 支持 T01 身份登记
- **核验日期**: 2026-10-15

### gemini-version-02 · 双上下文管理系统（默认链路 vs 实验图管线）

- **结论ID**: gemini-version-02
- **结论**: 存在两套上下文管理系统——**默认启用**的 `ChatCompressionService`/`ToolOutputMaskingService` 链路（`contextManagement.enabled=false` 时走 `client.ts:719`），与**默认关闭**的图管线 `ContextManager`+`PipelineOrchestrator`（`initializer.ts:35-38` 门控）。**不得**把图管线常量（如 `retainedTokens=65000`）当产品默认。
- **性质**: 事实
- **范围**: 快照 `42c5182…`；`packages/core/src/{core/client.ts,context/*}`
- **实现状态**: 默认（传统链路）/ 实验（图管线，门控默认关）
- **来源**: `<SHA>/packages/core/src/config/config.ts#L1207-L1208`（`enabled: params.contextManagement?.enabled ?? false`）；`<SHA>/packages/core/src/context/initializer.ts#L35-L38`；`<SHA>/packages/core/src/core/client.ts#L673-L729`；`<SHA>/schemas/settings.schema.json`（`experimental.contextManagement` default **false**）
- **数据走查**: DW-trigger-01
- **运行证据**: NOT_RUN（产品入口未运行）；常量与门控由源码直读
- **不能证明**: 不能证明远端是否有 experiment flag 会**改写**该门控；不能证明默认链路在所有版本/发行版均默认启用
- **冲突裁决**: 支持 C-08 裁决（旧"不压缩"标签基于未区分两套系统）
- **核验日期**: 2026-10-15

### gemini-version-03 · C-08 裁决（"大窗口不压缩"旧标签）`[待另一 Agent 复核]`

- **结论ID**: gemini-version-03
- **结论**: **撤回**旧标签"Gemini CLI 大窗口不压缩"。压缩**有实现且默认启用**：触发线 = `model.compressionThreshold`（官方默认 **0.5**）× `tokenLimit`，1M 窗口 → **524,288 token**。旧标签的**部分合理性**仅在于：因窗口大（1M）+ 阈值高（50%），**实践中很少触发**自动压缩。
- **性质**: 事实（撤回）+ 推断（"很少触发"）
- **范围**: 快照 `42c5182…`；默认模型窗口 1,048,576
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/context/chatCompressionService.ts#L45`（`DEFAULT_COMPRESSION_TOKEN_THRESHOLD=0.5`）、`#L502-L518`（阈值比较）；`<SHA>/packages/core/src/config/config.ts#L3454-L3468`；`<SHA>/docs/cli/settings.md#L107`（官方默认 0.5）；`<SHA>/docs/reference/configuration.md#L552-L556`；`<SHA>/packages/core/src/core/tokenLimits.ts#L20-L39`
- **数据走查**: DW-trigger-01
- **运行证据**: `OBS-gemini-trunc-01`（函数级：`tokenLimit=1048576`、派生 `0.5×1048576=524288` PASS）
- **不能证明**: 不能证明远端 `CONTEXT_COMPRESSION_THRESHOLD` 是否把阈值改小/改大；"很少触发"为**推断**（未跑真实长会话），**未实测**
- **冲突裁决**: **撤回** `ant-opus §5.3/§6.3` 旧标签；**支持**官方配置文档"已见压缩参数"
- **核验日期**: 2026-10-15

### gemini-layer-01 · 客户端/服务分层

- **结论ID**: gemini-layer-01
- **结论**: 上下文管理机制**绝大部分在 CLI 侧可观测**（组装/规整/触发判定/截断/落盘/掩蔽/记忆/恢复/重试）；**服务端**承担摘要 LLM 生成、真实 usage 计量与**全部 prompt cache 行为**（不可观测）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: 见 `工具概览.md §3` 分层表（逐条指向源码文件）
- **数据走查**: DW-cache-01
- **运行证据**: NOT_RUN（服务端不可观测）
- **不能证明**: 服务端缓存命中率/TTL/缓存键**完全不可观测**；CLI 只读字段，无法反推服务端行为
- **冲突裁决**: 支持 T09R"按服务标签 + 引用关系逐条判定"纪律（Gemini 侧边界清晰）
- **核验日期**: 2026-10-15

### gemini-assembly-01 · 请求组装与角色规整

- **结论ID**: gemini-assembly-01
- **结论**: 请求 = `systemInstruction` + `tools` + `contents`；`contents` 为 user/model 交替，**工具结果装在 `user` turn 的 `functionResponse`**；发送前经 `stripThoughts`（剥离 thought，补合成 thoughtSignature）+ `coalesceConsecutiveRoles`（合并相邻同 role）规整。
- **性质**: 事实
- **范围**: 快照 `42c5182…`；Gemini 2+ 模型
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/core/geminiChat.ts#L1270-L1292`（`getHistoryTurns`）、`#L2025-L2051`（`coalesceConsecutiveRoles`）、`#L2053-L2093`（`stripThoughts` + `SYNTHETIC_THOUGHT_SIGNATURE`）；`<SHA>/packages/core/src/core/client.ts#L673-L729`
- **数据走查**: DW-assembly-01
- **运行证据**: NOT_RUN
- **不能证明**: 不能证明服务端对 `contents` 的实际解析；不能证明 thoughtSignature 合成在所有模型上都足够（仅防 400 报错的兜底）
- **冲突裁决**: 支持 T02 §E"请求组装与角色"统一语义
- **核验日期**: 2026-10-15

### gemini-assembly-02 · 环境上下文与 Tier 分层

- **结论ID**: gemini-assembly-02
- **结论**: 环境上下文（`<session_context>`：日期/OS/目录树 + 记忆）作为**首条 user turn**注入；官方注释给出 Tier 分层——Tier1 系统提示词、Tier2 首条 user 消息（extension+project 记忆）、Tier3 子目录 JIT（工具输出）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/utils/environmentContext.ts#L50-L111`（`getEnvironmentContext`/`getInitialChatHistory`，注释 `#L62-L66`）；`<SHA>/packages/core/src/config/config.ts#L2617-L2637`（`getSessionMemory`）
- **数据走查**: DW-assembly-01
- **运行证据**: NOT_RUN
- **不能证明**: 目录树体量随仓库规模变化，**未实测**其对首请求 token 的贡献
- **冲突裁决**: 支持 T02 §E"项目规则/技能加载"
- **核验日期**: 2026-10-15

### gemini-rule-01 · GEMINI.md 分层记忆

- **结论ID**: gemini-rule-01
- **结论**: 记忆分四层：`global`（`~/.gemini/GEMINI.md`）、`extension`、`project`（受信任目录，边界标记默认 `.git`）、`userProjectMemory`（`MEMORY.md`）。global+userProjectMemory 进**系统提示词**；extension+project 进**首条 user 消息**（`<loaded_context>`）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/context/memoryContextManager.ts#L38-L203`；`<SHA>/packages/core/src/config/config.ts#L2600-L2637`；`<SHA>/packages/core/src/tools/memoryTool.ts#L11-L12`（`DEFAULT_CONTEXT_FILENAME='GEMINI.md'`、`PROJECT_MEMORY_INDEX_FILENAME='MEMORY.md'`）；`<SHA>/docs/tools/memory.md`
- **数据走查**: DW-rule-01
- **运行证据**: NOT_RUN
- **不能证明**: 未实测各层实际体积与截断行为（**未发现** GEMINI.md 的字节预算常量，见 gemini-rule-03）
- **冲突裁决**: 支持 T02 §E"项目规则/技能加载"
- **核验日期**: 2026-10-15

### gemini-rule-02 · 技能渐进式披露

- **结论ID**: gemini-rule-02
- **结论**: 技能由 `SkillManager.discoverSkills` 按 **Built-in → Extension → User → Workspace**（优先级递增）发现；通过 `activate_skill` 工具**按需激活**（渐进式披露）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/skills/skillManager.ts#L54-L81`；`<SHA>/packages/core/src/skills/skillLoader.ts`；`<SHA>/docs/tools/activate-skill.md`
- **数据走查**: DW-rule-01
- **运行证据**: NOT_RUN
- **不能证明**: 未实测"激活后注入体量"与"未激活时仅摘要"的确切边界
- **冲突裁决**: 支持 T02 §E"技能（渐进式披露）"
- **核验日期**: 2026-10-15

### gemini-rule-03 · JIT 子目录记忆（Tier 3）

- **结论ID**: gemini-rule-03
- **结论**: 访问某路径时，`discoverContext` 从该路径**向上**到项目根发现 GEMINI.md，作为**工具输出**注入（非全量预载）；已加载文件按 dev+ino **去重**。
- **性质**: 事实
- **范围**: 快照 `42c5182…`；仅受信任目录
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/context/memoryContextManager.ts#L141-L172`；`<SHA>/packages/core/src/utils/memoryDiscovery.ts#L54-L91`（`deduplicatePathsByFileIdentity`）；`<SHA>/packages/core/src/tools/jit-context.ts`
- **数据走查**: DW-rule-01
- **运行证据**: NOT_RUN
- **不能证明**: **"未发现"≠"没有"**（D10⑤）。**复跑命令 + 真实输出**：`grep -rniE "byte.?budget|memoryMaxBytes|budgetBytes" packages/core/src | wc -l` → **`0`**；加宽 `grep -rniE "maxBytes" packages/core/src/context packages/core/src/utils packages/core/src/tools` 命中的**全部**是 `COLLAPSED_FUNCTION_RESPONSE_MAX_BYTES`（工具输出折叠，非记忆）与 `truncateToolOutput` 测试——**无** GEMINI.md/MEMORY.md 字节预算常量。官方 `docs/tools/memory.md` 与 `docs/cli/gemini-md.md` 亦**未提**字节上限。**未发现默认实现（推断）**
- **冲突裁决**: 支持 T02 §E"发现范围"；对比 Codex 的 32 KiB 共享预算——Gemini 侧**未发现**同类硬预算
- **核验日期**: 2026-10-15

### gemini-retrieval-01 · 资料选择与代码检索

- **结论ID**: gemini-retrieval-01
- **结论**: 检索走**按需工具**：`read_file`/`read_many_files`/`grep`（`rip_grep`）/`glob`/`get_internal_docs`/`read_mcp_resource`；无"全量装填"路径，配合 JIT 子目录记忆（Tier 3）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/context/chatCompressionService.ts#L56-L67`（`RETRIEVAL_TOOL_NAMES_EXEMPT_FROM_COLLAPSE` 列出检索工具名）；`<SHA>/docs/reference/tools.md`；`<SHA>/packages/core/src/tools/jit-context.ts`
- **数据走查**: DW-retrieval-01
- **运行证据**: NOT_RUN
- **不能证明**: **复跑命令 + 真实输出**：`grep -rniE "stuffAll|bulkLoad|preloadAllFiles|loadAllFiles" packages/core/src | wc -l` → **`0`**（**无**全量装填路径）；未实测检索结果体量对窗口的贡献；`useRipgrep` 默认 true（`config.ts:1274`）但未跑
- **冲突裁决**: 支持 T02 §E"检索 / 按需读入"
- **核验日期**: 2026-10-15

### gemini-trunc-01 · 工具输出截断（40k 字符 + head20%/tail80% + 落盘）`[待另一 Agent 复核]`

- **结论ID**: gemini-trunc-01
- **结论**: 默认对 **shell 工具**与**单 part MCP 工具**文本，当 `content.length > threshold`（默认 **40,000 字符**【源码常量】）时：全量原文落盘 `tool-outputs/[session-<id>/]<tool>_<callId>.txt`，请求里替换为**头 20% + 尾 80%** + `... [N characters omitted] ...` + 文件路径。
- **性质**: 事实
- **范围**: 快照 `42c5182…`；`truncateToolOutputThreshold` 未改时
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/scheduler/tool-executor.ts#L202-L340`；`<SHA>/packages/core/src/config/config.ts#L483`（`DEFAULT_TRUNCATE_TOOL_OUTPUT_THRESHOLD=40_000`）、`#L1299-L1301`；`<SHA>/packages/core/src/utils/fileUtils.ts#L786-L806`（`formatTruncatedToolOutput`，head 20%/tail 80%）、`#L811`（`TOOL_OUTPUTS_DIR='tool-outputs'`）、`#L813-L837`（`saveTruncatedToolOutput`）
- **数据走查**: DW-trunc-01
- **运行证据**: `OBS-gemini-trunc-01`（函数级：`truncateProportionally` 头 8/尾 33/总长 50 边界 PASS）
- **不能证明**: 阈值对**非 shell/非 MCP 单 part** 工具（如 `read_file`）**不生效**——其治理依赖掩蔽/折叠链路；未实测落盘文件的可读回体验
- **冲突裁决**: 与 T02 §E"出口限长/落盘/预览"一致；口径为**字符**（非 token）
- **核验日期**: 2026-10-15

### gemini-trunc-02 · 硬上限 64 KB

- **结论ID**: gemini-trunc-02
- **结论**: 截断后若文本仍 > `MAX_STORED_TOOL_OUTPUT_BYTES`（**64 KB** = 65,536 字节【源码常量】）→ 再 `truncateToolOutput` 硬截。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/utils/constants.ts#L18`（`MAX_STORED_TOOL_OUTPUT_BYTES = 64 * 1024`）；`<SHA>/packages/core/src/scheduler/tool-executor.ts#L248-L257`
- **数据走查**: DW-trunc-01
- **运行证据**: NOT_RUN（常量由源码直读）
- **不能证明**: 未实测"头 20%+尾 80% 后再超 64KB"是否常见（取决于单字符字节数，中文下 40k 字符 ≈ 120 KB 字节，**会**触发二次硬截）
- **冲突裁决**: 与 gemini-trunc-01 互补（两级上限）
- **核验日期**: 2026-10-15

### gemini-masking-01 · 工具输出掩蔽（50k 保护 / 30k 批量 / 保护最新轮）`[待另一 Agent 复核]`

- **结论ID**: gemini-masking-01
- **结论**: 每次发请求前，`ToolOutputMaskingService.mask` 从倒数第 2 条起向后扫：累计工具 token 越过 **50,000** 保护窗、且可裁剪总量 ≥ **30,000** 时，把旧 tool part 替换为 `<tool_output_masked>` 块（head/tail 各 250 字符预览 + 落盘路径）。即需 **50k 保护 + 30k 可裁剪 ≈ 80k 总量** 才启动。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/context/toolOutputMaskingService.ts#L25-L27`（`50000`/`30000`/`protectLatestTurn=true`）、`#L67-L270`（算法与落盘）、`#L204-L213`（预览）；`<SHA>/packages/core/src/core/client.ts#L729`、`#L1287-L1295`（`tryMaskToolOutputs`）
- **数据走查**: DW-masking-01
- **运行证据**: NOT_RUN
- **不能证明**: 未实测"**50k 保护 + 30k 可裁剪 ≈ 80k 总量**"门槛在真实会话的触发频率；`protectLatestTurn=true` 时**最新一轮**工具输出永不掩蔽（可能仍超窗，由截断/压缩兜底）
- **冲突裁决**: 支持 T02 §E"落盘/预览/多块共享预算"（此处为全局聚合而非单请求共享预算）
- **核验日期**: 2026-10-15

### gemini-collapse-01 · 旧轮 functionResponse 折叠（最近 3 轮 / 2 KB / retrieval 豁免）

- **结论ID**: gemini-collapse-01
- **结论**: `collapseOlderFunctionResponses` 保护**最近 3 个**工具轮全保真；更旧的 functionResponse 中 > **2048 字节**的字符串折叠为前 2 KB + `... [Tool output collapsed from previous turn: N bytes omitted] ...`；**retrieval 工具豁免**。按 grapheme 切分，**不切断多字节字符**。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认（在 `local-executor.ts` 子 Agent 路径按压力触发；见 gemini-cm09-01）
- **来源**: `<SHA>/packages/core/src/context/chatCompressionService.ts#L50`（`RECENT_TURNS_PROTECTED=3`）、`#L88`（`COLLAPSED_FUNCTION_RESPONSE_MAX_BYTES=2048`）、`#L131-L263`（`collapseOlderFunctionResponses`）、`#L56-L67`（豁免集）；`<SHA>/packages/core/src/agents/local-executor.ts#L934-L945`
- **数据走查**: DW-collapse-01
- **运行证据**: NOT_RUN
- **不能证明**: **复跑命令 + 真实输出**：`grep -rn "collapseOlderFunctionResponses" packages/core/src | grep -v "\.test\.ts"` → 3 处：定义 `chatCompressionService.ts:131`、导入 `local-executor.ts:36`、**唯一调用** `local-executor.ts:936`——即**主 `client.ts` 默认路径未调用**，仅**子 Agent** 路径调用 → 主会话是否触发**未证实**（实现状态=条件）
- **冲突裁决**: 支持 T02 §E"头尾裁剪/多块共享预算"
- **核验日期**: 2026-10-15

### gemini-trigger-01 · 模型窗口常量 `[待另一 Agent 复核]`

- **结论ID**: gemini-trigger-01
- **结论**: `tokenLimit(model)`：Gemini 系列 **1,048,576**、Gemma-4 系列 **256,000**、未知模型 → `DEFAULT_TOKEN_LIMIT = 1,048,576`【源码常量】。
- **性质**: 事实
- **范围**: 快照 `42c5182…`；硬编码于 CLI
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/core/tokenLimits.ts#L20-L39`
- **数据走查**: DW-trigger-01
- **运行证据**: `OBS-gemini-trunc-01`（函数级：`DEFAULT_TOKEN_LIMIT=1048576`、`tokenLimit('gemini-2.5-pro')=1048576` PASS）
- **不能证明**: 该窗口是 **CLI 硬编码常量**，**非**服务端下发；若服务端实际窗口与常量不符，CLI 不可知
- **冲突裁决**: 支持 C-08 裁决（大窗口）
- **核验日期**: 2026-10-15

### gemini-trigger-02 · 压缩触发线（0.5 × 窗口）`[待另一 Agent 复核]`

- **结论ID**: gemini-trigger-02
- **结论**: 自动压缩触发线 = `getCompressionThreshold() ?? 0.5` × `tokenLimit(model)`。`getCompressionThreshold` 优先 CLI 参数，其次**远端 experiment flag** `CONTEXT_COMPRESSION_THRESHOLD`；远端为 0 → `undefined` → 落默认 **0.5**。1M 窗口 → **524,288 token**。
- **性质**: 事实（公式与默认）+ 推断（远端可能改写）
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/context/chatCompressionService.ts#L45`、`#L502-L518`；`<SHA>/packages/core/src/config/config.ts#L3454-L3468`；`<SHA>/docs/cli/settings.md#L107`；`<SHA>/docs/reference/configuration.md#L552-L556`；`<SHA>/schemas/settings.schema.json`（`model.compressionThreshold` default 0.5）
- **数据走查**: DW-trigger-01
- **运行证据**: `OBS-gemini-trunc-01`（派生 `0.5×1048576=524288` PASS）
- **不能证明**: **远端 flag 实际下发值不可观测**（服务端）；不能证明真实会话在 524,288 token 处一定触发（未跑）
- **冲突裁决**: **撤回** C-08 旧标签；支持官方配置文档
- **核验日期**: 2026-10-15

### gemini-trigger-03 · 溢出前置检查

- **结论ID**: gemini-trigger-03
- **结论**: 发请求前计算 `remainingTokenCount = tokenLimit(model) - getLastPromptTokenCount()`；若 `estimatedRequestTokenCount > remainingTokenCount` → 产出 `ContextWindowWillOverflow` 事件并**中止本轮**（不压缩、不发送）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/core/client.ts#L726-L745`；`<SHA>/packages/core/src/core/geminiChat.ts#L1796-L1798`（`getLastPromptTokenCount`）
- **数据走查**: DW-trigger-02
- **运行证据**: NOT_RUN
- **不能证明**: `estimatedRequestTokenCount` 含媒体时走 `countTokens` API（服务端计量，**不可观测**）
- **冲突裁决**: 支持 T02 §E"当前用量"
- **核验日期**: 2026-10-15

### gemini-compact-01 · 自动压缩入口

- **结论ID**: gemini-compact-01
- **结论**: 默认链路下，每轮发请求前 `tryCompressChat(prompt_id, force=false)` 做**自动压缩**；仅当达阈值才真正压缩（否则 NOOP）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/core/client.ts#L719-L724`、`#L1226-L1282`
- **数据走查**: DW-compact-01
- **运行证据**: NOT_RUN
- **不能证明**: 未实测"每轮都尝试、达线才压"的实际事件序列（未跑）
- **冲突裁决**: 支持 T02 §E"自动压缩"
- **核验日期**: 2026-10-15

### gemini-compact-02 · 手动压缩入口（`/compress`）

- **结论ID**: gemini-compact-02
- **结论**: `/compress` 命令 → `tryCompressChat(prompt_id, force=true)`：**跳过阈值判定**，无条件走摘要流程。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/core/client.ts#L1226-L1282`（`force` 透传到 `compress`）；`<SHA>/packages/core/src/context/chatCompressionService.ts#L492`（`trigger = force ? Manual : Auto`）、`#L502`（`if (!force)` 才判阈值）；`<SHA>/docs/reference/commands.md`
- **数据走查**: DW-compact-01
- **运行证据**: NOT_RUN
- **不能证明**: 命令名 `/compress` 的 CLI 侧绑定未在本包逐一核对（仅官方命令文档 + force 参数透传）
- **冲突裁决**: 支持 T02 §E"手动压缩"
- **核验日期**: 2026-10-15

### gemini-summary-01 · `<state_snapshot>` 结构化摘要 + 防注入

- **结论ID**: gemini-summary-01
- **结论**: 压缩摘要要求产出结构化 XML `<state_snapshot>`，含 `overall_goal / active_constraints / key_knowledge / artifact_trail / file_system_state / recent_actions / task_state`；提示词含**防注入安全规则**（忽略历史中的指令，绝不退出快照格式）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/prompts/snippets.ts#L898-L977`（`getCompressionPrompt`）；`<SHA>/packages/core/src/prompts/promptProvider.ts#L296-L307`
- **数据走查**: DW-summary-01
- **运行证据**: NOT_RUN（提示词文本由源码直读）
- **不能证明**: 摘要**内容**由模型生成，**不可预知**；不能证明"结构化"保证关键约束不丢（保真度待 T19）
- **冲突裁决**: 支持 T02 §E"摘要/重建"
- **核验日期**: 2026-10-15

### gemini-summary-02 · 保留后 30% + 切点约束 + 函数响应预算

- **结论ID**: gemini-summary-02
- **结论**: 切点 `findCompressSplitPoint(history, 1-0.3)`：保留**后 30%**（`COMPRESSION_PRESERVE_THRESHOLD=0.3`），切点**只落在非 functionResponse 的 user turn**；压缩前 `truncateHistoryToBudget` 对 functionResponse 用 **50,000 token 反向预算**，超预算的旧响应截断落盘。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/context/chatCompressionService.ts#L269`（`0.3`）、`#L274`（`50_000`）、`#L282-L322`（`findCompressSplitPoint`）、`#L364-L464`（`truncateHistoryToBudget`）
- **数据走查**: DW-summary-02
- **运行证据**: NOT_RUN
- **不能证明**: 未实测"后 30%"在真实会话的保留效果；`findCompressSplitPoint` 用 `JSON.stringify(content).length` 计字符（非 token），与 token 预算口径**不完全一致**
- **冲突裁决**: 支持 T02 §E"保留预算/裁剪"
- **核验日期**: 2026-10-15

### gemini-summary-03 · 二次校验 probe（自我纠正）`[待另一 Agent 复核]`

- **结论ID**: gemini-summary-03
- **结论**: 摘要是**两次 LLM 调用**：第一次生成 `<state_snapshot>`，第二次把摘要作为 `model` turn 回灌，问"是否遗漏技术细节/文件路径/约束，有则给最终改进版"；取第二次结果为准（为空则回退第一次）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/context/chatCompressionService.ts#L595-L645`（`promptId: ${promptId}-verify`）
- **数据走查**: DW-summary-03
- **运行证据**: NOT_RUN
- **不能证明**: **未实测**校验轮是否真能减少信息损失（保真收益未验证）；校验轮本身**增加一次调用成本**（代价未量化）
- **冲突裁决**: 支持 T02 §E"增量摘要/重建"；与 C-07"摘要=有独立模型调用"一致（此处为**两次**）
- **核验日期**: 2026-10-15

### gemini-summary-04 · 替代历史重建 + 膨胀即失败

- **结论ID**: gemini-summary-04
- **结论**: 压缩后新历史 = `[user: <state_snapshot>…, model: "Got it. Thanks for the additional context!", ...保留的后 30%]`；用 `getInitialChatHistory` 重拼环境上下文后重算用量，**若新用量 > 原用量 → 判失败**（不采纳）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/context/chatCompressionService.ts#L665-L719`
- **数据走查**: DW-summary-04
- **运行证据**: NOT_RUN
- **不能证明**: 未实测"膨胀即失败"在真实长会话的触发率
- **冲突裁决**: 支持 T02 §E"替代历史"
- **核验日期**: 2026-10-15

### gemini-memory-01 · 长期记忆由模型主动写文件

- **结论ID**: gemini-memory-01
- **结论**: 长期记忆载体是 **GEMINI.md / MEMORY.md 文件**；由**模型**用 `write_file`/`replace` 主动编辑，后续会话自动加载（分层注入）。**不是**后台自动抽取。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/docs/tools/memory.md`；`<SHA>/packages/core/src/tools/memoryTool.ts`；`<SHA>/packages/core/src/context/memoryContextManager.ts`
- **数据走查**: DW-memory-01
- **运行证据**: NOT_RUN
- **不能证明**: 未实测模型何时/是否主动写记忆（模型行为）；未实测记忆体量上限
- **冲突裁决**: 支持 T02 §E"长期记忆"；与**后台提取**（`gemini-memory-02/03`）**互补**——两条记忆路径：①模型主动写 GEMINI.md（本卡，默认开）；②后台提取写 `.inbox` 补丁待审批（默认关）
- **核验日期**: 2026-10-15

### gemini-memory-02 · 后台自动记忆提取**有实现（默认关，实验）**`[待另一 Agent 复核]`

- **结论ID**: gemini-memory-02
- **结论**: **有**"后台持续抽取会话记忆"的实现——`SkillExtractionAgent`（内部名 `confucius`/显示名 `Skill Extractor`），由 `memoryService.startMemoryService` 在**会话启动时后台**运行：扫描 `~/.gemini/tmp/<project>/chats/` 中**空闲 ≥3 小时且 ≥10 条 user 消息**的会话，产出**统一 diff `.patch`**（memory）与 `SKILL.md`（skill）候选，写入 `<projectMemoryDir>/.inbox/<kind>/extraction.patch`，**不自动应用**。**由实验开关 `experimental.autoMemory` 门控，默认 false**（即**默认关**）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`；`experimental.autoMemory`（默认 false）
- **实现状态**: 条件（实验门控，**默认关**）
- **来源**: `<SHA>/packages/core/src/agents/skill-extraction-agent.ts#L26-L490`（`SkillExtractionAgent`，`:31` "You are an Auto Memory Extraction Agent."，`:416-L417` `memoryInboxAccess:true`/`autoMemoryExtractionWriteAccess:true`，`:53` `.inbox`，`:86-L87` "held for /memory inbox review … nothing is applied automatically"）；`<SHA>/packages/core/src/services/memoryService.ts#L1133`（`startMemoryService`）、`#L1258`（调用 `SkillExtractionAgent`）、`#L856`（`validatePatches`）、`#L1371`（"nothing is auto-applied"）；`<SHA>/packages/cli/src/utils/autoMemory.ts#L13-L21`（`startAutoMemoryIfEnabled`，`:14` 门控 `isAutoMemoryEnabled()`）；`<SHA>/packages/core/src/config/config.ts#L1202`（`experimentalAutoMemory ?? false`）、`#L2663-L2665`；`<SHA>/docs/cli/auto-memory.md`（官方文档全文）；`<SHA>/docs/cli/settings.md#L181`（`experimental.autoMemory` 默认 **false**）
- **数据走查**: DW-memory-01
- **运行证据**: NOT_RUN（默认关；且本机未安装 `gemini`，未跑提取）
- **不能证明**: 不能证明开启后提取质量/触发频率；不能证明 `.patch` 应用后的效果（需 `/memory inbox` 人工批准，本包未跑）
- **冲突裁决**: **修正**本包初稿的过头断言"未发现默认实现"（见 `问题与审查.md §0`）——**有实现但默认关**；**修正** LQ-08 回执为"**有实现（默认关）**"。**纪律依据**：D10⑤"未找到当没有"陷阱 + "默认 vs 扩展"分列
- **核验日期**: 2026-10-15

### gemini-memory-03 · Memory Inbox 审批流（`/memory inbox`）

- **结论ID**: gemini-memory-03
- **结论**: 提取候选**不自动应用**：`.inbox/{private,global}/extraction.patch` 经解析 + 目标白名单校验 + dry-run 后，由用户用 `/memory inbox` **人工审批**（apply/dismiss；skill 可 promote 到 user/workspace 技能目录）；private 补丁只能落项目记忆目录，global 补丁只能落 `~/.gemini/GEMINI.md`；**项目 `GEMINI.md` 不可自动提取**（人管）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 条件（实验门控，默认关）
- **来源**: `<SHA>/docs/cli/auto-memory.md#L64-L112`（工作原理 + `/memory inbox` 复核步骤）；`<SHA>/packages/core/src/config/config.ts#L3212-L3321`（`isScopedMemoryInboxPatchPathAllowed`/`isScopedAutoMemoryExtractionWritePathAllowed` 白名单）；`<SHA>/packages/core/src/config/scoped-config.ts#L22-L83`（`memoryInboxAccess`/`autoMemoryExtractionWriteAccess`）；`<SHA>/packages/cli/src/ui/components/InboxDialog.tsx`
- **数据走查**: DW-memory-01
- **运行证据**: NOT_RUN
- **不能证明**: 未实测审批 UI 的交互与 patch 应用结果
- **冲突裁决**: 支持 T02 §E"记忆重注入"；与 `gemini-memory-01`（模型直接写 GEMINI.md）**互补**（两条记忆路径）
- **核验日期**: 2026-10-15

### gemini-cm09-01 · 子 Agent 交接（独立上下文窗口）

- **结论ID**: gemini-cm09-01
- **结论**: `agent` 工具调用子 Agent（如 `codebase_investigator`）；子 Agent 有**独立系统提示词 + 独立上下文窗口 + 独立会话文件**（`<sessionId>.jsonl`）；主 Agent 需发送**完整 prompt**（工具 schema 明确要求"comprehensive and detailed"），子 Agent 完成后把结论**回报**主 Agent。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/docs/core/subagents.md`（"Independent context window … saves tokens in your main conversation history"）；`<SHA>/packages/core/src/agents/agent-tool.ts#L43-L78`；`<SHA>/packages/core/src/services/chatRecordingService.ts#L812-L817`（subagent 文件名）；`<SHA>/packages/core/src/agents/local-executor.ts`
- **数据走查**: DW-cm09-01
- **运行证据**: NOT_RUN
- **不能证明**: **交接材料的生成方式**（是子 Agent 摘要还是原文回报）未逐字段核对；远端子 Agent（`remote-invocation.ts`）行为**不可观测**
- **冲突裁决**: 支持 T02 §E"子 Agent 交接"（Gemini **适用**，区别于 pi 的"不适用"）
- **核验日期**: 2026-10-15

### gemini-persist-01 · 会话追加式 JSONL 落盘

- **结论ID**: gemini-persist-01
- **结论**: 会话以**追加式 JSONL** 落盘：`<chatsDir>/session-<timestamp>-<shortId>.jsonl`（主）/`<sessionId>.jsonl`（子 Agent）；每次消息/工具调用追加写，**不删旧条目**。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/services/chatRecordingService.ts#L670-L830`；`<SHA>/packages/core/src/services/chatRecordingTypes.ts#L12`（`SESSION_FILE_PREFIX='session-'`）、`#L14`（`MAX_TOOL_OUTPUT_SIZE=50*1024`）
- **数据走查**: DW-persist-01
- **运行证据**: NOT_RUN
- **不能证明**: 未实测文件位置在具体平台的实际路径（依赖 `chatsDir` 解析）；未实测长期会话文件体量
- **冲突裁决**: 支持 T02 §E"会话存档"；支持 C-03"历史物理保留"（Gemini 侧）
- **核验日期**: 2026-10-15

### gemini-recover-01 · 恢复 = 从 JSONL 重建历史（重放路线）

- **结论ID**: gemini-recover-01
- **结论**: 恢复走 **"重建/重放"路线**（`convertSessionToClientHistory` 从 JSONL 消息重建 `HistoryTurn[]`，含 toolCalls→functionResponse 配对与去重），**非**"持久化断点"路线（无 `firstKeptEntryId` 式断点）。
- **性质**: 事实（路线）+ 推断（无断点）
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/services/chatRecordingService.ts#L702-L750`（`initialize`/`doInitialize`）；`<SHA>/packages/core/src/utils/sessionUtils.ts#L121-L319`（`convertSessionToClientHistory`）、`#L21-L79`（`ensureStableToolIds`）
- **数据走查**: DW-recover-01
- **运行证据**: NOT_RUN
- **不能证明**: **复跑命令 + 真实输出**：`grep -rniE "firstKeptEntryId|persisted.?breakpoint|tail_start_id" packages/core/src | wc -l` → **`0`**（无断点式恢复符号）→ 路线判定为**推断**。未实测恢复后"是否先重述有效约束"
- **冲突裁决**: **LQ-10**：Gemini = **重放/重建路线**（既非 Codex 的"替代历史+后缀回放"，也非 pi/omp 的"持久化断点"）
- **核验日期**: 2026-10-15

### gemini-fail-01 · 有界重试（maxAttempts=10）

- **结论ID**: gemini-fail-01
- **结论**: 网络/API 重试 `retryWithBackoff`：默认 `maxAttempts=10`、`initialDelayMs=5000`、`maxDelayMs=30000`，指数退避 + 抖动（非 quota ±30%，quota +20% 且尊重服务端最小延迟）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/utils/retry.ts#L20`、`#L42-L47`、`#L322-L323`、`#L483-L485`
- **数据走查**: DW-fail-01
- **运行证据**: NOT_RUN
- **不能证明**: 未实测退避序列；服务端限流策略不可观测
- **冲突裁决**: 支持 T02 §E"有界重试"
- **核验日期**: 2026-10-15

### gemini-fail-02 · 压缩失败分类

- **结论ID**: gemini-fail-02
- **结论**: 压缩状态：`NOOP`/`COMPRESSED`/`CONTENT_TRUNCATED`/`COMPRESSION_FAILED_EMPTY_SUMMARY`/`COMPRESSION_FAILED_INFLATED_TOKEN_COUNT`；`COMPRESSED` 重建会话，`CONTENT_TRUNCATED` 仅改内存历史。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/context/chatCompressionService.ts#L647-L719`；`<SHA>/packages/core/src/core/client.ts#L1246-L1279`；`<SHA>/packages/core/src/core/turn.ts`（`CompressionStatus`）
- **数据走查**: DW-fail-02
- **运行证据**: NOT_RUN
- **不能证明**: 未实测各状态在真实会话的分布
- **冲突裁决**: 支持 T02 §E"失败分类"
- **核验日期**: 2026-10-15

### gemini-fail-03 · 压缩失败降级为"仅截断"（有界）

- **结论ID**: gemini-fail-03
- **结论**: 一旦摘要失败（`hasFailedCompressionAttempt=true`）且非 force → 后续自动压缩**不再调模型摘要**，只做 `truncateHistoryToBudget` 截断（有减量则返回 `CONTENT_TRUNCATED`）；避免反复失败/花费。副作用：落盘文件**不回退**。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 默认
- **来源**: `<SHA>/packages/core/src/context/chatCompressionService.ts#L528-L555`；`<SHA>/packages/core/src/core/client.ts#L1246-L1251`、`#L1270-L1279`
- **数据走查**: DW-fail-03
- **运行证据**: NOT_RUN
- **不能证明**: 未实测"截断-only"模式下模型可见历史的长期质量
- **冲突裁决**: 支持 T02 §E"有界重试/副作用"
- **核验日期**: 2026-10-15

### gemini-cache-01 · CLI 侧只读缓存明细，服务端缓存不可观测 `[待另一 Agent 复核]`

- **结论ID**: gemini-cache-01
- **结论**: **CLI 侧**仅从服务端返回的 `usageMetadata` 读取 `cachedContentTokenCount`（写入遥测/记录），**无**显式缓存断点/缓存键/缓存预热逻辑。**服务端**缓存命中率、TTL、缓存键**全部 `UNOBSERVABLE`**（Gemini API 隐式缓存）。
- **性质**: 事实（CLI 侧）+ 推断（服务端不可观测）
- **范围**: 快照 `42c5182…`；Gemini API
- **实现状态**: 有条件（CLI 仅透传/读取）
- **来源**: `<SHA>/packages/core/src/telemetry/types.ts#L619`（`cached_content_token_count`）、`#L691`（`usage_data?.cachedContentTokenCount ?? 0`）；`<SHA>/packages/core/src/services/chatRecordingService.ts#L1146`；`<SHA>/packages/core/src/agent/event-translator.ts#L462-L470`；检索：`packages/core/src` grep `prompt_cache_key`/`cache_breakpoint` **零命中**
- **数据走查**: DW-cache-01
- **运行证据**: NOT_RUN（服务端 `UNOBSERVABLE`）
- **不能证明**: **复跑命令 + 真实输出**：`grep -rniE "prompt_cache_key|cache_breakpoint|cacheBreakpoint|cacheWarmer" packages/core/src | wc -l` → **`0`**（**无**缓存断点/键/预热逻辑）→ 支持"CLI 无显式缓存控制"。**不能**从 CLI 侧证明任何缓存命中/存活期；**不把缓存 token 重复相加**（本包只报告字段存在）
- **冲突裁决**: 支持 T02 §E"缓存"边界；与术语表"缓存存活期=仍未证实"一致
- **核验日期**: 2026-10-15

### gemini-cache-02 · `cachedContent` 字段透传（配置）

- **结论ID**: gemini-cache-02
- **结论**: 请求配置支持透传 `cachedContent`（缓存内容 ID）到服务端；**默认不使用**（无 CLI 侧创建/管理缓存内容的逻辑）。
- **性质**: 事实
- **范围**: 快照 `42c5182…`
- **实现状态**: 条件（配置透传）
- **来源**: `<SHA>/packages/core/src/utils/apiConversionUtils.ts#L24`、`#L54`（`restPayload['cachedContent'] = sdkCachedContent`）；`<SHA>/packages/core/src/code_assist/converter.ts#L44`、`#L170`
- **数据走查**: DW-cache-01
- **运行证据**: NOT_RUN
- **不能证明**: **复跑命令 + 真实输出**：`grep -rniE "createCachedContent|create_cached_content" packages/core/src | wc -l` → **`0`**（无 CLI 侧创建缓存内容）→ "默认不使用"为**推断**；服务端如何使用 `cachedContent` 字段不可观测
- **冲突裁决**: 支持 T02 §E"缓存"（CLI 侧可证部分）
- **核验日期**: 2026-10-15

---
*配套：`工具概览.md` / `源码导读.md` / `数据走查.md` / `过程观察.md` / `问题与审查.md`。*
