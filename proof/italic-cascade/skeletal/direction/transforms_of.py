"""Mark 2026-11-21: "can you give me the transformations being applied to bpdqg and o?" Process: obliquing.
Reads, for each letter and weight of the working base, what each step does: the round solve's own log (which curve is
read as what, about which corner, by how much), then what the evening and the build's later steps add, as moves of the
points with the slant taken out. Prints; writes nothing.
  FOOT=1 FOOT_ONLY="d g" python transforms_of.py [letters]"""
import os, sys, pickle, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE)
if HERE not in sys.path: sys.path.insert(0, HERE)
import cand, cascade as C, stored as ST
import round_solve as RS, round_all as RA
BASE = pickle.load(open(os.path.join(HERE, os.environ.get("PKL", "round_all_base_2026-11-21_mn3.pkl")), "rb"))
St = pickle.load(open(os.path.join(SK, "work", "vf_state.pkl"), "rb")); K, Y0 = .25, 253.5
flat = lambda cs: np.array([[n[0], n[1]] for c in cs for n in c["nodes"]], float)
def un(a): b = a.copy(); b[:, 0] = a[:, 0] - K * (a[:, 1] - Y0); return b
for name in (sys.argv[1:] or list("bpdqgo")):
    for m in ("Light", "Bold"):
        st = St[(m, name)]; g = dict(st["g"]); g["glyph"] = name; up = flat(g["contours"]); typ = [n[2] for c in g["contours"] for n in c["nodes"]]
        ci_of = [ci for ci, c in enumerate(g["contours"]) for _ in c["nodes"]]
        RS.EVEN = "0"; raw, log = RS.round_stored(dict(g)); RS.EVEN = "2"; ev, _ = RS.round_stored(dict(g))
        fin, how, steps = RA.solve(g, m); base = BASE[m][name]["final"]
        print("\n=== %s %s  width %s  points %d  steps: %s" % (m, name, g["width"], len(up), "+".join(steps)))
        print("   rebuilt equals the working base: max difference %.3f" % np.abs(flat(fin) - flat(base)).max())
        for ci, c in enumerate(g["contours"]):
            segs = ST.segments(c); P = [ST.un(np.array(ST.seg_ctrl(ST.shear([c], ST.HIND_K, ST.HIND_Y0)[0], s), float)) for s in segs]
            off = sum(len(x["nodes"]) for x in g["contours"][:ci])
            print("  contour %d: %d curves/lines" % (ci, len(segs)))
            for k, s in enumerate(segs):
                l = [x for x in log if x[0] == ci and x[1] == k]
                p = P[k]; kind = "curve" if len(s[1]) == 2 else "line"
                q = ST._corner(p) if kind == "curve" else None
                print("    %2d %-5s pts %d>%d  (%.0f,%.0f)>(%.0f,%.0f)  corner %s  %s" % (k, kind, off + s[0], off + s[2], p[0][0], p[0][1], p[-1][0], p[-1][1], "(%.0f,%.0f)" % tuple(q) if q is not None else "-", "; ".join("%s %s %s" % x[2:] for x in l)))
        a, b, c_, d = un(flat(raw)) - up, un(flat(ev)) - up, un(flat(fin)) - up, None
        print("  on-curve points, move from the plain slant (slant taken out): solve alone | + evening | final")
        for i in range(len(up)):
            if typ[i] == "o": continue
            print("    pt %2d c%d (%4.0f,%4.0f)  %6.1f,%6.1f | %6.1f,%6.1f | %6.1f,%6.1f" % (i, ci_of[i], up[i][0], up[i][1], a[i][0], a[i][1], b[i][0], b[i][1], c_[i][0], c_[i][1]))
