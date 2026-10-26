"""Drawing primitives for every sheet: Panel (a glyph panel in font units), titles, node numbers, fonts.

Label fonts (no paths in the package): Cal Sans Text UI for titles, Newsreader as the second choice, a monospace
(Menlo, DejaVu Sans Mono, Consolas) for node numbers. They are looked up by file name in $WMPARTS_FONTS (a list of
folders or font files, separated by os.pathsep), then in the platform's standard font folders; when none is found
PIL's default font is used. Every title starts with FAMILY Master · /glyph (fontlabel).
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ..rungs import Outline   # noqa: F401

SS = 2  # supersample
BG, INK, EDGE = (13, 13, 13), (45, 58, 32), (154, 154, 154)
ON, OFF, LBL_ON, LBL_OFF = (232, 232, 232), (91, 143, 217), (232, 184, 74), (111, 160, 230)
LABEL_FONTS = ("CalSansTextUI-Regular", "Cal Sans Text UI Regular", "CalSansUI-Regular", "Newsreader-VariableFont_opsz,wght",
               "Newsreader-Regular", "Newsreader[opsz,wght]", "Newsreader")
MONO_FONTS = ("Menlo", "DejaVuSansMono", "DejaVu Sans Mono", "Consolas", "consola", "LiberationMono-Regular", "Courier New")
FONT_EXT = (".ttf", ".otf", ".ttc")


def font_dirs():
    """$WMPARTS_FONTS first, then the standard per-user and system font folders of this platform"""
    env = [p for p in os.environ.get("WMPARTS_FONTS", "").split(os.pathsep) if p]
    home = os.path.expanduser("~")
    std = [os.path.join(home, "Library", "Fonts"), os.path.join(os.sep, "Library", "Fonts"),
           os.path.join(os.sep, "System", "Library", "Fonts"), os.path.join(os.sep, "System", "Library", "Fonts", "Supplemental"),
           os.path.join(home, ".local", "share", "fonts"), os.path.join(home, ".fonts"),
           os.path.join(os.sep, "usr", "share", "fonts"), os.path.join(os.sep, "usr", "local", "share", "fonts")]
    for var, sub in (("WINDIR", "Fonts"), ("LOCALAPPDATA", os.path.join("Microsoft", "Windows", "Fonts"))):
        if os.environ.get(var):
            std.append(os.path.join(os.environ[var], sub))
    return env + std


def find_font(names, dirs=None):
    """the first font file whose name (without extension) is one of names, searching dirs in order (2 levels deep)"""
    want = [n.lower() for n in names]
    for d in (dirs if dirs is not None else font_dirs()):
        if os.path.isfile(d):
            if os.path.splitext(os.path.basename(d))[0].lower() in want:
                return d
            continue
        if not os.path.isdir(d):
            continue
        hits = {}
        for root, subdirs, files in os.walk(d):
            if root[len(d):].count(os.sep) >= 2:
                subdirs[:] = []
            for f in files:
                stem, ext = os.path.splitext(f)
                if ext.lower() in FONT_EXT and stem.lower() in want:
                    hits.setdefault(stem.lower(), os.path.join(root, f))
        for n in want:
            if n in hits:
                return hits[n]
    return None


CAL = find_font(LABEL_FONTS)        # titles (None -> PIL's default font)
MENLO = find_font(MONO_FONTS)       # node numbers
_FONTS = {}


def _ft(path, px):
    key = (path, int(px))
    if key not in _FONTS:
        try:
            _FONTS[key] = ImageFont.truetype(path, int(px)) if path else ImageFont.load_default(int(px))
        except (OSError, TypeError):
            _FONTS[key] = ImageFont.load_default(int(px))
    return _FONTS[key]


def font(path, size):
    """a label font at size (supersampled); path None or unreadable -> PIL's default font"""
    return _ft(path, int(size * SS))


def ramp(w, lo, hi):
    """plugin scale: lo = 0.6 min stem, hi = 1.1 max stem; red (thin) -> yellow (mid) -> grey (top)."""
    if w is None or w < 0:
        return (80, 80, 80)
    t = (w - lo) / max(1e-6, hi - lo)
    stops = [(0.0, (232, 64, 42)), (0.5, (242, 209, 58)), (1.0, (165, 165, 165))]
    if t <= 0: return stops[0][1]
    if t >= 1: return stops[-1][1]
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if a <= t <= b:
            u = (t - a) / (b - a)
            return tuple(int(ca[i] + (cb[i] - ca[i]) * u) for i in range(3))


def fontlabel(g, glyph=None, master=None):
    """the mandatory title head (Mark 2026-10-24): FAMILY Master · /glyph, e.g. "MARYA Roman · /e" """
    fam = g.get("family") or ""
    return ("%s %s · /%s" % (fam, master or g["master"], glyph or g["glyph"])).strip()


def header(im, text, sub=None, size=30):
    """a sheet-level band on top: the FAMILY and master in large type (Mark: label proofs prominently)"""
    from PIL import Image as _I, ImageDraw as _D
    H = 64 if sub else 50
    out = _I.new("RGB", (im.width, im.height + H), BG)
    d = _D.Draw(out)
    d.text((14, 8), text, fill=LBL_ON, font=_ft(CAL, size))
    if sub:
        d.text((14, 44), sub, fill=(170, 170, 170), font=_ft(CAL, 13))
    out.paste(im, (0, H))
    return out


class Panel:
    def __init__(self, w, h, bbox, margin=70):
        self.im = Image.new("RGB", (w * SS, h * SS), BG)
        self.d = ImageDraw.Draw(self.im)
        x0, y0, x1, y1 = bbox
        sx = (w - 2 * margin) / max(1, x1 - x0); sy = (h - 2 * margin - 40) / max(1, y1 - y0)
        self.s = min(sx, sy) * SS
        self.ox = (w * SS - (x1 - x0) * self.s) / 2 - x0 * self.s
        self.oy = (h * SS + 40 * SS - (y1 - y0) * self.s) / 2 + y1 * self.s
        self.w, self.h = w, h

    def pt(self, p):
        return (self.ox + p[0] * self.s, self.oy - p[1] * self.s)

    def title(self, text, sub=None, size=19):
        # the family + master lead every title, in large type; shrink only as far as needed to fit the panel
        sz = size
        while sz > 10 and self.d.textlength(text, font=font(CAL, sz)) > (self.w - 24) * SS:
            sz -= 1
        self.d.text((14 * SS, 8 * SS), text, fill=LBL_ON, font=font(CAL, sz))
        if sub:
            self.d.text((14 * SS, 33 * SS), sub, fill=(170, 170, 170), font=font(CAL, 11))

    def fill_outline(self, ol, color=INK, edge=EDGE):
        # true nonzero winding fill (a contour drawn the other way round, an overlap, a counter all come out right)
        W, H = self.im.size
        acc = np.zeros((H, W), np.int16)
        for pi, poly in enumerate(ol.polys):
            if len(poly) < 3:
                continue
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).polygon([self.pt(p) for p in poly], fill=1)
            acc += np.asarray(m, np.int16) * (1 if ol.area[pi] > 0 else -1)
        ink = Image.fromarray(((acc != 0) * 255).astype(np.uint8), "L")
        self.im.paste(Image.new("RGB", (W, H), color), (0, 0), ink)
        for pi, poly in enumerate(ol.polys):
            pts = [self.pt(p) for p in poly] + [self.pt(poly[0])]
            self.d.line(pts, fill=edge, width=max(1, int(0.8 * SS)))

    def nodes(self, ol, labels=True):
        f = font(MENLO, 9)
        for gi, (x, y, t, sm) in ol.node_xy.items():
            X, Y = self.pt((x, y))
            if t == "o":
                r = 2.2 * SS
                self.d.ellipse([X - r, Y - r, X + r, Y + r], outline=OFF, width=max(1, int(0.9 * SS)))
                if labels: self.d.text((X + 4 * SS, Y - 4 * SS), str(gi), fill=LBL_OFF, font=f)
            else:
                r = 2.6 * SS
                self.d.rectangle([X - r, Y - r, X + r, Y + r], fill=ON)
                if labels: self.d.text((X + 4 * SS, Y + 1 * SS), str(gi), fill=LBL_ON, font=f)

    def line(self, a, b, color, width=1.0):
        self.d.line([self.pt(a), self.pt(b)], fill=color, width=max(1, int(width * SS)))

    def dot(self, p, color, r=1.6):
        X, Y = self.pt(p); r *= SS
        self.d.ellipse([X - r, Y - r, X + r, Y + r], fill=color)

    def text(self, p, s, color, size=8, dx=3, dy=-4):
        X, Y = self.pt(p)
        self.d.text((X + dx * SS, Y + dy * SS), s, fill=color, font=font(MENLO, size))

    def heat(self, F, prov, mask, geo, lo, hi):
        """paint the engine's field under the ink (pixel frame -> panel)."""
        H, W = F.shape
        res, ox, oy, pad = geo["res"], geo["ox"], geo["oy"], geo["pad"]
        img = np.zeros((H, W, 3), np.uint8); img[:] = BG
        t = np.clip((F - lo) / max(1e-6, hi - lo), 0, 1)
        # vectorised ramp
        c0 = np.array([232, 64, 42]); c1 = np.array([242, 209, 58]); c2 = np.array([165, 165, 165])
        col = np.where((t < 0.5)[..., None], c0 + (c1 - c0) * (t / 0.5)[..., None], c1 + (c2 - c1) * ((t - 0.5) / 0.5)[..., None])
        col = col.astype(np.uint8)
        img[mask] = col[mask]
        carried = mask & (prov == 1)
        img[carried] = (img[carried] * 0.55 + np.array(BG) * 0.45).astype(np.uint8)
        pil = Image.fromarray(img)
        # pixel (c,r) -> units: x = ox + (c - pad)/res ; y = oy + ((H-1-r) - pad)/res
        x_left = ox + (0 - pad - 0.5) / res; x_right = ox + (W - pad - 0.5) / res
        y_top = oy + (H - 1 - 0 - pad + 0.5) / res; y_bot = oy + (H - 1 - (H - 1) - pad - 0.5) / res
        X0, Y0 = self.pt((x_left, y_top)); X1, Y1 = self.pt((x_right, y_bot))
        pil = pil.resize((max(1, int(X1 - X0)), max(1, int(Y1 - Y0))), Image.NEAREST)
        self.im.paste(pil, (int(X0), int(Y0)))

    def legend(self, lo, hi, stems):
        x, y = 16 * SS, (self.h - 30) * SS
        wdt = 160 * SS
        for i in range(wdt):
            w = lo + (hi - lo) * i / wdt
            self.d.line([(x + i, y), (x + i, y + 8 * SS)], fill=ramp(w, lo, hi))
        f = font(MENLO, 8)
        self.d.text((x, y + 10 * SS), "%d" % lo, fill=(170, 170, 170), font=f)
        self.d.text((x + wdt - 18 * SS, y + 10 * SS), "%d" % hi, fill=(170, 170, 170), font=f)
        for s in stems:
            xi = x + wdt * (s - lo) / (hi - lo)
            self.d.line([(xi, y - 3 * SS), (xi, y + 11 * SS)], fill=(240, 240, 240), width=SS)
        self.d.text((x + wdt + 8 * SS, y), "stems " + ",".join(str(int(s)) for s in stems), fill=(170, 170, 170), font=f)

    def out(self, w=None, h=None):
        return self.im.resize((self.im.width // SS, self.im.height // SS), Image.LANCZOS)


def held_edges(panel, ol):
    for k in ol.serif_segs:
        sg = ol.segs[k]
        pts = [panel.pt(p) for p in sg.poly]
        panel.d.line(pts, fill=(96, 150, 230), width=max(1, int(2.6 * SS)))


def bbox_of(ol, pad=30):
    xs = [p[0] for poly in ol.polys for p in poly]; ys = [p[1] for poly in ol.polys for p in poly]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
