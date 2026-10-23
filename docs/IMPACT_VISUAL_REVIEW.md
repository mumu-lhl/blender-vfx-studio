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

实际从 v0.21.1 发布 examples ZIP 取出的旧 Impact 已载入、保存参数和复制，粒子保持版本 1。新版 examples ZIP 已在无插件进程检查三项资产、时间边界及嵌入预览。三平台 CI 和发布包复核尚待完成；本记录不会以本地检查代替这些结果。
