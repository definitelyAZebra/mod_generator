# -*- coding: utf-8 -*-
"""贴图处理工具函数

提供贴图裁剪、偏移计算、复制等功能。
所有函数均为模块级，不依赖 CodeGenerator。
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

from constants import (
    ARMOR_PREVIEW_HEIGHT,
    ARMOR_PREVIEW_WIDTH,
    GML_ANCHOR_X,
    GML_ANCHOR_Y,
    VALID_MAX_X,
    VALID_MAX_Y,
    VALID_MIN_X,
    VALID_MIN_Y,
    VIEWPORT_CHAR_OFFSET_X,
    VIEWPORT_CHAR_OFFSET_Y,
)
from core.specs import (
    ItemTexturesV2, WeaponCharTexture, MultiPoseCharTexture, NoCharTexture,
    Origin,
)


# ============== 贴图处理工具函数 ==============


def calculate_crop_region(
    img_width: int, img_height: int, off_x: int, off_y: int
) -> tuple[int, int, int, int, bool]:
    """计算武器贴图的裁剪区域

    Args:
        img_width: 原图宽度
        img_height: 原图高度
        off_x: 用户设置的水平偏移
        off_y: 用户设置的垂直偏移

    Returns:
        tuple: (crop_x1, crop_y1, crop_x2, crop_y2, is_valid)
    """
    valid_local_min_x = VALID_MIN_X + off_x
    valid_local_max_x = VALID_MAX_X + off_x
    valid_local_min_y = VALID_MIN_Y + off_y
    valid_local_max_y = VALID_MAX_Y + off_y

    crop_x1 = int(max(0, valid_local_min_x))
    crop_y1 = int(max(0, valid_local_min_y))
    crop_x2 = int(min(img_width, valid_local_max_x))
    crop_y2 = int(min(img_height, valid_local_max_y))

    is_valid = crop_x1 < crop_x2 and crop_y1 < crop_y2
    return crop_x1, crop_y1, crop_x2, crop_y2, is_valid


def calculate_adjusted_offsets(off_x: int, off_y: int) -> tuple[int, int]:
    """计算真正裁剪后的调整偏移量 (旧版接口，保留兼容性)

    X方向最大有效偏移: VIEWPORT_CHAR_OFFSET_X = 8
    Y方向最大有效偏移: VIEWPORT_CHAR_OFFSET_Y = 12
    """
    adjusted_off_x = min(off_x, VIEWPORT_CHAR_OFFSET_X)
    adjusted_off_y = min(off_y, VIEWPORT_CHAR_OFFSET_Y)
    return adjusted_off_x, adjusted_off_y


def calculate_clamped_origin(origin: Origin) -> tuple[int, int] | None:
    """计算裁剪后的 Origin 值

    如果 Origin 是默认值 (22, 34)，返回 None（无需注入）。
    否则返回有效范围内的 Origin 值。

    有效范围:
    - X: [22 - 8, 22] = [14, 22]  (向右偏移最多 8 像素)
    - Y: [34 - 12, 34] = [22, 34] (向下偏移最多 12 像素)
    """
    if origin.is_default:
        return None

    # Origin 值越小 = 装备向右/下偏移
    # 限制最小值 (即最大偏移量)
    clamped_x = max(origin.x, GML_ANCHOR_X - VIEWPORT_CHAR_OFFSET_X)
    clamped_y = max(origin.y, GML_ANCHOR_Y - VIEWPORT_CHAR_OFFSET_Y)

    # 如果裁剪后恢复为默认值，则无需注入
    if clamped_x == GML_ANCHOR_X and clamped_y == GML_ANCHOR_Y:
        return None

    return clamped_x, clamped_y


def copy_texture(src_path: str, dst_path: str | Path, mask_offsets: tuple[int, int] | None = None) -> str | None:
    """复制贴图文件，如果指定 mask_offsets 则根据有效范围进行裁剪

    Returns:
        错误信息字符串，成功则返回 None
    """
    if not src_path:
        return None
    if not os.path.exists(src_path):
        return f"贴图文件不存在: {src_path}"

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

    if mask_offsets and Image:
        try:
            off_x, off_y = mask_offsets
            with Image.open(src_path) as img:
                img = img.convert("RGBA")
                w, h = img.size

                crop_x1, crop_y1, crop_x2, crop_y2, is_valid = calculate_crop_region(
                    w, h, off_x, off_y
                )

                if is_valid:
                    cropped = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                    cropped.save(dst_path)
                    return None
                else:
                    # 贴图超出有效区域，创建占位符
                    placeholder = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
                    placeholder.save(dst_path)
                    return f"警告: 贴图 {src_path} 完全超出有效显示区域"
        except Exception as e:
            # 裁剪失败，回退到直接复制
            # 注：此处不返回警告，因为后续 shutil.copy2 会正常复制文件
            pass

    try:
        shutil.copy2(src_path, dst_path)
        return None
    except Exception as e:
        return f"复制贴图失败 {src_path}: {e}"


def copy_armor_pose_texture(
    src_path: str, dst_path: str | Path, off_x: int, off_y: int
) -> str | None:
    """复制护甲姿势贴图，通过裁剪+透明填充实现偏移效果

    护甲穿戴贴图固定为 48x40 尺寸，偏移通过裁剪原图并在透明画布上重绘实现。

    Args:
        src_path: 源贴图路径
        dst_path: 目标路径
        off_x: 水平偏移（正值向右移动贴图内容）
        off_y: 垂直偏移（正值向下移动贴图内容）

    Returns:
        错误信息字符串，成功则返回 None
    """
    if not src_path:
        return None
    if not os.path.exists(src_path):
        return f"贴图文件不存在: {src_path}"

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

    if not Image:
        # 没有 PIL，直接复制
        try:
            shutil.copy2(src_path, dst_path)
            return None
        except Exception as e:
            return f"复制贴图失败 {src_path}: {e}"

    try:
        with Image.open(src_path) as img:
            img = img.convert("RGBA")
            src_w, src_h = img.size

            # 目标尺寸固定为 48x40
            dst_w, dst_h = ARMOR_PREVIEW_WIDTH, ARMOR_PREVIEW_HEIGHT

            # 创建透明画布
            canvas = Image.new("RGBA", (dst_w, dst_h), (0, 0, 0, 0))

            # 计算源图裁剪区域和目标粘贴位置
            # 偏移的含义：off_x 正值表示贴图内容向右移动
            # 即从源图的 (off_x, off_y) 开始裁剪

            # 源图裁剪起点
            src_x1 = max(0, off_x)
            src_y1 = max(0, off_y)

            # 源图裁剪终点（不超过源图尺寸和目标尺寸）
            src_x2 = min(src_w, off_x + dst_w)
            src_y2 = min(src_h, off_y + dst_h)

            # 如果偏移为负，需要在目标画布上留出空白
            dst_x = max(0, -off_x)
            dst_y = max(0, -off_y)

            # 检查是否有有效区域
            if src_x1 < src_x2 and src_y1 < src_y2:
                cropped = img.crop((src_x1, src_y1, src_x2, src_y2))
                canvas.paste(cropped, (dst_x, dst_y))

            canvas.save(dst_path)
            return None
    except Exception as e:
        return f"处理护甲贴图失败 {src_path}: {e}"


def copy_item_textures_v2(
    item_id: str,
    textures: ItemTexturesV2,
    sprites_dir: Path,
    copy_char: bool,
    copy_left: bool,
    is_multi_pose_armor: bool = False,
) -> list[str]:
    """复制物品的所有贴图文件 (ItemTexturesV2 版本)

    Args:
        item_id: 物品ID
        textures: ItemTexturesV2 贴图数据
        sprites_dir: 精灵图输出目录
        copy_char: 是否复制角色/穿戴贴图
        copy_left: 是否复制左手贴图
        is_multi_pose_armor: 是否为多姿势护甲（头/身/手/腿/背）

    Returns:
        错误/警告信息列表
    """
    errors: list[str] = []

    def _copy(src: str, dst: str | Path, mask: tuple[int, int] | None = None) -> None:
        err = copy_texture(src, dst, mask)
        if err:
            errors.append(err)

    def _copy_armor_pose(src: str, dst: str | Path, off_x: int, off_y: int) -> None:
        err = copy_armor_pose_texture(src, dst, off_x, off_y)
        if err:
            errors.append(err)

    def _copy_texture_list(paths: list[str], prefix: str, mask: tuple[int, int] | None = None) -> None:
        """复制贴图列表，根据长度决定命名方式"""
        if not paths:
            return
        if len(paths) == 1:
            _copy(paths[0], sprites_dir / f"{prefix}.png", mask)
        else:
            for idx, path in enumerate(paths):
                _copy(path, sprites_dir / f"{prefix}_{idx}.png", mask)

    # 角色/手持/穿戴贴图
    if copy_char:
        match textures.char:
            case MultiPoseCharTexture() as mp:
                # 多姿势装备（头/身/手/腿/背）
                # 站立姿势0
                if mp.standing0.has_texture():
                    off_x, off_y = mp.standing0.origin.to_offset()
                    _copy_armor_pose(
                        mp.standing0.path,
                        sprites_dir / f"s_char_{item_id}_0.png",
                        off_x,
                        off_y,
                    )
                # 站立姿势1
                if mp.standing1.has_texture():
                    off_x, off_y = mp.standing1.origin.to_offset()
                    _copy_armor_pose(
                        mp.standing1.path,
                        sprites_dir / f"s_char_{item_id}_1.png",
                        off_x,
                        off_y,
                    )
                # 休息姿势
                if mp.rest.has_texture():
                    off_x, off_y = mp.rest.origin.to_offset()
                    _copy_armor_pose(
                        mp.rest.path,
                        sprites_dir / f"s_char3_{item_id}.png",
                        off_x,
                        off_y,
                    )
                # 女性版贴图
                if mp.standing0_female.has_texture():
                    off_x, off_y = mp.standing0_female.origin.to_offset()
                    _copy_armor_pose(
                        mp.standing0_female.path,
                        sprites_dir / f"s_char_{item_id}_female_0.png",
                        off_x,
                        off_y,
                    )
                if mp.standing1_female.has_texture():
                    off_x, off_y = mp.standing1_female.origin.to_offset()
                    _copy_armor_pose(
                        mp.standing1_female.path,
                        sprites_dir / f"s_char_{item_id}_female_1.png",
                        off_x,
                        off_y,
                    )
                if mp.rest_female.has_texture():
                    off_x, off_y = mp.rest_female.origin.to_offset()
                    _copy_armor_pose(
                        mp.rest_female.path,
                        sprites_dir / f"s_char3_{item_id}_female.png",
                        off_x,
                        off_y,
                    )

            case WeaponCharTexture() as w:
                # 武器/盾牌：动画帧序列
                if w.main.has_texture():
                    mask = w.main.origin.to_offset()
                    _copy_texture_list(w.main.paths, f"s_char_{item_id}", mask)

                # 左手贴图
                if copy_left and w.left.has_texture():
                    mask_left = w.left.origin.to_offset()
                    _copy_texture_list(w.left.paths, f"s_charleft_{item_id}", mask_left)

            case NoCharTexture():
                pass  # 无角色贴图

    # 常规/物品栏贴图
    for idx, inv_texture in enumerate(textures.inventory):
        _copy(inv_texture, sprites_dir / f"s_inv_{item_id}_{idx}.png")

    # 战利品贴图
    _copy_texture_list(textures.loot.paths, f"s_loot_{item_id}")

    return errors


def format_description(text: str) -> str:
    """处理描述文本：strip -> splitlines -> join('#') -> 转义双引号

    用于通过 C# 接口注入的物品描述（普通武器/护甲）
    """
    if not text:
        return ""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    joined = "#".join(lines)
    return joined.replace('"', '\\"')


def format_description_gml(text: str) -> str:
    """处理描述文本：仅转义双引号

    用于直接写入 GML 的物品描述（混合物品），不需要换行转译
    GML 中 # 本身就是换行符，用户可以直接在描述中使用 # 换行
    """
    if not text:
        return ""
    # 只转义引号，不处理换行（用户直接使用 # 作为换行符）
    return text.strip().replace('"', '\\"')
