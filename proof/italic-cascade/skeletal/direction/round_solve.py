"""Rounds solved like the o, wherever they are (Mark 2026-11-18, marking the bowls of the Bold nna and e: "will it
attempt this? i thought it would b obvious for curvy things be 'geometrically solved like o'"). Process: obliquing.

Everything is read on the outline with the slant taken back out, never from a letter's name:
  a QUARTER   a curve with one end level and the other upright, or with one end level or upright and the other running
              smoothly into a straight at any angle (the y's tail off its diagonal). It must be round: a taper is not.
              It is scaled about its own corner (where its two end
              tangents meet), across by LEVEL and up-and-down by UPRIGHT; away from the corner at upper right and lower
              left, toward it at upper left and lower right. Outside and counter alike: this is what the o gets.
  a CUT QUARTER  a curve that starts as a quarter at a level or upright end and stops at a corner. Its corner is where
              the whole quarter's would be (the round is completed by mirroring the quarter on the other side of its
              level or upright end), and the curve is scaled about that corner like any quarter. A piece that does not
              fit inside that mirrored quarter is not part of the round: it is left to follow its ends.
                - where the corner sits on a straight (a bowl meeting a stem, or the cut of an ending), the curve is
                  then cut again on that straight: the join slides along the stem, an ending's cut keeps its line and
                  its angle (every cut takes the shear) and only its corner slides along it;
                - where the corner is between two curves, it stays on the slant and the curve stretches to it.
  shared points  where two quarters meet, the point takes the mean of what each asks (on the o they ask the same).
  everything else  straights and curves that are not quarters do not move by themselves; they follow the points at
              their ends.
No size cut: a small quarter is a quarter. Only a curve under ST.SHORT (a transition) is left to follow.
Joint evening afterwards is the build's own (EVEN), the one the o gets; now that every quarter moves, it has the same\nthing to even in every round.
  round_stored(g, table=None) -> (contours, log), the same shape as stored.stored, so the cascade can use it."""
import math
import numpy as np
import cand                      # puts the build's folder on the path
import stored as ST
LEVEL, UPRIGHT = .16, .26        # the amounts of the 16-17 November proof (candidate C)
TOL = 9.0                        # degrees: how near level or upright an end must run
import os
EVEN = os.environ.get("EVEN", "2")             # joint evening after the solve. 2: the build's own, the one the o gets (the shared point slides along its tangent); 1: handle lengths only, points stay; 0: none
ROUND_SAG, ROUND_HANDLE, ROUND_LEGS = .08, .12, .25      # a round piece: bulge over chord, shorter handle over chord, shorter leg over longer leg to its corner
PARTNER_FIT = 2.0                # ...or this much, when the other edge of the same stroke end is already a piece of its round
FIT = 1.15                       # a cut piece may be this much of the mirrored quarter, in either direction, and no more
MIRROR = True                    # a cut quarter's missing extent: the quarter on the other side of its level or upright end


def _u(v):
    return v / max(np.linalg.norm(v), 1e-9)


def _ang(v):
    return abs(math.degrees(math.atan2(v[1], v[0]))) % 180


def _lev(v):
    a = _ang(v); return min(a, 180 - a) < TOL


def _upr(v):
    return abs(_ang(v) - 90) < TOL


def _blossom(P, a, b, c):
    l = lambda x, y, t: x + (y - x) * t
    q0, q1, q2 = l(P[0], P[1], a), l(P[1], P[2], a), l(P[2], P[3], a)
    r0, r1 = l(q0, q1, b), l(q1, q2, b)
    return l(r0, r1, c)


def _sub(P, a, b):
    return np.array([_blossom(P, a, a, a), _blossom(P, a, a, b), _blossom(P, a, b, b), _blossom(P, b, b, b)])


def _hit(P, L0, Ld, near):
    """parameter where the cubic P (run past its ends if need be) crosses the line through L0 along Ld, nearest to `near`"""
    nrm = np.array([-Ld[1], Ld[0]]); c = [(P[i] - L0) @ nrm for i in range(4)]
    co = [-c[0] + 3 * c[1] - 3 * c[2] + c[3], 3 * c[0] - 6 * c[1] + 3 * c[2], -3 * c[0] + 3 * c[1], c[0]]
    r = [float(x.real) for x in np.roots(co) if abs(x.imag) < 1e-7 and -.6 < x.real < 1.6]
    return min(r, key=lambda t: abs(t - near)) if r else None


KEEP = float(os.environ.get("KEEP", "0"))       # 0: off (the evening slides points); 0.6: the o's own share, fixed
FOOT_ONLY = set(os.environ.get("FOOT_ONLY", "").split())      # Mark 2026-11-21: "only apply the foot to d and g": the letters the foot rule may touch (empty: all it finds)
FOOT = os.environ.get("FOOT", "0") == "1"      # Mark's picks on the Light a, 2026-11-20: the bowl's lower right beside a stem stays on the plain slant
FOOT_COUNTER = os.environ.get("FOOT_COUNTER", "1") == "1"      # Mark 2026-11-21: "the foot doesnt might not need to touch the counter?" 0: only the outside's lower-right piece is held
FOOT_DIRS = set(os.environ.get("FOOT_DIRS", "SE").split())      # Mark 2026-11-21: "can i see what pdqgb looks like what dg DID do". SE: the lower right beside a stem (d, g, q). NW: the same piece turned half round, the upper left beside a stem (b, p): a slanted b is a slanted q turned half round
FOOT_POINT = os.environ.get("FOOT_POINT", "0") == "1"      # test, 2026-11-21 ("normalize both the top and bottom counter curves without having the part near the foot shrink away"): hold only the foot piece's end against the stem; its bottom (or top) point slides like the o's
BAR = float(os.environ.get("BAR", "0"))         # ...and a bowl running into a short level bar takes this share of its own width from the bar (his a: about 0.07)


def foot_holds(g, info):
    """Which lower-right pieces stay on the plain slant. A FOOT piece is a round's lower-right piece that ends in a
    crotch against a stem: at an inward corner on an upright straight (the a), or buried in another contour's ink (the
    d's ring under its stem). The counter's lower-right quarter of the same stroke (its bottom point just above the
    outside's, ink between them) goes with it: both edges of a stroke are read alike."""
    cs = g["contours"]; hold = set(); foots = []
    pts = lambda c: ST.sample_contour(c, 40)
    allink = ST.sk([pts(c) for c in cs], lambda q: (float(q[0]), float(q[1]))); oth = {}
    for r in info:
        buried = False
        if len(cs) > 1:
            # buried: the piece's upper end lies inside another contour AND has the letter's ink on every side of it
            # (the d's ring under its stem). A counter's own edge has white on one side and is not buried.
            if r["ci"] not in oth: oth[r["ci"]] = ST.sk([pts(c) for i, c in enumerate(cs) if i != r["ci"]], lambda q: (float(q[0]), float(q[1])))
            U = r["U"]
            buried = oth[r["ci"]].contains(float(U[0]), float(U[1])) and all(allink.contains(float(U[0] + dx), float(U[1] + dy)) for dx, dy in ((7, 0), (-7, 0), (0, 7), (0, -7)))
        up = 1 if r.get("dirn") == "NW" else -1
        outside = not allink.contains(float(r["E"][0]), float(r["E"][1] + 7 * up))      # white under its bottom point (over its top point, for an upper-left piece): the stroke's outside edge
        if (r["crotch"] or buried) and outside: foots.append(r); hold.add((r["ci"], r["k"]))
    if not FOOT_COUNTER: return hold
    for f in foots:
        for r in info:
            if (r["ci"], r["k"]) in hold: continue
            if r.get("dirn") != f.get("dirn"): continue
            dx = r["E"][0] - f["E"][0]; dy = (r["E"][1] - f["E"][1]) * (-1 if f.get("dirn") == "NW" else 1); mid = (r["E"] + f["E"]) / 2
            if abs(dx) <= .45 * max(f["w"], 60) and 0 < dy <= 260 and allink.contains(float(mid[0]), float(mid[1])): hold.add((r["ci"], r["k"]))
    return hold


# ONE READING, BY POINT (Mark 2026-11-20: "theyre supposed to be the same points to begin with whole things arent applying
# to the same points no matter the proportions"). The masters have the same points in the same order, so each curve is
# read ONCE for the letter and that reading is applied to the same curve in every weight, whatever its proportions
# there. FORCE[glyph name] = {(contour, curve): ("quarter", None) or ("cut", corner end)}; shared_reading() fills it:
# a curve read as a piece of a round in ANY weight is one in all of them (the first weight that reads it names the
# kind). No size or ratio test is asked of the other weights again.
FORCE = {}
HOLDS = {}       # glyph name -> the foot pieces held, found once on the reference weight and applied by point to all


def reading_of(g):
    keep = FORCE.pop(g.get("glyph"), None); R = {}
    try:
        round_stored(dict(g), _hold=set(), _reading=R)
    finally:
        if keep is not None: FORCE[g.get("glyph")] = keep
    return R


def shared_reading(name, glyphs):
    """glyphs: the same letter in each weight, the reference weight first. Records and returns the one reading."""
    F = {}
    for g in glyphs:
        for k, v in reading_of(dict(g, glyph=name)).items(): F.setdefault(k, v)
    FORCE[name] = F
    if FOOT and glyphs:
        HOLDS.pop(name, None); g0 = dict(glyphs[0], glyph=name); info = []
        round_stored(g0, _collect=info); HOLDS[name] = foot_holds(g0, info)
    return F


def round_stored(g, table=None, g2=True, _hold=None, _collect=None, _reading=None):
    if FOOT and (not FOOT_ONLY or g.get("glyph") in FOOT_ONLY) and _hold is None and _collect is None and _reading is None:
        if g.get("glyph") in HOLDS: return round_stored(g, table, g2, _hold=HOLDS[g.get("glyph")])
        info = []; round_stored(g, table, g2, _collect=info)
        return round_stored(g, table, g2, _hold=foot_holds(g, info))
    forced = FORCE.get(g.get("glyph"))
    cs = ST.shear(g["contours"], ST.HIND_K, ST.HIND_Y0); out = []; log = []; A = np.array([LEVEL, UPRIGHT])
    for ci, c in enumerate(cs):
        segs = ST.segments(c); n = len(segs); P = [ST.un(np.array(ST.seg_ctrl(c, s), float)) for s in segs]
        cur = [len(s[1]) == 2 for s in segs]
        t0 = [_u(p[1] - p[0]) if np.linalg.norm(p[1] - p[0]) > 1e-6 else _u(p[-1] - p[0]) for p in P]
        t1 = [_u(p[-1] - p[-2]) if np.linalg.norm(p[-1] - p[-2]) > 1e-6 else _u(p[-1] - p[0]) for p in P]
        smooth = [float(t1[k] @ t0[(k + 1) % n]) > .995 for k in range(n)]          # smooth[k]: the joint after curve k
        on = np.array([p[0] for p in P]); area = .5 * float(np.sum(on[:, 0] * np.roll(on[:, 1], -1) - np.roll(on[:, 0], -1) * on[:, 1]))
        inward = [(t1[k][0] * t0[(k + 1) % n][1] - t1[k][1] * t0[(k + 1) % n][0]) * area < 0 for k in range(n)]   # the outline turns inward at the joint after k
        big = [cur[k] and np.linalg.norm(P[k][3] - P[k][0]) >= ST.SHORT for k in range(n)]
        def round_enough(k, q=None):
            """a piece of a round bulges and has two real handles; a taper (the M's long inner edges, the crotch of a v)
            is nearly straight or turns only at its very end, and is not one"""
            p = P[k]; ch = np.linalg.norm(p[3] - p[0]); mid = (p[0] + 3 * p[1] + 3 * p[2] + p[3]) / 8
            if np.linalg.norm(mid - (p[0] + p[3]) / 2) < ROUND_SAG * ch: return False
            if min(np.linalg.norm(p[1] - p[0]), np.linalg.norm(p[2] - p[3])) < ROUND_HANDLE * ch: return False
            if q is not None:
                l0, l3 = np.linalg.norm(p[0] - q), np.linalg.norm(p[3] - q)
                if min(l0, l3) < ROUND_LEGS * max(l0, l3): return False
            return True
        # a quarter: one end level and the other upright; or one end level or upright and the other running smoothly
        # into a straight at any angle (the y's tail off its diagonal): the round stops where the straight takes over
        def into_line(k, end):
            j = (k - 1) % n if end == 0 else (k + 1) % n; return (not cur[j]) and (smooth[(k - 1) % n] if end == 0 else smooth[k])
        def axial(v): return _lev(v) or _upr(v)
        quarter = [big[k] and ((_lev(t0[k]) and _upr(t1[k])) or (_upr(t0[k]) and _lev(t1[k]))
                                or (axial(t0[k]) and smooth[(k - 1) % n] and not axial(t1[k]) and into_line(k, 3))
                                or (axial(t1[k]) and smooth[k] and not axial(t0[k]) and into_line(k, 0))) for k in range(n)]
        Q = [None] * n; S = [None] * n; cut = [None] * n      # corner, signed amounts, and for a cut quarter which end (0 or 3) is the corner end
        for k in range(n):
            if quarter[k]:
                q = ST._corner(P[k])
                if q is not None and np.linalg.norm(q - (P[k][0] + P[k][3]) / 2) >= 3 and round_enough(k, q): Q[k] = q
        toolong = [False] * n

        def try_cut(k, fit):
            if not big[k] or quarter[k]: return
            p = P[k]; s0 = smooth[(k - 1) % n]; s3 = smooth[k]
            e = 0 if (s0 and not s3 and (_lev(t0[k]) or _upr(t0[k]))) else 3 if (s3 and not s0 and (_lev(t1[k]) or _upr(t1[k]))) else None
            if e is None: return
            E = p[e]; C = p[3 - e]; tE = t0[k] if e == 0 else t1[k]; nb = (k - 1) % n if e == 0 else (k + 1) % n; level = _lev(tE)
            ax = 0 if level else 1                                     # the axis the missing extent lies along
            if abs(C[ax] - E[ax]) < 3 or abs(C[1 - ax] - E[1 - ax]) < 3: return
            if MIRROR and Q[nb] is not None and cut[nb] is None:
                ext = abs(P[nb][3][ax] - P[nb][0][ax]); oth = abs(P[nb][3][1 - ax] - P[nb][0][1 - ax])
                # a piece longer or deeper than the quarter it would complete is not a piece of that round (the 2's
                # diagonal, the long arm of a 6 or 9 running over its top): it is a run and follows its ends
                if abs(C[ax] - E[ax]) > fit * ext or abs(C[1 - ax] - E[1 - ax]) > fit * oth: toolong[k] = True; return
            else: ext = 1.5 * abs(C[ax] - E[ax])                       # no quarter beside it to mirror (a hook off a stem)
            ext = max(ext, 1.05 * abs(C[ax] - E[ax]))                  # the whole quarter is at least as long as the piece we have
            q = E.copy(); q[ax] = E[ax] + math.copysign(ext, C[ax] - E[ax])
            mid = (p[0] + 3 * p[1] + 3 * p[2] + p[3]) / 8; ch = (p[0] + p[3]) / 2
            if float((mid - ch) @ (q - ch)) <= 0: return               # it bulges away from that corner: a run, not a piece of a quarter
            if min(np.linalg.norm(p[1] - p[0]), np.linalg.norm(p[2] - p[3])) < ROUND_HANDLE * np.linalg.norm(p[3] - p[0]): return   # a taper, turning only at its very end
            Q[k] = q; cut[k] = 3 - e
        for k in range(n): try_cut(k, FIT)
        # the two edges of one stroke end are read alike: where one edge of an ending is a piece of its round and the
        # other only missed the size test (an inside edge is measured against a smaller quarter), the other is one too
        for j in range(n):
            if cur[j]: continue
            a_, b_ = (j - 1) % n, (j + 1) % n
            for x, y in ((a_, b_), (b_, a_)):
                if Q[x] is not None and cut[x] is not None and Q[y] is None and toolong[y]: try_cut(y, PARTNER_FIT)
        if forced is not None:
            # the letter's one reading, applied to these same curves whatever their proportions in this weight
            Q = [None] * n; cut = [None] * n
            for k in range(n):
                v = forced.get((ci, k))
                if v is None or not cur[k]: continue
                if v[0] == "quarter":
                    q = ST._corner(P[k])
                    if q is not None: Q[k] = q
            for k in range(n):
                v = forced.get((ci, k))
                if v is None or v[0] != "cut" or not cur[k]: continue
                p = P[k]; e = 3 - v[1]; E = p[e]; C = p[3 - e]; tE = t0[k] if e == 0 else t1[k]; nb = (k - 1) % n if e == 0 else (k + 1) % n
                a_ = _ang(tE); ax = 0 if min(a_, 180 - a_) <= abs(a_ - 90) else 1
                if MIRROR and Q[nb] is not None and forced.get((ci, nb), ("",))[0] == "quarter": ext = abs(P[nb][3][ax] - P[nb][0][ax])
                else: ext = 1.5 * abs(C[ax] - E[ax])
                ext = max(ext, 1.05 * abs(C[ax] - E[ax]))
                q = E.copy(); q[ax] = E[ax] + math.copysign(ext, C[ax] - E[ax] if abs(C[ax] - E[ax]) > 1e-6 else 1.0)
                Q[k] = q; cut[k] = v[1]
        if _reading is not None:
            for k in range(n):
                if Q[k] is not None: _reading[(ci, k)] = ("cut", cut[k]) if cut[k] is not None else ("quarter", None)
            continue
        for k in range(n):
            if Q[k] is None: continue
            d = Q[k] - (P[k][0] + P[k][3]) / 2; S[k] = A if d[0] * d[1] > 0 else -A
            log.append((ci, k, ("N" if d[1] > 0 else "S") + ("E" if d[0] > 0 else "W"), "cut quarter" if cut[k] is not None else "quarter", [round(float(x), 3) for x in S[k]]))
        if _collect is not None:
            for k in range(n):
                if S[k] is None: continue
                d = Q[k] - (P[k][0] + P[k][3]) / 2
                dirn = ("N" if d[1] > 0 else "S") + ("E" if d[0] > 0 else "W")
                if dirn not in ("SE", "NW") or dirn not in FOOT_DIRS: continue      # lower right; and, when asked, upper left
                lev = 0 if (_lev(t0[k]) and cut[k] != 0) else 3              # its level end (the bottom point); the other end is the upper one
                up_joint = k if lev == 0 else (k - 1) % n; other = (k + 1) % n if lev == 0 else (k - 1) % n
                crotch = cut[k] is not None and (not cur[other]) and inward[up_joint] and _upr(_u(P[other][-1] - P[other][0]))
                _collect.append(dict(ci=ci, k=k, E=P[k][lev], U=P[k][3 - lev], crotch=bool(crotch), w=abs(P[k][3][0] - P[k][0][0]), dirn=dirn))
            continue
        HJ = set()
        if _hold:
            for (ci_, k_) in _hold:
                if ci_ != ci: continue
                if FOOT_POINT:
                    HJ.add((k_ - 1) % n if _upr(t0[k_]) else k_); log.append((ci, k_, "", "its end against the stem held (foot point)", [0, 0])); continue
                S[k_] = None; HJ |= {k_, (k_ - 1) % n}; log.append((ci, k_, "", "held on the plain slant (foot)", [0, 0]))
        own = lambda k, pt: S[k] * (pt - Q[k])                         # what curve k asks of one of its points
        D = [np.zeros(2) for _ in range(n)]; recut = {}               # D[k]: the move of the point after curve k
        other_ink = None
        for k in range(n):
            j = (k + 1) % n; ask = []
            if k in HJ: continue                                        # an end of a held foot piece: it stays on the plain slant
            if S[k] is not None and cut[k] != 3: ask.append(own(k, P[k][-1]))
            if S[j] is not None and cut[j] != 0: ask.append(own(j, P[j][0]))
            if smooth[k]:
                if ask: D[k] = np.mean(ask, axis=0)
                # KEEP: a point shared by two quarters (the top, bottom or side point of a round) takes this share of
                # what they ask, the same in every round, and the joint evening afterwards moves handles only. Without
                # it the evening slides those points back by a different amount in every letter (o about 60%, the
                # Light P 29%, the Light R 100% outside and 16% inside).
                if KEEP and len(ask) == 2: D[k] = D[k] * KEEP
                if ask and cur[k] != cur[j]:                            # a quarter running into a straight: the point slides along the straight, no further than most of it
                    Ln = P[j] if not cur[j] else P[k]; Ld_ = _u(Ln[-1] - Ln[0]); D[k] = float(D[k] @ Ld_) * Ld_      # along the straight only, whatever its angle
                    lim = .8 * np.linalg.norm(Ln[-1] - Ln[0]); nm = np.linalg.norm(D[k])
                    if nm > lim > 0: D[k] = D[k] * lim / nm
                    # a round running into a short level bar that ends at a corner (the a's bowl off its stem): the
                    # point does not slide along the bar by the round's amount; the round takes BAR of its own width
                    # from the bar instead (the point moves toward the bar's far end)
                    if BAR:
                        x_ = k if cur[k] else j; far_corner = (not smooth[j]) if not cur[j] else (not smooth[(k - 1) % n])
                        w_ = abs(P[x_][3][0] - P[x_][0][0]); Ll = np.linalg.norm(Ln[-1] - Ln[0])
                        if far_corner and _lev(Ld_):      # no size test: the same bar must read the same in every weight, on both its edges
                            away = Ld_ if not cur[j] else -Ld_
                            D[k] = away * min(BAR * w_, .8 * Ll); log.append((ci, x_, "bar", "takes from its bar", [round(float(v), 1) for v in D[k]]))
                elif ask and len(ask) == 1:
                    # a quarter running into a short curve that itself stops at a corner (the e's side just above its
                    # bar): the point slides no further than that short curve can give and stay a curve (the build's
                    # own squeeze limit)
                    x = j if S[j] is None else k; far_smooth = smooth[j] if x == j else smooth[(k - 1) % n]
                    if not far_smooth:
                        Lx = np.linalg.norm(P[x][-1] - P[x][0]); lim = max(0.0, min(.65 * Lx, Lx - 1.25 * ST.SHORT)); nm = np.linalg.norm(D[k])
                        if nm > lim: D[k] = D[k] * (lim / nm) if nm > 0 else D[k]
            else:
                for x, end, other in ((k, 3, j), (j, 0, k)):
                    if S[x] is None or cut[x] != end or cur[other]: continue
                    # the corner sits on a straight: a join on a stem, or an ending's cut. An ending hidden under
                    # another contour's ink (the G's arc under its jaw) must stay hidden: its corner keeps its place
                    if len(g["contours"]) > 1:
                        if other_ink is None: other_ink = {}
                        if ci not in other_ink: other_ink[ci] = ST.sk([ST.sample_contour(o, 40) for i_, o in enumerate(g["contours"]) if i_ != ci], lambda q_: (float(q_[0]), float(q_[1])))
                        mid_ = (P[other][0] + P[other][-1]) / 2
                        if other_ink[ci].contains(float(mid_[0]), float(mid_[1])): continue
                    recut[x] = (end, other, k)

        def boxmap(p, d0, d1):
            q = p.copy()
            for a in (0, 1):
                span = p[-1][a] - p[0][a]
                if abs(span) > 2: f = (p[:, a] - p[0][a]) / span
                else:
                    chd = p[-1] - p[0]; f = ((p - p[0]) @ chd) / max(float(chd @ chd), 1e-9)
                q[:, a] = p[:, a] + d0[a] + f * (d1[a] - d0[a])
            return q
        # a cut quarter on a straight: scale it whole about its corner, find where that curve now meets the straight
        # (crossing it, or run on along its own end direction), and let the corner slide there along the straight
        for k, (end, other, joint) in recut.items():
            p = P[k]; full = boxmap(p, own(k, p[0]) if end == 0 else D[(k - 1) % n], own(k, p[-1]) if end == 3 else D[k])
            Ln = P[other]; Ld = _u(Ln[-1] - Ln[0]); L0 = p[end]; pt = None
            t = _hit(full, L0, Ld, 0.0 if end == 0 else 1.0)
            if t is not None and -1e-6 <= t <= 1 + 1e-6: pt = _blossom(full, t, t, t)
            else:
                e_ = full[0] if end == 0 else full[3]; dirn = _u(full[0] - full[1]) if end == 0 else _u(full[3] - full[2])   # outward past the corner end
                M = np.array([dirn, -Ld]).T
                if abs(np.linalg.det(M)) > 1e-6:
                    u_, v_ = np.linalg.solve(M, L0 - e_)
                    if 0 <= u_ <= np.linalg.norm(p[3] - p[0]): pt = L0 + v_ * Ld
            if pt is None: continue
            mv = float((pt - L0) @ Ld) * Ld
            if np.linalg.norm(mv) > .8 * np.linalg.norm(Ln[-1] - Ln[0]): continue
            D[joint] = mv; log.append((ci, k, "join", "cut again on the straight", [round(float(x), 1) for x in mv]))
        New = [boxmap(p, D[(k - 1) % n], D[k]) for k, p in enumerate(P)]
        nodes = [list(x) for x in c["nodes"]]
        for sg, p in zip(segs, New):
            R = ST.re_(p); i, o, j = sg
            for idx, q in ((i, R[0]), (j, R[-1])): nodes[idx][0], nodes[idx][1] = float(q[0]), float(q[1])
            for idx, q in zip(o, R[1:3] if len(o) == 2 else []): nodes[idx][0], nodes[idx][1] = float(q[0]), float(q[1])
        c2 = dict(c, nodes=nodes)
        skip = {j for k in ST.tiny_of(c2) for j in (k, (k - 1) % n)}
        ev = "0" if KEEP else EVEN        # with a fixed share nothing is evened afterwards: evening, by points or by handles, treated like letters differently
        out.append(c2 if (ev == "0" or not g2) else ST._g2_handles_only(c2, skip) if ev == "1" else ST._g2_free(c2, skip))
    if _reading is not None: return None, _reading
    if _collect is not None: return None, _collect
    assert ST.structure(out) == ST.structure(g["contours"])
    return out, log
