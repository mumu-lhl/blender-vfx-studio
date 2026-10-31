# 原生效果入门库

**main 包含 8 种完整效果、18 个资产文件。** Energy Charge、Arc Slash、Impact Burst 使用 Low；其余五套默认 Medium，`quality/` 目录另提供各自的 Low 和 High。质量文件属于同一种效果。

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

中心是带蓝色流带的白热焦点。蓄力时亮区扩大并向内收紧，释放时沿本地 Z 轴拉伸，随后交给较暗的碎片消散。主进流把能量带向中心，外围短流和粒子作为辅助；整套效果由四层构成。

粒子层的 **Spawn Radius** 控制出生距离，正的 **Velocity** 越大，抵达中心越快；抵达后停止，不穿过中心向外飞。粒子在控制器局部空间运动，移动整体也会移动已出生粒子，不保留角色走过的世界轨迹。

选择 **Charge • Compressed Core**，侧栏的 **Core Focus** 集中常用控制：

| 侧栏控制 | 作用 |
| --- | --- |
| **Stored Core Size** | 蓄满时内部能量团的相对大小，不扩大外围进流 |
| **Compression** | 积蓄时将内核向内收紧；0 关闭，有效范围 0–0.85 |
| **Release Stretch** | 释放时沿局部 Z 轴拉伸内核，不拉伸外围进流 |
| **Intake Weight (0–1)** | 改变核心层进流的粗细；0 隐藏进流，保留内核 |
| **Advanced Shape → Initial Core Size / Release Pinch** | 初始内核大小与释放时收腰；一般不必先改这两项 |

外层 **Converging Vortex** 和地面 **Ground Intake** 的 **Intake → Intake Weight** 分别调整这两层的透明权重；0 隐藏该层。它们不改变内核，也不控制独立粒子层。核心层通过进流截面的粗细调整视觉权重；外层和地面层通过透明度调整。

**组合的 Scale** 改变整套效果；核心层的 **Radius** 改变该层的内核与主进流；**Stored Core Size** 只改变内部积蓄，不是另一套整体尺寸。其他局部造型留在对应层的 Geometry Nodes，白色阈值位于核心材质：

| 控制 | 作用 |
| --- | --- |
| Main Intake Guide Width / Auxiliary Guide Width / Auxiliary Packet Width | 主体连接、辅助连接与辅助头部宽度 |
| Nucleus Compression | 积蓄时将内核向内收紧，0 关闭 |
| Nucleus Seed Size / Nucleus Stored Size | 初始与蓄满尺寸 |
| Release Pinch / Release Stretch | 释放时的形变 |
| Nucleus White Threshold | 越高，核心白色区域越小 |
| Spiral Turns / Intake Vertical Reach | 外层路径的绕行角度与起始高度 |
| Ground Intake Lift | 地面三条进流的抬升高度，默认 0.8 配合该层 Z=-0.8 |

使用 **Save Complete Effect** 保存这些形状和节点控制；参数 JSON 不包含 Intake Weight 等私有节点数值。角色镜头、明暗背景与实际观看范围见 [充能焦点检查](CHARGE_PLASMA_REVIEW.md)。

释放沿控制器的局部 **+Z** 方向前送。挂到武器或施法点时，将这个方向朝向能量要去的位置；可以给控制器旋转插关键帧，让积蓄转为沿剑刃或法术方向释放。

## Arc Slash

这是单层程序化刀光，与侧栏创建使用同一生成器，资产时长为 18 帧。

1. 选择 **Clean** 获得平整连续的基础刀光，或 **Stylized** 使用钩形、分面与破碎残弧。
2. 在 **Shape / Motion** 调整弧度、宽度、展开速度和残弧。**Depth Bend=0** 关闭深度弯折，**Contour=0** 关闭额外几何轮廓扰动；需要保留不规则轮廓时，**Hook / Inner Notches** 可分别调整前端钩形与几何内缘。
3. 用 **Body / Blade** 原生颜色选择器编辑主体和锋刃；主体颜色也用于残弧。右侧插帧按钮可给颜色插入关键帧。
4. 要手动保持连续轮廓，关闭 **Surface Cuts、Noise Erosion、Dissolve**，并将 **Fragment Release** 设为 0；此时 **Fade** 控制连续淡出。

风格按钮只改参数，不重建节点；尺寸、配色和整体时间保持不变。各控制的区别见 [刀光编辑](USAGE.md#编辑刀光)。实际图像和检查限制见 [艺术控制审查](ART_CONTROLS_REVIEW.md)。

放进角色动作后，先按实际武器设置 **Radius**，再用 **Arc** 限制刀光跟随的挥动范围、用 **Width** 保留角色轮廓。贴着剑刃的斩击可将 **Expansion** 设为 0；宽大的独立预览并不适合直接套入每个近身镜头。三维折叠会随带宽收尖，**Bank=0** 仍保持平面。

## Impact Burst

主体使用三帧白热短闪、三片翻卷的断裂压力面、四条细喷射、两条卷流及三段隆起压力弧，依次退场。压力面集中在接触附近，细喷射承担较长的方向线；短闪保留明亮中心、有色边缘和较弱的尖线。它与侧栏创建使用同一生成器，各层颜色与强度可分别调整。

选择 **Impact • Main Shards**，在 **Impact Shape** 调整主体与细喷射；选择 **Shockwave** 调整压力弧。**Advanced Shape** 保留较少使用的材质控制。

| 控制 | 作用 |
| --- | --- |
| **Body Curl** | 压力体截面的翻卷强度；0 关闭截面翻卷，中心路径仍保持弯曲 |
| **Fine Jet Width** | 只改细喷射的粗细，保留压力体和辅助卷流 |
| **Wave Height** | 压力弧的隆起高度，随该层 Width 成比例变化 |
| **Advanced → Early Body Breakup** | 主压力体出现初期的断裂程度，不改变细喷射 |
| **Advanced → Support Tone (0–1)** | 辅助压力体的着色明度；0 为黑色 |

**组合 Scale** 改整套大小，主层 **Size** 改该层整体尺寸，**Planar=1** 将主层压到局部平面。各层时间、颜色和发光可分开调整，**Ungroup All** 一次拆开全部层。使用 **Save Complete Effect** 保存节点控制；参数 JSON 只保存通用参数。

需要让压力面贴合被击表面时，可在主层 Geometry Nodes 中调整 **Pressure Surface Alignment → Rotation**；它只改变压力面方向，保留细喷射与卷流路径。此节点编辑需要 **Save Complete Effect** 保存。

近身使用时先检查压力弧是否盖过接触点，再调整该层 **Width / Expansion**。压力面仍偏薄，远景细层较弱；实际角色与隔帧范围见 [命中焦点检查](IMPACT_FOCUS_REVIEW.md)。

## Lightning Strike

主干先落地，再做两次逐渐减弱的复击，第一峰值在 Start+2 左右。地表分叉电弧随每次放电重新展开，在间歇清空；接触短闪与飞散火花承担第一击后的短暂反馈。

选择 **Lightning • Contact Corona**，用 **Radius / Expansion** 调整地表范围，**Width** 调整电弧粗细，**Dissolve** 裁去末端；**Width=0** 或 **Dissolve=1** 关闭该层。脚部遮挡和远景第三次放电仍较弱，见 [角色与时序检查](LIGHTNING_CONTACT_REVIEW.md)。

**Radius / Width / Strength** 调整分支横向范围、线宽与光量，**Noise Scale / Dissolve** 调整细扰动和侵蚀。选择主干层，在侧栏 **Bolt Shape → Bolt Length / Branch Reach** 直接调整高度和分支伸展。**Radius** 改变整层横向范围，**Branch Reach** 从各分叉的连接处伸缩，不改变主干高度。放电仍采用默认一次主击与两次复击。

已查看高清角色阶段图、全部隔帧样本与无插件重开。远景细枝和接触火花仍弱；范围与成本见 [闪电记录](LIGHTNING_REVIEW.md)。

## Dust Impact

不等大的云团先横向铺开，再抬升并变薄。**它不发光，需要场景灯光。** 原生 Volume Cube 把空间分成小格，几何节点直接计算每格当前帧的密度；这不是流体模拟，不需要历史缓存或外部 VDB 文件。Solid 模式只显示编辑域边界。

**Width / Expansion** 调整云团大小与铺开距离，**Noise Scale / Dissolve / Fade** 调整细节、密度侵蚀与消散。选择主层，在侧栏 **Shape / Motion / Material** 中使用 **Dust Rise Height / Dust Roll Speed / Dust Density** 调整抬升、纹理上卷与光学密度。接触时两侧体积先压低铺开，再抬升翻滚。地面薄雾层的 **Fade** 单独控制它的透明消散；它是较弱的辅助层，不替代主体体积。

三档改变密度网格分辨率、密度团和碎屑数量，体积计算有明显 CPU 成本。已实际查看高清图、全部隔帧样本、三档比较及 Cycles 预览；修复后的矩形伪影未再出现。检查范围、代价和限制见 [烟尘记录](DUST_REVIEW.md)。

## Stylized Fire

内焰较窄、较长，集中在主体附近；根部以上的宽窄和色带随 Flow Speed 上移。外焰主要提供橙红轮廓，较亮热区帮助辨认内部变化。实际角色图与当前限制见[下部热流检查](FIRE_ROOTED_REVIEW.md)。

主火舌从共同下部错相伸长、分叉，沿内部冷缝形成不同的热流层次，并产生上升余烬。主焰在 48 帧内点燃、维持并断燃，退场先切断底部、留下上部火丝；余烬晚四帧结束，完整资产为 52 帧。

**Width / Noise Scale / Strength / Dissolve / Fade** 控制宽度、流动色带、光量和退场。选择主焰层，在侧栏 **Shape / Motion** 使用 **Fire Height / Fire Flow Speed / Fire Curl** 调整高度、上卷节奏与火舌形变。

**Fire Flow Speed=0** 停止主焰几何与材质的流动；余烬仍由独立粒子层播放。

换色时：

1. 选择 **Fire • Sculpted Tongues**，点击 **Heat Palette → Orange / Blue / Green**。按钮直接修改主焰原生色带，并将乘色 **Heat Tint** 归为白色，不重建节点或改变几何。
2. 需要自定热芯和边缘颜色时，展开 **Edit Heat Ramp**，修改五个色点。Heat Tint 适合整体乘色，单独用它不容易把橙火变成蓝火。
3. 余烬是独立层，用该层的颜色选择器调整。最后使用 **Save Complete Effect** 保存色带和手动节点；参数 JSON 不包含这些数据。

需要进一步调整分叉时，可在主焰 Geometry Nodes 中编辑 **Fork Spread**；材质中的 **Flow Seam Contrast** 调整内部冷缝。两者都是原生节点控制，使用完整效果保存。

三档改变截面细节和余烬生成率。实际高清、明暗／远景、完整燃烧抽帧与成本见 [分叉检查](FIRE_FORK_REVIEW.md)。底部亮团仍偏圆，局部边缘偏薄，远景细余烬较弱，尚未观看实时播放。

## Character Dash Echoes

残影保存不同位置与姿态的角色网格，依次出现并淡去。内置示例使用固定版本 [KayKit CC0 角色](../assets/character-review/README.md)，无需原角色或骨架参与播放。代码许可仍为 GPL-3.0-or-later。

捕获自己的角色：

1. 在 Object Mode 选中 Mesh 或 Armature，点击 **Capture Dash Echoes**。
2. 指定 **First / Last Frame** 和 **Echo Count**。工具把 2–32 个姿态均匀分布在首尾之间，必要时求值子帧；例如 1–12 帧、五个残影会采样 1、3.75、6.5、9.25、12 帧，无需调整跨度来满足整除条件。
3. 设置 **Echo Tail**，决定每个姿态存活时间。创建后选择组合控制器，点击 **Set Echo Tail** 可单独改变尾部，保留已有姿态和进场间隔，不必重新捕获。
4. 用组合的 **Duration / Speed** 缩放整体节奏，或选择某层调整透明度、颜色、边缘和侵蚀。Set Echo Tail 的数值在组及层 Speed 之前计算；调整后组 Duration 会同步变化。

捕获保留源角色求值后的网格细节；**Echo Count 控制数量，不降低每个姿态的画质**。内置 Low / Medium / High 示例使用两／三／四个姿态；捕获自己的角色时直接选择数量，更多半透明姿态会增加开销。

若时间比例、Local Speed 或组 Duration 已有动画，或时间驱动被手工改写，请直接编辑这些时间通道，Set Echo Tail 会保留现有编排并拒绝覆盖。完整效果保存姿态与这些调整；[实际检查](DASH_SAMPLING_REVIEW.md#捕获后的尾部编辑) 包含观看范围。

捕获会求值修改器和形态键，保留原网格、材质、骨架及动画，随后恢复原帧和子帧；不保留运行时源引用。**源动画改变后需要重新捕获。** 参数 JSON 不含姿态网格，请保存完整效果。

残影的透明填充先淡，较暗的有色轮廓稍后淡出；**Opacity** 控制整体透明度，**Fade** 控制消退，**Dissolve=1** 隐藏整层。透明叠层有实际渲染开销，旧姿态在远景仍偏弱。冲刺、腾空与落地烟尘的实际镜头及观看边界见 [衔接检查](DASH_LANDING_REVIEW.md)。

## Calligraphic Magic Circle

主印逐笔形成，符文带反向转动；释放时立体符记升起，地面图案先退去。笔画由本项目生成，不依赖字体、贴图或缓存。

**Radius / Width** 调整尺寸和笔画，颜色与 **Strength** 可分层编辑，**Noise Scale / Dissolve / Fade** 调整侵蚀和消散。侧栏 **Motion → Sigil Spin** 控制各层周期转角；释放层还可用 **Sigil Lift** 调整移动距离，默认向上。三档改变曲线采样密度，保持同一图案和时序。

要让符记汇聚到角色前方，展开 **Magic • Release**，选中它的网格子对象，在 Geometry Nodes 中调整 **Release Direction** 和 **Release Gather**。例如方向 `(1, 0, 0)`、Gather `1`，配合 **Sigil Lift** 向本地 X 方向收拢移动；Gather `0` 保留分散排列，零方向停止平移。使用 **Save Complete Effect** 保存这些节点编辑。

细符文在远景仍偏弱，默认图案偏线描风格。默认形成与升起见 [魔法阵记录](MAGIC_REVIEW.md)，角色接火焰的空间衔接见 [施法检查](SPELL_TRANSFER_REVIEW.md)。

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
