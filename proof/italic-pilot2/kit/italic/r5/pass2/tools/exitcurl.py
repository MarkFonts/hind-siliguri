"""Round 5 · pass 2c: the EXIT beak's inner curl (Mark's s, both drawings: the lower beak's counter side arrives at the
beak 42 deg from vertical with a 77 u end radius; the roman 34 deg / 508 u; pass 2b 25 deg / 376 u). Class rule (terminal,
I15 trailing): at a trailing terminal, the end tangent of the COUNTER-side curve turns by k x theta further into the beak
(the opposite of the shear's turn), its handle length solved for the end radius r_end x the stroke width.
Untested beyond the s: the e's flick and the j / y tails are trailing terminals too, but none has a counter side."""
import math
import numpy as np
from comb_p2 import _kappa


def exit_curl(k=1.0, r_ratio=None):
    def post(Sk):
        U = Sk.U; th = Sk.theta
        counters = {nd for r in Sk.runs if r["counter"] for nd in r["nodes"]}
        for t in Sk.term_report:
            if t["leading"]:
                continue
            first, last = t["nodes"][0], t["nodes"][-1]
            for end, sg in ((first, U.seg_before[first]), (last, U.seg_after[last])):
                far = sg["gi"] if sg["gj"] == end else sg["gj"]
                if sg["kind"] != "curve" or far not in counters:
                    continue
                h = sg["offs"][1] if sg["gj"] == end else sg["offs"][0]
                v = Sk.new[h] - Sk.new[end]
                best = None
                for s in (+1, -1):
                    a = s * k * th; R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
                    w = R @ v; d = -w                              # direction INTO the beak at the end node
                    ang = math.degrees(math.atan2(d[0], d[1]))
                    ang = ((ang + 90) % 180) - 90
                    if best is None or ang < best[0]:
                        best = (ang, w)
                Sk.new[h] = Sk.new[end] + best[1]
    return post


def exit_curl_final(cs, up_cs, K, k=1.0):
    """the same rule on a finished letter (the width rules re-fit the handle when it is applied in the skeleton):
    -> contours. The trailing terminal and the counter runs are read on the upright."""
    import copy
    from skeleton_p2 import SkeletonP2
    Sk = SkeletonP2({"contours": up_cs, "width": 470.0, "master": "Regular", "glyph": "s"}); U = Sk.U
    th = math.atan(K); cs = copy.deepcopy(cs); flat = [n for c in cs for n in c["nodes"]]
    P = lambda i: np.array(flat[i][:2], float)
    counters = {nd for r in Sk.runs if r["counter"] for nd in r["nodes"]}
    done = []
    for t in Sk.term_report:
        if t["leading"]:
            continue
        first, last = t["nodes"][0], t["nodes"][-1]
        for end, sg in ((first, U.seg_before[first]), (last, U.seg_after[last])):
            far = sg["gi"] if sg["gj"] == end else sg["gj"]
            if sg["kind"] != "curve" or far not in counters:
                continue
            h = sg["offs"][1] if sg["gj"] == end else sg["offs"][0]
            v = P(h) - P(end); best = None
            for s in (+1, -1):
                a = s * k * th; R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
                w = R @ v; d = -w; ang = ((math.degrees(math.atan2(d[0], d[1])) + 90) % 180) - 90
                if best is None or ang < best[0]:
                    best = (ang, w)
            q = P(end) + best[1]; flat[h][0], flat[h][1] = float(q[0]), float(q[1]); done.append((end, h, round(best[0], 1)))
    return cs, done
