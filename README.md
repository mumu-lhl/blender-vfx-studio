# Blender VFX Studio

面向二次元 3D 动画的 Blender 原生 VFX 插件。目标 Blender **5.2 LTS**，优先 Eevee，兼容 Cycles。

当前预览版 **0.5.0** 已实现：

- **Particle Burst**：确定性原生粒子生成、随机方向/速度/尺寸、重力轨迹和网格实例化。
- **Screen VFX**：主动启用的原生合成辉光、时间闪光，可叠加、复制和安全移除。
- **Flipbook Atlas**：用户静态图集、行列与起止格、透明贴片和发光，原生 UV 选帧。
- **Shockwave / Energy Ring**：可编辑的程序化网格、UV 流动、噪声溶解、软边透明与发光。
- 开始帧、持续时间、速度、循环；半径、宽度、扩张、颜色及着色器参数可关键帧化。
- 原生 VFX 侧栏创建、独立复制、安全删除；32 / 64 / 128 段质量选项。
- 不使用 Python 每帧处理器；保存后无需插件也能播放。
- 用户参数预设 JSON 保存与加载，严格版本和数值校验；载入为独立实例。

这只是首个纵向切片。Trail、Simulation 和可浏览的预设库尚未实现；详见 [ROADMAP.md](ROADMAP.md)。

## 安装

从 [Releases](https://github.com/mumu-lhl/blender-vfx-studio/releases) 下载 `blender-vfx-studio-0.5.0.zip`。
未打 tag 的开发版本可从 [Actions](https://github.com/mumu-lhl/blender-vfx-studio/actions/workflows/ci.yml) 最新成功构建中下载 `blender-vfx-studio-extension` artifact，解压后安装其中的 ZIP。
Blender 5.2 → Edit → Preferences → Get Extensions → 右上角菜单 → Install from Disk，选择 ZIP 并启用。
源码也可直接构建：

```sh
python tools/build.py
```

安装 `dist/` 中生成的 ZIP；不要安装 GitHub 的源码 ZIP。

## 使用

1. 在 3D 视图按 **N**，打开 **VFX** 标签页，点击 **Create VFX**。
2. 选择 Shockwave 或 Energy Ring，以及质量级别。特效在 3D Cursor 处创建，以当前帧为开始帧。
3. 切换 **Material Preview** 或 **Rendered** 查看材质。Eevee 用户需要自有环境/灯光以查看场景；发光环本身不需要灯光。
4. 在 VFX 面板调整时间、网格和 Shader 参数。右键参数 → Insert Keyframe，可使用 Blender 原生动画编辑器。
5. 移动/旋转/缩放 Controller 控制整个效果。选择 Controller 或 Layer 均可编辑参数。
6. 使用 **Duplicate** 创建独立效果；使用 **Delete** 删除。支持 Blender Undo。

Energy Ring 默认一个 48 帧周期；启用 Loop 可持续显示。循环会重置到出生状态，Shockwave 不保证边界连续。
Emission 不自动添加屏幕辉光；如需辉光，请在自己的 Compositor 中配置 Glare。

选择 Layer 可直接编辑 Geometry Nodes、材质节点和基础网格。参数调整不会重建这些节点。
请保留命名属性 `vfx_inner` 和节点输入驱动目标。质量只在创建时生效。

## Flipbook 图集动画

点击 **Create Flipbook** 选择静态图集图片，在文件选择器中设定 Columns / Rows。
图集按**左上开始、向右后向下**编号，First Frame / Last Frame 为从 0 开始的闭区间。
统一生命周期内均匀播放所选格；持续时间、速度和循环与环形效果一致。
起止格限制在当前网格内；Last 小于 First 时保持 First 格，不倒放。

Width / Height 控制贴片尺寸，Opacity / Fade 控制透明度，RGB 与 Strength 控制染色和发光。
平面位于控制器局部 XY，手动旋转使其面向镜头；本版不提供自动朝向相机或独立 FPS 模式。
图片 alpha 与 Opacity 相乘；采用最近邻采样，图片色彩空间和 alpha 模式保持用户设置。
极接近切格边界时使用百万分之一周期容差，消除渲染求值浮点误差造成的上一格闪烁。

复制共享原图片、独立复制网格和材质；删除效果保留图片。图片可在侧栏数据块选择框或材质节点中替换。
`.blend` 默认保留外部图片引用；跨机器分享前使用 Blender 的 **File → External Data → Pack Resources**。
JSON 预设引用图片文件，不内嵌图片；把图片与 JSON 一同移动可保持相对路径。
未保存到磁盘的生成图片可保存到 `.blend`，导出参数预设前需先保存图片文件。

## Particle Burst 粒子爆发

点击 **Create Particle Burst**。默认 64 个低面数球形粒子，每实例只有控制器和一个网格对象；不逐帧创建对象。
Count 上限为 2048，默认 Low 质量；Medium / High 增加单粒子网格细分，仅在创建时选择。
Seed 决定随机方向及速度/尺寸变化；相同参数与帧得到相同结果，跳帧不需要预热或缓存。

Velocity / Gravity 使用控制器局部空间的单位/秒和单位/秒²。
**Motion Seconds** 是完整轨迹的物理时长；**Duration** 是播放这段轨迹的帧数。
例如 Motion Seconds=1、Duration=24，即在 24 帧内播放 1 秒运动；修改 Duration 或 Speed 可拉伸播放，轨迹形状保持。
Spread=0 指向局部 +Z，Spread=1 向各方向散射。Randomness 控制速度及尺寸变化，Spawn Radius 控制初始径向位置。
Size 为出生半径，Fade 控制生命周期内的尺寸缩减；结束后隐藏，循环时重置整组爆发。
RGB / Strength 控制发光材质，可结合 Screen Glare 使用。

本版是同时出生的无状态爆发；不包含连续发射、碰撞、逐粒子出生时间或缓存模拟。
关键帧修改运动参数会重新计算当前轨迹，不积累历史受力。
Geometry Nodes 保留可编辑；应用修改器后可得到当前帧的普通网格。

## Screen VFX 合成

点击 **Add Screen VFX**，为当前场景添加原生 Fog Glow 与闪光合成层；创建 3D 特效不会自动改写合成链。
没有合成树时创建 Render Layers → VFX → Image 输出；已有合成树时插入到其活动 Image 输出前。
必须有唯一活动的彩色 Image 输出和已连接的上游；共享或链接的合成树需先在 Blender 中 Make Single User。

Strength / Threshold / Glow Size 控制辉光。Flash 默认 0；调高可显示从出生帧开始、按 Fade 衰减的全屏颜色覆盖。
默认 Loop 开启；关闭后仅在生命周期内生效，结束后透传原图。
RGB 控制闪光颜色，控制器在 3D 场景中的位置/旋转不影响屏幕效果。
支持原生关键帧、JSON 参数预设与 Duplicate；多个 Screen VFX 按插入顺序串联。

Delete 会移除自身合成节点，并把当前上游重新连接到下游。保留用户节点、改线及分支；
若额外自定义输出仍有连线、输入断开或节点组被共享，则先报错，修复后可重试。
插件创建的空合成基础树在未被用户修改时一并恢复为空；编辑过的基础树会保留。
合成设备沿用场景设置；无独显设备可在原生渲染设置中把 **Compositor Device** 设为 **CPU**。
测试和发布预览显式使用 CPU 合成。

## 保存与复用预设

选择效果后点击 **Save Preset**，保存 `.json`；点击 **Load Preset** 可在当前 3D Cursor 和当前帧创建独立实例。
保存当前帧的参数值、质量和名称，不包含原始开始帧、UUID、关键帧、变换、图片内容或手动编辑的节点拓扑；Flipbook 另保存图片文件路径。
节点拓扑与动画的完整复用请保存 `.blend` 并使用 Blender 原生 Append。

格式有独立的 format/module/asset 版本，严格校验缺失字段、未知字段、非有限数值和参数范围，文件最大 64 KiB。
当前导出预设格式 2，支持 ring / atlas / screen / burst 资产版本 1；可迁移 v0.2 的格式 1 环形预设。未知版本会明确报错，不会修改场景。

## 安全与限制

- 使用 VFX **Duplicate**；Shift-D 会复制实例 UUID，插件会提示身份歧义。
- 若外部对象共享了生成的 Mesh、Material 或 Node Group，Delete 会拒绝操作，先解除共享。
- 删除保留用户子对象、外来材质和非空集合；自建约束/驱动器若引用 Controller，需自行处理这些外部依赖。
- 保存的 `.blend` 可在未安装插件、禁用自动执行时播放；重新创作需要启用插件。
- 本版实例 schema 保持 1；预设格式 1 → 2 迁移已有历史固定样例测试。未知版本会拒绝导入。
- 自动化已验证 Blender 5.2.2 Linux。其他操作系统和完整交互 UI 操作仍需人工验证。

## 开发与验证

需要 Python 3.11+ 和 Blender 5.2.2（可通过 `BLENDER_BIN` 指定路径）；无第三方运行依赖。

```sh
python tools/test.py
python tools/test_install.py
blender -b --factory-startup --python-exit-code 1 --python tools/preview.py
blender -b --factory-startup --python-exit-code 1 --python tools/preview.py -- --engine BLENDER_EEVEE --scale 25
```

测试在 CPU 后台验证真实 bpy、实例隔离、参数/时间、复制动画、删除安全、保存重开与插件安装生命周期。
预览场景及 PNG 写入忽略的 `work/`。CI 构建的 ZIP 在 Actions artifacts 中提供。
使用 Ruff 进行静态检查和格式校验；安装版本见 CI 配置。

架构见 [DESIGN.md](DESIGN.md)，领域约定见 [CONTEXT.md](CONTEXT.md)。
许可证：**GPL-3.0-or-later**。
