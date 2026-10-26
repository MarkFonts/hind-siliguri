"""Zoom on an issue region: engine pairing | rung pairing, every rung, labels on both."""
import sys, os, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheet import Panel, ramp, EDGE, BG, SS, font, MENLO
from rungs import Outline

def zoom(key, G, eng_dir, nodes, out_path, pad=40, PW=900, PH=760, every=2):
    g = G[key]; ol = Outline(g["contours"])
    geo = json.load(open(os.path.join(eng_dir, key + ".json")))
    m = geo["master"]; stems = sorted(m["vstems"] + m["hstems"]); lo, hi = 0.6 * min(stems), 1.1 * max(stems)
    xs = [ol.node_xy[n][0] for n in nodes]; ys = [ol.node_xy[n][1] for n in nodes]
    bb = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
    ol.pair_all(); ol.strokes(); nr = ol.node_readings()

    A = Panel(PW, PH, bb, margin=30)
    A.title("/%s %s · current engine pairing · nodes %d–%d" % (g["glyph"], g["master"], min(nodes), max(nodes)),
            "every %dnd sample→partner chord, coloured by width · grey dot = unpaired · number = width at that sample" % every)
    A.fill_outline(ol)
    for part in geo["chords"]:
        P = np.array(part["P"]); partner = np.array(part["partner"]); width = np.array(part["width"])
        for i in range(0, len(P), every):
            x, y = P[i]
            if not (bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]): continue
            j = partner[i]
            if j < 0:
                A.dot(P[i], (120, 120, 120), 1.4); continue
            w = width[i]; col = ramp(w if w > 0 else None, lo, hi)
            A.line(P[i], P[j], col, 1.0)
            if i % (every * 6) == 0:
                A.text(((P[i][0] + P[j][0]) / 2, (P[i][1] + P[j][1]) / 2), "%.0f" % w, col, size=8, dx=2, dy=-9)
    A.nodes(ol)

    B = Panel(PW, PH, bb, margin=30)
    B.title("/%s %s · rung pairing · nodes %d–%d" % (g["glyph"], g["master"], min(nodes), max(nodes)),
            "largest circle tangent at each point · blue edges = wedge serif, HELD (rule 8) · white dot = centre · grey tick = corner (rule 5) · blue tick = side-on · brown tick = rests on the far wall's end corner (cap, carried) · magenta = crossing")
    B.fill_outline(ol)
    from sheet import held_edges
    held_edges(B, ol)
    for r in ol.readings:
        if r is None: continue
        k, j = r["k"], r["j"]; p = ol.P[k]
        if not (bb[0] <= p[0] <= bb[2] and bb[1] <= p[1] <= bb[3]): continue
        if r["status"] == "serif": continue
        if r["status"] in ("corner", "oblique", "end"):
            n = ol.N[k]; B.line(p, (p[0] + n[0] * 5, p[1] + n[1] * 5), {"corner": (130, 130, 130), "oblique": (90, 120, 170), "end": (170, 120, 60)}[r["status"]], 0.9); continue
        if k % every: continue
        col = ramp(r["w"], lo, hi)
        if r.get("cross"): col = (200, 90, 220)
        B.line(p, ol.P[j], col, 0.9); B.dot(r["c"], (235, 235, 235), 1.0)
        if k % (every * 6) == 0:
            B.text(r["c"], "%.0f" % r["w"], col, size=8, dx=2, dy=-9)
    for gi, cands in nr.items():
        for side, r in cands:
            if r["status"] != "ok": continue
            p, q = ol.P[r["k"]], ol.P[r["j"]]
            if not (bb[0] <= p[0] <= bb[2] and bb[1] <= p[1] <= bb[3]): continue
            col = ramp(r["w"], lo, hi)
            if r.get("cross"): col = (220, 110, 240)
            B.line(p, q, col, 2.4); B.dot(r["c"], (255, 255, 255), 1.8)
            pn = ol.nearest_node(q)
            if pn is None:
                X, Y = B.pt(q); rr = 3 * SS
                B.d.ellipse([X - rr, Y - rr, X + rr, Y + rr], outline=(255, 255, 255), width=SS)
            B.text(r["c"], "%d: %.0f" % (gi, r["w"]), col, size=9, dx=3, dy=-12)
    B.nodes(ol)
    sheet = Image.new("RGB", (PW * 2 + 10, PH), BG)
    sheet.paste(A.out(), (0, 0)); sheet.paste(B.out(), (PW + 10, 0)); sheet.save(out_path)

if __name__ == "__main__":
    G = json.load(open(sys.argv[1])); eng = sys.argv[2]; outdir = sys.argv[3]
    for spec in sys.argv[4:]:
        key, ns = spec.split(":"); nodes = [int(n) for n in ns.split(",")]
        zoom(key, G, eng, nodes, os.path.join(outdir, key + "_zoom_%d-%d.png" % (min(nodes), max(nodes))))
        print("ok", spec)
