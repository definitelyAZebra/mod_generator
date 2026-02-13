# -*- coding: utf-8 -*-
"""
测试 3（P0）— 序列化/反序列化 (serde)

覆盖：
- 每种 Tagged Union 的每个 variant 的 round-trip
- EquipmentSpec 嵌套 DurabilitySpec
- Origin 特殊序列化（默认=None, 非默认=dict）
- ItemLocalization 自定义 hook
- HybridItemV2 完整 round-trip
- 路径转换 (_relativize_paths / _resolve_paths)
"""
from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path

import pytest

from serde.converter import (
    _get_converter,
    create_converter,
    unstructure,
    structure,
    unstructure_hybrid_item,
    structure_hybrid_item,
    _relativize_paths,
    _resolve_paths,
)
from core.specs import (
    # Quality
    QualitySpec,
    # Equipment
    EquipmentSpec, NotEquipable, WeaponEquip, ArmorEquip, CharmEquip,
    # Durability
    DurabilitySpec, NoDurability, HasDurability,
    # Trigger
    TriggerSpec, NoTrigger, EffectTrigger, SkillTrigger,
    # Charges
    ChargeSpec, NoCharges, LimitedCharges, UnlimitedCharges,
    # ChargeRecovery
    ChargeRecoverySpec, NoRecovery, IntervalRecovery,
    # Spawn
    SpawnSpec, ExcludedFromRandom, RandomSpawn, SpawnRuleType,
    # CharTexture
    CharTextureSpec, NoCharTexture, WeaponCharTexture, MultiPoseCharTexture,
    # LootAnimation
    LootAnimationSpeed, AbsoluteFps, RelativeSpeed,
    # Slots
    AnimatedSlot, StaticSlot, LootSlot, Origin,
    ItemTexturesV2,
)
from core.localization import ItemLocalization
from core.hybrid_item import HybridItemV2


# ============================================================================
# Helper: round-trip 断言
# ============================================================================

_conv = _get_converter()


def assert_round_trip(obj, union_type):
    """unstructure (通过 Union hook) → structure → 比较类型和数据

    注意: 必须用 conv.unstructure(obj, union_type) 才能触发 Tagged Union hook，
    普通 unstructure(obj) 走 cattrs 默认的 concrete-type 分发，不带 "type" tag。
    """
    data = _conv.unstructure(obj, union_type)
    restored = _conv.structure(data, union_type)
    assert type(restored) is type(obj)
    return data, restored


# ============================================================================
# QualitySpec
# ============================================================================


class TestQualitySpecSerde:

    @pytest.mark.parametrize("obj,expected_int", [
        (QualitySpec.COMMON, 1),
        (QualitySpec.UNIQUE, 6),
        (QualitySpec.ARTIFACT, 7),
    ])
    def test_round_trip(self, obj, expected_int):
        data = _conv.unstructure(obj, QualitySpec)
        assert data == expected_int
        restored = _conv.structure(data, QualitySpec)
        assert restored is obj

    def test_invalid_int_defaults_to_common(self):
        restored = _conv.structure(99, QualitySpec)
        assert restored is QualitySpec.COMMON

    def test_none_defaults_to_common(self):
        restored = _conv.structure(None, QualitySpec)
        assert restored is QualitySpec.COMMON


# ============================================================================
# EquipmentSpec (包含嵌套 DurabilitySpec)
# ============================================================================


class TestEquipmentSpecSerde:

    def test_not_equipable(self):
        data, restored = assert_round_trip(NotEquipable(), EquipmentSpec)
        assert data["type"] == "none"
        assert isinstance(restored, NotEquipable)

    def test_charm(self):
        data, restored = assert_round_trip(CharmEquip(), EquipmentSpec)
        assert data["type"] == "charm"
        assert isinstance(restored, CharmEquip)

    def test_weapon_no_durability(self):
        obj = WeaponEquip(weapon_type="dagger", balance=3, durability=NoDurability())
        data, restored = assert_round_trip(obj, EquipmentSpec)
        assert data["type"] == "weapon"
        assert data["weapon_type"] == "dagger"
        assert data["durability"]["type"] == "none"
        assert isinstance(restored, WeaponEquip)
        assert restored.weapon_type == "dagger"
        assert restored.balance == 3
        assert isinstance(restored.durability, NoDurability)

    def test_weapon_with_durability(self):
        obj = WeaponEquip(
            weapon_type="2hsword",
            durability=HasDurability(duration_max=200, wear_per_use=5),
        )
        data, restored = assert_round_trip(obj, EquipmentSpec)
        assert data["durability"]["type"] == "has"
        assert isinstance(restored.durability, HasDurability)
        assert restored.durability.duration_max == 200
        assert restored.durability.wear_per_use == 5

    def test_armor_with_durability(self):
        obj = ArmorEquip(
            armor_type="Chest",
            durability=HasDurability(
                duration_max=150,
                destroy_on_zero=False,
                affects_stats=True,
            ),
        )
        data, restored = assert_round_trip(obj, EquipmentSpec)
        assert data["type"] == "armor"
        assert isinstance(restored, ArmorEquip)
        assert restored.armor_type == "Chest"
        assert restored.durability.destroy_on_zero is False
        assert restored.durability.affects_stats is True

    def test_none_data_defaults_to_not_equipable(self):
        restored = _conv.structure(None, EquipmentSpec)
        assert isinstance(restored, NotEquipable)

    def test_class_vars_not_serialized(self):
        """WeaponEquip 的 ClassVar (TWO_HAND_WEAPONS 等) 不应出现在序列化结果中"""
        data = _conv.unstructure(WeaponEquip(), EquipmentSpec)
        assert "TWO_HAND_WEAPONS" not in data
        assert "LEFT_HAND_WEAPONS" not in data


# ============================================================================
# DurabilitySpec
# ============================================================================


class TestDurabilitySpecSerde:

    def test_no_durability(self):
        data, restored = assert_round_trip(NoDurability(), DurabilitySpec)
        assert data["type"] == "none"

    def test_has_durability(self):
        obj = HasDurability(duration_max=300, wear_per_use=10, destroy_on_zero=False)
        data, restored = assert_round_trip(obj, DurabilitySpec)
        assert data["type"] == "has"
        assert restored.duration_max == 300


# ============================================================================
# TriggerSpec
# ============================================================================


class TestTriggerSpecSerde:

    def test_no_trigger(self):
        data, _ = assert_round_trip(NoTrigger(), TriggerSpec)
        assert data["type"] == "none"

    def test_effect_trigger(self):
        obj = EffectTrigger(
            consumable_attributes={"HP": 10, "MP": -5},
            poison_duration=3,
        )
        _, restored = assert_round_trip(obj, TriggerSpec)
        assert restored.consumable_attributes == {"HP": 10, "MP": -5}
        assert restored.poison_duration == 3

    def test_skill_trigger(self):
        obj = SkillTrigger(skill_object="o_skill_fire")
        _, restored = assert_round_trip(obj, TriggerSpec)
        assert restored.skill_object == "o_skill_fire"


# ============================================================================
# ChargeSpec
# ============================================================================


class TestChargeSpecSerde:

    @pytest.mark.parametrize("obj,tag", [
        (NoCharges(), "none"),
        (LimitedCharges(max_charges=5, draw_charges=True), "limited"),
        (UnlimitedCharges(draw_charges=False), "unlimited"),
    ])
    def test_round_trip(self, obj, tag):
        data, _ = assert_round_trip(obj, ChargeSpec)
        assert data["type"] == tag


# ============================================================================
# ChargeRecoverySpec
# ============================================================================


class TestChargeRecoverySpecSerde:

    def test_no_recovery(self):
        assert_round_trip(NoRecovery(), ChargeRecoverySpec)

    def test_interval_recovery(self):
        obj = IntervalRecovery(interval=20)
        _, restored = assert_round_trip(obj, ChargeRecoverySpec)
        assert restored.interval == 20


# ============================================================================
# SpawnSpec
# ============================================================================


class TestSpawnSpecSerde:

    def test_excluded(self):
        data, _ = assert_round_trip(ExcludedFromRandom(), SpawnSpec)
        assert data["type"] == "excluded"

    def test_random_spawn(self):
        obj = RandomSpawn(
            container_spawn=SpawnRuleType.EQUIPMENT,
            shop_spawn=SpawnRuleType.ITEM,
            quality_tag="unique",
            dungeon_tag="crypt",
            country_tag="aldor",
            extra_tags=["test", "debug"],
        )
        data, restored = assert_round_trip(obj, SpawnSpec)
        assert data["type"] == "random"
        assert data["container_spawn"] == "equipment"
        assert restored.container_spawn == SpawnRuleType.EQUIPMENT
        assert restored.extra_tags == ["test", "debug"]


# ============================================================================
# LootAnimationSpeed
# ============================================================================


class TestLootAnimationSpeedSerde:

    def test_absolute(self):
        obj = AbsoluteFps(fps=15.0)
        _, restored = assert_round_trip(obj, LootAnimationSpeed)
        assert restored.fps == 15.0

    def test_relative(self):
        obj = RelativeSpeed(multiplier=0.5)
        _, restored = assert_round_trip(obj, LootAnimationSpeed)
        assert restored.multiplier == 0.5


# ============================================================================
# CharTextureSpec
# ============================================================================


class TestCharTextureSpecSerde:

    def test_no_char_texture(self):
        data, _ = assert_round_trip(NoCharTexture(), CharTextureSpec)
        assert data["type"] == "none"

    def test_weapon_char_texture(self):
        obj = WeaponCharTexture(
            main=AnimatedSlot(paths=["a.png", "b.png"], origin=Origin(24, 36)),
            left=AnimatedSlot(paths=["l.png"]),
        )
        _, restored = assert_round_trip(obj, CharTextureSpec)
        assert isinstance(restored, WeaponCharTexture)
        assert restored.main.paths == ["a.png", "b.png"]
        assert restored.main.origin.x == 24
        assert restored.left.paths == ["l.png"]

    def test_multi_pose_char_texture(self):
        obj = MultiPoseCharTexture(
            standing0=StaticSlot(path="s0.png", origin=Origin()),
            standing1=StaticSlot(path="s1.png"),
            rest=StaticSlot(path="r.png"),
        )
        _, restored = assert_round_trip(obj, CharTextureSpec)
        assert isinstance(restored, MultiPoseCharTexture)
        assert restored.standing0.path == "s0.png"
        assert restored.standing1.path == "s1.png"


# ============================================================================
# Origin 特殊序列化
# ============================================================================


class TestOriginSerde:

    def test_default_origin_serializes_to_none(self):
        data = unstructure(Origin())
        assert data is None

    def test_non_default_origin_serializes_to_dict(self):
        data = unstructure(Origin(24, 36))
        assert data == {"x": 24, "y": 36}

    def test_none_restores_to_default(self):
        restored = structure(None, Origin)
        assert restored.is_default

    def test_empty_dict_restores_to_default(self):
        """空 dict 触发 falsy → 默认 Origin"""
        restored = structure({}, Origin)
        assert restored.is_default

    def test_dict_restores_correctly(self):
        restored = structure({"x": 20, "y": 30}, Origin)
        assert restored.x == 20
        assert restored.y == 30


# ============================================================================
# ItemLocalization
# ============================================================================


class TestItemLocalizationSerde:

    def test_round_trip(self):
        loc = ItemLocalization(languages={"en": {"name": "Sword", "desc": "A sword"}})
        data = unstructure(loc)
        assert data == {"en": {"name": "Sword", "desc": "A sword"}}
        restored = structure(data, ItemLocalization)
        assert restored.languages == loc.languages

    def test_none_restores_empty(self):
        restored = structure(None, ItemLocalization)
        assert restored.languages == {}


# ============================================================================
# HybridItemV2 完整 round-trip
# ============================================================================


class TestHybridItemV2Serde:

    def test_minimal_round_trip(self):
        item = HybridItemV2(id="test_sword")
        data = unstructure_hybrid_item(item)
        restored = structure_hybrid_item(data)
        assert restored.id == "test_sword"
        assert restored.quality is item.quality
        assert type(restored.equipment) is type(item.equipment)

    def test_full_weapon_round_trip(self):
        item = HybridItemV2(
            id="magic_blade",
            quality=QualitySpec.UNIQUE,
            equipment=WeaponEquip(
                weapon_type="sword",
                balance=3,
                durability=HasDurability(duration_max=200),
            ),
            trigger=EffectTrigger(
                consumable_attributes={"Fire_Damage": 5},
                poison_duration=0,
            ),
            charges=LimitedCharges(max_charges=10, draw_charges=True),
            charge_recovery=IntervalRecovery(interval=15),
            spawn=RandomSpawn(
                container_spawn=SpawnRuleType.EQUIPMENT,
                quality_tag="unique",
            ),
            weight="Heavy",
            tier=4,
            material="metal",
            base_price=500,
            attributes={"Damage": 20, "Block_Power": 5},
        )
        data = unstructure_hybrid_item(item)
        restored = structure_hybrid_item(data)

        assert restored.id == "magic_blade"
        assert restored.quality is QualitySpec.UNIQUE
        assert isinstance(restored.equipment, WeaponEquip)
        assert restored.equipment.weapon_type == "sword"
        assert restored.equipment.durability.duration_max == 200
        assert isinstance(restored.trigger, EffectTrigger)
        assert restored.trigger.consumable_attributes == {"Fire_Damage": 5}
        assert isinstance(restored.charges, LimitedCharges)
        assert restored.charges.max_charges == 10
        assert isinstance(restored.charge_recovery, IntervalRecovery)
        assert isinstance(restored.spawn, RandomSpawn)
        assert restored.weight == "Heavy"
        assert restored.attributes == {"Damage": 20, "Block_Power": 5}


# ============================================================================
# 路径转换
# ============================================================================


class TestPathConversion:

    def test_relativize_and_resolve_inventory(self, tmp_path: Path):
        proj = str(tmp_path / "proj")
        inv = str(tmp_path / "proj" / "assets" / "inv.png")
        loot = str(tmp_path / "proj" / "assets" / "loot.png")

        data = {
            "textures": {
                "inventory": [inv],
                "loot": {"paths": [loot], "speed": {}},
                "char": {"type": "none"},
            }
        }
        _relativize_paths(data, proj)
        expected_inv = str(Path("assets") / "inv.png")
        expected_loot = str(Path("assets") / "loot.png")
        assert data["textures"]["inventory"] == [expected_inv]
        assert data["textures"]["loot"]["paths"] == [expected_loot]

        _resolve_paths(data, proj)
        assert Path(data["textures"]["inventory"][0]) == Path(proj) / "assets" / "inv.png"

    def test_relativize_weapon_char_paths(self, tmp_path: Path):
        proj = str(tmp_path / "proj")
        data = {
            "textures": {
                "inventory": [],
                "loot": {"paths": []},
                "char": {
                    "type": "weapon",
                    "main": {"paths": [str(Path(proj) / "a.png")]},
                    "left": {"paths": [str(Path(proj) / "b.png")]},
                },
            }
        }
        _relativize_paths(data, proj)
        assert data["textures"]["char"]["main"]["paths"] == ["a.png"]
        assert data["textures"]["char"]["left"]["paths"] == ["b.png"]

    def test_relativize_multi_pose_char_paths(self, tmp_path: Path):
        proj = str(tmp_path / "proj")
        data = {
            "textures": {
                "inventory": [],
                "loot": {"paths": []},
                "char": {
                    "type": "multi_pose",
                    "standing0": {"path": str(Path(proj) / "s0.png")},
                    "standing1": {"path": str(Path(proj) / "s1.png")},
                    "rest": {"path": ""},
                    "standing0_female": {"path": ""},
                    "standing1_female": {"path": ""},
                    "rest_female": {"path": ""},
                },
            }
        }
        _relativize_paths(data, proj)
        assert data["textures"]["char"]["standing0"]["path"] == "s0.png"
        assert data["textures"]["char"]["standing1"]["path"] == "s1.png"
        # 空路径不变
        assert data["textures"]["char"]["rest"]["path"] == ""

    def test_empty_paths_untouched(self, tmp_path: Path):
        data = {
            "textures": {
                "inventory": [],
                "loot": {"paths": []},
                "char": {"type": "none"},
            }
        }
        original = deepcopy(data)
        _relativize_paths(data, str(tmp_path))
        assert data == original

    def test_hybrid_item_path_round_trip(self, tmp_path: Path):
        """HybridItemV2 序列化/反序列化时路径正确转换"""
        project_dir = str(tmp_path)
        inv_path = str(tmp_path / "assets" / "inv.png")

        item = HybridItemV2(
            id="test",
            textures=ItemTexturesV2(inventory=[inv_path]),
        )

        data = unstructure_hybrid_item(item, project_dir)
        # 路径应被相对化
        assert not os.path.isabs(data["textures"]["inventory"][0])

        restored = structure_hybrid_item(data, project_dir)
        # 路径应被还原为绝对路径
        assert os.path.isabs(restored.textures.inventory[0])
