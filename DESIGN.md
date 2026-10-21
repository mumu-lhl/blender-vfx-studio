# 系统设计

目标：Blender 5.2 LTS 原生二次元动画 VFX；优先 Eevee，兼容 Cycles，低配置默认可用。
当前实现是完整的 Mesh + Shader 环形特效纵向切片，不是七类模块的空壳实现。

## 数据与边界

- `registry.py`：模块描述和内置预设。当前仅注册 `mesh.ring`，资产版本 1；预设是创建时的参数快照。
- `timing.py`：无 bpy 的时间约定及原生驱动表达式。
- `parameters.py`：无 bpy 的参数元数据；`presets.py`：纯 Python 参数预设校验和原子文件写入。
- `core.py`：实例创建、解析、复制、删除；所有权检查和参数预设实例化。
- `nodes.py`：原生 Geometry Nodes、Shader Nodes 和驱动器构建。
- `ui.py`：原生侧栏与 Undo 操作，委托 core；不承担节点构建。

Effect 对应一个 Empty Controller，一组原生 ID 属性控制一个或多个 Layer；当前实现一个 Mesh Layer。
每个实例具有 UUID 和私有网格、材质、Geometry Node Tree。Collection 仅负责组织；对象名和集合名不承担身份语义。
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
用户预设采用独立 JSON 格式 1，导入前校验完整字段、参数范围、有限数值、模块和资产版本。
64 KiB 有界读取；拒绝重复键；导出先验证，再以同目录临时文件原子替换，失败不损坏原文件。
预设保存参数快照，不保存时间起点、变换、UUID、Action 或自定义拓扑；载入创建新实例而不改写选中效果。
尚无历史格式，未来引入 schema 2 前必须增加逐版本迁移和历史固定样例测试。
目前不引入通用模块插件框架、专用节点编辑器、模拟管理器或资产数据库。

Particle / Flipbook / Trail 等新模块复用 Controller、时间约定和所有权；新增之前先形成真实 bpy 的可用切片。
Simulation 必须显式声明有状态，记录模拟区间、缓存版本、参数失效规则及烘焙状态，不能套用无状态任意帧承诺。
Screen VFX 必须主动启用并隔离自身节点，不能改写用户已有 Compositor 输出链。

## 验证

`python tools/test.py` 运行纯时间测试、真实 bpy 集成测试、全新进程无插件重开测试。
`python tools/test_install.py` 构建、校验并在临时配置中安装/启用/创建/卸载扩展。
`tools/preview.py` 生成可重复的场景与预览，默认 Cycles CPU，可选择 Eevee。CI 固定 Blender 5.2.2，并校验官方二进制 SHA256。
