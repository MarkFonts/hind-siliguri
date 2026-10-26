"""Round 5 · s round: the thickness of an s along its stroke, terminal -> bowl -> spine -> bowl -> terminal.

ONE instrument for every outline, so that Mark's drawn italic (which is not node-compatible with his roman: two extra
chamfer nodes) is read exactly like the others: the INSCRIBED BALL. Every outline sample p on either side, with its
inward normal n, carries the largest disc inside the ink that touches the outline at p (the shrinking-ball medial
axis): r = min over the other samples q in front of p of |q - p|^2 / (2 (q - p).n). The disc's diameter 2r is the
stroke's thickness there (measured square to the stroke, wherever the stroke runs), its centre p + r n a point of the
centreline. No pairing, no rungs, no fitting: a ball either fits in the ink or it does not.

The two sides of an s run between its two cuts (the longest straight segment of each run of lines); the cuts, the
short blunts beside them and the samples within 6 u of a corner carry no ball. Each side's centres are walked in
order from the upper cut to the lower cut; the abscissa is the arc length along the centreline, remapped piecewise
linearly between six landmarks so the five letters line up part by part:

    0 upper cut | 1 top of the upper bowl | 2 left of the upper bowl | 3 spine centre | 4 right of the lower bowl |
    5 bottom of the lower bowl | 6 lower cut

(the spine centre = the centreline's point at the mean height of its left and right landmarks, the place where the
stroke crosses from one bowl into the other). Both sides' balls are binned on the abscissa (0.05) and the median
taken; where the two sides disagree by more than 6 u the bin is a junction of the ball with a corner and is dropped.

    profile(contours) -> dict(x (bins), th (median diameter, nan = no reading), landmarks, centres, raw)
"""
import math
import numpy as np
import skia
import drawn

STEP = 1.5           # u between outline samples
CORNER = 6.0         # u: no ball within this of a corner node
BIN = 0.05


def _samples(cs):
    """outline samples with tangents, per contour, plus which segment (on-curve index pair, kind, length) they come from"""
    out = []
    for c in cs:
        ns = c["nodes"]; N = len(ns)
        ons = [i for i in range(N) if ns[i][2] != "o"]
        segs = []
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [k % N for k in range(i + 1, i + 1 + ((j - i - 1) % N))]
            P = np.array([ns[i][:2]] + [ns[k][:2] for k in offs] + [ns[j][:2]], float)
            segs.append((i, j, P))
        pts, tan, seg = [], [], []
        for si, (i, j, P) in enumerate(segs):
            if len(P) == 4:
                L = sum(np.linalg.norm(np.diff(_bez(P, np.linspace(0, 1, 50)), axis=0), axis=1))
                n = max(2, int(L / STEP)); ts = np.linspace(0, 1, n, endpoint=False)
                pts.append(_bez(P, ts)); tan.append(_bez1(P, ts))
            else:
                L = np.linalg.norm(P[1] - P[0]); n = max(2, int(L / STEP)); ts = np.linspace(0, 1, n, endpoint=False)
                pts.append(P[0] + (P[1] - P[0]) * ts[:, None]); tan.append(np.repeat((P[1] - P[0])[None, :], n, axis=0))
            seg += [si] * n
        out.append(dict(pts=np.vstack(pts), tan=np.vstack(tan), seg=np.array(seg), segs=segs, nodes=ns))
    return out


def _bez(P, t):
    t = np.asarray(t)[:, None]; u = 1 - t
    return u ** 3 * P[0] + 3 * u * u * t * P[1] + 3 * u * t * t * P[2] + t ** 3 * P[3]


def _bez1(P, t):
    t = np.asarray(t)[:, None]; u = 1 - t
    return 3 * u * u * (P[1] - P[0]) + 6 * u * t * (P[2] - P[1]) + 3 * t * t * (P[3] - P[2])


def _cuts(c):
    """the cut segment of each run of lines (its longest line), and every line in those runs"""
    segs = c["segs"]; K = len(segs)
    is_line = [len(P) == 2 for _, _, P in segs]
    runs = []; seen = set()
    for k in range(K):
        if is_line[k] and k not in seen and not is_line[(k - 1) % K]:
            r = [];
            q = k
            while is_line[q % K] and (q % K) not in seen:
                r.append(q % K); seen.add(q % K); q += 1
            runs.append(r)
    cuts = [max(r, key=lambda q: np.linalg.norm(segs[q][2][1] - segs[q][2][0])) for r in runs]
    return runs, cuts


def balls(cs):
    S = _samples(cs)
    assert len(S) == 1, "an s is one contour"
    c = S[0]
    path = drawn.path(cs)
    P, T = c["pts"], c["tan"]
    T = T / np.linalg.norm(T, axis=1)[:, None]
    Nrm = np.stack([-T[:, 1], T[:, 0]], axis=1)
    # inward: the side where the ink is
    probe = P + 0.8 * Nrm
    inside = np.array([path.contains(float(x), float(y)) for x, y in probe])
    Nrm[~inside] *= -1
    runs, cuts = _cuts(c)
    blunt = {q for r in runs for q in r if np.linalg.norm(c["segs"][q][2][1] - c["segs"][q][2][0]) < 40.0} | set(cuts)
    corners = [np.array(c["nodes"][i][:2]) for i, j, Pp in c["segs"]]
    # corners: on-curve nodes that are not smooth
    corner_pts = [np.array(n[:2]) for n in c["nodes"] if n[2] != "o" and not (len(n) > 3 and n[3])]
    ok = np.array([c["seg"][k] not in blunt for k in range(len(P))])
    if corner_pts:
        dmin = np.min(np.linalg.norm(P[:, None, :] - np.array(corner_pts)[None, :, :], axis=2), axis=1)
        ok &= dmin > CORNER
    R = np.full(len(P), np.nan)
    for k in np.nonzero(ok)[0]:
        d = P - P[k]; dn = d @ Nrm[k]
        m = (dn > 0.3) & (np.einsum("ij,ij->i", d, d) > 9.0)
        if not m.any():
            continue
        R[k] = np.min(np.einsum("ij,ij->i", d[m], d[m]) / (2 * dn[m]))
    return dict(P=P, N=Nrm, R=R, seg=c["seg"], runs=runs, cuts=cuts, segs=c["segs"], nodes=c["nodes"])


def profile(cs):
    B = balls(cs)
    P, Nrm, R, seg, cuts, segs = B["P"], B["N"], B["R"], B["seg"], B["cuts"], B["segs"]
    K = len(segs)
    # the two sides: from the end of one cut's run to the start of the other's, in contour order
    runs = B["runs"]
    assert len(runs) == 2, "an s has two terminals (runs of lines)"
    ri = sorted(range(2), key=lambda q: -np.mean([segs[x][2][:, 1].mean() for x in runs[q]]))      # upper run first
    up_run, lo_run = runs[ri[0]], runs[ri[1]]
    def side(from_run, to_run):
        k = (from_run[-1] + 1) % K; out = []
        while k != to_run[0]:
            out.append(k); k = (k + 1) % K
        return out
    sideA = side(up_run, lo_run)          # upper cut -> lower cut in contour order
    sideB = side(lo_run, up_run)          # lower cut -> upper cut: reversed below
    def centres(side_segs, reverse):
        idx = [i for s_ in side_segs for i in np.nonzero(seg == s_)[0]]
        if reverse:
            idx = idx[::-1]
        idx = [i for i in idx if not np.isnan(R[i])]
        C_ = np.array([P[i] + R[i] * Nrm[i] for i in idx]); D = np.array([2 * R[i] for i in idx])
        return C_, D
    CA, DA = centres(sideA, False); CB, DB = centres(sideB, True)
    # the centreline: side A's centres smoothed (a running median of 9), walked for arc length
    def smooth(X, w=9):
        out = X.copy()
        for i in range(len(X)):
            a, b = max(0, i - w // 2), min(len(X), i + w // 2 + 1)
            out[i] = np.median(X[a:b], axis=0)
        return out
    CL = smooth(CA)
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(CL, axis=0), axis=1))]
    # landmarks along the centreline
    n = len(CL)
    i_top = int(np.argmax(CL[: n // 2, 1]))
    yl = CL[:, 1]
    i_left = i_top + int(np.argmin(CL[i_top: int(0.75 * n), 0]))
    i_bot = (n // 2) + int(np.argmin(CL[n // 2:, 1]))
    i_right = i_left + int(np.argmax(CL[i_left: i_bot, 0]))
    ymid = (CL[i_left, 1] + CL[i_right, 1]) / 2
    i_mid = i_left + int(np.argmin(np.abs(CL[i_left: i_right, 1] - ymid)))
    lm = [0, i_top, i_left, i_mid, i_right, i_bot, n - 1]
    L = arc[lm]
    def xmap(a):
        return np.interp(a, L, np.arange(7.0))
    xA = xmap(arc)
    # side B: each centre takes the abscissa of the nearest centreline point
    from scipy.spatial import cKDTree
    tree = cKDTree(CL)
    dB, iB = tree.query(CB)
    xB = xA[iB]
    okB = dB < 6.0
    bins = np.arange(0, 6 + 1e-9, BIN)
    th = np.full(len(bins), np.nan); thA = np.full(len(bins), np.nan); thB = np.full(len(bins), np.nan)
    for k, b in enumerate(bins):
        a = DA[np.abs(xA - b) <= BIN / 2]; bb = DB[okB & (np.abs(xB - b) <= BIN / 2)]
        if len(a): thA[k] = np.median(a)
        if len(bb): thB[k] = np.median(bb)
        if len(a) and len(bb):
            if abs(thA[k] - thB[k]) <= 6.0:
                th[k] = np.median(np.r_[a, bb])
        elif len(a):
            th[k] = thA[k]
    return dict(x=bins, th=th, thA=thA, thB=thB, landmarks=[CL[i].tolist() for i in lm], centreline=CL, xA=xA, DA=DA, CA=CA, CB=CB, DB=DB)


LANDMARKS = ["upper cut", "top", "upper-left", "spine centre", "lower-right", "bottom", "lower cut"]


def zone_stats(prof):
    """mean thickness per zone: terminal arm (0-1, 5-6), bowl (1-2.4, 3.6-5), spine (2.4-3.6), and the spine's min/max"""
    x, th = prof["x"], prof["th"]
    def m(a, b, f=np.nanmean):
        s = th[(x >= a) & (x <= b)]
        return float(f(s)) if np.isfinite(s).any() else float("nan")
    return dict(upper_arm=m(0.15, 1.0), upper_bowl=m(1.0, 2.4), spine=m(2.4, 3.6), spine_core=m(2.7, 3.3),
                spine_max=m(2.4, 3.6, np.nanmax), lower_bowl=m(3.6, 5.0), lower_arm=m(5.0, 5.85),
                upper_bowl_max=m(1.0, 2.4, np.nanmax), lower_bowl_max=m(3.6, 5.0, np.nanmax),
                upper_bowl_min=m(0.6, 1.6, np.nanmin), lower_bowl_min=m(4.4, 5.4, np.nanmin))
