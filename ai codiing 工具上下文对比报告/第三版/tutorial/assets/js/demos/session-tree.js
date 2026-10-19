/* ============================================================
 * session-tree.js —— 会话树、分叉与回退演示
 * ------------------------------------------------------------
 * 教学示意，不是任何工具的真实实现：
 * 1. 日志只追加：回退只追加 marker，节点变灰但不删除。
 * 2. 可见历史 = 从根到 HEAD 的路径。
 * 3. 分叉可选生成一条分支摘要，替代被放弃的路径。
 * 4. 文件回退是单独的开关，开启后不可逆。
 * 依赖：无。纯 DOM + 内联 SVG 连线。
 * ============================================================ */
(function () {
  "use strict";

  var root = document.getElementById("demo-session-tree");
  if (!root) return;

  var INITIAL = [
    { id: "n0", parent: null, lane: 0, kind: "用户", text: "拆导出模块，别动 public API", tokens: 1200, file: 0 },
    { id: "n1", parent: "n0", lane: 0, kind: "助手", text: "读入口与调用方，确认包的边界", tokens: 2400, file: 0 },
    { id: "n2", parent: "n1", lane: 0, kind: "工具", text: "grep export → 37 处命中", tokens: 8600, file: 1 },
    { id: "n3", parent: "n2", lane: 0, kind: "用户", text: "改用方案 A：新建子包", tokens: 1000, file: 2 },
    { id: "n4", parent: "n3", lane: 0, kind: "助手", text: "搬迁 4 个文件，更新导入", tokens: 6200, file: 4 },
    { id: "n5", parent: "n4", lane: 0, kind: "工具", text: "run tests → 2 失败", tokens: 14800, file: 4 },
    { id: "n6", parent: "n5", lane: 0, kind: "用户", text: "修掉循环依赖再跑", tokens: 900, file: 4 },
    { id: "n7", parent: "n6", lane: 0, kind: "助手", text: "legacy 改 type-only import，测试通过", tokens: 5400, file: 6 },
    { id: "a1", parent: "n2", lane: 1, kind: "助手", text: "方案 A：抽 core 包", tokens: 3100, file: 2, branch: "A" },
    { id: "a2", parent: "a1", lane: 1, kind: "工具", text: "build 通过；包体 +12KB", tokens: 9700, file: 3, branch: "A" },
    { id: "b1", parent: "n3", lane: 2, kind: "助手", text: "方案 B：保留原包，只拆类型", tokens: 2800, file: 2, branch: "B" },
    { id: "b2", parent: "b1", lane: 2, kind: "工具", text: "测试通过；3 个调用方要改", tokens: 7900, file: 2, branch: "B" }
  ];

  var FORK_TEXT = [
    "新分支：先补一个复现测试",
    "新分支：改走 core.ts 的 re-export",
    "新分支：把 legacy 拆成两个文件"
  ];

  var nodes = [];
  var seq = 7;
  var forkCount = 0;
  var rewindCount = 0;
  var logLines = 22;
  var head = "n7";
  var selected = "n5";
  var currentFile = 6;
  var fileAction = null;
  var everOnPath = {};
  var lastStatus = "";

  var stree = root.querySelector("#stree");
  var wrap = root.querySelector(".stree-wrap");
  var visibleList = root.querySelector("#tree-visible");
  var visibleFoot = root.querySelector("#tree-visible-foot");
  var filesState = root.querySelector("#tree-files-state");
  var kpis = root.querySelector("#tree-kpis");
  var selectedOut = root.querySelector("#tree-selected");
  var statusOut = root.querySelector("#tree-status");
  var warning = root.querySelector("#tree-warning");
  var forkBtn = root.querySelector("#tree-fork");
  var rewindBtn = root.querySelector("#tree-rewind");
  var resetBtn = root.querySelector("#tree-reset");
  var filesCheck = root.querySelector("#tree-files");
  var summaryCheck = root.querySelector("#tree-summary");

  function clone(list) {
    return list.map(function (n) {
      var o = {};
      for (var k in n) {
        if (Object.prototype.hasOwnProperty.call(n, k)) o[k] = n[k];
      }
      return o;
    });
  }

  function fmt(value) {
    return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function tok(value) {
    if (value >= 1000) {
      var k = value / 1000;
      return (k >= 10 ? Math.round(k) : Math.round(k * 10) / 10) + "k";
    }
    return String(value);
  }

  function byId() {
    var map = {};
    nodes.forEach(function (n) { map[n.id] = n; });
    return map;
  }

  function pathOf(id, map) {
    var out = [];
    var cur = map[id];
    var guard = 0;
    while (cur && guard < 100) {
      out.unshift(cur);
      cur = cur.parent ? map[cur.parent] : null;
      guard += 1;
    }
    return out;
  }

  function addEver(list) {
    list.forEach(function (n) { everOnPath[n.id] = true; });
  }

  function laneLabel(node) {
    if (node.summary) return node.zone || "摘要分支";
    if (node.branch) return "分支 " + node.branch;
    if (node.zone) return node.zone;
    return "主干";
  }

  function nodeName(id) {
    return "#" + id;
  }

  function isBypassed(node) {
    return !!everOnPath[node.id] && node._onPath !== true;
  }

  function orderedNodes() {
    var children = {};
    nodes.forEach(function (n) {
      var key = n.parent || "__root";
      if (!children[key]) children[key] = [];
      children[key].push(n);
    });
    Object.keys(children).forEach(function (key) {
      children[key].sort(function (a, b) {
        var ab = a.lane > 0 ? 1 : 0;
        var bb = b.lane > 0 ? 1 : 0;
        if (ab !== bb) return bb - ab;
        return nodes.indexOf(a) - nodes.indexOf(b);
      });
    });
    var out = [];
    (function walk(key) {
      (children[key] || []).forEach(function (n) {
        out.push(n);
        walk(n.id);
      });
    })("__root");
    nodes.forEach(function (n) {
      if (out.indexOf(n) < 0) out.push(n);
    });
    return out;
  }

  function renderTree(map, pathSet) {
    stree.textContent = "";
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("aria-hidden", "true");
    stree.appendChild(svg);

    orderedNodes().forEach(function (node) {
      node._onPath = !!pathSet[node.id];
      node._bypassed = isBypassed(node);

      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "stree-node stree-node--lane-" + node.lane;
      if (node.lane === 1) btn.className += " stree-node--a";
      if (node.lane === 2) btn.className += " stree-node--b";
      if (node.summary) btn.className += " stree-node--sum";
      if (node.id === head) btn.className += " stree-node--head";
      if (node.id === selected) btn.className += " is-selected";
      if (node._bypassed) btn.className += " is-bypassed";
      else if (!node._onPath) btn.className += " is-offpath";
      btn.setAttribute("data-id", node.id);

      var headRow = document.createElement("span");
      headRow.className = "stree-node__head";
      var idText = document.createElement("b");
      idText.textContent = "#" + node.id;
      headRow.appendChild(idText);
      var kind = document.createElement("span");
      kind.className = "stree-node__kind";
      kind.textContent = node.kind;
      headRow.appendChild(kind);
      var lane = document.createElement("span");
      lane.className = "stree-node__lane";
      lane.textContent = laneLabel(node);
      headRow.appendChild(lane);
      btn.appendChild(headRow);

      var text = document.createElement("span");
      text.className = "stree-node__text";
      text.textContent = node.text;
      btn.appendChild(text);

      var meta = document.createElement("span");
      meta.className = "stree-node__meta";
      meta.appendChild(document.createTextNode(tok(node.tokens) + " tok · 文件 v" + node.file));
      if (node.id === head) {
        var h = document.createElement("span");
        h.className = "stree-node__flag stree-node__flag--head";
        h.textContent = "HEAD";
        meta.appendChild(h);
      }
      if (node._bypassed) {
        var b = document.createElement("span");
        b.className = "stree-node__flag";
        b.textContent = "已绕过";
        meta.appendChild(b);
      }
      btn.appendChild(meta);

      btn.setAttribute("aria-label",
        "#" + node.id + " " + node.kind + "，" + node.text +
        "，" + tok(node.tokens) + " token" +
        (node._bypassed ? "，已绕过，仍在日志里" : ""));

      btn.addEventListener("click", function () {
        selected = node.id;
        render();
        say("已选中 " + nodeName(node.id) + " · " + node.kind + "。可以回退到这里，或从这里分叉。");
      });

      stree.appendChild(btn);
    });
  }

  function drawEdges(map) {
    var svg = stree.querySelector("svg");
    if (!svg) return;
    var w = stree.scrollWidth;
    var h = stree.scrollHeight;
    svg.setAttribute("width", w);
    svg.setAttribute("height", h);
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    nodes.forEach(function (node) {
      if (!node.parent || !map[node.parent]) return;
      var pEl = stree.querySelector('[data-id="' + node.parent + '"]');
      var cEl = stree.querySelector('[data-id="' + node.id + '"]');
      if (!pEl || !cEl) return;
      var px = pEl.offsetLeft + 12;
      var py = pEl.offsetTop + pEl.offsetHeight;
      var cx = cEl.offsetLeft + 12;
      var cy = cEl.offsetTop;
      var mid = py + Math.max(5, Math.min(14, (cy - py) / 2));

      var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      var cls = "stree-edge";
      if (node.summary) cls += " stree-edge--sum";
      else if (node.lane === 1) cls += " stree-edge--a";
      else if (node.lane === 2) cls += " stree-edge--b";
      if (node._bypassed || map[node.parent]._bypassed) cls += " stree-edge--gone";
      path.setAttribute("class", cls);
      path.setAttribute("d", "M" + px + " " + py + " V" + mid + " H" + cx + " V" + cy);
      svg.appendChild(path);
    });
  }

  function renderVisible(map) {
    var path = pathOf(head, map);
    visibleList.textContent = "";
    var total = 0;
    path.forEach(function (node) {
      total += node.tokens;
      var li = document.createElement("li");
      var id = document.createElement("b");
      id.textContent = "#" + node.id;
      var text = document.createElement("span");
      text.textContent = node.summary ? "分支摘要：被放弃的路径" : node.text;
      text.title = text.textContent;
      var tokens = document.createElement("em");
      tokens.textContent = tok(node.tokens);
      li.appendChild(id);
      li.appendChild(text);
      li.appendChild(tokens);
      visibleList.appendChild(li);
    });
    visibleFoot.textContent =
      "共 " + path.length + " 条 · " + tok(total) + " token · HEAD " + nodeName(head) +
      (path.some(function (n) { return n.summary; }) ? " · 含 1 条摘要" : "");
    return { path: path, total: total };
  }

  function renderKpis(map, visible) {
    kpis.textContent = "";
    var items = [
      { k: "HEAD", v: "#" + head, s: laneLabel(map[head]) },
      { k: "可见历史", v: visible.path.length + " 条", s: tok(visible.total) + " token" },
      { k: "日志行数", v: logLines + " 行", s: "→ 只增不减" },
      { k: "删除", v: "0 行", s: "灰节点仍在" }
    ];
    items.forEach(function (item) {
      var box = document.createElement("div");
      box.className = "stree-kpi";
      var k = document.createElement("span");
      k.className = "stree-kpi__k";
      k.textContent = item.k;
      var v = document.createElement("span");
      v.className = "stree-kpi__v";
      v.textContent = item.v;
      var s = document.createElement("span");
      s.className = "stree-kpi__s";
      s.textContent = item.s;
      box.appendChild(k);
      box.appendChild(v);
      box.appendChild(s);
      kpis.appendChild(box);
    });
  }

  function renderFiles() {
    filesState.textContent = "";
    var title = document.createElement("p");
    title.className = "stree-files__title";
    title.textContent = "工作区快照";
    filesState.appendChild(title);

    var lines = [
      "src/export/index.ts  v" + currentFile,
      "src/export/legacy.ts  v" + currentFile,
      "src/export/core.ts  " + (currentFile >= 4 ? "存在" : "不存在")
    ];
    lines.forEach(function (text) {
      var p = document.createElement("p");
      p.textContent = text;
      filesState.appendChild(p);
    });

    if (fileAction) {
      var p = document.createElement("p");
      if (fileAction.onlyTalk) {
        p.textContent = "上次回退：只动对话，文件仍是 v" + fileAction.version;
      } else {
        p.textContent = "上次回退：文件 v" + fileAction.from + " → v" + fileAction.to;
      }
      filesState.appendChild(p);
    }
  }

  function renderSelected(map) {
    var node = map[selected];
    if (!node) return;
    selectedOut.textContent =
      "已选中 #" + node.id + " · " + node.kind + " · " + laneLabel(node) +
      (node._bypassed ? " · 已绕过" : "");
  }

  function render() {
    var map = byId();
    var path = pathOf(head, map);
    var pathSet = {};
    path.forEach(function (n) { pathSet[n.id] = true; });

    renderTree(map, pathSet);
    renderKpis(map, renderVisible(map));
    renderSelected(map);
    renderFiles();
    window.requestAnimationFrame(function () { drawEdges(map); });
  }

  function say(text) {
    lastStatus = text;
    statusOut.textContent = text;
  }

  function scrollHead() {
    var map = byId();
    var node = map[head];
    if (!node) return;
    var el = stree.querySelector('[data-id="' + head + '"]');
    if (el && wrap) wrap.scrollTop = Math.max(0, el.offsetTop - 60);
  }

  function fork() {
    var map = byId();
    var sel = map[selected];
    if (!sel) return;

    var oldPath = pathOf(head, map);
    var anc = {};
    pathOf(sel.id, map).forEach(function (n) { anc[n.id] = true; });
    var abandoned = oldPath.filter(function (n) { return !anc[n.id]; });

    var lane = Math.min(sel.lane + 1, 2);
    var zone = "新分支 " + (forkCount + 1);
    var added = 0;
    var summaryMade = false;
    var firstParent = sel.id;

    forkCount += 1;

    if (summaryCheck.checked && abandoned.length) {
      seq += 1;
      var first = abandoned[0].id;
      var last = abandoned[abandoned.length - 1].id;
      var toolCount = abandoned.filter(function (n) { return n.kind === "工具"; }).length;
      nodes.push({
        id: "s" + seq,
        parent: sel.id,
        lane: lane,
        kind: "摘要",
        summary: true,
        text: "分支摘要：放弃 #" + first + "–#" + last + " 的 " + abandoned.length + " 步" +
          (toolCount ? "（含 " + toolCount + " 次工具调用）" : ""),
        tokens: 700,
        file: sel.file,
        zone: zone
      });
      firstParent = "s" + seq;
      added += 1;
      summaryMade = true;
    }

    seq += 1;
    nodes.push({
      id: "n" + seq,
      parent: firstParent,
      lane: lane,
      kind: "助手",
      text: FORK_TEXT[forkCount % FORK_TEXT.length],
      tokens: 2600,
      file: sel.file,
      zone: zone
    });
    var f1 = "n" + seq;
    added += 1;

    seq += 1;
    nodes.push({
      id: "n" + seq,
      parent: f1,
      lane: lane,
      kind: "工具",
      text: "局部验证 → 通过（3 个测试）",
      tokens: 6400,
      file: sel.file,
      zone: zone
    });
    var f2 = "n" + seq;
    added += 1;

    addEver(oldPath);
    head = f2;
    addEver(pathOf(head, byId()));
    logLines += added + 1;

    fileAction = null;
    if (filesCheck.checked) {
      warning.hidden = false;
      warning.textContent = "文件回退已开启：回退会同时覆盖工作区，且不可逆。日志只能恢复对话，不能恢复被覆盖的文件。";
    } else {
      warning.hidden = true;
    }

    render();
    scrollHead();

    if (abandoned.length === 0) {
      say("从 #" + sel.id + " 分叉：新增 2 个节点。这个点就在当前路径末端，没有被放弃的步骤，因此不生成摘要。日志 +3 行，删除 0 行。");
    } else if (summaryMade) {
      say("从 #" + sel.id + " 分叉：新增 1 条摘要 + 2 个节点；被放弃的 " + abandoned.length + " 步压成 700 token。HEAD 移到 #" + f2 + "；旧路径变灰，日志 +4 行，删除 0 行。");
    } else {
      say("从 #" + sel.id + " 分叉：新增 2 个节点，未生成摘要；旧路径 " + abandoned.length + " 步不再可见（变灰），日志 +3 行，删除 0 行。");
    }
  }

  function rewind() {
    var map = byId();
    var target = map[selected];
    if (!target) return;

    if (selected === head) {
      say("#" + selected + " 就是当前 HEAD。回退不会改变可见历史，也不会删除任何行；换一个节点再试。");
      return;
    }

    var oldPath = pathOf(head, map);
    var wasOnPath = oldPath.some(function (n) { return n.id === selected; });
    var targetPath = pathOf(selected, map);
    var keep = {};
    targetPath.forEach(function (n) { keep[n.id] = true; });
    var leaving = oldPath.filter(function (n) { return !keep[n.id]; });

    addEver(oldPath);
    head = selected;
    addEver(targetPath);
    rewindCount += 1;
    logLines += 1;

    var fileText = "";
    if (filesCheck.checked) {
      var from = currentFile;
      currentFile = target.file;
      fileAction = { from: from, to: currentFile };
      warning.hidden = false;
      warning.textContent = "文件回退不可逆：工作区从 v" + from + " 覆盖到 v" + currentFile +
        (currentFile < 4 ? "，src/export/core.ts 被删除" : "") +
        "。日志无法恢复这些改动；演示中只改变演示状态。";
      fileText = "文件同时恢复到 v" + currentFile + "（不可逆）。";
    } else {
      fileAction = { onlyTalk: true, version: currentFile };
      warning.hidden = true;
      fileText = "文件保持 v" + currentFile + "，未回退；模型所见与磁盘可能不一致。";
    }

    render();
    scrollHead();

    say((wasOnPath ? "回退到 #" : "切换到 #") + selected + "：" +
      (leaving.length ? leaving.length + " 个节点不再进入模型可见历史（变灰）" : "可见历史不变") +
      "；日志追加 1 条 rewind 标记，删除 0 行。" + fileText);
  }

  function reset() {
    nodes = clone(INITIAL);
    seq = 7;
    forkCount = 0;
    rewindCount = 0;
    logLines = 22;
    head = "n7";
    selected = "n5";
    currentFile = 6;
    fileAction = null;
    everOnPath = {};
    addEver(pathOf(head, byId()));
    filesCheck.checked = false;
    summaryCheck.checked = true;
    warning.hidden = true;
    render();
    say("已重置：选中 #5。点“回退到这里”看可见历史如何缩短；点“从这里分叉”看新分支如何长出。");
  }

  forkBtn.addEventListener("click", fork);
  rewindBtn.addEventListener("click", rewind);
  resetBtn.addEventListener("click", reset);

  filesCheck.addEventListener("change", function () {
    if (filesCheck.checked) {
      warning.hidden = false;
      warning.textContent = "文件回退已开启：回退会同时覆盖工作区，且不可逆。日志只能恢复对话，不能恢复被覆盖的文件。";
      say("“同时回退文件”已开启。下一次回退会覆盖工作区；这一步不可逆。");
    } else {
      warning.hidden = true;
      say("“同时回退文件”已关闭。回退只改模型可见历史，工作区保持不变。");
    }
  });

  summaryCheck.addEventListener("change", function () {
    if (summaryCheck.checked) {
      say("分叉时将生成摘要：被放弃的路径会压成一条约 700 token 的分支摘要，挂在新分支起点。");
    } else {
      say("分叉时直接切：不生成摘要，旧路径只变灰，不进入新分支的可见历史。");
    }
  });

  var resizeTimer = 0;
  window.addEventListener("resize", function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () { drawEdges(byId()); }, 120);
  });

  reset();
})();
