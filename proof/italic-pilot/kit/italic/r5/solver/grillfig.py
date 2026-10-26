"""Figures for GRILL.pdf: light, print-legible drawings of the real outlines (set.json), the real movers
(move.Mover, groupmove.GroupMover) and hand-built options made with GroupMover's own handle rules.

Never edits other tools; imports them read-only."""
import sys, os, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import io, contextlib
from curvcomb import segments, analyse, kcol
from move import Mover
from groupmove import GroupMover

HERE = os.path.dirname(os.path.abspath(__file__))
SET = json.load(open(os.path.join(HERE, "..", "src", "set.json")))
SS = 2
CAL = "/Users/Mark/Documents/Github/sans-ui/fonts/ttf/CalSansTextUI-Regular.ttf"
CALB = "/Users/Mark/Documents/Github/sans-ui/fonts/ttf/CalSansTextUI-SemiBold.ttf"
NEWS = os.path.expanduser("~/Library/Fonts/Newsreader-VariableFont_opsz,wght.ttf")
NEWSI = os.path.expanduser("~/Library/Fonts/Newsreader-Italic-VariableFont_opsz,wght.ttf")
MENLO = "/System/Library/Fonts/Menlo.ttc"

WHITE = (255, 255, 255)
PAPER = (255, 255, 255)
INK = (20, 20, 20)
DIM_FILL = (226, 226, 226)
DIM_EDGE = (150, 150, 150)
RES_FILL = (196, 214, 238)       # option result fill (light blue)
RES_EDGE = (30, 60, 130)
DRAWN = (90, 90, 90)             # drawn outline, dashed
HI = (214, 60, 30)               # rings, arrows, highlighted points
HI2 = (20, 130, 70)              # second highlight colour
HL_FILL = (250, 224, 200)        # region of interest


_fonts = {}
def F(path, size, var=None):
    k = (path, size, var)
    if k not in _fonts:
        f = ImageFont.truetype(path, int(size * SS))
        if var:
            try:
                f.set_variation_by_axes(var)
            except Exception:
                pass
        _fonts[k] = f
    return _fonts[k]


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


# ---- geometry -------------------------------------------------------------------------------------------
def flat_xy(contours):
    return [(float(n[0]), float(n[1])) for c in contours for n in c["nodes"]]


def contour_polys(contours, n=40):
    """per contour: flattened polygon (list of (x, y))"""
    out = []
    base = 0
    for c in contours:
        segs = segments([c])
        pts = []
        for gi, gj, kind, P, _ in segs:
            if kind == "curve":
                t = np.linspace(0, 1, n)[:-1]
                u = 1 - t
                P_ = np.asarray(P, float)
                B = (u ** 3)[:, None] * P_[0] + (3 * u * u * t)[:, None] * P_[1] + (3 * u * t * t)[:, None] * P_[2] + (t ** 3)[:, None] * P_[3]
                pts += [tuple(b) for b in B]
            else:
                pts.append(tuple(P[0]))
        out.append(pts)
    return out


def seg_poly(contours, gi, gj, n=48):
    """flattened polyline of the segment from global node gi to gj (file order)"""
    for a, b, kind, P, _ in segments(contours):
        if a == gi and b == gj:
            if kind == "curve":
                t = np.linspace(0, 1, n); u = 1 - t; P_ = np.asarray(P, float)
                B = (u ** 3)[:, None] * P_[0] + (3 * u * u * t)[:, None] * P_[1] + (3 * u * t * t)[:, None] * P_[2] + (t ** 3)[:, None] * P_[3]
                return [tuple(b) for b in B]
            return [tuple(P[0]), tuple(P[1])]
    return []


def path_poly(contours, nodes):
    """polyline through consecutive on-curve nodes [a, b, c...] (each pair must be a segment)"""
    pts = []
    for a, b in zip(nodes, nodes[1:]):
        pts += seg_poly(contours, a, b)
    return pts


def bbox(contours_list, pad=20):
    xs = [p[0] for cs in contours_list for p in flat_xy(cs)]
    ys = [p[1] for cs in contours_list for p in flat_xy(cs)]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


# ---- movers ---------------------------------------------------------------------------------------------
_cache = {}
def gm(key):
    if ("gm", key) not in _cache:
        _cache[("gm", key)] = quiet(GroupMover, SET[key])
    return _cache[("gm", key)]


def mv(key):
    if ("mv", key) not in _cache:
        _cache[("mv", key)] = quiet(Mover, SET[key])
    return _cache[("mv", key)]


def drawn(key):
    return SET[key]["contours"]


def custom(key, vec, t=1.0):
    """hand-built option on the real nodes: on-curve node -> move (dx, dy); handles ride with their node,
    a curve whose two ends move differently keeps its handle directions and scales their lengths by
    new chord / drawn chord (GroupMover's own handle step, reused as is)."""
    G = quiet(GroupMover, SET[key])
    G.vec = {nd: tuple(map(float, v)) for nd, v in vec.items()}
    quiet(G._handles)
    return G.contours_at(t)


def custom_illustrator(key, vec):
    """Illustrator's default: selected points move with their own handles; nothing is rescaled."""
    cs = json.loads(json.dumps(SET[key]["contours"]))
    base = 0
    for c in cs:
        N = len(c["nodes"])
        nodes = c["nodes"]
        ons = [i for i in range(N) if nodes[i][2] != "o"]
        own = {}
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [(k % N) for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
            if len(offs) == 2:
                own[offs[0]] = i; own[offs[1]] = j
        moved = {}
        for i in range(N):
            gi = base + i
            if nodes[i][2] != "o" and gi in vec:
                moved[i] = vec[gi]
        for i in range(N):
            v = moved.get(i) if nodes[i][2] != "o" else moved.get(own.get(i, -1))
            if v:
                nodes[i][0] += v[0]; nodes[i][1] += v[1]
        base += N
    return cs


def node_xy(contours, nd):
    return flat_xy(contours)[nd]


def unit(v):
    L = math.hypot(*v)
    return (v[0] / L, v[1] / L) if L > 1e-12 else (0.0, 0.0)


# ---- drawing --------------------------------------------------------------------------------------------
class Fig:
    def __init__(self, w, h, box, margin=24, bg=PAPER):
        self.w, self.h = w, h
        self.im = Image.new("RGB", (w * SS, h * SS), bg)
        self.d = ImageDraw.Draw(self.im)
        x0, y0, x1, y1 = box
        s = min((w - 2 * margin) / max(1, x1 - x0), (h - 2 * margin) / max(1, y1 - y0))
        self.s = s * SS
        self.ox = (w * SS - (x1 - x0) * self.s) / 2 - x0 * self.s
        self.oy = (h * SS - (y1 - y0) * self.s) / 2 + y1 * self.s

    def pt(self, p):
        return (self.ox + p[0] * self.s, self.oy - p[1] * self.s)

    def fill(self, contours, color, edge=None, width=1.2):
        """nonzero winding fill of the real contours (overlaps stay ink)"""
        W, H = self.im.size
        acc = np.zeros((H, W), np.int16)
        polys = contour_polys(contours)
        for poly in polys:
            if len(poly) < 3:
                continue
            a = 0.0
            for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
                a += x0 * y1 - x1 * y0
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).polygon([self.pt(p) for p in poly], fill=1)
            acc += np.asarray(m, np.int16) * (1 if a > 0 else -1)
        mask = Image.fromarray(((acc != 0) * 255).astype(np.uint8))
        self.im.paste(Image.new("RGB", (W, H), color), (0, 0), mask)
        if edge:
            for poly in polys:
                if len(poly) > 1:
                    self.d.line([self.pt(p) for p in poly + poly[:1]], fill=edge, width=max(1, int(width * SS)))

    def outline(self, contours, color, width=1.2, dash=None):
        for poly in contour_polys(contours):
            self.poly(poly + poly[:1], color, width, dash)

    def poly(self, pts, color, width=1.2, dash=None):
        if len(pts) < 2:
            return
        if not dash:
            self.d.line([self.pt(p) for p in pts], fill=color, width=max(1, int(width * SS)), joint="curve")
            return
        on, acc = True, 0.0
        dpx = dash / (self.s / SS)          # dash length in screen px -> units
        for a, b in zip(pts, pts[1:]):
            L = math.dist(a, b)
            pos = 0.0
            while pos < L - 1e-9:
                step = min(L - pos, dpx - acc)
                pa = (a[0] + (b[0] - a[0]) * pos / L, a[1] + (b[1] - a[1]) * pos / L)
                pb = (a[0] + (b[0] - a[0]) * (pos + step) / L, a[1] + (b[1] - a[1]) * (pos + step) / L)
                if on:
                    self.d.line([self.pt(pa), self.pt(pb)], fill=color, width=max(1, int(width * SS)))
                pos += step; acc += step
                if acc >= dpx - 1e-9:
                    acc = 0.0; on = not on

    def handles(self, contours, nodes, color=(70, 110, 200), width=1.0):
        """draw the handles that belong to the given on-curve nodes"""
        xy = flat_xy(contours)
        for a, b, kind, P, idx in segments(contours):
            if kind != "curve":
                continue
            if a in nodes:
                self.line(P[0], P[1], color, width); self.dot(P[1], color, 3.2, hollow=True)
            if b in nodes:
                self.line(P[3], P[2], color, width); self.dot(P[2], color, 3.2, hollow=True)

    def line(self, a, b, color, width=1.0):
        self.d.line([self.pt(a), self.pt(b)], fill=color, width=max(1, int(width * SS)))

    def dot(self, p, color, r=3.0, hollow=False):
        X, Y = self.pt(p); r *= SS
        if hollow:
            self.d.ellipse([X - r, Y - r, X + r, Y + r], outline=color, width=max(1, int(1.2 * SS)), fill=PAPER)
        else:
            self.d.ellipse([X - r, Y - r, X + r, Y + r], fill=color)

    def node(self, p, color=INK, r=3.2):
        X, Y = self.pt(p); r *= SS
        self.d.rectangle([X - r, Y - r, X + r, Y + r], fill=color)

    def ring(self, p, label=None, color=HI, r=9.0, size=15, dx=None, dy=None, width=2.2):
        X, Y = self.pt(p); R = r * SS
        self.d.ellipse([X - R, Y - R, X + R, Y + R], outline=color, width=max(1, int(width * SS)))
        self.d.rectangle([X - 2.4 * SS, Y - 2.4 * SS, X + 2.4 * SS, Y + 2.4 * SS], fill=color)
        if label is not None:
            f = F(CALB, size)
            tx = X + (dx if dx is not None else r + 3) * SS
            ty = Y + (dy if dy is not None else -size * 0.6) * SS
            tw = self.d.textlength(str(label), font=f)
            self.d.rectangle([tx - 2 * SS, ty + 1 * SS, tx + tw + 2 * SS, ty + size * 1.05 * SS], fill=PAPER)
            self.d.text((tx, ty), str(label), fill=color, font=f)

    def label(self, p, text, color=INK, size=13, dx=6, dy=-8, bold=False, bgbox=True):
        X, Y = self.pt(p)
        f = F(CALB if bold else CAL, size)
        tx, ty = X + dx * SS, Y + dy * SS
        if bgbox:
            tw = self.d.textlength(text, font=f)
            self.d.rectangle([tx - 2 * SS, ty, tx + tw + 2 * SS, ty + size * 1.2 * SS], fill=PAPER)
        self.d.text((tx, ty), text, fill=color, font=f)

    def arrow(self, a, b, color=HI, width=2.2, head=9.0, min_px=26.0):
        """arrow from a to b (units); short moves are drawn at least min_px long so they can be seen"""
        A, B = self.pt(a), self.pt(b)
        L = math.dist(A, B)
        if L < 1e-6:
            return
        if L < min_px * SS:
            k = min_px * SS / L
            B = (A[0] + (B[0] - A[0]) * k, A[1] + (B[1] - A[1]) * k)
        self.d.line([A, B], fill=color, width=max(1, int(width * SS)))
        ux, uy = (B[0] - A[0]) / math.dist(A, B), (B[1] - A[1]) / math.dist(A, B)
        h = head * SS
        p1 = (B[0] - ux * h - uy * h * 0.55, B[1] - uy * h + ux * h * 0.55)
        p2 = (B[0] - ux * h + uy * h * 0.55, B[1] - uy * h - ux * h * 0.55)
        self.d.polygon([B, p1, p2], fill=color)

    def tag(self, text, color=INK, size=15):
        """small corner tag (top-left)"""
        f = F(CALB, size)
        self.d.text((10 * SS, 8 * SS), text, fill=color, font=f)

    def image(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def comb(fig, contours, scale, kgain, Lmax, touched=None, width=1.0):
    """curvature comb (curvcomb's colours), drawn on a light Fig"""
    segs, per, _, _ = analyse(contours)
    for si, (s, p) in enumerate(zip(segs, per)):
        if p is None:
            continue
        on = True if touched is None else touched[si]
        tips = []
        for k, B, n in zip(p["k"], p["B"], p["n"]):
            if np.isnan(k):
                continue
            L = min(Lmax, kgain * abs(k))
            tip = (B[0] - np.sign(k) * n[0] * L, B[1] - np.sign(k) * n[1] * L)
            col = kcol(abs(k), scale) if on else (175, 175, 175)
            col = tuple(int(c * 0.85) for c in col)
            fig.d.line([fig.pt(B), fig.pt(tip)], fill=col, width=max(1, int(0.8 * width * SS)))
            tips.append((tip, col))
        for (a, ca), (b, cb) in zip(tips, tips[1:]):
            fig.d.line([fig.pt(a), fig.pt(b)], fill=cb, width=max(1, int(1.5 * width * SS)))


def survey(key, out, w=1100, h=1100):
    """node plot of a drawn glyph, for planning"""
    cs = drawn(key)
    f = Fig(w, h, bbox([cs]))
    f.fill(cs, DIM_FILL, DIM_EDGE)
    for gi, (x, y) in enumerate(flat_xy(cs)):
        t = [n for c in cs for n in c["nodes"]][gi][2]
        if t == "o":
            f.dot((x, y), (90, 130, 210), 2.5, hollow=True)
            f.label((x, y), str(gi), (90, 130, 210), 10, dx=4, dy=-6, bgbox=False)
        else:
            f.node((x, y))
            f.label((x, y), str(gi), INK, 12, dx=5, dy=-2, bgbox=False)
    f.image().save(out)


if __name__ == "__main__":
    od = sys.argv[1]
    os.makedirs(od, exist_ok=True)
    for key in sys.argv[2].split(","):
        from readings import fname
        survey(key, os.path.join(od, fname(key) + "_survey.png"))
