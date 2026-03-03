# -*- coding: utf-8 -*-
"""
自动化打包脚本
用法: python build_release.py
      python build_release.py --force  # 跳过版本检查
"""

import subprocess
import shutil
import sys
import zipfile
import ast
from pathlib import Path

# 动态导入版本信息
from version import VERSION_STRING


def run_git(*args):
    """运行 git 命令并返回输出"""
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=Path(__file__).parent
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_version_updated():
    """
    检查 HEAD 是否打了 v{VERSION_STRING} 的 tag
    返回: (is_ok, message)
    """
    expected_tag = f"v{VERSION_STRING}"

    # 获取指向 HEAD 的所有 tag
    code, tags_on_head, _ = run_git("tag", "--points-at", "HEAD")
    if code != 0:
        return True, "⚠️  无法获取 HEAD 的 tag 信息，跳过检查"

    head_tags = [t.strip() for t in tags_on_head.splitlines() if t.strip()]

    if expected_tag in head_tags:
        return True, f"✓ HEAD 已打 tag: {expected_tag}"

    if head_tags:
        return False, (
            f"⚠️  HEAD 上有 tag {head_tags}，但不包含 {expected_tag}\n"
            f"请执行: git tag {expected_tag}"
        )

    return False, (
        f"⚠️  HEAD 没有 tag，当前版本 v{VERSION_STRING}\n"
        f"请执行: git tag {expected_tag}\n"
        f"使用 --force 参数可以强制继续打包。"
    )


def check_changelog_updated():
    """
    检查 CHANGELOG.md 是否包含当前版本的条目
    返回: (is_ok, message)
    """
    changelog_path = Path(__file__).parent / "CHANGELOG.md"

    if not changelog_path.exists():
        return False, "❌ 找不到 CHANGELOG.md"

    content = changelog_path.read_text(encoding="utf-8")

    # 检查是否有当前版本的条目，格式如 ## [0.9.1]
    version_pattern = f"## [{VERSION_STRING}]"
    if version_pattern in content:
        return True, f"✓ CHANGELOG.md 包含 v{VERSION_STRING} 的记录"

    return False, f"⚠️  CHANGELOG.md 中没有找到 [{VERSION_STRING}] 的条目，请先更新 changelog"


def get_active_font_files(project_dir: Path) -> list[Path]:
    """读取 ui/font_config.py，返回当前配置使用的字体文件列表。"""
    font_config = project_dir / "ui" / "font_config.py"
    if not font_config.exists():
        return []

    target_names = {"ENGLISH_FONT", "CHINESE_FONT", "ICON_FONT"}
    font_files: list[Path] = []

    try:
        tree = ast.parse(font_config.read_text(encoding="utf-8"))
    except Exception:
        return []

    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue

        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if target.id not in target_names:
            continue

        value = node.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value.strip():
            font_files.append(project_dir / value.value)

    # 去重，保持顺序
    unique_files: list[Path] = []
    seen: set[Path] = set()
    for file_path in font_files:
        normalized = file_path.resolve() if file_path.exists() else file_path
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_files.append(file_path)

    return unique_files


def main():
    project_dir = Path(__file__).parent
    dist_dir = project_dir / "dist"
    build_dir = project_dir / "build"
    force_build = "--force" in sys.argv

    print(f"🚀 开始打包 mod_generator v{VERSION_STRING}")
    print("=" * 50)

    # Step 0: 检查版本 tag 和 changelog 是否已更新
    print("\n🔍 检查版本 tag...")
    version_ok, message = check_version_updated()
    print(message)

    print("\n📋 检查更新日志...")
    changelog_ok, changelog_msg = check_changelog_updated()
    print(changelog_msg)

    if not version_ok or not changelog_ok:
        if force_build:
            print("\n⚡ 使用了 --force，继续打包...")
        else:
            print("\n❌ 打包已取消。请先更新相关文件或使用 --force 强制打包。")
            return 1

    # Step 1: 清理旧的构建文件
    print("\n📁 清理旧文件...")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
        print(f"  ✓ 已删除 {dist_dir}")
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print(f"  ✓ 已删除 {build_dir}")

    # 删除旧的 zip 文件
    old_zips = list(project_dir.glob("dist*.zip"))
    for old_zip in old_zips:
        old_zip.unlink()
        print(f"  ✓ 已删除 {old_zip.name}")

    # Step 2: 运行 PyInstaller (单文件模式)
    print("\n🔨 运行 PyInstaller...")

    # 动态获取依赖 DLL 路径
    binaries = []

    # 1. glfw3.dll (GLFW 窗口库)
    try:
        import glfw
        glfw_module_path = Path(glfw.__file__).parent
        glfw_dll = glfw_module_path / "glfw3.dll"
        if not glfw_dll.exists():
            print(f"⚠️  找不到 glfw3.dll: {glfw_dll}")
            return 1
        binaries.append((glfw_dll, "."))
        print(f"  ✓ glfw3.dll: {glfw_dll}")
    except ImportError:
        print("❌ 找不到 glfw 模块，请先安装: pip install glfw")
        return 1

    # 2. cimgui.dll (cimgui_py 核心库)
    cimgui_dll = project_dir / "cimgui_py" / "lib" / "cimgui.dll"
    if cimgui_dll.exists():
        binaries.append((cimgui_dll, "."))
        print(f"  ✓ cimgui.dll: {cimgui_dll}")
    else:
        print(f"⚠️  找不到 cimgui.dll: {cimgui_dll}")
        print("     尝试继续打包，但运行时可能出错")

    # 构建 PyInstaller 命令
    cmd = [
        "python", "-m", "PyInstaller",
        "--onefile",    # 单文件模式
        "--noconfirm",  # 覆盖输出目录
        "--clean",      # 清理缓存
    ]

    # 添加所有二进制文件
    for dll_path, target_dir in binaries:
        cmd.extend(["--add-binary", f"{dll_path};{target_dir}"])

    # 添加 cimgui_py 的路径（处理 editable install）
    cimgui_py_src = project_dir / "cimgui_py" / "src"
    if cimgui_py_src.exists():
        cmd.extend(["--paths", str(cimgui_py_src)])

    cmd.append("mod_generator.py")

    print(f"  命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=project_dir)

    if result.returncode != 0:
        print("\n❌ PyInstaller 打包失败!")
        return 1

    print("\n✓ PyInstaller 打包完成")

    # Step 3: 准备发行内容
    zip_name = f"dist_{VERSION_STRING}.zip"
    zip_path = project_dir / zip_name

    # --onefile 模式下 exe 直接在 dist/ 目录
    exe_path = dist_dir / "mod_generator.exe"

    if not exe_path.exists():
        print(f"❌ 找不到可执行文件: {exe_path}")
        return 1

    # 需要额外打包的文件和目录
    extra_files = ["CHANGELOG.md"]
    extra_dirs = ["resources", "fonts"]

    # datamine 运行时数据文件 (代码通过 Path(__file__) 相对路径加载)
    datamine_data_files = [
        "datamine/output/attribute_sources.json",
        "datamine/output/weapon_hands.json",
    ]
    datamine_data_globs = [
        "datamine/output/textloader/attributes/attribute_decimals.json",
        "datamine/output/textloader/attributes/attribute_percent_normalized.json",
        "datamine/output/textloader/attributes/attribute_order_*.json",
    ]

    # 复制额外文件到 dist 目录，方便检查发行内容
    print("\n📋 复制额外文件到 dist/...")
    for filename in extra_files:
        src = project_dir / filename
        if src.exists():
            shutil.copy2(src, dist_dir / filename)
            print(f"  ✓ 已复制 {filename}")

    for dirname in extra_dirs:
        src_dir = project_dir / dirname
        dst_dir = dist_dir / dirname
        if src_dir.exists():
            if dst_dir.exists():
                shutil.rmtree(dst_dir)
            shutil.copytree(src_dir, dst_dir)
            print(f"  ✓ 已复制 {dirname}/")

    # 额外确保打包当前实际使用的字体（支持字体路径不在 fonts/ 下的场景）
    print("\n📋 检查并补充复制当前使用的字体...")
    active_fonts = get_active_font_files(project_dir)
    if not active_fonts:
        print("  ⚠️  未从 ui/font_config.py 解析到字体配置，跳过补充复制")
    for font_path in active_fonts:
        if not font_path.exists():
            print(f"  ⚠️  配置字体不存在: {font_path}")
            continue
        try:
            rel = font_path.relative_to(project_dir)
        except ValueError:
            print(f"  ⚠️  字体不在项目目录内，跳过: {font_path}")
            continue

        dst = dist_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(font_path, dst)
        print(f"  ✓ 已确保字体: {rel}")

    # 复制 datamine 运行时数据
    print("\n📋 复制 datamine 数据文件到 dist/...")
    for filepath in datamine_data_files:
        src = project_dir / filepath
        dst = dist_dir / filepath
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  ✓ 已复制 {filepath}")
        else:
            print(f"  ⚠️  找不到 {filepath}")

    for glob_pattern in datamine_data_globs:
        matches = sorted(project_dir.glob(glob_pattern))
        if not matches:
            print(f"  ⚠️  未匹配到文件: {glob_pattern}")
        for src in matches:
            rel = src.relative_to(project_dir)
            dst = dist_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  ✓ 已复制 {rel}")

    print(f"\n📦 创建压缩包: {zip_name}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 直接打包 dist 目录的所有内容
        for file_path in dist_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(dist_dir)
                zf.write(file_path, arcname)

        # 统计内容
        file_count = sum(1 for _ in dist_dir.rglob('*') if _.is_file())
        print(f"  ✓ 已打包 {file_count} 个文件")

    # 显示压缩包信息
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ 压缩包大小: {zip_size_mb:.1f} MB")

    print("\n" + "=" * 50)
    print(f"✅ 打包完成! 输出文件: {zip_name}")

    return 0


if __name__ == "__main__":
    exit(main())
