# -*- coding: utf-8 -*-
"""通用编辑器工具函数

提供通用的编辑器方法，如基本属性、属性编辑器、验证错误显示等。
所有函数均为模块级，不依赖 GUI god object。
"""

from enum import Enum
from typing import Any

from ui import imgui_shim as imgui

from ui.styles import gap_l, gap_m, gap_s  # type: ignore
from ui.styles import text_secondary, text_warning, text_error
from ui.layout import tooltip

from attribute_data import ATTRIBUTE_TRANSLATIONS, ATTRIBUTE_DESCRIPTIONS
from constants import (
    ARMOR_CLASS_LABELS,
    ARMOR_FRAGMENT_LABELS,
    ARMOR_SLOT_LABELS,
    LANGUAGE_LABELS,
    PRIMARY_LANGUAGE,
    RARITY_LABELS,
    TIER,
    TIER_LABELS,
)
from models import Armor, Weapon


# =============================================================================
# 模块级工具函数 (已有)
# =============================================================================

def draw_indented_separator() -> None:
    """绘制缩进分隔线"""
    style = imgui.get_style()
    spacing = style.item_spacing.y
    imgui.dummy(0, spacing * 0.3)
    cursor_x, cursor_y = imgui.get_cursor_screen_pos()
    max_x = cursor_x + imgui.get_content_region_available_width()
    color = style.colors[imgui.COLOR_SEPARATOR]
    draw_list = imgui.get_window_draw_list()
    draw_list.add_line(
        cursor_x, cursor_y, max_x, cursor_y, imgui.get_color_u32_rgba(*color)
    )
    imgui.dummy(0, spacing * 0.3)


def get_attr_display(attr: str, lang: str = "Chinese") -> tuple[str, str]:
    """获取属性的本地化显示名称和说明

    Args:
        attr: 属性键名 (如 "Hit_Chance")
        lang: 语言 (默认 "Chinese")

    Returns:
        (显示名称, 详细说明) 元组
    """
    trans = ATTRIBUTE_TRANSLATIONS.get(attr, {})
    name = trans.get(lang) or trans.get("Chinese") or trans.get("English") or attr

    desc_dict = ATTRIBUTE_DESCRIPTIONS.get(attr, {})
    desc = desc_dict.get(lang) or desc_dict.get("Chinese") or desc_dict.get("English") or ""

    return (name, desc)


# =============================================================================
# 通用 UI 组件
# =============================================================================

def draw_enum_combo(
    label: str, current_value: Any,
    options: list, labels: dict, tooltip_text: str = ""
) -> Any:
    """通用枚举下拉框"""
    current_label = str(labels.get(current_value, current_value))
    new_value = current_value

    if current_value not in options:
        options = list(options) + [current_value]

    if imgui.begin_combo(label, current_label):
        for opt in options:
            display = str(labels.get(opt, opt))
            if imgui.selectable(display, opt == current_value)[0]:
                new_value = opt
        imgui.end_combo()

    if tooltip_text and imgui.is_item_hovered():
        imgui.set_tooltip(tooltip_text)

    return new_value


def draw_mode_combo(
    label: str, current_enum: Enum, enum_class: type[Enum],
    labels: dict, options: list | None = None, tooltip_text: str = ""
) -> Enum:
    """Enum 类型的下拉框

    Args:
        label: imgui 标签
        current_enum: 当前 Enum 值
        enum_class: Enum 类型
        labels: {Enum成员: 显示文本} 映射
        options: 可选的选项列表（Enum成员），默认为所有成员
        tooltip_text: 提示文本
    Returns:
        选中的 Enum 值
    """
    if options is None:
        options = list(enum_class)

    current_label = labels.get(current_enum, str(current_enum.value))
    new_value = current_enum

    if imgui.begin_combo(label, current_label):
        for opt in options:
            display = labels.get(opt, str(opt.value))
            if imgui.selectable(display, opt == current_enum)[0]:
                new_value = opt
        imgui.end_combo()

    if tooltip_text and imgui.is_item_hovered():
        imgui.set_tooltip(tooltip_text)

    return new_value


def draw_inline_checkbox(
    label: str, value: bool, tooltip_text: str = ""
) -> bool:
    """绘制内联复选框"""
    changed, new_value = imgui.checkbox(label, value)
    if tooltip_text and imgui.is_item_hovered():
        imgui.set_tooltip(tooltip_text)
    return new_value if changed else value


def draw_validation_errors(errors: list[str]) -> None:
    """显示验证错误 (standalone, 不依赖 gui)"""
    if not errors:
        return
    draw_indented_separator()
    imgui.text("消息:")

    for error in errors:
        if error.endswith("):"):
            continue
        content = error.lstrip()

        if content.startswith("• WARNING:"):
            imgui.text("  ")
            imgui.same_line()
            text_warning("!")
            imgui.same_line()
            text_warning(content[10:].strip())
        elif content.startswith("•"):
            imgui.text("  ")
            imgui.same_line()
            text_error("X")
            imgui.same_line()
            text_error(content[1:].strip())
        else:
            imgui.text("  ")
            imgui.same_line()
            text_error("X")
            imgui.same_line()
            text_error(error)


# =============================================================================
# 基本属性编辑器
# =============================================================================

def draw_basic_properties(
    item: Weapon | Armor, id_suffix: str,
    slot_labels: dict, material_labels: dict
) -> None:
    """绘制物品基本属性"""
    type_name = "武器" if id_suffix == "weapon" else "装备"

    # 系统ID - 占满宽度
    imgui.text(f"{type_name}系统ID")
    imgui.same_line()
    text_secondary(f"(生成ID: {item.id})")
    imgui.push_item_width(-1)
    changed, item.name = imgui.input_text(f"##{id_suffix}_sysid", item.name, 256)
    imgui.pop_item_width()
    if imgui.is_item_hovered():
        imgui.set_tooltip(
            "用来让游戏识别该物品的内部名称，不向玩家展示。\n请确保ID尽可能独特，以免与其他Mod冲突！"
        )

    imgui.dummy(0, 4)

    # 使用两列布局
    col_width = imgui.get_content_region_available_width() / 2 - 8

    imgui.columns(2, f"basic_props_{id_suffix}", border=False)
    imgui.set_column_width(0, col_width)

    # 左列
    imgui.push_item_width(-1)
    imgui.text("槽位")
    new_slot = draw_enum_combo(
        f"##slot_{id_suffix}", item.slot, list(slot_labels.keys()), slot_labels
    )
    if new_slot != item.slot:
        item.slot = new_slot
        if not item.needs_char_texture():
            item.textures.clear_char()
        if not item.needs_left_texture():
            item.textures.clear_left()

    imgui.text("等级")
    item.tier = draw_enum_combo(
        f"##tier_{id_suffix}", item.tier, TIER, TIER_LABELS
    )

    imgui.text("材料")
    item.mat = draw_enum_combo(
        f"##mat_{id_suffix}",
        item.mat,
        list(material_labels.keys()),
        material_labels,
    )

    if isinstance(item, Armor):
        imgui.text("护甲类别")
        item.armor_class = draw_enum_combo(
            f"##class_{id_suffix}",
            item.armor_class,
            list(ARMOR_CLASS_LABELS.keys()),
            ARMOR_CLASS_LABELS,
        )
    imgui.pop_item_width()

    # 右列
    imgui.next_column()
    imgui.push_item_width(-1)

    from constants import TAG_LABELS
    imgui.text("标签")
    new_tags = draw_enum_combo(
        f"##tags_{id_suffix}_{item.name}",
        item.tags,
        list(TAG_LABELS.keys()),
        TAG_LABELS,
    )
    if new_tags != item.tags:
        item.tags = new_tags
        item.rarity = (
            "Unique"
            if new_tags in ["unique", "special", "special exc"]
            else "Common"
        )

    imgui.text("稀有度")
    rarity_label = RARITY_LABELS.get(item.rarity, item.rarity)
    imgui.input_text(
        f"##rarity_{id_suffix}", rarity_label, 256, flags=imgui.INPUT_TEXT_READ_ONLY
    )
    if imgui.is_item_hovered():
        imgui.set_tooltip("由标签自动决定")

    imgui.text("价格")
    changed, item.price = imgui.input_int(f"##price_{id_suffix}", item.price)

    imgui.text("最大耐久")
    changed, item.max_duration = imgui.input_int(
        f"##dur_{id_suffix}", item.max_duration
    )
    imgui.pop_item_width()

    imgui.columns(1)

    # 武器距离（仅武器，弓弩专用）
    if isinstance(item, Weapon):
        if item.slot in ["bow", "crossbow"]:
            imgui.push_item_width(120)
            imgui.text("攻击距离")
            changed, item.rng = imgui.input_int(f"##rng_{id_suffix}", item.rng)
            if changed:
                item.rng = max(0, min(255, item.rng))
            imgui.pop_item_width()
            if imgui.is_item_hovered():
                imgui.set_tooltip(
                    "决定武器的基础攻击距离（游戏内部字段）\n类型: byte (0-255)"
                )
        else:
            item.rng = 1

    draw_indented_separator()

    # 布尔属性 - 横向排列
    imgui.text("特殊属性")
    item.fireproof = draw_inline_checkbox(
        f"防火##{id_suffix}", item.fireproof, "未被拾取时是否会被火焰摧毁"
    )
    imgui.same_line(spacing=gap_l())
    item.no_drop = draw_inline_checkbox(
        f"不可掉落##{id_suffix}", item.no_drop, "可能无法从宝箱中获取"
    )
    if isinstance(item, Armor):
        imgui.same_line(spacing=gap_l())
        item.is_open = draw_inline_checkbox(
            f"开放式##{id_suffix}",
            item.is_open,
            "装备是否为开放式设计（如头盔的面甲）",
        )


# =============================================================================
# 属性编辑器
# =============================================================================

def draw_attributes_editor(
    item: Weapon | Armor,
    attribute_groups: dict[str, list[str]], id_suffix: str
) -> None:
    """绘制属性编辑器 - 使用两列布局优化对齐"""
    font_size = imgui.get_font_size()

    for group_name, attributes in attribute_groups.items():
        tree_id = f"{group_name}##{id_suffix}_attr"
        if imgui.tree_node(tree_id):
            # 使用两列布局：输入框 | 属性名，确保对齐
            imgui.columns(2, f"attr_cols_{tree_id}", border=False)
            input_col_width = 120 + (font_size - 14) * 6
            imgui.set_column_width(0, input_col_width)

            for attr in attributes:
                desc_name, desc_detail = get_attr_display(attr)
                if not desc_name:
                    desc_name = attr

                val = item.attributes.get(attr, 0)

                # 第一列：输入框
                imgui.push_item_width(-1)
                input_id = f"##{attr}_{id_suffix}"
                changed, new_val = imgui.input_int(
                    input_id, val, step=1, step_fast=10
                )
                imgui.pop_item_width()

                if changed:
                    item.attributes[attr] = new_val

                # 第二列：属性名称
                imgui.next_column()
                imgui.text(desc_name)

                # tooltip 显示详细说明
                tooltip_text = ""
                if desc_detail:
                    tooltip_text = desc_detail
                tooltip(tooltip_text)

                imgui.next_column()

            imgui.columns(1)
            imgui.tree_pop()


# =============================================================================
# 拆解材料编辑器
# =============================================================================

def draw_fragments_editor(armor: Armor) -> None:
    """绘制拆解材料编辑器"""
    imgui.text("设置装备拆解后可获得的材料")
    tooltip("拆解装备时可能获得的材料碎片数量")

    for frag_type in ARMOR_FRAGMENT_LABELS:
        frag_label = ARMOR_FRAGMENT_LABELS.get(frag_type, frag_type)
        val = armor.fragments.get(frag_type, 0)

        imgui.push_item_width(100)
        changed, new_val = imgui.input_int(
            f"##{frag_type}", val, step=1, step_fast=5
        )
        imgui.pop_item_width()

        if new_val < 0:
            new_val = 0
            changed = True
        elif new_val > 255:
            new_val = 255
            changed = True

        if changed:
            if new_val == 0:
                armor.fragments.pop(frag_type, None)
            else:
                armor.fragments[frag_type] = new_val

        imgui.same_line()
        imgui.text(frag_label)


# =============================================================================
# 本地化编辑器
# =============================================================================

def draw_localization_editor(
    item: Weapon | Armor, id_suffix: str
) -> None:
    """绘制本地化编辑器

    使用 imgui.get_font_size() 替代旧 self.font_size。
    """
    suffix = f"_{id_suffix}"
    font_size = imgui.get_font_size()

    # 语言添加器
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
        f"##{PRIMARY_LANGUAGE}_name{suffix}", primary_data["name"], 256
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
            f"##{lang}_desc{suffix}", data["description"], 1024, height=desc_height
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

__all__ = [
    "draw_indented_separator",
    "get_attr_display",
    "draw_enum_combo",
    "draw_mode_combo",
    "draw_inline_checkbox",
    "draw_validation_errors",
    "draw_basic_properties",
    "draw_attributes_editor",
    "draw_fragments_editor",
    "draw_localization_editor",
]
