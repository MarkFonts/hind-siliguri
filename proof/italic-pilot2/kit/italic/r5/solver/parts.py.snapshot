"""Parts pairing: split the drawing into parts, each part = two sides; blend the sides.

walls (split at corners) -> cuts (single straight wall, both corners convex = terminal,
both concave = notch), flags (wedge serifs, rule 8), sides (the rest)
-> a side ending on a notch continues HIDDEN along its own line until it meets another wall
-> sides that face each other (mutual majority of inward-normal rays) are one stroke
-> nodes paired across the stroke: equal counts = the designer's own order; else an alignment
   that prefers rungs square to the stroke and lets a node pair with a point between nodes
-> the blend between the sides (Illustrator-style, by arc length) and its 50% = the centreline.
"""
import math
import numpy as np
from rungs import Outline, unit, point_in

COLL_DEG = 3.0
COLL_DIST = 8.0
START_MAX = 16.0
JOIN_DIST = 12.0   # a collinear side this close to the line joins the chain   # Mark: stroke beginnings have 3-10 unit blunt edges; a START wall, never paired


def seg_dir(seg):
    a, b = seg.pts[0], seg.pts[-1]
    return unit((b[0] - a[0], b[1] - a[1]))


def line_dist(p, a, d):
    """distance from p to the line through a with unit direction d"""
    v = (p[0] - a[0], p[1] - a[1])
    return abs(v[0] * d[1] - v[1] * d[0])


def ray_hit(p, d, A, B, skip=None):
    """first crossing of ray p + t d (t > 0.5) with pieces A->B (numpy arrays); returns (t, idx) or None"""
    e = B - A
    den = d[0] * e[:, 1] - d[1] * e[:, 0]
    w = A - np.array(p)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (w[:, 0] * e[:, 1] - w[:, 1] * e[:, 0]) / den
        u = (w[:, 0] * d[1] - w[:, 1] * d[0]) / den
    ok = (np.abs(den) > 1e-12) & (t > 0.5) & (u >= -1e-9) & (u <= 1 + 1e-9)
    if skip is not None:
        ok &= ~skip
    if not ok.any():
        return None
    k = int(np.argmin(np.where(ok, t, np.inf)))
    return float(t[k]), k


class Side:
    """An ordered polyline with named nodes: pieces of segments (with parameter) and hidden gaps."""

    def __init__(self, name):
        self.name = name
        self.pts = []        # dense points
        self.nodes = []      # (index into pts, node number or None for a hidden end)
        self.src = []        # per point: (seg index, t) or ("hidden", None)

    def add_seg(self, seg, k, n=32, node=None):
        if node is not None and (not self.nodes or self.nodes[-1][1] != node):
            idx = max(0, len(self.pts) - 1)
            if self.nodes and self.nodes[-1][0] == idx and self.nodes[-1][1] is None:
                self.nodes[-1] = (idx, node)
            else:
                self.nodes.append((idx, node))
        start = 1 if self.pts else 0
        for i in range(start, n + 1):
            t = i / n
            self.pts.append(seg.point(t)); self.src.append((k, t))

    def add_seg_rev(self, seg, k, n=32, node=None):
        if node is not None and (not self.nodes or self.nodes[-1][1] != node):
            idx = max(0, len(self.pts) - 1)
            if self.nodes and self.nodes[-1][0] == idx and self.nodes[-1][1] is None:
                self.nodes[-1] = (idx, node)
            else:
                self.nodes.append((idx, node))
        start = 1 if self.pts else 0
        for i in range(start, n + 1):
            t = 1.0 - i / n
            self.pts.append(seg.point(t)); self.src.append((k, t))

    def add_hidden(self, q, node=None):
        p = self.pts[-1]
        n = 16
        for i in range(1, n + 1):
            t = i / n
            self.pts.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)); self.src.append(("hidden", t))
        self.nodes.append((len(self.pts) - 1, node))

    def end_node(self, node):
        if not self.nodes or self.nodes[-1][0] != len(self.pts) - 1:
            self.nodes.append((len(self.pts) - 1, node))

    def finish(self):
        P = np.array(self.pts, float)
        d = np.r_[0.0, np.cumsum(np.hypot(*(P[1:] - P[:-1]).T))]
        self.P, self.al = P, d
        self.L = float(d[-1])
        T = np.gradient(P, axis=0)
        n_ = np.hypot(T[:, 0], T[:, 1]); n_[n_ == 0] = 1
        self.T = T / n_[:, None]
        self.hidden = np.array([s[0] == "hidden" for s in self.src])

    def at(self, s):
        """point at arc length s"""
        s = min(max(s, 0.0), self.L)
        i = int(np.searchsorted(self.al, s, side="right") - 1); i = min(max(i, 0), len(self.P) - 2)
        u = (s - self.al[i]) / max(1e-9, self.al[i + 1] - self.al[i])
        return tuple(self.P[i] + (self.P[i + 1] - self.P[i]) * u)

    def tan(self, s):
        i = int(np.searchsorted(self.al, s, side="right") - 1); i = min(max(i, 0), len(self.P) - 1)
        return tuple(self.T[i])

    def reversed(self):
        r = Side(self.name + "'")
        r.pts = self.pts[::-1]; r.src = self.src[::-1]
        N = len(self.pts)
        r.nodes = [(N - 1 - i, nd) for i, nd in reversed(self.nodes)]
        r.finish()
        return r


class Parts:
    def __init__(self, contours, slant=0.0, stem=None):
        self.stem = stem
        self.ol = ol = Outline(contours, slant=slant, stem=stem)
        self._split_collinear()
        self._classify()
        self._hidden()
        self._faces()
        self._pair()

    # ---- walls ---------------------------------------------------------------
    def _split_collinear(self):
        ol = self.ol
        changed = True
        while changed:
            changed = False
            for wi, w in enumerate(ol.walls):
                if len(w) < 2:
                    continue
                for pos in (0, -1):
                    k = w[pos]; s = ol.segs[k]
                    if s.kind != "line":
                        continue
                    d = seg_dir(s)
                    for k2, s2 in enumerate(ol.segs):
                        if s2.pi != s.pi or s2.wall == wi or s2.kind != "line":
                            continue
                        d2 = seg_dir(s2)
                        if abs(d[0] * d2[0] + d[1] * d2[1]) < math.cos(math.radians(COLL_DEG)):
                            continue
                        off = min(max(line_dist(s2.pts[0], s.pts[0], d), line_dist(s2.pts[1], s.pts[0], d)),
                                  max(line_dist(s.pts[0], s2.pts[0], d2), line_dist(s.pts[1], s2.pts[0], d2)))
                        if off < COLL_DIST:
                            rest = w[1:] if pos == 0 else w[:-1]
                            ol.walls[wi] = rest
                            ol.walls.append([k]); s.wall = len(ol.walls) - 1
                            changed = True
                            break
                    if changed:
                        break
                if changed:
                    break
        ol.wall_len = [sum(ol.segs[k].length for k in w) for w in ol.walls]
        # contour order of walls
        self.order = {}
        for pi in range(ol.npaths):
            ws = []
            for k, s in enumerate(ol.segs):
                if s.pi == pi and (not ws or ws[-1] != s.wall):
                    ws.append(s.wall)
            if len(ws) > 1 and ws[0] == ws[-1]:
                ws.pop()
            self.order[pi] = ws

    def corner_convex(self, wa, wb):
        """turn from the end of wall wa into the start of wall wb: True convex (ink on the left: a left turn)"""
        ol = self.ol
        ta = ol.segs[ol.walls[wa][-1]].tangent(1.0); tb = ol.segs[ol.walls[wb][0]].tangent(0.0)
        cr = ta[0] * tb[1] - ta[1] * tb[0]
        pi = ol.segs[ol.walls[wa][0]].pi
        return (cr > 0) if ol.area[pi] > 0 else (cr < 0)

    def _classify(self):
        ol = self.ol
        self.kind = {}
        # each contour's own height (a ligature's word height must not decide one letter's cuts)
        self.cheight = {}
        for pi_, poly in enumerate(ol.polys):
            xs = [q[0] for q in poly]; ys = [q[1] for q in poly]
            self.cheight[pi_] = max(max(ys) - min(ys), max(xs) - min(xs)) if ys else 0.0   # the contour's larger extent
        flag_segs = set(ol.serif_segs)
        for pi, ws in self.order.items():
            n = len(ws)
            for i, wi in enumerate(ws):
                w = ol.walls[wi]
                prev, nxt = ws[i - 1], ws[(i + 1) % n]
                kind = "side"
                if all(k in flag_segs for k in w):
                    kind = "flag"
                if len(w) == 1 and ol.segs[w[0]].kind == "line" and n > 2:
                    sg = ol.segs[w[0]]
                    d = seg_dir(sg)
                    # the neighbours' tangents, skipping tiny chamfers (a terminal face next to a 5-unit blunt)
                    def nb_tangent(direction):
                        j = i
                        for _ in range(n):
                            j = (j + direction) % n
                            if ol.wall_len[ws[j]] > START_MAX:
                                return ol.segs[ol.walls[ws[j]][-1]].tangent(1.0) if direction < 0 else ol.segs[ol.walls[ws[j]][0]].tangent(0.0)
                        return (0.0, 0.0)
                    ta, tb = nb_tangent(-1), nb_tangent(+1)
                    sharp = abs(d[0] * ta[0] + d[1] * ta[1]) < math.cos(math.radians(40)) and abs(d[0] * tb[0] + d[1] * tb[1]) < math.cos(math.radians(40))
                    tiny = sg.length <= START_MAX
                    # a cut is shorter than the walls it joins (skipping tiny chamfers next to it)
                    def big_nb(direction):
                        j = i
                        for _ in range(n):
                            j = (j + direction) % n
                            if ol.wall_len[ws[j]] > START_MAX:
                                return ol.wall_len[ws[j]]
                        return 0.0
                    # a cut joins the two sides of ONE stroke: its big neighbours run antiparallel
                    antipar = (ta[0] * tb[0] + ta[1] * tb[1]) < -0.5
                    shorter = sg.length < 0.8 * max(big_nb(-1), big_nb(+1)) and antipar and sg.length < 0.5 * self.cheight[pi]
                    nrm = (-d[1], d[0]); mid = sg.point(0.5)
                    if not ol.ink_shape(ol.shape_of[pi], mid[0] + nrm[0] * 3, mid[1] + nrm[1] * 3):
                        nrm = (-nrm[0], -nrm[1])
                    others = [pj for pj in range(ol.npaths) if pj != pi and ol.area[pj] > 0]
                    buried = bool(others) and all(
                        any(point_in(ol.polys[pj], sg.point(t)[0] - nrm[0] * 3, sg.point(t)[1] - nrm[1] * 3) for pj in others)
                        for t in (0.15, 0.3, 0.5, 0.7, 0.85))
                    shorter_any = sg.length < 0.8 * max(big_nb(-1), big_nb(+1)) and sg.length < 0.5 * self.cheight[pi]
                    c1, c2 = self.corner_convex(prev, wi), self.corner_convex(wi, nxt)
                    if buried:
                        kind = "cut"
                    elif (tiny or (sharp and shorter)) and c1 and c2:
                        kind = "cut"
                    elif (tiny or (sharp and shorter_any)) and not c1 and not c2:
                        kind = "notch"
                if kind == "side" and len(w) == 1 and ol.segs[w[0]].kind == "line":
                    sg = ol.segs[w[0]]; d = seg_dir(sg)
                    for nbw in (prev, nxt):
                        s2 = ol.segs[ol.walls[nbw][-1 if nbw == prev else 0]]
                        if s2.kind != "line":
                            continue
                        d2 = seg_dir(s2)
                        dot_ = d[0] * d2[0] + d[1] * d2[1]
                        hairpin = (sg.length <= 40.0 and dot_ < -math.cos(math.radians(40.0))) or \
                                  (sg.length <= 80.0 and dot_ < -math.cos(math.radians(20.0)))
                        collinear = abs(d[0] * d2[0] + d[1] * d2[1]) > math.cos(math.radians(COLL_DEG)) and \
                            max(line_dist(sg.pts[0], s2.pts[0], d2), line_dist(sg.pts[1], s2.pts[0], d2)) < COLL_DIST
                        if hairpin or collinear:
                            kind = "notch"
                self.kind[wi] = kind
        # a flag tip is tiny: make sure the serif's three edges are all 'flag'
        for k in flag_segs:
            self.kind[ol.segs[k].wall] = "flag" if all(kk in flag_segs for kk in ol.walls[ol.segs[k].wall]) else self.kind[ol.segs[k].wall]

    # ---- hidden continuations --------------------------------------------------
    def _pieces(self):
        """flattened pieces of every wall: arrays A, B, wall id"""
        A, B, W = [], [], []
        for wi, w in enumerate(self.ol.walls):
            for k in w:
                poly = self.ol.segs[k].poly
                for a, b in zip(poly, poly[1:]):
                    A.append(a); B.append(b); W.append(wi)
        return np.array(A, float), np.array(B, float), np.array(W)

    def _hidden(self):
        """Path extension. A side whose end sits on a START wall or a concave corner runs on along
        its own line: through walls that still have ink beyond them (another part lying on top),
        onto a collinear wall (which joins the chain), and stops where the ink ends."""
        ol = self.ol
        A, B, W = self._pieces()
        self.pieceA, self.pieceB, self.pieceW = A, B, W
        self.chains = {}
        used = set()
        todo = [(pi, wi) for pi, ws in self.order.items() for wi in ws if self.kind[wi] == "side"]
        todo.sort(key=lambda t: -ol.wall_len[t[1]])
        for pi, wi in todo:
            if True:
                if wi in used:
                    continue
                chain = [("wall", wi, True)]
                for end in ("end", "start"):
                    cur = wi; cur_fwd = (end == "end")     # which end of `cur` the ray leaves from
                    for _ in range(6):
                        ext = self._extend(cur, cur_fwd, pi)
                        if ext is None:
                            break
                        piece, join = ext
                        if end == "end":
                            chain.append(piece)
                        else:
                            chain.insert(0, ("hidden", piece[2], piece[1]))
                        if join is None:
                            break
                        wj, same_way = join
                        if wj == wi or (wj in used and wj not in self.chains):
                            break
                        if wj in self.chains:
                            del self.chains[wj]
                        used.add(wj)
                        wpiece = ("wall", wj, same_way if end == "end" else not same_way)
                        if end == "end":
                            chain.append(wpiece)
                        else:
                            chain.insert(0, wpiece)
                        cur, cur_fwd = wj, same_way
                used.add(wi)
                self.chains[wi] = chain
        self.hidden_edges = {wi: [(pc[1], pc[2]) for pc in ch if pc[0] == "hidden"] for wi, ch in self.chains.items()}
        self.merged_into = {}
        for wi, ch in self.chains.items():
            for pc in ch:
                if pc[0] == "wall" and pc[1] != wi:
                    self.merged_into[pc[1]] = wi

    def _extend(self, wi, forward, pi):
        """Extend wall wi beyond its end (forward) or start. Returns (("hidden", p, q), join) or None;
        join = (wall, that wall runs the same way as the ray) when the ray lands on a collinear wall."""
        ol = self.ol
        ws = self.order[pi]; i = ws.index(wi); n = len(ws)
        seg = ol.segs[ol.walls[wi][-1 if forward else 0]]
        if seg.kind != "line":
            return None
        nb = ws[(i + 1) % n] if forward else ws[i - 1]
        nb2 = ws[(i + 2) % n] if forward else ws[(i - 2) % n]
        concave = not (self.corner_convex(wi, nb) if forward else self.corner_convex(nb, wi))
        if not concave and self.kind.get(nb) != "notch":
            return None
        d = seg_dir(seg)
        p = seg.pts[1] if forward else seg.pts[0]
        if not forward:
            d = (-d[0], -d[1])
        A, B, W = self.pieceA, self.pieceB, self.pieceW
        g = ol.shape_of[pi]
        same = np.array([ol.shape_of[ol.segs[ol.walls[int(w)][0]].pi] == g for w in W])
        skip = (W == wi) | (W == nb) | (W == nb2) | ~same
        e = B - A
        den = d[0] * e[:, 1] - d[1] * e[:, 0]
        w_ = A - np.array(p)
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (w_[:, 0] * e[:, 1] - w_[:, 1] * e[:, 0]) / den
            u = (w_[:, 0] * d[1] - w_[:, 1] * d[0]) / den
        ok = (np.abs(den) > 1e-12) & (t > 0.5) & (u >= -1e-9) & (u <= 1 + 1e-9) & ~skip
        idx = np.where(ok)[0]
        stop = None; first_hit_flag = False; first = True
        for k in idx[np.argsort(t[idx])]:
            tk = float(t[k])
            if first:
                first_hit_flag = self.kind.get(int(W[k])) == "flag"; first = False
            beyond = (p[0] + d[0] * (tk + 2.0), p[1] + d[1] * (tk + 2.0))
            if ol.ink_shape(g, *beyond):
                continue                                   # another part lies on top: run on
            stop = tk
            break
        # a collinear straight side lying ahead on this line joins the chain
        best = None
        for wj in range(len(ol.walls)):
            if wj in (wi, nb, nb2) or self.kind.get(wj) != "side" or ol.segs[ol.walls[wj][0]].pi != pi:
                continue
            segs = [ol.segs[kk] for kk in ol.walls[wj]]
            if not all(sg.kind == "line" for sg in segs):
                continue
            d2 = seg_dir(segs[0])
            if abs(d[0] * d2[0] + d[1] * d2[1]) < math.cos(math.radians(4.0)):
                continue
            if max(line_dist(segs[0].pts[0], p, d), line_dist(segs[-1].pts[1], p, d)) > JOIN_DIST:
                continue
            same_way = (d[0] * d2[0] + d[1] * d2[1]) > 0
            near = segs[0].pts[0] if same_way else segs[-1].pts[1]
            along = (near[0] - p[0]) * d[0] + (near[1] - p[1]) * d[1]
            if along < -2.0:
                continue
            if best is None or along < best[0]:
                best = (along, wj, same_way, near)
        # Evidence that the side really runs on (Mark's k: the stem does, the leg does not):
        # it joins a collinear wall, it follows a START wall, it passes under a flag, or it
        # lands on a node the designer drew.
        near_node = False
        if stop is not None:
            q = (p[0] + d[0] * stop, p[1] + d[1] * stop)
            near_node = any(math.dist(q, (x, y)) <= 8.0 for x, y, t_, sm in ol.node_xy.values() if t_ != "o")
        allowed = (best is not None and (stop is None or best[0] <= stop + 8.0)) or \
                  self.kind.get(nb) == "notch" or first_hit_flag or near_node
        if not allowed:
            return None
        if best is not None and (stop is None or best[0] <= stop + 8.0):
            return ("hidden", p, best[3]), (best[1], best[2])
        if stop is None:
            return None
        return ("hidden", p, (p[0] + d[0] * stop, p[1] + d[1] * stop)), None

    # ---- sides as polylines -------------------------------------------------------
    def side_polyline(self, wi):
        ol = self.ol
        S = Side("w%d" % wi)
        for pc in self.chains[wi]:
            if pc[0] == "hidden":
                _, p, q = pc
                if not S.pts:
                    S.pts.append(p); S.src.append(("hidden", 0.0)); S.nodes.append((0, None))
                S.add_hidden(q, node=None)
            else:
                _, wj, fwd = pc
                ks = ol.walls[wj] if fwd else list(reversed(ol.walls[wj]))
                for k in ks:
                    sg = ol.segs[k]
                    n = max(1, int(math.ceil(sg.length / 6.0))) if sg.kind == "line" else 32
                    if fwd:
                        S.add_seg(sg, k, n=n, node=sg.gi)
                    else:
                        S.add_seg_rev(sg, k, n=n, node=sg.gj)
                lastseg = ol.segs[ks[-1]]
                S.end_node(lastseg.gj if fwd else lastseg.gi)
        S.finish()
        return S

    # ---- facing ----------------------------------------------------------------------
    def _faces(self):
        ol = self.ol
        sides = [wi for wi in self.chains]
        self.sides = {wi: self.side_polyline(wi) for wi in sides}
        # flag walls (serif brackets, tips, feet, beak sides) can be the far side of a stroke
        # (the E's arm sits on its serif's foot edge) but never start a pairing
        self.flag_sides = {}
        for wi, k in self.kind.items():
            if k == "flag":
                self.chains[wi] = [("wall", wi, True)]
                self.flag_sides[wi] = self.side_polyline(wi)
                del self.chains[wi]
        self.sides.update(self.flag_sides)
        # pieces for ray casting: all sides (with hidden stretches) + cuts + notches, per shape
        A, B, W = [], [], []
        for wi, S in self.sides.items():
            for a, b in zip(S.P[:-1], S.P[1:]):
                A.append(a); B.append(b); W.append(wi)
        for wi, k in self.kind.items():
            if k in ("cut", "notch"):
                for kk in ol.walls[wi]:
                    poly = ol.segs[kk].poly
                    for a, b in zip(poly, poly[1:]):
                        A.append(a); B.append(b); W.append(wi)
        A, B, W = np.array(A, float), np.array(B, float), np.array(W)
        shape_of_wall = {wi: ol.shape_of[ol.segs[ol.walls[wi][0]].pi] for wi in range(len(ol.walls))}
        votes = {}
        for wi, S in self.sides.items():
            if wi in self.flag_sides:
                continue
            g = shape_of_wall[wi]
            same = np.array([shape_of_wall[int(w)] == g for w in W])
            cnt = {}
            n = len(S.P)
            for i in range(0, n, max(1, n // 60)):
                p = S.P[i]; t = S.T[i]
                nrm = (-t[1], t[0])
                # inward: ink on the left of travel for an outer contour
                if not ol.ink_shape(g, p[0] + nrm[0] * 2.0, p[1] + nrm[1] * 2.0):
                    nrm = (-nrm[0], -nrm[1])
                h = ray_hit(p, nrm, A, B, skip=(W == wi) | ~same)
                if h is None:
                    continue
                hw = int(W[h[1]])
                if self.kind.get(hw) in ("side", "flag"):
                    cnt[hw] = cnt.get(hw, 0) + 1
            votes[wi] = cnt
        self.votes = votes
        pairs = set()
        total = {wi: sum(c.values()) for wi, c in votes.items()}
        for wi, cnt in votes.items():
            if not cnt:
                continue
            best = max(cnt, key=cnt.get)
            if best in self.flag_sides:
                # a held edge as the far side: accept when it takes most of my rays
                if cnt[best] >= 0.5 * max(1, total.get(wi, 0)):
                    pairs.add((wi, best) if wi < best else (best, wi))
                continue
            back = votes.get(best, {})
            # mutual majority, or my majority partner sends at least 15% of its rays back to me
            if back and (max(back, key=back.get) == wi or back.get(wi, 0) >= 0.15 * max(1, total.get(best, 0))):
                pairs.add((min(wi, best), max(wi, best)))
        self.stroke_pairs = sorted(pairs)
        self.unpaired = [wi for wi in self.sides if wi not in self.flag_sides and not any(wi in p for p in pairs)]
        # a closed loop with no partner (a dot) is a round part: its two halves face each other
        self.loops = []
        for wi in list(self.unpaired):
            S = self.sides[wi]
            if len(S.P) < 8 or math.dist(S.P[0], S.P[-1]) > 2.0:
                continue
            self.loops.append(wi)
        self.unpaired = [wi for wi in self.unpaired if wi not in self.loops]

    # ---- node pairing -------------------------------------------------------------------
    def _pair(self):
        self.strokes = []
        for wa, wb in self.stroke_pairs:
            SA = self.sides[wa]; SB = self.sides[wb].reversed()      # B runs the same way as A now
            rungs = self.align(SA, SB)
            self.strokes.append(dict(walls=(wa, wb), A=SA, B=SB, rungs=rungs, mode=self.last_mode))
        for wi in self.loops:
            S = self.sides[wi]
            P = S.P
            # split at the two points farthest apart (the dot's diameter)
            d2 = ((P[:, None, :] - P[None, :, :]) ** 2).sum(-1)
            i, j = np.unravel_index(int(np.argmax(d2)), d2.shape)
            i, j = sorted((int(i), int(j)))
            A = Side("w%d.a" % wi); B = Side("w%d.b" % wi)
            A.pts = list(map(tuple, P[i:j + 1])); A.src = S.src[i:j + 1]
            B.pts = list(map(tuple, np.concatenate([P[j:], P[:i + 1]]))); B.src = S.src[j:] + S.src[:i + 1]
            A.nodes = [(k - i, nd) for k, nd in S.nodes if i <= k <= j]
            B.nodes = [((k - j) if k >= j else (len(P) - j + k), nd) for k, nd in S.nodes if k >= j or k <= i]
            if not A.nodes or A.nodes[0][0] != 0: A.nodes.insert(0, (0, None))
            if A.nodes[-1][0] != len(A.pts) - 1: A.nodes.append((len(A.pts) - 1, None))
            if not B.nodes or B.nodes[0][0] != 0: B.nodes.insert(0, (0, None))
            if B.nodes[-1][0] != len(B.pts) - 1: B.nodes.append((len(B.pts) - 1, None))
            A.finish(); B.finish()
            rungs = self.align(A, B.reversed())
            self.strokes.append(dict(walls=(wi, wi), A=A, B=B.reversed(), rungs=rungs, mode="loop"))
        # flags: fan blends
        self.flags = []
        for sf in self.ol.serifs:
            ka, kb = sf["sides"]
            a, b = self.ol.segs[ka], self.ol.segs[kb]
            self.flags.append(dict(tip=sf["tip"], a=a, b=b))

    def align(self, SA, SB):
        """Pair A's nodes with B's. Ends pair with ends (a cut, or the stroke's root).
        Interior: equal counts = the designer's order (if every rung is near square),
        else an alignment that may pair a node with a point between nodes."""
        na = [(SA.al[i], nd) for i, nd in SA.nodes]
        nb = [(SB.al[i], nd) for i, nd in SB.nodes]
        def sine(sa, sb):
            pa, pb = SA.at(sa), SB.at(sb)
            r = (pb[0] - pa[0], pb[1] - pa[1]); L = math.hypot(*r)
            if L < 1e-6: return 0.0
            ta, tb = SA.tan(sa), SB.tan(sb)
            mt = unit((ta[0] + tb[0], ta[1] + tb[1]))
            return abs((r[0] * mt[0] + r[1] * mt[1]) / L)
        def square_end(sa, sb, nda, ndb, lo_a, hi_a, lo_b, hi_b):
            """an end rung that runs along the stroke (one side ends further along than the other, the
            v's arm reaching the foot) is replaced by the square rung from the shorter side's end; the
            stub beyond it is the root lead-in"""
            pa, pb = SA.at(sa), SB.at(sb)
            ta, tb = SA.tan(sa), SB.tan(sb)
            mt = unit((ta[0] + tb[0], ta[1] + tb[1]))
            rx, ry = pb[0] - pa[0], pb[1] - pa[1]; L = math.hypot(rx, ry)
            th = abs(rx * mt[1] - ry * mt[0])
            if L <= 1.6 * max(th, 1e-6):
                return (sa, sb, "end", nda, ndb)
            # the two nodes are joined by a face wall (a cut, a blunt, a flag edge): a terminal,
            # however slanted; keep the designer's rung
            if nda is not None and ndb is not None:
                for wi_, k_ in self.kind.items():
                    if k_ in ("cut", "notch", "flag"):
                        nds_ = {self.ol.segs[kk].gi for kk in self.ol.walls[wi_]} | {self.ol.segs[kk].gj for kk in self.ol.walls[wi_]}
                        if nda in nds_ and ndb in nds_:
                            return (sa, sb, "end", nda, ndb)
            cands = []
            sb2 = self.project(pa, ta, SB, lo_b, hi_b)
            if sb2 is not None:
                cands.append((math.dist(pa, SB.at(sb2)), (sa, sb2, "end", nda, None)))
            sa2 = self.project(pb, tb, SA, lo_a, hi_a)
            if sa2 is not None:
                cands.append((math.dist(SA.at(sa2), pb), (sa2, sb, "end", None, ndb)))
            if not cands:
                return (sa, sb, "end", nda, ndb)
            return min(cands)[1]
        first = square_end(na[0][0], nb[0][0], na[0][1], nb[0][1], 0.0, na[-1][0], 0.0, nb[-1][0])
        last = square_end(na[-1][0], nb[-1][0], na[-1][1], nb[-1][1], first[0] or 0.0, SA.L, first[1] or 0.0, SB.L)
        ia, ib = na[1:-1], nb[1:-1]
        mode = "index"
        rungs = []
        if len(ia) == len(ib) and all(sine(a[0], b[0]) < 0.77 for a, b in zip(ia, ib)):
            rungs = [(sa, sb, "node", nda, ndb) for (sa, nda), (sb, ndb) in zip(ia, ib)]
        else:
            mode = "align"
            m, n = len(ia), len(ib)
            GAP = 0.3
            D = np.full((m + 1, n + 1), np.inf); D[0, 0] = 0
            bt = {}
            for i in range(m + 1):
                for j in range(n + 1):
                    if i > 0 and D[i - 1, j] + GAP < D[i, j]: D[i, j] = D[i - 1, j] + GAP; bt[(i, j)] = (i - 1, j)
                    if j > 0 and D[i, j - 1] + GAP < D[i, j]: D[i, j] = D[i, j - 1] + GAP; bt[(i, j)] = (i, j - 1)
                    if i > 0 and j > 0:
                        c = D[i - 1, j - 1] + 2.0 * sine(ia[i - 1][0], ib[j - 1][0])
                        if c < D[i, j]: D[i, j] = c; bt[(i, j)] = (i - 1, j - 1)
            i, j = m, n; raw = []
            while (i, j) != (0, 0):
                pi_, pj = bt[(i, j)]
                if pi_ == i - 1 and pj == j - 1:
                    raw.append((ia[i - 1][0], ib[j - 1][0], "node", ia[i - 1][1], ib[j - 1][1]))
                elif pi_ == i - 1:
                    raw.append((ia[i - 1][0], None, "gapA", ia[i - 1][1], None))
                else:
                    raw.append((None, ib[j - 1][0], "gapB", None, ib[j - 1][1]))
                i, j = pi_, pj
            raw.reverse()
            # resolve gaps by projection, each inside the window between its matched neighbours
            matched = [(i, r) for i, r in enumerate(raw) if r[2] == "node"]
            for i, r in enumerate(raw):
                sa, sb, kind, nda, ndb = r
                if kind == "node":
                    rungs.append(r); continue
                prev_m = max([m for m in matched if m[0] < i], key=lambda m: m[0], default=None)
                next_m = min([m for m in matched if m[0] > i], key=lambda m: m[0], default=None)
                if kind == "gapA":
                    lo = prev_m[1][1] if prev_m else first[1]; hi = next_m[1][1] if next_m else last[1]
                    sb = self.project(SA.at(sa), SA.tan(sa), SB, lo, hi)
                    rungs.append((sa, sb, "virtB", nda, None) if sb is not None else (sa, None, "endA", nda, None))
                else:
                    lo = prev_m[1][0] if prev_m else first[0]; hi = next_m[1][0] if next_m else last[0]
                    sa = self.project(SB.at(sb), SB.tan(sb), SA, lo, hi)
                    rungs.append((sa, sb, "virtA", None, ndb) if sa is not None else (None, sb, "endB", None, ndb))
        rungs.sort(key=lambda r: (r[0] if r[0] is not None else (SA.L * (r[1] / max(SB.L, 1e-9)) if r[1] is not None else 0.0)))
        rungs = [first] + rungs + [last]
        clean = []; lastp = (-1e9, -1e9)
        for r in rungs:
            sa, sb = r[0], r[1]
            if sa is None or sb is None:
                clean.append(r); continue
            if sa >= lastp[0] - 1e-6 and sb >= lastp[1] - 1e-6:
                clean.append(r); lastp = (sa, sb)
            else:
                clean.append((sa, sb, "cross", r[3], r[4]))
        self.last_mode = mode
        return clean

    def project(self, p, t, S, lo=None, hi=None, guess=None):
        """arc length on S (within [lo, hi]) of the point where the rung from p is square to the mean
        tangent. Among candidates within 20 deg of square the SHORTEST rung wins (a far point on a
        winding stroke can also be square). None if nothing inside the window."""
        cands = []
        for i in range(len(S.P)):
            s_ = S.al[i]
            if lo is not None and s_ < lo - 1e-6: continue
            if hi is not None and s_ > hi + 1e-6: continue
            q = S.P[i]; r = (q[0] - p[0], q[1] - p[1]); L = math.hypot(*r)
            if L < 1e-6: continue
            mt = unit((t[0] + S.T[i][0], t[1] + S.T[i][1]))
            c = abs((r[0] * mt[0] + r[1] * mt[1]) / L)
            cands.append((c, L, i))
        if not cands:
            return None
        square = [x for x in cands if x[0] <= 0.35]
        if not square:
            return None
        c, L, i = min(square, key=lambda x: (x[1] * (1.0 + x[0])))
        if i in (0, len(S.P) - 1):
            return None
        return float(S.al[i])

    # ---- blend ----------------------------------------------------------------------------
    def blend(self, stroke, u, steps=24):
        """polyline of the blend at fraction u (0 = side A, 1 = side B)"""
        SA, SB = stroke["A"], stroke["B"]
        rs = [(r[0], r[1]) for r in stroke["rungs"] if r[0] is not None and r[1] is not None and r[2] != "cross"]
        if len(rs) < 2:
            return []
        pts = []
        for (a0, b0), (a1, b1) in zip(rs, rs[1:]):
            for k in range(steps + 1):
                f = k / steps
                pa = SA.at(a0 + (a1 - a0) * f); pb = SB.at(b0 + (b1 - b0) * f)
                pts.append((pa[0] + (pb[0] - pa[0]) * u, pa[1] + (pb[1] - pa[1]) * u))
        return pts

    def thickness(self, stroke, r):
        """perpendicular thickness of a rung: |rung x mean tangent|"""
        SA, SB = stroke["A"], stroke["B"]
        pa, pb = SA.at(r[0]), SB.at(r[1])
        ta, tb = SA.tan(r[0]), SB.tan(r[1])
        mt = unit((ta[0] + tb[0], ta[1] + tb[1]))
        rx, ry = pb[0] - pa[0], pb[1] - pa[1]
        return abs(rx * mt[1] - ry * mt[0]), math.hypot(rx, ry), pa, pb
