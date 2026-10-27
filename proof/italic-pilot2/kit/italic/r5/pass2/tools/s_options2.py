"""Round 5 · pass 2: five more s options, mapped off HIS skeleton (Mark: "the closest was actually 5 (without the bumps)
and 6a ... map the top and bottom off the skeleton of my drawing").

Every option is applied to his drawn roman s and goes through the shipped pipeline: the width rules I13 (thickness from
our roman rungs), the harmonizer last, I16 for the spine. Node count, order, handles and segment types never change.
"His drawing" is his 14.04 deg s for the 14.04 deg run, and his NEW s (drawn at theta_d = 17.78 deg) for the 18 deg runs.

  10  skeleton-mapped bowls       each bowl node keeps its place along the roman bowl's centreline (arc abscissa between the
                                  six landmarks) and its signed offset; it is re-placed at the same abscissa on HIS italic
                                  centreline with the same offset (handles by the local turn + stretch); spine I16;
                                  blended over 45 u of centreline next to the spine junctions; the terminals ride (I15):
                                  each takes the mean move of the mapped bowl nodes on its two sides (mapped node by node
                                  they hooked into the counters: the centreline ends at the cuts)
  11  option 5 without the bumps  I11 narrowing with the terminals narrowed by their part (the bumps were the narrowed bowl
                                  meeting a full-width beak); nu fitted to his new drawing (score)
  11b the same at the study's nu = 0.6 tan(theta), to show the bumps gone
  12  6a with full lean, his bowl sizes   each bowl scaled about its far extreme to HIS bowl width and height (his italic
                                  back-sheared by his stem angle, against his roman), spine re-fitted, rho = 1
  13  shorter handles, moved extremes     the bowls' top and bottom nodes move to HIS corresponding nodes (position and
                                  tangent); the two handles at each are solved for the ROMAN's curvature there, bounded to
                                  0.4-1.0 x (they may only shorten); no fairness
  14  10 + 13                     skeleton-mapped bowls, then the extremes' handles shortened as in 13

s_options2.py  -> sheets/s_options2_18.png, s_options2_14.png, word_saopne_18_options2.png, readings/s_options2.json
"""
import sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
import drawn, drawn5s, drawn18, curvcomb
import thickness5s as TH
from round_p2 import correct
from s_options import sheared, with_s, SParts, measures, Mv
from score18 import G_at
from proof5s import Sheet, INK, DIM, FAINT

OUT = os.path.join(C.R5, "sheets")
LBL = "round 5 · pass 2 · s options 10–14"
TH_D = drawn18.stem_angle()[0]; K_D = math.tan(math.radians(TH_D))


# ---- centreline geometry ------------------------------------------------------------------------------------------
class Poly:
    def __init__(self, pts):
        self.p = np.asarray(pts, float)
        d = np.diff(self.p, axis=0); L = np.linalg.norm(d, axis=1)
        self.s = np.r_[0.0, np.cumsum(L)]
        t = d / np.maximum(L, 1e-9)[:, None]
        self.t = np.vstack([t, t[-1:]])

    def nearest(self, q):
        q = np.asarray(q, float); a = self.p[:-1]; b = self.p[1:]; ab = b - a
        u = np.clip(((q - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-9), 0, 1)
        f = a + ab * u[:, None]; dd = np.linalg.norm(f - q, axis=1); i = int(np.argmin(dd))
        return self.s[i] + u[i] * np.linalg.norm(ab[i]), f[i], self.t[i]

    def at(self, s):
        s = float(np.clip(s, 0, self.s[-1])); i = int(np.clip(np.searchsorted(self.s, s) - 1, 0, len(self.p) - 2))
        u = (s - self.s[i]) / max(self.s[i + 1] - self.s[i], 1e-9)
        return self.p[i] + (self.p[i + 1] - self.p[i]) * u, self.t[i]


def centre(cs):
    P = TH.profile(cs)
    CL = Poly(P["centreline"])
    lm = [CL.nearest(q)[0] for q in P["landmarks"]]
    return CL, np.array(sorted(lm))


def rot(a):
    return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])


def nrm(t):
    return np.array([-t[1], t[0]])


def mapped_post(his_cs, blend=45.0):
    """option 10: the bowls' nodes re-placed on HIS italic centreline (same landmark abscissa, same signed offset)"""
    def post(Sk):
        U = Sk.U
        CLr, Lr = centre(Sk.g_up["contours"]); CLh, Lh = centre(his_cs)
        spine = set()
        for sg, _ in Sk.spine_segments():
            spine |= {sg["gi"], sg["gj"], *sg["offs"]}
        junction_s = [CLr.nearest(U.xy[j])[0] for sg, _ in Sk.spine_segments() for j in (sg["gi"], sg["gj"])]
        base = [p.copy() for p in Sk.new]
        frame = {}
        term = set(Sk.terminal_nodes)
        for nd in range(len(U.xy)):
            if U.typ[nd] == "o" or nd in spine or nd in term:
                continue
            s, f, t = CLr.nearest(U.xy[nd])
            v = U.xy[nd] - f; o = float(v @ nrm(t)); a = float(v @ t)
            u = np.interp(s, Lr, np.arange(len(Lr))); sh_ = np.interp(u, np.arange(len(Lh)), Lh)
            ph, th = CLh.at(sh_)
            q = ph + o * nrm(th) + a * th
            k = np.interp(u, np.arange(len(Lh) - 1) + 0.5, np.diff(Lh) / np.maximum(np.diff(Lr), 1e-9))   # local stretch
            ang = math.atan2(th[1], th[0]) - math.atan2(t[1], t[0])
            d = min(abs(s - sj) for sj in junction_s)
            w = 1.0 if d >= blend else (lambda x: x * x * (3 - 2 * x))(d / blend)
            Sk.new[nd] = base[nd] + w * (q - base[nd])
            frame[nd] = (k * rot(ang), w)
        # a terminal (I15 piece) rides: it takes the mean displacement of the mapped bowl nodes on its two sides, rigidly
        for nodes, _, _, _ in Sk.pieces:
            first, last = nodes[0], nodes[-1]
            nb = [U.seg_before[first]["gi"], U.seg_after[last]["gj"]]
            disp = np.mean([Sk.new[n] - base[n] for n in nb if n in frame], axis=0) if any(n in frame for n in nb) else np.zeros(2)
            for nd in nodes:
                Sk.new[nd] = base[nd] + disp
                frame[nd] = (None, 0.0)
        for h in range(len(U.xy)):
            if U.typ[h] != "o":
                continue
            nd = U.owner[h]
            if nd not in frame:
                continue
            if frame[nd][0] is None:
                Sk.new[h] = base[h] + (Sk.new[nd] - base[nd]); continue
            M, w = frame[nd]
            hm = Sk.new[nd] + M @ (U.xy[h] - U.xy[nd])
            Sk.new[h] = (base[h] + (Sk.new[nd] - base[nd])) * (1 - w) + w * hm
    return post


def kappa_end(P, end):
    P = np.asarray(P, float)
    if end == 0:
        d1, d2 = 3 * (P[1] - P[0]), 6 * (P[2] - 2 * P[1] + P[0])
    else:
        d1, d2 = 3 * (P[3] - P[2]), 6 * (P[3] - 2 * P[2] + P[1])
    return abs(float((d1[0] * d2[1] - d1[1] * d2[0]) / max(np.linalg.norm(d1), 1e-9) ** 3))


def extremes(Sk):
    jn = set()
    for sg, _ in Sk.spine_segments():
        jn |= {sg["gi"], sg["gj"]}
    return [nd for r in Sk.runs for nd in r["nodes"] if nd not in jn]


def shorten_post(his_cs=None, lo=0.4, hi=1.0, report=None):
    """option 13 (his_cs given: move the extremes to his corresponding nodes, position and tangent) and the handle
    solve: each extreme's two handles take the length that gives the ROMAN's curvature at the node, within lo..hi x"""
    def post(Sk):
        U = Sk.U
        F = extremes(Sk)
        if his_cs is not None:
            cur = []; k = 0
            for c in Sk.g_up["contours"]:
                cur.append({"closed": c["closed"], "nodes": [[float(Sk.new[k + i][0]), float(Sk.new[k + i][1])] + list(n[2:]) for i, n in enumerate(c["nodes"])]})
                k += len(c["nodes"])
            pairs, _ = drawn5s.correspond(cur, his_cs)
            pm = dict(pairs)
            Hn = [np.array(n[:2], float) for c in his_cs for n in c["nodes"]]
            Hns = [n for c in his_cs for n in c["nodes"]]; NH = len(Hn)
            for nd in F:
                if nd not in pm:
                    continue
                kk = pm[nd]
                hb, ha = Hn[(kk - 1) % NH], Hn[(kk + 1) % NH]
                tdir = ha - hb; tdir /= np.linalg.norm(tdir)
                d = Hn[kk] - Sk.new[nd]
                for h in (U.seg_before[nd]["offs"][1], U.seg_after[nd]["offs"][0]):
                    L = np.linalg.norm(Sk.new[h] - Sk.new[nd]); sgn = 1 if h == U.seg_after[nd]["offs"][0] else -1
                    Sk.new[h] = Hn[kk] + sgn * tdir * L
                Sk.new[nd] = Hn[kk].copy()
                if report is not None:
                    report.append(dict(node=nd, his=kk, moved=round(float(np.linalg.norm(d)), 1)))
        for nd in F:
            sb, sa = U.seg_before[nd], U.seg_after[nd]
            kt = 0.5 * (kappa_end(U.ctl(sb), 3) + kappa_end(U.ctl(sa), 0))        # the roman's curvature at the node
            for sg, end in ((sb, 3), (sa, 0)):
                idx = [sg["gi"]] + sg["offs"] + [sg["gj"]]
                P = np.array([Sk.new[i] for i in idx])
                if end == 0:
                    u = P[1] - P[0]; L0 = np.linalg.norm(u); u /= L0
                    c = abs(u[0] * (P[2] - P[0])[1] - u[1] * (P[2] - P[0])[0])
                    a = math.sqrt((2.0 / 3.0) * c / max(kt, 1e-9)); a = min(max(a, lo * L0), hi * L0)
                    Sk.new[idx[1]] = P[0] + a * u
                else:
                    w = P[2] - P[3]; L0 = np.linalg.norm(w); w /= L0
                    c = abs(w[0] * (P[1] - P[3])[1] - w[1] * (P[1] - P[3])[0])
                    b = math.sqrt((2.0 / 3.0) * c / max(kt, 1e-9)); b = min(max(b, lo * L0), hi * L0)
                    Sk.new[idx[2]] = P[3] + b * w
                if report is not None:
                    report.append(dict(node=nd, seg=(sg["gi"], sg["gj"]), handle_scale=round(float((a if end == 0 else b) / L0), 3)))
    return post


def chain(*posts):
    def post(Sk):
        for p in posts:
            p(Sk)
    return post


def bowl_boxes(cs):
    P = TH.profile(cs); waist = float(P["landmarks"][3][1])
    b = drawn.box_of(cs, pad=2); M = drawn.mask(cs, b, ppu=2.0)
    H, W = M.shape; yy = b[3] - (np.arange(H) + 0.5) / 2; xx = b[0] + (np.arange(W) + 0.5) / 2
    out = {}
    for nm, sel in (("upper", yy > waist), ("lower", yy <= waist)):
        m = M[sel]; rows = np.nonzero(m.any(axis=1))[0]; cols = np.nonzero(m.any(axis=0))[0]
        ys = yy[sel][rows]
        out[nm] = dict(w=float((cols.max() - cols.min() + 1) / 2), h=float(ys.max() - ys.min()))
    return out


def scale_bowls(SP, f):
    """each bowl scaled by f[bowl] = (sx, sy) about its far extreme; the spine is the affine map meeting the bowls"""
    U = SP.U; new = [np.array(p, float) for p in U.xy]; maps = {}
    for upper in (True, False):
        ids = [i for i in range(len(U.xy)) if i not in SP.spine_nodes and SP.upper(i) == upper]
        ons = [i for i in ids if U.typ[i] != "o"]
        e = max((U.xy[i] for i in ons), key=lambda p: p[1]) if upper else min((U.xy[i] for i in ons), key=lambda p: p[1])
        sx, sy = f["upper" if upper else "lower"]
        maps[upper] = (lambda e, S: (lambda p: e + S * (np.asarray(p, float) - e)))(np.array(e, float), np.array([sx, sy]))
        for i in ids:
            new[i] = maps[upper](U.xy[i])
    J = sorted(SP.junctions); A_, b_ = [], []
    for j in J:
        q = maps[U.xy[j][1] > SP.m[1]](U.xy[j]); x, y = U.xy[j]
        A_ += [[x, y, 1, 0, 0, 0], [0, 0, 0, x, y, 1]]; b_ += [q[0], q[1]]
    a = np.linalg.lstsq(np.array(A_), np.array(b_), rcond=None)[0]
    L = np.array([[a[0], a[1]], [a[3], a[4]]]); tv = np.array([a[2], a[5]])
    for i in SP.spine_nodes:
        new[i] = L @ U.xy[i] + tv
    return SP._contours(new)


# ---- the runs ----------------------------------------------------------------------------------------------------
def his_for(K, frame):
    if abs(K - 0.25) < 1e-9:
        raw = drawn.raw_contours("s", "italic"); kd = 0.25
    else:
        raw = drawn18.raw("s"); kd = K_D
    return drawn.shift(raw, drawn5s.centroid_x(frame) - drawn5s.centroid_x(raw)), kd


def options(K, nu_fit=None):
    G = G_at(K)
    up = G["GeistSerifRegular_s"]["contours"]; sl = G["GeistSerifSlant_s"]["contours"]
    his, kd = his_for(K, sl)
    SP = SParts(up)
    rep = {}
    O = []
    def add(key, name, rule, up_cs, cs):
        O.append(dict(key=key, name=name, rule=rule, up=up_cs, cs=cs))
    add("2", "pass 2b (shipped)", "reference", up, correct("s", G, "1-6")["contours"])
    add("5", "option 5 (nu 0.6, with its bumps)", "reference", up, correct("s", G, "1-6", nu_coef=0.6)["contours"])
    add("10", "skeleton-mapped bowls", "bowl nodes on HIS centreline, our offsets; spine I16; blend 45 u", up,
        correct("s", G, "1-6", post=mapped_post(his))["contours"])
    nu = nu_fit if nu_fit is not None else 0.0
    add("11", "narrowing, no bumps (nu %.2f tan θ)" % nu, "terminals narrowed with their part; nu fitted to his new s", up,
        correct("s", G, "1-6", nu_coef=nu, terminal_narrow=True)["contours"])
    add("11b", "narrowing 0.6 tan θ, no bumps", "option 5 with the terminals narrowed", up,
        correct("s", G, "1-6", nu_coef=0.6, terminal_narrow=True)["contours"])
    # 12: his bowl sizes
    his_up = sheared(his, -kd)
    bh, br = bowl_boxes(his_up), bowl_boxes(up)
    f = {k: (bh[k]["w"] / br[k]["w"], bh[k]["h"] / br[k]["h"]) for k in ("upper", "lower")}
    u12 = scale_bowls(SP, f)
    add("12", "his bowl sizes, full lean", "bowls x(%.3f, %.3f) / x(%.3f, %.3f) about their extremes, rho 1" % (*f["upper"], *f["lower"]), u12,
        correct("s", with_s(G, u12), "1-6", rho=1.0)["contours"])
    rep["12"] = dict(his_bowls=bh, roman_bowls=br, scale=f)
    r13 = []
    add("13", "his extremes, shorter handles", "top / bottom nodes to his nodes; handles for the roman's curvature, 0.4–1.0 x", up,
        correct("s", G, "1-6", post=shorten_post(his, report=r13))["contours"])
    rep["13"] = r13
    r14 = []
    add("14", "10 + 13", "skeleton-mapped bowls, then the extremes' handles shortened", up,
        correct("s", G, "1-6", post=chain(mapped_post(his), shorten_post(None, report=r14)))["contours"])
    rep["14"] = r14
    add("6a", "option 6a (smaller bowls x0.92)", "reference", None, None)
    u6, _ = SP.shrink_bowls(0.92)
    O[-1].update(up=u6, cs=correct("s", with_s(G, u6), "1-6")["contours"])
    return G, O, his, rep


COLS = {"2": (90, 222, 118), "5": (225, 110, 230), "10": (80, 200, 235), "11": (250, 200, 70), "11b": (250, 150, 60),
        "12": (180, 230, 90), "13": (255, 120, 160), "14": (130, 210, 255), "6a": (200, 160, 255)}


def fit_nu():
    G = G_at(K_D); sl = G["GeistSerifSlant_s"]["contours"]; his, _ = his_for(K_D, sl)
    best = None; scan = {}
    for nc in (0.0, 0.03, 0.06, 0.1, 0.15, 0.2, 0.3):
        x = drawn.xor_pct(correct("s", G, "1-6", nu_coef=nc, terminal_narrow=True)["contours"], his)
        scan[nc] = round(x, 2)
        if best is None or x < best[1]:
            best = (nc, x)
    return best[0], scan


def run():
    nu, scan = fit_nu()
    R = dict(theta_d=TH_D, K_d=K_D, nu_scan=scan, nu_fit=nu)
    res = {}
    for tag, K in (("14", 0.25), ("kd", K_D), ("18", 1.0 / 3.0)):
        G, O, his, rep = options(K, nu)
        for o in O:
            o["xor"] = drawn.xor_pct(o["cs"], his)
        res[tag] = dict(G=G, O=O, his=his, rep=rep)
    G18, O18 = res["18"]["G"], res["18"]["O"]
    for o in O18:
        o["m"] = measures(o["cs"])
        sl = {"contours": sheared(o["up"], 1.0 / 3.0), "glyph": "s", "master": "Slant", "width": 470.0}
        ev = curvcomb.evaluate(sl, Mv(sl["contours"], o["cs"]))
        o["comb"] = (len(ev["snaps"]), len(ev["spikes"]), len(ev["minors"]) + len(ev["minor_spikes"]))
    sheet18(res); sheet14(res); words(G18, O18, res["kd"]["his"])
    R["options"] = {o["key"]: dict(name=o["name"], rule=o["rule"], xor14=round(o14["xor"], 2), xor_kd=round(okd["xor"], 2),
                                   xor18=round(o["xor"], 2), comb18=o["comb"], measures={k: v for k, v in o["m"].items() if k != "centreline"})
                    for o, o14, okd in zip(O18, res["14"]["O"], res["kd"]["O"])}
    R["reports"] = {t: res[t]["rep"] for t in res}
    json.dump(R, open(os.path.join(C.R5, "readings", "s_options2.json"), "w"), indent=1, default=lambda v: float(v) if hasattr(v, "__float__") else str(v))
    print(json.dumps({k: v for k, v in R.items() if k != "reports"}, indent=1, default=str))


def sheet18(res):
    O = res["18"]["O"]; Okd = res["kd"]["O"]; his_kd = res["kd"]["his"]
    hisCL = measures(his_kd)["centreline"]
    cols = 3; CW, CH = 800, 1500
    rows = math.ceil(len(O) / cols)
    W, H = cols * (CW + 10) + 20, 190 + rows * (CH + 10) + 140
    sh = Sheet(W, H)
    sh.title("/s  ·  options 10–14, mapped off Mark's skeleton  ·  %s" % LBL, "18.43°  (x' = x + y/3)",
             "per option: SOLID at 18.43° · SOLID green 55 %% over his NEW drawn s (grey) at his stem angle %.2f° with XOR · centrelines: his new s grey, the option in its colour" % TH_D)
    sh.key(26, 122, [("%s %s" % (o["key"], o["name"]), COLS[o["key"]]) for o in O[:5]], 14)
    sh.key(26, 146, [("%s %s" % (o["key"], o["name"]), COLS[o["key"]]) for o in O[5:]], 14)
    B = (-60, -40, 640, 590)
    for k, (o, okd) in enumerate(zip(O, Okd)):
        x0 = 20 + (k % cols) * (CW + 10); y0 = 180 + (k // cols) * (CH + 10); col = COLS[o["key"]]
        sh.text(x0 + 8, y0 + 2, "%s  %s" % (o["key"], o["name"]), col, 18)
        pn = sh.panel(x0, y0 + 30, CW, 520, B, pad=6); pn.frame(); pn.hline(0); pn.hline(545); pn.fill(o["cs"], col)
        po = sh.panel(x0, y0 + 560, CW, 520, B, pad=6); po.frame(); po.hline(0); po.hline(545)
        po.fill(his_kd, (138, 138, 138)); po.fill(okd["cs"], (90, 222, 118), 140); po.outline(okd["cs"], (90, 222, 118), 1.0)
        sh.text(x0 + 8, y0 + 566, "over his new s at %.2f°:  XOR %.1f %%" % (TH_D, okd["xor"]), (90, 222, 118), 15)
        pc = sh.panel(x0, y0 + 1090, CW, 300, B, pad=6); pc.frame(); pc.fill(okd["cs"], (40, 40, 46))
        pc.polyline(hisCL, (160, 160, 166), 2.2); pc.polyline(measures(okd["cs"])["centreline"], col, 2.4)
        m = o["m"]
        sh.text(x0 + 8, y0 + 1396, "18.43°: spine %.1f°  waist %.0f u  bowls ↑%.0f ↓%.0f u  width %.0f (%.0f / %.0f) u" % (
            m["spine"], m["waist"], m["upper_h"], m["lower_h"], m["width"], m["w_upper"], m["w_lower"]), INK, 14)
        sh.text(x0 + 8, y0 + 1418, "XOR: 14.04° vs his 14° s %.1f %%  ·  %.2f° vs his new s %.1f %%  ·  18.43° vs his new s %.1f %%" % (
            res["14"]["O"][k]["xor"], TH_D, okd["xor"], o["xor"]), col, 14)
        sh.text(x0 + 8, y0 + 1440, "comb 18.43° (snaps/spikes/minor) %d/%d/%d  ·  %s" % (*o["comb"], o["rule"][:60]), DIM, 13)
    sh.text(26, H - 100, "his new s at %.2f°: spine %.1f°, waist %.0f u, width %.0f u · options 10 and 14 take their bowl centreline FROM his drawing, so their score against it is partly by construction" % (
        TH_D, measures(his_kd)["spine"], measures(his_kd)["waist"], measures(his_kd)["width"]), DIM, 15)
    return sh.save(os.path.join(OUT, "s_options2_18.png"))


def sheet14(res):
    O = res["14"]["O"]; his = res["14"]["his"]
    cols = 3; CW, CH = 800, 700
    rows = math.ceil(len(O) / cols)
    W, H = cols * (CW + 10) + 20, 190 + rows * (CH + 10) + 60
    sh = Sheet(W, H)
    sh.title("/s  ·  options 10–14, scored at 14.04°  ·  %s" % LBL, "14.04°  (x' = x + y/4)",
             "his 14.04° drawn italic SOLID grey, each option SOLID green at 55 % over it; options 10, 13, 14 use his 14° skeleton here")
    sh.key(26, 122, [("his drawn italic (14°)", (138, 138, 138)), ("the option, 55 %", (90, 222, 118))], 16)
    B = (-60, -40, 640, 590)
    for k, o in enumerate(O):
        x0 = 20 + (k % cols) * (CW + 10); y0 = 170 + (k // cols) * (CH + 10)
        pn = sh.panel(x0, y0 + 30, CW, CH - 40, B, pad=6); pn.frame(); pn.hline(0); pn.hline(545)
        pn.fill(his, (138, 138, 138)); pn.fill(o["cs"], (90, 222, 118), 140); pn.outline(o["cs"], (90, 222, 118), 1.1)
        sh.text(x0 + 8, y0 + 4, "%s  %s   XOR %.1f %%" % (o["key"], o["name"], o["xor"]), COLS[o["key"]], 17)
    return sh.save(os.path.join(OUT, "s_options2_14.png"))


def words(G, O, his_kd):
    import skia
    from PIL import Image, ImageDraw, ImageFont
    import italicsheet as IS
    IS.KERN = os.path.join(C.R5, "src", "kerning.json"); kern, _ = IS.load_kern()
    rows = O + [dict(key="his", name="his new s (17.78°, sheared +%.4f y)" % (1 / 3 - K_D), cs=sheared(his_kd, 1 / 3 - K_D))]
    S = 0.13; Wp = 1640; R = 4; LINE = 150; TOP = 150; H = TOP + len(rows) * LINE + 60
    surf = skia.Surface(Wp * R, H * R); cv = surf.getCanvas(); cv.clear(skia.ColorWHITE)
    for r, o in enumerate(rows):
        base = TOP + (r + 1) * LINE - 28; x = 0.0; prev = None
        for ch in "saopne saopne":
            n = IS.GNAME.get(ch, ch)
            if prev is not None:
                x += kern.get((prev, n), 0.0)
            if n == "space":
                x += 250; prev = n; continue
            cs = o["cs"] if n == "s" else G["GeistSerifItalic_" + n]["contours"]
            cv.drawPath(IS.skia_path(IS.shear(cs, -C.K), (330 + x * S) * R, base * R, S * R, C.K), skia.Paint(AntiAlias=True, Color=skia.Color(17, 17, 17)))
            x += G["GeistSerifRegular_" + n]["width"]; prev = n
    img = Image.fromarray(surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3].copy()).resize((Wp * 2, H * 2), Image.LANCZOS)
    d = ImageDraw.Draw(img); f = lambda sz: ImageFont.truetype(IS.MENLO, int(sz * 2))
    d.text((112, 60), "GEIST SERIF  18.43°  (x' = x + y/3)", fill=(17, 17, 17), font=f(28))
    d.text((112, 140), "%s  ·  one row per option: its s, every other letter pass 2b" % LBL, fill=(110, 110, 110), font=f(14))
    for r, o in enumerate(rows):
        y = 2 * (TOP + (r + 1) * LINE - 70)
        d.text((112, y), (o["name"] if o["key"] == "his" else "%s %s" % (o["key"], o["name"]))[:30], fill=tuple(int(c * 0.6) for c in COLS.get(o["key"], (110, 110, 110))), font=f(13))
    out = os.path.join(OUT, "word_saopne_18_options2.png"); img.save(out); print("wrote", out)


if __name__ == "__main__":
    run()


# ---- pass 2c: the bowl chains re-solved together (the fix for 13 / 14's bumps) ---------------------------------------
def chains(up_cs):
    """for each spine junction J of the upright s: the bowl arc J -> F -> E (two cubics, E = the terminal's end node)"""
    from skeleton_p2 import SkeletonP2
    Sk = SkeletonP2({"contours": up_cs, "width": 470.0, "master": "Regular", "glyph": "s"}); U = Sk.U
    spine = {(sg["gi"], sg["gj"]) for sg, _ in Sk.spine_segments()}
    out = []
    for sg, _ in Sk.spine_segments():
        for J in (sg["gi"], sg["gj"]):
            A = U.seg_before[J] if J == sg["gi"] else U.seg_after[J]
            if (A["gi"], A["gj"]) in spine or A["kind"] != "curve":
                continue
            fwd = A["gi"] == J
            F = A["gj"] if fwd else A["gi"]
            B = U.seg_after[F] if fwd else U.seg_before[F]
            if B["kind"] != "curve":
                continue
            out.append(dict(J=J, F=F, segs=[A, B], fwd=fwd, spine=sg))
    return out, U


def chain_solve(cs, up_cs, lo=0.4, hi=1.25, w_prof=1.0, w_keep=0.0):
    """every handle length of each bowl chain solved jointly, nodes and handle directions fixed: G2 at J (with the spine,
    at the roman's ratio) and at F (the roman's ratio), and the ROMAN's curvature profile along the chain (by arc-length
    fraction, scaled by roman length / new length) as the target; no fairness term. -> (contours, report)"""
    from scipy.optimize import least_squares
    import copy
    CH, U = chains(up_cs)
    cs = copy.deepcopy(cs)
    flat = [n for c in cs for n in c["nodes"]]
    pos = lambda i: np.array(flat[i][:2], float)
    ts = np.linspace(0, 1, 25); rep = []
    def ctl_up(sg):
        return np.array([U.xy[i] for i in [sg["gi"]] + sg["offs"] + [sg["gj"]]])
    for ch in CH:
        A, B = ch["segs"]; segs = [A, B]
        idxs = [[s["gi"]] + s["offs"] + [s["gj"]] for s in segs]
        if not ch["fwd"]:                       # walk the chain J -> F -> E
            idxs = [i[::-1] for i in idxs]
        P0 = [np.array([pos(i) for i in ix]) for ix in idxs]
        R0 = [np.array([U.xy[i] for i in ix]) for ix in idxs]
        dirs = [(P[1] - P[0]) / np.linalg.norm(P[1] - P[0]) for P in P0] + [(P[2] - P[3]) / np.linalg.norm(P[2] - P[3]) for P in P0]
        L0 = [np.linalg.norm(P[1] - P[0]) for P in P0] + [np.linalg.norm(P[2] - P[3]) for P in P0]
        def build(x):
            Q = []
            for k, P in enumerate(P0):
                q = P.copy(); q[1] = P[0] + x[k] * L0[k] * dirs[k]; q[2] = P[3] + x[2 + k] * L0[2 + k] * dirs[2 + k]; Q.append(q)
            return Q
        def prof(Ps):
            ks, ls = [], []
            for P in Ps:
                d1 = bez_d1(P, ts); ks.append(np.abs(_k(P, ts))); ls.append(np.linalg.norm(d1, axis=1))
            seg_len = [np.trapezoid(l, ts) for l in ls]
            return ks, seg_len
        kr, lr = prof(R0)
        sp_idx = [ch["spine"]["gi"]] + ch["spine"]["offs"] + [ch["spine"]["gj"]]
        S_new = np.array([pos(i) for i in sp_idx]); S_up = np.array([U.xy[i] for i in sp_idx])
        endJ = 0 if ch["spine"]["gi"] == ch["J"] else 3
        kJ_sp = abs(_k(S_new, [endJ / 3.0])[0]); kJ_up_sp = abs(_k(S_up, [endJ / 3.0])[0])
        rJ = abs(_k(R0[0], [0.0])[0]) / max(kJ_up_sp, 1e-9)
        rF = abs(_k(R0[0], [1.0])[0]) / max(abs(_k(R0[1], [0.0])[0]), 1e-9)
        def res(x):
            Q = build(x); kn, ln = prof(Q)
            scale = sum(lr) / max(sum(ln), 1e-9)
            r = [20 * (abs(_k(Q[0], [0.0])[0]) - rJ * kJ_sp) / max(kJ_sp, 1e-9),
                 20 * (abs(_k(Q[0], [1.0])[0]) - rF * abs(_k(Q[1], [0.0])[0])) / max(abs(_k(Q[1], [0.0])[0]), 1e-9)]
            for k in range(2):
                tgt = kr[k] * scale; r += list(w_prof * (kn[k] - tgt) / max(tgt.max(), 1e-9))
            r += [w_keep * (v - 1.0) for v in x]          # the least change of the handles (w_keep > 0)
            return r
        sol = least_squares(res, [1.0] * 4, bounds=([lo] * 4, [hi] * 4))
        Q = build(sol.x)
        for ix, q in zip(idxs, Q):
            for i, p in zip(ix[1:3], q[1:3]):
                flat[i][0], flat[i][1] = float(p[0]), float(p[1])
        rep.append(dict(J=ch["J"], F=ch["F"], handles=[round(float(v), 3) for v in sol.x]))
    return cs, rep


def _k(P, ts):
    from comb_p2 import _kappa
    return _kappa(P, ts)


from skeleton import bez_d1
