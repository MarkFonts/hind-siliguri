"""Per-node readings for hscontrast from the parts pairing.

readings.py SET.json OUTDIR [keys,...]   -> OUTDIR/<key>.readings.json  + OUTDIR/index.json

Per layer:
  parts:  strokes (two sides, rungs) and flags (held)
  nodes:  one entry per on-curve node, in .glyphs order counted across paths:
          kind  node     paired with a drawn node across the stroke (width = perpendicular thickness)
                virt     paired with a point between nodes on the other side
                cut      end rung along a cut (terminal face); width is the stroke's width there
                root     end rung at the stroke's root (it emerges from another part); width is NOT a stroke width
                flag     on a wedge serif: held, no width
                start    on a START wall (blunt stroke beginning): never paired
                unpaired on a side but with no rung (past the other side's end)
          width  perpendicular thickness at the rung (font units) or null
          partner_node  the drawn node across (or null), partner [x, y], centre [x, y], tangent [tx, ty]
"""
import sys, os, json, math, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parts import Parts, unit


def cut_between(P, pa, pb, tol=4.0):
    """is there a cut wall whose polyline passes within tol of both rung ends?"""
    ol = P.ol
    for wi, kind in P.kind.items():
        if kind != "cut":
            continue
        poly = []
        for k in ol.walls[wi]:
            poly += ol.segs[k].poly
        def near(p):
            return any(math.dist(p, q) <= tol for q in poly) or min(
                seg_dist(p, a, b) for a, b in zip(poly, poly[1:])) <= tol
        if near(pa) and near(pb):
            return wi
    return None


def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + dx * t), py - (ay + dy * t))


def readings(P, glyph, master):
    ol = P.ol
    out = {"glyph": glyph, "master": master, "parts": [], "nodes": [], "walls": []}
    for wi, w in enumerate(ol.walls):
        out["walls"].append({"id": wi, "kind": P.kind.get(wi, "side"),
                             "nodes": [ol.segs[k].gi for k in w] + [ol.segs[w[-1]].gj]})
    node_entry = {}
    contour_of = {}
    base = 0
    for pi, c in enumerate(ol.contours):
        for i in range(len(c["nodes"])):
            contour_of[base + i] = pi
        base += len(c["nodes"])
    for gi, (x, y, t, sm) in ol.node_xy.items():
        if t == "o":
            continue
        node_entry[gi] = {"node": gi, "contour": contour_of[gi], "x": x, "y": y, "kind": "unpaired",
                          "part": None, "side": None, "width": None, "partner_node": None,
                          "partner": None, "centre": None, "tangent": None}
    # START walls and flags first (a node on a flag/start edge is held even if it also sits on a side)
    for wi, kind in P.kind.items():
        if kind in ("notch", "flag"):
            for k in ol.walls[wi]:
                for nd in (ol.segs[k].gi, ol.segs[k].gj):
                    if nd in node_entry:
                        node_entry[nd]["kind"] = "flag" if kind == "flag" else "start"
    for si, st in enumerate(P.strokes):
        SA, SB = st["A"], st["B"]
        part = {"id": si, "kind": "stroke", "walls": list(st["walls"]), "mode": st["mode"],
                "sideA": [nd for _, nd in SA.nodes], "sideB": [nd for _, nd in SB.nodes], "rungs": []}
        for r in st["rungs"]:
            sa, sb, kind, nda, ndb = r
            if sa is None or sb is None:
                part["rungs"].append({"kind": kind, "a_node": nda, "b_node": ndb})
                for nd in (nda, ndb):
                    if nd is not None and node_entry[nd]["kind"] == "unpaired":
                        node_entry[nd]["part"] = si
                continue
            th, L, pa, pb = P.thickness(st, r)
            ta, tb = SA.tan(sa), SB.tan(sb)
            mt = unit((ta[0] + tb[0], ta[1] + tb[1]))
            c = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            rk = kind
            if kind == "end":
                rk = "cut" if cut_between(P, pa, pb) is not None else "root"
            elif kind in ("virtA", "virtB"):
                rk = "virt"
            rung = {"kind": rk, "a_node": nda, "b_node": ndb, "a": [pa[0], pa[1]], "b": [pb[0], pb[1]],
                    "centre": [c[0], c[1]], "tangent": [mt[0], mt[1]], "width": th, "rung": L}
            part["rungs"].append(rung)
            for nd, me, other, other_nd in ((nda, pa, pb, ndb), (ndb, pb, pa, nda)):
                if nd is None or nd not in node_entry:
                    continue
                e = node_entry[nd]
                if e["kind"] in ("flag", "start"):
                    continue
                e.update({"kind": rk if rk != "virt" else "virt", "part": si, "side": "A" if nd == nda else "B",
                          "width": None if rk == "root" else th, "partner_node": other_nd,
                          "partner": [other[0], other[1]], "centre": [c[0], c[1]], "tangent": [mt[0], mt[1]],
                          "rung": L})
        out["parts"].append(part)
    for fi, fl in enumerate(P.flags):
        out["parts"].append({"id": len(P.strokes) + fi, "kind": "flag", "tip": list(fl["tip"]),
                             "sides": [[fl["a"].gi, fl["a"].gj], [fl["b"].gi, fl["b"].gj]]})
    out["nodes"] = [node_entry[k] for k in sorted(node_entry)]
    out["unpaired_sides"] = list(P.unpaired)
    return out


def fname(key):
    """file-safe key on a case-insensitive disk: every capital in the glyph name gets a trailing _ (E -> E_)"""
    tag, _, gl = key.partition("_")
    return tag + "_" + "".join(c + "_" if c.isupper() else c for c in gl)

if __name__ == "__main__":
    src, outdir = sys.argv[1], sys.argv[2]
    G = json.load(open(src))
    keys = sys.argv[3].split(",") if len(sys.argv) > 3 else sorted(G)
    os.makedirs(outdir, exist_ok=True)
    index = []
    for key in keys:
        g = G[key]
        try:
            P = Parts(g["contours"], slant=(18.0 if "Italic" in g["master"] else 0.0))
            R = readings(P, g["glyph"], g["master"])
            json.dump(R, open(os.path.join(outdir, fname(key) + ".readings.json"), "w"))
            kinds = {}
            for n in R["nodes"]:
                kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
            row = {"key": key, "ok": True, "strokes": len(P.strokes), "flags": len(P.flags),
                   "unpaired_sides": P.unpaired, "node_kinds": kinds}
        except Exception as e:
            row = {"key": key, "ok": False, "error": repr(e), "trace": traceback.format_exc()[-600:]}
        index.append(row)
        print(key, {k: v for k, v in row.items() if k not in ("key", "trace")})
    json.dump(index, open(os.path.join(outdir, "index.json"), "w"), indent=1)
