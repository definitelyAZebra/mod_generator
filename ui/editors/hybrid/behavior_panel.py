# -*- coding: utf-8 -*-
"""混合物品编辑器 - 行为面板

"物品做什么" - 装备形态、触发、充能、耐久、生成规则

使用 ui.fields 声明式字段组件消除布局样板代码。
碎片和生成预测已内联到主表单区域 (不再使用弹窗)。
"""

from __future__ import annotations

from ui import imgui_shim as imgui
from ui import tw
from ui import layout as ly
from ui.layout import tooltip
from ui.fields import (
    field_row, enum_field, int_field, toggle_field,
    readonly_field, field_slot,
)

from hybrid_item_v2 import HybridItemV2
from constants import HYBRID_WEAPON_TYPES, HYBRID_ARMOR_TYPES
from specs import (
    WeaponEquip, ArmorEquip, CharmEquip, NotEquipable,
    is_weapon_mode, is_armor_mode, is_charm_mode,
    HasDurability,
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
# Label 映射
# =============================================================================

_EQUIPMENT_MODE_LABELS = {
    "none": "无",
    "weapon": "武器",
    "armor": "护甲",
    "charm": "护符",
}

_TRIGGER_MODE_LABELS = {
    "none": "无",
    "effect": "效果",
    "skill": "技能",
}

_CHARGE_MODE_LABELS = {
    "limited": "有限",
    "unlimited": "无限",
}

_BALANCE_LABELS = {"0": "0", "1": "1", "2": "2", "3": "3", "4": "4"}

_SPAWN_RULE_LABELS = {
    SpawnRuleType.EQUIPMENT: "按装备池",
    SpawnRuleType.ITEM: "按道具池",
    SpawnRuleType.NONE: "不生成",
}


# =============================================================================
# 辅助
# =============================================================================

def _get_eq_mode(hybrid: HybridItemV2) -> str:
    if is_weapon_mode(hybrid.equipment):
        return "weapon"
    if is_armor_mode(hybrid.equipment):
        return "armor"
    if is_charm_mode(hybrid.equipment):
        return "charm"
    return "none"


def _get_trigger_mode(hybrid: HybridItemV2) -> str:
    if isinstance(hybrid.trigger, EffectTrigger):
        return "effect"
    if isinstance(hybrid.trigger, SkillTrigger):
        return "skill"
    return "none"


def _get_durability(hybrid: HybridItemV2) -> HasDurability | None:
    match hybrid.equipment:
        case WeaponEquip(durability=d) if isinstance(d, HasDurability):
            return d
        case ArmorEquip(durability=d) if isinstance(d, HasDurability):
            return d
    return None


# 技能搜索框缓存
_skill_search_buf: str = ""


# =============================================================================
# 主入口
# =============================================================================

def draw_behavior_panel(hybrid: HybridItemV2) -> None:
    """绘制行为面板"""
    _draw_equipment_section(hybrid)

    ly.gap_y(3.5)
    _draw_trigger_section(hybrid)

    if hybrid.has_durability:
        ly.gap_y(3.5)
        _draw_durability_section(hybrid)

    if charge_has_charges(hybrid.charges):
        ly.gap_y(3.5)
        _draw_charges_section(hybrid)

    ly.gap_y(3.5)
    _draw_spawn_section(hybrid)


# =============================================================================
# 装备形态
# =============================================================================

def _draw_equipment_section(hybrid: HybridItemV2) -> None:
    current_mode = _get_eq_mode(hybrid)

    with field_row(4):
        changed, new_mode = enum_field(
            "装备形态", "##eq_mode", current_mode, _EQUIPMENT_MODE_LABELS,
        )
        if changed:
            match new_mode:
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
            eq = hybrid.equipment

            ch, new_wt = enum_field(
                "武器类型", "##wep_type", eq.weapon_type, HYBRID_WEAPON_TYPES,
            )
            if ch:
                object.__setattr__(eq, "weapon_type", new_wt)

            ch, new_bal = enum_field(
                "平衡", "##wep_balance", str(eq.balance), _BALANCE_LABELS,
            )
            if ch:
                object.__setattr__(eq, "balance", int(new_bal))

        elif is_armor_mode(hybrid.equipment):
            assert isinstance(hybrid.equipment, ArmorEquip)
            eq = hybrid.equipment

            ch, new_at = enum_field(
                "护甲类型", "##armor_type", eq.armor_type, HYBRID_ARMOR_TYPES,
            )
            if ch:
                object.__setattr__(eq, "armor_type", new_at)

            readonly_field("护甲分类", hybrid.armor_class)

            if hybrid.slot not in ["hand", "Ring", "Amulet"]:
                pass  # fragments now drawn below

    # 碎片内联网格 (仅护甲非饰品)
    if is_armor_mode(hybrid.equipment) and hybrid.slot not in ["hand", "Ring", "Amulet"]:
        ly.gap_y(2)
        _draw_fragments_inline(hybrid)


# =============================================================================
# 触发
# =============================================================================

def _draw_trigger_section(hybrid: HybridItemV2) -> None:
    old_mode = _get_trigger_mode(hybrid)

    with field_row(2):
        changed, new_mode = enum_field(
            "触发模式", "##trigger_mode", old_mode, _TRIGGER_MODE_LABELS,
        )
        if changed:
            match new_mode:
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
            _draw_skill_picker(hybrid.trigger)


def _draw_skill_picker(trigger: SkillTrigger) -> None:
    """技能选择器 - 平铺分组下拉 (无 tree_node)

    Tailwind: combo dropdown with grouped selectables, search filter
    """
    global _skill_search_buf

    with field_slot("技能") as w:
        imgui.set_next_item_width(w)
        current = trigger.skill_object
        label = SKILL_OBJECT_NAMES.get(current, current) if current else "-- 选择 --"

        if imgui.begin_combo("##skill_object", label):
            # 清除选项
            if imgui.selectable("-- 无 --", current == "")[0]:
                object.__setattr__(trigger, "skill_object", "")

            # 搜索框
            imgui.separator()
            imgui.set_next_item_width(-1)
            ch, _skill_search_buf = imgui.input_text(
                "##skill_search", _skill_search_buf, 64,
            )
            search_lower = _skill_search_buf.lower()
            imgui.separator()

            # 平铺分组列表
            for branch in sorted(SKILL_BY_BRANCH.keys()):
                if branch in ("none", "unknown"):
                    continue
                skills = SKILL_BY_BRANCH[branch]
                if not skills:
                    continue

                branch_label = SKILL_BRANCH_TRANSLATIONS.get(branch, branch)

                # 过滤
                visible: list[tuple[str, str]] = []
                for skill_obj in skills:
                    info = SKILL_OBJECTS.get(skill_obj, {})
                    name = info.get("name_chinese", skill_obj)
                    name_en = info.get("name_english", "")
                    if search_lower and search_lower not in f"{name} {name_en} {skill_obj}".lower():
                        continue
                    visible.append((skill_obj, name))

                if not visible:
                    continue

                # 分支标题
                ly.gap_y(0.5)
                tw.text_accent(imgui.text)(branch_label)

                # 技能列表
                for skill_obj, name in visible:
                    if imgui.selectable(f"  {name}##{skill_obj}", current == skill_obj)[0]:
                        object.__setattr__(trigger, "skill_object", skill_obj)
                        _skill_search_buf = ""

            imgui.end_combo()


# =============================================================================
# 耐久
# =============================================================================

def _draw_durability_section(hybrid: HybridItemV2) -> None:
    durability = _get_durability(hybrid)
    if not durability:
        return

    has_charges = charge_has_charges(hybrid.charges)

    with field_row(3):
        ch, new_val = int_field("耐久上限", "##dur_max", durability.duration_max, vmin=1)
        if ch:
            object.__setattr__(durability, "duration_max", new_val)

        if has_charges:
            ch, new_wear = int_field(
                "磨损%", "##wear", durability.wear_per_use,
                vmin=0, vmax=100,
                tooltip_text="每次使用消耗的耐久百分比",
            )
            if ch:
                object.__setattr__(durability, "wear_per_use", new_wear)

        ch, new_destroy = toggle_field(
            "耐久归零销毁", "##dur_del", durability.destroy_on_zero,
        )
        if ch:
            object.__setattr__(durability, "destroy_on_zero", new_destroy)


# =============================================================================
# 次数 / 充能
# =============================================================================

def _draw_charges_section(hybrid: HybridItemV2) -> None:
    is_unlimited = isinstance(hybrid.charges, UnlimitedCharges)
    current_mode = "unlimited" if is_unlimited else "limited"

    # --- 第一行: 模式 / 值 / 显示 ---
    with field_row(3):
        changed, new_mode = enum_field(
            "次数模式", "##charge_mode", current_mode, _CHARGE_MODE_LABELS,
        )
        if changed:
            if new_mode == "unlimited":
                hybrid.charges = UnlimitedCharges()
                hybrid.charge_recovery = NoRecovery()
            else:
                hybrid.charges = LimitedCharges()

        # 次数值
        if isinstance(hybrid.charges, UnlimitedCharges):
            readonly_field("次数值", "∞")
        elif isinstance(hybrid.charges, LimitedCharges):
            ch, new_max = int_field(
                "次数值", "##charge", hybrid.charges.max_charges, vmin=1,
            )
            if ch:
                object.__setattr__(hybrid.charges, "max_charges", new_max)

        # 显次数点
        current_draw = False
        match hybrid.charges:
            case LimitedCharges(draw_charges=d):
                current_draw = d
            case UnlimitedCharges(draw_charges=d):
                current_draw = d

        ch, new_draw = toggle_field(
            "显次数点", "##show_charge", current_draw,
            tooltip_text="在物品贴图左下角绘制小点表示剩余次数",
        )
        if ch:
            object.__setattr__(hybrid.charges, "draw_charges", new_draw)

    # --- 第二行: 恢复/终止 (仅有限次数) ---
    if isinstance(hybrid.charges, LimitedCharges):
        _draw_recovery_row(hybrid)


def _draw_recovery_row(hybrid: HybridItemV2) -> None:
    """充能恢复行 - 自动恢复 / 恢复间隔 / 耗尽销毁"""
    is_artifact = isinstance(hybrid.quality, ArtifactQuality)
    has_recovery = recovery_has_recovery(hybrid.charge_recovery)

    with field_row(3):
        # 自动恢复
        if is_artifact:
            # 文物强制自动恢复 (锁定)
            if not has_recovery:
                hybrid.charge_recovery = IntervalRecovery()
            with field_slot("自动恢复") as _w:
                imgui.push_style_var(imgui.STYLE_ALPHA, 0.5)
                imgui.checkbox("##recovery_locked", True)
                imgui.pop_style_var()
                tooltip("文物自动恢复")
        else:
            ch, new_recovery = toggle_field("自动恢复", "##recovery", has_recovery)
            if ch:
                if new_recovery:
                    hybrid.charge_recovery = IntervalRecovery()
                else:
                    hybrid.charge_recovery = NoRecovery()

        # 恢复间隔
        if recovery_has_recovery(hybrid.charge_recovery):
            assert isinstance(hybrid.charge_recovery, IntervalRecovery)
            ch, new_interval = int_field(
                "恢复间隔", "##interval",
                hybrid.charge_recovery.interval, vmin=1,
            )
            if ch:
                object.__setattr__(hybrid.charge_recovery, "interval", new_interval)

        # 耗尽销毁
        if not hybrid.has_durability and not is_artifact:
            ch, new_val = toggle_field(
                "耗尽销毁", "##charge_del", hybrid.delete_on_charge_zero,
            )
            if ch:
                hybrid.delete_on_charge_zero = new_val


# =============================================================================
# 生成规则
# =============================================================================

def _draw_spawn_section(hybrid: HybridItemV2) -> None:
    can_use_eq = not isinstance(hybrid.equipment, NotEquipable)
    is_excluded = spawn_is_excluded(hybrid.spawn)

    with field_row(4):
        ch, new_excluded = toggle_field(
            "排除随机生成", "##exc_random", is_excluded,
            tooltip_text="排除随机生成：物品不会在宝箱/商店随机出现\n启用后其他标签设置不生效",
        )
        if ch:
            hybrid.spawn = ExcludedFromRandom() if new_excluded else RandomSpawn()

        if not spawn_is_excluded(hybrid.spawn) and isinstance(hybrid.spawn, RandomSpawn):
            spawn = hybrid.spawn

            # 容器生成
            container_opts = (
                [SpawnRuleType.EQUIPMENT, SpawnRuleType.ITEM, SpawnRuleType.NONE]
                if can_use_eq
                else [SpawnRuleType.ITEM, SpawnRuleType.NONE]
            )
            current_container = hybrid.container_spawn
            if current_container not in container_opts:
                current_container = SpawnRuleType.NONE

            ch_c, new_c = enum_field(
                "容器生成", "##container_spawn",
                current_container, container_opts, _SPAWN_RULE_LABELS,
                tooltip_text=(
                    "容器生成规则（宝箱/桶/尸体等）\n\n"
                    "• 按装备池：根据武器类型/护甲类型 + 标签 + 层级匹配\n"
                    "• 按道具池：根据分类/子分类 + 标签 + 层级匹配\n"
                    "• 不生成：不在容器中随机出现"
                ),
            )
            if ch_c:
                object.__setattr__(spawn, "container_spawn", new_c)

            # 商店生成
            shop_opts = (
                [SpawnRuleType.EQUIPMENT, SpawnRuleType.ITEM, SpawnRuleType.NONE]
                if can_use_eq
                else [SpawnRuleType.ITEM, SpawnRuleType.NONE]
            )
            current_shop = hybrid.shop_spawn
            if current_shop not in shop_opts:
                current_shop = SpawnRuleType.NONE

            ch_s, new_s = enum_field(
                "商店生成", "##shop_spawn",
                current_shop, shop_opts, _SPAWN_RULE_LABELS,
                tooltip_text=(
                    "商店生成规则（商人进货时）\n\n"
                    "• 按装备池：根据武器/护甲/珠宝类别 + 层级 + 材质 + 标签匹配\n"
                    "• 按道具池：根据分类/子分类 + 层级 + 标签匹配\n"
                    "• 不生成：不在商店随机出现"
                ),
            )
            if ch_s:
                object.__setattr__(spawn, "shop_spawn", new_s)

    # 生成预测 — 内联显示在生成规则下方
    ly.gap_y(2)
    _draw_spawn_prediction_inline(hybrid)


# =============================================================================
# 碎片内联网格
# =============================================================================

_FRAG_DATA = [
    ("cloth01", "布1"), ("cloth02", "布2"), ("cloth03", "布3"), ("cloth04", "布4"),
    ("leather01", "皮1"), ("leather02", "皮2"), ("leather03", "皮3"), ("leather04", "皮4"),
    ("metal01", "铁1"), ("metal02", "铁2"), ("metal03", "铁3"), ("metal04", "铁4"),
    ("gold", "金"),
]


def _draw_fragments_inline(hybrid: HybridItemV2) -> None:
    """碎片内联网格 — 4列 label+input 布局

    Tailwind: grid grid-cols-4 gap-2, 每格 label + input
    """
    tw.text_muted(imgui.text)("拆解碎片")
    ly.gap_y(1)

    col_label_w = ly.sz(8)   # 32px
    col_input_w = ly.sz(14)  # 56px
    col_gap = ly.sz(1.5)     # 6px
    pair_gap = ly.sz(4)      # 16px between pairs
    cols_per_row = 4

    for i, (frag_key, frag_label) in enumerate(_FRAG_DATA):
        col_in_row = i % cols_per_row
        if col_in_row == 0 and i > 0:
            pass  # new row (automatic)
        elif col_in_row > 0:
            imgui.same_line(spacing=pair_gap)

        # Label
        imgui.align_text_to_frame_padding()
        val = hybrid.fragments.get(frag_key, 0)
        if val > 0:
            tw.text_default(imgui.text)(frag_label)
        else:
            tw.text_faint(imgui.text)(frag_label)

        imgui.same_line(spacing=col_gap)

        # Input
        imgui.set_next_item_width(col_input_w)
        changed, new_val = imgui.input_int(
            f"##{frag_key}_inline", val, step=0, step_fast=0,
        )
        if changed:
            hybrid.fragments[frag_key] = max(0, new_val)


# =============================================================================
# 生成预测内联
# =============================================================================

def _draw_spawn_prediction_inline(hybrid: HybridItemV2) -> None:
    """生成预测 — 内联显示在生成规则字段下方

    实时显示匹配的容器掉落点和商店 NPC，无需点击弹窗。
    """
    if spawn_is_excluded(hybrid.spawn):
        tw.text_faint(imgui.text)("已排除随机生成")
        return

    # 容器掉落
    if hybrid.container_spawn != SpawnRuleType.NONE:
        tw.text_muted(imgui.text)("容器掉落:")
        imgui.same_line()
        _draw_container_preview(hybrid, is_equipment=(hybrid.container_spawn == SpawnRuleType.EQUIPMENT))

    # 商店进货
    if hybrid.shop_spawn != SpawnRuleType.NONE:
        tw.text_muted(imgui.text)("商店进货:")
        imgui.same_line()
        _draw_shop_preview(hybrid)


def _draw_container_preview(hybrid: HybridItemV2, is_equipment: bool) -> None:
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
        tw.text_muted(imgui.text)("  (无匹配)")
        return

    display = ", ".join(matching)
    imgui.text_wrapped(f"  {display}")


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_behavior_panel"]
