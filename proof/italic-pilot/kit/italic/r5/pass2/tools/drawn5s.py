"""Round 5 · s round: Mark's drawn s (roman = the upright, italic = the target) and the comparisons against it.

  inputs()                      -> dict(up, sl14, sl18, up_anchors) from src/s_drawn.json (build_s.py)
  italic(frame, how)            -> his drawn italic s (contours) placed in `frame`'s x
        how "centroid"  (default) the drawing's ink centroid x on the frame's ink centroid x. Every part's centre stays
                        where the shear puts it (I10, I16), and the terminals now ride (I15), so the old anchor -- the
                        held terminal corners -- no longer holds anything
        how "corners"   round 5's anchor (drawn.placement: the lowest-left and highest-right on-curve nodes)
  best_xor(cand, ref)           -> (dx, XOR %) at the candidate's own best x shift (shape only, reported beside)
  correspond(a_cs, b_cs)        -> on-curve correspondence a -> b by order (dynamic programming; b may have extra nodes,
                                   his two chamfer nodes), with the off-curve handles of corresponding curves
  procrustes(P, Q)              -> rigid rotation (deg, + = anticlockwise) and rms taking P onto Q (no scale)
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
import drawn

SRC = os.path.join(C.R5S, "src", "s_drawn.json")


def inputs():
    D = json.load(open(SRC))
    return dict(up=D["GeistSerifDrawnRoman_s"], up_anchors=D["GeistSerifDrawnRoman_s.anchors"],
                sl14=D["GeistSerifDrawnSlant14_s"], sl18=D["GeistSerifDrawnSlant18_s"], D=D)


def centroid_x(cs):
    b = drawn.box_of(cs, pad=4); M = drawn.mask(cs, b)
    H, W = M.shape
    xx = b[0] + (np.arange(W) + 0.5) / drawn.PPU
    return float((M.sum(axis=0) * xx).sum() / M.sum())


def italic(frame, how="centroid"):
    raw = drawn.raw_contours("s", "italic")
    if how == "corners":
        dx, _ = drawn.placement("s", "italic", frame)
    else:
        dx = centroid_x(frame) - centroid_x(raw)
    return drawn.shift(raw, dx), dx


def best_xor(cand, ref, lo=-30, hi=30):
    f = lambda d: drawn.xor_pct(drawn.shift(cand, d), ref)
    xs = np.arange(lo, hi + 0.1, 2.0); v = [f(d) for d in xs]; d0 = xs[int(np.argmin(v))]
    xs = np.arange(d0 - 2, d0 + 2.01, 0.25); v = [f(d) for d in xs]
    return float(xs[int(np.argmin(v))]), float(min(v))


def ons(cs):
    out = []; k = 0
    for c in cs:
        for n in c["nodes"]:
            if n[2] != "o":
                out.append((k, np.array(n[:2], float)))
            k += 1
    return out


def flat(cs):
    return [np.array(n[:2], float) for c in cs for n in c["nodes"]]


def correspond(a_cs, b_cs):
    """a's on-curve nodes -> b's, in contour order, b may have extra nodes; cost = distance (a and b in one frame).
    Single contour each (the s)."""
    A = ons(a_cs); B = ons(b_cs); na, nb = len(A), len(B)
    best = None
    for shift in range(nb):                        # b's start may be rotated against a's
        Bs = B[shift:] + B[:shift]
        INF = 1e18
        D = np.full((na + 1, nb + 1), INF); D[0, :] = 0.0 if False else INF; D[0, 0] = 0.0
        for j in range(1, nb + 1):
            D[0, j] = D[0, j - 1] + 80.0            # skipping b nodes costs a constant
        bk = {}
        for i in range(1, na + 1):
            for j in range(1, nb + 1):
                m = D[i - 1, j - 1] + float(np.linalg.norm(A[i - 1][1] - Bs[j - 1][1]))
                s = D[i, j - 1] + 80.0
                if m <= s:
                    D[i, j] = m; bk[(i, j)] = "m"
                else:
                    D[i, j] = s; bk[(i, j)] = "s"
        if best is None or D[na, nb] < best[0]:
            best = (D[na, nb], shift, bk, Bs)
    _, shift, bk, Bs = best
    i, j = na, nb; pairs = []
    while i > 0 and j > 0:
        if bk[(i, j)] == "m":
            pairs.append((A[i - 1][0], Bs[j - 1][0])); i -= 1; j -= 1
        else:
            j -= 1
    pairs.reverse()
    matched_b = {b for _, b in pairs}
    extra = [k for k, _ in B if k not in matched_b]
    return pairs, extra


def procrustes(P, Q):
    P = np.asarray(P, float); Q = np.asarray(Q, float)
    pc, qc = P.mean(axis=0), Q.mean(axis=0)
    X, Y = P - pc, Q - qc
    a = math.atan2(np.sum(X[:, 0] * Y[:, 1] - X[:, 1] * Y[:, 0]), np.sum(X[:, 0] * Y[:, 0] + X[:, 1] * Y[:, 1]))
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    rms = float(np.sqrt(np.mean(np.sum((X @ R.T - Y) ** 2, axis=1))))
    return math.degrees(a), rms, pc, qc
