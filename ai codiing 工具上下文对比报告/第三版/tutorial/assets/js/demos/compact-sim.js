/* ============================================================
 * compact-sim.js —— 压缩阈值、保留量与切点模拟器
 * ------------------------------------------------------------
 * 教学模型（不是任何工具的真实算法）：
 * 1. 窗口固定 200k；可用输入 = 窗口 − 输出预留。
 * 2. 压缩在「刚越过触发线」的那一刻发生，因此只有触发点之前
 *    的消息参与本次压缩。
 * 3. 从最新往回保留整条消息，直到再加一条就超过保留量。
 * 4. 切点不能落在工具调用与它的结果之间；违反时前移到调用。
 * 5. 切点之前的真实用户消息进摘要，其余（助手/调用/结果）丢弃。
 * 依赖：无。纯 DOM。
 * ============================================================ */
(function () {
  "use strict";

  var root = document.getElementById("demo-compact-sim");
  if (!root) return;

  var WINDOW = 200000;

  /* 一条 14 条的示意会话；tokens 为示意值，不是实测 */
  var MESSAGES = [
    { role: "user", text: "把导出模块拆成独立包，先别动 public API。", tokens: 8000 },
    { role: "assistant", text: "先看依赖和调用方，再决定包边界。", tokens: 12000 },
    { role: "call", text: "read package.json", tokens: 3000, pair: "A" },
    { role: "result", text: "package.json 与 lockfile 全文", tokens: 22000, pair: "A" },
    { role: "assistant", text: "再看谁 import 了它。", tokens: 14000 },
    { role: "call", text: "grep \"export\" src/", tokens: 3000, pair: "B" },
    { role: "result", text: "搜索结果：37 个文件命中", tokens: 24000, pair: "B" },
    { role: "user", text: "记住：public API 不能改。", tokens: 9000 },
    { role: "assistant", text: "重构方案与第一版 diff。", tokens: 20000 },
    { role: "call", text: "run tests", tokens: 3000, pair: "C" },
    { role: "result", text: "测试日志：2 个失败", tokens: 25000, pair: "C" },
    { role: "user", text: "继续，把剩下的调用方也改掉。", tokens: 10000 },
    { role: "assistant", text: "改了 3 个调用方，补充迁移说明。", tokens: 22000 },
    { role: "user", text: "最后再跑一次全量测试。", tokens: 12000 }
  ];

  var ROLE_LABEL = {
    user: "用户",
    assistant: "助手",
    call: "工具调用",
    result: "工具结果"
  };

  var threshold = root.querySelector("#cmp-threshold");
  var keep = root.querySelector("#cmp-keep");
  var reserve = root.querySelector("#cmp-reserve");
  var thresholdOut = root.querySelector("#cmp-threshold-out");
  var keepOut = root.querySelector("#cmp-keep-out");
  var reserveOut = root.querySelector("#cmp-reserve-out");
  var list = root.querySelector("#cmp-list");
  var status = root.querySelector("#cmp-status");
  var warning = root.querySelector("#cmp-warning");
  var bar = root.querySelector("#cmp-bar");
  var marker = root.querySelector("#cmp-marker");
  var kpis = root.querySelector("#cmp-kpis");
  var reset = root.querySelector("#cmp-reset");

  function fmt(value) {
    var k = value / 1000;
    return (k >= 100 ? Math.round(k) : Math.round(k * 10) / 10) + "k";
  }

  function pct(value) {
    return (value / WINDOW) * 100;
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  /* 找到压缩发生时的最后一条消息：累计 token 首次达到触发线 */
  function findEnd(trigger) {
    var sum = 0;
    for (var i = 0; i < MESSAGES.length; i++) {
      sum += MESSAGES[i].tokens;
      if (sum >= trigger) return { end: i, used: sum };
    }
    return { end: MESSAGES.length - 1, used: sum };
  }

  /* 从最新往回保留整条消息；至少保留最后一条 */
  function findCut(end, keepTokens) {
    var suffix = 0;
    var cut = end;
    for (var i = end; i >= 0; i--) {
      var tokens = MESSAGES[i].tokens;
      if (suffix > 0 && suffix + tokens > keepTokens) {
        cut = i + 1;
        break;
      }
      suffix += tokens;
      cut = i;
    }
    return cut;
  }

  /* 若切点把 call 与 result 分开，前移到 call（整对保留） */
  function repairCut(cut) {
    if (
      cut > 0 &&
      cut < MESSAGES.length &&
      MESSAGES[cut].role === "result" &&
      MESSAGES[cut - 1].role === "call"
    ) {
      return { cut: cut - 1, brokenAt: cut, callAt: cut - 1 };
    }
    return { cut: cut, brokenAt: -1, callAt: -1 };
  }

  function render() {
    var t = Number(threshold.value);
    var keepTokens = Number(keep.value) * 1000;
    var reserveTokens = Number(reserve.value) * 1000;

    thresholdOut.textContent = t + "%";
    keepOut.textContent = keep.value + "k";
    reserveOut.textContent = reserve.value + "k";

    var usable = WINDOW - reserveTokens;
    var trigger = (usable * t) / 100;
    var found = findEnd(trigger);
    var end = found.end;
    var used = found.used;

    var rawCut = findCut(end, keepTokens);
    var repaired = repairCut(rawCut);
    var cut = repaired.cut;
    var retained = 0;
    var summarized = 0;
    var dropped = 0;
    var summarizedCount = 0;

    for (var i = 0; i <= end; i++) {
      if (i < cut) {
        if (MESSAGES[i].role === "user") {
          summarized += MESSAGES[i].tokens;
          summarizedCount++;
        } else {
          dropped += MESSAGES[i].tokens;
        }
      } else {
        retained += MESSAGES[i].tokens;
      }
    }

    /* 条形图：四段 + 触发线 */
    bar.textContent = "";
    var parts = [
      { cls: "cmp-bar__sum", value: summarized, label: "摘要" },
      { cls: "cmp-bar__drop", value: dropped, label: "丢弃" },
      { cls: "cmp-bar__keep", value: retained, label: "保留" },
      { cls: "cmp-bar__future", value: WINDOW - used, label: "未用" }
    ];
    parts.forEach(function (part) {
      if (part.value <= 0) return;
      var seg = el("span", part.cls);
      var w = pct(part.value);
      seg.style.width = w + "%";
      if (w >= 9) seg.textContent = part.label;
      seg.title = part.label + " " + fmt(part.value) + " token";
      bar.appendChild(seg);
    });
    marker.style.left = pct(trigger) + "%";
    marker.title = "触发线 " + fmt(trigger);

    /* KPI */
    kpis.textContent = "";
    [
      ["当前占用", fmt(used), "窗口 200k · " + Math.round(pct(used)) + "%"],
      ["触发线", fmt(trigger), t + "% × " + fmt(usable)],
      ["切点", "第 " + (cut + 1) + " 条", cut > end ? "无保留段" : "之前 · 保留 " + fmt(retained)],
      ["摘要候选", summarizedCount + " 条", "用户消息 · " + fmt(summarized)]
    ].forEach(function (item) {
      var box = el("div", "cmp-kpi");
      box.appendChild(el("span", "cmp-kpi__k", item[0]));
      box.appendChild(el("strong", "cmp-kpi__v", item[1]));
      box.appendChild(el("span", "cmp-kpi__s", item[2]));
      kpis.appendChild(box);
    });

    /* 消息列表 */
    list.textContent = "";
    MESSAGES.forEach(function (msg, index) {
      var zone;
      if (index > end) zone = "future";
      else if (index >= cut) zone = "kept";
      else if (msg.role === "user") zone = "summarized";
      else zone = "dropped";

      var row = el("div", "cmp-row cmp-row--" + zone);
      row.title = msg.text + "（" + fmt(msg.tokens) + "）";
      row.appendChild(el("span", "cmp-idx", index < 9 ? "0" + (index + 1) : String(index + 1)));

      var role = el("span", "cmp-role", ROLE_LABEL[msg.role]);
      if (msg.role === "call" || msg.role === "result") {
        role.appendChild(el("span", "cmp-pair", msg.pair));
      }
      row.appendChild(role);
      row.appendChild(el("span", "cmp-text", msg.text));
      row.appendChild(el("span", "cmp-tok", fmt(msg.tokens)));

      var zoneText = {
        summarized: "进摘要",
        dropped: "丢弃",
        kept: "保留",
        future: "尚未发生"
      }[zone];
      row.appendChild(el("span", "cmp-zone", zoneText));
      list.appendChild(row);
    });

    /* 状态与提示 */
    status.textContent =
      "压缩发生在第 " + (end + 1) + " 条之后；" +
      (cut > end
        ? "没有保留段，全部历史都要进摘要。"
        : "切点在第 " + (cut + 1) + " 条之前。摘要 " + summarizedCount +
          " 条用户消息（" + fmt(summarized) + "），保留 " + fmt(retained) +
          "，丢弃 " + fmt(dropped) + "。");

    if (repaired.brokenAt >= 0) {
      warning.hidden = false;
      warning.textContent =
        "原始切点会落在第 " + (repaired.callAt + 1) + " 条工具调用与第 " +
        (repaired.brokenAt + 1) + " 条结果之间：调用进了摘要、结果却留在保留段。" +
        "已自动前移到第 " + (cut + 1) + " 条之前，把这一对整对保留。";
    } else if (cut === end + 1) {
      warning.hidden = false;
      warning.textContent = "保留量为 0，全部历史都要进摘要；真实工具通常会拒绝执行这种没有收益的压缩。";
    } else if (cut <= end && retained > keepTokens) {
      warning.hidden = false;
      warning.textContent =
        "最后一条被保留的消息本身就有 " + fmt(MESSAGES[cut].tokens) +
        "，超过保留量 " + fmt(keepTokens) + "；切点无法再往后移，只能整条保留或整条丢弃。";
    } else {
      warning.hidden = true;
      warning.textContent = "";
    }
  }

  [threshold, keep, reserve].forEach(function (input) {
    input.addEventListener("input", render);
  });

  if (reset) {
    reset.addEventListener("click", function () {
      threshold.value = "80";
      keep.value = "20";
      reserve.value = "16";
      render();
    });
  }

  render();
})();
