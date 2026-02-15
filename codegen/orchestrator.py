# -*- coding: utf-8 -*-
"""模组生成 - 验证、生成、输出

纯业务逻辑，不依赖 GUI。
由 ui/menu.py 的生成按钮调用。
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path

from codegen.generator import CodeGenerator
from codegen.textures import copy_item_textures_v2
from core.models import (
    Armor,
    ModProject,
    validate_item,
    validate_hybrid_item,
)
from ui import popups


def validate_project_for_generation(project: ModProject) -> list[str]:
    """验证项目是否可以生成

    Args:
        project: 要验证的模组项目

    Returns:
        错误消息列表，如果为空则验证通过
    """
    errors: list[str] = []

    # 验证项目本身
    project_errors = project.validate()
    if project_errors:
        errors.extend(project_errors)

    # 验证武器和装备
    for item in project.weapons + project.armors:
        errors.extend(validate_item(item, project))

    # 验证混合物品
    for hybrid in project.hybrid_items:
        errors.extend(validate_hybrid_item(hybrid, project))

    return errors


def generate_mod_files_to_disk(project: ModProject) -> list[str]:
    """生成模组文件到磁盘

    将项目中的所有内容（C# 代码、GML 脚本、贴图等）生成到磁盘的模组目录中。

    Args:
        project: 要生成的模组项目

    Returns:
        贴图复制过程中的警告/错误列表

    Raises:
        Exception: 生成过程中的任何错误
    """
    mod_name = project.code_name.strip() or "ModProject"
    base_dir = os.path.dirname(project.file_path)
    mod_dir = Path(base_dir) / mod_name
    sprites_dir = mod_dir / "Sprites"

    print(f"创建目录: {mod_dir}")
    mod_dir.mkdir(exist_ok=True)
    sprites_dir.mkdir(exist_ok=True)

    print("生成 C# 代码...")
    generator = CodeGenerator(project)
    files = generator.generate()
    for filename, content in files.items():
        with open(mod_dir / filename, "w", encoding="utf-8") as f:
            f.write(content)

    print("生成空的 .csproj 文件...")
    with open(mod_dir / f"{mod_name}.csproj", "w", encoding="utf-8"):
        pass

    # 如果有混合物品，生成 Codes 文件夹和 GML 脚本
    if project.hybrid_items:
        codes_dir = mod_dir / "Codes"
        codes_dir.mkdir(exist_ok=True)
        print("生成 hover 辅助脚本...")

        with open(codes_dir / "scr_hoversEnsureExtendedOrderLists.gml", "w", encoding="utf-8") as f:
            f.write(generator.generate_ensure_extended_order_lists_gml())

        with open(codes_dir / "scr_hoversDrawHybridConsumAttributes.gml", "w", encoding="utf-8") as f:
            f.write(generator.generate_draw_hybrid_consum_attrs_gml())

    print("复制贴图文件...")
    texture_errors: list[str] = []
    for item in project.weapons + project.armors:
        is_multi_pose = (
            isinstance(item, Armor) and item.needs_multi_pose_textures()
        )
        errs = copy_item_textures_v2(
            item_id=item.id,
            textures=item.textures,
            sprites_dir=sprites_dir,
            copy_char=item.needs_char_texture(),
            copy_left=item.needs_left_texture(),
            is_multi_pose_armor=is_multi_pose,
        )
        texture_errors.extend(errs)

    for hybrid in project.hybrid_items:
        errs = copy_item_textures_v2(
            item_id=hybrid.id,
            textures=hybrid.textures,
            sprites_dir=sprites_dir,
            copy_char=hybrid.needs_char_texture(),
            copy_left=hybrid.needs_left_texture(),
            is_multi_pose_armor=hybrid.needs_multi_pose_textures(),
        )
        texture_errors.extend(errs)

    if texture_errors:
        for err in texture_errors:
            print(err)

    print("生成成功！")
    return texture_errors


def generate_mod_and_show_result(project: ModProject) -> None:
    """生成模组并显示结果弹窗"""
    try:
        generate_mod_files_to_disk(project)
        base_dir = os.path.dirname(project.file_path) if project.file_path else "."
        mod_dir = os.path.abspath(os.path.join(base_dir, project.code_name.strip() or "ModProject"))
        popups.success(mod_dir)
    except Exception as e:
        error_msg = f"生成模组失败:\n{e}\n\n堆栈跟踪:\n{traceback.format_exc()}"
        print(error_msg)  # 也打印到控制台
        popups.error(error_msg)


def generate_mod_with_validation(project: ModProject) -> None:
    """验证并生成模组

    执行项目验证、保存检查，然后生成模组。
    """
    print("开始生成模组...")

    validation_errors = validate_project_for_generation(project)
    if validation_errors:
        popups.error("验证失败:\n" + "\n".join(f"  • {e}" for e in validation_errors))
        return

    if not project.file_path:
        def save_and_generate():
            from ui.dialogs import select_directory_dialog
            directory = select_directory_dialog()
            if not directory:
                return
            project.file_path = os.path.join(directory, "project.json")
            os.makedirs(os.path.join(directory, "assets"), exist_ok=True)
            project.save()
            generate_mod_and_show_result(project)
        popups.save_prompt(on_confirm=save_and_generate)
        return

    generate_mod_and_show_result(project)
