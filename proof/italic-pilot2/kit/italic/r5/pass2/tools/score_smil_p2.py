"""Round 5 · pass 2: SMIL score animations, sheets/score_<g>.svg (s a o p, and e n as unfinished reference).

The glyph SOLID-FILLED morphs upright -> plain slant -> pass 1 -> pass 2 -> upright (12 s loop, holds between, state
ticker with the XOR). Left: the glyph alone. Right: Mark's drawn italic solid grey under the same morph in green at 55 %.
All four states share every node (nothing changes structure), so one <animate attributeName="d"> morphs them. The
drawing is placed as score_p2.py places it (readings/score_variants_14.json, written by score_p2.py).
Helpers (path data, keyframes, the ticker) are the s round's score_smil5s.py.
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
C.set_slant(0.25)
import drawn
import score_smil5s as SM

OUT = os.path.join(C.R5, "sheets")
SM.STATES = [("upright", "UPRIGHT  Geist Serif Regular", 0.00, 0.08),
             ("slant", "PLAIN SLANT  14.04°  (x' = x + y/4)", 0.17, 0.30),
             ("p1", "ROUND 5 PASS 1  (I10–I14 + harmonizer)", 0.39, 0.54),
             ("p2", "ROUND 5 · PASS 2  (I15 I16, arm serifs sheared)", 0.63, 0.88)]
BG, INK, GREY, GREEN, LBL, DIM = SM.BG, SM.INK, SM.GREY, SM.GREEN, SM.LBL, SM.DIM


def build(gl, G, V):
    S = SM.S; Y0, Y1, T = SM.Y0, SM.Y1, SM.T
    up = G["GeistSerifRegular_" + gl]["contours"]
    states = [up, V["slant"], V["p1"], V["p2_noI17"]]
    st0 = SM.structure(up)
    for c in states[1:]:
        assert SM.structure(c) == st0, gl
    D = V["drawn"]
    xor = {k: drawn.xor_pct(c, D) for k, c in zip(("slant", "p1", "p2"), states[1:])}
    unf = gl in drawn.UNFINISHED
    xs = [n[0] for cs in states + [D] for c in cs for n in c["nodes"]]
    x0, x1 = min(xs) - 60, max(xs) + 60
    PW = (x1 - x0) * S; PH = (Y1 - Y0) * S
    GAP = 40; HEAD = 190; FOOT = 110
    W = max(PW * 2 + GAP + 40, 1560.0); H = HEAD + PH + FOOT
    LX = (W - (PW * 2 + GAP)) / 2; RX = LX + PW + GAP
    ds = [SM.d_of(c) for c in states]
    vals, times = SM.keyframes(ds)
    anim = ('<animate attributeName="d" dur="%.1fs" repeatCount="indefinite" calcMode="linear" values="%s" keyTimes="%s"/>'
            % (T, ";".join(vals), ";".join("%.3f" % t for t in times)))
    tf = lambda ox: 'transform="translate(%.2f %.2f) scale(%.4f %.4f)"' % (ox - x0 * S, HEAD + Y1 * S, S, -S)
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.0f %.0f" width="%.0f" height="%.0f" font-family="Menlo, SF Mono, monospace">' % (W, H, W, H),
         '<rect width="100%%" height="100%%" fill="%s"/>' % BG,
         '<text x="20" y="46" font-size="34" fill="%s">GEIST SERIF  14.04°  ·  /%s</text>' % (INK, gl),
         '<text x="20" y="76" font-size="17" fill="%s">round 5 · pass 2  ·  solid fill morphing UPRIGHT → PLAIN SLANT → PASS 1 → PASS 2 (every state shares the same nodes)</text>' % INK,
         '<text x="20" y="100" font-size="15" fill="%s">right: <tspan fill="%s">Mark\'s drawn italic</tspan> (new_italics.pdf, 2026-10-25) solid grey under <tspan fill="%s">the morph</tspan>, placed by %s</text>' % (DIM, GREY, GREEN, V.get("placed", "score_p2.py's rule"))]
    if unf:
        o.append('<text x="20" y="124" font-size="17" fill="#ff785a">drawn %s NOT corrected by Mark yet: reference only, no fit, no score</text>' % gl)
    for k, (key, name, a, b) in enumerate(SM.STATES):
        ov, ot = SM.opacity_track(k)
        x_txt = ("XOR vs drawn %.1f %%" % xor[key]) if key in xor else ""
        o.append('<g opacity="0"><animate attributeName="opacity" dur="%.1fs" repeatCount="indefinite" calcMode="discrete" values="%s" keyTimes="%s"/>'
                 '<text x="20" y="162" font-size="26" fill="%s">%s</text><text x="%.0f" y="162" font-size="26" fill="%s" text-anchor="end">%s</text></g>'
                 % (T, ov, ot, LBL, name, W - 130, GREEN if key == "p2" else INK, x_txt))
        cx = W - 20 - (len(SM.STATES) - 1 - k) * 22
        o.append('<circle cx="%.0f" cy="154" r="5" fill="%s" opacity="0.25"/>' % (cx, INK))
        o.append('<circle cx="%.0f" cy="154" r="5" fill="%s" opacity="0"><animate attributeName="opacity" dur="%.1fs" repeatCount="indefinite" calcMode="discrete" values="%s" keyTimes="%s"/></circle>' % (cx, LBL, T, ov, ot))
    for ox in (LX, RX):
        yb = HEAD + Y1 * S
        o.append('<line x1="%.0f" x2="%.0f" y1="%.1f" y2="%.1f" stroke="#3a3a3a"/>' % (ox, ox + PW, yb, yb))
        o.append('<line x1="%.0f" x2="%.0f" y1="%.1f" y2="%.1f" stroke="#2a2a2a"/>' % (ox, ox + PW, yb - 545 * S, yb - 545 * S))
    o.append('<g %s><path fill="%s" fill-rule="nonzero" d="%s">%s</path></g>' % (tf(LX), INK, ds[0], anim))
    o.append('<g %s><path fill="%s" fill-rule="nonzero" d="%s"/>' % (tf(RX), GREY, SM.d_of(D)))
    o.append('<path fill="%s" fill-opacity="0.55" fill-rule="nonzero" d="%s">%s</path>' % (GREEN, ds[0], anim))
    o.append('<path fill="none" stroke="%s" stroke-width="%.1f" d="%s">%s</path></g>' % (GREEN, 1.2 / S, ds[0], anim))
    o.append('<text x="20" y="%.0f" font-size="15" fill="%s">overlap = light green · only ours = dark green · only his = grey</text>' % (H - 60, DIM))
    o.append('<text x="20" y="%.0f" font-size="15" fill="%s">XOR vs drawn: <tspan fill="#f0483a">slant %.1f %%</tspan>  ·  <tspan fill="#5091ff">pass 1 %.1f %%</tspan>  ·  <tspan fill="%s">pass 2 %.1f %%</tspan>  ·  loop %.0f s</text>'
             % (H - 34, DIM, xor["slant"], xor["p1"], GREEN, xor["p2"], T))
    o.append('</svg>')
    return "\n".join(o)


def main(letters):
    G = C.load()
    V = json.load(open(os.path.join(C.R5, "readings", "score_variants_14.json")))
    P = json.load(open(os.path.join(C.R5, "readings", "score_p2.json")))
    for gl in letters:
        v = dict(V[gl]); v["placed"] = P[gl]["placed"]
        fn = os.path.join(OUT, "score_%s.svg" % gl)
        open(fn, "w").write(build(gl, G, v)); print(fn)


if __name__ == "__main__":
    main(sys.argv[1].split(",") if len(sys.argv) > 1 else ["s", "a", "o", "p", "e", "n"])
