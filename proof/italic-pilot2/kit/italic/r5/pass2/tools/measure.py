"""Step 3: readings for every copy, the upright-vs-slant pairing check, and the measurement sheets.

measure.py [glyph,glyph,...]
  italic/readings/<fname>.readings.json  (each copy's OWN pairing, readings.py format) + index.json
  italic/readings/pairing_check.json     where the slant's own pairing disagrees with the upright's
  italic/sheets/<fname>_measure.png      upright | slant, measured on the UPRIGHT's rungs carried node for node
"""
import sys, os, json, math, traceback
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import carry as C
from readings import readings, fname
from sheet import Panel, bbox_of, BG, SS, font, MENLO
from partsheet import draw_poly
from rungs import Outline

OUT = os.path.join(C.WORK, "italic")
THICK, THIN = (255, 120, 60), (90, 200, 255)


def counted(R, Wu, si):
    """the rungs that measure a part: not a root (it emerges from another part), not a terminal tip (an end rung
    under half the part's median width, read inward from either end: the stroke closing to its point)"""
    rows = [(i, r) for i, r in enumerate(R.rungs) if r["si"] == si and r["kind"] != "root" and Wu[i]["w"] >= 5.0]
    if not rows:
        return []
    med = float(np.median([Wu[i]["w"] for i, _ in rows]))
    ids = [i for i, _ in rows]
    while len(ids) > 2 and Wu[ids[0]]["w"] < 0.5 * med:        # a taper into a tip, from either end
        ids.pop(0)
    while len(ids) > 2 and Wu[ids[-1]]["w"] < 0.5 * med:
        ids.pop()
    return ids


def part_extremes(R, W, si, Wu=None):
    ids = counted(R, Wu or W, si)
    rows = [(R.rungs[i], W[i]) for i in ids]
    if not rows:
        return None, None
    return max(rows, key=lambda x: x[1]["w"]), min(rows, key=lambda x: x[1]["w"])


def rung_name(r):
    if r["kind"] == "dense":
        (a0, b0), (a1, b1), f = r["between"]
        nm = lambda a, b: "%s↔%s" % ("·" if a is None else a, "·" if b is None else b)
        return "%s..%s@%.0f%%" % (nm(a0, b0), nm(a1, b1), 100 * f)
    return "%s↔%s" % ("·" if r["a"] is None else r["a"], "·" if r["b"] is None else r["b"])


def node_rung_set(P):
    out = set()
    for st in P.strokes:
        for r in st["rungs"]:
            if r[3] is not None and r[4] is not None and r[2] != "cross":
                out.add(frozenset((r[3], r[4])))
    return out


def held_set(P):
    ol = P.ol
    return {(ol.segs[k].gi, ol.segs[k].gj) for k in ol.serif_segs}


def side_sets(P):
    out = []
    for st in P.strokes:
        a = frozenset(nd for _, nd in st["A"].nodes if nd is not None); b = frozenset(nd for _, nd in st["B"].nodes if nd is not None)
        out.append(frozenset((a, b)))
    return set(out)


def compare(Pu, Ps):
    ru, rs = node_rung_set(Pu), node_rung_set(Ps)
    hu, hs = held_set(Pu), held_set(Ps)
    su, ss = side_sets(Pu), side_sets(Ps)
    fmt = lambda S: sorted(sorted(x) for x in S)
    return dict(agree=(ru == rs and hu == hs and su == ss),
                rungs_only_upright=fmt(ru - rs), rungs_only_slant=fmt(rs - ru),
                held_only_upright=sorted(hu - hs), held_only_slant=sorted(hs - hu),
                strokes_upright=len(Pu.strokes), strokes_slant=len(Ps.strokes),
                parts_differ=len(su ^ ss))


def panel(g, P_draw, R, W, title, sub, bb, PW=820, PH=920, Wu=None):
    ol = Outline(g["contours"])
    A = Panel(PW, PH, bb, margin=40)
    A.title(title, sub)
    A.fill_outline(ol, color=(36, 44, 30), edge=(110, 110, 110))
    # held (flags) in blue
    for k in P_draw.ol.serif_segs:
        draw_poly(A, ol.segs[k].poly, (80, 130, 255), 2.2)
    ext = {}
    for si in range(len(P_draw.strokes)):
        t, n = part_extremes(R, W, si, Wu)
        if t:
            ext[id(t[0])] = THICK; ext[id(n[0])] = THIN
    k_dense = 0
    for r, w in zip(R.rungs, W):
        col = ext.get(id(r))
        if col:
            continue
        if r["kind"] == "dense":
            A.line(w["pa"], w["pb"], (95, 95, 95), 0.6)
            k_dense += 1
            if k_dense % 3 == 0:
                c = ((w["pa"][0] + w["pb"][0]) / 2, (w["pa"][1] + w["pb"][1]) / 2)
                A.text(c, "%.0f" % w["w"], (120, 120, 120), size=6.5, dx=2, dy=-4)
        else:
            c0 = (170, 170, 170) if r["kind"] != "root" else (120, 90, 60)
            A.line(w["pa"], w["pb"], c0, 1.2)
            c = ((w["pa"][0] + w["pb"][0]) / 2, (w["pa"][1] + w["pb"][1]) / 2)
            A.text(c, ("root" if r["kind"] == "root" else "%.0f" % w["w"]), c0, size=7.5, dx=3, dy=-9)
    for r, w in zip(R.rungs, W):
        col = ext.get(id(r))
        if not col:
            continue
        A.line(w["pa"], w["pb"], col, 3.0)
        c = ((w["pa"][0] + w["pb"][0]) / 2, (w["pa"][1] + w["pb"][1]) / 2)
        A.text(c, "%.1f %s" % (w["w"], rung_name(r)), col, size=9.5, dx=4, dy=-12)
    A.nodes(ol, labels=True)
    return A


def measure_sheet(gl, G, R, Wu, Ws, Pu, out):
    up, sl = G["GeistSerifRegular_" + gl], G["GeistSerifSlant_" + gl]
    olu, ols = Outline(up["contours"]), Outline(sl["contours"])
    b1, b2 = bbox_of(olu, 60), bbox_of(ols, 60)
    bb = (min(b1[0], b2[0]), min(b1[1], b2[1]), max(b1[2], b2[2]), max(b1[3], b2[3]))
    sub = "orange = thickest, cyan = thinnest rung of each part · grey = node rungs, dim = dense rungs (every 3rd labelled) · blue edges = held (serifs, flags)"
    A = panel(up, Pu, R, Wu, "/%s upright (Regular) · its own pairing, measured" % gl, sub, bb)
    Pc = C.carry(Pu, sl["contours"])
    B = panel(sl, Pc, R, Ws, Wu=Wu, title="/%s slant (x + y/4, 14.04°) · the UPRIGHT's rungs carried node for node" % gl, sub=sub, bb=bb)
    im = Image.new("RGB", (A.w * 2 + 10, A.h), BG)
    im.paste(A.out(), (0, 0)); im.paste(B.out(), (A.w + 10, 0)); im.save(out)


def main(gls=None):
    G = C.load()
    gls = gls or C.glyphs(G)
    os.makedirs(os.path.join(OUT, "readings"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "sheets"), exist_ok=True)
    idx_p = os.path.join(OUT, "readings", "index.json")
    index = {r["key"]: r for r in (json.load(open(idx_p)) if os.path.exists(idx_p) else [])}
    chk_p = os.path.join(OUT, "readings", "pairing_check.json")
    checks = json.load(open(chk_p)) if os.path.exists(chk_p) else {}
    meas_p = os.path.join(OUT, "readings", "measure.json")
    meas = json.load(open(meas_p)) if os.path.exists(meas_p) else {}
    for gl in gls:
        Ps = {}
        for tag in ("Regular", "Slant", "Italic"):
            key = "GeistSerif%s_%s" % (tag, gl)
            if key not in G:
                continue
            g = G[key]
            try:
                P = C.parts_of(g); Ps[tag] = P
                Rd = readings(P, g["glyph"], g["master"])
                json.dump(Rd, open(os.path.join(OUT, "readings", fname(key) + ".readings.json"), "w"))
                kinds = {}
                for n in Rd["nodes"]:
                    kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
                index[key] = {"key": key, "ok": True, "slant": C.slant_of(g), "stem": C.stem_of(gl), "strokes": len(P.strokes),
                              "flags": len(P.flags), "serif_kinds": sorted({s["kind"] for s in P.ol.serifs}),
                              "unpaired_sides": P.unpaired, "node_kinds": kinds}
            except Exception as e:
                index[key] = {"key": key, "ok": False, "error": repr(e), "trace": traceback.format_exc()[-600:]}
                print("FAIL", key, e)
        Pu = Ps["Regular"]
        checks[gl] = compare(Pu, Ps["Slant"])
        R = C.Rungs(Pu)
        up, sl = G["GeistSerifRegular_" + gl], G["GeistSerifSlant_" + gl]
        Wu, Ws = R.widths(up["contours"]), R.widths(sl["contours"])
        parts = []
        for si in range(len(Pu.strokes)):
            rows = [(R.rungs[i], Wu[i], Ws[i]) for i in counted(R, Wu, si)]
            if not rows:
                continue
            tu = max(rows, key=lambda x: x[1]["w"]); nu = min(rows, key=lambda x: x[1]["w"])
            ts = max(rows, key=lambda x: x[2]["w"]); ns = min(rows, key=lambda x: x[2]["w"])
            parts.append(dict(part=si, walls=list(Pu.strokes[si]["walls"]), mode=Pu.strokes[si]["mode"],
                              upright=dict(thickest=[rung_name(tu[0]), round(tu[1]["w"], 1)], thinnest=[rung_name(nu[0]), round(nu[1]["w"], 1)]),
                              slant=dict(thickest=[rung_name(ts[0]), round(ts[2]["w"], 1), C.direction_class(ts[1]["t"])],
                                         thinnest=[rung_name(ns[0]), round(ns[2]["w"], 1), C.direction_class(ns[1]["t"])]),
                              ratio_range=[round(min(b["w"] / a["w"] for _, a, b in rows), 3), round(max(b["w"] / a["w"] for _, a, b in rows), 3)]))
        meas[gl] = parts
        measure_sheet(gl, G, R, Wu, Ws, Pu, os.path.join(OUT, "sheets", fname("GeistSerifRegular_" + gl).replace("GeistSerifRegular_", "") + "_measure.png"))
        c = checks[gl]
        print("%-10s parts %d · slant pairing %s%s" % (gl, len(parts), "agrees" if c["agree"] else "DIFFERS",
              "" if c["agree"] else " (rungs only upright %s, only slant %s, held diff %d/%d, strokes %d vs %d)" % (
                  c["rungs_only_upright"], c["rungs_only_slant"], len(c["held_only_upright"]), len(c["held_only_slant"]), c["strokes_upright"], c["strokes_slant"])))
        for p in parts:
            print("   part %d %-6s thickest %s %.1f -> slant %s %.1f (%s) · thinnest %s %.1f -> slant %s %.1f (%s) · slant/upright %s" % (
                p["part"], p["mode"], p["upright"]["thickest"][0], p["upright"]["thickest"][1], p["slant"]["thickest"][0], p["slant"]["thickest"][1], p["slant"]["thickest"][2],
                p["upright"]["thinnest"][0], p["upright"]["thinnest"][1], p["slant"]["thinnest"][0], p["slant"]["thinnest"][1], p["slant"]["thinnest"][2], p["ratio_range"]))
    json.dump(sorted(index.values(), key=lambda r: r["key"]), open(idx_p, "w"), indent=1)
    json.dump(checks, open(chk_p, "w"), indent=1)
    json.dump(meas, open(meas_p, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1].split(",") if len(sys.argv) > 1 else None)
