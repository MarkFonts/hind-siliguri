"""The move step: grow thin parts along their rungs with the spec's holds. Parts may overlap.

Spec rules used (CONTRAST-SPEC.md): 2 growth window, 3 stem never grows, 6 thins spread from the
centre with each side's hold, 7 a surface near the metric line it faces holds, 8 serifs/flags/beaks
held, 9 cut ends hold (move along the rung only, never along the stroke), 10/13 the root rung carries
its neighbour's move so an arch slides at its junction. Mark (10-22): parts may overlap after the move;
CNTR 100 need not be usable, only consistent.

Mover is the measuring layer GroupMover (groupmove.py, the ruleset in RULES.md) builds on: parts, rungs,
growth and holds. It needs a master description (masters.master_info: slant, stem, A, hairline, metric
lines); the package never guesses one from a master's name.
"""
import math
import numpy as np
from .parts import Parts, unit
from .masters import master_info, A_RATIO   # noqa: F401  (re-exported: the old tools import them from move)
from .font import load_set   # noqa: F401  (the old tools: from move import load_set)


def smoothstep(a, b, x):
    if x <= a: return 1.0
    if x >= b: return 0.0
    u = (x - a) / (b - a)
    return 1.0 - u * u * (3 - 2 * u)


class Mover:
    def __init__(self, g, slant=None, masters=None):
        """g: a glyph layer (wmparts.Glyph or the set.json dict: contours, master, glyph).
        masters: a master_info() dict; default g["_mi"] (attached by wmparts.load_glyphs / load_set)."""
        self.g = g
        master = g["master"]
        mi = masters if masters is not None else g.get("_mi")
        if mi is None:
            raise ValueError("no master values for %s %s: pass masters= (a Masters, a master_info() dict) or load the "
                             "set with its <set>.masters.json (Harvey's numbers ship as wmparts/data/harvey.masters.json)"
                             % (g.get("master"), g.get("glyph")))
        self.mi = mi
        self.slant = mi["ia"] if slant is None else slant
        self.A = mi["A"]
        self.thin_top = mi["thin_top"]
        self.thick_bot = 0.95 * mi["stem"]                     # the stem is measured square to itself
        self.lines = list(mi["lines_uc"] if g["glyph"][:1].isupper() else mi["lines_lc"])
        self.height = mi["x_height"] if g["glyph"].islower() else mi["cap_height"]
        self.stem = self.thick_bot / 0.95
        ys = [n[1] for c in g["contours"] for n in c["nodes"] if n[2] != "o"]
        self.y_lo, self.y_hi = min(ys), max(ys)
        self.P = Parts(g["contours"], slant=self.slant, stem=self.stem)
        self.ol = self.P.ol
        self.disp = {}       # node number -> (dx, dy) at CNTR 100
        self.node_host = {}
        self.rung_log = []
        self._compute()

    # -- holds ------------------------------------------------------------------
    def outside(self, p, out, g):
        """nothing of this shape lies ahead of the surface in the vertical direction it faces"""
        sgn = 1 if out[1] > 0 else -1
        return not any(self.ol.ink_shape(g, p[0], p[1] + sgn * d) for d in range(8, 400, 6))

    def hold_metric(self, p, out, g):
        """rule 7: 1 at the line this surface faces, fading to 0 by 0.3 x height; 2 past the outermost line"""
        facing = 1.0 - smoothstep(0.3, 0.65, abs(out[1]))
        if facing <= 0.0:
            return 0.0
        if not self.outside(p, out, g):
            return 0.0
        sgn = 1 if out[1] > 0 else -1
        ds = [abs(L - p[1]) for L in self.lines if (L - p[1]) * sgn >= -15]
        if not ds:
            return 2.0 * facing
        return facing * smoothstep(0.1 * self.height, 0.3 * self.height, min(ds))

    # -- the move -------------------------------------------------------------------
    def _compute(self):
        P, ol = self.P, self.ol
        shape_of_wall = {wi: ol.shape_of[ol.segs[ol.walls[wi][0]].pi] for wi in range(len(ol.walls))}
        self.side_disp = []   # per stroke: (SA, sa_list, dA_list, SB, sb_list, dB_list)
        self.stroke_rows = []  # additive (groupmove.py): per stroke (st, dense rows with gA/gB), unsmoothed
        self.stroke_kind = []  # additive (groupmove.py): per stroke (is_stem, is_dot), parallel to stroke_rows
        for st in P.strokes:
            SA, SB = st["A"], st["B"]
            g = shape_of_wall[st["walls"][0]]
            flagB = st["walls"][1] in P.flag_sides
            rs = [r for r in st["rungs"] if r[0] is not None and r[1] is not None and r[2] not in ("cross", "long")]
            if len(rs) < 2:
                continue
            # rule 3: two straight sides near stem weight = a stem, never grows (however light it is drawn)
            straightA = float(np.mean([self.ol.segs[src[0]].kind == "line" for src in SA.src if src[0] != "hidden"] or [0]))
            straightB = float(np.mean([self.ol.segs[src[0]].kind == "line" for src in SB.src if src[0] != "hidden"] or [0]))
            widths = [P.thickness(st, r)[0] for r in rs]
            stem_ref = self.thick_bot / 0.95
            is_stem = straightA > 0.6 and straightB > 0.6 and float(np.median(widths)) >= 0.75 * stem_ref
            is_dot = st.get("mode") == "loop"
            rows = []
            for r in rs:
                th, L, pa, pb = P.thickness(st, r)
                d = unit((pb[0] - pa[0], pb[1] - pa[1]))
                outA = (-d[0], -d[1]); outB = d
                is_root = (r[2] == "end" and L > 1.6 * th)
                grow = self.A * smoothstep(self.thin_top, self.thick_bot, th) if not is_root else None
                if is_stem or is_dot:
                    grow = 0.0 if not is_root else None
                hA = self.hold_metric(pa, outA, g)
                hB = 1.0 if flagB else self.hold_metric(pb, outB, g)
                rows.append(dict(r=r, th=th, L=L, pa=pa, pb=pb, d=d, grow=grow, hA=hA, hB=hB, root=is_root))
            # root rungs carry their neighbour's growth and direction (rules 10/13)
            for i, row in enumerate(rows):
                if row["root"]:
                    nb = rows[i + 1] if i == 0 else rows[i - 1]
                    # an honest root: the rung crosses the stroke the same way as its neighbour (the v's
                    # arm thinning into the stem) -> its own width counts. A skewed root (the n's arch
                    # lead-in, a rung running along the stem) inherits the neighbour's growth and direction.
                    cosang = abs(row["d"][0] * nb["d"][0] + row["d"][1] * nb["d"][1])
                    if cosang > math.cos(math.radians(35.0)) and not (is_stem or is_dot):
                        row["grow"] = self.A * smoothstep(self.thin_top, self.thick_bot, row["th"])
                        row["root"] = False
                        row["hA"] = self.hold_metric(row["pa"], (-row["d"][0], -row["d"][1]), g)
                        row["hB"] = 1.0 if flagB else self.hold_metric(row["pb"], row["d"], g)
                    else:
                        row["grow"] = nb["grow"] if nb["grow"] is not None else 0.0
                        row["d"] = nb["d"]; row["hA"] = nb["hA"]; row["hB"] = nb["hB"]
            # dense rungs between the node rungs: the width is read where it changes, so the growth
            # ramps with the taper instead of jumping between two nodes (the n's hook inside)
            dense = []
            for i, row in enumerate(rows):
                dense.append(row)
                if i + 1 >= len(rows):
                    break
                nxt = rows[i + 1]
                if row["root"] or nxt["root"]:
                    continue
                sa0, sb0 = row["r"][0], row["r"][1]; sa1, sb1 = nxt["r"][0], nxt["r"][1]
                nsub = max(2, int(max(sa1 - sa0, sb1 - sb0) / 12.0))
                for k in range(1, nsub):
                    f = k / nsub
                    sa = sa0 + (sa1 - sa0) * f; sb = sb0 + (sb1 - sb0) * f
                    pa, pb = SA.at(sa), SB.at(sb)
                    ta, tb = SA.tan(sa), SB.tan(sb)
                    mt = unit((ta[0] + tb[0], ta[1] + tb[1]))
                    rx, ry = pb[0] - pa[0], pb[1] - pa[1]
                    th = abs(rx * mt[1] - ry * mt[0])
                    d = unit((rx, ry))
                    grow = 0.0 if (is_stem or is_dot) else self.A * smoothstep(self.thin_top, self.thick_bot, th)
                    hA = row["hA"] + (nxt["hA"] - row["hA"]) * f; hB = row["hB"] + (nxt["hB"] - row["hB"]) * f
                    dense.append(dict(r=(sa, sb, "dense", None, None), th=th, L=math.hypot(rx, ry), pa=pa, pb=pb, d=d,
                                      grow=grow, hA=hA, hB=hB, root=False))
            def hidden_at(S, s_):
                i = int(np.searchsorted(S.al, s_, side="right") - 1)
                i = min(max(i, 0), len(S.P) - 1)
                return bool(S.hidden[i]) or bool(S.hidden[min(i + 1, len(S.P) - 1)])
            cut_nodes = set()
            for wi_, k_ in P.kind.items():
                if k_ == "cut":
                    for kk in ol.walls[wi_]:
                        cut_nodes.add(ol.segs[kk].gi); cut_nodes.add(ol.segs[kk].gj)
            for row in dense:
                # a side whose rung end is a drawn node is visible there, even where a hidden run starts beside it
                row["hid"] = (hidden_at(SA, row["r"][0]) and row["r"][3] is None) or (hidden_at(SB, row["r"][1]) and row["r"][4] is None)
                # an end rung along a cut face (rule 9: the end follows the stroke, it is no width)
                if row["r"][2] == "end" and row["r"][3] in cut_nodes and row["r"][4] in cut_nodes:
                    row["hid"] = True
            vis = [i for i, row in enumerate(dense) if not row["hid"] and not row["root"]]
            for i, row in enumerate(dense):
                if row["hid"] and vis:
                    j = min(vis, key=lambda k: abs(k - i))
                    row["grow"] = dense[j]["grow"]; row["hA"] = dense[j]["hA"]; row["hB"] = dense[j]["hB"]
            saL, dAL, sbL, dBL = [], [], [], []
            for row in dense:
                gA = row["grow"] / 2 * min(2.0, max(0.0, 1.0 - row["hA"] + row["hB"]))
                gB = row["grow"] / 2 * min(2.0, max(0.0, 1.0 - row["hB"] + row["hA"]))
                d = row["d"]
                vA = (-d[0] * gA, -d[1] * gA); vB = (d[0] * gB, d[1] * gB)
                saL.append(row["r"][0]); dAL.append(vA); sbL.append(row["r"][1]); dBL.append(vB)
                row["gA"], row["gB"] = gA, gB
                if row["r"][2] != "dense":
                    self.rung_log.append(dict(stroke=st["walls"], a=row["r"][3], b=row["r"][4], w=round(row["th"], 1),
                                              grow=round(row["grow"], 1), hA=round(row["hA"], 2), hB=round(row["hB"], 2),
                                              dA=round(gA, 1), dB=round(gB, 1), root=row["root"]))
            # smooth the displacement along each side (a 24-unit box, twice): no step within a segment
            for sL, dL in ((saL, dAL), (sbL, dBL)):
                for _ in range(2):
                    sm = []
                    for i, s_ in enumerate(sL):
                        acc = [0.0, 0.0]; wsum = 0.0
                        for j, s2 in enumerate(sL):
                            if abs(s2 - s_) <= 12.0:
                                acc[0] += dL[j][0]; acc[1] += dL[j][1]; wsum += 1
                        sm.append((acc[0] / wsum, acc[1] / wsum))
                    dL[:] = sm
            self.side_disp.append((SA, saL, dAL, SB, sbL, dBL, st))
            self.stroke_rows.append((st, dense))
            self.stroke_kind.append((bool(is_stem), bool(is_dot)))
        # node displacements: a node takes the displacement of its side at its arc length
        # Node moves. Every side proposes a move for each of its nodes; the side that moves a node
        # most is its mover. A node that also lies on another part's wall (a cut face, a serif or
        # beak edge, a START wall, another stroke's side) is a JUNCTION: it slides along that wall
        # to where the mover's shifted edge meets it (rule 9 faces hold, rule 8 stems slide along
        # serifs <= 60%, rules 10/13 the junction slides down the stem), and the mover's shift is
        # read one node inward so the whole end segment travels as one piece.
        self.node_side = {}
        self.node_stroke = {}
        cand = {}
        for SA, saL, dAL, SB, sbL, dBL, st in self.side_disp:
            for S, sL, dL in ((SA, saL, dAL), (SB, sbL, dBL)):
                nds = [(idx, nd) for idx, nd in S.nodes if nd is not None]
                for pos, (idx, nd) in enumerate(nds):
                    v = self.interp(S.al[idx], sL, dL)
                    inner = nds[1] if pos == 0 else (nds[-2] if pos == len(nds) - 1 else None)
                    v_in = self.interp(S.al[inner[0]], sL, dL) if (inner and len(nds) > 1) else v
                    cand.setdefault(nd, []).append(dict(v=v, v_in=v_in, S=S, sL=sL, dL=dL, st=st, idx=idx, end=(pos == 0 or pos == len(nds) - 1)))
        held = self.held_nodes()
        for nd, cs in cand.items():
            if nd in held:
                continue
            best = max(cs, key=lambda c: math.hypot(*c["v"]))
            self.node_side[nd] = (best["S"], best["sL"], best["dL"])
            self.node_stroke[nd] = best["st"]
            self.disp[nd] = best["v"]
            host = self._host_wall(nd, best["st"])
            if host is None:
                continue
            sg, kind = host
            t = sg.tangent(0.0) if sg.gi == nd else sg.tangent(1.0)
            u = best["S"].tan(best["S"].al[best["idx"]])
            v = best["v_in"] if best["end"] or kind != "cut" else best["v"]
            if math.hypot(*v) < 1e-6:
                self.disp[nd] = (0.0, 0.0); continue
            cross = t[0] * u[1] - t[1] * u[0]
            if abs(cross) > 0.17:                      # the edge meets the host at > 10 deg
                a = (v[0] * u[1] - v[1] * u[0]) / cross
            else:
                a = v[0] * t[0] + v[1] * t[1]
            if kind == "flag":
                cap = 0.6 * sg.length
                a = max(-cap, min(cap, a))
            cap15 = 1.6 * math.hypot(*v)                 # rule 15: a slide runs at most 1.6x the move
            a = max(-cap15, min(cap15, a))
            self.disp[nd] = (t[0] * a, t[1] * a)
            self.node_host[nd] = kind
        # a short blunt between two DIFFERENT parts (a junction) moves as one piece with the mover
        wall_stroke = {}
        for st in P.strokes:
            for w_ in self._stroke_walls(st):
                wall_stroke.setdefault(w_, st)
        for pi_, ws in P.order.items():
            n_ = len(ws)
            for i_, wi in enumerate(ws):
                if P.kind.get(wi) not in ("cut", "notch") or ol.wall_len[wi] > 25.0:
                    continue
                prev_, nxt_ = ws[i_ - 1], ws[(i_ + 1) % n_]
                sp, sn = wall_stroke.get(prev_), wall_stroke.get(nxt_)
                if sp is not None and sp is sn:
                    continue                                   # a terminal face of one stroke: it widens
                nds = [ol.segs[kk].gi for kk in ol.walls[wi]] + [ol.segs[ol.walls[wi][-1]].gj]
                vmax = max((self.disp.get(nd, (0.0, 0.0)) for nd in nds), key=lambda v: math.hypot(*v))
                for nd in nds:
                    self.disp[nd] = vmax
        # a cut face moves across as one piece (its own along-face slides stay per node)
        for wi, k in self.P.kind.items():
            if k != "cut" or len(ol.walls[wi]) != 1:
                continue
            sg = ol.segs[ol.walls[wi][0]]
            a_, b_ = sg.gi, sg.gj
            d = sg.tangent(0.0); nrm = (-d[1], d[0])
            va, vb = self.disp.get(a_, (0.0, 0.0)), self.disp.get(b_, (0.0, 0.0))
            pa, pb = va[0] * nrm[0] + va[1] * nrm[1], vb[0] * nrm[0] + vb[1] * nrm[1]
            pm = pa if abs(pa) >= abs(pb) else pb
            for nd, v in ((a_, va), (b_, vb)):
                al = v[0] * d[0] + v[1] * d[1]
                self.disp[nd] = (d[0] * al + nrm[0] * pm, d[1] * al + nrm[1] * pm)
        # START walls travel with their stroke
        for wi, k in self.P.kind.items():
            if k != "notch":
                continue
            for kk in ol.walls[wi]:
                a_, b_ = ol.segs[kk].gi, ol.segs[kk].gj
                va, vb = self.disp.get(a_, (0.0, 0.0)), self.disp.get(b_, (0.0, 0.0))
                if math.hypot(*va) >= math.hypot(*vb):
                    self.disp[b_] = va
                else:
                    self.disp[a_] = vb
        self._parallel()
        self._cups()

    def _host_wall(self, nd, st):
        """another part's wall through this node, if any: (segment, kind)"""
        ol = self.ol
        own = self._stroke_walls(st)
        for k, sg in enumerate(ol.segs):
            if nd not in (sg.gi, sg.gj) or sg.wall in own:
                continue
            kind = self.P.kind.get(sg.wall, "side")
            if kind == "buried":
                continue                                  # a buried wall is no surface to slide along (R19)
            if kind in ("cut", "flag", "notch"):
                return sg, kind
            return sg, "side"
        return None

    def _cups(self):
        """Rule 14, italics: an exit hook's cup. Where a side turns sharply (> 60 deg within a short arc)
        and the move jumps across the turn by more than A/2, the cup is not ramped: it moves rigidly
        with the edge beyond it (keeps its drawn roundness) and its start node slides along the edge it
        leaves (the stem/leg line stays, the cup rises)."""
        self.cups = {}
        if self.slant == 0:
            return
        for SA, saL, dAL, SB, sbL, dBL, st in self.side_disp:
            for S in (SA, SB):
                nds = [(idx, nd) for idx, nd in S.nodes if nd is not None]
                for (i0, n0), (i1, n1) in zip(nds, nds[1:]):
                    v0 = self.disp.get(n0, (0.0, 0.0)); v1 = self.disp.get(n1, (0.0, 0.0))
                    if math.hypot(*v1) - math.hypot(*v0) < 0.5 * self.A:
                        continue
                    arc = S.al[i1] - S.al[i0]
                    if arc > 90.0:
                        continue
                    t0, t1 = S.tan(S.al[i0] + 0.5), S.tan(S.al[i1] - 0.5)
                    turn = math.degrees(math.acos(max(-1.0, min(1.0, t0[0] * t1[0] + t0[1] * t1[1]))))
                    if turn < 60.0:
                        continue
                    if n0 in self.node_host or n1 in self.node_host:
                        continue                       # a junction, not a free hook
                    if self.node_stroke.get(n0) is not st or self.node_stroke.get(n1) is not st:
                        continue
                    # the cup: n0 -> n1. n1 keeps its move; n0 slides along its own incoming tangent
                    along = v1[0] * t0[0] + v1[1] * t0[1]
                    self.disp[n0] = (t0[0] * along, t0[1] * along)
                    self.cups[(n0, n1)] = dict(v=v1, t=t0)
                    # nodes of the same stroke before n0 on this side keep ramping to n0's new move
                    self.node_side.pop(n0, None)

    def _stroke_walls(self, st):
        ws = set()
        for S in (st["A"], st["B"]):
            for src in S.src:
                if src[0] != "hidden":
                    ws.add(self.ol.segs[src[0]].wall)
        return ws

    def _grew(self, st):
        return any(math.hypot(*v) > 1.0 for _, _, dAL, _, _, dBL, s2 in self.side_disp if s2 is st for v in dAL + dBL)

    def _parallel(self):
        """Rule 18: a straight edge keeps parallel - both ends take the smaller move across it."""
        ol = self.ol
        for wi, w in enumerate(ol.walls):
            if len(w) != 1 or ol.segs[w[0]].kind != "line" or self.P.kind.get(wi) != "side":
                continue
            sg = ol.segs[w[0]]
            a, b = sg.gi, sg.gj
            if a not in self.disp or b not in self.disp:
                continue
            d = sg.tangent(0.0); n = (-d[1], d[0])
            va, vb = self.disp[a], self.disp[b]
            pa, pb = va[0] * n[0] + va[1] * n[1], vb[0] * n[0] + vb[1] * n[1]
            if pa * pb < 0:
                m = 0.0
            else:
                m = min(abs(pa), abs(pb)) * (1 if pa + pb >= 0 else -1)
            for nd, v, pv in ((a, va, pa), (b, vb, pb)):
                al = v[0] * d[0] + v[1] * d[1]
                self.disp[nd] = (d[0] * al + n[0] * m, d[1] * al + n[1] * m)

    def held_nodes(self):
        if not hasattr(self, "_held"):
            h = set()
            side_nodes = set()
            for wi, k in self.P.kind.items():
                if k == "side":
                    for kk in self.ol.walls[wi]:
                        side_nodes.add(self.ol.segs[kk].gi); side_nodes.add(self.ol.segs[kk].gj)
            for wi, k in self.P.kind.items():
                if k == "flag":
                    for kk in self.ol.walls[wi]:
                        for nd in (self.ol.segs[kk].gi, self.ol.segs[kk].gj):
                            if nd not in side_nodes:
                                h.add(nd)
            self._held = h
        return self._held

    @staticmethod
    def interp(s, sL, dL):
        """piecewise-linear displacement along a side; held at the ends"""
        if s <= sL[0]: return dL[0]
        if s >= sL[-1]: return dL[-1]
        for (s0, v0), (s1, v1) in zip(zip(sL, dL), zip(sL[1:], dL[1:])):
            if s0 <= s <= s1:
                u = 0.0 if s1 == s0 else (s - s0) / (s1 - s0)
                return (v0[0] + (v1[0] - v0[0]) * u, v0[1] + (v1[1] - v0[1]) * u)
        return dL[-1]

    # -- apply ---------------------------------------------------------------------------
    def moved_point(self, gi_seg, t_val, S, sL, dL, t):
        pass

    def contours_at(self, t):
        """the glyph's contours with the move applied at fraction t (0..1).
        On-curve nodes move with their side. A curve whose both ends sit on one side is re-tensioned:
        its handles keep their drawn directions (rule 19; a handle continuing a straight edge follows
        that edge, rule 12) and take the lengths that best fit the moved side, within 0.5-1.6x drawn."""
        out = []
        base = 0
        seg_of = {}       # (gi, gj) -> seg index
        for k, sg in enumerate(self.ol.segs):
            seg_of[(sg.gi, sg.gj)] = k
        for c in self.g["contours"]:
            nodes = c["nodes"]; N = len(nodes)
            ons = [i for i in range(N) if nodes[i][2] != "o"]
            new = [list(n) for n in nodes]
            for a, i in enumerate(ons):
                gi = base + i
                vi = self.disp.get(gi, (0.0, 0.0))
                new[i][0] += vi[0] * t; new[i][1] += vi[1] * t
            for a, i in enumerate(ons):
                j = ons[(a + 1) % len(ons)]
                gi, gj = base + i, base + j
                vi = self.disp.get(gi, (0.0, 0.0)); vj = self.disp.get(gj, (0.0, 0.0))
                offs = [(k % N) for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
                if not offs:
                    continue
                P0 = (nodes[i][0], nodes[i][1]); P3 = (nodes[j][0], nodes[j][1])
                Q0 = (new[i][0], new[i][1]); Q3 = (new[j][0], new[j][1])
                fitted = False
                cup = self.cups.get((gi, gj))
                if cup is not None and len(offs) == 2:
                    v = cup["v"]
                    # the handle at the cup's start keeps its direction along the edge it leaves, with the
                    # start node's own (sliding) move; the far handle moves with the moved edge
                    new[offs[0]][0] += vi[0] * t; new[offs[0]][1] += vi[1] * t
                    new[offs[1]][0] += v[0] * t; new[offs[1]][1] += v[1] * t
                    fitted = True
                if not fitted and len(offs) == 2 and gi in self.node_side and gj in self.node_side and self.node_side[gi][0] is self.node_side[gj][0]:
                    S, sL, dL = self.node_side[gi]
                    k = seg_of.get((gi, gj))
                    pts = [(S.pts[m], S.src[m][1]) for m in range(len(S.pts)) if S.src[m][0] == k]
                    if k is not None and len(pts) >= 6:
                        P1 = (nodes[offs[0]][0], nodes[offs[0]][1]); P2 = (nodes[offs[1]][0], nodes[offs[1]][1])
                        d0 = unit((P1[0] - P0[0], P1[1] - P0[1])); d3 = unit((P2[0] - P3[0], P2[1] - P3[1]))
                        # a handle continuing a straight edge follows the MOVED edge (rule 12)
                        d0 = self._edge_dir(gi, d0, new, base, N, ons, a, -1) ; d3 = self._edge_dir(gj, d3, new, base, N, ons, (a + 1) % len(ons), +1)
                        L1 = math.dist(P0, P1); L2 = math.dist(P3, P2)
                        # the field along the segment, corrected so its ends land on the nodes' own
                        # (possibly slid) moves: the correction fades linearly across the segment
                        si_ = S.al[[m for m in range(len(S.pts)) if S.src[m][0] == k][0]]
                        ms = [m for m in range(len(S.pts)) if S.src[m][0] == k]
                        f0 = self.interp(S.al[ms[0]], sL, dL); f1 = self.interp(S.al[ms[-1]], sL, dL)
                        c0 = (vi[0] - f0[0], vi[1] - f0[1]); c1 = (vj[0] - f1[0], vj[1] - f1[1])
                        Q = []
                        for m in ms:
                            tt_ = S.src[m][1]
                            v = self.interp(S.al[m], sL, dL)
                            v = (v[0] + c0[0] * (1 - tt_) + c1[0] * tt_, v[1] + c0[1] * (1 - tt_) + c1[1] * tt_)
                            Q.append((tt_, (S.pts[m][0] + v[0] * t, S.pts[m][1] + v[1] * t)))
                        # least squares for the two handle lengths a, b
                        A11 = A12 = A22 = b1 = b2 = 0.0
                        for tt, q in Q:
                            u = 1 - tt
                            wa = 3 * u * u * tt; wb = 3 * u * tt * tt
                            bx = u ** 3 * Q0[0] + wa * Q0[0] + wb * Q3[0] + tt ** 3 * Q3[0]
                            by = u ** 3 * Q0[1] + wa * Q0[1] + wb * Q3[1] + tt ** 3 * Q3[1]
                            rx, ry = q[0] - bx, q[1] - by
                            ax, ay = wa * d0[0], wa * d0[1]; cx, cy = wb * d3[0], wb * d3[1]
                            A11 += ax * ax + ay * ay; A12 += ax * cx + ay * cy; A22 += cx * cx + cy * cy
                            b1 += ax * rx + ay * ry; b2 += cx * rx + cy * ry
                        det = A11 * A22 - A12 * A12
                        if abs(det) > 1e-9:
                            la = (b1 * A22 - b2 * A12) / det; lb = (A11 * b2 - A12 * b1) / det
                            if 0.5 * L1 <= la <= 1.6 * L1 and 0.5 * L2 <= lb <= 1.6 * L2:
                                pass
                            else:
                                la = min(max(la, 0.5 * L1), 1.6 * L1) if la > 0 else L1
                                lb = min(max(lb, 0.5 * L2), 1.6 * L2) if lb > 0 else L2
                            new[offs[0]][0] = Q0[0] + d0[0] * la; new[offs[0]][1] = Q0[1] + d0[1] * la
                            new[offs[1]][0] = Q3[0] + d3[0] * lb; new[offs[1]][1] = Q3[1] + d3[1] * lb
                            fitted = True
                if not fitted:
                    for m, k2 in enumerate(offs):
                        f = (m + 1) / (len(offs) + 1)
                        v = (vi[0] + (vj[0] - vi[0]) * f, vi[1] + (vj[1] - vi[1]) * f)
                        new[k2][0] += v[0] * t; new[k2][1] += v[1] * t
            out.append({"closed": c["closed"], "nodes": new})
            base += N
        return out

    def _edge_dir(self, gnode, d, new, base, N, ons, a, side):
        """if the neighbouring segment on `side` (-1 before, +1 after) is a straight line and the node is
        smooth, the handle direction is that moved line's direction (rule 12)"""
        i = gnode - base
        x, y, ty, sm = self.ol.node_xy[gnode]
        if not sm:
            return d
        nb = ons[(ons.index(i) + side) % len(ons)]
        # straight when there are no off-curves between
        between = ((nb - i) % N) if side > 0 else ((i - nb) % N)
        if between != 1:
            return d
        q = (new[nb][0], new[nb][1]); p = (new[i][0], new[i][1])
        dd = unit((p[0] - q[0], p[1] - q[1]))     # away from the line, through the node
        return dd if (dd[0] * d[0] + dd[1] * d[1]) > 0 else (-dd[0], -dd[1])



def _main(argv):
    """python -m wmparts.mover SET.json KEY[,KEY]: the rung log (growth and holds per rung)"""
    from .font import load_set
    G = load_set(argv[0])
    for key in argv[1].split(","):
        M = Mover(G[key])
        print(key, "A", M.A, "window", round(M.thin_top), round(M.thick_bot, 1))
        for row in M.rung_log:
            print("   %-8s %s<->%s w %5.1f grow %5.1f hA %.2f hB %.2f  dA %5.1f dB %5.1f %s" % (
                row["stroke"], row["a"], row["b"], row["w"], row["grow"], row["hA"], row["hB"], row["dA"], row["dB"], "root" if row["root"] else ""))


if __name__ == "__main__":
    import sys
    _main(sys.argv[1:])
