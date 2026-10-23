# 刀光接命中的镜头检查

单独看刀光或粒子，难以判断武器到达目标时爆点是否出现，以及消散是否遮住后续动作。`tools/combat_preview.py` 建立一个简易武器挥向靶体的 36 帧场景，使用现有 Arc Slash 和 Impact Burst 创建接口。所有节点、驱动和武器变换关键帧都保存在原生 .blend 中；场景不加辉光。

武器和靶体只是空间与时间参照。没有角色、骨架、碰撞检测或正式动作；命中时间明确设为第 7 帧。Impact 放在靶体前侧，避免中心闪光被靶体完全遮住。刀光的半径、弧度和时长通过现有参数调整，不另建效果生成器。

## 实际发现

2026-10-23，在 Blender 5.2.2 中用 Cycles CPU 生成了完整的 36 帧暗背景 960×540 序列，以及浅背景的第 4、8、12、23 帧。已用图像查看工具读取暗背景的第 3、4、5、7、8、12、23 帧和四张浅背景图。

初版预览武器只按刀光旋转量运动，忽略了刀光出现时尖端仍在展开，因此第 4 帧武器与刀尖分离。修正武器动画，使它跟随实际展开前端；命中时武器尖端与爆发位置接近。修正只涉及参照武器，原来的特效节点保持不变。

第 7–8 帧能同时分辨紫色刀光和白橙爆点，中心短闪位于靶体前侧；第 12 帧刀光已明显退去，冲击波和尖片继续扩散；第 23 帧只剩少量余烬，靶体轮廓恢复。浅背景中的细残影和余烬仍较弱。本镜头没有发现需要修改默认生成器的新问题，但单个距离和视角不足以覆盖所有技能镜头。

本地另把全部帧编码为 960×540、24 fps、36 帧的视频，并核对了编码信息。当前检查工具只读取了上述静帧，没有观看连续视频；因此尚未完成连续运动观感验收，也没有真实角色或集成显卡帧率结论。

## 重建与打开

仅在新的后台进程运行，脚本会创建空场景：

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/combat_preview.py
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/combat_preview.py -- --light
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/combat_preview.py -- --sequence
```

前两条生成暗/浅背景的四张关键帧，第三条生成暗背景全部 36 帧。输出在 `work/visual-combat/dark/` 和 `light/`；各自的 `combat.blend` 是完整预览场景，可用 Blender 正常打开并播放，无需插件。它包含相机、灯光与参照物，不是 Load Complete Effect 使用的资产文件。

安装 FFmpeg 后可另生成视频：

```sh
ffmpeg -framerate 24 -i work/visual-combat/dark/combat-%04d.png -c:v libx264 -pix_fmt yuv420p work/visual-combat/combat.mp4
```

本地另用关闭自动执行、不加载插件的新进程跳到第 36、0、8 帧，验证生命周期边界，再重渲染第 8 帧；PNG 所有像素通道与原图一致。Linux CI 重建暗/浅背景关键帧、执行同一无插件渲染检查，并上传 `combat-shot-visual-review`，包含八张 PNG 和两个原生场景。自动检查结果以关联 PR 的记录为准。
