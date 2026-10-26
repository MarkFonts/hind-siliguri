"""Compare the new Hind Siliguri build against the 2015 OTFs and the Google Fonts TTFs.

usage: compare.py NEW_DIR OLD_2015_DIR GF_DIR OUT_JSON
e.g.   compare.py intermediates/products/HindSiliguri-1.002-OTF legacy/build-2015 proof/fonts/gf report.json
"""
import sys, json, collections
from fontTools.ttLib import TTFont
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import BoundsPen
import uharfbuzz as hb

NEW, OLD, GF, OUT = sys.argv[1:5]
WEIGHTS = ["Light", "Regular", "Medium", "SemiBold", "Bold"]

def corpus():
    C = [chr(c) for c in range(0x0995, 0x09BA) if c not in (0x09A9, 0x09B1, 0x09B3, 0x09B4, 0x09B5)]
    C += ["ড়", "ঢ়", "য়", "ৎ"]
    V = [chr(c) for c in range(0x0985, 0x0995) if c not in (0x098D, 0x098E, 0x0991, 0x0992)] + ["ৠ", "ৡ"]
    M = [chr(c) for c in range(0x09BE, 0x09CD) if c not in (0x09C5, 0x09C6, 0x09C9, 0x09CA)] + ["ৗ", "ৢ", "ৣ"]
    S = ["ঁ", "ং", "ঃ"]
    H = "্"
    out = []
    out += V + C
    out += [c + m for c in C for m in M]
    out += [c + s for c in C for s in S]
    out += [c + "ি" + s for c in C for s in S]
    out += [c + H + d for c in C for d in C]
    out += [c + H + d + m for c in C for d in C[:12] for m in ("ি", "ু", "ে", "ো")]
    out += ["র" + H + c for c in C]
    out += ["র" + H + c + m for c in C for m in M]
    out += ["র" + H + c + m + "ঁ" for c in C for m in ("া", "ি", "ী", "ৌ")]
    out += [c + H + "য" for c in C]
    out += [c + H + "য" + m for c in C for m in M]
    out += [c + H + "র" for c in C]
    out += [c + H + "র" + m for c in C for m in M]
    out += [c + H + "ব" for c in C]
    out += [c + H + d + H + e for c, d, e in [
        ("স", "ত", "র"), ("ক", "ষ", "ণ"), ("ন", "ত", "র"),
        ("ম", "প", "র"), ("স", "প", "র"), ("জ", "ঞ", "য")]]
    out += [chr(c) for c in range(0x09E6, 0x09F0)] + ["০১২৩৪৫৬৭৮৯", "৳", "৲", "৺"]
    out += ["সমস্ত মানুষ স্বাধীনভাবে সমান মর্যাদা এবং অধিকার নিয়ে জন্মগ্রহণ করে।",
            "আমার সোনার বাংলা, আমি তোমায় ভালোবাসি।", "কার্ত্তিক র‍্যাব র্‍যাব ক্ষ্ম জ্ঞ হ্ম ঙ্ক্ষ"]
    out += [chr(c) for c in range(0x21, 0x7F)]
    out += ["The quick brown fox jumps over the lazy dog.", "Ångström façade naïve œuvre — “quotes” 1,234.56 €"]
    return list(dict.fromkeys(out))

def glyph_stats(font):
    gs = font.getGlyphSet()
    stats = {}
    for name in font.getGlyphOrder():
        ap, bp = AreaPen(gs), BoundsPen(gs)
        gs[name].draw(ap); gs[name].draw(bp)
        stats[name] = (gs[name].width, ap.value, bp.bounds)
    return stats

def shaper(path):
    blob = hb.Blob.from_file_path(path)
    face = hb.Face(blob)
    font = hb.Font(face)
    names = TTFont(path).getGlyphOrder()
    def shape(text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, {})
        return [(names[i.codepoint], p.x_advance, p.x_offset, p.y_offset)
                for i, p in zip(buf.glyph_infos, buf.glyph_positions)]
    return shape

texts = corpus()
report = {"corpus_size": len(texts)}
for w in WEIGHTS:
    paths = {"new": f"{NEW}/HindSiliguri-{w}.otf", "2015": f"{OLD}/HindSiliguri-{w}.otf", "gf": f"{GF}/HindSiliguri-{w}.ttf"}
    fonts = {k: TTFont(v) for k, v in paths.items()}
    stats = {k: glyph_stats(f) for k, f in fonts.items()}
    shapes = {k: shaper(v) for k, v in paths.items()}
    r = {}
    for ref in ("2015", "gf"):
        a, b = stats["new"], stats[ref]
        d = {
            "only_new": sorted(set(a) - set(b)),
            "only_ref": sorted(set(b) - set(a)),
            "width": {}, "area_sign_flip": {}, "area": {}, "bounds": {},
        }
        for n in sorted(set(a) & set(b)):
            wa, aa, ba = a[n]; wb, ab, bb = b[n]
            if wa != wb:
                d["width"][n] = (wa, wb)
            # CFF and TrueType wind outer contours opposite ways: compare magnitudes, and the sign relative to the
            # reference format's convention.
            sa = aa if ref == "2015" else -aa
            if abs(aa) > 1 and abs(ab) > 1 and (sa > 0) != (ab > 0):
                d["area_sign_flip"][n] = (round(aa), round(ab))
            tol = 0.5 if ref == "2015" else max(15, abs(ab) * 0.004)
            if abs(abs(aa) - abs(ab)) > tol:
                d["area"][n] = (round(aa), round(ab))
            if ba != bb and (ba is None or bb is None or max(abs(x - y) for x, y in zip(ba, bb)) > (0 if ref == "2015" else 1)):
                d["bounds"][n] = (ba, bb)
        sh = []
        for t in texts:
            x, y = shapes["new"](t), shapes[ref](t)
            if x != y:
                sh.append((t, x, y))
        d["shaping_diffs"] = len(sh)
        d["shaping_examples"] = sh[:40]
        d["shaping_glyphs_only_diffs"] = sum(1 for t, x, y in sh if [g[0] for g in x] != [g[0] for g in y])
        r[ref] = d
    report[w] = r
    print(w, {ref: {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in r[ref].items() if k != "shaping_examples"} for ref in r})
json.dump(report, open(OUT, "w"), ensure_ascii=False, indent=1, default=str)
