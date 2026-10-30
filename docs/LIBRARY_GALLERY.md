# 特效的真实角色镜头

这里展示内置效果的实际角色渲染，来源包括 CI 和本地检查，均为 **960×540、Eevee、AgX、无额外辉光**。图片直接复制自渲染 PNG，没有调色、裁切或重绘；点击可查看原尺寸。单帧只说明当前画面，完整时序、隔帧观看范围与成本见各效果记录。

角色、地面、灯光和相机用于检查，**不包含在效果资产中**。残影本身包含已捕获的角色网格，也可用 Capture Dash Echoes 捕获自己的角色。测试角色来源及 CC0 许可见 [资产说明](../assets/character-review/README.md)。

## energy-charge

![Energy Charge：第 32 帧](images/charge-plasma-after-32.png)

向内流动的蓝色外圈围绕白热中心积蓄，随后沿剑刃收束。第 **32 帧**，本地角色镜头；[编辑、隔帧与实际检查](CHARGE_PLASMA_REVIEW.md)。前段中心仍弱，背侧转剑可能被角色遮挡，未观看实时播放。

## Arc Slash

![Arc Slash 与命中：第 49 帧](images/slash-plane-after-49.png)

刀光跟随当前剑刃所在的平面，保留主体与独立残影；此图同时包含充能释放和白色命中核。第 **49 帧**，本地角色镜头；[空间对齐与实际观看范围](SLASH_PLANE_REVIEW.md)。多层蓝片仍有明显重叠，未观看实时播放。

## Impact Burst

![Impact Burst：第 53 帧](images/impact-focus-after-53.png)

接触附近的翻卷压力面，配合较长的细喷射和稍后消散的余烬。第 **53 帧**，本地角色镜头；[同帧与动画抽帧检查](IMPACT_FOCUS_REVIEW.md)。压力面仍偏薄，远景细层较弱，未观看实时播放。

## lightning-strike

![Lightning Strike：第 8 帧](images/lightning-strike.png)

主干复击时，地表分叉电弧重新展开。第 **8 帧**，本地角色镜头；[同帧与动画抽帧检查](LIGHTNING_CONTACT_REVIEW.md)。远景第三次放电和细枝仍偏弱，未观看实时播放。

## dust-impact

![dust-impact：第 39 帧](images/dust-impact.png)

落地后的体积烟尘；主体不发光，需要场景灯光。 第 **39 帧**；[编辑与实际检查](DUST_REVIEW.md) · [原始 Actions 附件](https://github.com/mumu-lhl/blender-vfx-studio/actions/runs/40519038623)。

## stylized-fire

![stylized-fire：第 40 帧](images/stylized-fire.png)

从共享下部交替伸长的分叉与热流，尖端在断裂前先侵蚀。第 **40 帧**，本地角色镜头；[完整抽帧与实际检查](FIRE_FORK_REVIEW.md)。底部团块和局部薄边仍需改善，远景细余烬较弱。

## dash-echoes

![dash-echoes：第 18 帧](images/dash-echoes.png)

真实冲刺位移留下的透明姿态，随后腾空并接上落地烟尘。第 **18 帧**，本地角色镜头；[完整动作与实际检查](DASH_LANDING_REVIEW.md)。远景旧姿态仍偏淡，未观看实时播放。

## magic-circle

![magic-circle：第 40 帧](images/magic-circle.png)

保持阶段的主印和反转符文带；细笔画在远景较弱。 第 **40 帧**；[编辑与实际检查](MAGIC_REVIEW.md) · [原始 Actions 附件](https://github.com/mumu-lhl/blender-vfx-studio/actions/runs/40466594123)。

## 施法与火焰释放

![符记汇聚后点燃：第 62 帧](images/spell-transfer-after-62.png)

符记从施法位置向剑前汇聚，火焰开始接入。第 **62 帧**，本地角色镜头；[多阶段与原生节点检查](SPELL_TRANSFER_REVIEW.md)。聚拢线条仍有重叠，初生火焰仍偏片状，未观看实时播放。

## 复现图像

从全新克隆，在安装 Blender 5.2.2 后，使用对应脚本的 `--frames` 参数，例如：

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 -t 2 --python tools/fire_preview.py -- --frames 36
```

默认生成浅背景近景，`--dark` 和 `--far` 用于对照。输出在忽略版本管理的 `work/`，不会覆盖上述已记录图像。设备、Blender 或渲染器版本可能导致像素差异。充能的来源、帧位与摘要见 [角色衔接清单](images/combat-handoff-samples.json)，命中见 [焦点清单](images/impact-focus-samples.json)，其他五套见 [清单](images/library-gallery.json)；图片不作为插件运行依赖。
