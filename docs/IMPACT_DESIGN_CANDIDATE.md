# Impact Burst 造型候选

这是 [#93](https://github.com/mumu-lhl/blender-vfx-studio/issues/93) 的原生喷流改造与检查记录。0.22.3 尚未发布，整体艺术目标 #89 仍未完成。已发布的 0.22.2 保留原有星芒和尖片。此前的历史检查见 [原视觉记录](IMPACT_VISUAL_REVIEW.md)，不能直接当作本候选的结论。

## 为什么重做

实际读取旧生成器的第 2、5、14 帧后，开场仍是五个平面尖片叠出的星芒，峰值是规则圆环和相近的放射尖片。随机方向与白尖渐变增加了细节，却没有形成有体积、方向和主次的爆发主体。

此前的曲面候选有较丰富的断口，但仍像撕开的纸片。根因是整圈网格只有一层表面，噪声裁切后保留下来的宽片仍没有厚度；共同的展开轨迹又形成花瓣感。仅增加轮廓细分和材质渐变没有解决这个问题。

现在主体改为七条带闭合横截面的弯曲喷流，配两条更细的辅助带。主喷流更长、更宽，其他方向留出空隙；不同高度和弯曲避免所有部分挤在同一平面。短闪收窄，白色只保留在更紧凑的根部，主体以暖橙色为主，侵蚀边缘短暂变黄后冷却。它不再靠大面积白色与统一亮度遮住目标。

几何节点根据当前进度计算各喷流错开的弯曲、沿长度移动的收缩和向外分离。中段形状会改变，而不是把同一个星形同比放大。压力弧仍先向外展开，主体随后消失，延迟余烬最后退场。一次测试发现新侵蚀边缘在第 10 帧仍过亮，已加快主体侵蚀并让边缘先冷却，没有放宽尾段清理的断言。

这些修改发生在实际创建接口调用的 `impact.py` / `impact_shape.py`，预览只提供相机和背景。默认显示对象和材质仍各为 4 个，Low 最多约 888 顶点，预算上限 900；旧资产约为 414 顶点。短闪和主体强度仍为 1.2 / 1.6，没有增加粒子槽位、纹理资源或辉光。几何预算不能代表视口帧率，实际低配置设备尚未测量。

## 编辑与保存

组合的 Start / Duration / Speed / Loop 仍统一控制四层。短闪可调整 Size、Fade、Strength；主体沿用 Size、Stretch、Velocity、Motion Seconds、Motion Ease、Planar、Seed、Randomness、Spawn Radius、Fade 和 Strength。Size 改变主体横向形状，Stretch 和运动参数改变展开范围，Planar=1 压平到 XY。Shader Editor 的 Side Contrast 控制主体明暗面，Illustrated Light 指定绘制风格的明暗方向，不跟随场景灯光。Flow Detail Contrast 调整流纹对比，Outer Tongue Taper 调整末端透明范围，Burning Edge Width 调整侵蚀边缘的色带宽度。几何节点 Curl Range 与 Pulse Depth 调整弯曲和收缩幅度；压力弧的 Pressure Ease 调整前段展开速度。

这两个成员沿用 Burst 控制器保存参数，但形状由私有节点生成。Count、Shape、Gravity、Spread 不驱动这些造型，侧栏已隐藏它们；普通 Particle Burst 仍保持原来的全部参数与行为。颜色、时间、网格、节点和动画保存在 Blender 原生数据中，无逐帧 Python、外部纹理或缓存。

请用 **Save Complete Effect** 保存这套编排。只导出单层参数 JSON 后重新创建，会得到普通 Burst，无法还原这些私有形状。旧完整资产载入时不会重建节点，也不会换成新造型。已经用实际 0.22.2 examples ZIP 验证旧 Impact 的载入、复制、删除原件与无插件重开，414 顶点及旧面色设置保持不变。

## 实际检查与尚未完成的部分

本轮造型对应 `5c58955`，`2584c85` 另将正、侧面预览加入 CI。实际读取了以下 960×540 图像：

- Cycles 默认镜头的第 2、5、14 帧，以及正面、侧面的峰值。
- Eevee 暗背景的第 2、5、7、9、11、14 帧；浅灰背景视频中对应第 1、3、5……25 帧的 13 张解码图，另读第 6、8、10 帧原始 PNG。
- Eevee / AgX 近白远景的第 2、5、14 帧。
- Eevee 浅灰背景的战斗衔接第 31、32、33、37、45、60 帧。场景使用简化武器与靶标。

与前轮宽片相比，喷流的空隙与更早的分离让靶标在命中时露出更多；第 7 帧中心已打开，第 9 帧主要剩零散碎片和余烬，25 帧清空。正、侧面保留了喷流的厚度。这些实图支持本轮造型改进，但主喷流仍有粗硬感，近白远景的边界与细余烬很弱；后续由 [#96](https://github.com/mumu-lhl/blender-vfx-studio/issues/96) 处理对比度，不将其写成已解决。

8 项 Blender 测试通过，覆盖形状参数、平面化、预算、重定时、独立副本、完整资产、Ungroup All、安全删除、材质编辑、中段像素与尾段清理。关闭自动执行、未加载插件的新进程验证了几何与五阶段像素；Cycles 暗背景和 Eevee 浅灰背景三阶段高清重渲染逐通道一致，25 帧所有层无残留。衔接场景的 31/33 帧原生重开一致，60 帧清空。实际 0.22.2 examples ZIP 的旧 Impact 也重新检查了载入、复制、删除原件与原生重开，414 顶点及旧面色设置保留。

本地视频为 960×540、25 帧、24 fps，约 1.042 秒。SHA256 为 `d8f132cbb505c5968c4bd13e758899318722c9338e9d95184d1453d2d82a147a`；源设置与 25 张 PNG 的组合 SHA256 为 `f037501108feb79bfa570ab1849256ff60345059927ce9bce7f37d852579a0c0`。它们标识本地已抽帧的序列，不代表已下载检查 CI 附件。没有实时观看视频，也没有验收真实角色、实际低配置视口或整体商业级品质。

前轮曲面候选的结论。实时视频、真实角色与实际低配置视口仍未验收。

前轮曲面候选的具体帧号、视频哈希和杯状残留修复记录保存在 [2d1f8a9 的检查文档](https://github.com/mumu-lhl/blender-vfx-studio/blob/2d1f8a97092d1262ac9a7562e48b8fddeee621db/docs/IMPACT_DESIGN_CANDIDATE.md)。它们不是当前喷流候选的验收记录。

在仓库根目录使用新的后台进程重建，软件 Eevee 可设置 `LIBGL_ALWAYS_SOFTWARE=1 EGL_PLATFORM=surfaceless`：

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py -- --engine BLENDER_EEVEE --light --sampled
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py -- --engine BLENDER_EEVEE --light --sequence
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py -- --engine BLENDER_EEVEE --pale --far --view-transform AgX
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py -- --view side
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py -- --baseline-asset /path/to/old-impact.blend
```

`--baseline-asset` 载入真实旧资产；`--legacy` 只重建更早的圆环与圆粒组合，不能代替 0.22.2 对照。结果在 `work/visual-impact/`，包括 PNG、原生场景和 `*-settings.json`。按记录中的图片列表检查本次结果，避免混入旧图；记录绑定生成器哈希、实际帧、相机、背景、色彩管理和旧资产哈希。

`--sequence` 输出 1–25 帧，场景固定为 24 fps，并停在第 5 帧保存，避免打开原生场景时只看到空的末帧。Linux CI 将完整浅背景序列编码为 MP4，核对 960×540、25 帧及 24 fps，并记录视频与源 PNG 的哈希。生成视频不代表已实时观看。

`--view front/side/high` 提供固定的正面、侧面和俯视相机；默认镜头不变，记录包含实际视角和相机位置。可与引擎、浅色背景、远景和帧选择组合使用。
