# 进度与状态

> 主控 agent 的唯一状态存储。上下文变长后，只依据本文件继续工作。
> 最近更新：2026-10-18

## 1. 源码快照（全部已在本机，只读）

根目录：`/Users/junjielong/workspace/agent-context-research/workbuddy-sources/`

| 工具 ID | 目录 | 远端 | ref / tag | 完整 SHA | 拉取日期 |
|---|---|---|---|---|---|
| codex | `codex-cli/` | openai/codex | main | `76ed3b484d62ccceb9fa512ff4dd139f421814c3` | 2026-10-14 |
| claude-code | `claude-code-v2.1.88/` | jun3355986/civil-engineering-cloud-claude-code-source-v2.1.88 | main | `988438af9293b198b03b8c01f97ee5556d2c74e2` | 2026-10-18 |
| pi | `pi/` | earendil-works/pi | main | `b45e0ebcc5ae2fc42a6f2f23104d10e656e6bedb` | 2026-10-14 |
| omp | `oh-my-pi/` | can1357/oh-my-pi | main | `f979f4639777858de28e6ecb99d577443abe0b7b` | 2026-10-14 |
| opencode-v1 | `opencode-v1/` | anomalyco/opencode | tag `v1.19.0` | `733b2c627e5aec39cb33cc22373bdce33053ef2c` | 2026-10-14 |
| opencode-v2 | `opencode-v2/` | anomalyco/opencode | tag `v2.0.29` | `042d0832f5f3a73eaa039a58a7d565776f6d4290` | 2026-10-14 |
| grok-build | `grok-build/` | xai-org/grok-build | main | `2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8` | 2026-10-18 |
| dsh | `deepseek-harness/` | deepseek-ai/deepseek-harness | master | `571902028a75c64c1d767f4ae5fd099485f0ddf0` | 2026-10-14 |

Permalink 基址：`https://github.com/<owner>/<repo>/blob/<SHA>/<path>#L<start>-L<end>`

## 2. 主控决策记录

| 编号 | 决策 | 理由 |
|---|---|---|
| D1 | 源码快照放在 `~/workspace/agent-context-research/workbuddy-sources/`，不进 iCloud 笔记目录 | 仓库合计约 1.5 GB，放进 iCloud 会触发同步风暴 |
| D2 | 调研票复用《第二版/WorkBuddy完整研究/02-工具/》研究包作为**基线线索**，但必须回源码逐条核验；未核验的写【待核实】 | 基线约 1.3 万行，可省掉重复摸底；但 spec 要求来源与可信度标签，不能照抄 |
| D3 | Claude Code 与 Grok Build 的基线**不可直接复用**（第二版把两者当闭源二进制观测），必须以 v2.1.88 源码与 xai-org/grok-build 源码重新推导 | 第三版新增了这两份源码，结论口径已变 |
| D4 | 01 号票是`toc.js`、`app.js`、`main.css` 的唯一创建者（例外于"只由主控修改"）；此后这三个文件只由主控改。06 号票把完整目录写成 `toc.snippet.js` 交主控合并 | 01 的骨架必须有可跑的导航，否则组件页无从验证 |
| D5 | spec.md 第 3 节的仓库地址按实际核验结果修正（pi 已迁至 earendil-works/pi；opencode 已迁至 anomalyco/opencode；Grok Build 现为开源仓库） | 地址过期会让子 agent clone 失败或分析错仓库 |
| D6 | `refs/` 三份参考材料映射：参考样例 1 = `CodexCLI 上下文管理-交互教程_workbuddy 版.html`；参考样例 2 = `CodexCLI上下文管理-交互教程_Notion版.html`；写作规范 = `HeadFirst式写作规范.md` | README 要求替换占位符 |
| D7 | 演示专属样式写在页面内 `<style>`，选择器必须加 `#demo-<名字>` 前缀；主控不再为单个演示改 main.css | 避免多个子 agent 并发改同一个 CSS 文件 |
| D8 | 入门章的场景开场统一用 `.callout--info` + 标题「场景 · …」，不新增 hf 变体（已写入 CONVENTIONS §10） | 07 号票实测后确认，保持 7 章一致 |
| D9 | 源码解读按每工具 3–4 节共 26 节（票面下限 2 节），章节 ID 与 outline 一致 | 6 号票按 source-map 建议扩充，已在 toc 落地 |
| D10 | 主线单章篇幅 8,000–13,000 字，以 main-08 的 12,911 字为上限参照；入门章 3,000–3,600 字（作者 2026-10-19 确认 Q1=A） | 保深度，不砍信息密度；已写入 CONVENTIONS §3 与 outline 主线表 |
| D11 | 源码解读保持 26 节（Q2=A） | 每节只讲一个功能，便于固定提交引用 |
| D12 | 阶段 2 五路并行：票 10–14 同批派发（Q3=A） | 10 依赖 07、11–14 依赖 08，均已 done |
| D13 | 【待核实】【推断】结论必须在句末加脚注，写清查了什么、缺什么（Q4=B） | 已新增 `.footnotes` 组件与 CONVENTIONS §3/§13 规则 |
| D14 | main-13 不复制 cache-hit 演示实现，改为链到 intro-05 的演示 + 本章静态失效点 SVG | 避免 10 与 14 两票对同一 JS 产生 DOM 契约耦合 |
| D15 | 源码解读 26 节全部保留，每节 6,000–9,000 字（Q1=A） | 源码是这套教程的差异化；outline 已上调目标篇幅 |
| D16 | 阶段 3 五路同开：15/16（进阶）+ 17/18/19（源码）（Q2=A） | 进阶只依赖已完成的主线；源码沿用 src-codex-01 模板 |
| D17 | 视频分镜做 5 个主题：压缩、缓存、子代理、会话树、评估（Q3=B） | 已写入 outline 附录行 |
| D18 | 跨部分引用必须写「入门第 N 章 / 主线第 N 章」；同部分内可只写「第 N 章」 | 两部分的章号都从 01 起，单独写「第 4 章」会歧义；已回改 main-05、main-13 |
| D19 | 篇幅上限按实测调整：源码节 6,000–11,500、进阶 6,500–10,000 | Q1=A 保深度；实测 26 节 7,900–11,400、进阶 8,200–9,800，未要求返工 |
| D20 | 行内 `<code>` 允许任意断行（`overflow-wrap:anywhere`） | 26 个源码页里有 5 页因长标识符把 375px 布局撑到 565px；属于全站 CSS 缺陷，改一次全站受益 |

## 2.1 阶段 3 前的一致性抽查（Q4=A）

抽查范围：24 个页面的工具名、术语、关键数字、跨章引用。

| 项 | 结果 | 处理 |
|---|---|---|
| 工具名 | 无 `Grok Builder` / `OpenCode` / `Deepseek` 等错写；`disableClaudeCodePrompt` 是 opencode 真实配置键，保留 | 无需改 |
| 术语 | `修剪` 1 处（main-01）与其他 139 处 `裁剪` 不一致 | 已统一为「裁剪」 |
| 关键数字 | Claude 13k 触发、Codex 20k/64k、Claude 50k 落盘、opencode 15k、Grok 85% 在 8 个页面间一致 | 无需改 |
| 跨章引用 | main-05 两处「第 4 章」实指入门第 4 章；main-13 两处「第 5 章」实指入门第 5 章 | 已加「入门」前缀，并写入 CONVENTIONS §3 规则 |
| 章号范围 | 全部落在 1–16，无越界 | 无需改 |

## 3. 票状态

| 票 | 标题 | 阶段 | 阻塞于 | 状态 | 产出 | 备注 |
|---|---|---|---|---|---|---|
| 01 | HTML 骨架与组件库 | 1 | — | done | tutorial/index.html、pages/_components.html、assets/css/main.css、assets/js/toc.js、assets/js/app.js、tutorial/CONVENTIONS.md | 无头 Chrome 自检：控制台 0 报错；弹窗/Esc/测验/主题/搜索全通过；375px 正常 |
| 02 | 调研 Codex + Claude Code | 1 | — | done | research/codex.md、research/claude-code.md、source-map 2 份 | 157 条 permalink 已脚本校验；【待核实】8 条；4 处源码/文档口径冲突待 06 裁决 |
| 03 | 调研 pi + omp | 1 | — | done | research/pi.md、research/omp.md、source-map 2 份 | 【待核实】2 条（规则文件字节上限） |
| 04 | 调研 opencode v1/v2 | 1 | — | done | research/opencode-v1.md、opencode-v2.md、source-map 2 份 | v1→v2 变化 7 条齐全；【待核实】4 条 |
| 05 | 调研 Grok Build + dsh | 1 | — | done | research/grok-build.md、research/dsh.md、source-map 2 份 | 【待核实】8 条；dsh 无记忆能力，矩阵将缺一格 |
| 06 | 大纲、矩阵、版本表 | 1 | 01–05 | done | outline.md、research/matrix.md、research/versions.md、toc.snippet.js | 60 章；128 格无空（117 已核实/10 推断/1 待核实）；已合入 toc.js |
| 07 | 样章 intro-01 | 1 | 06 | done | pages/intro-01.html、demos/context-budget.js | 无头自检：0 报错；键盘+重置+ARIA 通过；375px 无溢出；3482 字 |
| 08 | 样章 main-08 | 1 | 06 | done | pages/main-08.html、demos/compact-sim.js、demos/tool-pairing.js | 7 弹窗全开、3 测验可展开、2 演示联动正常；正文 12,911 字（超大纲估算，待作者定基准） |
| 09 | 样章 src-codex-01 | 1 | 06 | done | pages/src-codex-01.html | 4 条主 permalink + 8 条行内链接全部 200；摘录 15+45 行；3 张 SVG；3 处【订正】 |
| 10 | 入门 02–07 | 2 | 07 | done | pages/intro-02…07.html、demos/cache-hit.js | 6 章 3,162–3,774 字；1 页 1–2 图；演示预设实测：改开头命中 0、多付 +0.577 元；改末尾命中 39,600、多付≈0 |
| 11 | 主线 01–04 | 2 | 08 | done | pages/main-01…04.html | 各 9,350–9,901 字；7 弹窗/3 测验/9 行对比表齐全；main-02 含 8 工具查找路径图；脚注 1/3/4/3 |
| 12 | 主线 05–07、09 | 2 | 08 | done | pages/main-05…07、09.html | 各 9,207–12,213 字；main-05 含 200k/400k/1M 切换的五段计量图；main-07 明确裁剪/压缩边界；脚注 8/6/7/7 |
| 13 | 主线 10–12 + 2 演示 | 2 | 08 | done | pages/main-10…12.html、demos/subagent-isolation.js、session-tree.js | 8,385–10,192 字；两演示全控件实测；脚注 4/4/3 |
| 14 | 主线 13–16 | 2 | 08 | done | pages/main-13…16.html | 8,130–13,702 字；main-13 链回 intro-05 演示；main-16 给出 13 项指标清单；脚注 3/4/3/4 |
| 15 | 进阶：取舍与失败案例 | 3 | 11–14 | done | adv-01、adv-02、demos/compaction-drift.js | 6 组取舍、5 个案例；演示 1→6 次压缩：硬约束 3/3→0/3，精简模板把首丢从第 4 次提前到第 3 次 |
| 16 | 进阶：架构、策略与评估 | 3 | 11–14 | done | adv-03、adv-04、adv-05 | 一张图 5 种架构 × 4 个维度；2 个场景练习；MDE 与消融设计 |
| 17 | 源码：Codex + Claude Code | 3 | 09 | done | src-codex-02…04、src-claude-code-01…04 | 7 节；Codex 摘录 11–37 行，Claude 单段 ≤17 行；54 条 permalink 核对 |
| 18 | 源码：pi / omp / opencode | 3 | 09 | done | 12 节 | 每节 2–3 图、3 题；v1/v2 三对并排对照；最长代码块 58 行 |
| 19 | 源码：Grok Build + dsh | 3 | 09 | done | 6 节 | 32 条 permalink 全 200；Grok 五步链路图与装配顺序 |
| 20 | 附录与视频分镜 | 3 | 15–19 | done | appendix-glossary/params/matrix/reading/video.html、video/01…05.md | 术语 68 条、参数 65 条、矩阵 128 格 0 空、5 份分镜 1,433–1,970 字 |
| 21 | 全站集成与检查 | 3 | 20 | done | assets/js/search-index.js、qa-report.md | 60/60 done；604 外链 0 失效；323 锚点 + 332 相对链接 0 断；7/7 演示通过；61 页 375px 通过 |
| 20–21 | 附录视频 / 集成检查 | 3 | 15–19 / 20 | 未开始 | | |

状态取值：待派发 / 进行中 / 待验收 / 返工中 / done / blocked

## 4. 阶段日志

### 2026-10-18
- 就绪检查：spec.md、21 张票、refs/ 三份材料齐全；补齐两个缺失仓库（claude-code v2.1.88、grok-build），六个旧快照沿用。
- 修正 spec.md 的参考材料占位符与仓库地址（D5、D6）。
- 派发阶段 1 第一批：01–05，5 路并行。
- 第一批验收：01 骨架（无头 Chrome 自检 0 报错、375px 正常）、02–05 八份事实卡片（4,456 行、157+ 条 permalink 脚本校验）、06 大纲与矩阵（128 格无空）。
- 派发阶段 1 第二批：07–09 三份样章，并行；全部通过验收并已把 toc 状态改为 `done`。
- 阶段 1 小结：71 条外链全部 200；正文页 2,839 行；research 29 条【待核实】、34 条【推断】；正文 1 条【待核实】、2 条【订正】。

### 2026-10-19
- 作者裁决：Q1=A（主线 8k–13k，保深度）、Q2=A（源码 26 节不变）、Q3=A（阶段 2 五路并行）、Q4=B（【待核实】逐条脚注）。已写入 CONVENTIONS §3/§13、outline 主线表与 D10–D14。
- 核销 Grok 记忆文档 404：官方正文在 `crates/codegen/xai-grok-pager/docs/user-guide/13-memory.md`（473 行），已补「压缩后重检索」并更新矩阵第 12 行。
- 阶段 2 派发：10–14 五路并行，全部产出；21 个新页面 + 3 个演示。
- 主控验收（脚本）：25 个页面控制台 0 报错；16 个主线章各 7 弹窗全开、3 测验可展开、对比表 9 行；375px 全部 `scrollWidth=375`；443 条唯一外链（443 次 HTTP 校验）最终 0 失效，修掉 1 条 Claude Code 路径（`AgentTool/built-in/exploreAgent.ts`）。
- 收口修改：main-08 补 1 条脚注并把模板字数上调到 9,000–12,000；intro-01/07、main-09/12 的「待写」页脚改为真实链接；CONVENTIONS 脚注上限 6→8。
- 阶段 2 小结：正文页共 16,209 行；25/60 章 done；main 章脚注合计 60 条，intro 4 条。

### 2026-10-19（续）阶段 3 完成
- 作者裁决：Q1=A 保 26 节、Q2=A 五路并行、Q3=B 五个分镜、Q4=A 先做一致性抽查。已落 D15–D18。
- 15–19 五路派发并验收：进阶 5 章、源码 25 节、1 个演示。
- 20 完成附录 5 页 + 5 份分镜；21 完成集成与 QA：全文搜索索引 511 小节、`search-index.js` 接入 61 页、`app.js` 支持全文检索、`qa-report.md` 产出。
- 全站终态：**60/60 章 done**；61 个 HTML；7 个演示；604 条唯一外链 0 失效；内部 323 锚点 + 332 相对链接 0 断；61 页 375px 无溢出；控制台 0 报错。
- 关键缺陷修复：行内长 `<code>` 撑宽 375 布局（5 页实测 565/410/402/383px），已在 main.css 用 `overflow-wrap:anywhere` 修复。
- 遗留：Safari 未做运行时验证（自动化被系统阻止），静态兼容建议 Safari 16.4+；adv-04/05 句长偏长；Claude 四页缺【官方文档】标签。详见 `qa-report.md`。

### 2026-10-19（续）作者反馈修复
- 样式回归：全站扫描 SVG 文字溢出（25 页 40 处，含误报），视觉复核后修 12 张图——新增 `.svg-label--s/--xs/--xxs` 三级字号、缩短 6 个过长标签、重排 3 处拥挤标签；复检剩 8 处 ≤2px。
- 元素溢出：`.field__label` 在 5 页溢出 4px，已加 `flex-wrap`。
- 侧栏滚动：`app.js` 用 `sessionStorage` 记录 `nav.scrollTop`，换页后恢复；实测 900→900→900。
- Safari：WebDriver 驱动 Safari 27.0.1 全量通过——7/7 演示、`color-mix`/`structuredClone`/`.at` 支持、导航 60 项、索引 511；420px 下 scrollWidth=403。
- 两个可选项收尾：adv-04/05 句长降至 20.1 / 20.9（>40 字句 0）；Claude 四页新增「来源类型对照」，补齐【官方文档】【两者一致】与差异说明。
