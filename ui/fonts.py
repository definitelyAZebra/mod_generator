# -*- coding: utf-8 -*-
"""字体管理服务 — ImGui 1.92 动态光栅化架构

利用 ImGui 1.92 的 RendererHasTextures 后端:
- 字形按需加载和光栅化，不需要指定 glyph ranges
- 字号可随时通过 push_font(None, size) 动态切换
- 只需注册一次字体源 (EN + CN + Icon 合并)
- 不需要手动 Build() 或刷新纹理

缩放模型:
    渲染字号 = FontSizeBase × FontScaleMain × FontScaleDpi
    - FontSizeBase: 逻辑字号 (如 16.0)
    - FontScaleMain: 用户缩放因子 (默认 1.0)
    - FontScaleDpi: DPI 缩放因子 (如 1.5 for 150%)

字号命名 (Tailwind CSS v3.4):
    xs=12  sm=14  base/md=16  lg=18  xl=20
    2xl=24  3xl=30  4xl=36  5xl=48

使用方式:
    from ui.fonts import compute_font_px
    from ui import imgui_shim as imgui

    # 初始化 (一次)
    load_fonts(renderer)

    # 渲染时动态切换字号 (无需预加载)
    imgui.push_font(None, compute_font_px("xl"))
    imgui.text("大标题")
    imgui.pop_font()

    # 默认字号由 style.font_size_base 控制，无需 push
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ui import imgui_shim as imgui
from ui import config
from ui.state import dpi_scale

if TYPE_CHECKING:
    pass


# ==================== 字号常量 ====================

# Tailwind CSS v3.4.17 字号 (px)
# Source: https://tailwindcss.com/docs/font-size
FONT_SIZES: dict[str, float] = {
    "xs": 12.0,     # 0.75rem - caption, hints
    "sm": 14.0,     # 0.875rem - small text
    "base": 16.0,   # 1rem - body text (DEFAULT)
    "lg": 18.0,     # 1.125rem - large body
    "xl": 20.0,     # 1.25rem - heading
    "2xl": 24.0,    # 1.5rem - h3
    "3xl": 30.0,    # 1.875rem - h2
    "4xl": 36.0,    # 2.25rem - h1
    "5xl": 48.0,    # 3rem - display
    "6xl": 60.0,    # 3.75rem - hero
    "7xl": 72.0,    # 4.5rem
    "8xl": 96.0,    # 6rem
    "9xl": 128.0,   # 8rem
}

# 别名: md = base (向后兼容)
FONT_SIZES["md"] = FONT_SIZES["base"]

# 默认字号 token
DEFAULT_SIZE_TOKEN = "base"


# ==================== 从生成配置导入 ====================
# 字体路径和 baseline 偏移由 codegen/generate_font_config.py 自动测定
# 修改字体请编辑 codegen 中配置，然后运行 python codegen/generate_font_config.py

from ui.font_config import (
    ENGLISH_FONT,
    CHINESE_FONT,
    ICON_FONT,
    BASE_FONT_SIZE,
    CHINESE_GLYPH_OFFSET_Y,
    ICON_GLYPH_OFFSET_Y,
    ICON_SCALE,
)


# ==================== 公共 API ====================


def compute_font_px(token: str) -> float:
    """计算字号 token 对应的逻辑像素值 (未缩放)

    返回值传给 push_font(None, size) 作为 font_size_base_unscaled。
    ImGui 会自动乘以 style.FontScaleMain × style.FontScaleDpi。

    Args:
        token: "xs", "sm", "base", "md", "lg", "xl", "2xl" 等

    Returns:
        逻辑像素值 (如 16.0 for "base", 20.0 for "xl")

    Example:
        imgui.push_font(None, compute_font_px("xl"))
        imgui.text("大标题")
        imgui.pop_font()
    """
    return FONT_SIZES.get(token, FONT_SIZES[DEFAULT_SIZE_TOKEN])


# ==================== 字体加载 ====================


def load_fonts(renderer: Any) -> None:
    """注册字体源到 ImGui atlas (EN + CN + Icon 合并)

    ImGui 1.92 动态光栅化架构:
    - 只注册字体源，字形按需光栅化到纹理
    - 不需要指定 glyph ranges (CJK 等自动按需加载)
    - 不需要预烘焙多个字号
    - 不需要手动 Build()

    通过 style 属性控制缩放:
    - font_size_base: 基准逻辑字号
    - font_scale_main: 用户缩放因子
    - font_scale_dpi: DPI 缩放因子

    Args:
        renderer: GlfwRenderer 实例
    """
    io = imgui.get_io()
    io.fonts.clear_fonts()

    # 字体路径
    en_path = ENGLISH_FONT if os.path.exists(ENGLISH_FONT) else ""
    cn_path = CHINESE_FONT if os.path.exists(CHINESE_FONT) else ""
    icon_path = ICON_FONT if os.path.exists(ICON_FONT) else ""

    if not en_path:
        print(f"[fonts] 警告: 未找到英文字体 {ENGLISH_FONT}，使用默认字体")
    if not cn_path:
        print(f"[fonts] 警告: 未找到中文字体 {CHINESE_FONT}")
    if not icon_path:
        print(f"[fonts] 警告: 未找到图标字体 {ICON_FONT}")

    # --- 1. 英文主字体 (决定 baseline) ---
    font = None
    if en_path:
        try:
            font = io.fonts.add_font_from_file_ttf(en_path)
        except Exception as e:
            print(f"[fonts] 英文字体加载失败: {e}")

    if font is None:
        font = io.fonts.add_font_default()

    # --- 2. 中文字体 (合并，带 baseline 补偿) ---
    # GlyphOffset 在 1.92 中会随渲染字号自动等比缩放
    if cn_path:
        try:
            cn_cfg = imgui.core.FontConfig(
                merge_mode=True,
                pixel_snap_h=True,
                glyph_offset_y=CHINESE_GLYPH_OFFSET_Y,
            )
            io.fonts.add_font_from_file_ttf(
                cn_path, BASE_FONT_SIZE, font_cfg=cn_cfg.handle,
            )
        except Exception as e:
            print(f"[fonts] 中文字体加载失败: {e}")

    # --- 3. 图标字体 (合并，等宽对齐) ---
    # 使用 subset 字体 (fa-subset.ttf)，由 codegen/generate_icon_font.py 生成
    if icon_path:
        try:
            icon_cfg = imgui.core.FontConfig(
                merge_mode=True,
                pixel_snap_h=True,
                glyph_offset_y=ICON_GLYPH_OFFSET_Y,
                glyph_min_advance_x=BASE_FONT_SIZE * ICON_SCALE,
            )
            io.fonts.add_font_from_file_ttf(
                icon_path, BASE_FONT_SIZE * ICON_SCALE,
                font_cfg=icon_cfg.handle,
            )
        except Exception as e:
            print(f"[fonts] 图标字体加载失败: {e}")

    # --- 4. 设置默认字号和缩放因子 ---
    style = imgui.get_style()
    style.font_size_base = FONT_SIZES[DEFAULT_SIZE_TOKEN]
    style.font_scale_dpi = dpi_scale()
    style.font_scale_main = config.get_font_scale()

    # 1.92 后端自动管理纹理 (refresh 是 no-op 兼容)
    try:
        renderer.refresh_font_texture()
    except Exception as e:
        print(f"[fonts] 刷新字体纹理失败: {e}")

    print(
        f"[fonts] 字体已注册 (1.92 动态光栅化), "
        f"base={FONT_SIZES[DEFAULT_SIZE_TOKEN]}px, "
        f"dpi={dpi_scale():.2f}, scale={config.get_font_scale():.2f}"
    )


def update_font_scale() -> None:
    """更新缩放因子 (无需重新注册字体)

    当用户改变字体缩放或 DPI 变化时调用。
    比 load_fonts() 更轻量，不会清空字形缓存。
    """
    style = imgui.get_style()
    style.font_scale_dpi = dpi_scale()
    style.font_scale_main = config.get_font_scale()


def reload_fonts(renderer: Any) -> None:
    """重新加载字体 (完全重建，DPI 或字体文件变更后调用)"""
    load_fonts(renderer)


# ==================== 废弃兼容层 ====================
# 以下保留仅为 styles.py 类型注解兼容，将在后续版本移除


@dataclass
class FontSet:
    """[废弃] 旧版字体集，1.92 不再需要预加载多个字号。"""
    sm: Any = None
    base: Any = None
    lg: Any = None
    xl: Any = None

    @property
    def md(self) -> Any:
        return self.base

    @property
    def xs(self) -> Any:
        return self.sm

    def get(self, size: str) -> Any:
        return self.base

    def __getitem__(self, size: str) -> Any:
        return self.base

    def default(self) -> Any:
        return self.base


_fonts: FontSet | None = None


def get_fonts() -> FontSet:
    """[废弃] 返回空 FontSet"""
    return _fonts or FontSet()


def get_font(size: str = "base") -> Any:
    """[废弃] 请使用 push_font(None, compute_font_px(token))"""
    return None
