"""Verify the extra letters (src/geistserif_extra.json) against Glyphs' exported TTF, read in place (never copied):
raster XOR at 1 px = 1 unit, mismatch = XOR area / TTF glyph area (the corner_check.py method).
extra_check.py TTF OUT.png"""
import sys, os, json, math
import numpy as np, pathops
from PIL import Image, ImageDraw, ImageChops
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
HERE = os.path.dirname(os.path.abspath(__file__)); WORK = os.path.join(HERE, "..", "..")
W, H, OX, BASE = 1000, 1300, 150, 1000


def json_path(contours):
    p = pathops.Path(); pen = p.getPen()
    for c in contours:
        nodes = c["nodes"]
        s = next(i for i, nd in enumerate(nodes) if nd[2] != 'o')
        order = nodes[s:] + nodes[:s]
        pen.moveTo(tuple(order[0][:2])); buf = []
        for nd in order[1:] + [order[0]]:
            if nd[2] == 'o': buf.append(tuple(nd[:2]))
            elif nd[2] == 'l': pen.lineTo(tuple(nd[:2])); buf = []
            else: pen.curveTo(buf[0], buf[1], tuple(nd[:2])); buf = []
        pen.closePath()
    return p


def raster(path):
    q = pathops.Path(path); q.simplify(fix_winding=True)
    im = Image.new("1", (W, H), 0)
    from fontTools.pens.basePen import BasePen
    polys = []
    class P(BasePen):
        def _moveTo(self, p): polys.append([p])
        def _lineTo(self, p): polys[-1].append(p)
        def _curveToOne(self, a, b, c):
            p0 = polys[-1][-1]
            for t in np.linspace(0, 1, 25)[1:]:
                u = 1 - t
                polys[-1].append((u**3*p0[0]+3*u*u*t*a[0]+3*u*t*t*b[0]+t**3*c[0], u**3*p0[1]+3*u*u*t*a[1]+3*u*t*t*b[1]+t**3*c[1]))
        def _qCurveToOne(self, a, b):
            p0 = polys[-1][-1]
            for t in np.linspace(0, 1, 17)[1:]:
                u = 1 - t
                polys[-1].append((u*u*p0[0]+2*u*t*a[0]+t*t*b[0], u*u*p0[1]+2*u*t*a[1]+t*t*b[1]))
    q.draw(P(None))
    for poly in polys:
        if len(poly) < 3: continue
        m = Image.new("1", im.size, 0)
        ImageDraw.Draw(m).polygon([(x + OX, BASE - y) for x, y in poly], fill=1)
        im = ImageChops.logical_xor(im, m)
    return im


if __name__ == "__main__":
    ttf, out = sys.argv[1], sys.argv[2]
    font = TTFont(ttf); gs = font.getGlyphSet()
    E = json.load(open(os.path.join(WORK, "src", "geistserif_extra.json")))
    cells = []
    for key, g in E.items():
        if not g["contours"]:
            adv = font["hmtx"][g["glyph"]][0]
            print("%-11s advance json %d ttf %d" % (g["glyph"], g["width"], adv)); continue
        ref = pathops.Path(); gs[g["glyph"]].draw(ref.getPen(glyphSet=gs))
        a, b = raster(json_path(g["contours"])), raster(ref)
        x = ImageChops.logical_xor(a, b)
        ar, ax = np.array(b).sum(), np.array(x).sum()
        print("%-11s xor %5d u2  area %6d  mismatch %.2f%%  advance json %d ttf %d" % (g["glyph"], ax, ar, 100 * ax / ar, g["width"], font["hmtx"][g["glyph"]][0]))
        cells.append((g, b, x, 100 * ax / ar))
    cw, ch, S = 420, 560, 0.4
    sheet = Image.new("RGB", (cw * len(cells), ch), (255, 255, 255)); d = ImageDraw.Draw(sheet)
    for i, (g, b, x, mm) in enumerate(cells):
        cell = Image.new("RGB", (W, H), (255, 255, 255))
        cell.paste((200, 200, 200), mask=b.convert("L")); cell.paste((230, 30, 30), mask=x.convert("L"))
        dd = ImageDraw.Draw(cell)
        for c in g["contours"]:
            for nd in c["nodes"]:
                if nd[2] != 'o':
                    px, py = nd[0] + OX, BASE - nd[1]; dd.rectangle([px - 4, py - 4, px + 4, py + 4], fill=(0, 140, 60))
        sheet.paste(cell.resize((int(W * S), int(H * S)), Image.LANCZOS), (i * cw, 30))
        d.text((i * cw + 10, 8), "%s  %.2f%% XOR" % (g["glyph"], mm), fill=(0, 0, 0))
    d.text((10, ch - 16), "grey = exported TTF, red = XOR against the expanded cubic outline, green = on-curve nodes", fill=(0, 0, 0))
    sheet.save(out); print("sheet", out)
