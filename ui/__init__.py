# -*- coding: utf-8 -*-
"""UI 模块 - Stoneshard 装备模组编辑器

使用惰性加载优化启动性能。子模块在首次访问时才导入。

模块结构：
- styles.py: 核心样式系统 (StyleContext, 颜色/尺寸函数)
- tw.py: Tailwind-style tokens (bg_slate_800, text_white, p_4, ...)
- config.py: 全局配置状态 (get_font_scale, ...)
- fonts.py: 字体管理 (load_fonts, 字体路径常量)
- texture_manager.py: 贴图加载与缓存
- dialogs.py: 对话框模块函数
- popups.py: 弹窗服务
- menu.py: 主菜单

[已废弃，保留向后兼容]:
- theme.py: 主题色板定义 → 将合并到 tw.py

使用方式：
    from ui import tw
    with tw.bg_slate_800 | tw.text_white | tw.p_4:
        imgui.text("Hello!")
"""

from typing import TYPE_CHECKING

# =============================================================================
# 惰性加载映射
# =============================================================================
# 模块名 -> 导入路径
_LAZY_MODULES = {
    'config': 'ui.config',
    'styles': 'ui.styles',
    'tw': 'ui.tw',            # Tailwind-style tokens
    'theme': 'ui.theme',      # 主题色板 (crystal/abyss/parchment/...)
    'fonts': 'ui.fonts',
    'texture_manager': 'ui.texture_manager',
    'menu': 'ui.menu',
    'popups': 'ui.popups',
    'dialogs': 'ui.dialogs',
    'components': 'ui.components',  # Styled UI components
}

# 属性名 -> (模块路径, 属性名)
# 现在从 styles.py 导入 sizing 和 theme 相关内容
_LAZY_ATTRS = {
    # fonts
    'load_fonts': ('ui.fonts', 'load_fonts'),
    'compute_font_px': ('ui.fonts', 'compute_font_px'),
    'update_font_scale': ('ui.fonts', 'update_font_scale'),
    # texture_manager
    'load_texture': ('ui.texture_manager', 'load_texture'),
    'unload_all_textures': ('ui.texture_manager', 'unload_all_textures'),
    'draw_checkerboard': ('ui.texture_manager', 'draw_checkerboard'),
}

# 已加载的缓存
_loaded_modules: dict = {}
_loaded_attrs: dict = {}


def __getattr__(name: str):
    """惰性加载模块和属性

    Python 3.7+ 模块级 __getattr__，在访问未定义属性时调用。
    """
    # 先检查模块
    if name in _LAZY_MODULES:
        if name not in _loaded_modules:
            import importlib
            _loaded_modules[name] = importlib.import_module(_LAZY_MODULES[name])
        return _loaded_modules[name]

    # 再检查属性
    if name in _LAZY_ATTRS:
        if name not in _loaded_attrs:
            import importlib
            module_path, attr_name = _LAZY_ATTRS[name]
            module = importlib.import_module(module_path)
            _loaded_attrs[name] = getattr(module, attr_name)
        return _loaded_attrs[name]

    raise AttributeError(f"module 'ui' has no attribute {name!r}")


def __dir__():
    """支持自动补全"""
    return list(_LAZY_MODULES.keys()) + list(_LAZY_ATTRS.keys())


# 类型协议（仅用于类型检查，不影响运行时）
if TYPE_CHECKING:
    from ui import config as config
    from ui import styles as styles
    from ui.fonts import load_fonts as load_fonts
    from ui.fonts import compute_font_px as compute_font_px
    from ui.fonts import update_font_scale as update_font_scale
    from ui.texture_manager import (
        load_texture as load_texture,
        unload_all_textures as unload_all_textures,
        draw_checkerboard as draw_checkerboard,
    )


__all__ = [
    # 子模块
    'config', 'styles', 'tw', 'fonts',
    'texture_manager', 'menu', 'popups', 'dialogs',
    # fonts
    'load_fonts', 'compute_font_px', 'update_font_scale',
    # texture_manager
    'load_texture', 'unload_all_textures', 'draw_checkerboard',
]
