# 原生效果入门库

这是独立的示例资产包，不是插件安装包。从 Releases 下载与插件同版本的 examples ZIP，解压到普通文件夹，在 Preferences → File Paths → Asset Libraries 添加这个文件夹，再在 Asset Browser 中选择它。

先启用插件，选中资产后点击右侧 Blender VFX Studio 面板的 **Load VFX with New ID**。这个操作会分配新的实例编号；普通拖放不会分配，重复载入可能发生编号冲突。也可以在 VFX 侧栏用 **Load Complete Effect** 直接选择某个 `.blend`。

所有示例从第 1 帧开始，默认不循环。载入保留原时间和变换，不会自动放到当前帧或 3D Cursor。选择组合控制器可调整整体 Start、Duration、Speed 和 Loop；在组合面板选择某一层，则可修改该层的颜色、尺寸和时间。

**Energy Charge（48 帧）** 在 0.22.2 中由倾斜旋转的轨道环、低亮地面环、带深色主体与青色边缘的球壳，以及向中心汇聚的连续粒子组成，共 4 层。Spawn Radius 决定微粒出生位置，正的 Velocity 越大，抵达中心越快；抵达后停止，不会穿过中心再向外散出。粒子在控制器局部空间运动，移动整体也会移动已出生粒子，不保留角色走过的世界轨迹。

0.22.2 的环和球壳在末段逐渐变暗。它们的私有材质采用 Blended 透明，减少低采样 Eevee 中的颗粒；旧文件不会在载入时换材质或覆盖参数。出现、中段和退场的实际检查范围见 [充能记录](CHARGE_VISUAL_REVIEW.md)。

**Impact Burst（24 帧）** 包含白色短闪、12 个橙色定向尖片、较暗的侵蚀冲击波和 18 个稍晚出现的余烬，共 4 层。短闪先消失，冲击波随后断开，尖片逐渐缩短。修改环的 Expansion 控制扩散距离，修改粒子的 Stretch、Planar、Motion Ease 调整尖片长宽、散射平面和减速。组合 Duration 调整整体播放时长，Ungroup All 可拆开全部层。

**Arc Slash（18 帧）** 是单层紫色程序化刀光，不需要角色动画或采样路径。Arc 调整弧度，Width 调整宽度，Spin 调整旋转；Attack、Motion Ease、Core Width、Afterimage、Streaks 和 Breakup 调整展开、减速、锋刃、残影、笔触与侵蚀。0.22.2 包含版本 2 的规则月牙；当前未发布候选改用版本 3 的钩形与亮暗分面，并加入 Contour、Bank、Wake Spread 控制轮廓、深度与残影分离。它与侧栏直接创建的刀光使用同一生成器，只把时长设为 18 帧；旧文件不自动升级。

全部示例采用 Low 质量，保留原生对象、网格、材质和 Geometry Nodes。使用 VFX Duplicate 创建独立副本，使用 VFX Delete 删除。示例不需要外部贴图、角色或缓存；不加载插件也能播放和渲染，继续使用侧栏创作则需要启用插件。

保存手动节点、轨道驱动或整个组合时，使用 **Save Complete Effect**。单层参数预设只保存参数。例如，只保存充能粒子层的参数 JSON，再创建时会得到普通 Emitter；向内运动和尖形等私有节点不会随参数重建。

缩略图为 256×256 的 Cycles CPU 渲染。0.22.2 的 Energy Charge 缩略图曾加入额外 Screen 辉光；当前候选取消了它。相机、背景、辉光合成和预览图片都不会进入效果资产，载入也不会改动场景合成链。若需要光晕，可主动添加 Screen VFX；不加辉光时，原生发光材质也能显示。缩略图不代表高清效果验收或集成显卡帧率。

Arc Slash 和 Impact Burst 的缩略图均展示第 5 帧，不加辉光；Impact 使用与侧栏直接创建相同的接口和默认参数。高清三阶段检查见 [刀光记录](VISUAL_REVIEW.md) 和 [打击爆发记录](IMPACT_VISUAL_REVIEW.md)。充能到挥斩、命中的静帧检查及其限制见 [衔接记录](CHARGE_HANDOFF_REVIEW.md)。

从全新源码克隆重新生成：

```sh
blender -b --factory-startup --python-exit-code 1 --python tools/build_examples.py
```

脚本只接受未打开项目的全新后台进程，输出 3 个 `.blend` 到 `dist/examples/`，并生成带版本号的 examples ZIP；不会删除目录中其他文件。网格、节点、参数和嵌入预览均可重建。每次会产生新的内部编号，因此不保证 Blender 文件跨次构建的二进制完全相同。

0.22.3 尚未发布，艺术重设计由 [#89](https://github.com/mumu-lhl/blender-vfx-studio/issues/89) 跟踪。Energy Charge 最新候选改用六条有空隙的内卷路径和小内核；能量团沿路径向内加速，后段三轴收紧，白色集中于汇聚前端与内核。外侧保留盘卷移动段、地面收束形状和弯曲粒子，共四层。形体与阶段曲线可在原生节点中编辑，侧栏保留适用的尺寸、颜色、时间等参数。候选仍在视觉复核，预算及观看范围见 [压缩记录](CHARGE_COMPRESSION_REVIEW.md)，早期迭代见 [充能记录](CHARGE_VISUAL_REVIEW.md)。新缩略图取消额外辉光；已下载的 0.22.2 保留旧造型。
