"""Extract glyph layers (components decomposed, plain transforms) into the solver's JSON."""
import sys, json, glyphsLib
src, out = sys.argv[1], sys.argv[2]
names = sys.argv[3].split(','); masters = sys.argv[4].split(',')
f = glyphsLib.GSFont(src)
mid = {m.id: m.name for m in f.masters}
T = {'line': 'l', 'curve': 'c', 'offcurve': 'o', 'qcurve': 'c'}

def layer_of(gname, lid):
    g = f.glyphs[gname]
    for l in g.layers:
        if l.layerId == lid:
            return l
    return None

def contours(l, lid, xf=(1, 0, 0, 1, 0, 0), depth=0):
    a, b, c, d, tx, ty = xf
    cs = []
    for p in l.paths:
        nodes = []
        for n in p.nodes:
            x, y = n.position.x, n.position.y
            nodes.append([a * x + c * y + tx, b * x + d * y + ty, T[n.type], bool(n.smooth)])
        cs.append({"closed": bool(p.closed), "nodes": nodes})
    for comp in l.components:
        bl = layer_of(comp.name, lid)
        if bl is None or depth > 3:
            print('WARN missing component', comp.name); continue
        ct = comp.transform
        ca, cb, cc, cd, ctx, cty = ct[0], ct[1], ct[2], ct[3], ct[4], ct[5]
        # compose: outer xf applied after component transform
        na = a * ca + c * cb; nb = b * ca + d * cb
        nc = a * cc + c * cd; nd = b * cc + d * cd
        ntx = a * ctx + c * cty + tx; nty = b * ctx + d * cty + ty
        cs += contours(bl, lid, (na, nb, nc, nd, ntx, nty), depth + 1)
    return cs

res = {}
for gn in names:
    g = f.glyphs[gn]
    for l in g.layers:
        if l.layerId not in mid or mid[l.layerId] not in masters: continue
        cs = contours(l, l.layerId)
        key = "HS%s_%s" % (mid[l.layerId].replace(' ', ''), gn)
        res[key] = {"contours": cs, "width": float(l.width), "master": mid[l.layerId], "glyph": gn}
json.dump(res, open(out, 'w'))
print(len(res), 'layers;', {k: [len(c['nodes']) for c in v['contours']] for k, v in res.items() if v['glyph'] in ('j', 'H_a_r_v_e_y')})
