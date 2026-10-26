"""ItalicMover: optically correct a sheared (oblique) copy toward a true italic by moving GROUPS of points rigidly.

THE RULESET (no rule names a glyph or a node; every move falls out of the parts, the measurement and the groups).
Round 5's rules I10-I14 are at the end of this docstring.
The Harvey rule each one stands on is named: unchanged, adapted or new. R6, R7, R9, R10, R11, R13, R14 and R16 run as
GroupMover's own code (groupmove.py), unchanged; R2, R3, R8, R12 and R15 are adapted below; R1 is replaced (stems are
corrected too); I1, I2 and I9 (half-angle extrema) are new.

Correspondence and measurement
 I1  Correspondence (new). The slant is the upright sheared (x' = x + y/4). The parts, sides and rungs are read on
     the UPRIGHT and carried onto the slant node for node: every point of a side is the same (segment, t) on the
     slant, so every rung keeps its two ends. The pairing is never re-read on the slant (a shear changes angles,
     so the detectors may disagree there; the designer's correspondence survives it).
 I2  Target (new; replaces R1-R2's growth A). A rung's target width is the upright's width on that rung; the needed
     change is D = target - width measured on the slant, signed: a part that came out too thick thins (D < 0),
     too thin fattens (D > 0). Rungs are read at the nodes and every ~12 u between them (the dense rows of
     move.Mover). A rung with |D| < 1.5 u is left alone (noise floor); a rung asking for more than twice what the
     shear can change (2 x (lambda_max - 1) of its width, 27% at 14 deg) is a mis-pairing, not a width, and asks nothing; so is a rung running more than 1.6 x its width along the stroke (skewed). Stems are corrected like every other part
     (a vertical stem reads cos 14 deg = 3% thinner after the shear); a part that is a dot never moves; a root
     rung (the part emerging from another) asks nothing; flags,
     serifs, brackets, balls and spurs are held (spec rule 8) and never move.
 I3  Amount (R2 adapted). Each side of a rung takes D/2 x (1 - own hold + partner hold) along the rung's normal;
     holds are move.Mover's: a surface facing a metric line of its case holds (spec rule 7). A thinning move is
     the normal reversed, so the shares of a stroke's two sides still turn against each other (R4) and a node
     pushed both ways still pinches (R12).

Which nodes hold the part
 I4  Cores (R3 adapted). A node is a core where its rung's |D| is at least max(1.5 u, 0.5 x the largest |D| at
     any node of that part), and its share is at least 1 u (a node held by a metric line is no core).
 I5  Grades (R8 adapted). Walking out of a group, a node whose D has the core's sign joins graded by
     |D| / the core's |D|: >= 1/2 -> 2/3, else 1/3; the taper never rises outward. A node whose D changes sign
     or is below the noise floor is an anchor (R9).
 I6  Groups (R4, R5 unchanged). A group is a run of consecutive cores on one side; it moves as one rigid piece
     by one vector, snapped to x, y, the italic angle (atan K: 18.43 deg in round 5) or a straight edge beside the run, by the same
     cost; the magnitude gives the largest core its share; handles travel with their nodes.
 I7  Carry, slide, junctions, terminals, thin cut faces, the segment guard (R6, R7, R10, R11, R12, R13
     unchanged; R12 adapted: ANY cut face no group reaches -- not only a thin one -- slides each end along itself to
     where its side's moved line meets it, at most 1.6 x the share and 1/4 of the face, thinning or fattening).
     A side running on smoothly into the next wall (a serif's bracket, the next part's side) is no junction.
     A stem side meeting a serif's bracket ends there: the junction node moves with the stem side and
     the bracket, running to the held serif, is a connecting curve (R14).
 I8  Curves and the axis (R14, R16 unchanged; R15 adapted). A connecting segment is the drawn curve turned and
     scaled as one piece onto its new chord; smooth nodes stay smooth (a straight edge wins), and a node is smooth
     when it is drawn smooth OR its two tangents meet within 3 deg (what the eye and the comb read as smooth); every node and handle moves
     linearly from the slant (t = 0) to the corrected (t = 1); node count, order, handles and segment types never
     change.
 I9  Half-angle extrema (new; Mark's Italify measurement). The extrema of a round contour sit where a HALF-angle slant
     would put them; the body keeps the full slant, then the curves are re-fitted. Every smooth on-curve node between
     two curves (a mid-curve node) on a side of a part slides along its own tangent by tan(slant / 2) x its offset
     from its contour's centre (the lever arm across the tangent, read on the upright: the radius for an extreme).
     The centre is that of the closed contour's box, or, for an open run, of the run between the nearest nodes that
     may not slide. The sense undoes the shear's stretch -- the half-angle field -tan(slant/2) x (dy, dx) taken along
     the tangent: for a rightward slant top <-, bottom ->, left up, right down; the sign comes from the slant, so a
     leftward slant mirrors it. Outer and counter alike. Held nodes (serif, flag, ball, spur), junctions, cut-face
     ends, pinched nodes, nodes next to a straight segment and INFLECTION nodes (where a counter turns into a spine:
     each bowl is its own round part with its own centre, so a run ends there, also where the inflection lies inside a
     curve) do not slide -- except a spine's flat middle (the centre
     anchors: a straight run <= 120 u between two curves, smooth at both ends), which is ONE mid-curve node: both ends
     slide together along the run's direction, lever at its midpoint (Sebastian: the italic s only works without the
     centre spine anchors; keeping the nodes, this lets the spine flow). Slides run after the groups and add to a
     node's group vector. Every curve touching a slid node keeps both handle DIRECTIONS as drawn and scales both handle
     LENGTHS by its chord (new chord / drawn chord), as Italify does; nothing turns, so no R15 re-alignment is needed
     (a slide along the tangent keeps the node's tangent); at an end the slide did not move, the handle keeps the tangent
     the group rules gave that node, so it stays smooth with its other side. Last, at every slid node the two handles
     share their chord-scaled total length so the curvature on both sides of the node is the same (G2: endpoint
     curvature is (2/3) d / L^2, so L_a / L_b = sqrt(d_a / d_b)) -- Mark's "fitting the handles among each other";
     without it one side reads pointy and the other flat. Then G2 fans (Mark: "manipulate many vector handles"):
     Linus Romer's Curvatura harmonize-handles (tools/harmonize.py) runs over every contour that has a slid node --
     each smooth node between two curves takes the mean of its two sides' curvatures, each curve's handle LENGTHS are
     solved for them (directions kept, nodes fixed, 5 passes); held, junction, cut-face and pinched nodes keep their
     curvature; a solution outside 0.25-2.5 x a handle's incoming length is refused (it collapses a handle into a
     curvature needle). Harmonizing instead of the share was worse on the combs, so the share runs first
     (HARMONIZE = "after_share"). R14 / R15 stay as they are for segments the groups moved.
     Round 1's re-tension is still in the module, OFF (RETENSION).
     ROUND 5: I9 is OFF (class flag I9 = False); I10 replaces it. I9 = True puts round 4's slides back on top, for the
     comparison sheet only (sheets/i9_vs_i10_18.png).

ROUND 5 (italic/r5, 2026-10-25). The shear is one parameter, K (carry.set_slant: 1/3 = 18.43 deg, the deliverable;
1/4 = 14.04 deg, to score against Mark's drawings). The group rules no longer start from the plain slant: they start
from the SKELETON base (tools/skeleton.py), which I10-I12 and I14 build from the upright node for node, each on-curve
node carried by one affine map from its class and its handles by the same map (so smooth stays smooth); I13 sets
the widths the group rules then correct; the harmonizer runs last (tools/harmonize_pass.py). tools/round5.py chains them.
 I10 Two-angle shear (new; replaces I9). Stems, straight parts, bars and serifs lean the full angle theta; a ROUND part
     (a run of smooth curve-to-curve nodes, split at curvature sign changes, an outer run with the counters inside its
     box) leans rho x theta about its own centre, which stays where the shear puts it: p' = S(c) + [[s, tan(rho theta)],
     [0, 1]] (p - c). A junction node (a non-round node next to a round run, an inflection node between two runs, the
     end of a part buried in another's ink) takes the mean of its two sides' maps: the join is blended, and the cubic
     between two nodes of different classes carries each end by its own node's map. rho = 0.70 (Mark's drawn o, p, s,
     a by score; study default 0.6).
 I11 Bowl narrowing (new). The same map's x-scale: s = 1 - nu on an outer run, 1 - nu W / w on its counters (both
     sides of the stroke lose the same units); stems and serifs untouched. nu = NU_COEF x tan(theta); Mark's drawings
     say NU_COEF = 0 (o +1.3 %, p -1.4 %: he does not narrow), the study's default 0.6 is 15 % at 14 deg. The rule is in,
     at zero.
 I12 Rigid spine (new). The s's spine edges (the cubics holding the curvature sign change between the two bowls) turn
     as one piece by psi x theta clockwise about the mean of their inflections, placed where the shear puts it: the end
     nodes keep their bowls' maps and handle directions, the two handle lengths are fitted (least squares) to the drawn
     edge carried by the rigid turn in the spine's core (within 20 deg of its inflection tangent), blended over 45 u
     into the bowls. psi = 0.80 (score; the drawn spine's tangent turns 1.18 theta; study 0.75). The z's diagonal as a
     spine is built and OFF (Skeleton.I12_DIAGONAL): it made the z worse (NOTES).
 I13 Thickness by direction (new; replaces I2's single target). A rung's target is read by its stroke direction on the
     upright: '\' -> the roman width; '/' -> halfway from the width it has to the roman's; vertical -> the roman's
     HORIZONTAL measure (w_up / sin a_up x sin a_now: a sheared stem asks nothing, round 4's 2.5 u / 2.8 u stem
     correction is gone); horizontal -> the roman width. The rest of I2-I8 acts on D as before; because the remaining
     '\' thickening of a bowl sits BETWEEN its nodes (at the 45 deg places), round 1's re-tension is ON in round 5
     (RETENSION): each curve on a side of a part keeps its nodes and handle directions and takes the handle lengths
     that best fit the needed change along it (0.5-1.6 x).
 I14 Cuts keep the roman angle (new; replaces "held serif" by "held angle, moved position"). In the skeleton a serif
     group (the held nodes of a stem group: feet, heads, flags, brackets, spurs) is carried RIGIDLY by the shear's move
     at the height where it meets its stem; a TERMINAL (the non-round nodes between two round nodes: the s's beaks, the
     e's flick, the a's hood) is carried rigidly by its part's map at its centre with half the part's narrowing taken
     back. In the group rules every such terminal node is held (extra_held): its cut never turns.

ROUND 5 · s ROUND (italic/r5/s, 2026-10-25). The s alone, on Mark's drawn ROMAN s (anchor-free) as the upright, scored
against his drawn italic s at 14.04 deg. I10 (rho 0.70), I11 (nu 0) and I13 are kept; I12 and, for terminals, I14 are
replaced by I15-I17 (tools/skeleton5s.py; the pipeline is tools/round5s.py). Node count, order, handles and segment
types never change.
 I15 Terminals ride (new; replaces I14 for terminals). A terminal (the non-round nodes between two round nodes: an s's
     beak and its cut) is ONE piece carried by the motion of the two sides it ends: its translation is the mean of the
     two sides' own maps (I10) at the terminal's end nodes (the end of the side coming in, the end of the side going
     out), so the cut goes where its sides go. Its linear part, i.e. its cut angle, is set by the stroke's direction:
     the LEADING terminal (the stroke's entry, the one in the upper half of its contour, hanging from the x-height)
     keeps its ROMAN shape; the TRAILING terminal (the exit, near the baseline) keeps the SHEAR. (Mark's s: upper cut
     5.9 deg from vertical against the roman's 5.8; lower 11.8 against the shear's 10.2. Tested and lost: "a cut keeps
     its angle to its stroke", which turns both cuts alike, 12.2 / 1.4 deg.) In the group rules the piece is final: its
     own rungs ask nothing and a side's group ends at it (extra_held). Letting the width rules core it bent the lower
     beak's inner side into a hook (+23 points of XOR in that terminal).
 I16 Rigid spine piece (new; replaces I12). The spine of an s (the two cubics holding the curvature sign change
     between the bowls, junction node to junction node) turns as ONE piece, nodes AND handles, by psi x theta clockwise
     about its centre (the mean of the edges' inflections), placed where the shear puts it; handle lengths unchanged.
     The connecting curve beyond each junction is the I10 curve turned and scaled onto its new chord (R14); R15: at the
     junction the rigid spine's tangent wins, at the far node the base tangent is kept. psi = 1.23 (his node vectors,
     both spine edges, Procrustes; by score 1.25-1.30; round 5 used 0.80).
 I17 Re-seat side extremes (new; rule G). After the lean, a node that is a side extreme on the upright slides along
     the outline to the true vertical tangent, its handles vertical (the shortened neighbour split exactly, the
     lengthened one refitted), shape neutral -- EXCEPT a node a rigid piece carries (I16): the rigid piece wins. On the s
     every side extreme is a spine junction, so I17 does nothing to the s: Mark's spine-end nodes keep the spine's turn
     (13-18 deg off vertical) and sit 19-41 u from the vertical tangent of his own outline.
ROUND 5 · PASS 2 (italic/r5/pass2, 2026-10-25). The s round's I15-I17 carried back to the full set (19 letters), from
the extracted Regular (the s: Mark's drawn roman s, the newer source, tools/build_his_s.py), at 14.04 and 18.43 deg (tools/skeleton_p2.py, tools/round_p2.py). I10 (rho 0.70), I11 (nu 0), I13
and the harmonizer (last, two guards) are round 5's. Node count, order, handles and segment types never change.
 I14 for serifs, by the stroke a serif ends. A serif is not a terminal: entry / exit does not apply. A serif hanging from
     a HORIZONTAL stroke (an arm or bar end: its held piece taller than wide -- T's arms, E's three arms, z's beaks) keeps
     the SHEAR (it is sheared with its arm); a serif sitting on a stem (feet, heads, flags: wider than tall) keeps the
     roman angle, rigid at its joint, as in pass 1. Pass 1's all-roman serifs read as upright spikes on T and E at 18.43.
 I15 terminals ride, extended. (a) A terminal ends ONE part: the non-round run between two round nodes is a terminal
     only when the runs on both sides belong to the same part; between two parts it is a waist (B's 40-41), a junction.
     (b) A stroke end inside a stem group (f's hook, r's arm, j's and y's tails): nodes joined by lines, bounded by curves
     (one of them a stroke side, chord >= 1 stem), holding a free steep cut (12 u to 1.5 stems, > 45 deg from horizontal,
     empty ink outside). It rides its sheared sides; LEADING (upper half of its contour) keeps the roman cut, TRAILING
     keeps the shear; it holds in the group rules. Pull-in toward the letter's middle (k tan(theta) x height from
     mid-height) was tested at k 0 / 0.5 / 1: k = 0 (it worsened the 14.04 deg score and ballooned the arc into the beak).
 I16 rigid spine piece, plus: the bowl arc from each spine junction J to the next terminal end E (the connecting curve
     J->F and the bowl curve F->E) is re-faired: its four handle lengths and one common turn of the two handles at F
     (capped at 3 deg: at 15 the counter arcs of Mark's s turned 12 and ran flat into the beak) are solved for G2 with the spine at J, G2 at F, the terminal's end curvature
     at E kept, and an even comb along the arc. Without it the similarity ran flat into F with a curvature step at F
     (Mark on the s round's 18.43 deg comb). Only the s has a spine in this set; the z's diagonal stays off.
 PASS 2b (2026-10-26). I14b: a stem serif's slab AND its brackets are one rigid ROMAN piece carried by K x the mean
     height of the brackets' junctions with the stem (2a: K x the slab's top height, brackets as the shear); a bracket
     whose junctions differ in height is scaled onto its new chord (R14 lengths, R15 directions). Mark's drawn p foot is
     the plain shear (NOTES). I16's arc re-fair drops its fairness term: the connecting curve meets the spine and the
     bowl curve at the ROMAN's curvature ratios (2a pulled the bowls toward circles and flattened top and bottom).
 I17 re-seat side extremes: built, OFF. The s round's target (the TRUE vertical tangent) slides the o's side nodes 58 /
     85 u the wrong way and loses on o, p, a; a target at the ITALIC-angle tangent slides them 28 / 43 u where Mark's outer
     o nodes are and wins a little on XOR (o 7.9 -> 7.5, p 8.3 -> 8.1), but his o counter and p nodes stay unmoved: not
     shipped, a question for Mark (sheets/I17_opa.png).
"""
import sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
import carry as C
from move import Mover
from groupmove import GroupMover, SIN_TOL, MAX_EXT, CARRY_RATIO, BLUNT, dot, cross, add, sub, mul, norm
from parts import unit

FLOOR = 1.5          # u: a rung needing less than this is left alone (I2), and a node below it is an anchor (I5)
FLAT_RUN_MAX = 120.0 # u: a straight run between two curves up to this long is a spine's flat middle (I9: one sliding node)
CORE_OF_MAX = 0.5    # I4


class CarriedMover(Mover):
    """move.Mover on a pairing carried from the upright (I1): same holds, stroke rows and host walls"""

    def __init__(self, g, P, mi):
        self.g = g; self.mi = mi
        self.slant = mi["ia"]; self.A = mi["A"]; self.thin_top = mi["thin_top"]
        self.thick_bot = 0.95 * mi["stem"]
        self.lines = list(mi["lines_uc"] if g["glyph"][:1].isupper() else mi["lines_lc"])
        self.height = mi["x_height"] if g["glyph"].islower() else mi["cap_height"]
        self.stem = mi["stem"]
        ys = [n[1] for c in g["contours"] for n in c["nodes"] if n[2] != "o"]
        self.y_lo, self.y_hi = min(ys), max(ys)
        self.P = P; self.ol = P.ol
        self.disp, self.node_host, self.rung_log = {}, {}, []
        self._compute()


def _up_rung(st, sa, sb):
    """the UPRIGHT's width on the rung at slant arc lengths (sa, sb) and its mean tangent there (upright)"""
    SA, SB = st["A"], st["B"]
    fa, fb = C._frac(SA.al, sa), C._frac(SB.al, sb)
    def at(S, f):
        i = min(int(f), len(S.P_up) - 2); u = f - i
        return S.P_up[i] + (S.P_up[i + 1] - S.P_up[i]) * u, S.T_up[min(int(round(f)), len(S.T_up) - 1)]
    pa, ta = at(SA, fa); pb, tb = at(SB, fb)
    mt = unit((ta[0] + tb[0], ta[1] + tb[1]))
    rx, ry = pb[0] - pa[0], pb[1] - pa[1]
    return abs(rx * mt[1] - ry * mt[0]), mt


def i13_target(w_up, t_up, w_now, t_now):
    """I13 thickness by direction (round 5): the target width of a rung, from the upright's width and stroke direction
    (t_up) and the width / direction it has now (on the base outline the group rules correct):
      '\\'        -> the roman width (the shear's thickening is undone in full)
      '/'          -> halfway between the width it has now and the roman's (the thinning is undone only half)
      vertical     -> the roman's HORIZONTAL measure kept: w_up / sin(a_up) x sin(a_now) (a = the stroke's angle to the
                     x axis); a shear keeps horizontal measures, so a stem asks nothing (round 4 fattened it 2.5 u)
      horizontal   -> the roman width"""
    cls = C.direction_class(t_up)
    if cls == "\\":
        return w_up, cls
    if cls == "/":
        return w_now + 0.5 * (w_up - w_now), cls
    if cls == "vertical":
        su = abs(t_up[1]) / max(1e-9, math.hypot(*t_up)); sn = abs(t_now[1]) / max(1e-9, math.hypot(*t_now))
        return w_up / max(su, 1e-6) * sn, cls
    return w_up, cls


def _up_width(st, sa, sb):
    """the UPRIGHT's width on the rung that sits at slant arc lengths (sa, sb) (same fractional sample index)"""
    SA, SB = st["A"], st["B"]
    fa, fb = C._frac(SA.al, sa), C._frac(SB.al, sb)
    def at(S, f):
        i = min(int(f), len(S.P_up) - 2); u = f - i
        return S.P_up[i] + (S.P_up[i + 1] - S.P_up[i]) * u, S.T_up[min(int(round(f)), len(S.T_up) - 1)]
    pa, ta = at(SA, fa); pb, tb = at(SB, fb)
    mt = unit((ta[0] + tb[0], ta[1] + tb[1]))
    rx, ry = pb[0] - pa[0], pb[1] - pa[1]
    return abs(rx * mt[1] - ry * mt[0])


class ItalicMover(GroupMover):
    def __init__(self, g_slant, g_upright=None, extra_held=()):
        self.extra_held = set(extra_held)     # round 5, I14: terminals placed rigidly by the skeleton hold here
        if g_upright is None:
            g_upright = C.load()["GeistSerifRegular_" + g_slant["glyph"]]
        self.g_up = g_upright
        mi = C.master_info(g_slant["glyph"], C.SLANT)
        self.P_up = C.parts_of(g_upright)
        P = C.carry(self.P_up, g_slant["contours"], C.SLANT)
        M = CarriedMover(g_slant, P, mi)
        GroupMover.__init__(self, g_slant, mover=M)
        if self.RETENSION:
            self._retension()                 # round 1's I9, off by default (see the docstring)
        if self.I9:
            self._slides()                    # round 4's half-angle extrema: OFF in round 5 (I10 replaces it), kept for the comparison sheet
        else:
            self.slides_i9 = []; self.chord_scaled = []

    # ---- R15 adapted: smooth is what the eye (and the comb) reads ------------------------------------------------
    SMOOTH_DEG = 3.0
    def _index(self):
        GroupMover._index(self)
        for C_ in self.contours:
            for nd in C_["ons"]:
                if self.smooth.get(nd):
                    continue
                sb, sa = self.seg_before[nd], self.seg_after[nd]
                if sb["kind"] == "line" and sa["kind"] == "line":
                    continue
                a = self.seg_dir_at(sb, nd); b = self.seg_dir_at(sa, nd)
                if dot(a, b) < -math.cos(math.radians(self.SMOOTH_DEG)):
                    self.smooth[nd] = True            # drawn as a corner, read as smooth: kept smooth (R15)

    # ---- I2-I4: proposals from the target -----------------------------------------------------------------------
    def _proposals(self):
        M = self.M
        kinds = M.stroke_kind
        self.props, self.inspan, self.stroke_max = {}, {}, {}
        self.delta = {}                       # node -> signed D (its rung's)
        self.row_delta = []                   # per stroke: [(row, D)]
        self.side_field = []                  # per side: (Side, stroke, arc positions, signed shares, outward normals)
        for si, ((st, rows), (is_stem, is_dot)) in enumerate(zip(M.stroke_rows, kinds)):
            SA, SB = st["A"], st["B"]
            # signed D per row (I2); a root rung and a hidden row take their nearest visible neighbour's
            frozen = is_dot
            D = []
            for row in rows:
                if frozen:
                    D.append(0.0); continue
                sa, sb = row["r"][0], row["r"][1]
                if self.I13:
                    wu, tu = _up_rung(st, sa, sb)
                    ta_, tb_ = SA.tan(sa), SB.tan(sb)
                    tn = unit((ta_[0] + tb_[0], ta_[1] + tb_[1]))
                    tgt, _cls = i13_target(wu, tu, row["th"], tn)
                    D.append(tgt - row["th"])
                else:
                    D.append(_up_width(st, sa, sb) - row["th"])
            vis = [i for i, row in enumerate(rows) if not row.get("root") and not row.get("hid")]
            for i, row in enumerate(rows):
                if row.get("root"):
                    D[i] = 0.0              # the part emerges from another there: no stroke width to correct
                elif row.get("hid") and vis:
                    D[i] = D[min(vis, key=lambda k: abs(k - i))]
            # I2 ceiling: a shear of k changes a width by at most (lambda_max - 1) (13% at 14 deg); a rung asking for more
            # than twice that of its own width is a mis-pairing (a rung across the whole counter), not a width: it asks nothing
            kk = abs(math.tan(math.radians(self.slant)))
            lam = math.sqrt(1 + kk * kk / 2 + kk * math.sqrt(1 + kk * kk / 4))
            ceil = 2.0 * (lam - 1.0)
            # ... and a rung running more than 1.6 x its own width along the stroke is skewed (a pairing that drifted round a
            # counter: move.py's root test, applied to every rung): no measurement either
            D = [0.0 if (abs(d) < FLOOR or abs(d) > ceil * max(row['th'], 1.0) or row['L'] > 1.6 * max(row['th'], 1.0)) else d for d, row in zip(D, rows)]
            self.row_delta.append(list(zip(rows, D)))
            # the rung normal per row (as GroupMover: perpendicular to the mean of the two sides' tangents)
            nrm = []
            for row in rows:
                ta, tb = SA.tan(row["r"][0]), SB.tan(row["r"][1])
                mt = (ta[0] + tb[0], ta[1] + tb[1])
                if norm(mt) < 0.3:
                    n_ = row["d"]
                else:
                    mt = unit(mt); n_ = (-mt[1], mt[0])
                    if dot(n_, row["d"]) < 0: n_ = (-n_[0], -n_[1])
                nrm.append(n_)
            for i, row in enumerate(rows):
                if row.get("root"):
                    j = min((k for k in range(len(rows)) if not rows[k].get("root")), key=lambda k: abs(k - i), default=i)
                    nrm[i] = nrm[j]
            mx = 0.0
            stroke_sides = []
            for S, key, sgn, own, oth in ((SA, 0, -1.0, "hA", "hB"), (SB, 1, 1.0, "hB", "hA")):
                pos = [row["r"][key] for row in rows]
                order = np.argsort(pos)
                pos = [pos[k] for k in order]
                # signed share along the outward normal (I3): + fattens, - thins
                ss = [D[k] / 2 * min(2.0, max(0.0, 1.0 - rows[k][own] + rows[k][oth])) for k in order]
                ds = [D[k] for k in order]
                ns = [nrm[k] for k in order]
                ths = [rows[k]["th"] for k in order]
                hids = [bool(rows[k].get("hid")) for k in order]
                lo, hi = pos[0], pos[-1]
                side_nodes = []
                for idx, nd in S.nodes:
                    if nd is None:
                        continue
                    s = S.al[idx]
                    # a node beyond the part's first or last rung by less than the part's width there (the
                    # square end rung of a slanted stroke lands past the end node) takes that end rung's values
                    if s < lo - max(6.0, ths[0]) or s > hi + max(6.0, ths[-1]):
                        continue
                    k = int(np.searchsorted(pos, s))
                    if k <= 0: sv, dv, n_, th, hid = ss[0], ds[0], ns[0], ths[0], hids[0]
                    elif k >= len(pos): sv, dv, n_, th, hid = ss[-1], ds[-1], ns[-1], ths[-1], hids[-1]
                    else:
                        s0, s1 = pos[k - 1], pos[k]
                        u = 0.0 if s1 == s0 else (s - s0) / (s1 - s0)
                        sv = ss[k - 1] + (ss[k] - ss[k - 1]) * u
                        dv = ds[k - 1] + (ds[k] - ds[k - 1]) * u
                        th = ths[k - 1] + (ths[k] - ths[k - 1]) * u
                        hid = hids[k - 1] if u < 0.5 else hids[k]
                        n_ = unit(add(mul(ns[k - 1], 1 - u), mul(ns[k], u)))
                    if th < 5.0:
                        sv = 0.0                  # a side closing to a point has no width to correct
                    if abs(dv) < FLOOR:
                        sv, dv = 0.0, 0.0
                    out = mul(n_, sgn)
                    p = dict(a=float(abs(sv)), dir=(out if sv >= 0 else mul(out, -1.0)), st=si, side=S, th=float(th), hid=hid,
                             core=False, nd=nd, delta=float(dv))
                    self.props.setdefault(nd, []).append(p)
                    self.inspan.setdefault(nd, set()).add(si)
                    side_nodes.append(p)
                    mx = max(mx, abs(sv))
                stroke_sides.append(side_nodes)
                if not is_dot:
                    self.side_field.append((S, si, pos, ss, [mul(n_, sgn) for n_ in ns]))
            allp = [p for sn in stroke_sides for p in sn]
            dmax = max((abs(p["delta"]) for p in allp), default=0.0)
            for p in allp:                                        # I4
                if abs(p["delta"]) >= max(FLOOR, CORE_OF_MAX * dmax) and p["a"] >= 1.0:
                    p["core"] = True
            self.stroke_max[si] = mx
        for nd, ps in self.props.items():
            best = max(ps, key=lambda p: (p["core"], p["a"]))
            self.delta[nd] = best["delta"]

    # ---- I7: a side flowing into a bracket is no junction --------------------------------------------------------
    def _classify(self):
        GroupMover._classify(self)
        self.held |= getattr(self, "extra_held", set())
        for nd in list(self.junction):
            J = self.junction[nd]
            if J["kind"] in ("flag", "side") and self._tangent_into_host(nd, J):
                del self.junction[nd]                     # it moves with its side; the bracket / the next part connects (R14)
        self.partners = {J["partner"] for J in self.junction.values() if J["partner"] is not None}

    def _tangent_into_host(self, nd, J):
        """the node's own side and the held wall it meets leave it in opposite directions within 10 deg (the side
        runs on smoothly into the wall: a bracket), so there is no wall to slide along"""
        h = J["hseg"]
        segs = [sg for sg in (self.seg_before[nd], self.seg_after[nd])]
        host = [sg for sg in segs if {sg["gi"], sg["gj"]} == {h.gi, h.gj}]
        own = [sg for sg in segs if sg not in host]
        if not host or not own:
            return False
        a = self.seg_dir_at(own[0], nd); b = self.seg_dir_at(host[0], nd)
        return dot(a, b) < -math.cos(math.radians(10.0))

    # ---- I7: cut faces no group reaches (R12 adapted) ------------------------------------------------------------
    def _moves(self):
        GroupMover._moves(self)
        moved = False
        for nd, faces in self.cut_face.items():
            if nd in self.vec or nd in self.held or nd not in self.share:
                continue
            a_, d, si = self.share[nd]
            if a_ < 0.5:
                continue
            f = self.line_dir(faces[0][0])
            c = dot(d, f)
            sl = a_ / c if abs(c) > 0.17 else 0.0          # to where the side's moved line meets the face
            sg0 = faces[0][0]
            Lf = norm(sub(self.xy[sg0["gj"]], self.xy[sg0["gi"]]))
            cap = min(1.6 * a_, 0.25 * Lf)                 # never more than 1.6 x the share, nor 1/4 of the face
            if any(p["hid"] for p in self.props.get(nd, [])):
                cap = min(cap, a_)                         # a buried end (inside another part) only follows its share
            sl = max(-cap, min(cap, sl))
            self.vec[nd] = mul(f, sl); self.how[nd] = "cut"
            self.cut_moves.append(dict(node=nd, vec=self.vec[nd]))
            moved = True
        if moved:
            self._line_guard()

    # ---- I5: grades by D ------------------------------------------------------------------------------------------
    def _best_group(self, ci, run, nodes):
        free = [nd for nd in nodes if nd not in self.junction] or nodes
        self._dcore = max((self.delta.get(nd, 0.0) for nd in free), key=abs)
        return GroupMover._best_group(self, ci, run, nodes)

    def _junction_group(self, ci, run, nodes):
        self._dcore = max((self.delta.get(nd, 0.0) for nd in nodes), key=abs)
        return GroupMover._junction_group(self, ci, run, nodes)

    def _extend(self, ci, run, nodes, v, m, strokes, tcore):
        """GroupMover._extend with the grade read from D (I5) instead of from width; everything else unchanged"""
        C_ = self.contours[ci]; ons = C_["ons"]; K = len(ons)
        nodeset = set(nodes)
        dcore = getattr(self, "_dcore", 0.0)
        mem, stops, cost = {}, [], 0.0
        for end_p, step in ((run[0], -1), (run[-1], +1)):
            lvl = 1.0
            p = end_p
            for _ in range(MAX_EXT):
                q = (p + step) % K
                j = ons[q]
                sg = self.seg_after[ons[p]] if step > 0 else self.seg_before[ons[p]]
                if j in nodeset or j in self.claimed or j in mem:
                    break
                if j in self.core_nodes:
                    stops.append((j, "core", lvl)); break
                beyond = ons[(q + step) % K]
                if beyond in self.core_nodes and beyond not in nodeset and beyond not in self.junction:
                    stops.append((j, "between", lvl)); break
                if j in self.cut_face:
                    stops.append((j, "cut", lvl)); break
                if j in self.held or j in self.pinch or j in self.junction or j in self.partners:
                    stops.append((j, "hard", lvl)); break
                if (self.inspan.get(j, set()) & strokes) and self.share.get(j, (0,))[0] < 1.0:
                    stops.append((j, "held", lvl)); break
                if sg["kind"] == "line":
                    c = abs(cross(v, self.line_dir(sg)))
                    cost += 2.0 * c
                    stops.append((j, "line", lvl)); break
                nxt = self.seg_after[j] if step > 0 else self.seg_before[j]
                if nxt["kind"] == "line":
                    dl = self.line_dir(nxt)
                    c = abs(cross(v, dl))
                    farn = nxt["gj"] if step > 0 else nxt["gi"]
                    if farn in self.partners or (farn in self.junction and norm(sub(self.xy[farn], self.xy[j])) <= BLUNT):
                        stops.append((j, "line", lvl)); break
                    if c <= SIN_TOL:
                        chord = max(1.0, norm(sub(self.xy[j], self.xy[ons[p]])))
                        mem[j] = (lvl, "slide", dl); cost += lvl * m * c / chord
                        stops.append((nxt["gj"] if step > 0 else nxt["gi"], "slide-end", lvl))
                    else:
                        stops.append((j, "tol", lvl)); cost += 1.0
                    break
                if not (self.inspan.get(j, set()) & strokes):
                    stops.append((j, "outside", lvl)); break
                dj = self.delta.get(j, 0.0)
                if dj == 0.0 or dj * dcore < 0:
                    stops.append((j, "sign", lvl)); break          # I5: below the floor, or D turns: anchor
                r = self.th.get(j, 999.0) / max(1.0, tcore)
                nj = self.share[j][1] if j in self.share else self.outline_normal(j)
                c = abs(dot(v, nj))
                chord = norm(sub(self.xy[j], self.xy[ons[p]]))
                if c <= SIN_TOL and (r <= CARRY_RATIO or chord < 2.0 * m * lvl):
                    mem[j] = (lvl, "carry", None); cost += lvl * m * c / max(20.0, self.th.get(j, 80.0))
                    p = q; continue
                qd = abs(dj) / max(1e-6, abs(dcore))
                wl = 2 / 3 if qd >= 0.5 else 1 / 3
                lvl = min(lvl, wl)
                mem[j] = (lvl, "graded", None)
                p = q
        return mem, stops, cost

    # ---- I9: re-tension the curves between the nodes ------------------------------------------------------------
    RETENSION = True          # round 5: I13 acts between the nodes through round 1's re-tension (handle lengths fitted to the needed widths)
    I9 = False                # round 5: I10 (skeleton.py) replaces I9; True = round 4's slides on top (comparison only)
    I13 = True                # round 5: thickness by direction (see the docstring)
    TENSION = (0.5, 1.6)
    def _retension(self):
        """a curve lying on one side of a part keeps its two nodes where the groups put them and its handle
        DIRECTIONS (so every smooth node stays smooth), and takes the two handle LENGTHS that best fit the needed
        change along it: each dense point of the side moved by its share along the outward normal, the field
        bent linearly so its ends land on the nodes' own moves (least squares; lengths within 0.5-1.6 x)"""
        new = self.new
        self.retensioned = []
        done = set()
        flat = [n for c in self.g["contours"] for n in c["nodes"]]
        for S, si, pos, ss, nout in self.side_field:
            if not any(abs(x) > 0.05 for x in ss):
                continue
            byseg = {}
            for m, src in enumerate(S.src):
                if src[0] != "hidden":
                    byseg.setdefault(src[0], []).append(m)
            for k, ms in byseg.items():
                sg = self.ol.segs[k]
                if sg.kind != "curve" or len(ms) < 6 or k in done:
                    continue
                key = (sg.gi, sg.gj)
                seg = self.seg_after.get(sg.gi)
                if seg is None or seg["gj"] != sg.gj or seg["kind"] != "curve":
                    continue
                if sg.gi in self.held or sg.gj in self.held:
                    pass
                o1, o2 = seg["offs"]
                def field(sv):
                    j = int(np.searchsorted(pos, sv))
                    if j <= 0: return mul(nout[0], ss[0])
                    if j >= len(pos): return mul(nout[-1], ss[-1])
                    u = 0.0 if pos[j] == pos[j - 1] else (sv - pos[j - 1]) / (pos[j] - pos[j - 1])
                    a = ss[j - 1] + (ss[j] - ss[j - 1]) * u
                    n_ = unit(add(mul(nout[j - 1], 1 - u), mul(nout[j], u)))
                    return mul(n_, a)
                ms = sorted(ms, key=lambda m: S.src[m][1])
                vals = [(S.src[m][1], S.pts[m], field(S.al[m])) for m in ms]
                if max(norm(v) for _, _, v in vals) < 0.5:
                    continue
                P0, P3 = self.xy[sg.gi], self.xy[sg.gj]
                Q0, Q3 = new[sg.gi], new[sg.gj]
                v0, v1 = sub(Q0, P0), sub(Q3, P3)
                f0, f1 = vals[0][2], vals[-1][2]
                c0, c1 = sub(v0, f0), sub(v1, f1)
                Q = []
                for t, p, v in vals:
                    w = add(v, add(mul(c0, 1 - t), mul(c1, t)))
                    Q.append((t, add(p, w)))
                d0 = unit(sub(new[o1], Q0)); d3 = unit(sub(new[o2], Q3))
                L1 = norm(sub(new[o1], Q0)); L2 = norm(sub(new[o2], Q3))
                if L1 < 1e-6 or L2 < 1e-6:
                    continue
                A11 = A12 = A22 = b1 = b2 = 0.0
                for t, q in Q:
                    u = 1 - t
                    wa = 3 * u * u * t; wb = 3 * u * t * t
                    bx = (u ** 3 + wa) * Q0[0] + (wb + t ** 3) * Q3[0]
                    by = (u ** 3 + wa) * Q0[1] + (wb + t ** 3) * Q3[1]
                    rx, ry = q[0] - bx, q[1] - by
                    ax, ay = wa * d0[0], wa * d0[1]; cx, cy = wb * d3[0], wb * d3[1]
                    A11 += ax * ax + ay * ay; A12 += ax * cx + ay * cy; A22 += cx * cx + cy * cy
                    b1 += ax * rx + ay * ry; b2 += cx * rx + cy * ry
                det = A11 * A22 - A12 * A12
                if abs(det) < 1e-9:
                    continue
                la = (b1 * A22 - b2 * A12) / det; lb = (A11 * b2 - A12 * b1) / det
                lo, hi = self.TENSION
                la = min(max(la, lo * L1), hi * L1); lb = min(max(lb, lo * L2), hi * L2)
                new[o1] = add(Q0, mul(d0, la)); new[o2] = add(Q3, mul(d3, lb))
                done.add(k)
                self.retensioned.append((sg.gi, sg.gj, round(la / L1, 3), round(lb / L2, 3)))

    # ---- I9: slide at a sign change ----------------------------------------------------------------------------------
    def _slides(self):
        """I9 half-angle extrema (see the module docstring)"""
        self.slides_i9 = []
        segs = [sg for C_ in self.contours for sg in C_["segs"]]
        if len(segs) != len(self.ol.segs):
            return
        self.segctl = [[sg["gi"]] + list(sg["offs"]) + [sg["gj"]] if sg["kind"] == "curve" else [sg["gi"], sg["gj"]] for sg in segs]
        th = math.radians(self.slant)
        if abs(th) < 1e-9:
            return
        half = math.tan(th / 2.0) * self.I9_GAIN   # signed: a leftward slant mirrors every sense below; I9_GAIN scales every slide
        xy_up = {}
        base_i = 0
        for c in self.g_up["contours"]:
            for i, n_ in enumerate(c["nodes"]):
                xy_up[base_i + i] = (float(n_[0]), float(n_[1]))
            base_i += len(c["nodes"])

        def end_curv(sg, at_end):
            # signed curvature of a cubic at one of its ends (sign = turning sense), 0 for a line
            if sg["kind"] != "curve":
                return 0.0
            P = [self.xy[sg["gi"]], self.xy[sg["offs"][0]], self.xy[sg["offs"][1]], self.xy[sg["gj"]]]
            if at_end:
                P = P[::-1]
            a, b = sub(P[1], P[0]), sub(P[2], P[1])
            L = norm(a)
            return 0.0 if L < 1e-9 else -(2.0 / 3.0) * cross(a, b) / L ** 3 if at_end else (2.0 / 3.0) * cross(a, b) / L ** 3

        def inflection(nd):
            # the curve turns the other way across this node: a counter running into a spine. Such a node is a
            # run's end (each bowl gets its own centre) and does not slide itself
            kb, ka = end_curv(self.seg_before[nd], True), end_curv(self.seg_after[nd], False)
            return kb * ka < 0 and min(abs(kb), abs(ka)) > 1e-5

        def inner(nd):
            # a COUNTER node: the ink lies on the convex side of the curve (the concave side, where the centre of
            # curvature is, is empty). Mark's drawn italics (2026-10-25) keep the counters where the shear put them;
            # only the outer side of a part slides, and its top comes into alignment over the counter's top.
            sa = self.seg_after[nd]
            if sa["kind"] != "curve":
                return False
            t = self.seg_dir_at(sa, nd)
            k = end_curv(sa, False)
            if abs(k) < 1e-6:
                return False
            n_c = (-t[1], t[0]) if k > 0 else (t[1], -t[0])        # toward the centre of curvature
            x, y = self.xy[nd]
            g = self.ol.shape_of[self.ol.segs[sa["k"]].pi] if "k" in sa else None
            probe = (x + n_c[0] * 6.0, y + n_c[1] * 6.0)
            return not any(self.ol.ink_shape(gi, probe[0], probe[1]) for gi in range(len(self.ol.shapes)))

        def stop(nd):
            if nd in self.held or nd in self.junction or nd in self.cut_face or nd in self.pinch:
                return True
            if self.seg_before[nd]["kind"] == "line" or self.seg_after[nd]["kind"] == "line":
                return True
            return inflection(nd)


        # a spine's flat middle (the centre anchors): a short straight run between two curves, smooth at both ends,
        # is ONE mid-curve node -- both ends slide together along the run's direction, lever at the run's midpoint
        self.flat_runs = {}
        for C_ in self.contours:
            for sg in C_["segs"]:
                a, b = sg["gi"], sg["gj"]
                if sg["kind"] != "line" or not (self.smooth.get(a) and self.smooth.get(b)):
                    continue
                if self.seg_before[a]["kind"] != "curve" or self.seg_after[b]["kind"] != "curve":
                    continue
                if norm(sub(self.xy[b], self.xy[a])) > FLAT_RUN_MAX:
                    continue
                if any(n in self.held or n in self.junction or n in self.cut_face or n in self.pinch for n in (a, b)):
                    continue
                self.flat_runs[a] = (a, b); self.flat_runs[b] = (a, b)
        # every smooth on-curve node with a curve on both sides (the rule is geometric: it does not depend on the
        # pairing having reached the node -- a counter's extremes count whether or not a rung lands on them)
        done_runs = set()
        for nd in [n for C_ in self.contours for n in C_["ons"]]:
            if nd in self.flat_runs:
                run = self.flat_runs[nd]
                if run in done_runs:
                    continue
                done_runs.add(run)
            elif stop(nd) or not self.smooth.get(nd):
                continue
            # the contour, or the run of it between the nearest nodes that may not slide
            ci = self.contour_of[nd]; ons = self.contours[ci]["ons"]; K = len(ons); p0 = ons.index(nd)
            run = {nd}
            closed = True
            for step in (-1, 1):
                q = p0
                for _ in range(K - 1):
                    q = (q + step) % K
                    run.add(ons[q])
                    if stop(ons[q]):
                        closed = False
                        break
            # the run's extent (for the lever): walk out of the node both ways along the upright contour, sampling,
            # and stop at a stop node or where the curvature changes sign INSIDE a curve (the counter running into
            # the spine): each bowl / counter is measured on its own
            segs_c = self.contours[ci]["segs"]
            seg_after_ = {sg["gi"]: sg for sg in segs_c}; seg_before_ = {sg["gj"]: sg for sg in segs_c}
            def samp(sg, rev):
                P = [xy_up[i] for i in ([sg["gi"]] + list(sg["offs"]) + [sg["gj"]])]
                out = []
                for tt in np.linspace(0, 1, 13):
                    if len(P) == 4:
                        u = 1 - tt
                        q = (u ** 3 * P[0][0] + 3 * u * u * tt * P[1][0] + 3 * u * tt * tt * P[2][0] + tt ** 3 * P[3][0],
                             u ** 3 * P[0][1] + 3 * u * u * tt * P[1][1] + 3 * u * tt * tt * P[2][1] + tt ** 3 * P[3][1])
                        d1 = (3 * u * u * (P[1][0] - P[0][0]) + 6 * u * tt * (P[2][0] - P[1][0]) + 3 * tt * tt * (P[3][0] - P[2][0]),
                              3 * u * u * (P[1][1] - P[0][1]) + 6 * u * tt * (P[2][1] - P[1][1]) + 3 * tt * tt * (P[3][1] - P[2][1]))
                        d2 = (6 * u * (P[2][0] - 2 * P[1][0] + P[0][0]) + 6 * tt * (P[3][0] - 2 * P[2][0] + P[1][0]),
                              6 * u * (P[2][1] - 2 * P[1][1] + P[0][1]) + 6 * tt * (P[3][1] - 2 * P[2][1] + P[1][1]))
                        kk = cross(d1, d2)
                    else:
                        q = (P[0][0] + (P[-1][0] - P[0][0]) * tt, P[0][1] + (P[-1][1] - P[0][1]) * tt); kk = 0.0
                    out.append((q, kk))
                return out[::-1] if rev else out
            pts = [xy_up[nd]]
            k0 = None
            for step in (1, -1):
                q = nd
                for _ in range(K):
                    sg = seg_after_.get(q) if step > 0 else seg_before_.get(q)
                    if sg is None:
                        break
                    stopped = False
                    for (pt, kk) in samp(sg, step < 0)[1:]:
                        if abs(kk) > 1e-6:
                            if k0 is None:
                                k0 = 1 if kk > 0 else -1
                            elif (kk > 0) != (k0 > 0):
                                stopped = True; break                   # inflection inside the curve: the run ends here
                        pts.append(pt)
                    q = sg["gj"] if step > 0 else sg["gi"]
                    if stopped or q == nd or stop(q):
                        break
            closed = (len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1e-6)
            if not inner(nd):
                # an OUTER extreme is measured to the centre of its whole contour (the bowl as a whole); a counter
                # extreme to the centre of its own counter (the inflection-bounded run above)
                pts = [xy_up[i] for i in self.contours[ci]["ons"]]
                for sg in segs_c:
                    pts += [pt for pt, _ in samp(sg, False)]
            if not pts:
                continue
            A = np.array(pts)
            cx, cy = (A[:, 0].min() + A[:, 0].max()) / 2, (A[:, 1].min() + A[:, 1].max()) / 2
            # undo half the shear's stretch: the half-angle field -tan(slant/2) x (dy, dx) about the centre (upright
            # coordinates), taken along the node's own tangent on the slant
            members = list(self.flat_runs[nd]) if nd in self.flat_runs else [nd]
            if len(members) == 2:
                x = (xy_up[members[0]][0] + xy_up[members[1]][0]) / 2; y = (xy_up[members[0]][1] + xy_up[members[1]][1]) / 2
                t = unit(sub(self.xy[members[1]], self.xy[members[0]]))          # the run's own direction
            else:
                x, y = xy_up[nd]
                t = self.seg_dir_at(self.seg_after[nd], nd)
            field = (-half * (y - cy), -half * (x - cx))
            sv = dot(field, t)
            if abs(sv) < 0.05:
                continue
            for m_ in members:
                self.vec[m_] = add(self.vec.get(m_, (0.0, 0.0)), mul(t, sv))
                self.new[m_] = add(self.new[m_], mul(t, sv))
                self.how[m_] = (self.how.get(m_, "") + "+slide").lstrip("+")
                self.slides_i9.append(dict(node=m_, slide=round(abs(sv), 2), dir=[round(t[0] * (1 if sv > 0 else -1), 3), round(t[1] * (1 if sv > 0 else -1), 3)],
                                           lever=round(math.hypot(x - cx, y - cy), 1), closed=closed, run=(len(members) == 2)))
        # handles of every segment touching a slid node: drawn direction kept, length x (new chord / drawn chord)
        # (a slide along the tangent keeps the node's tangent by construction: no turning, no R15 re-alignment)
        slid = {x["node"] for x in self.slides_i9}
        self.chord_scaled = []
        for sg in segs:
            if sg["kind"] != "curve" or not ({sg["gi"], sg["gj"]} & slid):
                continue
            gi, gj = sg["gi"], sg["gj"]; o1, o2 = sg["offs"]
            L0 = norm(sub(self.xy[gj], self.xy[gi])); L1 = norm(sub(self.new[gj], self.new[gi]))
            if L0 < 1e-6:
                continue
            k = L1 / L0
            for end, o in ((gi, o1), (gj, o2)):
                h0 = sub(self.xy[o], self.xy[end])
                d = unit(h0)
                if end not in slid:
                    # an end the slide did not move keeps the tangent the group rules gave it (R14 / R15), so it
                    # stays smooth with its other side; only the length follows the chord
                    hg = sub(self.new[o], self.new[end])
                    if norm(hg) > 1e-6:
                        d = unit(hg)
                self.new[o] = add(self.new[end], mul(d, norm(h0) * k))
            self.chord_scaled.append((gi, gj, round(k, 3)))
        if self.HARMONIZE != "instead":
            self._g2_balance(slid)
        if self.HARMONIZE:
            self._harmonize(slid)

    I9_GAIN = 1.0               # 1 = half-angle; 1.5 / 2 = fifty / a hundred per cent more slide on every extreme (same field, same handles)
    HARMONIZE = "after_share"   # "after_share": G2 share, then Curvatura's harmonize; "instead": harmonize only; None: share only
    def _harmonize(self, slid):
        """I9, G2 fans (Curvatura's harmonize handles, tools/harmonize.py): on every contour with a slid node, every
        smooth node between two curves takes the mean of its two sides' curvatures and each curve's handle lengths
        are solved (directions kept, nodes fixed) to reach those curvatures at both ends; held, junction and cut-face
        nodes are selection ends (they keep their curvature)."""
        from harmonize import harmonize_handles
        self.harmonized = []
        for ci, C_ in enumerate(self.contours):
            base = C_["base"]; N = C_["N"]
            if not any(base <= nd < base + N for nd in slid):
                continue
            nodes = [[self.new[base + i][0], self.new[base + i][1]] + list(n[2:]) for i, n in enumerate(self.g["contours"][ci]["nodes"])]
            for i, nd in enumerate(range(base, base + N)):
                if nd in self.smooth and self.smooth[nd] and len(nodes[i]) > 3:
                    nodes[i][3] = True
            which = {i for i in range(N) if (base + i) not in self.held and (base + i) not in self.junction
                     and (base + i) not in self.cut_face and (base + i) not in self.pinch}
            out = harmonize_handles(nodes, which)
            for i, n in enumerate(out):
                if n[2] == "o":
                    self.new[base + i] = (n[0], n[1])
            self.harmonized.append(ci)

    G2_SHARE = (0.6, 1.5)   # a handle may give or take at most this much of its chord-scaled length when balancing
    def _g2_balance(self, slid):
        """I9, last step ("fitting the handles among each other"): at a slid node with a curve on both sides the two
        handles keep their directions and their chord-scaled TOTAL length, but share it so that the curvature of
        the two curves at the node is the same (G2). Endpoint curvature of a cubic is (2/3) d / L^2 with L the
        node's own handle length and d the distance of the curve's far handle from the node's tangent line, so
        L_a / L_b = sqrt(d_a / d_b). Without this the slide leaves one side pointy and the other flat (Mark)."""
        self.g2_balanced = []
        for nd in sorted(slid):
            sb, sa = self.seg_before[nd], self.seg_after[nd]
            if sb["kind"] != "curve" or sa["kind"] != "curve":
                continue
            hb, ha = sb["offs"][-1], sa["offs"][0]            # this node's handles
            fb, fa = sb["offs"][0], sa["offs"][-1]            # the far handles of the two curves
            q = self.new[nd]
            vb, va = sub(self.new[hb], q), sub(self.new[ha], q)
            Lb, La = norm(vb), norm(va)
            if Lb < 1e-6 or La < 1e-6:
                continue
            t = unit(va)
            db, da = abs(cross(t, sub(self.new[fb], q))), abs(cross(t, sub(self.new[fa], q)))
            if db < 1e-6 or da < 1e-6:
                continue
            S = La + Lb
            r = math.sqrt(da / db)                           # La / Lb that equalises (2/3) d / L^2 on both sides
            La2 = S * r / (1.0 + r); Lb2 = S - La2
            lo, hi = self.G2_SHARE
            La2 = min(max(La2, lo * La), hi * La); Lb2 = min(max(Lb2, lo * Lb), hi * Lb)
            self.new[ha] = add(q, mul(unit(va), La2)); self.new[hb] = add(q, mul(unit(vb), Lb2))
            self.g2_balanced.append((nd, round(La, 1), round(La2, 1), round(Lb, 1), round(Lb2, 1)))

    def _pt(self, src, new):
        k, t = src; ctl = self.segctl[k]
        if len(ctl) == 2:
            p, q = new[ctl[0]], new[ctl[1]]
            return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
        P0, P1, P2, P3 = (new[i] for i in ctl); u = 1 - t
        return (u ** 3 * P0[0] + 3 * u * u * t * P1[0] + 3 * u * t * t * P2[0] + t ** 3 * P3[0],
                u ** 3 * P0[1] + 3 * u * u * t * P1[1] + 3 * u * t * t * P2[1] + t ** 3 * P3[1])

    def report(self):
        r = GroupMover.report(self)
        r["ruleset"] = "italicmove I1-I14 (round 5)"
        r["delta"] = {int(k): round(v, 2) for k, v in self.delta.items()}
        r["retensioned"] = getattr(self, "retensioned", [])
        r["slides"] = self.slides_i9
        for g in r["groups"]:
            g["rules"] = [x.replace("R8", "I5").replace("R4", "I6") for x in g["rules"]]
        return r


if __name__ == "__main__":
    G = C.load()
    for gl in (sys.argv[1].split(",") if len(sys.argv) > 1 else C.glyphs(G)):
        IM = ItalicMover(G["GeistSerifSlant_" + gl], G["GeistSerifRegular_" + gl])
        R = IM.report()
        print("==", gl)
        for g in R["groups"]:
            print("  g%d core %s ext %s graded %s slides %s vec %s |%.1f| %s %.0f° stops %s" % (g["id"], g["core"], g["ext"], g["graded"], g["slides"],
                  g["vector"], g["mag"], g["snap"], g["snap_deg"], g["stops"]))
        for j in R["junctions"]: print("  junction", j)
        for t in R["terminals"]: print("  terminal", t)
        for c in R["cuts"]: print("  cut", c)
        for p in R["pinch"]: print("  pinch", p)
