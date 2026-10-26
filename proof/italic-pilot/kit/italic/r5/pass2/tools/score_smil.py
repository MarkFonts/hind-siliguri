"""SMIL animation of the score sheets: one SVG per letter, the glyph SOLID-FILLED, morphing
upright -> plain slant -> round 4 -> round 5 -> upright (holds between), with a state ticker.

Left panel: the morphing glyph alone, solid.  Right panel: Mark's drawn italic solid grey, the same morphing
glyph solid green at 55 % over it (overlap = dark green; grey = only the drawing has ink; light green = only ours),
plus its outline.  The four states share every node (the solver never changes structure), so one <animate d> morphs
them; the drawing has its own node count and is never morphed.  Placement of the drawing = drawn.placement (stems /
held corners / round centre), the same as score.py.

score_smil.py [letters]          default: s a o p e n  ->  sheets/smil/score_<g>.svg
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import drawn

R5 = os.path.abspath(os.path.join(HERE, ".."))
SRC14 = os.path.join(R5, "src", "geistserif_italic_14.json")
SRC_R4 = os.path.join(R5, "..", "src", "geistserif_italic.json")
OUT = os.path.join(R5, "sheets", "smil")

BG = "#0d0d0d"; INK = "#e6e6e6"; GREY = "#8a8a8a"; GREEN = "#5ad76e"; LBL = "#e8b84a"; DIM = "#9a9a9a"
S = 0.55                                   # px per unit
Y0, Y1 = -230.0, 800.0                     # units shown per panel
T = 12.0                                   # loop seconds

# timeline (fractions of T): state, start of hold, end of hold; morphs fill the gaps
STATES = [("upright", "UPRIGHT  Regular", 0.00, 0.08),
          ("slant", "PLAIN SLANT  14.04°  (x' = x + y/4)", 0.17, 0.30),
          ("r4", "ROUND 4  (I1–I9: half-angle slides)", 0.39, 0.54),
          ("r5", "ROUND 5  (I10–I14 + harmonize)", 0.63, 0.88)]


def d_of(contours):
    """path data; the command sequence depends only on the node types, so compatible states give compatible d"""
    out = []
    for c in contours:
        ns = c["nodes"]; N = len(ns)
        ons = [i for i in range(N) if ns[i][2] != "o"]
        if not ons:
            continue
        out.append("M%.2f %.2f" % (ns[ons[0]][0], ns[ons[0]][1]))
        for a, i in enumerate(ons):
            j = ons[(a + 1) % len(ons)]
            offs = [ns[q % N] for q in range(i + 1, i + 1 + ((j - i - 1) % N))]
            if len(offs) == 2:
                out.append("C%.2f %.2f %.2f %.2f %.2f %.2f" % (offs[0][0], offs[0][1], offs[1][0], offs[1][1], ns[j][0], ns[j][1]))
            else:
                out.append("L%.2f %.2f" % (ns[j][0], ns[j][1]))
        out.append("Z")
    return " ".join(out)


def structure(contours):
    return [tuple(n[2] for n in c["nodes"]) for c in contours]


def keyframes(ds):
    """values / keyTimes for the d animation: hold at each state, linear morph between, back to the first at the end"""
    vals, times = [], []
    for k, (_, _, a, b) in enumerate(STATES):
        vals += [ds[k], ds[k]]; times += [a, b]
    vals.append(ds[0]); times.append(1.0)
    return vals, times


def opacity_track(k):
    """a label is on during its state's hold (and half the morph into it)"""
    _, _, a, b = STATES[k]
    prev_end = STATES[k - 1][3] if k else None
    on = a if k == 0 else (prev_end + a) / 2
    off = b if k < len(STATES) - 1 else (b + 1.0) / 2
    vals, times = ["0", "1", "1", "0", "0"], [0.0, on, off, min(off + 0.001, 1.0), 1.0]
    if k == 0:
        vals, times = ["1", "1", "0", "0", "1"], [0.0, off, min(off + 0.001, 1.0), (STATES[-1][3] + 1.0) / 2, 1.0]
    return ";".join(vals), ";".join("%.3f" % t for t in times)


def build(gl, G, R4):
    up = G["GeistSerifRegular_" + gl]["contours"]
    sl = G["GeistSerifSlant_" + gl]["contours"]
    r4 = R4["GeistSerifItalic_" + gl]["contours"]
    r5 = G["GeistSerifItalic_" + gl]["contours"]
    states = [up, sl, r4, r5]
    st0 = structure(up)
    for nm, c in zip(("slant", "r4", "r5"), states[1:]):
        if structure(c) != st0:
            raise SystemExit("%s: %s is not node-compatible with the Regular" % (gl, nm))
    dr = drawn.letter(gl, "italic", sl); D = dr["contours"]
    xor = {k: drawn.xor_pct(c, D) for k, c in zip(("slant", "r4", "r5"), states[1:])}
    unfinished = gl in drawn.UNFINISHED

    allc = states + [D]
    xs = [n[0] for cs in allc for c in cs for n in c["nodes"]]
    x0, x1 = min(xs) - 60, max(xs) + 60
    PW = (x1 - x0) * S; PH = (Y1 - Y0) * S
    GAP = 40; HEAD = 170; FOOT = 110
    W = max(PW * 2 + GAP + 40, 1180.0); H = HEAD + PH + FOOT
    LX = (W - (PW * 2 + GAP)) / 2                     # panels centred when the letter is narrow
    RX = LX + PW + GAP
    ds = [d_of(c) for c in states]
    vals, times = keyframes(ds)
    anim = ('<animate attributeName="d" dur="%.1fs" repeatCount="indefinite" calcMode="linear" values="%s" keyTimes="%s"/>'
            % (T, ";".join(vals), ";".join("%.3f" % t for t in times)))

    def panel_tf(ox):
        return 'transform="translate(%.2f %.2f) scale(%.4f %.4f)"' % (ox - x0 * S, HEAD + Y1 * S, S, -S)

    o = []
    o.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.0f %.0f" width="%.0f" height="%.0f" font-family="Menlo, SF Mono, monospace">' % (W, H, W, H))
    o.append('<rect width="100%%" height="100%%" fill="%s"/>' % BG)
    o.append('<text x="20" y="44" font-size="30" fill="%s">GEIST SERIF  Regular → Italic 14.04°  ·  /%s%s</text>' % (INK, gl, "  ·  drawn e/n UNFINISHED (Mark), reference only" if unfinished else ""))
    o.append('<text x="20" y="74" font-size="15" fill="%s">solid fill, morphing UPRIGHT → PLAIN SLANT → ROUND 4 → ROUND 5 (every state shares the same nodes)</text>' % DIM)
    o.append('<text x="20" y="96" font-size="15" fill="%s">right: Mark\'s drawn italic (new_italics.pdf, 2026-10-25) solid grey under the same glyph, placed by %s</text>' % (DIM, dr["placed"].split(" (")[0]))
    # tickers
    for k, (key, name, a, b) in enumerate(STATES):
        ov, ot = opacity_track(k)
        x_txt = ("XOR vs drawn %.1f %%" % xor[key]) if key in xor else ""
        o.append('<g opacity="0"><animate attributeName="opacity" dur="%.1fs" repeatCount="indefinite" calcMode="discrete" values="%s" keyTimes="%s"/>'
                 '<text x="20" y="140" font-size="26" fill="%s">%s</text><text x="%.0f" y="140" font-size="26" fill="%s" text-anchor="end">%s</text></g>'
                 % (T, ov, ot, LBL, name, W - 130, GREEN if key == "r5" else INK, x_txt))
    # state dots
    for k, (key, name, a, b) in enumerate(STATES):
        cx = W - 20 - (len(STATES) - 1 - k) * 22
        ov, ot = opacity_track(k)
        o.append('<circle cx="%.0f" cy="132" r="5" fill="%s" opacity="0.25"/>' % (cx, INK))
        o.append('<circle cx="%.0f" cy="132" r="5" fill="%s" opacity="0"><animate attributeName="opacity" dur="%.1fs" repeatCount="indefinite" calcMode="discrete" values="%s" keyTimes="%s"/></circle>' % (cx, LBL, T, ov, ot))
    # baselines
    for ox in (LX, RX):
        yb = HEAD + Y1 * S
        o.append('<line x1="%.0f" x2="%.0f" y1="%.1f" y2="%.1f" stroke="#3a3a3a"/>' % (ox, ox + PW, yb, yb))
        o.append('<line x1="%.0f" x2="%.0f" y1="%.1f" y2="%.1f" stroke="#2a2a2a"/>' % (ox, ox + PW, yb - 530 * S, yb - 530 * S))
    # left: solid morph
    o.append('<g %s><path fill="%s" fill-rule="nonzero" d="%s">%s</path></g>' % (panel_tf(LX), INK, ds[0], anim))
    # right: drawn grey + morph green at 55 % + outline
    o.append('<g %s>' % panel_tf(RX))
    o.append('<path fill="%s" fill-rule="nonzero" d="%s"/>' % (GREY, d_of(D)))
    o.append('<path fill="%s" fill-opacity="0.55" fill-rule="nonzero" d="%s">%s</path>' % (GREEN, ds[0], anim))
    o.append('<path fill="none" stroke="%s" stroke-width="%.1f" d="%s">%s</path>' % (GREEN, 1.2 / S, ds[0], anim))
    o.append('</g>')
    o.append('<text x="20" y="%.0f" font-size="15" fill="%s">left: the solver\'s glyph, solid  ·  right: <tspan fill="%s">Mark\'s drawing</tspan> under <tspan fill="%s">the solver</tspan>, overlap <tspan fill="#3f7a46">dark green</tspan></text>' % (H - 60, DIM, GREY, GREEN))
    o.append('<text x="20" y="%.0f" font-size="15" fill="%s">XOR vs drawn (symmetric difference / drawing area): slant %.1f %%  ·  round 4 %.1f %%  ·  round 5 %.1f %%  ·  loop %.0f s, linear morph in node space</text>'
             % (H - 34, DIM, xor["slant"], xor["r4"], xor["r5"], T))
    o.append('</svg>')
    return "\n".join(o)


def main(letters):
    G = json.load(open(SRC14)); R4 = json.load(open(SRC_R4))
    os.makedirs(OUT, exist_ok=True)
    for gl in letters:
        svg = build(gl, G, R4)
        fn = os.path.join(OUT, "score_%s.svg" % gl)
        open(fn, "w").write(svg); print(fn, len(svg) // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1:] or ["s", "a", "o", "p", "e", "n"])
