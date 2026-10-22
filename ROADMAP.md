# Roadmap

更新：2026-10-22（Asia/Shanghai）。状态只反映已实现和验证的范围。

## M0 — 已实现

- Blender 5.2 Extension 注册与原生侧栏，GPL-3.0-or-later。
- 纯 Python 可重复 ZIP 构建，Blender manifest 校验。
- 时间单元测试、真实 bpy CPU 集成测试、无插件新进程重开测试、隔离安装/启用/卸载测试。
- CI 固定官方 Blender 5.2.2 并校验下载 SHA256；打包产物作为 Actions artifact。
- 架构、领域约定、ADR 与开发规则。

## M1 — 首个纵向切片已实现，Core 继续演进

- UUID / schema / asset version、Controller / Layer、参数元数据和轻量模块注册。
- 原生无状态统一时间：开始、持续时间、速度、循环、任意帧求值。
- Mesh + Shader：Shockwave / Energy Ring，原生 Geometry Nodes 与 Shader Nodes，可关键帧化参数。
- 独立复制（含 Action 与用户节点编辑）、保守删除、质量档位。
- 通过 Cycles CPU 800×500 及 Eevee 200×125 后台预览；Eevee 出现 EGL 警告但渲染成功。
- 用户参数预设 JSON 导入/导出、独立格式版本与严格校验（[#3](https://github.com/mumu-lhl/blender-vfx-studio/issues/3)）。
- 待实现：更完整的 Layer 组合和绑定界面；未来增加新 schema 前实现逐版本迁移和历史固定样例。

首次开发跟踪：[#1](https://github.com/mumu-lhl/blender-vfx-studio/issues/1)。

## M2 — 进行中

1. 已实现 Flipbook 图集动画：原生时间、UV 左上行序、区间、尺寸、透明度、独立复制和图片保留；支持 JSON 图片相对引用及格式 1 → 2 迁移（[#2](https://github.com/mumu-lhl/blender-vfx-studio/issues/2)）。
2. 扩展基础 Mesh / Shader 库，优先刀光与冲击波的视觉表现。
3. 已实现 Geometry Nodes 无状态粒子爆发：有界生成、确定性随机、弹道、生命周期和实例化（[#11](https://github.com/mumu-lhl/blender-vfx-studio/issues/11)）；连续发射与碰撞尚未实现。
4. 已实现主动启用的 Screen 辉光/时间闪光，保留现有合成链、支持独立复制与保守移除（[#9](https://github.com/mumu-lhl/blender-vfx-studio/issues/9)）。

## M3 — 尚未开始

Trail / Ribbon / 运动轨迹、角色骨骼绑定界面、多层组合、预设库与资源引用。

## M4 — 尚未开始

Simulation、参数变更引起的缓存失效、缓存烘焙与保存重开、高级效果、实测性能预算。

## M5 — 尚未开始

交互体验、跨平台、Eevee/Cycles 视觉回归与正式稳定发布。0.5.0 是早期预览，不代表正式版。

## 本次验证记录

Blender 5.2.2 Linux：时间表达式对照 60 个输入组合；9 个预设测试；8 个 Core、5 个 Flipbook、10 个 Screen 和 5 个 Particle 集成测试（包含多个子场景）；
四个独立进程禁用自动执行且不导入插件时的环形/图集/合成/粒子保存重开；Flipbook 另有实际 CPU 像素选帧校验；安装包安装、启用、创建、卸载；Ruff 检查与格式校验。
Cycles CPU 32 samples 800×500 与 Eevee 200×125 预览已人工检查，生成脚本 `tools/preview.py`。
未进行图形界面的点击/Undo 操作验证，也未测试 Windows/macOS。

## 发布状态

PR #4、#6、#7 已通过 GitHub CI 并合并，v0.2.0 已发布并下载校验；v0.3.0 Flipbook 已发布并通过全新 Clone 构建及下载 SHA256 校验；v0.4.0 原生 Screen VFX 已发布；0.5.0 增加原生粒子爆发和内部材质引用管理。
云端直接上传 Releases 附件返回 401（[#5](https://github.com/mumu-lhl/blender-vfx-studio/issues/5)）；新增 tag 发布任务使用 GitHub Actions 仓库令牌上传经过同一工作流测试的 ZIP。
发布前校验 tag 与 manifest 版本一致；构建/测试 job 只有读取权限，独立发布 job 才有 contents:write。
tag 构建同时生成 Cycles CPU 预览；Release 附加 ZIP、SHA256SUMS 和 PNG。实际附件状态以 GitHub Release 和 tag 工作流结果为准。
