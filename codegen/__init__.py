# -*- coding: utf-8 -*-
"""代码生成包

将 ModProject 模型编译为 C# / GML 代码。

子模块:
- codegen.generator       : CodeGenerator 门面类（组合式）
- codegen.textures         : 贴图处理工具函数
- codegen.emit_helpers     : 通用 C# 工具类（Mark / FunctionExists / …）
- codegen.emit_items       : 原版武器/护甲 C# 注入方法
- codegen.emit_hybrids     : 混合物品 C# 方法 + 嵌入 GML 事件
- codegen.emit_infra       : 跨项目共享基础设施（hover / registry / bytecode patch）
- codegen.orchestrator     : 高层验证/生成流程 (由 UI 调用)
"""

from codegen.generator import CodeGenerator
from codegen.textures import copy_item_textures_v2

__all__ = ["CodeGenerator", "copy_item_textures_v2"]
