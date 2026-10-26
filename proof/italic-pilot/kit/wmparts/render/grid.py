"""Parts-grid cells: one glyph's pairing over the letter (strokes, flags, slab serifs, balls, node numbers). render.grid() lays them out per master."""
import sys, os, json
from PIL import Image
from ..parts import Parts
from .draw import fontlabel, Panel, bbox_of, BG, SS, font, CAL
from .partsheet import draw_part, draw_flag, draw_poly, COLS
from ..masters import slant_stem  # noqa: F401  (grid.slant_stem in the old tools)

def draw_slab(A, ol, fl, FLAGC=(255, 80, 70)):
    """a slab serif: end face, face and bracket in red, a fan from the bracket to the face, root ringed"""
    import math
    B, F = fl["a"], fl["b"]
    E = next(sg for sg in ol.segs if (sg.gi, sg.gj) == fl["tip"])
    for sg in (B, F, E):
        draw_poly(A, sg.poly, FLAGC, 1.6)
    Fp = F.poly
    for p in B.poly[::4]:
        q = min(Fp, key=lambda f: math.dist(f, p))
        A.line(p, q, FLAGC, 0.6)
    if fl.get("root") is not None:
        x, y = ol.node_xy[fl["root"]][:2]
        X, Y = A.pt((x, y)); r = 6 * 2
        A.d.ellipse([X - r, Y - r, X + r, Y + r], outline=(250, 210, 60), width=3)


def cell(g, W, H, labels=True):
    sl, stem = slant_stem(g)
    P = Parts(g["contours"], slant=sl, stem=stem); ol = P.ol
    A = Panel(W, H, bbox_of(ol, pad=30), margin=28)
    nb = len(getattr(ol, "balls", []))
    A.title(fontlabel(g), "%d stroke%s, %d flag%s%s%s" % (len(P.strokes), "" if len(P.strokes) == 1 else "s", len(P.flags), "" if len(P.flags) == 1 else "s",
            (", %d ball%s" % (nb, "" if nb == 1 else "s")) if nb else "", ("  unpaired sides: %s" % P.unpaired) if P.unpaired else ""))
    A.fill_outline(ol, color=(38, 46, 30), edge=(90, 90, 90))
    for i, st in enumerate(P.strokes):
        draw_part(A, P, st, COLS[i % len(COLS)], labels=labels)
    for fl in P.flags:
        if fl.get("kind") == "slab":
            draw_slab(A, ol, fl)
        else:
            draw_flag(A, P, fl)
    for b in getattr(ol, "balls", []):
        import math
        r = b["D"] / 2
        circ = [(b["c"][0] + r * math.cos(t / 24 * math.pi), b["c"][1] + r * math.sin(t / 24 * math.pi)) for t in range(49)]
        draw_poly(A, circ, (60, 220, 240), 1.4)
        for k in b["segs"]:
            draw_poly(A, ol.segs[k].poly, (60, 220, 240), 2.6)
    A.nodes(ol, labels=labels)
    return A.out(), P
