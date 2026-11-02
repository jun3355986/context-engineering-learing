import sys,os
sys.path.insert(0,os.path.dirname(__file__))
from index_items import ITEMS
SRC="/home/ubuntu/work/codex-76ed3b4/codex-rs"
bad=0
for ch,topic,path,rng,kw in ITEMS:
    f=os.path.join(SRC,path)
    if not os.path.isfile(f): print("MISSING",path); bad+=1; continue
    L=open(f,encoding="utf-8",errors="replace").read().split("\n")
    a,b=(rng.split("-")+[rng])[:2] if "-" in rng else (rng,rng)
    a,b=int(a),int(b)
    if b>len(L): print("OOR",path,rng,len(L)); bad+=1; continue
    seg=[l.strip() for l in L[a-1:b] if l.strip()]
    first=seg[0][:70] if seg else ""
    flag=""
    if kw and not any(kw in l for l in L[max(0,a-4):b+3]): flag=" <<< kw '%s' not near"%kw; bad+=1
    print(f"{ch:>2} {path}:{rng} | {first}{flag}")
print("bad",bad)
