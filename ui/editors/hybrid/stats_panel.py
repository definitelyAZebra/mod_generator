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

# 网格每行显示的属性对数 (label + input 为一对)
_GRID_COLS = 3

# 输入框固定宽度 (Tailwind 单位)
_INPUT_TW = 22  # 88px


# =============================================================================
# 主入口
# =============================================================================

def draw_stats_panel(hybrid: HybridItemV2) -> None:
    """绘制属性面板

    Args:
        hybrid: 混合物品数据对象
    """
    # 装备属性
    if _should_show_equipment_attributes(hybrid):
        _draw_equipment_attributes_editor(hybrid)

    # 消耗品属性 - 仅当触发模式为效果时显示
    if isinstance(hybrid.trigger, EffectTrigger):
        if _should_show_equipment_attributes(hybrid):
            ly.gap_y(3.5)
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


def _draw_attr_table(attrs: list[str], target_dict: dict) -> None:
    """渲染属性紧凑表格: [label][input] × _GRID_COLS

    使用 ImGui Table 实现 6 列 (label, input) × 3 布局。
    label 列自动拉伸, input 列固定宽度。
    """
    input_w = sz(_INPUT_TW)
    cell_pad_x = sz(1.5)  # 6px 水平间距
    cell_pad_y = sz(0.5)  # 2px 垂直间距

    imgui.push_style_var(imgui.STYLE_CELL_PADDING, (cell_pad_x, cell_pad_y))

    table_cols = _GRID_COLS * 2  # label + input per logical column
    flags = imgui.TABLE_SIZING_STRETCH_SAME | imgui.TABLE_NO_BORDERS_IN_BODY

    if imgui.begin_table("##ag", table_cols, flags):
        # 列配置: 交替 stretch(label) + fixed(input)
        for i in range(_GRID_COLS):
            imgui.table_setup_column(f"##l{i}")  # stretch label
            imgui.table_setup_column(
                f"##i{i}", imgui.TABLE_COLUMN_WIDTH_FIXED, input_w
            )

        for i, attr in enumerate(attrs):
            if i % _GRID_COLS == 0:
                imgui.table_next_row()

            val = target_dict.get(attr, 0)
            name, desc = get_attr_display(attr)
            display_name = name or attr

            # --- Label column ---
            imgui.table_next_column()
            label_style = tw.text_faint if val == 0 else tw.text_muted
            imgui.align_text_to_frame_padding()
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
