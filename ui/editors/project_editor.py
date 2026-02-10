# -*- coding: utf-8 -*-
"""项目信息编辑器 - 卡片布局

与武器/装备/混合物品编辑器一致的卡片分区设计。
使用 common.py 共享的卡片基础设施。

布局结构:
    ┌──── 基本信息 ─────────────────────────────────────┐
    │ 模组名称/代号/作者/版本/目标版本 (field_flow)      │
    └───────────────────────────────────────────────────┘
    ┌──── 模组描述 ─────────────────────────────────────┐
    │ 多行文本                                           │
    └───────────────────────────────────────────────────┘
    ┌ 路径信息 (bg_surface) ────────────────────────────┐
    │ 📁 项目文件路径                                    │
    └───────────────────────────────────────────────────┘
    ✓ 项目配置有效  /  验证错误卡片
"""

from __future__ import annotations

import os

from ui import imgui_shim as imgui
from ui import tw
from ui import layout as ly
from ui.scale import Sp, dp
from ui.icons import FA_FOLDER, FA_CIRCLE_CHECK

from ui.editors.common import (
    CARD_GAP,
    draw_card_section,
    draw_validation_card,
)


# =============================================================================
# 主入口
# =============================================================================

def draw_project_editor() -> None:
    """项目编辑器 - 卡片布局

    无参数，由 main_editor._draw_project_main() 提供外层容器。
    """
    from ui.state import state as ui_state

    project = ui_state.project

    # =========================================================================
    # 基本信息 (全宽)
    # =========================================================================
    draw_card_section("基本信息", lambda: _draw_basic_info(project))

    # =========================================================================
    # 模组描述 (全宽)
    # =========================================================================
    ly.gap_y(CARD_GAP)
    draw_card_section("模组描述", lambda: _draw_description(project))

    # =========================================================================
    # 路径信息 (bg_surface 区分)
    # =========================================================================
    ly.gap_y(CARD_GAP)
    _draw_path_card(project)

    # =========================================================================
    # 验证状态
    # =========================================================================
    errors = project.validate()
    if errors:
        ly.gap_y(CARD_GAP)
        draw_validation_card(errors, "project")
    else:
        ly.gap_y(CARD_GAP)
        _draw_valid_status()


# =============================================================================
# 基本信息 — field_flow 流式表单
# =============================================================================

def _draw_basic_info(project) -> None:
    """基本信息字段

    Tailwind: flex flex-wrap gap-x-2 gap-y-3
    """
    from ui.fields import field_flow, field_slot

    with field_flow(gap=Sp.S2, row_gap=Sp.S3, default_width=Sp.S40):
        # 模组名称 (宽)
        with field_slot("模组名称", width=Sp.S56) as w:
            imgui.set_next_item_width(w)
            with tw.input_default:
                changed, nv = imgui.input_text_with_hint(
                    "##proj_name", "我的超棒模组", project.name, 256
                )
            if changed:
                project.name = nv

        # 模组代号
        with field_slot("模组代号", width=Sp.S40, tooltip_text="用于生成文件名，仅限英文和下划线") as w:
            imgui.set_next_item_width(w)
            with tw.input_default:
                changed, nv = imgui.input_text_with_hint(
                    "##proj_code_name", "my_mod", project.code_name, 256
                )
            if changed:
                project.code_name = nv

        # 作者
        with field_slot("作者", width=Sp.S36) as w:
            imgui.set_next_item_width(w)
            with tw.input_default:
                changed, nv = imgui.input_text_with_hint(
                    "##proj_author", "Your Name", project.author, 256
                )
            if changed:
                project.author = nv

        # 版本
        with field_slot("版本", width=Sp.S28, tooltip_text="语义化版本号") as w:
            imgui.set_next_item_width(w)
            with tw.input_default:
                changed, nv = imgui.input_text_with_hint(
                    "##proj_version", "1.0.0", project.version, 256
                )
            if changed:
                project.version = nv

        # 目标游戏版本
        with field_slot("目标游戏版本", width=Sp.S28, tooltip_text="兼容的 Stoneshard 版本") as w:
            imgui.set_next_item_width(w)
            with tw.input_default:
                changed, nv = imgui.input_text_with_hint(
                    "##proj_target_ver", "0.9.3.13", project.target_version, 256
                )
            if changed:
                project.target_version = nv


# =============================================================================
# 模组描述
# =============================================================================

def _draw_description(project) -> None:
    """描述输入框

    Tailwind: bg-abyss-700 rounded border border-abyss-600 p-2
    """
    avail_w = imgui.get_content_region_available_width()
    imgui.push_item_width(avail_w)
    with tw.input_default | tw.frame_p_2:
        _, new_desc = imgui.input_text_multiline(
            "##proj_desc", project.description, 2048, height=dp(Sp.S20)
        )
        project.description = new_desc
    imgui.pop_item_width()


# =============================================================================
# 路径信息
# =============================================================================

def _draw_path_card(project) -> None:
    """路径信息卡片 — bg_surface 以区别于 bg_elevated 的内容卡片

    Tailwind: bg-abyss-900 rounded-md px-4 py-3 flex items-center gap-2
    """
    project_dir = os.path.dirname(project.file_path) if project.file_path else ""

    _path_style = tw.bg_surface | tw.child_rounded_md | tw.p_3
    with _path_style:
        avail_w = imgui.get_content_region_available().x
        cf = int(imgui.ChildFlags.AlwaysUseWindowPadding) | int(imgui.ChildFlags.AutoResizeY)
        wf = imgui.WINDOW_NO_SCROLLBAR
        imgui.begin_child("##card_path", width=avail_w, height=0, child_flags=cf, window_flags=wf)

        icon_style = tw.text_accent if project_dir else tw.text_faint
        text_style = tw.text_muted if project_dir else tw.text_subtle
        path_text = project_dir if project_dir else "项目尚未保存到磁盘"

        icon_style(imgui.text)(FA_FOLDER)
        imgui.same_line(spacing=dp(Sp.S2))
        text_style(imgui.text)(path_text)

        imgui.end_child()


# =============================================================================
# 验证状态 — 成功
# =============================================================================

def _draw_valid_status() -> None:
    """验证通过状态

    Tailwind: flex items-center gap-2 text-green-400
    """
    tw.text_green_400(imgui.text)(FA_CIRCLE_CHECK)
    imgui.same_line(spacing=dp(Sp.S2))
    tw.text_green_400(imgui.text)("项目配置有效")


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_project_editor"]
