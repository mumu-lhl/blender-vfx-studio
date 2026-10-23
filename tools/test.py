"""CPU-safe test entry point. BLENDER_BIN can select a Blender executable."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
blender = os.environ.get("BLENDER_BIN", "blender")
for pattern in (
    "test_timing.py",
    "test_presets.py",
    "test_library.py",
    "test_fetch_blender.py",
    "test_combat_video.py",
):
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", pattern],
        check=True,
    )

base = [blender, "-b", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1"]
subprocess.run(base + ["--python", "tests/test_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/native.blend"), "--python", "tests/native_reopen.py"], check=True
)

subprocess.run(base + ["--python", "tests/test_flipbook_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/flipbook.blend"), "--python", "tests/flipbook_reopen.py"], check=True
)

subprocess.run(base + ["--python", "tests/test_screen_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/screen.blend"), "--python", "tests/screen_reopen.py"], check=True
)

subprocess.run(base + ["--python", "tests/test_particle_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/particle.blend"), "--python", "tests/particle_reopen.py"], check=True
)

subprocess.run(base + ["--python", "tests/test_trail_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/trail.blend"), "--python", "tests/trail_reopen.py"], check=True
)

subprocess.run(base + ["--python", "tests/test_binding_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/binding.blend"), "--python", "tests/binding_reopen.py"], check=True
)

subprocess.run(base + ["--python", "tests/test_library_blender.py"], check=True)

subprocess.run(base + ["--python", "tests/test_composition_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/composition.blend"), "--python", "tests/composition_reopen.py"],
    check=True,
)

subprocess.run(base + ["--python", "tests/test_simulation_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/simulation.blend"), "--python", "tests/simulation_reopen.py"],
    check=True,
)

subprocess.run(base + ["--python", "tests/test_slash_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/slash.blend"), "--python", "tests/slash_reopen.py"], check=True
)

subprocess.run(base + ["--python", "tests/test_undo_blender.py"], check=True)

subprocess.run(base + ["--python", "tests/test_shield_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/shield.blend"), "--python", "tests/shield_reopen.py"], check=True
)

subprocess.run(base + ["--python", "tests/test_assets_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/assets.blend"), "--python", "tests/assets_reopen.py"], check=True
)

subprocess.run(base + ["--python", "tests/test_sequence_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/sequence.blend"), "--python", "tests/sequence_reopen.py"], check=True
)

subprocess.run(base + ["--python", "tests/test_emitter_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/emitter.blend"), "--python", "tests/emitter_reopen.py"], check=True
)

subprocess.run(base + ["--python", "tests/test_examples_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/examples.blend"), "--python", "tests/examples_reopen.py"], check=True
)

subprocess.run(base + ["--python", "tests/test_impact_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/impact.blend"), "--python", "tests/impact_reopen.py"], check=True
)
