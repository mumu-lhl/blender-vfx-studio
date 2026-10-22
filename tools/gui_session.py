"""Open a scratch GUI session and record state for manual interaction checks.

Run: blender --factory-startup --python tools/gui_session.py
The preset folder and JSON state are isolated under work/gui/. No user file is loaded.
"""

import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import library_ui, register, simulation  # noqa: E402

if bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
    raise RuntimeError("Use a new GUI process with --factory-startup and no .blend file")
WORK = ROOT / "work/gui"
WORK.mkdir(parents=True, exist_ok=True)
(WORK / "presets").mkdir(exist_ok=True)
STOP = WORK / "stop"
STOP.unlink(missing_ok=True)
register()
library_ui.directory = lambda: str(WORK / "presets")
bpy.context.preferences.view.show_splash = False
last = None
configured = False


def record():
    global last, configured
    windows = bpy.context.window_manager.windows
    if not windows:
        return 0.25
    with bpy.context.temp_override(window=windows[0]):
        if not configured:
            for area in windows[0].screen.areas:
                if area.type == "VIEW_3D":
                    area.spaces.active.show_region_ui = True
            configured = True
        controllers = []
        for obj in bpy.data.objects:
            if obj.get("vfx_role") != "controller":
                continue
            entry = {"name": obj.name, "module": obj.get("vfx_module"), "id": obj.get("vfx_id")}
            if obj["vfx_module"] == "simulation.cloth":
                try:
                    _, output, cloth = simulation.parts(obj)
                    entry.update(
                        cache=simulation.state(bpy.context, obj),
                        mass=cloth.settings.mass,
                        poses=len(output.data.shape_keys.key_blocks)
                        if output.data.shape_keys
                        else 0,
                    )
                except ValueError as error:
                    entry["error"] = str(error)
            controllers.append(entry)
        state = {
            "controllers": controllers,
            "active": bpy.context.object.name if bpy.context.object else None,
        }
        (WORK / "state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if state != last:
            print("GUI_STATE", json.dumps(state, ensure_ascii=False), flush=True)
            last = state
        if STOP.exists():
            bpy.ops.wm.quit_blender()
            return None
    return 1.0


bpy.app.timers.register(record, first_interval=1.0)
