"""Build an offline playback page; encoding evidence never grants visual approval."""

import argparse
import json
from html import escape
from pathlib import Path

try:
    from .combat_video import sequence_digest
except ImportError:
    from combat_video import sequence_digest

CASES = {
    "dark": "Cycles · 近景 · 暗背景",
    "blender_eevee-near-dark": "Eevee · 近景 · 暗背景",
    "light": "Cycles · 近景 · 亮背景",
    "blender_eevee-near-light": "Eevee · 近景 · 亮背景",
    "blender_eevee-wide-dark": "Eevee · 远景 · 暗背景",
    "blender_eevee-wide-light": "Eevee · 远景 · 亮背景",
}


def current_video(folder, settings):
    """Exclude interrupted renders, keyframe sets and movies from older source PNGs."""
    if settings.get("rendered_frames") != list(range(1, 37)):
        return False
    try:
        info = json.loads((folder / "video-info.json").read_text(encoding="utf-8"))
        return (
            (folder / "combat.mp4").is_file()
            and settings.get("resolution") == [960, 540]
            and settings.get("fps") == 24
            and info.get("nb_frames") == "36"
            and info.get("r_frame_rate") == "24/1"
            and info.get("width") == 960
            and info.get("height") == 540
            and abs(float(info.get("duration", 0)) - 1.5) < 0.001
            and info.get("source_sha256") == sequence_digest(folder)
        )
    except (OSError, ValueError, TypeError):
        return False


def build(folder):
    folder = Path(folder)
    cards = []
    for name, label in CASES.items():
        case = folder / name
        settings_path = case / "render-settings.json"
        if not settings_path.is_file():
            continue
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        if current_video(case, settings):
            media = (
                f'<video controls loop muted playsinline preload="metadata" '
                f'poster="{name}/combat-0008.png" src="{name}/combat.mp4"></video>'
                "<p>完整视频：36 帧，24 fps，1.5 秒。请按正常速度播放。</p>"
            )
        else:
            media = (
                f'<img src="{name}/combat-0008.png" alt="第 8 帧静态图">'
                "<p>仅供静帧检查：缺少完整视频，或视频未绑定当前 PNG。"
                "请完成序列并重新运行 combat_video.py。</p>"
            )
        links = " · ".join(
            f'<a href="{name}/combat-{frame:04d}.png">第 {frame} 帧</a>'
            for frame in (4, 8, 12, 23)
            if (case / f"combat-{frame:04d}.png").is_file()
        )
        native = (
            f'<p><a href="{name}/combat.blend">下载原生 Blender 场景</a></p>'
            if (case / "combat.blend").is_file()
            else ""
        )
        cards.append(f"<section><h2>{escape(label)}</h2>{media}<p>{links}</p>{native}</section>")
    if not cards:
        raise ValueError("No completed render records found; run combat_preview.py first")
    page = (
        """<!doctype html>
<html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blender VFX Studio · 待验收的战斗预览</title>
<style>
body{font:16px/1.6 system-ui,sans-serif;margin:24px;color:#202734;background:#eef1f5}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,480px),1fr));gap:24px}
section{background:white;padding:16px;border-radius:8px}video,img{width:100%;height:auto}
h1{font-size:24px}h2{font-size:18px}a{color:#1856a1}
</style>
<h1>战斗预览：连续播放尚未验收</h1>
<p>本页面不自动批准视觉质量。点击视频播放，保持 1× 正常速度；先比较同镜头、同背景的
Cycles 与 Eevee，再检查远景与亮背景。记录实际播放工具、速度及观察结果。</p>
<p>重点观察：第 3–7 帧的挥砍是否可读，命中白闪是否短促，尖片与冲击波是否分层，
衰减是否给下一次动作留下空间。暂停和慢放可辅助定位问题，不能替代正常速度观看。</p>
<p>场景只有武器和靶体参照物，没有真实角色或碰撞系统。浏览器播放视频不代表 Blender 视口性能。</p>
<main>"""
        + "\n".join(cards)
        + "</main></html>\n"
    )
    destination = folder / "index.html"
    destination.write_text(page, encoding="utf-8")
    print(f"COMBAT_REVIEW_PAGE {destination} (playback not reviewed)")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, nargs="?", default=Path("work/visual-combat"))
    build(parser.parse_args().folder)
