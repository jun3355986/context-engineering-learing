import re,sys,os
from html.parser import HTMLParser
F=sys.argv[1]; D=os.path.dirname(F)
t=open(F,encoding="utf-8").read()
VOID={"meta","link","br","hr","img","input"}
class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.st=[]; s.err=[]; s.ids=set(); s.hrefs=[]; s.cls=set(); s.line=1
    def handle_starttag(s,tag,attrs):
        a=dict(attrs)
        if "id" in a: s.ids.add(a["id"])
        if "href" in a: s.hrefs.append(a["href"])
        for c in (a.get("class") or "").split(): s.cls.add(c)
        if tag not in VOID: s.st.append((tag,s.getpos()))
    def handle_endtag(s,tag):
        if tag in VOID: return
        if not s.st: s.err.append(("extra close",tag,s.getpos())); return
        if s.st[-1][0]==tag: s.st.pop()
        else:
            s.err.append(("mismatch",tag,s.st[-1],s.getpos()))
            # try recover
            for i in range(len(s.st)-1,-1,-1):
                if s.st[i][0]==tag: del s.st[i:]; break
p=P(); p.feed(t)
print("tag errors:",p.err[:5],"unclosed:",p.st[:5])
# anchors
bad=[h for h in p.hrefs if h.startswith("#") and h[1:] not in p.ids]
print("bad anchors:",bad)
files=[h.split("#")[0] for h in p.hrefs if not h.startswith("#") and not h.startswith("http")]
print("missing files:",[f for f in set(files) if f and not os.path.exists(os.path.join(D,f))])
css=open(os.path.join(D,"assets/book.css"),encoding="utf-8").read()+ "".join(re.findall(r"<style>(.*?)</style>",t,re.S))
known=set(re.findall(r"\.([A-Za-z][\w-]*)",css))
print("unknown classes:",sorted(c for c in p.cls if c not in known))
# words
txt=re.sub(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>","",t,flags=re.S)
for w in ["默认","普通","更小","更多","一些","只差","已核实"]:
    c=txt.count(w)
    if c: print("word",w,c)
dup=[i for i in re.findall(r'id="([^"]+)"',t)]
print("dup ids:",[i for i in set(dup) if dup.count(i)>1])
print("h2:",len(re.findall("<h2",t)),"h3:",len(re.findall("<h3",t)),"tables:",t.count("<table"))
# bracket balance in visible text
for a,b in ["()","（）","「」","[]"]:
    print(a+b,txt.count(a),txt.count(b))
