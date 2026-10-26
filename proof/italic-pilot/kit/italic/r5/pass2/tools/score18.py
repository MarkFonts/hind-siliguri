"""Round 5 · pass 2: the score against Mark's NEW drawn italic s and n (drawn for 18.43 deg; his stems measure theta_d),
and what he changed between his 14.04 deg and his new s.

score18.py  -> sheets/score_s_18.png, score_n_18.png, s_14_vs_18_drawn.png, readings/score18.json

Candidates (every one from the same upright: his drawn roman s, the extracted Regular n):
  plain slant, pass 1's rules, pass 2b       at K_d = tan(theta_d) (the fair angle) and at K = 1/3 (the deliverable)
Placement: the s by ink centroid on the plain slant's; the n by its stems (XOR optimum inside y 60..330).
"""
import sys, os, json, math, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
import drawn, drawn5s, drawn18
import thickness5s as TH
from round_p2 import correct
from proof5s import Sheet, INK, DIM, FAINT
from score_p2 import residual, onc

OUT = os.path.join(C.R5, "sheets")
LBL = "round 5 · pass 2"
COL = dict(drawn=(112, 112, 118), drawnS=(178, 178, 184), slant=(240, 72, 58), p1=(80, 145, 255), p2=(90, 222, 118),
           p2k=(80, 200, 235), alt=(250, 200, 70), d14=(225, 110, 230))


def sheared(cs, k):
    return [{"closed": c["closed"], "nodes": [[n[0] + k * n[1], n[1]] + list(n[2:]) for n in c["nodes"]]} for c in cs]


def G_at(K):
    """pass 2's sources with the Slant keys at K (the Regular keys of the _18 file)"""
    C.set_slant(1 / 3); G = dict(C.load())
    for g in ("s", "n"):
        up = G["GeistSerifRegular_" + g]
        G["GeistSerifSlant_" + g] = {"contours": sheared(up["contours"], K), "width": up["width"], "master": "Slant", "glyph": g}
    C.set_slant(K)
    return G


def candidates(Kd):
    p1kd = os.path.join(C.R5, "readings", "pass1_kd.json")
    subprocess.run([sys.executable, os.path.join(HERE, "pass1_at_k.py"), repr(Kd), p1kd, "s,n"], check=True)
    P1 = json.load(open(p1kd))
    Gd = G_at(Kd)
    out = {}
    for g in ("s", "n"):
        out[g] = dict(slant_kd=Gd["GeistSerifSlant_" + g]["contours"], p1_kd=P1[g], p2_kd=correct(g, Gd, "1-6")["contours"])
    G3 = G_at(1 / 3)
    for g in ("s", "n"):
        out[g].update(slant_3=G3["GeistSerifSlant_" + g]["contours"], p2_3=correct(g, G3, "1-6")["contours"],
                      p1_3=(G3.get("GeistSerifItalicPass1Rules_" + g) or G3["GeistSerifItalicPass1_" + g])["contours"])
    return out


def box(*cs):
    xs = [n[0] for c_ in cs for c in c_ for n in c["nodes"]]; ys = [n[1] for c_ in cs for c in c_ for n in c["nodes"]]
    return (min(xs) - 40, min(-40, min(ys) - 30), max(xs) + 40, max(600, max(ys) + 30))


def score_sheet(g, D, cand, X, how, ang, out, zones=None):
    rows = [("slant_kd", "plain slant", COL["slant"]), ("p1_kd", "pass 1's rules", COL["p1"]), ("p2_kd", "pass 2b", COL["p2"])]
    B = box(D, *cand.values())
    W, H = 2240, 2060
    sh = Sheet(W, H)
    sh.title("/%s  ·  %s  ·  scored against Mark's NEW drawn italic (geist-serif17 print, 2026-10-26)" % (g, LBL),
             "%.2f°  (his stems; x' = x + %.4f y)" % (ang, math.tan(math.radians(ang))),
             "upright = %s · his drawing placed by %s · pass 2b and pass 1 run at HIS stem angle (fair) and at 18.43° (the deliverable)" % (
                 "his drawn roman s" if g == "s" else "the extracted Regular n", how))
    sh.key(26, 122, [("his drawn italic", COL["drawn"])] + [(nm, col) for _, nm, col in rows], 19)
    p1 = sh.panel(20, 170, 1090, 1000, B); p1.frame()
    for y in (0, 545):
        p1.hline(y)
    p1.fill(D, COL["drawn"])
    for k, nm, col in rows:
        p1.outline(cand[k], col, 2.4 if k == "p2_kd" else 1.7)
    sh.text(32, 178, "outlines over his solid drawing (at his angle)", DIM, 15)
    p2p = sh.panel(1130, 170, 1090, 1000, B); p2p.frame()
    p2p.fill(D, (52, 52, 58)); p2p.outline(D, (225, 225, 225), 1.5); p2p.outline(cand["p2_kd"], COL["p2"], 1.6)
    res = residual(cand["p2_kd"], D)
    for p, q, d in res:
        p2p.dot(p, COL["p2"], 4, fill=False)
        if d >= 1.5:
            p2p.arrow(p, q, COL["alt"], 3, gain=2.0)
        if d >= 4:
            p2p.label(p + 2 * (q - p), "%.0f" % d, COL["alt"], 15)
    for q in onc(D):
        p2p.dot(q, (230, 230, 230), 3, fill=False)
    sh.text(1142, 178, "residual: pass 2b node → its mutual-nearest drawn node (arrows ×2, u)", COL["alt"], 15)
    y2 = 1220; pw = 535
    items = [("drawnS", D, "his drawn italic", None)] + [(k, cand[k], nm, X[k]) for k, nm, _ in rows]
    sh.text(26, y2 - 28, "SOLID, side by side (same frame, same scale); XOR against his drawing under each", DIM, 15)
    for k, (key, cs, nm, x) in enumerate(items):
        pn = sh.panel(20 + k * (pw + 20), y2, pw, 560, B)
        pn.hline(0); pn.hline(545)
        col = COL["drawnS"] if key == "drawnS" else dict((r[0], r[2]) for r in rows)[key]
        pn.fill(cs, col)
        sh.text(30 + k * (pw + 20), y2 + 566, nm + ("" if x is None else "   XOR %.1f %%" % x), col, 21)
    yy = H - 190
    t = "XOR at his angle:  "
    sh.text(26, yy, t, INK, 20); x = 26 + sh.tlen(t, 20)
    for k, nm, col in rows:
        s_ = "%s %.1f %%" % (nm, X[k]); sh.text(x, yy, s_, col, 20); x += sh.tlen(s_, 20) + 30
    t = "at 18.43° (the deliverable, against the same drawing):  "
    sh.text(26, yy + 34, t, DIM, 16); x = 26 + sh.tlen(t, 16)
    for k, nm, col in (("slant_3", "plain slant", COL["slant"]), ("p1_3", "pass 1", COL["p1"]), ("p2_3", "pass 2b", COL["p2"])):
        s_ = "%s %.1f %%" % (nm, X[k]); sh.text(x, yy + 34, s_, col, 16); x += sh.tlen(s_, 16) + 26
    if zones:
        t = "zones (XOR inside, slant / pass 1 / pass 2b):  "
        sh.text(26, yy + 64, t, DIM, 15); x = 26 + sh.tlen(t, 15)
        for zn, v in zones.items():
            s_ = "%s %.1f / %.1f / %.1f" % (zn, v["slant_kd"], v["p1_kd"], v["p2_kd"]); sh.text(x, yy + 64, s_, INK, 15); x += sh.tlen(s_, 15) + 24
    big = [d for _, _, d in res]
    sh.text(26, yy + 94, "residual nodes (pass 2b): median %.1f u, max %.1f u · XOR = area of the symmetric difference / his drawing's area, 2 px/u" % (
        float(np.median(big)), max(big)), FAINT, 14)
    return sh.save(out)


def zone_xor(cs, D, xb, yb):
    return drawn.xor_pct(cs, D, band=yb, xband=xb)


def n_zones(D):
    """the n's parts on HIS drawing's frame: feet, head flag, shoulder junction, arch top"""
    xs = [n[0] for c in D for n in c["nodes"]]; x0, x1 = min(xs), max(xs)
    # stem centre at mid height: the left stem is the leftmost ink run at y 250
    b = drawn.box_of(D, pad=2); M = drawn.mask(D, b, ppu=2.0)
    def runs(y):
        r = int(round((b[3] - y) * 2)); row = M[r]; xs_ = np.nonzero(row)[0]
        segs = np.split(xs_, np.nonzero(np.diff(xs_) > 1)[0] + 1)
        return [(b[0] + s[0] / 2, b[0] + s[-1] / 2) for s in segs if len(s)]
    l_stem = runs(250)[0]
    return {"feet": ((x0 - 10, x1 + 10), (-5, 70)),
            "head flag": ((x0 - 10, l_stem[0] + 0.33 * 300 + 60), (430, 560)),
            "shoulder": ((l_stem[1] + 0.33 * 150 - 20, l_stem[1] + 0.33 * 400 + 60), (330, 470)),
            "arch": ((l_stem[1] + 0.33 * 420, x1 + 10), (380, 560))}


def drawn_compare(D18, Kd):
    """his new s against his 14.04 deg s sheared by the stems' difference"""
    raw14 = drawn.raw_contours("s", "italic")
    d14 = sheared(raw14, Kd - 0.25)
    # the two drawings are node-compatible (38 nodes, same order): align them by the median node offset, so the
    # unchanged parts (the terminals) coincide and what moved shows
    A = np.array([n[:2] for n in d14[0]["nodes"]]); Bn = np.array([n[:2] for n in D18[0]["nodes"]])
    off = np.median(Bn - A, axis=0)
    d14 = drawn.shift(d14, float(off[0]), float(off[1]))
    A = np.array([n[:2] for n in d14[0]["nodes"]]); dd = Bn - A
    moves = sorted([(float(np.hypot(*dd[i])), i, D18[0]["nodes"][i][2], dd[i]) for i in range(len(A))], reverse=True)
    def m(cs):
        a, P = None, TH.profile(cs)
        CL = np.asarray(P["centreline"]); c3 = np.asarray(P["landmarks"][3])
        sel = CL[np.linalg.norm(CL - c3, axis=1) < 45]; cc = sel.mean(axis=0); _, _, vt = np.linalg.svd(sel - cc); d = vt[0]
        spine = math.degrees(math.atan2(d[1], d[0])) % 180.0
        b = drawn.box_of(cs, pad=2); M = drawn.mask(cs, b, ppu=2.0)
        H, W = M.shape; yy = b[3] - (np.arange(H) + 0.5) / 2
        rows = np.nonzero(M.any(axis=1))[0]; top, bot = yy[rows.min()], yy[rows.max()]
        cols = np.nonzero(M.any(axis=0))[0]
        waist = float(c3[1])
        def width_at(y):
            r = int(round((b[3] - y) * 2)); xs = np.nonzero(M[r])[0]
            return float((xs.max() - xs.min() + 1) / 2) if len(xs) else float("nan")
        # cut angles: the longest straight segment in each terminal (upper / lower half)
        ns = cs[0]["nodes"]; N = len(ns); cuts = []
        for i in range(N):
            a_, b_ = ns[i], ns[(i + 1) % N]
            if a_[2] != "o" and b_[2] != "o":
                L = math.hypot(b_[0] - a_[0], b_[1] - a_[1]); cuts.append((L, a_, b_))
        def cut_ang(upper):
            c_ = max([c for c in cuts if ((c[1][1] + c[2][1]) / 2 > waist) == upper], key=lambda c: c[0])
            e = np.array(c_[2][:2]) - np.array(c_[1][:2]); e = e if e[1] > 0 else -e
            return math.degrees(math.atan2(e[0], e[1])), c_[0]
        cu, lu = cut_ang(True); cl, ll = cut_ang(False)
        return dict(width=round(float((cols.max() - cols.min() + 1) / 2), 1), spine=round(spine, 1), waist=round(waist, 1),
                    upper_h=round(top - waist, 1), lower_h=round(waist - bot, 1), w_upper=round(width_at(waist + 0.5 * (top - waist)), 1),
                    w_lower=round(width_at(bot + 0.5 * (waist - bot)), 1), cut_upper=round(cu, 1), cut_upper_len=round(lu, 1),
                    cut_lower=round(cl, 1), cut_lower_len=round(ll, 1), centreline=CL, top=round(top, 1), bottom=round(bot, 1))
    M18, M14 = m(D18), m(d14)
    x = drawn.xor_pct(d14, D18)
    W, H = 2240, 1500
    sh = Sheet(W, H)
    sh.title("/s  ·  what Mark changed between his two italic s drawings  ·  %s" % LBL, "%.2f°  (his new stems)" % math.degrees(math.atan(Kd)),
             "his 14.04° s (new_italics.pdf, 2026-10-25) sheared by the stems' difference (x + %.4f y), aligned node for node, against his NEW s (2026-10-26); yellow dots = nodes that moved > 3 u" % (Kd - 0.25))
    sh.key(26, 122, [("his NEW s (18°)", COL["drawnS"]), ("his 14° s, sheared to his new angle", COL["d14"])], 19)
    B = box(D18, d14)
    p = sh.panel(20, 170, 720, 760, B); p.frame(); p.hline(0); p.hline(545); p.fill(D18, (150, 150, 156)); p.outline(d14, COL["d14"], 2.4)
    sh.text(30, 178, "outline over his new solid", DIM, 15)
    q = sh.panel(760, 170, 720, 760, B); q.frame(); q.hline(0); q.hline(545); q.fill(D18, COL["drawnS"])
    sh.text(770, 178, "his NEW s", COL["drawnS"], 16)
    r = sh.panel(1500, 170, 720, 760, B); r.frame(); r.hline(0); r.hline(545); r.fill(d14, COL["d14"])
    sh.text(1510, 178, "his 14° s, sheared", COL["d14"], 16)
    c = sh.panel(20, 950, 720, 520, B); c.frame(); c.fill(D18, (44, 44, 50))
    c.polyline(M18["centreline"], COL["drawnS"], 2.6); c.polyline(M14["centreline"], COL["d14"], 2.2)
    sh.text(30, 958, "centrelines (inscribed-ball centres)", DIM, 15)
    y = 960; x0 = 770
    rows = [("ink width", "width", "u"), ("spine angle (centreline at the spine centre)", "spine", "°"), ("waist height", "waist", "u"),
            ("upper bowl height", "upper_h", "u"), ("lower bowl height", "lower_h", "u"), ("upper bowl width (mid-height)", "w_upper", "u"),
            ("lower bowl width (mid-height)", "w_lower", "u"), ("upper cut angle (from vertical)", "cut_upper", "°"),
            ("upper cut length", "cut_upper_len", "u"), ("lower cut angle", "cut_lower", "°"), ("lower cut length", "cut_lower_len", "u")]
    sh.text(x0, y, "%-46s %10s %12s %8s" % ("", "his new", "his 14° sh.", "change"), INK, 16); y += 30
    for nm, k, u in rows:
        a_, b_ = M18[k], M14[k]
        sh.text(x0, y, "%-46s %9.1f%s %11.1f%s %+7.1f" % (nm, a_, u, b_, u, a_ - b_), INK, 16); y += 28
    sh.text(x0, y + 10, "XOR between the two drawings: %.1f %%  (aligned by the median node offset: the drawings are node-compatible)" % x, COL["alt"], 16)
    y += 44
    sh.text(x0, y, "largest node moves, new − old (u):", INK, 15); y += 24
    for L_, i, typ, v in moves[:8]:
        sh.text(x0, y, "node %2d %s  %5.1f u  (%+.1f, %+.1f)" % (i, "on-curve" if typ != "o" else "handle  ", L_, v[0], v[1]), DIM, 14); y += 22
    for i in range(len(A)):
        if np.hypot(*dd[i]) > 3:
            q.dot(Bn[i], COL["alt"], 4)
    sh.save(os.path.join(OUT, "s_14_vs_18_drawn.png"))
    R14 = {k: v for k, v in M14.items() if k != "centreline"}; R14["node_moves"] = [(i, round(L_, 1), [round(float(c), 1) for c in v]) for L_, i, _, v in moves[:12]]
    return {k: v for k, v in M18.items() if k != "centreline"}, R14, x


def main():
    th, angs = drawn18.stem_angle(); Kd = math.tan(math.radians(th))
    cand = candidates(Kd)
    R = dict(theta_d=round(th, 3), K_d=round(Kd, 5), stem_sides=angs)
    C.set_slant(Kd)
    for g in ("s", "n"):
        raw = drawn18.raw(g)
        if g == "s":
            D = drawn18.place_centroid(raw, cand[g]["slant_kd"]); how = "ink centroid on the plain slant's"
        else:
            D, e = drawn18.place_stems(raw, cand[g]["slant_kd"]); how = "its stems (XOR optimum inside y 60..330: %.1f %%)" % e
        X = {k: drawn.xor_pct(v, D) for k, v in cand[g].items()}
        zones = None
        if g == "n":
            Z = n_zones(D)
            zones = {zn: {k: round(zone_xor(cand[g][k], D, xb, yb), 1) for k in ("slant_kd", "p1_kd", "p2_kd")} for zn, (xb, yb) in Z.items()}
        score_sheet(g, D, cand[g], X, how, th, os.path.join(OUT, "score_%s_18.png" % g), zones)
        R[g] = dict(xor={k: round(v, 2) for k, v in X.items()}, placed=how, zones=zones)
        if g == "s":
            m18, m14, xx = drawn_compare(D, Kd)
            R["s_drawings"] = dict(new=m18, old_sheared=m14, xor_between=round(xx, 2))
    json.dump(R, open(os.path.join(C.R5, "readings", "score18.json"), "w"), indent=1, default=float)
    print(json.dumps(R, indent=1, default=float))


if __name__ == "__main__":
    main()
