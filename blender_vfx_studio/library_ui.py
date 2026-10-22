"""Native user preset browser; refresh is explicit, never per-frame filesystem IO."""

import bpy
from bpy.props import CollectionProperty, IntProperty, StringProperty

from . import core, library
from .registry import MODULES


def directory():
    return bpy.utils.user_resource("DATAFILES", path="blender_vfx_studio/presets", create=True)


def refresh(context):
    entries, errors = library.scan(directory())
    items = context.window_manager.vfx_library_entries
    old = selected(context)
    key = old.key if old else None
    items.clear()
    for entry in entries:
        item = items.add()
        item.key, item.name, item.module = entry.key, entry.name, entry.module
    context.window_manager.vfx_library_index = next(
        (i for i, entry in enumerate(entries) if entry.key == key), 0
    )
    context.window_manager.vfx_library_errors = len(errors)
    # CollectionProperty edits do not reliably notify every visible UIList.
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
    return errors


def selected(context):
    manager = context.window_manager
    index = manager.vfx_library_index
    return (
        manager.vfx_library_entries[index]
        if 0 <= index < len(manager.vfx_library_entries)
        else None
    )


class VFX_PG_library_entry(bpy.types.PropertyGroup):
    key: StringProperty()
    module: StringProperty()


class VFX_UL_library(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        columns = layout.split(factor=0.78)
        columns.label(text=item.name, icon="PRESET")
        columns.label(text=item.key[:6])


class VFX_OT_library_refresh(bpy.types.Operator):
    bl_idname = "vfx_studio.library_refresh"
    bl_description = "Read preset files from the user library and report invalid entries"
    bl_label = "Refresh Preset Library"

    def execute(self, context):
        try:
            errors = refresh(context)
        except (ValueError, OSError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        if errors:
            self.report(
                {"WARNING"},
                f"Skipped {len(errors)} invalid entries; first: {errors[0][0]}: {errors[0][1]}",
            )
        return {"FINISHED"}


class VFX_OT_library_save(bpy.types.Operator):
    bl_idname = "vfx_studio.library_save"
    bl_description = "Save a named parameter preset without overwriting entries with the same name"
    bl_label = "Save New Library Preset"
    name: StringProperty(name="Preset Name", maxlen=80)

    def invoke(self, context, event):
        try:
            self.name = core.preset_snapshot(context.object)["name"]
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        try:
            data = core.preset_snapshot(context.object)
            if self.name:
                data["name"] = self.name
            key = library.save(directory(), data)
            refresh(context)
            context.window_manager.vfx_library_index = next(
                i
                for i, entry in enumerate(context.window_manager.vfx_library_entries)
                if entry.key == key
            )
        except (ValueError, OSError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_library_load(bpy.types.Operator):
    bl_idname = "vfx_studio.library_load"
    bl_description = "Create an independent effect from the selected library entry"
    bl_label = "Create from Library Preset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        item = selected(context)
        if item is None:
            return {"CANCELLED"}
        try:
            core.create_from_preset(context, library.load(directory(), item.key))
        except (ValueError, OSError, UnicodeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_library_rename(bpy.types.Operator):
    bl_idname = "vfx_studio.library_rename"
    bl_description = "Change the selected preset name inside its JSON file"
    bl_label = "Rename Preset File Entry"
    name: StringProperty(name="Preset Name", maxlen=80)

    def invoke(self, context, event):
        item = selected(context)
        if item is None:
            return {"CANCELLED"}
        self.name = item.name
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        item = selected(context)
        if item is None:
            return {"CANCELLED"}
        try:
            library.rename(directory(), item.key, self.name)
            refresh(context)
        except (ValueError, OSError, UnicodeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_OT_library_delete(bpy.types.Operator):
    bl_idname = "vfx_studio.library_delete"
    bl_description = (
        "Permanently delete only the selected preset file; existing scene effects remain"
    )
    bl_label = "Delete Preset File (Not Undoable)"

    def execute(self, context):
        item = selected(context)
        if item is None:
            return {"CANCELLED"}
        try:
            library.remove(directory(), item.key)
            refresh(context)
        except (ValueError, OSError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class VFX_PT_library(bpy.types.Panel):
    bl_label = "User Preset Library"
    bl_idname = "VFX_PT_library"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VFX"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.operator("vfx_studio.library_refresh", icon="FILE_REFRESH")
        layout.template_list(
            "VFX_UL_library",
            "",
            context.window_manager,
            "vfx_library_entries",
            context.window_manager,
            "vfx_library_index",
            rows=4,
        )
        item = selected(context)
        if item:
            module = MODULES.get(item.module)
            layout.label(text=module.label if module else item.module)
        row = layout.row(align=True)
        save = row.row(align=True)
        try:
            root = core.resolve(context.object)
            save.enabled = root is not None and root["vfx_module"] not in {
                "trail.ribbon",
                "core.composition",
                "simulation.cloth",
            }
        except ValueError:
            save.enabled = False
        save.operator("vfx_studio.library_save", text="Save New", icon="ADD")
        create = row.row(align=True)
        create.enabled = item is not None
        create.operator("vfx_studio.library_load", text="Create", icon="IMPORT")
        row = layout.row()
        row.enabled = selected(context) is not None
        row.operator("vfx_studio.library_rename", text="Rename")
        row.operator("vfx_studio.library_delete", text="Delete File", icon="TRASH")
        if context.window_manager.vfx_library_errors:
            layout.label(
                text=f"{context.window_manager.vfx_library_errors} invalid entries skipped",
                icon="ERROR",
            )
        layout.label(text="Parameter snapshots; files are outside .blend")
        layout.label(text="Use Load Preset for external JSON files")


CLASSES = (
    VFX_PG_library_entry,
    VFX_UL_library,
    VFX_OT_library_refresh,
    VFX_OT_library_save,
    VFX_OT_library_load,
    VFX_OT_library_rename,
    VFX_OT_library_delete,
    VFX_PT_library,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.vfx_library_entries = CollectionProperty(type=VFX_PG_library_entry)
    bpy.types.WindowManager.vfx_library_index = IntProperty(default=0, min=0)
    bpy.types.WindowManager.vfx_library_errors = IntProperty(default=0, min=0)


def unregister():
    for name in ("vfx_library_entries", "vfx_library_index", "vfx_library_errors"):
        delattr(bpy.types.WindowManager, name)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
