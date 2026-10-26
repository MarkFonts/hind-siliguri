"""Round 5 · pass 2: the score table (readings/score_p2.json, written by score_p2.py) -> readings/score_table_p2.json
(for sheets_p2.py table -> sheets/score_table.png) and ../SCORE.md.
"""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C

FIT = ["s", "a", "o", "p"]
UNF = ["e", "n"]
KEYS = ["slant", "p1", "p2_noI17", "p2_I17v", "p2_I17"]
COLS = ["letter", "plain slant", "pass 1", "pass 2 (−I17)", "+I17 vertical", "+I17 italic"]


def main():
    S = json.load(open(os.path.join(C.R5, "readings", "score_p2.json")))
    rows = []
    for g in FIT:
        rows.append(dict(cells=["/" + g + (" (his roman)" if g == "s" else "")] + ["%.1f" % S[g]["xor"][k] for k in KEYS]))
    m = {k: float(np.mean([S[g]["xor"][k] for g in FIT])) for k in KEYS}
    rows.append(dict(cells=["mean s a o p"] + ["%.1f" % m[k] for k in KEYS], bold=True))
    m3 = {k: float(np.mean([S[g]["xor"][k] for g in ("a", "o", "p")])) for k in KEYS}
    rows.append(dict(cells=["mean a o p"] + ["%.1f" % m3[k] for k in KEYS]))
    for g in UNF:
        rows.append(dict(cells=["/%s UNFINISHED" % g] + ["%.1f" % S[g]["xor"][k] for k in KEYS], dim=True))
    notes = ["pass 2 = I10 I11 I13, I14 for stem serifs, arm serifs sheared, I15 terminals ride, I16 rigid spine (psi 1.23), harmonizer; shipped with I17 OFF",
             "+I17 vertical = the s round's I17 (re-seat to the TRUE vertical tangent); +I17 italic = re-seat to the tangent at the italic angle",
             "s: SOURCE CHANGE: the upright s is Mark's drawn roman s (anchor-free, %.1f %% from his drawing: no floor); pass 1 = pass 1's rules on it" % S["s"]["floor"],
             "e, n UNFINISHED (Mark, 2026-10-25): reference only, not in the means, no fit"]
    T = dict(cols=COLS, rows=rows, notes=notes, means=m, means_aop=m3)
    json.dump(T, open(os.path.join(C.R5, "readings", "score_table_p2.json"), "w"), indent=1)
    s = S["s"]
    L = ["# Round 5 · pass 2: score", "",
         "Geist Serif at 14.04° (x' = x + y/4) against Mark's drawn italic s a o p (`italic/src/mark_saopne_pdf_paths.json`). The upright "
         "is the extracted Geist Serif Regular for every column (pass 1 and pass 2 alike), EXCEPT the s: **source change** — the upright s "
         "is Mark's drawn roman s, anchor-free as the s round built it (`tools/build_his_s.py`), and the s's pass-1 column is pass 1's "
         "pipeline run on it. The s row has no floor (his anchor-free roman is %.1f %% from his drawn roman)." % S["s"]["floor"], "",
         "**XOR %** = area(candidate △ drawing) / area(drawing), 2 px/u, nonzero fill. Lower is closer. Placement of his drawing, the "
         "same for every column of a letter: o and e by the centre at mid-height, p n a by the stems, s by ink centroid on the plain "
         "slant's (the s round's rule; pass 1 placed the s by its held terminal corners, numbers below).", "",
         "| letter | plain slant | pass 1 | **pass 2, shipped (I17 off)** | pass 2 + I17 to the vertical tangent (s round) | pass 2 + I17 to the italic-angle tangent |",
         "|---|---|---|---|---|---|"]
    for r in rows:
        c = r["cells"]
        L.append("| %s | %s | %s | **%s** | %s | %s |" % tuple(c))
    L += ["", "Skeleton only (steps 1–3), I17 off / vertical / italic:", ""]
    for g in FIT + UNF:
        x = S[g]["xor"]
        L.append("- /%s%s: %.2f / %.2f / %.2f" % (g, " (unfinished)" if g in UNF else "", x["p2_13_noI17"], x["p2_13_I17v"], x["p2_13_I17"]))
    L += ["", "The s with pass 1's placement (held terminal corners): slant %.2f, pass 1's rules %.2f, pass 2 %.2f." % (
          s["corners_placement"]["slant"], s["corners_placement"]["p1"], s["corners_placement"]["p2_noI17"]), ""]
    np_ = os.path.join(C.R5, "readings", "score_notes.md")          # the hand-written notes under the table
    open(os.path.join(C.R5, "SCORE.md"), "w").write("\n".join(L) + "\n" + (open(np_).read() if os.path.exists(np_) else ""))
    print("\n".join(L))


if __name__ == "__main__":
    main()
