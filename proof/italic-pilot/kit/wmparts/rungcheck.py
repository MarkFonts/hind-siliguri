"""RUNG CHECK (round 6, 2026-10-24): does a move make any part THINNER than drawn?

Mark's law behind the contrast move: parts only grow. A group that takes one vector round a bowl turning more
than ~90 deg runs AGAINST the stroke somewhere (the Geist c's inner side moved as one vector: the bottom got
12 u thinner). This check measures every rung of every growing part (the dense rungs of move.Mover, node rungs
and the 12 u in-between rungs) on the drawn outline and again on the moved one -- each rung end is the same
(segment, t) point of the moved segment -- and reports rungs that got shorter.

  thin(GM, t=1.0) -> [dict(stroke, sa, sb, drawn, moved, delta, at, nodes)] for rungs shorter by > TOL u
  straight(GM)    -> straight sides of growing parts whose nodes move by different amounts across the side
                     (round 7: a straight side moves as one rigid lateral translation; > 1 u spread is a fault)
Hidden rungs (a side running on under another part), crossing / long rungs and stems/dots are skipped.
"""
import math
import numpy as np

TOL = 1.5        # u: a rung shorter than drawn by more than this is a THIN fault


def _bez(P, t):
    u = 1 - t
    return (u ** 3 * P[0][0] + 3 * u * u * t * P[1][0] + 3 * u * t * t * P[2][0] + t ** 3 * P[3][0],
            u ** 3 * P[0][1] + 3 * u * u * t * P[1][1] + 3 * u * t * t * P[2][1] + t ** 3 * P[3][1])


def _point(GM, pts, k, t):
    s0 = GM.ol.segs[k]
    sg = GM.seg_after.get(s0.gi)
    if sg is None or sg["gj"] != s0.gj:
        return None
    P0, P3 = pts[sg["gi"]], pts[sg["gj"]]
    if sg["kind"] == "curve":
        return _bez((P0, pts[sg["offs"][0]], pts[sg["offs"][1]], P3), t)
    return (P0[0] + (P3[0] - P0[0]) * t, P0[1] + (P3[1] - P0[1]) * t)


def _at(GM, S, s, pts):
    i = int(np.clip(np.searchsorted(S.al, s, side="right") - 1, 0, len(S.P) - 2))
    a, b = S.src[i], S.src[i + 1]
    if a[0] == "hidden" or b[0] == "hidden":
        return None
    u = (s - S.al[i]) / max(1e-9, S.al[i + 1] - S.al[i])
    if a[0] == b[0]:
        return _point(GM, pts, a[0], a[1] + (b[1] - a[1]) * u)
    p, q = _point(GM, pts, a[0], a[1]), _point(GM, pts, b[0], b[1])
    if p is None or q is None:
        return None
    return (p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u)


def thin(GM, t=1.0, tol=TOL):
    pts = {k: (GM.xy[k][0] + (GM.new[k][0] - GM.xy[k][0]) * t, GM.xy[k][1] + (GM.new[k][1] - GM.xy[k][1]) * t) for k in GM.xy}
    kinds = getattr(GM.M, "stroke_kind", None) or [(False, False)] * len(GM.M.stroke_rows)
    out = []
    for si, ((st, rows), (is_stem, is_dot)) in enumerate(zip(GM.M.stroke_rows, kinds)):
        if is_stem or is_dot or not GM.stroke_grows.get(si):
            continue
        SA, SB = st["A"], st["B"]
        for row in rows:
            if row.get("hid") or row.get("root") or row["r"][2] in ("end",):
                continue
            sa, sb = row["r"][0], row["r"][1]
            a0, b0 = _at(GM, SA, sa, GM.xy), _at(GM, SB, sb, GM.xy)
            a1, b1 = _at(GM, SA, sa, pts), _at(GM, SB, sb, pts)
            if None in (a0, b0, a1, b1):
                continue
            L0, L1 = math.dist(a0, b0), math.dist(a1, b1)
            if L1 < L0 - tol:
                out.append(dict(stroke=si, sa=round(sa, 1), sb=round(sb, 1), drawn=round(L0, 1), moved=round(L1, 1),
                                delta=round(L1 - L0, 1), at=(round((a0[0] + b0[0]) / 2), round((a0[1] + b0[1]) / 2)),
                                ends=(a0, b0), nodes=(row["r"][3], row["r"][4])))
    return out


STRAIGHT_TOL = 3.0    # u: a run of nodes (and handles) within this of one line is a straight side
STRAIGHT_MIN = 50.0   # u: shorter straight pieces are blunts / hairpins / end faces, not sides


def straight_runs(GM):
    """the drawn outline's straight sides of GROWING parts, found here independently of the mover: maximal runs of
    consecutive segments whose nodes and handles lie within STRAIGHT_TOL of the line through the run's two ends (all
    running the same way), at least STRAIGHT_MIN long, and that a growing stroke's side runs along (visible).
    -> [dict(nodes=[on-curve nodes in order], n=unit normal, stroke=si)]"""
    xy = GM.xy
    seg_k = {(sg.gi, sg.gj): k for k, sg in enumerate(GM.ol.segs)}
    side_of = {}
    for si, (st, rows) in enumerate(GM.M.stroke_rows):
        if not GM.stroke_grows.get(si):
            continue
        for key, S in ((0, st["A"]), (1, st["B"])):
            for src in S.src:
                if src[0] != "hidden":
                    side_of.setdefault(src[0], {}).setdefault((si, key), 0)
                    side_of[src[0]][(si, key)] += 1
    out = []
    for C in GM.contours:
        segs = C["segs"]; K = len(segs)
        def pts(sg):
            return [xy[sg["gi"]]] + [xy[o] for o in sg["offs"]] + [xy[sg["gj"]]]
        def fits(run):
            P = [p for sg in run for p in pts(sg)]
            a, b = P[0], P[-1]; L = math.dist(a, b)
            if L < 1.0:
                return False
            e = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            for sg in run:
                p0, p1 = xy[sg["gi"]], xy[sg["gj"]]
                if (p1[0] - p0[0]) * e[0] + (p1[1] - p0[1]) * e[1] <= 0:
                    return False
            return all(abs((p[0] - a[0]) * e[1] - (p[1] - a[1]) * e[0]) <= STRAIGHT_TOL for p in P)
        start = next((i for i in range(K) if not fits([segs[i]])), 0)
        cur = []
        order = [segs[(start + i) % K] for i in range(K)]
        runs = []
        for sg in order:
            if fits([sg]) and (not cur or fits(cur + [sg])):
                cur.append(sg); continue
            if cur: runs.append(cur)
            cur = [sg] if fits([sg]) else []
        if cur: runs.append(cur)
        for run in runs:
            a, b = xy[run[0]["gi"]], xy[run[-1]["gj"]]
            L = math.dist(a, b)
            if L < STRAIGHT_MIN:
                continue
            cnt = {}
            for sg in run:
                for kk, c in side_of.get(seg_k.get((sg["gi"], sg["gj"])), {}).items():
                    cnt[kk] = cnt.get(kk, 0) + c
            if not cnt:
                continue
            si, key = max(cnt, key=cnt.get)
            e = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            out.append(dict(nodes=[run[0]["gi"]] + [sg["gj"] for sg in run], n=(-e[1], e[0]), stroke=si, key=key))
    return out


def straight(GM, t=1.0, tol=1.0):
    """a straight side moves as ONE rigid lateral translation: the spread (max - min) of its nodes' moves across the
    side (along its normal). Sides spreading more than tol u are faults -> [dict(nodes, lateral, spread)]"""
    out = []
    for r in straight_runs(GM):
        lat = [((GM.new[nd][0] - GM.xy[nd][0]) * r["n"][0] + (GM.new[nd][1] - GM.xy[nd][1]) * r["n"][1]) * t for nd in r["nodes"]]
        sp = max(lat) - min(lat)
        r = dict(r, lateral=[round(x, 1) for x in lat], spread=round(sp, 1))
        if sp > tol:
            out.append(r)
    return out


def worst(GM, t=1.0):
    th = thin(GM, t)
    return min(th, key=lambda r: r["delta"]) if th else None



def _main(argv):
    """python -m wmparts.rungcheck SET.json [KEY,...] [--skip GLYPH,...]: thinned rungs and tilted straight sides at CNTR 100"""
    skip = set()
    if "--skip" in argv:
        i = argv.index("--skip"); skip = set(argv[i + 1].split(",")); argv = argv[:i] + argv[i + 2:]
    from .font import load_set
    from .groupmove import GroupMover
    G = load_set(argv[0])
    keys = sorted(G) if len(argv) < 2 else argv[1].split(",")
    for key in keys:
        if G[key]["glyph"] in skip or not any(len(c["nodes"]) for c in G[key]["contours"]):
            continue
        GM = GroupMover(G[key]); th = thin(GM)
        for r in straight(GM):
            print("%-26s straight side %s moves %s across itself: spread %.1f u" % (key, r["nodes"], r["lateral"], r["spread"]))
        if th:
            w = min(th, key=lambda r: r["delta"])
            print("%-26s %3d thin rungs, worst %5.1f u (%.0f -> %.0f) at %s" % (key, len(th), w["delta"], w["drawn"], w["moved"], w["at"]))


if __name__ == "__main__":
    import sys
    _main(sys.argv[1:])
