"""Step 2: the Slant outlines of "Harper’s Bazzar", placed with the proof page's layout, against the page's own 1x4 row
(the 4th big text path). Both filled nonzero, rasterised at SC x page pixels; XOR area / page ink area.
Writes italic/sheets/shear_check.png (grey = page, blue = ours, red = XOR) and prints per-letter mismatch."""
import sys, os, json, re, math
import numpy as np, skia
from PIL import Image, ImageDraw
from fontTools.svgLib.path import parse_path
from fontTools.pens.basePen import BasePen
HERE = os.path.dirname(os.path.abspath(__file__)); WORK = os.path.join(HERE, "..", "..")
S, X0, PAD, H, ROWS, LINE = 0.125, 326.0, 56, 2122, 7, int(710 * 0.125 * 1.55)
SC = 4
LINE1 = "Harper’s Bazzar"; NAME = {"’": "quoteright", " ": "space"}


class SkPen(BasePen):
    def __init__(self, path, xf=None):
        super().__init__(None); self.p = path; self.xf = xf or (lambda q: q)
    def _moveTo(self, a): self.p.moveTo(*self.xf(a))
    def _lineTo(self, a): self.p.lineTo(*self.xf(a))
    def _curveToOne(self, a, b, c): self.p.cubicTo(*self.xf(a), *self.xf(b), *self.xf(c))
    def _qCurveToOne(self, a, b): self.p.quadTo(*self.xf(a), *self.xf(b))
    def _closePath(self): self.p.close()


def glyph_path(contours, xf):
    p = skia.Path(); p.setFillType(skia.PathFillType.kWinding)
    for c in contours:
        nodes = c["nodes"]; s = next(i for i, n in enumerate(nodes) if n[2] != "o")
        order = nodes[s:] + nodes[:s]
        p.moveTo(*xf(order[0][:2])); buf = []
        for n in order[1:] + [order[0]]:
            if n[2] == "o": buf.append(n[:2])
            elif n[2] == "l": p.lineTo(*xf(n[:2])); buf = []
            else: p.cubicTo(*xf(buf[0]), *xf(buf[1]), *xf(n[:2])); buf = []
        p.close()
    return p


def raster(path, box):
    x0, y0, x1, y1 = box
    W, Hh = int((x1 - x0) * SC), int((y1 - y0) * SC)
    surf = skia.Surface(W, Hh); c = surf.getCanvas(); c.clear(skia.ColorWHITE)
    c.scale(SC, SC); c.translate(-x0, -y0)
    c.drawPath(path, skia.Paint(Color=skia.ColorBLACK, AntiAlias=False))
    return np.array(surf.makeImageSnapshot())[..., 0] < 128


if __name__ == "__main__":
    master = sys.argv[1] if len(sys.argv) > 1 else "Slant"
    G = json.load(open(os.path.join(WORK, "italic", "src", "geistserif_italic.json")))
    kern = json.load(open(os.path.join(WORK, "italic", "src", "kerning.json")))
    svg = open(os.path.join(WORK, "src", "proof", "page_geist-serif_Regular_harpers.svg")).read()
    big = [m for m in re.findall(r'<path d="([^"]*)" fill="#111"/>', svg) if len(m) > 15000]
    page = skia.Path(); page.setFillType(skia.PathFillType.kWinding)
    parse_path(big[3], SkPen(page))
    pitch = (H - 124 - PAD) / ROWS
    last = 124 + pitch * 4 - 30; first = last - LINE
    ours = skia.Path(); ours.setFillType(skia.PathFillType.kWinding)
    x = 0.0; prev = None; spans = []; boxes = []
    for ch in LINE1:
        g = NAME.get(ch, ch)
        if prev: x += kern.get("%s %s" % (prev, g), 0)
        if g != "space":
            ox = X0 + x * S
            gp = glyph_path(G["GeistSerif%s_%s" % (master, g)]["contours"], lambda q, ox=ox: (ox + q[0] * S, first - q[1] * S))
            ours.addPath(gp); boxes.append((g, gp))
            spans.append((g, ox + (-60) * S, ox + (G["space"]["width"] if g == "space" else G["GeistSerifRegular_" + g]["width"] + 260) * S))
        x += G["space"]["width"] if g == "space" else G["GeistSerifRegular_" + g]["width"]; prev = g
    box = (X0 - 20, first - 820 * S, X0 + x * S + 60, first + 260 * S)
    a = raster(page, box); b = raster(ours, box)
    # the page path also holds the second line: keep only rows above the second line's ascent
    xo = a ^ b
    print("line: page ink %d px, ours %d px, XOR %d px = %.3f%% of page ink (at %dx)" % (a.sum(), b.sum(), xo.sum(), 100 * xo.sum() / a.sum(), SC))
    # per letter: XOR inside the letter's own ink box (ours, padded 3 page px; boxes of sheared neighbours overlap a little)
    rows = []
    for g, gp in boxes:
        r = gp.computeTightBounds()
        c0 = max(0, int((r.left() - 3 - box[0]) * SC)); c1 = int((r.right() + 3 - box[0]) * SC)
        r0 = max(0, int((r.top() - 3 - box[1]) * SC)); r1 = int((r.bottom() + 3 - box[1]) * SC)
        rows.append((g, int(xo[r0:r1, c0:c1].sum()), int(a[r0:r1, c0:c1].sum())))
    for g, xx, aa in rows:
        print("  %-10s XOR %5d / ink %6d px  (%.2f%%)" % (g, xx, aa, 100 * xx / max(1, aa)))
    img = np.full(a.shape + (3,), 255, np.uint8)
    img[a] = (200, 200, 200); img[b & ~a] = (60, 110, 230); img[xo] = (230, 30, 30)
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    d.text((10, 6), "1x4 row, line 1: grey = proof page path (overlaps removed), blue = %s outlines placed by the page's layout, red = XOR · %.3f%% of page ink at %dx"
           % (master, 100 * xo.sum() / a.sum(), SC), fill=(0, 0, 0))
    d.text((10, 20), "quoteright: the page drew it with its component's 90% scale dropped (make_geist_pages.outline keeps only pos + angle); with that scale dropped ours matches it to 0.3%; ours (90%) matches the TTF. "
           "e: the tail's open corner, erased on the page (EraseOpenCornersPen), kept as drawn here.", fill=(120, 0, 0))
    out = os.path.join(WORK, "italic", "sheets", "shear_check.png" if master == "Slant" else "shear_check_%s.png" % master)
    im.save(out); print(out)
