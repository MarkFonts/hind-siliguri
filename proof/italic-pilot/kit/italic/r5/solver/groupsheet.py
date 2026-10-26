"""Sheets for GroupMover: the selections (groups), Mark's nested Illustrator look, x k n 0/100 vs the old
field, and a CNTR sweep of the Italic n.

usage: groupsheet.py SRC.json OUTDIR
"""
import sys, os, json, math
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from groupmove import GroupMover
from move import Mover
from movesheet import moved_side
from sheet import Panel, bbox_of, BG, SS, font, CAL, MENLO
from partsheet import COLS, draw_poly, draw_flag
from readings import fname
from rungs import Outline

GCOLS = [(255, 150, 40), (60, 220, 230), (240, 90, 220), (250, 230, 70), (140, 240, 90), (255, 110, 110)]
RED, GREEN, BLUE = (240, 80, 70), (90, 200, 90), (80, 130, 255)
BLUES = [(80, 130, 255), (150, 110, 255), (70, 190, 255)]


# ---- helpers -----------------------------------------------------------------------------------------------
def mapped_side(S, olt):
    """the side's dense points carried onto the moved outline (same segment, same parameter);
    hidden continuation points are re-interpolated between their moved visible ends"""
    pts = [None] * len(S.pts)
    for i, (src, p) in enumerate(zip(S.src, S.pts)):
        if src[0] != "hidden":
            pts[i] = olt.segs[src[0]].point(src[1])
    # fill hidden runs linearly between known neighbours, keeping the drawn offsets' shape
    i = 0
    n = len(pts)
    while i < n:
        if pts[i] is not None:
            i += 1; continue
        j = i
        while j < n and pts[j] is None:
            j += 1
        a = i - 1; b = j
        for k in range(i, j):
            if a >= 0 and b < n:
                u = (k - a) / (b - a)
                da = (pts[a][0] - S.pts[a][0], pts[a][1] - S.pts[a][1]); db = (pts[b][0] - S.pts[b][0], pts[b][1] - S.pts[b][1])
                pts[k] = (S.pts[k][0] + da[0] + (db[0] - da[0]) * u, S.pts[k][1] + da[1] + (db[1] - da[1]) * u)
            elif a >= 0:
                da = (pts[a][0] - S.pts[a][0], pts[a][1] - S.pts[a][1]); pts[k] = (S.pts[k][0] + da[0], S.pts[k][1] + da[1])
            elif b < n:
                db = (pts[b][0] - S.pts[b][0], pts[b][1] - S.pts[b][1]); pts[k] = (S.pts[k][0] + db[0], S.pts[k][1] + db[1])
            else:
                pts[k] = S.pts[k]
        i = j
    return pts


def runs_of(S, pts):
    """split into (hidden, polyline) runs"""
    out = []; cur = []; ch = None
    for p, h in zip(pts, S.hidden):
        if ch is None or h == ch:
            cur.append(p)
        else:
            out.append((ch, cur)); cur = [cur[-1], p]
        ch = h
    if cur:
        out.append((ch, cur))
    return out


def at_arc(S, pts, s):
    i = int(np.searchsorted(S.al, s, side="right") - 1); i = min(max(i, 0), len(S.al) - 2)
    u = (s - S.al[i]) / max(1e-9, S.al[i + 1] - S.al[i]); u = min(max(u, 0.0), 1.0)
    return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u)


def blend_pts(st, pa, pb, u):
    SA, SB = st["A"], st["B"]
    rs = [(r[0], r[1]) for r in st["rungs"] if r[0] is not None and r[1] is not None and r[2] != "cross"]
    out = []
    for (a0, b0), (a1, b1) in zip(rs, rs[1:]):
        for k in range(25):
            f = k / 24
            qa = at_arc(SA, pa, a0 + (a1 - a0) * f); qb = at_arc(SB, pb, b0 + (b1 - b0) * f)
            out.append((qa[0] + (qb[0] - qa[0]) * u, qa[1] + (qb[1] - qa[1]) * u))
    return out


def grows(GM, si):
    return GM.stroke_max.get(si, 0.0) > 0.5


def mix(c, k, base=BG):
    return tuple(int(base[i] + (c[i] - base[i]) * k) for i in range(3))


def arrow(A, p, v, col, w=1.6, head=6.0):
    q = (p[0] + v[0], p[1] + v[1])
    A.line(p, q, col, w)
    L = math.hypot(*v)
    if L < 1e-6:
        return
    ux, uy = v[0] / L, v[1] / L
    hs = head / (A.s / SS)          # head size in font units for ~head px
    for ang in (0.5, -0.5):
        ca, sa = math.cos(ang), math.sin(ang)
        bx = -(ux * ca - uy * sa) * hs; by = -(ux * sa + uy * ca) * hs
        A.line(q, (q[0] + bx, q[1] + by), col, w)


def square(A, p, col, r=5.0, fill=None, w=1.4):
    X, Y = A.pt(p); r *= SS
    A.d.rectangle([X - r, Y - r, X + r, Y + r], outline=col, width=max(1, int(w * SS)), fill=fill)


def diamond(A, p, col, r=6.0, w=1.4):
    X, Y = A.pt(p); r *= SS
    A.d.polygon([(X, Y - r), (X + r, Y), (X, Y + r), (X - r, Y)], outline=col, width=max(1, int(w * SS)))


def seg_poly(GM, ol, gi, gj):
    for sg in ol.segs:
        if sg.gi == gi and sg.gj == gj:
            return sg.poly
    return []


def group_path(GM, g):
    """the member nodes in contour order, and the segments joining consecutive members"""
    C = GM.contours[g["ci"]]; ons = C["ons"]; K = len(ons)
    mem = set(g["levels"])
    pos = sorted(ons.index(n) for n in mem)
    segs = []
    for p in pos:
        q = (p + 1) % K
        if ons[q] in mem:
            segs.append((ons[p], ons[q]))
    return segs


# ---- A. groups -----------------------------------------------------------------------------------------------
def groups_sheet(G, key, out, PW=900, PH=980):
    g = G[key]; GM = GroupMover(g); ol = GM.ol
    R = GM.report()
    bb = bbox_of(ol, pad=60)
    A = Panel(PW, PH, bb, margin=40)
    A.title("/%s %s · the selections (groups)" % (g["glyph"], g["master"]),
            "colour run = one group, ONE vector (arrow, true length) · ○ graded (×⅔ ×⅓) · □ anchor · ◇ slid / junction / terminal · rules R1–R16 in groupmove.py · A = %.1f" % GM.A)
    A.fill_outline(ol, color=(34, 40, 28), edge=(110, 110, 110))
    for gi_, grp in enumerate(GM.groups):
        col = GCOLS[gi_ % len(GCOLS)]
        for a, b in group_path(GM, grp):
            draw_poly(A, seg_poly(GM, ol, a, b), col, 5.0)
        for nd, lv in grp["levels"].items():
            p = GM.xy[nd]
            X, Y = A.pt(p); r = (5 if lv >= 0.99 else 3.5) * SS
            A.d.ellipse([X - r, Y - r, X + r, Y + r], fill=col if lv >= 0.99 else None, outline=col, width=2 * SS)
            if lv < 0.99:
                A.text(p, "×%s" % ("⅔" if lv > 0.5 else "⅓"), col, size=10, dx=6, dy=4)
        for T in grp.get("terminal") or []:
            for nd in T["nodes"]:
                diamond(A, GM.xy[nd], col, 8.0, 1.8)
            arrow(A, GM.xy[T["nodes"][0]], T["vec"], col, 1.8, 7)
        cx = np.mean([GM.xy[n][0] for n in grp["levels"]]); cy = np.mean([GM.xy[n][1] for n in grp["levels"]])
        v = (grp["dir"][0] * grp["mag"], grp["dir"][1] * grp["mag"])
        arrow(A, (cx, cy), v, col, 2.4, 9)
        A.text((cx + v[0], cy + v[1]), "g%d %.1f u · %s" % (grp["id"], grp["mag"], grp["dir_name"]), col, size=10, dx=6, dy=-6)
        for nd in grp["anchors"]:
            if nd in GM.xy:
                square(A, GM.xy[nd], (255, 255, 255), 6.5, w=1.6)
        for nd in grp["slides"]:
            diamond(A, GM.xy[nd], col, 8.0, 1.8)
    for j in GM.slid_junctions:
        for nd in (j["node"], j["partner"]):
            if nd is None:
                continue
            diamond(A, GM.xy[nd], (255, 255, 255), 8.0, 1.6)
            arrow(A, GM.xy[nd], GM.vec.get(nd, (0.0, 0.0)), (255, 255, 255), 1.6, 7)
    for c in GM.cut_moves:
        p = GM.xy[c["node"]]
        arrow(A, p, c["vec"], (255, 90, 90), 1.6, 7)
        X, Y = A.pt(p); r = 4.5 * SS
        A.d.polygon([(X, Y - r), (X + r, Y + r), (X - r, Y + r)], outline=(255, 90, 90), width=SS)
    for nd in GM.held:
        square(A, GM.xy[nd], (255, 80, 70), 4.0, fill=(255, 80, 70))
    A.nodes(ol)
    # the list, as text
    f = font(MENLO, 9.5)
    lines = []
    for gi_, grp in enumerate(R["groups"]):
        gr = ", ".join("%d×%s" % (n, "⅔" if grp["levels"][n] > 0.5 else "⅓") for n in grp["graded"])
        lines.append((GCOLS[gi_ % len(GCOLS)], ("[" + " ".join(grp["rules"]) + "]  ") + "g%d  core %s  +carried %s  +graded [%s]  +slides %s  → (%.1f, %.1f) |%.1f| %s %.0f°  anchors %s" % (
            grp["id"], grp["core"], grp["ext"], gr, grp["slides"], grp["vector"][0], grp["vector"][1], grp["mag"], grp["snap"], grp["snap_deg"], grp["anchors"])))
    for t in R["terminals"]:
        lines.append((GCOLS[t["group"] % len(GCOLS)], "[R11] terminal %s → (%.1f, %.1f) slides along its end face with g%d" % (t["nodes"], t["vector"][0], t["vector"][1], t["group"])))
    for j in R["junctions"]:
        lines.append(((235, 235, 235), "[R10] junction %d%s on %s → (%.1f, %.1f) (share %.1f, slides along the host wall)" % (
            j["node"], "+%d" % j["partner"] if j["partner"] is not None else "", j["kind"], j["vector"][0], j["vector"][1], j["share"])))
    for c in R["cuts"]:
        lines.append(((255, 120, 120), "[R12] cut face %d → (%.1f, %.1f) (along its face)" % (c["node"], c["vector"][0], c["vector"][1])))
    lines.append(((170, 170, 170), "held (flags): %s · [R14] connecting curves turned+scaled as one piece: %s" % (
        R["held"], ", ".join("%d-%d ×%.2f %+.0f°" % c for c in R["connecting"]) or "-")))
    big = [r_ for r_ in R["realigned"] if r_[2] >= 1.0]
    lines.append(((170, 170, 170), "[R15] smooth nodes re-aligned (≥1°): %s" % (", ".join("%d %.0f° %s" % (r_[0], r_[2], r_[3].split()[0]) for r_ in big) or "-")))
    y = (PH - 18 - 13 * len(lines)) * SS
    for col, s in lines:
        A.d.text((16 * SS, y), s, fill=col, font=f); y += 13 * SS
    # right: CNTR 100
    B = Panel(PW, PH, bb, margin=40)
    B.title("/%s %s · CNTR 100 (GroupMover)" % (g["glyph"], g["master"]), "filled = moved · dashed = drawn · node numbers on the moved outline")
    ol1 = Outline(GM.contours_at(1.0))
    B.fill_outline(ol1, color=(45, 58, 32), edge=(170, 170, 170))
    for poly in ol.polys:
        draw_poly(B, poly + [poly[0]], (150, 150, 150), 0.8, dash=6)
    for gi_, grp in enumerate(GM.groups):
        col = GCOLS[gi_ % len(GCOLS)]
        for a, b in group_path(GM, grp):
            draw_poly(B, seg_poly(GM, ol1, a, b), col, 2.4)
    B.nodes(ol1)
    sheet = Image.new("RGB", (PW * 2 + 10, PH), BG)
    sheet.paste(A.out(), (0, 0)); sheet.paste(B.out(), (PW + 10, 0)); sheet.save(out)
    return GM


# ---- B. nested -----------------------------------------------------------------------------------------------
def nested_sheet(G, key, out, PW=1100, PH=1100, ts=(0.0, 0.25, 0.5, 0.75, 1.0), GM=None):
    g = G[key]; GM = GM or GroupMover(g); ol = GM.ol; P = GM.P
    bb = bbox_of(ol, pad=50)
    A = Panel(PW, PH, bb, margin=40)
    A.title("/%s %s · sides of each part at CNTR 0 · 25 · 50 · 75 · 100, nested (dim → full)" % (g["glyph"], g["master"]),
            "red = parts that do not grow (stems, diagonals) · blue = growing parts (arch, bowl, hook, crescents) · green = flags · dashed = drawn outline")
    for poly in ol.polys:
        draw_poly(A, poly + [poly[0]], (95, 95, 95), 0.8, dash=6)
    for t in ts:
        k = 0.28 + 0.72 * t
        olt = Outline(GM.contours_at(t))
        bi = 0
        for si, (st, rows) in enumerate(GM.M.stroke_rows):
            col = (BLUES[bi % len(BLUES)] if grows(GM, si) else RED)
            if grows(GM, si): bi += 1
            for S in (st["A"], st["B"]):
                pts = mapped_side(S, olt)
                for hidden, run in runs_of(S, pts):
                    if hidden:
                        if t == 1.0:
                            draw_poly(A, run, mix(col, 0.45), 0.8, dash=5)
                    else:
                        draw_poly(A, run, mix(col, k), 1.25 if t < 1 else 1.8)
        for fl in P.flags:
            ka = GM.ol.segs.index(fl["a"]); kb = GM.ol.segs.index(fl["b"])
            a, b = olt.segs[ka], olt.segs[kb]
            tipA, tipB, farA, farB = a.pts[1], b.pts[0], a.pts[0], b.pts[1]
            c = mix(GREEN, k)
            A.line(farA, tipA, c, 1.2); A.line(tipB, farB, c, 1.2); A.line(tipA, tipB, c, 1.2)
            if t == 1.0:
                for kk in range(1, 5):
                    u = kk / 5
                    p0 = (tipA[0] + (tipB[0] - tipA[0]) * u, tipA[1] + (tipB[1] - tipA[1]) * u)
                    p1 = (farA[0] + (farB[0] - farA[0]) * u, farA[1] + (farB[1] - farA[1]) * u)
                    A.line(p0, p1, mix(GREEN, 0.6), 0.7)
    A.out().save(out)
    return GM


# ---- C. x k n --------------------------------------------------------------------------------------------------
def side_panel(A, P, strokes_rows, side_pts_fn, olt, fillcol=(45, 58, 32)):
    A.fill_outline(olt, color=fillcol, edge=(120, 120, 120))
    for i, (st, rows) in enumerate(strokes_rows):
        col = COLS[i % len(COLS)]
        pa, pb = side_pts_fn(st)
        draw_poly(A, pa, col, 1.5); draw_poly(A, pb, col, 1.5)
        for u, w in ((0.25, 0.8), (0.5, 1.5), (0.75, 0.8)):
            draw_poly(A, blend_pts(st, pa, pb, u), col if u != 0.5 else (255, 255, 255), w)
    for fl in P.flags:
        draw_flag(A, P, fl)


def xkn_sheet(G, master, out, glyphs=("x", "k", "n"), CW=640, CH=620):
    tag = "HS" + master.replace(" ", "")
    rows_im = []
    FH = int(CH * 0.62)
    sheet = Image.new("RGB", (CW * len(glyphs) + 20, CH * 2 + FH + 30), BG)
    for ci, gn in enumerate(glyphs):
        g = G["%s_%s" % (tag, gn)]
        GM = GroupMover(g)
        xs = [n[0] for c in g["contours"] for n in c["nodes"]]
        bb = (min(xs) - 40, -60, max(xs) + 40, 560)
        for ri, t in enumerate((0.0, 1.0)):
            A = Panel(CW, CH, bb, margin=20)
            A.title("/%s %s · CNTR %d · groups" % (gn, master, int(t * 100)))
            olt = Outline(GM.contours_at(t))
            if t > 0:
                for poly in GM.ol.polys:
                    draw_poly(A, poly + [poly[0]], (90, 90, 90), 0.7, dash=6)
            A.line((bb[0], 0), (bb[2], 0), (60, 160, 180), 0.8)
            side_panel(A, GM.P, GM.M.stroke_rows, lambda st: (mapped_side(st["A"], olt), mapped_side(st["B"], olt)), olt)
            if t > 0:
                for poly in GM.ol.polys:
                    draw_poly(A, poly + [poly[0]], (150, 150, 150), 0.7, dash=6)
            sheet.paste(A.out(), (10 + ci * CW, 10 + ri * CH))
        # the old field, small
        M = GM.M
        B = Panel(CW, FH, bb, margin=14)
        B.title("/%s %s · CNTR 100 · field (old)" % (gn, master))
        ol2 = Outline(M.contours_at(1.0))
        sd = {id(st): (SA, saL, dAL, SB, sbL, dBL) for SA, saL, dAL, SB, sbL, dBL, st in M.side_disp}
        def field_sides(st):
            SA, saL, dAL, SB, sbL, dBL = sd[id(st)]
            return moved_side(SA, saL, dAL, 1.0, M), moved_side(SB, sbL, dBL, 1.0, M)
        side_panel(B, M.P, [(st, r) for st, r in M.stroke_rows if id(st) in sd], field_sides, ol2, fillcol=(52, 40, 30))
        for poly in M.ol.polys:
            draw_poly(B, poly + [poly[0]], (150, 150, 150), 0.7, dash=6)
        sheet.paste(B.out(), (10 + ci * CW, 20 + 2 * CH))
    sheet.save(out)


# ---- D. sweep -----------------------------------------------------------------------------------------------------
def sweep_sheet(G, key, out, ts=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0), W=520, H=640):
    g = G[key]; GM = GroupMover(g)
    bb = bbox_of(GM.ol, pad=40)
    sheet = Image.new("RGB", (W * len(ts) + 10, H), BG)
    for i, t in enumerate(ts):
        A = Panel(W, H, bb, margin=18)
        A.title("/%s %s · CNTR %d" % (g["glyph"], g["master"], int(round(t * 100))))
        olt = Outline(GM.contours_at(t))
        A.fill_outline(olt, color=(150, 160, 140), edge=(230, 230, 230))
        for poly in GM.ol.polys:
            draw_poly(A, poly + [poly[0]], (90, 90, 160), 0.7, dash=6)
        for gi, (x, y, ty, sm) in olt.node_xy.items():
            if ty != "o":
                A.dot((x, y), (255, 150, 40), 1.8)
        sheet.paste(A.out(), (5 + i * W, 0))
    sheet.save(out)


# ---- overview (overview.py's layout, GroupMover) ------------------------------------------------------------------
def overview_group(G, master, out):
    from overview import strip, ROWS
    import traceback
    tag = "HS" + master.replace(" ", "")
    CW, CH = 280, 310
    SW = CW * 3 + 8
    sheet = Image.new("RGB", (SW * 4 + 50, (CH + 10) * 4 + 20), BG)
    log = []
    for ri, row in enumerate(ROWS):
        for ci, gn in enumerate(row):
            key = "%s_%s" % (tag, gn)
            if key not in G:
                continue
            try:
                M = GroupMover(G[key]); im = strip(G[key], M, CW, CH); log.append((key, "ok", len(M.groups)))
            except Exception as e:
                im = strip(G[key], None, CW, CH); log.append((key, "FAIL", repr(e)[:80])); print(traceback.format_exc()[-600:])
            sheet.paste(im, (10 + ci * (SW + 10), 10 + ri * (CH + 10)))
    sheet.save(out)
    return log


def terminal_zooms(G, out, specs, W=520, H=560):
    """6B proof: each r's terminal at CNTR 0 and 100, nodes numbered"""
    ims = []
    for key, bb in specs:
        GM = GroupMover(G[key])
        pair = Image.new("RGB", (W * 2 + 6, H), BG)
        for i, t in enumerate((0.0, 1.0)):
            A = Panel(W, H, bb, margin=12)
            A.title("/%s %s · CNTR %d" % (G[key]["glyph"], G[key]["master"], int(t * 100)), "terminal: " + (", ".join(
                "%s → (%.0f, %.0f)" % (T["nodes"], T["vec"][0], T["vec"][1]) for T in GM.terminals) or "none (flag / no cut face)"))
            olt = Outline(GM.contours_at(t))
            A.fill_outline(olt, color=(45, 58, 32), edge=(200, 200, 200))
            if t > 0:
                for poly in GM.ol.polys:
                    draw_poly(A, poly + [poly[0]], (150, 150, 150), 0.8, dash=6)
            A.nodes(olt)
            pair.paste(A.out(), (i * (W + 6), 0))
        ims.append(pair)
    sh = Image.new("RGB", (ims[0].width * 2 + 10, ims[0].height * ((len(ims) + 1) // 2) + 10), BG)
    for k, im in enumerate(ims):
        sh.paste(im, ((k % 2) * (im.width + 10), (k // 2) * (im.height + 10)))
    sh.save(out)


def all_keys(G):
    return [k for k in sorted(G) if "H_a_r_v_e_y" not in k]


if __name__ == "__main__" and len(sys.argv) > 3 and sys.argv[3] == "set":
    # the whole set (GRILL 12C): overviews, approval sheets, sweeps, r terminals
    G = json.load(open(sys.argv[1])); outdir = sys.argv[2]
    what = sys.argv[4].split(",") if len(sys.argv) > 4 else ["O", "G", "S", "R"]
    if "O" in what:
        for master in ("Regular", "Black", "Italic", "Black Italic"):
            log = overview_group(G, master, os.path.join(outdir, "overview_group_HS%s.png" % master.replace(" ", "")))
            print(master, [l for l in log if l[1] != "ok"] or "all ok")
    if "G" in what:
        for key in all_keys(G):
            groups_sheet(G, key, os.path.join(outdir, fname(key) + "_groups.png"))
        print("groups sheets", len(all_keys(G)))
    if "S" in what:
        sweep_sheet(G, "HSItalic_e", os.path.join(outdir, "e_Italic_sweep.png"))
        sweep_sheet(G, "HSItalic_v", os.path.join(outdir, "v_Italic_sweep.png"))
    if "R" in what:
        terminal_zooms(G, os.path.join(outdir, "r_terminals_0_100.png"),
                       [("HSRegular_r", (150, 250, 380, 520)), ("HSBlack_r", (190, 200, 450, 530)),
                        ("HSItalic_r", (150, 200, 450, 520)), ("HSBlackItalic_r", (200, 200, 520, 520))])
    sys.exit()

if __name__ == "__main__":
    G = json.load(open(sys.argv[1])); outdir = sys.argv[2]
    which = sys.argv[3].split(",") if len(sys.argv) > 3 else ["A", "B", "C", "D"]
    keys = ["HSItalic_n", "HSItalic_k", "HSItalic_x", "HSBlackItalic_n", "HSBlackItalic_k", "HSBlackItalic_x"]
    if len(sys.argv) > 4:
        keys = sys.argv[4].split(",")
    for key in keys:
        if "A" in which:
            GM = groups_sheet(G, key, os.path.join(outdir, fname(key) + "_groups.png"))
        else:
            GM = None
        if "B" in which:
            nested_sheet(G, key, os.path.join(outdir, fname(key) + "_nested.png"), GM=GM)
        print("done", key)
    if "C" in which:
        for master in ("Italic", "Black Italic"):
            xkn_sheet(G, master, os.path.join(outdir, "xkn_%s_groups_0_100.png" % master.replace(" ", "")))
    if "D" in which:
        sweep_sheet(G, "HSItalic_n", os.path.join(outdir, "n_Italic_sweep.png"))
    print("ok")
