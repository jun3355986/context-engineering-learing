/* ============================================================
 * compaction-drift.js —— 多次压缩的信息丢失与摘要累积
 * ------------------------------------------------------------
 * 教学模型，不是任何工具的真实摘要算法。
 *
 * 1. 原始会话固定为 12 条事实，其中 3 条是硬约束。
 * 2. 每条事实有一张示意衰减表：第几轮开始变形、第几轮丢失。
 *    硬约束只判“保留 / 丢失”，不判变形。
 * 3. 摘要模板决定衰减表与段落；精简更容易丢，详细更容易留。
 * 4. 重附文件只恢复文件与状态类事实，不恢复对话里的硬约束。
 * 5. 摘要长度为当前轮渲染文本的字符数，不是 token 实测。
 * 依赖：无。纯 DOM。
 * ============================================================ */
(function () {
  "use strict";

  var root = document.getElementById("demo-compaction-drift");
  if (!root) return;

  /* 12 条事实；drift 是变形后的写法 */
  var FACTS = [
    { id: 1, kind: "goal", hard: false, text: "把导出模块拆成独立包", drift: "拆分导出模块" },
    { id: 2, kind: "constraint", hard: true, text: "不要改 public API", drift: "尽量保持 public API 兼容" },
    { id: 3, kind: "constraint", hard: true, text: "测试命令是 pnpm test:unit", drift: "使用项目测试命令" },
    { id: 4, kind: "constraint", hard: true, text: "保留 export 的命名", drift: "注意导出命名" },
    { id: 5, kind: "file", hard: false, text: "已读 src/index.ts、src/export.ts", drift: "读过导出相关文件" },
    { id: 6, kind: "decision", hard: false, text: "新包名 @acme/export-kit", drift: "新建一个导出包" },
    { id: 7, kind: "decision", hard: false, text: "先改 3 个调用方", drift: "改调用方" },
    { id: 8, kind: "state", hard: false, text: "2 个测试失败，失败在 snapshot", drift: "测试有失败" },
    { id: 9, kind: "file", hard: false, text: "已创建 packages/export-kit/package.json", drift: "新包已初始化" },
    { id: 10, kind: "pref", hard: false, text: "提交信息用 conventional commits", drift: "提交信息保持规范" },
    { id: 11, kind: "todo", hard: false, text: "更新 README 迁移说明", drift: "补充迁移说明" },
    { id: 12, kind: "risk", hard: false, text: "循环依赖 utils → export", drift: "存在循环依赖风险" }
  ];

  /* 示意衰减表。
   * hard[id] = 第几轮丢失；0 表示 6 轮内不丢。
   * normal[id] = [第几轮开始变形, 第几轮丢失]。
   * 这张表是教学模型，不是任何工具的实测数据。 */
  var PLAN = {
    slim: {
      hard: { 2: 4, 3: 4, 4: 3 },
      normal: {
        1: [2, 3], 5: [2, 3], 6: [2, 4], 7: [2, 3],
        8: [1, 2], 9: [2, 3], 10: [1, 1], 11: [1, 2], 12: [1, 2]
      }
    },
    standard: {
      hard: { 2: 6, 3: 6, 4: 4 },
      normal: {
        1: [5, 6], 5: [4, 6], 6: [5, 6], 7: [4, 6],
        8: [3, 5], 9: [3, 5], 10: [1, 1], 11: [3, 5], 12: [3, 5]
      }
    },
    detail: {
      hard: { 2: 0, 3: 6, 4: 5 },
      normal: {
        1: [7, 8], 5: [6, 8], 6: [7, 8], 7: [6, 8],
        8: [3, 5], 9: [5, 7], 10: [2, 4], 11: [3, 5], 12: [3, 5]
      }
    }
  };

  var SECTION = {
    goal: "progress",
    constraint: "constraint",
    file: "files",
    decision: "progress",
    state: "state",
    pref: "pref",
    todo: "todo",
    risk: "todo"
  };

  var SECTION_LABEL = {
    constraint: "约束（逐字）",
    progress: "进度与决定",
    files: "文件",
    state: "状态",
    todo: "待办与风险",
    pref: "偏好"
  };

  var SECTION_ORDER = ["constraint", "progress", "files", "state", "todo", "pref"];

  var TEMPLATES = {
    slim: {
      key: "slim",
      label: "精简",
      keep: 0.64,
      band: 0.14,
      intro: "只写结论与硬约束，其余不展开。",
      sections: ["constraint", "progress"]
    },
    standard: {
      key: "standard",
      label: "标准",
      keep: 0.48,
      band: 0.16,
      intro: "写结论、约束、决定、文件与待办。",
      sections: ["constraint", "progress", "files", "state", "todo"]
    },
    detail: {
      key: "detail",
      label: "详细",
      keep: 0.40,
      band: 0.14,
      intro: "写结论、约束、决定、文件、状态、待办、风险与验证。",
      sections: ["constraint", "progress", "files", "state", "todo", "pref"]
    }
  };

  var KIND_LABEL = {
    goal: "目标",
    constraint: "约束",
    file: "文件",
    decision: "决定",
    state: "状态",
    pref: "偏好",
    todo: "待办",
    risk: "风险"
  };

  var roundsInput = root.querySelector("#cd-rounds");
  var roundsOut = root.querySelector("#cd-rounds-out");
  var templateSelect = root.querySelector("#cd-template");
  var reattachInput = root.querySelector("#cd-reattach");
  var resetBtn = root.querySelector("#cd-reset");
  var kpis = root.querySelector("#cd-kpis");
  var factsBox = root.querySelector("#cd-facts");
  var stream = root.querySelector("#cd-stream");
  var statusLine = root.querySelector("#cd-status");

  if (!roundsInput || !templateSelect || !reattachInput || !kpis || !factsBox || !stream) return;

  var lastRounds = 0;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  /* 模板实际会写哪些段落；重附文件时补上文件与状态段。 */
  function effectiveSections(template, reattach) {
    var sections = template.sections.slice();
    if (reattach) {
      ["files", "state"].forEach(function (section) {
        if (sections.indexOf(section) < 0) sections.push(section);
      });
    }
    return sections;
  }

  /* 计算每一轮的状态。返回 history 与 final。 */
  function compute(rounds, template, reattach) {
    var plan = PLAN[template.key];
    var sections = effectiveSections(template, reattach);
    var states = FACTS.map(function () {
      return {
        status: "keep",
        lostRound: 0,
        changedRound: 0,
        recovered: false
      };
    });
    var history = [];

    for (var r = 1; r <= rounds; r++) {
      var lostNow = [];

      FACTS.forEach(function (fact, index) {
        var state = states[index];
        var section = SECTION[fact.kind];
        var inTemplate = sections.indexOf(section) >= 0;

        /* 模板不写这一段，也不重附：本轮起丢失 */
        if (!inTemplate) {
          if (state.status !== "lost") {
            state.status = "lost";
            state.lostRound = r;
            state.recovered = false;
            lostNow.push(fact.id);
          }
          return;
        }

        /* 重附文件：文件与状态类事实按磁盘原文恢复 */
        if (reattach && (fact.kind === "file" || fact.kind === "state")) {
          if (state.status === "lost") {
            state.recovered = true;
            state.changedRound = r;
            state.lostRound = 0;
          }
          state.status = "keep";
          return;
        }

        if (fact.hard) {
          var hardLost = plan.hard[fact.id] || 0;
          if (hardLost && r >= hardLost) {
            if (state.status !== "lost") {
              state.status = "lost";
              state.lostRound = r;
              lostNow.push(fact.id);
            }
          } else {
            state.status = "keep";
          }
          return;
        }

        var normal = plan.normal[fact.id] || [7, 8];
        if (r >= normal[1]) {
          if (state.status !== "lost") {
            state.status = "lost";
            state.lostRound = r;
            lostNow.push(fact.id);
          }
        } else if (r >= normal[0]) {
          if (state.status === "keep") {
            state.changedRound = r;
          }
          state.status = "drift";
        } else {
          state.status = "keep";
        }
      });

      history.push({
        round: r,
        states: states.map(function (state) {
          return {
            status: state.status,
            lostRound: state.lostRound,
            changedRound: state.changedRound,
            recovered: state.recovered
          };
        }),
        lostNow: lostNow
      });
    }

    return { history: history, final: states };
  }

  /* 生成一轮摘要的文本行；同时返回字符数。 */
  function buildSummary(record, template, reattach) {
    var sections = effectiveSections(template, reattach);
    var lines = [];
    var r = record.round;

    lines.push({
      type: "meta",
      text: r === 1
        ? "输入：原始会话 12 条事实。模板：" + template.label + "。"
        : "承接第 " + (r - 1) + " 次摘要；本轮再压缩一次。"
    });
    lines.push({ type: "meta", text: "摘要要求：" + template.intro });

    SECTION_ORDER.forEach(function (section) {
      if (sections.indexOf(section) < 0) return;

      var rows = FACTS.filter(function (fact, index) {
        return SECTION[fact.kind] === section && record.states[index].status !== "lost";
      });

      if (!rows.length) {
        if (section === "constraint") {
          lines.push({ type: "drop", text: "（约束段为空：三条硬约束均已丢失）" });
        }
        return;
      }

      lines.push({ type: "section", text: SECTION_LABEL[section] });
      rows.forEach(function (fact) {
        var index = FACTS.indexOf(fact);
        var status = record.states[index].status;
        lines.push({
          type: status === "keep" ? "keep" : "drift",
          text: (status === "keep" ? fact.text : fact.drift) + (fact.hard ? "（硬约束）" : "")
        });
      });
    });

    if (reattach) {
      lines.push({ type: "section", text: "重附文件" });
      lines.push({ type: "meta", text: "src/index.ts · src/export.ts · packages/export-kit/package.json" });
      lines.push({ type: "meta", text: "文件与状态类事实按磁盘原文恢复；对话里的约束不在文件里。" });
    }

    if (record.lostNow.length) {
      var lostText = record.lostNow.map(function (id) {
        var fact = FACTS.filter(function (item) { return item.id === id; })[0];
        return fact.text;
      }).join("；");
      lines.push({ type: "drop", text: "本轮起不再出现：" + lostText });
    } else {
      lines.push({ type: "meta", text: "本轮无新增丢失。" });
    }

    var length = lines.reduce(function (sum, line) {
      return sum + line.text.length;
    }, 0);

    return { lines: lines, length: length };
  }

  function renderFacts(finalStates, reattach) {
    factsBox.textContent = "";

    FACTS.forEach(function (fact, index) {
      var state = finalStates[index];
      var row = el("div", "cd-fact cd-fact--" + state.status);
      row.setAttribute("role", "listitem");

      var no = el("span", "cd-fact__no", (fact.id < 10 ? "0" : "") + fact.id);
      var body = el("div", "cd-fact__body");
      var top = el("div", "cd-fact__top");
      top.appendChild(el("span", "cd-fact__kind", KIND_LABEL[fact.kind]));
      if (fact.hard) top.appendChild(el("span", "cd-fact__hard", "硬约束"));
      body.appendChild(top);
      body.appendChild(el("span", "cd-fact__text", fact.text));

      var label;
      if (state.status === "keep") {
        label = reattach && (fact.kind === "file" || fact.kind === "state") ? "重附" : "保留";
      } else if (state.status === "drift") {
        label = state.changedRound > 1 ? "第 " + state.changedRound + " 次变形" : "变形";
      } else {
        label = "第 " + state.lostRound + " 次丢失";
      }

      var chip = el("span", "cd-chip cd-chip--" + state.status, label);
      row.appendChild(no);
      row.appendChild(body);
      row.appendChild(chip);
      factsBox.appendChild(row);
    });
  }

  function renderStream(history, template, reattach) {
    stream.textContent = "";

    history.forEach(function (record) {
      var summary = buildSummary(record, template, reattach);
      var article = el("article", "cd-round");
      var head = el("div", "cd-round__head");
      head.appendChild(el("span", "cd-round__no", "第 " + record.round + " 次压缩"));
      head.appendChild(el("span", "cd-round__len", summary.length + " 字"));
      article.appendChild(head);

      summary.lines.forEach(function (line) {
        if (line.type === "section") {
          article.appendChild(el("p", "cd-sec", line.text));
        } else {
          article.appendChild(el("p", "cd-line cd-line--" + line.type, line.text));
        }
      });

      stream.appendChild(article);
    });
  }

  function renderKpis(history, finalStates) {
    var hardTotal = FACTS.filter(function (fact) { return fact.hard; }).length;
    var hardKept = FACTS.filter(function (fact, index) {
      return fact.hard && finalStates[index].status === "keep";
    }).length;
    var kept = finalStates.filter(function (state) { return state.status === "keep"; }).length;
    var drift = finalStates.filter(function (state) { return state.status === "drift"; }).length;
    var lost = finalStates.filter(function (state) { return state.status === "lost"; }).length;

    var firstHard = null;
    FACTS.forEach(function (fact, index) {
      if (!fact.hard) return;
      var state = finalStates[index];
      if (state.status === "lost" && (!firstHard || state.lostRound < firstHard.round)) {
        firstHard = { round: state.lostRound, text: fact.text };
      }
    });

    var last = history[history.length - 1];
    var lastSummary = last ? buildSummary(last, TEMPLATES[templateSelect.value], reattachInput.checked) : { length: 0 };

    kpis.textContent = "";
    [
      {
        key: "硬约束保留",
        value: hardKept + " / " + hardTotal,
        sub: "逐字保留；变形不算"
      },
      {
        key: "事实完整",
        value: kept + " / " + FACTS.length,
        sub: "另 " + drift + " 条变形 · " + lost + " 条丢失"
      },
      {
        key: "摘要长度",
        value: lastSummary.length + " 字",
        sub: "第 " + (last ? last.round : 0) + " 次压缩后（示意）"
      },
      {
        key: "首条约束丢失",
        value: firstHard ? "第 " + firstHard.round + " 次" : "未丢失",
        sub: firstHard ? firstHard.text : "≤ " + roundsInput.value + " 次内仍保留"
      }
    ].forEach(function (item) {
      var box = el("div", "cd-kpi");
      box.setAttribute("role", "group");
      box.setAttribute("aria-label", item.key + "：" + item.value + "。" + item.sub);
      box.appendChild(el("span", "cd-kpi__k", item.key));
      box.appendChild(el("strong", "cd-kpi__v", item.value));
      box.appendChild(el("span", "cd-kpi__s", item.sub));
      kpis.appendChild(box);
    });
  }

  function renderStatus(finalStates) {
    var hardFacts = FACTS.filter(function (fact) { return fact.hard; });
    var hardKept = hardFacts.filter(function (fact) {
      return finalStates[FACTS.indexOf(fact)].status === "keep";
    }).length;
    var kept = finalStates.filter(function (state) { return state.status === "keep"; }).length;
    var drift = finalStates.filter(function (state) { return state.status === "drift"; }).length;
    var lost = finalStates.filter(function (state) { return state.status === "lost"; }).length;

    var firstHard = null;
    hardFacts.forEach(function (fact) {
      var state = finalStates[FACTS.indexOf(fact)];
      if (state.status === "lost" && (!firstHard || state.lostRound < firstHard.round)) {
        firstHard = { round: state.lostRound, text: fact.text };
      }
    });

    var text = "第 " + roundsInput.value + " 次压缩后：硬约束保留 " + hardKept + "/" + hardFacts.length +
      "；" + FACTS.length + " 条事实中 " + kept + " 条完整、" + drift + " 条变形、" + lost + " 条丢失。";
    if (firstHard) {
      text += "第一次丢失硬约束在第 " + firstHard.round + " 次（" + firstHard.text + "）。";
    } else {
      text += "硬约束在 " + roundsInput.value + " 次内没有丢失，但已有 " + lost + " 条事实丢失。";
    }
    statusLine.textContent = text;
  }

  function render() {
    var rounds = Number(roundsInput.value);
    var template = TEMPLATES[templateSelect.value] || TEMPLATES.standard;
    var reattach = reattachInput.checked;

    roundsOut.textContent = rounds + " 次";

    var result = compute(rounds, template, reattach);
    renderKpis(result.history, result.final);
    renderFacts(result.final, reattach);
    renderStream(result.history, template, reattach);
    renderStatus(result.final);

    if (rounds >= lastRounds) {
      stream.scrollTop = stream.scrollHeight;
    }
    lastRounds = rounds;
  }

  roundsInput.addEventListener("input", render);
  roundsInput.addEventListener("change", render);
  templateSelect.addEventListener("change", render);
  reattachInput.addEventListener("change", render);

  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      roundsInput.value = "4";
      templateSelect.value = "standard";
      reattachInput.checked = false;
      lastRounds = 0;
      render();
    });
  }

  render();
})();
