"""x k n in Mark's blend layout: one row per CNTR value, sides + 3 blends, no fill, baseline."""
import sys, os, json
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from move import Mover
from movesheet import moved_side
from sheet import Panel, BG, SS, font, CAL
from partsheet import COLS, draw_poly, draw_flag

def row(G, master, t, glyphs, CW=640, CH=620):
    ims = []
    for gn in glyphs:
        g = G["HS%s_%s" % (master.replace(" ", ""), gn)]; M = Mover(g)
        xs = [n[0] for c in g["contours"] for n in c["nodes"]]
        bb = (min(xs) - 40, -60, max(xs) + 40, 560)
        A = Panel(CW, CH, bb, margin=20)
        A.title("/%s %s · CNTR %d" % (gn, master, int(t * 100)))
        if t > 0:
            for poly in M.ol.polys:
                draw_poly(A, poly + [poly[0]], (90, 90, 90), 0.7, dash=6)
        A.line((bb[0], 0), (bb[2], 0), (60, 160, 180), 0.8)
        for i, (SA, saL, dAL, SB, sbL, dBL, st) in enumerate(M.side_disp):
            col = COLS[i % len(COLS)]
            draw_poly(A, moved_side(SA, saL, dAL, t, M), col, 1.6); draw_poly(A, moved_side(SB, sbL, dBL, t, M), col, 1.6)
            rs = [(r[0], r[1]) for r in st["rungs"] if r[0] is not None and r[1] is not None and r[2] != "cross"]
            for u, w in ((0.25, 0.9), (0.5, 1.6), (0.75, 0.9)):
                pts = []
                for (a0, b0), (a1, b1) in zip(rs, rs[1:]):
                    for k in range(25):
                        f = k / 24; sa = a0 + (a1 - a0) * f; sb = b0 + (b1 - b0) * f
                        qa = SA.at(sa); va = M.interp(sa, saL, dAL); qa = (qa[0] + va[0] * t, qa[1] + va[1] * t)
                        qb = SB.at(sb); vb = M.interp(sb, sbL, dBL); qb = (qb[0] + vb[0] * t, qb[1] + vb[1] * t)
                        pts.append((qa[0] + (qb[0] - qa[0]) * u, qa[1] + (qb[1] - qa[1]) * u))
                draw_poly(A, pts, col if u != 0.5 else (255, 255, 255), w)
        for fl in M.P.flags:
            draw_flag(A, M.P, fl)
        ims.append(A.out())
    return ims

if __name__ == "__main__":
    G = json.load(open(sys.argv[1])); out = sys.argv[2]; master = sys.argv[3]
    glyphs = sys.argv[4].split(",")
    CW, CH = 640, 620
    sheet = Image.new("RGB", (CW * len(glyphs) + 20, CH * 2 + 20), BG)
    for ri, t in enumerate((0.0, 1.0)):
        for ci, im in enumerate(row(G, master, t, glyphs, CW, CH)):
            sheet.paste(im, (10 + ci * CW, 10 + ri * CH))
    sheet.save(out); print("wrote", out)
