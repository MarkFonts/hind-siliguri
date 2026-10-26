"""Mark's drawn roman + italic s a (a.alt) o p n e (src/mark_saopne_pdf_paths.json, his Glyphs print PDF of 2026-10-25,
170 pt, drawn at 14.04 deg = x + y/4) as contours in our node format, font units, each letter on its own origin.

  letter(gl, row)      -> {"contours", "glyph", "master"} in font units; the x origin is the letter's pen position on
                          the printed line (see ORIGIN below), y = 0 on the row's baseline
  path(contours, ...)  -> skia path (nonzero: overlapping contours are one ink, as the font renders them)
  mask / xor_pct       -> raster comparison (1 px = 1/PPU u)

ORIGIN. The roman row is set with the Regular's advances and kerning: every drawn roman letter lies on the JSON Regular
within 0.5 u once its pen position is known, and the pen positions step by advance + kern (s a +4, a o 0, o p -5,
p n -20, n e -10 u). The italic row is the same line with a.alt inserted after the a; its pen positions are recovered
from the STEMS (stems do not move except as a block, FINDINGS step 4): p's and n's stems for o p n e (one shift for the
four), the a's stem for s a. Both shifts are reported by `origins()`; nothing is aligned by bbox centre.

UNFINISHED (Mark, 2026-10-25): the drawn italic e and n were not corrected yet. They are drawn for the record only:
no parameter is fitted from them and round 5 is not scored against them (FIT_LETTERS).
"""
import os, json, math
import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
R5 = os.path.abspath(os.path.join(HERE, ".."))            # round 5 · pass 2
PATHS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "src", "mark_saopne_pdf_paths.json"))   # italic/src (read only)
FIT_LETTERS = ("o", "p", "s", "a")        # e and n: unfinished drawings, reference only
UNFINISHED = ("e", "n")
_D = None


def data():
    global _D
    if _D is None:
        _D = json.load(open(PATHS))
    return _D


def _smooth(nodes):
    """mark an on-curve node smooth when its two tangents are within 3 deg (the drawings' 'v'/'c' ops carry no flag)"""
    N = len(nodes)
    for i, n in enumerate(nodes):
        if n[2] == "o":
            continue
        a = nodes[(i - 1) % N]; b = nodes[(i + 1) % N]
        u = (n[0] - a[0], n[1] - a[1]); v = (b[0] - n[0], b[1] - n[1])
        lu, lv = math.hypot(*u), math.hypot(*v)
        if lu < 1e-6 or lv < 1e-6 or (a[2] != "o" and b[2] != "o"):
            n[3] = False; continue
        n[3] = (u[0] * v[0] + u[1] * v[1]) / (lu * lv) > math.cos(math.radians(3.0))
    return nodes


_BASEFIX = {}


def base_fix(row):
    """the PDF's italic baseline_pt (192.32) sits 4.0 u high: on it the drawn n's feet stand at y = +4 and the p's
    descender foot at -196. The fix puts the flat feet of n (0) and p (-200) back on their lines, as in the roman row
    (where both read 0 / -200 exactly)."""
    if row not in _BASEFIX:
        _BASEFIX[row] = 0.0
        lo_n = min(n[1] for c in raw_contours("n", row) for n in c["nodes"] if n[2] != "o")
        lo_p = min(n[1] for c in raw_contours("p", row) for n in c["nodes"] if n[2] != "o")
        _BASEFIX[row] = -((lo_n - 0.0) + (lo_p + 200.0)) / 2.0
    return _BASEFIX[row]


def raw_contours(gl, row):
    """font units, x = PDF x (not yet on the letter's origin), y on the row's baseline (base_fix applied)"""
    D = data(); U = D["units_per_pt"]; P = D["paths"]
    base = D["baseline_pt"][row] - _BASEFIX.get(row, 0.0) / U if row in _BASEFIX else None
    if base is None:
        base_fix(row); base = D["baseline_pt"][row] - _BASEFIX[row] / U
    out = []
    for i in D["letters"][row][gl]:
        nodes = []; start = None; cur = None
        for q in P[i]:
            if q[0] == "m":
                start = cur = q[1]; nodes.append([q[1][0] * U, (q[1][1] - base) * U, "l", False])
            elif q[0] == "l":
                cur = q[1]; nodes.append([q[1][0] * U, (q[1][1] - base) * U, "l", False])
            elif q[0] == "c":
                c1 = q[1] if q[1] else cur
                nodes.append([c1[0] * U, (c1[1] - base) * U, "o", False])
                nodes.append([q[2][0] * U, (q[2][1] - base) * U, "o", False])
                nodes.append([q[3][0] * U, (q[3][1] - base) * U, "c", False]); cur = q[3]
        # the closing duplicate: the last on-curve sits on the start point -> the start node goes, the last takes its place
        if len(nodes) > 1 and math.dist(nodes[0][:2], nodes[-1][:2]) < 0.05 * U:
            nodes.pop(0)
        elif nodes and nodes[0][2] == "l":
            pass                                    # closed by an implicit line back to the start
        out.append({"closed": True, "nodes": _smooth(nodes)})
    return out


def shift(contours, dx, dy=0.0):
    return [{"closed": c["closed"], "nodes": [[n[0] + dx, n[1] + dy] + list(n[2:]) for n in c["nodes"]]} for c in contours]


def path(contours, xf=None):
    p = skia.Path(); p.setFillType(skia.PathFillType.kWinding)
    xf = xf or (lambda q: (q[0], q[1]))
    for c in contours:
        ns = c["nodes"]; N = len(ns)
        ons = [i for i in range(N) if ns[i][2] != "o"]
        if not ons:
            continue
        p.moveTo(*xf(ns[ons[0]]))
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [ns[q % N] for q in range(i + 1, i + 1 + ((j - i - 1) % N))]
            if len(offs) == 2:
                p.cubicTo(*xf(offs[0]), *xf(offs[1]), *xf(ns[j]))
            else:
                p.lineTo(*xf(ns[j]))
        p.close()
    return p


PPU = 2.0          # raster px per unit for XOR


def mask(contours, box, ppu=PPU):
    x0, y0, x1, y1 = box
    W, H = int((x1 - x0) * ppu) + 2, int((y1 - y0) * ppu) + 2
    s = skia.Surface(W, H); c = s.getCanvas(); c.clear(skia.ColorBLACK)
    c.translate(-x0 * ppu, y1 * ppu); c.scale(ppu, -ppu)
    c.drawPath(path(contours), skia.Paint(Color=skia.ColorWHITE, AntiAlias=False))
    return s.makeImageSnapshot().toarray()[..., 0] > 127


def box_of(*cs, pad=40):
    xs = [n[0] for C in cs for c in C for n in c["nodes"]]; ys = [n[1] for C in cs for c in C for n in c["nodes"]]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def xor_pct(cand, ref, band=None, xband=None):
    """area(cand XOR ref) / area(ref) x 100, optionally inside a y band / x band (font units)"""
    b = box_of(cand, ref)
    A, B = mask(cand, b), mask(ref, b)
    if band or xband:
        H, W = A.shape
        yy = b[3] - (np.arange(H) + 0.5) / PPU; xx = b[0] + (np.arange(W) + 0.5) / PPU
        m = np.ones_like(A)
        if band: m &= ((yy >= band[0]) & (yy <= band[1]))[:, None]
        if xband: m &= ((xx >= xband[0]) & (xx <= xband[1]))[None, :]
        A, B = A & m, B & m
    return 100.0 * np.logical_xor(A, B).sum() / max(1, B.sum())


def best_dx(cand, ref, band=None, xband=None, lo=-80, hi=80):
    """the x shift of cand that minimises its XOR against ref (inside the band): coarse 2 u, then 0.25 u"""
    f = lambda d: xor_pct(shift(cand, d), ref, band, xband)
    xs = np.arange(lo, hi + 0.1, 2.0); v = [f(d) for d in xs]; d0 = xs[int(np.argmin(v))]
    xs = np.arange(d0 - 2, d0 + 2.01, 0.25); v = [f(d) for d in xs]
    return float(xs[int(np.argmin(v))]), float(min(v))


# ---- placing a drawn letter in the solver's frame -------------------------------------------------------------
ROMAN_ORDER = ["s", "a", "o", "p", "n", "e"]
STEM_BAND = {"p": ((-150, -60), None), "n": ((60, 330), None), "a": ((60, 330), 0.62)}


def _corners(P):
    """mark_vectors.py's held terminal corners: the lowest-left and highest-right on-curve nodes"""
    lo = min(P, key=lambda p: p[1] - 0.2 * p[0]); hi = max(P, key=lambda p: p[1] + 0.2 * p[0]); return lo, hi


def _mid_centre(cs, y):
    """the midpoint of a closed outline's ink extent on the scanline y (the o's centre at mid-height)"""
    from skia import Path
    b = box_of(cs, pad=2); M = mask(cs, b, ppu=4.0)
    r = int(round((b[3] - y) * 4.0)); xs = np.nonzero(M[r])[0]
    return b[0] + (xs.min() + xs.max() + 1) / 2.0 / 4.0


def placement(gl, row, frame):
    """the x shift that puts Mark's drawn letter (raw PDF x) into `frame` (contours of the same letter in our units:
    the Regular for the roman row, the PLAIN SLANT x + y/4 for the italic row). Returns (dx, method).
      roman             the same outline: the XOR optimum (s against the s with its spine anchors)
      italic p n a      by the STEMS (stems do not move except as a block): XOR optimum inside a stem band
      italic s          by the held terminal corners (mark_vectors.py)
      italic o e        by the centre at mid-height (x 265): a round part's centre stays where the shear puts it
      italic a.alt      by its stem against the a's (its pen position is not known)"""
    dr = raw_contours(gl, row)
    x0 = min(n[0] for c in dr for n in c["nodes"]) - min(n[0] for c in frame for n in c["nodes"])
    if row == "roman":
        d, e = best_dx(shift(frame, x0), dr, lo=-8, hi=8)
        return -(x0 + d), "same outline, XOR optimum (%.2f %%)" % e
    if gl in STEM_BAND or gl == "a.alt":
        band, xf = STEM_BAND.get(gl, STEM_BAND["a"])
        if gl == "a.alt":
            band, xf = (60, 330), 0.55
        ins = lambda C: [n for c in C for n in c["nodes"] if band[0] <= n[1] <= band[1]]
        x0 = min(n[0] for n in ins(dr)) - min(n[0] for n in ins(frame))
        xb = None
        if xf is not None:
            xs = [n[0] for c in frame for n in c["nodes"]]
            xb = (x0 + min(xs) + xf * (max(xs) - min(xs)), x0 + max(xs) + 80)
        d, e = best_dx(shift(frame, x0), dr, band=band, xband=xb, lo=-40, hi=40)
        return -(x0 + d), "stems (band y %d..%d%s, XOR there %.1f %%)" % (band[0], band[1], ", right part" if xb else "", e)
    if gl == "s":
        on = lambda C: [(n[0], n[1]) for c in C for n in c["nodes"] if n[2] != "o"]
        (a0, a1), (b0, b1) = _corners(on(frame)), _corners(on(dr))
        return ((a0[0] - b0[0]) + (a1[0] - b1[0])) / 2, "held terminal corners"
    y = 265.0
    return _mid_centre(frame, y) - _mid_centre(dr, y), "centre at mid-height (y %.0f)" % y


def letter(gl, row, frame):
    """Mark's drawn letter placed in `frame` (see placement)"""
    dx, how = placement(gl, row, frame)
    return {"contours": shift(raw_contours(gl, row), dx), "glyph": gl, "master": "drawn " + row, "placed": how, "dx": dx}
