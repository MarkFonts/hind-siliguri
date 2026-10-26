"""Round 5 · pass 2: pass 1's pipeline (r5/tools/round5.correct, steps 1-6, read only, unchanged) run on the new upright
s (Mark's drawn roman s) at 14.04 and 18.43 deg -> GeistSerifItalicPass1Rules_s in pass 2's src files. Runs in its own
process with r5/tools first on the path (pass 1 and pass 2 both have a carry.py)."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
P1 = os.path.abspath(os.path.join(HERE, "..", "..", "tools"))
sys.path.insert(0, os.path.join(P1, "..", "solver")); sys.path.insert(0, P1)
import carry as C1
from round5 import correct

for tag, K in (("14", 0.25), ("18", 1.0 / 3.0)):
    C1.set_slant(K)
    p = os.path.join(HERE, "..", "src", "geistserif_italic_%s.json" % tag)
    G = json.load(open(p))
    cs = correct("s", G, "1-6")["contours"]
    G["GeistSerifItalicPass1Rules_s"] = {"contours": cs, "width": G["GeistSerifRegular_s"]["width"], "glyph": "s",
                                         "master": "Italic, pass 1's rules (r5/tools) on Mark's drawn roman s"}
    json.dump(G, open(p, "w"))
    print(tag, "pass 1's rules on his s:", sum(len(c["nodes"]) for c in cs), "nodes")
