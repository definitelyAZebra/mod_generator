# -*- coding: utf-8 -*-
"""混合物品编辑器 V2 - 响应式卡片布局

Card-based responsive layout。宽屏双列(身份+装备并排)，窄屏单列瀑布。
生成预测作为独立卡片。属性和外观全宽展开。

================================================================================
设计原则
================================================================================

1. 卡片分区: 每个逻辑区域 = 一张 bg_surface 卡片 + rounded + padding
2. 响应式断点: avail_w > BREAKPOINT → 身份+装备并排 (ImGui Table 2col)
3. 滚动条隐藏: NO_SCROLLBAR，鼠标滚轮仍可滚动
4. 字段样式: input_default 由 fields.py 自动注入 (frame_bg + border + rounded)

================================================================================
卡片结构 (宽屏, >1100px 内容区)
================================================================================

    ┌──────── 身份 ──────────┐  ┌──── 装备与触发 ─────┐
    │ ID/品质/等级/...        │  │ 装备形态/类型/平衡   │
    │ 分类/标签               │  │ 触发/次数/恢复      │
    │ 生成规则                │  │                     │
    └────────────────────────┘  └─────────────────────┘
    ┌──── 生成预测 ─────────────────────────────────────┐
    │ 容器: slot1, slot2...  商店: npc1, npc2...        │
    └───────────────────────────────────────────────────┘
    ┌──── 属性 ─────────────────────────────────────────┐
    │ 伤害类型 [...grid...]                              │
    │ 状态效果 [...grid...]                              │
    └───────────────────────────────────────────────────┘
    ┌──── 外观 ─────────────────────────────────────────┐
    │ 贴图 | 音效 | 本地化                               │
    └───────────────────────────────────────────────────┘

================================================================================
"""

from __future__ import annotations

from ui import imgui_shim as imgui

from ui import tw
from ui import layout as ly
from ui.editors.common import draw_indented_separator
from ui.layout import sz
from ui.state import dpi_scale
from hybrid_item_v2 import HybridItemV2
from specs import EffectTrigger, SpawnRuleType, spawn_is_excluded, WeaponEquip, ArmorEquip, RandomSpawn
from models import validate_hybrid_item
from ui.state import state as ui_state
from drop_slot_data import find_matching_slots, find_matching_eq_slots
from shop_configs import NPC_METADATA, SHOP_CONFIGS


# =============================================================================
# 常量
# =============================================================================

_CARD_GAP = 3      # 卡片之间的间距 (12px)
_HEADING_GAP = 2   # 标题与内容间距 (8px)

# 响应式断点: 内容区 > 此值时启用双列
_BREAKPOINT = 275  # tw 单位 (1100px)

# 卡片样式 — p_4 = 16px 内边距
_card_style = tw.bg_surface | tw.child_rounded_md | tw.p_4


# =============================================================================
# 主入口
# =============================================================================

def draw_hybrid_editor(hybrid: HybridItemV2) -> None:
    """混合物品编辑器 - 响应式卡片布局

    Args:
        hybrid: 混合物品数据对象
    """
    from ui.editors.hybrid.base_panel import draw_base_panel
    from ui.editors.hybrid.behavior_panel import draw_behavior_panel
    from ui.editors.hybrid.stats_panel import draw_stats_panel
    from ui.editors.hybrid.presentation_panel import draw_presentation_panel

    show_attrs = _should_show_attributes(hybrid) or isinstance(hybrid.trigger, EffectTrigger)
    has_prediction = _has_spawn_prediction(hybrid)

    # 页面 padding 由外层 HybridEditor child 的 WindowPadding 提供 (p_5=20px)
    avail_w = imgui.get_content_region_available_width()
    is_wide = avail_w > sz(_BREAKPOINT)
    col_gap = sz(_CARD_GAP)

    if is_wide:
        _draw_dual_column_row(
            avail_w, col_gap,
            left_fn=lambda: _draw_card_section("身份", draw_base_panel, hybrid),
            right_fn=lambda: _draw_card_section("装备与触发", draw_behavior_panel, hybrid),
        )
    else:
        _draw_card_section("身份", draw_base_panel, hybrid)
        ly.gap_y(_CARD_GAP)
        _draw_card_section("装备与触发", draw_behavior_panel, hybrid)

    # =================================================================
    # 生成预测卡片 (独立, 全宽)
    # =================================================================
    if has_prediction:
        ly.gap_y(_CARD_GAP)
        _draw_prediction_card(hybrid)

    # =================================================================
    # 属性卡片 (全宽)
    # =================================================================
    if show_attrs:
        ly.gap_y(_CARD_GAP)
        _draw_card_section("属性", draw_stats_panel, hybrid)

    # =================================================================
    # 外观卡片 (全宽)
    # =================================================================
    ly.gap_y(_CARD_GAP)
    _draw_card_section("外观", draw_presentation_panel, hybrid)

    # =================================================================
    # 验证错误
    # =================================================================
    errors = validate_hybrid_item(hybrid, ui_state.project, include_warnings=True)
    if errors:
        ly.gap_y(_CARD_GAP)
        _draw_validation_errors(errors)

    # 底部呼吸空间
    ly.gap_y(4)


# =============================================================================
# 卡片渲染
# =============================================================================

def _draw_card_section(
    title: str,
    panel_fn,
    hybrid: HybridItemV2,
) -> None:
    """渲染一张带标题的 section 卡片

    结构: Card (begin_child auto-height) → heading + panel content
    """
    with _card_style:
        with ly.card(f"##card_{title}") as _state:
            _card_heading(title)
            panel_fn(hybrid)


def _card_heading(title: str) -> None:
    """卡片内标题 — 紫色强调条 + 文字

    Tailwind: border-l-2 border-crystal-500 pl-2 text-crystal-400 text-sm
    """
    screen_x, screen_y = imgui.get_cursor_screen_pos()
    text_h = imgui.get_font_size()
    bar_w = 2 * dpi_scale()
    bar_gap = sz(1.5)

    draw_list = imgui.get_window_draw_list()
    draw_list.add_rect_filled(
        screen_x, screen_y,
        screen_x + bar_w, screen_y + text_h,
        imgui.get_color_u32_rgba(*tw.CRYSTAL_500),
    )

    cursor = imgui.get_cursor_pos()
    imgui.set_cursor_pos((cursor[0] + bar_w + bar_gap, cursor[1]))
    tw.text_accent(imgui.text)(title)
    ly.gap_y(_HEADING_GAP)


# =============================================================================
# 双列布局 (ImGui Table)
# =============================================================================

def _draw_dual_column_row(
    content_w: float,
    col_gap: float,
    left_fn,
    right_fn,
) -> None:
    """用 ImGui Table 实现双列同行, 每列自适应高度"""
    flags = imgui.TABLE_NO_BORDERS_IN_BODY | imgui.TABLE_SIZING_STRETCH_SAME
    col_w = (content_w - col_gap) / 2

    imgui.push_style_var(imgui.STYLE_CELL_PADDING, (col_gap / 2, 0))

    if imgui.begin_table("##dual_col", 2, flags, (content_w, 0)):
        imgui.table_setup_column("##left", 0, col_w)
        imgui.table_setup_column("##right", 0, col_w)
        imgui.table_next_row()

        imgui.table_next_column()
        left_fn()

        imgui.table_next_column()
        right_fn()

        imgui.end_table()

    imgui.pop_style_var()


# =============================================================================
# 生成预测卡片
# =============================================================================

def _draw_prediction_card(hybrid: HybridItemV2) -> None:
    """生成预测卡片 — 容器匹配 + 商店匹配"""
    with _card_style:
        with ly.card("##card_prediction") as _state:
            _card_heading("生成预测")

            has_container = hybrid.container_spawn != SpawnRuleType.NONE
            has_shop = hybrid.shop_spawn != SpawnRuleType.NONE

            if has_container:
                is_eq = hybrid.container_spawn == SpawnRuleType.EQUIPMENT
                tw.text_muted(imgui.text)("容器:")
                imgui.same_line()
                _render_container_matches(hybrid, is_eq)

            if has_shop:
                tw.text_muted(imgui.text)("商店:")
                imgui.same_line()
                _render_shop_matches(hybrid)


def _has_spawn_prediction(hybrid: HybridItemV2) -> bool:
    """判断是否应显示生成预测卡片"""
    if spawn_is_excluded(hybrid.spawn):
        return False
    return (
        hybrid.container_spawn != SpawnRuleType.NONE
        or hybrid.shop_spawn != SpawnRuleType.NONE
    )


# =============================================================================
# 匹配渲染
# =============================================================================

def _render_container_matches(hybrid: HybridItemV2, is_equipment: bool) -> None:
    """渲染容器匹配结果"""
    tags_tuple = tuple(hybrid.effective_tags.split()) if hybrid.effective_tags else ()

    if is_equipment:
        eq_categories: list[str] = []
        match hybrid.equipment:
            case WeaponEquip(weapon_type=wt):
                eq_categories.append(wt)
                eq_categories.append("weapon")
            case ArmorEquip(armor_type=at):
                eq_categories.append(at)
                if at in ("Ring", "Amulet"):
                    eq_categories.append("jewelry")
                else:
                    eq_categories.append("armor")

        if not eq_categories:
            tw.text_faint(imgui.text)("无匹配")
            return

        all_matches = []
        for eq_cat in eq_categories:
            matches = find_matching_eq_slots(eq_cat, tags_tuple, hybrid.tier)
            all_matches.extend(matches)

        if not all_matches:
            tw.text_faint(imgui.text)("无匹配")
            return

        names = list(dict.fromkeys(m["entry_name_cn"] for m in all_matches))
        _render_truncated_names(names)
    else:
        if not (hybrid.cat or hybrid.subcats):
            tw.text_faint(imgui.text)("请设置分类")
            return

        matches = find_matching_slots(
            hybrid.cat, tuple(hybrid.subcats), tags_tuple, hybrid.tier,
        )
        if not matches:
            tw.text_faint(imgui.text)("无匹配")
            return

        names = list(dict.fromkeys(m["entry_name_cn"] for m in matches))
        _render_truncated_names(names)


def _render_truncated_names(names: list[str], max_display: int = 8) -> None:
    """渲染名称列表, 超过 max_display 个则截断并显示计数"""
    if not names:
        tw.text_faint(imgui.text)("无匹配")
        return
    if len(names) <= max_display:
        display = ", ".join(names)
    else:
        display = ", ".join(names[:max_display]) + f" …+{len(names) - max_display}"
    tw.text_default(imgui.text)(display)


def _render_shop_matches(hybrid: HybridItemV2) -> None:
    """渲染商店匹配结果"""
    matching: list[str] = []

    if hybrid.shop_spawn == SpawnRuleType.ITEM:
        if not (hybrid.cat or hybrid.subcats):
            tw.text_faint(imgui.text)("请设置分类")
            return
        item_cats = set([hybrid.cat] + list(hybrid.subcats))
        item_tags = set(hybrid.effective_tags.split()) if hybrid.effective_tags else set()

        for objects_tuple, config in SHOP_CONFIGS.items():
            selling_cats = config.get("selling_loot_category", {})
            tier_range = config.get("tier_range", [1, 1])
            trade_tags = set(config.get("trade_tags", []))
            matched_cats = item_cats & set(selling_cats.keys())
            if not matched_cats:
                continue
            if hybrid.tier > 0 and not (tier_range[0] <= hybrid.tier <= tier_range[1]):
                continue
            if trade_tags and item_tags and not item_tags.issubset(trade_tags):
                continue
            for obj in objects_tuple:
                meta = NPC_METADATA.get(obj, {})
                name = meta.get("name_zh") or meta.get("name_en")
                if name:
                    town = meta.get("town_zh") or meta.get("town") or ""
                    matching.append(f"{town}·{name}" if town else name)
    else:
        item_tier = hybrid.tier
        item_material = hybrid.material
        item_tags = set(hybrid.effective_tags.split()) if hybrid.effective_tags else set()

        item_weapon_type = None
        item_armor_slot = None
        match hybrid.equipment:
            case WeaponEquip(weapon_type=wt):
                item_weapon_type = wt
            case ArmorEquip(armor_type=at):
                item_armor_slot = at

        is_jewelry = (
            item_armor_slot in ("ring", "amulet", "Ring", "Amulet")
            if item_armor_slot
            else False
        )

        for objects_tuple, config in SHOP_CONFIGS.items():
            selling_cats = set(config.get("selling_loot_category", {}).keys())
            tier_range = config.get("tier_range", [1, 1])
            material_spec = config.get("material_spec", ["all"])
            trade_tags = set(config.get("trade_tags", []))

            category_matched = False
            if "weapon" in selling_cats and item_weapon_type:
                category_matched = True
            elif "armor" in selling_cats and item_armor_slot and not is_jewelry:
                category_matched = True
            elif "jewelry" in selling_cats and is_jewelry:
                category_matched = True

            if not category_matched:
                continue
            if item_tier > 0 and not (tier_range[0] <= item_tier <= tier_range[1]):
                continue
            if "all" not in material_spec and item_material not in material_spec:
                continue
            if trade_tags and (not item_tags or not item_tags.issubset(trade_tags)):
                continue

            for obj in objects_tuple:
                meta = NPC_METADATA.get(obj, {})
                name = meta.get("name_zh") or meta.get("name_en")
                if name:
                    town = meta.get("town_zh") or meta.get("town") or ""
                    matching.append(f"{town}·{name}" if town else name)

    if not matching:
        tw.text_faint(imgui.text)("无匹配")
        return

    _render_truncated_names(matching)


# =============================================================================
# 验证错误
# =============================================================================

def _draw_validation_errors(errors: list[str]) -> None:
    """绘制验证错误区域"""
    with tw.bg_app | tw.border_blood_700 | tw.child_border_size(1) | tw.rounded_md | tw.p_3:
        with ly.card("##validation_errors") as _state:
            draw_indented_separator()
            imgui.text("消息:")
            for error in errors:
                if error.endswith("):"):
                    continue
                content = error.lstrip()
                if content.startswith("• WARNING:"):
                    imgui.text("  ")
                    imgui.same_line()
                    tw.text_warning(imgui.text)("!")
                    imgui.same_line()
                    tw.text_warning(imgui.text)(content[10:].strip())
                elif content.startswith("\u2022"):
                    imgui.text("  ")
                    imgui.same_line()
                    tw.text_error(imgui.text)("X")
                    imgui.same_line()
                    tw.text_error(imgui.text)(content[1:].strip())
                else:
                    imgui.text("  ")
                    imgui.same_line()
                    tw.text_error(imgui.text)("X")
                    imgui.same_line()
                    tw.text_error(imgui.text)(error)


# =============================================================================
# 辅助
# =============================================================================

def _should_show_attributes(hybrid: HybridItemV2) -> bool:
    """判断是否显示属性加成编辑器"""
    from specs import is_weapon_mode, is_armor_mode, is_charm_mode
    return (
        is_weapon_mode(hybrid.equipment)
        or is_armor_mode(hybrid.equipment)
        or is_charm_mode(hybrid.equipment)
    )


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_hybrid_editor"]
