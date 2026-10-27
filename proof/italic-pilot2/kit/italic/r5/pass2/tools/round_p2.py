"""Round 5 · pass 2: the pipeline for every letter, from the extracted Regular (src/geistserif_italic_<14|18>.json).

  steps "1-3"   the skeleton: I10 (rho 0.70), I11 (nu 0), I14 serifs by the stroke they end, I15 terminals ride (incl.
                stem-group stroke ends), I16 rigid spine piece (psi 1.23), I17 re-seat side extremes
  steps "1-5"   + the group rules I2-I8 with I13's targets (italicmove.py, I9 off); I15 pieces hold (extra_held)
  steps "1-6"   + the harmonizer last (harmonize_pass.py, round 5's two guards)

  correct(gl, G, steps="1-6", **choices) -> dict(contours, skeleton, mover, harmonize, before_harmonize)
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..", "solver"))
import carry as C
from skeleton import check_same
from skeleton_p2 import SkeletonP2

# pass 2's choices (NOTES): the s round's, plus the serif class and the I17 decision
TERMINAL = "a"          # leading terminal keeps the roman angle, trailing keeps the shear
PSI = 1.23              # his node vectors (s round)
SERIF = "arm"           # arm/bar serifs keep the shear, stem serifs keep the roman angle (T_E_serifs_18.png)
I17 = False             # decided by o p a (SCORE.md, sheets/I17_opa.png): the vertical target loses, the italic-angle one is split; NOTES
I17_TARGET = "italic"   # the tangent parallel to the italic angle; "vertical" = the s round's wording, rejected
STEM_ENDS = True
SERIF_JOINT = "junction"  # I14b: stem serif + brackets rigid roman, hung at the brackets' junction height (pass 2b); "slab" = pass 2a
SIDE_HANDLES = False    # tested: giving the side handles the side's lean breaks G1 at the terminal's smooth end nodes (2 snaps); off
SPINE_G2 = "roman"      # I16 (pass 2b): the bowl arc meets the spine and the bowl curve at the ROMAN's curvature ratios (re-aim <= 3 deg); "fair" = pass 2a
PULL_K = 0.0            # I15 pull-in tested at k 0 / 0.5 / 1 (s_pullin_18.png): k 0 wins (it hurts the 14.04 deg score and balloons the arc)


def slant_of_source(up, sl):
    """K of a Slant key against its Regular (x' = x + K y), snapped to 1/4 or 1/3 when within 1e-3"""
    import numpy as np
    ks = [(b[0] - a[0]) / a[1] for ca, cb in zip(up["contours"], sl["contours"]) for a, b in zip(ca["nodes"], cb["nodes"]) if abs(a[1]) > 100]
    k = float(np.median(ks))
    for s in (0.25, 1.0 / 3.0):
        if abs(k - s) < 1e-3:
            return s
    return k


def correct(gl, G, steps="1-6", terminal=None, psi=None, serif=None, i17=None, i16=True, stem_ends=None, i17_target=None, side_handles=None, pull_k=None, spine_g2=None, serif_joint=None, rho=None, nu_coef=None, post=None, terminal_narrow=False, hold_brackets=False):
    from italicmove import ItalicMover
    terminal = TERMINAL if terminal is None else terminal; psi = PSI if psi is None else psi
    serif = SERIF if serif is None else serif; i17 = I17 if i17 is None else i17
    stem_ends = STEM_ENDS if stem_ends is None else stem_ends
    i17_target = I17_TARGET if i17_target is None else i17_target
    side_handles = SIDE_HANDLES if side_handles is None else side_handles; pull_k = PULL_K if pull_k is None else pull_k
    spine_g2 = SPINE_G2 if spine_g2 is None else spine_g2
    serif_joint = SERIF_JOINT if serif_joint is None else serif_joint
    up = G["GeistSerifRegular_" + gl]; sl = G["GeistSerifSlant_" + gl]
    # the slant K is read from the source itself (Slant = Regular sheared): calling correct() on the _14 file with
    # carry's default K (1/3) silently ran the 18.43 deg rules on 14.04 deg inputs (the coordinator's 50 u / 45 % XOR)
    k = slant_of_source(up, sl)
    if abs(k - C.K) > 1e-4:
        import sys as _s
        print("round_p2.correct: the source is sheared by K = %.4f, carry had %.4f: set_slant(%.4f)" % (k, C.K, k), file=_s.stderr)
        C.set_slant(k)
    IM0 = ItalicMover(sl, up)
    Sk = SkeletonP2(up, serif=serif, terminal=terminal, psi=psi, i16=i16, i17=i17, stem_ends=stem_ends, i17_target=i17_target, side_handles=side_handles, pull_k=pull_k, spine_g2=spine_g2, serif_joint=serif_joint, post=post, terminal_narrow=terminal_narrow, IM0=IM0,
                    **({} if rho is None else dict(rho=rho)), **({} if nu_coef is None else dict(nu_coef=nu_coef)))
    assert check_same(Sk.contours, up["contours"]), gl
    out = dict(skeleton=Sk, mover=None, harmonize=None, contours=Sk.contours, base=Sk.contours)
    if steps == "1-3":
        return out
    base = {"contours": Sk.contours, "width": up["width"], "master": "Slant", "glyph": gl}
    held = set(Sk.terminal_nodes)
    if hold_brackets:
        # pass 2c: a sheared serif's bracket ends where it meets the stem; that junction node holds in the group rules,
        # so the bracket stays the plain slant's (a group moving it turned the bracket's chord under fixed tangents)
        U = Sk.U
        for nd in Sk.held:
            for sg in (U.seg_before[nd], U.seg_after[nd]):
                other = sg["gi"] if sg["gj"] == nd else sg["gj"]
                if sg["kind"] == "curve" and other not in Sk.held:
                    held.add(other)
    IM = ItalicMover(base, up, extra_held=held)
    cs = [{"closed": c["closed"], "nodes": [[float(n[0]), float(n[1])] + list(n[2:]) for n in c["nodes"]]} for c in IM.contours_at(1.0)]
    assert check_same(cs, up["contours"]), gl
    out.update(mover=IM, contours=cs)
    if steps == "1-5":
        return out
    from harmonize_pass import harmonize_pass
    hc, rep = harmonize_pass(gl, up, base, cs, IM)
    assert check_same(hc, up["contours"]), gl
    out.update(contours=hc, harmonize=rep, before_harmonize=cs)
    return out
