"""Fit rho (round lean), nu (bowl narrowing) and psi (spine rotation) from MARK'S OWN roman -> italic drawings
(src/mark_saopne_pdf_paths.json, both rows from his print PDF, so a difference between his roman and our JSON Regular --
his s is a later drawing, 11.8 % XOR off ours -- cannot leak into the fit). Fitted from o, p, s and the two-storey a
only: the drawn e and n are unfinished (Mark, 2026-10-25) and are not used.

Model, per round part (I10 + I11), in the drawing's own units:
    x_it = t + s * x_rom + k * y_rom        y_it = b + sy * y_rom
    k = tan(rho * theta)  ->  rho = atan(k) / theta,   theta = atan(1/4) (his drawings are at 14.04 deg)
    outer: s = 1 - nu      counter: s = 1 - nu * W / w (the same units off each side, stroke widths kept)
fitted by least squares on the roman part's curve samples against the italic outline (point-to-curve, scipy).
The spine (I12): direction of the mid-line between the two spine edges at their inflections, roman vs italic:
    psi = (angle_roman - angle_italic) / theta       (a clockwise turn for a rightward slant)

fit_params.py [--json OUT]      prints the table; OUT (default ../readings/fit_params.json)
"""
import sys, os, json, math
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import drawn

TH = math.atan(0.25)


def samples(cs, n=24, keep=None):
    """dense points on each segment (on + off curve geometry), optionally filtered by keep(x, y)"""
    out = []
    for c in cs:
        ns = c["nodes"]; N = len(ns); ons = [i for i in range(N) if ns[i][2] != "o"]
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [ns[q % N] for q in range(i + 1, i + 1 + ((j - i - 1) % N))]
            P0, P3 = ns[i], ns[j]
            for t in np.linspace(0, 1, n, endpoint=False):
                if len(offs) == 2:
                    u = 1 - t; P1, P2 = offs
                    x = u ** 3 * P0[0] + 3 * u * u * t * P1[0] + 3 * u * t * t * P2[0] + t ** 3 * P3[0]
                    y = u ** 3 * P0[1] + 3 * u * u * t * P1[1] + 3 * u * t * t * P2[1] + t ** 3 * P3[1]
                else:
                    x = P0[0] + (P3[0] - P0[0]) * t; y = P0[1] + (P3[1] - P0[1]) * t
                if keep is None or keep(x, y):
                    out.append((x, y))
    return np.array(out)


def fit_affine(R, I_all, x0=None, R_all=None):
    """x' = t + s x + k y, y' = b + sy y; R (roman part samples) onto the italic outline samples I_all. The start is
    the plain slant with the two WHOLE letters' centres on each other (R_all = the whole roman letter's samples)"""
    tree = cKDTree(I_all)
    cx, cy = R[:, 0].mean(), R[:, 1].mean()
    RA = R if R_all is None else R_all
    sh = RA[:, 0] + 0.25 * (RA[:, 1] - cy)
    t_c = (I_all[:, 0].min() + I_all[:, 0].max()) / 2 - (sh.min() + sh.max()) / 2 + (RA[:, 0].min() + RA[:, 0].max()) / 2 - cx
    t_c = t_c - ((RA[:, 0].min() + RA[:, 0].max()) / 2 - cx) * 0.0
    def f(p):
        t, s, k, b, sy = p
        X = np.c_[t + cx + s * (R[:, 0] - cx) + k * (R[:, 1] - cy), b + cy + sy * (R[:, 1] - cy)]
        d, _ = tree.query(X)
        return d
    # t such that the sheared whole letter's box centre lands on the italic's: X = t + cx + (x - cx) + k (y - cy)
    t0 = (I_all[:, 0].min() + I_all[:, 0].max()) / 2 - (sh.min() + sh.max()) / 2
    p0 = x0 if x0 is not None else [t0, 1.0, math.tan(TH), 0.0, 1.0]
    best = None
    for dt in (-24, -12, 0, 12, 24):
        q = list(p0); q[0] += dt
        r = least_squares(f, q, loss="soft_l1", f_scale=2.0)
        if best is None or r.cost < best.cost:
            best = r
    t, s, k, b, sy = best.x
    res = f(best.x)
    return dict(s=float(s), k=float(k), sy=float(sy), rho=float(math.atan(k) / TH), rms=float(np.sqrt(np.mean(res ** 2))),
                p90=float(np.percentile(res, 90)), n=int(len(R)), W=float(R[:, 0].max() - R[:, 0].min()))


def fit_part(Ro, Rc, I_all, R_all):
    """the I10 + I11 model exactly, for one round part: outer samples Ro and counter samples Rc share the centre (the
    outer's box centre), the lean k and the vertical (b, sy); the outer scales by 1 - nu, the counter by 1 - nu W / w
    (the same units off each side). Returns rho, nu and the residual."""
    tree = cKDTree(I_all)
    cx, cy = (Ro[:, 0].min() + Ro[:, 0].max()) / 2, (Ro[:, 1].min() + Ro[:, 1].max()) / 2
    W = Ro[:, 0].max() - Ro[:, 0].min(); w = Rc[:, 0].max() - Rc[:, 0].min()
    sh = R_all[:, 0] + 0.25 * (R_all[:, 1] - cy)
    t0 = (I_all[:, 0].min() + I_all[:, 0].max()) / 2 - (sh.min() + sh.max()) / 2
    def X(p, R, sc):
        t, nu, k, b, sy = p
        return np.c_[t + cx + sc(nu) * (R[:, 0] - cx) + k * (R[:, 1] - cy), b + cy + sy * (R[:, 1] - cy)]
    def f(p):
        do, _ = tree.query(X(p, Ro, lambda nu: 1 - nu)); dc, _ = tree.query(X(p, Rc, lambda nu: 1 - nu * W / w))
        return np.r_[do, dc]
    best = None
    for dt in (-24, -12, 0, 12, 24):
        r = least_squares(f, [t0 + dt, 0.0, math.tan(TH), 0.0, 1.0], loss="soft_l1", f_scale=2.0)
        if best is None or r.cost < best.cost:
            best = r
    t, nu, k, b, sy = best.x; res = f(best.x)
    return dict(nu=float(nu), k=float(k), rho=float(math.atan(k) / TH), sy=float(sy), rms=float(np.sqrt(np.mean(res ** 2))),
                p90=float(np.percentile(res, 90)), W=float(W), w=float(w), n=int(len(res)))


def inflection_dir(cs, keep):
    """the tangent direction (deg, mod 180) at the curvature sign change inside a cubic, among segments whose
    inflection point passes keep(x, y); straight segments between two curves (a spine's anchors) count as the
    inflection itself (their direction)"""
    out = []
    for c in cs:
        ns = c["nodes"]; N = len(ns); ons = [i for i in range(N) if ns[i][2] != "o"]
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [ns[q % N] for q in range(i + 1, i + 1 + ((j - i - 1) % N))]
            P0, P3 = np.array(ns[i][:2]), np.array(ns[j][:2])
            if len(offs) != 2:
                m = (P0 + P3) / 2
                if keep(*m) and np.linalg.norm(P3 - P0) > 5:
                    d = P3 - P0; out.append((m, math.degrees(math.atan2(d[1], d[0])) % 180.0))
                continue
            P1, P2 = np.array(offs[0][:2]), np.array(offs[1][:2])
            ts = np.linspace(0, 1, 400); u = 1 - ts
            d1 = (3 * u * u)[:, None] * (P1 - P0) + (6 * u * ts)[:, None] * (P2 - P1) + (3 * ts * ts)[:, None] * (P3 - P2)
            d2 = (6 * u)[:, None] * (P2 - 2 * P1 + P0) + (6 * ts)[:, None] * (P3 - 2 * P2 + P1)
            k = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
            for q in np.nonzero(np.sign(k[:-1]) != np.sign(k[1:]))[0]:
                t = ts[q]; uu = 1 - t
                p = uu ** 3 * P0 + 3 * uu * uu * t * P1 + 3 * uu * t * t * P2 + t ** 3 * P3
                if keep(*p):
                    out.append((p, math.degrees(math.atan2(d1[q][1], d1[q][0])) % 180.0))
    return out


def main(out_p):
    R = {gl: drawn.raw_contours(gl, "roman") for gl in drawn.FIT_LETTERS}
    I = {gl: drawn.raw_contours(gl, "italic") for gl in drawn.FIT_LETTERS}
    res = {}
    # o: outer and counter
    oc = sorted(R["o"], key=lambda c: -(max(n[0] for n in c["nodes"]) - min(n[0] for n in c["nodes"])))
    ic = samples(I["o"])
    for name, c in (("o outer", oc[0]), ("o counter", oc[1])):
        res[name] = fit_affine(samples([c]), ic, R_all=samples(R["o"]))
    # p: the counter (closed) and the bowl's outer side right of the stem
    pc = sorted(R["p"], key=lambda c: len(c["nodes"]))
    xs_c = [n[0] for n in pc[0]["nodes"]]
    stem_r = min(xs_c)                                    # the counter's left = the stem's right side
    res["p counter"] = fit_affine(samples([pc[0]]), samples(I["p"]), R_all=samples(R["p"]))
    res["p bowl outer"] = fit_affine(samples([pc[1]], keep=lambda x, y: x > stem_r + 25 and y > -20), samples(I["p"]), R_all=samples(R["p"]))
    # a: the bowl's counter (closed) and the bowl's outer side left of the stem, below the bar
    ac = sorted(R["a"], key=lambda c: len(c["nodes"]))
    xa = [n[0] for n in ac[0]["nodes"]]; ya = [n[1] for n in ac[0]["nodes"]]
    res["a counter"] = fit_affine(samples([ac[0]]), samples(I["a"]), R_all=samples(R["a"]))
    res["a bowl outer"] = fit_affine(samples([ac[1]], keep=lambda x, y: x < max(xa) - 10 and y < max(ya) - 5), samples(I["a"]), R_all=samples(R["a"]))
    # s: the two counters' sides (the bowls) and the spine
    sx = [n[0] for c in R["s"] for n in c["nodes"]]; sy_ = [n[1] for c in R["s"] for n in c["nodes"]]
    xm, ym = (min(sx) + max(sx)) / 2, (min(sy_) + max(sy_)) / 2
    res["s upper bowl"] = fit_affine(samples(R["s"], keep=lambda x, y: y > ym + 90), samples(I["s"]), R_all=samples(R["s"]))
    res["s lower bowl"] = fit_affine(samples(R["s"], keep=lambda x, y: y < ym - 90), samples(I["s"]), R_all=samples(R["s"]))
    near = lambda x, y: abs(y - ym) < 130 and abs(x - xm) < 120
    dr_ = inflection_dir(R["s"], near); di_ = inflection_dir(I["s"], near)
    ar = float(np.mean([a for _, a in dr_])); ai = float(np.mean([a for _, a in di_]))
    # the plain slant of the roman spine direction
    a_r = math.radians(ar); v = (math.cos(a_r) + 0.25 * math.sin(a_r), math.sin(a_r)); asl = math.degrees(math.atan2(v[1], v[0])) % 180.0
    res["s spine"] = dict(roman_deg=ar, slant_deg=asl, italic_deg=ai, psi=(ar - ai) / math.degrees(TH),
                          shear_turn=(ar - asl) / math.degrees(TH), edges_roman=[round(a, 2) for _, a in dr_], edges_italic=[round(a, 2) for _, a in di_])
    # the model itself (I10 + I11: one lean, one narrowing per part, counters off by the same units), per part
    res["o (model)"] = fit_part(samples([oc[0]]), samples([oc[1]]), ic, samples(R["o"]))
    res["p bowl (model)"] = fit_part(samples([pc[1]], keep=lambda x, y: x > stem_r + 25 and y > -20),
                                     samples([pc[0]], keep=lambda x, y: x > stem_r + 25), samples(I["p"]), samples(R["p"]))
    res["a bowl (model)"] = fit_part(samples([ac[1]], keep=lambda x, y: x < max(xa) - 10 and y < max(ya) - 5),
                                     samples([ac[0]], keep=lambda x, y: x < max(xa) - 25), samples(I["a"]), samples(R["a"]))
    # summaries
    for k_, v_ in res.items():
        if "s" in v_ and "rho" in v_:
            v_["nu_if_outer"] = 1.0 - v_["s"]
    o_o, o_c = res["o outer"], res["o counter"]
    summ = dict(
        rho_o=(o_o["rho"] + o_c["rho"]) / 2, rho_p_counter=res["p counter"]["rho"], rho_a_counter=res["a counter"]["rho"],
        nu_o=1 - o_o["s"], nu_o_counter_pred=(1 - o_o["s"]) * o_o["W"] / o_c["W"], nu_o_counter_fit=1 - o_c["s"],
        nu_p_bowl=1 - res["p bowl outer"]["s"], psi=res["s spine"]["psi"])
    M = [res[k_] for k_ in ("o (model)", "p bowl (model)", "a bowl (model)")]
    wts = [1.0 / max(m["rms"], 1.0) ** 2 for m in M]
    summ["rho_model"] = {k_: round(res[k_]["rho"], 3) for k_ in ("o (model)", "p bowl (model)", "a bowl (model)")}
    summ["nu_model"] = {k_: round(res[k_]["nu"], 4) for k_ in ("o (model)", "p bowl (model)", "a bowl (model)")}
    summ["rho_fit"] = float(sum(w_ * m["rho"] for w_, m in zip(wts, M)) / sum(wts))
    summ["nu_fit_o_p"] = float(np.mean([res["o (model)"]["nu"], res["p bowl (model)"]["nu"]]))
    summ["nu_coef"] = summ["nu_fit_o_p"] / 0.25     # nu = coef x tan(theta): the number that carries to 18.43 deg
    json.dump(dict(parts=res, summary=summ), open(out_p, "w"), indent=1)
    print("%-15s %7s %7s %7s %7s %7s %6s %5s" % ("part", "s", "k", "rho", "sy", "rms u", "p90", "W"))
    for k_, v_ in res.items():
        if "rho" in v_ and "s" not in v_:
            print("%-15s nu %6.4f       %7.4f %7.3f %7.4f %7.2f %6.2f %5.0f/%.0f" % (k_, v_["nu"], v_["k"], v_["rho"], v_["sy"], v_["rms"], v_["p90"], v_["W"], v_["w"]))
        elif "rho" in v_:
            print("%-15s %7.4f %7.4f %7.3f %7.4f %7.2f %6.2f %5.0f" % (k_, v_["s"], v_["k"], v_["rho"], v_["sy"], v_["rms"], v_["p90"], v_["W"]))
    print("s spine: roman %.2f°, plain slant %.2f°, drawn italic %.2f° -> psi %.3f (the shear turns it %.3f θ); edges %s -> %s" % (
        res["s spine"]["roman_deg"], res["s spine"]["slant_deg"], res["s spine"]["italic_deg"], res["s spine"]["psi"], res["s spine"]["shear_turn"],
        res["s spine"]["edges_roman"], res["s spine"]["edges_italic"]))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[a.index("--json") + 1] if "--json" in a else os.path.join(HERE, "..", "readings", "fit_params.json"))
