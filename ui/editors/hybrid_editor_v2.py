# -*- coding: utf-8 -*-
"""混合物品编辑器 V2 - 单页滚动布局 + 浮动预测条

废除 Tab Bar，所有表单区域在同一页面内纵向排列，通过视觉分隔符分区。
浮动预测条固定在编辑器底部，实时显示匹配的容器掉落点和商店 NPC。

设计原则:
    - 所有内容始终可见，滚动即达，无需点击发现
    - 不使用 gui god object
    - 每个 panel 函数接收 hybrid 数据对象
    - 遵循 tw/ly UI 规范
    - 验证错误固定在底部

================================================================================
样式设计规范 (Tailwind 思路)
================================================================================

布局结构:
    ```jsx
    <div className="flex flex-col h-full bg-abyss-900">
      {/* 可滚动的单页表单 */}
      <div className="flex-1 overflow-y-auto px-4 py-2.5">
        {/* Section: 身份 — "这是什么物品" */}
        <SectionHeading accent>身份</SectionHeading>
        <BasePanel />   {/* ID/品质/等级/价格/重量/材质 + 分类标签 + 生成规则 */}

        <SectionDivider />

        {/* Section: 装备与触发 — "物品做什么" */}
        <SectionHeading accent>装备与触发</SectionHeading>
        <BehaviorPanel />  {/* 装备形态/触发/耐久/充能 */}

        <SectionDivider />

        {/* Section: 属性 (条件) — "数值配置" */}
        <SectionHeading accent>属性</SectionHeading>
        <StatsPanel />

        <SectionDivider />

        {/* Section: 外观 — "怎么呈现给玩家" */}
        <SectionHeading accent>外观</SectionHeading>
        <PresentationPanel />
      </div>

      {/* 浮动预测条 — 固定在底部 */}
      <PredictionBar />

      {/* 验证错误区 - 在预测条上方 */}
      <ErrorBox />
    </div>
    ```

间距常量:
    - CONTENT_PX = 4 (16px) - 内容区水平内边距
    - CONTENT_PY = 2.5 (10px) - 内容区顶部内边距
    - SECTION_GAP = 5 (20px) - 区域之间的间距
    - HEADING_GAP = 2.5 (10px) - 标题与内容之间的间距
    - ERROR_GAP = 2 (8px) - 错误区与内容间距
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
# 间距常量 (Tailwind 单位: 1 = 4px)
# =============================================================================

_CONTENT_PX = 4      # 内容区水平内边距 (16px)
_CONTENT_PY = 2.5    # 内容区顶部内边距 (10px)
_SECTION_GAP = 5     # 区域之间间距 (20px)
_HEADING_GAP = 2.5   # 标题与内容间距 (10px)
_ERROR_GAP = 2       # 错误区与内容间距 (8px)
_PREDICTION_H = 10   # 预测条高度 (40px)


def draw_hybrid_editor(hybrid: HybridItemV2) -> None:
    """混合物品编辑器 - 单页滚动表单

    布局结构:
        ┌─────────────────────────────────────────────────────┐
        │ ← px=16 →  │身份                      section 标题 │
        │  ID  品质  等级  价格  重量  材质    field_flow 行  │
        │  分类 [badge...] / 标签 [badge...]                  │
        │  生成规则: 排除 / 容器 / 商店                       │
        │─────────────────────────────────────── 视觉分隔符 ──│
        │  │装备与触发                                        │
        │  装备形态 / 武器类型 / 触发 / 耐久 / 充能           │
        │─────────────────────────────────────── 视觉分隔符 ──│
        │  │属性                                              │
        │  全属性网格 (label+input) × 3                       │
        │─────────────────────────────────────── 视觉分隔符 ──│
        │  │外观                                              │
        │  贴图 / 音效 / 本地化                               │
        └─────────────────────────────────────────────────────┘

    Args:
        hybrid: 混合物品数据对象
    """
    from ui.editors.hybrid.base_panel import draw_base_panel
    from ui.editors.hybrid.behavior_panel import draw_behavior_panel
    from ui.editors.hybrid.stats_panel import draw_stats_panel
    from ui.editors.hybrid.presentation_panel import draw_presentation_panel

    show_attrs = _should_show_attributes(hybrid) or isinstance(hybrid.trigger, EffectTrigger)

    # =========================================================================
    # 顶部间距 + 水平缩进
    # =========================================================================
    ly.gap_y(_CONTENT_PY)
    imgui.indent(ly.sz(_CONTENT_PX))

    # =========================================================================
    # Section 1: 身份 — "这是什么物品"
    # =========================================================================
    _section_heading("身份")
    draw_base_panel(hybrid)

    # =========================================================================
    # Section 2: 装备与触发 — "物品做什么"
    # =========================================================================
    _section_divider()
    _section_heading("装备与触发")
    draw_behavior_panel(hybrid)

    # =========================================================================
    # Section 3: 属性 (条件显示) — "数值配置"
    # =========================================================================
    if show_attrs:
        _section_divider()
        _section_heading("属性")
        draw_stats_panel(hybrid)

    # =========================================================================
    # Section 4: 外观 — "怎么呈现给玩家"
    # =========================================================================
    _section_divider()
    _section_heading("外观")
    draw_presentation_panel(hybrid)

    # =========================================================================
    # 底部留白 (滚动尾部呼吸空间)
    # =========================================================================
    ly.gap_y(_SECTION_GAP)

    imgui.unindent(ly.sz(_CONTENT_PX))

    # =========================================================================
    # 验证错误区域
    # =========================================================================
    errors = validate_hybrid_item(hybrid, ui_state.project, include_warnings=True)
    if errors:
        ly.gap_y(_ERROR_GAP)
        _draw_validation_errors(errors)


# =============================================================================
# 内部组件
# =============================================================================

def _section_heading(title: str) -> None:
    """区域标题 — 带左侧紫色强调条

    Tailwind: border-l-2 border-crystal-500 pl-2 text-crystal-400 text-sm
    """
    screen_x, screen_y = imgui.get_cursor_screen_pos()
    text_h = imgui.get_font_size()
    bar_w = 2 * dpi_scale()
    bar_gap = sz(1.5)  # 6px gap between bar and text

    # 绘制紫色强调条
    draw_list = imgui.get_window_draw_list()
    draw_list.add_rect_filled(
        screen_x, screen_y,
        screen_x + bar_w, screen_y + text_h,
        imgui.get_color_u32_rgba(*tw.CRYSTAL_500),
    )

    # 文字偏移到强调条右侧
    cursor = imgui.get_cursor_pos()
    imgui.set_cursor_pos((cursor[0] + bar_w + bar_gap, cursor[1]))
    tw.text_accent(imgui.text)(title)
    ly.gap_y(_HEADING_GAP)


def _section_divider() -> None:
    """区域分隔符 — 间距 + 细线 + 间距

    Tailwind: my-5 border-t border-stone-700/50
    """
    ly.gap_y(_SECTION_GAP)
    # 细线
    cursor_x, cursor_y = imgui.get_cursor_screen_pos()
    max_x = cursor_x + imgui.get_content_region_available_width()
    draw_list = imgui.get_window_draw_list()
    draw_list.add_line(
        cursor_x, cursor_y, max_x, cursor_y,
        imgui.get_color_u32_rgba(*tw.STONE_800), 1.0
    )
    imgui.dummy(0, 1)
    ly.gap_y(_SECTION_GAP)


# =============================================================================
# 浮动预测条 (由 main_editor 在滚动区域外调用)
# =============================================================================

def draw_prediction_bar(hybrid: HybridItemV2, width: float) -> None:
    """浮动预测条 — 实时显示匹配的容器掉落点和商店 NPC

    绘制在滚动区域外部，始终可见。结构:
        ┌─────────────────────────────────────┐
        │ 容器: slot1, slot2...  │ 商店: npc1 │
        └─────────────────────────────────────┘
    """
    if spawn_is_excluded(hybrid.spawn):
        return

    has_container = hybrid.container_spawn != SpawnRuleType.NONE
    has_shop = hybrid.shop_spawn != SpawnRuleType.NONE
    if not has_container and not has_shop:
        return

    bar_h = sz(_PREDICTION_H)
    with tw.bg_abyss_800 | tw.border_abyss_600 | tw.child_border_size(1) | tw.p_1:
        imgui.begin_child("##prediction_bar", width, bar_h, border=True)

    # 容器掉落
    if has_container:
        is_eq = hybrid.container_spawn == SpawnRuleType.EQUIPMENT
        tw.text_muted(imgui.text)("容器:")
        imgui.same_line()
        _render_container_matches(hybrid, is_eq)

        if has_shop:
            imgui.same_line(spacing=sz(4))

    # 商店进货
    if has_shop:
        tw.text_muted(imgui.text)("商店:")
        imgui.same_line()
        _render_shop_matches(hybrid)

    imgui.end_child()


def _render_container_matches(hybrid: HybridItemV2, is_equipment: bool) -> None:
    """渲染容器匹配结果 (内联文字)"""
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
        tw.text_default(imgui.text)(", ".join(names))
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
        tw.text_default(imgui.text)(", ".join(names))


def _render_shop_matches(hybrid: HybridItemV2) -> None:
    """渲染商店匹配结果 (内联文字)"""
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

    tw.text_default(imgui.text)(", ".join(matching))


def _draw_validation_errors(errors: list[str]) -> None:
    """绘制验证错误区域 (standalone, 不依赖 gui)"""
    with tw.bg_app | tw.border_blood_700 | tw.child_border_size(1) | tw.rounded_md | tw.p_3:
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


def _should_show_attributes(hybrid: HybridItemV2) -> bool:
    """判断是否显示属性加成编辑器"""
    from specs import is_weapon_mode, is_armor_mode, is_charm_mode
    return (
        is_weapon_mode(hybrid.equipment)
        or is_armor_mode(hybrid.equipment)
        or is_charm_mode(hybrid.equipment)
    )


__all__ = ["draw_hybrid_editor", "draw_prediction_bar"]
