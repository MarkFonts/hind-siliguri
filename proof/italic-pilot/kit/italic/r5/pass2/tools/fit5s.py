"""Round 5 · s round: the fits from Mark's drawing, at 14.04 deg.

fit5s.py   -> readings/fit5s.json, printed

  psi from his node vectors   the spine piece (both spine cubics: 2 nodes + 2 handles each, 8 points) of his roman
                              (anchor-free) against his italic: the rigid rotation that best takes one onto the other
                              (Procrustes, no scale); psi = -rotation / theta. Also each edge alone, the spine tangent at
                              each edge's inflection (round 5's 1.18 reading), and the same fit for the plain slant.
  psi by score                XOR against his italic over psi 0.8 .. 1.6 (steps 1-3 and 1-6, terminal rules a and b)
  side extremes               his spine-end nodes against the slant's seats (moves in u), their tangents from vertical,
                              and how far each sits from the TRUE vertical tangent on his own outline
  terminal cuts               the cut angles (from vertical, + = top leans right): roman, slant, his italic, a, b
  terminal zones              XOR inside a box round each terminal of his drawing (60 u round the cut), per rule
"""
import sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
import drawn, drawn5s
from skeleton import bez, bez_d1, curvature_sign_changes
from skeleton5s import vertical_ts, unit


def cubic_of(cs, gi, gj):
    ns = cs[0]["nodes"]; N = len(ns)
    return np.array([ns[gi][:2], ns[(gi + 1) % N][:2], ns[(gi + 2) % N][:2], ns[gj][:2]], float)


def spine_cubics(cs):
    """the two cubics holding exactly one curvature sign change (the anchor-free spine edges)"""
    ns = cs[0]["nodes"]; N = len(ns); out = []
    ons = [i for i in range(N) if ns[i][2] != "o"]
    for a, i in enumerate(ons):
        j = ons[(a + 1) % len(ons)]
        if (j - i) % N == 3:
            P = cubic_of(cs, i, j)
            if len(curvature_sign_changes(P)) == 1:
                out.append(((i, j), P))
    return out


def infl_angle(P):
    t = curvature_sign_changes(P)[0]; v = bez_d1(P, [t])[0]
    return math.degrees(math.atan2(v[1], v[0])) % 180.0, bez(P, [t])[0]


def tangent_from_vertical(v):
    v = unit(v); v = v if v[1] > 0 else -v
    return math.degrees(math.atan2(v[0], v[1]))


def cut_angles(cs):
    """the longest straight segment of each line run (an s's two cuts): (upper, lower) angle from vertical"""
    ns = cs[0]["nodes"]; N = len(ns)
    ons = [i for i in range(N) if ns[i][2] != "o"]
    lines = []
    for a, i in enumerate(ons):
        j = ons[(a + 1) % len(ons)]
        if (j - i) % N == 1:
            e = np.array(ns[j][:2]) - np.array(ns[i][:2]); lines.append((np.linalg.norm(e), i, j, e))
    lines.sort(key=lambda r: -r[0])
    two = lines[:2]
    two.sort(key=lambda r: -(ns[r[1]][1] + ns[r[2]][1]))
    return [dict(seg=(r[1], r[2]), deg=round(tangent_from_vertical(r[3]), 2), length=round(float(r[0]), 1),
                 mid=[round(float(v), 1) for v in (np.array(ns[r[1]][:2]) + np.array(ns[r[2]][:2])) / 2]) for r in two]


def zone_xor(cand, ref, cut):
    m = cut["mid"]
    return drawn.xor_pct(cand, ref, band=(m[1] - 90, m[1] + 90), xband=(m[0] - 90, m[0] + 90))


def main():
    C.set_slant(0.25)
    from round5s import correct5s, r5_rules
    th = math.atan(C.K)
    I = drawn5s.inputs(); up = I["up"]; sl = I["sl14"]
    his, dx = drawn5s.italic(sl["contours"])
    res = dict(theta_deg=round(math.degrees(th), 3), placement="centroid", dx=round(dx, 2))
    # -- psi from his node vectors
    R = spine_cubics(up["contours"]); H = spine_cubics(his); S = spine_cubics(sl["contours"])
    pairs, extra = drawn5s.correspond(sl["contours"], his)
    cmap = dict(pairs)
    def pair_edges(A, B, cmap=cmap):
        # match the edges by the node correspondence (roman node order -> his node order)
        out = []
        Bd = {ib: Pb for ib, Pb in B}
        for ia, Pa in A:
            ib = (cmap.get(ia[0]), cmap.get(ia[1]))
            if ib in Bd:
                out.append((ia, Pa, ib, Bd[ib]))
            else:
                print("no partner for", ia, ib, sorted(Bd))
        return out
    pe = pair_edges(R, H)
    rot, rms, _, _ = drawn5s.procrustes(np.vstack([p[1] for p in pe]), np.vstack([p[3] for p in pe]))
    rot_s, rms_s, _, _ = drawn5s.procrustes(np.vstack([p[1] for p in pair_edges(R, S, {k: k for k in range(999)})]), np.vstack([p[3] for p in pair_edges(R, S, {k: k for k in range(999)})]))
    fit = dict(both_edges=dict(rotation_deg=round(rot, 2), psi=round(-math.radians(rot) / th, 3), rms_u=round(rms, 2)),
               slant_both_edges=dict(rotation_deg=round(rot_s, 2), psi_equiv=round(-math.radians(rot_s) / th, 3), rms_u=round(rms_s, 2)),
               edges=[])
    for ia, Pa, ib, Pb in pe:
        r1, e1, _, _ = drawn5s.procrustes(Pa, Pb)
        a_r, _ = infl_angle(Pa); a_i, _ = infl_angle(Pb)
        fit["edges"].append(dict(roman=ia, italic=ib, rotation_deg=round(r1, 2), psi=round(-math.radians(r1) / th, 3), rms_u=round(e1, 2),
                                 inflection_tangent_roman=round(a_r, 2), inflection_tangent_italic=round(a_i, 2),
                                 psi_tangent=round(math.radians(a_r - a_i) / th, 3),
                                 handle_lengths_roman=[round(float(np.linalg.norm(Pa[1] - Pa[0])), 1), round(float(np.linalg.norm(Pa[2] - Pa[3])), 1)],
                                 handle_lengths_italic=[round(float(np.linalg.norm(Pb[1] - Pb[0])), 1), round(float(np.linalg.norm(Pb[2] - Pb[3])), 1)]))
    res["psi_from_nodes"] = fit
    # -- side extremes: his spine ends vs the slant seats; tangents; distance to his own vertical tangent
    res["correspondence"] = dict(pairs=pairs, his_extra_nodes=extra)
    F_sl = drawn5s.flat(sl["contours"]); F_h = drawn5s.flat(his)
    ext = []
    for (ia, Pa, ib, Pb) in pe:
        for end in (0, 1):
            r_node = ia[end]; h_node = ib[end]
            mv = F_h[h_node] - F_sl[r_node]
            # tangent of his node (the spine handle) from vertical
            tv = Pb[1] - Pb[0] if end == 0 else Pb[3] - Pb[2]
            # where on his outline (this spine cubic and its neighbour) is the tangent truly vertical, and how far
            ts = vertical_ts(Pb)
            near = min(ts, key=lambda t: abs(t - (0.0 if end == 0 else 1.0))) if ts else None
            dist = None
            if near is not None:
                q = bez(Pb, [near])[0]
                dist = float(np.linalg.norm(q - Pb[0 if end == 0 else 3]))
            ext.append(dict(roman_node=r_node, his_node=h_node, move_from_slant_seat=[round(float(v), 1) for v in mv],
                            move_u=round(float(np.linalg.norm(mv)), 1), his_tangent_from_vertical=round(tangent_from_vertical(tv), 2),
                            his_node_to_true_vertical_tangent_u=None if dist is None else round(dist, 1)))
    # the slant's tangent at those nodes: the roman's vertical sheared
    for e in ext:
        e["slant_tangent_from_vertical"] = round(math.degrees(th), 2)
    res["side_extremes"] = ext
    # -- cuts
    rr = r5_rules(up)["contours"]
    cand = {"roman": up["contours"], "slant": sl["contours"], "his italic": his, "r5 rules": rr}
    runs = {}
    for term in ("roman", "shear", "a", "b"):
        for psi in (1.18,):
            runs[term + "_13"] = correct5s(up, "1-3", terminal=term, psi=psi)["contours"]
            runs[term + "_16"] = correct5s(up, "1-6", terminal=term, psi=psi)["contours"]
    cand.update(runs)
    hc = cut_angles(his)
    res["cuts"] = {k: cut_angles(v) for k, v in cand.items()}
    res["terminal_zone_xor"] = {k: dict(upper=round(zone_xor(v, his, hc[0]), 2), lower=round(zone_xor(v, his, hc[1]), 2),
                                        whole=round(drawn.xor_pct(v, his), 2)) for k, v in cand.items() if k != "his italic"}
    # -- psi by score
    sc = {}
    for term in (("a", "b") if "--scan" in sys.argv else ()):
        for psi in (0.8, 0.9, 1.0, 1.1, 1.18, 1.25, 1.3, 1.4, 1.5, 1.6):
            a = correct5s(up, "1-3", terminal=term, psi=psi)["contours"]
            b = correct5s(up, "1-6", terminal=term, psi=psi)["contours"]
            sc["%s %.2f" % (term, psi)] = dict(steps13=round(drawn.xor_pct(a, his), 2), steps16=round(drawn.xor_pct(b, his), 2))
            print(term, psi, sc["%s %.2f" % (term, psi)], flush=True)
    if sc:
        res["psi_by_score"] = sc
    else:
        res["psi_by_score"] = json.load(open(os.path.join(C.R5S, "readings", "fit5s.json"))).get("psi_by_score")
    json.dump(res, open(os.path.join(C.R5S, "readings", "fit5s.json"), "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(json.dumps({k: res[k] for k in ("psi_from_nodes", "side_extremes", "cuts", "terminal_zone_xor")}, indent=1, default=str))


if __name__ == "__main__":
    main()
