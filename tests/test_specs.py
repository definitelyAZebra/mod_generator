# -*- coding: utf-8 -*-
"""
测试 4（P1）— core/specs.py 纯函数 & 领域逻辑

覆盖：
- quality_*: to_int, from_int, has_durability, to_rarity
- equipment_*: slot, is_equipable, hands, class vars
- needs_*: char_texture, left_texture, multi_pose
- charge_*: effective_value, has_charges, draw_charges
- durability / trigger / recovery helpers
- spawn_effective_tags / build_tags
- Origin: from_offset ↔ to_offset round-trip, is_default, adjustment
- MultiPoseCharTexture: resolve, is_ui_enabled, clear_with_cascade
- char_texture_for_equipment
- ItemTexturesV2: has_char, has_loot, clear helpers
- LootAnimationSpeed: loot_speed_to_preview_fps
"""
from __future__ import annotations

import pytest

from core.specs import (
    # Quality
    CommonQuality, UniqueQuality, ArtifactQuality,
    quality_to_int, quality_from_int, quality_has_durability, quality_to_rarity,
    # Equipment
    NotEquipable, WeaponEquip, ArmorEquip, CharmEquip,
    equipment_slot, equipment_is_equipable, equipment_hands,
    is_weapon_mode, is_armor_mode, is_charm_mode,
    needs_char_texture, needs_left_texture, needs_multi_pose,
    # Durability
    NoDurability, HasDurability,
    durability_has_durability, durability_max,
    # Trigger
    NoTrigger, EffectTrigger, SkillTrigger,
    trigger_has_effect,
    # Charges
    NoCharges, LimitedCharges, UnlimitedCharges,
    charge_effective_value, charge_has_charges, charge_draw_charges,
    # Recovery
    NoRecovery, IntervalRecovery,
    recovery_has_recovery, recovery_interval,
    # Spawn
    ExcludedFromRandom, RandomSpawn, SpawnRuleType,
    spawn_effective_tags, spawn_is_excluded,
    # Origin
    Origin,
    # CharTexture
    NoCharTexture, WeaponCharTexture, MultiPoseCharTexture,
    AnimatedSlot, StaticSlot, LootSlot,
    char_texture_for_equipment,
    # LootSpeed
    AbsoluteFps, RelativeSpeed, loot_speed_to_preview_fps,
    # Textures
    ItemTexturesV2,
)
from constants import CHAR_MODEL_ORIGIN


# ============================================================================
# QualitySpec helpers
# ============================================================================


class TestQualityHelpers:

    @pytest.mark.parametrize("spec,expected", [
        (CommonQuality, 1),
        (UniqueQuality, 6),
        (ArtifactQuality, 7),
    ])
    def test_quality_to_int(self, spec, expected):
        assert quality_to_int(spec) == expected

    @pytest.mark.parametrize("value,expected", [
        (1, CommonQuality),
        (6, UniqueQuality),
        (7, ArtifactQuality),
        (0, CommonQuality),   # 未知值默认 Common
        (99, CommonQuality),
    ])
    def test_quality_from_int(self, value, expected):
        assert quality_from_int(value) == expected

    def test_quality_round_trip(self):
        for spec in [CommonQuality, UniqueQuality, ArtifactQuality]:
            assert quality_from_int(quality_to_int(spec)) == spec

    @pytest.mark.parametrize("spec,expected", [
        (CommonQuality, True),
        (UniqueQuality, True),
        (ArtifactQuality, False),
    ])
    def test_quality_has_durability(self, spec, expected):
        assert quality_has_durability(spec) == expected

    @pytest.mark.parametrize("spec,expected", [
        (CommonQuality, ""),
        (UniqueQuality, "Unique"),
        (ArtifactQuality, "Unique"),
    ])
    def test_quality_to_rarity(self, spec, expected):
        assert quality_to_rarity(spec) == expected


# ============================================================================
# EquipmentSpec helpers
# ============================================================================


class TestEquipmentHelpers:

    def test_not_equipable_slot(self):
        assert equipment_slot(NotEquipable()) == "heal"

    def test_weapon_slot(self):
        assert equipment_slot(WeaponEquip()) == "hand"

    @pytest.mark.parametrize("armor_type", [
        "Head", "Chest", "Arms", "Legs", "Back",
        "Waist", "Ring", "Amulet", "shield",
    ])
    def test_armor_slot_equals_type(self, armor_type):
        assert equipment_slot(ArmorEquip(armor_type=armor_type)) == armor_type

    def test_charm_slot(self):
        assert equipment_slot(CharmEquip()) == "heal"

    @pytest.mark.parametrize("spec,expected", [
        (NotEquipable(), False),
        (WeaponEquip(), True),
        (ArmorEquip(), True),
        (CharmEquip(), False),
    ])
    def test_equipment_is_equipable(self, spec, expected):
        assert equipment_is_equipable(spec) == expected

    @pytest.mark.parametrize("weapon_type,expected_hands", [
        ("sword", 1), ("dagger", 1), ("axe", 1), ("mace", 1),
        ("2hsword", 2), ("2haxe", 2), ("2hmace", 2), ("2hStaff", 2),
        ("bow", 2), ("crossbow", 2), ("spear", 2),
    ])
    def test_weapon_hands(self, weapon_type, expected_hands):
        w = WeaponEquip(weapon_type=weapon_type)
        assert equipment_hands(w) == expected_hands
        assert w.hands == expected_hands

    def test_non_weapon_hands_is_one(self):
        assert equipment_hands(NotEquipable()) == 1
        assert equipment_hands(ArmorEquip()) == 1
        assert equipment_hands(CharmEquip()) == 1

    @pytest.mark.parametrize("spec,is_w,is_a,is_c", [
        (WeaponEquip(), True, False, False),
        (ArmorEquip(), False, True, False),
        (CharmEquip(), False, False, True),
        (NotEquipable(), False, False, False),
    ])
    def test_mode_predicates(self, spec, is_w, is_a, is_c):
        assert is_weapon_mode(spec) == is_w
        assert is_armor_mode(spec) == is_a
        assert is_charm_mode(spec) == is_c


# ============================================================================
# needs_* 谓词
# ============================================================================


class TestNeedsCharTexture:

    def test_weapon_needs_char(self):
        assert needs_char_texture(WeaponEquip()) is True

    def test_shield_needs_char(self):
        assert needs_char_texture(ArmorEquip(armor_type="shield")) is True

    @pytest.mark.parametrize("slot", ["Head", "Chest", "Arms", "Legs", "Back"])
    def test_multi_pose_armor_needs_char(self, slot):
        assert needs_char_texture(ArmorEquip(armor_type=slot)) is True

    @pytest.mark.parametrize("slot", ["Waist", "Ring", "Amulet"])
    def test_accessory_no_char(self, slot):
        assert needs_char_texture(ArmorEquip(armor_type=slot)) is False

    def test_not_equipable_no_char(self):
        assert needs_char_texture(NotEquipable()) is False

    def test_charm_no_char(self):
        assert needs_char_texture(CharmEquip()) is False


class TestNeedsLeftTexture:

    @pytest.mark.parametrize("wtype", ["sword", "dagger", "axe", "mace"])
    def test_single_hand_needs_left(self, wtype):
        assert needs_left_texture(WeaponEquip(weapon_type=wtype)) is True

    @pytest.mark.parametrize("wtype", ["2hsword", "bow", "spear", "2hStaff"])
    def test_two_hand_no_left(self, wtype):
        assert needs_left_texture(WeaponEquip(weapon_type=wtype)) is False

    def test_non_weapon_no_left(self):
        assert needs_left_texture(ArmorEquip()) is False
        assert needs_left_texture(NotEquipable()) is False


class TestNeedsMultiPose:

    @pytest.mark.parametrize("slot", ["Head", "Chest", "Arms", "Legs", "Back"])
    def test_body_armor_needs_multi_pose(self, slot):
        assert needs_multi_pose(ArmorEquip(armor_type=slot)) is True

    @pytest.mark.parametrize("slot", ["shield", "Waist", "Ring", "Amulet"])
    def test_no_multi_pose(self, slot):
        assert needs_multi_pose(ArmorEquip(armor_type=slot)) is False

    def test_weapon_no_multi_pose(self):
        assert needs_multi_pose(WeaponEquip()) is False


# ============================================================================
# DurabilitySpec helpers
# ============================================================================


class TestDurabilityHelpers:

    def test_no_durability(self):
        assert durability_has_durability(NoDurability()) is False
        assert durability_max(NoDurability()) == 0

    def test_has_durability(self):
        d = HasDurability(duration_max=250)
        assert durability_has_durability(d) is True
        assert durability_max(d) == 250


# ============================================================================
# TriggerSpec helpers
# ============================================================================


class TestTriggerHelpers:

    def test_no_trigger(self):
        assert trigger_has_effect(NoTrigger()) is False

    def test_effect_trigger(self):
        assert trigger_has_effect(EffectTrigger()) is True

    def test_skill_trigger(self):
        assert trigger_has_effect(SkillTrigger()) is True


# ============================================================================
# ChargeSpec helpers
# ============================================================================


class TestChargeHelpers:

    @pytest.mark.parametrize("spec,expected", [
        (NoCharges(), 0),
        (LimitedCharges(max_charges=5), 5),
        (UnlimitedCharges(), 1),
    ])
    def test_charge_effective_value(self, spec, expected):
        assert charge_effective_value(spec) == expected

    @pytest.mark.parametrize("spec,expected", [
        (NoCharges(), False),
        (LimitedCharges(), True),
        (UnlimitedCharges(), True),
    ])
    def test_charge_has_charges(self, spec, expected):
        assert charge_has_charges(spec) == expected

    @pytest.mark.parametrize("spec,expected", [
        (NoCharges(), False),
        (LimitedCharges(draw_charges=True), True),
        (LimitedCharges(draw_charges=False), False),
        (UnlimitedCharges(draw_charges=True), True),
    ])
    def test_charge_draw_charges(self, spec, expected):
        assert charge_draw_charges(spec) == expected


# ============================================================================
# ChargeRecoverySpec helpers
# ============================================================================


class TestRecoveryHelpers:

    def test_no_recovery(self):
        assert recovery_has_recovery(NoRecovery()) is False
        assert recovery_interval(NoRecovery()) == 0

    def test_interval_recovery(self):
        r = IntervalRecovery(interval=20)
        assert recovery_has_recovery(r) is True
        assert recovery_interval(r) == 20


# ============================================================================
# SpawnSpec helpers
# ============================================================================


class TestSpawnHelpers:

    def test_excluded_tags(self):
        assert spawn_effective_tags(ExcludedFromRandom()) == "special"

    def test_excluded_predicate(self):
        assert spawn_is_excluded(ExcludedFromRandom()) is True
        assert spawn_is_excluded(RandomSpawn()) is False

    def test_random_empty_tags(self):
        assert spawn_effective_tags(RandomSpawn()) == ""

    def test_random_build_tags(self):
        s = RandomSpawn(
            quality_tag="unique",
            dungeon_tag="crypt",
            country_tag="aldor",
            extra_tags=["special"],
        )
        assert spawn_effective_tags(s) == "unique crypt aldor special"

    def test_random_partial_tags(self):
        s = RandomSpawn(quality_tag="common")
        assert spawn_effective_tags(s) == "common"


# ============================================================================
# Origin
# ============================================================================


class TestOrigin:

    def test_default_is_char_model(self):
        o = Origin()
        assert o.is_default is True
        assert o.is_aligned_to_char is True
        assert (o.x, o.y) == CHAR_MODEL_ORIGIN

    def test_char_model_factory(self):
        o = Origin.char_model()
        assert o.is_default is True

    def test_non_default(self):
        o = Origin(24, 36)
        assert o.is_default is False
        assert o.x == 24 and o.y == 36

    def test_adjustment(self):
        o = Origin(CHAR_MODEL_ORIGIN[0] + 3, CHAR_MODEL_ORIGIN[1] - 2)
        assert o.adjustment == (3, -2)

    def test_default_adjustment_is_zero(self):
        assert Origin().adjustment == (0, 0)

    def test_from_offset_round_trip(self):
        """from_offset → to_offset 应为 identity"""
        for ox, oy in [(0, 0), (3, -2), (-5, 10)]:
            origin = Origin.from_offset(ox, oy)
            assert origin.to_offset() == (ox, oy)

    def test_to_offset_round_trip(self):
        """to_offset → from_offset 应为 identity"""
        o = Origin(25, 30)
        ox, oy = o.to_offset()
        assert Origin.from_offset(ox, oy) == o


# ============================================================================
# MultiPoseCharTexture 领域方法
# ============================================================================


class TestMultiPoseCharTexture:

    def _make(self, **kwargs) -> MultiPoseCharTexture:
        """创建 MultiPoseCharTexture，指定哪些 slot 有贴图"""
        m = MultiPoseCharTexture()
        for slot, path in kwargs.items():
            setattr(m, slot, StaticSlot(path=path))
        return m

    # --- resolve ---

    def test_resolve_direct(self):
        m = self._make(standing0="s0.png")
        slot, fb = m.resolve("standing0")
        assert slot.path == "s0.png"
        assert fb is None  # 无 fallback

    def test_resolve_standing1_fallback_to_standing0(self):
        m = self._make(standing0="s0.png")
        slot, fb = m.resolve("standing1")
        assert slot.path == "s0.png"
        assert fb == "standing0"

    def test_resolve_standing1_female_full_chain(self):
        """standing1_female fallback → standing0_female → standing1 → standing0"""
        m = self._make(standing0="s0.png")
        slot, fb = m.resolve("standing1_female")
        assert slot.path == "s0.png"
        assert fb == "standing0"  # 走完整条 fallback 链到底

    def test_resolve_standing0_female_fallback(self):
        m = self._make(standing0="s0.png")
        slot, fb = m.resolve("standing0_female")
        assert slot.path == "s0.png"
        assert fb == "standing0"

    def test_resolve_no_fallback_available(self):
        m = MultiPoseCharTexture()
        slot, fb = m.resolve("standing0")
        assert slot.path == ""
        assert fb is None

    # --- is_ui_enabled ---

    def test_ui_enabled_no_requires(self):
        """standing0 没有前置条件，始终启用"""
        m = MultiPoseCharTexture()
        assert m.is_ui_enabled("standing0") is True

    def test_ui_enabled_standing1_female_needs_both(self):
        """standing1_female 需要 standing1 和 standing0_female 都有"""
        m = self._make(standing1="s1.png")
        assert m.is_ui_enabled("standing1_female") is False

        m = self._make(standing0_female="s0f.png")
        assert m.is_ui_enabled("standing1_female") is False

        m = self._make(standing1="s1.png", standing0_female="s0f.png")
        assert m.is_ui_enabled("standing1_female") is True

    # --- clear_with_cascade ---

    def test_clear_standing1_cascades_to_female(self):
        m = self._make(standing1="s1.png", standing1_female="s1f.png")
        cleared = m.clear_with_cascade("standing1")
        assert "standing1" in cleared
        assert "standing1_female" in cleared
        assert m.standing1.path == ""
        assert m.standing1_female.path == ""

    def test_clear_standing0_female_cascades(self):
        m = self._make(standing0_female="s0f.png", standing1_female="s1f.png")
        cleared = m.clear_with_cascade("standing0_female")
        assert "standing0_female" in cleared
        assert "standing1_female" in cleared

    def test_clear_no_cascade_when_empty(self):
        m = self._make(standing1="s1.png")
        cleared = m.clear_with_cascade("standing1")
        assert cleared == ["standing1"]  # standing1_female 已空，不出现


# ============================================================================
# char_texture_for_equipment
# ============================================================================


class TestCharTextureForEquipment:

    def test_weapon(self):
        assert isinstance(char_texture_for_equipment(WeaponEquip()), WeaponCharTexture)

    def test_shield(self):
        assert isinstance(char_texture_for_equipment(ArmorEquip(armor_type="shield")), WeaponCharTexture)

    @pytest.mark.parametrize("slot", ["Head", "Chest", "Arms", "Legs", "Back"])
    def test_multi_pose_armor(self, slot):
        assert isinstance(char_texture_for_equipment(ArmorEquip(armor_type=slot)), MultiPoseCharTexture)

    @pytest.mark.parametrize("slot", ["Waist", "Ring", "Amulet"])
    def test_accessory_no_char(self, slot):
        assert isinstance(char_texture_for_equipment(ArmorEquip(armor_type=slot)), NoCharTexture)

    def test_not_equipable(self):
        assert isinstance(char_texture_for_equipment(NotEquipable()), NoCharTexture)

    def test_charm(self):
        assert isinstance(char_texture_for_equipment(CharmEquip()), NoCharTexture)


# ============================================================================
# ItemTexturesV2 辅助方法
# ============================================================================


class TestItemTexturesV2:

    def test_has_char_weapon(self):
        t = ItemTexturesV2(char=WeaponCharTexture(main=AnimatedSlot(paths=["a.png"])))
        assert t.has_char() is True

    def test_has_char_weapon_empty(self):
        t = ItemTexturesV2(char=WeaponCharTexture())
        assert t.has_char() is False

    def test_has_char_multi_pose(self):
        t = ItemTexturesV2(char=MultiPoseCharTexture(standing0=StaticSlot(path="s.png")))
        assert t.has_char() is True

    def test_has_char_no_texture(self):
        t = ItemTexturesV2(char=NoCharTexture())
        assert t.has_char() is False

    def test_has_char_left(self):
        t = ItemTexturesV2(char=WeaponCharTexture(left=AnimatedSlot(paths=["l.png"])))
        assert t.has_char_left() is True

    def test_has_loot(self):
        t = ItemTexturesV2(loot=LootSlot(paths=["loot.png"]))
        assert t.has_loot() is True
        assert ItemTexturesV2().has_loot() is False

    def test_clear_char_weapon(self):
        t = ItemTexturesV2(char=WeaponCharTexture(
            main=AnimatedSlot(paths=["a.png"], origin=Origin(25, 30)),
            left=AnimatedSlot(paths=["l.png"]),
        ))
        t.clear_char()
        assert not t.has_char()
        # clear_char 清 main 和 left
        # 根据实现: clear_char 只清 main，left 需要用 clear_left
        assert t.has_char_left() is True  # left 未被 clear_char 清除

    def test_clear_left(self):
        t = ItemTexturesV2(char=WeaponCharTexture(left=AnimatedSlot(paths=["l.png"])))
        t.clear_left()
        assert t.has_char_left() is False


# ============================================================================
# LootAnimationSpeed
# ============================================================================


class TestLootAnimationSpeed:

    def test_absolute_fps(self):
        assert loot_speed_to_preview_fps(AbsoluteFps(fps=15.0)) == 15.0

    def test_relative_speed_default_game_fps(self):
        # 默认 game_fps=40, multiplier=0.25 → 10.0
        assert loot_speed_to_preview_fps(RelativeSpeed(multiplier=0.25)) == 10.0

    def test_relative_speed_custom_game_fps(self):
        assert loot_speed_to_preview_fps(RelativeSpeed(multiplier=0.5), game_fps=60.0) == 30.0
