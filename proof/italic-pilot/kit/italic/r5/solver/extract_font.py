"""Extract master layers (components decomposed, in component order, nodes in file order) into the solver's JSON.

extract_font.py OUT.json TAGSPEC SRC [TAGSPEC SRC ...]   e.g.
  extract_font.py marya.json  MaryaRoman=Roman marya-roman.glyphs  MaryaItalic=Italic marya-italic.glyphs
Each SRC is followed by nothing else; TAGSPEC is  Tag=MasterName[,Tag=MasterName...]  ("*" = every master, tag = prefix+name without spaces).
Writes OUT.json and OUT.missing.json (master layers that are absent or empty, per glyph).
"""
import sys, os, json, glyphsLib
LETTERS = "f j H n a E T r v e y k x".split()
T = {'line': 'l', 'curve': 'c', 'offcurve': 'o', 'qcurve': 'c'}


def extract(f, tagmap):
    mid = {m.id: m.name for m in f.masters}
    res, missing = {}, []

    def layer_of(gname, lid):
        g = f.glyphs[gname]
        if g is None: return None
        for l in g.layers:
            if l.layerId == lid: return l
        return None

    def contours(l, lid, xf=(1, 0, 0, 1, 0, 0), depth=0):
        a, b, c, d, tx, ty = xf
        cs = []
        for p in l.paths:
            cs.append({"closed": bool(p.closed), "nodes": [
                [a * n.position.x + c * n.position.y + tx, b * n.position.x + d * n.position.y + ty, T[n.type], bool(n.smooth)]
                for n in p.nodes]})
        for comp in l.components:
            bl = layer_of(comp.name, lid)
            if bl is None or depth > 3:
                print('WARN missing component', comp.name); continue
            ca, cb, cc, cd, ctx, cty = comp.transform[:6]
            cs += contours(bl, lid, (a * ca + c * cb, b * ca + d * cb, a * cc + c * cd, b * cc + d * cd,
                                     a * ctx + c * cty + tx, b * ctx + d * cty + ty), depth + 1)
        return cs

    pkg = getattr(f, 'filepath', None)
    expand = bool(pkg) and str(pkg).rstrip('/').endswith('.glyphspackage')     # corner/cap components -> real points

    def expanded(gn, lid):
        """Corner + cap components expanded into points (tools/glyphs_corners.py, derived from geist-serif-morf/svg/source.py)."""
        import glyphs_corners as gc
        try:
            adv, shs = gc.shapes(gn, str(pkg), lid)
        except Exception as ex:
            print('WARN corner expansion failed', gn, lid, ex); return None
        return [{"closed": True, "nodes": gc.to_nodes(sh)} for sh in shs]

    for lid, mname in mid.items():
        tag = tagmap.get(mname) or tagmap.get('*')
        if tag is None: continue
        if tag.endswith('*'): tag = tag[:-1] + mname.replace(' ', '')
        for gn in LETTERS:
            l = layer_of(gn, lid)
            cs = None
            if expand and l is not None and (l.paths or l.components):
                cs = expanded(gn, lid)
            if cs is None: cs = contours(l, lid) if l is not None else []
            if not cs:
                missing.append({"master": mname, "tag": tag, "glyph": gn, "why": "no layer" if l is None else "empty layer"}); continue
            res["%s_%s" % (tag, gn)] = {"contours": cs, "width": float(l.width), "master": mname, "glyph": gn}
    return res, missing


if __name__ == "__main__":
    out = sys.argv[1]; args = sys.argv[2:]
    res, miss = {}, []
    for i in range(0, len(args), 2):
        tagmap = {}
        for kv in args[i].split(','):
            t, _, m = kv.partition('=')
            tagmap[m] = t
        r, m = extract(glyphsLib.GSFont(args[i + 1]), tagmap)
        res.update(r); miss += m
    json.dump(res, open(out, 'w'))
    json.dump(miss, open(out.replace('.json', '.missing.json'), 'w'), indent=1)
    print(len(res), 'layers;', len(miss), 'missing')
    for m in miss: print('  missing', m['tag'], m['glyph'], m['why'])
