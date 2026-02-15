# -*- coding: utf-8 -*-
"""代码生成器 — 组装门面（组合式）

CodeGenerator 通过调用 emit_* 纯函数模块组装最终输出：

  emit_helpers  — 通用 C# 工具类（Mark / FunctionExists / …）
  emit_items    — 原版武器/护甲注入方法
  emit_hybrids  — 混合物品注入方法（含嵌入 GML 事件）
  emit_infra    — 跨项目共享基础设施（hover / registry / bytecode patch）

贴图处理工具函数位于 codegen.textures（纯函数）。
"""
from __future__ import annotations

from core.hybrid_item import HybridItemV2
from core.models import ModProject

from codegen import emit_helpers, emit_items, emit_hybrids, emit_infra


class CodeGenerator:
    """C# 模组代码生成器"""

    def __init__(self, project: ModProject):
        self.project = project

    # ------------------------------------------------------------------
    # Shared utility
    # ------------------------------------------------------------------

    def _escape_multiline_string(self, text: str) -> str:
        """转义多行字符串用于 C# verbatim string (@"...")

        在 verbatim string 中，双引号需要用两个双引号转义
        """
        if not text:
            return ""
        # 在 C# verbatim string 中，" 需要转义为 ""
        return text.replace('"', '""')

    @property
    def registered_hybrids(self) -> list[HybridItemV2]:
        """获取所有需要注册的混合物品"""
        return [h for h in self.project.hybrid_items if h.needs_registration]

    # ------------------------------------------------------------------
    # Public API（orchestrator 使用）
    # ------------------------------------------------------------------

    def generate_ensure_extended_order_lists_gml(self) -> str:
        """生成 scr_hoversEnsureExtendedOrderLists.gml 内容"""
        return emit_infra.emit_ensure_extended_order_lists_gml()

    def generate_draw_hybrid_consum_attrs_gml(self) -> str:
        """生成 scr_hoversDrawHybridConsumAttributes.gml 内容"""
        return emit_infra.emit_draw_hybrid_consum_attrs_gml()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate(self) -> dict[str, str]:
        """生成完整的 C# 模组代码

        Returns:
            dict[str, str]: 文件名到内容的映射
                - "{code_name}.cs": 主文件，包含 PatchMod() 和物品方法
                - "{code_name}.Helpers.cs": 辅助文件，包含所有 helper 方法
        """
        code_namespace = self.project.code_name.strip() or "ModNamespace"
        has_hybrids = bool(self.project.hybrid_items)
        escape_fn = self._escape_multiline_string

        # ==================== 主文件 ====================
        main_code = f"""using ModShardLauncher;
using ModShardLauncher.Mods;
using UndertaleModLib;
using UndertaleModLib.Models;
using System.Collections.Generic;
using System.Linq;

namespace {code_namespace};
public partial class {code_namespace} : Mod
{{
    public override string Author => "{self.project.author}";
    public override string Name => "{self.project.name}";
    public override string Description => @"{escape_fn(self.project.description)}";
    public override string Version => "{self.project.version}";
    public override string TargetVersion => "{self.project.target_version}";

    public override void PatchMod()
    {{
"""

        # 如果有混合物品，先注入辅助脚本和 o_hoverHybrid（只需要一次）
        if has_hybrids:
            main_code += "        // 注入缺失的属性本地化（仅执行一次，使用 Mark 防止重复）\n"
            main_code += "        InjectMissingAttributeLocalizations();\n\n"
            main_code += "        // 注入 hover 辅助脚本（仅执行一次）\n"
            main_code += "        EnsureHoverScriptsExist();\n"
            main_code += "        // 注入混合物品专用 hover 对象（仅执行一次）\n"
            main_code += "        EnsureHoverHybridExists();\n"
            # 仅当有装备路径混合物品时才调用注册系统
            if self.registered_hybrids:
                main_code += "        // 注入混合装备注册系统（公共 Helper，仅执行一次）\n"
                main_code += "        EnsureHybridItemRegistry();\n"
                main_code += f"        // 注册本项目的混合装备（项目特定）\n"
                main_code += f"        RegisterHybridItem_{self.project.code_name}();\n"
            main_code += "\n"

        for weapon in self.project.weapons:
            main_code += f"        Add{weapon.id}();\n"
        for armor in self.project.armors:
            main_code += f"        AddArmor{armor.id}();\n"
        for hybrid in self.project.hybrid_items:
            main_code += f"        AddHybrid{hybrid.id}();\n"

        main_code += "    }\n\n"

        for item in self.project.weapons + self.project.armors:
            main_code += emit_items.emit_item_method(item)

        for hybrid in self.project.hybrid_items:
            main_code += emit_hybrids.emit_hybrid_item_method(hybrid, escape_fn)

        # 生成项目特定的混合装备注册方法（写入主文件）
        if self.registered_hybrids:
            main_code += emit_infra.emit_hybrid_item_registration(
                self.project, self.registered_hybrids,
            )

        main_code += "}\n"

        # ==================== 辅助文件 ====================
        helpers_code = f"""using ModShardLauncher;
using ModShardLauncher.Mods;
using UndertaleModLib;
using UndertaleModLib.Models;
using System.Collections.Generic;
using System.Linq;

namespace {code_namespace};

// ============== 辅助方法（partial class） ==============
public partial class {code_namespace}
{{
"""

        # 只在有混合物品时生成辅助方法
        if has_hybrids:
            helpers_code += emit_infra.emit_missing_attribute_localizations()
            helpers_code += emit_infra.emit_hover_scripts_injection()
            helpers_code += emit_infra.emit_hover_hybrid_object(escape_fn)
            helpers_code += emit_infra.emit_inject_item_stats()
            # 仅当有装备路径混合物品时才生成公共 Helper 方法
            if self.registered_hybrids:
                helpers_code += emit_infra.emit_hybrid_registry_helper()
            # 关闭 partial class 并添加 Mark 等辅助类
            helpers_code += emit_helpers.emit_csharp_utility_functions()
        else:
            helpers_code += "    // 无混合物品，无需辅助方法\n}\n"

        return {
            f"{code_namespace}.cs": main_code,
            f"{code_namespace}.Helpers.cs": helpers_code,
        }
