"""Round 5 · pass 2: the e tail source fix, checked (sheets/e_tail_fix.png): the Regular e before (31 nodes, the bow-tie
1-2) / after (29 nodes) / the compiled Geist Serif Regular (font-proofer/src/fonts, read only), tail x3 solid, and the
corrected e (pass 2c) at 18.43 deg before / after."""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
from proof5s import Sheet, INK, DIM
from comb_p2 import comb

TTF = "/Users/Mark/Documents/Github/font-proofer/src/fonts/GeistSerif-Regular.ttf"
OLD = os.path.join(C.R5, "src", "geistserif_italic_18.pre-efix.json"); NEW = os.path.join(C.R5, "src", "geistserif_italic_18.json")


def ttf_e():
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import RecordingPen
    f = TTFont(TTF); gs = f.getGlyphSet(); name = f.getBestCmap()[ord("e")]
    pen = RecordingPen(); gs[name].draw(pen)
    out = []; cur = []
    for op, args in pen.value:
        if op == "moveTo":
            cur = [[*args[0], "l", False]]
        elif op == "lineTo":
            cur.append([*args[0], "l", False])
        elif op == "qCurveTo":
            p0 = np.array(cur[-1][:2], float); pts = [np.array(a, float) for a in args]
            # split the quadratic spline into implied on-curve points, each quad raised to a cubic
            ons = []
            for i in range(len(pts) - 1):
                if i < len(pts) - 2:
                    ons.append((pts[i], (pts[i] + pts[i + 1]) / 2))
                else:
                    ons.append((pts[i], pts[i + 1]))
            for q, e in ons:
                c1 = p0 + 2 / 3 * (q - p0); c2 = e + 2 / 3 * (q - e)
                cur += [[*c1, "o", False], [*c2, "o", False], [*e, "c", False]]; p0 = e
        elif op == "curveTo":
            cur += [[*args[0], "o", False], [*args[1], "o", False], [*args[2], "c", False]]
        elif op in ("closePath", "endPath"):
            if len(cur) > 1 and np.allclose(cur[0][:2], cur[-1][:2]):
                cur.pop()
            out.append({"closed": True, "nodes": cur}); cur = []
    return out


def main():
    O, N = json.load(open(OLD)), json.load(open(NEW))
    V = [("before: Regular e, 31 nodes (bow-tie 1–2)", O["GeistSerifRegular_e"]["contours"], (240, 72, 58)),
         ("after: Regular e, 29 nodes", N["GeistSerifRegular_e"]["contours"], (90, 222, 118)),
         ("compiled GeistSerif-Regular.ttf (font-proofer)", ttf_e(), (80, 200, 235))]
    I = [("pass 2c e, 18.43°, before the fix", O["GeistSerifItalicPass2c_e"]["contours"], (240, 72, 58)),
         ("pass 2c e, 18.43°, after the fix", N["GeistSerifItalicPass2c_e"]["contours"], (90, 222, 118))]
    W, H = 2440, 1560
    sh = Sheet(W, H)
    sh.title("/e  ·  the tail terminal, source fix  ·  round 5 · pass 2", "Regular  ·  and the 18.43° italic",
             "the Regular e's tail held a bow-tie (nodes 1 and 2 crossing the cut): deleted; nothing else moved. Tail zoomed ×3, SOLID; the whole e small at the left of each.")
    sh.key(26, 122, [(nm, col) for nm, _, col in V], 17)
    for k, (nm, cs, col) in enumerate(V):
        x0 = 20 + k * 805
        pw = sh.panel(x0, 170, 260, 330, (-20, -30, 560, 580), pad=4); pw.frame(); pw.fill(cs, col)
        pz = sh.panel(x0 + 270, 170, 530, 330, (380, 80, 600, 220), pad=4); pz.frame(); pz.fill(cs, col)
        pc = sh.panel(x0 + 270, 510, 530, 330, (380, 80, 600, 220), pad=4); pc.frame(); pc.fill(cs, (46, 46, 52)); comb(pc, cs, col, gain=1500)
        sh.text(x0 + 6, 176, nm, col, 15)
    sh.key(26, 880, [(nm, col) for nm, _, col in I], 17)
    for k, (nm, cs, col) in enumerate(I):
        x0 = 20 + k * 1210
        pw = sh.panel(x0, 920, 400, 600, (60, -30, 760, 580), pad=4); pw.frame(); pw.fill(cs, col)
        pz = sh.panel(x0 + 410, 920, 790, 600, (430, 80, 700, 250), pad=4); pz.frame(); pz.fill(cs, col)
        sh.text(x0 + 6, 926, nm, col, 16)
    return sh.save(os.path.join(C.R5, "sheets", "e_tail_fix.png"))


if __name__ == "__main__":
    print(main())
