"""One sheet per master: every glyph's parts pairing over the letter, plus the Harvey ligature."""
import sys, os, json
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parts import Parts
from sheet import Panel, bbox_of, BG, SS, font, CAL
from partsheet import draw_part, draw_flag, COLS

def cell(g, W, H, labels=True):
    P = Parts(g["contours"], slant=(18.0 if "Italic" in g["master"] else 0.0)); ol = P.ol
    A = Panel(W, H, bbox_of(ol, pad=30), margin=28)
    A.title("/%s" % g["glyph"], "%d stroke%s, %d flag%s%s" % (len(P.strokes), "" if len(P.strokes) == 1 else "s", len(P.flags), "" if len(P.flags) == 1 else "s",
            ("  unpaired sides: %s" % P.unpaired) if P.unpaired else ""))
    A.fill_outline(ol, color=(38, 46, 30), edge=(90, 90, 90))
    for i, st in enumerate(P.strokes):
        draw_part(A, P, st, COLS[i % len(COLS)], labels=labels)
    for fl in P.flags:
        draw_flag(A, P, fl)
    A.nodes(ol, labels=labels)
    return A.out(), P

if __name__ == "__main__":
    G = json.load(open(sys.argv[1])); outdir = sys.argv[2]
    masters = sys.argv[3].split(",")
    rows = [["f", "j", "H", "n", "a", "E", "T"], ["r", "v", "e", "y", "k", "x"]]
    CW, CH = 440, 480
    for m in masters:
        tag = "HS" + m.replace(" ", "")
        sheet = Image.new("RGB", (CW * 7 + 60, CH * 2 + 520 + 40), BG)
        for ri, row in enumerate(rows):
            for ci, gn in enumerate(row):
                key = "%s_%s" % (tag, gn)
                if key not in G: continue
                try:
                    im, P = cell(G[key], CW, CH)
                except Exception as e:
                    im = Image.new("RGB", (CW, CH), (40, 10, 10)); print("FAIL", key, repr(e))
                sheet.paste(im, (ci * CW + 10, ri * CH + 10))
        key = "%s_H_a_r_v_e_y" % tag
        if key in G:
            try:
                im, P = cell(G[key], CW * 7 + 40, 520, labels=False)
                sheet.paste(im, (10, CH * 2 + 30))
            except Exception as e:
                print("FAIL", key, repr(e))
        out = os.path.join(outdir, "grid_%s.png" % tag)
        sheet.save(out); print("wrote", out)
