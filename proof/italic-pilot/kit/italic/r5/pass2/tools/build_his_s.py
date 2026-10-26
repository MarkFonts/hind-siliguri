"""Round 5 · pass 2, source change: the upright s is Mark's drawn ROMAN s (the newer drawing), anchor-free exactly as the
s round built it (r5/s/src/s_drawn.json, GeistSerifDrawnRoman_s: the least-squares merge of its two flat spine runs,
within 1.9 u of his drawing). Written into src/geistserif_italic_14.json and _18.json:

  GeistSerifRegular_s      his roman s in the set's frame: no scale (the PDF is read at 1000/170 u per pt for every
                           letter; his x-height overshoot 541 u = the Regular's), baseline 0 (drawn.base_fix), shifted in
                           x so that its INK left sidebearing equals the extracted Regular s's; advance 470 = the Regular's
  GeistSerifSlant_s        its plain slant x + K y
  GeistSerifRegularOld_s / GeistSerifSlantOld_s / GeistSerifItalicPass2Old_s   the extracted Regular s, its slant and
                           pass 2's correction of it, for the record
  GeistSerifItalicPass1_s  unchanged: pass 1 as delivered (made from the OLD s; the word sheets' pass-1 row)
  GeistSerifItalicPass1Rules_s   pass 1's own pipeline (r5/tools, round5.correct steps 1-6) run on HIS roman s at that
                           angle, by tools/pass1_on_his_s.py in its own process: the fair pass-1 column of the s score

build_his_s.py   (run once; then run_italic.py at both angles)
"""
import sys, os, json, copy, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import carry as C
import drawn

S_DRAWN = os.path.join(C.R5S, "src", "s_drawn.json")


def ink_x(cs):
    b = drawn.path(cs).computeTightBounds()
    return float(b.left()), float(b.right())


def main():
    his = json.load(open(S_DRAWN))["GeistSerifDrawnRoman_s"]
    rep = {}
    for tag, K in (("14", 0.25), ("18", 1.0 / 3.0)):
        p = os.path.join(C.R5, "src", "geistserif_italic_%s.json" % tag)
        G = json.load(open(p))
        old = G.get("GeistSerifRegularOld_s") or G["GeistSerifRegular_s"]
        if "GeistSerifRegularOld_s" not in G:
            G["GeistSerifRegularOld_s"] = copy.deepcopy(G["GeistSerifRegular_s"]); G["GeistSerifRegularOld_s"]["master"] = "Regular (extracted, old s)"
            G["GeistSerifSlantOld_s"] = copy.deepcopy(G["GeistSerifSlant_s"])
            if "GeistSerifItalic_s" in G:
                G["GeistSerifItalicPass2Old_s"] = copy.deepcopy(G["GeistSerifItalic_s"])
        lsb_old = ink_x(old["contours"])[0]; lsb_his = ink_x(his["contours"])[0]
        dx = lsb_old - lsb_his
        new = {"contours": drawn.shift(his["contours"], dx), "width": old["width"], "master": "Regular (Mark's drawn roman s, anchor-free)", "glyph": "s"}
        G["GeistSerifRegular_s"] = new
        G["GeistSerifSlant_s"] = {"contours": [{"closed": c["closed"], "nodes": [[n[0] + K * n[1], n[1]] + list(n[2:]) for n in c["nodes"]]} for c in new["contours"]],
                                  "width": old["width"], "master": "Slant", "glyph": "s"}
        G.pop("GeistSerifItalic_s", None)            # re-made by run_italic.py
        json.dump(G, open(p, "w"))
        l, r = ink_x(new["contours"]); lo, ro = ink_x(old["contours"])
        rep[tag] = dict(dx_from_s_round_frame=round(dx, 2), ink_lsb=round(l, 2), ink_rsb=round(new["width"] - r, 2),
                        old_ink_lsb=round(lo, 2), old_ink_rsb=round(old["width"] - ro, 2), width=new["width"],
                        nodes=sum(len(c["nodes"]) for c in new["contours"]),
                        xor_his_vs_old=round(drawn.xor_pct(new["contours"], old["contours"]), 2))
    # pass 1's pipeline on his s, in its own process (r5/tools has its own carry.py)
    subprocess.run([sys.executable, os.path.join(HERE, "pass1_on_his_s.py")], check=True)
    json.dump(rep, open(os.path.join(C.R5, "readings", "build_his_s.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
