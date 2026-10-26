import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from move import Mover
from movesheet import moved_side
from sheet import Panel, BG
from partsheet import COLS, draw_poly, draw_flag
from rungs import Outline
from PIL import Image

def zoom(G, key, bb, out, W=860, H=760):
    g = G[key]; M = Mover(g); ims = []
    for t in (0.0, 1.0):
        A = Panel(W, H, bb, margin=24)
        A.title('/%s %s · CNTR %d' % (g['glyph'], g['master'], int(t * 100)), 'sides coloured per part · dashed = drawn · numbers = nodes')
        ol2 = Outline(M.contours_at(t)); A.fill_outline(ol2, color=(50, 58, 42), edge=(110, 110, 110))
        if t > 0:
            for poly in M.ol.polys: draw_poly(A, poly + [poly[0]], (200, 200, 200), 0.8, dash=6)
        for i, (SA, saL, dAL, SB, sbL, dBL, st) in enumerate(M.side_disp):
            col = COLS[i % len(COLS)]
            draw_poly(A, moved_side(SA, saL, dAL, t, M), col, 1.3); draw_poly(A, moved_side(SB, sbL, dBL, t, M), col, 1.3)
        for fl in M.P.flags: draw_flag(A, M.P, fl)
        A.nodes(ol2)
        ims.append(A.out())
    sheet = Image.new('RGB', (W * 2 + 10, H), BG); sheet.paste(ims[0], (0, 0)); sheet.paste(ims[1], (W + 10, 0)); sheet.save(out)
    return M

def fname(key):
    """file-safe key on a case-insensitive disk: every capital in the glyph name gets a trailing _ (E -> E_)"""
    tag, _, gl = key.partition("_")
    return tag + "_" + "".join(c + "_" if c.isupper() else c for c in gl)

if __name__ == '__main__':
    G = json.load(open(sys.argv[1])); outdir = sys.argv[2]
    for spec in sys.argv[3:]:
        key, bbs = spec.split(':'); bb = tuple(float(x) for x in bbs.split(','))
        M = zoom(G, key, bb, os.path.join(outdir, fname(key) + '_zoommove.png'))
        print('==', key, 'kinds', {k: v for k, v in sorted(M.P.kind.items()) if v != 'side'}, 'cups', list(M.cups))
        for row in M.rung_log:
            print('   %-8s %s<->%s w %5.1f grow %5.1f hA %.2f hB %.2f  dA %5.1f dB %5.1f %s' % (row['stroke'], row['a'], row['b'], row['w'], row['grow'], row['hA'], row['hB'], row['dA'], row['dB'], 'root' if row['root'] else ''))
