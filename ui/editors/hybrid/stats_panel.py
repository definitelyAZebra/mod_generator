# -*- coding: utf-8 -*-
"""混合物品编辑器 - 属性面板

"数值配置" - 装备属性 + 消耗品效果属性

================================================================================
样式设计规范
================================================================================

布局结构:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ 装备属性 (如有):                                                        │
    │   [+装备] Label       [input] [×]                  vertical list        │
    │          Label       [input] [×]                                        │
    │          ...                                                            │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                      gap-y = 20px       │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ 消耗品属性 (如有 EffectTrigger):                                        │
    │   [+效果] 效果持续    [input]                       vertical list        │
    │          中毒几率    [input]                                             │
    │          ...                                                            │
    └─────────────────────────────────────────────────────────────────────────┘

注意: 本面板暂用旧版 GridLayout 的 span 计量系统，后续将迁移到 ly.*。
================================================================================
"""

from __future__ import annotations

from ui import imgui_shim as imgui
from ui import tw
from ui.layout import tooltip
from ui.styles import (
    gap_m, grid_gap,
    SPAN_INPUT, SPAN_BADGE,
)
import ui.styles as styles
from ui.state import state as ui_state

from hybrid_item_v2 import HybridItemV2
from ui.editors.common import get_attr_display
from constants import (
    STRICT_INT_ATTRIBUTES,
    SPECIAL_STEP_ATTRIBUTES,
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
# 本地辅助
# =============================================================================

# red-500 @ 20% — 用于删除按钮 hover
_BADGE_HOVER_REMOVE = (0.9373, 0.2667, 0.2667, 0.2)


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
            imgui.dummy(0, gap_m())
        _draw_consumable_attributes_editor(hybrid)


def _should_show_equipment_attributes(hybrid: HybridItemV2) -> bool:
    """武器/护甲/护符显示装备属性编辑器"""
    return (
        is_weapon_mode(hybrid.equipment)
        or is_armor_mode(hybrid.equipment)
        or is_charm_mode(hybrid.equipment)
    )


# =============================================================================
# 共享: 属性列表渲染
# =============================================================================

def _render_attribute_grid(
    display_list: list[dict],
    target_dict: dict,
    hybrid: HybridItemV2 | None = None,
    show_add_button: bool = False,
    add_button_label: str = "",
    add_popup_id: str = "",
) -> list[str]:
    """渲染属性垂直列表

    Args:
        display_list: 每项 {key, name, is_basic, custom_bind?, desc?}
        target_dict: 要修改的属性字典
        hybrid: 混合物品对象 (custom_bind 需要)
        show_add_button: 是否在第一行显示添加按钮
        add_button_label: 添加按钮文字
        add_popup_id: popup ID

    Returns:
        需要移除的 key 列表
    """
    to_remove: list[str] = []

    SPAN_ADD_BTN = SPAN_BADGE
    SPAN_LABEL = 4

    for idx, item in enumerate(display_list):
        key = item["key"]
        name = item.get("name", key)
        is_basic = item.get("is_basic", False)
        custom_bind = item.get("custom_bind", None)
        desc = item.get("desc", None)

        # === Column 1: Add Button (only first row) or spacer ===
        if idx == 0 and show_add_button:
            if imgui.button(f"{add_button_label}##{add_popup_id}_btn", styles.span(SPAN_ADD_BTN), 0):
                imgui.open_popup(add_popup_id)
            tooltip("添加属性")
        else:
            imgui.dummy(styles.span(SPAN_ADD_BTN), 0)

        imgui.same_line(spacing=grid_gap())

        # === Column 2: Label ===
        label_w = styles.span(SPAN_LABEL)
        imgui.align_text_to_frame_padding()
        tw.text_muted(imgui.text)(name)
        text_w = imgui.calc_text_size(name).x
        if text_w < label_w:
            imgui.same_line(spacing=0)
            imgui.dummy(label_w - text_w, 0)

        imgui.same_line(spacing=grid_gap())

        # === Column 3: Input ===
        input_w = styles.span(SPAN_INPUT)
        imgui.set_next_item_width(input_w)

        if custom_bind == "poison_duration" and hybrid and isinstance(hybrid.trigger, EffectTrigger):
            val = hybrid.trigger.poison_duration
            ch, nv = imgui.input_int("##v_poison_dur", val)
            if ch:
                object.__setattr__(hybrid.trigger, "poison_duration", max(0, nv))
        else:
            val = target_dict.get(key, 0)
            if key in STRICT_INT_ATTRIBUTES:
                ch, nv = imgui.input_int(f"##v_{key}", int(val))
            else:
                step = SPECIAL_STEP_ATTRIBUTES.get(key, 0.1)
                ch, nv = imgui.input_float(f"##v_{key}", float(val), step, step * 10 if step else 0, "%.2f")

            if ch:
                target_dict[key] = nv
                if is_basic:
                    target_dict[key] = max(0, target_dict[key])

        if desc:
            tooltip(desc)

        imgui.same_line(spacing=grid_gap())

        # === Column 4: Delete Button ===
        delete_w = styles.span(SPAN_BADGE)
        if not is_basic:
            imgui.push_style_color(imgui.COLOR_BUTTON, 0, 0, 0, 0)
            imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, *_BADGE_HOVER_REMOVE)
            imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, *_BADGE_HOVER_REMOVE)
            if imgui.button(f"×##del_{key}", delete_w, 0):
                to_remove.append(key)
            imgui.pop_style_color(3)
            tooltip("移除此属性")
        else:
            imgui.dummy(delete_w, 0)
            tooltip("基础属性不可移除")

    return to_remove


# =============================================================================
# 共享: 添加属性弹窗
# =============================================================================

def _draw_add_attribute_popup(
    popup_id: str,
    target_dict: dict,
    available_attrs: list[tuple[str, str]],
) -> None:
    """绘制添加属性弹窗 (不含触发按钮)"""
    imgui.set_next_window_size(300, 400)
    if imgui.begin_popup(popup_id):
        imgui.dummy(0, 2)
        imgui.set_next_item_width(-1)

        if popup_id not in ui_state.attr_search_buffers:
            ui_state.attr_search_buffers[popup_id] = ""

        changed, search_text = imgui.input_text(
            f"##search_{popup_id}", ui_state.attr_search_buffers[popup_id], 64,
        )
        if changed:
            ui_state.attr_search_buffers[popup_id] = search_text

        search_lower = search_text.lower()
        imgui.separator()

        # 过滤列表
        filtered = []
        for attr, group in available_attrs:
            if target_dict.get(attr, 0) != 0:
                continue
            name, desc = get_attr_display(attr)
            match_text = f"{attr} {name}".lower()
            if not search_lower or search_lower in match_text:
                filtered.append((group, attr, name, desc))

        if not filtered:
            tw.text_muted(imgui.text)("无匹配属性")

        last_group = None
        last_group_open = False
        flat_mode = bool(search_lower)
        group_visible = False

        for group, attr, name, desc in filtered:
            if group != last_group:
                if not flat_mode:
                    if last_group and last_group_open:
                        imgui.tree_pop()
                    last_group_open = imgui.tree_node(f"{group}##grp_{group}_{popup_id}")
                    group_visible = last_group_open
                else:
                    imgui.dummy(0, 2)
                    tw.text_muted(imgui.text)(f"--- {group} ---")
                    group_visible = True
                    last_group_open = False
                last_group = group

            if group_visible:
                if imgui.selectable(f"{name or attr}##sel_{attr}")[0]:
                    target_dict[attr] = 1
                    imgui.close_current_popup()
                    ui_state.attr_search_buffers[popup_id] = ""
                if desc:
                    tooltip(desc)

        if not flat_mode and last_group and last_group_open:
            imgui.tree_pop()

        imgui.end_popup()


# =============================================================================
# 装备属性编辑器
# =============================================================================

def _get_attribute_groups_for_hybrid(hybrid: HybridItemV2) -> dict:
    """根据槽位获取可编辑属性分组"""
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
    """绘制装备属性编辑器 — 垂直列表布局"""
    groups = _get_attribute_groups_for_hybrid(hybrid)
    if not groups:
        return

    # 收集所有可用属性用于搜索
    all_available_attrs = []
    for group, attrs in groups.items():
        for attr in attrs:
            all_available_attrs.append((attr, group))

    # 构建显示列表 (仅已激活的属性)
    active_attrs = []
    for _group, attrs in groups.items():
        for attr in attrs:
            if hybrid.attributes.get(attr, 0) != 0:
                active_attrs.append(attr)

    display_list = []
    for attr in active_attrs:
        attr_name, attr_desc = get_attr_display(attr)
        display_list.append({
            "key": attr,
            "name": attr_name or attr,
            "desc": attr_desc,
            "is_basic": False,
        })

    # 渲染垂直列表 (集成添加按钮)
    to_remove = _render_attribute_grid(
        display_list,
        hybrid.attributes,
        show_add_button=True,
        add_button_label="+装备",
        add_popup_id="equip_attr",
    )

    # 空列表时仍需添加按钮
    if not display_list:
        if imgui.button("+装备##equip_attr_btn", styles.span(SPAN_BADGE), 0):
            imgui.open_popup("equip_attr")
        tooltip("添加装备属性")

    _draw_add_attribute_popup("equip_attr", hybrid.attributes, all_available_attrs)

    # 执行移除
    for attr in to_remove:
        del hybrid.attributes[attr]

    # 清理不再允许的属性
    _prune_attributes(hybrid, groups)


def _prune_attributes(hybrid: HybridItemV2, groups: dict) -> None:
    """移除与当前类型不匹配的属性"""
    allowed = set()
    for attrs in groups.values():
        allowed.update(attrs)
    to_delete = [k for k in hybrid.attributes.keys() if k not in allowed]
    for k in to_delete:
        del hybrid.attributes[k]


# =============================================================================
# 消耗品属性编辑器
# =============================================================================

def _draw_consumable_attributes_editor(hybrid: HybridItemV2) -> None:
    """绘制消耗品属性编辑器 — 垂直列表布局"""
    if not charge_has_charges(hybrid.charges):
        return
    if not isinstance(hybrid.trigger, EffectTrigger):
        return

    consumable_attrs = hybrid.trigger.consumable_attributes

    # === 1. 构建统一的显示列表 ===
    display_list: list[dict] = []

    # 基础属性 (Mandatory)
    display_list.append({
        "key": CONSUMABLE_DURATION_ATTRIBUTE,
        "name": "效果持续 (轮)",
        "is_basic": True,
    })
    display_list.append({
        "key": "Poisoning_Chance",
        "name": "中毒几率 (%)",
        "is_basic": True,
    })

    # 条件基础属性
    if consumable_attrs.get("Poisoning_Chance", 0) > 0:
        display_list.append({
            "key": "Poison_Duration",
            "name": "中毒持续 (轮)",
            "is_basic": True,
            "custom_bind": "poison_duration",
        })

    # 即时效果
    for _grp, attrs in CONSUMABLE_INSTANT_ATTRS.items():
        for attr in attrs:
            if attr == "Poisoning_Chance":
                continue
            if consumable_attrs.get(attr, 0) != 0:
                d_name, d_desc = get_attr_display(attr)
                display_list.append({
                    "key": attr,
                    "name": d_name or attr,
                    "desc": d_desc,
                    "is_basic": False,
                })

    # 持续效果
    dur_keys = get_consumable_duration_attrs()
    dur_groups = get_attribute_groups(dur_keys, DEFAULT_GROUP_ORDER)
    for _grp, attrs in dur_groups.items():
        for attr in attrs:
            if attr == CONSUMABLE_DURATION_ATTRIBUTE:
                continue
            if consumable_attrs.get(attr, 0) != 0:
                d_name, d_desc = get_attr_display(attr)
                display_list.append({
                    "key": attr,
                    "name": d_name or attr,
                    "desc": d_desc,
                    "is_basic": False,
                })

    # === 2. 构建可添加属性列表 ===
    all_instants = []
    for grp, attrs in CONSUMABLE_INSTANT_ATTRS.items():
        for a in attrs:
            if a not in {"Poisoning_Chance"}:
                all_instants.append((a, grp))

    all_durations = []
    for grp, attrs in dur_groups.items():
        for a in attrs:
            if a != CONSUMABLE_DURATION_ATTRIBUTE:
                all_durations.append((a, grp))

    merged_source: list[tuple[str, str]] = []
    for a, g in all_instants:
        suffix = g.split("（")[-1].rstrip("）") if "（" in g else g
        merged_source.append((a, f"即时效果 - {suffix}"))
    for a, g in all_durations:
        merged_source.append((a, f"持续效果 - {g}"))

    # === 3. 渲染垂直列表 ===
    to_remove = _render_attribute_grid(
        display_list,
        consumable_attrs,
        hybrid,
        show_add_button=True,
        add_button_label="+效果",
        add_popup_id="add_consum_effect",
    )

    _draw_add_attribute_popup("add_consum_effect", consumable_attrs, merged_source)

    # === 4. 执行移除 ===
    for attr in to_remove:
        del consumable_attrs[attr]


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_stats_panel"]
