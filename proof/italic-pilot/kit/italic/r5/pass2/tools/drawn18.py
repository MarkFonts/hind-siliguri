"""Mark's NEW drawn italic s and n for the 18.43 deg target (italic/src/mark_sn18_pdf_paths.json, Glyphs print at 300 pt,
2026-10-26): contours in font units, baseline 0 on the n's flat feet (baseline_pt.italic = 283.0), x = PDF x.

  raw(gl)              -> contours (raw PDF x)
  stem_angle()         -> (theta_d in deg, the stem sides measured): the n's straight stem / leg sides
  place_centroid(cs, frame), place_stems(cs, frame, band)   -> his drawing shifted into `frame`'s x
"""
import os, json, math
import numpy as np
import drawn

PATHS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "mark_sn18_pdf_paths.json"))
_D = None


def data():
    global _D
    if _D is None:
        _D = json.load(open(PATHS))
    return _D


def raw(gl):
    D = data(); U = D["units_per_pt"]; base = D["baseline_pt"]["italic"]
    out = []
    for i in D["letters"]["italic"][gl]:
        nodes = []; cur = None
        for q in D["paths"][i]:
            if q[0] == "m":
                cur = q[1]; nodes.append([q[1][0] * U, (q[1][1] - base) * U, "l", False])
            elif q[0] == "l":
                cur = q[1]; nodes.append([q[1][0] * U, (q[1][1] - base) * U, "l", False])
            elif q[0] == "c":
                c1 = q[1] if q[1] else cur
                nodes.append([c1[0] * U, (c1[1] - base) * U, "o", False])
                nodes.append([q[2][0] * U, (q[2][1] - base) * U, "o", False])
                nodes.append([q[3][0] * U, (q[3][1] - base) * U, "c", False]); cur = q[3]
        if len(nodes) > 1 and math.dist(nodes[0][:2], nodes[-1][:2]) < 0.05 * U:
            nodes.pop(0)
        out.append({"closed": True, "nodes": drawn._smooth(nodes)})
    return out


def stem_angle():
    """the n's straight sides longer than 150 u running within 30 deg of vertical: their mean angle from vertical"""
    cs = raw("n"); angs = []
    for c in cs:
        ns = c["nodes"]; N = len(ns)
        for i in range(N):
            a, b = ns[i], ns[(i + 1) % N]
            if a[2] == "o" or b[2] == "o":
                continue
            dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
            if L > 150 and abs(dx) < abs(dy) * math.tan(math.radians(30)):
                ang = math.degrees(math.atan2(dx if dy > 0 else -dx, abs(dy)))
                angs.append((round(ang, 3), round(L, 1)))
    w = np.array([l for _, l in angs]); v = np.array([a for a, _ in angs])
    return float((w * v).sum() / w.sum()), angs


def place_centroid(cs, frame):
    import drawn5s
    return drawn.shift(cs, drawn5s.centroid_x(frame) - drawn5s.centroid_x(cs))


def place_stems(cs, frame, band=(60, 330)):
    ins = lambda C_: [n[0] for c in C_ for n in c["nodes"] if band[0] <= n[1] <= band[1]]
    x0 = min(ins(cs)) - min(ins(frame))
    d, e = drawn.best_dx(drawn.shift(frame, x0), cs, band=band, lo=-40, hi=40)
    return drawn.shift(cs, -(x0 + d)), e
