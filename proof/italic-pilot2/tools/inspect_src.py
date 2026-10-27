import glyphsLib, sys, collections
f = glyphsLib.GSFont(sys.argv[1])
print("masters", [(m.name, m.id, m.weightValue if hasattr(m,'weightValue') else None, m.xHeight, m.capHeight, m.ascender, m.descender) for m in f.masters])
print("upm", f.upm, "glyphs", len(f.glyphs))
cnt = collections.Counter()
for g in f.glyphs:
    L = g.layers[f.masters[0].id]
    kind = ("P" if L.paths else "") + ("C" if L.components else "")
    cnt[kind or "empty"] += 1
print(cnt)
for name in ["n","o","ka-bng","ma-bng","dda-bng","one-bng","a-bng","kassa-bng"]:
    g = f.glyphs[name]
    if g is None: print("missing", name); continue
    L = g.layers[f.masters[0].id]
    print(name, g.unicode, len(L.paths), [len(p.nodes) for p in L.paths], [c.name for c in L.components], [a.name for a in L.anchors], L.width)
print([g.name for g in f.glyphs][:40])
print([g.name for g in f.glyphs if 'bng' in g.name][:200])
