# 原生效果入门库

这是独立的示例资产包，不是插件安装包。先安装同版本的 Blender VFX Studio，再把 examples ZIP 解压到一个普通文件夹。
在 Preferences → File Paths → Asset Libraries 添加这个文件夹，然后在 Asset Browser 选择它。
选中效果，在右侧 Blender VFX Studio 面板点击 **Load VFX with New ID**；不要用普通拖放代替，以免重复实例编号。
也可以在 VFX 侧栏用 Load Complete Effect 选择某个 .blend。

所有效果从第 1 帧播放，默认不循环。载入保留时间和变换，不自动放到当前帧或 3D Cursor；选择控制器后可修改 Start、Duration、Speed 和 Loop。

**Energy Charge（48 帧）** 用两层细环、球面护盾和低数量的连续粒子组成蓝色蓄力效果。它有 4 个独立效果层；在组合面板选择成员后可以分别修改颜色、半径、发射率等。

0.22.2 候选把两层环和球壳的 Fade 改为 1，并在这三层的私有材质中使用 Blended，改善末段突然消失和低采样 Eevee 的颗粒。旧文件继续保留原参数与材质；不会在载入时自动覆盖你的编辑。检查方法见 [充能记录](CHARGE_VISUAL_REVIEW.md)。
粒子在控制器局部空间运动，移动整体会连同已出生的粒子移动，不保留角色走过的世界轨迹。

**Impact Burst（24 帧）** 组合白色短闪、12 个橙色定向尖片、较暗的侵蚀冲击波和 18 个细小余烬，共 4 层。短闪先消失，冲击波随后断开，尖片逐渐缩短。修改环的 Expansion 控制扩散距离；修改粒子的 Stretch / Planar / Motion Ease 调整尖片造型、散射平面和减速。组合 Duration 调整整体播放速度；Ungroup All 可拆开全部层。

**Arc Slash（18 帧）** 是单层紫色程序化刀光。Arc 调整弧度，Width 调整宽度，Spin 调整生命周期旋转；它不需要角色动画或预先采样路径。

全部使用 Low 质量，保留原生对象、材质和 Geometry Nodes，可以继续编辑或保存为自己的完整效果。副本使用 VFX Duplicate，删除使用 VFX Delete。
示例无需外部贴图、角色或缓存；不加载插件也能播放，继续使用侧栏创作需要启用插件。

资产缩略图由 Cycles CPU 渲染；仅 Energy Charge 加入额外的 Screen 辉光，Arc Slash 和 Impact Burst 不加辉光。相机、背景、合成辉光和用于生成预览的图片不会进入效果资产；载入不会改动你的场景合成链。
想获得相近的发光外观，可主动点击 Add Screen VFX；没有辉光时，原生发光材质仍然正常显示。预览不代表集成显卡的视口帧率保证。

从源码重新生成：

```sh
blender -b --factory-startup --python-exit-code 1 --python tools/build_examples.py
```

脚本只接受全新后台进程，不允许打开生产项目；输出 3 个 .blend 到 dist/examples/，并生成独立版本 ZIP。
不删除目录中其他文件。网格、节点、参数和嵌入预览均可重建；Blender 文件会包含新生成的内部编号，因此不保证跨次构建的二进制完全相同。

Arc Slash 已使用资产版本 2 的分层刀光，缩略图展示第 5 帧峰值，不加辉光。它与直接创建的新版刀光相同，只将播放时长设为 18 帧；Attack、Motion Ease、Core Width、Afterimage、Streaks 和 Breakup 等仍可编辑。原有版本 1 的文件不会自动换成新材质。高清检查见 [视觉记录](https://github.com/mumu-lhl/blender-vfx-studio/blob/main/docs/VISUAL_REVIEW.md)。

Impact Burst 与侧栏直接创建的效果使用同一接口和默认参数，缩略图展示第 5 帧。高清三阶段和实际看图范围见 [打击爆发视觉记录](https://github.com/mumu-lhl/blender-vfx-studio/blob/main/docs/IMPACT_VISUAL_REVIEW.md)。
