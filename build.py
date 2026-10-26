#! /usr/bin/env python3
# Hind Siliguri, built with hindkit (toolchain/hindkit) and current AFDKO from masters/HindSiliguri.glyphs.
# Follows the Hind fork's build.py (MarkFonts/hind). The 2015 hindkit 0.3 build is in legacy/.

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "toolchain", "hindkit", "lib"))

import defcon
import glyphsLib
from glyphsLib.classes import WEIGHT_CODES
from fontTools.designspaceLib import DesignSpaceDocument
import hindkit

SOURCE = "masters/HindSiliguri.glyphs"
EXPORT_DIR = "build/masters"
FEATURES_DIR = "build/features"

def export_masters(font):
    """HindSiliguri.glyphs -> UFO masters for hindkit. Anchors are not propagated, as in the 2015 build."""
    hindkit.remove(EXPORT_DIR)
    hindkit.makedirs(os.path.dirname(EXPORT_DIR))
    # The 2015 backup layers never reach the fonts.
    for glyph in font.glyphs:
        for layer in [l for l in glyph.layers if l.layerId != l.associatedMasterId]:
            del glyph.layers[layer.layerId]
    exported = glyphsLib.build_masters(
        font, EXPORT_DIR,
        designspace_path = os.path.join(EXPORT_DIR, "HindSiliguri.designspace"),
        propagate_anchors = False,
        generate_GDEF = False,
    )
    designspace = DesignSpaceDocument.fromfile(exported.designspace_path)
    # The glyphOrder parameter lists ~100 glyphs that were never drawn; WriteFeaturesMarkFDK trips on them.
    for ds_source in designspace.sources:
        ufo = defcon.Font(ds_source.path)
        ufo.glyphOrder = [name for name in ufo.glyphOrder if name in ufo]
        ufo.save()
    return designspace

def export_features(font):
    """The hand-written GSUB lives in the .glyphs file's prefixes; hindkit reads it as GSUB_lookups.fea and GSUB.fea.

    The `languagesystems` prefix is for builds straight from the .glyphs file; hindkit writes its own.
    """
    hindkit.remove(FEATURES_DIR)
    hindkit.makedirs(FEATURES_DIR)
    for name in ["GSUB_lookups", "GSUB"]:
        with open(os.path.join(FEATURES_DIR, name + ".fea"), "w", encoding="utf-8") as f:
            f.write(font.featurePrefixes[name].code)

def main():

    source = glyphsLib.GSFont(SOURCE)
    export_features(source)
    designspace = export_masters(glyphsLib.GSFont(SOURCE))

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
    i.copyright = source.copyright
    p = source.customParameters
    i.openTypeHheaAscender, i.openTypeHheaDescender, i.openTypeHheaLineGap = p["hheaAscender"], p["hheaDescender"], p["hheaLineGap"]
    i.openTypeOS2TypoAscender, i.openTypeOS2TypoDescender, i.openTypeOS2TypoLineGap = p["typoAscender"], p["typoDescender"], p["typoLineGap"]
    i.openTypeOS2WinAscent, i.openTypeOS2WinDescent = p["winAscent"], p["winDescent"]

    project = hindkit.Project(
        family,
        fontrevision = "{}.{:03d}".format(source.versionMajor, source.versionMinor),
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
hindkit.Project.directories["features"] = FEATURES_DIR
hindkit.Project.directories["output"] = ""

# --- Executing ---

main()
