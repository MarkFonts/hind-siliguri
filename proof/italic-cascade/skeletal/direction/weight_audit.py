"""Does the solve read each letter the same way in Light and Bold? (Mark 2026-11-20: "you are affecting BOTH the OUTer
curve and INNER curve of hind lgiht BPR INSIDE and in BOLD you ARENT", "why are things so random".) The two masters have
the same points in the same order, so every curve should get the same reading in both. This lists every curve that
does not. Run with the same switches as the build (FOOT, BAR, KEEP).
  python weight_audit.py [latin|all]"""
import os, sys, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE)
if HERE not in sys.path: sys.path.insert(0, HERE)
import round_solve as RS
St = pickle.load(open(os.path.join(SK, "work", "vf_state.pkl"), "rb"))
names = sorted(k[1] for k in St if k[0] == "Light")
if (sys.argv[1] if len(sys.argv) > 1 else "latin") == "latin": names = [n for n in names if not n.startswith("bn")]
SAME = os.environ.get("SAME", "0") == "1"
def reading(m, nm):
    if SAME: RS.shared_reading(nm, [St[(mm, nm)]["g"] for mm in ("Light", "Bold")])
    cn, log = RS.round_stored(dict(St[(m, nm)]["g"], glyph=nm)); R = {}
    for r in log: R.setdefault((r[0], r[1]), set()).add(("%s %s" % (r[2], r[3])) if r[2] not in ("join", "bar") else r[3])
    return R
bad = {}
for nm in names:
    a, b = reading("Light", nm), reading("Bold", nm)
    d = [(k, sorted(a.get(k, [])), sorted(b.get(k, []))) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
    if d: bad[nm] = d
print("letters read the same in both weights: %d of %d" % (len(names) - len(bad), len(names)))
for nm, d in bad.items():
    print("  %s:" % nm, "; ".join("curve c%d.%d Light %s / Bold %s" % (k[0], k[1], x or ["nothing"], y or ["nothing"]) for k, x, y in d)[:400])
