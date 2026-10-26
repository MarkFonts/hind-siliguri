"""A variable font with one contrast axis: CNTR 0 = the drawn outlines, CNTR 100 = GroupMover's moved contours (t = 1).

geist-serif-text/vf/build_vf.py made general (round 8). Needs ufoLib2, fontTools, glyphsLib and fontmake (the `fonts`
extra). Node count, order and handle count never change (R16), so the two masters are compatible by construction;
glyphsLib's eraseOpenCorners runs as a PRE filter on both (what Glyphs does on export: crossed nib "ears" are cut
away) and is run here first on both masters with the point counts compared glyph by glyph: any mismatch stops the
build. Overlaps are kept (fontmake -o variable keeps them).

  build_variable_font(font, out_dir, axis="CNTR", erase_open_corners=True, ...) -> dict (what verify.json holds)
"""
import json, math, os, subprocess, sys

OPEN_CORNERS = {"name": "eraseOpenCorners", "namespace": "glyphsLib.filters", "pre": True}


def _unicode(name):
    from fontTools import agl
    u = agl.toUnicode(name)
    return [ord(u)] if len(u) == 1 else []


def _put(glyph, contours):
    from ufoLib2.objects import Contour, Point
    for c in contours:
        pts = []
        for x, y, t, *rest in c["nodes"]:
            seg = {"l": "line", "c": "curve", "o": None}[t]
            pts.append(Point(round(float(x), 3), round(float(y), 3), seg, bool(rest[0]) if rest and seg else False))
        glyph.contours.append(Contour(points=pts))


def _erased_structure(u):
    """eraseOpenCorners on a copy of the UFO: per glyph the point count of every contour, and the glyphs it changed"""
    import copy
    from glyphsLib.filters.eraseOpenCorners import EraseOpenCornersFilter
    c = copy.deepcopy(u)
    changed = EraseOpenCornersFilter()(c)
    return {g.name: [len(ct.points) for ct in g.contours] for g in c}, sorted(changed)


def build_variable_font(font, out_dir, axis="CNTR", erase_open_corners=True, master=None, glyphs=None, t=1.0,
                        family_name=None, reference_ttf=None, instances=(0, 50, 100), mover=None):
    """Build <Family><axis>[<axis>].ttf in out_dir from one master of `font` (a wmparts Font).

    master          master name or tag (default: the font's first)
    glyphs          glyph names (default every layer of that master)
    t               the move at the axis maximum (1.0 = CNTR 100 as the solver defines it)
    family_name     default "<family> <axis>"
    reference_ttf   a TTF to copy vertical metrics and the space width from (default: the master's own values)
    instances       static instances to cut with fontTools.varLib.instancer (axis values)
    mover           a callable layer -> object with contours_at(t) (default wmparts.move)
    Writes the two UFOs, the designspace, the VF, the instances and verify.json; returns the verification dict."""
    import ufoLib2
    from ufoLib2.objects import Contour, Point
    from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor, InstanceDescriptor
    from fontTools.ttLib import TTFont
    from . import move as _move

    mover = mover or _move
    tags = font.tags
    tag = tags[0] if master is None else next((tg for tg in tags if tg == master or font.layers(tg)[0].master == master), None)
    if tag is None:
        raise ValueError("no master %r in %r" % (master, font))
    layers = [g for g in font.layers(tag) if (glyphs is None or g.name in glyphs) and any(len(c["nodes"]) for c in g.contours)]
    entry = font.masters[tag] if tag in font.masters else {}
    fam = family_name or ("%s %s" % ((font.family or "Font").title(), axis)).strip()
    ps = fam.replace(" ", "")
    os.makedirs(out_dir, exist_ok=True)

    G = {}
    for g in layers:
        M = mover(g)
        moved = M.contours_at(t)
        assert [len(c["nodes"]) for c in moved] == [len(c["nodes"]) for c in g.contours], g.name
        G[g.name] = (float(g.width), g.contours, moved)
    order = sorted(G, key=lambda n: (not n[:1].isupper(), n))

    ref = TTFont(reference_ttf) if reference_ttf else None
    upm = float(entry.get("upm") or 1000)
    asc = entry.get("ascender") or 0.8 * upm
    desc = entry.get("descender") or -0.2 * upm
    space = ref["hmtx"]["space"][0] if ref is not None and "space" in ref.getGlyphOrder() else round(0.25 * upm)

    def make_ufo(which, style):
        u = ufoLib2.Font()
        i = u.info
        i.familyName = fam; i.styleName = style
        i.unitsPerEm = upm; i.ascender = asc; i.descender = desc
        i.xHeight = entry.get("xHeight"); i.capHeight = entry.get("capHeight")
        i.italicAngle = -float(entry.get("ia", 0.0)) if entry.get("ia") else 0
        if ref is not None:
            i.openTypeHheaAscender = ref["hhea"].ascent; i.openTypeHheaDescender = ref["hhea"].descent; i.openTypeHheaLineGap = 0
            i.openTypeOS2TypoAscender = ref["OS/2"].sTypoAscender; i.openTypeOS2TypoDescender = ref["OS/2"].sTypoDescender
            i.openTypeOS2TypoLineGap = 0; i.openTypeOS2WinAscent = ref["OS/2"].usWinAscent; i.openTypeOS2WinDescent = ref["OS/2"].usWinDescent
            i.openTypeOS2Selection = [7]
        i.copyright = "%s: %s axis built by wmparts (contrast-move solver)." % (font.family.title() if font.family else "Font", axis)
        i.versionMajor, i.versionMinor = 0, 1
        nd = u.newGlyph(".notdef"); nd.width = round(0.5 * upm)
        h = 0.7 * upm; w = 0.5 * upm
        nd.contours.append(Contour(points=[Point(0.1 * w, 0, "line"), Point(0.9 * w, 0, "line"), Point(0.9 * w, h, "line"), Point(0.1 * w, h, "line")]))
        nd.contours.append(Contour(points=[Point(0.2 * w, 0.05 * upm, "line"), Point(0.2 * w, h - 0.05 * upm, "line"), Point(0.8 * w, h - 0.05 * upm, "line"), Point(0.8 * w, 0.05 * upm, "line")]))
        extra = [".notdef"]
        if "space" not in G:
            sp = u.newGlyph("space"); sp.width = space; sp.unicodes = [0x20]; extra.append("space")
        for name in order:
            w_, drawn, moved = G[name]
            gl = u.newGlyph(name); gl.width = w_; gl.unicodes = _unicode(name)
            _put(gl, drawn if which == 0 else moved)
        u.glyphOrder = extra + order
        if erase_open_corners:
            u.lib["com.github.googlei18n.ufo2ft.filters"] = [OPEN_CORNERS]
        return u

    paths, struct = {}, {}
    for which, style in ((0, "Regular"), (100, "%s100" % axis)):
        u = make_ufo(which, style)
        if erase_open_corners:
            struct[which] = _erased_structure(u)
        p = os.path.join(out_dir, "%s-%s.ufo" % (ps, style)); u.save(p, overwrite=True); paths[which] = p
    ch0 = []
    if erase_open_corners:
        (st0, ch0), (st1, ch1) = struct[0], struct[100]
        bad = sorted(n for n in st0 if st0[n] != st1.get(n))
        if bad or ch0 != ch1:
            raise RuntimeError("eraseOpenCorners leaves the masters incompatible (%s; changed %s vs %s): not building" % (bad, ch0, ch1))

    ds = DesignSpaceDocument()
    ax = AxisDescriptor(); ax.name = axis; ax.tag = axis[:4].ljust(4); ax.minimum = 0; ax.default = 0; ax.maximum = 100
    ax.labelNames = {"en": "Contrast move"}
    ds.addAxis(ax)
    for which, style in ((0, "Regular"), (100, "%s100" % axis)):
        s_ = SourceDescriptor(); s_.path = paths[which]; s_.filename = os.path.basename(paths[which])
        s_.familyName = fam; s_.styleName = style; s_.location = {axis: which}
        ds.addSource(s_)
    for v in instances:
        ins = InstanceDescriptor(); ins.familyName = fam; ins.styleName = "%s %d" % (axis, v)
        ins.location = {axis: v}; ds.addInstance(ins)
    dsp = os.path.join(out_dir, "%s.designspace" % ps); ds.write(dsp)

    vf = os.path.join(out_dir, "%s[%s].ttf" % (ps, axis))
    subprocess.run([sys.executable, "-m", "fontmake", "-m", dsp, "-o", "variable", "--output-path", vf], check=True)

    from fontTools.varLib import instancer
    for v in instances:
        f = TTFont(vf)
        inst = instancer.instantiateVariableFont(f, {axis: v}, updateFontNames=False)
        inst.save(os.path.join(out_dir, "%s-%s%03d.ttf" % (ps, axis, v)))

    f = TTFont(vf)
    gv = f["gvar"].variations
    gorder = f.getGlyphOrder()
    moved_names = [n for n in G if any(abs(a[0] - b[0]) > 0.5 or abs(a[1] - b[1]) > 0.5
                                       for ca, cb in zip(G[n][1], G[n][2]) for a, b in zip(ca["nodes"], cb["nodes"]))]
    nonzero = [n for n in gorder if any(any(c is not None and (c[0] or c[1]) for c in tv.coordinates) for tv in (gv.get(n) or []))]
    info = dict(vf=vf, fvar=[(a.axisTag, a.minValue, a.defaultValue, a.maxValue) for a in f["fvar"].axes],
                named_instances=[(i.coordinates, f["name"].getDebugName(i.subfamilyNameID)) for i in f["fvar"].instances],
                master=tag, glyphs=len(gorder), glyphs_with_gvar=len([n for n in gorder if gv.get(n)]),
                glyphs_with_nonzero_deltas=len(nonzero), outline_glyphs=len(G), moved_glyphs=sorted(moved_names),
                static_glyphs=sorted(set(gorder) - set(nonzero)))
    if erase_open_corners:
        info["eraseOpenCorners"] = dict(pre_filter=OPEN_CORNERS, glyphs_changed=ch0, point_counts_after={n: struct[0][0][n] for n in ch0})
    json.dump(info, open(os.path.join(out_dir, "verify.json"), "w"), indent=1, default=str)
    return info
