"""text sample sheet from the shaped runs: upright above italic, Light and Bold, solid fills"""
import os, sys, json, skia
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from sheets import Sheet, INK, DIM, UP_C, IT_C, col
PILOT = os.path.dirname(HERE)
D = json.load(open(os.path.join(PILOT, "work", "text_shaped.json")))

def gpath(ops, x0, y0, s):
    p = skia.Path()
    X = lambda q: (x0 + q[0] * s, y0 - q[1] * s)
    for op in ops:
        if op[0] == "M": p.moveTo(*X(op[1]))
        elif op[0] == "L": p.lineTo(*X(op[1]))
        elif op[0] == "C": p.cubicTo(*X(op[1]), *X(op[2]), *X(op[3]))
        elif op[0] == "Q": p.quadTo(*X(op[1]), *X(op[2]))
        else: p.close()
    return p

for master in ("Light", "Bold"):
    for li, tag in ((0, "bangla"), (1, "latin")):
        s = 0.078 if li == 0 else 0.082
        Wd = int(max(D[k]["lines"][li]["advance"] for k in D) * s + 120)
        sh = Sheet(Wd, 560)
        sh.header("HIND SILIGURI", master + " / " + master + " Italic", "text sample shaped with HarfBuzz from fontmake TTFs · upright above, italic below (14.04°, corrected)")
        for r, (nm, c) in enumerate(((master, UP_C), (master + " Italic", IT_C))):
            y = 300 + r * 200
            sh.text(40, y - 140, nm, c, 18)
            F = D[nm]
            for gn, x, dy in F["lines"][li]["items"]:
                sh.c.drawPath(gpath(F["glyphs"][gn], 60 + x * s, y - dy * s, s), skia.Paint(Color=col(c), AntiAlias=True))
        print(sh.save(os.path.join(PILOT, "sheets", "text_%s_%s.png" % (tag, master))))
