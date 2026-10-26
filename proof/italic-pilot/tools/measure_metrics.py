import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from geom import runs_at_y, runs_at_x
W = os.path.join(os.path.dirname(HERE), "work")
out = {}
for m in ("Light", "Bold"):
    G = json.load(open(os.path.join(W, "upright_%s.json" % m)))
    def bb(g):
        ys = [n[1] for c in G[g]["contours"] for n in c["nodes"]]; xs = [n[0] for c in G[g]["contours"] for n in c["nodes"]]
        return min(xs), min(ys), max(xs), max(ys)
    r = {}
    r["n_runs_250"] = runs_at_y(G["n"]["contours"], 250)
    r["H_runs_200"] = runs_at_y(G["H"]["contours"], 200)
    r["H_bar_x"] = runs_at_x(G["H"]["contours"], (bb("H")[0] + bb("H")[2]) / 2)
    r["o_top"] = bb("o")[3]; r["o_bot"] = bb("o")[1]; r["O_top"] = bb("O")[3]; r["d_top"] = bb("d")[3]; r["p_bot"] = bb("p")[1]
    for g in ("bnKA", "bnBA", "bnMA", "bnA", "bnTA"):
        r[g + "_bb"] = bb(g)
    b = bb("bnBA")
    r["bnBA_runs_250"] = runs_at_y(G["bnBA"]["contours"], 250)
    r["bnBA_runs_x"] = runs_at_x(G["bnBA"]["contours"], b[2] - 30)
    r["bnKA_runs_x_mid"] = runs_at_x(G["bnKA"]["contours"], (b[0] + b[2]) / 2)
    out[m] = r
    print(m, json.dumps(r))
