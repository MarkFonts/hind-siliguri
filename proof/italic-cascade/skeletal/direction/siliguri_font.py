"""Hind Siliguri oblique with the whole Bengali set and its shaping, for a Siliguri text proof (Mark 2026-11-18: "and
siliguri text as pdf?", after asking for option 2, the build). Process: obliquing.
Reads the fork's own built fonts/otf/HindSiliguri-{Light,Bold}.otf (never written to); every glyph's outline is replaced:
  - a glyph the build already holds (work/vf_state.pkl: Latin, figures, punctuation, 49 Bengali letters): the build's outline
  - any other glyph the text uses: run through the same cascade (cascade(g, m, extras=True)), from the OTF's outline
  - everything else, and any glyph the cascade cannot take: the plain slant
Mark and cursive anchors take the same slant, so marks sit where they sat. Shaping tables are kept as they are.
Writes skeletal/out/siliguri_option-2/HindSiliguriOblique-<Master>.otf and a report of which glyph took which path.
  python siliguri_font.py Light|Bold [glyph names file, one per line: the glyphs to cascade]"""
import os, sys, json, math, pickle, time, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE); SP = os.path.dirname(SK); FORK = os.path.dirname(os.path.dirname(SP))
sys.path.insert(0, os.path.join(SK, "proofs"))
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
K = .25; Y0 = 253.5; ROUND = os.environ.get("SOLVE") == "round"; OUT = os.path.join(SK, "out", "siliguri_" + os.environ.get("TAG", "round-solve" if ROUND else "option-2"))      # SOLVE=round: every glyph by round_all.solve (the round solve + the build's later steps)
def contours_of(ops):
    """pen ops -> the build's contour format: nodes [x, y, type, smooth] in Glyphs order (the start point is the last node)"""
    out = []; cur = None
    for op, a in ops:
        if op == "moveTo": cur = dict(start=a[0], segs=[])
        elif op == "lineTo": cur["segs"].append(("l", [a[0]]))
        elif op == "curveTo": cur["segs"].append(("c", list(a)))
        elif op in ("closePath", "endPath"):
            if cur is None: continue
            S = cur["segs"]; st = cur["start"]
            if not S: cur = None; continue
            if S[-1][1][-1] != st: S.append(("l", [st]))
            S = [s for i, s in enumerate(S) if not (s[0] == "l" and s[1][0] == (S[i - 1][1][-1] if i else st))]   # no zero-length lines
            nodes = []
            for t, pts in S:
                if t == "l": nodes.append([float(pts[0][0]), float(pts[0][1]), "l", False])
                else: nodes += [[float(pts[0][0]), float(pts[0][1]), "o", False], [float(pts[1][0]), float(pts[1][1]), "o", False], [float(pts[2][0]), float(pts[2][1]), "c", False]]
            n = len(nodes)
            for i, nd in enumerate(nodes):
                if nd[2] == "o": continue
                p, q = nodes[i - 1], nodes[(i + 1) % n]
                if p[2] != "o" and q[2] != "o": continue
                a_ = (nd[0] - p[0], nd[1] - p[1]); b_ = (q[0] - nd[0], q[1] - nd[1]); la, lb = math.hypot(*a_), math.hypot(*b_)
                if la > 0 and lb > 0 and (a_[0] * b_[0] + a_[1] * b_[1]) / (la * lb) > .9986: nd[3] = True
            if len([x for x in nodes if x[2] != "o"]) >= 2: out.append(dict(closed=True, nodes=nodes))
            cur = None
    return out
def plain(cs): return [dict(closed=c["closed"], nodes=[[n[0] + K * (n[1] - Y0), n[1]] + list(n[2:]) for n in c["nodes"]]) for c in cs]
def draw(cs, pen):
    for c in cs:
        N = c["nodes"]; pen.moveTo((N[-1][0], N[-1][1])); i = 0
        while i < len(N):
            if N[i][2] == "o": pen.curveTo((N[i][0], N[i][1]), (N[i + 1][0], N[i + 1][1]), (N[i + 2][0], N[i + 2][1])); i += 3
            else: pen.lineTo((N[i][0], N[i][1])); i += 1
        pen.closePath()
def roman(f):
    gs = f.getGlyphSet(); R = {}
    for nm in f.getGlyphOrder():
        p = RecordingPen(); gs[nm].draw(p); R[nm] = contours_of(p.value)
    return R
if __name__ == "__main__":
    m = sys.argv[1]; want = set(open(os.path.abspath(sys.argv[2])).read().split()) if len(sys.argv) > 2 else None
    os.chdir(os.path.join(SK, "proofs"))      # the build's modules read their neighbours by relative path
    from state import shear, HIND_K, HIND_Y0
    from cascade import cascade
    assert (HIND_K, HIND_Y0) == (K, Y0)
    St = pickle.load(open(os.path.join(SK, "work", "vf_state.pkl"), "rb")); UNI = json.load(open(os.path.join(SK, "work", "vf_unicode.json")))["uni"]
    f = TTFont(os.path.join(FORK, "fonts", "otf", "HindSiliguri-%s.otf" % m)); cm = f.getBestCmap(); R = roman(f); os.makedirs(OUT, exist_ok=True)
    held = {}
    if ROUND:
        if HERE not in sys.path: sys.path.insert(0, HERE)
        import round_all as RALL
        RA = pickle.load(open(os.path.join(HERE, "round_all.pkl"), "rb"))
    for (mm, nm), st in St.items():
        if mm != m or not st["final"]: continue
        for u in UNI.get(nm, []):
            if u in cm and f["hmtx"][cm[u]][0] == st["g"]["width"]: held[cm[u]] = RA[m][nm]["final"] if ROUND else st["final"]
    New = {}; how = {}; t0 = time.time()
    for nm, cs in R.items():
        if not cs: how[nm] = "empty"; continue
        if nm in held: New[nm] = held[nm]; how[nm] = "build"; continue
        if want is not None and nm not in want: New[nm] = plain(cs); how[nm] = "plain slant (not in the text)"; continue
        try:
            g = dict(glyph=nm, master=m, width=f["hmtx"][nm][0], contours=cs)
            if ROUND:
                cn, how_, steps_ = RALL.solve(g, m)
                if cn is None: raise ValueError(how_)
                lg = dict(steps=[how_.split(" (")[0]] + list(steps_))
            else: cn, lg = cascade(g, m, extras=True)
            ok = len(cn) == len(cs) and all(len(a["nodes"]) == len(b["nodes"]) and all(math.isfinite(x[0]) and math.isfinite(x[1]) for x in a["nodes"]) for a, b in zip(cn, cs))
            if not ok: raise ValueError("structure changed")
            New[nm] = cn; how[nm] = "cascade: " + "+".join(lg["steps"])
        except Exception as ex:
            New[nm] = plain(cs); how[nm] = "plain slant (cascade could not take it: %s)" % (str(ex)[:60])
    print(m, "glyphs", len(R), "in %.0fs" % (time.time() - t0))
    cff = f["CFF "].cff; td = cff.topDictIndex[0]; CS = td.CharStrings; nom = getattr(td.Private, "nominalWidthX", 0); dfl = getattr(td.Private, "defaultWidthX", 0)
    for nm, cs in New.items():
        w = f["hmtx"][nm][0]; pen = T2CharStringPen(None if w == dfl else w - nom, None); draw(cs, pen); CS[nm] = pen.getCharString(private=td.Private, globalSubrs=cff.GlobalSubrs)
    seen = set(); na = 0
    def walk(o):
        global na
        if id(o) in seen or o is None or isinstance(o, (int, float, str, bytes)): return
        seen.add(id(o))
        if isinstance(o, (list, tuple)):
            for x in o: walk(x)
            return
        if hasattr(o, "XCoordinate") and hasattr(o, "YCoordinate") and type(o).__name__ == "Anchor":
            o.XCoordinate = int(round(o.XCoordinate + K * (o.YCoordinate - Y0))); na += 1; return
        if hasattr(o, "__dict__"):
            for v in vars(o).values(): walk(v)
    walk(f["GPOS"].table.LookupList)
    f["post"].italicAngle = -14.0362; f["head"].macStyle |= 2; f["OS/2"].fsSelection = (f["OS/2"].fsSelection | 1) & ~64; f["hhea"].caretSlopeRise = 1000; f["hhea"].caretSlopeRun = 250
    fam = "Hind Siliguri Oblique Proof"
    for rec in f["name"].names:
        if rec.nameID in (1, 16): rec.string = fam
        elif rec.nameID == 4: rec.string = "%s %s" % (fam, m)
        elif rec.nameID == 6: rec.string = "HindSiliguriObliqueProof-%s" % m
        elif rec.nameID == 3: rec.string = "proof;HindSiliguriObliqueProof-%s" % m
    out = os.path.join(OUT, "HindSiliguriOblique-%s.otf" % m); f.save(out)
    json.dump(how, open(os.path.join(OUT, "how_%s.json" % m), "w"), indent=0)
    from collections import Counter
    C_ = Counter(v.split(":")[0].split(" (")[0] if not v.startswith("plain slant (cascade") else "plain slant, cascade failed" for v in how.values()); print(dict(C_), "| anchors slanted", na, "|", out)
