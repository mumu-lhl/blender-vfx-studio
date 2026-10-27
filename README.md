# Blender VFX Studio

面向二次元 3D 动画的 Blender 特效插件，目标版本为 **Blender 5.2 LTS**。插件创建 Blender 原生网格、材质、节点和动画；保存后的效果不需要插件持续运行，也能播放和渲染。优先支持 Eevee，同时兼容 Cycles。

目前可以创建冲击波、能量环、弧形刀光、Fresnel 能量护盾、图集与图片序列动画、粒子爆发与连续发射、轨迹刀带和屏幕辉光/闪光，还可以绑定到对象或骨骼、复制效果，以及管理参数预设。可以把多个空间效果组合起来统一调整，并用原生 Cloth 烘焙布面运动。当前仍是早期预览版，完整进度见 [ROADMAP.md](ROADMAP.md)。

## 安装和第一次使用

从 [Releases](https://github.com/mumu-lhl/blender-vfx-studio/releases) 下载最新版本的 `blender-vfx-studio-版本号.zip`。在 Blender 5.2 打开 **Edit → Preferences → Get Extensions → 右上角菜单 → Install from Disk**，选择 ZIP 并启用。不要安装 GitHub 的源码 ZIP。

1. 在 3D 视图按 **N**，打开 **VFX** 标签页，点击 **Create Mesh VFX**。
2. 选择 Shockwave（冲击波）、Energy Ring（能量环）、Arc Slash（弧形刀光）或 Impact Burst（打击爆发），以及质量。效果会出现在 3D Cursor 处，以当前帧开始播放。
3. 切换到 **Material Preview** 或 **Rendered** 查看材质，播放时间轴。
4. 调整面板中的时间、宽度、颜色等参数。右键参数选择 **Insert Keyframe**，即可制作参数动画。
5. 移动、旋转或缩放 Controller（Empty 控制器），控制整个空间效果。选中效果网格也能显示同一组参数。
6. 使用插件的 **Duplicate** 创建独立副本，使用 **Delete** 删除效果。这些场景操作支持 Blender Undo。

默认场景的 Cube 可能遮住平面特效。在 Outliner 选中 Cube 按 **H** 可临时隐藏它，或先把 3D Cursor 移到空处再创建。

Start 是开始帧，Duration 是播放帧数，Speed 是播放倍速，Loop 控制循环。例如 Start=1、Duration=24、Speed=1 时，第 1–24 帧可见，第 25 帧隐藏；Speed=2 时，第 13 帧开始隐藏。循环会回到出生状态，不保证画面首尾连续。
创建会对齐包含子帧的实际驱动时间；启用场景 Time Remapping 后，播放时间也跟随该映射。上面的整帧示例采用默认映射。

生成的效果保留原生可编辑性。选择效果网格后，可以编辑基础网格、Geometry Nodes（几何节点）和材质节点；调整面板参数不会重新生成节点。请保留驱动器引用的输入和所需属性。完整节点编辑和动画请保存在 `.blend` 中。

## 环形与弧形刀光

Shockwave 随时间向外扩张，Energy Ring 默认保持半径，播放一个 48 帧周期。启用 Loop 可重复播放。

Radius 是出生时外半径，Width 是环宽，Expansion 是一个周期增加的半径。内半径至少为 0.001，宽度过大时会接近实心圆。Dissolve 控制噪声溶解，Fade 控制生命周期内的淡出，Strength 控制表面发光强度。

质量只在创建时选择，分别使用 32、64、128 段。环形依赖网格的 `vfx_inner` 属性来区分内外边缘；删除该属性会破坏宽度计算。发光材质本身不需要灯光，但不会自动产生光晕。需要光晕时添加下文的 Screen VFX，或使用自己的 Glare 合成节点。

当前源码中的 Arc Slash 无需源动画，直接生成带有前端钩形、紫色亮暗分面和两条低亮残影的刀光。主体快速展开，残影逐渐分离；挥斩后拆成短笔触，再被侵蚀。已发布的 0.22.2 保留规则月牙造型。
这些层次由效果自己的几何、材质和时间参数生成，不依靠预览场景的辉光。Start / Duration / Speed / Loop 仍控制整个播放。

Arc 控制弧度（1–359 度），Spin 控制总旋转角度，正负值改变旋转方向。Attack 是展开所占的生命周期比例，例如 18 帧中 Attack=0.18 约用 3.2 帧展开。
Motion Ease 控制挥斩后的减速，0 为匀速；Head Bias 将主体宽度偏向前端。Radius / Width / Expansion 控制基本尺寸，Taper 控制收尖。

Core Width 控制窄亮锋刃的相对宽度，Afterimage 在开发版资产版本 5 中控制两条有色残影的面积，设为 0 可关闭残影；版本 1–4 仍控制透明度。
Streaks 控制主体笔触的对比，Breakup 控制挥斩后的噪声侵蚀；Dissolve=1 会完全隐藏材质。新版 Fade 控制退场时的分段镂空，设为 0 可保留这些段，但不关闭 Breakup。
Strength 控制整体发光，颜色控制主体；锋刃使用较浅的冷白色，因此仍有亮度和色彩层次。

Contour 控制前端钩形与内侧缺口，Bank 控制刀面的深度弯曲，设为 0 可恢复平面；Wake Spread 控制挥斩过程中残影的角度分离。新版以局部 XY 为主平面；旋转控制器即可改变斩击方向。Low / Medium / High 使用 32 / 64 / 128 个沿弧分段，新版 Low 仍为 594 顶点、480 个四边面。
保留 `vfx_arc`、`vfx_inner` 和新版的 `vfx_wake` 属性，它们控制沿弧位置、横向宽度和残影编号。需要雕改最终形状时，可先复制，再应用 Geometry Nodes 修改器。
支持参数 JSON、用户库、完整效果文件和无插件播放；跟随武器动画的真实采样路径仍使用 Ribbon Trail。

当前源码新建刀光使用资产版本 3，尚未发布。版本 1/2 的文件、材质、节点和参数预设继续按原结构读取或重建，不自动升级，不覆盖手动编辑。
高清三阶段渲染、复现命令和实际检查范围见 [刀光视觉验收](docs/VISUAL_REVIEW.md)。

刀光与打击爆发在同一镜头的原生预览场景、复现方法及检查限制见 [镜头衔接记录](docs/COMBAT_VISUAL_REVIEW.md)。

角色动作、正反遮挡、远景和同场景耗时的检查正在转向真实蒙皮角色，见 [角色战斗镜头](docs/CHARACTER_COMBAT_REVIEW.md)。完整场景与原生节点可从源码重建；这些技术检查不等于整体艺术验收。

## Impact Burst 打击爆发

在 **Create Mesh VFX** 中选择 **Impact Burst**，会在 3D Cursor 处创建一个 24 帧的四层组合。已发布的 0.22.2 使用中心白色短闪、橙色尖片、冲击波和延迟余烬。当前 0.22.3 开发版改用断裂的三团压力体积、四条细喷射、两条辅助卷流、压力弧和错峰退场，仍未发布；具体问题与实际检查范围见 [当前主体记录](docs/IMPACT_SURFACE_REVIEW.md)。默认只播放一次，不添加辉光合成。

选中组合调整整体 Start / Duration / Speed；选中成员可以分别调整颜色、强度和时间。需要独立编辑时点击 **Ungroup All**，保留拆分时各层状态。完整效果导出保留这四层及手动节点；单层参数 JSON 只保存该层参数，不保存手动节点。

普通 **Particle Burst** 提供 Shape（0 圆粒、1 尖片）、Stretch（尖片半长相对 Size 的倍数）、Planar（1 将随机散射压到局部 XY 平面）和 Motion Ease（0 匀速运动时钟、1 快出慢停）。例如 Shape=1、Stretch=6 可生成细长尖片。尖片沿轨迹方向转动，前端偏白、尾部较暗；Fade 仍控制尺寸缩减。Motion Ease 改变直接计算的位置与重力时钟，不是物理模拟；修改它会重新计算当前帧。

Impact 候选的短闪和主体采用私有网格，沿用 Burst 控制器保存时间、尺寸、运动等参数，侧栏只显示实际使用的项。Count、Shape、Gravity、Spread 不驱动这两个造型，普通 Burst 不受影响。主体的 Size、Stretch、Planar、运动参数与 Fade 可以编辑；材质中的 Rim Contrast / Rim Width 控制浅背景下的深色边界，设 Rim Contrast=0 可关闭；完整编排请用 Save Complete Effect 保存，单层参数 JSON 会重新创建普通 Burst。

要调整主体的细节，选择 `Impact • Main Shards` 下的网格：Geometry Nodes 的 **Pressure Unfurl** 调整截面翻卷，**Fine Ejection Width** 调整细喷射宽度。Shader Editor 的 **Pressure Fracture** 调整早期破口，**Pressure Support Value** 调整辅助压力块明暗；1 关闭这项明暗差异。已有资产保留原节点；这些控制需要用 **Save Complete Effect** 保存。

选择 `Impact • Shockwave` 下的网格，可在 Geometry Nodes 用 **Pressure Crest Height** 调整波面隆起高度；设为 0 可恢复平面。在材质中，**Pressure Crest Edge Contrast** 调整暗边，**Pressure Flow Travel** 调整噪声在寿命内移动的距离。Width 调整实际宽度，Dissolve 调整破碎程度；当前波面由三段长短、宽窄不同的压力弧组成。观看范围和限制见 [压力弧记录](docs/IMPACT_WAVE_REVIEW.md)。

普通 Burst 新建资产使用版本 2，旧版本 1 资产与参数预设继续按原结构读取。Impact 的短闪和主体使用私有造型，不会随载入自动更新。旧版主尖片的 Side Contrast / Illustrated Light 只适用于仍采用尖片材质的资产；当前主体请使用上面的压力控制。

Actions 的 `combat-shot-visual-review` 附件提供完整视频与原生场景。视频生成不等于已经观看；旧版 #69 已按用户允许的 MP4 隔帧方法检查，新生成器需重新复核。复现命令和限制见 [镜头记录](docs/COMBAT_VISUAL_REVIEW.md) 与 [当前主体记录](docs/IMPACT_SURFACE_REVIEW.md)，实时播放仍未验证。

## Fresnel 能量护盾

点击 **Create Energy Shield** 创建球形护盾。它有独立的球面网格和材质，不修改角色或已有模型。
Fresnel（菲涅耳）节点根据视线和表面的夹角计算反射比例，使球面边缘比正面明亮，中心仍可透视。
默认循环播放；Start / Duration / Speed / Loop 和其他效果相同，可以绑定角色、加入组合或保存参数预设。

Radius 控制初始半径，Expansion 控制一周期增加的半径。IOR 是折射率，这里用来调整 Fresnel 响应；
数值越大，正面越明显。Rim Power 越大，亮边越窄；例如 0.5 是较宽的柔和光边，1.5 更接近细边。
Opacity 调整整体透明度，RGB / Strength 调整发光。发光不自动添加光晕，需要另加 Screen VFX 或自己的合成节点。

Dissolve 用三维噪声切掉部分表面，1 表示完全消失。Noise Scale 调整噪声大小，Flow 控制一周期的噪声演变量，
0 保持不动，负值反向演变；Fade 控制周期内淡出。噪声使用球面的生成坐标，不依赖 UV 接缝。
循环会重置噪声，不能保证首尾连续。第一版只显示朝外的表面：摄像机进入球内时护盾不可见。

质量在创建时决定球面面数：Low / Medium / High 为 128 / 512 / 2048 面，均使用平滑法线。
可以继续编辑网格和节点；Geometry Nodes 会缩放原网格，因此编辑后的形状也会保留。
重叠的透明球面会增加渲染开销，低配置设备建议先用 Low，并减少屏幕内的重叠层数。
Eevee 使用抖动透明，低采样时可看到颗粒；可提高渲染采样，但会增加耗时。它与 Cycles 的透明外观并不完全相同。
CPU 和 Eevee 的三种外观预览可用 `tools/shield_preview.py` 重建；发布附件也包含 CPU 预览图。

## Flipbook 图集动画

图集是一张按网格排列多帧画面的静态图片。点击 **Create Flipbook** 选择图片，并设置 Columns（列数）和 Rows（行数）。格子从左上开始编号为 0，先向右再向下。First Frame / Last Frame 指定包含两端的播放范围。例如 4×4 图集有 16 格，完整范围为 0–15。

效果在一个生命周期内均匀播放所选格子。超出网格的编号会被限制；Last 小于 First 时保持 First 格，不倒放。Width / Height 控制贴片尺寸，Opacity / Fade 控制透明度，RGB / Strength 控制染色和发光。贴片位于控制器局部 XY 平面，请旋转它面向镜头；目前没有自动朝向相机或单独的图集 FPS 设置。

图片 alpha 与 Opacity 相乘。采样使用最近邻，保留原图片的色彩空间和 alpha 设置。选帧边界使用百万分之一周期的容差，避免渲染中的浮点误差导致偶尔显示上一格。图集模块只使用静态图片；图片序列使用下文的独立入口，电影和 UDIM 多块纹理尚不支持。

复制效果时共享图片，网格和材质则各自独立；删除效果不会删除图片。可以在侧栏图片选择框或材质节点中换图。分享 `.blend` 前使用 **File → External Data → Pack Resources** 打包图片。JSON 预设只引用图片文件；把图片与 JSON 一同迁移可保留相对路径。生成图片若尚未保存到磁盘，需要先保存才能导出参数预设。

## 图片序列 Sprite

点击 **Create Image Sequence**，选择第一张带编号的图片并设置 File Count（读取的文件数，1–4096）。
例如选择 `burst0010.png`、File Count=4，会使用 `burst0010.png` 到 `burst0013.png`。
文件编号必须连续，缺图时会在创建对象前报错；编号范围为 0–1000000。图片由 Blender 在使用时解码，创建时只检查文件存在并解码第一张。

First Frame / Last Frame 使用相对第一张图片的编号，从 0 开始。例如上述序列设置 1–2，会播放文件 0011 和 0012。
序列在一个 Duration 内均匀播放，与图集一样支持 Start / Speed / Loop、尺寸、染色、透明度和发光。
超出文件数会限制到末图，Last 小于 First 时保持 First，不倒放；支持子帧、负开始帧和场景时间映射。
复制效果共享图片数据，但各自的选帧驱动独立，不会改变用户已载入的静态图片类型。

图片序列仍依赖外部文件。JSON 记录第一张图片的相对路径和文件数，分享时请把整段序列一起复制。
当前不能将序列作为完整 `.blend` 效果导出，包含序列的组合也会拒绝导出；单个序列可用参数预设复用。
手动编辑材质中的序列源或 File Duration 后，请重新创建效果，避免预设中记录的文件数与节点不一致。
本功能使用原生 Image Texture 和驱动器，保存重开后无需插件，但图片文件仍必须可访问。

## Ribbon Trail 轨迹刀带

选择动画对象，或在 Pose Mode 选中活动骨骼，点击 **Bake Ribbon Trail**。设置 First / Last / Sample Step（采样步长）；范围必须能被步长整除，最多 2048 个点；采样时场景 Time Remapping 必须为 1:1，完成后可重定时播放。例如 1–25 帧、步长 2，会保存第 1、3、5……25 帧共 13 个位置。

插件读取对象原点或骨骼起点或末端在各采样帧的世界位置，包含父级和约束的影响。操作结束后恢复原来的帧和子帧，不修改源动画。若源对象由物理模拟驱动，请先用 Blender 完成模拟缓存；轨迹工具不负责预热模拟。

结果是可编辑的刀带网格，播放时在采样点间按时间直线插值，保留快慢变化。采样步长越大，越可能丢失源动画的细节。Start 默认等于 First，Duration 默认等于 Last−First。与其他效果一样，生命周期不包含右端帧；循环会在右端重新开始。

Width 是全宽，Length 是尾带占完整采样时间的比例，Fade 控制随时间缩窄。例如 Length=0.25 只显示最近四分之一采样时间的路径。初始宽度方向由轨迹切线和世界 Z 轴计算，退化时改用 Y 轴，并尽量保持相邻方向一致。目前不自动朝向镜头，也不模拟扭转；急转弯、回头和交叉可能重叠，可手动编辑网格及 `vfx_side` 向量属性。

移动控制器可整体变换已保存路径。修改源动画后，只有明确点击 **Rebake Ribbon** 才会重新采样：材质、节点、修改器和当前变换保留，手动路径编辑会被替换。Source / Bone / First / Last / Step 决定下一次采样，修改它们不会自动改变回放 Start / Duration。删除源对象后仍能播放已有刀带，但重新采样需要有效源。

为旋转的刀刃、翅膀或指尖创建拖尾时，在 Pose Mode 选择骨骼，创建对话框勾选 **Use Bone Tail**，采样骨骼末端；不勾选则采样起点。例如刀刃绕固定起点旋转，起点不会画出弧线，末端可以留下刀尖扫过的路径。
侧栏的同名选项决定下一次 Rebake 使用哪一端，不会自动替换已有路径。对象模式仍采样对象原点，忽略此选项。旧文件没有这个选项时，继续按起点重新采样；新建一个 Ribbon 可使用末端。
采样使用父级动画及约束求值后的世界位置，不修改骨架的动画或约束。`tools/bone_trail_preview.py` 可重建起点与末端的对比预览。

Ribbon 暂不支持 JSON 参数预设。使用 Duplicate 复制，或用下文的 **Save Complete Effect / Load Complete Effect** 复用完整路径。

## Particle Burst 粒子爆发

点击 **Create Particle Burst**，默认生成 64 个低面数球形粒子。每个效果只有控制器和一个网格对象，不会为每个粒子创建独立对象。Count 最多 2048；Low / Medium / High 在创建时决定球形粒子的细分级别；版本 2 也可切换为固定低面数尖片，参数见上文 Impact Burst。

Seed 决定可重复的随机方向、速度和尺寸变化。Spread=0 沿控制器局部 +Z 发射，Spread=1 向各方向散射；Randomness 控制变化幅度，Spawn Radius 控制初始径向距离，Size 是出生半径，Fade 控制逐渐缩小。

Velocity / Gravity 使用控制器局部空间的单位/秒和单位/秒²。**Motion Seconds** 是轨迹包含多少秒的物理运动，**Duration** 是用多少帧播放它。例如 Motion Seconds=1、Duration=24，会在 24 帧里播放一秒的弹道；改成 Duration=48，只会放慢播放，不改变轨迹形状。RGB / Strength 控制发光，可结合 Screen VFX 添加辉光。

Burst 的所有粒子同时出生，直接根据当前帧计算弹道，因此跳帧不需要缓存。改变运动参数会重新计算当前轨迹，不累积之前的受力；循环重置整组粒子。需要陆续出生的粒子时，使用下面的 Continuous Emitter。两者均不处理碰撞，Geometry Nodes 可继续编辑，应用修改器可得到当前帧的普通网格。

## Continuous Emitter 连续粒子发射

点击 **Create Continuous Emitter**，创建沿局部 +Z 喷出的粒子流。Rate 表示每运动秒出生多少个粒子，Emission Seconds 表示发射多少运动秒，Lifetime 表示每个粒子存活多少运动秒。第一个粒子在 Start 出生，后续粒子间隔为 1 / Rate；Rate 或 Emission Seconds 为 0 时不显示粒子。

**Duration 包含停止发射后的寿命尾段**：整个周期的运动时间为 Emission Seconds + Lifetime。例如 Rate=20、Emission Seconds=2、Lifetime=0.5、Duration=60，前 48 个播放帧陆续发射，后 12 帧等待剩余粒子消失。改变 Duration 或 Speed 只调整播放快慢，不改变弹道；场景帧率不改变这些运动秒参数。

Seed 为每次出生生成可重复的随机方向、速度和尺寸。Velocity / Gravity、Spread、Randomness、Spawn Radius、Size 的含义与 Burst 相同；Fade 按每个粒子自己的年龄缩小尺寸。Loop 重复整个发射及尾段，因此每轮都会重新填充粒子流，不保证无缝衔接。

每个效果只有一个网格对象。为控制开销，同时存活的粒子槽最多 2048 个；实际 Rate 不超过 `2048 / Lifetime`，面板显示 Effective Rate，触及限制时显示提示。默认使用 Low，每粒子 20 个三角面；数量多时先减少 Rate 或 Lifetime。

这是直接计算当前状态的局部空间效果，无需缓存。移动或绑定控制器会连同已经出生的粒子一起移动。修改 Rate、Lifetime、Emission Seconds，或为它们设置关键帧，会使用当前值重新计算出生安排，不累计过去的发射或受力。需要沿角色走过的世界路径留下效果时，使用 Ribbon Trail；本版没有世界空间发射历史、碰撞或外部力场。

支持独立复制、组合时间控制、参数预设及完整效果文件。保存后不安装插件也能播放。`tools/emitter_preview.py` 可重新生成填充、稳定发射和尾段三个阶段的 CPU 预览；用 `-- --engine BLENDER_EEVEE --scale 50` 检查 Eevee。

## Screen 辉光和闪光

点击 **Add Screen VFX**，为当前场景添加 Glare 辉光和随时间变化的全屏颜色覆盖。只有这个操作会插入合成节点，创建其他 3D 特效不会自动改写合成链。

没有合成节点树时，会创建 Render Layers → VFX → Image 输出；已有节点树时，插入到活动 Image 输出之前。节点树必须只有一个活动的彩色 Image 输出，且输入已连接。共享或链接的节点树需先在 Blender 中 **Make Single User**，使当前场景使用独立副本。

Strength / Threshold / Glow Size 控制辉光强度、亮部阈值和范围。Flash 控制开始时的全屏颜色覆盖，RGB 决定颜色，Fade 控制衰减。默认 Flash=0，避免创建时白屏；默认 Loop 开启。关闭循环后，生命周期结束即输出原图。移动控制器不影响屏幕效果。

可以复制或叠加多个 Screen 效果。删除时只移除自己的合成层，并将当前上游重新接到下游；用户新增节点和分支会保留。如果输入断开、额外输出仍被使用或节点组被共享，插件会先报错。只有没有被用户改过的默认基础树才会一并清理。

合成设备沿用场景设置。没有独立显卡时，可在渲染设置中将 **Compositor Device** 设为 **CPU**；自动测试和发布预览都使用 CPU 合成。

## Cloth Energy Sheet 布面模拟

点击 **Create Cloth Simulation**，选择网格质量：Low / Medium / High 分别为 81 / 169 / 289 个顶点。
效果包含隐藏的模拟源和可见的播放网格。初始显示静止布面，点击 **Bake / Replace Stored Cloth Motion** 才计算运动。
源使用 Blender 原生 Cloth，固定一侧边缘，在重力下下垂，可制作发光布片或能量幕。

模拟按连续帧计算，再按 Step 保存姿态。First / Last 是模拟帧区间，与播放 Start / Duration 分开；
默认模拟 1–25 帧，保存 25 个姿态。区间最多跨 240 帧，最多保存 121 个姿态，范围须能被 Step 整除。
结果存成绝对形态键（网格的多组顶点位置，由 Blender 在它们之间插值），而不是依赖临时目录的缓存文件。
保存 `.blend` 后，无需插件或模拟源也能播放已存运动；删除模拟源后将无法重新烘焙。源或输出缺失、重复，或源修改器结构损坏时，插件会在复制前报错，不留下半份副本；组合复制也会先检查所有 Cloth 层。

**UNBAKED** 表示尚未存运动，**BAKED** 表示源设置与上次烘焙一致，**STALE** 表示源已变化，需要重新烘焙。
修改源网格、固定点权重、Cloth 设置、场景重力、帧率或模拟区间会使旧结果过期。
旧结果仍保留可见，直到明确重新烘焙；烘焙失败也保留旧结果，并恢复当前帧、源父级和显示状态。
**Clear Stored Cloth Motion** 删除已存形态键，回到静态参考网格。

播放 Start / Duration / Speed / Loop 只重放已存运动，不重新求解。移动、旋转和缩放控制器也只变换播放结果；
模拟始终在效果局部坐标中计算。默认播放区间不包含右端帧，与其他效果相同；Loop 会重置到首个姿态，不保证动作首尾连续。

面板可调整求解精度、质量（Mass）、拉伸和弯曲刚度等原生 Cloth 参数。点击 **Show Cloth Source for Native Editing** 可显示线框源，
在 Blender 中编辑网格、固定点顶点组和 Cloth 设置；完成后离开 Edit Mode 再烘焙。源不参与渲染。
复制会得到独立的模拟源、形态键和播放驱动，删除效果会检查外部网格或形态键引用。
烘焙会替换播放网格及其姿态，保留输出材质槽和节点修改器；请先保存有价值的手动几何编辑。

当前版本限制为静态源、一个 Cloth 修改器、最多 625 顶点 / 1250 面 / 2500 边和 1–12 个求解质量步数。
不支持碰撞、自定义力场、源动画、未应用的源变换、外部磁盘缓存或改变拓扑的源修改器。
烘焙时场景 Time Remapping 必须为 1:1；完成后可使用场景映射重定时已存运动，无需重新求解。
可以给控制器制作播放动画、绑定角色或加入组合；完整效果用 **Save Complete Effect** 保存，暂不导出为参数 JSON。

## 对象和骨骼绑定

选择空间效果后点击 **Bind Object / Bone**，搜索当前场景中的目标对象；目标是骨架时还可选择骨骼。也可先选目标，再以效果为活动对象打开对话框，自动填入唯一目标。

绑定使用 Blender 原生 Child Of 约束，让控制器跟随目标。挂接瞬间保持当前世界位置、旋转和缩放，不修改目标动画、骨骼或约束。可在 Object Constraints 中查看约束；目标重命名或没有安装插件都不影响已保存的跟随关系。Screen 不提供空间绑定。

**Unbind** 移除插件添加的约束，保留当前帧的世界姿态。控制器若还有其他约束或变换/约束动画，会要求先用 Blender 的 Bake Action 等工具烘焙，避免丢失动画。颜色、时间等自定义参数动画可以保留。请勿重命名 `VFX • Binding` 约束；若已改名，恢复为控制器 `vfx_binding_constraint` 属性记录的名称后重试。

解绑若遇到剪切变换会先拒绝，保持约束和姿态。剪切可能由非均匀缩放的骨架与旋转共同产生，不能仅用位置、旋转、缩放三个通道准确保存；请先烘焙变换，或在不含剪切的姿态解绑。插件不会自动改动角色缩放。

副本保留相同目标，但约束独立，解绑或删除副本不影响原效果及目标。插件拒绝绑定到其他 VFX 层级，并检查常见父级、约束和对象驱动依赖环；用户自己搭建的 Geometry Nodes 仍需避免产生间接闭环。

## 多层组合

在 Object Mode 中选中 2–32 个空间效果的控制器或网格，点击 **Compose Selected VFX**。
插件创建一个组合控制器，将各效果设为子级，保持当前世界变换。原效果的网格、材质和节点仍可独立编辑。
为避免覆盖已有关系，参与组合的控制器不能已有父级、约束或时间参数动画；颜色和形状动画可以保留。
目前不支持组合 Screen 效果或嵌套组合。

组合的 Start / Duration / Speed 统一调整所有层。各层面板中的 Start Offset Ratio、Duration Ratio 和 Local Speed
分别控制相对开始位置、时长比例和额外倍速。例如组合时长 48 帧、某层开始比例 0.25，该层会延后 12 帧；
将组合时长改成 96 帧，会延后 24 帧。Speed=2 则把这些时间间隔减半。各层时长至少为一帧。
开启组合 Loop 后，每个组合周期统一重启，各层在自己的有效时间内显示，较短的层不会自行循环填满整个周期。
不循环时，Duration 是整体时间比例尺；如果手动调大某层的时长比例，它可以延长到组合参考区间之后。

组合面板列出各层，点击名称即可编辑。Duplicate 组合会复制全部层和动画，副本使用自己的控制器；
Duplicate 单层会得到脱离组合的独立效果，Detach Layer 则将原层移出组合，两者保留当前时间参数和世界姿态。

选中组合控制器，点击层列表上方的 **Ungroup All**，即可一次拆开全部层，并选中拆出的控制器。
例如在第 61.25 帧拆开 16 层循环组合，各层保留该帧的世界位置、旋转、缩放和已求值的 Start / Duration / Speed / Loop；
材质、节点、已存路径、模拟烘焙结果和参数关键帧仍属于原来的层，不会重建。拆分后各层独立播放，不再跟随组合未来的动画或循环。
没有其他引用时，空组合控制器自动删除；如果用户对象、驱动或自定义属性仍引用它，则保留控制器并显示提示。可以用一次 Undo 恢复整组。

拆分前会检查全部层。如果有一层存在变换或时间关键帧、约束、手动修改的时间驱动或无法用位置/旋转/缩放保存的剪切姿态，
操作会报错且不拆开任何一层，请先烘焙或处理相应编辑。单层 Detach Layer 和独立复制也采用相同的姿态保护。
完整组合的复制不需要解除成员的变换动画。

整组 Delete 会先检查所有层，任一层有外部共享资源就全部保留，不会删到一半才报错。
手动改变了成员的父级时，请先 Detach Layer 修复关系。组合可绑定到角色，也可用 **Save Complete Effect** 复用，暂不保存为参数 JSON。

## 保存完整效果

参数 JSON 适合保存数值；需要保留手动节点、网格修改、关键帧、轨迹或 Cloth 姿态时，使用 **Save Complete Effect**。
选中空间效果或组合控制器，选择一个独立的 `.blend` 文件。导出不会保存整个场景，也不能覆盖当前项目文件。
随后在另一个项目点击 **Load Complete Effect**，载入文件中的效果。每次载入都会分配新实例编号，
即使原效果仍在场景里，也可以独立编辑、复制和删除。

例如，将刀光与已烘焙的布面组成一组，编辑它们的材质后保存完整效果；载入时会保留组内时间关系、材质节点和存储的姿态。
开始帧、位置、变换动画保持导出时的设置，不会自动放到当前帧或 3D Cursor。载入后再移动控制器或修改时间。
导入支持 Undo；导出的文件和被覆盖的旧文件不能通过 Blender Undo 恢复。

完整效果必须独立于外部场景对象。绑定到角色的效果请先解绑，或先在副本上处理需要保留的动画，再保存；
导出不会自动带走角色模型、骨架或外部约束目标。节点引用的外部对象、非本效果对象组成的集合，以及链接库数据也会被拒绝。
静态图片先用 **File → External Data → Pack Resources** 打包，图片内容才能随效果文件移动。

轨迹的源对象只用于重新采样，导出会省略该引用，原项目的引用保持不变。载入后的路径正常播放，
需要重新采样时再指定 Source / Bone。已烘焙的 Cloth 则包含私有模拟源和姿态，仍可检查缓存状态及重新烘焙。
Screen 依赖场景合成链，图片序列依赖外部文件；两者继续使用参数预设，不保存为完整效果文件。

导出窗口的 **Preview Image (optional)** 可以选择已经加载到 Blender 的静态图片，留空则不嵌入预览。图片未加载时，先在 Image Editor 中用 Open 打开一张 PNG，再导出效果并选择它。例如给刀光选择一张已渲染的 PNG，资产库中就能按图片识别它。

输入每边最多 2048 像素，导出时保持比例、缩小到长边最多 256 像素，不放大小图。预览存入 `.blend`，之后无需原图片文件；源图片像素、尺寸、路径和颜色设置保持不变。这只影响资产缩略图，效果材质使用的贴图仍需按前述规则打包。

预览读取图片的 RGBA 像素，将直通透明度转换为预乘 RGB 后再缩小，以免透明边缘出现色晕；已经预乘的图片不会再次相乘。Alpha Mode 为 None 或 Channel Packed 时按不透明图处理，不改变源图片设置。预览不应用场景曝光、AgX 或其他视图变换；原生预览保存为 8 位通道，超出 0–1 的值会截断。建议选择已经处理好外观的普通 sRGB PNG。支持已生成的静态图片和已加载/打包的静态文件；序列、视频、UDIM 和 Render Result 不支持，渲染结果请先另存为 PNG 并打开。导出不会自动渲染预览图。

导出的集合使用效果名称，带有 Blender 原生资产标记和 VFX Studio 标签。0.17 及以上版本可读取旧版内部前缀名称的文件；新的可读名称文件需要 0.17 及以上版本载入。

需要在库中浏览时，把这些 `.blend` 放到一个文件夹，在 **Preferences → File Paths → Asset Libraries** 添加该文件夹。打开 **Asset Browser**，选择这个外部库和效果集合，在右侧边栏（N）的 **Blender VFX Studio** 面板点击 **Load VFX with New ID**。按钮会载入选中的集合，每次分配新编号，并保留原来的时间和变换；文件中有多个资产时，也只处理当前选中的集合。

请通过这个按钮或 **Load Complete Effect** 载入完整效果。普通拖放或 Append 不会更新实例编号，重复插入后可能无法安全管理。需要撤销时可使用顶栏 **Edit → Undo / Redo**；Asset Browser 内的快捷键也可能用于目录编辑。

本版只支持本地外部 `.blend` 库中的完整效果集合，不载入在线资产或 Current File 条目；场景内复制使用 VFX Duplicate。载入前需回到 Object Mode。普通集合、损坏文件或不支持的版本会报错，不留下半份实例。浏览、分类和缩略图显示使用 Blender 原生功能；插件不建立额外索引，也不会自动生成效果预览图。

## 保存和管理预设

选择效果后点击 **Save Preset** 导出参数 JSON，点击 **Load Preset** 读取文件，在当前帧和 3D Cursor 创建独立实例。它保存当前参数值、名称和质量，Flipbook 另存图片路径；不保存开始帧、绑定、变换、关键帧、图片内容或编辑后的节点。完整资产使用前文的 `.blend` 效果文件。

**User Preset Library** 面板提供用户库。点击 Refresh 读取列表，Save New 保存并命名，Create 创建效果，Rename 改名，Delete File 删除选中的 JSON。短标识用于区分同名条目。同名保存不会覆盖旧文件。文件删除先确认且不能 Undo，也不影响已创建的场景效果。

库放在 Blender 用户 DATAFILES 目录下的 `blender_vfx_studio/presets/`，不随 `.blend` 保存，卸载插件也不会自动删除。可以把外部参数 JSON 复制到该目录后刷新。最多 256 个 JSON 文件；损坏、超大和符号链接条目会被报告。Flipbook 图片缺失时会报错，不创建残缺实例，也不修改预设文件。

参数文件最大 64 KiB，使用独立格式版本，严格检查字段、数值范围和模块版本。当前格式 2 支持 ring / slash / shield / atlas / sequence / screen / burst / emitter 的资产版本 1，也能读取并转换旧格式 1 环形预设。未知版本会明确报错，不修改场景。轨迹路径暂不纳入参数 JSON。

## 删除与兼容性限制

使用插件的 **Duplicate**，不要用 Shift-D 代替；后者会复制实例编号，让插件无法区分两个效果。若外部对象共享了生成的网格、材质或节点组，Delete 会拒绝删除，请先解除共享。用户添加的子对象、外来材质和非空集合会保留；自行建立的外部约束或驱动若引用控制器，仍需自行处理。

当前实例保存结构版本为 1。保存的 `.blend` 可在未安装插件、关闭自动执行时播放，使用插件继续创作则需要重新启用。自动验证覆盖 Blender 5.2.2 Linux；Linux x64、Windows x64 和 Apple Silicon macOS 的基础后台套件已通过；新增功能的 CI 状态见路线图。
后台 Undo/Redo 已覆盖复制删除、组合、Cloth 和合成。Linux 已完成基本侧栏创建、快捷键撤销/重做、用户库保存和 Cloth 状态检查；完整交互检查尚未完成，详见 [GUI 检查记录](docs/GUI_CHECKS.md)。

## 入门资产库

当前按 [#138](https://github.com/mumu-lhl/blender-vfx-studio/issues/138) 扩库，计划加入闪电、烟尘、火焰、冲刺残影和魔法阵。闪电候选见 [PR #144](https://github.com/mumu-lhl/blender-vfx-studio/pull/144)，未验收原型不计入当前完整资产数量。

发布附件中的 `blender-vfx-studio-examples-版本.zip` 是独立资产库，不能作为插件安装。解压后，将文件夹添加到 Blender 的 Asset Libraries，再通过 Load VFX with New ID 创建效果。
已发布的 0.22.2 包含 Energy Charge、Impact Burst 和 Arc Slash 三套 Low 资产。当前开发包新增 Lightning Strike 候选：分支电弧、错峰复击、接触闪光、火花与地面余波；默认 Medium，`quality/` 另提供 Low / High 完整文件，质量版本不计作额外效果。全部使用原生节点和嵌入预览，不需要外部贴图或缓存。闪电的高清和完整动画检查正在进行，尚未发布新版本。

开发版 Energy Charge 会先汇聚、压紧中心，再收束释放。选中 `Charge • Compressed Core` 下的网格，在 Geometry Nodes 用 **Nucleus Compression** 调整积蓄时的压扁程度，0 关闭，默认 0.6。**Nucleus Seed Size / Nucleus Stored Size** 调整初始与蓄满大小，**Release Pinch / Release Stretch** 调整释放形态。修改后用 **Save Complete Effect** 保存；旧完整资产保留原节点。实际观看范围见 [压缩记录](docs/CHARGE_TENSION_REVIEW.md)。

地面层由三条较连贯的进流向核心上行。选中 `Charge • Ground Intake` 下的网格，用 Geometry Nodes 的 **Ground Intake Lift** 调整终点高度，默认 0.8 配合该层初始位置 Z=-0.8；0 回到低位平面。路径随组合移动，单独移动本层时需调整高度。材质的 **Flow Packet Density** 调整分段密度。观看范围与限制见 [地面进流记录](docs/CHARGE_GROUND_REVIEW.md)。

资产保留从第 1 帧开始的播放时间，不自动定位到当前帧。0.22.2 的充能缩略图使用额外 Screen 辉光，当前艺术重设计取消了它；载入均不会改动你的合成链。具体参数、时间和重建方法见 [入门库指南](docs/STARTER_LIBRARY.md)。

## 从源码构建与验证

需要 Python 3.11+ 和 Blender 5.2.2，没有第三方运行依赖。`BLENDER_BIN` 可指定 Blender 路径。

```sh
python tools/build.py
python tools/test.py
python tools/test_install.py
blender -b --factory-startup --python-exit-code 1 --python tools/build_examples.py
blender -b --factory-startup --python-exit-code 1 --python tools/preview.py
blender -b --factory-startup --python-exit-code 1 --python tools/preview.py -- --engine BLENDER_EEVEE --scale 25
```

构建的安装包在 `dist/`。未发布开发版本可从 [Actions](https://github.com/mumu-lhl/blender-vfx-studio/actions/workflows/ci.yml) 成功构建的 `blender-vfx-studio-extension` 附件下载。解压后，名称为 `blender-vfx-studio-版本.zip` 的文件用于安装插件；`blender-vfx-studio-examples-版本.zip` 是独立入门资产库，按上节载入，不能当作插件安装。

测试使用真实 Blender 后台模式检查参数、时间、实例隔离、安全删除、保存重开和安装/卸载。预览场景及 PNG 写入不提交到 Git 的 `work/`。静态检查使用 Ruff，固定版本见 CI 配置。

默认效果的 CPU 求值测量和限制见 [性能记录](docs/PERFORMANCE.md)。

代码分工见 [DESIGN.md](DESIGN.md)，参数和时间约定见 [CONTEXT.md](CONTEXT.md)。许可证：**GPL-3.0-or-later**。

当前发布的是 [0.22.2](https://github.com/mumu-lhl/blender-vfx-studio/releases/tag/v0.22.2)，附原生衔接检查包。0.22.3 尚未发布；当前充能、刀光与命中的改进、实际观看范围及未解决问题见 [Roadmap](ROADMAP.md) 和 [艺术缺口](docs/ART_DIRECTION_REVIEW.md)。下载的 0.22.2 保留原造型，不会自动换成开发版新造型；安装和参数编辑见 [使用指南](docs/STARTER_LIBRARY.md)。
