"""Package release PNG previews separately from installable Blender assets."""

import argparse
import hashlib
import os
import re
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(source, output, version):
    """Preserve every PNG's relative path and bytes in a reproducible archive."""
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[.-][A-Za-z0-9]+)*", version):
        raise ValueError("Use a version such as 0.22.3")
    source, output = Path(source), Path(output)
    images = sorted(source.rglob("*.png"))
    if not source.is_dir() or not images:
        raise ValueError("The preview directory must contain PNG images")
    if any(path.is_symlink() or not path.is_file() for path in images):
        raise ValueError("Preview PNGs must be regular files")
    prefix = f"blender-vfx-studio-previews-{version}"
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"{prefix}.zip"
    with tempfile.NamedTemporaryFile(dir=output, suffix=".zip", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:

            def write(name, data):
                info = zipfile.ZipInfo(f"{prefix}/{name}", (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)

            checksums = []
            for path in images:
                relative = path.relative_to(source).as_posix()
                data = path.read_bytes()
                write(relative, data)
                checksums.append(f"{hashlib.sha256(data).hexdigest()}  {relative}\n")
            write("SHA256SUMS", "".join(checksums).encode())
            write(
                "README.md",
                (
                    f"# Blender VFX Studio {version} 预览图\n\n"
                    "本包用于浏览效果图片，不是插件安装包，也不包含可编辑效果资产。\n\n"
                    "- 安装插件：下载 blender-vfx-studio-版本.zip。\n"
                    "- 使用完整效果：下载 blender-vfx-studio-examples-版本.zip。\n"
                    "- 本包保留原始 PNG 与目录；SHA256SUMS 可核对各张图片。\n\n"
                    "预览图不代表实时动画、设备帧率或整体艺术品质已经验收。\n"
                ).encode(),
            )
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "preview")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--version")
    args = parser.parse_args()
    version = (
        args.version
        or tomllib.loads(
            (ROOT / "blender_vfx_studio/blender_manifest.toml").read_text(encoding="utf-8")
        )["version"]
    )
    print(build(args.source, args.output, version))


if __name__ == "__main__":
    main()
