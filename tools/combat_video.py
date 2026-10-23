"""Encode a complete native review sequence; this does not approve its motion."""

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path


def sequence_digest(folder):
    """Bind a movie's encoding record to the exact settings and source PNGs."""
    folder = Path(folder)
    digest = hashlib.sha256((folder / "render-settings.json").read_bytes())
    for frame in range(1, 37):
        digest.update((folder / f"combat-{frame:04d}.png").read_bytes())
    return digest.hexdigest()


def encode(folder):
    folder = Path(folder)
    settings = json.loads((folder / "render-settings.json").read_text(encoding="utf-8"))
    if (
        settings.get("rendered_frames") != list(range(1, 37))
        or settings.get("fps") != 24
        or settings.get("resolution") != [960, 540]
    ):
        raise ValueError("Render a complete 36-frame 960x540 sequence at 24 fps before encoding")
    for frame in range(1, 37):
        path = folder / f"combat-{frame:04d}.png"
        with path.open("rb") as stream:
            header = stream.read(24)
        if (
            len(header) != 24
            or header[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            or struct.unpack(">II", header[16:24]) != (960, 540)
        ):
            raise ValueError(f"Expected a 960x540 PNG: {path}")
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("Install FFmpeg (including ffprobe) before encoding review videos")
    source_digest = sequence_digest(folder)
    destination = folder / "combat.mp4"
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        movie = Path(temporary) / "combat.mp4"
        subprocess.run(
            [
                ffmpeg,
                "-v",
                "error",
                "-framerate",
                "24",
                "-start_number",
                "1",
                "-i",
                str(folder / "combat-%04d.png"),
                "-frames:v",
                "36",
                "-c:v",
                "libx264",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-an",
                "-movflags",
                "+faststart",
                str(movie),
            ],
            check=True,
        )
        info = json.loads(
            subprocess.check_output(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=width,height,r_frame_rate,nb_frames,duration",
                    "-of",
                    "json",
                    str(movie),
                ],
                text=True,
            )
        )["streams"][0]
        if not (
            info["width"] == 960
            and info["height"] == 540
            and info["r_frame_rate"] == "24/1"
            and info["nb_frames"] == "36"
            and abs(float(info["duration"]) - 1.5) < 0.001
        ):
            raise ValueError(f"Unexpected video stream: {info}")
        movie.replace(destination)
    info["source_sha256"] = source_digest
    (folder / "video-info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(f"ENCODED_REVIEW_VIDEO {destination} (36 frames, 24 fps; playback not reviewed)")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "folder", type=Path, help="Folder containing combat-0001.png through combat-0036.png"
    )
    encode(parser.parse_args().folder)
