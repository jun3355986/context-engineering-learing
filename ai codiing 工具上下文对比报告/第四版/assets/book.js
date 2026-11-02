/* 第四版共用脚本：主题切换、左侧目录、上一章/下一章、答案框里的「回到问题」。
   新写完一章：在下面 BOOK.chapters 里按顺序加一行（只放已经写好的章）。
   规范说明见 docs/第四版重构指南.md 第 3.4 节。 */
(function () {
  'use strict';

  var BOOK = {
    title: 'AI 编程 agent 的上下文管理',
    sub: '第四版 · 回到目录',
    home: 'index.html',
    chapters: [
      { no: '第 2 章', name: '一次请求里装了什么', file: '02-一次请求里装了什么.html' },
      { no: '第 3 章', name: '命令输出几万行', file: '03-命令输出几万行.html' },
      { no: '第 4 章', name: '压缩之后还记得什么', file: '04-压缩之后还记得什么.html' },
      { no: '第 5 章', name: '缓存省的是什么', file: '05-缓存省的是什么.html' },
      { no: '第 6 章', name: '工具多了会怎样', file: '06-工具多了会怎样.html' },
      { no: '第 7 章', name: '子代理省了什么', file: '07-子代理省了什么.html' },
      { no: '第 8 章', name: '回退分叉与恢复', file: '08-回退分叉恢复.html' },
      { no: '第 9 章', name: '新会话与记忆', file: '09-新会话怎么记得我.html' },
      { no: '第 10 章', name: '窗口满了会怎样', file: '10-窗口满了会怎样.html' },
      { no: '第 11 章', name: '怎么证明更好', file: '11-怎么证明更好.html' },
      { no: '第 12 章', name: '给场景设计策略', file: '12-给场景设计策略.html' },
      { no: '附录', name: '对照表和索引', file: '附录.html' }
    ]
  };

  /* ---------- 主题：在页面画出来之前执行，避免闪一下 ---------- */
  var root = document.documentElement;
  try { var saved = localStorage.getItem('ctx4-theme'); if (saved) root.setAttribute('data-theme', saved); } catch (e) {}
  var darkQuery = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  function isDark() {
    var t = root.getAttribute('data-theme');
    return t ? t === 'dark' : !!(darkQuery && darkQuery.matches);
  }
  function paintThemeButtons() {
    var dark = isDark();
    each(document.querySelectorAll('[data-theme-toggle]'), function (b) {
      b.textContent = dark ? '☀ 浅色' : '☾ 深色';
      b.setAttribute('aria-label', dark ? '切换到浅色' : '切换到深色');
    });
  }
  function toggleTheme() {
    var nx = isDark() ? 'light' : 'dark';
    root.setAttribute('data-theme', nx);
    try { localStorage.setItem('ctx4-theme', nx); } catch (e) {}
    paintThemeButtons();
  }
  if (darkQuery) {
    if (darkQuery.addEventListener) darkQuery.addEventListener('change', paintThemeButtons);
    else if (darkQuery.addListener) darkQuery.addListener(paintThemeButtons);
  }

  /* ---------- 小工具 ---------- */
  function each(list, fn) { for (var i = 0; i < list.length; i++) fn(list[i], i); }
  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    if (attrs) for (var k in attrs) if (Object.prototype.hasOwnProperty.call(attrs, k)) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    return e;
  }
  function themeButton(cls) {
    var b = el('button', { type: 'button', 'class': cls, 'data-theme-toggle': '' });
    b.addEventListener('click', toggleTheme);
    return b;
  }
  function currentFile() {
    var p = location.pathname;
    try { p = decodeURIComponent(p); } catch (e) {}
    return p.split('/').pop() || BOOK.home;
  }
  function headingText(h) {
    var c = h.cloneNode(true);
    each(c.querySelectorAll('.sn'), function (s) { s.parentNode.removeChild(s); });
    return c.textContent.replace(/\s+/g, ' ').trim();
  }

  /* ---------- 章节页 ---------- */
  function buildChapter(page) {
    var body = document.body;
    var file = currentFile();
    var idx = -1;
    each(BOOK.chapters, function (c, i) { if (c.file === file) idx = i; });
    var kicker = page.querySelector('.kicker');
    var h1 = page.querySelector('h1');
    var self = idx >= 0 ? BOOK.chapters[idx] : {
      no: kicker ? kicker.textContent.trim() : '',
      name: document.title || (h1 ? h1.textContent.trim() : ''),
      file: file
    };
    if (h1 && !h1.id) h1.id = 'top';
    var topHref = h1 ? '#' + h1.id : '#';

    /* 本章目录：h2 是一级，h3 是二级；.qs 里的 h3 不收 */
    var heads = [];
    each(page.querySelectorAll('h2, h3'), function (h) {
      if (h.tagName === 'H3' && h.closest && h.closest('.qs')) return;
      heads.push(h);
    });
    var toc = el('ul', { 'class': 'toc' });
    var items = [], curH2 = null, n = 0;
    each(heads, function (h) {
      var target = h;
      var sec = h.parentElement;
      if (h.tagName === 'H2' && sec && sec.tagName === 'SECTION' && sec.id && sec.firstElementChild === h) target = sec;
      else if (!h.id) { n += 1; h.id = 'toc-' + n; }
      var a = el('a', { href: '#' + target.id });
      var sn = h.querySelector('.sn');
      if (sn) a.appendChild(el('span', { 'class': 'sn' }, sn.textContent));
      a.appendChild(document.createTextNode(h.getAttribute('data-toc') || headingText(h)));
      var li = el('li');
      li.appendChild(a);
      if (h.tagName === 'H2' || !curH2) {
        toc.appendChild(li);
        if (h.tagName === 'H2') curH2 = { li: li, sub: null };
      } else {
        if (!curH2.sub) { curH2.sub = el('ul', { 'class': 'toc-sub' }); curH2.li.appendChild(curH2.sub); }
        curH2.sub.appendChild(li);
      }
      items.push({ h: h, a: a, top: h.tagName === 'H2' ? li : (curH2 ? curH2.li : li) });
    });

    /* 左侧栏 */
    var side = el('aside', { 'class': 'side', id: 'side', 'aria-label': '目录' });
    var book = el('a', { 'class': 'side-book', href: BOOK.home }, BOOK.title);
    book.appendChild(el('small', null, BOOK.sub));
    side.appendChild(book);
    var chaps = el('ul', { 'class': 'side-chaps' });
    var list = idx >= 0 ? BOOK.chapters : BOOK.chapters.concat([self]);
    each(list, function (c) {
      var li = el('li');
      var mine = c.file === file;
      var a = el('a', { href: mine ? topHref : c.file }, (c.no ? c.no + ' ' : '') + c.name);
      li.appendChild(a);
      if (mine) { li.className = 'cur'; li.appendChild(toc); }
      chaps.appendChild(li);
    });
    side.appendChild(chaps);
    var foot = el('div', { 'class': 'side-foot' });
    foot.appendChild(themeButton('side-btn'));
    side.appendChild(foot);

    /* 窄屏：顶栏 + 抽屉 */
    var bar = el('div', { 'class': 'topbar' });
    var menu = el('button', { type: 'button', 'class': 'side-btn', 'aria-controls': 'side', 'aria-expanded': 'false' }, '☰ 目录');
    bar.appendChild(menu);
    bar.appendChild(el('span', { 'class': 't' }, (self.no ? self.no + ' · ' : '') + self.name));
    bar.appendChild(themeButton('side-btn'));
    var scrim = el('div', { 'class': 'scrim' });
    function setOpen(open) {
      body.classList.toggle('side-open', open);
      menu.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    menu.addEventListener('click', function () { setOpen(!body.classList.contains('side-open')); });
    scrim.addEventListener('click', function () { setOpen(false); });
    side.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('a')) setOpen(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });

    body.insertBefore(scrim, body.firstChild);
    body.insertBefore(bar, body.firstChild);
    body.insertBefore(side, body.firstChild);

    /* 翻页 */
    var pager = el('nav', { 'class': 'pager', 'aria-label': '翻页' });
    function pageLink(c, cls, label) {
      var a = el('a', { 'class': cls, href: c ? c.file : BOOK.home });
      a.appendChild(el('small', null, label));
      a.appendChild(document.createTextNode(c ? c.no + ' ' + c.name : '全书目录'));
      return a;
    }
    pager.appendChild(pageLink(idx > 0 ? BOOK.chapters[idx - 1] : null, 'prev', idx > 0 ? '← 上一章' : '← 回到'));
    if (idx >= 0) {
      var next = idx < BOOK.chapters.length - 1 ? BOOK.chapters[idx + 1] : null;
      pager.appendChild(pageLink(next, 'next', next ? '下一章 →' : '回到 →'));
    }
    page.appendChild(pager);

    /* 答案框加「回到问题」 */
    each(page.querySelectorAll('.answer[id]'), function (box) {
      var m = /^a(\d+)$/.exec(box.id);
      var qh = box.querySelector('.qh');
      if (!m || !qh || qh.querySelector('.back') || !document.getElementById('q' + m[1])) return;
      qh.appendChild(el('a', { 'class': 'back', href: '#q' + m[1] }, '↑ 回到问题'));
    });

    /* 滚动时高亮当前小节 */
    var active = null, ticking = false;
    function spy() {
      ticking = false;
      if (!items.length) return;
      var line = (window.innerWidth <= 1000 ? 68 : 24) + 80;
      var cur = items[0];
      for (var i = 0; i < items.length; i++) {
        if (items[i].h.getBoundingClientRect().top <= line) cur = items[i]; else break;
      }
      if (cur === active) return;
      if (active) { active.a.classList.remove('on'); active.top.classList.remove('open'); }
      cur.a.classList.add('on');
      cur.top.classList.add('open');
      active = cur;
      var t = cur.a.offsetTop, hgt = cur.a.offsetHeight;
      if (t < side.scrollTop + 60) side.scrollTop = t - 60;
      else if (t + hgt > side.scrollTop + side.clientHeight - 60) side.scrollTop = t + hgt - side.clientHeight + 60;
    }
    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; window.requestAnimationFrame(spy); }
    }, { passive: true });
    window.addEventListener('resize', spy);
    spy();

    /* 带 # 打开时，目录生成后重新定位一次 */
    if (location.hash.length > 1) {
      var id = location.hash.slice(1);
      try { id = decodeURIComponent(id); } catch (e) {}
      var target = document.getElementById(id);
      if (target) target.scrollIntoView();
    }
  }

  /* ---------- 入口 ---------- */
  function build() {
    var page = document.querySelector('main.page');
    if (page && document.body.classList.contains('chapter')) buildChapter(page);
    else document.body.appendChild(themeButton('side-btn theme-float'));
    paintThemeButtons();
  }
  window.BOOK = BOOK;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();
