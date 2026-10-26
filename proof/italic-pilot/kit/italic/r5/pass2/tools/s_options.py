"""Round 5 · pass 2: skeletal deformation OPTIONS for the italic s (Mark: "show me skeletal deformation options with s
italic"). Every option is a CLASS rule with one or two parameters, applied to HIS drawn roman s (anchor-free, the
pass-2 source) and run through the same pipeline (round_p2.correct: skeleton, width rules I13, harmonizer last). Node
count, order, handles and segment types never change.

  1  plain shear                      reference
  2  pass 2b                          rigid spine psi 1.23, bowls lean rho 0.70, nu 0 (shipped)
  3a old Regular s, fixed turn        psi 1.23 on the older extracted s: the spine overshoots
  3b old Regular s, TARGET angle      psi solved so the spine reaches what 2 reaches on his roman (the same end state)
  4a upright bowls                    rho = 0 for the s's bowls: only the spine turns
  4b full-lean bowls                  rho = 1
  5  bowl narrowing                   nu = 0.6 tan(theta) (the study's default)
  6a/6b smaller bowls                 bowls scaled x0.92 / x0.85 about their far extremes, the spine re-fitted to meet them
                                      (it steepens; its chord stays within 1 %); tested and dropped for 'a longer spine': the stretch along the spine (bowls
                                      pushed apart sideways) and a vertical push (the spine stood up, the bowls flattened)
  7  raised waist                     the spine piece raised 5 % of the x-height: lower bowl larger, upper smaller
  8  stress slide + thinning          counters turned 3.5 deg clockwise (thick zones slide ~6 u), arms -6 u, hairlines -4 u
  9  his drawn italic                 14.04 deg as drawn; 18.43 deg = his italic sheared by the stems' difference (y/12),
                                      an EXTRAPOLATION

Options 6-8 change the UPRIGHT (a deformed roman), then the shipped rules make it italic.

s_options.py      -> sheets/s_options_18.png, s_options_14.png, word_saopne_18_options.png, readings/s_options.json
"""
import sys, os, json, math, copy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
import drawn, drawn5s, curvcomb
import thickness5s as TH
from round_p2 import correct
from skeleton_p2 import SkeletonP2
from proof5s import Sheet, INK, DIM, FAINT

OUT = os.path.join(C.R5, "sheets")
LBL = "round 5 · pass 2 · s options"


def load(K):
    C.set_slant(K)
    return C.load()


def sheared(cs, k):
    return [{"closed": c["closed"], "nodes": [[n[0] + k * n[1], n[1]] + list(n[2:]) for n in c["nodes"]]} for c in cs]


def with_s(G, up_cs):
    """a copy of G whose s is the given upright (and its slant)"""
    H = dict(G)
    H["GeistSerifRegular_s"] = {"contours": up_cs, "width": G["GeistSerifRegular_s"]["width"], "master": "Regular (option)", "glyph": "s"}
    H["GeistSerifSlant_s"] = {"contours": sheared(up_cs, C.K), "width": G["GeistSerifRegular_s"]["width"], "master": "Slant", "glyph": "s"}
    return H


# ---- the s's classes on an upright (spine piece, bowls, terminals) ------------------------------------------------
class SParts:
    def __init__(self, up):
        self.up = up
        Sk = SkeletonP2({"contours": up, "width": 470.0, "master": "Regular", "glyph": "s"})
        self.Sk = Sk; U = Sk.U; self.U = U
        segs = Sk.spine_segments()
        self.spine_nodes = set()
        for sg, _ in segs:
            self.spine_nodes |= {sg["gi"], sg["gj"], *sg["offs"]}
        self.junctions = {sg["gi"] for sg, _ in segs} | {sg["gj"] for sg, _ in segs}
        self.m = np.mean([U.xy[j] for j in self.junctions], axis=0)
        P = np.array([U.xy[i] for i in self.spine_nodes]); c = P.mean(axis=0)
        _, _, vt = np.linalg.svd(P - c); d = vt[0]
        self.d = d if d[0] > 0 else -d            # spine direction, pointing right (down the \)
        self.owner = lambda i: i if U.typ[i] != "o" else U.owner[i]
        self.upper = lambda i: U.xy[self.owner(i)][1] > self.m[1]
        ys = [p[1] for p in U.xy]
        self.top, self.bottom = max(ys), min(ys)

    def deform(self, T):
        """the spine piece by the map T (on points); each bowl (with its terminal) by an affine map fixing its far
        extreme's height and keeping horizontals horizontal, fitted so the bowl meets its moved junctions"""
        U = self.U; new = [np.array(p, float) for p in U.xy]
        for i in self.spine_nodes:
            new[i] = T(U.xy[i])
        for upper in (True, False):
            J = [j for j in self.junctions if (U.xy[j][1] > self.m[1]) == upper]
            pj = np.mean([U.xy[j] for j in J], axis=0); dj = np.mean([T(U.xy[j]) - U.xy[j] for j in J], axis=0)
            ye = self.top if upper else self.bottom
            sy = (pj[1] + dj[1] - ye) / (pj[1] - ye); kx = dj[0] / (pj[1] - ye)
            for i in range(len(U.xy)):
                if i in self.spine_nodes or self.upper(i) != upper:
                    continue
                x, y = U.xy[i]
                new[i] = np.array([x + kx * (y - ye), ye + (y - ye) * sy])
        return self._contours(new)

    def shrink_bowls(self, s):
        """each bowl (with its terminal) scaled by s about its far extreme (the top of the upper bowl's outer run, the
        bottom of the lower's); the spine piece is the affine map that carries its four junctions onto the shrunk
        bowls' junctions (least squares), so it lengthens as the bowls shrink: smaller bowls, a longer spine, the height
        kept. Returns (contours, spine chord growth)"""
        U = self.U; new = [np.array(p, float) for p in U.xy]
        maps = {}
        for upper in (True, False):
            ids = [i for i in range(len(U.xy)) if i not in self.spine_nodes and self.upper(i) == upper]
            ons = [i for i in ids if U.typ[i] != "o"]
            e = max((U.xy[i] for i in ons), key=lambda p: p[1]) if upper else min((U.xy[i] for i in ons), key=lambda p: p[1])
            maps[upper] = (lambda e: (lambda p: e + s * (np.asarray(p, float) - e)))(np.array(e, float))
            for i in ids:
                new[i] = maps[upper](U.xy[i])
        J = sorted(self.junctions)
        A_ = []; b_ = []
        for j in J:
            q = maps[U.xy[j][1] > self.m[1]](U.xy[j]); x, y = U.xy[j]
            A_ += [[x, y, 1, 0, 0, 0], [0, 0, 0, x, y, 1]]; b_ += [q[0], q[1]]
        a = np.linalg.lstsq(np.array(A_), np.array(b_), rcond=None)[0]
        L = np.array([[a[0], a[1]], [a[3], a[4]]]); tvec = np.array([a[2], a[5]])
        for i in self.spine_nodes:
            new[i] = L @ U.xy[i] + tvec
        up = [j for j in J if U.xy[j][1] > self.m[1]]; lo = [j for j in J if U.xy[j][1] <= self.m[1]]
        c0 = np.linalg.norm(np.mean([U.xy[j] for j in up], axis=0) - np.mean([U.xy[j] for j in lo], axis=0))
        c1 = np.linalg.norm(np.mean([new[j] for j in up], axis=0) - np.mean([new[j] for j in lo], axis=0))
        return self._contours(new), c1 / c0 - 1

    def _contours(self, new):
        out = []; k = 0
        for c in self.up:
            ns = []
            for n in c["nodes"]:
                ns.append([float(new[k][0]), float(new[k][1])] + list(n[2:])); k += 1
            out.append({"closed": c["closed"], "nodes": ns})
        return out


def stretch(SP, e):
    """along the spine itself (the coordinator's wording): tested, it pushes the bowls apart SIDEWAYS (XOR 30.9 / 50.6 %)"""
    m, d = SP.m, SP.d
    return lambda p: np.asarray(p, float) + e * d * float(np.dot(np.asarray(p, float) - m, d))


def lengthen(SP, e):
    """the spine piece pushed apart VERTICALLY about its centre so that the chord between its junction pairs grows by
    e; the bowls then flatten to keep the height (SParts.deform) and the width stays: a longer, steeper spine"""
    U = SP.U; m = SP.m
    up = np.mean([U.xy[j] for j in SP.junctions if U.xy[j][1] > m[1]], axis=0)
    lo = np.mean([U.xy[j] for j in SP.junctions if U.xy[j][1] <= m[1]], axis=0)
    cx, cy = up - lo
    sv = math.sqrt(max(((1 + e) ** 2 * (cx * cx + cy * cy) - cx * cx) / (cy * cy), 1.0))
    return lambda p: m + np.array([1.0, sv]) * (np.asarray(p, float) - m)


def raise_waist(SP, dy):
    return lambda p: np.asarray(p, float) + np.array([0.0, dy])


def stress(SP, alpha_deg=3.5, arm=6.0, hair=4.0):
    """counters turned clockwise about their bowl's centre (the thick zones slide along the bowls: the upper bowl
    thickens earlier down its left side, the lower stays thick longer down its right, as in his drawing); each arm
    thinned at its terminal by moving the cut's counter-side end along the cut toward the outer side; each bowl's
    hairline thinned by moving the counter's extreme away from the counter"""
    Sk, U = SP.Sk, SP.U
    new = [np.array(p, float) for p in U.xy]
    a = -math.radians(alpha_deg); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    moved = set()
    for r in Sk.runs:
        if not r["counter"]:
            continue
        c = Sk.runs[r["part"]]["c"]
        for nd in r["nodes"]:
            for i in [nd] + [h for h in range(len(U.xy)) if U.typ[h] == "o" and U.owner[h] == nd]:
                new[i] = c + R @ (U.xy[i] - c); moved.add(i)
        # hairline: the counter's extreme node (top of the upper counter, bottom of the lower) away from the counter
        ext = max(r["nodes"], key=lambda n: U.xy[n][1]) if r["c"][1] > SP.m[1] else min(r["nodes"], key=lambda n: U.xy[n][1])
        dy = hair if U.xy[ext][1] > SP.m[1] else -hair
        for i in [ext] + [h for h in range(len(U.xy)) if U.typ[h] == "o" and U.owner[h] == ext]:
            new[i] = new[i] + np.array([0.0, dy])
    for t in Sk.term_report:
        nodes = t["nodes"]
        cnt = {i for r in Sk.runs if r["counter"] for i in r["nodes"]}
        first, last = nodes[0], nodes[-1]
        prev_counter = any(i in cnt for i in [U.seg_before[first]["gi"]])
        inner, outer = (first, last) if prev_counter else (last, first)
        v = U.xy[outer] - U.xy[inner]; v = v / np.linalg.norm(v)
        for i in [inner] + [h for h in range(len(U.xy)) if U.typ[h] == "o" and U.owner[h] == inner]:
            new[i] = new[i] + arm * v
    return SP._contours(new)


# ---- measurements ------------------------------------------------------------------------------------------------
def spine_angle(cs):
    P = TH.profile(cs); CL = np.asarray(P["centreline"]); m = np.asarray(P["landmarks"][3])
    sel = CL[np.linalg.norm(CL - m, axis=1) < 45]
    c = sel.mean(axis=0); _, _, vt = np.linalg.svd(sel - c); d = vt[0]
    return math.degrees(math.atan2(d[1], d[0])) % 180.0, P


def measures(cs):
    a, P = spine_angle(cs)
    b = drawn.box_of(cs, pad=2); M = drawn.mask(cs, b, ppu=2.0)
    H, W = M.shape; yy = b[3] - (np.arange(H) + 0.5) / 2; xx = b[0] + (np.arange(W) + 0.5) / 2
    rows = np.nonzero(M.any(axis=1))[0]; top, bot = yy[rows.min()], yy[rows.max()]
    cols = np.nonzero(M.any(axis=0))[0]
    waist = float(P["landmarks"][3][1])
    def width_at(y):
        r = int(round((b[3] - y) * 2)); xs = np.nonzero(M[r])[0]
        return float((xs.max() - xs.min() + 1) / 2) if len(xs) else float("nan")
    return dict(spine=round(a, 1), waist=round(waist, 1), upper_h=round(top - waist, 1), lower_h=round(waist - bot, 1),
                width=round(float((cols.max() - cols.min() + 1) / 2), 1), w_upper=round(width_at(waist + 0.5 * (top - waist)), 1),
                w_lower=round(width_at(bot + 0.5 * (waist - bot)), 1), centreline=np.asarray(P["centreline"]))


class Mv:
    def __init__(self, a, b):
        self.a, self.b = a, b

    def contours_at(self, t):
        return [{"closed": ca["closed"], "nodes": [[na[0] + (nb[0] - na[0]) * t, na[1] + (nb[1] - na[1]) * t] + list(na[2:])
                                                   for na, nb in zip(ca["nodes"], cb["nodes"])]} for ca, cb in zip(self.a, self.b)]


# ---- the options -------------------------------------------------------------------------------------------------
COLS = [(240, 72, 58), (90, 222, 118), (250, 150, 60), (250, 200, 70), (80, 200, 235), (80, 145, 255), (225, 110, 230),
        (180, 230, 90), (130, 210, 170), (255, 120, 160), (200, 160, 255), (178, 178, 184)]


def psi_for_target(G, up_cs, target, steps=24):
    lo, hi = 0.3, 2.2
    for _ in range(steps):
        mid = (lo + hi) / 2
        a = spine_angle(correct("s", with_s(G, up_cs), "1-3", psi=mid)["contours"])[0]
        if a > target:          # not turned enough (angles fall as the spine turns clockwise)
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def build(K):
    G = load(K)
    up = G["GeistSerifRegular_s"]["contours"]; old = G["GeistSerifRegularOld_s"]["contours"]
    SP = SParts(up)
    O = []
    def add(key, name, rule, up_cs, contours, src):
        O.append(dict(key=key, name=name, rule=rule, up=up_cs, cs=contours, src=src))
    add("1", "plain shear", "x' = x + K y", up, sheared(up, K), "reference")
    p2 = correct("s", G, "1-6")["contours"]
    add("2", "pass 2b (shipped)", "spine rigid psi 1.23, bowls rho 0.70, nu 0", up, p2, "pass 2b")
    add("3a", "old Regular s, fixed turn", "psi 1.23 on the older extracted s", old, correct("s", with_s(G, old), "1-6")["contours"],
        "the turn rule (s round)")
    target = spine_angle(correct("s", G, "1-3")["contours"])[0]
    psi_t = psi_for_target(G, old, target)
    add("3b", "old Regular s, TARGET angle", "spine to %.1f deg (what 2 reaches on his roman): psi %.2f" % (target, psi_t), old,
        correct("s", with_s(G, old), "1-6", psi=psi_t)["contours"], "an angle the italic spine reaches")
    add("4a", "upright bowls", "rho 0: only the spine turns", up, correct("s", G, "1-6", rho=0.0)["contours"], "study parameter A, rho = 0")
    add("4b", "full-lean bowls", "rho 1: bowls lean with the stems", up, correct("s", G, "1-6", rho=1.0)["contours"], "study parameter A, rho = 1")
    add("5", "bowl narrowing", "nu = 0.6 tan(theta) (%.0f %%)" % (60 * K), up, correct("s", G, "1-6", nu_coef=0.6)["contours"],
        "study parameter B default")
    for s_, k in ((0.92, "6a"), (0.85, "6b")):
        u2, grow = SP.shrink_bowls(s_)
        add(k, "smaller bowls x%.2f" % s_, "bowls x%.2f about their extremes, spine re-fitted (chord %+.0f %%)" % (s_, 100 * grow), u2,
            correct("s", with_s(G, u2), "1-6")["contours"], "narrow italic s (chancery)")
    u7 = SP.deform(raise_waist(SP, 0.05 * 545))
    add("7", "raised waist +5 %", "spine raised 27 u: lower bowl larger", u7, correct("s", with_s(G, u7), "1-6")["contours"],
        "the bigger lower bowl of most text s")
    u8 = stress(SP)
    add("8", "stress slide + thinning", "counters -3.5 deg, arms -6 u, hairlines -4 u", u8, correct("s", with_s(G, u8), "1-6")["contours"],
        "his drawing (s round thickness reading)")
    raw = drawn.raw_contours("s", "italic")
    sl14 = sheared(up, 0.25)
    his14 = drawn.shift(raw, drawn5s.centroid_x(sl14) - drawn5s.centroid_x(raw))
    his = his14 if abs(K - 0.25) < 1e-9 else sheared(his14, K - 0.25)
    add("9", "his drawn italic" + ("" if abs(K - 0.25) < 1e-9 else " (EXTRAPOLATED: + y/12)"), "as drawn at 14.04 deg", None, his, "Mark")
    for i, o in enumerate(O):
        o["col"] = COLS[i % len(COLS)]
    return G, O, his14


def run():
    R = {}
    G14, O14, his14 = build(0.25)
    for o in O14:
        o["xor"] = drawn.xor_pct(o["cs"], his14) if o["key"] != "9" else 0.0
    G18, O18, _ = build(1.0 / 3.0)
    for o in O18:
        o["m"] = measures(o["cs"])
        if o["up"] is not None and o["key"] != "1":
            sl = {"contours": sheared(o["up"], 1.0 / 3.0), "glyph": "s", "master": "Slant", "width": 470.0}
            ev = curvcomb.evaluate(sl, Mv(sl["contours"], o["cs"]))
            o["comb"] = (len(ev["snaps"]), len(ev["spikes"]), len(ev["minors"]) + len(ev["minor_spikes"]))
        else:
            o["comb"] = None
    up_m = measures(G18["GeistSerifRegular_s"]["contours"])
    sheet18(O18, up_m, O14); sheet14(O14, his14); words(G18, O18)
    out = {o["key"]: dict(name=o["name"], rule=o["rule"], src=o["src"], xor14=round(o14["xor"], 2),
                          measures={k: v for k, v in o["m"].items() if k != "centreline"}, comb18=o["comb"])
           for o, o14 in zip(O18, O14)}
    out["roman"] = {k: v for k, v in up_m.items() if k != "centreline"}
    json.dump(out, open(os.path.join(C.R5, "readings", "s_options.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


def sheet18(O, up_m, O14):
    cols = 4; CW, CH = 600, 1010
    rows = math.ceil(len(O) / cols)
    W, H = cols * (CW + 10) + 20, 190 + rows * (CH + 10) + 260
    sh = Sheet(W, H)
    sh.title("/s  ·  skeletal deformation options  ·  %s" % LBL, "18.43°  (x' = x + y/3)",
             "SOLID at 18.43°; under each, the centreline (inscribed-ball centres): his roman grey, the option in its colour. Upright = Mark's drawn roman s, the same pipeline for every option.")
    sh.key(26, 122, [("%s %s" % (o["key"], o["name"]), o["col"]) for o in O[:6]], 14)
    sh.key(26, 146, [("%s %s" % (o["key"], o["name"]), o["col"]) for o in O[6:]], 14)
    B = (-60, -40, 640, 590)
    for k, o in enumerate(O):
        x0 = 20 + (k % cols) * (CW + 10); y0 = 180 + (k // cols) * (CH + 10)
        pn = sh.panel(x0, y0 + 30, CW, 520, B, pad=6); pn.frame(); pn.hline(0); pn.hline(545)
        pn.fill(o["cs"], o["col"])
        pc = sh.panel(x0, y0 + 560, CW, 330, B, pad=6); pc.frame()
        pc.fill(o["cs"], (40, 40, 46))
        pc.polyline(up_m["centreline"] + np.array([[C.K * p[1], 0] for p in up_m["centreline"]]), (150, 150, 156), 2.0)
        pc.polyline(o["m"]["centreline"], o["col"], 2.4)
        sh.text(x0 + 8, y0 + 4, "%s  %s" % (o["key"], o["name"]), o["col"], 17)
        m = o["m"]
        sh.text(x0 + 8, y0 + 896, "spine %.1f°  waist %.0f u  bowls ↑%.0f ↓%.0f u" % (m["spine"], m["waist"], m["upper_h"], m["lower_h"]), INK, 14)
        sh.text(x0 + 8, y0 + 918, "width %.0f u (upper %.0f, lower %.0f)" % (m["width"], m["w_upper"], m["w_lower"]), INK, 14)
        x14 = O14[k]["xor"]
        sh.text(x0 + 8, y0 + 940, ("XOR 14.04° %.1f %%" % x14) if o["key"] != "9" else "his drawing (14.04° sheared + y/12)", o["col"], 14)
        sh.text(x0 + 8, y0 + 962, o["rule"][:70], DIM, 12)
    y = 190 + rows * (CH + 10)
    sh.text(26, y, "his roman (upright, sheared for the grey centreline): spine %.1f°, waist %.0f u, bowls ↑%.0f ↓%.0f u, width %.0f u" % (
        up_m["spine"], up_m["waist"], up_m["upper_h"], up_m["lower_h"], up_m["width"]), DIM, 15)
    sh.text(26, y + 30, "combs at 18.43° (curvcomb against each option's own plain slant): snaps / spikes / minor", INK, 16)
    x = 26; yy = y + 58
    for o in O:
        if o["comb"] is None:
            continue
        s_ = "%s %d/%d/%d" % (o["key"], *o["comb"])
        sh.text(x, yy, s_, o["col"], 16); x += sh.tlen(s_, 16) + 30
    sh.text(26, yy + 34, "options 6–8 deform the UPRIGHT (a different roman), then the shipped rules make it italic; 3a/3b start from the older extracted Regular s", DIM, 14)
    return sh.save(os.path.join(OUT, "s_options_18.png"))


def sheet14(O, his):
    cols = 4; CW, CH = 600, 640
    rows = math.ceil(len(O) / cols)
    W, H = cols * (CW + 10) + 20, 190 + rows * (CH + 10) + 60
    sh = Sheet(W, H)
    sh.title("/s  ·  skeletal deformation options, scored  ·  %s" % LBL, "14.04°  (x' = x + y/4)",
             "his drawn italic SOLID grey, each option SOLID green at 55 % over it (overlap = light green, only his = grey, only the option = dark green); XOR against his drawing")
    sh.key(26, 122, [("his drawn italic", (138, 138, 138)), ("the option, 55 %", (90, 222, 118))], 16)
    B = (-60, -40, 640, 590)
    for k, o in enumerate(O):
        x0 = 20 + (k % cols) * (CW + 10); y0 = 170 + (k // cols) * (CH + 10)
        pn = sh.panel(x0, y0 + 30, CW, CH - 40, B, pad=6); pn.frame(); pn.hline(0); pn.hline(545)
        pn.fill(his, (138, 138, 138))
        if o["key"] != "9":
            pn.fill(o["cs"], (90, 222, 118), 140); pn.outline(o["cs"], (90, 222, 118), 1.2)
        sh.text(x0 + 8, y0 + 4, "%s  %s   %s" % (o["key"], o["name"], ("XOR %.1f %%" % o["xor"]) if o["key"] != "9" else "(the target)"), o["col"], 16)
    return sh.save(os.path.join(OUT, "s_options_14.png"))


def words(G, O):
    """one row per option: 'saopne' with the option's s, the other letters pass 2b; white page"""
    import skia
    from PIL import Image, ImageDraw, ImageFont
    import italicsheet as IS
    IS.KERN = os.path.join(C.R5, "src", "kerning.json")
    kern, _ = IS.load_kern()
    S = 0.13; Wp = 1640; R = 4; LINE = 150; TOP = 150
    H = TOP + len(O) * LINE + 60
    surf = skia.Surface(Wp * R, H * R); cv = surf.getCanvas(); cv.clear(skia.ColorWHITE)
    for r, o in enumerate(O):
        base = TOP + (r + 1) * LINE - 28
        x = 0.0; prev = None
        for ch in "saopne saopne":
            n = IS.GNAME.get(ch, ch)
            if prev is not None:
                x += kern.get((prev, n), 0.0)
            if n == "space":
                x += G["space"]["width"] if "space" in G else 250; prev = n; continue
            cs = o["cs"] if n == "s" else G["GeistSerifItalic_" + n]["contours"]
            cv.drawPath(IS.skia_path(IS.shear(cs, -C.K), (330 + x * S) * R, base * R, S * R, C.K), skia.Paint(AntiAlias=True, Color=skia.Color(17, 17, 17)))
            x += G["GeistSerifRegular_" + n]["width"]; prev = n
    img = Image.fromarray(surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3].copy())
    img = img.resize((Wp * 2, H * 2), Image.LANCZOS)
    d = ImageDraw.Draw(img); f = lambda sz: ImageFont.truetype(IS.MENLO, int(sz * 2))
    d.text((112, 60), "GEIST SERIF  18.43°  (x' = x + y/3)", fill=(17, 17, 17), font=f(28))
    d.text((112, 140), "%s  ·  one row per option: its s, every other letter pass 2b" % LBL, fill=(110, 110, 110), font=f(14))
    for r, o in enumerate(O):
        y = 2 * (TOP + (r + 1) * LINE - 70)
        d.text((112, y), ("%s %s" % (o["key"], o["name"]))[:30], fill=tuple(int(c * 0.6) for c in o["col"]), font=f(13))
    out = os.path.join(OUT, "word_saopne_18_options.png"); img.save(out); print("wrote", out)


if __name__ == "__main__":
    run()
