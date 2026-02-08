# -*- coding: utf-8 -*-
"""混合物品编辑器 - 属性面板 (全属性网格)

"数值配置" - 装备属性 + 消耗品效果属性

================================================================================
设计理念
================================================================================

所有可用属性按分组平铺显示，取代逐个添加的弹窗模式。
- 值为 0 → 标签显示为 faint (灰暗), 输入框保持可编辑
- 值非 0 → 标签显示为 muted (正常), 属性"已激活"
- 无需添加/删除按钮; 用户直接编辑数值即可

Tailwind 映射:
    grid grid-cols-6 gap-x-6 gap-y-1    → ImGui Table (label-col + input-col) × 3
    text-stone-500 (faint)               → tw.text_faint
    text-stone-300 (muted)               → tw.text_muted
    text-purple-400 (accent heading)     → tw.text_accent
================================================================================
"""

from __future__ import annotations

from ui import imgui_shim as imgui
from ui import tw
from ui import layout as ly
from ui.layout import sz, tooltip
from ui.state import dpi_scale
from ui.fields import field_row, int_field

from hybrid_item_v2 import HybridItemV2
from ui.editors.common import get_attr_display
from constants import (
    STRICT_INT_ATTRIBUTES,
    DEFAULT_GROUP_ORDER,
    get_attribute_groups,
    get_hybrid_attrs_for_slot,
    get_consumable_duration_attrs,
    CONSUMABLE_DURATION_ATTRIBUTE,
    CONSUMABLE_INSTANT_ATTRS,
)
from specs import (
    is_weapon_mode, is_armor_mode, is_charm_mode,
    EffectTrigger,
    charge_has_charges,
)


# =============================================================================
# 常量
# =============================================================================

# 输入框固定宽度 (Tailwind 单位)
_INPUT_TW = 18  # 72px

# 最大列数上限
_MAX_COLS = 6

# 标签列: 固定 6 个中文字宽 (全局统一)
_LABEL_CHARS = 6
_label_w_cache: float = 0.0


def _get_label_width() -> float:
    """获取标签列固定宽度 (6 个中文字 + 余量)

    首次调用时用 calc_text_size 测量 6 个全角字，之后缓存。
    """
    global _label_w_cache
    if _label_w_cache <= 0:
        _label_w_cache = imgui.calc_text_size("测" * _LABEL_CHARS).x + sz(1)
    return _label_w_cache


# =============================================================================
# 子区域标题
# =============================================================================

def _sub_section(text: str) -> None:
    """属性子区域标题 — 金色文字

    Tailwind: text-goldrim-400 font-medium
    """
    tw.text_goldrim_400(imgui.text)(text)
    ly.gap_y(1.5)


# =============================================================================
# 主入口
# =============================================================================

def draw_stats_panel(hybrid: HybridItemV2) -> None:
    """绘制属性面板

    当两个区域同时存在时，用分隔线 + 子标题区分。

    Args:
        hybrid: 混合物品数据对象
    """
    show_eq = _should_show_equipment_attributes(hybrid)
    show_ce = (
        isinstance(hybrid.trigger, EffectTrigger)
        and charge_has_charges(hybrid.charges)
    )

    # 装备属性
    if show_eq:
        if show_ce:
            _sub_section("装备属性")
        _draw_equipment_attributes_editor(hybrid)

    # 消耗品属性 — 分隔线 + 子标题
    if show_ce:
        if show_eq:
            ly.gap_y(4)
            imgui.separator()
            ly.gap_y(3)
        _sub_section("使用效果")
        _draw_consumable_attributes_editor(hybrid)


def _should_show_equipment_attributes(hybrid: HybridItemV2) -> bool:
    """武器/护甲/护符显示装备属性编辑器"""
    return (
        is_weapon_mode(hybrid.equipment)
        or is_armor_mode(hybrid.equipment)
        or is_charm_mode(hybrid.equipment)
    )


# =============================================================================
# 核心: 属性全网格渲染
# =============================================================================

def _draw_attribute_full_grid(
    groups: dict[str, list[str]],
    target_dict: dict,
    id_prefix: str = "eq",
) -> None:
    """按分组渲染全属性网格

    每组: 标题 + 紧凑 N×3 表格 (label | input) × 3

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
            ly.gap_y(2)
        first = False

        imgui.push_id(f"{id_prefix}_{group_name}")

        # 分组标题
        tw.text_accent(imgui.text)(group_name)
        ly.gap_y(0.5)

        # 紧凑属性表格
        _draw_attr_table(attrs, target_dict)

        imgui.pop_id()


# 左端点缀圆点透明度
_DOT_ALPHA = 0.25


def _draw_attr_table(attrs: list[str], target_dict: dict) -> None:
    """渲染属性紧凑表格: [·label][input] × N (响应式, 右端齐平)

    布局策略:
    - label 列: 全局固定 6 中文字宽，文字右对齐 + 左端圆点点缀
    - input 列: 固定 72px
    - 列数: floor(avail / logical_col_w)，最大 6
    - cell_pad_x: 动态计算使最右列右边缘齐平卡片 padding
    """
    if not attrs:
        return

    label_w = _get_label_width()
    input_w = sz(_INPUT_TW)
    cell_pad_y = sz(0.5)  # 2px 垂直间距
    min_pad_x = sz(0.5)  # 2px 最小水平间距

    # 动态列数 + cell_pad_x 计算
    avail_w = imgui.get_content_region_available_width()
    # 逻辑列最小宽 = label + input + 4*min_pad (左右各一个 pad per cell)
    min_col_w = label_w + input_w + min_pad_x * 4
    num_cols = max(1, min(_MAX_COLS, int(avail_w / min_col_w)))
    # 反算 cell_pad_x 使总宽 = avail_w
    # total = num_cols * (label_w + input_w + 4*pad_x) = avail_w
    cell_pad_x = max(min_pad_x, (avail_w - num_cols * (label_w + input_w)) / (num_cols * 4))

    table_cols = num_cols * 2

    imgui.push_style_var(imgui.STYLE_CELL_PADDING, (cell_pad_x, cell_pad_y))

    flags = imgui.TABLE_SIZING_FIXED_FIT | imgui.TABLE_NO_BORDERS_IN_BODY

    if imgui.begin_table("##ag", table_cols, flags):
        for i in range(num_cols):
            imgui.table_setup_column(
                f"##l{i}", imgui.TABLE_COLUMN_WIDTH_FIXED, label_w,
            )
            imgui.table_setup_column(
                f"##i{i}", imgui.TABLE_COLUMN_WIDTH_FIXED, input_w,
            )

        draw_list = imgui.get_window_draw_list()
        dot_r = 1.5 * dpi_scale()  # 圆点半径
        dot_color = imgui.get_color_u32_rgba(0.5, 0.5, 0.6, _DOT_ALPHA)

        # input 样式: frame_bg + border + rounded
        with tw.input_default:
            for i, attr in enumerate(attrs):
                if i % num_cols == 0:
                    imgui.table_next_row()

                val = target_dict.get(attr, 0)
                name, desc = get_attr_display(attr)
                display_name = name or attr

                # --- Label column (右对齐 + 左端圆点) ---
                imgui.table_next_column()
                imgui.align_text_to_frame_padding()

                # 左端圆点点缀
                cx, cy = imgui.get_cursor_screen_pos()
                frame_h = imgui.get_frame_height()
                draw_list.add_circle_filled(
                    cx + dot_r, cy + frame_h * 0.5,
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
                        f"##v_{attr}", float(val), 0, 0, "%.2f"
                    )

                if ch:
                    target_dict[attr] = nv

        imgui.end_table()

    imgui.pop_style_var()


# =============================================================================
# 装备属性编辑器
# =============================================================================

def _get_attribute_groups_for_hybrid(hybrid: HybridItemV2) -> dict:
    """根据槽位获取可编辑属性分组 (有序 dict)"""
    has_passive = is_charm_mode(hybrid.equipment)
    attrs = get_hybrid_attrs_for_slot(hybrid.slot, has_passive)
    result = get_attribute_groups(attrs, DEFAULT_GROUP_ORDER)

    # 清理不再允许的属性
    if result:
        allowed = {a for attr_list in result.values() for a in attr_list}
        for k in [k for k in hybrid.attributes if k not in allowed]:
            del hybrid.attributes[k]

    return result


def _draw_equipment_attributes_editor(hybrid: HybridItemV2) -> None:
    """绘制装备属性编辑器 — 全属性网格"""
    groups = _get_attribute_groups_for_hybrid(hybrid)
    if not groups:
        return
    _draw_attribute_full_grid(groups, hybrid.attributes, "eq")


# =============================================================================
# 消耗品属性编辑器
# =============================================================================

def _draw_consumable_attributes_editor(hybrid: HybridItemV2) -> None:
    """绘制消耗品属性编辑器 — 基础字段 + 全效果网格"""
    if not charge_has_charges(hybrid.charges):
        return
    if not isinstance(hybrid.trigger, EffectTrigger):
        return

    consumable_attrs = hybrid.trigger.consumable_attributes

    # === 1. 基础字段 (Duration / Poisoning) ===
    _draw_consumable_basics(hybrid, consumable_attrs)

    ly.gap_y(3)

    # === 2. 全效果属性网格 ===
    all_keys = _build_consumable_attr_keys()
    groups = get_attribute_groups(all_keys, DEFAULT_GROUP_ORDER)
    if groups:
        _draw_attribute_full_grid(groups, consumable_attrs, "ce")


def _draw_consumable_basics(
    hybrid: HybridItemV2,
    consumable_attrs: dict,
) -> None:
    """渲染消耗品基础字段: 效果持续 / 中毒几率 / 中毒持续

    Tailwind: grid grid-cols-3 gap-3
    """
    show_poison_dur = consumable_attrs.get("Poisoning_Chance", 0) > 0
    num_cols = 3 if show_poison_dur else 2

    with field_row(num_cols):
        ch, nv = int_field(
            "效果持续 (轮)", "##dur",
            consumable_attrs.get(CONSUMABLE_DURATION_ATTRIBUTE, 0),
            vmin=0,
        )
        if ch:
            consumable_attrs[CONSUMABLE_DURATION_ATTRIBUTE] = nv

        ch, nv = int_field(
            "中毒几率 (%)", "##poison_chance",
            consumable_attrs.get("Poisoning_Chance", 0),
            vmin=0,
        )
        if ch:
            consumable_attrs["Poisoning_Chance"] = nv

        if show_poison_dur:
            ch, nv = int_field(
                "中毒持续 (轮)", "##poison_dur",
                hybrid.trigger.poison_duration,
                vmin=0,
            )
            if ch:
                object.__setattr__(hybrid.trigger, "poison_duration", nv)


def _build_consumable_attr_keys() -> list[str]:
    """构建消耗品全效果属性列表 (即时 + 持续, 去重, 排除基础字段)

    Returns:
        有序属性 key 列表
    """
    skip = {CONSUMABLE_DURATION_ATTRIBUTE, "Poisoning_Chance"}
    seen: set[str] = set()
    result: list[str] = []

    # 即时效果
    for attrs in CONSUMABLE_INSTANT_ATTRS.values():
        for a in attrs:
            if a not in skip and a not in seen:
                seen.add(a)
                result.append(a)

    # 持续效果
    for a in get_consumable_duration_attrs():
        if a not in skip and a not in seen:
            seen.add(a)
            result.append(a)

    return result


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_stats_panel"]
