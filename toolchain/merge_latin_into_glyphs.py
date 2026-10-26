# One-time, 2026-10-26: merged the Hind Latin (resources/hindkit-0.3.0/Hind.glyphs, removed afterward;
# see git history) and the 2015 GSUB (features/*.fea, likewise) into masters/HindiSiliguri.glyphs,
# so the .glyphs file builds on its own with fontmake and gftools builder. Kept as a record.

# One-time: make masters/HindiSiliguri.glyphs self-contained (Latin glyphs, GSUB, mark categories).
import re
SRC = "masters/HindiSiliguri.glyphs"
LATIN = "resources/hindkit-0.3.0/Hind.glyphs"
IDS = {"7C6C6D54-BD7C-484C-BA4C-283093F5BAFD": "D864283E-EAB4-426F-8533-332F2D658CBA",   # Light
       "9624E7F4-80FA-4A11-8396-8F8611ED4CD7": "731EBDE8-0F2D-4E32-814F-AAFC41A14D25"}   # Bold
MARKS = "bnmU bnmUU bnmvR bnmvRR bnCandrabindu bnReph bnRAc2 bnBAc2 bnReph.matraii".split()

def glyph_blocks(lines):
    """(start, end) line ranges of the top-level glyph dicts inside `glyphs = (`."""
    i = lines.index("glyphs = (") + 1
    blocks, depth, start = [], 0, None
    while True:
        s = lines[i]
        if depth == 0 and s == ");":
            return blocks, i
        if depth == 0 and s == "{":
            start = i
        depth += s.count("{") + s.count("(") - s.count("}") - s.count(")") if not s.startswith('"') else 0
        if depth == 0 and start is not None and s in ("}", "},"):
            blocks.append((start, i)); start = None
        i += 1

def esc(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\012") + '"'

src = open(SRC, encoding="utf-8").read().split("\n")
lat = open(LATIN, encoding="utf-8").read().split("\n")

# 1. bnCHA has two backup layers with the same name; glyphsLib refuses duplicates.
dup = [i for i, s in enumerate(src) if s == 'name = "Bold Mar 17 15, 13:33";']
assert len(dup) == 2
src[dup[1]] = 'name = "Bold Mar 17 15, 13:33 (2)";'

# 2. Mark categories, so GDEF from glyphsLib matches the hindkit build's @COMBINING_MARKS.
for name in MARKS:
    i = src.index("glyphname = %s;" % name)
    src[i + 1:i + 1] = ["category = Mark;", "subCategory = Nonspacing;"]

# 3. Latin glyphs, except names the Bangla source already has (space).
names = {s[len("glyphname = "):-1] for s in src if s.startswith("glyphname = ")}
blocks, _ = glyph_blocks(lat)
new = []
for a, b in blocks:
    block = lat[a:b + 1]
    gname = next(s for s in block if s.startswith("glyphname = "))[len("glyphname = "):-1]
    if gname.strip('"') in names or gname in names:
        continue
    text = "\n".join(block).rstrip(",")
    for old, newid in IDS.items():
        text = text.replace(old, newid)
    assert not re.search(r"7C6C6D54|9624E7F4", text)
    new.append(text)
_, end = glyph_blocks(src)
assert src[end - 1] == "}"
src[end - 1] = "},"
src[end:end] = [",\n".join(new)]
print("added", len(new), "Latin glyphs")

# 4. The hand-written OpenType code, as prefixes: language systems, then the 2015 GSUB files verbatim.
prefixes = [("languagesystems", "languagesystem DFLT dflt;\nlanguagesystem beng dflt;\nlanguagesystem bng2 dflt;\n"),
            ("GSUB_lookups", open("features/GSUB_lookups.fea", encoding="utf-8").read()),
            ("GSUB", open("features/GSUB.fea", encoding="utf-8").read())]
block = ["featurePrefixes = ("] + [",\n".join("{\ncode = %s;\nname = %s;\n}" % (esc(code), name) for name, code in prefixes)] + [");"]
i = src.index("fontMaster = (")
src[i:i] = block

open(SRC, "w", encoding="utf-8").write("\n".join(src))
