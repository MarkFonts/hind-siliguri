"""self-check crops: GroupMover outline at CNTR 0 / 50 / 100 overlaid, nodes numbered on the 100 state"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from groupmove import GroupMover
from sheet import Panel, BG
from partsheet import draw_poly
from rungs import Outline
from PIL import Image
G = json.load(open('../src/set.json'))
ims = []
for spec in sys.argv[2:]:
    key, bbs = spec.split(':'); bb = tuple(float(x) for x in bbs.split(','))
    GM = GroupMover(G[key])
    A = Panel(700, 640, bb, margin=10)
    A.title('%s %s' % (key, bbs))
    o1 = Outline(GM.contours_at(1.0))
    A.fill_outline(o1, color=(45, 58, 32), edge=(60, 60, 60))
    for t, col in ((0.0, (120, 120, 120)), (0.5, (90, 160, 255)), (1.0, (255, 255, 255))):
        o = Outline(GM.contours_at(t))
        for poly in o.polys:
            draw_poly(A, poly + [poly[0]], col, 1.2)
    A.nodes(o1)
    ims.append(A.out())
W = sum(i.width for i in ims) + 10 * len(ims)
sh = Image.new('RGB', (W, 640), BG); x = 0
for i in ims:
    sh.paste(i, (x, 0)); x += i.width + 10
sh.save(sys.argv[1])
