/* ============================================================
 * app.js —— 导航渲染、搜索、主题、弹窗、测验、复制
 * ------------------------------------------------------------
 * 01 号票创建；此后由主控统一维护。
 * 依赖：toc.js（先加载）
 * 约束：普通 script、无 ES module、无 fetch、无外部依赖；
 *       file:// 双击可运行；控制台不报错。
 * 对外接口：window.CTX.{openModal, closeModal, toast, prefix, toc}
 * ============================================================ */
(function (window, document) {
  "use strict";

  var KEY = {
    theme: "ctx-theme",
    nav: "ctx-nav-collapsed",
    navScroll: "ctx-nav-scroll",
    recent: "ctx-recent"
  };

  var TOC = window.TOC || { home: null, groups: [] };
  var currentChapter = "";
  var lastFocus = null;
  var toastTimer = null;
  var activeResult = -1;

  /* ---------- 小工具 ---------- */

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $$(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* 搜索结果摘要：截取命中位置前后文，命中词包 <mark> */
  function markSnippet(text, query) {
    var low = text.toLowerCase();
    var i = low.indexOf(String(query).toLowerCase());
    if (i < 0) return esc(text.slice(0, 110)) + (text.length > 110 ? "…" : "");
    var start = Math.max(0, i - 46);
    var end = Math.min(text.length, i + query.length + 74);
    return (
      (start > 0 ? "…" : "") +
      esc(text.slice(start, i)) +
      "<mark>" + esc(text.slice(i, i + query.length)) + "</mark>" +
      esc(text.slice(i + query.length, end)) +
      (end < text.length ? "…" : "")
    );
  }

  function read(key, fallback) {
    try {
      var raw = window.localStorage.getItem(key);
      return raw == null ? fallback : raw;
    } catch (e) {
      return fallback;
    }
  }

  function write(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      /* 隐私模式 / file:// 限制：静默降级 */
    }
  }

  function remove(key) {
    try {
      window.localStorage.removeItem(key);
    } catch (e) {
      /* 忽略 */
    }
  }

  function readJSON(key, fallback) {
    var raw = read(key, null);
    if (!raw) return fallback;
    try {
      var val = JSON.parse(raw);
      return val && typeof val === "object" ? val : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function today() {
    var d = new Date();
    var m = String(d.getMonth() + 1);
    var day = String(d.getDate());
    if (m.length < 2) m = "0" + m;
    if (day.length < 2) day = "0" + day;
    return m + "-" + day;
  }

  /* 根据 app.js 自身位置反推教程根目录，再算当前页到根的前缀 */
  function computePrefix() {
    var base = "";
    var script = document.currentScript;
    if (script && script.src) {
      base = script.src.replace(/assets\/js\/app\.js(?:\?[^#]*)?(?:#.*)?$/, "");
    }
    var here = window.location.href.split("#")[0].split("?")[0];
    if (base && here.indexOf(base) === 0) {
      var rest = here.slice(base.length);
      var depth = rest.split("/").length - 1;
      if (depth > 0) {
        var out = "";
        for (var i = 0; i < depth; i++) out += "../";
        return out;
      }
      return "";
    }
    /* 兜底：按路径判断层级 */
    return /\/pages\//.test(window.location.pathname) ? "../" : "";
  }

  var prefix = computePrefix();

  function allChapters() {
    var list = [];
    if (TOC.home) list.push({ chapter: TOC.home, group: null });
    (TOC.groups || []).forEach(function (g) {
      (g.chapters || []).forEach(function (ch) {
        list.push({ chapter: ch, group: g });
      });
    });
    return list;
  }

  function findEntry(id) {
    var all = allChapters();
    for (var i = 0; i < all.length; i++) {
      if (all[i].chapter.id === id) return all[i];
    }
    return null;
  }

  function linkTo(chapter) {
    return prefix + chapter.file;
  }

  function chapterNo(chapter, index, group) {
    if (group && group.numbering === "index") {
      var n0 = String(index + 1);
      return n0.length < 2 ? "0" + n0 : n0;
    }
    var m = /-(\d+)$/.exec(chapter.id || "");
    if (m) return m[1].length < 2 ? "0" + m[1] : m[1];
    var n = String(index + 1);
    return n.length < 2 ? "0" + n : n;
  }

  /* ---------- 提示条 ---------- */

  function toast(message) {
    var el = document.getElementById("toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "toast";
      el.className = "toast";
      el.setAttribute("role", "status");
      el.setAttribute("aria-live", "polite");
      document.body.appendChild(el);
    }
    el.textContent = message;
    /* 强制回流，保证连续调用时动画可重放 */
    void el.offsetWidth;
    el.classList.add("is-show");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () {
      el.classList.remove("is-show");
    }, 3000);
  }

  /* ---------- 导航 ---------- */

  function buildNav() {
    var nav = $("#nav");
    if (!nav) return;

    var collapsed = readJSON(KEY.nav, {});
    var html = "";

    if (TOC.home) {
      var homeCurrent = currentChapter === TOC.home.id;
      html +=
        '<a class="nav__home' + (homeCurrent ? " is-current" : "") + '" href="' +
        esc(linkTo(TOC.home)) + '" data-chapter="' + esc(TOC.home.id) + '"' +
        (homeCurrent ? ' aria-current="page"' : "") + ">" +
        '<span class="nav__home-dot" aria-hidden="true"></span>' +
        '<span>' + esc(TOC.home.title) + "</span></a>";
    }

    (TOC.groups || []).forEach(function (group) {
      var isCollapsed = collapsed[group.id] === true;
      html +=
        '<section class="nav__group' + (isCollapsed ? " is-collapsed" : "") +
        '" data-group="' + esc(group.id) + '">' +
        '<button class="nav__grouphead" type="button" aria-expanded="' +
        (isCollapsed ? "false" : "true") + '" aria-controls="nav-list-' + esc(group.id) + '">' +
        '<span class="nav__chev" aria-hidden="true">' +
        '<svg viewBox="0 0 12 12"><path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
        "</span>" +
        '<span class="nav__part">' + esc(group.part || "") + "</span>" +
        '<span class="nav__grouptitle">' + esc(group.title) + "</span>" +
        '<span class="nav__count">' + (group.chapters || []).length + "</span>" +
        "</button>" +
        '<ul class="nav__list" id="nav-list-' + esc(group.id) + '">';

      (group.chapters || []).forEach(function (chapter, index) {
        var isCurrent = chapter.id === currentChapter;
        var todo = chapter.status === "todo";
        html +=
          "<li>" +
          '<a class="nav__link' + (isCurrent ? " is-current" : "") + '" href="' +
          esc(linkTo(chapter)) + '" data-chapter="' + esc(chapter.id) + '"' +
          (todo ? ' data-todo="1"' : "") +
          (isCurrent ? ' aria-current="page"' : "") + ">" +
          '<span class="nav__no">' + chapterNo(chapter, index, group) + "</span>" +
          '<span class="nav__title">' + esc(chapter.title) + "</span>" +
          (todo ? '<span class="nav__badge">待写</span>' : "") +
          "</a></li>";
      });

      html += "</ul></section>";
    });

    nav.innerHTML = html;
    bindNav(nav);
    restoreNavScroll(nav);
  }

  /* 侧栏滚动位置：换页时保留，避免每次点章节都跳回顶部 */
  var navScrollTimer = null;

  function saveNavScroll(nav) {
    try {
      sessionStorage.setItem(KEY.navScroll, String(nav.scrollTop));
    } catch (err) {}
  }

  function restoreNavScroll(nav) {
    var saved = 0;
    try {
      saved = parseInt(sessionStorage.getItem(KEY.navScroll), 10) || 0;
    } catch (err) {}
    if (!saved) return;
    nav.scrollTop = saved;
    /* 字体度量完成后高度可能变化，再对齐一次 */
    window.requestAnimationFrame(function () {
      nav.scrollTop = saved;
    });
  }

  function bindNav(nav) {
    nav.addEventListener("scroll", function () {
      window.clearTimeout(navScrollTimer);
      navScrollTimer = window.setTimeout(function () {
        saveNavScroll(nav);
      }, 120);
    }, { passive: true });

    window.addEventListener("beforeunload", function () {
      saveNavScroll(nav);
    });

    nav.addEventListener("click", function (e) {
      var target = e.target;
      if (!target || !target.closest) return;

      var head = target.closest(".nav__grouphead");
      if (head) {
        var group = head.parentNode;
        var nowCollapsed = group.classList.toggle("is-collapsed");
        head.setAttribute("aria-expanded", nowCollapsed ? "false" : "true");
        persistCollapsed(nav);
        return;
      }

      var todoLink = target.closest("a[data-todo]");
      if (todoLink) {
        e.preventDefault();
        var titleEl = todoLink.querySelector(".nav__title");
        var title = titleEl ? titleEl.textContent : "这一章";
        toast("「" + title + "」还没写。目录已登记，正文会随章节陆续补齐。");
        closeNav();
        return;
      }

      if (target.closest("a")) saveNavScroll(nav);
      closeNav();
    });
  }

  function persistCollapsed(nav) {
    var state = {};
    $$(".nav__group", nav).forEach(function (group) {
      if (group.classList.contains("is-collapsed")) {
        state[group.getAttribute("data-group")] = true;
      }
    });
    write(KEY.nav, JSON.stringify(state));
  }

  /* ---------- 移动端抽屉 ---------- */

  function openNav() {
    document.body.classList.add("is-nav-open");
    var btn = $("#menu-btn");
    if (btn) btn.setAttribute("aria-expanded", "true");
  }

  function closeNav() {
    if (!document.body.classList.contains("is-nav-open")) return;
    document.body.classList.remove("is-nav-open");
    var btn = $("#menu-btn");
    if (btn) btn.setAttribute("aria-expanded", "false");
  }

  function bindChrome() {
    var menuBtn = $("#menu-btn");
    var backdrop = $("#nav-backdrop");
    if (menuBtn) {
      menuBtn.addEventListener("click", function () {
        if (document.body.classList.contains("is-nav-open")) closeNav();
        else openNav();
      });
    }
    if (backdrop) backdrop.addEventListener("click", closeNav);
    window.addEventListener("resize", function () {
      if (window.innerWidth > 1000) closeNav();
    });
  }

  /* ---------- 搜索（标题过滤 + 全文索引） ---------- */

  function bindSearch() {
    var input = $("#search-input");
    var panel = $("#search-results");
    var nav = $("#nav");
    if (!input || !panel) return;

    var index = allChapters().filter(function (item) {
      return item.chapter.id !== (TOC.home ? TOC.home.id : "");
    });
    var fulltext = window.SEARCH_INDEX || [];

    function closePanel() {
      panel.hidden = true;
      panel.innerHTML = "";
      input.setAttribute("aria-expanded", "false");
      activeResult = -1;
      if (nav) {
        nav.classList.remove("is-searching");
        $$(".nav__link", nav).forEach(function (a) {
          a.classList.remove("is-hidden");
        });
        $$(".nav__group", nav).forEach(function (g) {
          g.classList.remove("is-hidden");
        });
      }
    }

    function filterNav(query) {
      if (!nav) return;
      var q = query.toLowerCase();
      $$(".nav__group", nav).forEach(function (group) {
        var visible = 0;
        $$(".nav__link", group).forEach(function (a) {
          var titleEl = a.querySelector(".nav__title");
          var text = (titleEl ? titleEl.textContent : a.textContent) || "";
          var hit = text.toLowerCase().indexOf(q) !== -1;
          a.classList.toggle("is-hidden", !hit);
          if (hit) visible++;
        });
        group.classList.toggle("is-hidden", visible === 0);
      });
      nav.classList.add("is-searching");
    }

    function renderResults(query) {
      var q = query.toLowerCase();
      var hits = [];

      if (fulltext.length) {
        /* 全文检索：标题 8 分、小节标题 5 分、正文 3 分 + 词频（最多 3 次） */
        hits = fulltext
          .map(function (e) {
            var t = (e.t || "").toLowerCase();
            var h = (e.h || "").toLowerCase();
            var x = (e.x || "").toLowerCase();
            var s = 0;
            if (t.indexOf(q) !== -1) s += 8;
            if (h.indexOf(q) !== -1) s += 5;
            var pos = x.indexOf(q);
            if (pos !== -1) {
              s += 3;
              var c = 0;
              while (pos !== -1 && c < 3) {
                c++;
                pos = x.indexOf(q, pos + q.length);
              }
              s += c;
            }
            return { e: e, s: s };
          })
          .filter(function (r) {
            return r.s > 0;
          })
          .sort(function (a, b) {
            return b.s - a.s;
          })
          .slice(0, 12);
      } else {
        hits = index
          .filter(function (item) {
            var hay = (item.chapter.title + " " + item.chapter.id + " " +
              (item.group ? item.group.title : "")).toLowerCase();
            return hay.indexOf(q) !== -1;
          })
          .map(function (item) {
            return { e: { t: item.chapter.title, g: item.group ? item.group.title : "导读", h: "", x: "", p: item.chapter.file, a: "" }, s: 1, item: item };
          });
      }

      panel.innerHTML = "";
      activeResult = -1;

      if (!hits.length) {
        panel.innerHTML = '<p class="search__empty">没有匹配的内容。试试「压缩」「缓存」「子代理」。</p>';
      } else {
        hits.forEach(function (hit, i) {
          var e = hit.e;
          var a = document.createElement("a");
          a.className = "search__item";
          a.href = prefix + e.p + (e.a ? "#" + e.a : "");
          a.id = "search-opt-" + i;
          a.setAttribute("role", "option");
          a.innerHTML =
            '<span class="search__t">' + esc(e.t) + "</span>" +
            '<span class="search__g">' + esc(e.g || "导读") + "</span>" +
            (e.h && e.h !== e.t ? '<span class="search__h">' + esc(e.h) + "</span>" : "") +
            (e.x ? '<span class="search__x">' + markSnippet(e.x, query) + "</span>" : "");
          a.addEventListener("click", function () {
            closePanel();
          });
          panel.appendChild(a);
        });
        panel.insertAdjacentHTML(
          "beforeend",
          '<p class="search__foot">全文搜索 · 覆盖 ' + fulltext.length + " 个小节</p>"
        );
      }

      panel.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }

    function setActive(next) {
      var items = $$(".search__item", panel);
      if (!items.length) return;
      activeResult = (next + items.length) % items.length;
      items.forEach(function (el, i) {
        el.classList.toggle("is-active", i === activeResult);
      });
      var cur = items[activeResult];
      if (cur) {
        cur.scrollIntoView({ block: "nearest" });
        input.setAttribute("aria-activedescendant", cur.id);
      }
    }

    input.addEventListener("input", function () {
      var q = input.value.trim();
      if (!q) {
        closePanel();
        return;
      }
      renderResults(q);
      filterNav(q);
    });

    input.addEventListener("focus", function () {
      if (input.value.trim()) {
        renderResults(input.value.trim());
        filterNav(input.value.trim());
      }
    });

    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" && !panel.hidden) {
        e.preventDefault();
        setActive(activeResult + 1);
      } else if (e.key === "ArrowUp" && !panel.hidden) {
        e.preventDefault();
        setActive(activeResult - 1);
      } else if (e.key === "Enter" && !panel.hidden) {
        var items = $$(".search__item", panel);
        var target = items[activeResult >= 0 ? activeResult : 0];
        if (target) {
          e.preventDefault();
          target.click();
        }
      } else if (e.key === "Escape") {
        if (!panel.hidden) {
          e.preventDefault();
          closePanel();
          input.blur();
        }
      }
    });

    document.addEventListener("click", function (e) {
      if (!e.target || !e.target.closest) return;
      if (!e.target.closest(".search")) closePanel();
    });
  }

  /* ---------- 主题 ---------- */

  function effectiveTheme() {
    var attr = document.documentElement.getAttribute("data-theme");
    if (attr === "dark" || attr === "light") return attr;
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  }

  function refreshThemeLabel() {
    var btn = $("#theme-btn");
    if (!btn) return;
    var dark = effectiveTheme() === "dark";
    var label = dark ? "切换到浅色模式" : "切换到深色模式";
    btn.setAttribute("aria-label", label);
    btn.setAttribute("title", label);
  }

  function bindTheme() {
    var btn = $("#theme-btn");
    refreshThemeLabel();
    if (btn) {
      btn.addEventListener("click", function () {
        var next = effectiveTheme() === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        write(KEY.theme, next);
        refreshThemeLabel();
        toast(next === "dark" ? "已切换到深色模式" : "已切换到浅色模式");
      });
    }
    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      var onChange = function () {
        refreshThemeLabel();
      };
      if (mq.addEventListener) mq.addEventListener("change", onChange);
      else if (mq.addListener) mq.addListener(onChange);
    }
  }

  /* ---------- 弹窗 ---------- */

  function openModal(id) {
    var modal = document.getElementById("modal-" + id);
    if (!modal) {
      toast("没有找到弹窗 #modal-" + id);
      return;
    }
    if (!modal.hidden) return;

    var hadOpen = $(".modal.is-open");
    closeAllModals(true);
    if (!hadOpen) lastFocus = document.activeElement;
    modal.hidden = false;
    document.body.classList.add("is-modal-open");
    modal.classList.add("is-open");

    var panel = $(".modal__panel", modal);
    if (panel) {
      window.setTimeout(function () {
        try {
          panel.focus();
        } catch (e) {
          /* 忽略 */
        }
      }, 20);
    }
  }

  function closeAllModals(skipFocus) {
    var open = $$(".modal.is-open");
    open.forEach(function (modal) {
      modal.classList.remove("is-open");
      modal.hidden = true;
    });
    document.body.classList.remove("is-modal-open");

    if (!skipFocus && lastFocus && lastFocus.focus) {
      try {
        lastFocus.focus();
      } catch (e) {
        /* 忽略 */
      }
    }
    if (!skipFocus && /^#modal-/.test(window.location.hash || "")) {
      clearModalHash();
    }
  }

  function clearModalHash() {
    try {
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    } catch (e) {
      /* 某些 file:// 环境不允许，忽略 */
    }
  }

  function handleHashModal() {
    var hash = window.location.hash || "";
    if (hash.indexOf("#modal-") !== 0) {
      /* 用户按了后退，或手动清掉哈希：把还开着的弹窗收起 */
      if ($(".modal.is-open")) closeAllModals(false);
      return;
    }
    var id = hash.slice(7);
    var modal = document.getElementById("modal-" + id);
    if (modal && modal.hidden) openModal(id);
  }

  function bindModals() {
    document.addEventListener("click", function (e) {
      var t = e.target;
      if (!t || !t.closest) return;

      var trigger = t.closest("[data-modal]");
      if (trigger) {
        e.preventDefault();
        openModal(trigger.getAttribute("data-modal"));
        return;
      }

      var closer = t.closest("[data-close]");
      if (closer) {
        var modal = closer.closest(".modal");
        if (modal) {
          e.preventDefault();
          closeAllModals(false);
        }
        return;
      }

      var anchor = t.closest('a[href^="#modal-"]');
      if (anchor) {
        e.preventDefault();
        var href = anchor.getAttribute("href") || "";
        openModal(href.slice(7));
        try {
          window.history.replaceState(null, "", href);
        } catch (err) {
          /* 忽略 */
        }
        return;
      }

      /* 点击面板外的空白区也关闭 */
      if (t.classList && t.classList.contains("modal")) {
        closeAllModals(false);
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if ($(".modal.is-open")) {
          e.preventDefault();
          closeAllModals(false);
          return;
        }
        if (document.body.classList.contains("is-nav-open")) {
          closeNav();
          return;
        }
      }

      if (e.key === "Tab") {
        var modal = $(".modal.is-open");
        if (!modal) return;
        var panel = $(".modal__panel", modal);
        if (!panel) return;
        var nodes = $$(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
          panel
        ).filter(function (el) {
          return el.offsetParent !== null || el === document.activeElement;
        });
        if (!nodes.length) return;
        var first = nodes[0];
        var last = nodes[nodes.length - 1];
        if (e.shiftKey && (document.activeElement === first || document.activeElement === panel)) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    });

    window.addEventListener("hashchange", handleHashModal);
    handleHashModal();
  }

  /* ---------- 小测验 ---------- */

  function bindQuiz() {
    document.addEventListener("click", function (e) {
      var t = e.target;
      if (!t || !t.closest) return;
      var btn = t.closest("[data-quiz-toggle]");
      if (!btn) return;
      var quiz = btn.closest(".quiz");
      if (!quiz) return;
      var answer = $(".quiz__answer", quiz);
      if (!answer) return;

      var willOpen = answer.hidden;
      answer.hidden = !willOpen;
      btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
      btn.textContent = willOpen ? "收起答案" : "看答案";
    });
  }

  /* ---------- 复制代码 ---------- */

  function fallbackCopy(text) {
    return new Promise(function (resolve, reject) {
      try {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed";
        ta.style.top = "-2000px";
        ta.style.left = "0";
        document.body.appendChild(ta);
        ta.select();
        ta.setSelectionRange(0, text.length);
        var ok = document.execCommand("copy");
        document.body.removeChild(ta);
        if (ok) resolve();
        else reject(new Error("execCommand failed"));
      } catch (err) {
        reject(err);
      }
    });
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).catch(function () {
        return fallbackCopy(text);
      });
    }
    return fallbackCopy(text);
  }

  function selectCode(code) {
    try {
      var range = document.createRange();
      range.selectNodeContents(code);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    } catch (e) {
      /* 忽略 */
    }
  }

  function bindCopy() {
    document.addEventListener("click", function (e) {
      var t = e.target;
      if (!t || !t.closest) return;
      var btn = t.closest("[data-copy]");
      if (!btn) return;
      var block = btn.closest(".codeblock");
      var code = block ? $("code", block) : null;
      if (!code) return;

      var text = (code.innerText || code.textContent || "").replace(/\r\n/g, "\n");
      text = text.replace(/^\n+/, "").replace(/\n+$/, "");
      if (!text) return;

      var original = btn.getAttribute("data-label") || btn.textContent;
      btn.setAttribute("data-label", original);

      copyText(text).then(
        function () {
          btn.textContent = "已复制";
          btn.classList.add("is-copied");
          window.setTimeout(function () {
            btn.textContent = original;
            btn.classList.remove("is-copied");
          }, 1600);
        },
        function () {
          selectCode(code);
          toast("自动复制被浏览器阻止，已选中代码，请按 ⌘C 或 Ctrl+C 复制。");
        }
      );
    });
  }

  /* ---------- 最近阅读 ---------- */

  function saveRecent(entry) {
    var payload = {
      id: entry.chapter.id,
      title: entry.chapter.title,
      file: entry.chapter.file,
      at: today()
    };
    write(KEY.recent, JSON.stringify(payload));
  }

  function readRecent() {
    var data = readJSON(KEY.recent, null);
    if (!data || !data.file || !data.title) return null;
    return data;
  }

  function renderRecent() {
    var data = readRecent();
    var box = $("#recent");
    if (box) {
      if (!data) {
        box.hidden = true;
      } else {
        box.innerHTML =
          '<span class="recent__label">上次读到 · ' + esc(data.at || "") + "</span>" +
          '<a class="recent__link" href="' + esc(prefix + data.file) + '">' +
          esc(data.title) + "</a>";
        box.hidden = false;
      }
    }

    var slot = $("[data-recent-slot]");
    if (slot) {
      if (!data) {
        slot.innerHTML = "";
      } else {
        slot.innerHTML =
          '<div class="recent-card"><div>' +
          '<p class="recent-card__label">继续上次阅读 · ' + esc(data.at || "") + "</p>" +
          '<a class="recent-card__title" href="' + esc(prefix + data.file) + '">' +
          esc(data.title) + "</a>" +
          "</div>" +
          '<button class="btn btn--ghost btn--small" type="button" data-clear-recent>清除记录</button>' +
          "</div>";
      }
    }
  }

  function bindRecent() {
    var entry = findEntry(currentChapter);
    if (entry && entry.chapter.id !== (TOC.home ? TOC.home.id : "")) {
      saveRecent(entry);
    }
    renderRecent();

    document.addEventListener("click", function (e) {
      var t = e.target;
      if (!t || !t.closest) return;
      if (t.closest("[data-clear-recent]")) {
        remove(KEY.recent);
        renderRecent();
        toast("已清除阅读记录。");
      }
    });
  }

  /* ---------- 版面增强（第三版改版） ----------
   * 1. 本页目录：宽屏右侧显示各节标题，滚动时高亮当前节
   * 2. SVG 图文字自适应：按实际字体测量，文字超出方框或行距过密时缩小字号；
   *    内容超出画布时扩大 viewBox。不同系统字体（PingFang / 雅黑 / Noto）宽度不同，
   *    所以必须在浏览器里按真实渲染结果调整，而不是靠写死的坐标。
   * 3. 行内代码在 _ . / 等位置插入 <wbr>，长标识符只在自然断点换行
   * 4. 对比表：可横向滚动时显示提示；“已核实”改为对勾并在表注加图例
   * 5. 工具卡片显示弹窗首句作为一句话摘要；弹窗“关键参数”拆成列表
   */

  function buildPageToc() {
    var main = $(".main");
    var prose = $(".prose", main || document);
    if (!main || !prose || $(".page-toc", main)) return;
    var heads = $$(".prose > section > h2", main).filter(function (h) {
      return h.parentElement.id;
    });
    if (heads.length < 3) return;

    var nav = document.createElement("nav");
    nav.className = "page-toc";
    nav.setAttribute("aria-label", "本页目录");
    var title = document.createElement("p");
    title.className = "page-toc__title";
    title.textContent = "本页目录";
    nav.appendChild(title);
    var ol = document.createElement("ol");
    var links = [];
    heads.forEach(function (h, i) {
      var sec = h.parentElement;
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = "#" + sec.id;
      var no = document.createElement("span");
      no.className = "page-toc__no";
      no.textContent = (i < 9 ? "0" : "") + (i + 1);
      var label = document.createElement("span");
      label.textContent = h.textContent.replace(/\s+/g, " ").trim();
      a.appendChild(no);
      a.appendChild(label);
      li.appendChild(a);
      ol.appendChild(li);
      links.push({ a: a, sec: sec });
    });
    nav.appendChild(ol);
    main.appendChild(nav);
    main.classList.add("has-toc");

    var ticking = false;
    function update() {
      ticking = false;
      var line = window.innerHeight * 0.3;
      var current = links[0];
      links.forEach(function (item) {
        if (item.sec.getBoundingClientRect().top <= line) current = item;
      });
      links.forEach(function (item) {
        item.a.classList.toggle("is-active", item === current);
      });
    }
    window.addEventListener(
      "scroll",
      function () {
        if (!ticking) {
          ticking = true;
          window.requestAnimationFrame(update);
        }
      },
      { passive: true }
    );
    update();
  }

  var FIT_MIN = 0.72; // 字号最多缩到原来的 72%
  var FIT_LINE = 1.3; // 同一方框内多行文字，行距至少 1.3 倍字号

  function textLines(t) {
    var spans = $$("tspan", t).filter(function (s) {
      return s.getAttribute("x") !== null || s.getAttribute("dy") !== null || s.getAttribute("y") !== null;
    });
    if (spans.length < 2) return [t.getBoundingClientRect()];
    return spans.map(function (s) {
      return s.getBoundingClientRect();
    });
  }

  function fitSvg(svg) {
    if (svg.getAttribute("data-fitted")) return;
    var vb = svg.viewBox && svg.viewBox.baseVal;
    var sb = svg.getBoundingClientRect();
    if (!vb || !vb.width || !sb.width) return; // 不可见（弹窗、折叠中），稍后再试
    svg.setAttribute("data-fitted", "1");

    var ppu = sb.width / vb.width; // 每个 viewBox 单位对应的像素
    var pad = 6 * ppu;
    var rects = $$("rect", svg)
      .map(function (r) {
        return { el: r, b: r.getBoundingClientRect(), texts: [] };
      })
      .filter(function (r) {
        return r.b.width > 18 && r.b.height > 12;
      });

    var items = [];
    $$("text", svg).forEach(function (t) {
      var tb = t.getBoundingClientRect();
      if (!tb.width) return;
      var cs = window.getComputedStyle(t);
      var anchor = cs.textAnchor;
      var ax = anchor === "middle" ? tb.left + tb.width / 2 : anchor === "end" ? tb.right - 2 : tb.left + 2;
      var ay = tb.top + tb.height / 2;
      var box = null;
      rects.forEach(function (r) {
        var b = r.b;
        if (ax >= b.left && ax <= b.right && ay >= b.top && ay <= b.bottom) {
          if (!box || b.width * b.height < box.b.width * box.b.height) box = r;
        }
      });
      var item = { t: t, tb: tb, anchor: anchor, fs: parseFloat(cs.fontSize) || 16, kw: 1, kl: 1, box: box };
      if (box) {
        var b = box.b;
        var avail;
        if (anchor === "middle") avail = b.width - 2 * pad;
        else if (anchor === "end") avail = tb.right - (b.left + pad);
        else avail = b.right - pad - tb.left;
        if (avail > 0 && tb.width > avail) item.kw = avail / tb.width;
        box.texts.push(item);
      }
      items.push(item);
    });

    /* 同一方框内的多行文字：行距不足时整体缩小 */
    rects.forEach(function (r) {
      if (!r.texts.length) return;
      var lines = [];
      r.texts.forEach(function (it) {
        textLines(it.t).forEach(function (lb) {
          if (lb.height) lines.push({ top: lb.top + lb.height / 2, left: lb.left, right: lb.right, it: it });
        });
      });
      if (lines.length < 2) return;
      lines.sort(function (a, b) {
        return a.top - b.top;
      });
      var minGap = Infinity;
      var fsPx = 0;
      /* 只比较上下相邻、且水平方向有重叠的两行；同一行里的编号、标题、备注不算 */
      for (var i = 0; i < lines.length; i++) {
        for (var j = i + 1; j < lines.length; j++) {
          var a = lines[i];
          var c = lines[j];
          var f = Math.max(a.it.fs, c.it.fs) * ppu;
          var gap = c.top - a.top;
          if (gap < 0.5 * f) continue;
          if (Math.min(a.right, c.right) - Math.max(a.left, c.left) <= 0) continue;
          if (gap < minGap) {
            minGap = gap;
            fsPx = f;
          }
          break;
        }
      }
      if (minGap === Infinity || !fsPx) return;
      if (minGap < FIT_LINE * fsPx) {
        var k = minGap / (FIT_LINE * fsPx);
        r.texts.forEach(function (it) {
          it.kl = Math.min(it.kl, k);
        });
      }
    });

    items.forEach(function (it) {
      var want = Math.min(it.kw, it.kl);
      if (want >= 0.995) return;
      var k = Math.max(FIT_MIN, want);
      it.t.style.fontSize = (it.fs * k).toFixed(2) + "px";
      /* 缩到下限仍放不下：单行文字用 textLength 压紧字距 */
      if (it.kw < FIT_MIN && it.box && textLines(it.t).length < 2) {
        var b = it.box.b;
        var availPx = it.anchor === "middle" ? b.width - 2 * pad : it.anchor === "end" ? it.tb.right - (b.left + pad) : b.right - pad - it.tb.left;
        if (availPx > 0) {
          it.t.setAttribute("textLength", (availPx / ppu).toFixed(1));
          it.t.setAttribute("lengthAdjust", "spacingAndGlyphs");
        }
      }
    });

    /* 内容超出画布：扩大 viewBox，四周留 8 个单位 */
    try {
      var bb = svg.getBBox();
      var x0 = Math.min(vb.x, bb.x - 8);
      var y0 = Math.min(vb.y, bb.y - 8);
      var x1 = Math.max(vb.x + vb.width, bb.x + bb.width + 8);
      var y1 = Math.max(vb.y + vb.height, bb.y + bb.height + 8);
      var grow = x0 < vb.x - 0.5 || y0 < vb.y - 0.5 || x1 > vb.x + vb.width + 0.5 || y1 > vb.y + vb.height + 0.5;
      if (grow) {
        svg.setAttribute("viewBox", [x0, y0, x1 - x0, y1 - y0].map(function (n) {
          return Math.round(n * 10) / 10;
        }).join(" "));
      }
    } catch (e) {
      /* getBBox 在不可见元素上会抛错，忽略 */
    }
  }

  function fitFigures() {
    $$(".prose svg[viewBox], .modal svg[viewBox]").forEach(function (svg) {
      if (svg.closest(".demo") || svg.closest("button") || svg.closest(".topbar")) return;
      if (svg.viewBox.baseVal.width < 120) return; // 图标
      fitSvg(svg);
    });
  }

  function bindFigureFit() {
    var run = function () {
      fitFigures();
    };
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(run);
    window.addEventListener("load", run);
    run();
    /* 弹窗打开、答案展开后，原来不可见的图才有尺寸 */
    document.addEventListener("click", function () {
      window.setTimeout(run, 60);
    });
  }

  function softBreakCode() {
    $$(".prose code, .modal code").forEach(function (c) {
      if (c.closest("pre") || c.children.length || c.getAttribute("data-wbr")) return;
      var s = c.textContent;
      if (s.length < 14 || !/[_./:,=(]/.test(s)) return;
      c.setAttribute("data-wbr", "1");
      var parts = s.split(/([_./:,=(]+)/);
      c.textContent = "";
      parts.forEach(function (p, i) {
        if (!p) return;
        c.appendChild(document.createTextNode(p));
        if (i % 2 === 1) c.appendChild(document.createElement("wbr"));
      });
    });
  }

  function enhanceTables() {
    $$(".table-wrap").forEach(function (wrap) {
      var prev = wrap.previousElementSibling;
      var hint = prev && prev.classList.contains("table-hint") ? prev : null;
      var refresh = function () {
        if (hint) hint.classList.toggle("is-on", wrap.scrollWidth > wrap.clientWidth + 4);
      };
      refresh();
      window.addEventListener("resize", refresh);

      var oks = $$(".data-table .tag--ok", wrap);
      oks.forEach(function (t) {
        var label = t.textContent.trim() || "已核实";
        t.title = label;
        t.setAttribute("aria-label", label);
      });
      if (oks.length) {
        var next = wrap.nextElementSibling;
        var legend = document.createElement("span");
        legend.className = "table-legend";
        legend.textContent = "✓ = 已核实";
        if (next && next.classList.contains("table-caption")) {
          next.insertBefore(legend, next.firstChild);
        } else {
          var p = document.createElement("p");
          p.className = "table-caption";
          p.appendChild(legend);
          wrap.parentNode.insertBefore(p, wrap.nextSibling);
        }
      }
    });
  }

  function firstSentence(text) {
    var s = text.replace(/\s+/g, " ").trim();
    var m = s.match(/^(.{8,80}?[。；！？])/);
    return m ? m[1] : s.slice(0, 60);
  }

  function enhanceToolCards() {
    $$(".tool-btn[data-modal]").forEach(function (btn) {
      if ($(".tool-btn__sum", btn)) return;
      var modal = document.getElementById("modal-" + btn.getAttribute("data-modal"));
      var lead = modal && $(".modal__lead", modal);
      if (!lead) return;
      var sum = document.createElement("span");
      sum.className = "tool-btn__sum";
      sum.textContent = firstSentence(lead.textContent);
      btn.appendChild(sum);
    });
  }

  /* 弹窗里“关键参数与默认值”这一项：按“；”拆成列表，避免一长串行内代码挤成一团 */
  function enhanceKv() {
    $$(".modal .kv dd").forEach(function (dd) {
      var dt = dd.previousElementSibling;
      if (!dt || !/参数/.test(dt.textContent)) return;
      if ($$("code", dd).length < 3 || dd.textContent.split("；").length < 3) return;
      var groups = [[]];
      Array.prototype.slice.call(dd.childNodes).forEach(function (node) {
        if (node.nodeType === 3 && node.nodeValue.indexOf("；") !== -1) {
          var bits = node.nodeValue.split("；");
          bits.forEach(function (bit, i) {
            if (i > 0) groups.push([]);
            if (bit.trim()) groups[groups.length - 1].push(document.createTextNode(bit));
          });
        } else {
          groups[groups.length - 1].push(node);
        }
      });
      groups = groups.filter(function (g) {
        return g.some(function (n) {
          return (n.textContent || "").trim();
        });
      });
      if (groups.length < 3) return;
      var ul = document.createElement("ul");
      ul.className = "kv-list";
      groups.forEach(function (g) {
        var li = document.createElement("li");
        g.forEach(function (n) {
          li.appendChild(n);
        });
        ul.appendChild(li);
      });
      dd.textContent = "";
      dd.appendChild(ul);
    });
  }

  function enhanceLayout() {
    var steps = [buildPageToc, enhanceKv, softBreakCode, enhanceTables, enhanceToolCards, bindFigureFit];
    steps.forEach(function (fn) {
      try {
        fn();
      } catch (e) {
        if (window.console) console.warn("[layout]", fn.name, e);
      }
    });
  }

  /* ---------- 初始化 ---------- */

  function init() {
    currentChapter = document.body.getAttribute("data-chapter") || "";
    buildNav();
    bindChrome();
    bindSearch();
    bindTheme();
    bindModals();
    bindQuiz();
    bindCopy();
    bindRecent();
    enhanceLayout();
  }

  window.CTX = {
    openModal: openModal,
    closeModal: function () {
      closeAllModals(false);
    },
    toast: toast,
    get prefix() {
      return prefix;
    },
    toc: TOC
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window, document);
