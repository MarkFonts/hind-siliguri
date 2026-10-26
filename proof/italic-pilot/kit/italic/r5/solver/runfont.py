"""Run the existing pairing tools (partsheet, grid cell, readings) on another font without editing them.

runfont.py FONT                         FONT = marya | geistserif ; reads SCRATCH/src/FONT.json + FONT.masters.json
Writes out/sheets/FONT/<fname(key)>_parts.png, out/sheets/FONT/grid_<tag>.png, out/readings/FONT/*, out/sheets/FONT/summary.json
The slant passed to Parts is the master's italic angle from FONT.masters.json (the originals guess 18 deg from the word "Italic").
"""
import sys, os, json, traceback
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import parts, partsheet, grid, readings
from PIL import Image
from sheet import BG

_cur = {"slant": 0.0}
class PartsS(parts.Parts):
    def __init__(self, contours, slant=0.0):
        super().__init__(contours, slant=_cur["slant"])
for m in (partsheet, grid, readings):
    m.Parts = PartsS


def main(font):
    G = json.load(open(os.path.join(SCR, "src", font + ".json")))
    M = json.load(open(os.path.join(SCR, "src", font + ".masters.json")))
    sd = os.path.join(SCR, "out", "sheets", font); rd = os.path.join(SCR, "out", "readings", font)
    os.makedirs(sd, exist_ok=True); os.makedirs(rd, exist_ok=True)
    slant_of = lambda key: M[key.partition("_")[0]]["ia"]
    summary = []; index = []
    for key in sorted(G):
        _cur["slant"] = slant_of(key); g = G[key]
        row = {"key": key, "slant": _cur["slant"]}
        try:
            P = partsheet.partsheet(key, G, os.path.join(sd, partsheet.fname(key) + "_parts.png"))
            row.update(ok=True, strokes=len(P.strokes), flags=len(P.flags), unpaired=[int(u) if isinstance(u, int) else u for u in P.unpaired],
                       kinds={str(w): k for w, k in P.kind.items() if k != "side"})
        except Exception as e:
            row.update(ok=False, error=repr(e), trace=traceback.format_exc()[-500:])
        try:
            R = readings.readings(PartsS(g["contours"]), g["glyph"], g["master"])
            json.dump(R, open(os.path.join(rd, readings.fname(key) + ".readings.json"), "w"))
            kinds = {}
            for n in R["nodes"]: kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
            row["node_kinds"] = kinds
        except Exception as e:
            row["readings_error"] = repr(e)
        summary.append(row); print(row.get("key"), {k: v for k, v in row.items() if k not in ("key", "trace")})
    json.dump(summary, open(os.path.join(sd, "summary.json"), "w"), indent=1)
    json.dump(summary, open(os.path.join(rd, "index.json"), "w"), indent=1)
    # grids, one per master
    rows = [["f", "j", "H", "n", "a", "E", "T"], ["r", "v", "e", "y", "k", "x"]]
    CW, CH = 440, 480
    for tag in M:
        sheet = Image.new("RGB", (CW * 7 + 20, CH * 2 + 20), BG); n = 0
        for ri, r in enumerate(rows):
            for ci, gn in enumerate(r):
                key = "%s_%s" % (tag, gn)
                if key not in G: continue
                _cur["slant"] = M[tag]["ia"]
                try:
                    im, P = grid.cell(G[key], CW, CH); n += 1
                except Exception as e:
                    im = Image.new("RGB", (CW, CH), (40, 10, 10)); print("FAIL", key, repr(e))
                sheet.paste(im, (ci * CW + 10, ri * CH + 10))
        if n:
            sheet.save(os.path.join(sd, "grid_%s.png" % tag)); print("grid", tag, n, "cells")

if __name__ == "__main__":
    main(sys.argv[1])
