"""pass 1's pipeline (r5/tools/round5.correct, steps 1-6, read only) at any K on pass 2's uprights (his roman s, the
Regular n ...): pass1_at_k.py K OUT.json g1,g2,...   (its own process: pass 1 and pass 2 both have a carry.py)"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
P1 = os.path.abspath(os.path.join(HERE, "..", "..", "tools"))
sys.path.insert(0, os.path.join(P1, "..", "solver")); sys.path.insert(0, P1)
import carry as C1
from round5 import correct

K = float(sys.argv[1]); out = sys.argv[2]; gls = sys.argv[3].split(",")
C1.set_slant(K)
G = json.load(open(os.path.join(HERE, "..", "src", "geistserif_italic_18.json")))
for g in gls:
    up = G["GeistSerifRegular_" + g]
    G["GeistSerifSlant_" + g] = {"contours": [{"closed": c["closed"], "nodes": [[n[0] + K * n[1], n[1]] + list(n[2:]) for n in c["nodes"]]} for c in up["contours"]],
                                 "width": up["width"], "master": "Slant", "glyph": g}
R = {g: correct(g, G, "1-6")["contours"] for g in gls}
json.dump(R, open(out, "w")); print("pass 1 at K %.5f:" % K, ", ".join(gls))
