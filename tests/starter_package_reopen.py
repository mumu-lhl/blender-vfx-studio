"""Validate the actual rendered starter ZIP with native Blender only."""

import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
version = tomllib.loads(
    (ROOT / "blender_vfx_studio/blender_manifest.toml").read_text(encoding="utf-8")
)["version"]
package = ROOT / "dist" / f"blender-vfx-studio-examples-{version}.zip"
expected = {
    "energy-charge": ("core.composition", 48),
    "impact-burst": ("core.composition", 24),
    "arc-slash": ("mesh.slash", 18),
    "stylized-fire": ("core.composition", 52),
    "quality/stylized-fire-low": ("core.composition", 52),
    "quality/stylized-fire-high": ("core.composition", 52),
    "dash-echoes": ("core.composition", 30),
    "quality/dash-echoes-low": ("core.composition", 30),
    "quality/dash-echoes-high": ("core.composition", 30),
    "magic-circle": ("core.composition", 72),
    "quality/magic-circle-low": ("core.composition", 72),
    "quality/magic-circle-high": ("core.composition", 72),
    "dust-impact": ("core.composition", 32),
    "quality/dust-impact-low": ("core.composition", 32),
    "quality/dust-impact-high": ("core.composition", 32),
    "lightning-strike": ("core.composition", 18),
    "quality/lightning-strike-low": ("core.composition", 18),
    "quality/lightning-strike-high": ("core.composition", 18),
}
assert not any("blender_vfx_studio" in name for name in sys.modules)
with tempfile.TemporaryDirectory() as folder, zipfile.ZipFile(package) as archive:
    assert set(archive.namelist()) == {
        *(key + ".blend" for key in expected),
        "README.md",
        "LICENSE",
    }
    for key, (module, duration) in expected.items():
        member = key + ".blend"
        assert 0 < archive.getinfo(member).file_size <= 16 * 1024 * 1024
        path = Path(folder) / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(archive.read(member))
        bpy.ops.wm.read_factory_settings(use_empty=True)
        with bpy.data.libraries.load(str(path), link=False) as (available, requested):
            assert not available.cameras and not available.scenes
            assert len(available.images) == (1 if key == "impact-burst" else 0)
            assert not available.worlds
            assert len(available.collections) == 1
            requested.collections = available.collections
        bundle = requested.collections[0]
        if key == "impact-burst":
            assert len(bpy.data.images) == 1
            image = next(iter(bpy.data.images))
            assert image.packed_file and image.get("vfx_burst_heat") == 1
        assert bundle["vfx_bundle_version"] == 1
        root = next(
            obj
            for obj in bundle.objects
            if obj.get("vfx_role") == "controller"
            and obj.get("vfx_id") == bundle["vfx_bundle_root"]
        )
        assert root["vfx_module"] == module
        assert root["start"] == 1 and root["duration"] == duration and not root["loop"]
        assert bundle.preview.image_size[:] == (256, 256) and bundle.preview.is_image_custom
        assert (
            max(value for i, value in enumerate(bundle.preview.image_pixels_float) if i % 4 != 3)
            > 0.5
        )
        bpy.context.scene.collection.children.link(bundle)
        bpy.context.view_layer.update()
        for frame in (16, 0, 7, 1 + int(duration), 7):
            bpy.context.scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            count = sum(
                len(obj.evaluated_get(graph).data.vertices)
                for obj in root.children_recursive
                if obj.get("vfx_role") == "layer"
            )
            assert (count > 0) if frame in (7, 16) else count == 0, (key, frame, count)
        print("PACKAGED_STARTER_NATIVE_OK", key)
print("STARTER_PACKAGE_NATIVE_REOPEN_OK")
