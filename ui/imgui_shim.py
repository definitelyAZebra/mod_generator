# -*- coding: utf-8 -*-
"""pyimgui → cimgui_py 兼容垫片层 (shim)

本模块让现有 `import imgui` 代码无需修改即可运行在 cimgui_py 上。
使用方式: `from ui import imgui_shim as imgui`

桥接的差异:
  1. 常量名: COLOR_TEXT 等 pyimgui 风格别名
  2. push_style_color: (idx, r, g, b, a) → (idx, (r,g,b,a)) 打包
  3. vararg 函数: text, text_colored, text_wrapped, text_disabled, set_tooltip
  4. begin_child: pyimgui (label, w, h, border=) → cimgui_py (label, (w,h), child_flags)
  5. ImVec2 参数拆分: button(label, w, h) → button(label, (w,h))
  6. 名称差异: get_content_region_available → get_content_region_avail

不再需要桥接的 (由 binding 直接处理):
  - Vec2/Vec4 namedtuple 返回值 (.x/.y 属性)
  - push_style_var 多分派 (binding 内置 by_type dispatch)
  - push_style_color(idx, u32/tuple) 多分派
  - _GuiStyle vec2 属性 (binding 直接返回 Vec2)
  - begin/end tuple 解包 (binding 支持 __iter__)
  - push_font (不需要兼容旧签名)
"""

from __future__ import annotations

from typing import Any

import cimgui_py as _cimgui
from cimgui_py import core as _core
from cimgui_py import backend as _backend

# Re-export Vec2/Vec4 from binding (namedtuple, is-a tuple, has .x/.y)
from cimgui_py import Vec2 as Vec2, Vec4 as Vec4  # explicit re-export


# =============================================================================
# 常量映射: pyimgui SCREAMING_SNAKE → cimgui_py enums
# =============================================================================

# ── Col (ImGuiCol_) ──────────────────────────────────────────────────────────

COLOR_TEXT = _cimgui.Col.Text
COLOR_TEXT_DISABLED = _cimgui.Col.TextDisabled
COLOR_WINDOW_BACKGROUND = _cimgui.Col.WindowBg
COLOR_CHILD_BACKGROUND = _cimgui.Col.ChildBg
COLOR_POPUP_BACKGROUND = _cimgui.Col.PopupBg
COLOR_BORDER = _cimgui.Col.Border
COLOR_BORDER_SHADOW = _cimgui.Col.BorderShadow
COLOR_FRAME_BACKGROUND = _cimgui.Col.FrameBg
COLOR_FRAME_BACKGROUND_HOVERED = _cimgui.Col.FrameBgHovered
COLOR_FRAME_BACKGROUND_ACTIVE = _cimgui.Col.FrameBgActive
COLOR_TITLE_BACKGROUND = _cimgui.Col.TitleBg
COLOR_TITLE_BACKGROUND_ACTIVE = _cimgui.Col.TitleBgActive
COLOR_TITLE_BACKGROUND_COLLAPSED = _cimgui.Col.TitleBgCollapsed
COLOR_MENUBAR_BACKGROUND = _cimgui.Col.MenuBarBg
COLOR_SCROLLBAR_BACKGROUND = _cimgui.Col.ScrollbarBg
COLOR_SCROLLBAR_GRAB = _cimgui.Col.ScrollbarGrab
COLOR_SCROLLBAR_GRAB_HOVERED = _cimgui.Col.ScrollbarGrabHovered
COLOR_SCROLLBAR_GRAB_ACTIVE = _cimgui.Col.ScrollbarGrabActive
COLOR_CHECK_MARK = _cimgui.Col.CheckMark
COLOR_SLIDER_GRAB = _cimgui.Col.SliderGrab
COLOR_SLIDER_GRAB_ACTIVE = _cimgui.Col.SliderGrabActive
COLOR_BUTTON = _cimgui.Col.Button
COLOR_BUTTON_HOVERED = _cimgui.Col.ButtonHovered
COLOR_BUTTON_ACTIVE = _cimgui.Col.ButtonActive
COLOR_HEADER = _cimgui.Col.Header
COLOR_HEADER_HOVERED = _cimgui.Col.HeaderHovered
COLOR_HEADER_ACTIVE = _cimgui.Col.HeaderActive
COLOR_SEPARATOR = _cimgui.Col.Separator
COLOR_SEPARATOR_HOVERED = _cimgui.Col.SeparatorHovered
COLOR_SEPARATOR_ACTIVE = _cimgui.Col.SeparatorActive
COLOR_RESIZE_GRIP = _cimgui.Col.ResizeGrip
COLOR_RESIZE_GRIP_HOVERED = _cimgui.Col.ResizeGripHovered
COLOR_RESIZE_GRIP_ACTIVE = _cimgui.Col.ResizeGripActive
COLOR_TAB = _cimgui.Col.Tab
COLOR_TAB_HOVERED = _cimgui.Col.TabHovered
COLOR_TAB_ACTIVE = _cimgui.Col.TabSelected          # pyimgui name → 1.92 renamed
COLOR_TAB_UNFOCUSED = _cimgui.Col.TabDimmed          # pyimgui name → 1.92 renamed
COLOR_TAB_UNFOCUSED_ACTIVE = _cimgui.Col.TabDimmedSelected  # pyimgui name → 1.92 renamed
COLOR_PLOT_LINES = _cimgui.Col.PlotLines
COLOR_PLOT_LINES_HOVERED = _cimgui.Col.PlotLinesHovered
COLOR_PLOT_HISTOGRAM = _cimgui.Col.PlotHistogram
COLOR_PLOT_HISTOGRAM_HOVERED = _cimgui.Col.PlotHistogramHovered
COLOR_TABLE_HEADER_BACKGROUND = _cimgui.Col.TableHeaderBg
COLOR_TABLE_BORDER_STRONG = _cimgui.Col.TableBorderStrong
COLOR_TABLE_BORDER_LIGHT = _cimgui.Col.TableBorderLight
COLOR_TABLE_ROW_BACKGROUND = _cimgui.Col.TableRowBg
COLOR_TABLE_ROW_BACKGROUND_ALT = _cimgui.Col.TableRowBgAlt
COLOR_TEXT_SELECTED_BACKGROUND = _cimgui.Col.TextSelectedBg
COLOR_DRAG_DROP_TARGET = _cimgui.Col.DragDropTarget
COLOR_NAV_HIGHLIGHT = _cimgui.Col.NavCursor           # pyimgui name → 1.92 renamed
COLOR_NAV_WINDOWING_HIGHLIGHT = _cimgui.Col.NavWindowingHighlight
COLOR_NAV_WINDOWING_DIM_BACKGROUND = _cimgui.Col.NavWindowingDimBg
COLOR_MODAL_WINDOW_DIM_BACKGROUND = _cimgui.Col.ModalWindowDimBg

# ── StyleVar (ImGuiStyleVar_) ────────────────────────────────────────────────

STYLE_ALPHA = _cimgui.StyleVar.Alpha
STYLE_DISABLED_ALPHA = _cimgui.StyleVar.DisabledAlpha
STYLE_WINDOW_PADDING = _cimgui.StyleVar.WindowPadding
STYLE_WINDOW_ROUNDING = _cimgui.StyleVar.WindowRounding
STYLE_WINDOW_BORDERSIZE = _cimgui.StyleVar.WindowBorderSize
STYLE_WINDOW_MIN_SIZE = _cimgui.StyleVar.WindowMinSize
STYLE_WINDOW_TITLE_ALIGN = _cimgui.StyleVar.WindowTitleAlign
STYLE_CHILD_ROUNDING = _cimgui.StyleVar.ChildRounding
STYLE_CHILD_BORDERSIZE = _cimgui.StyleVar.ChildBorderSize
STYLE_POPUP_ROUNDING = _cimgui.StyleVar.PopupRounding
STYLE_POPUP_BORDERSIZE = _cimgui.StyleVar.PopupBorderSize
STYLE_FRAME_PADDING = _cimgui.StyleVar.FramePadding
STYLE_FRAME_ROUNDING = _cimgui.StyleVar.FrameRounding
STYLE_FRAME_BORDERSIZE = _cimgui.StyleVar.FrameBorderSize
STYLE_ITEM_SPACING = _cimgui.StyleVar.ItemSpacing
STYLE_ITEM_INNER_SPACING = _cimgui.StyleVar.ItemInnerSpacing
STYLE_INDENT_SPACING = _cimgui.StyleVar.IndentSpacing
STYLE_CELL_PADDING = _cimgui.StyleVar.CellPadding
STYLE_SCROLLBAR_SIZE = _cimgui.StyleVar.ScrollbarSize
STYLE_SCROLLBAR_ROUNDING = _cimgui.StyleVar.ScrollbarRounding
STYLE_GRAB_MIN_SIZE = _cimgui.StyleVar.GrabMinSize
STYLE_GRAB_ROUNDING = _cimgui.StyleVar.GrabRounding
STYLE_TAB_ROUNDING = _cimgui.StyleVar.TabRounding
STYLE_TAB_BORDERSIZE = _cimgui.StyleVar.TabBorderSize
STYLE_BUTTON_TEXT_ALIGN = _cimgui.StyleVar.ButtonTextAlign
STYLE_SELECTABLE_TEXT_ALIGN = _cimgui.StyleVar.SelectableTextAlign

# ── WindowFlags ──────────────────────────────────────────────────────────────

WINDOW_NONE = 0
WINDOW_NO_TITLE_BAR = _cimgui.WindowFlags.NoTitleBar
WINDOW_NO_RESIZE = _cimgui.WindowFlags.NoResize
WINDOW_NO_MOVE = _cimgui.WindowFlags.NoMove
WINDOW_NO_SCROLLBAR = _cimgui.WindowFlags.NoScrollbar
WINDOW_NO_SCROLL_WITH_MOUSE = _cimgui.WindowFlags.NoScrollWithMouse
WINDOW_NO_COLLAPSE = _cimgui.WindowFlags.NoCollapse
WINDOW_ALWAYS_AUTO_RESIZE = _cimgui.WindowFlags.AlwaysAutoResize
WINDOW_NO_BACKGROUND = _cimgui.WindowFlags.NoBackground
WINDOW_NO_SAVED_SETTINGS = _cimgui.WindowFlags.NoSavedSettings
WINDOW_MENU_BAR = _cimgui.WindowFlags.MenuBar
WINDOW_HORIZONTAL_SCROLLBAR = _cimgui.WindowFlags.HorizontalScrollbar
WINDOW_NO_FOCUS_ON_APPEARING = _cimgui.WindowFlags.NoFocusOnAppearing
WINDOW_NO_BRING_TO_FRONT_ON_FOCUS = _cimgui.WindowFlags.NoBringToFrontOnFocus
WINDOW_ALWAYS_VERTICAL_SCROLLBAR = _cimgui.WindowFlags.AlwaysVerticalScrollbar
WINDOW_ALWAYS_HORIZONTAL_SCROLLBAR = _cimgui.WindowFlags.AlwaysHorizontalScrollbar
WINDOW_NO_NAV_INPUTS = _cimgui.WindowFlags.NoNavInputs
WINDOW_NO_NAV_FOCUS = _cimgui.WindowFlags.NoNavFocus
WINDOW_NO_NAV = _cimgui.WindowFlags.NoNav
WINDOW_NO_DECORATION = _cimgui.WindowFlags.NoDecoration
WINDOW_NO_INPUTS = _cimgui.WindowFlags.NoInputs

# ── TableFlags ───────────────────────────────────────────────────────────────

TABLE_BORDERS_INNER = _cimgui.TableFlags.BordersInner
TABLE_BORDERS_OUTER = _cimgui.TableFlags.BordersOuter
TABLE_BORDERS = _cimgui.TableFlags.BordersInner | _cimgui.TableFlags.BordersOuter
TABLE_ROW_BACKGROUND = _cimgui.TableFlags.RowBg
TABLE_SIZING_STRETCH_SAME = _cimgui.TableFlags.SizingStretchSame
TABLE_SIZING_FIXED_FIT = _cimgui.TableFlags.SizingFixedFit
TABLE_NO_BORDERS_IN_BODY = _cimgui.TableFlags.NoBordersInBody

# ── TableColumnFlags ─────────────────────────────────────────────────────────

TABLE_COLUMN_WIDTH_FIXED = _cimgui.TableColumnFlags.WidthFixed

# ── TreeNodeFlags ────────────────────────────────────────────────────────────

TREE_NODE_DEFAULT_OPEN = _cimgui.TreeNodeFlags.DefaultOpen
TREE_NODE_FRAMED = _cimgui.TreeNodeFlags.Framed
TREE_NODE_LEAF = _cimgui.TreeNodeFlags.Leaf
TREE_NODE_OPEN_ON_ARROW = _cimgui.TreeNodeFlags.OpenOnArrow
TREE_NODE_OPEN_ON_DOUBLE_CLICK = _cimgui.TreeNodeFlags.OpenOnDoubleClick
TREE_NODE_SPAN_AVAILABLE_WIDTH = _cimgui.TreeNodeFlags.SpanAvailWidth
TREE_NODE_SPAN_FULL_WIDTH = _cimgui.TreeNodeFlags.SpanFullWidth

# ── InputTextFlags ───────────────────────────────────────────────────────────

INPUT_TEXT_CHARS_DECIMAL = _cimgui.InputTextFlags.CharsDecimal
INPUT_TEXT_ENTER_RETURNS_TRUE = _cimgui.InputTextFlags.EnterReturnsTrue
INPUT_TEXT_READ_ONLY = _cimgui.InputTextFlags.ReadOnly
INPUT_TEXT_ALLOW_TAB_INPUT = _cimgui.InputTextFlags.AllowTabInput
INPUT_TEXT_NO_HORIZONTAL_SCROLL = _cimgui.InputTextFlags.NoHorizontalScroll

# ── SelectableFlags ──────────────────────────────────────────────────────────

SELECTABLE_NONE = 0
SELECTABLE_DONT_CLOSE_POPUPS = _cimgui.SelectableFlags.NoAutoClosePopups
SELECTABLE_SPAN_ALL_COLUMNS = _cimgui.SelectableFlags.SpanAllColumns

# ── HoveredFlags ─────────────────────────────────────────────────────────────

HOVERED_NONE = 0
HOVERED_ALLOW_WHEN_BLOCKED_BY_POPUP = _cimgui.HoveredFlags.AllowWhenBlockedByPopup
HOVERED_ALLOW_WHEN_BLOCKED_BY_ACTIVE_ITEM = _cimgui.HoveredFlags.AllowWhenBlockedByActiveItem
HOVERED_ALLOW_WHEN_DISABLED = _cimgui.HoveredFlags.AllowWhenDisabled

# ── PopupFlags ───────────────────────────────────────────────────────────────

POPUP_NONE = 0
POPUP_MOUSE_BUTTON_RIGHT = _cimgui.PopupFlags.MouseButtonRight

# ── MouseButton ──────────────────────────────────────────────────────────────

MOUSE_BUTTON_LEFT = _cimgui.MouseButton.Left
MOUSE_BUTTON_RIGHT = _cimgui.MouseButton.Right
MOUSE_BUTTON_MIDDLE = _cimgui.MouseButton.Middle

# ── MouseCursor ───────────────────────────────────────────────────────────────

MOUSE_CURSOR_HAND = _cimgui.MouseCursor.Hand
MOUSE_CURSOR_ARROW = _cimgui.MouseCursor.Arrow

# ── Cond ─────────────────────────────────────────────────────────────────────

ALWAYS = _cimgui.Cond.Always
ONCE = _cimgui.Cond.Once
FIRST_USE_EVER = _cimgui.Cond.FirstUseEver
APPEARING = _cimgui.Cond.Appearing

# ── FocusedFlags ─────────────────────────────────────────────────────────────

FOCUSED_CHILD_WINDOWS = _cimgui.FocusedFlags.ChildWindows

# ── TabBarFlags ──────────────────────────────────────────────────────────────

TAB_BAR_NONE = 0
TAB_BAR_REORDERABLE = _cimgui.TabBarFlags.Reorderable

# ── TabItemFlags ─────────────────────────────────────────────────────────────

TAB_ITEM_NONE = 0

# ── DrawFlags ────────────────────────────────────────────────────────────────

# (DrawList flags — different from DrawFlags)
DRAW_ROUND_CORNERS_ALL = _cimgui.DrawFlags.RoundCornersAll


# =============================================================================
# 函数包装 — 仅处理 pyimgui 签名差异
# =============================================================================

# ── push_style_color: pyimgui (idx, r, g, b, a) → cimgui_py (idx, (r,g,b,a)) ─

def push_style_color(idx: int, *args: Any) -> None:
    """兼容 pyimgui 的 push_style_color(idx, r, g, b, a)。

    也支持: push_style_color(idx, u32) 和 push_style_color(idx, (r,g,b,a))
    binding 的 by_type dispatcher 自动区分 u32 vs tuple。
    """
    if len(args) == 4:
        # pyimgui style: (idx, r, g, b, a) → pack to tuple for Vec4 dispatch
        _cimgui.push_style_color(idx, (args[0], args[1], args[2], args[3]))
    elif len(args) == 1:
        # u32 or tuple — dispatcher handles it
        _cimgui.push_style_color(idx, args[0])
    else:
        raise TypeError(
            f"push_style_color expects (idx, r, g, b, a) or (idx, color), got {1 + len(args)} args"
        )


# ── push_style_var / pop_style_var: binding dispatcher handles float vs vec2 ─

push_style_var = _cimgui.push_style_var
pop_style_var = _cimgui.pop_style_var
pop_style_color = _cimgui.pop_style_color


# ── text / text_colored / text_wrapped / text_disabled (vararg wrappers) ─────

def text(msg: str) -> None:
    """pyimgui.text(msg) → text_unformatted(msg)"""
    _cimgui.text_unformatted(str(msg))


def text_colored(msg: str, r: float, g: float, b: float, a: float = 1.0) -> None:
    """pyimgui.text_colored(msg, r, g, b, a)"""
    _cimgui.push_style_color(_cimgui.Col.Text, (r, g, b, a))
    _cimgui.text_unformatted(str(msg))
    _cimgui.pop_style_color(1)


def text_wrapped(msg: str) -> None:
    """pyimgui.text_wrapped(msg)"""
    _cimgui.push_text_wrap_pos(0.0)
    _cimgui.text_unformatted(str(msg))
    _cimgui.pop_text_wrap_pos()


def text_disabled(msg: str) -> None:
    """pyimgui.text_disabled(msg)"""
    style = _cimgui.get_style()
    _cimgui.push_style_color(_cimgui.Col.Text, (1.0, 1.0, 1.0, style.disabled_alpha))
    _cimgui.text_unformatted(str(msg))
    _cimgui.pop_style_color(1)


def set_tooltip(msg: str) -> None:
    """pyimgui.set_tooltip(msg) — vararg wrapper"""
    # ImGui 1.92 removed SetTooltip (vararg). Use BeginTooltip + Text instead.
    if _cimgui.begin_tooltip():
        _cimgui.text_unformatted(str(msg))
        _cimgui.end_tooltip()


def bullet_text(msg: str) -> None:
    """pyimgui.bullet_text(msg) — vararg wrapper"""
    _cimgui.bullet()
    _cimgui.same_line()
    _cimgui.text_unformatted(str(msg))


# ── begin_child: pyimgui (label, w, h, border=, flags=) compat ───────────────

def begin_child(
    label: str | int,
    width: float = 0,
    height: float = 0,
    border: bool = False,
    flags: int = 0,
    *,
    # cimgui_py native kwargs (for forward compat)
    size: tuple[float, float] | None = None,
    child_flags: int = 0,
    window_flags: int = 0,
) -> bool:
    """兼容 pyimgui 的 begin_child 调用方式。

    pyimgui: begin_child("id", width=200, height=100, border=True, flags=WINDOW_NO_SCROLLBAR)
    cimgui_py: begin_child("id", (200, 100), ChildFlags.Borders, WindowFlags.NoScrollbar)
    """
    if size is not None:
        # Native cimgui_py call style
        sz = size
    else:
        sz = (width, height)

    cf = child_flags
    if border:
        cf |= int(_cimgui.ChildFlags.Borders)

    wf = window_flags or flags

    return _cimgui.begin_child(label, sz, cf, wf)


# ── begin/end: cimgui_py 支持 tuple 解包和 context manager，直接透传 ────────
# pyimgui: expanded, opened = imgui.begin("name", closable=True)
# cimgui_py: expanded, opened = imgui.begin("name", p_open=True)  # __iter__ 支持

begin = _cimgui.begin
end = _cimgui.end


# ── dummy: pyimgui (w, h) → cimgui_py ((w, h)) ──────────────────────────────

def dummy(width: float, height: float) -> None:
    """pyimgui.dummy(w, h) → cimgui_py.dummy((w, h))"""
    _cimgui.dummy((width, height))


# ── button: pyimgui button(label, width=0, height=0) compat ──────────────────

def button(label: str, width: float = 0, height: float = 0) -> bool:
    """pyimgui.button(label, width=0, height=0)"""
    return _cimgui.button(label, (width, height))


# ── selectable: pyimgui selectable(label, selected, flags, width, height) ─────

def selectable(
    label: str,
    selected: bool = False,
    flags: int = 0,
    width: float = 0,
    height: float = 0,
) -> tuple[bool, bool]:
    """pyimgui returns (clicked, selected)."""
    return _cimgui.selectable(label, selected, flags, (width, height))


# ── invisible_button: pyimgui (label, w, h) → cimgui_py (label, (w,h)) ──────

def invisible_button(str_id: str, width: float, height: float, flags: int = 0) -> bool:
    """pyimgui.invisible_button(label, width, height)"""
    return _cimgui.invisible_button(str_id, (width, height), flags)


# ── get_color_u32_rgba: pyimgui convenience → cimgui_py get_color_u32 ────────

def get_color_u32_rgba(r: float, g: float, b: float, a: float = 1.0) -> int:
    """pyimgui.get_color_u32_rgba(r, g, b, a) → get_color_u32((r,g,b,a))"""
    return _cimgui.get_color_u32((r, g, b, a))


# ── set_next_window_size: pyimgui (w, h, cond) ──────────────────────────────

def set_next_window_size(width: float, height: float, condition: int = 0) -> None:
    _cimgui.set_next_window_size((width, height), condition)


def set_next_window_pos(x: float, y: float, condition: int = 0, pivot_x: float = 0, pivot_y: float = 0) -> None:
    _cimgui.set_next_window_pos((x, y), condition, (pivot_x, pivot_y))


# pyimgui alias
set_next_window_position = set_next_window_pos


def set_next_window_size_constraints(
    min_width: float, min_height: float,
    max_width: float, max_height: float,
) -> None:
    _cimgui.set_next_window_size_constraints((min_width, min_height), (max_width, max_height))


def set_next_window_content_size(width: float, height: float) -> None:
    _cimgui.set_next_window_content_size((width, height))


# ── pyimgui 名称差异 ─────────────────────────────────────────────────────────

def get_content_region_available():
    """pyimgui name → cimgui_py get_content_region_avail"""
    return _cimgui.get_content_region_avail()


# ── image_button: pyimgui (tex_id, w, h, **kw) → cimgui_py (str_id, tex_ref, size, ...) ─

def image_button(texture_id: Any, width: float, height: float, *,
                 uv0: tuple[float, float] = (0, 0), uv1: tuple[float, float] = (1, 1), frame_padding: int = -1,
                 tint_color: tuple[float, float, float, float] = (1, 1, 1, 1), border_color: tuple[float, float, float, float] = (0, 0, 0, 0)) -> bool:
    """pyimgui compat: image_button(tex_id, w, h, ...) → ImageButton(str_id, tex_ref, size, ...)

    NOTE: frame_padding is ignored in ImGui 1.92+ (use style push instead).
    """
    str_id = f"##imgbtn_{texture_id}"
    tex_ref = (None, int(texture_id))
    return _cimgui.image_button(str_id, tex_ref, (width, height),
                                uv0=uv0, uv1=uv1,
                                bg_col=border_color, tint_col=tint_color)


def get_content_region_available_width() -> float:
    return _cimgui.get_content_region_avail()[0]


# pyimgui name aliases
get_window_position = _cimgui.get_window_pos  # pyimgui uses "position" suffix


def calc_text_size(text_str: str, hide_text_after_double_hash: bool = False, wrap_width: float = -1.0):
    """pyimgui: calc_text_size(text) → cimgui_py: calc_text_size(text, text_end, ...)"""
    return _cimgui.calc_text_size(text_str, None, hide_text_after_double_hash, wrap_width)


# ── Passthrough re-exports ───────────────────────────────────────────────────
# Functions with identical signatures — direct binding

# Window
end_child = _cimgui.end_child

# Style
get_style = _cimgui.get_style
get_io = _cimgui.get_io

# Layout
same_line = _cimgui.same_line
new_line = _cimgui.new_line
spacing = _cimgui.spacing
indent = _cimgui.indent
unindent = _cimgui.unindent
separator = _cimgui.separator
set_cursor_pos = _cimgui.set_cursor_pos

# Cursor
set_cursor_pos_x = _cimgui.set_cursor_pos_x
set_cursor_pos_y = _cimgui.set_cursor_pos_y
get_cursor_pos_x = _cimgui.get_cursor_pos_x
get_cursor_pos_y = _cimgui.get_cursor_pos_y
get_cursor_pos = _cimgui.get_cursor_pos
get_cursor_screen_pos = _cimgui.get_cursor_screen_pos
get_text_line_height = _cimgui.get_text_line_height
get_text_line_height_with_spacing = _cimgui.get_text_line_height_with_spacing
get_frame_height = _cimgui.get_frame_height
get_frame_height_with_spacing = _cimgui.get_frame_height_with_spacing
get_frame_count = _cimgui.get_frame_count

# Scroll
set_scroll_here_y = _cimgui.set_scroll_here_y
set_scroll_here_x = _cimgui.set_scroll_here_x
get_scroll_y = _cimgui.get_scroll_y
get_scroll_x = _cimgui.get_scroll_x
get_scroll_max_y = _cimgui.get_scroll_max_y
get_scroll_max_x = _cimgui.get_scroll_max_x
set_scroll_y = _cimgui.set_scroll_y
set_scroll_x = _cimgui.set_scroll_x

# Widgets
input_text = _cimgui.input_text


def input_text_multiline(label: str, value: str, buffer_size: int = 1024, *, width: float = 0.0, height: float = 0.0, size: tuple[float, float] | None = None, flags: int = 0, callback: Any = None) -> tuple[bool, str]:
    """pyimgui: separate width/height → cimgui_py: size=(w,h) tuple."""
    if size is None:
        size = (width, height)
    return _cimgui.input_text_multiline(label, value, buffer_size, size, flags, callback)
input_int = _cimgui.input_int
input_float = _cimgui.input_float
slider_int = _cimgui.slider_int
slider_float = _cimgui.slider_float
checkbox = _cimgui.checkbox
radio_button = _cimgui.radio_button
combo = _cimgui.combo
color_edit3 = _cimgui.color_edit3
color_edit4 = _cimgui.color_edit4
progress_bar = _cimgui.progress_bar
image = _cimgui.image

# Tree

def tree_node(label: str, flags: int = 0) -> bool:
    """pyimgui tree_node(label, flags=0) → dispatches to tree_node or tree_node_ex."""
    if flags:
        return _cimgui.tree_node_ex(label, flags)
    return _cimgui.tree_node(label)

tree_pop = _cimgui.tree_pop
collapsing_header = _cimgui.collapsing_header

# Table
begin_table = _cimgui.begin_table
end_table = _cimgui.end_table
table_next_row = _cimgui.table_next_row
table_next_column = _cimgui.table_next_column
table_set_column_index = _cimgui.table_set_column_index
table_setup_column = _cimgui.table_setup_column
table_headers_row = _cimgui.table_headers_row

# Tab bar
begin_tab_bar = _cimgui.begin_tab_bar
end_tab_bar = _cimgui.end_tab_bar
begin_tab_item = _cimgui.begin_tab_item
end_tab_item = _cimgui.end_tab_item

# Columns (legacy)

def columns(count: int = 1, identifier: str | None = None, border: bool = True) -> None:
    """pyimgui columns(count, id, border=) → cimgui_py columns(count, id_, borders=)."""
    _cimgui.columns(count, identifier or "", border)
next_column = _cimgui.next_column
get_column_width = _cimgui.get_column_width
set_column_width = _cimgui.set_column_width

# Group
begin_group = _cimgui.begin_group
end_group = _cimgui.end_group

# Popup
open_popup = _cimgui.open_popup
begin_popup = _cimgui.begin_popup
begin_popup_context_item = _cimgui.begin_popup_context_item
begin_popup_context_window = _cimgui.begin_popup_context_window
begin_popup_modal = _cimgui.begin_popup_modal
end_popup = _cimgui.end_popup
close_current_popup = _cimgui.close_current_popup
is_popup_open = _cimgui.is_popup_open

# Tooltip
begin_tooltip = _cimgui.begin_tooltip
end_tooltip = _cimgui.end_tooltip

# Combo
begin_combo = _cimgui.begin_combo
end_combo = _cimgui.end_combo

# Menu
begin_menu_bar = _cimgui.begin_menu_bar
end_menu_bar = _cimgui.end_menu_bar
begin_main_menu_bar = _cimgui.begin_main_menu_bar
end_main_menu_bar = _cimgui.end_main_menu_bar
begin_menu = _cimgui.begin_menu
end_menu = _cimgui.end_menu
menu_item = _cimgui.menu_item

# Item state
is_item_hovered = _cimgui.is_item_hovered
is_item_clicked = _cimgui.is_item_clicked
is_item_active = _cimgui.is_item_active
is_item_focused = _cimgui.is_item_focused
is_item_visible = _cimgui.is_item_visible
is_item_deactivated_after_edit = _cimgui.is_item_deactivated_after_edit

# Mouse
is_mouse_clicked = _cimgui.is_mouse_clicked
is_mouse_double_clicked = _cimgui.is_mouse_double_clicked
is_mouse_down = _cimgui.is_mouse_down
is_mouse_released = _cimgui.is_mouse_released
get_mouse_pos = _cimgui.get_mouse_pos
get_mouse_drag_delta = _cimgui.get_mouse_drag_delta

# Window queries
is_window_focused = _cimgui.is_window_focused
is_window_hovered = _cimgui.is_window_hovered
get_window_width = _cimgui.get_window_width
get_window_height = _cimgui.get_window_height
get_window_pos = _cimgui.get_window_pos
get_window_size = _cimgui.get_window_size

# Item geometry
get_item_rect_min = _cimgui.get_item_rect_min
get_item_rect_max = _cimgui.get_item_rect_max
get_item_rect_size = _cimgui.get_item_rect_size

# Misc
push_item_width = _cimgui.push_item_width
pop_item_width = _cimgui.pop_item_width
set_next_item_width = _cimgui.set_next_item_width
align_text_to_frame_padding = _cimgui.align_text_to_frame_padding
small_button = _cimgui.small_button
input_text_with_hint = _cimgui.input_text_with_hint
set_mouse_cursor = _cimgui.set_mouse_cursor
push_clip_rect = _cimgui.push_clip_rect
pop_clip_rect = _cimgui.pop_clip_rect
# set_tooltip: wrapper defined above (ImGui 1.92 removed SetTooltip vararg)
push_text_wrap_pos = _cimgui.push_text_wrap_pos
pop_text_wrap_pos = _cimgui.pop_text_wrap_pos
push_id = _cimgui.push_id
pop_id = _cimgui.pop_id
def push_font(font: Any, font_size_base_unscaled: float = 0.0) -> None:
    """push_font compat — ImGui 1.92 added font_size_base_unscaled param, default 0 = use font's own size."""
    _cimgui.push_font(font, font_size_base_unscaled)

pop_font = _cimgui.pop_font
get_font = _cimgui.get_font
get_font_size = _cimgui.get_font_size
text_unformatted = _cimgui.text_unformatted
color_convert_u32_to_float4 = _cimgui.color_convert_u32_to_float4

# DrawList compat wrapper — pyimgui uses separate x,y coords, cimgui_py uses tuples
class _DrawListCompat:
    """Wrap cimgui_py _DrawList to accept pyimgui-style separate x,y coordinate args."""
    __slots__ = ("_dl",)

    def __init__(self, dl: Any) -> None:
        self._dl = dl

    # ── add_line(x1, y1, x2, y2, col, thickness=1.0) ────────────────────
    def add_line(self, x1: float, y1: float, x2: float, y2: float, col: int, thickness: float = 1.0) -> None:
        self._dl.add_line((x1, y1), (x2, y2), col, thickness)

    # ── add_rect(x1, y1, x2, y2, col, rounding=0, flags=0, thickness=1.0) ──
    def add_rect(self, x1: float, y1: float, x2: float, y2: float, col: int, rounding: float = 0.0, flags: int = 0, thickness: float = 1.0) -> None:
        self._dl.add_rect((x1, y1), (x2, y2), col, rounding, flags, thickness)

    # ── add_rect_filled(x1, y1, x2, y2, col, rounding=0, flags=0) ───────
    def add_rect_filled(self, x1: float, y1: float, x2: float, y2: float, col: int, rounding: float = 0.0, flags: int = 0) -> None:
        self._dl.add_rect_filled((x1, y1), (x2, y2), col, rounding, flags)

    # ── add_text(x, y, col, text) ────────────────────────────────────────
    def add_text(self, x: float, y: float, col: int, text: str) -> None:
        self._dl.add_text((x, y), col, text)

    # ── add_image(tex_id, p_min, p_max, uv_min=(0,0), uv_max=(1,1), col=0xFFFFFFFF) ──
    def add_image(self, tex_id: Any, p_min: tuple[float, float], p_max: tuple[float, float], uv_min: tuple[float, float] = (0, 0), uv_max: tuple[float, float] = (1, 1), col: int = 0xFFFFFFFF) -> None:
        # pyimgui passes tex_id as int; cimgui_py expects (owner, tex_id) tuple
        if isinstance(tex_id, (tuple, list)):
            tex_ref = tex_id  # type: ignore[assignment]  # pyimgui compat
        else:
            tex_ref = (None, tex_id)
        self._dl.add_image(tex_ref, p_min, p_max, uv_min, uv_max, col)

    # ── path methods ─────────────────────────────────────────────────────
    def path_line_to(self, x: float, y: float) -> None:
        self._dl.path_line_to((x, y))

    def path_stroke(self, col: int, closed: bool = False, thickness: float = 1.0) -> None:
        self._dl.path_stroke(col, int(closed), thickness)

    def path_clear(self) -> None:
        self._dl.path_clear()

    # ── channels ─────────────────────────────────────────────────────────
    def channels_split(self, count: int) -> None:
        self._dl.channels_split(count)

    def channels_set_current(self, idx: int) -> None:
        self._dl.channels_set_current(idx)

    def channels_merge(self) -> None:
        self._dl.channels_merge()

    # ── clip rect ────────────────────────────────────────────────────────
    def push_clip_rect(self, x1: float, y1: float, x2: float, y2: float, intersect: bool = True) -> None:
        self._dl.push_clip_rect((x1, y1), (x2, y2), intersect)

    def pop_clip_rect(self) -> None:
        self._dl.pop_clip_rect()

    # Fallback for any other methods not wrapped
    def __getattr__(self, name: str) -> Any:
        return getattr(self._dl, name)


def get_window_draw_list() -> _DrawListCompat:
    return _DrawListCompat(_cimgui.get_window_draw_list())

def get_foreground_draw_list() -> _DrawListCompat:
    return _DrawListCompat(_cimgui.get_foreground_draw_list())

# Color utilities
get_color_u32 = _cimgui.get_color_u32
color_convert_float4_to_u32 = _cimgui.color_convert_float4_to_u32

# Window focus
set_window_focus = _cimgui.set_window_focus

# Keyboard
is_key_down = _cimgui.is_key_down
is_key_pressed = _cimgui.is_key_pressed
KEY_SPACE: Any = int(_cimgui.Key.Space)  # 524 in ImGui 1.92+ (was 32 in old pyimgui)

# Cursor (screen-space)
set_cursor_screen_pos = _cimgui.set_cursor_screen_pos

# Rendering / frame
new_frame = _cimgui.new_frame
render = _cimgui.render
get_draw_data = _cimgui.get_draw_data
create_context = _cimgui.create_context
destroy_context = _cimgui.destroy_context
get_current_context = _cimgui.get_current_context

# Clipboard
get_clipboard_text = _cimgui.get_clipboard_text
set_clipboard_text = _cimgui.set_clipboard_text

# Drag/drop
begin_drag_drop_source = _cimgui.begin_drag_drop_source
end_drag_drop_source = _cimgui.end_drag_drop_source
begin_drag_drop_target = _cimgui.begin_drag_drop_target
end_drag_drop_target = _cimgui.end_drag_drop_target

# ID
get_id = _cimgui.get_id

# ── Enum re-exports ──────────────────────────────────────────────────────────

Col = _cimgui.Col
StyleVar = _cimgui.StyleVar
WindowFlags = _cimgui.WindowFlags
ChildFlags = _cimgui.ChildFlags
TableFlags = _cimgui.TableFlags
TableColumnFlags = _cimgui.TableColumnFlags
TreeNodeFlags = _cimgui.TreeNodeFlags
InputTextFlags = _cimgui.InputTextFlags
SelectableFlags = _cimgui.SelectableFlags
HoveredFlags = _cimgui.HoveredFlags
FocusedFlags = _cimgui.FocusedFlags
PopupFlags = _cimgui.PopupFlags
TabBarFlags = _cimgui.TabBarFlags
TabItemFlags = _cimgui.TabItemFlags
MouseButton = _cimgui.MouseButton
Cond = _cimgui.Cond
DrawFlags = _cimgui.DrawFlags
ColorEditFlags = _cimgui.ColorEditFlags
ComboFlags = _cimgui.ComboFlags
SliderFlags = _cimgui.SliderFlags
ConfigFlags = _cimgui.ConfigFlags
BackendFlags = _cimgui.BackendFlags


# =============================================================================
# pyimgui compat: imgui.core.FontConfig
# =============================================================================


class FontConfig:
    """pyimgui-compatible FontConfig wrapper.

    Keyword args map to _FontConfig properties. The underlying cimgui_py
    _FontConfig is created on construction and exposed as .handle.
    """

    def __init__(
        self,
        *,
        merge_mode: bool = False,
        glyph_offset_y: float = 0.0,
        glyph_offset_x: float = 0.0,
        pixel_snap_h: bool = False,
        glyph_min_advance_x: float = 0.0,
        glyph_max_advance_x: float = float("inf"),
    ):
        fc: Any = _core._FontConfig.im_font_config()  # type: ignore[arg-type]
        fc.merge_mode = merge_mode
        fc.glyph_offset = (glyph_offset_x, glyph_offset_y)
        fc.pixel_snap_h = pixel_snap_h
        if glyph_min_advance_x:
            fc.glyph_min_advance_x = glyph_min_advance_x
        if glyph_max_advance_x != float("inf"):
            fc.glyph_max_advance_x = glyph_max_advance_x
        self.handle: Any = fc


class _CoreCompat:
    """Namespace emulating ``imgui.core`` for font-related APIs."""
    FontConfig = FontConfig


core = _CoreCompat()


# =============================================================================
# pyimgui compat: GlfwRenderer replacement
# =============================================================================
# mod_generator.py uses:
#   from imgui.integrations.glfw import GlfwRenderer
#   renderer = GlfwRenderer(window)
#   renderer.process_inputs()
#   renderer.render(draw_data)
#   renderer.refresh_font_texture()
#   renderer.shutdown()


class GlfwRenderer:
    """Drop-in replacement for pyimgui's GlfwRenderer using cimgui_py backend."""

    def __init__(self, window: Any):
        _backend.glfw_init_for_opengl(window, True)
        _backend.opengl3_init("#version 330")
        self._window = window

    def process_inputs(self) -> None:
        """Begin a new backend frame (replaces pyimgui process_inputs)."""
        _backend.opengl3_new_frame()
        _backend.glfw_new_frame()

    def render(self, draw_data: Any) -> None:
        """Render ImGui draw data via OpenGL3 backend."""
        _backend.opengl3_render_draw_data(draw_data)

    def refresh_font_texture(self) -> None:
        """Rebuild font atlas texture (called after loading/changing fonts).

        In cimgui_py 1.92+, the backend auto-manages font textures via
        opengl3_update_texture. This is a no-op kept for API compat.
        """
        # ImGui 1.92 multi-texture model: backend.opengl3_new_frame() calls
        # UpdateTexture internally when the atlas is dirty. No manual upload needed.
        pass

    def shutdown(self) -> None:
        """Shutdown backend."""
        _backend.opengl3_shutdown()
        _backend.glfw_shutdown()
