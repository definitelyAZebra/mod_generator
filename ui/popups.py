# -*- coding: utf-8 -*-
"""弹窗服务 - 模块即单例

使用方式:
    from ui import popups
    popups.error("发生错误")
    popups.success(mod_dir="/path/to/mod")
    popups.info("项目已迁移")
    popups.save_prompt(on_confirm=my_callback)

主循环中调用 popups.draw()

⚠️ ImGui 弹窗 ID 规则:
    open_popup() 和 begin_popup_modal() 必须在同一个窗口上下文内调用。
    因此公开 API 只设置 pending 标记，由 draw() 统一在同一上下文中
    调用 open_popup + begin_popup_modal。
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Generator

from ui import imgui_shim as imgui
from ui import tw
from ui import layout as ly
from ui.scale import Sp, Cn, dp
from ui.icons import (
    FA_CIRCLE_CHECK,
    FA_CIRCLE_EXCLAMATION,
    FA_CIRCLE_INFO,
    FA_CIRCLE_XMARK,
    FA_FOLDER_OPEN,
)


# ==================== 状态管理 ====================


@dataclass
class _PopupSlot:
    """单个弹窗的完整状态 (pending + active)"""
    popup_id: str
    pending: bool = False
    active_data: dict[str, Any] = field(default_factory=lambda: {})
    pending_data: dict[str, Any] = field(default_factory=lambda: {})

    def request(self, **data: Any) -> None:
        """排队打开弹窗 (下帧 draw() 时执行 open_popup)"""
        self.pending = True
        self.pending_data = data

    def flush(self) -> None:
        """在 draw() 中消费 pending, 执行 open_popup"""
        if self.pending:
            self.active_data = self.pending_data
            self.pending_data = {}
            self.pending = False
            imgui.open_popup(self.popup_id)

    def close(self) -> None:
        self.active_data = {}
        imgui.close_current_popup()


_error_slot = _PopupSlot("##popup_error")
_success_slot = _PopupSlot("##popup_success")
_info_slot = _PopupSlot("##popup_info")
_save_slot = _PopupSlot("##popup_save")


# ==================== 公开 API ====================


def error(message: str) -> None:
    """显示错误弹窗"""
    print(f"错误: {message.split(chr(10))[0]}")
    _error_slot.request(message=message)


def success(mod_dir: str) -> None:
    """显示生成成功弹窗 (带 "打开目录" 按钮)"""
    _success_slot.request(mod_dir=mod_dir)


def info(message: str) -> None:
    """显示信息弹窗 (纯文字提示)"""
    _info_slot.request(message=message)


def save_prompt(on_confirm: Callable[[], None] | None = None) -> None:
    """显示保存确认弹窗"""
    _save_slot.request(callback=on_confirm)


# ==================== 渲染 ====================


def draw() -> None:
    """绘制弹窗 (主循环每帧调用)"""
    # flush pending → open_popup (与 begin_popup_modal 同上下文)
    _error_slot.flush()
    _success_slot.flush()
    _info_slot.flush()
    _save_slot.flush()

    _draw_error_popup()
    _draw_success_popup()
    _draw_info_popup()
    _draw_save_popup()


# ==================== 内部 helpers ====================


@contextmanager
def _modal(
    slot: _PopupSlot,
    width: Sp | Cn = Cn.CMD,
) -> Generator[bool, None, None]:
    """弹窗脚手架: set_next_window_size → begin_popup_modal → end_popup

    Yields:
        True 如果弹窗已打开, False 如果未打开 (调用方可 early-return)
    """
    imgui.set_next_window_size(dp(width), 0, imgui.ONCE)
    result = imgui.begin_popup_modal(
        slot.popup_id,
        flags=imgui.WINDOW_ALWAYS_AUTO_RESIZE | imgui.WINDOW_NO_TITLE_BAR,
    )
    opened = bool(result)
    try:
        yield opened
    finally:
        if opened:
            imgui.end_popup()


def _popup_header(icon: str, text: str, icon_style: tw.StyleContext) -> None:
    """弹窗标题行: icon + 文字"""
    ly.gap_y(Sp.S2)
    ly.icon_label(icon, text, gap=Sp.S2, icon_style=icon_style, text_style=tw.text_bright)


def _popup_footer_buttons(
    slot: _PopupSlot,
    buttons: list[tuple[str, tw.StyleContext, Callable[[], None] | None]],
) -> None:
    """弹窗底部按钮行 (右对齐)

    Args:
        buttons: [(label, style, on_click | None)]  None 表示仅关闭弹窗
    """
    ly.gap_y(Sp.S4)
    with ly.auto_hcenter():
        for i, (label, style, on_click) in enumerate(buttons):
            if i > 0:
                imgui.same_line(spacing=dp(Sp.S2))
            if (style | tw.btn_sm)(imgui.button)(label):
                slot.close()
                if on_click:
                    on_click()


# ==================== 各弹窗实现 ====================


def _draw_error_popup() -> None:
    with tw.bg_elevated | tw.p_4 | tw.rounded_lg:
        with _modal(_error_slot, width=Cn.CMD) as opened:
            if not opened:
                return
            msg = _error_slot.active_data.get("message", "发生未知错误")
            _popup_header(FA_CIRCLE_XMARK, "发生错误", tw.text_error)
            ly.gap_y(Sp.S2)
            with tw.text_default:
                imgui.text_wrapped(msg)
            _popup_footer_buttons(_error_slot, [
                ("确定", tw.btn_secondary, None),
            ])


def _draw_success_popup() -> None:
    with tw.bg_elevated | tw.p_4 | tw.rounded_lg:
        with _modal(_success_slot, width=Cn.CMD) as opened:
            if not opened:
                return
            mod_dir = _success_slot.active_data.get("mod_dir", ".")
            _popup_header(FA_CIRCLE_CHECK, "模组生成成功！", tw.text_success)
            ly.gap_y(Sp.S2)
            tw.text_muted(imgui.text)("输出目录:")
            with tw.text_default:
                imgui.text_wrapped(mod_dir)

            def open_dir() -> None:
                try:
                    os.startfile(mod_dir)
                except Exception:
                    pass

            _popup_footer_buttons(_success_slot, [
                (f"{FA_FOLDER_OPEN} 打开目录", tw.btn_primary, open_dir),
                ("确定", tw.btn_secondary, None),
            ])


def _draw_info_popup() -> None:
    with tw.bg_elevated | tw.p_4 | tw.rounded_lg:
        with _modal(_info_slot, width=Cn.CSM) as opened:
            if not opened:
                return
            msg = _info_slot.active_data.get("message", "")
            _popup_header(FA_CIRCLE_INFO, "提示", tw.text_info)
            ly.gap_y(Sp.S2)
            with tw.text_default:
                imgui.text_wrapped(msg)
            _popup_footer_buttons(_info_slot, [
                ("确定", tw.btn_secondary, None),
            ])


def _draw_save_popup() -> None:
    with tw.bg_elevated | tw.p_4 | tw.rounded_lg:
        with _modal(_save_slot, width=Cn.CSM) as opened:
            if not opened:
                return
            callback = _save_slot.active_data.get("callback")
            _popup_header(FA_CIRCLE_EXCLAMATION, "需要保存项目", tw.text_warning)
            ly.gap_y(Sp.S2)
            with tw.text_default:
                imgui.text("生成模组前需要先保存项目。")
                imgui.text("是否现在保存？")
            _popup_footer_buttons(_save_slot, [
                ("保存", tw.btn_primary, callback),
                ("取消", tw.btn_secondary, None),
            ])
