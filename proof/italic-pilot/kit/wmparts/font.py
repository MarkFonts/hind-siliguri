"""Glyph layers and fonts as the solver reads them.

A layer is the set.json record: {"contours": [{"closed": bool, "nodes": [[x, y, type, smooth], ...]}, ...],
"width", "master", "glyph"} with type "l" (line), "c" (curve), "o" (off-curve) and the nodes in file order
(off-curves before the on-curve they arrive at). Node numbers are the indices counted across contours.

Glyph is that dict with attributes; Font is {key: Glyph} (key = "<tag>_<glyph>", tag = master tag) plus the
per-master values (masters.Masters). Every Glyph of a Font carries g["_mi"] (its master description) and
g["family"] (the label every sheet title starts with), so the solver classes take a Glyph directly.
"""
import json, os

from .masters import Masters

ISSUE_34 = "https://github.com/MarkFonts/wordmarktools/issues/34"


def fname(key):
    """file-safe key on a case-insensitive disk (the UFO glyph-file convention): every capital in the glyph name gets a
    trailing _ (HSBlack_E -> HSBlack_E_, H_a_r_v_e_y stays readable). A bare glyph name works too (E -> E_)."""
    tag, sep, gl = key.partition("_")
    if not sep:
        return "".join(c + "_" if c.isupper() else c for c in key)
    return tag + "_" + "".join(c + "_" if c.isupper() else c for c in gl)


class Glyph(dict):
    """One glyph in one master: the set.json dict, with attributes.

    name, master (the master's name), tag (master tag), key ("<tag>_<name>"), family, width,
    contours ([{"closed", "nodes": [[x, y, type, smooth], ...]}]), info (the master description or None)."""

    @classmethod
    def make(cls, name, master, contours, width=0.0, tag=None, family=""):
        g = cls(contours=contours, width=float(width), master=master, glyph=name)
        g["family"] = family
        g["_tag"] = tag if tag is not None else master.replace(" ", "")
        return g

    name = property(lambda self: self["glyph"])
    master = property(lambda self: self["master"])
    contours = property(lambda self: self["contours"])
    width = property(lambda self: self.get("width", 0.0))
    family = property(lambda self: self.get("family", ""))
    info = property(lambda self: self.get("_mi"))

    @property
    def tag(self):
        return self.get("_tag") or self.master.replace(" ", "")

    @property
    def key(self):
        return "%s_%s" % (self.tag, self.name)

    def nodes(self):
        """every node, numbered as the solver numbers them: [(index, contour index, [x, y, type, smooth])]"""
        out, i = [], 0
        for ci, c in enumerate(self.contours):
            for n in c["nodes"]:
                out.append((i, ci, n)); i += 1
        return out

    def as_record(self):
        """the plain set.json record (no private keys)"""
        return {k: v for k, v in self.items() if not k.startswith("_") and k != "family"}

    def __repr__(self):
        return "<Glyph %s · /%s, %d contours>" % (("%s %s" % (self.family, self.master)).strip(), self.name, len(self.contours))


class Font(dict):
    """{key: Glyph} for one family, key = "<tag>_<glyph>"; .masters (Masters), .family (label), .source (path).

        F.get_glyph("e", "Regular")   by glyph name and master name (or tag)
        F.layers(master=None)          Glyphs sorted by key
        F.tags                         master tags present
        F.to_json(path)                writes set.json (+ <set>.masters.json beside it)
    """

    def __init__(self, glyphs=(), masters=None, family="", source=None):
        super().__init__()
        self.masters = masters if masters is not None else Masters()
        self.family = family
        self.source = source
        for g in glyphs:
            self[g.key] = g

    def attach(self):
        """(re)compute every layer's master description from self.masters; layers whose tag has no entry keep none"""
        for key, g in self.items():
            tag = g.tag
            if isinstance(g, Glyph):
                g.font = self
            if tag in self.masters:
                g["_mi"] = self.masters.info(tag, self)
                fam = self.masters[tag].get("family")
                if fam and not g.get("family"):
                    g["family"] = fam
            if not g.get("family") and self.family:
                g["family"] = self.family
        return self

    def get_glyph(self, name, master):
        for g in self.values():
            if g.name == name and (g.master == master or g.tag == master):
                return g
        raise KeyError("/%s in master %s" % (name, master))

    def layers(self, master=None):
        return [self[k] for k in sorted(self) if master is None or self[k].master == master or self[k].tag == master]

    @property
    def tags(self):
        out = []
        for k in sorted(self):
            t = self[k].tag
            if t not in out:
                out.append(t)
        return out

    def to_json(self, path):
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump({k: g.as_record() for k, g in self.items()}, open(path, "w"))
        if len(self.masters):
            self.masters.to_json(path[:-5] + ".masters.json" if path.endswith(".json") else path + ".masters.json")

    def __repr__(self):
        return "<Font %s: %d layers, masters %s>" % (self.family or "?", len(self), ", ".join(self.masters.tags))


def _as_masters(m):
    if m is None or isinstance(m, Masters):
        return m
    if isinstance(m, (str, os.PathLike)):
        return Masters.from_json(m)
    if isinstance(m, dict):
        return Masters(m)
    raise TypeError("master values: a Masters, a {tag: entry} dict or a masters.json path, not %r" % type(m))


def load_set(path, masters=None):
    """A set.json as a Font. masters: a Masters / {tag: entry} / masters.json path; default <set>.masters.json beside it
    when present (without one the layers carry no master description and move() asks for one)."""
    raw = json.load(open(path))
    G = Font(source=path)
    for key, r in raw.items():
        g = Glyph(r)
        tag = key.split("_")[0]
        g["_tag"] = tag
        g.setdefault("family", "")
        G[key] = g
    M = _as_masters(masters)
    if M is None:
        mp = path[:-5] + ".masters.json" if path.endswith(".json") else None
        if mp and os.path.exists(mp):
            M = Masters.from_json(mp)
    if M is not None:
        G.masters = M
        fams = {e.get("family") for e in M.entries.values() if e.get("family")}
        if len(fams) == 1:
            G.family = fams.pop()
    return G.attach()


def load_glyphs(path, glyphs=None, masters=None, master_values=None, keep_components=False):
    """Load a font for the solver -> Font.

    path            a .glyphs / .glyphspackage (needs glyphsLib; corner and cap components are expanded into points), or
                    a set.json (the solver's JSON; its <set>.masters.json beside it is read when present)
    glyphs          glyph names to load (default: every glyph with outlines); for a source the measuring letters
                    (H n f k j e) are read as well to measure the masters, then dropped unless asked for
    masters         master names (or tags) to load (default all)
    master_values   the master values: a Masters or a masters.json path REPLACES the measured / sidecar ones; a
                    {tag: {key: value}} dict is merged over them (e.g. {"GeistSerifRegular": {"A": 30}})
    keep_components reserved: keep components as references instead of decomposing them (issue #34)
    """
    if keep_components:
        raise NotImplementedError("keep_components=True is not built yet: see %s" % ISSUE_34)
    p = str(path).rstrip("/")
    if p.endswith(".json"):
        F = load_set(p, masters=None if isinstance(master_values, dict) else master_values)
    elif p.endswith(".glyphs") or p.endswith(".glyphspackage"):
        from .glyphsfile import load_source
        F = load_source(p, glyphs=glyphs, masters=masters)
        if master_values is not None and not isinstance(master_values, dict):
            F.masters = _as_masters(master_values); F.attach()
    else:
        raise ValueError("load_glyphs: a .glyphs, .glyphspackage or set .json, not %s" % path)
    if isinstance(master_values, dict):
        F.masters = F.masters.with_overrides(master_values); F.attach()
    if glyphs is not None or masters is not None:
        keep = [k for k, g in F.items() if (glyphs is None or g.name in glyphs)
                and (masters is None or g.master in masters or g.tag in masters)]
        for k in list(F):
            if k not in keep:
                del F[k]
    return F

