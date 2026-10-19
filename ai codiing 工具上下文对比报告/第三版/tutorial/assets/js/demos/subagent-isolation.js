/* ============================================================
 * subagent-isolation.js —— 子代理上下文隔离演示
 * ------------------------------------------------------------
 * 教学示意，不是任何工具的真实计量：
 * 1. 父会话只增加两段：任务描述、最终返回。
 * 2. 子会话在自己的上下文里跑 7 步，全部标为 internal。
 * 3. 返回形态可切换：结构化 JSON 180 token / 自由文本 1350 token。
 * 依赖：无。纯 DOM。
 * ============================================================ */
(function () {
  "use strict";

  var root = document.getElementById("demo-subagent-isolation");
  if (!root) return;

  var BASE_TOKENS = 1200;
  var TASK_TOKENS = 160;
  var CHILD_TOTAL = 34200;

  var BASE = [
    { role: "用户", text: "导出模块有循环依赖。查清环在哪，给最小修复方案，不要动 public API。", cls: "sub-msg--user" },
    { role: "助手", text: "这个搜索会读很多文件。我派一个只读子代理去找，父会话只收结论。", cls: "sub-msg--assistant" }
  ];

  var STEPS = [
    { role: "工具调用 · grep", text: "grep \"from './export\" src/ → 37 处命中", tokens: 4400 },
    { role: "工具结果 · read", text: "src/export/index.ts：812 行，含 14 个 re-export", tokens: 9900 },
    { role: "工具结果 · read", text: "src/export/legacy.ts：244 行，运行时引用 index", tokens: 3200 },
    { role: "工具调用 · grep", text: "grep \"legacy\" src/ → 6 个调用点", tokens: 1700 },
    { role: "工具结果 · test", text: "run tests export → 2 failed，栈都指向 legacy.ts", tokens: 12500 },
    { role: "助手 · 推理", text: "环是 index → legacy → index；值导入是唯一原因。", tokens: 1600 },
    { role: "助手 · 草稿", text: "建议 legacy 改 type-only import；风险低，不动导出名。", tokens: 900 }
  ];

  var RETURN = {
    json: "{\n  \"status\": \"done\",\n  \"cycle\": [\"src/export/index.ts\", \"src/export/legacy.ts\"],\n  \"evidence\": [\"grep: 37 hits\", \"tests: 2 failed\"],\n  \"fix\": \"legacy.ts 改为 type-only import\",\n  \"risk\": \"low\",\n  \"files\": 2\n}",
    free: "我把 src/ 下所有 export 相关引用都过了一遍，一共 37 处命中。先读了 index.ts（812 行），又读了 legacy.ts（244 行），然后 grep legacy 找到 6 个调用点。跑了一次 export 相关测试，2 个失败，失败栈都指向 legacy.ts 对 index.ts 的运行时引用。\n\n结论：环是 index.ts → legacy.ts → index.ts。最小修复是把 legacy.ts 里对 index.ts 的值导入改成 type-only import，不动 public API。建议先改 legacy.ts，再跑同一组测试；如果还有失败，再看 core.ts 的 re-export。"
  };

  var state = {
    phase: "idle",      // idle | running | done
    form: "json",
    collapsed: false,
    shown: 0,
    runId: 0,
    timer: 0
  };

  var runBtn = root.querySelector("#sub-run");
  var toggleBtn = root.querySelector("#sub-toggle");
  var resetBtn = root.querySelector("#sub-reset");
  var formBtns = root.querySelectorAll("[data-sub-form]");
  var kpis = root.querySelector("#sub-kpis");
  var parentBox = root.querySelector("#sub-parent");
  var childBox = root.querySelector("#sub-child");
  var childPane = root.querySelector("#sub-child-pane");
  var folded = root.querySelector("#sub-folded");
  var parentFoot = root.querySelector("#sub-parent-foot");
  var childFoot = root.querySelector("#sub-child-foot");
  var status = root.querySelector("#sub-status");

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function fmt(value) {
    return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function shownTokens() {
    var sum = 0;
    for (var i = 0; i < state.shown && i < STEPS.length; i++) sum += STEPS[i].tokens;
    return sum;
  }

  function returnTokens() {
    return state.form === "json" ? 180 : 1350;
  }

  function parentTokens() {
    var n = BASE_TOKENS;
    if (state.phase !== "idle") n += TASK_TOKENS;
    if (state.phase === "done") n += returnTokens();
    return n;
  }

  function parentDelta() {
    var n = 0;
    if (state.phase !== "idle") n += TASK_TOKENS;
    if (state.phase === "done") n += returnTokens();
    return n;
  }

  function addMessage(box, role, text, cls) {
    var node = el("div", "sub-msg" + (cls ? " " + cls : ""));
    node.appendChild(el("span", "sub-msg__role", role));
    if (text.indexOf("\n") >= 0) {
      var pre = el("pre", "sub-json", text);
      node.appendChild(pre);
    } else {
      node.appendChild(document.createTextNode(text));
    }
    box.appendChild(node);
  }

  function renderParent() {
    parentBox.textContent = "";

    BASE.forEach(function (m) {
      addMessage(parentBox, m.role, m.text, m.cls);
    });

    if (state.phase === "running" || state.phase === "done") {
      parentBox.appendChild(el("p", "sub-cut", "父会话只增加下面两段"));
      addMessage(
        parentBox,
        "父 → 子 · 任务描述",
        "在 src/ 中定位 export 循环依赖；只读；返回环路径、证据、最小改动建议；不要动 public API。",
        "sub-msg--task"
      );
    }

    if (state.phase === "done") {
      var role = state.form === "json" ? "子 → 父 · 结构化返回（180 token）" : "子 → 父 · 自由文本返回（1,350 token）";
      addMessage(parentBox, role, RETURN[state.form], "sub-msg--return");
    }

    parentBox.scrollTop = parentBox.scrollHeight;
    parentFoot.textContent = "父上下文 " + fmt(parentTokens()) + " token · 新增 " + fmt(parentDelta());
  }

  function renderChild() {
    childBox.textContent = "";

    if (state.phase === "idle") {
      childBox.appendChild(el("p", "sub-empty", "尚未派发。子会话创建后，这里的每一步都不会进入父上下文。"));
    } else {
      for (var i = 0; i < state.shown; i++) {
        var step = STEPS[i];
        addMessage(childBox, step.role + " · " + fmt(step.tokens) + " tok", step.text, "sub-msg--internal");
      }
      if (state.phase === "running" && state.shown < STEPS.length) {
        childBox.appendChild(el("p", "sub-empty", "第 " + (state.shown + 1) + " / " + STEPS.length + " 步…"));
      }
      childBox.scrollTop = childBox.scrollHeight;
    }

    var childNow = state.shown ? shownTokens() : 0;
    childFoot.textContent =
      "子上下文 " + fmt(childNow) + " token" + (state.phase === "done" ? " · 峰值 " + fmt(CHILD_TOTAL) : "");

    var isCollapsed = state.collapsed;
    if (isCollapsed) childBox.classList.add("is-hidden");
    else childBox.classList.remove("is-hidden");
    folded.hidden = !isCollapsed;
    if (isCollapsed) {
      var text;
      if (state.phase === "idle") {
        text = "子会话尚未创建。";
      } else if (state.phase === "running") {
        text = "子会话运行中：已执行 " + state.shown + " / " + STEPS.length + " 步。这些输出不会进入父上下文。";
      } else {
        text = "子会话已完成：7 步 · " + fmt(CHILD_TOTAL) + " token。中间 7 段工具与推理从不进入父上下文；父只收到 " + fmt(returnTokens()) + " token 的" + (state.form === "json" ? "结构化" : "自由文本") + "返回。";
      }
      folded.textContent = text;
    }
  }

  function renderKpis() {
    kpis.textContent = "";
    var delta = parentDelta();
    var childNow = state.phase === "done" ? CHILD_TOTAL : shownTokens();
    var pct = delta + childNow > 0 ? (delta / (delta + childNow)) * 100 : 0;

    var items = [
      {
        k: "父上下文",
        v: fmt(parentTokens()) + " tok",
        s: state.phase === "idle" ? "初始 1,200" : "初始 1,200 + 任务 160" + (state.phase === "done" ? " + 返回 " + fmt(returnTokens()) : "")
      },
      {
        k: "子会话",
        v: state.phase === "idle" ? "—" : (state.phase === "done" ? "34.2k tok" : fmt(childNow) + " tok"),
        s: "7 步工具与推理"
      },
      {
        k: "父会话新增",
        v: fmt(delta) + " tok",
        s: "占本次总量 " + (pct < 0.05 ? "0" : pct.toFixed(1)) + "%"
      }
    ];

    items.forEach(function (item) {
      var box = el("div", "sub-kpi");
      box.appendChild(el("span", "sub-kpi__k", item.k));
      box.appendChild(el("span", "sub-kpi__v", item.v));
      box.appendChild(el("span", "sub-kpi__s", item.s));
      kpis.appendChild(box);
    });
  }

  function renderControls() {
    var running = state.phase === "running";
    runBtn.disabled = running;
    runBtn.textContent = running ? "子会话运行中…" : (state.phase === "done" ? "再派发一次" : "派发一次任务");
    toggleBtn.textContent = state.collapsed ? "展开子会话" : "收起子会话";
    toggleBtn.setAttribute("aria-expanded", state.collapsed ? "false" : "true");
    formBtns.forEach(function (btn) {
      btn.setAttribute("aria-pressed", btn.getAttribute("data-sub-form") === state.form ? "true" : "false");
    });
  }

  function renderStatus() {
    if (state.phase === "idle") {
      status.textContent = "尚未派发。点“派发一次任务”，观察左栏只增加两段。";
    } else if (state.phase === "running") {
      status.textContent = "子会话运行中：第 " + state.shown + " / " + STEPS.length + " 步。父会话的 token 计数目前只增加了任务描述。";
    } else {
      status.textContent =
        "子会话结束：7 步、" + fmt(CHILD_TOTAL) + " token 全部留在右栏；父会话新增 " +
        fmt(parentDelta()) + " token（任务 160 + 返回 " + fmt(returnTokens()) + "）。";
    }
  }

  function render() {
    renderParent();
    renderChild();
    renderKpis();
    renderControls();
    renderStatus();
  }

  function step() {
    var id = state.runId;
    if (state.shown >= STEPS.length) {
      state.phase = "done";
      render();
      return;
    }
    state.shown += 1;
    render();
    state.timer = window.setTimeout(function () {
      if (id !== state.runId) return;
      step();
    }, 420);
  }

  function start() {
    if (state.phase === "running") return;
    state.runId += 1;
    window.clearTimeout(state.timer);
    state.phase = "running";
    state.shown = 0;
    render();
    state.timer = window.setTimeout(step, 260);
  }

  runBtn.addEventListener("click", start);

  toggleBtn.addEventListener("click", function () {
    state.collapsed = !state.collapsed;
    render();
  });

  formBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var next = btn.getAttribute("data-sub-form");
      if (next === state.form) return;
      state.form = next;
      render();
      if (state.phase === "done") {
        status.textContent =
          "返回形态已切换：" + (next === "json" ? "结构化 JSON" : "自由文本") +
          "。父会话新增从 " + (next === "json" ? "1,510" : "340") + " token 变为 " +
          fmt(parentDelta()) + " token；子会话内部仍不进入父上下文。";
      } else {
        status.textContent =
          "返回形态已改为" + (next === "json" ? "结构化 JSON" : "自由文本") +
          "。派发后父会话将新增 " + (next === "json" ? "340" : "1,510") +
          " token（任务 160 + 返回 " + fmt(returnTokens()) + "）。";
      }
    });
  });

  resetBtn.addEventListener("click", function () {
    state.runId += 1;
    window.clearTimeout(state.timer);
    state.phase = "idle";
    state.shown = 0;
    state.collapsed = false;
    render();
  });

  render();
})();
