"""CPU-safe test entry point. BLENDER_BIN can select a Blender executable."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
blender = os.environ.get("BLENDER_BIN", "blender")
for pattern in ("test_timing.py", "test_presets.py"):
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", pattern],
        check=True,
    )

base = [blender, "-b", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1"]
subprocess.run(base + ["--python", "tests/test_blender.py"], check=True)
subprocess.run(
    base + [str(ROOT / "work/native.blend"), "--python", "tests/native_reopen.py"], check=True
)
