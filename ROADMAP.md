# 开发进度与后续计划

更新：2026-10-23（Asia/Shanghai）。目标是 Blender 5.2 LTS；当前仍是预览版，七类效果都有可用入口，但不代表各类功能已经完整。

最近发布 v0.20.0，增加 Ungroup All，可一次拆分多层组合。Asset Browser 的安全载入、可选图片预览和三个入门效果资产继续可用；透明预览的边缘串色已在 v0.19.1 修复。

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

v0.20.0 已通过 Linux、Windows、macOS 的 143 项测试、14 个无插件重开进程、安装/卸载和 Ruff，并已发布。下载 ZIP 的 SHA256 校验通过；扩展 ZIP 与对应标签的全新克隆构建逐字节一致，实际发布的 examples ZIP 也通过无插件进程验证。
v0.19.0 和 v0.19.1 下载包的 SHA256 均通过；扩展 ZIP 与对应标签的全新克隆构建逐字节一致。两个版本实际发布的 examples ZIP 另在无插件进程验证，包含完整原生效果及嵌入预览。

重开进程关闭脚本自动执行，检查驱动、节点、路径和烘焙姿态能独立播放。Cloth 和骨骼末端轨迹还会删除源后验证回放。
窗口检查、后台功能检查和渲染像素检查各有范围，不能互相替代。

图集、图片序列、合成、Burst、Emitter 和护盾有 CPU 像素检查。Continuous Emitter 的 Eevee 无插件像素检查也通过；组合场景、护盾、连续发射和骨骼端点对比预览可用 tools/ 下的脚本重建。刀尖对比的 Cycles CPU 与 Eevee 图像均已查看。CPU 求值开销和测量限制见 [性能记录](docs/PERFORMANCE.md)，尚无集成显卡上的视口帧率保证。

## 接下来的优先级

1. 继续验证复杂组合的编辑、拆分和复用，特别是角色动画与手动参数编辑后的行为。
2. 明确旧资产的升级范围与失败处理。当前只迁移格式 1 的环形参数 JSON 到格式 2；未知实例或模块资产版本仍拒绝编辑，不能假装已支持通用迁移。
3. 补充更复杂骨架、不同 UI 缩放、Windows/macOS 窗口和 Eevee/Cycles 的视觉验证；修复能复现的问题，再扩展功能。
4. 按实际需求增加世界空间粒子历史、碰撞或其他模拟。此类效果需先明确缓存和烘焙规则，不把依赖上一帧的模拟伪装成可直接跳帧的公式效果。

完整历史及安装包见 [Releases](https://github.com/mumu-lhl/blender-vfx-studio/releases)；具体实现与限制见 [README](README.md)、[DESIGN](DESIGN.md) 和 [CONTEXT](CONTEXT.md)。发布标签会重新执行三平台检查、生成 CPU 预览，再上传 ZIP、SHA256SUMS 和图片。标签版本必须与 manifest 一致；直接上传曾遇到凭据权限问题，现由独立 GitHub Actions 发布任务完成（[#5](https://github.com/mumu-lhl/blender-vfx-studio/issues/5)）。

## 0.20.0：批量拆分组合

[#57](https://github.com/mumu-lhl/blender-vfx-studio/issues/57) 在组合面板的层列表上方增加 Ungroup All，一次解除全部成员的组合时间和父级，保留当前帧的世界姿态、时间值和原生资源。全组先检查再修改；任一成员存在不明确的变换/时间动画、约束或剪切时整组保持原样。用户数据仍引用旧控制器时保留它。

本地完整回归、14 个无插件重开进程、安装/卸载和 Ruff 已通过；新增绑定动画组合及多 view layer 检查后，14 项组合测试另通过。覆盖 16 层、子帧、手动节点、参数动画、外部引用、导入资产拆分后独立保存，以及真实 Undo/Redo。Linux 窗口已实际点击按钮拆分 16 层，再撤销和重做，原有 Cube 保留。[PR #58](https://github.com/mumu-lhl/blender-vfx-studio/pull/58) 已合并；三平台 CI、标签检查及发布完成，实际下载包也已复核。

拆分只保存操作时的状态，不把组合未来的动画或循环烘焙到成员；这项限制已在使用文档说明。历史版本的完整说明见 Releases。
