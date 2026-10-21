"""Build a reproducible extension ZIP without Blender or third-party packages."""

import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "blender_vfx_studio"
version = tomllib.loads((SOURCE / "blender_manifest.toml").read_text())["version"]
output = ROOT / "dist" / f"blender-vfx-studio-{version}.zip"
output.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(SOURCE.rglob("*")):
        if path.is_file() and (path.suffix in {".py", ".toml"}):
            info = zipfile.ZipInfo(path.relative_to(SOURCE).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    info = zipfile.ZipInfo("LICENSE", (2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, (ROOT / "LICENSE").read_bytes())
print(output)
