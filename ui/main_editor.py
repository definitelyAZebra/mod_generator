# -*- coding: utf-8 -*-
"""主编辑区路由分发

根据当前导航选择，在中间区域显示对应的编辑器。

⚠️ 架构：纯路由分发，不创建容器
    - 本模块只负责根据状态调用对应的 editor
    - 每个 editor 完全自治，自己创建 Child Window 并控制样式
    - 接收 (width, height) 参数并传递给 editor
"""

from __future__ import annotations

from ui import imgui_shim as imgui

from ui.state import state as ui_state, dpi_scale
from ui import layout as ly
from ui import tw
from ui.theme import PARCHMENT


def draw_main_editor(width: float, height: float) -> None:
    """主编辑区路由分发

    ⚠️ 架构：纯路由，不创建容器
        每个 editor 完全自治，自己创建 Child Window 并控制样式

    根据当前导航选择显示对应编辑器：
    - 无选中: 项目信息编辑器
    - weapon: 武器编辑器
    - armor: 装备编辑器
    - hybrid: 混合物品编辑器

    Args:
        width: 面板宽度 (像素，已应用 DPI)
        height: 面板高度 (像素，已应用 DPI)
    """
    nav_type = ui_state.nav_item_type

    if nav_type is None or not ui_state.has_selection():
        # 没有选中任何物品，显示项目编辑器
        from ui.editors.project_editor import draw_project_editor
        draw_project_editor(width, height)

    elif nav_type == "weapon":
        _draw_weapon_main(width, height)

    elif nav_type == "armor":
        _draw_armor_main(width, height)

    elif nav_type == "hybrid":
        _draw_hybrid_main(width, height)

    else:
        _draw_empty_state(width, height, "请从左侧导航选择要编辑的内容")


def _draw_weapon_main(width: float, height: float) -> None:
    """绘制武器编辑器主区域"""
    from ui.panels import panel_style
    from ui.editors.weapon_editor import draw_weapon_editor

    with panel_style:
        imgui.begin_child("WeaponEditor", width, height, border=False, flags=imgui.WINDOW_NO_SCROLLBAR)

    current_index = ui_state.current_weapon_index
    weapons = ui_state.project.weapons

    if current_index < 0 or current_index >= len(weapons):
        _draw_empty_hint("请从左侧列表选择一个武器进行编辑")
    else:
        d = dpi_scale()
        padding = ly.sz(1.75)
        ly.gap_y_px(padding / d)
        imgui.indent(padding)
        draw_weapon_editor()
        imgui.unindent()

    imgui.end_child()


def _draw_armor_main(width: float, height: float) -> None:
    """绘制装备编辑器主区域"""
    from ui.panels import panel_style
    from ui.editors.armor_editor import draw_armor_editor

    with panel_style:
        imgui.begin_child("ArmorEditor", width, height, border=False, flags=imgui.WINDOW_NO_SCROLLBAR)

    current_index = ui_state.current_armor_index
    armors = ui_state.project.armors

    if current_index < 0 or current_index >= len(armors):
        _draw_empty_hint("请从左侧列表选择一个装备进行编辑")
    else:
        d = dpi_scale()
        padding = ly.sz(1.75)
        ly.gap_y_px(padding / d)
        imgui.indent(padding)
        draw_armor_editor()
        imgui.unindent()

    imgui.end_child()


def _draw_hybrid_main(width: float, height: float) -> None:
    """绘制混合物品编辑器主区域 - 单页滚动 + 浮动预测条

    ⚠️ 容器类型: Child Window (自己创建, 可纵向滚动)

    布局结构:
        ┌─────────────────────────────────────────────────────┐
        │ HybridEditor Child (bg-elevated, 可纵向滚动)         │
        │  │身份  ID / 品质 / 等级 / 价格 / 重量 / 材质      │
        │  分类 / 标签 / 生成规则                              │
        │  ─────────────── 分隔符 ───────────────             │
        │  │装备与触发  装备形态 / 触发 / 充能 / ...          │
        │  ─────────────── 分隔符 ───────────────             │
        │  │属性  装备属性 / 消耗品属性                       │
        │  ─────────────── 分隔符 ───────────────             │
        │  │外观  贴图 / 音效 / 本地化                       │
        │  ⚠️ 验证错误                                        │
        ├─────────────────────────────────────────────────────┤
        │ 预测条: 容器: slot1, ...  │ 商店: npc1, ...        │
        └─────────────────────────────────────────────────────┘
    """
    from ui.editors.hybrid_editor_v2 import draw_hybrid_editor, draw_prediction_bar

    current_index = ui_state.current_hybrid_index
    hybrids = ui_state.project.hybrid_items
    has_hybrid = 0 <= current_index < len(hybrids)
    hybrid = hybrids[current_index] if has_hybrid else None

    # 预测条高度 (仅当有生成规则时显示)
    from specs import spawn_is_excluded, SpawnRuleType
    prediction_h = 0.0
    if hybrid and not spawn_is_excluded(hybrid.spawn):
        if hybrid.container_spawn != SpawnRuleType.NONE or hybrid.shop_spawn != SpawnRuleType.NONE:
            prediction_h = ly.sz(10)  # 40px

    scroll_height = height - prediction_h

    # 容器样式：bg-elevated, 无边框, 内部边距由 hybrid_editor_v2 控制
    _style = (
        tw.bg_elevated |
        tw.child_rounded_none |
        tw.child_border_size(0) |
        tw.p_0
    )

    # 滚动区域
    _style(imgui.begin_child)(
        "HybridEditor",
        width,
        scroll_height,
        border=False,
        flags=0,
    )

    if not has_hybrid:
        _draw_empty_hint("请从左侧列表选择一个混合物品进行编辑")
    else:
        draw_hybrid_editor(hybrid)

    imgui.end_child()

    # 浮动预测条 — 在滚动区域下方
    if hybrid and prediction_h > 0:
        draw_prediction_bar(hybrid, width)


def _draw_empty_state(width: float, height: float, hint: str) -> None:
    """绘制空状态面板

    ⚠️ 容器类型: Child Window (自己创建)
    """
    from ui.panels import panel_style

    with panel_style:
        imgui.begin_child("EmptyState", width, height, border=False, flags=imgui.WINDOW_NO_SCROLLBAR)

    _draw_empty_hint(hint)

    imgui.end_child()


def _draw_empty_hint(hint: str) -> None:
    """绘制空状态提示"""
    region = imgui.get_content_region_available()
    hint_size = imgui.calc_text_size(hint)
    imgui.set_cursor_pos(((region.x - hint_size.x) / 2, region.y / 2))
    imgui.push_style_color(imgui.COLOR_TEXT, *PARCHMENT[300])
    imgui.text(hint)
    imgui.pop_style_color()





# =============================================================================
# 导出
# =============================================================================

__all__ = [
    'draw_main_editor',
]
