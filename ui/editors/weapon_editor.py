# -*- coding: utf-8 -*-
"""武器编辑器 - 响应式卡片布局

Card-based responsive layout。基本属性和武器属性各占全宽。
宽屏时贴图与本地化并排双列，窄屏单列瀑布。

================================================================================
卡片结构 (宽屏, >1100px 内容区)
================================================================================

    ┌──── 基本属性 ─────────────────────────────────────┐
    │ ID/槽位/等级/材料/标签/稀有度/价格/耐久             │
    └───────────────────────────────────────────────────┘
    ┌──── 武器属性 ─────────────────────────────────────┐
    │ 按分组平铺属性数值 (响应式 N 列)                    │
    └───────────────────────────────────────────────────┘
    ┌──── 贴图文件 ──────────┐  ┌── 武器名称与本地化 ───┐
    │ 物品栏+战利品+角色贴图  │  │ 主语言 + 其他语言     │
    └────────────────────────┘  └───────────────────────┘

================================================================================
"""

from __future__ import annotations

from ui import imgui_shim as imgui

from ui import layout as ly
from ui.state import dpi_scale, state as ui_state

from constants import (
    SLOT_LABELS,
    WEAPON_MATERIAL_LABELS,
    WEAPON_ATTR_GROUPS,
)
from core.models import Weapon, validate_item
from ui.editors.common import (
    CARD_GAP,
    BREAKPOINT_PX,
    CARD_STYLE,
    draw_card_section,
    draw_card_content,
    draw_validation_card,
    draw_basic_properties,
    draw_attributes_editor,
    draw_localization_editor,
)


# =============================================================================
# 主入口
# =============================================================================

def draw_weapon_editor() -> None:
    """武器编辑器 - 响应式卡片布局"""
    weapon = ui_state.project.weapons[ui_state.current_weapon_index]
    weapon.markup = 1

    with ly.scoped_id(id(weapon)):
        _draw_weapon_editor_content(weapon)


def _draw_weapon_editor_content(weapon: Weapon) -> None:
    """绘制武器编辑器内容（在 scoped_id 作用域内）。"""

    avail_w = imgui.get_content_region_available_width()
    is_wide = avail_w > BREAKPOINT_PX * dpi_scale()

    # =================================================================
    # 基本属性 (全宽)
    # =================================================================
    draw_card_section(
        "基本属性",
        lambda: draw_basic_properties(
            weapon, "weapon", SLOT_LABELS, WEAPON_MATERIAL_LABELS
        ),
    )

    # =================================================================
    # 武器属性 (全宽)
    # =================================================================
    ly.gap_y(CARD_GAP)
    draw_card_section(
        "武器属性",
        lambda: draw_attributes_editor(weapon, WEAPON_ATTR_GROUPS, "weapon"),
    )

    # =================================================================
    # 贴图 + 本地化 (响应式双列)
    # =================================================================
    ly.gap_y(CARD_GAP)
    if is_wide:
        with ly.equal_height_row("##weapon_dual_pres", cols=2, gap=CARD_GAP) as row:
            with row.col(0, style=CARD_STYLE):
                draw_card_content("贴图文件", lambda: _draw_textures(weapon))
            with row.col(1, style=CARD_STYLE):
                draw_card_content("武器名称与本地化", lambda: draw_localization_editor(weapon, "weapon"))
    else:
        draw_card_section("贴图文件", lambda: _draw_textures(weapon))
        ly.gap_y(CARD_GAP)
        draw_card_section(
            "武器名称与本地化",
            lambda: draw_localization_editor(weapon, "weapon"),
        )

    # =================================================================
    # 验证错误
    # =================================================================
    errors = validate_item(weapon, ui_state.project, include_warnings=True)
    if errors:
        ly.gap_y(CARD_GAP)
        draw_validation_card(errors, "weapon")


# =============================================================================
# 贴图
# =============================================================================

def _draw_textures(weapon: Weapon) -> None:
    """绘制武器贴图"""
    from ui.editors.texture_editor import draw_textures_editor
    draw_textures_editor(weapon, "weapon")


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_weapon_editor"]
