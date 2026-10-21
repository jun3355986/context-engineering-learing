# 教程组件写法手册（CONVENTIONS）

> 适用：`tutorial/` 下所有章节页。由 01 号票产出，是组件 class 名与写法的唯一依据。
> 原则：**只复制本手册里的结构，不自行发明 class**。确实需要新组件时，在交付说明里提出，由主控扩展 `main.css` / `app.js`。

---

## 1. 目录与文件

```
tutorial/
  index.html                 第 0 章导读（已存在，勿改结构）
  pages/<章节ID>.html        每章一个页面
  assets/css/main.css        全站样式（只由主控改）
  assets/js/toc.js           导航清单（只由主控改）
  assets/js/app.js           导航、弹窗、测验、搜索、主题（只由主控改）
  assets/js/demos/<名字>.js  交互演示，一个演示一个文件
  CONVENTIONS.md             本文件
```

- 章节 ID 与文件名一致：`main-08` → `pages/main-08.html`。
- 导航、搜索、深浅色、弹窗、测验、复制都由 `toc.js` + `app.js` 驱动，页面里**不写**这些逻辑。
- 不引入 CDN、外部字体、外部图片、构建工具；不写 ES module（`type="module"` 在 `file://` 下会失败）；不写 `fetch`。

---

## 2. 新页面模板（直接复制）

新建 `pages/main-08.html` 时，把 `data-chapter` 改成对应 ID，正文放进 `<article class="prose">`。

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>压缩：把历史换成摘要 · AI Coding Agent 上下文管理</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%232c6ecb'/%3E%3Cpath d='M9 21V11h4l3 6 3-6h4v10h-3v-6l-3 6h-2l-3-6v6z' fill='white'/%3E%3C/svg%3E">
<script>
  try {
    var t = localStorage.getItem("ctx-theme");
    if (t === "dark" || t === "light") document.documentElement.setAttribute("data-theme", t);
  } catch (e) {}
</script>
<link rel="stylesheet" href="../assets/css/main.css">
</head>
<body data-chapter="main-08">
<a class="skip-link" href="#main">跳到正文</a>

<header class="topbar">
  <button class="icon-btn menu-btn" id="menu-btn" type="button" aria-label="打开目录" aria-expanded="false" aria-controls="sidebar">
    <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 5h14M3 10h14M3 15h14"/></svg>
  </button>
  <a class="brand" href="../index.html">
    <span class="brand__mark" aria-hidden="true">ctx</span>
    <span class="brand__text">AI Coding Agent 上下文管理</span>
  </a>
  <div class="topbar__tools">
    <div class="search" role="search">
      <svg class="search__icon" viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5"/><path d="m13 13 4 4"/></svg>
      <input class="search__input" id="search-input" type="search" placeholder="搜索章节" autocomplete="off" aria-label="搜索章节" aria-controls="search-results" aria-expanded="false">
      <div class="search__results" id="search-results" hidden></div>
    </div>
    <button class="icon-btn theme-btn" id="theme-btn" type="button" aria-label="切换到深色模式">
      <svg class="ico ico--moon" viewBox="0 0 20 20" aria-hidden="true"><path d="M16 12.5A6.5 6.5 0 0 1 7.5 4a6.5 6.5 0 1 0 8.5 8.5Z"/></svg>
      <svg class="ico ico--sun" viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="3.6"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.3 4.3l1.4 1.4M14.3 14.3l1.4 1.4M15.7 4.3l-1.4 1.4M5.7 14.3l-1.4 1.4"/></svg>
    </button>
  </div>
</header>

<div class="nav-backdrop" id="nav-backdrop"></div>

<aside class="sidebar" id="sidebar" aria-label="教程目录">
  <div class="sidebar__inner">
    <div class="recent" id="recent" hidden></div>
    <nav class="nav" id="nav" aria-label="章节导航"></nav>
    <div class="sidebar__foot">
      <a href="../index.html">返回导读</a> · 版本 2026-10-18<br>
      纯静态页面，可离线阅读
    </div>
  </div>
</aside>

<main class="main" id="main">
  <article class="prose">

    <header class="page-head">
      <p class="kicker"><b>第二部分 · 主线</b><span>·</span><span>第 08 章</span></p>
      <h1>压缩：把历史换成摘要</h1>
      <p class="lede">一句话说清本章要解决的麻烦，再给读者一个继续读的理由。</p>
      <ul class="meta">
        <li>约 15 分钟</li>
        <li>3 个交互</li>
        <li>L2 → L3</li>
      </ul>
      <div class="learn">
        <h2>读完你能做到</h2>
        <ol>
          <li>第一条可验证的学习目标。</li>
          <li>第二条。</li>
          <li>第三条。</li>
        </ol>
      </div>
    </header>

    <!-- 正文 -->

    <p class="footer-note">下一章：多模态上下文（待写，暂不提供链接）。</p>

  </article>
</main>

<script src="../assets/js/toc.js"></script>
<script src="../assets/js/app.js"></script>
</body>
</html>
```

要点：

- `body[data-chapter]` 决定导航高亮和「最近阅读」，**必须**写，且与 `toc.js` 的 `id` 一致。
- `pages/` 下所有引用都用 `../`；`index.html` 用 `./`。导航链接由 `app.js` 自动计算前缀，正文里的普通链接仍要自己写对。
- 脚本顺序固定：先 `toc.js`，后 `app.js`，都放在 `</body>` 前。
- 深浅色初始化脚本必须放在 CSS 之前，否则会闪一下白屏。

---

## 3. 章节结构（主线）

主线每章按 spec 第 5 节的五段写，顺序不要变：

1. Codex 主线讲解（Codex 没有该能力时写明「Codex 无此能力」，改用做得最好的工具当主例）
2. 7 个工具按钮（点击弹窗）
3. 8 工具对比表
4. 设计取舍
5. 3 道小测验

入门章用 Head First 节奏：场景 → 人话直给 → 术语 → 类比/图 → 动动脑 → 没有傻问题 → 要点小结。

### 跨章引用写法（2026-10-19 定）

入门与主线的章号都从 01 开始，单独写「第 4 章」会有歧义。**跨部分引用必须带前缀**：`入门第 4 章` / `主线第 13 章`；同一部分内可以只写「第 4 章」。源码节与附录同理，写 `源码 · Codex 第 2 节`。

### 术语：产品叫 agent，协议层叫工具（2026-10-21 定）

「工具」在 AI 行业里同时指两样东西，混用会让读者分不清「哪个产品」和「哪个 function」。全站按下面两层写：

- **产品层**：统一写 **编码智能体（coding agent）**，正文简称 **agent**。标题、表头、弹窗标签用短名 `agent`；导读首次出现给全称和一句话定义。不要用「工具」指产品，也不要用「AI 编程工具」「AI 编码助手」泛指这八个产品。
- **协议层**：只有 tool 才叫「工具」——工具定义、工具调用、工具结果、工具输出、工具表、MCP 工具。
- **编码助手（coding assistant）**：专指补全型产品（Copilot 补全、行内建议），不要用来指本书比较的 agent。

判断方法：能自己规划多步、读写文件、执行命令、跑测试的是 agent；等你在光标处补下一行的是助手。

### 小节衔接（2026-10-20 定）

读者卡住的地方，多半不是某句话看不懂，而是**上一节和这一节之间断了**。每节的第一句要接住上一节的落点：

- **接落点**：回指刚讲完的东西（「刚才那块白板，是你用手拖满的」），或把上一节结尾抛出的问题接过来。不要另起一个话题。
- **新角色先报名**：工具、运行时、模型第一次出场，先用一句话交代「它是谁、在哪一层」，再让它做事。不要写「工具通常在三件事里选」——把工具当人使，读者会问「哪个工具」。写清是运行时在量 token、模型在读写。
- **节末留钩子**：用后果或问题收尾（「它长到头的时候，谁来踩刹车？」），不要用「下一节讲 X」的目录式过渡。
- **过渡句并进段落**：不要单开一段「接下来我们看看……」，并进上一节末段或下一节首段。

### 篇幅基准（2026-10-19 定）

| 类型 | 正文中文字数 | 说明 |
|---|---|---|
| 入门章 | 3,000–3,600 | 每屏信息量少，宁可少讲 |
| 主线章 | 8,000–13,000 | 以 `main-08`（12,911 字）为上限参照；低于 8,000 视为展开不足 |
| 源码解读节 | 6,000–11,500 | 含 2 段以内的代码摘录与 2–3 张图；实测 7,900–11,400 |
| 进阶章 | 6,500–10,000 | 受控中文 + 图；实测 8,200–9,800 |

超过上限时先删「重复解释」，不要删来源、参数与【订正】注。

### 【待核实】的强制写法（Q4=B）

凡正文用到了事实卡片里标【待核实】的结论，**必须**在句末加脚注，且脚注要写清「查了什么、缺什么、如何影响结论」，不许只在文末笼统列一句。同一页里相同结论只注一次。写法见第 13 节「脚注」。

---

## 4. 正文排版

直接用语义标签，不要手写字号和颜色：

```html
<p class="sec-no">01 · 一个真实会发生的下午</p>
<h2>“我第一句话就说过了啊”</h2>
<p>正文段落。</p>
<p class="lead-in">需要强调的开场句，左侧有蓝色竖线。</p>
<p class="muted small">次要说明。</p>
```

- 正文由 `.prose` 控制：最大 760px，桌面 16.5px / 行高 1.78，手机 16px / 1.76。
- 标题只用 `h1`（每页一个）、`h2`、`h3`、`h4`，不写 `<h1 style="font-size:...">`。
- 行内代码用 `<code>`；按键用 `<kbd>`。
- 段落内需要强调：`<strong>`；术语首次出现给英文原词：`上下文窗口（context window）`。
- 不写 `<br>` 控制段落间距；不加 `<div style="...">`。
- 颜色只用 token：`var(--accent)`、`var(--green)`、`var(--orange)`、`var(--red)`、`var(--muted)` 等，见 `main.css` 顶部。

---

## 5. 工具弹窗

### 5.1 触发按钮

每个工具一个按钮，`data-modal` 的值是弹窗 ID 去掉 `modal-` 前缀。8 个工具的 ID 固定为：

`codex`、`claude-code`、`pi`、`omp`、`opencode-v1`、`opencode-v2`、`grok-build`、`dsh`

```html
<div class="tool-grid">
  <button class="tool-btn" type="button" data-modal="codex">
    <span class="tool-btn__name">Codex CLI</span>
    <span class="tool-btn__id">codex</span>
  </button>
  <button class="tool-btn" type="button" data-modal="claude-code">
    <span class="tool-btn__name">Claude Code</span>
    <span class="tool-btn__id">claude-code</span>
  </button>
  <!-- 其余 6 个同样写 -->
</div>
```

### 5.2 弹窗本体

放在页面末尾、两个 `<script>` 之前。一章 7 个（或 8 个）弹窗，每个都要有唯一 ID。

```html
<div class="modal" id="modal-codex" hidden>
  <div class="modal__backdrop" data-close></div>
  <div class="modal__panel" role="dialog" aria-modal="true" aria-labelledby="modal-codex-title" tabindex="-1">
    <div class="modal__head">
      <div>
        <p class="modal__kicker">工具弹窗 · codex</p>
        <h2 class="modal__title" id="modal-codex-title">Codex CLI</h2>
      </div>
      <button class="modal__close" type="button" data-close aria-label="关闭弹窗">×</button>
    </div>
    <div class="modal__body">
      <p class="modal__lead">三到六句话：这个工具在这一类能力上做了什么。</p>
      <dl class="kv">
        <dt>关键参数</dt>
        <dd>参数名、默认值、触发阈值。<span class="tag tag--ok">已核实</span></dd>
        <dt>设计意图</dt>
        <dd>为什么这样做；代价是什么；和别家最大的差异。</dd>
        <dt>来源</dt>
        <dd><a href="https://github.com/.../blob/&lt;sha&gt;/path#L10-L40">path#L10-L40</a></dd>
      </dl>
      <p class="modal__note">源码与文档不一致时，在这里说明差异；不确定的结论标【待核实】。</p>
    </div>
  </div>
</div>
```

行为（由 `app.js` 提供，不用自己写）：

- 点 `[data-modal]` 打开；`Esc`、点遮罩、点 `[data-close]` 关闭。
- 地址后加 `#modal-codex` 可直接打开；关闭时自动清掉哈希。
- 打开时焦点进入弹窗，`Tab` 在弹窗内循环，关闭后焦点回到触发按钮。
- 同时只开一个弹窗，弹窗内容在 `.modal__body` 内滚动。

注意：`modal__title` 用 `h2`（页面里的 `h1` 已给章节标题），不要用 `h1`。

---

## 6. 8 工具对比表

窄屏横向滚动，第一列冻结。**必须**包在 `.table-wrap` 里，表头第一列写「工具」。

```html
<p class="table-hint">← 左右滑动查看全部列，首列固定 →</p>
<div class="table-wrap">
  <table class="data-table">
    <thead>
      <tr>
        <th scope="col">工具</th>
        <th scope="col">做法</th>
        <th scope="col">关键参数</th>
        <th scope="col">来源</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <th scope="row" class="cell-tool">Codex CLI<span>codex</span></th>
        <td>一句话做法。</td>
        <td><code>参数名</code>，默认值。</td>
        <td><span class="tag tag--ok">已核实</span></td>
      </tr>
      <tr>
        <th scope="row" class="cell-tool">Claude Code<span>claude-code</span></th>
        <td>一句话做法。</td>
        <td><code>参数名</code>，默认值。</td>
        <td><span class="tag tag--src">源码 v2.1.88</span></td>
      </tr>
      <!-- 其余 6 行 -->
    </tbody>
  </table>
</div>
<p class="table-caption">表注：版本、口径或需要提醒读者的差异。</p>
```

- 行首用 `<th scope="row" class="cell-tool">`，工具 ID 放在内层 `<span>` 里（会自动变成灰色小字）。
- 列多时不要减少到 3 列以下；宽屏靠 `min-width` 保证可读，窄屏靠容器滚动。
- 不要给表格加 `style="width:..."`，不要自己写 `overflow`。

---

## 7. 小测验

每章 3 道；题干先给，答案默认隐藏。

```html
<div class="quiz">
  <div class="quiz__head">
    <span class="quiz__no">Q1</span>
    <p class="quiz__q">题干：先让读者猜，再给答案。</p>
  </div>
  <button class="btn btn--small quiz__toggle" type="button" data-quiz-toggle aria-expanded="false">看答案</button>
  <div class="quiz__answer" hidden>
    <span class="quiz__label">解析</span>
    <p>答案与解析。说清“为什么”，不要只给结论。</p>
  </div>
</div>
```

- `data-quiz-toggle` 是唯一的钩子；按钮文字由 `app.js` 在「看答案 / 收起答案」之间切换。
- `.quiz__answer` 必须带 `hidden`，否则一开始就露答案。
- 答案里可以放 `<code>`、`<a>`、标签，但不要再嵌套 `.quiz`。

---

## 8. 带中文注释的代码块

整行注释用 `code__line--cmt`：绿色斜体 + 左侧色条 + 淡背景。行尾注释用 `<span class="cmt">`。

```html
<div class="codeblock" data-lang="ts">
  <div class="codeblock__bar">
    <span class="codeblock__lang">TypeScript</span>
    <button class="codeblock__copy" type="button" data-copy>复制</button>
  </div>
  <pre class="code"><code><span class="code__line code__line--cmt">// 中文注释：这一段在做什么</span>
<span class="code__line">const limit = 200_000; <span class="cmt">// 行尾注释</span></span>
<span class="code__line"> </span>
<span class="code__line code__line--cmt">// 空行也用一行空格占位，避免复制后行距塌陷</span>
<span class="code__line">function shouldCompact(used: number): boolean {</span>
<span class="code__line">  return used &gt; limit;</span>
<span class="code__line">}</span>
</code></pre>
</div>
```

规则：

- `<pre class="code"><code>` 里每行一个 `<span class="code__line">`。**行首不要缩进**，否则会带进复制文本。
- HTML 特殊字符转义：`<` → `&lt;`，`>` → `&gt;`，`&` → `&amp;`。
- 超过 20 行的源码摘录要拆成多块，或在正文里说明省略；Claude Code 单段不超过 15–20 行。
- 代码块上方的文件名/行号用正文写，不要塞进 `codeblock__lang`。
- `data-copy` 复制的是 `code.innerText`，会保留换行与注释；不要在里面放行号（行号会被复制走）。

---

## 9. 可信度标签

```html
<span class="tag tag--ok">已核实</span>
<span class="tag tag--guess">推断</span>
<span class="tag tag--todo">待核实</span>

<span class="tag tag--src">源码 v2.1.88</span>
<span class="tag tag--doc">官方文档</span>
<span class="tag tag--both">两者一致</span>
```

用法：

| class | 文案 | 什么时候用 |
|---|---|---|
| `tag--ok` | 已核实 | 源码或官方文档里直接看到，并附了链接 |
| `tag--guess` | 推断 | 根据结构/行为推断，没有直接文字依据 |
| `tag--todo` | 待核实 | 未核对，或两处来源冲突 |
| `tag--src` | 源码 v2.1.88 | Claude Code 结论来自 v2.1.88 源码 |
| `tag--doc` | 官方文档 | Claude Code 结论来自 Anthropic 文档 |
| `tag--both` | 两者一致 | 源码与文档一致；不一致时两边都写，不合并 |

- 标签放在结论句末，或表格「来源」列，不要堆在段首。
- 可以组合：`<span class="tag tag--ok">已核实</span> <span class="tag tag--both">两者一致</span>`。
- 标签不是来源链接的替代品；【已核实】必须能点到 permalink。
- 不要新增标签颜色；需要新类型时找主控。

---

## 10. Head First 卡片

### 场景引入（每章开头，且只出现一次）

用通用提示框承载，标题固定写成「场景 · 一句话点题」，紧跟一个具体时间、具体人物、具体失败现象的小故事。不要用 hf 系列，避免和后面的「动动脑 / 没有傻问题 / 要点」混淆。

```html
<div class="callout callout--info">
  <p class="callout__title">场景 · 它不是失忆，是看不见</p>
  <p>下午四点十分，你让 Agent 重构导出模块……（80–150 字，只讲现象，不讲原理）</p>
</div>
```

### 动动脑

```html
<div class="hf hf--think">
  <p class="hf__label"><span class="hf__icon" aria-hidden="true">?</span>动动脑</p>
  <div class="hf__body">
    <p>先抛一个问题，让读者停十秒。</p>
    <p class="small muted">提示：给一点线索，但不要直接给答案。</p>
  </div>
</div>
```

### 没有傻问题

```html
<div class="hf hf--qa">
  <p class="hf__label"><span class="hf__icon" aria-hidden="true">Q</span>没有傻问题</p>
  <div class="hf__body">
    <p class="hf__q">问：读者最可能卡住的那个问题。</p>
    <p class="hf__a">答：直接回答，必要时指回正文某节。</p>
  </div>
</div>
```

### 要点小结

```html
<div class="hf hf--takeaway">
  <p class="hf__label"><span class="hf__icon" aria-hidden="true">✓</span>要点小结</p>
  <div class="hf__body">
    <ul>
      <li>一句话一条，能单独成立。</li>
      <li>三到五条，不要超过六条。</li>
    </ul>
  </div>
</div>
```

- 三张卡片都用 `.hf` 基类 + 一个变体类，不要只写变体类。
- 卡片内的 `h3/h4` 不必要；需要小标题时用 `<strong>`。
- 图标字符固定为 `?`、`Q`、`✓`，不要换成 emoji。

---

## 11. SVG 图示

内联 SVG，容器负责边框和图注；SVG 只写 `viewBox`，不写 `width/height`。

```html
<figure class="fig">
  <svg viewBox="0 0 640 104" role="img" aria-labelledby="fig-1-title fig-1-desc">
    <title id="fig-1-title">图的标题</title>
    <desc id="fig-1-desc">给读屏软件的一句话描述，说明图里有什么、关系是什么。</desc>
    <rect class="svg-track" x="0" y="14" width="640" height="56" rx="8"/>
    <rect class="svg-seg--a" x="1" y="15" width="200" height="54" rx="7"/>
    <text class="svg-label" x="100" y="49" text-anchor="middle">系统提示</text>
    <line class="svg-rule" x1="1" y1="88" x2="639" y2="88"/>
  </svg>
  <figcaption>图 1　图注：这张图想让读者记住什么。</figcaption>
</figure>
```

- 可用的 SVG class：`.svg-track`、`.svg-seg--a`（蓝）、`.svg-seg--b`（青）、`.svg-seg--c`（橙）、`.svg-seg--free`（虚线）、`.svg-label`、`.svg-label--dark`、`.svg-note`、`.svg-rule`。
- 文字用 `font-family` 继承即可，不要写死字体。
- `viewBox` 建议 640 宽；标签 21px 左右。**重要信息不要只放在 `.svg-note` 里**：SVG 缩到手机宽度时字号会同比例缩小，必须让图注也把结论说一遍。
- 图示中的比例如果只是示意，必须在图注里写「示意，非真实比例」。
- 不要用外部图片代替 SVG；不要把大段正文塞进图里。
- **字号写在 `style` 里**：`<text class="svg-note" style="font-size:12px">`。写成 `font-size="12"` 属性会被 class 的 CSS 覆盖而失效，导致行重叠。
- 文字要留在所在矩形内、不超出 `viewBox`。`app.js` 的 `fitSvg()` 会在运行时兜底（缩小超框文字、拉开过近的行、扩大溢出的画布），但这只是保险，不要依赖它。
- 手机宽度（≤ 760px）下图示保持最小 540px 宽、可横向滑动，不再整体缩小。

---

## 12. 交互演示容器

结构固定：外框 `.demo`、头部 `.demo__head`、主体 `.demo__body`（左控制区 + 右画布区）、底部 `.demo__note`。

```html
<div class="demo" id="demo-compact">
  <div class="demo__head">
    <span class="demo__tag">交互演示</span>
    <h3 class="demo__title">压缩阈值与切点</h3>
  </div>
  <div class="demo__body">
    <div class="demo__controls">
      <label class="field" for="demo-compact-range">
        <span class="field__label">
          <span>触发阈值</span>
          <output class="field__value" id="demo-compact-out" for="demo-compact-range">80%</output>
        </span>
        <input id="demo-compact-range" type="range" min="50" max="95" step="1" value="80">
      </label>
      <button class="btn btn--ghost btn--small" type="button" id="demo-compact-reset">重置</button>
      <p class="demo__hint">一句话说明该拖哪里、看哪里。</p>
    </div>
    <div class="demo__canvas">
      <!-- 画布内容：条形、方块、会话树等 -->
    </div>
  </div>
  <p class="demo__note">数据是示意值，不是某工具的真实默认值。</p>
</div>
```

演示脚本放 `assets/js/demos/<名字>.js`，在页面末尾、`app.js` 之后引入：

```html
<script src="../assets/js/toc.js"></script>
<script src="../assets/js/app.js"></script>
<script src="../assets/js/demos/compact.js"></script>
```

脚本约定：

```js
(function () {
  "use strict";
  var root = document.getElementById("demo-compact");
  if (!root) return;

  var range = root.querySelector("input[type=range]");
  var out = root.querySelector("output");

  function render() {
    out.textContent = range.value + "%";
    /* 更新画布 */
  }

  range.addEventListener("input", render);
  var reset = root.querySelector("#demo-compact-reset");
  if (reset) reset.addEventListener("click", function () { range.value = "80"; render(); });
  render();
})();
```

- 每个演示一个 IIFE，不污染全局；需要提示时调用 `window.CTX.toast("...")`。
- 演示容器内**不要**再嵌套 `.demo`；多个演示并排时各自一个 `.demo`。
- 控件优先用原生 `input[type=range]`、`select`、`button`，不要引入 UI 库。
- 手机断点下 `.demo__body` 自动变成上下排列，脚本不用处理布局。

---

## 13. 辅助组件

### 脚注（【待核实】专用）

正文句末用上标引用，页尾用 `.footnotes` 收口。编号在页内唯一，格式 `fn-<章节ID>-<序号>`，回链 id 用 `fnref-` 前缀。

```html
<p>……这个上限只在客户端生效<sup class="fn-ref"><a href="#fn-main-02-1" id="fnref-main-02-1">1</a></sup>。</p>

<div class="footnotes">
  <p class="footnotes__title">脚注</p>
  <ol>
    <li id="fn-main-02-1">
      事实卡片标【待核实】：源码只找到单文件截断，未找到多文件合并后的总量上限；已检查 <code>AGENTS.md</code> 读取链路与 <code>WorldState</code> 组装处。结论按「单文件有上限、总量未知」表述。
      <a class="footnotes__back" href="#fnref-main-02-1">↩</a>
    </li>
  </ol>
</div>
```

规则：
- 只有【待核实】【推断】两类结论需要脚注；【已核实】给普通来源链接即可。
- 脚注里必须写「查了哪里、缺什么」，不要只写「待核实」三个字。
- 一页脚注超过 8 条时，说明该章事实密度有问题，回去合并同源结论（计量类章节如 main-05 允许到 8 条）。

### 提示框

```html
<div class="callout callout--info">
  <p class="callout__title">提示</p>
  <p>正文。</p>
</div>

<div class="callout callout--warn">
  <p class="callout__title">当心</p>
  <p>最容易踩的坑。</p>
</div>

<div class="callout callout--quiet">
  <p class="callout__title">补充</p>
  <p>不影响主线的说明。</p>
</div>
```

### 按钮

```html
<button class="btn" type="button">普通按钮</button>
<button class="btn btn--primary" type="button">主按钮</button>
<a class="btn btn--ghost btn--small" href="...">次要链接按钮</a>
```

### 章节头部信息

```html
<ul class="meta">
  <li>约 15 分钟</li>
  <li>3 个交互</li>
  <li>前置：intro-04</li>
</ul>
```

### 学习目标框

```html
<div class="learn">
  <h2>读完你能做到</h2>
  <ol>
    <li>可验证的目标一。</li>
    <li>可验证的目标二。</li>
  </ol>
</div>
```

### 工具标签（非交互）

需要显示工具 ID 时用 `<code>codex</code>` 或 `.tool-btn__id` 的写法；不要用彩色胶囊，除非是可信度标签。

---

## 14. JavaScript 钩子一览

| 钩子 | 作用 | 谁处理 |
|---|---|---|
| `body[data-chapter]` | 当前章节高亮、记录最近阅读 | `app.js` |
| `[data-modal="<id>"]` | 打开 `#modal-<id>` | `app.js` |
| `[data-close]` | 关闭所在弹窗 | `app.js` |
| `a[href="#modal-<id>"]` | 直接打开并写入哈希 | `app.js` |
| `[data-quiz-toggle]` | 展开/收起 `.quiz__answer` | `app.js` |
| `[data-copy]` | 复制所在 `.codeblock` 的代码 | `app.js` |
| `[data-recent-slot]` | 显示「继续上次阅读」卡片 | `app.js` |
| `[data-clear-recent]` | 清除阅读记录 | `app.js` |
| `#search-input` / `#search-results` | 标题搜索 | `app.js` |
| `#theme-btn` | 深浅色切换 | `app.js` |
| `#nav` / `#menu-btn` / `#nav-backdrop` | 导航与手机抽屉 | `app.js` |

页面里不要重复绑定这些事件，也不要把 `app.js` 的逻辑抄进章节。

---

## 15. 主题与本地存储

| key | 内容 | 写入方 |
|---|---|---|
| `ctx-theme` | `"light"` / `"dark"` | 主题按钮；未设置时跟随系统 |
| `ctx-nav-collapsed` | JSON，如 `{"main":true}` | 导航折叠 |
| `ctx-recent` | JSON：`{id,title,file,at}` | 打开已完成的章节时 |

- 主题变量定义在 `main.css` 的 `:root`、`@media (prefers-color-scheme: dark)`、`:root[data-theme="dark"]` 三处；写样式只用变量。
- 不要在章节里写 `data-theme` 初始化逻辑，模板已经包含。
- 不要新增 localStorage key；需要持久化时找主控。

---

## 16. 响应式断点

| 断点 | 行为 |
|---|---|
| ≥ 1360px | 右侧出现「本页目录」（由 h2/h3 自动生成）；表格、演示、代码块等宽组件最宽 1100px |
| > 1000px | 左侧固定导航（268px）；正文行宽 760px，宽组件随可用宽度放宽 |
| ≤ 1000px | 导航变抽屉，顶部出现菜单按钮，正文占满 |
| ≤ 760px | 正文 16px，工具按钮两列，演示上下排列，弹窗从底部升起 |
| ≤ 420px | 更紧的左右留白，搜索框缩小 |

写章节时不需要自己写媒体查询；用 grid/flex 时保证 `min-width: 0`，避免撑破容器。

---

## 17. 交付前自检

- [ ] `body[data-chapter]` 与文件名、`toc.js` 一致。
- [ ] 页面用 `../assets/...`，导航和品牌链接能回导读。
- [ ] 控制台无报错（file:// 与 http:// 各开一次）。
- [ ] 375px 下无横向滚动（表格自身滚动除外），弹窗可关闭。
- [ ] 每个弹窗有唯一 ID，`Esc`、遮罩、关闭按钮都有效。
- [ ] 测验默认收起，点开有解析。
- [ ] 代码块注释是中文，整行注释有左侧色条，复制出来是纯文本。
- [ ] 每条工具结论有来源；Claude Code 结论有来源类型标签。
- [ ] 每节首句接住了上一节的落点；新出现的角色（agent/运行时/模型）有交代。
- [ ] 产品写 agent、协议层写「工具」，没有把两者混用。
- [ ] 没有新增 class、没有内联样式、没有外部资源。
- [ ] 没有把「待写」章节的链接写成死链（正文引用未来章节时用文字说明，不硬链）。

---

## 18. 不要做的事

- 不要改 `toc.js`、`app.js`、`main.css`；需要改动时在交付说明里提出。
- 不要用 `type="module"`、`import`、`fetch`、`XMLHttpRequest` 加载本地文件。
- 不要引入 Tailwind、Bootstrap、Prism、highlight.js 等任何库。
- 不要用 emoji 当图标；Head First 卡片用固定字符。
- 不要写 `style="..."`（演示里动态设置宽度除外）。
- 不要复制参考样例里的 class 名；本手册之外的 class 一律视为不存在。
