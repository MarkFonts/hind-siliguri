# Hind Siliguri

Hind Siliguri is an open source typeface for Bangla and Latin, in five weights. Jyotish Sonowal designed the Bangla for the Indian Type Foundry, who first published the fonts in 2015. The Latin is Hind's, by Manushi Parikh and Satya Rajpurohit.

This is a fork of [itfoundry/hind-siliguri](https://github.com/itfoundry/hind-siliguri), whose last commit was the 1.000 release in October 2015. Google Fonts serves 1.001, a 2017 hotfix of those fonts. This fork ports the build to current tooling, the same way as the [Hind fork](https://github.com/MarkFonts/hind).

## Sources

`masters/HindiSiliguri.glyphs` is the source: two masters (Light, Bold) on a Weight axis and five instances. It holds the 485 Bangla glyphs.

The Latin glyphs live in `resources/hindkit-0.3.0/`. The 2015 build merged them in from hindkit 0.3.0's bundled copy of Hind ([itfoundry/hind-siliguri#8](https://github.com/itfoundry/hind-siliguri/issues/8)). That folder's README has the provenance.

OpenType features are written by hand in `features/` (`GSUB.fea`, `GSUB_lookups.fea`), unchanged from 2015 except for the file split. Mark positioning, and the OS/2, hhea, and name tables, are generated at build time by hindkit. The 2015 build, its feature files, and its OTFs are kept in `legacy/`.

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

The build exports UFO masters from `HindiSiliguri.glyphs` into `build/masters` and adds the Latin. It then interpolates the five instances with AFDKO's `makeinstancesufo` and compiles OTFs with `makeotf`. Working files go to `intermediates/`, and the OTFs to `intermediates/products/HindSiliguri-<version>-OTF/`. `products/` gets a zip of the OTFs and TTX dumps, as ITF's Google Fonts builds did. `build.py --test` builds only the two master styles, skipping interpolation and overlap removal.

The build system is ITF's [hindkit](https://github.com/itfoundry/hindkit), vendored as a git subtree in `toolchain/hindkit` and patched for current AFDKO. See `toolchain/README.md`.

### Matching the 2015 fonts

This build is version 1.002. Google Fonts' 1.001 ([google/fonts#893](https://github.com/google/fonts/pull/893)) is the 2015 OTFs converted to TrueType, with ttfautohint and vertical metrics of 1116/−501/0. This build keeps the 2015 metrics (1200/−800/0, win 1200/800) for now. They are custom parameters in the `.glyphs` file.

Against the 2015 OTFs, all five weights have the same 819 glyphs and advance widths. They shape identically across 5,493 test strings: every consonant with every vowel sign, every consonant + hasanta + consonant pair, reph and ya-, ra-, and ba-phala forms, digits, and Latin. Outlines match to within 0.5% of area, apart from the fixes below. The remaining differences come from overlap removal and are a few units at most. Getting there needed:

- `round_like_python2`: instances are rounded half away from zero, as the Python 2 tools did, not half to even.
- `correct_contour_direction`, run after overlap removal: a few glyphs are drawn clockwise in the masters, `bnOne` among them.
- hindkit's default mark-to-mark positioning. The 2015 writer appended it to `abvm` and `blwm`, which is where reph and candrabindu stack over ু and ূ.
- Backup layers dropped at export (two in `bnCHA` share a name, which glyphsLib rejects), and the glyph order pruned of about 100 glyphs that were listed but never drawn.

Name table records differ: hindkit's Google Fonts profile writes the version as `1.002`, the URL as indiantypefoundry.com, and a sample text, and drops the trademark line.
