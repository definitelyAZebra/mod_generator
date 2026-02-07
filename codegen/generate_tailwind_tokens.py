"""
Generate Tailwind-style tokens for ImGui.

This script generates ui/tw.py with pre-built StyleContext constants
that can be composed using the | operator.

Usage:
    python codegen/generate_tailwind_tokens.py

Outputs:
    ui/tw.py - Tailwind-style token constants

Design:
    - All tokens are pre-built StyleContext instances
    - Naming follows Tailwind conventions: text_gray_500, bg_slate_800, p_4, rounded_lg
    - Agent should use these like Tailwind CSS classes

Token Categories:
    - Colors: text_*, bg_*, border_*
    - Spacing: p_*, gap_*, space_y_*, space_x_*
    - Sizing: w_*, h_*
    - Typography: text_xs, text_sm, text_base, text_lg, ...
    - Radius: rounded_*
    - Buttons: btn_primary, btn_secondary, ...

==============================================================================
🎨 主题色系统 (Theme Colors) - 详见 ui/theme.py
==============================================================================

本项目使用 **暗黑2 + 紫水晶** 风格主题色:
  - crystal (紫水晶): 主强调色，用于主按钮、选中状态
  - goldrim (金边): 次强调色，暗黑2经典金色
  - abyss (深渊): 带紫调的深黑背景
  - parchment (羊皮纸): 温暖米黄色文字
  - blood (血红): 危险/错误色
  - stone (岩石): 中性深灰，边框/分隔线

完整设计理念和使用指南请参阅: ui/theme.py
==============================================================================
"""

from pathlib import Path

# Tailwind CSS v3.4.17 Official Colors
# Source: https://github.com/tailwindlabs/tailwindcss/blob/v3.4.17/src/public/colors.js
COLORS = {
    "black": "#000000",
    "white": "#ffffff",
    "slate": {
        50: "#f8fafc", 100: "#f1f5f9", 200: "#e2e8f0", 300: "#cbd5e1",
        400: "#94a3b8", 500: "#64748b", 600: "#475569", 700: "#334155",
        800: "#1e293b", 900: "#0f172a", 950: "#020617",
    },
    "gray": {
        50: "#f9fafb", 100: "#f3f4f6", 200: "#e5e7eb", 300: "#d1d5db",
        400: "#9ca3af", 500: "#6b7280", 600: "#4b5563", 700: "#374151",
        800: "#1f2937", 900: "#111827", 950: "#030712",
    },
    "zinc": {
        50: "#fafafa", 100: "#f4f4f5", 200: "#e4e4e7", 300: "#d4d4d8",
        400: "#a1a1aa", 500: "#71717a", 600: "#52525b", 700: "#3f3f46",
        800: "#27272a", 900: "#18181b", 950: "#09090b",
    },
    "neutral": {
        50: "#fafafa", 100: "#f5f5f5", 200: "#e5e5e5", 300: "#d4d4d4",
        400: "#a3a3a3", 500: "#737373", 600: "#525252", 700: "#404040",
        800: "#262626", 900: "#171717", 950: "#0a0a0a",
    },
    "stone": {
        50: "#fafaf9", 100: "#f5f5f4", 200: "#e7e5e4", 300: "#d6d3d1",
        400: "#a8a29e", 500: "#78716c", 600: "#57534e", 700: "#44403c",
        800: "#292524", 900: "#1c1917", 950: "#0c0a09",
    },
    "red": {
        50: "#fef2f2", 100: "#fee2e2", 200: "#fecaca", 300: "#fca5a5",
        400: "#f87171", 500: "#ef4444", 600: "#dc2626", 700: "#b91c1c",
        800: "#991b1b", 900: "#7f1d1d", 950: "#450a0a",
    },
    "orange": {
        50: "#fff7ed", 100: "#ffedd5", 200: "#fed7aa", 300: "#fdba74",
        400: "#fb923c", 500: "#f97316", 600: "#ea580c", 700: "#c2410c",
        800: "#9a3412", 900: "#7c2d12", 950: "#431407",
    },
    "amber": {
        50: "#fffbeb", 100: "#fef3c7", 200: "#fde68a", 300: "#fcd34d",
        400: "#fbbf24", 500: "#f59e0b", 600: "#d97706", 700: "#b45309",
        800: "#92400e", 900: "#78350f", 950: "#451a03",
    },
    "yellow": {
        50: "#fefce8", 100: "#fef9c3", 200: "#fef08a", 300: "#fde047",
        400: "#facc15", 500: "#eab308", 600: "#ca8a04", 700: "#a16207",
        800: "#854d0e", 900: "#713f12", 950: "#422006",
    },
    "lime": {
        50: "#f7fee7", 100: "#ecfccb", 200: "#d9f99d", 300: "#bef264",
        400: "#a3e635", 500: "#84cc16", 600: "#65a30d", 700: "#4d7c0f",
        800: "#3f6212", 900: "#365314", 950: "#1a2e05",
    },
    "green": {
        50: "#f0fdf4", 100: "#dcfce7", 200: "#bbf7d0", 300: "#86efac",
        400: "#4ade80", 500: "#22c55e", 600: "#16a34a", 700: "#15803d",
        800: "#166534", 900: "#14532d", 950: "#052e16",
    },
    "emerald": {
        50: "#ecfdf5", 100: "#d1fae5", 200: "#a7f3d0", 300: "#6ee7b7",
        400: "#34d399", 500: "#10b981", 600: "#059669", 700: "#047857",
        800: "#065f46", 900: "#064e3b", 950: "#022c22",
    },
    "teal": {
        50: "#f0fdfa", 100: "#ccfbf1", 200: "#99f6e4", 300: "#5eead4",
        400: "#2dd4bf", 500: "#14b8a6", 600: "#0d9488", 700: "#0f766e",
        800: "#115e59", 900: "#134e4a", 950: "#042f2e",
    },
    "cyan": {
        50: "#ecfeff", 100: "#cffafe", 200: "#a5f3fc", 300: "#67e8f9",
        400: "#22d3ee", 500: "#06b6d4", 600: "#0891b2", 700: "#0e7490",
        800: "#155e75", 900: "#164e63", 950: "#083344",
    },
    "sky": {
        50: "#f0f9ff", 100: "#e0f2fe", 200: "#bae6fd", 300: "#7dd3fc",
        400: "#38bdf8", 500: "#0ea5e9", 600: "#0284c7", 700: "#0369a1",
        800: "#075985", 900: "#0c4a6e", 950: "#082f49",
    },
    "blue": {
        50: "#eff6ff", 100: "#dbeafe", 200: "#bfdbfe", 300: "#93c5fd",
        400: "#60a5fa", 500: "#3b82f6", 600: "#2563eb", 700: "#1d4ed8",
        800: "#1e40af", 900: "#1e3a8a", 950: "#172554",
    },
    "indigo": {
        50: "#eef2ff", 100: "#e0e7ff", 200: "#c7d2fe", 300: "#a5b4fc",
        400: "#818cf8", 500: "#6366f1", 600: "#4f46e5", 700: "#4338ca",
        800: "#3730a3", 900: "#312e81", 950: "#1e1b4b",
    },
    "violet": {
        50: "#f5f3ff", 100: "#ede9fe", 200: "#ddd6fe", 300: "#c4b5fd",
        400: "#a78bfa", 500: "#8b5cf6", 600: "#7c3aed", 700: "#6d28d9",
        800: "#5b21b6", 900: "#4c1d95", 950: "#2e1065",
    },
    "purple": {
        50: "#faf5ff", 100: "#f3e8ff", 200: "#e9d5ff", 300: "#d8b4fe",
        400: "#c084fc", 500: "#a855f7", 600: "#9333ea", 700: "#7e22ce",
        800: "#6b21a8", 900: "#581c87", 950: "#3b0764",
    },
    "fuchsia": {
        50: "#fdf4ff", 100: "#fae8ff", 200: "#f5d0fe", 300: "#f0abfc",
        400: "#e879f9", 500: "#d946ef", 600: "#c026d3", 700: "#a21caf",
        800: "#86198f", 900: "#701a75", 950: "#4a044e",
    },
    "pink": {
        50: "#fdf2f8", 100: "#fce7f3", 200: "#fbcfe8", 300: "#f9a8d4",
        400: "#f472b6", 500: "#ec4899", 600: "#db2777", 700: "#be185d",
        800: "#9d174d", 900: "#831843", 950: "#500724",
    },
    "rose": {
        50: "#fff1f2", 100: "#ffe4e6", 200: "#fecdd3", 300: "#fda4af",
        400: "#fb7185", 500: "#f43f5e", 600: "#e11d48", 700: "#be123c",
        800: "#9f1239", 900: "#881337", 950: "#4c0519",
    },

    # =========================================================================
    # 自定义主题色 (暗黑2 + 紫水晶风格, 与 stoneshard_asset_browser 一致)
    # 详细设计理念请参阅: ui/theme.py
    # =========================================================================

    # 深渊 (Abyss) - 冷蓝紫中性暗色背景 (H≈248°, 低饱和度)
    "abyss": {
        50: "#f1f1f4", 100: "#e3e2e9", 200: "#cccad8", 300: "#a9a6bf",
        400: "#7e78a0", 500: "#544f73", 600: "#36334d", 700: "#1e1c2b",
        800: "#13121c", 900: "#0a0a10", 950: "#06060a",
    },

    # 羊皮纸 (Parchment) - 温暖米黄色文字 (H≈38°)
    "parchment": {
        50: "#f4efe6", 100: "#e7ddca", 200: "#d7c6a8", 300: "#c9b38d",
        400: "#b89e70", 500: "#a88a57", 600: "#8c734a", 700: "#6d5a3c",
        800: "#4e412c", 900: "#332b1e", 950: "#201b13",
    },

    # 金边 (Goldrim) - 暗黑2经典金色 (H≈42°, 高饱和度)
    "goldrim": {
        50: "#fdf8e8", 100: "#f9edc8", 200: "#efd690", 300: "#e0b952",
        400: "#d1a22e", 500: "#aa842c", 600: "#856828", 700: "#624d22",
        800: "#42341a", 900: "#2a2213", 950: "#18140c",
    },

    # 紫水晶 (Crystal) - 主强调色 (H≈260°, 冷饱和紫, 高饱和度)
    "crystal": {
        50: "#f5f2fd", 100: "#ebe5fb", 200: "#dcd0f6", 300: "#c6b3ef",
        400: "#ae93e6", 500: "#9a79dd", 600: "#845cd1", 700: "#6e40c4",
        800: "#5a359d", 900: "#4c2e7f", 950: "#2d1c4a",
    },

    # 血红 (Blood) - 生命/危险 (H≈3°)
    "blood": {
        50: "#fdeded", 100: "#f9d2d2", 200: "#f3a7a5", 300: "#e76460",
        400: "#c92821", 500: "#97221b", 600: "#801f19", 700: "#5d1913",
        800: "#3e120e", 900: "#290d0a", 950: "#140705",
    },

    # 岩石 (Stone) - 中性暖灰, 使用 Tailwind 原生 stone
}

# Tailwind CSS v3.4.17 Official Spacing (in rem, converted to px at 16px base)
# Source: https://github.com/tailwindlabs/tailwindcss/blob/v3.4.17/stubs/config.full.js
# Keys use underscore for Python compatibility: "0.5" -> "0_5"
SPACING = {
    "0": 0,
    "px": 1,
    "0_5": 2,
    "1": 4,
    "1_5": 6,
    "2": 8,
    "2_5": 10,
    "3": 12,
    "3_5": 14,
    "4": 16,
    "5": 20,
    "6": 24,
    "7": 28,
    "8": 32,
    "9": 36,
    "10": 40,
    "11": 44,
    "12": 48,
    "14": 56,
    "16": 64,
    "20": 80,
    "24": 96,
    "28": 112,
    "32": 128,
    "36": 144,
    "40": 160,
    "44": 176,
    "48": 192,
    "52": 208,
    "56": 224,
    "60": 240,
    "64": 256,
    "72": 288,
    "80": 320,
    "96": 384,
}

# Tailwind CSS v3.4.17 Official Border Radius (in rem, converted to px)
BORDER_RADIUS = {
    "none": 0,
    "sm": 2,
    "DEFAULT": 4,
    "md": 6,
    "lg": 8,
    "xl": 12,
    "2xl": 16,
    "3xl": 24,
    "full": 9999,
}

# Tailwind CSS v3.4.17 Font Sizes (first value in rem, converted to px)
FONT_SIZES = {
    "xs": 12,
    "sm": 14,
    "base": 16,
    "lg": 18,
    "xl": 20,
    "2xl": 24,
    "3xl": 30,
    "4xl": 36,
    "5xl": 48,
    "6xl": 60,
    "7xl": 72,
    "8xl": 96,
    "9xl": 128,
}

# Border widths
BORDER_WIDTHS = {
    "0": 0,
    "DEFAULT": 1,
    "2": 2,
    "4": 4,
    "8": 8,
}

# Tailwind CSS v3.4.17 Width/Height sizing
# Note: We use the same spacing scale for consistency
# w_full and h_full are special (100%)
SIZING = {
    **SPACING,  # 0, px, 0.5, 1, 1.5, ..., 96
}

# Special sizing values (will be handled separately)
SPECIAL_SIZING = {
    "auto": "auto",
    "full": "100%",
    "screen": "100vh/vw",
    "min": "min-content",
    "max": "max-content",
    "fit": "fit-content",
}


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    """Convert hex color to RGBA tuple (0-1 range)."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return (r, g, b, alpha)


def sanitize_name(name: str) -> str:
    """Convert Tailwind name to valid Python identifier."""
    # Replace dots and dashes
    name = name.replace(".", "_").replace("-", "_")
    # Prefix with underscore if starts with number
    if name[0].isdigit():
        name = "_" + name
    return name


def generate_file() -> str:
    """Generate the complete tw.py file."""
    lines = [
        '# -*- coding: utf-8 -*-',
        '"""Tailwind CSS v3.4.17 Design Tokens for ImGui.',
        '',
        'Auto-generated by codegen/generate_tailwind_tokens.py',
        'Source: https://github.com/tailwindlabs/tailwindcss',
        '',
        '==============================================================================',
        '🎨 主题色系统 (Theme Colors) - 暗黑2 + 紫水晶风格',
        '==============================================================================',
        '',
        '本项目使用自定义主题色 (非标准Tailwind):',
        '  • crystal (紫水晶) - 主强调色: btn_crystal, text_crystal_*, bg_crystal_*',
        '  • goldrim (金边)   - 次强调色: btn_goldrim, text_goldrim_*, bg_goldrim_*',
        '  • abyss (深渊)     - 深色背景: btn_abyss, bg_abyss_*',
        '  • parchment (羊皮纸) - 文字色: text_parchment_*',
        '  • blood (血红)     - 危险色: text_blood_*, bg_blood_*',
        '  • stone (岩石)     - 边框/分隔: border_stone_*, bg_stone_*',
        '',
        '语义别名:',
        '  • btn_primary = btn_crystal (紫水晶按钮)',
        '  • btn_secondary = btn_abyss (深渊按钮)',
        '  • text_default / text_muted / text_subtle / text_faint (文字层级)',
        '  • text_accent = text_crystal_400 (强调色)',
        '  • bg_app / bg_surface / bg_elevated / bg_input (背景层级)',
        '',
        '详细设计理念和使用指南请参阅: ui/theme.py',
        '==============================================================================',
        '',
        'Usage:',
        '    from ui import tw',
        '',
        '    with tw.bg_slate_800 | tw.text_white | tw.p_4 | tw.rounded_lg:',
        '        imgui.text("Hello, Tailwind!")',
        '',
        'Available tokens:',
        '    Colors:     text_{color}_{shade}, bg_{color}_{shade}, border_{color}_{shade}',
        '    Spacing:    p_*, gap_*, space_y_*, space_x_*',
        '    Sizing:     w_*, h_* (w_40 = 160px, h_10 = 40px)',
        '    Typography: text_xs, text_sm, text_base, text_lg, text_xl, ...',
        '    Radius:     rounded_none, rounded_sm, rounded, rounded_md, rounded_lg, ...',
        '    Buttons:    btn_primary, btn_secondary, btn_success, btn_danger, ...',
        '',
        'Color palettes:',
        '    slate, gray, zinc, neutral, stone (grays)',
        '    red, orange, amber, yellow, lime, green, emerald, teal, cyan, sky,',
        '    blue, indigo, violet, purple, fuchsia, pink, rose (colors)',
        '',
        'Shades: 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950',
        '"""',
        '',
        'from ui.styles import (',
        '    StyleContext,',
        '    text, bg, border, frame_bg, window_bg, popup_bg,',
        '    frame_padding, window_padding, cell_padding, item_spacing,',

        '    rounding, frame_rounding, child_rounding,',
        '    border_size, frame_border_size, child_border_size, alpha,',
        '    separator,',
        '    when, combine,',
        '    button as button_colors,',
        '    font as font_size,',
        '    width as set_width,',
        '    height as set_height,',
        '    size_meta,',
        ')',
        'from ui.layout import gap_y as _gap_y, gap_x as _gap_x',
        '',
        '',
        '# =============================================================================',
        '# Noop - 空样式上下文，用于条件样式',
        '# =============================================================================',
        '# 用法: with tw.text_red_500 if error else tw.noop:',
        '#           imgui.text(message)',
        '',
        'noop = StyleContext.empty()',
        '',
        '',
        '# =============================================================================',
        '# Raw Color Values (RGBA tuples)',
        '# =============================================================================',
        '',
        'BLACK = (0.0, 0.0, 0.0, 1.0)',
        'WHITE = (1.0, 1.0, 1.0, 1.0)',
        'TRANSPARENT = (0.0, 0.0, 0.0, 0.0)',
        '',
    ]

    # Generate color constants
    for color_name, shades in COLORS.items():
        if isinstance(shades, dict):
            for shade, hex_val in shades.items():
                r, g, b, a = hex_to_rgba(hex_val)
                const_name = f"{color_name.upper()}_{shade}"
                lines.append(f'{const_name} = ({r:.4f}, {g:.4f}, {b:.4f}, {a:.1f})')
            lines.append('')

    lines.extend([
        '',
        '# =============================================================================',
        '# Text Colors - StyleContext wrappers',
        '# =============================================================================',
        '',
    ])

    # Add black/white text first
    lines.append('text_black = text(BLACK)')
    lines.append('text_white = text(WHITE)')
    lines.append('')

    # Generate text color styles
    for color_name, shades in COLORS.items():
        if isinstance(shades, dict):
            for shade in shades.keys():
                const_name = f"{color_name.upper()}_{shade}"
                style_name = f"text_{color_name}_{shade}"
                lines.append(f'{style_name} = text({const_name})')
            lines.append('')

    lines.extend([
        '',
        '# =============================================================================',
        '# Background Colors - StyleContext wrappers',
        '# =============================================================================',
        '',
    ])

    # Add black/white/transparent bg first
    lines.append('bg_black = bg(BLACK)')
    lines.append('bg_white = bg(WHITE)')
    lines.append('bg_transparent = bg(TRANSPARENT)')
    lines.append('')

    # Generate background color styles
    for color_name, shades in COLORS.items():
        if isinstance(shades, dict):
            for shade in shades.keys():
                const_name = f"{color_name.upper()}_{shade}"
                style_name = f"bg_{color_name}_{shade}"
                lines.append(f'{style_name} = bg({const_name})')
            lines.append('')

    lines.extend([
        '',
        '# =============================================================================',
        '# Border Colors - StyleContext wrappers',
        '# =============================================================================',
        '',
    ])

    # Add black/white/transparent border first
    lines.append('border_black = border(BLACK)')
    lines.append('border_white = border(WHITE)')
    lines.append('border_transparent = border(TRANSPARENT)')
    lines.append('')

    # Generate border color styles
    for color_name, shades in COLORS.items():
        if isinstance(shades, dict):
            for shade in shades.keys():
                const_name = f"{color_name.upper()}_{shade}"
                style_name = f"border_{color_name}_{shade}"
                lines.append(f'{style_name} = border({const_name})')
            lines.append('')

    # =========================================================================
    # Separator Colors - 分隔线颜色
    # =========================================================================
    lines.extend([
        '',
        '# =============================================================================',
        '# Separator Colors - 分隔线颜色',
        '# =============================================================================',
        '',
    ])

    # Generate separator color styles for commonly used colors (stone, abyss, slate)
    separator_colors = ['stone', 'abyss', 'slate', 'gray', 'zinc', 'neutral']
    for color_name in separator_colors:
        shades = COLORS.get(color_name, {})
        if isinstance(shades, dict):
            for shade in shades.keys():
                const_name = f"{color_name.upper()}_{shade}"
                style_name = f"separator_{color_name}_{shade}"
                lines.append(f'{style_name} = separator({const_name})')
            lines.append('')

    # =========================================================================
    # Frame Background Colors (输入框/控件背景)
    # =========================================================================
    lines.extend([
        '',
        '# =============================================================================',
        '# Frame Background Colors - 输入框/控件背景色',
        '# =============================================================================',
        '',
    ])

    # Only generate frame_bg for commonly used dark colors (abyss, stone, slate dark shades)
    frame_bg_colors = [
        ('abyss', [600, 700, 800, 900]),
        ('stone', [800, 900, 950]),
        ('slate', [700, 800, 900, 950]),
        ('gray', [700, 800, 900, 950]),
        ('zinc', [700, 800, 900, 950]),
        ('neutral', [700, 800, 900, 950]),
    ]

    for color_name, shades in frame_bg_colors:
        for shade in shades:
            const_name = f"{color_name.upper()}_{shade}"
            style_name = f"frame_bg_{color_name}_{shade}"
            lines.append(f'{style_name} = frame_bg({const_name})')
        lines.append('')

    lines.extend([
        '',
        '# =============================================================================',
        '# Spacing (Padding) - StyleContext wrappers',
        '# =============================================================================',
        '# ⚠️ 设计决策: p_* 只设置 WindowPadding (容器内边距)',
        '#    - Tailwind 用户写 p-4 时想的是"容器内边距"',
        '#    - 控件 (按钮/输入框) 的 padding 由 btn_* 预设内置',
        '#    - 需要手动控制控件 padding 时用 frame_p_*',
        '#',
        '# p_*: 容器内边距 (Child Window)',
        '# frame_p_*: 控件内边距 (按钮、输入框内部)',
        '# px_*/py_*: 单方向容器内边距',
        '',
    ])

    # Generate padding styles (all directions) - 只设置 window_padding
    for name, px_value in SPACING.items():
        style_name = f"p_{name}"
        lines.append(f'{style_name} = window_padding({px_value}, {px_value})')

    lines.append('')
    lines.append('# Horizontal padding only (px-*) - 容器')
    for name, px_value in SPACING.items():
        style_name = f"px_{name}"
        lines.append(f'{style_name} = window_padding({px_value}, None)')

    lines.append('')
    lines.append('# Vertical padding only (py-*) - 容器')
    for name, px_value in SPACING.items():
        style_name = f"py_{name}"
        lines.append(f'{style_name} = window_padding(None, {px_value})')

    # =========================================================================
    # Frame Padding (控件内边距) - 新增
    # =========================================================================
    lines.extend([
        '',
        '',
        '# =============================================================================',
        '# Frame Padding - 控件内边距 (按钮、输入框内部)',
        '# =============================================================================',
        '# frame_p_*: 手动控制控件 padding (通常不需要，btn_* 已内置合理值)',
        '',
    ])

    for name, px_value in SPACING.items():
        style_name = f"frame_p_{name}"
        lines.append(f'{style_name} = frame_padding({px_value}, {px_value})')

    lines.append('')
    lines.append('# Horizontal frame padding (frame_px-*)')
    for name, px_value in SPACING.items():
        style_name = f"frame_px_{name}"
        lines.append(f'{style_name} = frame_padding({px_value}, None)')

    lines.append('')
    lines.append('# Vertical frame padding (frame_py-*)')
    for name, px_value in SPACING.items():
        style_name = f"frame_py_{name}"
        lines.append(f'{style_name} = frame_padding(None, {px_value})')

    lines.extend([
        '',
        '# =============================================================================',
        '# Border Radius - StyleContext wrappers',
        '# =============================================================================',
        '',
    ])

    # Generate border radius styles
    for name, px_value in BORDER_RADIUS.items():
        if name == "DEFAULT":
            style_name = "rounded"
        else:
            # Handle names like "2xl" -> "rounded_2xl"
            safe_name = name.replace("-", "_")
            style_name = f"rounded_{safe_name}"
        lines.append(f'{style_name} = rounding({px_value})')

    lines.extend([
        '',
        '# =============================================================================',
        '# Child Rounding - 子窗口/卡片圆角 (用于 ly.card 等)',
        '# =============================================================================',
        '',
    ])

    # Generate child rounding styles
    for name, px_value in BORDER_RADIUS.items():
        if name == "DEFAULT":
            style_name = "child_rounded"
        else:
            safe_name = name.replace("-", "_")
            style_name = f"child_rounded_{safe_name}"
        lines.append(f'{style_name} = child_rounding({px_value})')

    # =========================================================================
    # Child Border Size - 子窗口边框宽度
    # =========================================================================
    lines.extend([
        '',
        '',
        '# =============================================================================',
        '# Child Border Size - 子窗口边框宽度',
        '# =============================================================================',
        '',
        '# child_border_size(px) 是函数，直接导出供使用',
        '# 用法: with tw.child_border_size(1): ly.card(...)',
    ])

    # =========================================================================
    # Gap (item_spacing) tokens
    # =========================================================================
    lines.extend([
        '',
        '',
        '# =============================================================================',
        '# Gap (Item Spacing) - 控制子元素间距',
        '# =============================================================================',
        '',
    ])

    for name, px_value in SPACING.items():
        style_name = f"gap_{name}"
        lines.append(f'{style_name} = item_spacing({px_value})')

    # =========================================================================
    # Width tokens
    # =========================================================================
    lines.extend([
        '',
        '',
        '# =============================================================================',
        '# Width - 控件宽度 (w_40 = 160px) - 元数据注入，禁止 context manager',
        '# =============================================================================',
        '# 用法: (tw.w_40 | tw.h_9)(imgui.button)("确定")',
        '# 注意: with tw.w_40: ... 会抛出 RuntimeError',
        '',
    ])

    for name, px_value in SIZING.items():
        style_name = f"w_{name}"
        # 将 px 值转换回 Tailwind 单位 (除以 4)
        tw_units = px_value / 4 if px_value != 0 else 0
        lines.append(f'{style_name} = size_meta(width={tw_units})')

    # =========================================================================
    # Height tokens
    # =========================================================================
    lines.extend([
        '',
        '',
        '# =============================================================================',
        '# Height - 控件高度 (h_10 = 40px) - 元数据注入，禁止 context manager',
        '# =============================================================================',
        '# 用法: (tw.w_40 | tw.h_9)(imgui.button)("确定")',
        '# 注意: with tw.h_9: ... 会抛出 RuntimeError',
        '',
    ])

    for name, px_value in SIZING.items():
        style_name = f"h_{name}"
        # 将 px 值转换回 Tailwind 单位 (除以 4)
        tw_units = px_value / 4 if px_value != 0 else 0
        lines.append(f'{style_name} = size_meta(height={tw_units})')

    # =========================================================================
    # Typography (font size) tokens
    # =========================================================================
    lines.extend([
        '',
        '',
        '# =============================================================================',
        '# Typography - 字体大小',
        '# =============================================================================',
        '',
    ])

    for name in FONT_SIZES.keys():
        style_name = f"text_{name}"
        # Map to font("xs"), font("sm"), etc.
        lines.append(f'{style_name} = font_size("{name}")')

    # =========================================================================
    # Space Y / Space X callable tokens (返回函数而非 context)
    # =========================================================================
    lines.extend([
        '',
        '',
        '# =============================================================================',
        '# Vertical/Horizontal Spacing Functions',
        '# 用法: tw.space_y_4() 添加垂直间距',
        '# =============================================================================',
        '',
    ])

    for name, px_value in SPACING.items():
        lines.append(f'def space_y_{name}(): _gap_y({px_value})')

    lines.append('')

    for name, px_value in SPACING.items():
        lines.append(f'def space_x_{name}(): _gap_x({px_value})')

    # =========================================================================
    # Button presets
    # =========================================================================
    lines.extend([
        '',
        '',
        '# =============================================================================',
        '# Button Presets (三态按钮样式)',
        '# =============================================================================',
        '',
        '# 主要按钮 (蓝色)',
        'btn_primary = button_colors(BLUE_600, BLUE_500, BLUE_700) | text(WHITE)',
        'btn_blue = btn_primary',
        '',
        '# 次要按钮 (灰色)',
        'btn_secondary = button_colors(GRAY_700, GRAY_600, GRAY_800) | text(WHITE)',
        'btn_gray = btn_secondary',
        '',
        '# 成功按钮 (绿色)',
        'btn_success = button_colors(GREEN_600, GREEN_500, GREEN_700) | text(WHITE)',
        'btn_green = btn_success',
        '',
        '# 危险按钮 (红色)',
        'btn_danger = button_colors(RED_600, RED_500, RED_700) | text(WHITE)',
        'btn_red = btn_danger',
        '',
        '# 警告按钮 (橙色)',
        'btn_warning = button_colors(AMBER_600, AMBER_500, AMBER_700) | text(WHITE)',
        'btn_amber = btn_warning',
        '',
        '# Ghost 按钮 (透明背景)',
        'btn_ghost = button_colors(TRANSPARENT, GRAY_800, GRAY_700) | text(GRAY_300)',
        '',
        '# Slate 系列按钮',
        'btn_slate = button_colors(SLATE_700, SLATE_600, SLATE_800) | text(WHITE)',
        '',
        '# Zinc 系列按钮 (中性)',
        'btn_zinc = button_colors(ZINC_700, ZINC_600, ZINC_800) | text(WHITE)',
        '',
        '# === 主题色按钮 (暗黑2 + 紫水晶风格, 与 stoneshard_asset_browser 一致) ===',
        '',
        '# 紫水晶按钮 (主强调色)',
        'btn_crystal = button_colors(CRYSTAL_500, CRYSTAL_400, CRYSTAL_600) | text(PARCHMENT_50)',
        '',
        '# 金边按钮 (暗黑2经典)',
        'btn_goldrim = button_colors(GOLDRIM_500, GOLDRIM_400, GOLDRIM_600) | text(ABYSS_900)',
        '',
        '# 深渊按钮 (暗色背景)',
        'btn_abyss = button_colors(ABYSS_700, ABYSS_800, ABYSS_900) | text(PARCHMENT_100)',
    ])

    # =========================================================================
    # Semantic aliases
    # =========================================================================
    lines.extend([
        '',
        '',
        '# =============================================================================',
        '# Semantic Aliases',
        '# =============================================================================',
        '',
        '# --- Text Hierarchy (内容层级, 从亮到暗) ---',
        '# text_bright  → 最亮, 选中/活跃状态',
        '# text_default → 主阅读文字',
        '# text_muted   → 次要内容, 标签',
        '# text_subtle  → 图标, 提示, 占位符',
        '# text_faint   → 最暗, 禁用/装饰',
        'text_bright = text_parchment_50',
        'text_default = text_parchment_100',
        'text_muted = text_parchment_300',
        'text_subtle = text_parchment_500',
        'text_faint = text_parchment_600',
        '',
        '# --- Accent Text (强调色文字) ---',
        'text_accent = text_crystal_400',
        'text_accent_muted = text_crystal_300',
        'text_gold = text_goldrim_400',
        '',
        '# --- Status Text (语义状态) ---',
        'text_success = text_green_500',
        'text_warning = text_goldrim_400',
        'text_danger = text_blood_400',
        'text_error = text_blood_400',
        'text_info = text_blue_500',
        '',
        '# --- Status Backgrounds ---',
        'bg_success = bg_green_600',
        'bg_warning = bg_goldrim_600',
        'bg_danger = bg_blood_600',
        'bg_error = bg_blood_600',
        'bg_info = bg_blue_600',
        '',
        '# --- Primary/Secondary (主题色) ---',
        '# primary = crystal (紫水晶), secondary = abyss (深渊)',
        'bg_primary = bg_crystal_600',
        'bg_secondary = bg_abyss_800',
        '',
        '# 重定义 btn_primary/secondary 使用主题色',
        'btn_primary = btn_crystal',
        'btn_secondary = btn_abyss',
        '',
        '# Common combinations',
        'no_rounding = rounded_none',
        'p_none = p_0',
        'gap_none = gap_0',
        '',
    ])

    # =========================================================================
    # Semantic Layer Tokens (语义层 - 抽象 UI 概念)
    # =========================================================================
    lines.extend([
        '',
        '# =============================================================================',
        '# Semantic Layer Tokens - UI 层级系统',
        '# =============================================================================',
        '# 从深到浅: bg_app → bg_surface → bg_elevated → bg_overlay',
        '# 输入框: bg_input (略亮于 bg_elevated, 让控件可辨识)',
        '',
        '# 应用层 - 最深的背景，用于窗口底层',
        'bg_app = bg_abyss_900',
        '',
        '# 表面层 - 卡片、面板的背景',
        'bg_surface = bg_abyss_800',
        '',
        '# 浮层 - 弹窗、下拉菜单、tooltip',
        'bg_elevated = bg_abyss_700',
        '',
        '# 输入层 - 输入框、选择框的背景',
        'bg_input = bg_abyss_600',
        '',
        '# 遮罩层 - 模态框背景遮罩',
        'bg_overlay = alpha(0.7) | bg_black',
        '',
        '',
        '# =============================================================================',
        '# Semantic Border Tokens - 语义边框',
        '# =============================================================================',
        '',
        '# 微妙边框 - 几乎不可见，用于分隔区域',
        'border_subtle = border_abyss_700',
        '',
        '# 默认边框 - 标准可见边框',
        'border_default = border_stone_700',
        '',
        '# 强调边框 - 明显的边框，用于焦点/选中状态',
        'border_strong = border_stone_600',
        '',
        '# 交互边框 - 用于 hover/focus 状态',
        'border_interactive = border_crystal_500',
        '',
        '',
        '# =============================================================================',
        '# Component Presets - 预组合组件样式',
        '# =============================================================================',
        '# 常用 UI 组件的预设样式，可直接使用或作为基础扩展',
        '',
        '# 按钮尺寸预设 - 用于 imgui.button()',
        '# 用法: (tw.btn_primary | tw.btn_md)(imgui.button)("确定")',
        'btn_xs = size_meta(width=24, height=7)   # 96px × 28px',
        'btn_sm = size_meta(width=32, height=8)   # 128px × 32px',
        'btn_md = size_meta(width=40, height=9)   # 160px × 36px',
        'btn_lg = size_meta(width=48, height=10)  # 192px × 40px',
        'btn_xl = size_meta(width=56, height=11)  # 224px × 44px',
        '',
        '# 卡片 - 用于 ly.card() 的默认样式',
        'card_default = bg_abyss_800 | rounded_lg | p_3 | child_rounded_lg',
        '',
        '# 面板 - 用于侧边栏、工具栏等',
        'panel_default = bg_abyss_900 | rounded_md | p_2',
        '',
        '# 输入框 - 用于 input_text 等输入控件',
        'input_default = frame_bg_abyss_700 | rounded | border_stone_700 | frame_border_size(1)',
        '',
        '# 选中状态 - 用于列表项选中',
        'selected_default = bg_abyss_600',
        '',
        '# Hover 状态 - 用于列表项 hover',
        'hover_default = bg_abyss_700',
        '',
    ])

    return '\n'.join(lines)


def main():
    # Generate and write tw.py directly to ui/
    output_file = Path(__file__).parent.parent / "ui" / "tw.py"
    content = generate_file()
    output_file.write_text(content, encoding="utf-8")

    # Count generated tokens
    color_count = sum(len(v) if isinstance(v, dict) else 1 for v in COLORS.values())
    text_tokens = color_count + 2  # +2 for black/white
    bg_tokens = color_count + 3    # +3 for black/white/transparent
    border_tokens = color_count + 3
    spacing_tokens = len(SPACING)
    gap_tokens = len(SPACING)
    width_tokens = len(SIZING)
    height_tokens = len(SIZING)
    space_y_tokens = len(SPACING)
    space_x_tokens = len(SPACING)
    font_tokens = len(FONT_SIZES)
    radius_tokens = len(BORDER_RADIUS)
    button_tokens = 8  # btn_primary, btn_secondary, etc.

    total = (text_tokens + bg_tokens + border_tokens +
             spacing_tokens + gap_tokens + width_tokens + height_tokens +
             space_y_tokens + space_x_tokens + font_tokens + radius_tokens + button_tokens)

    print(f"Generated {output_file}")
    print(f"  Text colors:    {text_tokens}")
    print(f"  BG colors:      {bg_tokens}")
    print(f"  Border colors:  {border_tokens}")
    print(f"  Padding (p_*):  {spacing_tokens}")
    print(f"  Gap (gap_*):    {gap_tokens}")
    print(f"  Width (w_*):    {width_tokens}")
    print(f"  Height (h_*):   {height_tokens}")
    print(f"  Space Y/X:      {space_y_tokens + space_x_tokens}")
    print(f"  Typography:     {font_tokens}")
    print(f"  Border radius:  {radius_tokens}")
    print(f"  Buttons:        {button_tokens}")
    print(f"  Total tokens:   ~{total}")


if __name__ == "__main__":
    main()
