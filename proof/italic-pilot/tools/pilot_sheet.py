"""pilot check: upright | raw slant | corrected | overlay | comb (slant) | comb (corrected), one row per glyph"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hind_kit as H
from sheets import *
PILOT = os.path.dirname(HERE)
glyphs = sys.argv[2].split(","); out = sys.argv[3]
master = sys.argv[1]
G = json.load(open(os.path.join(PILOT, "work", "upright_%s.json" % master)))
s = 0.28; cw = 330; rh = 330
sh = Sheet(60 + 6 * cw, 200 + rh * len(glyphs))
sh.header("HIND SILIGURI", master + " Italic (pilot)", "14.04° (x' = x + (y − 253.5)/4) · round 5 pass 2c structure, Hind numbers")
sh.key(30, 150, [("upright", UP_C), ("raw slant", SL_C), ("corrected", IT_C), ("taken away", RED), ("added", GREEN)])
for r, gl in enumerate(glyphs):
    g = G[gl]; res = H.correct_glyph(g, master)
    up = g["contours"]; sl = H.sheared(up, shift=H.SHIFT); it = H.shift_cs(res["contours"], H.SHIFT)
    y0 = 200 + r * rh + 250
    for k, (cs, c) in enumerate(((up, UP_C), (sl, SL_C), (it, IT_C))):
        sh.glyph(cs, 40 + k * cw + 30, y0, s, c)
    sh.overlay(sl, it, 40 + 3 * cw + 30, y0, s)
    sh.glyph(sl, 40 + 4 * cw + 30, y0, s, FAINT); sh.comb(sl, 40 + 4 * cw + 30, y0, s, SL_C)
    sh.glyph(it, 40 + 5 * cw + 30, y0, s, FAINT); sh.comb(it, 40 + 5 * cw + 30, y0, s, IT_C)
    gt = res["gate"]
    sh.text(40, 200 + r * rh, "%s  gate %s  (snaps %d spikes %d humps %d)" % (gl, "PASS" if gt["ok"] else "FAIL", gt["snaps"], gt["spikes"], gt["hump"]), GREEN if gt["ok"] else RED, 16)
    for xx in range(6):
        sh.hline(40 + xx * cw + 10, 40 + xx * cw + cw - 10, y0)
sh.save(out); print(out)
