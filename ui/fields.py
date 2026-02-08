# -*- coding: utf-8 -*-
"""声明式表单字段组件

field_row + 标准 field 函数，消除表单布局样板代码。
每个字段渲染为: 标签 (上方, muted) + 控件 (下方)，自动排入下一列。

================================================================================
设计原则
================================================================================

1. 通用原子 — 不编码任何 UX 意见，只是 label+control 的列布局
2. ImGui 风格返回值 — (changed, new_value)
3. 与 tw/ly 系统兼容
4. field_row 不创建 ImGui 窗口/子窗口，纯 cursor 定位

⚠️ 容器类型: Group (无 padding，无背景)

================================================================================
用法
================================================================================

    from ui.fields import field_row, enum_field, int_field, toggle_field

    with field_row(3):
        changed, mode = enum_field("装备形态", "##eq", mode, MODE_OPTS)
        changed, wtype = enum_field("武器类型", "##wt", wtype, TYPE_OPTS)
        changed, bal = int_field("平衡", "##bal", bal, vmin=0, vmax=4)

    ly.gap_y(3.5)  # 手动控制行间距

    with field_row(2):
        changed, val = toggle_field("启用", "##enable", val)
        with field_slot("自定义") as w:
            imgui.set_next_item_width(w)
            if imgui.begin_combo("##custom", label):
                ...
                imgui.end_combo()

================================================================================
Tailwind 映射 (概念对照)
================================================================================

    Tailwind                    fields.py
    ─────────────────────────   ─────────────────────────
    grid grid-cols-3 gap-2      field_row(3, gap=2)
    <label class="text-muted">  field 函数自动绘制 muted 标签
    <select>...</select>        enum_field(...)
    <input type="number">       int_field(...)
    <input type="checkbox">     toggle_field(...)
    <span class="readonly">     readonly_field(...)
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from ui import imgui_shim as imgui
from ui.layout import sz, gap_y, tooltip


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


# 嵌套 field_row 支持 (栈)
_row_stack: list[_FieldRowState] = []


def _clamp(v, lo, hi):
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
def field_row(cols: int, *, width: float = 26, gap: float = 2):
    """N 列表单字段行

    每个 field_* 函数自动占用下一列，渲染 label (上) + control (下)。
    条件跳过的 field 不占列位。

    ⚠️ 容器类型: 纯 cursor 定位 (无 Child/Group/Table)

    Args:
        cols: 最大列数
        width: 列宽 (tw 单位, 26 = 104px)
        gap: 列间距 (tw 单位, 2 = 8px)

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
        col_width=sz(width),
        gap_px=sz(gap),
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
# 内部: 字段 begin/end
# =============================================================================

def _begin_field(label: str) -> float:
    """开始一个字段单元格: 定位到当前列, 画标签, 设置控件宽度。

    Returns:
        列宽 (px), 可用于自定义控件的 set_next_item_width
    """
    if not _row_stack:
        raise RuntimeError("field 函数必须在 field_row() 内调用")

    state = _row_stack[-1]
    col_x = state.start_x + state.current_col * (state.col_width + state.gap_px)
    imgui.set_cursor_pos((col_x, state.start_y))
    imgui.begin_group()

    # 标签 (muted)
    from ui import tw as _tw
    _tw.text_muted(imgui.text)(label)
    gap_y(1)  # 4px label-to-control

    # 为下一个 input/combo 预设宽度 (checkbox/button 不受影响)
    imgui.set_next_item_width(state.col_width)

    return state.col_width


def _end_field():
    """结束字段单元格: 关闭 group, 记录高度, 推进列索引"""
    imgui.end_group()
    state = _row_stack[-1]
    col_height = imgui.get_item_rect_size().y
    state.max_height = max(state.max_height, col_height)
    state.current_col += 1


# =============================================================================
# 标准字段函数
# =============================================================================

def enum_field(
    label: str,
    id: str,
    value: Any,
    options: list | dict,
    labels: dict | None = None,
    *,
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
    _begin_field(label)

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
    _begin_field(label)

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
    tooltip_text: str | None = None,
) -> tuple[bool, bool]:
    """布尔开关 (checkbox) 字段

    Returns:
        (changed, new_value)
    """
    _begin_field(label)

    changed, new_value = imgui.checkbox(id, value)

    if tooltip_text:
        tooltip(tooltip_text)

    _end_field()
    return changed, new_value


def readonly_field(
    label: str,
    value: str,
    *,
    tooltip_text: str | None = None,
) -> None:
    """只读文本显示字段"""
    _begin_field(label)

    imgui.align_text_to_frame_padding()
    imgui.text(str(value))

    if tooltip_text:
        tooltip(tooltip_text)

    _end_field()


def button_field(
    label: str,
    btn_label: str,
    *,
    tooltip_text: str | None = None,
) -> bool:
    """按钮字段

    Returns:
        clicked
    """
    _begin_field(label)

    clicked = imgui.button(btn_label)

    if tooltip_text:
        tooltip(tooltip_text)

    _end_field()
    return clicked


@contextmanager
def field_slot(label: str, *, tooltip_text: str | None = None):
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
    col_width = _begin_field(label)
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
    'enum_field',
    'int_field',
    'toggle_field',
    'readonly_field',
    'button_field',
    'field_slot',
]
