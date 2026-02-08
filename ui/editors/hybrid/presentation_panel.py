# -*- coding: utf-8 -*-
"""混合物品编辑器 - 外观面板: 贴图、音效、本地化

================================================================================
设计理念
================================================================================

三个子区域：贴图 / 音效 / 本地化，各用金色子标题区分。
贴图区内部的穿戴/物品栏/战利品用更轻的分隔 (gap + separator)。
音效用 field_row(2)。本地化用 tw.input_default 一致样式 + 语言块。

Tailwind 映射:
    text-goldrim-400          → tw.text_goldrim_400 (子区域标题)
    text-stone-400            → tw.text_muted (标签)
    bg-slate-700 border rounded → tw.input_default (输入框)
    flex flex-col gap-2       → ly.gap_y(2)
================================================================================
"""

from __future__ import annotations

from ui import imgui_shim as imgui

from ui import tw
from ui import layout as ly
from ui.layout import sz
from ui.fields import field_row, field_slot

from hybrid_item_v2 import HybridItemV2
from constants import (
    HYBRID_DROP_SOUNDS,
    HYBRID_PICKUP_SOUNDS,
    LANGUAGE_LABELS,
    PRIMARY_LANGUAGE,
)


# =============================================================================
# 子区域标题 (与 stats_panel 一致的金色风格)
# =============================================================================

def _sub_section(text: str) -> None:
    """子区域标题 — 金色文字

    Tailwind: text-goldrim-400 font-medium
    """
    tw.text_goldrim_400(imgui.text)(text)
    ly.gap_y(1.5)


# =============================================================================
# 主入口
# =============================================================================

def draw_presentation_panel(hybrid: HybridItemV2) -> None:
    """绘制呈现面板

    Args:
        hybrid: 混合物品数据对象
    """
    # 1. 贴图
    _sub_section("贴图")
    from ui.editors.texture_editor import draw_textures_editor
    draw_textures_editor(hybrid, "hybrid")

    ly.gap_y(4)
    imgui.separator()
    ly.gap_y(3)

    # 2. 音效
    _sub_section("音效")
    _draw_sounds_section(hybrid)

    ly.gap_y(4)
    imgui.separator()
    ly.gap_y(3)

    # 3. 本地化
    _sub_section("本地化")
    _draw_localization_editor(hybrid, "hybrid")


# =============================================================================
# 音效
# =============================================================================

def _draw_sounds_section(hybrid: HybridItemV2) -> None:
    """音效设置: 放下/拾取

    Tailwind: grid grid-cols-2 gap-2
    """
    with field_row(2, width=30):
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

    每个语言块: 语言标签 + 名称输入 + 描述多行输入
    主语言不可删除，其他语言可删除。
    """
    suffix = f"_{id_suffix}"

    # 确保主语言存在
    if not item.localization.has_language(PRIMARY_LANGUAGE):
        item.localization.languages[PRIMARY_LANGUAGE] = {
            "name": "",
            "description": "",
        }

    # --- 主语言 ---
    primary_label = LANGUAGE_LABELS.get(PRIMARY_LANGUAGE, PRIMARY_LANGUAGE)
    _draw_language_block(
        item.localization.languages[PRIMARY_LANGUAGE],
        primary_label,
        suffix,
        PRIMARY_LANGUAGE,
        is_primary=True,
    )

    # --- 其他语言 ---
    langs_to_remove: list[str] = []
    for lang in LANGUAGE_LABELS:
        if lang == PRIMARY_LANGUAGE:
            continue
        if not item.localization.has_language(lang):
            continue

        ly.gap_y(2)
        imgui.separator()
        ly.gap_y(2)

        data = item.localization.languages[lang]
        label = LANGUAGE_LABELS.get(lang, lang)
        removed = _draw_language_block(
            data, label, suffix, lang, is_primary=False,
        )
        if removed:
            langs_to_remove.append(lang)

    for lang in langs_to_remove:
        del item.localization.languages[lang]

    # --- 添加语言按钮 ---
    # 检查是否还有可添加的语言
    available_langs = [
        lang for lang in LANGUAGE_LABELS
        if not item.localization.has_language(lang)
    ]
    if available_langs:
        ly.gap_y(3)
        if (tw.btn_secondary | tw.btn_sm)(imgui.button)(f"+ 添加语言##{id_suffix}"):
            imgui.open_popup(f"add_language_popup{suffix}")

        if imgui.begin_popup(f"add_language_popup{suffix}"):
            for lang in available_langs:
                label = LANGUAGE_LABELS.get(lang, lang)
                if imgui.selectable(label)[0]:
                    item.localization.languages[lang] = {
                        "name": "",
                        "description": "",
                    }
            imgui.end_popup()


def _draw_language_block(
    data: dict,
    label: str,
    suffix: str,
    lang: str,
    *,
    is_primary: bool = False,
) -> bool:
    """绘制单个语言的名称+描述输入块

    Args:
        data: {"name": str, "description": str}
        label: 语言显示名
        suffix: ID 后缀
        lang: 语言 key
        is_primary: 是否主语言

    Returns:
        True if user clicked delete (non-primary only)
    """
    removed = False

    # 语言标签行
    if is_primary:
        tw.text_parchment_200(imgui.text)(f"{label}")
        imgui.same_line()
        tw.text_faint(imgui.text)("(主语言)")
    else:
        tw.text_parchment_200(imgui.text)(f"{label}")
        imgui.same_line()
        if (tw.btn_danger | tw.btn_xs)(imgui.button)(f"删除##{lang}{suffix}"):
            removed = True

    ly.gap_y(1)

    # 名称输入
    tw.text_muted(imgui.text)("名称")
    ly.gap_y(0.5)
    with tw.input_default:
        imgui.push_item_width(-1)
        changed, val = imgui.input_text(
            f"##{lang}_name{suffix}", data["name"], 256,
        )
        if changed:
            data["name"] = val
        imgui.pop_item_width()

    ly.gap_y(1.5)

    # 描述输入
    tw.text_muted(imgui.text)("描述")
    ly.gap_y(0.5)
    with tw.input_default:
        imgui.push_item_width(-1)
        changed, val = imgui.input_text_multiline(
            f"##{lang}_desc{suffix}",
            data["description"],
            1024,
            height=sz(16),  # 64px
        )
        if changed:
            data["description"] = val
        imgui.pop_item_width()

    return removed


# =============================================================================
# 导出
# =============================================================================

__all__ = ["draw_presentation_panel"]
