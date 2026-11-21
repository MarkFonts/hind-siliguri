"""The round solve on every letter the build holds (Mark 2026-11-20: "run the round solve on all the letters").
Process: obliquing. For each master and each of the build's 154 glyphs (Latin, figures, punctuation, 49 Bengali
letters): the cascade with round_solve.round_stored as its curve step, every later step kept (straights, cut handle,
lower terminal, notch, flat repair, welds, joint repair). A glyph the cascade cannot take that way falls back to the
round solve alone, then to the build's own outline; the report says which.
  python round_all.py            -> direction/round_all.pkl  {master: {name: {final, how, steps}}}  and round_all_report.json"""
import os, sys, json, pickle, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE)
if HERE not in sys.path: sys.path.insert(0, HERE)
import cand, cascade as C, stored as ST
import round_solve as RS
import diag as DG
import ocss_final as OF
import straights as SG
SAME = os.environ.get("SAME", "0") == "1"       # SAME=1: a curve is a piece of a round only if both weights read it so
NOTES = os.environ.get("NOTES", "1") == "1"      # NOTES=0: the run as sent on 2026-11-20, before his notes on diagonals and stems


def same(a, b):
    return len(a) == len(b) and all(len(x["nodes"]) == len(y["nodes"]) and all(p[2] == q[2] for p, q in zip(x["nodes"], y["nodes"])) for x, y in zip(a, b))


def finite(cs):
    return all(math.isfinite(n[0]) and math.isfinite(n[1]) for c in cs for n in c["nodes"])


def solve(g, m, extras=True):
    """-> (contours, how, steps)"""
    keep = C.stored; keep_bias = DG.bias; keep_g2 = (ST.g2r, C.g2r, OF.g2r)
    try:
        C.stored = RS.round_stored
        if RS.KEEP:
            # The build's later steps each end with its own joint evening, which SLIDES points (the "cut handle" step runs
            # it on every contour, logged or not). That is what moved the Light P's side point back and not the R's.
            # With a fixed share the points are final: those steps may even joints by handle length only.
            # ...and not even that: evening by handle length also gave the Light P and R different handles at the same
            # point (one shortened, one lengthened). No evening at all: every handle follows its own curve.
            ST.g2r = C.g2r = OF.g2r = (lambda c: c)
        if NOTES: DG.bias = SG.bias2            # Mark's notes of 2026-11-20: diagonals keep the roman's relation to the stem
        try:
            cn, lg = C.cascade(dict(g), m, extras=extras)
            if same(cn, g["contours"]) and finite(cn):
                if NOTES:                        # ...and upright straight strokes are thinned slightly
                    c2, nmv = SG.thin_stems(g, cn)
                    if nmv and same(c2, g["contours"]) and finite(c2): cn = c2; lg["steps"].append("stems thinned")
                return cn, "round solve + the build's later steps", lg["steps"]
            why = "structure changed"
        except Exception as ex:
            why = repr(ex)[:90]
        try:
            cn, _ = RS.round_stored(dict(g))
            if same(cn, g["contours"]) and finite(cn): return cn, "round solve alone (later steps failed: %s)" % why, ["base"]
        except Exception as ex:
            why += " | alone: " + repr(ex)[:90]
        return None, "kept the build's outline (%s)" % why, []
    finally:
        C.stored = keep; DG.bias = keep_bias; ST.g2r, C.g2r, OF.g2r = keep_g2


if __name__ == "__main__":
    St = pickle.load(open(os.path.join(SK, "work", "vf_state.pkl"), "rb")); out = {}; rep = {}; t0 = time.time()
    for m in ("Light", "Bold"):
        out[m] = {}; rep[m] = {}
        for nm in sorted(k[1] for k in St if k[0] == m):
            st = St[(m, nm)]; g = dict(st["g"]); g["glyph"] = nm
            if SAME: RS.shared_reading(nm, [St[(mm, nm)]["g"] for mm in ("Light", "Bold")])      # one reading for both weights
            cn, how, steps = solve(g, m)
            if cn is None: cn = st["final"]
            out[m][nm] = dict(final=cn, how=how, steps=steps); rep[m][nm] = how + (" | " + "+".join(steps) if steps else "")
    # the font needs each glyph to keep one structure in both masters
    pickle.dump(out, open(os.path.join(HERE, os.environ.get("PKL", "round_all.pkl")), "wb")); json.dump(rep, open(os.path.join(HERE, "round_all_report.json"), "w"), indent=0, ensure_ascii=False)
    from collections import Counter
    for m in out:
        c = Counter(v["how"].split(" (")[0] for v in out[m].values()); print(m, dict(c))
        for nm, v in out[m].items():
            if not v["how"].startswith("round solve +"): print("   ", nm, "|", v["how"])
    print("%.0fs" % (time.time() - t0))
