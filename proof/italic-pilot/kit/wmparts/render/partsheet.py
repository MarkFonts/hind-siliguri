"""Render the parts pairing: over the letter, and pulled apart (Illustrator-blend style)."""
import sys, os, json, math
import numpy as np
from PIL import Image
from ..parts import Parts
from .draw import fontlabel, Panel, bbox_of, BG, SS, font, MENLO

COLS = [(235, 235, 235), (90, 140, 255), (120, 210, 120), (200, 120, 255), (255, 170, 60), (90, 220, 220)]
FLAG = (255, 80, 70)
HID = (150, 150, 150)


def draw_poly(panel, pts, col, w=1.0, dash=None):
    if len(pts) < 2:
        return
    if dash is None:
        panel.d.line([panel.pt(p) for p in pts], fill=col, width=max(1, int(w * SS)))
    else:
        on = True; acc = 0.0
        for a, b in zip(pts, pts[1:]):
            L = math.dist(a, b)
            if on:
                panel.line(a, b, col, w)
            acc += L
            if acc > dash:
                acc = 0.0; on = not on


def side_pieces(S):
    """split a side's polyline into visible and hidden runs"""
    runs = []; cur = []; curh = None
    for p, h in zip(S.pts, S.hidden):
        if curh is None or h == curh:
            cur.append(p)
        else:
            runs.append((curh, cur)); cur = [cur[-1], p] if cur else [p]
        curh = h
    if cur:
        runs.append((curh, cur))
    return runs


def draw_part(panel, P, stroke, col, off=(0, 0), labels=True, fill_nodes=True):
    ox, oy = off
    sh = lambda p: (p[0] + ox, p[1] + oy)
    for S in (stroke["A"], stroke["B"]):
        for hidden, run in side_pieces(S):
            draw_poly(panel, [sh(p) for p in run], HID if hidden else col, 1.3, dash=(8 if hidden else None))
    for u, w in ((0.25, 0.8), (0.5, 1.6), (0.75, 0.8)):
        pts = P.blend(stroke, u)
        draw_poly(panel, [sh(p) for p in pts], col if u != 0.5 else (255, 255, 255), w)
    for r in stroke["rungs"]:
        if r[0] is None or r[1] is None:
            continue
        th, L, pa, pb = P.thickness(stroke, r)
        rc = col if r[2] not in ("cross", "long") else (255, 60, 200)
        panel.line(sh(pa), sh(pb), rc, 1.6 if r[2] in ("node", "end") else 1.0)
        if labels:
            root = r[2] == "end" and L > 1.6 * th
            lbl = "%s↔%s %s" % ("·" if r[3] is None else r[3], "·" if r[4] is None else r[4], "root" if root else "%.0f" % th)
            mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            panel.text(sh(mid), lbl, rc, size=8, dx=4, dy=-10)
        for p, nd in ((pa, r[3]), (pb, r[4])):
            if nd is None:
                X, Y = panel.pt(sh(p)); rr = 2.2 * SS
                panel.d.ellipse([X - rr, Y - rr, X + rr, Y + rr], outline=(255, 255, 255), width=SS)


def draw_flag(panel, P, fl, off=(0, 0), n=5):
    ox, oy = off
    sh = lambda p: (p[0] + ox, p[1] + oy)
    a, b = fl["a"], fl["b"]       # a arrives at the tip, b leaves it
    tipA, tipB = a.pts[1], b.pts[0]
    farA, farB = a.pts[0], b.pts[1]
    panel.line(sh(farA), sh(tipA), FLAG, 1.3); panel.line(sh(tipB), sh(farB), FLAG, 1.3); panel.line(sh(tipA), sh(tipB), FLAG, 1.3)
    for k in range(1, n):
        u = k / n
        p0 = (tipA[0] + (tipB[0] - tipA[0]) * u, tipA[1] + (tipB[1] - tipA[1]) * u)
        p1 = (farA[0] + (farB[0] - farA[0]) * u, farA[1] + (farB[1] - farA[1]) * u)
        panel.line(sh(p0), sh(p1), FLAG, 0.8)


def partsheet(key, G, out_path, PW=900, PH=960):
    """G[key]'s parts over the letter | pulled apart, saved to out_path; returns the Parts"""
    im, P = parts_sheet(G[key], PW, PH)
    im.save(out_path)
    return P


def parts_sheet(g, PW=900, PH=960):
    """-> (PIL image, Parts): the pairing over the letter and the same parts pulled apart (slant + stem from g's master)"""
    from ..masters import slant_stem
    sl, stem = slant_stem(g)
    P = Parts(g["contours"], slant=sl, stem=stem); ol = P.ol
    bb = bbox_of(ol, pad=40)
    # over the letter
    A = Panel(PW, PH, bb, margin=50)
    nstk = len(P.strokes); nfl = len(P.flags)
    A.title(fontlabel(g) + " · parts, paired",
            "%d stroke%s + %d flag%s · sides, 3 blends, white = centreline · rung label: nodeA↔nodeB thickness · dashed = hidden continuation · ○ = between nodes" % (
                nstk, "" if nstk == 1 else "s", nfl, "" if nfl == 1 else "s"))
    A.fill_outline(ol, color=(38, 46, 30), edge=(90, 90, 90))
    for i, st in enumerate(P.strokes):
        draw_part(A, P, st, COLS[i % len(COLS)])
    for fl in P.flags:
        draw_flag(A, P, fl)
    A.nodes(ol)
    # pulled apart
    cx = (bb[0] + bb[2]) / 2; cy = (bb[1] + bb[3]) / 2
    bb2 = (bb[0] - 160, bb[1] - 160, bb[2] + 160, bb[3] + 160)
    B = Panel(PW, PH, bb2, margin=30)
    B.title(fontlabel(g) + " · the same parts pulled apart", "each part moved away from the centre; nothing else changed")
    for i, st in enumerate(P.strokes):
        pts = np.array(st["A"].pts + st["B"].pts); c = pts.mean(0)
        d = (c[0] - cx, c[1] - cy); L = math.hypot(*d) or 1.0
        off = (d[0] / L * 130, d[1] / L * 130)
        draw_part(B, P, st, COLS[i % len(COLS)], off=off, labels=False)
    for fl in P.flags:
        pts = np.array([fl["a"].pts[0], fl["a"].pts[1], fl["b"].pts[1]]); c = pts.mean(0)
        d = (c[0] - cx, c[1] - cy); L = math.hypot(*d) or 1.0
        draw_flag(B, P, fl, off=(d[0] / L * 170, d[1] / L * 170))
    sheet = Image.new("RGB", (PW * 2 + 10, PH), BG)
    sheet.paste(A.out(), (0, 0)); sheet.paste(B.out(), (PW + 10, 0))
    return sheet, P


