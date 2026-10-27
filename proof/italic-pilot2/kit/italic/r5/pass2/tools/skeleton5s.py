"""Round 5 · s round: the skeleton base for the s with I15 (terminals ride), I16 (rigid spine piece) and I17 (re-seat
side extremes) in place of round 5's I12 (spine edges turned with refitted handles) and I14 (terminals held at the
roman angle). I10 (two-angle shear, rho 0.70) and I11 (nu 0) are round 5's, unchanged (skeleton.py, frozen copy).

    Skeleton5s(g_up, terminal="a", psi=1.18, i16=True, i17=True, K=None)
        .contours      the base (same nodes, order, types, smooth flags as the upright: asserted by the caller)
        .report()      round 5's report + terminals (I15), spine (I16), reseat (I17)

The rules (also in italicmove.py's docstring, I15-I17):

 I15 terminals ride. A terminal (the non-round nodes between two round nodes: an s's beak and its cut) is carried
     as ONE piece by the motion of the two sides it ends: its first node is the end of the side coming in, its last
     node the end of the side going out; each side's motion there is that side's own map (I10: its round run's lean
     about its part's centre). The piece's translation is the mean of the two sides' moves at those two end nodes, so
     the cut face goes where its sides go; it is not held in the group rules (the cut faces then follow R12 / I7 like
     any cut face). The piece's linear part, i.e. its cut angle, is a CLASS choice (`terminal=`):
       "roman"  every terminal keeps its roman shape (translated)
       "shear"  every terminal keeps the plain shear (sheared about its centre)
       "a"      the LEADING terminal (the stroke's entry: the terminal in the upper half of its contour, which hangs
                from the x-height) keeps the roman angle; the TRAILING one (the exit, standing near the baseline) keeps
                the shear
       "b"      a cut keeps its angle RELATIVE TO ITS STROKE: the piece turns rigidly by the turn of the stroke at the
                terminal (the mean of the two sides' end tangents, upright vs their side maps)
 I16 rigid spine piece. The spine (the two cubics of an s that hold the curvature sign change between the two bowls,
     from bowl junction node to bowl junction node) turns as ONE piece, nodes AND handles, about its centre m (the mean
     of the two edges' inflection points), placed where the shear puts m: T(p) = S(m) + R(-psi theta)(p - m). Handle
     lengths are unchanged (a rotation). The connecting curve on the other side of each junction node is the base
     curve (I10) turned and scaled onto its new chord as one piece (R14); then R15: at the junction the rigid spine's
     tangent wins (the bowl-side handle is turned onto it, its length kept from the similarity), at the far node the
     base tangent is kept.
 I17 re-seat side extremes (rule G). After the lean, every node that is a side extreme on the upright (a round node
     whose tangent is vertical within 3 deg) slides along its own outline to the nearest point of TRUE vertical tangent
     on the base; its handles become vertical. The shortened neighbour is split exactly (de Casteljau); the lengthened
     one is refitted, least squares to the base outline it now spans, with its far node and far tangent kept: shape
     neutral up to the reported deviation. Node count and order never change.
     A node that I16 carries (a spine junction) is NOT re-seated: the rigid piece wins (`i17=True`, the default). Mark's
     drawn italic s says so: his four spine-end nodes keep a tangent 13-18 deg off vertical (the spine's turn) and sit
     19-41 u from the true vertical tangent of his own outline; re-seating them slid them 25-43 u back along the curve,
     against his drawing (readings/fit5s.json, NOTES). `i17="all"` re-seats them too, for the comparison only. On the s
     every side extreme is a spine junction, so I17 does nothing to the s; it stays in for the o, the p's bowl, ...
"""
import sys, os, math, copy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
import carry as C
from skeleton import Skeleton, Map, translate, bez, bez_d1, curvature_sign_changes, RHO, NU_COEF

TERMINALS = ("roman", "shear", "a", "b", "flip")     # pass 2 adds "flip" (leading shear, trailing roman), for the comparison only


def unit(v):
    v = np.asarray(v, float); L = np.linalg.norm(v)
    return v / L if L > 1e-12 else v


def rot(a):
    return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])


def split(P, t):
    """de Casteljau: the cubic P split at t -> (left, right)"""
    P = np.asarray(P, float)
    a = P[:-1] + t * (P[1:] - P[:-1]); b = a[:-1] + t * (a[1:] - a[:-1]); c = b[0] + t * (b[1] - b[0])
    return np.array([P[0], a[0], b[0], c]), np.array([c, b[1], a[2], P[3]])


def fit_fixed_tangents(Q0, d0, Q3, d3, pts, iters=25):
    """least-squares cubic Q0, Q0 + a d0, Q3 + b d3, Q3 to pts (re-parametrised); returns (P, max deviation)"""
    pts = np.asarray(pts, float); Q0 = np.asarray(Q0, float); Q3 = np.asarray(Q3, float); d0 = unit(d0); d3 = unit(d3)
    al = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]; T = al / al[-1]
    ts = np.linspace(0, 1, 601)
    for _ in range(iters):
        u = 1 - T; wa = 3 * u * u * T; wb = 3 * u * T * T
        base = (u ** 3 + wa)[:, None] * Q0 + (wb + T ** 3)[:, None] * Q3
        r = pts - base; va = wa[:, None] * d0; vb = wb[:, None] * d3
        M = np.array([[np.sum(va * va), np.sum(va * vb)], [np.sum(va * vb), np.sum(vb * vb)]])
        a, b = np.linalg.solve(M, [np.sum(va * r), np.sum(vb * r)])
        a = max(a, 1.0); b = max(b, 1.0)
        P = np.array([Q0, Q0 + a * d0, Q3 + b * d3, Q3])
        cv = bez(P, ts)
        dd = np.linalg.norm(pts[:, None, :] - cv[None, :, :], axis=2)
        T = ts[np.argmin(dd, axis=1)]
    return P, float(dd.min(axis=1).max())


def vertical_ts(P):
    """parameters in [0, 1] where the cubic's tangent is vertical (dx/dt = 0)"""
    p0, p1, p2, p3 = [float(q[0]) for q in P]
    a = -p0 + 3 * p1 - 3 * p2 + p3; b = 2 * (p0 - 2 * p1 + p2); c = p1 - p0     # dx/dt / 3 = a t^2 + b t + c
    out = []
    if abs(a) < 1e-12:
        if abs(b) > 1e-12:
            out = [-c / b]
    else:
        D = b * b - 4 * a * c
        if D >= 0:
            out = [(-b - math.sqrt(D)) / (2 * a), (-b + math.sqrt(D)) / (2 * a)]
    return sorted(t for t in out if -1e-9 <= t <= 1 + 1e-9)


class Skeleton5s(Skeleton):
    def __init__(self, g_up, terminal="a", psi=1.18, i16=True, i17=True, rho=RHO, nu_coef=NU_COEF, IM0=None, K=None):
        assert terminal in TERMINALS, terminal
        self.terminal_rule = terminal; self.i16 = i16; self.i17 = i17
        self.term_report = []; self.spine_report = []; self.reseat_report = []
        Skeleton.__init__(self, g_up, rules=("I10", "I11"), rho=rho, nu_coef=nu_coef, psi=psi, IM0=IM0, K=K)

    # -- I15 ---------------------------------------------------------------------------------------------------------
    def _maps(self):
        Skeleton._maps(self)                      # round 5's maps without I12 / I14: a terminal takes its part's map
        U = self.U
        self.terminal_nodes = set()
        for G_ in self.groups:
            if not G_.get("terminal"):
                continue
            first, last = G_["nodes"][0], G_["nodes"][-1]
            rp, rn = self.run_of.get(G_["prev"], []), self.run_of.get(G_["next"], [])
            if not rp or not rn:
                continue
            Mp = Map.mean([self.run_map(ri) for ri in rp]); Mn = Map.mean([self.run_map(ri) for ri in rn])
            ci = G_["ci"]
            ys = [U.xy[nd][1] for nd in U.contours[ci]["ons"]]
            cen = np.mean([U.xy[nd] for nd in G_["nodes"]], axis=0)
            leading = cen[1] > (min(ys) + max(ys)) / 2.0
            # the stroke direction at the terminal: both sides' end tangents, pointing into the terminal
            t_in = unit(bez_d1(U.ctl(U.seg_before[first]), [1.0])[0]) if U.seg_before[first]["kind"] == "curve" else unit(U.xy[first] - U.xy[U.seg_before[first]["gi"]])
            sa = U.seg_after[last]
            t_out = -unit(bez_d1(U.ctl(sa), [0.0])[0]) if sa["kind"] == "curve" else -unit(U.xy[sa["gj"]] - U.xy[last])
            d_up = unit(t_in + t_out)
            d_new = unit(unit(Mp.L @ t_in) + unit(Mn.L @ t_out))
            turn = math.atan2(d_new[1], d_new[0]) - math.atan2(d_up[1], d_up[0])
            turn = (turn + math.pi) % (2 * math.pi) - math.pi
            rule = self.terminal_rule
            if rule == "a":
                rule = "roman" if leading else "shear"
            elif rule == "flip":
                rule = "shear" if leading else "roman"
            if rule == "roman":
                L = np.eye(2)
            elif rule == "shear":
                L = self.S.L.copy()
            else:
                L = rot(turn)
            t = np.mean([Mp(U.xy[first]) - L @ U.xy[first], Mn(U.xy[last]) - L @ U.xy[last]], axis=0)
            m = Map(L, t)
            how = "terminal rides its sides (I15, %s%s)" % (rule, ", leading" if leading else ", trailing")
            for nd in G_["nodes"]:
                self.map[nd] = m; self.why[nd] = how; self.terminal_nodes.add(nd)
            # the cut: the longest straight segment inside the terminal
            segs = [U.seg_after[nd] for nd in G_["nodes"][:-1] if U.seg_after[nd]["kind"] == "line"]
            cut = max(segs, key=lambda s: np.linalg.norm(U.xy[s["gj"]] - U.xy[s["gi"]])) if segs else None
            def ang(v):
                return math.degrees(math.atan2(v[0], v[1]))         # from vertical, + = top leans right
            rec = dict(nodes=G_["nodes"], leading=bool(leading), rule=rule, stroke_turn_deg=round(math.degrees(turn), 2),
                       move_in=[round(float(v), 2) for v in Mp(U.xy[first]) - U.xy[first]],
                       move_out=[round(float(v), 2) for v in Mn(U.xy[last]) - U.xy[last]])
            if cut is not None:
                e = U.xy[cut["gj"]] - U.xy[cut["gi"]]; e = e if e[1] > 0 else -e
                rec.update(cut=(cut["gi"], cut["gj"]), cut_roman_deg=round(ang(e), 2), cut_slant_deg=round(ang(self.S.L @ e), 2),
                           cut_new_deg=round(ang(L @ e), 2))
            self.term_report.append(rec)

    # -- apply: base maps, then I16, then I17 ----------------------------------------------------------------------
    def _apply(self):
        U = self.U
        new = [None] * len(U.xy)
        for i in range(len(U.xy)):
            nd = i if U.typ[i] != "o" else U.owner[i]
            new[i] = self.map[nd](U.xy[i])
        self.new = new
        self.base_new = [p.copy() for p in new]
        self.spine_fit = []
        if self.i16:
            self._spine_rigid()
        if self.i17:
            self._reseat()
        out = []
        for ci, c in enumerate(self.g_up["contours"]):
            base = U.contours[ci]["base"]
            out.append({"closed": c["closed"], "nodes": [[float(self.new[base + i][0]), float(self.new[base + i][1])] + list(n[2:]) for i, n in enumerate(c["nodes"])]})
        self.contours = out

    def spine_segments(self):
        U = self.U; segs = []
        for C_ in U.contours:
            for sg in C_["segs"]:
                if sg["kind"] != "curve":
                    continue
                ts = curvature_sign_changes(U.ctl(sg))
                if len(ts) != 1:
                    continue
                ra, rb = self.run_of.get(sg["gi"], []), self.run_of.get(sg["gj"], [])
                if not ra or not rb or {self.runs[r]["part"] for r in ra} & {self.runs[r]["part"] for r in rb}:
                    continue
                segs.append((sg, ts[0]))
        return segs

    def _ctl_new(self, sg):
        return np.array([self.new[i] for i in [sg["gi"]] + sg["offs"] + [sg["gj"]]])

    def _spine_rigid(self):
        U = self.U
        segs = self.spine_segments()
        if len(segs) < 2:
            return
        infl = [bez(U.ctl(sg), [t])[0] for sg, t in segs]
        m = np.mean(infl, axis=0)
        a = -self.psi * self.theta
        T = Map.about(m, self.S(m), rot(a))
        self.spine_centre = m; self.spine_map = T
        spine_nodes = set()
        for sg, ti in segs:
            for i in [sg["gi"]] + sg["offs"] + [sg["gj"]]:
                self.new[i] = T(U.xy[i]); spine_nodes.add(i)
            for nd in (sg["gi"], sg["gj"]):
                self.why[nd] = "spine junction node, rigid with the spine (I16)"
        spine_ids = {(sg["gi"], sg["gj"]) for sg, _ in segs}
        self.spine_junctions = {sg["gi"] for sg, _ in segs} | {sg["gj"] for sg, _ in segs}
        # the connecting curves: R14 similarity onto the new chord, then R15 at both ends
        for sg, ti in segs:
            for J in (sg["gi"], sg["gj"]):
                so = U.seg_before[J] if J == sg["gi"] else U.seg_after[J]
                if (so["gi"], so["gj"]) in spine_ids or so["kind"] != "curve":
                    continue
                F = so["gj"] if so["gi"] == J else so["gi"]
                Pb = np.array([self.base_new[i] for i in [so["gi"]] + so["offs"] + [so["gj"]]])
                # base chord (in the segment's own order) -> new chord
                a0, a1 = Pb[0], Pb[3]
                b0 = self.new[so["gi"]]; b1 = self.new[so["gj"]]
                ca, cb = a1 - a0, b1 - b0
                s = np.linalg.norm(cb) / max(np.linalg.norm(ca), 1e-9)
                ang = math.atan2(cb[1], cb[0]) - math.atan2(ca[1], ca[0])
                Sig = Map.about(a0, b0, s * rot(ang))
                h = [Sig(Pb[1]), Sig(Pb[2])]
                # handle at J (the one next to J in this segment), handle at F
                hJ_i = 0 if so["gi"] == J else 1; hF_i = 1 - hJ_i
                # R15 at J: the rigid spine's tangent wins
                sp_h = sg["offs"][0] if J == sg["gi"] else sg["offs"][1]
                d_sp = unit(self.new[sp_h] - self.new[J])
                LJ = np.linalg.norm(h[hJ_i] - self.new[J])
                hJ = self.new[J] - d_sp * LJ
                before_turn = math.degrees(math.atan2(*(unit(h[hJ_i] - self.new[J]))[::-1]) - math.atan2(*(-d_sp)[::-1]))
                # R15 at F: the base tangent is kept
                PF = Pb[3] if hF_i == 1 else Pb[0]; HF = Pb[2] if hF_i == 1 else Pb[1]
                d_F = unit(HF - PF); LF = np.linalg.norm(h[hF_i] - self.new[F])
                hF = self.new[F] + d_F * LF
                offs = so["offs"]
                self.new[offs[hJ_i]] = hJ; self.new[offs[hF_i]] = hF
                self.spine_report.append(dict(junction=J, far=F, seg=(so["gi"], so["gj"]), similarity_scale=round(float(s), 4),
                                              similarity_turn_deg=round(math.degrees(ang), 2),
                                              r15_turn_at_junction_deg=round(((before_turn + 180) % 360) - 180, 2),
                                              junction_move=[round(float(v), 2) for v in self.new[J] - self.base_new[J]]))
        for sg, ti in segs:
            P = U.ctl(sg); Pn = self._ctl_new(sg)
            def angle_at(Pc, t0):
                t2 = curvature_sign_changes(Pc); t2 = t2[0] if t2 else t0
                v1 = bez_d1(Pc, [t2])[0]; return math.degrees(math.atan2(v1[1], v1[0])) % 180.0
            Psl = np.array([self.S(p) for p in P])
            self.spine_fit.append(dict(seg=(sg["gi"], sg["gj"]), angle_roman=round(angle_at(P, ti), 2), angle_slant=round(angle_at(Psl, ti), 2),
                                       angle_got=round(angle_at(Pn, ti), 2), handles_kept=True,
                                       end_tangent_from_vertical_deg=[round(math.degrees(math.atan2(*(unit(Pn[1] - Pn[0]))[:: 1])), 2),
                                                                      round(math.degrees(math.atan2(*(unit(Pn[2] - Pn[3]))[:: 1])), 2)]))

    # -- I17 ---------------------------------------------------------------------------------------------------------
    def side_extremes(self):
        U = self.U; out = []
        for nd in sorted(self.round):
            sb, sa = U.seg_before[nd], U.seg_after[nd]
            if sb["kind"] != "curve" or sa["kind"] != "curve":
                continue
            d = unit(bez_d1(U.ctl(sa), [0.0])[0])
            if abs(d[0]) <= math.sin(math.radians(3.0)):
                out.append(nd)
        return out

    def _reseat(self):
        U = self.U
        rigid = getattr(self, "spine_junctions", set())
        for J in self.side_extremes():
            if J in rigid and self.i17 != "all":
                self.reseat_report.append(dict(node=J, moved=0.0, note="spine junction: carried by I16, not re-seated"))
                continue
            A, B = U.seg_before[J], U.seg_after[J]
            PA, PB = self._ctl_new(A), self._ctl_new(B)
            nA = len(PA); cand = []
            sA = np.r_[0, np.cumsum(np.linalg.norm(np.diff(bez(PA, np.linspace(0, 1, 201)), axis=0), axis=1))]
            sB = np.r_[0, np.cumsum(np.linalg.norm(np.diff(bez(PB, np.linspace(0, 1, 201)), axis=0), axis=1))]
            for t in vertical_ts(PA):
                cand.append(("A", t, sA[-1] - np.interp(t, np.linspace(0, 1, 201), sA)))
            for t in vertical_ts(PB):
                cand.append(("B", t, np.interp(t, np.linspace(0, 1, 201), sB)))
            if not cand:
                self.reseat_report.append(dict(node=J, moved=0.0, note="no vertical tangent on either curve")); continue
            side, t, arc = min(cand, key=lambda c: c[2])
            J0 = self.new[J].copy()
            if arc < 0.05:
                self.reseat_report.append(dict(node=J, moved=0.0, note="already at the vertical tangent")); continue
            if side == "B":
                B1, B2 = split(PB, t)
                pts = np.vstack([bez(PA, np.linspace(0, 1, 60)), bez(B1, np.linspace(0, 1, 30))[1:]])
                Jn = B2[0]
                dA0 = unit(PA[1] - PA[0]); dJ = unit(B2[0] - B2[1])          # into J from the A side
                PA2, dev = fit_fixed_tangents(PA[0], dA0, Jn, dJ, pts)
                PB2 = B2
            else:
                A1, A2 = split(PA, t)
                pts = np.vstack([bez(A2, np.linspace(0, 1, 30)), bez(PB, np.linspace(0, 1, 60))[1:]])
                Jn = A1[3]
                dJ = unit(A1[3] - A1[2]); dB3 = unit(PB[2] - PB[3])
                PB2, dev = fit_fixed_tangents(Jn, dJ, PB[3], dB3, pts)
                PA2 = A1
            self.new[A["offs"][0]] = PA2[1]; self.new[A["offs"][1]] = PA2[2]; self.new[J] = Jn
            self.new[B["offs"][0]] = PB2[1]; self.new[B["offs"][1]] = PB2[2]
            if side == "A":
                self.new[A["gi"]] = PA2[0]
            self.why[J] = self.why.get(J, "") + " + re-seated to the vertical tangent (I17)"
            self.reseat_report.append(dict(node=J, along=side, t=round(float(t), 4), moved=round(float(np.linalg.norm(Jn - J0)), 2),
                                           dxdy=[round(float(v), 2) for v in Jn - J0], arc=round(float(arc), 2), max_dev=round(dev, 2)))

    def report(self):
        R = Skeleton.report(self)
        R.update(terminal_rule=self.terminal_rule, i16=self.i16, i17=self.i17, terminals=self.term_report,
                 spine_connect=self.spine_report, reseat=self.reseat_report,
                 spine_centre=[round(float(v), 2) for v in getattr(self, "spine_centre", (np.nan, np.nan))])
        return R
