"""wmparts.render: the sheets (Pillow). Every title starts with FAMILY Master · /glyph; files follow fname() (E -> E_).

    parts(glyph, out=None)                 the pairing over the letter | the parts pulled apart
    cell(glyph, W=440, H=480)              one parts-grid cell (strokes, flags, slab serifs, balls, node numbers)
    grid(font, out_dir)                    grid_<Tag>.png per master (sets.grids)
    groups(glyph, out=None)                the selections: one colour per group, its vector, rule tags (the approval sheet)
    nested(glyph, out)                     each part's sides at CNTR 0 / 25 / 50 / 75 / 100 (Mark's Illustrator look)
    overview(font, tag, out)               every letter of a master at CNTR 0 · 50 · 100
    serifs(font, tag, out)                 feet and heads, CNTR 0 | 100
    before_after(glyph, before, after)     CNTR 100 before | after, crossings ringed
    combs(verdict_or_move, out)            curvature combs drawn | 50 | 100 (curvcomb's G2 sheet)
    combs_index(verdicts, master, out)     the worst-first thumbnail index of a master
Each returns a PIL image (and saves it when out is given) unless noted.
"""
import os
from PIL import Image
from .draw import Panel, fontlabel, header, font, CAL, MENLO, BG, find_font, font_dirs   # noqa: F401
from . import draw, partsheet, grid as _grid, groupsheet, overview as _overview, basheet, curvsheet as _combs, sets  # noqa: F401


def _save(im, out):
    if out:
        d = os.path.dirname(out)
        if d:
            os.makedirs(d, exist_ok=True)
        im.save(out)
    return im


def _set_of(glyph):
    f = getattr(glyph, "font", None)
    return f if f is not None else {"%s_%s" % (glyph.get("_tag") or glyph["master"].replace(" ", ""), glyph["glyph"]): glyph}


def _key_of(glyph, G):
    return next(k for k, v in G.items() if v is glyph)


def parts(glyph, out=None, PW=900, PH=960):
    im, P = partsheet.parts_sheet(glyph, PW, PH)
    return _save(im, out)


def cell(glyph, W=440, H=480, labels=True):
    return _grid.cell(glyph, W, H, labels=labels)[0]


def grid(font, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    sets.grids(font, out_dir)


def groups(glyph, out=None, PW=900, PH=980):
    """the approval sheet (GRILL 11A): groups, vectors, graded / anchor / slid nodes, the rule tags per group"""
    import tempfile
    G = _set_of(glyph)
    path = out or os.path.join(tempfile.mkdtemp(), "groups.png")
    groupsheet.groups_sheet(G, _key_of(glyph, G), path, PW, PH)
    return Image.open(path)


def nested(glyph, out, **kw):
    G = _set_of(glyph)
    return groupsheet.nested_sheet(G, _key_of(glyph, G), out, **kw)


def overview(font, tag, out):
    sets.overview(font, tag, out)
    return Image.open(out)


def serifs(font, tag, out, glyphs=("H", "n", "T", "E", "f")):
    sets.serifs_sheet(font, tag, out, glyphs=glyphs)
    return Image.open(out)


def before_after(glyph, before, after, out=None, bb=None, W=620, H=640, M=None, labels=("BEFORE", "AFTER")):
    """before / after: contour lists, or Move objects (their contours_at(1.0))"""
    b = before.contours_at(1.0) if hasattr(before, "contours_at") else before
    a = after.contours_at(1.0) if hasattr(after, "contours_at") else after
    if M is None and hasattr(after, "contours_at"):
        M = after
    return _save(basheet.before_after(glyph, b, a, bb=bb, W=W, H=H, M=M, labels=labels), out)


def combs(v, out, mover_name="groupmove"):
    """v: a Verdict (wmparts.evaluate) or a Move (evaluated here)"""
    if not hasattr(v, "raw"):
        from .. import evaluate
        v = evaluate(v)
    res = v.raw
    if res.get("key") is None:

        res["key"] = res["glyph"]
    _combs.render(res, out, mover_name)
    return Image.open(out)


def combs_index(verdicts, master, out, mover_name="groupmove"):
    rs = []
    for v in verdicts:
        r = v.raw
        if r.get("key") is None:
            r["key"] = r["glyph"]
        rs.append(r)
    _combs.index_sheet(rs, master, out, mover_name)
    return Image.open(out)
