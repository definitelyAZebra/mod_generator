# -*- coding: utf-8 -*-
"""混合物品编辑器 - 身份面板

"这是什么物品" - 物品的身份信息、分类、标签和生成规则

使用 ui.fields 声明式字段组件：
  - field_flow: 身份属性 (ID/品质/等级/价格/重量/材质) + 生成规则
  - 分类和标签组使用徽章+弹窗的特殊 UI，保留手动布局

Tailwind 映射:
    flex flex-wrap gap-2  → field_flow(gap=2)
    text-stone-400 text-sm → tw.text_muted (field 自动)
    flex flex-wrap gap-2  → same_line() + 手动换行
"""

from __future__ import annotations

from ui import imgui_shim as imgui

from ui import tw
from ui import layout as ly
from ui.layout import tooltip
from ui.fields import (
    field_flow, enum_field, int_field, text_field,
    toggle_field, readonly_field,
)

from core.hybrid_item import HybridItemV2
from constants import (
    HYBRID_QUALITY_LABELS,
    HYBRID_WEIGHT_LABELS,
    HYBRID_MATERIALS,
)
from data.drop_slots import (
    SELECTABLE_CATEGORIES,
    SELECTABLE_SUBCATEGORY_OPTIONS,
    CATEGORY_TRANSLATIONS,
    QUALITY_TAGS,
    DUNGEON_TAGS,
    COUNTRY_TAGS,
    EXTRA_TAGS,
)
from core.specs import (
    QualitySpec, ARTIFACT_CATEGORY,
    ExcludedFromRandom, RandomSpawn, SpawnRuleType,
)
from ui.scale import Sp, dp


# =============================================================================
# 间距常量 (Tailwind 单位: 1 = 4px)
# =============================================================================

_SUB_GAP = Sp.S3_5   # 子区之间的间距 (14px)


# =============================================================================
# Label 映射 (从 behavior_panel 迁移)
# =============================================================================

_SPAWN_RULE_LABELS = {
    SpawnRuleType.EQUIPMENT: "按装备池",
    SpawnRuleType.ITEM: "按道具池",
    SpawnRuleType.NONE: "不生成",
}


# =============================================================================
# 本地辅助组件 (徽章 — 非标准控件，保留手动布局)
# =============================================================================

def _badge(id_suffix: str, text: str, removable: bool = True) -> bool:
    """徽章组件"""
    style = tw.btn_abyss if removable else tw.btn_crystal
    with style | tw.rounded_sm | tw.p_1:
        clicked = imgui.button(f"{text}##{id_suffix}_badge")

    if removable:
        tooltip("点击移除")
    return clicked and removable


def _locked_badge(id_suffix: str, text: str, reason: str) -> None:
    """锁定徽章 - 不可移除"""
    with tw.btn_crystal | tw.rounded_sm | tw.p_1:
        imgui.button(f"{text}##{id_suffix}_badge")
    tooltip(f"[{reason}]")


# =============================================================================
# 主入口
# =============================================================================

def draw_base_panel(hybrid: HybridItemV2) -> None:
    """绘制身份面板

    Args:
        hybrid: 混合物品数据对象
    """
    # 1. 身份属性: ID / 品质 / 等级 / 价格 / 重量 / 材质 (field_flow)
    _draw_identity_flow(hybrid)

    ly.gap_y(_SUB_GAP)

    # 2. 分类组: 主分类 / 子分类
    _draw_category_section(hybrid)

    ly.gap_y(_SUB_GAP)

    # 3. 标签组
    _draw_tags_section(hybrid)

    ly.gap_y(_SUB_GAP)

    # 4. 生成规则 (从 behavior_panel 迁移)
    _draw_spawn_section(hybrid)


# =============================================================================
# 身份属性 field_flow: ID / 品质 / 等级 / 价格 / 重量 / 材质
# =============================================================================

def _draw_identity_flow(hybrid: HybridItemV2) -> None:
    """身份 + 物理属性合并为一个 field_flow

    Tailwind: flex flex-wrap gap-2
    ID 较宽 (40tw=160px), 其他字段自然宽度 (25~35tw)
    """
    quality_int = hybrid.quality.value

    with field_flow(gap=Sp.S2, row_gap=Sp.S2, default_width=Sp.S28):
        # ID (较宽)
        ch, new_id = text_field("ID", "##hybrid_id", hybrid.id,
                                width=Sp.S40,
                                tooltip_text="物品唯一标识符")
        if ch:
            hybrid.id = new_id

        # 品质
        ch, new_q = enum_field(
            "品质", "##quality_hybrid",
            quality_int,
            HYBRID_QUALITY_LABELS,
            width=Sp.S28,
        )
        if ch:
            hybrid.set_quality(QualitySpec.from_int(new_q))

        # 等级
        if hybrid.quality == QualitySpec.ARTIFACT:
            readonly_field("等级", "T0 (文物固定)",
                           width=Sp.S28,
                           tooltip_text="文物品质固定为等级 0")
        else:
            tier_labels = {0: "全", 1: "1", 2: "2", 3: "3", 4: "4", 5: "5"}
            ch, new_t = enum_field(
                "等级", "##tier_hybrid", hybrid.tier, tier_labels,
                width=Sp.S20,
                tooltip_text="用于掉落/商店筛选",
            )
            if ch:
                hybrid.tier = new_t

        # 价格
        ch, new_price = int_field("价格", "##price_hybrid", hybrid.base_price,
                                  width=Sp.S24, vmin=0)
        if ch:
            hybrid.base_price = new_price

        # 重量
        ch, new_w = enum_field(
            "重量", "##weight_hybrid", hybrid.weight, HYBRID_WEIGHT_LABELS,
            width=Sp.S24,
            tooltip_text="影响游泳；护甲时决定类别",
        )
        if ch:
            hybrid.weight = new_w

        # 材质
        ch, new_m = enum_field("材质", "##material_hybrid", hybrid.material,
                               HYBRID_MATERIALS, width=Sp.S28)
        if ch:
            hybrid.material = new_m


# =============================================================================
# 分类组: 主分类 / 子分类
# =============================================================================

def _draw_category_section(hybrid: HybridItemV2) -> None:
    """分类设置: 主分类 + 子分类徽章

    Tailwind: flex flex-wrap gap-2
    """
    is_artifact = hybrid.quality == QualitySpec.ARTIFACT
    forced_cat = ARTIFACT_CATEGORY if is_artifact else None

    # 构建选项: 强制分类时锁定单选, 否则允许 "无" + 全部可选分类
    if forced_cat is not None:
        cat_options: list[str] = [forced_cat]
    else:
        cat_options = ["", *SELECTABLE_CATEGORIES]
    cat_labels: dict[str, str] = {"": "—", **CATEGORY_TRANSLATIONS}

    tw.text_muted(imgui.text)("分类")
    ly.gap_y(Sp.S1)

    # 使用 wrap 布局实现自动换行 + gap
    with ly.wrap("cat_section", gap_x=Sp.S2, gap_y=Sp.S2) as w:
        # 主分类下拉
        w.next()
        if forced_cat is not None:
            imgui.push_style_var(imgui.STYLE_ALPHA, 0.6)

        imgui.push_item_width(dp(Sp.S24))  # 96px

        with tw.input_default:
            current_label = str(cat_labels.get(hybrid.cat, hybrid.cat))
            if imgui.begin_combo("##cat_hybrid", current_label):
                for opt in cat_options:
                    display = str(cat_labels.get(opt, opt))
                    if imgui.selectable(display, opt == hybrid.cat)[0]:
                        if forced_cat is None:
                            hybrid.cat = opt
                imgui.end_combo()

        imgui.pop_item_width()

        if forced_cat is not None:
            imgui.pop_style_var()

        tooltip("主分类 (Cat)\n用于掉落表匹配")

        # 添加子分类按钮
        w.next()
        _fh = imgui.get_frame_height()
        if (tw.btn_secondary)(imgui.button)("+##add_subcat", _fh, _fh):
            imgui.open_popup("subcats_popup")
        tooltip("添加子分类 (Subcats)\n可多选")

        # 已选子分类徽章
        for subcat in sorted(hybrid.subcats):
            w.next()
            if _badge(subcat, CATEGORY_TRANSLATIONS.get(subcat, subcat)):
                hybrid.subcats.remove(subcat)
                break  # 避免在迭代时修改列表

    # 子分类 popup
    _draw_subcats_popup(hybrid)


def _draw_subcats_popup(hybrid: HybridItemV2) -> None:
    """子分类选择弹窗"""
    if imgui.begin_popup("subcats_popup"):
        for subcat in SELECTABLE_SUBCATEGORY_OPTIONS:
            is_selected = subcat in hybrid.subcats
            is_disabled = subcat == hybrid.cat

            if is_disabled:
                imgui.push_style_var(imgui.STYLE_ALPHA, 0.5)

            changed, new_value = imgui.checkbox(
                f"{CATEGORY_TRANSLATIONS.get(subcat, subcat)}##subcat_{subcat}",
                is_selected,
            )

            if changed and not is_disabled:
                if new_value:
                    hybrid.subcats.append(subcat)
                else:
                    hybrid.subcats.remove(subcat)

            if is_disabled:
                imgui.pop_style_var()
        imgui.end_popup()


# =============================================================================
# 标签组
# =============================================================================

def _draw_tags_section(hybrid: HybridItemV2) -> None:
    """标签设置: 品质标签 + 地牢/国家/其他标签

    Tailwind: flex flex-wrap gap-2
    """
    tw.text_muted(imgui.text)("标签")
    ly.gap_y(Sp.S1)

    # 特殊情况: 排除随机生成时只显示 special
    if isinstance(hybrid.spawn, ExcludedFromRandom):
        _locked_badge("special_only", EXTRA_TAGS.get("special", "特殊"), "已排除随机生成")
        return

    # 正常模式 - wrap 布局自动换行
    if not isinstance(hybrid.spawn, RandomSpawn):
        return
    spawn = hybrid.spawn

    with ly.wrap("tags_section", gap_x=Sp.S2, gap_y=Sp.S2) as w:
        # 添加标签按钮 (方形，匹配徽章高度)
        w.next()
        _fh = imgui.get_frame_height()
        if (tw.btn_secondary)(imgui.button)("+##add_tag", _fh, _fh):
            imgui.open_popup("tags_popup")
        tooltip("添加标签")

        # 品质标签 (锁定)
        if spawn.quality_tag:
            w.next()
            _locked_badge(
                spawn.quality_tag,
                QUALITY_TAGS.get(spawn.quality_tag, spawn.quality_tag),
                "由品质自动设置",
            )

        # 地牢标签
        if spawn.dungeon_tag:
            w.next()
            if _badge(f"dungeon_{spawn.dungeon_tag}", DUNGEON_TAGS.get(spawn.dungeon_tag, spawn.dungeon_tag)):
                spawn.dungeon_tag = ""

        # 国家标签
        if spawn.country_tag:
            w.next()
            if _badge(f"country_{spawn.country_tag}", COUNTRY_TAGS.get(spawn.country_tag, spawn.country_tag)):
                spawn.country_tag = ""

        # 其他标签
        for tag in list(spawn.extra_tags):
            w.next()
            if _badge(f"extra_{tag}", EXTRA_TAGS.get(tag, tag)):
                spawn.extra_tags.remove(tag)
                break  # 避免在迭代时修改列表

    # 标签选择 popup
    _draw_tags_popup(spawn)


def _draw_tags_popup(spawn: RandomSpawn) -> None:
    """标签选择弹窗"""
    if imgui.begin_popup("tags_popup"):
        tw.text_muted(imgui.text)("地牢")
        for tag_val, tag_label in DUNGEON_TAGS.items():
            if imgui.radio_button(f"{tag_label}##dungeon", spawn.dungeon_tag == tag_val):
                spawn.dungeon_tag = tag_val

        imgui.separator()

        tw.text_muted(imgui.text)("国家/地区")
        for tag_val, tag_label in COUNTRY_TAGS.items():
            if imgui.radio_button(f"{tag_label}##country", spawn.country_tag == tag_val):
                spawn.country_tag = tag_val

        imgui.separator()

        tw.text_muted(imgui.text)("其他")
        for tag_val, tag_label in EXTRA_TAGS.items():
            if tag_val == "special":
                continue
            is_selected = tag_val in spawn.extra_tags
            changed, new_value = imgui.checkbox(f"{tag_label}##extra_{tag_val}", is_selected)
            if changed:
                if new_value:
                    spawn.extra_tags.append(tag_val)
                else:
                    spawn.extra_tags.remove(tag_val)

        imgui.end_popup()


# =============================================================================
# 生成规则 (从 behavior_panel 迁移)
# =============================================================================

def _draw_spawn_section(hybrid: HybridItemV2) -> None:
    """生成规则: 排除随机生成 / 容器生成 / 商店生成

    Tailwind: flex flex-wrap gap-2
    """
    spawn_rules = hybrid.available_spawn_rules

    with field_flow(gap=Sp.S2, row_gap=Sp.S2, default_width=Sp.S28):
        ch, new_excluded = toggle_field(
            "排除随机生成", "##exc_random", isinstance(hybrid.spawn, ExcludedFromRandom),
            width=Sp.S28,
            tooltip_text="排除随机生成：物品不会在宝箱/商店随机出现\n启用后其他标签设置不生效",
        )
        if ch:
            hybrid.spawn = ExcludedFromRandom() if new_excluded else RandomSpawn()

        if isinstance(hybrid.spawn, RandomSpawn):
            spawn = hybrid.spawn

            # 容器生成
            ch_c, new_c = enum_field(
                "容器生成", "##container_spawn",
                spawn.container_spawn, spawn_rules, _SPAWN_RULE_LABELS,
                width=Sp.S28,
                tooltip_text=(
                    "容器生成规则（宝箱/桶/尸体等）\n\n"
                    "• 按装备池：根据武器类型/护甲类型 + 标签 + 层级匹配\n"
                    "• 按道具池：根据分类/子分类 + 标签 + 层级匹配\n"
                    "• 不生成：不在容器中随机出现"
                ),
            )
            if ch_c:
                spawn.container_spawn = new_c

            # 商店生成
            ch_s, new_s = enum_field(
                "商店生成", "##shop_spawn",
                spawn.shop_spawn, spawn_rules, _SPAWN_RULE_LABELS,
                width=Sp.S28,
                tooltip_text=(
                    "商店生成规则（商人进货时）\n\n"
                    "• 按装备池：根据武器/护甲/珠宝类别 + 层级 + 材质 + 标签匹配\n"
                    "• 按道具池：根据分类/子分类 + 层级 + 标签匹配\n"
                    "• 不生成：不在商店随机出现"
                ),
            )
            if ch_s:
                spawn.shop_spawn = new_s


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_base_panel"]
