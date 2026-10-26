"""G2 tools ported from Linus Romer's Curvatura (FontForge plug-in, GPL-3.0-or-later, version 20220121), without
fontforge: the same mathematics on the solver's node lists ([[x, y, type, smooth], ...], type l / c / o, the two
off-curves of a cubic preceding its end node).

  harmonize_handles(nodes, which=None)  Curvatura's harmonizehandles_contour: at every smooth on-curve node between two
      cubics the target curvature is the mean of the curvatures on its two sides (0 at an inflection); each segment's
      handle LENGTHS are then solved (directions kept) so it reaches the targets at both its ends (Newton roots of the
      quartic, the least bending energy among several solutions). 5 passes. Node positions never move.
      `which` = the on-curve indices (in this contour's list) that may be harmonized; default every smooth node
      between two cubics. A segment end outside `which` keeps its current curvature as its target.
      One addition to Curvatura: a solution that would shrink a handle below 0.25 x or stretch it past 2.5 x its
      current length is refused and that segment keeps its handles (Curvatura takes any positive root; on a long
      merged curve it collapsed a handle to ~2 u and drew a curvature needle).
  softmerge(seg1, seg2)  Curvatura's softmerge: one cubic replacing two adjacent ones, keeping the directions AND the
      curvatures at the two outer ends. Returns the two new handles.
  curvature_at_start(P0, P1, P2, P3), adjust_handles(P0, P1, P2, P3, ka, kb)  the building blocks.
"""
import math

SMOOTH_DEG = 3.0


# ---- Curvatura's building blocks -------------------------------------------------------------------------------
def direction_at_start(P0, P1, P2, P3):
    if P1 == P0 and P2 == P3:
        return P3[0] - P0[0], P3[1] - P0[1]
    if P1 == P0:
        return P2[0] - P0[0], P2[1] - P0[1]
    return P1[0] - P0[0], P1[1] - P0[1]


def curvature_at_start(P0, P1, P2, P3):
    (a, b), (c, d), (e, f) = P0, P1, P2
    if a == c and b == d:
        return 0.0
    return 2.0 / 3.0 * (c * f - a * f - d * e + b * e + a * d - b * c) / ((b - d) ** 2 + (a - c) ** 2) ** 1.5


def energy(alpha, beta, a, b):
    """bending energy of the cubic (0,0) -> (1,0) with handle angles alpha, beta and lengths a, b (Simpson, 10 steps)"""
    sa, sb, ca, cb = math.sin(alpha), math.sin(beta), math.cos(alpha), math.cos(beta)
    xx_2 = 3 * b * cb + 3 * a * ca - 2; xx_1 = -2 * b * cb - 4 * a * ca + 2; xx_0 = a * ca
    yy_2 = -3 * b * sb + 3 * a * sa; yy_1 = -4 * a * sa + 2 * b * sb; yy_0 = a * sa
    xxx_1 = 3 * b * cb + 3 * a * ca - 2; xxx_0 = -b * cb - 2 * a * ca + 1
    yyy_1 = -3 * b * sb + 3 * a * sa; yyy_0 = b * sb - 2 * a * sa

    def curv2(t):
        xx = 3 * (xx_2 * t ** 2 + xx_1 * t + xx_0); yy = 3 * (yy_2 * t ** 2 + yy_1 * t + yy_0)
        xxx = 6 * (xxx_1 * t + xxx_0); yyy = 6 * (yyy_1 * t + yyy_0)
        den = (xx ** 2 + yy ** 2) ** 2.5
        return (xx * yyy - xxx * yy) ** 2 / den if den > 0 else 0.0
    integral = 0.0
    before = curv2(0.0)
    for tt in range(1, 11):
        t = tt / 10
        cur = curv2(t); mid = curv2(t - 0.05)
        integral += 0.1 / 6 * (before + 4 * mid + cur)
        before = cur
    return integral / 10


def _derive(co):
    n = len(co); return [co[i] * (n - i - 1) for i in range(n - 1)]


def _divide(co, r):
    res = [co[0]]
    for i in range(1, len(co) - 1):
        res.append(co[i] + res[-1] * r)
    return res


def _evaluate(co, x):
    res = co[0]
    for c in co[1:]:
        res = res * x + c
    return res


def _newton_root(co):
    der = _derive(co); x = 0.0
    for _ in range(100):
        dv = _evaluate(der, x)
        if dv == 0:
            x += 1e-9; dv = _evaluate(der, x)
            if dv == 0:
                return None
        d = _evaluate(co, x) / dv
        x -= d
        if abs(d) < 1e-9:
            return x
    return None


def _newton_roots(co):
    f = list(co)
    while f and f[0] == 0:
        f.pop(0)
    roots = []
    while len(f) > 1:
        r = _newton_root(f)
        if r is None:
            break
        roots.append(r)
        f = _divide(f, r)
    return roots


def scale_handles(alpha, beta, ka, kb, bounds=None):
    """handle lengths a, b of the cubic (0,0) -> (1,0) with angles alpha, beta so its curvature is ka at the start and
    kb at the end; (None, None) when there is no solution. bounds = ((a0, b0), (lo, hi)): only solutions within
    lo..hi x the current lengths count (an addition to Curvatura: a solution that collapses or overshoots a handle is
    the cubic failing to reach those curvatures with its directions, so the handles stay)"""
    sols = []
    sa = math.sin(alpha)
    if alpha + beta == 0:                      # ka = kb = 0 has no exact solution: the best available
        ra = None if ka == 0 else -2 * sa / (3 * ka)
        rb = None if kb == 0 else 2 * sa / (3 * kb)
        a = math.cos(alpha) if ka == 0 else (ra ** 0.5 if ra >= 0 else None)
        b = math.cos(beta) if kb == 0 else (rb ** 0.5 if rb >= 0 else None)
        if a is not None and b is not None:
            sols.append([a, b])
    else:
        sb = math.sin(beta); sba = math.sin(alpha + beta)
        for b in _newton_roots([27 * ka * kb ** 2, 0, 36 * ka * sb * kb, -8 * sba ** 3, 8 * sa * sba ** 2 + 12 * ka * sb ** 2]):
            if b > 0:
                a = (sb + 1.5 * kb * b ** 2) / sba
                if a > 0:
                    sols.append([a, b])
    if not sols:
        return None, None
    if bounds is not None:
        (a0, b0), (lo, hi) = bounds
        sols = [s_ for s_ in sols if lo * a0 <= s_[0] <= hi * a0 and lo * b0 <= s_[1] <= hi * b0]
        if not sols:
            return None, None
    return min(sols, key=lambda s: energy(alpha, beta, s[0], s[1]))


def chord_angles(P0, P1, P2, P3):
    (a, b), (g, h) = P0, P3
    l = math.hypot(g - a, h - b)
    da, db = direction_at_start(P0, P1, P2, P3)
    dab = math.hypot(da, db) or l
    da, db = da / dab, db / dab
    alpha = math.asin(max(-1.0, min(1.0, ((g - a) * db - (h - b) * da) / l)))
    dg, dh = direction_at_start(P3, P2, P1, P0)
    dgh = math.hypot(dg, dh) or l
    dg, dh = dg / dgh, dh / dgh
    beta = math.asin(max(-1.0, min(1.0, ((g - a) * dh - (h - b) * dg) / l)))
    return l, alpha, beta, da, db, dg, dh


def adjust_handles(P0, P1, P2, P3, ka, kg, limits=None, ref=None):
    """new handles (P1', P2') on the drawn directions so the cubic's curvature is ka at P0 and kg at P3;
    limits = (lo, hi): refuse solutions outside lo..hi x the reference handle lengths ref = (L1, L2) (default: the
    current ones); the handles then stay"""
    l, alpha, beta, da, db, dg, dh = chord_angles(P0, P1, P2, P3)
    if l < 1e-9:
        return P1, P2
    bounds = None
    if limits is not None:
        L1, L2 = ref if ref is not None else (math.dist(P0, P1), math.dist(P3, P2))
        bounds = ((L1 / l, L2 / l), limits)
    t, s = scale_handles(alpha, beta, ka * l, kg * l, bounds)
    if t is None or s is None:
        return P1, P2
    return (P0[0] + t * da * l, P0[1] + t * db * l), (P3[0] + s * dg * l, P3[1] + s * dh * l)


# ---- on the solver's node lists ----------------------------------------------------------------------------------
def _is_cubic_node(nodes, i):
    """on-curve node i with a cubic on both sides (o, o before it; o, o, then a curve node after it)"""
    N = len(nodes)
    if N < 7 or nodes[i][2] == "o":
        return False
    return (nodes[(i - 1) % N][2] == "o" and nodes[(i - 2) % N][2] == "o" and nodes[(i - 3) % N][2] != "o"
            and nodes[(i + 1) % N][2] == "o" and nodes[(i + 2) % N][2] == "o" and nodes[(i + 3) % N][2] == "c")


def _smooth(nodes, i):
    N = len(nodes)
    if len(nodes[i]) > 3 and nodes[i][3]:
        return True
    a, b, c = nodes[(i - 1) % N], nodes[i], nodes[(i + 1) % N]
    u = (b[0] - a[0], b[1] - a[1]); v = (c[0] - b[0], c[1] - b[1])
    lu, lv = math.hypot(*u), math.hypot(*v)
    if lu < 1e-9 or lv < 1e-9:
        return False
    return (u[0] * v[0] + u[1] * v[1]) / (lu * lv) > math.cos(math.radians(SMOOTH_DEG))


def harmonizable(nodes):
    return {i for i in range(len(nodes)) if _is_cubic_node(nodes, i) and _smooth(nodes, i)}


LIMITS = (0.25, 2.5)


def harmonize_handles(nodes, which=None, passes=5, limits=LIMITS):
    """Curvatura's harmonizehandles_contour on one contour; returns a new node list (positions of on-curves kept).
    limits: a handle may end between 0.25 and 2.5 x its length as it came in, else its segment keeps its handles
    (None = Curvatura exactly)"""
    c = [list(n) for n in nodes]
    N = len(c)
    L0 = {k: math.dist(c[k][:2], c[(k - 1) % N][:2]) if c[(k - 1) % N][2] != "o" else math.dist(c[k][:2], c[(k + 1) % N][:2])
          for k in range(N) if c[k][2] == "o"}       # each handle's length as it came in (the bounds' reference)
    cand = harmonizable(c)
    sel = cand if which is None else (set(which) & cand)
    P = lambda k: (c[k % N][0], c[k % N][1])
    for _ in range(passes):
        curv = {}
        for i in sorted(sel):
            post = curvature_at_start(P(i), P(i + 1), P(i + 2), P(i + 3))
            pre = -curvature_at_start(P(i), P(i - 1), P(i - 2), P(i - 3))
            if post * pre < 0:
                prenew = postnew = 0.0
            else:
                m = 0.5 * (abs(post) + abs(pre))
                postnew = math.copysign(m, post); prenew = math.copysign(m, pre)
            curv[i] = (pre, post, prenew, postnew)
        for i in sorted(curv):
            # the segment before i
            if (i - 3) % N in curv:
                ka = curv[(i - 3) % N][3]
            else:
                ka = curvature_at_start(P(i - 3), P(i - 2), P(i - 1), P(i))
            h1, h2 = adjust_handles(P(i - 3), P(i - 2), P(i - 1), P(i), ka, curv[i][2], limits,
                                    (L0[(i - 2) % N], L0[(i - 1) % N]))
            c[(i - 2) % N][0], c[(i - 2) % N][1] = h1; c[(i - 1) % N][0], c[(i - 1) % N][1] = h2
            # the segment after i, when its far end is not harmonized itself (a selection end)
            if (i + 3) % N not in curv:
                kg = -curvature_at_start(P(i + 3), P(i + 2), P(i + 1), P(i))
                h1, h2 = adjust_handles(P(i), P(i + 1), P(i + 2), P(i + 3), curv[i][3], kg, limits,
                                        (L0[(i + 1) % N], L0[(i + 2) % N]))
                c[(i + 1) % N][0], c[(i + 1) % N][1] = h1; c[(i + 2) % N][0], c[(i + 2) % N][1] = h2
    return c


def softmerge(seg1, seg2):
    """seg1 = (P0, P1, P2, P3), seg2 = (P3, P4, P5, P6): the handles (Q1, Q2) of one cubic P0 -> P6 keeping the
    directions and curvatures at P0 and P6"""
    P0, P1, P2, P3 = seg1; _, P4, P5, P6 = seg2
    ka = curvature_at_start(P0, P1, P2, P3)
    kb = -curvature_at_start(P6, P5, P4, P3)
    return adjust_handles(P0, P1, P5, P6, ka, kb)
