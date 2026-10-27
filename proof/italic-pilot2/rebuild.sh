#!/bin/zsh
# Pilot 2, end to end: solver (levels A, B, C) -> italic UFOs -> italic VF -> overlay SVGs -> roman-over-italic specimen PDF.
set -e
HERE=${0:A:h}
PY=/usr/local/bin/python3                      # skia + numpy, for the solver
GF=/private/tmp/claude-502/-Users-Mark-Documents-Github/409ac272-e6e0-4109-afcb-acdd1a1f6929/scratchpad/gfvenv/bin
ROMAN=/private/tmp/claude-502/-Users-Mark-Documents-Github/409ac272-e6e0-4109-afcb-acdd1a1f6929/scratchpad/spec/HindSiliguri-Roman-VF.ttf
cd $HERE/tools
rm -f ../work/results*.json
$PY run_all.py && $PY run_all.py --no-retension && $PY run_all.py --simple
cd $HERE
$GF/python tools/build_ufos.py | tail -1
$GF/fontmake -m HindSiliguri-Italic.designspace -o variable --output-path build/italic_vf/HindSiliguri-Italic-VF.ttf > build/fontmake_vf.log 2>&1
python3 - <<'EOF'
import json, subprocess
U = json.load(open("work/upright_Bold.json")); cm = {g["unicode"]: k for k, g in U.items() if g.get("unicode") and U[k]["contours"]}
names = lambda s: ",".join(cm["%04X" % ord(ch)] for ch in s if "%04X" % ord(ch) in cm)
sets = {"lc": "abcdefghijklmnopqrstuvwxyz", "uc": "ABCDEGKMOPQRSVWXZ0235689", "bn": "অআইউএওকখগঘঙচজঞটঠডতথদধনপফবভমযরলশষসহ০১২৩৫৬"}
for m in ("Light", "Bold"):
    for k, v in sets.items():
        for x in ("1", "4"):
            subprocess.run(["python3", "tools/overlay_svg.py", m, names(v), "sheets/overlay_%s_%s%s.svg" % (k, m, "" if x == "1" else "_x4"),
                            "9" if k != "bn" else "10", x], check=True, capture_output=True)
EOF
cd ../specimen && python3 build.py $ROMAN ../italic-pilot2/build/italic_vf/HindSiliguri-Italic-VF.ttf "pilot 2 · 14.04° · Frutiger rules" pilot2
echo PILOT2-REBUILD-DONE
