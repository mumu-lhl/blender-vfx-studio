# 开发进度与后续计划

更新：2026-10-26（UTC）。目标 Blender 5.2 LTS，优先 Eevee。最新发布版为 0.22.2；0.22.3 仍在开发，不发布标签。七类效果已有可用入口，但功能范围与艺术品质都还需要完善。

下一阶段先完成角色镜头的必要验证，再按 [#138](https://github.com/mumu-lhl/blender-vfx-studio/issues/138) 将完整库由三套扩充至八套。优先闪电、烟尘、风格化火焰、冲刺残影和魔法阵；保留高品质和可编辑性，暂停围绕旧三套效果的连续局部微调。复杂骨架、跨平台 GUI 和新的模拟类型继续暂缓。

## 已有的功能与边界

**M0：插件与开发基础已可用。** 原生侧栏、Extension 安装包、可重复构建、Python 与真实 Blender 后台测试、隔离配置的安装/卸载检查均已建立。CI 校验官方 Blender 5.2.2 下载包，覆盖 Linux x64、Windows x64 和 macOS ARM。

**M1：共享控制和 Mesh / Shader 已可用。** 效果拥有独立编号、控制器、网格、材质和节点。Start / Duration / Speed / Loop 使用原生驱动，支持跳帧、复制、安全删除和无插件播放。冲击波、能量环、弧形刀光和 Fresnel 护盾已有可编辑生成器；它们仍在持续打磨视觉表现。

**M2：基础效果库已可用。** Flipbook 支持静态图集与外部编号图片序列；Particle 支持同时出生的 Burst 和连续发射；Screen 可添加辉光与闪光，并保留用户合成链。粒子最多 2048 个存活槽，在局部空间直接计算，不处理碰撞或历史受力；修改发射参数会重算当前状态。外部序列图片暂不打包进完整效果文件。

**M3：轨迹、绑定、组合与复用已可用。** Ribbon 采样对象或骨骼起点/末端，保留原运动快慢；源动画修改后需明确 Rebake。Child Of 绑定保持挂接瞬间姿态；无法安全保留动画或剪切时拒绝解绑。2–32 个空间效果可组合、分层调整时间、整体复制/删除；Ungroup All 一次拆开所有成员，保留操作时的姿态、时间与原生资源，不烘焙组合未来动画。暂不支持 Screen 或嵌套组合。

用户参数库支持命名、列表创建、重命名和删除。完整 `.blend` 资产另存节点、动画、已采样路径与 Cloth 姿态，载入时分配新编号。原生 Asset Browser 已接入安全载入，保存资产时可嵌入静态预览；插件 UI 暂不自动渲染预览。

**M4：已实现首个有明确烘焙状态的模拟。** Cloth Energy Sheet 用原生布面求解，将姿态保存为 `.blend` 内的形态键；面板区分未烘焙、已烘焙和过期，修改物理输入不会覆盖旧结果。只有已存姿态支持任意帧回放。当前源需静态且有界，没有碰撞、外部力场、流体或烟雾；其他模拟类型尚未实现。

**M5：兼容性与稳定性持续推进。** 三平台后台功能、无插件重开和安装/卸载已有自动检查。Linux 实际窗口检查包括侧栏、文件选择器、Pose Mode、用户库、Cloth 状态、Undo/Redo 和 Ungroup All；Windows/macOS 的真实窗口交互、更多 UI 缩放仍未检查。具体范围见 [GUI 记录](docs/GUI_CHECKS.md)，不把后台检查当作窗口交互验收。

## 当前视觉开发

**真实角色镜头的必要验证已完成。** [#135 / PR #136](https://github.com/mumu-lhl/blender-vfx-studio/pull/136) 使用两名 CC0 KayKit 蒙皮角色与原生挥剑／受击动作，提供 96 帧、24 fps 场景。修正残影方向接入与末段充能衔接后，`d883fc5` 的六项 CI 全部通过；已下载校验最终 Actions 附件，读取全部 48 张视频隔帧图、远景／暗背景／反向机位及高清关键帧。无插件三帧像素一致，恢复阶段清空。软件 Eevee 实测记录了明显的求值和材质渲染成本；这不是视口帧率。充能焦点、刀光权重与命中结构仍未整体艺术验收。当前转向 #138 扩库，第四套闪电 [PR #144](https://github.com/mumu-lhl/blender-vfx-studio/pull/144) 已完成局部与 CI 实图检查，七项 CI 全部通过；#137 保留未验收原型。见 [镜头记录与实测](docs/CHARACTER_COMBAT_REVIEW.md)。

**Energy Charge：束流、材质流动与释放已重做。** [PR #117](https://github.com/mumu-lhl/blender-vfx-studio/pull/117) 将主体改为错开前沿的双束，减少辅助流，材质通道跟随能量团向内移动；内核积蓄后原位收束释放。四层、12 个粒子槽、Low 最高 894 顶点不变，旧完整资产不重建。18 项局部测试、四种高清重开、示例 ZIP 和五项 CI 通过，已实际读取完整连段全部 30 张视频隔帧图。远景主体仍细碎，整体 [#89](https://github.com/mumu-lhl/blender-vfx-studio/issues/89) 继续开放，见 [束流记录](docs/CHARGE_STREAM_REVIEW.md)。

**压力核改进已合并。** [PR #121](https://github.com/mumu-lhl/blender-vfx-studio/pull/121) 把平滑椭圆内核重新分为有间隙的三段蓝白束。18 项测试、四种高清重开、实际示例 ZIP 已通过，多视角、远景与 30 个 Eevee 阶段帧已读取。五项 CI 与完整连段通过，实际 Actions PNG 和全部 30 张视频解码图已读取。远景仍偏小，俯视下竖向释放较弱，未整体艺术验收，见 [内核记录](docs/CHARGE_FOCUS_REVIEW.md)。

**内核积蓄压缩已完成分项复核。** [#131 / PR #132](https://github.com/mumu-lhl/blender-vfx-studio/pull/132) 在已有三段内核上加入独立压缩，降低高度并扩展横截面，释放时解除压缩，保留原材质与外部路径。19 项局部检查、四种高清七帧原生比较、实际示例 ZIP 与新旧资产像素比较通过；30 个 Eevee 阶段图及完整连段的全部 30 张解码图已读取，五项 CI 全部通过，实际 CI PNG 也已复核。远景中心仍小，俯视释放较弱，见 [压缩记录](docs/CHARGE_TENSION_REVIEW.md)。

**地面进流已完成分项复核。** [#133 / PR #134](https://github.com/mumu-lhl/blender-vfx-studio/pull/134) 把五条短路径改为三条更平滑的上行进流，降低切段密度、收窄辅助层，并提供原生抬升控制。地面层仍为 90 顶点，整个蓄力最高 894 顶点。20 项局部检查、四种高清七帧原生比较、实际示例 ZIP、新旧资产像素与五项 CI 通过；30 个 Eevee 阶段图、实际 CI PNG 和完整连段全部 30 张视频解码图均已读取。仍有叶片感和远景弱细节，见 [地面进流记录](docs/CHARGE_GROUND_REVIEW.md)。

**Arc Slash：版本 5 的有色残影已复核。** [PR #119](https://github.com/mumu-lhl/blender-vfx-studio/pull/119) 保留版本 4 的主刀面，把灰色矩形片段改为保留本色、两端收尖的残弧；Afterimage 调整面积，旧版本保持透明度含义。Low 594 顶点、单显示对象不变。16 项刀光、11 项预设检查及五种高清重开、示例 ZIP 通过；实际 Low 资产也做了高清三阶段读取与原生像素比较。三组战斗视频全部 54 张隔帧图已读取。五项 CI 及完整连段通过，全部 30 张视频解码图已读取。当前保留硬笔触和远景细尾问题，见 [残影记录](docs/SLASH_WAKE_REVIEW.md)。

**Impact Burst：主体重做已合并。** [PR #105](https://github.com/mumu-lhl/blender-vfx-studio/pull/105) / [#104](https://github.com/mumu-lhl/blender-vfx-studio/issues/104) 将七条相似喷流重新分为三团卷曲主体、四条细喷射和两条辅助卷流，短闪改为紧凑球核，压力弧改为单个宽波峰；清理完全消散的透明几何，修正实际 Cycles 尾部黑片。Low 最高 824 顶点、四个显示对象、四个材质。四项 CI 成功，10 项局部测试、四种条件的高清原生重开、示例 ZIP 与完整 60 帧连段检查通过，全部 30 张视频隔帧图已读取。侧面仍偏实体，远景细层较弱。见 [主体记录](docs/IMPACT_PRESSURE_REVIEW.md)。

**断裂压力体积已完成分项复核。** [#124 / PR #126](https://github.com/mumu-lhl/blender-vfx-studio/pull/126) 用多瓣截面、贯穿厚度的破口和不同明暗替换实心卷管感，细喷射路径保持不变。Low 最高 860 顶点、四个显示对象。12 项局部检查、原生重开、四种高清条件、旧资产像素与示例 ZIP 通过；本地完整 Cycles 连段的全部 30 张解码图、CI 独立 Impact 视频的全部 13 张解码图已读取。接入 #129 后完整 Eevee 连段、原生重开和离线包通过，全部 30 张解码图已读取，五项 CI 全部通过。[#128 / PR #130](https://github.com/mumu-lhl/blender-vfx-studio/pull/130) 接着把压力弧改为隆起截面、不同宽窄和较慢的纹理行进，Low 顶点预算不变。14 项局部检查、五种高清原生重开、示例 ZIP、旧资产像素与五项 CI 通过；独立效果、完整连段和三组战斗视频的解码隔帧图均已读取。见 [压力弧记录](docs/IMPACT_WAVE_REVIEW.md)。见 [当前主体记录](docs/IMPACT_SURFACE_REVIEW.md)。

**细喷射改进已合并。** [PR #107](https://github.com/mumu-lhl/blender-vfx-studio/pull/107) / [#106](https://github.com/mumu-lhl/blender-vfx-studio/issues/106) 把细喷射的较宽头部向前移，增加独立原生节点宽度控制、彩色内芯和深色边界，不增加数量、发光强度或顶点预算。11 项局部测试与无插件重开通过，实际 Cycles / Eevee 近白远景对照中峰值主要笔触更清楚，最终四种条件的高清重开、实际示例 ZIP 和完整连段检查已通过，全部 30 张视频隔帧图已读取。详细记录随该 PR 保存。

[#69](https://github.com/mumu-lhl/blender-vfx-studio/issues/69) 已按用户授权的隔帧方法完成旧版三个视频检查；其结论不自动适用于新生成器。现在的工具支持生成完整 60 帧、24 fps、960×540 连段，绑定源码、场景与图像校验，并生成视频解码图和无插件离线检查包。见 [连续检查记录](docs/CONTINUOUS_SKILL_REVIEW.md)。该旧版检查没有实时播放或低配置视口帧率验收；新的真实角色镜头范围见 #135。

软件 Eevee 的完整连段在原生像素检查后退出崩溃，见 [#122](https://github.com/mumu-lhl/blender-vfx-studio/issues/122)。#123 / #127 已合并，失败时保留原始帧与崩溃文件，检查结束后主动释放临时场景。新压力体积曾在清理后复现崩溃，缓存对照显示默认首轮失败、关闭磁盘缓存十次正常。#129 已限制 CI 原生重开的 Mesa 磁盘缓存，功能提交的五项 CI 及新压力体积完整流程通过；临时诊断 #125 再次关闭且未合并。修正范围见 [退出检查记录](docs/EEVEE_EXIT_REVIEW.md)，不承诺所有驱动路径。

## 接下来的优先级

1. #135 的必要镜头验证已完成；继续将新资产放入这套角色镜头，保留具体的观看方式与艺术问题。
2. 推进 [闪电 #139](https://github.com/mumu-lhl/blender-vfx-studio/issues/139)、[烟尘 #142](https://github.com/mumu-lhl/blender-vfx-studio/issues/142)、[火焰 #141](https://github.com/mumu-lhl/blender-vfx-studio/issues/141)、[冲刺残影 #143](https://github.com/mumu-lhl/blender-vfx-studio/issues/143)、[魔法阵 #140](https://github.com/mumu-lhl/blender-vfx-studio/issues/140)。闪电 #144 的七项 CI、四种用途共六文件的示例包及实际图像检查已完成，完整库扩至四套。烟尘 #145、火焰 #146 正在实现和视觉验证，尚不计入数量。
3. 每套交付完整动画、实用参数、合理质量档、原生完整资产和 Asset Browser 预览，实际读取高清阶段图和动画样本。测量有／无特效成本，顶点数不代表性能。
4. #137 充能原型已保存在功能分支，21 项行为检查及原生重开通过，但造型仍偏平，未艺术验收，暂不合并。后续再按完整镜头决定是否采用其中的方向控制。


0.22.2 已通过发布后的 ZIP 校验、全新克隆构建和实际示例包检查。新版本需保留必要测试，并如实记录视觉范围与未解决问题；当前不因技术检查成功发布 0.22.3。历史发布、已关闭任务和详细验证记录分别见 [Releases](https://github.com/mumu-lhl/blender-vfx-studio/releases)、GitHub Issues 及各效果检查文档；使用和架构见 [README](README.md)、[DESIGN](DESIGN.md) 与 [CONTEXT](CONTEXT.md)。
