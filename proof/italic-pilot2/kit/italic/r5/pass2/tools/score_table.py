"""The score table at 14.04 deg against Mark's drawn italic: XOR % per letter for the plain slant, round 4, round 5
steps 1-3, 1-5, 1-6; bowl widths (the ink's horizontal extent at each round part's centre height); rho nu psi fitted vs
used. Writes readings/score_table.json (for sheets5.py table -> sheets/score_table.png) and ../SCORE.md.

score_table.py
"""
import sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
C.set_slant(0.25)
import drawn
from round5 import correct
import skeleton as SK

LET = ["o", "p", "s", "a"]          # scored (Mark's finished drawings)
UNF = ["e", "n"]                    # unfinished drawings: reference row only


def extent_at(cs, y):
    b = drawn.box_of(cs, pad=4); M = drawn.mask(cs, b, ppu=4.0)
    r = int(round((b[3] - y) * 4.0))
    xs = np.nonzero(M[r])[0]
    return float((xs.max() - xs.min() + 1) / 4.0) if len(xs) else float("nan")


def bowl_heights(gl, G):
    Sk = SK.Skeleton(G["GeistSerifRegular_" + gl])
    outs = [r for r in Sk.runs if not r["counter"]]
    if gl == "s":
        lo = min(outs, key=lambda r: r["c"][1]); hi = max(outs, key=lambda r: r["c"][1])
        return [("s upper", hi["c"][1]), ("s lower", lo["c"][1])]
    if gl == "a":
        r = min(outs, key=lambda r: r["c"][1]); return [("a bowl", r["c"][1])]
    r = max(outs, key=lambda r: r["W"]); return [("%s bowl" % gl if gl != "o" else "o", r["c"][1])]


def main():
    G = C.load(); R4 = json.load(open(os.path.join(C.R5, "src", "geistserif_italic.json")))
    X = {}; Wd = {}
    for gl in LET + UNF:
        sl = G["GeistSerifSlant_" + gl]["contours"]
        D = drawn.letter(gl, "italic", sl)["contours"]
        up = G["GeistSerifRegular_s.anchors" if gl == "s" else "GeistSerifRegular_" + gl]["contours"]
        floor = drawn.xor_pct(up, drawn.letter(gl, "roman", up)["contours"])
        cand = dict(slant=sl, r4=R4["GeistSerifItalic_" + gl]["contours"], s13=correct(gl, G, "1-3")["contours"],
                    s15=correct(gl, G, "1-5")["contours"], s16=correct(gl, G, "1-6")["contours"])
        X[gl] = {k: round(drawn.xor_pct(v, D), 2) for k, v in cand.items()}; X[gl]["floor"] = round(floor, 2)
        if gl in LET:
            for name, y in bowl_heights(gl, G):
                Wd[name] = dict(y=round(y), drawn=round(extent_at(D, y), 1), **{k: round(extent_at(v, y), 1) for k, v in cand.items()},
                                roman=round(extent_at(G["GeistSerifRegular_" + gl]["contours"], y), 1))
    fp = json.load(open(os.path.join(C.R5, "readings", "fit_params.json")))
    sj = json.load(open(os.path.join(C.R5, "readings", "scan_joint.json")))
    sm = fp["summary"]
    params = [
        ("rho (round lean)", "0.6", "o %.2f · p bowl %.2f · a bowl %.2f" % (fp["parts"]["o (model)"]["rho"], fp["parts"]["p bowl (model)"]["rho"], fp["parts"]["a bowl (model)"]["rho"]),
         "0.70 (o 0.70, p 0.80, a 0.60, s 0.40 alone)", "%.2f" % SK.RHO),
        ("nu (bowl narrowing)", "0.6 tanθ = 15 % at 14°", "o %+.1f %% · p bowl %+.1f %% · a bowl %+.1f %%" % (100 * fp["parts"]["o (model)"]["nu"], 100 * fp["parts"]["p bowl (model)"]["nu"], 100 * fp["parts"]["a bowl (model)"]["nu"]),
         "0 (o alone 0.05 tanθ = 1.3 %, p alone −0.05 tanθ)", "%.2f tanθ = %.1f %%" % (SK.NU_COEF, 100 * SK.NU_COEF * 0.25)),
        ("psi (spine turn)", "0.75", "spine tangent at the inflection: %.2f" % sm["psi"], "0.80 (s)", "%.2f" % SK.PSI),
    ]
    T = dict(xor=X, widths=Wd, params=params)
    cols = ["letter", "slant", "round 4", "r5 1-3", "r5 1-5", "r5 1-6", "floor"]
    rows = []
    for gl in LET:
        x = X[gl]; rows.append(dict(cells=["/" + gl, x["slant"], x["r4"], x["s13"], x["s15"], x["s16"], x["floor"]]))
    m = lambda k: round(float(np.mean([X[g][k] for g in LET])), 2)
    rows.append(dict(cells=["mean o p s a", m("slant"), m("r4"), m("s13"), m("s15"), m("s16"), m("floor")]))
    for gl in UNF:
        x = X[gl]; rows.append(dict(cells=["/%s UNFINISHED" % gl, x["slant"], x["r4"], x["s13"], x["s15"], x["s16"], x["floor"]], dim=True))
    notes = ["floor = Mark's drawn ROMAN against our JSON Regular: his s is a later drawing (11.8 %), so no s score can go far below it",
             "e, n UNFINISHED (Mark, 2026-10-25): his italic e and n are still plain slants; reference only, not in the mean, no fit",
             "rho 0.70 · nu 0 · psi 0.80, fitted by score on o p s a (study: 0.6 · 0.6 tanθ · 0.75); node-level fits in SCORE.md"]
    T["rows"] = rows; T["cols"] = cols; T["notes"] = notes
    json.dump(T, open(os.path.join(C.R5, "readings", "score_table.json"), "w"), indent=1)
    # SCORE.md
    L = ["# Round 5 score: Geist Serif Regular → Italic at 14.04° against Mark's drawn italic", "",
         "Mark's drawn s a o p n e (Glyphs print `new_italics.pdf`, 2026-10-25, 170 pt; `src/mark_saopne_pdf_paths.json`) are at "
         "14.04° (x + y/4), so round 5 is run at 14.04° (`--slant 1/4`) to be scored and at 18.43° (x + y/3) as the deliverable — "
         "same rules, same parameters, only K differs.", "",
         "**XOR %** = area of (candidate △ drawing) / area of the drawing, at 2 px/u, nonzero fill. Lower = closer. The drawing is "
         "put in the solver's frame by its stems (p, n, a: XOR optimum inside a stem band), by its held terminal corners (s, as "
         "`mark_vectors.py`), or by its centre at mid-height (o, e: a round part's centre stays where the shear puts it) — never "
         "by its bbox. The PDF's italic baseline sits 4.0 u high (the n's and p's feet read +4); it is corrected.", "",
         "**e and n are UNFINISHED** (Mark, 2026-10-25: he forgot to fix them; both are plain slants within 0.6–1.6 %). Their row is "
         "reference only: no parameter is fitted from them and they are not in the mean or the conclusions.", "",
         "| letter | plain slant | round 4 | round 5 steps 1–3 | round 5 steps 1–5 | round 5 steps 1–6 | floor (drawn roman vs ours) |",
         "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append("| " + " | ".join(("**%s**" % c if i == 0 and not r.get("dim") else str(c)) for i, c in enumerate(r["cells"])) + " |")
    L += ["", "Steps: 1–3 = the skeleton only (I10 two-angle shear, I11 narrowing at ν = 0, I12 rigid spine); 1–5 = + I14 (cuts at the "
          "roman angle) + the width rules I2–I8 with I13 (re-tension on); 1–6 = + the harmonizer.", "",
          "## Bowl widths (u): the ink's horizontal extent at the part's centre height", "",
          "| part | y | roman | drawn italic | slant | round 4 | r5 1–3 | r5 1–6 |", "|---|---|---|---|---|---|---|---|"]
    for k, v in Wd.items():
        L.append("| %s | %d | %.1f | %.1f | %.1f | %.1f | %.1f | %.1f |" % (k, v["y"], v["roman"], v["drawn"], v["slant"], v["r4"], v["s13"], v["s16"]))
    L += ["", "## Parameters: study default · fitted from Mark's drawings · used", "",
          "| parameter | study default | node-level fit (his roman → his italic, `fit_params.py`) | fit by score (`scan_params.py`, o p s a) | used |",
          "|---|---|---|---|---|"]
    for p in params:
        L.append("| " + " | ".join(p) + " |")
    L += ["", "The drawing wins for Geist Serif: ν = 0 contradicts the study's 0.6·tanθ (15 % at 14°, 20 % at 18.43°) — Mark does not "
          "narrow his bowls (the o loses 1.3 % of its outer width, the p's bowl gains 1.4 %). ρ = 0.70 sits between the study's "
          "0.6 and his o/p node fits (0.80/0.85); his a's bowl stands almost upright (ρ 0.15, a contradiction, NOTES). ψ: the "
          "drawn spine's own tangent turns 1.18 θ, the whole-letter score prefers 0.80 with our (older) s drawing.", ""]
    open(os.path.join(C.R5, "SCORE.md"), "w").write("\n".join(L) + "\n")
    print(json.dumps(dict(xor=X, widths=Wd), indent=1))


if __name__ == "__main__":
    main()
