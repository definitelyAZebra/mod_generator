# datamine/ — 游戏数据挖掘层

从 Stoneshard 游戏源文件中 **机械提取** 结构化数据。

## 快速开始

```bash
# 1. 下载 UTMT_CLI (一次性, ~60MB)
python datamine/setup_cli.py

# 2. 反编译 data.win → GML + 元数据
python datamine/decompile.py "C:/path/to/Stoneshard/data.win"

# 3. 运行提取脚本
python datamine/extract_attr_sources.py
```

## 目录结构

```
datamine/
├── setup_cli.py              下载 UTMT_CLI 工具
├── decompile.py              反编译 data.win → GML + meta
├── export_meta.csx           UMT 结构元数据导出脚本 (C#)
├── extract_attr_sources.py    属性来源元数据提取 (两层 flag 架构)
├── extract_textloader.py     textLoader 全量数据提取 (Python)
├── README.md                 本文件
├── vendor/                   (gitignored) 下载的工具
│   └── UTMT_CLI/             UndertaleModTool CLI
└── output/                   (gitignored) 提取产物
    ├── CodeEntries/          反编译 GML 代码 (~26000 .gml 文件)
    ├── meta/                 结构元数据 JSON
    │   ├── object_index_map.json
    │   ├── object_tree.json
    │   ├── sprite_index_map.json
    │   └── sound_index_map.json
    └── textloader/           textLoader 提取产物 (详见下方)
        ├── _variable_index.json   变量名 → 文件路径 + kind + 来源
        ├── _ir_summary.json       GML IR 诊断信息
        ├── _manifest.json         提取统计 + 文件清单
        ├── attributes/            属性元数据 (26 files)
        ├── basics/                基础文本 (43 files)
        ├── equipment/             武器 + 护甲 (14 files)
        ├── consumables/           消耗品 (7 files)
        ├── skills/                技能 (8 files)
        ├── enemies/               敌人 (9 files)
        └── ... (共 24 个语义文件夹, 182 个变量文件)
```

## 设计意图

项目中存在一条隐式的数据管线：

```
data.win → UTMT_CLI → GML + meta JSON → Python 提取脚本 → data/*.py
```

这个目录的作用是把 **"从游戏源码中提取数据"** 这一关注点显式独立出来，
与项目自身的 codegen（如 `generate_tailwind_tokens.py`）和业务逻辑分离。

**路径约定优于配置**: 所有路径都基于 `datamine/` 相对推算，零配置文件。
`data.win` 的路径是唯一因机器而异的输入 — 通过命令行参数传入。

### 与 `scripts/` + `references/` 的关系

采取 **冗余 + 逐步迁移** 策略：
- `scripts/` 中已有的脚本暂不搬动，避免打破现有工作流
- `references/` 是旧体系的输出目录，由 `paths.json` 配置
- 新增的数据挖掘脚本直接放这里，输出到 `datamine/output/`
- 未来可按需将 `scripts/` 中的 extract/generate 脚本逐步迁入

最终目标：`scripts/` 仅保留项目 codegen，`datamine/` 承载所有游戏数据提取。

## 完整管线概览

### Stage 0: 反编译 (`datamine/decompile.py`)

调用 UTMT_CLI 完成：
1. **GML dump** — 反编译所有 code entries → `datamine/output/CodeEntries/*.gml`
2. **Meta export** — 运行 `export_meta.csx` → `datamine/output/meta/*.json`

```bash
python datamine/decompile.py <data.win>             # 全量 (GML + meta)
python datamine/decompile.py <data.win> --gml-only   # 仅 GML
python datamine/decompile.py <data.win> --meta-only   # 仅 meta
```

### Stage 1: textLoader 全量数据提取 (`datamine/extract_textloader.py`)

从 `gml_Object_o_textLoader_Other_25.gml` 中自动解析所有 41 个 case，
提取游戏运行时加载的全部数据（翻译文本、数值属性、掉落表、配方等）。

- **输入**: `datamine/output/CodeEntries/gml_Object_o_textLoader_Other_25.gml`
  及其引用的 `gml_GlobalScript_table_*.gml` 文件
- **输出**: `datamine/output/textloader/` — 每个变量一个 JSON 文件，按语义分目录

```bash
python datamine/extract_textloader.py              # 提取全部
python datamine/extract_textloader.py --cases 4 32  # 仅提取指定 case
python datamine/extract_textloader.py --ir-only     # 仅打印解析的 IR (不提取)
python datamine/extract_textloader.py -v            # 详细日志
```

详见下方 [extract_textloader.py 详解](#extract_textloaderpy-详解)。

### Stage 1.5: GML 数据表解析 (`scripts/extract_gml_tables.py`)

扫描所有 `table_*.gml` 文件，解析 ds_map/ds_list 赋值为 JSON。

- **输入**: `references/gml/gml_GlobalScript_table_*.gml` (~44 文件)
- **输出**: `references/data/tables/*.json` (attributes, mobs, drops, skills, text 等)
- **迁移计划**: 未来迁入 datamine/，输入改为 `datamine/output/CodeEntries/`

### Stage 2: 生成可导入的 Python 模块

| 脚本 | 来源 | 输出 | 位置 |
|------|------|------|------|
| `extract_textloader.py` | GML (textLoader + tables) | `textloader/` (182 变量文件) | **datamine/** |
| `extract_attr_sources.py` | GML 直接解析 (5 文件) | 属性 SurfaceCall + SlotGroup flags / 效率 / 部位 / clamp | **datamine/** |
| `extract_attribute_specs.py` | GML 直接解析 (3 文件) | `data/attribute_meta.py` | scripts/ |
| `generate_translations.py` | `tables/attributes.json` | `data/attributes.py` | scripts/ |
| `generate_skill_constants.py` | tables + meta + GML | `data/skills.py` | scripts/ |
| `generate_enemy_drop_constants.py` | tables + meta + GML | `data/enemies.py` | scripts/ |
| `extract_shop_configs.py` | tables + meta + GML | `data/shops.py` | scripts/ |
| `preprocess_drops.py` | `tables/drops.json` | `data/drop_index.py` | scripts/ |

### 游戏更新后的执行顺序

```
# --- 新管线 (datamine/) ---
1. python datamine/setup_cli.py          # 首次/更新 CLI (一次性)
2. python datamine/decompile.py <data.win>  # GML + meta → datamine/output/

# --- textLoader 提取 (datamine/) ---
3. python datamine/extract_textloader.py    # 182 变量 → datamine/output/textloader/

# --- 旧管线 (scripts/ + references/) ---
# 以下脚本目前仍读取 references/，待未来迁移
4. extract_gml_tables   → references/data/tables/
5. 以下可并行:
   ├── generate_translations        → data/attributes.py
   ├── extract_attribute_specs      → data/attribute_meta.py
   ├── generate_skill_constants     → data/skills.py
   ├── generate_enemy_drop_constants→ data/enemies.py
   ├── extract_shop_configs         → data/shops.py
   └── preprocess_drops             → data/drop_index.py

# --- 新管线中的提取 ---
6. python datamine/extract_attr_sources.py  # 属性来源元数据 + 验证
```

## 本目录中的脚本

### `extract_textloader.py` 详解

#### 架构

两层设计，游戏更新后 **零手工修改即可重跑**：

1. **GML Parser** — 用正则从原始 GML 中自动提取所有硬编码数据
   （变量名、table 来源、column tags、ds_map_set 常量等）→ 结构化 IR
2. **Logic Replicator** — 在 Python 中实现 GML 辅助函数语义
   （`scr_tableWriteMap`, `scr_array2d_to_map` 等），按顺序执行 IR

执行模型为 **全局 store**：case 0→40 按顺序写入同一个 dict，
跨 case 的 `clear=false` 合并（如 `weapons_stat` 由 case 32 创建、case 33 追加）
自动正确处理。

#### 输出结构

```
textloader/
├── _variable_index.json          # 变量名 → 文件路径 + kind + 来源 case
├── _ir_summary.json              # 每个 case 的 IR 摘要 (GML 溯源)
├── _manifest.json                # 提取统计 + 完整文件清单
│
├── attributes/                   # 属性元数据
│   ├── attribute.json            # {id: {lang: text}} — 属性显示名
│   ├── attribute_negative.json   # ["FMB", ...] — 负面属性列表
│   ├── attribute_order_all.json  # 属性显示排序
│   └── ...                       # (26 files)
├── basics/                       # 基础 UI/角色/声望文本
│   ├── char_name.json            # 角色名多语言
│   ├── trade_category.json       # 交易分类
│   └── ...                       # (43 files)
├── books/                        # 书籍内容
├── caravan/                      # 大篷车升级/追随者
├── character/                    # 角色统计分类
├── consumables/                  # 消耗品名称/描述/数值
│   ├── consum_name.json          # {id: {lang: text}} — 消耗品名
│   ├── consum_stat_data.json     # {id: {attr: value}} — 消耗品数值
│   └── ...                       # (7 files)
├── contracts/                    # 合同任务
├── dialog/                       # 对话/独白/语音
├── drops/                        # 掉落表
│   └── drop_table.json           # {slot_id: {slot1..eq5 配置}}
├── dungeons/                     # 地牢名称/修饰词/预设
├── economy/                      # 供需系数
├── effects/                      # Buff/诅咒名称描述
├── enemies/                      # 敌人名称/属性/AI/平衡数值
├── equipment/                    # 武器 + 护甲 (共用)
│   ├── weapon_name.json          # {id: {lang: text}} — 包含武器+护甲名
│   ├── weapons_stat.json         # {id: {attr: value}} — 合并了武器+护甲
│   ├── weapons_csv.json          # [[header], [row]...] — 武器原始2D数组
│   ├── armor_csv.json            # [[header], [row]...] — 护甲原始2D数组
│   └── ...                       # (14 files)
├── locations/                    # 地点名称描述
├── misc/                         # 鸣谢/赞助者
├── npc/                          # NPC 信息/台词
├── potions/                      # 药水名称/效果/数值
├── quests/                       # 任务文本
├── recipes_cook/                 # 烹饪配方
├── recipes_craft/                # 制造配方
├── skills/                       # 技能名称/描述/数值
├── spawns/                       # 地牢+地表刷怪表
└── ui/                           # 操作日志/提示/快捷键
```

每个文件 = 一个 GML 全局变量，文件名 = 变量名。

#### `_variable_index.json` 格式

这是 agent 和脚本消费数据的**核心入口**。按变量名查 → 得到文件路径 + 数据类型：

```json
{
  "weapon_name": {
    "file": "equipment/weapon_name.json",
    "folder": "equipment",
    "kind": "localized_map",
    "cases": [4],
    "table": "table_equipment"
  },
  "weapons_stat": {
    "file": "equipment/weapons_stat.json",
    "folder": "equipment",
    "kind": "stat_map",
    "cases": [32, 33],
    "table": "table_weapons",
    "merged": true
  },
  "attribute_negative": {
    "file": "attributes/attribute_negative.json",
    "folder": "attributes",
    "kind": "flat_list",
    "cases": [40],
    "table": ""
  }
}
```

#### `kind` 字段说明

| kind | 结构 | 典型用途 |
|------|------|----------|
| `localized_map` | `{id: {ru, en, zh, ...}}` | 名称/描述的多语言翻译 |
| `stat_map` | `{id: {attr: number}}` | 武器/消耗品/敌人数值属性 |
| `key_value_map` | `{key: scalar}` | 属性小数位数、合同索引等 |
| `indexed_list` | `["N/A", {lang...}, ...]` | `scr_tableWriteList` 输出，0 号是 N/A |
| `flat_list` | `["str", ...]` | 属性排序列表、武器槽位等 |
| `ref_list` | `["var_name", ...]` | 引用其他变量名的组合列表 |
| `raw_csv` | `[[header], [row], ...]` | 原始 2D 数组（武器/护甲/技能/敌人 CSV） |
| `structured_list` | `[{...}, ...]` | 刷怪 spawn 配置等 |

#### 文件夹自动派生规则

文件夹名不是手工维护的，而是从 IR 中自动推导：

1. **优先**: 变量的 `table_name` → `_TABLE_TO_FOLDER` 映射表查找
2. **回退**: 变量名前缀匹配（`weapon_*` → `equipment/`，`attribute_*` → `attributes/`）
3. **兜底**: `misc/`

#### 跨 case 合并

GML 中 `weapons_stat` 由 case 32 创建（`clear=true`）、case 33 追加（`clear=false`）。
脚本使用全局 store 按 case 顺序执行，`clear=false` 时自动 `update()` 到已有 dict，
最终 `weapons_stat.json` 包含完整的 785 个条目（426 武器 + 359 护甲）。

`_variable_index.json` 中 `"merged": true` 标记这类跨 case 变量。

### `extract_attr_sources.py`

从 GML 属性计算函数中提取每个属性的来源元数据。采用两层 flag 架构:

- **Layer 1: SurfaceCall** — GML 中直接检测到的函数调用模式 (纯机械 regex 提取)
- **Layer 2: SlotGroup** — 通过 RESOLVE_MAP 展开得到的装备槽位覆盖范围
- **has_efficiency** — 武器手读取是否经过 Mainhand/Offhand_Efficiency 调制
- **has_body_parts** — 是否有头/胸/手/腿部位分离计算
- **clamp 范围** — 从 `clamp(expr, min, max)` 调用中提取

数据源: 5 个 GML 文件 (scr_atr_calc, scr_atr_calc_combat, scr_inv_param, scr_Health_Threshold_calc, scr_consum_use)

```
python datamine/extract_attr_sources.py
```

## 添加新脚本的约定

1. **只做机械提取** — 读游戏文件 → 输出结构化数据，不含项目业务逻辑
2. **在文件头 docstring 中注明** 数据源文件 + 输出目标
3. **路径解析** 使用 `ROOT = Path(__file__).resolve().parent.parent`
4. **如果输出 data/*.py**，在该文件头标注 `# Auto-generated by datamine/xxx.py`
5. **更新本 README** 的管线表
