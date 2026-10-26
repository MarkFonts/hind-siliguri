"""Round 5 · pass 2: the score at 14.04 deg against Mark's drawn italic (italic/src/mark_saopne_pdf_paths.json).

score_p2.py [s,a,o,p,e,n]      -> sheets/score_<g>.png, readings/score_p2.json, readings/score_variants_14.json,
                                  sheets/I17_opa.png

Candidates per letter (all from the extracted Regular, the same upright for every column):
  slant        the plain slant x + y/4
  pass 1       round 5 pass 1's Italic key (src/..._14.json, GeistSerifItalicPass1_<g>: I10-I14 + harmonizer)
  pass 2 -I17  pass 2 (round_p2.correct, steps 1-6) with I17 OFF
  pass 2 +I17v pass 2 with I17 ON, the s round's wording: re-seat to the TRUE vertical tangent
  pass 2 +I17  pass 2 with I17 ON, re-seat to the tangent parallel to the ITALIC angle (shipped)
  (and pass 2 steps 1-3, the skeleton alone, for the record)

Placement of his drawing (the same for every column of a letter):
  o, e      centre at mid-height (a round part's centre stays where the shear puts it; drawn.placement)
  p, n, a   by the stems (drawn.placement)
  s         by INK CENTROID on the plain slant's (the s round's rule: the terminals ride now, so the held corners that
            placed it in pass 1 hold nothing). Pass 1's own corner-placed number is reported beside it.
XOR % = area(candidate XOR drawing) / area(drawing), 2 px/u, nonzero fill.
e and n are UNFINISHED drawings (Mark, 2026-10-25): reference rows only, no fit, not in the mean.
"""
import sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
C.set_slant(0.25)
import drawn, drawn5s
from round_p2 import correct
from proof5s import Sheet, INK, DIM, FAINT

OUT = os.path.join(C.R5, "sheets")
LBL = "round 5 · pass 2"
A14 = "14.04°  (x' = x + y/4)"
LETTERS = ["s", "a", "o", "p", "e", "n"]
FIT = ["s", "a", "o", "p"]
COL = dict(drawn=(112, 112, 118), drawnS=(178, 178, 184), slant=(240, 72, 58), p1=(80, 145, 255), p2=(90, 222, 118),
           alt=(250, 200, 70), p2x=(225, 110, 230), p2i=(80, 200, 235))
NAME = dict(drawn="his drawn italic", slant="plain slant", p1="pass 1", p2="pass 2", p2x="pass 2, other I17 state")


def place(gl, frame):
    raw = drawn.raw_contours(gl, "italic")
    if gl == "s":
        dx = drawn5s.centroid_x(frame) - drawn5s.centroid_x(raw)
        return drawn.shift(raw, dx), "ink centroid on the plain slant's"
    d = drawn.letter(gl, "italic", frame)
    return d["contours"], d["placed"]


def candidates(gl, G):
    sl = G["GeistSerifSlant_" + gl]["contours"]
    # pass 1 = pass 1's rules on the SAME upright: for the s that is GeistSerifItalicPass1Rules_s (pass 1's pipeline on
    # Mark's drawn roman s, build_his_s.py); pass 1 as delivered was made from the old extracted s
    p1 = G.get("GeistSerifItalicPass1Rules_" + gl) or G["GeistSerifItalicPass1_" + gl]
    return dict(slant=sl, p1=p1["contours"],
                p2_noI17=correct(gl, G, "1-6", i17=False)["contours"],
                p2_I17v=correct(gl, G, "1-6", i17=True, i17_target="vertical")["contours"],
                p2_I17=correct(gl, G, "1-6", i17=True, i17_target="italic")["contours"],
                p2_13=correct(gl, G, "1-3")["contours"], p2_13_noI17=correct(gl, G, "1-3", i17=False)["contours"],
                p2_13_I17v=correct(gl, G, "1-3", i17=True, i17_target="vertical")["contours"],
                p2_13_I17=correct(gl, G, "1-3", i17=True, i17_target="italic")["contours"])


def onc(cs):
    return [np.array(n[:2], float) for c in cs for n in c["nodes"] if n[2] != "o"]


def residual(cand, D):
    """mutual-nearest on-curve nodes, candidate -> drawing (the two are not node-compatible everywhere)"""
    pa, pb = onc(cand), onc(D); out = []
    for p in pa:
        q = min(pb, key=lambda q: np.linalg.norm(p - q))
        back = min(pa, key=lambda r: np.linalg.norm(q - r))
        if back is p:
            out.append((p, q, float(np.linalg.norm(q - p))))
    return out


def box(*cs):
    xs = [n[0] for c_ in cs for c in c_ for n in c["nodes"]]; ys = [n[1] for c_ in cs for c in c_ for n in c["nodes"]]
    return (min(xs) - 40, min(-40, min(ys) - 30), max(xs) + 40, max(600, max(ys) + 30))


def score_sheet(gl, D, how, cand, X, ship_i17, out):
    p2 = cand["p2_I17" if ship_i17 else "p2_noI17"]; p2x = cand["p2_noI17" if ship_i17 else "p2_I17"]
    unf = gl in drawn.UNFINISHED
    B = box(D, *cand.values())
    W, H = 2240, 1980
    sh = Sheet(W, H)
    up_note = ("upright = MARK'S DRAWN ROMAN s (anchor-free; source change, pass 2) for every column; pass 1 = pass 1's rules on it"
               if gl == "s" else "upright = the extracted Geist Serif Regular for every column")
    sh.title("/%s  ·  %s  ·  scored against Mark's drawn italic (new_italics.pdf, 2026-10-25)" % (gl, LBL), A14,
             "%s · his drawing placed by %s (never the bbox)" % (up_note, how))
    if unf:
        sh.text(26, 112, "drawn %s NOT corrected by Mark yet: reference only, no fit, no score" % gl, (255, 120, 90), 20)
    sh.key(26, 140, [(NAME["drawn"], COL["drawn"]), (NAME["slant"], COL["slant"]), (NAME["p1"], COL["p1"]),
                     ("pass 2 (shipped: I17 %s)" % ("on, italic-angle tangent" if ship_i17 else "off"), COL["p2"])], 19)
    p1 = sh.panel(20, 180, 1090, 1000, B); p1.frame()
    for y in (0, 545, -200):
        p1.hline(y)
    p1.fill(D, COL["drawn"])
    p1.outline(cand["slant"], COL["slant"], 1.8); p1.outline(cand["p1"], COL["p1"], 1.8); p1.outline(p2, COL["p2"], 2.4)
    sh.text(32, 188, "outlines over his solid drawing", DIM, 15)
    p2p = sh.panel(1130, 180, 1090, 1000, B); p2p.frame()
    for y in (0, 545, -200):
        p2p.hline(y)
    p2p.fill(D, (52, 52, 58)); p2p.outline(D, (225, 225, 225), 1.5); p2p.outline(p2, COL["p2"], 1.6)
    res = residual(p2, D)
    for p, q, d in res:
        p2p.dot(p, COL["p2"], 4, fill=False)
        if d >= 1.5:
            p2p.arrow(p, q, COL["alt"], 3, gain=2.0)
        if d >= 4:
            p2p.label(p + 2 * (q - p), "%.0f" % d, COL["alt"], 15)
    for q in onc(D):
        p2p.dot(q, (230, 230, 230), 3, fill=False)
    sh.text(1142, 188, "residual: pass 2 node → its mutual-nearest drawn node (arrows ×2, u)", COL["alt"], 15)
    # row 2: solids
    y2 = 1230; pw = 535
    items = [("drawnS", D, "his drawn italic", None), ("slant", cand["slant"], "plain slant", X["slant"]),
             ("p1", cand["p1"], "pass 1", X["p1"]), ("p2", p2, "pass 2", X["p2_I17" if ship_i17 else "p2_noI17"])]
    sh.text(26, y2 - 28, "SOLID, side by side (same frame, same scale); XOR against his drawing under each", DIM, 15)
    for k, (key, cs, nm, x) in enumerate(items):
        pn = sh.panel(20 + k * (pw + 20), y2, pw, 560, B)
        pn.hline(0); pn.hline(545)
        pn.fill(cs, COL[key])
        sh.text(30 + k * (pw + 20), y2 + 566, nm + ("" if x is None else "   XOR %.1f %%" % x), COL[key], 21)
    yy = H - 110
    t = "XOR vs his drawing:  "
    sh.text(26, yy, t, INK, 21); x = 26 + sh.tlen(t, 21)
    for key, k2, nm in (("slant", "slant", "plain slant"), ("p1", "p1", "pass 1"), ("p2", "p2_noI17", "pass 2 (shipped, −I17)"),
                        ("p2x", "p2_I17v", "+I17 vertical"), ("p2i", "p2_I17", "+I17 italic")):
        s_ = "%s %.1f %%" % (nm, X[k2]); sh.text(x, yy, s_, COL[key], 21); x += sh.tlen(s_, 21) + 30
    big = [d for _, _, d in res]
    sh.text(26, yy + 36, "skeleton only (steps 1–3): −I17 %.1f %%, +I17 vertical %.1f %%, +I17 italic %.1f %%   ·   residual nodes (pass 2): median %.1f u, max %.1f u" % (
        X["p2_13_noI17"], X["p2_13_I17v"], X["p2_13_I17"], float(np.median(big)), max(big)), DIM, 15)
    sh.text(26, yy + 62, "XOR = area of the symmetric difference / his drawing's area, 2 px/u, nonzero fill", FAINT, 14)
    return sh.save(out)


def i17_sheet(R, out):
    """o p a: pass 2 without / with I17, outline over his solid, residual vectors to his nodes"""
    W, H = 2280, 2160
    sh = Sheet(W, H)
    sh.title("I17 re-seat side extremes  ·  /o /p /a  ·  %s" % LBL, A14,
             "his drawing solid grey · pass 2 outline · yellow = pass 2 node → his mutual-nearest node (arrow ×2, label in u)")
    sh.key(26, 122, [(NAME["drawn"], COL["drawn"]), ("I17 OFF (shipped)", COL["p2"]), ("I17 to the TRUE VERTICAL tangent (s round)", COL["p2x"]),
                     ("I17 to the tangent at the ITALIC ANGLE", COL["p2i"]), ("residual", COL["alt"])], 19)
    cols = (("p2_noI17", COL["p2"], "I17 OFF", "p2_13_noI17"), ("p2_I17v", COL["p2x"], "I17 vertical", "p2_13_I17v"),
            ("p2_I17", COL["p2i"], "I17 italic", "p2_13_I17"))
    for r, gl in enumerate(("o", "p", "a")):
        D, cand, X = R[gl]["D"], R[gl]["cand"], R[gl]["X"]
        B = box(D, cand["p2_I17"])
        for k, (key, col, nm, k13) in enumerate(cols):
            pn = sh.panel(20 + k * 750, 160 + r * 660, 730, 640, B); pn.frame()
            pn.hline(0); pn.hline(545)
            pn.fill(D, COL["drawn"]); pn.outline(cand[key], col, 2.0)
            res = residual(cand[key], D)
            for p, q, d in res:
                pn.dot(p, col, 4)
                if d >= 1.5:
                    pn.arrow(p, q, COL["alt"], 2.5, gain=2.0)
                if d >= 6:
                    pn.label(p + 2 * (q - p), "%.0f" % d, COL["alt"], 14)
            big = [d for _, _, d in res]
            sh.text(34 + k * 750, 168 + r * 660, "/%s  %s   XOR %.1f %%  (skeleton %.1f %%)" % (gl, nm, X[key], X[k13]), col, 17)
            sh.text(34 + k * 750, 192 + r * 660, "residual nodes: median %.1f u, max %.1f u" % (float(np.median(big)), max(big)), col, 15)
    return sh.save(out)


def js(o):
    if isinstance(o, dict):
        return {str(k): js(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [js(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return round(float(o), 3)
    return o


def main(letters):
    G = C.load()
    R = {}; V = {}
    for gl in letters:
        cand = candidates(gl, G)
        D, how = place(gl, cand["slant"])
        X = {k: drawn.xor_pct(v, D) for k, v in cand.items()}
        up = G["GeistSerifRegular_" + gl]["contours"]
        floor = drawn.xor_pct(up, drawn.letter(gl, "roman", up)["contours"])
        extra = {}
        if gl == "s":
            Dc, _ = drawn5s.italic(cand["slant"], "corners")
            extra["corners_placement"] = {k: round(drawn.xor_pct(v, Dc), 2) for k, v in cand.items()}
        R[gl] = dict(D=D, cand=cand, X=X)
        V[gl] = dict(cand, drawn=D)
        res = dict(xor={k: round(v, 2) for k, v in X.items()}, floor=round(floor, 2), placed=how, unfinished=gl in drawn.UNFINISHED, **extra)
        R[gl]["res"] = res
        print(gl, json.dumps(res))
    import round_p2
    for gl in letters:
        score_sheet(gl, R[gl]["D"], R[gl]["res"]["placed"], R[gl]["cand"], R[gl]["X"], round_p2.I17,
                    os.path.join(OUT, "score_%s.png" % gl))
    if all(g in R for g in ("o", "p", "a")):
        i17_sheet(R, os.path.join(OUT, "I17_opa.png"))
    json.dump({g: R[g]["res"] for g in R}, open(os.path.join(C.R5, "readings", "score_p2.json"), "w"), indent=1)
    json.dump(js(V), open(os.path.join(C.R5, "readings", "score_variants_14.json"), "w"))


if __name__ == "__main__":
    main(sys.argv[1].split(",") if len(sys.argv) > 1 else LETTERS)
