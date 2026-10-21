"""Blender UI delegates lifecycle operations to core."""

import bpy
from bpy.props import EnumProperty

from . import core
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


class VFX_PT_main(bpy.types.Panel):
    bl_label = "Blender VFX Studio"
    bl_idname = "VFX_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VFX"

    def draw(self, context):
        layout = self.layout
        layout.operator("vfx_studio.create", icon="ADD")
        try:
            root = core.resolve(context.object)
        except ValueError as error:
            layout.label(text=str(error), icon="ERROR")
            return
        if root is None:
            layout.label(text="Select a VFX controller or layer")
            return
        layout.prop(root, "name", text="Effect")
        row = layout.row(align=True)
        row.operator("vfx_studio.duplicate", text="Duplicate", icon="DUPLICATE")
        row.operator("vfx_studio.delete", text="Delete", icon="TRASH")
        layout.label(text="Timing · frames")
        for key in ("start", "duration", "speed", "loop"):
            layout.prop(root, f'["{key}"]', text=key.title())
        layout.label(text="Mesh + Shader")
        for key in ("radius", "width", "expansion", "strength", "dissolve", "noise_scale", "fade"):
            layout.prop(root, f'["{key}"]', text=key.replace("_", " ").title())
        for i, color in enumerate(("Red", "Green", "Blue")):
            layout.prop(root, f'["color_{i}"]', text=color)
        layout.label(text="Right-click controls to insert keyframes")
        layout.label(text="Material Preview / Rendered shows shader")


CLASSES = (VFX_OT_create, VFX_OT_duplicate, VFX_OT_delete, VFX_PT_main)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
