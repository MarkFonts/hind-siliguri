"""Master values: stems, zones, italic angle, metric lines and the move amount A, per master.

A masters entry (one per master tag, the `<set>.masters.json` format written by mk_masters / `wmparts masters`) is
the .glyphs master's own numbers where it defines them, MEASURED from the letters otherwise:
  "ia" italic angle, "upm", "V"/"H" vertical/horizontal stems, "Z" zones [[position, size], ...],
  "xHeight", "capHeight", "ascender", "descender", plus "Vm"/"Hm" (measured from the H), "measured" (cap / x /
  ascender / descender / baseline read off the letters), "file" (the raw .glyphs values), "src" (where each came
  from), "missing" (what could not be measured), "master" (the master's name), "family" (label for the sheets).
Optional overrides an entry may carry (they win over measuring): "stem" (a number, or "file" = min(V) x cos(ia)
instead of the n measured at half x-height), "A" (the move amount at CNTR 100), "thin_top" (the hairline),
"lines_lc" / "lines_uc" (metric lines), "x_height" / "cap_height".

master_info(tag, entry, glyphs) turns an entry into what the solver reads (the Mover's master description):
  dict(tag, ia, stem, A, thin_top, lines_lc, lines_uc, x_height, cap_height)
numpy-free; no font libraries.
"""
import json, math

# CONTRAST-SPEC.md gives A per Harvey master but no derivation (Regular 28 is 0.30 x its measured n stem, Black 44.8
# is 1.6 x Regular = 0.26 x its stem). For another face A keeps Harvey Regular's ratio to the stem:
# A = 28 x (the master's measured n stem) / 92 (Harvey Regular's measured n stem).
A_RATIO = 28.0 / 92.0


def flat(contour, n=12):
    """flatten a closed contour [[x,y,t,s]..] to a polyline (cubic order = file order, offcurves precede their oncurve)."""
    nodes = contour["nodes"]; N = len(nodes); pts = []
    on = [i for i, nd in enumerate(nodes) if nd[2] != 'o']
    if not on: return pts
    for k, i in enumerate(on):
        j = on[(k + 1) % len(on)]
        # offcurves between i and j (walking forward)
        offs = []; t = (i + 1) % N
        while t != j: offs.append(nodes[t]); t = (t + 1) % N
        p0 = nodes[i]; p3 = nodes[j]
        if len(offs) == 2:
            for s in range(n):
                u = s / n
                a = (1 - u) ** 3; b = 3 * u * (1 - u) ** 2; c = 3 * u * u * (1 - u); d = u ** 3
                pts.append((a * p0[0] + b * offs[0][0] + c * offs[1][0] + d * p3[0], a * p0[1] + b * offs[0][1] + c * offs[1][1] + d * p3[1]))
        else:
            pts.append((p0[0], p0[1]))
    return pts


def scan_y(cs, y):
    xs = []
    for c in cs:
        P = flat(c)
        for (x0, y0), (x1, y1) in zip(P, P[1:] + P[:1]):
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) / (y1 - y0) * (x1 - x0))
    xs.sort(); return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


def scan_x(cs, x):
    ys = []
    for c in cs:
        P = flat(c)
        for (x0, y0), (x1, y1) in zip(P, P[1:] + P[:1]):
            if (x0 <= x < x1) or (x1 <= x < x0):
                ys.append(y0 + (x - x0) / (x1 - x0) * (y1 - y0))
    ys.sort(); return [(ys[i], ys[i + 1]) for i in range(0, len(ys) - 1, 2)]


def hflat(cs, top):
    """y of the extreme node that is an end of a horizontal line segment (the flat serif/baseline), else None"""
    best = None
    for c in cs:
        nd = c["nodes"]; N = len(nd)
        for i in range(N):
            a, b = nd[i], nd[(i + 1) % N]
            if b[2] == 'l' and abs(a[1] - b[1]) < 0.5 and a[2] != 'o':
                y = a[1]
                if best is None or (y > best if top else y < best): best = y
    e = max(n[1] for c in cs for n in c["nodes"]) if top else min(n[1] for c in cs for n in c["nodes"])
    return best if best is not None and abs(best - e) <= 30 else None


def ext(cs, top):
    ys = [n[1] for c in cs for n in c["nodes"]]
    return max(ys) if top else min(ys)


def measure(G, tag):
    out = {"missing": []}
    H = G.get(tag + "_H")
    if H:
        cs = H["contours"]; cap = ext(cs, True); out["capHeight"] = cap; out["baseline"] = ext(cs, False)
        out["capFlat"] = hflat(cs, True)
        ys = sorted(set(round(n[1]) for c in cs for n in c["nodes"]))
        yy = 0.75 * cap
        iv = [(a, b) for a, b in scan_y(cs, yy)]
        wid = [b - a for a, b in iv]
        # stems = the two widest-in-the-outer-pair intervals; drop anything wider than 3x the median (merged crossbar)
        out["Vm"] = [round(w, 1) for w in wid] if len(wid) == 2 else None
        if out["Vm"] is None: out["missing"].append("V: %d intervals at 0.75 cap" % len(wid))
        if len(iv) >= 2:
            cx = (iv[0][1] + iv[-1][0]) / 2
            bars = scan_x(cs, cx)
            mid = [(a, b) for a, b in bars if 0.2 * cap < (a + b) / 2 < 0.8 * cap]
            out["Hm"] = [round(b - a, 1) for a, b in mid] if mid else None
            if not mid: out["missing"].append("H: no crossbar at centre x")
        else:
            out["Hm"] = None
    else:
        out["missing"].append("no H layer: V/H not measurable")
    n = G.get(tag + "_n")
    if n:
        out["xHeight"] = ext(n["contours"], True); out["xFlat"] = hflat(n["contours"], True)
    else: out["missing"].append("no n layer: x-height")
    asc = [ext(G[k]["contours"], True) for k in (tag + "_f", tag + "_k") if k in G]
    out["ascender"] = max(asc) if asc else None
    if not asc: out["missing"].append("no f/k layer: ascender")
    if tag + "_j" in G:
        out["descender"] = ext(G[tag + "_j"]["contours"], False); out["descFlat"] = hflat(G[tag + "_j"]["contours"], False)
    else: out["missing"].append("no j layer: descender")
    e = G.get(tag + "_e")
    if e:
        out["e_top"] = ext(e["contours"], True); out["e_bot"] = ext(e["contours"], False)
    zm = []
    def add(pos, ov):
        if pos is not None: zm.append([float(pos), float(ov)])
    if out.get("ascender") is not None: add(out["ascender"], 0)
    if out.get("capFlat") is not None: add(out["capFlat"], 0)
    xf = out.get("xFlat") if out.get("xFlat") is not None else out.get("xHeight")
    if xf is not None: add(xf, (out["e_top"] - xf) if "e_top" in out else 0)
    if out.get("baseline") is not None: add(0, (out["e_bot"] if "e_bot" in out else 0))
    if out.get("descender") is not None: add(out["descender"], 0)
    out["Zm"] = zm
    return out



def master_info(tag, entry, G):
    """A font-agnostic master description for Mover, from a masters entry and the set's own letters (G: key -> layer,
    keys "<tag>_<glyph>"): stem = the n's thinner stem measured across at half x-height (x cos italic angle),
    hairline = the file's horizontal stems (else the measured H bar), metric lines from the letters
    (the file's are stale in Geist), A = A_RATIO x stem. The entry's overrides (module doc) win."""
    ia = float(entry.get("ia", 0.0))
    meas = entry.get("measured", {}) or {}
    stem = entry.get("stem")
    if stem == "file":
        stem = min(entry.get("V") or entry.get("Vm")) * math.cos(math.radians(ia))
    elif stem is not None:
        stem = float(stem)
    n = G.get(tag + "_n") if stem is None else None
    if n:
        cs = n["contours"]; top = max(nd[1] for c in cs for nd in c["nodes"])
        iv = scan_y(cs, 0.5 * top)
        if iv:
            stem = min(b - a for a, b in iv) * math.cos(math.radians(ia))
    if stem is None:
        vm = entry.get("Vm") or entry.get("V")
        if not vm:
            raise ValueError("master %s: no n to measure the stem and no V stems in its entry" % tag)
        stem = min(vm) * math.cos(math.radians(ia))
    H = entry.get("H") or entry.get("Hm") or [0.3 * stem]
    xh = meas.get("xFlat") or meas.get("xHeight") or entry.get("xHeight")
    cap = meas.get("capFlat") or meas.get("capHeight") or entry.get("capHeight")
    asc = meas.get("ascender") or entry.get("ascender")
    desc = meas.get("descender") or entry.get("descender")
    lc = sorted({float(v) for v in (asc, xh, 0.0, desc) if v is not None}, reverse=True)
    uc = sorted({float(v) for v in (cap, 0.0) if v is not None}, reverse=True)
    out = dict(tag=tag, ia=ia, stem=float(stem), A=round(A_RATIO * stem, 1), thin_top=float(max(H)),
               lines_lc=lc, lines_uc=uc, x_height=float(xh) if xh is not None else None,
               cap_height=float(cap) if cap is not None else None)
    for k in ("A", "thin_top", "x_height", "cap_height"):
        if entry.get(k) is not None:
            out[k] = float(entry[k])
    for k in ("lines_lc", "lines_uc"):
        if entry.get(k) is not None:
            out[k] = [float(v) for v in entry[k]]
    return out


def slant_stem(g):
    """(slant, stem) of a layer as Mover sees them, from its master description g["_mi"]"""
    mi = g.get("_mi")
    if mi is None:
        raise ValueError("no master values for %s /%s: load it with wmparts.load_glyphs (or pass masters=)" % (g.get("master"), g.get("glyph")))
    return mi["ia"], mi["stem"]


def tag_of(G, master):
    """the tag of the layers of master (a master name or a tag) in a set {key: layer}"""
    for k, g in G.items():
        if g.get("master") == master or k.split("_")[0] == master:
            return k.split("_")[0]
    return master.replace(" ", "")


def file_entry(master, upm, meas):
    """a masters entry from a glyphsLib GSFontMaster (or any object with the same attributes) and measure()'s output:
    the file's values where defined, the measured ones otherwise (mk_masters.py's rules)."""
    file = {"horizontalStems": list(master.horizontalStems or []), "verticalStems": list(master.verticalStems or []),
            "zones": [[z.position, z.size] for z in (master.alignmentZones or [])],
            "xHeight": master.xHeight, "capHeight": master.capHeight, "ascender": master.ascender,
            "descender": master.descender, "italicAngle": master.italicAngle}
    return values_entry(master.name, upm, file, meas)


def values_entry(name, upm, file, meas=None):
    """a masters entry from plain values: file = dict(verticalStems, horizontalStems, zones, xHeight, capHeight,
    ascender, descender, italicAngle) (any may be missing / None), meas = measure() output or None."""
    measured = meas is not None
    meas = meas or {"missing": [], "Zm": []}
    file = dict(file)
    for k in ("horizontalStems", "verticalStems", "zones"):
        file[k] = list(file.get(k) or [])
    for k in ("xHeight", "capHeight", "ascender", "descender", "italicAngle"):
        file.setdefault(k, None)
    r = {"master": name, "ia": float(file["italicAngle"] or 0.0), "upm": float(upm)}
    srcs = {"ia": "file", "upm": "file"}
    for key, fk, mk in (("V", "verticalStems", "Vm"), ("H", "horizontalStems", "Hm")):
        if file[fk]:
            r[key] = [float(v) for v in file[fk]]; srcs[key] = "file"
        elif meas.get(mk):
            r[key] = sorted(meas[mk]); srcs[key] = "measured (file has none)"
        else:
            r[key] = []; srcs[key] = "unavailable"
    r["Z"] = [[float(a), float(b)] for a, b in file["zones"]]; srcs["Z"] = "file"
    for k in ("xHeight", "capHeight", "ascender", "descender"):
        r[k] = float(file[k]) if file[k] is not None else None; srcs[k] = "file"
    r["src"] = srcs; r["file"] = file
    if measured:
        _put_measured(r, meas)
    return r


MEASURED = ("capHeight", "capFlat", "xHeight", "xFlat", "ascender", "descender", "descFlat", "baseline", "e_top", "e_bot")


def _put_measured(r, meas):
    r["Vm"], r["Hm"] = meas.get("Vm"), meas.get("Hm")
    r["measured"] = {k: meas.get(k) for k in MEASURED}
    r["Zm"] = meas.get("Zm", [])
    r["missing"] = meas.get("missing", [])
    if not r.get("V") and r["Vm"]:
        r["V"] = sorted(r["Vm"]); r["src"]["V"] = "measured (file has none)"
    if not r.get("H") and r["Hm"]:
        r["H"] = sorted(r["Hm"]); r["src"]["H"] = "measured (file has none)"


class Masters:
    """Per-master values for one font, keyed by master TAG (the "<tag>" of the layer keys "<tag>_<glyph>").

        Masters(entries)                    entries: {tag: masters entry} (module doc)
        Masters.from_json(path)             a <set>.masters.json
        Masters.from_values(tag, ...)       one master from plain numbers (a Glyphs plugin's GSFontMaster)
        M.with_overrides({tag: {...}})      a copy with entry keys replaced (e.g. {"Regular": {"A": 30}})
        M.info(tag, glyphs)                 the solver's master description (master_info), cached per tag
        M.entries, M.tags, M[tag], tag in M, M.to_json(path)
    """

    def __init__(self, entries=None):
        self.entries = {t: dict(e) for t, e in (entries or {}).items()}
        self._info = {}

    @classmethod
    def from_json(cls, path):
        return cls(json.load(open(path)))

    @classmethod
    def from_values(cls, tag, italic_angle=0.0, V=(), H=(), xHeight=None, capHeight=None, ascender=None,
                    descender=None, zones=(), upm=1000, name=None, **overrides):
        """one master from the numbers a font editor shows (Glyphs: GSFontMaster.verticalStems, horizontalStems,
        xHeight, capHeight, ascender, descender, italicAngle, alignmentZones). overrides: stem, A, thin_top, family..."""
        e = values_entry(name or tag, upm, dict(verticalStems=list(V), horizontalStems=list(H), zones=[list(z) for z in zones],
                                                xHeight=xHeight, capHeight=capHeight, ascender=ascender,
                                                descender=descender, italicAngle=italic_angle))
        e.update(overrides)
        return cls({tag: e})

    def with_overrides(self, over):
        E = {t: dict(e) for t, e in self.entries.items()}
        for t, d in (over or {}).items():
            E.setdefault(t, {}).update(d)
        return Masters(E)

    @property
    def tags(self):
        return list(self.entries)

    def __contains__(self, tag):
        return tag in self.entries

    def __getitem__(self, tag):
        return self.entries[tag]

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def info(self, tag, glyphs=None):
        """master_info for tag; glyphs (key -> layer) supplies the n the stem is measured on. An entry without a
        "measured" block (Masters.from_values) is measured here first from the letters given (H n f k j e:
        metric lines, and the stems when the file has none); "measured": {} means use the entry's numbers as they are."""
        if tag not in self._info:
            e = self.entries[tag]
            if "measured" not in e and glyphs:
                _put_measured(e, measure(glyphs, tag))
            self._info[tag] = master_info(tag, e, glyphs or {})
        return self._info[tag]

    def to_json(self, path):
        json.dump(self.entries, open(path, "w"), indent=1)

    def __repr__(self):
        return "Masters(%s)" % ", ".join(self.entries)
