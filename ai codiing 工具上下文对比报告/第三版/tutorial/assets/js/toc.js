/* ============================================================
 * toc.js —— 教程导航清单（唯一来源）
 * ------------------------------------------------------------
 * 新增一章：在本文件登记 + 新建页面文件，导航自动出现。
 * file 路径一律相对 tutorial/ 根目录，不要写 ./ 或 ../。
 * no 为全书连续章号；附录用 label（如「附录 A」）。
 * status: "done"（有正文）| "todo"（待写，导航显示“待写”）
 * ============================================================ */
window.TOC = {
  version: "2026-10-18",

  /* 导读单独放在五组之外，固定显示在导航顶部 */
  home: {
    id: "intro-00",
    title: "导读",
    file: "index.html",
    status: "done"
  },

  groups: [
    {
      id: "intro",
      part: "第一部分",
      title: "入门",
      hint: "L1–L2 · Head First 风格",
      chapters: [
        { id: "intro-01", no: 1, title: "上下文窗口是什么", file: "pages/intro-01.html", status: "done" },
        { id: "intro-02", no: 2, title: "一次请求里装了什么", file: "pages/intro-02.html", status: "done" },
        { id: "intro-03", no: 3, title: "Agent 循环中上下文如何增长", file: "pages/intro-03.html", status: "done" },
        { id: "intro-04", no: 4, title: "窗口装得下，不等于模型用得好", file: "pages/intro-04.html", status: "done" },
        { id: "intro-05", no: 5, title: "Prompt cache 与成本", file: "pages/intro-05.html", status: "done" },
        { id: "intro-06", no: 6, title: "用户侧怎么管理上下文：决策流程图", file: "pages/intro-06.html", status: "done" },
        { id: "intro-07", no: 7, title: "总流程图", file: "pages/intro-07.html", status: "done" },
      ]
    },
    {
      id: "main",
      part: "第二部分",
      title: "主线",
      hint: "16 类能力 · L2→L3",
      chapters: [
        { id: "main-01", no: 8, title: "请求组装：系统提示词与工具定义", file: "pages/main-01.html", status: "done" },
        { id: "main-02", no: 9, title: "规则文件的发现与合并", file: "pages/main-02.html", status: "done" },
        { id: "main-03", no: 10, title: "按需加载与渐进披露", file: "pages/main-03.html", status: "done" },
        { id: "main-04", no: 11, title: "动态注入：提醒、状态与增量", file: "pages/main-04.html", status: "done" },
        { id: "main-05", no: 12, title: "Token 计量与可视化", file: "pages/main-05.html", status: "done" },
        { id: "main-06", no: 13, title: "单次工具输出控制", file: "pages/main-06.html", status: "done" },
        { id: "main-07", no: 14, title: "历史裁剪：不调用模型的减量", file: "pages/main-07.html", status: "done" },
        { id: "main-08", no: 15, title: "压缩：把历史换成摘要", file: "pages/main-08.html", status: "done" },
        { id: "main-09", no: 16, title: "多模态上下文", file: "pages/main-09.html", status: "done" },
        { id: "main-10", no: 17, title: "子代理隔离", file: "pages/main-10.html", status: "done" },
        { id: "main-11", no: 18, title: "会话时间线：恢复、分叉与回退", file: "pages/main-11.html", status: "done" },
        { id: "main-12", no: 19, title: "跨会话记忆", file: "pages/main-12.html", status: "done" },
        { id: "main-13", no: 20, title: "缓存友好设计", file: "pages/main-13.html", status: "done" },
        { id: "main-14", no: 21, title: "失败恢复：溢出、压缩失败与兜底", file: "pages/main-14.html", status: "done" },
        { id: "main-15", no: 22, title: "扩展点：hooks 与插件", file: "pages/main-15.html", status: "done" },
        { id: "main-16", no: 23, title: "评估与可观测：指标与 A/B", file: "pages/main-16.html", status: "done" },
      ]
    },
    {
      id: "adv",
      part: "第三部分",
      title: "进阶",
      hint: "L4 · 取舍与评估",
      chapters: [
        { id: "adv-01", no: 24, title: "设计取舍专题", file: "pages/adv-01.html", status: "done" },
        { id: "adv-02", no: 25, title: "失败案例分析", file: "pages/adv-02.html", status: "done" },
        { id: "adv-03", no: 26, title: "架构对比", file: "pages/adv-03.html", status: "done" },
        { id: "adv-04", no: 27, title: "设计你自己的上下文策略", file: "pages/adv-04.html", status: "done" },
        { id: "adv-05", no: 28, title: "评估方法：L5 入门", file: "pages/adv-05.html", status: "done" },
      ]
    },
    {
      id: "src",
      part: "第四部分",
      title: "源码",
      hint: "固定提交 · 逐行注释",
      chapters: [
        { id: "src-codex-01", no: 29, title: "Codex · 压缩保留谁：候选与预算", file: "pages/src-codex-01.html", status: "done" },
        { id: "src-codex-02", no: 30, title: "Codex · 请求四块与增量工具", file: "pages/src-codex-02.html", status: "done" },
        { id: "src-codex-03", no: 31, title: "Codex · 规则差分：只发变化", file: "pages/src-codex-03.html", status: "done" },
        { id: "src-codex-04", no: 32, title: "Codex · 头尾保留的截断预算", file: "pages/src-codex-04.html", status: "done" },
        { id: "src-claude-code-01", no: 33, title: "Claude Code · 系统提示的静态/动态分段", file: "pages/src-claude-code-01.html", status: "done" },
        { id: "src-claude-code-02", no: 34, title: "Claude Code · 只有一个消息级缓存断点", file: "pages/src-claude-code-02.html", status: "done" },
        { id: "src-claude-code-03", no: 35, title: "Claude Code · 压缩后重附清单", file: "pages/src-claude-code-03.html", status: "done" },
        { id: "src-claude-code-04", no: 36, title: "Claude Code · 只注入变化的附件 delta", file: "pages/src-claude-code-04.html", status: "done" },
        { id: "src-pi-01", no: 37, title: "pi · 切点、单回合拆分与文件跟踪", file: "pages/src-pi-01.html", status: "done" },
        { id: "src-pi-02", no: 38, title: "pi · 压缩只改投影，不删历史", file: "pages/src-pi-02.html", status: "done" },
        { id: "src-pi-03", no: 39, title: "pi · 用 section 补丁保住前缀缓存", file: "pages/src-pi-03.html", status: "done" },
        { id: "src-omp-01", no: 40, title: "oh-my-pi · 压缩方法链与回退", file: "pages/src-omp-01.html", status: "done" },
        { id: "src-omp-02", no: 41, title: "oh-my-pi · shake 的机械省略", file: "pages/src-omp-02.html", status: "done" },
        { id: "src-omp-03", no: 42, title: "oh-my-pi · snapcompact 把历史渲成图", file: "pages/src-omp-03.html", status: "done" },
        { id: "src-opencode-v1-01", no: 43, title: "opencode v1 · 切点：整轮边界与预算", file: "pages/src-opencode-v1-01.html", status: "done" },
        { id: "src-opencode-v1-02", no: 44, title: "opencode v1 · prune：默认关闭的旧结果擦除", file: "pages/src-opencode-v1-02.html", status: "done" },
        { id: "src-opencode-v1-03", no: 45, title: "opencode v1 · filterCompacted 重排替代历史", file: "pages/src-opencode-v1-03.html", status: "done" },
        { id: "src-opencode-v2-01", no: 46, title: "opencode v2 · 三入口触发与 due 判定", file: "pages/src-opencode-v2-01.html", status: "done" },
        { id: "src-opencode-v2-02", no: 47, title: "opencode v2 · 检查点：一条消息 + seq 边界", file: "pages/src-opencode-v2-02.html", status: "done" },
        { id: "src-opencode-v2-03", no: 48, title: "opencode v2 · 指令 epoch 推进", file: "pages/src-opencode-v2-03.html", status: "done" },
        { id: "src-grok-build-01", no: 49, title: "Grok Build · 自动压缩与 7 段装配", file: "pages/src-grok-build-01.html", status: "done" },
        { id: "src-grok-build-02", no: 50, title: "Grok Build · 零成本裁剪：软裁剪与硬清空", file: "pages/src-grok-build-02.html", status: "done" },
        { id: "src-grok-build-03", no: 51, title: "Grok Build · append-only 日志如何回退", file: "pages/src-grok-build-03.html", status: "done" },
        { id: "src-dsh-01", no: 52, title: "DeepSeek Harness · 日志与 surface 两层结构", file: "pages/src-dsh-01.html", status: "done" },
        { id: "src-dsh-02", no: 53, title: "DeepSeek Harness · 压缩选区的三个约束", file: "pages/src-dsh-02.html", status: "done" },
        { id: "src-dsh-03", no: 54, title: "DeepSeek Harness · 裁剪器与影子计价", file: "pages/src-dsh-03.html", status: "done" },
      ]
    },
    {
      id: "appendix",
      part: "",
      title: "附录",
      hint: "速查与延伸",
      chapters: [
        { id: "appendix-glossary", label: "附录 A", title: "术语表（中英对照）", file: "pages/appendix-glossary.html", status: "done" },
        { id: "appendix-params", label: "附录 B", title: "参数速查表", file: "pages/appendix-params.html", status: "done" },
        { id: "appendix-matrix", label: "附录 C", title: "16 类 × 8 agent总表", file: "pages/appendix-matrix.html", status: "done" },
        { id: "appendix-reading", label: "附录 D", title: "推荐阅读", file: "pages/appendix-reading.html", status: "done" },
        { id: "appendix-video", label: "附录 E", title: "视频分镜脚本", file: "pages/appendix-video.html", status: "done" },
      ]
    }
  ],

  /* 供后续章节或脚本查表使用：不参与导航渲染 */
  notes: {
    src: "源码共 26 章：Codex 4、Claude Code 4、其余 6 个工具各 3；每章讲一个功能并固定到提交。",
    status: "status 为 todo 时，导航显示“待写”，点击给出提示，不跳转。"
  }
};
