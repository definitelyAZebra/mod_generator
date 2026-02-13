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
from ui.scale import Sp, dp
from ui.fields import field_row, int_field

from core.hybrid_item import HybridItemV2
from ui.editors.common import get_attr_display
from ui.editors.attr_table import draw_attr_table, draw_attribute_full_grid
from constants import (
    DEFAULT_GROUP_ORDER,
    get_attribute_groups,
    get_equip_attrs_for_slot,
    get_consumable_buff_attrs,
    CONSUMABLE_DURATION_ATTRIBUTE,
    CONSUMABLE_INSTANT_ATTRS,
)
from core.specs import (
    CharmEquip, NotEquipable, NoCharges,
    EffectTrigger,
)


# =============================================================================
# 常量
# =============================================================================

# 输入框固定宽度 (Tailwind 单位)
_INPUT_TW = 20  # 80px


# =============================================================================
# 子区域标题
# =============================================================================

def _sub_section(text: str) -> None:
    """属性子区域标题 — 金色文字

    Tailwind: text-goldrim-400 font-medium
    """
    tw.text_goldrim_400(imgui.text)(text)
    ly.gap_y(Sp.S1_5)


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
        and not isinstance(hybrid.charges, NoCharges)
    )

    # 装备属性
    if show_eq:
        if show_ce:
            _sub_section("装备属性")
        _draw_equipment_attributes_editor(hybrid)

    # 消耗品属性 — 分隔线 + 子标题
    if show_ce:
        if show_eq:
            ly.gap_y(Sp.S4)
            imgui.separator()
            ly.gap_y(Sp.S3)
        _sub_section("使用效果")
        _draw_consumable_attributes_editor(hybrid)


def _should_show_equipment_attributes(hybrid: HybridItemV2) -> bool:
    """武器/护甲/护符显示装备属性编辑器"""
    return not isinstance(hybrid.equipment, NotEquipable)


# =============================================================================
# 核心: 属性全网格渲染
# =============================================================================

_draw_attribute_full_grid = draw_attribute_full_grid
_draw_attr_table = draw_attr_table


# =============================================================================
# 装备属性编辑器
# =============================================================================

def _get_attribute_groups_for_hybrid(hybrid: HybridItemV2) -> dict:
    """根据槽位获取可编辑属性分组 (有序 dict)"""
    has_passive = isinstance(hybrid.equipment, CharmEquip)
    attrs = get_equip_attrs_for_slot(hybrid.slot, has_passive)
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
    if isinstance(hybrid.charges, NoCharges):
        return
    if not isinstance(hybrid.trigger, EffectTrigger):
        return

    consumable_attrs = hybrid.trigger.consumable_attributes

    # === 1. 基础字段 (Duration / Poisoning) ===
    _draw_consumable_basics(hybrid, consumable_attrs)

    ly.gap_y(Sp.S3)

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
                hybrid.trigger.poison_duration = nv


def _build_consumable_attr_keys() -> list[str]:
    """有序属性 key 列表"""
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
    for a in get_consumable_buff_attrs():
        if a not in skip and a not in seen:
            seen.add(a)
            result.append(a)

    return result


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_stats_panel"]
