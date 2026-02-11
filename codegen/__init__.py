# -*- coding: utf-8 -*-
"""代码生成包

将 ModProject 模型编译为 C# / GML 代码。

子模块:
- codegen.generator: CodeGenerator 类 + 贴图处理工具
- codegen.orchestrator: 高层验证/生成流程 (由 UI 调用)
"""

from codegen.generator import CodeGenerator, copy_item_textures_v2

__all__ = ["CodeGenerator", "copy_item_textures_v2"]
