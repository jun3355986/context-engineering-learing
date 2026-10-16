---
title: T19 批次4 · oh-my-pi（omp）真实机制实验记录
task: T19
batch: 4
tool: oh-my-pi / omp
role: 实验 Agent（t19-omp）
created: 2026-10-15
snapshot: f979f4639777858de28e6ecb99d577443abe0b7b
execVersion: omp/18.11.0
pollution: extensions/teamai-hooks.ts（+ skills/teamai）
model: zhipu-coding-plan/glm-5.3-flash（智谱 Coding Plan）
template: 05-实验/T03/运行记录模板.md
---

# T19 批次4 · omp 真实机制实验记录

> 判据一律来自 T03 检查器（`check_task.py`）；**不靠模型自述**。HTTP 200 ≠ 推理成功；压缩成功不靠模型自述（看事件/产物）。
> 原始日志：`~/workspace/agent-context-research/experiments/t19/logs/omp-*.jsonl`（凭据不入日志；`--api-key` 未使用）。
> 工作区：`~/workspace/agent-context-research/experiments/t19/work-omp/`（**未遇** §2.9 的 workspace 锁类问题；本批次全部在 workspace 下完成，无需挪 `/tmp`）。

## 0. 版本三字段（本记录所有条件共用）

| 字段 | 值 | 来源 |
|---|---|---|
| **实际执行版本** | `omp/18.11.0`（入口 `/Users/junjielong/.bun/bin/omp` → `@oh-my-pi/pi-coding-agent/dist/cli.js`；开跑日复测 exit 0，**无漂移**） | `omp --version` |
| **研究快照** | `f979f4639777858de28e6ecb99d577443abe0b7b`（main@2026-10-14 17:18 +0200） | 前置登记-G7G8 §1 |
| **两者是否一致** | **不一致**：T08 登记 U4——快照 main 与发包版本**非同一代码**；本记录结论只用于**出货二进制行为**，不外推到快照 main 行号 | 前置登记 §1 |
| **模型 / provider / 登录** | `zhipu-coding-plan/glm-5.3-flash`；provider=`zhipu-coding-plan`；OAuth native（`~/.omp/oauth/native/darwin/`，**只验存在性**） | config.yml `modelRoles.default` |
| **本机污染** | `~/.omp/agent/extensions/teamai-hooks.ts`（6,087B，安装时 10:27 生成，**本次运行未禁用**，`--no-extensions` 可用但未用）；`~/.omp/agent/skills/teamai/` | G8 §2.4 + 现场核对 |
| **数据版本** | T03 冻结包 `T03-DATA-TRIP-v1`（`长工具结果-公交查询-v1.txt` sha256 `802b98df…40ec4b`）+ T19 样本 v2 `长工具结果-公交查询-v2.txt`（sha256 `1c9309e718e1a8823f3f6b1e42c13e297642b2880959aaa41238dd84ccf2011b`，2,254 行 / 161,144 字节，复算一致） | manifest.sha256 |
| **费用** | **不可核验费用（订阅）**——智谱 Coding Plan 订阅制；返回 usage 的 `cost` 字段全为 0，**不据此声称免费** | usage 事件 |

**归因限制（必写）**：模型 = `glm-5.3-flash`（**非 Anthropic / 非 OpenAI**）；provider = 智谱 Coding Plan。任何"机制生效/失效"结论都受此模型与 provider 限制；压缩方法链中 `remote`（provider 原生压缩）在 zhipu 上不可用属**provider 侧差异**，非 omp 机制缺失。

### 0.1 窗口与阈值的实测前提（重要）

- `omp models` 实测：`glm-5.3-flash` 上下文窗口 = **1M**（1,000,000）。
- 按 `ohmy-trigger-01` 公式：默认阈值 = `window − max(floor(W×0.15), 16384)` = `1,000,000 − 150,000` = **850,000** token。
- **填到 85 万 token 成本不可接受** → 依任务卡「如可小窗口覆盖则用更小值降成本」，改用**固定阈值点覆盖**：`compaction.thresholdTokens=30000` + `compaction.keepRecentTokens=8000`（覆盖文件见 §A1，**仅运行期生效**）。
- **负向对照（证明默认阈值确实很高）**：§A3 截断实验（**无** `--config` 覆盖）请求上下文达到 **29,775–29,816 token** 时**未发生任何压缩** → 与"默认阈值 850,000"一致，不与"阈值 30,000"矛盾。
- **全局配置未被改动**（复测）：`memory.backend=off`、`compaction.thresholdTokens=-1`、`compaction.keepRecentTokens=20000`、`~/.omp/agent/config.yml` 仍为原 6 行。

---

# 一、MECH-omp-trunc-* · 工具输出裁剪（E2）

## A1. 变量与固定量

| 项 | 值 |
|---|---|
| 唯一自变量 | 工具输出**是否超过出口限值**（v2 大样本 161KB vs v1 300 行 / 22KB 对照） |
| 固定量 | 工具版本 `omp/18.11.0`；模型 `glm-5.3-flash`；provider `zhipu-coding-plan`；窗口 1M；**无压缩覆盖**；cwd=`work-omp`；工具集 `--tools bash`；数据 v2/v1 冻结哈希 |
| 操作定义 | A 组：`cat` v2（2,254 行 / 161,144 字节）；B 组：`cat` v1（300 行 / 22,003 字节） |

## A2. 命令模板（逐字）

```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19/work-omp
/Users/junjielong/.bun/bin/omp -p --mode=json --auto-approve --tools bash \
  --session-dir "$W/sessions" \
  "Use the bash tool to run exactly: cat data/长工具结果-公交查询-v2.txt   Then reply only: DONE"
```

## A3. 预期事件（先写，后对照）

| # | 预期出现的事件 | 依据 |
|---|---|---|
| 1 | 超限输出被截断；上下文里只留预览 + `artifact://<id>` | `ohmy-trunc-01` / `ohmy-trunc-02` |
| 2 | 上限 = 3000 行 / 50 KiB 先到者 | `ohmy-trunc-01` |
| 3 | 未到线（v1）原样返回、无截断 | `ohmy-trunc-01` 负例 |

## A4. 观测结果（3 次重复，强制 `--tools bash`）

| 轮次 | 工具 | totalLines | totalBytes | outputLines | outputBytes | 方向 | headRange | tailRange | elidedLines | artifactId | 第 1 次请求 in/out | 第 2 次请求 in/out |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | bash | 2255 | 161144 | 717 | 51221 | **middle** | 1–358 | 1898–2255 | 1539 | `0` | 24 / 89 | 26677 / 3 |
| 2 | bash | 2255 | 161144 | 717 | 51221 | **middle** | 1–358 | 1898–2255 | 1539 | `0` | 24 / 48 | 26636 / 3 |
| 3 | bash | 2255 | 161144 | 717 | 51221 | **middle** | 1–358 | 1898–2255 | 1539 | `0` | 24 / 64 | 26652 / 17 |
| 中位数/范围 | — | 2255 | 161144 | 717 | 51221 | 恒定 | 恒定 | 恒定 | 1539 | 0 | — | — |
| **v1 对照** | bash | 301 | 22003 | — | — | **无截断**（`truncation=null`） | — | — | 0 | 无 | 3160 / 60 | 10860 / 28 |

- **关键事实**：`details.meta.truncation` 明写 `direction:"middle"`、`truncatedBy:"middle"`——**bash 工具是「保头+保尾、掐中间」**，与 `ohmy-trunc-01` 记载的 `truncateHead`/`truncateTail` 二元形态**不同**（`truncateHead` 只是函数级观察；产品侧 bash 走的是 middle）。**这是对证据卡的实测修正**。
- 可见文本（719 行）内嵌两处标记：
  - 掐断点：`[…1539ln elided…]`（插在 head 与 tail 之间）
  - 末尾：`[Showing lines 1-358 and 1898-2255 of 2255; 1,539 middle lines (107.4KB) elided. Read artifact://0 for full output]`
- **head 端点会切在半行**（head 末尾 `…地铁北站 |   43 | -` 后直接接标记，tail 起点也是半行 ` |   34 | -`）——与 `truncateHead`「不返回半行」不同；middle 形态按**字节预算**切。
- **中段关键事实丢失**：v2 README §3 的关键块 **文件第 1339–1344 行（班次号 L7-139~L7-144）落在被掐的 359–1897 行区间** → 上下文里 `L7-141`（推荐班次）**不可见**；`L7-139` 仅因**文末审计注**提及而出现（非数据行）。**头（1–13 行）与尾（结论区 2246–2254）存活**，结论注释 1/2（15:20 及以后不可用、可选仅 14:20/14:35/14:50）在尾部存活。
- **未强制的探索性观察（工具选择不确定性）**：同一 prompt 下 3 次中 1 次模型改用 `read` 工具，其截断形态为 `direction:"head"`、`truncatedBy:"lines"`、`outputLines=300`（=`read.defaultLimit` 默认 300，**非 3000**）、`shownRange 1–300`、`nextOffset=301`、`maxBytes=153600`。即 **read 与 bash 的裁剪策略不同**（read=保头 300 行 / 150KiB；bash=保头尾 / 50KiB）。

## A5. artifact 通道与哈希一致性（对齐 `ohmy-trunc-02`）

```bash
# artifact 落盘位置：<session-dir>/<sessionId>/<n>.bash.log
$ ls -la work-omp/sessions/2026-10-15T06-21-33-122Z_01a13e39-.../0.bash.log
-rw-r--r--  1 junjielong staff  161144  ...  0.bash.log
$ wc -l -c 0.bash.log          → 2254  161144
$ shasum -a 256 0.bash.log     → 1c9309e718e1a8823f3f6b1e42c13e297642b2880959aaa41238dd84ccf2011b
$ shasum -a 256 data/长工具结果-公交查询-v2.txt → 1c9309e718e1a8823f3f6b1e42c13e297642b2880959aaa41238dd84ccf2011b
```
**artifact 与原文逐字节一致（sha256 相同）→ 内容哈希一致 ✓**；被掐的中段（第 1339–1344 行 L7-139~L7-144）在 artifact 中完整可读。

## A6. 判据结果（检查器）

本条件**不产出候选方案 JSON**（E2 场景判据为"头/中/尾行号人工比对 + artifact 找回"，见 T03 规程 §3 E2 行）→ **不适用 `check_task.py`**；判据 = `details.meta.truncation` 结构字段 + artifact sha256 比对（见 A4/A5）。

## A7. 可归因性

| 项 | 内容 |
|---|---|
| 能归因于该机制吗 | **能**（裁剪阈值/形态是 omp 出口治理的直接产物，3 次完全一致） |
| 归因限制 | ① `details.meta.truncation` 是 omp 自报字段，未与源码 `streaming-output.ts` 逐行对齐（快照非同一代码）；② 模型偶发改用 `read`（工具选择不确定性）；③ 未测 3000 行上限单独触发的情形（v2 字节先到线）；④ 未测 16 MiB artifact 上限 |

---

# 二、MECH-omp-compact-* · 触发到线 + 压缩方法链（E1/E5）

## A1. 变量与固定量

| 项 | 值 |
|---|---|
| 唯一自变量 | 上下文是否越过**压缩触发线** |
| 固定量 | `omp/18.11.0`；`glm-5.3-flash`；`--tools bash`；cwd；数据（3 个合成长文本 `big1/2/3.txt`，各 144,901 字节 / 902 行，生成器 `gen_bigfiles.py` 固定种子） |
| 覆盖（非默认，已登记） | `--config work-omp/overlay-compact.yml` → `compaction.thresholdTokens: 30000`、`compaction.keepRecentTokens: 8000`（默认分别为 -1 / 20000） |

## A2. 命令模板（逐字）

```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19/work-omp
/Users/junjielong/.bun/bin/omp -p --mode=json --auto-approve --tools bash \
  --config "$W/overlay-compact.yml" --session-dir "$W/sessions" \
  "Run these three bash commands as three SEPARATE bash tool calls, in order, exactly one command per tool call (never combine them):
   1) cat data/big1.txt
   2) cat data/big2.txt
   3) cat data/big3.txt
   After each command, briefly note the last line you saw. At the end, reply with the total number of lines across all three files."
```

## A3. 预期事件（先写，后对照）

| # | 预期出现的事件 | 依据 |
|---|---|---|
| 1 | 越过阈值时发 `auto_compaction_start/end`，`reason` 标明触发路径 | `ohmy-trigger-03`、T08 过程观察 §4 |
| 2 | 方法链按 `methodOrder` 走：`remote→snapcompact→handoff→shake→soft`，失败逐级回退 | `ohmy-compact-01` |
| 3 | 压缩提交为**追加** `CompactionEntry{summary, firstKeptEntryId, tokensBefore}`，不删原条目 | `ohmy-persist-01` |
| 4 | 摘要是结构化格式（Goal/Constraints/…） | `ohmy-summary-01` |

## A4. 观测结果（3 次重复）

| 轮次 | 工具动作 | 请求 usage（in/out/cacheRead） | `auto_compaction_start` 序列 | 实际走法 | 会话内 `CompactionEntry`（method, before→after） |
|---|---|---|---|---|---|
| 1 | cat×3 | 3297 → 21957 → 23665 → 22916 | `snapcompact` → `handoff` | **remote 未尝试**；snapcompact 成功（无 error）→ 第 2 次 snapcompact 失败 → handoff 成功 | `snapcompact 21957→23293`；`handoff 23665→22396` |
| 2 | cat×3 | 3341 → 21942 → 23634 → 22852 | `snapcompact` → `handoff` | 同上 | `snapcompact 21942→23278`；`handoff 23634→22383` |
| 3 | cat×3 | 3346 → 21915 → 23608 → 22880 | `snapcompact` → `handoff` | 同上 | `snapcompact 21915→23254`；`handoff 23608→22499` |
| 中位数/范围 | 3 | — | — | 3/3 一致 | snapcompact before≈21.9K；handoff before≈23.6K |

**关键事件原文**（3 轮一致）：
```
auto_compaction_start :: {"reason":"threshold","action":"snapcompact"}
notice:: warning  snapcompact could not leave room under the compaction trigger; trying the next preferred compaction method.
auto_compaction_end :: {"action":"snapcompact","aborted":false,"willRetry":false,
                        "errorMessage":"snapcompact could not leave room under the compaction trigger; ..."}
auto_compaction_start :: {"reason":"threshold","action":"handoff"}
auto_compaction_end :: {"action":"handoff","aborted":false,"willRetry":false}
```

### A4.1 方法链实际走法（实测）

`compaction.methodOrder` 默认 = `["remote","snapcompact","handoff","shake","soft"]`（`omp config list` 实测确认）。**实测走法**：

1. **`remote`：未出现任何 `auto_compaction_start{action:"remote"}` 事件** → 在 `zhipu-coding-plan` 上**不可用**（provider 原生压缩为 OpenAI/Anthropic 能力），被**静默跳过**。**归因限制**：这是 provider 侧差异，不是 omp 机制缺失。
2. **`snapcompact`：实际执行**（产生 `CompactionEntry{method:"snapcompact"}`）。注意其 `tokensAfter(23293) > tokensBefore(21957)`——**未减小上下文**，故下一次触发时被判定"could not leave room under the compaction trigger"而**回退**。
3. **`handoff`：实际执行**（产生 `CompactionEntry{method:"handoff"}`），`tokensAfter < tokensBefore`（如 23665→22396），**成功**。
4. `shake` / `soft`：本条件**未触达**（handoff 已成功）。

> **实测与证据卡的差异**：`ohmy-compact-01` 只断言"五方法链、失败逐级回退"；本实验补上**真实走法**（remote 跳过 → snapcompact 执行但不减量 → handoff 成功），并首次观测到 snapcompact 的 `tokensAfter > tokensBefore` 现象。

## A5. 压缩产物与持久化（对齐 `ohmy-persist-01` / `ohmy-summary-01`）

`CompactionEntry` 实测字段（session JSONL，1 行 1 条）：
```
type=compaction  id=2993e675  parentId=…  runtime={"version":"18.11.0"}
summary="## Goal\nRun three specified bash commands …"      ← 结构化摘要（Goal / Constraints & Preferences / …）
firstKeptEntryId="…"   tokensBefore=…   tokensAfter=…   method="handoff"   details={"readFiles":[],"modifiedFiles":[]}
```
- **摘要格式**：以 `## Goal` 开头，含 `## Constraints & Preferences` 等分节 → 与 `ohmy-summary-01` 一致。
- **`firstKeptEntryId` 存在** → 支持"摘要 + 保留段"投影（`ohmy-summary-02`）。
- **原条目保留**：会话条目计数 `message 11 / custom 8 / compaction 1`——原 message 条目仍在同一 JSONL 内，**压缩为追加**。

## A6. 判据结果（检查器）

本条件为"触发/方法链"机制观测，**E1 的检查器判据在 §三 给出**（本条件不单独产出候选 JSON）。触发与压缩由 **事件 + `CompactionEntry` 产物**证实，**不采用模型自述**。

## A7. 可归因性

| 项 | 内容 |
|---|---|
| 能归因于该机制吗 | **能**（3/3 一致触发 `reason:"threshold"`；方法链走法 3/3 一致） |
| 归因限制 | ① 阈值用了**非默认覆盖**（30000/8000），非默认 850,000 → 只证明"阈值路径可用"，**不证明默认阈值数值**（默认值由 `omp models`+公式推定）；② `remote` 不可用属 provider 差异；③ `tokensBefore/After` 语义在 snapcompact 上表现反直觉（after>before），omp 未在事件里说明口径；④ 模型偶发把多条 `cat` 合并的倾向（本组 prompt 已强制分次，仍出现 r2 的 3 次压缩 vs r1/r3 的 1–2 次差异） |

---

# 三、MECH-omp-artifact-* / MECH-omp-resume-* · 压缩后找回 + 恢复语义（E4）

## A1. 变量与固定量

| 项 | 值 |
|---|---|
| 唯一自变量 | 压缩后**是否继续同一会话**（`--continue`）+ 是否读 `artifact://` |
| 固定量 | `omp/18.11.0`；`glm-5.3-flash`；`--tools bash`；`overlay-compact.yml`；cwd |
| 初始材料 | `work-omp/trip-context.md`（逐字取自 `消息序列.jsonl` 的 MSG-001~MSG-015）+ v2 长工具结果 + `big1/2/3.txt` 填充 |

## A2. 命令模板（逐字）

```bash
# Step A：灌入任务上下文 + 长工具结果 + 填充 → 触发压缩
cd /Users/junjielong/workspace/agent-context-research/experiments/t19/work-omp
/Users/junjielong/.bun/bin/omp -p --mode=json --auto-approve --tools bash \
  --config "$W/overlay-compact.yml" --session-dir "$W/sessions-e1-1" "$(cat trip-context.md)

你是班级郊游行程助手。…请严格按顺序执行以下工具步骤…1) cat data/长工具结果-公交查询-v2.txt 2) cat data/big1.txt 3) cat data/big2.txt 4) cat data/big3.txt …只回复一个词：READY"

# Step B：压缩后 --continue 追问（MSG-017 口径）
/Users/junjielong/.bun/bin/omp -p --mode=json --auto-approve --tools bash --continue \
  --config "$W/overlay-compact.yml" --session-dir "$W/sessions-e1-1" \
  "我回来了，接着上面的郊游任务，给出最终方案。另外先说一遍：现在有效的约束还有哪些？…"
```

## A3. 预期事件（先写，后对照）

| # | 预期出现的事件 | 依据 |
|---|---|---|
| 1 | 压缩后 `read artifact://<id>` 可取回原文，内容哈希一致 | `ohmy-trunc-01` artifact 通道 |
| 2 | 压缩后 `--continue`：上下文从**摘要 + 保留段**起，首条为 summary | `ohmy-recover-01`（持久化断点） |
| 3 | 恢复后**先重述有效约束**，不复活被否项 | T03 E4 判据 + `ohmy-recover-01` |

## A4. 观测结果（3 次重复）

| 轮次 | Step A 工具动作 | Step A 压缩事件 | Step B 首次请求 in/cacheRead | Step B 是否先重述约束 | 是否复活被否项 |
|---|---|---|---|---|---|
| 1 | 4（v2+big1+big2+big3） | snapcompact 失败 → handoff 成功；`dead-end recovery: elided 4 heavy blocks (~81,832 tokens)` | **1929 / 3072** | 是 | 否 |
| 2 | 4 | 3 次触发（1×snapcompact 成功 + 2×handoff） | **20236 / 3264**（首请求为工具循环首步） | 是 | 否 |
| 3 | 4 | snapcompact 失败 → handoff 成功；`dead-end recovery: elided 4 heavy blocks (~81,832 tokens)` | **2211 / 3072** | 是 | 否 |
| 中位数/范围 | 4 | 3/3 触发 | 1929–20236 | 3/3 | 3/3 |

**关键观察**：
- **恢复语义（`ohmy-recover-01` 持久化断点）**：Step B 首请求 `input` 仅 **1,929 / 2,211 token**（r2 因工具循环首步为 20,236）。若为"全量重放"，上下文应含 4 个重块（≈8.6 万 token）→ 实测**远小于**，与"从摘要 + 保留段投影重建、不重放被压前缀"一致。
- **首条是否为 summary**：JSON 事件流**不暴露完整请求体**，`agent_end.messages` 只列本回合新增消息 → **无法直接目视"首条 = summary"**。间接证据：① `CompactionEntry.firstKeptEntryId` 在场；② 恢复后 input 极小。→ 该点标 **UNOBSERVABLE（局部）**：不能证明"请求体第 1 条消息字面是 summary"。
- **dead-end recovery / shake（对 `ohmy-persist-01` 的实测修正）**：Step A 的 4 个重工具结果，在会话 JSONL 里被**改写为占位符**（原 toolResult 条目 id 不变、位置不变，内容变为 59 字节）：
  ```
  [shaken ~26560 tokens — recover: artifact://4 (region 1)]
  [shaken ~18416 tokens — recover: artifact://4 (region 2)]
  [shaken ~18455 tokens — recover: artifact://4 (region 3)]
  [shaken ~18474 tokens — recover: artifact://4 (region 4)]
  ```
  原文落在 artifact：`<sessionId>/0.bash.log … 3.bash.log`（= v2 与 big1~3 的**逐字节原文**）+ `4.shake.log`（205,473B，被 shake 的区域）。
  → **修正**：`ohmy-persist-01` 的"压缩只追加、不删任何原始条目"在**主压缩路径**成立（`CompactionEntry` 追加、原 message 条目保留）；但在 **dead-end recovery / `shake` 路径**，**重块条目的内容被就地替换为 `artifact://` 占位符**。**原始字节仍可经 artifact 找回**，但"条目内容不变"不成立。这是本批次对 T08 结论的**实测细化**（omp 源码里确有 `historyRewriteAt` 概念）。

## A5. artifact 找回（对齐 `ohmy-trunc-02`）

探索性单轮（`--tools bash,read`，prompt 要求先 `cat` v2 再 `read artifact://0` 并报 L7-141 行）：
```
TOOL bash  {"command":"cat data/长工具结果-公交查询-v2.txt"}  → middle 截断，artifact://0
TOOL read  {"path":"artifact://0"}                            → head 300 行，nextOffset=301（read 默认 limit）
TOOL read  {"path":"artifact://0:1300-1360"}                  → 65 行 / 5,120 字节（shownRange 1299–1363）
模型最终回答：141 | 2026-10-23 | L7-141 | 14:50 | 返程 | 示例一中 | 55 | 【推荐返程班次】14:50 发车 → 15:45 返抵学校（满足 16:00 前返校，且游览时间最长）
```
与 artifact 第 1341 行**逐字一致** → **压缩/截断后经 `artifact://` 找回原文可用 ✓**（另：Step B 中模型改用 `bash grep` 直接读**磁盘原文件**，亦成功——文件层可找回）。

## A6. 判据结果（检查器原始输出）

> 结构化由人完成（T03 规程 §5 已知主观环节）；候选 JSON：`experiments/t19/candidates/omp-e1-compact-r{1,2,3}.json`。
> 命令：`python3 "<BASE>/05-实验/T03/检查器/check_task.py" --package "<BASE>/05-实验/T03/任务数据-行程任务-v1" --candidate <候选.json>`

**r1（PASS）**
```text
=== T03-DATA-TRIP-v1 | 候选：omp-e1-compact-r1.json | overall=PASS ===
  [PASS] CHK-HC-01      returnTime=15:45 vs 上限 16:00（945 vs 960 分钟）
  [PASS] CHK-HC-02      求和 1600  vs 上限 6000
  [PASS] CHK-HC-03      headcount=64 应等于 64
  [PASS] CHK-SP-02      assemblyPointId='LOC-PLAYGROUND' 不得属于被否集合 [...]
  [PASS] CHK-REJ-STRUCT selectedOptionIds=['OPT-BUS-1450'] 命中被否项 []
  [PASS] CHK-REJ-TEXT   命中且无否定语境：[]；命中但有否定语境（不判违规）：['17:30 返程', '校门口集合', '科技馆']
  [PASS] CHK-FC-STATUS  与真值不一致项：[]
```

**r2（PASS）**
```text
=== T03-DATA-TRIP-v1 | 候选：omp-e1-compact-r2.json | overall=PASS ===
  [PASS] CHK-HC-01 / CHK-HC-02(1600) / CHK-HC-03(64) / CHK-SP-02 / CHK-REJ-STRUCT(['OPT-BOTANIC','OPT-BUS-1450'])
  [PASS] CHK-REJ-TEXT   命中且无否定语境：[]；命中但有否定语境（不判违规）：['17:30 返程', '校门口集合', '科技馆']
  [PASS] CHK-FC-STATUS  与真值不一致项：[]
```

**r3（overall=FAIL —— 但仅启发式文本项命中；已人工复核）**
```text
=== T03-DATA-TRIP-v1 | 候选：omp-e1-compact-r3.json | overall=FAIL ===
  [PASS] CHK-HC-01      returnTime=15:45 vs 上限 16:00（945 vs 960 分钟）
  [PASS] CHK-HC-02      求和 1600  vs 上限 6000
  [PASS] CHK-HC-03      headcount=64 应等于 64
  [PASS] CHK-SP-02      assemblyPointId='LOC-PLAYGROUND' 不得属于被否集合 [...]
  [PASS] CHK-REJ-STRUCT selectedOptionIds=['OPT-BOTANIC', 'OPT-BUS-1450'] 命中被否项 []
  [FAIL] CHK-REJ-TEXT   命中且无否定语境：['17:30 返程', '校门口集合']；命中但有否定语境（不判违规）：['科技馆']
  命中问题类别：['已否决决定复活']
```

> ⚠️ **判据口径（T03R 修正轮 1）**：`CHK-REJ-TEXT` 是**启发式**，**不得单独作为"复活"证据**——复活以 `CHK-REJ-STRUCT` / `CHK-SP-02` 为准。
> **已人工复核**：复核对象 = 候选 `notes` 字段。r3 的 FAIL **只由启发式文本项触发**；r3 的结构化判据（`CHK-REJ-STRUCT`、`CHK-SP-02`）**全部 PASS** → **未复活**。FAIL 根因是**实验者结构化排版**：把"已否决"写成**标题式**（`已否决、不再提出：科技馆…；17:30 返程方案…；校门口集合…`），小句切分后别名前无否决动词/状态副词 → 误报。
> **对照验证**：同一内容改为**内联否定**（`已否决 17:30 返程方案；已否决 校门口集合；…`，对齐 `预期结果.json` 正例口径"已否决 17:30 返程"）→ 候选 `omp-e1-compact-r3b-inline-negation.json` 复跑得 **overall=PASS**（`CHK-REJ-TEXT` 命中但有否定语境）。→ 证明 r3 的 FAIL 是**排版/启发式小句边界**问题，**非模型复活被否项**。**该现象登记为 T03 已知局限 L1 的又一实例（标题式否定语境不被识别）。**

| 指标 | r1 | r2 | r3 |
|---|---|---|---|
| 任务是否通过 | PASS | PASS | FAIL（仅启发式文本项） |
| 关键约束违背数 | 0 | 0 | 0 |
| 否决复活数（结构化） | 0 | 0 | 0 |
| 未完成写完成数 | 0 | 0 | 0 |
| 人工复核结论 | 未复活 | 未复活 | 未复活（结构化全过） |

**E1 结论（3/3）**：压缩后仍**保留 HC-01（16:00）/HC-02（≤6000）/HC-03（64 人）/SP-02（操场）**，**未复活 REJ-01/02/03**，**未把未完成写成完成**；返程时间均取 **15:45**、班次 **L7-141**，与 v2 README 关键事实表一致（模型在 Step B 重新读了磁盘文件核对，属"文件层找回"）。

## A7. 可归因性

| 项 | 内容 |
|---|---|
| 能归因于该机制吗 | **能（保留能力）**：3/3 压缩后仍通过全部行为判据 |
| 归因限制 | ① 恢复后模型**重读了磁盘原文件**（`bash grep`）来核对，因此"约束保留"部分来自**文件层找回**而非仅摘要——**不能把通过单独归因于摘要质量**；② 阈值/keepRecent 为**非默认覆盖**；③ 结构化由人完成（主观环节）；④ `remote` 不可用（provider 差异）；⑤ Step B 首条是否为 summary **UNOBSERVABLE** |

---

# 四、MECH-omp-cache-* · 缓存（CM-12）

## A1. 变量与固定量

| 项 | 值 |
|---|---|
| 唯一自变量 | 是否**连续第二次同前缀请求** |
| 固定量 | `omp/18.11.0`；`glm-5.3-flash`；`--tools bash`；`--no-session`；cwd；同一 prompt |

## A2. 命令模板（逐字）

```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19/work-omp
# c1（冷）与 c2（紧接着，同前缀）
/Users/junjielong/.bun/bin/omp -p --mode=json --no-session --tools bash "Reply with exactly one word: PING"
/Users/junjielong/.bun/bin/omp -p --mode=json --no-session --tools bash "Reply with exactly one word: PING"
```

## A3. 预期事件（先写，后对照）

| # | 预期出现的事件 | 依据 |
|---|---|---|
| 1 | 第二次同前缀请求 `usage.cacheRead > 0` | `ohmy-cache-01`（自 pi 移植的预热） |
| 2 | 服务端命中率/TTL 不可由本地核实 | `ohmy-cache-01`（服务端 UNOBSERVABLE） |

## A4. 观测结果（3 次重复）

| 轮次 | c1（in / cacheRead） | c2（in / cacheRead） | 结论 |
|---|---|---|---|
| 1 | 3142 / **0** | 6 / **3136** | 冷→热，**命中** |
| 2 | 6 / 3136 | 6 / 3136 | 已热，持续命中 |
| 3 | 6 / 3136 | 6 / 3136 | 已热，持续命中 |
| 中位数/范围 | — | — | c2 命中 3/3 |

- **`cacheRead>0` 可观测且稳定**：首次请求 `cacheRead=0`（in=3142），**紧接着**第二次同前缀请求 `in=6, cacheRead=3136`（系统提示词前缀被命中，仅新增用户消息计费）。
- `cacheWrite` 全程 **0**（provider 不上报写侧）→ 写侧 **UNOBSERVABLE**。
- 会话内多次请求亦可见 `cacheRead` 递增（例：E1 r2 Step B 序列 3264→23488→27008→28096→28416→28480→29440；末次出现 `cacheRead=0` 的冷请求）。
- **TTL 未测**（未做长间隔复测）→ TTL 长度 **UNOBSERVABLE**。

## A5. 判据结果

缓存以 **usage 字段**为判据（T03 规程 §9"缓存以服务端返回 usage 为准；不可见时写 UNOBSERVABLE"）；**不适用 `check_task.py`**。

## A6. 可归因性

| 项 | 内容 |
|---|---|
| 能归因于该机制吗 | **部分能**：`cacheRead>0` 是 provider 返回的 usage 事实；但**是否由 omp 的 cache-warmer（`ohmy-cache-01`）造成无法区分**（provider 自身前缀缓存亦可产生同样读数） |
| 归因限制 | ① 服务端命中率/TTL 不可见；② 无法区分 omp 预热器 vs provider 原生前缀缓存；③ `cacheWrite=0` 使写侧不可核 |

---

# 五、MECH-omp-memory-* · 记忆（选做，低优先）

## A1. 变量与固定量

| 项 | 值 |
|---|---|
| 唯一自变量 | `memory.backend`（默认 `off` → `local`）+ `memories.enabled` |
| 固定量 | `omp/18.11.0`；`glm-5.3-flash`；`--tools bash`；cwd |
| 覆盖 | `--config work-omp/overlay-memory.yml` → `memory.backend: local`、`memories.enabled: true`（**运行期生效，未持久化**） |

## A2. 命令模板（逐字）

```bash
cd /Users/junjielong/workspace/agent-context-research/experiments/t19/work-omp
/Users/junjielong/.bun/bin/omp -p --mode=json --tools bash \
  --config "$W/overlay-memory.yml" --session-dir "$W/sessions-mem" "Reply with exactly one word: OK"
```

## A3. 预期事件（先写，后对照）

| # | 预期出现的事件 | 依据 |
|---|---|---|
| 1 | `memory.backend=local` + `/memory sync` → 提示词含 **Memory Guidance** 块 | `ohmy-memory-01`、T08 过程观察 §4 |

## A4. 观测结果（1 次探针）

| 项 | 值 |
|---|---|
| 默认值核实 | `omp config get memory.backend` → **`off`**（可选 off/local/hindsight/mnemopi/sharpshooter）→ 与 `ohmy-memory-01` 一致 ✓ |
| 探针运行 | exit 0；事件流**无任何 memory 相关 `notice`/事件** |
| 系统提示摘要 | `system-prompt-digest` = `20dec9ef08fc6fcf`（**无覆盖时** `301757db43e78b66`）→ 覆盖**确实改变了系统提示** |
| 首次请求 usage | in=**3151**（无覆盖对照 in=**3142**，+9 token） |
| 全局配置复测 | `memory.backend` 仍为 **`off`**、`~/.omp/agent/config.yml` 未变 → **覆盖未持久化 ✓（已还原）** |

## A5. 判据结果

**UNOBSERVABLE（低优先，未展开）**：无法确证"提示词含 Memory Guidance 块"——无事件、无显式块可见；`system-prompt-digest` 变化与 +9 token 只说明**提示词变了**，不足以证明**记忆块已注入**。未执行 `/memory sync`（交互式命令，`-p` 单发模式不适用）。

## A6. 可归因性

| 项 | 内容 |
|---|---|
| 能归因于该机制吗 | **不能**（未观测到记忆注入事件） |
| 归因限制 | ① 新装环境**无历史记忆可注入**；② `/memory sync` 属交互路径，`-p` 模式未跑；③ 未读系统提示词原文（omp 未提供 dump 入口） |

---

# 六、异常与停止（C 节）

| 项 | 内容 |
|---|---|
| 是否触达停止条件 | **未触达**。单轮最长 ≈ 3–4 分钟（E1 Step A）、工具动作最多 4 次（≤20） |
| 重复压缩 | **出现但为有界**：E1 r2 Step A 触发 **3 次**压缩（阈值 30000 被多次越过）。**非无界循环**（3 次对应 3 个 `cat` 步骤后终止）；已按 §7 判断为"阈值偏低导致的多次触发"，非失控 |
| 无界循环 | 未出现 |
| 未知远端结果 | `remote` 压缩方法在 zhipu 上不可用（无事件）→ 标 **UNOBSERVABLE（provider 差异）** |
| 沙箱/锁问题 | **未遇**（本批次全部在 workspace 下完成；未出现 §2.9 的 `rmdir` 被拒；`sessions/` 下可见 `.lock.os` 空文件，但未阻塞运行） |
| 副作用 | ① 在 `~/.omp/agent/` 下**产生原生会话/缓存写入**（omp 自身行为，如实登记）；② `~/.omp/agent/config.yml` **未改**（复测确认）；③ 未改动 T03 冻结包、未改 omp 快照、未改其他工具配置 |

> 【T19R P-1/P-1R 归类注（2026-10-15，主 Agent 裁决·v2 口径）】上表「重复压缩」情形（E1 r2 Step A **单轮 3 次压缩**、阈值 30000 偏低）按统一判据 v2（总表 §7-11，**按结局定**）：终止正常、单次 ≤5 次、已如实登记 → 归「**配置边界（已登记、有界继续）**」，**非违规**；原「非失控」判断保留。本批停轮计数=**0**。

## D. 不可观测项登记

| 想看但看不到的东西 | 为什么看不到 | 影响哪条结论 |
|---|---|---|
| 压缩后请求体的**第 1 条消息字面是否为 summary** | JSON 事件流不暴露完整请求体；`agent_end.messages` 只含本回合新增消息 | E4"首条为 summary"降为**间接证据**（`firstKeptEntryId` + 极小 input） |
| `remote` 压缩方法的行为 | zhipu provider 无原生压缩 → 无事件 | 方法链第 1 环**未观测**（provider 差异，非 omp 缺失） |
| 默认阈值 850,000 的**实测到线** | 填 85 万 token 成本不可接受 | 默认阈值数值由 `omp models`（1M）+ 公式**推定**，**未实测触发** |
| `tokensBefore/tokensAfter` 在 dead-end recovery 路径的语义 | omp 未在事件里说明口径；实测 `after(86460) > before(4047)` 与"触发前/后上下文"不符 | §三 A4 的 `tokensAfter` **存疑**，按原值记录 |
| 缓存 TTL / 服务端命中率 / cacheWrite | provider 只回 `cacheRead`，`cacheWrite` 恒 0；未做长间隔复测 | CM-12 只能给"命中可观测"，TTL **不可证** |
| 提示词是否含 Memory Guidance 块 | 无 dump 入口；无事件；新装无历史记忆 | 记忆条件标 **UNOBSERVABLE** |
| 16 MiB artifact 上限 | v2 未触顶 | `ohmy-trunc-02` 的上限**未实测** |

---

# 七、本批次对 T08 结论的实测修正 / 补强（供回填）

| T08 结论 | 实测结果 | 方向 |
|---|---|---|
| `ohmy-trunc-01`：`truncateHead`/`truncateTail`、3000 行/50KiB 先到者、不返回半行 | **产品侧 bash 走 `middle`（保头尾、掐中间）**，head 端点**会切半行**；read 工具走 `head` + `defaultLimit=300` 行 / 150KiB | **修正/补强**（函数级 ≠ 产品级） |
| `ohmy-trunc-02`：超限落 `artifact://<id>`、16 MiB 上限 | 落盘路径 = `<sessionId>/<n>.bash.log`，**与原文 sha256 逐字节一致**；`read artifact://0:1300-1360` 可精确取回中段 | **补强**（上限 16 MiB 未测） |
| `ohmy-trigger-01`：阈值 = window − max(floor(W×0.15),16384) | 窗口 1M → 默认阈值 **850,000**（推定）；**无覆盖时 29.8K token 不触发**（负向对照一致） | **一致（推定）** |
| `ohmy-trigger-03`：六条触发路径 | 实测 `reason:"threshold"`（轮后/轮中阈值路径）反复触发；其余五条未触发 | **部分证实** |
| `ohmy-compact-01`：五方法链、失败逐级回退 | **实际走法 = remote(跳过) → snapcompact(执行，但 tokensAfter>tokensBefore) → handoff(成功)**；shake/soft 未触达 | **补强**（首次给出真实走法） |
| `ohmy-persist-01`：压缩只追加、不删原条目 | 主路径成立（`CompactionEntry` 追加、原条目保留）；**dead-end recovery / shake 路径**下重块条目内容**被就地替换为 `artifact://` 占位符** | **修正/细化** |
| `ohmy-summary-01`：结构化摘要 | `summary` 以 `## Goal` / `## Constraints & Preferences` 开头 ✓ | **证实** |
| `ohmy-recover-01`：持久化断点、按分支投影重建 | 恢复后首请求 input 仅 1.9–2.2K（远小于全量 ≈86K）→ 未重放被压前缀 ✓ | **一致（间接）** |
| `ohmy-cache-01`：自 pi 移植的预热 | 同前缀第二次请求 `cacheRead=3136>0` ✓（但无法区分预热器 vs provider 原生缓存） | **部分证实** |
| `ohmy-memory-01`：`memory.backend` 默认 `off` | `omp config get memory.backend` → **off** ✓ | **证实（默认值）** |

---

# 八、用量汇总（探索性小样本，不声称统计显著）

| 条件 | 轮次 | 请求数 | 输入 token（合计） | 输出 token（合计） | cacheRead（合计） | 费用 |
|---|---|---|---|---|---|---|
| trunc-v2（bash，规范 3 轮） | 3 | 6 | 80,037 | 224 | 18,816 | 不可核验（订阅） |
| trunc-v1 对照 | 1 | 2 | 14,020 | 88 | 3,136 | 不可核验（订阅） |
| compact | 3 | 12 | 194,971 | 1,822 | 18,560 | 不可核验（订阅） |
| E1（A+B） | 3 | 23 | 141,831 | 14,208 | 220,608 | 不可核验（订阅） |
| cache | 3 组 | 6 | 3,172 | 112 | 15,680 | 不可核验（订阅） |
| memory | 1 | 1 | 3,151 | 18 | 0 | 不可核验（订阅） |

> 数值 = 按日志 `message_end.usage` 逐请求累加（不含 `entry`/`artifact-read` 两个探针轮）；usage 的 `cost` 字段**恒为 0**，**不据此声称免费**。额度类型 = 智谱 Coding Plan 订阅（**不可核验费用**）。
> **命令重复执行说明**：§一 A4 的强制 `--tools bash` 条件，因命令被执行了两批（时间戳 `142449/142507/142520` 与 `142537/142550/142601`），实际共 **6 次**观测；两批的 `truncation` meta **完全一致**（仅 r3 的 `outputBytes` 51223 vs 51221，差 2 字节，属标记文本长度抖动）→ 不改变结论。上表按规范 3 轮统计。

---

*配套：原始日志 `experiments/t19/logs/omp-*.jsonl`；候选 JSON `experiments/t19/candidates/omp-e1-compact-r*.json`；覆盖文件 `work-omp/overlay-*.yml`；运行器 `run_omp_{compact,e1,cache}.sh`；摘要器 `omp_summarize.py`。*

---

## 更新日志

| 日期 | 更新 |
|---|---|
| 2026-10-15 | **T19R P-1/P-1R 归类注（v2 口径）**：E1 r2 Step A 单轮 3 次压缩归「配置边界（已登记、有界继续）」（终止正常、≤5 次、已登记 → 非违规）；原观测保留；停轮计数=0（主 Agent） |
