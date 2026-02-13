# -*- coding: utf-8 -*-
"""混合物品编辑器 - 装备与触发面板

"物品做什么" - 装备形态、触发、充能、耐久

使用 ui.fields 声明式字段组件消除布局样板代码。
碎片已内联到装备形态下方。
生成规则已迁移到 base_panel (身份面板)。
生成预测已迁移到 hybrid_editor_v2 (浮动预测条)。
"""

from __future__ import annotations

from ui import imgui_shim as imgui
from ui import tw
from ui import layout as ly
from ui.scale import Sp, dp
from ui.layout import tooltip
from ui.fields import (
    field_row, enum_field, int_field, toggle_field,
    readonly_field, field_slot,
)

from core.hybrid_item import HybridItemV2
from constants import HYBRID_WEAPON_TYPES, HYBRID_ARMOR_TYPES
from core.specs import (
    WeaponEquip, ArmorEquip, CharmEquip, NotEquipable,
    is_weapon_mode, is_armor_mode, is_charm_mode,
    char_texture_for_equipment,
    HasDurability,
    NoTrigger, EffectTrigger, SkillTrigger,
    NoCharges, LimitedCharges, UnlimitedCharges,
    charge_has_charges,
    NoRecovery, IntervalRecovery,
    recovery_has_recovery,
    QualitySpec,
)
from data.skills import (
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


def _sync_char_texture(hybrid: HybridItemV2) -> None:
    """同步 textures.char 类型与当前 equipment 匹配

    仅在类型不一致时替换，避免丢弃用户已设置的贴图数据。
    """
    expected = char_texture_for_equipment(hybrid.equipment)
    if type(hybrid.textures.char) is not type(expected):
        hybrid.textures.char = expected


# 技能搜索框缓存
_skill_search_buf: str = ""


# =============================================================================
# 主入口
# =============================================================================

def draw_behavior_panel(hybrid: HybridItemV2, *, flex_extra: float = 0) -> None:
    """绘制装备与触发面板

    Args:
        hybrid: 混合物品数据对象
        flex_extra: 由 equal_height_row 传入的剩余拉伸空间,
                   在面板底部以 dummy 填充使卡片撑满等高行.
    """
    _draw_equipment_section(hybrid)

    ly.gap_y(Sp.S4)
    _draw_trigger_section(hybrid)

    if hybrid.has_durability:
        ly.gap_y(Sp.S4)
        _draw_durability_section(hybrid)

    if charge_has_charges(hybrid.charges):
        ly.gap_y(Sp.S4)
        _draw_charges_section(hybrid)

    # flex 填充: 短列底部空白撑满等高行
    if flex_extra > 2:
        imgui.dummy(0, flex_extra)


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
            _sync_char_texture(hybrid)

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
                _sync_char_texture(hybrid)

            readonly_field("护甲分类", hybrid.armor_class)

            if hybrid.slot not in ["hand", "Ring", "Amulet"]:
                pass  # fragments now drawn below

    # 碎片内联网格 (仅护甲非饰品)
    if is_armor_mode(hybrid.equipment) and hybrid.slot not in ["hand", "Ring", "Amulet"]:
        ly.gap_y(Sp.S2)
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
                ly.gap_y(Sp.S0_5)
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
        ly.gap_y(Sp.S2)
        _draw_recovery_row(hybrid)


def _draw_recovery_row(hybrid: HybridItemV2) -> None:
    """充能恢复行 - 自动恢复 / 恢复间隔 / 耗尽销毁"""
    is_artifact = hybrid.quality == QualitySpec.ARTIFACT
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
# 碎片内联网格
# =============================================================================

_FRAG_DATA = [
    ("cloth01", "布1"), ("cloth02", "布2"), ("cloth03", "布3"), ("cloth04", "布4"),
    ("leather01", "皮1"), ("leather02", "皮2"), ("leather03", "皮3"), ("leather04", "皮4"),
    ("metal01", "铁1"), ("metal02", "铁2"), ("metal03", "铁3"), ("metal04", "铁4"),
    ("gold", "金"),
]


def _draw_fragments_inline(hybrid: HybridItemV2) -> None:
    """碎片内联网格 — 4列 label+input 布局 (ImGui Table)

    Tailwind: grid grid-cols-4 gap-2, 每格 label + input
    """
    tw.text_muted(imgui.text)("拆解碎片")
    ly.gap_y(Sp.S1)

    input_w = dp(Sp.S14)    # 56px 固定输入宽度
    cell_px = dp(Sp.S2)     # 8px 列间距
    cell_py = dp(Sp.S1)     # 4px 行间距
    cols_per_row = 4
    table_cols = cols_per_row * 2  # label + input per logical column

    imgui.push_style_var(imgui.STYLE_CELL_PADDING, (cell_px, cell_py))

    flags = imgui.TABLE_SIZING_FIXED_FIT | imgui.TABLE_NO_BORDERS_IN_BODY
    if imgui.begin_table("##frags", table_cols, flags):
        for _c in range(cols_per_row):
            imgui.table_setup_column(f"##fl{_c}")  # label: auto-fit
            imgui.table_setup_column(
                f"##fi{_c}", imgui.TABLE_COLUMN_WIDTH_FIXED, input_w,
            )

        with tw.input_default:
            for i, (frag_key, frag_label) in enumerate(_FRAG_DATA):
                if i % cols_per_row == 0:
                    imgui.table_next_row()

                val = hybrid.fragments.get(frag_key, 0)

                # Label
                imgui.table_next_column()
                imgui.align_text_to_frame_padding()
                label_style = tw.text_default if val > 0 else tw.text_faint
                label_style(imgui.text)(frag_label)

                # Input
                imgui.table_next_column()
                imgui.set_next_item_width(-1)
                changed, new_val = imgui.input_int(
                    f"##{frag_key}_inline", val, step=0, step_fast=0,
                )
                if changed:
                    hybrid.fragments[frag_key] = max(0, new_val)

        imgui.end_table()

    imgui.pop_style_var()


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_behavior_panel"]
