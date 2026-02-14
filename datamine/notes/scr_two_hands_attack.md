# scr_two_hands_attack & scr_two_hands_check

## 概述

双手/双持攻击系统的核心脚本，负责判断是否触发副手攻击并创建对应的攻击控制器。

---

## scr_two_hands_attack(target, is_skill)

### 函数签名

```gml
function scr_two_hands_attack(arg0, arg1 = false)
```

**参数：**
- `arg0` (target) — 攻击目标
- `arg1` (is_skill) — 是否为技能触发（默认 false）

### 完整代码

```gml
function scr_two_hands_attack(arg0, arg1 = false)
{
    with (o_player)
    {
        if (scr_two_hands_check())
        {
            scr_weapon_slot_equip(4488, true);  // 装备右手 (o_inv_right_hand)
            scr_atr_calc_combat();
            force_attack = arg1;
            scr_attack(arg0);
            scr_weapon_slot_equip(4487, true);  // 重置到父类 (o_weapon_slot_parent)
            
            if (!arg1)
            {
                // 普通攻击：创建普通副手攻击控制器
                with (instance_create_depth(x, y, 0, o_offhand_atack))
                {
                    target = arg0;
                }
            }
            else
            {
                // 技能攻击：创建技能副手攻击控制器
                with (instance_create_depth(x, y, 0, o_offhand_atack_skill))
                {
                    target = arg0;
                }
            }
        }
        else
        {
            // 不满足双手条件：执行普通单手攻击
            force_attack = arg1;
            scr_attack(arg0);
        }
        force_attack = false;
    }
}
```

### 执行流程

#### 满足双手条件时（双持/双武器）

```
1. scr_two_hands_check() → true
   │
2. 切换到右手 (4488)
   │
3. 重算战斗属性
   │
4. 执行主手攻击 scr_attack(target)
   │
5. 重置到父类 (4487)
   │
6. 创建副手攻击控制器：
   ├─ is_skill = false → o_offhand_atack (普通)
   └─ is_skill = true  → o_offhand_atack_skill (技能)
```

#### 不满足双手条件时

```
1. scr_two_hands_check() → false
   │
2. 直接执行 scr_attack(target)
   │
3. 无副手攻击
```

### 关键设计

1. **主手优先** — 先用右手攻击，再触发左手
2. **武器切换** — 攻击前切换到右手，攻击后重置父类
3. **延迟副手** — 副手攻击由控制器延迟执行（6 帧后）
4. **技能支持** — `is_skill` 参数决定使用哪种攻击控制器

---

## scr_two_hands_check(strict_mode)

### 函数签名

```gml
function scr_two_hands_check(arg0 = false)
```

**参数：**
- `arg0` (strict_mode) — 严格模式：要求左右手武器类型相同（默认 false）

### 完整代码

```gml
function scr_two_hands_check(arg0 = false)
{
    // 1. 射击武器不能双手攻击
    if (scr_is_weapon_type_shooting())
    {
        return false;
    }
    
    // 2. 玩家必须在地面上
    if (instance_exists(o_player))
    {
        if (o_player.isGround == -1)
        {
            return false;
        }
    }
    
    // 3. 检查双手装备
    if (instance_exists(o_inv_right_hand) && instance_exists(o_inv_left_hand))
    {
        if (o_inv_right_hand.children && o_inv_left_hand.children)
        {
            if (instance_exists(o_inv_right_hand.children) && instance_exists(o_inv_left_hand.children))
            {
                // 4. 双手都必须有 DMG 属性（即都是武器）
                if (!__is_undefined(ds_map_find_value(o_inv_left_hand.children.data, "DMG")) && 
                    !__is_undefined(ds_map_find_value(o_inv_right_hand.children.data, "DMG")))
                {
                    var _type_left = o_inv_left_hand.children.type;
                    var _type_right = o_inv_right_hand.children.type;
                    
                    // 5. 双手都不能是盾牌
                    if (_type_left != "shield" && _type_right != "shield")
                    {
                        // 6. 严格模式下要求武器类型相同
                        if (!arg0 || _type_left == _type_right)
                        {
                            return true;
                        }
                    }
                }
            }
        }
    }
    return false;
}
```

### 判断条件（全部满足才返回 true）

| # | 条件 | 说明 |
|---|------|------|
| 1 | 非射击武器 | `!scr_is_weapon_type_shooting()` |
| 2 | 玩家在地面 | `o_player.isGround != -1` |
| 3 | 双手都有装备 | `o_inv_right_hand.children` 和 `o_inv_left_hand.children` 存在 |
| 4 | 双手都有 DMG | 都是武器（而非杂物） |
| 5 | 双手都非盾牌 | `type != "shield"` |
| 6 | 类型匹配（严格模式） | `strict_mode = false` 或 `_type_left == _type_right` |

### 示例场景

#### ✅ 允许双手攻击

```
- 双持剑 (sword + sword)
- 双持匕首 (dagger + dagger)
- 剑 + 斧 (sword + axe) — 仅在非严格模式
```

#### ❌ 禁止双手攻击

```
- 剑 + 盾 (shield 禁止)
- 弓 (射击武器禁止)
- 单手武器 (缺少副手)
- 跳跃中 (isGround = -1)
- 剑 + 斧 (严格模式下类型不同)
```

---

## 与 o_offhand_atack 系统的关联

| 对象 | 创建时机 | 创建者 |
|------|---------|--------|
| `o_offhand_atack` | `scr_two_hands_attack(target, false)` | 普通双持攻击 |
| `o_offhand_atack_skill` | `scr_two_hands_attack(target, true)` | 技能触发的双持攻击 |

**流程图：**

```
玩家执行攻击
    │
    ├─ 调用 scr_two_hands_attack(target, is_skill)
    │      │
    │      ├─ scr_two_hands_check() == true?
    │      │      │
    │      │      ├─ YES → 主手攻击 + 创建副手控制器
    │      │      │         │
    │      │      │         ├─ is_skill = false → o_offhand_atack
    │      │      │         └─ is_skill = true  → o_offhand_atack_skill
    │      │      │
    │      │      └─ NO → 单手攻击
    │
    └─ 6 帧后，副手控制器的 Alarm_0 触发副手攻击
```

---

## 关键发现

1. **右手是主手** — `scr_two_hands_attack` 优先装备并攻击右手 (4488)
2. **左手是副手** — 副手攻击由 `o_offhand_atack` 延迟执行左手 (4490)
3. **严格模式未启用** — 原版游戏允许不同类型武器的双持（剑+斧）
4. **盾牌特殊处理** — 盾牌不参与双手攻击判断
5. **射击武器禁止** — 弓/弩等无法触发副手攻击

---

## 后续研究方向

- `scr_is_weapon_type_shooting()` — 射击武器类型判断
- `o_player.isGround` — 地面状态管理（跳跃/击飞）
- `children.data["DMG"]` — 武器属性数据结构
- `children.type` — 武器类型枚举（sword/dagger/axe/shield 等）
- 严格模式的使用场景（哪些技能会传入 `strict_mode = true`？）
