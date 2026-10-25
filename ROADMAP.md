# 开发进度与后续计划

更新：2026-10-25（UTC）。目标 Blender 5.2 LTS，优先 Eevee。最新发布版为 0.22.2；0.22.3 仍在开发，不发布标签。七类效果已有可用入口，但功能范围与艺术品质都还需要完善。

当前重点是适合二次元角色战斗动画的视觉品质。先做好充能、释放、命中与消散，再扩充效果库。复杂骨架、跨平台 GUI 和新的模拟类型暂缓。[艺术评估](docs/ART_DIRECTION_REVIEW.md) 记录当前差距，[参考笔记](docs/REFERENCE_VISUAL_STUDY.md) 记录四组作品的实际观图与拆解。

## 已有的功能与边界

**M0：插件与开发基础已可用。** 原生侧栏、Extension 安装包、可重复构建、Python 与真实 Blender 后台测试、隔离配置的安装/卸载检查均已建立。CI 校验官方 Blender 5.2.2 下载包，覆盖 Linux x64、Windows x64 和 macOS ARM。

**M1：共享控制和 Mesh / Shader 已可用。** 效果拥有独立编号、控制器、网格、材质和节点。Start / Duration / Speed / Loop 使用原生驱动，支持跳帧、复制、安全删除和无插件播放。冲击波、能量环、弧形刀光和 Fresnel 护盾已有可编辑生成器；它们仍在持续打磨视觉表现。

**M2：基础效果库已可用。** Flipbook 支持静态图集与外部编号图片序列；Particle 支持同时出生的 Burst 和连续发射；Screen 可添加辉光与闪光，并保留用户合成链。粒子最多 2048 个存活槽，在局部空间直接计算，不处理碰撞或历史受力；修改发射参数会重算当前状态。外部序列图片暂不打包进完整效果文件。

**M3：轨迹、绑定、组合与复用已可用。** Ribbon 采样对象或骨骼起点/末端，保留原运动快慢；源动画修改后需明确 Rebake。Child Of 绑定保持挂接瞬间姿态；无法安全保留动画或剪切时拒绝解绑。2–32 个空间效果可组合、分层调整时间、整体复制/删除；Ungroup All 一次拆开所有成员，保留操作时的姿态、时间与原生资源，不烘焙组合未来动画。暂不支持 Screen 或嵌套组合。

用户参数库支持命名、列表创建、重命名和删除。完整 `.blend` 资产另存节点、动画、已采样路径与 Cloth 姿态，载入时分配新编号。原生 Asset Browser 已接入安全载入，保存资产时可嵌入静态预览；插件 UI 暂不自动渲染预览。

**M4：已实现首个有明确烘焙状态的模拟。** Cloth Energy Sheet 用原生布面求解，将姿态保存为 `.blend` 内的形态键；面板区分未烘焙、已烘焙和过期，修改物理输入不会覆盖旧结果。只有已存姿态支持任意帧回放。当前源需静态且有界，没有碰撞、外部力场、流体或烟雾；其他模拟类型尚未实现。

**M5：兼容性与稳定性持续推进。** 三平台后台功能、无插件重开和安装/卸载已有自动检查。Linux 实际窗口检查包括侧栏、文件选择器、Pose Mode、用户库、Cloth 状态、Undo/Redo 和 Ungroup All；Windows/macOS 的真实窗口交互、更多 UI 缩放仍未检查。具体范围见 [GUI 记录](docs/GUI_CHECKS.md)，不把后台检查当作窗口交互验收。

## 当前视觉开发

**Energy Charge：压缩重做已合并。** [PR #101](https://github.com/mumu-lhl/blender-vfx-studio/pull/101) 将球壳与细环改为有空隙的内卷路径、小内核、移动能量团及汇聚粒子，后段三轴收紧，浅背景增加深蓝轮廓。四项 CI 成功；已读取完整连段的 30 张视频隔帧图，并完成高清与示例资产的无插件检查。Low 最高 894 顶点，仍有薄片感和远景细流不足，整体目标 [#89](https://github.com/mumu-lhl/blender-vfx-studio/issues/89) 保持开放。见 [压缩记录](docs/CHARGE_COMPRESSION_REVIEW.md)。

**Arc Slash：版本 4 已合并。** [PR #103](https://github.com/mumu-lhl/blender-vfx-studio/pull/103) 把宽度峰值向前移，增加不等缺口、独立残弧年龄与低频彩色流带。仍为 Low 594 顶点、一个显示对象；旧版 1/2/3 保留。四项 CI 成功，实际读取多背景、远景和完整连段抽帧，原生重开与旧版重建检查通过。后段残影仍有灰色薄片感，细尾偏弱。见 [刀光记录](docs/SLASH_LAYER_REVIEW.md)。

**Impact Burst：主体重做待 CI 及合并。** [PR #105](https://github.com/mumu-lhl/blender-vfx-studio/pull/105) / [#104](https://github.com/mumu-lhl/blender-vfx-studio/issues/104) 将七条相似喷流重新分为三团卷曲主体、四条细喷射和两条辅助卷流，短闪改为紧凑球核，压力弧改为单个宽波峰；清理完全消散的透明几何，修正实际 Cycles 尾部黑片。Low 最高 824 顶点、四个显示对象、四个材质。10 项局部测试、四种条件的高清原生重开、示例 ZIP 与完整 60 帧连段检查通过，全部 30 张视频隔帧图已读取。侧面仍偏实体，远景细层较弱。见 [主体记录](docs/IMPACT_PRESSURE_REVIEW.md)。

**细喷射改进已在继续。** [PR #107](https://github.com/mumu-lhl/blender-vfx-studio/pull/107) / [#106](https://github.com/mumu-lhl/blender-vfx-studio/issues/106) 把细喷射的较宽头部向前移，增加独立原生节点宽度控制、彩色内芯和深色边界，不增加数量、发光强度或顶点预算。11 项局部测试与无插件重开通过，实际 Cycles / Eevee 近白远景对照中峰值主要笔触更清楚，最终连续复核仍在进行。详细记录随该 PR 保存。

[#69](https://github.com/mumu-lhl/blender-vfx-studio/issues/69) 已按用户授权的隔帧方法完成旧版三个视频检查；其结论不自动适用于新生成器。现在的工具支持生成完整 60 帧、24 fps、960×540 连段，绑定源码、场景与图像校验，并生成视频解码图和无插件离线检查包。见 [连续检查记录](docs/CONTINUOUS_SKILL_REVIEW.md)。没有实时播放、真实角色镜头或低配置视口帧率验收。

## 接下来的优先级

1. 完成 PR #105 / #107 的最终复核与 CI，保留明暗主次和旧资产兼容；继续解决主体实体感、远景细层与残影薄片感。
2. 回到 Energy Charge，强化不同视角下的汇聚、压缩和释放关系，再继续打磨刀光残影。每轮修改真实生成器，比较同镜头多阶段实图，不能以测试或发光代替艺术判断。
3. 在已有绑定能力上验证真实角色、遮挡和镜头变化；实际设备的视口性能另行测量。保持三平台后台、安全删除、独立实例、无插件播放与安装检查。
4. 当前视觉问题解决后再扩展高级模拟、资产迁移和非必要交互功能。

0.22.2 已通过发布后的 ZIP 校验、全新克隆构建和实际示例包检查。新版本需保留必要测试，并如实记录视觉范围与未解决问题；当前不因技术检查成功发布 0.22.3。历史发布、已关闭任务和详细验证记录分别见 [Releases](https://github.com/mumu-lhl/blender-vfx-studio/releases)、GitHub Issues 及各效果检查文档；使用和架构见 [README](README.md)、[DESIGN](DESIGN.md) 与 [CONTEXT](CONTEXT.md)。
