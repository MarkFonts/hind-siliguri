# Latin glyphs from hindkit 0.3.0

Hind Siliguri's Latin is Hind's. The 2015 build didn't keep it in this repo: hindkit 0.3.0's `import_glyphs()` merged it into the Bangla masters at build time from the copy bundled inside hindkit (see [itfoundry/hind-siliguri#8](https://github.com/itfoundry/hind-siliguri/issues/8)). The files here are that copy, unchanged.

- Source: [itfoundry/hindkit](https://github.com/itfoundry/hindkit) `hindkit/resources/` at the 0.3.0 tag commit [`a9924452cd`](https://github.com/itfoundry/hindkit/tree/a9924452cddcc70dd8e9b338db5074e73722c681/hindkit/resources) (2015-10-17). This is the version `legacy/build.py` pins with `kit.confirm_version('0.3.0')`, released the same day as Hind Siliguri 1.000.
- `Hind-Light.ufo`, `Hind-Bold.ufo`: what `import_glyphs()` read. 336 glyphs each, exported from Glyphs.
- `Hind.glyphs`: their Glyphs source, for reference. The build doesn't read it.
- `hindkit-LICENSE.txt`: hindkit's MIT license. The glyphs themselves are Hind's, by the Indian Type Foundry, under the SIL Open Font License like the rest of this family.

`build.py` merges them as `import_glyphs()` did: every glyph the Bangla master lacks is copied in with its outlines, components, and anchors. The only name in both is `space`, and the Bangla master's wins. Kerning, groups, and font info are not imported. The result is the 2015 glyph set of 819 glyphs.
