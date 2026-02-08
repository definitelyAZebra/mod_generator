# -*- coding: utf-8 -*-
"""混合物品编辑器 - 外观面板: 贴图、音效、本地化"""

from __future__ import annotations

from ui import imgui_shim as imgui

from ui import tw
from ui import layout as ly
from ui.fields import field_flow, field_slot

from hybrid_item_v2 import HybridItemV2
from constants import (
    HYBRID_DROP_SOUNDS,
    HYBRID_PICKUP_SOUNDS,
    LANGUAGE_LABELS,
    PRIMARY_LANGUAGE,
)


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

    ly.gap_y(3.5)
    imgui.separator()
    ly.gap_y(2)

    # 2. 音效
    _draw_sounds_section(hybrid)

    ly.gap_y(3.5)
    imgui.separator()
    ly.gap_y(2)

    # 3. 本地化
    _draw_localization_editor(hybrid, "hybrid")


# =============================================================================
# 音效
# =============================================================================

def _draw_sounds_section(hybrid: HybridItemV2) -> None:
    """音效设置: 放下/拾取

    Tailwind: flex flex-wrap gap-2
    """
    with field_flow(gap=2, row_gap=2, default_width=30):
        # === 放下音效 ===
        with field_slot("放下音效", width=30, tooltip_text="物品放入物品栏或地面时的音效"):
            current_drop_label = HYBRID_DROP_SOUNDS.get(hybrid.drop_sound, f"{hybrid.drop_sound}")
            if imgui.begin_combo("##drop_sound", current_drop_label):
                for sound_id, sound_label in HYBRID_DROP_SOUNDS.items():
                    if imgui.selectable(sound_label, sound_id == hybrid.drop_sound)[0]:
                        hybrid.drop_sound = sound_id
                imgui.end_combo()

        # === 拾取音效 ===
        with field_slot("拾取音效", width=30, tooltip_text="物品被拾取时的音效"):
            current_pickup_label = HYBRID_PICKUP_SOUNDS.get(hybrid.pickup_sound, f"{hybrid.pickup_sound}")
            if imgui.begin_combo("##pickup_sound", current_pickup_label):
                for sound_id, sound_label in HYBRID_PICKUP_SOUNDS.items():
                    if imgui.selectable(sound_label, sound_id == hybrid.pickup_sound)[0]:
                        hybrid.pickup_sound = sound_id
                imgui.end_combo()


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

    ly.gap_y(2)

    # 主语言
    primary_label = LANGUAGE_LABELS.get(PRIMARY_LANGUAGE, PRIMARY_LANGUAGE)
    tw.text_muted(imgui.text)(f"{primary_label} (主语言)")

    if not item.localization.has_language(PRIMARY_LANGUAGE):
        item.localization.languages[PRIMARY_LANGUAGE] = {
            "name": "",
            "description": "",
        }

    primary_data = item.localization.languages[PRIMARY_LANGUAGE]

    tw.text_muted(imgui.text)("名称")
    imgui.push_item_width(-1)
    changed, val = imgui.input_text(
        f"##{PRIMARY_LANGUAGE}_name{suffix}", primary_data["name"], 256,
    )
    if changed:
        primary_data["name"] = val
    if not primary_data["name"] and imgui.is_item_hovered():
        imgui.set_tooltip("主语言名称（建议填写）")
    imgui.pop_item_width()

    tw.text_muted(imgui.text)("描述")
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
    ly.gap_y(3.5)

    # 其他语言
    langs_to_remove = []
    for lang in LANGUAGE_LABELS:
        if lang == PRIMARY_LANGUAGE:
            continue
        if not item.localization.has_language(lang):
            continue

        data = item.localization.languages[lang]

        imgui.separator()
        ly.gap_y(2)
        label = LANGUAGE_LABELS.get(lang, lang)
        tw.text_muted(imgui.text)(f"{label}")
        imgui.same_line()
        if imgui.button(f"删除##{lang}{suffix}"):
            langs_to_remove.append(lang)

        tw.text_muted(imgui.text)("名称")
        imgui.push_item_width(-1)
        changed, val = imgui.input_text(f"##{lang}_name{suffix}", data["name"], 256)
        if changed:
            data["name"] = val
        imgui.pop_item_width()

        tw.text_muted(imgui.text)("描述")
        imgui.push_item_width(-1)
        desc_height = 50 + (font_size - 14) * 3
        changed, val = imgui.input_text_multiline(
            f"##{lang}_desc{suffix}", data["description"], 1024, height=desc_height,
        )
        if changed:
            data["description"] = val
        imgui.pop_item_width()
        ly.gap_y(2)

    for lang in langs_to_remove:
        del item.localization.languages[lang]


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_presentation_panel"]
