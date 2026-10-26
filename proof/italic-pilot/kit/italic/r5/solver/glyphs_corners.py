# COPIED from /Users/Mark/Documents/Github/geist-serif-morf/svg/source.py (verified corner + cap decomposition
# for Geist Serif). Local changes only: SRC points at the SCRATCH copy of the package; _smart_layer follows the
# master being expanded (module global REG, set by shapes()); shapes() returns drawn paths first, then
# component refs (the order extract_font.py always used); to_nodes() converts to the solver's node format.
"""Geist Serif source outlines with corner and cap components decomposed.

Reads the Regular master straight from the .glyphspackage, so nodes and
handles are the drawn cubics. glyphsLib's corner filter gets this font wrong
(no caps, no left/right anchors), so the placement rules here were derived
from, and are checked against, the exported TTF (see verify()).

A shape is a closed list of nodes: {"pt", "h": None | (h1, h2), "serif": bool}
where "h" are the handles of the segment ARRIVING at the node, and "serif" is
false for drawn nodes or an id shared by the nodes one component contributed.
"""
import math, os
import openstep_plist as op

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "geist-serif17.glyphspackage")   # this work tree's COPY of the package
REG = "DCBCDAAA-39F5-436E-B8F7-AA5CB02C428B"
SANS_SRC = "/Users/Mark/Documents/Github/geist-font/sources/Geist.glyphspackage"   # Geist Sans; Regular is a master
SANS_REG = "6C190511-B94A-4F5A-B519-D6E9DB0E7B93"

_FONTINFO = None
def _fontinfo():
    global _FONTINFO
    if _FONTINFO is None: _FONTINFO = op.load(open(os.path.join(SRC, "fontinfo.plist")), use_numbers=True)
    return _FONTINFO

def _glyph(name, src=SRC):
    return op.load(open(os.path.join(src, "glyphs", _file(name))), use_numbers=True)

def kerning(left, right):
    """Regular-master kerning for a glyph pair, Glyphs precedence: exceptions beat class pairs."""
    k = _fontinfo()["kerningLTR"].get(REG, {})
    gl, gr = _glyph(left), _glyph(right)
    L = ["@MMK_L_" + gl["kernLeft"]] if "kernLeft" in gl else []      # kernLeft = the glyph's LEFT-side group...
    R = ["@MMK_R_" + gr["kernRight"]] if "kernRight" in gr else []    # ...but Glyphs kerns by the RIGHT side of `left`
    lkeys = [left] + (["@MMK_L_" + gl["kernRight"]] if "kernRight" in gl else [])
    rkeys = [right] + (["@MMK_R_" + gr["kernLeft"]] if "kernLeft" in gr else [])
    for a in lkeys:
        for b in rkeys:
            if a in k and b in k[a]: return k[a][b]
    return 0

def advance(name):
    return _layer(name)["width"]

def _file(name):
    return "".join(c + "_" if c.isupper() else c for c in name) + ".glyph"

def _layer(name, src=SRC, reg=REG):
    g = op.load(open(os.path.join(src, "glyphs", _file(name))), use_numbers=True)
    return next(L for L in g["layers"] if L["layerId"] == reg)

def _smart_layer(name):
    g = op.load(open(os.path.join(SRC, "glyphs", _file(name))), use_numbers=True)
    cands = [L for L in g["layers"] if L.get("associatedMasterId") == REG and "coordinates" in L.get("attr", {})]
    both = [L for L in cands if min(L["attr"]["coordinates"]) > 100]     # local: Black has several; use the one extending on both axes
    for L in (both or cands)[:1]:
        return L["attr"]["coordinates"], L
    return None

def _chain(nodes, closed):
    """Glyphs node list -> on-curve nodes with their arriving handles, plus raw-index map."""
    out = []; index = {}
    for i, n in enumerate(nodes):
        if n[2][0] == "o": continue
        h = None
        if n[2][0] == "c": h = (tuple(nodes[i - 2][:2]), tuple(nodes[i - 1][:2]))
        index[i] = len(out); out.append({"pt": (float(n[0]), float(n[1])), "h": h, "serif": False})
    return out, index

def _unit(a, b):
    d = math.hypot(b[0] - a[0], b[1] - a[1]); return ((b[0] - a[0]) / d, (b[1] - a[1]) / d)
def _add(p, v, k=1.0): return (p[0] + v[0] * k, p[1] + v[1] * k)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1]
def _perp_towards(axis, side):
    p = (-axis[1], axis[0]); return p if _dot(p, side) > 0 else (axis[1], -axis[0])
def _hit(o, d, a, u):
    """s such that o + s*d lies on the line through a with direction u."""
    den = d[0] * u[1] - d[1] * u[0]
    return ((a[0] - o[0]) * u[1] - (a[1] - o[1]) * u[0]) / den

def _corner(hint, path, k):
    L = _layer(hint["name"]); nodes = L["shapes"][0]["nodes"]
    anchors = {a["name"]: a.get("pos", (0, 0)) for a in L.get("anchors", [])}
    sx, sy = hint.get("scale", (1, 1)); flipped = sx * sy < 0; sx, sy = abs(sx), abs(sy)
    smart = _smart_layer(hint["name"])
    if smart:
        # A corner with a layer at {x%, y%} is not scaled geometrically: the hint's scale
        # picks a point between the 100% drawing and that layer (T's beaks land on it exactly,
        # G's 120% x 100% serif stays the 100% drawing).
        (px, py), S = smart
        # (local: a master whose smart layer sits at 100 on an axis, e.g. Black's {100,300}, has no extent there -> t from the other axis)
        ts = [(s_ * 100 - 100) / (p_ - 100) for s_, p_ in ((sx, px), (sy, py)) if p_ != 100]
        t = max(0.0, min([1.0] + ts)) if ts else 0.0
        mix = lambda a, b: a + (b - a) * t
        nodes = [[mix(a[0], b[0]), mix(a[1], b[1]), a[2]] for a, b in zip(nodes, S["shapes"][0]["nodes"])]
        sa = {a["name"]: a.get("pos", (0, 0)) for a in S.get("anchors", [])}
        anchors = {k: (mix(v[0], sa[k][0]), mix(v[1], sa[k][1])) for k, v in anchors.items()}
        sx = sy = 1.0
    cn, _ = _chain(nodes, False)
    P = path[k]["pt"]; prev = path[k - 1]["pt"]; nxt = path[(k + 1) % len(path)]["pt"]
    assert path[k]["h"] is None and path[(k + 1) % len(path)]["h"] is None, "corner on a curved stroke"
    back, out = _unit(P, prev), _unit(P, nxt)
    X, Y = (back, out) if flipped else (out, back)          # strokes the corner's x and y sides sit on
    x_far, y_far = (prev, nxt) if flipped else (nxt, prev)
    align = hint.get("options", 0) & 3                       # 0 outstroke, 1 instroke, 2 middle
    x_rigid = (align == 1) == flipped if align < 2 else True
    if x_rigid: ex = X; ey = _perp_towards(ex, Y)
    else: ey = Y; ex = _perp_towards(ey, X)
    ly = anchors["left"][1] * sy if "left" in anchors else 0.0
    rx = anchors["right"][0] * sx if "right" in anchors else 0.0
    O = P
    if "left" in anchors and x_rigid and abs(_dot(ex, Y)) > 1e-6:
        O = _add(P, ex, _hit(_add(P, ey, ly), ex, P, Y))     # slide until `left` meets the y stroke
    if "right" in anchors and not x_rigid and abs(_dot(ey, X)) > 1e-6:
        O = _add(P, ey, _hit(_add(P, ex, rx), ey, P, X))
    T = lambda c: _add(_add(O, ex, c[0] * sx), ey, c[1] * sy)
    pts = [{"pt": T(n["pt"]), "h": n["h"] and tuple(T(h) for h in n["h"]), "serif": id(hint)} for n in cn]
    # the two ends ride their strokes, whatever angle those run at
    Lp = _add(O, ey, ly); first = cn[0]["pt"]
    if abs(_dot(ex, Y)) > 1e-6: pts[0]["pt"] = _add(Lp, Y, first[1] * sy - ly)
    Rp = _add(O, ex, rx); last = cn[-1]["pt"]
    if abs(_dot(ey, X)) > 1e-6: pts[-1]["pt"] = _add(Rp if "right" in anchors else P, X, last[0] * sx - rx)
    # an end that overshoots its stroke merges into the stroke's far node
    if _dot((pts[-1]["pt"][0] - P[0], pts[-1]["pt"][1] - P[1]), X) >= math.dist(P, x_far) - 0.5: pts.pop()
    if _dot((pts[0]["pt"][0] - P[0], pts[0]["pt"][1] - P[1]), Y) >= math.dist(P, y_far) - 0.5:
        pts[1]["h"] = None; pts.pop(0)
    if flipped:
        rev = [dict(p) for p in reversed(pts)]
        for i, p in enumerate(rev):                          # handles belong to the arriving segment
            src = pts[len(pts) - i] if i else None
            p["h"] = src["h"][::-1] if src and src["h"] else None
        pts = rev
    pts[0]["h"] = None
    return pts

def _cap(hint, path, k):
    L = _layer(hint["name"]); cn, _ = _chain(L["shapes"][0]["nodes"], False)
    a = {x["name"]: x["pos"] for x in L["anchors"]}; n1, n2 = a["node1"], a["node2"]
    P, Q = path[k]["pt"], path[(k + 1) % len(path)]["pt"]
    u = _unit(P, Q); n = (u[1], -u[0])
    sx = math.dist(P, Q) / math.dist(n1, n2); sy = hint.get("scale", (1, 1))[1]
    T = lambda c: _add(_add(P, u, (n1[0] - c[0]) * sx), n, (c[1] - n1[1]) * sy)
    pts = [{"pt": T(x["pt"]), "h": x["h"] and tuple(T(h) for h in x["h"]), "serif": id(hint)} for x in cn]
    pts[0]["h"] = path[k]["h"]
    return pts

def shapes(name, src=SRC, reg=REG):
    """-> (advance, [shape]) for the Regular master, components flattened."""
    global REG
    REG = reg                                  # _smart_layer reads the master being expanded
    L = _layer(name, src, reg); out = []; refs = []
    paths = []; maps = []
    for s in L["shapes"]:
        if "ref" in s:
            dx, dy = s.get("pos", (0, 0))
            # (work-tree change) a component's angle and scale too: Glyphs applies scale, then rotation, then pos
            sx_, sy_ = s.get("scale", (1, 1)); an = math.radians(s.get("angle", 0) or 0)
            ca, sa = math.cos(an), math.sin(an)
            def _xf(p, dx=dx, dy=dy, sx_=sx_, sy_=sy_, ca=ca, sa=sa):
                x, y = p[0] * sx_, p[1] * sy_
                return (ca * x - sa * y + dx, sa * x + ca * y + dy)
            for sh in shapes(s["ref"], src, reg)[1]:
                refs.append([{**n, "pt": _xf(n["pt"]), "h": n["h"] and tuple(_xf(h) for h in n["h"])} for n in sh])
            paths.append(None); maps.append(None)
        else:
            c, ix = _chain(s["nodes"], True); paths.append(c); maps.append(ix)
    repl = {}
    for h in L.get("hints", []):
        if h.get("type") not in ("Corner", "Cap"): continue
        pi, ni = h["origin"]; path = paths[pi]; k = maps[pi][ni]
        if h["type"] == "Corner": repl[(pi, k)] = _corner(h, path, k)
        else:
            repl[(pi, k)] = _cap(h, path, k); repl[(pi, (k + 1) % len(path))] = []
    for pi, path in enumerate(paths):
        if path is None: continue
        new = []
        for k, node in enumerate(path):
            if (pi, k) in repl:
                chain = repl[(pi, k)]
                if chain and chain[0]["h"] is None and math.dist(chain[0]["pt"], node["pt"]) < 1e-6: chain[0]["h"] = node["h"]
                new += chain
            else: new.append(node)
        out.append(new)
    REG = reg
    return L["width"], out + refs

def to_nodes(shape):
    """expanded shape (nodes carry the handles of the ARRIVING segment) -> [[x,y,type,smooth],...] with off-curves."""
    n = len(shape); res = []
    for i, nd in enumerate(shape):
        if nd["h"]:
            res.append([nd["h"][0][0], nd["h"][0][1], 'o', False]); res.append([nd["h"][1][0], nd["h"][1][1], 'o', False])
        res.append([nd["pt"][0], nd["pt"][1], 'c' if nd["h"] else 'l', False])
    # smooth: a node with a curve on at least one side whose in/out tangents are parallel and opposite-facing
    def tang(a, b):
        d = math.hypot(b[0] - a[0], b[1] - a[1]); return None if d < 1e-9 else ((b[0] - a[0]) / d, (b[1] - a[1]) / d)
    k = 0
    for i, nd in enumerate(shape):
        k += 2 if nd["h"] else 0
        nxt = shape[(i + 1) % n]; prv = shape[i - 1]
        tin = tang(nd["h"][1], nd["pt"]) if nd["h"] else tang(prv["pt"], nd["pt"])
        tout = tang(nd["pt"], nxt["h"][0]) if nxt["h"] else tang(nd["pt"], nxt["pt"])
        if (nd["h"] or nxt["h"]) and tin and tout and abs(tin[0] * tout[1] - tin[1] * tout[0]) < 2e-3 and tin[0] * tout[0] + tin[1] * tout[1] > 0:
            res[k][3] = True
        k += 1
    if res[0][2] == 'o': res = res[2:] + res[:2]      # handles precede their node, as in the file
    return res

def draw(shape_list, pen):
    for sh in shape_list:
        pen.moveTo(sh[-1]["pt"])
        for n in sh:
            if n["h"]: pen.curveTo(n["h"][0], n["h"][1], n["pt"])
            else: pen.lineTo(n["pt"])
        pen.closePath()

def silhouette(name, src=SRC, reg=REG):
    """The filled outline of the source: open corners erased, overlaps united. Still cubic."""
    import pathops
    from glyphsLib.filters.eraseOpenCorners import EraseOpenCornersPen
    p = pathops.Path(); draw(shapes(name, src, reg)[1], EraseOpenCornersPen(p.getPen()))
    p.simplify(fix_winding=True, keep_starting_points=True)
    return p

def verify(name, ttf):
    """Largest gap between the decomposed source and the exported TTF, in units."""
    import pathops
    from morph import contours_from, pt_at
    def samples(path):
        from morph import seglen
        return [pt_at(s, i / n) for c in contours_from(path) for s in c
                for n in [max(2, int(seglen(s) / 4))] for i in range(n)]
    a = silhouette(name)
    gs = ttf.getGlyphSet(); b = pathops.Path(); gs[name].draw(b.getPen(glyphSet=gs))
    b.simplify(fix_winding=True, keep_starting_points=True)
    A, B = samples(a), samples(b)
    near = lambda p, S: min(math.dist(p, q) for q in S)
    return max(max(near(p, B) for p in A), max(near(p, A) for p in B))

if __name__ == "__main__":
    import sys
    from fontTools.ttLib import TTFont
    ttf = TTFont("/Users/Mark/Dropbox (Personal)/_ClientWork/Vercel/Geist Serif/exports/GeistSerif-Regular 09-30.ttf")
    for n in sys.argv[1:]:
        print(n, "max gap %.1f units" % verify(n, ttf))

def flat_shapes(name, src=SRC, reg=REG):
    """silhouette(name) as node lists like shapes(): overlaps removed, open corners erased.
    'serif' is carried over from the source node at the same position (intersection nodes get False)."""
    from fontTools.pens.recordingPen import RecordingPen
    flags = {}
    for sh in shapes(name, src, reg)[1]:
        for nd in sh: flags[nd["pt"]] = nd["serif"]
    def flag(p):
        q = min(flags, key=lambda q: math.dist(p, q))
        return flags[q] if math.dist(p, q) <= 1.0 else False
    out = []
    for c in silhouette(name, src, reg).contours:
        pen = RecordingPen(); c.draw(pen); nodes = []; start = None
        for op, args in pen.value:
            if op == "moveTo":
                start = tuple(map(float, args[0])); nodes.append({"pt": start, "h": None})
            elif op == "lineTo":
                nodes.append({"pt": tuple(map(float, args[0])), "h": None})
            elif op == "curveTo":
                c1, c2, p = (tuple(map(float, a)) for a in args)
                nodes.append({"pt": p, "h": (c1, c2)})
        if len(nodes) > 1 and math.dist(nodes[-1]["pt"], start) < 1e-6:
            nodes[0]["h"] = nodes[-1]["h"]; nodes.pop()      # closing segment arrives at the first node
        for nd in nodes: nd["serif"] = flag(nd["pt"])
        out.append(nodes)
    return out
