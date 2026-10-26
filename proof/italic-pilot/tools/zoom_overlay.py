import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from sheets import *
from proof import resolve, LEVEL
master, out = sys.argv[1], sys.argv[2]; gls = sys.argv[3].split(",")
s = 0.75
sh = Sheet(80 + len(gls) * 760, 1000)
sh.header("HIND SILIGURI", master + " Italic · overlay zoom", "raw slant vs corrected, solid: grey both, red taken away, green added")
sh.key(30, 120, [("in both", GREY), ("taken away", RED), ("added", GREEN)])
for i, gl in enumerate(gls):
    sh.text(40 + i * 760, 170, "%s  level %s" % (gl, LEVEL[gl]), INK, 18)
    sh.overlay(resolve(master, gl, "slant"), resolve(master, gl, "it"), 60 + i * 760, 900, s)
sh.save(out); print(out)
