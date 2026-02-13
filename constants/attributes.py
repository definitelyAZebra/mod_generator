# -*- coding: utf-8 -*-
"""
属性分组、属性列表和属性相关常量
"""

# 严格整数属性 (必须为整数的属性，如回合数、格子数)
STRICT_INT_ATTRIBUTES = {
    "Duration",
    "Poison_Duration",
    "Range",
    "Bonus_Range",
    "VSN",
    "Charge_Distance",
    "Arcanistic_Distance",

    # 伤害与防御类 (通常为整数)
    "DEF",
    "Block_Power",
    "Slashing_Damage",
    "Piercing_Damage",
    "Blunt_Damage",
    "Rending_Damage",
    "Fire_Damage",
    "Shock_Damage",
    "Poison_Damage",
    "Caustic_Damage",
    "Frost_Damage",
    "Arcane_Damage",
    "Unholy_Damage",
    "Sacred_Damage",
    "Psionic_Damage",
}

# 特殊步进属性配置
# Key: 属性名
# Value: (float) 编辑器微调步进值 (默认为 0.1)
SPECIAL_STEP_ATTRIBUTES = {
    "hear_value": 0.01,
    "Duration_Resistance": 0.01,
    "Sword_Duration_Resistance": 0.01,
    "Trade_Favorability": 0.01,
    "Fatigue_Change": 0.01,
    "Hunger_Change": 0.01,
    "Thirst_Change": 0.01,
    "Sanity_Change": 0.01,
    "Morale_Change": 0.01,
    "Intoxication_Change": 0.01,
    "Immunity_Change": 0.01,
    "Toxicity_Change": 0.01,
    "Pain_Change": 0.01,
}

# 负面属性 (这些属性的正值表示减益，负值表示增益)
NEGATIVE_ATTRIBUTES = {
    "FMB",
    "Cooldown_Reduction",
    "Abilities_Energy_Cost",
    "Skills_Energy_Cost",
    "Spells_Energy_Cost",
    "Miscast_Chance",
    "Fatigue_Gain",
    "Damage_Received",
}

# 伤害类型属性（用于武器伤害计算）
DAMAGE_ATTRIBUTES = {
    "Slashing_Damage", "Piercing_Damage", "Blunt_Damage", "Rending_Damage",
    "Fire_Damage", "Shock_Damage", "Poison_Damage", "Caustic_Damage",
    "Frost_Damage", "Arcane_Damage", "Unholy_Damage", "Sacred_Damage", "Psionic_Damage",
}


# 效果持续时间属性（控制其他属性是否生效的核心属性）
# 独立提取以便在编辑器中突出显示
CONSUMABLE_DURATION_ATTRIBUTE = "Duration"

# 消耗品分组前缀（用于自动区分即时效果和持续效果）
# 基于 CONSUMABLE_ATTRIBUTE_GROUPS 的命名约定
CONSUMABLE_INSTANT_GROUP_PREFIX = "即时效果"
CONSUMABLE_DURATION_GROUP_PREFIX = "持续效果"


# ============== 统一属性分组映射 ==============
# 每个属性只有一个分组归属（单一来源）
# 基于游戏逻辑：
#   - 抗性层级来自 scr_atr_calc.gml
#   - 属性归类基于功能用途

ATTRIBUTE_TO_GROUP = {
    # === 伤害类型 ===
    "Slashing_Damage": "伤害类型",
    "Piercing_Damage": "伤害类型",
    "Blunt_Damage": "伤害类型",
    "Rending_Damage": "伤害类型",
    "Fire_Damage": "伤害类型",
    "Shock_Damage": "伤害类型",
    "Poison_Damage": "伤害类型",
    "Caustic_Damage": "伤害类型",
    "Frost_Damage": "伤害类型",
    "Arcane_Damage": "伤害类型",
    "Unholy_Damage": "伤害类型",
    "Sacred_Damage": "伤害类型",
    "Psionic_Damage": "伤害类型",

    # === 状态效果（施加） ===
    "Bleeding_Chance": "状态效果",
    "Knockback_Chance": "状态效果",
    "Daze_Chance": "状态效果",
    "Stun_Chance": "状态效果",
    "Immob_Chance": "状态效果",
    "Stagger_Chance": "状态效果",

    # === 防护属性 ===
    "DEF": "防护属性",
    "PRR": "防护属性",
    "Block_Power": "防护属性",
    "Block_Recovery": "防护属性",
    "BlockPowerBonus": "防护属性",
    "EVS": "防护属性",
    "Crit_Avoid": "防护属性",
    "Fortitude": "防护属性",

    # === 战斗属性 ===
    "Hit_Chance": "战斗属性",
    "CRT": "战斗属性",
    "CRTD": "战斗属性",
    "CTA": "战斗属性",
    "FMB": "战斗属性",
    "Weapon_Damage": "战斗属性",
    "Armor_Piercing": "战斗属性",
    "Armor_Damage": "战斗属性",
    "Bodypart_Damage": "战斗属性",
    "Mainhand_Efficiency": "战斗属性",
    "Offhand_Efficiency": "战斗属性",

    # === 生存属性 ===
    "max_hp": "生存属性",
    "HP": "生存属性",
    "Health_Restoration": "生存属性",
    "Healing_Received": "生存属性",
    "Health_Threshold": "生存属性",
    "Pain_Limit": "生存属性",
    "Damage_Received": "生存属性",
    "Damage_Returned": "生存属性",
    "Lifesteal": "生存属性",
    "Manasteal": "生存属性",

    # === 精力相关 ===
    "max_mp": "精力相关",
    "MP": "精力相关",
    "MP_Restoration": "精力相关",
    "Max_Energy_Threshold": "精力相关",
    "Abilities_Energy_Cost": "精力相关",
    "Skills_Energy_Cost": "精力相关",
    "Spells_Energy_Cost": "精力相关",
    "Cooldown_Reduction": "精力相关",
    "Fatigue_Gain": "精力相关",
    "Swimming_Cost": "精力相关",

    # === 魔法属性 ===
    "Magic_Power": "魔法属性",
    "Miscast_Chance": "魔法属性",
    "Miracle_Chance": "魔法属性",
    "Miracle_Power": "魔法属性",
    "Backfire_Damage": "魔法属性",
    "Backfire_Damage_Change": "魔法属性",

    # === 元素法力 ===
    "Pyromantic_Power": "元素法力",
    "Geomantic_Power": "元素法力",
    "Venomantic_Power": "元素法力",
    "Electromantic_Power": "元素法力",
    "Cryomantic_Power": "元素法力",
    "Arcanistic_Power": "元素法力",
    "Astromantic_Power": "元素法力",
    "Psimantic_Power": "元素法力",

    # === 元素法力失误 ===
    "Pyromantic_Miscast_Chance": "元素法力失误",
    "Geomantic_Miscast_Chance": "元素法力失误",
    "Venomantic_Miscast_Chance": "元素法力失误",
    "Electromantic_Miscast_Chance": "元素法力失误",
    "Cryomantic_Miscast_Chance": "元素法力失误",
    "Arcanistic_Miscast_Chance": "元素法力失误",
    "Astromantic_Miscast_Chance": "元素法力失误",
    "Psimantic_Miscast_Chance": "元素法力失误",

    # === 抗性（综合）- 基于 scr_atr_calc.gml ===
    "Physical_Resistance": "抗性（综合）",
    "Nature_Resistance": "抗性（综合）",
    "Magic_Resistance": "抗性（综合）",

    # === 抗性（物理）===
    "Slashing_Resistance": "抗性（物理）",
    "Piercing_Resistance": "抗性（物理）",
    "Blunt_Resistance": "抗性（物理）",
    "Rending_Resistance": "抗性（物理）",

    # === 抗性（元素）===
    "Fire_Resistance": "抗性（元素）",
    "Frost_Resistance": "抗性（元素）",
    "Shock_Resistance": "抗性（元素）",
    "Caustic_Resistance": "抗性（元素）",
    "Poison_Resistance": "抗性（元素）",

    # === 抗性（魔法）===
    "Arcane_Resistance": "抗性（魔法）",
    "Unholy_Resistance": "抗性（魔法）",
    "Sacred_Resistance": "抗性（魔法）",
    "Psionic_Resistance": "抗性（魔法）",

    # === 抗性（状态）===
    "Bleeding_Resistance": "抗性（状态）",
    "Knockback_Resistance": "抗性（状态）",
    "Stun_Resistance": "抗性（状态）",
    "Pain_Resistance": "抗性（状态）",

    # === 生理变化 ===
    "Hunger_Change": "生理变化",
    "Hunger_Resistance": "生理变化",
    "Thirst_Change": "生理变化",
    "Toxicity_Change": "生理变化",
    "Toxicity_Resistance": "生理变化",
    "Pain_Change": "生理变化",
    "Immunity_Change": "生理变化",
    "Immunity_Influence": "生理变化",

    # === 心理变化 ===
    "Sanity_Change": "心理变化",
    "Morale_Change": "心理变化",
    "MoraleTemporary": "心理变化",

    # === 角色属性 ===
    "STR": "角色属性",
    "AGL": "角色属性",
    "PRC": "角色属性",
    "Vitality": "角色属性",
    "WIL": "角色属性",

    # === 其他 ===
    "VSN": "其他",
    "Bonus_Range": "其他",
    "Range": "其他",
    "Received_XP": "其他",
    "Noise_Produced": "其他",
    "ReputationGainContract": "其他",
    "ReputationGainGlobal": "其他",
    "STL": "其他",
    "Savvy": "其他",

    # === Buff专属（仅消耗品持续效果可用）===
    "HP_turn": "Buff专属",
    "MP_turn": "Buff专属",
    "Fatigue_Change": "Buff专属",
    "Charge_Distance": "Buff专属",
    "Arcanistic_Distance": "Buff专属",
    "Duration_Resistance": "Buff专属",
    "Avoiding_Trap": "Buff专属",
    "Trade_Favorability": "Buff专属",
    "Head_DEF": "Buff专属",
    "Body_DEF": "Buff专属",
    "Arms_DEF": "Buff专属",
    "Legs_DEF": "Buff专属",
    "CRTD_Main": "Buff专属",
    "CRTD_Off": "Buff专属",
    "CRT_Main": "Buff专属",
    "CRT_Off": "Buff专属",
    "Weapon_Damage_Main": "Buff专属",
    "Weapon_Damage_Off": "Buff专属",
    "Bleeding_Chance_Main": "Buff专属",
    "Bleeding_Chance_Off": "Buff专属",
    "Bleeding_Resistance_Head": "Buff专属",
    "Bleeding_Resistance_Tors": "Buff专属",
    "Bleeding_Resistance_Hands": "Buff专属",
    "Bleeding_Resistance_Legs": "Buff专属",
}


# ============== 各编辑器支持的属性列表 ==============

# 武器属性（来自 C# API）
WEAPON_ATTRIBUTES = [
    # 伤害类型
    "Slashing_Damage", "Piercing_Damage", "Blunt_Damage", "Rending_Damage",
    "Fire_Damage", "Shock_Damage", "Poison_Damage", "Caustic_Damage",
    "Frost_Damage", "Arcane_Damage", "Unholy_Damage", "Sacred_Damage", "Psionic_Damage",
    # 战斗属性
    "Hit_Chance", "CRT", "CRTD", "CTA", "PRR", "Block_Power", "Block_Recovery", "FMB",
    "Armor_Piercing", "Armor_Damage", "Bodypart_Damage",
    # 状态效果
    "Bleeding_Chance", "Knockback_Chance", "Daze_Chance", "Stun_Chance", "Immob_Chance", "Stagger_Chance",
    # 生存属性
    "max_hp", "Health_Restoration", "Healing_Received", "Crit_Avoid", "Damage_Received", "Lifesteal", "Manasteal",
    # 精力相关
    "MP", "MP_Restoration", "Abilities_Energy_Cost", "Skills_Energy_Cost", "Spells_Energy_Cost", "Cooldown_Reduction",
    # 魔法属性
    "Magic_Power", "Miscast_Chance", "Miracle_Chance", "Miracle_Power",
    # 元素法力
    "Pyromantic_Power", "Geomantic_Power", "Venomantic_Power", "Cryomantic_Power",
    "Electromantic_Power", "Arcanistic_Power", "Astromantic_Power", "Psimantic_Power",
    # 其他
    "Bonus_Range", "Fatigue_Gain",
]

# 护甲属性（来自 C# API）
ARMOR_ATTRIBUTES = [
    # 防护属性
    "DEF", "PRR", "Block_Power", "Block_Recovery", "EVS", "Crit_Avoid",
    # 战斗属性
    "FMB", "Hit_Chance", "Weapon_Damage", "Armor_Piercing", "Armor_Damage", "CRT", "CRTD", "CTA",
    # 生存属性
    "Damage_Received", "Fortitude", "max_hp", "Health_Restoration", "Healing_Received", "Lifesteal", "Manasteal", "Damage_Returned",
    # 精力相关
    "MP", "MP_Restoration", "Abilities_Energy_Cost", "Skills_Energy_Cost", "Spells_Energy_Cost",
    # 魔法属性
    "Magic_Power", "Miscast_Chance", "Miracle_Chance", "Miracle_Power", "Cooldown_Reduction",
    # 元素法力
    "Pyromantic_Power", "Geomantic_Power", "Venomantic_Power", "Electromantic_Power",
    "Cryomantic_Power", "Arcanistic_Power", "Astromantic_Power", "Psimantic_Power",
    # 抗性（状态）
    "Bleeding_Resistance", "Knockback_Resistance", "Stun_Resistance", "Pain_Resistance", "Fatigue_Gain",
    # 抗性（综合）
    "Physical_Resistance", "Nature_Resistance", "Magic_Resistance",
    # 抗性（物理）
    "Slashing_Resistance", "Piercing_Resistance", "Blunt_Resistance", "Rending_Resistance",
    # 抗性（元素）
    "Fire_Resistance", "Shock_Resistance", "Poison_Resistance", "Caustic_Resistance", "Frost_Resistance",
    # 抗性（魔法）
    "Arcane_Resistance", "Unholy_Resistance", "Sacred_Resistance", "Psionic_Resistance",
    # 其他
    "VSN", "Bonus_Range", "Received_XP",
]


# ============== 装备槽位属性分组 ==============
#
# 以下列表按 GML 属性读取路径分组。
# 每组对应一种 scr_atr_calc 中的 SurfaceCall 模式。
# 详细的 GML 函数调用链文档见 datamine/extract_attr_sources.py。
#
# 分组依据 (SlotGroup flag 组合):
#   COMMON     → INV_ALL: scr_inv_param 遍历所有 o_inv_slot 子类 (所有装备+被动物品)
#   COMBAT     → HAND_EFF + NOHAND_INV: 武器手(有效率) + 非手装备
#   DAMAGE     → HAND_EFF only: 仅武器手物品
#   RESISTANCE → ACC_SLOT + ARMOR_SLOT: 饰品逐槽 + 护甲部位
#   DEF        → ARMOR_SLOT only: 仅护甲部位 (head/chest/arms/legs)
#   BUFF_ONLY  → BUFF only: 仅 buff 数据，装备不贡献

# 所有装备共享的通用属性
# SlotGroup: INV_ALL | BUFF
# GML: scr_inv_buff_atr / scr_FullAtr / standalone scr_inv_param
EQUIP_COMMON_ATTRS = [
    # 基础属性
    "STR", "AGL", "PRC", "Vitality", "WIL",
    # 防护
    "PRR", "Block_Power", "BlockPowerBonus", "Block_Recovery",
    "EVS", "CTA", "STL", "Savvy", "VSN", "Bonus_Range",
    # 生存
    "max_hp", "Health_Restoration", "Healing_Received",  # "HP" 已移除，与 max_hp 重复
    "Damage_Received", "Damage_Returned", "Fortitude", "Pain_Resistance",
    "Crit_Avoid", "Knockback_Resistance", "Stun_Resistance",
    # 精力
    "max_mp", "MP_Restoration", "Max_Energy_Threshold",  # "MP" 已移除，与 max_mp 重复
    "Abilities_Energy_Cost", "Skills_Energy_Cost", "Spells_Energy_Cost",
    "Cooldown_Reduction", "Fatigue_Gain", "Swimming_Cost",
    # 魔法
    "Magic_Power", "Miscast_Chance", "Miracle_Chance", "Miracle_Power",
    "Backfire_Damage", "Backfire_Damage_Change",
    # 元素法力
    "Pyromantic_Power", "Geomantic_Power", "Venomantic_Power", "Cryomantic_Power",
    "Electromantic_Power", "Arcanistic_Power", "Astromantic_Power", "Psimantic_Power",
    "Pyromantic_Miscast_Chance", "Geomantic_Miscast_Chance", "Venomantic_Miscast_Chance",
    "Cryomantic_Miscast_Chance", "Electromantic_Miscast_Chance", "Arcanistic_Miscast_Chance",
    "Astromantic_Miscast_Chance", "Psimantic_Miscast_Chance",
    # 生理/心理
    "Hunger_Change", "Hunger_Resistance", "Thirst_Change",
    "Toxicity_Change", "Toxicity_Resistance", "Pain_Change",
    "Immunity_Change", "Immunity_Influence",
    "Sanity_Change", "Morale_Change", "MoraleTemporary",
    # 其他
    "Mainhand_Efficiency", "Offhand_Efficiency",
    "Received_XP", "Noise_Produced", "ReputationGainGlobal", "ReputationGainContract",
    "Range",
]

# 武器战斗属性 — 所有装备都有，但武器手有效率 (Efficiency) 加成
# SlotGroup: HAND_EFF | NOHAND_INV | BUFF
# GML: scr_inv_param(attr, _mainHandItem) * efficiency + scr_inv_param(attr, 4479, true) + scr_buff_param(attr)
EQUIP_COMBAT_ATTRS = [
    "Hit_Chance", "CRT", "CRTD", "FMB", "Weapon_Damage",
    "Armor_Damage", "Armor_Piercing", "Bodypart_Damage",
    "Lifesteal", "Manasteal",
    "Bleeding_Chance", "Daze_Chance", "Stun_Chance",
    "Knockback_Chance", "Immob_Chance", "Stagger_Chance",
]

# 伤害类型属性 — 仅武器手物品 (护甲/饰品不贡献)
# SlotGroup: HAND_EFF | BUFF
# GML: scr_inv_param(attr, _mainHandItem) * efficiency + scr_buff_param(attr)
EQUIP_DAMAGE_ATTRS = [
    "Slashing_Damage", "Piercing_Damage", "Blunt_Damage", "Rending_Damage",
    "Fire_Damage", "Frost_Damage", "Shock_Damage", "Poison_Damage", "Caustic_Damage",
    "Arcane_Damage", "Unholy_Damage", "Sacred_Damage", "Psionic_Damage",
]

# 抗性属性 — 通过 scr_inv_buff_param_ext / scr_resistance_calc 逐槽位累加
# SlotGroup: ACC_SLOT | PASSIVE_CONSUM | BUFF (+ ARMOR_SLOT for sub-resistances)
# GML:
#   综合抗性/Health_Threshold → scr_inv_buff_param_ext (饰品7槽 + 被动消耗品 + buff)
#   子类抗性 → scr_resistance_calc = scr_inv_buff_param_ext + scr_inv_param_slot(头/胸/手/腿)
EQUIP_RESISTANCE_ATTRS = [
    "Physical_Resistance", "Nature_Resistance", "Magic_Resistance",
    "Slashing_Resistance", "Piercing_Resistance", "Blunt_Resistance", "Rending_Resistance",
    "Fire_Resistance", "Frost_Resistance", "Shock_Resistance", "Caustic_Resistance", "Poison_Resistance",
    "Arcane_Resistance", "Unholy_Resistance", "Sacred_Resistance", "Psionic_Resistance",
    "Bleeding_Resistance", "Health_Threshold",
]

# DEF 属性 — 仅护甲部位 (head/chest/arms/legs) + buff
# SlotGroup: ARMOR_SLOT | BUFF
# GML: scr_def_calc 中 scr_buff_param("DEF") + scr_inv_param_slot("DEF", 4 armor slots)
EQUIP_DEF_ATTRS = ["DEF"]

# Buff 专属属性 — 仅 buff 数据层，装备无法提供
# SlotGroup: BUFF only
# GML: 仅通过 scr_buff_param 读取，不经过任何 scr_inv_param* 函数
# 典型用途: 消耗品持续效果、技能 buff
EQUIP_BUFF_ONLY_ATTRS = [
    "HP_turn", "MP_turn", "Fatigue_Change",
    "Charge_Distance", "Arcanistic_Distance",
    "Duration_Resistance", "Avoiding_Trap", "Trade_Favorability",
    "DEF", "Head_DEF", "Body_DEF", "Arms_DEF", "Legs_DEF",
    "CRTD_Main", "CRTD_Off", "CRT_Main", "CRT_Off",
    "Weapon_Damage_Main", "Weapon_Damage_Off",
    "Bleeding_Chance_Main", "Bleeding_Chance_Off",
    "Bleeding_Resistance_Head", "Bleeding_Resistance_Tors",
    "Bleeding_Resistance_Hands", "Bleeding_Resistance_Legs",
]


def get_equip_attrs_for_slot(slot: str, has_passive: bool = False) -> list[str]:
    """根据装备槽位返回可编辑的属性列表。

    基于 GML 属性计算系统中各槽位的属性读取覆盖范围:
      - COMMON + COMBAT: 所有装备/消耗品都有
      - DAMAGE: 仅武器手 (伤害类型)
      - DEF: 仅护甲部位 (scr_def_calc)
      - RESISTANCE: 饰品/护甲/被动消耗品 (scr_inv_buff_param_ext / scr_resistance_calc)

    Args:
        slot: 装备槽位
            "hand"  → 武器 (DAMAGE + RESISTANCE)
            "Head"/"Chest"/"Arms"/"Legs" → 护甲 (DEF + RESISTANCE)
            "Ring"/"Amulet"/"Waist"/"Back" → 饰品 (RESISTANCE)
            "heal" → 消耗品 (has_passive=True 时加 RESISTANCE)
        has_passive: 是否为被动携带物品 (check_inventory_data=true)
    """
    result = list(EQUIP_COMMON_ATTRS) + list(EQUIP_COMBAT_ATTRS)

    if slot == "hand":
        result.extend(EQUIP_DAMAGE_ATTRS)
        result.extend(EQUIP_RESISTANCE_ATTRS)
    elif slot in ("Head", "Chest", "Arms", "Legs"):
        result.extend(EQUIP_DEF_ATTRS)
        result.extend(EQUIP_RESISTANCE_ATTRS)
    elif slot in ("Ring", "Amulet", "Waist", "Back"):
        result.extend(EQUIP_RESISTANCE_ATTRS)
    elif slot == "heal" and has_passive:
        # 被动携带物品: 经过 scr_inv_param 遍历，与普通装备相同
        result.extend(EQUIP_RESISTANCE_ATTRS)
    # else: 纯消耗品 (slot=heal, has_passive=false): 仅通用 + 战斗

    return result


def get_consumable_buff_attrs() -> list[str]:
    """获取消耗品持续效果 (buff) 可用属性。

    消耗品通过 buff 机制生效时可以影响所有类型的属性:
    通用 + 战斗 + 伤害 + 抗性 + buff 专属 (如 HP_turn, Head_DEF)
    """
    return (list(EQUIP_COMMON_ATTRS) + list(EQUIP_COMBAT_ATTRS) +
            list(EQUIP_DAMAGE_ATTRS) + list(EQUIP_RESISTANCE_ATTRS) +
            list(EQUIP_BUFF_ONLY_ATTRS))


# 即时效果属性（独立case处理，不需要duration）
CONSUMABLE_INSTANT_ATTRS = {
    "即时效果（生理）": ["Hunger", "Thirsty", "Intoxication", "Pain", "Fatigue"],
    "即时效果（心理）": ["SanitySituational", "MoraleSituational", "MoraleDiet"],
    "即时效果（恢复）": ["max_hp_res", "max_mp_res", "Immunity", "Condition"],
    "即时效果（负面几率）": ["Poisoning_Chance", "Nausea_Chance"],
}


def get_attribute_groups(attr_list: list[str], group_order: list[str] | None = None) -> dict[str, list[str]]:
    """根据属性列表动态生成分组

    Args:
        attr_list: 属性名列表
        group_order: 可选的分组排序列表

    Returns:
        {分组名: [属性列表]}，按 group_order 排序（如提供）
    """
    groups = {}
    for attr in attr_list:
        group = ATTRIBUTE_TO_GROUP.get(attr, "其他")
        groups.setdefault(group, []).append(attr)

    # 如果提供了排序，按顺序返回
    if group_order:
        sorted_groups = {}
        for group in group_order:
            if group in groups:
                sorted_groups[group] = groups.pop(group)
        # 添加剩余未排序的组
        sorted_groups.update(groups)
        return sorted_groups

    return groups


# 推荐的分组顺序
DEFAULT_GROUP_ORDER = [
    "伤害类型", "状态效果", "防护属性", "战斗属性", "生存属性", "精力相关",
    "魔法属性", "元素法力", "元素法力失误",
    "抗性（综合）", "抗性（物理）", "抗性（元素）", "抗性（魔法）", "抗性（状态）",
    "生理变化", "心理变化", "角色属性", "Buff专属", "其他",
]

# ATTRIBUTE_TO_GROUP 中不在游戏 order lists 的额外属性
# 这些属性需要追加到扩展 order list 中才能在 hover 中显示
EXTRA_ORDER_ATTRS = (
    "AGL", "Arcanistic_Distance", "Arcanistic_Miscast_Chance", "Arms_DEF",
    "Astromantic_Miscast_Chance", "Avoiding_Trap", "Bleeding_Chance_Main",
    "Bleeding_Chance_Off", "Bleeding_Resistance_Hands", "Bleeding_Resistance_Head",
    "Bleeding_Resistance_Legs", "Bleeding_Resistance_Tors", "BlockPowerBonus",
    "Body_DEF", "CRTD_Main", "CRTD_Off", "CRT_Main", "CRT_Off", "Charge_Distance",
    "Cryomantic_Miscast_Chance", "Duration_Resistance", "Electromantic_Miscast_Chance",
    "Geomantic_Miscast_Chance", "Head_DEF", "Immunity_Influence", "Legs_DEF",
    "MoraleTemporary", "PRC", "Psimantic_Miscast_Chance", "Pyromantic_Miscast_Chance",
    "Range", "STR", "Venomantic_Miscast_Chance", "Vitality", "WIL",
    "Weapon_Damage_Main", "Weapon_Damage_Off",
)

# ============== 预计算的属性分组（模块级常量）==============
# 避免每帧重复计算

WEAPON_ATTR_GROUPS = get_attribute_groups(WEAPON_ATTRIBUTES, DEFAULT_GROUP_ORDER)
ARMOR_ATTR_GROUPS = get_attribute_groups(ARMOR_ATTRIBUTES, DEFAULT_GROUP_ORDER)


# ============== 向后兼容别名 ==============
# 旧名: HYBRID_* / get_hybrid_* — 已重命名为 EQUIP_* / get_equip_*
# 保留别名以避免破坏未更新的调用方

HYBRID_COMMON_ATTRS = EQUIP_COMMON_ATTRS
HYBRID_COMBAT_ATTRS = EQUIP_COMBAT_ATTRS
HYBRID_DAMAGE_ATTRS = EQUIP_DAMAGE_ATTRS
HYBRID_RESISTANCE_ATTRS = EQUIP_RESISTANCE_ATTRS
HYBRID_DEF_ATTRS = EQUIP_DEF_ATTRS
HYBRID_BUFF_ONLY_ATTRS = EQUIP_BUFF_ONLY_ATTRS
get_hybrid_attrs_for_slot = get_equip_attrs_for_slot
get_consumable_duration_attrs = get_consumable_buff_attrs
