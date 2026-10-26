"""Round 5's pipeline, one letter at a time (K from carry.set_slant):

  steps "1-3"   the skeleton field only: I10 two-angle shear, I11 bowl narrowing, I12 rigid spine (skeleton.py)
  steps "1-5"   + I14 (cuts keep the roman angle) in the skeleton, then the group rules I2-I8 with I13's targets
                (italicmove.py, I9 off) correct the widths on that base
  steps "1-6"   + the harmonizer (wmparts/harmonize.py, mode "auto", re-aim, the joints the width rules touched, target =
                the skeleton base's curvature ratios, R23 guard) last

  correct(gl, G, steps) -> dict(contours, skeleton, mover, harmonize)
"""
import sys, os, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
import carry as C
from skeleton import Skeleton, check_same, RHO, NU_COEF, PSI

STEPS = ("1-3", "1-5", "1-6")


def rules_for(steps):
    return ("I10", "I11", "I12") if steps == "1-3" else ("I10", "I11", "I12", "I14")


def correct(gl, G, steps="1-6", rho=RHO, nu_coef=NU_COEF, psi=PSI, rules=None):
    from italicmove import ItalicMover
    up = G["GeistSerifRegular_" + gl]; sl = G["GeistSerifSlant_" + gl]
    IM0 = ItalicMover(sl, up)                       # the classes, read on the plain slant (I1: the upright's pairing)
    Sk = Skeleton(up, rules=rules or rules_for(steps), rho=rho, nu_coef=nu_coef, psi=psi, IM0=IM0)
    out = dict(skeleton=Sk, mover=None, harmonize=None, contours=Sk.contours)
    if steps == "1-3":
        return out
    base = {"contours": Sk.contours, "width": up["width"], "master": "Slant", "glyph": gl}
    IM = ItalicMover(base, up, extra_held=Sk.terminal_nodes)     # I14: a rigid terminal holds
    cs = [{"closed": c["closed"], "nodes": [[float(n[0]), float(n[1])] + list(n[2:]) for n in c["nodes"]]} for c in IM.contours_at(1.0)]
    assert check_same(cs, up["contours"]), gl
    out.update(mover=IM, contours=cs)
    if steps == "1-5":
        return out
    from harmonize_pass import harmonize_pass
    hc, rep = harmonize_pass(gl, up, base, cs, IM)
    assert check_same(hc, up["contours"]), gl
    out.update(contours=hc, harmonize=rep)
    return out
