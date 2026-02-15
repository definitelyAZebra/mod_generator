# -*- coding: utf-8 -*-
"""
属性分组、属性列表和属性相关常量

数据来源:
  - datamine/output/attribute_sources.json:
      属性槽位元数据 — 三层 flag 架构 (GML datamined)
  - datamine/output/textloader/attributes/:
      属性精度、tooltip 分组顺序 (textLoader datamined)

架构:
  §1 DATAMINED DATA  — 直接从 JSON 加载
  §2 MANUAL CONFIG   — 需要人工维护的配置
  §3 COMPUTED         — 模块加载时自动计算
  §4 OTHER CONSTANTS — 与 slot/group 重构无关的常量
  §5 PRECOMPUTED
"""
from __future__ import annotations

import json
from pathlib import Path


# =============================================================================
# §1 DATAMINED DATA — 直接从 JSON 加载
# =============================================================================

_DATAMINE_DIR = Path(__file__).resolve().parent.parent / "datamine" / "output"
_ATTR_ORDER_DIR = _DATAMINE_DIR / "textloader" / "attributes"


def _load_json(path: Path) -> dict | list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- 属性精度数据 (来自游戏 o_textLoader 加载的 ds_map) ---

# {attr_name: decimals} — 游戏 tooltip 显示使用的小数位数
# 不在此 dict 中的属性 → 游戏用 math_round() 取整
ATTRIBUTE_DECIMALS: dict[str, int] = _load_json(
    _ATTR_ORDER_DIR / "attribute_decimals.json"
)

# 百分比归一化属性 — 游戏 tooltip 会先 ×100 再四舍五入
# 影响编辑器中 raw 值需要的小数精度
PERCENT_NORMALIZED_ATTRIBUTES: frozenset[str] = frozenset(
    _load_json(_ATTR_ORDER_DIR / "attribute_percent_normalized.json")
)


def get_attr_format(attr: str) -> tuple[bool, str]:
    """根据游戏数据决定属性编辑器输入精度。

    对应 GML: scr_hoversGetAttributeValue(attr, value)
        decimals = attribute_decimals[attr]  // -1 if missing
        if attr in attribute_percent_normalized:
            value *= 100
        return decimals == -1 ? round(value) : math_precision(value, decimals)

    Returns:
        (is_int, format_str):
        - is_int=True, format_str=""  → 使用 input_int
        - is_int=False, format_str="%.Nf" → 使用 input_float

    编辑器中 raw 值精度计算:
        - 不在 decimals → int
        - 在 decimals, 不在 pct_norm → %.{d}f
        - 不在 decimals, 在 pct_norm → %.2f  (整数%显示, raw 需 2 位)
        - 在 decimals, 在 pct_norm → %.{d+2}f  (raw 多 2 位补偿 ×100)
    """
    decimals = ATTRIBUTE_DECIMALS.get(attr)
    is_pct = attr in PERCENT_NORMALIZED_ATTRIBUTES

    if decimals is None:
        if is_pct:
            return False, "%.2f"
        return True, ""

    raw_decimals = decimals + 2 if is_pct else decimals
    return False, f"%.{raw_decimals}f"


# --- 属性来源元数据 (attribute_sources.json) ---

_ATTR_SOURCES: dict = _load_json(_DATAMINE_DIR / "attribute_sources.json")

# {attr_name: {surface_calls, slot_groups, equip_slots, has_efficiency, has_body_parts, clamp}}
_ATTR_META: dict[str, dict] = _ATTR_SOURCES["attributes"]


# --- 属性 tooltip 分组顺序 (textLoader order files) ---

# 元列表和非编辑器文件 — 不参与分组映射
# all / all_without_damage: 仅为 tooltip 排序用的全量列表
# damage_self: 14 个 *_Self 变体, 不在 attribute_sources 中
_ORDER_SKIP = {"all", "all_without_damage", "damage_self"}

_ORDER_GROUPS: dict[str, list[str]] = {}
for _f in sorted(_ATTR_ORDER_DIR.glob("attribute_order_*.json")):
    _gid = _f.stem.replace("attribute_order_", "")
    if _gid not in _ORDER_SKIP:
        _ORDER_GROUPS[_gid] = _load_json(_f)


# =============================================================================
# §2 MANUAL CONFIG — 需要人工维护的配置
# =============================================================================

# --- Order file gid → 英文 group ID ---
# key = order file basename (去掉 attribute_order_ 前缀和 .json 后缀)
# value = 编辑器内部使用的英文 group ID
#
# 新增 order file 时, 在此添加映射即可自动纳入分组系统。
# 两个 key 映射到同一 value 表示合并分组。
_ORDER_FILE_TO_GROUP: dict[str, str] = {
    "damage":              "damage",
    "effect_chances":      "effect_chances",
    "deffence_stats":      "defence",              # NOTE: 游戏原始拼写 "deffence"
    "attack_stats":        "attack",
    "attack_modifiers":    "attack",                # 合并: 攻击修正 (Weapon_Damage 等) 归入战斗属性
    "health_energy":       "health_energy",
    "abilities_modifiers": "abilities",
    "magic_stats":         "magic",
    "general_resists":     "resist_general",
    "damage_resists":      "resist_damage",
    "effect_resists":      "resist_effect",
    "survival_resists":    "resist_survival",
    "survival_changes":    "survival_changes",
    "basic_needs":         "basic_needs",
    "other":               "other",
}


# --- Group ID → 中文显示标签 (唯一中文来源) ---
GROUP_LABELS: dict[str, str] = {
    "damage":           "伤害类型",
    "effect_chances":   "状态效果",
    "defence":          "防护属性",
    "attack":           "战斗属性",
    "health_energy":    "生命与精力",
    "abilities":        "技能消耗",
    "magic":            "魔法属性",
    "miscast":          "元素法力失误",
    "resist_general":   "抗性（综合）",
    "resist_damage":    "抗性（伤害）",
    "resist_effect":    "抗性（状态）",
    "resist_survival":  "生存抗性",
    "basic_needs":      "基本需求",
    "survival_changes": "生存变化",
    "base_stats":       "角色属性",
    "buff_only":        "Buff专属",
    "other":            "其他",
}


# --- EXTRA 属性分组 ---
# 在 attribute_sources 中但不在任何 order file 的属性。
# 原因:
#   1. order files 来自 textLoader tooltip — 只包含 tooltip 显示的属性
#   2. 以下属性虽然参与 scr_atr_calc 计算, 但游戏 tooltip 不单独列出
#   3. 部分因游戏拼写不一致 (MoralTemporary/MoraleTemporary, Rng/Range) 落入 EXTRA
#
# 维护: 新增 datamine 属性如果缺少 order file 映射, 需要手动添加到
# 某个分组或 _SOURCES_BLACKLIST 中。
_EXTRA_ATTR_GROUPS: dict[str, list[str]] = {
    "base_stats": [
        # scr_FullAtr 直接读取的五围, textLoader 无 tooltip order
        "STR", "AGL", "PRC", "Vitality", "WIL",
    ],
    "miscast": [
        # scr_inv_buff_atr 读取, 与 *_Power 对称但 textLoader 无 order
        "Pyromantic_Miscast_Chance", "Geomantic_Miscast_Chance",
        "Venomantic_Miscast_Chance", "Cryomantic_Miscast_Chance",
        "Electromantic_Miscast_Chance", "Arcanistic_Miscast_Chance",
        "Astromantic_Miscast_Chance", "Psimantic_Miscast_Chance",
    ],
    "defence": [
        # BlockPowerBonus: scr_inv_buff_atr 读取但 tooltip 不单独显示
        "BlockPowerBonus",
    ],
    "survival_changes": [
        # MoraleTemporary: 游戏 order file 中拼为 "MoralTemporary" (少了 e),
        # attribute_sources 中为 "MoraleTemporary", 因拼写不匹配成为 EXTRA
        "MoraleTemporary",
        # Immunity_Influence: 免疫影响系数, 与 Immunity_Change 同属生存系统
        "Immunity_Influence",
    ],
    "other": [
        # Range: order file 中拼为 "Rng", sources 中为 "Range", 因名称不匹配成为 EXTRA
        "Range",
    ],
    "buff_only": [
        # === buff 数据层独有的变体属性 (仅 scr_buff_param 读取) ===
        # 部位 DEF (对应 scr_def_calc 中的 buff 部位加成)
        "Head_DEF", "Body_DEF", "Arms_DEF", "Legs_DEF",
        # 主副手战斗属性 (对应双持/盾反的独立计算)
        "CRT_Main", "CRT_Off", "CRTD_Main", "CRTD_Off",
        "Weapon_Damage_Main", "Weapon_Damage_Off",
        "Bleeding_Chance_Main", "Bleeding_Chance_Off",
        # 部位出血抗性 (对应 scr_buff_param 的逐部位读取)
        "Bleeding_Resistance_Head", "Bleeding_Resistance_Tors",
        "Bleeding_Resistance_Hands", "Bleeding_Resistance_Legs",
        # 距离/持续/特殊
        "Charge_Distance", "Arcanistic_Distance",
        "Duration_Resistance", "Sword_Duration_Resistance",
        "Avoiding_Trap",
    ],
}


# --- 属性来源黑名单 ---
# 在 attribute_sources 中但不应出现在编辑器属性列表中的属性。
# 被黑名单的属性不会进入 get_equip_attrs_for_slot、EXTRA_ORDER_ATTRS。
# ATTRIBUTE_TO_GROUP 不受影响 (如果 order file 包含则仍有映射)。
_SOURCES_BLACKLIST: frozenset[str] = frozenset({
    # DMG: GML 内部的聚合伤害值 (scr_inv_param("DMG", ...)),
    # 编辑器通过 13 种具体伤害类型 (Slashing_Damage 等) 编辑。
    "DMG",
    # HP: 与 max_hp 在 GML 计算中重复使用, 编辑器仅使用 max_hp。
    "HP",
    # MP: 与 max_mp 在 GML 计算中重复使用, 编辑器仅使用 max_mp。
    "MP",
})


# --- 分组覆盖 ---
# 当 order file 的 tooltip 分组不适合编辑器语义时的手动修正。
_GROUP_OVERRIDES: dict[str, str] = {
    # DEF 出现在 attribute_order_damage 是因为游戏 damage tooltip 中
    # 将 DEF 作为上下文显示, 但在编辑器中 DEF 语义上属于防护属性。
    "DEF": "defence",
}


# --- 编辑器分组排序 (英文 group ID) ---
DEFAULT_GROUP_ORDER: list[str] = [
    "damage",
    "effect_chances",
    "defence",
    "attack",
    "health_energy",
    "abilities",
    "magic",
    "miscast",
    "resist_general",
    "resist_damage",
    "resist_effect",
    "resist_survival",
    "basic_needs",
    "survival_changes",
    "base_stats",
    "buff_only",
    "other",
]


# --- 装备槽位 → equip_slots key 映射 ---
_SLOT_KEY: dict[str, str] = {
    "hand": "hand",
    "Head": "armor", "Chest": "armor", "Arms": "armor", "Legs": "armor",
    "Ring": "accessory", "Amulet": "accessory", "Waist": "accessory", "Back": "accessory",
}


# =============================================================================
# §3 COMPUTED — 模块加载时自动计算
# =============================================================================

# --- ATTRIBUTE_TO_GROUP (attr → 英文 group ID) ---

def _build_attribute_to_group() -> dict[str, str]:
    """从 order files + EXTRA 配置 + 覆盖 构建 attr→group 映射。

    优先级: _GROUP_OVERRIDES > _EXTRA_ATTR_GROUPS > order files (先匹配的 file 优先)
    """
    mapping: dict[str, str] = {}

    # 1. Order files → 分组 (先匹配的 file 优先)
    for gid, attrs in _ORDER_GROUPS.items():
        group = _ORDER_FILE_TO_GROUP.get(gid)
        if group is None:
            continue
        for attr in attrs:
            if attr not in mapping:
                mapping[attr] = group

    # 2. EXTRA → 分组
    for group, attrs in _EXTRA_ATTR_GROUPS.items():
        for attr in attrs:
            mapping[attr] = group

    # 3. 覆盖 (最高优先级)
    for attr, group in _GROUP_OVERRIDES.items():
        mapping[attr] = group

    return mapping


ATTRIBUTE_TO_GROUP: dict[str, str] = _build_attribute_to_group()


# --- EXTRA_ORDER_ATTRS (在 sources 但不在 order files 的属性) ---

def _compute_extra_order_attrs() -> tuple[str, ...]:
    """EXTRA = attribute_sources 中存在但不在任何 order file 中的属性。

    这些属性需要追加到扩展 order list 中才能在 hover 中显示。
    """
    all_order: set[str] = set()
    for attrs in _ORDER_GROUPS.values():
        all_order.update(attrs)

    return tuple(sorted(
        attr for attr in _ATTR_META
        if attr not in all_order and attr not in _SOURCES_BLACKLIST
    ))


EXTRA_ORDER_ATTRS: tuple[str, ...] = _compute_extra_order_attrs()


# --- 装备槽位属性查询 (直接基于 equip_slots) ---

_FILTERED_ATTRS: dict[str, dict] = {
    attr: meta for attr, meta in _ATTR_META.items()
    if attr not in _SOURCES_BLACKLIST
}


def get_equip_attrs_for_slot(slot: str, has_passive: bool = False) -> list[str]:
    """根据装备槽位返回可编辑的属性列表。

    直接查询 attribute_sources.json 的 equip_slots 字段。
    一个属性只要 equip_slots 包含该槽位对应的 key, 就可编辑。

    Args:
        slot: 装备槽位
            "hand" → 武器 (equip_slots contains "hand")
            "Head"/"Chest"/"Arms"/"Legs" → 护甲 (contains "armor")
            "Ring"/"Amulet"/"Waist"/"Back" → 饰品 (contains "accessory")
            "heal" → 消耗品
                has_passive=True → passive_consum
                has_passive=False → 无装备属性 (仅 buff / instant)
        has_passive: 是否为被动携带物品 (check_inventory_data=true)
    """
    if slot == "heal":
        if not has_passive:
            return []
        key = "passive_consum"
    else:
        key = _SLOT_KEY.get(slot)
        if key is None:
            return []

    return [attr for attr, meta in _FILTERED_ATTRS.items() if key in meta["equip_slots"]]


def get_consumable_buff_attrs() -> list[str]:
    """获取消耗品持续效果 (buff) 可用属性。

    消耗品通过 buff 机制生效时, 属性直接写入 buff 数据层,
    因此所有 equip_slots 含 "buff" 的属性均可使用。
    """
    return [attr for attr, meta in _FILTERED_ATTRS.items() if "buff" in meta["equip_slots"]]


def get_attribute_groups(
    attr_list: list[str],
    group_order: list[str] | None = None,
) -> dict[str, list[str]]:
    """根据属性列表动态生成分组。

    Args:
        attr_list: 属性名列表
        group_order: 可选的分组排序列表 (英文 group ID)

    Returns:
        {group_id: [属性列表]}，按 group_order 排序（如提供）
    """
    groups: dict[str, list[str]] = {}
    for attr in attr_list:
        group = ATTRIBUTE_TO_GROUP.get(attr, "other")
        groups.setdefault(group, []).append(attr)

    if group_order:
        sorted_groups: dict[str, list[str]] = {}
        for group in group_order:
            if group in groups:
                sorted_groups[group] = groups.pop(group)
        sorted_groups.update(groups)
        return sorted_groups

    return groups


# =============================================================================
# §4 OTHER CONSTANTS — 与 slot/group 重构无关的常量
# =============================================================================

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
CONSUMABLE_DURATION_ATTRIBUTE = "Duration"

# 消耗品分组前缀（用于自动区分即时效果和持续效果）
CONSUMABLE_INSTANT_GROUP_PREFIX = "即时效果"
CONSUMABLE_DURATION_GROUP_PREFIX = "持续效果"


# --- 各编辑器支持的属性列表 (来自 C# API) ---

# 武器属性
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

# 护甲属性
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


# 即时效果属性（独立case处理，不需要duration）
CONSUMABLE_INSTANT_ATTRS = {
    "即时效果（生理）": ["Hunger", "Thirsty", "Intoxication", "Pain", "Fatigue"],
    "即时效果（心理）": ["SanitySituational", "MoraleSituational", "MoraleDiet"],
    "即时效果（恢复）": ["max_hp_res", "max_mp_res", "Immunity", "Condition"],
    "即时效果（负面几率）": ["Poisoning_Chance", "Nausea_Chance"],
}


# =============================================================================
# §5 PRECOMPUTED
# =============================================================================

# 避免每帧重复计算
WEAPON_ATTR_GROUPS = get_attribute_groups(WEAPON_ATTRIBUTES, DEFAULT_GROUP_ORDER)
ARMOR_ATTR_GROUPS = get_attribute_groups(ARMOR_ATTRIBUTES, DEFAULT_GROUP_ORDER)
