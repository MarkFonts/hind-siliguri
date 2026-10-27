"""Full-page specimens: each page sets one passage in the roman on the top half and the italic below.

usage: build.py ROMAN_VF ITALIC_VF "ITALIC LABEL" OUT_DIR
Writes OUT_DIR/index.html (with the fonts beside it) and OUT_DIR/HindSiliguri-roman-italic-specimen.pdf.
Text: Tagore's Gitanjali, English (Project Gutenberg #7164) and Bangla (bn.wikisource, Gitanjali 1913).
"""
import sys, os, json, shutil, subprocess, html

ROMAN, ITALIC, ITALIC_LABEL, OUT = sys.argv[1:5]
HERE = os.path.dirname(os.path.abspath(__file__))
EN = {int(k): [l.strip() for l in v.split("\n")] for k, v in json.load(open(os.path.join(HERE, "text/gitanjali_en.json"))).items()}
BN = {k: [l.replace("\xa0", " ") for l in v] for k, v in json.load(open(os.path.join(HERE, "text/gitanjali_bn.json"))).items()}
WEIGHTS = {300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}

# (weight, size in pt, line height, script, text as a list of lines or paragraphs, columns)
PAGES = [
    (700, 96, 1.0, "latn", ["Thou hast made me endless"], 1),
    (700, 84, 1.1, "beng", ["অন্তর মম বিকশিত কর"], 1),
    (300, 80, 1.0, "latn", ["The light of thy music illumines the world"], 1),
    (300, 80, 1.1, "beng", ["কত অজানারে জানাইলে তুমি"], 1),
    (600, 54, 1.0, "latn", ["When thou commandest me to sing it seems that my heart would break with pride"], 1),
    (600, 54, 1.1, "beng", ["তুমি নব নব রূপে এস প্রাণে এস গন্ধে বরণে, এস গানে।"], 1),
    (500, 32, 1.05, "mixed", [EN[11][0], " ".join(BN["১"][:4])], 1),
    (400, 13, 1.45, "latn", EN[5] + EN[6], 2),
    (400, 13, 1.6, "beng", BN["২"], 2),
    (300, 12, 1.45, "latn", EN[35] + EN[36], 2),
    (300, 12, 1.6, "beng", BN["৩"], 2),
    (700, 12, 1.45, "latn", EN[60], 2),
    (700, 12, 1.6, "beng", BN["৫"], 2),
]

def block(lines, script, cols):
    if script == "mixed":
        return "".join(f'<p lang="{"en" if i == 0 else "bn"}">{html.escape(l)}</p>' for i, l in enumerate(lines))
    lang = "bn" if script == "beng" else "en"
    if cols == 1:
        return f'<p lang="{lang}">{html.escape(lines[0])}</p>'
    if script == "beng":  # verse: keep the poem's lines
        return f'<div class="cols" lang="bn"><p>' + "<br>".join(html.escape(l) for l in lines) + "</p></div>"
    return f'<div class="cols" lang="en">' + "".join(f"<p>{html.escape(l)}</p>" for l in lines) + "</div>"

def page(n, w, size, lh, script, lines, cols):
    name = WEIGHTS[w]
    body = block(lines, script, cols)
    half = lambda cls, label, sub: (
        f'<section class="{cls}"><header><span class="fam">Hind Siliguri {label}</span>'
        f'<span class="sub">{sub}</span></header>'
        f'<div class="set" style="font-weight:{w};font-size:{size}pt;line-height:{lh}">{body}</div></section>')
    return (f'<div class="page">'
            + half("roman", name, f"{size} pt")
            + half("italic", f"{name} Italic", html.escape(ITALIC_LABEL))
            + f'<footer>{n}</footer></div>')

os.makedirs(OUT, exist_ok=True)
shutil.copy(ROMAN, os.path.join(OUT, "roman.ttf"))
shutil.copy(ITALIC, os.path.join(OUT, "italic.ttf"))
CSS = """
@font-face{font-family:HS;src:url(roman.ttf);font-weight:300 700;font-style:normal}
@font-face{font-family:HS;src:url(italic.ttf);font-weight:300 700;font-style:italic}
@page{size:11in 8.5in;margin:0}
*{box-sizing:border-box}
html,body{margin:0;background:#fff;color:#111}
body{font-family:HS}
.page{width:11in;height:8.5in;padding:.45in .6in .35in;display:grid;grid-template-rows:1fr 1fr auto;page-break-after:always;break-after:page;overflow:hidden}
section{display:flex;flex-direction:column;min-height:0}
section.italic{border-top:1px solid #bbb;padding-top:.18in}
section.italic .set{font-style:italic}
header{display:flex;align-items:baseline;gap:.25in;margin-bottom:.12in;font-weight:500}
.fam{font-size:20pt;line-height:1}
.sub{font-size:10pt;color:#666;font-weight:400}
.set{flex:1;min-height:0}
.set p{margin:0}
.cols{column-count:2;column-gap:.45in}
.cols p{margin:0 0 .5em;text-align:left}
.set p[lang=bn]{margin-top:.15em}
footer{font-size:9pt;color:#888;text-align:right;font-weight:400}
@media screen{body{background:#ddd}.page{margin:.3in auto;background:#fff;box-shadow:0 1px 4px #0003}}
"""
pages = "".join(page(i + 1, *p) for i, p in enumerate(PAGES))
open(os.path.join(OUT, "index.html"), "w").write(
    f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Hind Siliguri roman and italic specimen</title>'
    f"<style>{CSS}</style></head><body>{pages}</body></html>")
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
pdf = os.path.join(OUT, "HindSiliguri-roman-italic-specimen.pdf")
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=5000",
                f"--print-to-pdf={pdf}", "file://" + os.path.join(os.path.abspath(OUT), "index.html")],
               check=True, capture_output=True)
print(pdf)
