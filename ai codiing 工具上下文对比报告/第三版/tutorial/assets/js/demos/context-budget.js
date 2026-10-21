(function () {
  "use strict";

  var root = document.getElementById("demo-context-budget");
  if (!root) return;

  var CAPACITY = 200000;
  var MIN_TOKENS = 4000;
  var STEP = 2000;
  var WARN_AT = 0.8;
  var DANGER_AT = 0.95;

  var bar = document.getElementById("cb-bar");
  var freeSeg = document.getElementById("cb-free-seg");
  var usedEl = document.getElementById("cb-used");
  var freeEl = document.getElementById("cb-free");
  var statusValue = document.getElementById("cb-status-value");
  var statusNote = document.getElementById("cb-status-note");
  var srEl = document.getElementById("cb-sr");
  var resetBtn = document.getElementById("cb-reset");
  if (!bar || !freeSeg || !usedEl || !freeEl) return;

  var segs = Array.prototype.slice.call(bar.querySelectorAll(".cb-seg[data-key]"));
  if (!segs.length) return;

  var tokens = {};
  var initial = {};
  var legends = {};

  segs.forEach(function (seg) {
    var key = seg.getAttribute("data-key");
    var value = parseInt(seg.getAttribute("data-tokens"), 10);
    if (!isFinite(value)) value = MIN_TOKENS;
    tokens[key] = value;
    initial[key] = value;
    legends[key] = {
      num: root.querySelector('[data-num="' + key + '"]'),
      pct: root.querySelector('[data-pct="' + key + '"]')
    };
  });

  var lastLevel = "";

  function totalUsed() {
    var sum = 0;
    segs.forEach(function (seg) {
      sum += tokens[seg.getAttribute("data-key")];
    });
    return sum;
  }

  function isDirty() {
    for (var i = 0; i < segs.length; i++) {
      var key = segs[i].getAttribute("data-key");
      if (tokens[key] !== initial[key]) return true;
    }
    return false;
  }

  function format(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function shortNum(n) {
    if (n >= 1000) {
      var k = Math.round(n / 100) / 10;
      return (k % 1 === 0 ? String(k) : k.toFixed(1)) + "k";
    }
    return String(n);
  }

  function pctText(value) {
    var p = Math.round(value * 10) / 10;
    return (p % 1 === 0 ? String(p) : p.toFixed(1)) + "%";
  }

  function levelOf(used) {
    var ratio = used / CAPACITY;
    if (ratio >= DANGER_AT) return "danger";
    if (ratio >= WARN_AT) return "warn";
    return "ok";
  }

  function render() {
    var used = totalUsed();
    var free = Math.max(0, CAPACITY - used);
    var usedRatio = used / CAPACITY;
    var freeRatio = free / CAPACITY;
    var level = levelOf(used);

    segs.forEach(function (seg) {
      var key = seg.getAttribute("data-key");
      var t = tokens[key];
      var ratio = t / CAPACITY;
      var label = seg.getAttribute("aria-label") || key;

      seg.style.width = ratio * 100 + "%";
      seg.classList.toggle("is-compact", ratio < 0.12);
      seg.classList.toggle("is-tiny", ratio < 0.045);
      seg.setAttribute("aria-valuenow", String(t));
      seg.setAttribute("aria-valuemax", String(t + free));
      seg.setAttribute("aria-valuetext", label + "，" + format(t) + " token，占 " + pctText(ratio * 100));

      var num = seg.querySelector(".cb-seg__num");
      if (num) num.textContent = shortNum(t);

      if (legends[key]) {
        if (legends[key].num) legends[key].num.textContent = format(t);
        if (legends[key].pct) legends[key].pct.textContent = pctText(ratio * 100);
      }
    });

    freeSeg.style.width = freeRatio * 100 + "%";
    freeSeg.classList.toggle("is-tiny", freeRatio < 0.09);
    var freeNum = freeSeg.querySelector(".cb-seg__num");
    if (freeNum) freeNum.textContent = shortNum(free);

    usedEl.textContent = format(used);
    freeEl.textContent = format(free);
    root.setAttribute("data-level", level);

    if (level === "danger") {
      statusValue.textContent = "危险";
      statusNote.textContent =
        free === 0 ? "已满，再塞只能挤占预留" : "只剩 " + pctText(freeRatio * 100) + "，预留快守不住了";
    } else if (level === "warn") {
      statusValue.textContent = "警戒";
      statusNote.textContent = "只剩 " + pctText(freeRatio * 100) + "，该考虑压缩了";
    } else {
      statusValue.textContent = "宽裕";
      statusNote.textContent = "还剩 " + pctText(freeRatio * 100) + "，空间够用";
    }

    if (lastLevel && level !== lastLevel && srEl) {
      if (level === "danger") {
        srEl.textContent = "进入危险区。已占 " + pctText(usedRatio * 100) + "，剩余 " + format(free) + " token。";
      } else if (level === "warn") {
        srEl.textContent = "进入警戒区。已占 " + pctText(usedRatio * 100) + "，剩余 " + format(free) + " token。";
      } else {
        srEl.textContent = "回到宽裕区。剩余 " + format(free) + " token。";
      }
    }
    lastLevel = level;

    if (resetBtn) resetBtn.classList.toggle("is-dirty", isDirty());
  }

  function maxFor(key) {
    return tokens[key] + (CAPACITY - totalUsed());
  }

  function setTokens(key, value) {
    var max = Math.max(MIN_TOKENS, maxFor(key));
    var next = Math.max(MIN_TOKENS, Math.min(max, Math.round(value / STEP) * STEP));
    tokens[key] = next;
    render();
  }

  segs.forEach(function (seg) {
    var key = seg.getAttribute("data-key");

    seg.addEventListener("pointerdown", function (event) {
      if (event.button !== undefined && event.button !== 0) return;
      var rect = bar.getBoundingClientRect();
      if (!rect.width) return;

      seg.__drag = {
        id: event.pointerId,
        startX: event.clientX,
        startTokens: tokens[key],
        freeAtStart: CAPACITY - totalUsed(),
        width: rect.width
      };
      seg.classList.add("is-dragging");
      try {
        seg.setPointerCapture(event.pointerId);
      } catch (err) {}
      if (typeof seg.focus === "function") seg.focus();
      event.preventDefault();
    });

    seg.addEventListener("pointermove", function (event) {
      var drag = seg.__drag;
      if (!drag || drag.id !== event.pointerId) return;

      var delta = ((event.clientX - drag.startX) / drag.width) * CAPACITY;
      var max = drag.startTokens + drag.freeAtStart;
      var next = Math.round((drag.startTokens + delta) / STEP) * STEP;
      next = Math.max(MIN_TOKENS, Math.min(max, next));

      if (next !== tokens[key]) {
        tokens[key] = next;
        render();
      }
      event.preventDefault();
    });

    function endDrag(event) {
      var drag = seg.__drag;
      if (!drag || drag.id !== event.pointerId) return;
      seg.__drag = null;
      seg.classList.remove("is-dragging");
      try {
        seg.releasePointerCapture(event.pointerId);
      } catch (err) {}
    }

    seg.addEventListener("pointerup", endDrag);
    seg.addEventListener("pointercancel", endDrag);

    seg.addEventListener("keydown", function (event) {
      var step = event.shiftKey ? STEP * 5 : STEP;
      var next = tokens[key];

      if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
        next = tokens[key] - step;
      } else if (event.key === "ArrowRight" || event.key === "ArrowUp") {
        next = tokens[key] + step;
      } else if (event.key === "Home") {
        next = MIN_TOKENS;
      } else if (event.key === "End") {
        next = maxFor(key);
      } else {
        return;
      }

      event.preventDefault();
      setTokens(key, next);
    });
  });

  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      segs.forEach(function (seg) {
        var key = seg.getAttribute("data-key");
        seg.__drag = null;
        seg.classList.remove("is-dragging");
        tokens[key] = initial[key];
      });
      render();

      var used = totalUsed();
      if (srEl) {
        srEl.textContent =
          "已恢复初始分配：已占 " + format(used) + "，剩余 " + format(CAPACITY - used) + " token。";
      }
    });
  }

  render();
})();
