"""GroupMover: raise contrast by moving GROUPS of points rigidly (Mark, images/11-13; GRILL answers 2026-10-23).

THE RULESET -- the plain-language version for plugin authors is wmparts/RULES.md (same R-numbers; keep the two in
step when a rule changes). No rule names a glyph or a node: every move falls out of the parts (stem / flag-serif / stroke /
terminal / dot), the measurement (which nodes hold a thin part) and the group logic below. The number in
brackets is the GRILL answer each rule generalises; the per-glyph report names the rules behind every group.

Measuring (parts, rungs and holds are move.Mover's, unchanged: spec rules 3, 6, 7, 8, 9, 10/13, 20)
 R1  Parts. A stem (two straight sides at >= 0.75 stem weight, spec rule 3), any part that is nowhere
     thinner than 0.75 stem weight (curved or not: the j's stem running into its tail) and a dot never
     grow. Flags and serifs never move (spec rule 8). Every other stroke is a growing part.       [7C]
 R2  Amount. A growing part gets the full A at CNTR 100; each side takes A/2 x (1 - own hold + partner hold)
     (spec rule 6; a surface facing a metric line holds, spec rule 7). The width window of spec rule 2 no
     longer sets the amount.                                                                      [7C]
 R3  Where. Measured widths only decide which nodes HOLD the thin part: a node is a core when its width is
     <= 1.25 x the part's thinnest, or <= 0.8 x the master's stem, or a clear local minimum along its side
     (<= 0.8 x both neighbours). A side closing to a point has no width (its tip never grows).    [7C, 9B]

Groups
 R4  A group is a run of consecutive core nodes on one side of one stroke; it moves as ONE rigid piece by
     ONE vector, handles travelling with their nodes. A run is split where the shares turn against each
     other (the two sides of a stroke never share a group).                                       [1C, 11A]
 R5  Direction: the share-weighted stroke normal (perpendicular to the mean of the two sides' tangents),
     snapped to x, y, the italic angle, or a straight edge beside the run (edges up to 45 deg off, the rest
     up to 35; when the run's two ends have straight edges leaning to opposite sides of the move by about
     the same angle (within 25%: mirror images, a bar between two beaks) and the run has two nodes or more, neither
     is followed). The snap that disturbs least wins: angle off the normal + width change of carried nodes +
     how much a sliding end has to bend its segment + 1 for every stop at a free node. Magnitude: the
     largest core share / cos(snap angle), so the thinnest rung still gets its full growth.       [2A, 5A]
 R6  Carry. Walking out of the run, a node the vector runs ALONG (|v . normal| <= sin 25 deg) is carried at
     the full amount when it is at most 2 x the core's width, or when the segment to it is shorter than
     2 x the move (it cannot absorb the move).                                                    [1C (7), 5A]
 R7  Slide. A node whose next segment is a straight edge slides along that edge by the part of the vector
     running along it (at most 3/4 of the edge), so the edge stays on its drawn line; the group ends there.
     This holds outside the part too: the junction where an arch leaves a stem slides down the stem. [1C, 3A, 5A]
 R8  Grade. A node not carried joins with a reduced share, same direction, by its width against the core:
     <= 2.2 x -> 2/3, <= 3 x -> 1/3, thicker -> anchor. The taper continues outward (never rises). [8B, 9B]
 R9  Anchors. A walk stops at: a node held by a metric line (no share), a held flag node, a junction, a node
     of another stroke outside its span, a free node it can neither carry nor grade, and a node standing
     alone between two groups (it belongs to neither and stays).                                  [9B]
 R10 Junctions. A thin side arriving at another part's wall (a stem side at a corner, a START blunt, any
     blunt <= 25 u, a flag edge) slides along that wall to where its moved edge meets it, capped at 1.6 x
     its share (spec rule 15) and 3/4 of the wall segment; along a held flag edge only by the edge's far end (round 8); a blunt
     travels with it as one piece.
     When the core of a group is such a junction, the group's other nodes move WITH it, by their grade x
     the junction's own slide.                                                                    [8B]
 R11 Terminals. Where a group runs into a cut face (a thin one: a face wider than 0.75 stem is a stem's foot
     and anchors the walk instead), the end slides along the face line (the stroke never
     lengthens, spec rule 9); a short blunt (<= 25 u and under half the stroke's width there: a face as wide
     as the stroke is its end face itself) before a straight end face moves as one piece along that face. A face running with the move keeps up with the group (|v| / cos); a face across the move
     moves to where the moved edge meets it.                                                      [5A, 6B]
 R12 A thin cut face (< 0.75 stem weight) no group reaches opens along itself by its own share (spec
     rule 9). A counter tip pushed both ways takes the sum of the pushes.
 R13 Every segment keeps at least 1/4 (straight) or 1/2 (curve) of its chord along its drawn direction: the
     ends that slide (slides, junctions, blunts, terminals, cut faces, tips) give back proportionally;
     group nodes never do.

Curves
 R14 A segment whose two ends moved by the same vector translates. A CONNECTING segment (ends moved
     differently) is the drawn curve turned and scaled as one piece onto its new chord (a similarity:
     both handles go with it).                                                                    [4C]
 R15 Smooth nodes stay smooth: a straight edge wins (spec rule 12); else the handle on the untransformed
     side is rotated onto the transformed side's tangent, keeping its length; a node between two
     transformed segments keeps its drawn tangent. Every re-alignment is listed in the report.    [4C]
 R16 The axis: every node and handle moves linearly from drawn (CNTR 0) to moved (CNTR 100); node count,
     order and handle count never change.                                                         [10D]

Other typefaces (2026-10-23, Marya / Geist Serif; the detectors are stated in rungs.py / parts.py)
 R17 Balls. A ball / teardrop terminal never grows: its nodes move as one piece by the stroke end's own
     move taken along the stroke (like R11's end faces); a group's walk stops at it.
 R18 Slab serifs are flags (R1: never move); the stroke's side runs on under the bracket to the slab, and
     the bracket's root node slides along the held bracket like any side along a held serif edge (R10; round 8: up
     to the edge's far end). (Tried: the root moving with the stroke and the bracket reshaping -- on
     Geist's 15 u deep brackets under a 25 u move the bracket folds: snaps at E 21/24/26/29, T 16/19/28/31.)
 R19 Buried walls (an edge whose outside is another contour's ink) are no surfaces: never paired, never
     measured, never moved by a group.

Round 5 (2026-10-23: Harvey T bar/beak fold, Marya e bars, Marya italic y crotch rung)
 R3b A straight edge is one piece. When a thin part's side runs on along ONE straight segment past its last
     rung to a node, and that node's only other readings are END rungs of other GROWING strokes landing on the
     thin part (>= 1.5 x thicker than the part: a bowl or terminal curve meeting a bar), the node reads the
     junction, not a width: it joins the thin part (takes its share and direction) and moves with it as a plain
     group node. A cut face's node is a terminal, never this. (Marya roman e 21, Harvey e 22: the crossbar's
     lower edge stays parallel instead of growing as a wedge.)
 R20 Buried STARTs. A growing side that runs on into another part's ink and comes back to that part's edge by a
     hairpin (side edge and hairpin leave the node within 60 deg of each other, the hairpin's far node lies on a
     straight edge of another part, the side's edge CROSSES that edge in the drawing, and the node is buried:
     ink on every side of it) is the side's START, whatever its length or how the parts table read it (notch,
     blunt, cut, side). The junction and the hairpin's far node travel as ONE piece along that host edge, by the
     slide that puts the side on its moved line -- also when the host is a held flag edge (the far node stays
     on the flag's drawn line; round 8: up to the edge's far end, no 60% / 1.6 x cap). The fold
     under the host keeps its drawn shape instead of stretching from one end. A host that grows itself (its far
     node is a thin core of its own part) is left to its own group. (Harvey T 9-10 / 11-12 under the beaks,
     italic E 4-5 and 6-7 under the stem: before, only the junction slid -- 59.6 u on the Black T -- and the
     drawn 5 u sliver opened into a 12 u thick triangle.)
 R21 A thin END part with no node of its own: a stroke's end part that runs from a junction node to its end
     face as ONE curve, the junction reading >= 2 x both its neighbours on the side (it reads the thicker part
     it leaves). Its end face is not a terminal of the group beyond the junction; it opens by its own share
     (R12). The part grows through its handles: each handle of the junction -> end curve whose foot (nearest
     point on the side) reads under 0.9 x the junction moves by the side's own growth there, along the stroke
     normal; the junction node stays with its own part. (Marya italic e 27-30 / 2-31 and the Harvey italic e
     bars: before, the bar's end followed the eye's group DOWN and the bar barely grew.)

Round 6 (2026-10-24: the T's serif darts; the Geist c / g / o bowls. R22 "counters fit" was REVERTED in round 7: the
e's corner it moved was hiding the R24 fault below)
 R23 A group never makes a rung of its own part shorter than drawn. A walk stops at a node the vector would push
     toward its partner (round a bowl that turns more than ~90 deg); and among the snap directions, one that shortens any rung of the part (read on the turned / scaled
     segments, the far side growing by its own share) by more than 15% of the move (at least 1.5 u) pays for it. (Geist c: one vector moved
     the whole inner side and the bottom got 12 u thinner.)
 R8b A held flag's nodes never move for a growing part beneath it: where a bar runs under a held wedge / beak, only
     the bar's own end node slides (round 8: up to the edge's far end); the serif's node stays even if that leaves
     a dart or overlap inside the serif -- crosscheck reports a fold inside a held serif as "info", not a cross
     (Mark: it "will not affect the final build"). A START under a part that is not held keeps R20.
     (Round 7: on a STRAIGHT side, R24 replaces this -- the START sliver travels with its end node along the held edge.)
 (parts.py) A ring (a closed counter) paired with another side opens at its node nearest that side's first point
     when its own first node faces it across the counter (Geist o and g: the counter read top against bottom).

Round 7 (2026-10-24: Mark, "not moving laterally the correct amount for BOTH parts of the stem" -- the Geist z / x
diagonals and bars rotated, the Harvey e bar top rose 5 u at one end and 22 u at the other)
 R24 A straight side moves as ONE rigid lateral translation (spec rule 18). A straight side is a run of consecutive
     segments whose nodes and handles lie within 3 u of one line, all running the same way, at least 50 u long, that a
     growing part's side runs along and its rungs measure (a run of a serif's own edges is never part of one; a straight
     serif edge holds as a whole). The whole side translates across itself by ONE amount, the same at both ends:
     its share A/2 x (1 - own hold + partner hold) with the holds decided for the side as a whole (their mean over
     its rungs, or the stricter end -- the largest -- when the side touches a metric line or a flag at all); a thick
     straight side (no core node on it, wider than the core rule allows) holds, groups slide along it (R7). Each end
     follows the translated line: two straight sides meeting at a corner meet where both translated lines cross; an end
     at a held serif / flag / beak / bracket edge goes to where the translated line meets that edge (the serif's own
     nodes do not move, its edge gets shorter or longer; a START sliver drawn under it travels with the end node as
     one piece); an end at another part's wall slides along that wall; an end at a cut face slides along the face; an
     end where the side runs on (its own curve, or a tangent) moves straight across. When an end cannot reach the
     translated line within its cap the WHOLE side takes the smaller amount, and a group
     holding a node of that side takes the same reduction (it is one piece with the side). What is left of a curved
     held edge keeps its drawn shape (the curve cut at the slid node; a tangent bracket keeps both end directions).
     Curved sides keep R4-R23.
     CAP (round 8, Mark: "relax the serif slide cap so the bar reaches its full amount; the serif edge may shorten more"):
     along a held serif / flag / beak / bracket edge the end goes wherever the translated line meets that edge -- no 60%,
     no 1.6 x -- and the only limit is the edge's far end (the serif's tip or its next node), never passed (stopping
     min(2 u, 1/4 edge) short of it): "capped at serif tip" in the report. Another part's wall keeps 3/4 of the wall and
     1.6 x the share ("capped by wall"). A short spur (<= 25 u) at a cut end that the translated line cannot slide along
     travels with the end as one piece.
     OPTION, off (RULES["bracket_rides"]): when a tangent bracket's far node flows (within 10 deg) into a straight held
     serif edge, the bracket rides along that edge as one rigid piece -- its far node slides along the serif's drawn line,
     the bracket keeps its exact shape and the bar reaches its full amount. It moves a serif node, so R8b forbids it.
 R25 (REPLACED in round 8 by the scoped R22 below; RULES["R25"] switches it back on for comparison) A counter's corner stays. The corner node where a counter's curved side arrives at a growing bar -- through a short
     spur (<= 50 u) up to the bar's straight side, or at the end face of a node-less bar (R21) -- never moves; the
     spur is a connecting segment. (Mark's node-18 request was about the MARYA roman e, misread from a sheet.)

Round 8 (2026-10-24: the serif slide cap; Geist n / m outer shoulder; the Marya roman e corner)
 R22 (restored, scoped) A counter's ROUND corner rides with the bar. Where a growing straight side (R24) flows without a
     corner (smooth / tangent end node) into a drawn ROUND -- one curve turning 60-120 deg, its chord at most half the
     side, its radius (chord / sqrt 2) at least the side's own width, its far node smooth and running on into the
     counter's wall at 50-130 deg to the side -- and the round bounds a COUNTER, the round moves as ONE rigid piece with
     the side, along the bisector of side and wall, by the side's amount / cos(bisector to the side's normal), so its
     drawn clearance is kept; the wall beyond keeps both drawn end directions, stretched onto its new chord. A sharp end
     with a hairpin spur is not a round (it rides with the side, R24); a hook's open cup is never a counter.
     (Fires on the Marya roman e 18/15 only; the Harvey e's 18 is a spur -> R24 alone.)
 R26 A growing part's END at a stem. Where a growing part ends against a part that never grows (R1: a stem, a
     stem-weight straight leg), its end rung reads across the stem: a node of that rung on one of the stem's straight
     sides is the stem's, never a core. The stem's sides hold (never translate); the part's group reaches that node only
     by sliding it along the stem's side (R7). (Geist n / m: the arch's end rung at the right leg read 85 u, within
     1.25 x the 73 u arch, so the leg's outer side at the shoulder moved 12.7 u right.)
"""
import math, cmath
import numpy as np
from .mover import Mover
from .rungs import unit

SIN_TOL = math.sin(math.radians(25.0))
SNAP_MAX = 35.0          # degrees: a snap further than this from the mean normal is not considered
SNAP_MAX_EDGE = 45.0     # a straight edge next to the run may be followed this far off (a cup rising along a stem)
MAX_EXT = 8
CORE_RATIO = 1.25
LOCALMIN = 0.8
THIN_OF_STEM = 0.8       # a node this much thinner than the master's stem is a core wherever it is
CARRY_RATIO = 2.0        # a node the vector runs along is carried in full only up to this x the core width
GRADE = ((1.25, 1.0), (2.2, 2 / 3), (3.0, 1 / 3))
BLUNT = 25.0
BAR_OF_JUNCTION = 0.9    # R21: a handle whose foot reads under 0.9 x the junction lies on the bar
JUNCTION_PEAK = 2.0      # R3c: a node reading >= 2 x both side neighbours next to the stroke's end is a junction reading
THIN_TOL = 1.5           # R23: a candidate vector that shortens a rung of its own part by more than this (u) ...
THIN_REL = 0.15          # ... and by more than this x the move pays for it
AGAINST_TOL = 1.0        # R23: a group member may shorten its own rung by at most this (u)
STRAIGHT_TOL = 3.0       # R24: nodes and handles within this of one line make a straight side ...
STRAIGHT_MIN = 2 * BLUNT # ... at least this long (shorter: blunts, hairpins, end faces)
RULES = {}               # rule switches for before/after comparisons only (all rules on by default)
TIP_GAP = 2.0            # R24 (round 8): an end sliding along a held serif edge stops this short of the edge's far end


def dot(a, b): return a[0] * b[0] + a[1] * b[1]
def cross(a, b): return a[0] * b[1] - a[1] * b[0]
def add(a, b): return (a[0] + b[0], a[1] + b[1])
def sub(a, b): return (a[0] - b[0], a[1] - b[1])
def mul(a, k): return (a[0] * k, a[1] * k)
def norm(a): return math.hypot(a[0], a[1])


def grade(r):
    for lim, lv in GRADE:
        if r <= lim:
            return lv
    return 0.0


class GroupMover:
    def __init__(self, g, mover=None, masters=None, slant=None):
        """masters/slant: as Mover (a master_info dict, or g["_mi"] from move.load_set); none = Harvey as before"""
        self.g = g
        self.tip_capped = []          # round 8: ends that would pass a held serif edge's far end (report)
        self.M = M = mover if mover is not None else Mover(g, slant=slant, masters=masters)
        self.P, self.ol, self.A, self.slant = M.P, M.ol, M.A, M.slant
        it = math.radians(self.slant)
        self.italic = (math.sin(it), math.cos(it))
        self._index()
        self._proposals()
        self._classify()
        self._groups()
        self._moves()
        self._handles()

    # ---- contour structure ---------------------------------------------------------------------------
    def _index(self):
        self.contours = []
        self.seg_after, self.seg_before = {}, {}
        self.xy, self.smooth = {}, {}
        base = 0
        for ci, c in enumerate(self.g["contours"]):
            nodes = c["nodes"]; N = len(nodes)
            for i, n in enumerate(nodes):
                self.xy[base + i] = (float(n[0]), float(n[1]))
                self.smooth[base + i] = bool(n[3]) if len(n) > 3 else False
            ons = [i for i in range(N) if nodes[i][2] != "o"]
            segs = []
            for a, i in enumerate(ons):
                j = ons[(a + 1) % len(ons)]
                offs = [base + (k % N) for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
                kind = "curve" if (len(offs) == 2 and nodes[j][2] != "l") else "line"
                sg = dict(gi=base + i, gj=base + j, offs=offs, kind=kind, ci=ci)
                segs.append(sg)
                self.seg_after[base + i] = sg; self.seg_before[base + j] = sg
            self.contours.append(dict(base=base, N=N, ons=[base + i for i in ons], segs=segs))
            base += N
        self.contour_of = {nd: ci for ci, C in enumerate(self.contours) for nd in C["ons"]}

    def seg_dir_at(self, sg, nd, pts=None):
        """unit tangent of segment sg at its end node nd, pointing AWAY from nd into the segment"""
        xy = pts or self.xy
        P0, P3 = xy[sg["gi"]], xy[sg["gj"]]
        if sg["kind"] == "line" or not sg["offs"]:
            d = sub(P3, P0) if nd == sg["gi"] else sub(P0, P3)
        else:
            P1, P2 = xy[sg["offs"][0]], xy[sg["offs"][1]]
            if nd == sg["gi"]:
                d = sub(P1, P0) if norm(sub(P1, P0)) > 1e-6 else sub(P2, P0)
            else:
                d = sub(P2, P3) if norm(sub(P2, P3)) > 1e-6 else sub(P1, P3)
        return unit(d)

    def outline_normal(self, nd):
        a = self.seg_dir_at(self.seg_before[nd], nd); b = self.seg_dir_at(self.seg_after[nd], nd)
        t = unit(sub(b, a)) if norm(sub(b, a)) > 1e-6 else unit((-a[1], a[0]))
        return (-t[1], t[0])

    def line_dir(self, sg):
        return unit(sub(self.xy[sg["gj"]], self.xy[sg["gi"]]))

    # ---- 1. proposals (7C: full growth) ----------------------------------------------------------------
    def _proposals(self):
        M = self.M
        kinds = getattr(M, "stroke_kind", None) or [(False, False)] * len(M.stroke_rows)
        self.props = {}           # node -> list of dict(a, dir, st, th, hid, core)
        self.inspan = {}
        self.stroke_max = {}
        self.stroke_grows = {}
        self.side_rows = {}
        self.stroke_tmin = {}
        self.bars = []            # R21: thin end parts with no node of their own
        for si, ((st, rows), (is_stem, is_dot)) in enumerate(zip(M.stroke_rows, kinds)):
            SA, SB = st["A"], st["B"]
            nrm = []
            for row in rows:
                sa, sb = row["r"][0], row["r"][1]
                ta, tb = SA.tan(sa), SB.tan(sb)
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
            vis_th = [row["th"] for row in rows if not row.get("hid") and row["th"] >= 5.0]
            stem_weight = bool(vis_th) and min(vis_th) >= 0.75 * self.M.thick_bot / 0.95
            grows = not (is_stem or is_dot or stem_weight)
            self.stroke_grows[si] = grows
            mx = 0.0
            stroke_sides = []
            for S, key, sgn, own, oth in ((SA, 0, -1.0, "hA", "hB"), (SB, 1, 1.0, "hB", "hA")):
                pos = [row["r"][key] for row in rows]
                order = np.argsort(pos)
                pos = [pos[k] for k in order]
                gs = [(self.A / 2 * min(2.0, max(0.0, 1.0 - rows[k][own] + rows[k][oth])) if grows else 0.0) for k in order]
                ns = [nrm[k] for k in order]
                ths = [rows[k]["th"] for k in order]
                hids = [bool(rows[k].get("hid")) for k in order]
                lo, hi = pos[0], pos[-1]
                self.side_rows[(si, key)] = dict(S=S, pos=np.array(pos), gs=np.array(gs), ns=ns, ths=np.array(ths), sgn=sgn,
                                                 hown=np.array([float(rows[k][own]) for k in order]),
                                                 hoth=np.array([float(rows[k][oth]) for k in order]), hid=np.array(hids))
                side_nodes = []
                for idx, nd in S.nodes:
                    if nd is None:
                        continue
                    s = S.al[idx]
                    if s < lo - 6.0 or s > hi + 6.0:
                        # R3b: the side runs on along ONE straight segment past its last rung to a node (a bar's
                        # bottom edge running on to the corner where it meets the bowl's outer side): a straight
                        # edge is one piece, so that node can carry this part's reading (used only when its other
                        # readings are junction readings, see _classify)
                        e_ = 0 if s < lo else -1
                        ip = int(np.clip(np.searchsorted(S.al, pos[e_]), 0, len(S.src) - 1))
                        kk = S.src[ip][0]
                        if grows and kk != "hidden" and self.ol.segs[kk].kind == "line" and nd in (self.ol.segs[kk].gi, self.ol.segs[kk].gj) \
                                and not hids[e_] and ths[e_] >= 5.0:
                            p = dict(a=float(gs[e_]), dir=mul(ns[e_], sgn), st=si, side=S, th=float(ths[e_]), hid=False, core=False,
                                     nd=nd, ext=True, end=False)
                            self.props.setdefault(nd, []).append(p)
                            side_nodes.append(p)
                        continue
                    k = int(np.searchsorted(pos, s))
                    if k <= 0: a, n_, th, hid = gs[0], ns[0], ths[0], hids[0]
                    elif k >= len(pos): a, n_, th, hid = gs[-1], ns[-1], ths[-1], hids[-1]
                    else:
                        s0, s1 = pos[k - 1], pos[k]
                        u = 0.0 if s1 == s0 else (s - s0) / (s1 - s0)
                        a = gs[k - 1] + (gs[k] - gs[k - 1]) * u
                        th = ths[k - 1] + (ths[k] - ths[k - 1]) * u
                        hid = hids[k - 1] if u < 0.5 else hids[k]
                        n_ = unit(add(mul(ns[k - 1], 1 - u), mul(ns[k], u)))
                    if th < 5.0:
                        a = 0.0                    # a side closing to a point (the stroke's own tip) has no width to grow
                    p = dict(a=float(a), dir=mul(n_, sgn), st=si, side=S, th=float(th), hid=hid, core=False, nd=nd,
                             ext=False, end=(s <= lo + 6.0 or s >= hi - 6.0))
                    self.props.setdefault(nd, []).append(p)
                    self.inspan.setdefault(nd, set()).add(si)
                    side_nodes.append(p)
                    mx = max(mx, float(a))
                stroke_sides.append(side_nodes)
            # cores: the thinnest nodes of the stroke, and clear local minima of width along a side
            # (end rungs that close to a point, th < 5, are not widths)
            allvis = [p for sn in stroke_sides for p in sn if not p["hid"] and p["th"] >= 5.0]
            tmin = min(p["th"] for p in allvis) if allvis else 0.0
            self.stroke_tmin[si] = tmin
            for side_nodes in (stroke_sides if grows and allvis else []):
                vis = [p for p in side_nodes if not p["hid"] and p["th"] >= 5.0]
                for i, p in enumerate(vis):
                    if p["a"] < 1.0:
                        continue
                    nb = [vis[j]["th"] for j in (i - 1, i + 1) if 0 <= j < len(vis)]
                    localmin = bool(nb) and all(p["th"] <= x for x in nb) and p["th"] <= LOCALMIN * max(nb)
                    if p["th"] <= CORE_RATIO * tmin or localmin or p["th"] <= THIN_OF_STEM * self.M.thick_bot:
                        p["core"] = True
            # R21: a thin END part with no node of its own (a bar running from the junction to its end face as ONE
            # curve): the junction node reads the thicker part (>= 2 x both its neighbours on the side), the end node
            # is the end face. Recorded here; the part grows through its handles (_handles) and its end face opens
            # by its own share (R12) instead of following the group beyond the junction.
            for key_, side_nodes in zip((0, 1), stroke_sides if grows and allvis else []):
                side_nodes = [q for q in side_nodes if not q.get("ext")]
                for i, p in enumerate(side_nodes):
                    if p["core"] or p["hid"]:
                        continue
                    for e_, n_ in ((0, -1), (len(side_nodes) - 1, 1)):
                        if i + n_ != e_ or not (0 <= i - n_ < len(side_nodes)):
                            continue
                        end, other = side_nodes[e_], side_nodes[i - n_]
                        if end["a"] < 1.0 or end["th"] < 5.0:
                            continue
                        if p["th"] >= JUNCTION_PEAK * end["th"] and p["th"] >= JUNCTION_PEAK * other["th"]:
                            self.bars.append(dict(st=si, key=key_, junction=p["nd"], end=end["nd"], th_end=end["th"], th_junction=p["th"]))
            self.stroke_max[si] = mx
        self._stem_end_rungs()

    def _stem_end_rungs(self):
        """R26 A growing part's END at a stem. Where a growing part ends against a part that never grows (R1: a stem,
        a stem-weight straight leg), its end rung reads across the stem: a node of that rung lying on one of the
        stem's straight sides is the stem's, never a core. The stem's sides hold (they never translate); the part's
        group reaches that node only by sliding it along the stem's side (R7)."""
        self.stem_end_nodes = set()
        if not RULES.get("R26", True):
            return
        seg_k = {(sg.gi, sg.gj): k for k, sg in enumerate(self.ol.segs)}
        fixed = set()
        for si, (st, _) in enumerate(self.M.stroke_rows):
            if not self.stroke_grows.get(si):
                fixed |= self.M._stroke_walls(st)
        if not fixed:
            return
        for si, (st, _) in enumerate(self.M.stroke_rows):
            if not self.stroke_grows.get(si):
                continue
            own = self.M._stroke_walls(st)
            for nd, ps in self.props.items():
                for p in ps:
                    if p["st"] != si or not p["core"] or not p["end"]:
                        continue
                    for sg in (self.seg_before.get(nd), self.seg_after.get(nd)):
                        k = seg_k.get((sg["gi"], sg["gj"])) if sg is not None else None
                        if k is not None and sg["kind"] == "line" and self.ol.segs[k].wall in fixed and self.ol.segs[k].wall not in own:
                            p["core"] = False; self.stem_end_nodes.add(nd)
                            break

    # ---- 2. node classes -------------------------------------------------------------------------------
    def _classify(self):
        M, P, ol = self.M, self.P, self.ol
        self.held = set(M.held_nodes())
        self.ball_nodes = {nd for b in getattr(ol, "balls", []) for nd in b["nodes"]}
        self.slab_roots = {sf["root"] for sf in ol.serifs if sf.get("root") is not None}
        self.share, self.pinch, self.th, self.corep = {}, {}, {}, {}
        bars = []
        for b in self.bars:
            j_, e_ = b["junction"], b["end"]
            sg = next((x for x in (self.seg_after.get(j_), self.seg_before.get(j_)) if x is not None and {x["gi"], x["gj"]} == {j_, e_}), None)
            if sg is not None and sg["kind"] == "curve" and e_ not in self.held and j_ not in self.held:
                b["seg"] = sg; bars.append(b)
        self.bars = bars
        self.bar_ends = {b["end"]: b for b in bars}
        self.joined = set()
        cut_nodes = {nd for wi, k in P.kind.items() if k == "cut" for kk in ol.walls[wi] for nd in (ol.segs[kk].gi, ol.segs[kk].gj)}
        for nd in list(self.props):
            ps = self.props[nd]
            ext = [p for p in ps if p.get("ext")]
            if ext:
                own = [p for p in ps if not p.get("ext")]
                if own and nd not in cut_nodes and any(q["core"] for q in ext) and \
                        all(p["end"] and self.stroke_grows.get(p["st"]) and p["th"] >= 1.5 * min(q["th"] for q in ext) for p in own):
                    # R3b: every other reading of this node is the END rung of another GROWING stroke (a bowl, a
                    # terminal curve) landing on the thin part, >= 1.5 x thicker than the part: a junction reading,
                    # not a width -- the node joins the thin part (a cut face's node is a terminal, never this)
                    self.props[nd] = [q for q in ext if q["core"]]
                    self.joined.add(nd)
                else:
                    self.props[nd] = own
                    if not own:
                        del self.props[nd]; continue
            ps = self.props[nd]
            big = [p for p in ps if p["a"] > 1.0]
            opp = any(dot(p["dir"], q["dir"]) < 0 for i, p in enumerate(big) for q in big[i + 1:])
            best = max(ps, key=lambda p: (p["core"], p["a"]))
            if opp:
                v = (0.0, 0.0)
                for p in big: v = add(v, mul(p["dir"], p["a"]))
                self.pinch[nd] = v
                self.share[nd] = (norm(v), unit(v) if norm(v) > 1e-9 else best["dir"], best["st"])
            else:
                self.share[nd] = (best["a"], best["dir"], best["st"])
            self.th[nd] = best["th"]
            self.corep[nd] = best["core"]
        # cut faces (rule 9)
        self.cut_face = {}        # node -> list of (seg dict, other node)
        for wi, k in P.kind.items():
            if k != "cut":
                continue
            for kk in ol.walls[wi]:
                s0 = ol.segs[kk]
                sg = self.seg_after.get(s0.gi)
                if sg is None or sg["gj"] != s0.gj:
                    continue
                self.cut_face.setdefault(s0.gi, []).append((sg, s0.gj)); self.cut_face.setdefault(s0.gj, []).append((sg, s0.gi))
        # junctions: a moving side arriving at another part's wall
        self.junction = {}
        strokes = [st for st, _ in M.stroke_rows]
        for nd, (a, d, si) in self.share.items():
            if a <= 1.0 or nd in self.held or nd in self.cut_face or nd in self.pinch or not self.corep.get(nd):
                continue                           # only a THIN side arriving at a wall is a junction (R10)
            if nd in self.joined:
                continue                           # R3b: the corner a straight thin side runs on to moves with that side
            host = M._host_wall(nd, strokes[si])
            if host is None:
                continue
            sg, kind = host
            if kind == "cut":
                continue
            if kind == "side" and self.smooth.get(nd):
                continue
            if kind == "side" and self._tangent_through(nd):
                continue                           # drawn tangent-continuous (flag unset): the side runs on, no wall
            partner = None
            hseg = sg
            chain = False
            if kind == "notch" or (kind == "side" and sg.length <= BLUNT):
                # a START blunt, or any short blunt between two parts: it travels as one piece with the
                # junction, along the wall beyond it
                kind = "notch" if kind == "notch" else "blunt"
                partner = sg.gj if sg.gi == nd else sg.gi
                nxt = [s2 for s2 in ol.segs if partner in (s2.gi, s2.gj) and s2 is not sg]
                if nxt:
                    hseg = nxt[0]
                    chain = hseg.length <= BLUNT and P.kind.get(hseg.wall) in ("notch", "cut")
            far = hseg.gj if hseg.gi in (nd, partner) else hseg.gi
            near = hseg.gi if far == hseg.gj else hseg.gj
            t = unit(sub(self.xy[far], self.xy[near]))
            self.junction[nd] = dict(kind=kind, t=t, partner=partner, hseg=hseg, flaglen=sg.length, chain=chain)
        self._buried_starts()
        self.partners = {J["partner"] for J in self.junction.values() if J["partner"] is not None}

    def _seg_poly(self, sg, n=16):
        P0, P3 = self.xy[sg["gi"]], self.xy[sg["gj"]]
        if sg["kind"] != "curve":
            return [P0, P3]
        P1, P2 = self.xy[sg["offs"][0]], self.xy[sg["offs"][1]]
        out = []
        for k in range(n + 1):
            t = k / n; u = 1 - t
            out.append((u ** 3 * P0[0] + 3 * u * u * t * P1[0] + 3 * u * t * t * P2[0] + t ** 3 * P3[0],
                        u ** 3 * P0[1] + 3 * u * u * t * P1[1] + 3 * u * t * t * P2[1] + t ** 3 * P3[1]))
        return out

    def _crosses(self, sa, sb):
        """the two segments cross properly (not merely touch at an end)"""
        A, B = self._seg_poly(sa), self._seg_poly(sb)
        for p, p2 in zip(A, A[1:]):
            r = sub(p2, p)
            for q, q2 in zip(B, B[1:]):
                s_ = sub(q2, q); den = cross(r, s_)
                if abs(den) < 1e-12:
                    continue
                qp = sub(q, p)
                t = cross(qp, s_) / den; u = cross(qp, r) / den
                if 1e-6 < t < 1 - 1e-6 and 1e-6 < u < 1 - 1e-6:
                    return True
        return False

    def _winding(self, pt):
        """nonzero winding number of the drawn outline at pt"""
        if not hasattr(self, "_polys"):
            self._polys = []
            for C in self.contours:
                P = []
                for sg in C["segs"]:
                    P.extend(self._seg_poly(sg)[:-1])
                self._polys.append(P)
        w = 0
        x, y = pt
        for P in self._polys:
            for (ax, ay), (bx, by) in zip(P, P[1:] + P[:1]):
                if (ay <= y) != (by <= y):
                    xc = ax + (y - ay) * (bx - ax) / (by - ay)
                    if xc > x:
                        w += 1 if by > ay else -1
        return w

    def _buried(self, nd, r=3.0):
        """the node lies inside ink on every side (hidden under another part)"""
        x, y = self.xy[nd]
        return all(self._winding((x + r * math.cos(k * math.pi / 4), y + r * math.sin(k * math.pi / 4))) != 0 for k in range(8))

    def _buried_starts(self):
        """R20 Buried STARTs. A growing side that runs on into another part's ink and comes back to that part's
        edge by a hairpin (the side's edge and the hairpin leave the node within 60 deg of each other, the hairpin's
        far node lies on a straight edge of another part, the side's edge CROSSES that edge in the drawing, and the
        junction node is buried: ink on every side of it)
        is the side's START, whatever its length or how the parts table reads it (notch, blunt, cut face, side).
        The junction and the hairpin's far node travel as ONE piece along that host edge, by the slide that puts
        the side on its moved line, even when the host is a held flag edge (the far node stays on the flag's drawn
        line): the fold under the host keeps its drawn shape instead of stretching from one end. A host that grows
        itself (its far node is a core of its own group) is left to its group."""
        ol = self.ol
        strokes = [st for st, _ in self.M.stroke_rows]
        by_ends = {(sg.gi, sg.gj): sg for sg in ol.segs}
        self.starts = {}
        for nd, (a, d, si) in sorted(self.share.items()):
            if a <= 1.0 or nd in self.held or nd in self.pinch or nd in self.ball_nodes:
                continue
            own_walls = self.M._stroke_walls(strokes[si])
            for hp in (self.seg_before[nd], self.seg_after[nd]):
                if hp["kind"] != "line":
                    continue
                f = hp["gi"] if hp["gj"] == nd else hp["gj"]
                own = self.seg_after[nd] if hp is self.seg_before[nd] else self.seg_before[nd]
                e = self.seg_before[f] if self.seg_after[f] is hp else self.seg_after[f]
                if e["kind"] != "line" or e is own:
                    continue
                E = by_ends.get((e["gi"], e["gj"]))
                if E is None or E.wall in own_walls or self.P.kind.get(E.wall) == "buried":
                    continue
                if dot(self.seg_dir_at(own, nd), self.seg_dir_at(hp, nd)) < math.cos(math.radians(60.0)):
                    continue
                if not self._crosses(own, e) or not self._buried(nd):
                    continue
                if f not in self.held and self.corep.get(f) and self.share.get(f, (0.0,))[0] >= 1.0:
                    continue                  # the host itself grows (a bar under an eye): its own group moves f
                far = e["gj"] if e["gi"] == f else e["gi"]
                t = unit(sub(self.xy[far], self.xy[f]))
                Hp = by_ends.get((hp["gi"], hp["gj"]))
                self.junction[nd] = dict(kind="start", t=t, partner=f, hseg=E, flaglen=E.length, chain=False,
                                         flag=self.P.kind.get(E.wall) == "flag" or f in self.held, hairpin=Hp)
                self.starts[nd] = (f, (e["gi"], e["gj"]))
                for n_ in (nd, f):
                    if n_ in self.cut_face:
                        self.cut_face[n_] = [(sg, o) for sg, o in self.cut_face[n_] if sg is not hp]
                        if not self.cut_face[n_]:
                            del self.cut_face[n_]
                break

    def _tangent_through(self, nd):
        """the outline passes node nd without turning (tangents within 3 deg), whatever its smooth flag says"""
        a = self.seg_dir_at(self.seg_before[nd], nd); b = self.seg_dir_at(self.seg_after[nd], nd)
        return -(a[0] * b[0] + a[1] * b[1]) >= math.cos(math.radians(3.0))

    def is_core(self, nd):
        if nd not in self.share or nd in self.held or nd in self.cut_face or nd in self.pinch or nd in self.ball_nodes:
            return False
        return self.corep.get(nd, False) and self.share[nd][0] >= 1.0

    # ---- 3. groups ---------------------------------------------------------------------------------------
    def _groups(self):
        self.groups, self.claimed = [], {}
        runs = []
        for ci, C in enumerate(self.contours):
            ons = C["ons"]; K = len(ons)
            core = [self.is_core(nd) for nd in ons]
            if not any(core):
                continue
            if all(core):
                runs.append((ci, list(range(K)))); continue
            start = next(i for i in range(K) if not core[i])
            cur = []
            for step in range(1, K + 1):
                p = (start + step) % K
                if core[p]:
                    cur.append(p)
                elif cur:
                    runs.append((ci, cur)); cur = []
            if cur:
                runs.append((ci, cur))
        # a run never spans both sides of a stroke: split it where the shares turn against each other
        split = []
        for ci, run in runs:
            ons = self.contours[ci]["ons"]
            cur = [run[0]]
            for p in run[1:]:
                if dot(self.share[ons[cur[-1]]][1], self.share[ons[p]][1]) < 0.0:
                    split.append((ci, cur)); cur = [p]
                else:
                    cur.append(p)
            split.append((ci, cur))
        runs = split
        self.core_nodes = {self.contours[ci]["ons"][p] for ci, run in runs for p in run}
        runs.sort(key=lambda r: -max(self.share[self.contours[r[0]]["ons"][p]][0] for p in r[1]))
        for ci, run in runs:
            C = self.contours[ci]
            nodes = [C["ons"][p] for p in run if C["ons"][p] not in self.claimed]
            if not nodes:
                continue
            g = self._best_group(ci, run, nodes)
            g["id"] = len(self.groups)
            self.groups.append(g)
            for nd in g["levels"]:
                self.claimed[nd] = g["id"]

    def _candidates(self, ci, run, mean):
        C = self.contours[ci]; ons = C["ons"]; K = len(ons)
        cands = [("x", (1.0, 0.0)), ("y", (0.0, 1.0))]
        if self.slant:
            cands.append(("italic", self.italic))
        edges = []
        for end, step in ((run[0], -1), (run[-1], +1)):
            p = end
            for _ in range(3):
                sg = self.seg_after[ons[p]] if step > 0 else self.seg_before[ons[p]]
                if sg["kind"] == "line":
                    edges.append(("edge %d-%d" % (sg["gi"], sg["gj"]), self.line_dir(sg)))
                    break
                p = (p + step) % K
        # straight edges at BOTH ends that disagree (a bar between two beaks, a T's arm) leaning to opposite sides of the
        # move (> 10 deg each): following either one would skew the whole run sideways -- the run keeps to the plain snaps and its ends slide (R7)
        if len(edges) == 2 and len(run) >= 2:
            e0 = edges[0][1] if dot(edges[0][1], mean) >= 0 else mul(edges[0][1], -1.0)
            e1 = edges[1][1] if dot(edges[1][1], mean) >= 0 else mul(edges[1][1], -1.0)
            c0, c1 = cross(mean, e0), cross(mean, e1)
            if c0 * c1 < 0 and min(abs(c0), abs(c1)) > math.sin(math.radians(10.0)) and \
                    abs(abs(c0) - abs(c1)) <= 0.25 * max(abs(c0), abs(c1)):
                edges = []                 # they lean to opposite sides of the move: mirror images
        cands += edges
        out = []
        for name, d in cands:
            for sgn in (1.0, -1.0):
                v = mul(d, sgn)
                ang = math.degrees(math.acos(max(-1.0, min(1.0, dot(v, mean)))))
                if ang <= (SNAP_MAX_EDGE if name.startswith("edge") else SNAP_MAX):
                    out.append((name, v, ang))
        if not out:
            out.append(("normal", mean, 0.0))
        return out

    def _against(self, j, w):
        """R23: moving node j by w would make its own part's rung shorter than drawn (w runs toward the partner)"""
        if j not in self.share:
            return False
        return dot(w, self.share[j][1]) < -AGAINST_TOL

    def _extend(self, ci, run, nodes, v, m, strokes, tcore):
        """walk outward from both ends of the run; returns members {node: (level, how)}, stops, cost"""
        C = self.contours[ci]; ons = C["ons"]; K = len(ons)
        nodeset = set(nodes)
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
                    stops.append((j, "between", lvl)); break          # a node alone between two groups stays
                if j in self.bar_ends:
                    stops.append((j, "bar-end", lvl)); break   # R21: the end of a node-less thin part opens by its own share
                if j in self.cut_face:
                    if all(norm(sub(self.xy[c2], self.xy[j])) > 0.75 * self.M.thick_bot / 0.95 for _, c2 in self.cut_face[j]):
                        stops.append((j, "hard", lvl)); break           # a stem-wide end (a foot) is no thin terminal: anchor
                    stops.append((j, "cut", lvl)); break               # terminal (6B), handled in _moves
                if j in self.ball_nodes:
                    stops.append((j, "ball", lvl)); break               # a ball terminal (R17), moved in _moves
                if j in self.held or j in self.pinch or j in self.junction or j in self.partners:
                    stops.append((j, "hard", lvl)); break
                if (self.inspan.get(j, set()) & strokes) and self.share.get(j, (0,))[0] < 1.0:
                    stops.append((j, "held", lvl)); break       # held by a metric line (rule 7)
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
                        stops.append((j, "line", lvl)); break       # the edge moves with its own junction
                    if c <= SIN_TOL:                 # (a slide keeps the node on its drawn edge: R7, not R23)
                        chord = max(1.0, norm(sub(self.xy[j], self.xy[ons[p]])))
                        mem[j] = (lvl, "slide", dl); cost += lvl * m * c / chord
                        stops.append((nxt["gj"] if step > 0 else nxt["gi"], "slide-end", lvl))
                    else:
                        stops.append((j, "tol", lvl)); cost += 1.0
                    break
                if not (self.inspan.get(j, set()) & strokes):
                    stops.append((j, "outside", lvl)); break
                r = self.th.get(j, 999.0) / max(1.0, tcore)
                wl = grade(r)
                nj = self.share[j][1] if j in self.share else self.outline_normal(j)
                c = abs(dot(v, nj))
                if self.share.get(j, (0,))[0] < 1.0:
                    stops.append((j, "held", lvl)); break
                chord = norm(sub(self.xy[j], self.xy[ons[p]]))
                wl_ = lvl if (c <= SIN_TOL and (r <= CARRY_RATIO or chord < 2.0 * m * lvl)) else min(lvl, wl)
                if wl_ > 0 and self._against(j, mul(v, m * wl_)):
                    stops.append((j, "against", lvl)); cost += 1.0           # R23: a group never thins its own part
                    break
                if c <= SIN_TOL and (r <= CARRY_RATIO or chord < 2.0 * m * lvl):
                    mem[j] = (lvl, "carry", None); cost += lvl * m * c / max(20.0, self.th.get(j, 80.0))
                    p = q; continue
                if wl > 0 and self.share.get(j, (0,))[0] >= 1.0:
                    lvl = min(lvl, wl)
                    mem[j] = (lvl, "graded", None)
                    p = q; continue
                stops.append((j, "tol", lvl)); cost += 1.0
                break
        return mem, stops, cost

    def _row_ends(self):
        """R23: every visible rung of every growing stroke as (stroke, pa, pb, seg-key a, t a, seg-key b, t b)"""
        if hasattr(self, "_rows_cache"):
            return self._rows_cache
        out = []
        def end(S_, s_):
            i = int(np.clip(np.searchsorted(S_.al, s_), 0, len(S_.src) - 1))
            src = S_.src[i]
            if src[0] == "hidden":
                return None
            sg = self.ol.segs[src[0]]
            return (sg.gi, sg.gj), float(src[1])
        kinds = getattr(self.M, "stroke_kind", None) or [(False, False)] * len(self.M.stroke_rows)
        for si, ((st, rows), _) in enumerate(zip(self.M.stroke_rows, kinds)):
            if not self.stroke_grows.get(si):
                continue
            for row in rows:
                if row.get("hid") or row.get("root") or row["r"][2] == "end":
                    continue
                ea, eb = end(st["A"], row["r"][0]), end(st["B"], row["r"][1])
                if ea and eb:
                    d = row["d"]
                    ga = complex(-d[0] * row.get("gA", 0.0), -d[1] * row.get("gA", 0.0))   # each side's own planned growth
                    gb = complex(d[0] * row.get("gB", 0.0), d[1] * row.get("gB", 0.0))
                    out.append((si, row["pa"], row["pb"], ea[0], ea[1], eb[0], eb[1], ga, gb))
        self._rows_cache = out
        return out

    def _thin_cost(self, ci, levels, v, m, slides, strokes):
        """R23: how much a candidate vector makes the group's own part THINNER than drawn: the largest shortening
        (u) of a rung of the group's strokes whose end lies on a segment the group moves (a segment between two
        members translates, one from a member to a node that stays is turned and scaled onto its new chord, R14)"""
        w = {}
        for nd, l in levels.items():
            x = mul(v, m * l)
            if nd in slides:
                x = mul(slides[nd], dot(x, slides[nd]))
            w[nd] = x
        sims = {}
        for sg in self.contours[ci]["segs"]:
            a, b = sg["gi"], sg["gj"]
            if a not in w and b not in w:
                continue
            P0, P3 = complex(*self.xy[a]), complex(*self.xy[b])
            if abs(P3 - P0) < 1e-6:
                continue
            Q0 = P0 + complex(*w.get(a, (0.0, 0.0)))
            sims[(a, b)] = (P0, Q0, (P3 + complex(*w.get(b, (0.0, 0.0))) - Q0) / (P3 - P0))
        if not sims:
            return 0.0
        def disp(key, p, planned):
            if key not in sims:
                return planned                    # a side this group does not move grows by its own share
            P0, Q0, sim = sims[key]
            z = complex(*p)
            return Q0 + sim * (z - P0) - z
        worst = 0.0
        for si, pa, pb, ka, ta, kb, tb, ga, gb in self._row_ends():
            if si not in strokes or (ka not in sims and kb not in sims):
                continue
            za, zb = complex(*pa), complex(*pb)
            L0 = abs(zb - za)
            L1 = abs(zb + disp(kb, pb, gb) - za - disp(ka, pa, ga))
            worst = max(worst, L0 - L1)
        return worst

    def _best_group(self, ci, run, nodes):
        free = [nd for nd in nodes if nd not in self.junction]
        if not free:
            return self._junction_group(ci, run, nodes)
        acc = (0.0, 0.0)
        for nd in free:
            a, d, si = self.share[nd]
            acc = add(acc, mul(d, a))
        mean = unit(acc) if norm(acc) > 1e-9 else self.share[nodes[0]][1]
        strokes = {self.share[nd][2] for nd in nodes}
        tcore = min(self.th.get(nd, 999.0) for nd in nodes)
        best = None
        for name, v, ang in self._candidates(ci, run, mean):
            m = 0.0
            for nd in free:
                a, d, si = self.share[nd]
                m = max(m, a / max(0.5, dot(v, d)))
            mem, stops, cost = self._extend(ci, run, nodes, v, m, strokes, tcore)
            cost += 2.0 * (1.0 - math.cos(math.radians(ang)))
            lv = {nd: 1.0 for nd in nodes}; sl = {}
            for nd_, (l_, h_, dl_) in mem.items():
                lv[nd_] = l_
                if h_ == "slide":
                    sl[nd_] = dl_
            thin = self._thin_cost(ci, lv, v, m, sl, strokes)
            if thin > max(THIN_TOL, THIN_REL * m):
                cost += 4.0 * thin / max(m, 1.0)       # R23: a group never makes its own part thinner than drawn
            cand = dict(name=name, v=v, m=m, cost=cost, ang=ang, mem=mem, stops=stops, thin=thin)
            if best is None or cand["cost"] < best["cost"] - 1e-9:
                best = cand
        levels = {nd: 1.0 for nd in nodes}
        how = {nd: ("junction" if nd in self.junction else "core") for nd in nodes}
        slides = {}
        for nd, (l, h, dl) in best["mem"].items():
            levels[nd] = l; how[nd] = h
            if h == "slide":
                slides[nd] = dl
        return dict(ci=ci, core=list(nodes), ext=[n for n, h in how.items() if h == "carry"],
                    graded=[n for n, h in how.items() if h == "graded"], slides=slides, levels=levels, how=how,
                    dir=best["v"], dir_name=best["name"], mag=best["m"], cost=best["cost"], snap_deg=best["ang"],
                    mean=mean, anchors=[s[0] for s in best["stops"]], stops=best["stops"], strokes=sorted(strokes),
                    terminal=None)

    def _junction_group(self, ci, run, nodes):
        """8B: a group whose core is a junction (the v's crotch 14): the junction slides along its host
        wall (rules 10/15), and the graded neighbours move WITH it, by level x that same vector"""
        nd = nodes[0]
        a_, d, si = self.share[nd]
        w = self._junction_slide(nd, mul(d, a_), self.junction[nd])
        m = norm(w)
        v = unit(w) if m > 1e-6 else d
        tcore = min(self.th.get(n, 999.0) for n in nodes)
        mem, stops, cost = self._extend(ci, run, nodes, v, m, {self.share[n][2] for n in nodes}, tcore)
        levels = {n: 1.0 for n in nodes}; how = {n: "junction" for n in nodes}; slides = {}
        for n, (l, h, dl) in mem.items():
            levels[n] = l; how[n] = h
            if h == "slide":
                slides[n] = dl
        stops = [s for s in stops if s[1] != "cut"]          # no terminal: the side itself does not move as a group
        return dict(ci=ci, core=list(nodes), ext=[n for n, h in how.items() if h == "carry"],
                    graded=[n for n, h in how.items() if h == "graded"], slides=slides, levels=levels, how=how,
                    dir=v, dir_name="junction slide", mag=m, cost=cost, snap_deg=0.0, mean=d,
                    anchors=[s[0] for s in stops], stops=stops, strokes=[si], terminal=None)

    # ---- moves ---------------------------------------------------------------------------------------------
    def _partner_moves(self, J):
        """the far node of a junction's blunt / hairpin travels with it -- except a node of a held flag: R8b, a held
        flag's nodes never move for a growing part beneath it (Mark 2026-10-24: a dart or overlap inside the serif
        "will not affect the final build"); only the part's own end node slides (round 8: up to the edge's far end)"""
        return J["partner"] is not None and J["partner"] not in self.held

    def _junction_slide(self, nd, w, J):
        own = [sg for sg in (self.seg_before[nd], self.seg_after[nd])
               if J["partner"] not in (sg["gi"], sg["gj"]) and not (J["kind"] != "notch" and self._is_host(sg, J))]
        u = self.seg_dir_at(own[0], nd) if own else (-w[1], w[0])
        t = J["t"]
        cr = cross(t, u)
        s = cross(w, u) / cr if abs(cr) > 0.17 else dot(w, t)
        if (J["kind"] == "start" and J["flag"]) or J["kind"] == "flag":
            # round 8: along a held flag / serif edge the slide goes wherever the moved edge meets it; the only limit
            # is the edge's far end (the serif's tip / next corner), never passed
            L = J["hseg"].length if J["kind"] == "start" else J["flaglen"]
            cap = max(0.0, L - min(TIP_GAP, 0.25 * L))
            if abs(s) > cap and hasattr(self, "tip_capped"):
                self.tip_capped.append(dict(node=nd, kind="junction " + J["kind"], need=round(abs(s), 1), cap=round(cap, 1)))
        else:
            cap = min(1.6 * norm(w), 0.75 * J["hseg"].length)
        s = max(-cap, min(cap, s))
        return mul(t, s)

    def _terminal(self, g, c, lvl):
        """6B: the group's moved edge arrives at cut node c"""
        v = mul(g["dir"], g["mag"] * lvl)
        if norm(v) < 1e-6:
            return None
        C = self.contours[g["ci"]]; ons = C["ons"]
        # the segment arriving at c from the group side
        arr = None
        for sg in (self.seg_before[c], self.seg_after[c]):
            other = sg["gi"] if sg["gj"] == c else sg["gj"]
            if other in g["levels"]:
                arr = sg
        if arr is None:
            return None
        u = self.seg_dir_at(arr, c)
        nodes, line = [c], None
        for face, c2 in self.cut_face[c]:
            if face is arr:
                continue
            L = norm(sub(self.xy[c2], self.xy[c]))
            far = self.seg_after[c2] if self.seg_before[c2] is face else self.seg_before[c2]
            if L <= BLUNT and L < 0.5 * self.th.get(c, 999.0) and far["kind"] == "line" and c2 not in self.held:
                nodes = [c, c2]; line = self.line_dir(far)
            else:
                line = self.line_dir(face)
            break
        if line is None:
            return None
        vl = dot(v, line)
        if abs(vl) >= math.cos(math.radians(35.0)) * norm(v):
            s = norm(v) ** 2 / vl              # the face runs with the move: the terminal keeps up with the side
        else:
            cr = cross(line, u)                # the face runs across the move: to where the moved edge meets it
            s = cross(v, u) / cr if abs(cr) > 0.17 else vl
        cap = 1.6 * norm(v)
        s = max(-cap, min(cap, s))
        return nodes, mul(line, s)

    def _moves(self):
        self.vec, self.how = {}, {}
        self.slid_junctions, self.terminals, self.cut_moves = [], [], []
        for g in self.groups:
            v = mul(g["dir"], g["mag"])
            for nd, l in g["levels"].items():
                w = mul(v, l)
                h = g["how"][nd]
                if h == "slide":
                    # along its straight edge, never more than 3/4 of that edge (the edge must not collapse)
                    dl = g["slides"][nd]; sl = dot(w, dl)
                    sg = self.seg_after[nd] if self.seg_after[nd]["kind"] == "line" and abs(abs(dot(self.line_dir(self.seg_after[nd]), dl)) - 1) < 1e-6 else self.seg_before[nd]
                    Lmax = 0.75 * norm(sub(self.xy[sg["gj"]], self.xy[sg["gi"]]))
                    w = mul(dl, max(-Lmax, min(Lmax, sl)))
                elif h == "junction":
                    a_, d, si = self.share[nd]
                    w = self._junction_slide(nd, mul(d, a_), self.junction[nd])
                    J = self.junction[nd]
                    if self._partner_moves(J):
                        self.vec[J["partner"]] = w; self.how[J["partner"]] = "junction-blunt"
                    self.slid_junctions.append(dict(node=nd, vec=w, kind=J["kind"], partner=J["partner"], share=a_, group=g["id"]))
                self.vec[nd] = w; self.how[nd] = h
            for j, why, lvl in g["stops"]:
                if why == "cut" and j not in self.vec:
                    T = self._terminal(g, j, lvl)
                    if T:
                        nodes, w = T
                        for nd in nodes:
                            if nd not in self.vec and nd not in self.held:
                                self.vec[nd] = w; self.how[nd] = "terminal"
                        g["terminal"] = (g.get("terminal") or []) + [dict(nodes=nodes, vec=w)]
                        self.terminals.append(dict(nodes=nodes, vec=w, group=g["id"]))
        for nd, J in self.junction.items():
            if nd in self.vec:
                continue
            a_, d, si = self.share[nd]
            mv = self._junction_slide(nd, mul(d, a_), J)
            self.vec[nd] = mv; self.how[nd] = "junction"
            if J["partner"] is not None and J["partner"] not in self.vec and self._partner_moves(J):
                self.vec[J["partner"]] = mv; self.how[J["partner"]] = "junction-blunt"
            self.slid_junctions.append(dict(node=nd, vec=mv, kind=J["kind"], partner=J["partner"], share=a_, group=None))
        # a blunt made of several tiny segments (two junctions sharing a partner): one piece, the smaller slide
        by_partner = {}
        for nd, J in self.junction.items():
            if J["partner"] is not None:
                by_partner.setdefault(J["partner"], []).append(nd)
        for pt, js in by_partner.items():
            if len(js) < 2:
                continue
            w = min((self.vec[n] for n in js if n in self.vec), key=norm, default=None)
            if w is None:
                continue
            for n in js + ([pt] if all(self._partner_moves(self.junction[j_]) for j_ in js) else []):
                if n not in self.held:
                    self.vec[n] = w; self.how[n] = "junction-blunt"
        for nd, faces in self.cut_face.items():
            if nd in self.vec or nd in self.held or nd not in self.share:
                continue
            a_, d, si = self.share[nd]
            if a_ <= 0.5 or self.th.get(nd, 999.0) > 0.75 * self.M.thick_bot / 0.95:
                continue                           # only a thin end opens (R12); a thick end is not a thin part
            f = self.line_dir(faces[0][0])
            s = dot(mul(d, a_), f)
            self.vec[nd] = mul(f, s); self.how[nd] = "cut"
            self.cut_moves.append(dict(node=nd, vec=self.vec[nd]))
        for nd, v in self.pinch.items():
            if nd in self.vec or nd in self.held:
                continue
            self.vec[nd] = v; self.how[nd] = "pinch"
        self._balls()
        self._line_guard()
        self._rigid_sides()
        self._round_corners()

    # ---- R22 (round 8, scoped) a counter's drawn round corner rides with the bar ---------------------------------
    def _round_corners(self):
        """R22 A counter's ROUND corner rides with a growing straight side. Where a growing straight side (R24) flows
        without a corner (its end node smooth / tangent) into a drawn ROUND -- one curve turning 60-120 deg, its chord
        at most half the side, its radius (chord / sqrt 2) at least the side's own width, its far node smooth and
        continuing into the counter's wall at 50-130 deg to the side -- and that round bounds a COUNTER (white enclosed
        by ink), the round moves as ONE rigid piece with the side: along the bisector of the side and the wall, by the
        side's amount / cos(bisector to the side's normal), so its drawn clearance from the moved side is kept (the side
        stays on its translated line, parallel). The wall beyond the round keeps both drawn end directions, stretched
        onto its new chord. A sharp end with a hairpin spur is not a round (it rides with the side, R24); open white (a
        hook's cup) is never a counter, so hooks keep overlapping."""
        self.corner_fits = []
        if not RULES.get("R22", True):
            return
        core = getattr(self, "core_nodes", set())
        for p in getattr(self, "_rigid_plans", []):
            g, n, r = p["g"], p["n"], p["r"]
            if g <= 0.5:
                continue
            for E, G, step in ((r["nodes"][0], self.seg_after[r["nodes"][0]], -1), (r["nodes"][-1], self.seg_before[r["nodes"][-1]], +1)):
                if not (self.smooth.get(E) or self._tangent_through(E)):
                    continue
                rd = self.seg_after[E] if step > 0 else self.seg_before[E]       # the curve the side flows into
                if rd["kind"] != "curve" or (rd["gi"], rd["gj"]) in {(sg["gi"], sg["gj"]) for sg in r["segs"]}:
                    continue
                turn = self._seg_turn(rd); ch = self._seg_len(rd)
                if not (60.0 <= turn <= 120.0) or ch > 0.5 * r["L"]:
                    continue
                F = rd["gj"] if rd["gi"] == E else rd["gi"]
                if F in self.held or F in core or F in self.ball_nodes or not (self.smooth.get(F) or self._tangent_through(F)):
                    continue
                side_w = float(np.median([self.th.get(nd, 0.0) for nd in r["nodes"] if self.th.get(nd, 0.0) > 0] or [0.0]))
                if side_w <= 0 or ch / math.sqrt(2.0) < side_w:
                    continue                                   # a round tighter than the bar is a corner, not a round
                beyond = self.seg_after[F] if step > 0 else self.seg_before[F]
                uG = self.seg_dir_at(G, E)                     # from the corner into the side
                uW = self.seg_dir_at(beyond, F)                # from the corner into the wall
                ang = math.degrees(math.acos(max(-1.0, min(1.0, dot(uG, uW)))))
                if not (50.0 <= ang <= 130.0):
                    continue
                b = unit(add(uG, uW)); cb = dot(b, n)
                if cb < 0.3:
                    continue                                   # the side does not grow into the corner
                if not any(self._hole_at(add(pt, mul(b, 4.0))) for pt in self._seg_poly(rd, 12)):
                    continue                                   # not a counter (a hook's open cup)
                T = mul(b, g / cb)
                before = {nd: self.vec.get(nd, (0.0, 0.0)) for nd in (E, F)}
                for nd in (E, F):
                    self.vec[nd] = T; self.how[nd] = "corner"
                self.corner_fits.append(dict(side=r["nodes"], run=[E, F], vec=(round(T[0], 1), round(T[1], 1)), g=round(g, 1),
                                             radius=round(ch / math.sqrt(2.0), 1), bar=round(side_w, 1),
                                             before={k: (round(v[0], 1), round(v[1], 1)) for k, v in before.items()}))

    def _balls(self):
        """R17 Balls. A ball / teardrop terminal (rungs.Outline._round_balls) never grows: all its nodes move by
        ONE vector, its handles with them, so it travels rigidly with the stroke end. The vector is the
        stroke's own move at the neck (the mean of the two neighbour nodes' moves) taken along the stroke's
        direction there (neck -> ball centre): like a cut face (R11) the end slides, it is not pushed sideways."""
        self.ball_moves = []
        for b in getattr(self.ol, "balls", []):
            nodes = b["nodes"]
            ci = self.contour_of.get(nodes[0])
            if ci is None:
                continue
            ons = self.contours[ci]["ons"]; K = len(ons)
            i0, i1 = ons.index(nodes[0]), ons.index(nodes[-1])
            nb = [ons[(i0 - 1) % K], ons[(i1 + 1) % K]]
            nb = [n for n in nb if n not in self.ball_nodes]
            if not nb:
                continue
            mid = (sum(self.xy[n][0] for n in nb) / len(nb), sum(self.xy[n][1] for n in nb) / len(nb))
            t = unit(sub(b["c"], mid))
            a = sum(dot(self.vec.get(n, (0.0, 0.0)), t) for n in nb) / len(nb)
            w = mul(t, a)
            for nd in nodes:
                if nd not in self.held:
                    self.vec[nd] = w; self.how[nd] = "ball"
            self.ball_moves.append(dict(nodes=nodes, vec=w))

    # ---- counters (R25) --------------------------------------------------------------------------------------
    def _holes(self):
        """the drawn glyph's counters: white enclosed by ink on every side (nonzero winding of all contours)"""
        if hasattr(self, "_hole_grid"):
            return self._hole_grid
        from . import crosscheck
        from scipy import ndimage
        P = crosscheck._polys(self.g["contours"])
        pts = np.concatenate([p["pts"] for p in P if p is not None])
        x0, y0 = np.floor(pts.min(0)) - 4; x1, y1 = np.ceil(pts.max(0)) + 4
        grid = (x0, y0, int(x1 - x0), int(y1 - y0))
        W = sum(crosscheck._winding(p["pts"], grid) for p in P if p is not None)
        ink = W != 0
        lab, n = ndimage.label(ndimage.binary_fill_holes(ink) & ~ink)
        self._hole_grid = (lab, grid)
        return self._hole_grid

    def _hole_at(self, p):
        lab, (x0, y0, W, H) = self._holes()
        i, j = int(p[0] - x0), int(p[1] - y0)
        return int(lab[j, i]) if 0 <= i < W and 0 <= j < H else 0

    def _seg_turn(self, sg):
        a = self.seg_dir_at(sg, sg["gi"]); b = self.seg_dir_at(sg, sg["gj"])
        return math.degrees(math.acos(max(-1.0, min(1.0, -dot(a, b)))))

    def _ride_edge(self, B, E, F):
        """OPTION bracket_rides: B is a curved bracket from the side's end E to F, and F continues TANGENTIALLY (within
        10 deg) into a straight held edge F -> F2: returns (unit direction F -> F2, its length), else None"""
        if B["kind"] != "curve":
            return None
        nxt = self.seg_after[F] if (self.seg_before[F] is B) else self.seg_before[F]
        if nxt is B or nxt["kind"] != "line" or not self._held_seg(nxt):
            return None
        F2 = nxt["gj"] if nxt["gi"] == F else nxt["gi"]
        u = self.seg_dir_at(nxt, F); w = self.seg_dir_at(B, F)
        if dot(u, w) > -math.cos(math.radians(10.0)):
            return None
        return u, norm(sub(self.xy[F2], self.xy[F]))

    def _arc(self, sg):
        poly = self._seg_poly(sg, 48)
        return sum(norm(sub(poly[i], poly[i - 1])) for i in range(1, len(poly)))

    def _seg_len(self, sg):
        return norm(sub(self.xy[sg["gj"]], self.xy[sg["gi"]]))

    # ---- R24 straight sides are rigid ---------------------------------------------------------------------------
    def _straight_runs(self):
        """R24: the straight sides of growing parts: maximal runs of consecutive segments (lines, or curves with both
        handles on the chord) whose nodes and handles all lie within STRAIGHT_TOL of the line through the run's two
        ends, all running the same way, at least STRAIGHT_MIN long, along which a growing stroke's side runs (the side
        with most visible samples on it owns the run)"""
        xy = self.xy
        seg_k = {(sg.gi, sg.gj): k for k, sg in enumerate(self.ol.segs)}
        held = lambda sg: self._held_seg(sg)
        side_of = {}
        for si, (st, rows) in enumerate(self.M.stroke_rows):
            if not self.stroke_grows.get(si):
                continue
            for key, S in ((0, st["A"]), (1, st["B"])):
                for i, src in enumerate(S.src):
                    if src[0] != "hidden":
                        side_of.setdefault(src[0], {}).setdefault((si, key), []).append(float(S.al[i]))
        out = []
        for ci, C in enumerate(self.contours):
            segs = C["segs"]; K = len(segs)
            def pts(sg):
                return [xy[sg["gi"]]] + [xy[o] for o in sg["offs"]] + [xy[sg["gj"]]]
            def fits(run):
                P = [p for sg in run for p in pts(sg)]
                a, b = P[0], P[-1]; L = norm(sub(b, a))
                if L < 1.0:
                    return False
                e = mul(sub(b, a), 1.0 / L)
                if any(dot(sub(xy[sg["gj"]], xy[sg["gi"]]), e) <= 0 for sg in run):
                    return False
                if len({held(sg) for sg in run}) > 1:
                    return False                   # a serif's edge and a stroke's side are never one piece
                return all(abs(cross(sub(p, a), e)) <= STRAIGHT_TOL for p in P)
            start = next((i for i in range(K) if not fits([segs[i]])), 0)
            runs, cur = [], []
            for i in range(K):
                sg = segs[(start + i) % K]
                if fits([sg]) and (not cur or fits(cur + [sg])):
                    cur.append(sg); continue
                if cur: runs.append(cur)
                cur = [sg] if fits([sg]) else []
            if cur: runs.append(cur)
            for run in runs:
                a, b = xy[run[0]["gi"]], xy[run[-1]["gj"]]
                L = norm(sub(b, a))
                if L < STRAIGHT_MIN:
                    continue
                cnt = {}
                for sg in run:
                    for kk, als in side_of.get(seg_k.get((sg["gi"], sg["gj"])), {}).items():
                        cnt.setdefault(kk, []).extend(als)
                if not cnt:
                    continue
                side = max(cnt, key=lambda kk: len(cnt[kk]))
                e = mul(sub(b, a), 1.0 / L)
                out.append(dict(ci=ci, segs=run, nodes=[run[0]["gi"]] + [sg["gj"] for sg in run], e=e, n0=(-e[1], e[0]),
                                side=side, al=(min(cnt[side]), max(cnt[side])), L=L, held=held(run[0])))
        return out

    def _held_seg(self, sg):
        """a segment of a held serif / flag / beak / bracket (spec rule 8)"""
        if not hasattr(self, "_seg_k"):
            self._seg_k = {(s0.gi, s0.gj): k for k, s0 in enumerate(self.ol.segs)}
        k = self._seg_k.get((sg["gi"], sg["gj"]))
        return k is not None and (k in self.ol.serif_segs or self.P.kind.get(self.ol.segs[k].wall) == "flag")

    def _counter_curve(self, sg):
        """R25: the segment is a curve bounding a COUNTER (white enclosed by ink on every side, just off the curve)"""
        if sg["kind"] != "curve":
            return False
        poly = self._seg_poly(sg, 12)
        for k in range(1, len(poly) - 1):
            t = unit(sub(poly[k + 1], poly[k - 1])); nn = (-t[1], t[0])
            for sgn in (1.0, -1.0):
                if self._hole_at(add(poly[k], mul(nn, 4.0 * sgn))):
                    return True
        return False

    def _along_edge(self, E, sg, n, need, cap, cap_ext=None):
        """slide node E along the drawn edge sg (line or curve, starting at E) to where it is `need` u further across
        (along n), within an arc of `cap`; else back along the edge's own line beyond E (the edge gets longer), within
        `cap_ext` (default cap). Returns (w, reach): the move (None if it cannot), and the most `need` the edge allows"""
        cap_ext = cap if cap_ext is None else cap_ext
        poly = self._seg_poly(sg, 48)
        if sg["gj"] == E:
            poly = poly[::-1]
        sg_ = 1.0 if need >= 0 else -1.0
        lam = [sg_ * dot(sub(p, poly[0]), n) for p in poly]
        reach = 0.0; arc = 0.0
        for i in range(1, len(poly)):
            d_ = norm(sub(poly[i], poly[i - 1]))
            fmax = min(1.0, (cap - arc) / max(1e-9, d_))          # the part of this step within the cap
            if lam[i] > lam[i - 1] and lam[i - 1] < abs(need) <= lam[i - 1] + (lam[i] - lam[i - 1]) * fmax:
                f = (abs(need) - lam[i - 1]) / (lam[i] - lam[i - 1])
                return sub(add(poly[i - 1], mul(sub(poly[i], poly[i - 1]), f)), poly[0]), abs(need)
            reach = max(reach, lam[i - 1] + (lam[i] - lam[i - 1]) * fmax)
            if fmax < 1.0:
                break
            arc += d_
        t0 = self.seg_dir_at(sg, E)
        c = -sg_ * dot(t0, n)                 # running on backwards along the edge's line
        if c >= 0.17:
            s_ = abs(need) / c
            reach = max(reach, cap_ext * c)
            if s_ <= cap_ext:
                return mul(t0, -s_), abs(need)
        return None, reach

    def _line_slide(self, t, n, need, cap):
        """slide along the straight direction t until `need` u across n; (w, reach within a slide of cap)"""
        c = dot(t, n)
        if abs(c) < 0.17:
            return None, 0.0
        s_ = need / c
        reach = cap * abs(c)
        return (mul(t, s_) if abs(s_) <= cap + 1e-9 else None), reach

    def _rigid_sides(self):
        """R24 A straight side moves as ONE rigid lateral translation; R25 a counter's curve-to-straight junction stays."""
        self.rigid_report, self.anchors, self.edge_slid = [], set(), {}
        runs = self._straight_runs()
        on_run = {}
        for ri, r in enumerate(runs):
            for nd in r["nodes"]:
                on_run.setdefault(nd, []).append(ri)
        strokes = [st for st, _ in self.M.stroke_rows]
        seg_k = {(sg.gi, sg.gj): k for k, sg in enumerate(self.ol.segs)}
        def ol_seg(sg):
            k = seg_k.get((sg["gi"], sg["gj"]))
            return (k, self.ol.segs[k]) if k is not None else (None, None)
        held_seg = self._held_seg
        plans, unmeasured = [], set()
        for ri, r in enumerate(runs):
            si, key = r["side"]
            R = self.side_rows[(si, key)]
            lo, hi = r["al"]
            pos = R["pos"]
            sel = [i for i in range(len(pos)) if lo - 1.0 <= pos[i] <= hi + 1.0 and not R["hid"][i] and R["ths"][i] >= 5.0]
            if not sel:
                unmeasured.update((sg["gi"], sg["gj"]) for sg in r["segs"])
                continue                                           # the side only runs on along it (no rung measures it)
            ho, hp = R["hown"][sel], R["hoth"][sel]
            Ho = float(ho.max()) if ho.max() >= 0.99 else float(ho.mean())      # a side touching a metric line holds as a whole
            Hp = float(hp.max()) if hp.max() >= 0.99 else float(hp.mean())
            g0 = self.A / 2 * min(2.0, max(0.0, 1.0 - Ho + Hp)) if self.stroke_grows.get(si) else 0.0
            th = float(np.median(R["ths"][sel])); tmin = max(1.0, self.stroke_tmin.get(si, th))
            core = any(nd in getattr(self, "core_nodes", set()) for nd in r["nodes"]) or th <= CORE_RATIO * tmin or th <= THIN_OF_STEM * self.M.thick_bot
            lvl = 1.0 if core else 0.0       # a thick straight side (a leg, a stem-like edge) holds: groups slide along it (R7)
            g0 *= lvl
            nm = (0.0, 0.0)
            for i in sel:
                nm = add(nm, mul(R["ns"][i], R["sgn"]))
            n = r["n0"] if dot(r["n0"], nm) >= 0 else mul(r["n0"], -1.0)
            if r["held"] or any(nd in self.held for nd in r["nodes"]):
                g0 = 0.0                                           # a straight serif edge (or a side through a held node) holds as a whole
            plans.append(dict(ri=ri, r=r, si=si, n=n, g0=g0, g=g0, ends=[], why=[], level=lvl))
        by_ri = {p["ri"]: p for p in plans}
        # the two ends of every side: how each end node may follow the translated line
        for p in plans:
            r, n, g0 = p["r"], p["n"], p["g0"]
            own_walls = self.M._stroke_walls(strokes[p["si"]])
            for E, B in ((r["nodes"][0], self.seg_before[r["nodes"][0]]), (r["nodes"][-1], self.seg_after[r["nodes"][-1]])):
                end = dict(node=E, kind="free", partners=[], fn=None, cap=None)
                F = B["gi"] if B["gj"] == E else B["gj"]
                other = [q for q in on_run.get(E, []) if q != p["ri"] and q in by_ri]
                k_, s0 = ol_seg(B)
                other = [q for q in other if not by_ri[q]["r"]["held"]]
                if other and not r["held"]:
                    end.update(kind="corner", other=other[0])
                elif RULES.get("R25", False) and B["kind"] == "line" and norm(sub(self.xy[F], self.xy[E])) <= 2 * BLUNT and F not in on_run \
                        and self._counter_curve(self.seg_before[F] if self.seg_after[F] is B else self.seg_after[F]):
                    end.update(kind="anchor", anchor=F)              # R25: the counter's junction node stays
                elif E in getattr(self, "starts", {}) or (E in self.junction and self.junction[E]["kind"] in ("notch", "blunt", "start")
                                                          and self.junction[E]["partner"] is not None):
                    J = self.junction[E]
                    hs = J["hseg"]
                    held = J.get("flag") or self.P.kind.get(hs.wall) == "flag" or seg_k.get((hs.gi, hs.gj)) in self.ol.serif_segs
                    # round 8: along a held serif edge only the edge's far end limits the slide; another wall keeps 3/4, 1.6 x
                    cap = max(0.0, hs.length - min(TIP_GAP, 0.25 * hs.length)) if held else min(0.75 * hs.length, 1.6 * g0)
                    t = J["t"]
                    end.update(kind="start-serif" if held else "start", partners=[J["partner"]],
                               fn=(lambda need, t=t, cap=cap, n=n: self._line_slide(t, n, need, cap)), cap=cap)
                elif (held_seg(B) or F in self.held) and RULES.get("bracket_rides", False) and self._ride_edge(B, E, F) is not None:
                    # OPTION (not the shipped rule; shown to Mark): a tangent bracket rides along the serif's straight
                    # edge beyond it as one rigid piece -- the bracket's far node slides along that edge (the serif
                    # edge shortens), the bracket keeps its exact drawn shape, the bar reaches its full amount
                    t, Lr = self._ride_edge(B, E, F)
                    cap = max(0.0, Lr - min(TIP_GAP, 0.25 * Lr))
                    end.update(kind="serif-ride", partners=[F], fn=(lambda need, t=t, cap=cap, n=n: self._line_slide(t, n, need, cap)), cap=cap)
                elif held_seg(B) or F in self.held:
                    cap = max(0.0, self._arc(B) - min(TIP_GAP, 0.25 * self._arc(B)))            # round 8: up to the serif edge's far end, no 60% / 1.6 x
                    end.update(kind="serif", fn=(lambda need, B=B, E=E, cap=cap, n=n: self._along_edge(E, B, n, need, cap)), cap=cap)
                elif k_ is not None and self.P.kind.get(s0.wall) == "cut":
                    t = self.seg_dir_at(B, E); cap = 1.6 * g0
                    end.update(kind="cut", fn=(lambda need, t=t, cap=cap, n=n: self._line_slide(t, n, need, cap)), cap=cap, soft=True, far=F)
                elif (B["gi"], B["gj"]) in unmeasured and abs(dot(self.seg_dir_at(B, E), n)) < SIN_TOL:
                    # the side runs on into a straight piece no rung measures (a serif half the detectors missed):
                    # that piece stays, the end slides along it like along a wall
                    L = norm(sub(self.xy[F], self.xy[E]))
                    cap = min(0.75 * L, 1.6 * g0)
                    end.update(kind="wall", fn=(lambda need, B=B, E=E, cap=cap, n=n, ce=1.6 * g0: self._along_edge(E, B, n, need, cap, ce)), cap=cap)
                elif (k_ is not None and s0.wall in own_walls) or abs(dot(self.seg_dir_at(B, E), n)) < SIN_TOL:
                    end.update(kind="free")                           # the side runs on (own side / tangent): pure lateral
                else:
                    L = s0.length if s0 is not None else norm(sub(self.xy[F], self.xy[E]))
                    cap = min(0.75 * L, 1.6 * g0)
                    end.update(kind="wall", fn=(lambda need, B=B, E=E, cap=cap, n=n, ce=1.6 * g0: self._along_edge(E, B, n, need, cap, ce)), cap=cap)
                p["ends"].append(end)
        # each side's ONE amount: the most every end allows (capped by serif / wall), the same at both ends
        for p in plans:
            for end in p["ends"]:
                if end["fn"] is None or p["g"] <= 0.5:
                    continue
                w, reach = end["fn"](p["g"])
                if w is None:
                    if end.get("soft"):
                        F_ = end.get("far")
                        if F_ is not None and norm(sub(self.xy[F_], self.xy[end["node"]])) <= BLUNT and F_ not in self.held \
                                and F_ not in on_run and len(self.cut_face.get(F_, [])) <= 1:
                            # a short spur the translated line cannot slide along travels with the end as one piece
                            end["fn"] = None; end["kind"] += " (spur rides)"; end["partners"] = [F_]; continue
                        end["fn"] = None; end["kind"] += " (free)"; continue
                    p["g"] = max(0.0, min(p["g"], 0.999 * reach))
                    p["why"].append(("capped at serif tip at node %d" if "serif" in end["kind"] else "capped by wall at node %d") % end["node"])
        # moves
        newvec = {}
        for p in plans:
            r, n, g, e = p["r"], p["n"], p["g"], p["r"]["e"]
            ws = []
            for end in p["ends"]:
                E = end["node"]
                if g <= 0.5:
                    v = self.vec.get(E, (0.0, 0.0)); w = mul(e, dot(v, e))      # a holding side: no lateral move at all
                elif end["kind"] == "corner":
                    q = by_ri[end["other"]]; n2, g2 = q["n"], q["g"]
                    det = cross(n, n2)
                    if abs(det) < 0.17:
                        w = mul(n, g)
                    else:                                              # on both translated lines
                        w = ((g * n2[1] - g2 * n[1]) / det, (n[0] * g2 - n2[0] * g) / det)
                elif end["fn"] is not None:
                    w, _ = end["fn"](g)
                    if w is None:
                        w = mul(n, g)
                    elif end["kind"] in ("serif", "wall"):
                        Bs = self.seg_before[E] if E == r["nodes"][0] else self.seg_after[E]
                        if Bs["kind"] == "curve":
                            self.edge_slid[(Bs["gi"], Bs["gj"])] = dict(node=E, kind=end["kind"])
                else:
                    w = mul(n, g)
                ws.append(w)
                end["w"] = w
            u0, u1 = dot(ws[0], e), dot(ws[1], e)
            a = self.xy[r["nodes"][0]]
            for nd in r["nodes"]:
                f = dot(sub(self.xy[nd], a), e) / r["L"]
                if nd == r["nodes"][0]: w = ws[0]
                elif nd == r["nodes"][-1]: w = ws[1]
                elif g <= 0.5: w = mul(e, dot(self.vec.get(nd, (0.0, 0.0)), e))
                else: w = add(mul(n, g), mul(e, u0 + (u1 - u0) * f))
                newvec[nd] = w
            for end in p["ends"]:
                for pt in end["partners"]:
                    if pt is not None and pt not in on_run and g > 0.5 and end["kind"] != "serif-ride":
                        newvec[pt] = end["w"]                     # a START sliver travels with its end node, as one piece
                if end["kind"] == "anchor" and g > 0.5:
                    self.anchors.add(end["anchor"])
            self.rigid_report.append(dict(nodes=r["nodes"], stroke=p["si"], normal=[round(n[0], 3), round(n[1], 3)],
                                          planned=round(p["g0"], 1), amount=round(g, 1), level=round(p["level"], 2),
                                          ends=[(end["node"], end["kind"]) for end in p["ends"]], capped=p["why"]))
        for p in plans:                                       # OPTION bracket_rides: the bracket's far node rides along
            for end in p["ends"]:                             # the serif edge with the side's end (after the held runs)
                if end["kind"] == "serif-ride" and p["g"] > 0.5:
                    for pt in end["partners"]:
                        newvec[pt] = end["w"]
        # a group holding a node of a straight side moves as one piece with that side: when the side's amount was
        # reduced (capped by serif / wall), the group's other members take the same reduction
        lat = {}
        for p in plans:
            for nd in p["r"]["nodes"]:
                lat[nd] = (p["n"], p["g"])
        self.group_scaled = []
        for g_ in self.groups:
            ratios = []
            for nd in g_["levels"]:
                if nd in lat and nd in self.vec:
                    n_, gg = lat[nd]
                    have = dot(self.vec[nd], n_)
                    if have > 1.0:
                        ratios.append(max(0.0, min(1.0, gg / have)))
            if not ratios or min(ratios) >= 0.95:
                continue
            k = min(ratios)
            for nd in list(g_["levels"]) + [x for T in (g_.get("terminal") or []) for x in T["nodes"]]:
                if nd not in newvec and nd in self.vec and self.how.get(nd) not in ("junction", "junction-blunt"):
                    self.vec[nd] = mul(self.vec[nd], k)
            self.group_scaled.append((g_["id"], round(k, 2)))
        for nd, w in newvec.items():
            self.vec[nd] = w; self.how[nd] = "rigid"
        # R25 the corner where a counter's curved side arrives at a growing bar -- through a short spur up to the bar's
        # straight side (R24), or at the end face of a node-less bar (R21) -- stays where it was drawn
        for C in (self.contours if RULES.get("R25", False) else []):
            for F in C["ons"]:
                if F in newvec or F in self.held or self.smooth.get(F) or self._tangent_through(F):
                    continue
                for A_, B_ in ((self.seg_before[F], self.seg_after[F]), (self.seg_after[F], self.seg_before[F])):
                    if B_["kind"] != "line" or A_["kind"] != "curve":
                        continue
                    far = B_["gi"] if B_["gj"] == F else B_["gj"]
                    if norm(sub(self.xy[far], self.xy[F])) > 2 * BLUNT or norm(self.vec.get(far, (0.0, 0.0))) <= 0.5:
                        continue
                    if not (far in newvec and self.how.get(far) != "anchor" and norm(newvec[far]) > 0.5) and F not in self.bar_ends:
                        continue                  # only at a growing straight side (R24) or at a node-less bar's end face (R21)
                    if norm(self.vec.get(F, (0.0, 0.0))) <= 1e-6 or not self._counter_curve(A_):
                        continue
                    self.anchors.add(F)
        for nd in self.anchors:
            if nd not in newvec:
                self.vec[nd] = (0.0, 0.0); self.how[nd] = "anchor"
        self._rigid_plans = plans

    def _line_guard(self):
        """a straight edge slid from both ends (or from one end past the other) keeps at least 1/4 of its
        drawn length and its direction: the sliding ends give back proportionally"""
        soft = ("slide", "junction", "junction-blunt", "terminal", "cut", "pinch")
        self.guarded = []
        for C in self.contours:
            for sg in C["segs"]:
                a, b = sg["gi"], sg["gj"]
                va, vb = self.vec.get(a, (0.0, 0.0)), self.vec.get(b, (0.0, 0.0))
                d = sub(self.xy[b], self.xy[a]); L2 = dot(d, d)
                if L2 < 1e-6:
                    continue
                rel = sub(vb, va)
                keep = 0.25 if sg["kind"] == "line" else 0.5
                if dot(add(d, rel), d) >= keep * L2:
                    continue
                k = -(1.0 - keep) * L2 / dot(rel, d)
                ends = [n for n in (a, b) if self.how.get(n) in soft]
                if not ends:
                    continue
                if len(ends) == 1:
                    n = ends[0]; sgn = 1.0 if n == b else -1.0
                    den = sgn * dot(self.vec[n], d)
                    kk = 1.0 + (keep * L2 - dot(add(d, rel), d)) / den if abs(den) > 1e-9 else 0.0
                    self.vec[n] = mul(self.vec[n], max(0.0, min(1.0, kk)))
                else:
                    for n in ends:
                        self.vec[n] = mul(self.vec[n], max(0.0, min(1.0, k)))
                self.guarded.append((a, b))

    def _is_host(self, sg, J):
        h = J["hseg"]
        return {sg["gi"], sg["gj"]} == {h.gi, h.gj}

    # ---- 4C. handles ------------------------------------------------------------------------------------------
    def _handles(self):
        new = dict(self.xy)
        for nd, v in self.vec.items():
            new[nd] = add(self.xy[nd], v)
        V = lambda nd: self.vec.get(nd, (0.0, 0.0))
        self.connecting = []
        self.realigned = []
        moved_seg = {}                     # (gi, gj) -> "rigid" | "similar"
        for C in self.contours:
            for sg in C["segs"]:
                if sg["kind"] != "curve":
                    for o in sg["offs"]:
                        new[o] = add(self.xy[o], mul(add(V(sg["gi"]), V(sg["gj"])), 0.5))
                    continue
                gi, gj = sg["gi"], sg["gj"]; o1, o2 = sg["offs"]
                vi, vj = V(gi), V(gj)
                if norm(sub(vi, vj)) < 1e-6:
                    new[o1] = add(self.xy[o1], vi); new[o2] = add(self.xy[o2], vj)
                    moved_seg[(gi, gj)] = "rigid" if norm(vi) > 1e-6 else "fixed"
                    continue
                P0, P3 = complex(*self.xy[gi]), complex(*self.xy[gj])
                Q0, Q3 = complex(*new[gi]), complex(*new[gj])
                if abs(P3 - P0) < 1e-6:
                    new[o1] = add(self.xy[o1], vi); new[o2] = add(self.xy[o2], vj); continue
                if (self.how.get(gi) == "corner") != (self.how.get(gj) == "corner"):
                    st = self._stretch(P0, complex(*self.xy[o1]), complex(*self.xy[o2]), P3, Q0, Q3)
                    if st is not None:
                        # R22: the wall beyond a fitted round keeps both drawn end directions, stretched onto the chord
                        new[o1], new[o2] = st
                        moved_seg[(gi, gj)] = "corner"
                        self.connecting.append((gi, gj, "wall stretched (R22)"))
                        continue
                es = getattr(self, "edge_slid", {}).get((gi, gj))
                if es is not None:
                    fit = self._held_rest(sg, es, Q0, Q3)
                    if fit is not None:
                        new[o1], new[o2] = fit
                        moved_seg[(gi, gj)] = "held"
                        self.connecting.append((gi, gj, "held edge shortened"))
                        continue
                s = (Q3 - Q0) / (P3 - P0)
                for o in (o1, o2):
                    z = Q0 + s * (complex(*self.xy[o]) - P0)
                    new[o] = (z.real, z.imag)
                moved_seg[(gi, gj)] = "similar"
                self.connecting.append((gi, gj, round(abs(s), 3), round(math.degrees(cmath.phase(s)), 1)))
        # R21: a node-less thin end part grows through its handles: each handle of the junction -> end curve whose
        # foot (nearest point on the side) lies on the bar (reads under 0.9 x the junction) moves by the side's own
        # growth there along the stroke normal; a handle at the junction stays, as does the junction node itself
        self.bar_moves = []
        for b in self.bars:
            sg = b["seg"]; R = self.side_rows.get((b["st"], b["key"]))
            if R is None:
                continue
            S_ = R["S"]
            for o in sg["offs"]:
                q = self.xy[o]
                d2 = (S_.P[:, 0] - q[0]) ** 2 + (S_.P[:, 1] - q[1]) ** 2
                sf = float(S_.al[int(np.argmin(d2))])
                k = int(np.clip(np.searchsorted(R["pos"], sf), 1, len(R["pos"]) - 1))
                s0, s1 = R["pos"][k - 1], R["pos"][k]
                u = 0.0 if s1 == s0 else min(1.0, max(0.0, (sf - s0) / (s1 - s0)))
                a = R["gs"][k - 1] + (R["gs"][k] - R["gs"][k - 1]) * u
                th = R["ths"][k - 1] + (R["ths"][k] - R["ths"][k - 1]) * u
                n_ = unit(add(mul(R["ns"][k - 1], 1 - u), mul(R["ns"][k], u)))
                w = mul(n_, R["sgn"] * a) if th < BAR_OF_JUNCTION * b["th_junction"] else (0.0, 0.0)
                new[o] = add(self.xy[o], w)
                self.bar_moves.append((o, round(float(w[0]), 1), round(float(w[1]), 1)))
            moved_seg[(sg["gi"], sg["gj"])] = "similar"
        # smooth nodes stay smooth: a straight edge wins (rule 12), then the similarity-turned side
        for C in self.contours:
            for nd in C["ons"]:
                if not self.smooth.get(nd) and not self._tangent_through(nd):
                    continue                       # (drawn tangent-continuous counts as smooth, flag or not)
                sb, sa = self.seg_before[nd], self.seg_after[nd]
                hb = sb["offs"][-1] if sb["kind"] == "curve" else None
                ha = sa["offs"][0] if sa["kind"] == "curve" else None
                q = new[nd]
                if hb is None and ha is None:
                    continue
                if hb is None or ha is None:
                    line = sb if hb is None else sa
                    other = line["gi"] if line["gj"] == nd else line["gj"]
                    dl = unit(sub(q, new[other]))
                    h = ha if ha is not None else hb
                    L = norm(sub(new[h], q))
                    if L > 1e-6:
                        cur = unit(sub(new[h], q))
                        ang = math.degrees(math.acos(max(-1.0, min(1.0, dot(cur, dl)))))
                        if ang > 0.05 and dot(cur, dl) > 0.5:
                            new[h] = add(q, mul(dl, L))
                            self.realigned.append((nd, h, round(ang, 2), "onto straight edge"))
                    continue
                db, da = sub(new[hb], q), sub(new[ha], q)
                Lb, La = norm(db), norm(da)
                if Lb < 1e-6 or La < 1e-6:
                    continue
                ang = math.degrees(math.acos(max(-1.0, min(1.0, -dot(unit(db), unit(da))))))
                if ang < 0.05:
                    continue
                kb = moved_seg.get((sb["gi"], sb["gj"]), "fixed"); ka = moved_seg.get((sa["gi"], sa["gj"]), "fixed")
                if ka == "similar" and kb == "similar":
                    # both sides turned: the node keeps its drawn tangent (a moved extremum stays an extremum)
                    t0 = unit(sub(self.xy[ha], self.xy[nd])) if norm(sub(self.xy[ha], self.xy[nd])) > 1e-6 else unit(sub(self.xy[nd], self.xy[hb]))
                    new[ha] = add(q, mul(t0, La)); new[hb] = add(q, mul(t0, -Lb))
                    self.realigned.append((nd, (hb, ha), round(ang, 2), "both onto drawn tangent"))
                    continue
                if ka == "similar" and kb != "similar":
                    keep_after = True
                elif kb == "similar" and ka != "similar":
                    keep_after = False
                else:
                    keep_after = La >= Lb
                if keep_after:
                    new[hb] = add(q, mul(unit(da), -Lb)); self.realigned.append((nd, hb, round(ang, 2), "rotated"))
                else:
                    new[ha] = add(q, mul(unit(db), -La)); self.realigned.append((nd, ha, round(ang, 2), "rotated"))
        self.new = new

    @staticmethod
    def _stretch(P0, P1, P2, P3, Q0, Q3):
        """the cubic P0..P3 onto the chord Q0 -> Q3 keeping both end tangents: the chord is written in the basis of
        the two handle directions and each handle scales with its own component (None if degenerate)"""
        e0, e3 = P1 - P0, P2 - P3
        if abs(e0) < 1e-6 or abs(e3) < 1e-6:
            return None
        e0, e3 = e0 / abs(e0), e3 / abs(e3)
        det = e0.real * e3.imag - e0.imag * e3.real
        if abs(det) < 0.3:
            return None
        def comp(c):
            return (c.real * e3.imag - c.imag * e3.real) / det, (e0.real * c.imag - e0.imag * c.real) / det
        u, w = comp(P3 - P0); u1, w1 = comp(Q3 - Q0)
        if abs(u) < 1e-6 or abs(w) < 1e-6:
            return None
        a, b = u1 / u, w1 / w
        if not (0.25 <= a <= 2.5 and 0.25 <= b <= 2.5):
            return None
        Q1 = Q0 + (P1 - P0) * a; Q2 = Q3 + (P2 - P3) * b
        return (Q1.real, Q1.imag), (Q2.real, Q2.imag)

    def _held_rest(self, sg, es, Q0, Q3):
        """R24: what is left of a curved held edge (a bracket) after a straight side's end slid along it. The edge keeps
        its drawn shape: the part from its other end to the slid node is the drawn curve cut there (de Casteljau);
        where the side flowed into the edge without a corner (a tangent bracket) the rest keeps both drawn end
        directions instead (handles stretched along them onto the new chord), so the joint stays smooth."""
        gi, gj = sg["gi"], sg["gj"]; o1, o2 = sg["offs"]
        P = [complex(*self.xy[k]) for k in (gi, o1, o2, gj)]
        E = es["node"]
        if es["kind"] == "serif" and (self.smooth.get(E) or self._tangent_through(E)):
            e0, e3 = P[1] - P[0], P[2] - P[3]
            if abs(e0) > 1e-6 and abs(e3) > 1e-6:
                e0, e3 = e0 / abs(e0), e3 / abs(e3)
                det = e0.real * e3.imag - e0.imag * e3.real
                if abs(det) >= 0.2:
                    c = Q3 - Q0
                    u = (c.real * e3.imag - c.imag * e3.real) / det; w = (e0.real * c.imag - e0.imag * c.real) / det
                    c0 = P[3] - P[0]
                    u0 = (c0.real * e3.imag - c0.imag * e3.real) / det; w0 = (e0.real * c0.imag - e0.imag * c0.real) / det
                    if abs(u0) > 1e-6 and abs(w0) > 1e-6 and 0.25 <= u / u0 <= 2.5 and 0.25 <= w / w0 <= 2.5:
                        Q1 = Q0 + (P[1] - P[0]) * (u / u0); Q2 = Q3 + (P[2] - P[3]) * (w / w0)
                        return (Q1.real, Q1.imag), (Q2.real, Q2.imag)
        # cut the drawn curve at the slid node's new place (nearest parameter)
        Pn = Q0 if E == gi else Q3
        def bz(t):
            u = 1 - t
            return u ** 3 * P[0] + 3 * u * u * t * P[1] + 3 * u * t * t * P[2] + t ** 3 * P[3]
        ts = np.linspace(0, 1, 401)
        tt = float(ts[int(np.argmin([abs(bz(t) - Pn) for t in ts]))])
        if abs(bz(tt) - Pn) > 1.5:
            return None
        def split(Pc, t):
            a = [Pc[i] + (Pc[i + 1] - Pc[i]) * t for i in range(3)]
            b = [a[i] + (a[i + 1] - a[i]) * t for i in range(2)]
            c = b[0] + (b[1] - b[0]) * t
            return [Pc[0], a[0], b[0], c], [c, b[1], a[2], Pc[3]]
        L, R = split(P, tt)
        seg = R if E == gi else L                      # the part that stays (from the slid node to the other end)
        sh0 = Q0 - seg[0]; sh3 = Q3 - seg[3]            # (both within 1.5 u: tidy onto the moved ends)
        q1, q2 = seg[1] + sh0, seg[2] + sh3
        return (q1.real, q1.imag), (q2.real, q2.imag)

    # ---- 7. the axis ------------------------------------------------------------------------------------------
    def contours_at(self, t):
        out = []
        for C, c in zip(self.contours, self.g["contours"]):
            nodes = []
            for i, n in enumerate(c["nodes"]):
                gi = C["base"] + i
                x0, y0 = self.xy[gi]; x1, y1 = self.new[gi]
                nodes.append([x0 + (x1 - x0) * t, y0 + (y1 - y0) * t] + list(n[2:]))
            out.append({"closed": c["closed"], "nodes": nodes})
        return out

    # ---- report -------------------------------------------------------------------------------------------------
    def report(self):
        r = dict(glyph=self.g["glyph"], master=self.g["master"], A=self.A, groups=[], junctions=[], cuts=[], terminals=[],
                 pinch=[], held=sorted(self.held), connecting=self.connecting, realigned=self.realigned,
                 guarded=getattr(self, "guarded", []))
        for g in self.groups:
            rules = ["R10" if g["dir_name"] == "junction slide" else "R4", "R5" if g["dir_name"] != "junction slide" else None]
            if g["ext"]: rules.append("R6")
            if g["slides"]: rules.append("R7")
            if g["graded"]: rules.append("R8")
            if any(st[1] == "between" for st in g["stops"]): rules.append("R9")
            if g.get("terminal"): rules.append("R11")
            r["groups"].append(dict(rules=[x for x in rules if x], id=g["id"], core=g["core"], ext=g["ext"], graded=g["graded"], slides=sorted(g["slides"]),
                                    levels={k: round(v, 2) for k, v in g["levels"].items()},
                                    vector=[round(g["dir"][0] * g["mag"], 1), round(g["dir"][1] * g["mag"], 1)],
                                    mag=round(g["mag"], 1), snap=g["dir_name"], snap_deg=round(g["snap_deg"], 1),
                                    anchors=g["anchors"], stops=[(s[0], s[1]) for s in g["stops"]], cost=round(g["cost"], 3)))
        for j in self.slid_junctions:
            r["junctions"].append(dict(node=j["node"], partner=j["partner"], kind=j["kind"], group=j["group"],
                                       vector=[round(j["vec"][0], 1), round(j["vec"][1], 1)], share=round(j["share"], 1)))
        for t in self.terminals:
            r["terminals"].append(dict(nodes=t["nodes"], group=t["group"], vector=[round(t["vec"][0], 1), round(t["vec"][1], 1)]))
        for c in self.cut_moves:
            r["cuts"].append(dict(node=c["node"], vector=[round(c["vec"][0], 1), round(c["vec"][1], 1)]))
        for nd, v in self.pinch.items():
            r["pinch"].append(dict(node=nd, vector=[round(v[0], 1), round(v[1], 1)]))
        r["rigid"] = getattr(self, "rigid_report", [])
        tc = {}
        for t in getattr(self, "tip_capped", []):
            if self.how.get(t["node"]) == "junction":
                tc[t["node"]] = dict(t, need=float(t["need"]), cap=float(t["cap"]))
        r["tip_capped"] = list(tc.values()) + [dict(node=int(c["capped"][0].split()[-1]), kind="straight side (R24) %s" % c["nodes"],
                                                    planned=c["planned"], amount=c["amount"])
                                               for c in r["rigid"] if c["capped"] and "tip" in c["capped"][0]]
        r["corners"] = getattr(self, "corner_fits", [])
        r["stem_ends"] = sorted(getattr(self, "stem_end_nodes", set()))
        r["anchors"] = sorted(getattr(self, "anchors", set()))
        r["balls"] = [dict(nodes=b["nodes"], vector=[round(b["vec"][0], 1), round(b["vec"][1], 1)]) for b in getattr(self, "ball_moves", [])]
        return r



def _main(argv):
    """python -m wmparts.groupmove SET.json KEY[,KEY]: the per-group report"""
    import time
    from .font import load_set
    G = load_set(argv[0])
    for key in argv[1].split(","):
        t0 = time.time(); GM = GroupMover(G[key]); dt = time.time() - t0
        R = GM.report()
        print("==", key, "%.3fs" % dt)
        for g in R["groups"]:
            print("  group", g["id"], "core", g["core"], "ext", g["ext"], "graded", g["graded"], "slides", g["slides"],
                  "vec", g["vector"], "|%.1f|" % g["mag"], g["snap"], "%.0f°" % g["snap_deg"], "levels", g["levels"], "stops", g["stops"])
        for j in R["junctions"]: print("  junction", j)
        for t in R["terminals"]: print("  terminal", t)
        for c in R["cuts"]: print("  cut", c)
        for p in R["pinch"]: print("  pinch", p)
        for c in R["rigid"]: print("  rigid side (R24)", c)
        if R["anchors"]: print("  anchors (R25)", R["anchors"])
        for c in R["corners"]: print("  round corner (R22)", c)
        for c in R["tip_capped"]: print("  capped at serif tip", c)
        if R["stem_ends"]: print("  stem end nodes (R26)", R["stem_ends"])
        print("  connecting (scale, turn deg)", R["connecting"])
        print("  realigned", R["realigned"])


if __name__ == "__main__":
    import sys
    _main(sys.argv[1:])
