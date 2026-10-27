"""Overlay of the raw slant and the corrected italic, letter by letter, the way the font renders them
(open corners erased, nonzero fill): ink in BOTH = light grey, ink only in the raw slant = red (what the
correction took away), ink only in the corrected = green (what it added).

overlay_sheet.py [letters] [--out PNG] [--label SIZE]      default: all 18 letters, six per row
"""
import sys, os, json, argparse
import numpy as np
import skia
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bowls_sheet import path_of, SRC, MENLO, BG, LBL

BOTH, GONE, ADDED = (225, 225, 225), (235, 70, 55), (90, 215, 110)
ALL = "f j H n a E T r v e y k x p s B z quoteright".split()


def mask(g, W, H, ox, oy, scale):
    surf = skia.Surface(W, H); cv = surf.getCanvas(); cv.clear(skia.ColorBLACK)
    cv.translate(ox, oy); cv.scale(scale, -scale)
    cv.drawPath(path_of(g), skia.Paint(AntiAlias=True, Color=skia.ColorWHITE))
    return np.frombuffer(surf.makeImageSnapshot().tobytes(), np.uint8).reshape(H, W, 4)[:, :, 0].astype(np.float32) / 255.0


def sheet(letters, out, label=21, scale=0.42, per_row=6):
    G = json.load(open(SRC))
    CW = int(max(G["GeistSerifSlant_%s" % gl]["width"] for gl in letters) * scale) + 110    # the slant's top leans right
    CH = int((800 + 212) * scale) + 90                                                         # ascender to descender + labels
    rows = (len(letters) + per_row - 1) // per_row
    W, H = CW * per_row + 20, CH * rows + 20
    img = np.zeros((H, W, 3), np.uint8); img[:] = BG
    labels = []
    for i, gl in enumerate(letters):
        r, c = divmod(i, per_row)
        x0, y0 = 10 + c * CW, 10 + r * CH
        ox, oy = x0 + 30, y0 + 50 + 800 * scale            # baseline sits 800 u (ascender) below the label band
        a = mask(G["GeistSerifSlant_%s" % gl], W, H, ox, oy, scale)
        b = mask(G["GeistSerifItalic_%s" % gl], W, H, ox, oy, scale)
        both = np.minimum(a, b); gone = np.clip(a - b, 0, 1); added = np.clip(b - a, 0, 1)
        for m, col in ((both, BOTH), (gone, GONE), (added, ADDED)):
            img = (img * (1 - m[..., None]) + np.array(col, np.float32) * m[..., None]).astype(np.uint8)
        labels.append((x0 + 8, y0 + 8, "/%s  slant + corrected" % gl))
    im = Image.fromarray(img); d = ImageDraw.Draw(im); f = ImageFont.truetype(MENLO, label)
    for x, y, t in labels:
        d.text((x, y), t, fill=LBL, font=f)
    d.text((12, H - label - 10), "light = ink in both   red = only in the raw slant (taken away)   green = only in the corrected (added)",
           fill=(170, 170, 170), font=ImageFont.truetype(MENLO, label))
    im.save(out); print("wrote", out, im.size)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("letters", nargs="?", default=",".join(ALL))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sheets", "overlay_slant_corrected.png"))
    ap.add_argument("--label", type=int, default=21)
    a = ap.parse_args()
    sheet(a.letters.replace(" ", ",").split(","), a.out, label=a.label)
