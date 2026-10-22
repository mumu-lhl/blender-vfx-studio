"""Native browser operations use a temporary library, never the real user folder."""

import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon
from blender_vfx_studio import core, library, library_ui

bpy.ops.wm.read_factory_settings(use_empty=True)
addon.register()
with tempfile.TemporaryDirectory(dir=ROOT / "work") as folder:
    original = library_ui.directory
    library_ui.directory = lambda: folder
    try:
        root = core.create_particle(bpy.context)
        root["count"] = 17
        assert bpy.ops.vfx_studio.library_save() == {"FINISHED"}
        assert len(bpy.context.window_manager.vfx_library_entries) == 1
        assert bpy.ops.vfx_studio.library_rename(name="Particle Preset") == {"FINISHED"}
        assert bpy.context.window_manager.vfx_library_entries[0].name == "Particle Preset"
        assert bpy.ops.vfx_studio.library_refresh() == {"FINISHED"}
        assert bpy.ops.vfx_studio.library_load() == {"FINISHED"}
        clone = bpy.context.object
        assert clone != root and clone["count"] == 17
        assert clone["vfx_id"] != root["vfx_id"]
        assert bpy.ops.vfx_studio.library_delete() == {"FINISHED"}
        assert not list(Path(folder).iterdir())
        assert len(bpy.context.window_manager.vfx_library_entries) == 0
        assert root.name in bpy.data.objects and clone.name in bpy.data.objects
        image = bpy.data.images.new("Temporary Atlas", 4, 4, alpha=True)
        image.filepath_raw = str(Path(folder) / "atlas.png")
        image.file_format = "PNG"
        image.save()
        flipbook = core.create_flipbook(bpy.context, image, 1, 1)
        key = library.save(folder, core.preset_snapshot(flipbook))
        Path(image.filepath_raw).unlink()
        counts = (len(bpy.data.objects), len(bpy.data.meshes))
        try:
            core.create_from_preset(bpy.context, library.load(folder, key))
            raise AssertionError("Missing atlas must fail before effect creation")
        except ValueError:
            pass
        assert (len(bpy.data.objects), len(bpy.data.meshes)) == counts
        assert (Path(folder) / key).is_file()
        library.remove(folder, key)
    finally:
        library_ui.directory = original
addon.unregister()
assert not hasattr(bpy.types.WindowManager, "vfx_library_entries")
print("PRESET_LIBRARY_OPERATORS_OK")
