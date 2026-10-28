# 图形界面检查

这份记录补充后台测试。后台可以验证数据和 Undo 栈，但不能证明面板能正常绘制、对话框可操作，或按钮文字能看清。

2026-10-22，在 Linux、Blender 5.2.2 和 1280×900 的 X11 虚拟显示中进行了以下检查：

- 打开 VFX 侧栏，点击 Create Mesh VFX，确认默认选项仍为 Shockwave；点击 OK 后生成效果，原场景 Cube 保留。
- 在 3D 视图按 Ctrl-Z、Ctrl-Shift-Z，确认效果分别消失和恢复。
- 打开用户库，保存参数预设，确认列表正常绘制并显示条目。
- 从侧栏创建 Cloth，确认显示 UNBAKED；点击烘焙并确认后，显示 BAKED，记录到 25 个姿态。
- 将 Vertex Mass 从 0.1 改为 0.2，确认状态变成 STALE，仍保留原来的 25 个姿态。

检查还发现预设列表把名称、模块编号和文件短编号平分宽度，默认名称只剩下几个字。现在名称使用约 78% 的行宽，模块名称移到选中项下方；空列表和不支持参数快照的效果不再提供无效的创建/保存按钮。主要按钮也补充了说明性提示。

另发现保存后列表可能仍显示旧内容，需要折叠面板才能看到新条目。现在刷新库时会主动通知所有 3D 视图重绘；已实际确认第二次同名保存后立即显示两个独立条目，无需折叠面板。新保存的条目会自动选中。

完整效果功能加入后，同一环境还实际检查了 Create Energy Shield 的质量对话框，以及 Save / Load Complete Effect 文件选择器。
导出后连续载入两次，状态记录显示三个不同实例编号；Ctrl-Z 移除最近载入的效果，Ctrl-Shift-Z 恢复相同编号及选中控制器。
取消载入不增加实例。重新保存已有文件时，原生选择器显示红色 Overwrite 按钮；确认后文件更新。
修改文件名后按 Enter 提交文本，再点击保存，已确认生成新文件。未发现这些面板或文件操作的 Python 异常。

同次检查还通过原生文件选择器保存/读取护盾 JSON，确认创建新实例；选择 `demo-atlas.png` 并使用 4×4 格子创建 Flipbook，侧栏显示正确图片和格数。
在 Pose Mode 选中静止单骨骼 Bone 后创建 Ribbon，面板保存 Armature / Bone 和 250 个采样点，创建后正常回到 Object Mode。
随后在绑定对话框搜索 Armature 和 Bone，原生 Child Of 面板显示目标及骨骼；Unbind 能移除该约束。这里只检查骨骼入口和对话框，未将静止采样当作运动轨迹的视觉验证。

图片序列入口也已检查：文件选择器显示 File Count=16，选择 `burst0000.png` 后创建 `flipbook.sequence`，
面板显示 16 个外部文件和范围 0–15。未选择图像时确认会报告需要编号首图，没有创建残缺对象，原 Cube 保留。

2026-10-23，同一 Linux 显示环境检查了 Continuous Emitter：点击创建按钮，质量对话框默认为 Low，确认后侧栏显示独立控制器、Effective rate=64 particles/s 和局部空间/寿命尾段说明，原 Cube 保留。
通过数值输入将 Rate 改为 10000，在默认 Lifetime=0.6 时，面板显示 Effective rate=3413 particles/s 和 2048 粒子预算提示；按钮及提示文字均可读，未出现面板绘制异常。
另外在后台使用 Eevee 重开已保存的发射器，不加载插件且关闭自动执行，验证有粒子的帧和尾段结束后的黑色像素；这项渲染检查不等同于窗口视口性能测试。

同日还用带父级动画和骨骼 Copy Rotation 约束的两骨骼场景，检查了骨骼末端入口：在 Pose Mode 激活 Blade，创建对话框勾选 Use Bone Tail，确认后返回 Object Mode，侧栏保留 Source、Bone=Blade 和已勾选状态。
取消侧栏勾选，再点击 Rebake 并确认，操作完成且参数仍可编辑，没有 Python 异常。路径位置和不改动骨架动画的检查由后台测试完成；Cycles CPU 与 Eevee 对比预览均已查看：固定起点没有扫过弧线，旋转末端会留下刀尖轨迹。

Asset Browser 安全载入也已在同一 Linux 窗口检查。测试库包含 Blue Shockwave、Orange Stream 和一个普通集合资产；库通过 Blender 原生设置添加，新导出名称及 VFX Studio 标签正常显示。
选中 Blue Shockwave 并连续点击 Load VFX with New ID 两次，得到两个不同实例编号；顶栏 Edit → Undo 移除最近一个，Redo 恢复同一编号。选择普通集合时，按钮报告不支持的完整效果，原有两个实例和 Cube 保留。
切到 Current File 选中已载入的集合时，载入按钮禁用，并提示使用场景中的 VFX Duplicate。这里验证了原生库选择和操作入口，没有验证自动缩略图生成；当前导出文件没有自动生成的预览图。

2026-10-23，完整效果的导出窗口增加预览图片选择后，已实际打开 Save Complete Effect，在 Preview Image (optional) 搜索并选择已加载的 Blade comparison PNG，再保存到独立的测试资产库。
窗口中的图片名称、2048 像素限制和视图变换说明可读。随后切到原生 Asset Browser，列表缩略图和右侧 Preview 均显示选定的刀尖对比图片；图片比例保持一致。
这里验证了用户选择图片、导出和浏览的流程，没有把嵌入现有图片描述为自动渲染效果预览。无插件进程中的像素持久化由后台测试覆盖。

入门库的三项实际生成资产也已在同一环境作为外部库检查：Asset Browser 分别显示 Arc Slash、Energy Charge 和 Impact Burst 的嵌入缩略图。
通过 Load VFX with New ID 分别载入三个模板，并连续载入两次 Energy Charge，记录到两个独立组合编号；原有 Cube 保留。后台另验证组合成员的依赖与时间关系，未将缩略图浏览当作视口帧率测试。

2026-10-23，Ungroup All 已在 Linux Blender 5.2.2 窗口检查。测试组合包含 16 个 Low 环形效果，在第 7.25 帧点击层列表上方的按钮后，16 个控制器一起脱离并选中，空组合控制器移除，原有 Cube 保留。
随后用 Ctrl-Z 恢复组合及成员关系，再用 Ctrl-Shift-Z 重新拆分；侧栏分别显示组合控制和独立层参数，没有逐层点击。后台测试另检查姿态、资源、时间、参数动画和无插件重开。

2026-10-28，Linux Blender 5.2.2、1600×1000 X11 虚拟显示、默认 UI 缩放下，实际检查了艺术控制：

- 打开 VFX 标签页，选中效果时 **Create / Load** 折叠；点击 **Motion** 可展开参数。颜色、刀光基础造型和充能 **Core Focus** 无需跨过全部创建按钮。
- 点击 Body 色块，原生颜色轮、RGB / HSV 与 Hex 控件正常显示。用颜色轮改为暖色后，控制器 RGB 值实际改变；点击插帧按钮后，记录到三个原生 `color_0/1/2` 通道。
- 选择测试火焰主层，点击 **Blue**，再展开 **Edit Heat Ramp**，实际看到五个色点变为蓝／青色。Heat Tint 保持白色；Height / Curl / Flow 入口可见。
- 在充能主层将 **Stored Core Size** 从 1.9 输入为 2.8，字段实际更新。核心、压缩与释放三项位于次级设置之前，保存完整效果与参数 JSON 的入口文字可读。
- 新建静态 Cube 后，通过侧栏打开 **Capture Dash Echoes**，输入 1–12 帧、Echo Count=5；对话框显示间距 2.75 帧，确认后出现五个层，源 Cube 保留。这里只验收操作流程，未把静态 Cube 当作残影动画品质验证。

窗口检查还发现捕获成本提示过长、组合复用提示和侧栏底部说明被截断，现用更短的句子分行。测试中的一次 F3 搜索没有找到操作，随后使用侧栏按钮完成；未出现面板绘制异常。这里没有检查其他 UI 缩放、Windows/macOS 窗口，也没有观看实时动画或测量视口 FPS。图像艺术判断另见 [艺术控制记录](ART_CONTROLS_REVIEW.md)。

需要继续检查的范围包括复杂动画骨架、长名称和不同 UI 缩放，以及 Windows/macOS 的实际窗口交互。当前结果不代表完整交互测试或正式版验收。

若要在自己的桌面上复查，运行：

```sh
blender --factory-startup --python tools/gui_session.py
```

脚本只用于新的未保存场景，会启用侧栏，并将预设隔离到 `work/gui/presets/`。`work/gui/state.json` 每秒记录当前效果和 Cloth 状态，方便对照操作结果；它不替用户点击按钮，也不是插件播放逻辑。
创建 `work/gui/stop` 可结束这次临时会话。此脚本不保存 Blender 用户偏好，也不会把测试预设写入真实用户库。

2026-10-28，同一 Linux 1600×1000、默认缩放的实际窗口检查 **Set Echo Tail**。在 VFX 侧栏点击按钮后，360 像素宽弹窗显示 Tail (Frames) 以及组／层 Speed 的含义，文字未截断。输入 30 后取消，组仍为 Duration=30、Tail=18；重新输入并确认，Duration=42、Tail=30，三姿态进场约为 1／7／13，原 User Pose Source 保留。窗口和 Xorg 均正常退出。只检查这组入口与取消／确认，不声称做了其他平台、缩放、Undo 或动画艺术验收。
