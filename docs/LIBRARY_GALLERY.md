# 特效的真实角色镜头

这里展示内置效果的实际角色渲染，来源包括 CI 和本地检查，均为 **960×540、Eevee、AgX、无额外辉光**。图片直接复制自渲染 PNG，没有调色、裁切或重绘；点击可查看原尺寸。单帧只说明当前画面，完整时序、隔帧观看范围与成本见各效果记录。

角色、地面、灯光和相机用于检查，**不包含在效果资产中**。残影本身包含已捕获的角色网格，也可用 Capture Dash Echoes 捕获自己的角色。测试角色来源及 CC0 许可见 [资产说明](../assets/character-review/README.md)。

## energy-charge

![Energy Charge：第 36 帧](images/energy-charge.png)

卷曲能量片围出中心，外围进流和粒子承担汇聚方向。第 **36 帧**，本地同源角色镜头；[编辑与实际检查](CHARGE_HIERARCHY_REVIEW.md)。远景细亮带仍弱，未观看实时播放。

## lightning-strike

![lightning-strike：第 4 帧](images/lightning-strike.png)

分支落雷；细枝与接触火花在远景偏弱。 第 **4 帧**；[编辑与实际检查](LIGHTNING_REVIEW.md) · [原始 Actions 附件](https://github.com/mumu-lhl/blender-vfx-studio/actions/runs/40454784154)。

## dust-impact

![dust-impact：第 39 帧](images/dust-impact.png)

落地后的体积烟尘；主体不发光，需要场景灯光。 第 **39 帧**；[编辑与实际检查](DUST_REVIEW.md) · [原始 Actions 附件](https://github.com/mumu-lhl/blender-vfx-studio/actions/runs/40519038623)。

## stylized-fire

![stylized-fire：第 36 帧](images/stylized-fire.png)

不等高外焰与热芯；中段仍有较完整的大火面。 第 **36 帧**；[编辑与实际检查](FIRE_REVIEW.md) · [原始 Actions 附件](https://github.com/mumu-lhl/blender-vfx-studio/actions/runs/40461231445)。

## dash-echoes

![dash-echoes：第 19 帧](images/dash-echoes.png)

真实位移留下的角色姿态；较旧残影在浅背景较淡。 第 **19 帧**；[编辑与实际检查](DASH_REVIEW.md) · [原始 Actions 附件](https://github.com/mumu-lhl/blender-vfx-studio/actions/runs/40465954679)。

## magic-circle

![magic-circle：第 40 帧](images/magic-circle.png)

保持阶段的主印和反转符文带；细笔画在远景较弱。 第 **40 帧**；[编辑与实际检查](MAGIC_REVIEW.md) · [原始 Actions 附件](https://github.com/mumu-lhl/blender-vfx-studio/actions/runs/40466594123)。

## 复现图像

从全新克隆，在安装 Blender 5.2.2 后，使用对应脚本的 `--frames` 参数，例如：

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 -t 2 --python tools/fire_preview.py -- --frames 36
```

默认生成浅背景近景，`--dark` 和 `--far` 用于对照。输出在忽略版本管理的 `work/`，不会覆盖上述已记录图像。设备、Blender 或渲染器版本可能导致像素差异。充能的来源、帧位与摘要见 [充能清单](images/charge-hierarchy-samples.json)，其他五套见 [清单](images/library-gallery.json)；图片不作为插件运行依赖。
