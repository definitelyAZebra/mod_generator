# -*- coding: utf-8 -*-
"""
Pytest conftest — 共享 fixtures 和测试工具
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from core.models import ModProject


# ============================================================================
# 路径常量
# ============================================================================

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECTS_DIR = FIXTURES_DIR / "projects"
FRAGMENTS_DIR = FIXTURES_DIR / "fragments"


# ============================================================================
# 动态发现所有 fixture 项目
# ============================================================================

def _all_project_dirs() -> list[Path]:
    """扫描 fixtures/projects/ 下所有包含 project.json 的目录"""
    if not PROJECTS_DIR.exists():
        return []
    return sorted(
        p for p in PROJECTS_DIR.iterdir()
        if p.is_dir() and (p / "project.json").exists()
    )


ALL_PROJECT_DIRS = _all_project_dirs()


# ============================================================================
# Fixtures — 项目路径
# ============================================================================


@pytest.fixture(params=ALL_PROJECT_DIRS, ids=lambda p: p.name)
def fixture_project_dir(request: pytest.FixtureRequest) -> Path:
    """每个用户样本项目的目录路径（参数化）"""
    return request.param


@pytest.fixture
def fixture_project_json(fixture_project_dir: Path) -> Path:
    """每个用户样本项目的 project.json 路径"""
    return fixture_project_dir / "project.json"


@pytest.fixture
def raw_project_data(fixture_project_json: Path) -> dict:
    """加载原始 JSON 数据（未迁移）"""
    with open(fixture_project_json, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def loaded_project(fixture_project_json: Path) -> ModProject:
    """完整加载（含迁移）的 ModProject 实例"""
    project, _ = ModProject.load(str(fixture_project_json))
    assert project is not None, f"Failed to load {fixture_project_json}"
    return project


# ============================================================================
# Fixtures — 临时项目
# ============================================================================

@pytest.fixture
def tmp_project_dir(tmp_path: Path) -> Path:
    """一个干净的临时项目目录（含 assets 子目录）"""
    assets = tmp_path / "assets"
    assets.mkdir()
    return tmp_path


@pytest.fixture
def empty_project(tmp_project_dir: Path) -> ModProject:
    """已保存到临时目录的空项目"""
    project = ModProject()
    project.save(str(tmp_project_dir / "project.json"))
    return project


# ============================================================================
# Fixtures — 复制 fixture 到临时目录（用于需要写入的测试）
# ============================================================================

@pytest.fixture
def writable_fixture(fixture_project_dir: Path, tmp_path: Path) -> Path:
    """将 fixture 复制到 tmp_path，用于需要修改/保存的测试"""
    dest = tmp_path / fixture_project_dir.name
    shutil.copytree(fixture_project_dir, dest)
    return dest
