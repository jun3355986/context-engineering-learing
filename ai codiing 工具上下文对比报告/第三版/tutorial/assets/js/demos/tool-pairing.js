/* ============================================================
 * tool-pairing.js —— 工具调用与结果必须整对保留
 * ------------------------------------------------------------
 * 一条 12 条消息的时间线，切点可在 0…12 之间移动。
 * 合法切点不能落在 call 与它的 result 之间。
 * 依赖：无。纯 DOM + Pointer Events（不支持时仍可用方向键）。
 * ============================================================ */
(function () {
  "use strict";

  var root = document.getElementById("demo-tool-pairing");
  if (!root) return;

  var ITEMS = [
    { role: "user", text: "重构导出模块，别动 public API。", tokens: 4000 },
    { role: "assistant", text: "先看 package.json。", tokens: 5000 },
    { role: "call", text: "read package.json", tokens: 2000, pair: "A" },
    { role: "result", text: "依赖与 scripts", tokens: 16000, pair: "A" },
    { role: "assistant", text: "再找调用方。", tokens: 5000 },
    { role: "call", text: "grep \"export\" src/", tokens: 2000, pair: "B" },
    { role: "result", text: "37 个文件命中", tokens: 18000, pair: "B" },
    { role: "user", text: "public API 保持兼容。", tokens: 4500 },
    { role: "call", text: "run tests", tokens: 2000, pair: "C" },
    { role: "result", text: "2 failed / 118 passed", tokens: 20000, pair: "C" },
    { role: "assistant", text: "改了 3 个调用方。", tokens: 9000 },
    { role: "user", text: "继续，把剩下的也改完。", tokens: 3500 }
  ];

  var PAIRS = [
    { call: 2, result: 3, name: "read package.json" },
    { call: 5, result: 6, name: "grep \"export\"" },
    { call: 8, result: 9, name: "run tests" }
  ];

  var ROLE_LABEL = {
    user: "用户",
    assistant: "助手",
    call: "调用",
    result: "结果"
  };
  var ROLE_SHORT = {
    user: "U",
    assistant: "A",
    call: "C",
    result: "R"
  };

  var track = root.querySelector("#pair-strip");
  var handle = root.querySelector("#pair-handle");
  var rows = root.querySelector("#pair-rows");
  var status = root.querySelector("#pair-status");
  var detail = root.querySelector("#pair-detail");
  var snap = root.querySelector("#pair-snap");
  var reset = root.querySelector("#pair-reset");

  var cut = 5;
  var drag = false;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function brokenPair(position) {
    for (var i = 0; i < PAIRS.length; i++) {
      if (PAIRS[i].call < position && position <= PAIRS[i].result) {
        return { pair: PAIRS[i], index: i };
      }
    }
    return null;
  }

  function legalPositions() {
    var out = [];
    for (var i = 0; i <= ITEMS.length; i++) {
      if (!brokenPair(i)) out.push(i);
    }
    return out;
  }

  function nearestLegal(position) {
    var legal = legalPositions();
    var best = legal[0];
    var bestDist = Math.abs(best - position);
    for (var i = 1; i < legal.length; i++) {
      var d = Math.abs(legal[i] - position);
      if (d < bestDist) {
        best = legal[i];
        bestDist = d;
      }
    }
    return best;
  }

  function countPairs(from) {
    var count = 0;
    PAIRS.forEach(function (pair) {
      if (pair.call >= from) count++;
    });
    return count;
  }

  function render() {
    var broken = brokenPair(cut);
    /* 时间线条：只重建消息格，保留切点手柄这个真实按钮 */
    Array.prototype.slice.call(track.querySelectorAll(".pair-cell")).forEach(function (node) {
      track.removeChild(node);
    });
    ITEMS.forEach(function (item, index) {
      var cell = el("span", "pair-cell pair-cell--" + item.role);
      cell.appendChild(el("b", null, ROLE_SHORT[item.role]));
      cell.appendChild(el("i", null, item.pair || ""));
      cell.title = (index + 1) + " · " + ROLE_LABEL[item.role] + " · " + item.text;
      if (index < cut) cell.classList.add("is-before");
      if (broken && (index === broken.pair.call || index === broken.pair.result)) {
        cell.classList.add("is-broken");
      }
      track.appendChild(cell);
    });
    track.appendChild(handle);

    handle.style.left = (cut / ITEMS.length) * 100 + "%";
    handle.setAttribute("aria-valuenow", String(cut));
    handle.setAttribute("aria-valuetext", "保留段从第 " + (cut + 1) + " 条开始");

    /* 明细表 */
    rows.textContent = "";
    ITEMS.forEach(function (item, index) {
      var row = el("div", "pair-row");
      if (index < cut) row.classList.add("is-summary");
      else row.classList.add("is-kept");
      if (broken && (index === broken.pair.call || index === broken.pair.result)) {
        row.classList.add("is-broken");
      }
      row.appendChild(el("span", "pair-idx", index < 9 ? "0" + (index + 1) : String(index + 1)));
      row.appendChild(el("span", "pair-role", ROLE_LABEL[item.role]));
      row.appendChild(el("span", "pair-text", item.text));
      row.appendChild(el("span", "pair-tok", (item.tokens / 1000) + "k"));
      rows.appendChild(row);
    });

    if (broken) {
      status.className = "pair-status pair-status--bad";
      status.textContent = "非法切点";
      detail.className = "pair-detail pair-detail--bad";
      detail.textContent =
        "会把第 " + (broken.pair.call + 1) + " 条的调用留在摘要里、第 " +
        (broken.pair.result + 1) + " 条的结果丢进保留段。结果是：保留段里出现一条没有对应调用的工具结果，" +
        "多数 API 会直接报错，模型也可能把这段输出当成新的用户输入。";
    } else {
      status.className = "pair-status pair-status--ok";
      status.textContent = "合法切点";
      detail.className = "pair-detail pair-detail--ok";
      detail.textContent =
        "保留段从第 " + (cut + 1) + " 条开始，共 " + countPairs(cut) +
        " 对完整配对；摘要段包含 " + cut + " 条消息。";
    }
  }

  function setCut(next) {
    cut = Math.max(0, Math.min(ITEMS.length, Math.round(next)));
    render();
  }

  function fromPointer(event) {
    var rect = track.getBoundingClientRect();
    if (!rect.width) return cut;
    var ratio = (event.clientX - rect.left) / rect.width;
    return Math.max(0, Math.min(ITEMS.length, Math.round(ratio * ITEMS.length)));
  }

  if (track) {
    track.addEventListener("pointerdown", function (event) {
      drag = true;
      if (track.setPointerCapture) {
        try { track.setPointerCapture(event.pointerId); } catch (e) {}
      }
      setCut(fromPointer(event));
      event.preventDefault();
    });
    track.addEventListener("pointermove", function (event) {
      if (!drag) return;
      setCut(fromPointer(event));
      event.preventDefault();
    });
    track.addEventListener("pointerup", function () {
      drag = false;
    });
    track.addEventListener("pointercancel", function () {
      drag = false;
    });
  }

  if (handle) {
    handle.addEventListener("keydown", function (event) {
      var next = cut;
      if (event.key === "ArrowLeft") next = cut - 1;
      else if (event.key === "ArrowRight") next = cut + 1;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = ITEMS.length;
      else return;
      event.preventDefault();
      setCut(next);
    });
  }

  if (snap) {
    snap.addEventListener("click", function () {
      setCut(nearestLegal(cut));
    });
  }

  if (reset) {
    reset.addEventListener("click", function () {
      setCut(5);
    });
  }

  render();
})();
