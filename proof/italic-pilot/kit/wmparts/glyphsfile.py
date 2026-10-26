"""Read a .glyphs / .glyphspackage into the solver's layers (needs glyphsLib; extract_font.py + mk_masters.py's logic).

Per master layer: components decomposed (full transform), nodes in file order, [x, y, type, smooth]. A layer that
uses Glyphs 3 corner or cap components (Geist Serif's serifs) is expanded into real points by corners.py instead
(drawn paths first, then component outlines). Masters: the file's stems / zones / metrics where defined, measured
from the letters (H n f k j e) otherwise; A from the measured n stem (masters.master_info).

  load_source(path, glyphs=None, masters=None) -> Font      (wmparts.load_glyphs calls this)
  extract(gsfont, tagmap, letters) -> (layers, missing)      the old extract_font.py interface
"""
import os

from .font import Font, Glyph
from .masters import Masters, measure, file_entry

LETTERS = "f j H n a E T r v e y k x".split()     # Mark's 13 test letters (the default of the old extract_font.py)
MEASURE = ("H", "n", "f", "k", "j", "e")          # what masters.measure reads
T = {'line': 'l', 'curve': 'c', 'offcurve': 'o', 'qcurve': 'c'}


def _layer_of(f, gname, lid):
    g = f.glyphs[gname]
    if g is None:
        return None
    for l in g.layers:
        if l.layerId == lid:
            return l
    return None


def _contours(f, l, lid, xf=(1, 0, 0, 1, 0, 0), depth=0):
    a, b, c, d, tx, ty = xf
    cs = []
    for p in l.paths:
        cs.append({"closed": bool(p.closed), "nodes": [
            [a * n.position.x + c * n.position.y + tx, b * n.position.x + d * n.position.y + ty, T[n.type], bool(n.smooth)]
            for n in p.nodes]})
    for comp in l.components:
        bl = _layer_of(f, comp.name, lid)
        if bl is None or depth > 3:
            print('WARN missing component', comp.name); continue
        ca, cb, cc, cd, ctx, cty = comp.transform[:6]
        cs += _contours(f, bl, lid, (a * ca + c * cb, b * ca + d * cb, a * cc + c * cd, b * cc + d * cd,
                                     a * ctx + c * cty + tx, b * ctx + d * cty + ty), depth + 1)
    return cs


def _source_path(f):
    p = getattr(f, 'filepath', None)
    return str(p).rstrip('/') if p else None


def extract(f, tagmap, letters=LETTERS):
    """f: a glyphsLib GSFont; tagmap {master name: tag} ("*" = every master, a tag ending in * gets the master name
    appended without spaces). -> ({key: layer record}, [missing layers])"""
    from . import corners
    mid = {m.id: m.name for m in f.masters}
    res, missing = {}, []
    pkg = _source_path(f)
    src = None
    if pkg and (pkg.endswith('.glyphspackage') or pkg.endswith('.glyphs')):
        try:
            src = corners.source(pkg)
            if not src.package:
                src._load_all()
        except Exception as ex:                       # a Glyphs 2 file: no corner components to expand
            src = None

    def expanded(gn, lid):
        try:
            adv, shs = corners.shapes(gn, src, lid)
        except Exception as ex:
            print('WARN corner expansion failed', gn, lid, ex); return None
        return [{"closed": True, "nodes": corners.to_nodes(sh)} for sh in shs]

    for lid, mname in mid.items():
        tag = tagmap.get(mname) or tagmap.get('*')
        if tag is None:
            continue
        if tag.endswith('*'):
            tag = tag[:-1] + mname.replace(' ', '')
        for gn in letters:
            l = _layer_of(f, gn, lid)
            cs = None
            if src is not None and l is not None and (l.paths or l.components):
                if src.package or src.has_corners(gn, lid):
                    cs = expanded(gn, lid)
            if cs is None:
                cs = _contours(f, l, lid) if l is not None else []
            if not cs:
                missing.append({"master": mname, "tag": tag, "glyph": gn, "why": "no layer" if l is None else "empty layer"}); continue
            res["%s_%s" % (tag, gn)] = {"contours": cs, "width": float(l.width), "master": mname, "glyph": gn}
    return res, missing


def load_source(path, glyphs=None, masters=None):
    """a .glyphs / .glyphspackage -> Font (tags "<FamilyNameWithoutSpaces><MasterNameWithoutSpaces>", family label =
    the family name in capitals, masters measured + the file's values). glyphs: names (default every exporting glyph
    with outlines); masters: master names to read (default all)."""
    import glyphsLib
    f = glyphsLib.GSFont(str(path))
    fam = (f.familyName or os.path.splitext(os.path.basename(str(path).rstrip('/')))[0]).strip()
    prefix = fam.replace(' ', '')
    tagmap = {m.name: prefix + m.name.replace(' ', '') for m in f.masters if masters is None or m.name in masters}
    if glyphs is None:
        want = [g.name for g in f.glyphs if g.export and any(l.paths or l.components for l in g.layers)]
    else:
        want = list(glyphs)
    letters = want + [m for m in MEASURE if m not in want and f.glyphs[m] is not None]
    raw, missing = extract(f, tagmap, letters)
    F = Font(family=fam.upper(), source=str(path))
    for key, r in raw.items():
        g = Glyph(r); g["_tag"] = key.split("_")[0]; g["family"] = fam.upper()
        F[key] = g
    E = {}
    for m in f.masters:
        if m.name not in tagmap:
            continue
        tag = tagmap[m.name]
        e = file_entry(m, f.upm, measure(F, tag))
        e["family"] = fam.upper()
        E[tag] = e
    F.masters = Masters(E)
    F.missing = missing
    F.attach()
    for key in list(F):
        if F[key].name not in want:
            del F[key]
    return F
