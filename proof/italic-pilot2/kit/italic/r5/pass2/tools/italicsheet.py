"""Renders for the Geist Serif italic correction: upright / plain slant 14.04 deg / corrected slant.

    python3.13 italicsheet.py [letters|all] [--out DIR]

letters: comma list of glyph names (n,H,quoteright) or a run of single letters (nHa); default all.
Writes into DIR (default italic/sheets):
  <fname>_italic.png        per letter. Row A: UPRIGHT | PLAIN SLANT | CORRECTED, filled, thickest (orange) and
                            thinnest (cyan) rung of every part, the rest thin grey; subtitle = mean thickness change
                            per stroke-direction class against the upright on the SAME rungs.
                            Row B: slant filled + corrected outlined (nodes, handles, yellow node moves) and swapped.
                            Row C: the acceptance test: corrected back-slanted (x - y/4) over the upright, with the
                            upright's thickest/thinnest rungs; the plain slant back-slanted (= the upright) as reference.
  overview_italic.png       every letter: UPRIGHT | SLANT | CORRECTED (slant dashed under it)
  word_harpers.png          the proof page's own layout, white, 3 rows: upright / plain slant / corrected, 3280 wide
  word_harpers_backslant.png  the same, rows 2 and 3 back-slanted by x -= y/4 (the Metro Nova bottom-row test)

Inputs (all optional except the Regular + Slant keys): italic/src/geistserif_italic.json (GeistSerif{Regular,Slant,
Italic}_<g>), italic/readings/<fname>.readings.json, italic/src/kerning.json ({"L R": value}).
A missing Italic key = "not corrected": the plain slant is drawn in a grey tint and labelled so.
A missing readings file = the rungs are computed here (upright: Parts + thickness on its own pairing;
slant / corrected: the upright's rungs carried to the same nodes / the same segment parameter and re-measured).
"""
import sys, os, json, math, re, argparse, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from sheet import Panel, BG, SS, INK, EDGE, ON, OFF, LBL_ON, font, MENLO, CAL
from partsheet import draw_poly
from rungs import Seg, unit
from parts import Parts
import readings as RD

ROOT = os.path.abspath(os.path.join(HERE, ".."))
SRC = os.path.join(ROOT, "src", "geistserif_italic.json")
KERN = os.path.join(ROOT, "src", "kerning.json")
RDIR = os.path.join(ROOT, "readings")
GPKG = os.path.abspath(os.path.join(ROOT, "..", "src", "geist-serif17.glyphspackage"))
REGULAR_MASTER_ID = "DCBCDAAA-39F5-436E-B8F7-AA5CB02C428B"

import carry as _C
K = _C.K                                   # round 5: set by --slant (default 1/3 = 18.43 deg); main() re-reads it
ANGLE = math.degrees(math.atan(K))
YK = "y/3"                                 # the shear's label, set in main()
TAG = "18"
TAGS = {"up": "GeistSerifRegular", "sl": "GeistSerifSlant", "it": "GeistSerifItalic"}
CORE = ["f", "j", "H", "n", "a", "E", "T", "r", "v", "e", "y", "k", "x"]
EXTRA = ["p", "s", "B", "z", "quoteright"]
METRICS = [(0, "baseline"), (530, "x 530"), (710, "cap 710"), (800, "asc 800"), (-150, "desc -150")]

THICK, THIN, REST = (255, 150, 40), (60, 220, 235), (120, 120, 120)
YEL = (250, 225, 60)
OFFINK = (255, 60, 200)
GREYFILL = (62, 62, 62)
BRIGHT = (240, 240, 240)
DIMUP = (38, 46, 30)
MEASURED = ("node", "virt", "cut")          # root rungs are not stroke widths; crossings are junctions
SQUARE = 1.15                               # a root rung no longer than this x its width is square to the stroke: a stem's own width
ROOT_MAX = 1.5 * 94.0                       # ... and no wider than 1.5 x the heaviest stem of the master (caps 94): wider = a junction
TIP = 12.0                                  # a part whose thickest rung is under this is a serif tip / blunt edge, not a stroke
EDGE_TOL = 2.0                              # a rung sample this close to the outline is on the ink (cut rungs lie ON the edge)


# ---- data ----------------------------------------------------------------------------------------------------
def load():
    return json.load(open(SRC))


def key(tag, g):
    return "%s_%s" % (TAGS[tag], g)


def get(G, tag, g):
    k = key(tag, g)
    if k in G:
        return G[k]
    if g == "space" and "space" in G:
        return G["space"]
    return None


def letters_in(G):
    have = [g for g in CORE + EXTRA if get(G, "up", g) is not None and get(G, "sl", g) is not None]
    others = sorted({k.split("_", 1)[1] for k in G if k.startswith(TAGS["up"] + "_")} - set(have) - {"space"})
    return have + [g for g in others if get(G, "sl", g) is not None]


def shear(contours, k):
    return [{**c, "nodes": [[n[0] + k * n[1], n[1]] + list(n[2:]) for n in c["nodes"]]} for c in contours]


def segs_of(contours):
    """rungs.Outline's segmenting without its detectors: [Seg] in file order"""
    out = []; base = 0
    for pi, c in enumerate(contours):
        nodes = c["nodes"]; N = len(nodes)
        ons = [i for i in range(N) if nodes[i][2] != "o"]
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [(nodes[k % N][0], nodes[k % N][1]) for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
            P0, P1 = (nodes[i][0], nodes[i][1]), (nodes[j][0], nodes[j][1])
            if len(offs) == 2 and nodes[j][2] != "l":
                out.append(Seg(pi, base + i, base + j, "curve", [P0, offs[0], offs[1], P1]))
            else:
                out.append(Seg(pi, base + i, base + j, "line", [P0, P1]))
        base += N
    return out


class Flat:
    """what Panel.fill_outline needs: polys + signed areas"""
    def __init__(self, contours):
        self.contours = contours
        self.segs = segs_of(contours)
        self.polys = []
        for pi in range(len(contours)):
            pts = []
            for s in self.segs:
                if s.pi == pi:
                    pts += s.poly[:-1]
            self.polys.append(pts)
        self.area = [sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1])) / 2 for p in self.polys]

    def inside(self, p):
        """nonzero winding"""
        x, y = p; wn = 0
        for poly in self.polys:
            n = len(poly)
            for k in range(n):
                x0, y0 = poly[k]; x1, y1 = poly[(k + 1) % n]
                if y0 <= y < y1 or y1 <= y < y0:
                    xc = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
                    if x < xc:
                        wn += 1 if y1 > y0 else -1
        return wn != 0

    def edge_dist(self, p):
        best = 1e9
        for poly in self.polys:
            A = np.array(poly, float); B = np.roll(A, -1, axis=0); D = B - A
            L2 = (D ** 2).sum(1); L2[L2 == 0] = 1e-9
            t = np.clip(((p[0] - A[:, 0]) * D[:, 0] + (p[1] - A[:, 1]) * D[:, 1]) / L2, 0, 1)
            q = A + D * t[:, None]
            best = min(best, float(np.sqrt(((q - np.array(p)) ** 2).sum(1)).min()))
        return best

    def bbox(self):
        xs = [p[0] for poly in self.polys for p in poly] or [0]; ys = [p[1] for poly in self.polys for p in poly] or [0]
        return min(xs), min(ys), max(xs), max(ys)


def nodes_flat(contours):
    return [n for c in contours for n in c["nodes"]]


# ---- rungs ---------------------------------------------------------------------------------------------------
def measured(r):
    """node / virt / cut rungs, and root rungs that are square to the stroke (a stem whose only nodes are its ends)"""
    return r["kind"] in MEASURED or (r["kind"] == "root" and r.get("square", False) and r.get("up_width", r["width"]) <= ROOT_MAX)


def dir_class(t):
    """stroke direction from the rung's mean tangent (upright): | vertical, - horizontal, / rising, \\ falling"""
    a = math.degrees(math.atan2(t[1], t[0])) % 180.0
    if abs(a - 90) <= 20:
        return "|"
    if a <= 20 or a >= 160:
        return "-"
    return "/" if a < 90 else "\\"


CLS_NAME = {"|": "vertical", "-": "horizontal", "/": "/", "\\": "\\"}


def rungs_from_readings(R):
    out = []
    for part in R["parts"]:
        if part.get("kind") != "stroke":
            continue
        for r in part["rungs"]:
            if "a" not in r or r.get("width") is None:
                continue
            L = r.get("rung") or math.dist(r["a"], r["b"])
            out.append(dict(part=part["id"], kind=r["kind"], a_node=r.get("a_node"), b_node=r.get("b_node"),
                            a=tuple(r["a"]), b=tuple(r["b"]), width=float(r["width"]), tangent=tuple(r["tangent"]),
                            square=L <= SQUARE * float(r["width"]) + 0.5))
    return out


def readings_for(G, tag, g):
    """(rungs, source) for one copy: the readings file if there is one, else None"""
    k = key(tag, g)
    p = os.path.join(RDIR, RD.fname(k) + ".readings.json")
    if os.path.exists(p):
        try:
            return rungs_from_readings(json.load(open(p))), "readings file"
        except Exception as e:
            print("  bad readings file", p, repr(e))
    return None, None


def upright_rungs(G, g):
    r, src = readings_for(G, "up", g)
    if r is not None:
        return r, src
    gu = get(G, "up", g)
    P = Parts(gu["contours"], slant=0.0)
    return rungs_from_readings(RD.readings(P, g, gu["master"])), "computed (Parts, upright pairing)"


def project(segs, p):
    best = None
    for si, s in enumerate(segs):
        n = 1 if s.kind == "line" else 32
        ts = np.linspace(0, 1, 33 if s.kind == "curve" else 2)
        if s.kind == "line":
            a, b = s.pts; d = (b[0] - a[0], b[1] - a[1]); L2 = d[0] ** 2 + d[1] ** 2
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * d[0] + (p[1] - a[1]) * d[1]) / L2))
            q = s.point(t); dd = math.dist(p, q)
        else:
            dd, t = min((math.dist(p, s.point(float(tt))), float(tt)) for tt in ts)
            h = 1 / 32
            for _ in range(12):
                cands = [max(0.0, t - h), t, min(1.0, t + h)]
                dd, t = min((math.dist(p, s.point(c)), c) for c in cands)
                h /= 2
        if best is None or dd < best[0]:
            best = (dd, si, t)
    return best


def carry(rungs_up, segs_up, segs_t, k):
    """the upright's rungs on another copy with the same nodes: each end goes to the same node (or the same
    segment parameter for a point between nodes); the stroke direction is the upright's mean tangent carried
    by the shear k (exact for the plain slant; the corrected copy turns its strokes by far less than a degree's
    worth of width); width = |rung x that direction|"""
    out = []
    for r in rungs_up:
        mt = r["tangent"]
        ends = []
        for p, nd in ((r["a"], r["a_node"]), (r["b"], r["b_node"])):
            cands = []
            if nd is not None:
                cands = [(si, 0.0) for si, s in enumerate(segs_up) if s.gi == nd] + \
                        [(si, 1.0) for si, s in enumerate(segs_up) if s.gj == nd]
            if cands:
                si, t = cands[0]
                ends.append(segs_t[si].point(t)); continue
            dd, si, t = project(segs_up, p)
            q_up, q_t = segs_up[si].point(t), segs_t[si].point(t)
            # a point on a hidden continuation (off the drawn outline): sheared, plus the move of the nearest outline point
            dx = q_t[0] - (q_up[0] + k * q_up[1]) if dd > 0.5 else 0.0
            dy = q_t[1] - q_up[1] if dd > 0.5 else 0.0
            ends.append((p[0] + k * p[1] + dx, p[1] + dy) if dd > 0.5 else q_t)
        pa, pb = ends
        m = unit((mt[0] + k * mt[1], mt[1]))
        rx, ry = pb[0] - pa[0], pb[1] - pa[1]
        out.append(dict(r, a=pa, b=pb, width=abs(rx * m[1] - ry * m[0]), tangent=m, up_width=r["width"],
                        cls=dir_class(r["tangent"])))
    return out


def extremes(rungs):
    """{part: (thickest, thinnest)} over measured rungs; rungs under TIP (serif tips, blunt edges) are not ranked"""
    by = {}
    for r in rungs:
        if not measured(r) or r["width"] < TIP:
            continue
        by.setdefault(r["part"], []).append(r)
    return {p: (max(rs, key=lambda r: r["width"]), min(rs, key=lambda r: r["width"])) for p, rs in by.items()}


def class_change(carried):
    acc = {}
    for r in carried:
        if not measured(r) or r["up_width"] < TIP:
            continue
        acc.setdefault(r["cls"], []).append(r["width"] / r["up_width"] - 1)
    parts = []
    for c in ("|", "-", "/", "\\"):
        if c in acc:
            parts.append("%s %+.1f%% (%d)" % (CLS_NAME[c], 100 * float(np.mean(acc[c])), len(acc[c])))
    return "vs upright, same rungs, by stroke direction: " + "  ·  ".join(parts) if parts else "no measured rungs"


def off_ink(flat, r):
    a, b = r["a"], r["b"]
    bad = 0
    for u in (0.2, 0.35, 0.5, 0.65, 0.8):
        q = (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
        if not flat.inside(q) and flat.edge_dist(q) > EDGE_TOL:
            bad += 1
    return bad >= 2


# ---- drawing helpers ----------------------------------------------------------------------------------------
def fixed_panel(w, h, scale, cx, cy, top=44):
    A = Panel(w, h, (0, 0, 1, 1), margin=10)
    A.s = scale * SS
    A.ox = w * SS / 2 - cx * A.s
    A.oy = (h + top) * SS / 2 + cy * A.s
    return A


def metric_lines(A, x0, x1, y0=-1e9, y1=1e9):
    f = font(MENLO, 7)
    for y, lab in METRICS:
        if not y0 - 1 <= y <= y1 + 1:
            continue
        A.line((x0, y), (x1, y), (44, 44, 44) if y else (60, 60, 60), 0.8)
        X, Y = A.pt((x1, y))
        A.d.text((X + 3 * SS, Y - 9 * SS), lab, fill=(85, 85, 85), font=f)


def fill(A, flat, color=INK, edge=EDGE):
    """nonzero fill with skia (overlapping contours stay ink; Panel.fill_outline paints counters over them), then the edges"""
    import skia
    W, H = A.im.size
    path = skia.Path(); path.setFillType(skia.PathFillType.kWinding)
    for c in flat.contours:
        ns = c["nodes"]; N = len(ns)
        ons = [i for i in range(N) if ns[i][2] != "o"]
        if not ons:
            continue
        path.moveTo(*A.pt(ns[ons[0]][:2]))
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [ns[q % N] for q in range(i + 1, i + 1 + ((j - i - 1) % N))]
            if len(offs) == 2 and ns[j][2] != "l":
                path.cubicTo(*A.pt(offs[0][:2]), *A.pt(offs[1][:2]), *A.pt(ns[j][:2]))
            else:
                path.lineTo(*A.pt(ns[j][:2]))
        path.close()
    surf = skia.Surface(W, H)
    cv = surf.getCanvas(); cv.clear(skia.ColorTRANSPARENT)
    cv.drawPath(path, skia.Paint(AntiAlias=True, Color=skia.ColorWHITE))
    alpha = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., 3]
    A.im.paste(color, (0, 0, W, H), Image.fromarray(alpha))
    if edge is not None:
        for poly in flat.polys:
            A.d.line([A.pt(p) for p in poly + [poly[0]]], fill=edge, width=max(1, int(0.8 * SS)))


def outline_only(A, flat, col, w=1.2, dash=None):
    for poly in flat.polys:
        draw_poly(A, poly + [poly[0]], col, w, dash=dash)


def draw_nodes(A, contours, col_on=ON, col_off=OFF):
    nodes = nodes_flat(contours)
    base = 0
    for c in contours:
        ns = c["nodes"]; N = len(ns)
        for i, n in enumerate(ns):
            if n[2] == "o":
                # handle: to the on-curve neighbour it belongs to
                prv, nxt = ns[(i - 1) % N], ns[(i + 1) % N]
                if prv[2] != "o":
                    A.line((prv[0], prv[1]), (n[0], n[1]), col_off, 0.7)
                if nxt[2] != "o":
                    A.line((nxt[0], nxt[1]), (n[0], n[1]), col_off, 0.7)
        base += N
    for n in nodes:
        X, Y = A.pt((n[0], n[1]))
        if n[2] == "o":
            r = 1.8 * SS
            A.d.ellipse([X - r, Y - r, X + r, Y + r], outline=col_off, width=max(1, int(0.8 * SS)))
        else:
            r = 2.2 * SS
            A.d.rectangle([X - r, Y - r, X + r, Y + r], fill=col_on)


def arrow(A, p, q, col, w=2.0, head=7.0):
    A.line(p, q, col, w)
    v = (q[0] - p[0], q[1] - p[1]); L = math.hypot(*v)
    if L < 1e-6:
        return
    ux, uy = v[0] / L, v[1] / L
    hs = head / (A.s / SS)
    for ang in (0.5, -0.5):
        ca, sa = math.cos(ang), math.sin(ang)
        A.line(q, (q[0] - (ux * ca - uy * sa) * hs, q[1] - (ux * sa + uy * ca) * hs), col, w)


def moves(A, c_from, c_to, gain):
    n0, n1 = nodes_flat(c_from), nodes_flat(c_to)
    k = 0; mx = 0.0
    for a, b in zip(n0, n1):
        d = math.dist(a[:2], b[:2]); mx = max(mx, d)
        if d < 1.0:
            continue
        k += 1
        q = (a[0] + (b[0] - a[0]) * gain, a[1] + (b[1] - a[1]) * gain)
        if a[2] == "o":
            arrow(A, (a[0], a[1]), q, tuple(int(c * 0.6) for c in YEL), 1.0, 4.5)
        else:
            arrow(A, (a[0], a[1]), q, YEL, 2.0, 7.0)
    return k, mx


def draw_rungs(A, rungs, flat, labels=True, grey=True, fmt=None):
    """thickest per part orange, thinnest cyan, the rest thin grey; returns the rungs that leave the ink"""
    ex = extremes(rungs)
    hot = {}
    for p, (tk, tn) in ex.items():
        hot[id(tk)] = THICK
        if tn is not tk:
            hot[id(tn)] = THIN
    bad = []
    for r in rungs:
        if not measured(r):
            continue
        oi = off_ink(flat, r)
        if oi:
            bad.append(r)
        if id(r) in hot and not oi:
            continue
        if grey or oi:
            A.line(r["a"], r["b"], OFFINK if oi else REST, 1.6 if oi else 0.6)
    f = font(MENLO, 8)
    for r in rungs:
        col = hot.get(id(r))
        if col is None:
            continue
        if r in bad:
            col = OFFINK
        A.line(r["a"], r["b"], col, 2.0)
        if labels:
            mid = ((r["a"][0] + r["b"][0]) / 2, (r["a"][1] + r["b"][1]) / 2)
            X, Y = A.pt(mid)
            s = fmt(r) if fmt else "%.0f" % r["width"]
            if r["kind"] == "root":
                s += "r"
            tw = A.d.textlength(s, font=f)
            A.d.rectangle([X + 3 * SS, Y - 6 * SS, X + 3 * SS + tw + 2 * SS, Y + 5 * SS], fill=(13, 13, 13))
            A.d.text((X + 4 * SS, Y - 6 * SS), s, fill=col, font=f)
    return bad


def legend(A, items, y=None):
    f = font(MENLO, 8)
    x = 16 * SS; y = (A.h - 18) * SS if y is None else y
    for col, s in items:
        A.d.line([(x, y + 5 * SS), (x + 16 * SS, y + 5 * SS)], fill=col, width=2 * SS)
        A.d.text((x + 20 * SS, y), s, fill=(170, 170, 170), font=f)
        x += 20 * SS + A.d.textlength(s, font=f) + 16 * SS


# ---- dense rungs from the solver's TABLE ---------------------------------------------------------------------
TABLE_P = os.path.join(ROOT, "TABLE_18.json")        # main() picks TABLE_<14|18>.json
DIR_SYM = {"vertical": "|", "horizontal": "-", "/": "/", "\\": "\\"}


def load_table():
    try:
        return json.load(open(TABLE_P))
    except Exception:
        return {}


class Dense:
    """the solver's measurement: node rungs + dense rungs every ~12 u on the UPRIGHT's pairing (italic/tools/carry.py),
    measured on every copy; TABLE.json names each part's thickest / thinnest rung per copy, looked up here by name.
    Raises when the solver's tools or the table entry are missing (the caller falls back to node rungs)."""

    def __init__(self, g, table_rows, contours):
        import carry as SC
        from measure import rung_name, counted
        self.SC, self.counted = SC, counted
        P_up = SC.parts_of({"contours": contours["up"], "master": "Regular", "glyph": g})
        self.R = R = SC.Rungs(P_up)
        self.W = {k: R.widths(c) for k, c in contours.items()}
        self.names = {}
        for i, r in enumerate(R.rungs):
            self.names.setdefault((r["si"], rung_name(r)), i)
        self.rows = table_rows
        self.stale = []
        self.hot = {}                       # tag -> [(index, colour)]
        for tag in ("up", "sl", "it"):
            hot = []
            for ent in table_rows:
                if tag not in ent:
                    continue
                for which, col in (("thickest", THICK), ("thinnest", THIN)):
                    e = ent[tag][which]
                    i = self.names.get((ent["part"], e["rung"]))
                    if i is None or abs(self.W[tag][i]["w"] - e["w"]) > 0.6:
                        self.stale.append("%s part %d %s %s" % (tag, ent["part"], which, e["rung"]))
                        i = self._recompute(ent["part"], tag, which)
                    if i is not None and not any(h[0] == i for h in hot):
                        hot.append((i, col))
            self.hot[tag] = hot
        self.counted_ids = sorted({i for si in range(len(P_up.strokes)) for i in counted(R, self.W["up"], si)})

    def _recompute(self, si, tag, which):
        ids = self.counted(self.R, self.W["up"], si)
        if not ids:
            return None
        f = max if which == "thickest" else min
        return f(ids, key=lambda i: self.W[tag][i]["w"])

    def rung(self, tag, i):
        w = self.W[tag][i]
        return dict(a=w["pa"], b=w["pb"], width=w["w"], kind=self.R.rungs[i]["kind"], part=self.R.rungs[i]["si"])

    def by_direction(self, tag):
        acc = {}
        for ent in self.rows:
            for c, v in ent.get("by_direction", {}).items():
                if tag in v:
                    a = acc.setdefault(c, [0.0, 0])
                    a[0] += v[tag] * v["n"]; a[1] += v["n"]
        parts = []
        for c in ("vertical", "horizontal", "/", "\\"):
            if c in acc and acc[c][1]:
                parts.append("%s %+.1f%% (%d)" % (c, 100 * (acc[c][0] / acc[c][1] - 1), acc[c][1]))
        return "dense rungs vs upright, by stroke direction: " + "  ·  ".join(parts) if parts else "no dense rungs"


def place_label(A, x, y, w, h):
    """first free slot at or below (x, y) among the labels already on this panel"""
    boxes = A.__dict__.setdefault("_boxes", [])
    for _ in range(12):
        if not any(x < bx + bw and bx < x + w and y < by + bh and by < y + h for bx, by, bw, bh in boxes):
            break
        y += h + 1 * SS
    boxes.append((x, y, w, h))
    return x, y


def draw_dense(A, D, tag, flat, labels=True, fmt=None, grey=True, geo_tag=None):
    """grey: every counted rung; orange / cyan: the table's thickest / thinnest of each part. geo_tag = whose
    geometry to draw (defaults to tag); widths labelled by fmt(index) or the tag's own width"""
    gt = geo_tag or tag
    bad = []
    hot = dict(D.hot[tag])
    if grey:
        for i in D.counted_ids:
            if i in hot:
                continue
            r = D.rung(gt, i)
            oi = off_ink(flat, r)
            if oi:
                bad.append(r)
            A.line(r["a"], r["b"], OFFINK if oi else (85, 85, 85), 1.4 if oi else 0.5)
    f = font(MENLO, 8)
    for i, col in D.hot[tag]:
        r = D.rung(gt, i)
        if off_ink(flat, r):
            bad.append(r); col = OFFINK
        A.line(r["a"], r["b"], col, 2.2)
        if labels:
            mid = ((r["a"][0] + r["b"][0]) / 2, (r["a"][1] + r["b"][1]) / 2)
            X, Y = A.pt(mid)
            s = fmt(i) if fmt else "%.0f" % D.W[tag][i]["w"]
            tw = A.d.textlength(s, font=f)
            X, Y = place_label(A, X + 3 * SS, Y - 6 * SS, tw + 2 * SS, 11 * SS)
            A.d.rectangle([X, Y, X + tw + 2 * SS, Y + 11 * SS], fill=(13, 13, 13))
            A.d.text((X + 1 * SS, Y), s, fill=col, font=f)
    return bad


# ---- per-letter sheet ----------------------------------------------------------------------------------------
class Letter:
    def __init__(self, G, g):
        self.g = g
        self.up = get(G, "up", g); self.sl = get(G, "sl", g); self.it = get(G, "it", g)
        self.corrected = self.it is not None
        cu, cs = self.up["contours"], self.sl["contours"]
        ci = self.it["contours"] if self.it else cs
        self.c = {"up": cu, "sl": cs, "it": ci, "bs_it": shear(ci, -K), "bs_sl": shear(cs, -K)}
        self.f = {k: Flat(v) for k, v in self.c.items()}
        self.fallbacks = []
        if not self.corrected:
            self.fallbacks.append("no Italic key: corrected = plain slant (grey)")
        self.r_up, src = upright_rungs(G, g)
        if src != "readings file":
            self.fallbacks.append("upright rungs " + src)
        su = self.f["up"].segs
        self.carried = {k: carry(self.r_up, su, self.f[k].segs, kk) for k, kk in (("sl", K), ("it", K), ("bs_it", 0.0))}
        self.r = {"up": self.r_up}
        for tag in ("sl", "it"):
            r, src = readings_for(G, tag, g) if (tag == "sl" or self.corrected) else (None, None)
            if r is None:
                r = self.carried[tag]
                if tag == "sl" or self.corrected:
                    self.fallbacks.append("%s rungs carried from the upright (no readings file)" % ("slant" if tag == "sl" else "corrected"))
            self.r[tag] = r
        self.D = None
        T = load_table()
        if g in T:
            try:
                self.D = Dense(g, T[g], {k: self.c[k] for k in ("up", "sl", "it", "bs_it")})
                if self.D.stale:
                    self.fallbacks.append("TABLE rungs not found / changed, re-ranked with the solver's rule: %d" % len(self.D.stale))
            except Exception as e:
                self.fallbacks.append("TABLE unusable (%s): node rungs" % repr(e)[:60])
                self.D = None
        else:
            self.fallbacks.append("letter not in TABLE.json: node rungs ranked here")
        bbs = [self.f[k].bbox() for k in ("up", "sl", "it", "bs_it")]
        self.bb = (min(b[0] for b in bbs), min(min(b[1] for b in bbs), 0), max(b[2] for b in bbs), max(max(b[3] for b in bbs), 530))


def letter_sheet(G, g, out_path, W=2400, RH=540, HEAD=44):
    L = Letter(G, g)
    x0, y0, x1, y1 = L.bb
    pad = 40
    wA = W // 3
    scale = min((wA - 2 * 30) / (x1 - x0 + 2 * pad), (RH - HEAD - 2 * 20) / (y1 - y0 + 2 * pad))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    mx0, mx1 = x0 - pad - 60, x1 + pad
    notes = []
    corr_name = "CORRECTED SLANT" if L.corrected else "CORRECTED SLANT · plain slant, not corrected"
    fillcol = {"up": INK, "sl": INK, "it": INK if L.corrected else GREYFILL}
    off = {}

    # Row A
    rowA = []
    for tag, name in (("up", "UPRIGHT"), ("sl", "PLAIN SLANT %.2f°" % ANGLE), ("it", corr_name)):
        A = fixed_panel(wA, RH, scale, cx, cy)
        metric_lines(A, mx0, mx1, y0 - pad, y1 + pad)
        fill(A, L.f[tag], color=fillcol[tag], edge=EDGE)
        if L.D is not None:
            bad = draw_dense(A, L.D, tag, L.f[tag])
            if tag == "up":
                sub = "%d parts · TABLE.json: orange = thickest rung of each part (node + dense rungs every ~12 u), cyan = thinnest" % len(L.D.rows)
            else:
                sub = L.D.by_direction(tag) if (tag == "sl" or L.corrected) else "no Italic key yet: this is the plain slant"
            leg = [((85, 85, 85), "every counted rung (node + dense, the solver's rule; roots and tips left out)")]
        else:
            bad = draw_rungs(A, L.r[tag], L.f[tag])
            if tag == "up":
                sub = "%d parts · node rungs only (no TABLE entry) · orange = thickest, cyan = thinnest" % len(extremes(L.r_up))
            else:
                sub = class_change(L.carried[tag]) if (tag == "sl" or L.corrected) else "no Italic key yet: this is the plain slant"
            leg = [(REST, "other rungs; serif tips < %d u not ranked; r = square end rung at a part's root" % TIP)]
        off[tag] = bad
        A.title(name, sub)
        legend(A, leg + ([(OFFINK, "%d rung%s leave the ink" % (len(bad), "" if len(bad) == 1 else "s"))] if bad else []))
        rowA.append(A)

    # Row B
    wB = W // 2
    gain = 4
    B1 = fixed_panel(wB, RH, scale, cx, cy)
    metric_lines(B1, mx0, mx1, y0 - pad, y1 + pad)
    fill(B1, L.f["sl"], color=INK, edge=(70, 80, 60))
    outline_only(B1, L.f["it"], BRIGHT if L.corrected else (150, 150, 150), 1.2)
    draw_nodes(B1, L.c["it"])
    k, mxd = moves(B1, L.c["sl"], L.c["it"], gain)
    B1.title("SUPERIMPOSED · plain slant filled, %s outlined" % ("corrected" if L.corrected else "corrected = plain slant (not corrected)"),
             "yellow = node move slant → corrected, drawn ×%d · %d node%s move ≥ 1 u · largest %.1f u" % (gain, k, "" if k == 1 else "s", mxd))
    B2 = fixed_panel(wB, RH, scale, cx, cy)
    metric_lines(B2, mx0, mx1, y0 - pad, y1 + pad)
    fill(B2, L.f["it"], color=INK if L.corrected else GREYFILL, edge=(70, 80, 60))
    outline_only(B2, L.f["sl"], BRIGHT, 1.2)
    draw_nodes(B2, L.c["sl"])
    moves(B2, L.c["sl"], L.c["it"], gain)
    B2.title("SUPERIMPOSED · roles swapped: corrected filled, plain slant outlined",
             "white squares = on-curve nodes of the outline, blue = handles · yellow = move ×%d" % gain)

    # Row C
    C1 = fixed_panel(wB, RH, scale, cx, cy)
    metric_lines(C1, mx0, mx1, y0 - pad, y1 + pad)
    fill(C1, L.f["up"], color=DIMUP, edge=(70, 70, 70))
    outline_only(C1, L.f["bs_it"], BRIGHT if L.corrected else (150, 150, 150), 1.3)
    if L.D is not None:
        D = L.D
        draw_dense(C1, D, "up", L.f["up"], grey=False, fmt=lambda i: "up %.0f · bs %.0f" % (D.W["up"][i]["w"], D.W["bs_it"][i]["w"]))
        dif = [(abs(D.W["bs_it"][i]["w"] - D.W["up"][i]["w"]), i) for i, _ in D.hot["up"]]
    else:
        bsr = {id(r0): r for r0, r in zip(L.r_up, L.carried["bs_it"])}
        ex = extremes(L.r_up)
        hot = [r for p, pair in ex.items() for r in pair]
        draw_rungs(C1, L.r_up, L.f["up"], grey=False,
                   fmt=lambda r: "up %.0f · bs %.0f" % (r["width"], bsr[id(r)]["width"]))
        dif = [(abs(bsr[id(r)]["width"] - r["width"]), r) for r in hot if measured(r)]
    # the worst mismatch on the thick/thin rungs
    worst = max(dif, key=lambda d: d[0]) if dif else (0, None)
    C1.title("ACCEPTANCE · %s back-slanted (x − %s) over the upright" % ("corrected" if L.corrected else "plain slant (not corrected)", YK),
             "upright filled dim · outline = back-slanted %s · rungs = the upright's thickest / thinnest: up = upright width, bs = back-slanted width · worst %.1f u"
             % ("corrected" if L.corrected else "slant", worst[0]))
    C2 = fixed_panel(wB, RH, scale, cx, cy)
    metric_lines(C2, mx0, mx1, y0 - pad, y1 + pad)
    fill(C2, L.f["bs_sl"], color=INK, edge=EDGE)
    if L.D is not None:
        draw_dense(C2, L.D, "up", L.f["up"], grey=True)
    else:
        draw_rungs(C2, L.r_up, L.f["up"], grey=True)
    C2.title("REFERENCE · plain slant back-slanted = upright",
             "the shear undone is the upright itself: its thickest / thinnest rungs are the target for the panel on the left")

    sheet = Image.new("RGB", (W, HEAD + 3 * RH + 2 * 6), BG)
    d = ImageDraw.Draw(sheet)
    d.text((16, 10), "GEIST SERIF  Regular → italic %.2f° (x' = x + %s)  ·  /%s  ·  round 5 · pass 2" % (ANGLE, YK, g), fill=LBL_ON,
           font=ImageFont.truetype(CAL, 20))
    fb = "; ".join(L.fallbacks) if L.fallbacks else "all from the solver's files"
    d.text((W - 16, 14), "rows A/B/C share one scale · " + fb, fill=(150, 150, 150) if L.fallbacks else (120, 120, 120),
           font=ImageFont.truetype(CAL, 13), anchor="ra")
    for i, A in enumerate(rowA):
        sheet.paste(A.out(), (i * wA, HEAD))
    for i, A in enumerate((B1, B2)):
        sheet.paste(A.out(), (i * wB, HEAD + RH + 6))
    for i, A in enumerate((C1, C2)):
        sheet.paste(A.out(), (i * wB, HEAD + 2 * (RH + 6)))
    # thin separators
    for y in (HEAD + RH + 2, HEAD + 2 * RH + 8):
        d.line([(0, y), (W, y)], fill=(40, 40, 40), width=2)
    for x in (wA, 2 * wA):
        d.line([(x, HEAD), (x, HEAD + RH)], fill=(40, 40, 40), width=2)
    for x in (wB,):
        d.line([(x, HEAD + RH + 6), (x, HEAD + 3 * RH + 12)], fill=(40, 40, 40), width=2)
    sheet.save(out_path)
    return L, off, worst


# ---- overview -----------------------------------------------------------------------------------------------
def overview(G, letters, out_path, CW=280, CH=310):
    SW = CW * 3 + 8
    per = 4
    rows = math.ceil(len(letters) / per)
    HEAD = 74
    sheet = Image.new("RGB", (SW * per + 10 * (per + 1), HEAD + rows * (CH + 10) + 10), BG)
    d = ImageDraw.Draw(sheet)
    d.text((12, 10), "GEIST SERIF %.2f° · UPRIGHT | PLAIN SLANT | CORRECTED round 5 · pass 2 (plain slant dashed under it)" % ANGLE,
           fill=LBL_ON, font=ImageFont.truetype(CAL, 30))
    nc = [g for g in letters if get(G, "it", g) is None]
    d.text((12, 46), ("not corrected yet (grey, plain slant): " + " ".join(nc)) if nc else "every letter corrected",
           fill=(160, 160, 160), font=ImageFont.truetype(CAL, 18))
    for i, g in enumerate(letters):

        up, sl, it = get(G, "up", g), get(G, "sl", g), get(G, "it", g)
        fs = {"up": Flat(up["contours"]), "sl": Flat(sl["contours"]), "it": Flat((it or sl)["contours"])}
        bbs = [f.bbox() for f in fs.values()]
        bb = (min(b[0] for b in bbs) - 30, min(min(b[1] for b in bbs), -150) - 20, max(b[2] for b in bbs) + 30, max(max(b[3] for b in bbs), 800) + 20)
        strip = Image.new("RGB", (SW, CH), BG)
        for j, (tag, name) in enumerate((("up", "upright"), ("sl", "slant"), ("it", "corrected" if it else "not corrected"))):
            A = Panel(CW, CH, bb, margin=14)
            A.title("/%s · %s" % (g, name))
            col = (60, 70, 50) if tag == "up" else ((78, 88, 64) if (tag == "sl" or it) else (70, 70, 70))
            fill(A, fs[tag], color=col, edge=(150, 150, 150))
            if tag == "it":
                outline_only(A, fs["sl"], (230, 230, 230), 0.9, dash=5)
            strip.paste(A.out(), (j * (CW + 4), 0))
        sheet.paste(strip, (10 + (i % per) * (SW + 10), HEAD + (i // per) * (CH + 10)))
    sheet.save(out_path)


# ---- the word proof -----------------------------------------------------------------------------------------
PAGE_W, PAD, LABELW = 1640, 56, 250
PITCH = (2122 - 124 - 56) / 7
S = 0.125
LINE = int(710 * S * 1.55)
LINES = ["Harper’s Bazzar", "Rolling Stone"]
GNAME = {"’": "quoteright", " ": "space"}
GEIST = os.path.expanduser("~/Library/Fonts/Geist-VariableFont_wght.ttf")


def load_kern():
    if not os.path.exists(KERN):
        return {}, False
    try:
        raw = json.load(open(KERN))
    except Exception:
        return {}, False
    out = {}
    if isinstance(raw, dict) and "pairs" in raw and isinstance(raw["pairs"], (dict, list)):
        raw = raw["pairs"]
    if isinstance(raw, list):
        for row in raw:
            out[(row[0], row[1])] = float(row[2])
    else:
        for k, v in raw.items():
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    out[(k, k2)] = float(v2)
            else:
                a, b = re.split(r"[ ,|/]+", k.strip(), maxsplit=1)
                out[(a, b)] = float(v)
    return out, True


_adv = {}


def pkg_advance(gname):
    """advance of a glyph that is not in the JSON: the Regular master layer of the .glyphspackage (read-only)"""
    if gname in _adv:
        return _adv[gname]
    fn = "".join(c + "_" if c.isupper() else c for c in gname) + ".glyph"
    w = None
    p = os.path.join(GPKG, "glyphs", fn)
    if os.path.exists(p):
        t = open(p).read()
        i = t.find(REGULAR_MASTER_ID)
        if i >= 0:
            m = re.search(r"\nwidth = (\d+(?:\.\d+)?);", t[i:])
            if m:
                w = float(m.group(1))
    _adv[gname] = w if w is not None else 600.0
    return _adv[gname]


def skia_path(contours, ox, oy, sx, k):
    import skia
    path = skia.Path(); path.setFillType(skia.PathFillType.kWinding)
    tr = lambda p: (ox + (p[0] + k * p[1]) * sx, oy - p[1] * sx)
    for c in contours:
        ns = c["nodes"]; N = len(ns)
        ons = [i for i in range(N) if ns[i][2] != "o"]
        if not ons:
            continue
        path.moveTo(*tr(ns[ons[0]]))
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [ns[q % N] for q in range(i + 1, i + 1 + ((j - i - 1) % N))]
            P1 = tr(ns[j])
            if len(offs) == 2 and ns[j][2] != "l":
                path.cubicTo(*tr(offs[0]), *tr(offs[1]), *P1)
            elif len(offs) == 1:
                path.quadTo(*tr(offs[0]), *P1)
            else:
                path.lineTo(*P1)
        path.close()
    return path


def word_page(G, out_path, back=False, scale=2, ss=2, lines=None, size=None):
    global LINES, S
    saved = LINES, S
    if lines is not None:
        LINES = lines
    if size is not None:
        S = size
    try:
        return _word_page(G, out_path, back, scale, ss)
    finally:
        LINES, S = saved


def _word_page(G, out_path, back=False, scale=2, ss=2):
    import skia
    kern, have_kern = load_kern()
    rows = [("up", 0.0), ("sl", K), ("it", K)]
    H = int(math.ceil(124 + PITCH * 3 + PAD))
    R = scale * ss
    surf = skia.Surface(PAGE_W * R, H * R)
    cv = surf.getCanvas()
    cv.clear(skia.ColorWHITE)
    paint = lambda rgb: skia.Paint(AntiAlias=True, Color=skia.Color(*rgb))
    missing, notcorr = set(), set()
    drawn_lines = []
    for li, line in enumerate(LINES):
        names = [GNAME.get(ch, ch) for ch in line]
        ok = all(n == "space" or get(G, "up", n) is not None for n in names)
        if li == 0 or ok:
            drawn_lines.append((li, line, names))
    for r, (tag, k) in enumerate(rows):
        last = 124 + PITCH * (r + 1) - 30
        first = last - (len(LINES) - 1) * LINE
        kk = k - K if (back and r > 0) else k
        for li, line, names in drawn_lines:
            base = first + li * LINE
            x = 0.0; prev = None
            for n in names:
                if prev is not None:
                    x += kern.get((prev, n), 0.0)
                gu = get(G, "up", n)
                if n == "space":
                    adv = (gu or {}).get("width") or pkg_advance("space")
                    x += adv; prev = n; continue
                if gu is None:
                    missing.add(n)
                    adv = pkg_advance(n)
                    # placeholder: a dotted x-height box over the advance
                    ox = (326 + x * S) * R; oy = base * R
                    pnt = skia.Paint(AntiAlias=True, Color=skia.Color(200, 200, 200), Style=skia.Paint.kStroke_Style,
                                     StrokeWidth=1.0 * R, PathEffect=skia.DashPathEffect.Make([3 * R, 3 * R], 0))
                    sh = (kk * 530) * S * R
                    pth = skia.Path(); pth.moveTo(ox + 20 * S * R, oy); pth.lineTo(ox + (adv - 20) * S * R, oy)
                    pth.lineTo(ox + (adv - 20) * S * R + sh, oy - 530 * S * R); pth.lineTo(ox + 20 * S * R + sh, oy - 530 * S * R); pth.close()
                    cv.drawPath(pth, pnt)
                    x += adv; prev = n; continue
                col = (17, 17, 17)
                if tag == "up":
                    cont = gu["contours"]
                elif tag == "sl":
                    cont = gu["contours"]          # sheared by the transform: the page's own construction
                else:
                    gi = get(G, "it", n)
                    if gi is None:
                        notcorr.add(n); cont = gu["contours"]; col = (166, 166, 166)
                    else:
                        cont = shear(gi["contours"], -K)   # the corrected drawing is already slanted
                cv.drawPath(skia_path(cont, (326 + x * S) * R, base * R, S * R, kk), paint(col))
                x += gu["width"]; prev = n
    img = Image.fromarray(surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3].copy())
    img = img.resize((PAGE_W * scale, H * scale), Image.LANCZOS)
    # labels, rules (PIL at 2x)
    d = ImageDraw.Draw(img)
    def gf(size, wght):
        f = ImageFont.truetype(GEIST if os.path.exists(GEIST) else CAL, int(size * scale))
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
        return f
    X = lambda v: v * scale
    d.text((X(PAD), X(70)), "Geist Serif  ·  Regular → Italic", fill=(17, 17, 17), font=gf(34, 700), anchor="ls")
    d.text((X(PAGE_W - PAD), X(70)), "wght 400 · 1×%s = %.2f° · round 5 · pass 2" % (YK.split("/")[1], ANGLE), fill=(119, 119, 119), font=gf(18, 400), anchor="rs")
    sub = ("Italic proof  ·  rows 2 and 3 BACK-SLANTED by x − %s: the plain slant becomes the upright again; the corrected row shows what the correction did" % YK
           if back else "Italic proof  ·  plain slant = the decomposed Regular sheared 1×%s  ·  corrected = round 5 · pass 2 (two-angle shear, rigid spine piece, terminals ride, arm serifs sheared, I13 widths, harmonized)" % YK.split("/")[1])
    d.text((X(PAD), X(102)), sub, fill=(119, 119, 119), font=gf(15, 400), anchor="ls")
    d.line([(X(PAD), X(124)), (X(PAGE_W - PAD), X(124))], fill=(204, 204, 204), width=scale)
    labels = [("upright", None, None),
              ("%.2f°" % ANGLE, "plain slant" + (", back-slanted = upright" if back else ""), None),
              ("%.2f°" % ANGLE, "corrected" + (", back-slanted" if back else ""),
               ("grey = not corrected: " + " ".join("’" if n == "quoteright" else n for n in sorted(notcorr))) if notcorr else None)]
    for r, (a, b, c) in enumerate(labels):
        last = 124 + PITCH * (r + 1) - 30
        d.line([(X(PAD + LABELW), X(last + 18)), (X(PAGE_W - PAD), X(last + 18))], fill=(230, 230, 230), width=scale)
        if b is None:
            d.text((X(PAD), X(last - 24)), a, fill=(68, 68, 68), font=gf(20, 400), anchor="ls")
            continue
        d.text((X(PAD), X(last - 52)), a, fill=(17, 17, 17), font=gf(24, 700), anchor="ls")
        bl = b.split(", ")
        d.text((X(PAD), X(last - 24)), bl[0], fill=(68, 68, 68), font=gf(20, 400), anchor="ls")
        if len(bl) > 1:
            d.text((X(PAD), X(last - 4)), bl[1], fill=(120, 120, 120), font=gf(14, 400), anchor="ls")
        if c:
            d.text((X(PAD), X(last + 12)), c, fill=(150, 150, 150), font=gf(13, 400), anchor="ls")
        if not back:
            u = 9; tx = PAD + LABELW - 50
            d.polygon([(X(tx), X(last)), (X(tx + u), X(last)), (X(tx + u), X(last - u / K))], outline=(204, 0, 0), width=max(1, int(1.2 * scale)))
    if missing:
        d.text((X(PAGE_W - PAD), X(H - 20)), "dotted box = glyph not in the source yet: " + " ".join(sorted(missing)),
               fill=(150, 150, 150), font=gf(13, 400), anchor="rs")
    if not have_kern:
        d.text((X(PAD), X(H - 20)), "no kerning.json: kerning 0", fill=(150, 150, 150), font=gf(13, 400), anchor="ls")
    img.save(out_path)
    return dict(missing=sorted(missing), not_corrected=sorted(notcorr), kern=have_kern,
                lines=[l for _, l, _ in drawn_lines])


# ---- CLI ----------------------------------------------------------------------------------------------------
def parse_letters(arg, G):
    have = letters_in(G)
    if arg in (None, "all"):
        return have
    if "," in arg:
        want = [a.strip() for a in arg.split(",") if a.strip()]
    elif arg in have:
        want = [arg]
    else:
        want = list(arg)
    return [g for g in want if g in have]


def main():
    global SRC, RDIR, K, ANGLE, YK, TAG, TABLE_P
    K = _C.set_slant(_C.parse_slant(sys.argv))
    ANGLE = math.degrees(math.atan(K))
    from fractions import Fraction
    YK = "y/%d" % Fraction(K).limit_denominator(12).denominator
    TAG = "14" if abs(K - 0.25) < 1e-9 else "18"
    SRC = _C.SRC; RDIR = os.path.join(ROOT, "readings", TAG); TABLE_P = os.path.join(ROOT, "TABLE_%s.json" % TAG)
    ap = argparse.ArgumentParser()
    ap.add_argument("letters", nargs="?", default="all")
    ap.add_argument("--out", default=os.path.join(ROOT, "sheets"))
    ap.add_argument("--no-letters", action="store_true")
    a = ap.parse_args(_C.strip_slant(sys.argv[1:]))
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    G = load()
    letters = parse_letters(a.letters, G)
    print("letters:", " ".join(letters), "· slant %.2f°" % ANGLE)
    suf = "" if TAG == "18" else "_" + TAG
    if not a.no_letters:
        for g in letters:
            out = os.path.join(a.out, RD.fname(key("it", g)).replace(TAGS["it"] + "_", "") + "_italic%s.png" % suf)
            L, off, worst = letter_sheet(G, g, out)
            offs = {t: len(v) for t, v in off.items() if v}
            print("  %-11s %s%s · acceptance worst %.1f u%s" % (g, "corrected" if L.corrected else "NOT corrected",
                  (" · fallbacks: " + "; ".join(L.fallbacks)) if L.fallbacks else "", worst[0],
                  (" · off-ink rungs " + str(offs)) if offs else ""))
    allL = letters_in(G)
    overview(G, allL, os.path.join(a.out, "overview_italic_%s.png" % TAG))
    print("  overview:", len(allL), "letters")
    for back, name, lines in ((False, "word_harpers_%s.png" % TAG, None), (True, "word_harpers_%s_backslant.png" % TAG, None),
                              (False, "word_saopne_%s.png" % TAG, ["saopne"])):
        info = word_page(G, os.path.join(a.out, name), back=back, lines=lines, size=0.19 if lines else None)
        print("  %s %s" % (name, info))
    print("done in %.1f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
