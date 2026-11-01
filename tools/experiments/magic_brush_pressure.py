"""Rejected native stroke-pressure study; run on a saved magic review scene."""

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy

assert not any("blender_vfx_studio" in n for n in sys.modules)
s = bpy.context.scene
scene_path = Path(bpy.data.filepath)
mode = scene_path.parent.name
root = next(o for o in s.objects if o.name.startswith("Magic • Seal"))
mesh = root.children[0].data
weights = mesh.attributes["sigil_weight"].data
draw = mesh.attributes["sigil_draw"].data
runs = []
run = []
for i, w in enumerate(weights):
    if abs(w.value - 1.25) < 1e-5:
        run.append(i)
    elif run:
        runs.append(run)
        run = []
if run:
    runs.append(run)
assert len(runs) == 6
for ids in runs:
    phase = min(draw[i].value for i in ids)
    for i in ids:
        t = max(0, min(1, (draw[i].value - phase) / (1 - phase)))
        pressure = 0.35 + 1.45 * math.sin(math.pi * t) ** 0.7 * (
            0.65 + 0.35 * math.sin(math.tau * t)
        )
        weights[i].value *= pressure
mesh.update()
root.update_tag()
s.frame_set(40)
p = Path("work/magic-contrast/probe") / mode
p.mkdir(parents=True, exist_ok=True)
s.render.filepath = str(p / "magic-0040.png")
bpy.ops.render.render(write_still=True)
(p / "record.json").write_text(
    json.dumps(
        {
            "source_scene_sha256": hashlib.sha256(scene_path.read_bytes()).hexdigest(),
            "changed_primary_strokes": len(runs),
            "geometry_vertices": len(mesh.vertices),
            "strength": root["strength"],
            "frame": 40,
        },
        indent=2,
    )
    + "\n"
)
print("MAGIC_BRUSH_WEIGHT_PROBE_COMPLETE", mode)
