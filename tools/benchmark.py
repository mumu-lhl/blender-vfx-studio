"""Measure native CPU evaluation, excluding viewport drawing and rendering.

Run: blender -b --factory-startup --python tools/benchmark.py
"""

import argparse
import json
import math
import os
import platform
import statistics
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import composition, core, simulation  # noqa: E402


def benchmark(instances, frames):
    result = {
        "blender": bpy.app.version_string,
        "platform": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "instances": instances,
        "frames": frames,
        "quality": "LOW",
        "cases": [],
    }
    for kind in ("ring", "slash", "particle", "emitter", "cloth", "composition"):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        roots = []
        bake_seconds = 0.0
        created = time.perf_counter()
        for _ in range(instances):
            if kind == "ring":
                root = core.create(bpy.context, quality="LOW")
            elif kind == "slash":
                root = core.create(bpy.context, "ARC_SLASH", "LOW")
            elif kind == "particle":
                root = core.create_particle(bpy.context)
            elif kind == "emitter":
                root = core.create_emitter(bpy.context)
            elif kind == "cloth":
                root = simulation.create(bpy.context)
                start = time.perf_counter()
                simulation.bake(bpy.context, root)
                bake_seconds += time.perf_counter() - start
            else:
                root = composition.create(
                    bpy.context,
                    [core.create(bpy.context, quality="LOW"), core.create_particle(bpy.context)],
                )
            root["loop"] = True
            root.update_tag()
            roots.append(root)
        creation_seconds = time.perf_counter() - created
        layers = [
            o
            for o in bpy.data.objects
            if o.type == "MESH" and o.get("vfx_role") == "layer" and not o.hide_get()
        ]
        timings = []
        for frame in range(1, frames + 4):
            started = time.perf_counter()
            bpy.context.scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            bpy.context.view_layer.update()
            meshes = [obj.evaluated_get(graph).data for obj in layers]
            # Access evaluated geometry so lazy native work is included in the measurement.
            vertices = sum(len(mesh.vertices) for mesh in meshes)
            faces = sum(len(mesh.polygons) for mesh in meshes)
            if frame > 3:
                timings.append((time.perf_counter() - started) * 1000)
        # Counts use a middle active frame, not a loop boundary with collapsed geometry.
        bpy.context.scene.frame_set(9)
        graph = bpy.context.evaluated_depsgraph_get()
        meshes = [obj.evaluated_get(graph).data for obj in layers]
        vertices = sum(len(mesh.vertices) for mesh in meshes)
        faces = sum(len(mesh.polygons) for mesh in meshes)
        case = {
            "module": kind,
            "objects": len(bpy.data.objects),
            "vertices": vertices,
            "faces": faces,
            "creation_seconds": creation_seconds,
            "cloth_bake_seconds": bake_seconds,
            "median_ms": statistics.median(timings),
            "p95_ms": sorted(timings)[math.ceil(len(timings) * 0.95) - 1],
        }
        result["cases"].append(case)
        print(json.dumps(case), flush=True)
    return result


def main():
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError(
            "Run in a new background process with --factory-startup and no .blend file"
        )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instances", type=int, default=8, choices=range(1, 33))
    parser.add_argument("--frames", type=int, default=30, choices=range(10, 241))
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    result = benchmark(args.instances, args.frames)
    output = ROOT / "work/benchmark.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("CPU_EVALUATION_BENCHMARK_OK", output)


if __name__ == "__main__":
    main()
