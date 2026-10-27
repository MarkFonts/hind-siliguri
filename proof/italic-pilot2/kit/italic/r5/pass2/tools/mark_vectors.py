"""Mark's own node moves, slant -> his drawn italic, in the Italify arrow picture: his drawn glyph (from a Glyphs
print PDF, paths parsed to JSON) is aligned on the slanted glyph by its held terminal corners (the cut ends, which
nobody moves), then every on-curve node of the slant is paired with the nearest on-curve node of his drawing and the
vector drawn (x2) with its length in units. Also prints the pairs.

mark_vectors.py PATHS.json LETTER SUBPATHS [--out PNG]     e.g. mark_vectors.py ../src/mark_sop_v2_pdf_paths.json s 0
"""
import sys, os, json, math, argparse
import numpy as np
import skia
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
from vectors_sheet import path_of
SRC = os.path.join(HERE, "..", "src", "geistserif_italic.json")
MENLO = "/System/Library/Fonts/Menlo.ttc"
S = 4.0


def mark_nodes(paths, idx, base_pt):
    """on-curve nodes (and the full node list) of Mark's subpaths in font units"""
    ons, allnodes = [], []
    for i in idx:
        cur = None
        for q in paths[i]:
            if q[0] in ("m", "l"):
                p = (q[1][0] * S, (q[1][1] - base_pt) * S); ons.append(p); allnodes.append((p, "on")); cur = q[1]
            elif q[0] == "c":
                c1 = q[1] if q[1] else cur
                for h in (c1, q[2]):
                    allnodes.append(((h[0] * S, (h[1] - base_pt) * S), "off"))
                p = (q[3][0] * S, (q[3][1] - base_pt) * S); ons.append(p); allnodes.append((p, "on")); cur = q[3]
    # drop the closing duplicate
    if len(ons) > 1 and math.dist(ons[0], ons[-1]) < 0.5:
        ons.pop()
    return ons, allnodes


def mark_path(paths, idx, base_pt, dx):
    p = skia.Path()
    for i in idx:
        cur = None
        for q in paths[i]:
            if q[0] == "m": p.moveTo(q[1][0] * S + dx, (q[1][1] - base_pt) * S); cur = q[1]
            elif q[0] == "l": p.lineTo(q[1][0] * S + dx, (q[1][1] - base_pt) * S); cur = q[1]
            elif q[0] == "c":
                c1 = q[1] if q[1] else cur
                p.cubicTo(c1[0] * S + dx, (c1[1] - base_pt) * S, q[2][0] * S + dx, (q[2][1] - base_pt) * S, q[3][0] * S + dx, (q[3][1] - base_pt) * S); cur = q[3]
            elif q[0] == "h": p.close()
        p.close()
    return p


def main(paths_file, gl, idx, out, o_outer=None):
    paths = json.load(open(paths_file)); G = json.load(open(SRC))
    if o_outer is None:                                   # the o's outer ring: the 6-op subpath with the widest box
        o_outer = max([i for i, p in enumerate(paths) if len(p) == 6], key=lambda i: max(q[-1][0] for q in paths[i] if len(q) > 1) - min(q[-1][0] for q in paths[i] if len(q) > 1))
    base_pt = min(q[-1][1] for q in paths[o_outer] if len(q) > 1) + 12 / S     # the o's bottom overshoot is -12 u
    sl = G["GeistSerifSlant_" + gl]
    sl_nodes = [n for c in sl["contours"] for n in c["nodes"]]
    sl_on = [(n[0], n[1]) for n in sl_nodes if n[2] != "o"]
    m_on, m_all = mark_nodes(paths, idx, base_pt)
    # align on the lowest-left and highest-right on-curve nodes (the terminal corners, held by everyone)
    def corners(P):
        lo = min(P, key=lambda p: p[1] - 0.2 * p[0]); hi = max(P, key=lambda p: p[1] + 0.2 * p[0]); return lo, hi
    (a0, a1), (b0, b1) = corners(sl_on), corners(m_on)
    dx = ((a0[0] - b0[0]) + (a1[0] - b1[0])) / 2
    m_on = [(x + dx, y) for x, y in m_on]; m_all = [((x + dx, y), k) for (x, y), k in m_all]
    pairs = []
    if len(m_on) == len(sl_on):
        # same node count: pair in sequence, choosing the cyclic shift and direction with the least total distance
        n = len(sl_on); best = None
        for rev in (False, True):
            M = m_on[::-1] if rev else m_on
            for sh in range(n):
                tot = sum(math.dist(sl_on[i], M[(i + sh) % n]) for i in range(n))
                if best is None or tot < best[0]: best = (tot, rev, sh)
        _, rev, sh = best; M = m_on[::-1] if rev else m_on
        pairs = [(p, M[(i + sh) % n], math.dist(p, M[(i + sh) % n])) for i, p in enumerate(sl_on)]
    else:
        for p in sl_on:
            q = min(m_on, key=lambda q: math.dist(p, q)); pairs.append((p, q, math.dist(p, q)))
    print("%s: slant %d on-curve nodes, Mark %d; aligned by the terminal corners (dx %+.0f)" % (gl, len(sl_on), len(m_on), dx))
    for p, q, d in pairs:
        print("  slant (%4.0f,%4.0f) -> Mark (%4.0f,%4.0f)  move (%+4.0f,%+4.0f) |%3.0f|" % (p[0], p[1], q[0], q[1], q[0] - p[0], q[1] - p[1], d))
    # sheet
    sc = 1.25
    xs = [n[0] for n in sl_nodes] + [p[0] for p in m_on]; ys = [n[1] for n in sl_nodes] + [p[1] for p in m_on]
    W = int((max(xs) - min(xs)) * sc) + 170; H = int((max(ys) - min(ys)) * sc) + 110
    ox = W / 2 - (min(xs) + max(xs)) / 2 * sc; oy = H / 2 + (min(ys) + max(ys)) / 2 * sc
    T = lambda p: (ox + p[0] * sc, oy - p[1] * sc)
    surf = skia.Surface(W, H); cv = surf.getCanvas(); cv.clear(skia.Color(28, 29, 35))
    for pth, col, w in ((path_of(sl["contours"]), (120, 120, 125), 2.0), (mark_path(paths, idx, base_pt, dx), (240, 240, 240), 2.6)):
        cv.save(); cv.translate(ox, oy); cv.scale(sc, -sc)
        cv.drawPath(pth, skia.Paint(AntiAlias=True, Color=skia.Color(*col), Style=skia.Paint.kStroke_Style, StrokeWidth=w / sc)); cv.restore()
    im = Image.frombytes("RGBA", (W, H), surf.makeImageSnapshot().tobytes()).convert("RGB"); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(MENLO, 17)
    for (x, y), k in m_all:
        X, Y = T((x, y))
        if k == "off": d.ellipse([X - 4, Y - 4, X + 4, Y + 4], fill=(110, 150, 230))
        else: d.ellipse([X - 8, Y - 8, X + 8, Y + 8], outline=(245, 245, 245), width=3)
    for p, q, dd in pairs:
        X0, Y0 = T(p); d.ellipse([X0 - 8, Y0 - 8, X0 + 8, Y0 + 8], outline=(150, 150, 150), width=2)
        if dd < 1.0: continue
        vx, vy = q[0] - p[0], q[1] - p[1]; X2, Y2 = X0 + vx * sc * 2, Y0 - vy * sc * 2
        col = (255, 215, 60); d.line([(X0, Y0), (X2, Y2)], fill=col, width=4)
        ang = math.atan2(Y2 - Y0, X2 - X0)
        for s_ in (+1, -1):
            d.line([(X2, Y2), (X2 - 14 * math.cos(ang + s_ * 0.45), Y2 - 14 * math.sin(ang + s_ * 0.45))], fill=col, width=4)
        arrow = "←" if vx < -0.3 * dd else "→" if vx > 0.3 * dd else "↑" if vy > 0 else "↓"
        d.text((X2 + 8, Y2 - 22), "%s%.0f u" % (arrow, dd), fill=col, font=f)
    d.text((14, 10), "/%s  Mark's drawing: plain slant (faint) → his italic (solid), nearest nodes (arrows ×2, units)" % gl, fill=(240, 200, 80), font=ImageFont.truetype(MENLO, 22))
    im.save(out); print("wrote", out, im.size)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("paths"); ap.add_argument("letter"); ap.add_argument("subpaths")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    idx = [int(v) for v in a.subpaths.split(",")]
    main(a.paths, a.letter, idx, a.out or os.path.join(HERE, "..", "sheets", "mark_vectors_%s.png" % a.letter))
