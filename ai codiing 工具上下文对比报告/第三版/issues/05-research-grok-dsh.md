# 05: 调研：Grok Build 与 DeepSeek Harness

**所属阶段：** 阶段 1

**要交付什么：** 为 Grok Build 和 DeepSeek Harness 各产出一份 16 类事实卡片和源码模块地图。Grok Build 重点核实：自动压缩阈值、/context 拆分、/context-window、/rewind、子代理类型、记忆功能（/flush、/dream），以及它从 codex 和 opencode 移植过来的部分。DeepSeek Harness 重点核实：会话日志推导消息、压缩服务的三种调用方式、工具结果裁剪器、图片移出、溢出恢复、插件机制，以及社区插件 dsh-compressor。

**被阻塞于：** None (can start immediately)

**状态：** ready-for-agent

- [ ] research/grok-build.md、research/dsh.md 覆盖全部 16 类，每条带来源和可信度标签
- [ ] 两份模块地图齐全，并各标出 2–4 个源码解读候选
- [ ] 写清 Grok Build 中移植自 codex 或 opencode 的具体部分
