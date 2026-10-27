"""Encode a complete native review sequence; this does not approve its motion."""

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

PROFILES = {
    "combat": ("render-settings.json", "rendered_frames", "combat", 36),
    "handoff": ("review-settings.json", "frames", "handoff", 60),
    "character": ("character-settings.json", "frames", "character", 96),
    "magic": ("magic-settings.json", "frames", "magic", 80),
    "dash": ("dash-settings.json", "frames", "dash", 48),
    "fire": ("fire-settings.json", "frames", "fire", 72),
    "dust": ("dust-settings.json", "frames", "dust", 60),
    "lightning": ("lightning-settings.json", "frames", "lightning", 28),
}


def sequence_digest(folder, profile="combat"):
    """Bind a movie's encoding record to the exact settings and source PNGs."""
    folder = Path(folder)
    settings_name, _, prefix, count = PROFILES[profile]
    digest = hashlib.sha256((folder / settings_name).read_bytes())
    for frame in range(1, count + 1):
        digest.update((folder / f"{prefix}-{frame:04d}.png").read_bytes())
    return digest.hexdigest()


def encode(folder, profile="combat"):
    folder = Path(folder)
    settings_name, frames_key, prefix, count = PROFILES[profile]
    settings = json.loads((folder / settings_name).read_text(encoding="utf-8"))
    if (
        settings.get(frames_key) != list(range(1, count + 1))
        or settings.get("fps") != 24
        or settings.get("fps_base", 1) != 1
        or settings.get("resolution") != [960, 540]
    ):
        raise ValueError(
            f"Render a complete {count}-frame 960x540 sequence at 24 fps before encoding"
        )
    for frame in range(1, count + 1):
        path = folder / f"{prefix}-{frame:04d}.png"
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
    source_digest = sequence_digest(folder, profile)
    destination = folder / f"{prefix}.mp4"
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
                str(folder / f"{prefix}-%04d.png"),
                "-frames:v",
                str(count),
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
            and info["nb_frames"] == str(count)
            and abs(float(info["duration"]) - count / 24) < 0.001
        ):
            raise ValueError(f"Unexpected video stream: {info}")
        if sequence_digest(folder, profile) != source_digest:
            raise ValueError("Render sources changed during encoding")
        movie.replace(destination)
    info["source_sha256"] = source_digest
    info["video_sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
    info["profile"] = profile
    info["realtime_playback_reviewed"] = False
    (folder / "video-info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(f"ENCODED_REVIEW_VIDEO {destination} ({count} frames, 24 fps; playback not reviewed)")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "folder", type=Path, help="Folder containing the selected profile’s complete PNG sequence"
    )
    parser.add_argument("--profile", choices=PROFILES, default="combat")
    args = parser.parse_args()
    encode(args.folder, args.profile)
