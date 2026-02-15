# -*- coding: utf-8 -*-
"""原版武器/护甲 C# 代码生成

生成 Add{weapon}() / AddArmor{armor}() 方法，包含：
- 物品属性注入（Msl.InjectTableWeapons / InjectTableArmor）
- 本地化注入（Msl.InjectTableWeaponTextsLocalization）
- 偏移注入（bytecode patch → global.customizationAnchors）
- 战利品动画设置（UndertaleSprite 操作）

自包含模块，无 codegen 内部依赖。
"""
from __future__ import annotations

from constants import (
    LANGUAGE_LABELS,
    LANGUAGE_TO_ENUM_MAP,
    PRIMARY_LANGUAGE,
    SLOT_BALANCE,
)
from core.models import Armor, Item, Weapon
from core.specs import (
    AbsoluteFps,
    RelativeSpeed,
    WeaponCharTexture,
)
from codegen.textures import calculate_clamped_origin, format_description


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def emit_item_method(item: Item) -> str:
    """生成单个原版武器/护甲的完整 C# 方法"""
    is_weapon = isinstance(item, Weapon)
    is_shield = isinstance(item, Armor) and item.slot == "shield"
    method_name = f"Add{item.id}" if is_weapon else f"AddArmor{item.id}"

    code = f"    private void {method_name}()\n    {{\n"
    code += _emit_injection(item)
    code += _emit_localization(item)
    if is_weapon or is_shield:
        code += _emit_gml_offset(item)
    code += _emit_loot_animation(item)
    code += "    }\n\n"
    return code


def emit_anchor_gml_block(val_y: int, val_x: int, sprite_name: str) -> str:
    """生成单个锚点的 GML bytecode 块

    被 emit_items 和 emit_hybrids 共同使用（武器/盾牌偏移注入）。
    """
    code = f"pushi.e {val_y}\n"
    code += "conv.i.v\n"
    code += f"pushi.e {val_x}\n"
    code += "conv.i.v\n"
    code += "call.i @@NewGMLArray@@(argc=2)\n"
    code += f"pushi.e {sprite_name}\n"
    code += "conv.i.v\n"
    code += "pushglb.v global.customizationAnchors\n"
    code += "call.i ds_map_add(argc=3)\n"
    code += "popz.v\n"
    return code


# ------------------------------------------------------------------
# 内部实现
# ------------------------------------------------------------------

# bytecode 锚点匹配模式（scr_ds_init 中的稳定片段）
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


def _emit_injection(item: Item) -> str:
    """生成物品属性注入 C# 代码"""
    is_weapon = isinstance(item, Weapon)

    if is_weapon:
        prefix = "Weapons"
        code = "        Msl.InjectTableWeapons(\n"
    else:
        assert isinstance(item, Armor)
        prefix = "Armor"
        code = "        Msl.InjectTableArmor(\n"
        code += f"            hook: Msl.ArmorHook.{item.hook},\n"

    code += f'            name: "{item.name}",\n'
    code += f"            Tier: Msl.{prefix}Tier.{item.tier},\n"
    code += f'            id: "{item.id}",\n'
    code += f"            Slot: Msl.{prefix}Slot.{item.slot},\n"

    if isinstance(item, Armor):
        code += f"            Class: Msl.ArmorClass.{item.armor_class},\n"

    code += f"            rarity: Msl.{prefix}Rarity.{item.rarity},\n"
    code += f"            Mat: Msl.{prefix}Material.{item.mat},\n"
    code += f"            tags: Msl.{prefix}Tags.{item.tags.replace(' ', '')},\n"

    if is_weapon:
        code += f"            Price: {item.price},\n"
        code += "            Markup: 1,\n"
        code += f"            MaxDuration: {item.max_duration},\n"
        code += f"            Rng: {item.rng}"

        balance_value = SLOT_BALANCE.get(item.slot)
        if balance_value is not None:
            code += f",\n            Balance: {balance_value}"
    else:
        code += f"            MaxDuration: {item.max_duration},\n"
        code += f"            Price: {item.price},\n"
        code += "            Markup: 1"

    code += f",\n            fireproof: {'true' if item.fireproof else 'false'}"
    if isinstance(item, Armor):
        code += f",\n            IsOpen: {'true' if item.is_open else 'false'}"
    code += f",\n            NoDrop: {'true' if item.no_drop else 'false'}"

    for attr, value in item.attributes.items():
        if value != 0:
            attr_name = attr
            if is_weapon and attr == "Electromantic_Power":
                attr_name = "Electroantic_Power"
            code += f",\n            {attr_name}: {value}"

    if isinstance(item, Armor):
        for frag_type, frag_value in item.fragments.items():
            if frag_value > 0:
                code += f",\n            {frag_type}: {frag_value}"

    code += "\n        );\n\n"
    return code


def _emit_localization(item: Item) -> str:
    """生成本地化注入 C# 代码"""
    code = "        Msl.InjectTableWeaponTextsLocalization(\n"
    code += "            new LocalizationWeaponText(\n"
    code += f'                id: "{item.name}",\n'
    code += "                name: new Dictionary<ModLanguage, string>() {\n"

    required_langs = {PRIMARY_LANGUAGE}
    if PRIMARY_LANGUAGE != "English":  # pyright: ignore[reportUnnecessaryComparison]
        required_langs.add("English")

    langs_to_generate = set(required_langs)
    for lang in item.localization.languages:
        if lang in LANGUAGE_TO_ENUM_MAP:
            langs_to_generate.add(lang)

    for lang in LANGUAGE_LABELS:
        if lang not in langs_to_generate:
            continue
        lang_enum = LANGUAGE_TO_ENUM_MAP.get(lang)
        if not lang_enum:
            continue
        name = item.localization.get_name(lang)
        code += f'                    {{{lang_enum}, "{name}"}},\n'

    code += "                },\n"
    code += "                description: new Dictionary<ModLanguage, string>() {\n"

    for lang in LANGUAGE_LABELS:
        if lang not in langs_to_generate:
            continue
        lang_enum = LANGUAGE_TO_ENUM_MAP.get(lang)
        if not lang_enum:
            continue
        desc = item.localization.get_description(lang)
        formatted_desc = format_description(desc)
        code += f'                    {{{lang_enum}, "{formatted_desc}"}},\n'

    code += "                }\n"
    code += "            )\n"
    code += "        );\n"
    return code


def _emit_gml_offset(item: Item) -> str:
    """生成 GML 偏移注入代码（武器/盾牌）"""
    char = item.textures.char
    if not isinstance(char, WeaponCharTexture):
        return ""

    gml_code_block = ""

    clamped = calculate_clamped_origin(char.main.origin)
    if clamped:
        val_x, val_y = clamped
        gml_code_block += emit_anchor_gml_block(val_y, val_x, f"s_char_{item.id}")

    if char.left.paths:
        clamped_left = calculate_clamped_origin(char.left.origin)
        if clamped_left:
            val_x, val_y = clamped_left
            gml_code_block += emit_anchor_gml_block(val_y, val_x, f"s_charleft_{item.id}")

    if not gml_code_block:
        return ""

    gml_code_block = gml_code_block.rstrip()

    code = f'        Msl.LoadAssemblyAsString("gml_GlobalScript_scr_ds_init")\n'
    code += f'            .MatchFrom(@"{_ANCHOR_MATCH_GML}")\n'
    code += f'            .InsertBelow(@"{gml_code_block}")\n'
    code += "            .Save();\n"
    return code


def _emit_loot_animation(item: Item) -> str:
    """生成战利品贴图动画设置 C# 代码"""
    loot = item.textures.loot
    if not loot.is_animated:
        return ""

    sprite_name = f"s_loot_{item.id}"

    match loot.speed:
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
