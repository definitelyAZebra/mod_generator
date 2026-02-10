# -*- coding: utf-8 -*-
"""混合物品编辑器 - 模块化面板

将 HybridEditorMixin 拆分为独立的面板模块:
- base_panel: 基础信息 (ID, 品质, 分类, 标签)
- behavior_panel: 行为设置 (装备形态, 触发, 充能, 生成规则)
- stats_panel: 属性配置 (装备属性 + 消耗品效果属性)
- presentation_panel: 呈现 (贴图 / 音效 / 本地化, 三卡片)
"""

from ui.editors.hybrid.base_panel import draw_base_panel
from ui.editors.hybrid.behavior_panel import draw_behavior_panel
from ui.editors.hybrid.stats_panel import draw_stats_panel
from ui.editors.hybrid.presentation_panel import draw_textures_panel, draw_sound_panel, draw_localization_panel

__all__ = [
    "draw_base_panel",
    "draw_behavior_panel",
    "draw_stats_panel",
    "draw_textures_panel",
    "draw_sound_panel",
    "draw_localization_panel",
]
