"""Fit rho, nu, psi by SCORE: the skeleton rules I10-I12 (steps 1-3) at 14.04 deg against Mark's drawn o, p, s and
two-storey a (e, n unfinished: not used); one parameter at a time, XOR % per letter.

scan_params.py [rho|nu|psi|all]       -> readings/scan_params.json
"""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
C.set_slant(0.25)
import drawn
from round5 import correct
import skeleton as SK

G = C.load()
FR = {gl: G["GeistSerifSlant_" + gl]["contours"] for gl in drawn.FIT_LETTERS}
DR = {gl: drawn.letter(gl, "italic", FR[gl])["contours"] for gl in drawn.FIT_LETTERS}
from italicmove import ItalicMover
IM0 = {gl: ItalicMover(G["GeistSerifSlant_" + gl], G["GeistSerifRegular_" + gl]) for gl in drawn.FIT_LETTERS}


def xor_at(gl, rho, nu, psi):
    Sk = SK.Skeleton(G["GeistSerifRegular_" + gl], rules=("I10", "I11", "I12"), rho=rho, nu_coef=nu, psi=psi, IM0=IM0[gl])
    return drawn.xor_pct(Sk.contours, DR[gl])


def scan(name, values, letters, fixed):
    rows = []
    for v in values:
        p = dict(fixed); p[name] = v
        x = {gl: round(xor_at(gl, p["rho"], p["nu"], p["psi"]), 2) for gl in letters}
        rows.append(dict(value=round(float(v), 3), xor=x, total=round(sum(x.values()), 2)))
        print(name, "%.3f" % v, x, "total %.2f" % rows[-1]["total"], flush=True)
    best = min(rows, key=lambda r: r["total"])
    return dict(rows=rows, best=best)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    fixed = dict(rho=SK.RHO, nu=SK.NU_COEF, psi=SK.PSI)
    out = {}
    if what in ("rho", "all"):
        out["rho"] = scan("rho", np.arange(0.0, 1.01, 0.1), ["o", "p", "a", "s"], fixed)
        for gl in ["o", "p", "a", "s"]:
            b = min(out["rho"]["rows"], key=lambda r: r["xor"][gl]); out["rho"]["best_" + gl] = b["value"]
    if what in ("nu", "all"):
        out["nu"] = scan("nu", np.arange(-0.3, 0.61, 0.1), ["o", "p", "a", "s"], fixed)
        for gl in ["o", "p", "a", "s"]:
            b = min(out["nu"]["rows"], key=lambda r: r["xor"][gl]); out["nu"]["best_" + gl] = b["value"]
    if what in ("psi", "all"):
        out["psi"] = scan("psi", np.arange(0.0, 1.61, 0.2), ["s"], fixed)
    p = os.path.join(C.R5, "readings", "scan_params_%s.json" % what)
    json.dump(out, open(p, "w"), indent=1)
    for k, v in out.items():
        print(k, "best total", v["best"], {kk: vv for kk, vv in v.items() if kk.startswith("best_")})
