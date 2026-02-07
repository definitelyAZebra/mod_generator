# -*- coding: utf-8 -*-
"""混合物品编辑器 - 呈现面板

"外观" - 贴图、音效、本地化

================================================================================
样式设计规范
================================================================================

布局结构:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ 贴图编辑器 (由 texture_editor 模块提供)                                 │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                        separator        │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ 音效组: [放下音效] [拾取音效]                           grid-cols-2     │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                        separator        │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ 本地化编辑器:                                                           │
    │   [添加语言]                                                            │
    │   主语言 (Chinese)                                                      │
    │     名称: [input]                                                       │
    │     描述: [multiline]                                                   │
    │   其他语言...                                                           │
    └─────────────────────────────────────────────────────────────────────────┘
================================================================================
"""

from __future__ import annotations

from ui import imgui_shim as imgui

from ui import tw
from ui import layout as ly
from ui.layout import tooltip
from ui.styles import gap_m, gap_s, text_secondary

from hybrid_item_v2 import HybridItemV2
from constants import (
    HYBRID_DROP_SOUNDS,
    HYBRID_PICKUP_SOUNDS,
    LANGUAGE_LABELS,
    PRIMARY_LANGUAGE,
)


# =============================================================================
# 间距常量 (Tailwind 单位: 1 = 4px)
# =============================================================================

_SECTION_GAP = 5     # 分组之间间距 (20px)
_LABEL_GAP = 1       # 标签与输入框间距 (4px)
_COL_GAP = 4         # 列间距 (16px)


# =============================================================================
# 本地辅助组件
# =============================================================================

def _label(text: str) -> None:
    """字段标签 — text-parchment-400"""
    tw.text_parchment_400(imgui.text)(text)


def _enum_combo(label: str, current_value, options: list, labels: dict):
    """值模式下拉框"""
    current_label = str(labels.get(current_value, current_value))
    new_value = current_value

    if current_value not in options:
        options = list(options) + [current_value]

    with tw.frame_bg_abyss_800 | tw.border_abyss_600 | tw.rounded_sm:
        if imgui.begin_combo(label, current_label):
            for opt in options:
                display = str(labels.get(opt, opt))
                if imgui.selectable(display, opt == current_value)[0]:
                    new_value = opt
            imgui.end_combo()

    return new_value


# =============================================================================
# 主入口
# =============================================================================

def draw_presentation_panel(hybrid: HybridItemV2) -> None:
    """绘制呈现面板

    Args:
        hybrid: 混合物品数据对象
    """
    # 1. 贴图编辑器
    from ui.editors.texture_editor import draw_textures_editor
    draw_textures_editor(hybrid, "hybrid")

    imgui.dummy(0, gap_m())
    imgui.separator()
    imgui.dummy(0, gap_s())

    # 2. 音效
    _draw_sounds_section(hybrid)

    imgui.dummy(0, gap_m())
    imgui.separator()
    imgui.dummy(0, gap_s())

    # 3. 本地化
    _draw_localization_editor(hybrid, "hybrid")


# =============================================================================
# 音效
# =============================================================================

def _draw_sounds_section(hybrid: HybridItemV2) -> None:
    """音效设置: 放下/拾取

    Tailwind: grid grid-cols-2 gap-4
    """
    with ly.columns(2, gap=_COL_GAP) as cols:
        # === 放下音效 ===
        with cols.col(0):
            _label("放下音效")
            ly.gap_y(_LABEL_GAP)
            imgui.push_item_width(cols.col_width)
            current_drop_label = HYBRID_DROP_SOUNDS.get(hybrid.drop_sound, f"{hybrid.drop_sound}")
            if imgui.begin_combo("##drop_sound", current_drop_label):
                for sound_id, sound_label in HYBRID_DROP_SOUNDS.items():
                    if imgui.selectable(sound_label, sound_id == hybrid.drop_sound)[0]:
                        hybrid.drop_sound = sound_id
                imgui.end_combo()
            imgui.pop_item_width()
            tooltip("物品放入物品栏或地面时的音效")

        # === 拾取音效 ===
        with cols.col(1):
            _label("拾取音效")
            ly.gap_y(_LABEL_GAP)
            imgui.push_item_width(cols.col_width)
            current_pickup_label = HYBRID_PICKUP_SOUNDS.get(hybrid.pickup_sound, f"{hybrid.pickup_sound}")
            if imgui.begin_combo("##pickup_sound", current_pickup_label):
                for sound_id, sound_label in HYBRID_PICKUP_SOUNDS.items():
                    if imgui.selectable(sound_label, sound_id == hybrid.pickup_sound)[0]:
                        hybrid.pickup_sound = sound_id
                imgui.end_combo()
            imgui.pop_item_width()
            tooltip("物品被拾取时的音效")


# =============================================================================
# 本地化编辑器
# =============================================================================

def _draw_localization_editor(item: HybridItemV2, id_suffix: str) -> None:
    """本地化编辑器 — 多语言名称和描述

    从 CommonEditorMixin._draw_localization_editor 提取。
    使用 imgui.get_font_size() 替代旧 self.font_size。
    """
    suffix = f"_{id_suffix}"
    font_size = imgui.get_font_size()

    # 添加语言按钮
    if imgui.button(f"添加语言##{id_suffix}"):
        imgui.open_popup(f"add_language_popup{suffix}")

    if imgui.begin_popup(f"add_language_popup{suffix}"):
        for lang in LANGUAGE_LABELS:
            if not item.localization.has_language(lang):
                label = LANGUAGE_LABELS.get(lang, lang)
                if imgui.selectable(label)[0]:
                    item.localization.languages[lang] = {
                        "name": "",
                        "description": "",
                    }
        imgui.end_popup()

    imgui.dummy(0, gap_s())

    # 主语言
    primary_label = LANGUAGE_LABELS.get(PRIMARY_LANGUAGE, PRIMARY_LANGUAGE)
    text_secondary(f"{primary_label} (主语言)")

    if not item.localization.has_language(PRIMARY_LANGUAGE):
        item.localization.languages[PRIMARY_LANGUAGE] = {
            "name": "",
            "description": "",
        }

    primary_data = item.localization.languages[PRIMARY_LANGUAGE]

    text_secondary("名称")
    imgui.push_item_width(-1)
    changed, val = imgui.input_text(
        f"##{PRIMARY_LANGUAGE}_name{suffix}", primary_data["name"], 256,
    )
    if changed:
        primary_data["name"] = val
    if not primary_data["name"] and imgui.is_item_hovered():
        imgui.set_tooltip("主语言名称（建议填写）")
    imgui.pop_item_width()

    text_secondary("描述")
    imgui.push_item_width(-1)
    desc_height = 50 + (font_size - 14) * 3
    changed, val = imgui.input_text_multiline(
        f"##{PRIMARY_LANGUAGE}_desc{suffix}",
        primary_data["description"],
        1024,
        height=desc_height,
    )
    if changed:
        primary_data["description"] = val
    imgui.pop_item_width()
    imgui.dummy(0, gap_m())

    # 其他语言
    langs_to_remove = []
    for lang in LANGUAGE_LABELS:
        if lang == PRIMARY_LANGUAGE:
            continue
        if not item.localization.has_language(lang):
            continue

        data = item.localization.languages[lang]

        imgui.separator()
        imgui.dummy(0, gap_s())
        label = LANGUAGE_LABELS.get(lang, lang)
        text_secondary(f"{label}")
        imgui.same_line()
        if imgui.button(f"删除##{lang}{suffix}"):
            langs_to_remove.append(lang)

        text_secondary("名称")
        imgui.push_item_width(-1)
        changed, val = imgui.input_text(f"##{lang}_name{suffix}", data["name"], 256)
        if changed:
            data["name"] = val
        imgui.pop_item_width()

        text_secondary("描述")
        imgui.push_item_width(-1)
        desc_height = 50 + (font_size - 14) * 3
        changed, val = imgui.input_text_multiline(
            f"##{lang}_desc{suffix}", data["description"], 1024, height=desc_height,
        )
        if changed:
            data["description"] = val
        imgui.pop_item_width()
        imgui.dummy(0, gap_s())

    for lang in langs_to_remove:
        del item.localization.languages[lang]


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_presentation_panel"]
