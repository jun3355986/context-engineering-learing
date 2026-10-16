---
title: T05 · Claude Code CLI 证据卡索引
task: T05
tool: claude-code-cli
created: 2026-10-15
status: SUBMITTED（待 T07 独立复核）
---

# 证据卡索引（结论ID `claude-*`）

> 格式按任务书 §4.4。**证据等级**：①官方文档/发布说明（承诺行为）｜②官方分发件/本地 CLI 可观测项（标观察方法）｜③社区线索。
> 闭源工具**没有**"源码证据"这一档；凡涉及实现处一律标 ①/②/③ 并写"不能证明"。

| 结论ID | 一句话结论 | 等级 | 关联机制/问题 | 文件 |
|---|---|---|---|---|
| claude-dist-01 | npm 包是安装包装层；实现为平台原生二进制 | ② | 身份边界 | `01-分发件与身份.md` |
| claude-dist-02 | 分发包声明 8 个平台原生包，均锁 2.1.299 | ② | 身份边界 | `01-分发件与身份.md` |
| claude-dist-03 | 本机 `~/.claude/transcripts/` 非官方原生会话路径，不能当格式证据 | ② | CM-10 | `01-分发件与身份.md` |
| claude-dist-04 | 真实 `claude -p` 会创建原生 `~/.claude/projects/<转义cwd>/<session-id>.jsonl`（惰性） | ②真实运行 | CM-10、claude-resume-01 | `01-分发件与身份.md` |
| claude-dist-05 | 原生 transcript 的 `attachment.type` 枚举暴露实际上下文附件类型（含 prompt_snapshot/systemPrompt、skill_listing） | ②真实运行 | CM-01、CM-02 | `01-分发件与身份.md` |
| claude-dist-06 | 本机受第三方扩展污染（teamai hooks + 非原生 transcripts/）须如实登记；字段集合差异是"非原生"的更硬证据 | ②本地观察 | 全包归因、G8 | `01-分发件与身份.md` |
| claude-assembly-01 | 请求按"system prompt / project context / conversation"三层排序 | ① | CM-01、CM-12 | `02-请求组装与规则技能.md` |
| claude-assembly-02 | 系统提示词首次请求构建一次、记入会话、压缩前不重建 | ① | CM-01 | `02-请求组装与规则技能.md` |
| claude-rules-01 | CLAUDE.md 四级层次 + 导入 4 跳 + 单文件 4 MiB 上限 | ① | CM-02 | `02-请求组装与规则技能.md` |
| claude-rules-02 | `paths:` 规则与子目录 CLAUDE.md 按需加载 | ① | CM-02/03 | `02-请求组装与规则技能.md` |
| claude-retrieval-01 | MCP 工具定义默认延迟，仅名称+服务端说明入上下文 | ① | CM-03 | `02-请求组装与规则技能.md` |
| claude-skill-01 | 技能描述 1,536 字符上限；正文按调用加载 | ① | CM-02 | `02-请求组装与规则技能.md` |
| claude-skill-02 | 压缩后被调用技能正文重注入，每技能 ≤5,000、合计 ≤25,000 tokens | ① | CM-02/07 | `02-请求组装与规则技能.md` |
| claude-toolout-01 | Bash 有效输出内联约 30,000 字符，超限给路径 + ≤2,000 字符预览 | ① | CM-04 | `03-工具输出治理.md` |
| claude-toolout-02 | Bash 失败输出约 10,000 字符内联，超限头尾摘录且**无路径** | ① | CM-04 | `03-工具输出治理.md` |
| claude-toolout-03 | Read 默认 25,000 tokens/次、整文件 256 KB 上限 | ① | CM-04 | `03-工具输出治理.md` |
| claude-toolout-04 | 大型工具输出外溢到 `projects/<project>/<session>/tool-results/` | ① | CM-04 | `03-工具输出治理.md` |
| claude-toolout-05 | 工具/hook 输出超 10,000 字符存文件，模型只拿预览+路径 | ① | CM-04 | `03-工具输出治理.md` |
| claude-trigger-01 | auto-compact 窗口可由 `autoCompactWindow`/`/autocompact`/`--autocompact`/env 设定，范围 100K–1M | ①+② | CM-05、LQ-11 | `04-窗口计量与触发.md` |
| claude-trigger-02 | 触发按"窗口百分比"，`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`（1–100）只能调低 | ① | CM-05、LQ-11、C-01/C-02 | `04-窗口计量与触发.md` |
| claude-trigger-03 | 默认在模型上下文上限压缩；例外：200K 边界 / 原生 1M ≈967K | ① | CM-05、C-01/C-02 | `04-窗口计量与触发.md` |
| claude-trigger-04 | 官方文档出现压缩事件示例 `preTokens: 167189`（**示例**，非默认阈值） | ① | LQ-05、C-01/C-02 | `04-窗口计量与触发.md` |
| claude-trigger-05 | `/context` 可视化用量；超限输出超出 token 数 | ① | CM-05 | `04-窗口计量与触发.md` |
| claude-compact-01 | 自动压缩在反复失败时**停止重试**并报 thrashing | ① | CM-06/11 | `05-压缩与摘要.md` |
| claude-compact-02 | `/compact [指令]` 手动压缩；可用 focus 指令 | ① | CM-06 | `05-压缩与摘要.md` |
| claude-compact-03 | `/rewind` 的 Summarize from/up to here、`/clear`、`/recap` 是不同动作 | ① | CM-06/07 | `05-压缩与摘要.md` |
| claude-compact-04 | `idleCompaction`（v2.1.290+）可在空闲、缓存到期前压缩 | ① | CM-06/12 | `05-压缩与摘要.md` |
| claude-compact-05 | 接近上限"**先清较旧工具输出，再按需摘要**"（两段式） | ① | CM-07、C-10 | `05-压缩与摘要.md` |
| claude-compact-06 | 压缩后保留/重载清单（系统提示、CLAUDE.md、auto memory、plan、技能正文、≤5 文件） | ① | CM-07 | `05-压缩与摘要.md` |
| claude-compact-07 | 摘要请求 = 同前缀独立请求（**不是零 API 调用**）；缓存冷时重处理全文 | ① | CM-07、C-07 | `05-压缩与摘要.md` |
| claude-compact-08 | API 侧服务端 `clear_tool_uses_20250919`（默认阈值 100,000 input tokens、保留 3 个） | ①（**API 能力**） | CM-07、C-07 | `05-压缩与摘要.md` |
| claude-memory-01 | auto memory 存 `~/.claude/projects/<project>/memory/MEMORY.md`，注入前 200 行或 25 KB | ① | CM-08、LQ-08 | `06-记忆与恢复.md` |
| claude-memory-02 | CLAUDE.md 4 MiB 上限、导入 4 跳、AGENTS.md 直读需 v2.1.277+ | ① | CM-02/08 | `06-记忆与恢复.md` |
| claude-memory-03 | 记忆由 Claude 在会话中读写；**无**"后台多次小请求持续抽取"的证据 | ① | CM-08、LQ-08、C-07 | `06-记忆与恢复.md` |
| claude-memory-04 | 子代理可用 `memory` 字段获得独立记忆目录（user/project/local） | ① | CM-08/09 | `06-记忆与恢复.md` |
| claude-resume-01 | 会话存 `~/.claude/projects/<project>/<session-id>.jsonl`（明文） | ①+② | CM-10、LQ-10 | `06-记忆与恢复.md` |
| claude-resume-02 | 旧 transcript 以 `superseded-*`/`orphaned-*` 方式保留，不覆盖删除 | ① | CM-10、C-03/C-12 | `06-记忆与恢复.md` |
| claude-resume-03 | `cleanupPeriodDays` 默认 30 天；auto memory 不随清理删除 | ① | CM-08/10 | `06-记忆与恢复.md` |
| claude-resume-04 | `--no-session-persistence` / `CLAUDE_CODE_SKIP_PROMPT_HISTORY` 关闭落盘 | ①+② | CM-10 | `06-记忆与恢复.md` |
| claude-resume-05 | 摘要**不改磁盘**，原消息留在 transcript；checkpoint 保留最近 100 个快照 | ① | CM-07/10、C-03/C-12 | `06-记忆与恢复.md` |
| claude-cache-01 | 请求三层顺序，system prompt 层变化会**失效全部** | ① | CM-12 | `07-缓存与成本.md` |
| claude-cache-02 | TTL 5 分钟/1 小时两档，按"主对话/其他"请求桶分配 | ① | CM-12 | `07-缓存与成本.md` |
| claude-cache-03 | 失效清单（切模型、改 effort、压缩、加 MCP、插件、升级等） | ① | CM-12 | `07-缓存与成本.md` |
| claude-cache-04 | 压缩按设计失效对话层；摘要请求**复用**缓存（暖）/重处理全文（冷） | ① | CM-12、CM-07 | `07-缓存与成本.md` |
| claude-cache-05 | `/recap` 追加为命令输出，保持前缀缓存；`/rewind` 截回已缓存前缀 | ① | CM-12 | `07-缓存与成本.md` |
| claude-subagent-01 | 子代理全新独立窗口；fork 继承全部（含缓存） | ① | CM-09 | `08-子代理与错误处理.md` |
| claude-subagent-02 | 子代理工具调用不进主上下文，只回摘要（带来源头标记） | ① | CM-09 | `08-子代理与错误处理.md` |
| claude-subagent-03 | 内置 Explore/Plan 跳过 CLAUDE.md 与 git 快照 | ① | CM-09 | `08-子代理与错误处理.md` |
| claude-error-01 | 上下文到线报 `Context limit reached · /compact or /clear to continue` | ① | CM-11 | `08-子代理与错误处理.md` |
| claude-error-02 | 输入与 max_tokens 之和超限时降 `max_tokens` 重试，两种情况改为压缩 | ① | CM-11 | `08-子代理与错误处理.md` |
| claude-error-03 | 后台竞态：压缩期间仍在运行的工具**不会**在恢复后重跑 | ① | CM-11、CM-10 | `08-子代理与错误处理.md` |
