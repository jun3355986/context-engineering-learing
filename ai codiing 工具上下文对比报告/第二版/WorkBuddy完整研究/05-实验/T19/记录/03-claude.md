---
title: T19 批次 3 · claude 真实机制实验记录
task: T19
batch: 3
tool: claude-code-cli
role: 实验 Agent（t19-claude）
created: 2026-10-15
status: SUBMITTED（待 T19R 复核）
consumers: T19 主 Agent（汇总裁决）、T19R（复核）、T14～T18 回填
---

# T19 批次 3 · claude 真实机制实验记录

> **本文件解决什么**：在**统一条件**下用真实 claude CLI 运行 T05 `过程观察.md §2/§3` 点名的 NOT_RUN 项，产出**可复现记录**（命令逐字、预期事件、真实结果、失败案例），并如实登记**代理条件**带来的归因限制。
> **本文件不做什么**：不声称统计显著（探索性小样本）；不把 HTTP 200 当推理成功；不把模型自述当压缩成功的证据；不读/写凭据。

## 0. 运行标识与统一条件（所有条件共用）

| 字段 | 值 |
|---|---|
| 执行者 | t19-claude（T19 批次 3 实验 Agent） |
| 运行日期 / 时区 | 2026-10-15（13:56–14:5x）/ 本地时区 |
| 入口（绝对路径） | `/Users/junjielong/.local/bin/claude` → `~/.local/share/claude/versions/2.1.300`（软链实测） |
| **实际执行的可执行版本** | **2.1.300 (Claude Code)**（`claude --version` 实测） |
| **研究快照 / 冻结分发件** | **2.1.299**（npm tgz，sha256 `af955f68…bae7d`，`00-管理/版本表.md`） |
| 两者是否一致 | **不一致**：本地领先 1 patch（2.1.300 > 2.1.299）；闭源，执行版本只能取入口自报 |
| 任务数据包 ID | `T03-DATA-TRIP-v1`（行程任务，含 3 条已否决决定） |
| 数据版本哈希 | 包内 `manifest.sha256` 文件自身 sha256 = `2c7350732882288eaed1062d157b06c14c6294c8a955e0508873265a8153aa17`；`shasum -a 256 -c manifest.sha256` 自校验 **rc=0**（整包 9 文件全 OK） |
| 大输出样本 | `05-实验/T19/样本/长工具结果-公交查询-v2.txt`（2,254 行 / 161,144 B / 131,099 字符；sha256 `1c9309e718e1a8823f3f6b1e42c13e297642b2880959aaa41238dd84ccf2011b`，与 manifest 一致） |
| 工作目录 | `/Users/junjielong/workspace/agent-context-research/experiments/t19/work-claude/`（+ 冷启动对照 `/tmp/t19-claude-cold/`） |
| 原始日志 | `/Users/junjielong/workspace/agent-context-research/experiments/t19/logs/claude-*.jsonl`（另 `.stderr.log` / `.cmd.txt` / pane 文本） |
| 候选 JSON | `experiments/t19/candidates/cand-claude-e1-{raw,norm}.json` |
| **模型 / provider / 登录方式** | 会话自报 `modelUsage = {"claude-opus-5[1m]": {…,"canonicalModel":"claude-opus-5","provider":"firstParty","contextWindow":1000000}}`；登录=oauth_token（经本地代理） |
| **生效配置与覆盖** | 见 §0.2（代理条件 + 双套 hooks + 6 技能） |

### 0.1 版本三字段（取自 `05-实验/T19/前置登记-G7G8.md`，开跑日复测）

| 字段 | 值 | 复测 |
|---|---|---|
| 执行版本 | **2.1.300 (Claude Code)** | 2026-10-15 复测 `claude --version` = `2.1.300 (Claude Code)`，与登记一致（无漂移） |
| 研究快照 | 冻结分发件 **2.1.299**（npm tgz sha256 `af955f68…bae7d`） | 未变 |
| 本机污染 | **Paseo + teamai 双套 hooks**；**本地代理 + 全模型重映射**；6 个本地技能；`transcripts/` 非原生 | 见 §0.2（开跑日实测） |

### 0.2 代理条件（**归因限制必写**，开跑日实测）

- `~/.claude/settings.json` `env`：`ANTHROPIC_BASE_URL=http://127.0.0.1:15721`；`ANTHROPIC_AUTH_TOKEN` 在场（值不记录，长度 13）；`ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku-5-5` / `SONNET_MODEL=claude-sonnet-5[1M]` / `OPUS_MODEL=claude-opus-5[1M]` / `FABLE_MODEL=claude-fable-5[1M]`；`*_MODEL_NAME=deepseek-v4.1-flash`；`CLAUDE_CODE_SUBAGENT_MODEL=deepseek-v4.1-flash[1M]`。
- 代理进程在场：`lsof -nP -iTCP:15721 -sTCP:LISTEN` → `cc-switch … TCP 127.0.0.1:15721 (LISTEN)`（PID 67767）。
- hooks 双套：`~/.claude/settings.json` hooks 键 = `Notification / SessionEnd / Stop / StopFailure / UserPromptSubmit`（Paseo）+ `SessionStart / Stop / UserPromptSubmit / PostToolUse / SubagentStop`（teamai）。
- 首轮运行还收到 CLI 提示：*"…your requests go through 127.0.0.1:15721, which isn't compatible with this update…"*（代理兼容性提示，非错误）。
- **结论**：本批「Claude Code 实验」实为 **「CLI 机制 + 本地代理（cc-switch）+ 重映射模型」组合**；会话自报模型名 `claude-opus-5[1m]`，**实际后端可能为 deepseek-v4.1-flash**（重映射），**模型层不可控**。

---

## 1. 条件状态总表

| # | 条件 | 记录 ID | 场景 | 状态 | 首轮重复 | 关键读数 |
|---|---|---|---|---|---|---|
| 1 | 大工具输出（v2 161KB / v1 300 行对照） | `MECH-claude-工具输出-01` | E2 | **OBSERVED** | v2 ×3（+2 次重跑）+ v1 ×1（+1 次重跑） | v2：`<persisted-output>` + 2KB 预览 + 落盘路径；落盘文件与源**逐字节相同** |
| 2 | 自动压缩触发 | `MECH-claude-触发-01` | E1/E5 | **OBSERVED**（含 1 处与文档不符，见 §3） | ×3（+1 变体） | `compact_boundary` trigger=auto，pre_tokens ≈ **98.0k**（3 轮 98,014/98,202/98,015） |
| 3 | 压缩后关键约束保留（E1 判据） | `MECH-claude-摘要-01` | E1 | **OBSERVED** | ×1（方案产出）+ ×3（约束复述探针） | 3/3 轮硬约束全保留；检查器 NORM 候选 **PASS** |
| 4 | 手动 `/compact` + 磁盘原文 | `MECH-claude-摘要-02` | E4 | **OBSERVED** | ×1 | trigger=manual，preTokens 40,134 → postTokens 5,512；磁盘原文仍在 |
| 5 | 缓存命中 | `MECH-claude-缓存-01` | E5 | **OBSERVED**（部分 UNOBSERVABLE） | ×3（+1 冷启动对） | `cache_read_input_tokens` 可观测且 >0；`cache_creation.ephemeral_*` **恒为 0** → TTL 桶 UNOBSERVABLE |
| 6 | 连续三次压缩 | `MECH-claude-摘要-03` | E3 | **OBSERVED**（2 次成功 + 1 次有界拒绝） | ×1 | 40,074→4,703；4,814→2,315；第 3 次 `Not enough messages to compact.` |
| 7 | 恢复语义 | `MECH-claude-恢复-01` | E4 | **OBSERVED** | ×3（1×--continue + 2×--resume 同一会话） | **3/3** 恢复全部硬约束 + 复述标记；标记召回源自**摘要**（已核） |

> 纪律：`NOT_RUN` 与「机制不存在」不混用；HTTP 200 ≠ 推理成功（本批所有判定均核 `is_error=false` + 会话文件/事件，不靠模型自述）。

---

## 2. 条件 1 · 大工具输出（E2）— `MECH-claude-工具输出-01`

### 2.1 变量与固定量

| 项 | 值 |
|---|---|
| 唯一自变量 | 被 `cat` 的文件大小：**v2 = 161,144 B（131,099 字符，2,254 行）** vs **v1 = 22,003 B（17,190 字符，300 行）** |
| 固定量 | 工具版本 2.1.300；模型 claude-opus-5[1m]（经代理）；provider firstParty；cwd=work-claude；同一 prompt 模板；`--dangerously-skip-permissions`；`--output-format stream-json --verbose` |

### 2.2 命令模板（逐字）

```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19/work-claude
/Users/junjielong/.local/bin/claude -p --output-format stream-json --verbose \
  --dangerously-skip-permissions \
  "请用 Bash 工具运行这条命令（原样）：cat \"<样本绝对路径>\"  —— 然后回答：(1) 你实际收到的工具返回内容有多少个字符；(2) 返回内容里是否出现文件路径，如有原样列出；(3) 贴出你收到的内容第一行与最后一行。不要读取其它文件。"
```
（封装脚本：`experiments/t19/run_claude.sh`；日志名 `claude-toolout-<v>-<r>-<时间>.jsonl`）

### 2.3 预期事件（先写，后对照）

| # | 预期出现的事件 | 依据（T05 证据卡 ID） |
|---|---|---|
| 1 | v2（>30,000 字符）→ 内联被拦，模型只拿到「落盘路径 + 最多前 2,000 字符预览」 | `claude-toolout-01`（官方文档：约 30,000 字符内联上限；预览 ≤2,000 字符） |
| 2 | 落盘路径形如 `~/.claude/projects/<project>/<session>/tool-results/<name>.txt` | `claude-toolout-04` |
| 3 | v1（17,190 字符 < 30,000）→ **全量内联**，无路径 | `claude-toolout-01`（阈值以下不落盘） |
| 4 | 落盘文件为**全量**（无 64 MiB 截断，因文件远小于上限） | `claude-toolout-01` |

### 2.4 观测结果（v2 ×3 + v1 ×1）

| 轮次 | 日志 | 工具动作数 | 总耗时(ms) | 工具返回形态 | 预览体字符数 | 落盘路径 | 任务通过? |
|---|---|---|---|---|---|---|---|
| v2-r1 | `claude-toolout-v2-r1-20261015-135715` | 1 | 21,967 | **PERSISTED** `Output too large (157.4KB)` | **1,991** | `…/9ff144bb-…/tool-results/ba3qoav93.txt` | ✅ 收到预览+路径 |
| v2-r2 | `claude-toolout-v2-r2-20261015-140025` | 3 | 48,736 | **PERSISTED** `157.4KB` | **1,994** | `…/1af575af-…/tool-results/b8f4qkzyc.txt` | ✅ |
| v2-r3 | `claude-toolout-v2-r3-20261015-140115` | 2 | 32,052 | **PERSISTED** `157.4KB` | **1,994** | `…/454d0c89-…/tool-results/b0n2bc179.txt` | ✅ |
| v1-r1 | `claude-toolout-v1-r1-20261015-140148` | 3 | 36,351 | **INLINE 全量** | — | 无 | ✅ 收到全文 17,189 字符 |
| 中位数 / 范围 | — | 2.5 / 1–3 | 36,351 / 21,967–48,736 | — | 1,994 / 1,991–1,994 | — | — |

**返回包装体（逐字，v2）**：
```text
<persisted-output>
Output too large (157.4KB). Full output saved to: /Users/junjielong/.claude/projects/-Users-junjielong-workspace-agent-context-research-experiments-t19-work-claude/<session-id>/tool-results/<random>.txt

Preview (first 2KB):
<文件前 2048 字节>
...
</persisted-output>
```
- 包装体总长 **2,283 字符**（固定）；预览体 **1,991–1,994 字符**（≈2048 字节，多字节中文按字节计 2KB）。
- **中段关键事实未存活**：预览**不含** `L7-141`（v2 第 1341 行 / 班次号 L7-141）、`15:20`、`结论注释` → 中/尾关键事实**不进上下文**，只能经落盘路径回读（符合 E2「头中尾」设计）。

**磁盘落盘核验（v2-r1）**：
```
落盘文件：…/tool-results/ba3qoav93.txt
字节数：161,144  ← 与源文件相同
sha256：1c9309e718e1a8823f3f6b1e42c13e297642b2880959aaa41238dd84ccf2011b  ← 与源文件完全相同
```
→ **全量落盘**（无 64 MiB 截断），且**落盘 ≠ 进请求**（进请求只有预览+路径）。

### 2.5 用量（usage，分列，不重复相加）

| 轮次 | input_tokens | output_tokens | cache_read | cache_creation | 备注 |
|---|---|---|---|---|---|
| v2-r1 | 21,710 | 1,691 | 20,096 | 0 | 末轮 result usage |
| v2-r2 | 6,634 | 5,407 | 84,736 | 0 | 模型额外跑了 2 条自测命令（同文件边界测量） |
| v2-r3 | 3,836 | 4,229 | 62,080 | 0 | 模型额外跑了 1 条自测命令 |
| v1-r1 | 28,823 | 4,456 | 88,320 | 0 | 模型额外跑了 2 条自测命令 |

> usage 为「末轮 result」口径；多轮会话的 cache_read 为累计读。费用：**不可核验（本地代理）**；`total_cost_usd` 按 list 价给出（v2-r1=0.1003…，冷启动=0.0105…），**不作为真实计费**。

### 2.6 可归因性 / 归因限制

| 项 | 内容 |
|---|---|
| 能把差异归因于该机制吗 | **能**（阈值行为确定）：同一 prompt/模型/cwd 下，仅改文件大小（17,190 vs 131,099 字符）即切换「全量内联 ↔ 持久化+预览」，3 轮 v2 结果一致 |
| 归因限制 | ① 经本地代理 + 重映射模型（`claude-opus-5[1m]` 名义 / 实际可能 deepseek-v4.1-flash）→ **阈值行为可能由 CLI 客户端决定（与后端模型无关），但仍受代理包装影响，不可外推到直连**；② 只测 2 档大小，未测 20k/40k/80MiB 档；③「30,000 字符」阈值本身未逐点逼近，只验证了「17,190 内联 / 131,099 持久化」 |
| 状态 | **OBSERVED** |

---

## 3. 条件 2 · 自动压缩触发（E1/E5）— `MECH-claude-触发-01`

### 3.1 变量与固定量

| 项 | 值 |
|---|---|
| 唯一自变量 | 上下文填充量（4 条 user 消息：任务+约束 → 131,099 字符填充 → 软约束 → 探针） |
| 固定量 | 工具 2.1.300；模型 claude-opus-5[1m]；`--autocompact 100k`；`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50`；`--input-format stream-json`（**带节奏流式输入**，每条间隔 18s）；cwd=work-claude |

### 3.2 命令模板（逐字）

```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19/work-claude
CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50 python3 experiments/t19/feed_paced.py /tmp/t19_autocompact_in.jsonl 18 \
 | CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50 /Users/junjielong/.local/bin/claude -p \
     --input-format stream-json --output-format stream-json --verbose \
     --autocompact 100k --dangerously-skip-permissions
```
输入构造器：`experiments/t19/mk_autocompact_input.py`（任务+HC-01/02/03+REJ-01/02/03 → v2 全量填充 → SP-02 → 探针）。

### 3.3 预期事件（先写，后对照）

| # | 预期出现的事件 | 依据（T05 证据卡 ID） |
|---|---|---|
| 1 | 出现 `compact_boundary` 事件（`trigger: auto`） | `claude-trigger-04` |
| 2 | `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50` 使触发点**提前**（约 50% 窗口 ≈ 50k） | `claude-trigger-02`（"设 50 更早压缩"） |
| 3 | 压缩后对话层缓存失效、system prompt 层通常复用 | `claude-cache-04` |
| 4 | 压缩后关键硬约束保留、已否决项不复活 | `claude-compact-06`（"What survives compaction"） |

### 3.4 观测结果（3 轮 + 1 变体）

| 轮次 | 日志 | compact_boundary | trigger | pre_tokens | post_tokens | cumulative_dropped | 压缩耗时(ms) | 压缩后探针答案 |
|---|---|---|---|---|---|---|---|---|
| r1b | `claude-autocompact-r1b-20261015-140601` | 1 | auto | **98,014** | 3,583 | 94,431 | 28,219 | HC-01/02/03 全列出 |
| r2 | `claude-autocompact-r2-20261015-141001` | 1 | auto | **98,202** | 2,088 | 96,114 | 26,812 | HC-01/02/03 全列出 |
| r3 | `claude-autocompact-r3-20261015-141110` | 1 | auto | **98,015** | 2,162 | 95,853 | 27,824 | HC-01/02/03 全列出 |
| 中位数 / 范围 | — | — | — | **98,015 / 98,014–98,202** | 2,162 / 2,088–3,583 | — | 27,824 / 26,812–28,219 | — |
| **变体 pct=1** | `claude-autocompact-variant-pct1-20261015-141221` | **2（重复压缩）** | auto ×2 | 98,044 → **21,219** | 3,139 → 2,257 | 94,905 → 113,867 | 28,080 / 27,443 | 列出 HC-01/02/03 + SP-02 |

**关键读数与预期不符（如实登记）**：
1. **触发点 ≈ 98k，而非 PCT_OVERRIDE=50 预期的 50k**。3 轮独立复现（98,014 / 98,202 / 98,015）→ 触发点稳定在 `--autocompact 100k` 窗口的 **约 98%**。`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50` **未**使触发提前。
2. 变体 `PCT_OVERRIDE=1`：**第 1 次压缩仍发生在 98,044**，随后在 **21,219** 又触发第 2 次压缩（累计丢弃 113,867）。→ override 疑似**只在首次压缩之后的回合生效**（或存在其它门控），**机制原因 UNOBSERVABLE**（客户端闭源 + 经代理）。
3. `compact_boundary` 字段名：**stream-json stdout 用 snake_case**（`compact_metadata` / `pre_tokens` / `post_tokens` / `cumulative_dropped_tokens` / `duration_ms` / `preserved_segment`），**磁盘 transcript 用 camelCase**（`compactMetadata` / `preTokens` / …，见 §4.5）。官方 `claude-trigger-04` 示例给的是 camelCase → **两个面口径不同**，引用时须注明取自哪一面。

**压缩后用量（探针轮）**：r1b `in=56, cache_read=21,888`；r2 `in=130, cr=20,608`；r3 `in=3,831, cr=17,408`。→ 压缩后有效上下文 ≈ **21–25k tokens**（system ~20k + 摘要 ~2–4k），较压缩前 98k 显著下降。

### 3.5 E1 判据：压缩后关键约束保留（检查器原始输出）

**压缩后探针**（逐字）：
- r1b：`HC-01：必须在下午 4 点（16:00）前返校 / HC-02：总费用不超过 6000 元 / HC-03：出行人数 64 人`
- r2：`HC-01：必须在 16:00 前返校 / HC-02：总费用不超过 6000 元 / HC-03：出行人数 64 人（60 名学生 + 4 名老师）`
- r3：`HC-01：必须在下午 4 点（16:00）前返校 / HC-02：总费用不超过 6000 元 / HC-03：出行人数 64 人`
→ **3/3 轮硬约束全保留**，均**未**复活 REJ-01/02/03。

**E1 方案产出运行**（`claude-e1-autocompact-20261015-141719`，压缩 trigger=auto，pre_tokens 98,151 → post_tokens 3,134；模型在压缩后**自行用 Bash 回读文件**产出方案 JSON）：

候选 JSON = 模型输出**逐字**转存 → `candidates/cand-claude-e1-raw.json`（**结构化由人完成**：仅转存模型原文，未改动字段）。

```text
=== T03-DATA-TRIP-v1 | 候选：cand-claude-e1-raw.json | overall=FAIL ===
  [PASS] CHK-HC-01      returnTime=15:45 vs 上限 16:00（945 vs 960 分钟）
  [FAIL] CHK-HC-02      求和 14800  vs 上限 6000
         └ 判据：costBreakdown 各分项求和须 ≤ 6000；只比总和，不比单项（severity=硬约束违反）
  [PASS] CHK-HC-03      headcount=64 应等于 64
  [PASS] CHK-SP-02      assemblyPointId='SP-02' 不得属于被否集合 [...]
  [PASS] CHK-REJ-STRUCT selectedOptionIds=['L7-141', 'BUS-55', 'BUS-33'] 命中被否项 []
  [PASS] CHK-REJ-TEXT   命中且无否定语境：[]
  [PASS] CHK-FC-STATUS  与真值不一致项：[]
  命中问题类别：['硬约束违反']
```

`CHK-HC-02` FAIL 的**原因已定位**：模型把 `costBreakdown` 写成含**元数据字段**的结构（`车费:1400` + 嵌套 `车费明细:{900,500}` + `已确认合计:1400` + `预算上限:6000` + `剩余可用额度:4600`），而检查器 `sum_numbers()` **递归求和 costBreakdown 内所有数字** → 1,400+900+500+1,400+6,000+4,600 = **14,800**。这是**「候选结构化不符合 candidateSchema」**导致的失败，**不是**模型违反了预算约束。

**按 `预期结果.json#candidateSchema` 归一后**（`costBreakdown` 仅保留分项金额：车费 1400；门票/讲解 null；**归一动作由人完成并如实标注**）→ `cand-claude-e1-norm.json`：

```text
=== T03-DATA-TRIP-v1 | 候选：cand-claude-e1-norm.json | overall=PASS ===
  [PASS] CHK-HC-01      returnTime=15:45 vs 上限 16:00（945 vs 960 分钟）
  [PASS] CHK-HC-02      求和 1400  vs 上限 6000
  [PASS] CHK-HC-03      headcount=64 应等于 64
  [PASS] CHK-SP-02      assemblyPointId='SP-02' 不得属于被否集合 [...]
  [PASS] CHK-REJ-STRUCT selectedOptionIds=['L7-141', 'BUS-55', 'BUS-33'] 命中被否项 []
  [PASS] CHK-REJ-TEXT   命中且无否定语境：[]
  [PASS] CHK-FC-STATUS  与真值不一致项：[]
```

| 指标 | RAW | NORM |
|---|---|---|
| 任务是否通过 | FAIL | **PASS** |
| 关键约束违背数 | 1（CHK-HC-02，**结构口径**，非真实超预算） | 0 |
| 否决复活数 | 0（CHK-REJ-STRUCT / CHK-SP-02 均 PASS） | 0 |
| 未完成写完成数 | 0（CHK-FC-STATUS PASS） | 0 |

> ⚠️ **判据口径（T03R 修正轮 1）**：`CHK-REJ-TEXT` 为**启发式**，复活结论以 `CHK-REJ-STRUCT` / `CHK-SP-02` 为准。本处 notes 含 `REJ-01/REJ-02/REJ-03 维持已否决，未复活` → **已人工复核**：小句内有否决动词「否决」，判否定语境正确，无漏报误报。

### 3.6 可归因性 / 归因限制

| 项 | 内容 |
|---|---|
| 能把差异归因于该机制吗 | 触发行为**能**归因（3 轮一致、pre_tokens 稳定）；「override=50 无效」**不能**归因到具体环节（客户端/代理/模型三者之一，UNOBSERVABLE） |
| 归因限制 | ① 经本地代理 + 重映射模型；② 触发点受模型/窗口共同决定，本批窗口为显式 `--autocompact 100k`，**默认百分比仍未知**；③ 变体 pct=1 的二次压缩机制未明；④ 候选 JSON 结构化由人完成（已知主观环节） |
| 状态 | **OBSERVED**（触发）/ **UNOBSERVABLE**（override 生效环节） |

---

## 4. 条件 3 · 手动 `/compact` + 磁盘原文（E4）— `MECH-claude-摘要-02`

### 4.1 方法

交互 TTY 路径（tmux 3.7c 驱动）：启动 `claude --dangerously-skip-permissions`（**须处理 2 个启动确认**：信任文件夹 / bypass 权限——默认高亮为 "No, exit"，误按 Enter 会退出，见 §11 失败案例）；发任务+约束+**唯一标记 `T19MARK-UNIQUE-7f3a9`**；粘贴 30KB 填充；执行 `/compact`；探针；退出后核磁盘 transcript。

### 4.2 命令事件与时间线（逐字）

```bash
tmux new-session -d -s t19c -x 200 -y 50
tmux send-keys -t t19c "cd /Users/junjielong/workspace/agent-context-research/experiments/t19/work-claude" C-m
tmux send-keys -t t19c "claude --dangerously-skip-permissions" C-m
# （信任文件夹 / bypass 确认：Down + Enter）
tmux paste-buffer -b m1 -t t19c        # 任务 + HC-01/02/03 + REJ-01/02/03 + 唯一标记
tmux paste-buffer -b fill -t t19c      # head -c 30000 长工具结果-公交查询-v2.txt
tmux send-keys -t t19c "/compact" ; tmux send-keys -t t19c C-m
tmux paste-buffer -b probe -t t19c     # "现在请回答：当前有效的硬约束有哪些？"
```

| 时刻 | 可见事件 | 原始日志位置 |
|---|---|---|
| 14:25:2x | 启动，出现信任/权限确认 → 选 Yes | `claude-manualcompact-pane-20261015-142522.txt` |
| 14:25:39 | msg1 → `⏺ 收到` | 同上 |
| 14:26–14:27 | 粘贴 30KB 填充 → 模型分析（含回读文件） | 同上 |
| 14:28:06 | 输入 `/compact`（自动补全显示 "Free up context by summarizing the conversation so far"） | 同上 |
| 14:28:2x | `✶ Compacting conversation… (7s · ↓ 863 tokens)` | 同上 |
| 14:29:0x | **`⎿ Compacted (ctrl+o to see full summary)`** | 同上 |
| 14:29:37 | 探针 → `⏺ HC-01：必须 16:00 前返校 / HC-02：总费用不超过 6000 元 / HC-03：人数 64` | `claude-manualcompact-finalpane-20261015-142956.txt` |
| 14:29:56 | `/exit` → `Resume this session with: claude --resume 01b4a432-…` | 同上 |

> 面板文字实测为 **`Compacted (ctrl+o to see full summary)`**；`claude-compact-02` 描述的 `"Conversation compacted"` + `preCompactTotal → totalTokens · freed …` 面板**未在 TUI 出现**——后者文本在**磁盘 transcript** 里（`content: "Conversation compacted"`，见 §4.5）。**文档面板文字与实际 TUI 文字不完全一致**。

### 4.3 预期事件（先写，后对照）

| # | 预期出现的事件 | 依据（T05 证据卡 ID） |
|---|---|---|
| 1 | `/compact` 用结构化摘要替换"截至目前"的整个对话；显示 "Conversation compacted" 与前后 token | `claude-compact-02` |
| 2 | **压缩不改变磁盘文件**；原始消息留在 transcript | `claude-resume-05`（核心一级证据） |
| 3 | transcript 落盘于原生 `~/.claude/projects/<project>/<session>.jsonl` | `claude-resume-01` |

### 4.4 磁盘 transcript 全文核验（**逐条命中**）

会话文件：`~/.claude/projects/-Users-junjielong-workspace-agent-context-research-experiments-t19-work-claude/01b4a432-288d-4172-9361-7e816dde12b7.jsonl`（599,648 B / 176 行）

| 关键串 | 磁盘命中 | 说明 |
|---|---|---|
| `T19MARK-UNIQUE-7f3a9`（唯一标记） | **6 行** | 原始 msg1 仍在（含第 4 行原始消息 + 摘要引用） |
| `S1-001`（填充内容） | 1 行 | 填充原文仍在磁盘 |
| `HC-01` | 12 行 | 硬约束原文仍在 |
| `REJ-02` | 9 行 | 已否决项原文仍在 |

→ **压缩不删磁盘原文**（`claude-resume-05` 由真实运行**升级为「文档+本地实测」**）。

### 4.5 压缩事件（磁盘 transcript 逐字）

```json
{"parentUuid": null, "logicalParentUuid": "52a7ca6d-…", "isSidechain": false,
 "type": "system", "subtype": "compact_boundary",
 "content": "Conversation compacted", "level": "info",
 "compactMetadata": {"trigger": "manual", "preTokens": 40134, "postTokens": 5512,
   "cumulativeDroppedTokens": 34622, "durationMs": 42909,
   "preservedSegment": {"headUuid": "bdfec0ce-…", "anchorUuid": "ef10302d-…", "tailUuid": "52a7ca6d-…"}}}
```
- `trigger=manual`、`preTokens=40,134`、`postTokens=5,512`、`cumulativeDroppedTokens=34,622`、`durationMs=42,909`。
- 压缩摘要作为**一条 `isCompactSummary: true` 的 user 消息**写入（第 110 行，15,669 字符），**摘要内逐字引用了原始 msg1（含唯一标记）**。

### 4.6 可归因性 / 归因限制

| 项 | 内容 |
|---|---|
| 能把差异归因于该机制吗 | **能**：压缩后「请求侧只剩摘要、磁盘侧全文仍在」两事实并存，且摘要落盘格式可核 |
| 归因限制 | ① 经本地代理 + 重映射模型（摘要由模型生成，质量受模型影响）；② 单次运行；③ `preCompactTotal → totalTokens` 面板文字未在 TUI 复现（UNOBSERVABLE，见 §4.2） |
| 状态 | **OBSERVED** |

---

## 5. 条件 4 · 缓存（E5）— `MECH-claude-缓存-01`

### 5.1 命令（逐字）

```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19/work-claude
/Users/junjielong/.local/bin/claude -p "T19 缓存对照实验：请只回复 ok" --output-format json   # 同前缀连续 2 次 × 3 轮
# 冷启动对照：cwd=/tmp/t19-claude-cold（全新目录，同前缀首次）
```

### 5.2 预期事件 / 观测结果

预期（`claude-cache-02`）：第二次命中 `cache_read_input_tokens > 0`；`cache_creation.ephemeral_1h/5m_input_tokens` 可读。

| 轮次 | 调用 | input | output | **cache_read** | cache_creation | ephemeral_5m | ephemeral_1h |
|---|---|---|---|---|---|---|---|
| 热 r1c1 | 1 | 94 | 2 | **19,968** | 0 | 0 | 0 |
| 热 r1c2 | 2 | 222 | 2 | **19,840** | 0 | 0 | 0 |
| 热 r2c1 | 1 | 94 | 2 | **19,968** | 0 | 0 | 0 |
| 热 r2c2 | 2 | 94 | 2 | **19,968** | 0 | 0 | 0 |
| 热 r3c1 | 1 | 222 | 2 | **19,840** | 0 | 0 | 0 |
| 热 r3c2 | 2 | 222 | 2 | **19,840** | 0 | 0 | 0 |
| **冷 c1** | 1 | **20,055** | 2 | **0** | 0 | 0 | 0 |
| **冷 c2** | 2 | 87 | 2 | **19,968** | 0 | 0 | 0 |

- **命中可观测**：同前缀第二次 `cache_read` 由 0 → ≈19,968（冷启动对最清晰）。→ `claude-cache-02`「验证入口」由「字段可见」升级为「**命中实测可见**」。
- **`cache_creation` 恒为 0**（含冷启动首调）：`ephemeral_5m/1h` 两个分档键**存在但始终为 0** → **TTL 桶（1h vs 5m）在本代理条件下 UNOBSERVABLE**。原因候选：代理转发剥离/改写 cache_creation 计费，或重映射后端不回报该字段——**不可判定**。
- 模型自报 `claude-opus-5[1m]`；费用 **不可核验（本地代理）**（`total_cost_usd` 0.0105–0.0111，按 list 价）。

### 5.3 归因限制

- ① 经本地代理 → **`cache_creation` 不可观测**，TTL 与请求桶无法确认；② `cache_read > 0` 只能证明「客户端/服务端计数侧命中」，**不能证明 KV 张量实现或断点位置**；③ 缓存作用域「一台机器 + 一个目录」；本批未跨目录测前缀失效。
- 状态：**OBSERVED（cache_read）/ UNOBSERVABLE（cache_creation TTL 桶）**。

---

## 6. 条件 5 · 连续三次压缩（E3）— `MECH-claude-摘要-03`

### 6.1 方法（tmux 交互路径，逐字）

```bash
# 承接 §4 同款 tmux 驱动；会话 ad908263-220b-4152-9d18-c5f36704852b
tmux send-keys -t t19e3 "/compact" ; tmux send-keys -t t19e3 C-m   # 连续 3 次
# 探针：(a) 当前有效硬约束 (b) 已否决项 (c) 是否记得唯一标记
```
（脚本 `experiments/t19/tmux_e3.sh`；面板日志 `claude-e3-pane-20261015-143112.txt`）

### 6.2 预期事件（先写，后对照）

| # | 预期出现的事件 | 依据（T05 证据卡 ID） |
|---|---|---|
| 1 | 连续 3 次 `/compact`，每次生成结构化摘要替换历史 | `claude-compact-02` |
| 2 | 摘要可能"漂移"：过期决策复活 / 未完成写成完成 | `claude-compact-05`、T03 E3 |
| 3 | 压缩不改磁盘原文 | `claude-resume-05` |

### 6.3 观测结果

| 次数 | 面板文字 | transcript compactMetadata（trigger/pre→post/dropped/durMs） | 摘要消息 |
|---|---|---|---|
| #1 | `⎿ Compacted (ctrl+o to see full summary)` | manual / **40,074 → 4,703** / 35,371 / 39,810 | line55，9,110 字符，**含** 标记 + HC-01 + REJ-03 |
| #2 | `⎿ Compacted (ctrl+o to see full summary)` | manual / **4,814 → 2,315** / 37,870 / 25,737 | line70，6,244 字符，**含** 标记 + HC-01 + REJ-03 |
| #3 | **`⎿ Not enough messages to compact.`** | **无事件（被拒）** | — |

- **第 3 次被拒**：连续两次压缩后会话过短 → CLI 返回 `Not enough messages to compact.`（**无 compact_boundary**）。→ 「连续三次压缩」在本路径下**只能完成 2 次**，第 3 次是**有界拒绝**（非无界循环、非 thrashing）。
- **无关键项漂移**：两次摘要（9,110 → 6,244 字符，**变短**）均**保留**唯一标记、HC-01、REJ-03；未出现「过期决策复活」或「未完成写成完成」。
- **压缩后探针（第 3 次被拒之后）**：`HC-01：必须 16:00 前返校 / HC-02：总费用不超过 6000 元 / HC-03：人数 64`；`REJ-01：17:30 返程 / REJ-02：校门口集合 / REJ-03：科技馆首选`；`唯一标记：T19MARK-E3-9c1d2 —— 记得`。→ **约束、已否决项、标记全保留**。
- **磁盘原文仍在**：`S1-001`（填充）命中 3 行（含 `api-request-blob` 行 33）；`T19MARK-E3-9c1d2` 11 行；`HC-01` 11 行；`REJ-01/02/03` 分别 11/9/9 行 → 2 次压缩后原文仍在磁盘。

> 附带观察：压缩前模型在分析 30KB 填充时**主动指出输入不完整**（只看到 S1–S6 接驳线与部分 L7），并**拒绝编造时间表**（"此时排出任何时间表都是我编的"）——属模型行为，非机制结论，仅记录。

### 6.4 归因限制

- 经本地代理 + 重映射模型；单次运行；「第三次被拒」是**内容量**门槛，不代表机制上限（未测更长会话）。
- 状态：**OBSERVED**（2 次成功压缩 + 1 次有界拒绝）。

---

## 7. 条件 6 · 恢复语义（E4）— `MECH-claude-恢复-01`

### 7.1 命令（逐字）

```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19/work-claude
# r1：恢复入场（承接 §4 手动压缩会话 01b4a432-…）
/Users/junjielong/.local/bin/claude -p --continue --output-format stream-json --verbose --dangerously-skip-permissions \
  "现在请回答：当前有效的硬约束有哪些？只列硬约束（编号：内容）。另外请说明你是否记得唯一标记。"
# r2 / r3：补跑（同一会话，同一 prompt）
/Users/junjielong/.local/bin/claude -p --resume 01b4a432-288d-4172-9361-7e816dde12b7 \
  --output-format stream-json --verbose --dangerously-skip-permissions \
  "现在请回答：当前有效的硬约束有哪些？只列硬约束（编号：内容）。另外请说明你是否记得唯一标记。"
# 补充行（异 prompt，不计入 3 轮）
/Users/junjielong/.local/bin/claude -p --resume 01b4a432-288d-4172-9361-7e816dde12b7 \
  --output-format stream-json --verbose --dangerously-skip-permissions \
  "请用一句话说明：本次恢复后你能看到的上下文里，HC-01 是什么？"
```

### 7.2 观测结果（**3 轮**；同一会话 01b4a432，压缩后状态）

**同型说明（取样方式）**：首轮（r1）用 `--continue`（当时 cwd 内最近会话即 01b4a432）；补跑的 r2/r3 用 `--resume 01b4a432-288d-4172-9361-7e816dde12b7`（因 r1 之后 cwd 内最近会话已变为 E3 会话，`--continue` 不再指向 01b4a432）。→ **入口混用（1×`--continue` + 2×`--resume` 同一会话），分列如下**。三轮使用**同一探针 prompt**（问约束 + 问标记）。

| 轮次 | 入口 | 首答是否含 HC-01/02/03 | 标记是否复述 | 模型回答（逐字摘要） | input | cache_read | 恢复后上下文 ≈ |
|---|---|---|---|---|---|---|---|
| r1 | `--continue` | **是（3/3）** | **是** `T19MARK-UNIQUE-7f3a9` | `HC-01：必须 16:00 前返校 / HC-02：总费用不超过 6000 元 / HC-03：人数 64`；并注明「REJ-01/02/03 属于已否决项，不算硬约束」 | 23,849 | 2,944 | ≈26.8k |
| r2 | `--resume <id>` | **是（3/3）** | **是** | `HC-01：必须 16:00 前返校 / HC-02：总费用不超过 6000 元 / HC-03：人数 64`；`唯一标记：记得，T19MARK-UNIQUE-7f3a9`；附注「这是同一个问题第 4 次，答案未变」 | 197 | 27,008 | ≈27.2k |
| r3 | `--resume <id>` | **是（3/3）** | **是** | `HC-01：必须 16:00 前返校 / HC-02：总费用不超过 6000 元 / HC-03：人数 64`；`唯一标记：记得，T19MARK-UNIQUE-7f3a9` | 188 | 27,136 | ≈27.3k |
| 中位数 / 范围 | — | 3/3 一致 | 3/3 一致 | — | 197 / 188–23,849 | **27,008 / 2,944–27,136** | ≈27.1k / 26.8–27.3k |

> **一致性**：**3/3 轮**均恢复全部硬约束、均复述唯一标记、均**未**复活已否决项。r1 的 `cache_read` 明显低于 r2/r3（2,944 vs ≈27k）——r1 为压缩后首次恢复（缓存较冷），r2/r3 前缀已暖。

**补充行（不同 prompt，不计入 3 轮）**：`--resume <id>` + 一问式 prompt（"HC-01 是什么"）→ `HC-01：必须 16:00 前返校。`，input 182 / cache_read 26,752 / ≈26.9k。与上表同会话、异 prompt。

- **是否先重述有效约束**：三轮**均未在未被问及前主动重述**；约束是在探针**明确提问**后才列出（探针本身即问约束，故「主动重述」未被独立测试，仅记录「首答含 HC-01/02/03 = 是」）。
- **标记召回的来源已核实（3 轮共用同一压缩摘要）**：磁盘 transcript 第 110 行 `isCompactSummary: true` 的摘要消息（15,669 字符）**逐字引用原始 msg1（含 `T19MARK-UNIQUE-7f3a9`、HC-01/02/03）** → 标记来自**摘要**，**不是**原始消息重新进入请求。→ 支持「压缩后请求侧只剩摘要」。

- **恢复了什么**：有效硬约束（HC-01/02/03）、已否决项的正确**区分**（模型主动说明 REJ-* 不算硬约束）；唯一标记也能复述。
- **丢了什么**：原始填充长文（`S1-001` 等）不在请求侧（仅在磁盘）；模型未见召回中段班次原文。

### 7.3 附加发现（请求侧可观测面）

原生 transcript 含 **`api-request-blob`** 记录类型（本会话 14 条），字段 = `{type, sessionId, hash, message}`；可用于核对「某次请求里装了什么」。本批**未深挖**（登记为后续可观测入口）。

### 7.4 归因限制

- 经本地代理 + 重映射模型；3 轮为**同一会话的重复恢复**（非 3 个独立会话），且入口混用（1×`--continue` + 2×`--resume`）；`--continue` 语义（"most recent conversation in cwd"）依赖 cwd 未被其它会话插入（本批已因 E3 会话插入而改走 `--resume`）。
- 「主动重述」未独立测试（探针本身即问约束）。
- 状态：**OBSERVED**（3/3 一致）。

---

## 8. 不可观测项登记

| 想看但看不到的东西 | 为什么看不到 | 影响哪条结论 |
|---|---|---|
| 服务端 KV 缓存实现 / 断点位置 | 服务端闭源；客户端只给计数 | `claude-cache-01`（本批只证计数侧命中） |
| 缓存 TTL 桶（1h vs 5m） | 经本地代理，`cache_creation.ephemeral_*` 恒 0 | `claude-cache-02` 的 TTL 分档（**UNOBSERVABLE**） |
| `PCT_OVERRIDE=50` 未生效的**环节** | 客户端闭源 + 经代理，无法区分客户端/代理/模型 | `claude-trigger-02`（触发口径方向成立，数值未复现） |
| 摘要 prompt 具体文本 | 未暴露 | `claude-compact-02` |
| 默认 auto-compact 百分比 | 本批用显式 `--autocompact 100k`，未测默认 | `claude-trigger-03`（默认值仍未知） |
| `preCompactTotal → totalTokens` TUI 面板文字 | 实测 TUI 只显示 `Compacted (ctrl+o to see full summary)` | `claude-compact-02` 面板文字描述 |

---

## 9. 归因限制（总，必写）

1. **代理条件**：全部运行经 `http://127.0.0.1:15721`（cc-switch）转发，模型名全重映射（`claude-opus-5[1m]` 名义 / 后端可能 `deepseek-v4.1-flash`）→ 本批是「**CLI 机制 + 本地代理 + 重映射模型**」组合，**不可外推为直连 Anthropic 的行为**。
2. **版本**：执行 2.1.300 ≠ 研究快照 2.1.299（本地领先 1 patch）。
3. **污染**：本机受 Paseo + teamai 双套 hooks 污染，且 6 个本地技能在场；所有观测**均在受污染本机**完成，不代表纯净默认环境。
4. **结构化主观环节**：候选 JSON 由人按 candidateSchema 转写（RAW 逐字转存；NORM 归一 costBreakdown），已在 §3.5 标注。
5. **闭源**：任何「实现里怎么算」只能给「文档承诺 / 可观测行为」；本批未读、未反编译二进制。
6. **探索性小样本**：每条件 3 次，**不声称统计显著**。

---

## 10. 异常与停止（T03 §7/§8）

| 项 | 内容 |
|---|---|
| 触达停止条件 | **是（1 处）**：变体 `PCT_OVERRIDE=1` 出现**重复压缩**（同轮 2 次 compact_boundary）→ 按 T03 §7「出现重复压缩立即停止该轮」**停止该变体**，未继续追加 |
| 停止时间点 | 变体运行结束（14:13 前后），未再跑 pct=1 |
| 已产生的副作用 | 仅该轮会话文件与日志；无外部副作用；可重复 |
| 失败案例（如实登记） | ① 首次自动压缩（非节奏流式输入）4 条消息被**合并为 2 轮**，**未触发**压缩 → 改用带节奏流式输入（`feed_paced.py`）后触发；② tmux 首次驱动因信任/权限确认默认高亮 "No, exit"，误按 Enter 导致 claude **退出**、后续粘贴落到 shell → 修正为 Down+Enter 选择 Yes |
| 后续动作 | 保留全部日志；重复压缩变体不扩批；等主 Agent 决定 |

---

## 11. 未决与下一步建议

1. **`PCT_OVERRIDE` 语义**：本批实测 50 无效、1 只对第二次压缩生效。**主 Agent 裁决（2026-10-15）：定为 `UNOBSERVABLE`，不加跑对照轮**（理由：客户端闭源 + 经代理双不可控；现有 3 轮 + 1 变体足以支撑「文档口径方向未被复现」的限定表述，节省额度）。→ 已按裁决关闭该项，不再排 `pct=25` 对照。
2. **默认 auto-compact 百分比仍未知**（`claude-trigger-03`）：需在**不设窗口**、用接近默认窗口的填充量复现，代价高 → 建议标未决。
3. **`api-request-blob`** 可作为「请求侧装了什么」的可观测入口，建议后续条件（尤其缓存失效/压缩）纳入。
4. **回填建议**（**主 Agent 已批准方向**，将在 T19 汇总时统一回填）：`claude-toolout-01/02/04`（工具输出）、`claude-resume-05`（压缩不改磁盘）、`claude-cache-02`（命中入口升级）、`claude-trigger-02`（触发口径方向成立 / 数值未复现的限定）、`claude-compact-02`（面板文字须限定为「文档描述 vs TUI 实测不同」）。
5. **操作陷阱**（保留于本记录 §10）：流式输入未加节奏 → 多条 user 消息被合并为单轮、压缩不触发；tmux 启动确认默认高亮 `No, exit` → 误按 Enter 使 claude 退出。**主 Agent 将在 T19 汇总并入「操作陷阱」附录（不动冻结的 T03）**。

---

## 附：原始日志清单

见 `experiments/t19/logs/`：
- `claude-toolout-v2-r{1,2,3}-*`（+ 重跑）、`claude-toolout-v1-r1-*`（+ 重跑）
- `claude-autocompact-r1b/r2/r3-*`、`claude-autocompact-variant-pct1-*`、`claude-e1-autocompact-*`
- `claude-cache-r{1,2,3}c{1,2}-*`、`claude-cache-cold-c{1,2}-*`
- `claude-manualcompact-pane-*`、`claude-manualcompact-finalpane-*`
- `claude-e4-continue-*`、`claude-e4-resume-*`、`claude-e4-resume-r{2,3}-*`
- 脚本：`experiments/t19/{run_claude.sh,parse_stream.py,feed_paced.py,mk_autocompact_input.py,mk_e1_input.py,tmux_manual_compact.sh,tmux_e3.sh}`
- 候选：`experiments/t19/candidates/cand-claude-e1-{raw,norm}.json`

> **凭据纪律**：本记录与全部日志**不含** `ANTHROPIC_AUTH_TOKEN` 等凭据值；`settings.json` 读取时对 token 字段脱敏（仅记录存在性与长度）。

## 更新日志

| 日期 | 更新 |
|---|---|
| 2026-10-15 | 建档：§0 版本三字段+代理条件；条件 1（工具输出）、2（自动压缩）、3（手动 /compact）、4（缓存）、6（恢复）实测；E1 检查器 raw/norm；异常与未决。 |
| 2026-10-15 | 补 §6 连续三次压缩（E3）：2 次成功 + 第 3 次有界拒绝；摘要 9,110→6,244 字符无关键项漂移；磁盘原文仍在。定稿 SUBMITTED。 |
| 2026-10-15 | **主 Agent 裁决落实 + 补强**：① §11 第 1 项改为「PCT_OVERRIDE 定 UNOBSERVABLE，不加轮」；② §11 回填/操作陷阱标注主 Agent 批准与并入计划；③ §7 恢复条件**补 2 次重复**（同一会话 01b4a432，入口混用 1×`--continue` + 2×`--resume`）→ **3/3 一致**（均恢复 HC-01/02/03 + 复述标记），补中位数/范围；④ 标记来源=摘要 3 轮共用摘要已复核。 |
