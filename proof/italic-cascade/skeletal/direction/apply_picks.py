"""Apply a pasted node-picker list to the letters, exactly as given, and blink the result (Mark 2026-11-20, first list:
"a: 0 1 2@6,19 19@6,29 20@2,9 21 22 28@32,0 31@49,0 37", then "id like not ALL the a points to skew and rotate").
Process: obliquing.
  index            hold that point where the plain slant puts it
  index@dx,dy      move that point dx across and dy up, in font units, from where it is drawn (round_all.pkl)
Nothing else is touched: no neighbouring handle follows, no joint is evened. What he picked is what he sees.
  python apply_picks.py <picks.txt> [Light|Bold]  -> direction/picks_applied_<master>.pkl and a blink in sheets/"""
import os, re, sys, pickle, copy, skia
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE)
if HERE not in sys.path: sys.path.insert(0, HERE)
import trusted as TR
PICKS = os.path.abspath(sys.argv[1]); m = sys.argv[2] if len(sys.argv) > 2 else "Light"
St = pickle.load(open(os.path.join(SK, "work", "vf_state.pkl"), "rb")); RA = pickle.load(open(os.path.join(HERE, os.environ.get("PKL", "round_all.pkl")), "rb"))


def read(path):
    out = {}
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"): continue
        name, rest = line.split(":", 1); d = {}
        for tok in rest.split():
            mm = re.fullmatch(r"(\d+)(?:@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?))?", tok)
            if not mm: sys.exit("cannot read %r in %r" % (tok, line))
            d[int(mm.group(1))] = (float(mm.group(2)), float(mm.group(3))) if mm.group(2) else None
        out[name.strip()] = d
    return out


def apply(name, picks):
    fin = copy.deepcopy(RA[m][name]["final"]); pla = St[(m, name)]["plain"]; i = 0; n_all = sum(len(c["nodes"]) for c in fin)
    bad = [k for k in picks if k >= n_all]
    if bad: sys.exit("%s has %d points; no point %s" % (name, n_all, bad))
    for c, p in zip(fin, pla):
        for n, q in zip(c["nodes"], p["nodes"]):
            if i in picks:
                if picks[i] is None: n[0], n[1] = q[0], q[1]
                else: n[0], n[1] = n[0] + picks[i][0], n[1] + picks[i][1]
            i += 1
    return fin


P = read(PICKS); NEW = {name: apply(name, d) for name, d in P.items()}
pickle.dump({m: {k: dict(final=v) for k, v in NEW.items()}}, open(os.path.join(HERE, "picks_applied_%s.pkl" % m.lower()), "wb"))
WORD = os.environ.get("WORD", "handgloves"); big = list(P.keys()); s1 = float(os.environ.get("BIG", ".9")); s2 = .3
get = [lambda n: RA[m][n]["final"], lambda n: NEW.get(n, RA[m][n]["final"])]
top, bot = 760, -260; W = int(max(60 + sum(St[(m, n)]["g"]["width"] + 40 for n in big) * s1, 60 + sum(St[(m, n)]["g"]["width"] for n in WORD) * s2) + 80); H = int(60 + (top - bot) * s1 + (top - bot) * s2 + 20); frames = []
for i, title in enumerate(("as drawn (the round solve with your notes)", "your picks applied exactly: holds on the plain slant, moves as given")):
    sf = skia.Surface(W, H); c = sf.getCanvas(); c.clear(skia.ColorWHITE); ink = skia.Paint(Color=skia.ColorBLACK, AntiAlias=True)
    c.drawString("Hind Siliguri %s, obliquing. %d of 2: %s" % (m, i + 1, title), 30, 36, skia.Font(skia.Typeface("Helvetica"), 22), ink)
    x = 40; base = 60 + top * s1
    for n in big:
        c.drawPath(TR.path_of(get[i](n), lambda p, x=x, base=base: (x + s1 * p[0], base - s1 * p[1])), ink); x += s1 * (St[(m, n)]["g"]["width"] + 40)
    x = 40; base = 60 + (top - bot) * s1 + top * s2
    for n in WORD:
        c.drawPath(TR.path_of(get[i](n), lambda p, x=x, base=base: (x + s2 * p[0], base - s2 * p[1])), ink); x += s2 * St[(m, n)]["g"]["width"]
    frames.append(Image.fromarray(sf.makeImageSnapshot().convert(alphaType=skia.kUnpremul_AlphaType, colorType=skia.kRGBA_8888_ColorType).toarray()[:, :, :3]))
tag = os.path.splitext(os.path.basename(PICKS))[0]
out = os.path.join(SK, "sheets", "hind-siliguri_%s_%s_as-drawn_vs_your-picks.gif" % (tag, "-".join(big))); frames[0].save(out, save_all=True, append_images=frames[1:], duration=1000, loop=0); print(out, W, H)
D = os.environ.get("LOOK_DIR", os.path.join(SK, "work", "look")); os.makedirs(D, exist_ok=True)      # working pictures for checking, not proofs
[fr.save(os.path.join(D, "picks_%s_%d.png" % (m, k))) for k, fr in enumerate(frames)]
