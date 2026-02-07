# -*- coding: utf-8 -*-
"""混合物品编辑器 - 行为面板

"物品做什么" - 装备形态、触发、充能、耐久、生成规则

================================================================================
样式设计规范
================================================================================

布局结构:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ 形态组: [装备形态] [武器类型/护甲类型] [平衡/分类]      grid-cols-3     │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                         gap-y = 20px    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ 触发组: [触发模式] [技能]                               grid-cols-2     │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                         gap-y = 20px    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ 耐久组: [耐久上限] [磨损%] [归零销毁]                   grid-cols-3     │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                         gap-y = 20px    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ 次数组: [次数模式] [次数值] [显次数点]                   grid-cols-3     │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                         gap-y = 20px    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ 生成组: [排除随机] [容器生成] [商店生成] [预测]          grid-cols-4     │
    └─────────────────────────────────────────────────────────────────────────┘

注意: 本面板暂用旧版 GridLayout，后续将迁移到 ly.columns()。
================================================================================
"""

from __future__ import annotations

from ui import imgui_shim as imgui
from ui import tw

from ui.grid import GridLayout
from ui.layout import tooltip, item_width
from ui.styles import (
    gap_m, gap_s, grid_gap,
    SPAN_INPUT, SPAN_BADGE, GRID_DEBUG,
)
import ui.styles as styles

from hybrid_item_v2 import HybridItemV2
from constants import (
    HYBRID_WEAPON_TYPES,
    HYBRID_ARMOR_TYPES,
)
from specs import (
    WeaponEquip, ArmorEquip, CharmEquip, NotEquipable,
    is_weapon_mode, is_armor_mode, is_charm_mode,
    NoDurability, HasDurability,
    NoTrigger, EffectTrigger, SkillTrigger,
    NoCharges, LimitedCharges, UnlimitedCharges,
    charge_has_charges,
    NoRecovery, IntervalRecovery,
    recovery_has_recovery,
    ExcludedFromRandom, RandomSpawn, SpawnRuleType,
    spawn_is_excluded,
    ArtifactQuality,
)
from drop_slot_data import find_matching_slots, find_matching_eq_slots
from shop_configs import NPC_METADATA, SHOP_CONFIGS
from skill_constants import (
    SKILL_OBJECTS,
    SKILL_BRANCH_TRANSLATIONS,
    SKILL_BY_BRANCH,
    SKILL_OBJECT_NAMES,
)


# =============================================================================
# 本地辅助组件
# =============================================================================

def _enum_combo(label: str, current_value, options: list, labels: dict):
    """值模式下拉框 — 返回选中的值"""
    current_label = str(labels.get(current_value, current_value))
    new_value = current_value

    if current_value not in options:
        options = list(options) + [current_value]

    if imgui.begin_combo(label, current_label):
        for opt in options:
            display = str(labels.get(opt, opt))
            if imgui.selectable(display, opt == current_value)[0]:
                new_value = opt
        imgui.end_combo()

    return new_value


# =============================================================================
# 主入口
# =============================================================================

def draw_behavior_panel(hybrid: HybridItemV2) -> None:
    """绘制行为面板

    Args:
        hybrid: 混合物品数据对象
    """
    grid = GridLayout(lambda t: tw.text_muted(imgui.text)(t))

    # ━━━ 形态行 ━━━
    _draw_equipment_section(grid, hybrid)

    imgui.dummy(0, gap_m())

    # ━━━ 触发组 ━━━
    _draw_trigger_section(grid, hybrid)

    # ━━━ 耐久组（条件显示）━━━
    if hybrid.has_durability:
        imgui.dummy(0, gap_m())
        _draw_durability_section(grid, hybrid)

    # ━━━ 次数组（条件显示）━━━
    if charge_has_charges(hybrid.charges):
        imgui.dummy(0, gap_m())
        _draw_charges_section(grid, hybrid)

    imgui.dummy(0, gap_m())

    # ━━━ 生成组 ━━━
    _draw_spawn_section(grid, hybrid)


# =============================================================================
# 装备形态
# =============================================================================

# UI 标签映射
_EQUIPMENT_MODE_LABELS = {
    "none": "无",
    "weapon": "武器",
    "armor": "护甲",
    "charm": "护符",
}


def _get_eq_mode(hybrid: HybridItemV2) -> str:
    if is_weapon_mode(hybrid.equipment):
        return "weapon"
    elif is_armor_mode(hybrid.equipment):
        return "armor"
    elif is_charm_mode(hybrid.equipment):
        return "charm"
    return "none"


def _draw_equipment_section(grid: GridLayout, hybrid: HybridItemV2) -> None:
    current_eq_mode = _get_eq_mode(hybrid)

    # Label 行
    grid.label_header("装备形态", SPAN_INPUT)
    if is_weapon_mode(hybrid.equipment):
        grid.next_cell()
        grid.label_header("武器类型", SPAN_INPUT)
        grid.next_cell()
        grid.label_header("平衡", SPAN_INPUT)
    elif is_armor_mode(hybrid.equipment):
        grid.next_cell()
        grid.label_header("护甲类型", SPAN_INPUT)
        grid.next_cell()
        grid.label_header("护甲分类", SPAN_INPUT)
        if hybrid.slot not in ["hand", "Ring", "Amulet"]:
            grid.next_cell()
            grid.label_header("碎片数", SPAN_INPUT)

    # Control 行
    grid.field_width(SPAN_INPUT)
    new_eq_mode = _enum_combo(
        "##eq_mode", current_eq_mode,
        list(_EQUIPMENT_MODE_LABELS.keys()), _EQUIPMENT_MODE_LABELS,
    )
    if new_eq_mode != current_eq_mode:
        match new_eq_mode:
            case "weapon":
                hybrid.equipment = WeaponEquip()
            case "armor":
                hybrid.equipment = ArmorEquip()
            case "charm":
                hybrid.equipment = CharmEquip()
            case _:
                hybrid.equipment = NotEquipable()

    if is_weapon_mode(hybrid.equipment):
        assert isinstance(hybrid.equipment, WeaponEquip)
        weapon_eq = hybrid.equipment
        grid.next_cell()
        grid.field_width(SPAN_INPUT)
        new_wt = _enum_combo(
            "##wep_type", weapon_eq.weapon_type,
            list(HYBRID_WEAPON_TYPES.keys()), HYBRID_WEAPON_TYPES,
        )
        if new_wt != weapon_eq.weapon_type:
            object.__setattr__(weapon_eq, "weapon_type", new_wt)

        grid.next_cell()
        grid.field_width(SPAN_INPUT)
        balance_options = {"0": "0", "1": "1", "2": "2", "3": "3", "4": "4"}
        new_balance = int(_enum_combo(
            "##wep_balance", str(weapon_eq.balance),
            list(balance_options.keys()), balance_options,
        ))
        if new_balance != weapon_eq.balance:
            object.__setattr__(weapon_eq, "balance", new_balance)

    elif is_armor_mode(hybrid.equipment):
        assert isinstance(hybrid.equipment, ArmorEquip)
        armor_eq = hybrid.equipment
        grid.next_cell()
        grid.field_width(SPAN_INPUT)
        old_armor_type = armor_eq.armor_type
        new_armor_type = _enum_combo(
            "##armor_type", armor_eq.armor_type,
            list(HYBRID_ARMOR_TYPES.keys()), HYBRID_ARMOR_TYPES,
        )
        if new_armor_type != old_armor_type:
            object.__setattr__(armor_eq, "armor_type", new_armor_type)

        grid.next_cell()
        grid.text_cell(hybrid.armor_class, SPAN_INPUT)

        if hybrid.slot not in ["hand", "Ring", "Amulet"]:
            grid.next_cell()
            frag_count = sum(hybrid.fragments.values())
            if grid.button_cell(f"({frag_count})##frags", SPAN_INPUT):
                imgui.open_popup("fragments_popup")
            _draw_fragments_popup(hybrid)


# =============================================================================
# 触发
# =============================================================================

_TRIGGER_MODE_LABELS = {
    "none": "无",
    "effect": "效果",
    "skill": "技能",
}


def _draw_trigger_section(grid: GridLayout, hybrid: HybridItemV2) -> None:
    current_trigger_mode = "none"
    if isinstance(hybrid.trigger, EffectTrigger):
        current_trigger_mode = "effect"
    elif isinstance(hybrid.trigger, SkillTrigger):
        current_trigger_mode = "skill"

    # Label 行
    grid.label_header("触发模式", SPAN_INPUT)
    if isinstance(hybrid.trigger, SkillTrigger):
        grid.next_cell()
        grid.label_header("技能", SPAN_INPUT)

    # Control 行
    grid.field_width(SPAN_INPUT)
    old_trigger_mode = current_trigger_mode
    new_trigger_mode = _enum_combo(
        "##trigger_mode", current_trigger_mode,
        list(_TRIGGER_MODE_LABELS.keys()), _TRIGGER_MODE_LABELS,
    )
    if new_trigger_mode != old_trigger_mode:
        match new_trigger_mode:
            case "effect":
                hybrid.trigger = EffectTrigger()
                if not charge_has_charges(hybrid.charges):
                    hybrid.charges = LimitedCharges()
            case "skill":
                hybrid.trigger = SkillTrigger()
                if not charge_has_charges(hybrid.charges):
                    hybrid.charges = LimitedCharges()
            case _:
                hybrid.trigger = NoTrigger()
                hybrid.charges = NoCharges()

    if isinstance(hybrid.trigger, SkillTrigger):
        skill_trigger = hybrid.trigger
        grid.next_cell()
        grid.field_width(SPAN_INPUT)
        current_skill = skill_trigger.skill_object
        current_label = SKILL_OBJECT_NAMES.get(current_skill, current_skill) if current_skill else "-- 选择 --"
        if imgui.begin_combo("##skill_object", current_label):
            if imgui.selectable("-- 无 --", current_skill == "")[0]:
                object.__setattr__(skill_trigger, "skill_object", "")
            imgui.separator()
            for branch in sorted(SKILL_BY_BRANCH.keys()):
                branch_label = SKILL_BRANCH_TRANSLATIONS.get(branch, branch)
                skills = SKILL_BY_BRANCH[branch]
                if not skills or branch in ("none", "unknown"):
                    continue
                if imgui.tree_node(f"{branch_label}##branch_{branch}"):
                    for skill_obj in skills:
                        skill_info = SKILL_OBJECTS.get(skill_obj, {})
                        skill_name = skill_info.get("name_chinese", skill_obj)
                        if imgui.selectable(f"{skill_name}##{skill_obj}", current_skill == skill_obj)[0]:
                            object.__setattr__(skill_trigger, "skill_object", skill_obj)
                    imgui.tree_pop()
            imgui.end_combo()


# =============================================================================
# 耐久
# =============================================================================

def _draw_durability_section(grid: GridLayout, hybrid: HybridItemV2) -> None:
    durability: HasDurability | None = None
    match hybrid.equipment:
        case WeaponEquip(durability=d) if isinstance(d, HasDurability):
            durability = d
        case ArmorEquip(durability=d) if isinstance(d, HasDurability):
            durability = d

    if not durability:
        return

    has_charges = charge_has_charges(hybrid.charges)

    # Label 行
    grid.label_header("耐久上限", SPAN_INPUT)
    grid.next_cell()
    if has_charges:
        grid.label_header("磨损%", SPAN_INPUT)
        grid.next_cell()
    grid.label_header("耐久归零销毁", SPAN_INPUT)

    # Control 行
    grid.field_width(SPAN_INPUT)
    changed, new_dur_max = imgui.input_int("##dur_max", durability.duration_max)
    if changed:
        object.__setattr__(durability, "duration_max", max(1, new_dur_max))
    grid.next_cell()

    if has_charges:
        grid.field_width(SPAN_INPUT)
        changed, new_wear = imgui.input_int("##wear", durability.wear_per_use)
        tooltip("每次使用消耗的耐久百分比")
        if changed:
            object.__setattr__(durability, "wear_per_use", max(0, min(100, new_wear)))
        grid.next_cell()

    _, new_destroy = grid.checkbox_cell("##dur_del", durability.destroy_on_zero, SPAN_INPUT)
    if new_destroy != durability.destroy_on_zero:
        object.__setattr__(durability, "destroy_on_zero", new_destroy)


# =============================================================================
# 次数 / 充能
# =============================================================================

_CHARGE_MODE_LABELS = {
    "limited": "有限",
    "unlimited": "无限",
}


def _draw_charges_section(grid: GridLayout, hybrid: HybridItemV2) -> None:
    is_unlimited = isinstance(hybrid.charges, UnlimitedCharges)
    current_charge_mode = "unlimited" if is_unlimited else "limited"

    # --- 第一行: 模式 / 值 / 显示 ---
    grid.label_header("次数模式", SPAN_INPUT)
    grid.next_cell()
    grid.label_header("次数值", SPAN_INPUT)
    grid.next_cell()
    grid.label_header("显次数点", SPAN_INPUT)

    # Control 行
    grid.field_width(SPAN_INPUT)
    new_charge_mode = _enum_combo(
        "##charge_mode", current_charge_mode,
        list(_CHARGE_MODE_LABELS.keys()), _CHARGE_MODE_LABELS,
    )
    if new_charge_mode != current_charge_mode:
        if new_charge_mode == "unlimited":
            hybrid.charges = UnlimitedCharges()
            hybrid.charge_recovery = NoRecovery()
        else:
            hybrid.charges = LimitedCharges()

    grid.next_cell()
    if isinstance(hybrid.charges, UnlimitedCharges):
        grid.text_cell("∞", SPAN_INPUT)
    elif isinstance(hybrid.charges, LimitedCharges):
        charges = hybrid.charges
        grid.field_width(SPAN_INPUT)
        changed, new_max = imgui.input_int("##charge", charges.max_charges)
        if changed:
            object.__setattr__(charges, "max_charges", max(1, new_max))

    grid.next_cell()
    current_draw = False
    match hybrid.charges:
        case LimitedCharges(draw_charges=d):
            current_draw = d
        case UnlimitedCharges(draw_charges=d):
            current_draw = d

    _, new_draw = grid.checkbox_cell("##show_charge", current_draw, SPAN_INPUT)
    tooltip("在物品贴图左下角绘制小点表示剩余次数")
    if new_draw != current_draw:
        object.__setattr__(hybrid.charges, "draw_charges", new_draw)

    # --- 第二行: 恢复/终止 (仅有限次数) ---
    if isinstance(hybrid.charges, LimitedCharges):
        is_artifact = isinstance(hybrid.quality, ArtifactQuality)

        grid.label_header("自动恢复", SPAN_INPUT)
        has_recovery = recovery_has_recovery(hybrid.charge_recovery)
        if has_recovery:
            grid.next_cell()
            grid.label_header("恢复间隔", SPAN_INPUT)
        if not hybrid.has_durability and not is_artifact:
            grid.next_cell()
            grid.label_header("耗尽销毁", SPAN_INPUT)

        # Control 行
        if is_artifact:
            if not has_recovery:
                hybrid.charge_recovery = IntervalRecovery()
            imgui.push_style_var(imgui.STYLE_ALPHA, 0.5)
            grid.checkbox_cell("##recovery_locked", True, SPAN_INPUT)
            imgui.pop_style_var()
            tooltip("文物自动恢复")
        else:
            _, new_recovery = grid.checkbox_cell("##recovery", has_recovery, SPAN_INPUT)
            if new_recovery != has_recovery:
                if new_recovery:
                    hybrid.charge_recovery = IntervalRecovery()
                else:
                    hybrid.charge_recovery = NoRecovery()

        if recovery_has_recovery(hybrid.charge_recovery):
            assert isinstance(hybrid.charge_recovery, IntervalRecovery)
            recovery = hybrid.charge_recovery
            grid.next_cell()
            grid.field_width(SPAN_INPUT)
            changed, new_interval = imgui.input_int("##interval", recovery.interval)
            if changed:
                object.__setattr__(recovery, "interval", max(1, new_interval))

        if not hybrid.has_durability and not is_artifact:
            grid.next_cell()
            _, hybrid.delete_on_charge_zero = grid.checkbox_cell(
                "##charge_del", hybrid.delete_on_charge_zero, SPAN_INPUT,
            )


# =============================================================================
# 生成规则
# =============================================================================

def _draw_spawn_section(grid: GridLayout, hybrid: HybridItemV2) -> None:
    spawn_rule_labels = {
        SpawnRuleType.EQUIPMENT: "按装备池",
        SpawnRuleType.ITEM: "按道具池",
        SpawnRuleType.NONE: "不生成",
    }
    can_use_equipment = not isinstance(hybrid.equipment, NotEquipable)

    is_excluded = spawn_is_excluded(hybrid.spawn)
    current_container = hybrid.container_spawn
    current_shop = hybrid.shop_spawn

    # Label 行
    grid.label_header("排除随机生成", SPAN_INPUT)
    grid.next_cell()
    if not is_excluded:
        grid.label_header("容器生成", SPAN_INPUT)
        grid.next_cell()
        grid.label_header("商店生成", SPAN_INPUT)
        grid.next_cell()
    grid.label_header("生成预测", SPAN_INPUT)

    # Control 行
    _, new_excluded = grid.checkbox_cell("##exc_random", is_excluded, SPAN_INPUT)
    tooltip("排除随机生成：物品不会在宝箱/商店随机出现\n启用后其他标签设置不生效")
    if new_excluded != is_excluded:
        if new_excluded:
            hybrid.spawn = ExcludedFromRandom()
        else:
            hybrid.spawn = RandomSpawn()

    grid.next_cell()
    if not new_excluded and isinstance(hybrid.spawn, RandomSpawn):
        spawn = hybrid.spawn

        # 容器
        grid.field_width(SPAN_INPUT)
        container_options = (
            [SpawnRuleType.EQUIPMENT, SpawnRuleType.ITEM, SpawnRuleType.NONE]
            if can_use_equipment
            else [SpawnRuleType.ITEM, SpawnRuleType.NONE]
        )
        if current_container not in container_options:
            current_container = SpawnRuleType.NONE
        if imgui.begin_combo("##container_spawn", spawn_rule_labels[current_container]):
            for rule in container_options:
                if imgui.selectable(spawn_rule_labels[rule], current_container == rule)[0]:
                    object.__setattr__(spawn, "container_spawn", rule)
            imgui.end_combo()
        tooltip(
            "容器生成规则（宝箱/桶/尸体等）\n\n"
            "• 按装备池：根据武器类型/护甲类型 + 标签 + 层级匹配\n"
            "• 按道具池：根据分类/子分类 + 标签 + 层级匹配\n"
            "• 不生成：不在容器中随机出现"
        )

        grid.next_cell()
        # 商店
        grid.field_width(SPAN_INPUT)
        shop_options = (
            [SpawnRuleType.EQUIPMENT, SpawnRuleType.ITEM, SpawnRuleType.NONE]
            if can_use_equipment
            else [SpawnRuleType.ITEM, SpawnRuleType.NONE]
        )
        if current_shop not in shop_options:
            current_shop = SpawnRuleType.NONE
        if imgui.begin_combo("##shop_spawn", spawn_rule_labels[current_shop]):
            for rule in shop_options:
                if imgui.selectable(spawn_rule_labels[rule], current_shop == rule)[0]:
                    object.__setattr__(spawn, "shop_spawn", rule)
            imgui.end_combo()
        tooltip(
            "商店生成规则（商人进货时）\n\n"
            "• 按装备池：根据武器/护甲/珠宝类别 + 层级 + 材质 + 标签匹配\n"
            "• 按道具池：根据分类/子分类 + 层级 + 标签匹配\n"
            "• 不生成：不在商店随机出现"
        )

        grid.next_cell()

    # 生成预测按钮
    if grid.button_cell("▶##gen_preview", SPAN_INPUT):
        imgui.open_popup("generation_preview_popup")
    tooltip("查看生成预测")
    _draw_generation_preview_popup(hybrid)


# =============================================================================
# 碎片弹窗
# =============================================================================

def _draw_fragments_popup(hybrid: HybridItemV2) -> None:
    if imgui.begin_popup("fragments_popup"):
        imgui.text("拆解碎片")
        imgui.separator()
        tw.text_muted(imgui.text)("拆解物品时可获得的材料碎片")

        frag_data = [
            ("cloth01", "布1"), ("cloth02", "布2"), ("cloth03", "布3"), ("cloth04", "布4"),
            ("leather01", "皮1"), ("leather02", "皮2"), ("leather03", "皮3"), ("leather04", "皮4"),
            ("metal01", "铁1"), ("metal02", "铁2"), ("metal03", "铁3"), ("metal04", "铁4"),
            ("gold", "金"),
        ]

        imgui.dummy(0, gap_s())

        if imgui.begin_table("frag_popup_table", 4, imgui.TABLE_SIZING_STRETCH_SAME):
            imgui.table_setup_column("L1", imgui.TABLE_COLUMN_WIDTH_FIXED, 30)
            imgui.table_setup_column("I1", imgui.TABLE_COLUMN_WIDTH_FIXED, 50)
            imgui.table_setup_column("L2", imgui.TABLE_COLUMN_WIDTH_FIXED, 30)
            imgui.table_setup_column("I2", imgui.TABLE_COLUMN_WIDTH_FIXED, 50)

            for i, (frag_key, frag_label) in enumerate(frag_data):
                if i % 2 == 0:
                    imgui.table_next_row()

                imgui.table_next_column()
                imgui.text(frag_label)

                imgui.table_next_column()
                val = hybrid.fragments.get(frag_key, 0)
                with item_width(-1):
                    changed, new_val = imgui.input_int(f"##{frag_key}_popup", val, step=0, step_fast=0)
                if changed:
                    hybrid.fragments[frag_key] = max(0, new_val)

            imgui.end_table()

        imgui.end_popup()


# =============================================================================
# 生成预测弹窗
# =============================================================================

def _draw_generation_preview_popup(hybrid: HybridItemV2) -> None:
    imgui.set_next_window_size(500, 350, imgui.ALWAYS)
    if imgui.begin_popup("generation_preview_popup"):
        imgui.text("生成预测")
        imgui.separator()

        if spawn_is_excluded(hybrid.spawn):
            tw.text_muted(imgui.text)("物品已排除随机生成")
            imgui.text("不会出现在宝箱掉落、商店库存中")
        else:
            # 容器掉落
            imgui.text("容器掉落:")
            if hybrid.container_spawn == SpawnRuleType.NONE:
                tw.text_muted(imgui.text)("  关闭")
            elif hybrid.container_spawn == SpawnRuleType.EQUIPMENT:
                _draw_container_preview(hybrid, is_equipment=True)
            else:
                _draw_container_preview(hybrid, is_equipment=False)

            imgui.dummy(0, gap_m())

            # 商店进货
            imgui.text("商店进货:")
            if hybrid.shop_spawn == SpawnRuleType.NONE:
                tw.text_muted(imgui.text)("  关闭")
            else:
                _draw_shop_preview(hybrid)

            imgui.dummy(0, gap_m())

        imgui.end_popup()


def _draw_container_preview(hybrid: HybridItemV2, is_equipment: bool) -> None:
    tags_tuple = tuple(hybrid.effective_tags.split()) if hybrid.effective_tags else ()

    if is_equipment:
        eq_categories = []
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
            tw.text_muted(imgui.text)("  (无匹配)")
            return

        all_matches = []
        for eq_cat in eq_categories:
            matches = find_matching_eq_slots(eq_cat, tags_tuple, hybrid.tier)
            all_matches.extend(matches)

        if not all_matches:
            tw.text_muted(imgui.text)("  (无匹配)")
            return

        names = list(dict.fromkeys(m["entry_name_cn"] for m in all_matches))
        display = ", ".join(names)
        imgui.text_wrapped(f"  {display}")
    else:
        if not (hybrid.cat or hybrid.subcats):
            tw.text_muted(imgui.text)("  (请设置分类)")
            return

        matches = find_matching_slots(
            hybrid.cat, tuple(hybrid.subcats), tags_tuple, hybrid.tier,
        )
        if not matches:
            tw.text_muted(imgui.text)("  (无匹配)")
            return

        names = list(dict.fromkeys(m["entry_name_cn"] for m in matches))
        display = ", ".join(names)
        imgui.text_wrapped(f"  {display}")


def _draw_shop_preview(hybrid: HybridItemV2) -> None:
    matching: list[str] = []

    if hybrid.shop_spawn == SpawnRuleType.ITEM:
        if not (hybrid.cat or hybrid.subcats):
            tw.text_muted(imgui.text)("  (请设置分类)")
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

        is_jewelry = item_armor_slot in ("ring", "amulet", "Ring", "Amulet") if item_armor_slot else False

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
        tw.text_muted(imgui.text)("  (无匹配)")
        return

    display = ", ".join(matching)
    imgui.text_wrapped(f"  {display}")


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_behavior_panel"]
