# 开发进度与后续计划

更新：2026-10-25（UTC）。目标是 Blender 5.2 LTS；当前仍是预览版，七类效果都有可用入口，但不代表各类功能已经完整。

近期重点已调整为视觉品质。v0.21.1 首先升级 Arc Slash 的造型、分层材质、运动节奏和高清预览；Impact Burst 与组合战斗检查也已完成首轮改进，当前继续打磨充能资产。非必要的复杂骨架扩展与跨平台 GUI 扩展暂缓。Ungroup All 和原有资产复用功能继续保留。

## 已可使用的功能

**M0：插件与开发基础。** 原生 VFX 侧栏、Extension 安装包、可重复构建、普通 Python 测试、真实 Blender 后台测试，以及隔离配置的安装/卸载检查。CI 校验官方 Blender 5.2.2 下载包，覆盖 Linux x64、Windows x64 和 macOS ARM（[#24](https://github.com/mumu-lhl/blender-vfx-studio/issues/24)）。

**M1：共享控制和 Mesh / Shader。** 每个效果拥有独立编号、控制器、网格、材质和节点。Start / Duration / Speed / Loop 使用原生驱动；支持跳帧、复制、安全删除和无插件播放。冲击波、能量环、弧形刀光及 Fresnel 护盾可调整形状、发光、流动和溶解（[#26](https://github.com/mumu-lhl/blender-vfx-studio/issues/26)、[#34](https://github.com/mumu-lhl/blender-vfx-studio/issues/34)）。

**M2：基础效果库。** Flipbook 支持静态图集和外部编号图片序列；Particle 支持同时出生的 Burst，以及独立出生时间和寿命的 Continuous Emitter；Screen 可主动添加辉光和闪光，并保留现有合成链（[#8](https://github.com/mumu-lhl/blender-vfx-studio/issues/8)、[#38](https://github.com/mumu-lhl/blender-vfx-studio/issues/38)、[#11](https://github.com/mumu-lhl/blender-vfx-studio/issues/11)、[#40](https://github.com/mumu-lhl/blender-vfx-studio/issues/40)、[#9](https://github.com/mumu-lhl/blender-vfx-studio/issues/9)）。

粒子最多使用 2048 个存活槽；连续发射面板会显示受限制后的实际发射率。两种粒子都在局部空间直接计算，不处理碰撞或历史受力；改变发射参数会重算当前状态。序列图片仍为外部文件，完整效果导出不负责序列打包。

**M3：轨迹、绑定、组合与复用。** Ribbon 采样对象原点或骨骼起点/末端，按原采样时间播放；修改源动画后需明确 Rebake（[#13](https://github.com/mumu-lhl/blender-vfx-studio/issues/13)、[#44](https://github.com/mumu-lhl/blender-vfx-studio/issues/44)）。对象/骨骼绑定用 Child Of 保持挂接瞬间姿态；不能安全保留动画或剪切姿态时拒绝解绑（[#15](https://github.com/mumu-lhl/blender-vfx-studio/issues/15)、[#45](https://github.com/mumu-lhl/blender-vfx-studio/issues/45)）。

2–32 个空间效果可以组合、分层调整时间、整体复制/删除，并用 Ungroup All 一次拆开全部层；拆分保留当前帧的姿态、时间和原生资源，暂不支持 Screen 或嵌套组合（[#19](https://github.com/mumu-lhl/blender-vfx-studio/issues/19)）。用户参数库提供命名、列表创建、重命名和文件删除；完整效果文件另存节点、动画、已采样路径和 Cloth 姿态，载入时分配新编号（[#17](https://github.com/mumu-lhl/blender-vfx-studio/issues/17)、[#36](https://github.com/mumu-lhl/blender-vfx-studio/issues/36)）。已接入 Blender 原生 Asset Browser 的安全载入；已支持选择静态图片嵌入预览，尚无自动效果渲染。

**M4：首个模拟效果。** Cloth Energy Sheet 使用原生布面求解，明确烘焙成保存在 .blend 中的形态键姿态。面板区分未烘焙、已烘焙和过期；改变物理输入不会自动覆盖旧结果（[#22](https://github.com/mumu-lhl/blender-vfx-studio/issues/22)）。仅已存姿态支持任意帧回放。当前源必须静态、有界，没有碰撞、外部力场、流体或烟雾；损坏源的复制会提前拒绝，不留下残缺实例（[#41](https://github.com/mumu-lhl/blender-vfx-studio/issues/41)）。

**M5：兼容性与稳定性仍在推进。** 后台功能已覆盖三个平台；Linux 已实际检查侧栏、文件选择器、Pose Mode 入口、用户库、Cloth 状态和撤销/重做。Windows/macOS 的真实窗口交互、更多骨架形式及不同 UI 缩放仍待检查，不能据此承诺正式版稳定性。具体范围见 [GUI 记录](docs/GUI_CHECKS.md)。

## 当前验证基线

v0.22.2 已通过 Linux、Windows、macOS 的后台测试、无插件重开、安装/卸载和 Ruff，并已发布。实际下载的三个 ZIP 均通过 SHA256；扩展与标签新克隆构建逐字节一致，实际 examples ZIP 通过无插件检查，衔接检查包与实际已读图及记录一致。

重开进程关闭脚本自动执行，检查驱动、节点、路径和烘焙姿态能独立播放。Cloth 和骨骼末端轨迹还会删除源后验证回放。
窗口检查、后台功能检查和渲染像素检查各有范围，不能互相替代。

图集、图片序列、合成、Burst、Emitter 和护盾有 CPU 像素检查。Continuous Emitter 的 Eevee 无插件像素检查也通过；组合场景、护盾、连续发射和骨骼端点对比预览可用 tools/ 下的脚本重建。刀尖对比的 Cycles CPU 与 Eevee 图像均已查看。CPU 求值开销和测量限制见 [性能记录](docs/PERFORMANCE.md)，尚无集成显卡上的视口帧率保证。

## 接下来的优先级

1. **视觉品质优先：充能首轮重设计已合并，Arc Slash 版本 3 已合并，正在处理 Impact Burst 的整体造型。** 检查真实效果的出现、峰值、衰减与连续抽帧，使用至少 960×540 的实图。重点是轮廓、主次、色彩、细节和节奏，不靠提高发光或预览合成。
2. #69 已按用户授权完成三个旧版战斗视频的隔帧检查。新造型继续检查充能、释放、命中、消散的衔接；旧视频的结论不自动适用于新生成器。
3. 保留现有三平台后台测试、安全删除、独立实例、无插件播放和安装检查。暂停非必要的复杂骨架扩展及 Windows/macOS GUI 测试扩展。
4. 更广的资产迁移和需要缓存的新模拟类型暂缓，不为它们推迟当前视觉交付。

完整历史及安装包见 [Releases](https://github.com/mumu-lhl/blender-vfx-studio/releases)；具体实现与限制见 [README](README.md)、[DESIGN](DESIGN.md) 和 [CONTEXT](CONTEXT.md)。发布标签会重新执行三平台检查、生成 CPU 预览，再上传 ZIP、SHA256SUMS 和图片。标签版本必须与 manifest 一致；直接上传曾遇到凭据权限问题，现由独立 GitHub Actions 发布任务完成（[#5](https://github.com/mumu-lhl/blender-vfx-studio/issues/5)）。

## 0.20.0：批量拆分组合

[#57](https://github.com/mumu-lhl/blender-vfx-studio/issues/57) 在组合面板的层列表上方增加 Ungroup All，一次解除全部成员的组合时间和父级，保留当前帧的世界姿态、时间值和原生资源。全组先检查再修改；任一成员存在不明确的变换/时间动画、约束或剪切时整组保持原样。用户数据仍引用旧控制器时保留它。

本地完整回归、14 个无插件重开进程、安装/卸载和 Ruff 已通过；新增绑定动画组合及多 view layer 检查后，14 项组合测试另通过。覆盖 16 层、子帧、手动节点、参数动画、外部引用、导入资产拆分后独立保存，以及真实 Undo/Redo。Linux 窗口已实际点击按钮拆分 16 层，再撤销和重做，原有 Cube 保留。[PR #58](https://github.com/mumu-lhl/blender-vfx-studio/pull/58) 已合并；三平台 CI、标签检查及发布完成，实际下载包也已复核。

拆分只保存操作时的状态，不把组合未来的动画或循环烘焙到成员；这项限制已在使用文档说明。历史版本的完整说明见 Releases。

## 0.21.1：Arc Slash 视觉改进

[#60](https://github.com/mumu-lhl/blender-vfx-studio/issues/60) 为新建刀光加入窄亮锋刃、渐变拉丝主体、低亮短残影、快速展开与减速挥斩，以及由内侧和尾部开始的侵蚀。
7 个新参数可在原生侧栏和关键帧中编辑；旧版资产和参数 JSON 仍保持旧版生成结果。预览直接使用创建出来的效果，不增加渲染专用发光层。

本地完整回归通过；实际查看了三阶段 Cycles PNG，并修正出现时平切口和衰减时过于完整的描线。Eevee 三阶段、浅背景、安装/卸载及实际示例包也已验证；保存后在无插件进程渲染峰值，所有像素通道与原图一致。三平台 CI 和软件渲染预览均通过，v0.21.1 已发布。实际下载包的 SHA256 通过，扩展 ZIP 与对应标签的全新克隆构建逐字节一致；九张发布高清图已核对，三阶段实图已直接查看。Impact Burst 的后续进展见下文。

v0.21.0 标签的三平台测试通过，但 Linux 缺少 EGL 动态库，Eevee 预览失败，因此没有发布包。[PR #64](https://github.com/mumu-lhl/blender-vfx-studio/pull/64) 已在 v0.21.1 补齐 Mesa 软件渲染依赖，并把 Eevee/浅背景预览加入 Linux PR 检查；修复后的 PR 和标签流程均通过。

## 0.22.0：Impact Burst 视觉改进

[#62](https://github.com/mumu-lhl/blender-vfx-studio/issues/62) 把同亮度圆环加圆粒改为白色短闪、渐变尖片、低亮侵蚀冲击波和延迟余烬。Create Mesh VFX 可直接创建完整四层组合；Burst 的 Shape / Stretch / Planar / Motion Ease 可编辑，旧版资产继续按版本 1 读取。

本地 152 项测试、15 个无插件重开进程、安装/卸载及 Ruff 已通过。实际查看 Cycles、软件 Eevee 和浅背景的三阶段 960×540 PNG；中心先爆发、冲击波随后消失、细小余烬最后散去。原生保存后的高清峰值在无插件进程重渲染，所有像素通道一致。实际 v0.21.1 入门库中的旧 Impact 已载入、保存参数和复制验证。[PR #66](https://github.com/mumu-lhl/blender-vfx-studio/pull/66) 已合并，三平台 CI 与发布任务通过，[v0.22.0](https://github.com/mumu-lhl/blender-vfx-studio/releases/tag/v0.22.0) 已发布。实际下载的两个 ZIP 均通过 SHA256；扩展 ZIP 与对应标签的全新克隆构建逐字节一致，实际 examples ZIP 通过无插件检查。九张发布高清图尺寸已核对，并直接查看三阶段 Cycles 与 Eevee 峰值。

浅背景上的微小余烬较弱，尚未检查角色实战镜头或集成显卡视口帧率；本轮不把这些写成已通过。检查细节见 [Impact 视觉记录](docs/IMPACT_VISUAL_REVIEW.md)。

## 镜头衔接检查

[#67](https://github.com/mumu-lhl/blender-vfx-studio/issues/67) 增加可重建的 36 帧武器/靶体预览场景，复用实际刀光和打击爆发，不加辉光。已生成完整暗背景序列和 24 fps 视频；实际查看了展开、命中、扩散及恢复阶段，以及浅背景的四个关键帧。初版武器未跟上正在展开的刀尖，已修正预览武器的原生动画。第 8 帧在无插件进程重渲染，所有像素通道一致。CI 配置包含暗/浅背景 PNG、可打开的原生场景和无插件渲染对比，运行结果见对应 PR。

这个简易场景检查空间衔接与遮挡；尚未观看连续视频或使用真实角色，不能据此认定完整战斗动作已验收。复现方法和发现见 [镜头记录](docs/COMBAT_VISUAL_REVIEW.md)。

## 0.22.1：远景可读性与隔帧检查

[#70](https://github.com/mumu-lhl/blender-vfx-studio/pull/70) 增厚真实 Impact 的短闪与主尖片、缩短短闪并提前侵蚀冲击波。随后 [#71](https://github.com/mumu-lhl/blender-vfx-studio/issues/71) 加入可编辑的主尖片亮暗面，保留白尖；发光强度、粒子数和几何预算不变，普通 Burst 与旧完整资产不重建。

[#69](https://github.com/mumu-lhl/blender-vfx-studio/issues/69) 已关闭。用户允许隔帧查看替代实时观看后，实际读取了三个 MP4 的第 1、3……35 帧，共 54 张高清解码图，检查完整的展开、命中、扩散与退场。按该方案，衔接与层次通过；远景亮背景的细残影和微余烬仍弱，实时播放掉帧、单帧级异常、真实角色和集成显卡性能未验证。精确视频哈希和范围见 [抽样记录](docs/COMBAT_SAMPLE_REVIEW.json) 与 [镜头说明](docs/COMBAT_VISUAL_REVIEW.md)。

[PR #73](https://github.com/mumu-lhl/blender-vfx-studio/pull/73) 已合并，三平台完整 156 项测试、15 个无插件重开进程、安装/卸载和高清预览检查通过。三个完整序列的命中帧在无插件新进程重渲染，与原 PNG 所有通道一致。离线播放页区分视频和静帧；视频记录绑定源序列，原生场景停在命中帧。

0.22.1 已通过标签流程发布，[#74](https://github.com/mumu-lhl/blender-vfx-studio/issues/74) 已关闭。实际下载的三个 ZIP 均通过 SHA256；扩展与标签新克隆构建逐字节一致，实际示例 ZIP 通过无插件检查，审阅 ZIP 中三个视频、54 张解码图和检查记录一致。发布文件以 [Releases](https://github.com/mumu-lhl/blender-vfx-studio/releases) 为准。

下一阶段继续提高可复用效果库的视觉品质，优先补强亮背景下的高对比表现与充能效果；复杂骨架和跨平台 GUI 扩展继续暂缓。

## 0.22.2 候选：充能末段淡出

[#76](https://github.com/mumu-lhl/blender-vfx-studio/issues/76) 修复新建入门库中 Energy Charge 的双环、球壳在生命末帧仍很亮的问题，并将其私有透明材质改为 Blended，减少软件 Eevee 低采样下的颗粒。时长、发光强度、层数与粒子预算不变，旧完整资产保持原样。

本地四项入门库测试、保存重开及实际旧资产兼容检查通过；Cycles 与 Eevee 的中段、末帧在无插件进程重渲染后逐像素一致。已读取五阶段高清图并对比旧末帧，CI 增加对应附件。[PR #77](https://github.com/mumu-lhl/blender-vfx-studio/pull/77) 已合并，三平台 CI 全部通过，实际候选示例 ZIP 也通过无插件检查。0.22.2 已发布并完成下载复核（[#81](https://github.com/mumu-lhl/blender-vfx-studio/issues/81)），后续聚能造型改进见 [充能记录](docs/CHARGE_VISUAL_REVIEW.md)。

## 充能的汇聚方向与视觉主次

[#79](https://github.com/mumu-lhl/blender-vfx-studio/issues/79) 改进实际入门资产：将外散粒子改为从外围向中心汇聚，并在中心停止；一个地面环改为原生驱动的倾斜轨道，另一个保留为低亮地面辅助层。球壳用深色主体到青色边缘的渐变，在前段逐渐显现，使浅背景也能看清主体。四层结构、LOW 质量、48 帧时长和粒子槽位预算保持不变，普通 Emitter 与旧完整资产不重建。

检查包含九个高清时刻、汇聚距离和任意帧重算；这不是实时播放或角色蓄力动作的完整验收。[PR #80](https://github.com/mumu-lhl/blender-vfx-studio/pull/80) 已合并并通过三平台完整 CI，改进已随 0.22.2 发布。具体证据与不足见 [充能记录](docs/CHARGE_VISUAL_REVIEW.md)。

## 充能到命中的衔接

[#82](https://github.com/mumu-lhl/blender-vfx-studio/issues/82) 复用真实效果与原战斗靶体，先充能，再挥斩和命中。实际读取 Cycles 暗背景 17 帧及 Eevee 亮背景释放阶段 6 帧，未见抽查帧中的焦点冲突或明显空档；两条件保存后的第 31、33 帧无插件重渲染逐像素一致，60 帧无 VFX 网格残留。[PR #84](https://github.com/mumu-lhl/blender-vfx-studio/pull/84) 已合并，实际检查包随 0.22.2 发布。该工具没有修改真实生成器，也未实时观看完整动画；范围和重建命令见 [衔接记录](docs/CHARGE_HANDOFF_REVIEW.md)。

## 0.22.3 候选：尖形充能微粒

[#85](https://github.com/mumu-lhl/blender-vfx-studio/issues/85) 改进实际新建充能资产的私有节点：以低面数尖形替代圆点，沿汇聚方向排列，暗尾向青色前端渐变。层数、发射率、生命周期与发光强度不增加，每粒几何减少；旧完整资产和普通 Emitter 保持原样。Size 仍可调整，完整效果保存这些节点，单层参数预设不保存节点编排。

本地六项入门库测试、实际示例 ZIP 无插件重开与三种渲染条件的原生像素对比通过；已读取出现、中段和末段高清图。[PR #86](https://github.com/mumu-lhl/blender-vfx-studio/pull/86) 已合并，三平台 CI 全部通过；实际下载的 0.22.2 旧资产及其副本在无插件重开后仍保留圆粒。0.22.3 尚未发布，具体观察和限制见 [充能记录](docs/CHARGE_VISUAL_REVIEW.md)。

## 蓄力环的显现节奏

[#88](https://github.com/mumu-lhl/blender-vfx-studio/issues/88) 对照实际渲染与节点，发现环的出生透明度为 1，而球壳有前段显现。已在真实新资产材质中加入两段弧的平滑闭合，地面环先完成、轨道后完成；几何和发光不增加。实际查看 Cycles / Eevee 暗、亮背景出现与峰值图，Cycles 峰值与改动前像素一致。局部回归、重定时和原生开场渲染检查跟随 PR 记录，0.22.3 仍未发布。

## 艺术设计重新评估：Energy Charge 优先

用户复核指出原有球壳、细环、月牙与星芒仍过于简单。此前技术检查不等于成熟游戏品质，整体差距见 [艺术评估](docs/ART_DIRECTION_REVIEW.md)。[#89](https://github.com/mumu-lhl/blender-vfx-studio/issues/89) 跟踪真实原生资产的整体提升；[#88](https://github.com/mumu-lhl/blender-vfx-studio/issues/88) 的局部环显现不足以解决整体问题，已被此项取代。充能首轮、刀光版本 3 与命中喷流改进已合并，当前优先重做 Energy Charge 的压缩表现，再继续刀光与命中。

[PR #90](https://github.com/mumu-lhl/blender-vfx-studio/pull/90) 三平台 CI 全部通过，已合并。隔帧复核发现核心仍有硬质叶片感，随后增加各瓣独立的卷动和局部鼓胀，流带改用明确色阶；这些修改发生在真实原生生成器。该轮为四层、最高约 826 顶点，后续压缩重做由 #99 取代。整体质量目标 #89 保持开放；历史看图范围见充能记录。

默认退场采用不透明表面的空间侵蚀，减少 Eevee 低采样颗粒；核心已增宽主瓣、降低辅助瓣与流带高度，保留压缩体积，避免纵向翻倍形成长叶片。正面亮白与深蓝外缘建立焦点，流带为分离收尖段；发光强度和几何数量不增加。实际看图又发现 Cycles 透明穿透上限产生的末段黑点，现让完全隐藏或塌缩后的核心停止输出几何，不改变用户场景设置。十项入门库测试通过；多阶段原生渲染、看图与 CI 状态在 #89 / PR #90 记录，整体艺术验收尚未结束。

释放阶段先将白核退为青蓝，再裂解与塌缩，减少挥斩开始后的焦点冲突。两引擎六阶段原生重开一致，衔接场景重开与实际示例 ZIP 检查通过。预览脚本已支持固定正面、侧面、俯视、远景和 AgX，记录相机与色彩管理；新选项的实图已读取，默认峰值像素保持一致。真实角色镜头、实际低配置视口与整体商业级品质仍未验收。

## Arc Slash 版本 3：轮廓与分段退场

[#91](https://github.com/mumu-lhl/blender-vfx-studio/issues/91) 修改真实刀光生成器，加入前端钩形、内侧缺口、深度弯曲与逐渐分离的残影；材质改为亮暗分面和分段消散。新增 Contour、Bank、Wake Spread，Low 仍为 594 顶点和一个显示对象，默认发光降低。版本 1/2 保留原结构，版本 2 重建的三阶段高清图与修改前逐像素一致。

11 项刀光测试、两引擎三阶段高清原生重开、实际示例 ZIP 检查通过；已读取 Cycles 三阶段及斜视角、Eevee 暗/浅灰背景共 22 张抽帧图，以及 AgX 近白背景远景三阶段。主体轮廓可辨，细残影与远景末段笔触仍弱。[PR #92](https://github.com/mumu-lhl/blender-vfx-studio/pull/92) 三平台 CI 全部成功后已合并，#91 已关闭。新充能与刀光的相邻帧衔接已实际查看，Cycles 暗背景及 Eevee 亮背景的 31/33 帧无插件重开逐通道一致，60 帧无残留。实时视频、真实角色与实际视口帧率没有验收，0.22.3 仍未发布。详见 [刀光记录](docs/VISUAL_REVIEW.md)。

## Impact Burst：喷流造型改进

[#93](https://github.com/mumu-lhl/blender-vfx-studio/issues/93) 已开始重做真实生成器。当前候选用七条带横截面的弯曲喷流代替整圈宽片，配紧凑短闪、分段压力弧和延迟余烬。几何节点计算独立弯曲、收缩和向外分离；侵蚀边缘先变黄再冷却。仍为四层，Low 约 888 顶点，预算上限 900；普通模块不变，实际 0.22.2 完整资产保持原样。

8 项局部 Blender 测试、几何/五阶段像素无插件重开、实际 0.22.2 完整资产兼容检查通过。已实际查看 Cycles 三阶段与正/侧面峰值、Eevee 暗背景六帧、近白远景三阶段、13 张视频解码图及相邻中段；两引擎三阶段高清重开逐通道一致。最新武器/靶标衔接的 31/32/33/37/45/60 帧也已读取，31/33 帧重开一致，60 帧清空。比前轮宽片更早露出靶标，但主喷流仍有粗硬感，近白远景对比仍弱。[PR #94](https://github.com/mumu-lhl/blender-vfx-studio/pull/94) 的三平台 CI 全部成功，已合并，#93 已关闭；后续 [#96](https://github.com/mumu-lhl/blender-vfx-studio/issues/96) 已开始处理浅背景轮廓。具体节点原因、参数和范围见 [检查记录](docs/IMPACT_DESIGN_CANDIDATE.md)。

#89 继续开放；尚未发布 0.22.3，也没有完成实时视频、真实角色或低配置视口验收。非必要的骨架与 GUI 扩展继续暂缓。

## 浅背景的主体轮廓

[#96](https://github.com/mumu-lhl/blender-vfx-studio/issues/96) 在真实主体材质中加入深橙边界，由原生表面法线和视线计算，不改变透明覆盖、几何或运动。Rim Contrast 与 Rim Width 可在材质中编辑，颜色跟随控制器；四层与约 888 顶点不变。

9 项局部测试与无插件重开通过，包含透明覆盖不变和颜色编辑验证；Cycles、近白远景三阶段高清重开一致。实际读取默认三阶段、正/侧面峰值、Eevee 浅灰/近白远景三阶段、暗背景中段及武器/靶标衔接。主边界比窄暗边试验更清楚，细余烬仍弱，整体艺术目标不据此关闭。详情见 [轮廓检查](docs/IMPACT_CONTRAST_REVIEW.md)。

## Energy Charge：重新建立压缩感

[#99](https://github.com/mumu-lhl/blender-vfx-studio/issues/99) 根据真实连段图及四个参考的实际观图，重做核心而非继续叠加发光。六条有空隙的内卷路径围绕小内核，后段三轴收紧；能量团向内加速并带动截面鼓起。仍为四层、12 个粒子槽、低质量最高 894 顶点，旧完整资产不重建。

11 项局部测试通过。实际看图发现线圈与圆珠感后，改用随移动能量团鼓起的扫掠薄片，并减少微粒绕行；两引擎多个阶段、侧面、俯视和 Eevee 浅背景隔帧图已读取。远景发现亮部融入背景，已在真实核心材质增加可编辑深蓝边界，相同远景重读后轮廓更完整，细点缀仍弱。最终 Cycles 六阶段、实际示例 ZIP 和完整 60 帧 Eevee 连段的原生检查通过，已读取全部 30 张视频解码图和 25–33 相邻帧。充能先交出亮点，刀光与命中随后接管；整体商业品质仍未验收。设计依据、预算和观看范围见 [压缩记录](docs/CHARGE_COMPRESSION_REVIEW.md) 和 [参考笔记](docs/REFERENCE_VISUAL_STUDY.md)。非必要骨架与 GUI 扩展继续暂缓，0.22.3 不发布。
## 连续连段检查与当前艺术重做

[#98](https://github.com/mumu-lhl/blender-vfx-studio/issues/98) 已实现完整 60 帧的连续生成、源代码/场景/图片校验、编码、隔帧解码与离线原生检查包。本地编码和无插件检查通过，实际读取了全部 30 张解码图；原生 31/33 帧匹配，60 帧清空。详情与未验收范围见 [连续检查记录](docs/CONTINUOUS_SKILL_REVIEW.md)。

用户新增四组参考后，继续优先重做压缩、汇聚与分层运动，而非准备发版。[#99](https://github.com/mumu-lhl/blender-vfx-studio/issues/99) 的本轮充能压缩重做已通过 [PR #101](https://github.com/mumu-lhl/blender-vfx-studio/pull/101) 合并，四项 CI 全部成功；当前继续改进刀光与粗硬命中喷流。0.22.3 暂不发标签，整体 #89 保持开放。

## Arc Slash：前端体积与独立残弧

[#102](https://github.com/mumu-lhl/blender-vfx-studio/issues/102) 已实现版本 4 候选：Head Bias 将宽度峰值向前移，三个不等缺口随时间变化，两条残弧分别使用延迟、较慢的局部年龄和不同宽度。实际看图发现衰减仍像细丝后，降低噪声频率并沿挥斩方向滚动，补入可编辑彩色流带。仍为 Low 594 顶点、一个显示对象和一个材质。

15 项局部测试、11 项预设测试和版本 3/4 原生重开通过；旧版三阶段高清重建与修改前像素一致。已读取多轮 Cycles 三阶段、Eevee 浅灰背景全部 11 张选帧和 AgX 近白远景三阶段。残弧后段偏弱，节点遮罩实验后进一步调整宽度和透明权重；最终三种条件的高清原生检查、实际示例 ZIP 和完整 60 帧 Eevee 连段检查通过。全部 30 张视频解码图及相邻衔接帧已读取；细尾、灰色薄片感和真实角色镜头仍需提升，整体艺术验收不据此完成。详见 [分层检查](docs/SLASH_LAYER_REVIEW.md)。
