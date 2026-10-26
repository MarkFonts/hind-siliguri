"""The solver's node moves in Italify's picture: per letter the plain slant (faint) and the corrected (solid) outline,
on-curve nodes as rings, handles as blue dots, and one arrow per on-curve node that moved (drawn x2, label in units).
Compare with sheets/italify_vectors.png, which is the same picture measured from Mark's Italify screenshots.

vectors_sheet.py [letters] [--out PNG]      default o,s,e
"""
import sys, os, json, math, argparse
import skia
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src", "geistserif_italic.json")
MENLO = "/System/Library/Fonts/Menlo.ttc"


def path_of(contours):
    p = skia.Path()
    for c in contours:
        nodes = c["nodes"]
        s = next(i for i, nd in enumerate(nodes) if nd[2] != "o"); order = nodes[s:] + nodes[:s]
        p.moveTo(order[0][0], order[0][1]); buf = []
        for nd in order[1:] + [order[0]]:
            if nd[2] == "o": buf.append((nd[0], nd[1]))
            elif nd[2] == "l": p.lineTo(nd[0], nd[1]); buf = []
            else: p.cubicTo(buf[0][0], buf[0][1], buf[1][0], buf[1][1], nd[0], nd[1]); buf = []
        p.close()
    return p


def panel(gl, G, sc=1.25):
    sl, it = G["GeistSerifSlant_" + gl], G["GeistSerifItalic_" + gl]
    xs = [n[0] for c in sl["contours"] for n in c["nodes"]]; ys = [n[1] for c in sl["contours"] for n in c["nodes"]]
    W = int((max(xs) - min(xs)) * sc) + 170; H = int((max(ys) - min(ys)) * sc) + 110      # the letter plus room for labels
    ox = W / 2 - (min(xs) + max(xs)) / 2 * sc; oy = H / 2 + (min(ys) + max(ys)) / 2 * sc
    T = lambda p: (ox + p[0] * sc, oy - p[1] * sc)
    surf = skia.Surface(W, H); cv = surf.getCanvas(); cv.clear(skia.Color(28, 29, 35))
    # metric lines
    for y in (0, 530):
        a, b = T((-1000, y)), T((3000, y)); cv.drawLine(a[0], a[1], b[0], b[1], skia.Paint(Color=skia.Color(90, 90, 95), StrokeWidth=1, PathEffect=skia.DashPathEffect.Make([8, 8], 0)))
    for g, col, w in ((sl, (120, 120, 125), 2.0), (it, (240, 240, 240), 2.6)):
        cv.save(); cv.translate(ox, oy); cv.scale(sc, -sc)
        cv.drawPath(path_of(g["contours"]), skia.Paint(AntiAlias=True, Color=skia.Color(*col), Style=skia.Paint.kStroke_Style, StrokeWidth=w / sc))
        cv.restore()
    im = Image.frombytes("RGBA", (W, H), surf.makeImageSnapshot().tobytes()).convert("RGB"); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(MENLO, 17)
    fs, fi = [n for c in sl["contours"] for n in c["nodes"]], [n for c in it["contours"] for n in c["nodes"]]
    # handle dots (corrected), rings for on-curve nodes (slant faint, corrected solid), arrows
    for n0, n1 in zip(fs, fi):
        if n0[2] == "o":
            X, Y = T(n1); d.ellipse([X - 4, Y - 4, X + 4, Y + 4], fill=(110, 150, 230)); continue
        X0, Y0 = T(n0); X1, Y1 = T(n1)
        d.ellipse([X0 - 8, Y0 - 8, X0 + 8, Y0 + 8], outline=(150, 150, 150), width=2)
        d.ellipse([X1 - 8, Y1 - 8, X1 + 8, Y1 + 8], outline=(245, 245, 245), width=3)
        dx, dy = n1[0] - n0[0], n1[1] - n0[1]; L = math.hypot(dx, dy)
        if L < 1.0:
            continue
        X2, Y2 = X0 + dx * sc * 2, Y0 - dy * sc * 2
        col = (255, 215, 60)
        d.line([(X0, Y0), (X2, Y2)], fill=col, width=4)
        ang = math.atan2(Y2 - Y0, X2 - X0)
        for s_ in (+1, -1):
            d.line([(X2, Y2), (X2 - 14 * math.cos(ang + s_ * 0.45), Y2 - 14 * math.sin(ang + s_ * 0.45))], fill=col, width=4)
        arrow = "←" if dx < -0.3 * L else "→" if dx > 0.3 * L else "↑" if dy > 0 else "↓"
        d.text((X2 + 8, Y2 - 22), "%s%.0f u" % (arrow, L), fill=col, font=f)
    d.text((14, 10), "/%s  solver: plain slant → corrected  (arrows ×2, units)" % gl, fill=(240, 200, 80), font=ImageFont.truetype(MENLO, 22))
    return im


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("letters", nargs="?", default="o,s,e")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "sheets", "solver_vectors.png"))
    a = ap.parse_args()
    G = json.load(open(SRC))
    panels = [panel(gl, G) for gl in a.letters.split(",")]
    W = sum(p.size[0] for p in panels) + 20 * (len(panels) - 1); H = max(p.size[1] for p in panels)
    out = Image.new("RGB", (W, H), (20, 20, 24)); x = 0
    for p in panels:
        out.paste(p, (x, 0)); x += p.size[0] + 20
    out.save(a.out); print("wrote", a.out, out.size)
