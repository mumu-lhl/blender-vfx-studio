# Impact Burst 造型候选

这是 [#93](https://github.com/mumu-lhl/blender-vfx-studio/issues/93) 的开发草稿，尚未合并或发布，也没有完成艺术验收。已发布的 0.22.2 保留原有星芒和尖片。此前的历史检查见 [原视觉记录](IMPACT_VISUAL_REVIEW.md)，不能直接当作本候选的结论。

## 为什么重做

实际读取旧生成器的第 2、5、14 帧后，开场仍是五个平面尖片叠出的星芒，峰值是规则圆环和相近的放射尖片。随机方向与白尖渐变增加了细节，却没有形成有体积、方向和主次的爆发主体。

第一轮把尖片换成宽曲面，实图变成了橙色花瓣；随后尝试定向壳体，又出现像金属碎片的表面。根因分别是曲面都连接在同一中心、沿相似弧线展开，以及把连续法线明暗和白尖渐变直接用于大面积主体。这两种外观都没有作为完成结果保留。

当前候选使用紧凑的短闪、一个有深度的破裂主体、较暗的压力弧和延迟余烬。主体以局部 XY 为主要展开平面，Z 保存弯曲深度；各方向尖端的长度与宽度不同，其中一支更大。白核、亮橙主体和红色外缘分开。白色先退出，主体裂成短段，最后保留少量暖色碎片与余烬。压力弧同时改变轮廓和覆盖范围，避免完整圆环持续描边。

峰值的整块色面曾显得扁平，现将主体拱起，用平滑法线形成弯曲的明暗分界，并让材质沿展开方向形成细纹和断口。主尖端保留较完整的形状，辅助方向更早拆散。退场还会把碎片从中心向外移，而不只缩小或变暗。

所有修改发生在实际创建接口调用的 `impact.py` / `impact_shape.py`，预览只提供相机与背景。默认显示对象和材质仍各为 4 个，Low 最多约 807 顶点，上限预算为 900；旧资产约为 414 顶点。短闪强度由 2.4 降至 1.2，主体由 2.0 降至 1.6，没有增加粒子槽位或额外辉光。几何预算不能代表视口帧率，实际低配置设备尚未测量。

## 编辑与保存

组合的 Start / Duration / Speed / Loop 仍统一控制四层。短闪可调整 Size、Fade、Strength；主体沿用 Size、Stretch、Velocity、Motion Seconds、Motion Ease、Planar、Seed、Randomness、Spawn Radius、Fade 和 Strength。Size 改变主体横向形状，Stretch 和运动参数改变展开范围，Planar=1 压平到 XY。Shader Editor 的 Side Contrast 控制主体明暗面，Illustrated Light 指定绘制风格的明暗方向，不跟随场景灯光。

这两个成员沿用 Burst 控制器保存参数，但形状由私有节点生成。Count、Shape、Gravity、Spread 不驱动这些造型，侧栏已隐藏它们；普通 Particle Burst 仍保持原来的全部参数与行为。颜色、时间、网格、节点和动画保存在 Blender 原生数据中，无逐帧 Python、外部纹理或缓存。

请用 **Save Complete Effect** 保存这套编排。只导出单层参数 JSON 后重新创建，会得到普通 Burst，无法还原这些私有形状。旧完整资产载入时不会重建节点，也不会换成新造型。已经用实际 0.22.2 examples ZIP 验证旧 Impact 的载入、复制、删除原件与无插件重开，414 顶点及旧面色设置保持不变。

## 实际检查与尚未完成的部分

本轮已多次读取三阶段 Cycles 960×540 PNG，确认宽曲面、壳体方向和材质各自造成的问题。修复杯状残留后，完整 Eevee 浅灰背景序列已生成并编码；视频为 960×540、25 帧、24 fps，时长约 1.042 秒。实际读取了视频中对应 Blender 第 1、3、5……25 帧的 13 张解码图，并另看原始 PNG 的第 6、8、10 帧，检查中段连续变化。这里属于抽帧检查，没有实时观看，也没有使用真实角色。

第 1–5 帧由紧凑白闪展开为主爆发，第 7–10 帧白色退出、主体裂开并向外移，第 11 帧后主要剩余烬，25 帧清空。抽查中不再出现杯状残留，但浅背景的细余烬很弱；峰值的连续色面和硬边仍需打磨，不能写成整体艺术验收完成。暗背景、AgX 近白远景和动作衔接的最新范围跟随 PR 更新。

当前峰值仍有连续色面偏大、扁平感偏强的问题；要继续判断主尖端、内部断口、退场碎片是否构成可信的命中爆发。不会仅凭测试通过将草稿转为艺术验收通过。

连续相邻帧暴露过一个关键帧检查漏掉的问题：第 11 帧出现棕色杯状残留。原本重合在中心的一圈顶点向外移动后形成了环，而材质一直保护这部分不被侵蚀。现在白核退场后解除保护，随后在几何节点中移除耗尽的内圈；基础网格仍保留，往回跳帧可以恢复。已实际查看修复后的 9、10、11、14 帧 Cycles PNG，杯状残留消失。

7 项 Blender 测试覆盖形状参数、平面化、预算、重定时、独立副本、完整资产、Ungroup All、安全删除、材质编辑与阶段变化，并检查主体在余烬阶段不能留下整片色面。原生重开比较几何与五个阶段的像素，包含中段退场。Cycles 暗背景及 Eevee 浅灰背景的出现、峰值、衰减三张高清 PNG 在新进程无插件重渲染，所有通道一致，25 帧全部效果层不再输出几何。

本地已检查视频的 SHA256 为 `42781dadb441542ce64c6229ebcee7251d86c5e17e3a563cf5adb58a1d20919b`，源记录与 25 张 PNG 的组合 SHA256 为 `d766b7977c64e4ea401626fcbbf8e20b6d6e092acc2b7016db71ce334b13d5ae`。这是本地编码的标识；CI 会重新生成自己的文件与哈希，不将本地读图写成已下载检查 CI 附件。

在仓库根目录使用新的后台进程重建，软件 Eevee 可设置 `LIBGL_ALWAYS_SOFTWARE=1 EGL_PLATFORM=surfaceless`：

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py -- --engine BLENDER_EEVEE --light --sampled
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py -- --engine BLENDER_EEVEE --light --sequence
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py -- --engine BLENDER_EEVEE --pale --far --view-transform AgX
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py -- --baseline-asset /path/to/old-impact.blend
```

`--baseline-asset` 载入真实旧资产；`--legacy` 只重建更早的圆环与圆粒组合，不能代替 0.22.2 对照。结果在 `work/visual-impact/`，包括 PNG、原生场景和 `*-settings.json`。按记录中的图片列表检查本次结果，避免混入旧图；记录绑定生成器哈希、实际帧、相机、背景、色彩管理和旧资产哈希。

`--sequence` 输出 1–25 帧，场景固定为 24 fps，并停在第 5 帧保存，避免打开原生场景时只看到空的末帧。Linux CI 将完整浅背景序列编码为 MP4，核对 960×540、25 帧及 24 fps，并记录视频与源 PNG 的哈希。生成视频不代表已实时观看。
