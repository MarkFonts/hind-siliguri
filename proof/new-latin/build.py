"""New Latin Core letters in real words, roman over italic, Light / Regular / Bold. usage: build.py ROMAN_VF ITALIC_VF OUT_DIR"""
import sys, os, shutil, subprocess
ROMAN, ITALIC, OUT = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
shutil.copy(ROMAN, os.path.join(OUT, "roman.ttf")); shutil.copy(ITALIC, os.path.join(OUT, "italic.ttf"))
# real words where I know them (Maltese, Northern Sámi, German, 18th-century English); the rest as letters
LINES = ["Ħaġar Qim, il-ħobż u l-ħalib", "ŋuovvamánnu, ŊUOVVAMÁNNU", "STRAẞE, GROẞ, ß ẞ", "Maſſachuſetts", "Ħ ħ Ŧ ŧ Ŋ ŋ Ǥ ǥ ſ ẞ", "ı ȷ í ǰ į́ ė ż İ Ż ċ ġ"]
WEIGHTS = [(300, "Light"), (400, "Regular"), (700, "Bold")]
rows = []
for w, name in WEIGHTS:
    for style in ("normal", "italic"):
        label = "Hind Siliguri %s%s" % (name, " Italic" if style == "italic" else "")
        rows.append('<section><h2>%s</h2>%s</section>' % (label, "".join(
            '<p style="font-weight:%d;font-style:%s">%s</p>' % (w, style, l) for l in LINES)))
html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Hind Siliguri new Latin</title><style>
@font-face{font-family:HS;src:url(roman.ttf);font-weight:300 700;font-style:normal}
@font-face{font-family:HS;src:url(italic.ttf);font-weight:300 700;font-style:italic}
@page{size:11in 8.5in;margin:.5in}
body{font-family:HS;margin:0;color:#111;background:#fff}
section{page-break-inside:avoid;margin-bottom:.25in}
h2{font-size:14pt;font-weight:500;font-style:normal;margin:0 0 .05in;color:#555}
p{font-size:34pt;line-height:1.05;margin:0}
section:nth-of-type(2n){page-break-after:always}
</style></head><body>""" + "".join(rows) + "</body></html>"
open(os.path.join(OUT, "index.html"), "w").write(html)
pdf = os.path.join(OUT, "HindSiliguri-new-latin.pdf")
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                "--virtual-time-budget=5000", "--print-to-pdf=" + pdf, "file://" + os.path.abspath(os.path.join(OUT, "index.html"))], check=True, capture_output=True)
print(pdf)
