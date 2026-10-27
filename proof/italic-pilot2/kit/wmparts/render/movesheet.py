"""CNTR 0 / 50 / 100 in Mark's blend style: each part's two sides + 3 blends, moved; drawn outline dashed."""
import sys, os, json
import numpy as np
from PIL import Image
from ..mover import Mover
from .draw import Panel, bbox_of, BG, SS
from .partsheet import COLS, FLAG, draw_poly, draw_flag
from ..rungs import Outline


def moved_side(S, sL, dL, t, M):
    return [(p[0] + v[0] * t, p[1] + v[1] * t) for p, v in ((p, M.interp(s, sL, dL)) for p, s in zip(S.pts, S.al))]


def panel(M, t, W, H, bb, title):
    A = Panel(W, H, bb, margin=36)
    A.title(title, "sides + 3 blends per part, moved along their rungs · dashed = drawn · A = %.0f · window %.0f–%.0f" % (M.A, M.thin_top, M.thick_bot))
    # moved outline, light fill
    ol2 = Outline(M.contours_at(t))
    A.fill_outline(ol2, color=(30, 36, 26), edge=(60, 60, 60))
    if t > 0:
        for poly in M.ol.polys:
            draw_poly(A, poly + [poly[0]], (120, 120, 120), 0.8, dash=6)
    for i, (SA, saL, dAL, SB, sbL, dBL, st) in enumerate(M.side_disp):
        col = COLS[i % len(COLS)]
        pa = moved_side(SA, saL, dAL, t, M); pb = moved_side(SB, sbL, dBL, t, M)
        draw_poly(A, pa, col, 1.4); draw_poly(A, pb, col, 1.4)
        # blends between moved sides, by rung spans
        rs = [(r[0], r[1]) for r in st["rungs"] if r[0] is not None and r[1] is not None and r[2] not in ("cross", "long")]
        for u, w in ((0.25, 0.8), (0.5, 1.5), (0.75, 0.8)):
            pts = []
            for (a0, b0), (a1, b1) in zip(rs, rs[1:]):
                for k in range(25):
                    f = k / 24
                    sa = a0 + (a1 - a0) * f; sb = b0 + (b1 - b0) * f
                    qa = SA.at(sa); va = M.interp(sa, saL, dAL); qa = (qa[0] + va[0] * t, qa[1] + va[1] * t)
                    qb = SB.at(sb); vb = M.interp(sb, sbL, dBL); qb = (qb[0] + vb[0] * t, qb[1] + vb[1] * t)
                    pts.append((qa[0] + (qb[0] - qa[0]) * u, qa[1] + (qb[1] - qa[1]) * u))
            draw_poly(A, pts, col if u != 0.5 else (255, 255, 255), w)
    for fl in M.P.flags:
        draw_flag(A, M.P, fl)
    return A.out()


def movesheet(G, key, out_path, W=820, H=860):
    g = G[key]; M = Mover(g)
    bb = bbox_of(M.ol, pad=50)
    ims = [panel(M, t, W, H, bb, "/%s %s · CNTR %d" % (g["glyph"], g["master"], int(t * 100))) for t in (0.0, 0.5, 1.0)]
    sheet = Image.new("RGB", (W * 3 + 20, H), BG)
    for i, im in enumerate(ims):
        sheet.paste(im, (i * (W + 10), 0))
    sheet.save(out_path)
    return M


