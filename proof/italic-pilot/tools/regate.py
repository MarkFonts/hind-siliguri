import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hind_kit as H
from multiprocessing import Pool
W = os.path.join(os.path.dirname(HERE), "work")
def job(a):
    m, gl, cs = a
    G = json.load(open(os.path.join(W, "upright_%s.json" % m)))
    return m, gl, H.gate_visible(cs, G[gl]["contours"])
if __name__ == "__main__":
    R = {m: json.load(open(os.path.join(W, "results_%s.json" % m))) for m in ("Light", "Bold")}
    tasks = [(m, gl, r["contours"]) for m in R for gl, r in R[m].items() if r["ok"]]
    with Pool(7) as P:
        for m, gl, g in P.imap_unordered(job, tasks, chunksize=4):
            R[m][gl]["gate"] = g
    for m in R:
        json.dump(R[m], open(os.path.join(W, "results_%s.json" % m), "w"))
        v = [r for r in R[m].values() if r["ok"]]
        print(m, "pass", sum(r["gate"]["ok"] for r in v), "of", len(v), "| buried-only", sum(1 for r in v if r["gate"]["ok"] and r["gate"]["hump_buried"]))
