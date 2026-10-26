"""Mark's drawn italic s o p (the Glyphs print PDF of 2026-10-25, 250 pt) over the solver's corrected and the plain slant.
The PDF draws the letters as paths in its content stream; pdf_paths.json is the parsed path list (scratchpad walker).

mark_sop.py [PDFPATHS.json] [--out PNG]
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bowls_sheet import path_of
import skia
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src", "geistserif_italic.json")
MENLO = "/System/Library/Fonts/Menlo.ttc"
S = 4.0                       # units per pt at 250 pt
def groups_of(paths):
    """subpaths grouped into letters left to right: a subpath whose x-range lies inside the previous letter's is its counter"""
    boxes = []
    for i, p in enumerate(paths):
        xs = [q[-1][0] for q in p if len(q) > 1]
        if len(xs) > 2: boxes.append((min(xs), max(xs), i))
    boxes.sort(); letters = []
    for x0, x1, i in boxes:
        if letters and x0 >= letters[-1][0] and x1 <= letters[-1][1]: letters[-1][2].append(i)
        else: letters.append([x0, x1, [i]])
    return {gl: L[2] for gl, L in zip(["s", "o", "p"], letters)}
GROUPS = None


def skpath(paths, idx, base_pt):
    p = skia.Path(); p.setFillType(skia.PathFillType.kWinding)
    for i in idx:
        cur = None
        for q in paths[i]:
            if q[0] == "m": p.moveTo(q[1][0] * S, (q[1][1] - base_pt) * S); cur = q[1]
            elif q[0] == "l": p.lineTo(q[1][0] * S, (q[1][1] - base_pt) * S); cur = q[1]
            elif q[0] == "c":
                c1 = q[1] if q[1] else cur
                p.cubicTo(c1[0] * S, (c1[1] - base_pt) * S, q[2][0] * S, (q[2][1] - base_pt) * S, q[3][0] * S, (q[3][1] - base_pt) * S); cur = q[3]
            elif q[0] == "h": p.close()
        p.close()
    return p


def bbox(p):
    b = p.computeTightBounds(); return b.left(), b.top(), b.right(), b.bottom()


def sheet(paths, out, sc=0.5):
    global GROUPS
    GROUPS = groups_of(paths)
    G = json.load(open(SRC))
    base_pt = min(q[-1][1] for q in paths[GROUPS["o"][0]] if len(q) > 1) + 12 / S     # the o's overshoot = -12 u
    cols = [("Mark's drawn italic (print PDF)", "fill"), ("solver corrected (green) over Mark's", "mine"), ("plain slant (red) over Mark's", "slant")]
    CW = int(760 * sc); colw = CW * 3 + 60; RH = int(1000 * sc) + 90
    W, H = colw * 3 + 40, RH + 60
    surf = skia.Surface(W, H); cv = surf.getCanvas(); cv.clear(skia.Color(13, 13, 13))
    labels = []; rows = []
    for ci, (title, mode) in enumerate(cols):
        x0 = 20 + ci * colw; labels.append((x0, 16, title))
        for li, gl in enumerate(["s", "o", "p"]):
            mp = skpath(paths, GROUPS[gl], base_pt); mb = bbox(mp)
            mine = path_of(G["GeistSerifItalic_" + gl]); ib = bbox(mine)
            slant = path_of(G["GeistSerifSlant_" + gl]); sb = bbox(slant)
            dx = (ib[0] + ib[2]) / 2 - (mb[0] + mb[2]) / 2            # Mark's aligned on mine by bbox centre, both on their baseline
            mp2 = skia.Path(); mp2.addPath(mp, dx, 0)
            ox = x0 + 30 + li * CW - ib[0] * sc; oy = 60 + 800 * sc
            layers = [(mp2, (200, 200, 200), None)] if mode == "fill" else \
                     [(mp2, (75, 75, 75), None), (mine if mode == "mine" else slant, None, (90, 215, 110) if mode == "mine" else (235, 70, 55))]
            for pth, fill, stroke in layers:
                cv.save(); cv.translate(ox, oy); cv.scale(sc, -sc)
                if fill: cv.drawPath(pth, skia.Paint(AntiAlias=True, Color=skia.Color(*fill)))
                if stroke: cv.drawPath(pth, skia.Paint(AntiAlias=True, Color=skia.Color(*stroke), Style=skia.Paint.kStroke_Style, StrokeWidth=2.5 / sc))
                cv.restore()
            if ci == 0:
                rows.append("%s: width Mark %.0f u · corrected %.0f · slant %.0f" % (gl, mb[2] - mb[0], ib[2] - ib[0], sb[2] - sb[0]))
    im = Image.frombytes("RGBA", (W, H), surf.makeImageSnapshot().tobytes()).convert("RGB"); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(MENLO, 22)
    for X, Y, t in labels: d.text((X, Y), t, fill=(232, 184, 74), font=f)
    d.text((20, H - 34), "   ·   ".join(rows) + "   ·   each pair on its baseline, aligned by bbox centre", fill=(170, 170, 170), font=ImageFont.truetype(MENLO, 19))
    im.save(out); print("wrote", out, im.size)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="?", default="/private/tmp/claude-502/-Users-Mark-Documents-Github/bf271dff-92b2-436c-94bd-a92c2f4aefbf/scratchpad/pdf/pdf_paths.json")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "sheets", "mark_sop_vs_solver.png"))
    a = ap.parse_args()
    sheet(json.load(open(a.paths)), a.out)
