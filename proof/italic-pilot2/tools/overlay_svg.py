"""Roman vs italic overlay as SVG, Frutiger-sheet style: the italic is un-sheared by theta (about y 253.5) so it sits on
the roman; whatever differs is the correction (back-lean, stroke weight), not the slant.

usage: overlay_svg.py MASTER GLYPHS(comma list) OUT.svg [cols] [exaggerate]
  exaggerate (default 1): every italic node is moved EXAG times as far from its roman position, to make few-unit
  corrections visible; the sheet says so in its header.
"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); W = os.path.join(os.path.dirname(HERE), "work")
K = 0.25; YC = 253.5
master, names, out = sys.argv[1], sys.argv[2].split(","), sys.argv[3]
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 8
EXAG = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
UP = json.load(open(os.path.join(W, "upright_%s.json" % master)))
IT = json.load(open(os.path.join(W, "italic_%s.json" % master)))
LV = json.load(open(os.path.join(W, "levels.json")))


def d(cs, unshear=False):
    """contours ([x, y, type, smooth], Glyphs order: off-curves before the node they arrive at) -> SVG path data, y up"""
    out = []
    for c in cs:
        N = [list(n) for n in c["nodes"]]
        if unshear:
            N = [[n[0] - K * (n[1] - YC), n[1]] + n[2:] for n in N]
        if c["closed"]:
            i = next(i for i, n in enumerate(N) if n[2] != "o")
            N = N[i + 1:] + N[:i + 1]          # end on an on-curve, so it is also the start
            s = N[-1]
        else:
            s, N = N[0], N[1:]
        out.append("M%.1f %.1f" % (s[0], -s[1]))
        off = []
        for n in N:
            if n[2] == "o":
                off.append(n); continue
            if len(off) == 2:
                out.append("C%.1f %.1f %.1f %.1f %.1f %.1f" % (off[0][0], -off[0][1], off[1][0], -off[1][1], n[0], -n[1]))
            elif len(off) == 1:
                out.append("Q%.1f %.1f %.1f %.1f" % (off[0][0], -off[0][1], n[0], -n[1]))
            else:
                out.append("L%.1f %.1f" % (n[0], -n[1]))
            off = []
        if c["closed"]:
            out.append("Z")
    return " ".join(out)


CELL_W, CELL_H, TOP = 900, 1250, 520          # font units per cell; the sheet scales to fit
rows = (len(names) + cols - 1) // cols
Wd, Ht = cols * CELL_W + 120, TOP + rows * CELL_H + 80
BG, INK, DIM, BOTH, AWAY, ADDED = "#1c1c20", "#ececf0", "#96969e", "#78787f", "#f0483a", "#5ade76"
ITAL = AWAY


def exaggerated(up_cs, it_cs):
    """italic nodes un-sheared, then pushed EXAG times their distance from the roman node (same structure)"""
    out = []
    for cu, ci in zip(up_cs, it_cs):
        ns = []
        for nu, ni in zip(cu["nodes"], ci["nodes"]):
            x = ni[0] - K * (ni[1] - YC)
            ns.append([nu[0] + EXAG * (x - nu[0]), nu[1] + EXAG * (ni[1] - nu[1])] + list(nu[2:]))
        out.append({"closed": cu["closed"], "nodes": ns})
    return out
s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (Wd, Ht, Wd // 4, Ht // 4),
     '<rect width="100%%" height="100%%" fill="%s"/>' % BG,
     '<g font-family="Menlo, monospace">',
     '<text x="60" y="190" font-size="150" font-weight="bold" fill="%s" font-family="Helvetica, Arial, sans-serif">HIND SILIGURI %s</text>' % (ITAL, master.upper()),
     '<text x="60" y="290" font-size="60" fill="%s">roman vs %s Italic, pilot 2 &#183; italic un-sheared by &#952; 14.04&#176;, so only the correction shows%s</text>' % (INK, master, " &#183; corrections EXAGGERATED &#215;%g" % EXAG if EXAG != 1 else " &#183; true size"),
     '<rect x="60" y="350" width="60" height="60" fill="%s"/><text x="140" y="400" font-size="56" fill="%s">in both</text>' % (BOTH, BOTH),
     '<rect x="460" y="350" width="60" height="60" fill="%s"/><text x="540" y="400" font-size="56" fill="%s">taken away (roman only)</text>' % (AWAY, AWAY),
     '<rect x="1360" y="350" width="60" height="60" fill="%s"/><text x="1440" y="400" font-size="56" fill="%s">added (italic only)</text>' % (ADDED, ADDED),
     '</g>']
for i, gl in enumerate(names):
    r, c = divmod(i, cols)
    up, it = UP[gl], IT[gl]
    xs = [n[0] for cc in up["contours"] for n in cc["nodes"]] or [0, up["width"]]
    ox = 60 + c * CELL_W + (CELL_W - (max(xs) + min(xs))) / 2
    base = TOP + r * CELL_H + 900
    s.append('<g transform="translate(%.1f %.1f)">' % (ox, base))
    s.append('<line x1="%.1f" x2="%.1f" y1="0" y2="0" stroke="#3c3c44" stroke-width="3"/>' % (min(xs) - 60, max(xs) + 60))
    du = d(up["contours"])
    di = d(exaggerated(up["contours"], it["contours"])) if len(it["contours"]) == len(up["contours"]) else d(it["contours"], True)
    s.append('<clipPath id="c%d"><path d="%s"/></clipPath>' % (i, di))
    s.append('<path d="%s" fill="%s"/>' % (du, AWAY))
    s.append('<path d="%s" fill="%s"/>' % (di, ADDED))
    s.append('<path d="%s" fill="%s" clip-path="url(#c%d)"/>' % (du, BOTH, i))
    s.append('</g>')
    lab = UP[gl].get("unicode")
    ch = chr(int(lab, 16)) if lab else gl
    s.append('<text x="%d" y="%d" font-family="Menlo, monospace" font-size="52" fill="%s">%s</text>' % (60 + c * CELL_W + 20, base + 300, INK, ch.replace("&", "&amp;").replace("<", "&lt;")))
    s.append('<text x="%d" y="%d" font-family="Menlo, monospace" font-size="40" fill="%s">%s &#183; level %s</text>' % (60 + c * CELL_W + 20, base + 355, DIM, gl, LV[gl]))
s.append("</svg>")
open(out, "w").write("\n".join(s))
print(out)
