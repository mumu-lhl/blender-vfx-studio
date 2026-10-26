# 角色战斗镜头

此镜头用于判断特效放进角色动作后是否成立。两名 KayKit CC0 低多边形角色使用原生骨架、蒙皮、持剑待机、挥剑和受击动作；来源与校验见 [角色资产说明](../assets/character-review/README.md)。它们能暴露遮挡和衔接问题，不能代替正式二次元角色的最终验收。

场景共 96 帧，24 fps。第 1–48 帧充能跟随剑身中部；第 37 帧开始挥剑动作，第 47 帧开始刀光，第 49 帧剑刃实际穿过防守角色变形网格并触发受击与爆发。刀光的位置与旋转保存为普通关键帧；命中点来自剑段与网格的求交。第 80 帧进入无特效的恢复阶段。几何和材质来自当前真实生成器，镜头脚本不替换它们的节点或增加辉光。

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

打开生成目录的 `index.html` 查看完整视频、隔帧解码图和各机位关键帧；也可以关闭自动执行后打开 `character.blend`。贴图打包在文件内，骨架、NLA 动作、绑定、关键帧和特效节点均保留。`Combat VFX • toggle for comparison` 集合可以关闭全部特效。该文件是检查场景，不是插件安装包。

`performance.json` 比较同场景开启／关闭特效的后台求值与渲染墙钟时间。求值先预热三轮，再测量三种阶段各九次；渲染保留两个预热样本，再交错测量三个匹配阶段。记录 CPU 配额、线程、实际 OpenGL 渲染器、采样与分辨率。数字不能换算成交互视口帧率，也不代表独立显卡性能；顶点数不作为通过标准。

## 当前结论

第一组 960×540 软件 Eevee 实图已经实际读取。过肩机位遮住了充能中心和命中主体；侧面机位暴露出充能中心偏小、外围碎片权重较高。原先刀光提前五帧出现，在预备动作中形成背后的大色块，现改为接触前两帧开始，仍需连续序列复核。

完整 96 帧视频、远景、暗背景、反向遮挡、无插件像素比较和匹配耗时正在验证。未完成实时播放与正式二次元角色验收，也未通过整体艺术验收；[#89](https://github.com/mumu-lhl/blender-vfx-studio/issues/89) 保持开放。生成视频、增加节点或测试通过均不改变这个结论。
