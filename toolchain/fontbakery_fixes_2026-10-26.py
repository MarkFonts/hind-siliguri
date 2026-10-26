# One-time, 2026-10-26: source fixes for fontbakery's Google Fonts profile (fontbakery 1.1.0),
# applied to masters/HindiSiliguri.glyphs as text so the rest of the file stays byte-identical.
# Kept as a record; see the commit message for the before/after check results.
# The source has since been renamed masters/HindSiliguri.glyphs; SRC below is the name at the time.

SRC = "masters/HindiSiliguri.glyphs"
LIGHT = "D864283E-EAB4-426F-8533-332F2D658CBA"
BOLD = "731EBDE8-0F2D-4E32-814F-AAFC41A14D25"

lines = open(SRC, encoding="utf-8").read().split("\n")

def delta(s):
    return 0 if s.startswith('"') else s.count("{") + s.count("(") - s.count("}") - s.count(")")

def block_end(i):
    """Index of the line that closes the block opened on line i."""
    depth, j = 0, i
    while True:
        depth += delta(lines[j])
        if depth == 0:
            return j
        j += 1

def children(a, b):
    """Top-level `{...}` items of the list opened on line a and closed on line b."""
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
    """Line of `key` directly inside the dict on lines a..b (not in nested blocks)."""
    depth = 0
    for k in range(a, b + 1):
        if depth == 1 and (lines[k] == key or lines[k].startswith(key)):
            return k
        depth += delta(lines[k])
    raise KeyError(key)

def glyph_range(name):
    i = lines.index("glyphname = %s;" % name)
    while lines[i] != "{":
        i -= 1
    return i, block_end(i)

def layer_range(glyph, layer_id):
    a, b = glyph_range(glyph)
    la = key_at_depth1(a, b, "layers = (")
    for s, e in children(la, block_end(la)):
        if key_at_depth1(s, e, "layerId = ") and lines[key_at_depth1(s, e, "layerId = ")] == 'layerId = "%s";' % layer_id:
            return s, e
    raise KeyError(layer_id)

def path_ranges(glyph, layer_id):
    """(start, end) of each path dict in the layer's own paths (not its background's)."""
    a, b = layer_range(glyph, layer_id)
    p = key_at_depth1(a, b, "paths = (")
    return children(p, block_end(p))

def nodes_range(start, end):
    n = next(k for k in range(start, end) if lines[k] == "nodes = (")
    e = next(k for k in range(n, end) if lines[k] == ");")
    return n + 1, e

# 1. Contour order: Bold lists two small rectangles in the opposite order from Light, so each one
#    travels to the other's place between the masters (visible in SemiBold).
for glyph in ["bnL_PHA", "bnL_D_RA"]:
    ranges = path_ranges(glyph, BOLD)
    (a4, b4), (a5, b5) = ranges[4], ranges[5]
    assert a5 == b4 + 1
    # Each block ends with "}" or "},"; swap the bodies and keep each slot's closing line.
    body4, body5 = lines[a4:b4], lines[a5:b5]
    lines[a4:b5 + 1] = body5 + [lines[b4]] + body4 + [lines[b5]]

# 2. Contour direction: these outer contours run clockwise in both masters (TrueType from fontmake
#    then comes out counter-clockwise). Reverse them in both masters alike, so they stay compatible.
#    The bnSS_* diagonals that defcon also flags are overlaps, not reversed contours; leave them.
def reverse_nodes(node_lines):
    pts = []
    for s in node_lines:
        parts = s.strip().rstrip(",").strip('"').split()
        pts.append([parts[0], parts[1], parts[2], len(parts) > 3 and parts[3] == "SMOOTH"])
    # Glyphs: each on-curve node's type is the segment that ends at it. Reversed, an on-curve
    # ends the segment that used to start at it, i.e. it takes the type of the next on-curve.
    n = len(pts)
    on = [i for i in range(n) if pts[i][2] != "OFFCURVE"]
    new_type = {}
    for idx, i in enumerate(on):
        new_type[i] = pts[on[(idx + 1) % len(on)]][2]
    rev = []
    for i in reversed(range(n)):
        x, y, t, smooth = pts[i]
        t = new_type.get(i, t)
        rev.append('"%s %s %s%s"' % (x, y, t, " SMOOTH" if smooth else ""))
    # Keep the start node (Glyphs stores it last): the old last node stays last.
    rev = rev[1:] + rev[:1]
    return [s + "," for s in rev[:-1]] + [rev[-1]]

for glyph, paths in [("bnOne", [0]), ("bnTwo", [0]), ("bnNine", [0, 1])]:
    for layer_id in (LIGHT, BOLD):
        for p in paths:
            a, b = path_ranges(glyph, layer_id)[p]
            na, nb = nodes_range(a, b)
            lines[na:nb] = reverse_nodes(lines[na:nb])

# 3. Dotted circle: base anchors for the above (candrabindu, reph) and below (u, uu, vocalic r) marks,
#    centered, at the headline and baseline the consonants use (634/671 and 0).
for layer_id, top in [(LIGHT, 634), (BOLD, 671)]:
    a, b = layer_range("dottedcircle", layer_id)
    i = key_at_depth1(a, b, "layerId = ")
    anchors = [("abvm.chandrabindu", 330, top), ("abvm.reph", 330, top), ("blwm.u", 330, 0)]
    block = ["anchors = ("] + [",\n".join('{\nname = %s;\nposition = "{%d, %d}";\n}' % t for t in anchors)] + [");"]
    lines[i:i] = block

# 4. U+00A0, which Google Fonts requires: an empty glyph as wide as space in each master.
a, b = glyph_range("space")
nbsp = ["{", "glyphname = nbspace;", "layers = (", "{",
        'layerId = "%s";' % BOLD, "name = Bold;", "width = 250;", "},", "{",
        'layerId = "%s";' % LIGHT, "name = Light;", "width = 220;", "}", ");", "unicode = 00A0;", "},"]
lines[b + 1:b + 1] = nbsp

# 5. Instance style linking: Bold is the bold of Regular.
i = lines.index("instances = (")
k = next(k for k in range(i, len(lines)) if lines[k] == "name = Bold;")
lines[k:k] = ["isBold = 1;"]

# 6. Font info: Google Fonts' copyright pattern, the real manufacturer, no "~" placeholders.
for old, new in [('copyright = "~";', 'copyright = "Copyright 2015 The Hind Siliguri Project Authors (https://github.com/itfoundry/hind-siliguri)";'),
                 ('manufacturer = "~";', 'manufacturer = "Indian Type Foundry";'),
                 ('manufacturerURL = "~";', 'manufacturerURL = "https://www.indiantypefoundry.com";')]:
    assert lines.count(old) == 1, old
    lines[lines.index(old)] = new
lines.remove('designerURL = "~";')

# 7. Font-wide parameters: the vertical metrics Google Fonts has served since 2017, typo metrics on,
#    installable embedding, and ITF's vendor ID.
text = "\n".join(lines)
for name, old, new in [("hheaAscender", 1200, 1116), ("hheaDescender", -800, -501),
                       ("typoAscender", 1200, 1116), ("typoDescender", -800, -501),
                       ("winAscent", 1200, 1116), ("winDescent", 800, 501)]:
    before = "{\nname = %s;\nvalue = %d;\n}" % (name, old)
    assert text.count(before) == 1, name
    text = text.replace(before, "{\nname = %s;\nvalue = %d;\n}" % (name, new))
anchor = "{\nname = Axes;"
extra = "".join("{\nname = %s;\nvalue = %s;\n},\n" % kv for kv in [
    ("fsType", "(\n)"), ('"Use Typo Metrics"', "1"), ("vendorID", "ITFO")])
assert text.count(anchor) == 1
text = text.replace(anchor, extra + anchor)

open(SRC, "w", encoding="utf-8").write(text)
print("done")
