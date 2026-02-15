# -*- coding: utf-8 -*-
"""
从 GML 源码中提取属性来源元数据 (三层 flag + 二次 resolve 架构)。

=== 背景 ===

Stoneshard 的属性计算分散在多个 GML 函数中，各函数有嵌套调用关系。
本脚本从 GML 源码中 **机械提取** 每个属性的读取方式，然后通过
**两级 resolve** 将底层调用模式展开为"该属性对哪些装备栏位有效"。

=== 三层 flag 架构 ===

Layer 1 — SurfaceCall (表层调用模式):
    直接通过 regex 从 GML 中检测到的函数调用。
    纯粹描述 "GML 代码里写了什么"，不含推理。
    主要作用是 **文档** — 让人一眼看出属性走的是哪条 GML 路径。

Layer 2 — SlotGroup (GML 函数语义):
    通过 CALL_RESOLVE_MAP 从 SurfaceCall 展开得到。
    描述 "GML 函数内部做了什么" — 按内部调用模式分组。
    是中间层，用于 debug 和理解 GML 函数结构。

Layer 3 — EquipSlot (实际装备栏位):
    通过 EQUIP_RESOLVE_MAP 从 SlotGroup 展开得到。
    描述 "这个属性对哪些玩家装备栏位有效"。
    这是 get_equip_attrs_for_slot() 等消费者直接使用的终端 flag。

    SurfaceCall ──CALL_RESOLVE_MAP──▶ SlotGroup ──EQUIP_RESOLVE_MAP──▶ EquipSlot
      (GML 写了什么)        (函数做了什么)            (哪些栏位生效)

为什么需要三层而不是两层?
    SlotGroup 仍然是 GML 函数行为的抽象 — 比如 ACC_SLOT 实际读了
    "饰品4槽 + 武器手2槽" (scr_inv_buff_param_ext 内部)，这个 "武器也贡献"
    的事实在 SlotGroup 中是隐式的。EquipSlot 把它显式化：
        ACC_SLOT → HAND | ACCESSORY。
    这样消费者只需查 EquipSlot.HAND，不需要知道 ACC_SLOT 内部有手持槽。

=== GML 函数嵌套关系 (核心领域知识) ===

以下是 scr_atr_calc 体系中属性读取函数的调用链:

    scr_inv_buff_atr(attr)
        ├── scr_inv_param(attr)        所有已装备+被动物品 (遍历 o_inv_slot 子类)
        └── scr_buff_param(attr)       buff 数据

    scr_FullAtr(attr)
        ├── scr_atr(attr)              角色基础属性 (我们不需要追踪这个)
        ├── scr_inv_param(attr)
        └── scr_buff_param(attr)

    scr_inv_param(attr, _mainHandItem) × efficiency
        → 仅读取指定武器手物品，结果乘以 Mainhand/Offhand_Efficiency

    scr_inv_param(attr, 4479, true)
        → 跳过右手+左手，读取其余所有装备+被动物品

    scr_inv_buff_param_ext(attr)
        ├── scr_buff_param(attr)
        ├── scr_inv_param_slot(attr, 戒指1)     ← 4493
        ├── scr_inv_param_slot(attr, 戒指2)     ← 5219
        ├── scr_inv_param_slot(attr, 背部)       ← 4492
        ├── scr_inv_param_slot(attr, 腰带)       ← 4499
        ├── scr_inv_param_slot(attr, 项链)       ← 4495
        ├── scr_inv_param_slot(attr, 右手)       ← 4488
        ├── scr_inv_param_slot(attr, 左手)       ← 4490
        └── scr_inv_param_consum(attr)           被动消耗品

    scr_resistance_calc(attr, parent_attr)
        ├── scr_inv_buff_param_ext(attr)         上面整套 → 通用抗性值
        └── scr_inv_param_slot(attr, 头/胸/手/腿) ← 4500/4494/4497/4496
            → 通用值 + 部位单独值 = 该部位最终抗性

    scr_def_calc(isPlayer)
        ├── scr_buff_param("DEF")                基础 DEF (仅 buff)
        ├── scr_inv_param_slot("DEF", 头/胸/手/腿)  各部位护甲的 DEF
        └── scr_buff_param("Head_DEF" / ...)     部位 DEF buff 加成

=== 数据源 ===

仅需 5 个 GML 文件:
  - scr_atr_calc.gml              玩家属性计算主入口 (含 scr_def_calc, scr_resistance_calc)
  - scr_atr_calc_combat.gml       战斗属性 (主副手分离计算)
  - scr_inv_param.gml             辅助函数 (含 scr_inv_buff_param_ext)
  - scr_Health_Threshold_calc.gml Health_Threshold 的部位计算
  - scr_consum_use.gml            消耗品即时效果 case 列表

输出:
  datamine/output/attribute_sources.json
"""

from __future__ import annotations

import enum
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Ensure stdout handles Unicode (Windows GBK terminals choke on emoji)
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── paths ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
GML_DIR = ROOT / "datamine" / "output" / "CodeEntries"
# 部分文件在 CodeEntries 中反编译失败，备用位置在 references/gml
# GML_FALLBACK_DIR = ROOT / "references" / "gml"  # 暂时注释以测试
OUTPUT_DIR = ROOT / "datamine" / "output"
OUTPUT_JSON = OUTPUT_DIR / "attribute_sources.json"

# GML files needed (basename → will search CodeEntries first, then references/gml)
_GML_FILES = {
    "atr_calc": "gml_GlobalScript_scr_atr_calc.gml",
    "combat": "gml_GlobalScript_scr_atr_calc_combat.gml",
    "inv_param": "gml_GlobalScript_scr_inv_param.gml",
    "ht_calc": "gml_GlobalScript_scr_Health_Threshold_calc.gml",
    "consum_use": "gml_GlobalScript_scr_consum_use.gml",
}


def _read_gml(key: str) -> str:
    """Read a GML file, trying CodeEntries first then references/gml as fallback.

    Some files fail to decompile in newer UTMT versions but exist in references/gml
    from earlier extractions.
    """
    name = _GML_FILES[key]
    primary = GML_DIR / name
    if primary.exists():
        text = primary.read_text(encoding="utf-8")
        # Check for decompile errors
        if "DECOMPILE ERROR" not in text[:200]:
            return text
    # fallback = GML_FALLBACK_DIR / name  # 暂时注释以测试
    # if fallback.exists():
    #     return fallback.read_text(encoding="utf-8")
    raise FileNotFoundError(
        f"Cannot find {name} in {GML_DIR}"
    )


# ═══════════════════════════════════════════════════════════════════
# Layer 1: SurfaceCall — GML 中直接检测到的调用模式
# ═══════════════════════════════════════════════════════════════════

class SurfaceCall(str, enum.Enum):
    """GML 属性计算中检测到的表层函数调用模式。

    每个值对应一种 regex 可以在 GML 源码中匹配到的模式。
    一个属性可以有多个 SurfaceCall（例如 Hit_Chance 同时出现在
    scr_inv_param(..., hand)、scr_inv_param(..., 4479, true) 和 scr_buff_param 中）。

    命名约定: 与 GML 函数名对应，但加了后缀来区分同一函数的不同调用形式。
    """

    # ── scr_inv_buff_atr("X") ──────────────────────────────────
    # = scr_inv_param(attr) + scr_buff_param(attr)
    # 所有装备（含武器）+ 被动物品 + buff
    INV_BUFF_ATR = "inv_buff_atr"

    # ── scr_FullAtr("X") ──────────────────────────────────────
    # = scr_atr(attr) + scr_inv_param(attr) + scr_buff_param(attr)
    # 同上，但还加了角色基础属性
    FULL_ATR = "full_atr"

    # ── scr_inv_param("X") (standalone, no 2nd arg) ──────────
    # 单独的 scr_inv_param，不带手物品参数
    # 读取所有已装备+被动物品
    INV_PARAM = "inv_param"

    # ── scr_inv_param("X", _mainHandItem/_offHandItem) ──────
    # 仅读取指定武器手物品
    # 结果通常乘以 Mainhand/Offhand_Efficiency
    INV_PARAM_HAND = "inv_param_hand"

    # ── scr_inv_param("X", 4479, true) ──────────────────────
    # 跳过右手+左手，读取其余所有装备+被动物品
    # (4479 = o_inv_slot, 所有槽位的父类)
    INV_PARAM_NOHAND = "inv_param_nohand"

    # ── scr_inv_buff_param_ext("X") ──────────────────────────
    # 逐槽位累加: buff + 饰品7槽 + 被动消耗品
    # 用于: Physical/Nature/Magic_Resistance, Bleeding_Resistance, Health_Threshold
    INV_BUFF_PARAM_EXT = "inv_buff_param_ext"

    # ── scr_resistance_calc("X", parent) ─────────────────────
    # = scr_inv_buff_param_ext(X) + scr_inv_param_slot(X, 头/胸/手/腿)
    # 用于: 所有子类抗性 (Fire/Frost/... Resistance)
    RESISTANCE_CALC = "resistance_calc"

    # ── scr_def_calc 中的 DEF 读取 ───────────────────────────
    # DEF: scr_buff_param("DEF") + scr_inv_param_slot("DEF", 头/胸/手/腿)
    # 部位 DEF: scr_inv_param_slot + buff_DEF + scr_buff_param(部位DEF)
    DEF_CALC = "def_calc"

    # ── scr_buff_param("X") (standalone) ─────────────────────
    # 仅从 buff 数据读取，装备不贡献
    BUFF_PARAM = "buff_param"


# ═══════════════════════════════════════════════════════════════════
# Layer 2: SlotGroup — 属性对哪些装备槽位类别有效
# ═══════════════════════════════════════════════════════════════════

class SlotGroup(enum.Flag):
    """Layer 2 — GML 函数的内部行为模式。

    由 CALL_RESOLVE_MAP 从 SurfaceCall 自动展开得到。
    描述的是 "函数内部做了什么"，不直接回答 "哪些装备栏位有效"。

    ⚠️ 注意: 这些 flag 的命名以 GML 函数行为命名，不等于装备栏位。
    例如 ACC_SLOT 名义上是 "饰品槽"，但 scr_inv_buff_param_ext 内部
    实际读了 7 个槽位包括 rhand(4488) 和 lhand(4490)。
    要知道实际涉及哪些装备栏位，请看 Layer 3 (EquipSlot)。
    """
    INV_ALL        = enum.auto()  # scr_inv_param() 遍历所有 o_inv_slot 子类
    HAND_EFF       = enum.auto()  # 武器手 via scr_inv_param(attr, handItem)，有效率加成
    NOHAND_INV     = enum.auto()  # 非手装备 via scr_inv_param(attr, 4479, true)
    ARMOR_SLOT     = enum.auto()  # 护甲4部位 via scr_inv_param_slot(attr, 头/胸/手/腿)
    ACC_SLOT       = enum.auto()  # scr_inv_buff_param_ext 逐槽位: 饰品4 + 手持2 + 被动消耗品
    PASSIVE_CONSUM = enum.auto()  # 被动消耗品 via scr_inv_param_consum
    BUFF           = enum.auto()  # buff 数据 via scr_buff_param


# ═══════════════════════════════════════════════════════════════════
# Resolve 1: SurfaceCall → SlotGroup (表层调用 → 函数语义)
# ═══════════════════════════════════════════════════════════════════
#
# 编码 "每个 GML 表层调用，其内部做了哪些事"。
# 如果游戏更新修改了某个函数的内部实现（例如 scr_inv_buff_param_ext
# 新增了一个槽位），只需要改这里的一行。

S = SlotGroup

CALL_RESOLVE_MAP: dict[SurfaceCall, SlotGroup] = {
    # scr_inv_buff_atr = scr_inv_param + scr_buff_param
    # scr_inv_param 遍历所有 o_inv_slot 子类 (含武器、护甲、饰品、被动物品)
    SurfaceCall.INV_BUFF_ATR: S.INV_ALL | S.BUFF,

    # scr_FullAtr = scr_atr + scr_inv_param + scr_buff_param
    # 与 INV_BUFF_ATR 相同的装备覆盖范围，额外加了基础属性(我们不追踪)
    SurfaceCall.FULL_ATR: S.INV_ALL | S.BUFF,

    # 独立的 scr_inv_param("X") — 不带手物品参数
    # 遍历所有 o_inv_slot 子类
    SurfaceCall.INV_PARAM: S.INV_ALL,

    # scr_inv_param("X", _mainHandItem) — 仅武器手
    SurfaceCall.INV_PARAM_HAND: S.HAND_EFF,

    # scr_inv_param("X", 4479, true) — 排除武器手
    SurfaceCall.INV_PARAM_NOHAND: S.NOHAND_INV,

    # scr_inv_buff_param_ext 内部调用链:
    #   scr_buff_param(attr)                → BUFF
    #   scr_inv_param_slot(attr, 戒指1)     → ACC_SLOT
    #   scr_inv_param_slot(attr, 戒指2)     → ACC_SLOT
    #   scr_inv_param_slot(attr, 背部)      → ACC_SLOT
    #   scr_inv_param_slot(attr, 腰带)      → ACC_SLOT
    #   scr_inv_param_slot(attr, 项链)      → ACC_SLOT
    #   scr_inv_param_slot(attr, 右手)      → ACC_SLOT (注意：手持也在这里！)
    #   scr_inv_param_slot(attr, 左手)      → ACC_SLOT
    #   scr_inv_param_consum(attr)          → PASSIVE_CONSUM
    SurfaceCall.INV_BUFF_PARAM_EXT: S.BUFF | S.ACC_SLOT | S.PASSIVE_CONSUM,

    # scr_resistance_calc(attr, parent) 内部:
    #   scr_inv_buff_param_ext(attr)                → 上面整套
    #   scr_inv_param_slot(attr, 头/胸/手/腿)       → ARMOR_SLOT
    # 即: 所有装备槽位都能贡献抗性，只是方式不同:
    #   饰品+手持 → 进入 scr_inv_buff_param_ext 的通用值
    #   护甲      → 通过 scr_inv_param_slot 直接加到对应部位
    SurfaceCall.RESISTANCE_CALC: S.BUFF | S.ACC_SLOT | S.PASSIVE_CONSUM | S.ARMOR_SLOT,

    # scr_def_calc 中 DEF 的读取:
    #   scr_buff_param("DEF")                   → BUFF
    #   scr_inv_param_slot("DEF", 头/胸/手/腿)  → ARMOR_SLOT
    SurfaceCall.DEF_CALC: S.ARMOR_SLOT | S.BUFF,

    # 独立的 scr_buff_param — 只从 buff 读取
    SurfaceCall.BUFF_PARAM: S.BUFF,
}


def resolve_slot_groups(calls: set[SurfaceCall]) -> SlotGroup:
    """Resolve 1: 将一组 SurfaceCall 展开为 SlotGroup flags。"""
    result = SlotGroup(0)
    for call in calls:
        result |= CALL_RESOLVE_MAP[call]
    return result


# ═══════════════════════════════════════════════════════════════════
# Layer 3: EquipSlot — 玩家装备栏位 (编辑器/消费者视角)
# ═══════════════════════════════════════════════════════════════════

class EquipSlot(enum.Flag):
    """Layer 3 — 该属性对哪些玩家装备栏位实际有效。

    这是整个 flag 系统的终端输出，直接对应玩家背包中的装备栏位。
    由 EQUIP_RESOLVE_MAP 从 SlotGroup 自动展开得到。

    get_equip_attrs_for_slot("Ring") 等消费者只需查这一层：
        if meta.equip_slots & EquipSlot.ACCESSORY:  # Ring 属于 ACCESSORY
            include_attr()

    ┌─────────────────────────────────────────────────────────────┐
    │ 游戏装备栏位分组                                            │
    │                                                             │
    │ HAND       = 右手 + 左手 (武器/盾牌/工具)                   │
    │ ARMOR      = 头部 + 胸部 + 手套 + 腿部                      │
    │ ACCESSORY  = 戒指×2 + 项链 + 腰带 + 背部                    │
    │ PASSIVE_CONSUM = 被动消耗品 (check_inventory_data=true)      │
    │ BUFF       = buff 数据层 (消耗品持续效果/技能 buff)           │
    │                                                             │
    │ ALL_EQUIP  = HAND | ARMOR | ACCESSORY | PASSIVE_CONSUM      │
    └─────────────────────────────────────────────────────────────┘
    """
    HAND           = enum.auto()  # 右手/左手 (武器/盾牌/工具，与 slot="hand" 对应)
    ARMOR          = enum.auto()  # 头/胸/手/腿 (4 armor slots)
    ACCESSORY      = enum.auto()  # 戒指/项链/腰带/背部 (4 accessory slots)
    PASSIVE_CONSUM = enum.auto()  # 被动消耗品
    BUFF           = enum.auto()  # buff 数据


E = EquipSlot


# ═══════════════════════════════════════════════════════════════════
# Resolve 2: SlotGroup → EquipSlot (函数语义 → 实际栏位)
# ═══════════════════════════════════════════════════════════════════
#
# 编码 "每种函数行为模式，最终触及了哪些装备栏位"。
#
# ⚠️ 关键非直觉映射:
#   ACC_SLOT → ACCESSORY | HAND
#   因为 scr_inv_buff_param_ext 内部逐槽位读取时，除了 4 个饰品槽，
#   还读了 rhand(4488) 和 lhand(4490)。所以抗性类属性中，
#   手持物品也贡献数值 — 只是不经过效率 (Efficiency) 加成。

EQUIP_RESOLVE_MAP: dict[SlotGroup, EquipSlot] = {
    # scr_inv_param() 遍历 o_inv_slot 所有子类
    # → 手持、护甲、饰品、被动消耗品全部命中
    SlotGroup.INV_ALL:        E.HAND | E.ARMOR | E.ACCESSORY | E.PASSIVE_CONSUM,

    # scr_inv_param(attr, _mainHandItem) — 仅读手持物品
    SlotGroup.HAND_EFF:       E.HAND,

    # scr_inv_param(attr, 4479, true) — 跳过 rhand+lhand
    # → 护甲 + 饰品 + 被动消耗品
    SlotGroup.NOHAND_INV:     E.ARMOR | E.ACCESSORY | E.PASSIVE_CONSUM,

    # scr_inv_param_slot(attr, 头/胸/手/腿) — 4 个护甲部位
    SlotGroup.ARMOR_SLOT:     E.ARMOR,

    # scr_inv_buff_param_ext 的逐槽位读取:
    #   戒指1(4493), 戒指2(5219), 背部(4492), 腰带(4499), 项链(4495)
    #   + 右手(4488), 左手(4490)  ← 手持物品也在这里！
    # → ACCESSORY + HAND (不含护甲，不含被动消耗品 — 那个是单独的)
    SlotGroup.ACC_SLOT:       E.ACCESSORY | E.HAND,

    # scr_inv_param_consum — 被动消耗品
    SlotGroup.PASSIVE_CONSUM: E.PASSIVE_CONSUM,

    # scr_buff_param — 仅 buff 数据
    SlotGroup.BUFF:           E.BUFF,
}


def resolve_equip_slots(sg: SlotGroup) -> EquipSlot:
    """Resolve 2: 将 SlotGroup 展开为 EquipSlot flags。"""
    result = EquipSlot(0)
    for flag, equip in EQUIP_RESOLVE_MAP.items():
        if sg & flag:
            result |= equip
    return result


# ═══════════════════════════════════════════════════════════════════
# AttrMeta — 单个属性的完整元数据
# ═══════════════════════════════════════════════════════════════════

@dataclass
class AttrMeta:
    """单个属性的 GML 元数据。

    surface_calls: 表层调用模式 (Layer 1, 自动提取)
    has_efficiency: 武器手读取时是否乘以 Mainhand/Offhand_Efficiency
    has_body_parts: 是否有 attr_Head/Tors/Hands/Legs 部位分离计算
    clamp:          从 clamp(expr, min, max) 调用中提取的范围
    """
    surface_calls: set[SurfaceCall] = field(default_factory=set)
    has_efficiency: bool = False   # 隐含 → 仅对 HAND slot 有意义 (HAND_EFF slot group)
    has_body_parts: bool = False   # 隐含 → 仅对 ARMOR slot 有意义 (ARMOR_SLOT slot group)
    # TODO: 如果需要显式化 efficiency/body_parts 对哪些 EquipSlot 起作用，
    #       可扩展为 efficiency_slots: set[EquipSlot] / body_part_slots: set[EquipSlot]。
    #       当前一对一映射 (efficiency→HAND, body_parts→ARMOR) 足够用。
    clamp: tuple[float, float] | None = None

    @property
    def slot_groups(self) -> SlotGroup:
        """Layer 2: 由 surface_calls 经 CALL_RESOLVE_MAP 展开得到。"""
        return resolve_slot_groups(self.surface_calls)

    @property
    def equip_slots(self) -> EquipSlot:
        """Layer 3: 由 slot_groups 经 EQUIP_RESOLVE_MAP 展开得到。

        这是消费者应该使用的终端 flag。
        例: HAND in meta.equip_slots → 手持物品可以提供该属性
        """
        return resolve_equip_slots(self.slot_groups)


# ═══════════════════════════════════════════════════════════════════
# Regex helpers
# ═══════════════════════════════════════════════════════════════════

def _find_all_string_args(pattern: str, text: str) -> list[str]:
    """从 GML 文本中提取所有匹配 pattern 的字符串参数。

    Returns: deduplicated list in order of first occurrence.
    """
    seen: set[str] = set()
    result: list[str] = []
    for m in re.findall(pattern, text):
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def _extract_player_block(atr_calc_text: str) -> str:
    """提取 scr_atr_calc.gml 中 `with (o_player) { ... }` 块。

    这是所有玩家属性计算的入口，我们从这里检测 surface calls。
    """
    marker = "with (o_player)"
    idx = atr_calc_text.find(marker)
    if idx == -1:
        raise ValueError("Cannot find 'with (o_player)' in scr_atr_calc.gml")
    return atr_calc_text[idx:]


def _extract_clamp(attr: str, text: str) -> tuple[float, float] | None:
    """从 `attr = clamp(..., min, max)` 中提取值域范围。"""
    pattern = re.escape(attr) + r'\s*=\s*clamp\([^,]+,\s*(-?[\d.]+),\s*(-?[\d.]+)\)'
    m = re.search(pattern, text)
    if m:
        return (float(m.group(1)), float(m.group(2)))
    return None


def _detect_efficiency_attrs(combat_text: str) -> dict[str, str]:
    """检测哪些属性在武器手读取时有效率加成。

    Returns: {attr_name: "multiply" | "divide"}

    大多数属性: value * _mainHandDebuff (正相关)
    FMB 特殊:   value / _mainHandDebuff (反相关 — 高效率降低 FMB)
    """
    result: dict[str, str] = {}

    # Normal: scr_inv_param("X", _mainHandItem) * _mainHandDebuff
    for m in re.finditer(
        r'scr_inv_param\("(\w+)",\s*_mainHandItem\)\s*\*\s*_mainHandDebuff',
        combat_text,
    ):
        result[m.group(1)] = "multiply"

    # Inverse: scr_inv_param("X", _mainHandItem) without * _mainHandDebuff
    # then separately divided. FMB is the known case.
    for m in re.finditer(
        r'scr_inv_param\("(\w+)",\s*_mainHandItem\)',
        combat_text,
    ):
        attr = m.group(1)
        if attr not in result:
            result[attr] = "divide"

    return result


def _detect_body_part_attrs(player_block: str) -> set[str]:
    """检测有 Head/Tors/Hands/Legs 部位分离计算的属性。

    检测方式: 扫描 `attr_Head = ...`, `attr_Tors = ...` 等变量赋值。
    """
    parts = set()
    for m in re.finditer(r'(\w+?)_(Head|Tors|Hands|Legs)\s*=', player_block):
        parts.add(m.group(1))
    return parts


# ═══════════════════════════════════════════════════════════════════
# 核心提取逻辑
# ═══════════════════════════════════════════════════════════════════

def extract_attr_registry() -> dict[str, AttrMeta]:
    """从 GML 源文件中提取完整的属性元数据。

    提取流程:
      1. 用 regex 逐一检测各 SurfaceCall 模式
      2. 检测 efficiency / body_parts / clamp 等辅助特征
      3. SlotGroup 由 AttrMeta.slot_groups 属性自动 resolve，不在此处计算

    Returns: {属性名: AttrMeta}
    """
    atr_calc_full = _read_gml("atr_calc")
    combat_text = _read_gml("combat")
    ht_text = _read_gml("ht_calc")

    player_block = _extract_player_block(atr_calc_full)
    clamp_text = player_block + "\n" + combat_text

    registry: dict[str, AttrMeta] = {}

    def _ensure(attr: str) -> AttrMeta:
        if attr not in registry:
            registry[attr] = AttrMeta()
        return registry[attr]

    # ── SurfaceCall 检测 ────────────────────────────────────────
    #
    # 以下每个段落对应一种 GML 调用模式。
    # 搜索范围: player_block (主计算) + combat_text (战斗属性)
    # 某些模式只出现在特定文件中。

    all_text = player_block + "\n" + combat_text

    # 1. scr_inv_buff_atr("X") — 通用装备+buff
    #    示例: STL = clamp(scr_inv_buff_atr("STL"), -100, 100)
    for attr in _find_all_string_args(r'scr_inv_buff_atr\("(\w+)"\)', all_text):
        _ensure(attr).surface_calls.add(SurfaceCall.INV_BUFF_ATR)

    # 2. scr_FullAtr("X") — 基础属性+装备+buff
    #    示例: STR = clamp(scr_FullAtr("STR"), 5, 30)
    for attr in _find_all_string_args(r'scr_FullAtr\("(\w+)"\)', player_block):
        _ensure(attr).surface_calls.add(SurfaceCall.FULL_ATR)

    # 3. scr_inv_param("X") — 独立的不带第二参数的调用
    #    示例: scr_inv_param("HP"), scr_inv_param("Range"), scr_inv_param("DMG")
    #    注意排除 scr_inv_param("X", ...) 的多参数形式
    for attr in _find_all_string_args(
        r'scr_inv_param\("(\w+)"\)(?!\s*[\*/])', player_block
    ):
        _ensure(attr).surface_calls.add(SurfaceCall.INV_PARAM)

    # 4. scr_inv_param("X", _mainHandItem/_offHandItem) — 武器手
    #    只出现在 scr_atr_calc_combat 中
    for attr in _find_all_string_args(
        r'scr_inv_param\("(\w+)",\s*_(?:main|off)HandItem\)', combat_text
    ):
        _ensure(attr).surface_calls.add(SurfaceCall.INV_PARAM_HAND)

    # 5. scr_inv_param("X", 4479, true) — 排除武器手
    #    只出现在 scr_atr_calc_combat 中
    for attr in _find_all_string_args(
        r'scr_inv_param\("(\w+)",\s*4479,\s*true\)', combat_text
    ):
        _ensure(attr).surface_calls.add(SurfaceCall.INV_PARAM_NOHAND)

    # 6. scr_inv_buff_param_ext("X") — 逐槽位累加
    #    出现在 player_block (Physical/Nature/Magic_Resistance, Bleeding_Resistance)
    #    和 ht_calc (Health_Threshold)
    #    注意: scr_resistance_calc 内部也调用此函数，但那些属性
    #    已经被下面的 RESISTANCE_CALC 检测覆盖
    ext_scan = player_block + "\n" + ht_text
    for attr in _find_all_string_args(
        r'scr_inv_buff_param_ext\("(\w+)"\)', ext_scan
    ):
        _ensure(attr).surface_calls.add(SurfaceCall.INV_BUFF_PARAM_EXT)

    # 7. scr_resistance_calc("X", parent) — 子类抗性的完整计算
    #    内部 = scr_inv_buff_param_ext + scr_inv_param_slot(头/胸/手/腿)
    for attr in _find_all_string_args(
        r'scr_resistance_calc\("(\w+)"', player_block
    ):
        _ensure(attr).surface_calls.add(SurfaceCall.RESISTANCE_CALC)

    # 8. scr_def_calc 中的 DEF 和部位 DEF — 特殊处理
    #    DEF: scr_buff_param("DEF") + scr_inv_param_slot("DEF", 头/胸/手/腿)
    #    由于 scr_def_calc 是一个独立函数，不是通过参数名调用的，
    #    我们直接硬编码检测 "DEF" 的存在
    if "scr_def_calc" in player_block:
        _ensure("DEF").surface_calls.add(SurfaceCall.DEF_CALC)

    # 9. scr_buff_param("X") — 所有独立的 buff 读取
    #    包括: 被其他 surface calls 包含的 (如 scr_inv_buff_atr 内部的 buff)
    #    和独立的 (如 MP_turn = scr_buff_param("MP_turn"))
    for attr in _find_all_string_args(r'scr_buff_param\("(\w+)"\)', all_text):
        _ensure(attr).surface_calls.add(SurfaceCall.BUFF_PARAM)

    # ── 辅助特征检测 ──────────────────────────────────────────

    # has_efficiency: 武器手读取是否有效率调制
    efficiency_map = _detect_efficiency_attrs(combat_text)
    for attr in efficiency_map:
        if attr in registry:
            registry[attr].has_efficiency = True

    # has_body_parts: 是否有头/胸/手/腿分离计算
    body_part_attrs = _detect_body_part_attrs(player_block)
    for attr in body_part_attrs:
        if attr in registry:
            registry[attr].has_body_parts = True

    # clamp 范围
    for attr in list(registry):
        c = _extract_clamp(attr, clamp_text)
        if c:
            registry[attr].clamp = c

    return registry


# ═══════════════════════════════════════════════════════════════════
# 消耗品即时效果
# ═══════════════════════════════════════════════════════════════════

def extract_consumable_instant_attrs() -> list[str]:
    """提取 scr_consum_use 中 switch case 的属性名列表。

    这些属性是消耗品的即时效果，不需要 Effects_Duration。
    例如: Hunger, Thirsty, Intoxication, Pain, Fatigue 等。
    """
    text = _read_gml("consum_use")
    return _find_all_string_args(r'case\s+"(\w+)"', text)


# ═══════════════════════════════════════════════════════════════════
# Legacy 兼容: 从 registry 派生旧的 HYBRID_*_ATTRS 分组
# ═══════════════════════════════════════════════════════════════════

def derive_legacy_groups(registry: dict[str, AttrMeta]) -> dict[str, list[str]]:
    """从 registry 派生旧的 6 组 HYBRID_*_ATTRS 列表。

    这些分组是 constants/attributes.py 中硬编码列表的等价物。
    用于验证提取结果与现有常量的一致性。

    映射规则 (基于 SlotGroup flags):
      COMMON     = 有 INV_ALL (所有装备+被动都贡献)
      COMBAT     = 有 HAND_EFF + NOHAND_INV, 无 INV_ALL (武器+非手装备都有)
      DAMAGE     = 有 HAND_EFF, 无 NOHAND_INV, 无 INV_ALL (仅武器手)
      RESISTANCE = 有 ARMOR_SLOT 或 ACC_SLOT, 无 INV_ALL (走 scr_inv_buff_param_ext 路径)
      DEF        = 有 ARMOR_SLOT, 无 ACC_SLOT, 无 INV_ALL (仅护甲部位)
      BUFF_ONLY  = 仅有 BUFF, 无任何装备 flag
    """
    common, combat, damage, resistance, def_attrs, buff_only = [], [], [], [], [], []

    for attr, meta in registry.items():
        sg = meta.slot_groups
        has_inv_all = bool(sg & S.INV_ALL)
        has_hand = bool(sg & S.HAND_EFF)
        has_nohand = bool(sg & S.NOHAND_INV)
        has_armor = bool(sg & S.ARMOR_SLOT)
        has_acc = bool(sg & S.ACC_SLOT)
        has_buff = bool(sg & S.BUFF)
        has_any_equip = bool(sg & (S.INV_ALL | S.HAND_EFF | S.NOHAND_INV | S.ARMOR_SLOT | S.ACC_SLOT | S.PASSIVE_CONSUM))

        if has_inv_all:
            common.append(attr)
        elif has_hand and has_nohand:
            combat.append(attr)
        elif has_hand and not has_nohand:
            damage.append(attr)
        elif has_armor and not has_acc:
            # DEF: scr_def_calc 路径 (仅护甲+buff，无饰品)
            def_attrs.append(attr)
        elif has_acc or has_armor:
            # INV_BUFF_PARAM_EXT 或 RESISTANCE_CALC 路径 (饰品+可能护甲)
            resistance.append(attr)
        elif has_buff and not has_any_equip:
            buff_only.append(attr)

    return {
        "HYBRID_COMMON_ATTRS": common,
        "HYBRID_COMBAT_ATTRS": combat,
        "HYBRID_DAMAGE_ATTRS": damage,
        "HYBRID_RESISTANCE_ATTRS": resistance,
        "HYBRID_DEF_ATTRS": def_attrs,
        "HYBRID_BUFF_ONLY_ATTRS": buff_only,
    }


# ═══════════════════════════════════════════════════════════════════
# 验证
# ═══════════════════════════════════════════════════════════════════

def validate_against_existing(registry: dict[str, AttrMeta]) -> bool:
    """将提取结果的 equip_slots 与 constants/attributes.py 的查询函数对比。

    对每个槽位调用 get_equip_attrs_for_slot, 验证结果与本次提取
    的 equip_slots 集合一致。
    """
    sys.path.insert(0, str(ROOT))
    from constants.attributes import (
        get_equip_attrs_for_slot,
        get_consumable_buff_attrs,
        _SOURCES_BLACKLIST,
    )

    # 从本次提取的 registry 构建 equip_slots 查询: slot_key → set[attr]
    extracted: dict[str, set[str]] = {
        "hand": set(), "armor": set(), "accessory": set(),
        "passive_consum": set(), "buff": set(),
    }
    for attr, meta in registry.items():
        if attr in _SOURCES_BLACKLIST:
            continue
        for flag, name in _EQUIP_SLOT_SHORT.items():
            if meta.equip_slots & flag:
                extracted[name].add(attr)

    # 槽位 → get_equip_attrs_for_slot 参数
    slot_checks = [
        ("hand",           "hand",  False),
        ("armor",          "Head",  False),
        ("accessory",      "Ring",  False),
        ("passive_consum", "heal",  True),
    ]

    print("\n" + "=" * 70)
    print("VALIDATION: Extracted equip_slots vs get_equip_attrs_for_slot()")
    print("=" * 70)

    all_ok = True
    for slot_key, slot_arg, has_passive in slot_checks:
        ext_set = extracted[slot_key]
        cur_set = set(get_equip_attrs_for_slot(slot_arg, has_passive))
        added = sorted(ext_set - cur_set)
        removed = sorted(cur_set - ext_set)

        if not added and not removed:
            print(f"\n  ✅ {slot_key}: MATCH ({len(cur_set)} attrs)")
        else:
            all_ok = False
            print(f"\n  ⚠️  {slot_key}:")
            print(f"     Existing: {len(cur_set)} | Extracted: {len(ext_set)}")
            if added:
                print(f"     ➕ New:     {added}")
            if removed:
                print(f"     ➖ Missing: {removed}")

    # buff 验证
    ext_buff = extracted["buff"]
    cur_buff = set(get_consumable_buff_attrs())
    added = sorted(ext_buff - cur_buff)
    removed = sorted(cur_buff - ext_buff)
    if not added and not removed:
        print(f"\n  ✅ buff: MATCH ({len(cur_buff)} attrs)")
    else:
        all_ok = False
        print(f"\n  ⚠️  buff:")
        print(f"     Existing: {len(cur_buff)} | Extracted: {len(ext_buff)}")
        if added:
            print(f"     ➕ New:     {added}")
        if removed:
            print(f"     ➖ Missing: {removed}")

    if all_ok:
        print("\n  🎉 All slot queries match perfectly!")
    return all_ok


# ═══════════════════════════════════════════════════════════════════
# 输出
# ═══════════════════════════════════════════════════════════════════

_SLOT_GROUP_SHORT: dict[SlotGroup, str] = {
    SlotGroup.INV_ALL:        "inv_all",
    SlotGroup.HAND_EFF:       "hand_eff",
    SlotGroup.NOHAND_INV:     "nohand_inv",
    SlotGroup.ARMOR_SLOT:     "armor_slot",
    SlotGroup.ACC_SLOT:       "acc_slot",
    SlotGroup.PASSIVE_CONSUM: "passive_consum",
    SlotGroup.BUFF:           "buff",
}

_EQUIP_SLOT_SHORT: dict[EquipSlot, str] = {
    EquipSlot.HAND:           "hand",
    EquipSlot.ARMOR:          "armor",
    EquipSlot.ACCESSORY:      "accessory",
    EquipSlot.PASSIVE_CONSUM: "passive_consum",
    EquipSlot.BUFF:           "buff",
}


def _slot_group_names(sg: SlotGroup) -> list[str]:
    return [name for flag, name in _SLOT_GROUP_SHORT.items() if sg & flag]


def _equip_slot_names(es: EquipSlot) -> list[str]:
    return [name for flag, name in _EQUIP_SLOT_SHORT.items() if es & flag]


def serialize_registry(registry: dict[str, AttrMeta]) -> dict[str, object]:
    """将 registry 序列化为 JSON 格式。

    输出结构:
    {
      "attr_name": {
        "surface_calls": ["inv_buff_atr", ...],      ← Layer 1 (GML 写了什么)
        "slot_groups":   ["inv_all", "buff", ...],    ← Layer 2 (函数做了什么)
        "equip_slots":   ["hand", "armor", ...],    ← Layer 3 (哪些栏位生效)
        "has_efficiency": false,
        "has_body_parts": false,
        "clamp": [min, max] | null
      }
    }
    """
    result: dict[str, object] = {}
    for attr, meta in registry.items():
        result[attr] = {
            "surface_calls": sorted(c.value for c in meta.surface_calls),
            "slot_groups": _slot_group_names(meta.slot_groups),
            "equip_slots": _equip_slot_names(meta.equip_slots),
            "has_efficiency": meta.has_efficiency,
            "has_body_parts": meta.has_body_parts,
            "clamp": list(meta.clamp) if meta.clamp else None,
        }
    return result


def print_registry(registry: dict[str, AttrMeta]) -> None:
    """Pretty-print 所有属性，按 legacy group 分组。"""
    groups: dict[str, list[tuple[str, AttrMeta]]] = {}
    for attr, meta in registry.items():
        sg = meta.slot_groups
        has_inv_all = bool(sg & S.INV_ALL)
        has_hand = bool(sg & S.HAND_EFF)
        has_nohand = bool(sg & S.NOHAND_INV)
        has_acc = bool(sg & S.ACC_SLOT)
        has_armor = bool(sg & S.ARMOR_SLOT)
        has_any_equip = bool(sg & (S.INV_ALL | S.HAND_EFF | S.NOHAND_INV | S.ARMOR_SLOT | S.ACC_SLOT | S.PASSIVE_CONSUM))

        if has_inv_all:
            g = "COMMON"
        elif has_hand and has_nohand:
            g = "COMBAT"
        elif has_hand and not has_nohand:
            g = "DAMAGE"
        elif has_armor and not has_acc:
            g = "DEF"
        elif has_acc or has_armor:
            g = "RESISTANCE"
        elif (sg & S.BUFF) and not has_any_equip:
            g = "BUFF_ONLY"
        else:
            g = "???"
        groups.setdefault(g, []).append((attr, meta))

    group_order = ["COMMON", "COMBAT", "DAMAGE", "RESISTANCE", "DEF", "BUFF_ONLY", "???"]
    for g in group_order:
        items = groups.get(g, [])
        if not items:
            continue
        print(f"\n{'─' * 70}")
        print(f"  {g} ({len(items)} attrs)")
        print(f"{'─' * 70}")
        for attr, meta in items:
            calls = ", ".join(sorted(c.value for c in meta.surface_calls))
            equip = ", ".join(_equip_slot_names(meta.equip_slots))
            flags: list[str] = []
            if meta.has_efficiency:
                flags.append("eff")
            if meta.has_body_parts:
                flags.append("parts")
            if meta.clamp:
                flags.append(f"[{meta.clamp[0]:g}..{meta.clamp[1]:g}]")
            flags_str = f"  ({', '.join(flags)})" if flags else ""
            print(f"  {attr:<40s} equip=[{equip}]  calls=[{calls}]{flags_str}")


def save_json_output(
    registry: dict[str, AttrMeta],
    legacy: dict[str, list[str]],
    instant: list[str],
) -> None:
    """保存提取结果到 JSON 文件。"""
    output = {
        "_meta": {
            "source": "extract_attr_sources.py",
            "description": (
                "Stoneshard 属性来源元数据 (三层 flag 架构)。\n"
                "surface_calls = Layer 1: GML 中检测到的表层函数调用。\n"
                "slot_groups   = Layer 2: GML 函数内部行为模式 (中间层)。\n"
                "equip_slots   = Layer 3: 实际生效的玩家装备栏位 (终端消费)。\n"
                "详见 extract_attr_sources.py 顶部的架构文档。"
            ),
        },
        "attributes": serialize_registry(registry),
        "legacy_groups": legacy,
        "consumable_instant_cases": instant,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 70}")
    print(f"  ✅ JSON output saved to: {OUTPUT_JSON}")
    print(f"{'=' * 70}")


# ═══════════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════════

def main():
    registry = extract_attr_registry()
    print_registry(registry)

    legacy = derive_legacy_groups(registry)
    instant = extract_consumable_instant_attrs()

    validate_against_existing(registry)

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  Total attrs in registry: {len(registry)}")
    eff_count = sum(1 for m in registry.values() if m.has_efficiency)
    bp_count = sum(1 for m in registry.values() if m.has_body_parts)
    clamp_count = sum(1 for m in registry.values() if m.clamp)
    print(f"  has_efficiency: {eff_count}")
    print(f"  has_body_parts: {bp_count}")
    print(f"  has clamp:      {clamp_count}")

    save_json_output(registry, legacy, instant)


if __name__ == "__main__":
    main()
