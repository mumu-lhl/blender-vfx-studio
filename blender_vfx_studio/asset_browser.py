"""Use Blender's asset selection while retaining validated, independent VFX imports."""

from textwrap import wrap

import bpy
from bpy_extras.asset_utils import AssetBrowserPanel, SpaceAssetInfo

from . import assets


def selection(asset):
    """Read selection metadata only; drawing the panel must not read .blend files."""
    if asset is None:
        raise ValueError("Select a complete effect collection")
    if asset.id_type != "COLLECTION":
        raise ValueError("Select a collection asset")
    if asset.local_id is not None:
        raise ValueError("Choose an external library; use VFX Duplicate for Current File")
    if asset.is_online:
        raise ValueError("Choose a local .blend library asset")
    if not asset.full_library_path or not asset.name:
        raise ValueError("The selected asset has no local file or collection name")
    return asset.full_library_path, asset.name


class VFX_OT_load_browser_asset(bpy.types.Operator):
    bl_idname = "vfx_studio.load_browser_asset"
    bl_label = "Load VFX with New ID"
    bl_description = "Load the selected complete effect with independent IDs, nodes and animation"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if not SpaceAssetInfo.is_asset_browser_poll(context):
            return False
        active = context.view_layer.objects.active
        if active is not None and active.mode != "OBJECT":
            cls.poll_message_set("Switch to Object Mode before loading a complete effect")
            return False
        try:
            selection(context.asset)
        except ValueError as error:
            cls.poll_message_set(str(error))
            return False
        return True

    def execute(self, context):
        try:
            filepath, name = selection(context.asset)
            assets.load(context, filepath, collection_name=name)
        except (ValueError, OSError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class VFX_PT_asset_browser(AssetBrowserPanel, bpy.types.Panel):
    bl_region_type = "TOOL_PROPS"
    bl_label = "Blender VFX Studio"

    def draw(self, context):
        layout = self.layout
        layout.operator("vfx_studio.load_browser_asset", icon="IMPORT")
        try:
            selection(context.asset)
        except ValueError as error:
            for i, line in enumerate(wrap(str(error), 30)):
                layout.label(text=line, icon="INFO" if i == 0 else "NONE")
        else:
            layout.label(text="Keeps saved time and transform")
            layout.label(text="Use this button for complete VFX")


CLASSES = (VFX_OT_load_browser_asset, VFX_PT_asset_browser)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
