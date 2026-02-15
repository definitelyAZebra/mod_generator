# specialItemsPool 与物品存档/加载机制

## specialItemsPool 的作用

`specialItemsPool` 是一个 `ds_list`，通过 `scr_atr("specialItemsPool")` 访问。
存储已生成的**独特 (quality 6)** 和**文物 (quality 7)** 物品的 ID 字符串，防止同一存档中重复生成。

---

## 原版物品生成路径与 pool 处理

### 武器路径 (vanilla weapons = string ID)

| 函数 | 用途 | pool 检查 | pool 注册 |
|------|------|----------|----------|
| `scr_inventory_add_weapon` | 武器进背包 | `quality == 6` → 检查 | `quality == 6` → 注册 + `lootedUniques` |
| `scr_weapon_loot` | 武器地面掉落 | `quality == 6 && arg5 == "dynamic"` → 检查 | 同上 |

- **独特武器 (quality 6):** 完整处理 ✓
- **文物 (quality 7):** 武器路径没有 quality 7 的物品，不处理

### 物品路径 (vanilla items = object index)

| 函数 | 用途 | pool 检查 | pool 注册 |
|------|------|----------|----------|
| `scr_inventory_add_item` | 物品进背包 | `arg6 == true` → 检查 | `arg6 == true` → 注册 + `lootedTreasures` |
| `scr_loot` | 物品地面掉落 | 无 (由 caller 负责) | 无 |

- **文物 (quality 7):** 通过 `arg6` 参数由 caller 控制
- **独特 (quality 6):** vanilla 物品路径根本没有 unique 概念，unique 都是武器

### 小结

```
Vanilla unique (6)  → 全走武器路径 → scr_inventory_add_weapon / scr_weapon_loot 自带处理
Vanilla artifact (7) → 全走物品路径 → caller 传 arg6=true 触发 scr_inventory_add_item 内置处理
```

---

## scr_inventory_add_item 签名与参数语义

```gml
function scr_inventory_add_item(
    arg0,           // object index (e.g. o_inv_xxx)
    arg1 = id,      // owner instance
    arg2 = -4,      // stack count (-4 = 不设置)
    arg3 = true,    // ★ trigger alarm 0 (新建=true, 读档=false)
    arg4 = -4,      // Duration (-4 = 不设置)
    arg5 = true,    // 尝试放入背包 (false = 仅创建不放置)
    arg6 = false,   // ★ isTreasure → specialItemsPool 检查/注册
    arg7 = false     // isDropOnce → scr_consum_check_drop_once 检查
)
```

### arg3 的双重含义

`arg3` 原本是 "是否触发 alarm 0"，但在实践中也作为**新建 vs 加载**的区分标志：

- `scr_load_player` 传 `arg3 = false` → 不触发初始化 alarm，因为数据会从存档覆盖
- `scr_loadContainerContent` 传 `arg3 = false` → 同理
- 正常新建时使用默认值 `arg3 = true`

### arg6 的 treasure 路径

当 `arg6 = true` 时，函数入口处：
```gml
if (arg6) {
    if (ds_list_find_index(scr_atr("specialItemsPool"), _idName) != -1)
        return -4;  // 已存在，阻止重复生成
}
```

成功创建后：
```gml
if (arg6) {
    ds_list_add(scr_atr("specialItemsPool"), _idName);
    achivmentCounter(5, "That_Belongs_In_A_Museum");
    scr_characterStatsUpdateAdd("lootedTreasures", 1);
}
```

---

## 存档加载路径

### scr_load_player (玩家背包)

```gml
// 对每个保存的物品:
if (!is_real(_idName))
    _item = scr_inventory_add_weapon(_idName, -4, false, false, false);
                                      // quality=-4  ↑ 不触发 pool 检查
else
    _item = scr_inventory_add_item(_idName, id, _stack, false, -4, false);
                                                         // arg3=false ↑ arg5=false, arg6=默认false
```

**关键:** 
- 武器路径传 `quality = -4` → `quality == 6` 检查不命中 → 安全
- 物品路径传 `arg6 = false`（默认） → treasure 检查不触发 → 安全

### scr_loadContainerContent (容器内容)

```gml
if (!is_real(_item_id))
    _item = scr_inventory_add_weapon(_item_id, -4, false, arg4, false);
else
    _item = scr_inventory_add_item(_item_id, id, stack, false, -4, arg4);
                                                          // arg3=false ↑
```

同样安全：`quality = -4`，`arg6 = false`。

### scr_loot_drop_saved (地面掉落物品恢复)

```gml
if (!is_real(_item))
    _script = scr_weapon_loot;   // 武器
else
    _script = scr_loot;          // 普通物品

script_execute(_script, _obj, x, y, 100);  // chance=100 保证生成
```

- `scr_weapon_loot` 传 `quality = -4`（默认）→ `checkSpecialPool = false` → 安全
- `scr_loot` 本身无 pool 检查 → 安全

---

## Hybrid 物品的特殊性

Hybrid 物品打破了 vanilla 的 "unique=武器, artifact=物品" 假设：

1. **Hybrid unique (6)** 走物品路径 (`scr_inventory_add_item`)，但 vanilla 物品路径没有 unique 处理
   → 需要 patch 6 补充 unique 检查/注册
   
2. **Hybrid artifact (7)** 走物品路径，vanilla 有内置处理，但 caller 需要显式传 `arg6 = true`
   → wrapper 函数需查 registry 判断品质后传参

### 读档问题

patch 6 注入的 unique 检查如果不加 `argument3` 守卫，会在读档时阻止已拥有物品的重建。
原因：存档恢复后 `specialItemsPool` 已包含该 ID，但 `scr_load_player` 随后又调用
`scr_inventory_add_item` 重建物品 → 检查命中 → `return -4` → 物品消失。

---

## scr_loot_from_tables 中的生成逻辑

这是容器（箱子、桶等）的掉落表函数。分两部分：

### 消耗品部分 (slot1-slot9)
- 按具体物品 ID 生成，普通物品走 `scr_inventory_add_item`
- treasure 由 caller 传 `arg6 = _isTreasure` (基于 `Cat == "treasure"`)

### 装备部分 (eq1-eq5)
- `scr_find_weapon` 搜索候选 → 我们 patch 为 `scr_find_item_wrapper`
- `scr_inventory_add_weapon` 添加到背包 → patch 为 `scr_inventory_add_item_wrapper`
- `scr_weapon_loot` 地面掉落 → patch 为 `scr_loot_spawn_wrapper`
- quality 由 `_slot_rarity` 字段决定 ("unique" → `Value_6`)

### 品质传递

```gml
// scr_loot_from_tables 中:
if (!arg2)
    with (scr_inventory_add_weapon(_item, _quality)) { ... }  // 进背包
else
    with (scr_weapon_loot(_item, x, y, 100, _quality)) { ... }  // 地面掉落
```

patch 后变为:
```gml
if (!arg2)
    with (scr_inventory_add_item_wrapper(_item, _quality)) { ... }
else
    with (scr_loot_spawn_wrapper(_item, x, y, 100, _quality)) { ... }
```

注意: `_quality` 是掉落表配置的品质 (如 `Value_6`)，与 hybrid registry 中记录的 `quality` 是独立的。
掉落表的 `_quality` 控制生成时的品质效果（词缀等），而 registry 的 `quality` 控制 pool 行为。
