# 开发进度与后续计划

更新：2026-10-27（UTC）。目标 **Blender 5.2 LTS**，优先 Eevee，兼容 Cycles。**项目尚未正式分发，仅提供开发构建。** 当前实现可以调整，过时生成器和兼容性专用代码无需保留。

## 当前重点

**完整库已由三套扩充至八套。** 闪电、烟尘、火焰、冲刺残影和魔法阵已完成首轮真实角色图像、隔帧动画及原生文件检查并合并；与原三套合计 18 个质量文件。不同质量不计作新种类。入口、参数和画面见 [入门指南](docs/STARTER_LIBRARY.md) 与 [角色图集](docs/LIBRARY_GALLERY.md)。

艺术表现仍是首要目标。允许有价值的几何、材质和粒子增加开销，用质量选择和实测成本说明取舍，不设统一低成本或顶点上限。复杂骨架、跨平台 GUI 扩展和新的模拟类型暂缓。

## 已有功能与边界

| 阶段 | 已能使用 | 当前边界 |
| --- | --- | --- |
| M0 开发基础 | 原生侧栏、Extension 构建、安装/卸载、三平台后台 CI | 目标测试版本 5.2.2，后台检查不代替 GUI 检查 |
| M1 共享控制 | 独立实例、Start / Duration / Speed / Loop、Mesh / Shader、跳帧及无插件播放 | 保留原生可编辑数据与实例资源安全 |
| M2 基础模块与资产库 | 8 套完整资产、Burst / Emitter、Flipbook、Screen | 粒子在局部空间计算，无碰撞或历史受力；外部序列图不打包 |
| M3 创作与复用 | Ribbon、对象/骨骼绑定、角色残影捕获、组合、Ungroup All、参数库、完整资产和 Asset Browser | 源动画改变需重新采样；组合不含 Screen 或嵌套组合 |
| M4 首个模拟 | Cloth Energy Sheet、状态提示、姿态烘焙与无插件回放 | 静态有界源，无碰撞、外部力场或流体；只有已存姿态支持任意帧 |
| M5 稳定性 | Windows/Linux/macOS 后台测试、保存重开、部分 Linux 窗口检查 | Windows/macOS 实际窗口与更多 UI 缩放未验收，见 [GUI 记录](docs/GUI_CHECKS.md) |

## 本轮视觉交付

| 效果 | 合并 PR | 实际读取的最终视频隔帧图 | 编辑、成本与未解决问题 |
| --- | --- | ---: | --- |
| Lightning Strike | [#144](https://github.com/mumu-lhl/blender-vfx-studio/pull/144) | 14 张 | [闪电记录](docs/LIGHTNING_REVIEW.md)：远景细枝和接触火花偏弱 |
| Dust Impact | [#145](https://github.com/mumu-lhl/blender-vfx-studio/pull/145) | 30 张 | [烟尘记录](docs/DUST_REVIEW.md)：原生密度网格解决矩形伪影，逐帧密度计算有 CPU 成本 |
| Stylized Fire | [#146](https://github.com/mumu-lhl/blender-vfx-studio/pull/146) | 36 张 | [火焰记录](docs/FIRE_REVIEW.md)：连接底部与较小热芯已进入生成器，中段大火面仍明显 |
| Character Dash Echoes | [#147](https://github.com/mumu-lhl/blender-vfx-studio/pull/147) | 24 张 | [残影记录](docs/DASH_REVIEW.md)：可捕获自己的角色，透明叠层渲染较贵，结束处动作切换仍硬 |
| Calligraphic Magic Circle | [#148](https://github.com/mumu-lhl/blender-vfx-studio/pull/148) | 40 张 | [魔法阵记录](docs/MAGIC_REVIEW.md)：逐笔、反转和升起有先后，远景细笔画偏弱 |

以上均实际查看了 960×540 阶段图、明暗背景与远景，并检查了嵌入预览。**未观看实时播放**；隔帧能检查出现顺序、位置和消散，不能完整证明速度感或商业成片品质。后台求值与软件渲染时间也不是视口 FPS。

整合功能源码与 `d7c79d78576984d1eb810e74891c1f4ed8a0e2be` 一致，完整后台套件通过。从 GitHub 全新克隆后，构建、安装/启用/卸载、18 文件重建和无插件重开通过。每套的最终生成器还保留对应 CI、图像摘要与原生高清像素对照；详见上表记录。

## 原三套与角色镜头

[PR #136](https://github.com/mumu-lhl/blender-vfx-studio/pull/136) 已完成两名 CC0 KayKit 蒙皮角色的必要战斗验证：96 帧、24 fps，全部 48 张视频隔帧图和远景、暗背景、反向机位实际读取，无插件三帧像素一致，恢复阶段清空。见 [角色镜头记录](docs/CHARACTER_COMBAT_REVIEW.md)。

- **Energy Charge**：原生束流、压缩内核和地面进流已重做；远景主体仍小、细碎。见 [束流](docs/CHARGE_STREAM_REVIEW.md)、[内核](docs/CHARGE_FOCUS_REVIEW.md)、[压缩](docs/CHARGE_TENSION_REVIEW.md) 与 [地面进流](docs/CHARGE_GROUND_REVIEW.md)。
- **Arc Slash**：主刀面配有色、两端收尖的独立残弧；硬笔触和远景细尾仍待完整动作判断。见 [残影记录](docs/SLASH_WAKE_REVIEW.md)。
- **Impact Burst**：已分为断裂主体、细喷射、辅助卷流与隆起压力弧；侧面偏实体、远景细层弱。见 [主体](docs/IMPACT_SURFACE_REVIEW.md)、[细喷射](docs/IMPACT_FINE_REVIEW.md) 与 [压力弧](docs/IMPACT_WAVE_REVIEW.md)。

[#69](https://github.com/mumu-lhl/blender-vfx-studio/issues/69) 按用户授权的隔帧方法完成的是旧版检查，不自动适用于后来生成器。[#89](https://github.com/mumu-lhl/blender-vfx-studio/issues/89) 继续跟踪整体艺术品质。[#137](https://github.com/mumu-lhl/blender-vfx-studio/issues/137) 的充能原型已提交保留，但造型未通过，不合并。

软件 Eevee 曾在完成像素检查后退出崩溃；CI 的原生重开采用局部 Mesa 磁盘缓存设置并要求正常退出，不忽略失败。具体范围和对照见 [退出记录](docs/EEVEE_EXIT_REVIEW.md)。

## 下一步

1. 把新库用于有明确动作目的的完整技能镜头，优先检查冲刺接落地、施法接释放的节奏、遮挡和远景焦点；不把八套同时叠在画面上作为品质证明。
2. 按完整镜头中最明显的问题改真实生成器与参数，再看修改前后的高清图和动画样本，避免恢复无止境的局部修补。
3. 保留质量选择，在可用设备测量有／无特效成本；需要更高复杂度时以画面收益判断，不用低顶点数代替性能证据。
4. 处理发布所需的实际问题并检查安装附件；完成必要视觉与使用验证后再准备首次正式分发，不急于新增仅换色的第九套。

历史提交、发布和详细检查见 [Releases](https://github.com/mumu-lhl/blender-vfx-studio/releases)、GitHub Issues 与上述记录；使用和结构见 [README](README.md)、[DESIGN](DESIGN.md) 与 [CONTEXT](CONTEXT.md)。
