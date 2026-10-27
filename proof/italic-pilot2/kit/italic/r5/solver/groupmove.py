"""GroupMover: raise contrast by moving GROUPS of points rigidly (Mark, images/11-13; GRILL answers 2026-10-23).

THE RULESET. No rule names a glyph or a node: every move falls out of the parts (stem / flag-serif / stroke /
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
     up to 35). The snap that disturbs least wins: angle off the normal + width change of carried nodes +
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
     its share (spec rule 15), 3/4 of the wall segment and 60% of a flag edge (spec rule 8); a blunt
     travels with it as one piece.
     When the core of a group is such a junction, the group's other nodes move WITH it, by their grade x
     the junction's own slide.                                                                    [8B]
 R11 Terminals. Where a group runs into a cut face, the end slides along the face line (the stroke never
     lengthens, spec rule 9); a short blunt (<= 25 u) before a straight end face moves as one piece along
     that face. A face running with the move keeps up with the group (|v| / cos); a face across the move
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
"""
import sys, os, json, math, cmath
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from move import Mover
from rungs import unit

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
                side_nodes = []
                for idx, nd in S.nodes:
                    if nd is None:
                        continue
                    s = S.al[idx]
                    if s < lo - 6.0 or s > hi + 6.0:
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
                    p = dict(a=float(a), dir=mul(n_, sgn), st=si, side=S, th=float(th), hid=hid, core=False, nd=nd)
                    self.props.setdefault(nd, []).append(p)
                    self.inspan.setdefault(nd, set()).add(si)
                    side_nodes.append(p)
                    mx = max(mx, float(a))
                stroke_sides.append(side_nodes)
            # cores: the thinnest nodes of the stroke, and clear local minima of width along a side
            # (end rungs that close to a point, th < 5, are not widths)
            allvis = [p for sn in stroke_sides for p in sn if not p["hid"] and p["th"] >= 5.0]
            tmin = min(p["th"] for p in allvis) if allvis else 0.0
            for side_nodes in (stroke_sides if grows and allvis else []):
                vis = [p for p in side_nodes if not p["hid"] and p["th"] >= 5.0]
                for i, p in enumerate(vis):
                    if p["a"] < 1.0:
                        continue
                    nb = [vis[j]["th"] for j in (i - 1, i + 1) if 0 <= j < len(vis)]
                    localmin = bool(nb) and all(p["th"] <= x for x in nb) and p["th"] <= LOCALMIN * max(nb)
                    if p["th"] <= CORE_RATIO * tmin or localmin or p["th"] <= THIN_OF_STEM * self.M.thick_bot:
                        p["core"] = True
            self.stroke_max[si] = mx

    # ---- 2. node classes -------------------------------------------------------------------------------
    def _classify(self):
        M, P, ol = self.M, self.P, self.ol
        self.held = set(M.held_nodes())
        self.share, self.pinch, self.th, self.corep = {}, {}, {}, {}
        for nd, ps in self.props.items():
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
            host = M._host_wall(nd, strokes[si])
            if host is None:
                continue
            sg, kind = host
            if kind == "cut":
                continue
            if kind == "side" and self.smooth.get(nd):
                continue
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
        self.partners = {J["partner"] for J in self.junction.values() if J["partner"] is not None}

    def is_core(self, nd):
        if nd not in self.share or nd in self.held or nd in self.cut_face or nd in self.pinch:
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
        for end, step in ((run[0], -1), (run[-1], +1)):
            p = end
            for _ in range(3):
                sg = self.seg_after[ons[p]] if step > 0 else self.seg_before[ons[p]]
                if sg["kind"] == "line":
                    cands.append(("edge %d-%d" % (sg["gi"], sg["gj"]), self.line_dir(sg)))
                    break
                p = (p + step) % K
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
                if j in self.cut_face:
                    stops.append((j, "cut", lvl)); break               # terminal (6B), handled in _moves
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
                    if c <= SIN_TOL:
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
            cand = dict(name=name, v=v, m=m, cost=cost, ang=ang, mem=mem, stops=stops)
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
    def _junction_slide(self, nd, w, J):
        own = [sg for sg in (self.seg_before[nd], self.seg_after[nd])
               if J["partner"] not in (sg["gi"], sg["gj"]) and not (J["kind"] != "notch" and self._is_host(sg, J))]
        u = self.seg_dir_at(own[0], nd) if own else (-w[1], w[0])
        t = J["t"]
        cr = cross(t, u)
        s = cross(w, u) / cr if abs(cr) > 0.17 else dot(w, t)
        cap = min(1.6 * norm(w), 0.75 * J["hseg"].length if J["kind"] != "flag" else 1e9)
        if J["kind"] == "flag":
            cap = min(cap, 0.6 * J["flaglen"])
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
            if L <= BLUNT and far["kind"] == "line" and c2 not in self.held:
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
                    if J["partner"] is not None and J["partner"] not in self.held:
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
            if J["partner"] is not None and J["partner"] not in self.vec and J["partner"] not in self.held:
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
            for n in js + [pt]:
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
        self._line_guard()

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
                s = (Q3 - Q0) / (P3 - P0)
                for o in (o1, o2):
                    z = Q0 + s * (complex(*self.xy[o]) - P0)
                    new[o] = (z.real, z.imag)
                moved_seg[(gi, gj)] = "similar"
                self.connecting.append((gi, gj, round(abs(s), 3), round(math.degrees(cmath.phase(s)), 1)))
        # smooth nodes stay smooth: a straight edge wins (rule 12), then the similarity-turned side
        for C in self.contours:
            for nd in C["ons"]:
                if not self.smooth.get(nd):
                    continue
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
        return r


if __name__ == "__main__":
    import time
    G = json.load(open(sys.argv[1]))
    for key in sys.argv[2].split(","):
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
        print("  connecting (scale, turn deg)", R["connecting"])
        print("  realigned", R["realigned"])
