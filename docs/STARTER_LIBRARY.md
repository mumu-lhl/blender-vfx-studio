# 原生效果入门库

这是独立的示例资产包，不是插件安装包。从 Releases 下载与插件同版本的 examples ZIP，解压到普通文件夹，在 Preferences → File Paths → Asset Libraries 添加这个文件夹，再在 Asset Browser 中选择它。

先启用插件，选中资产后点击右侧 Blender VFX Studio 面板的 **Load VFX with New ID**。这个操作会分配新的实例编号；普通拖放不会分配，重复载入可能发生编号冲突。也可以在 VFX 侧栏用 **Load Complete Effect** 直接选择某个 `.blend`。

所有示例从第 1 帧开始，默认不循环。载入保留原时间和变换，不会自动放到当前帧或 3D Cursor。选择组合控制器可调整整体 Start、Duration、Speed 和 Loop；在组合面板选择某一层，则可修改该层的颜色、尺寸和时间。

**Energy Charge（48 帧）** 在 0.22.2 中包含轨道环、地面环、球壳及向内汇聚的连续粒子，共 4 层。开发版本使用错开前沿的双束、辅助进流、直接汇入中心的短弯流、地面进流和弯曲粒子；外围收紧时，中心积蓄为有间隙的蓝白束，再收束释放。仍为 4 层，不需要外部贴图或缓存。旧完整文件不自动换造型或材质。

粒子的 Spawn Radius 控制出生距离，正的 Velocity 越大，抵达中心越快；到达后停止，不穿过中心向外散出。粒子在控制器局部空间运动，移动整体也会移动已出生粒子，不保留角色走过的世界轨迹。

开发版核心的 Geometry Nodes 提供 Main Intake Guide Width、Auxiliary Guide Width 和 Auxiliary Packet Width，分别调整主体连接、辅助连接与辅助头部。Nucleus Compression 调整积蓄时的压扁程度，0 关闭；Nucleus Seed Size / Nucleus Stored Size 调整初始和蓄满尺寸，Release Pinch / Release Stretch 调整释放形变；核心材质的 Nucleus White Threshold 越高，白色区域越小。外层丝带的 Spiral Turns / Intake Vertical Reach 调整绕行角度与起始高度。地面层为三条上行进流；其 Geometry Nodes 的 Ground Intake Lift 调整抬升高度，默认 0.8 配合本层位置 Z=-0.8，路径随组合移动。这些私有造型需用 Complete Effect 保存。具体选择哪个对象、观看范围和限制见 [进流](CHARGE_INTAKE_REVIEW.md)、[外层路径](CHARGE_FLOW_REVIEW.md) 、[束流](CHARGE_STREAM_REVIEW.md) 与 [内核](CHARGE_FOCUS_REVIEW.md) 记录。

**Impact Burst（24 帧）** 在 0.22.2 中由白色短闪、12 个橙色尖片、冲击波和稍晚出现的余烬组成，共 4 层。开发版本改为紧凑闪核、三团有不同明暗的断裂主体、四条细喷射、两条卷流及三段有隆起截面的压力弧，继续分层退场。它与侧栏直接创建使用同一生成器；Size 调整主层整体，主层 Geometry Nodes 的 Fine Ejection Width 单独调整细喷射宽度。外层仍可分别修改时间与颜色，Ungroup All 一次拆开全部层。形体和远景仍需打磨，见 [当前主体](IMPACT_SURFACE_REVIEW.md) 和 [细喷射](IMPACT_FINE_REVIEW.md) 记录。

**Arc Slash（18 帧）** 是单层紫色程序化刀光，不需要角色动画或采样路径。Arc 调整弧度，Width 调整宽度，Spin 调整旋转；Attack、Motion Ease、Core Width、Afterimage、Streaks 和 Breakup 调整展开、减速、锋刃、残影、笔触与侵蚀。0.22.2 包含版本 2 的规则月牙。版本 4 把体积推向前端，让两条残弧独立揭示和退场，并用较宽的流动笔触减少细丝；Head Bias 控制前端偏重，Contour、Bank、Wake Spread 控制轮廓、深度与残影分离。当前开发分支的版本 5 保留主刀面，将残影片段两端收尖；Afterimage 调整可见面积，存活部分保留紫色。仍在提升艺术品质，实际观看范围见 [残影记录](SLASH_WAKE_REVIEW.md)。它与侧栏直接创建的刀光使用同一生成器，只把时长设为 18 帧；版本 1/2/3/4 及旧完整文件不自动升级。

原三套示例保留 Low 质量；Lightning Strike 默认 Medium，quality/ 目录另提供 Low 和 High 两个完整文件。同一效果的质量文件不计作额外种类。

**Lightning Strike（18 帧）** 由分支电弧、短促接触闪光、飞散火花和地面余波组成。主干先落地，再做两次逐渐减弱的复击；第一峰值在 Start+2 左右。主层 Radius 调整分支横向范围，Width 调整线宽，Strength 调整发光，Noise Scale 调整细扰动，Dissolve 侵蚀电弧。在 Geometry Nodes 用 **Bolt Length** 调整高度，**Branch Reach** 调整分支伸展。普通参数 JSON 会重建原生环形基础，完整造型与手动节点请用 **Save Complete Effect** 保存。已完成高清角色、隔帧动画和无插件检查，范围、实测成本与限制见 [闪电记录](LIGHTNING_REVIEW.md)。未观看实时播放；远景细枝和接触火花较弱。

**Dust Impact（32 帧，开发候选）** 使用一个原生程序化体积域形成不等大的烟尘团，配合地面薄尘和短促碎屑，适合落地、踩踏或地面冲击。云团先横向散开，再抬升并变薄；不发光，需要场景灯光。主层 Width 调整团块大小，Expansion 调整铺开距离，Noise Scale 调整密度细节，Fade 调整消散，Dissolve 侵蚀密度。主层 Object Properties → Custom Properties 的 Dust Rise Height、Dust Roll Speed 和 Dust Density 分别控制抬升、内部纹理上卷与光学密度。体积需要 Eevee 的体积渲染或 Cycles，Solid 模式仅显示域边界；这不是流体模拟，不需要缓存。三种质量档改变密度团数量、噪声细节与碎屑数量。完整动画、明暗背景和实测成本还在检查，暂不计入已验收数量。

**Stylized Fire（52 帧，开发候选）** 是三团不等高的外焰、两团较小的热色内焰和持续上升的余烬。主层在 48 帧内完成点燃、维持和断燃，余烬晚四帧结束。主层 Width 调整宽度，Noise Scale 调整流动色带，Strength 控制光量，Dissolve 侵蚀火面；Object Properties → Custom Properties 的 Fire Height、Fire Flow Speed 和 Fire Curl 控制高度、上卷节奏与火舌形变。颜色参数作为红橙黄色带的乘色。Low / Medium / High 改变截面细节和余烬生成率；不是换色变体。当前只通过行为与原生重开检查，尚未查看实际火焰渲染，不计入已验收数量。

**Character Dash Echoes（30 帧，开发候选）** 保存三个不同位置与姿态的角色残影，依次出现、逐个淡去。Low / Medium / High 分别保留两／三／四姿态，保留角色原始网格形状。选中自己的 Mesh 或 Armature，在侧栏点击 **Capture Dash Echoes**，指定首尾帧即可创建独立残影；默认采样跨度为 12 帧。跨度须能被姿态间隔数整除，例如三姿态用 1、7、13 帧。Echo Tail 决定每个姿态存活的帧数，组合控制器可再调整整体时间和位置。各层可调透明度、颜色、边缘与噪声侵蚀。采样会求值现有修改器和形态键，随后恢复原帧和子帧；不改动源数据，不保留运行时源引用。源动画修改后需重新捕获；参数 JSON 不包含姿态网格，请保存完整效果。此功能不重定向或修改骨架。

内置残影轮廓取自本仓库固定版本的 [KayKit Adventurers CC0 角色](../assets/character-review/README.md)，没有角色贴图或骨架依赖；可用上述按钮捕获自己的角色。代码许可证仍为 GPL-3.0-or-later。当前完成行为检查，实际角色镜头与资产预览尚在检查，不计入已验收数量。

**Calligraphic Magic Circle（72 帧，开发候选）** 分为花瓣主印、反向转动的符文带和释放时升起的立体符记。前段逐笔形成图案，中段保持，后段符记升起，地面印记先退去。Radius 和 Width 调整尺寸与笔画，颜色与 Strength 可分层编辑，Noise Scale / Dissolve 调整墨迹侵蚀，Fade 调整消散。各层 Object Properties → Custom Properties 的 Sigil Spin 控制一个周期的转角，释放层的 Sigil Lift 控制升起高度。图案是本项目生成的原生网格笔画，不依赖字体、图片或缓存；可直接编辑网格与节点，完整造型请用 Save Complete Effect 保存。三档质量改变曲线采样密度，保持同一图案与时序。已完成高清阶段图、明暗与远景、完整视频隔帧及原生文件检查，CI 通过；范围和限制见 [魔法阵记录](MAGIC_REVIEW.md)。预览仍需完成实际读取，待依赖合并后计入 main 数量。

全部资产保留原生对象、网格、材质和 Geometry Nodes。使用 VFX Duplicate 创建独立副本，使用 VFX Delete 删除。示例不需要外部贴图、角色或缓存；不加载插件也能播放和渲染，继续使用侧栏创作则需要启用插件。

保存手动节点、轨道驱动或整个组合时，使用 **Save Complete Effect**。单层参数预设只保存参数。例如，只保存充能粒子层的参数 JSON，再创建时会得到普通 Emitter；向内运动和尖形等私有节点不会随参数重建。

缩略图为 256×256 的 Cycles CPU 渲染。0.22.2 的 Energy Charge 缩略图曾加入额外 Screen 辉光；当前候选取消了它。相机、背景、辉光合成和预览图片都不会进入效果资产，载入也不会改动场景合成链。若需要光晕，可主动添加 Screen VFX；不加辉光时，原生发光材质也能显示。缩略图不代表高清效果验收或集成显卡帧率。

Arc Slash 和 Impact Burst 的缩略图均展示第 5 帧，不加辉光；Impact 使用与侧栏直接创建相同的接口和默认参数。高清三阶段检查见 [刀光记录](VISUAL_REVIEW.md) 和 [打击爆发记录](IMPACT_VISUAL_REVIEW.md)。充能到挥斩、命中的静帧检查及其限制见 [衔接记录](CHARGE_HANDOFF_REVIEW.md)。

从全新源码克隆重新生成：

```sh
blender -b --factory-startup --python-exit-code 1 --python tools/build_examples.py
```

脚本只接受未打开项目的全新后台进程，输出四套效果、共六个 `.blend`（含闪电质量文件） 到 `dist/examples/`，并生成带版本号的 examples ZIP；不会删除目录中其他文件。网格、节点、参数和嵌入预览均可重建。每次会产生新的内部编号，因此不保证 Blender 文件跨次构建的二进制完全相同。

0.22.3 尚未发布，整体艺术重设计由 [#89](https://github.com/mumu-lhl/blender-vfx-studio/issues/89) 跟踪。开发版可从成功 Actions 的 `blender-vfx-studio-extension` 附件取得独立 examples ZIP，或按上面的命令自行生成。当前仍有片状能量段、远景细流偏弱等问题；具体状态见 [Roadmap](../ROADMAP.md)。上述技术检查不代表实时播放、真实角色镜头或商业艺术验收，已下载的 0.22.2 保留旧造型。
