# One-time, 2026-10-26: GF Latin Core in masters/HindSiliguri.glyphs, everything except the three
# glyphs drawn by hand (Hbar, hbar, Germandbls):
#   16 composites, dotless j, 14 combining marks, top/bottom/ogonek anchors on the base letters
#   and the dotted circle, a dotless i-ogonek, a ccmp rule for dotless i and j before marks above,
#   and the GlyphOrderAndAliasDB entries.
# All geometry comes from the font's own accented letters. Applied as text, so the rest of the
# file stays byte-identical. Kept as a record.

import statistics
import glyphsLib

SRC = "masters/HindSiliguri.glyphs"
LIGHT = "D864283E-EAB4-426F-8533-332F2D658CBA"
BOLD = "731EBDE8-0F2D-4E32-814F-AAFC41A14D25"
MASTERS = {LIGHT: "Light", BOLD: "Bold"}

TOP = ["grave", "acute", "circumflex", "tilde", "macron", "breve", "dotaccent", "dieresis", "ring", "hungarumlaut", "caron"]
UNBIASED = {"circumflex", "dieresis", "caron", "macron", "breve", "dotaccent", "ring", "tilde"}
COMBINING = [  # name, unicode, source accent, anchor
    ("gravecomb", "0300", "grave", "top"), ("acutecomb", "0301", "acute", "top"),
    ("circumflexcomb", "0302", "circumflex", "top"), ("tildecomb", "0303", "tilde", "top"),
    ("macroncomb", "0304", "macron", "top"), ("brevecomb", "0306", "breve", "top"),
    ("dotaccentcomb", "0307", "dotaccent", "top"), ("dieresiscomb", "0308", "dieresis", "top"),
    ("ringcomb", "030A", "ring", "top"), ("hungarumlautcomb", "030B", "hungarumlaut", "top"),
    ("caroncomb", "030C", "caron", "top"), ("cedillacomb", "0327", "cedilla", "bottom"),
    ("ogonekcomb", "0328", "ogonek", "ogonek"),
]
COMPOSITES = [  # name, unicode, base, accent
    ("Cdotaccent", "010A", "C", "dotaccent"), ("cdotaccent", "010B", "c", "dotaccent"),
    ("Gdotaccent", "0120", "G", "dotaccent"), ("gdotaccent", "0121", "g", "dotaccent"),
    ("Wcircumflex", "0174", "W", "circumflex"), ("wcircumflex", "0175", "w", "circumflex"),
    ("Ycircumflex", "0176", "Y", "circumflex"), ("ycircumflex", "0177", "y", "circumflex"),
    ("Wgrave", "1E80", "W", "grave"), ("wgrave", "1E81", "w", "grave"),
    ("Wacute", "1E82", "W", "acute"), ("wacute", "1E83", "w", "acute"),
    ("Wdieresis", "1E84", "W", "dieresis"), ("wdieresis", "1E85", "w", "dieresis"),
    ("Ygrave", "1EF2", "Y", "grave"), ("ygrave", "1EF3", "y", "grave"),
]
BASES = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + [chr(c) for c in range(ord("a"), ord("z") + 1)] + ["dotlessi", "dotlessj"]
OGONEK_BASES = ["A", "a", "E", "e", "I", "i", "U", "u"]

font = glyphsLib.GSFont(SRC)
lines = open(SRC, encoding="utf-8").read().split("\n")

# --- geometry -------------------------------------------------------------------------------------

def layer(name, mid):
    return next(l for l in font.glyphs[name].layers if l.layerId == mid)

def outline_points(l):
    """Points of a layer's own paths and decomposed components, in layer coordinates."""
    pts = [(n.position.x, n.position.y) for p in l.paths for n in p.nodes]
    for c in l.components:
        t = c.transform
        for x, y in outline_points(layer(c.name, l.layerId)):
            pts.append((t[0] * x + t[2] * y + t[4], t[1] * x + t[3] * y + t[5]))
    return pts

def bbox(name, mid):
    pts = outline_points(layer(name, mid))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)

def cx(name, mid):
    b = bbox(name, mid)
    return (b[0] + b[2]) / 2

def master(mid):
    return next(m for m in font.masters if m.id == mid)

def accented(mid):
    """(glyph, base, accent, dx, dy) for every base + accent composite. A mixed glyph whose path is
    the dotless stem (igrave etc.) counts as a composite of dotlessi."""
    out = []
    for g in font.glyphs:
        l = next((l for l in g.layers if l.layerId == mid), None)
        if l is None:
            continue
        comps = l.components
        if len(comps) == 2 and not l.paths and tuple(comps[0].transform[4:]) == (0, 0):
            out.append((g.name, comps[0].name, comps[1].name, comps[1].transform[4], comps[1].transform[5]))
        elif len(comps) == 1 and len(l.paths) == 1 and g.name[0] == "i" and comps[0].name in TOP:
            out.append((g.name, "dotlessi", comps[0].name, comps[0].transform[4], comps[0].transform[5]))
    return out

def stem_points(name, mid):
    """Outline points; for dotlessj, j's points without the dot (which doesn't exist yet)."""
    if name == "dotlessj":
        l = layer("j", mid)
        xh = master(mid).xHeight
        return [(n.position.x, n.position.y) for p in l.paths if min(n.position.y for n in p.nodes) < xh for n in p.nodes]
    return outline_points(layer(name, mid))

def top_band_center(name, mid):
    pts = stem_points(name, mid)
    top = max(p[1] for p in pts)
    band = [p[0] for p in pts if p[1] >= top - 100]
    return (min(band) + max(band)) / 2, top

geo = {}
for mid in MASTERS:
    m = master(mid)
    xh, cap = m.xHeight, m.capHeight
    comps = accented(mid)
    center = {}  # base -> accent center, from symmetric accents
    for _, base, acc, dx, dy in comps:
        if acc in UNBIASED:
            center.setdefault(base, []).append(dx + cx(acc, mid))
    center = {k: statistics.median(v) for k, v in center.items()}
    bias, rise = {}, {}
    for _, base, acc, dx, dy in comps:
        case = "uc" if base[0].isupper() else "lc"
        rise.setdefault((acc, case), []).append(dy)
        if base in center and acc in TOP:
            bias.setdefault((acc, case), []).append(dx + cx(acc, mid) - center[base])
    bias = {k: statistics.median(v) for k, v in bias.items()}
    rise = {k: statistics.median(v) for k, v in rise.items()}
    # Each top accent's attachment height in its own coordinates: lowercase composites put it at x-height.
    a_y = {a: xh - rise[(a, "lc")] for a in TOP if (a, "lc") in rise}

    anchors = {}
    for b in BASES:
        case = "uc" if b[0].isupper() else "lc"
        mine = [(acc, dx, dy) for _, base, acc, dx, dy in comps if base == b and acc in TOP and acc in a_y]
        # Symmetric accents say where the letter's center is; acute and grave only after removing their lean.
        if any(acc in UNBIASED for acc, dx, dy in mine):
            mine = [m for m in mine if m[0] in UNBIASED]
        if mine:
            x = statistics.median(dx + cx(acc, mid) - bias.get((acc, case), 0) for acc, dx, dy in mine)
            y = statistics.median(dy + a_y[acc] for acc, dx, dy in mine)
        else:
            x, top = top_band_center(b, mid)
            y = cap if case == "uc" else (top if top > xh + 60 else xh)
        ced = [(dx, dy) for _, base, acc, dx, dy in comps if base == b and acc == "cedilla"]
        sx = [p[0] for p in stem_points(b, mid)]
        bx = (ced[0][0] + cx("cedilla", mid)) if ced else (min(sx) + max(sx)) / 2
        a = {"top": (x, y), "bottom": (bx, 0)}
        if b in OGONEK_BASES:
            og = [(dx, dy) for _, base, acc, dx, dy in comps if base == b and acc == "ogonek"]
            if og:
                a["ogonek"] = (og[0][0] + cx("ogonek", mid), og[0][1])
            else:  # drawn Aogonek/aogonek: center the ogonek on its hook, the part below the baseline
                hook = [p[0] for p in outline_points(layer(b + "ogonek", mid)) if p[1] < -10]
                a["ogonek"] = ((min(hook) + max(hook)) / 2, 0)
        anchors[b] = a

    # Composite placements: base anchor minus the accent's own attachment point.
    place = {}
    for name, uni, base, acc in COMPOSITES:
        case = "uc" if base[0].isupper() else "lc"
        bx, by = anchors[base]["top"]
        place[name] = (round(bx + bias.get((acc, case), 0) - cx(acc, mid)), round(by - a_y[acc]))

    # Combining marks: the spacing accent shifted to sit over a lowercase o, plus the matching anchor.
    o_w = layer("o", mid).width
    marks = {}
    for name, uni, acc, kind in COMBINING:
        ox = round(-o_w / 2 - cx(acc, mid))
        if kind == "top":
            oy = round(rise[(acc, "lc")])
            anchor = ("_top", round(ox + cx(acc, mid) - bias.get((acc, "lc"), 0)), round(oy + a_y[acc]))
        elif kind == "bottom":
            oy = 0
            anchor = ("_bottom", round(ox + cx(acc, mid)), 0)
        else:
            oy = 0
            anchor = ("_ogonek", round(ox + cx(acc, mid)), 0)
        marks[name] = ((ox, oy), anchor)

    geo[mid] = {"anchors": anchors, "place": place, "marks": marks, "o_w": o_w, "xh": xh}

# --- text editing -----------------------------------------------------------------------------------

def delta(s):
    return 0 if s.startswith('"') else s.count("{") + s.count("(") - s.count("}") - s.count(")")

def block_end(i):
    depth, j = 0, i
    while True:
        depth += delta(lines[j])
        if depth == 0:
            return j
        j += 1

def children(a, b):
    out, k = [], a + 1
    while k < b:
        if lines[k] == "{":
            e = block_end(k)
            out.append((k, e))
            k = e + 1
        else:
            k += 1
    return out

def key_at_depth1(a, b, key):
    depth = 0
    for k in range(a, b + 1):
        if depth == 1 and (lines[k] == key or lines[k].startswith(key)):
            return k
        depth += delta(lines[k])
    return None

def glyph_range(name):
    i = lines.index("glyphname = %s;" % name)
    while lines[i] != "{":
        i -= 1
    return i, block_end(i)

def layer_range(glyph, mid):
    a, b = glyph_range(glyph)
    la = key_at_depth1(a, b, "layers = (")
    for s, e in children(la, block_end(la)):
        k = key_at_depth1(s, e, "layerId = ")
        if k is not None and lines[k] == 'layerId = "%s";' % mid:
            return s, e
    raise KeyError((glyph, mid))

def anchors_text(items):
    return ["anchors = ("] + [",\n".join('{\nname = %s;\nposition = "{%d, %d}";\n}' % (n, round(x), round(y)) for n, x, y in items)] + [");"]

def path_texts(glyph, mid, keep):
    """Raw text of the layer's own path dicts at the given indexes."""
    a, b = layer_range(glyph, mid)
    p = key_at_depth1(a, b, "paths = (")
    out = []
    for i, (s, e) in enumerate(children(p, block_end(p))):
        if i in keep:
            out.append("\n".join(lines[s:e] + ["}"]))
    return out

def shift_path(text, dx, dy):
    out = []
    for s in text.split("\n"):
        if s.startswith('"'):
            body = s.rstrip(",").strip('"').split()
            body[0], body[1] = str(round(float(body[0]) + dx)), str(round(float(body[1]) + dy))
            s = '"%s"' % " ".join(body) + ("," if s.endswith(",") else "")
        out.append(s)
    return "\n".join(out)

# 1. Anchors on the base letters (none of them has anchors yet). dotlessj is new; see below.
for b in BASES[:-1]:
    for mid in MASTERS:
        a, _ = layer_range(b, mid)
        assert key_at_depth1(a, block_end(a), "anchors = (") is None, b
        items = [(k, x, y) for k, (x, y) in sorted(geo[mid]["anchors"][b].items())]
        lines[a + 1:a + 1] = anchors_text(items)

# Dotted circle: it already has the Bangla anchors; add the Latin ones, centered, with marks above
# sitting on its top edge as they do on an o.
for mid in MASTERS:
    a, e = layer_range("dottedcircle", mid)
    k = key_at_depth1(a, e, "anchors = (")
    k_end = block_end(k)
    x0, y0, x1, y1 = bbox("dottedcircle", mid)
    o_top = bbox("o", mid)[3]
    top_y = y1 - (o_top - master(mid).xHeight)
    extra = [("ogonek", (x0 + x1) / 2, 0), ("top", (x0 + x1) / 2, top_y), ("bottom", (x0 + x1) / 2, 0)]
    assert lines[k_end - 1] == "}"
    lines[k_end - 1] = "},"
    lines[k_end:k_end] = [",\n".join('{\nname = %s;\nposition = "{%d, %d}";\n}' % (n, round(x), round(y)) for n, x, y in extra)]

# 2. New glyphs, appended to the glyph list.
def components_text(items):
    parts = []
    for name, t in items:
        if t == (0, 0):
            parts.append("{\nname = %s;\n}" % name)
        else:
            parts.append('{\nname = %s;\ntransform = "{1, 0, 0, 1, %d, %d}";\n}' % (name, t[0], t[1]))
    return ["components = ("] + [",\n".join(parts)] + [");"]

new = []
for name, uni, base, acc in COMPOSITES:
    layers = {}
    for mid in MASTERS:
        layers[mid] = components_text([(base, (0, 0)), (acc, geo[mid]["place"][name])])
    new.append((name, uni, layers, [layer(base, mid).width for mid in (LIGHT, BOLD)], []))

# Dotless i-ogonek, for Lithuanian i-ogonek + accent: iogonek's own ogonek offset on dotlessi.
layers = {}
for mid in MASTERS:
    og = next(c for c in layer("iogonek", mid).components if c.name == "ogonek")
    # Its own anchors (dotlessi's): hindkit doesn't propagate anchors from components.
    items = [(k, x, y) for k, (x, y) in sorted(geo[mid]["anchors"]["dotlessi"].items())]
    layers[mid] = anchors_text(items) + components_text([("dotlessi", (0, 0)), ("ogonek", (round(og.transform[4]), round(og.transform[5])))])
new.append(("iogonek.dotless", None, layers, [layer("iogonek", mid).width for mid in (LIGHT, BOLD)], []))

# Dotless j: j's paths without the dot (the path entirely above x-height).
layers = {}
for mid in MASTERS:
    l = layer("j", mid)
    keep = [i for i, p in enumerate(l.paths) if min(n.position.y for n in p.nodes) < geo[mid]["xh"]]
    items = [(k, x, y) for k, (x, y) in sorted(geo[mid]["anchors"]["dotlessj"].items())]
    layers[mid] = anchors_text(items) + ["paths = ("] + [",\n".join(path_texts("j", mid, keep))] + [");"]
new.append(("dotlessj", "0237", layers, [layer("j", mid).width for mid in (LIGHT, BOLD)], []))

# Combining marks: zero-width components of the spacing accents.
for name, uni, acc, kind in COMBINING:
    layers = {}
    for mid in MASTERS:
        (ox, oy), (an, ax, ay) = geo[mid]["marks"][name]
        layers[mid] = anchors_text([(an, ax, ay)]) + components_text([(acc, (ox, oy))])
    new.append((name, uni, layers, [0, 0], ["category = Mark;", "subCategory = Nonspacing;"]))

# Combining comma below: the comma drawn into Scommaaccent, centered under a lowercase o.
layers = {}
for mid in MASTERS:
    l = layer("Scommaaccent", mid)
    idx = [i for i, p in enumerate(l.paths) if max(n.position.y for n in p.nodes) <= 0]
    assert len(idx) == 1
    xs = [n.position.x for n in l.paths[idx[0]].nodes]
    dx = -geo[mid]["o_w"] / 2 - (min(xs) + max(xs)) / 2
    text = shift_path(path_texts("Scommaaccent", mid, idx)[0], dx, 0)
    layers[mid] = anchors_text([("_bottom", -geo[mid]["o_w"] / 2, 0)]) + ["paths = ("] + [text] + [");"]
new.append(("commaaccentcomb", "0326", layers, [0, 0], ["category = Mark;", "subCategory = Nonspacing;"]))

blocks = []
for name, uni, layers, widths, extra in new:
    lb = []
    for mid, w in zip((LIGHT, BOLD), widths):
        lb.append("\n".join(["{"] + layers[mid] + ['layerId = "%s";' % mid, "name = %s;" % MASTERS[mid], "width = %d;" % w, "}"]))
    tail = ["unicode = %s;" % uni] if uni else []
    blocks.append("\n".join(["{", "glyphname = %s;" % name] + extra + ["layers = (", ",\n".join(lb), ");"] + tail + ["}"]))

gi = lines.index("glyphs = (")
end = block_end(gi)
assert lines[end - 1] == "}"
lines[end - 1] = "},"
lines[end:end] = [",\n".join(blocks)]

# 3. ccmp: i and j lose their dot before a mark above. A prefix of its own, after the 2015 GSUB.
code = (
    "# GF Latin Core, 2026-10-26\n\n"
    "@COMBINING_TOP = [gravecomb acutecomb circumflexcomb tildecomb macroncomb brevecomb dotaccentcomb dieresiscomb ringcomb hungarumlautcomb caroncomb];\n\n"
    "@COMBINING_BOTTOM = [cedillacomb commaaccentcomb ogonekcomb];\n\n"
    "lookup ccmp_dotless {\n"
    "  sub [i j iogonek]' @COMBINING_TOP by [dotlessi dotlessj iogonek.dotless];\n"
    "  sub [i j iogonek]' @COMBINING_BOTTOM @COMBINING_TOP by [dotlessi dotlessj iogonek.dotless];\n"
    "} ccmp_dotless;\n\n"
    "feature ccmp {\n  lookup ccmp_dotless;\n} ccmp;\n"
)
esc = '"' + code.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\012") + '"'
fp = lines.index("featurePrefixes = (")
fe = block_end(fp)
assert lines[fe - 1] == "}"
lines[fe - 1] = "},"
lines[fe:fe] = ["{\ncode = %s;\nname = Latin;\n}" % esc]

open(SRC, "w", encoding="utf-8").write("\n".join(lines))

# 4. GlyphOrderAndAliasDB, for the hindkit build.
import unicodedata
goadb = open("GlyphOrderAndAliasDB", encoding="utf-8").read().rstrip("\n").split("\n")
for name, uni, *_ in new:
    if uni:
        goadb.append("uni%s %s uni%s # %s" % (uni, name, uni, unicodedata.name(chr(int(uni, 16)))))
    else:
        goadb.append("%s %s" % (name, name))
open("GlyphOrderAndAliasDB", "w", encoding="utf-8").write("\n".join(goadb) + "\n")

# Report, for the record.
for mid, mname in MASTERS.items():
    print(mname, "composites", geo[mid]["place"])
    print(mname, "marks", {k: v for k, v in geo[mid]["marks"].items()})
print("added", len(new), "glyphs")
