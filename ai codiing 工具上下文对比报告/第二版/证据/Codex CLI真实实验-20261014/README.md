# Codex CLI 上下文管理：真实实验复现包

这套实验让你实际看到四件事：同一段历史能否命中缓存，自动压缩后任务能否继续，手动 `/compact` 后是否等待新指令，以及长工具输出的中间内容是否被裁掉。

本次观察日期为 **2026-10-14**，运行 **Codex CLI 0.152.0**、**gpt-5.6-sol**、**low** 推理强度，使用已有的 **ChatGPT 登录**。教程正文的源码讲解固定于提交 `a07c8ebd`，这里的已安装 CLI 是另一版本；两者的相同现象和版本差异分别记录，不把运行结果倒推成旧快照的源码事实。

先看 `observed/` 中整理过的实际证据，再运行脚本生成自己的 `artifacts/`。验收的是事件、标记和任务行为，**不用得到与本次完全相同的 token 数或耗时**。

你先让 Codex 读资料，完成后再追加一个核对问题：保存这段聊天的是**会话（thread）**，每次指令从开始到结束是一**轮任务（turn）**。一轮内可能多次问模型、运行工具。`rollout.jsonl` 是这次会话一行一条的本地记录；整理后额外写下以后采用的材料，叫**整理检查点**。本包的 `app-server` 是真实 CLI 提供给程序的接口，方便脚本记录事件；手动实验仍在真实终端输入 `/compact`。

## 1. 先准备一张独立的实验桌

需要本机已有 `codex` 和 Python 3.10 或以上版本，已经登录 ChatGPT。`manual_tui.py` 使用 PTY，适用于 macOS / Linux。先把实验包解压或复制到项目与笔记库之外的新目录，例如 `~/workspace/codex-context-lab`。避免继承现有项目的 AGENTS、工具与规则。然后在终端 `cd` 到这个 README 所在的目录，再运行：

```sh
export CODEX_LAB_HOME="$(mktemp -d /tmp/codex-context-lab.XXXXXX)"
export CODEX_LAB_MODEL=gpt-5.6-sol
python3 setup_runtime.py
```

`CODEX_LAB_HOME` 是本次 CLI 的独立运行目录。把它放在 `/tmp` 等本机临时目录，避免把登录关联和新会话放进 iCloud 同步目录。准备脚本只为独立目录建立登录引用；不要打开、复制或展示认证文件。

查看实际版本、登录状态和该模型是否可用：

```sh
codex --version
CODEX_HOME="$CODEX_LAB_HOME" codex login status
CODEX_HOME="$CODEX_LAB_HOME" codex debug models
```

本次版本输出是 `codex-cli 0.152.0`。如果你使用另一版本，把输出记在自己的结果旁；如果模型列表中没有 `gpt-5.6-sol`，先把 `CODEX_LAB_MODEL` 设为账户实际支持的模型，再记录这项差异。

接着做一次短预检：

```sh
CODEX_HOME="$CODEX_LAB_HOME" codex exec --json --skip-git-repo-check -C workspace -s read-only -m "$CODEX_LAB_MODEL" -c model_reasoning_effort='"low"' '不要使用工具，只回复 EXPERIMENT_READY'
```

看到 `EXPERIMENT_READY`，并确认本次执行成功结束，再继续。它验证了登录、模型、目录和一次真实请求；后面的压缩、裁剪和缓存仍要各自验证。

**工作资料都是人工构造的测试内容。** `workspace/` 约 200 KB，包含三份约 19.7 KB 的读取资料、独立规则，以及 `long-output.txt`。长文件是 **136,009 字节、1,602 行**，开头、中间、末尾分别埋了不同标记，方便判断哪部分进入了模型可见的结果。

可以检查下载内容是否完整：

```sh
shasum -a 256 -c SHA256SUMS.txt
```

Linux 上也可以用 `sha256sum -c SHA256SUMS.txt`。如果校验失败，先恢复包内文件，再做实验；运行输出保存在 `artifacts/`，不要把它与下载前的 `observed/` 混淆。

## 2. 先验证缓存：只追加问题，保持历史

```sh
python3 run_lab.py cache
```

脚本在独立运行目录中新建一个线程，连续发三条短指令，不使用工具。第一条给出三项事实，后两条只要求重新核对：

```json
{"RETURN_BY":"16:00","BUDGET_CNY":1280,"MEETING_POINT":"东门"}
```

用量与结果在 `artifacts/cache/results.json`，协议事件在 `artifacts/cache/events.jsonl`。对比同一线程三次普通调用的 `usage[].last`，主要看 `inputTokens` 和 `cachedInputTokens`。

本次观察值如下：

| 调用 | 输入 token | 已缓存输入 token | 可以从中读出的结论 |
| --- | ---: | ---: | --- |
| 第 1 次 | 11,934 | 0 | 本次请求没有报告缓存读取 |
| 第 2 次 | 14,076 | 11,776 | 部分输入实际命中了缓存 |
| 第 3 次 | 14,127 | 13,952 | 更多输入实际命中了缓存 |

第二次约 83.7%、第三次约 98.8% 的输入被报告为已缓存。输入比你的三行 JSON 大，因为 CLI 还组装了运行规则、工具定义等内容。`cachedInputTokens` 属于 `inputTokens`，不能再加一次。`total` 是累计用量，也不能拿它当某一次请求的输入大小。

你的第一轮也可能命中已有缓存，后两轮也可能没有命中。**命中的证据是响应中的数值，而不是回答更快、内容一样或前缀看起来相同。** 这套 ChatGPT 登录实验也不能直接推出 API 账单金额。

运行下面的只读检查可打印每次调用最后一条用量，不展示认证或隐藏内容：

```sh
python3 - <<'PY'
import json
from pathlib import Path
result = json.loads(Path('artifacts/cache/results.json').read_text())
for index, run in enumerate(result.get('runs', []), 1):
    usages = run.get('usage', [])
    print('调用', index, '状态', run.get('turn', {}).get('status'))
    print('最近用量', usages[-1].get('last') if usages else '没有用量通知')
PY
```

## 3. 在真实输入框输入 `/compact`

先完成上一节；手动脚本恢复的就是你刚才创建的 cache 线程。

```sh
python3 manual_tui.py
```

这不是发送一条“请压缩”的普通聊天消息。脚本启动真正的 Codex TUI，在终端输入框键入 `/compact` 并回车，观察本实验线程的整理检查点。整理检查点安装完成后，保持 **6 秒**没有新用户指令，再输入一条新的“三约束核对”请求。

查看 `artifacts/manual-tui/results.json`、`terminal-readable.txt` 和前后 rollout 文件。验收顺序是：

1. 输入记录中能看到字面量 `/compact` 及回车。
2. 整理后检查点数量比之前增加，记录里有 `compacted`。
3. 安静的 6 秒里没有新增用户消息；本次也没有新增任务记录。
4. 新的核对指令发出后，一轮新任务结束，最终 JSON 保留三项事实。

本次观察是 **0 个 → 1 个检查点**，6 秒内记录增长 **0**，新指令之后成功回答。新请求也会重新注入含有三项约束的 AGENTS，所以“答对三项”不能单独证明它们由压缩块保留。这支持“手动整理结束后，继续工作需要新的用户指令”在本例中的表现。6 秒只是观察区间，不是压缩时限；单看等了 6 秒不能判定整理成功。

如果希望亲自操作，可代替脚本执行以下命令。先从你新生成的结果中只取线程 ID：

```sh
LAB_THREAD_ID="$(python3 - <<'PY'
import json
from pathlib import Path
result = json.loads(Path('artifacts/cache/results.json').read_text())
print(result['start']['thread']['id'])
PY
)"
CODEX_HOME="$CODEX_LAB_HOME" codex resume "$LAB_THREAD_ID" --no-alt-screen -m "$CODEX_LAB_MODEL" -s read-only -a never --strict-config -c model_reasoning_effort='"low"' -c model_context_window=100000 -c model_auto_compact_token_limit=90000 -c model_auto_compact_token_limit_scope='"total"' -c check_for_update_on_startup=false
```

如果 CLI 询问是否信任目录，核对它是本实验的合成资料目录。进入输入框后，亲自键入 `/compact`、回车，等待界面报告整理完成；**从完成时开始**观察 6 秒，再输入：

```text
不要使用工具。请从刚才整理后的上下文核对 RETURN_BY、BUDGET_CNY、MEETING_POINT，输出这三项的 JSON。
```

人工操作与 `manual_tui.py` 是两种复现方式；人工方式的终端观察不会自动生成脚本的全部采集文件。

## 4. 让 CLI 自己触发压缩

```sh
python3 run_lab.py automatic
```

本例配置 `model_context_window=100000`、`model_auto_compact_token_limit=22000`、`model_auto_compact_token_limit_scope="total"`，目的是在很小的合成任务内观察到事件。**22,000 是本次主动设置的实验阈值，不是 Codex 的通用默认值。**

脚本只发送一次用户任务，让模型按 A → B → C 顺序分别读取三份文件，然后提交 JSON。runner 不发 `thread/compact/start`，也不输入 `/compact`。检查 `artifacts/automatic/events.jsonl` 和 `results.json`，按顺序找：

1. 唯一一次 `turn/start` 和三次实际读取命令。
2. `contextCompaction` 的开始、完成通知，以及 rollout 中的 `compacted` 检查点。
3. 压缩后出现同一任务的最终回答，`turn/completed` 状态为 `completed`。
4. 最终 JSON 包含三份文件名、三项硬约束和三个尾部标记。

本次压缩发生在 **三次读取之后、最终 JSON 之前**。因此这次直接证明了“自动压缩后，原任务继续完成最终回答”；它没有直接证明“压缩后又继续执行剩余工具”，因为本次工具已经全部读取完毕。

三个尾部标记分别是 `NONCE_3B94A2585BC1`、`NONCE_F18624E3CD52`、`NONCE_575B2680BF92`，可与 `workspace/context-*.txt` 核对。观察整理前后的输入时，要把普通模型请求、压缩操作和累计用量分开；新请求内容不同，输入差值也不能一概叫“压缩净省了多少”。

`thread/read` 中仍然存在旧轮属于显示历史。它不等于后续请求仍然携带所有旧消息。压缩替换的直接证据在本实验 rollout 的检查点和 `replacement_history`；不需要扫描其他私人会话。

## 5. 看长输出怎样被裁剪

```sh
python3 run_lab.py truncation-call
```

这个实验只允许一次 `cat long-output.txt`，并要求该次调用明确设置 `max_output_tokens=128`；禁止通过 `grep` 或再次读取中间位置找回标记。

完整文件中有：

```text
HEAD_MARKER=ALPHA_20261014
MIDDLE_MARKER=RETURN_BY_16_00_SECRET_P7
TAIL_MARKER=OMEGA_20261014
```

本次模型实际回答：

```json
{"head_marker":"ALPHA_20261014","middle_marker":"UNKNOWN","tail_marker":"OMEGA_20261014","saw_truncation_marker":true}
```

对照 `artifacts/truncation-call/` 的命令、工具条目和模型回答，先确认这次工具确实使用了 128 的预算，再看裁剪标记与首尾内容。这里的 `SECRET_P7` 只是合成测试标记，不是账户凭据。

**这一例直接验证显式调用预算下的裁剪。** 这次安装版本使用了 CodeMode 工具包装，不能只凭页面看到了省略号就认定所有内部层都按同一个数裁剪；UI 展示的完整/聚合输出与下一次模型请求中的输出也要分别核对。

可选追加一组实验：

```sh
python3 run_lab.py truncation-config
```

它将配置级 `tool_output_token_limit` 设为 **256**，而调用仍要求 **60,000**。用它观察两层预算的关系。**本次虽然同样看到首尾保留、中间标记缺失，但没有充分证明内部各层最终精确钳制到 256**。因此不能把此组写成“配置 256 必然把所有输出压到 256”；应保留工具包装、实际调用参数、记录字节数和后续请求的差异，继续查对应版本源码。

## 6. 自己的日志怎样读、怎样保存

每个 app-server 模式通常生成：

| 文件 | 用途 |
| --- | --- |
| `results.json` | 实际线程设置、轮状态、用量、工具和回答的集中结果 |
| `events.jsonl` | 带时间的发送与接收事件；可核对是否显式发了压缩请求 |
| `stderr.txt` | 运行错误和诊断信息 |
| `rollout.jsonl` | 仅这个新实验线程的本地历史；用于核对检查点与工具结果 |

手动 TUI 另有原始终端、可读终端及整理前、整理后、安静期、新指令后的记录。先看集中结果，再循着线程和轮 ID 回到关键事件，不需要从头读所有 JSON 行。

`observed/` 是本次已经挑选、整理过的公开证据。你运行后生成的 `artifacts/` 是个人原始记录，可能包含本机路径、线程标识和不透明的压缩数据。公开时另做摘录：保留设置、时间、条目类型、首中尾标记和普通回答；不要直接公开认证、完整不透明压缩块或未经检查的全部原始记录。

最后可以解除本次脚本创建的登录引用：

```sh
python3 setup_runtime.py --cleanup
```

它只清理本脚本建立的认证软链接。保留实验记录以便复核；独立运行目录的生命周期由你自行管理。

## 7. 现象没出现时，先检查哪一步

| 现象 | 先查证据与处理 |
| --- | --- |
| `EXPERIMENT_READY` 没出现 | 先看登录状态、实际模型列表和该次错误，确认请求完成；不要继续把后续模式当有效实验 |
| `gpt-5.6-sol` 不可用 | 选账户实际支持的模型，用 `CODEX_LAB_MODEL` 明确记录；版本、窗口和行为变化也写入结果 |
| 缓存是 0 | 确认三轮同一线程、没改模型/规则，保存实际 usage；缓存命中受运行条件影响，0 本身是有效观察 |
| 自动任务没有压缩 | 核对实际配置、工具是否真的依次读完、输入是否增长到实验阈值；没事件就记录“本次未触发” |
| 自动模式失败或超时 | 看 `turn.status`、错误和最后事件；保留这一轮，不把局部工具成功写成整个任务成功 |
| 手动脚本说没有检查点 | 先确认 cache 线程已生成、同一 `CODEX_LAB_HOME` 能恢复它、TUI 真正收到了 `/compact`；必要时按人工步骤复现 |
| TUI 弹更新提示 | 本例禁用了启动检查，脚本会停止记录异常；不要在实验中更新 CLI，以免两次运行条件变化 |
| 中间标记竟然出现 | 检查调用预算是否真实为 128、模型是否换了工具或重复读取；以记录为准，不能只按预期填写 UNKNOWN |
| 只看到完整终端输出 | 分清 UI 聚合结果与模型可见工具条目，继续对照本实验 rollout；完整显示本身不能证明没有裁剪 |
| 校验和不一致 | 先恢复下载文件；生成日志属于 `artifacts/`，不应修改原 `observed/` 或测试资料 |

这套复现的合格结果是：你能说明实际用了哪些条件，指出每项结论对应的事件或条目，并把已经证明的行为与仍需查源码的部分分开。
