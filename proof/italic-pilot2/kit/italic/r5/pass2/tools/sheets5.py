"""Round 5's comparison sheets (dark, Menlo, GEIST SERIF + angle first):

  i9_vs_i10_18.png     per letter at 18.43 deg: plain slant | round 4's ruleset (I1-I9, run at 18.43 deg: I9 on, I13 and
                       re-tension off) | round 5 (I10-I14 + harmonizer); filled, the plain slant's outline under each
  a_alt.png            at 14.04 deg: Mark's drawn two-storey a | his drawn a.alt (single-storey, "made for reference,
                       poorly") | the solver's a (round 5); each on the baseline, a.alt placed by its stem on the a's
  dev/z_I12_diagonal_18.png   the z with the diagonal-spine rule ON vs OFF (why it is off)
  score_table.png      the score table (readings/score_table.json, written by score_table.py)

sheets5.py [i9|aalt|z|table|all]
"""
import sys, os, json, math
import numpy as np
import skia
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
import drawn

MENLO = "/System/Library/Fonts/Menlo.ttc"
BG = (24, 25, 30)
OUT = os.path.join(C.R5, "sheets")


def fnt(sz):
    return ImageFont.truetype(MENLO, sz)


class Canvas:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.s = skia.Surface(W, H); self.c = self.s.getCanvas(); self.c.clear(skia.Color(*BG))
        self.texts = []

    def glyph(self, cs, ox, oy, sc, fill=None, stroke=None, w=1.5):
        c = self.c; c.save(); c.translate(ox, oy); c.scale(sc, -sc)
        p = drawn.path(cs)
        if fill:
            c.drawPath(p, skia.Paint(AntiAlias=True, Color=skia.Color(*fill)))
        if stroke:
            c.drawPath(p, skia.Paint(AntiAlias=True, Color=skia.Color(*stroke), Style=skia.Paint.kStroke_Style, StrokeWidth=w / sc))
        c.restore()

    def line(self, x0, y0, x1, y1, col=(55, 56, 62), w=1.0):
        self.c.drawLine(x0, y0, x1, y1, skia.Paint(AntiAlias=True, Color=skia.Color(*col), StrokeWidth=w))

    def text(self, xy, s, col=(220, 220, 220), size=16):
        self.texts.append((xy, s, col, size))

    def save(self, path):
        im = Image.frombytes("RGBA", (self.W, self.H), self.s.makeImageSnapshot().tobytes()).convert("RGB")
        d = ImageDraw.Draw(im)
        for xy, s, col, size in self.texts:
            d.text(xy, s, fill=col, font=fnt(size))
        im.save(path); print("wrote", path, im.size)


def i9_vs_i10(letters=("o", "e", "p", "s", "a", "n", "B", "z")):
    C.set_slant(1 / 3)
    G = C.load()
    import italicmove as IMm
    from round5 import correct
    def round4_at(gl):
        saved = (IMm.ItalicMover.I9, IMm.ItalicMover.I13, IMm.ItalicMover.RETENSION)
        IMm.ItalicMover.I9, IMm.ItalicMover.I13, IMm.ItalicMover.RETENSION = True, False, False
        try:
            IM = IMm.ItalicMover(G["GeistSerifSlant_" + gl], G["GeistSerifRegular_" + gl])
            return IM.contours_at(1.0)
        finally:
            IMm.ItalicMover.I9, IMm.ItalicMover.I13, IMm.ItalicMover.RETENSION = saved
    sc = 0.36; CW = int(760 * sc); RH = int(1000 * sc)
    HEAD = 130; LW = 270
    W = LW + CW * len(letters) + 40; H = HEAD + RH * 3 + 40
    cv = Canvas(W, H)
    cv.text((20, 14), "GEIST SERIF  Regular → Italic 18.43° (x' = x + y/3)", (240, 240, 240), 34)
    cv.text((20, 62), "I9 vs I10: round 4's half-angle slides against round 5's two-angle shear (+ I11-I14, harmonizer) · red = the plain slant's outline", (170, 170, 170), 16)
    rows = [("plain slant", "x + y/3"), ("round 4 ruleset", "I1–I9 at 18.43°"), ("round 5", "I10–I14 + harmonize")]
    for ri, (a, b) in enumerate(rows):
        y = HEAD + ri * RH
        cv.text((20, y + RH // 2 - 30), a, (240, 240, 240), 22); cv.text((20, y + RH // 2), b, (150, 150, 150), 15)
        cv.line(LW - 10, y + RH - 4, W - 20, y + RH - 4)
    for li, gl in enumerate(letters):
        sl = G["GeistSerifSlant_" + gl]["contours"]
        cs = [sl, round4_at(gl), correct(gl, G, "1-6")["contours"]]
        for ri, c in enumerate(cs):
            ox = LW + li * CW + 10; oy = HEAD + ri * RH + RH - 90
            cv.line(ox, oy, ox + CW - 20, oy)
            cv.glyph(c, ox + 20, oy, sc, fill=(232, 232, 232))
            if ri:
                cv.glyph(sl, ox + 20, oy, sc, stroke=(240, 70, 55), w=1.2)
    cv.save(os.path.join(OUT, "i9_vs_i10_18.png"))


def a_alt():
    C.set_slant(0.25)
    G = C.load()
    from round5 import correct
    sl = G["GeistSerifSlant_a"]["contours"]
    da = drawn.letter("a", "italic", sl)
    # a.alt: placed by its stem (the right part of the letter, y 60..330) on the drawn a's stem
    alt_raw = drawn.raw_contours("a.alt", "italic")
    dx, how = drawn.placement("a.alt", "italic", da["contours"])
    alt = drawn.shift(alt_raw, dx)
    r5 = correct("a", G, "1-6")["contours"]
    sc = 0.7; CW = int(760 * sc); H = 180 + int(1000 * sc) + 120; W = 40 + CW * 3
    cv = Canvas(W, H)
    cv.text((20, 14), "GEIST SERIF  Regular → Italic 14.04° (x' = x + y/4)  ·  /a  ·  the structural swap", (240, 240, 240), 30)
    cv.text((20, 58), "Mark's drawn italic (new_italics.pdf, 2026-10-25) · a.alt = his single-storey a, \"made for reference, poorly\" · not built by the solver",
            (170, 170, 170), 15)
    titles = [("drawn two-storey a", "Mark, italic row"), ("drawn a.alt", "Mark, single-storey (reference)"), ("solver a", "round 5, steps 1-6")]
    for i, ((t, s), cs, col) in enumerate(zip(titles, (da["contours"], alt, r5), ((200, 200, 200), (200, 200, 200), (120, 230, 140)))):
        ox = 20 + i * CW; oy = 180 + int(800 * sc)
        for yl in (0, 545):
            cv.line(ox, oy - yl * sc, ox + CW - 30, oy - yl * sc)
        xs = [n[0] for c in cs for n in c["nodes"]]
        x0 = (min(xs) + max(xs)) / 2
        cv.glyph(cs, ox + CW / 2 - x0 * sc - 15, oy, sc, fill=col)
        cv.text((ox, 110), t, (240, 240, 240), 22); cv.text((ox, 140), s, (150, 150, 150), 15)
    cv.text((20, H - 92), "what survives the swap: the stem and its foot tail (the same wedge). What is new: ONE bowl the full x-height high (an o-like oval", (170, 170, 170), 14)
    cv.text((20, H - 70), "closing on the stem, its top running into the stem's head under a small spur at the x-height). Gone: the hood and its terminal, the bar, the", (170, 170, 170), 14)
    cv.text((20, H - 48), "half-height bowl. Each letter centred in its column for viewing (not scored); a.alt's stem matched to the a's: %s." % how, (170, 170, 170), 14)
    cv.save(os.path.join(OUT, "a_alt.png"))


def z_diag():
    C.set_slant(1 / 3)
    G = C.load()
    import skeleton as SK
    from round5 import correct
    sl = G["GeistSerifSlant_z"]["contours"]
    off = correct("z", G, "1-6")["contours"]
    SK.Skeleton.I12_DIAGONAL = True
    try:
        on = correct("z", G, "1-6")["contours"]
    finally:
        SK.Skeleton.I12_DIAGONAL = False
    sc = 0.9; CW = int(760 * sc); H = 140 + int(800 * sc) + 80; W = 40 + CW * 3
    cv = Canvas(W, H)
    cv.text((20, 14), "GEIST SERIF  Regular → Italic 18.43° (x' = x + y/3)  ·  /z  ·  I12 on the diagonal", (240, 240, 240), 30)
    cv.text((20, 58), "the s's rigid spine rule applied to the z's diagonal (psi theta = 14.7° clockwise about its centre, ends sliding on the bars) · red = plain slant",
            (170, 170, 170), 15)
    for i, (t, cs) in enumerate((("plain slant", sl), ("round 5, diagonal spine OFF (shipped)", off), ("round 5, diagonal spine ON", on))):
        ox = 20 + i * CW; oy = 140 + int(650 * sc)
        cv.line(ox, oy, ox + CW - 30, oy)
        cv.glyph(cs, ox + 30, oy, sc, fill=(225, 225, 225))
        if i:
            cv.glyph(sl, ox + 30, oy, sc, stroke=(240, 70, 55), w=1.4)
        cv.text((ox, 100), t, (240, 240, 240), 20)
    cv.text((20, H - 60), "ON: the shear already turns a '/' diagonal 11.7° clockwise; the rigid turn takes it 3° further, so its ends run past the sheared bars", (190, 190, 190), 15)
    cv.text((20, H - 36), "(spikes at the top-right and bottom-left corners, the z ~20 u wider). The rule is kept behind Skeleton.I12_DIAGONAL.", (190, 190, 190), 15)
    os.makedirs(os.path.join(OUT, "dev"), exist_ok=True)
    cv.save(os.path.join(OUT, "dev", "z_I12_diagonal_18.png"))


def table():
    T = json.load(open(os.path.join(C.R5, "readings", "score_table.json")))
    rows = T["rows"]; cols = T["cols"]
    cw = [190] + [150] * (len(cols) - 1)
    W = max(sum(cw) + 40, 1560); H = 170 + 40 * (len(rows) + 1) + 40 * len(T["notes"]) + 40
    cv = Canvas(W, H)
    cv.text((20, 14), "GEIST SERIF  Regular → Italic 14.04° (x' = x + y/4)  ·  SCORE vs Mark's drawn italic", (240, 240, 240), 30)
    cv.text((20, 58), "XOR % = area(candidate △ drawing) / area(drawing) · lower is closer · drawings placed by stems / held corners / round centre", (170, 170, 170), 15)
    y = 110
    x = 20
    for c, w in zip(cols, cw):
        cv.text((x, y), c, (232, 184, 74), 17); x += w
    y += 40
    for r in rows:
        x = 20
        col = (150, 150, 150) if r.get("dim") else (235, 235, 235)
        for v, w in zip(r["cells"], cw):
            cv.text((x, y), str(v), col, 17); x += w
        cv.line(20, y + 32, W - 20, y + 32)
        y += 40
    y += 10
    for n in T["notes"]:
        cv.text((20, y), n, (170, 170, 170), 14); y += 30
    cv.save(os.path.join(OUT, "score_table.png"))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("i9", "all"): i9_vs_i10()
    if what in ("aalt", "all"): a_alt()
    if what in ("z", "all"): z_diag()
    if what in ("table", "all") and os.path.exists(os.path.join(C.R5, "readings", "score_table.json")): table()
