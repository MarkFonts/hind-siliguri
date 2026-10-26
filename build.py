#! /usr/bin/env python3
# Hind Siliguri, built with hindkit (toolchain/hindkit) and current AFDKO from masters/HindiSiliguri.glyphs.
# Follows the Hind fork's build.py (MarkFonts/hind). The 2015 hindkit 0.3 build is in legacy/.

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "toolchain", "hindkit", "lib"))

import defcon
import glyphsLib
from glyphsLib.classes import WEIGHT_CODES
from fontTools.designspaceLib import DesignSpaceDocument
import hindkit

SOURCE = "masters/HindiSiliguri.glyphs"
EXPORT_DIR = "build/masters"
LATIN_DIR = "resources/hindkit-0.3.0"

def export_masters():
    """HindiSiliguri.glyphs -> UFO masters for hindkit. Anchors are not propagated, as in the 2015 build."""
    hindkit.remove(EXPORT_DIR)
    hindkit.makedirs(os.path.dirname(EXPORT_DIR))
    font = glyphsLib.GSFont(SOURCE)
    # Drop the 2015 backup layers: they never reach the fonts, and two in bnCHA share a name, which glyphsLib rejects.
    for glyph in font.glyphs:
        for layer in [l for l in glyph.layers if l.layerId != l.associatedMasterId]:
            del glyph.layers[layer.layerId]
    exported = glyphsLib.build_masters(
        font, EXPORT_DIR,
        designspace_path = os.path.join(EXPORT_DIR, "HindSiliguri.designspace"),
        propagate_anchors = False,
        generate_GDEF = False,
    )
    return DesignSpaceDocument.fromfile(exported.designspace_path)

def import_latin(designspace):
    """hindkit 0.3.0's import_glyphs(): add the Hind Latin glyphs the masters don't already have.

    The Bangla master wins on a name clash (only `space`). Kerning, groups, and info stay Bangla.
    """
    for ds_source in designspace.sources:
        receiver = defcon.Font(ds_source.path)
        source = defcon.Font(os.path.join(LATIN_DIR, "Hind-{}.ufo".format(ds_source.styleName)))
        for name in source.keys():
            if name not in receiver:
                receiver.insertGlyph(source[name])
        # The glyphOrder parameter lists ~100 glyphs that were never drawn; WriteFeaturesMarkFDK trips on them.
        receiver.glyphOrder = [name for name in receiver.glyphOrder if name in receiver]
        receiver.save()

def main():

    source = glyphsLib.GSFont(SOURCE)
    designspace = export_masters()
    import_latin(designspace)

    family = hindkit.Family(
        trademark = source.familyName,
        script_name = "Bangla",
        append_script_name = False,
        client_name = "Google Fonts",
        initial_release_year = 2015,
    )
    family.set_masters([(m.name, m.axes[0]) for m in source.masters])
    family.set_styles([(i.name, i.axes[0], WEIGHT_CODES[i.weight]) for i in source.instances if i.exports])

    for master, ds_source in zip(family.masters, designspace.sources):
        master._filename = os.path.splitext(os.path.basename(ds_source.path))[0]

    i = family.info
    i.openTypeNameDesigner = source.designer
    p = source.customParameters
    i.openTypeHheaAscender, i.openTypeHheaDescender, i.openTypeHheaLineGap = p["hheaAscender"], p["hheaDescender"], p["hheaLineGap"]
    i.openTypeOS2TypoAscender, i.openTypeOS2TypoDescender, i.openTypeOS2TypoLineGap = p["typoAscender"], p["typoDescender"], p["typoLineGap"]
    i.openTypeOS2WinAscent, i.openTypeOS2WinDescent = p["winAscent"], p["winDescent"]

    project = hindkit.Project(
        family,
        fontrevision = "1.002",
        options = {
            "prepare_mark_positioning": True,
            "round_like_python2": True,
            "correct_contour_direction": True,
            "do_style_linking": True,
            "additional_unicode_range_bits": [0, 1, 2],
            "use_os_2_version_4": True,
                "prefer_typo_metrics": True,
                "is_width_weight_slope_only": True,
        },
    )
    project.build()

# --- Overriding ---

hindkit.Project.directories["masters"] = EXPORT_DIR
hindkit.Project.directories["output"] = ""

# --- Executing ---

main()
