# 开发进度与后续计划

更新：2026-10-23（Asia/Shanghai）。目标是 Blender 5.2 LTS；当前仍是预览版，七类效果都有可用入口，但不代表各类功能已经完整。

最近完成连续粒子发射、骨骼末端拖尾、安全解绑，以及原生 Asset Browser 的独立实例载入。v0.15.0、v0.16.0、v0.17.0 均已通过三平台发布检查并发布；下载 ZIP 的 SHA256 校验通过，且分别与全新克隆构建逐字节一致。

## 已可使用的功能

**M0：插件与开发基础。** 原生 VFX 侧栏、Extension 安装包、可重复构建、普通 Python 测试、真实 Blender 后台测试，以及隔离配置的安装/卸载检查。CI 校验官方 Blender 5.2.2 下载包，覆盖 Linux x64、Windows x64 和 macOS ARM（[#24](https://github.com/mumu-lhl/blender-vfx-studio/issues/24)）。

**M1：共享控制和 Mesh / Shader。** 每个效果拥有独立编号、控制器、网格、材质和节点。Start / Duration / Speed / Loop 使用原生驱动；支持跳帧、复制、安全删除和无插件播放。冲击波、能量环、弧形刀光及 Fresnel 护盾可调整形状、发光、流动和溶解（[#26](https://github.com/mumu-lhl/blender-vfx-studio/issues/26)、[#34](https://github.com/mumu-lhl/blender-vfx-studio/issues/34)）。

**M2：基础效果库。** Flipbook 支持静态图集和外部编号图片序列；Particle 支持同时出生的 Burst，以及独立出生时间和寿命的 Continuous Emitter；Screen 可主动添加辉光和闪光，并保留现有合成链（[#8](https://github.com/mumu-lhl/blender-vfx-studio/issues/8)、[#38](https://github.com/mumu-lhl/blender-vfx-studio/issues/38)、[#11](https://github.com/mumu-lhl/blender-vfx-studio/issues/11)、[#40](https://github.com/mumu-lhl/blender-vfx-studio/issues/40)、[#9](https://github.com/mumu-lhl/blender-vfx-studio/issues/9)）。

粒子最多使用 2048 个存活槽；连续发射面板会显示受限制后的实际发射率。两种粒子都在局部空间直接计算，不处理碰撞或历史受力；改变发射参数会重算当前状态。序列图片仍为外部文件，完整效果导出不负责序列打包。

**M3：轨迹、绑定、组合与复用。** Ribbon 采样对象原点或骨骼起点/末端，按原采样时间播放；修改源动画后需明确 Rebake（[#13](https://github.com/mumu-lhl/blender-vfx-studio/issues/13)、[#44](https://github.com/mumu-lhl/blender-vfx-studio/issues/44)）。对象/骨骼绑定用 Child Of 保持挂接瞬间姿态；不能安全保留动画或剪切姿态时拒绝解绑（[#15](https://github.com/mumu-lhl/blender-vfx-studio/issues/15)、[#45](https://github.com/mumu-lhl/blender-vfx-studio/issues/45)）。

2–32 个空间效果可以组合、分层调整时间并整体复制/删除，暂不支持 Screen 或嵌套组合（[#19](https://github.com/mumu-lhl/blender-vfx-studio/issues/19)）。用户参数库提供命名、列表创建、重命名和文件删除；完整效果文件另存节点、动画、已采样路径和 Cloth 姿态，载入时分配新编号（[#17](https://github.com/mumu-lhl/blender-vfx-studio/issues/17)、[#36](https://github.com/mumu-lhl/blender-vfx-studio/issues/36)）。已接入 Blender 原生 Asset Browser 的安全载入；已支持选择静态图片嵌入预览，尚无自动效果渲染。

**M4：首个模拟效果。** Cloth Energy Sheet 使用原生布面求解，明确烘焙成保存在 .blend 中的形态键姿态。面板区分未烘焙、已烘焙和过期；改变物理输入不会自动覆盖旧结果（[#22](https://github.com/mumu-lhl/blender-vfx-studio/issues/22)）。仅已存姿态支持任意帧回放。当前源必须静态、有界，没有碰撞、外部力场、流体或烟雾；损坏源的复制会提前拒绝，不留下残缺实例（[#41](https://github.com/mumu-lhl/blender-vfx-studio/issues/41)）。

**M5：兼容性与稳定性仍在推进。** 后台功能已覆盖三个平台；Linux 已实际检查侧栏、文件选择器、Pose Mode 入口、用户库、Cloth 状态和撤销/重做。Windows/macOS 的真实窗口交互、更多骨架形式及不同 UI 缩放仍待检查，不能据此承诺正式版稳定性。具体范围见 [GUI 记录](docs/GUI_CHECKS.md)。

## 当前验证基线

v0.17.0 在三个平台通过 125 项测试、13 个无插件重开进程、安装/卸载和 Ruff。重开进程不加载插件，并关闭脚本自动执行；检查原生驱动、节点和已存路径/姿态能独立工作。Cloth 和骨骼末端路径还会删除源后再验证回放。

新增的 5 项测试覆盖受约束、带父级动画和非均匀缩放的骨架、子帧采样、端点切换、旧文件重新采样、复制、完整资产，以及剪切姿态解绑时保留原约束。未改动骨架的 Action 或约束。Linux 窗口检查了端点复选框及 Rebake 确认。

图集、图片序列、合成、Burst、Emitter 和护盾有 CPU 像素检查。Continuous Emitter 的 Eevee 无插件像素检查也通过；组合场景、护盾、连续发射和骨骼端点对比预览可用 tools/ 下的脚本重建。刀尖对比的 Cycles CPU 与 Eevee 图像均已查看。CPU 求值开销和测量限制见 [性能记录](docs/PERFORMANCE.md)，尚无集成显卡上的视口帧率保证。

## 接下来的优先级

1. 补充带原生资产预览的常用效果示例，继续验证不同图片与显示设置；不另建文件索引或资产浏览器。
2. 明确旧资产的升级范围与失败处理。当前只迁移格式 1 的环形参数 JSON 到格式 2；未知实例或模块资产版本仍拒绝编辑，不能假装已支持通用迁移。
3. 补充更复杂骨架、不同 UI 缩放、Windows/macOS 窗口和 Eevee/Cycles 的视觉验证；修复能复现的问题，再扩展功能。
4. 按实际需求增加世界空间粒子历史、碰撞或其他模拟。此类效果需先明确缓存和烘焙规则，不把依赖上一帧的模拟伪装成可直接跳帧的公式效果。

完整历史及安装包见 [Releases](https://github.com/mumu-lhl/blender-vfx-studio/releases)；具体实现与限制见 [README](README.md)、[DESIGN](DESIGN.md) 和 [CONTEXT](CONTEXT.md)。发布标签会重新执行三平台检查、生成 CPU 预览，再上传 ZIP、SHA256SUMS 和图片。标签版本必须与 manifest 一致；直接上传曾遇到凭据权限问题，现由独立 GitHub Actions 发布任务完成（[#5](https://github.com/mumu-lhl/blender-vfx-studio/issues/5)）。

## 最近完成的资产复用改进

[#48](https://github.com/mumu-lhl/blender-vfx-studio/issues/48) 增加 Asset Browser 的 Load VFX with New ID，按选中集合载入并分配新编号；新导出集合使用可读名称和 VFX Studio 标签，旧导出文件仍可读取。
非视口载入和 Undo/Redo 针对性检查已通过。Linux 窗口已验证重复载入、独立编号、Edit 菜单撤销/重做、普通集合拒绝，以及 Current File 按钮禁用。
新增编辑模式保护；三平台 125 项测试、13 个无插件重开进程、安装/卸载与 Ruff 已通过，新增 5 项资产测试和 1 项 Undo/Redo 测试。v0.17.0 已发布并完成下载/全新克隆构建校验。此项不包含自动预览图生成、在线库或 Current File 资产的直接载入。

## 正在验证的 0.18.0

[#50](https://github.com/mumu-lhl/blender-vfx-studio/issues/50) 已实现可选静态图片预览：导出窗口选择已加载图片，缩小后直接存入原生资产，保留源数据和场景设置。
本地完整 129 项测试、13 个无插件重开进程及 Ruff 通过；新增 4 项资产测试，覆盖像素、透明度、尺寸、缺失/无效输入、文件保护和写入失败清理。既有资产重开进程另检查嵌入预览可独立读取，不增加外部图片依赖。
Linux 实际窗口已确认导出图片选择、可读的说明，以及 Asset Browser 列表和侧栏的原生预览显示。本地安装/卸载和三平台 CI 均已通过，v0.18.0 已发布；下载及干净构建校验另行记录。

## 正在验证的 0.19.0

[#53](https://github.com/mumu-lhl/blender-vfx-studio/issues/53) 增加入门原生资产库：Energy Charge、Impact Burst 和 Arc Slash，可由提交的脚本重新生成并单独打包。
三张 Cycles CPU 缩略图已查看，实际生成的 ZIP 已在无插件进程中验证。相机、背景、合成节点和预览源图片不进入资产；模板默认 Low，不循环，保留从第 1 帧开始的时间。
新增生成器保护、重复载入和依赖隔离检查，并增加第 14 个无插件重开进程。完整套件、三平台 CI、发布及实际窗口库导入仍待完成。
