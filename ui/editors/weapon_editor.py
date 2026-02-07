# -*- coding: utf-8 -*-
"""武器编辑器 - 独立函数

不依赖 GUI god object，直接调用 common.py 的模块级工具函数。
"""

from ui import imgui_shim as imgui

from constants import (
    SLOT_LABELS,
    WEAPON_MATERIAL_LABELS,
    WEAPON_ATTR_GROUPS,
)
from models import validate_item
from ui.state import state as ui_state
from ui.editors.common import (
    draw_basic_properties,
    draw_attributes_editor,
    draw_localization_editor,
    draw_validation_errors,
)


def draw_weapon_editor() -> None:
    """绘制武器编辑器"""
    weapon = ui_state.project.weapons[ui_state.current_weapon_index]
    weapon.markup = 1

    if imgui.tree_node("基本属性", flags=imgui.TREE_NODE_FRAMED):
        draw_basic_properties(
            weapon, "weapon", SLOT_LABELS, WEAPON_MATERIAL_LABELS
        )
        imgui.tree_pop()

    if imgui.tree_node("武器属性", flags=imgui.TREE_NODE_FRAMED):
        draw_attributes_editor(weapon, WEAPON_ATTR_GROUPS, "weapon")
        imgui.tree_pop()

    if imgui.tree_node("武器名称与本地化", flags=imgui.TREE_NODE_FRAMED):
        draw_localization_editor(weapon, "weapon")
        imgui.tree_pop()

    if imgui.tree_node("贴图文件", flags=imgui.TREE_NODE_FRAMED):
        from ui.editors.texture_editor import draw_textures_editor
        draw_textures_editor(weapon, "weapon")
        imgui.tree_pop()

    errors = validate_item(weapon, ui_state.project, include_warnings=True)
    draw_validation_errors(errors)


__all__ = ["draw_weapon_editor"]
