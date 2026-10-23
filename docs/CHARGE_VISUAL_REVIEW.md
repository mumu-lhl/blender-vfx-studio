# Energy Charge 的末段淡出

0.22.2 候选修复 [#76](https://github.com/mumu-lhl/blender-vfx-studio/issues/76)。旧入门资产的两层环 Fade=0.35，球壳 Fade=0；第 48 帧仍保留明显亮轮廓，第 49 帧生命周期结束时整体消失。修复把这三层的现有 Fade 参数改为 1，48 帧时长、层数、粒子预算和发光强度不变。

软件 Eevee 的 16 samples 实图还显示明显的透明颗粒，因此新建充能资产的三个私有材质改用 Blended。Cycles 与 Eevee 的主体和末段已分别在无插件进程重渲染，所有 PNG 像素通道与原图一致。普通 Ring、Shield 生成器及旧完整资产的参数、材质保持原样；实际 v0.22.0 示例载入并复制后仍保留旧值。

实际读取了 Cycles、软件 Eevee、亮背景 Cycles 的第 4、22、42、48、49 帧 960×540 PNG，并对比旧版末帧。环和球壳在后段逐渐变暗，Eevee 的连续轮廓比原来的颗粒透明更稳定，末帧只有很淡的残留，结束帧清空。回归检查要求第 48 帧的像素 RGB 总量低于第 22 帧的 20%，并确认几何直到生命周期结束才移除；旧值约为 94%，未达到该标准。

预览使用相同的相机和背景，不加辉光。16:9 画面使用 7.2 的相机可见宽度，避免直接沿用正方形缩略图构图而裁掉地面环。`--legacy` 只恢复旧 Fade 与透明模式，用于同条件对照，不是旧资产迁移。

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/charge_preview.py -- --legacy
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/charge_preview.py
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/charge_preview.py -- --engine BLENDER_EEVEE
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/charge_preview.py -- --light
```

Linux 无 GPU 时可加 `LIBGL_ALWAYS_SOFTWARE=1 EGL_PLATFORM=surfaceless`。结果在 `work/visual-charge/`，含五帧 PNG 和原生场景；CI 附件名为 `energy-charge-visual-review`。本次检查的是淡出和低采样透明，现有双环、球壳与外散圆粒的聚能造型、主次和连续节奏仍需继续改进。
