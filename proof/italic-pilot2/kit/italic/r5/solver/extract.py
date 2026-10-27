import sys, json, glyphsLib
src, out = sys.argv[1], sys.argv[2]
names = sys.argv[3].split(',')
f = glyphsLib.GSFont(src)
mid = {m.id: m.name for m in f.masters}
T = {'line': 'l', 'curve': 'c', 'offcurve': 'o', 'qcurve': 'c'}
res = {}
for gn in names:
    g = f.glyphs[gn]
    for l in g.layers:
        if l.layerId not in mid: continue
        if l.components: print('WARN components', gn, mid[l.layerId], [c.name for c in l.components])
        cs = []
        for p in l.paths:
            cs.append({"closed": bool(p.closed), "nodes": [[float(n.position.x), float(n.position.y), T[n.type], bool(n.smooth)] for n in p.nodes]})
        key = "HS%s_%s" % (mid[l.layerId].replace(' ', ''), gn)
        res[key] = {"contours": cs, "width": float(l.width), "master": mid[l.layerId], "glyph": gn, "hints": len(l.hints)}
json.dump(res, open(out, 'w'), indent=0)
for k, v in res.items(): print(k, [len(c['nodes']) for c in v['contours']], 'hints', v['hints'])
