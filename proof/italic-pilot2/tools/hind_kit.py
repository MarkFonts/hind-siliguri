"""PILOT 2 (2026-10-26). Changes from pilot 1, Mark's settled rules with the Frutiger outtake's numbers:
  - terminals "shear": every cut is carried by the shear (parallel to the stems), never turned back to the roman angle
  - beta by part and master (theta fractions, + = back against the slant):
      closed free round   lc/bn Light 0.40, Bold 0.32 (Frutiger 55 0.43 / 65 0.32); caps 0.33
      bowl with a counter lc Light 0.36, Bold 0.25; Bangla loops Light 0.40, Bold 0.30; caps 0 (Frutiger ~0.05)
      open arc            lc -0.18 (c, a hood); caps -0.24 Light, -0.50 Bold (C G); Bangla 0 (no chord rule yet)
  - I13 '/' diagonals take the roman perpendicular width in full (pilot 1: halfway); the vertical class is narrowed
    from 22.5 deg to 3 deg, so steep diagonals (v w y) keep their perpendicular width too
  - arches (an open part with no free terminal: n m h u shoulders) take the bowl beta, like p q (Mark)
  - counters of back-leaning rounds lean back less than their outside (COUNTER_DBETA) so I13's 45-degree thickness lands
  - Bangla keeps the kit's I13, no arch rule, no counter offset, and leans back only parts that close a counter
  - a bowl drawn over its stem (b d p q) follows the stem at the joins and leans fully only at the far side
  - psi 1.20 (s spine with the slant 0.2 theta)

Pilot 1's notes follow.

Hind Siliguri italic pilot: round 5 pass 2c's STRUCTURE (copied kit in ../kit, unmodified files) with Hind's numbers.

  - shear K = 1/4 (14.04 deg). The kit shears about y = 0; the result is translated by -K * 253.5 afterwards, so the
    italic is the shear about the middle of the x-height (every rule is translation-equivariant in x).
  - master_info / stem_of: Hind's measured stems and metric lines, per master and per class (lc, uc, bn).
  - PRE-LEAN beta per round part (the back-slant study's medians), as rho = 1 - beta/theta in I10:
      closed free round (a part whose outer run is a whole round contour): beta 0.22 theta (lc, figures, Bangla), 0.36 theta (caps)
      every other round part (bowl on a stem or stroke, Bangla loops, open arcs): beta 0 -> plain shear
  - nu = 0 (no narrowing, scale 1.0), psi = 1.25 (spine turned with the slant), serifs n/a (sheared), terminals class "a",
    I13 thickness by direction ON with re-tension, harmonizer last, then comb_p2.repair, then the comb gate.
"""
import sys, os, json, math, copy, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__)); PILOT = os.path.dirname(HERE)
KIT = os.path.join(PILOT, "kit", "italic", "r5", "pass2", "tools")
sys.path.insert(0, KIT); sys.path.insert(0, os.path.join(PILOT, "kit", "italic", "r5", "solver"))
import numpy as np
import carry as C
C.set_slant(0.25)
import skeleton as SK
from skeleton import Map
import round_p2
from comb_p2 import hump, repair
import comb_p2


def _g2_repair_guarded(cs, up_cs, _orig=comb_p2.g2_repair):
    """pilot 2: the kit's G2 repair divides by handle length; a retracted handle (the curved ink traps at v w y's
    vertices) made NaN outlines. When it would, the glyph keeps its unrepaired curves and the gate judges them."""
    keep = copy.deepcopy(cs)
    with np.errstate(all="ignore"):
        out, rep = _orig(cs, up_cs)
    if all(math.isfinite(n[0]) and math.isfinite(n[1]) for c in out for n in c["nodes"]):
        return out, rep
    return keep, []


comb_p2.g2_repair = _g2_repair_guarded
import curvcomb

K = 0.25; YC = 253.5; SHIFT = -K * YC
THETA = math.atan(K)
BETA = {  # (closed free round, bowl with a counter, open arc) per class, per master
    "Light": {"lc": (0.40, 0.36, -0.18), "bn": (0.40, 0.40, 0.0), "uc": (0.33, 0.0, -0.24)},
    "Bold":  {"lc": (0.32, 0.25, -0.18), "bn": (0.32, 0.30, 0.0), "uc": (0.33, 0.0, -0.50)},
}
PSI = 1.20
# counter lean offset (theta fractions): a backward-leaning round's counter leans back this much LESS than its outside, so
# the thickness at the 45 deg places comes back to the roman's (I13 + re-tension alone recovered about half; Hind's o
# measured: Light -0.15 -> 45/135/225/315 within 2 %, Bold -0.30 -> within 1 %). Only where the part leans back (beta > 0).
COUNTER_DBETA = {"Light": 0.0, "Bold": 0.0}   # was -0.15 / -0.30: the counters read as over-rotated (Mark, 2026-10-27);
# Le Jeune changes top/bottom contrast slightly instead of rotating the counter
I16_BN = False           # the rigid spine (I16) is an s/S convention measured on Latin only; on Bangla it fired on
                         # inflected strokes (the ১) and broke the comb gate, so Bangla strokes are not spines
NU = 0.0

METRICS = {
    "Light": dict(stem=dict(lc=61.25, uc=62.25, bn=61.25), thin=dict(lc=57.25, uc=57.25, bn=55.25),
                  lines=dict(lc=[707.0, 514.0, 0.0, -200.0], uc=[674.0, 0.0], bn=[634.0, 0.0, -200.0]),
                  height=dict(lc=514.0, uc=674.0, bn=634.0)),
    "Bold":  dict(stem=dict(lc=146.25, uc=154.25, bn=135.25), thin=dict(lc=131.25, uc=131.25, bn=112.25),
                  lines=dict(lc=[707.0, 515.0, 0.0, -187.0], uc=[674.0, 0.0], bn=[671.0, 0.0, -187.0]),
                  height=dict(lc=515.0, uc=674.0, bn=671.0)),
}
STATE = dict(master="Light", cls={}, glyph="")


def glyph_class(g):
    if g["glyph"].startswith("bn") or g.get("script") == "bengali":
        return "bn"
    for u in g.get("unicodes") or []:
        if chr(int(u, 16)).isupper():
            return "uc"
    nm = g["glyph"]
    if nm[:1].isupper() and not nm.startswith("bn"):
        return "uc"
    return "lc"


def _cls(glyph):
    return STATE["cls"].get(glyph, "lc")


def stem_of(glyph):
    return METRICS[STATE["master"]]["stem"][_cls(glyph)]


def master_info(glyph, slant):
    M = METRICS[STATE["master"]]; c = _cls(glyph); stem = M["stem"][c]
    L = M["lines"][c]; h = M["height"][c]
    return dict(tag="HindSiliguri", ia=slant, stem=stem, A=round(28.0 / 92.0 * stem, 1), thin_top=M["thin"][c],
                lines_lc=L, lines_uc=L, x_height=h, cap_height=h)


C.stem_of = stem_of
C.master_info = master_info
import italicmove
italicmove.C.master_info = master_info


def i13_target(w_up, t_up, w_now, t_now, _orig=italicmove.i13_target):
    """pilot 2: every stroke that is not a true stem keeps its roman perpendicular width. The kit's 'vertical' class
    spans 22.5 deg either side and keeps the HORIZONTAL measure, i.e. the plain shear: Hind's v w y (about 20 deg off
    vertical) got nothing while k x z (about 35 deg) were corrected. True stems (within 3 deg) keep the horizontal
    measure (Frutiger: cos theta x roman); '/' takes the roman width in full like '\\' (pilot 1: halfway)."""
    if _cls(STATE["glyph"]) == "bn":
        return _orig(w_up, t_up, w_now, t_now)   # Bangla: the kit's I13 ('/' halfway, 22.5 deg vertical class): its curved
                                                 # sides 3-22 deg off vertical bumped under the perpendicular rule
    ang = math.degrees(math.atan2(t_up[1], t_up[0])) % 180.0
    if abs(ang - 90.0) < 3.0:
        return _orig(w_up, t_up, w_now, t_now)
    cls = C.direction_class(t_up)
    if cls == "vertical":
        cls = "/" if ang < 90 else "\\"
    if cls in ("/", "\\"):
        return w_up, cls
    return _orig(w_up, t_up, w_now, t_now)


italicmove.i13_target = i13_target


# ---- beta per round part (I10's rho per class) --------------------------------------------------------------------
def _encloses_counter(ink, box, step=6.0, pad=12.0):
    """True when the ink inside the box (padded) closes an empty region off from the box's border: a counter. Hind draws
    counters by self-crossing paths, so the test reads the fill, not the contour list."""
    x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
    nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    empty = [[not ink.contains(x0 + i * step, y0 + j * step) for i in range(nx)] for j in range(ny)]
    seen = [[False] * nx for _ in range(ny)]
    stack = [(i, j) for i in range(nx) for j in (0, ny - 1)] + [(i, j) for j in range(ny) for i in (0, nx - 1)]
    while stack:
        i, j = stack.pop()
        if 0 <= i < nx and 0 <= j < ny and empty[j][i] and not seen[j][i]:
            seen[j][i] = True
            stack += [(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)]
    return sum(1 for j in range(ny) for i in range(nx) if empty[j][i] and not seen[j][i]) >= 4


S_LIKE = {"s", "S", "dollar"}


def _terminal_parts(self):
    """parts that end in a free terminal (c, s, the a's hood, r's flag): a terminal group's neighbouring runs"""
    if getattr(self, "_tparts", None) is None:
        self._tparts = {self.runs[ri]["part"] for G_ in self._groups() if G_["terminal"]
                        for e in (G_["prev"], G_["next"]) if e is not None for ri in self.run_of.get(e, [])}
    return self._tparts


def part_beta(self, part_run):
    """closed free round: the part's runs are every contour the glyph has (o, O, 0). Any other part that closes a
    counter inside its box is a bowl (p b d q drawn as stem + bowl, e, the a's bowl, D R, Bangla loops); a part that
    closes none is an open arc (c C G, the a's hood, s)."""
    closed, bowl, arc = BETA[STATE["master"]][_cls(self.g_up["glyph"])]
    if self.g_up["glyph"] in S_LIKE:
        return 0.0               # Frutiger: s and S bowls keep their chords (~0); only the spine turns (psi)
    pi = self.runs.index(part_run)
    mine = {r["ci"] for r in self.runs if r["part"] == pi}
    if part_run.get("closed") and len(mine) == len(self.g_up["contours"]):
        return closed
    xs = [n[0] for c in self.g_up["contours"] for n in c["nodes"]]
    b = part_run["box"]          # widened to the glyph's ink: D's and R's counters close against the stem, not the run
    if _encloses_counter(self.ink, (min(xs), b[1], max(xs), b[3])):
        return bowl
    if _cls(self.g_up["glyph"]) == "bn":
        return arc               # Bangla: only parts that close a counter lean back; open rounds (ত ভ ও ড) and hooks stay at
                                 # 0 (Tiro: open bowls ~0; Frutiger: hooks without a clear chord 0). The arch rule and an
                                 # "open round body" rule both put most Bangla glyphs on plain slant (pilot 2 run 2)
    if pi not in _terminal_parts(self):
        return bowl              # an arch: an open part with no free terminal (n m h u shoulders) leans back like p q
    return closed                # an open arc (c C G, the a's hood) leans back like its class's o / O so the rounds share
                                 # one axis. Frutiger's c -0.18 / C G -0.24..-0.51 are CHORD readings (terminal to
                                 # terminal), not the bowl's lean; used as the bowl's lean they turned C against O (Mark)


def run_map(self, ri, narrow=1.0):
    r = self.runs[ri]
    part = self.runs[r["part"]]
    beta = part_beta(self, part)
    if r["counter"] and beta > 0 and _cls(self.g_up["glyph"]) != "bn":
        beta += COUNTER_DBETA[STATE["master"]]   # the counter leans back less than the outside: I13's job done by the lean
    kr = math.tan((1.0 - beta) * self.theta)
    s = 1.0 - (1.0 - r["s"]) * narrow
    r["beta"] = beta
    return Map.about(r["c"], self.S(r["c"]), [[s, kr], [0.0, 1.0]])


SK.Skeleton.run_map = run_map


def sheared(cs, k=K, shift=0.0):
    return [{"closed": c["closed"], "nodes": [[n[0] + k * n[1] + shift, n[1]] + list(n[2:]) for n in c["nodes"]]} for c in cs]


def shift_cs(cs, dx):
    return [{"closed": c["closed"], "nodes": [[n[0] + dx, n[1]] + list(n[2:]) for n in c["nodes"]]} for c in cs]


class Mv:
    def __init__(self, a, b):
        self.a, self.b = a, b

    def contours_at(self, t):
        return [{"closed": ca["closed"], "nodes": [[na[0] + (nb[0] - na[0]) * t, na[1] + (nb[1] - na[1]) * t] + list(na[2:])
                                                   for na, nb in zip(ca["nodes"], cb["nodes"])]} for ca, cb in zip(self.a, self.b)]


def gate(cs, up_cs):
    sl = sheared(up_cs)
    ev = curvcomb.evaluate({"contours": sl, "glyph": "x", "master": "Slant", "width": 500.0}, Mv(sl, cs))
    h = hump(cs, up_cs, K=K)
    return dict(snaps=len(ev["snaps"]), spikes=len(ev["spikes"]), minor=len(ev["minors"]) + len(ev["minor_spikes"]), hump=len(h),
                hump_where=[(x["kind"], x.get("node", x.get("seg"))) for x in h],
                ok=(len(ev["snaps"]) == 0 and len(ev["spikes"]) == 0 and len(h) == 0))


def _join_blend(cs, up_cs, Sk):
    """a bowl drawn as its own closed contour overlapping a stem (Hind's b d p q) follows the stem where it meets it: each
    on-curve node (with its handles) is blended from the plain shear at the stem side (w 0) to the bowl's full lean at
    the far side (w 1), so the top and bottom joins keep the roman's relation to the stem (Mark: d's top and bottom joins
    should look alike; a rigid lean swung the bottom into the stem and the top away from it). Affine along each handle
    line, so smooth nodes stay smooth."""
    if not JOIN_BLEND:
        return cs
    bowls = set()
    for i, r in enumerate(Sk.runs):
        if r["part"] == i and r.get("closed") and (r.get("beta") or 0) > 0:
            mine = {q["ci"] for q in Sk.runs if q["part"] == i}
            if len(mine) < len(up_cs):
                bowls |= mine
    if not bowls:
        return cs
    sl = sheared(up_cs)
    xs_b = [n[0] for ci in bowls for n in up_cs[ci]["nodes"]]
    others = [n[0] for ci, c in enumerate(up_cs) if ci not in bowls for n in c["nodes"]]
    if not others:
        return cs
    x0, x1 = min(xs_b), max(xs_b)
    stem_right = (sum(others) / len(others)) > (x0 + x1) / 2
    out = [dict(c, nodes=[list(n) for n in c["nodes"]]) for c in cs]
    for ci in bowls:
        N = up_cs[ci]["nodes"]; L = len(N)
        on = [i for i, n in enumerate(N) if n[2] != "o"]
        owner = {}
        for i in range(L):     # an off-curve takes the weight of the on-curve it belongs to (nearest along the contour)
            if N[i][2] != "o":
                owner[i] = i
            else:
                owner[i] = min(on, key=lambda j: min((i - j) % L, (j - i) % L))
        for i in range(L):
            u = (N[owner[i]][0] - x0) / max(x1 - x0, 1.0)
            w = (1.0 - u) if stem_right else u
            w = w * w * (3 - 2 * w)                     # smoothstep: no lean at the stem, full lean at the far side
            a, b = sl[ci]["nodes"][i], cs[ci]["nodes"][i]
            out[ci]["nodes"][i][0] = a[0] + w * (b[0] - a[0]); out[ci]["nodes"][i][1] = a[1] + w * (b[1] - a[1])
    return out


JOIN_BLEND = True
# top/bottom hairline change on back-leaning rounds (Le Jeune: o thin-h +10.3 % Poster, +0.8 % Dek, +0.1 % Text; it
# changes contrast there instead of turning the counter). Fraction of the roman thickness at that place; Latin only.
HAIRLINE_TB = {"Light": 0.0, "Bold": 0.0}


def _hairline_tb(cs, up_cs, Sk):
    """move each counter's top and bottom extreme (a node with a horizontal tangent at the counter's top / bottom),
    with its two handles, inward by HAIRLINE_TB x the roman thickness there: a translation, so smooth stays smooth"""
    h = HAIRLINE_TB[STATE["master"]]
    if not h or _cls(STATE["glyph"]) == "bn":
        return cs
    out = [dict(c, nodes=[list(n) for n in c["nodes"]]) for c in cs]
    for i, r in enumerate(Sk.runs):
        if not r["counter"] or (self_beta := (Sk.runs[r["part"]].get("beta") or 0)) <= 0:
            continue
        ci = r["ci"]; N = up_cs[ci]["nodes"]; L = len(N)
        ys = [n[1] for n in N if n[2] != "o"]
        if not ys:
            continue
        top, bot = max(ys), min(ys)
        outer = [n for k, c in enumerate(up_cs) if k != ci for n in c["nodes"] if n[2] != "o"]
        for j, n in enumerate(N):
            if n[2] == "o" or n[1] not in (top, bot):
                continue
            prv, nxt = N[(j - 1) % L], N[(j + 1) % L]
            if abs(prv[1] - n[1]) > 1 or abs(nxt[1] - n[1]) > 1:
                continue              # not a horizontal-tangent extreme
            sgn = -1 if n[1] == top else 1
            # roman thickness there: the nearest outer node straight above / below
            cand = [o for o in outer if abs(o[0] - n[0]) < 40 and (o[1] - n[1]) * (-sgn) > 0]
            if not cand:
                continue
            t = min(abs(o[1] - n[1]) for o in cand)
            dy = sgn * h * t
            for k in (j - 1, j, j + 1):
                out[ci]["nodes"][k % L][1] += dy
    return out


def same_structure(a, b):
    return len(a) == len(b) and all(len(x["nodes"]) == len(y["nodes"]) and [n[2] for n in x["nodes"]] == [n[2] for n in y["nodes"]] for x, y in zip(a, b))


def correct_glyph(g, master, quiet=True, retension=True, simple=False):
    """-> dict(contours (kit frame: sheared about y=0), skeleton report bits, gate)"""
    STATE["master"] = master
    gl = g["glyph"]
    STATE["cls"][gl] = glyph_class(g)
    STATE["glyph"] = gl
    up = {"contours": copy.deepcopy(g["contours"]), "width": g["width"], "master": "Regular", "glyph": gl}
    sl = {"contours": sheared(up["contours"]), "width": g["width"], "master": "Slant", "glyph": gl}
    G = {"GeistSerifRegular_" + gl: up, "GeistSerifSlant_" + gl: sl}
    italicmove.ItalicMover.RETENSION = retension
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        out = round_p2.correct(gl, G, "1-6", serif="shear", side_handles="corners", hold_brackets=True, psi=PSI, nu_coef=NU,
                               i16=(not simple) and (I16_BN or STATE["cls"][gl] != "bn"), terminal="shear")
        cs = out["contours"]
        cs = _join_blend(cs, up["contours"], out["skeleton"])
        cs = _hairline_tb(cs, up["contours"], out["skeleton"])
        cs, rep = repair(cs, up["contours"], K)
    assert same_structure(cs, up["contours"])
    Sk = out["skeleton"]
    info = dict(cls=STATE["cls"][gl],
                parts=[dict(nodes=len(r["nodes"]), closed=r["closed"], counter=bool(r["counter"]), beta=r.get("beta"))
                       for i, r in enumerate(Sk.runs) if r["part"] == i],
                spine=[(sg["gi"], sg["gj"]) for sg, _ in Sk.spine_segments()],
                terminals=len(getattr(Sk, "term_report", []) or []),
                repairs=len(rep))
    gt = gate_visible(cs, up["contours"])
    return dict(contours=cs, info=info, gate=gt, log=buf.getvalue()[-2000:])


# ---- the gate on what the fill shows ---------------------------------------------------------------------------------
def _seg_ctl(cs, gi, gj):
    flat = [n for c in cs for n in c["nodes"]]
    base = 0
    for c in cs:
        N = len(c["nodes"])
        if base <= gi < base + N:
            i, j = gi - base, gj - base
            offs = [base + (k % N) for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
            return [flat[gi][:2]] + [flat[o][:2] for o in offs] + [flat[gj][:2]]
        base += N
    return None


def buried(cs, pts, eps=2.5):
    """True when every sample has ink on BOTH sides (eps u along the normal): the curve is inside the union fill,
    so the compiled (overlap-removed) glyph never shows it"""
    from geom import path
    p = path(cs, flip=False)
    for (x, y), (nx, ny) in pts:
        if not (p.contains(x + nx * eps, y + ny * eps) and p.contains(x - nx * eps, y - ny * eps)):
            return False
    return True


def _samples(P, ts):
    P = np.array(P, float); out = []
    for t in ts:
        u = 1 - t
        if len(P) == 4:
            p = u**3*P[0] + 3*u*u*t*P[1] + 3*u*t*t*P[2] + t**3*P[3]
            d = 3*(u*u*(P[1]-P[0]) + 2*u*t*(P[2]-P[1]) + t*t*(P[3]-P[2]))
        else:
            p = P[0] + (P[-1] - P[0]) * t; d = P[-1] - P[0]
        L = np.hypot(*d)
        if L < 1e-9: continue
        out.append(((p[0], p[1]), (-d[1] / L, d[0] / L)))
    return out


def gate_visible(cs, up_cs):
    """pass 2c's gate (curvcomb 0 snaps 0 spikes + comb_p2.hump), with each hump/peak/G2 failure tested for visibility:
    a failure on a segment (or at a node) that lies wholly inside the glyph's own ink is listed as buried, not failed"""
    g = gate(cs, up_cs)
    h = hump(cs, up_cs, K=K)
    # pilot 2: a G2 (curvature jump) failure at a CORNER node is not a failure: a corner keeps no curvature continuity.
    # Hind's curved ink traps (v w y crotches) are corners with retracted handles, which failed here in every level.
    flat_up = [n for c in up_cs for n in c["nodes"]]
    h = [f for f in h if not (f["kind"] == "g2" and "node" in f and not flat_up[f["node"]][3])]
    vis, bur = [], []
    S = {}
    for f in h:
        if "seg" in f:
            P = _seg_ctl(cs, *f["seg"]); pts = _samples(P, np.linspace(0.05, 0.95, 19))
        else:
            nd = f["node"]; flat = [n for c in cs for n in c["nodes"]]
            # the two curves either side of the node, near the node
            pts = []
            for c_ in [_seg_ctl(cs, a, b) for a, b in _node_segs(cs, nd)]:
                if c_: pts += _samples(c_, [0.0, 0.08, 0.92, 1.0])
        (bur if (pts and buried(cs, pts)) else vis).append((f["kind"], f.get("seg", f.get("node"))))
    fin = all(math.isfinite(n[0]) and math.isfinite(n[1]) for c in cs for n in c["nodes"])
    g.update(hump_visible=vis, hump_buried=bur, finite=fin, ok=(fin and g["snaps"] == 0 and g["spikes"] == 0 and not vis))
    return g


def _node_segs(cs, nd):
    base = 0
    for c in cs:
        N = len(c["nodes"])
        if base <= nd < base + N:
            ons = [base + i for i in range(N) if c["nodes"][i][2] != "o"]
            k = ons.index(nd)
            return [(ons[k - 1], nd), (nd, ons[(k + 1) % len(ons)])]
        base += N
    return []
