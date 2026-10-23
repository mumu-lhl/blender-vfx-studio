"""Extract every other decoded MP4 frame for an explicitly recorded visual review."""

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def extract(folder):
    folder = Path(folder)
    movie = folder / "combat.mp4"
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
        "36",
    ):
        raise ValueError("Expected a 36-frame 960x540 review movie at 24 fps")
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
                "18",
                "-start_number",
                "1",
                str(Path(temporary) / "frame-%02d.png"),
            ],
            check=True,
        )
        samples = []
        for index, frame in enumerate(range(1, 37, 2), 1):
            filename = f"frame-{index:02d}.png"
            (Path(temporary) / filename).replace(output / filename)
            samples.append({"file": filename, "source_frame": frame, "seconds": (frame - 1) / 24})
    record = {"movie_sha256": source_digest, "step": 2, "samples": samples}
    (output / "frames.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"DECODED_VIDEO_SAMPLES {output} (18 frames; visual review not automatic)")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    extract(parser.parse_args().folder)
