"""Blender UI delegates lifecycle operations to core."""

import bpy
from bpy.props import EnumProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import core, presets
from .registry import PRESETS


class VFX_OT_create(bpy.types.Operator):
    bl_idname = "vfx_studio.create"
    bl_label = "Create VFX"
    bl_options = {"REGISTER", "UNDO"}

    preset: EnumProperty(items=[(key, p["label"], "") for key, p in PRESETS.items()])
    quality: EnumProperty(
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


class VFX_OT_duplicate(bpy.types.Operator):
    bl_idname = "vfx_studio.duplicate"
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


class VFX_PT_main(bpy.types.Panel):
    bl_label = "Blender VFX Studio"
    bl_idname = "VFX_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VFX"

    def draw(self, context):
        layout = self.layout
        layout.operator("vfx_studio.create", text="Create Ring", icon="ADD")
        layout.operator("vfx_studio.create_flipbook", text="Create Flipbook", icon="IMAGE_DATA")
        layout.operator("vfx_studio.import_preset", text="Load Preset", icon="IMPORT")
        try:
            root = core.resolve(context.object)
        except ValueError as error:
            layout.label(text=str(error), icon="ERROR")
            return
        if root is None:
            layout.label(text="Select a VFX controller or layer")
            return
        layout.prop(root, "name", text="Effect")
        layout.operator("vfx_studio.export_preset", text="Save Preset", icon="EXPORT")
        row = layout.row(align=True)
        row.operator("vfx_studio.duplicate", text="Duplicate", icon="DUPLICATE")
        row.operator("vfx_studio.delete", text="Delete", icon="TRASH")
        layout.label(text="Timing · frames")
        for key in ("start", "duration", "speed", "loop"):
            layout.prop(root, f'["{key}"]', text=key.title())
        if root["vfx_module"] == "flipbook.atlas":
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
        for key in keys:
            layout.prop(root, f'["{key}"]', text=key.replace("_", " ").title())
        for i, color in enumerate(("Red", "Green", "Blue")):
            layout.prop(root, f'["color_{i}"]', text=color)
        layout.label(text="Right-click controls to insert keyframes")
        layout.label(text="Material Preview / Rendered shows shader")


CLASSES = (
    VFX_OT_create,
    VFX_OT_create_flipbook,
    VFX_OT_duplicate,
    VFX_OT_delete,
    VFX_OT_export_preset,
    VFX_OT_import_preset,
    VFX_PT_main,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
