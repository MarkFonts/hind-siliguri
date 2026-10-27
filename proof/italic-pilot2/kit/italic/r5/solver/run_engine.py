"""Run the current Stemperature engine (stemcore, Glyphs-free raster) on extracted glyphs.
Saves per key: F, prov, mask (npz), geometry + chords (json, font units)."""
import sys, os, json, time
import numpy as np
CORE = "/Users/Mark/Documents/Github/wordmarktools/stemperature/core"
sys.path.insert(0, os.path.join(CORE, "engine")); sys.path.insert(0, os.path.join(CORE, "raster"))
import stemcore
from part_raster import part_raster, glyph_raster
import raster as R

src, outdir = sys.argv[1], sys.argv[2]
keys = sys.argv[3].split(",")
G = json.load(open(src))
M = json.load(open("/Users/Mark/Documents/Github/wordmarktools/stemperature/perf/serif/dump_hs/masters.json"))
os.makedirs(outdir, exist_ok=True)
for key in keys:
    g = G[key]
    mname = "HS" + g["master"].replace(" ", "")
    mk = M[mname]
    master = {"upm": mk["upm"], "italicAngle": mk["ia"], "vstems": mk["V"], "hstems": mk["H"], "zones": [list(z) for z in mk["Z"]]}
    contours = [{"closed": c["closed"], "nodes": [[x, y, t] for x, y, t, s in c["nodes"]]} for c in g["contours"]]
    r = glyph_raster(contours, R.RES_TARGET, upm=mk["upm"])
    mask, cov, res, ox, oy, W, H = r
    chords = []
    t0 = time.perf_counter()
    out = stemcore.solve(contours, master, mask, res, ox, oy, W, H, {"raster": part_raster, "name": key, "dbg_chords": chords})
    dt = time.perf_counter() - t0
    F, prov = out["F"], out["prov"]
    np.savez_compressed(os.path.join(outdir, key + ".npz"), F=np.nan_to_num(F) if F is not None else np.zeros((1,1)), prov=prov if prov is not None else np.zeros((1,1), np.uint8), mask=mask)
    ch = []
    for P, partner, width, run in chords:
        P = np.asarray(P, float)
        ch.append({"P": P.tolist(), "partner": np.asarray(partner).astype(int).tolist(), "width": np.nan_to_num(np.asarray(width, float), nan=-1).tolist(), "run": np.asarray(run).astype(int).tolist()})
    meas = float((prov == 2).sum()) / max(1, int(mask.sum())) if prov is not None else 0
    json.dump({"key": key, "res": res, "ox": ox, "oy": oy, "W": W, "H": H, "pad": R.PAD_PX, "master": master, "chords": ch, "meas": meas, "diag": out["diag"]}, open(os.path.join(outdir, key + ".json"), "w"))
    Prange = [(float(np.min(c["P"])), float(np.max(c["P"]))) for c in ch[:1]]
    print("%-20s %dx%d res %.3f  %.2fs  parts %d  meas %.0f%%  Prange %s  flags %s" % (key, W, H, res, dt, len(ch), 100*meas, Prange, out["flags"]))
