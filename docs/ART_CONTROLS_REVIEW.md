# 艺术控制与编辑流程审查

2026-10-27。范围是当前八套完整效果，优先解决控制无效、无法恢复基础形态和换色困难，再处理角色镜头中的造型问题。[#161](https://github.com/mumu-lhl/blender-vfx-studio/issues/161) 跟踪实施；整体艺术品质仍由 [#89](https://github.com/mumu-lhl/blender-vfx-studio/issues/89) 跟踪。

## 优先判断

| 效果 | 核对结果与处理顺序 |
| --- | --- |
| Arc Slash | Bank=0 已能恢复平面，但固定材质裁切仍留下小缺口，锋刃颜色固定。先补全关闭裁切和独立锋刃配色，再用同一生成器提供 Clean / Stylized。Contour 仍同时包含钩形与内缘扰动，尚未拆成独立控制。 |
| Energy Charge | 核心压缩、尺寸与各类进流仍在原生节点中。高价值问题是集中核心与外围的视觉权重，不能靠继续加宽或增亮解决；本批不声称已完成。 |
| Impact Burst | 实际侧栏已经隐藏特制主体不使用的 Count / Shape / Gravity / Spread，无需重复修复。侧面实体感和主体／辅助权重仍待处理。 |
| Lightning Strike | 长度、分支和放电时序仍需更方便的控制；远景细枝与接触火花偏弱。本批保留原演出。 |
| Stylized Fire | RGB 是暖色色带的乘色，不能方便变成蓝火。提供原生五色配色与直接色带编辑；集中 Height / Flow / Curl。持续阶段大火面仍未解决。 |
| Dust Impact | 主体体积保留；集中 Rise / Roll / Density。辅助 Ground Veil 的 Fade 原先没有驱动材质，现接入透明消散；隐藏该层仅作终点开关的 Dissolve，避免把它呈现为连续侵蚀。 |
| Character Dash Echoes | 捕获数量仍由质量决定，跨度存在整除限制。应独立控制数量与时间采样；本批不改捕获行为。 |
| Magic Circle | 集中实际生效的 Spin / Lift；Seal / Runes 上未驱动的 Lift 不显示。图案变体不是当前阻塞。 |

## 本批真实行为

侧栏用小型静态分组组织 Shape / Motion / Color / Material / Dissolve，其他项收在 Advanced；只显示相应层实际支持的控制。颜色选择器写回已有 RGB 属性，旁边的菱形给这三个原生通道插入关键帧，播放不依赖新增界面属性。

刀光的 Surface Cuts 关闭固定内缘裁切与残弧分段；Fragment Release=0 将退场改为连续透明淡出。Breakup 与 Dissolve 均为 0 时不再保留固定噪声侵蚀。Clean / Stylized 只设置当前节点的参数，保留配色、尺寸、时间和手动节点。当前格式参数预设缺少新增艺术字段时补安全默认值，不修改输入字典；完整效果载入仍保留其原生节点，不自动改造手工材质。

火焰 Orange / Blue / Green 只改主焰五个热色色点，并把 Heat Tint 设为白色；不改色点位置、几何、链接或其他节点。手工增加色点的色带继续直接编辑，不套用五色预设。余烬为独立层，仍可单独调色。私有造型与色带必须保存 Complete Effect，JSON 参数不包含它们。

## 已实际读取的画面

- 刀光：960×540 Eevee，出现 2、峰值 5、衰减 11；读取连续形态、暖色锋刃及灰背景对照。固定小缺口可关闭，尾部保持连续淡出。默认 Stylized 第 5 帧与修改前基线的解码像素相同，保留不规则风格。
- 火焰：960×540 Eevee 浅色角色镜头，Blue 第 20、36、60 帧已读取。冷色外焰、深边与浅色热芯生效；余烬保留独立暖色。持续阶段仍是较大的完整火面，配色改进不能代表造型验收。
- 烟尘：重新清空场景后读取 Fade=0/1 的辅助薄雾对照。差异较弱，符合其辅助权重；不称为主体画质提升。最初带默认 Cube 遮挡的对照作废。64×64 Cycles CPU 透明渲染回归确认 Fade 实际改变透明度。

这些是实图和阶段对照，**没有观看实时播放**。后台面板绘制已逐层检查八套资产的字段，但没有检查实际窗口布局、色彩弹窗或 UI 缩放。现有角色战斗与完整施法证据仍有效；新配色、连续刀光在完整战斗中的速度感和遮挡尚未补验。

## 复现与必要检查

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/slash_preview.py -- --engine BLENDER_EEVEE --style CLEAN
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/slash_preview.py -- --engine BLENDER_EEVEE --style CLEAN --light --body-color 1 .2 .015 --blade-color 1 .75 .08
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python tools/fire_preview.py -- --palette BLUE --frames 20 36 60
```

`--light` / `--dark` 切换上述各工具支持的背景；输出设置记录源文件摘要。CI 生成 Clean、暖色刀光和蓝／绿火焰的阶段图，保存为原有 visual-review 附件，不增加散落的发布附件。

功能检查覆盖风格切换不重建节点、原生 RGB 动画、现有参数预设、手工完整资产、火焰色带保护、烟尘实际透明渲染。刀光颜色动画与蓝焰均已保存并在不导入插件的新进程跳帧重开。小型界面与配色改动不重复所有无关电影渲染；最终提交的检查范围另记于 PR。
