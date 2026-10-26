"""Round 5 · s round: the pipeline for the s, on Mark's drawn roman s (anchor-free) as the upright.

  steps "1-3"   the skeleton only: I10 (rho 0.70), I11 (nu 0), I15 terminals ride, I16 rigid spine piece, I17 re-seat
  steps "1-5"   + the group rules I2-I8 with I13's targets (italicmove.py, I9 off); terminals are NOT held (I15)
  steps "1-6"   + the harmonizer last (harmonize_pass.py, round 5's two guards), on the joints the width rules touched

  correct5s(up, steps="1-6", terminal="a", psi=1.18, i16=True, i17=True, K=None) -> dict(contours, skeleton, mover, harmonize)
  r5_rules(up, K)       round 5's own pipeline (round5.correct, unchanged) on the same upright, for comparison
"""
import sys, os, math, copy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
import carry as C
from skeleton import check_same
from skeleton5s import Skeleton5s

# round 5 · s round's choices (NOTES): the drawing wins
TERMINAL = "a"
PSI = 1.23             # his node vectors, both spine edges (fit5s.py); score optimum 1.25-1.30
I17 = True               # on, but a node carried by I16 is never re-seated: on the s that is every side extreme
HOLD_TERMINALS = True


def slant_of(up, K):
    g = copy.deepcopy(up); g["master"] = "Slant"
    for c in g["contours"]:
        for n in c["nodes"]:
            n[0] = n[0] + K * n[1]
    return g


def correct5s(up, steps="1-6", terminal=TERMINAL, psi=PSI, i16=True, i17=I17, K=None, hold_terminals=HOLD_TERMINALS):
    from italicmove import ItalicMover
    K = C.K if K is None else K
    assert abs(K - C.K) < 1e-12, "set carry.set_slant first"
    sl = slant_of(up, K)
    IM0 = ItalicMover(sl, up)
    Sk = Skeleton5s(up, terminal=terminal, psi=psi, i16=i16, i17=i17, IM0=IM0)
    assert check_same(Sk.contours, up["contours"])
    out = dict(skeleton=Sk, mover=None, harmonize=None, contours=Sk.contours, base=Sk.contours)
    if steps == "1-3":
        return out
    base = {"contours": Sk.contours, "width": up["width"], "master": "Slant", "glyph": up["glyph"]}
    # I15 in the group rules: the terminal piece is final after the skeleton -- its own rungs ask nothing and a side's
    # group ends at it (hold_terminals=True); False lets the width rules core it (the comparison: NOTES)
    IM = ItalicMover(base, up, extra_held=Sk.terminal_nodes if hold_terminals else ())
    cs = [{"closed": c["closed"], "nodes": [[float(n[0]), float(n[1])] + list(n[2:]) for n in c["nodes"]]} for c in IM.contours_at(1.0)]
    assert check_same(cs, up["contours"])
    out.update(mover=IM, contours=cs)
    if steps == "1-5":
        return out
    from harmonize_pass import harmonize_pass
    hc, rep = harmonize_pass(up["glyph"], up, base, cs, IM)
    assert check_same(hc, up["contours"])
    out.update(contours=hc, harmonize=rep, before_harmonize=cs)
    return out


def r5_rules(up, steps="1-6"):
    from round5 import correct
    G = {"GeistSerifRegular_" + up["glyph"]: up, "GeistSerifSlant_" + up["glyph"]: slant_of(up, C.K)}
    return correct(up["glyph"], G, steps)
