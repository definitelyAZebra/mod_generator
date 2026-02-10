# -*- coding: utf-8 -*-
"""原子 UI 控件

⚠️ LEGACY: 本文件中的大部分组件在 Tailwind 风格设计体系建立之前实现，
   未使用 tw tokens / ly helpers，而是直接调用 imgui API。
   未来重构时应改用 tw.* 和 ly.* 。

提供正交、可组合的 ImGui 风格控件：

帧控制:
    - tab_index: 标签页选择
    - animation_frame: 动画帧控制（自动播放）
    - slider_index: 滑块索引选择

Origin 编辑:
    - origin_input: Origin 坐标输入

贴图选择:
    - single_texture_input: 单张贴图选择
    - frame_strip: 帧条（多帧管理 + 帧选择）

速度设置:
    - loot_speed_input: 战利品动画速度

模型选择:
    - model_combo: 角色模型选择
    - race_combo: 种族选择

预览:
    - texture_preview: 贴图预览（支持 origin、模型叠加、图层选择）
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Callable, TYPE_CHECKING

from ui import imgui_shim as imgui

from constants import (
    CHAR_MODEL_ORIGIN,
    CHARACTER_MODEL_LABELS,
    CHARACTER_RACE_LABELS,
    CHARACTER_RACES,
    GAME_FPS,
)
from specs import Origin, AbsoluteFps, RelativeSpeed
from ui.dialogs import file_dialog
from ui import layout as ly
from ui.layout import tooltip
from ui.scale import Sp, dp
from ui import tw

if TYPE_CHECKING:
    from ui.canvas import InfiniteCanvas, CanvasOutput


# ============================================================================
# 隐式状态存储
# ============================================================================

@dataclass
class _TabState:
    index: int = 0


@dataclass
class _AnimationState:
    frame: int = 0
    paused: bool = False
    last_update: float = field(default_factory=time.time)


@dataclass
class _SliderState:
    index: int = 0


@dataclass
class _LayerState:
    selected: str = "sprite"  # "sprite" | "model"


_tab_states: dict[str, _TabState] = {}
_animation_states: dict[str, _AnimationState] = {}
_slider_states: dict[str, _SliderState] = {}
_layer_states: dict[str, _LayerState] = {}


def _get_tab_state(id_suffix: str) -> _TabState:
    if id_suffix not in _tab_states:
        _tab_states[id_suffix] = _TabState()
    return _tab_states[id_suffix]


def _get_animation_state(id_suffix: str) -> _AnimationState:
    if id_suffix not in _animation_states:
        _animation_states[id_suffix] = _AnimationState()
    return _animation_states[id_suffix]


def _get_slider_state(id_suffix: str) -> _SliderState:
    if id_suffix not in _slider_states:
        _slider_states[id_suffix] = _SliderState()
    return _slider_states[id_suffix]


def _get_layer_state(id_suffix: str) -> _LayerState:
    if id_suffix not in _layer_states:
        _layer_states[id_suffix] = _LayerState()
    return _layer_states[id_suffix]


# ============================================================================
# 1. tab_index - 标签页选择
# ============================================================================


def tab_index(
    id_suffix: str,
    labels: list[str],
    current: int = 0,
    *,
    accent_color: tuple[float, float, float, float] | None = None,
) -> int:
    """标签页选择控件

    渲染一排按钮，当前选中的高亮显示。

    Args:
        id_suffix: 唯一标识符
        labels: 标签列表
        current: 当前选中的索引（用于外部状态同步）
        accent_color: 选中按钮的高亮颜色，None 则使用默认

    Returns:
        当前选中的索引 (0-based)，labels 为空时返回 0
    """
    if not labels:
        return 0

    state = _get_tab_state(id_suffix)

    # 同步外部状态
    if current != state.index and 0 <= current < len(labels):
        state.index = current

    # 确保索引在有效范围内
    if state.index >= len(labels):
        state.index = 0

    # 获取 accent 颜色
    if accent_color is None:
        accent_color = tw.CRYSTAL_500

    for i, label in enumerate(labels):
        if i > 0:
            imgui.same_line(0, dp(Sp.S1))

        is_selected = (i == state.index)
        style = tw.btn_primary | tw.btn_xs if is_selected else tw.btn_secondary | tw.btn_xs

        if style(imgui.button)(f"{label}##{id_suffix}_{i}"):
            state.index = i

    return state.index


# ============================================================================
# 2. origin_input - Origin 坐标输入
# ============================================================================


def origin_input(
    id_suffix: str,
    origin: Origin,
    *,
    label: str = "Origin",
    tooltip_text: str | None = None,
) -> Origin:
    """Origin 坐标输入控件

    渲染 X/Y 两个整数输入框。

    Args:
        id_suffix: 唯一标识符
        origin: 当前 Origin 值
        label: 标签文本
        tooltip_text: 悬停提示，None 则使用默认

    Returns:
        更新后的 Origin 对象
    """
    if tooltip_text is None:
        tooltip_text = (
            f"精灵定位点，决定贴图与角色的对齐位置。\n"
            f"默认 ({CHAR_MODEL_ORIGIN[0]}, {CHAR_MODEL_ORIGIN[1]}) 与人体模型对齐。"
        )

    tw.text_muted(imgui.text)(label)
    tooltip(tooltip_text)

    with tw.input_default:
        imgui.push_item_width(dp(Sp.S16))

        changed_x, new_x = imgui.input_int(f"X##{id_suffix}_x", origin.x)
        tooltip(f"默认 {CHAR_MODEL_ORIGIN[0]}。值越小，装备越向右偏移。")

        imgui.same_line(0, dp(Sp.S2))

        changed_y, new_y = imgui.input_int(f"Y##{id_suffix}_y", origin.y)
        tooltip(f"默认 {CHAR_MODEL_ORIGIN[1]}。值越小，装备越向下偏移。")

        imgui.pop_item_width()

    if changed_x or changed_y:
        return Origin(new_x, new_y)
    return origin


# ============================================================================
# 3. animation_frame - 动画帧控制
# ============================================================================


def animation_frame(
    id_suffix: str,
    count: int,
    fps: float,
    *,
    show_pause: bool = True,
) -> int:
    """动画帧控制器

    自动按 fps 推进帧，可选显示暂停按钮。

    Args:
        id_suffix: 唯一标识符
        count: 帧总数
        fps: 播放帧率
        show_pause: 是否显示暂停按钮

    Returns:
        当前帧索引 (0-based)，count <= 0 时返回 0
    """
    if count <= 0:
        return 0

    state = _get_animation_state(id_suffix)

    # 确保帧索引在有效范围内
    if state.frame >= count:
        state.frame = 0

    # 暂停按钮
    if show_pause:
        pause_label = "⏸" if not state.paused else "▶"
        if imgui.button(f"{pause_label}##{id_suffix}_pause"):
            state.paused = not state.paused
        imgui.same_line()
        tw.text_muted(imgui.text)(f"{state.frame + 1}/{count}")

    # 自动播放
    if not state.paused and fps > 0:
        now = time.time()
        elapsed = now - state.last_update
        if elapsed >= 1.0 / fps:
            state.frame = (state.frame + 1) % count
            state.last_update = now

    return state.frame


# ============================================================================
# 4. single_texture_input - 单张贴图选择
# ============================================================================


def single_texture_input(
    id_suffix: str,
    path: str,
    *,
    importer: Callable[[str], str] | None = None,
    label: str | None = None,
) -> str:
    """单张贴图选择控件

    渲染 [选择...] 或 [更换] [清除] 按钮。

    Args:
        id_suffix: 唯一标识符
        path: 当前贴图路径
        importer: 路径转换函数（用于复制到项目目录）
        label: 可选标签，None 则不显示

    Returns:
        更新后的路径
    """
    if label:
        imgui.text(label)
        imgui.same_line()

    result = path

    if path:
        # 已设置状态
        if (tw.btn_secondary | tw.btn_xs)(imgui.button)(f"更换##{id_suffix}"):
            selected = file_dialog([("PNG文件", "*.png")])
            if selected and isinstance(selected, str):
                result = importer(selected) if importer else selected

        imgui.same_line(0, dp(Sp.S1))

        if (tw.btn_danger | tw.btn_xs)(imgui.button)(f"清除##{id_suffix}"):
            result = ""

        imgui.same_line(0, dp(Sp.S1))
        filename = os.path.basename(path)
        tw.text_muted(imgui.text)(filename)
        if imgui.is_item_hovered():
            imgui.set_tooltip(path)
    else:
        # 未设置状态
        if (tw.btn_secondary | tw.btn_xs)(imgui.button)(f"选择...##{id_suffix}"):
            selected = file_dialog([("PNG文件", "*.png")])
            if selected and isinstance(selected, str):
                result = importer(selected) if importer else selected

    return result


# ============================================================================
# 5. loot_speed_input - 战利品动画速度
# ============================================================================


def loot_speed_input(
    id_suffix: str,
    speed: AbsoluteFps | RelativeSpeed,
) -> AbsoluteFps | RelativeSpeed:
    """战利品动画速度输入控件

    Args:
        id_suffix: 唯一标识符
        speed: 当前速度设置

    Returns:
        更新后的速度设置
    """
    imgui.text("动画速度设置")
    tooltip("设置战利品贴图的动画播放速度。\n此设置会影响生成的模组代码。")

    is_relative = isinstance(speed, RelativeSpeed)

    if imgui.begin_combo(
        f"速度模式##{id_suffix}_mode",
        "相对速度" if is_relative else "固定帧率 (FPS)"
    ):
        if imgui.selectable("固定帧率 (FPS)", not is_relative)[0] and is_relative:
            speed = AbsoluteFps(fps=10.0)
        if imgui.selectable("相对速度", is_relative)[0] and not is_relative:
            speed = RelativeSpeed(multiplier=0.25)
        imgui.end_combo()

    if isinstance(speed, AbsoluteFps):
        imgui.push_item_width(150)
        changed, new_fps = imgui.input_float(
            f"播放帧率 (FPS)##{id_suffix}_fps",
            speed.fps,
            step=1.0,
            step_fast=5.0,
            format_="%.1f",
        )
        if changed:
            speed.fps = max(0.1, new_fps)
        imgui.pop_item_width()
        tooltip("每秒播放的帧数。\n这是一个固定值，不会随游戏速度变化。\n默认值: 10")

    elif isinstance(speed, RelativeSpeed):  # pyright: ignore[reportUnnecessaryIsInstance]
        imgui.push_item_width(180)
        changed, new_mult = imgui.input_float(
            f"速度倍率##{id_suffix}_mult",
            speed.multiplier,
            step=0.01,
            step_fast=0.1,
            format_="%.3f",
        )
        if changed:
            speed.multiplier = max(0.001, round(new_mult, 3))
        imgui.pop_item_width()
        tooltip(
            f"每个游戏帧内动画前进的帧数。\n\n"
            f"例如:\n  • 值为 0.1 时: 实际播放速度 = {GAME_FPS} × 0.1 = 4 fps\n"
            f"  • 值为 0.25 时: 实际播放速度 = {GAME_FPS} × 0.25 = 10 fps\n"
            f"  • 值为 0.5 时: 实际播放速度 = {GAME_FPS} × 0.5 = 20 fps\n"
            f"  • 值为 1.0 时: 实际播放速度 = {GAME_FPS} × 1.0 = 40 fps\n\n"
            f"提示: 手持贴图默认相对帧率为 0.25 (即 {GAME_FPS // 4} fps)。\n最小值: 0.001"
        )
        tw.text_muted(imgui.text)(f"实际播放速度: {GAME_FPS * speed.multiplier:.3f} fps (游戏 {GAME_FPS} fps 时)")

    return speed


# ============================================================================
# 6. model_combo / race_combo - 模型选择
# ============================================================================


def model_combo(id_suffix: str, current: str) -> str:
    """角色模型选择下拉框

    Args:
        id_suffix: 唯一标识符
        current: 当前选中的模型 key

    Returns:
        选中的模型 key
    """
    current_label = CHARACTER_MODEL_LABELS.get(current, current)

    with tw.input_default:
        imgui.push_item_width(dp(Sp.S32))
        if imgui.begin_combo(f"▼模特##{id_suffix}", current_label):
            for model_key, model_label in CHARACTER_MODEL_LABELS.items():
                if imgui.selectable(model_label, model_key == current)[0]:
                    current = model_key
            imgui.end_combo()
        imgui.pop_item_width()

    return current


def race_combo(id_suffix: str, current: str) -> str:
    """种族选择下拉框

    Args:
        id_suffix: 唯一标识符
        current: 当前选中的种族 key

    Returns:
        选中的种族 key
    """
    current_label = CHARACTER_RACE_LABELS.get(current, current)

    with tw.input_default:
        imgui.push_item_width(dp(Sp.S20))
        if imgui.begin_combo(f"人种##{id_suffix}", current_label):
            for race in CHARACTER_RACES:
                label = CHARACTER_RACE_LABELS.get(race, race)
                if imgui.selectable(label, race == current)[0]:
                    current = race
            imgui.end_combo()
        imgui.pop_item_width()

    return current


# ============================================================================
# 7. texture_preview - 贴图预览
# ============================================================================


# 画布实例缓存
_preview_canvases: dict[str, InfiniteCanvas] = {}
# 上次预览的内容路径（用于检测内容变更并重置视口）
_preview_last_paths: dict[str, str] = {}


def _get_preview_canvas(id_suffix: str, content_path: str = "") -> InfiniteCanvas:
    """获取或创建预览画布

    当 content_path 变化时自动重置画布视口，避免不同物品共用缩放状态。
    """
    from ui.canvas import InfiniteCanvas
    if id_suffix not in _preview_canvases:
        _preview_canvases[id_suffix] = InfiniteCanvas(id_suffix)
    canvas = _preview_canvases[id_suffix]
    # 检测内容是否变化
    if content_path and _preview_last_paths.get(id_suffix) != content_path:
        _preview_last_paths[id_suffix] = content_path
        canvas.reset_view()
    return canvas


def texture_preview(
    id_suffix: str,
    path: str,
    *,
    origin: Origin | None = None,
    model_path: str | None = None,
    size: tuple[int, int] | None = None,
    draggable: bool = False,
    layer_select: bool = False,
) -> CanvasOutput:
    """贴图预览控件

    Args:
        id_suffix: 唯一标识符
        path: 贴图路径
        origin: 精灵 Origin（None 则使用居中模式）
        model_path: 角色模型贴图路径（None 则不叠加）
        size: 预览区域尺寸 (width, height)，None 则自动适应
        draggable: 是否可拖拽精灵
        layer_select: 是否启用图层选择

    Returns:
        CanvasOutput 包含交互信息
    """
    from ui.canvas import (
        InfiniteCanvas as InfiniteCanvas, CanvasOutput as CanvasOutput, CanvasItem,
        centered_sprite_item, char_sprite_item, char_model_item,
    )
    from ui.texture_manager import load_texture
    from constants import VALID_AREA_SIZE

    canvas = _get_preview_canvas(id_suffix, content_path=path)
    items: list[CanvasItem] = []
    selected_ids: set[str] = set()

    # 图层选择状态
    if layer_select:
        layer_state = _get_layer_state(id_suffix)
        selected_ids.add(layer_state.selected)

    if origin is not None:
        # 有 origin: 使用角色贴图模式
        # 添加角色模型（如果有）
        if model_path:
            model_item = char_model_item(
                "model", model_path,
                selectable=layer_select,
                draggable=False,
                z_order=0
            )
            if model_item:
                items.append(model_item)

        # 添加装备贴图
        sprite_item = char_sprite_item(
            "sprite", path, origin,
            selectable=layer_select,
            draggable=draggable,
            z_order=10
        )
        if sprite_item:
            items.append(sprite_item)

        # 默认尺寸
        if size is None:
            size = (VALID_AREA_SIZE, VALID_AREA_SIZE)
    else:
        # 无 origin: 使用居中模式
        sprite_item = centered_sprite_item(
            "sprite", path,
            selectable=layer_select,
            draggable=draggable,
        )
        if sprite_item:
            items.append(sprite_item)

        # 默认尺寸：贴图的 4 倍
        if size is None:
            tex = load_texture(path)
            if tex:
                size = (int(tex["width"] * 4), int(tex["height"] * 4))
            else:
                size = (64, 64)

    # 绘制画布
    output = canvas.draw(size[0], size[1], items, selected_ids)

    # 更新图层选择状态
    if layer_select and output.clicked_id:
        layer_state = _get_layer_state(id_suffix)
        layer_state.selected = output.clicked_id

    return output


# ============================================================================
# 8. frame_strip - 帧条
# ============================================================================


def frame_strip(
    id_suffix: str,
    paths: list[str],
    *,
    animated: bool = True,
    fps: float = 10.0,
    importer: Callable[[str], str] | None = None,
    max_width: float = 0,
) -> tuple[list[str], int]:
    """帧条控件 - 多帧管理 + 帧选择

    Layout (Tailwind):
        <div class="flex flex-col gap-1">
          <!-- Row 1: scrollable thumbnail strip -->
          <div class="overflow-x-auto flex items-center gap-1 h-8">
            [frame1] [frame2] [frame3] ...
          </div>
          <!-- Row 2: compact controls toolbar -->
          <div class="flex items-center gap-0.5 text-xs text-muted">
            [+ 添加帧]  [⏮] [▶⏸] [⏭]  10fps          帧 3/8
          </div>
        </div>

    交互方式：
    - 点击缩略图：选中帧
    - 右键缩略图：移动/删除菜单
    - 鼠标滚轮悬停缩略图条：水平滚动（无 scrollbar）
    - ⏮/⏭ 按钮：逐帧导航（自动滚动到当前帧）
    - ▶/⏸ 按钮：播放/暂停动画

    Args:
        id_suffix: 唯一标识符
        paths: 当前路径列表
        animated: 是否自动播放
        fps: 播放帧率（仅 animated=True 时有效）
        importer: 路径转换函数
        max_width: 最大宽度 (像素, 0=自动填充)

    Returns:
        (更新后的路径列表, 当前帧索引)
    """
    from ui.texture_manager import load_texture
    from ui.icons import FA_PLUS, FA_PLAY, FA_PAUSE, FA_BACKWARD_STEP, FA_FORWARD_STEP

    result_paths = list(paths)  # 复制以便修改
    state = _get_animation_state(id_suffix)

    # 空列表处理
    if not result_paths:
        if (tw.btn_ghost | tw.btn_xs)(imgui.button)(f"{FA_PLUS} 选择贴图...##{id_suffix}_add"):
            selected = file_dialog([("PNG文件", "*.png")], multiple=True)
            if selected:
                for p in (selected if isinstance(selected, list) else [selected]):
                    result_paths.append(importer(p) if importer else p)
        return result_paths, 0

    # 确保帧索引有效
    if state.frame >= len(result_paths):
        state.frame = len(result_paths) - 1
    if state.frame < 0:
        state.frame = 0

    # === 尺寸常量 ===
    thumb_h = round(dp(Sp.S7))       # 缩略图高度 28px
    pad = round(dp(Sp.S0_5))         # 缩略图 frame padding 2px
    frame_outer = thumb_h + pad * 2   # 含 padding 的外框高度
    gap = round(dp(Sp.S1))           # 缩略图间距 4px

    # === 缩略图样式 ===
    # 选中: 紫水晶主色 (明显高亮)
    # 未选中: 深渊按钮 (实体背景，有交互反馈)
    _thumb_selected = tw.btn_primary | tw.rounded_sm
    _thumb_unselected = tw.btn_secondary | tw.rounded_sm

    # === Row 1: 缩略图条 (鼠标滚轮滚动, 无 scrollbar) ===
    # 预计算内容总宽度
    thumb_widths: list[float] = []
    for p in result_paths:
        tex = load_texture(p)
        if tex and tex["height"] > 0:
            aspect = tex["width"] / tex["height"]
            thumb_widths.append(round(thumb_h * aspect) + pad * 2)
        else:
            thumb_widths.append(frame_outer)  # 方形 fallback

    total_content_w = sum(thumb_widths) + gap * max(0, len(thumb_widths) - 1)

    child_w = max_width if max_width > 0 else 0
    child_h = frame_outer  # 缩略图高度

    # 设置内容宽度以启用水平滚动 (滚轮)
    imgui.set_next_window_content_size(total_content_w, 0)
    imgui.begin_child(
        f"##framebar_{id_suffix}",
        width=child_w,
        height=child_h,
        border=False,
        flags=imgui.WINDOW_HORIZONTAL_SCROLLBAR | imgui.WINDOW_NO_SCROLLBAR,
    )

    # 绘制帧缩略图
    to_delete: int | None = None
    to_move: tuple[int, int] | None = None

    for i, p in enumerate(result_paths):
        if i > 0:
            imgui.same_line(0, gap)

        is_current = (i == state.frame)
        imgui.push_id(f"{id_suffix}_{i}")

        tex = load_texture(p)
        thumb_style = _thumb_selected if is_current else _thumb_unselected

        if tex and tex["height"] > 0:
            aspect = tex["width"] / tex["height"]
            img_h = thumb_h
            img_w = round(img_h * aspect)
            with thumb_style:
                imgui.push_style_var(imgui.STYLE_FRAME_PADDING, (pad, pad))
                clicked = imgui.image_button(
                    tex["tex_id"],
                    img_w, img_h,
                    uv0=(0, 0), uv1=(1, 1),
                )
                if clicked:
                    state.frame = i
                    state.paused = True
                imgui.pop_style_var()
        else:
            # 无贴图：显示序号 (方形)
            if thumb_style(imgui.button)(
                f"{i+1}##{id_suffix}_frame_{i}",
                width=frame_outer, height=frame_outer,
            ):
                state.frame = i
                state.paused = True

        # 选中帧自动滚动到可见区域
        if is_current:
            imgui.set_scroll_here_x(0.5)

        # 右键上下文菜单
        if imgui.begin_popup_context_item(f"frame_ctx_{id_suffix}_{i}"):
            imgui.text(f"帧 {i+1}: {os.path.basename(p)}")
            imgui.separator()

            if i > 0:
                if imgui.selectable("← 左移")[0]:
                    to_move = (i, i - 1)
            else:
                imgui.text_disabled("← 左移")

            if i < len(result_paths) - 1:
                if imgui.selectable("→ 右移")[0]:
                    to_move = (i, i + 1)
            else:
                imgui.text_disabled("→ 右移")

            imgui.separator()

            if imgui.selectable("× 删除")[0]:
                to_delete = i

            imgui.end_popup()

        # 悬停提示
        elif imgui.is_item_hovered():
            imgui.set_tooltip(f"帧 {i+1}: {os.path.basename(p)}\n右键打开菜单")

        imgui.pop_id()

    imgui.end_child()  # framebar scroll child

    # === 执行移动/删除 (在 scroll child 之外) ===
    if to_move is not None:
        from_idx, to_idx = to_move
        result_paths[from_idx], result_paths[to_idx] = result_paths[to_idx], result_paths[from_idx]
        if state.frame == from_idx:
            state.frame = to_idx
        elif state.frame == to_idx:
            state.frame = from_idx

    if to_delete is not None:
        result_paths.pop(to_delete)
        if state.frame >= len(result_paths) and result_paths:
            state.frame = len(result_paths) - 1

    # === Row 2: 控制栏 ===
    # Tailwind: flex items-center gap-0.5 text-xs text-muted
    # 使用 same_line() 保证垂直对齐 (所有元素在同一基线)
    ly.gap_y(Sp.S1)

    avail_w = child_w if child_w > 0 else imgui.get_content_region_available().x
    ctrl_h = round(dp(Sp.S5))  # 20px 紧凑控制按钮
    ctrl_style = tw.btn_secondary | tw.rounded_sm

    # [+ 添加帧]
    with ctrl_style:
        if imgui.button(f"{FA_PLUS} 添加帧##{id_suffix}_add", 0, ctrl_h):
            selected_files = file_dialog([("PNG文件", "*.png")], multiple=True)
            if selected_files:
                for p in (selected_files if isinstance(selected_files, list) else [selected_files]):
                    result_paths.append(importer(p) if importer else p)

    if len(result_paths) > 1:
        imgui.same_line(0, dp(Sp.S3))

        # [⏮] 上一帧
        with ctrl_style:
            if imgui.button(f"{FA_BACKWARD_STEP}##{id_suffix}_prev", ctrl_h, ctrl_h):
                state.frame = (state.frame - 1) % len(result_paths)
                state.paused = True

        imgui.same_line(0, dp(Sp.S0_5))

        # [▶/⏸] 播放/暂停 (仅 animated 模式)
        if animated:
            play_icon = FA_PAUSE if not state.paused else FA_PLAY
            with ctrl_style:
                if imgui.button(f"{play_icon}##{id_suffix}_pause", ctrl_h, ctrl_h):
                    state.paused = not state.paused
            imgui.same_line(0, dp(Sp.S0_5))

        # [⏭] 下一帧
        with ctrl_style:
            if imgui.button(f"{FA_FORWARD_STEP}##{id_suffix}_next", ctrl_h, ctrl_h):
                state.frame = (state.frame + 1) % len(result_paths)
                state.paused = True

        if animated:
            imgui.same_line(0, dp(Sp.S2))
            imgui.align_text_to_frame_padding()
            tw.text_muted(imgui.text)(f"{fps:.0f}fps")

    # 右对齐帧计数器
    frame_text = f"帧 {state.frame + 1}/{len(result_paths)}"
    text_w = imgui.calc_text_size(frame_text).x
    imgui.same_line(avail_w - text_w)
    imgui.align_text_to_frame_padding()
    tw.text_muted(imgui.text)(frame_text)

    # === 自动播放逻辑 ===
    if animated and len(result_paths) > 1 and not state.paused and fps > 0:
        now = time.time()
        elapsed = now - state.last_update
        if elapsed >= 1.0 / fps:
            state.frame = (state.frame + 1) % len(result_paths)
            state.last_update = now

    return result_paths, state.frame


# ============================================================================
# 辅助函数
# ============================================================================


def slider_index(
    id_suffix: str,
    count: int,
    *,
    label: str = "",
) -> int:
    """滑块索引选择

    Args:
        id_suffix: 唯一标识符
        count: 总数量
        label: 可选标签

    Returns:
        当前选中索引 (0-based)，count <= 1 时返回 0
    """
    if count <= 1:
        return 0

    state = _get_slider_state(id_suffix)

    # 确保索引在有效范围内
    if state.index >= count:
        state.index = count - 1

    if label:
        imgui.text(label)
        imgui.same_line()

    imgui.push_item_width(150)
    changed, new_val = imgui.slider_int(
        f"##{id_suffix}_slider",
        state.index,
        0,
        count - 1,
        format_=f"%d / {count - 1}",
    )
    if changed:
        state.index = new_val
    imgui.pop_item_width()

    return state.index
