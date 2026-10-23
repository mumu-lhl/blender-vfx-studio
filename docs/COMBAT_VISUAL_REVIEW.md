# 刀光接命中的镜头检查

**Issue #69 的连续播放观感仍未验收。** 当前工具可以读取 PNG，不能真正观看连续视频。完整序列、视频编码、逐帧检查和无插件回放检查均不能代替按实际速度观看；本记录只对实际做过的检查负责。

`tools/combat_preview.py` 创建 36 帧、24 fps 的简易武器/靶体场景，使用用户创建效果时相同的 Arc Slash 和 Impact Burst 接口。武器变换关键帧、材质和节点都保存在原生 .blend 中，不加辉光。靶体没有碰撞系统，命中时间明确设为第 7 帧；它用于检查空间衔接和遮挡，不代表真实角色动作。

## 本轮改变与实图发现

远景检查把相机可见宽度从 9.5 增加到 19，效果本身不放大。第一轮 Eevee 实图中，中心短闪偏细，扩散后圆环的权重相对偏高。实际 Impact 生成器已把短闪 Size 从 0.18 调到 0.24、Stretch 从 2.4 调到 2、持续时间从 7 帧缩为 6 帧；主尖片略增厚，但保留接近原来的长度。冲击波初始 Dissolve 从 0.35 调到 0.42，并保留末段完全侵蚀。各层强度、数量、节点结构和顶点预算保持原样。

同一中灰背景、同一相机的前后第 8 帧 PNG 已直接读取；新版白色中心更饱满。旧的“浅背景”实际接近中灰，因此本轮还使用更亮的蓝灰背景重新检查，不能把两种背景混为同一组前后对比。新浅背景使用线性 RGB (0.55, 0.60, 0.68)，配合 Standard 视图转换。

已通过图像工具读取 Eevee 远景亮背景第 4、6、7、8、9、11、12、13、14、23、31、36 帧，以及近景暗/亮背景和远景暗背景的对比帧。第 6 帧刀光仍能表达挥砍方向，第 7–9 帧命中中心和橙色尖片可辨；第 13 帧中心短闪已结束，冲击波退为次要轮廓。第 23 帧只有零散余烬，第 31、36 帧已清空。亮背景下刀光细残影偏淡，远景微小余烬接近亚像素，不能依靠它们传达命中信息。

这些帧能确认轮廓、主次和时序边界，不能确认挥砍的速度感、爆发是否足够有力或连续衔接是否自然。当前预览的主挥砍在第 3–7 帧到达命中点；这段节奏和残影的连续稳定性仍需真正播放检查。

## 可复现的对比条件

所有输出为 960×540；Cycles 使用 CPU、24 samples，软件 Eevee 使用 16 samples。无 GPU 的渲染耗时不代表集成显卡视口帧率。

| 条件 | 输出目录 | 内容 |
| --- | --- | --- |
| Cycles 近景暗背景 | `dark` | 36 帧、视频、原生场景 |
| Cycles 近景亮背景 | `light` | 四个关键帧、原生场景 |
| Eevee 近景暗背景 | `blender_eevee-near-dark` | 36 帧、视频、原生场景 |
| Eevee 近景亮背景 | `blender_eevee-near-light` | 四个关键帧、原生场景 |
| Eevee 远景暗背景 | `blender_eevee-wide-dark` | 四个关键帧、原生场景 |
| Eevee 远景亮背景 | `blender_eevee-wide-light` | 36 帧、视频、原生场景 |

只在新的后台进程运行；脚本会建立空场景：

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/combat_preview.py -- --sequence
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/combat_preview.py -- --engine BLENDER_EEVEE --sequence
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/combat_preview.py -- --engine BLENDER_EEVEE --wide --light --sequence
python tools/combat_video.py work/visual-combat/dark
python tools/combat_video.py work/visual-combat/blender_eevee-near-dark
python tools/combat_video.py work/visual-combat/blender_eevee-wide-light
python tools/combat_review.py work/visual-combat
```

安装 FFmpeg（含 ffprobe）后，combat_video.py 编码 MP4，检查完整 36 帧、24 fps 和 1.5 秒时长。缺少完成记录、只渲染了关键帧、缺帧或尺寸不符时拒绝编码，保留之前的视频。重新渲染开始时会清除旧的完成记录和播放页，避免中断后把新旧 PNG 混成“完整序列”。

最后一条命令生成离线播放页 `work/visual-combat/index.html`，直接用浏览器打开即可，无需服务器或联网。Actions 附件解压后也可打开同名文件；请保留旁边的条件目录。先按 1× 正常速度播放 Cycles 与 Eevee 的近景暗背景，两者相机与背景相同；再播放 Eevee 远景亮背景。其他三种条件仍只有关键帧，页面会明确标记，不能据此判断连续播放。

编码记录包含当前渲染设置和全部源 PNG 的 SHA256，即用于识别文件内容的摘要。播放页只嵌入与当前序列匹配的视频；重渲染后需重新编码并生成页面，旧的编码记录也需重新生成。这只能防止误看过期视频，不代表视觉通过。页面没有自动批准按钮，也不能证明浏览器的实际播放速度或掉帧情况。

观看后在 #69 记录播放工具、实际速度，以及挥砍速度感、命中力度、尖片/冲击波层次和衔接的观察。指出问题所在的条件与帧区间，再优先改真实生成器或普通参数并重渲染。慢放和暂停可辅助定位，但不能替代正常速度观看。

去掉 `--sequence` 只生成第 4、8、12、23 帧；去掉 `--wide` 使用近景，去掉 `--light` 使用暗背景。Linux 无 GPU 时可在 Blender 命令前加 `LIBGL_ALWAYS_SOFTWARE=1 EGL_PLATFORM=surfaceless`。结果位于 `work/visual-combat/`，`render-settings.json` 记录实际渲染条件；不要同时向同一目录运行两个渲染进程。

新生成的 `combat.blend` 打开时停在第 8 帧命中画面，可直接播放，无需插件；时间轴包含出现、命中和恢复标记。它含相机、灯光与参照物，是完整预览场景，不供 Load Complete Effect 载入。原生播放仍需检查能否达到 24 fps，后台软件渲染耗时不能当作视口帧率。

## 验证范围与待验收项

已有 152 项测试、15 个无插件重开进程、安装/卸载和 Ruff 通过，另增加两项编码预检。Eevee 远景亮背景与 Cycles 近景场景均在无插件新进程跳帧、重渲染第 8 帧，PNG 所有像素通道与原图一致。实际 v0.22.0 示例资产载入、复制及各粒子层参数 JSON 重建后仍保留旧参数；新版默认值只影响重新创建的 Impact。新版入门库也已重建并通过无插件验证。

CI 配置生成上述六种条件、三个视频、离线播放页和原生场景，并对三个完整序列的命中帧执行无插件像素对比，附件为 `combat-shot-visual-review`。自动检查结果见关联 PR。视频文件存在和元数据检查通过只证明交付物可供播放，不代表已经观看。

[Issue #69](https://github.com/mumu-lhl/blender-vfx-studio/issues/69) 保持打开：尚需按 24 fps 真正观看三段视频，判断挥砍速度感、命中力度、粒子/冲击波层次和衔接；真实角色、其他帧率及集成显卡性能也未验收。该项完成前不宣布连续战斗动画视觉通过。

后续 [#71](https://github.com/mumu-lhl/blender-vfx-studio/issues/71) 增厚主尖片横向轮廓并加入亮暗面。已读取修改后的 Eevee 亮背景近景、远景命中与扩散图，并对比旧图：近景面色更清楚，远景主尖片略易辨认，细余烬仍弱。Cycles 出现、峰值、衰减图已查看。155 项本地回归和两种引擎的无插件命中帧像素对比通过；详细参数、编辑方式和限制见 [Impact 检查记录](IMPACT_VISUAL_REVIEW.md)。#69 的连续播放部分仍未验收。
