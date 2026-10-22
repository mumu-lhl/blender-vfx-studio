# 开发进度与后续计划

更新：2026-10-22（Asia/Shanghai）。以下区分已实现代码、已验证范围和尚未完成的工作；早期预览版不等同于正式稳定版。

## M0：插件与开发基础——已实现

插件可以按 Blender 5.2 Extension 格式构建、安装、启用和卸载，提供原生 VFX 侧栏。安装 ZIP 可以从源码重复构建。CI 使用官方 Blender 5.2.2，并校验下载文件的 SHA256。

测试包括普通 Python 测试、真实 Blender CPU 后台测试、无插件保存重开和隔离用户配置的安装测试。架构说明、领域约定、开发规则和首项架构决策记录均已建立。

## M1：共享控制与首个效果——已可使用

已有统一控制器、实例 UUID、参数范围、版本检查、开始帧/时长/速度/循环，以及 Mesh + Shader 环形效果。冲击波和能量环支持参数关键帧、独立复制、安全删除和创建时质量选择。参数 JSON 可以保存、读取并创建新实例。

已有空间效果多层组合，后续继续完善完整资产复用。将来修改实例保存结构前，要先补充明确的逐版本迁移和旧数据测试，不能只改变版本号。首次开发及参数预设分别见 [#1](https://github.com/mumu-lhl/blender-vfx-studio/issues/1)、[#3](https://github.com/mumu-lhl/blender-vfx-studio/issues/3)。

## M2：基础效果库——已覆盖主要类型，继续扩展

- Flipbook：静态图集选帧、尺寸、透明度、独立复制和图片保留；JSON 支持图片相对路径及旧格式转换（[#2](https://github.com/mumu-lhl/blender-vfx-studio/issues/2)）。
- Particle：最多 2048 个粒子的可重复随机爆发、重力弹道和实例化；尚无连续发射或碰撞（[#11](https://github.com/mumu-lhl/blender-vfx-studio/issues/11)）。
- Screen：主动添加辉光和时间闪光，保留现有合成链，支持叠加、复制和安全移除（[#9](https://github.com/mumu-lhl/blender-vfx-studio/issues/9)）。

下一步继续扩展 Mesh / Shader 预设，改善刀光、冲击波等常用效果的外观。已实现独立的 Arc Slash 程序化弧形刀光：弧度、生命周期旋转、收尖、溶解和预设复用（[#26](https://github.com/mumu-lhl/blender-vfx-studio/issues/26)）；Trail 继续用于动画采样路径。

## M3：轨迹、绑定、组合与复用——进行中

已完成对象原点/骨骼起点采样的 Ribbon Trail，按采样时间插值播放，提供宽度、尾长和明确的重新采样操作（[#13](https://github.com/mumu-lhl/blender-vfx-studio/issues/13)）。轨迹最多 2048 点，暂用 `.blend` 复用，不支持 JSON 路径资产、自动朝向相机或扭转模拟。

已完成对象/骨骼绑定界面，使用 Child Of 约束保持挂接瞬间的世界姿态，并在无法安全保留动画时拒绝解绑（[#15](https://github.com/mumu-lhl/blender-vfx-studio/issues/15)）。

用户参数预设库已实现命名保存、列表创建、重命名、文件删除和损坏文件报告，并完成本地及 CI 验证（[#17](https://github.com/mumu-lhl/blender-vfx-studio/issues/17)、[PR #18](https://github.com/mumu-lhl/blender-vfx-studio/pull/18)）。它保存参数，不代替完整 Blender 资产库。

已实现多个空间效果的统一控制、分层时间设置和整体复制/删除（[#19](https://github.com/mumu-lhl/blender-vfx-studio/issues/19)）。下一步完善路径、节点和资源的整体复用，并开始第一个原生模拟效果。

## M4：模拟和缓存——首个布面效果已实现

Cloth Energy Sheet 使用原生布面求解，显式烘焙为保存在 `.blend` 的形态键动画，并显示未烘焙、已烘焙和过期状态。
播放参数与物理输入分开，支持独立复制、安全删除和组合；模拟输入改变后需要明确重烘焙（[#22](https://github.com/mumu-lhl/blender-vfx-studio/issues/22)）。

当前只支持有界的静态源 Cloth，暂无碰撞、外部力场、流体或烟雾。后续完善更多模拟类型、完整缓存版本迁移及实际性能预算。
未烘焙的模拟不能承诺任意帧都正确，已存姿态才能直接跳帧播放。

## M5：交互、兼容性和正式发布——尚未完成

正在增加 Windows x64、Apple Silicon macOS 和 Linux x64 的完整后台测试（[#24](https://github.com/mumu-lhl/blender-vfx-studio/issues/24)），目前跨平台结果尚待 CI。
仍需图形界面点击/Undo 检查、更系统的 Eevee/Cycles 视觉比较和稳定性修复。完成这些验证前，不将预览版标为正式稳定版。

## 已验证的范围与发布状态

Blender 5.2.2 Linux 已通过 80 项测试，包括时间公式的 60 组输入对照、参数文件和用户库检查，以及真实 Blender 中的各模块行为。
用户库另有隔离目录中的界面操作验证，包含图片缺失时不创建残缺实例。

环形、图集、合成、粒子、轨迹、绑定、组合、Cloth 和 Arc Slash 分别在新进程中重开 `.blend`，不加载插件且关闭脚本自动执行。
图集、合成和粒子还有 CPU 渲染像素检查；Cloth 重开时会删除模拟源，验证已存姿态独立可用。
安装包已验证安装、启用、创建和卸载，Ruff 检查与格式校验通过。

`tools/preview.py` 可重新生成组合场景。Cycles CPU 800×500 和 Eevee 预览已查看；最新 Trail 构图另检查了 Eevee 400×250 图像。尚未进行图形界面点击/Undo 操作和 Windows/macOS 测试。

v0.2–v0.5 已发布，分别覆盖环形与参数预设、图集、合成、粒子。v0.6 增加轨迹，v0.7 增加绑定；两版均已发布并下载校验，v0.6 的 ZIP 也与干净源码构建一致。用户库版本 0.8.0 和组合版本 0.9.0 已发布并下载校验，Cloth 开发版本为 0.10.0，Arc Slash 开发版本为 0.11.0，发布情况以 [Releases](https://github.com/mumu-lhl/blender-vfx-studio/releases) 为准。

版本标签会触发测试和 CPU 预览，再上传 ZIP、SHA256SUMS 和 PNG。云端直接上传附件曾返回 401，现由 GitHub Actions 的独立发布任务完成（[#5](https://github.com/mumu-lhl/blender-vfx-studio/issues/5)）。v0.6 首次标签误指旧提交，被版本校验拦截；未发布的标签修正后已通过完整发布流程，没有发布错误安装包。
