"""Round 5 · s round: curvature (G2) check of the s, as italiccurv.py does for round 5's set: the plain slant (t = 0)
against the corrected (t = 1), curvcomb.evaluate + curvcomb.render (solver/curvcomb.py, unchanged).

curv5s.py   -> sheets/curv/s_<14|18>_<r5s|r5rules>_curv.png, readings/curv5s.json, printed
"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
import curvcomb
import carry as C
import drawn5s


class Lin:
    def __init__(self, a, b):
        self.a, self.b = a, b

    def contours_at(self, t):
        return [{"closed": ca["closed"], "nodes": [[na[0] + (nb[0] - na[0]) * t, na[1] + (nb[1] - na[1]) * t] + list(na[2:])
                                                   for na, nb in zip(ca["nodes"], cb["nodes"])]} for ca, cb in zip(self.a, self.b)]


def main():
    D = json.load(open(drawn5s.SRC))
    out = {}
    os.makedirs(os.path.join(C.R5S, "sheets", "curv"), exist_ok=True)
    for tag in ("14", "18"):
        sl = D["GeistSerifDrawnSlant%s_s" % tag]
        for nm, key in (("r5s", "GeistSerifDrawnItalic%s_s" % tag), ("r5rules", "GeistSerifDrawnR5rules%s_s" % tag)):
            g = dict(sl, glyph="s", master="Slant")
            res = curvcomb.evaluate(g, Lin(sl["contours"], D[key]["contours"]))
            fn = os.path.join(C.R5S, "sheets", "curv", "s_%s_%s_curv.png" % (tag, nm))
            curvcomb.render(res, fn, "round 5 · s round: %s at %s deg (his roman s)" % ("round 5s" if nm == "r5s" else "round 5's rules", "14.04" if tag == "14" else "18.43"))
            out["%s %s" % (tag, nm)] = dict(verdict=res["verdict"], sev=res["sev"], snaps=[(x["node"], x["bump"], x["R1"]) for x in res["snaps"]],
                                           spikes=[tuple(x["seg"]) for x in res["spikes"]], minors=[x["node"] for x in res["minors"]] + [tuple(x["seg"]) for x in res["minor_spikes"]])
            print(tag, nm, out["%s %s" % (tag, nm)])
    json.dump(out, open(os.path.join(C.R5S, "readings", "curv5s.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
