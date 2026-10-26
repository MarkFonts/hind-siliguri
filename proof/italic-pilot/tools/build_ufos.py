"""pick the level per glyph (A full ruleset, B re-tension off, C plain slant: the highest level that passes the comb gate
in BOTH masters), then write the italic UFOs from the snapshot (glyphsLib keeps features, groups, kerning, glyph order)
with the outlines, anchors and component offsets replaced. Run with the gfvenv python."""
import os, sys, json, glyphsLib, ufoLib2
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor, InstanceDescriptor
HERE = os.path.dirname(os.path.abspath(__file__)); PILOT = os.path.dirname(HERE); W = os.path.join(PILOT, "work")
K = 0.25; YC = 253.5; SHIFT = -K * YC
UP = {m: json.load(open(os.path.join(W, "upright_%s.json" % m))) for m in ("Light", "Bold")}
RA = {m: json.load(open(os.path.join(W, "results_%s.json" % m))) for m in ("Light", "Bold")}
RB = {m: json.load(open(os.path.join(W, "results_B_%s.json" % m))) for m in ("Light", "Bold")}
RC = {m: json.load(open(os.path.join(W, "results_C_%s.json" % m))) for m in ("Light", "Bold")}

import math
def finite(cs):
    return all(math.isfinite(n[0]) and math.isfinite(n[1]) for c in cs for n in c["nodes"])

def passes(R, gl):
    return all(gl in R[m] and R[m][gl]["ok"] and R[m][gl]["gate"]["ok"] and finite(R[m][gl]["contours"]) for m in R)

level = {}
for gl, g in UP["Light"].items():
    if not g["contours"]:
        level[gl] = "composite" if g["components"] else "empty"
    elif passes(RA, gl):
        level[gl] = "A"
    elif passes(RB, gl):
        level[gl] = "B"
    elif passes(RC, gl):
        level[gl] = "C"
    else:
        # no level passes in both masters: each master takes its own highest passing level (marked mixed)
        per = []
        for m in ("Light", "Bold"):
            lv = next((L for L, R in (("A", RA), ("B", RB), ("C", RC)) if gl in R[m] and R[m][gl]["ok"] and R[m][gl]["gate"]["ok"] and finite(R[m][gl]["contours"])), "D")
            per.append(lv)
        level[gl] = "D" if per == ["D", "D"] else "mixed " + "/".join(per)

def italic_contours(m, gl):
    lv = level[gl]
    if lv.startswith("mixed"):
        lv = lv.split()[1].split("/")[0 if m == "Light" else 1]
    up = UP[m][gl]["contours"]
    if lv == "A": cs = RA[m][gl]["contours"]
    elif lv == "B": cs = RB[m][gl]["contours"]
    elif lv == "C": cs = RC[m][gl]["contours"]
    else: cs = [{"closed": c["closed"], "nodes": [[n[0] + K * n[1], n[1]] + list(n[2:]) for n in c["nodes"]]} for c in up]
    return [{"closed": c["closed"], "nodes": [[n[0] + SHIFT, n[1]] + list(n[2:]) for n in c["nodes"]]} for c in cs]

json.dump(level, open(os.path.join(W, "levels.json"), "w"), indent=0)
# final italic outlines as JSON for the sheets
for m in ("Light", "Bold"):
    out = {gl: {"contours": italic_contours(m, gl) if UP[m][gl]["contours"] else [], "level": level[gl]} for gl in UP[m]}
    json.dump(out, open(os.path.join(W, "italic_%s.json" % m), "w"))

font = glyphsLib.GSFont(os.path.join(PILOT, "src", "HindSiliguri.glyphs"))
ufos = glyphsLib.to_ufos(font, ufo_module=ufoLib2, minimize_glyphs_diffs=True)
T = {"l": "line", "c": "curve", "q": "qcurve", "o": None}
from ufoLib2.objects import Contour, Point, Component, Anchor
for ufo in ufos:
    m = ufo.info.styleName  # Light / Bold
    for gl in list(ufo.keys()):
        G = ufo[gl]; src = UP[m][gl]
        # outlines: same node order as the .glyphs source (glyphsLib writes Glyphs order; start point preserved)
        assert len(G.contours) == len(src["contours"]), (m, gl)
        new = italic_contours(m, gl) if src["contours"] else []
        for C_, nc in zip(G.contours, new):
            assert len(C_.points) == len(nc["nodes"]), (m, gl)
            # glyphsLib may rotate the start; match by index offset found from the upright
            pts = C_.points
            up_nodes = [n for n in src["contours"][new.index(nc)]["nodes"]]
            N = len(pts); off = None
            for o in range(N):
                if all(abs(pts[(i + o) % N].x - up_nodes[i][0]) < 1e-6 and abs(pts[(i + o) % N].y - up_nodes[i][1]) < 1e-6 for i in range(N)):
                    off = o; break
            assert off is not None, (m, gl, "start")
            for i in range(N):
                p = pts[(i + off) % N]; p.x = nc["nodes"][i][0]; p.y = nc["nodes"][i][1]
        for cp in G.components:
            t = cp.transformation
            cp.transformation = (t[0], t[1], t[2], t[3], t[4] + K * t[5], t[5])
        for a in G.anchors:
            a.x = a.x + K * (a.y - YC)
    ufo.info.italicAngle = -14.036
    ufo.info.styleName = m + " Italic"
    ufo.info.styleMapStyleName = "italic" if m == "Light" else "bold italic"
    ufo.info.postscriptFontName = "HindSiliguri-%sItalic" % m
    ufo.info.openTypeOS2Selection = None
    ufo.lib["com.github.googlei18n.ufo2ft.filters"] = [{"name": "flattenComponents", "pre": True}] if False else ufo.lib.get("com.github.googlei18n.ufo2ft.filters", [])
    fn = os.path.join(PILOT, "HindSiliguri-%sItalic.ufo" % m)
    ufo.save(fn, overwrite=True)
    print("wrote", fn)

ds = DesignSpaceDocument()
a = AxisDescriptor(); a.tag = "wght"; a.name = "Weight"; a.minimum = 300; a.default = 300; a.maximum = 700; a.map = [(300, 0), (700, 100)]
ds.addAxis(a)
for m, v in (("Light", 0), ("Bold", 100)):
    s = SourceDescriptor(); s.path = "HindSiliguri-%sItalic.ufo" % m; s.filename = s.path; s.familyName = "Hind Siliguri"; s.styleName = m + " Italic"
    s.location = {"Weight": v}; ds.addSource(s)
for nm, v in (("Light Italic", 0), ("Regular Italic", 25), ("Medium Italic", 50), ("SemiBold Italic", 75), ("Bold Italic", 100)):
    i = InstanceDescriptor(); i.familyName = "Hind Siliguri"; i.styleName = nm; i.location = {"Weight": v}; ds.addInstance(i)
ds.write(os.path.join(PILOT, "HindSiliguri-Italic.designspace"))
from collections import Counter
print(Counter(level.values()))
