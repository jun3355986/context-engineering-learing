---
title: Prompt Caching 官方文档核查与交互来源
date: 2026-10-14
status: 官方正文与原版交互已核验，未调用 API
tags:
  - AI/上下文管理
  - PromptCaching
---

# Prompt Caching 官方文档核查与交互来源

核查日期：2026-10-14（Asia/Shanghai）。遵循 OpenAI Docs：先官方域名搜索，再实际打开原页；补读官方 `.md` 正文与 Responses API 参考，并在 Chrome 中检查 DOM 和操作官方模拟器。本记录保存官方事实、交互来源与教程验收证据；未执行真实模型请求。

## 1. 官方图实际是什么

原页：[Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)。正文 DOM 没有可提取的图片、视频或 iframe 媒体资源；主要图由页面内 HTML/CSS、React、SVG 绘制。

| 内容 | 实际形态 | 可用原页位置 |
|---|---|---|
| KV 逐 token 三步说明 | 静态 HTML `figure/div`；展示 tiny、chips、power、big、ideas，与对应 KV 状态 | [What is the prompt cache](https://developers.openai.com/api/docs/guides/prompt-caching#what-is-the-prompt-cache) |
| 完整上下文的组成条 | 静态 HTML `figure/div`；角色、工具、历史和多模态内容 | 同上；官方明确该条不是固定序列化顺序 |
| 两次请求与可复用前缀 | 真正的 React 交互组件 `PromptCachingSimulator` | [How prefix matching works](https://developers.openai.com/api/docs/guides/prompt-caching#how-prefix-matching-works) |
| 多分支与两个显式断点 | 静态 HTML `figure/div`，不是独立图片 | [Choose a caching mode](https://developers.openai.com/api/docs/guides/prompt-caching#choose-a-caching-mode) |
| 前缀长度与平均输入成本 | React 交互组件 `PromptCachingCost`，图表本身为 SVG | [Escape the minimum cacheable length cost trap](https://developers.openai.com/api/docs/guides/prompt-caching#escape-the-minimum-cacheable-length-cost-trap)；默认位于折叠内容内 |

模拟器有模型代际选择、Implicit/Explicit 选择、7 个分段长度滑块，以及可展开的请求参数和 usage。成本图有 4 个数字输入：最小可缓存长度、每次写入后的完整读取次数、读取倍率、写入倍率。

## 2. 官方整页 iframe 的实际验证

用仅提供静态测试 HTML 的临时 localhost HTTP 服务，嵌入原页 `#how-prefix-matching-works`。Chrome 中官方页实际加载成功；在 iframe 内切换 Earlier models 后，界面计算由 12,000 改为 11,264，证明组件在该 iframe 中可操作。截图也看到了两条请求及控件。未访问登录入口或发起 API 请求。

本次原页 GET 未见 `X-Frame-Options` 或 `Content-Security-Policy` 响应头。浏览器实测比这个头部观察更强，初次结论覆盖 Chrome、当前网络与 localhost HTTP；随后也完成了本地 `file://` 教程验证，见第 6 节。Obsidian 内嵌未验证。

可以采用“默认折叠 → 用户点开后才设置 iframe src → 展示官方整页”的方案。必须同时保留“另开官方原页”的链接。它会连同官方导航一起显示，不能称为官方提供的独立嵌入组件。跨域父页面不能直接裁剪其 DOM、改中文、读取内部成功状态；iframe 的 load 事件本身也不能证明页面交互完全可用。

离线中文交互需明确写“依据 OpenAI 官方说明制作的中文教学演示”；官方 iframe 标为“OpenAI 官方原版（联网）”。两者不要混称原图。

## 3. 需要准确写进教程的规则

缓存保存可重复使用前缀的 KV 计算状态；后续请求仍需处理新输入并生成新输出。匹配针对完整渲染后的前缀，相关设置也可能改变它。中途变化会影响从该位置往后的复用，并非任何一处变动必然让之前的全部前缀也失效。稳定内容置前、变化内容后置、历史追加而非反复改写，是合理的组织方式。[官方机制说明](https://developers.openai.com/api/docs/guides/prompt-caching#what-is-the-prompt-cache)

| 当前文档分支 | GPT-5.6 及以后 | 更早模型 |
|---|---|---|
| 最小长度 | 1,024 个用户可见输入 token，不含隐藏系统内容 | 随模型与请求设置变化，不能统一套 1,024 |
| 断点 | 支持隐式与显式；显式标记位于受支持内容块 | 只支持隐式，间隔依模型；5.5/5.5 Pro 为 2,048 |
| cached_tokens | 合格边界扣除隐藏 token 后的精确值 | 扣除隐藏 token 后，向下取 128 的倍数 |
| key 的作用 | 可选，用于按客户等分开缓存计量；不需要靠它优化路由 | 稳定 key 有助相同前缀的请求路由，但不保证命中 |
| 保留控制 | `prompt_cache_options.ttl="30m"`，表示至少保留到最近写入/复用后 30 分钟 | `prompt_cache_retention`：模型允许时 `in_memory` 或 `24h`；5.5/5.5 Pro 仅 24h |

来源：[模型差异表](https://developers.openai.com/api/docs/guides/prompt-caching#summary-of-model-differences)、[Responses API 参数](https://developers.openai.com/api/reference/resources/responses/methods/create)。API 参考确认显式断点不是按 token 块取整，且 `ttl` 是最小寿命；旧 `retention` 描述最大保留策略，两者语义不同。搜索抓取有时漏掉 Earlier models 折叠标题，造成串段；本次浏览器展开和 Markdown 正文已核清，不存在“新模型也只支持隐式”的结论。

更早模型的 `in_memory` 通常在不活跃 5–10 分钟后失效，最长约一小时；`24h` 通常约 30 分钟、最多 24 小时，不能承诺一定 24 小时命中。对支持两者的旧模型，默认还受组织 ZDR 策略影响。缓存不能跨组织、跨处理地域复用；需到达仍持有匹配条目的机器。文档的约 15 请求/分钟路由建议不是账户统一限流阈值。[保留与位置](https://developers.openai.com/api/docs/guides/prompt-caching#cache-lifetime)

`usage.input_tokens_details.cached_tokens` 表示从缓存读取的输入数；`cache_write_tokens` 表示写入缓存的输入数。它们都是输入明细，不应再重复加到 `input_tokens`。计算输入成本时分开普通输入、缓存读取、缓存写入，不能把写入倍率当作叠加附加费。当前新模型分支写入为普通输入的 1.25 倍，读取倍率仍按具体模型核对；别把“所有缓存都免费写入”或“全模型便宜固定比例”写成常识。[Responses API usage](https://developers.openai.com/api/reference/resources/responses/methods/create)、[监测与计费](https://developers.openai.com/api/docs/guides/prompt-caching#monitor-cache-performance)

命中失败排查还包括模型、服务层级、工具集合/顺序、设置、key、边界、过期和路由，不能只看两份可见文字是否相同。可查诊断响应，不能用“感觉更快”证明命中。[官方诊断](https://developers.openai.com/api/docs/guides/prompt-caching/diagnostics)

## 4. 中文交互的教学设计建议

先讲一个分工：“压缩减少带上的材料；缓存减少对相同材料的重复计算。”缓存命中后，上下文条的总长度保持不变；只把其中已复用的计算区域染绿。压缩则真的替换历史内容、缩短当前请求。压缩可能改变前缀和后续缓存复用，但此前未改变且仍合格的前缀不必一概归零。

建议在中文演示中依次提供四个小实验，而不是首次就暴露所有 API 配置：

1. **只追加新问题**：两条请求共用稳定前缀，新增尾部标橙；观察复用部分保持，输入总数仍增长。
2. **把日期放到最前面**：改变第一个动态位置，匹配从这里中断。再移动到稳定内容之后，对照可复用前缀。
3. **历史变成摘要**：显示原长历史被替换，总材料缩短；指出这段不能继续当作完全相同的旧前缀复用。
4. **同样文字仍然没命中**：用已过期/没有合格缓存断点/未找到相应缓存等明确教学案例，说明相同前缀是必要条件之一而非充分条件。

画绿色区域时标“本例假设缓存仍可用且边界合格”，让示例确定可推演；实际命中另看返回 usage。教学卡片数不冒充真实 tokenizer。官方模拟器的隐藏 3,000 token 也是它自己的演示值，不写成每个 API 请求都有的固定开销。

进阶折叠再放新旧模型规则表、断点、key 与保留设置。成本图若复现，应让读者输入读写倍率和复用次数；强调示例假设每次完整命中，真实取舍要看实际费用与任务质量，不鼓励为了凑阈值加入无用文字。

## 5. 与 Codex CLI 固定源码分开陈述

上述为核查日的 OpenAI API 文档规则，**不能据此宣布固定 `a07c8ebd57feedc4cf5dfe854c8e9101de54186b` 的 CLI 已启用新断点、30m TTL、prewarm 或以该方式计费**。若要落到 CLI，需要另查它实际发送的字段、提供者能力和真实返回 usage。账户模式、服务配置和 API 接口规则也不能混为一个默认。

可用于教程的边界台词：“这一节用官方 API 文档解释缓存机制。前面八章的 Codex CLI 源码快照用来解释请求和压缩怎样组织；具体服务是否命中缓存，以运行时返回的信息为准。”


## 6. 教程文件内的最终核验

2026-10-14 在 Chrome 中直接打开本地 file:// 教程，点击加载官方整页，成功切换官方模拟器的模型代际：可见数字从 12,000 变为 11,264。说明这次本地文件内嵌实际可操作；不据此保证其他笔记软件或未来站点策略相同。教程同时保留官方独立页面入口，中文练习可离线使用。
