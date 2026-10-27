"""Round 5 · pass 2: a plain curvature comb for the proof kit (proof5s.Panel): teeth along the outline's normal, length
= curvature x gain, every cubic sampled at 40 steps; one gain for a whole sheet so the panels compare."""
import math
import numpy as np
from skeleton import bez, bez_d1, bez_d2


def segments(cs):
    for c in cs:
        ns = c["nodes"]; N = len(ns)
        ons = [i for i in range(N) if ns[i][2] != "o"]
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [(i + 1 + q) % N for q in range((j - i - 1) % N)]
            if len(offs) == 2:
                yield np.array([ns[i][:2], ns[offs[0]][:2], ns[offs[1]][:2], ns[j][:2]], float)


def comb(pn, cs, col, gain=4000.0, n=40, w=1.0, alpha=200):
    for P in segments(cs):
        ts = np.linspace(0, 1, n)
        p = bez(P, ts); d1 = bez_d1(P, ts); d2 = bez_d2(P, ts)
        sp = np.linalg.norm(d1, axis=1)
        k = (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.maximum(sp, 1e-9) ** 3
        nrm = np.stack([d1[:, 1], -d1[:, 0]], axis=1) / np.maximum(sp, 1e-9)[:, None]
        tips = p + nrm * (k * gain)[:, None]
        for a, b in zip(p, tips):
            pn.polyline([a, b], col, w, alpha)
        pn.polyline(list(tips), col, w + 0.6, 255)


# ---- the HUMP test (round 5 · pass 2c, Mark: "why are these bumpy … why aren't we looking at combs") --------------
#  A letter passes when, compared with ITS UPRIGHT (node-compatible):
#   (1) unimodal: along every cubic between two on-curve nodes, |curvature| has no dip-and-rise (an interior local
#       minimum with a rise of more than DIP of the segment's own peak on BOTH sides) that the upright's segment does not
#       have too (an inflection that the upright has, the s's spine, is the upright's own);
#   (2) G2 at smooth nodes: the relative curvature jump |ka - kb| / max(|ka|, |kb|) at every smooth node is at most
#       JUMP_X x the upright's own jump there, with a floor JUMP_FLOOR (a node the upright draws G2-continuous may jump
#       up to the floor; below it the eye does not read a step at text sizes).
#  Every failure is a SNAP. curvcomb's "minor" flags that fail it are snaps.
DIP = 0.12
JUMP_X = 1.25
PEAK_X = 1.25
PEAK_MIN = 1.3
JUMP_FLOOR = 0.05   # 0.20 let a visible step through at the s's top node (0.17 where the roman has 0.01)


def _segs(cs):
    out = []; base = 0
    for ci, c in enumerate(cs):
        ns = c["nodes"]; N = len(ns)
        ons = [i for i in range(N) if ns[i][2] != "o"]
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [(i + 1 + q) % N for q in range((j - i - 1) % N)]
            P = np.array([ns[i][:2]] + [ns[o][:2] for o in offs] + [ns[j][:2]], float)
            out.append(dict(gi=base + i, gj=base + j, P=P, curve=len(offs) == 2))
        base += N
    return out


def _kappa(P, ts):
    d1 = bez_d1(P, ts); d2 = bez_d2(P, ts); sp = np.linalg.norm(d1, axis=1)
    return (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.maximum(sp, 1e-9) ** 3


def _dips(k):
    a = np.abs(k); pk = a.max()
    if pk < 1e-6:
        return []
    out = []
    for i in range(1, len(a) - 1):
        if a[i] <= a[i - 1] and a[i] <= a[i + 1]:
            left, right = a[:i].max(), a[i + 1:].max()
            if min(left, right) - a[i] > DIP * pk:
                out.append(i)
    return out


def hump(cs, up_cs, smooth=None, K=None):
    """-> list of failures: dict(kind 'hump'|'peak'|'g2', node or seg, value, upright value). The references are the
    upright AND its plain slant at K (read from the outline's own lean when K is None): what either already has is the
    design or the shear, not a bump"""
    S, U = _segs(cs), _segs(up_cs)
    if K is None:
        a = np.array([n[:2] for c in cs for n in c["nodes"]], float); b = np.array([n[:2] for c in up_cs for n in c["nodes"]], float)
        m = np.abs(b[:, 1]) > 100
        K = float(np.median((a[m, 0] - b[m, 0]) / b[m, 1])) if m.any() else 0.0
        K = min((0.25, 1 / 3, K), key=lambda k: abs(k - K)) if min(abs(K - 0.25), abs(K - 1 / 3)) < 0.03 else K
    SL = _segs([{"closed": c["closed"], "nodes": [[n[0] + K * n[1], n[1]] + list(n[2:]) for n in c["nodes"]]} for c in up_cs])
    ts = np.linspace(0, 1, 81)
    fails = []
    for s, u, v in zip(S, U, SL):
        if not s["curve"]:
            continue
        ks, ku, kv = _kappa(s["P"], ts), _kappa(u["P"], ts), _kappa(v["P"], ts)
        if _dips(ks) and not _dips(ku) and not _dips(kv):
            i = _dips(ks)[0]
            fails.append(dict(kind="hump", seg=(s["gi"], s["gj"]), at=[round(float(v), 1) for v in bez(s["P"], [ts[i]])[0]]))
        # (3) a curvature PEAK inside the cubic that the upright does not have: its interior maximum over its larger
        # end value grows past PEAK_X x the upright's and past PEAK_MIN (option 5's bumps: unimodal, but a knot)
        def peak(k):
            a = np.abs(k); return a[3:-3].max() / max(a[0], a[-1], 1e-9)
        ps, pu = peak(ks), max(peak(ku), peak(kv))
        if ps > max(PEAK_X * pu, PEAK_MIN):
            i = 3 + int(np.argmax(np.abs(ks)[3:-3]))
            fails.append(dict(kind="peak", seg=(s["gi"], s["gj"]), ratio=round(float(ps), 2), upright=round(float(pu), 2),
                              at=[round(float(v), 1) for v in bez(s["P"], [ts[i]])[0]]))
    # G2 jumps at smooth nodes (curve on both sides, tangents within 3 deg on the upright)
    before = {s["gj"]: s for s in S}; after = {s["gi"]: s for s in S}
    ub = {u["gj"]: u for u in U}; ua = {u["gi"]: u for u in U}
    for nd in after:
        sb, sa = before.get(nd), after.get(nd)
        if sb is None or not (sb["curve"] and sa["curve"]):
            continue
        t1 = ub[nd]["P"][3] - ub[nd]["P"][2]; t2 = ua[nd]["P"][1] - ua[nd]["P"][0]
        if np.dot(t1, t2) < np.cos(np.radians(3.0)) * np.linalg.norm(t1) * np.linalg.norm(t2):
            continue
        def jump(b, a):
            kb, ka = _kappa(b, [1.0])[0], _kappa(a, [0.0])[0]
            return abs(kb - ka) / max(abs(kb), abs(ka), 1e-9)
        j, ju = jump(sb["P"], sa["P"]), jump(ub[nd]["P"], ua[nd]["P"])
        if j > max(JUMP_X * ju, JUMP_FLOOR):
            fails.append(dict(kind="g2", node=nd, jump=round(float(j), 2), upright=round(float(ju), 2)))
    return fails


def g2_repair(cs, up_cs, lo=0.75, hi=1.33, passes=4):
    """the hump test's G2 half, repaired (pass 2c): at every smooth node that fails it, the two handle LENGTHS at the node
    (directions kept, so the node stays smooth) are changed as little as possible until the jump is inside the test
    (<= max(JUMP_X x the upright's jump, JUMP_FLOOR) minus a 10 % margin), bounded lo..hi x. Repeated `passes` times (a repair moves its neighbours' end
    curvature). Returns (contours, report)."""
    from scipy.optimize import least_squares
    import copy
    cs = copy.deepcopy(cs); rep = []
    flat = lambda C_: [n for c in C_ for n in c["nodes"]]
    for _ in range(passes):
        F = [f for f in hump(cs, up_cs) if f["kind"] == "g2"]
        if not F:
            break
        S, U = _segs(cs), _segs(up_cs)
        before = {s["gj"]: s for s in S}; after = {s["gi"]: s for s in S}
        ub = {u["gj"]: u for u in U}; ua = {u["gi"]: u for u in U}
        nodes = flat(cs)
        idx = {}
        k = 0
        for ci, c in enumerate(cs):
            N = len(c["nodes"])
            for i in range(N):
                idx[k + i] = (ci, i, N)
            k += N
        for f in F:
            nd = f["node"]; sb, sa = before[nd], after[nd]
            kbu = _kappa(ub[nd]["P"], [1.0])[0]; kau = _kappa(ua[nd]["P"], [0.0])[0]
            ju = abs(kbu - kau) / max(abs(kbu), abs(kau), 1e-9)
            allowed = 0.9 * max(JUMP_X * ju, JUMP_FLOOR)
            Pb, Pa = sb["P"].copy(), sa["P"].copy()
            db = Pb[2] - Pb[3]; Lb = np.linalg.norm(db); db /= Lb
            da = Pa[1] - Pa[0]; La = np.linalg.norm(da); da /= La
            def res(x):
                Qb = Pb.copy(); Qb[2] = Pb[3] + x[0] * Lb * db
                Qa = Pa.copy(); Qa[1] = Pa[0] + x[1] * La * da
                kb, ka = _kappa(Qb, [1.0])[0], _kappa(Qa, [0.0])[0]
                j = abs(kb - ka) / max(abs(kb), abs(ka), 1e-9)
                return [20 * max(0.0, j - allowed), (x[0] - 1) * Lb / 20.0, (x[1] - 1) * La / 20.0]   # cost in units moved
            sol = least_squares(res, [1.0, 1.0], bounds=([lo, lo], [hi, hi]))
            # write the two handles back: the handle before nd is the 2nd off-curve of sb, after nd the 1st of sa
            ci, i, N = idx[nd]
            hb = (i - 1) % N; ha = (i + 1) % N
            cs[ci]["nodes"][hb][0], cs[ci]["nodes"][hb][1] = [float(v) for v in Pb[3] + sol.x[0] * Lb * db]
            cs[ci]["nodes"][ha][0], cs[ci]["nodes"][ha][1] = [float(v) for v in Pa[0] + sol.x[1] * La * da]
            rep.append(dict(node=nd, before=f["jump"], scales=[round(float(v), 3) for v in sol.x]))
    return cs, rep


def peak_repair(cs, up_cs, K, lo=0.5, hi=2.0):
    """the hump test's peak half, repaired (pass 2c): a cubic whose interior curvature peak grew past the test gets its
    two handle LENGTHS (directions kept) solved so its |curvature| profile, normalised by its own length, follows the
    plain slant's same cubic. -> (contours, report)"""
    from scipy.optimize import least_squares
    import copy
    cs = copy.deepcopy(cs); rep = []
    F = [f for f in hump(cs, up_cs, K=K) if f["kind"] == "peak"]
    if not F:
        return cs, rep
    S = {(s["gi"], s["gj"]): s for s in _segs(cs)}
    SL = {(s["gi"], s["gj"]): s for s in _segs([{"closed": c["closed"], "nodes": [[n[0] + K * n[1], n[1]] + list(n[2:]) for n in c["nodes"]]} for c in up_cs])}
    flat = [n for c in cs for n in c["nodes"]]
    ts = np.linspace(0, 1, 41)
    def prof(P):
        d1 = bez_d1(P, ts); L = np.trapezoid(np.linalg.norm(d1, axis=1), ts)
        return np.abs(_kappa(P, ts)) * L
    for f in F:
        key = tuple(f["seg"]); P = S[key]["P"]; tgt = prof(SL[key]["P"])
        d0 = P[1] - P[0]; L0 = np.linalg.norm(d0); d0 /= L0
        d3 = P[2] - P[3]; L3 = np.linalg.norm(d3); d3 /= L3
        def build(x):
            Q = P.copy(); Q[1] = P[0] + x[0] * L0 * d0; Q[2] = P[3] + x[1] * L3 * d3; return Q
        sol = least_squares(lambda x: list((prof(build(x)) - tgt) / max(tgt.max(), 1e-9)) + [0.05 * (x[0] - 1), 0.05 * (x[1] - 1)],
                            [1.0, 1.0], bounds=([lo, lo], [hi, hi]))
        Q = build(sol.x)
        U_ = {(u["gi"], u["gj"]): u for u in _segs(up_cs)}
        def smooth_end(nd, at_start):
            for u in _segs(up_cs):
                if (u["gj"] == nd if at_start else u["gi"] == nd):
                    o = U_[key]["P"]; t1 = (o[1] - o[0]) if at_start else (o[3] - o[2])
                    t0 = (u["P"][-1] - u["P"][-2]) if at_start else (u["P"][1] - u["P"][0])
                    return np.dot(t0, t1) > math.cos(math.radians(3.0)) * np.linalg.norm(t0) * np.linalg.norm(t1)
            return False
        corners = not smooth_end(key[0], True) and not smooth_end(key[1], False)
        if corners and (prof(Q)[3:-3].max() / max(prof(Q)[0], prof(Q)[-1], 1e-9)) > max(PEAK_X * (tgt[3:-3].max() / max(tgt[0], tgt[-1], 1e-9)), PEAK_MIN):
            # lengths cannot do it (the chord turned under fixed tangents): the plain slant's cubic as a similarity onto
            # this chord (R14), the end tangents turning with the chord
            R_ = SL[key]["P"]; a, b = R_[3] - R_[0], P[3] - P[0]
            s_ = np.linalg.norm(b) / max(np.linalg.norm(a), 1e-9); ang = math.atan2(b[1], b[0]) - math.atan2(a[1], a[0])
            M = s_ * np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
            Q = np.array([P[0] + M @ (r - R_[0]) for r in R_]); Q[0], Q[3] = P[0], P[3]
            sol.x = np.array([np.nan, np.nan])
        # write back: the off-curves of this cubic are the nodes after gi
        gi = key[0]
        base = 0
        for c in cs:
            N = len(c["nodes"])
            if base <= gi < base + N:
                i = gi - base
                for k, q in ((1, Q[1]), (2, Q[2])):
                    c["nodes"][(i + k) % N][0], c["nodes"][(i + k) % N][1] = float(q[0]), float(q[1])
                break
            base += N
        rep.append(dict(seg=key, scales=[round(float(v), 3) for v in sol.x], before=f["ratio"]))
    return cs, rep


def repair(cs, up_cs, K, rounds=3):
    """pass 2c's last step: peak_repair then g2_repair, repeated until the hump test is clean (or `rounds`)"""
    rep = []
    for _ in range(rounds):
        cs, r1 = peak_repair(cs, up_cs, K); cs, r2 = g2_repair(cs, up_cs); rep += r1 + r2
        if not hump(cs, up_cs, K=K):
            break
    return cs, rep
