# 版本表

> 数据取自 `progress.md` 第 1 节与 8 份事实卡片开头。短 SHA 为完整提交号前 7 位；正文引用必须用完整 SHA 的 permalink。
> 所有工具的事实核实日期均为 **2026-10-18**；快照日期指本机仓库拉取日期。

| 工具 | 版本或提交号 | 快照日期 | 该版本的特殊性 |
|---|---|---|---|
| Codex CLI | `76ed3b4`（main） | 2026-10-14 | 滚动 main 快照，无发布版本号；上下文逻辑全在 Rust 的 `codex-rs/`，TS 入口不含上下文逻辑 |
| Claude Code | `988438a`（非官方源码 v2.1.88） | 2026-10-18 | 非 Anthropic 官方开源，结论只代表 v2.1.88；源码由 source map 还原，函数名可能非原始命名 |
| pi | `b45e0eb`（main） | 2026-10-14 | 仓库已从 `badlogic/pi-mono` 迁至 `earendil-works/pi`；自我定位最小内核，明确跳过子代理与 plan mode |
| oh-my-pi（omp） | `f979f46`（main） | 2026-10-14 | pi 的 fork：保留“树 + 投影 + 摘要 + 保留段”骨架，新增方法链、预裁剪、记忆、子代理、checkpoint |
| opencode v1 | `733b2c6`（tag `v1.19.0`） | 2026-10-14 | 最后一个 v1 出货线快照；`packages/core/src/session/*` 已带 v2 标签，不能当作 v1 行为证据 |
| opencode v2 | `042d083`（tag `v2.0.29`，**beta**） | 2026-10-14 | beta 线，字段与默认值可能在下个版本变化；v1 的 `prune`、`tail_turns` 已标 unsupported |
| Grok Build | `2bdd1d6`（main；`SOURCE_REV` = `559751f`） | 2026-10-18 | 首次拿到开源仓库（此前只有闭源二进制观测）；无 tag，`SOURCE_REV` 指向 monorepo 提交，映射不到语义化版本 |
| DeepSeek Harness（dsh） | `5719020`（master） | 2026-10-14 | Cordis“一切皆插件”架构，没有特权内核；无记忆、无 rewind，跨会话只靠 AGENTS.md 与 `@session` |

## 写第 0 章版本表时的三条注意

1. **不要补版本号**：Codex、pi、omp、Grok Build、dsh 都是分支快照，写“提交号 + 日期”即可；只有 opencode v1/v2 有 tag。
2. **Claude Code 必须带声明**：非官方源码、仅代表 v2.1.88、与官方文档冲突时两边都写。
3. **opencode v2 必须标 beta**：任何“v2 改成……”的句子都要限定在 `v2.0.29`，不能外推到正式版。

## 完整提交号（permalink 用）

| 工具 | 完整 SHA |
|---|---|
| codex | `76ed3b484d62ccceb9fa512ff4dd139f421814c3` |
| claude-code | `988438af9293b198b03b8c01f97ee5556d2c74e2` |
| pi | `b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb` |
| omp | `f979f4639777858de28e6ecb99d577443abe0b7b` |
| opencode-v1 | `733b2c627e5aec39cb33cc22373bdce33053ef2c` |
| opencode-v2 | `042d0832f5f3a73eaa039a58a7d565776f6d4290` |
| grok-build | `2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8` |
| dsh | `571902028a75c64c1d767f4ae5fd099485f0ddf0` |
