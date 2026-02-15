# -*- coding: utf-8 -*-
"""贴图编辑器模块 — 统一 2 列布局

所有贴图区域均采用一致的 2 列布局：
- 护甲: 左列=默认/男性, 右列=女性, 每列 3 行 (站立0/站立1/休息)
- 武器: 左列=右手(默认), 右列=左手(或占位)
- 物品栏+战利品: 左列=物品栏, 右列=战利品
- 画布: 正方形, 宽度=列宽
"""

import os
from typing import Callable, Union

from ui import imgui_shim as imgui

from ui.state import state as ui_state

from constants import (
    CHARACTER_MODELS,
    GAME_FPS,
)
from core.models import Armor, Weapon
from core.hybrid_item import HybridItemV2
from core.specs import (
    WeaponCharTexture, MultiPoseCharTexture, NoCharTexture,
    AnimatedSlot, StaticSlot, LootSlot, loot_speed_to_preview_fps,
    equipment_pose_index,
    WeaponEquip, ArmorEquip,
)
from ui import tw
from ui import layout as ly
from ui.layout import tooltip
from ui.scale import Sp

# 任何拥有 textures: ItemTexturesV2 属性的物品
AnyItemWithTextures = Union[Weapon, Armor, HybridItemV2]

# 2 列布局的列间距
_COL_GAP = Sp.S3

# 画布边框样式 — 在明亮棋盘格画布与深色卡片间提供可见分界线,
# 抵抗瞳孔收缩导致的明暗适应边界“消失”问题
_canvas_frame = tw.border_abyss_600 | tw.child_border_size(1) | tw.child_rounded_sm

def _get_pose_index(item: AnyItemWithTextures) -> int:
    """获取贴图编辑器姿势索引 (0=单手, 1=双手)

    统一处理旧 model (Weapon/Armor) 和新 model (HybridItemV2):
    - Weapon: 按 weapon_type 从 weapon_hands.json 查询
    - Armor:  仅 shield 有 WeaponCharTexture, 固定 pose 0
    - HybridItemV2: 按 equipment 变体查询
    """
    from constants.game import get_weapon_hands

    match item:
        case Weapon():
            return get_weapon_hands(item.slot).pose_index
        case Armor():
            return 0  # shield (唯一有 WeaponCharTexture 的护甲)
        case _:  # HybridItemV2
            return equipment_pose_index(item.equipment)

# ============================================================================
# 内部函数 - 物品栏/战利品 贴图
# ============================================================================


def _draw_inventory_column(
    paths: list[str],
    id_suffix: str,
    canvas_size: int,
    importer: Callable[[str], str] | None = None,
) -> list[str]:
    """绘制物品栏贴图 (单列内容)

    Tailwind: flex flex-col gap-1
    """
    from ui.widgets import frame_strip, texture_preview

    tw.text_muted(imgui.text)("物品栏贴图")
    tooltip("多张贴图可表示不同耐久状态，排在后面的贴图代表更低耐久")

    paths, selected = frame_strip(
        f"{id_suffix}_inv",
        paths,
        animated=False,
        importer=importer,
        max_width=canvas_size,
    )

    if paths and 0 <= selected < len(paths) and paths[selected]:
        ly.gap_y(Sp.S1)
        with _canvas_frame:
            texture_preview(
                f"{id_suffix}_inv_preview",
                paths[selected],
                size=(canvas_size, canvas_size),
            )

    return paths


def _draw_loot_column(
    loot: LootSlot,
    id_suffix: str,
    canvas_size: int,
    importer: Callable[[str], str] | None = None,
) -> None:
    """绘制战利品贴图 (单列内容)

    Tailwind: flex flex-col gap-1
    """
    from ui.widgets import frame_strip, texture_preview

    tw.text_muted(imgui.text)("战利品贴图*")
    tooltip("战利品掉落时显示的贴图，支持动画")

    fps = loot_speed_to_preview_fps(loot.speed, GAME_FPS)

    new_paths, frame = frame_strip(
        f"{id_suffix}_loot",
        loot.paths,
        animated=True,
        fps=fps,
        importer=importer,
        max_width=canvas_size,
    )
    loot.paths = new_paths

    if loot.paths and 0 <= frame < len(loot.paths) and loot.paths[frame]:
        ly.gap_y(Sp.S1)
        with _canvas_frame:
            texture_preview(
                f"{id_suffix}_loot_preview",
                loot.paths[frame],
                size=(canvas_size, canvas_size),
            )

    if loot.is_animated:
        from ui.widgets import loot_speed_input
        loot.speed = loot_speed_input(id_suffix, loot.speed)


def _draw_inv_loot_columns(
    inv_paths: list[str],
    loot: LootSlot,
    id_suffix: str,
    importer: Callable[[str], str] | None = None,
) -> list[str]:
    """物品栏 + 战利品 2 列布局

    Tailwind: grid grid-cols-2 gap-3
    """
    with ly.columns(2, gap=_COL_GAP) as c:
        canvas_sz = int(c.col_width)

        with c.col(0):
            inv_paths = _draw_inventory_column(
                inv_paths, id_suffix, canvas_sz, importer
            )

        with c.col(1):
            _draw_loot_column(loot, id_suffix, canvas_sz, importer)

    return inv_paths



# ============================================================================
# 角色贴图编辑器 - 武器
# ============================================================================


def draw_weapon_char_textures(
    char: WeaponCharTexture,
    id_suffix: str,
    has_left: bool,
    pose_index: int = 0,
    importer: Callable[[str], str] | None = None,
) -> str:
    """绘制武器/盾牌手持贴图编辑器 — 2 列布局

    左列=右手(默认)，右列=左手(或占位提示)。
    画布为正方形，宽度填满列宽。

    Tailwind: grid grid-cols-2 gap-3

    Args:
        char: WeaponCharTexture 对象（会被原地修改）
        id_suffix: ID 后缀
        has_left: 是否需要左手贴图
        pose_index: 姿势索引 (0=单手, 1=双手)
        importer: 路径转换函数

    Returns:
        当前选中的模型 key
    """
    from ui.widgets import model_combo, frame_strip, origin_input, texture_preview

    is_weapon = id_suffix == "weapon"
    title = "手持状态贴图" if is_weapon else "穿戴状态贴图"

    # 标题行 + 模特选择
    tw.text_muted(imgui.text)(title)
    imgui.same_line()
    selected_model = model_combo(id_suffix, ui_state.selected_model)
    ui_state.selected_model = selected_model

    # 获取模型路径
    model_files = CHARACTER_MODELS.get(selected_model, [])
    model_path = (
        os.path.join("resources", model_files[pose_index])
        if pose_index < len(model_files) else None
    )

    ly.gap_y(Sp.S1)

    # 单列内容绘制函数
    def _draw_weapon_slot(label: str, slot: AnimatedSlot, slot_suffix: str, canvas_sz: int):
        tw.text_muted(imgui.text)(label)
        slot.paths, frame = frame_strip(
            f"{id_suffix}_{slot_suffix}",
            slot.paths,
            animated=True,
            importer=importer,
            max_width=canvas_sz,
        )
        if slot.paths and 0 <= frame < len(slot.paths):
            ly.gap_y(Sp.S1)
            with _canvas_frame:
                texture_preview(
                    f"{id_suffix}_{slot_suffix}_preview",
                    slot.paths[frame],
                    origin=slot.origin,
                    model_path=model_path,
                    size=(canvas_sz, canvas_sz),
                )
        slot.origin = origin_input(f"{id_suffix}_{slot_suffix}_origin", slot.origin)

    # 2 列布局
    with ly.columns(2, gap=_COL_GAP) as c:
        canvas_sz = int(c.col_width)

        with c.col(0):
            right_label = "右手/默认*" if has_left else "贴图*"
            _draw_weapon_slot(right_label, char.main, "main", canvas_sz)

        with c.col(1):
            if has_left:
                _draw_weapon_slot("左手*", char.left, "left", canvas_sz)
            else:
                tw.text_faint(imgui.text)("（无左手贴图）")

    return selected_model


# 姿势槽位元数据
_POSE_SLOTS = {
    # 男性/默认版
    "standing0": ("站立0 (男)", True),   # (标签, 是否必须)
    "standing1": ("站立1 (男)", False),
    "rest": ("休息 (男)", True),
    # 女性版
    "standing0_female": ("站立0 (女)", False),
    "standing1_female": ("站立1 (女)", False),
    "rest_female": ("休息 (女)", False),
}


def _draw_pose_slot(
    char: MultiPoseCharTexture,
    slot_name: str,
    id_suffix: str,
    model_path: str | None,
    canvas_size: int,
    importer: Callable[[str], str] | None = None,
) -> None:
    """绘制单个姿势槽位

    使用 MultiPoseCharTexture 的声明式规则：
    - resolve(): 获取实际显示的贴图和 fallback 来源
    - is_ui_enabled(): 判断是否启用编辑
    - clear_with_cascade(): 清除时级联清除依赖

    Args:
        canvas_size: 画布边长 (像素), 正方形画布
    """
    from ui.widgets import single_texture_input, origin_input, texture_preview

    label, required = _POSE_SLOTS[slot_name]
    slot: StaticSlot = getattr(char, slot_name)
    is_enabled = char.is_ui_enabled(slot_name)

    # 提前resolve获取fallback信息
    resolved_slot, fallback_from = char.resolve(slot_name)

    # 标签
    tw.text_muted(imgui.text)(label)
    if required:
        imgui.same_line()
        tw.text_blood_400(imgui.text)("*")
        tooltip("必填项")
    elif not is_enabled:
        # 禁用状态：显示原因
        requires = char.UI_ENABLE_REQUIRES.get(slot_name, ())
        missing = [r for r in requires if not getattr(char, r).has_texture()]
        imgui.same_line()
        if missing:
            missing_labels = [_POSE_SLOTS.get(m, (m,))[0] for m in missing]
            tw.text_muted(imgui.text)(f"(需先设置: {', '.join(missing_labels)})")
        else:
            tw.text_muted(imgui.text)("(禁用)")
    elif fallback_from:
        imgui.same_line()
        tw.text_muted(imgui.text)(f"(使用 {_POSE_SLOTS.get(fallback_from, (fallback_from,))[0]})")

    # 编辑按钮（禁用时显示占位按钮保持高度一致）
    if is_enabled:
        new_path = single_texture_input(
            f"{id_suffix}_{slot_name}",
            slot.path,
            importer=importer,
        )
        if new_path != slot.path:
            if new_path:
                slot.path = new_path
            else:
                # 清除时级联
                char.clear_with_cascade(slot_name)
    else:
        # 显示灰色占位按钮
        with tw.text_faint:
            single_texture_input(
                f"{id_suffix}_{slot_name}_disabled",
                "",
                importer=None,
            )

    # 预览（使用 resolve 获取实际显示的贴图） — 与编辑按钮间加间距
    if resolved_slot.has_texture():
        ly.gap_y(Sp.S1)
        with _canvas_frame:
            texture_preview(
                f"{id_suffix}_{slot_name}_preview",
                resolved_slot.path,
                origin=resolved_slot.origin,
                model_path=model_path,
                size=(canvas_size, canvas_size),
            )

    # Origin — 有自己的贴图时可编辑，fallback 时显示只读文本
    if slot.has_texture():
        slot.origin = origin_input(f"{id_suffix}_{slot_name}_origin", slot.origin)
    elif fallback_from and resolved_slot.has_texture():
        fallback_label = _POSE_SLOTS.get(fallback_from, (fallback_from,))[0]
        o = resolved_slot.origin
        tw.text_faint(imgui.text)(f"Origin (← {fallback_label})")
        tw.text_faint(imgui.text)(f"{o.x} X  {o.y} Y")


def draw_multi_pose_armor_textures(
    char: MultiPoseCharTexture,
    id_suffix: str,
    importer: Callable[[str], str] | None = None,
) -> str:
    """绘制多姿势护甲贴图编辑器 — 2 列布局

    左列=默认/男性 (站立0→站立1→休息)
    右列=女性 (站立0→站立1→休息)
    画布正方形，宽度填满列宽。去掉性别 Tab 切换。

    Tailwind: grid grid-cols-2 gap-3

    Args:
        char: MultiPoseCharTexture 对象（会被原地修改）
        id_suffix: ID 后缀
        importer: 路径转换函数

    Returns:
        当前选中的种族 key
    """
    from constants import get_model_key, CHARACTER_MODELS
    from ui.widgets import race_combo

    tw.text_muted(imgui.text)("穿戴状态贴图")

    # 模特种族选择
    imgui.same_line()
    selected_race = race_combo(id_suffix, ui_state.selected_race)
    ui_state.selected_race = selected_race

    ly.gap_y(Sp.S1)

    # 获取模型路径
    male_model_key = get_model_key(selected_race, False)
    female_model_key = get_model_key(selected_race, True)
    male_model_files = CHARACTER_MODELS.get(male_model_key, [])
    female_model_files = CHARACTER_MODELS.get(female_model_key, [])
    male_model_path = os.path.join("resources", male_model_files[0]) if male_model_files else None
    female_model_path = os.path.join("resources", female_model_files[0]) if female_model_files else None

    # 每列 3 行: standing0 → standing1 → rest
    male_slots = ["standing0", "standing1", "rest"]
    female_slots = ["standing0_female", "standing1_female", "rest_female"]

    with ly.columns(2, gap=_COL_GAP) as c:
        canvas_sz = int(c.col_width)

        with c.col(0):
            for i, slot_name in enumerate(male_slots):
                if i > 0:
                    ly.gap_y(Sp.S2)
                _draw_pose_slot(char, slot_name, id_suffix, male_model_path, canvas_sz, importer)

        with c.col(1):
            for i, slot_name in enumerate(female_slots):
                if i > 0:
                    ly.gap_y(Sp.S2)
                _draw_pose_slot(char, slot_name, id_suffix, female_model_path, canvas_sz, importer)

    return selected_race


# ============================================================================
# 主贴图编辑器函数
# ============================================================================


def draw_textures_editor(
    item: AnyItemWithTextures,
    id_suffix: str,
) -> None:
    """绘制贴图编辑器 - 统一 2 列布局

    结构:
    1. 角色穿戴贴图 (护甲: 男|女, 武器: 右手|左手)
    2. 物品栏 + 战利品 (左|右)

    Args:
        item: 物品对象（Weapon/Armor/HybridItemV2）
        id_suffix: ID 后缀（如 "weapon", "armor", "hybrid"）
    """
    # 穿戴/手持状态贴图
    match item.textures.char:
        case MultiPoseCharTexture() as char:
            draw_multi_pose_armor_textures(
                char, id_suffix, importer=ui_state.import_texture
            )
            ly.gap_y(Sp.S3)

        case WeaponCharTexture() as char:
            # 确定姿势索引：数据驱动，解决 hands ≠ sprite_hands 的武器类型
            pose_index = _get_pose_index(item)
            draw_weapon_char_textures(
                char,
                id_suffix,
                has_left=item.needs_left_texture(),
                pose_index=pose_index,
                importer=ui_state.import_texture,
            )
            ly.gap_y(Sp.S3)

        case NoCharTexture():
            pass

    # 物品栏 + 战利品 2 列
    item.textures.inventory = _draw_inv_loot_columns(
        item.textures.inventory,
        item.textures.loot,
        id_suffix,
        importer=ui_state.import_texture,
    )
