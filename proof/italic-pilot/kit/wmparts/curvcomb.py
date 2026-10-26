"""Curvature comb (G2) evaluator for the move step.

Glyphs' "Show Curvature" / Speed Punk look: a comb of normals along every cubic, height = curvature,
yellow (gentle) -> orange -> hot red (spiking). Drawn, CNTR 50 and CNTR 100 share ONE scale per glyph
(the drawn outline's 95th-percentile |k|), so a comb that grows between panels really grew.

Judged only on TOUCHED segments (any of the 4 control points moved at CNTR 50 or 100), per state (50, 100):
  KINK   a smooth node whose two handles now turn by > KINK_DEG (G1 break): always a SNAP
  SNAP   a smooth node whose curvature jump |kL - kR| grew (> MINOR_RATIO x drawn, + MINOR_FLOOR x scale)
         AND is visible: the curve crosses its own end tangent by >= BUMP_U units next to the node (an
         extremum slid off its node), or the jump read over WIN units of arc is a radius <= VIS_R units
  SPIKE  a segment whose peak |k| > SPIKE_RATIO x drawn (and > SPIKE_FLOOR x scale) or that gained an
         inflection, AND whose tightest WIN-arc radius is <= VIS_R units and SPIKE_VIS x tighter than drawn
  minor  nominated by the curvature numbers but not visible by the rules above
  CROSS  (round 5, crosscheck.py) the moved outline crosses itself where the drawing did not, or a fold the
         drawing has (a START hairpin dipping under a bar) grew: a new crossing between two segments of one
         contour (or a counter and its bowl), or a new / grown hole, inside-out ear, self-overlap fold or escaped
         counter of >= 25 u^2. Ringed cyan on the sheets, listed `kind a-b x c-d area (drawn area)`. A layer with
         a cross is verdict "cross" whatever its combs say (cross > snapped > minor > clean).
The bare endpoint jump alone over-flags: a short handle blows endpoint curvature up over a sliver of arc
the eye never sees (Italic n 24 reads 4.2x scale yet is a 2.7 u bump), so it only nominates.

This module is the judging only (numpy + scipy): evaluate(g, M) -> the result dict. The comb drawings, index sheets,
CURV.md and the command line live in wmparts/render/combs.py (PIL):
  python3.13 -m wmparts.render.curvsheet SET.json OUTDIR [--mover groupmove:GroupMover]... [--keys k1,k2|all]
  python3.13 -m wmparts.render.curvsheet --md OUTDIR        (re-write CURV.md from the results_*.json there)
  python3.13 -m wmparts.render.curvsheet SET.json OUTDIR --zoom KEY:x0,y0,x1,y1 [--mover ...]   (drawn | 50 | 100 close-up)
"""
import math
import numpy as np
from . import crosscheck
CROSSC = (60, 230, 255)

NS = 40                 # samples per cubic
SNAP_RATIO, SNAP_FLOOR = 3.0, 0.75
MINOR_RATIO, MINOR_FLOOR = 1.75, 0.35
SPIKE_RATIO, SPIKE_FLOOR = 3.0, 1.5
INFL_EPS = 0.08         # |k| below this x scale does not count as a sign (inflection noise)
SMOOTH_DEG = 3.0        # handles within this of collinear = smooth
TOUCH_TOL = 0.05        # font units
# what the eye sees (the curvature thresholds above only nominate; these decide snap vs minor)
WIN = 8.0               # curvature read over 8 units of arc, not at the bare endpoint
BUMP_U = 3.0            # a node whose curve now crosses its own tangent by >= 3 units = visible bump
VIS_R = 10.0            # ... or whose 8-unit curvature jump is a radius <= 10 units (and 1.5x drawn)
KINK_DEG = 4.0          # a smooth node whose handles now turn by > 4 deg (and 4 deg more than drawn) = G1 kink, always a snap
KINK_MINOR = 1.5        # 1.5..4 deg: a kink too small to see, listed as minor
SEV_CAP = 30.0          # one flag adds at most this to a glyph's severity (a reversed handle reads 180)
SPIKE_VIS = 2.5         # a spike is visible when its 8-unit peak radius is <= VIS_R and 2.5x tighter than drawn

GREY = (88, 88, 88)
SNAPC = (255, 45, 45)
MINORC = (255, 160, 40)
SPIKEC = (255, 70, 200)


# --- geometry ------------------------------------------------------------------------
def segments(contours):
    """[(gi, gj, kind, pts, ctrl_global_indices)] in file order; mirrors rungs.Outline's segmenting."""
    out = []; base = 0
    for c in contours:
        nodes = c["nodes"]; N = len(nodes)
        ons = [i for i in range(N) if nodes[i][2] != "o"]
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [k % N for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
            P0, P3 = tuple(nodes[i][:2]), tuple(nodes[j][:2])
            if len(offs) == 2 and nodes[j][2] != "l":
                pts = [P0, tuple(nodes[offs[0]][:2]), tuple(nodes[offs[1]][:2]), P3]
                out.append((base + i, base + j, "curve", pts, [base + i, base + offs[0], base + offs[1], base + j]))
            else:
                out.append((base + i, base + j, "line", [P0, P3], [base + i] + [base + o for o in offs] + [base + j]))
        base += N
    return out


def flat(contours):
    return [(n[0], n[1]) for c in contours for n in c["nodes"]]


def cubic(P, t):
    P = np.asarray(P, float); t = np.asarray(t, float)[:, None]; u = 1 - t
    B = u ** 3 * P[0] + 3 * u * u * t * P[1] + 3 * u * t * t * P[2] + t ** 3 * P[3]
    d1 = 3 * u * u * (P[1] - P[0]) + 6 * u * t * (P[2] - P[1]) + 3 * t * t * (P[3] - P[2])
    d2 = 6 * u * (P[2] - 2 * P[1] + P[0]) + 6 * t * (P[3] - 2 * P[2] + P[1])
    return B, d1, d2


def kappa(P, t):
    """signed curvature, position, unit left normal at parameters t"""
    B, d1, d2 = cubic(P, t)
    sp = np.hypot(d1[:, 0], d1[:, 1])
    k = (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.maximum(sp, 1e-9) ** 3
    k[sp < 1e-6] = np.nan
    n = np.stack([-d1[:, 1], d1[:, 0]], 1) / np.maximum(sp, 1e-9)[:, None]
    return k, B, n


def tparams(P):
    """sample params; a retracted handle (on its node) leaves that end's curvature undefined, so step in"""
    t = np.linspace(0, 1, NS)
    if math.dist(P[0], P[1]) < 0.5: t[0] = 0.02
    if math.dist(P[3], P[2]) < 0.5: t[-1] = 0.98
    return t


def end_tan(seg, end):
    gi, gj, kind, P, _ = seg
    if kind == "line":
        d = (P[1][0] - P[0][0], P[1][1] - P[0][1])
    elif end == 0:
        d = next(((q[0] - P[0][0], q[1] - P[0][1]) for q in P[1:] if math.dist(q, P[0]) > 0.5), (0, 0))
    else:
        d = next(((P[3][0] - q[0], P[3][1] - q[1]) for q in P[2::-1] if math.dist(q, P[3]) > 0.5), (0, 0))
    L = math.hypot(*d)
    return (d[0] / L, d[1] / L) if L > 1e-9 else None


def end_kappa(seg, end):
    """curvature at the segment's start (end=0) or finish (end=1); None if undefined (retracted handle)"""
    gi, gj, kind, P, _ = seg
    if kind == "line":
        return 0.0
    if end == 0 and math.dist(P[0], P[1]) < 0.5: return None
    if end == 1 and math.dist(P[3], P[2]) < 0.5: return None
    k, _, _ = kappa(P, [float(end)])
    return None if np.isnan(k[0]) else float(k[0])


def analyse(contours):
    segs = segments(contours)
    per = []
    for s in segs:
        if s[2] == "curve":
            t = tparams(s[3]); k, B, n = kappa(s[3], t)
            per.append(dict(t=t, k=k, B=B, n=n))
        else:
            per.append(None)
    into = {s[1]: i for i, s in enumerate(segs)}
    outof = {s[0]: i for i, s in enumerate(segs)}
    return segs, per, into, outof


def sign_changes(k, eps):
    s = [1 if v > eps else -1 for v in k if not np.isnan(v) and abs(v) > eps]
    return sum(1 for a, b in zip(s, s[1:]) if a != b)


# --- evaluation ---------------------------------------------------------------------------
def arc(P, n=400):
    """arc length and unwrapped tangent angle along a cubic"""
    t = np.linspace(0, 1, n); B, d1, _ = cubic(P, t)
    s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(B, axis=0).T))])
    return s, np.unwrap(np.arctan2(d1[:, 1], d1[:, 0]))


def win_side(seg, end):
    """curvature seen over WIN units of arc next to a node (turning angle / length): what the eye sees,
    immune to the endpoint blow-up of a very short handle"""
    if seg[2] == "line":
        return 0.0
    s, th = arc(seg[3]); L = s[-1]; w = min(WIN, L)
    if w < 1e-6: return 0.0
    if end == 1:
        return float((th[-1] - np.interp(L - w, s, th)) / w)
    return float((np.interp(w, s, th) - th[0]) / w)


def win_peak(seg):
    s, th = arc(seg[3]); L = s[-1]; w = min(WIN, L)
    if w < 1e-6: return 0.0
    ss = np.linspace(0, L - w, 120)
    return float(np.max(np.abs(np.interp(ss + w, s, th) - np.interp(ss, s, th)) / w))


def overshoot(S, K0, a, b, node):
    """how far (font units) the curve next to this node crosses to the wrong side of its OWN end tangent
    there: the bump you see when an extremum slides off its node. Only the half of each segment next to
    the node is measured, against the side the DRAWN curve bends to in that half."""
    best = 0.0
    for i, end in ((a, 1), (b, 0)):
        if S[i][2] != "curve" or K0[i] is None: continue
        T = end_tan(S[i], end)
        if T is None: continue
        P = np.array(S[i][3][3 if end else 0]); N = np.array([-T[1], T[0]])
        half = slice(NS // 2, NS) if end else slice(0, NS // 2)
        sg = np.sign(np.nanmedian(K0[i]["k"][half]))
        if sg == 0: continue
        tt = np.linspace(0.5, 1, 100) if end else np.linspace(0, 0.5, 100)
        B, _, _ = cubic(S[i][3], tt)
        best = max(best, float(np.max(-sg * ((B - P) @ N))))
    return best


def turn_deg(S, a, b):
    ta, tb = end_tan(S[a], 1), end_tan(S[b], 0)
    if not (ta and tb): return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, ta[0] * tb[0] + ta[1] * tb[1]))))


def judge(drawn, moved, scale, touched, S0, K0, IN0, OUT0, smooth_nodes):
    """flags for one moved state against the drawn outline"""
    S1, K1, _, _ = analyse(moved)
    snaps, minors, spikes, mspikes = [], [], [], []
    for gi in smooth_nodes:
        a, b = IN0[gi], OUT0[gi]
        if not (touched[a] or touched[b]):
            continue
        kl0, kr0 = end_kappa(S0[a], 1), end_kappa(S0[b], 0)
        kl1, kr1 = end_kappa(S1[a], 1), end_kappa(S1[b], 0)
        if None in (kl0, kr0, kl1, kr1):
            continue
        j0, j1 = abs(kl0 - kr0) / scale, abs(kl1 - kr1) / scale
        grew = j1 - j0
        g0, g1 = turn_deg(S0, a, b), turn_deg(S1, a, b)
        kink = g1 > max(KINK_DEG, g0 + KINK_DEG)        # the node is no longer smooth at all (G1 break)
        kink_small = not kink and g1 > max(KINK_MINOR, g0 + KINK_MINOR)
        if not kink and not kink_small and not (j1 > MINOR_RATIO * max(j0, 0.05) and grew > MINOR_FLOOR):
            continue
        w0 = abs(win_side(S0[a], 1) - win_side(S0[b], 0)); w1 = abs(win_side(S1[a], 1) - win_side(S1[b], 0))
        ov0, ov1 = overshoot(S0, K0, a, b, gi), overshoot(S1, K0, a, b, gi)
        R1 = 1 / max(w1, 1e-4)
        row = dict(node=gi, j0=round(j0, 2), j1=round(j1, 2), R0=round(1 / max(w0, 1e-4)), R1=round(R1, 1),
                   bump=round(ov1 - ov0, 1), kink=round(g1, 1) if (kink or kink_small) else 0.0,
                   sev=round(min(SEV_CAP, max(ov1 - ov0, VIS_R / R1, g1 if kink else 0.0)), 2))
        strong = j1 > SNAP_RATIO * max(j0, 0.05) and grew > SNAP_FLOOR
        visible = kink or (ov1 - ov0) >= BUMP_U or (R1 <= VIS_R and w1 > 1.5 * w0)
        (snaps if visible else minors).append(dict(row, strong=strong))
    for si, s in enumerate(S0):
        if s[2] != "curve" or not touched[si]:
            continue
        k0, k1 = K0[si]["k"], K1[si]["k"]
        m0 = float(np.nanmax(np.abs(k0))) / scale; m1 = float(np.nanmax(np.abs(k1))) / scale
        n0 = sign_changes(k0, INFL_EPS * scale); n1 = sign_changes(k1, INFL_EPS * scale)
        why = []
        if m1 > SPIKE_RATIO * max(m0, 0.05) and m1 > SPIKE_FLOOR:
            why.append("peak x%.1f" % (m1 / max(m0, 0.05)))
        if n1 > n0:
            why.append("+%d inflection" % (n1 - n0))
        if not why:
            continue
        p0, p1 = win_peak(s), win_peak(S1[si])
        r1 = 1 / max(p1, 1e-4)
        row = dict(seg=[s[0], s[1]], m0=round(m0, 2), m1=round(m1, 2), n0=n0, n1=n1, why=", ".join(why),
                   r0=round(1 / max(p0, 1e-4), 1), r1=round(r1, 1), sev=round(min(SEV_CAP, VIS_R / r1), 2))
        visible = r1 <= VIS_R and p1 > SPIKE_VIS * p0
        (spikes if visible else mspikes).append(row)
    if snaps or spikes:
        verdict = "snapped"
    elif minors or mspikes:
        verdict = "minor"
    else:
        verdict = "clean"
    sev = sum(x["sev"] for x in snaps + spikes)
    return dict(snaps=snaps, minors=minors, spikes=spikes, minor_spikes=mspikes, verdict=verdict, sev=round(sev, 2))


def evaluate(g, M):
    drawn = g["contours"]
    c50, c100 = M.contours_at(0.5), M.contours_at(1.0)
    S0, K0, IN0, OUT0 = analyse(drawn)
    allk = np.concatenate([np.abs(p["k"][~np.isnan(p["k"])]) for p in K0 if p is not None] or [np.array([1e-3])])
    scale = max(float(np.percentile(allk, 95)) if len(allk) else 1e-3, 1e-4)
    f0, f1, f5 = flat(drawn), flat(c100), flat(c50)
    moved = {i for i, (a, b, c) in enumerate(zip(f0, f1, f5)) if math.dist(a, b) > TOUCH_TOL or math.dist(a, c) > TOUCH_TOL}
    touched = [any(ix in moved for ix in s[4]) for s in S0]
    smooth_nodes = []
    for gi, n in enumerate([n for c in drawn for n in c["nodes"]]):
        if n[2] == "o" or gi not in IN0 or gi not in OUT0:
            continue
        a, b = IN0[gi], OUT0[gi]
        if S0[a][2] == "line" and S0[b][2] == "line":
            continue
        ta, tb = end_tan(S0[a], 1), end_tan(S0[b], 0)
        smooth = bool(n[3] if len(n) > 3 else False)
        if ta and tb:
            ang = math.degrees(math.acos(max(-1.0, min(1.0, ta[0] * tb[0] + ta[1] * tb[1]))))
            smooth = smooth or ang < SMOOTH_DEG
        if smooth:
            smooth_nodes.append(gi)
    J = {t: judge(drawn, c, scale, touched, S0, K0, IN0, OUT0, smooth_nodes) for t, c in ((50, c50), (100, c100))}
    for t, c in ((50, c50), (100, c100)):
        cr = crosscheck.check(drawn, c, held=crosscheck.held_polys(M))
        J[t]["crosses"] = cr
        if crosscheck.counted(cr):
            J[t]["verdict"] = "cross"
    res = dict(key=None, glyph=g["glyph"], master=g["master"], family=g.get("family", ""), scale=scale, touched=sum(touched),
               ncurves=sum(1 for s in S0 if s[2] == "curve"), touched_segs=[[s[0], s[1]] for s, tt in zip(S0, touched) if tt],
               at50={k: v for k, v in J[50].items()},
               _contours={0: drawn, 50: c50, 100: c100}, _touched=touched, _J=J)
    res.update(J[100])
    return res




ORDER = {"cross": 3, "snapped": 2, "minor": 1, "clean": 0}


def worst_first(rs):
    return sorted(rs, key=lambda r: (-ORDER[r["verdict"]], -r["sev"], -(len(r["minors"]) + len(r["minor_spikes"]))))
