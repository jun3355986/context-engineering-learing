---
title: T19 批次 7 · Grok Build 真实机制实验记录
task: T19
batch: 7
tool: grok-builder
role: 实验 Agent（t19-grok）
created: 2026-10-15
spec: 05-实验/T03/实验规程.md + 运行记录模板.md；02-工具/grok-builder/过程观察.md §5
status: SUBMITTED（待 T19R 复核）
---

# T19 批次 7 · Grok Build（grok）真实机制实验记录

> **本文件解决什么**：在统一条件下用合成数据**真实运行 grok CLI**，给出**条件 / 命令 / 文件 / 预期事件 / 真实结果 / 失败案例与解释**，使读者能照着复现；并**实测裁决 T12 遗留的 Q-01**（`/rewind` 是否还原磁盘文件）。
> **本文件不做什么**：不做性能排名；不声称统计显著（探索性小样本，每条件 3 次）；不把 HTTP 200 或模型自述当推理成功。

---

## 0. 运行标识（两类共用）

| 字段 | 值 |
|---|---|
| 运行 ID 族 | `MECH-grok-trigger-*` / `MECH-grok-toolout-*` / `MECH-grok-compactcont-*` / `MECH-grok-rewind-*` / `MECH-grok-memory-*` / `MECH-grok-cache-*` |
| 运行日期 / 时区 | 2026-10-15（CST, UTC+8）；日志内时间戳为 UTC（+08:00 换算） |
| 执行者 | t19-grok（实验 Agent） |
| 对应场景 | E1 关键约束保留（条件 1）、E2 大工具输出（条件 2）、E3 连续三次压缩（条件 3）、CM-10 恢复/裁决 Q-01（条件 4）、CM-08 记忆（条件 5，选做）、CM-12 缓存（条件 6） |
| 任务数据包 ID + 版本哈希 | `T03-DATA-TRIP-v1`（整包摘要哈希见 `05-实验/T03/任务数据-行程任务-v1/manifest.sha256`）；大输出另用 `05-实验/T19/样本/长工具结果-公交查询-v2.txt`（2,254 行 / 161,144 字节；sha256 `1c9309e7…011b`） |
| **实际执行的可执行版本** | **grok 1.0.52（`0920c8169e27`）**（开跑日 `grok --version` 复测，见 §9） |
| **研究快照 / 冻结分发包** | 冻结件 **1.0.50**（`~/.grok/downloads/grok-1.0.50-macos-aarch64`，sha256 `af41b1d65d4116ff649a689ad9d070d4c2abe255737d46ba0b3e8161345696e6`，开跑日复核**逐位一致**）；另有 1.0.52 分发包 sha256 `c2caa9895dd763297a75e8fb6077e175d9c5304c53903e52cff8891a1384bbb9` |
| 两者是否一致 | **不一致**：本地执行 1.0.52，研究快照为 1.0.50 → 本记录结论**只对 1.0.52 有效**；基于 1.0.50 写的结论**不得**用本轮观测互证（T03 规程 §1） |
| 模型 / provider / 登录方式 | 会话自报 `grok-4.7`（`signals.primaryModelId`）／响应 `modelUsage` 键为 `grok-4.7-build`；`grok models` 显示 "You are logged in with grok.com"，默认模型 `grok-4.7`；可用：grok-4.7 / grok-4.7-build-fast / grok-4.6 / grok-4.5 |
| 生效配置与覆盖 | 隔离 `GROK_HOME=/tmp/t19-grok` + `HOME=/tmp/t19-grok-home` + `GROK_DISABLE_AUTOUPDATER=1` + `GROK_SUBAGENTS=0`；`[session] auto_compact_threshold_percent=85`（默认值，未改）；`[model."grok-4.7"] context_window` 按条件改为 30000 / 15000 / 200000（默认 256000）；`[ui] permission_mode="always-approve"` |
| 原始日志路径 | `/Users/junjielong/workspace/agent-context-research/experiments/t19/logs/grok-*.json`（59 个，逐次调用一份）；公开摘录见 `experiments/t19/公开摘录/grok-摘录.md` |
| 状态 | `OBSERVED`（条件 1/2/3/4/6）；`NOT_RUN / UNOBSERVABLE`（条件 5 记忆；TUI slash 路径） |

### 0.1 隔离与"干净环境"（复现必需）

| 项 | 做法 | 结果 |
|---|---|---|
| GROK_HOME | `/tmp/t19-grok`（新建；仅 `auth.json` 从 `~/.grok/auth.json` 复制，**内容不入日志**）+ 最小 `config.toml` | 生效；`grok inspect --json` 的 `configSources.layers` 仅 `/tmp/t19-grok/config.toml` |
| HOME | `/tmp/t19-grok-home`（隔离 `~/.claude` 兼容单元） | 认证仍可用（token 在 GROK_HOME 的 auth.json） |
| 自动更新 | `GROK_DISABLE_AUTOUPDATER=1` | 开跑日与收尾日 `grok --version` 均为 1.0.52，**未再漂移** |
| 子 Agent | `GROK_SUBAGENTS=0` | `signals` 无 subagents 活动；`toolCallCount` 与主会话一致 |
| 污染登记（本机仍可见项） | 未加 HOME 隔离时，`~/.claude` 的 MCP（`mongodb-dev`、`codegraph`）会被 grok 加载（`logs/mcp/*.stderr.log`） | 加 `HOME=` 隔离后不再出现；**本记录全部条件均使用 HOME 隔离**，故非"产品默认"级结论 |

> ⚠️ **本机污染与"产品默认"纪律**：本记录的所有观测都在**隔离 HOME + 隔离 GROK_HOME**下取得，**不代表用户日常环境**；T12 登记的 hooks 7 条 / skills 61 条 / MCP 4 条在本轮被隔离掉。因此本记录可用于**机制归因**，但**不能**直接外推为"Grok 开箱默认行为"。

### 0.2 总归因限制（必读）

1. **版本**：执行 1.0.52 ≠ 研究快照 1.0.50；所有"默认值/常量"结论只对 1.0.52 的**实测行为**作证。
2. **服务端闭源**：压缩摘要由服务端 side-model 生成；prompt cache 命中/TTL/键全部不可观测（§8）。
3. **结构化由人完成**：E1/E3 的候选 JSON 由实验者从模型自然语言输出中**人工提取**（记录里注明每例的提取方式），属已知主观环节。
4. **窗口口径不一致（实测发现）**：`signals.contextWindowTokens` 在**无工具调用**的会话里报配置覆盖值（30000/15000），在**有工具调用**的会话里报内置值（256000）；而 `auto_compact_started.context_window` 始终报**配置覆盖值**（30000/15000）。即：**触发线用配置窗口，signals 的窗口字段在带工具会话中不可靠**（证据见 §2.1）。
5. **TUI 不可用**：本沙箱下 grok 交互 TUI 无法初始化（§7），故 `/context`、`/compact`、`/rewind`、`/flush`、`/dream` 等 slash 路径**未能实测**；相关结论用等价 headless 证据 + 磁盘落盘裁决。

### 0.3 命令纪律（逐字，可重跑）

```zsh
# 环境（所有条件共用）
export GROK_HOME=/tmp/t19-grok
export HOME=/tmp/t19-grok-home
export GROK_DISABLE_AUTOUPDATER=1
export GROK_SUBAGENTS=0
G=/Users/junjielong/.local/bin/grok

# 新建会话（--prompt-file 规避 argv/UTF-8 边界问题；-s 指定 UUIDv7/4）
cd /tmp/t19-grok && $G --prompt-file <PROMPT_FILE> --output-format json > <LOG>.json 2>&1

# 续接会话
$G --prompt-file <PROMPT_FILE> -r <SESSION_ID> --output-format json > <LOG>.json 2>&1
```

> **踩坑记录（复现必读）**：① 用 `-p "$(cat bigfile)"` 传大文本时，若文件按**字节**截断（`head -c`）会切在多字节字符中间 → grok 在 `std::env::set_var` 处 **panic**（`library/std/src/env.rs:871`）；必须按**字符**边界切分或改用 `--prompt-file`。② `[model.grok-4.7]` 这种**未加引号**的 TOML 键会被解析成 `model.grok-4` + 未知字段 `7`（`configWarnings` 可见）→ 必须写 `[model."grok-4.7"]`。

---

## 1. 条件 1 · 触发线 85% + E1 关键约束保留（`MECH-grok-trigger-01/02/03`）

### 1.1 变量与固定量

| 项 | 值 |
|---|---|
| 唯一自变量 | 是否跨过自动压缩触发线（由上下文用量自然跨过；阈值本身固定为默认 85） |
| 固定量 | 工具版本 1.0.52 / 模型 grok-4.7 / provider grok.com / `context_window=30000` / 阈值 85% / 数据 `T03-DATA-TRIP-v1` 内容 / 命令模板 / 初始材料（p1~p4 提示文件） |
| 操作定义 | A 组（对照）= 未跨线；B 组 = 跨线并触发 `auto_compact`；本条件报告 B 组并给出 A 组读数 |

### 1.2 为什么改 `context_window`

默认窗口 **256,000** tokens（`signals.contextWindowTokens` 实测），85% 线 = **217,600** tokens —— 在 ≤10 分钟/≤20 工具动作的预算内**不可能达到**。故按 T03 §1「配置与覆盖须区分默认与配置后启用」，**显式覆盖** `[model."grok-4.7"] context_window = 30000`（85% 线 = 25,500），并如实登记为**条件说明**（不是产品默认）。阈值 `auto_compact_threshold_percent` 保持**默认 85**，未改。

### 1.3 命令模板（逐字）

```zsh
cd /tmp/t19-grok
export GROK_HOME=/tmp/t19-grok HOME=/tmp/t19-grok-home GROK_DISABLE_AUTOUPDATER=1 GROK_SUBAGENTS=0
G=/Users/junjielong/.local/bin/grok
$G --prompt-file /tmp/t19-grok/p1.txt --output-format json > logs/grok-e1-r<R>-p1-<TS>.json 2>&1     # 建会话（p1 = 任务+HC-01/02/03+REJ-01/02+SP）
$G --prompt-file /tmp/t19-grok/p2.txt -r <UUID> --output-format json > logs/grok-e1-r<R>-p2-<TS>.json 2>&1  # 场馆/门票工具结果 + REJ-03
$G --prompt-file /tmp/t19-grok/p3.txt -r <UUID> --output-format json > logs/grok-e1-r<R>-p3-<TS>.json 2>&1  # 公交查询 v1（300 行，22,159 字节）
$G --prompt-file /tmp/t19-grok/p4.txt -r <UUID> --output-format json > logs/grok-e1-r<R>-p4-<TS>.json 2>&1  # 70,019 字符填充 → 跨线
$G --prompt-file /tmp/t19-grok/p5.txt -r <UUID> --output-format json > logs/grok-e1-r<R>-p5-<TS>.json 2>&1  # 恢复入场：出最终方案 + 复述有效约束
```

> **p5 在 3 轮间被修订过（如实登记）**：v1（R1）未要求 `statusClaims` 真值键；v2（R2）示例值写成 `"行程已确认": true`（**有偏置**）；v3（R3 起）改为占位符 `<true|false>` 并加"按事实填写"。该修订**影响 `CHK-FC-STATUS` 一项**，对 HC/REJ 判据无影响（见 §1.6）。

### 1.4 预期事件（先写，后对照）

| # | 预期出现的事件 | 依据（T12 证据卡） |
|---|---|---|
| 1 | 用量跨过 85% 后自动压缩，并出现可见事件 | `grok-trigger-02`（默认 85%）、`grok-compact-01` |
| 2 | 压缩产生 checkpoint 落盘 `compaction_checkpoints/` | `grok-summary-01` |
| 3 | 压缩后压缩摘要替代旧历史，硬约束**仍在最终方案中生效** | `grok-summary-02`、E1 场景 |
| 4 | 不出现被否项复活（REJ-01/02/03） | `grok-summary-02`、检查器 CHK-REJ-STRUCT/SP-02 |
| 5 | 两趟压缩（`two_pass_compaction` 默认 true） | `grok-compact-02` |

### 1.5 观测结果（3 次重复）

**A 组（对照，未跨线）**：R1 p1→p3 用量 1,424 → 1,942 → 7,488（4% → 6% → 24%），`compactionCount=0`。

**B 组（跨线，触发压缩）**：

| 轮次 | p1 | p2 | p3 | p4（跨线） | p5（恢复入场） | 触发百分比 | `compactionCount` | `totalTokensBeforeCompaction` |
|---|---|---|---|---|---|---|---|---|
| R1 | 1,424 (4%) | 1,942 (6%) | 7,488 (24%) | 29,081 (97%) | 7,803→(下一轮刷新) | **97%** | **2** | 36,569 |
| R2 | 1,425 (4%) | 1,943 (6%) | 7,489 (24%) | 29,082 (97%) | 7,803 (26%) | **97%** | **2** | 36,571 |
| R3 | 1,425 (4%) | 1,943 (6%) | 7,489 (24%) | 29,082 (97%) | 7,847 (26%) | **97%** | **2** | 36,571 |
| 中位数 / 范围 | — | — | 7,489 | 29,082 | — | 97%（3/3 一致） | 2 | 36,571（±2） |

> 表内数字为 `signals.json` 的 `contextTokensUsed`（括号内 `contextWindowUsage`，分母 = 配置窗口 30,000）。

**`updates.jsonl` 里的压缩事件（权威可观测，3 轮逐条一致）**：

```text
# R1  01a13e6d-fdc0-7102-8e9f-80efbeb48468
auto_compact_started   {"tokens_used":29081,"context_window":30000,"percentage":97,"reason":"Context window 97% full"}
compaction_checkpoint  {"checkpoint_id":"f7acbf92-8f86-4b79-ab41-240f7f316688","prompt_index_at_compaction":4,"schema_version":1}
auto_compact_completed {"tokens_before":29081,"tokens_after":7488,"elapsed_ms":475938,"summary_preview":null}
# R2  01a13e78-d1be-70e2-bdbd-32c58d3b6316
auto_compact_started   {"tokens_used":29082,"context_window":30000,"percentage":97,...}
auto_compact_completed {"tokens_before":29082,"tokens_after":7489,"elapsed_ms":101224}
# R3  01a13e7c-163d-7462-95ed-43ddc963d682
auto_compact_started   {"tokens_used":29082,"context_window":30000,"percentage":97,...}
auto_compact_completed {"tokens_before":29082,"tokens_after":7489,"elapsed_ms":138436}
```

**关键读数**：

1. **触发在 97% 而非恰好 85%**：判定发生在**该轮消息加入之后**，因此跨线幅度大时会在 85%~100% 之间任意点触发（本条件因一次性加入 70k 字符而落在 97%）。**85% 是"下限判定线"，不是"触发点读数"** —— 这一点 T12 文档未说明，属本轮实测补充。
2. **`compactionCount=2` 但 `updates.jsonl` 只有 1 组 started/completed** → `compactionCount` 计的是**两趟**（`two_pass_compaction` 默认 true），`totalTokensBeforeCompaction` = 两趟 before 之和（29082 + 7489 = 36571）。**这是"两趟压缩"的首个端到端实测证据**（T12 `grok-compact-02` 原为文档级）。
3. **压缩后用量**：`tokens_after ≈ 7,489`（**压缩比 ≈ 74% 缩减**）；下一轮 `signals` 刷新为 26%（≈7,800）。
4. **落盘产物**：`compaction_checkpoints/<uuid>.json`（含 `compacted_history` / `original_user_info` / `reread_file_paths` / `prompt_index_at_compaction`）；`compaction/INDEX.md` + `segment_000.md`（**默认模式 = segments**，`detail=verbose`；R1 另有 8 轮/turn 统计与 curated summary）。
5. **压缩耗时**：`elapsed_ms` 101,224 ~ 475,938（R1 含一次网络 `retry_state` 超时重试，见 §7）。

### 1.6 判据结果（检查器原始输出）

**R1**（p5 = v1 提示；`candidates/grok-e1-r1.json`，**JSON 由实验者从模型输出中人工提取**）：

```text
=== T03-DATA-TRIP-v1 | 候选：grok-e1-r1.json | overall=FAIL ===
  [PASS] CHK-HC-01      returnTime=15:45 vs 上限 16:00（945 vs 960 分钟）
  [PASS] CHK-HC-02      求和 1600  vs 上限 6000
  [PASS] CHK-HC-03      headcount=64 应等于 64
  [PASS] CHK-SP-02      assemblyPointId='LOC-PLAYGROUND' 不得属于被否集合 [...]
  [PASS] CHK-REJ-STRUCT selectedOptionIds=['LOC-BOTANIC','BUS-55','BUS-33','L7-141'] 命中被否项 []
  [PASS] CHK-REJ-TEXT   命中且无否定语境：[]；命中但有否定语境（不判违规）：['校门口集合','科技馆']
  [FAIL] CHK-FC-STATUS  与真值不一致项：[{"key":"车辆预订","claim":null,"truth":"未开始",...},
                        {"key":"校方报备","claim":null,...},{"key":"行程已确认","claim":null,...}]
  命中问题类别：['未完成被写成完成']
exit=1
```

**R2**（p5 = v2 提示；`candidates/grok-e1-r2.json`）：

```text
=== T03-DATA-TRIP-v1 | 候选：grok-e1-r2.json | overall=FAIL ===
  [PASS] CHK-HC-01 / CHK-HC-02 / CHK-HC-03 / CHK-SP-02 / CHK-REJ-STRUCT / CHK-REJ-TEXT   （同上，全 PASS）
  [FAIL] CHK-FC-STATUS  与真值不一致项：[{"key":"行程已确认","claim":true,"truth":false,"type":"未完成写成完成"}]
exit=1
```

**R3**（p5 = v3 提示；`candidates/grok-e1-r3.json`）：

```text
=== T03-DATA-TRIP-v1 | 候选：grok-e1-r3.json | overall=FAIL ===
  [PASS] CHK-HC-01 / CHK-HC-02 / CHK-HC-03 / CHK-SP-02 / CHK-REJ-STRUCT
  [FAIL] CHK-REJ-TEXT   命中且无否定语境：['科技馆']；命中但有否定语境（不判违规）：['校门口集合']
  [PASS] CHK-FC-STATUS  与真值不一致项：[]
exit=1
```

| 指标 | R1 | R2 | R3 |
|---|---|---|---|
| 任务是否通过 | FAIL | FAIL | FAIL |
| 关键约束违背数（CHK-HC-*） | **0** | **0** | **0** |
| 否决复活数（CHK-REJ-STRUCT/SP-02 结构化） | **0** | **0** | **0** |
| 否决复活数（CHK-REJ-TEXT 文本层） | 0 | 0 | **1（已人工复核，判为误报）** |
| 未完成写完成数（CHK-FC-STATUS） | 3（**缺字段**） | 1（**声明 true**） | 0 |
| 体积缩减率（仅参考） | 74%（29081→7488） | 74% | 74% |

> ⚠️ **判据降级标注（T03 规程 §5，必读）**：
> - **R3 的 `CHK-REJ-TEXT` FAIL 不构成"复活"结论。** 结构化判据 `CHK-REJ-STRUCT`（selectedOptionIds 求交）与 `CHK-SP-02`（集合点）**均 PASS**；文本层命中的原因是 R3 的 `notes` 把"科技馆（周五闭馆）"放在**与"已否决："不同的小句**里，规则式否定语境未覆盖 → **启发式误报**。**已人工复核**：复核对象 = R3 候选 `notes` 全文；结论 = **未复活**（科技馆在"已否决"列表语义内被明确排除）。
> - **R1 的 `CHK-FC-STATUS` FAIL 是"缺字段从严"所致**：模型未输出真值三键（`车辆预订/校方报备/行程已确认`），检查器按 strict 判 FAIL。这**不是**"未完成写完成"的真实违反（模型并未声明已完成），是**我的提示词未要求该 schema** 造成的口径问题。
> - **R2 的 `CHK-FC-STATUS` FAIL 属提示词偏置**：p5 v2 的示例值写成 `"行程已确认": true`，模型照抄。**不可归因于压缩机制**。
> - **R3（p5 v3，去掉偏置）`CHK-FC-STATUS` PASS**：模型如实填 `未开始/未开始/false`。

**E1 结论（口径分离）**：

| 口径 | 结果 |
|---|---|
| **关键约束保留（E1 核心）** | **3/3 轮全部保留**：HC-01（15:45 ≤ 16:00）、HC-02（1600 ≤ 6000）、HC-03（64）、SP-02（操场）、REJ 结构化不复活 |
| 未完成写完成 | 受提示词 schema/示例偏置影响，**3 轮不可比**；去偏置后（R3）**PASS** |
| 任务整体 | 3/3 FAIL —— 但失败项**均非**机制结论（见上三条降级标注） |

### 1.7 可归因性

| 项 | 内容 |
|---|---|
| 能把差异归因于该机制吗 | **部分能** |
| 理由 | 压缩事件（started/completed + checkpoint + segment）由磁盘权威记录，**触发与两趟性可归因**；"压缩后约束仍保留"由**结构化检查器**判定，可归因到"该会话在压缩后仍产出满足约束的方案"。但**不能**归因到"摘要文本本身保留了约束"，因为 R1 的 p5 明确**重新读取了磁盘上的 p1~p4 文件**（`num_turns=6`，thought 中自述"核对 p1、p2、p3 的完整内容"）——存在**磁盘回退通道**。R2/R3 已加"不要读取磁盘文件"约束且 `num_turns=1`（无回退），此两轮为**纯上下文保留**证据。 |
| 归因限制 | 模型不可控（服务端 side-model 生成摘要）；窗口被显式覆盖（非默认 256k）；候选 JSON 结构化由人完成；p5 提示词在 3 轮间有修订（§1.3） |

### 1.8 状态

`OBSERVED`（触发线 + 两趟压缩 + 压缩产物 + E1 约束保留）；`NOT_RUN`：用**默认 256k 窗口**复现 85% 线（预算内不可达，已给原因）；`NOT_RUN`：`auto_compact_threshold_percent=70` 提前触发变体（见 §1.9 未做原因）。

### 1.9 未做项与原因

| 项 | 状态 | 原因 |
|---|---|---|
| 默认窗口（256k）下复现 85% 线 | `NOT_RUN` | 85% = 217,600 tokens，超出"单轮 ≤10 分钟 / ≤20 工具动作"预算；改用显式覆盖窗口 30k（已登记） |
| `[session] auto_compact_threshold_percent = 70` 提前触发变体 | **`OBSERVED`（T19 补做，见 §1.10）** | 主 Agent 批准补做；两发（大步长 / 小步长）已给出阈值生效性与触发点位置的结论 |
| `/context`、`/session-info` 读数 | `NOT_RUN` | slash 命令在 headless `-p` 下**不执行**（实测：`/context` 被当作 `hostTurn:true` 的用户消息，5 ms 返回空文本，无输出）；TUI 不可用（§7）。**替代证据**：`signals.json` 的 `contextWindowUsage/contextTokensUsed/contextWindowTokens` + `updates.jsonl` 的 `auto_compact_started.percentage` |

---

## 1.10 补测 · 阈值生效性与"触发点位置"（`MECH-grok-trigger-04/05`，T19 补做）

> **补测动机**（主 Agent 裁决 §1 第 1 条）：条件 1 实测触发读数为 **92%~97%**，与文档默认 **85** 不一致。需回答：85 是"触发点"还是"下限判定线"？

### 命令（逐字）

```zsh
# T70（大步长）：threshold=70 + window=30000（线 21,000）；沿用条件 1 的 p1~p4（p4 = 70,019 字符）
# T70b（小步长）：threshold=70 + window=30000；p1（小） + 单个 65,000 字符填充（步长 ≈20.4k tokens）
cd /tmp/t19-grok
export GROK_HOME=/tmp/t19-grok HOME=/tmp/t19-grok-home GROK_DISABLE_AUTOUPDATER=1 GROK_SUBAGENTS=0
G=/Users/junjielong/.local/bin/grok
# config.toml: [session] auto_compact_threshold_percent = 70 ; [model."grok-4.7"] context_window = 30000
$G --prompt-file /tmp/t19-grok/p1.txt --output-format json > logs/grok-t70b-p1-<TS>.json 2>&1
$G --prompt-file /tmp/t19-grok/c3_fill65k.txt -r <UUID> --output-format json > logs/grok-t70b-fill-<TS>.json 2>&1
```

### 结果（两次，逐字事件）

| 变体 | 阈值 | 线（tokens） | 该轮步长（tokens） | `auto_compact_started` | 是否触发 |
|---|---|---|---|---|---|
| **T70**（大步长） | 70 | 21,000 | ≈+21,600（p3→p4 一步） | `{"tokens_used":29081,"context_window":30000,"percentage":97,"reason":"Context window 97% full"}` | 触发（97%） |
| **T70b**（小步长） | 70 | 21,000 | ≈+20,045（p1 1,425 → 21,470） | `{"tokens_used":21470,"context_window":30000,"percentage":72,"reason":"Context window 72% full"}` | **触发（72%）** |
| 对照：条件 1（R1~R3） | 85 | 25,500 | ≈+21,600 | `percentage: 97` | 触发（97%） |

`auto_compact_completed`：T70 `29081 → 7488`（78,995 ms）；T70b `21470 → 1425`（41,076 ms）。

### 结论（回答主 Agent 的疑问）

> **`auto_compact_threshold_percent` 是"下限判定线"，不是"触发点读数"。**
> 判定在**轮界**执行——即**该轮消息（含工具结果）已加入上下文之后**才检查百分比；因此**观测到的触发百分比 = 阈值 + 该轮内增量**：
> - **小步长**（T70b）：增量小 → 触发读数紧贴阈值上方（阈值 70 → 读数 **72%**），**证明阈值确实生效**（若仍为 85，21,470 = 71.6% 不会触发）。
> - **大步长**（条件 1 与 T70）：单步 +21.6k tokens 一步跨过 70% 与 85% 两条线 → **两个阈值得到相同的触发读数 97%**（因此"条件 1 读到 97%"**不能**被解释为"85 未生效"）。

**对总表/T14 的口径建议**：Grok 的触发线应写成 **「`context_window × auto_compact_threshold_percent`（默认 85），在轮界判定，实测触发读数 ≥ 阈值」**；与"阈值即触发点"的写法**不等价**，横向比较时须注明口径。

### 状态

`OBSERVED`（2 次补测，事件逐字）。剩余未做：用**多轮小步长**逼近以给出"触发读数 − 阈值"的分布（本轮仅 2 个点，**不声称统计意义**）。

---


## 2. 条件 2 · 工具输出治理（`MECH-grok-toolout-01/02`）

### 2.1 变量与固定量

| 项 | 值 |
|---|---|
| 唯一自变量 | 工具（`run_terminal_command`）输出体积：161,144 字节（v2）／22,003 字节（v1，300 行）／30,001 字符（ASCII） |
| 固定量 | 工具版本 1.0.52 / 模型 grok-4.7 / 数据 v2·v1 样本 / 命令 `cat <file>` / 会话隔离同 §0 |
| 窗口 | 会话 A（`MECH-grok-toolout-01`）：`context_window=30000`（默认阈值 85）；会话 B（`MECH-grok-toolout-02`）：`context_window=200000`（**刻意抬高以避免压缩干扰剪枝观察**） |

### 2.2 命令模板（逐字）

```zsh
cd /tmp/t19-grok
export GROK_HOME=/tmp/t19-grok HOME=/tmp/t19-grok-home GROK_DISABLE_AUTOUPDATER=1 GROK_SUBAGENTS=0
G=/Users/junjielong/.local/bin/grok
# 会话 A
$G --prompt-file /tmp/t19-grok/c2_a_v2.txt --output-format json > logs/grok-c2-v2-<TS>.json 2>&1      # cat v2（161KB）
$G --prompt-file /tmp/t19-grok/c2_b_v1.txt -r <UUID> --output-format json > logs/grok-c2-v1-<TS>.json 2>&1  # cat v1（22KB）
for n in 3 4 5 6; do $G --prompt-file /tmp/t19-grok/c2_tick.txt -r <UUID> --output-format json > logs/grok-c2-tick$n-<TS>.json 2>&1; done
# 会话 B（剪枝观察，12 轮）
$G --prompt-file /tmp/t19-grok/c2p_a_ascii.txt --output-format json > logs/grok-c2p-ascii-<TS>.json 2>&1   # python3 print('A'*30000)
$G --prompt-file /tmp/t19-grok/c2_a_v2.txt   -r <UUID> --output-format json > logs/grok-c2p-v2-<TS>.json 2>&1
for n in $(seq 3 12); do $G --prompt-file /tmp/t19-grok/c2_tick.txt -r <UUID> --output-format json > logs/grok-c2p-tick$n-<TS>.json 2>&1; cp <SESSDIR>/chat_history.jsonl logs/grok-c2p-chat-after-t$n-<TS>.jsonl; done
```

### 2.3 预期事件（先写，后对照）

| # | 预期出现的事件 | 依据（T12 证据卡） |
|---|---|---|
| 1 | bash 输出超限被截断 | `grok-toolout-01`（`output_byte_limit` 默认 **65536 字节**） |
| 2 | 截断形态为"保头/保头尾/留标记"之一（文档未描述） | `grok-toolout-01`「不能证明」栏 |
| 3 | 是否落盘（文档未描述 bash 输出落盘路径） | `grok-toolout-01`「不能证明」栏 |
| 4 | 旧工具结果（>4000 字符）软裁为头 1500/尾 1500；>10 轮硬清为占位符 | `grok-toolout-03`（`[compaction.pruning]` 4000/1500/1500/3/10） |

### 2.4 观测结果（真实结果）

#### (a) 截断阈值与形态 —— **文档常量与实测不符（重要）**

| 输入 | 原始字节 | 模型可见结果 | 截断标记 |
|---|---|---|---|
| `cat` v2 样本 | 161,144 | **20,030 字符 / 25,636 字节** | 见下 |
| `python3 print('A'*30000)` | 30,001 | **20,260 字符** | 见下 |
| `cat` v1 样本（300 行） | 22,003 | **17,190 字符（≈全文，未截断）** | 无 |

**模型可见结果的首行（`chat_history.jsonl`，逐字）**：

```text
exit: 0 [truncated: showing first/last 25.0 KB of 157.4 KB - full output at: /tmp/t19-grok/sessions/%2Fprivate%2Ftmp%2Ft19-grok/<UUID>/terminal/call-42f5fb32-6d14-4848-8ae4-8fc5f1855258-1.log]
```

```text
exit: 0 [truncated: showing first/last 19.6 KB of 29.3 KB - full output at: /tmp/t19-grok/sessions/%2Fprivate%2Ftmp%2Ft19-grok/<UUID>/terminal/call-be29cdfb-1dc4-442b-aeea-e8b50a49ace1-0.log]
```

**形态 = 头 + 标记 + 尾**（逐字标记，两处不同写法并存）：

```text
# 会话 A（updates.jsonl 的展示态）：
... 156 | 2026-10-23 | S1-059 | 16:10 | 返程 | 城郊植物园 | 50 | -

... (output truncated) ...

23 | 08:32 | 返程 | 支线南段 | 35 | -
```

**精确切分（实测）**：

| 项 | v2（CJK 为主） | ASCII 30k |
|---|---|---|
| 头部保留 | **10,000 字符**（= 12,855 字节） | 10,228 字符（含 228 字符 header） |
| 尾部保留 | **10,000 字符**（= 12,751 字节） | 10,006 字符 |
| 合计 | 20,030 字符 / 25,636 字节（标记自称 "25.0 KB"） | 20,260 字符（标记自称 "19.6 KB"） |

> **结论（vs 文档）**：`grok-toolout-01` 登记的 `toolset.bash.output_byte_limit = 65536 字节` **在本轮未成为约束**：① 30,001 字节（< 65536）也被截断；② 161,144 字节的**全文**被完整落盘（无 65536 上限）。实测的**模型可见上限 ≈ 头 10,000 字符 + 尾 10,000 字符**（标记按字节换算显示 "25.0 KB"）。**这是对 T12 文档常量的否证**（至少对 1.0.52 的这条 headless 路径）。

#### (b) 是否落盘 —— **是，全文落盘**

| 工具调用 | 落盘文件 | 字节 |
|---|---|---|
| `cat` v2 | `<SESSDIR>/terminal/call-76f0f1be-…-0.log` | **161,144**（与源文件逐字节一致） |
| `cat` v1 | `<SESSDIR>/terminal/call-58bfe0ab-…-1.log` | **22,003**（完整） |
| `echo tick` | `terminal/call-…-0.log` | 11 |

- 落盘路径 = `<GROK_HOME>/sessions/<encoded-cwd>/<session-id>/terminal/call-<toolCallId>.log`。
- **标记里直接把该路径写给模型**（"full output at: …"）→ 模型可自行 `read_file` 取回中段。
- 说明：**中段（关键块）并未丢失**，只是从"模型可见层"移到"磁盘层"，且**给了模型可寻址路径**。

#### (c) 剪枝（软裁 / 硬清）—— **硬清实测到；软裁未观测到**

会话 B（`context_window=200000`，**12 轮无压缩**，逐轮快照 `chat_history.jsonl`）：

| 轮次（t1 = ASCII 30k 工具结果产生处） | t1 工具结果在模型可见历史中的长度 | 观察 |
|---|---|---|
| t1 | 20,260 字符 | 原始（已截断态） |
| t2 ~ t11（轮龄 1~10） | **20,260 字符（不变）** | **未见软裁**（若按文档 4000/1500/1500 应缩到 ~3,030 字符） |
| **t12（轮龄 11）** | **31 字符** | **硬清发生** |

**硬清占位符（逐字）**：

```text
[Tool result omitted — too old]
```

- 硬清**实测到**，且落在"轮龄 11"（文档 `hard_clear_age_turns = 10`，含 `keep_last_n_turns=3` 语义 → 实际生效点 11 轮，与文档量级一致）。
- **软裁（`soft_trim_threshold=4000` / head 1500 / tail 1500）在本轮 12 轮窗口内未观测到**：模型可见历史里的旧工具结果始终是 20,260 字符。**可能解释（未验证，不得当结论）**：① 软裁只在**请求组装时**施加、`chat_history.jsonl` 存的是施加前状态；② `[compaction.pruning]` 的软裁分支在 1.0.52 的这条路径未生效。→ **标 `UNOBSERVABLE`（软裁环节）**，不写成"该机制不存在"。

#### (d) 窗口口径不一致（附带发现，重要）

同一会话 B（带工具调用）：`signals.contextWindowTokens = 256000`，但 `auto_compact_started.context_window = 30000`（会话 A）。**对照实验**：

```zsh
# 无工具调用（仅问答）
$G -p "Reply OK" --output-format json            → signals.contextWindowTokens = 30000   （= 配置覆盖值）
# 有工具调用（echo hello）
$G --prompt-file win_test.txt --output-format json → signals.contextWindowTokens = 256000 （= 内置值）
```

→ **触发判定用配置窗口（30,000）；`signals` 的窗口字段在带工具会话中报内置值（256,000），不可用作触发线分母**。会话 A 的触发亦印证：`auto_compact_started{tokens_used:34428, context_window:30000, percentage:100}` —— 若分母真是 256,000，34,428 tokens 只是 13%，不会触发。

> [!warning] **口径注（主 Agent 裁决 §1 第 3 条，横向比较必读）**
> **Grok 的触发线分母一律取配置 `context_window`；`signals.contextWindowTokens` / `contextWindowUsage` 在带工具会话中报内置窗口值（256,000），不得作触发线分母。** 需要窗口/百分比读数时，用 `updates.jsonl` 的 `auto_compact_started.context_window` 与 `.percentage`（该处恒为配置值）。

### 2.5 判据结果

本条件为**机制观察**，无"最终方案"产出 → **不适用检查器**（`NOT_APPLICABLE`）。判据 = 落盘文件字节数 + 模型可见长度 + 占位符/标记逐字比对（上述均为**确定性计数**，非启发式）。

### 2.6 可归因性

| 项 | 内容 |
|---|---|
| 能把差异归因于该机制吗 | **能**（截断/落盘/硬清均为确定性计数） |
| 理由 | 同一命令、同一文件、同一工具，仅改变输出体积；落盘文件字节与源文件逐字节一致 |
| 归因限制 | 截断上限为**观测值**（头/尾各 10,000 字符），**未能定位到配置键**（`toolset.bash.output_byte_limit` 未约束该路径）；软裁环节 `UNOBSERVABLE` |

### 2.7 状态

`OBSERVED`（截断形态与阈值、全文落盘、硬清）；`UNOBSERVABLE`（软裁是否施加于请求组装层）；`NOT_RUN`（`mcp.max_output_bytes` / `max_request_bytes` 路径）。

---

## 3. 条件 3 · 连续三次压缩（`MECH-grok-compactcont-01`）

### 3.1 变量与固定量

| 项 | 值 |
|---|---|
| 唯一自变量 | 连续触发的压缩次数（1→2→3） |
| 固定量 | 1.0.52 / grok-4.7 / `context_window=15000`（阈值默认 85% → 线 12,750）/ 同一填充文本（v2 前 40,000 字符）/ 隔离同 §0 |

### 3.2 命令模板（逐字）

```zsh
cd /tmp/t19-grok
export GROK_HOME=/tmp/t19-grok HOME=/tmp/t19-grok-home GROK_DISABLE_AUTOUPDATER=1 GROK_SUBAGENTS=0
G=/Users/junjielong/.local/bin/grok
$G --prompt-file /tmp/t19-grok/c3_p1.txt --output-format json > logs/grok-c3-p1-<TS>.json 2>&1      # 任务+HC+REJ+准备项状态
for n in 1 2 3; do $G --prompt-file /tmp/t19-grok/c3_fill40k.txt -r <UUID> --output-format json > logs/grok-c3-fill$n-<TS>.json 2>&1; done
$G --prompt-file /tmp/t19-grok/c3_probe.txt -r <UUID> --output-format json > logs/grok-c3-probe-<TS>.json 2>&1
```

### 3.3 预期事件（先写，后对照）

| # | 预期出现的事件 | 依据 |
|---|---|---|
| 1 | 每次填充触发 1 次压缩，共 3 次 | `grok-compact-01/02` |
| 2 | `compaction_checkpoints/` 与 `compaction/` 逐次累积 | `grok-summary-01` |
| 3 | 连续压缩后**关键事实仍在**（E3 判据：不复活被否项、不把未完成写完成） | E3 场景 + 检查器 |

### 3.4 观测结果

| 阶段 | `contextTokensUsed`（占比） | `compactionCount` | `totalTokensBeforeCompaction` |
|---|---|---|---|
| p1（任务） | 1,356 (9%) | 0 | 0 |
| fill1 | 13,753 (91%) | **2** | 15,109 |
| fill2 | 13,856 (92%) | **4** | 30,424 |
| fill3 | 13,811 (92%) | **6** | 45,649 |
| probe | 1,659 (11%) | 6 | 45,649 |

**3 次压缩事件（`updates.jsonl`，逐字）**：

```text
auto_compact_started   {"tokens_used":13753,"context_window":15000,"percentage":92,"reason":"Context window 92% full"}
auto_compact_completed {"tokens_before":13753,"tokens_after":1356,"elapsed_ms":71079}
auto_compact_started   {"tokens_used":13856,"context_window":15000,"percentage":92,...}
auto_compact_completed {"tokens_before":13856,"tokens_after":1311,"elapsed_ms":88155}
auto_compact_started   {"tokens_used":13811,"context_window":15000,"percentage":92,...}
auto_compact_completed {"tokens_before":13811,"tokens_after":1407,"elapsed_ms":53807}
```

- 每次填充 → 1 次压缩事件（= 2 趟，`compactionCount` +2）；3 次连续压缩**无重复压缩、无无界循环**（`compactionCount` 单调 +2，未失控）。
- **压缩比极高**：13,7xx → 1,3xx（≈90% 缩减），因填充内容高度同质（同一文件的不同片段）。
- **落盘**：`compaction/segment_000.md`(82,129B) / `segment_001.md`(142,649B) / `segment_002.md`(137,545B) + `INDEX.md`（**每次压缩新增一个 segment**）；另见 `compaction_requests/` 目录（T12 文档未列，属"文档清单非穷尽"）。

### 3.5 判据结果（检查器原始输出）

```text
=== T03-DATA-TRIP-v1 | 候选：grok-c3-probe.json | overall=FAIL ===
  [FAIL] CHK-HC-01      returnTime='' 无法解析为 HH:MM
  [PASS] CHK-HC-02      求和 1600  vs 上限 6000
  [FAIL] CHK-HC-03      headcount=0 应等于 64
  [PASS] CHK-SP-02      assemblyPointId='' 不得属于被否集合 [...]
  [PASS] CHK-REJ-STRUCT selectedOptionIds=[] 命中被否项 []
  [PASS] CHK-REJ-TEXT   命中且无否定语境：[]
  [PASS] CHK-FC-STATUS  与真值不一致项：[]
  命中问题类别：['硬约束违反']
exit=1
```

| 指标 | 值 |
|---|---|
| 任务是否通过 | **FAIL** |
| 关键约束违背数 | **2**（HC-01 无法给出返抵时间；HC-03 人数 0 ≠ 64） |
| 否决复活数 | **0**（结构化与文本层均 0） |
| 未完成写完成数 | 0 |
| 体积缩减率（仅参考） | ≈90%（13,7xx → 1,3xx） |

**失败形态 = 关键约束丢失（不是复活）**，模型自述（`notes` 逐字摘录）：

```text
仍有效：日期2026-10-23（周五）、双向；返校终点只核示例一中（L7主线站序1）；返抵学校时间=发车+车程（L7主线55分钟，L7A/L7B支线70分钟）；S1–S6不进校区，仅换乘。
已否决：把地铁北站或城郊植物园当成到校终点；…将车辆预订、校方报备或行程标成已完成/已确认。
当前上下文在S4-086（20:40，去程，地铁北站）截断，没有L7返程段、文末结论和周末/停运审计，因此返抵时间、集合点（LOC-PLAYGROUND与REJ-02均无依据）和选项都不能确定。
```

> **解读（诚实标注）**：模型**如实承认"不能确定"**，未幻觉、未复活被否项；原始任务的 HC-01/02/03 与 REJ-01/02/03 **已被 3 次压缩挤出上下文**，只剩填充资料（公交表）的"约束"。这是 E3 场景下**"连续压缩导致早期关键约束丢失"**的正面证据。
> **归因限制**：本条件把 3 次压缩压在同一批**同质大填充**上，属**压力形态**（真实会话的压缩通常伴随任务推进）；因此"丢失"结论**只对"早期小消息 + 后续大量同质填充 + 连续 3 次压缩"这一形态成立**，不外推为"Grok 压缩必然丢约束"（对比 §1：**1 次**压缩时约束 3/3 保留）。

### 3.6 可归因性 / 状态

| 项 | 内容 |
|---|---|
| 能归因吗 | **能**（3 次压缩事件、segment 累积、判据 FAIL 均为确定性记录） |
| 归因限制 | 服务端摘要不可见；填充形态人为构造；`signals` 窗口字段不可靠（§2.4d），此处以 `auto_compact_started.context_window` 为准 |
| 状态 | `OBSERVED` |

---

## 4. 条件 4 · 恢复语义 + **Q-01 实测裁决**（`MECH-grok-rewind-01/02`）

### 4.1 裁决对象（T12 遗留）

| 出处 | 表述 |
|---|---|
| `17-sessions.md` L158 | 「`/rewind` does not restore files on disk. Only conversation history is truncated.」 |
| `~/.grok/README.md` L498 | `/rewind <prompt>` = "Rewind to a previous prompt (**restores files**)" |
| `rewind_points.jsonl` 语义 | README 称 "**file snapshots** for /rewind undo"；17-sessions 称 "rewind points" |

### 4.2 方法（因 TUI 不可用而设计的两条 headless 证据）

| 证据 | 做法 |
|---|---|
| **证据 1：文件快照是否被捕获** | 在 git 工作目录 `/tmp/t19-grok/work-q01` 建会话 → 让模型改 `file.txt`（**两种路径各一次**：bash 改写 / grok 自带 `write` 文件工具）→ 检查 `rewind_points.jsonl` 的 `file_snapshots` / `after_snapshots` |
| **证据 2：`--restore-code` 是否还原** | 同会话 `-r <UUID> --restore-code` 续接，检查磁盘文件是否被还原 |

命令（逐字）：

```zsh
cd /tmp/t19-grok/work-q01     # git init；file.txt 初始 = "STATE=V1"
export GROK_HOME=/tmp/t19-grok HOME=/tmp/t19-grok-home GROK_DISABLE_AUTOUPDATER=1 GROK_SUBAGENTS=0
G=/Users/junjielong/.local/bin/grok
$G --prompt-file /tmp/t19-grok/q01_edit2.txt      --output-format json > logs/grok-q01-edit-<TS>.json 2>&1     # bash 路径
$G --prompt-file /tmp/t19-grok/q01_edit_tool.txt  --output-format json > logs/grok-q01b-edit-<TS>.json 2>&1    # 文件工具路径
$G --prompt-file /tmp/t19-grok/q01_rc.txt -r <UUID> --restore-code --output-format json > logs/grok-q01b-restorecode-<TS>.json 2>&1
```

### 4.3 观测结果（逐条 before/after 证据）

**证据 1a（bash 路径）** — 磁盘确实被改，快照仍为空：

```text
--- BEFORE ---    STATE=V1
--- AFTER EDIT (disk) ---   STATE=V2 / EDITED=yes        ← 磁盘已被修改（确定性）
--- rewind_points.jsonl ---
{"prompt_index":0,"created_at":"2026-10-15T07:58:25.417916Z","file_snapshots":{},"after_snapshots":{}}
{"prompt_index":1,"created_at":"2026-10-15T07:59:02.062628Z","file_snapshots":{},"after_snapshots":{}}
```

**证据 1b（grok 自带文件工具路径）** — 工具调用被记录，快照仍为空：

```text
tool_call: write  {"file_path":"/tmp/t19-grok/work-q01/file.txt","content":"STATE=V2\nEDITED=yes\n"}
--- AFTER (disk) ---   STATE=V2 / EDITED=yes
--- rewind_points.jsonl ---
{"prompt_index":0,"created_at":"2026-10-15T07:59:55.342655Z","file_snapshots":{},"after_snapshots":{}}
```

**证据 2（`--restore-code`）** — 未还原：

```text
--- disk after --restore-code ---   STATE=V2 / EDITED=yes     ← 与 resume 前一致，未被还原
response text: "I'll read `file.txt` and reply with only its contents.STATE=V2\nEDITED=yes"
```

### 4.4 裁决（Q-01）

> **裁决：`/rewind` 不还原磁盘文件；`rewind_points.jsonl` 不是可用的"文件快照"。**
> **支持 `17-sessions.md`（"does not restore files on disk"）；README 的 "restores files" / "file snapshots" 表述在本轮实测中未获任何证据支持。**
> **证据等级：直接执行观测**（`/rewind` 本体已在 tmux TUI 中真实执行，见 §4.7）——由"间接证据"升格为"直接证据"。

**证据强度与限制（必须一并引用）**：

| 项 | 内容 |
|---|---|
| 支持证据（headless，§4.3） | ① 2 个会话、3 个 rewind point，`file_snapshots` 与 `after_snapshots` **全部为 `{}`**，其中包含一次**用 grok 自带 `write` 工具**的编辑（排除"只有 bash 编辑才不记录"的解释）；② `--restore-code` 明确续接后磁盘文件**未变化**；③ `signals.hasReverted=false`（无回退发生） |
| 支持证据（TUI 直接执行，§4.7） | ④ `/rewind` → 选轮次 → 确认 `y` 后：**对话被截断**（助手回复消失、提示词回到输入框）、`updates.jsonl` 写入 `rewind_marker{target_prompt_index:0}`；⑤ **磁盘文件仍是 `STATE=V2 / EDITED=yes`，`git status` 仍为 ` M file.txt`**；⑥ 该会话 `rewind_points.jsonl` **0 字节（完全为空）**；⑦ `signals.hasReverted=false`、`totalFilesTouched=0` |
| 反证/未排除 | 无（`/rewind` 已真实执行且未还原文件）。**唯一限制**：TUI 复跑使用的是**全量 grok home 副本**（`GROK_HOME=/tmp/t19-grok-full`，含用户 `settings_cache.json`/`skills`/`trusted_folders.toml`），非 §0 的干净隔离环境 —— 但该差异不影响"文件是否被还原"这一确定性判据 |
| 结论强度 | **裁决成立（直接观测）** |

### 4.5 恢复语义（顺带观测）

| 入口 | 实测 |
|---|---|
| `-r <UUID>`（resume） | 生效：续接同一会话，`cwd`/`sessionId` 保持；**恢复 = 重放/重建**（与 `grok-recover-01` 一致） |
| `--continue/-c` | 未测（需"最近会话"语义，隔离环境无歧义场景）→ `NOT_RUN` |
| `--restore-code` | 生效（接受参数、正常续接），但**未观察到任何文件还原效果** |
| `grok export <SESSION_ID>` | 未测（会话正文导出，非本条件判据）→ `NOT_RUN` |

### 4.6 状态

`OBSERVED`（Q-01 **直接裁决** + resume 语义 + `--restore-code` 无效还原）；`NOT_RUN`（`--continue`、`grok export`）。

### 4.7 补测 · `/rewind` 直接执行（`MECH-grok-rewind-03`，T19 补做 · tmux TUI）

> **补测动机**（主 Agent 裁决 §1 第 1 条）：把 Q-01 从"间接证据"升格为"直接执行观测"。

**TUI 启动的根因与修法（重要，供其它批次复用）**

| 项 | 内容 |
|---|---|
| 早期失败现象 | `tmux` 内运行 grok TUI **完全无输出**（`capture-pane` 无内容、`capture-pane -e` 无转义序列、`GROK_HOME` 下无 `sessions/` 落盘） |
| **根因** | pane 里的 shell 被**用户 profile 的 `safe-delete` 钩子**卡住：pane 首屏只有 `[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED] {...}` 提示并等待确认 → 后续 `send-keys` 的命令**根本没有被执行**（因此连 stderr 重定向文件都没创建） |
| **修法** | 用**免 rc 的 shell** 启动 tmux：`tmux new-session -d -s t19gt -x 200 -y 50 "/bin/zsh -f"`，并在命令里给绝对 `PATH`。此后 TUI 正常渲染（欢迎框 + `❯` 输入框 + 状态行 `Grok 4.7 (high) · always-approve`） |
| 附带发现 | grok TUI 把界面写到 **stderr**（`< /dev/null` 直跑可见 `^[[?1049h` 等转义序列）；管道喂 stdin 时**不渲染**（可能因非 TTY 判定） |

**命令（逐字）**

```zsh
tmux new-session -d -s t19gt -x 200 -y 50 "/bin/zsh -f"
tmux send-keys -t t19gt "cd /tmp/t19-grok/work-q01 && PATH=/Users/junjielong/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin GROK_HOME=/tmp/t19-grok-full GROK_DISABLE_AUTOUPDATER=1 /Users/junjielong/.local/bin/grok ; echo GROK_EXIT=\$?" C-m
# ① 磁盘 before：file.txt = "STATE=V1"
# ② 发编辑指令（paste-buffer 避免中文转义）→ 模型用 bash 改写文件
tmux set-buffer -b q01e "请用 bash 把 /tmp/t19-grok/work-q01/file.txt 改写为两行：第一行 STATE=V2，第二行 EDITED=yes。完成后只回复 done"
tmux paste-buffer -b q01e -t t19gt; tmux send-keys -t t19gt C-m
# ③ 执行真实 slash 命令
tmux send-keys -t t19gt "/rewind"; tmux send-keys -t t19gt C-m     # → 弹出 "Rewind to which turn?" 选择器
tmux send-keys -t t19gt C-m                                       # → 选中该轮
tmux send-keys -t t19gt "y"                                       # → "Rewind conversation to “…”?" 选 y
```

**过程逐字（TUI 面板）**

```text
# ② 编辑完成
  ❯ 请用 bash 把 /tmp/t19-grok/work-q01/file.txt 改写为两行：第一行 STATE=V2，第二行 EDITED=yes。完成后只回复 done
  我用 bash 把文件改成这两行。
  ◆ Ran rewrite file.txt to two specified lines
  done
  Worked for 5.0s
  master /p/t/t19-grok/work-q01     20K / 256K │ [Dashboard]
  DISK = STATE=V2 / EDITED=yes          ← before /rewind

# ③ /rewind 选择器
  ┃  Rewind to which turn?
  ┃  · 请用 bash 把 /tmp/t19-grok/work-q01/file.txt 改写为两行：第一行 STATE...

# ③ 确认框（注意措辞："Rewind **conversation**"）
  ┃  Rewind conversation to “请用 bash 把 /tmp/t19-grok/work-q01/file.txt 改写为两行：第一行 STATE...”?
  ┃  y   (●) Yes
  ┃  a   (○) Yes, and don't ask again
  ┃  n   (○) No

# ③ 选 y 之后：助手回复消失，提示词回到输入框（对话被截断）
  │ ❯ 请用 bash 把 /tmp/t19-grok/work-q01/file.txt 改写为两行：第一行 STATE=V2，第二行 EDITED=yes。完成后只回复 done │
```

**判据（before / after，确定性）**

| 观测 | before `/rewind` | after `/rewind` | 结论 |
|---|---|---|---|
| 磁盘 `file.txt` | `STATE=V2` / `EDITED=yes` | **`STATE=V2` / `EDITED=yes`（未变）** | **未还原** |
| `git status --porcelain` | ` M file.txt` | **` M file.txt`** | 未还原 |
| 对话历史 | 含助手回复 `done` | **助手回复消失**，提示词回到输入框 | **已截断** |
| `updates.jsonl` | — | `rewind_marker {"target_prompt_index":0,"created_at":"2026-10-15T08:15:12.221393+00:00"}` | 回退事件落盘 |
| `<session>/rewind_points.jsonl` | — | **0 字节（空）** | **无任何文件快照** |
| `signals` | — | `hasReverted:false`、`totalFilesTouched:0`、`turnCount:1` | 无文件回退记账 |

**结论**：`/rewind` **只截断对话历史，不还原磁盘文件** —— 与 `17-sessions.md` L158 一致；确认框自身措辞亦为 "Rewind **conversation**"。**Q-01 由间接证据升格为直接证据。**

**状态**：`OBSERVED`（直接执行）。**副作用**：`/tmp/t19-grok-full`（全量 home 副本）与 `/tmp/t19-grok/work-q01/file.txt`（=STATE=V2）为实验残留，均在 `/tmp` 隔离区，**未触碰** `~/.grok`。

---


## 5. 条件 5 · 记忆（`MECH-grok-memory-01`，**选做·低优先**）

| 项 | 值 |
|---|---|
| 变量 | `GROK_MEMORY=1`（显式开启；默认关，`grok-memory-01`） |
| 命令 | `GROK_MEMORY=1 $G -p "记住一个事实：本次实验编号是 T19-GROK-MEM-<i>。只回复 ok。" -s/-r <UUID> --output-format json`（3 轮） |
| 预期事件 | 每轮后台复盘写入 `memory-v2/<scope>/observations/_inbox/`；`/flush` 后计数增加；`/dream`（≥20 条或最旧 ≥24h）折叠进 `topics/`；索引注入 ≤8 KiB（`grok-shell-memory_injection`） |
| **实测** | 会话正常完成（12 条消息）；日志出现 `memory_init` **70 次**（组件初始化）；但 **`memory-v2/` 目录未被创建**，`observations/_inbox/` 计数 = **0**；无 `grok-shell-memory_injection` 记录 |
| 未能做的步骤 | `/flush`、`/dream` 均为 **TUI slash 命令**，headless 下不执行（§7）；`grok memory` 子命令**只有 `clear`**（无 flush/dream CLI 等价物） |
| 状态 | **`NOT_RUN`（捕获/Dream/注入）** + **`UNOBSERVABLE`（是否在别的路径捕获）** |
| 原因（不得写成"没有该机制"） | ① headless 短会话 + 实验特性默认关；② 观察窗口内**无 `/flush`/`/dream` 入口**；③ 本机 `~/.grok/memory-v2/`（非隔离）虽有脚手架但内容为空（T12 已登记）。**T12 `grok-memory-03/04` 的文档级结论未被本轮证实或否证。** |

---

## 6. 条件 6 · 缓存（`MECH-grok-cache-01`）

### 6.1 变量与固定量

| 项 | 值 |
|---|---|
| 变量 | 同一会话内**前缀是否已被缓存**（跨会话 vs 会话内）；以及**硬清是否使前缀失效** |
| 固定量 | 1.0.52 / grok-4.7 / 同一提示词 / 隔离同 §0 |

### 6.2 观测结果（来自服务端返回 usage，非本地估算）

**(a) 跨会话同提示词 → 无命中**：

```text
run1: input=15526 cache_read=0 cache_creation=0 out=43 cost=$0.0106454
run2: input=15526 cache_read=0 cache_creation=0 out=35 cost=$0.0106291
```

→ 两次**独立会话**、同一提示词，`cache_read` 均为 **0**。缓存**不跨会话复用**（至少在本观测窗口内）。

**(b) 会话内逐轮 → 前缀命中并累积（会话 B，12 轮）**：

| 轮 | input（未缓存） | cache_read | output | costUsdTicks |
|---|---|---|---|---|
| t1 | 32,631 | **0** | 170 | 225,358,800 |
| t2 | 47,209 | **32,512** | 255 | 160,412,000 |
| t3 | 60,147 | **47,104** | 87 | 170,544,000 |
| t4 | 60,424 | **60,032** | 65 | 106,046,000 |
| t5 | 60,674 | 60,288 | 78 | 106,705,600 |
| t6 | 60,936 | 60,544 | 74 | 107,100,000 |
| t7 | 61,198 | 60,800 | 68 | 107,453,600 |
| t8 | 61,449 | 61,056 | 75 | 107,997,600 |
| t9 | 61,713 | 61,312 | 76 | 108,507,600 |
| t10 | 61,986 | 61,568 | 77 | 109,078,800 |
| t11 | 62,248 | 61,824 | 76 | 109,534,400 |
| **t12** | 59,763 | **17,792** | 74 | **317,158,800** |

**两条结论**：

1. **前缀缓存随轮次累积并饱和**：t1 冷启动 `cache_read=0` → t2 起命中 32.5k → t4 起饱和在 ≈60k（会话稳定前缀）。**缓存桶为 CLI 侧可读的服务端回传读数**（`grok-cache-01` 得到实证）。
2. **硬清会击穿缓存并显著抬高成本**：t12 发生 `[Tool result omitted — too old]`（§2.4c）后，`cache_read` 从 61,824 **骤降到 17,792**，该轮 `costUsdTicks` 从 ≈109.5M **跳到 317.2M（≈2.9×）**。→ **剪枝的"硬清"不是免费的：它改写前缀 → 缓存失效 → 单轮成本约 3 倍**。这是 T14/T16 成本口径可直接引用的实测点。

### 6.3 服务端不可观测项

`UNOBSERVABLE`：缓存**命中率、TTL、缓存键、前缀断点**全部在服务端（`grok-cache-02` 一致）；CLI 只能读回三个不相交桶（`input_tokens` / `cache_read_input_tokens` / `cache_creation_input_tokens`）。**不得**把"有 cache_read 读数"当作"缓存一定命中"。

### 6.4 状态

`OBSERVED`（CLI 侧三桶读数、会话内前缀累积、硬清→缓存击穿→成本跳升）；`UNOBSERVABLE`（服务端缓存行为）。

---

## 7. 异常与停止（两类共用）

| 项 | 内容 |
|---|---|
| 是否触达停止条件 | **否**（无重复压缩、无无界循环；单轮均 ≤10 分钟、工具动作 ≤20） |
| **TUI 初始化（先阻塞→已解决）** | 首次尝试：`tmux`（`-x 200 -y 50`）内直接运行、`--minimal`、`--fullscreen`、`--no-alt-screen`、`COLORTERM=truecolor TERM=xterm-256color`、`script -q /dev/null grok`（pty 包装）、两次隔离 GROK_HOME —— 全部**无输出**（pane 空、无转义序列、无 `sessions/` 落盘、`grok doctor` 报 `terminal Unknown / multiplexer None detected`）。**根因已定位（补测期间）**：pane 里的 shell 被**用户 profile 的 `safe-delete` 钩子**卡在确认提示上，`send-keys` 的命令从未被执行。**修法**：`tmux new-session … "/bin/zsh -f"`（免 rc）→ TUI 正常渲染（见 §4.7）。**后果（仍存在）**：`/context`、`/session-info`、`/compact`、`/flush`、`/dream` 等 slash 路径**未逐条实测**（仅 `/rewind` 已直接实测） |
| **slash 命令在 headless 下不执行（实测）** | `$G --prompt-file <"/context"> -r <UUID>` → `updates.jsonl` 记为 `user_message_chunk{hostTurn:true}`、`turn_completed{elapsed_ms:5}`、`text:""`；无任何 `/context` 输出。`/compact` 同轮被 120 s 前台超时杀死（exit 137），亦未产生压缩事件 |
| **网络超时重试（CM-11 观测）** | R3 p5 期间 `updates.jsonl` 出现 `retry_state{"type":"retrying","attempt":1,"max_retries":15,"reason":"request error: … client error (Connect): operation timed out","error_type":"http"}`；R1 p4 压缩 `elapsed_ms=475,938`（含该重试等待）。**记录**：`max_retries` 实测为 **15**（T12 `grok-fail-01` 记为 `models.max_retries` 默认 8 —— **口径不一致，待核**） |
| **压缩单次耗时** | 53,807 ~ 475,938 ms（中位 ≈101,224 ms）；慢的那次含上述网络重试 |
| 已产生的副作用 | 均在 `/tmp/t19-grok*` 隔离目录与 `experiments/t19/` 内；**未改** `~/.grok` 既有文件、未改 T03 冻结包、未改 grok 冻结件 |
| 后续动作 | 保留全部原始日志；TUI 相关项标 `NOT_RUN` 并给出替代证据；建议 T19R 在有 TUI 的终端补做 `/rewind` 直接复跑 |

---

## 8. 不可观测项登记

| 想看但看不到的东西 | 为什么看不到 | 影响哪条结论 |
|---|---|---|
| 压缩摘要的**具体文本**（服务端 side-model 产物） | `auto_compact_completed.summary_preview = null`；摘要被写入 `chat_history.jsonl` 的 `compaction_meta` 用户消息（可读但**非** raw 服务端输出） | §1 E1 保真度、§3 失真度 |
| 服务端 prompt cache 的命中率 / TTL / 键 / 前缀断点 | 服务端行为，CLI 不可控 | §6（只能给 CLI 侧读数） |
| `toolset.bash.output_byte_limit` 是否为实际生效键 | 本轮 30 KB 与 161 KB 均不按 65536 字节表现；未定位到实际生效键 | §2 截断上限（只能给观测值） |
| 软裁（4000/1500/1500）是否在**请求组装层**生效 | `chat_history.jsonl` 未体现；无法抓取 wire 请求字节 | §2.4c（标 `UNOBSERVABLE`） |
| 远端 `requirements/managed` 下发的阈值覆盖值 | 服务端不可观测（T12 U4） | §1 触发线"默认 85"的普适性 |
| `/rewind` 执行瞬间的行为 | ~~TUI 不可用；slash 在 headless 不执行~~ → **补测已直接执行（§4.7）** | 已消解；`/context`、`/compact`、`/flush`、`/dream` 仍待测 |

---

## 9. 版本漂移复测（开跑日）

```text
$ /Users/junjielong/.local/bin/grok --version
grok 1.0.52 (0920c8169e27)          # exit 0   ← 与 G7G8 §1 grok 行一致，未漂移
$ cat ~/.grok/version.json          # {"version":"1.0.52","checked_at":"2026-10-15T00:37:39Z"}
$ shasum -a 256 ~/.grok/downloads/grok-1.0.50-macos-aarch64
af41b1d65d4116ff649a689ad9d070d4c2abe255737d46ba0b3e8161345696e6   # 与版本表 §2 逐位一致
$ shasum -a 256 ~/.grok/downloads/grok-1.0.52-macos-aarch64
c2caa9895dd763297a75e8fb6077e175d9c5304c53903e52cff8891a1384bbb9   # 与 G7G8 登记一致
```

| 字段 | 值 |
|---|---|
| 执行版本（当日复测） | **1.0.52（`0920c8169e27`）** |
| 冻结件 | **1.0.50**（sha256 未变，仍可复现） |
| GROK_HOME 隔离 | `/tmp/t19-grok`（+ `HOME=/tmp/t19-grok-home`） |
| 漂移结论 | **未发现新增漂移**（开跑日 = 收尾日均 1.0.52）；`GROK_DISABLE_AUTOUPDATER=1` 全程生效 |

---

## 10. 用量与费用汇总

| 条件族 | 模型调用数 | input | cache_read | cache_creation | output | 费用（USD，账号实际返回） |
|---|---|---|---|---|---|---|
| E1 触发线/约束保留（3 轮） | 18 | 429,735 | 721,280 | 0 | 12,520 | **0.4492** |
| 条件 2 会话 A（截断/落盘） | 6 | 103,390 | 157,184 | 0 | 1,186 | **0.0994** |
| 条件 2 会话 B（剪枝 12 轮） | 12 | 105,546 | 584,832 | 0 | 1,175 | **0.1736** |
| 条件 3 连续压缩 | 5 | 72,224 | 115,328 | 0 | 7,312 | **0.0836** |
| 条件 4 Q-01（含 `--restore-code`） | 4 | 48,108 | 78,336 | 0 | 633 | **0.0474** |
| 小计（计入表内） | **45** | **759,003** | **1,656,960** | **0** | **22,826** | **0.8532** |
| 另：入口验证 / 配置校准 / 窗口对照 / 缓存冷热 / 记忆 / **TUI 与补测** | ≈16 | — | — | — | — | ≈0.08 |
| **批次合计（T19R P-3 复核定稿）** | **52 次 CLI 调用**（51 有回执 + 1 空文件；Σ num_turns = **78**） | — | — | — | — | **$0.9757**（Σ total_cost_usd，逐日志核算） |

> 口径：`input_tokens` 为**未缓存**输入，`cache_read_input_tokens` 单列**不重复相加**；`cache_creation_input_tokens` 全程为 0（服务端未回传创建量）。费用取 CLI 返回的 `total_cost_usd`（ticks ÷ 10¹⁰）；`cost_is_partial` 未出现。

> 【T19R P-3 复核（2026-10-15，主 Agent 逐日志核算）】`grok-*.json` 共 **52** 个：51 个含 `total_cost_usd`（**Σ = $0.9757**）、1 个为空文件（`grok-e1-r1-p4-151548`，失败/中止）；Σ `num_turns` = **78**。原表「≈61 次 / ≈0.93 USD」为**批内自计（近似）**——计数口径与逐日志不完全对应（61 介于 52 次调用与 78 轮之间），**费用以逐日志合计 $0.9757 为准**；**TUI 路径运行（/rewind 直测等）不产 -p JSON，其费用未含在 $0.9757 内**（自估 <$0.02）。

---

## 11. 条件状态表（含"为什么"）

| # | 条件 | 状态 | 为什么 |
|---|---|---|---|
| 1 | 触发线 85% + E1 约束保留 | **OBSERVED** | 3/3 轮触发（97%）、两趟压缩、checkpoint/segment 落盘、结构化判据 3/3 保留约束 |
| 1b | 默认 256k 窗口下 85% 线 | `NOT_RUN` | 217,600 tokens 超出单轮预算 |
| 1c | `threshold_percent=70` 变体 | **`OBSERVED`（§1.10，T19 补做）** | 大步长→97%；小步长→**72%**（证明阈值生效、判定在轮界） |
| 2 | 工具输出截断 / 落盘 | **OBSERVED** | 头/尾各 10,000 字符 + 显式标记 + 全文落盘（字节级核对） |
| 2b | 硬清（>10 轮） | **OBSERVED** | t12 出现 `[Tool result omitted — too old]` |
| 2c | 软裁（>4000 字符旧结果） | `UNOBSERVABLE` | 12 轮窗口内未体现；wire 请求字节不可抓 |
| 3 | 连续三次压缩 | **OBSERVED** | 3 次事件、segment 累积、判据 FAIL（硬约束丢失，非复活） |
| 4 | 恢复语义 | **OBSERVED** | `-r` 生效；`--restore-code` 无还原效果 |
| 4b | **Q-01 裁决** | **`OBSERVED`（直接证据，§4.7）** | `/rewind` 真实执行后磁盘未变、`rewind_points.jsonl` 0 字节、对话被截断 → 支持"不还原文件" |
| 5 | 记忆 | `NOT_RUN` / `UNOBSERVABLE` | headless 短会话 + `/flush`、`/dream` 无 headless 入口 + `memory-v2/` 未创建 |
| 6 | 缓存 | **OBSERVED**（CLI 侧）/ `UNOBSERVABLE`（服务端） | 三桶读数、会话内前缀累积饱和、硬清→缓存击穿→成本 2.9× |
| — | `/context`、`/session-info`、`/compact`、`/rewind`、`/flush`、`/dream` | `NOT_RUN` | TUI 无法初始化 + slash 在 headless 不执行（§7） |

---

## 12. 对 T14～T18 的回填建议（供主 Agent 汇总裁决）

| 机制 | 本轮可回填值（引用本文件） | 强度 |
|---|---|---|
| CM-05 触发线 | Grok 触发 = **配置 `context_window` × `auto_compact_threshold_percent`（默认 85）**；**判定在轮界（该轮 payload 加入后）执行**，触发读数 = **阈值 + 轮内增量**（阈值 70 + 小步长 → **72%**；阈值 70/85 + 大步长 → 均 97%）（§1.5、§1.10、§3.4）。**口径须写"触发读数 ≥ 阈值"，不得写"阈值即触发点"** | 强（磁盘事件 + 阈值对照） |
| CM-06 压缩 | 压缩**是 side-model 调用**（`elapsed_ms` 41.1~475.9 s 有真实耗时）；**两趟**由 `compactionCount=2/事件` 实证（§1.5） | 强 |
| CM-07 摘要/裁剪 | 默认模式 = **segments**（`segment_NNN.md` + `INDEX.md`，`detail=verbose`）；压缩比 74%（1 次）/90%（同质连续 3 次）；**连续 3 次后早期关键约束丢失**（§3.5） | 强（判据来自检查器） |
| CM-04 工具输出 | bash 模型可见上限 = **头/尾各 10,000 字符**（非文档的 65,536 字节）；**全文落盘** `<session>/terminal/call-<id>.log` 且**路径写给模型**；硬清占位符 `[Tool result omitted — too old]`（§2.4） | 强（字节级） |
| CM-10 恢复 | `-r` 恢复 = 重放/重建；**`/rewind` 不还原磁盘文件**（Q-01，**直接执行观测**：磁盘未变 + `rewind_points.jsonl` 0 字节 + 对话截断 + `rewind_marker` 落盘，§4.7） | **强（直接证据）** |
| CM-08 记忆 | 本轮**未能证实或否证**捕获/Dream/注入（§5） | 弱（未测） |
| CM-12 缓存 | CLI 侧三桶可读；会话内前缀缓存累积至 ≈60k 饱和；**硬清使缓存击穿、单轮成本 ×2.9**；服务端 TTL/键 `UNOBSERVABLE`（§6） | 强（服务端回传读数） |
| CM-11 错误 | 网络超时重试实测 `max_retries=15`（与 T12 记录的默认 8 口径不一致，待核）；压缩单次最长 475.9 s（§7） | 中 |

---

## 13. 交给主 Agent 的未决项

1. **`max_retries` 默认值口径**：实测 15 vs T12 记录 8 → 需核（可能是不同代码路径/1.0.52 变更）。
2. **`toolset.bash.output_byte_limit=65536` 是否仍为默认**：本轮两条路径均不按其表现 → 建议 T12/T21 复核文档或实测更多尺寸定位阈值。
3. **软裁（4000/1500/1500）是否生效**：`UNOBSERVABLE`，建议用 OTEL 导出（`grok_code.*`）或代理抓 wire 请求复核。
4. **触发读数 − 阈值 的分布**：本轮仅 2 个点（72% / 97%），**不声称统计意义**；如需分布，需多轮小步长逼近。
5. **记忆条件**：如需 CM-08 结论，需 TUI（`/flush`、`/dream`）或更长的 headless 窗口。
6. **其它 slash 路径**（`/context`、`/session-info`、`/compact`）**现已具备 TUI 条件**（§4.7 的 `/bin/zsh -f` 修法）→ 建议补做。

### 13.1 已闭环（本次补测）

- ~~`threshold_percent=70` 变体~~ → **已做**（§1.10）：阈值生效，触发读数 = 阈值 + 轮内增量。
- ~~`/rewind` 直接复跑~~ → **已做**（§4.7）：直接证据，维持原裁决。
- **TUI 阻塞根因** → **已定位**：pane shell 被用户 profile 的 `safe-delete` 钩子卡住；用 `/bin/zsh -f` 规避。

---

## 更新日志

| 日期 | 更新 |
|---|---|
| 2026-10-15 | 建档：t19-grok 完成条件 1~4、6 实测与 Q-01 裁决；条件 5（记忆）标 NOT_RUN/UNOBSERVABLE；记录 TUI 阻塞与 slash 不执行两项环境限制；登记窗口口径不一致、截断阈值与文档不符、硬清击穿缓存等 3 项新发现。 |
| 2026-10-15 | **补测轮（主 Agent 批准）**：① 新增 **§1.10 阈值生效性补测**（threshold=70：大步长→97%、**小步长→72%**）→ 口径定为「判定在轮界、触发读数 = 阈值 + 轮内增量」；② 新增 **§4.7 `/rewind` 直接执行**（tmux TUI，`/bin/zsh -f` 修法）→ **Q-01 由间接证据升格为直接证据**，维持原裁决；③ §4.4/§7/§8/§11/§12/§13 同步更新（含 TUI 阻塞根因=safe-delete 钩子）；④ 用量更新为 ≈61 次调用 / ≈0.93 USD。 |
| 2026-10-15 | **T19R P-3 费用复核定稿**：批次合计改为「52 次 CLI 调用（51 有回执）/ **$0.9757**（Σ total_cost_usd）/ 78 轮」；原「≈61 次 / ≈0.93」标注为批内自计近似（口径未完全对应），费用以逐日志为准；TUI 路径费用未含（自估 <$0.02）（主 Agent） |
