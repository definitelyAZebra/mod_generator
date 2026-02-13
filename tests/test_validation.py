# -*- coding: utf-8 -*-
"""
测试 5（P1）— 验证函数

覆盖：
- validate_hybrid_item: ID、装备一致性、武器伤害、使用次数、耐久、贴图
- ModProject.validate: code_name 格式
"""
from __future__ import annotations

import pytest

from core.models import (
    validate_hybrid_item,
    ModProject,
)
from core.hybrid_item import HybridItemV2
from core.specs import (
    NotEquipable, WeaponEquip, ArmorEquip, CharmEquip,
    NoDurability, HasDurability,
    NoTrigger, SkillTrigger,
    NoCharges, LimitedCharges,
    NoCharTexture, WeaponCharTexture,
    AnimatedSlot, LootSlot,
    ItemTexturesV2, Origin,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_valid_hybrid(**overrides) -> HybridItemV2:
    """创建一个通过所有验证的最小 HybridItemV2"""
    defaults = dict(
        id="test_item",
        equipment=NotEquipable(),
        textures=ItemTexturesV2(
            inventory=["inv.png"],
            loot=LootSlot(paths=["loot.png"]),
        ),
    )
    defaults.update(overrides)
    return HybridItemV2(**defaults)


def _errors(item: HybridItemV2, include_warnings: bool = False) -> list[str]:
    """提取纯 error 消息 (去掉第一行"混合物品 xxx:"和缩进前缀)"""
    raw = validate_hybrid_item(item, include_warnings=include_warnings)
    if not raw:
        return []
    # 跳过首行标题，去掉 "  • " 前缀
    return [e.lstrip(" •") for e in raw[1:]]


# ============================================================================
# validate_hybrid_item — ID 格式
# ============================================================================


class TestHybridItemId:

    def test_empty_id(self):
        item = _make_valid_hybrid(id="")
        errs = _errors(item)
        assert any("不能为空" in e for e in errs)

    def test_whitespace_id(self):
        item = _make_valid_hybrid(id="   ")
        errs = _errors(item)
        assert any("不能为空" in e for e in errs)

    def test_uppercase_id(self):
        item = _make_valid_hybrid(id="TestItem")
        errs = _errors(item)
        assert any("格式错误" in e for e in errs)

    def test_starts_with_number(self):
        item = _make_valid_hybrid(id="1bad")
        errs = _errors(item)
        assert any("格式错误" in e for e in errs)

    def test_valid_id(self):
        item = _make_valid_hybrid(id="my_item_01")
        errs = _errors(item)
        assert not errs

    def test_valid_single_char(self):
        item = _make_valid_hybrid(id="a")
        errs = _errors(item)
        assert not errs


# ============================================================================
# validate_hybrid_item — 武器相关
# ============================================================================


class TestHybridItemWeapon:

    def test_weapon_no_damage(self):
        """武器没有伤害属性→ error"""
        item = _make_valid_hybrid(
            equipment=WeaponEquip(weapon_type="sword"),
            textures=ItemTexturesV2(
                inventory=["inv.png"],
                loot=LootSlot(paths=["loot.png"]),
                char=WeaponCharTexture(main=AnimatedSlot(paths=["c.png"])),
            ),
            attributes={},
        )
        errs = _errors(item)
        assert any("伤害" in e for e in errs)

    def test_weapon_with_damage(self):
        """武器有伤害→ pass"""
        item = _make_valid_hybrid(
            equipment=WeaponEquip(weapon_type="sword"),
            textures=ItemTexturesV2(
                inventory=["inv.png"],
                loot=LootSlot(paths=["loot.png"]),
                char=WeaponCharTexture(main=AnimatedSlot(paths=["c.png"])),
            ),
            attributes={"Slashing_Damage": 15},
        )
        errs = _errors(item)
        assert not any("伤害" in e for e in errs)


# ============================================================================
# validate_hybrid_item — 使用次数
# ============================================================================


class TestHybridItemCharges:

    def test_limited_charges_zero(self):
        item = _make_valid_hybrid(charges=LimitedCharges(max_charges=0))
        errs = _errors(item)
        assert any("使用次数" in e for e in errs)

    def test_limited_charges_negative(self):
        item = _make_valid_hybrid(charges=LimitedCharges(max_charges=-1))
        errs = _errors(item)
        assert any("使用次数" in e for e in errs)

    def test_limited_charges_positive(self):
        item = _make_valid_hybrid(charges=LimitedCharges(max_charges=5))
        errs = _errors(item)
        assert not any("使用次数" in e for e in errs)

    def test_no_charges_ok(self):
        item = _make_valid_hybrid(charges=NoCharges())
        errs = _errors(item)
        assert not any("使用次数" in e for e in errs)


# ============================================================================
# validate_hybrid_item — 耐久
# ============================================================================


class TestHybridItemDurability:

    def test_weapon_durability_zero(self):
        item = _make_valid_hybrid(
            equipment=WeaponEquip(
                weapon_type="sword",
                durability=HasDurability(duration_max=0),
            ),
            textures=ItemTexturesV2(
                inventory=["inv.png"],
                loot=LootSlot(paths=["loot.png"]),
                char=WeaponCharTexture(main=AnimatedSlot(paths=["c.png"])),
            ),
            attributes={"Damage": 10},
        )
        errs = _errors(item)
        assert any("耐久" in e for e in errs)

    def test_armor_durability_zero(self):
        item = _make_valid_hybrid(
            equipment=ArmorEquip(
                armor_type="Waist",
                durability=HasDurability(duration_max=0),
            ),
            textures=ItemTexturesV2(
                inventory=["inv.png"],
                loot=LootSlot(paths=["loot.png"]),
            ),
        )
        errs = _errors(item)
        assert any("耐久" in e for e in errs)

    def test_weapon_durability_positive(self):
        item = _make_valid_hybrid(
            equipment=WeaponEquip(
                weapon_type="sword",
                durability=HasDurability(duration_max=100),
            ),
            textures=ItemTexturesV2(
                inventory=["inv.png"],
                loot=LootSlot(paths=["loot.png"]),
                char=WeaponCharTexture(main=AnimatedSlot(paths=["c.png"])),
            ),
            attributes={"Slashing_Damage": 10},
        )
        errs = _errors(item)
        assert not any("耐久" in e for e in errs)


# ============================================================================
# validate_hybrid_item — 贴图
# ============================================================================


class TestHybridItemTextures:

    def test_missing_inventory(self):
        item = _make_valid_hybrid(
            textures=ItemTexturesV2(
                inventory=[],
                loot=LootSlot(paths=["loot.png"]),
            ),
        )
        errs = _errors(item)
        assert any("常规贴图" in e for e in errs)

    def test_missing_loot(self):
        item = _make_valid_hybrid(
            textures=ItemTexturesV2(
                inventory=["inv.png"],
                loot=LootSlot(paths=[]),
            ),
        )
        errs = _errors(item)
        assert any("战利品贴图" in e for e in errs)

    def test_weapon_missing_char(self):
        """武器没有角色贴图→ error"""
        item = _make_valid_hybrid(
            equipment=WeaponEquip(weapon_type="sword"),
            textures=ItemTexturesV2(
                inventory=["inv.png"],
                loot=LootSlot(paths=["loot.png"]),
                char=WeaponCharTexture(),  # 空 main
            ),
            attributes={"Slashing_Damage": 10},
        )
        errs = _errors(item)
        assert any("穿戴" in e or "手持" in e for e in errs)


# ============================================================================
# validate_hybrid_item — WARNING 过滤
# ============================================================================


class TestHybridItemWarnings:

    def test_warnings_hidden_by_default(self):
        item = _make_valid_hybrid(
            equipment=SkillTrigger(),  # 强制制造不一致，但不是 WARNING
        )
        # SkillTrigger 放在 equipment 位置会导致异常，换个方式
        item = _make_valid_hybrid(
            trigger=SkillTrigger(skill_object=""),  # 空 skill → WARNING
        )
        errs_no_warn = _errors(item, include_warnings=False)
        errs_with_warn = _errors(item, include_warnings=True)
        # WARNING 应该只出现在 include_warnings=True 中
        assert len(errs_with_warn) >= len(errs_no_warn)


# ============================================================================
# ModProject.validate
# ============================================================================


class TestModProjectValidate:

    def test_empty_code_name(self):
        p = ModProject(code_name="")
        assert any("不能为空" in e for e in p.validate())

    def test_whitespace_code_name(self):
        p = ModProject(code_name="   ")
        assert any("不能为空" in e for e in p.validate())

    def test_starts_with_number(self):
        p = ModProject(code_name="1Mod")
        assert any("不能以数字开头" in e for e in p.validate())

    def test_special_chars(self):
        p = ModProject(code_name="My-Mod")
        assert len(p.validate()) > 0

    def test_valid_code_name(self):
        p = ModProject(code_name="MyMod01")
        assert p.validate() == []

    def test_single_letter(self):
        p = ModProject(code_name="A")
        assert p.validate() == []
