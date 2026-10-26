# The wmparts ruleset (R1–R26)

This is the contract a plugin author reads. `wmparts.move()` raises a glyph's contrast by these rules and nothing
else. **No rule names a glyph or a node.** Every move falls out of three things: the *parts* (stem, serif or flag,
stroke, terminal, dot), the *measurement* (which nodes hold a thin part), and the *group logic* below. When a rule
changes, this file and the `groupmove.py` docstring change together; the R-numbers are stable.

Each rule ends with the answer from Mark's question paper (GRILL.md, answered in GRILL-ANSWERS.md, 2026-10-23) that
it generalizes, or with the round and Mark's words that produced it. Read an answer as one instance of the rule,
never as a special case: "Italic n, point 10 slides down the leg" became "a junction slides along the host wall" (R7).

Mark's method, in his words: a glyph is **parts**; each part is **two sides**; the Illustrator **blend** between the
two sides is the part, its 50% blend is the centerline, and the **node-to-node rungs** are the measurement. Stroke
beginnings have 3–10 unit blunt edges: a **START wall**, never paired. When a thin part is below the thickness
threshold, **pull away the points that hold it**, moving **groups** of points **as one piece**: no zigzags, no
per-point nudging. Node count, node order and handle count never change: the axis is deltas on the drawn points.

The per-glyph report (`Move.report()`, and the groups sheet `render.groups()`) lists the rules behind every group.
That sheet is the approval sheet: the solver proposes the groups, Mark approves them [11A].

## Measuring

Parts, rungs and holds come from `parts.py` / `mover.py` (CONTRAST-SPEC.md rules 3, 6, 7, 8, 9, 10/13, 20).

**R1 · Parts.** A stem (two straight sides at 0.75 stem weight or more, spec rule 3), any part that is nowhere thinner
than 0.75 stem weight (curved or not: a j's stem running into its tail), and a dot never grow. Flags and serifs never
move (spec rule 8). Every other stroke is a growing part. [7C]

**R2 · Amount.** A growing part gets the full move amount A at CNTR 100. Each side takes
A/2 × (1 − its own hold + its partner's hold) (spec rule 6). A surface facing a metric line holds (spec rule 7). The
width window of spec rule 2 no longer sets the amount. [7C: the x crescents get the full amount, not 3 units]

**R3 · Where.** Measured widths only decide which nodes HOLD the thin part. A node is a *core* when its width is at
most 1.25 × the part's thinnest, or at most 0.8 × the master's stem, or a clear local minimum along its side (at most
0.8 × both neighbors). A side closing to a point has no width; its tip never grows. [7C, 9B]

**R3b · A straight edge is one piece.** When a thin part's side runs on along ONE straight segment past its last rung
to a node, and that node's only other readings are end rungs of other growing strokes landing on the thin part (at
least 1.5 × thicker: a bowl or terminal curve meeting a bar), the node reads the junction, not a width. It joins the
thin part and moves with it. A cut face's node is a terminal, never this. (Round 5: a crossbar's lower edge stays
parallel instead of growing as a wedge.)

## Groups

**R4 · A group** is a run of consecutive core nodes on one side of one stroke. It moves as ONE rigid piece by ONE
vector, handles traveling with their nodes. A run is split where the shares turn against each other; the two sides
of a stroke never share a group. [1C: the arch's 1, 4 and 7 move together; 11A]

**R5 · Direction.** The share-weighted stroke normal (perpendicular to the mean of the two sides' tangents), snapped
to x, y, the italic angle, or a straight edge beside the run (edges up to 45° off, the rest up to 35°). When the run's
two ends have straight edges leaning to opposite sides by about the same angle (mirror images: a bar between two
beaks) and the run has two nodes or more, neither is followed. The snap that disturbs least wins: angle off the
normal + width change of carried nodes + how much a sliding end bends its segment + 1 for every stop at a free node.
Magnitude: the largest core share / cos(snap angle), so the thinnest rung still gets its full growth.
[2A: the Black Italic arch moves along the leg edge; 5A]

**R6 · Carry.** Walking out of the run, a node the vector runs ALONG (|v · normal| ≤ sin 25°) is carried at the full
amount when it is at most 2 × the core's width, or when the segment to it is shorter than 2 × the move (it cannot
absorb the move). [1C, 5A]

**R7 · Slide.** A node whose next segment is a straight edge slides along that edge by the part of the vector running
along it (at most 3/4 of the edge), so the edge stays on its drawn line; the group ends there. This holds outside the
part too: where an arch leaves a stem, the junction slides down the stem. [1C, 3A: point 10 slides down the leg; 5A]

**R8 · Grade.** A node not carried joins with a reduced share, in the same direction, by its width against the core:
up to 2.2 × → 2/3, up to 3 × → 1/3, thicker → anchor. The taper continues outward and never rises.
[8B: the v arm's 11 moves somewhat less than 14; 9B]

**R8b · Held flags stay.** A held flag's nodes never move for a growing part beneath it. Where a bar runs under a held
wedge or beak, only the bar's own end node slides (up to the edge's far end); the serif's node stays even if that
leaves a dart inside the serif. crosscheck reports a fold inside a held serif as *info*, not a cross. (Mark, round 6:
darts in the T's serif "will not affect the final build".) On a straight side R24 replaces this.

**R9 · Anchors.** A walk stops at: a node held by a metric line, a held flag node, a junction, a node of another
stroke outside its span, a free node it can neither carry nor grade, and a node standing alone between two groups
(it belongs to neither and stays). [9B: the e's 9 stays]

**R10 · Junctions.** A thin side arriving at another part's wall (a stem side at a corner, a START blunt, any blunt of
25 units or less, a flag edge) slides along that wall to where its moved edge meets it, capped at 1.6 × its share
(spec rule 15) and 3/4 of the wall segment; along a held flag edge only by the edge's far end (round 8). A blunt
travels with it as one piece. When the core of a group is such a junction, the group's other nodes move WITH it, by
their grade × the junction's own slide. [8B]

**R11 · Terminals.** Where a group runs into a thin cut face (a face wider than 0.75 stem is a stem's foot and anchors
the walk instead), the end slides along the face line: the stroke never lengthens (spec rule 9). A short blunt (25
units or less, under half the stroke's width there) before a straight end face moves as one piece along that face. A
face running with the move keeps up with the group (|v| / cos); a face across the move moves to where the moved edge
meets it. [5A: the cut end slides along itself; 6B: the r's end face slides along its own line, the blob keeps its shape]

**R12 · Lone cut faces.** A thin cut face (under 0.75 stem weight) that no group reaches opens along itself by its own
share (spec rule 9). A counter tip pushed both ways takes the sum of the pushes.

**R13 · Segments keep their direction.** Every segment keeps at least 1/4 (straight) or 1/2 (curve) of its chord
along its drawn direction. The ends that slide (slides, junctions, blunts, terminals, cut faces, tips) give back
proportionally; group nodes never do.

## Curves

**R14 · Connecting curves.** A segment whose two ends moved by the same vector translates. A CONNECTING segment (ends
moved differently) is the drawn curve turned and scaled as one piece onto its new chord (a similarity: both handles
go with it). [4C]

**R15 · Smooth stays smooth.** A straight edge wins (spec rule 12). Otherwise the handle on the untransformed side is
rotated onto the transformed side's tangent, keeping its length; a node between two transformed segments keeps its
drawn tangent. Every realignment is listed in the report. [4C]

**R16 · The axis.** Every node and handle moves linearly from drawn (CNTR 0) to moved (CNTR 100). Node count, order
and handle count never change. [10D; Mark: "I have never wanted vector structure / number of nodes / handles to
change: these are a variable axis with the original letters."]

## Other typefaces (round 4: Marya, Geist Serif)

The detectors behind these are stated in `rungs.py` and `parts.py`.

**R17 · Balls.** A ball or teardrop terminal never grows. Its nodes move as one piece by the stroke end's own move,
taken along the stroke (like R11's end faces); a group's walk stops at it. [6B]

**R18 · Slab serifs are flags** (R1: they never move). The stroke's side runs on under the bracket to the slab, and
the bracket's root node slides along the held bracket like any side along a held serif edge (R10; round 8: up to the
edge's far end). Tried and rejected: the root moving with the stroke and the bracket reshaping (a 15-unit-deep bracket
under a 25-unit move folds).

**R19 · Buried walls** (an edge whose outside is another contour's ink) are not surfaces: never paired, never
measured, never moved by a group.

**R20 · Buried STARTs.** A growing side that runs on into another part's ink and comes back to that part's edge by a
hairpin is the side's START, whatever its length or how the parts table read it. The junction and the hairpin's far
node travel as ONE piece along that host edge, by the slide that puts the side on its moved line, also when the host
is a held flag edge (the far node stays on the flag's drawn line; round 8: up to the edge's far end). The fold under
the host keeps its drawn shape instead of stretching from one end. A host that grows itself is left to its own group.
(Round 5: before, only the junction slid and a drawn 5-unit sliver opened into a 12-unit triangle.)

**R21 · Node-less end parts.** A stroke's end part that runs from a junction node to its end face as ONE curve (the
junction reading at least 2 × both its neighbors) grows through its handles: each handle of the junction-to-end curve
whose foot reads under 0.9 × the junction moves by the side's own growth there, along the stroke normal. Its end
face opens by its own share (R12); the junction stays with its own part. (Round 5: before, the bar's end followed the
eye's group down and the bar barely grew.)

## Rounds 6–8

**R22 · A counter's ROUND corner rides with the bar** (round 8, scoped). Where a growing straight side (R24) flows
without a corner into a drawn ROUND (one curve turning 60–120°, chord at most half the side, radius at least the
side's width, its far node smooth and running into the counter's wall at 50–130°) that bounds a COUNTER, the round
moves as ONE rigid piece with the side, along the bisector of side and wall, by the side's amount / cos(bisector to
the side's normal), so its drawn clearance is kept. A sharp end with a hairpin spur is not a round (it rides with the
side, R24); a hook's open cup is never a counter. Mark: "counters fit, hooks overlap" (he approved this look on the
Marya roman e, 2026-10-24).

**R23 · No thinning.** A group never makes a rung of its own part shorter than drawn. A walk stops at a node the vector
would push toward its partner (round a bowl that turns more than about 90°), and a snap direction that shortens any
rung of the part by more than 15% of the move (at least 1.5 units) pays for it in the R5 cost. (Round 6: one vector
round a c's inner side made its bottom 12 units thinner.) `Verdict.thinning` lists what is left.

**R24 · A straight side moves as ONE rigid lateral translation** (spec rule 18; round 7, Mark: the strokes were "not
moving laterally the correct amount for BOTH parts of the stem"). A straight side is a run of segments whose nodes and
handles lie within 3 units of one line, all running the same way, at least 50 units long, that a growing part's side
runs along and its rungs measure; a serif's own edges are never part of one. The whole side translates across itself
by ONE amount, the same at both ends: its share with the holds decided for the side as a whole (their mean, or the
stricter end when the side touches a metric line or a flag). A thick straight side holds; groups slide along it (R7).
Each end follows the translated line: two straight sides meet where both translated lines cross; an end at a held
serif, flag, beak or bracket edge goes to where the translated line meets that edge (the serif's own nodes do not
move; a START sliver drawn under it travels with the end node); an end at another part's wall slides along that wall;
an end at a cut face slides along the face; an end where the side runs on moves straight across. When an end cannot
reach the translated line within its cap, the WHOLE side takes the smaller amount, and a group holding a node of that
side takes the same reduction. Curved sides keep R4–R23. `Verdict.tilts` must be empty.
*Cap* (round 8, Mark: "relax the serif slide cap so the bar reaches its full amount; the serif edge may shorten
more"): along a held serif edge the end goes wherever the translated line meets it, limited only by the edge's far end
(stopping min(2 units, 1/4 edge) short: "capped at serif tip" in the report). Another part's wall keeps 3/4 of the
wall and 1.6 × the share ("capped by wall"). A short spur (25 units or less) at a cut end travels with the end.

**R25 · (off since round 8)** A counter's corner node never moves. Replaced by the scoped R22; Mark's node-18 request
was about the Marya roman e, misread from an unlabeled sheet. `RULE_SWITCHES["R25"] = True` turns it back on for
comparison.

**R26 · A growing part's end at a stem.** Where a growing part ends against a part that never grows (R1: a stem, a
stem-weight straight leg), its end rung reads across the stem: a node of that rung on one of the stem's straight sides
is the stem's, never a core. The stem's sides hold; the part's group reaches that node only by sliding it along the
stem's side (R7). (Round 8: an n's arch end rung read 85 units, within 1.25 × the 73-unit arch, so the leg's outer side
moved 12.7 units.)

## Switches

`wmparts.RULE_SWITCHES` (the `groupmove.RULES` dict) exists for before/after comparisons only; every rule is on by
default and the regression counts assume the defaults:

| switch | default | effect |
|---|---|---|
| `R22` | on | the scoped round-corner rule |
| `R25` | off | the old corner anchor |
| `R26` | on | stem-end rungs |
| `bracket_rides` | off | a tangent bracket rides along a straight held serif edge as one rigid piece (moves a serif node, so R8b forbids it; shown to Mark in round 8, his call) |

## Acceptance

Mark judges by eye at CNTR 20 / 50 / 100, by curvature combs, and by straight-line travel [10D]. In code:
`wmparts.evaluate(move)` gives clean / minor / snapped / cross, `tilts` (R24) and `thinning` (R23). The regression in
`tests/test_regression.py` holds the round-8 counts for the three faces.
