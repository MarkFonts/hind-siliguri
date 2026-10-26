"""Hind Siliguri .glyphs snapshot -> solver JSON (one file per master), plus the artefact scan.
Node format = the parts solver's: [x, y, type l|c|o, smooth], Glyphs order (off-curves before the node they arrive at)."""
import glyphsLib, json, sys, os, math, itertools
HERE = os.path.dirname(os.path.abspath(__file__)); PILOT = os.path.dirname(HERE)
SRC = os.path.join(PILOT, "src", "HindSiliguri.glyphs")
OUT = os.path.join(PILOT, "work"); os.makedirs(OUT, exist_ok=True)
f = glyphsLib.GSFont(SRC)
T = {"line": "l", "curve": "c", "offcurve": "o", "qcurve": "q"}
data = {}
for m in f.masters:
    G = {}
    for g in f.glyphs:
        L = g.layers[m.id]
        cs = []
        for p in L.paths:
            cs.append({"closed": bool(p.closed), "nodes": [[float(n.position.x), float(n.position.y), T[n.type], bool(n.smooth)] for n in p.nodes]})
        comps = [{"name": c.name, "transform": [float(v) for v in c.transform]} for c in L.components]
        anchors = [{"name": a.name, "x": float(a.position.x), "y": float(a.position.y)} for a in L.anchors]
        G[g.name] = {"glyph": g.name, "unicode": g.unicode, "unicodes": list(g.unicodes or []), "width": float(L.width), "contours": cs,
                     "components": comps, "anchors": anchors, "master": m.name, "category": g.category, "script": g.script,
                     "export": bool(g.export)}
    data[m.name] = G
    json.dump(G, open(os.path.join(OUT, "upright_%s.json" % m.name), "w"))
info = {"family": f.familyName, "upm": f.upm, "masters": [{"name": m.name, "weight": m.weightValue, "xHeight": m.xHeight, "capHeight": m.capHeight,
        "ascender": m.ascender, "descender": m.descender} for m in f.masters], "order": [g.name for g in f.glyphs]}
json.dump(info, open(os.path.join(OUT, "fontinfo.json"), "w"), indent=1)

# ---- artefact scan: segments under 3 u, self-crossing contours, master compatibility --------------------------
def segs(c):
    n = c["nodes"]; N = len(n); ons = [i for i in range(N) if n[i][2] != "o"]
    out = []
    for a, b in zip(ons, ons[1:] + ons[:1]):
        offs = [n[k % N][:2] for k in range(a + 1, a + 1 + ((b - a - 1) % N))]
        out.append([n[a][:2]] + offs + [n[b][:2]])
    return out
def poly(c, k=16):
    pts = []
    for s in segs(c):
        if len(s) == 4:
            for i in range(k):
                t = i / k; u = 1 - t
                pts.append((u**3*s[0][0]+3*u*u*t*s[1][0]+3*u*t*t*s[2][0]+t**3*s[3][0], u**3*s[0][1]+3*u*u*t*s[1][1]+3*u*t*t*s[2][1]+t**3*s[3][1]))
        else:
            pts.append(tuple(s[0]))
    return pts
def inter(p1, p2, p3, p4):
    d = (p2[0]-p1[0])*(p4[1]-p3[1]) - (p2[1]-p1[1])*(p4[0]-p3[0])
    if abs(d) < 1e-12: return False
    t = ((p3[0]-p1[0])*(p4[1]-p3[1]) - (p3[1]-p1[1])*(p4[0]-p3[0])) / d
    u = ((p3[0]-p1[0])*(p2[1]-p1[1]) - (p3[1]-p1[1])*(p2[0]-p1[0])) / d
    return 1e-6 < t < 1-1e-6 and 1e-6 < u < 1-1e-6
scan = {"short": [], "selfcross": [], "incompatible": []}
for mn, G in data.items():
    for gn, g in G.items():
        for ci, c in enumerate(g["contours"]):
            for si, s in enumerate(segs(c)):
                L = math.dist(s[0], s[-1])
                if L < 3.0:
                    scan["short"].append([mn, gn, ci, si, round(L, 2)])
            P = poly(c); E = list(zip(P, P[1:] + P[:1])); n = len(E)
            hit = False
            for i in range(n):
                for j in range(i + 2, n):
                    if i == 0 and j == n - 1: continue
                    if inter(E[i][0], E[i][1], E[j][0], E[j][1]):
                        hit = True; break
                if hit: break
            if hit: scan["selfcross"].append([mn, gn, ci])
A, B = data["Light"], data["Bold"]
for gn in A:
    a, b = A[gn], B[gn]
    sa = [[n[2] for n in c["nodes"]] for c in a["contours"]]; sb = [[n[2] for n in c["nodes"]] for c in b["contours"]]
    if sa != sb or [c["name"] for c in a["components"]] != [c["name"] for c in b["components"]] or sorted(x["name"] for x in a["anchors"]) != sorted(x["name"] for x in b["anchors"]):
        scan["incompatible"].append(gn)
json.dump(scan, open(os.path.join(OUT, "artefact_scan.json"), "w"), indent=1)
print("short segments <3u:", len(scan["short"]), "| self-crossing contours:", len(scan["selfcross"]), "| incompatible glyphs:", scan["incompatible"])
print("short by glyph:", sorted({(s[1]) for s in scan["short"]})[:80])
print("selfcross:", scan["selfcross"][:60])
