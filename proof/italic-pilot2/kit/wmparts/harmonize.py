"""Harmonize (PROTOTYPE, not wired into the pipeline): curvature-continuous smooth nodes after the move, with the node
structure frozen (R16). docs/HARMONIZER.md has the background (RMX Harmonizer, GreenHarmony, Curvatura, beziers.py).

The math. A smooth node N joins the cubic A0 A1 A2 N to the cubic N B1 B2 B3; A2, N and B1 lie on one tangent line T.
The curvature at the end of a cubic is

    kA = 2/3 * sA / LA**2        sA = signed distance of A1 from T,  LA = |A2 - N|
    kB = 2/3 * sB / LB**2        sB = signed distance of B2 from T,  LB = |B1 - N|

so G2 (kA = kB) holds when LA / LB = sqrt(sA / sB). Two ways to get there without adding or removing a point:

  slide    move N along T between A2 and B1, handles fixed in space (sA, sB, and LA + LB do not change):
           N = A2 + r / (1 + r) * (B1 - A2),  r = sqrt(sA / (rho * sB)).  Closed form, exact, and LOCAL: the curvature
           at A0 and B3 does not depend on N, so every node can be slid on its own in one pass. (GreenHarmony, Simon
           Cozens' algorithm, Curvatura's harmonize; FontLab "Harmonize"; Glyphs' Opt-drag of a green node by hand.)
  handles  keep N; give the node a target curvature and re-solve the two handle LENGTHS of each adjacent cubic (both
           directions kept) so it reaches its targets at both ends: with P1 = P0 + a d0, P2 = P3 + b d3,
               k0 = 2/3 (d0 x (P3 - P0) + b (d0 x d3)) / a**2,   k3 = -2/3 (d3 x (P0 - P3) + a (d3 x d0)) / b**2
           two quadratics in (a, b), solved by Newton from the current lengths (the nearest root, never a far one).
           A far end that is not harmonized keeps its current curvature, so nothing spreads along the contour.
           (Curvatura's harmonize handles, FontLab "Harmonize Handles".)

rho is the target ratio kA / kB: 1 for G2 (target="g2"), or the DRAWN ratio at that node (target="drawn", the default
when the drawn outline is given): CNTR 100 then has the drawn letter's continuity, step for step, which is what an axis
"with the original letters" asks for. An inflection node (kA, kB of opposite sign) can only be restored to its drawn
ratio; G2 there would need both curvatures to be zero, so target="g2" leaves it.

In handles mode the node's target is the curvature of the side whose cubic kept its drawn shape (translated or not
moved, R14): only the re-fitted connecting curve changes, as in R15 ("the untransformed side wins"). When both sides
were re-fitted the two curvatures meet at their geometric mean (each handle length changes by the same factor).

  harmonize_glyph(glyph, nodes=None, mode="auto", target=None, drawn=None, pinned=None, exclude=(), ...) -> (Glyph, report)
  harmonize_move(M, mode="auto", target="drawn", scope="touched", ...) -> a copy of the Move: .new harmonized,
      .moved its own CNTR 100, .harmonize_report; contours_at(t) linear drawn -> harmonized

mode "node" slides every node it may (pinned nodes are skipped), "handles" scales handles only, "auto" slides unless
the node is pinned (an extreme or a node on a metric line keeps its position), the slide is longer than max_slide, or
a slide would thin a rung (harmonize_move, rungcheck R23); then it scales handles.

RE-AIM (the third operation; RMX also picks new tangent angles: "Supersmooth shifts the node perpendicular to the
handles"). A slide or a handle scale keeps sA and sB on their sides of T, so neither can undo a SIGN FLIP (the move
left one side bending the wrong way at the node, a new inflection there). Re-aim turns both handles together about
the node (lengths kept, still smooth) by the smallest angle within +-25 deg that gives both sides their drawn sign and
brings kA / kB towards the target; cost = |angle| + ratio deviation + handles leaving their drawn side of the chord +
worse neighbouring joints + the R23 rung term (a rotation that makes a part's thinnest rung thinner than the move left
it is refused). The slide / handle scale then finishes the ratio. "auto" re-aims only where a sign flipped; "reaim"
tries it at every joint. A node on a metric line or its overshoot ("metric extreme") never re-aims; another extreme may,
and stops being an extreme (the report says so: was="extreme", tangent_before / tangent_after). Node count, order, types, smooth
flags and handle count are asserted unchanged.
"""
import copy
import math

import numpy as np

from .font import Glyph

SMOOTH_DEG = 3.0          # tangent-continuous within this = smooth (curvcomb's rule)
RETRACTED = 0.5           # a handle shorter than this (u) has no end curvature
FLAT_R = 20000.0          # both radii above this (u): nothing to harmonize
ABRUPT = 3.0              # target="g2": a DRAWN curvature ratio above this is a design feature (RMX: "intentional")
EXTREME_DEG = 1.5         # a node whose tangent is within this of x, y (or the italic angle) is an extreme
ON_LINE = 1.0             # u: a node this close to a metric line is on it
OVERSHOOT = 15.0          # u: a horizontal extreme this close to a metric line sits on it (its overshoot)
LIMITS = (0.25, 2.5)      # a handle may end at 0.25 .. 2.5 x its incoming length (italic/NOTES.md: Curvatura's needles)
MAX_SLIDE = 20.0          # u: auto mode scales handles instead of sliding further than this
TOL = 1e-4                # relative curvature mismatch counted as harmonized


# ---- geometry ---------------------------------------------------------------------------------------------
def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _flat(contours):
    return np.array([[float(n[0]), float(n[1])] for c in contours for n in c["nodes"]], float)


def _structure(contours):
    return [(c.get("closed", True), [(n[2], bool(n[3]) if len(n) > 3 else False) for n in c["nodes"]]) for c in contours]


def _segments(contours):
    """[(gi, gj, ctrl)] in file order, ctrl = [gi, o1, o2, gj] for a cubic, None for a line (curvcomb's segmenting)"""
    out, base = [], 0
    for c in contours:
        nodes = c["nodes"]; N = len(nodes)
        ons = [i for i in range(N) if nodes[i][2] != "o"]
        for a, i in enumerate(ons):
            if not c.get("closed", True) and a == len(ons) - 1:
                break
            j = ons[(a + 1) % len(ons)]
            offs = [k % N for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
            cub = len(offs) == 2 and nodes[j][2] != "l"
            out.append((base + i, base + j, [base + i, base + offs[0], base + offs[1], base + j] if cub else None))
        base += N
    return out


def end_curvature(X, ctrl, end):
    """signed curvature of the cubic ctrl at its start (end=0) or finish (end=1), along the contour; None if retracted"""
    P0, P1, P2, P3 = (X[k] for k in ctrl)
    if end == 0:
        L = math.hypot(*(P1 - P0))
        return None if L < RETRACTED else 2.0 / 3.0 * _cross(P1 - P0, P2 - P0) / L ** 3
    L = math.hypot(*(P3 - P2))
    return None if L < RETRACTED else 2.0 / 3.0 * _cross(P3 - P2, P1 - P2) / L ** 3


def _turn_deg(X, a, b):
    """angle between the incoming handle (a: ctrl of the segment before) and the outgoing one (b)"""
    ta, tb = X[a[3]] - X[a[2]], X[b[1]] - X[b[0]]
    la, lb = math.hypot(*ta), math.hypot(*tb)
    if la < RETRACTED or lb < RETRACTED:
        return 180.0
    c = max(-1.0, min(1.0, float(ta @ tb) / (la * lb)))
    return math.degrees(math.acos(c))


class _Joints:
    """the smooth curve-to-curve joints of an outline: {node: (ctrl before, ctrl after)}"""

    def __init__(self, contours, X=None):
        X = _flat(contours) if X is None else X
        segs = _segments(contours)
        into = {s[1]: s for s in segs}; outof = {s[0]: s for s in segs}
        flags = [bool(n[3]) if len(n) > 3 else False for c in contours for n in c["nodes"]]
        self.joint, self.line_joint = {}, set()
        for nd in into:
            if nd not in outof:
                continue
            a, b = into[nd][2], outof[nd][2]
            if a is None or b is None:
                if (a is None) != (b is None):
                    self.line_joint.add(nd)          # straight into curve: the straight side wins (left alone)
                continue
            if flags[nd] or _turn_deg(X, a, b) < SMOOTH_DEG:
                self.joint[nd] = (a, b)
        self.segs = segs


# ---- the two operations --------------------------------------------------------------------------------------
def slide_node(X, a, b, rho=1.0):
    """the G2 position of the node a[3] == b[0] on its tangent line (handles fixed): the new (x, y), or None when the
    curvatures cannot be matched by a slide (inflection with rho > 0, a retracted handle, a flat joint)"""
    A1, A2, N, B1, B2 = X[a[1]], X[a[2]], X[a[3]], X[b[1]], X[b[2]]
    D = B1 - A2; Ld = math.hypot(*D)
    if Ld < 2 * RETRACTED or math.hypot(*(N - A2)) < RETRACTED or math.hypot(*(B1 - N)) < RETRACTED:
        return None
    T = D / Ld
    sA, sB = _cross(T, A1 - A2), _cross(T, B2 - B1)
    q = sA / (rho * sB) if abs(sB) > 1e-9 else -1.0
    if not q > 0:
        return None
    r = math.sqrt(q)
    return A2 + D * (r / (1.0 + r))


def solve_handles(X, ctrl, k0, k3, limits=LIMITS, ref=None, iters=40):
    """handle lengths (a, b) of the cubic ctrl that give curvature k0 at its start and k3 at its finish, directions kept;
    Newton from the current lengths. k0 or k3 None: only the other end's handle changes (closed form). ref: the lengths
    the limits are taken against (default the current ones). Returns (new P1, new P2) or None (no root nearby, or a
    length outside limits x ref)"""
    P0, P1, P2, P3 = (X[k] for k in ctrl)
    a0, b0 = math.hypot(*(P1 - P0)), math.hypot(*(P2 - P3))
    if a0 < RETRACTED or b0 < RETRACTED:
        return None
    ra, rb = ref if ref is not None else (a0, b0)
    d0, d3 = (P1 - P0) / a0, (P2 - P3) / b0
    c0, c3, s = _cross(d0, P3 - P0), _cross(d3, P0 - P3), _cross(d0, d3)
    lo, hi = limits
    if k3 is None or k0 is None:
        # one handle only (the other end is a corner or must not change): the near handle's length alone
        if k0 is not None:
            q = (c0 + s * b0) / (1.5 * k0) if abs(k0) > 1e-12 else -1.0
            if not q > 0 or not lo * ra <= math.sqrt(q) <= hi * ra:
                return None
            return P0 + d0 * math.sqrt(q), P2
        q = -(c3 - s * a0) / (1.5 * k3) if abs(k3) > 1e-12 else -1.0
        if not q > 0 or not lo * rb <= math.sqrt(q) <= hi * rb:
            return None
        return P1, P3 + d3 * math.sqrt(q)
    # G1 = 1.5 k0 a^2 - c0 - s b = 0 ;  G2 = -1.5 k3 b^2 - c3 + s a = 0   (d3 x d0 = -s)
    a, b = a0, b0
    for _ in range(iters):
        g1 = 1.5 * k0 * a * a - c0 - s * b
        g2 = -1.5 * k3 * b * b - c3 + s * a
        J = np.array([[3.0 * k0 * a, -s], [s, -3.0 * k3 * b]])
        det = np.linalg.det(J)
        if abs(det) < 1e-12:
            return None
        da, db = np.linalg.solve(J, [-g1, -g2])
        a, b = a + da, b + db
        if a <= 0 or b <= 0:
            return None
        if abs(da) < 1e-9 and abs(db) < 1e-9:
            break
    k0c = 2.0 / 3.0 * (c0 + s * b) / (a * a); k3c = -2.0 / 3.0 * (c3 - s * a) / (b * b)
    if abs(k0c - k0) > 1e-6 * max(abs(k0), 1e-6) + 1e-9 or abs(k3c - k3) > 1e-6 * max(abs(k3), 1e-6) + 1e-9:
        return None
    if not (lo * ra <= a <= hi * ra and lo * rb <= b <= hi * rb):
        return None
    return P0 + d0 * a, P3 + d3 * b


REAIM_WINDOW = 25.0        # deg: the re-aim searches rotations within +-this
REAIM_STEP = 0.25          # deg: search step (then refined to 0.01)


def _sgn(v, eps=1e-12):
    return 0 if abs(v) <= eps else (1 if v > 0 else -1)


def rotate_handles(X, a, b, theta):
    """X with the node a[3] == b[0]'s two handles rotated together by theta (deg) about the node, lengths kept"""
    Y = X.copy()
    N = X[a[3]]
    c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    for k in (a[2], b[1]):
        d = X[k] - N
        Y[k] = N + np.array([c * d[0] - s * d[1], s * d[0] + c * d[1]])
    return Y


def reaim_node(X, a, b, rho, signs, side0=None, neighbours=(), window=REAIM_WINDOW, step=REAIM_STEP, rung_fn=None):
    """RE-AIM: the smallest rotation of the node's tangent (both handles turned together about the node, each keeping
    its length, the node staying smooth) that gives each side its required curvature SIGN (signs = (sign kA, sign kB),
    from the drawn) and brings kA / kB towards rho. Searched over +-window deg.

    cost = |theta| / window + |log(ratio / rho)| + 2 per handle that left the drawn side of its chord (side0)
           + 5 x the worsening of the neighbouring joints' ratio (neighbours: [(ctrl_in, ctrl_out, rho), ...])
           + the rung term of rung_fn(Y) -> (penalty in u, ok): a rotation with ok False is refused (R23)
    returns dict(theta, Y=new positions, cost terms), dict(refused="R23", ...) when every sign-correct rotation thins
    a part's thinnest rung, or None (no sign-correct rotation within the window)"""
    def dev(Y, ai, bi, r):
        kA, kB = end_curvature(Y, ai, 1), end_curvature(Y, bi, 0)
        if kA is None or kB is None or kB == 0 or kA * kB * r <= 0:
            return 9.0
        return abs(math.log((kA / kB) / r))

    nb0 = [dev(X, ai, bi, r) for ai, bi, r in neighbours]

    def terms(theta):
        Y = rotate_handles(X, a, b, theta)
        kA, kB = end_curvature(Y, a, 1), end_curvature(Y, b, 0)
        if kA is None or kB is None or (_sgn(kA), _sgn(kB)) != tuple(signs):
            return None
        d = abs(math.log((kA / kB) / rho)) if kA * kB * rho > 0 else 9.0
        side = 0
        if side0 is not None:
            sA = _sgn(_cross(Y[a[3]] - Y[a[0]], Y[a[2]] - Y[a[0]])); sB = _sgn(_cross(Y[b[3]] - Y[b[0]], Y[b[1]] - Y[b[0]]))
            side = (sA != side0[0]) + (sB != side0[1])
        nb = sum(max(0.0, dev(Y, ai, bi, r) - d0) for (ai, bi, r), d0 in zip(neighbours, nb0))
        return dict(theta=theta, Y=Y, rot=abs(theta) / window, dev=d, side=side, nb=nb)

    def total(t):
        return t["rot"] + t["dev"] + 2.0 * t["side"] + 5.0 * t["nb"] + t.get("rung", 0.0)

    cands = []
    for th in np.arange(-window, window + 1e-9, step):
        t = terms(float(th))
        if t is not None:
            cands.append(t)
    if not cands:
        return None
    cands.sort(key=total)
    best, least = None, None
    for t in cands[:40]:                       # the rung term only for the cheapest candidates
        if rung_fn is not None:
            pen, ok = rung_fn(t["Y"])
            least = pen if least is None else min(least, pen)
            if not ok:
                continue
            t["rung"] = pen
        if best is None or total(t) < total(best):
            best = t
    if best is None:
        return dict(refused="R23", least_rung_loss=round(float(least or 0.0), 2),
                    sign_window=(min(c["theta"] for c in cands), max(c["theta"] for c in cands)))
    for th in np.arange(max(-window, best["theta"] - step), min(window, best["theta"] + step) + 1e-9, 0.01):     # refine
        t = terms(float(th))
        if t is None:
            continue
        if rung_fn is not None:
            pen, ok = rung_fn(t["Y"])
            if not ok:
                continue
            t["rung"] = pen
        if total(t) < total(best):
            best = t
    best["cost"] = total(best)
    return best


# ---- the driver --------------------------------------------------------------------------------------------
def _seg_kept_shape(X0, X1, ctrl, tol=0.05):
    """the cubic only translated (or did not move) between the drawn X0 and X1: it kept its drawn shape"""
    d = X1[ctrl] - X0[ctrl]
    return bool(np.all(np.abs(d - d[0]) <= tol))


def _pinned_default(glyph, X, joints, slant=0.0):
    """extremes (tangent along x, y or the italic angle) and nodes on a metric line keep their position. A horizontal
    extreme within OVERSHOOT of a metric line is a "metric extreme" (it sits on the line or its overshoot); it never
    re-aims. Other extremes ("extreme") may re-aim when a sign flip asks for it (they stop being extremes)."""
    mi = glyph.get("_mi") or {}
    name = glyph.get("glyph", "")
    lines = list(mi.get("lines_uc" if name[:1].isupper() else "lines_lc", []) or [])
    dirs = [0.0, 90.0] + ([90.0 - slant] if abs(slant) > 0.1 else [])
    out = {}
    for nd, (a, b) in joints.items():
        t = X[b[1]] - X[a[2]]
        ang = math.degrees(math.atan2(t[1], t[0])) % 180.0
        off = lambda d: min(abs(ang - d) % 180.0, 180.0 - abs(ang - d) % 180.0)
        if off(0.0) <= EXTREME_DEG and any(abs(X[nd][1] - L) <= OVERSHOOT for L in lines):
            out[nd] = "metric extreme"
        elif any(off(d) <= EXTREME_DEG for d in dirs):
            out[nd] = "extreme"
        elif any(abs(X[nd][1] - L) <= ON_LINE for L in lines):
            out[nd] = "metric line"
    return out


def harmonize_glyph(glyph, nodes=None, mode="auto", target=None, drawn=None, pinned=None, exclude=(), slant=None,
                    max_slide=MAX_SLIDE, limits=LIMITS, passes=6, tol=TOL, handles_only=(), rung_fn=None,
                    reaim_window=REAIM_WINDOW, reaim=True):
    """Harmonize the smooth curve-to-curve nodes of glyph (its contours as they are: for the solver, the MOVED outline).

    glyph      a wmparts Glyph (or a set.json layer dict); not modified
    nodes      on-curve node numbers to harmonize; None = every smooth curve-curve joint (with drawn given: only the
               joints whose two cubics the move touched)
    mode       "node" (slide), "handles" (scale handle lengths), "auto" (slide unless pinned / too far / handles_only;
               re-aim first where a side's curvature sign flipped), "reaim" (re-aim every joint it may, then as auto)
    target     "drawn" (restore the drawn curvature ratio at each node; needs drawn) or "g2" (equal curvature);
               default "drawn" when drawn is given, else "g2"
    drawn      the drawn contours (CNTR 0) for target="drawn", for the kept-shape side, and for the touched default
    pinned     {node: why} nodes that may not move (auto/node -> handles); default extremes + metric-line nodes
    exclude    node numbers never harmonized (held serifs, junctions, ...); their handles are not changed either
    rung_fn    for the re-aim: rung_fn(X) -> (penalty u, ok); harmonize_move passes the R23 rung check
    reaim      False: "auto" never re-aims (the first prototype's behavior)
    returns    (a new Glyph with the harmonized contours, report dict)"""
    contours = glyph["contours"]
    X = _flat(contours); X_in = X.copy()
    st0 = _structure(contours)
    J = _Joints(contours, X)
    ia = (glyph.get("_mi") or {}).get("ia", 0.0) if slant is None else slant
    target = target or ("drawn" if drawn is not None else "g2")
    X0 = _flat(drawn) if drawn is not None else None
    if X0 is not None and X0.shape != X.shape:
        raise ValueError("drawn and glyph do not have the same nodes")
    exclude = set(exclude)
    if pinned is None:
        pinned = _pinned_default(glyph, X, J.joint, ia)
    handles_only = set(handles_only)
    rep = dict(mode=mode, target=target, nodes=[], skipped=[], refused=[], line_joints=sorted(J.line_joint))

    # which joints
    if nodes is None:
        cand = sorted(J.joint)
        if X0 is not None:
            touched = lambda nd: any(np.any(np.abs(X[c] - X0[c]) > 0.05) for c in J.joint[nd])
            cand = [nd for nd in cand if touched(nd)]
    else:
        cand = [nd for nd in nodes if nd in J.joint]
        rep["skipped"] += [(nd, "not a smooth curve-curve joint") for nd in nodes if nd not in J.joint]
    work = {}
    for nd in cand:
        if nd in exclude:
            rep["skipped"].append((nd, "excluded")); continue
        work[nd] = J.joint[nd]

    def rho_at(nd):
        a, b = work[nd]
        if target == "g2" or X0 is None:
            return 1.0
        kA0, kB0 = end_curvature(X0, a, 1), end_curvature(X0, b, 0)
        if kA0 is None or kB0 is None or abs(kB0) < 1e-12:
            return None
        return kA0 / kB0

    rho = {}
    reaimed = set()
    for nd in list(work):
        a, b = work[nd]
        kA, kB = end_curvature(X, a, 1), end_curvature(X, b, 0)
        if kA is None or kB is None:
            rep["skipped"].append((nd, "retracted handle")); del work[nd]; continue
        if max(abs(kA), abs(kB)) < 1.0 / FLAT_R:
            rep["skipped"].append((nd, "flat")); del work[nd]; continue
        r = rho_at(nd)
        if r is None or r == 0:
            rep["skipped"].append((nd, "drawn ratio undefined")); del work[nd]; continue
        if target == "g2":
            ref = (end_curvature(X0, a, 1), end_curvature(X0, b, 0)) if X0 is not None else (kA, kB)
            if None in ref or ref[0] * ref[1] <= 0:
                rep["skipped"].append((nd, "inflection: G2 needs zero curvature")); del work[nd]; continue
            q = max(abs(ref[0]), abs(ref[1])) / max(min(abs(ref[0]), abs(ref[1])), 1e-12)
            if q > ABRUPT:
                rep["skipped"].append((nd, "abrupt drawn step x%.1f (intentional)" % q)); del work[nd]; continue
        sgn0 = (_sgn(end_curvature(X0, a, 1)), _sgn(end_curvature(X0, b, 0))) if X0 is not None else None
        if target == "g2":
            want = (sgn0 if sgn0 is not None else (_sgn(kA), _sgn(kA)))
        else:
            want = sgn0
        flip = want is not None and (_sgn(kA), _sgn(kB)) != tuple(want)
        if (flip and reaim and mode in ("auto", "reaim")) or (mode == "reaim" and want is not None):
            why = pinned.get(nd)
            if why in ("metric extreme", "metric line"):
                if flip:
                    rep["skipped"].append((nd, "sign flip at a %s: no re-aim" % why)); del work[nd]
                    continue
            else:
                side0 = None
                if X0 is not None:
                    side0 = (_sgn(_cross(X0[a[3]] - X0[a[0]], X0[a[2]] - X0[a[0]])), _sgn(_cross(X0[b[3]] - X0[b[0]], X0[b[1]] - X0[b[0]])))
                nbs = []
                for far in (a[0], b[3]):
                    if far in J.joint and far != nd:
                        fa, fb = J.joint[far]
                        rr = 1.0
                        if target != "g2" and X0 is not None:
                            k1, k2 = end_curvature(X0, fa, 1), end_curvature(X0, fb, 0)
                            rr = k1 / k2 if (k1 and k2) else 1.0
                        nbs.append((fa, fb, rr))
                T0 = X[b[1]] - X[a[2]]
                res = reaim_node(X, a, b, r, want, side0, nbs, window=reaim_window, rung_fn=rung_fn)
                if res is not None and res.get("refused"):
                    if flip:
                        rep["skipped"].append((nd, "sign flip: every sign-correct rotation (%.1f..%.1f deg) thins the part's thinnest rung, "
                                               "least by %.2f u (R23)" % (res["sign_window"] + (res["least_rung_loss"],))))
                        del work[nd]
                        continue
                    res = None
                if res is None:
                    if flip:
                        rep["skipped"].append((nd, "sign flip: no sign-correct rotation within +-%g deg" % reaim_window)); del work[nd]
                        continue
                elif flip or abs(res["theta"]) >= 0.01:
                    X[:] = res["Y"]
                    T1 = X[b[1]] - X[a[2]]
                    rep.setdefault("reaim", []).append(dict(
                        node=nd, angle=round(res["theta"], 2), flip=flip, was=why,
                        tangent_before=round(math.degrees(math.atan2(T0[1], T0[0])), 2),
                        tangent_after=round(math.degrees(math.atan2(T1[1], T1[0])), 2),
                        ratio_dev=round(res["dev"], 4), side_changes=int(res["side"]), neighbour_worse=round(res["nb"], 4),
                        rung_pen=round(float(res.get("rung", 0.0)), 2)))
                    reaimed.add(nd)
                    kA, kB = end_curvature(X, a, 1), end_curvature(X, b, 0)
        if target == "g2":
            pass
        elif kA * kB * r <= 0:
            rep["skipped"].append((nd, "curvature sign differs from the drawn")); del work[nd]; continue
        rho[nd] = r

    how = {}
    for nd in work:
        if mode == "handles" or nd in handles_only:
            how[nd] = "handles"
        elif nd in pinned and nd not in reaimed:
            how[nd] = "handles" if mode in ("auto", "reaim") else "skip"
        else:
            how[nd] = "slide"
    for nd in [n for n, h in how.items() if h == "skip"]:
        rep["skipped"].append((nd, "pinned (%s), mode=node" % pinned[nd])); del work[nd]; del how[nd]

    def mismatch(nd):
        a, b = work[nd]
        kA, kB = end_curvature(X, a, 1), end_curvature(X, b, 0)
        if kA is None or kB is None:
            return float("inf")
        t = rho[nd] * kB
        return abs(kA - t) / max(abs(kA), abs(t), 1e-12)

    before = {nd: mismatch(nd) for nd in work}
    for it in range(passes):
        # 1. handles: node targets first (from the curvatures as they are now), then each cubic solved once
        tgt = {}
        for nd in work:
            if how[nd] != "handles":
                continue
            a, b = work[nd]
            kA, kB = end_curvature(X, a, 1), end_curvature(X, b, 0); r = rho[nd]
            keepA = X0 is not None and _seg_kept_shape(X0, X, a)
            keepB = X0 is not None and _seg_kept_shape(X0, X, b)
            if keepA and not keepB:
                tA, tB = kA, kA / r
            elif keepB and not keepA:
                tA, tB = r * kB, kB
            else:
                g = math.sqrt(abs(kA * kB))
                tA, tB = math.copysign(g * math.sqrt(abs(r)), kA), math.copysign(g / math.sqrt(abs(r)), kB)
            tgt[nd] = (tA, tB)
        done = set()
        for nd in tgt:
            for seg, end in ((work[nd][0], 1), (work[nd][1], 0)):
                key = tuple(seg)
                if key in done:
                    continue
                done.add(key)
                s_, e_ = seg[0], seg[3]
                # an end that is harmonized gets its target; a smooth end that is not keeps its curvature; a corner
                # or excluded end keeps its handle (only the near handle changes)
                def end_target(nd_, e):
                    if nd_ in tgt:
                        return tgt[nd_][1] if e == 0 else tgt[nd_][0]
                    if nd_ in exclude or nd_ not in J.joint:
                        return None
                    return end_curvature(X, seg, e)
                k0, k3 = end_target(s_, 0), end_target(e_, 1)
                if k0 is None and k3 is None:
                    continue
                ref = (math.hypot(*(X_in[seg[1]] - X_in[seg[0]])), math.hypot(*(X_in[seg[2]] - X_in[seg[3]])))
                sol = solve_handles(X, seg, k0, k3, limits=limits, ref=ref)
                if sol is None:
                    if it == 0:
                        rep["refused"].append((seg[0], seg[3], "no handle solution within %.2f-%.2f x" % limits))
                    continue
                X[seg[1]], X[seg[2]] = sol
        # 2. slides (local and exact: a slide changes no other node's curvature)
        for nd in work:
            if how[nd] != "slide":
                continue
            a, b = work[nd]
            p = slide_node(X, a, b, rho[nd])
            if p is None:
                how[nd] = "handles" if mode in ("auto", "reaim") else "none"; continue
            d = math.hypot(*(p - X_in[nd]))
            if mode in ("auto", "reaim") and max_slide is not None and d > max_slide:
                how[nd] = "handles"; continue
            X[nd] = p
        if all(mismatch(nd) <= tol for nd in work):
            break
    rep["passes"] = it + 1

    for nd in sorted(work):
        sl = float(math.hypot(*(X[nd] - X_in[nd])))
        a, b = work[nd]
        hd = [float(math.hypot(*(X[k] - X_in[k]))) for k in (a[1], a[2], b[1], b[2])]
        rep["nodes"].append(dict(node=nd, how=how[nd], rho=round(float(rho[nd]), 4), before=round(float(before[nd]), 4),
                                 after=round(float(mismatch(nd)), 6), slide=round(sl, 2), handle_moves=[round(h, 2) for h in hd],
                                 pinned=pinned.get(nd), reaim=next((r_["angle"] for r_ in rep.get("reaim", []) if r_["node"] == nd), None)))
    rep["max_slide"] = max([n["slide"] for n in rep["nodes"]] or [0.0])
    rep.setdefault("reaim", [])
    rep["max_handle_move"] = float(np.max(np.hypot(*(X - X_in).T))) if len(X) else 0.0

    out = []
    k = 0
    for c in contours:
        nn = []
        for n in c["nodes"]:
            nn.append([float(X[k][0]), float(X[k][1])] + list(n[2:])); k += 1
        out.append(dict(c, nodes=nn))
    assert _structure(out) == st0, "harmonize changed the node structure (R16)"
    assert len(out) == len(contours) and all(len(p["nodes"]) == len(q["nodes"]) for p, q in zip(out, contours))
    g2 = Glyph(copy.copy(dict(glyph)))
    g2["contours"] = out
    return g2, rep


# ---- on a Move ---------------------------------------------------------------------------------------------
NEVER = ("junction", "junction-blunt", "cut", "terminal", "pinch", "ball", "rigid", "anchor")


def _harmonized(M, new, report):
    """a shallow copy of the Move whose .new is the harmonized CNTR 100 (.moved keeps the Move's own): contours_at(t)
    stays linear from drawn to harmonized (R16), so curvcomb.evaluate / wmparts.evaluate / rungcheck read it as a Move"""
    H = copy.copy(M)
    H.moved, H.new, H.harmonize_report = M.new, new, report
    return H


def harmonize_move(M, mode="auto", target="drawn", scope="touched", r23=True, junctions="never", reaim_rung_tol=0.05, **kw):
    """Harmonize a Move's CNTR 100 outline by our rules:
       never  held serifs / flags, junctions and their blunts, cut faces, terminals, pinches, balls, R24 straight
              sides, anchors, stem-end nodes (R1, R8b, R10, R11, R17, R24, R26): no slide, and their joints are skipped
       pinned extremes and metric-line nodes (R2's holds): handles only
       scope  "touched" (joints whose cubics the move touched) or "all" (every smooth joint)
       r23    a rung of a growing part newly thinner than drawn (rungcheck) backs its nearest changed joint off one
              step: a slide goes to handles (reverted_r23), a handle scale or re-aim is dropped (dropped_r23)
       reaim_rung_tol  u a re-aim may take off a part's thinnest rung (default 0.05: never thinner than the move left it)
       junctions  "never" (default) or "handles": a smooth curve-curve junction keeps the place R10 slid it to, but
              its handle lengths may change (the Geist s spine: its two largest steps are junction nodes)
    returns a copy of M with .new harmonized, .moved (the Move's own CNTR 100) and .harmonize_report"""
    from . import rungcheck
    g = getattr(M, "glyph", None) or M.g
    moved = M.contours_at(1.0)
    gm = Glyph(copy.copy(dict(g))); gm["contours"] = moved
    exclude = set(getattr(M, "held", ())) | set(getattr(M, "ball_nodes", ())) | set(getattr(M, "stem_end_nodes", ()))
    exclude |= {nd for nd, h in getattr(M, "how", {}).items() if h in NEVER}
    drawn = g["contours"]
    nodes = None if scope == "touched" else sorted(_Joints(moved).joint)
    handles_only = set(kw.pop("handles_only", ()))
    if junctions == "handles":
        jn = {nd for nd, h in getattr(M, "how", {}).items() if h in ("junction", "junction-blunt")} - set(getattr(M, "held", ()))
        exclude -= jn; handles_only |= jn
    base_thin = {(t["stroke"], t["sa"], t["sb"]) for t in rungcheck.thin(M)} if r23 else set()
    base_all = {(t["stroke"], t["sa"], t["sb"]): t for t in rungcheck.thin(M, tol=-1e9)}
    base_min = {}
    for k, t in base_all.items():
        base_min[k[0]] = min(base_min.get(k[0], 1e9), t["moved"])

    def rung_fn(Y):
        """R23 for a re-aim candidate: the largest rung shortening against the move (u), and ok = no part's thinnest
        rung thinner than the move left it, no rung newly thinner than drawn"""
        new = {k: (float(Y[k][0]), float(Y[k][1])) for k in range(len(Y))}
        rows = rungcheck.thin(_harmonized(M, new, None), tol=-1e9)
        pen, mins, ok = 0.0, {}, True
        for t in rows:
            k = (t["stroke"], t["sa"], t["sb"]); b = base_all.get(k)
            mins[k[0]] = min(mins.get(k[0], 1e9), t["moved"])
            if b is None:
                continue
            pen = max(pen, b["moved"] - t["moved"])
            if t["moved"] < t["drawn"] - rungcheck.TOL <= b["moved"]:
                ok = False
        ok = ok and all(v >= base_min.get(si, -1e9) - reaim_rung_tol for si, v in mins.items())
        return pen, ok

    reverted = []
    dropped = []
    for _ in range(8):
        hg, rep = harmonize_glyph(gm, nodes=nodes, mode=mode, target=target, drawn=drawn, exclude=exclude,
                                  slant=getattr(M, "slant", None), handles_only=handles_only,
                                  rung_fn=rung_fn if r23 else None, **kw)
        new = {}
        k = 0
        for c in hg["contours"]:
            for n in c["nodes"]:
                new[k] = (n[0], n[1]); k += 1
        H = _harmonized(M, new, rep)
        if not r23:
            break
        thin = [t for t in rungcheck.thin(H) if (t["stroke"], t["sa"], t["sb"]) not in base_thin]
        if not thin:
            H.thin_new = thin
            break
        # R23 after everything: the changed joint nearest each newly thin rung backs off one step
        # (slide -> handles; handles or re-aim -> left as the move left it)
        how = {n["node"]: n["how"] for n in rep["nodes"]
               if n["slide"] > 0.05 or max(n["handle_moves"]) > 0.05 or n.get("reaim") is not None}
        if not how:
            H.thin_new = thin
            break
        for t in thin:
            c = np.array(t["at"], float)
            nd = next((x for x in (t.get("nodes") or ()) if x in how), None)
            if nd is None:
                nd = min(how, key=lambda x: math.hypot(*(np.array(new[x]) - c)))
            if how[nd] == "slide" and nd not in handles_only:
                handles_only.add(nd); reverted.append(nd)
            else:
                exclude.add(nd); dropped.append(nd)
    rep["reverted_r23"] = reverted
    rep["dropped_r23"] = sorted(set(dropped))
    return H
