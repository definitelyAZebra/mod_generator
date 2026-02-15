# -*- coding: utf-8 -*-
"""
物品/武器/护甲相关枚举和标签常量
"""

from __future__ import annotations

# ============== 通用枚举类型 ==============

# 等级（武器/护甲共用）
TIER = ["Tier1", "Tier2", "Tier3", "Tier4", "Tier5"]
TIER_LABELS = {tier: str(idx + 1) for idx, tier in enumerate(TIER)}

# 稀有度标签
RARITY_LABELS = {"Common": "普通", "Unique": "独特"}

# ============== 武器相关枚举 ==============

# 武器槽位标签
SLOT_LABELS = {
    "dagger": "匕首",
    "mace": "单手锤棒",
    "sword": "单手刀剑",
    "axe": "单手斧",
    "bow": "弓",
    "crossbow": "弩",
    "twohandedmace": "双手锤棒",
    "twohandedsword": "双手刀剑",
    "twohandedaxe": "双手斧",
    "spear": "长杆刃器",
    "twohandedstaff": "长杖",
    "chain": "锁链",
    "lute": "鲁特琴",
}

# 武器材料标签
WEAPON_MATERIAL_LABELS = {"wood": "木", "metal": "金属", "leather": "皮"}

# 通用标签（武器/护甲共用）
TAG_LABELS = {
    "aldor": "奥尔多",
    "elven": "精灵",
    "fjall": "弗约",
    "magic": "魔法",
    "nistra": "尼斯特拉",
    "skadia": "斯卡迪亚",
    "special": "特殊",
    "unique": "独特",
    "special exc": "特殊（新英雄）",
}

# 武器槽位平衡值
SLOT_BALANCE = {
    "twohandedaxe": 0,
    "twohandedmace": 0,
    "twohandedstaff": 2,
    "twohandedsword": 0,
    "axe": 3,
    "bow": 0,
    "crossbow": 0,
    "dagger": 4,
    "mace": 1,
    "sword": 2,
    "lute": 2,
    "chain": 2,
}

# 支持左手持握的槽位 (单手武器)
LEFT_HAND_SLOTS = ["dagger", "mace", "sword", "axe"]

# ============== 护甲/装备相关枚举 ==============

# 护甲钩子标签
ARMOR_HOOK_LABELS = {
    "SHIELDS": "盾牌",
    "HELMETS": "头盔",
    "CHESTPIECES": "胸甲",
    "GLOVES": "手套",
    "BOOTS": "靴子",
    "BELTS": "腰带",
    "RINGS": "戒指",
    "NECKLACES": "项链",
    "CLOAKS": "披风",
}

# 护甲槽位标签
ARMOR_SLOT_LABELS = {
    "shield": "盾牌",
    "Head": "头部",
    "Chest": "胸部",
    "Arms": "手臂",
    "Legs": "腿部",
    "Waist": "腰部",
    "Ring": "戒指",
    "Amulet": "护身符",
    "Back": "背部",
}

# Hook 和 Slot 的绑定关系
ARMOR_HOOK_TO_SLOT = {
    "SHIELDS": "shield",
    "HELMETS": "Head",
    "CHESTPIECES": "Chest",
    "GLOVES": "Arms",
    "BOOTS": "Legs",
    "BELTS": "Waist",
    "RINGS": "Ring",
    "NECKLACES": "Amulet",
    "CLOAKS": "Back",
}

ARMOR_SLOT_TO_HOOK = {v: k for k, v in ARMOR_HOOK_TO_SLOT.items()}

# 护甲类别标签
ARMOR_CLASS_LABELS = {
    "Light": "轻甲",
    "Medium": "中甲",
    "Heavy": "重甲",
}

# 护甲材料标签
ARMOR_MATERIAL_LABELS = {
    "wood": "木",
    "leather": "皮",
    "metal": "金属",
    "cloth": "布料",
    "silver": "银",
    "gold": "金",
    "gem": "宝石",
}

# 需要角色贴图预览的槽位
ARMOR_SLOTS_WITH_CHAR_PREVIEW = ["shield", "Head", "Chest", "Arms", "Legs", "Back"]

# 需要多姿势穿戴贴图的装备槽位 (头/身/手/腿/背)
# 游戏姿势系统：
# - 站立姿势0: 单手武器/盾牌/长杆 → s_char_{id}_0.png (帧序列第0帧)
# - 站立姿势1: 其他双手武器 → s_char_{id}_1.png (帧序列第1帧，可选)
# - 休息姿势: 休息状态 → s_char3_{id}.png (独立贴图槽)
# 注：游戏用 s_char 帧序列的两帧存储站立姿势，导致这些装备无法支持动画
ARMOR_SLOTS_MULTI_POSE = ["Head", "Chest", "Arms", "Legs", "Back"]

# ============== 拆解材料 ==============

ARMOR_FRAGMENT_LABELS = {
    "fragment_cloth01": "布料碎片 1",
    "fragment_cloth02": "布料碎片 2",
    "fragment_cloth03": "布料碎片 3",
    "fragment_cloth04": "布料碎片 4",
    "fragment_leather01": "皮革碎片 1",
    "fragment_leather02": "皮革碎片 2",
    "fragment_leather03": "皮革碎片 3",
    "fragment_leather04": "皮革碎片 4",
    "fragment_metal01": "金属碎片 1",
    "fragment_metal02": "金属碎片 2",
    "fragment_metal03": "金属碎片 3",
    "fragment_metal04": "金属碎片 4",
    "fragment_gold": "金块碎片",
}

# ============== 物品类型配置 ==============


def _build_item_type_config() -> dict:
    """延迟构建 ITEM_TYPE_CONFIG 以避免循环导入"""
    from constants.hybrid import HYBRID_SLOT_LABELS

    return {
        "weapon": {
            "type_name": "武器",
            "slot_labels": SLOT_LABELS,
        },
        "armor": {
            "type_name": "装备",
            "slot_labels": ARMOR_SLOT_LABELS,
        },
        "hybrid": {
            "type_name": "混合物品",
            "slot_labels": HYBRID_SLOT_LABELS,
        },
    }


# 延迟初始化的物品类型配置
class _LazyItemTypeConfig:
    """Lazy proxy to avoid circular import between items.py and hybrid.py"""

    _cache: dict | None = None

    def __getitem__(self, key: str):
        if self._cache is None:
            self._cache = _build_item_type_config()
        return self._cache[key]

    def __contains__(self, key: str):
        if self._cache is None:
            self._cache = _build_item_type_config()
        return key in self._cache

    def __iter__(self):
        if self._cache is None:
            self._cache = _build_item_type_config()
        return iter(self._cache)

    def items(self):
        if self._cache is None:
            self._cache = _build_item_type_config()
        return self._cache.items()

    def keys(self):
        if self._cache is None:
            self._cache = _build_item_type_config()
        return self._cache.keys()

    def values(self):
        if self._cache is None:
            self._cache = _build_item_type_config()
        return self._cache.values()

    def get(self, key: str, default=None):
        if self._cache is None:
            self._cache = _build_item_type_config()
        return self._cache.get(key, default)


ITEM_TYPE_CONFIG = _LazyItemTypeConfig()
