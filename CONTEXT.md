# 领域概念与约定

- **Effect**：具有稳定 UUID 的一个特效实例，不等同于对象名。
- **Controller**：Empty，拥有实例参数、可关键帧化的原生 ID 属性和变换。
- **Layer**：一个实例内的原生对象；当前是 Mesh + Material + Geometry Nodes。
- **Module**：效果生成能力，例如 `mesh.ring`；七大 VFX 类别是方向，不要求每类一个基类。
- **Preset**：模块与参数的创建快照。内置 Shockwave / Energy Ring 及用户 JSON 保存/加载可用。预设不包含节点拓扑、Action、UUID、变换或开始帧；加载以当前帧为起点。
- **Schema version**：实例持久化结构版本，当前为 1。
- **Preset format version**：JSON 参数快照协议版本，当前导出为 2；格式 1 环形预设迁移为 2，未知版本拒绝。
- **Asset version**：模块生成节点/几何的资产协议版本，当前 ring / atlas / screen / burst 均为 1。
- **Ownership**：`vfx_id` 标记资源归属，`vfx_role` 区分 controller/layer；名称可任意修改。

## 时间

单位为帧，支持子帧。`elapsed = (frame - start) * max(speed, .001) / max(duration, 1)`。
非循环时 progress 为 elapsed 限制到 [0, 1]，有效区间为 `[start, start + duration/speed)`。
循环时 progress 为 `elapsed - floor(elapsed)`，start 之前仍隐藏。环在无效时间从求值几何中移除。

speed 仅允许正数；speed=1 时 duration 是生命周期帧数。当前不提供倒放语义或秒制转换。
参数可随帧关键帧化；动画 start/duration/speed 会直接改变当前帧的计算结果，不积累历史时间。

`radius` 为出生时外半径，`expansion` 为一个周期增加的半径，`width` 为径向宽度。
内半径限制为 .001；宽度超过当前半径时接近实心环，不产生负半径。
RGB 为线性颜色分量；dissolve=1 完全透明，fade=1 在生命周期末淡出，fade=0 保持不透明度。
Emission 亮度不等同于辉光；辉光需要用户自己的 Compositor，目前插件不修改它。

## 状态

当前 ring / atlas / screen / burst 均为无状态函数：同一场景参数和帧产生同一几何结果，任意帧预览不需要预热或缓存。
未来模拟模块需区分预览、已烘焙、失效缓存；保存重开后必须能解释其状态，不能默默使用过期缓存。

## 图集

图集左上格编号 0，先向右再向下；First / Last 为包含端点的范围。
First 限制到 [0, rows×columns−1]，Last 限制到 [First, rows×columns−1]。
一生均匀播放此闭区间，选帧为 floor((progress+1e-6)×格数)，并限制到末格；容差只用于选帧，不修改生命周期。
格数及边界为整数，网格最大 256×256；图片来源支持 FILE / GENERATED 静态图，不支持电影、序列或 UDIM。
图片是用户资源，可在原生 `.blend` 中打包；JSON 只保存本地路径，不执行脚本，也不读取远程 URL。

## 屏幕合成

Screen Layer 是所属 Scene 的合成节点，不是 Mesh 子对象；Controller 的 vfx_scene 为原生 Scene ID 引用。
Strength 为生命周期内的辉光强度；Flash 为出生时全屏颜色覆盖，实际系数为 Flash × Active × (1−Progress×Fade)。
结束后 Glare Strength 与 Flash 都为 0，原图透传；默认循环且 Flash=0，避免创建时出现白屏。
多个 Screen Layer 按输出链顺序叠加；Duplicate 使用当前场景作为目标，Delete 只处理控制器记录的所属场景。

## 粒子爆发

整组粒子在 Start 出生，粒子 ID 为原生点 Index；Count 不超过 2048，Seed 决定可重复的方向和变化。
Motion Time = Progress × Motion Seconds；位置为 Direction × (Spawn Radius + Varied Velocity × Motion Time) − (0,0,Gravity×Motion Time²/2)。
Motion Seconds 使用轨迹秒，Duration 使用播放帧；修改帧率不改变这两个参数的数值语义。
Fade 在此模块表示尺寸缩减而非透明度；一个周期结束后全体消失，循环重新从出生状态开始。
用户编辑的参数是当前帧的输入，不是模拟历史；连续发射、碰撞和缓存属于后续 Simulation/Particle 功能。
