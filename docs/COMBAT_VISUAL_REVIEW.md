# 刀光接命中的镜头检查

**#69 已按用户明确允许的隔帧抽样方案完成视觉检查。** 2026-10-23，用户允许“隔一帧看一帧，来代替实际观看视频的能力”。本轮从三个实际 MP4 解码原视频第 1、3、5……35 帧，每段 18 张，共 54 张 960×540 PNG，并通过图像工具逐张读取。没有实时观看视频，也不能据此判断实际播放掉帧、采样间隔内的单帧异常或完整主观速度感。

`tools/combat_preview.py` 创建 36 帧、24 fps 的简易武器/靶体场景，使用用户创建效果时相同的 Arc Slash 和 Impact Burst 接口。武器变换关键帧、材质和节点都保存在原生 .blend 中，不加辉光。靶体没有碰撞系统，命中时间明确设为第 7 帧；它用于检查空间衔接和遮挡，不代表真实角色动作。

## 本轮改变与实图发现

远景检查把相机可见宽度从 9.5 增加到 19，效果本身不放大。第一轮 Eevee 实图中，中心短闪偏细，扩散后圆环的权重相对偏高。实际 Impact 生成器已把短闪 Size 从 0.18 调到 0.24、Stretch 从 2.4 调到 2、持续时间从 7 帧缩为 6 帧；主尖片略增厚，但保留接近原来的长度。冲击波初始 Dissolve 从 0.35 调到 0.42，并保留末段完全侵蚀。各层强度、数量、节点结构和顶点预算保持原样。

同一中灰背景、同一相机的前后第 8 帧 PNG 已直接读取；新版白色中心更饱满。旧的“浅背景”实际接近中灰，因此本轮还使用更亮的蓝灰背景重新检查，不能把两种背景混为同一组前后对比。新浅背景使用线性 RGB (0.55, 0.60, 0.68)，配合 Standard 视图转换。

已通过图像工具读取 Eevee 远景亮背景第 4、6、7、8、9、11、12、13、14、23、31、36 帧，以及近景暗/亮背景和远景暗背景的对比帧。第 6 帧刀光仍能表达挥砍方向，第 7–9 帧命中中心和橙色尖片可辨；第 13 帧中心短闪已结束，冲击波退为次要轮廓。第 23 帧只有零散余烬，第 31、36 帧已清空。亮背景下刀光细残影偏淡，远景微小余烬接近亚像素，不能依靠它们传达命中信息。

以上是初轮静帧阶段的记录。随后按用户允许的隔帧方案检查了实际编码视频，结果见下节；没有把 PNG 检查写成实时播放。

## 隔帧抽样结果

抽样间隔为 2/24 秒，约 83 毫秒，覆盖从准备到退场的完整 1.5 秒片段。先检查 Cycles 近景暗背景与同镜头的 Eevee 近景暗背景，再检查 Eevee 远景亮背景。确切视频 SHA256 和已看过的帧号保存在 [抽样记录](COMBAT_SAMPLE_REVIEW.json)；SHA256 用于识别实际检查的是哪个文件，不授予视觉批准。

第 1、3 帧尚未出现刀光；第 5 帧刀弧成型，前端跟随武器；第 7 帧命中并出现紧凑白闪，第 9 帧主尖片快速外散。第 11 帧白闪已明显缩小，第 13 帧中心退场，靶体重新露出。第 13–19 帧尖片继续前行、缩短，冲击波先破碎再消失；第 21–29 帧只剩逐渐变小的零散余烬，第 31、33、35 帧没有重新冒出特效。

按这些间隔观察，前段展开快、后段位移变小，没有明显跳位或消失后重新出现；命中中心到外散尖片的空间衔接清楚。白色中心、橙色主尖片、较暗冲击波、细小余烬保持主次，退场后不会留下完整亮环遮住参照物。两种引擎的同条件抽样保持同样的轮廓和阶段安排。这些发现支持本镜头按抽样方案通过，不等于已经体验过实时播放的速度感或力度。

远景亮背景中，第 5–9 帧仍能辨认主刀弧与命中，第 13–19 帧仍有外散主尖片。细残影和微余烬很弱，尤其在 MP4 色度压缩后更易消失；它们不承担方向或命中信息，所以不阻塞这个简易镜头的抽样验收。此结论不推广到任意背景、角色或更远距离。

本轮没有发现需要继续调整真实生成器的阻塞问题，因此保留此前已验证的刀光、短闪、主尖片、冲击波参数和材质，不为凑改动而提高亮度。后续优先保留这一检查方法，再扩展高对比变体或真实角色镜头。

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
python tools/combat_frames.py work/visual-combat/dark
python tools/combat_frames.py work/visual-combat/blender_eevee-near-dark
python tools/combat_frames.py work/visual-combat/blender_eevee-wide-light
python tools/combat_review.py work/visual-combat
```

安装 FFmpeg（含 ffprobe）后，combat_video.py 编码 MP4，检查完整 36 帧、24 fps 和 1.5 秒时长。缺少完成记录、只渲染了关键帧、缺帧或尺寸不符时拒绝编码，保留之前的视频。重新渲染开始时会清除旧的完成记录和播放页，避免中断后把新旧 PNG 混成“完整序列”。

combat_frames.py 从实际 MP4 提取隔帧 PNG，video-frames/frames.json 记录原视频帧号、时间和视频 SHA256；它不读取原始渲染 PNG 冒充解码图。最后一条命令生成离线播放页 `work/visual-combat/index.html`，直接用浏览器打开即可，无需服务器或联网。Actions 附件解压后也可打开同名文件；请保留旁边的条件目录。先按 1× 正常速度播放 Cycles 与 Eevee 的近景暗背景，两者相机与背景相同；再播放 Eevee 远景亮背景。其他三种条件仍只有关键帧，页面会明确标记，不能据此判断连续播放。

编码记录包含当前渲染设置和全部源 PNG 的 SHA256，即用于识别文件内容的摘要。播放页只嵌入与当前序列匹配的视频；重渲染后需重新编码并生成页面，旧的编码记录也需重新生成。这只能防止误看过期视频，不代表视觉通过。页面没有自动批准按钮，也不能证明浏览器的实际播放速度或掉帧情况。

观看后在 #69 记录播放工具、实际速度，以及挥砍速度感、命中力度、尖片/冲击波层次和衔接的观察。指出问题所在的条件与帧区间，再优先改真实生成器或普通参数并重渲染。慢放和暂停可辅助定位。若采用用户授权的隔帧替代方案，必须记录抽样间隔、实际读取的帧和遗漏范围，不能写成已实时观看。

去掉 `--sequence` 只生成第 4、8、12、23 帧；去掉 `--wide` 使用近景，去掉 `--light` 使用暗背景。Linux 无 GPU 时可在 Blender 命令前加 `LIBGL_ALWAYS_SOFTWARE=1 EGL_PLATFORM=surfaceless`。结果位于 `work/visual-combat/`，`render-settings.json` 记录实际渲染条件；不要同时向同一目录运行两个渲染进程。

新生成的 `combat.blend` 打开时停在第 8 帧命中画面，可直接播放，无需插件；时间轴包含出现、命中和恢复标记。它含相机、灯光与参照物，是完整预览场景，不供 Load Complete Effect 载入。原生播放仍需检查能否达到 24 fps，后台软件渲染耗时不能当作视口帧率。

## 验证范围与待验收项

已有 152 项测试、15 个无插件重开进程、安装/卸载和 Ruff 通过，另增加两项编码预检。Eevee 远景亮背景与 Cycles 近景场景均在无插件新进程跳帧、重渲染第 8 帧，PNG 所有像素通道与原图一致。实际 v0.22.0 示例资产载入、复制及各粒子层参数 JSON 重建后仍保留旧参数；新版默认值只影响重新创建的 Impact。新版入门库也已重建并通过无插件验证。

CI 配置生成上述六种条件、三个视频、离线播放页和原生场景，并对三个完整序列的命中帧执行无插件像素对比，附件为 `combat-shot-visual-review`。自动检查结果见关联 PR。视频文件存在和元数据检查通过只证明交付物可供播放，不代表已经观看。

[Issue #69](https://github.com/mumu-lhl/blender-vfx-studio/issues/69) 按用户授权的隔帧替代方案验收，待本轮 PR 的完整检查通过后关闭。实时播放、真实角色、其他帧率及集成显卡性能不在本次已验证范围内。后续可以补充实时播放评审，但不再把缺少这一工具写成抽样验收无法完成。

后续 [#71](https://github.com/mumu-lhl/blender-vfx-studio/issues/71) 增厚主尖片横向轮廓并加入亮暗面。已读取修改后的 Eevee 亮背景近景、远景命中与扩散图，并对比旧图：近景面色更清楚，远景主尖片略易辨认，细余烬仍弱。Cycles 出现、峰值、衰减图已查看。155 项本地回归和两种引擎的无插件命中帧像素对比通过；详细参数、编辑方式和限制见 [Impact 检查记录](IMPACT_VISUAL_REVIEW.md)。#69 的实际 MP4 隔帧验收结果见上文；实时播放仍未检查。
