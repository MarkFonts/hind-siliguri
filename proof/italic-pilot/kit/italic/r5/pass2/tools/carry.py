"""The correspondence: the slant is the upright sheared, so the upright's pairing is carried onto it node for node.

  parts_of(g)              Parts read on one copy (its own pairing): slant from the master, the master's stem
  carry(P_up, contours)    a deep copy of the upright's Parts whose geometry is `contours` (same nodes, same
                           segments, same parameters); every Side point is the same (segment, t) on the new
                           outline, so every rung keeps its two ends. Rung arc positions are re-read on the new
                           sides by fractional sample index.
  Rungs(P_up)              the measurement: every node rung of every stroke plus dense rungs every ~12 u between
                           them, each fixed by fractional sample indices on its two sides; .widths(contours)
                           measures the same rungs on any copy (upright, slant, corrected).
"""
import sys, os, json, math, copy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
from parts import Parts, unit
from rungs import Seg

K = 1.0 / 3.0                              # round 5: x' = x + y / 3 (1 x 3 units = 18.435 deg); --slant 1/4 = round 4's 14.036
SLANT = math.degrees(math.atan(K))
WORK = os.path.join(HERE, "..", "..", "..", "..")   # core/parts (r5/pass2 sits two levels deeper than round 4)
R5 = os.path.abspath(os.path.join(HERE, ".."))            # round 5 · pass 2 (src/, sheets/, readings/: the outputs)
R5IN = os.path.abspath(os.path.join(HERE, "..", ".."))    # round 5 pass 1 (read only)
R5S = os.path.join(R5IN, "s")                             # round 5 · s round (read only: its tools' imports)
SRC = os.path.join(R5, "src", "geistserif_italic_18.json")


def src_for(k):
    """the source file of a slant: _14 for 1/4 (scoring against Mark's drawings), _18 for 1/3 (the deliverable)"""
    return os.path.join(R5, "src", "geistserif_italic_%d.json" % (14 if abs(k - 0.25) < 1e-9 else 18 if abs(k - 1 / 3) < 1e-9 else round(1000 * k)))


def set_slant(k):
    """THE shear parameter of round 5 (every tool reads C.K / C.SLANT / C.SRC at run time)"""
    global K, SLANT, SRC
    K = float(k); SLANT = math.degrees(math.atan(K)); SRC = src_for(K)
    return K


def parse_slant(argv, default="1/3"):
    """--slant 1/4 | --slant=1/4 | --slant 0.25 on any command line; default 1/3"""
    from fractions import Fraction
    v = default
    for i, a in enumerate(argv):
        if a == "--slant" and i + 1 < len(argv):
            v = argv[i + 1]
        elif a.startswith("--slant="):
            v = a.split("=", 1)[1]
    return float(Fraction(v))


def strip_slant(argv):
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False; continue
        if a == "--slant":
            skip = True; continue
        if a.startswith("--slant="):
            continue
        out.append(a)
    return out


def angle_label(k=None):
    """'18.43° (x' = x + y/3)'"""
    k = K if k is None else k
    from fractions import Fraction
    f = Fraction(k).limit_denominator(12)
    return "%.2f° (x' = x + %s)" % (math.degrees(math.atan(k)), "y/%d" % f.denominator if f.numerator == 1 else "%s·y" % f)


def stem_of(glyph):
    """the master's vertical stem (geistserif.masters.json, Regular): 94 capitals (H), 84 lowercase (n)"""
    return 94.0 if glyph[:1].isupper() else 84.0


def master_info(glyph, slant):
    """move.Mover's master description for Geist Serif Regular (geistserif.masters.json measured lines)"""
    stem = stem_of(glyph)
    return dict(tag="GeistSerif", ia=slant, stem=stem, A=round(28.0 / 92.0 * stem, 1), thin_top=35.0,
                lines_lc=[770.0, 545.0, 0.0, -212.0], lines_uc=[710.0, 0.0], x_height=545.0, cap_height=710.0)


def slant_of(g):
    return 0.0 if g["master"] == "Regular" else SLANT


def parts_of(g):
    return Parts(g["contours"], slant=slant_of(g), stem=stem_of(g["glyph"]))


# ---- carrying ----------------------------------------------------------------------------------------------
def _frac(al, s):
    """arc length s on a side -> fractional sample index"""
    i = int(np.searchsorted(al, s, side="right") - 1); i = min(max(i, 0), len(al) - 2)
    d = al[i + 1] - al[i]
    return i + (0.0 if d <= 0 else min(1.0, max(0.0, (s - al[i]) / d)))


def _arc(al, f):
    i = min(int(f), len(al) - 2); u = f - i
    return float(al[i] + (al[i + 1] - al[i]) * u)


def side_points(S, ol_new):
    """S's dense points carried onto the outline ol_new: a real point is the same (segment, t) there; a hidden
    point keeps its place between its two visible neighbours (linear, as the hidden run is drawn)"""
    pts = [None] * len(S.pts)
    for i, src in enumerate(S.src):
        if src[0] != "hidden":
            pts[i] = ol_new.segs[src[0]].point(src[1])
    n = len(pts); i = 0
    while i < n:
        if pts[i] is not None:
            i += 1; continue
        j = i
        while j < n and pts[j] is None:
            j += 1
        a, b = i - 1, j
        for k in range(i, j):
            if a >= 0 and b < n:
                u = (k - a) / (b - a)
                # on the line through the two moved ends, at the drawn fraction
                fa = math.dist(S.pts[a], S.pts[k]); fb = math.dist(S.pts[k], S.pts[b])
                u = fa / max(1e-9, fa + fb)
                pts[k] = (pts[a][0] + (pts[b][0] - pts[a][0]) * u, pts[a][1] + (pts[b][1] - pts[a][1]) * u)
            elif a >= 0 or b < n:
                # a hidden run at the side's end continues the side's own straight end: carried along that
                # line as it now lies (exact under any affine map of a straight end)
                e, step = (a, -1) if a >= 0 else (b, +1)
                c = e
                while 0 <= c + step < n and S.src[c + step][0] == S.src[e][0] and pts[c + step] is not None:
                    c += step
                if c == e:
                    d = (pts[e][0] - S.pts[e][0], pts[e][1] - S.pts[e][1]); pts[k] = (S.pts[k][0] + d[0], S.pts[k][1] + d[1])
                else:
                    u0 = (S.pts[e][0] - S.pts[c][0], S.pts[e][1] - S.pts[c][1]); L2 = u0[0] ** 2 + u0[1] ** 2
                    lam = ((S.pts[k][0] - S.pts[e][0]) * u0[0] + (S.pts[k][1] - S.pts[e][1]) * u0[1]) / max(1e-9, L2)
                    u1 = (pts[e][0] - pts[c][0], pts[e][1] - pts[c][1])
                    pts[k] = (pts[e][0] + u1[0] * lam, pts[e][1] + u1[1] * lam)
            else:
                pts[k] = S.pts[k]
        i = j
    return pts


def _restage_outline(ol, contours, slant):
    """the Outline's geometry replaced by `contours` (same node list); walls, kinds, shapes kept"""
    ol.contours = contours
    ol.slant = slant
    base = 0
    for pi, c in enumerate(contours):
        for i, n in enumerate(c["nodes"]):
            ol.node_xy[base + i] = (n[0], n[1], n[2], (n[3] if len(n) > 3 else False))
        base += len(c["nodes"])
    flat = [n for c in contours for n in c["nodes"]]
    for sg in ol.segs:
        wall = sg.wall
        if sg.kind == "line":
            pts = [tuple(flat[sg.gi][:2]), tuple(flat[sg.gj][:2])]
        else:
            # the two off-curves sit between gi and gj in the file (wrapping inside the contour)
            pts = [tuple(flat[sg.gi][:2])]
            c0 = 0; pi = sg.pi
            for c in contours[:pi]:
                c0 += len(c["nodes"])
            N = len(contours[pi]["nodes"]); i, j = sg.gi - c0, sg.gj - c0
            offs = [c0 + (k % N) for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
            pts += [tuple(flat[o][:2]) for o in offs] + [tuple(flat[sg.gj][:2])]
        Seg.__init__(sg, sg.pi, sg.gi, sg.gj, sg.kind, pts)
        sg.wall = wall
    ol.polys = []
    for pi in range(ol.npaths):
        pts = []
        for s in ol.segs:
            if s.pi == pi:
                pts += s.poly[:-1]
        ol.polys.append(pts)
    ol.wall_len = [sum(ol.segs[k].length for k in w) for w in ol.walls]
    # samples: same (segment, t), new place; the normal keeps its inward sense against its own tangent
    P, N = [], []
    for k in range(len(ol.P)):
        sg = ol.segs[int(ol.S[k])]; t = float(ol.T[k])
        p = sg.point(t); tg = sg.tangent(t); sgn = ol._nsign[k]
        P.append(p); N.append((-tg[1] * sgn, tg[0] * sgn))
    ol.P = np.array(P, float); ol.N = np.array(N, float)


def carry(P_up, contours, slant=None):
    """the upright's Parts, deep-copied, on the slant's (or any copy's) geometry: same walls, kinds, strokes,
    rungs (re-read by fractional index), flags, hidden runs"""
    slant = SLANT if slant is None else slant
    # remember each sample normal's sense relative to its own tangent (flipped per shape by Outline._sample)
    ol0 = P_up.ol
    nsign = []
    for k in range(len(ol0.P)):
        sg = ol0.segs[int(ol0.S[k])]; tg = sg.tangent(float(ol0.T[k]))
        nsign.append(1.0 if (ol0.N[k][0] * -tg[1] + ol0.N[k][1] * tg[0]) >= 0 else -1.0)
    P = copy.deepcopy(P_up)
    P.ol._nsign = nsign
    _restage_outline(P.ol, contours, slant)
    sides = {}
    for st in P.strokes:
        for key in ("A", "B"):
            sides[id(st[key])] = st[key]
    for S in list(P.sides.values()) + list(P.flag_sides.values()):
        sides[id(S)] = S
    for S in sides.values():
        S.al_up = S.al.copy(); S.P_up = S.P.copy(); S.T_up = S.T.copy()
        S.pts = side_points(S, P.ol)
        S.finish()
    for st in P.strokes:
        SA, SB = st["A"], st["B"]
        new = []
        for r in st["rungs"]:
            sa, sb = r[0], r[1]
            sa = None if sa is None else _arc(SA.al, _frac(SA.al_up, sa))
            sb = None if sb is None else _arc(SB.al, _frac(SB.al_up, sb))
            new.append((sa, sb) + tuple(r[2:]))
        st["rungs"] = new
    P.carried = True
    return P


# ---- the measurement ------------------------------------------------------------------------------------------
DENSE = 12.0


class Rungs:
    """every rung of the upright's pairing: node rungs (the designer's pairs) and dense rungs between them.
    A rung is (stroke, fa, fb): fractional sample indices on the stroke's side A and side B."""

    def __init__(self, P_up):
        self.P = P_up
        self.rungs = []          # dict(si, fa, fb, kind, a, b, between)
        for si, st in enumerate(P_up.strokes):
            SA, SB = st["A"], st["B"]
            rs = [r for r in st["rungs"] if r[0] is not None and r[1] is not None and r[2] != "cross"]
            prev = None
            for r in rs:
                th, L, pa, pb = P_up.thickness(st, r)
                root = r[2] == "end" and L > 1.6 * max(th, 1e-6)
                kind = "root" if root else ("end" if r[2] == "end" else ("node" if r[2] == "node" else "virt"))
                cur = dict(si=si, fa=_frac(SA.al, r[0]), fb=_frac(SB.al, r[1]), kind=kind, a=r[3], b=r[4], between=None)
                if prev is not None and prev["kind"] != "root" and kind != "root":
                    sa0, sb0 = _arc(SA.al, prev["fa"]), _arc(SB.al, prev["fb"])
                    nsub = max(2, int(max(r[0] - sa0, r[1] - sb0) / DENSE))
                    for k in range(1, nsub):
                        f = k / nsub
                        self.rungs.append(dict(si=si, fa=_frac(SA.al, sa0 + (r[0] - sa0) * f), fb=_frac(SB.al, sb0 + (r[1] - sb0) * f),
                                               kind="dense", a=None, b=None, between=((prev["a"], prev["b"]), (r[3], r[4]), round(f, 2))))
                self.rungs.append(cur)
                prev = cur

    @staticmethod
    def _at(pts, f):
        i = min(int(f), len(pts) - 2); u = f - i
        return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u)

    @staticmethod
    def _tan(pts, f):
        i = min(int(round(f)), len(pts) - 1)
        a = pts[max(0, i - 1)]; b = pts[min(len(pts) - 1, i + 1)]
        return unit((b[0] - a[0], b[1] - a[1]))

    def geometry(self, contours):
        """per stroke, both sides' dense points on this copy"""
        from rungs import Outline
        ol = Outline(contours)          # segment geometry only (same node list => same segment indices)
        return {si: (side_points(st["A"], ol), side_points(st["B"], ol)) for si, st in enumerate(self.P.strokes)}

    def widths(self, contours, geo=None):
        geo = geo or self.geometry(contours)
        out = []
        for r in self.rungs:
            A, B = geo[r["si"]]
            pa, pb = self._at(A, r["fa"]), self._at(B, r["fb"])
            ta, tb = self._tan(A, r["fa"]), self._tan(B, r["fb"])
            mt = unit((ta[0] + tb[0], ta[1] + tb[1]))
            rx, ry = pb[0] - pa[0], pb[1] - pa[1]
            out.append(dict(w=abs(rx * mt[1] - ry * mt[0]), pa=pa, pb=pb, t=mt))
        return out


def direction_class(t):
    """stroke direction of a rung's mean tangent (upright): vertical, horizontal, '/' or '\\'"""
    ang = math.degrees(math.atan2(t[1], t[0])) % 180.0
    if ang < 22.5 or ang >= 157.5:
        return "horizontal"
    if 67.5 <= ang < 112.5:
        return "vertical"
    return "/" if ang < 90 else "\\"


def load():
    return json.load(open(SRC))      # SRC follows set_slant()


def glyphs(G):
    """letters with all copies present (a reference key such as a drawn variant kept beside the letter is skipped)"""
    return sorted(g for g in {k.split("_", 1)[1] for k in G if k.startswith("GeistSerifRegular_")} if "GeistSerifSlant_" + g in G)
