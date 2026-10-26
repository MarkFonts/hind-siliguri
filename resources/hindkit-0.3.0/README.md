# Latin glyphs from hindkit 0.3.0

Hind Siliguri's Latin is Hind's. The 2015 build didn't keep it in this repo: hindkit 0.3.0's `import_glyphs()` merged it into the Bangla masters at build time from the copy bundled inside hindkit (see [itfoundry/hind-siliguri#8](https://github.com/itfoundry/hind-siliguri/issues/8)).

- Source: [itfoundry/hindkit](https://github.com/itfoundry/hindkit) `hindkit/resources/` at the 0.3.0 tag commit [`a9924452cd`](https://github.com/itfoundry/hindkit/tree/a9924452cddcc70dd8e9b338db5074e73722c681/hindkit/resources) (2015-10-17). This is the version `legacy/build.py` pins with `kit.confirm_version('0.3.0')`, released the same day as Hind Siliguri 1.000.
- That folder holds `Hind.glyphs` and the two UFO masters exported from it, `Hind-Light.ufo` and `Hind-Bold.ufo`, which `import_glyphs()` read. The UFOs and the Glyphs file draw the same outlines; only the start points of closed contours differ, the same way in both masters.

Since 2026-10-26 the 334 Latin glyphs live in `masters/HindSiliguri.glyphs` itself, copied from `Hind.glyphs` by `toolchain/merge_latin_into_glyphs.py`. As in 2015, the Bangla `space` wins over Hind's, and Hind's kerning, groups, and font info are not used. The vendored copies were removed then; they are in this repo's history (commit `85393a1`) and in hindkit at the commit above.

The glyphs are Hind's, by the Indian Type Foundry, under the SIL Open Font License like the rest of this family.
