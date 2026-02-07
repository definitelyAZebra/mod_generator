# -*- coding: utf-8 -*-
"""装备编辑器 - 独立函数

不依赖 GUI god object，直接调用 common.py 的模块级工具函数。
"""

from ui import imgui_shim as imgui

from constants import (
    ARMOR_MATERIAL_LABELS,
    ARMOR_SLOT_LABELS,
    ARMOR_ATTR_GROUPS,
)
from models import validate_item
from ui.state import state as ui_state
from ui.editors.common import (
    draw_basic_properties,
    draw_attributes_editor,
    draw_fragments_editor,
    draw_localization_editor,
    draw_validation_errors,
)


def draw_armor_editor() -> None:
    """绘制护甲编辑器"""
    armor = ui_state.project.armors[ui_state.current_armor_index]

    if imgui.tree_node("基本属性##armor", flags=imgui.TREE_NODE_FRAMED):
        draw_basic_properties(
            armor, "armor", ARMOR_SLOT_LABELS, ARMOR_MATERIAL_LABELS
        )
        imgui.tree_pop()

    if imgui.tree_node("装备属性", flags=imgui.TREE_NODE_FRAMED):
        draw_attributes_editor(armor, ARMOR_ATTR_GROUPS, "armor")
        imgui.tree_pop()

    # 项链、戒指、盾牌不允许拆解材料
    no_fragment_slots = ["Ring", "Amulet", "shield"]
    if armor.slot in no_fragment_slots:
        # 强制清空拆解材料
        armor.fragments.clear()
    else:
        if imgui.tree_node("拆解材料", flags=imgui.TREE_NODE_FRAMED):
            draw_fragments_editor(armor)
            imgui.tree_pop()

    if imgui.tree_node("装备名称与本地化", flags=imgui.TREE_NODE_FRAMED):
        draw_localization_editor(armor, "armor")
        imgui.tree_pop()

    if imgui.tree_node("贴图文件##armor", flags=imgui.TREE_NODE_FRAMED):
        from ui.editors.texture_editor import draw_textures_editor
        draw_textures_editor(armor, "armor")
        imgui.tree_pop()

    errors = validate_item(armor, ui_state.project, include_warnings=True)
    draw_validation_errors(errors)


__all__ = ["draw_armor_editor"]
