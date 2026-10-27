"""wmparts: the parts-pairing and contrast-move solver (wordmark tools), as a library.

A glyph is PARTS; each part is two sides; the Illustrator blend between the sides is the part, its 50% blend the
centreline, the node-to-node rungs the measurement. The move raises contrast by translating GROUPS of nodes rigidly
away from the centreline (one vector per group), by the rules in RULES.md (R1-R26). Node count, order and handle
count never change: CNTR is deltas on the drawn points.

    import wmparts
    F = wmparts.load_glyphs("Font.glyphspackage", glyphs=["n", "e"])     # or a set.json
    g = F.get_glyph("n", "Regular")
    P = wmparts.pair(g)                    # Pairing: walls, kinds, strokes, rungs, flags, balls, unpaired
    R = wmparts.readings(P)                # per-node readings (READINGS.md format)
    M = wmparts.move(g)                    # Move: .contours_at(t), .report() (rule tags per group)
    V = wmparts.evaluate(M)                # Verdict: clean / minor / snapped / cross, snaps, spikes, tilts, thinning
    wmparts.render.groups(g, "n_groups.png")                   # PIL
    wmparts.build_variable_font(F, "vf/")                      # fontmake

The core (load a set.json, pair, readings, move, evaluate) needs numpy and scipy only (Glyphs' own Python has them);
.glyphs reading needs glyphsLib, rendering Pillow, the variable font fontTools + ufoLib2 + glyphsLib + fontmake.
"""
from .font import Glyph, Font, load_glyphs, load_set, fname, ISSUE_34
from .masters import Masters, master_info
from .parts import Parts
from .rungs import Outline
from .mover import Mover
from .groupmove import GroupMover, RULES as RULE_SWITCHES

__version__ = "0.1.0"
__all__ = ["Glyph", "Font", "Masters", "Pairing", "Move", "Verdict", "load_glyphs", "load_set", "pair", "readings",
           "move", "evaluate", "render", "build_variable_font", "fname", "master_info", "RULES_MD", "__version__"]

import os as _os
RULES_MD = _os.path.join(_os.path.dirname(__file__), "RULES.md")
DATA = _os.path.join(_os.path.dirname(__file__), "data")


def data_path(name):
    """a file shipped in wmparts/data (e.g. "harvey.masters.json", the example master values)"""
    return _os.path.join(DATA, name)


def _layer(glyph):
    if isinstance(glyph, dict):
        return glyph
    raise TypeError("a wmparts.Glyph (or a set.json layer dict), not %r" % type(glyph))


def _info(glyph, masters):
    """the master description for glyph: masters may be None (the glyph's own, attached by load_glyphs), a Masters,
    a {tag: entry} dict, a master_info() dict or a masters.json path"""
    g = _layer(glyph)
    if masters is None:
        if g.get("_mi") is None:
            raise ValueError("no master values for %s /%s: load it with load_glyphs or pass masters=" % (g.get("master"), g.get("glyph")))
        return g["_mi"]
    if isinstance(masters, (str, _os.PathLike)):
        masters = Masters.from_json(masters)
    if isinstance(masters, dict) and "stem" in masters and "A" in masters and "ia" in masters:
        return masters                                          # already a master_info() dict
    if isinstance(masters, dict):
        masters = Masters(masters)
    tag = g.tag if isinstance(g, Glyph) else (g.get("_tag") or g["master"].replace(" ", ""))
    if tag not in masters:
        if len(masters) == 1:
            tag = masters.tags[0]
        else:
            raise KeyError("no master %r in %r" % (tag, masters))
    return masters.info(tag, getattr(g, "font", None) or {"%s_%s" % (tag, g["glyph"]): g})


class Pairing:
    """The parts of one glyph (parts.Parts + rungs.Outline), read-only views:

    walls     [[segment index, ...]]: the outline split at corners (rungs.Outline.walls)
    kinds     {wall: "side" | "cut" | "notch" | "flag" | "buried" | ...} (walls not listed are sides)
    strokes   [{"A": Side, "B": Side, "walls", "mode", "rungs": [(sa, sb, kind, node_a, node_b), ...]}]
    flags     wedge / bracket / slab serifs and beaks (held, never move)
    balls     ball / teardrop terminals (rungs.Outline.balls)
    unpaired  walls that found no partner
    parts     the parts.Parts object; outline the rungs.Outline; glyph, info (the master description)"""

    def __init__(self, glyph, info):
        self.glyph = glyph
        self.info = info
        self.parts = Parts(glyph["contours"], slant=info["ia"], stem=info["stem"])
        self.outline = self.parts.ol

    walls = property(lambda self: self.outline.walls)
    kinds = property(lambda self: self.parts.kind)
    strokes = property(lambda self: self.parts.strokes)
    flags = property(lambda self: self.parts.flags)
    balls = property(lambda self: getattr(self.outline, "balls", []))
    unpaired = property(lambda self: self.parts.unpaired)

    def rungs(self):
        """every measured rung: [(stroke index, node_a, node_b, kind, width)] (width = |rung x mean tangent|)"""
        out = []
        for si, st in enumerate(self.strokes):
            for r in st["rungs"]:
                if r[0] is None or r[1] is None:
                    continue
                th = self.parts.thickness(st, r)[0]
                out.append((si, r[3], r[4], r[2], th))
        return out

    def __repr__(self):
        return "<Pairing %s · /%s: %d strokes, %d flags, %d balls, unpaired %s>" % (
            self.glyph.get("master"), self.glyph.get("glyph"), len(self.strokes), len(self.flags), len(self.balls), self.unpaired)


def pair(glyph, masters=None):
    """Pair one glyph's parts -> Pairing. masters: see Move (default: the glyph's own master values)."""
    return Pairing(_layer(glyph), _info(glyph, masters))


def readings(pairing, masters=None):
    """Per-node readings (readings/READINGS.md format): parts, walls, nodes (kind node / virt / cut / root / flag /
    start / unpaired, width, partner node, centre, tangent), unpaired sides. Takes a Pairing (or a glyph, paired
    first with masters)."""
    from .nodereadings import readings as _readings
    if not isinstance(pairing, Pairing):
        pairing = pair(pairing, masters)
    g = pairing.glyph
    return _readings(pairing.parts, g["glyph"], g["master"])


class Move(GroupMover):
    """GroupMover with the glyph it moved: contours_at(t) (t 0 = drawn, 1 = CNTR 100, linear per node, R16),
    report() (groups with their rule tags, junctions, terminals, cuts, rigid sides, ...), deltas(t)."""

    def __init__(self, glyph, masters=None, slant=None):
        self.glyph = _layer(glyph)
        super().__init__(self.glyph, masters=_info(glyph, masters), slant=slant)

    def deltas(self, t=1.0):
        """[(node index, dx, dy)] at t for every node (handles included), in the glyph's node order"""
        out = []
        for gi in sorted(self.xy):
            (x0, y0), (x1, y1) = self.xy[gi], self.new[gi]
            out.append((gi, (x1 - x0) * t, (y1 - y0) * t))
        return out

    def __repr__(self):
        return "<Move %s · /%s: A %.1f, %d groups>" % (self.glyph.get("master"), self.glyph.get("glyph"), self.A, len(self.groups))


def move(glyph, masters=None, slant=None):
    """The contrast move of one glyph -> Move (a GroupMover). masters: None (the glyph's own, from load_glyphs), a
    Masters, a {tag: entry} dict, a master_info() dict or a masters.json path."""
    return Move(glyph, masters=masters, slant=slant)


class Verdict:
    """The G2 + crossing + rung judgement of a move at CNTR 100 (curvcomb, crosscheck, rungcheck).

    verdict    "clean" | "minor" | "snapped" | "cross" (cross > snapped > minor > clean)
    snaps      smooth nodes whose curvature visibly snapped or kinked: [{node, bump, R1, kink?, ...}]
    spikes     segments whose curvature visibly spiked: [{seg: [a, b], r0, r1, ...}]
    minors     nominated but not visible; crosses: new crossings / folds (counted), infos: folds inside held serifs
    tilts      straight sides whose nodes moved by different amounts across the side (rungcheck.straight, R24)
    thinning   rungs of growing parts shorter than drawn (rungcheck.thin, R23)
    at50       the same judgement at CNTR 50; raw: curvcomb.evaluate's dict (renderers read it)"""

    def __init__(self, raw, tilts, thinning):
        from . import crosscheck
        self.raw = raw
        self.verdict = raw["verdict"]
        self.snaps, self.spikes = raw["snaps"], raw["spikes"]
        self.minors = raw["minors"] + raw["minor_spikes"]
        self.crosses = crosscheck.counted(raw.get("crosses", []))
        self.infos = crosscheck.infos(raw.get("crosses", []))
        self.tilts, self.thinning = tilts, thinning
        self.at50 = raw["at50"]["verdict"]
        self.severity = raw.get("sev", 0.0)

    clean = property(lambda self: self.verdict == "clean")

    def as_dict(self):
        return dict(verdict=self.verdict, snaps=self.snaps, spikes=self.spikes, minors=self.minors, crosses=self.crosses,
                    tilts=self.tilts, thinning=self.thinning, at50=self.at50, severity=self.severity)

    def __repr__(self):
        return "<Verdict %s: %d snaps, %d spikes, %d crosses, %d tilted sides, %d thinned rungs>" % (
            self.verdict, len(self.snaps), len(self.spikes), len(self.crosses), len(self.tilts), len(self.thinning))


def evaluate(mv, glyph=None):
    """Judge a move -> Verdict. mv: a Move (or any GroupMover / Mover with contours_at; then pass glyph)."""
    from . import curvcomb, rungcheck
    g = glyph if glyph is not None else getattr(mv, "glyph", None) or mv.g
    raw = curvcomb.evaluate(g, mv)
    raw["key"] = g.key if isinstance(g, Glyph) else None
    tilts = rungcheck.straight(mv) if isinstance(mv, GroupMover) else []
    thinning = rungcheck.thin(mv) if isinstance(mv, GroupMover) else []
    return Verdict(raw, tilts, thinning)


def build_variable_font(font, out_dir, axis="CNTR", erase_open_corners=True, **kw):
    """CNTR 0 = drawn, CNTR 100 = moved: UFOs + designspace + fontmake VF + instances (wmparts.vf; fontmake needed).
    kw: master, glyphs, t, family_name, reference_ttf, instances (see vf.build_variable_font)."""
    from .vf import build_variable_font as _b
    return _b(font, out_dir, axis=axis, erase_open_corners=erase_open_corners, **kw)


class _LazyRender:
    """wmparts.render: imported on first use (Pillow)"""

    def __getattr__(self, name):
        import importlib
        mod = importlib.import_module(".render", __name__)
        globals()["render"] = mod
        return getattr(mod, name)


render = _LazyRender()
