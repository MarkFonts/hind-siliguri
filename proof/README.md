# Proof: this build against Google Fonts

`index.html` sets Google Fonts' Hind Siliguri 1.001 (`fonts/gf/`, from google/fonts `ofl/hindsiliguri/`) next to this build's 1.002 (`fonts/new/`) in all five weights: the digits ০–৯, the five glyphs fixed by matching start points, the ষ conjuncts, and running text. Serve the folder, for example with `python3 -m http.server -d proof`, and open it. The two SVGs are outline sheets of the same glyphs.

`compare.py` produced the numbers below. It compares glyph sets, advance widths, outline areas, and bounding boxes, and shapes 5,493 strings with HarfBuzz: independent vowels and consonants; every consonant with every vowel sign and with candrabindu, anusvara, and visarga; every consonant + hasanta + consonant pair; three-consonant clusters with vowel signs; reph on every consonant, alone, with every vowel sign, and with candrabindu; ya-, ra-, and ba-phala on every consonant, with vowel signs; digits and currency signs; sentences; and printable ASCII and Latin-1 text.

## Results, Google Fonts 1.001 against 1.002

| | Light | Regular | Medium | SemiBold | Bold |
|---|---|---|---|---|---|
| Glyphs | 821 / 819 | 821 / 819 | 821 / 819 | 821 / 819 | 821 / 819 |
| Advance widths that differ | 0 | 0 | 0 | 0 | 0 |
| Shaped strings that differ (of 5,493) | 0 | 0 | 0 | 0 | 0 |
| Outlines changed by the start-point fix | 0 | 5 | 5 | 5 | 0 |
| Largest other outline difference (area) | 0.92% | 0.71% | 0.54% | 0.50% | 0.50% |

Differences, grouped by cause:

1. **The start-point fix.** `bnOne` (১), `bnH_RA` (হ্র), `bnN_JA` (ন্জ), `bnN_TTHA` (ন্ঠ), and `bnG_D_RA` (গ্দ্র) change in Regular, Medium, and SemiBold, by 3.5% to 94% of their area. These are the intended fixes. Light and Bold are the masters and are unchanged.
2. **Contour direction.** `bnOne` is drawn clockwise in both masters, and Google Fonts' Light and Bold keep that. This build winds it the standard way. It renders the same.
3. **TrueType conversion.** Google Fonts converted the 2015 OTFs to quadratic outlines. Small round glyphs (period, parentheses, tilde, ellipsis, `bnIsshar`) differ by up to 0.92% of their area. Against the 2015 OTFs themselves, every glyph except the five fixes matches to within 0.5%, with a median difference of 0.004%, from current overlap removal.
4. **Glyphs only in Google Fonts.** `.null` and `nonmarkingreturn`, added by the TrueType conversion.
5. **Font-wide metadata.**
   - Vertical metrics: Google Fonts' 2017 hotfix uses 1116/−501/0, with win 1116/501. This build keeps the 2015 1200/−800/0, with win 1200/800.
   - `fsSelection`: Google Fonts clears the WWS bit. This build sets it, as in 2015.
   - Hinting: Google Fonts is TrueType with ttfautohint. This build is unhinted CFF, as in 2015.
   - Name table: hindkit's Google Fonts profile writes the version as `1.002` (not `Version 1.002`), the URL as indiantypefoundry.com, and a Bangla sample text, and drops the trademark line. The copyright reads 2015–2026.

The Google Fonts TTFs are the 2015 OTFs: against the OTFs in `legacy/build-2015/`, only the eight small round glyphs from item 3 differ.
