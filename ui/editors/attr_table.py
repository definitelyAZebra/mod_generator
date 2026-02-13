# -*- coding: utf-8 -*-
"""属性紧凑网格表格 — 共享组件

提供 `draw_attr_table` 和 `draw_attribute_full_grid`,
被 `ui/editors/common.py` 和 `ui/editors/hybrid/stats_panel.py` 共同使用。

Tailwind 映射:
    grid grid-cols-N gap-x-auto gap-y-0.5
    text-stone-500 (faint for zero) / text-stone-300 (muted for non-zero)
    ·label 左端圆点点缀 + 右对齐
"""
from __future__ import annotations

from typing import Any

from ui import imgui_shim as imgui
from ui import tw
from ui import layout as ly
from ui.layout import tooltip
from ui.scale import Sp, dp
from ui.state import dpi_scale

from data.attributes import ATTRIBUTE_TRANSLATIONS, ATTRIBUTE_DESCRIPTIONS
from constants import STRICT_INT_ATTRIBUTES

# =============================================================================
# 常量 (single source of truth)
# =============================================================================

# 最大列数上限
MAX_COLS = 6

# 标签列: 固定 6 个中文字宽
LABEL_CHARS = 6

# 左端点缀圆点透明度
DOT_ALPHA = 0.25

# 标签宽度缓存 (模块级单例)
_label_w_cache: float = 0.0


def _get_attr_display(attr: str, lang: str = "Chinese") -> tuple[str, str]:
    """获取属性的本地化显示名称和说明"""
    trans = ATTRIBUTE_TRANSLATIONS.get(attr, {})
    name = trans.get(lang) or trans.get("Chinese") or trans.get("English") or attr
    desc_dict = ATTRIBUTE_DESCRIPTIONS.get(attr, {})
    desc = desc_dict.get(lang) or desc_dict.get("Chinese") or desc_dict.get("English") or ""
    return (name, desc)


def get_label_width() -> float:
    """获取标签列固定宽度 (6 个中文字 + 余量)"""
    global _label_w_cache
    if _label_w_cache <= 0:
        _label_w_cache = imgui.calc_text_size("测" * LABEL_CHARS).x + dp(Sp.S1)
    return _label_w_cache


# =============================================================================
# 核心: 属性紧凑表格
# =============================================================================

def draw_attr_table(attrs: list[str], target_dict: dict[str, Any]) -> None:
    """渲染属性紧凑表格: [·label][input] × N (响应式, 右端齐平)

    Tailwind: grid grid-cols-N gap-x-auto gap-y-0.5

    布局策略:
    - label 列: 全局固定 6 中文字宽，文字右对齐 + 左端圆点点缀
    - input 列: 固定 80px
    - 列数: floor(avail / logical_col_w)，最大 MAX_COLS
    - cell_pad_x: 动态计算使最右列右边缘齐平卡片 padding
    """
    if not attrs:
        return

    label_w = get_label_width()
    input_w = dp(Sp.S20)
    cell_pad_y = dp(Sp.S0_5)  # 2px 垂直间距
    min_pad_x = dp(Sp.S0_5)  # 2px 最小水平间距

    # 动态列数 + cell_pad_x 计算
    avail_w = imgui.get_content_region_available_width()
    min_col_w = label_w + input_w + min_pad_x * 4
    num_cols = max(1, min(MAX_COLS, int(avail_w / min_col_w)))
    num_gaps = 2 * num_cols - 1
    cell_pad_x = max(min_pad_x, (avail_w - num_cols * (label_w + input_w)) / (num_gaps * 2))

    table_cols = num_cols * 2

    imgui.push_style_var(imgui.STYLE_CELL_PADDING, (cell_pad_x, cell_pad_y))

    flags = imgui.TABLE_SIZING_FIXED_FIT | imgui.TABLE_NO_BORDERS_IN_BODY

    try:
        if not imgui.begin_table("##ag", table_cols, flags):
            return

        try:
            for i in range(num_cols):
                imgui.table_setup_column(
                    f"##l{i}", imgui.TABLE_COLUMN_WIDTH_FIXED, label_w,
                )
                imgui.table_setup_column(
                    f"##i{i}", imgui.TABLE_COLUMN_WIDTH_FIXED, input_w,
                )

            draw_list = imgui.get_window_draw_list()
            dot_r = 1.5 * dpi_scale()  # 圆点半径
            dot_color = imgui.get_color_u32_rgba(0.5, 0.5, 0.6, DOT_ALPHA)

            # input 样式: frame_bg + border + rounded
            with tw.input_default:
                for i, attr in enumerate(attrs):
                    if i % num_cols == 0:
                        imgui.table_next_row()

                    val = target_dict.get(attr, 0)
                    if val is None:
                        val = 0
                    name, desc = _get_attr_display(attr)
                    display_name = name or attr

                    # --- Label column (右对齐 + 左端圆点) ---
                    imgui.table_next_column()
                    imgui.align_text_to_frame_padding()

                    # 左端圆点点缀
                    cx, cy = imgui.get_cursor_screen_pos()
                    frame_h = imgui.get_frame_height()
                    draw_list.add_circle_filled(
                        (cx + dot_r, cy + frame_h * 0.5),
                        dot_r, dot_color,
                    )

                    # 右对齐: 计算偏移
                    text_w = imgui.calc_text_size(display_name).x
                    offset = label_w - text_w
                    if offset > 0:
                        cursor = imgui.get_cursor_pos()
                        imgui.set_cursor_pos((cursor[0] + offset, cursor[1]))

                    label_style = tw.text_faint if val == 0 else tw.text_muted
                    label_style(imgui.text)(display_name)
                    if desc:
                        tooltip(desc)

                    # --- Input column ---
                    imgui.table_next_column()
                    imgui.set_next_item_width(-1)

                    if attr in STRICT_INT_ATTRIBUTES:
                        ch, nv = imgui.input_int(f"##v_{attr}", int(val), 0, 0)
                    else:
                        ch, nv = imgui.input_float(
                            f"##v_{attr}", float(val), 0, 0, "%.2f",
                        )

                    if ch:
                        target_dict[attr] = nv

        finally:
            imgui.end_table()
    finally:
        imgui.pop_style_var()


def draw_attribute_full_grid(
    groups: dict[str, list[str]],
    target_dict: dict[str, Any],
    id_prefix: str = "eq",
) -> None:
    """按分组渲染全属性网格

    每组: 标题 + 紧凑 N×3 表格

    Args:
        groups: {分组名: [属性名列表]}  (有序)
        target_dict: 属性值字典, key → number
        id_prefix: ImGui ID 前缀 (区分装备/消耗品)
    """
    first = True
    for group_name, attrs in groups.items():
        if not attrs:
            continue

        if not first:
            ly.gap_y(Sp.S2)
        first = False

        imgui.push_id(f"{id_prefix}_{group_name}")
        try:
            # 分组标题
            tw.text_accent(imgui.text)(group_name)
            ly.gap_y(Sp.S0_5)

            # 紧凑属性表格
            draw_attr_table(attrs, target_dict)
        finally:
            imgui.pop_id()



__all__ = [
    "MAX_COLS",
    "LABEL_CHARS",
    "DOT_ALPHA",
    "get_label_width",
    "draw_attr_table",
    "draw_attribute_full_grid",
]
