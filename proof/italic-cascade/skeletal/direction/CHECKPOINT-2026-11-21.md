# Hind Siliguri oblique: checkpoint, 2026-11-21

A checkpoint of the oblique (slanted, not cursive) masters work for Light and Bold at 14.04 degrees, taken when the
transforms on d, g, n and o were confirmed as the set to keep. It is work in progress, not a release, and nothing here
has been built into the font sources.

## What the letters are

`working_base_2026-11-21.json` holds the outline of every glyph the work covers (154 per weight: Latin, figures,
punctuation, 49 Bengali letters), as contours of `[x, y, type, smooth]` points in the source's own point order.
`round_all_base_2026-11-21_foot-bpdqg.pkl` is the same thing as the scripts read it. In order, the letters are:

1. the plain slant;
2. the round solve (`round_solve.py`): every quarter of a round, outside and counter, scaled about its own corner as
   the o is; a bowl cut by a stem or an ending is moved as the whole round and cut again on the straight it meets;
3. the build's later steps (not in this commit, see below): straights, cut handles, lower terminal, notch;
4. the notes of 2026-11-20 (`straights.py`, `round_solve.py`): a diagonal keeps the roman's relation to its stem,
   upright stems lose 3%, a curve running smoothly into a straight counts as a quarter, a taper does not;
5. the foot, on d and g only: the bowl's lower right beside the stem stays on the plain slant;
6. the picked points of the a (`picks_2026-11-20_light.txt`), applied exactly in the Light and in proportion in the Bold.
7. the m and n (`picks_2026-11-21_m_n.txt`, `picks_exact.py`): one held point on the Bold m; the Bold n's arch takes
   the Bold m's arch, and the Light n's arch takes the Light h's, point for point;
8. the foot on p, d, q, g and b (second commit, see below). Steps 1 to 7 are the letters of the text proof of
   2026-11-21; step 8 changes only those five letters.

Earlier states are kept beside it: `round_all_2026-11-20_sent.pkl` (step 3), `round_all.pkl` (step 4),
`round_all_base_2026-11-21.pkl` (step 5), `round_all_base_2026-11-21_picks.pkl` (step 6),
`round_all_base_2026-11-21_mn3.pkl` (step 7).

## The foot on p, d, q, g and b (second commit)

Where a bowl runs into a stem at its lower right (d, q, g) or its upper left (b, p), the round solve squeezes that
quarter toward its corner and the notch between bowl and stem closes. Step 5 answered this on d and g by keeping the
whole quarter, outside and counter, on the plain slant; that left the counter's top turned and its bottom not.

Step 8 replaces it on all five letters:

- the counter turns in full, like the o's counter, so its top and bottom match;
- on the outside, only the one point hidden under the stem stays on the plain slant; the outside's bottom (or top)
  point slides with the counter's, so the stroke keeps its weight.

It costs a little: the stroke at the join is a few units thinner, and the notch sits a little lower than with the
whole quarter held (but far higher than with no foot). b and p take the upper left because a slanted b is a slanted
q turned half round, and a slanted p is a slanted d turned half round.

Switches in `round_solve.py`: `FOOT_DIRS="SE NW"` (lower right and upper left), `FOOT_POINT=1` (hold the point, not
the quarter), `FOOT_COUNTER=0` (the counter is left to turn). `foot_variant.py` rebuilds named letters over a base.

Views used to judge it: `transforms_of.py` (what each step does to each point), `comb_sheet.py` (curvature combs on
the counters, blinking), `round_sheet.py` with `FRAMES` (any number of blink frames).

Not in this commit: a first look at the same rule on Bengali letters. It changes very little there and is not taken.

## Switched off, on purpose

`round_solve.py` also carries four later experiments behind switches that are OFF in this checkpoint: the bar move
(`BAR`), a fixed share for shared points (`KEEP`), one reading per letter applied by point (`SAME`), and no joint
evening. They were rolled back on 2026-11-21 because too much changed at once.

## To rebuild the letters

    FOOT=1 FOOT_ONLY="d g" PKL=round_all_base_2026-11-21.pkl python round_all.py
    python picks_onto_base.py picks_2026-11-20_light.txt
    python picks_exact.py picks_2026-11-21_m_n.txt <base.pkl> <out.pkl> Bold      (the m; the n arches were copied as the file's notes say)
    FOOT=1 FOOT_ONLY="b p d q g" FOOT_DIRS="SE NW" FOOT_POINT=1 FOOT_COUNTER=0 \
        python foot_variant.py round_all_base_2026-11-21_mn3.pkl round_all_base_2026-11-21_foot-bpdqg.pkl b p d q g

## What is not in this commit

The scripts here import an older set of build modules (`cascade`, `stored`, `diag`, `cand`, `trusted`, `l_build` and
others) and a state file with the upright outlines. Those stay in the ignored working folder, so this commit records
the method and the result but does not run by itself. Fonts, PDFs, proof sheets and reference material are not here
either.
