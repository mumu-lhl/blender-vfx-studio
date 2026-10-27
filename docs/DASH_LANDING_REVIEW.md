# 冲刺、腾空与落地烟尘

这段 84 帧角色动作使用原生 Running_A 与 Jump_Full_Short 动作、根位移关键帧，以及实际 Dash Echoes 和 Dust Impact 生成器。三个残影捕获第 6、15、24 帧的姿态；求值后的脚部网格在第 44 帧回到地面，触发烟尘。效果可分别编辑，不依赖 Python 参与播放。

## 当前检查范围

已实际读取浅背景第 18、35、44、52 帧的 960×540 Eevee 图：残影随位置与姿态留下，腾空能辨认，落地后烟尘遮挡下半身，上半身仍清楚。残影在浅背景较淡，烟尘仍偏柔和；这些图不证明完整速度感已通过。两项接触／跳帧行为检查与新进程无插件回放通过。

完整隔帧、暗背景、远景、原生高清像素和实测成本检查尚未完成。**未观看实时播放，#156 保持开放。**

## 生成和编辑

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 -t 2 --python tools/dash_landing_preview.py -- --sampled
```

`--sampled` 渲染真实时间轴的隔帧图，并加入准确落地帧；不把缺少的帧复制成假视频。`--sequence` 可渲染全部 84 帧，`--dark`、`--far` 生成对照。输出保存在 `work/dash-landing-review/`，包括可编辑 `.blend`、接触轨迹和采样记录。

编辑两个 Dash Landing 组合控制器调整整体时间或位置；各层保留原生节点和材质。源角色根位移、NLA 动作条和脚部接触记录均保留在测试场景中。
