"""Step 1: add the letters of the proof line that the solver JSON lacks (Regular master), corner and cap
components expanded exactly as extract_font.py does (tools/glyphs_corners.shapes + to_nodes, on this work
tree's COPY of the package). Writes src/geistserif_extra.json; the 13 already in src/geistserif.json are
re-expanded only to check that this route reproduces them node for node.
"""
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
import glyphs_corners as gc

REG = "DCBCDAAA-39F5-436E-B8F7-AA5CB02C428B"
EXTRA = ["p", "s", "B", "z", "quoteright"]
THIRTEEN = "f j H n a E T r v e y k x".split()


def layer(gn):
    adv, shs = gc.shapes(gn, gc.SRC, REG)
    return {"contours": [{"closed": True, "nodes": gc.to_nodes(sh)} for sh in shs], "width": float(adv),
            "master": "Regular", "glyph": gn}


if __name__ == "__main__":
    G = json.load(open(os.path.join(WORK, "src", "geistserif.json")))
    bad = []
    for gn in THIRTEEN:
        a = G["GeistSerifRegular_" + gn]["contours"]; b = layer(gn)["contours"]
        fa = [n for c in a for n in c["nodes"]]; fb = [n for c in b for n in c["nodes"]]
        same = len(fa) == len(fb) and all(x[2] == y[2] and math.dist(x[:2], y[:2]) < 1e-6 for x, y in zip(fa, fb))
        if not same: bad.append(gn)
    print("re-expansion of the 13 reproduces src/geistserif.json:", "yes" if not bad else "NO: %s" % bad)
    out = {}
    for gn in EXTRA:
        try:
            out["GeistSerifRegular_" + gn] = L = layer(gn)
            print(gn, "contours", len(L["contours"]), "nodes", [len(c["nodes"]) for c in L["contours"]], "width", L["width"])
        except Exception as e:
            print("LEFT OUT", gn, repr(e))
    out["GeistSerifRegular_space"] = {"contours": [], "width": float(gc.advance("space")), "master": "Regular", "glyph": "space"}
    json.dump(out, open(os.path.join(WORK, "src", "geistserif_extra.json"), "w"))
