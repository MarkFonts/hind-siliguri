"""Mark 2026-11-18, on the Bold pa and e of the Siliguri oblique proof: "can you show me the geomteric transformations
for these? show me the un-skewed versions of the compensations on top of the uprights?" Process: obliquing.
Two frames, bare ink, blinking, nothing drawn over the letters: the upright, then the build's letter with the slant
taken back out (x - K (y - y0)), so whatever moves between the frames is what the build did beyond the slant.
AMP=n multiplies that difference n times (a second sheet, labelled as exaggerated, for seeing where it acts).
  python unskew_blink.py [letters, default ণএ]"""
import os, sys, json, pickle, skia
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE)
if HERE not in sys.path: sys.path.insert(0, HERE)
import trusted as TR
K = .25; Y0 = 253.5; AMP = float(os.environ.get("AMP", "1")); MASTERS = os.environ.get("MASTERS", "Bold Light").split()
TEXT = sys.argv[1] if len(sys.argv) > 1 else "ণএ"
os.chdir(os.path.join(SK, "proofs")); sys.path.insert(0, os.path.join(SK, "proofs"))
from fontTools.ttLib import TTFont
import siliguri_font as SF
from cascade import cascade
FORK = SF.FORK; ST = pickle.load(open(os.path.join(SK, "work", "vf_state.pkl"), "rb")); UNI = json.load(open(os.path.join(SK, "work", "vf_unicode.json")))["uni"]; INV = {u: n for n, us in UNI.items() for u in us}
St = {}; NAMES = []
PK = pickle.load(open(os.path.join(HERE, os.environ["PKL"]), "rb")) if os.environ.get("PKL") else None      # PKL=<letters pickle>: frame 2 is that pickle's letter (the working base) instead of the build's
for m in MASTERS:
    f = TTFont(os.path.join(FORK, "fonts", "otf", "HindSiliguri-%s.otf" % m)); cm = f.getBestCmap(); gs = f.getGlyphSet()
    for ch in TEXT:
        nm = cm[ord(ch)]; held = ST.get((m, INV.get(ord(ch))))
        if nm not in NAMES: NAMES.append(nm)
        if held and held["final"] and held["g"]["width"] == f["hmtx"][nm][0]:      # the build holds it: its own upright and its own outline
            bn = INV.get(ord(ch)); St[(m, nm)] = dict(g=held["g"], final=PK[m][bn]["final"] if (PK and bn in PK[m]) else held["final"], steps=held["log"]["steps"]); continue
        from fontTools.pens.recordingPen import RecordingPen
        pen = RecordingPen(); gs[nm].draw(pen); cs = SF.contours_of(pen.value); g = dict(glyph=nm, master=m, width=f["hmtx"][nm][0], contours=cs)
        cn, lg = cascade(g, m, extras=True); St[(m, nm)] = dict(g=g, final=cn, steps=lg["steps"])      # the same call siliguri_font.py made for this glyph
    print(m, {n: St[(m, n)]["steps"] for n in NAMES})
def back(up, fin):
    out = []
    for cu, cf in zip(up, fin):
        nodes = []
        for a, b in zip(cu["nodes"], cf["nodes"]):
            x = b[0] - K * (b[1] - Y0); nodes.append([a[0] + AMP * (x - a[0]), a[1] + AMP * (b[1] - a[1])] + list(b[2:]))
        out.append(dict(closed=cf["closed"], nodes=nodes))
    return out
FR = [("upright", lambda m, n: St[(m, n)]["g"]["contours"]),
      (os.environ.get("T2", "the build, slant taken back out") + ("" if AMP == 1 else " (difference shown %g times, exaggerated)" % AMP), lambda m, n: back(St[(m, n)]["g"]["contours"], St[(m, n)]["final"]))]
ys = [p[1] for m in MASTERS for n in NAMES for c in St[(m, n)]["g"]["contours"] for p in c["nodes"]]; top, bot = max(ys) + 40, min(ys) - 40
s = float(os.environ.get("SCALE", ".8")); rh = (top - bot) * s; gap = 60
W = int(60 + max(sum(St[(m, n)]["g"]["width"] + gap for n in NAMES) for m in MASTERS) * s + 60); H = int(70 + len(MASTERS) * rh + 20); frames = []
for i, (title, get) in enumerate(FR):
    sf = skia.Surface(W, H); c = sf.getCanvas(); c.clear(skia.ColorWHITE); ink = skia.Paint(Color=skia.ColorBLACK, AntiAlias=True)
    c.drawString("Hind Siliguri, obliquing. %d of %d: %s" % (i + 1, len(FR), title), 30, 40, skia.Font(skia.Typeface("Helvetica"), 24), ink)
    for r, m in enumerate(MASTERS):
        x = 50; base = 70 + r * rh + top * s
        for n in NAMES:
            c.drawPath(TR.path_of(get(m, n), lambda p, x=x, base=base: (x + s * p[0], base - s * p[1])), ink); x += s * (St[(m, n)]["g"]["width"] + gap)
    frames.append(Image.fromarray(sf.makeImageSnapshot().convert(alphaType=skia.kUnpremul_AlphaType, colorType=skia.kRGBA_8888_ColorType).toarray()[:, :, :3]))
tag = "_".join(NAMES) + ("" if AMP == 1 else "_x%g" % AMP)
out = os.path.join(SK, "sheets", os.environ.get("OUTNAME", "hind-siliguri_%s_upright_vs_build-unslanted.gif" % tag)); frames[0].save(out, save_all=True, append_images=frames[1:], duration=900, loop=0); print(out, W, H)
d = os.environ.get("LOOK_DIR", os.path.join(SK, "work", "look")); os.makedirs(d, exist_ok=True)      # working pictures for checking, not proofs
[f.save(os.path.join(d, "unskew_%s_%d.png" % (tag, i))) for i, f in enumerate(frames)]
# for my own reading, not for the sheet: where the ink differs between the two frames
from PIL import ImageChops
ImageChops.difference(frames[0], frames[1]).convert("L").point(lambda v: 255 - min(255, v * 3)).save(os.path.join(d, "unskew_%s_diff.png" % tag))
