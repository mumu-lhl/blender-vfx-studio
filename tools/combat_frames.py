"""Extract every other decoded MP4 frame for an explicitly recorded visual review."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.combat_video import PROFILES  # noqa: E402


def extract(folder, profile="combat"):
    folder = Path(folder)
    _, _, prefix, count = PROFILES[profile]
    movie = folder / f"{prefix}.mp4"
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("Install FFmpeg (including ffprobe) before extracting frames")
    info = json.loads(
        subprocess.check_output(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,r_frame_rate,nb_frames",
                "-of",
                "json",
                str(movie),
            ],
            text=True,
        )
    )["streams"][0]
    if (info["width"], info["height"], info["r_frame_rate"], info["nb_frames"]) != (
        960,
        540,
        "24/1",
        str(count),
    ):
        raise ValueError(f"Expected a {count}-frame 960x540 review movie at 24 fps")
    source_digest = hashlib.sha256(movie.read_bytes()).hexdigest()
    output = folder / "video-frames"
    output.mkdir(exist_ok=True)
    (output / "frames.json").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        subprocess.run(
            [
                ffmpeg,
                "-v",
                "error",
                "-i",
                str(movie),
                "-vf",
                r"select=not(mod(n\,2))",
                "-fps_mode",
                "vfr",
                "-frames:v",
                str((count + 1) // 2),
                "-start_number",
                "1",
                str(Path(temporary) / "frame-%02d.png"),
            ],
            check=True,
        )
        samples = []
        if hashlib.sha256(movie.read_bytes()).hexdigest() != source_digest:
            raise ValueError("Review movie changed during decoding")
        for index, frame in enumerate(range(1, count + 1, 2), 1):
            filename = f"frame-{index:02d}.png"
            (Path(temporary) / filename).replace(output / filename)
            samples.append({"file": filename, "source_frame": frame, "seconds": (frame - 1) / 24})
    record = {"movie_sha256": source_digest, "step": 2, "samples": samples}
    (output / "frames.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"DECODED_VIDEO_SAMPLES {output} ({len(samples)} frames; visual review not automatic)")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--profile", choices=PROFILES, default="combat")
    args = parser.parse_args()
    extract(args.folder, args.profile)
