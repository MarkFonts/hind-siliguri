# Hind Siliguri

Hind Siliguri is an open source typeface for Bangla and Latin, in five weights. Jyotish Sonowal designed the Bangla for the Indian Type Foundry, who first published the fonts in 2015. The Latin is Hind's, by Manushi Parikh and Satya Rajpurohit.

This is a fork of [itfoundry/hind-siliguri](https://github.com/itfoundry/hind-siliguri), whose last commit was the 1.000 release in October 2015. Google Fonts serves 1.001, a 2017 hotfix of those fonts. This fork ports the build to current tooling, the same way as the [Hind fork](https://github.com/MarkFonts/hind).

## Sources

`masters/HindSiliguri.glyphs` is the only source: two masters (Light, Bold) on a Weight axis and five instances. It holds 852 glyphs: the 485 Bangla, Hind's 334 Latin, a no-break space, and 32 GF Latin Core additions. It also holds the hand-written OpenType code. Until 2026-10-26 it was named `HindiSiliguri.glyphs`; Google Fonts' override config for this family still points at that name.

The Latin came from hindkit 0.3.0's bundled copy of Hind, which the 2015 build merged in at build time ([itfoundry/hind-siliguri#8](https://github.com/itfoundry/hind-siliguri/issues/8)). `resources/hindkit-0.3.0/README.md` has the provenance.

The GSUB is unchanged from 2015. It sits in three feature prefixes: `languagesystems`, `GSUB_lookups`, and `GSUB`. Mark positioning, GDEF, and the OS/2, hhea, and name tables are generated at build time. The nine combining marks carry the Glyphs category Mark, which gives GDEF the same mark class as 2015. The 2015 build, its feature files, and its OTFs are kept in `legacy/`.

## Building

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install afdko glyphsLib defcon fontTools
```

```bash
source .venv/bin/activate && python build.py
```

The venv's `bin` has to be on `PATH`, because hindkit calls `makeotf` and `makeinstancesufo` by name.

The build exports UFO masters from `HindSiliguri.glyphs` into `build/masters`, and the `GSUB_lookups` and `GSUB` prefixes into `build/features`. It then interpolates the five instances with AFDKO's `makeinstancesufo` and compiles OTFs with `makeotf`. Working files go to `intermediates/`, and the OTFs to `intermediates/products/HindSiliguri-<version>-OTF/`. `products/` gets a zip of the OTFs and TTX dumps, as ITF's Google Fonts builds did. `build.py --test` builds only the two master styles, skipping interpolation and overlap removal.

The build system is ITF's [hindkit](https://github.com/itfoundry/hindkit), vendored as a git subtree in `toolchain/hindkit` and patched for current AFDKO. See `toolchain/README.md`.

### Building with gftools

The `.glyphs` file also builds on its own with fontmake, which is what Google Fonts uses. `config.yaml` matches the override config Google Fonts keeps for this family:

```bash
gftools builder config.yaml
```

That writes a variable font (`wght` 300–700), plus static TTF, OTF, and WOFF2 files, to `fonts/`. Checked with gftools 0.10.4 and fontmake 3.12.2:

- **Matches the hindkit build:** the same glyphs, advance widths, and GSUB. Across the 5,493-string test below, every glyph sequence is identical in all five weights.
- **Outlines:** the same, apart from TrueType conversion and the overlaps fontmake leaves in place, for example in the ogonek letters.
- **Mark positioning:** ufo2ft writes it, not the 2015 Indic writer. It places marks differently in about 63 strings per weight. Three cases are improvements:
  - The reph lands over the consonant before ৢ and ৣ, where 2015 leaves it unattached, off to the right.
  - The candrabindu centers over ঢ়, which has its anchors only through its components.
  - The reph sits 34 units lower over ু for ten consonants.

  `proof/marks-hindkit-vs-gftools.svg` draws these cases from both builds.
- **Variable font:** shapes like the statics at each named weight.
- **File name:** gftools names the variable font after the source file: `HindSiliguri[wght].ttf`.

### Fontbakery

fontbakery 1.1.0's Google Fonts profile, run on the gftools build, gives these results:

| | Before | After |
|---|---|---|
| Variable font | 9 FAIL, 13 WARN | 2 FAIL, 9 WARN |
| Five statics | 39 FAIL, 72 WARN | 10 FAIL, 62 WARN |

The fixes are in the source. `toolchain/fontbakery_fixes_2026-10-26.py` applied them:

- **Contour order in ল্ফ (`bnL_PHA`) and ল্দ্র (`bnL_D_RA`).** The Bold master listed two small rectangles in the opposite order from Light, so in the middle weights each rectangle travelled to the other's place. SemiBold ল্দ্র came out as a filled block, here and on Google Fonts. `proof/fontbakery-fixes.svg` shows before and after.
- **Contour direction in ১, ২, and ৯.** These ran clockwise in both masters. Both masters were reversed alike, so they stay compatible.
- **Dotted circle anchors.** `dottedcircle` gets the headline and baseline anchors the consonants use, so candrabindu, ু, ূ, and ৃ attach to it.
- **No-break space.** `nbspace` (U+00A0) is added.
- **Font info:**
  - the copyright in Google Fonts' "Project Authors" form;
  - Indian Type Foundry as manufacturer;
  - fsType 0, typo metrics on, and vendor ITFO;
  - Bold style-linked to Regular;
  - the source renamed to match the family.
- **Vertical metrics:** Google Fonts' 1116/−501/0 (win 1116/501), which it has served since 2017, replace the 2015 values. The hindkit build uses them too.

**Still failing:** three GF Latin Core letters, Ħ ħ ẞ, which need drawing (`Hbar`, `hbar`, `Germandbls`). With the Latin Core work below, they're all fontbakery fails on: the variable font has 2 FAILs (coverage and German/Maltese shaping), and each static has the same two.

### GF Latin Core

`toolchain/latin_core_2026-10-26.py` added everything that didn't need drawing. It reads all its geometry from the font's own 98 accented letters:

- **16 composites:** Ċ ċ Ġ ġ Ŵ ŵ Ŷ ŷ Ẁ ẁ Ẃ ẃ Ẅ ẅ Ỳ ỳ, placed where the existing accented letters put the same accents.
- **Dotless ȷ:** `j` without its dot.
- **14 combining marks**, U+0300 to U+0328: zero-width components of the spacing accents, with `_top`, `_bottom`, or `_ogonek` anchors. The combining comma below is cut from Ș.
- **Anchors:** `top`, `bottom`, and (for A E I U) `ogonek` on A–Z, a–z, ı, and ȷ, plus the dotted circle. A base + combining mark renders the same as the precomposed letter, so e + U+0301 matches é.
- **`ccmp`** (the `Latin` feature prefix): i, j, and į drop their dot before a mark above, as in Dutch íj́ or Lithuanian į́. `iogonek.dotless` is new for the last.

Both builds have the additions. In the hindkit build no existing glyph changed, and shaping against 2015 is still identical. `proof/latin-plan/` holds the plan, the renders, and the drawing brief for Ħ ħ ẞ.

**Remaining warnings:**
- Outline polish: zero-length or colinear segments and near-vertical lines in a few dozen glyphs.
- Math-sign widths.
- An unencoded `ITF` logo glyph.
- The soft hyphen.
- Items Google Fonts sets on its side: article, meta table, and METADATA subsets.

### Matching the 2015 fonts

This build is version 1.002. Google Fonts' 1.001 ([google/fonts#893](https://github.com/google/fonts/pull/893)) is the 2015 OTFs converted to TrueType, with ttfautohint and vertical metrics of 1116/−501/0. This build uses those metrics (win 1116/501) rather than the 2015 1200/−800/0, so line spacing on Google Fonts doesn't change. They are custom parameters in the `.glyphs` file.

Against the 2015 OTFs, all five weights have the same glyphs (plus the no-break space) and advance widths. They shape identically across 5,493 test strings: every consonant with every vowel sign, every consonant + hasanta + consonant pair, reph and ya-, ra-, and ba-phala forms, digits, and Latin. Outlines match to within 0.5% of area, apart from the fix below. The remaining differences come from overlap removal and are a few units at most. Getting there needed:

- `round_like_python2`: instances are rounded half away from zero, as the Python 2 tools did, not half to even.
- `correct_contour_direction`, run after overlap removal: a few glyphs are drawn clockwise in the masters, `bnOne` among them.
- hindkit's default mark-to-mark positioning. The 2015 writer appended it to `abvm` and `blwm`, which is where reph and candrabindu stack over ু and ূ.
- Backup layers dropped at export, and the glyph order pruned of about 100 glyphs that were listed but never drawn.

### Fixed: ১ and four conjuncts in Regular, Medium, and SemiBold

The digit ১ (`bnOne`) is malformed in the middle weights on Google Fonts ([google/fonts#6037](https://github.com/google/fonts/issues/6037), [itfoundry/hind-siliguri#9](https://github.com/itfoundry/hind-siliguri/issues/9)), and so are হ্র (`bnH_RA`), ন্জ (`bnN_JA`), ন্ঠ (`bnN_TTHA`), and গ্দ্র (`bnG_D_RA`). In each, one contour starts at a different node in the Bold master than in Light. The point counts match, so the masters look compatible, but interpolation pairs the wrong nodes. In ১, the tail swings through the stem. Contour direction is not involved.

The Bold contours are rotated to start where Light's do. Both masters draw exactly as before; only the instances change. `proof/index.html` shows Google Fonts and this build side by side.

Name table records differ: hindkit's Google Fonts profile writes the version as `1.002`, the URL as indiantypefoundry.com, and a sample text, and drops the trademark line.
