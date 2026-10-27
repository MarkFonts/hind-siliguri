"""2026-10-27, on Mark's save of masters/HindSiliguri.glyphs (run with the file closed in Glyphs).

1. Dots. Mark redrew `dotaccent` to the i's dot and made `i` = dotlessi + dotaccentcomb. The redrawn dot sits 57 u
   (Light) / 60 u (Bold) lower in its glyph, so every composite that places `dotaccent` at a fixed offset
   (Ċ Ė Ġ İ Ż ċ ė ġ ż and dotaccentcomb) dropped by that much: lowercase dots 25 u above the letter in Light,
   overlapping it in Bold. Each `dotaccent` component is raised by the same amount, which puts every dot back where
   it was, with the new shape. Then the i's dot moves down to ė's height (Mark: "i dot should match ė").
2. Names. dotlessi -> idotless, dotlessj -> jdotless (Glyphs 3 names), everywhere in the source: glyph names,
   components, the ccmp feature, display strings. GlyphOrderAndAliasDB keeps the 2015 production names
   (dotlessi, uni0237) and takes the new design names.
"""
import re, sys
SRC, GOADB = "masters/HindSiliguri.glyphs", "GlyphOrderAndAliasDB"
LIGHT, BOLD = "D864283E-EAB4-426F-8533-332F2D658CBA", "731EBDE8-0F2D-4E32-814F-AAFC41A14D25"
RAISE = {LIGHT: 57, BOLD: 60}
s = open(SRC, encoding="utf-8").read()
ALREADY = 'name = dotaccent;\ntransform = "{1, 0, 0, 1, 82, -32}";' in s     # ė Light after 1a: run once only

# 1a. raise every dotaccent component, per master layer
comp = re.compile(r'(?<=\n)(name = dotaccent;\n)(transform = "\{1, 0, 0, 1, (-?[\d.]+), (-?[\d.]+)\}";\n)?')
out, pos, n = [], 0, 0
for m in ([] if ALREADY else comp.finditer(s)):
    lid = re.search(r'layerId = "([^"]+)";', s[m.end():]).group(1)
    if lid not in RAISE:
        continue
    x = float(m.group(3) or 0); y = float(m.group(4) or 0) + RAISE[lid]
    fmt = lambda v: str(int(v)) if v == int(v) else str(v)
    out.append(s[pos:m.start()]); out.append('%stransform = "{1, 0, 0, 1, %s, %s}";\n' % (m.group(1), fmt(x), fmt(y)))
    pos = m.end(); n += 1
s = "".join(out) + s[pos:]
print("dotaccent components raised:", n)

# 1b. i: its dotaccentcomb goes down to e-dotaccent's dot height (dot bottom 595 Light, 561 Bold, as before)
I_COMB = {LIGHT: (112, -89), BOLD: (138, -68)}
gi = s.index("\nglyphname = i;\n"); ge = s.index("\nglyphname =", gi + 10)
blk = s[gi:ge]
def fix(m):
    lid = re.search(r'layerId = "([^"]+)";', blk[m.end():]).group(1)
    return '%stransform = "{1, 0, 0, 1, %d, %d}";\n' % ((m.group(1),) + I_COMB[lid])
blk = re.sub(r'(?<=\n)(name = dotaccentcomb;\n)transform = "[^"]*";\n', fix, blk)
s = s[:gi] + blk + s[ge:]

# 2. dotlessi -> idotless, dotlessj -> jdotless
s = re.sub(r"\bdotlessi\b", "idotless", s); s = re.sub(r"\bdotlessj\b", "jdotless", s)
open(SRC, "w", encoding="utf-8").write(s)
g = open(GOADB, encoding="utf-8").read()
g = g.replace("dotlessi dotlessi uni0131", "dotlessi idotless uni0131").replace("uni0237 dotlessj uni0237", "uni0237 jdotless uni0237")
open(GOADB, "w", encoding="utf-8").write(g)
print("i dot lowered; dotless glyphs renamed; GOADB design names updated")

# 3. (applied by hand after 1-2, recorded here) dotaccentcomb's dot lowered 90 u Light / 67 u Bold, so the combining
#    mark on a top anchor (e + U+0307, i + U+0307 through ccmp) lands where the precomposed e-dotaccent's dot is; the
#    i's dotaccentcomb offset goes back up by the same, to Mark's (112, 1) / (138, -1).
