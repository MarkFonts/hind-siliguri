"""OUTLINE-CROSSING check of the move step (round 5, 2026-10-23): a fault the curvature combs cannot see.

The combs judge curvature along each segment; an outline that folds over itself (a node slid past the edge it
meets, so the segments cross) keeps every curve smooth and still prints a hole or an ear. This check compares
the moved outline (CNTR 50 / 100) with the drawn one, on the outline itself and on what it prints:

  CROSSING   a segment of the moved outline crosses another segment of the same contour (or of a contour
             wound the other way: a counter against its outer) where the drawn outline had no crossing
             between those two segments. Neighbouring segments meeting at their shared node do not count.
  FOLD INK   what a fold prints, measured on a 1-unit grid with the true nonzero winding of each contour
             (a contour alone can never print a hole, an inside-out loop, or ink twice):
               hole   inside the contour's own outline but unprinted (a loop turned over onto the body),
               flip   printed by a loop wound against its own contour (an ear turned inside out),
               double the contour covering itself twice (a loop folded onto its body),
               escape the glyph's winding takes the counter's sign (a counter poking out of its bowl).
             Only fold ink that is NEW at the moved state counts (the drawn outline's own folds, e.g. a START
             hairpin that dips 10 u under a bar, grown by <= 1 grid unit, are the drawing).
  A fault region (>= AREA_MIN u^2, at least 2 units thick) is a CROSS when the drawing has no such region of the
  same kind on the same contour (bounded by the same two segments, or within the largest node move of it): NEW;
  or when it matches one but its thickness (2 x area / perimeter) grew by more than half (OPEN_RATIO): OPENED.
  A drawn fold that only travelled or scaled with its parts (two overlapping strokes that both thicken: the v's
  crotch overlap 11.8 -> 17.5 u, x1.48; the e's bar end under the bowl, x1.15) is the drawing, not a cross.
  OPENED is what the outline-pair test alone cannot see: the Harvey Black T's START hairpin 9-10 already dips
  under the bar in the drawing (8-9 x 10-11, a 5 u thick sliver); when only node 10 slid 59.6 u along the beak
  the same two segments still crossed, but the sliver opened into a 12 u thick, 963 u^2 triangle (x2.4).
  A new crossing between two segments that leaves no region of AREA_MIN is listed (status "line"), not counted.
Each region is named by the segment crossings that bound it (`a-b x c-d`), else by the nearest nodes.
INFO (round 6, Mark 2026-10-24: darts and small overlaps inside the T's bar/beak serif "will not affect the final
build"): a region that would count but lies (>= 90% of its area) inside a HELD flag / serif of the drawing -- the
polygon of a wedge, beak or bracket whose tip and at least three nodes hold -- is reported with status "info" and does not count.
"""
import math
import numpy as np
from scipy import ndimage

AREA_MIN = 25.0          # u^2: a new fold region smaller than a 5 x 5 u square is not reported
OPEN_RATIO = 1.5         # a drawn fold whose thickness (2 x area / perimeter) grew by more than half has OPENED
RES = 1.0                # font units per grid cell
NFLAT = 24               # samples per cubic


def _polys(contours):
    """per contour: polyline points and, per polyline edge, the (gi, gj) node pair of the segment it belongs to"""
    out = []; base = 0
    for c in contours:
        nodes = c["nodes"]; N = len(nodes)
        ons = [i for i in range(N) if nodes[i][2] != "o"]
        pts, seg = [], []
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [k % N for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
            P0, P3 = np.array(nodes[i][:2], float), np.array(nodes[j][:2], float)
            key = (base + i, base + j)
            if len(offs) == 2 and nodes[j][2] != "l":
                P1, P2 = np.array(nodes[offs[0]][:2], float), np.array(nodes[offs[1]][:2], float)
                t = np.linspace(0, 1, NFLAT + 1)[:-1][:, None]; u = 1 - t
                B = u ** 3 * P0 + 3 * u * u * t * P1 + 3 * u * t * t * P2 + t ** 3 * P3
                pts.extend(map(tuple, B)); seg.extend([key] * NFLAT)
            else:
                pts.append(tuple(P0)); seg.append(key)
        base += N
        if len(pts) >= 3:
            out.append(dict(pts=np.array(pts), seg=seg))
        else:
            out.append(None)
    return out


def _area(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _winding(P, grid):
    """nonzero winding number of closed polyline P at the grid's cell centres"""
    x0, y0, W, H = grid
    acc = np.zeros((H, W + 1), np.int32)
    Q = np.roll(P, -1, axis=0)
    ys = y0 + (np.arange(H) + 0.5) * RES
    for (ax, ay), (bx, by) in zip(P, Q):
        if ay == by:
            continue
        lo, hi = (ay, by) if ay < by else (by, ay)
        j0 = int(math.ceil((lo - y0) / RES - 0.5)); j1 = int(math.ceil((hi - y0) / RES - 0.5))
        j0 = max(j0, 0); j1 = min(j1, H)
        if j1 <= j0:
            continue
        yc = ys[j0:j1]
        xc = ax + (yc - ay) * (bx - ax) / (by - ay)
        col = np.clip(np.ceil((xc - x0) / RES - 0.5).astype(int), 0, W)
        np.add.at(acc, (np.arange(j0, j1), col), -1 if by > ay else 1)   # counter-clockwise = +1
    return np.cumsum(acc[:, :W], axis=1)


def _crossings(polys):
    """all proper crossings between polyline edges of different segments: [(segA, segB, (x, y))]"""
    E = []
    for ci, p in enumerate(polys):
        if p is None:
            continue
        P = p["pts"]; Q = np.roll(P, -1, axis=0)
        for k in range(len(P)):
            E.append((ci, p["seg"][k], P[k], Q[k]))
    if not E:
        return []
    A = np.array([e[2] for e in E]); B = np.array([e[3] for e in E])
    segs = [e[1] for e in E]; cis = [e[0] for e in E]
    lo = np.minimum(A, B); hi = np.maximum(A, B)
    out = []
    n = len(E)
    for i in range(n):
        m = (lo[i + 1:, 0] <= hi[i, 0]) & (hi[i + 1:, 0] >= lo[i, 0]) & (lo[i + 1:, 1] <= hi[i, 1]) & (hi[i + 1:, 1] >= lo[i, 1])
        idx = np.nonzero(m)[0] + i + 1
        if not len(idx):
            continue
        p, r = A[i], B[i] - A[i]
        q, s = A[idx], B[idx] - A[idx]
        den = r[0] * s[:, 1] - r[1] * s[:, 0]
        ok = np.abs(den) > 1e-12
        qp = q - p
        t = np.where(ok, (qp[:, 0] * s[:, 1] - qp[:, 1] * s[:, 0]) / np.where(ok, den, 1), -1)
        u = np.where(ok, (qp[:, 0] * r[1] - qp[:, 1] * r[0]) / np.where(ok, den, 1), -1)
        eps = 1e-6
        hit = ok & (t > eps) & (t < 1 - eps) & (u > eps) & (u < 1 - eps)
        for k, jj in zip(np.nonzero(hit)[0], idx[hit]):
            sa, sb = segs[i], segs[jj]
            if sa == sb:
                continue                     # a flattening artefact inside one cubic (a cubic's own loop counts below)
            if cis[i] == cis[jj] and (sa[1] == sb[0] or sb[1] == sa[0]):
                # neighbours: they share a node; a crossing right at it is the join itself
                X = p + t[k] * r
                shared = sa[1] if sa[1] == sb[0] else sb[1]
                if t[k] < 1e-3 or t[k] > 1 - 1e-3:
                    continue
            key = (min(sa, sb), max(sa, sb))
            out.append((key, cis[i] == cis[jj], tuple(p + t[k] * r)))
    return out


def _inks(polys, grid):
    """per contour: its own printed area (nonzero winding != 0) and its winding taken along its own orientation"""
    out = []
    for p in polys:
        if p is None:
            out.append(None); continue
        s = 1 if _area(p["pts"]) > 0 else -1
        out.append(_winding(p["pts"], grid) * s)
    return out


def _counters(polys, W0):
    """counter -> its container, from the DRAWN outline: a contour wound against a contour that holds >= 90%
    of its ink (two inks may overlap however they are wound; a counter belongs inside its bowl)"""
    out = {}
    for c, wc in enumerate(W0):
        if wc is None:
            continue
        ic = wc != 0; n = ic.sum()
        for o, wo in enumerate(W0):
            if o == c or wo is None or n == 0:
                continue
            if (_area(polys[c]["pts"]) > 0) != (_area(polys[o]["pts"]) > 0) and (ic & (wo != 0)).sum() >= 0.9 * n \
                    and (wo != 0).sum() > n:
                out[c] = o
    return out


KINDS = ("hole", "ear", "fold", "escape")


def _regions(Wc, counters, X, grid):
    """fault regions of one state: [dict(kind, ci, area, bbox, mask, pairs)]. Kinds:
       hole   inside the contour's own outline yet unprinted (prints wrong),
       ear    printed by a loop wound against its own contour (an inside-out loop),
       fold   the contour covering itself twice (nonzero prints it solid; an even-odd fill -- these sheets,
              Panel.fill_outline fills each contour even-odd -- shows it black),
       escape a counter's ink outside its bowl (prints wrong)."""
    x0, y0, W, H = grid
    out = []
    masks = []
    for ci, w in enumerate(Wc):
        if w is None:
            continue
        ink = w != 0
        masks += [("hole", ci, ndimage.binary_fill_holes(ink) & ~ink), ("ear", ci, w < 0), ("fold", ci, w > 1)]
    for c, o in counters.items():
        masks.append(("escape", c, (Wc[c] != 0) & (Wc[o] == 0)))
    for kind, ci, m in masks:
        m = ndimage.binary_opening(m, iterations=1)       # at least 2 units thick
        lab, n = ndimage.label(m)
        for r in range(1, n + 1):
            mm = lab == r
            area = float(mm.sum()) * RES * RES
            if area < 4.0:
                continue
            jj, ii = np.nonzero(mm)
            bb = (x0 + ii.min() * RES, y0 + jj.min() * RES, x0 + (ii.max() + 1) * RES, y0 + (jj.max() + 1) * RES)
            pairs = sorted({k for k, same, xy in X if bb[0] - 4 <= xy[0] <= bb[2] + 4 and bb[1] - 4 <= xy[1] <= bb[3] + 4})
            out.append(dict(kind=kind, ci=ci, area=area, bbox=bb, mask=mm, pairs=pairs))
    return out


def _near(ra, rb, reach, grid):
    """the two regions come within `reach` units of each other (distance transform on the joint window)"""
    x0, y0, W, H = grid
    ax0, ay0, ax1, ay1 = ra["bbox"]; bx0, by0, bx1, by1 = rb["bbox"]
    if ax0 - reach > bx1 or bx0 - reach > ax1 or ay0 - reach > by1 or by0 - reach > ay1:
        return False
    i0 = int(max(0, (min(ax0, bx0) - x0) / RES - 2)); i1 = int(min(W, (max(ax1, bx1) - x0) / RES + 2))
    j0 = int(max(0, (min(ay0, by0) - y0) / RES - 2)); j1 = int(min(H, (max(ay1, by1) - y0) / RES + 2))
    a = ra["mask"][j0:j1, i0:i1]; b = rb["mask"][j0:j1, i0:i1]
    if not a.any() or not b.any():
        return False
    d = ndimage.distance_transform_edt(~a) * RES
    return bool((d[b] <= reach).any())


def held_polys(M):
    """the drawn polygons of the held flags / serifs of a mover (wedges, beaks, brackets whose nodes all hold)"""
    ol = getattr(M, "ol", None)
    held = set(M.held_nodes()) if hasattr(M, "held_nodes") else set(getattr(M, "held", ()))
    if ol is None:
        return []
    out = []
    for sf in getattr(ol, "serifs", []):
        if sf.get("kind") not in ("wedge", "beak", "bracket") or not sf.get("tip") or not sf.get("sides"):
            continue
        nds = set(sf["tip"])
        for k in sf["sides"]:
            nds |= {ol.segs[k].gi, ol.segs[k].gj}
        if not set(sf["tip"]) <= held or len(nds & held) < 3:
            continue                           # the serif holds (its tip and most of its nodes)
        pts = np.array([ol.node_xy[n][:2] for n in nds], float)
        c = pts.mean(0)
        order = np.argsort(np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0]))
        out.append(pts[order])
    return out


def _inside_frac(mask, grid, polys):
    if not polys:
        return 0.0
    x0, y0, W, H = grid
    jj, ii = np.nonzero(mask)
    X = x0 + (ii + 0.5) * RES; Y = y0 + (jj + 0.5) * RES
    inside = np.zeros(len(X), bool)
    for P in polys:
        w = np.zeros(len(X), bool)
        Q = np.roll(P, -1, axis=0)
        for (ax, ay), (bx, by) in zip(P, Q):
            if ay == by:
                continue
            m = (ay <= Y) != (by <= Y)
            xc = ax + (Y - ay) * (bx - ax) / (by - ay)
            w ^= m & (xc > X)
        inside |= w
    return float(inside.mean()) if len(X) else 0.0


def check(drawn, moved, held=None):
    """new crossings and new / grown fault regions of the moved outline against the drawn one
    (held: polygons of held flags / serifs, held_polys(M); a fault inside one is "info")"""
    P0, P1 = _polys(drawn), _polys(moved)
    pts = np.concatenate([p["pts"] for p in P0 + P1 if p is not None])
    x0, y0 = np.floor(pts.min(0)) - 4; x1, y1 = np.ceil(pts.max(0)) + 4
    grid = (x0, y0, int((x1 - x0) / RES), int((y1 - y0) / RES))
    W0, W1 = _inks(P0, grid), _inks(P1, grid)
    counters = _counters(P0, W0)
    ci_of = {}
    for ci, p in enumerate(P1):
        if p is not None:
            for s in p["seg"]:
                ci_of[s] = ci
    def counts(key, same):
        if same:
            return True
        a, b = ci_of[key[0]], ci_of[key[1]]
        return counters.get(a) == b or counters.get(b) == a     # inks may overlap; a counter may not cross its bowl
    X0 = [x for x in _crossings(P0) if counts(x[0], x[1])]
    X1 = [x for x in _crossings(P1) if counts(x[0], x[1])]
    pairs0 = {k for k, _, _ in X0}
    R0, R1 = _regions(W0, counters, X0, grid), _regions(W1, counters, X1, grid)
    for r in R0 + R1:
        per = float((r["mask"] & ~ndimage.binary_erosion(r["mask"])).sum()) * RES
        r["thick"] = 2.0 * r["area"] / max(per, 1.0)
    # how far anything moved: a drawn fold may have travelled that far with its parts
    f0 = [q for p in P0 if p is not None for q in p["pts"]]; f1 = [q for p in P1 if p is not None for q in p["pts"]]
    reach = max([math.dist(a_, b_) for a_, b_ in zip(f0, f1)] + [1.0])
    crosses = []
    used_pairs = set()
    for rg in R1:
        if rg["area"] < AREA_MIN:
            continue
        # the same fold in the drawing: same contour and kind, bounded by a crossing of the same two segments,
        # or lying within reach of where the drawn one lay (it travelled with its parts)
        dil = None
        match = []
        for r0 in R0:
            if r0["kind"] != rg["kind"] or r0["ci"] != rg["ci"]:
                continue
            if set(rg["pairs"]) & set(r0["pairs"]):
                match.append(r0); continue
            if _near(rg, r0, reach, grid):
                match.append(r0)
        a0 = sum(r0["area"] for r0 in match)
        t0 = max([r0["thick"] for r0 in match] + [0.0])
        if match and not (rg["thick"] > OPEN_RATIO * t0 and rg["area"] > a0 + AREA_MIN):
            continue                      # the drawing's own fold, travelled or scaled with its parts
        used_pairs |= set(rg["pairs"])
        bb = rg["bbox"]
        status = "new" if not match else "opened"
        if held and _inside_frac(rg["mask"], grid, held) >= 0.9:
            status = "info"                    # inside a held serif: the drawing's serif covers it (Mark 2026-10-24)
        crosses.append(dict(kind=rg["kind"], status=status, pairs=[[list(a_), list(b_)] for a_, b_ in rg["pairs"]],
                            area=round(rg["area"]), drawn_area=round(a0), thick=round(rg["thick"], 1), drawn_thick=round(t0, 1),
                            bbox=[round(v, 1) for v in bb], at=[round((bb[0] + bb[2]) / 2, 1), round((bb[1] + bb[3]) / 2, 1)]))
    # a new crossing that left no region to see is still listed (status "line"), but not counted
    for k, same, xy in X1:
        if k not in pairs0 and k not in used_pairs:
            used_pairs.add(k)
            crosses.append(dict(kind="crossing", status="line", pairs=[[list(k[0]), list(k[1])]], area=0, drawn_area=0,
                                bbox=[round(xy[0] - 6, 1), round(xy[1] - 6, 1), round(xy[0] + 6, 1), round(xy[1] + 6, 1)],
                                at=[round(xy[0], 1), round(xy[1], 1)]))
    return crosses


def counted(crosses):
    return [c for c in crosses if c["status"] not in ("line", "info")]


def infos(crosses):
    return [c for c in crosses if c["status"] == "info"]


def label(c):
    pr = ", ".join("%d-%d x %d-%d" % (a[0], a[1], b[0], b[1]) for a, b in c["pairs"]) or "near (%.0f, %.0f)" % tuple(c["at"])
    if c["status"] == "line":
        return "%s (new crossing, no area)" % pr
    if c["status"] == "info":
        return "info: %s %s %d u2, %.0f u thick, inside a held serif" % (c["kind"], pr, c["area"], c.get("thick", 0))
    if c["status"] == "new":
        return "%s %s %d u2 (new)" % (c["kind"], pr, c["area"])
    return "%s opened %s %d u2, %.0f u thick (drawn %d u2, %.0f u)" % (c["kind"], pr, c["area"], c["thick"], c["drawn_area"], c["drawn_thick"])
