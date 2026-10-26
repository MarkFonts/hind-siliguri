"""Build <font>.masters.json: per-master stems / zones / metrics, file values where defined, MEASURED from the glyphs otherwise.

mk_masters.py OUT.masters.json SRC.json TAG=SRCFILE:MasterName [...]
Shape follows dump_hs/masters.json ("ia","V","H","Z","upm") plus: "src" (where each number came from),
"Vm","Hm" (always measured from the H), "measured" (cap/x/asc/desc/baseline from the letters), "xHeight","capHeight",
"ascender","descender", "file" (raw values from the .glyphs master), "master" (name), "missing" (what could not be measured).
Z is [position, size] like Harvey's.  lo/hi (stemperature colour-ramp bounds) are NOT produced: they are a display choice, not a font fact.
"""
import sys, json, math, glyphsLib


def flat(contour, n=12):
    """flatten a closed contour [[x,y,t,s]..] to a polyline (cubic order = file order, offcurves precede their oncurve)."""
    nodes = contour["nodes"]; N = len(nodes); pts = []
    on = [i for i, nd in enumerate(nodes) if nd[2] != 'o']
    if not on: return pts
    for k, i in enumerate(on):
        j = on[(k + 1) % len(on)]
        # offcurves between i and j (walking forward)
        offs = []; t = (i + 1) % N
        while t != j: offs.append(nodes[t]); t = (t + 1) % N
        p0 = nodes[i]; p3 = nodes[j]
        if len(offs) == 2:
            for s in range(n):
                u = s / n
                a = (1 - u) ** 3; b = 3 * u * (1 - u) ** 2; c = 3 * u * u * (1 - u); d = u ** 3
                pts.append((a * p0[0] + b * offs[0][0] + c * offs[1][0] + d * p3[0], a * p0[1] + b * offs[0][1] + c * offs[1][1] + d * p3[1]))
        else:
            pts.append((p0[0], p0[1]))
    return pts


def scan_y(cs, y):
    xs = []
    for c in cs:
        P = flat(c)
        for (x0, y0), (x1, y1) in zip(P, P[1:] + P[:1]):
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) / (y1 - y0) * (x1 - x0))
    xs.sort(); return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


def scan_x(cs, x):
    ys = []
    for c in cs:
        P = flat(c)
        for (x0, y0), (x1, y1) in zip(P, P[1:] + P[:1]):
            if (x0 <= x < x1) or (x1 <= x < x0):
                ys.append(y0 + (x - x0) / (x1 - x0) * (y1 - y0))
    ys.sort(); return [(ys[i], ys[i + 1]) for i in range(0, len(ys) - 1, 2)]


def hflat(cs, top):
    """y of the extreme node that is an end of a horizontal line segment (the flat serif/baseline), else None"""
    best = None
    for c in cs:
        nd = c["nodes"]; N = len(nd)
        for i in range(N):
            a, b = nd[i], nd[(i + 1) % N]
            if b[2] == 'l' and abs(a[1] - b[1]) < 0.5 and a[2] != 'o':
                y = a[1]
                if best is None or (y > best if top else y < best): best = y
    e = max(n[1] for c in cs for n in c["nodes"]) if top else min(n[1] for c in cs for n in c["nodes"])
    return best if best is not None and abs(best - e) <= 30 else None


def ext(cs, top):
    ys = [n[1] for c in cs for n in c["nodes"]]
    return max(ys) if top else min(ys)


def measure(G, tag):
    out = {"missing": []}
    H = G.get(tag + "_H")
    if H:
        cs = H["contours"]; cap = ext(cs, True); out["capHeight"] = cap; out["baseline"] = ext(cs, False)
        out["capFlat"] = hflat(cs, True)
        ys = sorted(set(round(n[1]) for c in cs for n in c["nodes"]))
        yy = 0.75 * cap
        iv = [(a, b) for a, b in scan_y(cs, yy)]
        wid = [b - a for a, b in iv]
        # stems = the two widest-in-the-outer-pair intervals; drop anything wider than 3x the median (merged crossbar)
        out["Vm"] = [round(w, 1) for w in wid] if len(wid) == 2 else None
        if out["Vm"] is None: out["missing"].append("V: %d intervals at 0.75 cap" % len(wid))
        if len(iv) >= 2:
            cx = (iv[0][1] + iv[-1][0]) / 2
            bars = scan_x(cs, cx)
            mid = [(a, b) for a, b in bars if 0.2 * cap < (a + b) / 2 < 0.8 * cap]
            out["Hm"] = [round(b - a, 1) for a, b in mid] if mid else None
            if not mid: out["missing"].append("H: no crossbar at centre x")
        else:
            out["Hm"] = None
    else:
        out["missing"].append("no H layer: V/H not measurable")
    n = G.get(tag + "_n")
    if n:
        out["xHeight"] = ext(n["contours"], True); out["xFlat"] = hflat(n["contours"], True)
    else: out["missing"].append("no n layer: x-height")
    asc = [ext(G[k]["contours"], True) for k in (tag + "_f", tag + "_k") if k in G]
    out["ascender"] = max(asc) if asc else None
    if not asc: out["missing"].append("no f/k layer: ascender")
    if tag + "_j" in G:
        out["descender"] = ext(G[tag + "_j"]["contours"], False); out["descFlat"] = hflat(G[tag + "_j"]["contours"], False)
    else: out["missing"].append("no j layer: descender")
    e = G.get(tag + "_e")
    if e:
        out["e_top"] = ext(e["contours"], True); out["e_bot"] = ext(e["contours"], False)
    zm = []
    def add(pos, ov):
        if pos is not None: zm.append([float(pos), float(ov)])
    if out.get("ascender") is not None: add(out["ascender"], 0)
    if out.get("capFlat") is not None: add(out["capFlat"], 0)
    xf = out.get("xFlat") if out.get("xFlat") is not None else out.get("xHeight")
    if xf is not None: add(xf, (out["e_top"] - xf) if "e_top" in out else 0)
    if out.get("baseline") is not None: add(0, (out["e_bot"] if "e_bot" in out else 0))
    if out.get("descender") is not None: add(out["descender"], 0)
    out["Zm"] = zm
    return out


if __name__ == "__main__":
    out, src = sys.argv[1], sys.argv[2]; G = json.load(open(src)); res = {}
    cache = {}
    for spec in sys.argv[3:]:
        tag, _, rest = spec.partition('='); path, _, mname = rest.partition(':')
        f = cache.setdefault(path, glyphsLib.GSFont(path))
        m = next(m for m in f.masters if m.name == mname)
        meas = measure(G, tag)
        file = {"horizontalStems": list(m.horizontalStems), "verticalStems": list(m.verticalStems),
                "zones": [[z.position, z.size] for z in m.alignmentZones],
                "xHeight": m.xHeight, "capHeight": m.capHeight, "ascender": m.ascender, "descender": m.descender,
                "italicAngle": m.italicAngle}
        r = {"master": mname, "ia": float(m.italicAngle), "upm": float(f.upm)}
        srcs = {"ia": "file", "upm": "file"}
        for key, fk, mk in (("V", "verticalStems", "Vm"), ("H", "horizontalStems", "Hm")):
            if file[fk]:
                r[key] = [float(v) for v in file[fk]]; srcs[key] = "file"
            elif meas.get(mk):
                r[key] = sorted(meas[mk]); srcs[key] = "measured (file has none)"
            else:
                r[key] = []; srcs[key] = "unavailable"
        r["Z"] = [[float(a), float(b)] for a, b in file["zones"]]; srcs["Z"] = "file"
        for k in ("xHeight", "capHeight", "ascender", "descender"):
            r[k] = float(file[k]) if file[k] is not None else None; srcs[k] = "file"
        r["Vm"], r["Hm"] = meas.get("Vm"), meas.get("Hm")
        r["measured"] = {k: meas.get(k) for k in ("capHeight", "capFlat", "xHeight", "xFlat", "ascender", "descender", "descFlat", "baseline", "e_top", "e_bot")}
        r["Zm"] = meas["Zm"]
        r["missing"] = meas["missing"]; r["src"] = srcs; r["file"] = file
        res[tag] = r
    json.dump(res, open(out, 'w'), indent=1)
    for t, r in res.items():
        print(t, "ia", r["ia"], "V", r["V"], "H", r["H"], "| measured V", r["Vm"], "H", r["Hm"], "|", r["measured"], "| file x/cap/asc/desc", r["xHeight"], r["capHeight"], r["ascender"], r["descender"], r["missing"])
