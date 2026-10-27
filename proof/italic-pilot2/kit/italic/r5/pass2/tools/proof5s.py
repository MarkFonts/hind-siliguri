"""Round 5 · s round: the proof-sheet kit (dark background, Menlo, the family and the angle first and large, colour
keys drawn in their colours).

    sh = Sheet(W, H)
    pn = sh.panel(ox, oy, w, h, box=(x0, y0, x1, y1))          # font units -> pixels, y up, fitted into w x h
    pn.fill(contours, col, alpha=255); pn.outline(contours, col, w=2); pn.nodes(contours, col); pn.lines(...)
    sh.text(x, y, s, col, size); sh.key(x, y, [(name, col), ...]); sh.title(...)
    sh.save(path)
"""
import os, math
import numpy as np
import skia
from PIL import Image, ImageDraw, ImageFont
import drawn

MENLO = "/System/Library/Fonts/Menlo.ttc"
BG = (18, 19, 23)
INK = (236, 236, 236)
DIM = (150, 150, 155)
FAINT = (70, 71, 78)
COL = dict(drawn=(112, 112, 118), roman=(80, 200, 235), slant=(240, 72, 58), r5=(80, 145, 255), r5s=(90, 222, 118),
           his=(232, 232, 236), alt=(250, 200, 70), mag=(225, 110, 230), cyan=(80, 200, 235))


def fnt(sz):
    return ImageFont.truetype(MENLO, sz)


class Panel:
    def __init__(self, sheet, ox, oy, w, h, box, pad=10):
        self.sh = sheet; self.ox, self.oy, self.w, self.h = ox, oy, w, h
        x0, y0, x1, y1 = box
        self.s = min((w - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0))
        # centre the box
        self.tx = ox + (w - (x1 - x0) * self.s) / 2 - x0 * self.s
        self.ty = oy + (h - (y1 - y0) * self.s) / 2 + y1 * self.s
        self.box = box

    def P(self, p):
        return (self.tx + p[0] * self.s, self.ty - p[1] * self.s)

    def _begin(self):
        cv = self.sh.cv; cv.save()
        cv.clipRect(skia.Rect.MakeXYWH(self.ox, self.oy, self.w, self.h))
        cv.translate(self.tx, self.ty); cv.scale(self.s, -self.s)
        return cv

    def fill(self, cs, col, alpha=255):
        cv = self._begin()
        cv.drawPath(drawn.path(cs), skia.Paint(AntiAlias=True, Color=skia.Color(*col, alpha)))
        cv.restore()

    def outline(self, cs, col, w=2.0, alpha=255):
        cv = self._begin()
        cv.drawPath(drawn.path(cs), skia.Paint(AntiAlias=True, Color=skia.Color(*col, alpha), Style=skia.Paint.kStroke_Style,
                                               StrokeWidth=w / self.s, StrokeJoin=skia.Paint.kRound_Join))
        cv.restore()

    def polyline(self, pts, col, w=2.0, alpha=255, closed=False):
        if len(pts) < 2:
            return
        cv = self._begin(); p = skia.Path(); p.moveTo(*map(float, pts[0]))
        for q in pts[1:]:
            p.lineTo(*map(float, q))
        if closed:
            p.close()
        cv.drawPath(p, skia.Paint(AntiAlias=True, Color=skia.Color(*col, alpha), Style=skia.Paint.kStroke_Style, StrokeWidth=w / self.s,
                                  StrokeJoin=skia.Paint.kRound_Join, StrokeCap=skia.Paint.kRound_Cap))
        cv.restore()

    def hline(self, y, col=FAINT, w=1.0):
        self.polyline([(self.box[0] - 1e4, y), (self.box[2] + 1e4, y)], col, w)

    def dot(self, p, col, r=3.0, fill=True):
        cv = self.sh.cv; X, Y = self.P(p)
        pt = skia.Paint(AntiAlias=True, Color=skia.Color(*col), Style=skia.Paint.kFill_Style if fill else skia.Paint.kStroke_Style, StrokeWidth=1.5)
        cv.drawCircle(X, Y, r, pt)

    def nodes(self, cs, col, r=3.0, handles=False):
        for c in cs:
            ns = c["nodes"]; N = len(ns)
            for i, n in enumerate(ns):
                if n[2] != "o":
                    self.dot(n[:2], col, r)
                elif handles:
                    self.dot(n[:2], col, r * 0.6, fill=False)
            if handles:
                for i, n in enumerate(ns):
                    if n[2] == "o":
                        for j in ((i - 1) % N, (i + 1) % N):
                            if ns[j][2] != "o":
                                self.polyline([ns[j][:2], n[:2]], col, 1.0, 160)

    def arrow(self, p, q, col, w=2.5, gain=1.0):
        q = (p[0] + (q[0] - p[0]) * gain, p[1] + (q[1] - p[1]) * gain)
        self.polyline([p, q], col, w)
        X0, Y0 = self.P(p); X1, Y1 = self.P(q)
        a = math.atan2(Y1 - Y0, X1 - X0)
        cv = self.sh.cv; pt = skia.Paint(AntiAlias=True, Color=skia.Color(*col), StrokeWidth=w, Style=skia.Paint.kStroke_Style)
        for s_ in (+1, -1):
            cv.drawLine(X1, Y1, X1 - 9 * math.cos(a + s_ * 0.45), Y1 - 9 * math.sin(a + s_ * 0.45), pt)

    def label(self, p, s, col, size=13, dx=5, dy=-16):
        X, Y = self.P(p); self.sh.text(X + dx, Y + dy, s, col, size)

    def frame(self, col=FAINT):
        cv = self.sh.cv
        cv.drawRect(skia.Rect.MakeXYWH(self.ox, self.oy, self.w, self.h), skia.Paint(Color=skia.Color(*col), Style=skia.Paint.kStroke_Style, StrokeWidth=1))


class Sheet:
    def __init__(self, W, H):
        self.W, self.H = int(W), int(H)
        self.surf = skia.Surface(self.W, self.H); self.cv = self.surf.getCanvas(); self.cv.clear(skia.Color(*BG))
        self.texts = []

    def panel(self, ox, oy, w, h, box, pad=10):
        return Panel(self, ox, oy, w, h, box, pad)

    def text(self, x, y, s, col=INK, size=16):
        self.texts.append((x, y, s, col, size))

    def tlen(self, s, size):
        return ImageDraw.Draw(Image.new("RGB", (4, 4))).textlength(s, font=fnt(size))

    def key(self, x, y, items, size=17, swatch=True):
        """the colour key IN its colours: a swatch and the word, each in its own colour"""
        for name, col in items:
            if swatch:
                self.rects.append((x, y + 3, x + size - 3, y + size, col)) if hasattr(self, "rects") else setattr(self, "rects", [(x, y + 3, x + size - 3, y + size, col)])
                x += size + 4
            self.text(x, y, name, col, size); x += self.tlen(name, size) + 26
        return x

    def title(self, glyph_line, angle, sub=None):
        self.text(24, 16, "GEIST SERIF", INK, 40)
        self.text(24 + self.tlen("GEIST SERIF", 40) + 24, 16, angle, INK, 40)
        self.text(26, 66, glyph_line, (205, 205, 210), 19)
        if sub:
            self.text(26, 92, sub, DIM, 15)

    def save(self, path):
        im = Image.frombytes("RGBA", (self.W, self.H), self.surf.makeImageSnapshot().tobytes()).convert("RGB")
        d = ImageDraw.Draw(im)
        for r in getattr(self, "rects", []):
            d.rectangle(r[:4], fill=r[4])
        for x, y, s, col, size in self.texts:
            d.text((x, y), s, fill=col, font=fnt(size))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        im.save(path)
        return path
