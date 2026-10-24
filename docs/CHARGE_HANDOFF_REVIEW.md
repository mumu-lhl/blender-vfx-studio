# 从充能到命中的衔接检查

本场景复用真实 Energy Charge、Arc Slash、Impact Burst，以及 #69 的中性武器和靶体，不加辉光。它检查三个效果是否争夺焦点，以及切换时是否有明显空档；不是新的技能生成器，也没有重做角色动画。

充能从第 1 帧开始，Duration 设为 32，因此第 33 帧隐藏；挥斩在第 27 帧开始、39 帧隐藏，命中从 31 帧开始、55 帧隐藏。时间值使用现有控制器参数，原生武器关键帧整体后移 24 帧。场景以 24 fps 保存，镜头与效果尺寸沿用原战斗检查，不随背景改变。

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/charge_handoff.py
LIBGL_ALWAYS_SOFTWARE=1 EGL_PLATFORM=surfaceless blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/charge_handoff.py -- --engine BLENDER_EEVEE --light
```

结果在 `work/charge-handoff/cycles-dark/` 和 `work/charge-handoff/blender_eevee-light/`，每种条件有 17 张 960×540 PNG、原生场景和 `review-settings.json`。只有所有帧渲染并保存成功才写入记录。场景停在第 31 帧命中时刻，保存后无需插件即可播放。

实际查看了 Cycles 暗背景的第 1、7、13、19、25、26、27、28、29、30、31、32、33、37、45、55、60 帧；另读取软件 Eevee 亮背景的第 13、27、29、31、32、33 帧。充能中段有明确的蓝色主体；挥斩开始前它已经减弱。第 31 帧白色命中短闪与橙色尖片成为焦点，第 33 帧充能退出，刀光和打击层继续退场；第 37 帧主要保留尖片与破碎冲击波，45 帧只剩细余烬，55 和 60 帧无效果残留。亮背景上主体切换仍可读，但细轨道、刀光残影与余烬较弱。

这些抽查帧没有显示需要立刻修改真实生成器的新缺陷，因此本轮没有用演示场景美化替代资产修改。检查包含释放前后的相邻帧，但没有实时观看，也不覆盖全部 60 帧、真实角色动作、更多镜头距离或集成显卡帧率，不能称为完整战斗动画验收。

两个原生场景均在关闭自动执行、未导入插件的新进程中重渲染第 31 和 33 帧，PNG 所有通道与原图一致；第 60 帧所有带 VFX 标记的网格为空，武器与靶体仍存在。复核命令如下，将路径换为要检查的场景；软件 Eevee 仍需上面的环境变量。

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 work/charge-handoff/cycles-dark/handoff.blend --python tests/charge_handoff_reopen.py
```
