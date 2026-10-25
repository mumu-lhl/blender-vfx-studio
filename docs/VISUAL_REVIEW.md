# Arc Slash 视觉检查

当前源码正在重做刀光，尚未发布。0.22.2 的资产仍是版本 2 的规则月牙；新建效果使用版本 3，不会覆盖旧文件。整体商业级艺术品质尚未验收。

## 问题与实际修改

版本 2 的几何节点把所有外缘点放在同一个圆上，残影只是固定半径和角度偏移，整个刀面位于平面。材质有拉丝与噪声，却改变不了规则轮廓。实际峰值图仍像一条发光月牙，退场留下过长的完整细线。

版本 3 在真实生成器中加入一个偏向前端的主钩形、较小的外缘变化和内侧缺口。第一轮外缘扰动过强，实图出现生硬的波浪肩部；随后减小辅助起伏，并降低残影的轮廓扰动。Bank 将刀面弯入深度，Wake Spread 让两条较暗残影逐渐分离。

材质用冷白锋刃、亮紫中带和深紫内侧建立主次；细笔触只辅助色块。峰值后先降低锋刃白色，再把主体拆成短段并侵蚀，避免靠透明度留下完整月牙。Fade 控制分段退场，Breakup 控制噪声侵蚀，Dissolve=1 仍会完全隐藏材质。默认发光从 2.2 降至 1.6，没有增加几何数量或额外辉光。

Contour、Bank、Wake Spread 与原有控制都可关键帧编辑。Low 仍是一个显示对象、一个材质、594 顶点和 480 个四边面。无外部纹理、缓存或逐帧 Python；形体与材质保存在原生节点中。

## 实际看图范围

本轮在 Blender 5.2.2 中用图像查看工具读取实际 960×540 PNG，包括 Cycles 暗背景的出现、峰值、衰减，以及浅灰背景斜视角三阶段。Eevee 使用软件渲染、16 samples；暗/浅灰背景序列抽取第 1、2、3、5、7、9、11、13、15、17、19 帧。

已读取暗/浅灰两个序列的全部 22 帧：第 2–5 帧快速展开，峰值的锋刃和深色内面均能辨认；第 7 帧开始分段，第 9–11 帧只留短笔触，后段退净。暗背景能辨认分离的辅助残影；浅背景上它们仍弱，不能承诺所有背景上的细节都清楚。

另实际读取 Eevee、AgX、近白背景、远景的三阶段图。峰值仍能辨认深紫主体、钩形与浅色锋刃；颜色比 Standard 更柔和，辅助残影很弱，衰减短笔触也接近背景。这个结果支持主体轮廓的可读性，不代表所有细节通过。背景线性 RGB 为 0.72/0.76/0.8，远景相机宽度为 14，常规为 9.2；AgX 会把该背景显示为较柔和的灰白。

版本 2 通过明确的资产版本重新构建，其 Cycles 三阶段与修改前保存的实际 PNG 逐像素一致。这证明保留了旧版生成结果；它不是两版等参数的性能比较。

抽帧只检查这些时刻的形状、位置与层次，没有实时观看视频，不能验证实际播放掉帧或未抽取帧的闪烁。角色实战镜头、集成显卡视口帧率和更多镜头仍未验收。

## 复现与验证

在仓库根目录，用新的后台进程执行：

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/slash_preview.py
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/slash_preview.py -- --engine BLENDER_EEVEE --light --sampled
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/slash_preview.py -- --light --angled
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/slash_preview.py -- --asset-version 2
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/slash_preview.py -- --engine BLENDER_EEVEE --pale --far --view-transform AgX
```

输出在 `work/visual-slash/`，包括 PNG、原生 `.blend` 和 `*-settings.json`。记录包含实际帧列表、图片文件名、源文件哈希、相机与引擎；旧图片可能仍在目录中，应按记录选择本次结果。`--frames 2 5 11` 指定抽查帧，`--far` 拉远相机，`--legacy` 保留版本 1 的对照入口。

11 项 Blender 刀光测试通过，覆盖版本 1/2 保留、新版形状控制与重定时、实例独立、参数及完整资产复用、表面控制和几何预算。保存后在不导入插件、关闭自动执行的新进程跳帧：版本 3 的几何与三个阶段低分辨率像素保持一致。另对 Cycles 暗背景及 Eevee 浅灰背景的三阶段高清 PNG 完成原生重开逐通道对比；19 帧所有效果层不再输出几何。实际 examples ZIP 也通过无插件检查。测试不代替上面的实际看图。

版本 2 首轮改进与 v0.21.1 发布验证属于历史结果，详见 [该版本发布页](https://github.com/mumu-lhl/blender-vfx-studio/releases/tag/v0.21.1)。当前候选的 CI、合并与后续问题由 [#91](https://github.com/mumu-lhl/blender-vfx-studio/issues/91) 跟踪。
