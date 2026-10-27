"""Round 5, step 6: the harmonizer (wmparts/harmonize.py, the clean-room one, NOT the GPL Curvatura port) as the LAST
pass, on the joints round 5 touched.

harmonize_pass(gl, up, base, cs, IM) -> (contours, report)      base = the skeleton glyph

  what moves    every smooth curve-to-curve joint whose cubics the WIDTH rules (I2-I8 with I13, re-tension) moved away
                from the skeleton base (I10-I12, I14)
  target        "drawn" = the base's own curvature ratio kA/kB at each joint: the roman's wherever the skeleton is affine
                on both sides of the node (an affine map keeps a smooth node's ratio), and the spine's where I12 shaped
                it. (The first version targeted the PLAIN SLANT's ratio: it handed the s's spine handles back to the
                roman, +26-33 u, and undid I12 -- the spine came out 18 u thicker. R23 cannot see that: it only guards
                thinning.)
  mode          "auto": slide the node along its tangent, unless it is pinned (an extreme or a metric-line node: then
                handles only) or the slide is over 20 u; re-aim (turn both handles about the node, within +-25 deg) only
                where a side's curvature sign flipped
  never         held serifs / flags / brackets / spurs, junctions, cut faces, pinches (italicmove's classes on the
                corrected letter) -- their joints are skipped and their handles kept
  R23           a re-aim that makes a part's thinnest rung thinner than the correction left it is refused
                (reaim_rung_tol 0.05 u); after everything, a rung newly thinner (rungcheck, 1.5 u) than before this pass
                backs its nearest changed joint off one step (a slide becomes handles only, a handle scale or re-aim is
                dropped), up to 8 rounds -- harmonize_move's loop with the slant as the drawn target
                The same back-off runs for a rung more than 1.5 u THICKER than before this pass (round 5: the harmonizer
                must not undo I13's widths either; without it the p bowl and the n arch came back 4-6 u heavier).
The report lists every joint, its operation and size, the re-aims and the R23 back-offs.
"""
import sys, os, math, copy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "..")))     # core/parts (wmparts)
from wmparts import harmonize as HM
from wmparts import rungcheck


class _AsMove:
    """the corrected ItalicMover seen as a Move for rungcheck: drawn = the outline the rules started from (xy),
    new = the outline being judged"""
    def __init__(self, IM, new):
        self.xy = IM.xy; self.new = new; self.M = IM.M; self.P = IM.P; self.ol = IM.ol
        for k in ("held", "junction", "cut_face", "pinch", "how", "slant", "g", "seg_after", "seg_before", "contours"):
            if hasattr(IM, k):
                setattr(self, k, getattr(IM, k))
        # every part is checked (in the italic every part may be corrected; rungcheck skips stems and dots itself)
        self.stroke_grows = {si: True for si in range(len(IM.M.stroke_rows))}


def _flat_new(contours):
    out = {}; k = 0
    for c in contours:
        for n in c["nodes"]:
            out[k] = (float(n[0]), float(n[1])); k += 1
    return out


def harmonize_pass(gl, up, base, cs, IM, mode="auto", reaim_rung_tol=0.05, **kw):
    gm = HM.Glyph(copy.copy({"contours": cs, "glyph": gl, "master": "Italic", "width": up["width"]}))
    gm["contours"] = cs
    gm["_mi"] = dict(IM.M.mi) if hasattr(IM.M, "mi") else {}
    exclude = set(IM.held) | set(IM.junction) | set(IM.cut_face) | set(IM.pinch)
    drawn = base["contours"]
    handles_only = set()
    M0 = _AsMove(IM, _flat_new(cs))
    base_thin = {(t["stroke"], t["sa"], t["sb"]) for t in rungcheck.thin(M0)}
    base_all = {(t["stroke"], t["sa"], t["sb"]): t for t in rungcheck.thin(M0, tol=-1e9)}
    base_min = {}
    for k, t in base_all.items():
        base_min[k[0]] = min(base_min.get(k[0], 1e9), t["moved"])

    def rung_fn(Y):
        new = {k: (float(Y[k][0]), float(Y[k][1])) for k in range(len(Y))}
        rows = rungcheck.thin(_AsMove(IM, new), tol=-1e9)
        pen, mins, ok = 0.0, {}, True
        for t in rows:
            k = (t["stroke"], t["sa"], t["sb"]); b = base_all.get(k)
            mins[k[0]] = min(mins.get(k[0], 1e9), t["moved"])
            if b is None:
                continue
            pen = max(pen, b["moved"] - t["moved"])
            if t["moved"] < t["drawn"] - rungcheck.TOL <= b["moved"]:
                ok = False
        ok = ok and all(v >= base_min.get(si, -1e9) - reaim_rung_tol for si, v in mins.items())
        return pen, ok

    reverted, dropped = [], []
    rep = None
    for _ in range(8):
        hg, rep = HM.harmonize_glyph(gm, nodes=None, mode=mode, target="drawn", drawn=drawn, exclude=exclude,
                                     slant=IM.slant, handles_only=handles_only, rung_fn=rung_fn, **kw)
        new = _flat_new(hg["contours"])
        thin = [t for t in rungcheck.thin(_AsMove(IM, new)) if (t["stroke"], t["sa"], t["sb"]) not in base_thin]
        # the same guard the other way (round 5): harmonizing must not undo I13 either -- a rung more than 1.5 u
        # THICKER than the width rules left it backs its joint off too
        for t in rungcheck.thin(_AsMove(IM, new), tol=-1e9):
            b = base_all.get((t["stroke"], t["sa"], t["sb"]))
            if b is not None and t["moved"] > b["moved"] + rungcheck.TOL:
                thin.append(t)
        if not thin:
            break
        how = {n["node"]: n["how"] for n in rep["nodes"] if n["slide"] > 0.05 or max(n["handle_moves"]) > 0.05 or n.get("reaim") is not None}
        if not how:
            break
        for t in thin:
            c = np.array(t["at"], float)
            nd = next((x for x in (t.get("nodes") or ()) if x in how), None)
            if nd is None:
                nd = min(how, key=lambda x: math.hypot(*(np.array(new[x]) - c)))
            if how[nd] == "slide" and nd not in handles_only:
                handles_only.add(nd); reverted.append(nd)
            else:
                exclude.add(nd); dropped.append(nd)
    rep["reverted_r23"] = reverted
    rep["dropped_r23"] = sorted(set(dropped))
    # R23 check of the result against the corrected outline it started from
    rows = rungcheck.thin(_AsMove(IM, _flat_new(hg["contours"])), tol=-1e9)
    worst = 0.0
    for t in rows:
        b = base_all.get((t["stroke"], t["sa"], t["sb"]))
        if b is not None:
            worst = max(worst, b["moved"] - t["moved"])
    gain = 0.0
    for t in rows:
        b = base_all.get((t["stroke"], t["sa"], t["sb"]))
        if b is not None:
            gain = max(gain, t["moved"] - b["moved"])
    rep["r23_worst_loss_u"] = round(float(worst), 2)
    rep["worst_gain_u"] = round(float(gain), 2)
    rep["r23_new_thin"] = len([t for t in rungcheck.thin(_AsMove(IM, _flat_new(hg["contours"]))) if (t["stroke"], t["sa"], t["sb"]) not in base_thin])
    out = [{"closed": c.get("closed", True), "nodes": [[float(n[0]), float(n[1])] + list(n[2:]) for n in c["nodes"]]} for c in hg["contours"]]
    return out, rep
