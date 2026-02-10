# -*- coding: utf-8 -*-
"""声明式表单字段组件

提供两种布局容器 + 标准字段函数，消除表单布局样板代码。
每个字段渲染为: 标签 (上方, muted) + 控件 (下方)。

================================================================================
布局容器
================================================================================

field_row(N)    等宽 N 列网格 — 所有列固定宽度
field_flow()    自然宽度流式布局 — 每个字段指定自己的宽度，自动换行

================================================================================
设计原则
================================================================================

1. 通用原子 — 不编码任何 UX 意见
2. ImGui 风格返回值 — (changed, new_value)
3. 与 tw/ly 系统兼容
4. 不创建 ImGui 窗口/子窗口，纯 cursor 定位
5. field_flow 中字段保持自然宽度，不强制拉伸

⚠️ 容器类型: Group (无 padding，无背景)

================================================================================
用法
================================================================================

    # 等宽网格
    with field_row(3):
        changed, a = enum_field("A", "##a", a, opts)
        changed, b = enum_field("B", "##b", b, opts)
        changed, c = int_field("C", "##c", c)

    # 自然宽度流式布局 (niri 风格)
    with field_flow():
        enum_field("品质", "##q", q, labels, width=Sp.S40)   # 160px
        enum_field("等级", "##t", t, labels, width=Sp.S24)   # 96px
        int_field("价格", "##p", p, width=Sp.S24)             # 96px
        enum_field("重量", "##w", w, labels, width=Sp.S36)   # 144px
        enum_field("材质", "##m", m, labels, width=Sp.S36)   # 144px
    # → 所有字段在一行内 (640px < 容器宽度)，窄屏自动换行
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, TypeVar

from ui import imgui_shim as imgui
from ui.layout import gap_y, tooltip
from ui.scale import Sp, SpacingArg, SizingArg, dp


# =============================================================================
# 内部状态
# =============================================================================

@dataclass
class _FieldRowState:
    """field_row 的运行时状态"""
    start_x: float
    start_y: float
    col_width: float
    gap_px: float
    num_cols: int
    current_col: int = 0
    max_height: float = 0.0


@dataclass
class _FieldFlowState:
    """field_flow 的运行时状态 — 自然宽度 + 自动换行"""
    start_x: float          # 容器起始 X (cursor)
    start_y: float          # 容器起始 Y (cursor)
    available_width: float  # 容器可用宽度 (px)
    gap_px: float           # 字段间距 (px)
    row_gap_px: float       # 行间距 (px)
    default_width: float    # 默认字段宽度 (px)
    # 运行时追踪
    current_x: float = 0.0    # 当前行已用宽度 (相对 start_x)
    current_y: float = 0.0    # 当前行 Y 偏移 (相对 start_y)
    line_height: float = 0.0  # 当前行最大高度
    total_height: float = 0.0 # 总高度
    # 每个 field 的宽度 (通过 set_next_field_width 设置)
    _next_width: float | None = None


# 嵌套布局支持 (栈)  — field_row 或 field_flow
_row_stack: list[_FieldRowState | _FieldFlowState] = []


_T = TypeVar('_T', int, float)


def _clamp(v: _T, lo: _T | None, hi: _T | None) -> _T:
    """Clamp 值到 [lo, hi] 范围，None 表示不限"""
    if lo is not None and v < lo:
        return lo
    if hi is not None and v > hi:
        return hi
    return v


# =============================================================================
# field_row — 列容器
# =============================================================================

@contextmanager
def field_row(cols: int, *, width: SizingArg = Sp.S28, gap: SpacingArg = Sp.S2):
    """N 列表单字段行

    每个 field_* 函数自动占用下一列，渲染 label (上) + control (下)。
    条件跳过的 field 不占列位。

    ⚠️ 容器类型: 纯 cursor 定位 (无 Child/Group/Table)

    Args:
        cols: 最大列数
        width: 列宽 (Sp token, Sp.S28 = 112px)
        gap: 列间距 (Sp token, Sp.S2 = 8px)

    用法::

        with field_row(3):
            changed, a = enum_field("标签A", "##a", a, opts)
            if condition:
                changed, b = enum_field("标签B", "##b", b, opts)
            changed, c = int_field("标签C", "##c", c)
    """
    cursor = imgui.get_cursor_pos()
    state = _FieldRowState(
        start_x=cursor.x,
        start_y=cursor.y,
        col_width=dp(width),
        gap_px=dp(gap),
        num_cols=cols,
    )
    _row_stack.append(state)
    try:
        yield
    finally:
        _row_stack.pop()
        # 推进 cursor 到行下方
        imgui.set_cursor_pos((state.start_x, state.start_y + state.max_height))


# =============================================================================
# field_flow — 自然宽度流式布局
# =============================================================================

@contextmanager
def field_flow(*, gap: SpacingArg = Sp.S2, row_gap: SpacingArg = Sp.S3, default_width: SizingArg = Sp.S28):
    """自然宽度流式布局 — 每个字段指定自己的宽度，自动换行

    类似 CSS flex-wrap: wrap。字段按自然宽度排列，超出容器宽度时自动换行。

    ⚠️ 容器类型: 纯 cursor 定位 (无 Child/Group/Table)

    Args:
        gap: 字段间距 (Sp token, Sp.S2 = 8px)
        row_gap: 行间距 (Sp token, Sp.S3 = 12px)
        default_width: 未指定 width 时的默认字段宽度 (Sp token, Sp.S28 = 112px)

    用法::

        with field_flow():
            enum_field("品质", "##q", q, labels, width=Sp.S40)   # 160px
            enum_field("等级", "##t", t, labels, width=Sp.S24)   # 96px
            int_field("价格", "##p", p, width=Sp.S24)             # 96px
            # → 一行放得下就一行，放不下自动换行
    """
    cursor = imgui.get_cursor_pos()
    avail = imgui.get_content_region_available_width()
    state = _FieldFlowState(
        start_x=cursor.x,
        start_y=cursor.y,
        available_width=avail,
        gap_px=dp(gap),
        row_gap_px=dp(row_gap),
        default_width=dp(default_width),
    )
    _row_stack.append(state)
    try:
        yield
    finally:
        _row_stack.pop()
        # 推进 cursor 到最后一行下方
        total = state.current_y + state.line_height
        imgui.set_cursor_pos((state.start_x, state.start_y + total))


def set_next_field_width(width: SizingArg) -> None:
    """设置下一个 field 的宽度 (Sp/Cn token)

    仅在 field_flow() 内有效。field_row 内忽略。

    Args:
        width: 字段宽度 (Sp token, 如 Sp.S40 = 160px)
    """
    if _row_stack and isinstance(_row_stack[-1], _FieldFlowState):
        _row_stack[-1]._next_width = dp(width)  # pyright: ignore[reportPrivateUsage]


# =============================================================================
# 内部: 字段 begin/end
# =============================================================================

def _begin_field(label: str, *, width: SizingArg | None = None) -> float:
    """开始一个字段单元格: 定位到当前列, 画标签, 设置控件宽度。

    Args:
        label: 标签文字
        width: 字段宽度 (Sp/Cn token)。仅 field_flow 模式使用，field_row 忽略。

    Returns:
        列宽 (px), 可用于自定义控件的 set_next_item_width
    """
    if not _row_stack:
        raise RuntimeError("field 函数必须在 field_row() 或 field_flow() 内调用")

    state = _row_stack[-1]

    if isinstance(state, _FieldFlowState):
        return _begin_field_flow(state, label, width)
    else:
        return _begin_field_row(state, label)


def _begin_field_row(state: _FieldRowState, label: str) -> float:
    """field_row 模式: 定位到固定列"""
    col_x = state.start_x + state.current_col * (state.col_width + state.gap_px)
    imgui.set_cursor_pos((col_x, state.start_y))
    imgui.begin_group()

    from ui import tw as _tw
    _tw.text_muted(imgui.text)(label)
    gap_y(Sp.S0_5)

    # 控件默认样式: 背景 + 边框 + 圆角
    _tw.input_default.__enter__()

    imgui.set_next_item_width(state.col_width)
    return state.col_width


def _begin_field_flow(state: _FieldFlowState, label: str, width_tw: SizingArg | None) -> float:
    """field_flow 模式: 自然宽度 + 自动换行"""
    # 确定本 field 的宽度
    if state._next_width is not None:  # pyright: ignore[reportPrivateUsage]
        field_w = state._next_width  # pyright: ignore[reportPrivateUsage]
        state._next_width = None  # pyright: ignore[reportPrivateUsage]
    elif width_tw is not None:
        field_w = dp(width_tw)
    else:
        field_w = state.default_width

    # 自动换行: 如果当前行放不下，换到下一行
    if state.current_x > 0 and state.current_x + state.gap_px + field_w > state.available_width:
        state.current_y += state.line_height + state.row_gap_px
        state.current_x = 0
        state.line_height = 0

    # 计算位置
    x = state.start_x + state.current_x
    y = state.start_y + state.current_y
    imgui.set_cursor_pos((x, y))
    imgui.begin_group()

    from ui import tw as _tw
    _tw.text_muted(imgui.text)(label)
    gap_y(Sp.S0_5)

    # 控件默认样式: 背景 + 边框 + 圆角
    _tw.input_default.__enter__()

    imgui.set_next_item_width(field_w)
    return field_w


def _end_field():
    """结束字段单元格: 关闭 group, 记录高度, 推进位置"""
    # 弹出控件默认样式
    from ui import tw as _tw
    _tw.input_default.__exit__(None, None, None)

    imgui.end_group()
    state = _row_stack[-1]
    col_height = imgui.get_item_rect_size().y

    if isinstance(state, _FieldFlowState):
        col_width = imgui.get_item_rect_size().x
        state.line_height = max(state.line_height, col_height)
        state.current_x += col_width + state.gap_px
    else:
        state.max_height = max(state.max_height, col_height)
        state.current_col += 1


# =============================================================================
# 标准字段函数
# =============================================================================

def enum_field(
    label: str,
    id: str,
    value: Any,
    options: list[Any] | dict[Any, str],
    labels: dict[Any, str] | None = None,
    *,
    width: SizingArg | None = None,
    tooltip_text: str | None = None,
) -> tuple[bool, Any]:
    """枚举下拉框字段

    Args:
        label: 上方标签文字
        id: ImGui ID (如 "##eq_mode")
        value: 当前值
        options: 选项列表, 或 {value: display_label} 字典
        labels: 值→显示文字映射 (若 options 为 dict 则自动提取)
        tooltip_text: 悬停提示

    Returns:
        (changed, new_value)
    """
    _begin_field(label, width=width)

    # 统一 options/labels
    if isinstance(options, dict):
        if labels is None:
            labels = options
        options = list(options.keys())
    if labels is None:
        labels = {v: str(v) for v in options}

    current_label = str(labels.get(value, value))
    new_value = value

    # 安全: 当前值不在选项中时追加，避免显示异常
    if value not in options:
        options = list(options) + [value]

    if imgui.begin_combo(id, current_label):
        for opt in options:
            display = str(labels.get(opt, opt))
            if imgui.selectable(display, opt == value)[0]:
                new_value = opt
        imgui.end_combo()

    if tooltip_text:
        tooltip(tooltip_text)

    _end_field()
    return new_value != value, new_value


def int_field(
    label: str,
    id: str,
    value: int,
    *,
    width: SizingArg | None = None,
    vmin: int | None = None,
    vmax: int | None = None,
    step: int = 0,
    step_fast: int = 0,
    tooltip_text: str | None = None,
) -> tuple[bool, int]:
    """整数输入字段

    Args:
        label: 上方标签文字
        id: ImGui ID
        value: 当前值
        vmin: 最小值 (None = 不限)
        vmax: 最大值 (None = 不限)
        step: 步进值 (0 = 隐藏 +/- 按钮)
        step_fast: 快速步进值
        tooltip_text: 悬停提示

    Returns:
        (changed, new_value) — new_value 已 clamp
    """
    _begin_field(label, width=width)

    changed, new_value = imgui.input_int(id, value, step=step, step_fast=step_fast)
    if changed:
        new_value = _clamp(new_value, vmin, vmax)

    if tooltip_text:
        tooltip(tooltip_text)

    _end_field()
    return changed, new_value


def toggle_field(
    label: str,
    id: str,
    value: bool,
    *,
    width: SizingArg | None = None,
    tooltip_text: str | None = None,
) -> tuple[bool, bool]:
    """布尔开关 (checkbox) 字段

    Returns:
        (changed, new_value)
    """
    _begin_field(label, width=width)

    changed, new_value = imgui.checkbox(id, value)

    if tooltip_text:
        tooltip(tooltip_text)

    _end_field()
    return changed, new_value


def readonly_field(
    label: str,
    value: str,
    *,
    width: SizingArg | None = None,
    tooltip_text: str | None = None,
) -> None:
    """只读文本显示字段"""
    _begin_field(label, width=width)

    imgui.align_text_to_frame_padding()
    imgui.text(str(value))

    if tooltip_text:
        tooltip(tooltip_text)

    _end_field()


def text_field(
    label: str,
    id: str,
    value: str,
    *,
    width: SizingArg | None = None,
    buffer_size: int = 256,
    tooltip_text: str | None = None,
) -> tuple[bool, str]:
    """文本输入字段

    Args:
        label: 上方标签文字
        id: ImGui ID
        value: 当前文本
        buffer_size: 缓冲区大小
        tooltip_text: 悬停提示

    Returns:
        (changed, new_value)
    """
    _begin_field(label, width=width)

    changed, new_value = imgui.input_text(id, value, buffer_size)

    if tooltip_text:
        tooltip(tooltip_text)

    _end_field()
    return changed, new_value


def button_field(
    label: str,
    btn_label: str,
    *,
    width: SizingArg | None = None,
    tooltip_text: str | None = None,
) -> bool:
    """按钮字段

    Returns:
        clicked
    """
    _begin_field(label, width=width)

    clicked = imgui.button(btn_label)

    if tooltip_text:
        tooltip(tooltip_text)

    _end_field()
    return clicked


@contextmanager
def field_slot(label: str, *, width: SizingArg | None = None, tooltip_text: str | None = None):
    """自定义字段槽位 — 标签由 field_slot 绘制, 控件由用户提供

    适用于标准 field 函数无法覆盖的复杂控件 (如树形选择器)。

    Yields:
        col_width (float) — 列宽 px, 可用于 set_next_item_width

    用法::

        with field_slot("技能") as w:
            imgui.set_next_item_width(w)
            if imgui.begin_combo("##skill", current_label):
                # 树形选择...
                imgui.end_combo()
    """
    col_width = _begin_field(label, width=width)
    try:
        yield col_width
    finally:
        if tooltip_text:
            tooltip(tooltip_text)
        _end_field()


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    'field_row',
    'field_flow',
    'set_next_field_width',
    'enum_field',
    'int_field',
    'text_field',
    'toggle_field',
    'readonly_field',
    'button_field',
    'field_slot',
]
