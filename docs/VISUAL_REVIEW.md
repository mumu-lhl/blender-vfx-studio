# Arc Slash 视觉检查

本轮先改刀光，Impact Burst 随后处理。复杂骨架扩展和跨平台 GUI 扩展暂缓；原有后台兼容性检查继续运行。

## 实际改变了什么

旧预览只有均匀发光的月牙。新版把视觉权重分给窄亮锋刃、渐变拉丝主体和两条较短、较暗的残影。
前端快速展开并收尖，挥斩随后减速；内侧和尾部先被侵蚀，最后只留下低亮细丝。这里采用的是战斗特效常用的焦点、主次和快入慢出原则，没有复制具体游戏资产。

所有变化都在新建的 Arc Slash 中，7 个新参数可以关键帧编辑。高清预览只将 Duration 设为 18 帧，使用固定相机和固定背景，不添加辉光合成、灯光美化或额外效果。
入门库使用同一创建接口和参数，并选择峰值作为缩略图；缩略图也不加辉光。

## 看过的实图和发现

2026-10-23，在 Linux Blender 5.2.2 中生成并通过图像查看工具逐张读取了 960×540 PNG：第 2 帧出现、第 5 帧峰值、第 11 帧衰减。
Cycles 使用 CPU、24 samples；另检查 Eevee 的三个阶段，以及 Cycles 浅灰背景的峰值和衰减。暗背景三阶段同时用于最终验收，浅背景用于检查轮廓的可辨识程度。

初版出现时前端像平切口，已改为随展开位置移动的尖端；初版衰减仍是一整条描边，已让后段侵蚀穿过锋刃。初版残影太像平行描线，已缩短并错开。
Eevee 的抖动透明在细线中产生颗粒，改为原生 Blended 透明后重渲染，已实际确认颗粒减轻且保留主体细节。

最终峰值能分辨浅色锋刃、紫色主体和较暗残影；衰减阶段的主体明显减薄、断裂，亮度也下降。浅背景上主体和锋刃仍可辨识，但暗残影较难看见，不能据此承诺所有角色背景都有同样对比。
本轮没有角色实战镜头、Windows/macOS 视口或集成显卡帧率验收；这些不作为本轮视觉交付的前置扩展。

发布页附带 `slash-cycles-appear.png`、`slash-cycles-peak.png`、`slash-cycles-decay.png`，每张均为 960×540。
标签流程还生成 Eevee 和浅背景三阶段图；PR 的 Linux Actions 提供 `arc-slash-visual-review` 下载包，可在合并前检查实际 PNG。

## 复现与数据验证

在全新克隆中运行，默认生成暗背景的 Cycles 三阶段；只在新的后台进程使用这些命令：

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/slash_preview.py
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/slash_preview.py -- --engine BLENDER_EEVEE
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/slash_preview.py -- --light
```

输出在 `work/visual-slash/`，包含 PNG 和可检查的原生 `.blend`。`--legacy` 可渲染版本 1 的默认效果作为旧结构参考；两版默认颜色、尺寸和亮度不同，不能把它当成等参数的性能比较。

本地完整 146 项测试、14 个无插件重开进程、安装/卸载和 Ruff 已通过。刀光的 8 项检查包含旧版预设重建、新版参数改变几何和像素、侵蚀和完全溶解、独立复制/载入及资源清理。
实际从 v0.20.0 发布包取出的旧刀光也已载入、保存参数和复制，仍保持版本 1。新版不自动重建旧文件的节点。

另外把高清预览保存后，关闭自动执行、不加载插件，在新进程渲染同一峰值，确认 PNG 所有像素通道与原结果完全一致。
实际生成的 examples ZIP 另在无插件进程检查三项资产、时间边界和嵌入预览。自动像素检查只验证外部行为，不替代上面的实际看图。
