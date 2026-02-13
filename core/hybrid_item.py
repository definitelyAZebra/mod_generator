# -*- coding: utf-8 -*-
"""
HybridItem V2 - 使用 Tagged Union 重构的混合物品类

设计原则：
- 使用 specs 模块的 Tagged Union 类型替代平铺字段
- 模型层保证自身一致性，mutation 方法封装约束联动
- 消费者应 match equipment/trigger/charges 变体，不使用投影属性
- 计算属性仅限跨字段推导 (has_durability 等)

序列化由 serde 模块处理，本模块只定义数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.specs import (
    # Literal 类型
    Weight, Material,
    QualitySpec, ARTIFACT_CATEGORY,
    # Equipment
    EquipmentSpec, NotEquipable, WeaponEquip, ArmorEquip, CharmEquip,
    equipment_hands,
    needs_char_texture, needs_left_texture, needs_multi_pose,
    char_texture_for_equipment,
    # Trigger
    TriggerSpec, NoTrigger, EffectTrigger, SkillTrigger,
    ChargeSpec, NoCharges, LimitedCharges, UnlimitedCharges,
    ChargeRecoverySpec, NoRecovery, IntervalRecovery,
    HasDurability,
    SpawnSpec, SpawnRuleType, ExcludedFromRandom, RandomSpawn,
    spawn_effective_tags,
    # Textures (V2)
    ItemTexturesV2,
)
from core.localization import ItemLocalization


# ============================================================================
# HybridItemV2 - 使用 Tagged Union 的混合物品
# ============================================================================


@dataclass
class HybridItemV2:
    """混合物品 V2 - 使用 Tagged Union 重构

    核心设计：
    - quality: QualitySpec (替代 quality: int + rarity: str)
    - equipment: EquipmentSpec (替代 equipment_mode + weapon_type + armor_type + ...)
    - trigger: TriggerSpec (替代 trigger_mode + skill_object + consumable_attributes + ...)
    - charges: ChargeSpec (替代 charge_mode + charge + draw_charges)
    - charge_recovery: ChargeRecoverySpec (替代 has_charge_recovery + charge_recovery_interval)
    - durability: DurabilitySpec (嵌入 equipment，替代 has_durability + duration_max + ...)
    - spawn: SpawnSpec (替代 exclude_from_random + container_spawn + shop_spawn + tags)
    """

    # ====== 基础信息 ======
    id: str = ""

    # 本地化
    localization: ItemLocalization = field(default_factory=ItemLocalization)

    # 父对象
    parent_object: str = "o_inv_consum"

    # ====== Tagged Union 规格 ======
    quality: QualitySpec = QualitySpec.COMMON
    equipment: EquipmentSpec = field(default_factory=NotEquipable)
    trigger: TriggerSpec = field(default_factory=NoTrigger)
    charges: ChargeSpec = field(default_factory=NoCharges)
    charge_recovery: ChargeRecoverySpec = field(default_factory=NoRecovery)
    # 注: durability 已嵌入 WeaponEquip/ArmorEquip，非装备无需耐久
    spawn: SpawnSpec = field(default_factory=ExcludedFromRandom)

    # ====== 分类元数据 ======
    cat: str = ""
    subcats: list[str] = field(default_factory=list[str])

    # ====== 通用属性 ======
    attributes: dict[str, Any] = field(default_factory=dict[str, Any])

    # ====== 拆解碎片 ======
    fragments: dict[str, int] = field(default_factory=dict[str, int])

    # ====== 顶层字段：所有物品都需要 (InjectItemStats) ======
    weight: Weight = "Light"
    tier: int = 1                   # 等级 1-5
    material: Material = "organic"  # 材质，默认 organic (非装备)

    # ====== 价格与音效 ======
    base_price: int = 100
    drop_sound: int = 911
    pickup_sound: int = 907

    # ====== 贴图 (V2 Tagged Union) ======
    textures: ItemTexturesV2 = field(default_factory=ItemTexturesV2)

    # ====== Mutation 方法：约束联动集中在模型层 ======

    def set_quality(self, quality: QualitySpec) -> None:
        """设置品质，自动处理约束联动

        联动规则:
        - 文物 → tier=0, cat="treasure"
        - 文物 + 有限次数 → 强制自动恢复
        - 从文物切走 → 清除 treasure 分类约束
        - 独特 → quality_tag="unique"
        - 普通 → quality_tag=""
        """
        old = self.quality
        self.quality = quality
        if quality == QualitySpec.ARTIFACT:
            self.tier = 0
            self.cat = ARTIFACT_CATEGORY
            if isinstance(self.charges, LimitedCharges) and not isinstance(self.charge_recovery, IntervalRecovery):
                self.charge_recovery = IntervalRecovery()
        elif old == QualitySpec.ARTIFACT:
            # 从文物切走: 清理 treasure 约束
            if self.cat == ARTIFACT_CATEGORY:
                self.cat = ""
            if ARTIFACT_CATEGORY in self.subcats:
                self.subcats.remove(ARTIFACT_CATEGORY)
        if isinstance(self.spawn, RandomSpawn):
            self.spawn.quality_tag = "unique" if quality == QualitySpec.UNIQUE else ""

    def set_equipment(self, equipment: EquipmentSpec) -> None:
        """设置装备形态，自动同步贴图类型

        联动规则:
        - textures.char 类型与 equipment 匹配
        """
        self.equipment = equipment
        expected = char_texture_for_equipment(equipment)
        if type(self.textures.char) is not type(expected):
            self.textures.char = expected

    def set_trigger(self, trigger: TriggerSpec) -> None:
        """设置触发模式，自动处理充能联动

        联动规则:
        - 效果/技能触发 + 无充能 → 自动设 LimitedCharges
        - 无触发 → 清除充能和恢复
        """
        self.trigger = trigger
        if isinstance(trigger, (EffectTrigger, SkillTrigger)):
            if isinstance(self.charges, NoCharges):
                self.charges = LimitedCharges()
        elif isinstance(trigger, NoTrigger):
            self.charges = NoCharges()
            self.charge_recovery = NoRecovery()

    def set_charges(self, charges: ChargeSpec) -> None:
        """设置充能模式，自动处理触发和恢复联动

        联动规则:
        - 无充能 → 清除触发和恢复
        - 无限充能 → 清除恢复
        - 文物 + 有限次数 → 强制自动恢复
        """
        self.charges = charges
        if isinstance(charges, NoCharges):
            self.trigger = NoTrigger()
            self.charge_recovery = NoRecovery()
        elif isinstance(charges, UnlimitedCharges):
            self.charge_recovery = NoRecovery()
        elif isinstance(charges, LimitedCharges) and self.quality == QualitySpec.ARTIFACT:
            if not isinstance(self.charge_recovery, IntervalRecovery):
                self.charge_recovery = IntervalRecovery()

    # ====== 校验：跨字段约束的显式文档 ======

    def validate(self) -> list[str]:
        """校验跨字段不变式，返回违规描述列表

        用于保存时检查数据一致性。mutation 方法在交互时维护不变式，
        validate 在持久化边界提供最终保障。
        """
        errors: list[str] = []
        if self.quality == QualitySpec.ARTIFACT and self.has_durability:
            errors.append("文物品质不应有耐久系统")
        if (self.quality == QualitySpec.ARTIFACT
                and isinstance(self.charges, LimitedCharges)
                and not isinstance(self.charge_recovery, IntervalRecovery)):
            errors.append("文物有限次数必须有自动恢复")
        if isinstance(self.trigger, SkillTrigger) and not self.trigger.skill_object:
            errors.append("启用了技能触发但未设置技能对象")
        if isinstance(self.trigger, (EffectTrigger, SkillTrigger)) and isinstance(self.charges, NoCharges):
            errors.append("有触发效果但无使用次数")
        return errors

    # ====== 计算属性：跨字段推导 ======

    @property
    def slot(self) -> str:
        """装备槽位

        .. deprecated:: 消费者应直接 match equipment 变体获取 slot
        """
        return self.equipment.slot

    @property
    def equipable(self) -> bool:
        """是否可装备到身体槽位 (武器/护甲，不含护符)"""
        return isinstance(self.equipment, (WeaponEquip, ArmorEquip))

    # ====== 兼容性别名 ======

    @property
    def name(self) -> str:
        """别名：返回 id

        .. deprecated:: 消费者应直接使用 .id
        """
        return self.id

    @name.setter
    def name(self, value: str):
        self.id = value

    # ====== 跨字段计算属性 ======

    @property
    def armor_class(self) -> str:
        """护甲类别 - 仅护甲模式有意义

        映射规则 (weight → armor_class):
        - Very Light / Light → "Light"
        - Medium → "Medium"
        - Heavy → "Heavy"

        游戏来源: scr_atr_calc.gml 中 armor_class 用于抗性计算
        """
        return {"Very Light": "Light", "Light": "Light",
                "Medium": "Medium", "Heavy": "Heavy"}.get(self.weight, "Light")

    @property
    def durability(self) -> HasDurability | None:
        """提取耐久规格 (需品质允许 + 装备有 HasDurability)

        返回 HasDurability 实例或 None (品质不允许/非装备/无耐久)。
        消费者应 match 返回值而非假设存在。
        """
        if not self.quality.has_durability:
            return None
        match self.equipment:
            case WeaponEquip(durability=HasDurability() as d):
                return d
            case ArmorEquip(durability=HasDurability() as d):
                return d
            case _:
                return None

    @property
    def has_durability(self) -> bool:
        """是否有耐久系统 (跨 quality × equipment × durability)"""
        return self.durability is not None

    @property
    def wear_applies(self) -> bool:
        """磨损率是否生效 (有耐久 + 有充能)"""
        return self.has_durability and not isinstance(self.charges, NoCharges)

    @property
    def has_fragmentable_armor(self) -> bool:
        """是否可拆解碎片的护甲 (排除盾牌和饰品)"""
        return (isinstance(self.equipment, ArmorEquip)
                and self.equipment.armor_type not in ("shield", "Ring", "Amulet"))

    # ====== Spawn 属性 ======

    @property
    def effective_tags(self) -> str:
        """有效 tags 字符串

        TODO: 评估是否可删除，让消费者直接调用 spawn_effective_tags(item.spawn)
        """
        return spawn_effective_tags(self.spawn)

    # ====== 约束查询 ======

    @property
    def recovery_locked(self) -> bool:
        """恢复是否被锁定为开启 (文物品质 + 有限次数 → 强制自动恢复)"""
        return (self.quality == QualitySpec.ARTIFACT
                and isinstance(self.charges, LimitedCharges))

    @property
    def can_delete_on_zero(self) -> bool:
        """耗尽销毁选项是否可用。

        False when:
        - 充能非有限 (无限/无充能不存在耗尽)
        - 有耐久系统 (耐久控制物品生命周期)
        - 恢复被锁定开启 (文物自动恢复, 不会耗尽)
        """
        return (
            isinstance(self.charges, LimitedCharges)
            and not self.has_durability
            and not self.recovery_locked
        )

    # ====== 值域查询 ======

    @property
    def available_spawn_rules(self) -> list[SpawnRuleType]:
        """当前装备形态下可选的生成规则类型"""
        if isinstance(self.equipment, NotEquipable):
            return [SpawnRuleType.ITEM, SpawnRuleType.NONE]
        return [SpawnRuleType.EQUIPMENT, SpawnRuleType.ITEM, SpawnRuleType.NONE]

    # ====== 贴图需求方法 ======

    def needs_char_texture(self) -> bool:
        """是否需要角色贴图"""
        return needs_char_texture(self.equipment)

    def needs_left_texture(self) -> bool:
        """是否需要左手贴图"""
        return needs_left_texture(self.equipment)

    def needs_multi_pose_textures(self) -> bool:
        """是否需要多姿势贴图"""
        return needs_multi_pose(self.equipment)

    # ====== 注册判断 ======

    @property
    def needs_registration(self) -> bool:
        """是否需要注册到混合物品系统"""
        match self.spawn:
            case ExcludedFromRandom():
                return False
            case RandomSpawn(container_spawn=c, shop_spawn=s):
                if SpawnRuleType.EQUIPMENT in (c, s):
                    return True
                return s != SpawnRuleType.ITEM or c != SpawnRuleType.ITEM
