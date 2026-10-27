"""Proof sheets (PNG, skia). House look: dark ground, Menlo labels, family + master first and large, color keys drawn in
their own colors, solid fills on every comparison."""
import skia, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from geom import path

BG = skia.Color(22, 22, 26); INK = (236, 236, 240); DIM = (150, 150, 158); FAINT = (60, 60, 68)
UP_C = (200, 200, 206); SL_C = (240, 120, 100); IT_C = (110, 220, 140)
RED = (240, 72, 58); GREEN = (90, 222, 118); GREY = (120, 120, 128)
MENLO = skia.Typeface("Menlo"); MENLO_B = skia.Typeface("Menlo", skia.FontStyle.Bold())
BANGLA = skia.Typeface("Kohinoor Bangla")


def col(c, a=255):
    return skia.Color(c[0], c[1], c[2], a)


class Sheet:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.surf = skia.Surface(W, H); self.c = self.surf.getCanvas(); self.c.clear(BG)

    def text(self, x, y, s, color=INK, size=18, bold=False, face=None):
        f = skia.Font(face or (MENLO_B if bold else MENLO), size)
        self.c.drawString(s, x, y + size, f, skia.Paint(Color=col(color), AntiAlias=True))
        return f.measureText(s)

    def header(self, family, master, sub, note=None):
        self.text(30, 24, family + "  ·  " + master, INK, 46, True)
        self.text(30, 84, sub, DIM, 22)
        if note:
            self.text(30, 116, note, DIM, 16)

    def key(self, x, y, items, size=18):
        """color key drawn in its colors: swatch + colored word"""
        for name, c in items:
            self.c.drawRect(skia.Rect.MakeXYWH(x, y + 3, size, size), skia.Paint(Color=col(c), AntiAlias=True))
            x += size + 8
            w = self.text(x, y, name, c, size)
            x += w + 30
        return x

    def glyph(self, cs, x, y, s, color, alpha=255, stroke=None):
        p = path(cs, dx=x, s=s, base=y)
        self.c.drawPath(p, skia.Paint(Color=col(color, alpha), AntiAlias=True))
        if stroke:
            self.c.drawPath(p, skia.Paint(Color=col(stroke), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.0))

    def overlay(self, sl, it, x, y, s):
        """raw slant vs corrected: grey = both, red = taken away (slant only), green = added (corrected only)"""
        a = path(sl, dx=x, s=s, base=y); b = path(it, dx=x, s=s, base=y)
        try:
            raise RuntimeError("coverage always: path ops mis-fill self-crossing Bangla outlines")
            both = skia.Op(a, b, skia.PathOp.kIntersect_PathOp)
            gone = skia.Op(a, b, skia.PathOp.kDifference_PathOp)
            add = skia.Op(b, a, skia.PathOp.kDifference_PathOp)
            for p, c in ((both, GREY), (gone, RED), (add, GREEN)):
                if p is not None:
                    self.c.drawPath(p, skia.Paint(Color=col(c), AntiAlias=True))
        except RuntimeError:
            # path ops refuse some self-crossing outlines: composite by coverage instead (same colors)
            bb = a.computeTightBounds(); bb.join(b.computeTightBounds())
            x0, y0 = int(bb.left()) - 2, int(bb.top()) - 2; w, h = int(bb.width()) + 5, int(bb.height()) + 5
            def mask(p):
                sf = skia.Surface(w, h); cv = sf.getCanvas(); cv.clear(skia.Color(0, 0, 0)); cv.translate(-x0, -y0)
                cv.drawPath(p, skia.Paint(Color=skia.Color(255, 255, 255), AntiAlias=True))
                return sf.makeImageSnapshot().toarray()[:, :, 0].astype(float) / 255.0
            ma, mb = mask(a), mask(b)
            img = np.zeros((h, w, 4), np.uint8)
            for m_, c in ((np.minimum(ma, mb), GREY), (np.clip(ma - mb, 0, 1), RED), (np.clip(mb - ma, 0, 1), GREEN)):
                for k in range(3):
                    img[:, :, k] = np.clip(img[:, :, k] + m_ * c[k], 0, 255).astype(np.uint8)
                img[:, :, 3] = np.clip(img[:, :, 3].astype(float) + m_ * 255, 0, 255).astype(np.uint8)
            im = skia.Image.fromarray(img, colorType=skia.ColorType.kRGBA_8888_ColorType, alphaType=skia.AlphaType.kUnpremul_AlphaType)
            self.c.drawImage(im, x0, y0)

    def comb(self, cs, x, y, s, color, gain=4000.0, n=24):
        """curvature comb on the outline (teeth inward/outward by the curvature sign)"""
        pnt = skia.Paint(Color=col(color, 150), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=0.8)
        env = skia.Paint(Color=col(color, 230), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.0)
        for c in cs:
            nd = c["nodes"]; N = len(nd); ons = [i for i in range(N) if nd[i][2] != "o"]
            for a_, b_ in zip(ons, ons[1:] + ons[:1]):
                offs = [nd[k % N] for k in range(a_ + 1, a_ + 1 + ((b_ - a_ - 1) % N))]
                if len(offs) != 2:
                    continue
                P = np.array([nd[a_][:2], offs[0][:2], offs[1][:2], nd[b_][:2]], float)
                ts = np.linspace(0, 1, n + 1)
                tops = []
                for t in ts:
                    u = 1 - t
                    p = u**3*P[0] + 3*u*u*t*P[1] + 3*u*t*t*P[2] + t**3*P[3]
                    d1 = 3*(u*u*(P[1]-P[0]) + 2*u*t*(P[2]-P[1]) + t*t*(P[3]-P[2]))
                    d2 = 6*(u*(P[2]-2*P[1]+P[0]) + t*(P[3]-2*P[2]+P[1]))
                    L = np.hypot(*d1)
                    if L < 1e-9:
                        continue
                    k = (d1[0]*d2[1] - d1[1]*d2[0]) / L**3
                    nrm = np.array([d1[1], -d1[0]]) / L
                    L_ = max(-120.0, min(120.0, k * gain))      # teeth capped at 120 u
                    q = p + nrm * L_
                    P0 = (x + p[0]*s, y - p[1]*s); Q = (x + q[0]*s, y - q[1]*s)
                    self.c.drawLine(*P0, *Q, pnt); tops.append(Q)
                for A, B in zip(tops, tops[1:]):
                    self.c.drawLine(*A, *B, env)

    def nodes(self, cs, x, y, s, color=INK, r=2.2):
        for c in cs:
            for n in c["nodes"]:
                p = (x + n[0]*s, y - n[1]*s)
                if n[2] == "o":
                    self.c.drawCircle(*p, r*0.7, skia.Paint(Color=col(DIM), AntiAlias=True))
                else:
                    self.c.drawCircle(*p, r, skia.Paint(Color=col(color), AntiAlias=True))

    def hline(self, x0, x1, y, color=FAINT):
        self.c.drawLine(x0, y, x1, y, skia.Paint(Color=col(color), StrokeWidth=1))

    def save(self, fn):
        img = self.surf.makeImageSnapshot(); img.save(fn, skia.kPNG)
        return fn
