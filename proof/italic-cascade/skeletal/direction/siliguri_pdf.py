"""Siliguri text proof in the oblique (Mark 2026-11-18: "and siliguri text as pdf?"). Tagore's Gitanjali in Bangla, the
copy already in the fork (proof/specimen/text/gitanjali_bn.json, read only). Verse, flush left. One PDF per master,
set in out/siliguri_option-2/HindSiliguriOblique-<Master>.otf (siliguri_font.py). UPRIGHT=1 sets the same pages in the
fork's upright OTF, for my own check of the shaping.
  python siliguri_pdf.py [Light|Bold ...]"""
import html, json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE); FORK = os.path.dirname(os.path.dirname(os.path.dirname(SK))); OUT = os.path.join(SK, "out", "siliguri_" + os.environ.get("TAG", "option-2")); NAME = os.environ.get("NAME", "option-2_the-build")
UP = os.environ.get("UPRIGHT") == "1"; LABEL = os.environ.get("LABEL", "option 2: the build")
BN = {k: [l.replace("\xa0", " ") for l in v] for k, v in json.load(open(os.path.join(FORK, "proof", "specimen", "text", "gitanjali_bn.json"), encoding="utf8")).items()}
CSS = """@font-face{font-family:"P";src:url("FONT") format("opentype")}
@page{size:6.5in 9.5in;margin:.8in .5in .95in .5in}
*{font-synthesis:none}
html{font-family:"P";font-size:14pt;line-height:23pt;font-kerning:normal}
body{margin:0;padding:0 .25in}
h1,h2,p{font-weight:normal;font-style:normal;margin:0}
.title{break-after:page;padding-top:1.6in}
.title h1{font-size:64pt;line-height:80pt}
.by{margin-top:.4in;font-size:12pt;line-height:17pt}
.show{break-after:page;padding-top:.3in}
.show p{font-size:40pt;line-height:58pt;margin-bottom:.35in}
.poem{break-inside:avoid-page;margin-bottom:.5in}
.poem h2{font-size:22pt;line-height:30pt;margin-bottom:.12in}
"""
for m in (sys.argv[1:] or ["Light", "Bold"]):
    font = "HindSiliguri-%s.otf" % m if UP else "HindSiliguriOblique-%s.otf" % m
    if UP: shutil.copy(os.path.join(FORK, "fonts", "otf", font), os.path.join(OUT, font))
    B = ['<section class="title"><h1 lang="bn">গীতাঞ্জলি</h1><p class="by" lang="en">Hind Siliguri %s %s proof, %s</p></section>' % (m, "upright (for checking)" if UP else "Oblique", html.escape(LABEL))]
    B.append('<section class="show" lang="bn">' + "".join("<p>%s</p>" % html.escape(l) for l in (BN["৫"][0], BN["৩"][0], " ".join(BN["৭"][:2]), " ".join(BN["১"][:2]))) + "</section>")
    for k, lines in BN.items():
        B.append('<section class="poem" lang="bn"><h2>%s</h2><p>%s</p></section>' % (html.escape(k), "<br>".join(html.escape(l) for l in lines)))
    tag = "upright" if UP else "oblique"; H = os.path.join(OUT, "gitanjali_%s_%s.html" % (m.lower(), tag))
    open(H, "w", encoding="utf8").write('<!doctype html><html lang="bn"><head><meta charset="utf-8"><title>Gitanjali, Hind Siliguri %s %s proof</title><style>%s</style></head><body>%s</body></html>' % (m, tag, CSS.replace("FONT", font), "\n".join(B)))
    pdf = os.path.join(OUT, "Hind-Siliguri-%s-%s_%s_Gitanjali-Bangla.pdf" % (m, "Upright-check" if UP else "Oblique", NAME))
    if os.path.exists(pdf): os.remove(pdf)
    r = subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files", "--virtual-time-budget=30000", "--user-data-dir=" + os.path.join(OUT, ".chrome"), "--print-to-pdf=" + pdf, "file://" + H], capture_output=True, text=True, timeout=300)
    print(m, os.path.exists(pdf) and os.path.getsize(pdf) // 1024, "KB", pdf)
