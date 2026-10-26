"""Hind Siliguri italic pilot: round 5 pass 2c's STRUCTURE (copied kit in ../kit, unmodified files) with Hind's numbers.

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
import curvcomb

K = 0.25; YC = 253.5; SHIFT = -K * YC
THETA = math.atan(K)
BETA_ROUND = {"lc": 0.22, "bn": 0.22, "uc": 0.36}
BETA_OTHER = 0.0          # bowls on a stem / stroke, Bangla loops, open arcs (rho_loop is tied here: one switch)
PSI = 1.25
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
STATE = dict(master="Light", cls={})


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


# ---- beta per round part (I10's rho per class) --------------------------------------------------------------------
def part_beta(self, part_run):
    if part_run.get("closed"):
        return BETA_ROUND[_cls(self.g_up["glyph"])]
    return BETA_OTHER


def run_map(self, ri, narrow=1.0):
    r = self.runs[ri]
    part = self.runs[r["part"]]
    beta = part_beta(self, part)
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


def same_structure(a, b):
    return len(a) == len(b) and all(len(x["nodes"]) == len(y["nodes"]) and [n[2] for n in x["nodes"]] == [n[2] for n in y["nodes"]] for x, y in zip(a, b))


def correct_glyph(g, master, quiet=True, retension=True, simple=False):
    """-> dict(contours (kit frame: sheared about y=0), skeleton report bits, gate)"""
    STATE["master"] = master
    gl = g["glyph"]
    STATE["cls"][gl] = glyph_class(g)
    up = {"contours": copy.deepcopy(g["contours"]), "width": g["width"], "master": "Regular", "glyph": gl}
    sl = {"contours": sheared(up["contours"]), "width": g["width"], "master": "Slant", "glyph": gl}
    G = {"GeistSerifRegular_" + gl: up, "GeistSerifSlant_" + gl: sl}
    italicmove.ItalicMover.RETENSION = retension
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        out = round_p2.correct(gl, G, "1-6", serif="shear", side_handles="corners", hold_brackets=True, psi=PSI, nu_coef=NU,
                               i16=(not simple) and (I16_BN or STATE["cls"][gl] != "bn"), terminal=("shear" if simple else "a"))
        cs = out["contours"]
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
