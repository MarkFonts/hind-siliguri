"""One page of running text as a picture (Mark 2026-11-20: "can you show me a running text page of the hind italic?").
Process: obliquing. Takes the paragraphs of the Tale of Two Cities proof already set for TAG (out/vf_<TAG>/tale_*.html),
sets one 6.5 x 9.5 in page flush left, no hyphenation, no kerning (Hind has none decided), and photographs it with
headless Chrome at twice size. Bare page: text only.
  TAG=round-solve python text_page.py [Light|Bold ...]     WGHT=400 sets an in-between weight (interpolated, not a master); SCALE=4 doubles the picture (default 2)
  -> sheets/hind-siliguri_<TAG>_running-text_<master>.png"""
import os, re, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(HERE); TAG = os.environ.get("TAG", "round-solve"); OUT = os.path.join(SK, "out", "vf_" + TAG)
SRC = open(os.path.join(OUT, "tale_light_ragged.html"), encoding="utf8").read(); PS = re.findall(r"<p[^>]*>(.*?)</p>", SRC, flags=re.S)[1:14]
SIZE = os.environ.get("SIZE", "11.2pt/15.6pt"); fs, lh = SIZE.split("/")
for m in (sys.argv[1:] or ["Light"]):
    w = int(os.environ.get("WGHT", {"Light": 300, "Bold": 700}.get(m, 400)))
    css = """@font-face{font-family:"P";src:url("HindProofL-VF.ttf") format("truetype");font-weight:300 700}
*{font-synthesis:none;font-variation-settings:"wght" %d,"slnt" -14.0362}
html,body{margin:0;background:#fff}
body{width:6.5in;height:9.5in;overflow:hidden;box-sizing:border-box;padding:.8in .75in .95in .75in;font-family:"P";font-size:%s;line-height:%s;font-kerning:none;color:#000}
div{height:100%%;overflow:hidden}
p{margin:0;text-indent:1.35em;text-align:left;hyphens:none}
p:first-child{text-indent:0}""" % (w, fs, lh)
    name = m.lower() if "WGHT" not in os.environ else "wght%d" % w
    H = os.path.join(OUT, "page_%s.html" % name); open(H, "w", encoding="utf8").write('<!doctype html><html lang="en"><head><meta charset="utf-8"><style>%s</style></head><body><div>%s</div></body></html>' % (css, "".join("<p>%s</p>" % p for p in PS)))
    png = os.path.join(SK, "sheets", "hind-siliguri_%s_running-text_%s%s.png" % (TAG, name, "" if os.environ.get("SCALE", "2") == "2" else "_%sx" % os.environ["SCALE"]))
    subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--disable-gpu", "--allow-file-access-from-files", "--hide-scrollbars", "--force-device-scale-factor=%s" % os.environ.get("SCALE", "2"), "--virtual-time-budget=8000", "--user-data-dir=" + os.path.join(OUT, ".chrome"), "--window-size=624,912", "--screenshot=" + png, "file://" + H], capture_output=True, text=True, timeout=180)
    print(m, w, os.path.exists(png) and os.path.getsize(png) // 1024, "KB", png)
