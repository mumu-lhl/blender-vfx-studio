# Impact Burst 造型候选

这是 [#93](https://github.com/mumu-lhl/blender-vfx-studio/issues/93) 的开发草稿，尚未合并或发布，也没有完成艺术验收。已发布的 0.22.2 保留原有星芒和尖片。此前的历史检查见 [原视觉记录](IMPACT_VISUAL_REVIEW.md)，不能直接当作本候选的结论。

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

当前喷流候选已实际读取 Cycles 默认镜头的三阶段及 3、5、7、9 帧，以及正面、侧面的峰值图。宽曲面变成了分开的尖端与弯曲喷流，低角度也保留体积；但主喷流仍偏粗硬，尚不能据此宣布整体艺术验收完成。

8 项 Blender 测试及无插件重开已通过，覆盖形状参数、平面化、预算、重定时、独立副本、完整资产、Ungroup All、安全删除、材质编辑、中段像素与尾段清理。新的完整 Eevee 序列、近白远景和战斗衔接仍需重渲染、读图，不能沿用前轮曲面候选的结论。实时视频、真实角色与实际低配置视口仍未验收。

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
