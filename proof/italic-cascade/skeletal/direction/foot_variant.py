"""Rebuild only the named letters with the current switches and lay them over a base pickle (Mark 2026-11-21, on the
foot of d and g: "the foot doesnt might not need to touch the counter?"). Process: obliquing.
  FOOT=1 FOOT_ONLY="d g" FOOT_COUNTER=0 python foot_variant.py <base.pkl> <out.pkl> d g"""
import os, sys, pickle, copy, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE)
if HERE not in sys.path: sys.path.insert(0, HERE)
import round_all as RA
base = pickle.load(open(os.path.join(HERE, sys.argv[1]), "rb")); St = pickle.load(open(os.path.join(SK, "work", "vf_state.pkl"), "rb")); out = copy.deepcopy(base)
for m in ("Light", "Bold"):
    for nm in sys.argv[3:]:
        g = dict(St[(m, nm)]["g"]); g["glyph"] = nm; cn, how, steps = RA.solve(g, m)
        a = np.array([[n[0], n[1]] for c in cn for n in c["nodes"]]); b = np.array([[n[0], n[1]] for c in base[m][nm]["final"] for n in c["nodes"]])
        d = np.abs(a - b).max(axis=1); print(m, nm, how, "+".join(steps), "| points changed:", [int(i) for i in np.where(d > .05)[0]], "largest %.1f" % d.max())
        out[m][nm] = dict(final=cn, how=how, steps=steps)
pickle.dump(out, open(os.path.join(HERE, sys.argv[2]), "wb"))
