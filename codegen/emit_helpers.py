# -*- coding: utf-8 -*-
"""通用 C# 辅助代码生成

生成被 Helpers.cs 底部共享的工具代码：
- FunctionExists / InitScriptExists / RegisterToGlobalInit
- AddGlobalFunction / AddInitScript
- Mark 标记类（防重复 patch）
- AttributeLocalizationHelper + LocalizationAttribute（属性本地化注入）

这些代码是所有混合物品基础设施（hover / registry）的叶子依赖。
"""
from __future__ import annotations


# ------------------------------------------------------------------
# C# helper: 脚本管理函数 + Mark + AttributeLocalizationHelper
# ------------------------------------------------------------------

def emit_csharp_utility_functions() -> str:
    """生成通用 C# 工具函数 + 辅助类

    输出内容直接拼接到 Helpers.cs 的 partial class **尾部**，
    包含 partial class 的右花括号以及随后的独立类定义。
    """
    return '''
    bool FunctionExists(string functionName)
    {
        string codeName = $"gml_GlobalScript_{functionName}";
        return DataLoader.data.Code.ByName(codeName) != null
            || DataLoader.data.Scripts.ByName(functionName) != null
            || DataLoader.data.Functions.ByName(functionName) != null;
    }

    bool InitScriptExists(string scriptId)
    {
        string codeName = $"gml_GlobalScript_init_{scriptId}";
        return DataLoader.data.Code.ByName(codeName) != null;
    }

    void RegisterToGlobalInit(UndertaleCode code)
    {
        if (DataLoader.data.GlobalInitScripts.Any(g => g.Code?.Name?.Content == code.Name?.Content))
            return;

        UndertaleGlobalInit globalInit = new UndertaleGlobalInit();
        globalInit.Code = code;
        DataLoader.data.GlobalInitScripts.Add(globalInit);
    }

    void AddGlobalFunction(string functionName, string gmlCode)
    {
        string codeName = $"gml_GlobalScript_{functionName}";

        // Code
        UndertaleCode code = new UndertaleCode();
        code.Name = DataLoader.data.Strings.MakeString(codeName);
        DataLoader.data.Code.Add(code);

        // CodeLocals
        UndertaleCodeLocals locals = new UndertaleCodeLocals();
        locals.Name = code.Name;
        DataLoader.data.CodeLocals.Add(locals);

        // 编译
        code.ReplaceGML(gmlCode, DataLoader.data);

        // Script
        UndertaleScript script = new UndertaleScript();
        script.Name = DataLoader.data.Strings.MakeString(functionName);
        script.Code = code;
        DataLoader.data.Scripts.Add(script);

        // GlobalInit
        RegisterToGlobalInit(code);
    }

    void AddInitScript(string scriptId, string gmlCode)
    {
        string codeName = $"gml_GlobalScript_init_{scriptId}";

        // Code
        UndertaleCode code = new UndertaleCode();
        code.Name = DataLoader.data.Strings.MakeString(codeName);
        DataLoader.data.Code.Add(code);

        // CodeLocals
        UndertaleCodeLocals locals = new UndertaleCodeLocals();
        locals.Name = code.Name;
        DataLoader.data.CodeLocals.Add(locals);

        // 编译
        code.ReplaceGML(gmlCode, DataLoader.data);

        // GlobalInit
        RegisterToGlobalInit(code);
    }

}

// ============== Patch 标记辅助类 ==============

public static class Mark
{
    const string PREFIX = "__MK_";

    public static bool Has(UndertaleData data, string name)
    {
        return data.Scripts.ByName(PREFIX + name) != null;
    }

    public static void Set(UndertaleData data, string name)
    {
        string fullName = PREFIX + name;
        if (data.Scripts.ByName(fullName) != null) return;

        var str = data.Strings.MakeString(fullName);
        var code = new UndertaleCode { Name = str };
        data.Code.Add(code);

        data.Scripts.Add(new UndertaleScript
        {
            Name = str,
            Code = code
        });
    }

    public static void Remove(UndertaleData data, string name)
    {
        string fullName = PREFIX + name;
        var script = data.Scripts.ByName(fullName);
        if (script == null) return;

        if (script.Code != null)
            data.Code.Remove(script.Code);
        data.Scripts.Remove(script);
    }

    public static IEnumerable<string> GetAll(UndertaleData data)
    {
        return data.Scripts
            .Where(s => s.Name.Content.StartsWith(PREFIX))
            .Select(s => s.Name.Content.Substring(PREFIX.Length));
    }
}

// ============== 属性本地化辅助类 ==============

public class LocalizationAttribute : ILocalizationElement
{
    public string Id { get; }
    public Dictionary<ModLanguage, string> Text { get; }

    public LocalizationAttribute(string id, Dictionary<ModLanguage, string> text)
    {
        Id = id;
        Text = Localization.SetDictionary(text);
    }

    public IEnumerable<string> CreateLine(string? selector)
    {
        switch(selector)
        {
            case "text":
                yield return $"{Id};{string.Concat(Text.Values.Select(x => @$"{x};"))}";
                break;
        }
    }
}

public static class AttributeLocalizationHelper
{
    public static Func<IEnumerable<string>, IEnumerable<string>> CreateInjectionAttributesLocalization(params LocalizationAttribute[] attributes)
    {
        LocalizationBaseTable localizationBaseTable = new(
            ("attribute_text_end;", "text")
        );
        return localizationBaseTable.CreateInjectionTable(attributes.Select(x => x as ILocalizationElement).ToList());
    }

    public static void InjectTableAttributesLocalization(params LocalizationAttribute[] attributes)
    {
        Localization.InjectTable("gml_GlobalScript_table_attributes", CreateInjectionAttributesLocalization(attributes));
    }
}

'''
