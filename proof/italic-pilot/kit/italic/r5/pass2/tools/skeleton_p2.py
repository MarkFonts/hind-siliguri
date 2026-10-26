"""Round 5 · pass 2: the skeleton base for the FULL set, with the s round's I15-I17 carried back (skeleton5s.py, the s
round's code, copied unchanged) plus what the full set needs that the s did not have: serifs, stem-group stroke ends,
and a waist that is not a terminal.

    SkeletonP2(g_up, serif="arm", i17=True, psi=1.23, stem_ends=True, IM0=..., K=None)
        .contours, .report()      as Skeleton5s, plus .serif_report, .stem_end_report, .waists

What is added (also in italicmove.py's docstring, "ROUND 5 · PASS 2"):

 I14 for serifs, by the stroke a serif ends (`serif=`):
       "roman"  pass 1: every serif group (the held nodes of a stem group) is carried RIGIDLY by the shear's move at
                its joint, so every serif cut keeps the roman angle
       "arm"    (shipped) a serif that hangs from a HORIZONTAL stroke -- an arm or bar end, the held piece standing
                TALLER than it is wide (T's two arm ends, E's three arm ends) -- keeps the SHEAR, i.e. it is sheared
                with its arm; a serif that sits on a stem (foot, head, flag: wider than tall) keeps the roman angle
       "shear"  every serif keeps the shear (= the plain slant's serifs)
     A serif is NOT a terminal: entry / exit does not apply to it. Its class is the direction of the stroke it ends.

 I15 terminals ride -- two extensions of the s round's class:
   (a) a terminal ENDS ONE PART: the non-round run between two round nodes is a terminal only when the round runs on
       its two sides belong to the same part (its outer and its counter: the s's beaks, the e's flick, the a's hood,
       the quoteright's tail). Between two DIFFERENT parts it is a waist (B's 40-41): a junction, carried by the mean
       of the two parts' maps (pass 1 treated it as a rigid terminal).
   (b) a STROKE END inside a stem group (a curved stroke that runs out of a stem: f's hook, r's arm, j's and y's
       tails): a run of nodes joined by straight segments only, bounded on both sides by curves at least one of which
       is a stroke side (chord >= 1 stem; a serif's brackets are shorter), holding a free steep cut (a straight
       segment of 12 u to 1.5 stems, more than 45 deg from horizontal, empty ink just outside it). It rides its sides (they are
       sheared: its translation is the shear's move at its two end nodes) and takes the s round's cut class: the
       LEADING end (upper half of its contour) keeps the roman angle, the TRAILING end keeps the shear. Its nodes
       hold in the group rules (extra_held), like the s's terminals.
 I16 rigid spine piece: unchanged; it finds a spine only where two cubics carry the curvature sign change between
     the round runs of two different parts. In this set that is the s alone (reported per letter). The z's diagonal
     stays OFF (Skeleton.I12_DIAGONAL).
 I17 re-seat side extremes: the s round's code, now acting on the letters it was built for (o, p, a, e, B, j's dot,
     quoteright). Its target, tested against Mark's o, p and a: the TRUE vertical tangent (`i17_target="vertical"`, as
     the s round wrote it) slides the o's side nodes 58 / 85 u the wrong way (down on the left) and scores worse than no
     re-seat; the tangent PARALLEL TO THE ITALIC ANGLE (`"italic"`, shipped: the node slides to where the leaned bowl's
     tangent runs along the stems, its handles along theta) slides them 28 / 43 u up on the left, down on the right,
     where Mark's nodes are (his o: 25 u up left, 19 u down right), and scores better than both.
"""
import sys, os, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
import carry as C
from skeleton import Map, translate, curvature_sign_changes, RHO, NU_COEF
from skeleton5s import Skeleton5s, unit

SERIF_RULES = ("roman", "arm", "shear")


class SkeletonP2(Skeleton5s):
    BLUNT = 6.0              # u: a straight end this short is a blunt (START wall), it turns with its stroke
    REAIM_MAX = 3.0          # I16 arc fairing: the largest common turn of the two handles at the bowl node (deg); at 15 the counter arcs of Mark's s turned 12 deg and ran flat into the beak
    FAIR_W = 0.15            # I16 arc fairing: weight of the curvature-change term against the three G2 conditions
    CUT_MAX = 1.5            # a stroke end's cut is at most 1.5 stems long (a longer free steep line is a stroke side)

    def __init__(self, g_up, serif="arm", terminal="a", psi=1.23, i16=True, i17=True, stem_ends=True, i17_target="italic",
                 side_handles=False, pull_k=0.0, spine_g2=True, serif_joint=None, post=None, terminal_narrow=False, rho=RHO, nu_coef=NU_COEF, IM0=None, K=None):
        if serif_joint is not None:
            self.SERIF_JOINT = serif_joint
        self.post = post; self.terminal_narrow = terminal_narrow
        self.side_handles = side_handles; self.pull_k = pull_k; self.spine_g2 = spine_g2; self.g2_report = []
        self.handle_map = {}; self.pull_report = []
        assert serif in SERIF_RULES, serif
        assert i17_target in ("vertical", "italic"), i17_target
        self.I17_TARGET = i17_target
        self.serif_rule = serif; self.stem_ends = stem_ends
        self.serif_report = []; self.stem_end_report = []; self.waists = []
        Skeleton5s.__init__(self, g_up, terminal=terminal, psi=psi, i16=i16, i17=i17, rho=rho, nu_coef=nu_coef, IM0=IM0, K=K)

    # Skeleton5s passes rules=("I10", "I11"); pass 2 needs I14 for the serifs
    def _classify(self):
        self.rules = set(self.rules) | {"I14"}
        Skeleton5s._classify(self)

    # -- I15 (a): a terminal ends one part; between two parts it is a waist (junction) --------------------------------
    def _groups(self):
        out = Skeleton5s._groups(self)
        for G_ in out:
            if not G_.get("terminal"):
                continue
            pa = {self.runs[r]["part"] for r in self.run_of.get(G_["prev"], [])}
            pb = {self.runs[r]["part"] for r in self.run_of.get(G_["next"], [])}
            if pa and pb and not (pa & pb):
                G_["terminal"] = False; G_["buried"] = True; G_["waist"] = True
                self.waists.append(list(G_["nodes"]))
        return out

    # -- I14 serifs by the stroke they end ------------------------------------------------------------------------
    SERIF_JOINT = "junction"   # I14b (pass 2b): a stem serif hangs at its brackets' junction height; "slab" = pass 2a / pass 1

    def _serif_groups(self, G_):
        if not hasattr(self, "serif_brackets"):
            self.serif_brackets = []
        before = {nd: self.map.get(nd) for nd in G_["nodes"]}
        Skeleton5s._serif_groups(self, G_)          # pass 1: every held run rigid at its joint (roman angle)
        U = self.U
        held = [nd for nd in G_["nodes"] if nd in self.held]
        if not held:
            return
        ons = U.contours[G_["ci"]]["ons"]; K_ = len(ons)
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
            P = np.array([U.xy[nd] for nd in r])
            w = float(P[:, 0].max() - P[:, 0].min()); h = float(P[:, 1].max() - P[:, 1].min())
            arm = h > w
            brackets = []
            if self.serif_rule == "shear" or (self.serif_rule == "arm" and arm):
                for nd in r:
                    self.map[nd] = self.S; self.why[nd] = "serif on an %s, sheared with it (I14, pass 2)" % ("arm" if arm else "stem")
                kept = "shear"
            else:
                kept = "roman"
                if self.SERIF_JOINT == "junction":
                    # I14b: the serif = slab + its brackets, one rigid ROMAN piece hung at the height where its brackets
                    # meet the stem (the junction nodes), so each bracket keeps its roman chord
                    for nd in r:
                        for sg in (U.seg_before[nd], U.seg_after[nd]):
                            other = sg["gi"] if sg["gj"] == nd else sg["gj"]
                            if sg["kind"] == "curve" and other not in self.held and other not in r:
                                brackets.append(dict(end=nd, junction=other, seg=sg))
                    if brackets:
                        yref = float(np.mean([U.xy[b["junction"]][1] for b in brackets]))
                        m = translate([self.K * yref, 0.0])
                        for nd in r:
                            self.map[nd] = m; self.why[nd] = "stem serif + brackets, rigid roman at junction height %.0f (I14b)" % yref
                        self.serif_brackets += brackets
            self.serif_report.append(dict(nodes=r, width=round(w, 1), height=round(h, 1), hangs_from="arm" if arm else "stem", cut=kept,
                                          junctions=[b["junction"] for b in brackets]))

    # -- I15 (b): stroke ends in stem groups ----------------------------------------------------------------------
    def _free(self, sg):
        U = self.U
        a, b = U.xy[sg["gi"]], U.xy[sg["gj"]]
        e = b - a; L = float(np.linalg.norm(e))
        if L < 12.0 or L > self.CUT_MAX * self.stem:
            return False, L
        steep = abs(e[1]) > abs(e[0])
        m = (a + b) / 2; n = np.array([e[1], -e[0]]) / L
        out = [m + 4.0 * n, m - 4.0 * n]
        empty = [not self.ink.contains(float(q[0]), float(q[1])) for q in out]
        return steep and (empty[0] != empty[1]), L

    def stem_end_pieces(self):
        U = self.U; pieces = []
        for G_ in self.groups:
            if not G_["stem"]:
                continue
            ci = G_["ci"]; ons = U.contours[ci]["ons"]; K_ = len(ons)
            inG = set(G_["nodes"])
            # maximal runs of on-curve nodes of this group joined by LINES, bounded by curves on both sides
            seen = set()
            for p in range(K_):
                nd = ons[p]
                if nd in seen or nd not in inG or U.seg_before[nd]["kind"] != "curve":
                    continue
                run = [nd]; q = p
                while U.seg_after[ons[q % K_]]["kind"] == "line" and len(run) < 8:
                    q += 1; run.append(ons[q % K_])
                if U.seg_after[run[-1]]["kind"] != "curve" or not all(x in inG for x in run):
                    continue
                seen |= set(run)
                cb, ca = U.seg_before[run[0]], U.seg_after[run[-1]]
                chords = [float(np.linalg.norm(U.xy[s["gj"]] - U.xy[s["gi"]])) for s in (cb, ca)]
                if max(chords) < self.stem:
                    continue
                cuts = [(U.seg_after[x], self._free(U.seg_after[x])) for x in run[:-1]]
                cuts = [(s, L) for s, (ok, L) in cuts if ok]
                if not cuts:
                    continue
                pieces.append(dict(nodes=run, ci=ci, chords=[round(c, 1) for c in chords], cut=max(cuts, key=lambda c: c[1])[0]))
        return pieces

    def _maps(self):
        Skeleton5s._maps(self)
        self.pieces = []                          # every I15 piece: (nodes, side map coming in, side map going out)
        for G_ in self.groups:
            if G_.get("terminal") and self.run_of.get(G_["prev"]) and self.run_of.get(G_["next"]):
                Mp = Map.mean([self.run_map(ri) for ri in self.run_of[G_["prev"]]])
                Mn = Map.mean([self.run_map(ri) for ri in self.run_of[G_["next"]]])
                self.pieces.append((list(G_["nodes"]), Mp, Mn, G_["ci"]))
        if self.stem_ends:
            self._stem_end_maps()
        if self.terminal_narrow and self.nu:
            self._terminal_narrowing()
        self._side_handles_and_pull()

    def _terminal_narrowing(self):
        """(s option 11) a terminal takes its part's x-narrowing (I11) in its linear part: without it the narrowed bowl
        met a full-width beak and the connecting curves bulged (option 5's bumps); the translation is re-solved from the
        two sides' moves at the piece's end nodes"""
        U = self.U
        for nodes, Mp, Mn, ci in self.pieces:
            first, last = nodes[0], nodes[-1]
            parts = {self.runs[r]["part"] for r in self.run_of.get(U.seg_before[first]["gi"], []) + self.run_of.get(U.seg_after[last]["gj"], [])}
            if not parts:
                continue
            s = float(np.mean([self.runs[p]["s"] for p in parts]))
            m = self.map[first]
            L = np.diag([s, 1.0]) @ m.L
            tt = np.mean([Mp(U.xy[first]) - L @ U.xy[first], Mn(U.xy[last]) - L @ U.xy[last]], axis=0)
            for nd in nodes:
                self.map[nd] = Map(L, tt)

    def _side_handles_and_pull(self):
        """I15, pass 2 (Mark on the s round's 18.43 deg comb):
          side handles: the handle a side curve has AT a terminal's end node belongs to the SIDE (its lean, I10 / the
            shear), not to the terminal's cut class. With the terminal's own linear part (roman for a leading terminal)
            the outer bowl ran into the beak on its roman tangent: 18 deg off the leaned bowl, the comb flat across the
            top and bunched before the beak. The cut keeps its class; only the two side handles change.
          pull-in: the piece slides horizontally toward the letter's middle by pull_k x tan(theta) x |its centre's
            height above or below the contour's mid-height| (the conventions' 'terminals pull in toward the body')."""
        U = self.U
        self.blunts = []
        for nodes, Mp, Mn, ci in self.pieces:
            first, last = nodes[0], nodes[-1]
            if self.side_handles:
                # "corners" (pass 2c): only where the stroke meets the cut at a CORNER does its end tangent belong to the
                # stroke (it leans with its side); where the stroke runs smoothly into the piece the two are one piece and
                # the tangent stays the piece's (True: everywhere -- that broke G1 at the s's smooth beak ends, 2 snaps)
                sb, sa = U.seg_before[first], U.seg_after[last]
                def corner(nd):
                    """a corner, or a smooth end whose straight neighbour inside the piece is a blunt (a START wall,
                    < BLUNT u): the blunt then turns with the stroke's tangent (self.blunts)"""
                    if not (U.smooth[nd] or self.IM0.smooth.get(nd)):
                        return True
                    inner = U.seg_after[nd] if nd == first else U.seg_before[nd]
                    other = inner["gj"] if nd == first else inner["gi"]
                    if inner["kind"] == "line" and np.linalg.norm(U.xy[other] - U.xy[nd]) < self.BLUNT:
                        self.blunts.append((nd, other, Mp if nd == first else Mn))
                        return True
                    return False
                if sb["kind"] == "curve" and (self.side_handles is True or corner(first)):
                    self.handle_map[sb["offs"][1]] = ("side", first, Mp)
                if sa["kind"] == "curve" and (self.side_handles is True or corner(last)):
                    self.handle_map[sa["offs"][0]] = ("side", last, Mn)
            if self.pull_k:
                ons = U.contours[ci]["ons"]
                xs = [U.xy[n][0] for n in ons]; ys = [U.xy[n][1] for n in ons]
                cen = np.mean([U.xy[n] for n in nodes], axis=0)
                xm, ym = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
                dx = -math.copysign(1.0, cen[0] - xm) * self.pull_k * self.K * abs(cen[1] - ym)
                for nd in nodes:
                    m = self.map[nd]; self.map[nd] = Map(m.L, m.t + np.array([dx, 0.0]))
                self.pull_report.append(dict(nodes=nodes, dx=round(float(dx), 2)))

    def _apply(self):
        """Skeleton5s._apply with one change: a side handle at a terminal's end node (side_handles) is carried by the
        side's linear part about the end node's new position"""
        U = self.U
        new = [None] * len(U.xy)
        for i in range(len(U.xy)):
            nd = i if U.typ[i] != "o" else U.owner[i]
            new[i] = self.map[nd](U.xy[i])
        for i, (_, nd, Ms) in self.handle_map.items():
            new[i] = new[nd] + Ms.L @ (U.xy[i] - U.xy[nd])
        for nd, other, Ms in getattr(self, "blunts", []):
            v = Ms.L @ (U.xy[other] - U.xy[nd])            # the blunt turned with the stroke, its length kept
            new[other] = new[nd] + v / np.linalg.norm(v) * np.linalg.norm(U.xy[other] - U.xy[nd])
        # I14b: a bracket whose two ends moved apart (junctions at different heights) is the roman bracket scaled onto
        # its new chord (R14 similarity for the lengths); its end directions stay the piece's (roman) and the stem's (R15)
        self.bracket_report = []
        for b in getattr(self, "serif_brackets", []):
            if b["end"] in self.terminal_nodes:
                continue                      # the held run became an I15 stroke end (the j's tail): not a serif
            sg = b["seg"]; i0, i3 = sg["gi"], sg["gj"]; h0, h3 = sg["offs"]
            c_up = np.linalg.norm(U.xy[i3] - U.xy[i0]); c_new = np.linalg.norm(new[i3] - new[i0])
            s = c_new / max(c_up, 1e-9)
            for h, e in ((h0, i0), (h3, i3)):
                d = new[h] - new[e]; Ld = np.linalg.norm(d)
                if Ld > 1e-9:
                    new[h] = new[e] + d / Ld * np.linalg.norm(U.xy[h] - U.xy[e]) * s
            self.bracket_report.append(dict(seg=(i0, i3), chord_scale=round(float(s), 4)))
        self.new = new
        self.base_new = [p.copy() for p in new]
        self.spine_fit = []
        if self.i16:
            self._spine_rigid()
        if self.i17:
            self._reseat()
        if self.post is not None:
            self.post(self)                 # an exploration option's move on the finished skeleton (s_options2.py)
        out = []
        for ci, c in enumerate(self.g_up["contours"]):
            base = U.contours[ci]["base"]
            out.append({"closed": c["closed"], "nodes": [[float(self.new[base + i][0]), float(self.new[base + i][1])] + list(n[2:]) for i, n in enumerate(c["nodes"])]})
        self.contours = out

    # -- I16, pass 2: the bowl arc from the spine to the terminal is harmonized -------------------------------------
    def _spine_rigid(self):
        """the s round's I16, then (spine_g2) the bowl arc between a spine junction J and the next terminal is made one
        even arc again. The arc is two cubics: A, the connecting curve J -> F (R14 similarity), and B, the bowl's curve
        F -> E (E = the terminal's end node). Their four handle LENGTHS and (spine_g2="fair", shipped) one common turn of
        the two handles at F, at most REAIM_MAX = 3 deg, are re-solved, every other handle DIRECTION kept (so every smooth
        node stays smooth and the cut keeps its class), for
            curvature of A at J  = the spine's at J          (G2 with the rigid spine)
            curvature of A at F  = curvature of B at F = the mean of the two before   (G2 at F, Curvatura's rule)
            curvature of B at E  = as it was                (the terminal's end untouched)
        Why: at 18.43 deg the similarity left A flat next to F and B curled into the beak (the leading terminal holds
        the roman tangent at E while F leans rho theta): a curvature step at F. Mark: 'odd flattening / additional
        curling' on the s round's comb."""
        Skeleton5s._spine_rigid(self)
        if not self.spine_g2:
            return
        from scipy.optimize import least_squares
        U = self.U

        def kappa(P, end):
            P = np.asarray(P, float)
            if end == 0:
                d1, d2 = 3 * (P[1] - P[0]), 6 * (P[2] - 2 * P[1] + P[0])
            else:
                d1, d2 = 3 * (P[3] - P[2]), 6 * (P[3] - 2 * P[2] + P[1])
            return float((d1[0] * d2[1] - d1[1] * d2[0]) / max(np.linalg.norm(d1), 1e-9) ** 3)

        def oriented(sg, start):
            """control points of sg ordered from node `start`, and the offs indices in that order"""
            idx = [sg["gi"]] + sg["offs"] + [sg["gj"]]
            if sg["gi"] != start:
                idx = idx[::-1]
            return idx
        for rec in self.spine_report:
            J, F = rec["junction"], rec["far"]
            A = U.seg_before[J] if U.seg_before[J]["gi"] == F else U.seg_after[J]
            Sp = U.seg_after[J] if A is U.seg_before[J] else U.seg_before[J]
            B = U.seg_after[F] if A["gj"] == F else U.seg_before[F]
            if A["kind"] != "curve" or B["kind"] != "curve" or Sp["kind"] != "curve":
                continue
            ia = oriented(A, J); ib = oriented(B, F); isp = oriented(Sp, J)
            E = ib[3]
            PA = np.array([self.new[i] for i in ia]); PB = np.array([self.new[i] for i in ib])
            kJ = kappa(np.array([self.new[i] for i in isp]), 0)
            # orientation: A runs J -> F, B runs F -> E, the spine runs J -> away; curvature signs follow travel
            # direction, so the spine's at J is negated to read along A's direction into J... compare magnitudes
            # with the sign of A's own curvature at J
            kA0, kA3, kB0, kB3 = kappa(PA, 0), kappa(PA, 3), kappa(PB, 0), kappa(PB, 3)
            tJ = abs(kJ) * np.sign(kA0); tF = 0.5 * (kA3 + kB0); tE = kB3
            u = [unit(PA[1] - PA[0]), unit(PA[2] - PA[3]), unit(PB[1] - PB[0]), unit(PB[2] - PB[3])]
            L = [np.linalg.norm(PA[1] - PA[0]), np.linalg.norm(PA[2] - PA[3]), np.linalg.norm(PB[1] - PB[0]), np.linalg.norm(PB[2] - PB[3])]
            mode = self.spine_g2 if self.spine_g2 in ("fair", "g2", "roman") else "lengths"
            fair = mode in ("fair", "g2", "roman")          # these modes carry the re-aim at F as a 5th unknown
            # the roman's curvature ratios across J (connecting curve : spine) and F (connecting curve : bowl curve)
            def kup(sg, at):
                idx = oriented(sg, at); return kappa(np.array([U.xy[i] for i in idx]), 0)
            def kup_end(sg, start, at_end):
                idx = oriented(sg, start); Q = np.array([U.xy[i] for i in idx]); return kappa(Q, 3 if at_end else 0)
            rJ = kup(A, J) / kup(Sp, J) if abs(kup(Sp, J)) > 1e-9 else 1.0
            kAF_up = kup_end(A, J, True); kBF_up = kup(B, F)
            rF = kAF_up / kBF_up if abs(kBF_up) > 1e-9 else 1.0
            rJ = abs(rJ); rF = abs(rF)
            def build(x):
                uF_A, uF_B = u[1], u[2]
                if fair:                                    # re-aim: both handles at F turn together (F stays smooth)
                    R = np.array([[math.cos(x[4]), -math.sin(x[4])], [math.sin(x[4]), math.cos(x[4])]])
                    uF_A, uF_B = R @ u[1], R @ u[2]
                QA = np.array([PA[0], PA[0] + x[0] * u[0], PA[3] + x[1] * uF_A, PA[3]])
                QB = np.array([PB[0], PB[0] + x[2] * uF_B, PB[3] + x[3] * u[3], PB[3]])
                return QA, QB
            ts = np.linspace(0, 1, 41)
            def kcurve(Q):
                d1 = 3 * ((1 - ts) ** 2)[:, None] * (Q[1] - Q[0]) + 6 * ((1 - ts) * ts)[:, None] * (Q[2] - Q[1]) + 3 * (ts ** 2)[:, None] * (Q[3] - Q[2])
                d2 = 6 * (1 - ts)[:, None] * (Q[2] - 2 * Q[1] + Q[0]) + 6 * ts[:, None] * (Q[3] - 2 * Q[2] + Q[1])
                sp = np.linalg.norm(d1, axis=1)
                return (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / sp ** 3, sp
            x_ref = L + [0.0]
            def res(x):
                QA, QB = build(x)
                if mode == "lengths":
                    return [(kappa(QA, 0) - tJ) / max(abs(tJ), 1e-5), (kappa(QA, 3) - tF) / max(abs(tF), 1e-5),
                            (kappa(QB, 0) - tF) / max(abs(tF), 1e-5), (kappa(QB, 3) - tE) / max(abs(tE), 1e-5)]
                if mode == "roman":
                    # the roman's distribution: A meets the spine and the bowl curve at the ROMAN's curvature ratios;
                    # B keeps its lengths (it is the lean of the roman's bowl curve), only the re-aim at F touches it
                    kB0 = kappa(QB, 0)
                    r = [(kappa(QA, 0) - rJ * tJ) / max(abs(tJ), 1e-5), (kappa(QA, 3) - rF * kB0) / max(abs(kB0), 1e-5)]
                    reg = [0.05 * (x[2] - L[2]) / L[2] * 100, 0.05 * (x[3] - L[3]) / L[3] * 100, 0.3 * x[4] / math.radians(self.REAIM_MAX)]
                    return [10 * v for v in r] + reg
                r = [(kappa(QA, 0) - tJ) / max(abs(tJ), 1e-5), (kappa(QA, 3) - kappa(QB, 0)) / max(abs(tF), 1e-5),
                     (kappa(QB, 3) - tE) / max(abs(tE), 1e-5)]
                if mode == "g2":
                    # no fairness: the least change of the handles that meets the three G2 conditions
                    reg = [0.3 * (xi - xr) / xr for xi, xr in zip(x[:4], L)] + [0.3 * x[4] / math.radians(self.REAIM_MAX)]
                    return [10 * v for v in r] + reg
                # "fair" (pass 2a): the curvature's change along the arc, per unit length
                ka, sa = kcurve(QA); kb, sb = kcurve(QB)
                kk = np.r_[ka, kb[1:]]; ss = np.r_[sa, sb[1:]] / 40.0
                dk = np.diff(kk) / np.maximum(0.5 * (ss[1:] + ss[:-1]), 1e-6)
                w = self.FAIR_W / max(abs(tF), 1e-5) * 40.0
                return [10 * v for v in r] + list(w * dk * np.sqrt(0.5 * (ss[1:] + ss[:-1])) / np.sqrt(np.sum(ss)))
            x0 = L + ([0.0] if fair else [])
            lo = [0.4 * v for v in L] + ([-math.radians(self.REAIM_MAX)] if fair else []); hi = [2.5 * v for v in L] + ([math.radians(self.REAIM_MAX)] if fair else [])
            sol = least_squares(res, x0, bounds=(lo, hi))
            phi = float(sol.x[4]) if fair else 0.0
            QA, QB = build(sol.x)
            for (i, q) in zip(ia[1:3], QA[1:3]):
                self.new[i] = q
            for (i, q) in zip(ib[1:3], QB[1:3]):
                self.new[i] = q
            self.g2_report.append(dict(arc=[J, F, E], mode=self.spine_g2, reaim_at_F_deg=round(math.degrees(phi), 2),
                                       handles=[round(float(x / l), 3) for x, l in zip(sol.x[:4], L)],
                                       curvature_before=dict(A_at_J=round(kA0, 5), A_at_F=round(kA3, 5), B_at_F=round(kB0, 5), B_at_E=round(kB3, 5)),
                                       targets=dict(J=round(tJ, 5), F=round(tF, 5), E=round(tE, 5)),
                                       residual=[round(float(v), 3) for v in sol.fun[:4]]))

    def _stem_end_maps(self):
        U = self.U
        for pc in self.stem_end_pieces():
            ys = [U.xy[nd][1] for nd in U.contours[pc["ci"]]["ons"]]
            cen = np.mean([U.xy[nd] for nd in pc["nodes"]], axis=0)
            leading = cen[1] > (min(ys) + max(ys)) / 2.0
            rule = self.terminal_rule
            if rule == "a":
                rule = "roman" if leading else "shear"
            elif rule == "flip":
                rule = "shear" if leading else "roman"
            elif rule == "b":
                rule = "roman"          # "b" (cut keeps its angle to its stroke) is not defined for a sheared stroke end: its stroke does not turn
            L = np.eye(2) if rule == "roman" else self.S.L.copy()
            first, last = pc["nodes"][0], pc["nodes"][-1]
            t = np.mean([self.S(U.xy[first]) - L @ U.xy[first], self.S(U.xy[last]) - L @ U.xy[last]], axis=0)
            m = Map(L, t)
            for nd in pc["nodes"]:
                self.map[nd] = m; self.why[nd] = "stroke end rides its sides (I15, %s, %s)" % (rule, "leading" if leading else "trailing")
                self.terminal_nodes.add(nd)
            self.pieces.append((list(pc["nodes"]), self.S, self.S, pc["ci"]))
            cut = pc["cut"]; e = U.xy[cut["gj"]] - U.xy[cut["gi"]]; e = e if e[1] > 0 else -e
            ang = lambda v: round(math.degrees(math.atan2(v[0], v[1])), 2)
            self.stem_end_report.append(dict(nodes=pc["nodes"], leading=bool(leading), rule=rule, cut=(cut["gi"], cut["gj"]),
                                             cut_roman_deg=ang(e), cut_slant_deg=ang(self.S.L @ e), cut_new_deg=ang(L @ e),
                                             bounding_chords=pc["chords"]))

    # -- I17 target: the TRUE vertical tangent (as built in the s round) or the tangent parallel to the ITALIC angle --
    #    (shipped: "italic"; Mark's o / p nodes sit there, sheets/I17_opa.png)
    I17_TARGET = "italic"

    def _reseat(self):
        import skeleton5s as S5
        if self.I17_TARGET == "vertical":
            return Skeleton5s._reseat(self)
        K = self.K
        vt = S5.vertical_ts
        S5.vertical_ts = lambda P: vt(np.array([[q[0] - K * q[1], q[1]] for q in P]))     # tangent parallel to (K, 1)
        try:
            return Skeleton5s._reseat(self)
        finally:
            S5.vertical_ts = vt

    def report(self):
        R = Skeleton5s.report(self)
        R.update(serif_rule=self.serif_rule, side_handles=self.side_handles, pull_k=self.pull_k, pull=self.pull_report,
                 spine_g2=self.g2_report,
                 serifs=self.serif_report, stem_ends=self.stem_end_report, waists=self.waists,
                 spine_segments=[(sg["gi"], sg["gj"]) for sg, _ in self.spine_segments()] if self.i16 else [])
        return R
