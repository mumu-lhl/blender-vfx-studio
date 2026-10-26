# Energy Charge：积蓄后的压缩与释放

[#131](https://github.com/mumu-lhl/blender-vfx-studio/issues/131) 继续处理内核的形态节奏。实际高清图与完整连段中，中心虽逐渐长大，但积蓄时仍像竖向火舌，外围碎片更显眼。生成器已有尺寸增长与释放拉伸，缺少积蓄阶段独立的压缩形变。

新候选在原有三段内核上逐渐降低高度，并扩展横截面补偿体积。它从现有 Compression Builds 读取统一进度；释放开始时解除压缩，接上原来的收束拉长。外围路径、材质与 Release Stretch 默认值保持不变，没有增加发光、纹理、顶点、粒子或对象。四层、12 个粒子槽、Low 894 顶点预算不变。

选择 Charge • Compressed Core 下的网格，在 Geometry Nodes 调整 Nucleus Compression；0 关闭新增形变，默认 0.6，内部限制为 0–0.85，避免截面翻转。原来的 Seed Size / Stored Size 继续决定大小，Release Pinch / Release Stretch 决定释放形态。节点、驱动器和网格随 Complete Effect 保存，已有完整资产不重建。

19 项局部 Blender 检查通过。新增检查确认压缩降低内核高度并扩展横截面、包围盒体积保持一致、外围顶点不变，早期与释放后不受影响；速度加倍后仍能得到对应形态。原型 Cycles 浅背景与 AgX 远景已实际读取，积蓄到释放的轮廓变化更明确，但远景中心仍小。

Eevee 多阶段与连续采样、暗背景、侧面、无插件重开、示例 ZIP 和完整连段仍在验证。当前为候选，不宣布整体视觉验收，不发布 0.22.3。整体 #89 保持开放，没有实时播放、真实角色或设备帧率验收。
