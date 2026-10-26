"""Filled 3-up (upright | plain slant | corrected) of the bowl letters, the way the font renders them:
open corners erased (Glyphs' EraseOpenCornersPen, what the export does), nonzero fill, no outlines.

bowls_sheet.py [letters] [--out PNG] [--label SIZE]      default letters: e n a p s B
"""
import sys, os, json, argparse
import skia
from PIL import Image, ImageDraw, ImageFont
from glyphsLib.filters.eraseOpenCorners import EraseOpenCornersPen

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src", "geistserif_italic.json")
MENLO = "/System/Library/Fonts/Menlo.ttc"
BG, INK, LBL = (13, 13, 13), (232, 232, 232), (232, 184, 74)


class SkiaPen:
    def __init__(self):
        self.p = skia.Path(); self.p.setFillType(skia.PathFillType.kWinding)
    def moveTo(self, pt): self.p.moveTo(*pt)
    def lineTo(self, pt): self.p.lineTo(*pt)
    def curveTo(self, *pts): self.p.cubicTo(*pts[0], *pts[1], *pts[2])
    def qCurveTo(self, *pts): raise NotImplementedError
    def closePath(self): self.p.close()
    def endPath(self): self.p.close()


def draw_glyph(g, pen):
    for c in g["contours"]:
        nodes = c["nodes"]
        s = next(i for i, nd in enumerate(nodes) if nd[2] != "o"); order = nodes[s:] + nodes[:s]
        pen.moveTo(tuple(order[0][:2])); buf = []
        for nd in order[1:] + [order[0]]:
            if nd[2] == "o": buf.append(tuple(nd[:2]))
            elif nd[2] == "l": pen.lineTo(tuple(nd[:2])); buf = []
            else: pen.curveTo(buf[0], buf[1], tuple(nd[:2])); buf = []
        pen.closePath()


def path_of(g, erase=True):
    sp = SkiaPen()
    draw_glyph(g, EraseOpenCornersPen(sp) if erase else sp)
    return sp.p


def sheet(letters, out, label=14, cell_h=int((800 + 212) * 0.42) + 90, scale=0.42, per_row=2):
    G = json.load(open(SRC))
    cols = [("Regular", "upright"), ("Slant", "slant"), ("Italic", "corrected")]
    # column widths from the widest advance per column position
    cw = [int(max(G["GeistSerif%s_%s" % (m, gl)]["width"] for gl in letters) * scale) + 40 for m, _ in cols]
    LW = sum(cw) + 40
    rows = (len(letters) + per_row - 1) // per_row
    W, H = LW * per_row + 20, cell_h * rows + 20
    surf = skia.Surface(W, H); cv = surf.getCanvas(); cv.clear(skia.Color(*BG))
    paint = skia.Paint(AntiAlias=True, Color=skia.Color(*INK))
    labels = []
    for i, gl in enumerate(letters):
        r, c = divmod(i, per_row)
        x0 = 10 + c * LW; y0 = 10 + r * cell_h
        x = x0
        for (m, name), w in zip(cols, cw):
            g = G["GeistSerif%s_%s" % (m, gl)]
            cv.save(); cv.translate(x + 20, y0 + 50 + 800 * scale); cv.scale(scale, -scale); cv.drawPath(path_of(g), paint); cv.restore()
            labels.append((x + 6, y0 + 6, "/%s %s" % (gl, name)))
            x += w
    im = Image.frombytes("RGBA", (W, H), surf.makeImageSnapshot().tobytes()).convert("RGB")
    d = ImageDraw.Draw(im); f = ImageFont.truetype(MENLO, label)
    for x, y, t in labels:
        d.text((x, y), t, fill=LBL, font=f)
    im.save(out); print("wrote", out, im.size)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("letters", nargs="?", default="e,n,a,p,s,B")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "sheets", "bowls_3up.png"))
    ap.add_argument("--label", type=int, default=21)       # Mark 2026-10-23: 50% larger than the 14 px dev sheet
    a = ap.parse_args()
    sheet(a.letters.replace(" ", ",").split(","), a.out, label=a.label)
