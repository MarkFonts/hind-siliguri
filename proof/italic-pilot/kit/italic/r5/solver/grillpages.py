"""GRILL.pdf: an illustrated question paper for Mark (letter size, 200 dpi, light, one question per page).

Every option figure is the real outline: GroupMover / Mover output, or a hand-built option made on the real
points with GroupMover's own handle rules (grillfig.custom). Run:
    python3.13 grillpages.py OUTDIR
"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grillfig import *
from grillfig import _fonts
from PIL import Image, ImageDraw

DPI = 200
PW, PH = 1700, 2200
MX = 95
IMG = "/private/tmp/claude-502/-Users-Mark-Documents-Github/1390710e-1654-4392-a465-3fce7c767a3d/images"

HOOK = {20, 21, 24, 27, 30}


def P(path, size, var=None):
    """page font (no supersampling)"""
    k = ("page", path, size, str(var))
    if k not in _fonts:
        f = ImageFont.truetype(path, size)
        if var:
            try:
                f.set_variation_by_axes(var)
            except Exception:
                pass
        _fonts[k] = f
    return _fonts[k]


def wrap(d, text, font, width):
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=font) <= width:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def draw_text(d, xy, text, font, width, fill=INK, lead=1.32):
    x, y = xy
    for ln in wrap(d, text, font, width):
        d.text((x, y), ln, fill=fill, font=font)
        y += int(font.size * lead)
    return y


# ---- figure helpers -------------------------------------------------------------------------------------
def gmvec(key, drop=()):
    G = gm(key)
    v = {n: (float(a), float(b)) for n, (a, b) in G.vec.items()}
    for n in drop:
        v.pop(n, None)
    return v


def slide(key, nd, nxt, w):
    """the part of move w that runs along the straight edge nd -> nxt"""
    xy = flat_xy(drawn(key))
    dl = unit((xy[nxt][0] - xy[nd][0], xy[nxt][1] - xy[nd][1]))
    s = w[0] * dl[0] + w[1] * dl[1]
    return (dl[0] * s, dl[1] * s)


def off_line(key, nd, a, b, w):
    """how far point nd, moved by w, ends up off the drawn line a-b (units)"""
    xy = flat_xy(drawn(key))
    p = (xy[nd][0] + w[0], xy[nd][1] + w[1])
    dl = unit((xy[b][0] - xy[a][0], xy[b][1] - xy[a][1]))
    return abs((p[0] - xy[a][0]) * dl[1] - (p[1] - xy[a][1]) * dl[0])


def option(key, res, box, rings, W=740, H=520, **kw):
    """box: one (x0, y0, x1, y1), or a list of (box, caption) insets side by side"""
    if isinstance(box[0], (int, float)):
        return _option_one(key, res, box, rings, W, H, **kw)
    out = Image.new("RGB", (W, H), PAPER)
    dd = ImageDraw.Draw(out)
    n = len(box)
    x = 0
    ws = [int(W * wgt) for wgt in kw.pop("weights", [1.0 / n] * n)]
    ws[-1] = W - sum(ws[:-1])
    for (b, cap), w in zip(box, ws):
        im = _option_one(key, res, b, rings, w, H, **kw)
        out.paste(im, (x, 0))
        if x:
            dd.line([(x, 0), (x, H)], fill=(205, 205, 205), width=2)
        if cap:
            tw = dd.textlength(cap, font=P(CAL, 20))
            dd.rectangle([x + w - tw - 16, H - 34, x + w - 4, H - 6], fill=PAPER)
            dd.text((x + w - tw - 10, H - 32), cap, fill=(110, 110, 110), font=P(CAL, 20))
        x += w
    return out


def _option_one(key, res, box, rings, W=740, H=520, handles_of=(), grey=(), note=None, dash_drawn=True,
                fill=RES_FILL, labels=None):
    d = drawn(key)
    f = Fig(W, H, box, margin=18)
    f.fill(res, fill, RES_EDGE, 1.3)
    if dash_drawn:
        f.outline(d, DRAWN, 1.3, dash=7)
    if handles_of:
        f.handles(res, set(handles_of))
    x0, x1 = flat_xy(d), flat_xy(res)
    labels = labels or {}
    for nd in grey:
        f.ring(x1[nd], labels.get(nd, nd), (120, 120, 120), r=7, size=13, width=1.6)
    for nd in rings:
        m = math.dist(x0[nd], x1[nd])
        if m > 0.6:
            f.dot(x0[nd], HI, 3.0, hollow=True)
            f.arrow(x0[nd], x1[nd], HI, 2.4, head=min(10.0, max(5.0, m * f.s / SS * 0.5)))
            f.ring(x1[nd], labels.get(nd, nd), HI)
        else:
            f.ring(x1[nd], labels.get(nd, nd), INK)
    if note:
        for p, text in note:
            f.label(p, text, INK, 13)
    return f.image()


def stem_fig(key, box, path_runs, rings, W=760, H=640, labels=None, extra=None, note=None, zooms=()):
    """the letter dimmed, the region of interest drawn thick, the named points ringed; zooms = the boxes the
    answers show close up, drawn as dashed frames"""
    d = drawn(key)
    f = Fig(W, H, box, margin=20)
    f.fill(d, DIM_FILL, DIM_EDGE, 1.0)
    for zb, cap in zooms:
        x0, y0, x1, y1 = zb
        f.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], (110, 110, 110), 1.4, dash=6)
        if cap:
            f.label((x0, y1), cap, (90, 90, 90), 13, dx=4, dy=-20)
    for run, col in path_runs:
        f.poly(path_poly(d, run), col, 5.0)
    xy = flat_xy(d)
    labels = labels or {}
    for nd in rings:
        f.ring(xy[nd], labels.get(nd, nd), HI if nd not in (extra or ()) else (120, 120, 120))
    if note:
        for p, text in note:
            f.label(p, text, INK, 14)
    return f.image()


def full_box(key, pad=18):
    return bbox([drawn(key)], pad)


# ---- page layout ----------------------------------------------------------------------------------------
def page_question(n, total, topic, stem, stem_img, options, e_text="(E)  None of these. I'll draw it.", foot=None):
    pg = Image.new("RGB", (PW, PH), PAPER)
    d = ImageDraw.Draw(pg)
    d.text((MX, 70), "QUESTION %d" % n, fill=HI, font=P(CALB, 30))
    d.text((MX + 230, 74), topic, fill=(110, 110, 110), font=P(CAL, 26))
    d.line([(MX, 120), (PW - MX, 120)], fill=(200, 200, 200), width=2)
    # stem text (left) + stem figure (right)
    sw, sh = stem_img.size
    tw = PW - 2 * MX - sw - 30
    # 14 pt Newsreader, opsz 14, wght 400; the lines that fit beside the figure go there, the rest run
    # on below it at full width
    fnt = P(NEWS, 39, [400, 14]); lead = int(39 * 1.34)
    lines = wrap(d, stem, fnt, tw)
    nfit = max(0, (sh + 10) // lead)
    y = 145
    for ln in lines[:nfit]:
        d.text((MX, y), ln, fill=INK, font=fnt); y += lead
    if len(lines) > nfit:
        rest = " ".join(lines[nfit:])
        y = draw_text(d, (MX, 140 + sh + 18), rest, fnt, PW - 2 * MX, lead=1.34)
    text_end = y
    pg.paste(stem_img, (PW - MX - sw, 140))
    d.rectangle([PW - MX - sw, 140, PW - MX, 140 + sh], outline=(205, 205, 205), width=2)
    # options 2 x 2
    top = max(140 + max(sh, 0), text_end) + 28
    cw = (PW - 2 * MX - 30) // 2
    # when the stem ran long, the two option rows shrink to keep the (E) line and the footer on the page
    pitch = min(640, (PH - 150 - top) // 2)
    for i, (letter, img, cap) in enumerate(options):
        cx = MX + (i % 2) * (cw + 30)
        cy = top + (i // 2) * pitch
        iw, ih = img.size
        if pitch < 640:
            sc = (pitch - 120) / (ih + 0.0)
            img = img.resize((int(iw * sc), int(ih * sc)), Image.LANCZOS)
            iw, ih = img.size
        pg.paste(img, (cx, cy + 4))
        d.rectangle([cx, cy + 4, cx + iw, cy + 4 + ih], outline=(205, 205, 205), width=2)
        d.rounded_rectangle([cx + 8, cy + 12, cx + 66, cy + 58], 8, fill=INK)
        d.text((cx + 20, cy + 14), letter, fill=PAPER, font=P(CALB, 34))
        draw_text(d, (cx + 4, cy + ih + 14), cap, P(CAL, 25), iw - 8, lead=1.25)
    ey = top + 2 * pitch + 4
    if e_text:
        d.text((MX, ey), e_text, fill=INK, font=P(CALB, 27))
    if foot:
        draw_text(d, (MX, ey + 44), foot, P(CAL, 22), PW - 2 * MX, fill=(110, 110, 110))
    d.text((PW - MX - 140, PH - 60), "%d / %d" % (n, total), fill=(150, 150, 150), font=P(CAL, 22))
    return pg


# ---- the questions -----------------------------------------------------------------------------------
def q_arch_points():
    k = "HSItalic_n"; xy = flat_xy(drawn(k))
    base = gmvec(k, drop=HOOK)
    A = custom(k, base)
    vB = dict(base); vB[1] = (0.0, -28.0)
    off1 = off_line(k, 1, 0, 40, (0.0, -28.0))
    B = custom(k, vB)
    vC = dict(base); vC[1] = slide(k, 1, 0, (0.0, -28.0))
    C = custom(k, vC)
    slid = math.hypot(*vC[1])
    vD = dict(base); vD[7] = (0.0, 0.0); vD[10] = (0.0, 0.0)
    D = custom(k, vD)
    Z = [((290, 280, 450, 475), "top of the arch"), ((55, -5, 185, 125), "point 1")]
    box = Z
    rings = [1, 4, 7, 10]
    stem = ("The top of the n's arch is the thinnest part of the letter. To thicken it at CNTR 100, a set of "
            "points on the inside of the arch moves down together as one piece, 28 units (the full amount for "
            "Italic). Point 1 is where the inside of the arch leaves the stem. Point 10 is where the inside of "
            "the arch turns into the straight inside edge of the right leg.\n\nWhich points should move together?\n\n"
            "(In all four pictures the hook is left as drawn; that is question 5. Point 40, where the outside of "
            "the arch leaves the stem, slides up the stem as the code does now.)")
    sf = stem_fig(k, (40, -30, 520, 515), [([1, 4, 7, 10, 11], HI)], [1, 4, 7, 10, 11, 40], W=700, H=620,
                  extra=(11, 40), zooms=Z)
    opts = [("A", option(k, A, box, rings, grey=[40], weights=[0.56, 0.44]),
             "4 and 7 move down 28. 10 slides down the leg's straight edge. 1 stays on the stem. (What the code does now.)"),
            ("B", option(k, B, box, rings, grey=[40], weights=[0.56, 0.44]),
             "1, 4 and 7 all move straight down 28, like your Illustrator selection. 1 ends up %.0f units off the stem's edge, out in the counter." % off1),
            ("C", option(k, C, box, rings, grey=[40], weights=[0.56, 0.44]),
             "1, 4 and 7 move together, but 1 slides %.0f units down along the stem's edge, so it stays on the stem." % slid),
            ("D", option(k, D, box, rings, grey=[40], weights=[0.56, 0.44]),
             "Only 4 moves down 28. The shoulder (7) and 10 stay where they are drawn.")]
    return "Italic n, the arch: which points move together", stem, sf, opts


def q_black_direction():
    k = "HSBlackItalic_n"; xy = flat_xy(drawn(k))
    base = gmvec(k, drop=HOOK)
    G = gm(k)
    A = custom(k, base)
    vA = base[4]
    dy = vA[1]
    vB = dict(base); w = (0.0, dy)
    for nd in (4, 7):
        vB[nd] = w
    vB[10] = slide(k, 10, 11, w)
    B = custom(k, vB)
    lean = math.tan(math.radians(18.0))
    vC = dict(base); w2 = (dy * lean, dy)
    for nd in (4, 7):
        vC[nd] = w2
    vC[10] = slide(k, 10, 11, w2)
    C = custom(k, vC)
    Z = [((300, 255, 470, 505), "top of the arch"), (full_box(k), "whole letter")]
    box = Z
    rings = [4, 7, 10]
    ang = math.degrees(math.atan2(-vA[0], -vA[1]))
    stem = ("Black Italic n, same group as question 1: points 4 and 7 move together, and 10 slides down the leg. "
            "In the Italic the code moved the group straight down. In the Black Italic it tilted the move "
            "%.0f° to follow the leg's straight edge (10 to 11), so the top of the arch also moves %.0f units to the left. "
            "Each picture moves the group %.0f units down.\n\nWhich direction should the Black Italic arch move? "
            "(Your answer will also apply to the Italic.)" % (ang, -vA[0], -dy))
    sf = stem_fig(k, full_box(k), [([4, 7, 10], HI), ([10, 11], (120, 120, 120))], [4, 7, 10, 11], W=700, H=620, extra=(11,), zooms=Z[:1])
    opts = [("A", option(k, A, box, rings),
             "Along the leg's straight edge, %.0f° off vertical: down %.0f and left %.0f. The leg slides along itself and keeps its thickness. (What the code chose.)" % (ang, -dy, -vA[0])),
            ("B", option(k, B, box, rings),
             "Straight down %.0f, as the Italic does. 10 slides down the leg's edge by the part of the move that runs along it." % -dy),
            ("C", option(k, C, box, rings),
             "Along the italic slant (18°): down %.0f and left %.0f." % (-dy, -w2[0])),
            ]
    return "Black Italic n, the arch: which way it moves", stem, sf, opts


def q_point10():
    k = "HSItalic_n"; xy = flat_xy(drawn(k))
    base = gmvec(k, drop=HOOK)
    A = custom(k, base)
    vB = dict(base); vB[10] = (0.0, 0.0); B = custom(k, vB)
    vC = dict(base); vC[10] = (0.0, -28.0); C = custom(k, vC)
    thin = off_line(k, 10, 10, 11, (0.0, -28.0))
    vD = dict(base); vD[10] = (0.0, -28.0); vD[11] = (0.0, -28.0); D = custom(k, vD)
    Z = [((300, 250, 455, 445), "point 10"), ((200, 40, 500, 470), "the right leg")]
    box = Z
    rings = [7, 10, 11]
    stem = ("Point 10 is where the inside of the arch turns into the straight inside edge of the right leg "
            "(10 to 11). The leg is already as thick as the stem. When the arch group (4 and 7) moves down 28, "
            "what should point 10 do?")
    sf = stem_fig(k, full_box(k), [([7, 10], HI), ([10, 11], (60, 120, 200))], [4, 7, 10, 11], W=700, H=620, zooms=Z[:1])
    opts = [("A", option(k, A, box, rings),
             "10 slides %.0f units down along the leg's edge. The edge stays on its drawn line; the leg does not change. (What the code does now.)" % math.hypot(*base[10])),
            ("B", option(k, B, box, rings),
             "10 stays where it is drawn. The curve from 7 to 10 gets shorter and takes up all of the change."),
            ("C", option(k, C, box, rings),
             "10 moves straight down 28 with the group. The edge 10 to 11 tilts, and the leg gets %.0f units thinner at its top." % thin),
            ("D", option(k, D, box, rings),
             "10 and 11 both move down 28. The leg's whole inside edge shifts over, and the leg gets %.0f units thinner along its length." % thin)]
    return "Italic n, where the arch meets the right leg", stem, sf, opts


def q_handles():
    k = "HSItalic_n"
    G = gm(k)
    A = G.contours_at(1.0)
    d = drawn(k)
    P0 = flat_xy(d); Q = flat_xy(A)
    # Illustrator default on 21 -> 24: each handle rides with its own point, lengths as drawn
    B = json.loads(json.dumps(A))
    flatB = [n for c in B for n in c["nodes"]]
    for off, own in ((22, 21), (23, 24)):
        flatB[off][0] = Q[own][0] + (P0[off][0] - P0[own][0]); flatB[off][1] = Q[own][1] + (P0[off][1] - P0[own][1])
    # stretched: the drawn curve turned and scaled as one piece to fit its new ends
    C = json.loads(json.dumps(A))
    flatC = [n for c in C for n in c["nodes"]]
    a0, a1 = complex(*P0[21]), complex(*P0[24]); b0, b1 = complex(*Q[21]), complex(*Q[24])
    m = (b1 - b0) / (a1 - a0)
    for off in (22, 23):
        z = b0 + (complex(*P0[off]) - a0) * m
        flatC[off][0], flatC[off][1] = z.real, z.imag
    rot = math.degrees(math.atan2(m.imag, m.real))
    r = dict(((a, b), rr) for a, b, rr in G.connecting)[(21, 24)]
    box = (330, 12, 492, 136)
    rings = [21, 24]
    stem = ("When the two ends of a curve move by different amounts, the curve between them has to change. "
            "In the hook, the bottom of the cup (24) rises and the corner at the tip (21) slides along the end, "
            "so the curve from 21 to 24 gets %.0f%% as long as drawn.\n\nWhat should its two handles do? "
            "(The handles are drawn in blue.)" % (r * 100))
    sf = stem_fig(k, full_box(k), [([21, 24], HI)], [21, 24], W=700, H=620, zooms=[(box, "close-up")])
    opts = [("A", option(k, A, box, rings, handles_of=(21, 24)),
             "The handles keep their drawn directions and shrink with the curve, to %.0f%% of their length. (What the code does now.)" % (r * 100)),
            ("B", option(k, B, box, rings, handles_of=(21, 24)),
             "Each handle rides with its point, at its drawn length and direction (Illustrator's default when you move points)."),
            ("C", option(k, C, box, rings, handles_of=(21, 24)),
             "The drawn curve is turned (%.0f°) and scaled as one piece to fit between its new ends, so the handles turn too. Here it looks almost like A; it differs more on curves that turn more." % abs(rot)),
            ]
    return "Italic n, the curves that join a moved group", stem, sf, opts


def q_crescents():
    k = "HSItalic_x"
    base = gmvec(k)
    xy = flat_xy(drawn(k))
    vA = dict(base); vA[21] = (0.0, -2.8); vA[31] = (0.0, 3.3); A = custom(k, vA)
    vB = dict(base); vB[21] = (0.0, -14.0); vB[31] = (0.0, 14.0); B = custom(k, vB)
    vC = dict(base); vC[21] = (0.0, -28.0); vC[31] = (0.0, 28.0); C = custom(k, vC)
    Z = [((330, 330, 500, 510), "upper crescent"), ((-45, -25, 135, 155), "lower crescent")]
    box = Z
    rings = [21, 31]
    stem = ("The x's two curved strokes (the crescents) are 76 units thick at their thinnest, between 14 and 21 on top "
            "and between 31 and 39 at the bottom. The spec's rule says Italic strokes thinner than 56 get the full 28, and "
            "strokes thicker than 81 get nothing. So the crescents get only about 3 units, and the group code "
            "moves them by nothing at all. The outside edges sit on the x-height and the baseline and stay; "
            "the inside points 21 and 31 move.\n\nHow much should the crescents thicken at CNTR 100?")
    sf = stem_fig(k, full_box(k, 45), [([18, 21, 24], HI), ([28, 31, 34], HI)], [14, 21, 31, 39], W=700, H=620, extra=(14, 39), zooms=Z)
    opts = [("A", option(k, A, box, rings), "About 3 units, what the spec's rule asks for (21 down 3, 31 up 3)."),
            ("B", option(k, B, box, rings), "Half the full amount: 21 down 14, 31 up 14."),
            ("C", option(k, C, box, rings), "The full amount, like the n's arch: 21 down 28, 31 up 28."),
            ]
    return "Italic x, the thin curved strokes", stem, sf, opts


def q_hook():
    k = "HSItalic_n"
    base = gmvec(k)
    A = custom(k, base)
    vB = dict(base); w = (0.0, 28.2)
    vB[24] = w; vB[27] = w; vB[30] = slide(k, 30, 31, w); B = custom(k, vB)
    vC = {n: v for n, v in base.items() if n not in HOOK}; C = custom(k, vC)
    D = mv(k).contours_at(1.0)
    box = (255, -25, 500, 175)
    rings = [20, 21, 24, 27, 30]
    stem = ("Inside the hook, points 24 and 27 make the cup, the round bottom of the inside. Point 30 is where "
            "the cup turns into the straight right edge of the leg (30 to 31). The hook ends in the straight cut "
            "end 20 to 21.\n\nWhat should the hook do at CNTR 100? (Your answer also covers the k's kick, which is "
            "built the same way.)")
    sf = stem_fig(k, full_box(k), [([21, 24, 27, 30], HI), ([30, 31], (60, 120, 200))], [20, 21, 24, 27, 30], W=700, H=620, zooms=[(box, "close-up")])
    opts = [("A", option(k, A, box, rings),
             "24 and 27 rise together 30 units along the leg's edge direction, and 30 slides up that edge. The cut end slides along itself. (What the code does now.)"),
            ("B", option(k, B, box, rings),
             "24 and 27 rise straight up 28, and 30 slides up the leg's edge. The cut end slides along itself, as in A."),
            ("C", option(k, C, box, rings),
             "The hook stays exactly as drawn. Nothing in it moves."),
            ("D", option(k, D, box, rings),
             "The old move, where every point gets its own move: 21 moves up and out, so the hook gets longer, and the cup flattens.")]
    return "Italic n, the hook", stem, sf, opts


def q_r_terminal():
    k = "HSBlackItalic_r"; xy = flat_xy(drawn(k))
    base = gmvec(k)
    A = custom(k, base)
    dy = base[4][1]
    dl = unit((xy[8][0] - xy[9][0], xy[8][1] - xy[9][1]))
    s = dy / dl[1]
    vB = dict(base); vB[7] = (dl[0] * s, dl[1] * s); vB[8] = vB[7]; B = custom(k, vB)
    C = mv(k).contours_at(1.0)
    box = (270, 225, 505, 515)
    rings = [4, 7, 9]
    stem = ("The r's arm ends in a straight cut end, 8 to 9. Its underside runs 1, 4, 7, and point 7 is the "
            "corner where the underside meets the end. The code moves point 4 down %.0f and leaves 7 and the "
            "end alone, which leaves a small bump just before 7.\n\nWhat should the end of the arm do?" % -dy)
    sf = stem_fig(k, full_box(k), [([1, 4, 7], HI), ([8, 9], (60, 120, 200))], [1, 4, 7, 9], labels={7: "7, 8"}, W=700, H=620, zooms=[(box, "close-up")])
    opts = [("A", option(k, A, box, rings, labels={7: "7, 8"}),
             "4 moves down %.0f. 7, 8 and 9 stay, so the curve from 4 to 7 bunches into a bump. (What the code does now.)" % -dy),
            ("B", option(k, B, box, rings, labels={7: "7, 8"}),
             "4 moves down %.0f, and 7 and 8 slide %.0f down along the line of the end. The end gets longer at the bottom and keeps its angle." % (-dy, s)),
            ("C", option(k, C, box, rings, labels={7: "7, 8"}),
             "The old move, where every point gets its own move: 9 rises, and the arm gets longer and reaches higher."),
            ]
    return "Black Italic r, the end of the arm", stem, sf, opts


def q_v_arm():
    k = "HSItalic_v"; xy = flat_xy(drawn(k))
    base = gmvec(k)
    A = custom(k, base)
    vB = dict(base); vB[11] = base[14]; B = custom(k, vB)
    vC = dict(base); vC[0] = (28.0, 0.0); C = custom(k, vC)
    D = drawn(k)
    Z = [((140, -30, 345, 175), "bottom of the arm"), (full_box(k, 14), "whole letter")]
    box = Z
    rings = [0, 3, 11, 14]
    stem = ("The v's right arm is thinnest just above the bottom, where it is 35 units thick, between 14 (where "
            "it meets the left stroke) and the outside curve from 0 to 3. No point sits at that thin spot; the "
            "nearest are 14 and 11 on the inside and 0 and 3 on the outside. Today the code only slides 14 up "
            "the left stroke's edge by %.0f.\n\nWhat should happen to the arm?" % math.hypot(*base[14]))
    sf = stem_fig(k, full_box(k, 14), [([11, 14], HI), ([0, 3], HI)], [0, 3, 11, 14], W=700, H=620, zooms=Z[:1])
    opts = [("A", option(k, A, box, rings),
             "14 slides %.0f up the left stroke's edge. Nothing else moves. (What the code does now.)" % math.hypot(*base[14])),
            ("B", option(k, B, box, rings),
             "11 and 14 move together by the same amount, so the whole inside curve of the arm shifts up."),
            ("C", option(k, C, box, rings),
             "As A, and 0 also slides 28 to the right along the baseline. The arm thickens on its outside, and the v's bottom gets wider."),
            ("D", option(k, D, box, rings, dash_drawn=False),
             "The v is left exactly as drawn.")]
    return "Italic v, the thin arm", stem, sf, opts


def q_e_counter():
    k = "HSItalic_e"
    base = gmvec(k)
    A = custom(k, base)
    vB = dict(base); vB[9] = (0.0, 0.0); vB[15] = (0.0, 0.0); B = custom(k, vB)
    vC = dict(vB); vC[6] = (0.0, 0.0); C = custom(k, vC)
    vD = {n: (v[0] * 0.5, v[1] * 0.5) for n, v in base.items()}; D = custom(k, vD)
    box = full_box(k, 14)
    rings = [6, 9, 12, 15, 18, 19]
    stem = ("The e's thin places are the top of the eye (inside point 12), the bottom of the bowl (6) and the "
            "crossbar's end (18 to 19). The code moves 12 down 28 and takes points 9 and 15 along with it, raises "
            "6 by 25, and lengthens the crossbar's end. Your note from 10-22: the italic e should change less of "
            "its inside shape.\n\nHow much of the inside may change?")
    sf = stem_fig(k, box, [([6, 9, 12, 15, 18], HI)], rings, W=700, H=620)
    opts = [("A", option(k, A, box, rings),
             "12, 9 and 15 move down 28 together, and 6 rises 25. The counters lose height and their sides move. (What the code does now.)"),
            ("B", option(k, B, box, rings),
             "Only 12 moves down 28 and 6 rises 25. The sides of the counters (9, 15) stay where they are drawn."),
            ("C", option(k, C, box, rings),
             "Only the top of the eye (12) moves down 28. The bottom of the bowl (6) stays."),
            ("D", option(k, D, box, rings),
             "Like A, but everything moves half as far.")]
    return "Italic e, the inside shape", stem, sf, opts


def strip(key, mover, ts, W=740, H=560, combs=False):
    """the letter at several CNTR values side by side, one shared scale"""
    cs = [mover.contours_at(t / 100.0) for t in ts]
    box = bbox([drawn(key)] + cs, 14)
    n = len(ts)
    out = Image.new("RGB", (W, H), PAPER)
    cw = W // n
    for i, (t, c) in enumerate(zip(ts, cs)):
        f = Fig(cw, H - 40, box, margin=10)
        f.fill(c, RES_FILL, RES_EDGE, 1.0)
        out.paste(f.image(), (i * cw, 0))
        ImageDraw.Draw(out).text((i * cw + cw // 2 - 40, H - 36), "CNTR %d" % t, fill=INK, font=P(CAL, 22))
    return out


def comb_fig(key, cs, W, H, box=None, title=None):
    from curvcomb import analyse as an
    S0, K0, _, _ = an(drawn(key))
    allk = np.concatenate([np.abs(p["k"][~np.isnan(p["k"])]) for p in K0 if p is not None])
    scale = max(float(np.percentile(allk, 95)), 1e-4)
    box = box or bbox([drawn(key), cs], 60)
    f = Fig(W, H, box, margin=14)
    f.fill(cs, (232, 236, 242), (150, 160, 180), 1.0)
    comb(f, cs, scale, 40.0 / scale, 130.0, width=1.0)
    if title:
        f.tag(title, INK, 17)
    return f.image()


def q_acceptance():
    k = "HSItalic_n"
    G = gm(k)
    sA = strip(k, G, (20, 50, 100), H=520)
    sB = comb_fig(k, G.contours_at(1.0), 740, 520)
    il = Image.open(os.path.join(IMG, "12.webp")).convert("RGB").crop((800, 160, 1650, 1150))
    il.thumbnail((740, 520))
    sC = Image.new("RGB", (740, 520), PAPER); sC.paste(il, ((740 - il.size[0]) // 2, (520 - il.size[1]) // 2))
    sD = Image.new("RGB", (740, 520), PAPER)
    a = sA.resize((370, 280)); b = sB.resize((370, 280))
    sD.paste(a, (0, 120)); sD.paste(b, (370, 120))
    stem = ("At CNTR 100 the letters don't have to be usable, but every value up to 100 must be consistent. "
            "How will you decide that a letter is done?\n\n(Curvature comb: the bristles along each curve; "
            "their height shows how sharply the curve bends. A sudden jump in the bristles is a bump you would "
            "feel when you run a finger along the outline.)")
    sf = strip(k, G, (0, 25, 50, 75, 100), W=700, H=620)
    opts = [("A", sA, "You look at filled prints at CNTR 20, 50 and 100, by eye."),
            ("B", sB, "The curvature combs at CNTR 100 show no new bumps, like this n, and every point travels in a straight line from 0 to 100."),
            ("C", sC, "The n at 100 matches your own Illustrator n point for point. (Send me the .ai.)"),
            ("D", sD, "A and B together.")]
    return "How you will judge it", stem, sf, opts


def groups_fig(key, W, H, extra_rings=(), selected=None, title=None):
    G = gm(key)
    d = drawn(key)
    box = full_box(key)
    f = Fig(W, H, box, margin=16)
    f.fill(d, DIM_FILL, DIM_EDGE, 1.0)
    xy = flat_xy(d)
    cols = [HI, HI2, (60, 100, 200), (150, 70, 170)]
    if selected is None:
        for gi, g in enumerate(G.groups):
            col = cols[gi % len(cols)]
            nodes = list(g["levels"].keys())
            for nd in nodes:
                v = G.vec.get(nd, (0, 0))
                f.arrow(xy[nd], (xy[nd][0] + v[0], xy[nd][1] + v[1]), col, 2.2, head=7)
                f.ring(xy[nd], nd, col, r=8, size=14)
        for nd in extra_rings:
            f.ring(xy[nd], nd, (120, 120, 120), r=8, size=14, width=1.8)
    else:
        for nd in selected:
            X, Y = f.pt(xy[nd]); r = 6 * SS
            f.d.rectangle([X - r, Y - r, X + r, Y + r], fill=(30, 90, 220))
            f.label(xy[nd], str(nd), (30, 90, 220), 14, dx=8, dy=-10, bold=True)
    if title:
        f.tag(title, INK, 16)
    return f.image()


def q_who():
    k = "HSItalic_n"
    a = groups_fig(k, 740, 520)
    b = groups_fig(k, 740, 520)
    fb = Image.new("RGB", (740, 520), PAPER); fb.paste(b, (0, 0))
    db = ImageDraw.Draw(fb)
    for i, t in enumerate(["click a point to add it", "to a group or take it out"]):
        db.text((24, 114 + i * 28), t, fill=(60, 60, 60), font=P(CAL, 22))
    db.rounded_rectangle([12, 100, 282, 180], 10, outline=(120, 120, 120), width=2)
    c = groups_fig(k, 740, 520, selected=[1, 4, 7])
    stem = ("Someone has to decide which points move together. In the figure the code has proposed its groups "
            "for the Italic n: one color per group, and arrows show each point's move at CNTR 100.\n\n"
            "Who should choose the groups?")
    sf = groups_fig(k, 700, 620, extra_rings=())
    opts = [("A", a, "The code proposes them from the measurements, and you approve a sheet like this one, as you did with the parts."),
            ("B", fb, "The code proposes them, and a page lets you click points in or out of a group. Your changes are saved per letter and master."),
            ("C", c, "You select the points in Glyphs, and the selection is saved with the file. The code only moves what you selected."),
            ]
    return "Who chooses the groups", stem, sf, opts


def thumbs(keys, W, H, cols, top=0):
    """one shared scale for every letter, sitting on a common baseline"""
    out = Image.new("RGB", (W, H), PAPER)
    rows = math.ceil(len(keys) / cols)
    cw, ch = W // cols, (H - top) // rows
    ylo, yhi = -240.0, 800.0
    wu = max(SET[k]["width"] for k in keys) * 1.05
    for i, key in enumerate(keys):
        cx = SET[key]["width"] / 2.0
        f = Fig(cw, ch, (cx - wu / 2, ylo, cx + wu / 2, yhi), margin=0)
        f.fill(drawn(key), (60, 70, 90))
        out.paste(f.image(), ((i % cols) * cw, top + (i // cols) * ch))
    return out


def q_scope():
    lets = ["f", "j", "H", "n", "a", "E", "T", "r", "v", "e", "y", "k", "x"]
    ms = ["Regular", "Black", "Italic", "BlackItalic"]
    A = thumbs(["HSItalic_n", "HSBlackItalic_n"], 740, 520, 2, top=60)
    B = thumbs(["HS%s_%s" % (m, l) for m in ms for l in "nkxv"], 740, 520, 4, top=60)
    C = thumbs(["HS%s_%s" % (m, l) for m in ms for l in lets], 740, 520, 13, top=60)
    stem = ("What would make you say \"done\" for this round? The Harvey ligature is left out (your note: a "
            "leftover of the client's logotype). The letters H a r v e y themselves are in, and any accented "
            "letters built from these as components follow automatically.")
    sf = thumbs(["HSItalic_%s" % l for l in lets], 700, 620, 5, top=10)
    opts = [("A", A, "The n only, in Italic and Black Italic, judged against your own Illustrator n."),
            ("B", B, "n, k, x and v in all four masters: the letters whose parts you approved."),
            ("C", C, "All thirteen letters (f j H n a E T r v e y k x) in all four masters."),
            ]
    return "What counts as done", stem, sf, opts


# ---- preface + answer sheet ---------------------------------------------------------------------------
def preface(total):
    pg = Image.new("RGB", (PW, PH), PAPER)
    d = ImageDraw.Draw(pg)
    d.text((MX, 70), "Raising contrast in Harvey Sans", fill=INK, font=P(NEWS, 56, [500, 36]))
    d.text((MX, 150), "Questions for Mark, with a picture for every answer", fill=(110, 110, 110), font=P(CAL, 30))
    d.line([(MX, 205), (PW - MX, 205)], fill=(200, 200, 200), width=2)
    y = 230
    y = draw_text(d, (MX, y), "How to answer", P(CALB, 30), PW - 2 * MX)
    y = draw_text(d, (MX, y + 4),
                  "Each page asks one question and shows the letter, with the points it asks about numbered and "
                  "circled. Then come up to four answers. Each answer is a real outline at CNTR 100: the drawn "
                  "letter is dashed, the answer is filled blue, the points that move are circled in red, and the "
                  "arrows show how far they move. Answers marked \"what the code does now\" are the current build. "
                  "Mark the sheet on the last page, or reply with a line like \"1A 2B 3A ...\". Point numbers are "
                  "the node order in the .glyphs file. The node count, the order and the handles never change "
                  "(your rule); only the positions do.",
                  P(NEWS, 39, [400, 14]), PW - 2 * MX, lead=1.38)
    y += 26
    y = draw_text(d, (MX, y), "What I think we were missing", P(CALB, 30), PW - 2 * MX)
    pts = [
        "The measurements should decide which points move together and how far. They should not give every point its own move.",
        "When a group of points moves as one piece, every curve inside the group keeps its exact shape, so it cannot zigzag. "
        "A thin part still thickens most where it faces the move and less where it runs along it.",
        "All of the change lands in the one or two curves that join a moved group to points that stay, and in points "
        "that slide along a neighbor's straight edge.",
        "The old move gave every point its own move, so the curves between the points had to bend. Every rule added since was patching that.",
        "If you want the n's thin start by the stem to thicken as much as the top of the arch, this idea is wrong: moving one piece gives it less.",
    ]
    for t in pts:
        d.text((MX + 4, y + 4), "•", fill=HI, font=P(NEWS, 39, [400, 14]))
        y = draw_text(d, (MX + 36, y + 4), t, P(NEWS, 39, [400, 14]), PW - 2 * MX - 36, lead=1.34)
        y += 6
    # figure: old vs group, with combs
    k = "HSItalic_n"
    old = mv(k).contours_at(1.0); new = gm(k).contours_at(1.0)
    box = bbox([drawn(k), old, new], 70)
    fh = PH - y - 170
    fw = (PW - 2 * MX - 30) // 2
    a = comb_fig(k, old, fw, fh, box)
    b = comb_fig(k, new, fw, fh, box)
    y += 20
    pg.paste(a, (MX, y)); pg.paste(b, (MX + fw + 30, y))
    for x in (MX, MX + fw + 30):
        d.rectangle([x, y, x + fw, y + fh], outline=(205, 205, 205), width=2)
    d.text((MX + 14, y + 10), "Old: every point gets its own move", fill=INK, font=P(CALB, 25))
    d.text((MX + fw + 44, y + 10), "New: groups move as one piece", fill=INK, font=P(CALB, 25))
    draw_text(d, (MX, y + fh + 14),
              "Italic n at CNTR 100, with curvature combs (the bristles along each curve; their height shows how "
              "sharply the curve bends, with orange to red where it bends hard). On the left the combs jump at the "
              "top of the arch (4, 7) and in the hook (24, 27). On the right they run smoothly, because the "
              "curves inside each group keep their drawn shape.",
              P(CAL, 23), PW - 2 * MX, fill=(80, 80, 80))
    return pg


def answer_sheet(titles):
    pg = Image.new("RGB", (PW, PH), PAPER)
    d = ImageDraw.Draw(pg)
    d.text((MX, 70), "Answer sheet", fill=INK, font=P(NEWS, 56, [500, 36]))
    d.text((MX, 150), "Fill one bubble per question, or reply \"1A 2B 3C ...\". E means you'll draw it.", fill=(110, 110, 110), font=P(CAL, 28))
    d.line([(MX, 205), (PW - MX, 205)], fill=(200, 200, 200), width=2)
    y = 250
    rowh = 128
    for i, t in enumerate(titles):
        d.text((MX, y), "%d" % (i + 1), fill=HI, font=P(CALB, 36))
        d.text((MX + 70, y + 6), t, fill=INK, font=P(CAL, 27))
        for j, L in enumerate("ABCDE"):
            cx = MX + 80 + j * 110; cy = y + 70
            d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], outline=INK, width=3)
            d.text((cx - 9, cy - 17), L, fill=INK, font=P(CALB, 26))
        d.line([(MX + 640, y + 90), (PW - MX, y + 90)], fill=(190, 190, 190), width=2)
        d.text((MX + 640, y + 52), "notes", fill=(160, 160, 160), font=P(CAL, 20))
        y += rowh + 20
    return pg


PREFACE_POINTS = [
    "The measurements should decide which points move together and how far. They should not give every point its own move.",
    "When a group of points moves as one piece, every curve inside the group keeps its exact shape, so it cannot zigzag. "
    "A thin part still thickens most where it faces the move and less where it runs along it.",
    "All of the change lands in the one or two curves that join a moved group to points that stay, and in points "
    "that slide along a neighbor's straight edge.",
    "The old move gave every point its own move, so the curves between the points had to bend. Every rule added since was patching that.",
    "If you want the n's thin start by the stem to thicken as much as the top of the arch, this idea is wrong: moving one piece gives it less.",
]


def write_md(path, md):
    L = ["# GRILL: raising contrast in Harvey Sans", "",
         "Questions for Mark, one per page in `GRILL.pdf` (same folder). Every answer there has its own figure: "
         "the real outline at CNTR 100, the drawn letter dashed, moved points circled in red with arrows. "
         "Page images: `grill/page_NN.png`. Built by `tools/grillpages.py`; this file is written by the same run.", "",
         "Settled by Mark and not asked: node count, node order and handles never change (only positions do); "
         "the Harvey ligature is left out, while the letters H a r v e y and anything built from them as components are in.", "",
         "Answer with a line like `1A 2B 3C ...`; E means \"none of these, I'll draw it\".", "",
         "## What I think we were missing", ""]
    L += ["- " + t for t in PREFACE_POINTS]
    L += ["", "Figure (page 1): Italic n at CNTR 100, the old per-point move against the group move, with curvature combs.", ""]
    for i, (topic, stem, opts) in enumerate(md):
        L += ["## %d. %s" % (i + 1, topic), "", "Page %d." % (i + 2), ""]
        L += [stem.replace("\n\n", "\n\n"), ""]
        for letter, cap in opts:
            L.append("- **(%s)** %s" % (letter, cap))
        L += ["- **(E)** None of these. I'll draw it.", ""]
    open(path, "w").write("\n".join(L))


QUESTIONS = [q_arch_points, q_black_direction, q_point10, q_handles, q_hook, q_r_terminal, q_crescents,
             q_v_arm, q_e_counter, q_acceptance, q_who, q_scope]


def build(outdir):
    os.makedirs(outdir, exist_ok=True)
    pdir = os.path.join(outdir, "grill")
    os.makedirs(pdir, exist_ok=True)
    total = len(QUESTIONS)
    pages = [preface(total)]
    titles, md = [], []
    for i, q in enumerate(QUESTIONS):
        topic, stem, sf, opts = q()
        titles.append(topic)
        pages.append(page_question(i + 1, total, topic, stem, sf, opts))
        md.append((topic, stem, [(L, cap) for L, _, cap in opts]))
    pages.append(answer_sheet(titles))
    for i, pgi in enumerate(pages):
        pgi.save(os.path.join(pdir, "page_%02d.png" % (i + 1)))
    pages[0].save(os.path.join(outdir, "GRILL.pdf"), save_all=True, append_images=pages[1:], resolution=DPI)
    json.dump(md, open(os.path.join(pdir, "questions.json"), "w"), indent=1)
    write_md(os.path.join(outdir, "GRILL.md"), md)
    print("pages", len(pages))


if __name__ == "__main__":
    build(sys.argv[1])
