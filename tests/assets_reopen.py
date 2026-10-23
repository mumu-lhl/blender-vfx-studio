"""Imported native composition plays without the extension or a sampling source."""

import bpy

root = bpy.data.objects["Persisted Native Asset"]
controllers = [obj for obj in root.children if obj.get("vfx_role") == "controller"]
assert len(controllers) == 3
source = bpy.data.objects["User Source"]
bpy.data.objects.remove(source, do_unlink=True)
for frame in (13, 7, 13):
    bpy.context.scene.frame_set(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for controller in controllers:
        assert controller["vfx_composition"] == root
        for layer in controller.children:
            if layer.get("vfx_sim_part") == "source":
                continue
            mesh = layer.evaluated_get(depsgraph).data
            assert mesh.vertices
            if controller["vfx_module"] == "simulation.cloth":
                assert layer.data.shape_keys.eval_time > 0
            if controller["vfx_module"] == "trail.ribbon":
                assert controller.get("vfx_source") is None
bpy.context.scene.frame_set(25)
for controller in controllers:
    for layer in controller.children:
        if layer.get("vfx_sim_part") != "source":
            assert not layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
print("ASSETS_NATIVE_REOPEN_OK")

bundle = next(c for c in root.users_collection if c.get("vfx_bundle_version"))
assert bundle.preview.image_size[:] == (2, 2)
assert bundle.preview.is_image_custom
expected = [1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1]
assert all(abs(a - b) < 1 / 255 for a, b in zip(bundle.preview.image_pixels_float, expected))
assert "Fixture Preview" not in bpy.data.images
print("ASSET_PREVIEW_NATIVE_REOPEN_OK")
