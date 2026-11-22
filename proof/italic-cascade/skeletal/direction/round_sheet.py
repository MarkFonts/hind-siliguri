"""Every letter, the build against the round solve (Mark 2026-11-20: "run the round solve on all the letters").
Process: obliquing. Bare ink, two frames blinking, nothing drawn over the letters: 1 the build (option 2), 2 the round
solve with the build's later steps (round_all.pkl). One gif per master and per set.
  python round_sheet.py [Bold|Light ...]     SET=latin (default) | bengali"""
import os, sys, pickle, skia
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE)
if HERE not in sys.path: sys.path.insert(0, HERE)
import trusted as TR
St = pickle.load(open(os.path.join(SK, "work", "vf_state.pkl"), "rb")); RA = pickle.load(open(os.path.join(HERE, os.environ.get("PKL", "round_all.pkl")), "rb"))
SET = os.environ.get("SET", "latin"); s = float(os.environ.get("SCALE", ".2"))
FIG = "zero one two three four five six seven eight nine".split()
if os.environ.get("ROWS"): ROWS = [r.split() for r in os.environ["ROWS"].split("|")]
elif SET == "latin": ROWS = [list("abcdefghijklm"), list("nopqrstuvwxyz"), list("ABCDEFGHIJKLM"), list("NOPQRSTUVWXYZ"), FIG]
else:
    bn = sorted(k[1] for k in St if k[0] == "Bold" and k[1].startswith("bn")); ROWS = [bn[i:i + 13] for i in range(0, len(bn), 13)]
D = os.environ.get("LOOK_DIR", os.path.join(SK, "work", "look")); os.makedirs(D, exist_ok=True)      # working pictures for checking, not proofs
for m in (sys.argv[1:] or ["Bold", "Light"]):
    FR = [("the build (option 2)", lambda n: St[(m, n)]["final"]), ("the round solve, every letter", lambda n: RA[m][n]["final"])]
    if os.environ.get("FRAME1"):      # FRAME1=<pickle>: blink an earlier run of the round solve against this one
        F1 = pickle.load(open(os.path.join(HERE, os.environ["FRAME1"]), "rb")); FR = [(os.environ.get("T1", "the round solve as sent"), lambda n: F1[m][n]["final"]), (os.environ.get("T2", "with the notes"), lambda n: RA[m][n]["final"])]
    if os.environ.get("FRAMES"):      # FRAMES="a.pkl|title;b.pkl|title;...": any number of frames, each a letters pickle in this folder
        FR = []
        for item in os.environ["FRAMES"].split(";"):
            pk, title = item.split("|", 1); Dd = pickle.load(open(os.path.join(HERE, pk), "rb")); FR.append((title, lambda n, Dd=Dd: Dd[m][n]["final"]))
    top, bot = 760, -260; rh = (top - bot) * s; W = int(60 + max(sum(St[(m, n)]["g"]["width"] for n in r) for r in ROWS) * s + 80); H = int(60 + len(ROWS) * rh + 10); frames = []
    for i, (title, get) in enumerate(FR):
        sf = skia.Surface(W, H); c = sf.getCanvas(); c.clear(skia.ColorWHITE); ink = skia.Paint(Color=skia.ColorBLACK, AntiAlias=True)
        c.drawString("Hind Siliguri %s, obliquing. %d of %d: %s" % (m, i + 1, len(FR), title), 30, 36, skia.Font(skia.Typeface("Helvetica"), 22), ink)
        for r, row in enumerate(ROWS):
            x = 40; base = 60 + r * rh + top * s
            for n in row:
                c.drawPath(TR.path_of(get(n), lambda p, x=x, base=base: (x + s * p[0], base - s * p[1])), ink); x += s * St[(m, n)]["g"]["width"]
        frames.append(Image.fromarray(sf.makeImageSnapshot().convert(alphaType=skia.kUnpremul_AlphaType, colorType=skia.kRGBA_8888_ColorType).toarray()[:, :, :3]))
    out = os.path.join(SK, "sheets", os.environ.get("OUTNAME", "hind-siliguri_round-solve_all_%s_%%s_build_vs_round-solve.gif" % SET) % m.lower()); frames[0].save(out, save_all=True, append_images=frames[1:], duration=1000, loop=0); print(out, W, H)
    [fr.save(os.path.join(D, "roundall_%s_%s_%d.png" % (SET, m, i))) for i, fr in enumerate(frames)]
