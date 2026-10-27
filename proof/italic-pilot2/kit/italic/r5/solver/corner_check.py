"""Verify geistserif.json (Regular master) against Glyphs' exported TTF: raster XOR + side-by-side sheet.
corner_check.py [json] [ttf] [outdir_png]"""
import sys, json, math
import numpy as np, pathops
from PIL import Image, ImageDraw, ImageChops, ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
HERE = "/private/tmp/claude-502/-Users-Mark-Documents-Github/1390710e-1654-4392-a465-3fce7c767a3d/scratchpad/"
J = sys.argv[1] if len(sys.argv) > 1 else HERE + "src/geistserif.json"
TTF = sys.argv[2] if len(sys.argv) > 2 else HERE + "src/GeistSerif-Regular.ttf"
OUT = sys.argv[3] if len(sys.argv) > 3 else HERE + "out/sheets/geistserif/corner_check.png"
LETTERS = "f j H n a E T r v e y k x".split()
W, H, OX, BASE = 1200, 1400, 150, 1050

def json_path(contours):
    p = pathops.Path(); pen = p.getPen()
    for c in contours:
        nodes = c["nodes"]; n = len(nodes)
        # start at an on-curve node; its preceding off-curves are at the end of the list
        s = next(i for i, nd in enumerate(nodes) if nd[2] != 'o')
        order = nodes[s:] + nodes[:s]
        pen.moveTo(tuple(order[0][:2])); buf = []
        for nd in order[1:] + [order[0]]:
            if nd[2] == 'o': buf.append(tuple(nd[:2]))
            elif nd[2] == 'l': pen.lineTo(tuple(nd[:2])); buf = []
            else:
                pen.curveTo(buf[0], buf[1], tuple(nd[:2])); buf = []
        pen.closePath()
    return p

def ttf_path(font, name):
    gs = font.getGlyphSet(); p = pathops.Path(); gs[name].draw(p.getPen(glyphSet=gs)); return p

def flatten(path):
    """pathops path -> list of polygons (flattened curves)."""
    polys = []; cur = []
    from fontTools.pens.recordingPen import RecordingPen
    rp = RecordingPen(); path.draw(rp)
    for verb, pts in rp.value:
        if verb == "moveTo": cur = [tuple(pts[0])]
        elif verb == "lineTo": cur.append(pts[0])
        elif verb in ("qCurveTo",):
            ps = list(pts)
            if ps[-1] is None:      # closed contour of only off-curve points
                o = ps[:-1]; m = ((o[-1][0] + o[0][0]) / 2, (o[-1][1] + o[0][1]) / 2); cur = [m]; ps = o + [m]
            p0 = cur[-1]
            # TrueType implied on-curve points
            offs = ps[:-1]; end = ps[-1]; segs = []
            a = p0
            for i, o in enumerate(offs):
                nxt = end if i == len(offs) - 1 else ((o[0] + offs[i + 1][0]) / 2, (o[1] + offs[i + 1][1]) / 2)
                segs.append((a, o, nxt)); a = nxt
            for a, o, b in segs:
                for t in np.linspace(0, 1, 25)[1:]:
                    cur.append(((1-t)**2*a[0]+2*(1-t)*t*o[0]+t*t*b[0], (1-t)**2*a[1]+2*(1-t)*t*o[1]+t*t*b[1]))
        elif verb == "curveTo":
            p0 = cur[-1]; c1, c2, p3 = pts
            for t in np.linspace(0, 1, 25)[1:]:
                u = 1 - t
                cur.append((u**3*p0[0]+3*u*u*t*c1[0]+3*u*t*t*c2[0]+t**3*p3[0], u**3*p0[1]+3*u*u*t*c1[1]+3*u*t*t*c2[1]+t**3*p3[1]))
        elif verb == "closePath":
            polys.append(cur); cur = []
        elif verb == "endPath":
            polys.append(cur); cur = []
    return polys

def raster(path, scale=1):
    q = pathops.Path(path); q.simplify(fix_winding=True)
    im = Image.new("1", (W * scale, H * scale), 0)
    for poly in flatten(q):
        if len(poly) < 3: continue
        m = Image.new("1", im.size, 0)
        ImageDraw.Draw(m).polygon([((x + OX) * scale, (BASE - y) * scale) for x, y in poly], fill=1)
        im = ImageChops.logical_xor(im, m)
    return im

def outline_img(contours, size, scale):
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    return None

def main():
    data = json.load(open(J)); font = TTFont(TTF)
    rows = []; cells = []
    for g in LETTERS:
        k = "GeistSerifRegular_" + g
        mine = json_path(data[k]["contours"]); ref = ttf_path(font, g)
        a = raster(mine); b = raster(ref)
        x = ImageChops.logical_xor(a, b)
        area_ref = np.array(b).sum(); area_x = np.array(x).sum()
        rows.append((g, int(area_x), int(area_ref), 100.0 * area_x / area_ref, sum(len(c["nodes"]) for c in data[k]["contours"])))
        cells.append((g, a, b, x, mine))
    print("glyph  xor_units2  glyph_area  mismatch%  nodes")
    for r in rows: print("%-5s %9d %11d %9.2f%%  %d" % r)
    # sheet: 4 columns x 4 rows, crop each to a common 560x720 window (units x 0.5)
    S = 0.62; cw, ch = 520, 640
    cols = 5; nrows = math.ceil(len(cells) / cols)
    sheet = Image.new("RGB", (cols * cw, nrows * ch), (255, 255, 255)); dr = ImageDraw.Draw(sheet)
    for i, (g, a, b, x, mine) in enumerate(cells):
        ox, oy = (i % cols) * cw, (i // cols) * ch
        box = (OX - 40, BASE - 800, OX + 840, BASE + 280)     # units window
        def cr(im): return im.crop(box).convert("L").resize((int((box[2]-box[0]) * S), int((box[3]-box[1]) * S)), Image.LANCZOS)
        cell = Image.new("RGB", (cw, ch), (255, 255, 255))
        gray = ImageChops.invert(cr(b).point(lambda v: 0 if v < 128 else 255).convert("L"))   # 255 where ttf filled
        gray = cr(b).point(lambda v: 255 if v > 127 else 0)
        base = Image.new("RGB", gray.size, (255, 255, 255)); base.paste((200, 200, 200), mask=gray)
        red = cr(x).point(lambda v: 255 if v > 30 else 0); base.paste((230, 30, 30), mask=red)
        # my outline in colour (flattened polygons, full-res then scaled)
        d2 = ImageDraw.Draw(base)
        q = pathops.Path(mine); 
        for poly in flatten(mine):
            pts = [((px + OX - box[0]) * S, (BASE - py - box[1]) * S) for px, py in poly]
            d2.line(pts + [pts[0]], fill=(20, 60, 220), width=1)
        for c in data["GeistSerifRegular_" + g]["contours"]:
            for nd in c["nodes"]:
                if nd[2] != 'o':
                    px, py = (nd[0] + OX - box[0]) * S, (BASE - nd[1] - box[1]) * S
                    d2.rectangle([px - 1.5, py - 1.5, px + 1.5, py + 1.5], fill=(0, 140, 60))
        sheet.paste(base, (ox + 10, oy + 30))
        r = rows[i]
        dr.text((ox + 12, oy + 8), "%s  xor %d u2  %.2f%%  (%d nodes)" % (g, r[1], r[3], r[4]), fill=(0, 0, 0))
    dr.text((10, nrows * ch - 14), "grey = exported TTF, blue = expanded cubic outline (green = on-curve nodes), red = XOR", fill=(0, 0, 0))
    sheet.save(OUT); print("sheet", OUT)

main()
