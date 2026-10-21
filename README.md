# Blender VFX Studio

面向二次元 3D 动画的 Blender 原生 VFX 插件。目标 Blender **5.2 LTS**，优先 Eevee，兼容 Cycles。

当前预览版 **0.2.0** 已实现：

- **Shockwave / Energy Ring**：可编辑的程序化网格、UV 流动、噪声溶解、软边透明与发光。
- 开始帧、持续时间、速度、循环；半径、宽度、扩张、颜色及着色器参数可关键帧化。
- 原生 VFX 侧栏创建、独立复制、安全删除；32 / 64 / 128 段质量选项。
- 不使用 Python 每帧处理器；保存后无需插件也能播放。
- 用户参数预设 JSON 保存与加载，严格版本和数值校验；载入为独立实例。

这只是首个纵向切片。Particle、Trail、Flipbook、Simulation、Screen 和可浏览的预设库尚未实现；详见 [ROADMAP.md](ROADMAP.md)。

## 安装

在 [Actions](https://github.com/mumu-lhl/blender-vfx-studio/actions/workflows/ci.yml) 最新成功构建中下载 `blender-vfx-studio-extension` artifact，解压得到 `blender-vfx-studio-0.2.0.zip`。
当前云端无法向 GitHub Releases 上传附件（uploads.github.com 返回 401）；也可从源码构建。
Blender 5.2 → Edit → Preferences → Get Extensions → 右上角菜单 → Install from Disk，选择 ZIP 并启用。
源码也可直接构建：

```sh
python tools/build.py
```

安装 `dist/` 中生成的 ZIP；不要安装 GitHub 的源码 ZIP。

## 使用

1. 在 3D 视图按 **N**，打开 **VFX** 标签页，点击 **Create VFX**。
2. 选择 Shockwave 或 Energy Ring，以及质量级别。特效在 3D Cursor 处创建，以当前帧为开始帧。
3. 切换 **Material Preview** 或 **Rendered** 查看材质。Eevee 用户需要自有环境/灯光以查看场景；发光环本身不需要灯光。
4. 在 VFX 面板调整时间、网格和 Shader 参数。右键参数 → Insert Keyframe，可使用 Blender 原生动画编辑器。
5. 移动/旋转/缩放 Controller 控制整个效果。选择 Controller 或 Layer 均可编辑参数。
6. 使用 **Duplicate** 创建独立效果；使用 **Delete** 删除。支持 Blender Undo。

Energy Ring 默认一个 48 帧周期；启用 Loop 可持续显示。循环会重置到出生状态，Shockwave 不保证边界连续。
Emission 不自动添加屏幕辉光；如需辉光，请在自己的 Compositor 中配置 Glare。

选择 Layer 可直接编辑 Geometry Nodes、材质节点和基础网格。参数调整不会重建这些节点。
请保留命名属性 `vfx_inner` 和节点输入驱动目标。质量只在创建时生效。

## 保存与复用预设

选择效果后点击 **Save Preset**，保存 `.json`；点击 **Load Preset** 可在当前 3D Cursor 和当前帧创建独立实例。
保存当前帧的参数值、质量和名称，不包含原始开始帧、UUID、关键帧、变换、图片或手动编辑的节点拓扑。
节点拓扑与动画的完整复用请保存 `.blend` 并使用 Blender 原生 Append。

格式有独立的 format/module/asset 版本，严格校验缺失字段、未知字段、非有限数值和参数范围，文件最大 64 KiB。
当前只支持预设格式 1 和 ring 资产版本 1；未支持的版本会明确报错，不会修改场景。

## 安全与限制

- 使用 VFX **Duplicate**；Shift-D 会复制实例 UUID，插件会提示身份歧义。
- 若外部对象共享了生成的 Mesh、Material 或 Node Group，Delete 会拒绝操作，先解除共享。
- 删除保留用户子对象、外来材质和非空集合；自建约束/驱动器若引用 Controller，需自行处理这些外部依赖。
- 保存的 `.blend` 可在未安装插件、禁用自动执行时播放；重新创作需要启用插件。
- 本版仅支持实例 schema 1 和预设格式 1；旧版迁移尚未需要实现，未知版本会拒绝导入。
- 自动化已验证 Blender 5.2.2 Linux。其他操作系统和完整交互 UI 操作仍需人工验证。

## 开发与验证

需要 Python 3.11+ 和 Blender 5.2.2（可通过 `BLENDER_BIN` 指定路径）；无第三方运行依赖。

```sh
python tools/test.py
python tools/test_install.py
blender -b --factory-startup --python-exit-code 1 --python tools/preview.py
blender -b --factory-startup --python-exit-code 1 --python tools/preview.py -- --engine BLENDER_EEVEE --scale 25
```

测试在 CPU 后台验证真实 bpy、实例隔离、参数/时间、复制动画、删除安全、保存重开与插件安装生命周期。
预览场景及 PNG 写入忽略的 `work/`。CI 构建的 ZIP 在 Actions artifacts 中提供。
使用 Ruff 进行静态检查和格式校验；安装版本见 CI 配置。

架构见 [DESIGN.md](DESIGN.md)，领域约定见 [CONTEXT.md](CONTEXT.md)。
许可证：**GPL-3.0-or-later**。
