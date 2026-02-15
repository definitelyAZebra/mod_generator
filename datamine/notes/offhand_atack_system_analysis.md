# o_offhand_atack 系统分析

## 对象索引与继承关系

### 对象索引

| 对象名 | 索引 | 层级 |
|--------|------|------|
| `o_offhand_atack` | 6692 | 普通副手攻击控制器 |
| `o_offhand_atack_skill` | 6693 | 技能触发的副手攻击控制器 |
| `o_inv_weapon_slot` | 4478 | 武器栏基类 |
| `o_weapon_slot_parent` | 4487 | 武器栏父类 |
| `o_inv_right_hand` | 4488 | 右手栏位（子类） |
| `o_inv_left_hand` | 4490 | 左手栏位（子类） |

### 继承结构

```
o_inv_weapon_slot (4478) — 武器栏基类
  ├─ o_armor_slot_parent
  ├─ o_inv_neck
  ├─ o_ring_slot_parent
  └─ o_weapon_slot_parent (4487) — 武器栏父类
      ├─ o_inv_left_hand (4490) — 左手/副手
      └─ o_inv_right_hand (4488) — 右手/主手
```

---

## o_offhand_atack (普通副手攻击)

### Create_0 事件

```gml
is_counterattack = false;
var _time = 6;
alarm[0] = _time;
if (!global.contrattack)
{
    scr_unitTurnNext(scr_unitTurnGetTime() + _time);
}
```

**功能：**
- 初始化 `is_counterattack = false`（非反击）
- 设置 6 帧延迟的 Alarm[0]
- 如果不是反击攻击 (`!global.contrattack`)，则延长回合时间

### Alarm_0 事件

```gml
if (instance_exists(o_weapon_slot_parent))
{
    scr_weapon_slot_equip(4490, true);  // 装备左手武器 (副手)
    with (o_player)
    {
        scr_atr_calc_combat();  // 重算战斗属性
    }
    
    with (o_player)
    {
        if (other.is_counterattack)
        {
            force_attack = true;
            global.contrattack = false;
        }
        is_offhand_attack = true;
        if (scr_tile_distance_min(id, other.target) == 1)
        {
            scr_attack(other.target, other.is_counterattack);
        }
        is_offhand_attack = false;
        force_attack = false;
    }
    
    scr_weapon_slot_equip(4487, true);  // 重置到父类 (o_weapon_slot_parent)
    with (o_player)
    {
        scr_atr_calc_combat();  // 再次重算战斗属性
    }
    
    // 处理群体控制 debuff
    if (instance_exists(target))
    {
        with (o_db_crowdcontrol)
        {
            if (target != other.target)
            {
                event_user(4);
            }
            else
            {
                is_attack = true;
            }
        }
    }
}
instance_destroy();
```

**核心流程：**
1. 切换到左手武器 (4490 - o_inv_left_hand)
2. 重算战斗属性
3. 执行副手攻击（标记 `is_offhand_attack = true`）
4. 仅在目标距离 1 格时攻击
5. 切换到父类 (4487 - o_weapon_slot_parent)
   - **注意**：这不是"恢复主手"，而是重置到父类状态
6. 再次重算战斗属性
7. 处理群体控制效果
8. 销毁攻击控制器

---

## o_offhand_atack_skill (技能触发副手攻击)

### Create_0 事件

```gml
var _time = 6;
alarm[0] = _time;
owner = -4;              // 技能拥有者
slot = 4490;             // 副手栏位
destroy_after_hit = false;
play_animation = false;
event_call = false;
attack_mod = false;      // 是否应用攻击修正
```

**初始化参数：**
- `owner` — 技能对象的引用
- `slot` — 默认副手 (4490)，但可配置
- `destroy_after_hit` — 命中后是否销毁技能对象
- `play_animation` — 播放动画 ID
- `event_call` — 命中后是否调用 owner 的 event_user(0)
- `attack_mod` — 是否触发 event_user(15) 修改攻击属性

### Alarm_0 事件

```gml
if (instance_exists(o_weapon_slot_parent))
{
    scr_weapon_slot_equip(slot, true);  // 装备指定栏位（通常是 4490 副手）
    var hit;
    with (o_player)
    {
        force_attack = true;
        if (other.play_animation)
        {
            scr_skill_hit(other.play_animation);  // 播放技能动画
        }
        scr_atr_calc_combat();
        if (other.attack_mod)
        {
            with (other.owner)
            {
                event_user(15);  // 调用技能的攻击修正事件
            }
        }
        hit = scr_attack(other.target);  // 执行攻击
        force_attack = false;
    }
    
    with (owner)
    {
        is_hit = hit;  // 记录是否命中
    }
    
    scr_weapon_slot_equip(4487, true);  // 重置到父类 (o_weapon_slot_parent)
    with (o_player)
    {
        scr_atr_calc_combat();
    }
    
    // 处理群体控制 debuff
    if (instance_exists(target))
    {
        with (o_db_crowdcontrol)
        {
            if (target != other.target)
            {
                event_user(4);
            }
            else
            {
                is_attack = true;
            }
        }
    }
}

// 命中后处理
if (destroy_after_hit)
{
    with (owner)
    {
        instance_destroy();  // 销毁技能对象
    }
}
else
{
    with (owner)
    {
        alarm[0] = alarm0_delay_offhand_skill;  // 重置技能 alarm
        if (other.event_call)
        {
            event_user(0);  // 调用技能的后续事件
        }
    }
}
instance_destroy();
```

**核心区别：**
1. 支持自定义 `slot`（不一定是左手）
2. 可以播放技能动画 (`play_animation`)
3. 可以触发技能的攻击修正 (`attack_mod` → `event_user(15)`)
4. 记录命中结果到 `owner.is_hit`
5. 命中后可销毁技能或触发后续事件

---

## 关键差异对比

| 特性 | o_offhand_atack | o_offhand_atack_skill |
|------|----------------|---------------------|
| **用途** | 普通副手攻击（如双持） | 技能触发的副手攻击 |
| **栏位** | 固定 4490 (左手) | 可配置 `slot` |
| **距离检查** | 必须距离 1 格 | 无距离检查 |
| **动画** | 无 | 支持 `scr_skill_hit()` |
| **攻击修正** | 无 | 支持 `event_user(15)` |
| **命中反馈** | 无 | 记录到 `owner.is_hit` |
| **后续处理** | 直接销毁 | 可销毁技能或触发事件 |
| **反击支持** | 有 `is_counterattack` | 无 |

---

## 武器切换机制

两种对象都使用相同的武器切换流程：

```gml
// 1. 切换到副手
scr_weapon_slot_equip(4490, true);  // o_inv_left_hand (或自定义 slot)
scr_atr_calc_combat();  // 用副手属性重算

// 2. 执行攻击
// ...

// 3. 重置到父类
scr_weapon_slot_equip(4487, true);  // o_weapon_slot_parent
scr_atr_calc_combat();  // 重算属性
```

**设计要点：**
- 每次切换武器都重新计算战斗属性
- 攻击前：切换到具体子类 (o_inv_left_hand / o_inv_right_hand)
- 攻击后：重置到父类 (o_weapon_slot_parent)
- **推测**：父类状态可能代表"当前主要装备武器"或"默认战斗状态"

---

## 群体控制处理 (CrowdControl)

两种对象都在攻击后处理 `o_db_crowdcontrol` debuff：

```gml
with (o_db_crowdcontrol)
{
    if (target != other.target)
    {
        event_user(4);  // 非当前目标：触发某种逻辑
    }
    else
    {
        is_attack = true;  // 当前目标：标记为攻击
    }
}
```

**可能用途：**
- 处理仇恨/嘲讽效果
- 更新群体控制状态
- 触发 debuff 特效或伤害

---

## 使用场景推测

### o_offhand_atack (普通副手攻击)
- **双持武器** — 主手攻击后触发副手攻击
- **反击机制** — `is_counterattack` 支持反击流程
- **距离限制** — 必须近战距离 (1格)

### o_offhand_atack_skill (技能副手攻击)
- **技能系统** — 某些技能可触发额外副手攻击
- **灵活配置** — `attack_mod` 允许技能修改伤害计算
- **动画支持** — 播放特定技能动画
- **持续技能** — `destroy_after_hit = false` 支持多次触发

---

## 后续研究方向

1. **scr_weapon_slot_equip()** — 武器切换具体实现
2. **scr_attack()** — 攻击逻辑与伤害计算
3. **scr_atr_calc_combat()** — 战斗属性计算公式
4. **event_user(15)** — 技能的攻击修正机制
5. **o_db_crowdcontrol** — 群体控制 debuff 系统
6. **双持武器触发条件** — 何时创建 `o_offhand_atack`
7. **scr_skill_hit()** — 技能动画播放机制
