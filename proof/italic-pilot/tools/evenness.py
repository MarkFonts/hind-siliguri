"""stroke evenness check: the upright's rungs carried node for node; mean |width - upright width| on slant vs corrected,
and the ratio by stroke direction (for the report; the sheets are the result)"""
import json, sys, os, numpy as np, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hind_kit as H
import carry as C
from proof import LAT, BN
W = os.path.join(os.path.dirname(HERE), "work")
out = {}
for m in ("Light", "Bold"):
    UP = json.load(open(os.path.join(W, "upright_%s.json" % m))); IT = json.load(open(os.path.join(W, "italic_%s.json" % m)))
    H.STATE["master"] = m
    agg = {"lat": collections.defaultdict(list), "bn": collections.defaultdict(list)}
    per = {}
    for gl in LAT + BN:
        g = UP[gl]
        if not g["contours"]: continue
        H.STATE["cls"][gl] = H.glyph_class(g)
        try:
            P = C.parts_of({"contours": g["contours"], "master": "Regular", "glyph": gl})
            R = C.Rungs(P)
            wu = R.widths(g["contours"]); ws = R.widths(H.sheared(g["contours"])); wi = R.widths(H.shift_cs(IT[gl]["contours"], -H.SHIFT))
        except Exception as e:
            per[gl] = repr(e)[:80]; continue
        es, ei = [], []
        key = "bn" if gl.startswith("bn") else "lat"
        for r, a, b, c in zip(R.rungs, wu, ws, wi):
            if r["kind"] == "root" or a["w"] < 0.4 * H.METRICS[m]["stem"][H._cls(gl)] or a["w"] > 2.2 * H.METRICS[m]["stem"][H._cls(gl)]:
                continue
            d = C.direction_class(a["t"])
            agg[key][d].append((b["w"] / a["w"], c["w"] / a["w"]))
            es.append(abs(b["w"] - a["w"])); ei.append(abs(c["w"] - a["w"]))
        per[gl] = (round(float(np.mean(es)), 2), round(float(np.mean(ei)), 2)) if es else None
    out[m] = per
    for key in agg:
        print(m, key, {d: "%.3f -> %.3f (n %d)" % (np.mean([x[0] for x in v]), np.mean([x[1] for x in v]), len(v)) for d, v in agg[key].items()})
json.dump(out, open(os.path.join(W, "evenness.json"), "w"), indent=0)
for m in out:
    print(m, " ".join("%s %s" % (g, v) for g, v in out[m].items()))
