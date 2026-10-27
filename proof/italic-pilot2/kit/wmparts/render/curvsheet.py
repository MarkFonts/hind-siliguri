"""Curvature-comb renders, index sheets, CURV.md and the curvcomb command line (PIL). The judging is wmparts.curvcomb.

  python3.13 -m wmparts.render.curvsheet SET.json OUTDIR [--mover groupmove:GroupMover]... [--keys k1,k2|all]
  python3.13 -m wmparts.render.curvsheet --md OUTDIR
  python3.13 -m wmparts.render.curvsheet SET.json OUTDIR --zoom KEY:x0,y0,x1,y1 [--mover ...]
--mover MODULE:CLASS names a mover in the wmparts package (move:Mover = wmparts.mover.Mover, groupmove:GroupMover).
"""
import sys, os, json, math, importlib, argparse, glob, traceback
import numpy as np
from PIL import Image, ImageDraw
from ..curvcomb import *          # noqa: F401,F403  the judging (segments, analyse, evaluate, thresholds ...)
from ..curvcomb import ORDER, worst_first
from .draw import fontlabel, Panel, BG, SS, font, MENLO, CAL
from ..rungs import Outline
from ..font import fname
from .. import crosscheck


# --- drawing --------------------------------------------------------------------------------
def kcol(a, scale):
    u = min(1.0, a / (2.5 * scale))
    stops = [(0.0, (242, 214, 64)), (0.45, (247, 150, 40)), (1.0, (255, 30, 30))]
    for (p, ca), (q, cb) in zip(stops, stops[1:]):
        if u <= q:
            f = (u - p) / (q - p)
            return tuple(int(ca[i] + (cb[i] - ca[i]) * f) for i in range(3))
    return stops[-1][1]


def comb(A, contours, touched, scale, kgain, Lmax, width=1.0, teeth=True):
    segs, per, _, _ = analyse(contours)
    for si, (s, p) in enumerate(zip(segs, per)):
        if p is None:
            continue
        on = touched[si]
        tips = []
        for k, B, n in zip(p["k"], p["B"], p["n"]):
            if np.isnan(k):
                continue
            L = min(Lmax, kgain * abs(k))
            tip = (B[0] - np.sign(k) * n[0] * L, B[1] - np.sign(k) * n[1] * L)
            col = kcol(abs(k), scale) if on else GREY
            if teeth:
                A.d.line([A.pt(B), A.pt(tip)], fill=col, width=max(1, int(0.7 * width * SS)))
            tips.append((tip, col))
        for (a, ca), (b, cb) in zip(tips, tips[1:]):
            A.d.line([A.pt(a), A.pt(b)], fill=cb, width=max(1, int(1.4 * width * SS)))


def curve_poly(P, n=48):
    t = np.linspace(0, 1, n); B, _, _ = cubic(P, t)
    return [tuple(b) for b in B]


def node_marks(A, contours, J, labels=True, size=9):
    snapn = {r["node"]: r for r in J["snaps"]}; minn = {r["node"]: r for r in J["minors"]}
    f = font(MENLO, size); fb = font(MENLO, size + 3)
    gi = 0
    for c in contours:
        for n in c["nodes"]:
            if n[2] != "o":
                X, Y = A.pt((n[0], n[1])); r = 2.3 * SS
                A.d.rectangle([X - r, Y - r, X + r, Y + r], fill=(235, 235, 235))
                if gi in snapn or gi in minn:
                    row = snapn.get(gi) or minn[gi]
                    col = SNAPC if gi in snapn else MINORC
                    R = (11 if gi in snapn else 8) * SS
                    A.d.ellipse([X - R, Y - R, X + R, Y + R], outline=col, width=int(2.2 * SS))
                    if labels:
                        A.d.text((X + R + 2 * SS, Y - 9 * SS), "%d" % gi, fill=col, font=fb)
                        if size >= 9:
                            A.d.text((X + R + 2 * SS, Y + 5 * SS), ("kink %.1f°  " % row["kink"] if row.get("kink") else "") + "bump %.1fu  r%.0f" % (max(0, row["bump"]), row["R1"]), fill=col, font=f)
                elif labels:
                    A.d.text((X + 4 * SS, Y + 1 * SS), str(gi), fill=(232, 184, 74), font=f)
            gi += 1


def spike_marks(A, contours, J, labels=True):
    segs = {(s[0], s[1]): s for s in segments(contours)}
    for lst, col, w in ((J["minor_spikes"], MINORC, 1.6), (J["spikes"], SPIKEC, 3.2)):
        for sp in lst:
            s = segs.get(tuple(sp["seg"]))
            if not s:
                continue
            A.d.line([A.pt(p) for p in curve_poly(s[3])], fill=col, width=int(w * SS))
            if lst is J["spikes"]:
                for a, b in ((s[3][0], s[3][1]), (s[3][3], s[3][2])):
                    A.d.line([A.pt(a), A.pt(b)], fill=(200, 120, 230), width=SS)
                    X, Y = A.pt(b); r = 2.4 * SS
                    A.d.ellipse([X - r, Y - r, X + r, Y + r], outline=(200, 120, 230), width=SS)
                if labels:
                    m = curve_poly(s[3], 3)[1]
                    A.text(m, "%d-%d r%.0f->%.1f" % (s[0], s[1], sp["r0"], sp["r1"]), SPIKEC, size=10, dx=6, dy=4)


def cross_marks(A, J, labels=True, size=10):
    f = font(MENLO, size)
    for c in J.get("crosses", []):
        x0, y0, x1, y1 = c["bbox"]
        p0, p1 = A.pt((x0 - 8, y1 + 8)), A.pt((x1 + 8, y0 - 8))
        line = c["status"] in ("line", "info")
        col = (150, 150, 255) if c["status"] == "info" else (CROSSC if not line else (40, 120, 140))
        A.d.ellipse([p0[0], p0[1], p1[0], p1[1]], outline=col, width=int((2.6 if not line else 1.2) * SS))
        if labels:
            A.d.text((p1[0] + 3 * SS, p0[1]), crosscheck.label(c), fill=col if c["status"] == "info" else CROSSC, font=f)


def handles(A, contours, which, col=(110, 150, 220)):
    """draw handles of the curves adjacent to flagged nodes"""
    for s in segments(contours):
        if s[2] == "curve" and (s[0] in which or s[1] in which):
            for a, b in ((s[3][0], s[3][1]), (s[3][3], s[3][2])):
                A.d.line([A.pt(a), A.pt(b)], fill=col, width=SS)
                X, Y = A.pt(b); r = 2.2 * SS
                A.d.ellipse([X - r, Y - r, X + r, Y + r], outline=col, width=SS)


def glyph_bbox(res, pad):
    pts = [p for t in (0, 50, 100) for p in flat(res["_contours"][t])]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def gains(res):
    # 95th-pct curvature -> 40 units of comb; clamp at 130
    return 40.0 / res["scale"], 130.0


NONE = dict(snaps=[], minors=[], spikes=[], minor_spikes=[], crosses=[])


def subline(J, t):
    nc = len(crosscheck.counted(J.get("crosses", [])))
    return ("CNTR %d: %d snap%s (red ring) · %d spike%s (pink) · %d minor (orange) · %d cross (cyan) · %s"
            % (t, len(J["snaps"]), "" if len(J["snaps"]) == 1 else "s", len(J["spikes"]), "" if len(J["spikes"]) == 1 else "s",
               len(J["minors"]) + len(J["minor_spikes"]), nc, J["verdict"].upper()))


def render(res, out_path, mover_name):
    bb = glyph_bbox(res, 110)
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]
    PH = 900 if bw / bh < 1.6 else 760
    PW = max(560, min(2400, int((PH - 150) * bw / bh) + 120))
    kgain, Lmax = gains(res)
    flagged = {r["node"] for t in (50, 100) for r in res["_J"][t]["snaps"] + res["_J"][t]["minors"]}
    ims = []
    for t in (0, 50, 100):
        A = Panel(PW, PH, bb, margin=40)
        c = res["_contours"][t]
        J = res["_J"].get(t, NONE)
        name = "drawn (CNTR 0)" if t == 0 else "CNTR %d" % t
        ttl = ("%s · %s · %s" % (fontlabel(res), name, mover_name),
               ("curvature comb, one scale for all three (drawn 95th pct |k| = 1/%.0f u) · colour = touched by the move, grey = untouched"
                % (1 / res["scale"])) if t == 0 else subline(J, t))
        A.fill_outline(Outline(c), color=(40, 48, 34), edge=(120, 120, 120))
        if t > 0:
            from .partsheet import draw_poly
            for poly in Outline(res["_contours"][0]).polys:
                draw_poly(A, poly + [poly[0]], (150, 150, 150), 0.7, dash=6)
        comb(A, c, res["_touched"], res["scale"], kgain, Lmax)
        handles(A, c, flagged)
        if t > 0:
            spike_marks(A, c, J)
            cross_marks(A, J)
        node_marks(A, c, J)
        if t == 0 and flagged:
            for gi, n in enumerate([n for cc in c for n in cc["nodes"]]):
                if gi in flagged:
                    X, Y = A.pt((n[0], n[1])); R = 9 * SS
                    A.d.ellipse([X - R, Y - R, X + R, Y + R], outline=(150, 150, 150), width=SS)
        A.d.rectangle([0, 0, A.im.width, 46 * SS], fill=BG)
        A.title(*ttl)
        ims.append(A.out())
    sheet = Image.new("RGB", (PW * 3 + 20, PH), BG)
    for i, im in enumerate(ims):
        sheet.paste(im, (i * (PW + 10), 0))
    d = ImageDraw.Draw(sheet)
    x0, y0 = 16, PH - 26
    for i in range(200):
        d.line([(x0 + i, y0), (x0 + i, y0 + 8)], fill=kcol(i / 200 * 2.5 * res["scale"], res["scale"]))
    d.text((x0 + 208, y0 - 3), LEGEND, fill=(170, 170, 170), font=font(MENLO, 9).font_variant(size=11))
    sheet.save(out_path)


LEGEND = ("|k| 0 -> 2.5x drawn 95th pct   red ring = SNAP: G1 kink > %g deg, or G2 jump grew (>%gx, +%g) and is visible (bump >= %gu past the node's tangent, or %gu-arc radius <= %gu)"
          " · orange = same jump, not visible · pink = SPIKE: peak > %gx or new inflection, and %gu-arc radius <= %gu and %gx tighter · r = radius in units"
          % (KINK_DEG, MINOR_RATIO, MINOR_FLOOR, BUMP_U, WIN, VIS_R, SPIKE_RATIO, WIN, VIS_R, SPIKE_VIS))


def zoom(res, bb, out_path, mover_name, W=820, H=760):
    """drawn | CNTR 50 | CNTR 100 of one region, comb + every handle, to judge a flag by eye"""
    kgain, Lmax = gains(res)
    ims = []
    for t in (0, 50, 100):
        A = Panel(W, H, bb, margin=20)
        c = res["_contours"][t]; J = res["_J"].get(t, NONE)
        ttl = ("%s · %s · %s · zoom" % (fontlabel(res), "drawn" if t == 0 else "CNTR %d" % t, mover_name),
               "comb on the drawn scale · all handles shown · dashed = drawn outline" if t == 0 else subline(J, t))
        A.fill_outline(Outline(c), color=(40, 48, 34), edge=(170, 170, 170))
        if t:
            from .partsheet import draw_poly
            for poly in Outline(res["_contours"][0]).polys:
                draw_poly(A, poly + [poly[0]], (150, 150, 150), 0.7, dash=6)
        comb(A, c, res["_touched"], res["scale"], kgain * 0.6, Lmax)
        handles(A, c, {n for s in segments(c) for n in (s[0], s[1])})
        if t:
            spike_marks(A, c, J)
            cross_marks(A, J)
        node_marks(A, c, J, size=11)
        A.d.rectangle([0, 0, A.im.width, 46 * SS], fill=BG)
        A.title(*ttl)
        ims.append(A.out())
    sh = Image.new("RGB", (W * 3 + 20, H), BG)
    for i, im in enumerate(ims):
        sh.paste(im, (i * (W + 10), 0))
    sh.save(out_path)


def thumb(res, W=300, H=330):
    bb = glyph_bbox(res, 90)
    A = Panel(W, H, bb, margin=10)
    ns, nsp = len(res["snaps"]), len(res["spikes"])
    nx = len(crosscheck.counted(res.get("crosses", [])))
    col = CROSSC if res["verdict"] == "cross" else SNAPC if res["verdict"] == "snapped" else (MINORC if res["verdict"] == "minor" else (150, 210, 120))
    A.d.text((10 * SS, 8 * SS), fontlabel(res), fill=(235, 235, 235), font=font(CAL, 13))
    A.d.text((10 * SS, 28 * SS), "%s%d snap%s · %d spike%s · %d minor%s" % (
        ("%d cross · " % nx) if nx else "", ns, "" if ns == 1 else "s", nsp, "" if nsp == 1 else "s", len(res["minors"]) + len(res["minor_spikes"]),
        "  (worse at 50)" if res["at50"]["sev"] > res["sev"] + 0.5 else ""), fill=col, font=font(CAL, 12))
    c = res["_contours"][100]
    A.fill_outline(Outline(c), color=(40, 48, 34), edge=(110, 110, 110))
    kgain, Lmax = gains(res)
    comb(A, c, res["_touched"], res["scale"], kgain, Lmax, width=0.8, teeth=True)
    spike_marks(A, c, res, labels=False)
    cross_marks(A, res, labels=False)
    node_marks(A, c, res, labels=True, size=6)
    return A.out()


def index_sheet(results, master, out_path, mover_name):
    """letters worst first in a grid; a wide glyph (drawn wider than 2.5 x the median: a ligature, a logotype) gets its own
    full-width row at the end"""
    rs = worst_first(results)

    def bw(r):
        xs = [n[0] for c in r["_contours"][0] for n in c["nodes"]] or [0]
        return max(xs) - min(xs)
    med = sorted(bw(r) for r in rs)[len(rs) // 2] if rs else 0
    wide = [r for r in rs if med and bw(r) > 2.5 * med]
    rs = [r for r in rs if r not in wide]
    cols = 5; W, H = 300, 330; WH = 400
    rows = math.ceil(len(rs) / cols)
    SW = cols * (W + 8) + 8
    sheet = Image.new("RGB", (SW, rows * (H + 8) + 60 + len(wide) * (WH + 8)), BG)
    d = ImageDraw.Draw(sheet)
    allr = rs + wide
    tot = sum(len(r["snaps"]) for r in allr); tsp = sum(len(r["spikes"]) for r in allr)
    fam = next((r.get("family") for r in allr if r.get("family")), "")
    d.text((12, 12), ("%s %s · CNTR 100 curvature combs · %s · %d snaps, %d spikes · worst first" % (fam, master, mover_name, tot, tsp)).strip(),
           fill=(232, 184, 74), font=font(CAL, 16).font_variant(size=18))
    d.text((12, 36), "red ring = snap node, pink = spiking segment, orange = curvature jump too small to see, grey comb = untouched",
           fill=(160, 160, 160), font=font(CAL, 12).font_variant(size=13))
    for i, r in enumerate(rs):
        sheet.paste(thumb(r, W, H), (8 + (i % cols) * (W + 8), 60 + (i // cols) * (H + 8)))
    for j, r in enumerate(wide):
        sheet.paste(thumb(r, SW - 16, WH), (8, 60 + rows * (H + 8) + j * (WH + 8)))
    sheet.save(out_path)


# --- report -------------------------------------------------------------------------------------
def write_md(outdir):
    files = sorted(glob.glob(os.path.join(outdir, "results_*.json")), key=lambda f: (not f.endswith("results_move.json"), f))
    L = ["# Curvature (G2) check of the move step, CNTR 100", "",
         "Judged on touched segments only (a control point moved). A smooth node whose two handles now turn by more than %g deg "
         "(and %g deg more than drawn) is a **kink** (G1 break) and always a snap (1.5-4 deg: minor). Otherwise it is nominated when its curvature jump "
         "|kL - kR| grew > %gx drawn and by > %g x the glyph's drawn 95th-pct |k|; it is a **snap** when that is visible: the curve now "
         "crosses the node's own tangent by >= %g u (a bump: the extremum slid off its node), or the jump read over %g u of arc is a radius "
         "<= %g u. A segment is nominated when its peak |k| > %gx drawn or it gained an inflection; it is a **spike** when its tightest %g u-arc "
         "radius is <= %g u and %gx tighter than drawn. Nominated but not visible = minor. Snaps are listed `node (bump u, radius u)`, spikes "
         "`a-b (drawn radius -> 100 radius)`." % (KINK_DEG, KINK_DEG, MINOR_RATIO, MINOR_FLOOR, BUMP_U, WIN, VIS_R, SPIKE_RATIO, WIN, VIS_R, SPIKE_VIS), "",
         "Renders: `<glyph>_curv[_<mover>].png` (drawn | 50 | 100), `curv_index_<Master>[_<mover>].png` (worst first).", ""]
    allR = {}
    for f in files:
        R = json.load(open(f)); allR[R["mover"]] = {r["key"]: r for r in R["results"]}
    if len(allR) > 1:
        L += ["## movers compared", "", "| mover | cross | snapped | minor | clean | FAIL | snaps | spikes | total severity |", "|---|---|---|---|---|---|---|---|---|"]
        for mv, D in allR.items():
            rs = list(D.values()); v = lambda k: sum(1 for r in rs if r["verdict"] == k)
            L.append("| `%s` | %d | %d | %d | %d | %d | %d | %d | %.1f |" % (mv, v("cross"), v("snapped"), v("minor"), v("clean"), v("FAIL"),
                     sum(len(r["snaps"]) for r in rs), sum(len(r["spikes"]) for r in rs), sum(r.get("sev", 0) for r in rs)))
        L.append("")
    for mv, D in allR.items():
        rs_all = list(D.values())
        cnt = {}
        for r in rs_all:
            cnt[r["verdict"]] = cnt.get(r["verdict"], 0) + 1
        L += ["## mover `%s`" % mv, "",
              "%d layers: %s · %d snaps, %d spikes" % (len(rs_all), ", ".join("%d %s" % (v, k) for k, v in sorted(cnt.items())),
                                                       sum(len(r["snaps"]) for r in rs_all), sum(len(r["spikes"]) for r in rs_all)), ""]
        good = [r for r in rs_all if not r.get("error")]
        L += ["Worst ten: " + ", ".join("%s %s (%s)" % (r["master"], r["glyph"], "; ".join(crosscheck.label(c) for c in crosscheck.counted(r.get("crosses", []))) or
                                                     ", ".join(str(x["node"]) for x in r["snaps"]) or
                                                     "spikes " + ", ".join("%d-%d" % tuple(x["seg"]) for x in r["spikes"]))
                                      for r in worst_first(good)[:10]), ""]
        order = ["Regular", "Black", "Italic", "Black Italic"]
        for master in sorted({r["master"] for r in rs_all}, key=lambda m: (order.index(m) if m in order else 9, m)):
            rs = [r for r in rs_all if r["master"] == master]
            if not rs: continue
            L += ["### %s" % master, "", "| glyph | touched / all segments | snaps | spikes | minor | cross | at CNTR 50 | verdict |", "|---|---|---|---|---|---|---|---|"]
            for r in sorted(rs, key=lambda r: r["glyph"]):
                if r.get("error"):
                    L.append("| %s | - | - | - | - | - | - | FAIL: %s |" % (r["glyph"], r["error"][:60])); continue
                sn = ", ".join("%d (%s%.1f, r%.0f)" % (x["node"], "kink %.1f deg, " % x["kink"] if x.get("kink") else "", max(0, x["bump"]), x["R1"]) for x in r["snaps"]) or "-"
                sp = ", ".join("%d-%d (r%.0f->%.1f)" % (x["seg"][0], x["seg"][1], x["r0"], x["r1"]) for x in r["spikes"]) or "-"
                mi = ", ".join([str(x["node"]) for x in r["minors"]] + ["%d-%d" % tuple(x["seg"]) for x in r["minor_spikes"]]) or "-"
                a5 = r["at50"]
                extra = sorted({x["node"] for x in a5["snaps"]} - {x["node"] for x in r["snaps"]})
                extras = sorted({tuple(x["seg"]) for x in a5["spikes"]} - {tuple(x["seg"]) for x in r["spikes"]})
                at50 = a5["verdict"] + ("; worse: " + ", ".join([str(n) for n in extra] + ["%d-%d" % e for e in extras]) if extra or extras else "")
                cx = "; ".join(crosscheck.label(c) for c in crosscheck.counted(r.get("crosses", []))) or "-"
                L.append("| %s | %d / %d | %s | %s | %s | %s | %s | %s |" % (r["glyph"], r["touched"], r["ncurves_total"], sn, sp, mi, cx, at50, r["verdict"]))
            L.append("")
    open(os.path.join(outdir, "CURV.md"), "w").write("\n".join(L) + "\n")


MOVERS = {"move": "wmparts.mover", "groupmove": "wmparts.groupmove", "mover": "wmparts.mover"}


def mover_class(spec):
    """"groupmove:GroupMover" / "move:Mover" (the package's), or any importable "module:Class" """
    modname, clsname = spec.split(":")
    return getattr(importlib.import_module(MOVERS.get(modname, modname)), clsname)


def run(G, keys, outdir, spec):
    modname, clsname = spec.split(":")
    Cls = mover_class(spec)
    suffix = "" if spec == "move:Mover" else "_" + modname
    results = []
    for key in keys:
        g = G[key]
        try:
            M = Cls(g)
            res = evaluate(g, M)
            res["key"] = key
            res["ncurves_total"] = len(segments(g["contours"]))
            render(res, os.path.join(outdir, fname(key) + "_curv%s.png" % suffix), modname)
            print("%-28s %-8s sev %5.1f snaps %s spikes %s minor %s cross %s" % (key, res["verdict"], res["sev"], [(x["node"], x["bump"], x["R1"]) for x in res["snaps"]],
                  [(tuple(x["seg"]), x["r0"], x["r1"]) for x in res["spikes"]], [x["node"] for x in res["minors"]] + [tuple(x["seg"]) for x in res["minor_spikes"]],
                  [crosscheck.label(c) for c in crosscheck.counted(res["crosses"])]), flush=True)
        except Exception as e:
            traceback.print_exc()
            res = dict(key=key, glyph=g["glyph"], master=g["master"], error=repr(e), verdict="FAIL", snaps=[], spikes=[], minors=[], minor_spikes=[], crosses=[], sev=0)
        results.append(res)
    good = [r for r in results if not r.get("error")]
    for master in sorted({r["master"] for r in good}):
        index_sheet([r for r in good if r["master"] == master], master,
                    os.path.join(outdir, "curv_index_%s%s.png" % (master.replace(" ", ""), suffix)), modname)
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]
    json.dump({"mover": spec, "results": clean}, open(os.path.join(outdir, "results_%s.json" % modname), "w"), indent=1)


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="curvcomb")
    ap.add_argument("src", nargs="?"); ap.add_argument("outdir")
    ap.add_argument("--mover", action="append"); ap.add_argument("--keys", default="all")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--skip", default="", help="glyph names left out of --keys all (comma list)")
    ap.add_argument("--zoom", action="append", help="key:x0,y0,x1,y1 (writes <glyph>_curvzoom_x0-y0.png)")
    a = ap.parse_args(argv)
    if a.md:
        write_md(a.outdir if a.src is None else a.src); return
    from ..font import load_set
    G = load_set(a.src)          # adds g["_mi"] from <set>.masters.json
    os.makedirs(a.outdir, exist_ok=True)
    keys = sorted(G) if a.keys == "all" else a.keys.split(",")
    skip = {x for x in a.skip.split(",") if x}
    keys = [k for k in keys if G[k]["glyph"] not in skip or a.keys != "all"]
    keys = [k for k in keys if any(len(c["nodes"]) for c in G[k]["contours"])]
    if a.zoom:
        for spec in (a.mover or ["move:Mover"]):
            modname, clsname = spec.split(":")
            Cls = mover_class(spec)
            for z in a.zoom:
                key, bbs = z.split(":"); bb = tuple(float(v) for v in bbs.split(","))
                res = evaluate(G[key], Cls(G[key])); res["key"] = key
                zoom(res, bb, os.path.join(a.outdir, "%s_curvzoom_%d-%d%s.png" % (fname(key), bb[0], bb[1], "" if spec == "move:Mover" else "_" + modname)), modname)
        return
    for spec in (a.mover or ["move:Mover"]):
        run(G, keys, a.outdir, spec)
    write_md(a.outdir)


if __name__ == "__main__":
    _main()
