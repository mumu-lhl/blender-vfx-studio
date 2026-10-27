"""Measure this saved shot with/without VFX; these are not viewport FPS measurements."""

import argparse
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not bpy.data.filepath or any("blender_vfx_studio" in name for name in sys.modules):
        raise RuntimeError("Open the saved shot in a fresh process without the extension")
    scene = bpy.context.scene
    folder = Path(bpy.data.filepath).parent
    settings = json.loads((folder / "character-settings.json").read_text())
    effects = bpy.data.collections["Combat VFX • toggle for comparison"]
    frames = [32, settings["contact"]["frame"] + 4, settings["contact"]["frame"] + 12]
    evaluation = []
    render = []
    for enabled in (False, True):
        effects.hide_render = effects.hide_viewport = not enabled
        bpy.context.view_layer.update()
        for trial in range(12):
            for frame in frames:
                scene.frame_set(frame - 1)
                started = time.perf_counter()
                scene.frame_set(frame)
                bpy.context.evaluated_depsgraph_get().update()
                evaluation.append(
                    {
                        "fx": enabled,
                        "warmup": trial < 3,
                        "frame": frame,
                        "milliseconds": (time.perf_counter() - started) * 1000,
                    }
                )
    # Alternate matched renders to expose ordering effects; retain the first two as warmup.
    effects.hide_viewport = False
    if not args.evaluation_only:
        for index, (frame, enabled) in enumerate(
            [(frames[0], True), (frames[0], False)]
            + [
                (frame, enabled)
                for i, frame in enumerate(frames)
                for enabled in ((False, True) if i % 2 == 0 else (True, False))
            ]
        ):
            effects.hide_render = not enabled
            scene.frame_set(frame)
            scene.render.filepath = str(
                folder / f"performance-{'fx' if enabled else 'bare'}-{frame:04d}.png"
            )
            started = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            row = {
                "fx": enabled,
                "warmup": index < 2,
                "frame": frame,
                "seconds": time.perf_counter() - started,
            }
            render.append(row)
            print("CHARACTER_PERFORMANCE", json.dumps(row), flush=True)
    renderer = "not queried (no rendered context)"
    if render:
        import gpu

        renderer = {
            "vendor": gpu.platform.vendor_get(),
            "renderer": gpu.platform.renderer_get(),
            "version": gpu.platform.version_get(),
        }
    quota = Path("/sys/fs/cgroup/cpu.max")
    summary = {}
    for enabled in (False, True):
        values = sorted(
            r["milliseconds"] for r in evaluation if r["fx"] == enabled and not r["warmup"]
        )
        summary["fx" if enabled else "bare"] = {
            "scene_evaluation_median_ms": statistics.median(values),
            "scene_evaluation_p95_ms": values[int((len(values) - 1) * 0.95)],
            "measured_samples": len(values),
        }
    report = {
        "blender": bpy.app.version_string,
        "platform": platform.platform(),
        "cpu_quota": quota.read_text().strip() if quota.exists() else None,
        "blender_threads": scene.render.threads,
        "lp_num_threads": os.getenv("LP_NUM_THREADS"),
        "software_gl_requested": os.getenv("LIBGL_ALWAYS_SOFTWARE") == "1",
        "gl": renderer,
        "engine": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "samples": scene.eevee.taa_render_samples,
        "source_sha256": settings["source_sha256"],
        "evaluation": evaluation,
        "evaluation_summary": summary,
        "renders": render,
        "limits": [
            "Headless scene evaluation and render wall time, not viewport FPS",
            "Two warmup renders and three matched frame pairs; too few for a render p95",
            "The same saved scene is used; only its VFX collection is excluded",
            "Evaluation excludes the collection from the viewport dependency graph; render comparison only excludes it from rendering",
        ],
    }
    (folder / "performance.json").write_text(json.dumps(report, indent=2) + "\n")
    print("CHARACTER_PERFORMANCE_COMPLETE", json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
