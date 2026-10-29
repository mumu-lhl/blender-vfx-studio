# 持续火焰的分叉与热流检查

这轮修改真实 Fire 生成器，目标是减少中上部完整的平滑大面，让火舌有持续向上生长、分开和断裂的变化。角色、动作、相机、灯光、粒子数量及发光强度保留。图像为 Blender 5.2.2、960×540、Eevee 16 samples、AgX，无额外辉光。

![同一阶段的分叉：第 36 帧](images/fire-forks-after-36.png)

## 画面原因与原生节点

原火舌都是连续收尖的封闭形状。宽窄与弯折能让它们摆动，但不会产生真正分叉；高度渐变和宽噪声也容易在中段保留大块相似颜色。

两根主火舌现在由共享下部接到错开的上部双尖。各支沿同一 Flow Speed 时钟错相生长，Geometry Nodes 控制伸长和展开，Shader Nodes 在重置前先侵蚀断开。单纯同时伸长会像固定叉角，整支透明淡出则会留下半透明叶片，因此用生长与侵蚀共同完成交接。

材质保留原来的热色色带，加入沿流向上卷的窄冷缝，区分相邻热流；没有增加发光。原生 **Fork Spread** 调整展开范围，**Flow Seam Contrast** 调整内部冷缝，常用宽高、Flow Speed、Curl、颜色和生命周期保持原有入口。共享下部与各支使用短距离相交，不依赖布尔运算或逐帧 Python。

## 已查看的画面与边界

已实际读取基线第 36／48 帧与当前第 36／40／48 帧高清角色图。中上部有不同高度的分叉和缺口，完整大面减少，尖端不再固定地同时伸长；底部亮色团块仍偏圆，整体仍有片状边缘。没有声称达到成熟游戏火焰品质。

[36 前](images/fire-forks-before-36.png) · [36 后](images/fire-forks-after-36.png) · [40 后](images/fire-forks-after-40.png) · [48 前](images/fire-forks-before-48.png) · [48 后](images/fire-forks-after-48.png)。图片直接复制自渲染，没有裁切或调色。明暗／远景、整段隔帧、施法上下文与实测成本仍在补齐；**未观看实时播放，PR 保持草稿。**

参考的用途与原作方法见 [参考区分](LIBRARY_REFERENCE_STUDY.md)。本轮实际查看了原作者成片 GIF 的八张样本：可见错相运动与变化的边界，但其 HDR、辉光和纹理也影响了观感，不能当作本项目实现或验收结果。

## 功能检查与复现

8 项火焰、14 项艺术控制和 22 项完整资产检查通过，包含停止流动、实际热缝像素、分叉范围不改变共享下部、完整资产节点编辑与独立复制。无插件顶点回放与八套完整资产回放通过。高清原生重渲染仍在运行；测试通过不代表艺术验收。

```sh
LP_NUM_THREADS=2 blender -b -t 2 --factory-startup --disable-autoexec --python-exit-code 1 --python tools/fire_preview.py -- --frames 36 40 48
```

使用 `--dark`、`--far` 对照，或 `--sequence` 渲染全部 72 帧。完整施法使用 `tools/spell_preview.py`。图像、批次与源码摘要见 [检查清单](images/fire-forks-samples.json)。工作由 [#184](https://github.com/mumu-lhl/blender-vfx-studio/issues/184) 跟踪，整体品质见 [#89](https://github.com/mumu-lhl/blender-vfx-studio/issues/89)。
