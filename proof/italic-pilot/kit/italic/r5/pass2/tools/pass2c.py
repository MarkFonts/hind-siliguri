"""Round 5 · pass 2c (2026-10-26, Mark: "why are these bumpy … find GOOD LOOKING options"): the comb gate, the fixes,
and ONE recommendation.

  gate                  curvcomb (0 snaps, 0 spikes) AND comb_p2.hump (unimodal curvature per cubic, G2 jump at smooth
                        nodes <= 1.25 x the upright's, floor 0.05): anything that fails is not shown as a candidate
  pass 2c pipeline      pass 2b with
                        (1) every serif SHEARED (stem serifs too: Mark's finished n and p feet are the plain shear; I14b's
                            rigid bracket meeting the sheared stem was the a's foot curl, r 51 u), and a sheared serif's
                            bracket junction holds in the group rules (a group moving it turned the bracket: v, x peaks);
                        (2) I15 terminals: where the stroke meets the cut at a CORNER (or through a blunt < 6 u) its end
                            tangent leans with its side (side_handles="corners"); the cut keeps its class angle. The a's
                            hood curl was its end tangent held at the roman's vertical while the hood leaned;
                        (3) comb_p2.repair last: peak_repair (a cubic's interior curvature peak grown past the roman's and
                            the slant's) then g2_repair (the re-tension's per-curve handle fits broke G2 at smooth nodes;
                            the harmonizer backed off), handle lengths only, least units moved
  the s (recommended)   option 14 fixed: bowls on Mark's NEW drawn s's centreline (s_options2.mapped_post), extremes'
                        handles shortened, then the bowl chains solved jointly (s_options2.chain_solve: G2 at J and F, the
                        roman's curvature profile weight 3, handles 0.4-1.6 x, no fairness), then repair

pass2c.py -> src keys GeistSerifItalicPass2c_<g> (14 and 18), sheets/s_14fixed_18.png, a_foot_18.png,
             word_saopne_18_pass2c.png, readings/pass2c.json (the gate on every earlier result)
"""
import sys, os, json, math, copy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
import drawn, drawn18, curvcomb
import s_options2 as S2
from comb_p2 import hump, g2_repair, comb, _kappa, repair
from round_p2 import correct
from s_options import Mv, sheared
from proof5s import Sheet, INK, DIM, FAINT

OUT = os.path.join(C.R5, "sheets")
LBL = "round 5 · pass 2c"
GREEN, BLUE, RED, PINK, GREY, GOLD = (90, 222, 118), (80, 145, 255), (240, 72, 58), (255, 120, 160), (178, 178, 184), (250, 200, 70)


def gate(cs, up_cs, K):
    sl = sheared(up_cs, K)
    ev = curvcomb.evaluate({"contours": sl, "glyph": "x", "master": "Slant", "width": 500.0}, Mv(sl, cs))
    h = hump(cs, up_cs)
    return dict(snaps=len(ev["snaps"]), spikes=len(ev["spikes"]), minor=len(ev["minors"]) + len(ev["minor_spikes"]), hump=len(h),
                hump_where=[(x["kind"], x.get("node", x.get("seg"))) for x in h],
                ok=(len(ev["snaps"]) == 0 and len(ev["spikes"]) == 0 and len(h) == 0))


def letter_2c(g, G, post=None, s_fix=False, his=None):
    up = G["GeistSerifRegular_" + g]["contours"]
    cs = correct(g, G, "1-6", serif="shear", side_handles="corners", post=post, hold_brackets=True)["contours"]
    if s_fix:
        cs, _ = S2.chain_solve(cs, up, w_prof=3.0, hi=1.6)
    K = C.K
    cs, rep = repair(cs, up, K)
    return cs


def s_fixed(G, his, which):
    if which == "14":
        post = S2.chain(S2.mapped_post(his), S2.shorten_post(None))
    elif which == "13":
        post = S2.shorten_post(his)
    else:
        post = None
    return letter_2c("s", G, post=post, s_fix=which in ("13", "14"))


def sheet_s(G, V, his, gates, X):
    W, H = 2440, 780
    sh = Sheet(W, H)
    sh.title("/s  ·  the bowls fixed, combs beside  ·  %s" % LBL, "18.43°  (x' = x + y/3)",
             "SOLID large, the curvature comb beside it (same gain). Every s here passes the comb gate: 0 snaps, 0 spikes, 0 humps. Mark's new drawing is the small reference at the right.")
    sh.key(26, 122, [(nm, col) for nm, _, col in V] + [("Mark's new s (reference)", GREY)], 18)
    B = (-60, -40, 640, 590)
    for r, (nm, cs, col) in enumerate(V):
        y = 170 + r * 560
        pn = sh.panel(20, y, 700, 540, B, pad=6); pn.frame(); pn.hline(0); pn.hline(545); pn.fill(cs, col)
        pc = sh.panel(730, y, 700, 540, B, pad=6); pc.frame(); pc.fill(cs, (46, 46, 52)); comb(pc, cs, col, gain=5000)
        pz = sh.panel(1440, y, 560, 540, (60, -40, 640, 260), pad=4); pz.frame(); pz.fill(cs, (46, 46, 52)); comb(pz, cs, col, gain=5000)
        g = gates[nm]
        sh.text(30, y + 6, nm, col, 20)
        sh.text(740, y + 6, "comb · snaps %d · spikes %d · humps %d · (curvcomb minor %d, all pass the hump test)" % (g["snaps"], g["spikes"], g["hump"], g["minor"]), col, 14)
        sh.text(1450, y + 6, "bottom bowl, comb", col, 14)
        sh.text(30, y + 516, "XOR vs his new s: at %.2f° %.1f %%, at 18.43° %.1f %%" % (S2.TH_D, X[nm][0], X[nm][1]), DIM, 14)
    ph = sh.panel(2010, 170, 410, 540, B, pad=6); ph.frame(); ph.hline(0); ph.hline(545); ph.fill(sheared(his, 1 / 3 - S2.K_D), GREY)
    sh.text(2020, 176, "his new s (+y/80 to 18.43°)", GREY, 14)
    return sh.save(os.path.join(OUT, "s_14fixed_18.png"))


def sheet_a(G, Va):
    W, H = 2440, 1360
    sh = Sheet(W, H)
    sh.title("/a  ·  the foot  ·  %s" % LBL, "18.43°  (x' = x + y/3)",
             "the a's foot between the stem and the tail (node 27) · SOLID above, comb below (same gain) · the slant's x is shifted back by the shear at the foot so the four line up")
    sh.key(26, 122, [(nm, col) for nm, _, col, _ in Va], 18)
    for k, (nm, cs, col, dx) in enumerate(Va):
        zb = (300 + dx, -30, 600 + dx, 200)
        pn = sh.panel(20 + k * 605, 170, 595, 560, zb, pad=4); pn.frame(); pn.hline(0); pn.fill(cs, col)
        pc = sh.panel(20 + k * 605, 750, 595, 560, zb, pad=4); pc.frame(); pc.fill(cs, (46, 46, 52)); comb(pc, cs, col, gain=2500)
        r = radius_at(cs, 27)
        sh.text(30 + k * 605, 176, nm, col, 18)
        sh.text(30 + k * 605, 756, "radius at node 27 (into the stem): %s" % r, col, 15)
    return sh.save(os.path.join(OUT, "a_foot_18.png"))


def sheet_hood(G, Va, out):
    W, H = 2440, 1500
    sh = Sheet(W, H)
    sh.title("/a  ·  the hood (upper-left arc into the hood terminal)  ·  %s" % LBL, "18.43°  (x' = x + y/3)",
             "SOLID above, comb below (same gain), zoomed ×3 · nodes 31 → 34 (outer arc into the cut) and 36 → 39 (counter side) · the slanted panels are shifted back by the shear at the hood")
    sh.key(26, 122, [(nm, col) for nm, _, col, _ in Va], 18)
    for k, (nm, cs, col, dx) in enumerate(Va):
        zb = (20 + dx, 330, 330 + dx, 570)
        pn = sh.panel(20 + k * 605, 170, 595, 600, zb, pad=4); pn.frame(); pn.fill(cs, col)
        pc = sh.panel(20 + k * 605, 790, 595, 600, zb, pad=4); pc.frame(); pc.fill(cs, (46, 46, 52)); comb(pc, cs, col, gain=4000)
        flat = [n for c in cs for n in c["nodes"]]
        for i in (31, 34, 36, 39):
            pc.dot(flat[i][:2], INK, 4); pc.label(flat[i][:2], str(i), INK, 14, dx=6, dy=-6)
        d = np.array(flat[33][:2]) - np.array(flat[34][:2])
        ang = math.degrees(math.atan2(d[0], d[1]))
        sh.text(30 + k * 605, 176, nm, col, 18)
        sh.text(30 + k * 605, 796, "arc end tangent at 34: %+.1f° from vertical · radius %s" % (ang, radius_at(cs, 34)), col, 14)
    return sh.save(out)


def radius_at(cs, nd):
    S = {}
    k = 0; flat = [n for c in cs for n in c["nodes"]]
    from comb_p2 import _segs
    for s in _segs(cs):
        if s["gj"] == nd and s["curve"]:
            kk = abs(_kappa(s["P"], [1.0])[0]); return "%.0f u" % (1 / kk) if kk > 1e-9 else "straight"
    return "-"


def words(G, recs, out):
    import skia
    from PIL import Image, ImageDraw, ImageFont
    import italicsheet as IS
    IS.KERN = os.path.join(C.R5, "src", "kerning.json"); kern, _ = IS.load_kern()
    lines = ["saopne saopne", "Harper’s Bazzar", "THE foxy jazz fern"]
    rows = [("pass 2c", "GeistSerifItalicPass2c_")]
    S = 0.125; Wp = 1640; R = 4; LINE = 140; TOP = 150
    H = TOP + len(rows) * (len(lines) * LINE + 60) + 40
    surf = skia.Surface(Wp * R, H * R); cv = surf.getCanvas(); cv.clear(skia.ColorWHITE)
    for r, (nm, key) in enumerate(rows):
        for li, line in enumerate(lines):
            base = TOP + r * (len(lines) * LINE + 60) + (li + 1) * LINE - 30
            x = 0.0; prev = None
            for ch in line:
                n = IS.GNAME.get(ch, ch)
                if prev is not None:
                    x += kern.get((prev, n), 0.0)
                gu = G.get("GeistSerifRegular_" + n)
                if n == "space" or gu is None:
                    x += 250; prev = n; continue
                cs = recs[n] if key.endswith("Pass2c_") else G[key + n]["contours"]
                cv.drawPath(IS.skia_path(IS.shear(cs, -C.K), (300 + x * S) * R, base * R, S * R, C.K), skia.Paint(AntiAlias=True, Color=skia.Color(17, 17, 17)))
                x += gu["width"]; prev = n
    img = Image.fromarray(surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3].copy()).resize((Wp * 2, H * 2), Image.LANCZOS)
    d = ImageDraw.Draw(img); f = lambda sz: ImageFont.truetype(IS.MENLO, int(sz * 2))
    d.text((112, 60), "GEIST SERIF  18.43°  (x' = x + y/3)", fill=(17, 17, 17), font=f(28))
    d.text((112, 140), "%s  ·  the recommendation: the fixed s, every serif sheared, terminals' end tangents lean at corners, repaired to the comb gate" % LBL, fill=(110, 110, 110), font=f(14))
    for r, (nm, key) in enumerate(rows):
        y = 2 * (TOP + r * (len(lines) * LINE + 60) + LINE - 70)
        d.text((112, y), nm, fill=(17, 17, 17), font=f(16))
    img.save(out); print("wrote", out)


def main():
    R = dict(gate_rule="0 snaps, 0 spikes (curvcomb) and 0 humps (comb_p2.hump: DIP 0.12 of the cubic's peak, G2 jump <= 1.25 x upright, floor 0.05)")
    # 1. re-grade everything shown before
    C.set_slant(1 / 3); G = C.load()
    for key, nm in (("GeistSerifSlant_", "plain slant"), ("GeistSerifItalicPass1_", "pass 1"), ("GeistSerifItalicPass2a_", "pass 2a"), ("GeistSerifItalic_", "pass 2b")):
        R.setdefault("regrade", {})[nm] = {g: gate(G[key + g]["contours"], (G["GeistSerifRegularOld_s"] if (g == "s" and nm == "pass 1") else G["GeistSerifRegular_" + g])["contours"], C.K)
                                          for g in C.glyphs(G)}
    import s_options
    G18, O18, _ = s_options.build(1 / 3)
    R["regrade_options_1_9"] = {o["key"]: gate(o["cs"], o["up"], 1 / 3) for o in O18 if o["up"] is not None}
    G3 = S2.G_at(1 / 3)
    _, O2, his3, _ = S2.options(1 / 3, 0.0)
    R["regrade_options_10_14"] = {o["key"]: gate(o["cs"], o["up"], 1 / 3) for o in O2}
    # 2. pass 2c, every letter at both angles
    recs = {}
    for tag, K in (("14", 0.25), ("18", 1.0 / 3.0)):
        C.set_slant(K); p = os.path.join(C.R5, "src", "geistserif_italic_%s.json" % tag); Gt = json.load(open(p))
        Gs = S2.G_at(K) if tag == "18" else Gt
        his_t, _ = S2.his_for(K, Gt["GeistSerifSlant_s"]["contours"])
        R.setdefault("gate_2c", {})[tag] = {}
        for g in C.glyphs(Gt):
            cs = s_fixed(Gs, his_t, "14") if g == "s" else letter_2c(g, Gt)
            Gt["GeistSerifItalicPass2c_" + g] = {"contours": cs, "width": Gt["GeistSerifRegular_" + g]["width"], "glyph": g,
                                                 "master": "Italic pass 2c (recommended)"}
            R["gate_2c"][tag][g] = gate(cs, Gt["GeistSerifRegular_" + g]["contours"], K)
            if tag == "18":
                recs[g] = cs
        json.dump(Gt, open(p, "w"))
    # 3. the s sheet
    C.set_slant(1 / 3); G = C.load(); G3 = S2.G_at(1 / 3)
    up = G3["GeistSerifRegular_s"]["contours"]
    his3, _ = S2.his_for(1 / 3, G3["GeistSerifSlant_s"]["contours"])
    Gd = S2.G_at(S2.K_D); hisd, _ = S2.his_for(S2.K_D, Gd["GeistSerifSlant_s"]["contours"])
    V = [("14 fixed: his skeleton, bowl chains solved (RECOMMENDED)", recs["s"], GREEN)]
    R["s_13_fixed_gate"] = gate(s_fixed(G3, his3, "13"), up, 1 / 3)      # not rendered: it fails (a peak before the lower beak)
    gates = {nm: gate(cs, up, 1 / 3) for nm, cs, _ in V}
    X = {}
    for nm, cs, _ in V:
        csd = (G["GeistSerifItalic_s"]["contours"] if nm.startswith("pass 2b") else None)
        Gd_ = S2.G_at(S2.K_D)
        if nm.startswith("13"):
            csd = s_fixed(Gd_, hisd, "13")
        else:
            csd = s_fixed(Gd_, hisd, "14")
        X[nm] = (drawn.xor_pct(csd, hisd), drawn.xor_pct(cs, his3))
    C.set_slant(1 / 3)
    sheet_s(G, V, his3, gates, X)
    R["s_sheet"] = {nm: dict(gate=gates[nm], xor_kd=round(X[nm][0], 2), xor_18=round(X[nm][1], 2)) for nm in gates}
    # 4. the a's foot
    ua = G["GeistSerifRegular_a"]["contours"]; K = C.K
    Va = [("roman", ua, GREY, 0.0), ("plain slant", G["GeistSerifSlant_a"]["contours"], RED, K * 109),
          ("pass 2b (foot rigid)", G["GeistSerifItalic_a"]["contours"], BLUE, K * 109), ("pass 2c (sheared)", recs["a"], GREEN, K * 109)]
    sheet_a(G, Va)
    Vh = [(nm, cs, col, K * 440 if dx else 0.0) for nm, cs, col, dx in Va]
    Vh[2] = ("pass 2b (end tangent roman)", Vh[2][1], Vh[2][2], Vh[2][3])
    Vh[3] = ("pass 2c (end tangent leans)", Vh[3][1], Vh[3][2], Vh[3][3])
    sheet_hood(G, Vh, os.path.join(OUT, "a_hood_18.png"))
    fl = lambda cs: [n for c in cs for n in c["nodes"]]
    R["a_hood_tangent_34"] = {nm: round(math.degrees(math.atan2(*(np.array(fl(cs)[33][:2]) - np.array(fl(cs)[34][:2])))), 1) for nm, cs, _, _ in Vh}
    R["a_foot_radius_27"] = {nm: radius_at(cs, 27) for nm, cs, _, _ in Va}
    # 5. word line
    words(G, recs, os.path.join(OUT, "word_saopne_18_pass2c.png"))
    json.dump(R, open(os.path.join(C.R5, "readings", "pass2c.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in R.items() if k not in ("regrade",)}, indent=1, default=str)[:6000])
    print({nm: {g: v["hump"] + v["snaps"] + v["spikes"] for g, v in d.items() if not v["ok"]} for nm, d in R["regrade"].items()})


if __name__ == "__main__":
    main()
