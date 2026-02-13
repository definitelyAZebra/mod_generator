# -*- coding: utf-8 -*-
"""
测试 — codegen emit 模块（业务代码）

覆盖:
- emit_helpers: C# 工具函数输出结构
- emit_items:   原版武器/护甲 C# 方法生成
- emit_hybrids: 混合物品 C# 方法 + GML 事件
- emit_infra:   hover 系统 / 注册系统 / 属性本地化
- generator:    整体生成流程（集成测试，使用真实 fixture）
"""
from __future__ import annotations

import re

import pytest

from codegen import emit_helpers, emit_items, emit_hybrids, emit_infra
from codegen.generator import CodeGenerator
from core.hybrid_item import HybridItemV2
from core.localization import ItemLocalization
from core.models import Armor, ModProject, Weapon
from core.specs import (
    AbsoluteFps,
    AnimatedSlot,
    ArmorEquip,
    ArtifactQuality,
    CharmEquip,
    CommonQuality,
    EffectTrigger,
    ExcludedFromRandom,
    HasDurability,
    IntervalRecovery,
    ItemTexturesV2,
    LimitedCharges,
    LootSlot,
    NoDurability,
    NoCharTexture,
    NoCharges,
    NoRecovery,
    NoTrigger,
    NotEquipable,
    Origin,
    RandomSpawn,
    RelativeSpeed,
    SpawnRuleType,
    SkillTrigger,
    UniqueQuality,
    UnlimitedCharges,
    WeaponCharTexture,
    WeaponEquip,
)


# ============================================================================
# Helpers — 构造 fixture 数据
# ============================================================================

def _loc(en_name: str = "Test Item", en_desc: str = "A test item") -> ItemLocalization:
    loc = ItemLocalization()
    loc.set_name("English", en_name)
    loc.set_description("English", en_desc)
    return loc


def _loc_bilingual(
    en_name: str = "Test",
    en_desc: str = "Desc",
    zh_name: str = "测试",
    zh_desc: str = "描述",
) -> ItemLocalization:
    loc = _loc(en_name, en_desc)
    loc.set_name("Chinese", zh_name)
    loc.set_description("Chinese", zh_desc)
    return loc


def _weapon(
    name: str = "TestSword",
    slot: str = "sword",
    tier: str = "Tier3",
    rarity: str = "Common",
    mat: str = "metal",
    tags: str = "aldor",
    price: int = 200,
    max_duration: int = 150,
    rng: int = 1,
    attributes: dict | None = None,
    localization: ItemLocalization | None = None,
    textures: ItemTexturesV2 | None = None,
    fireproof: bool = False,
    no_drop: bool = False,
) -> Weapon:
    return Weapon(
        name=name,
        slot=slot,
        tier=tier,
        rarity=rarity,
        mat=mat,
        tags=tags,
        price=price,
        max_duration=max_duration,
        rng=rng,
        attributes=attributes or {},
        localization=localization or _loc(name, f"A {name}"),
        textures=textures or ItemTexturesV2(),
        fireproof=fireproof,
        no_drop=no_drop,
    )


def _armor(
    name: str = "TestHelm",
    slot: str = "Head",
    tier: str = "Tier2",
    rarity: str = "Common",
    mat: str = "leather",
    tags: str = "aldor",
    price: int = 80,
    max_duration: int = 100,
    armor_class: str = "Light",
    fragments: dict | None = None,
    localization: ItemLocalization | None = None,
    textures: ItemTexturesV2 | None = None,
    is_open: bool = False,
) -> Armor:
    return Armor(
        name=name,
        slot=slot,
        tier=tier,
        rarity=rarity,
        mat=mat,
        tags=tags,
        price=price,
        max_duration=max_duration,
        armor_class=armor_class,
        fragments=fragments or {},
        localization=localization or _loc(name, f"A {name}"),
        textures=textures or ItemTexturesV2(),
        is_open=is_open,
    )


def _hybrid_consumable(
    id: str = "test_potion",
    trigger: EffectTrigger | None = None,
    charges: LimitedCharges | None = None,
    consumable_attrs: dict | None = None,
    attributes: dict | None = None,
    quality: CommonQuality | UniqueQuality | ArtifactQuality | None = None,
    delete_on_charge_zero: bool = True,
    tier: int = 1,
    base_price: int = 50,
    localization: ItemLocalization | None = None,
) -> HybridItemV2:
    """消耗品类混合物品快捷构造"""
    tr = trigger or EffectTrigger(
        consumable_attributes=consumable_attrs or {"Hunger": 10, "Thirsty": 5},
    )
    return HybridItemV2(
        id=id,
        parent_object="o_inv_consum",
        quality=quality or CommonQuality(),
        equipment=NotEquipable(),
        trigger=tr,
        charges=charges or LimitedCharges(max_charges=3, draw_charges=True),
        charge_recovery=NoRecovery(),
        spawn=ExcludedFromRandom(),
        cat="food",
        subcats=["fruit"],
        attributes=attributes or {},
        weight="Light",
        tier=tier,
        material="organic",
        base_price=base_price,
        delete_on_charge_zero=delete_on_charge_zero,
        localization=localization or _loc(id, f"Desc of {id}"),
        textures=ItemTexturesV2(
            inventory=["inv.png"],
            loot=LootSlot(paths=["loot.png"]),
        ),
    )


def _hybrid_weapon(
    id: str = "test_blade",
    weapon_type: str = "sword",
    balance: int = 2,
    durability: HasDurability | NoDurability | None = None,
    trigger: SkillTrigger | EffectTrigger | NoTrigger | None = None,
    charges: LimitedCharges | UnlimitedCharges | NoCharges | None = None,
    attributes: dict | None = None,
    consumable_attrs: dict | None = None,
    quality: CommonQuality | UniqueQuality | ArtifactQuality | None = None,
    tier: int = 3,
    localization: ItemLocalization | None = None,
    textures: ItemTexturesV2 | None = None,
    spawn: ExcludedFromRandom | RandomSpawn | None = None,
) -> HybridItemV2:
    """武器类混合物品快捷构造"""
    dur = durability or HasDurability(duration_max=200, wear_per_use=5)
    tr = trigger or NoTrigger()
    ch = charges or NoCharges()
    attrs = attributes or {"Slashing_Damage": 20, "CRT": 5}
    tex = textures or ItemTexturesV2(
        inventory=["inv.png"],
        loot=LootSlot(paths=["loot.png"]),
        char=WeaponCharTexture(
            main=AnimatedSlot(paths=["char.png"]),
        ),
    )
    return HybridItemV2(
        id=id,
        parent_object="o_inv_slot",
        quality=quality or CommonQuality(),
        equipment=WeaponEquip(
            weapon_type=weapon_type,
            balance=balance,
            durability=dur,
        ),
        trigger=tr,
        charges=ch,
        charge_recovery=NoRecovery(),
        spawn=spawn or ExcludedFromRandom(),
        cat="",
        subcats=[],
        attributes=attrs,
        weight="Medium",
        tier=tier,
        material="metal",
        base_price=300,
        localization=localization or _loc(id, f"Desc of {id}"),
        textures=tex,
    )


def _hybrid_armor_amulet(
    id: str = "test_amulet",
    trigger: SkillTrigger | EffectTrigger | NoTrigger | None = None,
    charges: LimitedCharges | UnlimitedCharges | NoCharges | None = None,
    attributes: dict | None = None,
    quality: CommonQuality | UniqueQuality | ArtifactQuality | None = None,
    spawn: ExcludedFromRandom | RandomSpawn | None = None,
    tier: int = 2,
) -> HybridItemV2:
    """护甲(项链)类混合物品快捷构造"""
    return HybridItemV2(
        id=id,
        parent_object="o_inv_slot",
        quality=quality or UniqueQuality(),
        equipment=ArmorEquip(armor_type="Amulet"),
        trigger=trigger or NoTrigger(),
        charges=charges or NoCharges(),
        charge_recovery=NoRecovery(),
        spawn=spawn or ExcludedFromRandom(),
        cat="",
        subcats=[],
        attributes=attributes or {"Dodge_Chance": 3, "Magic_Power": 5},
        weight="VeryLight",
        tier=tier,
        material="gem",
        base_price=500,
        localization=_loc(id, f"A magical amulet"),
        textures=ItemTexturesV2(
            inventory=["inv.png"],
            loot=LootSlot(paths=["loot.png"]),
        ),
    )


def _escape(text: str) -> str:
    """模拟 CodeGenerator._escape_multiline_string"""
    return text.replace('"', '""')


# ============================================================================
# emit_helpers
# ============================================================================

class TestEmitHelpers:

    def test_returns_nonempty_string(self):
        result = emit_helpers.emit_csharp_utility_functions()
        assert isinstance(result, str)
        assert len(result) > 100

    def test_contains_function_exists(self):
        result = emit_helpers.emit_csharp_utility_functions()
        assert "bool FunctionExists(string functionName)" in result

    def test_contains_init_script_exists(self):
        result = emit_helpers.emit_csharp_utility_functions()
        assert "bool InitScriptExists(string scriptId)" in result

    def test_contains_add_global_function(self):
        result = emit_helpers.emit_csharp_utility_functions()
        assert "void AddGlobalFunction(string functionName, string gmlCode)" in result

    def test_contains_add_init_script(self):
        result = emit_helpers.emit_csharp_utility_functions()
        assert "void AddInitScript(string scriptId, string gmlCode)" in result

    def test_contains_mark_class(self):
        result = emit_helpers.emit_csharp_utility_functions()
        assert "public static class Mark" in result
        assert "Mark.Has" in result or "public static bool Has" in result
        assert "Mark.Set" in result or "public static void Set" in result

    def test_contains_localization_attribute(self):
        result = emit_helpers.emit_csharp_utility_functions()
        assert "class LocalizationAttribute" in result

    def test_contains_attribute_localization_helper(self):
        result = emit_helpers.emit_csharp_utility_functions()
        assert "class AttributeLocalizationHelper" in result
        assert "InjectTableAttributesLocalization" in result

    def test_closes_partial_class(self):
        """partial class 的右花括号必须在 Mark 类之前"""
        result = emit_helpers.emit_csharp_utility_functions()
        close_brace_idx = result.index("}")
        mark_idx = result.index("public static class Mark")
        assert close_brace_idx < mark_idx


# ============================================================================
# emit_items — emit_item_method
# ============================================================================

class TestEmitItemMethodWeapon:

    def test_method_name_contains_weapon_id(self):
        w = _weapon(name="FireSword")
        code = emit_items.emit_item_method(w)
        assert w.id == "firesword"
        assert "private void Addfiresword()" in code

    def test_injection_uses_correct_weapon_api(self):
        w = _weapon(name="IceBlade", slot="sword")
        code = emit_items.emit_item_method(w)
        assert "Msl.InjectTableWeapons(" in code
        assert 'id: "iceblade"' in code
        assert 'Slot: Msl.WeaponsSlot.sword' in code

    def test_injection_includes_attributes(self):
        w = _weapon(attributes={"Slashing_Damage": 25, "CRT": 5})
        code = emit_items.emit_item_method(w)
        assert "Slashing_Damage: 25" in code
        assert "CRT: 5" in code

    def test_injection_skips_zero_attributes(self):
        w = _weapon(attributes={"CRT": 0, "Dodge_Chance": 3})
        code = emit_items.emit_item_method(w)
        assert "CRT: 0" not in code
        assert "Dodge_Chance: 3" in code

    def test_electromantic_power_rename(self):
        """武器中 Electromantic_Power → Electroantic_Power (MSL typo)"""
        w = _weapon(attributes={"Electromantic_Power": 10})
        code = emit_items.emit_item_method(w)
        assert "Electroantic_Power: 10" in code
        assert "Electromantic_Power" not in code

    def test_fireproof_and_nodrop(self):
        w = _weapon(fireproof=True, no_drop=True)
        code = emit_items.emit_item_method(w)
        assert "fireproof: true" in code
        assert "NoDrop: true" in code

    def test_localization_section(self):
        loc = _loc_bilingual("Fire Sword", "Blazing", "火剑", "炽热")
        w = _weapon(name="FireSword", localization=loc)
        code = emit_items.emit_item_method(w)
        assert "Msl.InjectTableWeaponTextsLocalization(" in code
        assert 'ModLanguage.English, "Fire Sword"' in code
        assert 'ModLanguage.Chinese, "火剑"' in code

    def test_balance_from_slot(self):
        from constants import SLOT_BALANCE
        for slot, expected_balance in SLOT_BALANCE.items():
            w = _weapon(slot=slot)
            code = emit_items.emit_item_method(w)
            assert f"Balance: {expected_balance}" in code


class TestEmitItemMethodArmor:

    def test_method_name_prefixed_with_armor(self):
        a = _armor(name="IronHelm")
        code = emit_items.emit_item_method(a)
        assert a.id == "ironhelm"
        assert "private void AddArmorironhelm()" in code

    def test_injection_uses_correct_armor_api(self):
        a = _armor(slot="Head", armor_class="Heavy")
        code = emit_items.emit_item_method(a)
        assert "Msl.InjectTableArmor(" in code
        assert "Msl.ArmorSlot.Head" in code
        assert "Msl.ArmorClass.Heavy" in code

    def test_armor_hook(self):
        a = _armor(slot="Chest")
        code = emit_items.emit_item_method(a)
        assert "Msl.ArmorHook." in code

    def test_is_open(self):
        a = _armor(is_open=True)
        code = emit_items.emit_item_method(a)
        assert "IsOpen: true" in code

    def test_fragments(self):
        a = _armor(fragments={"cloth01": 3, "metal02": 1})
        code = emit_items.emit_item_method(a)
        assert "cloth01: 3" in code
        assert "metal02: 1" in code


class TestEmitAnchorGmlBlock:

    def test_block_structure(self):
        block = emit_items.emit_anchor_gml_block(34, 22, "s_char_test")
        assert "pushi.e 34" in block
        assert "pushi.e 22" in block
        assert "pushi.e s_char_test" in block
        assert "ds_map_add(argc=3)" in block
        assert "global.customizationAnchors" in block

    def test_left_sprite_name(self):
        block = emit_items.emit_anchor_gml_block(40, 25, "s_charleft_myblade")
        assert "pushi.e s_charleft_myblade" in block


class TestEmitItemLootAnimation:

    def test_no_animation_when_single_frame(self):
        w = _weapon(textures=ItemTexturesV2(loot=LootSlot(paths=["single.png"])))
        code = emit_items.emit_item_method(w)
        assert "UndertaleSprite" not in code

    def test_animation_with_absolute_fps(self):
        loot = LootSlot(
            paths=["f1.png", "f2.png", "f3.png"],
            speed=AbsoluteFps(fps=15.0),
        )
        w = _weapon(name="AnimBlade", textures=ItemTexturesV2(loot=loot))
        code = emit_items.emit_item_method(w)
        assert "AnimSpeedType.FramesPerSecond" in code
        assert "15.000f" in code
        assert "s_loot_animblade" in code

    def test_animation_with_relative_speed(self):
        loot = LootSlot(
            paths=["f1.png", "f2.png"],
            speed=RelativeSpeed(multiplier=0.25),
        )
        w = _weapon(name="RelBlade", textures=ItemTexturesV2(loot=loot))
        code = emit_items.emit_item_method(w)
        assert "AnimSpeedType.FramesPerGameFrame" in code
        assert "0.250f" in code


class TestEmitItemGmlOffset:

    def test_no_offset_with_default_origin(self):
        """默认 origin 不产生偏移注入代码"""
        char = WeaponCharTexture(
            main=AnimatedSlot(paths=["char.png"], origin=Origin()),
        )
        w = _weapon(textures=ItemTexturesV2(char=char))
        code = emit_items.emit_item_method(w)
        assert "LoadAssemblyAsString" not in code

    def test_offset_with_custom_origin(self):
        char = WeaponCharTexture(
            main=AnimatedSlot(paths=["char.png"], origin=Origin(x=30, y=40)),
        )
        w = _weapon(textures=ItemTexturesV2(char=char))
        code = emit_items.emit_item_method(w)
        assert "LoadAssemblyAsString" in code
        assert "scr_ds_init" in code

    def test_left_hand_offset(self):
        char = WeaponCharTexture(
            main=AnimatedSlot(paths=["char.png"]),
            left=AnimatedSlot(paths=["left.png"], origin=Origin(x=30, y=40)),
        )
        w = _weapon(textures=ItemTexturesV2(char=char))
        code = emit_items.emit_item_method(w)
        assert "s_charleft_testsword" in code


# ============================================================================
# emit_hybrids
# ============================================================================

class TestEmitHybridConsumable:
    """消耗品类混合物品"""

    def test_method_name(self):
        h = _hybrid_consumable(id="cherry_pie")
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "private void AddHybridcherry_pie()" in code

    def test_creates_inv_and_loot_objects(self):
        h = _hybrid_consumable(id="cherry_pie")
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert '"o_inv_cherry_pie"' in code
        assert '"o_loot_cherry_pie"' in code
        assert '"s_inv_cherry_pie"' in code
        assert '"s_loot_cherry_pie"' in code

    def test_parent_object(self):
        h = _hybrid_consumable(id="cherry_pie")
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert '"o_inv_consum"' in code

    def test_inject_item_stats(self):
        h = _hybrid_consumable(id="myitem", tier=3, base_price=150)
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "InjectItemStats(" in code
        assert 'id: "myitem"' in code
        assert "Price: 150" in code
        assert "ItemTier.Tier3" in code

    def test_localization_injection(self):
        h = _hybrid_consumable(
            id="testfood",
            localization=_loc_bilingual("Test Food", "Yummy", "测试食物", "美味"),
        )
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "Msl.InjectTableItemsLocalization(" in code
        assert 'ModLanguage.English, "Test Food"' in code
        assert 'ModLanguage.Chinese, "测试食物"' in code

    def test_create_event_contains_scr_consum_atr(self):
        h = _hybrid_consumable(id="mypotion")
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert 'scr_consum_atr(""mypotion"")' in code  # escaped for verbatim string

    def test_create_event_sets_is_hybrid_item(self):
        h = _hybrid_consumable()
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "is_hybrid_item = true" in code

    def test_create_event_sets_charges(self):
        h = _hybrid_consumable(charges=LimitedCharges(max_charges=5, draw_charges=True))
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "charge = 5" in code
        assert "max_charge = 5" in code
        assert "draw_charges = true" in code

    def test_create_event_sets_consumable_attributes(self):
        h = _hybrid_consumable(
            consumable_attrs={"Hunger": 20, "Duration": 10},
        )
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert 'ds_map_add(attributes_data, ""Hunger"", 20)' in code
        assert 'ds_map_add(attributes_data, ""Duration"", 10)' in code

    def test_other24_has_use_effect(self):
        h = _hybrid_consumable()
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "scr_actionsLog" in code
        assert "scr_allturn()" in code

    def test_other24_skipped_when_no_trigger(self):
        h = HybridItemV2(
            id="passive_item",
            trigger=NoTrigger(),
            charges=NoCharges(),
            localization=_loc("passive", "passive"),
            textures=ItemTexturesV2(inventory=["i.png"], loot=LootSlot(paths=["l.png"])),
        )
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        # Other_24 存在但为空白注释
        assert "未启用主动效果" in code

    def test_delete_on_charge_zero(self):
        h = _hybrid_consumable(delete_on_charge_zero=True)
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "delete_after_use = true" in code
        assert "event_user(12)" in code  # 充能耗尽销毁

    def test_quality_unique(self):
        h = _hybrid_consumable(quality=UniqueQuality())
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "quality = 6" in code
        assert 'make_colour_rgb(130, 72, 188)' in code

    def test_quality_artifact(self):
        h = _hybrid_consumable(quality=ArtifactQuality())
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "quality = 7" in code
        assert "shineDelay" in code


class TestEmitHybridWeapon:
    """武器类混合物品"""

    def test_creates_weapon_equip_vars(self):
        h = _hybrid_weapon(weapon_type="2hsword", balance=4)
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "is_weapon = true" in code
        assert 'type = ""2hsword""' in code
        assert "Balance = 4" in code

    def test_damage_type_computed_from_attributes(self):
        h = _hybrid_weapon(attributes={"Piercing_Damage": 30, "Slashing_Damage": 10})
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert 'DamageType = ""Piercing_Damage""' in code

    def test_damage_type_defaults_to_slashing(self):
        h = _hybrid_weapon(attributes={"CRT": 10})  # no damage attrs
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert 'DamageType = ""Slashing_Damage""' in code

    def test_bow_creates_ammo_slot(self):
        h = _hybrid_weapon(weapon_type="bow")
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "haveAmmunitionSlot = true" in code
        assert 'ammunitionType = ""arrow""' in code

    def test_crossbow_creates_bolt_slot(self):
        h = _hybrid_weapon(weapon_type="crossbow")
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "isCrossbow = true" in code
        assert 'ammunitionType = ""bolt""' in code

    def test_alarm_event_injects_damage_attrs(self):
        h = _hybrid_weapon(attributes={"Slashing_Damage": 20, "Piercing_Damage": 10, "CRT": 5})
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert 'ds_map_add(data, ""Slashing_Damage"", 20)' in code
        assert 'ds_map_add(data, ""Piercing_Damage"", 10)' in code
        assert 'ds_map_add(data, ""DMG"", 30)' in code  # total damage

    def test_durability_creates_step_logic(self):
        h = _hybrid_weapon(
            durability=HasDurability(duration_max=200, wear_per_use=5),
        )
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "duration = 200" in code  # Create
        assert "DurDecrease" in code  # Step

    def test_no_durability_skips_step_logic(self):
        h = _hybrid_weapon(durability=NoDurability())
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "DurDecrease" not in code

    def test_other10_sets_metatype_weapon(self):
        h = _hybrid_weapon()
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert 'matatype = ""weapon""' in code

    def test_other13_uses_hover_hybrid(self):
        """武器型混合物品使用 o_hoverHybrid"""
        h = _hybrid_weapon()
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "o_hoverHybrid" in code
        assert "scr_hoverWeaponGetComparisonID" in code

    def test_other16_emitted_when_equipable_with_durability(self):
        h = _hybrid_weapon(durability=HasDurability())
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "ev_other, 16" in code

    def test_gml_offset_with_custom_origin(self):
        char = WeaponCharTexture(
            main=AnimatedSlot(paths=["char.png"], origin=Origin(x=30, y=40)),
        )
        h = _hybrid_weapon(
            textures=ItemTexturesV2(
                inventory=["inv.png"],
                loot=LootSlot(paths=["loot.png"]),
                char=char,
            ),
        )
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "LoadAssemblyAsString" in code
        assert "s_char_test_blade" in code


class TestEmitHybridArmorAmulet:
    """护甲(项链)类混合物品"""

    def test_armor_type_set(self):
        h = _hybrid_armor_amulet()
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert 'type = ""Amulet""' in code
        assert 'matatype = ""armor""' in code

    def test_alarm_event_injects_armor_attrs(self):
        h = _hybrid_armor_amulet(attributes={"DEF": 5, "Dodge_Chance": 3})
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert 'ds_map_add(data, ""DEF"", 5)' in code
        assert 'ds_map_add(data, ""Dodge_Chance"", 3)' in code


class TestEmitHybridSkillTrigger:
    """技能触发模式"""

    def test_other24_creates_skill_instance(self):
        h = _hybrid_weapon(
            trigger=SkillTrigger(skill_object="o_skill_adrenaline_rush"),
            charges=LimitedCharges(max_charges=3),
        )
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "o_skill_adrenaline_rush" in code
        assert "o_skill_adrenaline_rush_ico" in code
        assert "event_user(7)" in code  # 更新参数
        assert "event_user(0)" in code  # 激活技能

    def test_step_tracks_skill_state(self):
        h = _hybrid_weapon(
            trigger=SkillTrigger(skill_object="o_skill_adrenaline_rush"),
            charges=LimitedCharges(max_charges=3),
        )
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "_active_skill" in code
        assert "_should_cleanup" in code

    def test_skill_with_charge_recovery(self):
        h = HybridItemV2(
            id="recovery_charm",
            parent_object="o_inv_consum",
            equipment=CharmEquip(),
            trigger=SkillTrigger(skill_object="o_skill_adrenaline_rush"),
            charges=LimitedCharges(max_charges=2),
            charge_recovery=IntervalRecovery(interval=50),
            localization=_loc("recovery_charm"),
            textures=ItemTexturesV2(
                inventory=["inv.png"], loot=LootSlot(paths=["l.png"]),
            ),
        )
        code = emit_hybrids.emit_hybrid_item_method(h, _escape)
        assert "last_recovery_turn" in code  # Step 中的恢复逻辑
        assert "50" in code  # interval value


class TestEmitHybridComputeDamageType:
    """_compute_damage_type 内部函数"""

    def test_single_damage_type(self):
        result = emit_hybrids._compute_damage_type({"Piercing_Damage": 20})
        assert result == "Piercing_Damage"

    def test_multiple_damage_highest_wins(self):
        result = emit_hybrids._compute_damage_type(
            {"Slashing_Damage": 10, "Piercing_Damage": 30}
        )
        assert result == "Piercing_Damage"

    def test_tie_prefers_slashing(self):
        result = emit_hybrids._compute_damage_type(
            {"Slashing_Damage": 20, "Piercing_Damage": 20}
        )
        assert result == "Slashing_Damage"

    def test_no_damage_defaults_to_slashing(self):
        result = emit_hybrids._compute_damage_type({"CRT": 10, "Speed": 5})
        assert result == "Slashing_Damage"

    def test_empty_attrs_defaults_to_slashing(self):
        result = emit_hybrids._compute_damage_type({})
        assert result == "Slashing_Damage"


# ============================================================================
# emit_infra
# ============================================================================

class TestEmitInfraGmlScripts:

    def test_ensure_extended_order_lists_returns_gml_function(self):
        gml = emit_infra.emit_ensure_extended_order_lists_gml()
        assert gml.startswith("function scr_hoversEnsureExtendedOrderLists()")
        assert "global.attribute_order_extra" in gml
        assert "global.attribute_order_all_extended" in gml
        assert "global.attribute_order_all_without_damage_extended" in gml

    def test_draw_hybrid_consum_attrs_returns_gml_function(self):
        gml = emit_infra.emit_draw_hybrid_consum_attrs_gml()
        assert gml.startswith("function scr_hoversDrawHybridConsumAttributes()")
        assert "scr_hoversGetAttributeValue" in gml
        assert "scr_hoversGetAttributeName" in gml
        # 检查即时属性列表已嵌入
        assert "_instantAttrs" in gml


class TestEmitInfraHoverScriptsInjection:

    def test_hover_scripts_injection_method(self):
        code = emit_infra.emit_hover_scripts_injection()
        assert "void EnsureHoverScriptsExist()" in code
        assert "FunctionExists" in code
        assert "scr_hoversEnsureExtendedOrderLists" in code
        assert "scr_hoversDrawHybridConsumAttributes" in code


class TestEmitInfraHoverHybridObject:

    def test_hover_hybrid_object_creates_object(self):
        code = emit_infra.emit_hover_hybrid_object(_escape)
        assert "void EnsureHoverHybridExists()" in code
        assert '"o_hoverHybrid"' in code
        assert '"o_hoverRenderContent"' in code

    def test_hover_hybrid_has_create_event(self):
        code = emit_infra.emit_hover_hybrid_object(_escape)
        assert "EventType.Create" in code
        assert "minWidth" in code  # Create 事件设置 minWidth

    def test_hover_hybrid_has_other20_event(self):
        """Other_20 = 数据初始化"""
        code = emit_infra.emit_hover_hybrid_object(_escape)
        assert "subtype: 20" in code
        assert "scr_hoversEnsureExtendedOrderLists()" in code

    def test_hover_hybrid_has_other21_event(self):
        """Other_21 = 绘制"""
        code = emit_infra.emit_hover_hybrid_object(_escape)
        assert "subtype: 21" in code
        assert "scr_hoversDrawDamageAttributes" in code
        assert "scr_hoversDrawWeaponAttributes" in code
        assert "scr_hoversDrawHybridConsumAttributes" in code

    def test_hover_hybrid_has_cleanup_event(self):
        code = emit_infra.emit_hover_hybrid_object(_escape)
        assert "EventType.CleanUp" in code
        assert "__dsDebuggerMapDestroy" in code


class TestEmitInfraInjectItemStats:

    def test_inject_item_stats_method(self):
        code = emit_infra.emit_inject_item_stats()
        assert "void InjectItemStats(" in code
        assert "table_items_stats" in code

    def test_inject_item_stats_has_enums(self):
        code = emit_infra.emit_inject_item_stats()
        assert "enum ItemTier" in code
        assert "Tier1" in code and "Tier5" in code
        assert "enum ItemWeight" in code
        assert "VeryLight" in code
        assert "enum ItemMaterial" in code
        assert "Organic" in code and "Metal" in code


class TestEmitInfraMissingAttributeLocalizations:

    def test_returns_method(self):
        code = emit_infra.emit_missing_attribute_localizations()
        assert "void InjectMissingAttributeLocalizations()" in code
        assert "Mark.Has" in code
        assert "Mark.Set" in code

    def test_contains_known_missing_attrs(self):
        code = emit_infra.emit_missing_attribute_localizations()
        # 抽查几个已知缺失的属性
        assert "Arcanistic_Distance" in code
        assert "BlockPowerBonus" in code
        assert "Weapon_Damage_Main" in code
        assert "HP_turn" in code

    def test_bilingual_entries(self):
        code = emit_infra.emit_missing_attribute_localizations()
        assert "ModLanguage.English" in code
        assert "ModLanguage.Chinese" in code


class TestEmitInfraRegistryHelper:

    def test_registry_helper_structure(self):
        code = emit_infra.emit_hybrid_registry_helper()
        assert "void EnsureHybridItemRegistry()" in code

    def test_registry_creates_global_registry(self):
        code = emit_infra.emit_hybrid_registry_helper()
        assert "hybrid_item_registry" in code
        assert "hybrid_item_by_slot" in code

    def test_registry_has_candidate_finders(self):
        code = emit_infra.emit_hybrid_registry_helper()
        assert "scr_find_item_candidates" in code
        assert "scr_find_hybrid_candidates" in code
        assert "scr_find_unified_item" in code

    def test_registry_has_spawn_helpers(self):
        code = emit_infra.emit_hybrid_registry_helper()
        assert "scr_shop_spawn_unified_item" in code
        assert "scr_loot_spawn_hybrid" in code
        assert "scr_loot_spawn_wrapper" in code

    def test_registry_has_bytecode_patches(self):
        code = emit_infra.emit_hybrid_registry_helper()
        assert "patch_scr_loot_from_tables" in code
        assert "patch_o_NPC_Other_24" in code

    def test_registry_uses_mark_for_idempotency(self):
        code = emit_infra.emit_hybrid_registry_helper()
        assert "Mark.Has" in code
        assert "Mark.Set" in code


class TestEmitInfraHybridItemRegistration:

    def test_empty_hybrids_returns_empty(self):
        proj = ModProject(code_name="TestMod")
        result = emit_infra.emit_hybrid_item_registration(proj, [])
        assert result == ""

    def test_registration_method_name(self):
        proj = ModProject(code_name="MyWeaponMod")
        hybrids = [
            _hybrid_weapon(
                id="fire_sword",
                spawn=RandomSpawn(
                    container_spawn=SpawnRuleType.EQUIPMENT,
                    shop_spawn=SpawnRuleType.EQUIPMENT,
                ),
            ),
        ]
        code = emit_infra.emit_hybrid_item_registration(proj, hybrids)
        assert "void RegisterHybridItem_MyWeaponMod()" in code

    def test_registration_contains_item_data(self):
        proj = ModProject(code_name="TestMod")
        hybrids = [
            _hybrid_weapon(
                id="magic_blade",
                weapon_type="sword",
                tier=4,
                spawn=RandomSpawn(
                    container_spawn=SpawnRuleType.EQUIPMENT,
                    shop_spawn=SpawnRuleType.EQUIPMENT,
                ),
            ),
        ]
        code = emit_infra.emit_hybrid_item_registration(proj, hybrids)
        assert "magic_blade" in code
        assert "sword" in code  # slot from weapon_type

    def test_multiple_hybrids_registered(self):
        proj = ModProject(code_name="TestMod")
        h1 = _hybrid_weapon(
            id="blade_a",
            spawn=RandomSpawn(
                container_spawn=SpawnRuleType.EQUIPMENT,
                shop_spawn=SpawnRuleType.EQUIPMENT,
            ),
        )
        h2 = _hybrid_armor_amulet(
            id="amulet_b",
            spawn=RandomSpawn(
                container_spawn=SpawnRuleType.ITEM,
                shop_spawn=SpawnRuleType.ITEM,
            ),
        )
        code = emit_infra.emit_hybrid_item_registration(proj, [h1, h2])
        assert "blade_a" in code
        assert "amulet_b" in code


# ============================================================================
# CodeGenerator 集成测试 — 使用手工数据
# ============================================================================

class TestGeneratorUnit:
    """CodeGenerator 单元行为"""

    def test_empty_project_generates_valid_csharp(self):
        proj = ModProject(code_name="EmptyMod", author="Tester")
        gen = CodeGenerator(proj)
        files = gen.generate()
        assert "EmptyMod.cs" in files
        assert "EmptyMod.Helpers.cs" in files

    def test_main_file_has_namespace(self):
        proj = ModProject(code_name="MyMod")
        files = CodeGenerator(proj).generate()
        assert "namespace MyMod;" in files["MyMod.cs"]

    def test_main_file_has_mod_metadata(self):
        proj = ModProject(
            code_name="CoolMod",
            author="Alice",
            name="Cool Mod",
            version="2.0.0",
            description='A "cool" mod',
        )
        files = CodeGenerator(proj).generate()
        main = files["CoolMod.cs"]
        assert 'Author => "Alice"' in main
        assert 'Name => "Cool Mod"' in main
        assert 'Version => "2.0.0"' in main
        assert 'Description => @"A ""cool"" mod"' in main

    def test_weapons_generate_method_calls_in_patchmod(self):
        proj = ModProject(code_name="WepMod", weapons=[_weapon(name="SwordA"), _weapon(name="SwordB")])
        files = CodeGenerator(proj).generate()
        main = files["WepMod.cs"]
        assert "Addsworda();" in main
        assert "Addswordb();" in main

    def test_hybrids_generate_method_calls_in_patchmod(self):
        h = _hybrid_consumable(id="test_food")
        proj = ModProject(code_name="FoodMod", hybrid_items=[h])
        files = CodeGenerator(proj).generate()
        main = files["FoodMod.cs"]
        assert "AddHybridtest_food();" in main

    def test_helpers_file_has_infra_when_hybrids_exist(self):
        h = _hybrid_consumable(id="item_a")
        proj = ModProject(code_name="HybMod", hybrid_items=[h])
        files = CodeGenerator(proj).generate()
        helpers = files["HybMod.Helpers.cs"]
        assert "EnsureHoverScriptsExist" in helpers
        assert "EnsureHoverHybridExists" in helpers
        assert "InjectMissingAttributeLocalizations" in helpers
        assert "FunctionExists" in helpers  # from emit_helpers

    def test_helpers_file_minimal_without_hybrids(self):
        proj = ModProject(code_name="VanillaMod", weapons=[_weapon()])
        files = CodeGenerator(proj).generate()
        helpers = files["VanillaMod.Helpers.cs"]
        assert "无混合物品" in helpers
        assert "EnsureHoverScriptsExist" not in helpers

    def test_registry_generated_when_registration_needed(self):
        h = _hybrid_weapon(
            id="reg_blade",
            spawn=RandomSpawn(
                container_spawn=SpawnRuleType.EQUIPMENT,
                shop_spawn=SpawnRuleType.EQUIPMENT,
            ),
        )
        proj = ModProject(code_name="RegMod", hybrid_items=[h])
        files = CodeGenerator(proj).generate()
        main = files["RegMod.cs"]
        helpers = files["RegMod.Helpers.cs"]
        assert "EnsureHybridItemRegistry();" in main
        assert "RegisterHybridItem_RegMod();" in main
        assert "EnsureHybridItemRegistry" in helpers

    def test_registry_skipped_when_excluded_from_random(self):
        h = _hybrid_consumable(id="excluded_item")  # ExcludedFromRandom by default
        proj = ModProject(code_name="NoRegMod", hybrid_items=[h])
        files = CodeGenerator(proj).generate()
        main = files["NoRegMod.cs"]
        assert "EnsureHybridItemRegistry" not in main

    def test_gml_script_public_api(self):
        proj = ModProject(code_name="TestMod")
        gen = CodeGenerator(proj)
        gml1 = gen.generate_ensure_extended_order_lists_gml()
        gml2 = gen.generate_draw_hybrid_consum_attrs_gml()
        assert "scr_hoversEnsureExtendedOrderLists" in gml1
        assert "scr_hoversDrawHybridConsumAttributes" in gml2

    def test_registered_hybrids_property(self):
        h_reg = _hybrid_weapon(
            id="reg",
            spawn=RandomSpawn(
                container_spawn=SpawnRuleType.EQUIPMENT,
                shop_spawn=SpawnRuleType.EQUIPMENT,
            ),
        )
        h_excl = _hybrid_consumable(id="excl")  # ExcludedFromRandom
        proj = ModProject(code_name="T", hybrid_items=[h_reg, h_excl])
        gen = CodeGenerator(proj)
        assert len(gen.registered_hybrids) == 1
        assert gen.registered_hybrids[0].id == "reg"


# ============================================================================
# CodeGenerator 集成测试 — 使用真实 fixture 项目
# ============================================================================

class TestGeneratorWithFixtures:
    """使用真实 fixture 项目进行端到端验证"""

    def test_generate_produces_two_files(self, loaded_project: ModProject):
        gen = CodeGenerator(loaded_project)
        files = gen.generate()
        assert len(files) == 2
        code_name = loaded_project.code_name.strip() or "ModNamespace"
        assert f"{code_name}.cs" in files
        assert f"{code_name}.Helpers.cs" in files

    def test_main_file_is_valid_csharp_structure(self, loaded_project: ModProject):
        gen = CodeGenerator(loaded_project)
        files = gen.generate()
        code_name = loaded_project.code_name.strip() or "ModNamespace"
        main = files[f"{code_name}.cs"]

        # 基本 C# 结构检查
        assert "using ModShardLauncher;" in main
        assert f"namespace {code_name};" in main
        assert "public override void PatchMod()" in main

    def test_every_weapon_has_method(self, loaded_project: ModProject):
        gen = CodeGenerator(loaded_project)
        files = gen.generate()
        code_name = loaded_project.code_name.strip() or "ModNamespace"
        main = files[f"{code_name}.cs"]

        for w in loaded_project.weapons:
            method_id = w.id  # already lowercase
            assert f"Add{method_id}();" in main, f"缺少武器方法调用: Add{method_id}"
            assert f"private void Add{method_id}()" in main, f"缺少武器方法定义: Add{method_id}"

    def test_every_armor_has_method(self, loaded_project: ModProject):
        gen = CodeGenerator(loaded_project)
        files = gen.generate()
        code_name = loaded_project.code_name.strip() or "ModNamespace"
        main = files[f"{code_name}.cs"]

        for a in loaded_project.armors:
            method_id = a.id  # already lowercase
            assert f"AddArmor{method_id}();" in main, f"缺少护甲方法调用: AddArmor{method_id}"
            assert f"private void AddArmor{method_id}()" in main, f"缺少护甲方法定义: AddArmor{method_id}"

    def test_every_hybrid_has_method(self, loaded_project: ModProject):
        gen = CodeGenerator(loaded_project)
        files = gen.generate()
        code_name = loaded_project.code_name.strip() or "ModNamespace"
        main = files[f"{code_name}.cs"]

        for h in loaded_project.hybrid_items:
            assert f"AddHybrid{h.id}();" in main, f"缺少混合物品方法调用: AddHybrid{h.id}"
            assert f"private void AddHybrid{h.id}()" in main, f"缺少混合物品方法定义: AddHybrid{h.id}"

    def test_helpers_file_consistency(self, loaded_project: ModProject):
        gen = CodeGenerator(loaded_project)
        files = gen.generate()
        code_name = loaded_project.code_name.strip() or "ModNamespace"
        helpers = files[f"{code_name}.Helpers.cs"]

        if loaded_project.hybrid_items:
            # 有混合物品时，Helpers 必须包含基础设施
            assert "FunctionExists" in helpers
            assert "Mark" in helpers
        else:
            assert "无混合物品" in helpers

    def test_hybrid_project_has_hover_infrastructure(self, loaded_project: ModProject):
        if not loaded_project.hybrid_items:
            pytest.skip("无混合物品")

        gen = CodeGenerator(loaded_project)
        files = gen.generate()
        code_name = loaded_project.code_name.strip() or "ModNamespace"
        main = files[f"{code_name}.cs"]

        assert "EnsureHoverScriptsExist();" in main
        assert "EnsureHoverHybridExists();" in main
        assert "InjectMissingAttributeLocalizations();" in main

    def test_registered_hybrids_have_registry(self, loaded_project: ModProject):
        gen = CodeGenerator(loaded_project)
        files = gen.generate()
        code_name = loaded_project.code_name.strip() or "ModNamespace"
        main = files[f"{code_name}.cs"]
        helpers = files[f"{code_name}.Helpers.cs"]

        if gen.registered_hybrids:
            assert "EnsureHybridItemRegistry();" in main
            assert f"RegisterHybridItem_{code_name}" in main
            assert "EnsureHybridItemRegistry" in helpers
        elif loaded_project.hybrid_items:
            # 有混合物品但无需注册 → 不应有注册代码
            assert "EnsureHybridItemRegistry" not in main

    def test_gml_scripts_valid(self, loaded_project: ModProject):
        if not loaded_project.hybrid_items:
            pytest.skip("无混合物品")

        gen = CodeGenerator(loaded_project)
        gml1 = gen.generate_ensure_extended_order_lists_gml()
        gml2 = gen.generate_draw_hybrid_consum_attrs_gml()

        # GML 脚本必须以 function 关键字开头
        assert gml1.strip().startswith("function ")
        assert gml2.strip().startswith("function ")
        # 函数体必须有花括号
        assert gml1.count("{") >= 1
        assert gml2.count("{") >= 1

    def test_no_unescaped_quotes_in_verbatim_strings(self, loaded_project: ModProject):
        """C# verbatim string (@"...") 中不应有未转义的单引号"""
        if not loaded_project.hybrid_items:
            pytest.skip("无混合物品")

        gen = CodeGenerator(loaded_project)
        files = gen.generate()
        code_name = loaded_project.code_name.strip() or "ModNamespace"
        main = files[f"{code_name}.cs"]

        # 提取 @"..." 块并检查内部无单独的 "
        # verbatim string 中 " 必须为 ""
        verbatim_pattern = re.compile(r'@"((?:[^"]|"")*)"')
        for match in verbatim_pattern.finditer(main):
            content = match.group(1)
            # 替换掉合法的 "" 后不应还有 "
            cleaned = content.replace('""', '')
            assert '"' not in cleaned, (
                f"检测到未转义的引号在 verbatim string 中:\n"
                f"...{match.group(0)[:100]}..."
            )

    def test_weapon_injection_api_consistency(self, loaded_project: ModProject):
        """武器必须用 InjectTableWeapons, 护甲必须用 InjectTableArmor"""
        gen = CodeGenerator(loaded_project)
        files = gen.generate()
        code_name = loaded_project.code_name.strip() or "ModNamespace"
        main = files[f"{code_name}.cs"]

        weapon_inject_count = main.count("Msl.InjectTableWeapons(")
        armor_inject_count = main.count("Msl.InjectTableArmor(")

        assert weapon_inject_count == len(loaded_project.weapons)
        assert armor_inject_count == len(loaded_project.armors)

    def test_hybrid_object_creation_consistency(self, loaded_project: ModProject):
        """每个 hybrid 应创建恰好 2 个游戏对象 (inv + loot)"""
        gen = CodeGenerator(loaded_project)
        files = gen.generate()
        code_name = loaded_project.code_name.strip() or "ModNamespace"
        main = files[f"{code_name}.cs"]

        for h in loaded_project.hybrid_items:
            assert f'"o_inv_{h.id}"' in main, f"缺少 o_inv_{h.id}"
            assert f'"o_loot_{h.id}"' in main, f"缺少 o_loot_{h.id}"

    def test_localization_present_for_all_items(self, loaded_project: ModProject):
        """所有物品都应有本地化注入"""
        gen = CodeGenerator(loaded_project)
        files = gen.generate()
        code_name = loaded_project.code_name.strip() or "ModNamespace"
        main = files[f"{code_name}.cs"]

        vanilla_loc_count = main.count("InjectTableWeaponTextsLocalization")
        hybrid_loc_count = main.count("InjectTableItemsLocalization")

        expected_vanilla = len(loaded_project.weapons) + len(loaded_project.armors)
        expected_hybrid = len(loaded_project.hybrid_items)

        assert vanilla_loc_count == expected_vanilla, (
            f"本地化注入数量不匹配: 期望 {expected_vanilla} 个 "
            f"InjectTableWeaponTextsLocalization, 实际 {vanilla_loc_count}"
        )
        assert hybrid_loc_count == expected_hybrid, (
            f"混合物品本地化不匹配: 期望 {expected_hybrid} 个 "
            f"InjectTableItemsLocalization, 实际 {hybrid_loc_count}"
        )
