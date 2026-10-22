"""Exercise the built extension in isolated Blender preferences, never the user's."""

import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
blender = os.environ.get("BLENDER_BIN", "blender")
subprocess.run([sys.executable, str(ROOT / "tools/build.py")], check=True)
version = tomllib.loads(
    (ROOT / "blender_vfx_studio/blender_manifest.toml").read_text(encoding="utf-8")
)["version"]
archive = ROOT / "dist" / f"blender-vfx-studio-{version}.zip"
(ROOT / "work").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="install-", dir=ROOT / "work") as temporary:
    directory = Path(temporary)
    (directory / "extensions/blender_org").mkdir(parents=True)
    env = dict(
        os.environ,
        BLENDER_USER_CONFIG=str(directory / "config"),
        BLENDER_USER_EXTENSIONS=str(directory / "extensions"),
    )

    def run(*args):
        subprocess.run([blender, *args], env=env, cwd=directory, check=True)

    run("--command", "extension", "validate", str(archive))
    run("--command", "extension", "install-file", "-r", "user_default", "-e", str(archive))
    run(
        "-b",
        "--python-exit-code",
        "1",
        "--python-expr",
        "import bpy; assert 'bl_ext.user_default.blender_vfx_studio' in bpy.context.preferences.addons; "
        "assert bpy.ops.vfx_studio.create()=={'FINISHED'}; print('INSTALLED_ENABLED_OK')",
    )
    run("--command", "extension", "remove", "blender_vfx_studio")
    run(
        "-b",
        "--python-exit-code",
        "1",
        "--python-expr",
        "import bpy; assert 'bl_ext.user_default.blender_vfx_studio' not in bpy.context.preferences.addons; "
        "assert not hasattr(bpy.types, 'VFX_PT_main'); print('UNINSTALLED_OK')",
    )
print("EXTENSION_LIFECYCLE_OK")
