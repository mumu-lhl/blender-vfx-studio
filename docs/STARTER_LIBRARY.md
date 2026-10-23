# 原生效果入门库

这是独立的示例资产包，不是插件安装包。先安装同版本的 Blender VFX Studio，再把 examples ZIP 解压到一个普通文件夹。
在 Preferences → File Paths → Asset Libraries 添加这个文件夹，然后在 Asset Browser 选择它。
选中效果，在右侧 Blender VFX Studio 面板点击 **Load VFX with New ID**；不要用普通拖放代替，以免重复实例编号。
也可以在 VFX 侧栏用 Load Complete Effect 选择某个 .blend。

所有效果从第 1 帧播放，默认不循环。载入保留时间和变换，不自动放到当前帧或 3D Cursor；选择控制器后可修改 Start、Duration、Speed 和 Loop。

**Energy Charge（48 帧）** 用两层细环、球面护盾和低数量的连续粒子组成蓝色蓄力效果。它有 4 个独立效果层；在组合面板选择成员后可以分别修改颜色、半径、发射率等。
粒子在控制器局部空间运动，移动整体会连同已出生的粒子移动，不保留角色走过的世界轨迹。

**Impact Burst（24 帧）** 组合橙色扩散环与 40 个一次出生的粒子。修改环的 Expansion 控制扩散距离，修改粒子的 Velocity / Gravity / Motion Seconds 调整弹道；组合 Duration 调整整体播放速度。

**Arc Slash（18 帧）** 是单层紫色程序化刀光。Arc 调整弧度，Width 调整宽度，Spin 调整生命周期旋转；它不需要角色动画或预先采样路径。

全部使用 Low 质量，保留原生对象、材质和 Geometry Nodes，可以继续编辑或保存为自己的完整效果。副本使用 VFX Duplicate，删除使用 VFX Delete。
示例无需外部贴图、角色或缓存；不加载插件也能播放，继续使用侧栏创作需要启用插件。

资产缩略图由 Cycles CPU 渲染，并加入了额外的 Screen 辉光。相机、背景、合成辉光和用于生成预览的图片不会进入效果资产；载入不会改动你的场景合成链。
想获得相近的发光外观，可主动点击 Add Screen VFX；没有辉光时，原生发光材质仍然正常显示。预览不代表集成显卡的视口帧率保证。

从源码重新生成：

```sh
blender -b --factory-startup --python-exit-code 1 --python tools/build_examples.py
```

脚本只接受全新后台进程，不允许打开生产项目；输出 3 个 .blend 到 dist/examples/，并生成独立版本 ZIP。
不删除目录中其他文件。网格、节点、参数和嵌入预览均可重建；Blender 文件会包含新生成的内部编号，因此不保证跨次构建的二进制完全相同。
