import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hind_kit as H
from sheets import *
PILOT = os.path.dirname(HERE)
master, gl, out = sys.argv[1], sys.argv[2], sys.argv[3]
opts = dict(a.split("=") for a in sys.argv[4:])
if "i16" in opts:
    import round_p2; _c = round_p2.correct
    round_p2.correct = lambda *a, **k: _c(*a, **dict(k, i16=opts["i16"] == "1"))
G = json.load(open(os.path.join(PILOT, "work", "upright_%s.json" % master)))
g = G[gl]; res = H.correct_glyph(g, master)
sl = H.sheared(g["contours"], shift=H.SHIFT); it = H.shift_cs(res["contours"], H.SHIFT)
s = 1.1
sh = Sheet(2400, 1200)
sh.header("HIND SILIGURI", master + " Italic (pilot zoom)", "%s  gate %s %s" % (gl, res["gate"]["ok"], res["gate"]["hump_where"]))
sh.glyph(sl, 60, 1000, s, SL_C); sh.nodes(sl, 60, 1000, s)
sh.glyph(it, 1260, 1000, s, IT_C); sh.comb(it, 1260, 1000, s, INK); sh.nodes(it, 1260, 1000, s)
sh.save(out); print(res["info"])
