"""class map: which rule carries each on-curve node (the skeleton's classes), on the upright; shows the Bangla anchor choice"""
import sys, os, json, io, contextlib, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hind_kit as H, round_p2
from sheets import *
from proof import BN, LAT, UP, resolve
PILOT = os.path.dirname(HERE)
CLS = [("sheared at θ: stems, headline, straights", (110, 160, 255)),
       ("round, plain shear (β 0: bowls, loops, arcs)", (90, 222, 118)),
       ("closed round, leans back (β 0.22θ / 0.36θ caps)", (225, 110, 230)),
       ("junction (blended)", (250, 200, 70)),
       ("terminal, rides its sides", (250, 140, 60)),
       ("spine piece (I16)", (240, 72, 58))]


def node_class(why, beta):
    w = why or ""
    if "spine" in w: return 5
    if "rides" in w or "terminal" in w or "stroke end" in w: return 4
    if "junction" in w or "buried" in w: return 3
    if w.startswith("round run"): return 2 if beta > 0 else 1
    return 0


def classes(master, gl):
    g = UP[master][gl]
    H.STATE["master"] = master; H.STATE["cls"][gl] = H.glyph_class(g)
    up = {"contours": g["contours"], "width": g["width"], "master": "Regular", "glyph": gl}
    GG = {"GeistSerifRegular_" + gl: up, "GeistSerifSlant_" + gl: {"contours": H.sheared(g["contours"]), "width": g["width"], "master": "Slant", "glyph": gl}}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        Sk = round_p2.correct(gl, GG, "1-3", serif="shear", side_handles="corners", hold_brackets=True, psi=H.PSI, nu_coef=0.0,
                              i16=H.STATE["cls"][gl] != "bn")["skeleton"]
    out = {}
    for nd, w in Sk.why.items():
        rs = Sk.run_of.get(nd, [])
        beta = max([Sk.runs[Sk.runs[r]["part"]].get("beta", 0.0) or 0.0 for r in rs] or [0.0])
        out[nd] = node_class(w, beta)
    return out


if __name__ == "__main__":
    master = sys.argv[1] if len(sys.argv) > 1 else "Light"
    glyphs = [g for g in ["n", "o", "e", "s", "O"] + BN if UP[master][g]["contours"]]
    s = 0.17; cols = 7; cw = 210; rh = 230
    rows = math.ceil(len(glyphs) / cols)
    sh = Sheet(60 + cols * cw, 300 + rows * rh)
    sh.header("HIND SILIGURI", master + " · class map", "which rule carries each on-curve node, read on the upright (glyphs' own outlines; components not drawn)",
              "Bangla anchor: the full-height verticals (the ka/ba right stem) and the headline are stems/straights sheared at θ; loops are anchored bowls (β 0)")
    x, y = 30, 150
    for i, (nm, c) in enumerate(CLS):
        if i == 3: x, y = 30, 180
        x = sh.key(x, y, [(nm, c)], 16)
    for i, gl in enumerate(glyphs):
        r, cc = divmod(i, cols)
        x0 = 40 + cc * cw; y0 = 230 + r * rh
        try:
            cl = classes(master, gl)
        except Exception as e:
            sh.text(x0, y0, gl + " (error)", RED, 13); continue
        sh.text(x0, y0, gl, INK, 13)
        base = y0 + 190
        cs = UP[master][gl]["contours"]
        sh.glyph(cs, x0 + 10, base, s, (70, 70, 80))
        flat = [n for c in cs for n in c["nodes"]]
        for nd, n in enumerate(flat):
            if n[2] == "o": continue
            k = cl.get(nd, 0)
            sh.c.drawCircle(x0 + 10 + n[0] * s, base - n[1] * s, 3.4, skia.Paint(Color=col(CLS[k][1]), AntiAlias=True))
    print(sh.save(os.path.join(PILOT, "sheets", "classmap_%s.png" % master)))
