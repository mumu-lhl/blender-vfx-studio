# 连续技能检查包

`tools/charge_handoff.py` 用真实资产生成 60 帧的蓄力、挥斩、命中与消散，24 fps、960×540。默认仍只渲染 17 个选定帧；`--sequence` 才生成完整序列。场景使用简化武器和靶标，不能替代真实角色验收。

在全新克隆中，先安装 Blender 5.2.2 LTS、Python 和 FFmpeg（含 ffprobe），然后运行：

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/charge_handoff.py -- --engine BLENDER_EEVEE --light --sequence
blender -b work/charge-handoff/blender_eevee-light/handoff.blend --disable-autoexec --python-exit-code 1 --python tests/charge_handoff_reopen.py
python tools/handoff_bundle.py work/charge-handoff/blender_eevee-light
```

无显示设备的软件 Eevee 可设置 `LIBGL_ALWAYS_SOFTWARE=1 EGL_PLATFORM=surfaceless`。结果是 `dist/blender-vfx-studio-handoff-版本.zip`，解压后打开 `index.html` 播放，或打开 `handoff.blend` 编辑。原生场景停在命中帧 31，渲染输出使用相对路径 `//renders/handoff-`，播放不需要插件。

检查包包含 MP4、60 张源 PNG、30 张视频隔帧解码图、原生场景、设置和文件哈希。渲染记录绑定相机、色彩管理及生成器；原生检查核对 31/33 帧像素和 60 帧清空，并绑定场景与对应图片。若代码、场景或图片在检查后改变，打包会拒绝旧记录；失败不会替换已有 ZIP。编码与解码共用原战斗检查工具，原有 36 帧模式保持默认行为。

## 本轮基线实际观察

已读取本地 MP4 对应第 1、3、5……59 帧的全部 30 张解码图。13–27 帧的充能仍像翻动的白蓝壳体，压缩变化不足；29 帧可见刀光的大块月牙和较弱残带；35–37 帧的命中主喷流仍偏粗硬。它们是待改进项，不因成功编码或测试而获艺术批准。参考驱动的充能重做由 [#99](https://github.com/mumu-lhl/blender-vfx-studio/issues/99) 跟踪。

这批基线视频为 60 帧、24 fps、2.5 秒。SHA256 为 `7f10391331c0187c9a70382be293a95b19f907af95eb0cb097d5fcc294205080`，源设置与 PNG 组合 SHA256 为 `1cd246c6a3d1ae64b26e7c0a4c5efce6e8234930388354424155d71b2216c7ae`。这是本地文件标识；CI 会独立生成自己的包。没有实时观看视频、真实角色或实际视口帧率验收。

Energy Charge 内卷路径候选后来用同一工具生成了完整新连段，并实际读取全部 30 张解码图及释放到命中的相邻帧。它替代基线白壳造型，但不改变刀光和命中生成器。最新画面观察、校验标识及仍有的问题见 [充能压缩检查](CHARGE_COMPRESSION_REVIEW.md)，不能把上面的基线视频与新资产混用。

新增的 Linux 软件渲染任务独立生成此包，避免继续延长已有预览任务。36 帧战斗场景另由独立任务生成三套视频、抽帧和原生检查，避免与单效果预览串行挤占同一任务的 40 分钟预算；原帧数、采样与附件保持不变，使用两线程软件渲染。标签发布需同时通过三平台任务、战斗预览和完整技能连段任务，才会把检查包与安装包、示例资产一起交付。当前仍未发布 0.22.3。
