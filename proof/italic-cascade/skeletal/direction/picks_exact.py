"""Apply a pasted picker list exactly, to the weight it names (the picker now copies the weight on its own line).
Mark 2026-11-21: "m is looking good, different than Bold / m: 26 / n: 4@11,0 6@-22,-33 7@-20,-80". Process: obliquing.
A bare index holds the point on the plain slant; index@dx,dy moves it from where the base draws it. Nothing else moves,
and the other weight is not touched.
  python picks_exact.py <picks.txt> <base.pkl> <out.pkl> [weight if the list names none]"""
import os, re, sys, copy, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE)
St = pickle.load(open(os.path.join(SK, "work", "vf_state.pkl"), "rb")); RA = pickle.load(open(os.path.join(HERE, sys.argv[2]), "rb")); OUT = copy.deepcopy(RA)
w = sys.argv[4] if len(sys.argv) > 4 else None; flat = lambda cs: [n for c in cs for n in c["nodes"]]
for line in open(os.path.abspath(sys.argv[1])):
    line = line.strip()
    if not line or line.startswith("#"): continue
    if line in ("Light", "Bold"): w = line; continue
    assert w, "the list names no weight"
    name, rest = line.split(":", 1); name = name.strip(); F = flat(OUT[w][name]["final"]); P = flat(St[(w, name)]["plain"])
    for tok in rest.split():
        mm = re.fullmatch(r"(\d+)(?:@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?))?", tok); assert mm, tok
        i = int(mm.group(1)); assert i < len(F), (name, i)
        if mm.group(2) is None: F[i][0], F[i][1] = P[i][0], P[i][1]
        else: F[i][0] += float(mm.group(2)); F[i][1] += float(mm.group(3))
        print("%s %s point %2d (%s): ends (%+6.1f,%+6.1f) from the plain slant" % (w, name, i, "handle" if F[i][2] == "o" else "on-curve", F[i][0] - P[i][0], F[i][1] - P[i][1]))
pickle.dump(OUT, open(os.path.join(HERE, sys.argv[3]), "wb")); print(sys.argv[3])
