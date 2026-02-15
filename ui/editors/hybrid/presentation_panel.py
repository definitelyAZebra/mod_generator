# -*- coding: utf-8 -*-
"""混合物品编辑器 - 外观面板: 贴图与音效 / 本地化

================================================================================
设计理念
================================================================================

拆分为两张独立卡片, 由 hybrid_editor_v2 以响应式双列渲染:
  - "贴图与音效" 卡片: 穿戴/物品栏/战利品贴图 + 音效 combo
  - "本地化" 卡片: Tab 切换语言, 名称 + 描述输入

宽屏 (>1100px): 双列并排, 类似 "身份" + "装备与触发"
窄屏: 垂直堆叠

层级与视觉语言:
  L0: 卡片标题 (紫色强调条, 由 hybrid_editor_v2 渲染)
  L1: tw.text_muted 标签 → 贴图类型、音效、名称/描述
  分隔: 仅 gap_y, 不使用 separator
================================================================================
"""

from __future__ import annotations

from ui import imgui_shim as imgui

from ui import tw
from ui import layout as ly
from ui.scale import Sp

from core.hybrid_item import HybridItemV2
from constants import (
    HYBRID_DROP_SOUNDS,
    HYBRID_PICKUP_SOUNDS,
)
from ui.editors.common import draw_localization_editor


# =============================================================================
# 贴图与音效 卡片
# =============================================================================

def draw_textures_panel(hybrid: HybridItemV2) -> None:
    """贴图面板 — 穿戴/物品栏/战利品贴图"""
    from ui.editors.texture_editor import draw_textures_editor
    draw_textures_editor(hybrid, "hybrid")


def draw_sound_panel(hybrid: HybridItemV2) -> None:
    """音效面板 — 放下/拾取音效 combo"""
    _draw_sounds(hybrid)


def _draw_sounds(hybrid: HybridItemV2) -> None:
    """音效设置: 双列布局, 放下/拾取并排

    Tailwind: grid grid-cols-2 gap-4
    """
    with tw.input_default:
        with ly.columns(2, gap=Sp.S3) as c:
            with c.col(0):
                tw.text_muted(imgui.text)("放下音效")
                ly.gap_y(Sp.S0_5)
                imgui.set_next_item_width(c.col_width)
                current_drop = HYBRID_DROP_SOUNDS.get(hybrid.drop_sound, f"{hybrid.drop_sound}")
                if imgui.begin_combo("##drop_sound", current_drop):
                    for sid, slabel in HYBRID_DROP_SOUNDS.items():
                        if imgui.selectable(slabel, sid == hybrid.drop_sound)[0]:
                            hybrid.drop_sound = sid
                    imgui.end_combo()

            with c.col(1):
                tw.text_muted(imgui.text)("拾取音效")
                ly.gap_y(Sp.S0_5)
                imgui.set_next_item_width(c.col_width)
                current_pickup = HYBRID_PICKUP_SOUNDS.get(hybrid.pickup_sound, f"{hybrid.pickup_sound}")
                if imgui.begin_combo("##pickup_sound", current_pickup):
                    for sid, slabel in HYBRID_PICKUP_SOUNDS.items():
                        if imgui.selectable(slabel, sid == hybrid.pickup_sound)[0]:
                            hybrid.pickup_sound = sid
                    imgui.end_combo()


# =============================================================================
# 本地化 卡片
# =============================================================================

def draw_localization_panel(hybrid: HybridItemV2) -> None:
    """本地化面板 — Tab 切换语言, 名称 + 描述输入

    Args:
        hybrid: 混合物品数据对象
    """
    draw_localization_editor(hybrid, "hybrid")


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_textures_panel", "draw_sound_panel", "draw_localization_panel"]
