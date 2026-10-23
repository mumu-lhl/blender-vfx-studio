"""One-off delivery of already reviewed public data, without adding binaries to Git history."""

import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path

manifest = json.loads(Path("review-evidence.json").read_text())
assert manifest["tag"] == "v0.22.1"
assert manifest["filename"] == "blender-vfx-studio-combat-review-0.22.1.zip"
repository = os.environ["GH_REPO"]
output = Path("review-upload")
output.mkdir()
archive = output / manifest["filename"]
with archive.open("wb") as destination:
    for index, part in enumerate(manifest["parts"]):
        local = output / f"part-{index}"
        with local.open("wb") as stream:
            subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{repository}/git/blobs/{part['sha']}",
                    "-H",
                    "Accept: application/vnd.github.raw+json",
                ],
                stdout=stream,
                check=True,
            )
        data = local.read_bytes()
        assert len(data) == part["size"]
        assert hashlib.sha256(data).hexdigest() == part["sha256"]
        destination.write(data)
        local.unlink()
assert archive.stat().st_size == manifest["size"]
assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest["sha256"]
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    record = json.loads(bundle.read("review-record.json"))
    assert record["sample_count"] == 54
    for case in record["cases"]:
        movie = bundle.read(case["folder"] + "/combat.mp4")
        assert hashlib.sha256(movie).hexdigest() == case["movie_sha256"]

release = json.loads(
    subprocess.check_output(
        ["gh", "api", f"repos/{repository}/releases/tags/{manifest['tag']}"], text=True
    )
)
existing = next((a for a in release["assets"] if a["name"] == archive.name), None)
if existing:
    # A rerun may finish checksums after a previously successful asset upload.
    subprocess.run(
        [
            "gh",
            "release",
            "download",
            manifest["tag"],
            "-p",
            archive.name,
            "-D",
            str(output / "existing"),
        ],
        check=True,
    )
    assert (
        hashlib.sha256((output / "existing" / archive.name).read_bytes()).hexdigest()
        == manifest["sha256"]
    )
else:
    subprocess.run(["gh", "release", "upload", manifest["tag"], str(archive)], check=True)
subprocess.run(
    ["gh", "release", "download", manifest["tag"], "-p", "SHA256SUMS", "-D", str(output)],
    check=True,
)
checksums = output / "SHA256SUMS"
lines = checksums.read_text().splitlines()
matching = [line.split() for line in lines if line.split()[-1] == archive.name]
if matching:
    assert matching[0][0] == manifest["sha256"]
else:
    lines.append(f"{manifest['sha256']}  {archive.name}")
checksums.write_text("\n".join(lines) + "\n")
subprocess.run(
    ["gh", "release", "upload", manifest["tag"], str(checksums), "--clobber"], check=True
)
print("EXACT_REVIEW_ARCHIVE_AND_CHECKSUM_PUBLISHED", manifest["sha256"])
