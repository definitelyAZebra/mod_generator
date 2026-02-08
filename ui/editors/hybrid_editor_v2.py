# -*- coding: utf-8 -*-
"""混合物品编辑器 V2 - 单页滚动布局

废除 Tab Bar，所有表单区域在同一页面内纵向排列，通过视觉分隔符分区。
每个 section 由对应的 panel 模块绘制。

设计原则:
    - 所有内容始终可见，滚动即达，无需点击发现
    - 不使用 gui god object
    - 每个 panel 函数接收 hybrid 数据对象
    - 遵循 tw/ly UI 规范
    - 验证错误固定在底部

================================================================================
样式设计规范 (Tailwind 思路)
================================================================================

布局结构:
    ```jsx
    <div className="flex flex-col h-full bg-abyss-900">
      {/* 可滚动的单页表单 */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {/* Section: 基础 */}
        <SectionHeading>基础</SectionHeading>
        <BasePanel />

        <SectionDivider />

        {/* Section: 行为 */}
        <SectionHeading>行为</SectionHeading>
        <BehaviorPanel />

        <SectionDivider />

        {/* Section: 属性 (条件) */}
        <SectionHeading>属性</SectionHeading>
        <StatsPanel />

        <SectionDivider />

        {/* Section: 呈现 */}
        <SectionHeading>呈现</SectionHeading>
        <PresentationPanel />
      </div>

      {/* 验证错误区 - 固定在底部 */}
      <div className="px-4 pb-3">
        <ErrorBox />
      </div>
    </div>
    ```

间距常量:
    - CONTENT_PX = 4 (16px) - 内容区水平内边距
    - CONTENT_PY = 3 (12px) - 内容区顶部内边距
    - SECTION_GAP = 6 (24px) - 区域之间的间距
    - HEADING_GAP = 3 (12px) - 标题与内容之间的间距
    - ERROR_GAP = 3 (12px) - 错误区与上方的间距
================================================================================
"""

from __future__ import annotations

from ui import imgui_shim as imgui

from ui import tw
from ui import layout as ly
from ui.editors.common import draw_indented_separator
from hybrid_item_v2 import HybridItemV2
from specs import EffectTrigger
from models import validate_hybrid_item
from ui.state import state as ui_state


# =============================================================================
# 间距常量 (Tailwind 单位: 1 = 4px)
# =============================================================================

_CONTENT_PX = 4      # 内容区水平内边距 (16px)
_CONTENT_PY = 3      # 内容区顶部内边距 (12px)
_SECTION_GAP = 6     # 区域之间间距 (24px)
_HEADING_GAP = 3     # 标题与内容间距 (12px)
_ERROR_GAP = 3       # 错误区与内容间距 (12px)


def draw_hybrid_editor(hybrid: HybridItemV2) -> None:
    """混合物品编辑器 - 单页滚动表单

    布局结构:
        ┌─────────────────────────────────────────────────────┐
        │ ← px=16 →  [基础]                     section 标题 │
        │  ID        品质        等级                         │
        │  [input]   [combo]     [combo]            基础面板  │
        │  ...                                                │
        │─────────────────────────────────────── 视觉分隔符 ──│
        │  [行为]                                             │
        │  装备形态  触发  充能  ...                行为面板  │
        │─────────────────────────────────────── 视觉分隔符 ──│
        │  [属性]                                             │
        │  ...                                      属性面板  │
        │─────────────────────────────────────── 视觉分隔符 ──│
        │  [呈现]                                             │
        │  贴图 / 音效 / 本地化                    呈现面板  │
        ├─────────────────────────────────────────────────────┤
        │ ⚠️ 验证错误...                                      │
        └─────────────────────────────────────────────────────┘

    Args:
        hybrid: 混合物品数据对象
    """
    from ui.editors.hybrid.base_panel import draw_base_panel
    from ui.editors.hybrid.behavior_panel import draw_behavior_panel
    from ui.editors.hybrid.stats_panel import draw_stats_panel
    from ui.editors.hybrid.presentation_panel import draw_presentation_panel

    show_attrs = _should_show_attributes(hybrid) or isinstance(hybrid.trigger, EffectTrigger)

    # =========================================================================
    # 顶部间距 + 水平缩进
    # =========================================================================
    ly.gap_y(_CONTENT_PY)
    imgui.indent(ly.sz(_CONTENT_PX))

    # =========================================================================
    # Section 1: 基础
    # =========================================================================
    _section_heading("基础")
    draw_base_panel(hybrid)

    # =========================================================================
    # Section 2: 行为
    # =========================================================================
    _section_divider()
    _section_heading("行为")
    draw_behavior_panel(hybrid)

    # =========================================================================
    # Section 3: 属性 (条件显示)
    # =========================================================================
    if show_attrs:
        _section_divider()
        _section_heading("属性")
        draw_stats_panel(hybrid)

    # =========================================================================
    # Section 4: 呈现
    # =========================================================================
    _section_divider()
    _section_heading("呈现")
    draw_presentation_panel(hybrid)

    # =========================================================================
    # 底部留白 (滚动尾部呼吸空间)
    # =========================================================================
    ly.gap_y(_SECTION_GAP)

    imgui.unindent(ly.sz(_CONTENT_PX))

    # =========================================================================
    # 验证错误区域
    # =========================================================================
    errors = validate_hybrid_item(hybrid, ui_state.project, include_warnings=True)
    if errors:
        ly.gap_y(_ERROR_GAP)
        _draw_validation_errors(errors)


# =============================================================================
# 内部组件
# =============================================================================

def _section_heading(title: str) -> None:
    """区域标题

    Tailwind: text-crystal-400 text-sm font-medium tracking-wide
    """
    tw.text_accent(imgui.text)(title)
    ly.gap_y(_HEADING_GAP)


def _section_divider() -> None:
    """区域分隔符 — 间距 + 细线 + 间距

    Tailwind: my-6 border-t border-stone-700/50
    """
    ly.gap_y(_SECTION_GAP)
    # 细线
    cursor_x, cursor_y = imgui.get_cursor_screen_pos()
    max_x = cursor_x + imgui.get_content_region_available_width()
    draw_list = imgui.get_window_draw_list()
    draw_list.add_line(
        cursor_x, cursor_y, max_x, cursor_y,
        imgui.get_color_u32_rgba(*tw.STONE_800), 1.0
    )
    imgui.dummy(0, 1)
    ly.gap_y(_SECTION_GAP)


def _draw_validation_errors(errors: list[str]) -> None:
    """绘制验证错误区域 (standalone, 不依赖 gui)"""
    with tw.bg_app | tw.border_blood_700 | tw.child_border_size(1) | tw.rounded_md | tw.p_3:
        draw_indented_separator()
        imgui.text("消息:")
        for error in errors:
            if error.endswith("):"):
                continue
            content = error.lstrip()
            if content.startswith("• WARNING:"):
                imgui.text("  ")
                imgui.same_line()
                tw.text_warning(imgui.text)("!")
                imgui.same_line()
                tw.text_warning(imgui.text)(content[10:].strip())
            elif content.startswith("\u2022"):
                imgui.text("  ")
                imgui.same_line()
                tw.text_error(imgui.text)("X")
                imgui.same_line()
                tw.text_error(imgui.text)(content[1:].strip())
            else:
                imgui.text("  ")
                imgui.same_line()
                tw.text_error(imgui.text)("X")
                imgui.same_line()
                tw.text_error(imgui.text)(error)


def _should_show_attributes(hybrid: HybridItemV2) -> bool:
    """判断是否显示属性加成编辑器"""
    from specs import is_weapon_mode, is_armor_mode, is_charm_mode
    return (
        is_weapon_mode(hybrid.equipment)
        or is_armor_mode(hybrid.equipment)
        or is_charm_mode(hybrid.equipment)
    )


__all__ = ["draw_hybrid_editor"]
