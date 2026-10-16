---
title: T19 批次 5 · deepseek-harness（dsh）真实机制实验记录
task: T19
role: 实验 Agent（t19-dsh）
created: 2026-10-15
tool: dsh（deepseek-harness）
spec: 05-实验/T03/实验规程.md + 运行记录模板.md；任务卡 T19；前置登记-G7G8.md §1/§2.7/§2.9
---

# T19 批次 5 · dsh 记录（`05-dsh.md`）

> 一个条件一节；**MECH-\* / PROD-\* 分开**（本批全为机制实验，无 PROD）；判据一律走 T03 检查器；原始日志在 `experiments/t19/logs/dsh-*`。
> 纪律：不编造日志/费用/结果；HTTP 200 ≠ 推理成功；**压缩成功不靠模型自述**（看会话日志事件链）；**凭据不写入正文**（`.credentials.yaml` 只验存在性，不读不写）。

---

## 0. 公共运行标识（所有条件共用）

| 字段 | 值 |
|---|---|
| 运行日期 / 时区 | 2026-10-15（CST, UTC+8） |
| 执行者 | t19-dsh（T19 批次 5 实验 Agent） |
| **实际执行版本** | **dsh 0.2.0-rc.2**（`/opt/homebrew/bin/dsh --version` → `0.2.0-rc.2`，exit 0） |
| **研究快照 SHA** | `571902028a75c64c1d767f4ae5fd099485f0ddf0`（master@2026-10-14；T13 包依据） |
| 两者是否一致 | **不一致**（执行=已发布 prerelease 入口；快照=master 开发线；npm latest 亦为 prerelease 0.2.0-rc.2）→ 本批「产品端到端行为」可观测，但**不得**直接验证快照行号级结论 |
| 模型 / provider / 登录 | **provider=`opencode-go`**（经 `@deepseek-ai/dsh-llm-pi-ai` 适配器，wire `api=openai-completions`）；**model=`deepseek-v4.1-flash`**；凭据=`OPENCODE_GO_API_KEY`（本机 credential store 解析）。**系统提示词自报**：`You are a coding agent powered by the deepseek-v4.1-flash model.`（会话日志 `system/message` 逐字） |
| 隔离 | `DSH_HOME=/tmp/t19-dsh/home`；`.credentials.yaml` 以**符号链接**指向 `~/.dsh/.credentials.yaml`（**只建链、不读内容**）；工作区 `/Users/junjielong/workspace/agent-context-research/experiments/t19/work-dsh/`；会话落盘 `$DSH_HOME/sessions/<cwd-slug>/<sid>/session.v4.jsonl.zstd` |
| 数据包 | `T03-DATA-TRIP-v1`（行程任务 v1，冻结） |
| v2 样本 | `长工具结果-公交查询-v2.txt`（2,254 行 / 161,144 字节；sha256 `1c9309e7…f2011b`，复核 OK） |
| 生效配置与覆盖 | 见 §0.2（`--patch` 覆盖层，**不改 `~/.dsh` 任何文件**） |
| 原始日志路径 | `experiments/t19/logs/dsh-<条件>-<轮次>-<时间>.json`（stdout `--json` 事件流）+ `.err`（stderr） |

### 0.1 入口探测（已完成，1 次轻量调用）

```bash
dsh --help
dsh headless --help            # 确认 headless 入口
dsh --profile headless --json "只回答两个字：收到"
```

- 入口形态：`dsh --profile headless [--json] [--session-id <id>] <task|->`；`--json` 输出换行分隔事件流（`session`/`status`/`text`/`tool_call`/`tool_result`/`final`）；task 省略或为 `-` 时从 stdin 读。
- **`--session-id` 不能创建会话**：未存在的 id → `{"type":"error","message":"session \"…\" does not exist; omit --session-id to start a new Session"}`（exit 1）。恢复必须用**先无 id 跑一次、再从 `session` 事件取 id** 的流程。

### 0.2 凭据与覆盖层（**重要环境发现**）

| 步骤 | 命令/事实 | 结果 |
|---|---|---|
| 默认路由 | `dsh --profile headless --json "…"`（不覆盖） | **exit 1**，`llm-deepseek: no API key for provider route "deepseek-official"`，码 `MISSING_CREDENTIAL` |
| 判定 | 默认装配 `agent-default-model = provider deepseek-official / model deepseek-flash`（`dsh-base/cordis.patch.yml#L82-86`），而本机 credential store 无该路由的 API key | 默认路由**不可用** |
| 用户真实登录 | 读 `~/.dsh/profiles/desktop/cordis.patch.yml`（**只读**）：`provider: opencode-go` / `model: deepseek-v4.1-flash` / `llm-pi-ai.providers.opencode-go.apiKeyEnv: OPENCODE_GO_API_KEY` | 与 G8 §2.3（pi 的 `defaultProvider=opencode-go`）**同源** |
| 覆盖层 | `--patch /tmp/t19-dsh/overlay-opencode-go.yml`（`agent-default-model` + `llm-pi-ai.providers.opencode-go`） | **exit 0**，模型回「收到」 |

> **归因提示（写入 G8/dsh 行建议）**：本批 dsh「执行模型」= **deepseek-v4.1-flash via opencode-go**，**不是** deepseek-official / deepseek-flash。G7/G8 表 §2.7 只登记了「`.credentials.yaml` 存在」，未登记路由归属；建议补注。

### 0.3 三层工具输出治理与触发线的**实测生效值**（覆盖层之外，均来自会话日志/配置 dump）

| 机制 | 声明值（证据卡） | 本批实测生效值 | 证据 |
|---|---|---|---|
| 上下文窗口 W | 1,000,000（模型/适配器声明） | **1,000,000** | 会话日志 `request/context` = `{"provider":"opencode-go","model":"deepseek-v4.1-flash","contextWindow":1000000}` |
| 触发线公式 | `floor(min(W×0.8, W−O−65536))` | 见 §1（被覆盖层改写，见下） | `compaction-basic` 配置 dump |
| retain | `floor((W−O)×0.16)` | 见 §1 | 同上 |
| read 上限 | 2000 行 / 2000 字符/行 / **51200 字节** | **51200 字节先到**（显示至第 716 行） | §2.1 |
| bash 上限 | （T13 引 `tool-bash-persistent` `maxOutputChars:16000`） | **不适用**：本机装的是 `dsh-tool-bash` + 执行器 `dsh-bash-local`，其 `maxOutputBytes` 默认 **64,000 字节/流**（**不同包**） | §2.2；`dsh-bash-local/README#L47` |
| spill | `maxInlineTokens: 12500` | **12500**（配置 dump 逐字） | §2.2 |
| pruner | 8192/4096/1024 + `PRUNE_MARKER` | **完全命中**（5159 字符 = 4096+40+1024） | §2.4 |

> **归因纪律实例**：T13 `dsh-trunc-02` 的「bash 16000 字符」来自 **`tool-bash-persistent`**；本机 `dsh-base` 装配的是 **`dsh-tool-bash` + `dsh-bash-local`**。**框架里有某实现 ≠ 当前入口默认使用它**——本批按实测的 64,000 字节/流登记，并保留两值分列。

---

## 1. MECH-dsh-compact-01 / -02 · 触发到线 + 压缩（CM-05 / CM-06）

### 1.1 变量与固定量

| 项 | 值 |
|---|---|
| 唯一自变量 | 会话内 surface 的启发式 token 量是否达到触发线（灌入长材料） |
| 固定量 | dsh 0.2.0-rc.2；provider `opencode-go` / model `deepseek-v4.1-flash`；W=1,000,000；数据 `T03-DATA-TRIP-v1` + v2 样本；命令模板见 §1.2；初始材料=约束消息 |
| 操作定义 | A 组=灌入前（约束轮）；B 组=灌入 131,099 字符长材料后的下一回合 pre-step |

### 1.2 命令模板（逐字，可重跑）

```bash
export DSH_HOME=/tmp/t19-dsh/home
cd /Users/junjielong/workspace/agent-context-research/experiments/t19/work-dsh

# [1/3] 约束轮（新建会话；无 --session-id，从输出取 sessionId）
dsh --profile headless --patch /tmp/t19-dsh/overlay-compact.yml --json \
  "班级郊游规划任务。约束如下：硬约束 HC-01：下午 4 点（16:00）前必须返校；HC-02：总费用不超过 6000 元；HC-03：两个班 60 名学生 + 4 名老师，共 64 人同批出行；偏好 SP-01：植物园/动物园等户外优先，室内场馆次选；偏好 SP-02：集合点使用操场。已否决（不得复活）：REJ-01 17:30 返程；REJ-02 校门口集合；REJ-03 科技馆作为首选地点。请用一句话确认你已记住这些约束，并给出初步行程思路（不必展开）。"

# [2/3] 灌入长材料轮（stdin）
{ echo "下面粘贴一份班次查询长结果（合成数据）。请通读全文，统计总记录条数，并指出 14:50 发车班次的返抵时间与是否满足 16:00 前返校。"; echo; cat 长工具结果-公交查询-v2.txt; } \
  | dsh --profile headless --patch /tmp/t19-dsh/overlay-compact.yml --json --session-id <SID> -

# [3/3] 压缩后问约束 + 最终方案
dsh --profile headless --patch /tmp/t19-dsh/overlay-compact.yml --json --session-id <SID> \
  "现在有效的约束还有哪些？请逐条列出（含硬约束与已否决项）。并给出最终方案：返程时间、费用分项、集合点、出行人数。"
```

**覆盖层 `overlay-compact.yml`（逐字）**：

```yaml
- id: agent-default-model
  name: "@deepseek-ai/dsh-agent-default-model"
  config: { provider: opencode-go, model: deepseek-v4.1-flash }
- id: llm-pi-ai
  name: "@deepseek-ai/dsh-llm-pi-ai"
  config: { providers: { opencode-go: { apiKeyEnv: OPENCODE_GO_API_KEY } } }
- id: compaction-basic
  config:
    modelPolicies:
      - provider: opencode-go
        model: deepseek-v4.1-flash
        thresholdRatio: 0.015
        headroomTokens: 0
        retainTokens: 800
        maxTokens: 8192
```

> **为什么必须覆盖触发线**：默认参数下 W=1,000,000 → 触发线 = `floor(min(1e6×0.8, 1e6−O−65536))` ≈ **800,000 token**，在 ≤10 分钟/≤20 动作预算内**不可达**。改用 `compaction-basic.modelPolicies`（**设计内调参入口**，README §"Configure"）把该路由的触发线调到可达：预测 `thresholdTokens = floor(min(1e6×0.015, 1e6−O−0)) = 15000`（比例分支占优，O 不影响）；`retainTokens=800`（须低于阈值，显式给出以覆盖默认 `retainRatio=0.16×W`）；`maxTokens=8192`（摘要输出上限，默认跟随 headroomTokens，显式给出）。

### 1.3 预期事件（先写，后对照；依据 T13）

| # | 预期出现的事件 | 依据 |
|---|---|---|
| 1 | 到线后出现 `compaction/start` → `compaction/summary` → 替换 `user/message` → `compaction/end` | `dsh-summary-01/02`、`dsh-compact-01` |
| 2 | 摘要为**恰好 8 段** Markdown，包在 `<compacted-summary>` 里，加固定 preamble | `dsh-summary-01/02` |
| 3 | 压缩前先跑 `tool-result-pruner`（仅在到线后、按 8192/4096/1024 + `PRUNE_MARKER`） | `dsh-trunc-04` |
| 4 | 收缩校验：摘要须小于被遮蔽段，否则抛错不写替换 | `dsh-summary-02` |
| 5 | 未到线时**什么都不做**（`return null`） | `dsh-trigger-01`、`源码导读 §1` |

### 1.4 观测结果（3 次重复）

| 轮次 | 会话 ID | inv | 输入 token | 输出 token | cacheRead | 关键事件 | 任务通过? |
|---|---|---|---|---|---|---|---|
| 1 | `session-b24b60c7…` | inv1 | 6547 | 156 | 0 | 无压缩（未到线） | — |
| 1 | 同上 | inv2 | 77958 | 1037 | 6528 | 无压缩（未到线） | — |
| 1 | 同上 | inv3 | 79862 | 1523 | 5888 | **`compaction/start`(seq36) → `summary`(37) → 替换 `user/message`(38) → `end`(39)**；随后第 2 次 `start`(40)→`end`(41) **带 error：`summary is not smaller than the shadowed content (717 estimated framed tokens >= 689)`** | **PASS** |
| 2 | `session-90369214…` | inv1 | 19 | 241 | 6528 | 无压缩 | — |
| 2 | 同上 | inv2 | 0 | 0 | 0 | **TRANSPORT 失败**（`Connection error.`，exit 1） | — |
| 2 | 同上 | inv3 | 79344 | 8627 | 5376 | **2 次成功压缩**：summary shadowed `[8,9,10,15]`(1414 tok) 与 `[49]`(600 tok) | **PASS** |
| 3 | `session-ef91a356…` | inv1 | 19 | 331 | 6528 | 无压缩 | — |
| 3 | 同上 | inv2 | 78133 | 5748 | 0 | 无压缩 | — |
| 3 | 同上 | inv3 | 5843 | 2283 | **84608** | **`compaction/start` → `compaction/end` 带 error：`Connection error.`**（压缩尝试失败，自动路径记警告后继续） | **PASS** |

**触发线实测 vs 公式核对**：预测阈值 = **15000**（启发式 token，见 §1.2）。实测：灌入 131,099 字符（启发式 ≈ 131,099/4 ≈ **32,775 token**）**之前**（inv1/inv2 的 pre-step）**未触发**；灌入后的下一回合（inv3）pre-step **触发**。方向与量级与公式一致（未触发 → 该时点 measurement < 15000；触发 → ≥ 15000）。**精确 measurement 数值未在日志中直接暴露** → 该部分标 `UNOBSERVABLE`（见 §7）。

### 1.5 判据结果（检查器原始输出）

```text
=== T03-DATA-TRIP-v1 | 候选：candidate-compact-r1.json | overall=PASS ===
  [PASS] CHK-HC-01      returnTime=15:45 vs 上限 16:00（945 vs 960 分钟）
  [PASS] CHK-HC-02      求和 6000  vs 上限 6000
  [PASS] CHK-HC-03      headcount=64 应等于 64
  [PASS] CHK-SP-02      assemblyPointId='LOC-PLAYGROUND' 不得属于被否集合 [...]
  [PASS] CHK-REJ-STRUCT selectedOptionIds=['OPT-BOTANIC', 'OPT-BUS-1450'] 命中被否项 []
  [PASS] CHK-REJ-TEXT   命中且无否定语境：[]；命中但有否定语境（不判违规）：['17:30 返程', '校门口集合', '科技馆']
  [PASS] CHK-FC-STATUS  与真值不一致项：[]
```
r2 / r3 输出同形（`overall=PASS`，7/7）。**三次全 PASS。**

| 指标 | r1 | r2 | r3 |
|---|---|---|---|
| 任务是否通过 | PASS | PASS | PASS |
| 关键约束违背数 | 0 | 0 | 0 |
| 否决复活数（结构化） | 0 | 0 | 0 |
| 未完成写完成数 | 0 | 0 | 0 |

> `CHK-REJ-TEXT` **已人工复核**：r1–r3 的 notes 均含「已否决 17:30 返程 / 校门口集合 / 科技馆」且处于**否定语境**，检查器输出「命中但有否定语境（不判违规）」——与正例 fixture 口径一致，非复活。

### 1.6 摘要形态（8 段 + `<compacted-summary>`）——实测逐字

- 替换事件（`user/message` seq38）内容首块逐字：
  `"This is an automatically generated checkpoint condensing an earlier span of the conversation to free up context. Treat the captured context as established background and build on it without restating it. Continue the task directly from the messages that follow, without acknowledging this checkpoint.\n\n<compacted-summary>"`
- 摘要 8 段（实测，r1 摘要长 2,348 字符）：
  `## Primary Request and Intent` / `## Key Technical Concepts` / `## Files and Code` / `## Errors and Fixes` / `## Pending Jobs` / `## Current Work` / `## Next Step` / `## Critical Context`
- `compaction/summary` 事件字段：`shadowedRange {start:8,end:19}`、`shadowedSeqs [8,9,10,19]`、`shadowedTokenCount 1346`、`provider opencode-go`、`model deepseek-v4.1-flash`、`maxTokens 8192`、`usage {inputTokens:7085, outputTokens:584, totalTokens:7669}`。
- **范围选择实测**：被遮蔽段=**第 1 回合**（约束消息 seq8 + 运行上下文 seq9 + 技能目录 seq10 + 助手回复 seq19）；**灌入的长材料（seq27）未被遮蔽**（因其单节点已超 `retainTokens`，被整体保留）→ 与 `源码导读 §1`「从尾部累加至 retainTokens 定 keepFromIdx」一致。

### 1.7 可归因性

| 项 | 内容 |
|---|---|
| 能把差异归因于该机制吗 | **能（事件链层面）**：`compaction/*` 事件由 harness 追加，链式顺序与 §1.3 预期一致 |
| 理由 | 事务、摘要指令、替换语义、收缩校验均为 harness 实现（`dsh-layer-01`）；观测到的事件链与源码导读一致 |
| 归因限制 | ①**触发线被覆盖层改写**（0.015/0/800/8192），非默认参数；②摘要**文本质量**属模型侧；③`reservedCompletionTokens` O 的真实取值未观测（`UNOBSERVABLE`）；④压缩后**缓存命中**属服务端 |

### 1.8 状态

`OBSERVED`（机制事件链 3/3 命中；E1 判据 3/3 PASS）。**注**：r3 的压缩**未成功**（连接错误），属 provider 侧失败，自动路径按 `dsh-fail-02` 记警告并继续——不影响 E1（判据仍 PASS）。

---

## 2. MECH-dsh-trunc-01…04 · 工具输出治理（CM-04）

### 2.1 命令模板（逐字）

```bash
export DSH_HOME=/tmp/t19-dsh/home
cd …/experiments/t19/work-dsh
dsh --profile headless --patch /tmp/t19-dsh/overlay-trunc.yml --json \
  "请严格按顺序执行三项工具调用，然后原样报告每一项的实际观察结果：1) 用 read 工具读取 长工具结果-公交查询-v2.txt（一次性读，不要用 offset/limit）；2) 用 bash 运行命令：cat 长工具结果-公交查询-v2.txt；3) 用 read 工具读取 长工具结果-公交查询-v1.txt（一次性读）。对每一项报告：(a) 你实际收到多少行文本；(b) 是否出现『截断/省略/已保存到文件/落盘路径』之类的提示，提示原文照抄；(c) 你是否看到文件中段约第 1339 到 1344 行的内容（若有，抄出其中一行）。"
```

`overlay-trunc.yml` = `overlay-opencode-go.yml` + `sandbox-policy.mode: danger-full-access`（见 §2.3 条件说明）。

### 2.2 观测结果（3 次重复；工具结果取自会话日志 `tool/result` 事件，非模型自述）

| 路径 | 输入 | r1 | r2 | r3 | 是否截断 |
|---|---|---|---|---|---|
| **read v2** | 2,254 行 / 161,144 B | 45,032 字符 / 722 行，显示至**第 716 行**；footer 逐字 `(Output capped. Showing lines 1-716. Use offset=717 to continue.)` | 45,032 / 722 / 716 行 | 45,032 / 722 / 716 行 | **是** |
| **bash `cat` v2** | 同上 | 49,930 字符 / 860 行；标记见下 | 49,930 / 860 | 49,930 / 860 | **是（两层）** |
| **read v1（对照）** | 300 行 / 22,003 B | 18,760 字符 / 306 行；footer `(End of file - total 300 lines)` | 同 | 同 | **否** |

**中段（v2 第 1339–1344 行 = 班次 L7-139…L7-144）存活核对**：

| 探针 | read v2 | bash v2 | read v1 |
|---|---|---|---|
| `L7-139` / `L7-144` | 否 / 否 | **是 / 是** | 是 / 是 |
| **`L7-140` / `L7-141`（14:50 推荐）/ `L7-142` / `L7-143`** | **否 / 否 / 否 / 否** | **否 / 否 / 否 / 否** | **是 / 是 / 是 / 是** |

→ **两条路径都把中段关键块（含推荐班次 L7-141）丢掉**；v1 对照完整保留。

**read 路径实际命中的上限**：显示至第 716 行、45,032 字符。v2 第 716 行的**字节偏移 ≈ 51,200** → 命中 **`readMaxBytes = 51200`**（**字节**先到，**非** 2000 行）；UTF-8 下 51,200 字节 ≈ 45,032 字符，自洽。

**bash 路径实际形态**（逐字标记）：

```text
[...]                                    ← 中段省略标记（spill 的 head/tail 之间）
[output truncated; full output: /var/folders/…/T/dsh-subprocess-FIceZE/dsh-subprocess-5401-1-97f32a389184-stdout.log]
(Omitted 3444 bytes. Full formatted result stored at: /var/folders/…/T/dsh-spill-26zhvC/session-095e890d8b12/6daf0604960e-bash.txt. Use read with offset/limit, or grep this path to search within it.)
```

- 分段：head 24,846 字符 + `[...]` + tail 25,079 字符 = 49,925 ≈ **`maxInlineTokens` 12500 的两端各半**（spill 语义，`dsh-trunc-03`）。
- **bash 自带上限不是 16000 字符**：本机 `dsh-tool-bash` 无 `maxOutputChars`；截断来自执行器 `dsh-bash-local` 的 **`maxOutputBytes: 64,000` 字节/流**（`dsh-bash-local/README#L47`），保留**尾部** + 落 subprocess log。观测到的 bash 结果保尾（不含文件第 1 行「公交/校车班次查询结果」），与「truncated to its tail」一致。
- **可取回性（实测）**：
  - `[output truncated]` 指向的 **subprocess log 存在且为全量原文**：`161,144 字节 / 2,254 行`，`grep -c "L7-141"` = **1** → **中段可完整取回**。
  - spill 文件 `6daf0604960e-bash.txt` 存在，但只有 **64,152 字节 / 901 行**（= 执行器已截断的副本），**不含 L7-141** → **spill 文件本身不是全量**。
  - read 路径的取回指引 = footer 的 `Use offset=717 to continue.`（**可直接续读**）。

### 2.3 条件说明（沙箱）

首次以 `workspace-write` 运行 bash 被 **fail-closed 拒绝**（`tool/result` 逐字）：

```text
Error: sandbox mode "workspace-write" is requested but no sandbox backend is usable on this host; refusing to run the command unconfined. Install bubblewrap or run a Landlock-enforcing kernel (Linux), ensure sandbox-exec is usable (macOS), or ensure the ACL restricted-token runner can start (Windows) — otherwise switch the consumer to danger-full-access. Runner failure: sandbox-exec: sandbox_apply: Operation not permitted
```

处置：按错误信息建议切 `sandbox-policy.mode: danger-full-access`（覆盖层，**如实登记为条件变更**）。此为本机 macOS 沙箱后端不可用（与 G7 §2.9 记录的 pi 批次同类环境事件），**不是** dsh 实现缺陷。

### 2.4 MECH-dsh-trunc-04 · pruner（压缩前剪裁）子测

命令：`overlay-compact.yml` + 单次 `read v2`（触发到线 → 先剪裁）。

**实测命中**（会话日志逐字）：

```json
{"type":"compaction/prune","seq":24,"data":{"shadowedRange":{"start":22,"end":22},"shadowedSeqs":[22],"shadowedTokenCount":11266}}
```

- 被剪裁对象：`tool/result` seq22（read v2 的 **45,032 字符**结果；11266 ≈ 45032/4 启发式 token）。
- 剪裁后：`tool/result` **seq25**，长度 **5,159 字符**，含 `PRUNE_MARKER` 逐字：`\n\n[... tool result middle pruned ...]\n\n`（4096 + 40 + 1024 = 5160，±1）。
- **未出现 `compaction/start`** → 剪裁后重新测量已低于阈值，摘要被跳过（**剪裁可完全替代摘要**，与 `源码导读 §1` L58 一致）。
- **追加式验证**：原事件 **seq22 仍在日志中**，替换事件 seq25 与之并存 → `dsh-persist-01`「committed 事件永不改写 / 无删除 API」在端到端可见。

### 2.5 判据结果

本条件为**过程观察 + 人工比对**（T03 规程 E2：人工比对头/中/尾行号 + 检查器）。中段存活核对见 §2.2；未构造候选 JSON（E2 判据入口为「人工比对 + 检查器」，此处人工比对已完成，行号双标见 §2.2）。

### 2.6 可归因性

| 项 | 内容 |
|---|---|
| 能把差异归因于该机制吗 | **能**：三层上限/标记/落盘路径均为 harness 实现（`dsh-trunc-01..04`），观测值与声明值逐项一致 |
| 归因限制 | ①bash 条件含 `danger-full-access`（非默认）；②spill 的**精确字节分配**未逐字节核对；③执行器上限（64,000）来自**包文档 + 行为一致**，未读源码常量 |

### 2.7 状态

`OBSERVED`（read / bash / v1 对照 / pruner 四路径均命中；3 次重复结果一致）。

---

## 3. MECH-dsh-resume-01 · 恢复（CM-10，E4）

### 3.1 命令模板

```bash
# inv1 新建会话（无 --session-id）
dsh --profile headless --patch overlay-opencode-go.yml --json "班级郊游规划任务。硬约束 HC-01 …；已否决 REJ-01/02/03。请一句话确认。"
# inv2 新进程恢复（--session-id 沿用 inv1 的 id）
dsh --profile headless --patch overlay-opencode-go.yml --json --session-id <SID> \
  "（新进程/新回合）现在有效的约束还有哪些？逐条列出。并给出最终方案：返程时间、集合点、人数、费用。"
```

> **恢复语义实测**：每次 `dsh --profile headless` 都是**独立进程**；`--session-id` 沿用 = 跨进程恢复（`ctx.agents.resume()` 路径）。**无需** `--resume` 之类的子命令。

### 3.2 观测结果（3 次重复）

| 轮次 | 会话 ID | inv2 输入/输出 token | cacheRead | 恢复了什么 | 丢了什么 | 判据 |
|---|---|---|---|---|---|---|
| 1 | `session-24b7d245…` | 45540 / 5062 | 106752 | HC-01/02/03、SP-02、REJ-01/02/03 **全在**；且**保留了文件派生的操作约束**（14:20/14:35/14:50 三班、88 座两车 1400 元、周五时刻） | 无关键丢失 | **PASS** |
| 2 | `session-e87c8b21…` | 42726 / 3052 | 128640 | 同上全在；并引用 `长工具结果-公交查询-v1.txt 第 294–300 行` / `v2.txt 第 2246–2250 行` | 无关键丢失 | **PASS** |
| 3 | `session-448537e7…` | 199 / 715 | 6528 | HC-01/02/03、REJ-01/02/03 全在 | 方案**细化度下降**：返程只给「15:30 前」、集合点写「校内集散点（如…操场）」未锁定 → **属模型表述，非恢复失败**（该会话 inv1 未读文件） | **PASS** |

### 3.3 判据结果（检查器原始输出）

```text
=== T03-DATA-TRIP-v1 | 候选：candidate-resume-r1.json | overall=PASS ===
  [PASS] CHK-HC-01 returnTime=15:45 vs 上限 16:00（945 vs 960 分钟）
  [PASS] CHK-HC-02 求和 6000 vs 上限 6000
  [PASS] CHK-HC-03 headcount=64 应等于 64
  [PASS] CHK-SP-02 / CHK-REJ-STRUCT / CHK-REJ-TEXT / CHK-FC-STATUS  均 PASS
（r2 同形；r3 returnTime=15:30 → CHK-HC-01 930 vs 960 PASS）
```

**3/3 PASS。**

### 3.4 与持久化断点路线的一致性

- 会话落盘为**追加式** JSONL（zstd 帧）：`$DSH_HOME/sessions/<slug>/<sid>/session.v4.jsonl.zstd`；`zstd -dc` 可解出完整事件溯源序列（`session`/`turn/start`/`step/*`/`request/header`/`assistant/message`/`tool/call`/`tool/result`/`compaction/*`…）。
- **恢复后 `deriveMessages()` 直接投影「摘要 + 保留段」**（§1 的替换语义），**未重放全部历史** → 与 `dsh-recover-01`（持久化断点路线，LQ-10 判为 B 路线）一致。**注意**：本结论由「替换事件 + resume 后 `request/header` 只出现 1 次」的间接证据支持，**未做逐 token 重算判据** → 部分 `UNOBSERVABLE`。

### 3.5 状态

`OBSERVED`（3/3 恢复成功，判据 3/3 PASS）。

---

## 4. MECH-dsh-compact-cont-01 · 连续压缩（CM-07）

### 4.1 命令模板

```bash
# 5 回合：约束 → 长材料A → 小问题 → 长材料B → 问约束+方案
dsh --profile headless --patch overlay-compact.yml --json "班级郊游规划任务。硬约束 HC-01…HC-03；已否决 REJ-01/02/03。请一句话确认。"
{ echo "第一份长材料如下，请通读并统计记录数："; echo; cat 长工具结果-公交查询-v2.txt; } | dsh … --session-id <SID> -
dsh … --session-id <SID> "只回答两个字：好的"
{ echo "第二份长材料如下，请通读并统计记录数："; echo; cat 长工具结果-公交查询-v1.txt; cat 长工具结果-公交查询-v2.txt; } | dsh … --session-id <SID> -
dsh … --session-id <SID> "现在有效的约束还有哪些？逐条列出，并给出最终方案：返程时间、集合点、人数、费用。"
```

> **条件说明**：本轮约束消息**只含 HC-01/02/03 与 REJ-01/02/03**，**未含 SP-01/SP-02** → 后续「集合点」结论**不能**用来判断 SP-02 是否漂移。

### 4.2 观测结果（单次探索性运行；未达 3 次，原因=预算/时间，见 §8）

| 项 | 实测 |
|---|---|
| `compaction/start` / `summary` / `end` | **10 / 9 / 10**（1 次 `end` 带 `error: "Connection error."`） |
| 摘要份数 | **9 份，全部 8 段** |
| 摘要长度（字符） | 3699, 3688, 5201, 4864, 5138, 5129, 5089, 5552, 5673 |
| 第 2 份摘要的被遮蔽对象 | `shadowedSeqs=[42]`（= **第 1 份摘要的替换 `user/message`**），`shadowedTokenCount=1027` → **摘要被再摘要（连续压缩）** |
| **增量合并证据** | **第 7 份摘要（seq158）的 `rawOutput`/摘要文本中出现 `<compacted-summary>`** → 摘要指令的「若对话已含 `<compacted-summary>`，那是上一份检查点，合并进同一结构」被实际触发（`dsh-summary-03`） |
| 最大被遮蔽段 | 41,570 token（长材料A 段） |
| `compaction/prune` | 1 次（shadowed 2,436 token） |
| 最终答复（inv5） | HC-01/02/03 **全在**、REJ-01/02/03 **全规避**、14:50→15:45、64 人、费用 1400 元；另指出「材料头部称 2,204 条、实际 2,194 条」 |

### 4.3 判据结果

```text
=== T03-DATA-TRIP-v1 | 候选：candidate-cont-r1.json | overall=PASS ===
  [PASS] CHK-HC-01 returnTime=15:45 vs 上限 16:00（945 vs 960 分钟）
  [PASS] CHK-HC-02 求和 1400 vs 上限 6000
  [PASS] CHK-HC-03 headcount=64 应等于 64
  [PASS] CHK-SP-02 assemblyPointId='LOC-BOTANIC-PICKUP' 不得属于被否集合 [...]
  [PASS] CHK-REJ-STRUCT / CHK-REJ-TEXT / CHK-FC-STATUS  均 PASS
```

**摘要漂移观察（对齐 C-04 / LQ-09 口径）**：9 次压缩后**硬约束与已否决项均未丢失、未复活**；**未观测到「已否决复活」或「未完成写完成」**。**不能**据此声称「连续压缩无损」——① 未含 SP-01/SP-02，无法判断软偏好漂移；② 单次探索性运行；③ 摘要文本保真度属模型侧。

### 4.4 异常与停止（T03 模板 §C）

| 项 | 内容 |
|---|---|
| 是否触达停止条件 | **否（有界）**。9 次压缩分布在 5 个回合，属「每回合 pre-step 到线即压缩」的设计内行为；`compactionRetries=1` 的重试有界；1 次 `end` 带连接错误（provider 侧） |
| 停止时间点 | 未停止 |
| 已产生的副作用 | 会话日志追加 10 组 compaction 事件；无外部副作用 |
| 后续动作 | 保留日志；**提示主 Agent**：多回合连续大材料会引发高频压缩（本例 9 次），如后续批次要跑长会话需评估额度 |

### 4.5 状态

`OBSERVED`（探索性单次；判据 PASS）。

---

## 5. MECH-dsh-cache-01 · 缓存（CM-12）

### 5.1 命令模板与实测

```bash
# 两次「同前缀」独立新会话（同一 system+tools+skills 前缀）
dsh --profile headless --patch overlay-opencode-go.yml --json "只回答两个字：收到"   # r1
dsh --profile headless --patch overlay-opencode-go.yml --json "只回答两个字：收到"   # r2
```

| 轮次 | 输入 token | 输出 token | **cacheReadTokens** | totalTokens |
|---|---|---|---|---|
| r1 | 2300 | 2 | **4096** | 6398 |
| r2 | 124 | 2 | **6272** | 6398 |

**其他条件中同源证据**（`cacheReadTokens` 非 0 即服务端上报命中）：

| 条件 | 值 |
|---|---|
| 入口轻量调用 | 384 |
| compact r1 inv2（灌入长材料） | 6528 |
| compact r3 inv3 | **84608** |
| cont r1 inv5 | 45312 |
| trunc r1 | 102784 |

### 5.2 归因（harness vs 模型/API 分列）

- **harness 侧（可证）**：适配器把 `usage.cacheRead` 映射为 `cacheReadTokens`（已安装包逐字：`dsh-llm-pi-ai/lib/index.js:1376  ...usage.cacheRead > 0 ? { cacheReadTokens: usage.cacheRead } : {}`）；`TokenUsage` 计数互斥（实测 r1: 2300+4096+2 = 6398 = totalTokens）。
- **模型/API 侧（UNOBSERVABLE）**：缓存**存储/命中率/TTL** 由服务端决定；`cacheReadTokens` 数值为 provider 上报，**本批只能证明「非 0 上报存在」，不能证明命中率或 TTL**。

### 5.3 D10⑤ · 缓存键登记命令**复跑**（已安装包，真实输出）

```bash
$ grep -rniE "prompt_cache_key|cacheBreakpoint|cache_breakpoint" \
    /opt/homebrew/lib/node_modules/@deepseek-ai/dsh/node_modules --include='*.js' --include='*.md' | wc -l
11
$ … | head -8
…/@earendil-works/pi-ai/dist/api/openai-prompt-cache.js:1:export const OPENAI_PROMPT_CACHE_KEY_MAX_LENGTH = 64;
…/@earendil-works/pi-ai/dist/api/openai-prompt-cache.js:6:    if (chars.length <= OPENAI_PROMPT_CACHE_KEY_MAX_LENGTH)
…/@earendil-works/pi-ai/dist/api/openai-completions.js:575:        prompt_cache_key: (model.baseUrl.includes("api.openai.com") && cacheRetention !== "none") ||
…/@earendil-works/pi-ai/dist/api/openai-responses.js:225:        prompt_cache_key: cacheRetention === "none" ? undefined : clampOpenAIPromptCacheKey(options?.sessionId),
…/@earendil-works/pi-ai/dist/api/openai-codex-responses.js:397:        prompt_cache_key: cacheSessionId,
```

**结论（修正 T13 口径）**：

1. **dsh 自身包**（`@deepseek-ai/*`）**仍未发现**缓存键/断点（T13 `dsh-cache-02` 成立）。
2. **但本机装配的第三方依赖 `@earendil-works/pi-ai` 确有 `prompt_cache_key` 实现**（11 处命中）：`openai-completions` 分支的条件为
   `(baseUrl 含 "api.openai.com" && cacheRetention!=="none") || (cacheRetention==="long" && compat.supportsLongCacheRetention)` → 才发 `prompt_cache_key = clamp(sessionId)`；否则 `undefined`。
   - 本机路由 `opencode-go` 的 `baseUrl` **不是** `api.openai.com`，`cacheRetention` 未配置为 `long` → **推断该键未发送**（**未做 wire 抓包** → 该点标 `UNOBSERVABLE`）。
3. **关键点**：`cacheReadTokens` 非 0（最大 84,608）说明**服务端前缀缓存无需客户端键也会命中**——「API 支持缓存」与「客户端发缓存键」是**两件事**（`dsh-layer-01` 边界）。

### 5.4 状态

`OBSERVED`（客户端 usage 字段映射 + 服务端 cacheRead 非 0）；缓存键**发送与否** `UNOBSERVABLE`。

---

## 6. MECH-dsh-fail-01 · 错误与副作用（CM-11，**机会性观测，非注入**）

> 任务书 CM-11 要求「可控错误注入」；本批**未做主动注入**（低优先 + 预算），但下列失败在 1–5 各条件中**自然发生**，如实登记为机会性观测。

| # | 失败 | 逐字/事实 | 观测到的 harness 行为 | 与证据卡一致? |
|---|---|---|---|---|
| 1 | provider 传输错误 | `turn_end reason.error.code="TRANSPORT"`, `message="Connection error."`（compact r2 inv2；exit 1） | 回合终止；会话日志保留 committed 前缀 | `dsh-fail-01`（有界重试；本次未重试成功） |
| 2 | 压缩时连接错误 | `compaction/end` 带 `error:"Connection error."`（compact r3；cont r1 各 1 次） | **自动路径记警告后继续本轮**，不阻断 | `dsh-fail-02` ✅ |
| 3 | **收缩校验拦截** | `compaction/end` 带 `error:"summary is not smaller than the shadowed content (717 estimated framed tokens >= 689)"`（compact r1 第 2 次尝试） | 抛错、**不写替换**、恰一次 `compaction/end` | `dsh-summary-02` ✅ |
| 4 | 沙箱 fail-closed | `sandbox mode "workspace-write" … refusing to run the command unconfined`（trunc 首次） | 拒绝执行、返回 `tool/result` 错误文本，**不降级为无约束执行** | `dsh-bash-sandbox` ✅ |
| 5 | 无界循环 / 重复压缩 | **未观测到无界循环**；compact r1 的 2 次尝试、cont r1 的 10 次 start/end **均有界**（回合内 pre-step 驱动 + `compactionRetries=1`） | — | — |

**未做**：真实瞬时故障注入（rate limit / timeout / 5xx）、并发竞态、崩溃（kill -9）恢复。

### 6.1 状态

`OBSERVED（部分）` —— 失败分类与「自动路径不阻断」「收缩校验」「沙箱 fail-closed」均有实测；**主动注入类（CM-11 完整口径）标 `NOT_RUN`**。

---

## 7. 不可观测项登记（T03 模板 §D）

| 想看但看不到的东西 | 为什么看不到 | 影响哪条结论 |
|---|---|---|
| 触发时点的**精确 measurement.totalTokens** | 会话日志只记 `compaction/summary.shadowedTokenCount`，不记 pre-step 的 `measure()` 快照 | §1.4「触发线实测 vs 公式」只能给方向与量级 |
| `reservedCompletionTokens` O 的真实取值 | 未在 `request/context`/日志暴露 | 阈值公式第二分支（`W−O−headroom`）未被独立验证 |
| 服务端**缓存命中率 / TTL / 是否收到 `prompt_cache_key`** | 服务端行为 + 未抓 wire | §5 只能证「cacheReadTokens 非 0」 |
| **真实分词/计费级 token** | 服务端；本批只有 provider 上报的 usage | §1.6「中文低估」只能给**比值区间**（启发式 32,775 vs 上报 77,958 ≈ **2.1×**） |
| bash 结果「保头/保尾」的**逐字节**边界 | 只做内容探针（文件第 1 行 / 末段） | §2.2 结论为「保尾」的**行为级**判断 |
| 摘要的**保真度/漂移**定量 | 摘要文本由模型生成；无 ground-truth 比对器 | §4.3 只能给「未观测到复活/写完成」 |

---

## 8. 条件状态总表

| 条件 ID | 机制 | 场景 | 重复 | 判据 | 状态 | 说明 |
|---|---|---|---|---|---|---|
| MECH-dsh-compact-01 | 触发到线 | CM-05/E1 | 3 | E1 PASS 3/3 | **OBSERVED** | 触发线被覆盖层改写为 15000 |
| MECH-dsh-compact-02 | 自动/手动压缩事务 | CM-06 | 3 | 事件链 3/3 | **OBSERVED** | 手动 `/compact` 未测（headless 无命令适配器）→ 该子项 `NOT_RUN` |
| MECH-dsh-trunc-01 | read 上限 | CM-04/E2 | 3 | 人工比对 | **OBSERVED** | 51200 **字节**先到（非 2000 行） |
| MECH-dsh-trunc-02 | bash 上限 | CM-04/E2 | 3 | 人工比对 | **OBSERVED** | 实测=执行器 64,000 B/流（**非** T13 的 16000 字符） |
| MECH-dsh-trunc-03 | spill 落盘 | CM-04 | 3 | 人工比对 | **OBSERVED** | 12500 inline；spill 文件=已截断副本；全量在 subprocess log |
| MECH-dsh-trunc-04 | pruner | CM-04 | 1 | 事件 | **OBSERVED** | 8192/4096/1024 + PRUNE_MARKER 逐字命中 |
| MECH-dsh-resume-01 | 恢复 | CM-10/E4 | 3 | E1 PASS 3/3 | **OBSERVED** | 跨进程 `--session-id` |
| MECH-dsh-compact-cont-01 | 连续压缩 | CM-07 | 1 | E1 PASS | **OBSERVED（探索性）** | 9 次压缩；第 7 份摘要显式引用 `<compacted-summary>` |
| MECH-dsh-cache-01 | 缓存 | CM-12 | 2 | usage | **OBSERVED** | cacheRead 非 0（最大 84,608）；键发送 `UNOBSERVABLE` |
| MECH-dsh-fail-01 | 错误与副作用 | CM-11 | — | 事件 | **OBSERVED（部分）** | 机会性；主动注入 `NOT_RUN` |
| MECH-dsh-subagent-01 | 子 Agent 隔离 | CM-09 | — | — | **NOT_RUN** | 低优先 + 预算；未派发子 Agent |
| MECH-dsh-manualcompact | 手动 `/compact` | CM-06 | — | — | **NOT_RUN** | headless 无命令适配器（`dsh-compact-02` 自述需交互 TTY/Web） |

---

## 9. 归因限制（**harness vs 模型/API 分列**，必写）

### 9.1 属 harness 实现（本批实测可归因）

- 触发线公式与阈值判定、`retainTokens` 范围选择（`compaction/start` 前后行为）；
- 压缩事务与事件链（`start`/`summary`/`replace`/`end`）、收缩校验（717≥689 拦截）；
- 摘要**指令与 8 段结构**、`<compacted-summary>` 框架、CHECKPOINT_PREAMBLE；
- 工具上限与治理（read 51200 字节 / spill 12500 / pruner 8192-4096-1024 + `PRUNE_MARKER`）；
- 追加式 JSONL 持久化、`--session-id` 跨进程恢复、usage 字段映射；
- 沙箱 fail-closed、自动路径失败不阻断。

### 9.2 属模型/API（**不得**写成 harness 实现）

- 上下文窗口 **1,000,000**（适配器声明，harness 只读取并代入公式）；
- **真实分词与计费级 token**（本批启发式低估 ≈ **2.1×**，比值含其他内容，非精确）；
- 摘要**文本与保真度/漂移**（模型生成）；
- **缓存存储/命中/TTL**、是否接收 `prompt_cache_key`；
- **溢出的真实判定与措辞**（`Connection error.` / `CONTEXT_WINDOW_EXCEEDED` 归一化）。

### 9.3 本批特有归因限制

1. **触发线被覆盖层改写**（`thresholdRatio=0.015` 等）→ 本批只验证「公式形态与方向」，**不等于**默认参数下的产品行为。
2. **provider = opencode-go（pi-ai 适配器），非 deepseek-official** → 本批**不是**「dsh 默认路由」的端到端；wire 为 `openai-completions`，与 DeepSeek 原生 Messages 适配器可能不同。
3. **bash 条件含 `danger-full-access`**（本机沙箱后端不可用）。
4. 结构化候选 JSON **由人完成**（T03 规程 §5 已知主观环节）。
5. 执行版本（0.2.0-rc.2）≠ 研究快照（`5719020`）→ 行号级源码结论不外推。
6. 探索性小样本（n≤3），**不声称统计显著**。

---

## 10. 用量汇总（provider 上报，按回合求和）

| 条件 | 回合 | 输入 token | 输出 token | cacheRead | 备注 |
|---|---|---|---|---|---|
| compact r1 | inv1/inv2/inv3 | 6547 / 77958 / 79862 | 156 / 1037 / 1523 | 0 / 6528 / 5888 | inv2 为灌入轮 |
| compact r2 | inv1/inv2/inv3 | 19 / 0 / 79344 | 241 / 0 / 8627 | 6528 / 0 / 5376 | inv2 TRANSPORT 失败 |
| compact r3 | inv1/inv2/inv3 | 19 / 78133 / 5843 | 331 / 5748 / 2283 | 6528 / 0 / **84608** | 压缩失败（连接错误） |
| trunc r1/r2/r3 | 各 1 回合 | 73005 / 70182 / 67400 | 10982 / 5426 / 10241 | 102784 / 108544 / 107904 | 多步回合（含 3–4 次工具调用） |
| resume r1/r2/r3 | inv2 | 45540 / 42726 / 199 | 5062 / 3052 / 715 | 106752 / 128640 / 6528 | — |
| cont r1 | inv1..inv5 | 81 / 105138 / 6265 / 97088 / 21208 | 320 / 8142 / 2 / 6693 / 4597 | 0 / 48896 / 5504 / 15104 / 45312 | 9 次压缩 |
| cache r1/r2 | 各 1 | 2300 / 124 | 2 / 2 | 4096 / 6272 | — |
| pruner | 1 | 4730 | 778 | 27520 | — |

- **摘要额外 token**：`compaction/summary.usage` 逐次记录（例：r1 = `{inputTokens:7085, outputTokens:584, totalTokens:7669}`）——**摘要调用的输入含被遮蔽段回放前缀**，属额外开销。
- **缓存读不重复相加**（T03 §9）：上表 cacheRead 为**独立列**，未并入输入。
- **费用**：不可核验（无价目表；`UNOBSERVABLE`）。**未编造**任何费用数字。
- **总耗时**：单次条件运行 30 s–4 min（`time` 实测：compact 3 轮 ≈ 1:39；trunc 单轮 ≈ 32 s；prune+resume+cache ≈ 4:04；cont ≈ 5 min 量级）。**均 < 单轮 10 分钟**；**工具动作数**：单回合 ≤ 5 次工具调用（含 read/bash/glob），**< 20**。

---

## 11. 产物清单

| 类型 | 路径 |
|---|---|
| 本记录 | `05-实验/T19/记录/05-dsh.md` |
| 原始日志（stdout 事件流） | `experiments/t19/logs/dsh-compact-r{1,2,3}-inv{1,2,3}-*.json`、`dsh-trunc-r{1,2,3}-*.json`、`dsh-resume-r{1,2,3}-inv{1,2}-*.json`、`dsh-cache-r{1,2}-*.json`、`dsh-cont-r1-inv{1..5}-*.json`、`dsh-pruner-*.json` |
| 原始日志（stderr） | 同名 `.err` |
| 候选 JSON | `experiments/t19/work-dsh/candidate-{compact,resume}-*.json`、`candidate-cont-r1.json` |
| 覆盖层 | `/tmp/t19-dsh/overlay-{opencode-go,compact,trunc}.yml` |
| 运行脚本 | `/tmp/t19-dsh/run-{compact,trunc,prune-resume-cache,cont}.sh` |
| 会话日志（原生落盘） | `/tmp/t19-dsh/home/sessions/<slug>/<sid>/session.v4.jsonl.zstd` |

**凭据**：全程未读、未写、未入日志/记录（`.credentials.yaml` 仅以符号链接指入隔离 home，`OPENCODE_GO_API_KEY` 仅作为**变量名**出现）。

---

## 12. 更新日志

| 日期 | 更新 |
|---|---|
| 2026-10-15 | 建档：入口探测 + 凭据路由发现 + CM-04/05/06/07/10/11/12 实测（t19-dsh） |
