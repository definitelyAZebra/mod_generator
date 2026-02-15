# -*- coding: utf-8 -*-
"""
测试 2（P0）— Schema 迁移

覆盖：
- migrate() 入口的版本逻辑（正常/未来版本/非法版本）
- V1→V2 HybridItem 平铺字段 → Tagged Union
- V1→V2 Weapon/Armor 贴图格式迁移
- offset→origin 转换
- weight 字段格式修正
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from migrations import (
    CURRENT_SCHEMA_VERSION,
    FutureVersionError,
    MigrationError,
    migrate,
    _offset_to_origin,
    _pass_v1_to_v2,
    _pass_v2_to_v3,
)
from constants import CHAR_MODEL_ORIGIN


# ============================================================================
# migrate() 入口逻辑
# ============================================================================


class TestMigrateEntry:
    """migrate() 版本检测与分发"""

    def test_v1_triggers_migration(self):
        data = {"name": "test"}  # 无 schema_version → 默认 1
        result, migrated = migrate(data)
        assert migrated is True
        assert result["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_explicit_v1_triggers_migration(self):
        data = {"schema_version": 1, "name": "test"}
        _, migrated = migrate(data)
        assert migrated is True

    def test_current_version_no_migration(self):
        data = {"schema_version": CURRENT_SCHEMA_VERSION, "name": "test"}
        _, migrated = migrate(data)
        assert migrated is False

    def test_future_version_raises(self):
        data = {"schema_version": CURRENT_SCHEMA_VERSION + 1}
        with pytest.raises(FutureVersionError):
            migrate(data)

    def test_version_zero_raises(self):
        data = {"schema_version": 0}
        with pytest.raises(MigrationError):
            migrate(data)

    def test_negative_version_raises(self):
        data = {"schema_version": -1}
        with pytest.raises(MigrationError):
            migrate(data)

    def test_non_int_version_raises(self):
        data = {"schema_version": "2"}
        with pytest.raises(MigrationError):
            migrate(data)

    def test_float_version_raises(self):
        data = {"schema_version": 1.5}
        with pytest.raises(MigrationError):
            migrate(data)

    def test_idempotent_on_already_v3(self):
        """已经是 v3 的数据不应被修改"""
        data = {
            "schema_version": 3,
            "hybrid_items": [
                {
                    "id": "test",
                    "equipment": {"type": "none"},
                    "quality": 1,
                }
            ],
        }
        original = deepcopy(data)
        result, migrated = migrate(data)
        assert migrated is False
        assert result["hybrid_items"] == original["hybrid_items"]


# ============================================================================
# _offset_to_origin
# ============================================================================


class TestOffsetToOrigin:
    """offset → origin 转换"""

    def test_zero_offset_returns_empty_dict(self):
        """(0, 0) 偏移返回空字典（使用默认 origin）"""
        assert _offset_to_origin(0, 0) == {}

    def test_positive_offset(self):
        result = _offset_to_origin(5, -3)
        expected = {
            "origin": {
                "x": CHAR_MODEL_ORIGIN[0] + 5,
                "y": CHAR_MODEL_ORIGIN[1] - 3,
            }
        }
        assert result == expected

    def test_negative_offset(self):
        result = _offset_to_origin(-2, -4)
        expected = {
            "origin": {
                "x": CHAR_MODEL_ORIGIN[0] - 2,
                "y": CHAR_MODEL_ORIGIN[1] - 4,
            }
        }
        assert result == expected


# ============================================================================
# V1→V2 HybridItem 迁移
# ============================================================================


def _make_v1_hybrid(**overrides: Any) -> dict[str, Any]:
    """构造 V1 格式的最小 HybridItem"""
    base: dict[str, Any] = {
        "id": "test_item",
        "equipment_mode": "none",
        "trigger_mode": "none",
        "charge_mode": "limited",
        "quality": 1,
        "charge": 1,
        "draw_charges": False,
        "has_charge_recovery": False,
        "exclude_from_random": True,
        "textures": {},
    }
    base.update(overrides)
    return base


class TestV1ToV2Hybrid:
    """HybridItem V1→V2 平铺字段 → Tagged Union"""

    # ---- Equipment ----

    def test_equipment_none(self):
        data = {"hybrid_items": [_make_v1_hybrid(equipment_mode="none")]}
        _pass_v1_to_v2(data)
        eq = data["hybrid_items"][0]["equipment"]
        assert eq["type"] == "none"

    def test_equipment_weapon(self):
        data = {"hybrid_items": [_make_v1_hybrid(
            equipment_mode="weapon",
            weapon_type="2hsword",
            balance=3,
        )]}
        _pass_v1_to_v2(data)
        eq = data["hybrid_items"][0]["equipment"]
        assert eq["type"] == "weapon"
        assert eq["weapon_type"] == "2hsword"
        assert eq["balance"] == 3
        # weapon_type / balance 应从顶层移除
        assert "weapon_type" not in data["hybrid_items"][0]

    def test_equipment_armor(self):
        data = {"hybrid_items": [_make_v1_hybrid(
            equipment_mode="armor",
            armor_type="Head",
        )]}
        _pass_v1_to_v2(data)
        eq = data["hybrid_items"][0]["equipment"]
        assert eq["type"] == "armor"
        assert eq["armor_type"] == "Head"

    def test_equipment_charm(self):
        data = {"hybrid_items": [_make_v1_hybrid(equipment_mode="charm")]}
        _pass_v1_to_v2(data)
        assert data["hybrid_items"][0]["equipment"]["type"] == "charm"

    # ---- Durability ----

    def test_weapon_with_durability(self):
        data = {"hybrid_items": [_make_v1_hybrid(
            equipment_mode="weapon",
            quality=6,
            duration_max=200,
            wear_per_use=5,
            destroy_on_durability_zero=False,
            durability_affects_stats=True,
        )]}
        _pass_v1_to_v2(data)
        dur = data["hybrid_items"][0]["equipment"]["durability"]
        assert dur["type"] == "has"
        assert dur["duration_max"] == 200
        assert dur["wear_per_use"] == 5
        assert dur["destroy_on_zero"] is False
        assert dur["affects_stats"] is True

    def test_artifact_no_durability(self):
        """文物 (quality=7) 不应有耐久"""
        data = {"hybrid_items": [_make_v1_hybrid(
            equipment_mode="weapon",
            quality=7,
            duration_max=999,
        )]}
        _pass_v1_to_v2(data)
        dur = data["hybrid_items"][0]["equipment"]["durability"]
        assert dur["type"] == "none"

    # ---- Quality ----

    def test_quality_common(self):
        data = {"hybrid_items": [_make_v1_hybrid(quality=1)]}
        _pass_v1_to_v2(data)
        assert data["hybrid_items"][0]["quality"]["type"] == "common"

    def test_quality_unique(self):
        data = {"hybrid_items": [_make_v1_hybrid(quality=6)]}
        _pass_v1_to_v2(data)
        assert data["hybrid_items"][0]["quality"]["type"] == "unique"

    def test_quality_artifact(self):
        data = {"hybrid_items": [_make_v1_hybrid(quality=7)]}
        _pass_v1_to_v2(data)
        assert data["hybrid_items"][0]["quality"]["type"] == "artifact"

    # ---- Trigger ----

    def test_trigger_none(self):
        data = {"hybrid_items": [_make_v1_hybrid(trigger_mode="none")]}
        _pass_v1_to_v2(data)
        assert data["hybrid_items"][0]["trigger"]["type"] == "none"

    def test_trigger_effect(self):
        attrs = {"Health_Restoration": 10}
        data = {"hybrid_items": [_make_v1_hybrid(
            trigger_mode="effect",
            consumable_attributes=attrs,
            poison_duration=5,
        )]}
        _pass_v1_to_v2(data)
        trig = data["hybrid_items"][0]["trigger"]
        assert trig["type"] == "effect"
        assert trig["consumable_attributes"] == attrs
        assert trig["poison_duration"] == 5

    def test_trigger_skill(self):
        data = {"hybrid_items": [_make_v1_hybrid(
            trigger_mode="skill",
            skill_object="o_skill_fire",
        )]}
        _pass_v1_to_v2(data)
        trig = data["hybrid_items"][0]["trigger"]
        assert trig["type"] == "skill"
        assert trig["skill_object"] == "o_skill_fire"

    # ---- Charges ----

    def test_charges_limited_with_trigger(self):
        data = {"hybrid_items": [_make_v1_hybrid(
            trigger_mode="effect",
            consumable_attributes={},
            charge_mode="limited",
            charge=5,
            draw_charges=True,
        )]}
        _pass_v1_to_v2(data)
        ch = data["hybrid_items"][0]["charges"]
        assert ch["type"] == "limited"
        assert ch["max_charges"] == 5
        assert ch["draw_charges"] is True

    def test_charges_unlimited_with_trigger(self):
        data = {"hybrid_items": [_make_v1_hybrid(
            trigger_mode="effect",
            consumable_attributes={},
            charge_mode="unlimited",
            draw_charges=False,
        )]}
        _pass_v1_to_v2(data)
        ch = data["hybrid_items"][0]["charges"]
        assert ch["type"] == "unlimited"

    def test_charges_none_when_no_trigger(self):
        """trigger_mode=none 时，charge_mode 被忽略，结果为 NoCharges"""
        data = {"hybrid_items": [_make_v1_hybrid(
            trigger_mode="none",
            charge_mode="unlimited",
            charge=99,
        )]}
        _pass_v1_to_v2(data)
        assert data["hybrid_items"][0]["charges"]["type"] == "none"

    # ---- ChargeRecovery ----

    def test_charge_recovery_none(self):
        data = {"hybrid_items": [_make_v1_hybrid(has_charge_recovery=False)]}
        _pass_v1_to_v2(data)
        assert data["hybrid_items"][0]["charge_recovery"]["type"] == "none"

    def test_charge_recovery_interval(self):
        data = {"hybrid_items": [_make_v1_hybrid(
            has_charge_recovery=True,
            charge_recovery_interval=20,
        )]}
        _pass_v1_to_v2(data)
        cr = data["hybrid_items"][0]["charge_recovery"]
        assert cr["type"] == "interval"
        assert cr["interval"] == 20

    # ---- Spawn ----

    def test_spawn_excluded(self):
        data = {"hybrid_items": [_make_v1_hybrid(exclude_from_random=True)]}
        _pass_v1_to_v2(data)
        assert data["hybrid_items"][0]["spawn"]["type"] == "excluded"

    def test_spawn_random(self):
        data = {"hybrid_items": [_make_v1_hybrid(
            exclude_from_random=False,
            container_spawn="equipment",
            shop_spawn="item",
            quality_tag="unique",
            dungeon_tag="crypt",
            country_tag="aldor",
            extra_tags=["test"],
        )]}
        _pass_v1_to_v2(data)
        sp = data["hybrid_items"][0]["spawn"]
        assert sp["type"] == "random"
        assert sp["container_spawn"] == "equipment"
        assert sp["shop_spawn"] == "item"
        assert sp["quality_tag"] == "unique"
        assert sp["country_tag"] == "aldor"
        assert sp["extra_tags"] == ["test"]

    # ---- Weight fixup ----

    def test_weight_very_light_fixed(self):
        """VeryLight → Very Light"""
        data = {"hybrid_items": [_make_v1_hybrid(weight="VeryLight")]}
        _pass_v1_to_v2(data)
        assert data["hybrid_items"][0]["weight"] == "Very Light"

    def test_weight_normal_untouched(self):
        """正常的 weight 不应被修改"""
        data = {"hybrid_items": [_make_v1_hybrid(weight="Heavy")]}
        _pass_v1_to_v2(data)
        assert data["hybrid_items"][0]["weight"] == "Heavy"

    # ---- Residual field cleanup ----

    def test_obsolete_fields_removed(self):
        """废弃字段应被清理"""
        data = {"hybrid_items": [_make_v1_hybrid(
            rarity="Common",
            slot="heal",
        )]}
        _pass_v1_to_v2(data)
        h = data["hybrid_items"][0]
        assert "rarity" not in h
        assert "slot" not in h
        assert "equipment_mode" not in h
        assert "trigger_mode" not in h
        assert "charge_mode" not in h

    # ---- Already V2 skip ----

    def test_already_v2_hybrid_skipped(self):
        """已是 V2 结构的 hybrid 不应被重复迁移"""
        v2_item = {
            "id": "test",
            "equipment": {"type": "weapon", "weapon_type": "sword"},
            "quality": {"type": "unique"},
        }
        data = {"hybrid_items": [v2_item]}
        original = deepcopy(v2_item)
        _pass_v1_to_v2(data)
        assert data["hybrid_items"][0]["equipment"] == original["equipment"]
        assert data["hybrid_items"][0]["quality"] == original["quality"]


# ============================================================================
# V1→V2 Weapon/Armor 贴图迁移
# ============================================================================


class TestV1ToV2WeaponTextures:
    """武器贴图 V1→V2 迁移"""

    def test_basic_weapon_char_texture(self):
        weapon = {
            "textures": {
                "inventory": ["inv.png"],
                "loot": ["loot.png"],
                "character": ["char.png"],
                "character_left": [],
            }
        }
        data = {"weapons": [weapon]}
        _pass_v1_to_v2(data)
        tex = data["weapons"][0]["textures"]
        assert tex["char"]["type"] == "weapon"
        assert tex["char"]["main"]["paths"] == ["char.png"]
        assert tex["loot"]["paths"] == ["loot.png"]

    def test_weapon_with_offset(self):
        weapon = {
            "textures": {
                "inventory": [],
                "loot": [],
                "character": ["char.png"],
                "character_left": ["left.png"],
                "offset_x": 3,
                "offset_y": -2,
                "offset_x_left": 1,
                "offset_y_left": 0,
            }
        }
        data = {"weapons": [weapon]}
        _pass_v1_to_v2(data)
        char = data["weapons"][0]["textures"]["char"]
        assert char["main"]["origin"]["x"] == CHAR_MODEL_ORIGIN[0] + 3
        assert char["main"]["origin"]["y"] == CHAR_MODEL_ORIGIN[1] - 2

    def test_weapon_relative_loot_speed(self):
        weapon = {
            "textures": {
                "inventory": [],
                "loot": ["l.png"],
                "character": [],
                "character_left": [],
                "loot_use_relative_speed": True,
                "loot_fps": 0.5,
            }
        }
        data = {"weapons": [weapon]}
        _pass_v1_to_v2(data)
        speed = data["weapons"][0]["textures"]["loot"]["speed"]
        assert speed["type"] == "relative"
        assert speed["multiplier"] == 0.5


class TestV1ToV2ArmorTextures:
    """护甲贴图 V1→V2 迁移"""

    def test_multi_pose_armor(self):
        armor = {
            "slot": "Head",
            "textures": {
                "inventory": ["inv.png"],
                "loot": [],
                "character": ["standing0.png"],
                "character_standing1": "standing1.png",
                "character_rest": "rest.png",
            },
        }
        data = {"armors": [armor]}
        _pass_v1_to_v2(data)
        char = data["armors"][0]["textures"]["char"]
        assert char["type"] == "multi_pose"
        assert char["standing0"]["path"] == "standing0.png"
        assert char["standing1"]["path"] == "standing1.png"
        assert char["rest"]["path"] == "rest.png"

    def test_shield_uses_weapon_texture(self):
        armor = {
            "slot": "shield",
            "textures": {
                "inventory": [],
                "loot": [],
                "character": ["shield.png"],
                "character_left": [],
            },
        }
        data = {"armors": [armor]}
        _pass_v1_to_v2(data)
        char = data["armors"][0]["textures"]["char"]
        assert char["type"] == "weapon"
        assert char["main"]["paths"] == ["shield.png"]

    def test_accessory_no_char_texture(self):
        """饰品 (Ring/Amulet/Waist) 无角色贴图"""
        for slot in ("Ring", "Amulet", "Waist"):
            armor = {
                "slot": slot,
                "textures": {
                    "inventory": ["inv.png"],
                    "loot": [],
                    "character": [],
                },
            }
            data = {"armors": [armor]}
            _pass_v1_to_v2(data)
            assert data["armors"][0]["textures"]["char"]["type"] == "none"

    def test_multi_pose_with_female_variants(self):
        armor = {
            "slot": "Chest",
            "textures": {
                "inventory": [],
                "loot": [],
                "character": ["m_stand0.png"],
                "character_standing1": "m_stand1.png",
                "character_rest": "m_rest.png",
                "character_female": "f_stand0.png",
                "character_standing1_female": "f_stand1.png",
                "character_rest_female": "f_rest.png",
                "offset_x_female": 2,
                "offset_y_female": -1,
            },
        }
        data = {"armors": [armor]}
        _pass_v1_to_v2(data)
        char = data["armors"][0]["textures"]["char"]
        assert char["standing0_female"]["path"] == "f_stand0.png"
        assert char["standing1_female"]["path"] == "f_stand1.png"
        assert char["rest_female"]["path"] == "f_rest.png"
        # 女性版 offset → origin
        assert char["standing0_female"]["origin"]["x"] == CHAR_MODEL_ORIGIN[0] + 2


# ============================================================================
# V2→V3 QualitySpec 迁移
# ============================================================================


class TestV2ToV3Quality:
    """QualitySpec tagged union → int"""

    @pytest.mark.parametrize("tag,expected_int", [
        ("common", 1),
        ("unique", 6),
        ("artifact", 7),
    ])
    def test_quality_dict_to_int(self, tag, expected_int):
        data = {"hybrid_items": [{"id": "test", "quality": {"type": tag}}]}
        _pass_v2_to_v3(data)
        assert data["hybrid_items"][0]["quality"] == expected_int

    def test_unknown_tag_defaults_to_common(self):
        data = {"hybrid_items": [{"id": "test", "quality": {"type": "unknown"}}]}
        _pass_v2_to_v3(data)
        assert data["hybrid_items"][0]["quality"] == 1

    def test_already_int_untouched(self):
        data = {"hybrid_items": [{"id": "test", "quality": 6}]}
        _pass_v2_to_v3(data)
        assert data["hybrid_items"][0]["quality"] == 6

    def test_no_hybrid_items_noop(self):
        data = {"weapons": []}
        _pass_v2_to_v3(data)  # 不应报错

    def test_v1_through_v3_end_to_end(self):
        """V1 数据经过完整 migrate 后 quality 为 int"""
        data = {
            "schema_version": 1,
            "hybrid_items": [{
                "id": "test",
                "equipment_mode": "none",
                "trigger_mode": "none",
                "charge_mode": "limited",
                "quality": 7,
                "charge": 1,
                "draw_charges": False,
                "has_charge_recovery": False,
                "exclude_from_random": True,
                "textures": {},
            }],
        }
        result, migrated = migrate(data)
        assert migrated is True
        assert result["hybrid_items"][0]["quality"] == 7
        assert result["schema_version"] == CURRENT_SCHEMA_VERSION
