# -*- coding: utf-8 -*-
"""
测试 6（P1）— 代码生成 (codegen)

覆盖：
- calculate_crop_region: 边界裁剪逻辑
- calculate_clamped_origin: Origin 钳制
- format_description: 多行描述 → C# 注入格式
- format_description_gml: GML 描述格式
- CodeGenerator._escape_multiline_string: C# verbatim string 转义
"""
from __future__ import annotations

import pytest

from codegen.textures import (
    calculate_crop_region,
    calculate_clamped_origin,
    format_description,
    format_description_gml,
)
from codegen.generator import CodeGenerator
from core.specs import Origin
from core.models import ModProject
from constants import (
    VALID_MIN_X, VALID_MAX_X, VALID_MIN_Y, VALID_MAX_Y,
    GML_ANCHOR_X, GML_ANCHOR_Y,
    VIEWPORT_CHAR_OFFSET_X, VIEWPORT_CHAR_OFFSET_Y,
)


# ============================================================================
# calculate_crop_region
# ============================================================================


class TestCalculateCropRegion:

    def test_zero_offset(self):
        """无偏移时，裁剪区域 = 有效区域与图片的交集"""
        # 默认: VALID_MIN_X=-8, VALID_MAX_X=56, VALID_MIN_Y=-12, VALID_MAX_Y=52
        # 48x40 图片
        x1, y1, x2, y2, valid = calculate_crop_region(48, 40, 0, 0)
        assert valid is True
        assert x1 == 0       # max(0, -8) = 0
        assert y1 == 0       # max(0, -12) = 0
        assert x2 == 48      # min(48, 56) = 48
        assert y2 == 40      # min(40, 52) = 40

    def test_positive_offset(self):
        """正偏移 → 有效区域右移/下移"""
        x1, y1, x2, y2, valid = calculate_crop_region(48, 40, 5, 5)
        assert valid is True
        assert x1 == 0       # max(0, -8+5) = max(0, -3) = 0
        assert y1 == 0       # max(0, -12+5) = max(0, -7) = 0
        assert x2 == 48      # min(48, 56+5) = 48
        assert y2 == 40      # min(40, 52+5) = 40

    def test_negative_offset_clips_start(self):
        """负偏移可能将有效区域起点推入图片内"""
        x1, y1, x2, y2, valid = calculate_crop_region(48, 40, -20, -20)
        assert valid is True
        assert x1 == max(0, VALID_MIN_X - 20)
        assert y1 == max(0, VALID_MIN_Y - 20)

    def test_extreme_offset_invalid(self):
        """极端偏移导致裁剪区域为空"""
        _, _, _, _, valid = calculate_crop_region(48, 40, -200, 0)
        assert valid is False

    def test_large_image_zero_offset(self):
        """大图无偏移"""
        x1, y1, x2, y2, valid = calculate_crop_region(200, 200, 0, 0)
        assert valid is True
        # VALID_MIN_X=-8 → 裁剪起点 0 (clamped)
        assert x1 == 0
        assert x2 == VALID_MAX_X  # 56
        assert y2 == VALID_MAX_Y  # 52

    def test_1x1_image(self):
        """最小尺寸图片（1×1）"""
        x1, y1, x2, y2, valid = calculate_crop_region(1, 1, 0, 0)
        assert valid is True
        assert x1 == 0 and y1 == 0
        assert x2 == 1 and y2 == 1


# ============================================================================
# calculate_clamped_origin
# ============================================================================


class TestCalculateClampedOrigin:

    def test_default_origin_returns_none(self):
        assert calculate_clamped_origin(Origin()) is None

    def test_slight_offset(self):
        """微调：x-2 → 仍在有效范围"""
        result = calculate_clamped_origin(Origin(20, 30))
        assert result is not None
        x, y = result
        # x=20 >= 22-8=14 → ok
        # y=30 >= 34-12=22 → ok
        assert x == 20
        assert y == 30

    def test_extreme_negative_clamped(self):
        """极端偏移被钳制"""
        result = calculate_clamped_origin(Origin(0, 0))
        assert result is not None
        x, y = result
        assert x == GML_ANCHOR_X - VIEWPORT_CHAR_OFFSET_X  # 14
        assert y == GML_ANCHOR_Y - VIEWPORT_CHAR_OFFSET_Y  # 22

    def test_clamped_to_default_returns_none(self):
        """钳制后恢复为默认值 → 返回 None"""
        # 例: Origin(30, 40) → clamped = max(30,14)=30, max(40,22)=40 → 不等于默认
        # 需要一个值使得 max(x, 14) = 22 且 max(y, 22) = 34
        # 即 x >= 22 且 y >= 34
        assert calculate_clamped_origin(Origin(22, 34)) is None  # 就是默认值
        assert calculate_clamped_origin(Origin(25, 37)) is not None  # 不等于默认


# ============================================================================
# format_description
# ============================================================================


class TestFormatDescription:

    def test_empty(self):
        assert format_description("") == ""

    def test_single_line(self):
        assert format_description("Hello") == "Hello"

    def test_multi_line(self):
        text = "Line 1\nLine 2\nLine 3"
        assert format_description(text) == "Line 1#Line 2#Line 3"

    def test_strips_whitespace(self):
        text = "  Hello  \n  World  "
        assert format_description(text) == "Hello#World"

    def test_escapes_quotes(self):
        text = 'He said "hello"'
        assert format_description(text) == 'He said \\"hello\\"'

    def test_blank_lines_removed(self):
        text = "Line 1\n\n  \nLine 2"
        assert format_description(text) == "Line 1#Line 2"


class TestFormatDescriptionGml:

    def test_empty(self):
        assert format_description_gml("") == ""

    def test_single_line(self):
        assert format_description_gml("Hello") == "Hello"

    def test_preserves_hash_newlines(self):
        """GML 用 # 作换行符，不做换行转译"""
        text = "Line 1#Line 2"
        assert format_description_gml(text) == "Line 1#Line 2"

    def test_escapes_quotes(self):
        text = 'He said "hello"'
        assert format_description_gml(text) == 'He said \\"hello\\"'

    def test_strips_outer_whitespace(self):
        text = "  Hello World  "
        assert format_description_gml(text) == "Hello World"


# ============================================================================
# CodeGenerator._escape_multiline_string
# ============================================================================


class TestEscapeMultilineString:

    @pytest.fixture()
    def gen(self):
        """CodeGenerator 需要 project 参数"""
        proj = ModProject(code_name="TestMod")
        return CodeGenerator(proj)

    def test_empty(self, gen):
        assert gen._escape_multiline_string("") == ""

    def test_no_quotes(self, gen):
        assert gen._escape_multiline_string("Hello world") == "Hello world"

    def test_double_quotes_escaped(self, gen):
        assert gen._escape_multiline_string('He said "hi"') == 'He said ""hi""'

    def test_multiple_quotes(self, gen):
        result = gen._escape_multiline_string('"A" and "B"')
        assert result == '""A"" and ""B""'
