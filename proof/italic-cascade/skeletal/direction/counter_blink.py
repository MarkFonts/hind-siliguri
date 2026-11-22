"""Mark 2026-11-18, on the Bold e-matra bowl and the Latin d of the option 2 proofs: "if we have en exterior comp, we
must have an interior comp. the dq counters rotate the wrong way (or too much)". Process: obliquing.
Found: the build (option 2) turns a round's outside back (9.9% / 18.2%; open outsides 15%) and its counter hardly at
all (3%), so the counter keeps the plain slant's lean inside an outside that was turned back. The 16-17 November proof
(option 3, top_build.py) already gives the counter the outside's amounts (16% / 26%; a counterform bend or run keeps 3%).
This sheet: the same letters both ways, bare ink, blinking, nothing drawn over them.
  VIEW=oblique (default): the build, then the counter taking the outside's amounts
  VIEW=unslanted:         the upright, then the second one with the slant taken back out
Latin letters come from the proofs he has seen (vf_state.pkl, progress_build_2026-11-17.pkl); a letter those do not
hold (Bengali) is built here by the same two calls.
  python counter_blink.py [letters, default dqbpoণএ]"""
import os, sys, json, pickle, skia
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE)
if HERE not in sys.path: sys.path.insert(0, HERE)
import trusted as TR
import cand, cascade as C, stored as ST          # cand puts the build's folder on the path and makes it the working folder
from l_build import OUT, LOW
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
import siliguri_font as SF
K = .25; Y0 = 253.5; VIEW = os.environ.get("VIEW", "oblique"); MASTERS = os.environ.get("MASTERS", "Bold Light").split(); TEXT = sys.argv[1] if len(sys.argv) > 1 else "dqbpoণএ"
GIVE = os.environ.get("GIVE") == "1"      # GIVE=1: a curve that ends at a corner gives way to the curve it meets (cand.GIVE_WAY_ALL), and no size cut is the usual partner (BEND=0)
BEND = float(os.environ.get("BEND", "80")); FRESH = os.environ.get("FRESH") == "1"      # BEND: a counter quarter smaller than this keeps the small amount; FRESH=1 builds every letter here instead of taking the proof's
ST_ = pickle.load(open(os.path.join(SK, "work", "vf_state.pkl"), "rb")); P3 = pickle.load(open(os.path.join(HERE, "progress_build_2026-11-17.pkl"), "rb"))
UNI = json.load(open(os.path.join(SK, "work", "vf_unicode.json")))["uni"]; INV = {u: n for n, us in UNI.items() for u in us}
MIXED = os.environ.get("MIXED") == "1"    # MIXED=1: outside joints are evened by handles only, so the outside's points stay where the curve step put them (cand.MIXED_EVEN)
BASE = os.environ.get("BASE", "build")     # BASE=rule: frame 1 is the counter rule as first sent (no GIVE, no MIXED, size cut 80) instead of the build
SOLVE = os.environ.get("SOLVE", "")       # SOLVE=round: frame 2 is round_solve.round_stored alone; SOLVE=round+cascade: the cascade run on top of it
def with_counters(g, m, plainrule=False):
    if SOLVE and not plainrule:
        import round_solve as RS
        if SOLVE == "round": return RS.round_stored(g)[0]
        keep = C.stored
        try:
            C.stored = RS.round_stored; return C.cascade(g, m)[0]
        finally: C.stored = keep
    """top_build.py's one change, on one outline: outside and counter take the same amounts"""
    keep = (C.stored, C.table_for, cand.BEND)
    try:
        C.stored = cand.stored_axes; cand.BEND = 80.0 if plainrule else BEND; cand.SQUEEZE_SHORT = GIVE and not plainrule; cand.GIVE_WAY_ALL = GIVE and not plainrule; cand.MIXED_EVEN = MIXED and not plainrule; cand.SHARP_CAP = None; cand.INN_RIGID = 0.0
        C.table_for = lambda m_: (lambda c: dict(out=OUT, inn=OUT, inn_run=LOW))
        return C.cascade(g, m)[0]
    finally:
        C.stored, C.table_for, cand.BEND = keep; cand.SQUEEZE_SHORT = False; cand.GIVE_WAY_ALL = False; cand.MIXED_EVEN = False
L = {}; NAMES = []
for m in MASTERS:
    f = TTFont(os.path.join(SF.FORK, "fonts", "otf", "HindSiliguri-%s.otf" % m)); cm = f.getBestCmap(); gs = f.getGlyphSet()
    for ch in TEXT:
        nm = cm[ord(ch)]; bn = INV.get(ord(ch)); held = ST_.get((m, bn))
        if nm not in NAMES: NAMES.append(nm)
        if held and held["final"] and held["g"]["width"] == f["hmtx"][nm][0]:
            g = dict(held["g"]); g.setdefault("glyph", bn); build = held["final"]
        else:
            pen = RecordingPen(); gs[nm].draw(pen); g = dict(glyph=nm, master=m, width=f["hmtx"][nm][0], contours=SF.contours_of(pen.value)); build = C.cascade(g, m, extras=True)[0]
        if BASE == "rule": build = with_counters(g, m, plainrule=True)
        if BASE == "proof": build = P3[m][bn]["final"] if bn in P3[m] else with_counters(g, m, plainrule=True)      # frame 1: the 17 November proof's own letter where it holds one, else the counter rule as sent
        L[(m, nm)] = dict(g=g, build=build, new=P3[m][bn]["final"] if (bn in P3[m] and not FRESH) else with_counters(g, m))
def back(cs): return [dict(closed=c["closed"], nodes=[[n[0] - K * (n[1] - Y0), n[1]] + list(n[2:]) for n in c["nodes"]]) for c in cs]
T1 = os.environ.get("T1", "the build (option 2): the outside is turned back, the counter hardly"); T2 = os.environ.get("T2", "the counter takes the outside's amounts (the rule of option 3)")
FR = {"oblique": [(T1, lambda k: L[k]["build"]), (T2, lambda k: L[k]["new"])],
      "unslanted": [("upright", lambda k: L[k]["g"]["contours"]),
                    ("the counter takes the outside's amounts, slant taken back out", lambda k: back(L[k]["new"]))]}[VIEW]
ys = [p[1] for k in L for c in L[k]["g"]["contours"] for p in c["nodes"]]; top, bot = max(ys) + 40, min(ys) - 40
s = float(os.environ.get("SCALE", ".36")); rh = (top - bot) * s; gap = 40; lean = K * (top - Y0) if VIEW == "oblique" else 0
W = int(50 + max(sum(L[(m, n)]["g"]["width"] + gap for n in NAMES) for m in MASTERS) * s + lean * s + 50); H = int(70 + len(MASTERS) * rh + 20); frames = []
for i, (title, get) in enumerate(FR):
    sf = skia.Surface(W, H); c = sf.getCanvas(); c.clear(skia.ColorWHITE); ink = skia.Paint(Color=skia.ColorBLACK, AntiAlias=True)
    c.drawString("Hind Siliguri, obliquing. %d of %d: %s" % (i + 1, len(FR), title), 30, 40, skia.Font(skia.Typeface("Helvetica"), 24), ink)
    for r, m in enumerate(MASTERS):
        x = 50; base = 70 + r * rh + top * s
        for n in NAMES:
            c.drawPath(TR.path_of(get((m, n)), lambda p, x=x, base=base: (x + s * p[0], base - s * p[1])), ink); x += s * (L[(m, n)]["g"]["width"] + gap)
    frames.append(Image.fromarray(sf.makeImageSnapshot().convert(alphaType=skia.kUnpremul_AlphaType, colorType=skia.kRGBA_8888_ColorType).toarray()[:, :, :3]))
tag = os.environ.get("TAG", "d-q-b-p-o_nna_e")
out = os.path.join(SK, "sheets", "hind-siliguri_counters_%s_%s.gif" % (tag, "build_vs_counter-with-outside" if VIEW == "oblique" else "upright_vs_unslanted")); frames[0].save(out, save_all=True, append_images=frames[1:], duration=1000, loop=0); print(out, W, H)
d = os.environ.get("LOOK_DIR", os.path.join(SK, "work", "look")); os.makedirs(d, exist_ok=True)      # working pictures for checking, not proofs
[fr.save(os.path.join(d, "counter_%s_%s_%d.png" % (tag, VIEW, i))) for i, fr in enumerate(frames)]
