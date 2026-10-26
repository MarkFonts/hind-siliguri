# Toolchain

Hind Siliguri builds with `hindkit/` and current AFDKO (see `../build.py` and the top-level README). The 2015 build used hindkit 0.3.0's `Builder`, AFDKO 2.5's `makeInstancesUFO`, and Python 2. It is kept in `../legacy/build.py`.

## hindkit

`hindkit/` is [itfoundry/hindkit](https://github.com/itfoundry/hindkit) at master (2019-09-02, `553654362f`), added as a squashed `git subtree`, the same commit and patches as the [Hind fork](https://github.com/MarkFonts/hind). Update with

```bash
git subtree pull --prefix=toolchain/hindkit https://github.com/itfoundry/hindkit.git master --squash
```

### Local patches

These are needed for AFDKO 5 and to match the 2015 fonts:

- `objects/family.py`: the designspace is written with `fontTools.designspaceLib`, with real axes. AFDKO 5's `makeinstancesufo` rejects MutatorMath's axis-less format.
- `objects/font.py`: `updateInstance(path, options)`; AFDKO 5 swapped the arguments.
- `objects/family.py`, `objects/font.py`, `objects/project.py`: two new options, both off by default.
  - `round_like_python2`: interpolate unrounded, then round half away from zero, as the Python 2 FDK did. Widths are re-interpolated from the masters, because `makeinstancesufo` rounds them half to even even with `-r`.
  - `correct_contour_direction`: run defcon's `correctContourDirection` on each instance after overlap removal, on the overlap-free outlines `checkoutlinesufo` writes to the `com.adobe.type.processedglyphs` layer. The default layer stays as it is, because `makeotf` checks it against the hashes `checkoutlinesufo` stored and silently writes nothing if they differ.

The Hind fork runs `correct_contour_direction` before overlap removal. That works for Hind but not here. On overlapping contours, defcon takes the ষ diagonal for a counter, reverses it, and the overlap cancels out, leaving white slivers in 18 ষ conjuncts. The 2014 `checkoutlines` also fixed direction after removing overlaps.

## Latin

`../resources/hindkit-0.3.0/` holds the Hind Latin that hindkit 0.3.0 merged in at build time. Its README has the provenance.
