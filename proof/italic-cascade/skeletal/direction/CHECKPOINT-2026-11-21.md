# Hind Siliguri oblique: checkpoint, 2026-11-21

A checkpoint of the oblique (slanted, not cursive) masters work for Light and Bold at 14.04 degrees, taken when the
transforms on d, g, n and o were confirmed as the set to keep. It is work in progress, not a release, and nothing here
has been built into the font sources.

## What the letters are

`working_base_2026-11-21.json` holds the outline of every glyph the work covers (154 per weight: Latin, figures,
punctuation, 49 Bengali letters), as contours of `[x, y, type, smooth]` points in the source's own point order.
`round_all_base_2026-11-21_picks.pkl` is the same thing as the scripts read it. In order, the letters are:

1. the plain slant;
2. the round solve (`round_solve.py`): every quarter of a round, outside and counter, scaled about its own corner as
   the o is; a bowl cut by a stem or an ending is moved as the whole round and cut again on the straight it meets;
3. the build's later steps (not in this commit, see below): straights, cut handles, lower terminal, notch;
4. the notes of 2026-11-20 (`straights.py`, `round_solve.py`): a diagonal keeps the roman's relation to its stem,
   upright stems lose 3%, a curve running smoothly into a straight counts as a quarter, a taper does not;
5. the foot, on d and g only: the bowl's lower right beside the stem stays on the plain slant;
6. the picked points of the a (`picks_2026-11-20_light.txt`), applied exactly in the Light and in proportion in the Bold.

Earlier states are kept beside it: `round_all_2026-11-20_sent.pkl` (step 3), `round_all.pkl` (step 4),
`round_all_base_2026-11-21.pkl` (step 5).

## Switched off, on purpose

`round_solve.py` also carries four later experiments behind switches that are OFF in this checkpoint: the bar move
(`BAR`), a fixed share for shared points (`KEEP`), one reading per letter applied by point (`SAME`), and no joint
evening. They were rolled back on 2026-11-21 because too much changed at once.

## To rebuild the letters

    FOOT=1 FOOT_ONLY="d g" PKL=round_all_base_2026-11-21.pkl python round_all.py
    python picks_onto_base.py picks_2026-11-20_light.txt

## What is not in this commit

The scripts here import an older set of build modules (`cascade`, `stored`, `diag`, `cand`, `trusted`, `l_build` and
others) and a state file with the upright outlines. Those stay in the ignored working folder, so this commit records
the method and the result but does not run by itself. Fonts, PDFs, proof sheets and reference material are not here
either.
