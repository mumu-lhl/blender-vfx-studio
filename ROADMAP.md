# 开发进度与后续计划

更新：2026-10-23（UTC）。目标是 Blender 5.2 LTS；当前仍是预览版，七类效果都有可用入口，但不代表各类功能已经完整。

近期重点已调整为视觉品质。v0.21.1 首先升级 Arc Slash 的造型、分层材质、运动节奏和高清预览；本轮继续升级 Impact Burst。非必要的复杂骨架扩展与跨平台 GUI 扩展暂缓。Ungroup All 和原有资产复用功能继续保留。

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

v0.22.0 已通过 Linux、Windows、macOS 的 152 项测试、15 个无插件重开进程、安装/卸载和 Ruff，并已发布。下载 ZIP 的 SHA256 校验通过；扩展 ZIP 与对应标签的全新克隆构建逐字节一致，实际发布的 examples ZIP 也通过无插件进程验证。

重开进程关闭脚本自动执行，检查驱动、节点、路径和烘焙姿态能独立播放。Cloth 和骨骼末端轨迹还会删除源后验证回放。
窗口检查、后台功能检查和渲染像素检查各有范围，不能互相替代。

图集、图片序列、合成、Burst、Emitter 和护盾有 CPU 像素检查。Continuous Emitter 的 Eevee 无插件像素检查也通过；组合场景、护盾、连续发射和骨骼端点对比预览可用 tools/ 下的脚本重建。刀尖对比的 Cycles CPU 与 Eevee 图像均已查看。CPU 求值开销和测量限制见 [性能记录](docs/PERFORMANCE.md)，尚无集成显卡上的视口帧率保证。

## 接下来的优先级

1. **视觉品质优先：Arc Slash 与 Impact Burst 完成首轮改进后，检查组合使用。** 验收真实效果的出现、峰值、衰减三阶段，使用至少 960×540 的实图，直接查看 PNG。重点是轮廓、主次、渐变、细节和节奏，不靠提高发光或预览合成。
2. 用短战斗镜头检查刀光与打击爆发的衔接、镜头距离和浅背景对比，优先修正实际画面问题，再考虑新增效果。
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

## 0.22.1 候选：远景可读性与播放证据

本轮优先推进 [#69](https://github.com/mumu-lhl/blender-vfx-studio/issues/69)，该 Issue 仍打开，连续播放观感未验收。当前工具只能读取 PNG，不能真正观看视频，不能以编码或逐帧检查代替播放批准。

Impact 的真实生成器增厚短闪与主尖片、缩短短闪并提前侵蚀冲击波，没有提高发光强度或增加层数。旧完整资产和粒子参数预设保持原值。预览新增 Eevee、双倍相机可见宽度和真正的亮背景；工具可生成两段完整 36 帧、24 fps 视频，以及六种条件的原生场景。已实际读取命中前后的连续帧和对比图；远景主体可辨，亮背景的细残影与微小余烬仍较弱。

已有 152 项回归、15 个无插件重开进程、安装/卸载、旧版实际资产与新版示例包检查通过；另新增两项编码预检，防止把不完整帧集误当完整视频。无插件重渲染的 Eevee 远景亮背景与 Cycles 近景峰值均保持全部像素通道一致。当前为未发布候选，CI 与后续播放结果见对应 PR 和 [镜头记录](docs/COMBAT_VISUAL_REVIEW.md)。
