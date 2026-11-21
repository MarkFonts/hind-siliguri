"""Straight strokes after the slant: Mark 2026-11-20, on the round solve run on every letter:
"we should shift diagonals slightly. angles that are going in the other direction of the italic should get thicker,
things that are directly slanted (verticals that become slants) need to get slightly thinned". Process: obliquing.

What I measured first (stroke thickness across the stroke, against the roman): stems come out 3% thinner from the slant
alone; a / stroke 6 to 7% thinner after the build's step; a \\ stroke was held to the STEM's thickness by the build's cap
("never thicker than its closest stem"), though the roman draws it thicker than the stem (Light y: 63 against 61).
So in the italic the \\ lost its place against the stem, and the stem sat heavy against the / strokes.

  bias2      the build's diagonal step (diag.bias) with one change: a diagonal may stay as much thicker than its stem as
             the roman draws it (cap = stem as drawn x roman diagonal / roman stem, never less than the old cap).
  thin_stems every upright straight stroke (two long upright edges facing each other across ink) loses STEM_THIN of its
             thickness, half from each edge; an edge welded to another contour's node stays and its partner takes it all.
Both read the roman outline, never a letter's name."""
import math
import numpy as np
import cand
import stored as ST
import diag as DG
STEM_THIN = .03          # share of a stem's thickness taken off (Light about 2 units, Bold about 4)
RELATION = True          # the diagonal cap keeps the roman's diagonal-to-stem relation


def _apply(g, cs, off):
    """diag.bias's own way of moving edges: a node between two straights goes to their new crossing, a node on a curve
    moves with its handle"""
    un_ = lambda p: np.array([p[0] - ST.HIND_K * (p[1] - ST.HIND_Y0), p[1]]); re_2 = lambda p: np.array([p[0] + ST.HIND_K * (p[1] - ST.HIND_Y0), p[1]])
    out = []
    for ci, c in enumerate(cs):
        segs = ST.segments(c); n = len(segs); nodes = [list(x) for x in c["nodes"]]; N = c["nodes"]
        if not any((ci, k) in off for k in range(n)): out.append(c); continue
        for k in range(n):
            p, q = segs[k], segs[(k + 1) % n]; nid = p[2]; vp, vq = off.get((ci, k), np.zeros(2)), off.get((ci, (k + 1) % n), np.zeros(2))
            if not (vp.any() or vq.any()): continue
            P0 = un_(N[nid][:2]); new = None
            if len(p[1]) == 0 and len(q[1]) == 0:
                a1 = un_(N[p[0]][:2]); d1 = P0 - a1; a2 = P0; d2 = un_(N[q[2]][:2]) - P0; cr = d1[0] * d2[1] - d1[1] * d2[0]
                if abs(cr) / (np.linalg.norm(d1) * np.linalg.norm(d2)) > .05:
                    A = a1 + vp; B = a2 + vq; tt = ((B - A)[0] * d2[1] - (B - A)[1] * d2[0]) / cr; new = A + tt * d1
            if new is None: new = P0 + (vp if vp.any() else vq)
            dv = new - P0; R = re_2(new); nodes[nid][0], nodes[nid][1] = float(R[0]), float(R[1])
            for sg, h in ((p, 1), (q, 0)):
                if len(sg[1]) == 2:
                    idx = sg[1][h]; H = un_(N[idx][:2]) + dv; RH = re_2(H); nodes[idx][0], nodes[idx][1] = float(RH[0]), float(RH[1])
        out.append(dict(c, nodes=nodes))
    return out


def bias2(g, cs, m):
    """diag.bias with the cap keeping the roman's relation of a diagonal to its stem"""
    if not RELATION: return _BIAS(g, cs, m)
    keep = DG.cap_for; R = DG.refs(m)
    ink = DG.ink_of([ST.sample_contour(c, 40) for c in g["contours"]]); S_ = DG.strokes(DG.lines_hind(g["contours"]), ink)
    top = max(n[1] for c in g["contours"] for n in c["nodes"]); case = "lc" if top < 560 else "cap"
    def cap_for(g_, m_, pd):
        base = keep(g_, m_, pd); near_v = abs(pd) < 45; ref = R[case + ("_v" if near_v else "_h")]
        # the stroke bias is asking about: the one whose drawn lean is pd
        c = [s for s in S_ if abs(math.degrees(math.atan(math.tan(math.radians(s[2])) + ST.HIND_K)) - pd) < .6]
        if not c or not ref: return base
        return base * max(1.0, max(s[3] for s in c) / ref)
    try:
        DG.cap_for = cap_for; return _BIAS(g, cs, m)
    finally:
        DG.cap_for = keep


_BIAS = DG.bias


def thin_stems(g, cs, share=None):
    """-> (contours, how many edges moved). g the roman glyph, cs the italic outline being built"""
    share = STEM_THIN if share is None else share
    if not share: return cs, 0
    L = [e for e in DG.lines_hind(g["contours"]) if np.linalg.norm(e["b"] - e["a"]) >= DG.MIN_LEN and abs(DG.phi_of(e)) <= 2]
    if len(L) < 2: return cs, 0
    ink = DG.ink_of([ST.sample_contour(c, 40) for c in g["contours"]]); off = {}
    for i, e in enumerate(L):
        u = _u(e["b"] - e["a"]); nrm = np.array([-u[1], u[0]]); le = np.linalg.norm(e["b"] - e["a"]); best = None
        for j, f in enumerate(L):
            if i == j: continue
            sa, sb = (f["a"] - e["a"]) @ u, (f["b"] - e["a"]) @ u; lo, hi = max(0, min(sa, sb)), min(le, max(sa, sb))
            if hi - lo < .4 * min(le, np.linalg.norm(f["b"] - f["a"])): continue
            mid_e = e["a"] + u * (lo + hi) / 2; t = abs((mid_e - f["a"]) @ np.array([-(f["b"] - f["a"])[1], (f["b"] - f["a"])[0]]) / np.linalg.norm(f["b"] - f["a"]))
            if t < 12 or t > 260: continue
            side = np.sign(((f["a"] + f["b"]) / 2 - e["a"]) @ nrm); p = mid_e + nrm * side * t / 2
            if not ink.contains(float(p[0]), float(p[1])): continue
            # ink all the way across: a stem, not two edges with a counter between them
            if not all(ink.contains(float((mid_e + nrm * side * t * a)[0]), float((mid_e + nrm * side * t * a)[1])) for a in (.2, .8)): continue
            if best is None or t < best[0]: best = (t, j, side)
        if best is None: continue
        t, j, side = best; we = DG.welded_edge(g, e); wf = DG.welded_edge(g, L[j])
        if we: continue
        off[(e["ci"], e["k"])] = nrm * side * share * t * (1.0 if wf else .5)
    return (_apply(g, cs, off), len(off)) if off else (cs, 0)


def _u(v):
    return v / max(np.linalg.norm(v), 1e-9)
