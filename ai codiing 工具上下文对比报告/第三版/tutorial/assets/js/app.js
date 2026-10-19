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
