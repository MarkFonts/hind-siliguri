"""Round 5 · pass 2: run the pass-2 pipeline (round_p2.correct, steps 1-6: skeleton I10, I11, I14 serifs, I15-I17, group rules I2-I8 with I13,
harmonizer) on every letter, write GeistSerifItalic_<g> into src/geistserif_italic_<14|18>.json, re-measure on the SAME
rungs, TABLE_<14|18>.json / .md, readings/<14|18>/, the approval sheets sheets/groups_<14|18>/<fname>_groups.png, and
readings/pass2_<14|18>.json (skeleton classes, groups, harmonizer report per letter).

run_italic.py [glyph,glyph,...] [--no-sheets] [--skip=quoteright] [--slant 1/4]     default slant 1/3 (18.43 deg)
"""
import sys, os, json, math, traceback
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import carry as C
from italicmove import ItalicMover
from round_p2 import correct
from measure import counted, rung_name
from readings import readings, fname
from sheet import Panel, bbox_of, BG, SS, font, MENLO, CAL
from partsheet import draw_poly
from groupsheet import GCOLS, group_path, seg_poly, arrow, square, diamond
from rungs import Outline

OUT = C.R5


def tag():
    return "14" if abs(C.K - 0.25) < 1e-9 else "18" if abs(C.K - 1 / 3) < 1e-9 else "%d" % round(1000 * C.K)
GAIN = 10.0          # arrows on the approval sheet are drawn 10x their true length (the moves are 1-5 u)


def gfn(gl):
    return fname("X_" + gl)[2:]


def check_same(a, b):
    fa = [n for c in a for n in c["nodes"]]; fb = [n for c in b for n in c["nodes"]]
    return len(a) == len(b) and len(fa) == len(fb) and all(x[2] == y[2] for x, y in zip(fa, fb)) and \
        all(len(ca["nodes"]) == len(cb["nodes"]) for ca, cb in zip(a, b))


def table_rows(gl, P_up, R, W):
    rows = []
    for si in range(len(P_up.strokes)):
        ids = counted(R, W["up"], si)
        if not ids:
            continue
        ent = dict(part=si, walls=list(P_up.strokes[si]["walls"]), mode=P_up.strokes[si]["mode"])
        for tag in ("up", "sl", "it"):
            t = max(ids, key=lambda i: W[tag][i]["w"]); n = min(ids, key=lambda i: W[tag][i]["w"])
            ent[tag] = dict(thickest=dict(rung=rung_name(R.rungs[t]), w=round(W[tag][t]["w"], 1), dir=C.direction_class(W["up"][t]["t"]),
                                          up=round(W["up"][t]["w"], 1)),
                            thinnest=dict(rung=rung_name(R.rungs[n]), w=round(W[tag][n]["w"], 1), dir=C.direction_class(W["up"][n]["t"]),
                                          up=round(W["up"][n]["w"], 1)))
        # how far each copy is from the target over every counted rung
        for tag in ("sl", "it"):
            d = [W[tag][i]["w"] - W["up"][i]["w"] for i in ids]
            ent[tag]["max_err"] = round(max(d, key=abs), 1)
            ent[tag]["mean_abs_err"] = round(float(np.mean(np.abs(d))), 2)
        # per direction class: mean ratio to the upright
        cls = {}
        for i in ids:
            c = C.direction_class(W["up"][i]["t"])
            cls.setdefault(c, {"sl": [], "it": []})
            for tag in ("sl", "it"):
                cls[c][tag].append(W[tag][i]["w"] / max(1e-6, W["up"][i]["w"]))
        ent["by_direction"] = {c: {tag: round(float(np.mean(v)), 3) for tag, v in d.items()} | {"n": len(d["sl"])} for c, d in cls.items()}
        rows.append(ent)
    return rows


def groups_sheet(gl, IM, g_it, out, PW=900, PH=1000):
    g = IM.g; ol = IM.ol
    R = IM.report()
    bb = bbox_of(ol, pad=60)
    A = Panel(PW, PH, bb, margin=40)
    A.title("GEIST SERIF %.2f° · /%s skeleton base → italic · the groups (I2–I8 with I13; round 5 · pass 2)" % (C.SLANT, gl),
            "colour = one group, ONE vector (arrow ×%g) · ○ graded ⅔ ⅓ · □ anchor · ◇ slid / junction / terminal · red ■ held (serifs, I15 terminals) · white = corrected" % GAIN)
    A.fill_outline(ol, color=(34, 40, 28), edge=(90, 90, 90))
    for k in IM.P.ol.serif_segs:
        draw_poly(A, ol.segs[k].poly, (80, 130, 255), 2.0)
    for gi_, grp in enumerate(IM.groups):
        col = GCOLS[gi_ % len(GCOLS)]
        for a, b in group_path(IM, grp):
            draw_poly(A, seg_poly(IM, ol, a, b), col, 5.0)
        for nd, lv in grp["levels"].items():
            p = IM.xy[nd]
            X, Y = A.pt(p); r = (5 if lv >= 0.99 else 3.5) * SS
            A.d.ellipse([X - r, Y - r, X + r, Y + r], fill=col if lv >= 0.99 else None, outline=col, width=2 * SS)
            if lv < 0.99:
                A.text(p, "×%s" % ("⅔" if lv > 0.5 else "⅓"), col, size=10, dx=6, dy=4)
        for T in grp.get("terminal") or []:
            for nd in T["nodes"]:
                diamond(A, IM.xy[nd], col, 8.0, 1.8)
            arrow(A, IM.xy[T["nodes"][0]], (T["vec"][0] * GAIN, T["vec"][1] * GAIN), col, 1.8, 7)
        cx = np.mean([IM.xy[n][0] for n in grp["levels"]]); cy = np.mean([IM.xy[n][1] for n in grp["levels"]])
        v = (grp["dir"][0] * grp["mag"], grp["dir"][1] * grp["mag"])
        arrow(A, (cx, cy), (v[0] * GAIN, v[1] * GAIN), col, 2.4, 9)
        rr = [x for x in R["groups"][gi_]["rules"]]
        d = IM._dcore_of.get(grp["id"], 0.0) if hasattr(IM, "_dcore_of") else 0.0
        A.text((cx + v[0] * GAIN, cy + v[1] * GAIN), "g%d %.1f u %s [%s]" % (grp["id"], grp["mag"], grp["dir_name"], " ".join(rr)), col, size=10, dx=6, dy=-6)
        for nd in grp["anchors"]:
            if nd in IM.xy:
                square(A, IM.xy[nd], (255, 255, 255), 6.5, w=1.6)
        for nd in grp["slides"]:
            diamond(A, IM.xy[nd], col, 8.0, 1.8)
    for j in IM.slid_junctions:
        diamond(A, IM.xy[j["node"]], (255, 255, 255), 8.0, 1.6)
        v = IM.vec.get(j["node"], (0.0, 0.0))
        arrow(A, IM.xy[j["node"]], (v[0] * GAIN, v[1] * GAIN), (255, 255, 255), 1.6, 7)
    for c in IM.cut_moves:
        arrow(A, IM.xy[c["node"]], (c["vec"][0] * GAIN, c["vec"][1] * GAIN), (255, 90, 90), 1.6, 7)
    SLIDE = (120, 255, 200)
    for sl_ in getattr(IM, "slides_i9", []):
        p0 = IM.xy[sl_["node"]]; v = (sl_["dir"][0] * sl_["slide"], sl_["dir"][1] * sl_["slide"])
        arrow(A, p0, v, SLIDE, 2.6, 9)                      # true length
        diamond(A, p0, SLIDE, 9.0, 2.0)
        A.text((p0[0] + v[0], p0[1] + v[1]), "%.1f u [I9]" % abs(sl_["slide"]), SLIDE, size=10, dx=6, dy=4)
    for nd in IM.held:
        square(A, IM.xy[nd], (255, 80, 70), 4.0, fill=(255, 80, 70))
    ol1 = Outline(g_it["contours"])
    for poly in ol1.polys:
        draw_poly(A, poly + [poly[0]], (245, 245, 245), 1.0)
    A.nodes(ol)
    f = font(MENLO, 9.5)
    lines = []
    for gi_, grp in enumerate(R["groups"]):
        gr = ", ".join("%d×%s" % (n, "⅔" if grp["levels"][n] > 0.5 else "⅓") for n in grp["graded"])
        dd = ", ".join("%d:%+.1f" % (n, IM.delta.get(n, 0.0)) for n in grp["core"])
        lines.append((GCOLS[gi_ % len(GCOLS)], ("[" + " ".join(grp["rules"]) + "]  ") + "g%d core %s (D %s) +carried %s +graded [%s] +slides %s → (%.1f, %.1f) |%.1f| %s  anchors %s" % (
            grp["id"], grp["core"], dd, grp["ext"], gr, grp["slides"], grp["vector"][0], grp["vector"][1], grp["mag"], grp["snap"], grp["anchors"])))
    for t in R["terminals"]:
        lines.append((GCOLS[t["group"] % len(GCOLS)], "[R11] terminal %s → (%.1f, %.1f) with g%d" % (t["nodes"], t["vector"][0], t["vector"][1], t["group"])))
    for j in R["junctions"]:
        lines.append(((235, 235, 235), "[R10] junction %d%s on %s → (%.1f, %.1f)" % (j["node"], "+%d" % j["partner"] if j["partner"] is not None else "", j["kind"], j["vector"][0], j["vector"][1])))
    for c in R["cuts"]:
        lines.append(((255, 120, 120), "[R12] cut face %d → (%.1f, %.1f)" % (c["node"], c["vector"][0], c["vector"][1])))
    for p in R["pinch"]:
        lines.append(((255, 120, 120), "[I3/R12] pinch %d → (%.1f, %.1f)" % (p["node"], p["vector"][0], p["vector"][1])))
    lines.append(((170, 170, 170), "[R14] connecting curves (scale, turn): %s" % (", ".join("%d-%d ×%.3f %+.1f°" % c for c in R["connecting"]) or "-")))
    lines.append(((120, 255, 200), "[I9] half-angle extrema (tan(slant/2) x lever): %s" % (
        ", ".join("%d %.1f u (lever %.0f)" % (x["node"], x["slide"], x["lever"]) for x in R["slides"]) or "-")))
    y = (PH - 18 - 13 * len(lines)) * SS
    for col, s_ in lines:
        A.d.text((16 * SS, y), s_, fill=col, font=f); y += 13 * SS
    A.out().save(out)


def three_up(gl, G, out, W=520, H=600):
    """upright | slant | corrected, filled by the nonzero rule (overlapping contours as the font renders them);
    the corrected panel carries the slant's outline in red"""
    import skia
    from shear_check import glyph_path
    keys = ["GeistSerifRegular_" + gl, "GeistSerifSlant_" + gl, "GeistSerifItalic_" + gl]
    ols = [Outline(G[k]["contours"]) for k in keys]
    bbs = [bbox_of(o, 50) for o in ols]
    bb = (min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs))
    sc = min((W - 40) / (bb[2] - bb[0]), (H - 80) / (bb[3] - bb[1]))
    ox = (W - (bb[2] - bb[0]) * sc) / 2 - bb[0] * sc; oy = 50 + bb[3] * sc
    xf = lambda q: (ox + q[0] * sc, oy - q[1] * sc)
    surf = skia.Surface(W * 3 + 20, H); c = surf.getCanvas(); c.clear(skia.Color(*BG))
    font_ = skia.Font(skia.Typeface("Menlo"), 15)
    for i, (k, nm) in enumerate(zip(keys, ("upright", "slant", "corrected"))):
        c.save(); c.translate(i * (W + 10), 0)
        c.drawPath(glyph_path(G[k]["contours"], xf), skia.Paint(Color=skia.Color(228, 228, 228), AntiAlias=True))
        if i == 2:
            c.drawPath(glyph_path(G[keys[1]]["contours"], xf), skia.Paint(Color=skia.Color(235, 60, 60), AntiAlias=True,
                                                                          Style=skia.Paint.kStroke_Style, StrokeWidth=1.0))
        c.drawString("/%s %s" % (gl, nm), 16, 26, font_, skia.Paint(Color=skia.Color(232, 184, 74), AntiAlias=True))
        c.restore()
    surf.makeImageSnapshot().save(out, skia.kPNG)


def main(gls=None, sheets=True, skip=()):
    G = C.load()
    gls = gls or C.glyphs(G)
    T = tag()
    gdir = os.path.join(OUT, "sheets", "groups_" + T); rdir = os.path.join(OUT, "readings", T)
    os.makedirs(gdir, exist_ok=True); os.makedirs(rdir, exist_ok=True)
    tab_p = os.path.join(OUT, "TABLE_%s.json" % T)
    rep5_p = os.path.join(OUT, "readings", "pass2_%s.json" % T)
    REP5 = json.load(open(rep5_p)) if os.path.exists(rep5_p) else {}
    TABLE = json.load(open(tab_p)) if os.path.exists(tab_p) else {}
    reports = {}
    for gl in gls:
        up, sl = G["GeistSerifRegular_" + gl], G["GeistSerifSlant_" + gl]
        if gl in skip:
            # left out on the command line: the Italic copy is the slant unchanged (reported in NOTES.md)
            G["GeistSerifItalic_" + gl] = {"contours": sl["contours"], "width": sl["width"], "master": "Italic", "glyph": gl, "uncorrected": True}
            Pu = C.parts_of(up); R = C.Rungs(Pu)
            W = {"up": R.widths(up["contours"]), "sl": R.widths(sl["contours"])}; W["it"] = W["sl"]
            TABLE[gl] = table_rows(gl, Pu, R, W)
            for p_ in TABLE[gl]:
                p_["skipped"] = True
            print("%-10s SKIPPED (Italic = slant)" % gl); continue
        try:
            res = correct(gl, G, "1-6")
            IM = res["mover"]
        except Exception:
            traceback.print_exc(); print("FAIL", gl); continue
        cs = res["contours"]
        hrep = res["harmonize"] or {}
        REP5[gl] = dict(skeleton=res["skeleton"].report(),
                        harmonize=dict(nodes=hrep.get("nodes", []), reaim=hrep.get("reaim", []), skipped=[list(map(str, x)) for x in hrep.get("skipped", [])],
                                       refused=[list(map(str, x)) for x in hrep.get("refused", [])], max_slide=hrep.get("max_slide"),
                                       max_handle_move=hrep.get("max_handle_move"), reverted_r23=hrep.get("reverted_r23"), dropped_r23=hrep.get("dropped_r23"),
                                       r23_worst_loss_u=hrep.get("r23_worst_loss_u"), r23_new_thin=hrep.get("r23_new_thin")),
                        retensioned=[list(map(float, x)) for x in getattr(IM, "retensioned", [])])
        assert check_same(sl["contours"], cs), gl
        it = {"contours": cs, "width": sl["width"], "master": "Italic", "glyph": gl}
        G["GeistSerifItalic_" + gl] = it
        # readings for the corrected copy (its own pairing, read at the italic angle)
        P_it = C.parts_of(it)
        json.dump(readings(P_it, gl, "Italic"), open(os.path.join(rdir, fname("GeistSerifItalic_" + gl) + ".readings.json"), "w"))
        # re-measure on the upright's rungs
        R = C.Rungs(IM.P_up)
        W = {"up": R.widths(up["contours"]), "sl": R.widths(sl["contours"]), "it": R.widths(cs)}
        TABLE[gl] = table_rows(gl, IM.P_up, R, W)
        rep = IM.report()
        reports[gl] = dict(groups=len(rep["groups"]), moved=sum(1 for v in IM.vec.values() if math.hypot(*v) > 0.05),
                           max_move=round(max([math.hypot(*v) for v in IM.vec.values()] or [0.0]), 2))
        print("%-10s groups %d · moved nodes %d · largest move %.2f u" % (gl, reports[gl]["groups"], reports[gl]["moved"], reports[gl]["max_move"]))
        for p in TABLE[gl]:
            print("   part %d: thickest up %.1f sl %.1f it %.1f (%s) · thinnest up %.1f sl %.1f it %.1f (%s) · max err sl %+.1f it %+.1f · mean|err| sl %.2f it %.2f" % (
                p["part"], p["up"]["thickest"]["w"], p["sl"]["thickest"]["w"], p["it"]["thickest"]["w"], p["sl"]["thickest"]["dir"],
                p["up"]["thinnest"]["w"], p["sl"]["thinnest"]["w"], p["it"]["thinnest"]["w"], p["sl"]["thinnest"]["dir"],
                p["sl"]["max_err"], p["it"]["max_err"], p["sl"]["mean_abs_err"], p["it"]["mean_abs_err"]))
        if sheets:
            groups_sheet(gl, IM, it, os.path.join(gdir, gfn(gl) + "_groups.png"))
    json.dump(G, open(C.SRC, "w"))
    json.dump(TABLE, open(tab_p, "w"), indent=1)
    json.dump(REP5, open(rep5_p, "w"), indent=1, default=lambda o: float(o) if hasattr(o, "__float__") else str(o))
    write_md(TABLE, os.path.join(OUT, "TABLE_%s.md" % T))
    # readings index: add the Italic keys
    idx_p = os.path.join(rdir, "index.json")
    index = {r["key"]: r for r in (json.load(open(idx_p)) if os.path.exists(idx_p) else [])}
    for gl in gls:
        key = "GeistSerifItalic_" + gl
        if key in G:
            P = C.parts_of(G[key])
            index[key] = {"key": key, "ok": True, "slant": C.SLANT, "stem": C.stem_of(gl), "strokes": len(P.strokes), "flags": len(P.flags),
                          "serif_kinds": sorted({s["kind"] for s in P.ol.serifs}), "unpaired_sides": P.unpaired}
    json.dump(sorted(index.values(), key=lambda r: r["key"]), open(idx_p, "w"), indent=1)


def write_md(TABLE, path):
    L = ["# Geist Serif Regular: upright, %.2f° slant, round-5 corrected italic — per part" % C.SLANT, "",
         "Every width is read on the SAME rung (the upright's pairing carried node for node). `thickest` / `thinnest` = that copy's "
         "own extreme among the part's counted rungs (roots and terminal tapers left out); rung names: `a↔b` a node rung, "
         "`a↔b..c↔d@f%` a dense rung f of the way between two node rungs; `·` = a point between nodes. dir = the stroke direction "
         "of the rung on the upright. err = copy − upright on every counted rung (max signed, mean absolute). "
         "`by direction` = mean width ratio to the upright per stroke direction.", ""]
    for gl in sorted(TABLE, key=lambda s: (s.lower(), s)):
        L += ["## /%s%s" % (gl, " — LEFT OUT: corrected = slant (see NOTES.md)" if any(p.get("skipped") for p in TABLE[gl]) else ""), "",
              "| part | | upright | slant | corrected | dir |", "|---|---|---|---|---|---|"]
        for p in TABLE[gl]:
            for which in ("thickest", "thinnest"):
                L.append("| %d %s | %s | %s %.1f | %s %.1f | %s %.1f | %s |" % (
                    p["part"], p["mode"], which, p["up"][which]["rung"], p["up"][which]["w"], p["sl"][which]["rung"], p["sl"][which]["w"],
                    p["it"][which]["rung"], p["it"][which]["w"], p["sl"][which]["dir"]))
            L.append("| | err | | max %+.1f, mean %.2f | max %+.1f, mean %.2f | |" % (p["sl"]["max_err"], p["sl"]["mean_abs_err"], p["it"]["max_err"], p["it"]["mean_abs_err"]))
            L.append("| | by direction | | %s | %s | |" % (", ".join("%s %.3f" % (c, d["sl"]) for c, d in p["by_direction"].items()),
                                                         ", ".join("%s %.3f" % (c, d["it"]) for c, d in p["by_direction"].items())))
        L.append("")
    open(path, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    C.set_slant(C.parse_slant(sys.argv))
    sys.argv = [sys.argv[0]] + C.strip_slant(sys.argv[1:])
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    skip = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--skip=")]
    skip = skip[0].split(",") if skip else ()
    main(args[0].split(",") if args else None, sheets="--no-sheets" not in sys.argv, skip=skip)
