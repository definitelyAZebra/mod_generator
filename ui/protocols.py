# -*- coding: utf-8 -*-
"""UI 协议定义 - 为 Mixin 提供类型标注支持

使用 Protocol 和 TYPE_CHECKING 让 Mixin 能够获得完整的类型检查和 IDE 智能提示，
而不需要在运行时引入循环依赖。

使用方式：
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ui.protocols import GUIProtocol

    class SomeMixin:
        def some_method(self: "GUIProtocol"):
            self.project.weapons  # IDE 可以正确推断类型
"""

from typing import TYPE_CHECKING, Protocol, Any

if TYPE_CHECKING:
    from models import ModProject
    import types


class GUIProtocol(Protocol):
    """主 GUI 类的协议定义

    仅保留 ThemeMixin 和 MenuMixin 所需的接口。
    所有编辑器方法已提取为独立模块函数。
    """

    # ==================== 核心属性 ====================
    project: "ModProject"
    layout: "types.ModuleType"  # 向后兼容属性，返回 styles 模块
    font_size: int    # 向后兼容属性，返回 config.get_font_size()
    texture_scale: float  # 向后兼容属性，返回 config.get_texture_scale()

    # ==================== 主题相关 ====================
    theme_colors: dict[str, tuple[float, float, float, float]]

    # ==================== 窗口 ====================
    window: Any  # glfw window
    renderer: Any  # GlfwRenderer

    # ==================== ThemeMixin 方法 ====================
    def apply_theme(self) -> None: ...
    def text_secondary(self, text: str) -> None: ...
    def text_success(self, text: str) -> None: ...
    def text_warning(self, text: str) -> None: ...
    def text_error(self, text: str) -> None: ...
    def text_accent(self, text: str) -> None: ...

    # ==================== MenuMixin 方法 ====================
    def draw_main_menu(self) -> None: ...
