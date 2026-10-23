# Impact Burst 视觉检查

旧效果是同样明亮的粗圆环和圆粒，中心爆点不够明确。本轮改成四层：白色短闪确定命中位置，橙色长尖片强调放射方向，较暗冲击波扩张后被噪声侵蚀，较小余烬延迟消散。采用战斗特效常用的清晰焦点、快爆发和错峰消散原则，没有通过增加辉光掩盖轮廓。

用户在 Create Mesh VFX 中选择 Impact Burst 即可得到同一个四层组合。粒子增加 Shape、Stretch、Planar 和 Motion Ease；颜色、强度、速度、重力和时间仍由各层原生参数控制。冲击波的侵蚀驱动保存在私有材质中，跟随成员进度，整体重定时不会错位。完整效果导出保留节点编辑；单层参数 JSON 不保存手工节点修改。

## 实际看过的画面

2026-10-23，在 Linux Blender 5.2.2 中渲染并用图像查看工具读取了三阶段 960×540 PNG：第 2 帧出现、第 5 帧峰值、第 14 帧衰减。检查包括 Cycles CPU 24 samples、软件 Eevee，以及 Cycles 浅灰背景，共九张图；预览不加辉光、灯光或其他合成美化。

第一版尖片已改善方向感，但中心闪光消失过早，衰减仍留着完整圆环。修改后短闪持续 7 帧，冲击波随生命周期提高噪声阈值；最终峰值仍有小而亮的白色中心，冲击波比尖片暗，衰减时圆环已消失，只剩稀疏尖片和余烬。尖片从暗色尾部渐变到浅色前端，随轨迹切线转向。

最终 Eevee 与 Cycles 的主要轮廓接近。浅背景仍能辨认中心和长尖片，但微小余烬较难看清，不能保证所有背景上的对比。这次没有检查带角色的战斗镜头、Windows/macOS 实际视口或集成显卡帧率。静态关键帧也不能替代完整镜头的节奏检查，下一步优先验证刀光与命中效果的衔接。

入门库使用相同创建接口和参数；256×256 缩略图取第 5 帧且不加辉光。高清图独立生成，不以缩略图代替验收。

## 复现与验证

只在新的后台进程运行，脚本会建立空场景：

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py -- --engine BLENDER_EEVEE
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/impact_preview.py -- --light
```

结果在 `work/visual-impact/`，包括三阶段 PNG 和原生 .blend。`--legacy` 重建旧入门库的圆环和圆粒组合；新旧默认参数不同，这不是等参数性能对比。无 GPU 的 Linux 可以设置 `LIBGL_ALWAYS_SOFTWARE=1 EGL_PLATFORM=surfaceless` 使用 Mesa；Actions 显式安装 EGL/Mesa，并提供 `impact-burst-visual-review` 图片附件。

本地 152 项测试、15 个无插件重开进程、安装/卸载及 Ruff 已通过。新增检查覆盖尖片参数、旧版 JSON、实例隔离、四层生命周期、低质量顶点预算、整体重定时、完整资产导出与载入、Ungroup All、安全删除及 CPU 像素阶段变化。高清峰值另在关闭自动执行、不加载插件的新进程渲染，PNG 所有像素通道与原图完全一致。

实际从 v0.21.1 发布 examples ZIP 取出的旧 Impact 已载入、保存参数和复制，粒子保持版本 1。新版 examples ZIP 已在无插件进程检查三项资产、时间边界及嵌入预览。三平台 CI 和发布流程均通过，[v0.22.0 已发布](https://github.com/mumu-lhl/blender-vfx-studio/releases/tag/v0.22.0)。实际下载的两个 ZIP 通过 SHA256；扩展 ZIP 与对应标签全新克隆的构建逐字节一致，实际 examples ZIP 通过无插件检查。九张发布高清图的尺寸已核对，并直接读取发布的 Cycles 三阶段和 Eevee 峰值，层次与本地检查一致。

后续把刀光和爆发放进同一简易镜头的检查，见 [衔接记录](COMBAT_VISUAL_REVIEW.md)。

0.22.1 候选根据远景实图增厚短闪和主尖片、缩短短闪并提前侵蚀冲击波；没有改变强度、层数或资产结构。上述 7 帧短闪描述的是 v0.22.0；候选改为 6 帧。连续播放观感尚未验收，具体条件和限制见 [镜头记录](COMBAT_VISUAL_REVIEW.md)。

## 候选版后续：主尖片面色

[#71](https://github.com/mumu-lhl/blender-vfx-studio/issues/71) 为主尖片加入固定方向的亮面、暗面，并把 Size 从 0.085 调到 0.11、Stretch 从 5 调到 4。横向约宽三成，长度基本保持；粒子数、发光强度和四层时间安排不变。白色前端在面色之后混合，不会被暗面覆盖。只修改新建 Impact 的私有材质，普通 Burst 和旧完整资产不变。

已实际读取新版 Cycles 第 2、5、14 帧 960×540 PNG，以及软件 Eevee 近景、远景亮背景第 8、12、23 帧；也直接对比修改前后第 12 帧。近景尖片的橙色主体更厚，侧面有较暗的色带，白尖仍清晰；远景变化较小，主尖片尚可辨，微小余烬依然很弱。这次改进不代表所有背景、方向或连续播放均已验收。

Shader Editor 的 Side Contrast 可调明暗差异，Illustrated Light 的向量可改世界空间的面色方向；这是绘制风格的假定方向，不跟随场景灯光。改控制器颜色或 Emission 仍有效。面色节点和用户修改需用 Save Complete Effect 保存，单层参数 JSON 不保存它们。

本地 155 项测试、15 个无插件重开进程、安装/卸载和 Ruff 通过。新增像素检查将 Side Contrast 改为非默认值后导出、载入并复制，画面保持一致；重新上色也确实改变像素。Cycles 近景与 Eevee 远景亮背景的原生场景另在无插件进程重渲染第 8 帧，所有通道完全一致。新版示例 ZIP 已重建并通过无插件检查；实际 v0.22.0 示例仍保留旧参数。
