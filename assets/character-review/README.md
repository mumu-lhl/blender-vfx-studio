# 战斗检查用角色

`kaykit/` 保存 Kay Lousberg 发布的 KayKit Adventurers 1.0 中两名完整蒙皮角色。Knight 和 Rogue 各自包含骨架、动作和内嵌贴图；测试场景只保留使用的武器和动画。来源固定到官方仓库提交，文件大小和 SHA256 见 [provenance.json](kaykit/provenance.json)，原作者许可保存在 [LICENSE.txt](kaykit/LICENSE.txt)。这些文件按 CC0 使用，与插件源代码的许可分别保留。

这些低多边形角色用于复现挥剑、网格遮挡和特效衔接，不能代替正式二次元角色的最终艺术验收。使用 `tools/character_combat.py` 可从全新克隆生成可编辑的原生 `.blend`；骨架、动作和贴图不依赖外部下载或插件持续运行。它们是测试资产，不放进插件安装 ZIP。
