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

from __future__ import annotations
from typing import Any

from ui import imgui_shim as imgui

from ui import tw
from ui import layout as ly
from ui.editors.common import (
    CARD_GAP,
    BREAKPOINT_PX,
    CARD_STYLE,
    card_heading,
    draw_card_section,
    draw_card_content,
    draw_validation_card,
)
from ui.scale import Sp  # noqa: F401  # pyright: ignore[reportUnusedImport]
from ui.state import dpi_scale
from core.hybrid_item import HybridItemV2
from core.specs import EffectTrigger, SpawnRuleType, RandomSpawn, WeaponEquip, ArmorEquip, CharmEquip, NotEquipable
from core.models import validate_hybrid_item
from ui.state import state as ui_state
from data.drop_slots import find_matching_slots, find_matching_eq_slots
from data.shops import NPC_METADATA, SHOP_CONFIGS


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
    from ui.editors.hybrid.presentation_panel import draw_textures_panel, draw_sound_panel, draw_localization_panel

    show_attrs = _should_show_attributes(hybrid) or isinstance(hybrid.trigger, EffectTrigger)
    has_prediction = _has_spawn_prediction(hybrid)

    # 页面 padding 由外层 HybridEditor child 的 WindowPadding 提供 (p_5=20px)
    avail_w = imgui.get_content_region_available_width()
    is_wide = avail_w > BREAKPOINT_PX * dpi_scale()

    if is_wide:
        with ly.equal_height_row("##dual_col", cols=2, gap=CARD_GAP) as row:
            with row.col(0, style=CARD_STYLE):
                draw_card_content("身份", lambda: draw_base_panel(hybrid))
            with row.col(1, style=CARD_STYLE):
                draw_card_content("装备与触发", lambda: draw_behavior_panel(hybrid))
    else:
        draw_card_section("身份", lambda: draw_base_panel(hybrid))
        ly.gap_y(CARD_GAP)
        draw_card_section("装备与触发", lambda: draw_behavior_panel(hybrid))

    # =================================================================
    # 生成预测卡片 (独立, 全宽)
    # =================================================================
    if has_prediction:
        ly.gap_y(CARD_GAP)
        _draw_prediction_card(hybrid)

    # =================================================================
    # 属性卡片 (全宽)
    # =================================================================
    if show_attrs:
        ly.gap_y(CARD_GAP)
        draw_card_section("属性", lambda: draw_stats_panel(hybrid))

    # =================================================================
    # 贴图 + 音效 + 本地化 (响应式双列)
    # =================================================================
    ly.gap_y(CARD_GAP)
    if is_wide:
        with ly.equal_height_row("##dual_col_pres", cols=2, gap=CARD_GAP) as row:
            with row.col(0, style=CARD_STYLE):
                draw_card_content("贴图", lambda: draw_textures_panel(hybrid))
            with row.col(1):  # 透明列, 内含两张独立卡片
                # 音效卡片 (AutoResizeY)
                draw_card_section("音效", lambda: draw_sound_panel(hybrid))
                ly.gap_y(CARD_GAP)

                # 本地化卡片 (填充剩余高度)
                remaining_h = imgui.get_content_region_available().y
                draw_card_section("本地化", lambda: draw_localization_panel(hybrid), height=remaining_h)
    else:
        draw_card_section("贴图", lambda: draw_textures_panel(hybrid))
        ly.gap_y(CARD_GAP)
        draw_card_section("音效", lambda: draw_sound_panel(hybrid))
        ly.gap_y(CARD_GAP)
        draw_card_section("本地化", lambda: draw_localization_panel(hybrid))

    # =================================================================
    # 验证错误
    # =================================================================
    errors = validate_hybrid_item(hybrid, ui_state.project, include_warnings=True)
    if errors:
        ly.gap_y(CARD_GAP)
        draw_validation_card(errors, "hybrid")

    # 底部呼吸空间
    # ly.gap_y(Sp.S4)


# =============================================================================
# 生成预测卡片
# =============================================================================

def _draw_prediction_card(hybrid: HybridItemV2) -> None:
    """生成预测卡片 — 容器匹配 + 商店匹配"""
    with CARD_STYLE:
        with ly.card("##card_prediction") as _state:
            card_heading("生成预测")

            assert isinstance(hybrid.spawn, RandomSpawn)
            spawn = hybrid.spawn

            has_container = spawn.container_spawn != SpawnRuleType.NONE
            has_shop = spawn.shop_spawn != SpawnRuleType.NONE

            if has_container:
                is_eq = spawn.container_spawn == SpawnRuleType.EQUIPMENT
                tw.text_muted(imgui.text)("容器:")
                imgui.same_line()
                _render_container_matches(hybrid, is_eq)

            if has_shop:
                tw.text_muted(imgui.text)("商店:")
                imgui.same_line()
                _render_shop_matches(hybrid)


def _has_spawn_prediction(hybrid: HybridItemV2) -> bool:
    """判断是否应显示生成预测卡片"""
    match hybrid.spawn:
        case RandomSpawn(container_spawn=c, shop_spawn=s):
            return c != SpawnRuleType.NONE or s != SpawnRuleType.NONE
        case _:
            return False


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
            case _:
                pass

        if not eq_categories:
            tw.text_faint(imgui.text)("无匹配")
            return

        all_matches: list[dict[str, Any]] = []
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
    assert isinstance(hybrid.spawn, RandomSpawn)
    matching: list[str] = []

    if hybrid.spawn.shop_spawn == SpawnRuleType.ITEM:
        if not (hybrid.cat or hybrid.subcats):
            tw.text_faint(imgui.text)("请设置分类")
            return
        item_cats = set([hybrid.cat] + list(hybrid.subcats))
        item_tags: set[str] = set(hybrid.effective_tags.split()) if hybrid.effective_tags else set()

        for objects_tuple, config in SHOP_CONFIGS.items():
            selling_cats: dict[str, Any] = config.get("selling_loot_category", {})  # type: ignore[assignment]
            tier_range: list[int] = config.get("tier_range", [1, 1])  # type: ignore[assignment]
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
        item_tags: set[str] = set(hybrid.effective_tags.split()) if hybrid.effective_tags else set()

        item_weapon_type = None
        item_armor_slot = None
        match hybrid.equipment:
            case WeaponEquip(weapon_type=wt):
                item_weapon_type = wt
            case ArmorEquip(armor_type=at):
                item_armor_slot = at
            case _:
                pass

        is_jewelry = (
            item_armor_slot in ("ring", "amulet", "Ring", "Amulet")
            if item_armor_slot
            else False
        )

        for objects_tuple, config in SHOP_CONFIGS.items():
            selling_cats = set(config.get("selling_loot_category", {}).keys())  # type: ignore[union-attr]
            tier_range: list[int] = config.get("tier_range", [1, 1])  # type: ignore[assignment]
            material_spec: list[str] = config.get("material_spec", ["all"])  # type: ignore[assignment]
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
# 辅助
# =============================================================================

def _should_show_attributes(hybrid: HybridItemV2) -> bool:
    """判断是否显示属性加成编辑器"""
    return not isinstance(hybrid.equipment, NotEquipable)


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_hybrid_editor"]
