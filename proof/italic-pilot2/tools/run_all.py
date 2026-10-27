"""run the correction on every glyph with outlines, both masters, in parallel; per-glyph 90 s alarm"""
import sys, os, json, signal, time, traceback
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
PILOT = os.path.dirname(HERE); W = os.path.join(PILOT, "work")

def job(args):
    master, gl, ret, simple = args
    import hind_kit as H
    G = json.load(open(os.path.join(W, "upright_%s.json" % master)))
    g = G[gl]
    def alarm(*a): raise TimeoutError("90 s")
    signal.signal(signal.SIGALRM, alarm); signal.alarm(90)
    t = time.time()
    try:
        r = H.correct_glyph(g, master, retension=ret, simple=simple)
        signal.alarm(0)
        return master, gl, dict(ok=True, contours=r["contours"], gate=r["gate"], info=r["info"], secs=round(time.time() - t, 2))
    except BaseException as e:
        signal.alarm(0)
        return master, gl, dict(ok=False, error=repr(e)[:300], where=traceback.format_exc().strip().splitlines()[-3:], secs=round(time.time() - t, 2))

if __name__ == "__main__":
    ret = "--no-retension" not in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = args[0].split(",") if args else None
    simple = "--simple" in sys.argv
    tag = "_C" if simple else ("" if ret else "_B")
    tasks = []
    for m in ("Light", "Bold"):
        G = json.load(open(os.path.join(W, "upright_%s.json" % m)))
        for gl, g in G.items():
            if g["contours"] and (only is None or gl in only):
                tasks.append((m, gl, ret, simple))
    res = {"Light": {}, "Bold": {}}
    with Pool(7) as P:
        for i, (m, gl, r) in enumerate(P.imap_unordered(job, tasks, chunksize=2)):
            res[m][gl] = r
            if i % 100 == 0: print(i, len(tasks), flush=True)
    for m in res:
        fn = os.path.join(W, "results%s_%s.json" % (tag, m))
        old = json.load(open(fn)) if (only and os.path.exists(fn)) else {}
        old.update(res[m]); json.dump(old, open(fn, "w"))
    for m in res:
        v = res[m].values()
        print(m, "ran", len(res[m]), "errors", sum(1 for r in v if not r["ok"]), "gate pass", sum(1 for r in v if r["ok"] and r["gate"]["ok"]))
