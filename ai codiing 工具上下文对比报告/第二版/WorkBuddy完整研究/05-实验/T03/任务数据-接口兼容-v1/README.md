---
packageId: T03-DATA-COMPAT-v1
version: v1
frozenAt: 2026-10-15
frozen: true
task: T03
synthetic: true
modelCallsRequired: false
---

# 任务数据包 · 接口兼容迁移 v1

> **这个包解决什么**：给 T18（迁移题）、T19（重启恢复 / 压缩后约束保留实验）和 T03 检查器提供一份**冻结、可复现、不依赖真实模型**的 coding 迁移任务数据。对应第二版方案 §1.4 / §6.3：修改一个简单接口且保持旧客户端兼容，经过**读文件 → 长日志 → 测试 → 压缩 → 隔天恢复**。
>
> **纪律**：全程合成；v1 冻结后不原地修改；不含任何凭据、私钥、真实仓库或生产数据。

## 1. 包内文件

| 文件 | 解决什么问题 |
|---|---|
| `任务定义.json` | 任务目标、约束索引、失败模式、检查项、测试真值 `groundTruthStatus`（testsPassed=false 等） |
| `约束清单.json` | 3 条硬约束（不删/不改名字段、不改路径、新字段须可选）+ 1 条流程约束（隔天恢复先验证）+ **3 条已否决决定**（重命名 user_name / 新增 v2 路径 / age 改 string） |
| `消息序列.jsonl` | 13 条带 `MSG-Cxxx` ID 的多轮消息：读文件 → 3 次否决 → 跑测试 → 整理触发 → **隔天恢复（MSG-C012 要求先重述有效约束）** |
| `长工具结果-测试日志-v1.txt` | **300 行**契约测试日志：**头（测试启动、计划 42 条）、中（149–156 行 `displayNameShouldBeOptional FAILED`）、尾（结论：Tests run 42 / Failures 1 / BUILD FAILURE / 未提交）** |
| `工具结果-接口定义.json` | 读文件结果：现状字段与旧客户端契约文档摘要 |
| `坏摘要样例.md` | **故意漏掉兼容硬约束、复活 3 条被否改法、把测试未通过写成全部通过**的整理产物，附 D1–D5 缺陷标注 |
| `预期结果.json` | 检查器行为清单（8 条检查项 + 正反例预期结论） |
| `manifest.sha256` | v1 文件哈希登记 |

## 2. 关键事实「头 / 中 / 尾」分布（可核对）

> **行号口径**：下表「文件行号」= 日志文件的**第 N 行（1 起）**，**不是**测试用例编号。引用时请带文件行号。
> 本节行号已由 `scripts/locate_keyfacts.py` 实测校订（原先误把行号写成 296/297/300，实测为 **292/293/298**）。

| 位置 | 文件行号 | 关键事实 | 若只保留头尾会怎样 |
|---|---|---|---|
| 头 | 3 | 任务：新增可选字段 displayName，旧客户端须可用 | 任务目标线索 |
| 头 | 9 | 计划测试总数 42 | 无法判断尾部 "Failures: 1" 的分母 |
| 中 | **150** | **`UserContractV1Test > displayNameShouldBeOptional FAILED`** | 头尾裁剪删中间 → 真正的原因最先死 |
| 中 | 151 | expected: field 'displayName' to be OPTIONAL (nullable=true) | 修复方向 |
| 中 | 152 | actual: field 'displayName' is REQUIRED (nullable=false) | 修复方向 |
| 中 | 153 | 契约影响：旧客户端无法解析未知必需字段 | 为什么这是硬约束 |
| 尾 | 292 | `Tests run: 42, Failures: 1, Errors: 0, Skipped: 0` | 统计结论 |
| 尾 | 293 | `BUILD FAILURE` | 构建结论 |
| 尾 | 296 | 结论 1：旧客户端契约测试未通过；displayName 被标为 REQUIRED | 结论重述 |
| 尾 | 298 | 结论 3：变更**尚未提交**（working tree dirty） | 完成状态真值（`testsPassed=false` 的书面依据） |

**核对方式（推荐用脚本，不靠手数）**：
```bash
python3 <工作区>/scripts/locate_keyfacts.py <本包目录的上一级>
```
手工核对：`sed -n '1,12p;148,156p;289,300p' 长工具结果-测试日志-v1.txt`（行号在同一冻结版本内固定）。

## 3. 怎么用（不调用模型）

```bash
python3 <检查器目录>/check_task.py --package "<本包目录>" --self-test
```

- 明确预期：**9 个用例** = 2 个正例（PASS）、6 个反例（FAIL）、1 个回归样例（FAIL，对抗例 G 缺字段空真）。
- 判据使用口径见 `预期结果.json#knownLimitations`：`CHK-REJ-TEXT` 为启发式，**不得单独作为复活证据**。
- 隔天恢复场景的检查入口：候选方案若声明 `testsPassed=true` 而真值为 false → 判「未完成被写成完成」。

## 4. 边界与未决项

- 语言/框架仅作**扩展示例**（Java/Spring 风格命名），检查器**不依赖**任何 Java 工具链；不运行真实构建。
- 「恢复后必须先验证约束」是流程型约束（HC-04），当前不由检查器自动判定，需要候选方案在 `notes` 中体现；是否可自动化的结论留给 T19 观察后回填。
- 日志是真值来源，不是真实 CI 输出；不得据此推断任何真实构建行为。
