"""Round 5's skeleton field: the base outline the group rules (I2-I8, I13) then correct, in place of the plain slant.

    Skeleton(g_up, rules=("I10", "I11", "I12", "I14"), rho=, nu_coef=, psi=)   K comes from carry (set_slant)
        .contours    the base outline (same nodes, same order, same types, same smooth flags as the upright)
        .report()    classes, parts, maps, the spine fit

Every on-curve node gets ONE affine map (upright -> base) from its class; its off-curve handles take the same map, so a
smooth node stays smooth and a corner stays a corner (both handles share one linear part). The curve between two
nodes of different classes is the drawn cubic with each end carried by its own node's map: the join is blended by the
curve itself. The classes come from the parts the pairing already names (italicmove's held / junction / cut-face /
pinch classes, read on the plain slant with the upright's pairing carried, I1) plus the geometry of the upright:

  round node    a smooth node with a curve on both sides that is not held, junction, cut face or pinch
  round run     consecutive round nodes of a contour; a run also ends where the curvature changes sign (at a node, or
                inside a curve: each bowl of an s is its own run); a run is a COUNTER when its ink lies on its convex
                side (the concave side, toward the centre of curvature, is empty), else an OUTER
  round part    an outer run and the counter runs whose box centre lies inside its box (the smallest such outer);
                the part's centre c and width W are the OUTER run's box (the run walked out to its ends), w = a
                counter's own box width
  stem group    a run of non-round nodes holding a side of a stroke the pairing calls a stem, or a whole straight
                contour, or a BAR (a straight segment of 1.2 stems whose stroke runs into another contour's ink, or
                any of 2 stems), or, not between two round nodes, a straight segment of 1.2 stems; its nodes are
                sheared, its held nodes (serifs, flags, brackets) are serif nodes
  terminal      a run of non-round nodes between two round nodes, not buried in another contour's ink, with no stem
                segment: the free end of a round part (the s's beaks, the e's flick, the a's hood)
  buried end    a run of non-round nodes between round nodes whose straight segments lie inside another contour's ink
                (the p's bowl running into the stem): a junction
  other         a non-round node next to a round node is a junction (blended), every other node is sheared

The maps (upright coordinates, S = the plain slant x' = x + K y, theta = atan K):
 I10 two-angle shear: a round node of a part with centre c is carried by p' = S(c) + L (p - c),
     L = [[s, tan(rho theta)], [0, 1]]: the part keeps the shear's centre but leans rho theta; stems, straight parts
     and serifs keep theta. A junction node (a non-round node next to a round run, an inflection node between two
     runs, a buried end) takes the mean of its two sides' maps.
 I11 bowl narrowing: s = 1 - nu for the outer run, s = 1 - nu W / w for a counter: both sides of the stroke lose the
     same units, so stroke widths are kept. nu = nu_coef x tan theta (the number carried from 14.04 to 18.43 deg).
 I12 rigid spine: the spine of an s (the stretch of the two spine edges between the bowls, around their inflections)
     is turned as one piece by psi theta (clockwise for a rightward slant) about its centre m (the mean of the edge
     inflections), placed where the shear puts m: T(p) = S(m) + R(-psi theta) (p - m). The spine has no nodes (the s is
     anchor-free), so the rule acts on the spine edge's cubic: its end nodes keep their bowls' maps and handle
     directions, its two handle lengths are fitted (least squares) to the drawn edge carried by T in the spine core
     (where the edge runs within 35 deg of its inflection tangent) blended over 45 u into the bowls' maps. A z's
     diagonal (a straight stroke between two horizontal bars) is the same class: its two sides turn by psi theta about
     the stroke's centre, their end nodes slide along their bars (horizontal lines keep y).
 I14 cuts keep the roman angle: a serif group (held nodes of a stem group: foot and head serifs, flags, brackets) is
     carried RIGIDLY, by the shear's move at its joint (the mean height of its nodes that meet the stem): every serif
     edge keeps its drawn angle, the foot stays level and slides with the stem foot. A terminal is carried rigidly by
     its part's map at the terminal's centre with HALF its narrowing (I11) taken back: the cut keeps the roman angle,
     the position moves with the part and pulls in by half the local narrowing.
     Without I14 a serif group is sheared and a terminal takes its part's map.
Node count, order, types and smooth flags never change (asserted).
"""
import sys, os, math, json
import numpy as np
import skia
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
import carry as C

# fitted by SCORE from Mark's drawn o, p, s and two-storey a at 14.04 deg (scan_params.py, readings/scan_joint.json);
# the node-level model fits of his own roman -> italic are in fit_params.py (readings/fit_params.json). The drawing wins.
RHO = 0.70            # study default 0.6; node fits: o 0.80, p bowl 0.85, a bowl 0.15
NU_COEF = 0.0         # nu = NU_COEF x tan(theta). Study default 0.6 (15 % at 14.04 deg): Mark does NOT narrow (o 2.1 %, p -1.4 %)
PSI = 0.80            # study default 0.75; the drawn spine's own tangent turns 1.18 theta (fit_params.py)
SPINE_CORE_DEG = 20.0
SPINE_BLEND = 45.0
ALL_RULES = ("I10", "I11", "I12", "I14")


# ---- affine maps -------------------------------------------------------------------------------------------------
class Map:
    """p' = L p + t"""
    def __init__(self, L, t):
        self.L = np.array(L, float); self.t = np.array(t, float)

    def __call__(self, p):
        return self.L @ np.asarray(p, float)[:2] + self.t

    @staticmethod
    def about(c, c_new, L):
        L = np.array(L, float); c = np.asarray(c, float)
        return Map(L, np.asarray(c_new, float) - L @ c)

    @staticmethod
    def mean(maps, w=None):
        w = np.ones(len(maps)) if w is None else np.asarray(w, float); w = w / w.sum()
        return Map(sum(wi * m.L for wi, m in zip(w, maps)), sum(wi * m.t for wi, m in zip(w, maps)))


def shear_map(K):
    return Map([[1.0, K], [0.0, 1.0]], [0.0, 0.0])


def translate(d):
    return Map(np.eye(2), d)


# ---- cubic helpers -------------------------------------------------------------------------------------------------
def bez(P, t):
    t = np.asarray(t, float)[:, None]; u = 1 - t
    return u ** 3 * P[0] + 3 * u * u * t * P[1] + 3 * u * t * t * P[2] + t ** 3 * P[3]


def bez_d1(P, t):
    t = np.asarray(t, float)[:, None]; u = 1 - t
    return 3 * u * u * (P[1] - P[0]) + 6 * u * t * (P[2] - P[1]) + 3 * t * t * (P[3] - P[2])


def bez_d2(P, t):
    t = np.asarray(t, float)[:, None]; u = 1 - t
    return 6 * u * (P[2] - 2 * P[1] + P[0]) + 6 * t * (P[3] - 2 * P[2] + P[1])


def curvature_sign_changes(P):
    ts = np.linspace(0, 1, 401)
    d1, d2 = bez_d1(P, ts), bez_d2(P, ts)
    k = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
    out = []
    for i in np.nonzero(np.sign(k[:-1]) * np.sign(k[1:]) < 0)[0]:
        if 0.02 < ts[i] < 0.98:
            out.append(float(ts[i] + (ts[i + 1] - ts[i]) * abs(k[i]) / (abs(k[i]) + abs(k[i + 1]))))
    return out


class Glyph:
    """the upright's node / segment structure (flat numbering = the solver's)"""
    def __init__(self, g):
        self.g = g
        self.xy = []; self.typ = []; self.smooth = []
        self.contours = []
        base = 0
        for ci, c in enumerate(g["contours"]):
            ns = c["nodes"]; N = len(ns)
            for n in ns:
                self.xy.append(np.array(n[:2], float)); self.typ.append(n[2]); self.smooth.append(bool(n[3]) if len(n) > 3 else False)
            ons = [base + i for i in range(N) if ns[i][2] != "o"]
            segs = []
            for a, gi in enumerate(ons):
                gj = ons[(a + 1) % len(ons)]
                i, j = gi - base, gj - base
                offs = [base + (k % N) for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
                kind = "curve" if len(offs) == 2 else "line"
                segs.append(dict(gi=gi, gj=gj, offs=offs, kind=kind, ci=ci))
            self.contours.append(dict(base=base, N=N, ons=ons, segs=segs))
            base += N
        self.seg_after = {sg["gi"]: sg for C_ in self.contours for sg in C_["segs"]}
        self.seg_before = {sg["gj"]: sg for C_ in self.contours for sg in C_["segs"]}
        self.contour_of = {nd: ci for ci, C_ in enumerate(self.contours) for nd in C_["ons"]}
        self.owner = {}
        for C_ in self.contours:
            for sg in C_["segs"]:
                if sg["kind"] == "curve":
                    self.owner[sg["offs"][0]] = sg["gi"]; self.owner[sg["offs"][1]] = sg["gj"]

    def ctl(self, sg):
        return np.array([self.xy[i] for i in [sg["gi"]] + sg["offs"] + [sg["gj"]]]) if sg["kind"] == "curve" else \
            np.array([self.xy[sg["gi"]], self.xy[sg["gj"]]])

    def samples(self, sg, n=24, t0=0.0, t1=1.0):
        ts = np.linspace(t0, t1, n)
        P = self.ctl(sg)
        if sg["kind"] == "curve":
            return bez(P, ts)
        return P[0][None, :] + (P[1] - P[0])[None, :] * ts[:, None]

    def path(self, skip=None):
        p = skia.Path(); p.setFillType(skia.PathFillType.kWinding)
        for ci, C_ in enumerate(self.contours):
            if skip is not None and ci == skip:
                continue
            p.moveTo(*self.xy[C_["ons"][0]])
            for sg in C_["segs"]:
                P = self.ctl(sg)
                if sg["kind"] == "curve":
                    p.cubicTo(*P[1], *P[2], *P[3])
                else:
                    p.lineTo(*P[1])
            p.close()
        return p


# ---- the skeleton --------------------------------------------------------------------------------------------------
class Skeleton:
    I12_DIAGONAL = False      # the z's diagonal as a spine: built, judged worse (NOTES), kept behind this flag

    def __init__(self, g_up, rules=ALL_RULES, rho=RHO, nu_coef=NU_COEF, psi=PSI, IM0=None, K=None):
        from italicmove import ItalicMover
        self.K = C.K if K is None else K
        self.theta = math.atan(self.K)
        self.rules = set(rules); self.rho, self.nu_coef, self.psi = rho, nu_coef, psi
        self.nu = nu_coef * self.K
        self.kr = math.tan(rho * self.theta)
        self.g_up = g_up
        self.U = Glyph(g_up)
        slant = {"contours": [{"closed": c["closed"], "nodes": [[n[0] + self.K * n[1], n[1]] + list(n[2:]) for n in c["nodes"]]} for c in g_up["contours"]],
                 "width": g_up["width"], "master": "Slant", "glyph": g_up["glyph"]}
        self.slant = slant
        if IM0 is None:
            IM0 = ItalicMover(slant, g_up)
        self.IM0 = IM0
        self.S = shear_map(self.K)
        self.stem = C.stem_of(g_up["glyph"])
        self._classify()
        self._runs()
        self._parts()
        self._maps()
        self._apply()

    # -- classes ---------------------------------------------------------------------------------------------------
    def _classify(self):
        U, IM = self.U, self.IM0
        self.held = set(IM.held); self.junction = set(IM.junction); self.cut = set(IM.cut_face); self.pinch = set(IM.pinch)
        self.round = set()
        for C_ in U.contours:
            for nd in C_["ons"]:
                sb, sa = U.seg_before[nd], U.seg_after[nd]
                if sb["kind"] != "curve" or sa["kind"] != "curve":
                    continue
                if nd in self.held or nd in self.junction or nd in self.cut or nd in self.pinch:
                    continue
                if U.smooth[nd] or IM.smooth.get(nd):
                    self.round.add(nd)
        # the upright's ink, for the counter and buried tests
        self.ink = U.path()
        self.ink_other = {ci: U.path(skip=ci) for ci in range(len(U.contours))}

    def _end_curv(self, sg, at_end):
        if sg["kind"] != "curve":
            return 0.0
        P = self.U.ctl(sg)
        d1 = bez_d1(P, [1.0 if at_end else 0.0])[0]; d2 = bez_d2(P, [1.0 if at_end else 0.0])[0]
        L = np.linalg.norm(d1)
        return 0.0 if L < 1e-9 else float((d1[0] * d2[1] - d1[1] * d2[0]) / L ** 3)

    def _inflection_node(self, nd):
        kb, ka = self._end_curv(self.U.seg_before[nd], True), self._end_curv(self.U.seg_after[nd], False)
        return kb * ka < 0 and min(abs(kb), abs(ka)) > 1e-5

    def _runs(self):
        """round runs per contour (lists of nodes in contour order), split at inflections"""
        U = self.U
        self.runs = []                       # dict(nodes, ci, closed)
        self.run_of = {}
        self.split_infl = set()              # inflection nodes: shared by the two runs either side
        for ci, C_ in enumerate(U.contours):
            ons = C_["ons"]; K_ = len(ons)
            isr = [nd in self.round for nd in ons]
            if not any(isr):
                continue
            # break points: a non-round node, an inflection node (it ends both runs), an inflection inside a curve
            # between two round nodes (the run breaks between them)
            infl_node = {nd for nd in ons if nd in self.round and self._inflection_node(nd)}
            self.split_infl |= infl_node
            def breaks_after(p):
                nd, nx = ons[p], ons[(p + 1) % K_]
                sg = U.seg_after[nd]
                if nd not in self.round or nx not in self.round or nd in infl_node:
                    return True
                return sg["kind"] == "curve" and bool(curvature_sign_changes(U.ctl(sg)))
            if all(isr) and not any(breaks_after(p) for p in range(K_)):
                self.runs.append(dict(nodes=list(ons), ci=ci, closed=True)); continue
            start = next(p for p in range(K_) if breaks_after(p))
            cur = []
            for k in range(1, K_ + 1):
                p = (start + k) % K_
                nd = ons[p]
                if nd in self.round:
                    cur.append(nd)
                if breaks_after(p):
                    if cur:
                        self.runs.append(dict(nodes=cur, ci=ci, closed=False))
                    cur = [nd] if (nd in infl_node and nd in self.round) else []
            if cur:
                self.runs.append(dict(nodes=cur, ci=ci, closed=False))
        # inflection nodes appear at the end of one run and the start of the next: run_of keeps a list
        for ri, r in enumerate(self.runs):
            for nd in r["nodes"]:
                self.run_of.setdefault(nd, []).append(ri)
        for r in self.runs:
            r["pts"] = self._run_extent(r)
            A = r["pts"]
            r["box"] = (A[:, 0].min(), A[:, 1].min(), A[:, 0].max(), A[:, 1].max())
            r["counter"] = self._is_counter(r)

    def _run_extent(self, r):
        """samples of the run walked out along the contour to its ends: the nearest non-round node, or the curvature
        sign change inside a curve"""
        U = self.U
        if r["closed"]:
            return np.vstack([U.samples(sg) for sg in U.contours[r["ci"]]["segs"]])
        nodes = r["nodes"]; pts = []
        # inner segments
        for a, b in zip(nodes, nodes[1:]):
            pts.append(U.samples(U.seg_after[a]))
        for end, fwd in ((nodes[-1], True), (nodes[0], False)):
            sg = U.seg_after[end] if fwd else U.seg_before[end]
            ts = curvature_sign_changes(U.ctl(sg)) if sg["kind"] == "curve" else []
            if fwd:
                t1 = ts[0] if ts else 1.0
                pts.append(U.samples(sg, t0=0.0, t1=t1))
            else:
                t0 = ts[-1] if ts else 0.0
                pts.append(U.samples(sg, t0=t0, t1=1.0))
        pts.append(np.array([U.xy[nd] for nd in nodes]))
        return np.vstack(pts)

    def _is_counter(self, r):
        """a counter: probing 6 u toward the centre of curvature of its nodes finds no ink (I9's test, on the upright)"""
        U = self.U; votes = 0; n = 0
        for nd in r["nodes"]:
            sa = U.seg_after[nd]
            P = U.ctl(sa); d1 = bez_d1(P, [0.0])[0]; d2 = bez_d2(P, [0.0])[0]
            k = d1[0] * d2[1] - d1[1] * d2[0]
            if abs(k) < 1e-9:
                continue
            t = d1 / np.linalg.norm(d1)
            nc = np.array([-t[1], t[0]]) if k > 0 else np.array([t[1], -t[0]])
            q = U.xy[nd] + 6.0 * nc
            votes += 0 if self.ink.contains(float(q[0]), float(q[1])) else 1; n += 1
        return n > 0 and votes * 2 > n

    def _parts(self):
        outers = [i for i, r in enumerate(self.runs) if not r["counter"]]
        for i, r in enumerate(self.runs):
            r["part"] = i
        for i, r in enumerate(self.runs):
            if not r["counter"]:
                continue
            b = r["box"]; cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            hosts = [j for j in outers if self.runs[j]["box"][0] <= cx <= self.runs[j]["box"][2] and self.runs[j]["box"][1] <= cy <= self.runs[j]["box"][3]]
            if hosts:
                j = min(hosts, key=lambda j: (self.runs[j]["box"][2] - self.runs[j]["box"][0]) * (self.runs[j]["box"][3] - self.runs[j]["box"][1]))
                r["part"] = j
        for i, r in enumerate(self.runs):
            o = self.runs[r["part"]]; b = o["box"]
            r["c"] = np.array([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]); r["W"] = b[2] - b[0]
            r["w"] = r["box"][2] - r["box"][0]
            if r["part"] == i:
                r["s"] = 1.0 - (self.nu if "I11" in self.rules else 0.0)
            else:
                r["s"] = 1.0 - ((self.nu * r["W"] / max(r["w"], 1.0)) if "I11" in self.rules else 0.0)
                r["s"] = max(r["s"], 0.5)

    def run_map(self, ri, narrow=1.0):
        r = self.runs[ri]
        if "I10" not in self.rules and "I11" not in self.rules:
            return self.S
        kr = self.kr if "I10" in self.rules else self.K
        s = 1.0 - (1.0 - r["s"]) * narrow
        return Map.about(r["c"], self.S(r["c"]), [[s, kr], [0.0, 1.0]])

    # -- the maps per node ---------------------------------------------------------------------------------------------
    def _groups(self):
        """maximal runs of non-round on-curve nodes per contour, each with its kind"""
        U = self.U
        out = []
        for ci, C_ in enumerate(U.contours):
            ons = C_["ons"]; K_ = len(ons)
            isr = [nd in self.round for nd in ons]
            if all(isr):
                continue
            if not any(isr):
                out.append(dict(nodes=list(ons), ci=ci, prev=None, next=None, closed=True)); continue
            start = next(p for p in range(K_) if isr[p])
            cur = []
            for k in range(1, K_ + 1):
                p = (start + k) % K_
                if not isr[p]:
                    cur.append(ons[p])
                elif cur:
                    out.append(dict(nodes=cur, ci=ci, prev=ons[(ons.index(cur[0]) - 1) % K_], next=ons[p], closed=False)); cur = []
        for G_ in out:
            segs = [U.seg_after[nd] for nd in G_["nodes"][:-1]] if not G_["closed"] else [U.seg_after[nd] for nd in G_["nodes"]]
            lines = [sg for sg in segs if sg["kind"] == "line"]
            long_ = [sg for sg in lines if np.linalg.norm(U.xy[sg["gj"]] - U.xy[sg["gi"]]) >= 1.2 * self.stem]
            # a stem group holds a side of a stroke the pairing calls a stem, or is a whole straight contour; a long straight
            # segment counts too, except between two round nodes (an s's beak has a long cut, and it is a terminal)
            in_stem = any(self.IM0.M.stroke_kind[p_["st"]][0] for nd in G_["nodes"] for p_ in self.IM0.props.get(nd, []))
            between_rounds = (not G_["closed"]) and G_["prev"] in self.round and G_["next"] in self.round
            buried_l = [sg for sg in lines if self.ink_other[G_["ci"]].contains(*map(float, (U.xy[sg["gi"]] + U.xy[sg["gj"]]) / 2))]
            # a bar: a straight stroke running into another part (its end face is buried there: the a's and e's bars)
            bar = bool(long_) and bool(buried_l) or any(np.linalg.norm(U.xy[sg["gj"]] - U.xy[sg["gi"]]) >= 2.0 * self.stem for sg in lines)
            G_["stem"] = bool(in_stem or G_["closed"] or bar or (long_ and not between_rounds))
            buried = bool(lines) and len(buried_l) == len(lines)
            if not lines:
                buried = all(self.ink_other[G_["ci"]].contains(*map(float, U.xy[nd])) for nd in G_["nodes"])
            G_["buried"] = buried and not G_["stem"]
            G_["terminal"] = (not G_["closed"]) and not G_["stem"] and not G_["buried"]
        return out

    def _maps(self):
        U = self.U
        self.map = {}; self.why = {}; self.terminal_nodes = set()
        S = self.S
        # round nodes: their run's map (an inflection node shared by two runs: the mean)
        for nd in self.round:
            rs = self.run_of.get(nd, [])
            if not rs:
                self.map[nd] = S; self.why[nd] = "round, no run"; continue
            self.map[nd] = Map.mean([self.run_map(ri) for ri in rs]); self.why[nd] = "round run %s" % rs
        self.groups = self._groups()
        self.spine_lines = []
        for G_ in self.groups:
            nb_runs = []
            for e in (G_["prev"], G_["next"]):
                if e is not None and self.run_of.get(e):
                    nb_runs += self.run_of[e]
            # the run each end of the group touches (the nearest round node along the contour)
            if G_["stem"] or G_["closed"]:
                # held nodes of a stem group: serif groups, carried rigidly by the shear's move at their joint (I14)
                for nd in G_["nodes"]:
                    self.map[nd] = S; self.why[nd] = "stem group"
                if "I14" in self.rules:
                    self._serif_groups(G_)
                # a non-round node of a stem group next to a round node: a junction, blended across the join
                for e, nd in ((G_["prev"], G_["nodes"][0]), (G_["next"], G_["nodes"][-1])):
                    if e is not None and self.run_of.get(e) and nd not in self.held:
                        self.map[nd] = Map.mean([S, Map.mean([self.run_map(ri) for ri in self.run_of[e]])]); self.why[nd] = "junction (stem | round)"
            elif G_["buried"]:
                m = Map.mean([S] + [self.run_map(ri) for ri in nb_runs]) if nb_runs else S
                for nd in G_["nodes"]:
                    self.map[nd] = m; self.why[nd] = "buried end (junction)"
            else:
                # a terminal: its part's map (the mean of the runs it joins), at the terminal's centre
                pm = Map.mean([self.run_map(ri) for ri in nb_runs]) if nb_runs else S
                if "I14" in self.rules and nb_runs:
                    cen = np.mean([U.xy[nd] for nd in G_["nodes"]], axis=0)
                    half = Map.mean([self.run_map(ri, narrow=0.5) for ri in nb_runs])
                    d = half(cen) - cen
                    m = translate(d); how = "terminal, rigid (I14): roman angle, part's move with half its narrowing"
                else:
                    m = pm; how = "terminal: its part's map"
                for nd in G_["nodes"]:
                    self.map[nd] = m; self.why[nd] = how
                    if "I14" in self.rules and nb_runs:
                        self.terminal_nodes.add(nd)
        # z-like diagonals (I12): OFF -- at 18.43 deg the shear already turns a '/' diagonal 11.7 deg clockwise, the rigid
        # turn by psi theta takes it 3 deg further and runs its ends past the sheared bars (sheets/dev/z_I12_diagonal_18.png)
        if "I12" in self.rules and self.I12_DIAGONAL:
            self._diagonal_spines()
        for C_ in U.contours:
            for nd in C_["ons"]:
                if nd not in self.map:
                    self.map[nd] = S; self.why[nd] = "default shear"

    def _serif_groups(self, G_):
        """I14: connected held nodes inside a stem group move as one rigid piece by the shear's move at the height
        where they meet the stem (the mean height of the group's nodes whose neighbour is not held)"""
        U = self.U
        nodes = G_["nodes"]
        ons = U.contours[G_["ci"]]["ons"]; K_ = len(ons)
        held = [nd for nd in nodes if nd in self.held]
        if not held:
            return
        # connected runs along the contour
        pos = {nd: ons.index(nd) for nd in held}
        runs = []
        for nd in sorted(held, key=lambda n: pos[n]):
            if runs and (pos[nd] - pos[runs[-1][-1]]) % K_ == 1:
                runs[-1].append(nd)
            else:
                runs.append([nd])
        if len(runs) > 1 and (pos[runs[0][0]] - pos[runs[-1][-1]]) % K_ == 1:
            runs[0] = runs.pop() + runs[0]
        for r in runs:
            ends = [nd for nd in r if ons[(pos[nd] - 1) % K_] not in self.held or ons[(pos[nd] + 1) % K_] not in self.held]
            yref = float(np.mean([U.xy[nd][1] for nd in ends])) if ends else float(np.mean([U.xy[nd][1] for nd in r]))
            m = translate([self.K * yref, 0.0])
            for nd in r:
                self.map[nd] = m; self.why[nd] = "serif, rigid at y %.0f (I14)" % yref

    def _diagonal_spines(self):
        """I12 for a z: a straight stroke between two horizontal bars turns as one piece by psi theta about its centre;
        its end nodes slide along their bars (horizontal lines keep y), and a short corner piece (< 0.5 stem) between
        an end and its bar travels with the end"""
        U = self.U
        SHORT = 0.5 * self.stem
        def L_(sg):
            return float(np.linalg.norm(U.xy[sg["gj"]] - U.xy[sg["gi"]]))
        def horiz(sg2):
            e = U.xy[sg2["gj"]] - U.xy[sg2["gi"]]
            return sg2["kind"] == "line" and abs(e[1]) <= 0.14 * abs(e[0]) and abs(e[0]) > 10
        def walk(nd, fwd):
            """from a diagonal's end along the contour away from it: (the first segment of SHORT or more, the corner
            nodes passed on the way)"""
            passed = []
            for _ in range(4):
                sg = U.seg_after[nd] if fwd else U.seg_before[nd]
                if L_(sg) >= SHORT:
                    return sg, passed
                nd = sg["gj"] if fwd else sg["gi"]; passed.append(nd)
            return None, passed
        cand = []
        for C_ in U.contours:
            for sg in C_["segs"]:
                if sg["kind"] != "line":
                    continue
                d = U.xy[sg["gj"]] - U.xy[sg["gi"]]; L = np.linalg.norm(d)
                ang = abs(math.degrees(math.atan2(d[1], d[0]))) % 180.0
                ang = min(ang, 180 - ang)
                if L < 2.0 * self.stem or not (20.0 <= ang <= 70.0):
                    continue
                a_sg, a_pass = walk(sg["gi"], False); b_sg, b_pass = walk(sg["gj"], True)
                if a_sg is not None and b_sg is not None and horiz(a_sg) and horiz(b_sg):
                    cand.append((sg, a_pass, b_pass))
        if not cand:
            return
        m = np.mean([(U.xy[sg["gi"]] + U.xy[sg["gj"]]) / 2 for sg, _, _ in cand], axis=0)
        a = -self.psi * self.theta
        R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
        T = Map.about(m, self.S(m), R)
        for sg, a_pass, b_pass in cand:
            p, q = T(U.xy[sg["gi"]]), T(U.xy[sg["gj"]])
            d = q - p
            for nd, passed in ((sg["gi"], a_pass), (sg["gj"], b_pass)):
                y = U.xy[nd][1]
                x = p[0] + d[0] * (y - p[1]) / d[1] if abs(d[1]) > 1e-9 else T(U.xy[nd])[0]
                mv = translate(np.array([x, y]) - U.xy[nd])
                self.map[nd] = mv; self.why[nd] = "diagonal spine end, slides on its bar (I12)"
                for c in passed:
                    self.map[c] = mv; self.why[c] = "corner piece of a diagonal spine end (I12)"
            self.spine_lines.append((sg["gi"], sg["gj"]))
        self.spine_centre = m

    # -- apply -------------------------------------------------------------------------------------------------------
    def _apply(self):
        U = self.U
        new = [None] * len(U.xy)
        for i in range(len(U.xy)):
            nd = i if U.typ[i] != "o" else U.owner[i]
            new[i] = self.map[nd](U.xy[i])
        self.new = new
        self.spine_fit = []
        if "I12" in self.rules:
            self._spine_s()
        out = []
        for ci, c in enumerate(self.g_up["contours"]):
            base = U.contours[ci]["base"]
            out.append({"closed": c["closed"], "nodes": [[float(self.new[base + i][0]), float(self.new[base + i][1])] + list(n[2:]) for i, n in enumerate(c["nodes"])]})
        self.contours = out

    def _spine_s(self):
        """I12 for an s: the spine edges are the cubics holding a curvature sign change between two round runs of
        different parts; their handle lengths are fitted to the drawn edge carried by the spine's rigid turn"""
        U = self.U
        segs = []
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
        if len(segs) < 2:
            return
        infl = [bez(U.ctl(sg), [t])[0] for sg, t in segs]
        m = np.mean(infl, axis=0)
        a = -self.psi * self.theta
        R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
        T = Map.about(m, self.S(m), R)
        self.spine_centre = m
        for (sg, ti), pi in zip(segs, infl):
            P = U.ctl(sg)
            ts = np.linspace(0, 1, 61)
            pts = bez(P, ts); d1 = bez_d1(P, ts)
            ang = np.degrees(np.arctan2(d1[:, 1], d1[:, 0]))
            a0 = math.degrees(math.atan2(*bez_d1(P, [ti])[0][::-1]))
            dev = np.abs((ang - a0 + 90) % 180 - 90)
            # arc length from the inflection, the core where the edge runs within SPINE_CORE_DEG of its inflection
            seglen = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
            s_i = np.interp(ti, ts, seglen)
            core = dev <= SPINE_CORE_DEG
            # the core's extent along the curve, as a contiguous interval round the inflection
            idx = np.arange(len(ts)); i0 = int(round(ti * 60))
            lo = i0
            while lo > 0 and core[lo - 1]: lo -= 1
            hi = i0
            while hi < 60 and core[hi + 1]: hi += 1
            s_lo, s_hi = seglen[lo], seglen[hi]
            def v_of(s):
                if s_lo <= s <= s_hi:
                    return 1.0
                d = (s_lo - s) if s < s_lo else (s - s_hi)
                x = max(0.0, 1.0 - d / SPINE_BLEND)
                return x * x * (3 - 2 * x)
            v = np.array([v_of(s) for s in seglen])
            # the per-node carried cubic (ends and handle directions fixed), and the target
            Q0, Q3 = self.new[sg["gi"]], self.new[sg["gj"]]
            Q1, Q2 = self.new[sg["offs"][0]], self.new[sg["offs"][1]]
            base_pts = bez(np.array([Q0, Q1, Q2, Q3]), ts)
            tgt = (1 - v)[:, None] * base_pts + v[:, None] * np.array([T(p) for p in pts])
            d0 = (Q1 - Q0) / np.linalg.norm(Q1 - Q0); d3 = (Q2 - Q3) / np.linalg.norm(Q2 - Q3)
            L1, L2 = np.linalg.norm(Q1 - Q0), np.linalg.norm(Q2 - Q3)
            u = 1 - ts
            wa = 3 * u * u * ts; wb = 3 * u * ts * ts
            B = (u ** 3 + wa)[:, None] * Q0 + (wb + ts ** 3)[:, None] * Q3
            Aa = wa[:, None] * d0; Ab = wb[:, None] * d3
            r = tgt - B
            M = np.array([[np.sum(Aa * Aa), np.sum(Aa * Ab)], [np.sum(Aa * Ab), np.sum(Ab * Ab)]])
            rhs = np.array([np.sum(Aa * r), np.sum(Ab * r)])
            la, lb = np.linalg.solve(M, rhs)
            la = min(max(la, 0.4 * L1), 2.0 * L1); lb = min(max(lb, 0.4 * L2), 2.0 * L2)
            self.new[sg["offs"][0]] = Q0 + d0 * la; self.new[sg["offs"][1]] = Q3 + d3 * lb
            got = bez(np.array([Q0, Q0 + d0 * la, Q3 + d3 * lb, Q3]), ts)
            # the spine angle achieved at the inflection, vs the slant's and the rigid turn's
            def angle_at(Pc):
                t2 = curvature_sign_changes(Pc); t2 = t2[0] if t2 else ti
                v1 = bez_d1(Pc, [t2])[0]; return math.degrees(math.atan2(v1[1], v1[0])) % 180.0
            Psl = np.array([self.S(p) for p in P])
            self.spine_fit.append(dict(seg=(sg["gi"], sg["gj"]), handles=(round(la / L1, 3), round(lb / L2, 3)),
                                       rms_to_target=round(float(np.sqrt(np.mean(np.sum((got - tgt) ** 2, axis=1)))), 2),
                                       angle_roman=round(angle_at(P), 2), angle_slant=round(angle_at(Psl), 2),
                                       angle_target=round((angle_at(P) - math.degrees(self.psi * self.theta)) % 180, 2),
                                       angle_got=round(angle_at(np.array([Q0, Q0 + d0 * la, Q3 + d3 * lb, Q3])), 2),
                                       core_u=round(float(s_hi - s_lo), 1)))

    def report(self):
        return dict(rules=sorted(self.rules), K=self.K, rho=self.rho, nu=self.nu, nu_coef=self.nu_coef, psi=self.psi,
                    runs=[dict(nodes=r["nodes"], counter=r["counter"], part=r["part"], c=[round(float(v), 1) for v in r["c"]],
                               W=round(float(r["W"]), 1), w=round(float(r["w"]), 1), s=round(float(r["s"]), 4)) for r in self.runs],
                    groups=[dict(nodes=G_["nodes"], stem=G_["stem"], buried=G_["buried"], terminal=G_["terminal"]) for G_ in self.groups],
                    why={int(k): v for k, v in self.why.items()}, spine=self.spine_fit, spine_lines=self.spine_lines)


def check_same(a, b):
    fa = [n for c in a for n in c["nodes"]]; fb = [n for c in b for n in c["nodes"]]
    return len(a) == len(b) and len(fa) == len(fb) and all(x[2:] == y[2:] for x, y in zip(fa, fb))


if __name__ == "__main__":
    K = C.set_slant(C.parse_slant(sys.argv))
    args = C.strip_slant(sys.argv[1:])
    G = C.load()
    for gl in (args[0].split(",") if args else C.glyphs(G)):
        Sk = Skeleton(G["GeistSerifRegular_" + gl])
        assert check_same(Sk.contours, G["GeistSerifRegular_" + gl]["contours"])
        R = Sk.report()
        print("==", gl, "K %.4f rho %.2f nu %.4f psi %.2f" % (K, Sk.rho, Sk.nu, Sk.psi))
        for r in R["runs"]:
            print("  run", r)
        for g_ in R["groups"]:
            print("  group", g_)
        for s_ in R["spine"]:
            print("  spine", s_)
