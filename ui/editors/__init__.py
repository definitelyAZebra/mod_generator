# -*- coding: utf-8 -*-
"""编辑器模块 - 所有编辑器均为独立函数，不使用 Mixin

- common.py: 共享工具函数 (draw_enum_combo, draw_basic_properties, ...)
- weapon_editor.py: draw_weapon_editor()
- armor_editor.py: draw_armor_editor()
- hybrid/: 混合物品 4 panel 模块
"""

from ui.editors.common import (
    draw_indented_separator,
    get_attr_display,
    draw_enum_combo,
    draw_validation_errors,
    draw_basic_properties,
    draw_attributes_editor,
    draw_fragments_editor,
    draw_localization_editor,
)
from ui.editors.weapon_editor import draw_weapon_editor
from ui.editors.armor_editor import draw_armor_editor

__all__ = [
    # common
    'draw_indented_separator',
    'get_attr_display',
    'draw_enum_combo',
    'draw_validation_errors',
    'draw_basic_properties',
    'draw_attributes_editor',
    'draw_fragments_editor',
    'draw_localization_editor',
    # editors
    'draw_weapon_editor',
    'draw_armor_editor',
]
