# -*- coding: utf-8 -*-
"""通用编辑器工具函数

提供通用的编辑器方法，如基本属性、属性编辑器、验证错误显示等。
所有函数均为模块级，不依赖 GUI god object。
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ui import imgui_shim as imgui
from ui import tw
from ui import layout as ly
from ui.layout import tooltip
from ui.scale import Sp, dp
from ui.state import dpi_scale

from data.attributes import ATTRIBUTE_TRANSLATIONS, ATTRIBUTE_DESCRIPTIONS
from constants import (
    ARMOR_CLASS_LABELS,
    ARMOR_FRAGMENT_LABELS,
    LANGUAGE_LABELS,
    PRIMARY_LANGUAGE,
    RARITY_LABELS,
    TIER_LABELS,
)
from core.models import Armor, Weapon


# =============================================================================
# 卡片布局常量与辅助 (公共)
# =============================================================================

CARD_GAP = Sp.S3        # 卡片之间的间距 (12px)
CARD_HEADING_GAP = Sp.S2  # 标题与内容间距 (8px)
BREAKPOINT_PX = 1100    # 响应式断点: 内容区 > 此值时启用双列

# 卡片样式 — p_4 = 16px 内边距, bg_elevated + 圆角
CARD_STYLE = tw.bg_elevated | tw.child_rounded_md | tw.p_4


def card_heading(title: str) -> None:
    """卡片内标题 — 紫色强调条 + 文字

    Tailwind: border-l-2 border-crystal-500 pl-2 text-crystal-400 text-sm
    """
    screen_x, screen_y = imgui.get_cursor_screen_pos()
    text_h = imgui.get_font_size()
    bar_w = 2 * dpi_scale()
    bar_gap = dp(Sp.S1_5)

    draw_list = imgui.get_window_draw_list()
    draw_list.add_rect_filled(
        screen_x, screen_y,
        screen_x + bar_w, screen_y + text_h,
        imgui.get_color_u32_rgba(*tw.CRYSTAL_500),
    )

    cursor = imgui.get_cursor_pos()
    imgui.set_cursor_pos((cursor[0] + bar_w + bar_gap, cursor[1]))
    tw.text_accent(imgui.text)(title)
    ly.gap_y(CARD_HEADING_GAP)


def draw_card_section(
    title: str,
    draw_fn: Callable[[], None],
    *,
    height: float = 0,
) -> None:
    """渲染一张独立的 section 卡片 (自带 child 容器 + 样式).

    结构: Card (begin_child) → heading + draw_fn()

    Args:
        title: 卡片标题
        draw_fn: 内容渲染回调 (无参数, 需要参数请用 lambda 包裹)
        height: 0 = AutoResizeY; >0 = 固定高度 (用于填充剩余空间)
    """
    with CARD_STYLE:
        avail_w = imgui.get_content_region_available().x
        wf = imgui.WINDOW_NO_SCROLLBAR
        if height > 0:
            cf = int(imgui.ChildFlags.AlwaysUseWindowPadding)
        else:
            cf = int(imgui.ChildFlags.AlwaysUseWindowPadding) | int(imgui.ChildFlags.AutoResizeY)

        imgui.begin_child(f"##card_{title}", width=avail_w, height=height, child_flags=cf, window_flags=wf)
        card_heading(title)
        draw_fn()
        imgui.end_child()


def draw_card_content(
    title: str,
    draw_fn: Callable[[], None],
) -> None:
    """渲染卡片内容 (标题 + 内容), 不包含外层 child 容器.

    用于 equal_height_row 的 col(style=CARD_STYLE) 内部,
    col child 本身已是卡片容器.
    """
    card_heading(title)
    draw_fn()


def draw_validation_card(errors: list[str], id_suffix: str = "") -> None:
    """验证错误卡片 — bg_app 背景 + card 容器 + 错误列表

    Args:
        errors: 验证错误列表
        id_suffix: card ID 后缀, 避免 ID 冲突
    """
    if not errors:
        return
    card_id = f"##validation_errors{('_' + id_suffix) if id_suffix else ''}"
    with tw.bg_app | tw.rounded_md | tw.p_3:
        with ly.card(card_id) as _state:
            draw_validation_errors(errors)


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
    options: list[Any], labels: dict[Any, str], tooltip_text: str = ""
) -> Any:
    """通用枚举下拉框"""
    current_label = str(labels.get(current_value, current_value))
    new_value = current_value

    if current_value not in options:
        options = list(options) + [current_value]

    with tw.input_default:
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
    labels: dict[Any, str], options: list[Any] | None = None, tooltip_text: str = ""
) -> Enum:
    """枚举类型的下拉框"""
    if options is None:
        options = list(enum_class)

    current_label = labels.get(current_enum, str(current_enum.value))
    new_value = current_enum

    with tw.input_default:
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
    with tw.input_default:
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


# =============================================================================
# 基本属性编辑器 — field_flow 流式布局
# =============================================================================

def draw_basic_properties(
    item: Weapon | Armor, id_suffix: str,
    slot_labels: dict[Any, str], material_labels: dict[Any, str]
) -> None:
    """绘制物品基本属性

    Tailwind: flex flex-wrap gap-2 → field_flow
    ID 较宽 (40tw=160px), 其他字段自然宽度
    """
    from ui.fields import field_flow, enum_field, int_field, readonly_field
    from constants import TAG_LABELS

    type_name = "武器" if id_suffix == "weapon" else "装备"

    # 1. 系统ID — 单独一行, 占满宽度
    with ly.hstack(gap=Sp.S2):
        with ly.slot():
            tw.text_muted(imgui.text)(f"{type_name}系统ID")
        with ly.slot():
            tw.text_faint(imgui.text)(f"(生成ID: {item.id})")
    ly.gap_y(Sp.S0_5)
    with tw.input_default:
        imgui.push_item_width(-1)
        _changed, item.name = imgui.input_text(f"##{id_suffix}_sysid", item.name, 256)
        imgui.pop_item_width()
    if imgui.is_item_hovered():
        imgui.set_tooltip(
            "用来让游戏识别该物品的内部名称，不向玩家展示。\n请确保ID尽可能独特，以免与其他Mod冲突！"
        )

    ly.gap_y(Sp.S3)

    # 2. 主要属性 — field_flow 自动换行
    with field_flow(gap=Sp.S2, row_gap=Sp.S2, default_width=Sp.S28):
        # 槽位
        ch, new_slot = enum_field(
            "槽位", f"##slot_{id_suffix}",
            item.slot, slot_labels,
            width=Sp.S28,
        )
        if ch:
            item.slot = new_slot
            if not item.needs_char_texture():
                item.textures.clear_char()
            if not item.needs_left_texture():
                item.textures.clear_left()

        # 等级
        ch, new_tier = enum_field(
            "等级", f"##tier_{id_suffix}",
            item.tier, TIER_LABELS,
            width=Sp.S20,
        )
        if ch:
            item.tier = new_tier

        # 材料
        ch, new_mat = enum_field(
            "材料", f"##mat_{id_suffix}",
            item.mat, material_labels,
            width=Sp.S28,
        )
        if ch:
            item.mat = new_mat

        # 护甲类别 (仅护甲)
        if isinstance(item, Armor):
            ch, new_ac = enum_field(
                "护甲类别", f"##class_{id_suffix}",
                item.armor_class, ARMOR_CLASS_LABELS,
                width=Sp.S28,
            )
            if ch:
                item.armor_class = new_ac

        # 标签
        ch, new_tags = enum_field(
            "标签", f"##tags_{id_suffix}_{item.name}",
            item.tags, TAG_LABELS,
            width=Sp.S28,
        )
        if ch:
            item.tags = new_tags
            item.rarity = (
                "Unique"
                if new_tags in ["unique", "special", "special exc"]
                else "Common"
            )

        # 稀有度 (只读)
        rarity_label = RARITY_LABELS.get(item.rarity, item.rarity)
        readonly_field(
            "稀有度", rarity_label,
            width=Sp.S24,
            tooltip_text="由标签自动决定",
        )

        # 价格
        ch, new_price = int_field(
            "价格", f"##price_{id_suffix}",
            item.price, width=Sp.S24,
        )
        if ch:
            item.price = new_price

        # 最大耐久
        ch, new_dur = int_field(
            "最大耐久", f"##dur_{id_suffix}",
            item.max_duration, width=Sp.S24,
        )
        if ch:
            item.max_duration = new_dur

        # 攻击距离 (仅弓弩)
        if isinstance(item, Weapon):
            if item.slot in ["bow", "crossbow"]:
                ch, new_rng = int_field(
                    "攻击距离", f"##rng_{id_suffix}",
                    item.rng, width=Sp.S24,
                    vmin=0, vmax=255,
                    tooltip_text="决定武器的基础攻击距离（游戏内部字段）\n类型: byte (0-255)",
                )
                if ch:
                    item.rng = new_rng
            else:
                item.rng = 1

    ly.gap_y(Sp.S3)
    imgui.separator()
    ly.gap_y(Sp.S2)

    # 3. 特殊属性 — 横向排列
    tw.text_muted(imgui.text)("特殊属性")
    ly.gap_y(Sp.S1)
    with ly.hstack(gap=Sp.S5):
        with ly.slot():
            item.fireproof = draw_inline_checkbox(
                f"防火##{id_suffix}", item.fireproof, "未被拾取时是否会被火焰摧毁"
            )
        with ly.slot():
            item.no_drop = draw_inline_checkbox(
                f"不可掉落##{id_suffix}", item.no_drop, "可能无法从宝箱中获取"
            )
        if isinstance(item, Armor):
            with ly.slot():
                item.is_open = draw_inline_checkbox(
                    f"开放式##{id_suffix}",
                    item.is_open,
                    "装备是否为开放式设计（如头盔的面甲）",
                )


# =============================================================================
# 属性编辑器 — 响应式全网格
# =============================================================================

from ui.editors.attr_table import (
    draw_attr_table as _draw_attr_table,
    draw_attribute_full_grid as _draw_attribute_full_grid,
    get_label_width as _get_label_width,
    MAX_COLS as _MAX_COLS,
    DOT_ALPHA as _DOT_ALPHA,
)


def draw_attributes_editor(
    item: Weapon | Armor,
    attribute_groups: dict[str, list[str]], id_suffix: str
) -> None:
    """绘制属性编辑器 — 响应式全网格

    每组: 标题 + 紧凑 N×3 表格 (label | input) × 3
    与混合物品编辑器的 stats_panel 风格一致。
    """
    _draw_attribute_full_grid(attribute_groups, item.attributes, id_suffix)


# =============================================================================
# 拆解材料编辑器 — 紧凑网格
# =============================================================================

def draw_fragments_editor(armor: Armor) -> None:
    """绘制拆解材料编辑器

    Tailwind: grid grid-cols-N gap-x-auto gap-y-0.5
    与属性编辑器相同的紧凑表格风格。
    """
    tw.text_muted(imgui.text)("设置装备拆解后可获得的材料")
    tooltip("拆解装备时可能获得的材料碎片数量")
    ly.gap_y(Sp.S1)

    frag_types = list(ARMOR_FRAGMENT_LABELS.keys())
    frag_labels = ARMOR_FRAGMENT_LABELS

    label_w = _get_label_width()
    input_w = dp(Sp.S20)
    cell_pad_y = dp(Sp.S0_5)
    min_pad_x = dp(Sp.S0_5)

    avail_w = imgui.get_content_region_available_width()
    min_col_w = label_w + input_w + min_pad_x * 4
    num_cols = max(1, min(_MAX_COLS, int(avail_w / min_col_w)))
    num_gaps = 2 * num_cols - 1
    cell_pad_x = max(min_pad_x, (avail_w - num_cols * (label_w + input_w)) / (num_gaps * 2))

    table_cols = num_cols * 2

    imgui.push_style_var(imgui.STYLE_CELL_PADDING, (cell_pad_x, cell_pad_y))
    flags = imgui.TABLE_SIZING_FIXED_FIT | imgui.TABLE_NO_BORDERS_IN_BODY

    try:
        if not imgui.begin_table("##frags", table_cols, flags):
            return

        try:
            for i in range(num_cols):
                imgui.table_setup_column(f"##fl{i}", imgui.TABLE_COLUMN_WIDTH_FIXED, label_w)
                imgui.table_setup_column(f"##fi{i}", imgui.TABLE_COLUMN_WIDTH_FIXED, input_w)

            draw_list = imgui.get_window_draw_list()
            dot_r = 1.5 * dpi_scale()
            dot_color = imgui.get_color_u32_rgba(0.5, 0.5, 0.6, _DOT_ALPHA)

            with tw.input_default:
                for i, frag_type in enumerate(frag_types):
                    if i % num_cols == 0:
                        imgui.table_next_row()

                    val = armor.fragments.get(frag_type, 0)
                    display_name = frag_labels.get(frag_type, frag_type)

                    # --- Label column ---
                    imgui.table_next_column()
                    imgui.align_text_to_frame_padding()

                    cx, cy = imgui.get_cursor_screen_pos()
                    frame_h = imgui.get_frame_height()
                    draw_list.add_circle_filled(
                        (cx + dot_r, cy + frame_h * 0.5),
                        dot_r, dot_color,
                    )

                    text_w = imgui.calc_text_size(display_name).x
                    offset = label_w - text_w
                    if offset > 0:
                        cursor = imgui.get_cursor_pos()
                        imgui.set_cursor_pos((cursor[0] + offset, cursor[1]))

                    label_style = tw.text_faint if val == 0 else tw.text_muted
                    label_style(imgui.text)(display_name)

                    # --- Input column ---
                    imgui.table_next_column()
                    imgui.set_next_item_width(-1)

                    changed, new_val = imgui.input_int(f"##{frag_type}", val, 0, 0)

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

        finally:
            imgui.end_table()
    finally:
        imgui.pop_style_var()


# =============================================================================
# 本地化编辑器 — Tab 切换语言
# =============================================================================

@dataclass
class _LocTabState:
    """本地化编辑器 Tab 状态"""
    index: int = 0

_loc_tab_states: dict[str, _LocTabState] = {}


def _get_loc_tab_state(id_suffix: str) -> _LocTabState:
    if id_suffix not in _loc_tab_states:
        _loc_tab_states[id_suffix] = _LocTabState()
    return _loc_tab_states[id_suffix]


def draw_localization_editor(item: Any, id_suffix: str) -> None:
    """本地化编辑器 — Tab 切换语言, 名称 + 描述输入

    适用于所有拥有 localization: ItemLocalization 属性的物品
    (Weapon / Armor / HybridItemV2)。

    Tab 行: [中文] [Deutsch] ... [+] [删除]
    编辑区: 名称 + 描述
    描述框自动填充剩余高度 (在卡片内部使用 get_content_region_available)。
    """
    suffix = f"_{id_suffix}"

    # 确保主语言存在
    if not item.localization.has_language(PRIMARY_LANGUAGE):
        item.localization.languages[PRIMARY_LANGUAGE] = {
            "name": "",
            "description": "",
        }

    # 收集当前已有的语言 (按 LANGUAGE_LABELS 顺序)
    active_langs: list[str] = []
    for lang in LANGUAGE_LABELS:
        if item.localization.has_language(lang):
            active_langs.append(lang)
    if not active_langs:
        active_langs = [PRIMARY_LANGUAGE]

    # Tab 状态
    state = _get_loc_tab_state(id_suffix)
    if state.index >= len(active_langs):
        state.index = 0

    # === Tab 行: 圆角按钮 + 间距 ===
    for i, lang in enumerate(active_langs):
        if i > 0:
            imgui.same_line(0, dp(Sp.S1))
        is_selected = (i == state.index)
        tab_label = LANGUAGE_LABELS.get(lang, lang)

        style = tw.btn_primary | tw.btn_xs if is_selected else tw.btn_secondary | tw.btn_xs
        if style(imgui.button)(f"{tab_label}##{id_suffix}_tab_{i}"):
            state.index = i

    # [+] 添加语言
    available_langs = [l for l in LANGUAGE_LABELS if not item.localization.has_language(l)]
    if available_langs:
        imgui.same_line(0, dp(Sp.S1))
        if (tw.btn_secondary | tw.btn_xs)(imgui.button)(f"+##{id_suffix}_add"):
            imgui.open_popup(f"add_lang{suffix}")
        if imgui.begin_popup(f"add_lang{suffix}"):
            for lang in available_langs:
                label = LANGUAGE_LABELS.get(lang, lang)
                if imgui.selectable(label)[0]:
                    item.localization.languages[lang] = {"name": "", "description": ""}
            imgui.end_popup()

    # [删除] 非主语言
    current_lang = active_langs[state.index]
    is_primary = (current_lang == PRIMARY_LANGUAGE)
    lang_removed = False

    if not is_primary:
        imgui.same_line(0, dp(Sp.S1))
        if (tw.btn_danger | tw.btn_xs)(imgui.button)(f"删除##{id_suffix}_del"):
            lang_removed = True

    ly.gap_y(Sp.S2)

    # === 编辑区 ===
    data = item.localization.languages.get(current_lang)
    if data is not None and not lang_removed:
        # 名称
        tw.text_muted(imgui.text)("名称")
        ly.gap_y(Sp.S0_5)
        with tw.input_default:
            imgui.push_item_width(-1)
            changed, val = imgui.input_text(
                f"##{current_lang}_name{suffix}", data["name"], 256,
            )
            if changed:
                data["name"] = val
            imgui.pop_item_width()

        ly.gap_y(Sp.S1_5)

        # 描述
        tw.text_muted(imgui.text)("描述")
        ly.gap_y(Sp.S0_5)

        # 自动计算描述框高度: 填充剩余可用空间
        # 在 equal_height_row 中，这会自动拉伸以匹配另一列的高度
        remaining_h = imgui.get_content_region_available().y
        desc_h = max(dp(Sp.S24), remaining_h - dp(Sp.S1))  # 最小 96px

        with tw.input_default:
            changed, val = imgui.input_text_multiline(
                f"##{current_lang}_desc{suffix}",
                data["description"],
                1024,
                width=-1,
                height=desc_h,
            )
            if changed:
                data["description"] = val

    # 延迟删除
    if lang_removed:
        del item.localization.languages[current_lang]
        state.index = max(0, state.index - 1)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 卡片布局
    "CARD_GAP",
    "CARD_HEADING_GAP",
    "BREAKPOINT_PX",
    "CARD_STYLE",
    "card_heading",
    "draw_card_section",
    "draw_card_content",
    "draw_validation_card",
    # 工具函数
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
