# -*- coding: utf-8 -*-
"""
从 GML 源码中提取武器单双手 & 角色贴图姿势数据。

=== 背景 ===

Stoneshard 的武器有两个独立的"手数"概念:
- hands:                游戏机制手数 (占几个手槽)
- character_sprite_hands: 角色贴图姿势 (1=单手握持, 2=双手握持)

这两个值 *通常* 一致，但在 bow / spear 等武器上不同:
    bow:   hands=2 (占2手), character_sprite_hands=1 (单手姿势)
    spear: hands=2 (占2手), character_sprite_hands=1 (单手姿势)

GML 中由 scr_inv_weapon_get_hands(type) 决定:
    Switch 1 — 按 Slot (武器类型) 设置默认规则
    Switch 2 — 按 idName (物品名)  覆盖特定物品

Switch 2 中的物品不一定有独立的"武器类型" — 有些是已有类型的物品级例外
(如 Peasant Scythe 是 2haxe 但使用单手姿势)。本脚本从 weapons.json
查出这些物品的 Slot 类型，然后:
    - 若该类型在 Switch 1 中未出现 → 以该物品为代表，新增类型规则
    - 若该类型已有规则但值不同 → 记为 item_overrides (物品级例外)

=== 派生字段 ===

needs_char_left: 是否需要左手角色贴图 (= 可双持的单手武器)
    hands == 1 → True (sword, dagger, axe, mace 等)
    hands == 2 → False

pose_index: 贴图编辑器使用的姿势索引
    character_sprite_hands - 1 (0=单手, 1=双手)

=== 输出 ===

datamine/output/weapon_hands.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
# Paths
# ═══════════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GML_DIR = ROOT / "datamine" / "output" / "CodeEntries"
GML_FILE = GML_DIR / "gml_GlobalScript_scr_inv_weapon_get_hands.gml"
WEAPONS_JSON = ROOT / "references" / "data" / "tables" / "weapons.json"
OUTPUT_DIR = ROOT / "datamine" / "output"
OUTPUT_JSON = OUTPUT_DIR / "weapon_hands.json"


# ═══════════════════════════════════════════════════════════════════
# GML parsing — Switch 1 (weapon type rules)
# ═══════════════════════════════════════════════════════════════════

# 匹配 switch 块中的 case + 赋值语句
#   case "2hsword":
#       character_sprite_hands = 2;
#       hands = 2;
_RE_CASE = re.compile(r'case\s+"([^"]+)"\s*:')
_RE_SPRITE_HANDS = re.compile(r"character_sprite_hands\s*=\s*(\d+)\s*;")
_RE_HANDS = re.compile(r"(?<!\w)hands\s*=\s*(\d+)\s*;")


def _parse_switch_block(text: str) -> list[tuple[str, int, int]]:
    """解析一个 switch 块中的 (key, hands, sprite_hands) 条目。

    Returns: [(key, hands, sprite_hands), ...]
    """
    results: list[tuple[str, int, int]] = []
    current_key: str | None = None
    current_hands: int | None = None
    current_sprite: int | None = None

    for line in text.splitlines():
        stripped = line.strip()

        case_m = _RE_CASE.match(stripped)
        if case_m:
            # 提交上一个 case
            if current_key is not None and current_hands is not None and current_sprite is not None:
                results.append((current_key, current_hands, current_sprite))
            current_key = case_m.group(1)
            current_hands = None
            current_sprite = None
            continue

        if stripped.startswith("default:"):
            if current_key is not None and current_hands is not None and current_sprite is not None:
                results.append((current_key, current_hands, current_sprite))
            current_key = "__default__"
            current_hands = None
            current_sprite = None
            continue

        sprite_m = _RE_SPRITE_HANDS.search(stripped)
        if sprite_m:
            current_sprite = int(sprite_m.group(1))

        hands_m = _RE_HANDS.search(stripped)
        if hands_m:
            current_hands = int(hands_m.group(1))

        if stripped == "break;":
            if current_key is not None and current_hands is not None and current_sprite is not None:
                results.append((current_key, current_hands, current_sprite))
            current_key = None
            current_hands = None
            current_sprite = None

    # 最后一个 case (没有 break 的情况)
    if current_key is not None and current_hands is not None and current_sprite is not None:
        results.append((current_key, current_hands, current_sprite))

    return results


def parse_gml(gml_path: Path) -> tuple[
    dict[str, tuple[int, int]],   # type_rules:  {type: (hands, sprite)}
    dict[str, tuple[int, int]],   # id_overrides: {idName: (hands, sprite)}
    tuple[int, int],              # default_rule: (hands, sprite)
]:
    """解析 scr_inv_weapon_get_hands.gml，提取两个 switch 的规则。"""
    text = gml_path.read_text(encoding="utf-8")

    # 分割两个 switch 块
    # Switch 1: switch (arg0) — 按武器类型
    # Switch 2: switch (ds_map_find_value(data, "idName")) — 按物品名
    switch_splits = list(re.finditer(r"switch\s*\(", text))
    if len(switch_splits) < 2:
        raise ValueError(f"Expected 2 switch blocks in {gml_path}, found {len(switch_splits)}")

    switch1_start = switch_splits[0].start()
    switch2_start = switch_splits[1].start()
    switch1_text = text[switch1_start:switch2_start]
    switch2_text = text[switch2_start:]

    # 解析 Switch 1 — 类型级规则
    entries1 = _parse_switch_block(switch1_text)
    type_rules: dict[str, tuple[int, int]] = {}
    default_rule: tuple[int, int] = (1, 1)  # fallback
    for key, hands, sprite in entries1:
        if key == "__default__":
            default_rule = (hands, sprite)
        else:
            type_rules[key] = (hands, sprite)

    # 解析 Switch 2 — 物品级覆盖
    entries2 = _parse_switch_block(switch2_text)
    id_overrides: dict[str, tuple[int, int]] = {
        key: (hands, sprite) for key, hands, sprite in entries2 if key != "__default__"
    }

    return type_rules, id_overrides, default_rule


# ═══════════════════════════════════════════════════════════════════
# weapons.json — 查询物品的 Slot 类型
# ═══════════════════════════════════════════════════════════════════


def load_weapon_slots(weapons_json: Path) -> dict[str, str]:
    """从 weapons.json 加载 {idName: Slot} 映射。"""
    data = json.loads(weapons_json.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for _section_name, section in data.items():
        if not isinstance(section, dict):
            continue
        for item_name, item_data in section.items():
            if isinstance(item_data, dict) and "Slot" in item_data:
                slot = item_data["Slot"]
                if isinstance(slot, str) and slot:
                    result[item_name] = slot
    return result


# ═══════════════════════════════════════════════════════════════════
# 合并 — 将物品级覆盖归入类型或标记为例外
# ═══════════════════════════════════════════════════════════════════


def merge_overrides(
    type_rules: dict[str, tuple[int, int]],
    id_overrides: dict[str, tuple[int, int]],
    default_rule: tuple[int, int],
    weapon_slots: dict[str, str],
) -> tuple[
    dict[str, tuple[int, int]],          # final type_rules (可能新增条目)
    dict[str, dict[str, str | int]],     # item_overrides (无法归入类型的例外)
    list[str],                           # warnings
]:
    """将 Switch 2 的物品级覆盖合并到类型规则中。

    策略:
    - 物品的 Slot 类型在 type_rules 中无条目 → 新增类型规则
    - 物品的 Slot 类型在 type_rules 中有条目但值不同 → item_overrides
    - 物品的 Slot 类型找不到 → warning
    """
    final_rules = dict(type_rules)
    item_exceptions: dict[str, dict[str, str | int]] = {}
    warnings: list[str] = []

    for id_name, (hands, sprite) in id_overrides.items():
        slot = weapon_slots.get(id_name)
        if slot is None:
            warnings.append(f"  ⚠ Item '{id_name}' not found in weapons.json, skipping")
            continue

        # 该类型的当前规则 (可能是 Switch 1 定义的，也可能是 default)
        existing_rule = final_rules.get(slot)

        if existing_rule is None:
            # 类型在 Switch 1 中未出现 → 新增类型规则
            # 先检查 default 是否已经匹配
            if default_rule == (hands, sprite):
                # 与 default 一致，无需新增
                continue
            final_rules[slot] = (hands, sprite)
            print(f"  + New type rule: {slot} = (hands={hands}, sprite={sprite})"
                  f"  ← from '{id_name}'")
        elif existing_rule == (hands, sprite):
            # 与类型默认一致，无需处理
            pass
        else:
            # 覆盖值与类型默认不同 → 物品级例外
            item_exceptions[id_name] = {
                "slot": slot,
                "hands": hands,
                "sprite_hands": sprite,
                "note": (
                    f"overrides {slot} default "
                    f"(hands={existing_rule[0]}, sprite={existing_rule[1]})"
                ),
            }
            print(f"  ! Item exception: {id_name} ({slot}) = "
                  f"(hands={hands}, sprite={sprite})"
                  f"  [type default: hands={existing_rule[0]}, sprite={existing_rule[1]}]")

    return final_rules, item_exceptions, warnings


# ═══════════════════════════════════════════════════════════════════
# 输出
# ═══════════════════════════════════════════════════════════════════


def build_output(
    type_rules: dict[str, tuple[int, int]],
    default_rule: tuple[int, int],
    item_overrides: dict[str, dict[str, str | int]],
) -> dict:
    """构建输出 JSON。

    每个类型规则包含:
    - hands: 游戏机制手数
    - sprite_hands: 角色贴图姿势
    - needs_char_left: 是否需要左手角色贴图 (= hands == 1)
    - pose_index: 贴图编辑器姿势索引 (= sprite_hands - 1)
    """
    def _entry(hands: int, sprite: int) -> dict:
        return {
            "hands": hands,
            "sprite_hands": sprite,
            "needs_char_left": hands == 1,
            "pose_index": sprite - 1,
        }

    # 按类型名字母序排列
    sorted_types = sorted(type_rules.keys())

    return {
        "_meta": {
            "source": "extract_weapon_hands.py",
            "gml": "gml_GlobalScript_scr_inv_weapon_get_hands.gml",
            "description": (
                "武器单双手 & 角色贴图姿势数据。\n"
                "hands = 游戏机制手数 (占几个手槽)。\n"
                "sprite_hands = 角色贴图姿势 (1=单手, 2=双手)。\n"
                "needs_char_left = 是否需要左手角色贴图。\n"
                "pose_index = 贴图编辑器姿势索引 (sprite_hands - 1)。"
            ),
        },
        "default": _entry(*default_rule),
        "type_rules": {t: _entry(*type_rules[t]) for t in sorted_types},
        "item_overrides": item_overrides,
    }


def print_summary(
    type_rules: dict[str, tuple[int, int]],
    default_rule: tuple[int, int],
    item_overrides: dict[str, dict[str, str | int]],
) -> None:
    """打印提取结果摘要。"""
    dh, ds = default_rule
    print(f"\n{'=' * 60}")
    print(f"  武器单双手 & 贴图姿势提取结果")
    print(f"{'=' * 60}")
    print(f"\n  Default: hands={dh}, sprite_hands={ds}")
    print(f"\n  类型规则 ({len(type_rules)}):")
    print(f"  {'Type':<12} {'hands':>5} {'sprite':>7} {'left':>6} {'pose':>5}")
    print(f"  {'-' * 12} {'-' * 5} {'-' * 7} {'-' * 6} {'-' * 5}")

    for t in sorted(type_rules.keys()):
        h, s = type_rules[t]
        left = "✓" if h == 1 else ""
        pose = s - 1
        marker = ""
        if h != s:
            marker = "  ← hands ≠ sprite!"
        print(f"  {t:<12} {h:>5} {s:>7} {left:>6} {pose:>5}{marker}")

    if item_overrides:
        print(f"\n  物品级例外 ({len(item_overrides)}):")
        for name, info in item_overrides.items():
            print(f"    {name}: slot={info['slot']}, "
                  f"hands={info['hands']}, sprite={info['sprite_hands']}")
            print(f"      {info['note']}")


def save_output(output: dict) -> None:
    """保存 JSON 输出。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n{'=' * 60}")
    print(f"  ✅ Saved to: {OUTPUT_JSON}")
    print(f"{'=' * 60}")


# ═══════════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════════


def main():
    # 1. 解析 GML
    print(f"Parsing {GML_FILE.name} ...")
    type_rules, id_overrides, default_rule = parse_gml(GML_FILE)
    print(f"  Switch 1 (type rules): {len(type_rules)} entries + default")
    print(f"  Switch 2 (id overrides): {len(id_overrides)} entries")

    # 2. 加载武器数据
    print(f"\nLoading {WEAPONS_JSON.name} ...")
    weapon_slots = load_weapon_slots(WEAPONS_JSON)
    print(f"  {len(weapon_slots)} weapons loaded")

    # 3. 合并
    print(f"\nMerging overrides ...")
    final_rules, item_exceptions, warnings = merge_overrides(
        type_rules, id_overrides, default_rule, weapon_slots,
    )
    for w in warnings:
        print(w)

    # 4. 打印摘要
    print_summary(final_rules, default_rule, item_exceptions)

    # 5. 验证 — 与现有硬编码常量交叉检查
    print(f"\n  验证 ...")
    _validate(final_rules, default_rule)

    # 6. 保存
    output = build_output(final_rules, default_rule, item_exceptions)
    save_output(output)


def _validate(
    type_rules: dict[str, tuple[int, int]],
    default_rule: tuple[int, int],
) -> None:
    """与 specs.py 中的硬编码常量交叉检查。"""
    from core.specs import WeaponEquip

    # 检查 TWO_HAND_WEAPONS
    two_hand_from_data = {t for t, (h, _) in type_rules.items() if h == 2}
    two_hand_from_specs = set(WeaponEquip.TWO_HAND_WEAPONS)
    delta_extra = two_hand_from_data - two_hand_from_specs
    delta_missing = two_hand_from_specs - two_hand_from_data

    if delta_extra:
        print(f"    ℹ Data has 2H types not in TWO_HAND_WEAPONS: {delta_extra}")
        print(f"      (These are newly discovered types: tool, pick, etc.)")
    if delta_missing:
        print(f"    ⚠ TWO_HAND_WEAPONS has types not in data: {delta_missing}")
    if not delta_extra and not delta_missing:
        print(f"    ✓ TWO_HAND_WEAPONS matches")

    # 检查 LEFT_HAND_WEAPONS
    left_from_data = {t for t, (h, s) in type_rules.items() if h == 1}
    # 加上 default 的 hands==1 类型 (不在 type_rules 中的类型走 default)
    left_from_specs = set(WeaponEquip.LEFT_HAND_WEAPONS)
    if left_from_data == left_from_specs:
        print(f"    ✓ LEFT_HAND_WEAPONS matches (data h==1 types)")
    else:
        # LEFT_HAND_WEAPONS 中的类型应该都走 default (hands=1)
        # 且 default hands=1，所以 LEFT_HAND_WEAPONS 都不在 type_rules 中
        in_rules = left_from_specs & set(type_rules.keys())
        not_in_rules = left_from_specs - set(type_rules.keys())
        if in_rules:
            print(f"    ⚠ LEFT_HAND_WEAPONS types in explicit rules: {in_rules}")
        if not_in_rules:
            dh, _ = default_rule
            if dh == 1:
                print(f"    ✓ LEFT_HAND_WEAPONS types use default (hands=1): {not_in_rules}")
            else:
                print(f"    ⚠ LEFT_HAND_WEAPONS types use default but default hands≠1!")


if __name__ == "__main__":
    main()
