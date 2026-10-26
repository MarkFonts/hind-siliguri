"""Round 5, step 0: src/geistserif_italic_<14|18>.json = GeistSerifRegular_<g> (copied) + GeistSerifSlant_<g>
(x' = x + K*y, master "Slant") + "space", for the 19 letters + o of round 4.

The round-4 builder read core/parts/src/geistserif_extra.json and the Glyphs package copy (glyphs_corners) for the
corner-expanded Regular and the kerning; neither is in the work tree any more (the package copy is gone, the extra
file was never kept), and italic/src/geistserif_expanded.json holds only 13 of the 19 letters (no o p s B z
quoteright). So the Regular keys are taken from round 4's kept source, src/geistserif_italic.json (a frozen copy of
italic/src/geistserif_italic.json: the same corner-expanded Regular, s anchor-free with s.anchors beside it; the 13
letters in geistserif_expanded.json are byte-identical there), and the Slant keys are derived from them directly:
it is only a shear. kerning.json is round 4's (Regular master, Harper's line).

build_italic_src.py [--slant 1/3|1/4|all]        default: both files
"""
import sys, os, json
from fractions import Fraction
HERE = os.path.dirname(os.path.abspath(__file__))
R5 = os.path.abspath(os.path.join(HERE, ".."))
IN = os.path.join(R5, "src", "geistserif_italic.json")      # round 4's source, frozen copy


def shear(g, k):
    return {"contours": [{"closed": c["closed"], "nodes": [[n[0] + n[1] * k, n[1]] + list(n[2:]) for n in c["nodes"]]} for c in g["contours"]],
            "width": g["width"], "master": "Slant", "glyph": g["glyph"]}


def out_path(k):
    return os.path.join(R5, "src", "geistserif_italic_%d.json" % (14 if abs(k - 0.25) < 1e-9 else 18 if abs(k - 1 / 3) < 1e-9 else round(1000 * k)))


def build(k):
    G = json.load(open(IN))
    p = out_path(k)
    old = json.load(open(p)) if os.path.exists(p) else {}
    out = {}
    for key in sorted(G):
        if key.startswith("GeistSerifRegular_"):
            out[key] = G[key]
            gl = key.split("_", 1)[1]
            if gl.endswith(".anchors"):
                continue                       # the drawn s with its spine anchors: reference only, no slant
            out["GeistSerifSlant_" + gl] = shear(G[key], k)
            if "GeistSerifItalic_" + gl in old:
                out["GeistSerifItalic_" + gl] = old["GeistSerifItalic_" + gl]
    out["space"] = G["space"]
    json.dump(out, open(p, "w"))
    print(p, len(out), "keys")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:]]
    sl = a[a.index("--slant") + 1] if "--slant" in a else "all"
    for k in ([0.25, 1 / 3] if sl == "all" else [float(Fraction(sl))]):
        build(k)
