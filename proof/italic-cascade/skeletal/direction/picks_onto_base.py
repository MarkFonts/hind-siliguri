"""Put a pasted picker list back onto the working base (Mark 2026-11-21: "add back the a: 0 1 2@6,19 19@6,29 20@2,9
21 22 28@32,0 31@49,0 37"). Process: obliquing.
Light: the list exactly as given (a bare index holds the point on the plain slant; index@dx,dy moves it from where the
base draws it). The list was made on the Light, so for the Bold the same points take the same thing in proportion: each
picked point ends at the same share of its own (drawn - plain slant) as in the Light, per axis (a hold is share 0).
  python picks_onto_base.py <picks.txt> [base.pkl]  -> <base>_picks.pkl (every letter, both weights)"""
import os, re, sys, copy, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE)
PICKS = os.path.abspath(sys.argv[1]); BASE = sys.argv[2] if len(sys.argv) > 2 else "round_all_base_2026-11-21.pkl"
St = pickle.load(open(os.path.join(SK, "work", "vf_state.pkl"), "rb")); RA = pickle.load(open(os.path.join(HERE, BASE), "rb")); OUT = copy.deepcopy(RA)
flat = lambda cs: [n for c in cs for n in c["nodes"]]
for line in open(PICKS):
    line = line.strip()
    if not line or line.startswith("#"): continue
    name, rest = line.split(":", 1); name = name.strip(); picks = {}
    for tok in rest.split():
        mm = re.fullmatch(r"(\d+)(?:@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?))?", tok); assert mm, tok
        picks[int(mm.group(1))] = (float(mm.group(2)), float(mm.group(3))) if mm.group(2) else None
    L = flat(OUT["Light"][name]["final"]); Lp = flat(St[("Light", name)]["plain"]); B = flat(OUT["Bold"][name]["final"]); Bp = flat(St[("Bold", name)]["plain"])
    assert len(L) == len(B) and max(picks) < len(L)
    for i, mv in picks.items():
        drawn = (L[i][0], L[i][1]); want = (Lp[i][0], Lp[i][1]) if mv is None else (drawn[0] + mv[0], drawn[1] + mv[1])
        share = [((want[a] - Lp[i][a]) / (drawn[a] - Lp[i][a])) if abs(drawn[a] - Lp[i][a]) >= 3 else 0.0 for a in (0, 1)]
        L[i][0], L[i][1] = want
        bd = (B[i][0], B[i][1]); B[i][0], B[i][1] = Bp[i][0] + share[0] * (bd[0] - Bp[i][0]), Bp[i][1] + share[1] * (bd[1] - Bp[i][1])
        print("%s point %2d: Light ends (%+5.1f,%+5.1f) from the plain slant; Bold (%+5.1f,%+5.1f)" % (name, i, L[i][0] - Lp[i][0], L[i][1] - Lp[i][1], B[i][0] - Bp[i][0], B[i][1] - Bp[i][1]))
out = os.path.join(HERE, BASE.replace(".pkl", "_picks.pkl")); pickle.dump(OUT, open(out, "wb")); print(out)
