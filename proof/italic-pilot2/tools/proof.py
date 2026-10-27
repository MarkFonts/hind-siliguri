"""the proof sheets: side by side (upright | raw slant | corrected), overlays (raw slant vs corrected), class map"""
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from sheets import *
PILOT = os.path.dirname(HERE); W = os.path.join(PILOT, "work"); OUT = os.path.join(PILOT, "sheets")
K = 0.25; YC = 253.5
LAT = "n o e a s g B R O S ampersand three eight".split()
BN = ("bnA bnAA bnI bnU bnE bnO bnKA bnKHA bnGA bnGHA bnCA bnJA bnTTA bnDDA bnNNA bnTA bnDA bnNA bnPA bnBA bnMA bnYA bnRA bnLA "
      "bnSHA bnSA bnHA bnK_SSA bnJ_NYA bnN_TA bnS_TA bnZero bnOne bnTwo bnThree bnFour bnFive bnSix bnSeven bnEight bnNine").split()
UP = {m: json.load(open(os.path.join(W, "upright_%s.json" % m))) for m in ("Light", "Bold")}
IT = {m: json.load(open(os.path.join(W, "italic_%s.json" % m))) for m in ("Light", "Bold")}
LEVEL = json.load(open(os.path.join(W, "levels.json")))
LEVEL_C = {"A": GREEN, "B": (250, 200, 70), "C": (250, 150, 60), "D": RED, "composite": (120, 170, 255)}
LEVEL_C["mixed"] = (200, 160, 255)
LEVEL_T = {"mixed": "per-master level (Light/Bold)", "A": "A full ruleset", "B": "B re-tension off", "C": "C + terminals sheared, no spine", "D": "D plain slant (gate failed)", "composite": "composite"}


def shear(cs, dx=0.0):
    return [{"closed": c["closed"], "nodes": [[n[0] + K * (n[1] - YC) + dx, n[1]] + list(n[2:]) for n in c["nodes"]]} for c in cs]


def move(cs, dx, dy):
    return [{"closed": c["closed"], "nodes": [[n[0] + dx, n[1] + dy] + list(n[2:]) for n in c["nodes"]]} for c in cs]


def resolve(m, gl, which, depth=0):
    g = UP[m][gl]
    if which == "up": cs = g["contours"]
    elif which == "slant": cs = shear(g["contours"])
    else: cs = IT[m][gl]["contours"]
    out = list(cs)
    for c in g["components"]:
        t = c["transform"]; dx, dy = t[4], t[5]
        sub = resolve(m, c["name"], which, depth + 1)
        out += move(sub, dx + (K * dy if which != "up" else 0.0), dy)
    return out


def char_of(gl):
    u = UP["Light"][gl]["unicodes"]
    return chr(int(u[0], 16)) if u else ""


def label(sh, x, y, gl, size=15):
    ch = char_of(gl)
    w = sh.text(x, y, gl, INK, size)
    if ch and gl.startswith("bn"):
        sh.text(x + w + 8, y - 4, ch, INK, size + 6, face=BANGLA)
    lv = LEVEL[gl]
    if lv.startswith("mixed"):
        sh.text(x, y + size + 6, "level Light/Bold " + lv.split()[1], (200, 160, 255), size); return
    sh.text(x, y + size + 6, ("level " + lv) if lv != "composite" else "composite", LEVEL_C[lv], size)


def side_by_side(master, glyphs, name, title):
    s = 0.13; maxw = max(UP[master][g]["width"] for g in glyphs); sp = max(maxw * 1.1 * s + 25, 1000 * s * 0.9)
    tw = 3 * sp + 20; cols = 2 if maxw > 1000 else 3
    rows = math.ceil(len(glyphs) / cols)
    rh = 250
    sh = Sheet(int(60 + cols * (tw + 60)), 230 + rows * rh)
    sh.header("HIND SILIGURI", master + " Italic", "%s · upright | raw slant 14.04° | corrected — solid fills" % title,
              "corrected = round 5 pass 2c structure with Hind's numbers; the letter under each name says which level shipped")
    x = sh.key(30, 150, [("upright", UP_C), ("raw slant", SL_C), ("corrected", IT_C)])
    sh.key(x + 20, 150, [(LEVEL_T[k], LEVEL_C[k]) for k in ("A", "B", "C", "D", "mixed")], 15)
    for i, gl in enumerate(glyphs):
        r, c = divmod(i, cols)
        x0 = 40 + c * (tw + 60); y0 = 230 + r * rh
        label(sh, x0, y0, gl)
        base = y0 + 200
        for k, (which, colr) in enumerate((("up", UP_C), ("slant", SL_C), ("it", IT_C))):
            sh.glyph(resolve(master, gl, which), x0 + 10 + k * sp, base, s, colr)
        sh.hline(x0, x0 + 3 * sp + 10, base)
    return sh.save(os.path.join(OUT, "side_%s_%s.png" % (name, master)))


def overlays(master, glyphs, name, title):
    s = 0.22; cw = 260; cols = 8 if name == "bangla" else 7
    rows = math.ceil(len(glyphs) / cols); rh = 300
    wide = max(UP[master][g]["width"] for g in glyphs) * s
    cw = max(cw, int(wide + 40))
    sh = Sheet(60 + cols * cw, 230 + rows * rh)
    sh.header("HIND SILIGURI", master + " Italic", "%s · overlay: raw slant vs corrected (solid)" % title,
              "grey = in both, red = taken away from the raw slant, green = added; the corrected thickness changes are the colored slivers")
    sh.key(30, 150, [("in both", GREY), ("taken away", RED), ("added", GREEN)])
    for i, gl in enumerate(glyphs):
        r, c = divmod(i, cols)
        x0 = 40 + c * cw; y0 = 220 + r * rh
        label(sh, x0, y0, gl, 14)
        base = y0 + 240
        sh.overlay(resolve(master, gl, "slant"), resolve(master, gl, "it"), x0 + 10, base, s)
    return sh.save(os.path.join(OUT, "overlay_%s_%s.png" % (name, master)))


if __name__ == "__main__":
    for m in ("Light", "Bold"):
        print(side_by_side(m, LAT, "latin", "Latin")); print(side_by_side(m, BN, "bangla", "Bangla"))
        print(overlays(m, LAT, "latin", "Latin")); print(overlays(m, BN, "bangla", "Bangla"))
