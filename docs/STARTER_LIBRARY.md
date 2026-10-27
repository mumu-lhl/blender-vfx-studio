# 原生效果入门库

**main 包含 8 种完整效果、18 个资产文件。** 原三套使用 Low；新增五套默认 Medium，`quality/` 目录另提供各自的 Low 和 High。质量文件属于同一种效果。

项目尚未正式分发。使用成功 [开发构建](https://github.com/mumu-lhl/blender-vfx-studio/actions/workflows/ci.yml) 的 `blender-vfx-studio-extension` 附件，或从源码构建。实际画面见 [角色镜头图集](LIBRARY_GALLERY.md)。

## 载入和开始编辑

examples ZIP 是资产库，**不是插件安装包**。

1. 下载并解压与插件同版本的 examples ZIP。
2. 在 **Preferences → File Paths → Asset Libraries** 添加解压后的文件夹。
3. 启用插件，在 Asset Browser 选中效果，点击右侧 **Load VFX with New ID**。
4. 选择组合控制器，调整 **Start / Duration / Speed / Loop** 和整体位置；选择某层则编辑该层。

也可以在 VFX 侧栏点击 **Load Complete Effect**，直接选择 `.blend`。插件按钮会分配独立实例编号；普通拖放或 Append 不会，重复载入可能发生编号冲突。

所有示例从第 1 帧开始、默认不循环。载入保留原时间和位置，**不会自动放到当前帧或 3D Cursor**。保存后不加载插件也能播放、渲染和编辑原生节点；继续使用插件侧栏操作则需要启用插件。

| 效果 | 完整时长 | 适合用途 | 分层或主要结构 |
| --- | ---: | --- | --- |
| Energy Charge | 48 帧 | 汇聚、蓄力与释放 | 主体、外层进流、地面进流、汇聚粒子 |
| Arc Slash | 18 帧 | 程序化挥砍 | 主刀面、残弧与笔触共用一个显示对象 |
| Impact Burst | 24 帧 | 命中爆发 | 短闪、断裂主体、压力弧、余烬 |
| Lightning Strike | 18 帧 | 落雷和复击 | 分支电弧、接触闪光、火花、地面余波 |
| Dust Impact | 32 帧 | 落地、踩踏 | 体积云团、地面薄尘、碎屑 |
| Stylized Fire | 52 帧 | 点燃、燃烧与断燃 | 三团外焰、两团热芯、连续余烬 |
| Character Dash Echoes | 30 帧 | 冲刺姿态残影 | 默认三个独立的角色姿态 |
| Calligraphic Magic Circle | 72 帧 | 施法与符记释放 | 主印、反转符文带、升起符记 |

## Energy Charge

主体使用错开前沿的双束、辅助进流、汇入中心的短弯流和弯曲粒子。外围逐步收紧，中心积蓄为有间隙的蓝白束，再原位收束释放，由四层构成。

粒子层的 **Spawn Radius** 控制出生距离，正的 **Velocity** 越大，抵达中心越快；抵达后停止，不穿过中心向外飞。粒子在控制器局部空间运动，移动整体也会移动已出生粒子，不保留角色走过的世界轨迹。

私有造型控制位于对应层的 Geometry Nodes，白色阈值位于核心材质：

| 控制 | 作用 |
| --- | --- |
| Main Intake Guide Width / Auxiliary Guide Width / Auxiliary Packet Width | 主体连接、辅助连接与辅助头部宽度 |
| Nucleus Compression | 积蓄时压低内核并扩展截面，0 关闭 |
| Nucleus Seed Size / Nucleus Stored Size | 初始与蓄满尺寸 |
| Release Pinch / Release Stretch | 释放时的形变 |
| Nucleus White Threshold | 越高，核心白色区域越小 |
| Spiral Turns / Intake Vertical Reach | 外层路径的绕行角度与起始高度 |
| Ground Intake Lift | 地面三条进流的抬升高度，默认 0.8 配合该层 Z=-0.8 |

远景主体仍偏小、细碎。具体对象、节点和观看范围见 [进流](CHARGE_INTAKE_REVIEW.md)、[外层路径](CHARGE_FLOW_REVIEW.md)、[束流](CHARGE_STREAM_REVIEW.md)、[内核](CHARGE_FOCUS_REVIEW.md) 与 [压缩](CHARGE_TENSION_REVIEW.md)。

## Arc Slash

这是单层紫色程序化刀光，不需要角色动画或采样路径。它与侧栏创建使用同一生成器，资产时长设为 18 帧。

- **Arc / Width / Spin**：弧度、宽度和旋转。
- **Attack / Motion Ease**：展开与减速节奏。
- **Core Width / Afterimage / Streaks / Breakup**：锋刃、残影、笔触与侵蚀。
- **Head Bias / Contour / Bank / Wake Spread**：前端偏重、轮廓、深度与残影分离。

主刀面与两端收尖的残弧分别展开和退场，残影保留紫色；**Afterimage** 控制残弧的可见面积。硬笔触和远景细尾仍待改善，见 [实际残影检查](SLASH_WAKE_REVIEW.md)。

## Impact Burst

主体使用紧凑闪核、三团明暗不同的断裂主体、四条细喷射、两条卷流及三段隆起压力弧，依次退场。它与侧栏创建使用同一生成器。

**Size** 调整主层整体尺寸；主层 Geometry Nodes 的 **Fine Ejection Width** 单独调整细喷射宽度。各层时间与颜色可分开编辑，**Ungroup All** 一次拆开全部层。

当前侧面仍偏实体，远景细层较弱，见 [主体](IMPACT_SURFACE_REVIEW.md)、[细喷射](IMPACT_FINE_REVIEW.md) 与 [压力弧](IMPACT_WAVE_REVIEW.md)。

## Lightning Strike

主干先落地，再做两次逐渐减弱的复击，第一峰值在 Start+2 左右。接触闪光短促，火花和地面余波随后退去。

**Radius / Width / Strength** 调整分支横向范围、线宽与光量，**Noise Scale / Dissolve** 调整细扰动和侵蚀。主层 Geometry Nodes 的 **Bolt Length / Branch Reach** 调整高度和分支伸展。

已查看高清角色阶段图、全部隔帧样本与无插件重开。远景细枝和接触火花仍弱；范围与成本见 [闪电记录](LIGHTNING_REVIEW.md)。

## Dust Impact

不等大的云团先横向铺开，再抬升并变薄。**它不发光，需要场景灯光。** 原生 Volume Cube 把空间分成小格，几何节点直接计算每格当前帧的密度；这不是流体模拟，不需要历史缓存或外部 VDB 文件。Solid 模式只显示编辑域边界。

**Width / Expansion** 调整云团大小与铺开距离，**Noise Scale / Dissolve / Fade** 调整细节、密度侵蚀与消散。主层 **Object Properties → Custom Properties** 的 **Dust Rise Height / Dust Roll Speed / Dust Density** 控制抬升、纹理上卷与光学密度。

三档改变密度网格分辨率、密度团和碎屑数量，体积计算有明显 CPU 成本。已实际查看高清图、全部隔帧样本、三档比较及 Cycles 预览；修复后的矩形伪影未再出现。检查范围、代价和限制见 [烟尘记录](DUST_REVIEW.md)。

## Stylized Fire

三团不等高的外焰围绕较小的热芯，持续产生上升余烬。主焰在 48 帧内点燃、维持并断燃，余烬晚四帧结束，完整资产为 52 帧。

**Width / Noise Scale / Strength / Dissolve / Fade** 控制宽度、流动色带、光量和退场。主层自定义属性 **Fire Height / Fire Flow Speed / Fire Curl** 调整高度、上卷节奏与火舌形变。颜色参数乘到红橙黄色带上；编辑材质的 **Painted Red Orange Yellow** 色带可改变热色顺序。

三档改变截面细节和余烬生成率。已实际查看高清、明暗与远景、全部隔帧样本和三档预览；中段大火面与远景细余烬仍需改善。见 [火焰记录](FIRE_REVIEW.md)。

## Character Dash Echoes

残影保存不同位置与姿态的角色网格，依次出现并淡去。内置示例使用固定版本 [KayKit CC0 角色](../assets/character-review/README.md)，无需原角色或骨架参与播放。代码许可仍为 GPL-3.0-or-later。

捕获自己的角色：

1. 在 Object Mode 选中 Mesh 或 Armature，点击 **Capture Dash Echoes**。
2. 指定 **First / Last Frame** 和 **Echo Count**。工具把 2–32 个姿态均匀分布在首尾之间，必要时求值子帧；例如 1–12 帧、五个残影会采样 1、3.75、6.5、9.25、12 帧，无需调整跨度来满足整除条件。
3. 设置 **Echo Tail**，决定每个姿态存活时间。创建后编辑组合时间和位置，或各层的透明度、颜色、边缘与侵蚀。

捕获保留源角色求值后的网格细节；**Echo Count 控制数量，不降低每个姿态的画质**。内置 Low / Medium / High 示例使用两／三／四个姿态；捕获自己的角色时直接选择数量，更多半透明姿态会增加开销。

捕获会求值修改器和形态键，保留原网格、材质、骨架及动画，随后恢复原帧和子帧；不保留运行时源引用。**源动画改变后需要重新捕获。** 参数 JSON 不含姿态网格，请保存完整效果。

透明叠层渲染较贵，旧姿态在远景偏淡；测试镜头末段由跑步切回站姿，衔接仍硬。已查看全部隔帧样本、明暗与远景、三档预览，删除源后的原生播放也通过。见 [残影记录](DASH_REVIEW.md)。

## Calligraphic Magic Circle

主印逐笔形成，符文带反向转动；释放时立体符记升起，地面图案先退去。笔画由本项目生成，不依赖字体、贴图或缓存。

**Radius / Width** 调整尺寸和笔画，颜色与 **Strength** 可分层编辑，**Noise Scale / Dissolve / Fade** 调整侵蚀和消散。各层自定义属性 **Sigil Spin** 控制周期转角，释放层的 **Sigil Lift** 调整升起高度。三档改变曲线采样密度，保持同一图案和时序。

已查看高清、明暗与远景、全部隔帧样本和三档实际嵌入预览。细符文远景偏弱，画面仍偏干净的线描风格，见 [魔法阵记录](MAGIC_REVIEW.md)。

## 保存、质量与观看范围

**使用 Save Complete Effect 保存完整造型。** `.blend` 保留私有网格、节点、关键帧、姿态和多层关系；单层参数 JSON 只保存参数，会重建对应基础模块。例如充能粒子只存 JSON 会得到普通 Emitter，私有的汇聚运动和尖形不会保留。

场景中的副本使用 **VFX Duplicate**，删除使用 **VFX Delete**。八套资产均保留原生可编辑数据，不需要外部贴图、角色或模拟缓存。质量选择服务于镜头效果：可以为更好的轮廓、细节或轨迹增加复杂度，不要求统一低成本，也不用顶点数代表性能。

Asset Browser 缩略图是 **256×256 的 Cycles CPU 渲染**，相机、背景、合成和预览图片不进入效果资产。刀光和命中均展示第 5 帧，不加辉光。需要光晕时可以主动添加 Screen VFX；载入资产不改场景合成链。

**缩略图、测试通过和视频生成均不等于艺术验收。** 各记录区分实际读取的高清图、隔帧动画与技术检查；当前未观看实时播放，不承诺商业成片品质或设备视口帧率。整体艺术工作由 [#89](https://github.com/mumu-lhl/blender-vfx-studio/issues/89) 跟踪，当前问题见 [路线图](../ROADMAP.md)。

## 从全新克隆重建

在未打开项目的全新后台进程运行：

```sh
blender -b --factory-startup --python-exit-code 1 --python tools/build_examples.py
```

脚本在 `dist/examples/` 输出 **8 套、18 个 `.blend`** 和带版本号的 examples ZIP，不删除目录中的其他文件。网格、节点、参数与嵌入预览均由脚本重建；每次分配新实例编号，因此不保证 `.blend` 文件跨次构建的二进制完全相同。
