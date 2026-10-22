"""Install the checksum-verified official Blender build for a CI runner."""

import argparse
import hashlib
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def archive_name(version, system=None, machine=None):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Use a complete Blender release version, such as 5.2.2")
    system, machine = system or platform.system(), (machine or platform.machine()).lower()
    if system == "Linux" and machine in {"x86_64", "amd64"}:
        suffix = "linux-x64.tar.xz"
    elif system == "Windows" and machine in {"x86_64", "amd64"}:
        suffix = "windows-x64.zip"
    elif system == "Darwin" and machine in {"arm64", "aarch64"}:
        suffix = "macos-arm64.dmg"
    else:
        raise ValueError(f"No supported Blender CI build for {system} {machine}")
    return f"blender-{version}-{suffix}"


def checksum(text, filename):
    matches = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].lstrip("*") == filename:
            if not re.fullmatch(r"[a-fA-F0-9]{64}", fields[0]):
                raise ValueError("Invalid official SHA256 entry")
            matches.append(fields[0].lower())
    if len(matches) != 1:
        raise ValueError("Expected exactly one official checksum for " + filename)
    return matches[0]


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(url, path, expected):
    if path.is_file() and digest(path) == expected:
        return
    temporary = path.with_suffix(path.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
        if digest(temporary) != expected:
            raise ValueError("Downloaded Blender checksum does not match the official release")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def install(version, directory):
    name = archive_name(version)
    base = "https://download.blender.org/release/Blender" + ".".join(version.split(".")[:2])
    with urllib.request.urlopen(f"{base}/blender-{version}.sha256", timeout=30) as response:
        expected = checksum(response.read(1024 * 1024).decode(), name)
    directory.mkdir(parents=True, exist_ok=True)
    archive = directory / name
    download(f"{base}/{name}", archive, expected)
    print(f"Verified {name}: {expected}", flush=True)
    if name.endswith(".tar.xz"):
        with tarfile.open(archive) as package:
            package.extractall(directory, filter="data")
        binary = directory / name.removesuffix(".tar.xz") / "blender"
    elif name.endswith(".zip"):
        with zipfile.ZipFile(archive) as package:
            for member in package.namelist():
                if not (directory / member).resolve().is_relative_to(directory.resolve()):
                    raise ValueError("Archive member escapes extraction directory")
            package.extractall(directory)
        binary = directory / name.removesuffix(".zip") / "blender.exe"
    else:
        app = directory / f"blender-{version}-macos-arm64" / "Blender.app"
        app.parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="blender-mount-", dir=directory) as mount:
            subprocess.run(
                ["hdiutil", "attach", "-readonly", "-nobrowse", "-mountpoint", mount, str(archive)],
                check=True,
            )
            try:
                subprocess.run(["ditto", str(Path(mount) / "Blender.app"), str(app)], check=True)
            finally:
                subprocess.run(["hdiutil", "detach", mount], check=True)
        binary = app / "Contents/MacOS/Blender"
    if not binary.is_file():
        raise ValueError("Blender executable is missing from the official package")
    return binary.resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="5.2.2")
    args = parser.parse_args()
    binary = install(args.version, ROOT / "work/blender-tools")
    for key, value in (
        ("GITHUB_ENV", "BLENDER_BIN=" + str(binary)),
        ("GITHUB_PATH", str(binary.parent)),
    ):
        if os.environ.get(key):
            with open(os.environ[key], "a", encoding="utf-8") as out:
                out.write(value + "\n")
    subprocess.run([str(binary), "-b", "--factory-startup", "--version"], check=True)


if __name__ == "__main__":
    main()
