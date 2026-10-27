"""Create a human-readable page beside the native scenes and actual decoded movie frames."""

import argparse
import hashlib
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.combat_frames import extract  # noqa: E402
from tools.combat_video import encode  # noqa: E402
from tools.handoff_bundle import check_sources  # noqa: E402


def build(base):
    base = Path(base)
    primary = base / "light-near"
    record = json.loads((primary / "character-settings.json").read_text())
    check_sources(record)
    if not record["contact"]["verified_intersection"]:
        raise ValueError("The saved sequence must contain actual blade/character contact")
    native = json.loads((primary / "native-check.json").read_text())
    if (
        native.get("native_render_verified") is not True
        or native.get("frames") != [53, 16, 32]
        or native.get("clear_frame") != 96
        or native.get("scene_sha256")
        != hashlib.sha256((primary / "character.blend").read_bytes()).hexdigest()
    ):
        raise ValueError("Repeat the native check on the current saved scene")
    for name, expected in native["source_frame_sha256"].items():
        if hashlib.sha256((primary / name).read_bytes()).hexdigest() != expected:
            raise ValueError("The native comparison images changed")
    encode(primary, "character")
    decoded = extract(primary, "character")
    samples = json.loads((decoded / "frames.json").read_text())["samples"]
    figures = "".join(
        f'<figure><a href="light-near/video-frames/{item["file"]}"><img loading="lazy" width="320" src="light-near/video-frames/{item["file"]}"></a><figcaption>第 {item["source_frame"]} 帧 · {item["seconds"]:.3f} 秒</figcaption></figure>'
        for item in samples
    )
    variants = []
    for path in sorted(base.glob("*/character-settings.json")):
        settings = json.loads(path.read_text())
        check_sources(settings)
        if settings["source_sha256"] != record["source_sha256"]:
            raise ValueError("Review variants must use the same scene and generator source")
        name = html.escape(path.parent.name)
        frames = settings["frames"] if path.parent != primary else [16, 32, 48, 49, 53, 61, 80]
        variants.append(
            f'<h2>{name}</h2><p><a href="{name}/character.blend">原生场景</a> · <a href="{name}/character-settings.json">生成与耗时记录</a></p><section>'
            + "".join(
                f'<figure><a href="{name}/character-{frame:04d}.png"><img loading="lazy" width="320" src="{name}/character-{frame:04d}.png"></a><figcaption>第 {frame} 帧</figcaption></figure>'
                for frame in frames
            )
            + "</section>"
        )
    page = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>角色战斗 VFX 检查</title>
<style>body{{max-width:1100px;margin:2rem auto;padding:1rem;font:16px system-ui;background:#20232a;color:#eee}}a{{color:#91caff}}video{{max-width:100%}}section{{display:flex;flex-wrap:wrap}}figure{{margin:.5rem}}img{{max-width:100%}}</style>
<h1>充能 → 挥剑 → 命中 → 消散</h1><p>96 帧，24 fps，960×540，软件 Eevee，AgX，无辉光。两名 KayKit CC0 低多边形蒙皮角色使用原生 NLA 动画；这不能代替正式二次元角色的最终验收。充能跟随剑身，刀光对齐挥剑，命中在实际剑刃接触帧 {record["contact"]["frame"]} 开始。</p>
<p>本页面不自动批准视觉质量。编码、解码和无插件重开成功不代表已实时观看；下方为视频每隔一帧的解码图。骨架、材质、节点和关键帧均可编辑，播放不需要插件或自动执行脚本。</p>
<video controls width="960" height="540" src="light-near/character.mp4"></video>
<p><a href="light-near/performance.json">同场景有／无特效的实测耗时</a> · <a href="light-near/native-check.json">无插件比较记录</a> · <a href="light-near/video-info.json">编码记录</a> · <a href="https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0">角色来源与 CC0 许可</a></p>
<p>耗时是当前设备的后台求值与渲染墙钟时间，不能当作交互视口帧率或独立显卡性能。</p>
{"".join(variants)}<h2>完整视频隔帧图</h2><section>{figures}</section></html>"""
    destination = base / "index.html"
    destination.write_text(page, encoding="utf-8")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    build(parser.parse_args().folder)
