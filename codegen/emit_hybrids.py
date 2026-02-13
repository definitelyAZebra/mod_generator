# -*- coding: utf-8 -*-
"""混合物品 C# 方法生成

生成 AddHybrid{id}() 方法，包含：
- 游戏对象创建（o_inv_ / o_loot_）
- 物品元数据注入（InjectItemStats）
- 本地化注入
- GML 事件代码（Create_0 / Step_0 / Alarm_0 / Other_10/13/16/24）
- 偏移注入（武器/盾牌类）
- 战利品动画设置

依赖：
- codegen.textures（format_description / calculate_clamped_origin）
- codegen.emit_items（emit_anchor_gml_block — 共享偏移 bytecode 生成）
"""
from __future__ import annotations

from typing import Any

from constants import (
    CONSUMABLE_INSTANT_ATTRS,
    DAMAGE_ATTRIBUTES,
)
from core.hybrid_item import HybridItemV2
from core.specs import (
    AbsoluteFps,
    ArmorEquip,
    QualitySpec,
    LimitedCharges,
    NoTrigger,
    RelativeSpeed,
    SkillTrigger,
    UnlimitedCharges,
    WeaponCharTexture,
    WeaponEquip,
)
from codegen.textures import calculate_clamped_origin, format_description
from codegen.emit_items import emit_anchor_gml_block


# ------------------------------------------------------------------
# 常量
# ------------------------------------------------------------------

TIER_TO_ENUM = {1: "Tier1", 2: "Tier2", 3: "Tier3", 4: "Tier4", 5: "Tier5"}
WEIGHT_TO_ENUM = {
    "VeryLight": "VeryLight", "Very Light": "VeryLight",
    "Light": "Light", "Medium": "Medium", "Heavy": "Heavy", "Net": "Net",
}

# bytecode 锚点匹配模式（与 emit_items 相同）
_ANCHOR_MATCH_GML = """pushi.e 34
conv.i.v
pushi.e 29
conv.i.v
call.i @@NewGMLArray@@(argc=2)
pushi.e 16635
conv.i.v
pushglb.v global.customizationAnchors
call.i ds_map_add(argc=3)
popz.v"""


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def emit_hybrid_item_method(item: HybridItemV2, escape_fn: _EscapeFn) -> str:
    """生成单个混合物品的完整 C# 方法

    Args:
        item: 混合物品数据
        escape_fn: C# verbatim string 转义函数
    """
    method_name = f"AddHybrid{item.id}"

    code = f"    private void {method_name}()\n    {{\n"
    code += _emit_objects(item)
    code += _emit_events(item, escape_fn)
    if _is_weapon_equip(item) or (_is_armor_equip(item) and item.slot == "hand"):
        code += _emit_gml_offset(item)
    code += _emit_loot_animation(item)
    code += "    }\n\n"
    return code


# ------------------------------------------------------------------
# 类型别名
# ------------------------------------------------------------------

from typing import Callable
_EscapeFn = Callable[[str], str]


# ------------------------------------------------------------------
# 辅助判断
# ------------------------------------------------------------------

def _is_weapon_equip(item: HybridItemV2) -> bool:
    return isinstance(item.equipment, WeaponEquip)

def _is_armor_equip(item: HybridItemV2) -> bool:
    return isinstance(item.equipment, ArmorEquip)

def _compute_damage_type(attributes: dict[str, Any]) -> str:
    """计算主伤害类型（最高值优先，无则默认 Slashing）"""
    damage_attrs = {k: v for k, v in attributes.items() if k in DAMAGE_ATTRIBUTES and v != 0}
    if not damage_attrs:
        return "Slashing_Damage"
    max_val = max(damage_attrs.values())
    ties = [t for t, v in damage_attrs.items() if v == max_val]
    return "Slashing_Damage" if "Slashing_Damage" in ties else ties[0]


# ------------------------------------------------------------------
# 对象创建 + 元数据 + 本地化
# ------------------------------------------------------------------

def _emit_objects(item: HybridItemV2) -> str:
    """生成混合物品的游戏对象创建代码"""
    inv_obj_name = f"o_inv_{item.id}"
    loot_obj_name = f"o_loot_{item.id}"
    inv_sprite = f"s_inv_{item.id}"
    loot_sprite = f"s_loot_{item.id}"
    loot_parent = item.get_loot_parent()

    # 确定材质枚举值（首字母大写）
    if _is_weapon_equip(item) or _is_armor_equip(item):
        material_enum = item.material.capitalize()
    else:
        material_enum = "Organic"

    weight_enum = WEIGHT_TO_ENUM.get(item.weight, "Light")
    tier_enum = TIER_TO_ENUM.get(item.tier, "None")

    # 本地化字典
    languages = item.localization.languages
    if "English" not in languages:
        languages = {"English": {"name": "", "description": ""}, **languages}

    localization_entries: list[str] = []
    localization_desc_entries: list[str] = []
    for lang, data in languages.items():
        name = data.get("name", "").replace('"', '\\"')
        localization_entries.append(f'                    {{ModLanguage.{lang}, "{name}"}}')
        desc = format_description(data.get("description", ""))
        localization_desc_entries.append(f'                    {{ModLanguage.{lang}, "{desc}"}}')

    name_dict = ",\n".join(localization_entries)
    desc_dict = ",\n".join(localization_desc_entries)

    return f"""        // 创建 Inventory 对象
        UndertaleGameObject {inv_obj_name} = Msl.AddObject(
            name: "{inv_obj_name}",
            parentName: "{item.parent_object}",
            spriteName: "{inv_sprite}",
            isVisible: true,
            isPersistent: true,
            isAwake: true
        );

        // 创建 Loot 对象
        UndertaleGameObject {loot_obj_name} = Msl.AddObject(
            name: "{loot_obj_name}",
            parentName: "{loot_parent}",
            spriteName: "{loot_sprite}",
            isVisible: true,
            isPersistent: false,
            isAwake: true
        );

        // 注入物品元数据（使用本地 Helper 以支持自定义 Cat/Subcat/tags）
        InjectItemStats(
            id: "{item.id}",
            Price: {item.base_price},
            tier: ItemTier.{tier_enum},
            Cat: "{item.cat}",
            Subcat: "{" ".join(item.subcats)}",
            Material: ItemMaterial.{material_enum},
            Weight: ItemWeight.{weight_enum},
            tags: "{item.effective_tags}",
            dropsOnce: false
        );


        // 注入本地化
        Msl.InjectTableItemsLocalization(
            new LocalizationItem(
                id: "{item.id}",
                name: new Dictionary<ModLanguage, string>() {{
{name_dict}
                }},
                effect: new Dictionary<ModLanguage, string>() {{
                    {{ModLanguage.English, ""}}
                }},
                description: new Dictionary<ModLanguage, string>() {{
{desc_dict}
                }}
            )
        );

"""


# ------------------------------------------------------------------
# GML 事件组装
# ------------------------------------------------------------------

def _emit_events(item: HybridItemV2, escape: _EscapeFn) -> str:
    """生成混合物品的所有 GML 事件代码，包裹在 C# ApplyEvent 调用中"""
    inv_obj_name = f"o_inv_{item.id}"

    create_code = _emit_create_gml(item)
    alarm_code = _emit_alarm_gml(item)
    step_code = _emit_step_gml(item)
    other10_code = _emit_other10_gml(item)
    other13_code = _emit_other13_gml(item)
    other16_code = _emit_other16_gml(item)
    other24_code = _emit_other24_gml(item)

    code = f"""        // 应用事件代码
        {inv_obj_name}.ApplyEvent(
            new MslEvent(eventType: EventType.Create, subtype: 0, code: @"
{escape(create_code)}
            ")"""

    if alarm_code:
        code += f""",
            new MslEvent(eventType: EventType.Alarm, subtype: 0, code: @"
{escape(alarm_code)}
            ")"""

    if step_code:
        code += f""",
            new MslEvent(eventType: EventType.Step, subtype: 0, code: @"
{escape(step_code)}
            ")"""

    if other10_code:
        code += f""",
            new MslEvent(eventType: EventType.Other, subtype: 10, code: @"
{escape(other10_code)}
            ")"""

    code += f""",
            new MslEvent(eventType: EventType.Other, subtype: 13, code: @"
{escape(other13_code)}
            ")"""

    if other16_code:
        code += f""",
            new MslEvent(eventType: EventType.Other, subtype: 16, code: @"
{escape(other16_code)}
            ")"""

    code += f""",
            new MslEvent(eventType: EventType.Other, subtype: 24, code: @"
{escape(other24_code)}
            ")"""

    code += "\n        );\n\n"
    return code


# ------------------------------------------------------------------
# GML 事件: Create_0
# ------------------------------------------------------------------

def _emit_create_gml(item: HybridItemV2) -> str:
    """生成混合物品的 Create_0 GML 代码"""
    lines: list[str] = []
    lines.append("event_inherited();")
    lines.append("")

    lines.append("// 从 global.consum_stat_data 初始化基础属性")
    lines.append(f'scr_consum_atr("{item.id}");')
    lines.append("")

    # poison_duration
    poisoning_chance = item.consumable_attributes.get("Poisoning_Chance", 0)
    if poisoning_chance > 0 and item.poison_duration > 0:
        lines.append(f"poison_duration = {item.poison_duration};")
        lines.append("")

    lines.append("empty = false;")
    lines.append("is_hybrid_item = true;")
    lines.append("")

    # ===== 品质 =====
    lines.append(f"quality = {item.quality_int};")
    if item.quality == QualitySpec.ARTIFACT:
        lines.append("// 品质: 文物")
        lines.append("shineDelay = room_speed * 2;")
        lines.append('ds_map_set(data, "quality", 7);')
        lines.append('ds_map_set(data, "Colour", make_colour_rgb(229, 193, 85));')
        lines.append("alarm[11] = shineDelay;")
    elif item.quality == QualitySpec.UNIQUE:
        lines.append("// 品质: 独特")
        lines.append('ds_map_set(data, "quality", 6);')
        lines.append('ds_map_set(data, "Colour", make_colour_rgb(130, 72, 188));')
    else:
        lines.append("// 品质: 普通")
        lines.append('ds_map_set(data, "quality", 1);')
    lines.append("")

    # ===== 槽位与装备 =====
    if item.equipable:
        lines.append(f'slot = "{item.slot}";')
        lines.append("can_equip = true;")
        if item.slot == "hand":
            lines.append(f"hands = {item.hands};")
            lines.append(f"character_sprite_hands = {item.hands};")
    else:
        lines.append('slot = "heal";')
        lines.append("can_equip = false;")
    lines.append("")

    # ===== Tier =====
    lines.append(f"Tier = {item.tier};")
    lines.append("")

    # ===== 武器/护甲标记 =====
    if item.is_weapon:
        lines.append("is_weapon = true;")

    if _is_weapon_equip(item):
        lines.append("// 武器数值")
        lines.append(f'type = "{item.weapon_type}";')
        lines.append(f"Balance = {item.balance};")

        best_type = _compute_damage_type(item.attributes)
        lines.append(f'DamageType = "{best_type}";')

        if item.weapon_type == "crossbow":
            lines.append("haveAmmunitionSlot = true;")
            lines.append('ammunitionType = "bolt";')
            lines.append("isCrossbow = true;")
        elif item.weapon_type == "bow":
            lines.append("haveAmmunitionSlot = true;")
            lines.append('ammunitionType = "arrow";')
        lines.append("")

    if _is_armor_equip(item):
        lines.append("// 护甲数值")
        lines.append(f'type = "{item.armor_type}";')
        lines.append(f'armor_type = "{item.armor_class}";')

        if item.slot not in ["hand", "Ring", "Amulet"]:
            lines.append("")
            lines.append("// 碎片材料（拆解用）")
            frag_keys = ["cloth01", "cloth02", "cloth03", "cloth04",
                         "leather01", "leather02", "leather03", "leather04",
                         "metal01", "metal02", "metal03", "metal04", "gold"]
            for frag in frag_keys:
                val = item.fragments.get(frag, 0)
                lines.append(f"fragment_{frag} = {val};")
        lines.append("")

    # ===== 使用次数 =====
    if item.has_charges:
        lines.append("// 使用次数（父类 Alarm_0 会处理持久化）")
        lines.append(f"charge = {item.effective_charge};")
        lines.append(f"max_charge = {item.effective_charge};")
        lines.append(f"draw_charges = {'true' if item.draw_charges else 'false'};")
        lines.append("")

        lines.append("// 消耗品属性 (attributes_data)")
        has_consum_attr = False
        for attr, value in item.consumable_attributes.items():
            if value != 0:
                lines.append(f'ds_map_add(attributes_data, "{attr}", {value});')
                has_consum_attr = True
        if not has_consum_attr:
            lines.append("// 无消耗品属性")
        lines.append("")

    # ===== 耐久 =====
    if item.has_durability:
        lines.append("// 耐久度（父类 Alarm_0 会处理持久化）")
        lines.append(f"duration = {item.duration_max};")
        lines.append("")

    lines.append(f"duration_change = {item.wear_per_use};")
    lines.append(f"delete_after_use = {'true' if item.delete_on_charge_zero else 'false'};")
    lines.append("")

    # ===== 被动效果 =====
    if item.has_passive:
        lines.append("check_inventory_data = true;")
        lines.append("")

    # ===== 音效与价格 =====
    lines.append("// 音效与价格")
    lines.append(f"drop_gui_sound = {item.drop_sound};")
    lines.append(f"pickup_sound = {item.pickup_sound};")
    lines.append(f"base_price = {item.base_price};")
    lines.append("price = base_price;")
    lines.append("")

    # ===== 精灵 =====
    lines.append("// 精灵")
    lines.append(f"s_index = s_inv_{item.id};")
    if item.needs_char_texture():
        lines.append(f"char_sprite = s_char_{item.id};")
        if item.needs_left_texture():
            lines.append(f"charleft_sprite = s_charleft_{item.id};")
        else:
            lines.append("charleft_sprite = -4;")
    else:
        lines.append("char_sprite = -4;")
        lines.append("charleft_sprite = -4;")
    lines.append("char_upper_sprite = -4;")
    lines.append("rest_char_sprite = -4;")
    lines.append("rest_char_upper_sprite = -4;")
    lines.append("")

    # ===== data map =====
    lines.append("// data map 元数据")
    lines.append(f'ds_map_replace(data, "tags", "{item.effective_tags}");')
    lines.append(f'ds_map_replace(data, "rarity", "{item.rarity}");')
    lines.append('ds_map_replace(data, "key", "");')
    lines.append("ds_map_replace(data, \"identified\", true);")

    if item.has_durability:
        lines.append(f'ds_map_replace(data, "MaxDuration", {item.duration_max});')

    if _is_weapon_equip(item):
        best_type = _compute_damage_type(item.attributes)
        lines.append(f'ds_map_replace(data, "DamageType", "{best_type}");')
        lines.append('ds_map_replace(data, "Metatype", "Weapon");')

    if _is_armor_equip(item):
        lines.append('ds_map_replace(data, "Metatype", "Armor");')
        lines.append("ds_map_replace(data, \"Armor_Type\", Weight);")

    if _is_weapon_equip(item) or _is_armor_equip(item):
        lines.append(f'ds_map_replace(data, "Suffix", string({item.quality_int}) + " " + type);')

        lines.append("")
        lines.append("// 生成 type_text")
        lines.append("var _space = scr_actionsLogGetSpace();")
        lines.append('var _type = scr_text_exeption(global.weapon_type, type);')
        lines.append('var _rar = (quality == 7)')
        lines.append('    ? ds_map_find_value_ext(global.consum_type, "treasure", "")')
        lines.append("    : scr_string_get_part(ds_list_find_value(global.rar_text, quality), 1);")
        if _is_armor_equip(item) and item.armor_type not in ("Ring", "Amulet", "Waist"):
            lines.append("var _class = ds_map_find_value(global.armor_class, Weight);")
            lines.append('var _armor = !__is_undefined(_class) ? scr_string_get_part(_class, 1) + _space : "";')
        else:
            lines.append('var _armor = "";')
        lines.append("")
        lines.append("var _lang = global.language;")
        lines.append("if (_lang == 5 || _lang == 6 || _lang == 8)")
        lines.append("    type_text = scr_stringTransformFirst(_type) + _space + _armor + _rar;")
        lines.append("else")
        lines.append("    type_text = scr_stringTransformFirst(_rar) + _space + _armor + _type;")

    return "\n".join(lines)


# ------------------------------------------------------------------
# GML 事件: Alarm_0
# ------------------------------------------------------------------

def _emit_alarm_gml(item: HybridItemV2) -> str:
    """生成混合物品的 Alarm_0 GML 代码"""
    lines = ["event_inherited();"]

    attrs = {k: v for k, v in item.attributes.items() if v != 0}
    if not attrs:
        return "\n".join(lines)

    lines.append("")
    lines.append("if (is_new) {")
    lines.append('    var _main = ds_map_find_value(data, "Main");')

    if _is_weapon_equip(item):
        damage_attrs = {k: v for k, v in attrs.items() if k in DAMAGE_ATTRIBUTES}
        total_dmg = sum(damage_attrs.values())

        for t, v in damage_attrs.items():
            lines.append(f'    ds_list_add(_main, "{t}", {v});')
            lines.append(f'    ds_map_add(data, "{t}", {v});')
        lines.append(f'    ds_map_add(data, "DMG", {total_dmg});')

        for attr, val in attrs.items():
            if attr in DAMAGE_ATTRIBUTES:
                continue
            if attr == "Range":
                lines.append(f'    ds_map_add(data, "Rng", {val});')
                lines.append(f'    ds_map_add(data, "Range", {val});')
            else:
                lines.append(f'    ds_map_add(data, "{attr}", {val});')

    elif _is_armor_equip(item):
        for attr, val in attrs.items():
            if attr == "DEF":
                lines.append(f'    ds_map_add(data, "DEF", {val});')
                lines.append(f'    ds_list_add(_main, "DEF", {val});')
            else:
                lines.append(f'    ds_map_add(data, "{attr}", {val});')

    else:
        for attr, val in attrs.items():
            lines.append(f'    ds_map_add(data, "{attr}", {val});')

    lines.append("}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# GML 事件: Step_0
# ------------------------------------------------------------------

def _emit_step_gml(item: HybridItemV2) -> str:
    """生成混合物品的 Step_0 GML 代码"""
    from data.skills import SKILL_OBJECTS

    sections = ["event_inherited();"]

    # 耐久度控制逻辑
    if item.has_durability:
        sections.append("""\
// 耐久度控制逻辑（仿 o_inv_slot）
var _duration = ds_map_find_value(data, "Duration");
var _maxDuration = ds_map_find_value(data, "MaxDuration");

// 根据耐久度切换贴图
var _max_index = sprite_get_number(s_index) - 1;
var _new_index = 0;
if (_duration <= _maxDuration) _new_index = 0;
if (_duration < (_maxDuration / 2)) _new_index = 1;
if (_duration < (_maxDuration / 4)) _new_index = 2;
if (_new_index > _max_index) _new_index = _max_index;
i_index = _new_index;

// 属性衰减逻辑
var _tier = _duration / _maxDuration;
if (_tier < 0.5) {
    DurDecrease = (_tier > 0.25) ? 0.6 : 0.3;
} else {
    DurDecrease = 1;
}

if (_duration > _maxDuration)
    ds_map_replace(data, "Duration", _maxDuration);""")

    # 使用次数恢复逻辑
    if item.has_charge_recovery and isinstance(item.charges, LimitedCharges):
        sections.append(f"""\
// 使用次数恢复
var _lastTurn = ds_map_find_value(data, "last_recovery_turn");
if (!is_undefined(_lastTurn)) {{
    var _totalSec = scr_timeGetTimestamp() * 60 + ds_map_find_value(global.timeDataMap, "seconds");
    var _turnsPassed = floor(_totalSec / 30) - _lastTurn;

    if (_turnsPassed >= {item.charge_recovery_interval}) {{
        var _recoveries = floor(_turnsPassed / {item.charge_recovery_interval});
        charge = min(max_charge, charge + _recoveries);
        ds_map_replace(data, "charge", charge);

        if (charge >= max_charge)
            ds_map_delete(data, "last_recovery_turn");
        else
            ds_map_replace(data, "last_recovery_turn", _lastTurn + (_recoveries * {item.charge_recovery_interval}));
    }}
}}""")

    # 技能释放状态跟踪
    if isinstance(item.trigger, SkillTrigger):
        skill_info = SKILL_OBJECTS[item.skill_object]
        is_no_target = skill_info.get("target", "") == "No Target"

        if is_no_target:
            detection = """\
    } else {
        // 'No Target' 技能: 延迟计数器等待 buff 创建
        var _delay = ds_map_find_value(data, "_skill_cleanup_delay");
        if (is_undefined(_delay))
            ds_map_set(data, "_skill_cleanup_delay", 5);
        else if (_delay <= 0) {
            _should_cleanup = true;
            _was_successful = _active_skill.last_activated;
            ds_map_delete(data, "_skill_cleanup_delay");
        } else
            ds_map_replace(data, "_skill_cleanup_delay", _delay - 1);"""
        else:
            detection = """\
    } else if (!_active_skill.is_activate) {
        _should_cleanup = true;
        _was_successful = _active_skill.last_activated;"""

        success_logic_parts: list[str] = []

        if isinstance(item.charges, LimitedCharges):
            charge_block = """\
charge--;
            ds_map_replace(data, "charge", charge);"""
            if item.has_charge_recovery:
                charge_block += """

            // 记录恢复起始回合
            var _lastRecTurn = ds_map_find_value(data, "last_recovery_turn");
            if (is_undefined(_lastRecTurn)) {
                var _totalSec = scr_timeGetTimestamp() * 60 + ds_map_find_value(global.timeDataMap, "seconds");
                ds_map_set(data, "last_recovery_turn", floor(_totalSec / 30));
            }"""
            success_logic_parts.append(charge_block)

        if item.has_durability and item.wear_per_use > 0:
            durability_block = f"""\

            // 耐久扣减
            var _maxd = ds_map_find_value(data, "MaxDuration");
            var _cost = (_maxd * {item.wear_per_use}) / 100;
            if (_cost <= 0) _cost = 1;
            var _dur = ds_map_find_value(data, "Duration");
            ds_map_replace(data, "Duration", max(0, _dur - _cost));"""
            success_logic_parts.append(durability_block)

        success_logic = "".join(success_logic_parts) if success_logic_parts else "// 无限模式：不扣减"

        destruction_parts: list[str] = []
        if item.delete_on_charge_zero and isinstance(item.charges, LimitedCharges):
            destruction_parts.append("if (charge <= 0) { event_user(12); exit; }")
        if item.has_durability and item.destroy_on_durability_zero:
            destruction_parts.append('if (ds_map_find_value(data, "Duration") <= 0) { event_user(12); exit; }')
        destruction_logic = "\n        ".join(destruction_parts) if destruction_parts else ""

        sections.append(f"""\
// 技能释放状态跟踪
var _active_skill = ds_map_find_value(data, "_active_skill");
if (!is_undefined(_active_skill)) {{
    var _should_cleanup = false;
    var _was_successful = false;

    if (!instance_exists(_active_skill)) {{
        _should_cleanup = true;
{detection}
    }}

    if (_should_cleanup) {{
        if (_was_successful) {{
            {success_logic}
        }}

        // 清理技能实例
        var _active_ico = ds_map_find_value(data, "_active_ico");
        if (instance_exists(_active_ico)) instance_destroy(_active_ico);
        if (instance_exists(_active_skill)) instance_destroy(_active_skill);
        ds_map_delete(data, "_active_skill");
        ds_map_delete(data, "_active_ico");

        {destruction_logic}
    }}
}}""")

    return "\n\n".join(sections)


# ------------------------------------------------------------------
# GML 事件: Other_10
# ------------------------------------------------------------------

def _emit_other10_gml(item: HybridItemV2) -> str:
    lines: list[str] = ["event_inherited();"]

    if _is_weapon_equip(item):
        lines.append('matatype = "weapon";')
        lines.append(f'slot = "{item.slot}";')
    elif _is_armor_equip(item):
        lines.append('matatype = "armor";')
        lines.append(f'slot = "{item.slot}";')
    elif item.equipable:
        lines.append(f'slot = "{item.slot}";')

    return "\n".join(lines)


# ------------------------------------------------------------------
# GML 事件: Other_13 (Hover)
# ------------------------------------------------------------------

def _emit_other13_gml(item: HybridItemV2) -> str:
    """生成混合物品的 Other_13 (Hover) GML 代码"""
    lines: list[str] = []

    lines.append("switch (guiInteractiveState) {")

    # ===== case 0: hover 显示 =====
    lines.append("    case 0:")
    lines.append("        inmouse = true;")
    lines.append("        event_perform(ev_step, ev_step_normal);")
    lines.append("        ")
    lines.append("        // hover 位置配置（基于 owner 类型）")
    lines.append("        var _hoverPlacementsArray = -4;")
    lines.append("        var _hoverDepthOffset = 0;")
    lines.append("        var _hoverComparisonPlacementsArray = -4;")
    lines.append("        var _hoverComparisonDepthOffset = 0;")
    lines.append("        hoverComparisonID = scr_hoverDestroy(hoverComparisonID, false);")
    lines.append("        hoverComparisonIndex = -1;")
    lines.append("        ")
    lines.append("        with (owner) {")
    lines.append("            switch (object_index) {")
    lines.append("                case o_craftingFoodMenu:")
    lines.append("                case o_craftingConsumsMenu:")
    lines.append("                case o_trade_inventory:")
    lines.append("                case o_stash_inventory_left:")
    lines.append("                case o_container:")
    lines.append("                case o_container_quiver:")
    lines.append("                case o_container_backpack:")
    lines.append("                case o_container_gold:")
    lines.append("                    _hoverPlacementsArray = [2, 1, 5, 0, 0, 1, -5, 0];")
    lines.append("                    _hoverComparisonPlacementsArray = [2, 1, -3, 0, 0, 1, -(other.sprite_width + 8), 0];")
    lines.append("                    _hoverDepthOffset = -1;")
    lines.append("                    break;")
    lines.append("                default:")
    lines.append("                    _hoverPlacementsArray = [0, 1, -5, 0, 2, 1, 5, 0];")
    lines.append("                    _hoverComparisonPlacementsArray = [0, 1, 1, 0, 2, 1, other.sprite_width + 8, 0];")
    lines.append("                    _hoverComparisonDepthOffset = -1;")
    lines.append("                    break;")
    lines.append("            }")
    lines.append("        }")
    lines.append("        ")
    lines.append('        if (ds_map_find_value_ext(data, "identified", true)) {')

    if _is_weapon_equip(item) or _is_armor_equip(item):
        lines.append("            // 武器/护甲类混合物品：使用混合 hover")
        lines.append("            var _comparisonID = scr_hoverWeaponGetComparisonID(id);")
        lines.append("            hoverID = scr_hoverCreate(id, id, o_hoverHybrid, _hoverPlacementsArray, _hoverDepthOffset);")
        lines.append("            scr_hoverTierUpdate(hoverID, Tier);")
        lines.append("            ")
        lines.append("            if (_comparisonID) {")
        lines.append("                // 检查对比目标类型")
        lines.append('                var _isHybrid = variable_instance_exists(_comparisonID, "is_hybrid_item") && _comparisonID.is_hybrid_item;')
        lines.append("                var _isEquipment = object_is_ancestor(_comparisonID.object_index, o_inv_slot);")
        lines.append("                ")
        lines.append("                // 混合物品或普通装备都可以进行对比")
        lines.append("                if (_isHybrid || _isEquipment) {")
        lines.append("                    with (_comparisonID)")
        lines.append("                        event_perform(ev_step, ev_step_normal);")
        lines.append("                    // 对比物品也使用 o_hoverHybrid")
        lines.append("                    hoverComparisonID = scr_hoverCreate(hoverID, _comparisonID, o_hoverHybrid, _hoverComparisonPlacementsArray, _hoverComparisonDepthOffset);")
        lines.append('                    scr_hoverTierUpdate(hoverComparisonID, variable_instance_exists(_comparisonID, "Tier") ? _comparisonID.Tier : 1);')
        lines.append('                    scr_hoverHeaderUpdate(hoverComparisonID, ds_list_find_value(global.weap_param_text, 3));')
        lines.append("                }")
        lines.append("            }")
    else:
        lines.append("            // 消耗品类混合物品：使用混合 hover")
        lines.append("            hoverID = scr_hoverCreate(id, id, o_hoverHybrid, _hoverPlacementsArray, _hoverDepthOffset);")

    lines.append("        } else {")
    lines.append("            // 未鉴定物品")
    lines.append("            hoverID = scr_hoverCreate(id, id, o_hoverUnidentified, _hoverPlacementsArray, _hoverDepthOffset);")
    lines.append("        }")
    lines.append("        break;")
    lines.append("    ")
    lines.append("    default:")
    lines.append("        event_perform_object(o_inv_slot, ev_other, 13);")
    lines.append("        break;")
    lines.append("}")

    return "\n".join(lines)


# ------------------------------------------------------------------
# GML 事件: Other_16
# ------------------------------------------------------------------

def _emit_other16_gml(item: HybridItemV2) -> str:
    if not item.has_durability or not item.equipable:
        return ""
    return "event_perform_object(o_inv_slot, ev_other, 16);"


# ------------------------------------------------------------------
# GML 事件: Other_24 (使用效果)
# ------------------------------------------------------------------

def _emit_other24_gml(item: HybridItemV2) -> str:
    """生成混合物品的 Other_24 (使用效果) GML 代码"""
    if not item.has_charges or isinstance(item.trigger, NoTrigger):
        return "// 空白 Other_24（未启用主动效果）"

    lines: list[str] = []

    lines.append("// 充能检查")
    lines.append("if (charge <= 0)")
    lines.append("    exit;")
    lines.append("")

    if item.has_durability and item.wear_per_use > 0:
        lines.append("var _maxd = ds_map_find_value(data, \"MaxDuration\");")
        lines.append(f"var _cost = (_maxd * {item.wear_per_use}) / 100;")
        lines.append("if (_cost <= 0) _cost = 1;")
        lines.append("var _dur = ds_map_find_value(data, \"Duration\");")
        lines.append("")

    if isinstance(item.trigger, SkillTrigger):
        lines.append("// 技能释放模式")
        if item.skill_object:
            ico_object = f"{item.skill_object}_ico"
            lines.append(f"// 创建对应的技能图标对象作为 owner_skill")
            lines.append(f"var _owner_skill = instance_create_depth(-10000, -10000, 0, {ico_object});")
            lines.append("with (_owner_skill) {")
            lines.append("    owner = o_player;")
            lines.append("    is_open = true;")
            lines.append("    persistent = false;  // 不跨房间持久化")
            lines.append("}")
            lines.append("")
            lines.append(f"var _skill = instance_create_depth(o_player.x, o_player.y, 0, {item.skill_object});")
            lines.append("with (_skill) {")
            lines.append("    owner = o_player;")
            lines.append("    aoe_target = o_player;")
            lines.append("    owner_skill = _owner_skill;")
            lines.append("    persistent = false;  // 不跨房间持久化")
            lines.append("    event_user(7);     // 更新技能参数")
            lines.append("    event_user(0);     // 激活技能（显示范围指示器）")
            lines.append("}")
            lines.append("")
            lines.append("// 保存技能引用供 Step_0 跟踪，充能将在技能成功执行后扣减")
            lines.append('ds_map_set(data, "_active_skill", _skill);')
            lines.append('ds_map_set(data, "_active_ico", _owner_skill);')
        else:
            lines.append("// 警告：未设置技能对象")

    else:  # consumable 模式
        lines.append('scr_actionsLog("useItem", [scr_id_get_name(o_player), log_text, ds_map_find_value(data, "Name")]);')
        lines.append("// 使用消耗品效果（仅使用 attributes_data）")
        lines.append('var _key = ds_map_find_first(attributes_data);')
        lines.append('var _size = ds_map_size(attributes_data);')
        lines.append('repeat (_size) {')
        lines.append('    var _val = ds_map_find_value(attributes_data, _key);')
        lines.append('    if (is_real(_val)) {')
        lines.append('        switch(_key) {')
        lines.append('            // ====== Instant / Independent Effects ======')
        lines.append('            case "MoraleDiet":')
        lines.append('                 var _diet_penalty = scr_psy_diet_penalty_get(object_get_name(object_index));')
        lines.append('                 scr_psy_change("MoraleDiet", _val + _diet_penalty, "consum_morale_diet(penalty:" + string(_diet_penalty) + ")");')
        lines.append('                 scr_psy_pessimism_delay(_val);')
        lines.append('                 break;')
        lines.append('            case "SanitySituational":')
        lines.append('                 scr_psy_change("SanitySituational", _val, "consum_sanity_sit");')
        lines.append('                 break;')
        lines.append('            case "MoraleSituational":')
        lines.append('                 scr_psy_change("MoraleSituational", _val, "consum_morale_sit");')
        lines.append('                 scr_psy_pessimism_delay(_val);')
        lines.append('                 break;')
        lines.append('            case "Hunger":')
        lines.append('                 var _stage = 1;')
        lines.append('                 var _recipeDataMap = ds_map_find_value(global.recipes_food_data, idName);')
        lines.append('                 if (!is_undefined(_recipeDataMap)) {')
        lines.append('                     var _satiety_value = ds_map_find_value(_recipeDataMap, "SATIETY");')
        lines.append('                     if (_satiety_value == "V") _stage = 2;')
        lines.append('                 }')
        lines.append('                 scr_hunger_incr(_val, _stage);')
        lines.append('                 break;')
        lines.append('            case "Thirsty":')
        lines.append('            case "Intoxication":')
        lines.append('            case "Pain":')
        lines.append('                 scr_atr_incr(_key, _val);')
        lines.append('                 break;')
        lines.append('            case "Immunity":')
        lines.append('                 scr_immunity_change(_val);')
        lines.append('                 break;')
        lines.append('            case "max_mp_res":')
        lines.append('                 scr_restore_mp(o_player, (o_player.max_mp * _val) / 100, ds_map_find_value(data, "Name"));')
        lines.append('                 break;')
        lines.append('            case "max_hp_res":')
        lines.append('                 if (_val < 0)')
        lines.append('                     scr_pure_damage(o_player, (-o_player.max_hp * _val) / 100);')
        lines.append('                 else')
        lines.append('                     scr_restore_hp(o_player, (o_player.max_hp * _val) / 100, ds_map_find_value(data, "Name"));')
        lines.append('                 break;')
        lines.append('            case "Condition":')
        lines.append('                 break;')
        lines.append('            case "Fatigue":')
        lines.append('                 scr_fatigue_change(_val, true);')
        lines.append('                 break;')
        lines.append('            case "Poisoning_Chance":')
        lines.append('                 if (scr_chance_value(_val)) scr_effect_create(o_db_poison, poison_duration);')
        lines.append('                 break;')
        lines.append('            case "Nausea_Chance":')
        lines.append('                 if (scr_chance_value(_val)) scr_effect_create(o_db_nause, 1);')
        lines.append('                 break;')
        lines.append('            // ====== Duration Dependent Buffs (Default) ======')
        lines.append('            default:')
        lines.append('                 var dur = ds_map_find_value(attributes_data, "Duration");')
        lines.append('                 if (!is_undefined(dur) && dur > 0)')
        lines.append('                     scr_temp_effect_update(object_index, o_player, _key, _val, dur, 1);')
        lines.append('                 break;')
        lines.append('        }')
        lines.append('    }')
        lines.append('    _key = ds_map_find_next(attributes_data, _key);')
        lines.append('}')
        lines.append("")
        lines.append("with (o_player)")
        lines.append("    scr_guiAnimation(o_b_gamekeeper_brew, 1, 1, 0);")
        lines.append("")

        if not isinstance(item.charges, UnlimitedCharges):
            lines.append("charge--;")
            lines.append("ds_map_replace(data, \"charge\", charge);")

            if item.has_charge_recovery:
                lines.append("")
                lines.append("// 记录恢复起始回合")
                lines.append('var _lastTurn = ds_map_find_value(data, "last_recovery_turn");')
                lines.append("if (is_undefined(_lastTurn)) {")
                lines.append('    var _totalSec = scr_timeGetTimestamp() * 60 + ds_map_find_value(global.timeDataMap, "seconds");')
                lines.append('    ds_map_set(data, "last_recovery_turn", floor(_totalSec / 30));')
                lines.append("}")

        if item.has_durability and item.wear_per_use > 0:
            if item.destroy_on_durability_zero:
                lines.append("if (_dur <= _cost)")
                lines.append("    event_user(12);")
                lines.append("else")
                lines.append("    ds_map_replace(data, \"Duration\", _dur - _cost);")
            else:
                lines.append("ds_map_replace(data, \"Duration\", max(0, _dur - _cost));")

        lines.append("scr_allturn();")
        lines.append("scr_characterStatsConsumUse();")
        lines.append("")
        lines.append("with (o_player)")
        lines.append("    scr_noise_produce(scr_noise_food(), grid_x, grid_y);")
        lines.append("")

        if item.delete_on_charge_zero:
            lines.append("// 充能耗尽后的处理")
            lines.append("if (charge <= 0)")
            lines.append("    event_user(12);")

    return "\n".join(lines)


# ------------------------------------------------------------------
# 偏移注入 + 动画
# ------------------------------------------------------------------

def _emit_gml_offset(item: HybridItemV2) -> str:
    """生成 Hybrid 物品的 GML 偏移注入代码（武器/盾牌）"""
    gml_code_block = ""

    match item.textures.char:
        case WeaponCharTexture() as w:
            clamped = calculate_clamped_origin(w.main.origin)
            if clamped:
                val_x, val_y = clamped
                gml_code_block += emit_anchor_gml_block(val_y, val_x, f"s_char_{item.id}")

            if item.needs_left_texture() and w.left.has_texture():
                clamped_left = calculate_clamped_origin(w.left.origin)
                if clamped_left:
                    val_x, val_y = clamped_left
                    gml_code_block += emit_anchor_gml_block(val_y, val_x, f"s_charleft_{item.id}")
        case _:
            pass

    if not gml_code_block:
        return ""

    gml_code_block = gml_code_block.rstrip()

    code = f'        Msl.LoadAssemblyAsString("gml_GlobalScript_scr_ds_init")\n'
    code += f'            .MatchFrom(@"{_ANCHOR_MATCH_GML}")\n'
    code += f'            .InsertBelow(@"{gml_code_block}")\n'
    code += "            .Save();\n"
    return code


def _emit_loot_animation(item: HybridItemV2) -> str:
    """生成混合物品的战利品贴图动画设置 C# 代码"""
    if not item.textures.loot.is_animated:
        return ""

    sprite_name = f"s_loot_{item.id}"

    match item.textures.loot.speed:
        case AbsoluteFps(fps=fps_value):
            speed_type = "AnimSpeedType.FramesPerSecond"
        case RelativeSpeed(multiplier=fps_value):
            speed_type = "AnimSpeedType.FramesPerGameFrame"

    fps_formatted = f"{fps_value:.3f}"

    return f"""
        // 设置战利品贴图动画播放速度
        UndertaleSprite lootSprite_{item.id} = Msl.GetSprite("{sprite_name}");
        if (lootSprite_{item.id}.CollisionMasks != null && lootSprite_{item.id}.CollisionMasks.Count > 0)
        {{
            lootSprite_{item.id}.CollisionMasks.RemoveAt(0);
        }}
        lootSprite_{item.id}.IsSpecialType = true;
        lootSprite_{item.id}.SVersion = 3;
        lootSprite_{item.id}.GMS2PlaybackSpeed = {fps_formatted}f;
        lootSprite_{item.id}.GMS2PlaybackSpeedType = {speed_type};

"""
