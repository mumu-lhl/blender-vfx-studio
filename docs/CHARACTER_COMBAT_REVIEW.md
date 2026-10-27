# 角色战斗镜头

此镜头用于判断特效放进角色动作后是否成立。两名 KayKit CC0 低多边形角色使用原生骨架、蒙皮、持剑待机、挥剑和受击动作；来源与校验见 [角色资产说明](../assets/character-review/README.md)。它们能暴露遮挡和衔接问题，不能代替正式二次元角色的最终验收。

场景共 96 帧，24 fps。第 1–52 帧充能跟随剑身中部；第 37 帧开始挥剑动作，第 47 帧开始刀光，第 49 帧剑刃实际穿过防守角色变形网格并触发受击与爆发。刀光的位置与旋转保存为普通关键帧；命中点来自剑段与网格的求交。第 80 帧进入无特效的恢复阶段。几何和材质来自当前真实生成器，镜头脚本不替换它们的节点或增加辉光。

## 重建与检查

在仓库根目录运行以下命令。Linux 无独显环境可设置 `LIBGL_ALWAYS_SOFTWARE=1 EGL_PLATFORM=surfaceless LP_NUM_THREADS=2`。生成物保存在忽略的 `work/character-combat/`，不写入已有工程。

```bash
blender -b --factory-startup --disable-autoexec --python-exit-code 1 -t 2 --python tools/character_combat.py -- --sequence
blender -b --factory-startup --disable-autoexec --python-exit-code 1 -t 2 --python tools/character_combat.py -- --far --frames 16 32 48 49 53 61 80
blender -b --factory-startup --disable-autoexec --python-exit-code 1 -t 2 --python tools/character_combat.py -- --dark --frames 16 32 48 49 53 61 80
blender -b --factory-startup --disable-autoexec --python-exit-code 1 -t 2 --python tools/character_combat.py -- --reverse --frames 16 32 48 49 53 61 80
blender -b work/character-combat/light-near/character.blend --disable-autoexec --python-exit-code 1 -t 2 --python tests/character_visual_reopen.py
blender -b work/character-combat/light-near/character.blend --disable-autoexec --python-exit-code 1 -t 2 --python tools/character_performance.py
python tools/character_review.py work/character-combat
```

软件 Mesa 驱动在原生检查后的退出路径存在已记录的缓存问题；CI 只对两个重开文件的进程设置 `MESA_SHADER_CACHE_DISABLE=true`，仍要求正常退出。检查记录包含生成器、场景代码与资产 SHA256；渲染过程中修改这些文件会使检查失败。

打开生成目录的 `index.html` 查看完整视频、隔帧解码图和各机位关键帧；也可以关闭自动执行后打开 `character.blend`。贴图打包在文件内，骨架、原生动作轨道（NLA）、绑定、关键帧和特效节点均保留。`Combat VFX • toggle for comparison` 集合可以关闭全部特效。该文件是检查场景，不是插件安装包。

`performance.json` 比较同场景开启／关闭特效的后台求值与渲染实际花费的时间。求值先预热三轮，再测量三种阶段各九次；渲染保留两个预热样本，再交错测量三个匹配阶段。记录 CPU 配额、线程、实际 OpenGL 渲染器、采样与分辨率。数字不能换算成交互视口帧率，也不代表独立显卡性能；顶点数不作为通过标准。

## 实际检查与结论

第一轮功能提交 `ce49c1f` 的六项 CI 全部通过。已下载并校验 [Actions 40368155631](https://github.com/mumu-lhl/blender-vfx-studio/actions/runs/40368155631) 的 `character-combat-review` 附件（ID 12676261244），读取完整 96 帧、4 秒视频的全部 48 张隔帧解码图，以及远景、暗背景和反向机位各七张阶段图，并单独读取对应的 960×540 PNG。未实际观看 24 fps 连续播放。原生重开在命中、早期充能和积蓄三帧逐像素一致，角色动作正常，恢复帧特效清空；本地和 CI 均正常退出。

画面尚未通过艺术验收。充能从早期到积蓄的变化较弱，焦点相对剑身偏小，外围碎片的权重较高；远景中心尤其不清楚。正反机位证明角色确实遮住了部分主体。命中时紫色刀面横跨角色，橙色压力主体难以成为第一焦点，末段主要剩下零散余烬。恢复阶段没有残留几何。

检查也发现了镜头脚本的错误：为对齐剑身而把 Spin 设为零，同时关闭了原生残影的方向与角度分离。修正后保留原生 Spin，只用控制器关键帧抵消主刀面的旋转；实际第 49、53 帧已读取，残影分离后命中主体更容易看清，刀光仍偏宽。另将充能持续时间从 48 延长到 52 帧，保留接触前的末段充能。修正提交 `d883fc5` 的六项 CI 已全部通过；已下载并校验 [最终 Actions 40448455312](https://github.com/mumu-lhl/blender-vfx-studio/actions/runs/40448455312) 的附件 12711708371，再读全部 48 张视频隔帧图、三组机位阶段图和高清第 47／53 帧。两层残影有角度分离，第 47 帧仍可见内核；三帧原生像素一致且进程正常退出。镜头必要验证完成，艺术问题继续保留。

本地 Blender 5.2.2、两线程、2 CPU 配额、Mesa 25.0.7 llvmpipe 上，无特效的后台求值中位数为 0.86 ms，开启后为 10.90 ms（27 个有效样本，p95 为 0.88 / 15.77 ms）。匹配渲染如下，单位为秒，分辨率 960×540、Eevee 16 samples、AgX、无辉光：

| 阶段帧 | 无特效 | 有特效 |
| --- | ---: | ---: |
| 32 积蓄 | 14.84 | 29.19 |
| 53 命中 | 17.01 | 44.55 |
| 61 消散 | 15.66 | 42.19 |

只有第 32 帧在同进程内做了两次渲染预热；另外两阶段可能包含首次材质准备成本，不能把这些单次结果当作稳定平均值或 p95。CI 的 Mesa 25.2.8 llvmpipe 也测得明显开销：求值中位数 0.69 / 7.37 ms，三个有特效渲染为 31.12 / 44.33 / 42.00 秒，无特效约 14.82 秒。顶点较少并不意味着这套材质与透明叠加便宜；这些结果均不是视口帧率。

修正后 CI 的求值中位数为无特效 0.67 ms／有特效 6.26 ms；三个匹配阶段的渲染约为 14.55–14.61 秒／30.89–44.15 秒。条件和预热限制同上，不据此宣称交互性能通过。

按最新优先级，转向 [#138](https://github.com/mumu-lhl/blender-vfx-studio/issues/138) 扩充完整效果库。#137 的充能原型已保存到功能分支，但造型仍偏平，暂缓合并；不继续围绕旧三套效果微调。正式二次元角色、实时播放和交互视口性能仍未验收；整体 [#89](https://github.com/mumu-lhl/blender-vfx-studio/issues/89) 保持开放。
