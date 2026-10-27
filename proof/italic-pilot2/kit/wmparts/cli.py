"""python -m wmparts <verb> ...   (also the `wmparts` console script)

  extract  FONT --glyphs a,b,c [--masters Regular,Bold] [--keep-components] -o set.json
  masters  SET                      [-o set.masters.json]   the solver's master values (stem, A, slant, hairline, lines)
  pair     SET [--keys k1,k2]       -o readings/           <fname(key)>.readings.json + index.json
  move     SET [--keys ...] [--t 1.0] -o moved.json        moved contours (set.json format) + moved.report.json
  eval     SET [--keys ...]         -o curv/               results.json, CURV-style counts; comb PNGs unless --no-render
  sheets   SET --kind parts|grid|groups|overview|combs [--keys ...] -o sheets/
  vf       SET [--master Regular] [--no-erase-open-corners] -o vf/

SET / FONT: a set.json (its <set>.masters.json beside it is read) or a .glyphs / .glyphspackage. Every verb takes
--master-values PATH (a masters.json that replaces the file's / sidecar's values) and --skip GLYPH,... (left out of
"all"). --keys takes layer keys (HSRegular_n) or glyph names (n). Files follow the UFO convention (E -> E_).
"""
import argparse, json, os, sys, time, traceback

from . import __version__


def _load(a, glyphs=None):
    from .font import load_glyphs
    mv = a.master_values if getattr(a, "master_values", None) else None
    F = load_glyphs(a.src, glyphs=glyphs, master_values=mv)
    return F


def _keys(F, a):
    skip = {x for x in (getattr(a, "skip", "") or "").split(",") if x}
    if getattr(a, "keys", None):
        want = a.keys.split(",")
        return [k for k in sorted(F) if k in want or F[k]["glyph"] in want]
    return [k for k in sorted(F) if F[k]["glyph"] not in skip and any(len(c["nodes"]) for c in F[k]["contours"])]


def cmd_extract(a):
    from .font import load_glyphs
    glyphs = a.glyphs.split(",") if a.glyphs else None
    masters = a.masters.split(",") if a.masters else None
    F = load_glyphs(a.src, glyphs=glyphs, masters=masters, keep_components=a.keep_components,
                    master_values=a.master_values or None)
    F.to_json(a.out)
    miss = getattr(F, "missing", [])
    print("%d layers, masters %s -> %s (+ .masters.json)" % (len(F), ", ".join(F.masters.tags), a.out))
    for m in miss:
        if glyphs is None or m["glyph"] in glyphs:
            print("  missing", m["tag"], m["glyph"], m["why"])


def cmd_masters(a):
    F = _load(a)
    rows = {}
    for tag in F.masters.tags:
        mi = F.masters.info(tag, F)
        rows[tag] = mi
        print("%-22s ia %5.1f  stem %6.1f  A %5.1f  hairline %5.1f  x %s cap %s  lines lc %s uc %s" % (
            tag, mi["ia"], mi["stem"], mi["A"], mi["thin_top"], mi["x_height"], mi["cap_height"], mi["lines_lc"], mi["lines_uc"]))
    if a.out:
        F.masters.to_json(a.out); print("wrote", a.out)


def cmd_pair(a):
    from . import pair, readings
    from .font import fname
    F = _load(a)
    os.makedirs(a.out, exist_ok=True)
    index = []
    for key in _keys(F, a):
        g = F[key]
        try:
            P = pair(g); R = readings(P)
            json.dump(R, open(os.path.join(a.out, fname(key) + ".readings.json"), "w"))
            kinds = {}
            for n in R["nodes"]:
                kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
            row = {"key": key, "ok": True, "strokes": len(P.strokes), "flags": len(P.flags), "balls": len(P.balls),
                   "unpaired_sides": P.unpaired, "node_kinds": kinds}
        except Exception as e:
            row = {"key": key, "ok": False, "error": repr(e), "trace": traceback.format_exc()[-600:]}
        index.append(row)
        print(key, {k: v for k, v in row.items() if k not in ("key", "trace")})
    json.dump(index, open(os.path.join(a.out, "index.json"), "w"), indent=1)


def cmd_move(a):
    from . import move
    F = _load(a)
    out, reports = {}, {}
    for key in _keys(F, a):
        g = F[key]; t0 = time.time()
        M = move(g)
        rec = g.as_record(); rec["contours"] = M.contours_at(a.t)
        out[key] = rec
        R = M.report(); reports[key] = R
        print("%-28s %2d groups  A %5.1f  %.2fs" % (key, len(R["groups"]), M.A, time.time() - t0))
    d = os.path.dirname(a.out)
    if d:
        os.makedirs(d, exist_ok=True)
    json.dump(out, open(a.out, "w"))
    rp = a.out[:-5] + ".report.json" if a.out.endswith(".json") else a.out + ".report.json"
    json.dump(reports, open(rp, "w"), indent=1, default=str)
    print("wrote", a.out, "and", rp)


def evaluate_set(F, keys):
    """-> ({key: Verdict or Exception}, counts {verdict: n}, tilted sides)"""
    from . import move, evaluate
    res, cnt, tilt = {}, {}, 0
    for key in keys:
        try:
            v = evaluate(move(F[key]))
            res[key] = v; cnt[v.verdict] = cnt.get(v.verdict, 0) + 1; tilt += len(v.tilts)
        except Exception as e:
            res[key] = e; cnt["FAIL"] = cnt.get("FAIL", 0) + 1
            traceback.print_exc()
    return res, cnt, tilt


def cmd_eval(a):
    F = _load(a)
    keys = _keys(F, a)
    os.makedirs(a.out, exist_ok=True)
    res, cnt, tilt = evaluate_set(F, keys)
    rows = []
    for key, v in res.items():
        if isinstance(v, Exception):
            rows.append(dict(key=key, verdict="FAIL", error=repr(v))); print("%-28s FAIL %r" % (key, v)); continue
        rows.append(dict(key=key, **v.as_dict()))
        print("%-28s %-8s snaps %s spikes %s crosses %s tilted %d thinned %d" % (
            key, v.verdict, [x["node"] for x in v.snaps], [tuple(x["seg"]) for x in v.spikes], len(v.crosses), len(v.tilts), len(v.thinning)))
    json.dump(dict(counts=cnt, tilted=tilt, results=rows), open(os.path.join(a.out, "results.json"), "w"), indent=1, default=str)
    print("clean %d · minor %d · snapped %d · cross %d · FAIL %d · tilted straight sides %d" % (
        cnt.get("clean", 0), cnt.get("minor", 0), cnt.get("snapped", 0), cnt.get("cross", 0), cnt.get("FAIL", 0), tilt))
    if not a.no_render:
        from .render import curvsheet as C
        from .font import fname
        good = [v for v in res.values() if not isinstance(v, Exception)]
        for key, v in res.items():
            if not isinstance(v, Exception):
                v.raw["key"] = key
                v.raw["ncurves_total"] = len(C.segments(F[key]["contours"]))
                C.render(v.raw, os.path.join(a.out, fname(key) + "_curv.png"), "groupmove")
        for master in sorted({v.raw["master"] for v in good}):
            C.index_sheet([v.raw for v in good if v.raw["master"] == master], master,
                          os.path.join(a.out, "curv_index_%s.png" % master.replace(" ", "")), "groupmove")
        print("renders in", a.out)


def cmd_sheets(a):
    from . import render
    from .render import sets
    from .font import fname
    F = _load(a)
    os.makedirs(a.out, exist_ok=True)
    keys = _keys(F, a)
    kind = a.kind
    if kind == "grid":
        sets.grids(F, a.out)
    elif kind == "overview":
        for tag in F.tags:
            sets.overview(F, tag, os.path.join(a.out, "overview_group_%s.png" % tag))
    elif kind in ("parts", "groups", "combs"):
        for key in keys:
            out = os.path.join(a.out, "%s_%s.png" % (fname(key), {"parts": "parts", "groups": "groups", "combs": "curv"}[kind]))
            try:
                getattr(render, kind)(F[key], out) if kind != "combs" else render.combs(_move_of(F[key]), out)
                print("wrote", out)
            except Exception:
                print("FAIL", kind, key, traceback.format_exc()[-600:])
    elif kind == "serifs":
        for tag in F.tags:
            sets.serifs_sheet(F, tag, os.path.join(a.out, "serifs_%s.png" % tag))
    else:
        raise SystemExit("unknown --kind %s" % kind)


def _move_of(g):
    from . import move
    return move(g)


def cmd_vf(a):
    from . import build_variable_font
    F = _load(a)
    info = build_variable_font(F, a.out, axis=a.axis, erase_open_corners=not a.no_erase_open_corners, master=a.master,
                               glyphs=a.glyphs.split(",") if a.glyphs else None, reference_ttf=a.reference_ttf)
    print(json.dumps({k: info[k] for k in ("vf", "fvar", "glyphs", "glyphs_with_nonzero_deltas", "static_glyphs")}, indent=1, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="wmparts", description="parts pairing + contrast move (see RULES.md)")
    ap.add_argument("--version", action="version", version="wmparts " + __version__)
    sub = ap.add_subparsers(dest="verb", required=True)

    def common(p, out_required=True, out_help=""):
        p.add_argument("src")
        p.add_argument("-o", "--out", required=out_required, help=out_help)
        p.add_argument("--master-values", help="a masters.json replacing the file's / sidecar's master values")
        p.add_argument("--skip", default="", help="glyph names left out of all (comma list)")
        return p

    p = common(sub.add_parser("extract", help="a .glyphs / .glyphspackage -> set.json + masters.json"), out_help="set.json")
    p.add_argument("--glyphs", help="comma list (default every exporting glyph)")
    p.add_argument("--masters", help="master names, comma list (default all)")
    p.add_argument("--keep-components", action="store_true", help="reserved (issue #34)")
    p.set_defaults(fn=cmd_extract)
    p = common(sub.add_parser("masters", help="print / write the solver's master values"), out_required=False)
    p.set_defaults(fn=cmd_masters)
    p = common(sub.add_parser("pair", help="per-node readings"), out_help="readings dir")
    p.add_argument("--keys"); p.set_defaults(fn=cmd_pair)
    p = common(sub.add_parser("move", help="moved contours at t"), out_help="moved.json")
    p.add_argument("--keys"); p.add_argument("--t", type=float, default=1.0); p.set_defaults(fn=cmd_move)
    p = common(sub.add_parser("eval", help="curvature combs + crossings + rung checks"), out_help="curv dir")
    p.add_argument("--keys"); p.add_argument("--no-render", action="store_true"); p.set_defaults(fn=cmd_eval)
    p = common(sub.add_parser("sheets", help="render sheets"), out_help="sheets dir")
    p.add_argument("--kind", required=True, choices=["parts", "grid", "groups", "overview", "combs", "serifs"])
    p.add_argument("--keys"); p.set_defaults(fn=cmd_sheets)
    p = common(sub.add_parser("vf", help="variable font with a CNTR axis"), out_help="vf dir")
    p.add_argument("--master"); p.add_argument("--glyphs"); p.add_argument("--axis", default="CNTR")
    p.add_argument("--reference-ttf"); p.add_argument("--no-erase-open-corners", action="store_true")
    p.set_defaults(fn=cmd_vf)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
