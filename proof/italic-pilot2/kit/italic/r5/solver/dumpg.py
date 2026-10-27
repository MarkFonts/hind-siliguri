"""dump a glyph's segments: node numbers, kind, length, turn, chord direction"""
import sys, json, math
sys.path.insert(0, __import__('os').path.dirname(__file__))
from rungs import Outline
G = json.load(open(sys.argv[1]))
for key in sys.argv[2].split(","):
    g = G[key]; ol = Outline(g["contours"])
    print("==", key)
    for k, s in enumerate(ol.segs):
        t0, t1 = s.tangent(0), s.tangent(1)
        turn = math.degrees(math.atan2(t0[0]*t1[1]-t0[1]*t1[0], t0[0]*t1[0]+t0[1]*t1[1]))
        a, b = s.pts[0], s.pts[-1]
        print("  p%d %3d->%-3d %-5s L%6.1f turn%7.1f  (%g,%g)->(%g,%g) wall %d" % (s.pi, s.gi, s.gj, s.kind, s.length, turn, a[0], a[1], b[0], b[1], s.wall))
