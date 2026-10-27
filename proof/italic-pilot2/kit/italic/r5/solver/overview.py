"""Per-master overview: every letter at CNTR 0 / 50 / 100 (filled, drawn dashed under 50 and 100), Harvey below."""
import sys, os, json, math, traceback
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from move import Mover
from sheet import Panel, BG, SS, font, CAL
from partsheet import draw_poly
from rungs import Outline

ROWS = [["f", "j", "H", "n"], ["a", "E", "T", "r"], ["v", "e", "y", "k"], ["x"]]

def strip(g, M, W, H, label=True):
    """three panels side by side for one glyph"""
    xs = [n[0] for c in g["contours"] for n in c["nodes"]]; ys = [n[1] for c in g["contours"] for n in c["nodes"]]
    bb = (min(xs) - 30, min(ys) - 30, max(xs) + 30, max(ys) + 30)
    out = Image.new("RGB", (W * 3 + 8, H), BG)
    for i, t in enumerate((0.0, 0.5, 1.0)):
        A = Panel(W, H, bb, margin=16)
        if label:
            A.title("/%s · %d" % (g["glyph"], int(t * 100)))
        ol2 = Outline(M.contours_at(t)) if M is not None else Outline(g["contours"])
        A.fill_outline(ol2, color=(78, 88, 64) if t > 0 else (60, 70, 50), edge=(150, 150, 150))
        if t > 0 and M is not None:
            for poly in M.ol.polys:
                draw_poly(A, poly + [poly[0]], (230, 230, 230), 0.9, dash=5)
        out.paste(A.out(), (i * (W + 4), 0))
    return out

if __name__ == "__main__":
    G = json.load(open(sys.argv[1])); outdir = sys.argv[2]
    log = []
    for m in sys.argv[3].split(","):
        tag = "HS" + m.replace(" ", "")
        CW, CH = 280, 310
        SW = CW * 3 + 8
        sheet = Image.new("RGB", (SW * 4 + 50, (CH + 10) * 4 + 520), BG)
        d = sheet
        for ri, row in enumerate(ROWS):
            for ci, gn in enumerate(row):
                key = "%s_%s" % (tag, gn)
                if key not in G: continue
                try:
                    M = Mover(G[key]); im = strip(G[key], M, CW, CH)
                    log.append((key, "ok", len(M.cups), round(max([math.hypot(*v) for v in M.disp.values()] or [0]), 1)))
                except Exception as e:
                    im = strip(G[key], None, CW, CH); log.append((key, "FAIL", repr(e)[:80])); print(traceback.format_exc()[-400:])
                sheet.paste(im, (10 + ci * (SW + 10), 10 + ri * (CH + 10)))
        key = "%s_H_a_r_v_e_y" % tag
        if key in G:
            try:
                M = Mover(G[key]); im = strip(G[key], M, (SW * 4 + 30) // 3 - 4, 480)
                log.append((key, "ok", len(M.cups), round(max([math.hypot(*v) for v in M.disp.values()] or [0]), 1)))
            except Exception as e:
                im = strip(G[key], None, (SW * 4 + 30) // 3 - 4, 480); log.append((key, "FAIL", repr(e)[:80])); print(traceback.format_exc()[-400:])
            sheet.paste(im, (10, (CH + 10) * 4 + 20))
        out = os.path.join(outdir, "overview_%s.png" % tag); sheet.save(out); print("wrote", out)
    for row in log: print(row)
