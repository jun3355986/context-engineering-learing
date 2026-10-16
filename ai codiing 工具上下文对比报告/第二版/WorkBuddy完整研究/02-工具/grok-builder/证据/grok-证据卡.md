---
title: Grok Build · 证据卡
task: T12
role: 工具研究 Agent
tool: grok-builder
created: 2026-10-15
spec: 08-验收/T07-后六工具样本规范.md
status: SUBMITTED（待独立复核）
---

# Grok Build · 证据卡（40 张）

> 格式依任务书 §4.4 / 规范 §2；每卡强制含「性质/范围/实现状态/来源/不能证明/冲突裁决/核验日期」。
> 角标：【①文档】官方文档承诺；【①文档·两版一致】= 1.0.50 与 1.0.52 自带文档逐文件 diff 后**内容一致**；【①文档·1.0.52】= 仅 1.0.52 提取版有；【②分发件观察】= 本机分发包/文件/运行可观测。
> 链接基址（闭源无 SHA 链接）：官方产品页 `https://x.ai/build`；可核验锚点 = **分发包 sha256 + 本地路径 + 随包文档路径**。

---

## 族 A：身份与版本

### grok-version-01｜官方名与身份
```yaml
结论ID: grok-version-01
结论: 研究对象官方名为「Grok Build」（两词、无 -er）；任务书作「Grok Builder」；xAI 官方闭源 CLI，命令 grok，主页 x.ai/build。
性质: 事实
范围: 产品身份；所有版本
实现状态: 默认
来源: 【②分发件观察】`grok --help` 首行「Grok Build TUI」；00-管理/版本表 §1 行7；§4 Q4
数据走查: DW-dist-01
运行证据: NOT_RUN（身份为文档/分发件级，无需运行）；版本表 T01 已验收
不能证明: 不能证明 x.ai/build 页面内容与本地二进制一致（未联网核页）；不能把 grok.com 网页版/Grok API 当作同一实现。
冲突裁决: 支持 版本表 Q4（统一用 Grok Build）；纠正任务书用名。
核验日期: 2026-10-15
```

### grok-version-02｜版本双重口径与漂移（高风险·待复核）
```yaml
结论ID: grok-version-02
结论: 研究冻结件为 1.0.50（sha256 af41b1d6…696e6，与版本表 §2 一致）；本机会话期间自动升级到 1.0.52（sha256 c2caa989…4bbb9，`grok --version` 自报「1.0.52 (0920c8169e27)」）；随包文档在升级时刻被重新提取为 1.0.52。
性质: 事实
范围: 本地观测环境；2026-10-15
实现状态: 默认（auto_update 默认开）
来源: 【②分发件观察】`grok --version`（会话起始=1.0.50 c58f321264ba，后=1.0.52 0920c8169e27）；`~/.grok/version.json`（version=1.0.52，checked_at 2026-10-14T18:39:57Z）；`shasum -a 256` 两个 downloads 文件；`~/.grok/docs/user-guide/*` mtime=2026-10-15 02:39:57；版本表 §2
数据走查: DW-version-01
运行证据: OBS-grok-dist-01（会话期内 `grok --version` 两次）
不能证明: 不能证明 1.0.52 相对 1.0.50 的全部实现差异（只有文档 diff + 行为抽样）；不能证明其他机器会同时升级。
冲突裁决: **限制**版本表 §2「本地二进制 sha256 af41b1d6…（1.0.50）」为"冻结件"口径——冻结件未删仍可复现，但**本机实际运行版本已变为 1.0.52**，需在版本表补记。
核验日期: 2026-10-15
```

### grok-version-03｜闭源边界
```yaml
结论ID: grok-version-03
结论: Grok Build 实现闭源（预编译原生二进制，无公开实现仓库）；可观测=官方文档承诺 + 分发件/本地文件/运行行为；不可观测=内核实现与服务端。
性质: 事实
范围: 全部版本
实现状态: 默认
来源: 【②分发件观察】`file` = `Mach-O 64-bit executable arm64`；版本表 §1 行7「闭源，无公开仓库」
数据走查: —
运行证据: NOT_RUN（边界声明）
不能证明: 不能证明任何"源码级"细节；不得据二进制字符串推断实现。
冲突裁决: 支持 T05 闭源路线（三级证据、禁逆向、UNOBSERVABLE）。
核验日期: 2026-10-15
```

---

## 族 B：分发件观察

### grok-dist-01｜顶层帮助与子命令清单
```yaml
结论ID: grok-dist-01
结论: `grok --help` 暴露顶层选项（--system-prompt-override/--rules/--agents/--no-subagents/--max-turns/--fork-session/--resume/--continue/--session-id/--output-format/--sandbox/--permission-mode 等）与子命令（agent/clone/export/inspect/leader/mcp/memory/models/plugin/sessions/setup/trace/update/usage/version/worktree/wrap/doctor/du/dashboard 等）。
性质: 事实
范围: 1.0.50 与 1.0.52（帮助文本一致段）
实现状态: 默认
来源: 【②分发件观察】`grok --help`、`grok memory/sessions/usage/export/inspect/agent/trace --help`
数据走查: DW-dist-01
运行证据: OBS-grok-dist-01
不能证明: 帮助文本**不列全部标志**（官方 README 亦提示）；子命令存在 ≠ 对应机制默认启用。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-dist-02｜随分发件提取的官方文档
```yaml
结论ID: grok-dist-02
结论: 分发件随包携带官方文档：`~/.grok/README.md`（约 2,700 行）+ `~/.grok/docs/user-guide/01..27`（27 篇，合计约 11.2k 行）；`26-config-reference.md` 自述"on launch"提取。
性质: 事实
范围: 1.0.50 与 1.0.52（均含，逐文件 diff 有差异）
实现状态: 默认
来源: 【①文档】`~/.grok/README.md`、`~/.grok/docs/user-guide/*`；26-config-reference.md L3
数据走查: DW-dist-02
运行证据: OBS-grok-dist-01
不能证明: 随包文档=承诺行为，不等于该版本实际运行；文档不带版本号。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-dist-03｜产品家目录布局
```yaml
结论ID: grok-dist-03
结论: 产品家目录 `~/.grok/`（`GROK_HOME` 可覆盖）含 config.toml、sessions/、memory-v2/、skills/、bundled/、docs/、downloads/、README.md、version.json、marketplace-cache/、installed-plugins/、grove/、worktrees/、memtrace/、logs/ 等。
性质: 事实
范围: 本地 1.0.52 环境
实现状态: 默认（部分目录为使用后产生）
来源: 【②分发件观察】`ls -la ~/.grok/`
数据走查: DW-dist-01
运行证据: OBS-grok-dist-01
不能证明: 本机残留（marketplace-cache/installed-plugins/grove）**不代表官方默认布局**；不同使用史会不同。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-dist-04｜`grok inspect --json` 输出结构
```yaml
结论ID: grok-dist-04
结论: `grok inspect --json` 在合成目录（非 git、未信任）返回 exit 0，顶层 **20** 键：grokVersion/channel/cwd/projectRoot/projectTrusted/projectInstructions/permissions/loginPolicy/hooks/hookLoadErrors/skills/agents/plugins/marketplaces/mcpServers/lspServers/configSources/experiments/externalCompat/configWarnings。
性质: 事实
范围: 1.0.52（本机执行）；--json 为公开接口
实现状态: 默认
来源: 【②分发件观察】`grok inspect --json`（/tmp/grok-obs-01）
数据走查: DW-dist-03
运行证据: OBS-grok-dist-01（PASS exit 0）
不能证明: 该输出是**发现面**（discovery），不等于实际进入请求的内容；未覆盖服务端组装。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-dist-05｜本机污染登记（高风险·影响归因）
```yaml
结论ID: grok-dist-05
结论: 本机 `~/.grok` 环境**受第三方扩展污染**：`grok inspect` 报 hooks 7 条（全部来自 `~/.claude`）、hookLoadErrors 6 条、skills 61 条、mcpServers 4 条、plugins 0；claude 与 cursor 兼容单元（skills/rules/agents/mcps/hooks/sessions）**默认全开**；`memory-v2/` 已建脚手架（global/MEMORY.md 内容为空）；`configWarnings` 报 `privacy` 键未知。
性质: 事实
范围: 本地 1.0.52 环境；2026-10-15
实现状态: 条件（受使用史影响）
来源: 【②分发件观察】`grok inspect --json` 各段；`ls ~/.grok/memory-v2/global/`
数据走查: DW-dist-03
运行证据: OBS-grok-dist-01
不能证明: 受污染环境**不能代表产品默认**；所有本机观测只作**行为样点**。
冲突裁决: 支持 T03/全组纪律「污染环境当默认」防范；本包所有"默认行为"结论以**文档承诺**为准，本机观测仅作样点。
核验日期: 2026-10-15
```

---

## 族 C：请求组装（CM-01）

### grok-assembly-01｜请求组装构成
```yaml
结论ID: grok-assembly-01
结论: 一次请求由系统提示词（默认 / `--system-prompt-override` 整体替换 / `--rules` 追加且包在 `<human_rules>` 块）+ AGENTS.md 项目规则追加 + `<memory>` 段（记忆开启时）+ 工具定义 + 消息列表组成；wire 协议由 `model.<id>.api_backend`（chat_completions/responses/messages）选择。
性质: 事实
范围: 1.0.50/1.0.52（`--rules` 追加语义两版略有差异）
实现状态: 默认
来源: 【①文档】README「AGENTS.md」「Memory」；`docs/user-guide/12-project-rules.md` L171-180；`26-config-reference.md`（agent.system_prompt_label、model.<id>.api_backend）
数据走查: DW-assembly-01
运行证据: NOT_RUN（组装内容未端到端抓取；`system_prompt.txt` 为磁盘侧入口）
不能证明: 具体拼接字节序与模板文本（闭源）；`<human_rules>`/`<memory>` 块的确切渲染。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-assembly-02｜组装结果的磁盘侧可观测入口
```yaml
结论ID: grok-assembly-02
结论: 会话目录落盘 `system_prompt.txt`（渲染后系统提示词原文）、`prompt_context.json`（渲染输入）、`tool_definitions.json`（最新模型调用发送的函数工具，**不含 MCP server__tool**——MCP 走 search_tool/use_tool）。
性质: 事实
范围: 1.0.52 文档；1.0.50 文档同段一致
实现状态: 默认
来源: 【①文档·两版一致】`docs/user-guide/17-sessions.md` L31-42
数据走查: DW-persist-01
运行证据: NOT_RUN（本机未逐文件核对 system_prompt.txt 内容）
不能证明: 该文件是"渲染后原文"，但**不保证**与网络请求字节完全一致（服务端可能再加工）。
冲突裁决: 无
核验日期: 2026-10-15
```

---

## 族 D：项目规则 / 技能（CM-02）

### grok-rule-01｜AGENTS.md 发现顺序与文件名
```yaml
结论ID: grok-rule-01
结论: Grok 在每个目录按文件名 `Agents.md / Claude.md / CLAUDE.md / CLAUDE.local.md / AGENT.md / AGENTS.md` 发现项目规则；顺序 = 家目录 →（git 仓库时）从 repo 根到 CWD 逐目录 → 非 git 时仅 CWD；深层文件在后、冲突时胜出；被 gitignore 的跳过；**启动加载需文件夹信任**。
性质: 事实
范围: 1.0.50/1.0.52（L87 新增符号链接一条，1.0.52）
实现状态: 默认
来源: 【①文档】`docs/user-guide/12-project-rules.md` L3/L17-26/L58-88；README「AGENTS.md」
数据走查: DW-rule-01
运行证据: OBS-grok-dist-01（合成目录未信任→未加载项目文件，仅加载全局 ~/.claude/Claude.md）
不能证明: 信任判定的内部实现；交互式授权流程细节。
冲突裁决: 支持「默认 vs 扩展」纪律——本机 61 skills/7 hooks 属扩展面。
核验日期: 2026-10-15
```

### grok-rule-02｜rules 目录集合
```yaml
结论ID: grok-rule-02
结论: 除 AGENTS.md 外，Grok 扫描规则目录 `<dir>/.grok/rules/`（恒扫）、`.claude/rules/`、`.cursor/rules/`（兼容可配），以及家级 `$GROK_HOME/rules/`、`~/.claude/rules/`、`~/.cursor/rules/` 与 `[paths] extra_rule_dirs`；每目录内 `*.md` 按字母序，不扫子目录。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认
来源: 【①文档·两版一致】`docs/user-guide/12-project-rules.md` L28-54
数据走查: DW-rule-01
运行证据: NOT_RUN（合成目录规则因未信任未加载）
不能证明: 各兼容单元默认值的最终合并顺序（受 requirements/managed 影响）。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-rule-03｜技能发现与内联上限
```yaml
结论ID: grok-rule-03
结论: 技能从 4 位置按优先级发现（`./.grok/skills/` > `<repo>/.grok/skills/` > `~/.grok/skills/` > `~/.claude/skills/`，同名高优先覆盖）；`/skills <name>` 注入上下文；模型可依 description 自动调用；**技能体最多内联前 25,000 tokens**（与 read_file 同上限），更长内容应放兄弟文件按行偏移读取。
性质: 事实
范围: 1.0.50/1.0.52（README 技能段一致）
实现状态: 默认
来源: 【①文档】README「Skills」；`docs/user-guide/08-skills.md` L235
数据走查: DW-rule-01
运行证据: NOT_RUN（未做技能注入实测）
不能证明: 25,000 tokens 的**分词口径**（服务端/本地估算）；"前 25,000 tokens"的截断点是否含 frontmatter。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-rule-04｜项目规则文件大小口径内部冲突（未决）
```yaml
结论ID: grok-rule-04
结论: 官方文档对"项目规则文件是否有大小上限"**自相矛盾**：README「AGENTS.md」段称「Each file is capped at 10,000 characters（超出截断并告警）」；`12-project-rules.md`「File Size」段称「Grok loads each project instruction file in full; there is no character cap and no truncation」。
性质: 事实（记录文档冲突）；**哪条为准=未决**
范围: 1.0.50/1.0.52（两版均同时存在两段）
实现状态: 未证实
来源: 【①文档】`~/.grok/README.md`（AGENTS.md 段）vs `docs/user-guide/12-project-rules.md` L183-185
数据走查: DW-rule-01
运行证据: NOT_RUN（需构造 >10,000 字符规则文件做实测，属 T19）
不能证明: 无法据文档裁决；**不得**挑"更自信的一段"当结论（冲突表 §3 纪律）。
冲突裁决: **未决**；登记为内部文档冲突，影响 CM-02 的"装多少"结论。留给 T19 实测或 T21 复核。
核验日期: 2026-10-15
```

---

## 族 E：资料选择与代码检索（CM-03）

### grok-retrieval-01｜按需工具与代码图索引
```yaml
结论ID: grok-retrieval-01
结论: 资料选择走**按需工具**（read_file/grep_search/list_dir/search_replace）；`features.codebase_indexing` **默认 true**（代码图索引，可传 include/exclude glob）；`tools.respect_gitignore`（1.0.52 config 示例默认 false，README 示例默认 true——口径不一，见 Q-04）门控是否跳过被忽略文件；读到初始集合之外的目录时**按需读取**其规则文件（JIT）。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认（codebase_indexing 默认 true）
来源: 【①文档】README「Built-in Tools」「File References」；`05-configuration.md` L97/L108；`12-project-rules.md` L85-88；`26-config-reference.md`（features.codebase_indexing、tools.respect_gitignore）
数据走查: DW-retrieval-01
运行证据: NOT_RUN（未做检索实测）
不能证明: 代码图索引的实际召回质量与是否进入请求；JIT 触发的精确条件。
冲突裁决: 无
核验日期: 2026-10-15
```

---

## 族 F：工具输出治理（CM-04）

### grok-toolout-01｜bash 输出上限（高风险·待复核）
```yaml
结论ID: grok-toolout-01
结论: bash 工具捕获输出上限 `toolset.bash.output_byte_limit` 默认 **65536 字节（64 KiB）**；前台命令超时 `toolset.bash.timeout_secs` 默认 **120.0 秒**，模型可请求前台超时受 `max_timeout_secs` 封顶。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认
来源: 【①文档·两版一致】`~/.grok/README.md`（Configuration 示例 `output_byte_limit = 65536  # max output size (64KB)`）；`26-config-reference.md`（toolset.bash.*）
数据走查: DW-toolout-01
运行证据: NOT_RUN（未做超限实测；数值为**字节**非字符/token）
不能证明: 截断是"保头"还是"保头尾"；是否落盘全文（文档未描述 bash 输出落盘路径）。
冲突裁决: 无（区别于 Claude Code 的 30,000 **字符**与 2,000 字符预览——**单位不同，不得互套**）。
核验日期: 2026-10-15
```

### grok-toolout-02｜MCP 与请求体上限
```yaml
结论ID: grok-toolout-02
结论: MCP 工具输出上限 `mcp.max_output_bytes`（项目文件可设）；单次请求体上限 `model.<id>.max_request_bytes`，未设时继承 `[model_providers.<id>]`，再落到 `api_backend` 默认：`messages` **30 MB**、其他 **50 MiB**；内联图片会被驱逐以不超限。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认
来源: 【①文档·两版一致】`26-config-reference.md`（mcp.max_output_bytes；model.<id>.max_request_bytes）
数据走查: DW-toolout-01
运行证据: NOT_RUN
不能证明: MCP 输出超限时的截断策略与是否落盘；图片驱逐顺序。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-toolout-03｜工具结果剪枝（高风险·待复核）
```yaml
结论ID: grok-toolout-03
结论: Grok 有**工具结果剪枝**层 `[compaction.pruning]`：`enabled` 默认 **true**；`keep_last_n_turns` 默认 **3**（最近 3 轮工具结果永不剪）；`soft_trim_threshold` 默认 **4000 字符**（旧工具结果超过则软裁）；`soft_trim_head`/`soft_trim_tail` 各 **1500 字符**（保留头尾）；`hard_clear_age_turns` 默认 **10**（超龄替换为占位符）。
性质: 事实
范围: 1.0.50/1.0.52（两版一致）
实现状态: 默认
来源: 【①文档·两版一致】`docs/user-guide/13-memory.md` L351-362（"You configure pruning under `[compaction]`, not `[memory]`"）
数据走查: DW-toolout-02
运行证据: NOT_RUN（未做剪枝实测）
不能证明: 剪枝发生在**请求组装前**还是压缩时；软裁是否保留中间标记；与 bash 字节截断的先后顺序。
冲突裁决: 无（这是 Grok 相对 Claude/Codex 的**独有**裁剪层，T14 比较时单列）。
核验日期: 2026-10-15
```

---

## 族 G：窗口计量与触发（CM-05）

### grok-trigger-01｜窗口来源
```yaml
结论ID: grok-trigger-01
结论: 上下文窗口由 `model.<id>.context_window`（tokens）给出，驱动自动压缩时机；未指定时回落到已知模型的**内置默认**；可用 `context_windows = [256000, 500000]` 提供多选，`context_window` 为默认（未设时取列表首个）。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认
来源: 【①文档·两版一致】`26-config-reference.md` L408；`~/.grok/README.md` L1846-1851（Custom Models）
数据走查: DW-trigger-01
运行证据: OBS-grok-dist-01（本地某会话 `signals.json`：`contextWindowTokens=500000`，`contextTokensUsed=137902`，`contextWindowUsage=27`）
不能证明: 各模型内置默认窗口的**具体数值表**（文档只给个别示例）；服务端实际窗口。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-trigger-02｜触发阈值默认 85%（高风险·待复核）
```yaml
结论ID: grok-trigger-02
结论: 自动压缩触发线 = `session.auto_compact_threshold_percent`，默认 **85**（占 `context_window` 的百分比，取值 0–100）；可被 `model.<id>.auto_compact_threshold_percent`（0–100）**逐模型覆盖**；另有 `model.<id>.compaction_at_tokens` 提供**绝对 token 阈值**。
性质: 事实
范围: 1.0.50/1.0.52（两版一致）
实现状态: 默认
来源: 【①文档·两版一致】`docs/user-guide/05-configuration.md` L104（`= 85    # auto-compact at this % of context window (default: 85)`）；`docs/user-guide/04-slash-commands.md` L31（"auto-compacts once the context window hits 85%"）；`26-config-reference.md`（session.auto_compact_threshold_percent；model.<id>.auto_compact_threshold_percent；model.<id>.compaction_at_tokens）
数据走查: DW-trigger-01
运行证据: OBS-grok-dist-01（本地会话 `signals.json` 有 `compactionCount`/`totalTokensBeforeCompaction` 字段，该会话为 0）
不能证明: requirements/managed/远端 pin 的**实际下发值**可能覆盖 85（U-04）；"85%"的分母是否含工具定义/系统提示词。
冲突裁决: **否证** C-01/C-02 的「90%–95% 总括句」在 Grok Build 侧——Grok 默认 **85%**；支持"各家不同、须逐工具核"。
核验日期: 2026-10-15
```

### grok-trigger-03｜触发与用量的可观测入口
```yaml
结论ID: grok-trigger-03
结论: 用量可观测入口：`/context`（把窗口分为 System prompt / Messages / Reasoning·overhead / Free）；`/session-info`（已用/总量/百分比）；会话 `signals.json`（`contextWindowUsage`/`contextTokensUsed`/`contextWindowTokens`/`compactionCount`/`totalTokensBeforeCompaction`）；status-line 变量 `context_window.auto_compact_threshold_percent`。
性质: 事实
范围: 1.0.50/1.0.52（`25-status-line.md` 变量 1.0.50 亦有）
实现状态: 默认
来源: 【①文档】`04-slash-commands.md` L33-40；`17-sessions.md` L176-195；`25-status-line.md` L105-106；【②分发件观察】本地 `signals.json` 字段
数据走查: DW-trigger-01
运行证据: OBS-grok-dist-01
不能证明: `contextTokensUsed` 是本地估算还是服务端回传；`/context` 各分段口径。
冲突裁决: 无
核验日期: 2026-10-15
```

---

## 族 H：自动 / 手动压缩（CM-06）

### grok-compact-01｜自动与手动入口
```yaml
结论ID: grok-compact-01
结论: 手动 `/compact` 压缩会话历史；自动压缩在窗口接近上限时触发并给 TUI 通知；触发线由模型 `context_window` + `auto_compact_threshold_percent`（默认 85）决定。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认
来源: 【①文档·两版一致】`17-sessions.md` L162-172；`04-slash-commands.md` L27-31
数据走查: DW-compact-01
运行证据: NOT_RUN（未触发真实压缩）
不能证明: 自动压缩在轮前/轮中/轮后的**确切时机**（文档未明说）。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-compact-02｜两趟压缩与策略（高风险·待复核）
```yaml
结论ID: grok-compact-02
结论: `features.two_pass_compaction` 默认 **true**（"prefire two-pass compaction"）；压缩策略 `features.compaction_mode` ∈ {summary, transcript, segments}；`features.compaction_detail` ∈ {none, minimal, balanced, verbose}（segments 模式的逐字细节层级）；`features.compaction_verbatim_input` 默认 true；另有 `features.compaction_tool_choice`。
性质: 事实
范围: 1.0.50/1.0.52（两版一致）
实现状态: 默认（two_pass 默认开；compaction_mode/detail 为可配项）
来源: 【①文档·两版一致】`docs/user-guide/05-configuration.md` L98；`26-config-reference.md` L219-222
数据走查: DW-compact-02
运行证据: NOT_RUN
不能证明: "两趟"的两趟各做什么（闭源 U-01）；segments 模式逐字保留的精确规则。
冲突裁决: 支持"层数不是维度"——不按"几层压缩"比较；Grok 的策略是**模式 + 细节层级**，非层叠管道。
核验日期: 2026-10-15
```

### grok-compact-03｜压缩剩余上下文的发送方式与可观测事件
```yaml
结论ID: grok-compact-03
结论: `model.<id>.compactions_remaining`（别名 `send_compactions_remaining`）控制"压缩剩余上下文如何发送"；压缩可观测：OTEL `grok_code.compaction`（`duration_ms`/`tokens_before`/`tokens_after`/`model?`）；headless `streaming-messages-json` 的 `system`/`compact_boundary` 帧标记一次自动压缩；`streaming-json` 可能发 `auto_compact_*` 事件；`signals.json` 有 `compactionCount`。
性质: 事实
范围: 1.0.50/1.0.52（`compactions_remaining` 两版一致；OTEL 事件 1.0.50/1.0.52 一致）
实现状态: 默认
来源: 【①文档·两版一致】`26-config-reference.md` L407；`24-monitoring-usage.md` L301；`14-headless-mode.md` L247/L268
数据走查: DW-compact-02
运行证据: NOT_RUN（未触发压缩）
不能证明: `tokens_before/after` 的计量口径；`compactions_remaining` 的取值语义细节。
冲突裁决: 无
核验日期: 2026-10-15
```

---

## 族 I：摘要 / 裁剪 / 重建（CM-07）

### grok-summary-01｜压缩产物
```yaml
结论ID: grok-summary-01
结论: 压缩（手动或自动）在会话目录保存状态到 `compaction_checkpoints/`。
性质: 事实
范围: 1.0.50/1.0.52（README 描述为 "saved state from auto-compact"；17-sessions.md 为 "manual or auto"）
实现状态: 默认（有压缩时才生成）
来源: 【①文档·两版一致】`17-sessions.md` L38；`~/.grok/README.md` L2421
数据走查: DW-summary-01
运行证据: NOT_RUN（本地抽样会话未见该目录——未触发压缩）
不能证明: checkpoint 的**内容结构**与是否可逆恢复；`compaction_checkpoints/` 缺失≠"没有实现"（仅该会话未压缩）。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-summary-02｜裁剪层（剪枝）与摘要层分列
```yaml
结论ID: grok-summary-02
结论: Grok 的"缩短"含**两层且性质不同**：(a) **裁剪层** = `[compaction.pruning]` 工具结果软裁（4000/1500/1500）+ 硬清（>10 轮占位符）；(b) **摘要层** = `/compact` / 自动压缩生成的替代历史（`compaction_mode`）。两层必须分列，不得合并成"压缩"一词。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认（pruning enabled 默认 true）
来源: 【①文档·两版一致】`13-memory.md` L351-362；`17-sessions.md` L162-172
数据走查: DW-summary-01
运行证据: NOT_RUN
不能证明: 两层的**执行顺序**与是否同时作用于同一批数据。
冲突裁决: 支持 C-10「层数不是维度」——Grok 可证实的"缩短层"= 裁剪 + 摘要（两性质），不按数量叙事。
核验日期: 2026-10-15
```

### grok-summary-03｜压缩保真度（未决）
```yaml
结论ID: grok-summary-03
结论: 压缩后的信息保真度、连续多次压缩是否失真——**未决**。可证实的只有：有 `compaction_detail` 逐字层级（none..verbose）与 segments 模式；OTEL 暴露 tokens_before/after。
性质: 推断（未决）
范围: 全部版本
实现状态: 未证实
来源: 【①文档】`26-config-reference.md` L219-220；【②分发件观察】OTEL 事件字段
数据走查: DW-summary-01
运行证据: NOT_RUN（需 T19 连续三次压缩实验）
不能证明: 不能证明摘要"无损"或"有损"，也不能给出失真度。
冲突裁决: **维持 C-04 未决**（"旧摘要只做字符串级 merge"在 Grok 侧无证据）。
核验日期: 2026-10-15
```

---

## 族 J：长期记忆（CM-08）

### grok-memory-01｜默认关 + 优先级（高风险·待复核）
```yaml
结论ID: grok-memory-01
结论: 跨会话记忆为**实验性、默认关闭**（`memory.enabled` 与 `memory_v2.enabled` 默认 **false**）；开启方式 `GROK_MEMORY=1` / TOML / 远端；优先级（1.0.52）：`requirements.toml` pin > `--no-memory` > `GROK_MEMORY` > `[memory_v2] enabled` > `[memory] enabled` > managed 远端 > 关。
性质: 事实
范围: 1.0.50/1.0.52（1.0.52 优先级多一层 requirements）
实现状态: 实验（默认关）
来源: 【①文档】`13-memory.md` L16/L80-97（1.0.52 版）；`26-config-reference.md` L381-382
数据走查: DW-memory-01
运行证据: OBS-grok-dist-01（本机 memory-v2 脚手架存在但 MEMORY.md 空）
不能证明: 远端 managed 实际下发值（U-04）。
冲突裁决: 支持「默认 vs 扩展」纪律——**不得**把"Grok 有记忆"当默认能力。
核验日期: 2026-10-15
```

### grok-memory-02｜存储布局
```yaml
结论ID: grok-memory-02
结论: 记忆存于 `~/.grok/memory-v2/`：`global/` 与 `workspaces/<project-slug>-<hash8>/`；每 scope 含 `topics/`（一主题一 md）、`observations/_inbox/`、`MEMORY.md`（生成的索引，勿手改），以及 SQLite 状态（index.sqlite / memory_state.sqlite）与 archive/。workspace 目录名 hash 由 git remote URL 派生，同一仓库的 clone/worktree 共享。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 实验
来源: 【①文档·两版一致】`13-memory.md` L104-122；【②分发件观察】`find ~/.grok/memory-v2`
数据走查: DW-memory-01
运行证据: OBS-grok-dist-01
不能证明: SQLite 内部 schema 与检索实现（闭源）。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-memory-03｜后台复盘 + Dream + 索引注入
```yaml
结论ID: grok-memory-03
结论: 每完成一轮，Grok **在后台复盘该轮**并把新事实写入 `observations/_inbox/`（提前停止的轮也捕获）；Dream 在一个 scope 有 **≥20 条** inbox 观察或最旧观察 **≥24 小时**时自动折叠进 topics；索引每会话注入一次（每 scope ≤ **8 KiB**）；注入时发遥测 `grok-shell-memory_injection`（含各 scope 条目数、注入字节与估算 tokens、是否用 compact index）。
性质: 事实
范围: 1.0.50/1.0.52（README 与 13-memory.md 一致）
实现状态: 实验（默认关）
来源: 【①文档】`~/.grok/README.md`（Memory「What gets saved automatically」）；`13-memory.md` L126-130/L280-290；`26-config-reference.md`（memory_v2.compact_index_enabled / daily_token_cap）
数据走查: DW-memory-01
运行证据: NOT_RUN（本机未开启记忆捕获；`memory-v2` 内容为空）
不能证明: 捕获所用模型的实际输出与质量（U-05）；"8 KiB"是字节预算的确切切法。
冲突裁决: 见 grok-memory-04（对 LQ-08）。
核验日期: 2026-10-15
```

### grok-memory-04｜对 LQ-08「后台持续抽取会话记忆」的裁决
```yaml
结论ID: grok-memory-04
结论: 对 LQ-08：Grok Build **确有**"每轮后台复盘写入观察"的机制（文档明述），Dream 亦自动触发——但它是**默认关的实验特性**，不是"默认行为"；因此旧表述"后台持续抽取会话记忆"在 Grok 侧**有条件成立**（仅当显式开启 memory），不能写成默认。
性质: 推断（基于文档承诺；默认关为事实）
范围: 1.0.50/1.0.52
实现状态: 实验
来源: 【①文档】`13-memory.md` L126-130；`~/.grok/README.md` Memory 段；`26-config-reference.md` L381-382（默认 false）
数据走查: DW-memory-01
运行证据: NOT_RUN
不能证明: 后台复盘是否"持续多次小请求"（文档说"reviews the turn in the background"，未描述请求粒度）；`memory_v2.daily_token_cap` 默认 20,000,000 说明**有模型调用开销**。
冲突裁决: **有条件支持** LQ-08；与 Claude 侧（文档未描述后台抽取）形成对照——Grok 有、但默认关。
核验日期: 2026-10-15
```

---

## 族 K：子 Agent 交接（CM-09）

### grok-cm09-01｜独立窗口 + 默认启用
```yaml
结论ID: grok-cm09-01
结论: 子 Agent **默认启用**（`subagents.enabled` 默认 true，`--no-subagents`/`GROK_SUBAGENTS=0` 关）；每个子 Agent 有**独立上下文窗口**，可选择性继承父会话历史；完成时向父回传摘要（"usually a summary"）。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认
来源: 【①文档】`16-subagents.md` L3/L51/L55；`~/.grok/README.md`「Subagents」；`26-config-reference.md` L553
数据走查: DW-cm09-01
运行证据: OBS-grok-dist-01（本地会话目录 `subagents/` 实测存在）
不能证明: "摘要"是否由子 Agent 自己生成、父实际看到多少；子窗口大小。
冲突裁决: 无（与 pi 的"刻意不含 sub-agents"形成对照）。
核验日期: 2026-10-15
```

### grok-cm09-02｜并发 / 深度 / 模型继承
```yaml
结论ID: grok-cm09-02
结论: 子 Agent 受 `subagents.max_concurrent`、`max_depth`（≥1）、`limit_behavior`（queue/fail）约束；模型默认继承父会话，除非 `[subagents.models].<name>` 或 agent 定义的 `model` 显式 pin；`features.subagent_model_inheritance` 默认 false；`resume_from` 可让新子 Agent 继承源的 transcript/tool state（源须已完成、同会话、同 agent 类型）。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认（继承）/条件（resume_from）
来源: 【①文档】`26-config-reference.md` L553-558/L241；`16-subagents.md` L207-216
数据走查: DW-cm09-01
运行证据: NOT_RUN
不能证明: 并发上限的默认值（文档未给具体数）；`resume_from` 继承的 token 体量。
冲突裁决: 无
核验日期: 2026-10-15
```

---

## 族 L：保存 / fork / 恢复（CM-10）

### grok-persist-01｜会话落盘布局
```yaml
结论ID: grok-persist-01
结论: 会话按 `~/.grok/sessions/<encoded-cwd>/<session-id>/` 落盘，文档列：summary.json（索引条目）、updates.jsonl（**权威对话日志**，驱动 /resume 与恢复）、chat_history.jsonl（发送给模型的原始消息）、system_prompt.txt、prompt_context.json、tool_definitions.json、plan.json、rewind_points.jsonl、signals.json、feedback.jsonl、compaction_checkpoints/、subagents/。JSONL 追加式。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认
来源: 【①文档·两版一致】`17-sessions.md` L26-42；`~/.grok/README.md` L2412-2425；【②分发件观察】本地某会话目录实测（另含 events.jsonl/usage.json/resources_state.json/announcement_state.json/title_refresh_idx 与 .lock，未列在文档清单——**文档清单非穷尽**）
数据走查: DW-persist-01
运行证据: OBS-grok-dist-01
不能证明: 各文件在恢复时的**读取优先级**（除 updates.jsonl 为权威外）；追加式写入的并发安全细节。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-persist-02｜会话 ID 与清理
```yaml
结论ID: grok-persist-02
结论: 会话 ID 为 UUIDv7（客户端可用 `-s` 自供，但**只能新建**，采用"反覆盖"模型）；`storage.cleanup_ttl_days` 控制空闲会话目录删除天数（未设或 0 = 禁用）；`grok sessions search` 维护本地 SQLite FTS5 索引。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认
来源: 【①文档·两版一致】`17-sessions.md` L18/L216/L393；`26-config-reference.md` L547
数据走查: DW-persist-01
运行证据: NOT_RUN
不能证明: 清理的默认 TTL（文档未给默认值）。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-recover-01｜恢复路线 = 重放/重建；`/rewind` 不还原文件（高风险·待复核）
```yaml
结论ID: grok-recover-01
结论: 恢复路线为**从 `updates.jsonl` 重放/重建**（"the authoritative conversation log that drives `/resume` and session restore"）；入口 `--resume`/`-r`、`--continue`/`-c`、`--fork-session`、`--restore-code`；`/rewind`（别名 `/undo`）**只截断对话历史、不还原磁盘文件**（"`/rewind` does not restore files on disk. Only conversation history is truncated."）。**注意内部文档冲突**：README 的 TUI 斜杠命令表把 `/rewind <prompt>` 描述为 "restores files"。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认
来源: 【①文档·两版一致】`17-sessions.md` L42/L141-158/L199-224；`~/.grok/README.md` L498（冲突源）
数据走查: DW-recover-01
运行证据: NOT_RUN（未做恢复实测）
不能证明: 恢复是否完全等价于原历史；`rewind_points.jsonl`（README 称"file snapshots"，17-sessions 称"rewind points"）的**真实内容**（文档两处口径不一）。
冲突裁决: **登记内部文档冲突**（`/rewind` 是否还原文件；`rewind_points.jsonl` 语义）；对 LQ-10 给出 Grok = **重放/重建路线**（非持久化断点）。
核验日期: 2026-10-15
```

---

## 族 M：错误与副作用（CM-11）

### grok-fail-01｜重试与限流
```yaml
结论ID: grok-fail-01
结论: 推理重试 `models.max_retries` 默认 **8**；限流总尝试上限 `models.rate_limit_retry_threshold`（配置后禁用独立的子 Agent 429 等待环）；子 Agent 429 等待 `subagent_rate_limit_max_attempts` 默认 **8**、上限 32、`0` 关闭；`inference_idle_timeout_secs` 默认 600（全局）。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认
来源: 【①文档·两版一致】`05-configuration.md` L66-68；`26-config-reference.md` L425/L431/L458
数据走查: DW-fail-01
运行证据: NOT_RUN
不能证明: 退避算法（指数/固定）；重试是否重复副作用。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-fail-02｜doom loop 恢复与沙箱不可逆
```yaml
结论ID: grok-fail-02
结论: `doom_loop_recovery.enabled` 重采样"自信的工具调用循环"；`signals.json` 记 `doomLoopRecoveryAttempts` 等计数；沙箱（Landlock/Seatbelt）一旦在启动时应用即**不可逆**（"security feature — the model cannot convince the agent to relax restrictions"）；沙箱事件写 `~/.grok/sandbox-events.jsonl`。
性质: 事实
范围: 1.0.50/1.0.52（sandbox-events 1.0.50 亦有）
实现状态: 默认（doom loop 默认开；sandbox 默认 off）
来源: 【①文档】`26-config-reference.md` L188；`~/.grok/README.md`「Sandbox」；【②分发件观察】本地 `signals.json` doomLoop* 字段
数据走查: DW-fail-01
运行证据: OBS-grok-dist-01
不能证明: doom loop 判定的内部阈值（闭源）；重采样的副作用。
冲突裁决: 无
核验日期: 2026-10-15
```

---

## 族 N：缓存与总成本（CM-12）

### grok-cache-01｜CLI 侧可观测的三个 token 桶
```yaml
结论ID: grok-cache-01
结论: **CLI 侧可观测**：`usage.json`/`grok usage`/headless JSON 给出三个**不相交**桶——`input_tokens`（**uncached**）、`cache_read_input_tokens`、`cache_creation_input_tokens`，`total_tokens = input + cache_read + cache_creation + output`；会话文件字段名为 `cachedReadTokens`/`cacheCreationTokens`；`costUsdTicks`（1 USD = 10¹⁰ ticks）。
性质: 事实
范围: 1.0.50/1.0.52
实现状态: 默认
来源: 【①文档·两版一致】`14-headless-mode.md` L144-175/L297；`17-sessions.md` L288；【②分发件观察】本地 `usage.json` 字段（session/turns 均含 inputTokens/outputTokens/reasoningTokens/cachedReadTokens/cacheCreationTokens/totalTokens/costUsdTicks/modelCalls）
数据走查: DW-cache-01
运行证据: OBS-grok-dist-01
不能证明: 这些桶是**服务端回传**（CLI 只 reshape）；缓存是否真命中由服务端决定。
冲突裁决: 无
核验日期: 2026-10-15
```

### grok-cache-02｜服务端缓存 = UNOBSERVABLE
```yaml
结论ID: grok-cache-02
结论: **服务端不可观测**：prompt cache 的**命中率、存活期（TTL）、缓存键、前缀断点**全部落在 `cli-chat-proxy`/`grok.com` 侧；CLI 只能读到读数（`cache_read_input_tokens` 等）与 OTEL `grok_code.token.usage{type=cache_read}`；`total_cost_usd` 仅在服务端报告**完整** cost 时出现（否则 `cost_is_partial` 且省略全部 cost 浮点）。
性质: 事实（可观测部分）/ 推断（不可观测边界）
范围: 1.0.50/1.0.52
实现状态: 未证实（服务端）
来源: 【①文档·两版一致】`24-monitoring-usage.md` L231/L293；`14-headless-mode.md` L184-200
数据走查: DW-cache-01
运行证据: NOT_RUN（服务端行为不可控）
不能证明: 命中率、TTL、缓存键；不得把"有 cache_read 读数"当作"缓存一定命中"。
冲突裁决: 支持规范 §3「CM-12 区分 CLI 侧可证 / 服务端 UNOBSERVABLE」。
核验日期: 2026-10-15
```

---

*配套：`工具概览.md` / `证据导读.md` / `数据走查.md` / `过程观察.md` / `问题与审查.md`；冻结件：`~/.grok/downloads/grok-1.0.50-macos-aarch64`（sha256 `af41b1d6…696e6`）。*
