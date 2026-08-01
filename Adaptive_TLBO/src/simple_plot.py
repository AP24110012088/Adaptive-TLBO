"""Small Pillow-backed plotting fallback for environments without matplotlib."""
from PIL import Image, ImageDraw

class _Style:
    def use(self, *_): pass
class Axis:
    def __init__(self): self.items=[]; self.labels={}
    def plot(self, x, y, **kw): self.items.append(("line", list(x), list(y), kw))
    def bar(self, x, y, **kw): self.items.append(("bar", list(x), list(y), kw))
    def boxplot(self, groups, **kw): self.items.append(("box", [list(g) for g in groups], [], kw))
    def set(self, **kw): self.labels.update(kw)
    def legend(self, **kw): pass
    def tick_params(self, **kw): pass
class Figure:
    def __init__(self, axis, size): self.axis=axis; self.size=size
    def savefig(self, path, dpi=300):
        w,h=1200,700; im=Image.new("RGB",(w,h),"white"); d=ImageDraw.Draw(im)
        d.rectangle((95,55,w-45,h-100),outline="#9aa5b1",width=2)
        d.text((95,18),str(self.axis.labels.get("title","Performance chart")),fill="#17365D")
        vals=[]
        for kind,x,y,kw in self.axis.items:
            if kind in ("line","bar"): vals += [float(v) for v in y]
            elif kind=="box": vals += [float(v) for group in x for v in group]
        lo=min(vals) if vals else 0; hi=max(vals) if vals else 1
        if hi<=lo: hi=lo+1
        def sy(v): return h-100-int((float(v)-lo)/(hi-lo)*(h-170))
        colors=["#4E79A7","#59A14F","#E15759","#8C8C8C","#A61C1C"]
        for j,(kind,x,y,kw) in enumerate(self.axis.items):
            color=kw.get("color",colors[j%len(colors)])
            if isinstance(color, (list, tuple)):
                color = color[j % len(color)]
            if kind=="line":
                n=max(1,len(y)-1); pts=[(95+int(i/n*(w-140)),sy(v)) for i,v in enumerate(y)]
                if len(pts)>1: d.line(pts,fill=color,width=max(1,int(kw.get("linewidth",2))))
            elif kind=="bar":
                n=max(1,len(y)); bw=max(14,(w-160)//n//2)
                for i,v in enumerate(y):
                    cx=120+int(i*(w-180)/n); d.rectangle((cx-bw,sy(v),cx+bw,h-100),fill=color)
                    d.text((cx-bw, h-85),str(x[i])[:16],fill="#333333")
            else:
                groups=x; n=max(1,len(groups));
                for i,g in enumerate(groups):
                    if not g: continue
                    cx=120+int(i*(w-180)/n); a,b=min(g),max(g); d.rectangle((cx-18,sy(b),cx+18,sy(a)),outline=color,width=2); d.line((cx,sy(a),cx,sy(b)),fill=color,width=2)
        d.text((100,h-55),str(self.axis.labels.get("xlabel","")),fill="#333333")
        d.text((w-260,h-55),str(self.axis.labels.get("ylabel","")),fill="#333333")
        im.save(path,"PNG")
style=_Style()
def subplots(figsize=(8,4.5), constrained_layout=True):
    a=Axis(); return Figure(a,figsize),a
def close(*_): pass