"""Round 5 · pass 2: the comparison sheets (dark, Menlo, GEIST SERIF + angle first and large; keys in their colours;
solid fills).

sheets_p2.py [serifs|ends|words|table|all]

  T_E_serifs_18.png              18.43 deg, SOLID: T, E, z under the three serif classes (I14 "roman" = pass 1, "arm" =
                                 shipped: arm/bar serifs sheared, stem serifs roman, "shear" = every serif sheared),
                                 with the plain slant; then zooms on T's left arm end and E's upper arm end
  ends_18.png                    18.43 deg, SOLID: the I15 stroke ends in stem groups (f hook, r arm, j tail, y tail)
                                 and the terminals (s, a, e, quoteright): plain slant | pass 1 | pass 2 | the other cut class
  word_harpers_18_pass1_vs_pass2.png   white proof page: pass 1 corrected over pass 2 corrected, solid, same layout and
                                 kerning as word_harpers_18.png (Harper's Bazzar, saopne, and a line of the set's other letters)
  score_table.png                readings/score_p2.json as a table (SCORE.md is written by score_table_p2.py)
"""
import sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
import drawn
from proof5s import Sheet, INK, DIM, FAINT

OUT = os.path.join(C.R5, "sheets")
LBL = "round 5 · pass 2"
A18 = "18.43°  (x' = x + y/3)"
A14 = "14.04°  (x' = x + y/4)"
COL = dict(slant=(240, 72, 58), p1=(80, 145, 255), p2=(90, 222, 118), alt=(225, 110, 230), shear=(250, 200, 70), up=(178, 178, 184))


def box(*cs, pad=30):
    xs = [n[0] for c_ in cs for c in c_ for n in c["nodes"]]; ys = [n[1] for c_ in cs for c in c_ for n in c["nodes"]]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def serifs():
    C.set_slant(1 / 3)
    from round_p2 import correct
    G = C.load()
    rows = ["T", "E", "z"]
    cols = [("slant", "plain slant", COL["slant"]), ("roman", "I14 roman: every serif cut roman (pass 1's class)", COL["p1"]),
            ("arm", "arm serifs sheared, stem serifs roman (SHIPPED)", COL["p2"]), ("shear", "every serif sheared", COL["shear"])]
    V = {}
    for gl in rows:
        V[gl] = {"slant": G["GeistSerifSlant_" + gl]["contours"]}
        for k, _, _ in cols[1:]:
            V[gl][k] = correct(gl, G, "1-6", serif=k)["contours"]
    W, H = 2400, 3100
    sh = Sheet(W, H)
    sh.title("/T /E /z  ·  arm and bar serifs  ·  %s" % LBL, A18,
             "SOLID fills, same scale per row. The class question: does a serif's cut keep the roman angle or the shear? Pass 1 kept every cut roman.")
    sh.key(26, 122, [(nm, col) for _, nm, col in cols], 17)
    pw, ph = 585, 560
    for r, gl in enumerate(rows):
        B = box(*V[gl].values())
        for k, (key, nm, col) in enumerate(cols):
            pn = sh.panel(20 + k * (pw + 10), 170 + r * (ph + 20), pw, ph, B, pad=14)
            pn.frame(); pn.hline(0); pn.hline(545 if gl.islower() else 710)
            pn.fill(V[gl][key], col)
        sh.text(28, 176 + r * (ph + 20), "/" + gl, INK, 22)
    # zooms: T's left arm end, E's upper arm end -- solid, with the shipped outline over the others' solid
    y0 = 170 + 3 * (ph + 20) + 30
    sh.text(26, y0 - 26, "ZOOM, solid: T's left arm end (top) and E's upper arm end (bottom); the thin white line is the stem's lean (18.43°)", DIM, 15)
    zooms = [("T", (-60, 420, 260, 760)), ("E", (300, 420, 620, 760))]
    zh = 520
    for r, (gl, zb) in enumerate(zooms):
        cs = V[gl]["slant"]
        xs = [n[0] for c in cs for n in c["nodes"] if n[1] > 600]
        if gl == "T":
            zb = (min(xs) - 40, 380, min(xs) + 300, 750)
        else:
            zb = (max(xs) - 300, 380, max(xs) + 40, 750)
        for k, (key, nm, col) in enumerate(cols):
            pn = sh.panel(20 + k * (pw + 10), y0 + r * (zh + 16), pw, zh, zb, pad=6)
            pn.frame()
            pn.fill(V[gl][key], col)
            # the italic angle through the serif's outer tip, for reference
            tip = min(((n[0], n[1]) for c in V[gl]["slant"] for n in c["nodes"] if n[2] != "o" and n[1] < 720 and n[1] > 400),
                      key=lambda p: p[0] if gl == "T" else -p[0])
            pn.polyline([(tip[0] - 400 / 3, tip[1] - 400), (tip[0] + 400 / 3, tip[1] + 400)], (235, 235, 235), 1.0, 150)
    return sh.save(os.path.join(OUT, "T_E_serifs_18.png"))


def ends():
    C.set_slant(1 / 3)
    from round_p2 import correct
    G = C.load()
    letters = ["f", "r", "j", "y", "s", "a", "e", "quoteright"]
    W, H = 2400, 3060 + 2 * 470
    sh = Sheet(W, H)
    sh.title("I15 terminals ride: every terminal class in the set  ·  %s" % LBL, A18,
             "SOLID. Leading terminal (upper half of its contour) keeps the ROMAN cut; trailing keeps the SHEAR. Last column: the other cut class on the same letter.")
    cols = [("slant", "plain slant", COL["slant"]), ("p1", "pass 1 (I14: s e a terminals rigid at the roman angle, f r y sheared, j held roman, ’ = slant)", COL["p1"]),
            ("p2", "pass 2 (I15, shipped)", COL["p2"]), ("flip", "pass 2, cut classes swapped", COL["alt"])]
    sh.key(26, 122, [(nm, col) for _, nm, col in cols], 17)
    pw, ph = 585, 340
    keep = {}
    for r, gl in enumerate(letters):
        flip = {"a": "b"}.get(gl)
        Vs = {"slant": G["GeistSerifSlant_" + gl]["contours"], "p1": (G.get("GeistSerifItalicPass1Rules_" + gl) or G["GeistSerifItalicPass1_" + gl])["contours"],
              "p2": G["GeistSerifItalic_" + gl]["contours"], "flip": correct(gl, G, "1-6", terminal="flip")["contours"]}
        B = box(*Vs.values()); keep[gl] = Vs
        for k, (key, nm, col) in enumerate(cols):
            pn = sh.panel(20 + k * (pw + 10), 170 + r * (ph + 10), pw, ph, B, pad=8)
            pn.frame(); pn.hline(0)
            pn.fill(Vs[key], col)
        rep = correct(gl, G, "1-3")["skeleton"].report()
        info = ["%s %s→%s°" % ("lead" if t["leading"] else "trail", t.get("cut_roman_deg"), t.get("cut_new_deg")) for t in rep["terminals"] + rep["stem_ends"]]
        sh.text(28, 176 + r * (ph + 10), "/%s  %s" % (gl, "  ".join(info)), INK, 16)
    y0 = 170 + len(letters) * (ph + 10) + 40
    sh.text(26, y0 - 28, "ZOOM, solid: the two LEADING stroke ends that I15 gives the roman cut: f's hook, r's arm (the thin line = the stems' 18.43°)", DIM, 15)
    for r, gl in enumerate(("f", "r")):
        cs = keep[gl]["slant"]
        tip = max(((n[0], n[1]) for c in cs for n in c["nodes"] if n[2] != "o"), key=lambda p: p[0] + 0.3 * p[1])
        zb = (tip[0] - 260, tip[1] - 260, tip[0] + 60, tip[1] + 60)
        for k, (key, nm, col) in enumerate(cols):
            pn = sh.panel(20 + k * (pw + 10), y0 + r * 470, pw, 450, zb, pad=4)
            pn.frame(); pn.fill(keep[gl][key], col)
            pn.polyline([(tip[0] - 300 / 3, tip[1] - 300), (tip[0] + 100 / 3, tip[1] + 100)], (235, 235, 235), 1.0, 150)
        sh.text(28, y0 + r * 470 + 6, "/" + gl, INK, 20)
    sh.text(26, H - 40, "cut angles in degrees from vertical (+ = top leans right), roman → pass 2; the plain slant adds 18.43° to a vertical cut", DIM, 15)
    return sh.save(os.path.join(OUT, "ends_18.png"))


def words():
    """pass 1 over pass 2, solid, the word page's own lines, advances and kerning"""
    import skia
    from PIL import Image, ImageDraw, ImageFont
    import italicsheet as IS
    C.set_slant(1 / 3)
    IS.KERN = os.path.join(C.R5, "src", "kerning.json")
    G = C.load()
    kern, _ = IS.load_kern()
    lines = ["Harper’s Bazzar", "saopne", "THE foxy jazz fern"]          # only glyphs in the set
    S = 0.125; Wp = 1640; R = 4
    rows = [("pass 1", "GeistSerifItalicPass1_", (17, 17, 17)), ("pass 2", "GeistSerifItalic_", (17, 17, 17))]   # pass 1 as delivered
    LINE = 140; TOP = 150; H = TOP + len(rows) * (len(lines) * LINE + 70) + 40
    surf = skia.Surface(Wp * R, H * R); cv = surf.getCanvas(); cv.clear(skia.ColorWHITE)
    ys = []
    for r, (nm, key, col) in enumerate(rows):
        for li, line in enumerate(lines):
            base = TOP + r * (len(lines) * LINE + 70) + (li + 1) * LINE - 30
            ys.append((r, li, base))
            x = 0.0; prev = None
            for ch in line:
                n = IS.GNAME.get(ch, ch)
                if prev is not None:
                    x += kern.get((prev, n), 0.0)
                gu = G.get("GeistSerifRegular_" + n)
                if n == "space" or gu is None:
                    x += (gu or G.get("space") or {"width": 250}).get("width", 250); prev = n; continue
                gi = G.get(key + n)
                cont = IS.shear(gi["contours"], -C.K)
                cv.drawPath(IS.skia_path(cont, (300 + x * S) * R, base * R, S * R, C.K), skia.Paint(AntiAlias=True, Color=skia.Color(*col)))
                x += gu["width"]; prev = n
    img = Image.fromarray(surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3].copy())
    img = img.resize((Wp * 2, H * 2), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    f = lambda sz: ImageFont.truetype(IS.MENLO, int(sz * 2))
    d.text((112, 70), "GEIST SERIF  18.43°  (x' = x + y/3)", fill=(17, 17, 17), font=f(30))
    d.text((112, 150), "%s  ·  pass 1 corrected (top) and pass 2 corrected (bottom), solid, same advances and kerning" % LBL, fill=(110, 110, 110), font=f(15))
    for r, (nm, key, col) in enumerate(rows):
        y = TOP + r * (len(lines) * LINE + 70) + LINE - 60
        d.text((112, 2 * y), nm, fill=(17, 17, 17), font=f(22))
        d.text((112, 2 * y + 52), "I10–I14" if r == 0 else "I10–I16, I17 off", fill=(120, 120, 120), font=f(13))
        d.text((112, 2 * y + 84), "as delivered: old extracted s" if r == 0 else "s = Mark's drawn roman s", fill=(120, 120, 120), font=f(13))
        if r:
            yy = 2 * (TOP + r * (len(lines) * LINE + 70) - 30)
            d.line([(112, yy), (2 * Wp - 112, yy)], fill=(200, 200, 200), width=2)
    out = os.path.join(OUT, "word_harpers_18_pass1_vs_pass2.png")
    img.save(out); print("wrote", out)
    return out


def table():
    T = json.load(open(os.path.join(C.R5, "readings", "score_table_p2.json")))
    cols, rows, notes = T["cols"], T["rows"], T["notes"]
    cw = [230] + [205] * (len(cols) - 1)
    W = sum(cw) + 60; H = 230 + 46 * (len(rows) + 1) + 30 * len(notes) + 40
    sh = Sheet(W, H)
    sh.title("score vs Mark's drawn italic  ·  %s" % LBL, A14, "XOR % = area(candidate △ drawing) / area(drawing) · lower is closer · same upright (the extracted Regular) for every column")
    ccol = [INK, COL["slant"], COL["p1"], COL["p2"], COL["alt"], (80, 200, 235)]
    y = 140; x = 26
    for c, w, cc in zip(cols, cw, ccol):
        sh.text(x, y, c, cc, 17); x += w
    y += 46
    for r_ in rows:
        x = 26
        for i, (v, w) in enumerate(zip(r_["cells"], cw)):
            col = (130, 130, 135) if r_.get("dim") else (ccol[i] if i else INK)
            if r_.get("bold") and i:
                col = ccol[i]
            sh.text(x, y, str(v), col, 19 if r_.get("bold") else 17); x += w
        y += 46
    y += 10
    for n in notes:
        sh.text(26, y, n, DIM, 14); y += 30
    return sh.save(os.path.join(OUT, "score_table.png"))


def pullin():
    """s_pullin_18.png: the terminal pull-in k = 0 / 0.5 / 1 at 18.43 deg (solid + comb) with the XOR at 14.04 deg, and
    s_arcfair_18.png: where the top's flattening came from (the I16 connecting curve) and the fix"""
    from round_p2 import correct
    from comb_p2 import comb
    import drawn5s
    C.set_slant(0.25); G14 = C.load()
    sl14 = G14["GeistSerifSlant_s"]["contours"]; raw = drawn.raw_contours("s", "italic")
    D = drawn.shift(raw, drawn5s.centroid_x(sl14) - drawn5s.centroid_x(raw))
    X = {k: drawn.xor_pct(correct("s", G14, "1-6", pull_k=k)["contours"], D) for k in (0.0, 0.5, 1.0)}
    C.set_slant(1 / 3); G = C.load()
    V = {k: correct("s", G, "1-6", pull_k=k) for k in (0.0, 0.5, 1.0)}
    cols = {0.0: COL["p2"], 0.5: COL["shear"], 1.0: COL["alt"]}
    W, H = 2400, 1900
    sh = Sheet(W, H)
    sh.title("/s  ·  terminal pull-in k · tan θ · |height from mid-height|, toward the letter's middle  ·  %s" % LBL, A18,
             "SOLID beside the curvature comb (one gain for all). XOR at 14.04° against Mark's drawn italic s under each. All with the I16 arc fix.")
    sh.key(26, 122, [("k = 0 (shipped)", cols[0.0]), ("k = 0.5", cols[0.5]), ("k = 1.0", cols[1.0])], 19)
    B = (40, -40, 720, 600)
    for r, k in enumerate((0.0, 0.5, 1.0)):
        cs = V[k]["contours"]; y = 170 + r * 570
        pn = sh.panel(20, y, 560, 550, B); pn.frame(); pn.hline(0); pn.hline(545); pn.fill(cs, cols[k])
        pc = sh.panel(600, y, 560, 550, B); pc.frame(); pc.fill(cs, (46, 46, 52)); comb(pc, cs, cols[k], gain=5000)
        zb = (300, 330, 720, 600)
        pz = sh.panel(1180, y, 1200, 550, zb); pz.frame(); pz.fill(cs, (46, 46, 52)); comb(pz, cs, cols[k], gain=5000)
        pull = V[k]["skeleton"].pull_report
        sh.text(30, y + 8, "k = %.1f   XOR at 14.04° %.1f %%" % (k, X[k]), cols[k], 19)
        sh.text(30, y + 34, "terminal moves: " + ("  ".join("%+.0f u" % p["dx"] for p in pull) if pull else "none"), cols[k], 15)
        sh.text(1190, y + 8, "zoom: the upper bowl into the beak", DIM, 15)
    out1 = sh.save(os.path.join(OUT, "s_pullin_18.png"))
    # the cause and the fix
    VV = [("plain slant", G["GeistSerifSlant_s"]["contours"], COL["slant"]),
          ("I16 as the s round built it (similarity + R15)", correct("s", G, "1-6", spine_g2=False)["contours"], COL["alt"]),
          ("I16 + the arc re-faired (shipped)", V[0.0]["contours"], COL["p2"])]
    W, H = 2400, 1500
    sh = Sheet(W, H)
    sh.title("/s  ·  the flattening at the top: where it comes from  ·  %s" % LBL, A18,
             "Comb across the upper bowl: spine junction → top node → beak, outer and counter. The connecting curve (the spine's similarity) ran flat into the top node, then a curvature step there.")
    sh.key(26, 122, [(nm, col) for nm, _, col in VV], 19)
    zb_in = lambda n: 250 <= n[0] <= 720 and 300 <= n[1] <= 600
    for k, (nm, cs, col) in enumerate(VV):
        pn = sh.panel(20 + k * 790, 170, 770, 600, B); pn.frame(); pn.fill(cs, (46, 46, 52)); comb(pn, cs, col, gain=5000)
        pz = sh.panel(20 + k * 790, 790, 770, 680, (250, 300, 720, 600)); pz.frame(); pz.fill(cs, (46, 46, 52)); comb(pz, cs, col, gain=5000)
        i = 0
        for c in cs:
            for n in c["nodes"]:
                if n[2] != "o" and zb_in(n):
                    pz.dot(n[:2], INK, 4); pz.label(n[:2], str(i), INK, 14, dx=6, dy=-6)
                i += 1
        sh.text(30 + k * 790, 178, nm, col, 17)
    out2 = sh.save(os.path.join(OUT, "s_arcfair_18.png"))
    json.dump(dict(xor_14={str(k): round(v, 2) for k, v in X.items()}, pull={str(k): V[k]["skeleton"].pull_report for k in V}),
              open(os.path.join(C.R5, "readings", "pullin.json"), "w"), indent=1)
    return out1, out2


def serifs18():
    """serifs_18.png: n p H feet and heads at 18.43 deg, zoomed, SOLID: upright | plain slant | pass 2a (I14: slab slid at the
    slab-top height, brackets as the shear) | pass 2b (I14b: slab + brackets one rigid roman piece hung at the brackets'
    junction height); then the combs of pass 2a and pass 2b at the same zoom"""
    from round_p2 import correct
    from comb_p2 import comb
    C.set_slant(1 / 3); G = C.load()
    rows = []
    for gl in ("n", "p", "H"):
        Sk = correct(gl, G, "1-3")["skeleton"]; U = Sk.U
        sers = [s for s in Sk.serif_report if s["cut"] == "roman"]
        def box_of(s):
            P = np.array([U.xy[n] for n in s["nodes"] + s.get("junctions", [])]); return P
        foot = min(sers, key=lambda s: (box_of(s)[:, 1].mean(), box_of(s)[:, 0].mean()))
        head = max(sers, key=lambda s: (box_of(s)[:, 1].mean(), -box_of(s)[:, 0].mean()))
        for nm, s in (("foot", foot), ("head", head)):
            P = box_of(s); x0, y0 = P.min(axis=0) - 40; x1, y1 = P.max(axis=0) + 40
            w = max(x1 - x0, 1.25 * (y1 - y0)); xc = (x0 + x1) / 2
            rows.append((gl, nm, (xc - w / 2, y0, xc + w / 2, y1)))
    cols = [("upright", None, COL["up"]), ("plain slant", "GeistSerifSlant_", COL["slant"]), ("pass 2a: slab slid, brackets sheared", "GeistSerifItalicPass2a_", COL["p1"]),
            ("pass 2b: slab + brackets rigid roman (I14b)", "GeistSerifItalic_", COL["p2"])]
    PW, PH = 395, 330
    W, H = 6 * (PW + 6) + 20, 200 + len(rows) * (PH + 8) + 40
    sh = Sheet(W, H)
    sh.title("/n /p /H  ·  stem serifs, feet and heads, zoomed  ·  %s" % LBL, A18,
             "SOLID, then the curvature comb of pass 2a and pass 2b (same gain). Mark's drawn p foot at 14.04° is the plain shear (NOTES).")
    sh.key(26, 122, [(nm, col) for nm, _, col in cols] + [("comb 2a", COL["p1"]), ("comb 2b", COL["p2"])], 16)
    for r, (gl, nm, (x0, y0, x1, y1)) in enumerate(rows):
        y = 170 + r * (PH + 8); ym = (y0 + y1) / 2
        for k, (cn, key, col) in enumerate(cols + [("comb 2a", "GeistSerifItalicPass2a_", COL["p1"]), ("comb 2b", "GeistSerifItalic_", COL["p2"])]):
            cs = G["GeistSerifRegular_" + gl]["contours"] if key is None else G[key + gl]["contours"]
            dx = 0 if key is None else C.K * ym
            pn = sh.panel(20 + k * (PW + 6), y, PW, PH, (x0 + dx, y0, x1 + dx, y1), pad=4); pn.frame()
            if k < 4:
                pn.fill(cs, col)
            else:
                pn.fill(cs, (46, 46, 52)); comb(pn, cs, col, gain=1500)
        sh.text(28, y + 6, "/%s %s" % (gl, nm), INK, 18)
    return sh.save(os.path.join(OUT, "serifs_18.png"))


def bowls14():
    """s_bowls_14.png: the s's top and bottom bowls at 14.04 deg against Mark's drawn italic s: pass 1's rules (on his
    roman s) | pass 2a (arc re-fair WITH the fairness term) | pass 2b (no fairness: the roman's curvature ratios at the
    junction and the bowl node); outlines over his solid, solids side by side, combs at 14.04 and 18.43"""
    from round_p2 import correct
    from comb_p2 import comb
    import drawn5s
    out = {}
    for tag, K in (("14", 0.25), ("18", 1.0 / 3.0)):
        C.set_slant(K); G = C.load()
        out[tag] = dict(p1=G["GeistSerifItalicPass1Rules_s"]["contours"], a=G["GeistSerifItalicPass2a_s"]["contours"],
                        b=G["GeistSerifItalic_s"]["contours"], sl=G["GeistSerifSlant_s"]["contours"])
    sl = out["14"]["sl"]; raw = drawn.raw_contours("s", "italic")
    D = drawn.shift(raw, drawn5s.centroid_x(sl) - drawn5s.centroid_x(raw))
    V = [("p1", "pass 1's rules (I12 refitted handles)", COL["p1"]), ("a", "pass 2a: arc re-fair WITH fairness", COL["alt"]),
         ("b", "pass 2b: roman curvature ratios, no fairness", COL["p2"])]
    X = {k: drawn.xor_pct(out["14"][k], D) for k, _, _ in V}
    W, H = 2440, 3020
    sh = Sheet(W, H)
    sh.title("/s  ·  top and bottom bowls  ·  %s" % LBL, A14 + "  and 18.43°",
             "his drawn italic SOLID grey · upright = his drawn roman s · rows 1–2 at 14.04°: outlines over his solid, then SOLID side by side · rows 3–4: combs at 14.04° and 18.43°")
    sh.key(26, 122, [("his drawn italic", (150, 150, 156))] + [("%s  XOR %.1f %%" % (nm, X[k]), col) for k, nm, col in V], 17)
    zones = [("top bowl", (140, 330, 580, 560)), ("bottom bowl", (10, -25, 450, 205))]
    PW = 600
    for r, (zn, zb) in enumerate(zones):
        y = 170 + r * 520
        pn = sh.panel(20, y, PW, 500, zb, pad=4); pn.frame(); pn.fill(D, (112, 112, 118))
        for k, nm, col in V:
            pn.outline(out["14"][k], col, 2.2)
        sh.text(28, y + 6, "%s · 14.04° · outlines over his solid" % zn, INK, 16)
        for j, (k, nm, col) in enumerate(V):
            pz = sh.panel(20 + (j + 1) * (PW + 6), y, PW, 500, zb, pad=4); pz.frame(); pz.fill(out["14"][k], col)
            pz.outline(D, (235, 235, 235), 1.0, 160)
            sh.text(28 + (j + 1) * (PW + 6), y + 6, "%s  (his outline white)" % nm.split(":")[0], col, 15)
    combrows = [("14", "whole s", (40, -50, 700, 600), 620), ("18", "top bowl", (190, 330, 700, 590), 520), ("18", "bottom bowl", (20, -40, 560, 230), 520)]
    y = 1230
    for tag, zn, zb, ph in combrows:
        sh.text(28, y - 4, "combs at %s°, %s (same gain)" % ("14.04" if tag == "14" else "18.43", zn), DIM, 15)
        for j, (k, nm, col) in enumerate([("sl", "plain slant", COL["slant"])] + V):
            pn = sh.panel(20 + j * (PW + 6), y + 16, PW, ph, zb, pad=4); pn.frame()
            pn.fill(out[tag][k], (46, 46, 52)); comb(pn, out[tag][k], col, gain=5000)
            sh.text(28 + j * (PW + 6), y + 22, nm.split(":")[0], col, 15)
        y += ph + 40
    json.dump({k: round(v, 2) for k, v in X.items()}, open(os.path.join(C.R5, "readings", "s_bowls_14.json"), "w"))
    return sh.save(os.path.join(OUT, "s_bowls_14.png"))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("serifs", "all"): print(serifs())
    if what in ("ends", "all"): print(ends())
    if what in ("words", "all"): words()
    if what in ("pullin", "all"): print(pullin())
    if what in ("serifs18", "all"): print(serifs18())
    if what in ("bowls", "all"): print(bowls14())
    if what in ("table", "all") and os.path.exists(os.path.join(C.R5, "readings", "score_table_p2.json")): print(table())
