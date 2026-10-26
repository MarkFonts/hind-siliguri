"""Per-master overview: every letter at CNTR 0 / 50 / 100 (filled, drawn dashed under 50 and 100), Harvey below."""
import sys, os, json, math, traceback
from PIL import Image
from ..mover import Mover
from .draw import fontlabel, Panel, BG, SS, font, CAL
from .partsheet import draw_poly
from ..rungs import Outline

ROWS = [["f", "j", "H", "n"], ["a", "E", "T", "r"], ["v", "e", "y", "k"], ["x"]]

def strip(g, M, W, H, label=True):
    """three panels side by side for one glyph"""
    xs = [n[0] for c in g["contours"] for n in c["nodes"]]; ys = [n[1] for c in g["contours"] for n in c["nodes"]]
    bb = (min(xs) - 30, min(ys) - 30, max(xs) + 30, max(ys) + 30)
    out = Image.new("RGB", (W * 3 + 8, H), BG)
    for i, t in enumerate((0.0, 0.5, 1.0)):
        A = Panel(W, H, bb, margin=16)
        if label:
            A.title("%s · %d" % (fontlabel(g), int(t * 100)))
        ol2 = Outline(M.contours_at(t)) if M is not None else Outline(g["contours"])
        A.fill_outline(ol2, color=(78, 88, 64) if t > 0 else (60, 70, 50), edge=(150, 150, 150))
        if t > 0 and M is not None:
            for poly in M.ol.polys:
                draw_poly(A, poly + [poly[0]], (230, 230, 230), 0.9, dash=5)
        out.paste(A.out(), (i * (W + 4), 0))
    return out
