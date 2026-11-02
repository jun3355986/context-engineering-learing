#!/usr/bin/env python3
"""生成 第四版/附录.html。三个第三版表格用程序解析后原样搬进来，Codex 和 Claude Code 两列、术语、源码索引来自 app_data.py / index_items.py。"""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from app_data import *  # noqa
from index_items import ITEMS  # noqa

V3 = "/home/ubuntu/work/context-engineering-learing/ai codiing 工具上下文对比报告/第三版/tutorial/pages"
OUT = "/home/ubuntu/work/context-engineering-learing/ai codiing 工具上下文对比报告/第四版/附录.html"

AGENTS = ["Codex", "Claude Code", "pi", "oh-my-pi", "opencode v1", "opencode v2", "Grok Build", "DeepSeek Harness"]

TAG = {"h": ('lvl-h', '高'), "m": ('lvl-m', '中'), "l": ('lvl-l', '待核实')}


def tag(level):
    cls, txt = TAG[level]
    return '<span class="tag %s">%s</span>' % (cls, txt)


def chs(nums):
    return "、".join(ch(n) for n in nums)


def esc(s):
    return html.escape(s, quote=False)


tag_re = re.compile(r"<[^>]+>")


def tv3(s):
    """第三版的字句搬进来时，只做用词统一（缺省 / 具体说法），不改意思"""
    s = s.replace("才是普通 LLM 摘要", "才是让 LLM 写摘要的那一级")
    s = s.replace("普通错误重试", "非超窗的错误才重试")
    return s.replace("默认", "缺省")



def plain(s):
    s = re.sub(r"<sup[^>]*>.*?</sup>", "", s, flags=re.S)
    return tv3(html.unescape(tag_re.sub("", s)).strip())


def code_keep(s):
    """保留 <code>，其余标签去掉，文本转义"""
    s = re.sub(r"<sup[^>]*>.*?</sup>", "", s, flags=re.S)
    parts = re.split(r"(<code>.*?</code>)", s, flags=re.S)
    out = []
    for p in parts:
        if p.startswith("<code>"):
            out.append("<code>%s</code>" % esc(plain(p)))
        else:
            out.append(esc(plain(p)))
    return "".join(out)


# ---------------------------------------------------------------- 解析第三版
mx = open(V3 + "/appendix-matrix.html", encoding="utf-8").read()
tbody = mx[mx.find("<tbody"):]
tbody = tbody[:tbody.find("</tbody>")]
MATRIX = []
for row in re.findall(r"<tr>\s*<th scope=\"row\".*?</th>(.*?)</tr>", tbody, re.S):
    cells = re.findall(r"<td>(.*?)</td>", row, re.S)
    assert len(cells) == 8, len(cells)
    line = []
    for c in cells:
        text = plain(re.split(r'<span class="tag', c)[0])
        flag = re.search(r'<span class="tag[^"]*">([^<]*)</span>', c).group(1)
        line.append((text, flag))
    MATRIX.append(line)
assert len(MATRIX) == 16, len(MATRIX)

pm = open(V3 + "/appendix-params.html", encoding="utf-8").read()
PARAMS = {}
for sid, body in re.findall(r'<section id="(params-[^"]+)">(.*?)</section>', pm, re.S):
    name = plain(re.search(r"<h2>(.*?)</h2>", body, re.S).group(1))
    ver = plain(re.search(r'<p class="small muted">(.*?)</p>', body, re.S).group(1)) if '<p class="small muted">' in body else ""
    rows = []
    for r in re.findall(r"<tr>\s*<th scope=\"row\">(.*?)</th>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>", body, re.S):
        src = plain(r[3])
        src = re.sub(r"#L(\d+)-L(\d+)", r":\1-\2", src)
        src = re.sub(r"#L(\d+)", r":\1", src)
        rows.append((code_keep(r[0]), code_keep(r[1]), code_keep(r[2]), esc(src)))
    cap = re.search(r'<p class="table-caption">(.*?)</p>', body, re.S)
    PARAMS[sid] = (name, ver, rows, code_keep(cap.group(1)) if cap else "")

# ---------------------------------------------------------------- 组件
def table(head, rows, cls=""):
    h = "".join("<th>%s</th>" % x for x in head)
    b = "\n".join("<tr>%s</tr>" % "".join(r) for r in rows)
    return '<div class="tablewrap"><table%s>\n<tr>%s</tr>\n%s\n</table></div>' % (
        ' class="%s"' % cls if cls else "", h, b)


def td(x, cls=""):
    return "<td%s>%s</td>" % (' class="%s"' % cls if cls else "", x)


# ---------------------------------------------------------------- 一、怎么读
VERSIONS = [
    ("Codex", "源码 <code>76ed3b4</code>（main）；CLI <code>0.165.0</code>", "读源码，加本机假服务器实验（第 2–12 章）"),
    ("Claude Code", "官方文档 <code>code.claude.com/docs</code>，2026-11-02 抓取；第三版读的是非官方源码 v2.1.88（<code>988438a</code>）", "读官方文档，没抓过请求"),
    ("pi", "<code>b45e0eb</code>（main）", "第三版读源码；本版没有这份源码，没核对"),
    ("oh-my-pi", "<code>f979f46</code>（main），pi 的 fork", "同上"),
    ("opencode v1", "tag <code>v1.19.0</code>（<code>733b2c6</code>）", "同上"),
    ("opencode v2", "tag <code>v2.0.29</code>（beta，<code>042d083</code>）", "同上"),
    ("Grok Build", "<code>2bdd1d6</code>；SOURCE_REV <code>559751f</code>，无 tag", "同上"),
    ("DeepSeek Harness", "<code>5719020</code>（master）", "同上；其中一部分是第三版从同仓文档推出来的"),
]

s1 = """<section id="s1">
<h2><span class="sn">一、</span>怎么读这份附录</h2>
<p>每个格子都带一个依据标签，先看标签再看内容。</p>
%s
<p>第三版里关于 Codex 的几处说法，在本版核对时被实验推翻（子代理缺省带不带父的历史、有没有回退入口、记忆的实现）。别的 agent 的格子是同一种读法记下的，当线索用，别当结论。</p>
<h3>八个 agent 的版本和本版怎么查的</h3>
%s
<p class="note">版本是第三版记下的快照（核实日期 2026-10-18）；Codex 的 <code>76ed3b4</code> 本版也在用。pi、oh-my-pi、opencode、Grok Build、DeepSeek Harness 只在这份附录出场，正文各章没写它们。</p>
</section>""" % (
    table(["标签", "意思"], [
        [td(tag("h")), td("本版读了源码，并且做过实验（假服务器抓请求或读存档）。")],
        [td(tag("m")), td("读了源码或官方文档，没做实验；缺什么写在格子里。Claude Code 一列的「中」都是官方文档，没抓过请求。")],
        [td(tag("l")), td("第三版 2026-10-18 的记录，本版没核对。Claude Code 的这类格子来自非官方源码 v2.1.88。")],
    ]),
    table(["agent", "版本", "本版的依据"], [[td(a, "nm"), td(v), td(w)] for a, v, w in VERSIONS]),
)

# ---------------------------------------------------------------- 二、总表
CAT_SECTION = []
for pos, i in enumerate(ORDER, 1):
    name, ask, nums = CATS[i]
    where = ("本版：" + chs(nums)) if nums else "本版没有单独写"
    rows = []
    for a, agent in enumerate(AGENTS):
        text, flag = MATRIX[i][a]
        if a == 0 and i in CODEX:
            t, lv, cn = CODEX[i]
            cell = [td(agent, "nm"), td(t), td(tag(lv) + " " + chs(cn), "ev")]
            cls = "me"
        elif a == 1 and i in CLAUDE:
            t, lv, cn = CLAUDE[i]
            cell = [td(agent, "nm"), td(t), td(tag(lv) + " 官方文档 " + chs(cn), "ev")]
            cls = ""
        else:
            note = ""
            if flag != "已核实":
                note = '<span class="sub">第三版就标了「%s」</span>' % esc(flag)
            if a == 1:
                note += '<span class="sub">来源：非官方源码 v2.1.88</span>'
            cell = [td(agent, "nm"), td(esc(text)), td(tag("l") + note, "ev")]
            cls = ""
        rows.append('<tr%s>%s</tr>' % (' class="%s"' % cls if cls else "", "".join(cell)))
    h = '<div class="tablewrap"><table class="mx">\n<tr><th>agent</th><th>做法</th><th>依据</th></tr>\n%s\n</table></div>' % "\n".join(rows)
    CAT_SECTION.append('<h3>%s</h3>\n<p class="meta">%s · %s</p>\n%s' % (name, ask, where, h))

s2 = """<section id="s2">
<h2><span class="sn">二、</span>对照总表：16 类做法 × 8 个 agent</h2>
<p>先 Codex（底色加深），再 Claude Code，后面六个按 pi、oh-my-pi、opencode v1、opencode v2、Grok Build、DeepSeek Harness 排。类按本版章节的顺序排；表里的阈值是各自快照里的值，换了版本可能变。</p>
%s
</section>""" % "\n".join(CAT_SECTION)

# ---------------------------------------------------------------- 三、参数
cx_rows = []
for k, where, dflt, role, nums, lv in CODEX_PARAMS:
    cx_rows.append([td(k), td(where), td(dflt), td(role), td(tag(lv) + " " + chs(nums), "ev")])
fx_rows = [[td(n, "nm"), td(w), td(tag(lv) + " " + chs(nums), "ev")] for n, w, nums, lv in CODEX_FIXED]
cc_rows = [[td(k), td(v), td(w), td(tag("m") + " " + chs(nums), "ev")] for k, v, w, nums in CLAUDE_PARAMS]
cf_rows = [[td(a), td(b), td(c), td(d)] for a, b, c, d in CLAUDE_CONFLICTS]

OTHER = [("params-pi", "pi"), ("params-omp", "oh-my-pi"), ("params-opencode-v1", "opencode v1"),
         ("params-opencode-v2", "opencode v2"), ("params-grok", "Grok Build"), ("params-dsh", "DeepSeek Harness")]
other_html = []
for sid, label in OTHER:
    name, ver, rows, cap = PARAMS[sid]
    t = table(["参数", "缺省", "作用", "第三版给的出处"], [[td(a), td(b), td(c), td("<code>%s</code>" % d)] for a, b, c, d in rows])
    other_html.append("<h3>%s</h3>\n<p class=\"meta\">%s</p>\n%s%s" % (
        label, esc(ver), t, ('<p class="note">%s</p>' % cap) if cap else ""))

s3 = """<section id="s3">
<h2><span class="sn">三、</span>参数</h2>
<p>「缺省」是没配置时的值，不是推荐值。Codex 一列写清每项写在哪个文件里；Claude Code 是官方文档里的值；其余六个 agent 的参数整张表都是第三版的记录，本版没核对。</p>

<h3>Codex：能配置的</h3>
<p class="meta">条目名和缺省值 2026-11-02 在源码 <code>76ed3b4</code> 里逐个搜过（<code>config/src/config_toml.rs</code>、<code>config/src/types.rs</code>、<code>core/src/config/mod.rs</code>、<code>config/src/mcp_types.rs</code>、<code>model-provider-info/src/lib.rs</code>）。<code>config.toml</code> 指 <code>~/.codex/config.toml</code>，也可以在命令行用 <code>-c 名=值</code> 临时覆盖（第 11 章只验证了命令跑得完）。</p>
%s

<h3>Codex：写死的数</h3>
<p class="meta">改不了配置，只能换版本。</p>
%s

<h3>Claude Code：官方文档里的值</h3>
<p class="meta">官方文档 <code>code.claude.com/docs</code>，2026-11-02 抓取，页面里最新版本号 v2.1.309。都没做实验。</p>
%s
<h3>Claude Code：非官方源码和官方文档对不上的四处</h3>
<p class="meta">第三版读的是非官方源码 v2.1.88，下面是它和官方文档不一致的地方。本版正文只用官方文档的值。</p>
%s

<h3>其余六个 agent</h3>
<p class="note"><span class="tag lvl-l">待核实</span> 下面六张表整张都来自第三版（2026-10-18 读源码），出处是第三版给的文件和行号；本版没有这些源码，没核对。Grok Build 没有语义化版本号，表里的缺省只对那个快照成立。</p>
%s
</section>""" % (
    table(["配置项", "写在哪", "缺省", "作用", "依据"], cx_rows),
    table(["数", "是什么", "依据"], fx_rows),
    table(["参数", "值", "补充", "依据"], cc_rows),
    table(["项目", "非官方源码 v2.1.88", "官方文档", "本版怎么处理"], cf_rows),
    "\n".join(other_html),
)

# ---------------------------------------------------------------- 四、术语
term_html = []
n_terms = 0
for group, items in TERMS:
    rows = []
    for zh, en, defn, first in items:
        rows.append([td(zh, "nm"), td(en), td(defn), td(first)])
        n_terms += 1
    term_html.append("<h3>%s</h3>\n%s" % (group, table(["术语", "英文或代码名", "一句话", "首次讲解"], rows)))
o_rows = [[td(zh, "nm"), td(en), td(d), td(tag("l"), "ev")] for zh, en, d in OTHER_TERMS]
cf_rows2 = [[td(w, "nm"), td(d), td(chs(nums), "ev")] for w, d, nums in CONFUSABLE]

s4 = """<section id="s4">
<h2><span class="sn">四、</span>术语</h2>
<p>只收本版正文用到的词，按章节顺序排，一个词只在「首次讲解」那一章讲透。第 1 章（token、窗口）还没写，那几条先指到用到它的章。</p>
%s
<h3>其他 agent 的专有名词</h3>
<p class="meta">上面的格子里出现过这些词。它们都来自第三版的记录，本版没核对。</p>
%s
<h3>容易混的几组</h3>
%s
</section>""" % (
    "\n".join(term_html),
    table(["词", "英文名", "一句话", "依据"], o_rows),
    table(["词", "区别", "首次讲解"], cf_rows2),
)

# ---------------------------------------------------------------- 五、源码索引
idx_rows = []
for c, topic, path, rng, kw in ITEMS:
    idx_rows.append([td(ch(c), "nm"), td(esc(topic)), td("<code>%s:%s</code>" % (path, rng))])

s5 = """<section id="s5">
<h2><span class="sn">五、</span>Codex 源码索引</h2>
<p>想自己看源码，从这里下手。路径相对 <code>codex-rs/</code>，提交 <code>76ed3b4</code>；每条对应一章里的某个结论，按章排。共 %d 条。</p>
%s
</section>""" % (len(ITEMS), table(["章", "看什么", "文件:行"], idx_rows))

# ---------------------------------------------------------------- 证据说明
s6 = """<section id="evidence">
<h2>证据说明</h2>
<ul>
<li><b>总表里 Codex 和 Claude Code 两列</b>：每个结论的出处和等级在对应章的证据表里，格子「依据」一栏的章号可以点进去。总表只是把各章的结论按类摆在一起，没有新实验。</li>
<li><b>总表里其余六个 agent</b>：整格取自第三版总表（2026-10-18），程序解析搬运，没改写；第三版标「推断」的格子保留了这个标注。本机没有这些源码，全部是待核实。</li>
<li><b>Codex 参数表</b>：配置项名、缺省值在源码里逐个搜到。其中有两项各章没写、是编这份附录时新读到的，只读了源码没做实验：V1 子代理的 <code>max_threads</code> 缺省 6（<code>core/src/config/mod.rs:255</code>、<code>1677</code>）；<code>min_rate_limit_remaining_percent</code> 缺省 25（<code>config/src/types.rs:58</code>）。</li>
<li><b>源码索引</b>：2026-11-02 用脚本逐条核对了：文件存在、行号没有超出文件长度，起始行看过、和「看什么」对得上。没有逐行读每一段。第 2 章证据表里个别行号写的是文件名缩写（如 <code>agents_md.rs</code>），这里换成了完整路径。</li>
<li><b>术语表</b>：定义取自各章正文和证据表；没有新的事实。「token」「上下文窗口」两条的首次讲解指向第 1 章，第 1 章还没写。</li>
</ul>
</section>"""

# ---------------------------------------------------------------- 整页
PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>对照表和索引</title>
<link rel="stylesheet" href="assets/book.css">
<script src="assets/book.js"></script>
<style>
/* 本页专用：总表和参数表的列宽、Codex 行的底色 */
.mx td.nm,td.nm{white-space:nowrap;font-weight:600}
.mx td.ev,td.ev{white-space:nowrap;font-size:.82rem}
.mx td.ev .sub{display:block;font-size:.76rem;color:var(--muted);white-space:normal}
.mx tr.me td{background:var(--note-bg)}
.page h3{scroll-margin-top:16px}
</style>
</head>
<body class="chapter">
<main class="page">

<header class="chap-head">
<p class="kicker">附录</p>
<h1>附录：8 个 agent 的做法和参数、术语、Codex 源码行号</h1>
<p class="meta">2026-11-02 · Codex 源码 <code>76ed3b4</code> / CLI <code>0.165.0</code> · Claude Code 官方文档 2026-11-02 抓取 · 其余六个 agent：第三版 2026-10-18 的源码记录，未核对</p>
</header>

<p class="lede">这是查表用的附录，不用从头读。四张表：16 类上下文做法 × 8 个 agent、各家参数、术语、Codex 源码行号。每个结论都标了依据：本版核对过的，还是旧记录里的、本版没核对。</p>
<p class="note">本版有源码的只有 Codex，有官方文档的只有 Claude Code。其余六个 agent（pi、oh-my-pi、opencode v1 和 v2、Grok Build、DeepSeek Harness）的内容全部来自第三版，标【待核实】。</p>

%s
%s
%s
%s
%s
%s

</main>
</body>
</html>
""" % (s1, s2, s3, s4, s5, s6)

open(OUT, "w", encoding="utf-8").write(PAGE)
print("wrote", OUT, len(PAGE), "bytes;", "terms:", n_terms, "index:", len(ITEMS))
