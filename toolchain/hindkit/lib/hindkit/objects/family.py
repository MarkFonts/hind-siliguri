import os, subprocess, math
import defcon
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor, InstanceDescriptor
import hindkit as kit

class Family(object):

    def __init__(
        self,
        trademark = None,
        name_script_independent = None,
        script_name = "Latin",
        append_script_name = False,
        name = None,
        client_name = None,
        source_tag = None,
        initial_release_year = None,
    ):

        self.trademark = trademark
        self.name_script_independent = kit.fallback(name_script_independent, self.trademark)
        self.script = kit.constants.SCRIPT_NAMES_TO_SCRIPTS.get(script_name)
        if name:
            self.name = name
        else:
            self.name = self.name_script_independent
            if script_name and append_script_name:
                self.name += " " + script_name
        self.name_postscript = kit.remove_illegal_chars_for_postscript_name_part(self.name)

        self.masters = None
        self.styles = None

        self.info = defcon.Font().info

        self.client_name = client_name
        self.source_tag = source_tag
        self.initial_release_year = initial_release_year

        self.project: kit.Project = None

    def get_client_data(self):
        return kit.Client(self, self.client_name)

    def set_masters(self, scheme=None):
        scheme = kit.fallback(scheme, [("Light", 0), ("Bold",  100)])
        self.masters = [
            kit.Master(self, name, location)
            for name, location in scheme
        ]

    def set_styles(self, scheme=None):
        scheme = kit.fallback(scheme, self.get_client_data().style_scheme)
        self.styles = [
            kit.Style(self, name, location, weight_and_width_class)
            for name, location, weight_and_width_class in scheme
        ]
        if self.masters is None:
            self.masters = []
        for master in self.masters:
            for style in self.styles:
                if style.location == master.location:
                    style.master = master
                    break

    def _has_kerning(self):
        raise NotImplementedError()

    def _has_mark_positioning(self):
        raise NotImplementedError()

    def _has_mI_variants(self):
        raise NotImplementedError()

    def prepare_styles(self):

        p = self.project
        styles = [i.style for i in p.products if not i.subsidiary]

        if p.options["run_makeinstances"]:
            self.generate_styles()
            if p.options["round_like_python2"]:
                self.round_styles_like_python2(styles)
        elif self.masters:
            for style in styles:
                kit.copy(style.master.get_path(), style.get_path())
                if style.file_format == "UFO":
                    style.open().info.postscriptFontName = style.full_name_postscript
                    style.dirty = True
        else:
            for style in styles:
                style.prepare(whole_directory=True)

        for style in styles:
            if hasattr(style, "postprocess"):
                style.postprocess()
                style.refresh_groups()
                style.dirty = True
            style.save()

    def generate_styles(self):
        self.project.designspace.prepare()
        subprocess.call([
            "makeInstancesUFO",
            "-v",
            "-d", self.project.designspace.get_path(),
            "-a",
            "-c",
            "-n",
        ] + (["-r"] if self.project.options["round_like_python2"] else []))

    def round_styles_like_python2(self, styles):
        """Round instances the way the 2014 FDK did (half away from zero), not Python 3's half to even.

        makeInstancesUFO -r leaves outlines and anchors unrounded but still rounds widths
        half to even, so widths are interpolated again from the masters here.
        """
        if len(self.masters) != 2 or len(self.masters[0].location) != 1:
            raise NotImplementedError("round_like_python2 handles two masters on one axis.")
        m0, m1 = self.masters
        f0, f1 = (defcon.Font(m.get_path()) for m in self.masters)
        for style in styles:
            t = (style.location[0] - m0.location[0]) / (m1.location[0] - m0.location[0])
            font = style.open()
            for glyph in font:
                w0, w1 = f0[glyph.name].width, f1[glyph.name].width
                # defcon skips a set that compares equal (275 == 275.0), so step off the value first.
                width = round_half_away_from_zero(w0 + (w1 - w0) * t)
                glyph.width = width + 1
                glyph.width = width
                for contour in glyph:
                    for point in contour:
                        point.x, point.y = round_half_away_from_zero(point.x), round_half_away_from_zero(point.y)
                for component in glyph.components:
                    xx, xy, yx, yy, dx, dy = component.transformation
                    component.transformation = (xx, xy, yx, yy, round_half_away_from_zero(dx), round_half_away_from_zero(dy))
                for anchor in glyph.anchors:
                    x, y = round_half_away_from_zero(anchor.x), round_half_away_from_zero(anchor.y)
                    anchor.x, anchor.y = x + 1, y + 1
                    anchor.x, anchor.y = x, y
                glyph.dirty = True
            style.dirty = True


def round_half_away_from_zero(value):
    """Python 2's round(), which the 2014 FDK scripts ran on."""
    return int(math.copysign(math.floor(abs(value) + 0.5), value))


class DesignSpace(kit.BaseFile):

    def __init__(self, project, name="font"):
        super(DesignSpace, self).__init__(
            name,
            project = project,
            file_format = "DesignSpace",
        )

    def generate(self):

        # AFDKO's makeinstancesufo reads designspace 4+, which needs real axes.
        doc = DesignSpaceDocument()
        masters = self.project.family.masters
        for axis_number in range(len(masters[0].location)):
            positions = [m.location[axis_number] for m in masters]
            axis = AxisDescriptor()
            if axis_number == 0:
                axis.name, axis.tag = "weight", "wght"
            else:
                axis.name, axis.tag = "axis " + str(axis_number), "AX{:02d}".format(axis_number)
            axis.minimum, axis.maximum = min(positions), max(positions)
            axis.default = masters[0].location[axis_number]
            doc.addAxis(axis)

        def location(position):
            return {a.name: v for a, v in zip(doc.axes, position)}

        for i, master in enumerate(masters):
            source = SourceDescriptor()
            source.path = os.path.abspath(kit.relative_to_cwd(master.get_path()))
            source.name = "master " + master.name
            source.location = location(master.location)
            source.copyLib = source.copyGroups = source.copyInfo = i == 0
            doc.addSource(source)

        for product in self.project.products:
            if not product.subsidiary:
                style = product.style
                instance = InstanceDescriptor()
                instance.name = "instance " + style.name
                instance.location = location(style.location)
                instance.familyName = self.project.family.name
                instance.styleName = style.name
                instance.path = os.path.abspath(kit.relative_to_cwd(style.get_path()))
                instance.postScriptFontName = style.full_name_postscript
                if self.project.options["prepare_kerning"]:
                    instance.kerning = True
                doc.addInstance(instance)

        doc.write(os.path.abspath(kit.relative_to_cwd(self.get_path())))


class Fmndb(kit.BaseFile):

    LINES_HEAD = [
        "# [PostScriptName]",
        "#   f = Family Name",
        "#   s = Style Name",
        "#   l = Style-Linking Family Name",
    ]

    def __init__(self, project, name="FontMenuNameDB"):
        super(Fmndb, self).__init__(name, project=project)
        self.lines = []
        self.lines.extend(self.LINES_HEAD)

    def generate(self):

        for product in self.project.products:

            if product.subsidiary:
                continue

            self.lines.append("")
            self.lines.append("[" + product.full_name_postscript + "]")
            self.lines.append("  f = " + product.family.name)
            self.lines.append("  s = " + product.name)

            comment_lines = []

            if self.project.options["do_style_linking"]:
                name_parts = product.name.split(" ")
                try:
                    name_parts.remove("Regular")
                except ValueError:
                    pass
                if product.is_bold:
                    name_parts.remove("Bold")
                    comment_lines.append("  # IsBoldStyle")
                if product.is_italic:
                    name_parts.remove("Italic")
                    comment_lines.append("  # IsItalicStyle")
                product._style_linking_family_name = " ".join(
                    [product.family.name] + name_parts
                )

            if product.style_linking_family_name != product.family.name:
                self.lines.append("  l = " + product.style_linking_family_name)

            self.lines.extend(comment_lines)

        with open(self.get_path(), "w") as f:
            f.writelines(i + "\n" for i in self.lines)
