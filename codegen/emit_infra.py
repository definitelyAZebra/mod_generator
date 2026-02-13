# -*- coding: utf-8 -*-
"""混合物品基础设施代码生成

生成所有混合物品共享的基础设施，包括：

1. **hover 系统**
   - o_hoverHybrid 对象（Create/Other_20/Other_21/CleanUp 事件）
   - 两个纯 GML 辅助脚本（写入 Codes/ 目录）
   - 脚本注入方法 EnsureHoverScriptsExist()
   - InjectItemStats 辅助方法 + 枚举定义

2. **注册系统**
   - 全局注册表 + Helper 函数
   - bytecode patch（shop/container/item path）
   - 项目特定的注册方法 RegisterHybridItem_{name}()

3. **属性本地化注入**
   - InjectMissingAttributeLocalizations()

依赖：
- codegen.emit_helpers（通用 C# 工具类，附加在文件尾部）
"""
from __future__ import annotations

from core.hybrid_item import HybridItemV2
from core.models import ModProject
from core.specs import WeaponEquip, ArmorEquip, CharmEquip
from constants import (
    CONSUMABLE_INSTANT_ATTRS,
    EXTRA_ORDER_ATTRS,
)


# ======================================================================
# 纯 GML 脚本（输出为独立 .gml 文件，由 orchestrator 写入 Codes/）
# ======================================================================

def emit_ensure_extended_order_lists_gml() -> str:
    """生成 scr_hoversEnsureExtendedOrderLists.gml 脚本内容

    惰性初始化扩展的属性排序列表。
    """
    from constants import ATTRIBUTE_TO_GROUP, DEFAULT_GROUP_ORDER

    group_order_map = {g: i for i, g in enumerate(DEFAULT_GROUP_ORDER)}

    def get_sort_key(attr: str) -> int:
        group = ATTRIBUTE_TO_GROUP.get(attr, "其他")
        return group_order_map.get(group, len(DEFAULT_GROUP_ORDER))

    sorted_attrs = sorted(EXTRA_ORDER_ATTRS, key=get_sort_key)
    extra_attrs_str = ", ".join(f'"{attr}"' for attr in sorted_attrs)

    return f'''function scr_hoversEnsureExtendedOrderLists() {{
    // 额外属性列表（ATTRIBUTE_TO_GROUP 中不在游戏 order lists 的）
    if (!variable_global_exists("attribute_order_extra")) {{
        global.attribute_order_extra = ds_list_create();
        ds_list_add(global.attribute_order_extra, {extra_attrs_str});
    }}

    // 扩展 order_all（包含伤害）
    if (!variable_global_exists("attribute_order_all_extended")) {{
        global.attribute_order_all_extended = ds_list_create();
        var _size = ds_list_size(global.attribute_order_all);
        for (var _i = 0; _i < _size; _i++)
            ds_list_add(global.attribute_order_all_extended, ds_list_find_value(global.attribute_order_all, _i));
        ds_list_add(global.attribute_order_all_extended, global.attribute_order_extra);
    }}

    // 扩展 order_all_without_damage
    if (!variable_global_exists("attribute_order_all_without_damage_extended")) {{
        global.attribute_order_all_without_damage_extended = ds_list_create();
        var _size = ds_list_size(global.attribute_order_all_without_damage);
        for (var _i = 0; _i < _size; _i++)
            ds_list_add(global.attribute_order_all_without_damage_extended, ds_list_find_value(global.attribute_order_all_without_damage, _i));
        ds_list_add(global.attribute_order_all_without_damage_extended, global.attribute_order_extra);
    }}
}}
'''


def emit_draw_hybrid_consum_attrs_gml() -> str:
    """生成 scr_hoversDrawHybridConsumAttributes.gml 脚本内容

    用于绘制消耗品属性，为非即时效果属性显示持续时间。
    """
    instant_attrs: list[str] = []
    for attrs in CONSUMABLE_INSTANT_ATTRS.values():
        instant_attrs.extend(attrs)
    instant_attrs_str = ", ".join(f'"{attr}"' for attr in instant_attrs)

    return f'''function scr_hoversDrawHybridConsumAttributes() {{
    // 使用 GML 内置 argument0-argument7 避免 bytecode 歧义
    var _x = argument0;
    var _y = argument1;
    var _width = argument2;
    var _lineHeight = argument3;
    var _spaceHeight = argument4;
    var _attributesArray = argument5;
    var _duration = argument6;
    var _textScale = argument7;

    // 即时效果属性列表（不显示持续时间）
    var _instantAttrs = [{instant_attrs_str}];

    var _arrLen = array_length(_attributesArray);
    var _durationStr = "N/A";
    var _offsetY = 0;

    if (_duration > 0) {{
        var _space = scr_actionsLogGetSpace();
        var _open = scr_actionsLogGetSymbol("openRoundBracket");
        var _close = scr_actionsLogGetSymbol("closeRoundBracket");
        _durationStr = _space + _open + string(_duration) + _space + ds_list_find_value(global.other_hover, 57) + _close;
    }}

    for (var _i = 0; _i < _arrLen; _i++) {{
        var _part = _attributesArray[_i];
        var _partLen = array_length(_part);

        for (var _j = 0; _j < _partLen; _j += 2) {{
            var _key = _part[_j];
            var _val = scr_hoversGetAttributeValue(_key, _part[_j + 1]);
            var _name = scr_hoversGetAttributeName(_key);
            var _valStr = scr_hoversGetAttributeString(_key, _val);
            var _color = scr_hoversGetAttributeColor(_key, _val, make_colour_rgb(114, 222, 142), make_colour_rgb(158, 27, 49), 16777215);

            scr_drawText(_x, _y + _offsetY, _name, 16777215, 0, 0, global.f_dmg, _textScale);

            // 检查是否为即时效果属性
            var _isInstant = false;
            for (var _k = 0; _k < array_length(_instantAttrs); _k++) {{
                if (_instantAttrs[_k] == _key) {{ _isInstant = true; break; }}
            }}

            if (_duration > 0 && !_isInstant)
                scr_draw_text_doublecolor(_x + _width, _y + _offsetY, _valStr, _durationStr, _color, 16777215, 2, 0, _textScale);
            else
                scr_drawText(_x + _width, _y + _offsetY, _valStr, _color, 2, 0, global.f_dmg, _textScale);

            _offsetY += _lineHeight;
        }}
        _offsetY += _spaceHeight;
    }}
}}
'''


# ======================================================================
# hover 系统 C# 方法（写入 Helpers.cs）
# ======================================================================

def emit_hover_scripts_injection() -> str:
    """生成 EnsureHoverScriptsExist() C# 方法"""
    return '''    private void EnsureHoverScriptsExist()
    {
        // 注入 scr_hoversEnsureExtendedOrderLists
        if (!FunctionExists("scr_hoversEnsureExtendedOrderLists"))
        {
            AddGlobalFunction("scr_hoversEnsureExtendedOrderLists", ModFiles.GetCode("scr_hoversEnsureExtendedOrderLists.gml"));
        }

        // 注入 scr_hoversDrawHybridConsumAttributes
        if (!FunctionExists("scr_hoversDrawHybridConsumAttributes"))
        {
            AddGlobalFunction("scr_hoversDrawHybridConsumAttributes", ModFiles.GetCode("scr_hoversDrawHybridConsumAttributes.gml"));
        }
    }

'''


def emit_hover_hybrid_object(escape_fn) -> str:
    """生成 EnsureHoverHybridExists() C# 方法（创建 o_hoverHybrid 对象）"""
    create_code = _hover_hybrid_create_gml()
    other20_code = _hover_hybrid_other20_gml()
    other21_code = _hover_hybrid_other21_gml()
    cleanup_code = _hover_hybrid_cleanup_gml()

    code = """    private void EnsureHoverHybridExists()
    {
        // 检查 o_hoverHybrid 是否已存在（可能由其他模组创建）
        var existingObj = DataLoader.data.GameObjects.FirstOrDefault(t => t.Name.Content == "o_hoverHybrid");
        if (existingObj != null)
        {
            // 对象已存在，跳过创建
            return;
        }

        // 创建 o_hoverHybrid 对象（继承自 o_hoverRenderContent）
        UndertaleGameObject o_hoverHybrid = Msl.AddObject(
            name: "o_hoverHybrid",
            parentName: "o_hoverRenderContent",
            spriteName: "",
            isVisible: true,
            isPersistent: false,
            isAwake: true
        );

        // 应用事件代码
        o_hoverHybrid.ApplyEvent(
            new MslEvent(eventType: EventType.Create, subtype: 0, code: @"
"""
    code += escape_fn(create_code)
    code += """            "),
            new MslEvent(eventType: EventType.Other, subtype: 20, code: @"
"""
    code += escape_fn(other20_code)
    code += """            "),
            new MslEvent(eventType: EventType.Other, subtype: 21, code: @"
"""
    code += escape_fn(other21_code)
    code += """            "),
            new MslEvent(eventType: EventType.CleanUp, subtype: 0, code: @"
"""
    code += escape_fn(cleanup_code)
    code += """            ")
        );
    }

"""
    return code


# ======================================================================
# InjectItemStats 辅助方法 + 枚举
# ======================================================================

def emit_inject_item_stats() -> str:
    """生成 InjectItemStats C# 辅助方法和相关枚举"""
    return '''    // ============== 物品属性注入辅助类型 ==============

    public enum ItemTier
    {
        None,
        Tier1,
        Tier2,
        Tier3,
        Tier4,
        Tier5
    }

    public enum ItemWeight
    {
        VeryLight,
        Light,
        Medium,
        Heavy,
        Net
    }

    public enum ItemMaterial
    {
        Organic,
        Cloth,
        Leather,
        Wood,
        Paper,
        Pottery,
        Glass,
        Stone,
        Metal,
        Silver,
        Gold,
        Gem
    }

    private static string GetTierValue(ItemTier tier) => tier switch
    {
        ItemTier.Tier1 => "1",
        ItemTier.Tier2 => "2",
        ItemTier.Tier3 => "3",
        ItemTier.Tier4 => "4",
        ItemTier.Tier5 => "5",
        _ => ""
    };

    private static string GetWeightValue(ItemWeight weight) => weight switch
    {
        ItemWeight.VeryLight => "Very Light",
        ItemWeight.Light => "Light",
        ItemWeight.Medium => "Medium",
        ItemWeight.Heavy => "Heavy",
        ItemWeight.Net => "Net",
        _ => "Light"
    };

    private static string GetMaterialValue(ItemMaterial material) => material.ToString().ToLower();

    private void InjectItemStats(
        string id,
        int? Price = null,
        ItemTier tier = ItemTier.None,
        string Cat = "",
        string Subcat = "",
        ItemMaterial Material = ItemMaterial.Organic,
        ItemWeight Weight = ItemWeight.Light,
        string tags = "",
        ushort? Fresh = null,
        ushort? Stacks = null,
        bool Diet = false,
        bool purse = false,
        bool bottle = false,
        string? upgrade = null,
        short? fodder = null,
        short? stack = null,
        bool fireproof = false,
        bool dropsOnce = false)
    {
        const string tableName = "gml_GlobalScript_table_items_stats";
        List<string> table = Msl.ThrowIfNull(ModLoader.GetTable(tableName));

        string tierVal = GetTierValue(tier);
        string weightVal = GetWeightValue(Weight);
        string materialVal = GetMaterialValue(Material);

        // 构建数据行 - 基于 MSL InjectTableItemStats 格式 (100 个分号)
        string newline = $"{id};;{Price};;{tierVal};{Cat};{Subcat};{materialVal};{weightVal};;{Fresh};;{Stacks};{(Diet ? "1" : "")};;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;{(purse ? "1" : "")};{(bottle ? "1" : "")};{upgrade};{fodder};{stack};{(fireproof ? "1" : "")};{(dropsOnce ? "1" : "")};{tags};";

        table.Add(newline);
        ModLoader.SetTable(table, tableName);
    }

'''


# ======================================================================
# 缺失属性本地化注入
# ======================================================================

def emit_missing_attribute_localizations() -> str:
    """生成 InjectMissingAttributeLocalizations() C# 方法"""
    missing_attrs = {
        "Arcanistic_Distance": ("Arcanistic Distance", "奥术距离"),
        "Arcanistic_Miscast_Chance": ("Arcanistic Miscast Chance", "奥术施法失误几率"),
        "Astromantic_Miscast_Chance": ("Astromantic Miscast Chance", "星象施法失误几率"),
        "Avoiding_Trap": ("Trap Avoidance", "陷阱回避"),
        "Bleeding_Chance_Main": ("Main Hand Bleed Chance", "主手流血几率"),
        "Bleeding_Chance_Off": ("Off-Hand Bleed Chance", "副手流血几率"),
        "Bleeding_Resistance_Hands": ("Hands Bleed Resistance", "手部流血抗性"),
        "Bleeding_Resistance_Head": ("Head Bleed Resistance", "头部流血抗性"),
        "Bleeding_Resistance_Legs": ("Legs Bleed Resistance", "腿部流血抗性"),
        "Bleeding_Resistance_Tors": ("Torso Bleed Resistance", "躯干流血抗性"),
        "BlockPowerBonus": ("Block Power Bonus", "格挡力量加成"),
        "CRTD_Main": ("Main Hand Crit Efficiency", "主手暴击效果"),
        "CRTD_Off": ("Off-Hand Crit Efficiency", "副手暴击效果"),
        "CRT_Main": ("Main Hand Crit Chance", "主手暴击几率"),
        "CRT_Off": ("Off-Hand Crit Chance", "副手暴击几率"),
        "Charge_Distance": ("Charge Distance", "冲锋距离"),
        "Cryomantic_Miscast_Chance": ("Cryomantic Miscast Chance", "冰霜施法失误几率"),
        "Duration_Resistance": ("Duration Resistance", "持续时间抗性"),
        "Electromantic_Miscast_Chance": ("Electromantic Miscast Chance", "雷电施法失误几率"),
        "Geomantic_Miscast_Chance": ("Geomantic Miscast Chance", "大地施法失误几率"),
        "HP_turn": ("Health per Turn", "每回合生命"),
        "Immunity_Influence": ("Immunity Influence", "免疫影响"),
        "Psimantic_Miscast_Chance": ("Psimantic Miscast Chance", "灵能施法失误几率"),
        "Pyromantic_Miscast_Chance": ("Pyromantic Miscast Chance", "火焰施法失误几率"),
        "ReputationGainContract": ("Contract Reputation Gain", "合同声望获取"),
        "Venomantic_Miscast_Chance": ("Venomantic Miscast Chance", "毒素施法失误几率"),
        "Weapon_Damage_Main": ("Main Hand Weapon Damage", "主手武器伤害"),
        "Weapon_Damage_Off": ("Off-Hand Weapon Damage", "副手武器伤害"),
    }

    attr_lines: list[str] = []
    for attr_id, (en_text, zh_text) in missing_attrs.items():
        attr_lines.append(f'''            new LocalizationAttribute(
                "{attr_id}",
                new Dictionary<ModLanguage, string>() {{
                    {{ModLanguage.English, "{en_text}"}},
                    {{ModLanguage.Chinese, "{zh_text}"}}
                }}
            )''')

    attrs_code = ",\n".join(attr_lines)

    return f'''    // 注入缺失的属性本地化（使用 Mark 防止重复）
    void InjectMissingAttributeLocalizations()
    {{
        if (Mark.Has(DataLoader.data, "AttrLocInjected")) return;
        Mark.Set(DataLoader.data, "AttrLocInjected");

        AttributeLocalizationHelper.InjectTableAttributesLocalization(
{attrs_code}
        );
    }}

'''


# ======================================================================
# 注册系统
# ======================================================================

def emit_hybrid_registry_helper() -> str:
    """生成 EnsureHybridItemRegistry() 公共 Helper 代码

    包含全局注册表初始化、所有 Helper 函数、bytecode patch。
    """
    # 此函数体过长但是完整的 C# 代码字符串，内容与旧 gml_registry.py 一致
    return '''
    void EnsureHybridItemRegistry()
    {
        // 1. 全局常量定义 (使用独立 InitScript)
        if (!InitScriptExists("hybrid_system_constants"))
        {
            AddInitScript("hybrid_system_constants", @"
global.hybrid_item_registry = {};
global.hybrid_item_by_slot = {};
global.item_table_weapon_slots = [
    ""2haxe"", ""2hmace"", ""2hStaff"", ""2hsword"",
    ""axe"", ""bow"", ""chain"", ""crossbow"",
    ""dagger"", ""lute"", ""mace"", ""pick"",
    ""sling"", ""spear"", ""sword"", ""tool""
];

global.item_table_armor_slots = [
    ""Amulet"", ""Arms"", ""Back"", ""Chest"",
    ""Head"", ""Legs"", ""Ring"", ""shield"", ""Waist""
];
");
        }

        // 2. Helper Functions (使用 AddGlobalFunction)
        // 注意：GML 函数签名保持为空，内部使用 argument0 等访问参数

        if (!FunctionExists("_is_in_array")) {
            AddGlobalFunction("_is_in_array", @"
function _is_in_array() {
    var _value = argument0;
    var _arr = argument1;
    var _len = array_length(_arr);
    for (var i = 0; i < _len; i++) {
        if (_arr[i] == _value) return true;
    }
    return false;
}
");
        }

        if (!FunctionExists("_get_table_by_slot")) {
            AddGlobalFunction("_get_table_by_slot", @"
function _get_table_by_slot() {
    var _slot = argument0;
    if (_is_in_array(_slot, global.item_table_weapon_slots)) return ""weapon"";
    if (_is_in_array(_slot, global.item_table_armor_slots)) return ""armor"";
    return ""unknown"";
}
");
        }

        if (!FunctionExists("_struct_get")) {
            AddGlobalFunction("_struct_get", @"
function _struct_get() {
    var _struct = argument0;
    var _key = argument1;
    var _default = (argument_count > 2) ? argument2 : undefined;
    if (variable_struct_exists(_struct, _key)) {
        return variable_struct_get(_struct, _key);
    }
    return _default;
}
");
        }

        // --- Candidate Finders ---

        if (!FunctionExists("scr_find_item_candidates")) {
            AddGlobalFunction("scr_find_item_candidates", @"
function scr_find_item_candidates() {
    var _options = (argument_count > 0) ? argument0 : {};
    var _candidates = [];
    var _keys = ds_map_keys_to_array(global.weapons_stat);
    var _len = array_length(_keys);

    var _slot            = _struct_get(_options, ""slot"", undefined);
    var _tier_range      = _struct_get(_options, ""tier_range"", undefined);
    var _material        = _struct_get(_options, ""material"", ""all"");
    var _tags            = _struct_get(_options, ""tags"", undefined);
    var _check_repeat    = _struct_get(_options, ""check_repeat"", false);
    var _all_type        = _struct_get(_options, ""all_type"", false);
    var _exclude_special = _struct_get(_options, ""exclude_special"", false);
    var _exclude_slots   = _struct_get(_options, ""exclude_slots"", undefined);
    var _table           = _struct_get(_options, ""table"", ""all"");

    var _special_pool = _exclude_special ? scr_atr(""specialItemsPool"") : undefined;
    var _has_tier_limit = is_array(_tier_range);
    var _tier_min = _has_tier_limit ? _tier_range[0] : 0;
    var _tier_max = _has_tier_limit ? _tier_range[1] : 0;
    var _has_slot_filter = (!is_undefined(_slot));
    var _has_exclude_slots = is_array(_exclude_slots);
    var _filter_table = (_table != ""all"");

    for (var i = 0; i < _len; i++) {
        var _item_id = _keys[i];

        // 优化过滤逻辑：根据数据分析结果
        // 1. 跳过表头行（Key 为 ""name""）
        if (_item_id == ""name"") continue;


        // 2. 跳过分类标题行（Key 以 ""["" 开头）
        if (string_char_at(_item_id, 1) == ""["") continue;

        var _item_data = ds_map_find_value(global.weapons_stat, _item_id);

        if (!ds_exists(_item_data, ds_type_map)) continue;

        var _item_slot = ds_map_find_value(_item_data, ""Slot"");

        if (_filter_table) {
            var _item_table = _get_table_by_slot(_item_slot);
            if (_item_table != _table) continue;
        }

        if (_has_slot_filter) {
            if (_all_type) {
                if (_has_exclude_slots && _is_in_array(_item_slot, _exclude_slots)) continue;
            } else {
                if (_item_slot != _slot) continue;
            }
        }

        var _tier_raw = ds_map_find_value(_item_data, ""Tier"");
        var _tier = 0;

        // 严格模式：非数字且无法转换的值直接跳过
        if (is_real(_tier_raw)) {
            _tier = _tier_raw;
        } else if (is_string(_tier_raw) && string_digits(_tier_raw) != """") {
            // 字符串包含数字，尝试转换
            _tier = real(string_digits(_tier_raw));
        } else {
            // 无法转换，跳过这个物品
            continue;
        }
        if (_has_tier_limit && _tier != 0) {
            if (_tier < _tier_min || _tier > _tier_max) continue;
        }

        if (_material != ""all"") {
            var _mat = string(ds_map_find_value(_item_data, ""Mat""));
            if (!scr_material_compare(_mat, _material)) continue;
        }

        if (!is_undefined(_tags)) {
            var _item_tags_str = ds_map_find_value(_item_data, ""tags"");
            var _item_tags = string_split_custom(_item_tags_str, "" "");
            if (!scr_weapon_tags_compare(_item_tags, _tags)) continue;
        }

        if (_exclude_special && ds_list_find_index(_special_pool, _item_id) != -1) continue;
        if (_check_repeat && ds_list_find_index(global.item_buffer, _item_id) >= 0) continue;

        array_push(_candidates, _item_id);
    }
    return _candidates;
}
");
        }

        if (!FunctionExists("scr_find_hybrid_candidates")) {
            AddGlobalFunction("scr_find_hybrid_candidates", @"
function scr_find_hybrid_candidates() {
    var _options = (argument_count > 0) ? argument0 : {};
    var _candidates = [];

    var _slot            = _struct_get(_options, ""slot"", undefined);
    var _tier_range      = _struct_get(_options, ""tier_range"", undefined);
    var _material        = _struct_get(_options, ""material"", ""all"");
    var _tags            = _struct_get(_options, ""tags"", undefined);
    var _mode            = _struct_get(_options, ""mode"", ""container"");
    var _all_type        = _struct_get(_options, ""all_type"", false);
    var _check_repeat    = _struct_get(_options, ""check_repeat"", false);
    var _exclude_special = _struct_get(_options, ""exclude_special"", false);

    var _special_pool = _exclude_special ? scr_atr(""specialItemsPool"") : undefined;

    var _slots_to_check = [];
    if (!is_undefined(_slot)) {
         if (string_pos("","", _slot) > 0) {
             _slots_to_check = string_split_custom(_slot, "", "", false);
         } else {
             _slots_to_check = [_slot];
         }
    } else if (_all_type) {
         _slots_to_check = variable_struct_get_names(global.hybrid_item_by_slot);
    } else {
         // If no slot and no all_type, assume we check nothing or logic error?
         // Original vanilla usually has slot or table logic.
         // For 'all' table searches, we might check all.
    }

    var _tags_arr = undefined;
    if (!is_undefined(_tags) && _tags != """") _tags_arr = string_split_custom(_tags, "" "");

    var _tmin = -4, _tmax = -4;
    if (is_array(_tier_range)) { _tmin = _tier_range[0]; _tmax = _tier_range[1]; }

    for (var k = 0; k < array_length(_slots_to_check); k++) {
        var _s = _slots_to_check[k];
        _s = string_replace_all(_s, "" "", """");

        if (!variable_struct_exists(global.hybrid_item_by_slot, _s)) continue;

        var _cands = variable_struct_get(global.hybrid_item_by_slot, _s);
        for (var i = 0; i < array_length(_cands); i++) {
            var _id = _cands[i];
            var _data = variable_struct_get(global.hybrid_item_registry, _id);

            if (_mode == ""shop"") {
                if (_data.shop_spawn != ""equipment"") continue;
            } else if (_mode == ""container"") {
                if (_data.container_spawn != ""equipment"") continue;
            }

            if (_tmin != -4) {
                 if (_data.tier < _tmin || _data.tier > _tmax) continue;
            }

            if (_material != ""all"") {
                 // Hybrid doesn't always have material field fully populated for all types?
                 // Model has it.
                 if (!scr_material_compare(_data.material, _material)) continue;
            }

            if (!is_undefined(_tags_arr)) {
                 var _data_tags = string_split_custom(_data.tags, "" "");
                 if (!scr_weapon_tags_compare(_data_tags, _tags_arr)) continue;
            }

            if (_exclude_special && (_data.quality == 6 || _data.quality == 7)) {
                 if (ds_list_find_index(_special_pool, _id) != -1) continue;
            }

            if (_check_repeat && ds_list_find_index(global.item_buffer, _id) >= 0) continue;

            array_push(_candidates, _id);
        }
    }
    return _candidates;
}
");
        }

        if (!FunctionExists("scr_find_unified_item")) {
            AddGlobalFunction("scr_find_unified_item", @"
function scr_find_unified_item() {
    var _options = (argument_count > 0) ? argument0 : {};

    // 1. Resolve vanilla and hybrid candidates
    var _vanilla_pool = scr_find_item_candidates(_options);
    var _hybrid_pool = scr_find_hybrid_candidates(_options);

    var _vanilla_count = array_length(_vanilla_pool);
    var _pool = _vanilla_pool;
    for (var i = 0; i < array_length(_hybrid_pool); i++) {
        array_push(_pool, _hybrid_pool[i]);
    }

    var _winner = -4;
    var _is_hybrid = false;

    if (array_length(_pool) > 0) {
        var _idx = irandom(array_length(_pool) - 1);
        _winner = _pool[_idx];

        if (_idx >= _vanilla_count) _is_hybrid = true;

        var _chk = _struct_get(_options, ""check_repeat"", false);
        if (_struct_get(_options, ""mode"") == ""shop"" && _chk) {
             ds_list_add(global.item_buffer, _winner);
        }

    } else {
        return -4;
    }

    return { id: _winner, is_hybrid: _is_hybrid };
}
");
        }

        if (!FunctionExists("scr_shop_spawn_unified_item")) {
            AddGlobalFunction("scr_shop_spawn_unified_item", @"
function scr_shop_spawn_unified_item() {
    // Args: npc, material, table, all_type, category, quality
    var _npc = argument0;
    var _material = argument1;
    var _table = argument2;
    var _all_type = argument3;
    var _category = argument4;
    var _quality = argument5;

    var _opts = {
        tier_range: [_npc.Equipment_Tier_Min, _npc.Equipment_Tier_Max],
        material: _material,
        tags: _npc.trade_tags,
        check_repeat: true,
        table: _table,
        all_type: _all_type,
        mode: ""shop""
    };

    if (!_all_type) _opts.slot = _category;
    else if (_table == ""armor"") _opts.exclude_slots = [""Ring"", ""Amulet""];

    var _res = scr_find_unified_item(_opts);

    if (_res == -4) return -4; // Failed to find anything

    if (_res.is_hybrid) {
         var _hid = _res.id;
         var _h_obj = asset_get_index(""o_inv_"" + _hid);
         if (object_exists(_h_obj)) {
             // Use scr_inventory_add_item to handle instantiation and adding to shop owner
             return scr_inventory_add_item(_h_obj, _npc);
         }
         return -4;
    } else {
         return scr_inventory_add_weapon(_res.id, _quality, true, true, true, true);
    }
}
");
        }

        if (!FunctionExists("scr_loot_spawn_hybrid")) {
            AddGlobalFunction("scr_loot_spawn_hybrid", @"
function scr_loot_spawn_hybrid() {
    var _hid = argument[0];
    var _x = argument[1];
    var _y = argument[2];
    var _chance = argument[3];
    var _quality = argument[4];
    var _arg5 = (argument_count > 5) ? argument[5] : 1;
    var _arg6 = (argument_count > 6) ? argument[6] : 100;
    var _arg7 = (argument_count > 7) ? argument[7] : false;

    if (irandom(100) > _chance) return -4;

    var _hdata = variable_struct_get(global.hybrid_item_registry, _hid);
    var _isUnique = (_hdata.quality == 6);
    var _isTreasure = (_hdata.quality == 7);
    var _pool = scr_atr(""specialItemsPool"");

    if (_isUnique || _isTreasure) {
         if (ds_list_find_index(_pool, _hid) != -1) return -4;
    }

    var _loot_obj = asset_get_index(""o_loot_"" + _hid);
    if (object_exists(_loot_obj)) {
         var _px = scr_round_cell(_x) + 13;
         var _py = scr_round_cell(_y) + 13;

         // Using 'with' on the result of scr_loot_drop to initialize
         var _drop_inst = scr_loot_drop(_px, _py, _loot_obj, true, _arg5, _arg6, _arg7);
         with (_drop_inst) {
             if (_quality != -4) determined_quality = _quality;
             event_user(1);

             if (_isUnique) {
                  ds_list_add(_pool, _hid);
                  achivmentCounter(5, ""That_Belongs_In_A_Museum"");
                  scr_characterStatsUpdateAdd(""lootedUniques"", 1);
             } else if (_isTreasure) {
                  ds_list_add(_pool, _hid);
                  achivmentCounter(5, ""That_Belongs_In_A_Museum"");
                  scr_characterStatsUpdateAdd(""lootedTreasures"", 1);
             }
         }
         return _drop_inst;
    }
    return -4;
}
");
        }

        if (!FunctionExists("scr_find_item_wrapper")) {
            AddGlobalFunction("scr_find_item_wrapper", @"
function scr_find_item_wrapper() {
    var _type = argument0;
    var _tags = argument1;
    var _tier = argument2;

    var _opts = {
        slot: _type,
        tier_range: _tier,
        tags: _tags,
        exclude_special: true,
        mode: ""container""
    };
    var _res = scr_find_unified_item(_opts);

    if (_res != -4) return _res.id;
    return -4;
}
");
        }

        if (!FunctionExists("scr_inventory_add_item_wrapper")) {
            AddGlobalFunction("scr_inventory_add_item_wrapper", @"
function scr_inventory_add_item_wrapper() {
    var _item = argument0;
    var _quality = argument1;

    if (is_string(_item) && variable_struct_exists(global.hybrid_item_registry, _item)) {
         var _h_obj = asset_get_index(""o_inv_"" + _item);
         if (object_exists(_h_obj)) {
             return scr_inventory_add_item(_h_obj);
         }
         return -4;
    }
    return scr_inventory_add_weapon(_item, _quality);
}
");
        }

        if (!FunctionExists("scr_loot_spawn_wrapper")) {
            AddGlobalFunction("scr_loot_spawn_wrapper", @"
function scr_loot_spawn_wrapper() {
    var _item = argument[0];
    var _x = argument[1];
    var _y = argument[2];
    var _chance = argument[3];
    var _quality = argument[4];
    var _arg5 = (argument_count > 5) ? argument[5] : 1;
    var _arg6 = (argument_count > 6) ? argument[6] : 100;
    var _arg7 = (argument_count > 7) ? argument[7] : false;

    if (is_string(_item) && variable_struct_exists(global.hybrid_item_registry, _item)) {
         return scr_loot_spawn_hybrid(_item, _x, _y, _chance, _quality, _arg5, _arg6, _arg7);
    }
    return scr_weapon_loot(_item, _x, _y, _chance, _quality, _arg5, _arg6, _arg7);
}
");
        }

        // 3. Patch scr_loot_from_tables (Container)
        // 使用 bytecode assembly patch 避免反编译器将 repeat(20) 错误转换为 while(true)
        if (!Mark.Has(DataLoader.data, "patch_scr_loot_from_tables"))
        {
            Msl.LoadAssemblyAsString("gml_GlobalScript_scr_loot_from_tables")
                // Patch 1: scr_find_weapon -> scr_find_item_wrapper (第一处: 循环内)
                .MatchFrom("call.i gml_Script_scr_find_weapon(argc=3)")
                .ReplaceBy("call.i gml_Script_scr_find_item_wrapper(argc=3)")
                // Patch 2: scr_find_weapon -> scr_find_item_wrapper (第二处: 特定槽位)
                .MatchFrom("call.i gml_Script_scr_find_weapon(argc=3)")
                .ReplaceBy("call.i gml_Script_scr_find_item_wrapper(argc=3)")
                // Patch 3: scr_inventory_add_weapon -> scr_inventory_add_item_wrapper
                .MatchFrom("call.i gml_Script_scr_inventory_add_weapon(argc=2)")
                .ReplaceBy("call.i gml_Script_scr_inventory_add_item_wrapper(argc=2)")
                // Patch 4: scr_weapon_loot -> scr_loot_spawn_wrapper
                .MatchFrom("call.i gml_Script_scr_weapon_loot(argc=5)")
                .ReplaceBy("call.i gml_Script_scr_loot_spawn_wrapper(argc=5)")
                .Save();
            Mark.Set(DataLoader.data, "patch_scr_loot_from_tables");
        }

        // 4. Patch o_NPC_Other_24 (Shop)
        if (!Mark.Has(DataLoader.data, "patch_o_NPC_Other_24"))
        {
            Msl.LoadAssemblyAsString("gml_Object_o_NPC_Other_24")
                .MatchFromUntil(@":[55]", @"call.i gml_Script_scr_inventory_add_weapon(argc=6)")
                .ReplaceBy(@":[55]
pushloc.v local._item_quality
pushloc.v local._category
pushloc.v local._all_type
pushloc.v local._table
pushloc.v local.Material_Spec
push.v other.id
call.i gml_Script_scr_shop_spawn_unified_item(argc=6)")
                .Save();
            Mark.Set(DataLoader.data, "patch_o_NPC_Other_24");
        }

        // 5. Non-Equipment Path Support (Item Filter)
        if (!Mark.Has(DataLoader.data, "patch_scr_weapon_array_get_consum"))
        {
            Msl.LoadGML("gml_GlobalScript_scr_weapon_array_get_consum")
                .MatchFrom("if (_item_tags == \\"\\" || __is_undefined(_item_tags) || argument1 == \\"\\")")
                .InsertAbove(@"
                        if (variable_struct_exists(global.hybrid_item_registry, _item_id)) {
                            var _hdata = variable_struct_get(global.hybrid_item_registry, _item_id);
                            if (argument3 == -4) {
                                if (_hdata.shop_spawn != ""item"") continue;
                                if (_hdata.tier > 0 && instance_exists(other) && variable_instance_exists(other, ""Equipment_Tier_Min"")) {
                                    if (_hdata.tier < other.Equipment_Tier_Min || _hdata.tier > other.Equipment_Tier_Max) continue;
                                }
                            } else {
                                if (_hdata.container_spawn != ""item"") continue;
                            }
                        }
")
                .Save();
            Mark.Set(DataLoader.data, "patch_scr_weapon_array_get_consum");
        }

        // 6. Instantiation Helper for Unique in Item Path
        if (!Mark.Has(DataLoader.data, "patch_scr_inventory_add_item"))
        {
            Msl.LoadGML("gml_GlobalScript_scr_inventory_add_item")
                .MatchFrom("with (scr_guiCreateInteractive(global.guiBaseContainerVisible, argument0))")
                .InsertAbove(@"
var _isHybridUnique = false;
if (!is_undefined(argument0) && variable_struct_exists(global.hybrid_item_registry, _idName)) {
    var _hdata = variable_struct_get(global.hybrid_item_registry, _idName);
    if (_hdata.quality == 6) {
        _isHybridUnique = true;
        if (ds_list_find_index(scr_atr(""specialItemsPool""), _idName) != -1) return -4;
    }
}
")
                .MatchFrom("if argument5")
                .InsertAbove(@"
        if _isHybridUnique {
            ds_list_add(scr_atr(""specialItemsPool""), _idName)
            achivmentCounter(5, ""That_Belongs_In_A_Museum"")
            scr_characterStatsUpdateAdd(""lootedUniques"", 1)
        }
")
                .Save();
            Mark.Set(DataLoader.data, "patch_scr_inventory_add_item");
        }
    }

'''


def emit_hybrid_item_registration(
    project: ModProject,
    registered_hybrids: list[HybridItemV2],
) -> str:
    """生成项目特定的混合物品注册方法

    写入主文件。必须在 EnsureHybridItemRegistry() 之后调用。
    """
    if not registered_hybrids:
        return ""

    item_entries: list[str] = []
    for h in registered_hybrids:
        if isinstance(h.equipment, WeaponEquip):
            slot = h.equipment.weapon_type
        elif isinstance(h.equipment, ArmorEquip):
            slot = h.equipment.armor_type
        else:
            slot = h.slot

        match h.equipment:
            case WeaponEquip(): eq_mode = "weapon"
            case ArmorEquip(): eq_mode = "armor"
            case CharmEquip(): eq_mode = "charm"
            case _: eq_mode = "none"

        item_entries.append(
            f'[\"\"{h.id}\"\", \"\"{slot}\"\", {h.tier}, \"\"{h.material}\"\", '
            f'\"\"{h.effective_tags}\"\", \"\"{h.container_spawn.value}\"\", \"\"{h.shop_spawn.value}\"\", '
            f'\"\"{eq_mode}\"\", {h.quality_int}]'
        )

    items_array = ", ".join(item_entries)
    code_name = project.code_name

    return f'''
    void RegisterHybridItem_{code_name}()
    {{
        // 注册本项目的混合物品到全局注册表
        // 必须在 EnsureHybridItemRegistry() 之后调用
        if (!InitScriptExists("{code_name}_hybrid_item"))
        {{
            AddInitScript("{code_name}_hybrid_item", @"
// === {code_name} 混合物品注册 ===
var _items = [{items_array}];
for (var _i = 0; _i < array_length(_items); _i++) {{
    var _item = _items[_i];
    var _id = _item[0];
    var _slot = _item[1];

    // 跳过已注册的物品（避免重复）
    if (variable_struct_exists(global.hybrid_item_registry, _id)) continue;

    var _data = {{
        id: _id,
        slot: _slot,
        tier: _item[2],
        material: _item[3],
        tags: _item[4],
        container_spawn: _item[5],
        shop_spawn: _item[6],
        equipment_mode: _item[7],
        quality: _item[8]
    }};

    variable_struct_set(global.hybrid_item_registry, _id, _data);

    if (!variable_struct_exists(global.hybrid_item_by_slot, _slot)) {{
        variable_struct_set(global.hybrid_item_by_slot, _slot, []);
    }}
    array_push(variable_struct_get(global.hybrid_item_by_slot, _slot), _id);
}}
");
        }}
    }}

'''


# ======================================================================
# o_hoverHybrid GML 事件（内部实现）
# ======================================================================

def _hover_hybrid_create_gml() -> str:
    return """event_inherited();
minWidth = 160 * surfaceScale;
title = "N/A";
titleWidth = 0;
titleHeight = 0;
type = "N/A";
typeColor = 16777215;
typeHeight = 0;
damageAttributesArray = [];
damageAttributesHeight = 0;
attributesArray = [];
attributesHeight = 0;
consumAttributesArray = [];
consumAttributesHeight = 0;

// 武器特有变量
cursedName = "N/A";
cursedNameHeight = 0;
cursedDescription = "N/A";
cursedDescriptionHeight = 0;
cursedAttributesArray = [];
cursedAttributesHeight = 0;
enchantedAttributesArray = [];
enchantedAttributesHeight = 0;
durabilityLeft = "N/A";
durabilityRight = "N/A";
durabilityColor = 16777215;
durabilityHeight = 0;
materialLeft = "N/A";
materialRight = "N/A";
materialColor = 16777215;
materialHeight = 0;

// 消耗品特有变量
attributesDuration = 0;
freshLeft = "N/A";
freshRight = "N/A";
freshColor = 16777215;
freshHeight = 0;
chargesLeft = "N/A";
chargesRight = "N/A";
chargesHeight = 0;

// 通用变量
middleText = "N/A";
middleHeight = 0;
middleTextMap = __dsDebuggerMapCreate();
stolen = "N/A";
stolenHeight = 0;
description = "N/A";
descriptionHeight = 0;
price = 0;
priceSprite = 9729;
priceColor = 16777215;
priceHeight = 0;
"""


def _hover_hybrid_other20_gml() -> str:
    return """event_inherited();

// 确保扩展的 order lists 存在
scr_hoversEnsureExtendedOrderLists();

var _linesHeight = lineHeight;

with (owner)
{
    other.title = scr_loot_name(id);
    other.titleColor = scr_loot_color(id);

    // 智能选择类型文本
    if (variable_instance_exists(id, "type_text") && type_text != "")
        other.type = type_text;
    else if (variable_instance_exists(id, "type"))
        other.type = type;
    else
        other.type = "";

    // 武器/护甲属性
    // 需求2：注释掉 enchantedAttributes 部分，暂时不处理区分
    if (variable_instance_exists(id, "cursedName"))
    {
        other.cursedName = cursedName;
        other.cursedDescription = variable_instance_exists(id, "cursedDesc") ? cursedDesc : "";
        other.cursedAttributesArray = scr_hoversGetCursedAttributes();
    }
    // other.enchantedAttributesArray = scr_hoversGetEnchantedAttributes();

    // 伤害属性（从 data）
    other.damageAttributesArray = scr_hoversGetAttributesPart(data, global.attribute_order_damage, [other.cursedAttributesArray, other.enchantedAttributesArray]);

    // 普通属性（仅显示 data 中的属性 - 武器/装备属性）
    // 需求1：来自 data 的数据用 scr_hoversDrawWeaponAttributes，来自 attributes_data 的数据用 scr_hoversDrawConsumAttributes
    other.attributesArray = scr_hoversGetAttributes(data, global.attribute_order_all_without_damage_extended, [other.cursedAttributesArray, other.enchantedAttributesArray]);

    // 消耗品属性（仅显示 attributes_data 中的属性）
    if (variable_instance_exists(id, "attributes_data") && ds_exists(attributes_data, ds_type_map))
    {
        // 需求5：hover 时动态计算 MoraleDiet 的 _diet_penalty 影响
        // 参考 gml_GlobalScript_scr_consum_get_value_for_hover
        var _moraleDiet = ds_map_find_value(attributes_data, "MoraleDiet");
        if (!is_undefined(_moraleDiet))
        {
            var _diet_penalty = scr_psy_diet_penalty_get(object_get_name(object_index));
            // 临时修改 attributes_data 用于生成 hover 数组，生成后还原（或者直接修改，因为 hover 是每帧调用的？不，hover 生成是一次性的）
            // 注意：attributes_data 是引用，修改会影响原数据。但这里是在 hover 对象中生成数组，
            // scr_hoversGetAttributes 读取 map 生成数组。
            // 为了不破坏源数据，我们可以临时 set，生成完后 restore。
            // 或者更安全地：复制一个 map？(开销大)
            // 实际上 scr_psy_diet_penalty_get 返回的是当前惩罚值。
            // 让我们先修改，再改回去。
            ds_map_replace(attributes_data, "MoraleDiet", _moraleDiet + _diet_penalty);
        }

        other.consumAttributesArray = scr_hoversGetAttributes(attributes_data, global.attribute_order_all_extended, [other.cursedAttributesArray, other.enchantedAttributesArray]);

        // 还原 MoraleDiet
        if (!is_undefined(_moraleDiet))
        {
             ds_map_replace(attributes_data, "MoraleDiet", _moraleDiet);
        }
    }

    // 消耗品效果持续时间
    other.attributesDuration = ds_map_find_value_ext(attributes_data, "Duration", 0);

    // mid_text
    var _middleText = "";
    if (variable_instance_exists(id, "mid_text") && mid_text != "")
        _middleText = mid_text;

    if (scr_caravanPositionGetX() != -1 && scr_caravanPositionGetY() != -1)
    {
        var _upgradesArray = scr_hoversCaravanUpgradesArrayGenerate(id);
        var _upgradesArrayLength = array_length(_upgradesArray);

        for (var _i = 0; _i < _upgradesArrayLength; _i++)
        {
            if (!scr_caravanUpgradeIsOpen(_upgradesArray[_i]))
            {
                _middleText += ((_middleText == "") ? "" : "\\n\\n");
                _middleText += ds_list_find_value_ext(global.caravan_other_text, 7, "N/A");
                break;
            }
        }
    }
    other.middleText = (_middleText == "") ? "N/A" : _middleText;

    // 耐久度（武器特性）
    var _hasDuration = ds_map_exists(data, "Duration") && ds_map_exists(data, "MaxDuration");
    if (_hasDuration)
    {
        var _durability = global.is_devinfo ? scr_inv_atr("Duration") : math_round(scr_inv_atr("Duration"));
        var _durabilityMax = math_round(scr_inv_atr("MaxDuration"));
        if (_durabilityMax > 0)
        {
            other.durabilityLeft = ds_list_find_value(global.weap_param_text, 1) + scr_actionsLogGetSymbol("colon") + scr_actionsLogGetSpace();
            other.durabilityRight = string(_durability) + "/" + string(_durabilityMax);
            other.durabilityColor = (_durability < (_durabilityMax / 2)) ? make_colour_rgb(158, 27, 49) : 16777215;
        }
    }

    // 使用次数（消耗品特性）
    if (variable_instance_exists(id, "draw_charges") && draw_charges)
    {
        other.chargesLeft = ds_list_find_value(global.other_hover, 2) + scr_actionsLogGetSpace();
        other.chargesRight = string(charge) + "/" + string(max_charge);
    }

    // 新鲜度（消耗品特性）
    var _canChange = variable_instance_exists(id, "can_change") ? can_change : false;
    if (_canChange)
    {
        var _fresh = ds_map_find_value(data, "Fresh");
        if (!is_undefined(_fresh) && _fresh > 0)
        {
            var _freshValue = ceil(_fresh / 24);
            other.freshLeft = ds_list_find_value(global.other_hover, 52) + scr_actionsLogGetSpace();
            other.freshRight = string(_freshValue) + scr_actionsLogGetSpace() + scr_pluralFormChoose(_freshValue, ds_list_find_value(global.other_hover, 53));
            other.freshColor = (_freshValue == 1) ? make_colour_rgb(158, 27, 49) : 16777215;
        }
    }

    // 被盗标记
    if (scr_inv_atr("HasOwner") == 2)
    {
        var _townKey = ds_map_find_value_ext(data, "Town", "N/A");
        var _town = ds_map_find_value_ext(global.location_titles, _townKey, "N/A");
        other.stolen = string_replace_all(ds_list_find_value(global.other_hover, 65), "%faction%", _town);
    }

    // 材质（武器特性）
    other.materialLeft = "N/A";
    other.materialRight = "N/A";
    if (variable_instance_exists(id, "Material") && base_price != 0)
    {
        if (instance_exists(o_skill_repair_item_master))
        {
            other.materialLeft = ds_list_find_value_ext(global.weap_param_text, 4, "Material") + scr_actionsLogGetSymbol("colon") + scr_actionsLogGetSpace();
            other.materialRight = scr_stringTransformFirst(ds_map_find_value_ext(global.item_material, Material, Material), true);
        }
    }

    // 价格
    other.price = 0;
    if (base_price != 0)
    {
        if (variable_instance_exists(id, "repair_cost") && repair_cost > 0)
        {
            other.priceSprite = instance_exists(o_skill_ingenuity) ? 4326 : 7398;
            other.price = repair_cost;
            other.priceColor = scr_hoversGetPriceColor(owner, repair_cost, true);
        }
        else
        {
            other.priceSprite = 7395;
            other.price = price;
            other.priceColor = scr_hoversGetPriceColor(owner, price, false);
        }
    }

    other.description = variable_instance_exists(id, "desc") ? desc : "";
}

// 计算布局高度
titleWidth = minWidth - (guiParent.tierDraw ? (30 * surfaceScale) : 0);
title = scr_stringInsertLineBreaks(title, titleWidth, global.f_digits, textScale);
titleHeight = scr_stringGetHeightExt(title, titleWidth, global.f_digits, textScale);
typeHeight = (type == "") ? 0 : fontDmgHeight;

damageAttributesHeight = 0;
var _damageAttributesArrayLength = array_length(damageAttributesArray);
if (_damageAttributesArrayLength > 0)
{
    damageAttributesHeight = (_damageAttributesArrayLength / 2) * fontDmgHeight;
    _linesHeight += lineHeight;
}

attributesHeight = 0;
var _attributesArrayLength = array_length(attributesArray);
if (_attributesArrayLength > 0)
{
    for (var _i = 0; _i < _attributesArrayLength; _i++)
        attributesHeight += ((array_length(attributesArray[_i]) / 2) * fontDmgHeight);
    attributesHeight += ((_attributesArrayLength - 1) * spaceHeight);
}

// 消耗品属性高度
consumAttributesHeight = 0;
var _consumAttributesArrayLength = array_length(consumAttributesArray);
if (_consumAttributesArrayLength > 0)
{
    for (var _i = 0; _i < _consumAttributesArrayLength; _i++)
        consumAttributesHeight += ((array_length(consumAttributesArray[_i]) / 2) * fontDmgHeight);
    consumAttributesHeight += ((_consumAttributesArrayLength - 1) * spaceHeight);
}

cursedNameHeight = 0;
cursedAttributesHeight = 0;
var _cursedAttributesArrayLength = array_length(cursedAttributesArray);
if (_cursedAttributesArrayLength > 0)
{
    cursedNameHeight = scr_stringGetHeightExt(cursedName, minWidth, global.f_dmg, textScale) + spaceHeight;
    cursedAttributesHeight = ((_cursedAttributesArrayLength / 2) * fontDmgHeight) + spaceHeight;
}

    enchantedAttributesHeight = 0;
/*
var _enchantedAttributesArrayLength = array_length(enchantedAttributesArray);
if (_enchantedAttributesArrayLength > 0)
    enchantedAttributesHeight = ((_enchantedAttributesArrayLength / 2) * fontDmgHeight) + spaceHeight;
*/

if (middleText == "N/A")
{
    ds_map_clear(middleTextMap);
    middleHeight = 0;
}
else
{
    scr_colorTextCreate(middleTextMap, middleText, 16777215, minWidth, textScale);
    middleHeight = ds_map_find_value(middleTextMap, "height");
}

materialHeight = (materialLeft == "N/A" && materialRight == "N/A") ? 0 : fontDmgHeight;
durabilityHeight = (durabilityLeft == "N/A" && durabilityRight == "N/A") ? 0 : fontDmgHeight;
freshHeight = (freshLeft == "N/A" && freshRight == "N/A") ? 0 : fontDmgHeight;
chargesHeight = (chargesLeft == "N/A" && chargesRight == "N/A") ? 0 : fontDmgHeight;
stolenHeight = (stolen == "N/A") ? 0 : fontDmgHeight;
description = scr_stringInsertLineBreaks(description, minWidth, global.f_dmg, textScale);
descriptionHeight = scr_stringGetHeightExt(description, minWidth, global.f_dmg, textScale);
priceHeight = (price == 0) ? 0 : fontDmgHeight;

// 间距调整
if (attributesHeight)
{
    if (consumAttributesHeight || middleHeight || freshHeight || chargesHeight || durabilityHeight || materialHeight || stolenHeight)
        attributesHeight += spaceHeight;
}
if (consumAttributesHeight)
{
    if (middleHeight || freshHeight || chargesHeight || durabilityHeight || materialHeight || stolenHeight)
        consumAttributesHeight += spaceHeight;
}

if (middleHeight)
{
    if (freshHeight || chargesHeight || durabilityHeight || materialHeight || stolenHeight)
        middleHeight += spaceHeight;
}
if (freshHeight)
{
    if (chargesHeight || durabilityHeight || materialHeight || stolenHeight)
        freshHeight += spaceHeight;
}
if (chargesHeight)
{
    if (durabilityHeight || materialHeight || stolenHeight)
        chargesHeight += spaceHeight;
}
if (materialHeight)
{
    if (durabilityHeight || stolenHeight)
        materialHeight += spaceHeight;
}
if (durabilityHeight)
{
    if (stolenHeight)
        durabilityHeight += spaceHeight;
}

if (attributesHeight || consumAttributesHeight || middleHeight || freshHeight || chargesHeight || durabilityHeight || materialHeight || stolenHeight)
    _linesHeight += lineHeight;

contentWidth = minWidth;
contentHeight = titleHeight + typeHeight + damageAttributesHeight + attributesHeight + consumAttributesHeight + cursedNameHeight + cursedAttributesHeight + enchantedAttributesHeight + middleHeight + freshHeight + chargesHeight + materialHeight + durabilityHeight + stolenHeight + descriptionHeight + priceHeight + _linesHeight;

"""


def _hover_hybrid_other21_gml() -> str:
    return """event_inherited();
var _offsetY = 0;

// 标题
scr_drawTextExt(contentX + (contentWidth / 2), contentY + _offsetY, title, titleColor, titleWidth, 1, 0, global.f_digits, textScale);
_offsetY += titleHeight;

// 类型
if (typeHeight)
{
    scr_drawText(contentX + (contentWidth / 2), contentY + _offsetY, type, make_colour_rgb(157, 154, 154), 1, 0, global.f_dmg, textScale);
    _offsetY += fontDmgHeight;
}

// 分隔线
scr_hoversDrawLine(contentX, contentY + _offsetY, contentWidth, lineHeight, surfaceScale);
_offsetY += lineHeight;

// 伤害属性
if (damageAttributesHeight)
{
    with (owner)
        scr_hoversDrawDamageAttributes(other.contentX, other.contentY + _offsetY, other.contentWidth, other.fontDmgHeight, other.damageAttributesArray, other.textScale);
    _offsetY += damageAttributesHeight;
}

if (damageAttributesHeight)
{
    scr_hoversDrawLine(contentX, contentY + _offsetY, contentWidth, lineHeight, surfaceScale);
    _offsetY += lineHeight;
}

// 普通属性 ( Weapon / Armor attributes from data )
if (attributesHeight)
{
    with (owner)
        scr_hoversDrawWeaponAttributes(other.contentX, other.contentY + _offsetY, other.contentWidth, other.fontDmgHeight, other.spaceHeight, other.attributesArray, other.textScale);
    _offsetY += attributesHeight;
}

// 消耗品属性 ( Consumable attributes from attributes_data )
if (consumAttributesHeight)
{
    with (owner)
        scr_hoversDrawHybridConsumAttributes(other.contentX, other.contentY + _offsetY, other.contentWidth, other.fontDmgHeight, other.spaceHeight, other.consumAttributesArray, other.attributesDuration, other.textScale);
    _offsetY += consumAttributesHeight;
}

// 诅咒属性（武器特性）
if (cursedAttributesHeight)
{
    scr_drawTextExt(contentX + (contentWidth / 2), contentY + _offsetY, cursedName, make_color_rgb(130, 72, 88), contentWidth, 1, 0, global.f_dmg, textScale);
    _offsetY += cursedNameHeight;
    with (owner)
        scr_hoversDrawWeaponAttributes(other.contentX, other.contentY + _offsetY, other.contentWidth, other.fontDmgHeight, other.spaceHeight, other.cursedAttributesArray, other.textScale);
    _offsetY += cursedAttributesHeight;
}

// 附魔属性（武器特性）- 需求2：注释掉
/*
if (enchantedAttributesHeight)
{
    with (owner)
        scr_hoversDrawWeaponAttributes(other.contentX, other.contentY + _offsetY, other.contentWidth, other.fontDmgHeight, other.spaceHeight, other.enchantedAttributesArray, other.textScale);
    _offsetY += enchantedAttributesHeight;
}
*/

// 中间文本（mid_text）
if (middleHeight)
{
    scr_colorTextDraw(middleTextMap, contentX, contentY + _offsetY);
    _offsetY += middleHeight;
}

// 新鲜度（消耗品特性）
if (freshHeight)
{
    scr_draw_text_doublecolor(contentX, contentY + _offsetY, freshLeft, freshRight, make_colour_rgb(157, 154, 154), freshColor, 0, 0, textScale);
    _offsetY += freshHeight;
}

// 使用次数（消耗品特性）
if (chargesHeight)
{
    scr_draw_text_doublecolor(contentX, contentY + _offsetY, chargesLeft, chargesRight, make_colour_rgb(157, 154, 154), 16777215, 0, 0, textScale);
    _offsetY += chargesHeight;
}

// 材质（武器特性）
if (materialHeight)
{
    scr_draw_text_doublecolor(contentX, contentY + _offsetY, materialLeft, materialRight, make_colour_rgb(157, 154, 154), materialColor, 0, 0, textScale);
    _offsetY += materialHeight;
}

// 耐久度（武器特性）
if (durabilityHeight)
{
    scr_draw_text_doublecolor(contentX, contentY + _offsetY, durabilityLeft, durabilityRight, make_colour_rgb(157, 154, 154), durabilityColor, 0, 0, textScale);
    _offsetY += durabilityHeight;
}

// 被盗标记
if (stolenHeight)
{
    scr_drawText(contentX, contentY + _offsetY, stolen, make_colour_rgb(225, 45, 31), 0, 0, global.f_dmg, textScale);
    _offsetY += stolenHeight;
}

// 分隔线
if (attributesHeight || middleHeight || freshHeight || chargesHeight || durabilityHeight || materialHeight || stolenHeight)
{
    scr_hoversDrawLine(contentX, contentY + _offsetY, contentWidth, lineHeight, surfaceScale);
    _offsetY += lineHeight;
}

// 描述
scr_drawTextExt(contentX, contentY + _offsetY, description, make_colour_rgb(149, 121, 106), contentWidth, 0, 0, global.f_dmg, textScale);
_offsetY += descriptionHeight;

// 价格
if (priceHeight)
    scr_hoversDrawPrice(contentX + contentWidth, contentY + _offsetY, priceSprite, price, priceColor, surfaceScale, textScale);
"""


def _hover_hybrid_cleanup_gml() -> str:
    return """event_inherited();
middleTextMap = __dsDebuggerMapDestroy(middleTextMap);
"""
