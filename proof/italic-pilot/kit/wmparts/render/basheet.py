"""Before/after panels at CNTR 100 (round 5): BEFORE (e.g. an older ruleset's moved contours) | AFTER (this one's),
drawn outline dashed under both, node numbers, crossings ringed. The round-by-round driver that reads dumped states
from out/ is tools/basheet.py."""
import sys, os, json
from PIL import Image
from ..font import load_set
from ..groupmove import GroupMover
from .draw import fontlabel, Panel, BG, SS, font, CAL, MENLO
from .partsheet import draw_poly
from ..rungs import Outline
from .. import crosscheck

CROSSC = (60, 230, 255)


def ring_crosses(A, crosses, f):
    for c in crosscheck.counted(crosses):
        x0, y0, x1, y1 = c["bbox"]
        p0, p1 = A.pt((x0 - 6, y1 + 6)), A.pt((x1 + 6, y0 - 6))
        A.d.ellipse([p0[0], p0[1], p1[0], p1[1]], outline=CROSSC, width=int(2.2 * SS))
        A.d.text((p1[0] + 3 * SS, p0[1]), crosscheck.label(c), fill=CROSSC, font=f)


INFOC = (150, 150, 255)


def ring_infos(A, crosses, f):
    for c in crosscheck.infos(crosses):
        x0, y0, x1, y1 = c["bbox"]
        p0, p1 = A.pt((x0 - 6, y1 + 6)), A.pt((x1 + 6, y0 - 6))
        A.d.ellipse([p0[0], p0[1], p1[0], p1[1]], outline=INFOC, width=int(1.2 * SS))
        A.d.text((p1[0] + 3 * SS, p0[1]), crosscheck.label(c), fill=INFOC, font=f)


def panel(g, contours, bb, title, sub, W, H, M=None, info=True):
    A = Panel(W, H, bb, margin=24)
    olt = Outline(contours)
    A.fill_outline(olt, color=(60, 72, 48), edge=(190, 190, 190))
    for poly in Outline(g["contours"]).polys:
        draw_poly(A, poly + [poly[0]], (150, 150, 150), 0.8, dash=6)
    A.nodes(olt, labels=True)
    cr = crosscheck.check(g["contours"], contours, held=crosscheck.held_polys(M) if M is not None else None)
    ring_crosses(A, cr, font(MENLO, 10))
    if info:
        ring_infos(A, cr, font(MENLO, 10))
    A.d.rectangle([0, 0, A.im.width, 48 * SS], fill=BG)
    A.title(title, sub)
    return A.out()


def before_after(g, before, after, bb=None, W=620, H=640, M=None, labels=("BEFORE", "AFTER"), t=100):
    """-> PIL image: two panels of one glyph at CNTR t, `before` | `after` (contour lists, e.g. an older ruleset's
    contours_at(1.0) and this one's), drawn outline dashed under both, crossings / folds ringed (crosscheck)."""
    if bb is None:
        xs = [n[0] for c in g["contours"] for n in c["nodes"]]; ys = [n[1] for c in g["contours"] for n in c["nodes"]]
        bb = (min(xs) - 40, min(ys) - 40, max(xs) + 40, max(ys) + 40)
    name = fontlabel(g)
    sub = "dashed = drawn · cyan ring = crossing / fold · violet = fold inside a held serif (info)"
    b = panel(g, before, bb, "%s · CNTR %d %s" % (name, t, labels[0]), sub, W, H, M=M)
    a = panel(g, after, bb, "%s · CNTR %d %s" % (name, t, labels[1]), sub, W, H, M=M)
    im = Image.new("RGB", (2 * W, H), BG)
    im.paste(b, (0, 0)); im.paste(a, (W, 0))
    return im


def before_after_sheet(pairs, out=None, cols=2):
    """pairs: [PIL image from before_after()] -> one sheet, cols pairs wide"""
    W, H = pairs[0].width, pairs[0].height
    sheet = Image.new("RGB", ((W + 10) * cols + 10, (H + 10) * ((len(pairs) + cols - 1) // cols) + 10), BG)
    for i, im in enumerate(pairs):
        sheet.paste(im, (10 + (i % cols) * (W + 10), 10 + (i // cols) * (H + 10)))
    if out:
        sheet.save(out)
    return sheet
