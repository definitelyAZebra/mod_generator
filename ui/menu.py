# -*- coding: utf-8 -*-
"""主工具栏 - 直接按钮式操作

取代传统菜单，所有高频操作一键直达。
使用 Tailwind 风格的 tw/layout helpers 设计。
"""

from ui import imgui_shim as imgui

from ui import config
from ui.state import state as ui_state
from ui import tw
from ui import layout as ly
from ui.scale import Sp, dp
from ui.icons import (
    FA_FILE, FA_FOLDER_OPEN, FA_FLOPPY_DISK,
    FA_DOWNLOAD
)


# =============================================================================
# 工具栏配置
# =============================================================================

# Debug 模式 - 绘制边框进行调试
TOOLBAR_DEBUG = False  # 设为 False 关闭 debug 绘制

TOOLBAR_PADDING_Y = Sp.S2    # 8px 上下内边距
TOOLBAR_PADDING_X = Sp.S3    # 12px 左右内边距


def get_toolbar_height() -> float:
    """获取工具栏高度 (已应用 DPI 缩放)

    计算: font_size + 按钮 padding(默认) + 工具栏 padding + 底部边框
    """
    font_size = imgui.get_font_size()
    # 按钮高度由 FramePadding 决定（tw.btn_* 内置）
    # 这里只需计算工具栏自身的 padding
    frame_py = dp(Sp.S1_5)  # frame_py_1_5 = 6px each side
    btn_height = font_size + 2 * frame_py
    return btn_height + 2 * dp(TOOLBAR_PADDING_Y) + 1  # +1 底部边框


def draw_main_menu() -> None:
    """绘制主工具栏

    Tailwind 设计:
      flex items-center justify-between gap-1 px-2 py-1 bg-abyss-900

    布局结构:
    ┌─────────────────────────────────────────────────────────────────┐
    │ [新建] [打开] [保存] │ [生成模组]       字体: [100%▼] │
    └─────────────────────────────────────────────────────────────────┘
    """
    toolbar_h = get_toolbar_height()
    viewport_width = imgui.get_io().display_size.x

    # 窗口 flags
    flags = (
        imgui.WINDOW_NO_TITLE_BAR |
        imgui.WINDOW_NO_RESIZE |
        imgui.WINDOW_NO_MOVE |
        imgui.WINDOW_NO_SCROLLBAR |
        imgui.WINDOW_NO_SCROLL_WITH_MOUSE |
        imgui.WINDOW_NO_SAVED_SETTINGS
    )

    imgui.set_next_window_position(0, 0)
    imgui.set_next_window_size(viewport_width, toolbar_h)

    # Tailwind: bg-app px-3 py-2 gap-1 border-0
    toolbar_style = (
        tw.bg_app |
        tw.px_3 | tw.py_2 |
        tw.gap_1 |            # ItemSpacing = 4px (按钮间距)
        tw.border_size(0)
    )

    with toolbar_style:
        imgui.begin("##toolbar", flags=flags)

        # Debug: 绘制工具栏边框和信息
        if TOOLBAR_DEBUG:
            _draw_debug_overlay()

        # 左侧按钮组 + 分隔符 + 生成按钮
        _draw_file_buttons()
        imgui.same_line(spacing=dp(Sp.S2))  # 8px 间距
        _draw_separator()
        imgui.same_line(spacing=dp(Sp.S2))  # 8px 间距
        _draw_generate_button()

        # 右对齐的字体缩放选择器
        # 使用 FramePadding 让 combo 与左侧按钮等高对齐
        with tw.frame_py_1_5:
            with ly.auto_right_slot("toolbar_right"):
                _draw_font_scale_selector()

        # 底部边框线
        _draw_bottom_border(viewport_width, toolbar_h)

        imgui.end()


def _draw_debug_overlay() -> None:
    """绘制 Debug 覆盖层（边框和信息）"""
    win_pos = imgui.get_window_position()
    win_size = imgui.get_window_size()
    style = imgui.get_style()
    draw_list = imgui.get_window_draw_list()

    # 绘制外边框（红色）- 窗口完整区域
    draw_list.add_rect(
        win_pos.x, win_pos.y,
        win_pos.x + win_size.x, win_pos.y + win_size.y,
        imgui.get_color_u32_rgba(1.0, 0.0, 0.0, 1.0), 0, 0, 2
    )

    # 绘制内容区域（绿色）- 去除 padding 后
    content_min = imgui.get_cursor_screen_pos()
    content_max_x = content_min.x + imgui.get_content_region_available().x
    content_max_y = win_pos.y + win_size.y
    draw_list.add_rect(
        content_min.x, content_min.y,
        content_max_x, content_max_y,
        imgui.get_color_u32_rgba(0.0, 1.0, 0.0, 1.0), 0, 0, 1
    )

    # 计算内容区域高度
    toolbar_content_h = win_size.y - style.window_padding.y * 2

    # 绘制文字信息（右上角）
    info_x = win_pos.x + win_size.x - 400
    info_y = win_pos.y + 2
    text_color = imgui.get_color_u32_rgba(1.0, 1.0, 0.0, 1.0)  # 黄色

    draw_list.add_text(
        info_x, info_y,
        text_color,
        f"Toolbar: {win_size.x:.0f}x{win_size.y:.0f} @ ({win_pos.x:.0f}, {win_pos.y:.0f})"
    )
    draw_list.add_text(
        info_x, info_y + 16,
        text_color,
        f"Padding: ({style.window_padding.x:.0f}, {style.window_padding.y:.0f})"
    )
    draw_list.add_text(
        info_x, info_y + 32,
        text_color,
        f"Content: {imgui.get_content_region_available().x:.0f}x{toolbar_content_h:.0f}"
    )

    # 绘制中心线（蓝色虚线）
    center_y = win_pos.y + win_size.y * 0.5
    for i in range(0, int(win_size.x), 10):
        if i % 20 < 10:
            draw_list.add_line(
                win_pos.x + i, center_y,
                win_pos.x + i + 10, center_y,
                imgui.get_color_u32_rgba(0.0, 0.5, 1.0, 0.8), 1
            )


def _draw_file_buttons() -> None:
    """绘制文件操作按钮组

    Tailwind: flex gap-0 items-center (按钮紧凑排列)
    """
    from ui import dialogs

    # Tailwind: btn-ghost rounded-sm frame-px-2 frame-py-1.5
    btn_style = tw.btn_ghost | tw.rounded_sm | tw.frame_px_2 | tw.frame_py_1_5

    # 新建
    if btn_style(imgui.button)(f"{FA_FILE} 新建"):
        project = dialogs.new_project_dialog()
        if project:
            ui_state.set_project(project)
    if imgui.is_item_hovered():
        imgui.set_tooltip("新建项目 (Ctrl+N)")

    # 打开
    imgui.same_line(spacing=dp(Sp.S1_5))  # 6px gap
    if btn_style(imgui.button)(f"{FA_FOLDER_OPEN} 打开"):
        project = dialogs.open_project_dialog()
        if project:
            ui_state.set_project(project)
    if imgui.is_item_hovered():
        imgui.set_tooltip("打开项目 (Ctrl+O)")

    # 保存
    imgui.same_line(spacing=dp(Sp.S1_5))  # 6px gap
    has_path = bool(ui_state.project and ui_state.project.file_path)
    save_style = btn_style if has_path else btn_style | tw.alpha(0.4)
    if save_style(imgui.button)(f"{FA_FLOPPY_DISK} 保存") and has_path:
        ui_state.project.save()
    if imgui.is_item_hovered(flags=imgui.HOVERED_ALLOW_WHEN_DISABLED):
        tip = "保存项目 (Ctrl+S)" if has_path else "请先创建或打开项目"
        imgui.set_tooltip(tip)


def _draw_separator() -> None:
    """绘制竖线分隔符

    Tailwind: text-abyss-600
    """
    tw.text_abyss_600(imgui.text)("|")


def _draw_generate_button() -> None:
    """绘制生成模组按钮

    Tailwind: btn-crystal rounded-sm
    """
    if (tw.btn_crystal | tw.rounded_sm | tw.frame_px_2 | tw.frame_py_1_5)(imgui.button)(f"{FA_DOWNLOAD} 生成模组"):
        from generation import generate_mod_with_validation
        generate_mod_with_validation(ui_state.project)
    if imgui.is_item_hovered():
        imgui.set_tooltip("生成 Mod 文件到输出目录")


def _draw_font_scale_selector() -> None:
    """绘制字体缩放选择器

    Tailwind: flex items-center gap-1 (标签和下拉框水平排列)
    """
    # 标签
    tw.text_muted(imgui.text)("字体:")

    # 下拉框
    imgui.same_line()
    combo_style = tw.input_default | tw.text_default

    current_scale = config.get_font_scale()
    scales = [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5]
    current_label = f"{int(current_scale * 100)}%"

    imgui.push_item_width(dp(Sp.S20))  # 80px
    with combo_style:
        if imgui.begin_combo("##font_scale", current_label):
            for scale in scales:
                label = f"{int(scale * 100)}%"
                is_selected = abs(current_scale - scale) < 0.01

                # 选中项用紫色高亮
                text_style = tw.text_accent if is_selected else tw.text_default
                with text_style:
                    if imgui.selectable(label, is_selected)[0]:
                        config.set_font_scale(scale)
                        config.save_to_file()

            imgui.end_combo()
    imgui.pop_item_width()


def _draw_bottom_border(viewport_width: float, toolbar_h: float) -> None:
    """绘制底部边框线

    Tailwind: border-b border-abyss-700
    """
    draw_list = imgui.get_window_draw_list()
    win_pos = imgui.get_window_position()
    border_color = imgui.get_color_u32_rgba(*tw.BORDER_SUBTLE)
    y = win_pos.y + toolbar_h - 1
    draw_list.add_line(0, y, viewport_width, y, border_color, 1.0)
