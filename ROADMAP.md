# 开发进度与后续计划

更新：2026-10-30（UTC）。目标 **Blender 5.2 LTS**，优先 Eevee，兼容 Cycles。**项目尚未正式分发，仅提供开发构建。** 当前实现可以调整，过时生成器和兼容性专用代码无需保留。

## 当前重点

**完整库已由三套扩充至八套。** 闪电、烟尘、火焰、冲刺残影和魔法阵已完成首轮真实角色图像、隔帧动画及原生文件检查并合并；与原三套合计 18 个质量文件。不同质量不计作新种类。入口、参数和画面见 [入门指南](docs/STARTER_LIBRARY.md) 与 [角色图集](docs/LIBRARY_GALLERY.md)。

艺术表现仍是首要目标。允许有价值的几何、材质和粒子增加开销，用质量选择和实测成本说明取舍，不设统一低成本或顶点上限。复杂骨架、跨平台 GUI 扩展和新的模拟类型暂缓。

## 当前艺术判断

接触时序已由 [#188](https://github.com/mumu-lhl/blender-vfx-studio/pull/188) 合入；17 张高清、48 张整段原生隔帧及无插件三阶段像素复现已检查，功能源码 CI 十二项成功。分叉火焰在完整施法中的 54 张视频隔帧也已补查。它们不代表整库已达到成熟游戏品质，未观看实时视频。

**Energy Charge 的主体仍未达到目标。** [#186](https://github.com/mumu-lhl/blender-vfx-studio/pull/186) 的压力核、流动曲面与密度方案没有形成清楚的聚能主体，密度原型还会在 Cycles 检查中崩溃，已关闭而不合入。源码、失败实图和复现见[独立归档](https://github.com/mumu-lhl/blender-vfx-studio/blob/c57df84977dd1d02ced5e67bac1849fd18ec9cb8/docs/experiments/CHARGE_DENSITY.md)，这些失败不属于 main 的可用功能。

[#190](https://github.com/mumu-lhl/blender-vfx-studio/pull/190) 的预备动作与剑柄交接完成高清明暗／远景、22 张前奏隔帧及无插件复现，但中心可读性没有明确优于主线，继续保持草稿。新能量场已改善手边焦点，但原生下劈开头的复查仍存在回落再后摆、身体压重不足的问题；[新实图与原生轨迹检查](https://github.com/mumu-lhl/blender-vfx-studio/blob/45b05e1/docs/experiments/WINDUP_FIELD.md)继续保持草稿。后续以完整动作的连续性判断取舍，不因姿态变多就宣布力量感通过。

[#193](https://github.com/mumu-lhl/blender-vfx-studio/pull/193) 修复角色刀光在中间转向帧偏离剑刃平面的问题。16 张高清对照、48 张整段原生隔帧与三个阶段无插件高清像素复现已检查；头部的大蓝片错位消除，多层重叠仍存在。功能源码 `639edfc` 的 CI 已完成全部 12 项并成功，详见[空间对齐](docs/SLASH_PLANE_REVIEW.md)。充能的火瓣和实体候选均已拒绝并[独立归档](https://github.com/mumu-lhl/blender-vfx-studio/blob/9474a9b/docs/experiments/CHARGE_FLARE.md)；[#194](https://github.com/mumu-lhl/blender-vfx-studio/pull/194) 的程序化能量场已完成 16 张新版高清图、28 张充能周期原生隔帧、22 项入门库、无插件高清复现与完整资产预览检查；中心清晰度改善，前段和背侧遮挡仍有限制。CI 已完成全部 12 项并成功，另已读完实际 CI 视频的 48 张隔帧，已合入，见[能量场检查](docs/CHARGE_PLASMA_REVIEW.md)。

## 已有功能与边界

| 阶段 | 已能使用 | 当前边界 |
| --- | --- | --- |
| M0 开发基础 | 原生侧栏、Extension 构建、安装/卸载、三平台后台 CI | 目标测试版本 5.2.2，后台检查不代替 GUI 检查 |
| M1 共享控制 | 独立实例、Start / Duration / Speed / Loop、Mesh / Shader、跳帧及无插件播放 | 保留原生可编辑数据与实例资源安全 |
| M2 基础模块与资产库 | 8 套完整资产、Burst / Emitter、Flipbook、Screen | 粒子在局部空间计算，无碰撞或历史受力；外部序列图不打包 |
| M3 创作与复用 | Ribbon、对象/骨骼绑定、角色残影捕获、组合、Ungroup All、参数库、完整资产和 Asset Browser | 源动画改变需重新采样；组合不含 Screen 或嵌套组合 |
| M4 首个模拟 | Cloth Energy Sheet、状态提示、姿态烘焙与无插件回放 | 静态有界源，无碰撞、外部力场或流体；只有已存姿态支持任意帧 |
| M5 稳定性 | Windows/Linux/macOS 后台测试、保存重开、部分 Linux 窗口检查 | Windows/macOS 实际窗口与更多 UI 缩放未验收，见 [GUI 记录](docs/GUI_CHECKS.md) |

## 资产库首轮视觉检查

| 效果 | 合并 PR | 实际读取的最终视频隔帧图 | 编辑、成本与未解决问题 |
| --- | --- | ---: | --- |
| Lightning Strike | [#144](https://github.com/mumu-lhl/blender-vfx-studio/pull/144) | 14 张 | [闪电记录](docs/LIGHTNING_REVIEW.md)：远景细枝和接触火花偏弱 |
| Dust Impact | [#145](https://github.com/mumu-lhl/blender-vfx-studio/pull/145) | 30 张 | [烟尘记录](docs/DUST_REVIEW.md)：原生密度网格解决矩形伪影，逐帧密度计算有 CPU 成本 |
| Stylized Fire | [#146](https://github.com/mumu-lhl/blender-vfx-studio/pull/146) | 36 张 | [火焰记录](docs/FIRE_REVIEW.md)：连接底部与较小热芯已进入生成器，中段大火面仍明显 |
| Character Dash Echoes | [#147](https://github.com/mumu-lhl/blender-vfx-studio/pull/147) | 24 张 | [残影记录](docs/DASH_REVIEW.md)：可捕获自己的角色，透明叠层渲染较贵，结束处动作切换仍硬 |
| Calligraphic Magic Circle | [#148](https://github.com/mumu-lhl/blender-vfx-studio/pull/148) | 40 张 | [魔法阵记录](docs/MAGIC_REVIEW.md)：逐笔、反转和升起有先后，远景细笔画偏弱 |

以上均实际查看了 960×540 阶段图、明暗背景与远景，并检查了嵌入预览。**未观看实时播放**；隔帧能检查出现顺序、位置和消散，不能完整证明速度感或商业成片品质。后台求值与软件渲染时间也不是视口 FPS。

上表首轮整合的功能源码为 `d7c79d78576984d1eb810e74891c1f4ed8a0e2be`，该次完整后台套件通过。后续生成器与角色镜头改动的检查分别记录在下文。从 GitHub 全新克隆后，构建、安装/启用/卸载、18 文件重建和无插件重开通过。每套的最终生成器还保留对应 CI、图像摘要与原生高清像素对照；详见上表记录。

## 原三套与角色镜头

[PR #136](https://github.com/mumu-lhl/blender-vfx-studio/pull/136) 已完成两名 CC0 KayKit 蒙皮角色的必要战斗验证：96 帧、24 fps，全部 48 张视频隔帧图和远景、暗背景、反向机位实际读取，无插件三帧像素一致，恢复阶段清空。见 [角色镜头记录](docs/CHARACTER_COMBAT_REVIEW.md)。

- **Energy Charge**：卷曲内核、沿形体运动的亮带和可调进流权重已完成角色对照；中心更集中，远景细亮带与部分角度的弯片感仍待改善。见 [焦点与动画检查](docs/CHARGE_HIERARCHY_REVIEW.md)。
- **Arc Slash**：主刀面配有色、两端收尖的独立残弧；硬笔触和远景细尾仍待完整动作判断。见 [残影记录](docs/SLASH_WAKE_REVIEW.md)。
- **Impact Burst**：已分为断裂主体、细喷射、辅助卷流与隆起压力弧；侧面偏实体、远景细层弱。见 [主体](docs/IMPACT_SURFACE_REVIEW.md)、[细喷射](docs/IMPACT_FINE_REVIEW.md) 与 [压力弧](docs/IMPACT_WAVE_REVIEW.md)。

[#89](https://github.com/mumu-lhl/blender-vfx-studio/issues/89) 跟踪整体艺术品质。完整施法镜头的准备／释放／退场已完成必要检查，实际读取 54 张解码隔帧图及明暗、远景对照；范围与成本见 [施法记录](docs/SPELL_SEQUENCE_REVIEW.md)。冲刺接落地烟尘 [#156](https://github.com/mumu-lhl/blender-vfx-studio/issues/156) 已完成位移／接触／恢复的镜头与抽帧检查，远景与早期反馈的艺术限制仍保留。当前参数与艺术可编辑性审查由 [#161](https://github.com/mumu-lhl/blender-vfx-studio/issues/161) 跟踪。

软件 Eevee 曾在完成像素检查后退出崩溃；CI 的原生重开采用局部 Mesa 磁盘缓存设置并要求正常退出，不忽略失败。具体范围和对照见 [退出记录](docs/EEVEE_EXIT_REVIEW.md)。

[#180](https://github.com/mumu-lhl/blender-vfx-studio/issues/180)／[PR #181](https://github.com/mumu-lhl/blender-vfx-studio/pull/181) 将闪电的单次细圆环改为随三次放电重新展开的地表分叉电弧。19 张最终高清图、九张有序隔帧与三阶段无插件像素对照已检查，三档原生资产与嵌入预览保留；前两次远景反馈改善，第三次和细枝仍弱。详见 [接触反馈](docs/LIGHTNING_CONTACT_REVIEW.md)，未宣布整套艺术验收通过。

## 艺术控制与易用性

[#161](https://github.com/mumu-lhl/blender-vfx-studio/issues/161) 先处理真实无效、无法关闭造型和换色困难的控制；[审查记录](docs/ART_CONTROLS_REVIEW.md) 列出八套的核对结果与边界。

- [PR #162](https://github.com/mumu-lhl/blender-vfx-studio/pull/162)：Clean / Stylized 刀光、独立锋刃配色、原生颜色选择器与关键帧、蓝／绿火焰色带、现有 Fire / Dust / Magic 控制分组、Ground Veil Fade 修复。多阶段 Eevee 图已实际读取，Clean 与蓝焰无插件高清重开像素一致，完整后台与安装检查通过；CI 仍以 PR 的最终状态为准。
- [#163](https://github.com/mumu-lhl/blender-vfx-studio/issues/163)：独立 Echo Count 与任意跨度的均匀子帧捕获，保留源网格细节；八项捕获测试与无源重开通过；五姿态角色的三个高清阶段及暗背景已读取，原生重渲染像素一致。浅背景旧影仍淡，详见 [采样记录](docs/DASH_SAMPLING_REVIEW.md)。
- [PR #165](https://github.com/mumu-lhl/blender-vfx-studio/pull/165)：充能核心大小／压缩／释放、闪电长度／分支集中访问；Hook 与几何内缘分别控制。18 张角色对照、刀光隔离图与默认峰值／尾部像素对照已实际查看，11 项艺术控制、10 项刀光、8 项残影回归与无插件重开通过。手工嵌套节点及完整保存保留，JSON 入口明确命名；Linux 默认缩放已检查折叠、原生色轮／RGB 插帧、热色色带和五姿态捕获；其他平台／缩放与实时播放未验收。
- [#166](https://github.com/mumu-lhl/blender-vfx-studio/issues/166)／[PR #167](https://github.com/mumu-lhl/blender-vfx-studio/pull/167)：重塑 Energy Charge 卷曲内核、流动亮带与可调进流权重。21 项入门库、11 项艺术控制及原生跳帧通过。实际读取 17 张高清明暗／远景／反向对照与 60 张修改前后隔帧；三个阶段无插件高清重渲染像素一致，实测成本与观看边界见 [记录](docs/CHARGE_HIERARCHY_REVIEW.md)。三平台及长视觉 CI 已全部成功。
- PR #165 的 [CI 40607385631](https://github.com/mumu-lhl/blender-vfx-studio/actions/runs/40607385631) 全部 12 项成功。Impact 主次调节、Lightning 放电节奏仍待实施；集中编辑入口不等于已经完成艺术改进。

[#168](https://github.com/mumu-lhl/blender-vfx-studio/issues/168)／[PR #169](https://github.com/mumu-lhl/blender-vfx-studio/pull/169) 集中 Impact 现有原生造型与高级材质控制。14 项行为检查和无插件重开通过；10 张高清角色对照已实际读取，修改场景三阶段原生重渲染像素一致。对照参数增加了实体感，因此保留默认画面；短闪的旋转可读性由 [#170](https://github.com/mumu-lhl/blender-vfx-studio/issues/170) 继续修复。

[#170](https://github.com/mumu-lhl/blender-vfx-studio/issues/170)／[PR #171](https://github.com/mumu-lhl/blender-vfx-studio/pull/171) 修复短闪随绑定旋转变暗：14 张高清明暗／远景／反向对照已读取，15 项行为检查和三个阶段无插件高清重开通过，退场后画面与基线一致。反向焦点被模型遮挡，未记为可读性通过。详见 [短闪检查](docs/IMPACT_FLASH_REVIEW.md)。

[#172](https://github.com/mumu-lhl/blender-vfx-studio/issues/172)／[PR #173](https://github.com/mumu-lhl/blender-vfx-studio/pull/173) 支持捕获后设置 Echo Tail，保留当前进场间隔、姿态和节点；13 项残影、14 项组合与无源原生跳帧通过。8 张角色阶段图、三个阶段无插件高清像素和 Linux 默认缩放弹窗检查已完成。CI 40711832268 全部 12 项成功；Lightning 首次下载校验失败，整轮结束后单独重试通过，官方校验保持启用。

PR #167 的 CI 40693445113、PR #169 的 CI 40694847951、PR #171 的 CI 40700723464 均已完成全部 12 项并成功。本轮未发布新版本。

[#178](https://github.com/mumu-lhl/blender-vfx-studio/issues/178)／[PR #179](https://github.com/mumu-lhl/blender-vfx-studio/pull/179) 收敛近身命中的压力弧，并将主压力体改为独立贴合接触面的翻卷曲面，细喷射保留方向。实际同帧与隔帧中遮挡、主次和恢复阶段有所改善；主体体积感仍不足，未宣布整体艺术验收通过。功能与图像范围见 [命中焦点检查](docs/IMPACT_FOCUS_REVIEW.md)。

[#156](https://github.com/mumu-lhl/blender-vfx-studio/issues/156)／[PR #157](https://github.com/mumu-lhl/blender-vfx-studio/pull/157) 用真实脚部接触连接冲刺、腾空和落地；新建残影保留透明填充与稍晚消退的轮廓，两侧体积烟尘先压低展开再翻滚。14 张高清阶段、42 张原生隔帧、六个质量资产及无插件像素复现已检查，CI 全部 12 项成功。远景旧残影与接触后一帧仍弱，不宣布整体艺术验收通过。见 [角色衔接](docs/DASH_LANDING_REVIEW.md)。

[#182](https://github.com/mumu-lhl/blender-vfx-studio/issues/182)／[PR #183](https://github.com/mumu-lhl/blender-vfx-studio/pull/183) 让释放符记沿原生可编辑方向汇聚，再接上火焰点燃。地面逐笔形成和符文反转保留，完整角色多阶段、明暗／远景、54 张解码隔帧、三档资产与无插件高清复现已检查，实测成本已记录，CI 全部 12 项成功。符记重叠与初生火焰大面仍需改善，见 [施法交接](docs/SPELL_TRANSFER_REVIEW.md)。

[#184](https://github.com/mumu-lhl/blender-vfx-studio/issues/184)／[PR #185](https://github.com/mumu-lhl/blender-vfx-studio/pull/185) 已合入共享下部、错相生长的分叉火舌和沿流向的热色冷缝。已读取 14 张高清明暗／远景及施法阶段、36 张原生隔帧和三档完整资产预览；无插件高清像素一致，实测成本已记录。CI 全部 12 项成功；底部团块、局部薄边与实时播放判断的艺术限制仍保留。见 [分叉检查](docs/FIRE_FORK_REVIEW.md)。

[#187](https://github.com/mumu-lhl/blender-vfx-studio/issues/187)／[PR #188](https://github.com/mumu-lhl/blender-vfx-studio/pull/188) 已把充能释放对齐真实接触帧，并补齐快速转剑关键帧。17 张同机位、明暗与远景高清图，以及完整动作的 48 张原生隔帧均已实际读取；时序、无插件参数和三阶段高清全通道像素复现通过，CI 全部 12 项成功。卷片遮手和整体艺术问题仍保留，见[接触时序](docs/CHARGE_CONTACT_REVIEW.md)。另补查分叉火焰进入完整施法的 54 张视频隔帧，底部团块和角色蓄势仍弱。

## 下一步

1. 当前重点转向实际画面。[#174](https://github.com/mumu-lhl/blender-vfx-studio/issues/174) 修正刀光深度收尖，并按真实挥剑轨迹连接充能与释放；同帧角色图、连续隔帧、明暗／远景与原生复现已检查，方向衔接和遮挡改善，反向命中仍被角色遮住。实测成本和艺术边界见 [衔接检查](docs/COMBAT_HANDOFF_REVIEW.md)。
2. [#176](https://github.com/mumu-lhl/blender-vfx-studio/issues/176) 的持续火焰已完成角色多阶段、两组各 11 张持续燃烧抽帧、明暗／远景与无插件高清复现。轮廓与退场改善，局部鼓包、色块和细节仍弱；见 [流动检查](docs/FIRE_FLOW_REVIEW.md)。命中主体、接触闪电和冲刺落地的首轮改动已合入；施法空间交接及错相分叉火舌已合入，并补查完整施法隔帧。充能焦点的首轮能量场改动已合入；下一优先项是早段中心与进流的主次、独立释放的交叉白带及动作蓄势的连续性，再依据完整镜头处理火焰底部团块和仍弱的远景层次。暂缓继续整理参数。
3. 保留质量选择，在可用设备测量有／无特效成本；需要更高复杂度时以画面收益判断，不用低顶点数代替性能证据。
4. 处理发布所需的实际问题并检查安装附件；完成必要视觉与使用验证后再准备首次正式分发，不急于新增仅换色的第九套。

历史提交、发布和详细检查见 [Releases](https://github.com/mumu-lhl/blender-vfx-studio/releases)、GitHub Issues 与上述记录；使用和结构见 [README](README.md)、[DESIGN](DESIGN.md) 与 [CONTEXT](CONTEXT.md)。

当前 main 的开发包构建 [41091740203](https://github.com/mumu-lhl/blender-vfx-studio/actions/runs/41091740203) 正在运行；新能量场功能源码的 PR 构建已完成全部 12 项并成功，18 个示例的实际附件已下载并原生核对。本轮没有发布正式版本。
