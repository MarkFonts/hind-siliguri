"""Glyphs 3 corner and cap components expanded into real points (Geist Serif's serifs are corner components).

Derived from geist-serif-morf/svg/source.py (the verified corner + cap decomposition for Geist Serif), made source-
independent for wmparts: a GlyphsSource reads a .glyphspackage or a Glyphs-3 .glyphs file with openstep_plist, and
every function takes the source and the master id. Placement rules were derived from, and checked against, Glyphs'
exported TTF (verify(); Regular H 12 -> 60 nodes, < 1% XOR). glyphsLib's own corner filter gets these fonts wrong
(no caps, no left/right anchors).

A shape is a closed list of nodes: {"pt", "h": None | (h1, h2), "serif": bool | id} where "h" are the handles of the
segment ARRIVING at the node, and "serif" is false for drawn nodes or an id shared by the nodes one component
contributed. to_nodes(shape) -> the solver's [[x, y, type, smooth], ...] (handles before their node).
Needs openstep_plist (installed with glyphsLib); silhouette / verify also need skia-pathops and fontTools.
"""
import math, os
import openstep_plist as op


def glyph_file(name):
    """a .glyphspackage glyph file name (UFO-style: every capital gets a trailing _)"""
    return "".join(c + "_" if c.isupper() else c for c in name) + ".glyph"


class GlyphsSource:
    """glyph dicts by name from a .glyphspackage (glyphs/<name>.glyph) or a Glyphs-3 .glyphs file"""

    def __init__(self, path):
        self.path = str(path).rstrip("/")
        self.package = self.path.endswith(".glyphspackage")
        self._glyphs = {}
        self._all = None
        self._fontinfo = None
        self._warned = set()

    def fontinfo(self):
        if self._fontinfo is None:
            if self.package:
                self._fontinfo = op.load(open(os.path.join(self.path, "fontinfo.plist")), use_numbers=True)
            else:
                self._load_all(); self._fontinfo = self._file
        return self._fontinfo

    def _load_all(self):
        if self._all is None:
            self._file = op.load(open(self.path), use_numbers=True)
            if int(self._file.get(".formatVersion", 2)) < 3:
                raise ValueError("%s is a Glyphs 2 file: corner components are read from Glyphs 3 sources only" % self.path)
            self._all = {g["glyphname"]: g for g in self._file.get("glyphs", [])}

    def glyph(self, name):
        if name not in self._glyphs:
            if self.package:
                self._glyphs[name] = op.load(open(os.path.join(self.path, "glyphs", glyph_file(name))), use_numbers=True)
            else:
                self._load_all(); self._glyphs[name] = self._all[name]
        return self._glyphs[name]

    def layer(self, name, reg):
        return next(L for L in self.glyph(name)["layers"] if L["layerId"] == reg)

    def master_axes(self):
        """{master id: [axis values]} from the font info"""
        return {m["id"]: list(m.get("axesValues", [])) for m in self.fontinfo().get("fontMaster", [])}

    def corner_layer(self, name, reg):
        """a corner / cap component's layer for master reg; when that master's layer is empty (a source whose
        other masters are unfinished), the layer of the NEAREST master (axis values) that has one, with a warning"""
        L = next((L for L in self.glyph(name)["layers"] if L["layerId"] == reg), None)
        if L is not None and L.get("shapes"):
            return L
        ax = self.master_axes(); here = ax.get(reg, [])
        drawn = [L for L in self.glyph(name)["layers"] if L["layerId"] in ax and L.get("shapes")]
        if not drawn:
            raise KeyError("corner component %s has no drawn master layer" % name)
        dist = lambda L: sum((a - b) ** 2 for a, b in zip(ax[L["layerId"]], here))
        best = min(drawn, key=dist)
        key = (name, reg)
        if key not in self._warned:
            self._warned.add(key)
            print("WARN corner component %s: master %s has no drawing, using master %s's" % (name, reg, best["layerId"]))
        return best

    def smart_layer(self, name, reg):
        cands = [L for L in self.glyph(name)["layers"] if L.get("associatedMasterId") == reg and "coordinates" in L.get("attr", {})]
        both = [L for L in cands if min(L["attr"]["coordinates"]) > 100]     # Black has several; use the one extending on both axes
        for L in (both or cands)[:1]:
            return L["attr"]["coordinates"], L
        return None

    def has_corners(self, name, reg, depth=0):
        """does this layer (or a component it uses) carry Corner / Cap hints?"""
        try:
            L = self.layer(name, reg)
        except (StopIteration, KeyError, FileNotFoundError):
            return False
        if any(h.get("type") in ("Corner", "Cap") for h in L.get("hints", [])):
            return True
        return depth < 4 and any(self.has_corners(s["ref"], reg, depth + 1) for s in L.get("shapes", []) if "ref" in s)


_SOURCES = {}


def source(src):
    if isinstance(src, GlyphsSource):
        return src
    key = str(src).rstrip("/")
    if key not in _SOURCES:
        _SOURCES[key] = GlyphsSource(key)
    return _SOURCES[key]


def advance(name, src, reg):
    return source(src).layer(name, reg)["width"]


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

def _corner(hint, path, k, S, reg):
    L = S.corner_layer(hint["name"], reg); nodes = L["shapes"][0]["nodes"]
    anchors = {a["name"]: a.get("pos", (0, 0)) for a in L.get("anchors", [])}
    sx, sy = hint.get("scale", (1, 1)); flipped = sx * sy < 0; sx, sy = abs(sx), abs(sy)
    smart = S.smart_layer(hint["name"], reg)
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

def _cap(hint, path, k, S, reg):
    L = S.corner_layer(hint["name"], reg); cn, _ = _chain(L["shapes"][0]["nodes"], False)
    a = {x["name"]: x["pos"] for x in L["anchors"]}; n1, n2 = a["node1"], a["node2"]
    P, Q = path[k]["pt"], path[(k + 1) % len(path)]["pt"]
    u = _unit(P, Q); n = (u[1], -u[0])
    sx = math.dist(P, Q) / math.dist(n1, n2); sy = hint.get("scale", (1, 1))[1]
    T = lambda c: _add(_add(P, u, (n1[0] - c[0]) * sx), n, (c[1] - n1[1]) * sy)
    pts = [{"pt": T(x["pt"]), "h": x["h"] and tuple(T(h) for h in x["h"]), "serif": id(hint)} for x in cn]
    pts[0]["h"] = path[k]["h"]
    return pts

def shapes(name, src, reg):
    """-> (advance, [shape]) for master id reg, corner / cap components expanded, components flattened (translated
    by their position: drawn paths first, then component refs, the order the solver's JSON always used).
    src: a .glyphspackage / Glyphs-3 .glyphs path or a GlyphsSource."""
    S = source(src)
    L = S.layer(name, reg); out = []; refs = []
    paths = []; maps = []
    for s in L["shapes"]:
        if "ref" in s:
            dx, dy = s.get("pos", (0, 0))
            for sh in shapes(s["ref"], S, reg)[1]:
                refs.append([{**n, "pt": _add(n["pt"], (dx, dy)), "h": n["h"] and tuple(_add(h, (dx, dy)) for h in n["h"])} for n in sh])
            paths.append(None); maps.append(None)
        else:
            c, ix = _chain(s["nodes"], True); paths.append(c); maps.append(ix)
    repl = {}
    for h in L.get("hints", []):
        if h.get("type") not in ("Corner", "Cap"): continue
        pi, ni = h["origin"]; path = paths[pi]; k = maps[pi][ni]
        if h["type"] == "Corner": repl[(pi, k)] = _corner(h, path, k, S, reg)
        else:
            repl[(pi, k)] = _cap(h, path, k, S, reg); repl[(pi, (k + 1) % len(path))] = []
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

def silhouette(name, src, reg):
    """The filled outline of the source: open corners erased, overlaps united. Still cubic."""
    import pathops
    from glyphsLib.filters.eraseOpenCorners import EraseOpenCornersPen
    p = pathops.Path(); draw(shapes(name, src, reg)[1], EraseOpenCornersPen(p.getPen()))
    p.simplify(fix_winding=True, keep_starting_points=True)
    return p


def _samples(path, step=4.0):
    """points every ~step units along a pathops path"""
    from fontTools.pens.recordingPen import RecordingPen
    rp = RecordingPen(); path.draw(rp); pts = []; cur = start = None
    for verb, args in rp.value:
        if verb == "moveTo":
            cur = start = tuple(args[0])
        elif verb == "lineTo":
            p = tuple(args[0]); n = max(2, int(math.dist(cur, p) / step))
            pts += [(cur[0] + (p[0] - cur[0]) * i / n, cur[1] + (p[1] - cur[1]) * i / n) for i in range(n)]; cur = p
        elif verb == "curveTo":
            c1, c2, p = (tuple(a) for a in args)
            n = max(2, int((math.dist(cur, c1) + math.dist(c1, c2) + math.dist(c2, p)) / step))
            for i in range(n):
                t = i / n; u = 1 - t
                pts.append((u ** 3 * cur[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p[0],
                            u ** 3 * cur[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p[1]))
            cur = p
        elif verb in ("closePath", "endPath") and cur is not None and start is not None:
            n = max(2, int(math.dist(cur, start) / step))
            pts += [(cur[0] + (start[0] - cur[0]) * i / n, cur[1] + (start[1] - cur[1]) * i / n) for i in range(n)]
    return pts


def verify(name, src, reg, ttf):
    """Largest gap (units) between the decomposed source and an exported TTF's glyph (ttf: a path or a TTFont)."""
    import pathops
    from fontTools.ttLib import TTFont
    if not hasattr(ttf, "getGlyphSet"):
        ttf = TTFont(ttf)
    a = silhouette(name, src, reg)
    gs = ttf.getGlyphSet(); b = pathops.Path(); gs[name].draw(b.getPen(glyphSet=gs))
    b.simplify(fix_winding=True, keep_starting_points=True)
    A, B = _samples(a), _samples(b)
    near = lambda p, S: min(math.dist(p, q) for q in S)
    return max(max(near(p, B) for p in A), max(near(p, A) for p in B))


def flat_shapes(name, src, reg):
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
