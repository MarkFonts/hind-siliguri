"""Curvature (G2) check of the italic correction: the plain slant (t = 0) against the corrected slant (t = 1).

    python3.13 italiccurv.py [letters|all] [--out DIR] [--stub]

Per letter: curvcomb.evaluate(g_slant, ItalicMover(g_slant)) + curvcomb.render -> <out>/<fname>_curv.png
(drawn = plain slant | CNTR 50 | CNTR 100 = corrected), then curvcomb.index_sheet -> <out>/curv_index_Italic.png,
and a snap / spike / minor summary on stdout. Default out: italic/sheets/curv.
--stub replaces the mover with a zero move (contours_at(t) = the slant) to prove the pipeline; it is never the default.
"""
import sys, os, json, argparse, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
sys.path.insert(0, HERE)
import curvcomb
from readings import fname

ROOT = os.path.abspath(os.path.join(HERE, ".."))
import carry as _C
SRC = _C.SRC


class Round5Mover:
    """round 5's corrected letter (the Italic key run_italic.py wrote, = round_p2.correct steps 1-6) as a mover:
    contours_at(t) runs linearly from the plain slant (t = 0) to the corrected (t = 1), node for node"""
    G = None

    def __init__(self, g, g_upright=None):
        self.g = g
        it = Round5Mover.G["GeistSerifItalic_" + g["glyph"]]["contours"]
        self.a = g["contours"]; self.b = it

    def contours_at(self, t):
        return [{"closed": ca["closed"], "nodes": [[na[0] + (nb[0] - na[0]) * t, na[1] + (nb[1] - na[1]) * t] + list(na[2:])
                                                   for na, nb in zip(ca["nodes"], cb["nodes"])]} for ca, cb in zip(self.a, self.b)]
ORDER = ["f", "j", "H", "n", "a", "E", "T", "r", "v", "e", "y", "k", "x", "p", "s", "B", "z", "quoteright"]


class StubMover:
    """zero move: the pipeline check only"""
    def __init__(self, g, g_upright=None):
        self.g = g

    def contours_at(self, t):
        return json.loads(json.dumps(self.g["contours"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("letters", nargs="?", default="all")
    ap.add_argument("--out", default=os.path.join(ROOT, "sheets", "curv_18"))
    ap.add_argument("--stub", action="store_true")
    _C.set_slant(_C.parse_slant(sys.argv))
    a = ap.parse_args(_C.strip_slant(sys.argv[1:]))
    G = json.load(open(_C.SRC))
    Round5Mover.G = G
    if a.stub:
        Mover, name = StubMover, "stub (zero move)"
    else:
        Mover = Round5Mover
        name = "round 5 · pass 2 (steps 1-6) %.2f deg" % _C.SLANT
    have = [g for g in ORDER if "GeistSerifSlant_" + g in G] + \
           sorted({k.split("_", 1)[1] for k in G if k.startswith("GeistSerifSlant_")} - set(ORDER))
    if a.letters == "all":
        letters = have
    elif "," in a.letters or a.letters in have:
        letters = [x for x in a.letters.split(",") if x in have]
    else:
        letters = [x for x in a.letters if x in have]
    os.makedirs(a.out, exist_ok=True)
    results = []
    tot = {"snapped": 0, "minor": 0, "clean": 0, "FAIL": 0}
    for g in letters:
        key = "GeistSerifSlant_" + g
        gs = G[key]
        try:
            res = curvcomb.evaluate(gs, Mover(gs))
            res["key"] = key
            curvcomb.render(res, os.path.join(a.out, fname("GeistSerifSlant_" + g).split("_", 1)[1] + "_curv.png"), name)
            results.append(res)
            print("%-11s %-8s sev %5.1f  snaps %s  spikes %s  minor %s" % (
                g, res["verdict"], res["sev"], [(x["node"], x["bump"], x["R1"]) for x in res["snaps"]],
                [(tuple(x["seg"]), x["r0"], x["r1"]) for x in res["spikes"]],
                [x["node"] for x in res["minors"]] + [tuple(x["seg"]) for x in res["minor_spikes"]]), flush=True)
            tot[res["verdict"]] += 1
        except Exception as e:
            traceback.print_exc()
            tot["FAIL"] += 1
            print("%-11s FAIL %r" % (g, e))
    if results:
        curvcomb.index_sheet(results, "Slant → Italic", os.path.join(a.out, "curv_index_Italic.png"), name)
    print("summary (%s): %d snapped, %d minor, %d clean, %d FAIL · %d snaps, %d spikes, %d minor flags" % (
        name, tot["snapped"], tot["minor"], tot["clean"], tot["FAIL"],
        sum(len(r["snaps"]) for r in results), sum(len(r["spikes"]) for r in results),
        sum(len(r["minors"]) + len(r["minor_spikes"]) for r in results)))


if __name__ == "__main__":
    main()
