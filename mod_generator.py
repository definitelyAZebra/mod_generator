# -*- coding: utf-8 -*-
"""Stoneshard 装备模组编辑器 - 主程序

基于 ImGui 的图形界面，用于创建和编辑 Stoneshard 游戏的武器/装备模组。

模块化架构:
- generation.py: 模组生成 (验证、代码生成、贴图复制)
- ui/imgui_shim.py: pyimgui → cimgui_py 兼容层
- ui/styles.py: 样式系统 (StyleContext, apply_preflight)
- ui/tw.py: Tailwind 风格 tokens
- ui/layout.py: 布局 helpers
- ui/menu.py: 主工具栏 (draw_main_menu)
- ui/navigator.py: 左侧导航 (draw_navigator)
- ui/main_editor.py: 主编辑区路由 (draw_main_editor)
- ui/panels.py: 布局协调器 (draw_two_column_layout)
- ui/editors/: 各编辑器模块
- ui/popups.py: 弹窗服务
- ui/dialogs.py: 文件对话框
"""

import os
import sys

import glfw
from ui import imgui_shim as imgui
from ui.imgui_shim import GlfwRenderer
from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    glClear,
    glClearColor,
)

from ui import config
from ui.state import state as ui_state
from ui.styles import apply_preflight
from ui.texture_manager import unload_all_textures
from ui import popups
from ui.menu import draw_main_menu, get_toolbar_height
from ui.fonts import load_fonts
from models import ModProject


# ==================== 应用入口 ====================


def create_window() -> tuple:
    """创建 GLFW 窗口和 ImGui 上下文

    Returns:
        (window, renderer) 元组
    """
    if not glfw.init():
        print("无法初始化 GLFW")
        sys.exit(1)

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)

    window = glfw.create_window(
        1200, 800, "Stoneshard 装备模组编辑器", None, None
    )
    if not window:
        glfw.terminate()
        print("无法创建 GLFW 窗口")
        sys.exit(1)

    glfw.make_context_current(window)
    imgui.create_context()
    renderer = GlfwRenderer(window)

    # 初始化 DPI 缩放 (必须在加载字体之前)
    from ui.state import init_dpi
    init_dpi(window)

    # 确保字体目录存在
    os.makedirs("fonts", exist_ok=True)

    # 加载配置、应用主题和字体
    config.load_from_file()
    apply_preflight()
    load_fonts(renderer)

    # 初始化项目
    ui_state.set_project(ModProject())

    return window, renderer


def run(window, renderer) -> None:
    """主循环"""
    running = True
    while running:
        if glfw.window_should_close(window):
            running = False
        glfw.poll_events()
        renderer.process_inputs()

        # 检查配置变更 — 字体重载必须在 new_frame() 之前
        try:
            if config.needs_font_reload():
                config.clear_font_reload_flag()
                load_fonts(renderer)
        except Exception as e:
            print(f"[main] 配置更新失败: {e}")
            config.clear_font_reload_flag()

        imgui.new_frame()

        draw_main_menu()
        _draw_main_interface()

        popups.draw()

        imgui.render()
        glClearColor(0, 0, 0, 1)
        glClear(GL_COLOR_BUFFER_BIT)
        renderer.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    unload_all_textures()
    renderer.shutdown()
    glfw.terminate()


# ==================== 主界面 ====================


def _draw_main_interface():
    """绘制主界面 — 工具栏下方全屏窗口"""
    from ui.panels import draw_two_column_layout
    from ui.navigator import draw_navigator
    from ui.main_editor import draw_main_editor

    io = imgui.get_io()
    display_w, display_h = io.display_size
    toolbar_height = get_toolbar_height()

    imgui.set_next_window_position(0, toolbar_height)
    imgui.set_next_window_size(display_w, display_h - toolbar_height)

    imgui.begin(
        "Main Interface",
        flags=imgui.WINDOW_NO_RESIZE
        | imgui.WINDOW_NO_MOVE
        | imgui.WINDOW_NO_COLLAPSE
        | imgui.WINDOW_NO_TITLE_BAR,
    )

    if not ui_state.project.file_path:
        _draw_welcome_screen()
    else:
        draw_two_column_layout(
            draw_navigator=draw_navigator,
            draw_main=draw_main_editor,
        )

    imgui.end()


# ==================== 欢迎界面 ====================


def _draw_welcome_screen():
    """欢迎界面 — 简洁的单卡片设计

    Tailwind 设计思路:
        - 手动居中计算
        - 单卡片包含所有内容
    """
    from ui import tw
    from ui import layout as ly
    from ui.icons import FA_FOLDER_OPEN, FA_SWORD, FA_SHIELD, FA_FLASK, FA_PLUS
    from ui.dialogs import open_project_dialog

    # 手动居中计算
    avail = imgui.get_content_region_available()
    card_width = ly.sz(120)  # 480px
    card_height = ly.sz(100)  # 400px (减少高度因为删除了快速指南)

    start_x = (avail.x - card_width) / 2
    start_y = (avail.y - card_height) / 2

    if start_x > 0 and start_y > 0:
        imgui.set_cursor_pos((start_x, start_y))

    # 主卡片 - border 必须为 True 且宽度至少 1 才能使 padding 生效
    with tw.bg_abyss_800 | tw.rounded_xl | tw.p_8 | tw.child_rounded_xl | tw.border_abyss_800 | tw.child_border_size(1):
        imgui.begin_child("welcome_card", width=card_width, height=card_height, border=True)

        # ===== 装饰图标 =====
        with tw.text_crystal_500 | tw.text_xl:
            ly.text_center(f"{FA_SWORD}  {FA_SHIELD}  {FA_FLASK}")

        ly.gap_y(4)

        # ===== 主标题 =====
        with tw.text_parchment_50 | tw.text_2xl:
            ly.text_center("Stoneshard 装备模组编辑器")

        ly.gap_y(2)

        # ===== 副标题 =====
        with tw.text_parchment_400 | tw.text_sm:
            ly.text_center("武器、装备、混合物品模组的可视化创建工具")

        ly.gap_y(8)

        # ===== 分隔线 =====
        _draw_simple_divider()

        ly.gap_y(8)

        # ===== 操作标题 =====
        with tw.text_goldrim_500 | tw.text_lg:
            ly.text_center("开始使用")

        ly.gap_y(6)

        # ===== 按钮组 =====
        with ly.auto_hcenter():
            # 按钮样式 - btn_* 已内置合理的 FramePadding
            if (tw.btn_primary | tw.rounded_lg | tw.btn_md)(imgui.button)(f"{FA_PLUS}  新建项目"):
                from ui import dialogs
                if project := dialogs.new_project_dialog():
                    ui_state.set_project(project)

            ly.same_line(3)

            if (tw.btn_secondary | tw.rounded_lg | tw.border_abyss_600 | tw.frame_border_size(1) | tw.btn_md)(imgui.button)(f"{FA_FOLDER_OPEN}  打开项目"):
                if project := open_project_dialog():
                    ui_state.set_project(project)

        ly.gap_y(8)

        # ===== 底部提示 =====
        with tw.text_parchment_600 | tw.text_xs:
            ly.text_center("项目保存为 JSON 文件 • 贴图和配置统一管理")

        imgui.end_child()


def _draw_simple_divider():
    """绘制简单的分隔线"""
    from ui import tw
    from ui.state import dpi_scale

    draw_list = imgui.get_window_draw_list()
    cursor_screen = imgui.get_cursor_screen_pos()
    avail_width = imgui.get_content_region_available().x

    # 水平线
    center_x = cursor_screen.x + avail_width / 2
    y = cursor_screen.y
    line_width = 100 * dpi_scale()
    line_color = imgui.get_color_u32_rgba(*tw.ABYSS_600)

    draw_list.add_line(
        center_x - line_width / 2, y,
        center_x + line_width / 2, y,
        line_color, 1.0
    )

    imgui.dummy(0, 4)


if __name__ == "__main__":
    window, renderer = create_window()
    run(window, renderer)
