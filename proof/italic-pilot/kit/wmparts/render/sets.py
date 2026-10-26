"""Whole-set sheets (fontrun.py's, 2026-10-23): per master a parts grid, every letter at CNTR 0 / 50 / 100, the serifs
zoomed, and a pairing summary. G is a Font / {key: layer} with master descriptions attached (wmparts.load_glyphs).

  grids(G, outdir)            grid_<Tag>.png
  summary(G, outdir)          summary.json (strokes, slab faces, flags, balls, unpaired / buried walls, move time)
  overview(G, tag, out)       every letter at CNTR 0 · 50 · 100
  serifs_sheet(G, tag, out)   feet and heads, CNTR 0 | 100
Letters are laid out in ORDER (Mark's 13 test letters) first, then every other glyph by name."""
import os, json, math, time, traceback
from PIL import Image
from . import grid, groupsheet
from ..font import load_set
from ..groupmove import GroupMover
from ..parts import Parts
from ..font import fname
from .draw import fontlabel, Panel, BG, SS, font, CAL
from .overview import strip
from .partsheet import draw_poly
from ..rungs import Outline

ROWS = [["f", "j", "H", "n", "a", "E", "T"], ["r", "v", "e", "y", "k", "x"]]
ORDER = [gn for r in ROWS for gn in r]


def glyphs_of(G, tag):
    """the glyph names of one master, ORDER first, then the rest by name"""
    names = {G[k]["glyph"] for k in G if k.split("_")[0] == tag and any(len(c["nodes"]) for c in G[k]["contours"])}
    return [n for n in ORDER if n in names] + sorted(names - set(ORDER))


def rows_of(names, cols):
    return [names[i:i + cols] for i in range(0, len(names), cols)]


def tags_of(G):
    out = []
    for k in sorted(G):
        t = k.split("_")[0]
        if t not in out:
            out.append(t)
    return out


def grids(G, sd):
    CW, CH = 440, 480
    for tag in tags_of(G):
        names = glyphs_of(G, tag)
        rows = ROWS if set(names) <= set(ORDER) else rows_of(names, 7)
        sheet = Image.new("RGB", (CW * 7 + 20, CH * len(rows) + 20), BG); n = 0
        for ri, r in enumerate(rows):
            for ci, gn in enumerate(r):
                key = "%s_%s" % (tag, gn)
                if key not in G: continue
                try:
                    im, P = grid.cell(G[key], CW, CH); n += 1
                except Exception:
                    im = Image.new("RGB", (CW, CH), (40, 10, 10)); print("FAIL grid", key, traceback.format_exc()[-400:])
                sheet.paste(im, (ci * CW + 10, ri * CH + 10))
        from .draw import header
        g0 = next(G[k] for k in sorted(G) if k.startswith(tag + "_"))
        header(sheet, "%s %s · parts grid" % (g0.get("family", ""), g0["master"])).save(os.path.join(sd, "grid_%s.png" % tag)); print("grid", tag, n)


def summary(G, sd):
    rows = []
    for key in sorted(G):
        g = G[key]; mi = g["_mi"]
        P = Parts(g["contours"], slant=mi["ia"], stem=mi["stem"]); ol = P.ol
        t0 = time.time()
        try:
            GM = GroupMover(g); dt = time.time() - t0; ok = True; ng = len(GM.groups)
        except Exception as e:
            dt = time.time() - t0; ok = False; ng = None; print("FAIL move", key, traceback.format_exc()[-500:])
        def wall_nodes(wi):
            return sorted({ol.segs[k].gi for k in ol.walls[wi]} | {ol.segs[k].gj for k in ol.walls[wi]})
        rows.append(dict(key=key, strokes=len(P.strokes), slab_serif_faces=sum(1 for s in ol.serifs if s["kind"] == "slab"),
                         other_flags=sum(1 for s in ol.serifs if s["kind"] != "slab"), balls=[b["nodes"] for b in ol.balls],
                         unpaired=[dict(wall=w, nodes=wall_nodes(w)) for w in P.unpaired],
                         buried=[wall_nodes(w) for w, k in P.kind.items() if k == "buried"],
                         move_ok=ok, groups=ng, move_s=round(dt, 3)))
        print(key, {k: v for k, v in rows[-1].items() if k != "key"})
    json.dump(rows, open(os.path.join(sd, "summary.json"), "w"), indent=1)
    return rows


def overview(G, tag, out):
    lc = glyphs_of(G, tag)
    CW, CH = 280, 310; SW = CW * 3 + 8; cols = 4
    nrow = (len(lc) + cols - 1) // cols
    sheet = Image.new("RGB", (SW * cols + 50, (CH + 10) * nrow + 20), BG)
    for i, gn in enumerate(lc):
        key = "%s_%s" % (tag, gn)
        try:
            M = GroupMover(G[key]); im = strip(G[key], M, CW, CH)
        except Exception:
            print(traceback.format_exc()[-600:]); im = strip(G[key], None, CW, CH)
        sheet.paste(im, (10 + (i % cols) * (SW + 10), 10 + (i // cols) * (CH + 10)))
    from .draw import header
    g0 = G["%s_%s" % (tag, lc[0])]
    header(sheet, "%s %s · every letter at CNTR 0 · 50 · 100" % (g0.get("family", ""), g0["master"]), "GroupMover round 8 · filled = moved · dashed = drawn").save(out); print("wrote", out)


def serifs_sheet(G, tag, out, glyphs=("H", "n", "T", "E", "f"), W=420, H=360):
    """the feet / heads zoomed: CNTR 0 | CNTR 100 per glyph, drawn outline dashed under 100"""
    panels = []
    for gn in glyphs:
        key = "%s_%s" % (tag, gn)
        if key not in G: continue
        g = G[key]; GM = GroupMover(g); ol = GM.ol
        ys = [n[1] for c in g["contours"] for n in c["nodes"]]; xs = [n[0] for c in g["contours"] for n in c["nodes"]]
        x0, x1 = min(xs) - 20, max(xs) + 20
        zones = [("foot", (x0, -40, x1, 170))] if gn != "T" else [("foot", ((x0 + x1) / 2 - 160, -40, (x0 + x1) / 2 + 160, 170))]
        top = max(ys)
        zones.append(("head", (x0, top - 230, x1, top + 30)))
        for zname, bb in zones:
            row = []
            for t in (0.0, 1.0):
                A = Panel(W, H, bb, margin=14)
                A.title("%s %s · CNTR %d" % (fontlabel(g), zname, int(t * 100)), "red = held slab serif (end face, face, bracket) · A = %.1f" % GM.A if t == 0 else "dashed = drawn")
                olt = Outline(GM.contours_at(t))
                A.fill_outline(olt, color=(60, 70, 50) if t == 0 else (78, 88, 64), edge=(170, 170, 170))
                if t > 0:
                    for poly in ol.polys:
                        draw_poly(A, poly + [poly[0]], (230, 230, 230), 0.9, dash=5)
                for k in ol.slab_segs:
                    sg = olt.segs[k]
                    draw_poly(A, sg.poly, (255, 80, 70), 1.8)
                A.nodes(olt, labels=True)
                row.append(A.out())
            panels.append(row)
    sheet = Image.new("RGB", (W * 2 * 2 + 30, (H + 8) * ((len(panels) + 1) // 2) + 10), BG)
    for i, row in enumerate(panels):
        x = 10 + (i % 2) * (2 * W + 10); y = 5 + (i // 2) * (H + 8)
        sheet.paste(row[0], (x, y)); sheet.paste(row[1], (x + W, y))
    g0 = G["%s_%s" % (tag, glyphs[0])] if "%s_%s" % (tag, glyphs[0]) in G else next(iter(G.values()))
    from .draw import header
    header(sheet, "%s %s · serifs, CNTR 0 | 100" % (g0.get("family", ""), g0["master"])).save(out); print("wrote", out)
