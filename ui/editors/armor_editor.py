# -*- coding: utf-8 -*-
"""装备编辑器 - 响应式卡片布局

Card-based responsive layout。基本属性、装备属性、拆解材料各占全宽。
宽屏时贴图与本地化并排双列，窄屏单列瀑布。

================================================================================
卡片结构 (宽屏, >1100px 内容区)
================================================================================

    ┌──── 基本属性 ─────────────────────────────────────┐
    │ ID/槽位/等级/材料/标签/稀有度/价格/耐久             │
    └───────────────────────────────────────────────────┘
    ┌──── 装备属性 ─────────────────────────────────────┐
    │ 按分组平铺属性数值 (响应式 N 列)                    │
    └───────────────────────────────────────────────────┘
    ┌──── 拆解材料 (条件显示) ──────────────────────────┐
    │ 各材料碎片数量                                     │
    └───────────────────────────────────────────────────┘
    ┌──── 贴图文件 ──────────┐  ┌── 装备名称与本地化 ───┐
    │ 物品栏+战利品+角色贴图  │  │ 主语言 + 其他语言     │
    └────────────────────────┘  └───────────────────────┘

================================================================================
"""

from __future__ import annotations

from ui import imgui_shim as imgui

from ui import layout as ly
from ui.state import dpi_scale, state as ui_state

from constants import (
    ARMOR_MATERIAL_LABELS,
    ARMOR_SLOT_LABELS,
    ARMOR_ATTR_GROUPS,
)
from models import validate_item
from ui.editors.common import (
    CARD_GAP,
    BREAKPOINT_PX,
    CARD_STYLE,
    card_heading,
    draw_card_section,
    draw_card_content,
    draw_validation_card,
    draw_basic_properties,
    draw_attributes_editor,
    draw_fragments_editor,
    draw_localization_editor,
)


# =============================================================================
# 主入口
# =============================================================================

def draw_armor_editor() -> None:
    """装备编辑器 - 响应式卡片布局"""
    armor = ui_state.project.armors[ui_state.current_armor_index]

    avail_w = imgui.get_content_region_available_width()
    is_wide = avail_w > BREAKPOINT_PX * dpi_scale()

    # =================================================================
    # 基本属性 (全宽)
    # =================================================================
    draw_card_section(
        "基本属性",
        lambda: draw_basic_properties(
            armor, "armor", ARMOR_SLOT_LABELS, ARMOR_MATERIAL_LABELS
        ),
    )

    # =================================================================
    # 装备属性 (全宽)
    # =================================================================
    ly.gap_y(CARD_GAP)
    draw_card_section(
        "装备属性",
        lambda: draw_attributes_editor(armor, ARMOR_ATTR_GROUPS, "armor"),
    )

    # =================================================================
    # 拆解材料 (条件显示, 全宽)
    # =================================================================
    no_fragment_slots = ["Ring", "Amulet", "shield"]
    if armor.slot in no_fragment_slots:
        armor.fragments.clear()
    else:
        ly.gap_y(CARD_GAP)
        draw_card_section(
            "拆解材料",
            lambda: draw_fragments_editor(armor),
        )

    # =================================================================
    # 贴图 + 本地化 (响应式双列)
    # =================================================================
    ly.gap_y(CARD_GAP)
    if is_wide:
        with ly.equal_height_row("##armor_dual_pres", cols=2, gap=CARD_GAP) as row:
            with row.col(0, style=CARD_STYLE):
                draw_card_content("贴图文件", lambda: _draw_textures(armor))
            with row.col(1, style=CARD_STYLE):
                draw_card_content("装备名称与本地化", lambda: draw_localization_editor(armor, "armor"))
    else:
        draw_card_section("贴图文件", lambda: _draw_textures(armor))
        ly.gap_y(CARD_GAP)
        draw_card_section(
            "装备名称与本地化",
            lambda: draw_localization_editor(armor, "armor"),
        )

    # =================================================================
    # 验证错误
    # =================================================================
    errors = validate_item(armor, ui_state.project, include_warnings=True)
    if errors:
        ly.gap_y(CARD_GAP)
        draw_validation_card(errors, "armor")


# =============================================================================
# 贴图
# =============================================================================

def _draw_textures(armor) -> None:
    """绘制装备贴图"""
    from ui.editors.texture_editor import draw_textures_editor
    draw_textures_editor(armor, "armor")


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_armor_editor"]
