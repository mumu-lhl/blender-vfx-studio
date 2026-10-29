# 效果库参考与本项目实图的区分

这里区分原作明确说明、实际观图与本项目拟采用的方法。参考文件只留在 ignored `work/references/library/`，未进入插件或示例资产。没有实时观看动画，也没有取得原作者工程。

## 火焰：原作者教程

来源：[Aka 的 Simple Fire Shader Breakdown](https://realtimevfx.com/t/simple-fire-shader-breakdown/11213)。作者说明使用 Unity / Amplify：噪声以不同尺度和速度滚动，边界单独动画化，多粒子可使用不同相位；效果采用 HDR 与辉光。这不是 Blender 5.2 节点接口教程。

实际读取三组 GIF 各八张样本：成片 66 帧／2.74 秒、边界演示 61 帧／2.51 秒、粒子相位对照 63 帧／2.63 秒，并查看边界节点原图。可见边缘不断变化；同步与错相的团块表现不同。采样覆盖全段，不等于实时播放；辉光也影响了参考中的白芯与光晕。

对本项目的候选应用是检查各火舌的相位分工和保持阶段的边界变化，不复制纹理、节点源码或后期。当前 Fire 在角色镜头中仍有较完整的大火面，是否采用这些方法要以实际生成器修改后的图像判断。

## 烟尘：概念设计图

来源：[HALCYON ZERO PROJECT: VFX CONCEPT ARTS p.1](https://www.behance.net/gallery/190451557/HALCYON-ZERO-PROJECT-VFX-CONCEPT-ARTS-p1) 的公开 1400×787 图像。原页面访问返回 403；实际读取的是其公开 CDN 概念图，图中署名 Pando Labs，个人作者未进一步核实。

这张静态概念图把大团、小团、深色团块间隙与尖长贴地运动线分开。它能说明轮廓与明暗组织，**不能证明运动节奏或引擎实现**。本项目的实际烟尘是原生密度网格，两者不能混作同一种技术结果；暂不因概念图而替换现有体积实现。

## 本项目证据

本项目画面见 [角色图集](LIBRARY_GALLERY.md)、[施法镜头 PR #152](https://github.com/mumu-lhl/blender-vfx-studio/pull/152) 和 [冲刺落地](DASH_LANDING_REVIEW.md)。参考作品的丰富度不能作为本项目验收结果；代码测试、渲染生成和实际查看也分别记录。
