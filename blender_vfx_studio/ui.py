"""Blender UI delegates lifecycle operations to core."""

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatVectorProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import core, palettes, presets
from .registry import PRESETS


def _read_color(owner, prefix, fallback):
    return tuple(float(owner.get(f"{prefix}_{i}", fallback[i])) for i in range(3))


def _write_color(owner, values, prefix):
    for i, value in enumerate(values):
        owner[f"{prefix}_{i}"] = float(value)
    owner.update_tag()


_ART_GROUPS = (
    (
        "Shape",
        (
            "radius",
            "width",
            "height",
            "arc",
            "taper",
            "head_bias",
            "contour",
            "bank",
            "size",
            "shape",
            "stretch",
            "planar",
            "columns",
            "rows",
            "Fire Height",
            "Fire Curl",
            "Dust Rise Height",
        ),
    ),
    (
        "Motion",
        (
            "attack",
            "spin",
            "expansion",
            "motion_seconds",
            "velocity",
            "gravity",
            "spread",
            "randomness",
            "spawn_radius",
            "rate",
            "emission_seconds",
            "lifetime",
            "count",
            "motion_ease",
            "afterimage",
            "wake_spread",
            "flow",
            "first_frame",
            "last_frame",
            "length",
            "Fire Flow Speed",
            "Dust Roll Speed",
            "Sigil Spin",
            "Sigil Lift",
        ),
    ),
    (
        "Material",
        (
            "strength",
            "opacity",
            "ior",
            "rim_power",
            "core_width",
            "streaks",
            "surface_cuts",
            "noise_scale",
            "threshold",
            "glow_size",
            "flash",
            "Dust Density",
        ),
    ),
    ("Dissolve", ("dissolve", "fade", "breakup", "fragment_release")),
)
_ART_LABELS = {
    "bank": "Depth Bend (0 = Flat)",
    "head_bias": "Leading Weight",
    "core_width": "Blade Width",
    "afterimage": "Wake Amount",
    "streaks": "Brush Detail",
    "breakup": "Noise Erosion",
    "motion_ease": "Deceleration",
}
_EXTRA_ART_KEYS = {
    "Fire Height",
    "Fire Flow Speed",
    "Fire Curl",
    "Dust Rise Height",
    "Dust Roll Speed",
    "Dust Density",
    "Sigil Spin",
    "Sigil Lift",
}

# These existing constant nodes already author the complete assets. Edit their
# native sockets directly instead of adding a second controller value/driver.
_NATIVE_SHAPE_VALUES = (
    ("Nucleus Stored Size", "Stored Core Size", False),
    ("Nucleus Compression", "Compression (0–0.85)", False),
    ("Release Stretch", "Release Stretch", False),
    ("Bolt Length", "Bolt Length", False),
    ("Branch Reach", "Branch Reach", False),
    ("Nucleus Seed Size", "Initial Core Size", True),
    ("Release Pinch", "Release Pinch (0–1)", True),
)


def _native_shape_values(root):
    found = {}
    for child in root.children:
        if child.get("vfx_role") != "layer" or child.get("vfx_id") != root["vfx_id"]:
            continue
        for modifier in child.modifiers:
            if modifier.type != "NODES" or modifier.node_group is None:
                continue
            tree = modifier.node_group
            driven = (
                {c.data_path for c in tree.animation_data.drivers} if tree.animation_data else set()
            )
            for name, label, advanced in _NATIVE_SHAPE_VALUES:
                node = tree.nodes.get(name)
                if node is None or node.type != "VALUE" or not node.outputs[0].is_linked:
                    continue
                socket = node.outputs[0]
                if socket.path_from_id("default_value") not in driven:
                    found.setdefault(name, (label, socket, advanced))
    return found


def _driven_art_properties(root):
    """Expose known custom art properties only when native drivers actually read them."""
    trees = []
    for obj in root.children:
        if obj.type != "MESH":
            continue
        trees += [m.node_group for m in obj.modifiers if m.type == "NODES" and m.node_group]
        trees += [m.node_tree for m in obj.data.materials if m and m.node_tree]
    paths = set()
    for tree in trees:
        if tree.animation_data:
            for curve in tree.animation_data.drivers:
                for variable in curve.driver.variables:
                    for target in variable.targets:
                        if target.id == root:
                            paths.add(target.data_path)
    return {key for key in _EXTRA_ART_KEYS if key in root and f'["{key}"]' in paths}


def _draw_art_parameters(layout, context, root, keys):
    remaining = {key for key in keys if key in root} | _driven_art_properties(root)
    for title, candidates in _ART_GROUPS:
        shown = [key for key in candidates if key in remaining]
        if not shown:
            continue
        box = layout.box()
        box.label(text=title)
        for key in shown:
            box.prop(root, f'["{key}"]', text=_ART_LABELS.get(key, key.replace("_", " ").title()))
        remaining.difference_update(shown)
    if remaining:
        layout.prop(context.window_manager, "vfx_advanced_controls", text="Advanced")
        if context.window_manager.vfx_advanced_controls:
            box = layout.box()
            for key in sorted(remaining):
                box.prop(root, f'["{key}"]', text=key.replace("_", " ").title())


class VFX_OT_key_color(bpy.types.Operator):
    bl_idname = "vfx_studio.key_color"
    bl_label = "Keyframe Color"
    bl_description = (
        "Insert native keyframes on the stored RGB channels; playback needs no extension"
    )
    bl_options = {"REGISTER", "UNDO"}
    palette: EnumProperty(items=(("BODY", "Color", ""), ("BLADE", "Blade", "")), default="BODY")

    def execute(self, context):
        root = core.resolve(context.object)
        prefix = "blade_color" if self.palette == "BLADE" else "color"
        if root is None or not all(f"{prefix}_{i}" in root for i in range(3)):
            self.report({"ERROR"}, "Select an effect with these color controls")
            return {"CANCELLED"}
        for i in range(3):
            root.keyframe_insert(data_path=f'["{prefix}_{i}"]')
        return {"FINISHED"}


class VFX_OT_fire_palette(bpy.types.Operator):
    bl_idname = "vfx_studio.fire_palette"
    bl_label = "Set Fire Palette"
    bl_description = (
        "Set native heat-ramp colors and neutral tint, keeping nodes, positions and animation"
    )
    bl_options = {"REGISTER", "UNDO"}
    palette: EnumProperty(
        items=(("ORANGE", "Orange", ""), ("BLUE", "Blue", ""), ("GREEN", "Green", "")),
        default="ORANGE",
    )

    def execute(self, context):
        root = core.resolve(context.object)
        try:
            if root is None:
                raise ValueError("Select a fire layer")
            palettes.apply_fire(root, self.palette)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_slash_style(bpy.types.Operator):
    bl_idname = "vfx_studio.slash_style"
    bl_label = "Apply Slash Style"
    bl_description = "Set shape and surface controls while keeping palette, timing and edited nodes"
    bl_options = {"REGISTER", "UNDO"}
    style: EnumProperty(
        items=(
            ("CLEAN", "Clean", "Planar, continuous blade"),
            ("STYLIZED", "Stylized", "Sculpted silhouette and separate colored wakes"),
        ),
        default="STYLIZED",
    )

    def execute(self, context):
        from . import slash

        try:
            slash.apply_style(context.object, self.style)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_create(bpy.types.Operator):
    bl_idname = "vfx_studio.create"
    bl_description = "Create an editable ring, slash or impact composition at the 3D Cursor"
    bl_label = "Create Mesh VFX"
    bl_options = {"REGISTER", "UNDO"}

    preset: EnumProperty(
        name="Effect",
        items=[(key, p["label"], "") for key, p in PRESETS.items()],
        default="SHOCKWAVE",
    )
    quality: EnumProperty(
        name="Quality",
        items=[("LOW", "Low · 32", ""), ("MEDIUM", "Medium · 64", ""), ("HIGH", "High · 128", "")],
        default="MEDIUM",
    )

    def execute(self, context):
        core.create(context, self.preset, self.quality)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class VFX_OT_create_flipbook(bpy.types.Operator, ImportHelper):
    bl_idname = "vfx_studio.create_flipbook"
    bl_description = "Create an animated sprite from a still image containing a grid of frames"
    bl_label = "Create Flipbook from Atlas"
    bl_options = {"REGISTER", "UNDO"}
    filter_glob: StringProperty(
        default="*.png;*.tga;*.jpg;*.jpeg;*.exr;*.tif;*.tiff;*.webp", options={"HIDDEN"}
    )
    columns: IntProperty(name="Columns", default=4, min=1, max=256)
    rows: IntProperty(name="Rows", default=4, min=1, max=256)

    def execute(self, context):
        try:
            core.create_flipbook(context, core.load_atlas(self.filepath), self.columns, self.rows)
        except (ValueError, OSError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_create_sequence(bpy.types.Operator, ImportHelper):
    bl_idname = "vfx_studio.create_sequence"
    bl_label = "Create Sprite from Image Sequence"
    bl_description = "Load consecutive numbered images and animate them with shared VFX timing"
    bl_options = {"REGISTER", "UNDO"}
    filter_glob: StringProperty(
        default="*.png;*.tga;*.jpg;*.jpeg;*.exr;*.tif;*.tiff;*.webp", options={"HIDDEN"}
    )
    frame_count: IntProperty(name="File Count", default=16, min=1, max=4096)

    def execute(self, context):
        try:
            core.create_sequence(context, self.filepath, self.frame_count)
        except (ValueError, OSError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_create_screen(bpy.types.Operator):
    bl_idname = "vfx_studio.create_screen"
    bl_description = "Insert a timed glow and flash layer into the current scene compositor"
    bl_label = "Add Screen Glare + Flash"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            core.create_screen(context)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_create_particle(bpy.types.Operator):
    bl_idname = "vfx_studio.create_particle"
    bl_description = "Create a repeatable particle burst with native motion and no simulation cache"
    bl_label = "Create Particle Burst"
    bl_options = {"REGISTER", "UNDO"}
    quality: EnumProperty(
        name="Quality",
        items=[("LOW", "Low", ""), ("MEDIUM", "Medium", ""), ("HIGH", "High", "")],
        default="LOW",
    )

    def execute(self, context):
        core.create_particle(context, self.quality)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class VFX_OT_create_emitter(bpy.types.Operator):
    bl_idname = "vfx_studio.create_emitter"
    bl_description = "Create a continuous local-space stream with individual particle lifetimes"
    bl_label = "Create Continuous Emitter"
    bl_options = {"REGISTER", "UNDO"}
    quality: EnumProperty(
        name="Quality",
        items=[("LOW", "Low", ""), ("MEDIUM", "Medium", ""), ("HIGH", "High", "")],
        default="LOW",
    )

    def execute(self, context):
        core.create_emitter(context, self.quality)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class VFX_OT_create_shield(bpy.types.Operator):
    bl_idname = "vfx_studio.create_shield"
    bl_description = "Create an editable sphere with a bright Fresnel rim and noise dissolve"
    bl_label = "Create Energy Shield"
    bl_options = {"REGISTER", "UNDO"}
    quality: EnumProperty(
        name="Sphere Quality",
        items=[
            ("LOW", "Low", "16 segments"),
            ("MEDIUM", "Medium", "32 segments"),
            ("HIGH", "High", "64 segments"),
        ],
        default="MEDIUM",
    )

    def execute(self, context):
        core.create_shield(context, self.quality)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class VFX_OT_create_trail(bpy.types.Operator):
    bl_idname = "vfx_studio.create_trail"
    bl_description = "Sample the active object or pose bone animation into an editable ribbon"
    bl_label = "Bake Ribbon from Active Object / Bone"
    bl_options = {"REGISTER", "UNDO"}
    first: IntProperty(name="First Frame", default=1, min=-100000, max=100000)
    last: IntProperty(name="Last Frame", default=25, min=-100000, max=100000)
    step: IntProperty(name="Sample Step", default=1, min=1, max=100000)

    bone_tail: BoolProperty(
        name="Use Bone Tail",
        description="Sample the active pose bone's tip instead of its head; ignored for objects",
        default=False,
    )

    def execute(self, context):
        from . import trail

        bone = context.active_pose_bone.name if context.active_pose_bone else ""
        try:
            trail.create(
                context,
                context.object,
                bone,
                self.first,
                self.last,
                self.step,
                bone_tail=self.bone_tail,
            )
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context, event):
        self.first, self.last = context.scene.frame_start, context.scene.frame_end
        return context.window_manager.invoke_props_dialog(self)


class VFX_OT_capture_dash(bpy.types.Operator):
    bl_idname = "vfx_studio.capture_dash"
    bl_label = "Capture Dash Echoes"
    bl_description = (
        "Store a few evaluated poses from the active mesh or armature; preserve its animation"
    )
    bl_options = {"REGISTER", "UNDO"}
    first: IntProperty(name="First Frame", default=1, min=-100000, max=100000)
    last: IntProperty(name="Last Frame", default=13, min=-100000, max=100000)
    quality: EnumProperty(
        name="Quality",
        items=[
            ("LOW", "Low · 2 poses", ""),
            ("MEDIUM", "Medium · 3 poses", ""),
            ("HIGH", "High · 4 poses", ""),
        ],
        default="MEDIUM",
    )
    tail: IntProperty(name="Echo Tail (Frames)", default=18, min=1, max=100000)

    def execute(self, context):
        from . import dash

        try:
            dash.create(
                context, context.object, self.first, self.last, self.quality, tail=self.tail
            )
        except (ValueError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context, event):
        self.last = context.scene.frame_current
        self.first = self.last - 12
        return context.window_manager.invoke_props_dialog(self)


class VFX_OT_rebake_trail(bpy.types.Operator):
    bl_idname = "vfx_studio.rebake_trail"
    bl_description = (
        "Replace the stored ribbon mesh from its source animation; keep materials and nodes"
    )
    bl_label = "Rebake Ribbon (Replace Edited Mesh)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import trail

        try:
            trail.rebake(context, context.object)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class VFX_OT_bind(bpy.types.Operator):
    bl_idname = "vfx_studio.bind"
    bl_description = "Follow an object or pose bone while keeping the current world transform"
    bl_label = "Bind VFX to Object / Bone"
    bl_options = {"REGISTER", "UNDO"}
    target: StringProperty(name="Target")
    bone: StringProperty(name="Bone (optional)")

    def draw(self, context):
        self.layout.prop_search(self, "target", context.scene, "objects")
        target = context.scene.objects.get(self.target)
        if target and target.type == "ARMATURE":
            self.layout.prop_search(self, "bone", target.pose, "bones")
        else:
            self.layout.prop(self, "bone")

    def invoke(self, context, event):
        root = core.resolve(context.object)
        targets = [o for o in context.selected_objects if o != root and core.resolve(o) is None]
        if len(targets) == 1:
            self.target = targets[0].name
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        from . import binding

        try:
            binding.bind(context, context.object, context.scene.objects.get(self.target), self.bone)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_unbind(bpy.types.Operator):
    bl_idname = "vfx_studio.unbind"
    bl_description = (
        "Remove the managed binding and keep the current pose; animated transforms need baking"
    )
    bl_label = "Unbind VFX (Keep World Transform)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import binding

        try:
            binding.unbind(context, context.object)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_create_simulation(bpy.types.Operator):
    bl_idname = "vfx_studio.create_simulation"
    bl_description = "Create a pinned energy sheet ready for an explicit Cloth bake"
    bl_label = "Create Cloth Energy Sheet"
    bl_options = {"REGISTER", "UNDO"}
    quality: EnumProperty(
        name="Quality",
        items=[
            ("LOW", "Low · 81 vertices", ""),
            ("MEDIUM", "Medium · 169 vertices", ""),
            ("HIGH", "High · 289 vertices", ""),
        ],
        default="LOW",
    )

    def execute(self, context):
        from . import simulation

        simulation.create(context, self.quality)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class VFX_OT_bake_simulation(bpy.types.Operator):
    bl_idname = "vfx_studio.bake_simulation"
    bl_label = "Bake / Replace Stored Cloth Motion"
    bl_description = "Solve the cloth and replace its stored shape-key animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import simulation

        try:
            simulation.bake(context, context.object)
        except (ValueError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class VFX_OT_clear_simulation(bpy.types.Operator):
    bl_idname = "vfx_studio.clear_simulation"
    bl_description = "Remove stored cloth poses and keep the static reference mesh"
    bl_label = "Clear Stored Cloth Motion"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import simulation

        try:
            simulation.clear(context.object)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class VFX_OT_edit_simulation_source(bpy.types.Operator):
    bl_idname = "vfx_studio.edit_simulation_source"
    bl_description = "Show the hidden source as wireframe for mesh, pin and Cloth editing"
    bl_label = "Show Cloth Source for Native Editing"

    def execute(self, context):
        from . import simulation

        try:
            source, _, _ = simulation.parts(context.object)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        source.hide_set(False)
        source.display_type = "WIRE"
        core.select(context, source)
        return {"FINISHED"}


class VFX_OT_compose(bpy.types.Operator):
    bl_idname = "vfx_studio.compose"
    bl_description = "Control 2–32 selected spatial effects with one parent and shared timing"
    bl_label = "Compose Selected VFX"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        from . import composition

        try:
            composition.create(context, context.selected_objects)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_detach_member(bpy.types.Operator):
    bl_idname = "vfx_studio.detach_member"
    bl_description = (
        "Remove group timing and parenting while keeping current timing values and world pose"
    )
    bl_label = "Detach Layer as Independent VFX"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import composition

        try:
            composition.detach(context, context.object)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_ungroup_all(bpy.types.Operator):
    bl_idname = "vfx_studio.ungroup_all"
    bl_label = "Ungroup All"
    bl_description = (
        "Detach every layer, preserving current world poses and timing; "
        "keep the former controller if user data still references it"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            context.mode == "OBJECT"
            and context.object is not None
            and context.object.get("vfx_module") == "core.composition"
        )

    def execute(self, context):
        from . import composition

        try:
            children, retained = composition.ungroup_all(context, context.object)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        message = f"Ungrouped {len(children)} layers"
        if retained:
            message += "; kept controller because user data still references it"
        self.report({"INFO"}, message)
        return {"FINISHED"}


class VFX_OT_select_member(bpy.types.Operator):
    bl_idname = "vfx_studio.select_member"
    bl_description = "Select a composition controller or member to edit its own controls"
    bl_label = "Edit Composition Layer"
    uid: StringProperty()

    def execute(self, context):
        roots = [
            o
            for o in context.scene.objects
            if o.get("vfx_id") == self.uid and o.get("vfx_role") == "controller"
        ]
        if len(roots) != 1:
            self.report({"ERROR"}, "Layer is missing or its ID was copied")
            return {"CANCELLED"}
        core.select(context, roots[0])
        return {"FINISHED"}


class VFX_OT_duplicate(bpy.types.Operator):
    bl_idname = "vfx_studio.duplicate"
    bl_description = (
        "Copy the selected effect or composition with independent generated assets and animation"
    )
    bl_label = "Duplicate VFX"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            core.duplicate(context, context.object)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_delete(bpy.types.Operator):
    bl_idname = "vfx_studio.delete"
    bl_description = (
        "Delete owned effect data after checking external users; preserve unrelated scene objects"
    )
    bl_label = "Delete VFX"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            core.delete(context.object)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class VFX_OT_export_preset(bpy.types.Operator, ExportHelper):
    bl_idname = "vfx_studio.export_preset"
    bl_description = (
        "Save current parameter values to JSON; use Save Complete Effect for edited nodes or paths"
    )
    bl_label = "Save VFX Preset"
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        try:
            presets.write(self.filepath, core.preset_snapshot(context.object))
        except (ValueError, OSError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_import_preset(bpy.types.Operator, ImportHelper):
    bl_idname = "vfx_studio.import_preset"
    bl_description = "Create an independent effect from a validated parameter JSON file"
    bl_label = "Load VFX Preset"
    bl_options = {"REGISTER", "UNDO"}
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        try:
            core.create_from_preset(context, presets.read(self.filepath))
        except (ValueError, OSError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_export_asset(bpy.types.Operator, ExportHelper):
    bl_idname = "vfx_studio.export_asset"
    bl_label = "Save Complete Effect"
    bl_description = "Save native nodes, animation and stored motion in a reusable .blend asset"
    filename_ext = ".blend"
    filter_glob: StringProperty(default="*.blend", options={"HIDDEN"})

    preview_image: StringProperty(
        name="Preview Image",
        description="Optional loaded still image, at most 2048 pixels per side; source stays unchanged",
        default="",
    )

    def draw(self, context):
        self.layout.label(text="Preview Image (optional)")
        self.layout.prop_search(self, "preview_image", bpy.data, "images", text="")
        self.layout.label(text="Still image · up to 2048 px")
        self.layout.label(text="No scene view transform")

    def execute(self, context):
        from . import assets

        try:
            image = bpy.data.images.get(self.preview_image) if self.preview_image else None
            if self.preview_image and image is None:
                raise ValueError("The selected preview image no longer exists")
            assets.write(self.filepath, context.object, preview_image=image)
        except (ValueError, OSError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_import_asset(bpy.types.Operator, ImportHelper):
    bl_idname = "vfx_studio.import_asset"
    bl_label = "Load Complete Effect"
    bl_description = "Append a complete VFX .blend asset with fresh independent instance IDs"
    bl_options = {"REGISTER", "UNDO"}
    filter_glob: StringProperty(default="*.blend", options={"HIDDEN"})

    def execute(self, context):
        from . import assets

        try:
            assets.load(context, self.filepath)
        except (ValueError, OSError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_PT_main(bpy.types.Panel):
    bl_label = "Blender VFX Studio"
    bl_idname = "VFX_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VFX"

    def draw(self, context):
        layout = self.layout
        layout.operator("vfx_studio.create", text="Create Mesh VFX", icon="ADD")
        layout.operator("vfx_studio.create_flipbook", text="Create Flipbook", icon="IMAGE_DATA")
        layout.operator(
            "vfx_studio.create_sequence", text="Create Image Sequence", icon="FILE_IMAGE"
        )
        layout.operator(
            "vfx_studio.create_particle", text="Create Particle Burst", icon="PARTICLES"
        )
        layout.operator(
            "vfx_studio.create_emitter", text="Create Continuous Emitter", icon="PARTICLES"
        )
        layout.operator("vfx_studio.create_screen", text="Add Screen VFX", icon="RENDERLAYERS")
        layout.operator(
            "vfx_studio.create_shield", text="Create Energy Shield", icon="SHADING_RENDERED"
        )
        layout.operator(
            "vfx_studio.create_simulation", text="Create Cloth Simulation", icon="MOD_CLOTH"
        )
        layout.operator("vfx_studio.create_trail", text="Bake Ribbon Trail", icon="CURVE_PATH")
        layout.operator("vfx_studio.capture_dash", text="Capture Dash Echoes", icon="MOD_TIME")
        layout.operator(
            "vfx_studio.compose", text="Compose Selected VFX", icon="OUTLINER_COLLECTION"
        )
        layout.operator("vfx_studio.import_preset", text="Load Preset", icon="IMPORT")
        layout.operator("vfx_studio.import_asset", text="Load Complete Effect", icon="APPEND_BLEND")
        try:
            root = core.resolve(context.object)
        except ValueError as error:
            layout.label(text=str(error), icon="ERROR")
            return
        if root is None:
            layout.label(text="Select a VFX controller or layer")
            return
        layout.prop(root, "name", text="Effect")
        if root["vfx_module"] not in {"screen.glare", "flipbook.sequence"}:
            layout.operator(
                "vfx_studio.export_asset", text="Save Complete Effect", icon="FILE_BLEND"
            )
        if root["vfx_module"] not in {"trail.ribbon", "core.composition", "simulation.cloth"}:
            layout.operator("vfx_studio.export_preset", text="Save Preset", icon="EXPORT")
        else:
            layout.label(text="Reuse with Duplicate or Save Complete Effect")
        row = layout.row(align=True)
        row.operator("vfx_studio.duplicate", text="Duplicate", icon="DUPLICATE")
        row.operator("vfx_studio.delete", text="Delete", icon="TRASH")
        if root["vfx_module"] != "screen.glare":
            if root.get("vfx_binding_constraint"):
                layout.label(text="Native Child Of binding (Object Constraints)")
                layout.operator("vfx_studio.unbind", text="Unbind", icon="UNLINKED")
            else:
                layout.operator("vfx_studio.bind", text="Bind Object / Bone", icon="CONSTRAINT")
        if root.get("vfx_composition"):
            layout.label(text="Timing follows composition")
            for key, label in (
                ("vfx_offset_ratio", "Start Offset Ratio"),
                ("vfx_duration_ratio", "Duration Ratio"),
                ("vfx_local_speed", "Local Speed"),
            ):
                layout.prop(root, f'["{key}"]', text=label)
            layout.operator("vfx_studio.detach_member", text="Detach Layer", icon="UNLINKED")
            layout.operator("vfx_studio.select_member", text="Edit Composition").uid = root[
                "vfx_composition"
            ]["vfx_id"]
        else:
            layout.label(text="Timing · frames")
            for key in ("start", "duration", "speed", "loop"):
                layout.prop(root, f'["{key}"]', text=key.title())
        if root["vfx_module"] == "core.composition":
            from . import composition

            try:
                children = composition.members(root)
            except ValueError as error:
                layout.label(text=str(error), icon="ERROR")
                return
            layout.label(text=f"{len(children)} spatial layers")
            layout.operator("vfx_studio.ungroup_all", icon="UNLINKED")
            for child in children:
                layout.operator("vfx_studio.select_member", text=child.name).uid = child["vfx_id"]
            layout.label(text="Loop restarts all layers each group cycle")
            return
        if root["vfx_module"] == "shader.shield":
            layout.label(
                text="Authored shader layer"
                if root.get("vfx_parameter_keys")
                else "Fresnel shield · exterior surface"
            )
            keys = (
                "radius",
                "expansion",
                "opacity",
                "ior",
                "rim_power",
                "strength",
                "dissolve",
                "noise_scale",
                "flow",
                "fade",
            )
        elif root["vfx_module"] == "mesh.slash":
            layout.label(text="Arc Slash")
            if "surface_cuts" in root and "fragment_release" in root:
                row = layout.row(align=True)
                row.operator("vfx_studio.slash_style", text="Clean").style = "CLEAN"
                row.operator("vfx_studio.slash_style", text="Stylized").style = "STYLIZED"
            keys = (
                "radius",
                "width",
                "arc",
                "spin",
                "taper",
                "expansion",
                "strength",
                "dissolve",
                "noise_scale",
                "fade",
            )
            keys += (
                "attack",
                "motion_ease",
                "head_bias",
                "core_width",
                "afterimage",
                "streaks",
                "breakup",
            )
            keys += ("contour", "bank", "wake_spread", "surface_cuts", "fragment_release")
        elif root["vfx_module"] == "simulation.cloth":
            from . import simulation

            try:
                _, _, cloth = simulation.parts(root)
                status = simulation.state(context, root)
            except ValueError as error:
                layout.label(text=str(error), icon="ERROR")
                return
            layout.label(
                text=f"Stored motion: {status}", icon="ERROR" if status == "STALE" else "INFO"
            )
            layout.label(text="Source edits require an explicit Bake")
            for key in ("vfx_sim_first", "vfx_sim_last", "vfx_sim_step"):
                layout.prop(root, f'["{key}"]', text=key.removeprefix("vfx_sim_").title())
            for key in ("quality", "mass", "tension_stiffness", "bending_stiffness", "air_damping"):
                layout.prop(cloth.settings, key)
            layout.operator("vfx_studio.bake_simulation", icon="REC")
            layout.operator("vfx_studio.clear_simulation", icon="TRASH")
            layout.operator("vfx_studio.edit_simulation_source", icon="EDITMODE_HLT")
            keys = ("strength",)
        elif root["vfx_module"] == "trail.ribbon":
            layout.label(text="Ribbon · explicit sampled animation")
            layout.prop(root, '["vfx_source"]', text="Source")
            layout.prop(root, '["vfx_bone"]', text="Bone")
            if "vfx_bone_tail" in root:
                row = layout.row()
                row.enabled = bool(root.get("vfx_bone"))
                row.prop(root, '["vfx_bone_tail"]', text="Use Bone Tail")
            else:
                layout.label(text="Ribbon · samples bone head")
            for key in ("vfx_bake_first", "vfx_bake_last", "vfx_bake_step"):
                layout.prop(root, f'["{key}"]', text=key.removeprefix("vfx_bake_").title())
            layout.label(text=f"{root['vfx_samples']} baked samples; source edits need Rebake")
            layout.operator("vfx_studio.rebake_trail", icon="FILE_REFRESH")
            keys = ("width", "length", "fade", "strength")
        elif root["vfx_module"] == "particle.emitter":
            from .emitter import limits

            effective, _ = limits(root["rate"], root["lifetime"])
            layout.label(text=f"Effective rate: {effective:.4g} particles/s")
            if root["rate"] > effective:
                layout.label(text="Rate limited by 2048-particle budget", icon="INFO")
            layout.label(text="Local space · includes lifetime tail")
            keys = (
                "rate",
                "emission_seconds",
                "lifetime",
                "seed",
                "velocity",
                "gravity",
                "spread",
                "randomness",
                "spawn_radius",
                "size",
                "fade",
                "strength",
            )
        elif root["vfx_module"] == "particle.burst":
            layout.label(
                text="Authored mesh layer"
                if root.get("vfx_parameter_keys")
                else "Particle Burst · stateless"
            )
            keys = (
                "count",
                "seed",
                "motion_seconds",
                "velocity",
                "gravity",
                "spread",
                "randomness",
                "spawn_radius",
                "size",
                "fade",
                "strength",
            )
            if not root.get("vfx_parameter_keys"):
                layout.label(text="Shape: 0 Round / 1 Shard")
            keys += ("shape", "stretch", "planar", "motion_ease")
        elif root["vfx_module"] == "screen.glare":
            layout.label(text="Screen · scene compositor")
            keys = ("strength", "threshold", "glow_size", "flash", "fade")
        elif root["vfx_module"] == "flipbook.sequence":
            layout.label(text=f"Sequence · {root['vfx_sequence_count']} external files")
            layout.label(text="Image indices start at zero")
            keys = ("first_frame", "last_frame", "width", "height", "opacity", "strength", "fade")
        elif root["vfx_module"] == "flipbook.atlas":
            layout.label(text="Flipbook · top-left row order")
            try:
                tex = core.atlas_node(root)
                layout.template_ID(tex, "image")
            except ValueError as error:
                layout.label(text=str(error), icon="ERROR")
            keys = (
                "columns",
                "rows",
                "first_frame",
                "last_frame",
                "width",
                "height",
                "opacity",
                "strength",
                "fade",
            )
        else:
            layout.label(text="Mesh + Shader")
            keys = ("radius", "width", "expansion", "strength", "dissolve", "noise_scale", "fade")
        profile = root.get("vfx_parameter_keys")
        if isinstance(profile, str):
            visible = {key.strip() for key in profile.split(",")}
            keys = tuple(key for key in keys if key in visible)
        _draw_art_parameters(layout, context, root, keys)
        native_values = _native_shape_values(root)
        if native_values:
            box = layout.box()
            box.label(text="Core Focus" if "Nucleus Stored Size" in native_values else "Bolt Shape")
            for label, socket, advanced in native_values.values():
                if not advanced or context.window_manager.vfx_advanced_controls:
                    box.prop(socket, "default_value", text=label)
            if any(v[2] for v in native_values.values()):
                box.prop(context.window_manager, "vfx_advanced_controls", text="Advanced Shape")
        color_box = layout.box()
        color_box.label(text="Color")
        row = color_box.row(align=True)
        row.prop(
            root,
            "vfx_primary_color",
            text="Body"
            if root["vfx_module"] == "mesh.slash"
            else "Heat Tint"
            if palettes.fire_ramp(root)
            else "Color",
        )
        row.operator("vfx_studio.key_color", text="", icon="KEY_HLT").palette = "BODY"
        if all(f"blade_color_{i}" in root for i in range(3)):
            row = color_box.row(align=True)
            row.prop(root, "vfx_blade_color", text="Blade")
            row.operator("vfx_studio.key_color", text="", icon="KEY_HLT").palette = "BLADE"
        heat_ramp = palettes.fire_ramp(root)
        if heat_ramp is not None:
            palette_box = layout.box()
            palette_box.label(text="Heat Palette")
            if len(heat_ramp.color_ramp.elements) == 5:
                row = palette_box.row(align=True)
                for choice in ("ORANGE", "BLUE", "GREEN"):
                    row.operator("vfx_studio.fire_palette", text=choice.title()).palette = choice
            palette_box.prop(context.window_manager, "vfx_advanced_controls", text="Edit Heat Ramp")
            if context.window_manager.vfx_advanced_controls:
                palette_box.template_color_ramp(heat_ramp, "color_ramp")
        if root.get("vfx_parameter_keys"):
            layout.label(text="Custom shape: save Complete Effect (.blend)", icon="INFO")
        layout.label(text="Diamonds key colors; right-click other controls")
        layout.label(text="Material Preview / Rendered shows shader")


CLASSES = (
    VFX_OT_key_color,
    VFX_OT_slash_style,
    VFX_OT_fire_palette,
    VFX_OT_create,
    VFX_OT_create_flipbook,
    VFX_OT_create_sequence,
    VFX_OT_create_screen,
    VFX_OT_create_particle,
    VFX_OT_create_emitter,
    VFX_OT_create_shield,
    VFX_OT_create_trail,
    VFX_OT_capture_dash,
    VFX_OT_rebake_trail,
    VFX_OT_bind,
    VFX_OT_unbind,
    VFX_OT_create_simulation,
    VFX_OT_bake_simulation,
    VFX_OT_clear_simulation,
    VFX_OT_edit_simulation_source,
    VFX_OT_compose,
    VFX_OT_detach_member,
    VFX_OT_ungroup_all,
    VFX_OT_select_member,
    VFX_OT_duplicate,
    VFX_OT_delete,
    VFX_OT_export_preset,
    VFX_OT_import_preset,
    VFX_OT_export_asset,
    VFX_OT_import_asset,
    VFX_PT_main,
)


def register():
    bpy.types.WindowManager.vfx_advanced_controls = BoolProperty(
        name="Advanced", default=False, options={"SKIP_SAVE"}
    )
    # These editing proxies never store animation; the key button targets native RGB ID properties.
    bpy.types.Object.vfx_primary_color = FloatVectorProperty(
        name="Color",
        subtype="COLOR",
        size=3,
        min=0,
        max=1,
        options=set(),
        get=lambda o: _read_color(o, "color", (0.08, 0.5, 1)),
        set=lambda o, v: _write_color(o, v, "color"),
    )
    bpy.types.Object.vfx_blade_color = FloatVectorProperty(
        name="Blade Color",
        subtype="COLOR",
        size=3,
        min=0,
        max=1,
        options=set(),
        get=lambda o: _read_color(o, "blade_color", (0.8, 0.9, 1)),
        set=lambda o, v: _write_color(o, v, "blade_color"),
    )
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    del bpy.types.WindowManager.vfx_advanced_controls
    del bpy.types.Object.vfx_primary_color
    del bpy.types.Object.vfx_blade_color
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
