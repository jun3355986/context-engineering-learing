---
title: T19 批次 1 · codex 真实机制实验记录（01-codex）
task: T19
batch: 1
tool: codex
role: 实验 Agent（t19-codex）
created: 2026-10-15
status: 批次 1 完成（四项点名 + E1/E4 已跑；部分项标 NOT_RUN/UNOBSERVABLE）
template: 05-实验/T03/运行记录模板.md
---

# T19 批次 1 · codex 真实机制实验记录

> **本文件解决什么**：给出 codex 四项点名机制（自动压缩 / 手动 `/compact` / 工具裁剪 / 缓存）+ E1/E4 的**真实运行记录**：条件、逐字命令、预期事件、3 次重复表、检查器原始输出、可归因性与限制、状态。
> **本文件不做什么**：不外推为「快照 `76ed3b4` 的默认行为」；不把「模型自述」当证据；不把 HTTP 200 当推理成功。
> **记录纪律**：MECH（机制实验，控变量）与 PROD（产品组合观察，原生差异）**分开填**；`CHK-REJ-TEXT` 为启发式，**不得单独作证**。

## 0. 统一条件与版本三字段（全批次共用）

| 字段 | 值 |
|---|---|
| 执行入口（绝对路径） | `/opt/homebrew/bin/codex`（⚠️ 另有 volta 侧 `/Users/junjielong/.volta/bin/codex` 并存；本批次**固定用 homebrew 入口**） |
| **实际执行版本** | `codex-cli 0.162.1`（开跑日实测 `codex --version`） |
| **研究快照 SHA** | `76ed3b484d62ccceb9fa512ff4dd139f421814c3`（main@2026-10-14 15:22 UTC；浅克隆无 tag） |
| 两者是否一致 | **不一致**（执行 0.162.1 vs 快照无 release 号；精确对应**不可判定**）→ 观测只作「0.162.1 行为样点」，**不得**直接验证基于快照写的结论 |
| 本机污染（G8 §2.2） | 主条件=**干净 `CODEX_HOME`**（`experiments/t19/clean-codex-home/`，仅 `auth.json`，无 plugins/notify/gmn）；对照=**污染代理 `CODEX_HOME`**（`experiments/t19/polluted-codex-home/`，仅复制 `config.toml`/`auth.json`/`hooks.json`/`AGENTS.md`，含 14 个 `[plugins.*]`、`notify`、`[model_providers.gmn]`、`[hooks.state]`；**未复制 9.1G 的 sessions/cache**） |
| 模型 / provider | `-m gpt-5.6-sol`（默认 `gpt-6.1-sol` 不被该 ChatGPT 账号支持，T04 已登记）；provider=OpenAI（ChatGPT 账号，经 `wss://chatgpt.com/backend-api/codex/responses`） |
| 生效配置与覆盖 | `-c model_context_window=16000`（自动压缩条件）/ `200000`（裁剪条件）；`-s danger-full-access`；`--skip-git-repo-check` |
| 工作目录 | `/Users/junjielong/workspace/agent-context-research/experiments/t19/work-codex/`（独立合成目录，非生产） |
| 数据版本 | 行程包 `T03-DATA-TRIP-v1`（整包哈希见 T03 `manifest.sha256`）；样本 v2 `长工具结果-公交查询-v2.txt`（2,254 行 / 161,144 字节 / sha256 `1c9309e7…011b`）、v1（300 行 / 22,003 字节 / `802b98df…c4b`） |
| 原始日志目录 | `/Users/junjielong/workspace/agent-context-research/experiments/t19/logs/`（`codex-*` 前缀） |
| 分析脚本 | `experiments/t19/analyze.py`、`extract_final.py`（只读） |

> **条件残差（必读）**：**干净 HOME 未隔离 `~/.agents/skills`**（用户级 skills 根仍被加载，会话 `skills_instructions` 的 `r0` = `/Users/junjielong/.agents/skills`，含 `defuddle/find-skills/json-canvas/obsidian-*` 等）。本批次四项机制观测**均不涉及技能路径**，故作为**条件残差登记**，**不外推为「完全无污染」**；另见 §D 与 §A-6 的 `Exceeded skills context budget` 事件。
>
> **窗口实测**：传 `-c model_context_window=16000` 后，rollout `token_count` 回报 `model_context_window=15200`（= 16000×0.95）。**按源码口径**，该字段是**整段线**（`W×95%`），不是原始 W；记录时两者并列。

## 1. 批次状态总览

| # | 机制 / 场景 | 运行 ID | 状态 | 一句话结论 |
|---|---|---|---|---|
| 0 | 入口验证 | `codex-entry-01` | OBSERVED | 干净 HOME × 0.162.1 可跑；usage 含 `cached_input_tokens` |
| 1 | 自动压缩 | `MECH-codex-autocompact-01..03` | **OBSERVED** | 到线后**自动压缩确实发生**（1 turn 内 2–3 次）；产物=远端 v2 **加密条目**；压缩后材料变短；`codex exec --json` **不暴露**压缩事件（只在 rollout） |
| 2 | 手动 `/compact` | `MECH-codex-manualcompact-01` | **OBSERVED（TUI）/ NOT_RUN（exec）** | TUI 可驱动：`/compact` → "Context compacted · 2s" + rollout `compacted`；`codex exec` 路径**不触发**压缩 |
| 3 | 工具裁剪 | `MECH-codex-trunc-01..03`（干净）+ `MECH-codex-trunc-04..06`（污染对照） | **OBSERVED** | v2 触发头尾裁剪 + 标记；v1 不裁；中段关键块丢失、可从磁盘二次检索取回；干净/污染 HOME 形态一致 |
| 4 | 缓存 | `MECH-codex-cache-01` | OBSERVED（CLI 侧）/ UNOBSERVABLE（服务端） | `cached_input_tokens>0`、`cache_write_input_tokens=0`；命中率/TTL 不可观测 |
| 5 | E1 关键约束保留 | `MECH-codex-e1-01..03` | OBSERVED | 压缩后**硬约束 3/3 全存活**；结构化无复活；文本层启发式误报（人工复核判定无复活） |
| 6 | E4 重启恢复 | `MECH-codex-e4-01..03` | OBSERVED | `codex exec resume` 恢复后**先重述有效约束**（HC-01/02/03 + REJ-01/02/03 **3/3 轮均 6/6 全对**） |
| 7 | PROD 原生 TUI 观察 | `PROD-codex-tui-compact-01` | OBSERVED | 见 §B |

---

## A. 机制实验记录（MECH · 可控变量）

### A-0 入口验证（`codex-entry-01`）

**命令（逐字）**
```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19
CODEX_HOME=/Users/junjielong/workspace/agent-context-research/experiments/t19/clean-codex-home \
/opt/homebrew/bin/codex exec --skip-git-repo-check -s danger-full-access \
  -m gpt-5.6-sol -c model_context_window=16000 \
  -C /Users/junjielong/workspace/agent-context-research/experiments/t19/work-codex \
  --json "回复一句：入口验证 OK" | tee logs/codex-entry-01-20261015-134420.log
```
**结果**：EXIT=0；事件 `thread.started/turn.started/item.completed/turn.completed`；
usage `{"input_tokens":13163,"cached_input_tokens":11264,"cache_write_input_tokens":0,"output_tokens":7,"reasoning_output_tokens":0}`。
**结论**：入口可跑、模型可用、usage 可抓（含缓存明细）。日志：`logs/codex-entry-01-20261015-134420.log`。

---

### A-1 自动压缩（`MECH-codex-autocompact-01..03`）

**唯一自变量**：会话是否被灌到触发线（用小窗口 + 让模型 `cat` 超阈值大文件）。
**固定量**：工具版本 0.162.1（绝对路径 `/opt/homebrew/bin/codex`）、模型 `gpt-5.6-sol`、provider=OpenAI(ChatGPT)、窗口覆盖 `model_context_window=16000`、数据 v2 样本、工作目录 `work-codex/`、命令模板（下）。

**命令（逐字，3 轮相同）**
```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19
CODEX_HOME=$PWD/clean-codex-home /opt/homebrew/bin/codex exec \
  --skip-git-repo-check -s danger-full-access -m gpt-5.6-sol \
  -c model_context_window=16000 -C "$PWD/work-codex" --json \
  "请用 shell 执行 cat samples/长工具结果-公交查询-v2.txt 读取全文，然后只回答两点：1) 14:50 发车几点返校？2) 15:20 发车几点返校？"
```

**A3 预期事件（先写，后对照）**

| # | 预期出现的事件 | 依据（工具研究包结论 ID） |
|---|---|---|
| 1 | 到线条件满足（A ≥ 范围线+缓冲 或 A ≥ 整段线），轮中/轮前触发压缩 | `codex-trigger-01`/`02` |
| 2 | 压缩产物 = 替代历史 + `CompactedItem` 检查点（含 `replacement_history`/window id/usage 记录/resume_metadata） | `codex-persist-01` |
| 3 | OpenAI provider 走**远端 v2** 路径（共享预算 64,000、单条 ≤10,000、重试 min(provider,2)、`compaction_count==1`） | `codex-retain-02`、`codex-provider-01`/`02` |
| 4 | 压缩后下一次请求材料变短 | `codex-trigger-01` |
| 5 | 任务硬约束（16:00 前返校）仍存活 | E1 |

**A4 观测结果（3 次重复）**

| 轮次 | 首字延迟 | 总耗时 | 输入 token | 输出 token | 摘要额外 token | 缓存读/写 | 重读次数 | 工具动作数 | 关键事件 | 任务通过? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | n/a | 44s | 40839 | 245 | 未单列（压缩请求另计） | 读 37632 / 写 0 | 1 | 2 | **compacted ×2**；答案正确 | 是 |
| 2 | n/a | 61s | 55518 | 361 | 同上 | 读 48896 / 写 0 | 2 | 3 | **compacted ×3**；答案正确 | 是 |
| 3 | n/a | 66s | 54884 | 395 | 同上 | 读 46976 / 写 0 | 2 | 3 | **compacted ×3**；1 次传输层 error（ws 重连 2/5）后成功 | 是 |
| 中位数 / 范围 | — | 中位 61s / 44–66s | 中位 54884 / 40839–55518 | 中位 361 / 245–395 | — | 读 中位 46976 / 写 0 | 1–2 | 2–3 | 压缩 2–3 次 | 3/3 通过 |

> 探索性小样本（n=3），**不声称统计显著**。

**压缩产物形态（rollout `compacted` 事件，机器可读证据）**

payload 字段：`message`(="")、`replacement_history`(6 条)、`replacement_history_metadata`(每条 `client_authored:false`)、`retained_context`(`verified_answers:[]`、`incomplete:false`、`user_messages:[…]`)、`window_number`(1→2→3)、`first_window_id`、`previous_window_id`、`window_id`、`compaction_response_id`(有值)、`latest_token_usage_record`、`resume_metadata`。

`replacement_history` 6 条 = 3 条 developer（skills 说明 / 多智能体说明 / multi_agent_mode）+ 1 条 user（`<environment_context>`）+ 1 条 user（原始提问，`retained_context.user_messages` 标记保留）+ **1 条 `type=compaction`**。该条目：
```json
{"type":"compaction","id":"cmp_…","encrypted_content":"gAAAAAB…","internal_chat_message_metadata_passthrough":{…}}
```
→ **`encrypted_content` 存在** ⇒ 与 T15 M04 口径一致：**官方 OpenAI provider 默认走远端 v2、压缩产物为服务端加密条目**（本地不可读、无明文摘要文本；`message` 为空）。

**压缩后材料变短（`token_count` 的 `last_token_usage.total_tokens`）**
- r1：13507 → **7248** →（13827）→ **7148** → 13750
- r2：13509 → **8033** →（14194）→ **8096** →（14262）→ **7460** → 13914
- r3：13507 → **7265** →（13832）→ **7580** →（14045）→ **7445** → 13895

**触发相位**：3 轮均为**轮中（MidTurn）**——每次工具输出写回后到线 → 压缩 → `continue`（rollout 条目顺序：`custom_tool_call_output` → `token_usage_record` → **compacted** → `world_state/turn_context/token_count` → 下一次请求）。符合 `codex-trigger-01` 的「轮中触发」分支。

**事件可见性（重要）**：`codex exec --json` **不输出任何压缩事件**；压缩只在 **rollout 会话存档**可见（`type:"compacted"` 事件 + `event_msg.item_completed` 的 `item.type="ContextCompaction"`）。→ 判「压缩是否发生」**必须读 rollout**，不能只看 exec 事件流。

**A5 判据结果**：本条件不直接产出候选方案 JSON（问的是班次时刻），故不走检查器；**答案正确性由人工比对 rollout 与样本**：3/3 轮回答 `14:50→15:45`、`15:20→16:15`，与 v2 样本文件第 1341/1343 行（班次 L7-141/L7-143）一致。

**A6 可归因性**

| 项 | 内容 |
|---|---|
| 能把差异归因于该机制吗 | **部分能**（「压缩是否发生/何时发生」可归因到到线触发；「压缩内容质量」不能） |
| 理由 | 触发事件、产物结构、压缩后 token 下降均为机器可读产物；但加密条目内容不可读，无法判定摘要保真度 |
| 归因限制 | ① 观测为 **0.162.1**，≠ 快照 `76ed3b4`；② 模型 `gpt-5.6-sol` 不可控；③ 阈值依赖**服务端下发的模型元数据**（非源码常量）；④ 压缩产物为**服务端加密**，内容不可核验；⑤ 干净 HOME **未隔离** `~/.agents/skills`（见 §D） |

**日志**：`logs/codex-autocompact-r{1,2,3}-*.jsonl` + `.stderr.log`；对应 rollout 在 `clean-codex-home/sessions/2026/10/15/`。

---

### A-2 手动 `/compact`（`MECH-codex-manualcompact-01`）

**变量**：压缩入口（交互 TUI 手动命令 vs 非交互 `codex exec`）。

**命令（逐字）**
```bash
# ① 交互 TUI（tmux 驱动；记录真实命令事件）
tmux new-session -d -s t19compact -x 200 -y 50 -c "$PWD/work-codex" \
  "CODEX_HOME=$PWD/clean-codex-home /opt/homebrew/bin/codex -m gpt-5.6-sol -c model_context_window=16000"
tmux send-keys -t t19compact "请回复：TUI 已就绪。" Enter   # 建立会话上下文
tmux send-keys -t t19compact "/"          # 斜杠菜单
tmux send-keys -t t19compact "compact"    # 过滤 → 命中 /compact
tmux send-keys -t t19compact C-m          # 执行
# ② 非交互路径
CODEX_HOME=$PWD/clean-codex-home /opt/homebrew/bin/codex exec resume <SID> \
  --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox \
  -m gpt-5.6-sol -c model_context_window=16000 --json "/compact"
```

**预期事件（依据 `codex-retain-02`/`codex-provider-01`/源码导读 §4.3 `tasks/compact.rs` D7/D8）**
| # | 预期 |
|---|---|
| 1 | `/compact` 是 TUI 斜杠命令；出现手动压缩事件 |
| 2 | provider=OpenAI → 走**远端 V2 任务**（分流：TokenBudget / V2→远端 / Unsupported→本地） |
| 3 | 产物与自动压缩同形（`replacement_history` + 检查点） |
| 4 | `codex exec` 非交互路径**可能不认**斜杠命令 |

**观测结果（1 次，附非交互对照 1 次）**

| 轮次 | 入口 | 耗时 | 关键事件 | 产物 | 任务通过? |
|---|---|---|---|---|---|
| 1 | TUI（tmux） | 压缩 "2s" | 斜杠菜单命中 `/compact — summarize conversation to prevent hitting the context limit`；执行后 TUI 显示 **"Context compacted · 2s"** | rollout 新增**独立 `task_started`** + `compacted`（`window_number=1`、6 条替代历史、`compaction_response_id` 有值、`compaction` 条目含 `encrypted_content`）+ `task_complete` | 是 |
| 对照 | `codex exec resume "/compact"` | — | **无压缩事件**（该 rollout `compacted` 总数仍为 1，仅 TUI 那次）；`/compact` 被当作**普通用户消息**（`agent_message`，output 20 token） | 无 | 不适用 |

**A5 判据结果**：不产出候选 JSON → 不走检查器；以 **rollout 机器可读事件**为判据（手动路径**从真实命令事件核对**，未依赖模型自述）。

**A6 可归因性**

| 项 | 内容 |
|---|---|
| 能把差异归因于该机制吗 | **能**（「TUI 手动命令会触发压缩」有真实事件；「exec 不触发」亦有反例） |
| 归因限制 | ① TUI 由 tmux 驱动，非人手交互；② 仍为 0.162.1；③ 压缩产物加密，内容不可核验；④ 窗口覆盖为 16000，与默认窗口下的行为可能不同 |

**日志**：`logs/codex-manualcompact-exec-*.jsonl`（首次因 TUI 仍占用 writer 而失败，见 §C）、`logs/codex-manualcompact-exec2-*.jsonl`；TUI rollout = `clean-codex-home/sessions/2026/10/15/rollout-2026-10-15T14-04-59-01a13e29-f5bc-7020-890c-a4b59663cb66.jsonl`。

---

### A-3 工具裁剪（`MECH-codex-trunc-01..03` 干净 + `MECH-codex-trunc-04..06` 污染对照）

**变量**：工具出口是否超限值（v2 大样本 vs v1 小样本）+ CODEX_HOME 是否受污染。
**固定量**：0.162.1 / `gpt-5.6-sol` / `-c model_context_window=200000`（大窗口以**隔离压缩变量**）/ `danger-full-access` / `codex exec`。

**命令（逐字，逐轮相同；v1 只换文件名）**
```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19
CODEX_HOME=<clean 或 polluted> /opt/homebrew/bin/codex exec \
  --skip-git-repo-check -s danger-full-access -m gpt-5.6-sol \
  -c model_context_window=200000 -C "$PWD/work-codex" --json \
  "请用 shell 执行 cat samples/长工具结果-公交查询-v2.txt 读取全文，然后回答三点：1) 14:50 发车几点返校？2) 15:20 发车几点返校？3) 头部的车程规则是什么？"
```

**预期事件（依据 `codex-trunc-01`/`02`/`03`）**
| # | 预期 |
|---|---|
| 1 | v2（161KB）超限 → 出口限长；v1（22KB）不超限 |
| 2 | 保留**头 + 尾**，中间替换为标记 `…N tokens truncated…`，正文前包说明头 `Warning: truncated output (original token count: N)` + `Total output lines: N` |
| 3 | 中间原文仍可从会话存档/磁盘原文找回 |
| 4 | 阈值来自模型元数据（`truncation_policy`），非源码常量 |

**A4 观测结果**

**（a）干净 HOME × v2（3 轮）**

| 轮次 | 耗时 | 压缩次数 | 模型可见工具输出 | 说明头 | 内联标记 | 中段关键块存活? | 任务通过? |
|---|---|---|---|---|---|---|---|
| 1 | 21s | 0 | 32,046 chars / 562 行 | `(30027)`+`(40286)` 双层 | `…20027 tokens truncated…` | **否** | 是 |
| 2 | 40s | 0 | 32,046 chars / 562 行 | `(30027)`+`(40286)` 双层 | `…20027 tokens truncated…` | **否** | 是 |
| 3 | 28s | 0 | 32,046 chars / 562 行 | `(30027)`+`(40286)` 双层 | `…20027 tokens truncated…` | **否** | 是 |
| 中位数 | 28s | 0 | 32,046 chars | 双层 | 20027 | 否 | 3/3 |

**（b）干净 HOME × v1（未截断对照，1 轮）**

| 轮次 | 耗时 | 压缩次数 | 模型可见工具输出 | 说明头 | 内联标记 | 关键事实存活? | 任务通过? |
|---|---|---|---|---|---|---|---|
| 1 | 25s | 0 | 17,237 chars / 303 行 | **无** | **无** | **全部存活** | 是 |

**（c）污染代理 HOME × v2（3 轮，污染变量单独可比）**

| 轮次 | 耗时 | 模型可见工具输出 | 说明头 | 内联标记 | 中段存活? | 任务通过? |
|---|---|---|---|---|---|---|
| 1 | 49s | 32,046 chars / 562 行 | `(30027)`+`(40286)` 双层 | `…20027 tokens truncated…` | 否 | 是 |
| 2 | 32s | 32,046 chars / 562 行 | `(30027)`+`(40286)` 双层 | `…20027 tokens truncated…` | 否 | 是 |
| 3 | 33s | 32,028 chars / 560 行 | `(40286)` **单层** | `…30286 tokens truncated…` | 否 | 是 |

**E2 专项：头/中/尾关键事实存活（双标行号，引用 v2 README §3）**

| 位置 | 文件行号 | 班次号 | 关键事实 | 模型可见输出中是否存活 |
|---|---|---|---|---|
| 头 | 5 | — | 返抵 = 发车 + 55 分钟（主线） | **存活** |
| 头 | 6 | — | 学校站 = 示例一中 | **存活** |
| 中 | 1339 | L7-139 | 14:20 发车 → 15:15 | 文本块丢失（`L7-139` 字样仅出现在尾部「审计注」） |
| 中 | **1341** | **L7-141** | **14:50 发车 → 15:45（推荐）** | **丢失**（被 `…20027 tokens truncated…` 替换） |
| 中 | **1343** | **L7-143** | **15:20 发车 → 16:15（不可用）** | **丢失** |
| 中 | 1344 | L7-144 | 15:50 发车 → 16:45 | **丢失** |
| 尾 | 2247 | — | 结论注释 1（15:20 及以后无法 16:00 前返校） | **存活** |
| 尾 | 2248 | — | 结论注释 2（可选仅 14:20/14:35/14:50） | **存活** |
| 尾 | 2250 | — | 车辆报价 900+500=1400 元 | **存活** |

**三条必须分开记（E2 核心）**
1. **出口限长是否发生、触发哪条规则**：v2 **发生**（保头尾、中间替换为标记）；v1 **未发生**。
2. **进请求的是不是只有「预览 + 路径」**：**否**——进模型请求的是「说明头 + 头段 + 标记 + 尾段」（无「路径」，全文未落盘到独立文件）。**另**：同一命令的输出在**三处不同长度**：exec `--json` 的 `aggregated_output` = **131,099 chars / 2,254 行（完整原文，无标记）**；rollout `event_msg.item_completed.aggregated_output` = **52,913 chars / 917 行（含 truncated，头尾保留）**；rollout `response_item.custom_tool_call_output`（**模型实际所见**）= **32,046 chars / 562 行**。
3. **中间那几行能否取回**：**能**——模型通过**二次 shell 检索**（`rg -n -C 12 '14:50|15:20'`、`grep -aoE`、`perl -0777`）从**磁盘原文**取回；**不需重跑原工具**；3 轮重读 1–2 次。**中间原文也在 exec `--json` 的 `aggregated_output` 中完整保留**（可离线核验）。

**人工比对结论（G3 无自动判据，必写）**：检查器只判「约束/复活/完成」三类，判不了「中间原文是否丢」。本轮**人工比对**结论：**头尾关键事实存活、中段关键块（含 HC-01 证据「15:20→16:15 不可用」）在模型首次可见输出中丢失**；模型 3/3 轮均通过二次检索补齐并给出正确答案（`14:50→15:45`、`15:20→16:15`）。→ 与 T04 `codex-trunc-03` 的「头尾保留 + 中间可找回」**同向**；差异点：本轮**中间块确证不可见于首屏**，必须二次检索。

**A5 判据结果**：本条件不产出候选方案 JSON → 不走检查器；以 **rollout 机器可读产物**为判据（`custom_tool_call_output` 文本 + 说明头 + 内联标记）。

**A6 可归因性**

| 项 | 内容 |
|---|---|
| 能把差异归因于该机制吗 | **能**（v2 裁 / v1 不裁，同一命令、同一模型、同一窗口，构成对照） |
| 归因限制 | ① 0.162.1 ≠ 快照 `76ed3b4`；② 阈值依赖服务端模型元数据（非源码常量）；③ 说明头**层数不稳定**（同一条件下出现「双层/单层」两种形态，见 §C）；④ 中文样本，`ceil(bytes/4)` 估算式的普适性不证；⑤ 干净 HOME **未隔离** `~/.agents/skills` |

**日志**：`logs/codex-trunc-v2{a,b,c}-*.jsonl`、`logs/codex-trunc-v1ctl-*.jsonl`、`logs/codex-trunc-polluted-r{1,2,3}-*.jsonl`。

---

### A-4 缓存（`MECH-codex-cache-01`）

**变量**：请求前缀是否复用（新会话 vs 同会话续跑 vs 另一新会话同 prompt）。
**固定量**：0.162.1 / `gpt-5.6-sol` / `model_context_window=16000` / clean HOME / `work-codex/`。

**命令（逐字）**
```bash
# A：新会话
CODEX_HOME=$PWD/clean-codex-home /opt/homebrew/bin/codex exec --skip-git-repo-check \
  -s danger-full-access -m gpt-5.6-sol -c model_context_window=16000 -C "$PWD/work-codex" \
  --json "缓存对照测试：请只回复一句话：收到。"
# B：同会话续跑（同一 session_id → 同一 prompt_cache_key）
CODEX_HOME=$PWD/clean-codex-home /opt/homebrew/bin/codex exec resume <A_SID> \
  --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox -m gpt-5.6-sol \
  -c model_context_window=16000 --json "缓存对照测试：请只回复一句话：收到。 再回复一句：好的。"
# C：另一新会话，同 prompt
CODEX_HOME=$PWD/clean-codex-home /opt/homebrew/bin/codex exec ... --json "缓存对照测试：请只回复一句话：收到。"
```

**预期事件（依据 `codex-cache-01`）**
| # | 预期 |
|---|---|
| 1 | 请求携带 `prompt_cache_key`（默认 = `session_id`） |
| 2 | 响应 usage 解析出 `cached_input_tokens` / `cache_write_input_tokens` |
| 3 | 服务端命中率 / TTL **不可由本地观测** |

**观测结果**

| 运行 | session | input_tokens | cached_input_tokens | cache_write_input_tokens | output_tokens |
|---|---|---|---|---|---|
| A（新会话） | `01a13e28-…0a4c` | 13364 | **11264** | **0** | 6 |
| B（同会话续跑） | 同上 | 26883 | **22528** | **0** | 14 |
| C（另一新会话，同 prompt） | `01a13e29-…d74e` | 13364 | **11264** | **0** | 6 |

**A5 判据结果**：不走检查器（无候选方案）。
**结论（有范围）**：CLI 侧可证——**发了缓存键、也认了缓存明细**（`cached_input_tokens>0`）；`cache_write_input_tokens` 恒为 **0**（OpenAI 自动前缀缓存不计写入）。A 与 C（两个**不同**会话、同 prompt）cached 完全相同（11264），说明**系统/基础前缀被服务端自动缓存**，与 `session_id` 无关；B（同会话）cached 升至 22528。
**不可观测**：命中率、TTL、显式断点、真实计费口径 → `UNOBSERVABLE`。
**费用**：ChatGPT 订阅账号**无可核验单价** → 记「**不可核验费用（订阅）**」+ 用量字段；不编造金额。

**归因限制**：0.162.1；服务端缓存策略闭源、会随时间/账号变化；B 轮出现 1 次传输层 error（ws 重连）但最终成功。

**日志**：`logs/codex-cache-{A,B,C}-*.jsonl`。

---

### A-5 E1 关键约束保留（`MECH-codex-e1-01..03`，随自动压缩携带）

**设计（有界版）**：小窗口（16000）+ 读 v1（22KB，**不触发出口截断**）→ 制造**恰好 1 次**压缩；要求模型输出候选 JSON。
**命令（逐字）**
```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19
CODEX_HOME=$PWD/clean-codex-home /opt/homebrew/bin/codex exec \
  --skip-git-repo-check -s danger-full-access -m gpt-5.6-sol \
  -c model_context_window=16000 -C "$PWD/work-codex" --json \
  "$(cat "$PWD/work-codex/e1-prompt-bounded.txt")"
```
（prompt 内含 HC-01/02/03、REJ-01/02/03、集合点操场、地点植物园、报价，并要求先 `cat samples/长工具结果-公交查询-v1.txt` 再输出候选 JSON。）

**预期事件**：压缩发生 ≥1 次；压缩后硬约束与已否决项仍存活；输出候选 JSON 可被检查器判定。

**A4 观测结果（3 次重复）**

| 轮次 | 耗时 | 压缩次数 | 工具动作数 | input | cached | write | output | 任务通过? |
|---|---|---|---|---|---|---|---|---|
| 1 | 39s | **1** | 1 | 27990 | 22528 | 0 | 306 | 硬约束 3/3 通过 |
| 2 | 39s | **1** | 1 | 28148 | 24832 | 0 | 315 | 硬约束 3/3 通过 |
| 3 | 40s | **1** | 1 | 28064 | 22528 | 0 | 273 | 硬约束 3/3 通过 |
| 中位数 / 范围 | 39s / 39–40s | 1 | 1 | 28064 / 27990–28148 | 22528 / 22528–24832 | 0 | 306 / 273–315 | 3/3 |

**候选 JSON 摘要（逐轮）**
- r1：`returnTime="14:50"`（⚠️ 模型填了**发车**时间而非返校时间）、`costBreakdown{1400,0,200}`、`headcount=64`、`assemblyPointId="LOC-PLAYGROUND"`、`selectedOptionIds=[BUS-55,BUS-33,L7-141]`、`statusClaims{未预订,未报备,false}`
- r2：同 r1 结构；`returnTime="14:50"`；`statusClaims{待预订,待报备,false}`
- r3：`returnTime="15:45"`（正确）；`statusClaims{未预订（仅取得报价）,未报备,false}`

**A5 判据结果（检查器原始输出，3 轮）**
```text
=== T03-DATA-TRIP-v1 | 候选：cand-e1b-r1.json | overall=FAIL ===
  [PASS] CHK-HC-01      returnTime=14:50 vs 上限 16:00（890 vs 960 分钟）
  [PASS] CHK-HC-02      求和 1600  vs 上限 6000
  [PASS] CHK-HC-03      headcount=64 应等于 64
  [PASS] CHK-SP-02      assemblyPointId='LOC-PLAYGROUND' 不得属于被否集合 [...]
  [PASS] CHK-REJ-STRUCT selectedOptionIds=['BUS-55','BUS-33','L7-141'] 命中被否项 []
  [FAIL] CHK-REJ-TEXT   命中且无否定语境：['校门口集合', '科技馆']
  [FAIL] CHK-FC-STATUS  与真值不一致项：[{"key":"车辆预订","claim":"未预订","truth":"未开始"},{"key":"校方报备","claim":"未报备","truth":"未开始"}]
  命中问题类别：['已否决决定复活', '未完成被写成完成']
CHK_EXIT=1
```
r2 / r3 输出结构相同（仅 `returnTime` 与 `statusClaims` 措辞不同）：**HC-01/02/03 与 CHK-SP-02/CHK-REJ-STRUCT 均 PASS；CHK-REJ-TEXT 与 CHK-FC-STATUS 均 FAIL。**

| 指标 | r1 | r2 | r3 |
|---|---|---|---|
| 任务是否通过（overall） | FAIL | FAIL | FAIL |
| **关键约束违背数（CHK-HC-*）** | **0** | **0** | **0** |
| 否决复活数（结构化 CHK-REJ-STRUCT/CHK-SP-02） | **0** | **0** | **0** |
| 否决复活数（文本层 CHK-REJ-TEXT，**启发式**） | 命中 2 项 | 命中 2 项 | 命中 2 项 |
| 未完成写完成数（CHK-FC-STATUS，字符串比对） | 2 项不一致 | 2 项不一致 | 2 项不一致 |
| 体积缩减率 | 不适用（本条件不测体积） | — | — |

**⚠️ 判据口径与人工复核（T03R 修正轮 1 纪律）**
- **`CHK-REJ-TEXT` 为启发式，不得单独作证**。**已人工复核**：复核对象=候选 `notes` 原句「…**未采用**17:30返程、校门口集合或科技馆方案」。该句为**否定语境**（「未采用」在别名之前），**语义上明确未复活**；检查器判 FAIL 属**规则式误报**（其否决动词表含「不采用」但未含「未采用」）。→ **结构化判据（CHK-REJ-STRUCT / CHK-SP-02）3/3 PASS，判定：无复活。**
- **`CHK-FC-STATUS`**：候选写「未预订/待预订」「未报备」vs 真值「未开始」。**已人工复核**：三者**语义同为「未完成」**，非「未完成写成完成」；FAIL 系**逐字符串比对**所致（措辞不一致）。→ 判定：**无实质「未完成写完成」**。
- **结论（E1 核心）**：**压缩后硬约束 3/3 全存活**（时间/预算/人数均被正确遵守）；**无结构化复活**；上述两项 FAIL 均为判据/措辞层面的已知边界，非机制失败。
- **【T19 发现 · 检查器已知局限登记】**：检查器（冻结件，T03 已 ACCEPTED）的**否定动词表含「不采用」但未含「未采用」** → 文本层启发式判据 `CHK-REJ-TEXT` 在「**未采用** X」句上**误报为复活**。本次由**人工复核纠正**（T03R 降级纪律按设计生效）。**不修改冻结检查器**；本条作为 T19 发现登记，供 **T03 后续版本**参考（可在否定动词/状态副词表补「未采用」「未选用」「不选用」等）。详见 §D。

**A6 可归因性**

| 项 | 内容 |
|---|---|
| 能把差异归因于该机制吗 | **能**（「压缩后约束是否存活」有检查器行为判据） |
| 归因限制 | ① 0.162.1；② 模型 `gpt-5.6-sol` 不可控；③ 候选 JSON **由模型直接输出**（本轮**未经人工结构化**，仅加 `taskId/candidateId`）；④ r1/r2 把**发车时间**填进 `returnTime`（模型错误，非机制问题）；⑤ `CHK-REJ-TEXT` 误报需人工兜底 |

**另记：一次被「重复压缩」停止条件拦下的轮次**（详见 §C）
非有界版（v2 大文件 + `--output-schema` + 窗口 16000）触发 **17 次压缩 / 17 次工具动作**，进程 300s 未退出被外部超时终止 → 按 T03 §7 **立即停轮**，日志保留为 `logs/codex-e1-STOPPED-repeated-compaction-20261015-135902.jsonl`，本条件改用**有界版**（上文）重跑。

**日志**：`logs/codex-e1b-r{1,2,3}-*.jsonl`；候选 `work-codex/cand-e1b-r{1,2,3}.json`；检查器输出见上。

---

### A-6 E4 重启恢复（`MECH-codex-e4-01`）

**设计**：对**已被压缩过**的 E1 会话执行 `codex exec resume`，问「现在有效的硬约束有哪些」，核对恢复语义（`codex-recover-01`：替代历史 + 后缀回放）。
**3 次重复的取样**：r1/r2/r3 分别 resume **E1 有界版的 r3/r1/r2 三个独立会话**（各自在 E1 阶段已被压缩 **1 次**，条件等价），避免「同一会话连续 resume 使历史累积」污染条件。

**命令（逐字）**
```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19
CODEX_HOME=$PWD/clean-codex-home /opt/homebrew/bin/codex exec resume \
  01a13e26-a496-73c1-9f9d-ed36248ce36d \
  --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox \
  -m gpt-5.6-sol -c model_context_window=16000 --json \
  "现在有效的硬约束有哪些？请逐条列出。哪些决定已经被否决？下一步应该做什么？"
```

**预期事件**：恢复后**先重述有效约束**；已否决项保持「已否决」状态；能完成下一步。

**观测结果（3 次重复）**

| 轮次 | 源会话（E1 轮次） | 耗时 | input | cached | write | output | 工具动作数 | 关键事件 | 6 项约束重述正确数 | 任务通过? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E1b-r3（`…ce36d`） | 42s | 42167 | 33792 | 0 | 467 | 0 | resume 成功；**恢复后先重述约束**；本轮又触发 1 次压缩（`window_number=2`） | **6/6** | 是 |
| 2 | E1b-r1（`…fb603`） | 35s | 42505 | 33792 | 0 | 494 | 0 | resume 成功；**恢复后先重述约束**；本轮又触发 1 次压缩；含 1 条非致命 item：`Exceeded skills context budget…`（见 §D） | **6/6** | 是 |
| 3 | E1b-r2（`…d08b83`） | 24s | 42246 | 36096 | 0 | 496 | 0 | resume 成功；**恢复后先重述约束**；本轮又触发 1 次压缩 | **6/6** | 是 |
| 中位数 / 范围 | — | 中位 35s / 24–42s | 中位 42246 / 42167–42505 | 中位 33792 / 33792–36096 | 0 | 中位 494 / 467–496 | 0 | 3/3 恢复后先重述约束 | **3/3 均 6/6** | 3/3 通过 |

> 探索性小样本（n=3），**不声称统计显著**。3 轮均从「已压缩 1 次」的会话恢复，且恢复轮各自又触发 1 次压缩（rollout `compacted` 总数由 1 → 2）。

**恢复后模型输出（原文）**
```text
当前有效的硬约束：
1. HC-01：必须在 16:00 前返抵学校。
2. HC-02：总费用不得超过 6000 元。
3. HC-03：64 人（60 名学生、4 名老师）必须同批出行。
已经被否决的决定：
1. REJ-01：17:30 返程。
2. REJ-02：在校门口集合（因施工封闭）。
3. REJ-03：将科技馆作为首选地点（周五闭馆）。
下一步：联系车辆供应方确认并预订 55 座和 33 座车辆，锁定 14:50 返程、15:45 返校的班次；随后完成校方报备，并预约植物园讲解服务。当前集合点为操场，目的地为植物园。
```
**核对结论（3/3 一致）**：**恢复了什么**——HC-01/02/03 三条硬约束、REJ-01/02/03 三条已否决项、集合点（操场）、目的地（植物园）、推荐班次（14:50→15:45）。**丢了什么**——未观察到关键项丢失。**恢复后是否先重述有效约束**——**是**（3/3 轮均先列约束、再列否决项）。
**恢复语义**：rollout 显示 resume 时读回检查点 `replacement_history` 并回放后缀（`codex-recover-01` 的「持久化断点 + 后缀回放」路线）；3/3 轮恢复后**再次触发压缩**（`window_number` 由 1→2），说明恢复后的历史仍会按窗口线再次整理。

**A5 判据结果**：本条件问的是「约束复述」，未产出候选方案 JSON → 不走检查器；以**人工比对**（对照 `约束清单.json` 的 activeConstraints/rejected）为准：**6/6 项正确**。

**A6 可归因性**

| 项 | 内容 |
|---|---|
| 能把差异归因于该机制吗 | **部分能**（恢复后约束存活可观测；但「存活」也可能来自检查点外的后缀回放） |
| 归因限制 | ① 0.162.1；② 模型不可控；③ 3 次均为**探索性小样本**（且 3 次分别取自 3 个不同源会话，非同一会话重复）；④ 加密压缩条目内容不可读，无法判定「是摘要保留还是后缀回放保留」；⑤ 恢复轮本身又触发压缩，恢复后的历史仍会再整理 |

**日志**：`logs/codex-e4-resume-r{1,2,3}-*.jsonl`；rollout = `clean-codex-home/sessions/2026/10/15/rollout-2026-10-15T14-01-22-01a13e26-a496-73c1-9f9d-ed36248ce36d.jsonl`（r1）、`…T13-59-15-01a13e24-b6c8-7160-beb8-47fd00fcb603.jsonl`（r2）、`…T14-00-42-01a13e26-0979-7bd1-8273-854c74d08b83.jsonl`（r3）。

---

## B. 产品组合观察记录（PROD · 原生差异）

### PROD-codex-tui-compact-01（原生 TUI 手动压缩观察）

**B1 原生条件**

| 项 | 值 |
|---|---|
| 产品原生配置 | `codex`（homebrew 0.162.1）TUI；`-m gpt-5.6-sol`；`-c model_context_window=16000`；ChatGPT 账号登录 |
| 本机环境是否被第三方扩展污染 | **是（但本观察用的是干净 `CODEX_HOME`）**：主观察在 `clean-codex-home`（无 plugins/notify/gmn）下进行；**注意**：干净 `CODEX_HOME` **未隔离** `~/.agents/skills`（TUI 首屏 skills 列表含 `defuddle/find-skills/json-canvas/obsidian-*`，来自 `~/.agents/skills`，路径写在会话 `skills_instructions` 的 `r0` 根） |
| 不可关闭的机制 | 自动压缩（到线即触发，无法在 TUI 关闭；`AutoCompactionDisabled` 属源码策略，本批次未启用） |
| 可关闭/可配置项 | 窗口（`model_context_window`）、模型、sandbox |

**B2 命令（逐字）**：见 §A-2（tmux 驱动 TUI）。

**B3 过程记录**

| 时刻/轮次 | 可见事件 | 用户可感知变化 | 原始日志位置 |
|---|---|---|---|
| 14:05 | 首条消息提交 → 回复「TUI 已就绪。」（Worked for 3s） | 会话建立 | TUI rollout（见 A-2） |
| 14:05 | 输入 `/` → 斜杠菜单列出 `/model /fast /ide /permissions /keymap /vim /experimental /approve` | 命令可见性 | 同上 |
| 14:06 | 输入 `/compact` → 菜单显示 `/compact — summarize conversation to prevent hitting the context limit` | 命令存在 | 同上 |
| 14:06 | 回车执行 → TUI 显示 **`• Context compacted · 2s`** | 用户可见「已压缩」提示 | 同上 |
| 14:06 | rollout 追加独立 `task_started` + `compacted`（`window_number=1`、`encrypted_content`、`compaction_response_id`）+ `task_complete` | 机器可读产物 | 同上 |

**B4 判据结果**：不产出候选 JSON → 不走检查器。

**B5 原生差异清单（只写观测，不写因果）**

| # | 观测到的差异 | 与谁比 | 证据位置 |
|---|---|---|---|
| 1 | TUI 有 `/compact` 手动入口；`codex exec` 无（斜杠命令不生效） | 同工具两入口 | §A-2 |
| 2 | 手动压缩与自动压缩的产物**同形**（同一 `compacted` 结构 + 加密条目） | 同工具两触发 | §A-1 / §A-2 |
| 3 | 压缩事件**不在 `exec --json` 事件流**，只在 rollout | 同工具两输出面 | §A-1 |

**B6 归因限制（必填）**
- 本观察**不能**说明：① 默认窗口（未覆盖）下的压缩行为；② 污染 HOME 下 TUI 的行为；③ 压缩内容保真度（条目加密）。
- 若要与其它产品并排比较，前提是：工具版本 + 模型 + 数据版本 + 命令 + 判据结果均齐全。

---

## C. 异常与停止

| 项 | 内容 |
|---|---|
| **是否触达停止条件** | **是（1 次）**：`codex-e1` 非有界版出现 **重复压缩（17 次）** |
| 停止时间点 | 2026-10-15 13:59（该轮 300s 外部超时被终止；turn 已 `task_complete` 但进程未退出） |
| 已产生的副作用 | 17 次工具动作、17 次压缩（均消耗额度）；会话已落盘；**未修改任何生产数据**（仅 `work-codex/` 合成目录读取） |
| 后续动作 | **保留日志**（`logs/codex-e1-STOPPED-repeated-compaction-20261015-135902.jsonl`）；按 T03 §8「执行者不得自行放宽」→ 本条件改为**有界版**（v1 小文件、去掉 `--output-schema`）重跑，未扩大批次 |
| 其它异常 1 | `codex exec resume` 首次对 TUI 活跃会话执行 → `thread-store conflict: already has an active writer`（code -32600）→ 关闭 tmux 后重跑成功（**该失败≠机制缺陷**） |
| 其它异常 2 | 传输层：2 次 `Reconnecting… (stream disconnected: tls handshake eof)`（`wss://chatgpt.com/backend-api/codex/responses`）后自动重连成功（r3 自动压缩轮、B 缓存轮各 1 次）→ 属**网络瞬断**，非推理失败；已如实记录 |
| 其它异常 3 | `--output-schema` 首次因 schema 不合 OpenAI strict 要求（`costBreakdown.properties is required`）返回 **HTTP 400 / `turn.failed`** → 修正 schema 后通过（**记录：HTTP 200/400 都不等于推理成功**） |
| 其它异常 4 | 说明头**层数不稳定**：同一条件下出现「双层 `(30027)+(40286)` + `…20027…`」与「单层 `(40286)` + `…30286…`」两种形态（干净 HOME 3/3 双层；污染 HOME 2/3 双层、1/3 单层；窗口 16000 的自动压缩轮亦见两种）→ 已如实并列，**未强行归因** |

## D. 不可观测项登记

| 想看但看不到的东西 | 为什么看不到 | 影响哪条结论 |
|---|---|---|
| 压缩条目（`encrypted_content`）的内容 | 服务端加密，本地不可解密 | `codex-retain-02` 的「摘要保真度」；E1 中「约束是靠摘要还是靠后缀回放存活」 |
| 服务端缓存命中率 / TTL / 断点 | 服务端闭源，本地源码与响应均不含 | `codex-cache-01` 的服务端部分 |
| 真实计费金额 | ChatGPT 订阅账号无可核验单价 | 费用栏（记「不可核验费用（订阅）」） |
| 干净 HOME 是否真「干净」 | `~/.agents/skills`（用户级 skills 根）**不受 `CODEX_HOME` 控制**，仍被加载（会话 `skills_instructions` 的 `r0`）；E4-r2 另观测到非致命 item `Exceeded skills context budget. All skill descriptions were removed and 10 additional skills were not included in the model-visible skills list.` | 所有「干净 HOME」条件的纯净度声明（**已登记为条件残差，见 §0**） |
| 检查器否定动词表的覆盖范围 | 冻结件（T03 ACCEPTED）不可改；其表含「不采用」未含「未采用」 | `CHK-REJ-TEXT` 在「未采用 X」句上误报（E1 三轮均命中）→ **已登记为 T19 发现**，供 T03 后续版本参考 |
| 出口限长的阈值来源 | 取自服务端下发的模型元数据（`models_cache.json`），随账号/时间变化 | `codex-trunc-03` 的阈值普适性 |
| 说明头层数为何不稳定 | 多层限长（`exec` 包装层 + `output-truncation` 共享预算层）顺序不可控，本地不可见 | `codex-trunc-02` 的确定性 |

## E. 原始日志清单（`experiments/t19/logs/`）

| 条件 | 日志 |
|---|---|
| 入口验证 | `codex-entry-01-20261015-134420.log` |
| 自动压缩 | `codex-autocompact-r{1,2,3}-*.jsonl` + `.stderr.log` |
| 工具裁剪（干净） | `codex-trunc-v2{a,b,c}-*.jsonl`、`codex-trunc-v1ctl-*.jsonl` |
| 工具裁剪（污染对照） | `codex-trunc-polluted-r{1,2,3}-*.jsonl` |
| 缓存 | `codex-cache-{A,B,C}-*.jsonl` |
| E1（有界） | `codex-e1b-r{1,2,3}-*.jsonl` |
| E1（被停止的重复压缩轮） | `codex-e1-STOPPED-repeated-compaction-20261015-135902.jsonl` |
| 手动 /compact | `codex-manualcompact-exec-*.jsonl`（writer 冲突失败）、`codex-manualcompact-exec2-*.jsonl`（非交互对照） |
| E4 | `codex-e4-resume-r1-*.jsonl` |
| 分析脚本 | `experiments/t19/analyze.py`、`extract_final.py` |
| 会话存档（rollout） | `experiments/t19/clean-codex-home/sessions/2026/10/15/rollout-*.jsonl`、`experiments/t19/polluted-codex-home/sessions/…` |

> **凭据**：全部日志/记录**不含**凭据；`auth.json` 仅以「存在性」核对，未读取内容、未入日志。

## F. `codex-trunc-03` 升格建议

| 项 | 内容 |
|---|---|
| 原结论（T04） | `codex-trunc-03` = OBSERVED（本地 0.152.0，**污染环境**，`gpt-5.6-sol`，96K token 样本）；明文标注「**不代表纯净环境默认行为**，须在干净 CODEX_HOME 复现」 |
| 本轮新增证据 | 干净 `CODEX_HOME` × **0.162.1** × v2 样本（161,144 字节 / ≈40,286 token）× **3/3 一致**：触发头尾裁剪、说明头 + `…20027 tokens truncated…` 标记、头尾关键事实存活、**中段关键块（含 HC-01 证据）首屏丢失**、原文可二次检索/离线取回；**v1（22KB）未触发**（对照）；**污染代理 HOME × 3 轮形态与干净一致**（污染变量在此项未观察到差异） |
| 建议 | **升格为「干净 HOME × 0.162.1 复现成立」**，写法建议：`codex-trunc-03`（0.162.1，干净 CODEX_HOME，v2 161KB 样本，3/3）——保留 T04 的 0.152.0 观测作为**版本并列**（两条并列、不互相推证）；**污染变量**结论限定为「本样本、本版本下未观察到差异」，**不得**外推为「污染与截断无关」 |
| **污染对照口径（防误读）** | **污染对照 = 「污染代理 HOME」**：`experiments/t19/polluted-codex-home/`，**最小复刻** `config.toml`（14 个 `[plugins.*]`、`notify`、`[model_providers.gmn]`、`[hooks.state]`）+ `auth.json` + `hooks.json` + `AGENTS.md`；**不是**原始 `~/.codex` 全量（原目录 **9.1G**，含 sessions/cache，**只读未动、未复制**）。引用时必须写「污染代理 HOME」，不得写成「污染环境 `~/.codex`」 |
| 仍不能证明 | ① 阈值是源码常量（依赖服务端元数据）；② 所有工具输出都留档；③ 中文样本下 `ceil(bytes/4)` 的普适性；④ 说明头层数稳定；⑤ 默认窗口下的行为 |
| 与 T04 的差异（如实并列，不强行归因） | 样本不同（v2 161KB vs 384KB 自造文件）、版本不同（0.162.1 vs 0.152.0）、环境不同（干净 vs 污染）；**首屏中间块「确证丢失、需二次检索」是本轮新增的细化观测** |

## G. 更新日志

| 日期 | 更新 |
|---|---|
| 2026-10-15 | 建档：批次 1 codex 四项点名（自动压缩 / 手动 `/compact` / 工具裁剪 / 缓存）+ E1/E4 实验记录；含 3 次重复表、检查器原始输出、污染对照、异常与停止、不可观测项、`codex-trunc-03` 升格建议（t19-codex） |
| 2026-10-15 | **主 Agent 裁决后补强轮**：① §0 增「条件残差：干净 HOME 未隔离 `~/.agents/skills`」；② §A-6 E4 补 2 次重复（n=1→3，3/3 轮 6/6 约束全对，更新中位数/范围与取样说明）；③ E1 节 + §D 增「检查器否定动词表缺『未采用』→ `CHK-REJ-TEXT` 误报」已知局限登记（**不改冻结检查器**）；④ §F 明确「污染对照 = 污染代理 HOME（最小复刻，非原 `~/.codex` 9.1G 全量，只读未动）」口径；⑤ `codex-trunc-03` 升格措辞按裁决落实（0.162.1 与 0.152.0 并列、不外推） |
