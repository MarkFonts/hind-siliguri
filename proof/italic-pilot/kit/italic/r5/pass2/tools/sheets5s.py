"""Round 5 · s round: the proof sheets (sheets/), all from src/s_drawn.json and readings/ (run run5s.py first).

sheets5s.py [score|skeleton|thickness|psi|cuts|18|all]

  s_score.png      14.04 deg: his drawn italic SOLID grey, over it the plain slant (red), round 5's rules on his roman
                   (blue) and round 5s (green) as outlines; the residual node vectors; a second row of SOLID fills beside
                   his solid drawing; XOR for each
  s_skeleton.png   centrelines (inscribed-ball centres) of his roman, the plain slant, his italic and round 5s, overlaid,
                   with the spine's tangent angle at its centre
  s_thickness.png  thickness along the stroke (inscribed-ball diameter, thickness5s.py) for his roman, the plain slant,
                   his italic, round 5's rules and round 5s
  s_psi.png        psi 0.80 / 1.00 / 1.18 (and the chosen 1.23) solid over his drawing
  s_cuts.png       the terminal hypotheses (a) and (b) over his drawing, zoomed on both terminals
  s_18.png         18.43 deg: upright (his roman) | plain slant | round 5s, solid, with curvature combs
"""
import sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
import drawn, drawn5s, fit5s
import thickness5s as TH
from proof5s import Sheet, COL, INK, DIM, FAINT, BG
from skeleton import bez, bez_d1, bez_d2

OUT = os.path.join(C.R5S, "sheets")
LBL = "round 5 · s round"
A14 = "14.04°  (x' = x + y/4)"
A18 = "18.43°  (x' = x + y/3)"
NAMES = dict(roman="his roman (upright)", slant="plain slant", his="his drawn italic", r5="round 5's rules on his roman", r5s="round 5s")


def load():
    D = json.load(open(drawn5s.SRC))
    R14 = json.load(open(os.path.join(C.R5S, "readings", "round5s_14.json")))
    V = json.load(open(os.path.join(C.R5S, "readings", "variants_14.json")))
    g = lambda k: D[k]["contours"]
    return dict(up=g("GeistSerifDrawnRoman_s"), sl14=g("GeistSerifDrawnSlant14_s"), sl18=g("GeistSerifDrawnSlant18_s"),
                his=g("GeistSerifMarkItalic14_s"), r5=g("GeistSerifDrawnR5rules14_s"), r5s=g("GeistSerifDrawnItalic14_s"),
                r5_18=g("GeistSerifDrawnR5rules18_s"), r5s_18=g("GeistSerifDrawnItalic18_s"), R14=R14, V=V)


def xor(a, b):
    return drawn.xor_pct(a, b)


BOX = (-40, -40, 590, 580)


# ---- s_score ---------------------------------------------------------------------------------------------------
def sheet_score(L):
    his = L["his"]
    cand = [("slant", L["sl14"]), ("r5", L["r5"]), ("r5s", L["r5s"])]
    X = {k: xor(c, his) for k, c in cand}
    W, H = 2200, 1880
    sh = Sheet(W, H)
    sh.title("/s  ·  %s  ·  scored against Mark's drawn italic s (new_italics.pdf, 2026-10-25)" % LBL, A14,
             "upright = HIS drawn roman s (anchor-free); his drawing is placed by its ink centroid on the plain slant's (no bbox, no held corners)")
    sh.key(26, 122, [("his drawn italic", COL["drawn"]), ("plain slant", COL["slant"]), ("round 5's rules on his roman", COL["r5"]), ("round 5s", COL["r5s"])], 19)
    # row 1: outlines over his solid | residual vectors
    p1 = sh.panel(20, 170, 1060, 1000, BOX); p1.frame()
    for y in (0, 545):
        p1.hline(y)
    p1.fill(his, COL["drawn"])
    for k, c in cand:
        p1.outline(c, COL[k], 2.4 if k == "r5s" else 1.8)
    sh.text(32, 180, "outlines over his solid drawing", DIM, 15)
    p2 = sh.panel(1120, 170, 1060, 1000, BOX); p2.frame()
    for y in (0, 545):
        p2.hline(y)
    p2.fill(his, (52, 52, 58)); p2.outline(his, (225, 225, 225), 1.5); p2.outline(L["r5s"], COL["r5s"], 1.6)
    pairs, extra = drawn5s.correspond(L["r5s"], his)
    Fa, Fb = drawn5s.flat(L["r5s"]), drawn5s.flat(his)
    res = []
    for a, b in pairs:
        p, q = Fa[a], Fb[b]; d = float(np.linalg.norm(q - p)); res.append(d)
        p2.dot(p, COL["r5s"], 4, fill=False)
        if d >= 1.5:
            p2.arrow(p, q, COL["alt"], 3, gain=2.0)
        if d >= 4:
            p2.label((p[0] + 2 * (q[0] - p[0]), p[1] + 2 * (q[1] - p[1])), "%.0f" % d, COL["alt"], 15)
    for b in extra:
        p2.dot(Fb[b], COL["mag"], 6)
        p2.label(Fb[b], "chamfer (no partner)", COL["mag"], 14, dx=9, dy=-8)
    for _, b in pairs:
        X_, Y_ = p2.P(Fb[b]); sh.cv.drawRect(__import__("skia").Rect.MakeXYWH(X_ - 3, Y_ - 3, 6, 6), __import__("skia").Paint(Color=__import__("skia").Color(230, 230, 230), Style=__import__("skia").Paint.kStroke_Style, StrokeWidth=1.2))
    sh.text(1132, 180, "residual: round 5s node → his corresponding node (×2, u); his 2 chamfer nodes have no partner", COL["alt"], 15)
    # row 2: solids side by side
    y2 = 1200; pw = 530
    items = [("drawn", his, "his drawn italic"), ("slant", L["sl14"], "plain slant  %.1f %%" % X["slant"]),
             ("r5", L["r5"], "round 5's rules  %.1f %%" % X["r5"]), ("r5s", L["r5s"], "round 5s  %.1f %%" % X["r5s"])]
    for k, (key, cs, nm) in enumerate(items):
        pn = sh.panel(20 + k * (pw + 20), y2 + 30, pw, 540, BOX)
        pn.hline(0); pn.hline(545)
        pn.fill(cs, COL[key] if key != "drawn" else (178, 178, 184))
        sh.text(30 + k * (pw + 20), y2, nm, COL[key] if key != "drawn" else (178, 178, 184), 21)
    sh.text(26, y2 - 26, "SOLID, side by side (same frame, same scale)", DIM, 15)
    yy = H - 92
    t = "XOR vs his drawing:  "
    sh.text(26, yy, t, INK, 22); x = 26 + sh.tlen(t, 22)
    for key in ("slant", "r5", "r5s"):
        s_ = "%s %.1f %%" % ({"slant": "plain slant", "r5": "round 5's rules", "r5s": "round 5s"}[key], X[key])
        sh.text(x, yy, s_, COL[key], 22); x += sh.tlen(s_, 22) + 30
    R = L["R14"]["xor"]
    sh.text(26, yy + 36, "terminal zones (180 u boxes round his cuts), upper / lower:  slant %.1f / %.1f  ·  round 5's rules %.1f / %.1f  ·  round 5s %.1f / %.1f %%   ·   residual nodes: median %.1f u, max %.1f u" % (
        R["slant"]["upper_terminal"], R["slant"]["lower_terminal"], R["r5_rules"]["upper_terminal"], R["r5_rules"]["lower_terminal"],
        R["r5s"]["upper_terminal"], R["r5s"]["lower_terminal"], float(np.median(res)), max(res)), DIM, 15)
    sh.text(26, yy + 60, "XOR = area of the symmetric difference / his drawing's area, 2 px/u, nonzero fill · no floor: the upright is his own roman (anchor-free, 0.7 % from his drawn roman)", FAINT, 14)
    return sh.save(os.path.join(OUT, "s_score.png"))


# ---- centrelines ---------------------------------------------------------------------------------------------------
def spine_angle(prof):
    CL = np.asarray(prof["centreline"]); m = np.asarray(prof["landmarks"][3])
    sel = CL[np.linalg.norm(CL - m, axis=1) < 45]
    c = sel.mean(axis=0); u, s, vt = np.linalg.svd(sel - c); d = vt[0]
    a = math.degrees(math.atan2(d[1], d[0])) % 180.0
    return a, m


def sheet_skeleton(L):
    his = L["his"]
    items = [("roman", L["up"], COL["roman"]), ("slant", L["sl14"], COL["slant"]), ("his", his, COL["his"]), ("r5s", L["r5s"], COL["r5s"])]
    P = {k: TH.profile(cs) for k, cs, _ in items}
    W, H = 2100, 1220
    sh = Sheet(W, H)
    sh.title("/s  ·  %s  ·  centrelines (inscribed-ball centres), overlaid" % LBL, A14,
             "spine tangent = the centreline's direction at the spine centre (a line through its points within 45 u), degrees from the horizontal")
    sh.key(26, 122, [(NAMES[k], col) for k, _, col in items], 19)
    p = sh.panel(20, 160, 1040, 1040, BOX); p.frame()
    for y in (0, 545):
        p.hline(y)
    p.fill(his, (44, 44, 50))
    for k, cs, col in items:
        p.polyline(P[k]["centreline"], col, 3.0 if k in ("his", "r5s") else 2.2)
        a, m = spine_angle(P[k])
        p.dot(m, col, 5)
    # zoom on the spine
    m0 = np.asarray(P["his"]["landmarks"][3])
    zb = (m0[0] - 170, m0[1] - 150, m0[0] + 170, m0[1] + 150)
    z = sh.panel(1080, 160, 1000, 880, zb); z.frame()
    z.fill(his, (44, 44, 50))
    yy = 1060
    for i, (k, cs, col) in enumerate(items):
        z.polyline(P[k]["centreline"], col, 3.5)
        a, m = spine_angle(P[k])
        d = np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])
        z.polyline([m - 120 * d, m + 120 * d], col, 1.2, 150)
        z.dot(m, col, 6)
        s_ = "%s  spine %.1f°" % (NAMES[k], a)
        sh.text(1090 + (i % 2) * 500, yy + (i // 2) * 34, s_, col, 20)
    ar = spine_angle(P["roman"])[0]; ah = spine_angle(P["his"])[0]; a5 = spine_angle(P["r5s"])[0]; asl = spine_angle(P["slant"])[0]
    th = math.degrees(math.atan(0.25))
    sh.text(1090, yy + 80, "spine turn from his roman (θ = %.2f°):" % th, DIM, 16)
    x = 1090
    for s_, col in (("plain slant %.1f° (%.2f θ)" % (ar - asl, (ar - asl) / th), COL["slant"]), ("his italic %.1f° (%.2f θ)" % (ar - ah, (ar - ah) / th), COL["his"]),
                    ("round 5s %.1f° (%.2f θ)" % (ar - a5, (ar - a5) / th), COL["r5s"])):
        sh.text(x, yy + 106, s_, col, 16); x += sh.tlen(s_, 16) + 24
    sh.save(os.path.join(OUT, "s_skeleton.png"))
    return {k: dict(spine_deg=round(spine_angle(P[k])[0], 2)) for k in P}


# ---- thickness -------------------------------------------------------------------------------------------------------
def sheet_thickness(L):
    items = [("roman", L["up"], COL["roman"]), ("slant", L["sl14"], COL["slant"]), ("his", L["his"], COL["his"]),
             ("r5", L["r5"], COL["r5"]), ("r5s", L["r5s"], COL["r5s"])]
    P = {k: TH.profile(cs) for k, cs, _ in items}
    Z = {k: TH.zone_stats(P[k]) for k in P}
    W, H = 2200, 1400
    sh = Sheet(W, H)
    sh.title("/s  ·  %s  ·  thickness along the stroke, terminal → bowl → spine → bowl → terminal" % LBL, A14,
             "thickness = the diameter of the largest disc inside the ink touching the outline there (inscribed ball): one instrument for all five, no pairing")
    sh.key(26, 122, [(NAMES[k], col) for k, _, col in items], 19)
    ox, oy, pw, ph = 110, 190, 2040, 820
    ymin, ymax = 20, 110
    X = lambda x: ox + x / 6.0 * pw
    Y = lambda t: oy + ph - (t - ymin) / (ymax - ymin) * ph
    import skia
    cv = sh.cv
    grid = skia.Paint(Color=skia.Color(*FAINT), StrokeWidth=1)
    for t in range(ymin, ymax + 1, 10):
        cv.drawLine(ox, Y(t), ox + pw, Y(t), grid); sh.text(ox - 46, Y(t) - 9, "%d" % t, DIM, 14)
    for i, nm in enumerate(TH.LANDMARKS):
        cv.drawLine(X(i), oy, X(i), oy + ph, grid)
        sh.text(X(i) - sh.tlen(nm, 15) / 2, oy + ph + 10, nm, DIM, 15)
    # the spine zone
    cv.drawRect(skia.Rect.MakeLTRB(X(2.4), oy, X(3.6), oy + ph), skia.Paint(Color=skia.Color(255, 255, 255, 14)))
    sh.text(X(3) - sh.tlen("spine", 15) / 2, oy + 6, "spine", DIM, 15)
    for k, cs, col in items:
        x, th = P[k]["x"], P[k]["th"]
        pth = skia.Path(); pen = False
        for xi, ti in zip(x, th):
            if not np.isfinite(ti):
                pen = False; continue
            if pen:
                pth.lineTo(X(xi), Y(ti))
            else:
                pth.moveTo(X(xi), Y(ti)); pen = True
        cv.drawPath(pth, skia.Paint(AntiAlias=True, Color=skia.Color(*col), Style=skia.Paint.kStroke_Style, StrokeWidth=4.0 if k in ("his", "r5s") else 2.6,
                                    StrokeJoin=skia.Paint.kRound_Join))
    sh.text(ox - 100, oy - 30, "u", DIM, 15)
    # table
    ty = oy + ph + 60
    cols = [("upper arm", "upper_arm"), ("upper bowl", "upper_bowl"), ("upper bowl max", "upper_bowl_max"), ("spine", "spine"), ("spine max", "spine_max"),
            ("lower bowl", "lower_bowl"), ("lower bowl max", "lower_bowl_max"), ("lower arm", "lower_arm")]
    sh.text(26, ty, "mean / max diameter by zone (u)", DIM, 16)
    for j, (nm, _) in enumerate(cols):
        sh.text(420 + j * 215, ty + 26, nm, DIM, 15)
    for i, (k, cs, col) in enumerate(items):
        sh.text(26, ty + 56 + i * 30, NAMES[k], col, 17)
        for j, (_, key) in enumerate(cols):
            sh.text(420 + j * 215, ty + 56 + i * 30, "%.1f" % Z[k][key], col, 17)
    sh.save(os.path.join(OUT, "s_thickness.png"))
    return {k: {kk: round(v, 2) for kk, v in Z[k].items()} for k in Z}


# ---- psi ---------------------------------------------------------------------------------------------------------------
def sheet_psi(L):
    his = L["his"]; V = L["V"]
    import round5s
    keys = [("0.80", "psi 0.80"), ("1.00", "psi 1.00"), ("1.18", "psi 1.18"), ("%.2f chosen" % round5s.PSI, "psi %.2f" % round5s.PSI)]
    W, H = 2200, 900
    sh = Sheet(W, H)
    sh.title("/s  ·  %s  ·  I16 rigid spine piece, psi (the spine's turn = psi × θ)" % LBL, A14,
             "round 5s steps 1-6 with each psi, SOLID green at 55 % over his SOLID grey: both = light green, only ours = dark green, only his = grey · psi from his node vectors 1.23 (both spine edges), by score 1.25-1.30")
    sh.key(26, 122, [("his drawn italic", COL["drawn"]), ("round 5s", COL["r5s"])], 19)
    pw = 530
    for k, (nm, key) in enumerate(keys):
        cs = V[key]
        pn = sh.panel(20 + k * (pw + 20), 200, pw, 600, BOX)
        pn.hline(0); pn.hline(545)
        pn.fill(his, COL["drawn"]); pn.fill(cs, COL["r5s"], 140); pn.outline(cs, COL["r5s"], 1.4)
        sh.text(30 + k * (pw + 20), 168, "psi %s" % nm, COL["r5s"] if "chosen" in nm else INK, 24)
        sh.text(30 + k * (pw + 20), 810, "XOR %.1f %%" % xor(cs, his), COL["r5s"], 22)
    sh.save(os.path.join(OUT, "s_psi.png"))


# ---- cuts --------------------------------------------------------------------------------------------------------------
def sheet_cuts(L):
    his = L["his"]; V = L["V"]
    hc = fit5s.cut_angles(his)
    W, H = 2200, 1520
    sh = Sheet(W, H)
    sh.title("/s  ·  %s  ·  I15 terminals ride: the two cut-angle hypotheses" % LBL, A14,
             "(a) the leading terminal (upper, the stroke's entry) keeps the roman angle, the trailing one (lower, the exit) keeps the shear  ·  (b) a cut keeps its angle to its stroke")
    sh.key(26, 122, [("his drawn italic", COL["drawn"]), ("(a) leading roman / trailing shear", COL["r5s"]), ("(b) angle to its stroke", COL["alt"])], 19)
    hyp = [("a", "terminal a", COL["r5s"]), ("b", "terminal b", COL["alt"])]
    zones = [("upper terminal", hc[0]), ("lower terminal", hc[1])]
    pw, ph = 520, 520
    for i, (zn, cut) in enumerate(zones):
        m = cut["mid"]
        zb = (m[0] - 110, m[1] - 110, m[0] + 110, m[1] + 110)
        for j, (h, key, col) in enumerate(hyp):
            cs = V[key]
            pn = sh.panel(20 + j * (pw + 20), 230 + i * (ph + 110), pw, ph, zb); pn.frame()
            pn.fill(his, COL["drawn"]); pn.fill(cs, col, 110); pn.outline(cs, col, 2.0)
            ca = fit5s.cut_angles(cs)[i]["deg"]
            sh.text(30 + j * (pw + 20), 166 + i * (ph + 110), "(%s) %s" % (h, zn), col, 19)
            sh.text(30 + j * (pw + 20), 194 + i * (ph + 110), "cut %.1f° (his %.1f°) · XOR here %.1f %%" % (ca, cut["deg"], fit5s.zone_xor(cs, his, cut)), col, 16)
    # whole letters, small
    for j, (h, key, col) in enumerate(hyp):
        pn = sh.panel(1120 + j * 540, 230, 520, 600, BOX)
        pn.fill(his, COL["drawn"]); pn.fill(V[key], col, 110); pn.outline(V[key], col, 1.4)
        sh.text(1130 + j * 540, 166, "(%s) whole letter" % h, col, 19)
        sh.text(1130 + j * 540, 194, "XOR %.1f %%" % xor(V[key], his), col, 16)
    R = L["R14"]["skeleton"]["terminals"]
    y = 900
    sh.text(1120, y, "cut angles from vertical, + = top leans right (his drawing / roman / plain slant / (a) / (b))", DIM, 16)
    sl = fit5s.cut_angles(L["sl14"]); ro = fit5s.cut_angles(L["up"]); a = fit5s.cut_angles(V["terminal a"]); b = fit5s.cut_angles(V["terminal b"])
    for i, nm in enumerate(("upper", "lower")):
        sh.text(1120, y + 34 + i * 32, "%s:" % nm, INK, 18)
        x = 1230
        for s_, col in (("his %.1f°" % hc[i]["deg"], COL["his"]), ("roman %.1f°" % ro[i]["deg"], COL["roman"]), ("slant %.1f°" % sl[i]["deg"], COL["slant"]),
                        ("(a) %.1f°" % a[i]["deg"], COL["r5s"]), ("(b) %.1f°" % b[i]["deg"], COL["alt"])):
            sh.text(x, y + 34 + i * 32, s_, col, 18); x += sh.tlen(s_, 18) + 26
    lines = ["(a) puts both cuts on his angles by construction; (b) turns them the wrong way: the stroke turns about the same",
             "at both terminals under the bowls' lean (−6.4° upper, −5.4° lower), so (b) cannot tell the two terminals apart",
             "and his drawing does. The class that does tell them apart is the stroke's direction: entry vs exit."]
    for i, s_ in enumerate(lines):
        sh.text(1120, y + 120 + i * 26, s_, DIM, 15)
    sh.save(os.path.join(OUT, "s_cuts.png"))


# ---- 18.43 -------------------------------------------------------------------------------------------------------------
def comb_paths(cs, gain=2400.0, n=40):
    """curvature comb per cubic: teeth from the curve along the normal by gain x curvature (u)"""
    out = []
    for c in cs:
        ns = c["nodes"]; N = len(ns)
        ons = [i for i in range(N) if ns[i][2] != "o"]
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [k % N for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
            if len(offs) != 2:
                continue
            P = np.array([ns[i][:2], ns[offs[0]][:2], ns[offs[1]][:2], ns[j][:2]], float)
            ts = np.linspace(0, 1, n); B = bez(P, ts); d1 = bez_d1(P, ts); d2 = bez_d2(P, ts)
            sp = np.linalg.norm(d1, axis=1); k = (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.maximum(sp ** 3, 1e-9)
            nrm = np.stack([-d1[:, 1], d1[:, 0]], axis=1) / np.maximum(sp, 1e-9)[:, None]
            tips = B - nrm * (k * gain)[:, None]
            out.append((B, tips))
    return out


def sheet_18(L):
    items = [("roman", L["up"], "upright: his roman"), ("slant", L["sl18"], "plain slant 18.43°"), ("r5s", L["r5s_18"], "round 5s at 18.43°")]
    W, H = 2200, 1540
    sh = Sheet(W, H)
    sh.title("/s  ·  %s  ·  the deliverable angle" % LBL, A18,
             "same rules and parameters as at 14.04° (rho 0.70, nu 0, psi 1.23 x θ, terminals (a), I17 rigid-wins, I13, harmonizer last); no drawing exists at this angle")
    pw = 700
    for k, (key, cs, nm) in enumerate(items):
        col = COL[key]
        pn = sh.panel(20 + k * (pw + 20), 190, pw, 620, (-40, -40, 640, 580))
        pn.hline(0); pn.hline(545)
        pn.fill(cs, col)
        sh.text(30 + k * (pw + 20), 158, nm, col, 22)
        pc = sh.panel(20 + k * (pw + 20), 860, pw, 620, (-40, -40, 640, 580))
        pc.outline(cs, (150, 150, 155), 1.2)
        for B, tips in comb_paths(cs):
            for b, t in zip(B, tips):
                pc.polyline([b, t], COL["alt"], 0.8, 150)
            pc.polyline(tips, COL["alt"], 1.4)
        pc.nodes(cs, (230, 230, 230), 3)
    sh.text(26, 830, "curvature combs (teeth = 2400 × curvature, u; same gain for all three)", COL["alt"], 16)
    sh.save(os.path.join(OUT, "s_18.png"))


def main(what):
    L = load()
    out = {}
    if what in ("score", "all"):
        print(sheet_score(L))
    if what in ("skeleton", "all"):
        out["skeleton"] = sheet_skeleton(L)
    if what in ("thickness", "all"):
        out["thickness"] = sheet_thickness(L)
    if what in ("psi", "all"):
        sheet_psi(L)
    if what in ("cuts", "all"):
        sheet_cuts(L)
    if what in ("18", "all"):
        sheet_18(L)
    if out:
        p = os.path.join(C.R5S, "readings", "sheets5s_%s.json" % what)
        json.dump(out, open(p, "w"), indent=1); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    C.set_slant(0.25)
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
