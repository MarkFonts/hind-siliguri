"""Step 7: what stress is left. The thin axis of each round part (conventions/tools/thickness.py: normal-ray field,
th(phi) = a + b cos 2(phi - phi0) fitted about the part's centre; angle from vertical, + = top leans right) on Mark's
drawn roman and italic, the plain slant, round 4 and round 5, all at 14.04 deg; o, the p bowl, the a bowl, the s bowls.
The stem side of p and a is masked out (a straight stem has no stress). e and n are unfinished drawings: not read.

stress.py  -> readings/stress_14.json, printed table
"""
import sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "conventions", "tools")))
import carry as C
C.set_slant(0.25)
import drawn
from round5 import correct
import thickness as TH
class _G:
    """our contours as the conventions kit's glyph: a contour = [{pt, in, out}] on-curve nodes with their handles"""
    def __init__(self, cs, name):
        self.name = name; self.contours = []
        for c in cs:
            ns = c["nodes"]; N = len(ns); out = []
            for i, n in enumerate(ns):
                if n[2] == "o":
                    continue
                pv, nx = ns[(i - 1) % N], ns[(i + 1) % N]
                out.append(dict(pt=(n[0], n[1]), **{"in": (pv[0], pv[1]) if pv[2] == "o" else None,
                                                     "out": (nx[0], nx[1]) if nx[2] == "o" else None}))
            self.contours.append(out)


def G_(cs, name):
    return _G(cs, name)


def parts_of(gl, G, slanted):
    """[(name, centre, rmin, rmax, mask fn)]: each round part's centre from the skeleton's runs on the upright (the
    counter run's box centre), carried by the shear when the copy is slanted (I10 keeps a part's centre there)"""
    from skeleton import Skeleton
    Sk = Skeleton(G["GeistSerifRegular_" + gl])
    K = C.K if slanted else 0.0
    cen = lambda c: (float(c[0] + K * c[1]), float(c[1]))
    runs = [r for r in Sk.runs if r["counter"]]
    if gl == "o":
        r = runs[0]; c = cen(r["c"]); return [("o", c, 60, 320, None)]
    if gl == "p":
        r = runs[0]; c = cen(r["c"]); x0 = c[0] - 30
        return [("p bowl", c, 40, 300, lambda P, x0=x0: P[:, 0] > x0)]
    if gl == "a":
        r = min(runs, key=lambda r: r["c"][1]); c = cen(r["c"]); x1 = c[0] + 40
        return [("a bowl", c, 40, 260, lambda P, x1=x1: P[:, 0] < x1)]
    if gl == "s":
        lo = min(runs, key=lambda r: r["c"][1]); hi = max(runs, key=lambda r: r["c"][1])
        cl, ch = cen(lo["c"]), cen(hi["c"])
        ym = (cl[1] + ch[1]) / 2
        return [("s upper", ch, 30, 230, lambda P, ym=ym: P[:, 1] > ym + 40), ("s lower", cl, 30, 230, lambda P, ym=ym: P[:, 1] < ym - 40)]


def read(gl, cs, ref):
    F = TH.ray_field(G_(cs, gl), step=3.0)
    out = {}
    for name, c, r0, r1, mfn in ref:
        m = None if mfn is None else mfn(F.centre)
        s = TH.stress(F, c, r0, r1, mask=m)
        out[name] = None if s is None else dict(thin=round(s["thin_axis_deg"], 1), amp=round(s["amp"], 1), resid=round(s["resid"], 1), n=s["n"])
    return out


def main():
    G = C.load(); R4 = json.load(open(os.path.join(C.R5, "src", "geistserif_italic.json")))
    res = {}
    for gl in ("o", "p", "a", "s"):
        sl = G["GeistSerifSlant_" + gl]["contours"]
        up = G["GeistSerifRegular_s.anchors" if gl == "s" else "GeistSerifRegular_" + gl]["contours"]
        pu, ps = parts_of(gl, G, False), parts_of(gl, G, True)
        rows = dict(drawn_roman=read(gl, drawn.letter(gl, "roman", up)["contours"], pu),
                    our_roman=read(gl, G["GeistSerifRegular_" + gl]["contours"], pu),
                    slant=read(gl, sl, ps),
                    round4=read(gl, R4["GeistSerifItalic_" + gl]["contours"], ps),
                    round5=read(gl, correct(gl, G, "1-6")["contours"], ps),
                    drawn_italic=read(gl, drawn.letter(gl, "italic", sl)["contours"], ps))
        res[gl] = rows
        for part in rows["slant"]:
            print("%-8s %s" % (part, "  ".join("%s %s" % (k, ("%+.1f° (amp %.0f, resid %.0f)" % (v[part]["thin"], v[part]["amp"], v[part]["resid"])) if v.get(part) else "-")
                                           for k, v in rows.items())))
    json.dump(res, open(os.path.join(C.R5, "readings", "stress_14.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
