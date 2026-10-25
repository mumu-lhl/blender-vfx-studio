"""Build an offline review ZIP from a complete native charge-to-hit render."""

import argparse
import hashlib
import html
import json
import os
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.combat_frames import extract  # noqa: E402
from tools.combat_video import encode, sequence_digest  # noqa: E402


def check_sources(record):
    if not record.get("source_sha256"):
        raise ValueError("Missing generator hashes; render with charge_handoff.py")
    for name, expected in record["source_sha256"].items():
        source = (ROOT / name).resolve()
        if (
            not source.is_relative_to(ROOT)
            or hashlib.sha256(source.read_bytes()).hexdigest() != expected
        ):
            raise ValueError(f"Generator changed since rendering: {name}")


def build(folder, destination=None):
    folder = Path(folder)
    record = json.loads((folder / "review-settings.json").read_text(encoding="utf-8"))
    if record.get("frames") != list(range(1, 61)) or record.get("saved_frame") != 31:
        raise ValueError("Render the complete 60-frame handoff, saved at frame 31")
    if not record.get("portable_render_path", "").startswith("//"):
        raise ValueError("The native scene needs a portable render output path")
    check_sources(record)
    if not (folder / "handoff.blend").is_file():
        raise FileNotFoundError(folder / "handoff.blend")
    native = json.loads((folder / "native-check.json").read_text(encoding="utf-8"))
    if (
        native.get("native_render_verified") is not True
        or native.get("frames") != [31, 33]
        or native.get("clear_frame") != 60
        or native.get("scene_sha256")
        != hashlib.sha256((folder / "handoff.blend").read_bytes()).hexdigest()
    ):
        raise ValueError("Run charge_handoff_reopen.py on the current native scene")
    if set(native.get("source_frame_sha256", {})) != {"handoff-0031.png", "handoff-0033.png"}:
        raise ValueError("Missing native comparison frames")
    for name, expected in native["source_frame_sha256"].items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Native comparison frames changed; repeat the reopen check")
    encode(folder, "handoff")
    extract(folder, "handoff")
    info = json.loads((folder / "video-info.json").read_text(encoding="utf-8"))
    samples = json.loads((folder / "video-frames/frames.json").read_text(encoding="utf-8"))
    version = tomllib.loads(
        (ROOT / "blender_vfx_studio/blender_manifest.toml").read_text(encoding="utf-8")
    )["version"]
    destination = (
        Path(destination)
        if destination
        else ROOT / "dist" / f"blender-vfx-studio-handoff-{version}.zip"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = [folder / f"handoff-{frame:04d}.png" for frame in range(1, 61)]
    files += [
        folder / name
        for name in (
            "handoff.blend",
            "handoff.mp4",
            "review-settings.json",
            "native-check.json",
            "video-info.json",
            "video-frames/frames.json",
        )
    ]
    files += [folder / "video-frames" / item["file"] for item in samples["samples"]]
    figures = "".join(
        f'<figure><a href="video-frames/{html.escape(item["file"])}"><img loading="lazy" src="video-frames/{html.escape(item["file"])}" width="240"></a><figcaption>第 {item["source_frame"]} 帧 · {item["seconds"]:.3f} 秒</figcaption></figure>'
        for item in samples["samples"]
    )
    page = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Charge → Slash → Impact</title>
<style>body{{max-width:1100px;margin:2rem auto;padding:1rem;font:16px system-ui;background:#20232a;color:#f4f4f4}}a{{color:#91caff}}video{{max-width:100%}}section{{display:flex;flex-wrap:wrap}}figure{{margin:.5rem}}img{{max-width:100%}}</style>
<h1>蓄力 → 挥斩 → 命中</h1><p>60 帧，24 fps，960×540。武器与靶标为简化物体，未验收真实角色。本页面不自动批准视觉质量；编码完成和抽帧不代表已实时观看。</p>
<video controls preload="metadata" width="960" height="540" src="handoff.mp4"></video>
<p><a href="handoff.blend">可编辑原生场景</a> · <a href="review-settings.json">相机、色彩与生成器记录</a> · <a href="video-info.json">编码记录</a></p>
<p>场景打开在命中帧 31。充能在 1–32 帧，挥斩在 27–38 帧，命中层在 31–54 帧；55 帧后清空。下列是视频隔帧解码图。</p><section>{figures}</section></html>"""
    guide = """这是可编辑的 Blender 原生检查场景，不是完整角色动画。解压后打开 index.html 播放视频，或直接打开 handoff.blend。播放不需要插件，脚本自动执行可以关闭。

场景停在第 31 帧，时间范围为 1–60，24 fps。几何、材质、控制器和动画均可编辑。渲染输出使用 //renders/handoff-，相对于本文件保存位置；打开文件不会自动导出图片。

将某一套效果带入已有工程时，可先在本场景选中其控制器并 Save Complete Effect，再用 Load VFX with New ID 载入。视频、PNG 和编码成功不等于完成艺术验收；请保留实际观看方式与未验证项。

源代码与重建命令见 https://github.com/mumu-lhl/blender-vfx-studio 。bundle-manifest.json 绑定本包文件，review-settings.json 记录实际生成器哈希。不要把本 ZIP 当作插件安装。
"""
    manifest = {
        path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, suffix=".zip", delete=False
        ) as stream:
            temporary = Path(stream.name)
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, "handoff-review/" + path.relative_to(folder).as_posix())
            archive.writestr("handoff-review/index.html", page)
            archive.writestr("handoff-review/README.md", guide)
            archive.writestr(
                "handoff-review/bundle-manifest.json", json.dumps(manifest, indent=2) + "\n"
            )
            archive.write(ROOT / "LICENSE", "handoff-review/LICENSE")
        check_sources(record)
        if any(
            hashlib.sha256(path.read_bytes()).hexdigest()
            != manifest[path.relative_to(folder).as_posix()]
            for path in files
        ):
            raise ValueError("Review inputs changed while building the package")
        if sequence_digest(folder, "handoff") != info["source_sha256"]:
            raise ValueError("Render changed while building the package")
        if (
            hashlib.sha256((folder / "handoff.mp4").read_bytes()).hexdigest()
            != samples["movie_sha256"]
        ):
            raise ValueError("Movie changed while building the package")
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"HANDOFF_REVIEW_BUNDLE {destination} (visual review not automatic)")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    build(args.folder, args.output)
