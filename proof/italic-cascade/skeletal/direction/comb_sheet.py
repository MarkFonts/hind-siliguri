"""Curvature combs on the counters, drawn into the counter (Mark 2026-11-21: "how does g2 curves look stacked onto these
pdqgb counterforms? they should extend toward the middle of the counter"). Process: obliquing.
Two frames blinking: bare ink, then the same ink with each counter's comb. A tooth's length is the curve's curvature
there (one scale per weight), pointing into the counter; a step in the comb at a point is a break in G2.
  PKL=<letters.pkl> OUTNAME=<gif> TITLE=<what the letters are> python comb_sheet.py p d q g b"""
import os, sys, pickle, math, numpy as np, skia
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE)
if HERE not in sys.path: sys.path.insert(0, HERE)
import trusted as TR
import cand, stored as ST
St = pickle.load(open(os.path.join(SK, "work", "vf_state.pkl"), "rb")); D = pickle.load(open(os.path.join(HERE, os.environ["PKL"]), "rb"))
NAMES = sys.argv[1:] or list("pdqgb"); MASTERS = os.environ.get("MASTERS", "Light Bold").split(); s = float(os.environ.get("SCALE", ".5")); TEETH = int(os.environ.get("TEETH", "22")); SHARE = float(os.environ.get("SHARE", ".3"))


def area(c):
    P = np.array([[n[0], n[1]] for n in c["nodes"] if n[2] != "o"]); return .5 * float(np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]))


def counters(cs):
    A = [area(c) for c in cs]; big = A[int(np.argmax(np.abs(A)))]
    return [i for i, a in enumerate(A) if a * big < 0]


def comb(c):
    """-> list of (point, signed curvature, inward unit normal) along the contour"""
    out = []; sgn = 1 if area(c) > 0 else -1
    for sg in ST.segments(c):
        if len(sg[1]) != 2: continue
        P = np.array(ST.seg_ctrl(c, sg), float)
        for t in np.linspace(0, 1, TEETH + 1):
            d1 = 3 * ((1 - t) ** 2 * (P[1] - P[0]) + 2 * (1 - t) * t * (P[2] - P[1]) + t * t * (P[3] - P[2])); d2 = 6 * ((1 - t) * (P[2] - 2 * P[1] + P[0]) + t * (P[3] - 2 * P[2] + P[1]))
            sp = max(np.linalg.norm(d1), 1e-9); k = float(d1[0] * d2[1] - d1[1] * d2[0]) / sp ** 3; tn = d1 / sp
            pt = (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t * t * P[2] + t ** 3 * P[3]
            out.append((pt, k * sgn, sgn * np.array([-tn[1], tn[0]])))      # k*sgn > 0: the curve bends round the counter's inside
    return out


top, bot = 760, -260; rh = (top - bot) * s; gap = 60
W = int(60 + max(sum(St[(m, n)]["g"]["width"] + gap for n in NAMES) for m in MASTERS) * s + 120); H = int(60 + len(MASTERS) * rh + 10); frames = []
TITLE = os.environ.get("TITLE", "")
for i, title in enumerate(("bare ink", "curvature combs on the counters, drawn into the counter")):
    sf = skia.Surface(W, H); cv = sf.getCanvas(); cv.clear(skia.ColorWHITE); ink = skia.Paint(Color=skia.ColorBLACK, AntiAlias=True)
    cv.drawString("Hind Siliguri, obliquing. %s. %d of 2: %s" % (TITLE, i + 1, title), 30, 36, skia.Font(skia.Typeface("Helvetica"), 22), ink)
    for r, m in enumerate(MASTERS):
        x = 40; base = 60 + r * rh + top * s
        # one comb scale per weight: a tooth is SHARE of the radius where the curve is as round as the weight's mean counter
        R = np.mean([math.sqrt(abs(area(D[m][n]["final"][ci])) / math.pi) for n in NAMES for ci in counters(D[m][n]["final"])]); Cc = SHARE * R * R
        for n in NAMES:
            fin = D[m][n]["final"]; to = lambda p, x=x, base=base: (x + s * p[0], base - s * p[1])
            cv.drawPath(TR.path_of(fin, to), ink)
            if i == 1:
                pen = skia.Paint(Color=skia.Color(120, 120, 120), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.2)
                for ci in counters(fin):
                    cm = comb(fin[ci]); tips = []
                    for pt, k, nrm in cm:
                        tip = pt + nrm * Cc * k; a, b = to(pt), to(tip); cv.drawLine(a[0], a[1], b[0], b[1], pen); tips.append(b)
                    path = skia.Path(); path.moveTo(*tips[0])
                    for b in tips[1:]: path.lineTo(*b)
                    path.close(); cv.drawPath(path, pen)
            x += s * (St[(m, n)]["g"]["width"] + gap)
    frames.append(Image.fromarray(sf.makeImageSnapshot().convert(alphaType=skia.kUnpremul_AlphaType, colorType=skia.kRGBA_8888_ColorType).toarray()[:, :, :3]))
out = os.path.join(SK, "sheets", os.environ["OUTNAME"]); frames[0].save(out, save_all=True, append_images=frames[1:], duration=1100, loop=0); print(out, W, H)
d = os.environ.get("LOOK_DIR", os.path.join(SK, "work", "look")); os.makedirs(d, exist_ok=True)      # working pictures for checking, not proofs
[f.save(os.path.join(d, "comb_%s_%d.png" % (os.environ.get("LOOK", "a"), k))) for k, f in enumerate(frames)]
