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
- 通过 Cycles CPU 预览；实际 Eevee 渲染受当前云端 EGL 上下文限制，尚未完成视觉验收。
- 待实现：用户预设导入导出和迁移协议（[#3](https://github.com/mumu-lhl/blender-vfx-studio/issues/3)）、更完整的 Layer 组合和绑定界面。

首次开发跟踪：[#1](https://github.com/mumu-lhl/blender-vfx-studio/issues/1)。

## M2 — 下一阶段

1. Flipbook 原生图集动画：复用统一时间，明确 UV 行列顺序与外部图片所有权（[#2](https://github.com/mumu-lhl/blender-vfx-studio/issues/2)）。
2. 扩展基础 Mesh / Shader 库，优先刀光与冲击波的视觉表现。
3. Geometry Nodes 粒子切片，先实现可确定性求值的生成、寿命、随机与实例化。
4. 主动启用的 Screen 辉光/闪光，保留用户 Compositor 链。

## M3 — 尚未开始

Trail / Ribbon / 运动轨迹、角色骨骼绑定界面、多层组合、预设库与资源引用。

## M4 — 尚未开始

Simulation、参数变更引起的缓存失效、缓存烘焙与保存重开、高级效果、实测性能预算。

## M5 — 尚未开始

交互体验、跨平台、Eevee/Cycles 视觉回归与正式稳定发布。0.1.0 是早期预览，不代表正式版。

## 本次验证记录

Blender 5.2.2 Linux：时间表达式对照 144 个输入组合；5 个集成测试（包含多个子场景）；
独立进程禁用自动执行且不导入插件时的保存重开；安装包安装、启用、创建、卸载；Ruff 检查与格式校验。
Cycles CPU 32 samples 800×500 预览已人工检查，生成脚本 `tools/preview.py`。
未进行图形界面的点击/Undo 操作验证，也未测试 Windows/macOS。
