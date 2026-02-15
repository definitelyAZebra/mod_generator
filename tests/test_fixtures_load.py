# -*- coding: utf-8 -*-
"""
测试 1（P0）— 用户样本项目加载回归

使用 17 个真实用户 fixture 项目验证：
- 所有样本都能加载
- 所有 v1 样本都触发迁移
- 加载 → 保存 → 再加载 round-trip 数据一致
- 加载后模型结构完整
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from core.models import ModProject, Weapon, Armor
from core.hybrid_item import HybridItemV2
from core.specs import (
    WeaponCharTexture,
    MultiPoseCharTexture,
    NoCharTexture,
    ItemTexturesV2,
)
from migrations import CURRENT_SCHEMA_VERSION


# ============================================================================
# 加载成功
# ============================================================================


class TestFixtureLoad:
    """所有用户样本都能成功加载"""

    def test_load_succeeds(self, fixture_project_json: Path):
        """每个 fixture 都能成功加载为 ModProject"""
        project, _ = ModProject.load(str(fixture_project_json))
        assert project is not None

    def test_project_has_basic_fields(self, loaded_project: ModProject):
        """加载后的项目有合法的基础字段"""
        assert isinstance(loaded_project.name, str)
        assert isinstance(loaded_project.code_name, str)
        assert isinstance(loaded_project.weapons, list)
        assert isinstance(loaded_project.armors, list)
        assert isinstance(loaded_project.hybrid_items, list)

    def test_weapons_are_weapon_type(self, loaded_project: ModProject):
        """所有武器都是 Weapon 实例"""
        for w in loaded_project.weapons:
            assert isinstance(w, Weapon), f"{w.name} is not Weapon"

    def test_armors_are_armor_type(self, loaded_project: ModProject):
        """所有护甲都是 Armor 实例"""
        for a in loaded_project.armors:
            assert isinstance(a, Armor), f"{a.name} is not Armor"

    def test_hybrids_are_v2(self, loaded_project: ModProject):
        """所有混合物品都是 HybridItemV2"""
        for h in loaded_project.hybrid_items:
            assert isinstance(h, HybridItemV2), f"{h.id} is not HybridItemV2"

    def test_item_textures_are_v2(self, loaded_project: ModProject):
        """所有物品的贴图都是 ItemTexturesV2"""
        for item in loaded_project.weapons + loaded_project.armors:
            assert isinstance(item.textures, ItemTexturesV2)
        for h in loaded_project.hybrid_items:
            assert isinstance(h.textures, ItemTexturesV2)


# ============================================================================
# 迁移触发
# ============================================================================


class TestFixtureMigration:
    """所有 fixture 项目的迁移行为"""

    def test_all_fixtures_trigger_migration(
        self, fixture_project_json: Path, raw_project_data: dict
    ):
        """所有样本都是 v1 schema（无版本字段），应触发迁移"""
        # 确认原始数据确实没有或版本 < 2
        version = raw_project_data.get("schema_version", 1)
        assert version < CURRENT_SCHEMA_VERSION, (
            f"Expected v1 fixture, got v{version}"
        )

    def test_migration_flag_is_true(self, fixture_project_json: Path):
        """load() 返回的 migrated 标志应为 True"""
        _, migrated = ModProject.load(str(fixture_project_json))
        assert migrated is True


# ============================================================================
# Round-trip: 加载 → 保存 → 再加载
# ============================================================================


class TestFixtureRoundTrip:
    """加载 → 保存 → 再加载 的数据一致性"""

    def test_round_trip_preserves_item_counts(
        self, loaded_project: ModProject, tmp_path: Path
    ):
        """round-trip 后物品数量不变"""
        n_weapons = len(loaded_project.weapons)
        n_armors = len(loaded_project.armors)
        n_hybrids = len(loaded_project.hybrid_items)

        save_path = str(tmp_path / "project.json")
        loaded_project.save(save_path)

        project2, migrated2 = ModProject.load(save_path)
        assert project2 is not None
        assert migrated2 is False, "Re-saved project should not need migration"

        assert len(project2.weapons) == n_weapons
        assert len(project2.armors) == n_armors
        assert len(project2.hybrid_items) == n_hybrids

    def test_round_trip_preserves_project_metadata(
        self, loaded_project: ModProject, tmp_path: Path
    ):
        """round-trip 后项目元数据不变"""
        save_path = str(tmp_path / "project.json")
        loaded_project.save(save_path)
        project2, _ = ModProject.load(save_path)
        assert project2 is not None

        assert project2.name == loaded_project.name
        assert project2.code_name == loaded_project.code_name
        assert project2.author == loaded_project.author
        assert project2.version == loaded_project.version
        assert project2.target_version == loaded_project.target_version

    def test_round_trip_preserves_weapon_fields(
        self, loaded_project: ModProject, tmp_path: Path
    ):
        """round-trip 后武器关键字段不变"""
        if not loaded_project.weapons:
            pytest.skip("No weapons in this fixture")

        save_path = str(tmp_path / "project.json")
        loaded_project.save(save_path)
        project2, _ = ModProject.load(save_path)
        assert project2 is not None

        for w1, w2 in zip(loaded_project.weapons, project2.weapons):
            assert w1.name == w2.name
            assert w1.slot == w2.slot
            assert w1.tier == w2.tier
            assert w1.rarity == w2.rarity
            assert w1.mat == w2.mat
            assert w1.price == w2.price
            assert w1.attributes == w2.attributes

    def test_round_trip_preserves_armor_fields(
        self, loaded_project: ModProject, tmp_path: Path
    ):
        """round-trip 后护甲关键字段不变"""
        if not loaded_project.armors:
            pytest.skip("No armors in this fixture")

        save_path = str(tmp_path / "project.json")
        loaded_project.save(save_path)
        project2, _ = ModProject.load(save_path)
        assert project2 is not None

        for a1, a2 in zip(loaded_project.armors, project2.armors):
            assert a1.name == a2.name
            assert a1.slot == a2.slot
            assert a1.tier == a2.tier
            assert a1.rarity == a2.rarity
            assert a1.mat == a2.mat
            assert a1.armor_class == a2.armor_class
            assert a1.attributes == a2.attributes

    def test_round_trip_preserves_hybrid_fields(
        self, loaded_project: ModProject, tmp_path: Path
    ):
        """round-trip 后混合物品关键字段不变"""
        if not loaded_project.hybrid_items:
            pytest.skip("No hybrid items in this fixture")

        save_path = str(tmp_path / "project.json")
        loaded_project.save(save_path)
        project2, _ = ModProject.load(save_path)
        assert project2 is not None

        for h1, h2 in zip(loaded_project.hybrid_items, project2.hybrid_items):
            assert h1.id == h2.id
            assert h1.quality.value == h2.quality.value
            assert h1.slot == h2.slot
            assert h1.weight == h2.weight
            assert h1.tier == h2.tier
            assert h1.material == h2.material
            assert h1.base_price == h2.base_price
            assert h1.attributes == h2.attributes
            assert type(h1.equipment) is type(h2.equipment)
            assert type(h1.trigger) is type(h2.trigger)
            assert type(h1.charges) is type(h2.charges)
            assert type(h1.spawn) is type(h2.spawn)

    def test_round_trip_json_is_v2(self, loaded_project: ModProject, tmp_path: Path):
        """保存后的 JSON 文件 schema_version 为当前版本"""
        save_path = tmp_path / "project.json"
        loaded_project.save(str(save_path))

        with open(save_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["schema_version"] == CURRENT_SCHEMA_VERSION


# ============================================================================
# 贴图结构完整性
# ============================================================================


class TestFixtureTextures:
    """加载后的贴图结构完整且类型正确"""

    def test_weapon_textures_are_weapon_char(self, loaded_project: ModProject):
        """武器的 char 贴图应为 WeaponCharTexture"""
        for w in loaded_project.weapons:
            assert isinstance(w.textures.char, WeaponCharTexture), (
                f"Weapon {w.name} char texture should be WeaponCharTexture, "
                f"got {type(w.textures.char).__name__}"
            )

    def test_multi_pose_armor_textures(self, loaded_project: ModProject):
        """多姿势护甲 (头/身/手/腿/背) 的 char 应为 MultiPoseCharTexture"""
        for a in loaded_project.armors:
            if a.needs_multi_pose_textures():
                assert isinstance(a.textures.char, MultiPoseCharTexture), (
                    f"Armor {a.name} (slot={a.slot}) should have MultiPoseCharTexture, "
                    f"got {type(a.textures.char).__name__}"
                )

    def test_non_char_armor_textures(self, loaded_project: ModProject):
        """饰品类护甲 (腰带/戒指/项链) 的 char 应为 NoCharTexture"""
        no_char_slots = {"Waist", "Ring", "Amulet"}
        for a in loaded_project.armors:
            if a.slot in no_char_slots:
                assert isinstance(a.textures.char, NoCharTexture), (
                    f"Armor {a.name} (slot={a.slot}) should have NoCharTexture, "
                    f"got {type(a.textures.char).__name__}"
                )
