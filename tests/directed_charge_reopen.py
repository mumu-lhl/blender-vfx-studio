"""Append the directed charge using native Blender only, including its node keys."""

import sys
from pathlib import Path

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
path = Path(__file__).resolve().parents[1] / "work/directed-charge.blend"
with bpy.data.libraries.load(str(path)) as (available, requested):
    requested.collections = available.collections
bundle = next(c for c in requested.collections if c.get("vfx_bundle_version"))
bpy.context.scene.collection.children.link(bundle)
root = next(o for o in bundle.objects if o.get("vfx_id") == bundle["vfx_bundle_root"])
member = next(o for o in root.children if o.get("vfx_module") == "shader.shield")
tree = member.children[0].modifiers[0].node_group
assert "Artist retained" in tree.nodes
for frame, expected in ((49, 0.9), (32, 2.65), (49, 0.9)):
    bpy.context.scene.frame_set(frame)
    assert abs(tree.nodes["Nucleus Stored Size"].outputs[0].default_value - expected) < 1e-5
    assert member.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
bpy.context.scene.frame_set(56)
assert not any(
    o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    for o in root.children_recursive
    if o.get("vfx_role") == "layer"
)
print("DIRECTED_CHARGE_NATIVE_NODE_ANIMATION_OK")
