(function () {
  "use strict";

  var root = document.getElementById("demo-cache-hit");
  if (!root) return;

  /* 两档示意单价：元 / 千 token；未命中统一按普通输入，不模拟缓存写费。 */
  var PRICE = { read: 0.002, miss: 0.02 };

  /* 七个块：名字、初始长度、初始内容 */
  var BLOCKS = [
    { name: "系统提示", tokens: 8000, text: "你是编程助手，先读代码再改。" },
    { name: "工具定义", tokens: 14000, text: "read_file, write_file, run_tests, search" },
    { name: "规则文件", tokens: 3200, text: "不要改 schema；测试用 pnpm。" },
    { name: "环境信息", tokens: 700, text: "cwd=/repo  branch=main" },
    { name: "历史（第 1–3 轮）", tokens: 6500, text: "用户：登录 500。助手：先看日志。" },
    { name: "历史（第 4–6 轮）", tokens: 7200, text: "助手：定位到探活。用户：继续。" },
    { name: "你这句话", tokens: 260, text: "把探活改成可配置的。" }
  ];

  var baseTokens = BLOCKS.map(function (b) { return b.tokens; });
  var baseTexts = BLOCKS.map(function (b) { return b.text; });
  var tokens = baseTokens.slice();
  var texts = baseTexts.slice();
  var selected = 0;

  var bar = document.getElementById("ch-bar");
  var list = document.getElementById("ch-list");
  var mark = document.getElementById("ch-mark");
  var markLabel = document.getElementById("ch-mark-label");
  var hitEl = document.getElementById("ch-hit");
  var breakEl = document.getElementById("ch-break");
  var costEl = document.getElementById("ch-cost");
  var extraEl = document.getElementById("ch-extra");
  var srEl = document.getElementById("ch-sr");
  var textInput = document.getElementById("ch-text");
  var lenRange = document.getElementById("ch-len");
  var lenOut = document.getElementById("ch-len-out");
  var selName = document.getElementById("ch-sel-name");
  var rows = Array.prototype.slice.call(list.querySelectorAll(".ch-row"));

  if (!bar || !rows.length || !textInput || !lenRange) return;

  var segs = BLOCKS.map(function (b, i) {
    var el = document.createElement("span");
    el.className = "ch-seg";
    bar.appendChild(el);
    return el;
  });

  function fmt(n) {
    return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function sum(arr, from, to) {
    var s = 0;
    for (var i = from; i < to; i++) s += arr[i];
    return s;
  }

  function total() {
    return sum(tokens, 0, tokens.length);
  }

  /* 失效点：第一个与基准不同的块；-1 表示完全一致 */
  function breakIndex() {
    for (var i = 0; i < BLOCKS.length; i++) {
      if (texts[i] !== baseTexts[i] || tokens[i] !== baseTokens[i]) return i;
    }
    return -1;
  }

  function compute() {
    var t = total();
    var k = breakIndex();
    var hit = k < 0 ? t : sum(tokens, 0, k);
    var changed = k < 0 ? 0 : tokens[k];
    var rest = k < 0 ? 0 : sum(tokens, k + 1, tokens.length);

    var cost = (hit * PRICE.read + (changed + rest) * PRICE.miss) / 1000;
    var ideal = (t * PRICE.read) / 1000;

    return { total: t, k: k, hit: hit, changed: changed, rest: rest, cost: cost, extra: cost - ideal };
  }

  function render() {
    var r = compute();

    segs.forEach(function (seg, i) {
      var share = r.total ? tokens[i] / r.total : 0;
      var state = "miss";
      if (r.k < 0 || i < r.k) state = "hit";
      else if (i === r.k) state = "write";

      seg.className = "ch-seg ch-seg--" + state;
      seg.style.width = share * 100 + "%";

      var row = rows[i];
      row.setAttribute("data-state", state);
      row.setAttribute("aria-pressed", i === selected ? "true" : "false");
      row.querySelector(".ch-row__num").textContent = fmt(tokens[i]);
      row.querySelector(".ch-row__state").textContent =
        state === "hit" ? "命中" : state === "write" ? "改动" : "重算";
      row.querySelector(".ch-row__name").textContent = (i + 1) + " · " + BLOCKS[i].name;
    });

    if (r.k < 0) {
      mark.style.display = "none";
    } else {
      mark.style.display = "block";
      var pct = r.total ? (r.hit / r.total) * 100 : 0;
      mark.style.left = pct + "%";
      mark.setAttribute("data-edge", pct > 62 ? "right" : "left");
      markLabel.textContent = "失效点";
    }

    hitEl.textContent = fmt(r.hit) + " token";
    breakEl.textContent = r.k < 0
      ? "失效点：无（七块全部命中）"
      : "失效点：第 " + (r.k + 1) + " 块「" + BLOCKS[r.k].name + "」";
    costEl.textContent = r.cost.toFixed(3) + " 元";
    extraEl.textContent = r.extra > 0.0005 ? "+" + r.extra.toFixed(3) + " 元" : "≈ 0 元";

    root.setAttribute("data-level", r.k >= 0 && r.hit / (r.total || 1) < 0.5 ? "bad" : "ok");

    if (srEl) {
      srEl.textContent =
        "命中前缀 " + fmt(r.hit) + " token；" +
        (r.k < 0 ? "没有失效点" : "失效点在第 " + (r.k + 1) + " 块" + BLOCKS[r.k].name + "开头") +
        "；比全命中多付 " + r.extra.toFixed(3) + " 元。";
    }
  }

  function syncControls() {
    var min = Math.round(baseTokens[selected] * 0.4 / 100) * 100;
    var max = Math.round(baseTokens[selected] * 1.6 / 100) * 100;

    selName.textContent = BLOCKS[selected].name;
    textInput.value = texts[selected];
    lenRange.min = String(min);
    lenRange.max = String(max);
    lenRange.value = String(tokens[selected]);
    lenOut.textContent = fmt(tokens[selected]);
  }

  function select(i) {
    if (i < 0 || i >= BLOCKS.length) return;
    selected = i;
    syncControls();
    render();
  }

  rows.forEach(function (row) {
    row.addEventListener("click", function () {
      select(parseInt(row.getAttribute("data-i"), 10));
    });
  });

  textInput.addEventListener("input", function () {
    texts[selected] = textInput.value;
    render();
  });

  lenRange.addEventListener("input", function () {
    tokens[selected] = parseInt(lenRange.value, 10) || baseTokens[selected];
    lenOut.textContent = fmt(tokens[selected]);
    render();
  });

  function resetAll() {
    texts = baseTexts.slice();
    tokens = baseTokens.slice();
  }

  var presetTail = document.getElementById("ch-preset-tail");
  if (presetTail) {
    presetTail.addEventListener("click", function () {
      resetAll();
      var last = BLOCKS.length - 1;
      texts[last] = baseTexts[last] + "（先跑测试）";
      selected = last;
      syncControls();
      render();
    });
  }

  var presetHead = document.getElementById("ch-preset-head");
  if (presetHead) {
    presetHead.addEventListener("click", function () {
      resetAll();
      texts[0] = baseTexts[0] + "（v2）";
      selected = 0;
      syncControls();
      render();
    });
  }

  var resetBtn = document.getElementById("ch-reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      resetAll();
      selected = 0;
      syncControls();
      render();
    });
  }

  select(0);
})();
