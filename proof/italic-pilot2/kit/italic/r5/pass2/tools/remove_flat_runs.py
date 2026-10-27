"""Remove a spine's centre anchors (Mark, 2026-10-25, after Sebastian: "the italic s only works WITHOUT the center
spine anchors" -- "remove these points from roman AND italic"): every flat run (a straight segment <= FLAT_RUN_MAX
between two curves, smooth at both ends) is merged with the two curves round it into ONE cubic whose ends are the
run's outer neighbours: Curvatura's softmerge (tools/harmonize.py) -- the drawn tangent directions AND curvatures at
the two outer ends are kept, the two handle lengths solved for them (the least-squares fit is kept as fit_cubic for
comparison). The deviation from the drawn path is reported both ways. The roman loses the nodes; the slant is the new roman sheared; the corrected copy is the solver's.

remove_flat_runs.py LETTER [LETTER ...]        rewrites the three keys of each letter in src/geistserif_italic.json
"""
import sys, os, json, math, copy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "solver")); sys.path.insert(0, HERE)
from rungs import bez
import carry as C
from italicmove import ItalicMover, FLAT_RUN_MAX
from harmonize import softmerge

SRC = os.path.join(HERE, "..", "src", "geistserif_italic.json")


def unit(v):
    L = math.hypot(*v); return (v[0] / L, v[1] / L) if L > 1e-9 else (0.0, 0.0)


def contour_segments(nodes):
    N = len(nodes); ons = [i for i in range(N) if nodes[i][2] != "o"]
    segs = []
    for a, i in enumerate(ons):
        j = ons[(a + 1) % len(ons)]
        offs = [k % N for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
        segs.append((i, j, offs, "curve" if (len(offs) == 2 and nodes[j][2] != "l") else "line"))
    return segs


def samples(nodes, seg, n=40):
    i, j, offs, kind = seg
    P0 = nodes[i][:2]; P3 = nodes[j][:2]
    if kind == "line":
        return [(P0[0] + (P3[0] - P0[0]) * t, P0[1] + (P3[1] - P0[1]) * t) for t in np.linspace(0, 1, n)]
    P = [tuple(P0), tuple(nodes[offs[0]][:2]), tuple(nodes[offs[1]][:2]), tuple(P3)]
    return [bez(P, t) for t in np.linspace(0, 1, n)]


def fit_cubic(Q0, Q3, d0, d3, pts):
    """handle lengths a, b (Q0 + a d0, Q3 + b d3) by least squares to pts (chord-length parametrised)"""
    pts = np.array(pts, float)
    al = np.r_[0.0, np.cumsum(np.hypot(*(pts[1:] - pts[:-1]).T))]; T = al / al[-1]
    A11 = A12 = A22 = b1 = b2 = 0.0
    for t, q in zip(T, pts):
        u = 1 - t; wa = 3 * u * u * t; wb = 3 * u * t * t
        base = (u ** 3 + wa) * np.array(Q0) + (wb + t ** 3) * np.array(Q3)
        r = q - base
        va = wa * np.array(d0); vb = wb * np.array(d3)
        A11 += va @ va; A12 += va @ vb; A22 += vb @ vb; b1 += va @ r; b2 += vb @ r
    det = A11 * A22 - A12 * A12
    a = (b1 * A22 - b2 * A12) / det; b = (A11 * b2 - A12 * b1) / det
    P = [Q0, (Q0[0] + d0[0] * a, Q0[1] + d0[1] * a), (Q3[0] + d3[0] * b, Q3[1] + d3[1] * b), Q3]
    dev = max(min(math.dist(bez(P, t), q) for t in np.linspace(0, 1, 200)) for q in pts[::4])
    return P, a, b, dev


def fit_cubic_reparam(Q0, Q3, d0, d3, pts, iters=30):
    """round 5 · s round: fit_cubic with Hoschek re-parametrisation (each drawn sample re-projected onto the current
    cubic, then the two handle lengths re-solved): the true least-squares cubic with the drawn end nodes and tangents"""
    pts = np.array(pts, float); Q0 = np.array(Q0, float); Q3 = np.array(Q3, float); d0 = np.array(d0); d3 = np.array(d3)
    al = np.r_[0.0, np.cumsum(np.hypot(*(pts[1:] - pts[:-1]).T))]; T = al / al[-1]
    ts = np.linspace(0, 1, 801)
    for _ in range(iters):
        u = 1 - T; wa = 3 * u * u * T; wb = 3 * u * T * T
        base = (u ** 3 + wa)[:, None] * Q0 + (wb + T ** 3)[:, None] * Q3
        r = pts - base; va = wa[:, None] * d0; vb = wb[:, None] * d3
        M = np.array([[np.sum(va * va), np.sum(va * vb)], [np.sum(va * vb), np.sum(vb * vb)]])
        a, b = np.linalg.solve(M, [np.sum(va * r), np.sum(vb * r)])
        P = np.array([Q0, Q0 + a * d0, Q3 + b * d3, Q3])
        uu = 1 - ts
        curve = (uu ** 3)[:, None] * P[0] + (3 * uu * uu * ts)[:, None] * P[1] + (3 * uu * ts * ts)[:, None] * P[2] + (ts ** 3)[:, None] * P[3]
        d = np.linalg.norm(pts[:, None, :] - curve[None, :, :], axis=2)
        T = ts[np.argmin(d, axis=1)]
    dev = float(d.min(axis=1).max())
    return [tuple(p) for p in P], a, b, dev


def remove_runs(g, method="softmerge"):
    """method "softmerge" (round 4: end curvatures kept) or "lsq" (round 5 · s round: end nodes and tangents kept,
    handle lengths least squares to the drawn path, re-parametrised)"""
    g = copy.deepcopy(g); report = []
    for c in g["contours"]:
        nodes = c["nodes"]
        while True:
            segs = contour_segments(nodes); N = len(segs)
            kinds = {s[0]: s for s in segs}
            found = None
            for k, (i, j, offs, kind) in enumerate(segs):
                if kind != "line":
                    continue
                prev, nxt = segs[k - 1], segs[(k + 1) % N]
                if prev[3] != "curve" or nxt[3] != "curve":
                    continue
                # smooth by angle (as the solver reads it, I8): the run's direction within 3 deg of both curves' handles
                d_run = unit((nodes[j][0] - nodes[i][0], nodes[j][1] - nodes[i][1]))
                d_in = unit((nodes[i][0] - nodes[prev[2][1]][0], nodes[i][1] - nodes[prev[2][1]][1]))
                d_out = unit((nodes[nxt[2][0]][0] - nodes[j][0], nodes[nxt[2][0]][1] - nodes[j][1]))
                cos3 = math.cos(math.radians(3.0))
                if d_run[0] * d_in[0] + d_run[1] * d_in[1] < cos3 or d_run[0] * d_out[0] + d_run[1] * d_out[1] < cos3:
                    continue
                if math.dist(nodes[i][:2], nodes[j][:2]) > FLAT_RUN_MAX:
                    continue
                found = (prev, (i, j, offs, kind), nxt); break
            if not found:
                break
            prev, run, nxt = found
            Q0 = tuple(nodes[prev[0]][:2]); Q3 = tuple(nodes[nxt[1]][:2])
            d0 = unit((nodes[prev[2][0]][0] - Q0[0], nodes[prev[2][0]][1] - Q0[1]))       # drawn tangent out of Q0
            d3 = unit((nodes[nxt[2][1]][0] - Q3[0], nodes[nxt[2][1]][1] - Q3[1]))         # drawn tangent into Q3 (from its handle)
            pts = samples(nodes, prev) + samples(nodes, run)[1:] + samples(nodes, nxt)[1:]
            seg1 = [tuple(nodes[prev[0]][:2]), tuple(nodes[prev[2][0]][:2]), tuple(nodes[prev[2][1]][:2]), tuple(nodes[prev[1]][:2])]
            seg2 = [tuple(nodes[nxt[0]][:2]), tuple(nodes[nxt[2][0]][:2]), tuple(nodes[nxt[2][1]][:2]), tuple(nodes[nxt[1]][:2])]
            if method == "lsq":
                P, _, _, _ = fit_cubic_reparam(Q0, Q3, d0, d3, pts)
                h1, h2 = P[1], P[2]
            else:
                h1, h2 = softmerge(seg1, seg2)
            P = [Q0, h1, h2, Q3]
            a, b = math.dist(Q0, h1), math.dist(Q3, h2)
            curve = [bez(P, t) for t in np.linspace(0, 1, 400)]
            dev = max(min(math.dist(c, q) for c in curve) for q in pts)            # drawn -> merged
            dev_back = max(min(math.dist(c, q) for q in pts) for c in curve[::4])  # merged -> drawn
            _, _, _, dev_lsq = fit_cubic(Q0, Q3, d0, d3, pts)
            # replace prev.offs + run nodes + nxt.offs by the two new handles: build the new node list
            drop = set(prev[2]) | {run[0], run[1]} | set(nxt[2])
            new = []
            for idx, n in enumerate(nodes):
                if idx == prev[0]:
                    new.append(n); new.append([P[1][0], P[1][1], "o", False]); new.append([P[2][0], P[2][1], "o", False])
                elif idx in drop:
                    continue
                else:
                    new.append(n)
            # the node after the run must be a curve node now
            for n in new:
                if n[:2] == list(Q3) or (abs(n[0] - Q3[0]) < 1e-9 and abs(n[1] - Q3[1]) < 1e-9):
                    n[2] = "c"
            report.append(dict(method=method, run=(run[0], run[1]), ends=(prev[0], nxt[1]), handle_lengths=(round(a, 1), round(b, 1)),
                               max_dev_drawn_to_merged=round(dev, 2), max_dev_merged_to_drawn=round(dev_back, 2),
                               lsq_max_dev=round(dev_lsq, 2)))
            nodes[:] = new
    return g, report


if __name__ == "__main__":
    G = json.load(open(SRC))
    for gl in sys.argv[1:]:
        up = G.get("GeistSerifRegular_" + gl + ".anchors", G["GeistSerifRegular_" + gl])   # always from the drawn letter
        up2, rep = remove_runs(up)
        if not rep:
            print(gl, "no flat runs"); continue
        n0 = sum(len(c["nodes"]) for c in up["contours"]); n1 = sum(len(c["nodes"]) for c in up2["contours"])
        print(gl, "runs removed:", rep, "nodes %d -> %d" % (n0, n1))
        sl = copy.deepcopy(up2); sl["master"] = "Slant"
        for c in sl["contours"]:
            for n in c["nodes"]:
                n[0] = n[0] + n[1] / 4.0
        IM = ItalicMover(sl, up2)
        it = {"contours": IM.contours_at(1.0), "width": up2["width"], "master": "Italic", "glyph": gl}
        G["GeistSerifRegular_" + gl + ".anchors"] = up            # the drawn s with its centre anchors, kept for reference
        G["GeistSerifRegular_" + gl] = up2; G["GeistSerifSlant_" + gl] = sl; G["GeistSerifItalic_" + gl] = it
        print("  slides:", [(x["node"], round(x["slide"], 1)) for x in IM.slides_i9])
    json.dump(G, open(SRC, "w")); print("written", SRC)
