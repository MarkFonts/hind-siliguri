"""Debug/approval sheet for the stem-relative detectors: slab serifs (red, root = yellow ring), balls (cyan,
inscribed circle drawn), Harvey's own serifs (grey). One sheet per master.
detectsheet.py SET.json OUT.png TAG STEM [SLANT]"""
import sys, os, json, math
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rungs import Outline
from sheet import Panel, BG, bbox_of
from partsheet import draw_poly

def cell(g, stem, slant, W=440, H=480):
    ol = Outline(g["contours"], slant=slant, stem=stem)
    A = Panel(W, H, bbox_of(ol, pad=30), margin=28)
    ns = sum(1 for s in ol.serifs if s["kind"] == "slab")
    A.title("/%s" % g["glyph"], "%d slab-serif end faces, %d balls" % (ns, len(ol.balls)))
    A.fill_outline(ol, color=(38, 46, 30), edge=(90, 90, 90))
    for k in ol.serif_segs:
        col = (240, 70, 60) if k in ol.slab_segs else (150, 150, 150)
        draw_poly(A, ol.segs[k].poly, col, 2.2)
    for k in ol.ball_segs:
        draw_poly(A, ol.segs[k].poly, (60, 220, 240), 2.6)
    for b in ol.balls:
        r = b["D"] / 2
        draw_poly(A, [(b["c"][0] + r * math.cos(t / 24 * math.pi), b["c"][1] + r * math.sin(t / 24 * math.pi)) for t in range(49)], (60, 220, 240), 0.8, dash=4)
    for s in ol.serifs:
        if s["kind"] == "slab":
            x, y = ol.node_xy[s["root"]][:2]
            A.dot((x, y), (250, 210, 60), r=5)
    A.nodes(ol, labels=True)
    return A.out()

if __name__ == "__main__":
    G = json.load(open(sys.argv[1])); out = sys.argv[2]; tag = sys.argv[3]; stem = float(sys.argv[4])
    slant = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
    keys = [k for k in sorted(G) if k.split("_")[0] == tag and "H_a_r_v_e_y" not in k]
    CW, CH = 440, 480; cols = 7
    rows = (len(keys) + cols - 1) // cols
    sheet = Image.new("RGB", (CW * cols + 20, CH * rows + 20), BG)
    for i, k in enumerate(keys):
        sheet.paste(cell(G[k], stem, slant, CW, CH), (10 + (i % cols) * CW, 10 + (i // cols) * CH))
    sheet.save(out); print("wrote", out)
