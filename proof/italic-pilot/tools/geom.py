"""outline helpers: skia paths from solver contours, scanlines, shear"""
import skia, math
K = 0.25
YC = 253.5            # shear centre: the middle of the x-height

def path(cs, dx=0.0, dy=0.0, s=1.0, flip=True, base=0.0):
    p = skia.Path()
    for c in cs:
        n = c["nodes"]; N = len(n)
        ons = [i for i in range(N) if n[i][2] != "o"]
        if not ons: continue
        X = lambda q: (dx + q[0] * s, (base - q[1] * s) if flip else dy + q[1] * s)
        st = ons[-1] if c["closed"] else ons[0]
        p.moveTo(*X(n[st]))
        seq = ons if c["closed"] else ons[1:]
        prev = st
        for j in seq:
            offs = [n[k % N] for k in range(prev + 1, prev + 1 + ((j - prev - 1) % N))]
            if len(offs) == 2:
                p.cubicTo(*X(offs[0]), *X(offs[1]), *X(n[j]))
            elif len(offs) == 1:
                p.quadTo(*X(offs[0]), *X(n[j]))
            else:
                p.lineTo(*X(n[j]))
            prev = j
        if c["closed"]: p.close()
    p.setFillType(skia.PathFillType.kWinding)
    return p

def shear_cs(cs, k=K, yc=YC):
    return [{"closed": c["closed"], "nodes": [[n[0] + k * (n[1] - yc), n[1]] + list(n[2:]) for n in c["nodes"]]} for c in cs]

def runs_at_y(cs, y, x0=-500, x1=2000):
    """ink runs (x_start, x_end) on the horizontal y, nonzero fill (overlaps merged)"""
    p = path(cs, flip=False)
    xs, inside, out = [], False, []
    step = 0.25
    x = x0; start = None
    while x < x1:
        c = p.contains(x, y)
        if c and start is None: start = x
        if not c and start is not None: out.append((start, x)); start = None
        x += step
    return out

def runs_at_x(cs, x, y0=-400, y1=1100):
    p = path(cs, flip=False); out = []; start = None; y = y0
    while y < y1:
        c = p.contains(x, y)
        if c and start is None: start = y
        if not c and start is not None: out.append((start, y)); start = None
        y += 0.25
    return out
