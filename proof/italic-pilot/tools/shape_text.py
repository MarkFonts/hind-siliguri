"""shape the two lines with uharfbuzz on the compiled TTFs (gfvenv python) -> work/text_shaped.json
(per font: glyph outlines as pen ops, positions in font units)"""
import os, json, uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
HERE = os.path.dirname(os.path.abspath(__file__)); PILOT = os.path.dirname(HERE); B = os.path.join(PILOT, "build")
LINES = ["সমস্ত মানুষ স্বাধীনভাবে সমান মর্যাদা এবং অধিকার নিয়ে জন্মগ্রহণ করে।", "The quick brown fox jumps over the lazy dog 0123456789"]
FONTS = {"Light": "upright/HindSiliguri-Light.ttf", "Light Italic": "italic/HindSiliguri-LightItalic.ttf",
         "Bold": "upright/HindSiliguri-Bold.ttf", "Bold Italic": "italic/HindSiliguri-BoldItalic.ttf"}

class Rec(BasePen):
    def __init__(self, gs): super().__init__(gs); self.ops = []
    def _moveTo(self, p): self.ops.append(["M", p])
    def _lineTo(self, p): self.ops.append(["L", p])
    def _curveToOne(self, a, b, c): self.ops.append(["C", a, b, c])
    def _qCurveToOne(self, a, b): self.ops.append(["Q", a, b])
    def _closePath(self): self.ops.append(["Z"])

out = {}
for nm, fn in FONTS.items():
    path = os.path.join(B, fn)
    blob = hb.Blob.from_file_path(path); face = hb.Face(blob); font = hb.Font(face)
    tt = TTFont(path); gs = tt.getGlyphSet(); order = tt.getGlyphOrder()
    res = {"lines": [], "glyphs": {}, "upm": tt["head"].unitsPerEm}
    for line in LINES:
        buf = hb.Buffer(); buf.add_str(line); buf.guess_segment_properties()
        hb.shape(font, buf, {})
        x = 0; items = []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            gn = order[info.codepoint]
            items.append([gn, x + pos.x_offset, pos.y_offset])
            x += pos.x_advance
            if gn not in res["glyphs"]:
                r = Rec(gs); gs[gn].draw(r); res["glyphs"][gn] = r.ops
        res["lines"].append({"text": line, "items": items, "advance": x})
    out[nm] = res
json.dump(out, open(os.path.join(PILOT, "work", "text_shaped.json"), "w"))
print({k: [l["advance"] for l in v["lines"]] for k, v in out.items()})
