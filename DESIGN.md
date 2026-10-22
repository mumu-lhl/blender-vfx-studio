# 系统设计

目标：Blender 5.2 LTS 原生二次元动画 VFX；优先 Eevee，兼容 Cycles，低配置默认可用。
当前实现 Mesh + Shader 环形效果、Flipbook 图集动画、Screen 合成及无状态粒子爆发。

## 数据与边界

- `registry.py`：模块描述和内置预设。注册 `mesh.ring`、`flipbook.atlas` 、`screen.glare` 与 `particle.burst`，资产版本均为 1；预设是创建时的参数快照。
- `timing.py`：无 bpy 的时间约定及原生驱动表达式。
- `parameters.py`：无 bpy 的参数元数据；`presets.py`：纯 Python 参数预设校验和原子文件写入。
- `core.py`：实例创建、解析、复制、删除；所有权检查和参数预设实例化。
- `nodes.py`：原生 Geometry Nodes、Shader Nodes 和驱动器构建。
- `flipbook.py`：静态贴片、原生几何生命周期和 Shader Nodes 图集 UV 求值。
- `screen.py`：场景级合成 Layer，负责保守插入、透传恢复和私有节点组复制。
- `particle.py`：有界、确定性的 Geometry Nodes 粒子爆发，原生实例化与弹道求值。
- `ui.py`：原生侧栏与 Undo 操作，委托 core；不承担节点构建。

Effect 对应一个 Empty Controller，一组原生 ID 属性控制 Layer；当前每实例一个空间 Mesh Layer 或场景级 Compositor Layer。
每实例具有 UUID；空间效果拥有私有网格、材质和 Geometry Node Tree，Screen 拥有私有合成节点组。Collection 仅负责组织；名称不承担身份语义。
Layer 使用命名点属性标记内外边缘，由 Geometry Nodes 重建径向位置；UV 沿圆周和宽度展开。
材质包含 UV 流动、噪声阈值溶解、边缘透明、发光和生命周期淡出；节点保留描述和布局供编辑。

## 原生求值与编辑

Controller 的原生 ID 属性是持久化真值，可使用 Blender 原生关键帧。
对象驱动器连接 Geometry Nodes 输入，材质驱动器连接节点值；没有 Python 帧处理器、驱动命名空间函数或插件运行依赖。
5.2 修改器输入路径为 `modifiers[...].properties.inputs.Socket_N.value`；使用实际 bpy 测试验证，不套用旧版 IDProperty 写法。
驱动器使用 Blender 的 simple expressions。循环用 `x-floor(x)`，因为 `%` 会落入 Python 求值路径。
插件停用或未安装时，保存的几何、着色器、动画和简单驱动器仍可由 Blender 求值，禁用自动执行也可播放。

参数更新只改变输入，不重建节点。自定义节点和拓扑可保留；若用户删除驱动目标或命名属性，相应功能可能失效。
质量级别仅在创建时选择 32/64/128 段，避免修改参数时重建用户编辑的网格。

## 生命周期与安全

生命周期定义见 [CONTEXT.md](CONTEXT.md)。当前环形效果为无状态效果，可直接跳到任意帧；循环会在周期边界重置，不承诺连续外观。
Effect 复制会复制私有数据、节点和 Action，并重定向到新控制器；保留手动节点编辑。
外部父对象/骨骼绑定沿用 Blender 原生关系，尚无专用绑定 UI。

删除只处理该控制器层级中的自有 Layer 和零用户的自有资源；保留其他子对象并保持世界变换，保留外来材质和非空集合。
共享生成资产仍依赖原控制器，因此删除前拒绝外部共享网格、材质和节点组；解除共享后重试。
外部自建驱动器或约束若引用控制器，需要用户自行处理；当前没有通用依赖迁移。
使用 Blender 的 Shift-D 复制控制器会复制 UUID；检测到歧义即拒绝管理操作，使用 VFX Duplicate 创建独立实例。

## 演进接口

schema 与 asset version 分离。当前仅支持 schema 1；未来版本或缺失版本拒绝编辑，不做猜测性迁移。
用户预设采用独立 JSON 格式 2，导入前校验完整字段、参数范围、有限数值、模块和资产版本。
64 KiB 有界读取；拒绝重复键；导出先验证，再以同目录临时文件原子替换，失败不损坏原文件。
预设保存参数快照，不保存时间起点、变换、UUID、Action 或自定义拓扑；载入创建新实例而不改写选中效果。
保留固定历史样例验证预设格式 1 → 2：环形参数不变，补充空 assets 字段。未知版本拒绝导入；实例 schema 未改变。
目前不引入通用模块插件框架、专用节点编辑器、模拟管理器或资产数据库。

Particle / Flipbook / Trail 等新模块复用 Controller、时间约定和所有权；新增之前先形成真实 bpy 的可用切片。
Simulation 必须显式声明有状态，记录模拟区间、缓存版本、参数失效规则及烘焙状态，不能套用无状态任意帧承诺。
Screen VFX 必须主动启用并隔离自身节点，不能改写用户已有 Compositor 输出链。

## 验证

`python tools/test.py` 运行纯时间测试、真实 bpy 集成测试、全新进程无插件重开测试。
`python tools/test_install.py` 构建、校验并在临时配置中安装/启用/创建/卸载扩展。
`tools/preview.py` 生成可重复的场景与预览，默认 Cycles CPU，可选择 Eevee。CI 固定 Blender 5.2.2，并校验官方二进制 SHA256。

版本 tag 触发同一 CI 验证，检查 manifest 版本一致，再由依赖测试成功的独立 job 发布 ZIP。PR 和测试 job 保持只读仓库权限。

## Flipbook 资产

控制器共享原生生命周期；私有四顶点 Mesh 与 Geometry Nodes 处理尺寸及生命周期隐藏。
Shader Nodes 夹取起止格后均匀选帧，使用图集左上行序，将基础 UV 缩放/偏移到目标格。
GPU/CPU 的 float32 边界误差用百万分之一周期的选帧容差修正；真实四色图集像素测试覆盖跳帧、速度、区间、循环和透明度。
复制私有节点树并重定向所有驱动器，图片保持共享；删除永不清理图片 ID。
JSON assets.image 为图片引用，导出优先写相对 JSON 目录的路径，导入相对此目录解析而非进程工作目录。
图片内容不内嵌到 JSON；生成图片未写磁盘时明确拒绝导出。原生 `.blend` 可由用户打包图片实现独立播放。

## Screen VFX

Screen Controller 使用同一 UUID、参数、时间、Action、预设协议；Layer 是其所属 Scene 合成树内的 Compositor Group Node。
Controller 的原生 Scene ID 指针标明归属；几何变换不影响屏幕效果。私有节点组使用低质量 Fog Glow 和带 alpha 的颜色覆盖。
Blender 5.2 使用 `Scene.compositing_node_group`、Group Output Image 及菜单输入形式的 Glare。
复用共享的 ShaderNodeMath / ShaderNodeValue；不使用旧版 Scene.node_tree 或旧版 Glare RNA 属性。

插入前验证输出和单用户树；现有用户节点保持原样。移除时用该层当前输入恢复所有 Image 下游分支，额外自定义输出有连接则拒绝删除。
共享节点组、缺失或歧义的 Layer、断开的输入均明确拒绝。仅在生成基础树结构/关键设置未改变时恢复无合成树状态。
记录首次插入前的 use_compositing，移除末层后恢复；合成设备保持用户选择。测试和发布预览显式设 CPU。
多个实例顺序串联，复制保留私有节点编辑和独立 Action、驱动器；保存后无插件亦可播放。

## 无状态粒子与私有材质引用

粒子由 Mesh Line 提供稳定 Index，确定性 Random Value 计算方向和变化，Set Position 根据当前 Motion Time 直接计算弹道。
Motion Time = Progress × Motion Seconds；播放时长与物理轨迹时长分离，重定时保持路径形状。末帧删除点，再实例化小型 Icosphere 并实现网格输出。
Count 在驱动器中限制到 [1, 2048]；默认 Low 使用 20 三角面的粒子网格，所有粒子共用实例内的私有材质。

复制建立对象、网格、材质和节点树的 ID 映射；除驱动目标外，原生节点的 ID 输入及修改器界面的 ID 输入也重定向到私有副本。
删除通过 bpy user_map 区分内部 Set Material 引用与外部用户引用，并先释放节点组再释放材质；外部共享仍拒绝删除。
真实双色粒子渲染与资源删除测试验证实例互不串色、无私有材质残留。该规则同时用于 Mesh / Shader / Flipbook。

UUID 还用于发现手动编辑中从对象上拆下的生成资产。材质释放前复查真实 datablock 消费者，处理 5.2 移除修改器 ID 输入后可能残留的引用计数；保留 Fake User / Extra User 和所有实际外部消费者。

### Sampled Ribbon Trail (asset v1)

`trail.ribbon` separates explicit authoring-time sampling from stateless native playback.
Sample a bounded, uniformly spaced frame range into a private paired-vertex Mesh, restoring scene frame/subframe in `finally`.
Object origins and evaluated pose-bone heads use world space; the initial controller is identity.
No source Action is copied or mutated. Source Object ID and bone/range metadata are optional rebake inputs, never playback dependencies.
Geometry Nodes clamp each sample index into a moving temporal window, Sample Index and linearly interpolate center/side fields, then offset width.
This preserves sampled variable-speed timing rather than converting it to arc-length timing. The common half-open lifetime applies.
Rebake replaces only an owned, unshared mesh after successful sampling, converting world points to current layer-local coordinates.
Native node edits survive; manual path edits are replaced only by explicit Rebake. JSON presets reject this module until path assets have a supported schema.

### Native spatial binding

`binding.py` adds one opt-in Child Of constraint with an evaluated target inverse, preserving the current world pose.
Targets and optional pose bones remain external native ID references; duplication keeps targets and copies constraints.
Known parenting, constraint (including pose bone), and object driver target dependencies are traversed before mutation.
Managed constraint name is persisted on the controller; ambiguous/renamed constraints are refused rather than guessed.
Unbind retains the evaluated pose, refusing additional constraints or transform/constraint animation that cannot be solved without baking.
Layered Action/NLA and driver paths for custom ID parameters are safe to retain. Screen controllers reject spatial binding.
No runtime handlers or new persistence schema are needed. Arbitrary user Geometry Nodes dependency cycles are outside the dependency preflight.

### User parameter preset library

`library.py` is a bpy-free filesystem boundary over validated v2 snapshots. UUID filenames avoid name collisions; rename uses atomic preset writes.
All selected keys are confined to a single directory and symlinks rejected. Scans are capped at 256 JSON files and report invalid entries separately.
`library_ui.py` maintains a WindowManager UIList refreshed only by explicit operations. It never scans from panel draw or frame handlers.
Blender's user DATAFILES path owns the durable library, independent of install versions and scene data. Deletion is explicit, file-only and not Blender Undo.
Material images remain external resources; failed instantiation never edits the preset. Native trail meshes, bindings, Actions and node edits are outside parameter snapshots.
