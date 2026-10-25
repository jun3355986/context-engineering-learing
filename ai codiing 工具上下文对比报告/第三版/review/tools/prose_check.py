#!/usr/bin/env python3
"""教程修订自检脚本。只读，不改任何页面。

用法（在「第三版」目录下运行；页面 id 写 main-13、intro-07，导读写 index）：

  python3 -I review/tools/prose_check.py text  main-13            抽出正文纯文本（不含弹窗、代码、SVG）
  python3 -I review/tools/prose_check.py text  main-13 --modals   只抽弹窗正文
  python3 -I review/tools/prose_check.py scan  [id ...]           每页各类可疑措辞计数（不写 id = 全站）
  python3 -I review/tools/prose_check.py hits  直译词 [id ...]     列出命中的句子；类别名见 PATTERNS 和 QUERIES，也可直接写正则
  python3 -I review/tools/prose_check.py terms main-13            行话第一次出现的位置，用来检查有没有白话解释
  python3 -I review/tools/prose_check.py time  main-13            按 CONVENTIONS 公式算阅读时长，并和页头对比
  python3 -I review/tools/prose_check.py check main-13            标签配对、h1 个数、重复 id
  python3 -I review/tools/prose_check.py hedge main-13 [--base 提交]  限定语密度和改前比，并列出新增的限定句（默认和 HEAD 比）

命中不等于错误：脚本只负责把可疑的地方找出来，改不改由人判断。
"""
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
TUTORIAL = os.path.normpath(os.path.join(HERE, "..", "..", "tutorial"))
PAGES = os.path.join(TUTORIAL, "pages")

SKIP = {"pre", "svg", "script", "style"}
BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "td", "th", "figcaption", "dd", "dt", "summary"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "source", "track", "wbr", "path", "rect", "circle", "line", "polyline",
        "polygon", "ellipse", "use", "stop"}
HAN = re.compile(r"[一-鿿]")

# 可疑措辞。来源：作者在 docs/上下文教程修订.md 标出的句子、第 4–6 章修订时发现的问题。
PATTERNS = {
    "直译词": r"形状|旋钮|杠杆|爆炸半径|复利|买单|买到|买[“「]|一等公民|甜点|甜区|表面积|心智模型|第一性|有哪些手|最粗|活在|住在|坐在|到场|按什么顺序说话|默认面|钉住|钉死",
    # 「模型以为……」用来说明「模型拿不到某条信息」，通常没问题，不算在内
    "拟人": r"(?:模型|agent|Agent|它)[^，。；：]{0,5}?(?:觉得|热情|擅长|怀疑自己|想要|希望|愿意|喜欢|讨厌|害怕|担心)",
    "口头禅": r"本质上|本质是|真正|关键在于|值得注意的是|换句话说|说到底|归根结底|这意味着",
    "翻案腔": r"不是[^。！？；]{1,40}?而是",
    "直译标签": r"没有傻问题|收口",
    "粗俗口语": r"擦屁股|背锅|甩锅",
    "工序泄漏": r"Karpathy|第 ?[1-4] ?级（|受控中文|输出级别|样章|任务票",
    "破折号": r"——",
}

# 限定语：核查型改写最容易堆出来的句式，如「不能据此推定」「仍取决于」「不一定」。
# 第 20 章第一轮 GPT 改写后，这类句子从每千字 0.9 处涨到 7.3 处。合理的限定也会被数进来，要逐条判断。
HEDGE = (r"不能(?:据此|单凭|仅凭|只凭|直接|一概|笼统|由|推定|认定|推出|推导|推广|代替|保证|证明|当作|视为|硬分)"
         r"|不等于|不一定|未必|并非|不足以|无法(?:据此|单独|证明)|不意味着|不代表"
         r"|仍(?:需|要|须|取决于|可能|依赖|有待)|取决于|有机会|(?:只|仅)(?:代表|限于)|为限|以[^，。；]{1,12}为准")
PATTERNS["限定语"] = HEDGE
HEDGE_ALLOWANCE = 1.0  # 每千字最多比改前多几处

# 只给 hits 用的查询（不进 scan 的统计列）：核对跨章口径时用
QUERIES = {
    "动作口径": r"新会话|另开|清空|/clear|/new|回退|/rewind",
    "成本口径": r"回本|净亏|摊薄|失效.{0,6}(?:贵|成本|代价)|(?:贵|成本|代价).{0,8}失效",
    "绝对化": r"一定|总是|必然|永远|定律|从来",
}

# 行话：入门读者第一次见到时需要一句白话。按出现先后检查，不要求每个都解释，只要求第一次出现时读得懂。
TERMS = ["采样", "前缀", "失效点", "断点", "切点", "摘要", "裁剪", "投影", "落盘", "指针",
         "占位符", "增量", "差分", "delta", "序列化", "反序列化", "rollout", "检查点", "快照",
         "回放", "重放", "分叉", "叶子", "墓碑", "游标", "水位", "滞回", "驱逐", "熔断",
         "回边", "KV", "surface", "epoch", "seq", "due", "护栏", "打点", "tokenizer"]


class Extract(HTMLParser):
    """按块收集文本。mode='article' 只收 <article> 内、弹窗外；mode='modals' 只收弹窗。"""

    def __init__(self, mode="article"):
        super().__init__(convert_charrefs=True)
        self.mode = mode
        self.in_article = 0
        self.skip = 0
        self.modal = 0
        self.stack = []
        self.buf = []
        self.blocks = []
        self.tag = None

    def _want(self):
        if self.skip:
            return False
        if self.mode == "modals":
            return self.modal > 0
        return self.in_article > 0 and self.modal == 0

    def handle_starttag(self, tag, attrs):
        cls = (dict(attrs).get("class") or "").split()
        if tag == "article":
            self.in_article += 1
        if tag in SKIP:
            self.skip += 1
        if tag == "div":
            is_modal = "modal" in cls
            self.stack.append(is_modal)
            if is_modal:
                self.modal += 1
        if tag in BLOCK:
            self.flush()
            self.tag = tag

    def handle_endtag(self, tag):
        if tag in BLOCK:
            self.flush()
        if tag == "article":
            self.flush()
            self.in_article -= 1
        if tag in SKIP:
            self.skip -= 1
        if tag == "div" and self.stack:
            if self.stack.pop():
                self.modal -= 1

    def handle_data(self, data):
        if self._want():
            self.buf.append(data)

    def flush(self):
        text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        if text:
            self.blocks.append((self.tag or "?", text))
        self.buf = []
        self.tag = None


def path_of(pid):
    if pid in ("index", "intro-00"):
        return os.path.join(TUTORIAL, "index.html")
    if pid.endswith(".html") and os.path.exists(pid):
        return pid
    return os.path.join(PAGES, pid + ".html")


def all_ids():
    ids = ["index"]
    ids += sorted(f[:-5] for f in os.listdir(PAGES) if f.endswith(".html"))
    return ids


def blocks(pid, mode="article", html=None):
    p = Extract(mode)
    p.feed(html if html is not None else open(path_of(pid), encoding="utf-8").read())
    p.flush()
    return p.blocks


def prose(pid, with_modals=True, html=None):
    out = [t for _, t in blocks(pid, html=html)]
    if with_modals:
        out += [t for _, t in blocks(pid, "modals", html=html)]
    return out


def html_at(pid, rev):
    """取某个 git 提交里的页面原文。"""
    folder, name = os.path.split(os.path.abspath(path_of(pid)))
    r = subprocess.run(["git", "-C", folder, "show", f"{rev}:./{name}"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"取不到 {rev} 里的 {name}：{r.stderr.strip()}")
    return r.stdout


def cmd_text(args):
    mode = "modals" if "--modals" in args else "article"
    for tag, t in blocks(args[0], mode):
        print(f"[{tag}] {t}")


def cmd_scan(args):
    ids = args or all_ids()
    keys = list(PATTERNS) + ["长句>60", "引号混用"]
    print("页面\t汉字\t" + "\t".join(keys))
    total = {k: 0 for k in keys}
    for pid in ids:
        text = "\n".join(prose(pid))
        row = [pid, str(len(HAN.findall(text)))]
        for k, pat in PATTERNS.items():
            n = len(re.findall(pat, text))
            total[k] += n
            row.append(str(n))
        long_n = sum(1 for s in re.split(r"[。！？]", text) if len(HAN.findall(s)) > 60)
        mixed = int("“" in text and "「" in text)
        total["长句>60"] += long_n
        total["引号混用"] += mixed
        row += [str(long_n), "是" if mixed else ""]
        print("\t".join(row))
    if len(ids) > 1:
        print("合计\t\t" + "\t".join(str(total[k]) for k in keys))


def cmd_hits(args):
    pat = PATTERNS.get(args[0]) or QUERIES.get(args[0]) or args[0]
    for pid in args[1:] or all_ids():
        for src, mode in (("正文", "article"), ("弹窗", "modals")):
            for tag, t in blocks(pid, mode):
                for m in re.finditer(pat, t):
                    s, e = max(0, m.start() - 30), min(len(t), m.end() + 30)
                    print(f"{pid}\t{src}[{tag}]\t…{t[s:e]}…")


def cmd_terms(args):
    pid = args[0]
    text = "\n".join(prose(pid))
    found = []
    for term in TERMS:
        pat = re.escape(term) if re.match(r"[一-鿿]", term) else r"(?<![A-Za-z_])" + re.escape(term) + r"(?![A-Za-z_])"
        m = re.search(pat, text)
        if m:
            found.append((m.start(), term, len(re.findall(pat, text))))
    for pos, term, n in sorted(found):
        s, e = max(0, pos - 40), min(len(text), pos + 60)
        snippet = text[s:e].replace("\n", " ⏎ ")
        print(f"{term}（{n} 次）\t…{snippet}…")


def cmd_time(args):
    for pid in args or all_ids():
        if pid == "index":
            continue
        html = open(path_of(pid), encoding="utf-8").read()
        art = re.search(r"<article[\s\S]*?</article>", html)
        art = art.group(0) if art else ""
        han = sum(len(HAN.findall(t)) for t in prose(pid, with_modals=False))
        figs = len(re.findall(r"<figure\b", art))
        demos = len(re.findall(r'class="demo"', art))
        codes = len(re.findall(r'class="codeblock"', art))
        minutes = max(1, round(han / 300 + figs * 0.5 + demos * 2 + codes))
        meta = re.search(r"约 ?(\d+) ?分钟", html)
        stated = int(meta.group(1)) if meta else None
        flag = "" if stated == minutes else "  ← 不一致"
        print(f"{pid}\t正文 {han} 字 / 图 {figs} / 演示 {demos} / 代码块 {codes} → {minutes} 分钟；页头写 {stated}{flag}")


def hedge_sentences(pid, html=None):
    """按句切开正文和弹窗，返回 (来源, 句子) 列表。"""
    out = []
    for src, mode in (("正文", "article"), ("弹窗", "modals")):
        for _, t in blocks(pid, mode, html=html):
            out += [(src, s.strip()) for s in re.split(r"(?<=[。！？；])", t) if s.strip()]
    return out


def hedge_rate(sents):
    text = "\n".join(s for _, s in sents)
    han = len(HAN.findall(text))
    n = len(re.findall(HEDGE, text))
    return n, n * 1000 / max(han, 1)


def cmd_hedge(args):
    base = "HEAD"
    if "--base" in args:
        i = args.index("--base")
        base, args = args[i + 1], args[:i] + args[i + 2:]
    for pid in args:
        now, old = hedge_sentences(pid), hedge_sentences(pid, html_at(pid, base))
        (n_now, r_now), (n_old, r_old) = hedge_rate(now), hedge_rate(old)
        limit = r_old + HEDGE_ALLOWANCE
        verdict = "通过" if r_now <= limit else "超出：逐条处理下面的句子"
        print(f"{pid}  限定语 改前（{base}）{n_old} 处，每千字 {r_old:.1f} → 现在 {n_now} 处，每千字 {r_now:.1f}；"
              f"上限 {limit:.1f}  {verdict}")
        before = {s for _, s in old}
        fresh = [(src, s) for src, s in now if s not in before and re.search(HEDGE, s)]
        if fresh:
            print(f"新增或改写过、含限定语的句子（{len(fresh)} 句）。每句要么写明依据和它纠正的误解，要么删掉限定：")
        for src, s in fresh:
            print(f"  {src}｜" + re.sub(HEDGE, lambda m: f"【{m.group(0)}】", s))


class Balance(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.ids, self.h1 = [], [], {}, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if a.get("id"):
            self.ids[a["id"]] = self.ids.get(a["id"], 0) + 1
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids[a["id"]] = self.ids.get(a["id"], 0) + 1

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for t, line in self.stack[i + 1:]:
                    self.errors.append(f"第 {line} 行 <{t}> 没有闭合")
                del self.stack[i:]
                return
        self.errors.append(f"第 {self.getpos()[0]} 行多出 </{tag}>")


def cmd_check(args):
    bad = 0
    for pid in args or all_ids():
        b = Balance()
        b.feed(open(path_of(pid), encoding="utf-8").read())
        problems = list(b.errors)
        problems += [f"<{t}> 到文件末尾都没闭合（第 {line} 行）" for t, line in b.stack if t not in ("html", "body", "head")]
        if b.h1 != 1:
            problems.append(f"h1 有 {b.h1} 个，应为 1 个")
        problems += [f"id 重复：{k} × {v}" for k, v in b.ids.items() if v > 1]
        if problems:
            bad += 1
            print(f"{pid}：")
            for p in problems[:20]:
                print("  " + p)
        else:
            print(f"{pid}：通过")
    sys.exit(1 if bad else 0)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("text", "scan", "hits", "terms", "time", "check", "hedge"):
        print(__doc__)
        sys.exit(2)
    cmd, args = sys.argv[1], sys.argv[2:]
    {"text": cmd_text, "scan": cmd_scan, "hits": cmd_hits, "terms": cmd_terms,
     "time": cmd_time, "check": cmd_check, "hedge": cmd_hedge}[cmd](args)


if __name__ == "__main__":
    main()
