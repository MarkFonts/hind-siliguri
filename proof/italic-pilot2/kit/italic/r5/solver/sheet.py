"""Sheet per glyph x master: drawing + PS numbers | current engine (pixel) chords on its field | rung pairing."""
import sys, os, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rungs import Outline

SS = 2  # supersample
BG, INK, EDGE = (13, 13, 13), (45, 58, 32), (154, 154, 154)
ON, OFF, LBL_ON, LBL_OFF = (232, 232, 232), (91, 143, 217), (232, 184, 74), (111, 160, 230)
MENLO = "/System/Library/Fonts/Menlo.ttc"
CAL = "/Users/Mark/Documents/Github/sans-ui/fonts/ttf/CalSansTextUI-Regular.ttf"


def font(path, size):
    return ImageFont.truetype(path, int(size * SS))


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

    def title(self, text, sub=None):
        self.d.text((16 * SS, 12 * SS), text, fill=LBL_ON, font=font(CAL, 15))
        if sub:
            self.d.text((16 * SS, 32 * SS), sub, fill=(170, 170, 170), font=font(CAL, 12))

    def fill_outline(self, ol, color=INK, edge=EDGE):
        # nonzero fill by drawing outers then counters in BG (good enough for display: counters are inside)
        for pi, poly in enumerate(ol.polys):
            if ol.area[pi] > 0:
                self.d.polygon([self.pt(p) for p in poly], fill=color)
        for pi, poly in enumerate(ol.polys):
            if ol.area[pi] <= 0:
                self.d.polygon([self.pt(p) for p in poly], fill=BG)
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


def sheet(key, G, eng_dir, out_path, PW=700, PH=780):
    g = G[key]
    ol = Outline(g["contours"])
    geo = json.load(open(os.path.join(eng_dir, key + ".json")))
    npz = np.load(os.path.join(eng_dir, key + ".npz"))
    F, prov, mask = npz["F"], npz["prov"], npz["mask"]
    m = geo["master"]
    stems = sorted(m["vstems"] + m["hstems"])
    lo, hi = 0.6 * min(stems), 1.1 * max(stems)
    bb = bbox_of(ol)

    # A: drawing
    A = Panel(PW, PH, bb)
    A.title("/%s %s · drawn" % (g["glyph"], g["master"]), "%d contour%s · %d shape%s (overlapping pieces measured alone) · %d walls" % (
        ol.npaths, "s" if ol.npaths != 1 else "", len(ol.shapes), "s" if len(ol.shapes) != 1 else "", len(ol.walls)))
    A.fill_outline(ol)
    # wall ids: small tick + id at each wall's middle
    for wi, w in enumerate(ol.walls):
        idx = np.where(ol.Wl == wi)[0]
        if not len(idx): continue
        k = idx[len(idx) // 2]
        p, n = ol.P[k], ol.N[k]
        A.text((p[0] - n[0] * 14, p[1] - n[1] * 14), "w%d" % wi, (120, 200, 140), size=8, dx=-6, dy=-5)
    A.nodes(ol)

    # B: current engine field (what Stemperature paints)
    B = Panel(PW, PH, bb)
    B.title("/%s %s · current engine · field" % (g["glyph"], g["master"]),
            "what Stemperature paints (v67 core, pixel) · dim = carried from a neighbour · measured %.0f%%" % (100 * geo["meas"]))
    B.heat(F, prov, mask, geo, lo, hi)
    for pi, poly in enumerate(ol.polys):
        pts = [B.pt(p) for p in poly] + [B.pt(poly[0])]
        B.d.line(pts, fill=EDGE, width=max(1, int(0.8 * SS)))
    B.nodes(ol, labels=False)
    B.legend(lo, hi, stems)

    # C: current engine pairing (sample -> partner chords)
    C0 = Panel(PW, PH, bb)
    npair = sum(int((np.array(part["partner"]) >= 0).sum()) for part in geo["chords"])
    ntot = sum(len(part["P"]) for part in geo["chords"])
    C0.title("/%s %s · current engine · pairing" % (g["glyph"], g["master"]),
             "every 4th sample→partner chord, coloured by its width · %d of %d samples paired · grey dots = unpaired" % (npair, ntot))
    C0.fill_outline(ol)
    for part in geo["chords"]:
        P = np.array(part["P"]); partner = np.array(part["partner"]); width = np.array(part["width"])
        for i in range(0, len(P), 4):
            j = partner[i]
            if j < 0:
                C0.dot(P[i], (110, 110, 110), 1.1); continue
            w = width[i]
            C0.line(P[i], P[j], ramp(w if w > 0 else None, lo, hi), 0.9)
    C0.nodes(ol, labels=False)
    C0.legend(lo, hi, stems)

    # D: rungs
    C = Panel(PW, PH, bb)
    ol.pair_all(); strokes = ol.strokes()
    nr = ol.node_readings()
    nok = sum(1 for r in ol.readings if r and r["status"] == "ok")
    ncorner = sum(1 for r in ol.readings if r and r["status"] == "corner")
    nser = len(ol.serifs)
    C.title("/%s %s · rung pairing (bezier, no raster)" % (g["glyph"], g["master"]),
            "largest circle tangent at each point · %d wedge serif%s HELD (blue edges, rule 8) · grey tick = corner (rule 5) · blue tick = side-on · brown tick = rests on the far wall's end corner (cap, carried) · magenta = crossing" % (nser, "" if nser == 1 else "s"))
    C.fill_outline(ol)
    held_edges(C, ol)
    for r in ol.readings:
        if r is None: continue
        k, j = r["k"], r["j"]
        if r["status"] == "serif":
            continue
        if r["status"] in ("corner", "oblique", "end"):
            if k % 4 == 0:
                p = ol.P[k]; n = ol.N[k]
                C.line(p, (p[0] + n[0] * 6, p[1] + n[1] * 6), {"corner": (120, 120, 120), "oblique": (90, 120, 170), "end": (170, 120, 60)}[r["status"]], 0.8)
            continue
        if k % 6 == 0:
            col = ramp(r["w"], lo, hi)
            col = tuple(int(c * 0.75) for c in col)
            if r.get("cross"):
                col = (200, 90, 220)
            C.line(ol.P[k], ol.P[j], col, 0.7)
            C.dot(r["c"], (225, 225, 225), 0.8)
    for gi, cands in nr.items():
        for side, r in cands:
            if r["status"] != "ok":
                continue
            p, q = ol.P[r["k"]], ol.P[r["j"]]
            col = ramp(r["w"], lo, hi)
            if r.get("cross"):
                col = (220, 110, 240)
            C.line(p, q, col, 2.2)
            C.dot(r["c"], (255, 255, 255), 1.5)
            pn = ol.nearest_node(q)
            if pn is None:
                X, Y = C.pt(q); rr = 2.4 * SS
                C.d.ellipse([X - rr, Y - rr, X + rr, Y + rr], outline=(255, 255, 255), width=SS)
            C.text(r["c"], "%.0f" % r["w"], col, size=8, dx=3, dy=-10)
    C.nodes(ol)
    C.legend(lo, hi, stems)

    W = PW * 4 + 30
    sheet = Image.new("RGB", (W, PH), BG)
    for i, Pn in enumerate((A, B, C0, C)):
        sheet.paste(Pn.out(), (i * (PW + 10), 0))
    sheet.save(out_path)
    return strokes, nr, ol


if __name__ == "__main__":
    src, eng_dir, outdir = sys.argv[1:4]
    G = json.load(open(src))
    os.makedirs(outdir, exist_ok=True)
    for key in sys.argv[4].split(","):
        strokes, nr, ol = sheet(key, G, eng_dir, os.path.join(outdir, key + ".png"))
        print(key, "walls", len(ol.walls), "strokes:", [(s["walls"], s["n"], sum(1 for r in s["rungs"] if r.get("cross"))) for s in strokes[:12]])
