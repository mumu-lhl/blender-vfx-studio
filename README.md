# Blender VFX Studio

**为二次元 3D 角色动画制作可编辑特效。** 在 Blender 中创建刀光、命中爆发、充能等效果，调整造型、颜色和节奏，再组合成完整技能。

目标版本为 **Blender 5.2 LTS**，优先 Eevee，同时兼容 Cycles。效果使用 Blender 原生网格、材质、几何节点和动画，保存后即使没有安装插件，也能继续播放、渲染和编辑。

> **项目正在开发，尚未正式分发。** 当前功能请使用源码构建，或下载成功的开发构建包。

[下载开发包](https://github.com/mumu-lhl/blender-vfx-studio/actions/workflows/ci.yml) · [完整入门库](docs/STARTER_LIBRARY.md) · [详细使用指南](docs/USAGE.md) · [开发进度](ROADMAP.md)

## 可以做什么

| 功能 | 适合的用途 |
| --- | --- |
| Mesh / Shader VFX | 刀光、冲击波、能量环、溶解与发光护盾 |
| Particle VFX | 一次爆发或持续发射的粒子，独立调整方向、形状和寿命 |
| Trail VFX | 采样武器、对象或骨骼运动，生成可编辑的轨迹刀带 |
| Flipbook VFX | 播放图集或连续图片，制作 Sprite 特效 |
| Screen VFX | 在合成中添加辉光和闪光 |
| Simulation VFX | 制作原生 Cloth 布面运动，烘焙后独立播放 |
| 组合与绑定 | 统一调整多层时间、绑定角色、复制和保存完整效果 |

**艺术表现优先。** 有价值的几何、粒子和材质复杂度可以换取更好的画面。质量档和实测开销用于帮助选择，不要求每套效果都低成本，也不用顶点数代表性能。

## 下载与安装

开发包的 ZIP 按用途区分：

| 文件 | 用途 |
| --- | --- |
| `blender-vfx-studio-版本.zip` | 安装插件 |
| `blender-vfx-studio-examples-版本.zip` | 完整效果资产库，解压后使用 |
| `blender-vfx-studio-previews-版本.zip` | 预览图片，解压后浏览，不用于安装 |

1. 在 [开发构建页面](https://github.com/mumu-lhl/blender-vfx-studio/actions/workflows/ci.yml) 打开最近成功的 main 构建，下载 `blender-vfx-studio-extension` 附件，解压外层 ZIP 后取出插件安装包。
2. 在 Blender 打开 **Edit → Preferences → Get Extensions**。
3. 在右上角菜单选择 **Install from Disk**，选中安装包并启用。
4. 回到 3D 视图，按 **N**，打开 **VFX** 标签页。

**安装请选择插件 ZIP 本体。** GitHub 的源码 ZIP 和 Actions 附件外层 ZIP 均不能直接作为插件安装。

## 第一个效果

### 从基础效果开始

1. 在 VFX 面板点击 **Create Mesh VFX**。
2. 选择 **Arc Slash**、**Impact Burst**、**Shockwave** 或 **Energy Ring**，再选择质量。
3. 切换到 **Material Preview** 或 **Rendered**，播放时间轴。
4. 修改颜色、尺寸和时间；数值可右键选择 **Insert Keyframe**，颜色使用选择器旁的菱形插入关键帧。

效果在 **3D Cursor** 处创建，以当前帧开始。移动、旋转或缩放 Empty 控制器，就能变换整个效果；选中网格也能查看所属效果的参数。

*看不到平面特效时，先检查默认 Cube 是否遮挡了它，以及当前帧是否在效果的播放区间内。*

### 载入完整入门资产

1. 下载并解压 examples ZIP。
2. 在 **Preferences → File Paths → Asset Libraries** 添加解压后的文件夹。
3. 打开 **Asset Browser**，选择效果。
4. 在右侧 **Blender VFX Studio** 面板点击 **Load VFX with New ID**。

也可以在 3D 视图的 VFX 面板点击 **Load Complete Effect**，选择某个效果 `.blend`。

**通过插件按钮载入，才能为每个实例分配独立编号。** 普通拖放或 Append 不会更新编号。载入保留资产原来的开始帧和位置，之后可以移动控制器、修改 Start。

## 完整资产库

| 效果 | 主要用途 | 编辑特点 |
| --- | --- | --- |
| Energy Charge | 汇聚、蓄力与释放 | 主体、进流、粒子分层控制 |
| Arc Slash | 弧形挥砍与残影 | 弧度、宽头尖尾与独立残弧 |
| Impact Burst | 命中爆发与冲击扩散 | 短闪、压力体积、喷射与余烬分层 |
| Lightning Strike | 分支落雷、短闪和逐次减弱的复击 | 分支形状、复击时序与线宽 |
| Dust Impact | 落地、踩踏的体积烟尘与碎屑 | 原生密度场、抬升与扩散 |
| Stylized Fire | 点燃、持续燃烧与断燃余烬 | 火舌、热色色带与上卷运动 |
| Character Dash Echoes | 捕获角色姿态，制作冲刺残影 | 捕获自己的角色姿态 |
| Calligraphic Magic Circle | 逐笔形成、转动与立体符记释放 | 笔画形成、反向转动与符记升起 |

main 现有 **8 种完整效果、18 个资产文件**。Energy Charge、Arc Slash、Impact Burst 提供 Low，其余五套各提供 Low / Medium / High；质量文件不作为额外种类。当前源码和开发构建包含这些资产。

新增效果的真实 Eevee 图像见 **[角色镜头图集](docs/LIBRARY_GALLERY.md)**。图集保留实际画面，包括远景弱细节等问题；不代表全部效果已达到商业成片品质。

参数、各层作用与实际观看范围见 [入门库指南](docs/STARTER_LIBRARY.md)。原生角色测试镜头、渲染图和检查限制见 [角色战斗记录](docs/CHARACTER_COMBAT_REVIEW.md)。生成视频和测试通过，不等同于已经完成艺术验收。

## 时间、组合与编辑

| 参数 / 操作 | 用法 |
| --- | --- |
| **Start** | 效果开始的帧 |
| **Duration** | 播放时长，以帧为单位 |
| **Speed** | 播放倍速，例如 2 表示快一倍 |
| **Loop** | 到周期末重新开始，不保证首尾无缝 |
| **Compose Selected VFX** | 把多个空间效果组合，统一移动和调整时间 |
| **Ungroup All** | 一次拆开全部层，保留拆分时的姿态和已求值时间 |

例如，Start=1、Duration=24、Speed=1 时，第 1–24 帧可见，第 25 帧隐藏；Speed=2 时，第 13 帧开始隐藏。以上采用默认场景时间映射。

侧栏按 **Shape / Motion / Color / Material / Dissolve** 分组。刀光可切换 **Clean / Stylized**，主体与锋刃可以分别换色；火焰主层提供 **Orange / Blue / Green** 热色色带。

调整面板参数不会重建节点，可以继续编辑网格、Geometry Nodes 和材质。组合中的各层也能单独修改。场景中复制、删除请使用 **VFX Duplicate / Delete**，相关操作支持 Undo。

## 保存与复用

| 要保留什么 | 使用方式 |
| --- | --- |
| 完整造型、节点、参数动画、各层关系、轨迹或已烘焙运动 | **Save Complete Effect**，保存为 `.blend` |
| 一组参数数值，用于重新创建基础模块 | **Save Parameters (JSON)**，保存为 JSON |

**手动改过节点，或使用完整入门资产时，优先保存完整效果。** 参数 JSON 不包含私有造型、手动节点和关键帧。静态贴图可打包进 `.blend`；图片序列仍需保留外部文件。

完整效果导出要求不依赖场景外部对象。已绑定角色时，可先在副本上处理需要保留的动画并解绑，再导出。具体操作和限制见 [详细指南](docs/USAGE.md#保存完整效果)。

## 了解更多

- [入门库指南](docs/STARTER_LIBRARY.md)：每套完整效果怎样使用和修改。
- [详细使用指南](docs/USAGE.md)：粒子、图集、轨迹、Cloth、绑定、组合和预设。
- [路线图](ROADMAP.md)：已完成、正在验证和下一步工作。
- [系统设计](DESIGN.md) / [概念与约定](CONTEXT.md)：开发者需要了解的结构和时间规则。
- [性能记录](docs/PERFORMANCE.md)：测量方式与设备限制；后台渲染耗时不是视口 FPS。

## 从源码构建

需要 Python 3.11+ 和 Blender 5.2.2；插件没有第三方运行依赖。

```sh
python tools/build.py
python tools/test.py
python tools/test_install.py
blender -b --factory-startup --python-exit-code 1 --python tools/build_examples.py
```

构建结果在 `dist/`，`BLENDER_BIN` 可指定 Blender 路径。未发布的构建也可从 [Actions](https://github.com/mumu-lhl/blender-vfx-studio/actions/workflows/ci.yml) 成功运行的 `blender-vfx-studio-extension` 附件下载。

许可证：**[GPL-3.0-or-later](LICENSE)**。测试角色的来源和独立许可见 [角色资产说明](assets/character-review/README.md)。
