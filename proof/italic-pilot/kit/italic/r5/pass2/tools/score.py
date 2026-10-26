"""Score sheets: round 5 at 14.04 deg against Mark's drawn italic (src/mark_saopne_pdf_paths.json).

score.py [s,a,o,p,n,e] [--steps 1-3|1-5|1-6] [--out DIR] [--json PATH]

Per letter, sheets/score_<g>.png:
  left   Mark's drawn italic filled grey; over it the plain slant (red), round 4's corrected (blue,
         src/geistserif_italic.json) and round 5 (green); all on the baseline; the drawing is placed in the solver's
         frame by its stems (p n a), its held terminal corners (s) or its centre at mid-height (o e) -- drawn.placement
  right  the residual: every on-curve node of round 5 -> the nearest on-curve node of the drawing (arrows x2, units),
         i.e. what Mark's drawing still asks of round 5
  foot   XOR % against the drawing (area of the symmetric difference / the drawing's area) for slant, round 4, round 5
         steps 1-3 and the steps run; the FLOOR is the drawn roman against our JSON Regular (his s is a later drawing)
The drawn e and n are UNFINISHED (Mark, 2026-10-25): their sheets say so and their numbers are reference only.
"""
import sys, os, json, math, argparse
import numpy as np
import skia
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
import drawn
from round5 import correct

MENLO = "/System/Library/Fonts/Menlo.ttc"
BG = (24, 25, 30)
COL = dict(drawn=(108, 108, 112), slant=(240, 70, 55), r4=(90, 150, 255), r5=(95, 225, 120), r5a=(250, 205, 70))
LETTERS = ["s", "a", "o", "p", "n", "e"]
R4_SRC = os.path.join(C.R5, "src", "geistserif_italic.json")


def fnt(sz):
    return ImageFont.truetype(MENLO, sz)


def onc(cs):
    return [(n[0], n[1]) for c in cs for n in c["nodes"] if n[2] != "o"]


def candidates(gl, G, R4, steps):
    sl = G["GeistSerifSlant_" + gl]["contours"]
    r4 = R4["GeistSerifItalic_" + gl]["contours"]
    a = correct(gl, G, "1-3")["contours"]
    b = correct(gl, G, steps)["contours"] if steps != "1-3" else a
    return dict(slant=sl, r4=r4, r5_13=a, r5=b)


def score_letter(gl, G, R4, steps, out_dir):
    up = G["GeistSerifRegular_s.anchors" if gl == "s" else "GeistSerifRegular_" + gl]["contours"]
    cand = candidates(gl, G, R4, steps)
    dr_r = drawn.letter(gl, "roman", up)
    dr = drawn.letter(gl, "italic", cand["slant"])
    D = dr["contours"]
    x = {k: drawn.xor_pct(v, D) for k, v in cand.items()}
    floor = drawn.xor_pct(up if gl != "s" else up, dr_r["contours"])
    # ---- render
    sc = 0.9
    allc = [D] + list(cand.values())
    xs = [n[0] for cs in allc for c in cs for n in c["nodes"]]
    x0, x1 = min(xs) - 40, max(xs) + 40
    y0, y1 = -230, 800
    PW = max(int((x1 - x0) * sc), 760); PH = int((y1 - y0) * sc)
    x1 = x0 + PW / sc
    HEAD, FOOT = 150, 150
    W = PW * 2 + 60; H = PH + HEAD + FOOT
    surf = skia.Surface(W, H); cv = surf.getCanvas(); cv.clear(skia.Color(*BG))
    def panel(ox):
        cv.save(); cv.translate(ox - x0 * sc, HEAD + y1 * sc); cv.scale(sc, -sc)
    def stroke(col, w):
        return skia.Paint(AntiAlias=True, Color=skia.Color(*col), Style=skia.Paint.kStroke_Style, StrokeWidth=w / sc)
    for ox in (20, PW + 40):
        panel(ox)
        for yl in (0, 545, 710, -200):
            cv.drawLine(x0, yl, x1, yl, stroke((55, 56, 62), 1.0))
        cv.restore()
    # left: drawn filled + three outlines
    panel(20)
    cv.drawPath(drawn.path(D), skia.Paint(AntiAlias=True, Color=skia.Color(*COL["drawn"])))
    for k, w in (("slant", 1.6), ("r4", 1.8), ("r5", 2.2)):
        cv.drawPath(drawn.path(cand[k]), stroke(COL[k], w))
    cv.restore()
    # right: residual node vectors, drawn outline white, round 5 green
    panel(PW + 40)
    cv.drawPath(drawn.path(D), skia.Paint(AntiAlias=True, Color=skia.Color(52, 52, 58)))
    cv.drawPath(drawn.path(D), stroke((235, 235, 235), 1.6))
    cv.drawPath(drawn.path(cand["r5"]), stroke(COL["r5"], 1.6))
    cv.restore()
    im = Image.frombytes("RGBA", (W, H), surf.makeImageSnapshot().tobytes()).convert("RGB"); d = ImageDraw.Draw(im)
    T = lambda p, ox: (ox - x0 * sc + p[0] * sc, HEAD + y1 * sc - p[1] * sc)
    pm = onc(D); pr = onc(cand["r5"])
    vec = []
    for p in pr:
        q = min(pm, key=lambda q: math.dist(p, q))
        back = min(pr, key=lambda r: math.dist(q, r))
        if back == p:                                   # mutual nearest nodes only: the two drawings are not node-compatible
            vec.append((p, q, math.dist(p, q)))
    f13 = fnt(13)
    for p, q, dd in vec:
        X0, Y0 = T(p, PW + 40)
        d.ellipse([X0 - 4, Y0 - 4, X0 + 4, Y0 + 4], outline=COL["r5"], width=2)
        if dd < 1.5:
            continue
        X2, Y2 = X0 + (q[0] - p[0]) * sc * 2, Y0 - (q[1] - p[1]) * sc * 2
        d.line([(X0, Y0), (X2, Y2)], fill=(255, 215, 60), width=3)
        ang = math.atan2(Y2 - Y0, X2 - X0)
        for s_ in (+1, -1):
            d.line([(X2, Y2), (X2 - 10 * math.cos(ang + s_ * 0.45), Y2 - 10 * math.sin(ang + s_ * 0.45))], fill=(255, 215, 60), width=3)
        if dd >= 4:
            d.text((X2 + 5, Y2 - 16), "%.0f" % dd, fill=(255, 215, 60), font=f13)
    for X, Y in [T(q, PW + 40) for q in pm]:
        d.rectangle([X - 3, Y - 3, X + 3, Y + 3], outline=(235, 235, 235))
    unfinished = gl in drawn.UNFINISHED
    d.text((20, 14), "GEIST SERIF  Regular → Italic 14.04° (x' = x + y/4)  ·  /%s" % gl, fill=(240, 240, 240), font=fnt(34))
    sub = "SCORE vs Mark's drawn italic (new_italics.pdf, 2026-10-25)  ·  round 5 = steps %s  ·  drawing placed by %s" % (steps, dr["placed"])
    d.text((20, 62), sub, fill=(170, 170, 170), font=fnt(16))
    if unfinished:
        d.text((20, 86), "drawn %s NOT corrected by Mark yet, reference only: no fit, no score" % gl, fill=(255, 120, 90), font=fnt(20))
    # the key is written IN its colours (Mark: a grey line naming colours is "like writing blue with green letters")
    kx = 24
    for k, name in (("drawn", "drawn italic"), ("slant", "plain slant"), ("r4", "round 4"), ("r5", "round 5")):
        d.rectangle([kx, HEAD - 20, kx + 14, HEAD - 6], fill=COL[k])
        d.text((kx + 20, HEAD - 22), name, fill=COL[k], font=fnt(15)); kx += 20 + d.textlength(name, font=fnt(15)) + 26
    d.text((PW + 44, HEAD - 22), "residual: round 5 node → its mutual-nearest drawn node (×2, u)", fill=(255, 215, 60), font=fnt(15))
    yy = H - FOOT + 14
    line = "XOR vs drawn:  slant %.1f %%  ·  round 4 %.1f %%  ·  round 5 (1-3) %.1f %%" % (x["slant"], x["r4"], x["r5_13"]) + (
        "  ·  round 5 (%s) %.1f %%" % (steps, x["r5"]) if steps != "1-3" else "")
    d.text((20, yy), line, fill=(240, 240, 240) if not unfinished else (170, 170, 170), font=fnt(22))
    big = [v for _, _, v in vec]
    d.text((20, yy + 36), "floor: drawn roman vs our Regular %.1f %%%s  ·  residual nodes: median %.1f u, max %.1f u" % (
        floor, " (his roman s is a later drawing than ours)" if gl == "s" else "", float(np.median(big)), max(big)), fill=(170, 170, 170), font=fnt(16))
    d.text((20, yy + 62), "XOR = area of the symmetric difference / the drawing's area · all on the baseline · the drawing is anchored by stems / held corners / round centre, never the bbox",
           fill=(130, 130, 130), font=fnt(13))
    fn = os.path.join(out_dir, "score_%s.png" % drawn_fname(gl))
    im.save(fn)
    return dict(xor={k: round(v, 2) for k, v in x.items()}, floor=round(floor, 2), placed=dr["placed"], unfinished=unfinished,
                residual_median=round(float(np.median(big)), 2), residual_max=round(max(big), 2), sheet=fn)


def drawn_fname(gl):
    return "".join(c + "_" if c.isupper() else c for c in gl)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("letters", nargs="?", default=",".join(LETTERS))
    ap.add_argument("--steps", default="1-6")
    ap.add_argument("--out", default=os.path.join(C.R5, "sheets"))
    ap.add_argument("--json", default=None)
    a, _ = ap.parse_known_args(C.strip_slant(sys.argv[1:]))
    C.set_slant(0.25)                                   # scoring is against drawings made at 14.04 deg
    G = C.load(); R4 = json.load(open(R4_SRC))
    res = {}
    for gl in a.letters.split(","):
        res[gl] = score_letter(gl, G, R4, a.steps, a.out)
        print(gl, res[gl])
    jp = a.json or os.path.join(C.R5, "readings", "score_%s.json" % a.steps)
    json.dump(res, open(jp, "w"), indent=1)


if __name__ == "__main__":
    main()
