"""Consolidate an existing release's PNGs after verifying the uploaded replacement."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.build_preview_bundle import build  # noqa: E402


def gh(*arguments):
    return subprocess.check_output(["gh", *arguments], text=True)


def verify(package, images):
    """The uploaded replacement must contain every original PNG byte."""
    with zipfile.ZipFile(package) as archive:
        if archive.testzip() is not None:
            raise ValueError("Preview archive failed its CRC check")
        names = {n.split("/", 1)[-1]: n for n in archive.namelist() if n.endswith(".png")}
        for image in images:
            if image.name not in names or archive.read(names[image.name]) != image.read_bytes():
                raise ValueError(f"Uploaded archive does not preserve {image.name}")


def repack(repository, tag, folder):
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository) or not re.fullmatch(
        r"v[0-9]+\.[0-9]+\.[0-9]+", tag
    ):
        raise ValueError("Specify owner/repository and a version tag such as v0.22.2")
    release = json.loads(gh("api", f"repos/{repository}/releases/tags/{tag}"))
    assets = {a["name"]: a for a in release["assets"]}
    pngs = [a for a in assets.values() if a["name"].endswith(".png")]
    name = f"blender-vfx-studio-previews-{tag[1:]}.zip"
    if not pngs:
        if name not in assets:
            raise ValueError("Release has neither PNG previews nor a preview archive")
        print(f"{tag}: previews are already bundled")
        return
    original, packaged, downloaded = (folder / n for n in ("original", "packaged", "downloaded"))
    gh(
        "release",
        "download",
        tag,
        "--repo",
        repository,
        "--dir",
        str(original),
        "--pattern",
        "*.png",
        "--pattern",
        "*.zip",
        "--pattern",
        "SHA256SUMS",
    )
    for path in original.iterdir():
        data = path.read_bytes()
        expected = assets[path.name]
        if len(data) != expected["size"] or (
            expected.get("digest")
            and expected["digest"] != "sha256:" + hashlib.sha256(data).hexdigest()
        ):
            raise ValueError(f"Original asset digest mismatch: {path.name}")
    for line in (original / "SHA256SUMS").read_text().splitlines():
        digest, filename = line.split(maxsplit=1)
        filename = filename.lstrip("*")
        if Path(filename).name != filename:
            raise ValueError("Checksum filenames must refer to release attachments")
        if hashlib.sha256((original / filename).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Original checksum mismatch: {filename}")
    images = sorted(original.glob("*.png"))
    if len(images) != len(pngs):
        raise ValueError("Not all release PNGs were downloaded")
    if name in assets:
        # Allows retry after a partial cleanup, keeping the previously verified full archive.
        package = original / name
    else:
        package = build(original, packaged, tag[1:])
        verify(package, images)
        gh("release", "upload", tag, str(package), "--repo", repository)
    gh(
        "release",
        "download",
        tag,
        "--repo",
        repository,
        "--dir",
        str(downloaded),
        "--pattern",
        name,
    )
    remote = downloaded / name
    if remote.read_bytes() != package.read_bytes():
        raise ValueError("Uploaded/downloaded preview archive differs")
    verify(remote, images)
    print(
        f"VERIFIED_UPLOADED_PREVIEWS {len(images)} PNGs; SHA256 {hashlib.sha256(remote.read_bytes()).hexdigest()}"
    )
    packaged.mkdir(exist_ok=True)
    checksum = packaged / "SHA256SUMS"
    packages = {p.name: p for p in original.glob("*.zip")}
    packages[name] = remote
    checksum.write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {n}\n"
            for n, p in sorted(packages.items())
        )
    )
    gh("release", "upload", tag, str(checksum), "--repo", repository, "--clobber")
    checksum_download = folder / "checksums"
    gh(
        "release",
        "download",
        tag,
        "--repo",
        repository,
        "--dir",
        str(checksum_download),
        "--pattern",
        "SHA256SUMS",
    )
    if (checksum_download / "SHA256SUMS").read_bytes() != checksum.read_bytes():
        raise ValueError("Published checksums differ")
    latest = json.loads(gh("api", f"repos/{repository}/releases/tags/{tag}"))
    current = {a["name"]: a["id"] for a in latest["assets"]}
    if latest["id"] != release["id"] or any(current.get(a["name"]) != a["id"] for a in pngs):
        raise ValueError("Original preview attachments changed during repackaging")
    for asset in pngs:
        gh("api", "--method", "DELETE", f"repos/{repository}/releases/assets/{asset['id']}")
    final = json.loads(gh("api", f"repos/{repository}/releases/tags/{tag}"))
    if any(a["name"].endswith(".png") for a in final["assets"]):
        raise ValueError("Release still has loose PNG attachments")
    remaining = {a["name"]: a for a in final["assets"]}
    for filename, asset in assets.items():
        if filename.endswith(".zip") and remaining[filename]["id"] != asset["id"]:
            raise ValueError(f"Existing ZIP was replaced: {filename}")
    notes = folder / "notes.md"
    explanation = f"预览图片已统一整理为 `{name}`，解压后浏览，不用于安装。原插件、示例与检查 ZIP 保持不变；SHA256SUMS 已加入预览包。"
    if explanation not in final["body"]:
        notes.write_text(final["body"].rstrip() + "\n\n" + explanation + "\n")
        gh("release", "edit", tag, "--repo", repository, "--notes-file", str(notes))
    print(f"REPACK_COMPLETE {tag}: {len(pngs)} loose PNGs replaced; existing ZIP IDs unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="vfx-release-previews-") as temporary:
        repack(args.repo, args.tag, Path(temporary))
