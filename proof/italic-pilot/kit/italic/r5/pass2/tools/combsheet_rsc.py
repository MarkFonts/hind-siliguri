"""Curvature combs of one letter in its three states: ROMAN (upright) | plain slant | corrected, one scale for all
three (the roman's 95th-percentile curvature), every curve coloured. The roman's comb is the reference the italic's
should resemble (Mark, 2026-10-25: "show me your comb illustration on roman Geist Serif s").

combsheet_rsc.py LETTER [LETTER ...] [--out DIR]
"""
import sys, os, json, argparse
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "solver")); sys.path.insert(0, HERE)
import curvcomb as cc
from sheet import Panel, BG, SS, font, MENLO
from rungs import Outline
from readings import fname

SRC = os.path.join(HERE, "..", "src", "geistserif_italic.json")


def node_numbers(A, contours):
    f = font(MENLO, 9); gi = 0
    for c in contours:
        for n in c["nodes"]:
            if n[2] != "o":
                X, Y = A.pt((n[0], n[1])); r = 2.2 * SS
                A.d.rectangle([X - r, Y - r, X + r, Y + r], fill=(232, 232, 232))
                A.d.text((X + 4 * SS, Y + 1 * SS), str(gi), fill=(232, 184, 74), font=f)
            gi += 1


def sheet(gl, out):
    G = json.load(open(SRC))
    states = [("roman (upright)", G["GeistSerifRegular_" + gl]["contours"]),
              ("plain slant 14.04°", G["GeistSerifSlant_" + gl]["contours"]),
              ("corrected (ItalicMover)", G["GeistSerifItalic_" + gl]["contours"])]
    S0, K0, _, _ = cc.analyse(states[0][1])
    allk = np.concatenate([np.abs(p["k"][~np.isnan(p["k"])]) for p in K0 if p is not None])
    scale = max(float(np.percentile(allk, 95)), 1e-4)
    kgain, Lmax = 40.0 / scale, 130.0
    pts = [p for _, c in states for p in cc.flat(c)]
    bb = (min(p[0] for p in pts) - 110, min(p[1] for p in pts) - 110, max(p[0] for p in pts) + 110, max(p[1] for p in pts) + 110)
    PW, PH = 900, 900
    ims = []
    for title, c in states:
        A = Panel(PW, PH, bb, margin=40)
        A.fill_outline(Outline(c), color=(40, 48, 34), edge=(120, 120, 120))
        segs = cc.segments(c)
        cc.comb(A, c, [True] * len(segs), scale, kgain, Lmax)
        node_numbers(A, c)
        A.d.rectangle([0, 0, A.im.width, 46 * SS], fill=BG)
        A.title("/%s · %s" % (gl, title), "comb = curvature, one scale for all three (roman 95th pct |k| = 1/%.0f u)" % (1 / scale))
        ims.append(A.out())
    im = Image.new("RGB", (PW * 3 + 20, PH), BG)
    for i, p in enumerate(ims):
        im.paste(p, (i * (PW + 10), 0))
    im.save(out); print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("letters", nargs="+")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "sheets", "curv"))
    a = ap.parse_args()
    for gl in a.letters:
        sheet(gl, os.path.join(a.out, fname("X_" + gl)[2:] + "_roman_slant_corrected.png"))
