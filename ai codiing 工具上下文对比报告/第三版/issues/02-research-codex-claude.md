# 02: 调研：Codex CLI 与 Claude Code（v2.1.88）

**所属阶段：** 阶段 1

**要交付什么：** 为 Codex CLI 和 Claude Code 各产出一份完整的 16 类事实卡片，以及一份源码模块地图（文件路径、职责、对应清单类别）。Codex 基于 openai/codex 的最新稳定提交；Claude Code 基于作者仓库中的 v2.1.88 源码，并与官方文档交叉核对。Claude Code 需要重点覆盖 12 项：系统提示词组装、CLAUDE.md 分层与合并、system reminder、token 计数与 /context、工具输出落盘、旧工具结果清理、自动压缩与 /compact（包括压缩后重新附带的内容）、子代理、会话持久化与 /rewind、缓存断点、Skills 和 MCP 按需加载、hooks。

**被阻塞于：** None (can start immediately)

**状态：** ready-for-agent

- [ ] research/codex.md、research/claude-code.md 都覆盖全部 16 类，每条带来源和可信度标签
- [ ] research/source-map/ 下两份模块地图齐全
- [ ] 每个工具标出 2–4 个建议做源码解读的功能
- [ ] Claude Code 部分遵守 spec.md 第 9 节的使用边界，没有复制系统提示词原文
