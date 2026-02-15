"""Extract all data loaded by o_textLoader (cases 0–40).

Two-layer architecture:

1. **GML Parser** — reads the raw GML source and auto-extracts all
   hardcoded data (variable names, table sources, column tags, attribute
   lists, ds_map_set constants, ds_list_add items, etc.) into a structured
   intermediate representation (IR).
2. **Logic Replicator** — implements the GML helper semantics in Python
   (``scr_tableWriteMap``, ``scr_array2d_to_map``, etc.) and executes them
   against the parsed IR so the output matches the game's runtime state.

When the game updates and adds new cases, column tags, or attribute
constants, re-running on the new GML produces correct output without
manual edits.

Preprocessing reference: ``scripts/extract_gml_tables.py``.
Output dir: ``datamine/output/textloader/``
"""

from __future__ import annotations

import ast
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATAMINE_DIR = Path(__file__).resolve().parent
CODE_ENTRIES = DATAMINE_DIR / "output" / "CodeEntries"
TEXTLOADER_GML = CODE_ENTRIES / "gml_Object_o_textLoader_Other_25.gml"
OUTPUT_DIR = DATAMINE_DIR / "output" / "textloader"

log = logging.getLogger("extract_textloader")

# ---------------------------------------------------------------------------
# Language mapping  (column indices in localization tables)
# ---------------------------------------------------------------------------

LANGUAGE_COLUMNS: dict[int, str] = {
    1: "ru", 2: "en", 3: "zh", 4: "de", 5: "es", 6: "fr",
    7: "it", 8: "pt", 9: "pl", 10: "tr", 11: "ko", 12: "ja", 13: "uk",
}

# ---------------------------------------------------------------------------
# Semantic name for each case (auto-derives from IR if absent)
# ---------------------------------------------------------------------------

CASE_SEMANTIC_NAMES: dict[int, str] = {
    0: "basics",
    1: "consumable_text",
    2: "effects_text",
    3: "skills_text",
    4: "equipment_text",
    5: "potions_text",
    6: "attributes_text",
    7: "prologue",
    8: "books_text",
    9: "potions_stats",
    10: "curses_text",
    11: "speech",
    12: "controls",
    13: "enemies_text",
    14: "contracts_text",
    15: "dungeons_text",
    16: "bosses_text",
    17: "npc_names",
    18: "action_log",
    19: "gui_text",
    20: "backers",
    21: "hints",
    22: "quests_text",
    23: "dialog_answers",
    24: "locations_text",
    25: "consumable_stats",
    26: "npc_lines",
    27: "character_stats",
    28: "caravan_text",
    29: "recipes",
    30: "enemy_balance",
    31: "skills_stats",
    32: "weapon_stats",
    33: "armor_stats",
    34: "ai_data",
    35: "contract_stats",
    36: "boss_types",
    37: "spawns",
    38: "drop_tables",
    39: "supply_demand",
    40: "attribute_meta",
}


# ═══════════════════════════════════════════════════════════════════════════
#  IR — Intermediate Representation (parsed from GML)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class WriteMapCall:
    """``scr_tableWriteMap(global.X, _array, "tag", clear?)``"""
    global_var: str
    tag: str
    clear: bool = True  # 4th arg; default true


@dataclass
class WriteListCall:
    """``scr_tableWriteList(global.X, _array, "tag")``"""
    global_var: str
    tag: str


@dataclass
class DsMapSetGroup:
    """A ``global.X`` map populated via repeated ``ds_map_set`` calls.

    ``entries`` is an ordered list of (key, value) pairs.
    """
    global_var: str
    entries: list[tuple[str, Any]] = field(default_factory=list)


@dataclass
class DsListAddGroup:
    """A ``global.X`` list populated via ``ds_list_add`` calls.

    ``items``: flat list of string literal values.
    ``ref_vars``: referenced variable names (for composite lists like
    ``attribute_order_all`` where items are ``global.attribute_order_*``).
    """
    global_var: str
    items: list[str] = field(default_factory=list)
    ref_vars: list[str] = field(default_factory=list)


@dataclass
class AddAtrPercentCall:
    """``scr_add_atr_percent("a", "b", ...)``"""
    args: list[str] = field(default_factory=list)


@dataclass
class TableLoadAssign:
    """``global.X = scr_tableLoad(table_Y)`` — raw array assignment."""
    global_var: str
    table_name: str


@dataclass
class FilterAndMapCall:
    """Pattern: ``scr_table_array_filter`` + ``scr_array2d_to_map``."""
    csv_var: str
    map_var: str
    table_name: str
    has_string_attr: bool = False


@dataclass
class Array2dToMapCall:
    """Standalone ``scr_array2d_to_map(csv, global.X)``."""
    csv_source: str
    map_var: str
    table_name: str
    has_string_attr: bool = False


@dataclass
class RecipeBlock:
    """Case 29's iterable recipe pattern."""
    entries: list[tuple[str, str, str, str]] = field(default_factory=list)
    # each: (table_name, data_var, categories_order_var, category_order_map_var)


@dataclass
class SpawnBlock:
    """Case 37: scr_dungeonSpawnsDoc / scr_surfaceSpawnsDoc."""
    dungeon_table: str = "table_dungeons_spawn"
    surface_table: str = "table_surface_spawn"


@dataclass
class CaseIR:
    """All parsed instructions for one textLoader case."""
    case_num: int
    table_name: str | None = None  # primary scr_tableLoad source
    write_maps: list[WriteMapCall] = field(default_factory=list)
    write_lists: list[WriteListCall] = field(default_factory=list)
    ds_map_sets: list[DsMapSetGroup] = field(default_factory=list)
    ds_list_adds: list[DsListAddGroup] = field(default_factory=list)
    atr_percent: AddAtrPercentCall | None = None
    raw_assigns: list[TableLoadAssign] = field(default_factory=list)
    filter_maps: list[FilterAndMapCall] = field(default_factory=list)
    array2d_maps: list[Array2dToMapCall] = field(default_factory=list)
    recipe_block: RecipeBlock | None = None
    spawn_block: SpawnBlock | None = None
    slot_lists: list[DsListAddGroup] = field(default_factory=list)
    # Special-case flags (auto-detected from GML patterns):
    has_voice_column: bool = False    # case 7
    has_hash_replace: bool = False    # case 26
    has_speech_real_convert: bool = False  # case 11
    has_backer_logic: bool = False    # case 20


# ═══════════════════════════════════════════════════════════════════════════
#  GML Parser — extract IR from raw GML text
# ═══════════════════════════════════════════════════════════════════════════

_RE_TABLE_WRITE_MAP = re.compile(
    r'scr_tableWriteMap\(global\.(\w+),\s*_array,\s*"([^"]+)"'
    r'(?:,\s*(false|true))?\)',
)
_RE_TABLE_WRITE_LIST = re.compile(
    r'scr_tableWriteList\(global\.(\w+),\s*_array,\s*"([^"]+)"\)',
)
_RE_TABLE_LOAD_TO_LOCAL = re.compile(
    r'(?:var\s+)?_\w*\s*=\s*scr_tableLoad\((\w+)\)',
)
_RE_TABLE_LOAD_TO_GLOBAL = re.compile(
    r'global\.(\w+)\s*=\s*scr_tableLoad\((\w+)\)',
)
_RE_DS_MAP_SET = re.compile(
    r'ds_map_set\(global\.(\w+),\s*"([^"]+)",\s*(.+?)\);',
)
_RE_DS_LIST_ADD = re.compile(
    r'ds_list_add\(global\.(\w+),\s*(.+?)\);',
)
_RE_ADD_ATR_PERCENT = re.compile(
    r'scr_add_atr_percent\((.+?)\);',
)
_RE_FILTER_ASSIGN = re.compile(
    r'(?:global\.)?(\w+)\s*=\s*scr_table_array_filter\(',
)
_RE_ARRAY2D_TO_MAP = re.compile(
    r'scr_array2d_to_map\((?:global\.)?(\w+),\s*global\.(\w+)'
    r'(?:,\s*global\.(\w+))?\)',
)
_RE_CASE_START = re.compile(r'^\s*case\s+(\d+):')
_RE_BREAK = re.compile(r'^\s*break;')
_RE_RECIPE_ITER_ARRAY = re.compile(
    r'_iterableArray\s*=\s*\[(.+?)\];',
)


def _parse_gml_value(raw: str) -> Any:
    """Parse a GML literal value to Python."""
    raw = raw.strip()
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    try:
        v = float(raw)
        return int(v) if v == int(v) else v
    except ValueError:
        return raw


def _split_gml_string_args(raw: str) -> list[str]:
    """Extract all double-quoted string literals from a GML arg list."""
    return [m.group(1) for m in re.finditer(r'"([^"]*)"', raw)]


def parse_textloader_gml(gml_path: Path | None = None) -> dict[int, CaseIR]:
    """Parse the textLoader GML into per-case IR.

    Returns ``{case_number: CaseIR, ...}``.
    """
    path = gml_path or TEXTLOADER_GML
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    cases: dict[int, CaseIR] = {}
    current_case: int | None = None
    case_lines: list[str] = []

    for line in lines:
        m = _RE_CASE_START.match(line)
        if m:
            if current_case is not None:
                cases[current_case] = _parse_case_block(
                    current_case, case_lines,
                )
            current_case = int(m.group(1))
            case_lines = []
        elif current_case is not None:
            if _RE_BREAK.match(line):
                cases[current_case] = _parse_case_block(
                    current_case, case_lines,
                )
                current_case = None
                case_lines = []
            else:
                case_lines.append(line)

    if current_case is not None:
        cases[current_case] = _parse_case_block(current_case, case_lines)

    return cases


def _parse_case_block(case_num: int, lines: list[str]) -> CaseIR:
    """Parse a single case block into :class:`CaseIR`."""
    ir = CaseIR(case_num=case_num)
    block = "\n".join(lines)

    # --- Primary table load into local var (_array) ---
    m = _RE_TABLE_LOAD_TO_LOCAL.search(block)
    if m:
        ir.table_name = m.group(1)

    # --- scr_tableWriteMap ---
    for m in _RE_TABLE_WRITE_MAP.finditer(block):
        clear = True
        if m.group(3) is not None:
            clear = m.group(3).lower() != "false"
        ir.write_maps.append(WriteMapCall(
            global_var=m.group(1), tag=m.group(2), clear=clear,
        ))

    # --- scr_tableWriteList ---
    for m in _RE_TABLE_WRITE_LIST.finditer(block):
        ir.write_lists.append(WriteListCall(
            global_var=m.group(1), tag=m.group(2),
        ))

    # --- global.X = scr_tableLoad(table_Y) ---
    for m in _RE_TABLE_LOAD_TO_GLOBAL.finditer(block):
        ir.raw_assigns.append(TableLoadAssign(
            global_var=m.group(1), table_name=m.group(2),
        ))

    # --- scr_table_array_filter + scr_array2d_to_map pattern ---
    filter_csv_vars: set[str] = set()
    for m_filt in _RE_FILTER_ASSIGN.finditer(block):
        csv_var = m_filt.group(1)
        filter_csv_vars.add(csv_var)
        # Find corresponding array2d_to_map
        for m_map in _RE_ARRAY2D_TO_MAP.finditer(block):
            source = m_map.group(1)
            if source == csv_var:
                # Determine table: check if csv_var was assigned from raw_assigns
                table = ""
                for ra in ir.raw_assigns:
                    if ra.global_var == csv_var:
                        table = ra.table_name
                        break
                if not table:
                    table = ir.table_name or ""
                ir.filter_maps.append(FilterAndMapCall(
                    csv_var=csv_var,
                    map_var=m_map.group(2),
                    table_name=table,
                    has_string_attr=m_map.group(3) is not None,
                ))
                break

    # --- standalone scr_array2d_to_map (not preceded by filter) ---
    seen_map_vars = {fm.map_var for fm in ir.filter_maps}
    for m_map in _RE_ARRAY2D_TO_MAP.finditer(block):
        map_var = m_map.group(2)
        if map_var in seen_map_vars:
            continue
        source_var = m_map.group(1)
        # Find the table source
        load_pat = re.compile(
            r'(?:var\s+)?' + re.escape(source_var)
            + r'\s*=\s*scr_tableLoad\((\w+)\)',
        )
        m_load = load_pat.search(block)
        table_name = m_load.group(1) if m_load else ""
        ir.array2d_maps.append(Array2dToMapCall(
            csv_source=source_var,
            map_var=map_var,
            table_name=table_name,
            has_string_attr=m_map.group(3) is not None,
        ))
        seen_map_vars.add(map_var)

    # --- ds_map_set groups ---
    map_set_groups: dict[str, DsMapSetGroup] = {}
    for m in _RE_DS_MAP_SET.finditer(block):
        var = m.group(1)
        key = m.group(2)
        val = _parse_gml_value(m.group(3))
        if var not in map_set_groups:
            map_set_groups[var] = DsMapSetGroup(global_var=var)
        map_set_groups[var].entries.append((key, val))
    ir.ds_map_sets = list(map_set_groups.values())

    # --- ds_list_add groups ---
    list_add_groups: dict[str, DsListAddGroup] = {}
    for m in _RE_DS_LIST_ADD.finditer(block):
        var = m.group(1)
        args_raw = m.group(2)
        if var not in list_add_groups:
            list_add_groups[var] = DsListAddGroup(global_var=var)
        grp = list_add_groups[var]

        string_args = _split_gml_string_args(args_raw)
        if string_args:
            grp.items.extend(string_args)
        else:
            refs = [
                ref.strip().replace("global.", "")
                for ref in args_raw.split(",")
                if "global." in ref
            ]
            if refs:
                grp.ref_vars.extend(refs)

    # Separate slot lists (e.g. weapons_slot, armor_slot)
    for var_name in list(list_add_groups.keys()):
        if var_name.endswith("_slot"):
            ir.slot_lists.append(list_add_groups.pop(var_name))
    ir.ds_list_adds = list(list_add_groups.values())

    # --- scr_add_atr_percent ---
    m = _RE_ADD_ATR_PERCENT.search(block)
    if m:
        ir.atr_percent = AddAtrPercentCall(
            args=_split_gml_string_args(m.group(1)),
        )

    # --- Recipe block (case 29) ---
    m = _RE_RECIPE_ITER_ARRAY.search(block)
    if m:
        items = [x.strip() for x in m.group(1).split(",")]
        recipe = RecipeBlock()
        for i in range(0, len(items), 4):
            if i + 3 < len(items):
                recipe.entries.append((
                    items[i],
                    items[i + 1].replace("global.", ""),
                    items[i + 2].replace("global.", ""),
                    items[i + 3].replace("global.", ""),
                ))
        ir.recipe_block = recipe

    # --- Spawn block (case 37) ---
    has_dungeon = bool(re.search(r'scr_dungeonSpawnsDoc\(\)', block))
    has_surface = bool(re.search(r'scr_surfaceSpawnsDoc\(\)', block))
    if has_dungeon or has_surface:
        ir.spawn_block = SpawnBlock()

    # --- Special-case flags (auto-detected) ---
    if re.search(r'_voiceIndex', block):
        ir.has_voice_column = True
    if re.search(r'string_replace_all.*"#".*"\\\\n"', block):
        ir.has_hash_replace = True
    if re.search(r'ds_map_set\(global\.speech_chance.*real\(_value\)', block):
        ir.has_speech_real_convert = True
    if re.search(r'scr_tableLoad\(table_backers\)', block):
        ir.has_backer_logic = True

    return ir


# ═══════════════════════════════════════════════════════════════════════════
#  Logic Replicators — implement GML helper semantics
# ═══════════════════════════════════════════════════════════════════════════

def _preprocess_table_file(table_name: str) -> list[str]:
    """Read ``table_*.gml`` → raw row-string list via ``ast.literal_eval``."""
    gml_path = CODE_ENTRIES / f"gml_GlobalScript_{table_name}.gml"
    if not gml_path.exists():
        raise FileNotFoundError(f"Table file not found: {gml_path}")
    with open(gml_path, encoding="utf-8") as f:
        lines = f.readlines()
    raw = lines[2].strip()
    if raw.startswith("return "):
        raw = raw[7:]
    if raw.endswith(";"):
        raw = raw[:-1]
    return ast.literal_eval(raw)


def table_load(table_name: str) -> list[list[str]]:
    """Replicate ``scr_tableLoad``: parse table file → 2D string array."""
    raw_rows = _preprocess_table_file(table_name)
    return [row.split(";") for row in raw_rows]


def _find_tag_range(
    array: list[list[str]], tag: str,
) -> tuple[int, int] | None:
    """Find row range bounded by *tag* / *tag_end* in column 1."""
    start = -1
    end_tag = tag + "_end"
    for i, row in enumerate(array):
        if len(row) > 1:
            if row[1] == tag and start == -1:
                start = i
            elif row[1] == end_tag and start != -1:
                return (start, i)
    return None


def table_write_map(
    array: list[list[str]], tag: str,
) -> dict[str, dict[str, str]]:
    """Replicate ``scr_tableWriteMap``: tag section → ``{key: {lang: val}}``."""
    rng = _find_tag_range(array, tag)
    if rng is None:
        return {}
    start, end = rng
    result: dict[str, dict[str, str]] = {}
    for i in range(start + 1, end):
        row = array[i]
        key = row[0]
        if not key:
            continue
        lang_dict: dict[str, str] = {}
        for col_idx, lang_code in LANGUAGE_COLUMNS.items():
            if col_idx < len(row):
                lang_dict[lang_code] = row[col_idx].replace("#", "\n")
        result[key] = lang_dict
    return result


def table_write_list(
    array: list[list[str]], tag: str,
) -> list[Any]:
    """Replicate ``scr_tableWriteList``: tag section → indexed list.

    Game prepends ``"N/A"`` at index 0.
    """
    rng = _find_tag_range(array, tag)
    if rng is None:
        return []
    start, end = rng
    result: list[Any] = ["N/A"]
    for i in range(start + 1, end):
        row = array[i]
        lang_dict: dict[str, str] = {}
        for col_idx, lang_code in LANGUAGE_COLUMNS.items():
            if col_idx < len(row):
                lang_dict[lang_code] = row[col_idx].replace("#", "\n")
        result.append(lang_dict)
    return result


def real_lite(value: str) -> float | int | str:
    """Replicate ``scr_real_lite``: try to parse as number, else 0."""
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            v = float(value)
            return int(v) if v == int(v) else v
        except ValueError:
            pass
    return 0


def table_array_filter(array: list[list[str]]) -> list[list[str]]:
    """Replicate ``scr_table_array_filter``.

    Remove rows where col[0] starts with ``#``;
    remove columns where header starts with ``#``.
    """
    if not array:
        return array
    headers = array[0]
    keep_cols = [j for j, h in enumerate(headers) if not h.startswith("#")]
    result: list[list[str]] = []
    for row in array:
        cell0 = row[0] if row else ""
        if cell0.startswith("#"):
            continue
        if not cell0 and result:
            continue
        result.append([row[j] if j < len(row) else "" for j in keep_cols])
    return result


def array2d_to_map(
    array: list[list[str]],
    string_attrs: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Replicate ``scr_array2d_to_map``.

    ``{row_key: {col_header: typed_value, ...}, ...}``
    """
    if not array or len(array) < 2:
        return {}
    headers = array[0]
    result: dict[str, dict[str, Any]] = {}
    for i in range(1, len(array)):
        row = array[i]
        id_name = row[0] if row else ""
        if not id_name:
            continue
        attr_map: dict[str, Any] = {}
        for j in range(1, len(headers)):
            col_name = headers[j]
            if not col_name:
                continue
            value: Any = row[j] if j < len(row) else ""
            if string_attrs is not None:
                if col_name not in string_attrs:
                    value = real_lite(value)
            attr_map[col_name] = value
        result[id_name] = attr_map
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  Special-case logic (auto-detected; code replicated)
# ═══════════════════════════════════════════════════════════════════════════

def _exec_voice_column(table_name: str) -> list[str]:
    """Case 7: extract ``dialog_voice`` from 3rd-from-last column."""
    array = table_load(table_name)
    if not array or not array[0]:
        return []
    voice_idx = len(array[0]) - 3
    return [
        row[voice_idx] if voice_idx < len(row) else ""
        for row in array[1:]
    ]


def _exec_backer_logic() -> list[str]:
    """Case 20: format backer name + nickname from ``table_backers``."""
    array = table_load("table_backers")
    backers: list[str] = []
    for i in range(1, len(array)):
        row = array[i]
        name = row[0] if len(row) > 0 else ""
        nickname = row[1] if len(row) > 1 else ""
        s = ""
        if name:
            s += name
        if nickname:
            s = f"{s} ({nickname})" if s else nickname
        if s:
            backers.append(s)
    return backers


def _exec_recipe_table(table_name: str) -> dict[str, Any]:
    """Case 29: process a recipe table (cook or craft)."""
    array = table_load(table_name)
    if not array:
        return {"data": {}, "categories_order": [], "category_map": {}}

    headers = array[0]
    data_map: dict[str, dict[str, str]] = {}
    categories_order: list[str] = []
    category_map: dict[str, list[str]] = {}

    for j in range(len(array)):
        row = array[j]
        id_name = row[0] if row else ""
        if not id_name or id_name == "NAME" or id_name.startswith("//"):
            continue
        cat = row[1] if len(row) > 1 else ""
        if cat not in categories_order:
            categories_order.append(cat)
        category_map.setdefault(cat, []).append(id_name)
        row_data: dict[str, str] = {}
        for k in range(1, len(headers)):
            row_data[headers[k]] = row[k] if k < len(row) else ""
        data_map[id_name] = row_data

    return {
        "data": data_map,
        "categories_order": categories_order,
        "category_map": category_map,
    }


def _exec_dungeon_spawns() -> list[dict[str, Any]]:
    """Case 37: replicate ``scr_dungeonSpawnsDoc``."""
    array = table_load("table_dungeons_spawn")
    result: list[dict[str, Any]] = []
    for i in range(1, len(array)):
        row = array[i]
        m: dict[str, Any] = {
            "id": row[0] if len(row) > 0 else "",
            "template": row[1] if len(row) > 1 else "",
        }
        for col_idx, key in [(2, "tierList"), (3, "factionList"), (4, "dungeonTypeList")]:
            raw = (row[col_idx] if col_idx < len(row) else "").replace(" ", "")
            m[key] = [s for s in raw.split(",") if s]
        enemies: list[list[str]] = []
        for j in range(5, min(11, len(row))):
            if row[j] and row[j].strip():
                el = [e.strip() for e in row[j].split(", ") if e.strip()]
                if el:
                    enemies.append(el)
        m["enemiesList"] = enemies
        result.append(m)
    return result


def _exec_surface_spawns() -> list[dict[str, Any]]:
    """Case 37: replicate ``scr_surfaceSpawnsDoc``."""
    array = table_load("table_surface_spawn")
    result: list[dict[str, Any]] = []
    for i in range(1, len(array)):
        row = array[i]
        m: dict[str, Any] = {
            "slot": row[0] if len(row) > 0 else "",
            "faction": row[3] if len(row) > 3 else "",
        }
        try:
            m["chance"] = float(row[4]) if len(row) > 4 and row[4] else 0.0
        except ValueError:
            m["chance"] = 0.0
        m["tierList"] = [
            t.strip() for t in (row[1] if len(row) > 1 else "").split(", ")
            if t.strip()
        ]
        m["biomesList"] = [
            b.strip() for b in (row[2] if len(row) > 2 else "").split(", ")
            if b.strip()
        ]
        enemies: list[list[str]] = []
        for j in range(5, min(11, len(row))):
            if row[j] and row[j].strip():
                el = [e.strip() for e in row[j].split(", ") if e.strip()]
                if el:
                    enemies.append(el)
        m["enemiesList"] = enemies
        result.append(m)
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  Case Executor — run parsed IR through replicators
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class _VarProvenance:
    """Tracks where a variable came from (for index generation)."""
    cases: list[int] = field(default_factory=list)
    table: str = ""  # primary table_name source
    merged: bool = False  # True if multiple cases wrote to this var


def execute_case(
    ir: CaseIR,
    store: dict[str, Any],
    provenance: dict[str, _VarProvenance],
) -> list[str]:
    """Execute a :class:`CaseIR`, writing results into *store*.

    Cross-case merging (``clear=false``) works correctly because *store*
    accumulates across sequential case execution.

    Returns list of variable names produced/updated by this case.
    """
    produced: list[str] = []

    def _put(var: str, value: Any, *, table: str = "") -> None:
        store[var] = value
        produced.append(var)
        if var not in provenance:
            provenance[var] = _VarProvenance(
                cases=[ir.case_num],
                table=table or ir.table_name or "",
            )
        else:
            prov = provenance[var]
            if ir.case_num not in prov.cases:
                prov.cases.append(ir.case_num)
                prov.merged = True

    def _merge_map(var: str, value: dict, *, table: str = "") -> None:
        """Put a dict, merging with existing if present (clear=false)."""
        if var in store and isinstance(store[var], dict):
            store[var].update(value)
            produced.append(var)
            prov = provenance.setdefault(
                var, _VarProvenance(table=table or ir.table_name or ""),
            )
            if ir.case_num not in prov.cases:
                prov.cases.append(ir.case_num)
            prov.merged = True
        else:
            _put(var, value, table=table)

    # --- Standard writeMap / writeList (the bulk of cases 0-28) ---
    if ir.table_name and (ir.write_maps or ir.write_lists):
        array = table_load(ir.table_name)

        # Group writeMaps by target var to handle intra-case merge (clear=false)
        map_groups: dict[str, list[WriteMapCall]] = {}
        for wm in ir.write_maps:
            map_groups.setdefault(wm.global_var, []).append(wm)

        for var_name, calls in map_groups.items():
            # Build the intra-case result first
            intra: dict[str, dict[str, str]] = {}
            for wm in calls:
                result = table_write_map(array, wm.tag)
                if wm.clear and not intra:
                    intra = result
                elif wm.clear:
                    intra = result
                else:
                    intra.update(result)

            # Now merge with global store (cross-case clear=false)
            any_clear = any(wm.clear for wm in calls)
            if any_clear:
                _put(var_name, intra)
            else:
                _merge_map(var_name, intra)

        for wl in ir.write_lists:
            _put(wl.global_var, table_write_list(array, wl.tag))

    # --- Case 7: voice column ---
    if ir.has_voice_column and ir.table_name:
        _put("dialog_voice", _exec_voice_column(ir.table_name))

    # --- Case 11: speech_chance real conversion ---
    if ir.has_speech_real_convert and "speech_chance" in store:
        orig = store["speech_chance"]
        converted: dict[str, Any] = {}
        for k, v in orig.items():
            if isinstance(v, dict):
                converted[k] = {lk: real_lite(lv) for lk, lv in v.items()}
            else:
                converted[k] = real_lite(v)
        store["speech_chance"] = converted

    # --- Case 20: backer formatting ---
    if ir.has_backer_logic:
        _put("backers", _exec_backer_logic())

    # --- Raw array assigns (global.X = scr_tableLoad(table_Y)) ---
    for ra in ir.raw_assigns:
        if ra.global_var not in store:
            loaded = table_load(ra.table_name)
            if ir.has_hash_replace:
                loaded = [
                    [cell.replace("#", "\n") for cell in row]
                    for row in loaded
                ]
            _put(ra.global_var, loaded, table=ra.table_name)

    # --- Filter + array2d_to_map ---
    for fm in ir.filter_maps:
        table = fm.table_name
        if not table:
            for ra in ir.raw_assigns:
                if ra.global_var == fm.csv_var:
                    table = ra.table_name
                    break
        if not table:
            table = ir.table_name or ""
        if table:
            array = table_load(table)
            filtered = table_array_filter(array)
            _put(fm.csv_var, filtered, table=table)
            # Cross-case merge for the map variable (e.g. weapons_stat)
            map_result = array2d_to_map(
                filtered,
                string_attrs=set() if fm.has_string_attr else None,
            )
            _merge_map(fm.map_var, map_result, table=table)

    # --- Standalone array2d_to_map ---
    for am in ir.array2d_maps:
        if am.table_name:
            csv = table_load(am.table_name)
            _put(am.map_var, array2d_to_map(
                csv,
                string_attrs=set() if am.has_string_attr else None,
            ), table=am.table_name)

    # --- ds_map_set groups ---
    for group in ir.ds_map_sets:
        if all(v is True for _, v in group.entries):
            _put(group.global_var, [k for k, _ in group.entries])
        else:
            _put(group.global_var, {k: v for k, v in group.entries})

    # --- scr_add_atr_percent → deduplicated list ---
    if ir.atr_percent:
        seen: set[str] = set()
        deduped: list[str] = []
        for a in ir.atr_percent.args:
            if a not in seen:
                deduped.append(a)
                seen.add(a)
        _put("attribute_percent", deduped)

    # --- ds_list_add groups ---
    for group in ir.ds_list_adds:
        if group.ref_vars:
            _put(group.global_var, group.ref_vars)
        elif group.items:
            _put(group.global_var, group.items)

    # --- Slot lists ---
    for group in ir.slot_lists:
        _put(group.global_var, group.items)

    # --- Recipe block (case 29) ---
    if ir.recipe_block:
        for table_name, data_var, cat_list_var, cat_map_var in ir.recipe_block.entries:
            result = _exec_recipe_table(table_name)
            _put(data_var, result["data"], table=table_name)
            _put(cat_list_var, result["categories_order"], table=table_name)
            _put(cat_map_var, result["category_map"], table=table_name)

    # --- Spawn block (case 37) ---
    if ir.spawn_block:
        _put("dungeon_spawn_list", _exec_dungeon_spawns(),
             table="table_dungeons_spawn")
        _put("surface_spawn_list", _exec_surface_spawns(),
             table="table_surface_spawn")

    return produced


# ═══════════════════════════════════════════════════════════════════════════
#  Folder derivation — auto-group variables into subdirectories
# ═══════════════════════════════════════════════════════════════════════════

# table_name → folder name  (auto-derived, override only for exceptions)
_TABLE_TO_FOLDER: dict[str, str] = {
    "table_text": "basics",
    "table_items": "consumables",
    "table_items_stats": "consumables",
    "table_effects": "effects",
    "table_skills": "skills",
    "table_skills_stats": "skills",
    "table_equipment": "equipment",
    "table_potions": "potions",
    "table_potions_stats": "potions",
    "table_attributes": "attributes",
    "table_prologue": "dialog",
    "table_books": "books",
    "table_curses": "effects",
    "table_speech": "dialog",
    "table_controls": "ui",
    "table_mobs": "enemies",
    "table_mobs_stats": "enemies",
    "table_contracts": "contracts",
    "table_contracts_stats": "contracts",
    "table_dungeons": "dungeons",
    "table_bosses": "enemies",
    "table_bosses_types": "enemies",
    "table_names": "npc",
    "table_log": "ui",
    "table_gui": "ui",
    "table_backers": "misc",
    "table_hints": "ui",
    "table_quests": "quests",
    "table_char_lines": "dialog",
    "table_locations": "locations",
    "table_lines": "npc",
    "table_stats": "character",
    "table_caravan": "caravan",
    "table_weapons": "equipment",
    "table_armor": "equipment",
    "table_ai": "enemies",
    "table_drops": "drops",
    "table_supply_demand": "economy",
    "table_dungeons_spawn": "spawns",
    "table_surface_spawn": "spawns",
}

# Variable-name prefix → folder  (fallback when table is unknown)
_VAR_PREFIX_TO_FOLDER: list[tuple[str, str]] = [
    ("attribute_order_", "attributes"),
    ("attribute_", "attributes"),
    ("weapon", "equipment"),
    ("armor", "equipment"),
    ("consum", "consumables"),
    ("skill", "skills"),
    ("enemy", "enemies"),
    ("recipe", "recipes"),
    ("caravan", "caravan"),
    ("dungeon_spawn", "spawns"),
    ("surface_spawn", "spawns"),
    ("contract", "contracts"),
    ("npc", "npc"),
    ("quest", "quests"),
    ("book", "books"),
    ("potion", "potions"),
    ("buff", "effects"),
    ("curse", "effects"),
    ("speech", "dialog"),
    ("dialog", "dialog"),
    ("prologue", "dialog"),
    ("location", "locations"),
    ("drop", "drops"),
    ("supply", "economy"),
    ("miniboss", "enemies"),
    ("actionsLog", "ui"),
    ("color_hovers", "ui"),
    ("hints", "ui"),
    ("keycode", "ui"),
]


def _derive_folder(var_name: str, prov: _VarProvenance) -> str:
    """Determine the output subdirectory for a variable.

    Priority: table_name mapping → variable prefix → "misc".
    """
    # 1. Try table_name
    if prov.table:
        folder = _TABLE_TO_FOLDER.get(prov.table)
        if folder:
            return folder
        # Auto-derive: strip "table_" prefix
        auto = prov.table.replace("table_", "")
        if auto:
            return auto

    # 2. Try variable-name prefix
    for prefix, folder in _VAR_PREFIX_TO_FOLDER:
        if var_name.startswith(prefix):
            return folder

    # 3. Fallback
    return "misc"


# ═══════════════════════════════════════════════════════════════════════════
#  Schema / kind inference
# ═══════════════════════════════════════════════════════════════════════════

def _infer_kind(value: Any) -> str:
    """Classify the semantic data kind for a variable value.

    Returns one of:
    - ``localized_map`` — ``{id: {lang: text}}``
    - ``stat_map``      — ``{id: {attr: number|str}}``
    - ``key_value_map`` — ``{key: scalar}``
    - ``indexed_list``  — list starting with ``"N/A"``
    - ``flat_list``     — plain list of strings
    - ``ref_list``      — list of variable references
    - ``raw_csv``       — 2D string array ``[[header], [row], ...]``
    - ``structured_list`` — list of dicts (spawn data, etc.)
    - ``scalar``        — single value
    """
    if isinstance(value, dict):
        if not value:
            return "key_value_map"
        sample = next(iter(value.values()))
        if isinstance(sample, dict):
            # Distinguish localization from stat
            inner_keys = set(sample.keys())
            lang_keys = set(LANGUAGE_COLUMNS.values())
            if inner_keys & lang_keys:
                return "localized_map"
            return "stat_map"
        return "key_value_map"
    if isinstance(value, list):
        if not value:
            return "flat_list"
        if isinstance(value[0], list):
            return "raw_csv"
        if isinstance(value[0], dict):
            return "structured_list"
        if len(value) > 0 and value[0] == "N/A":
            return "indexed_list"
        # Check if items look like variable references
        if all(isinstance(v, str) and v.startswith("attribute_order_")
               for v in value if isinstance(v, str)):
            return "ref_list"
        return "flat_list"
    return "scalar"


# ═══════════════════════════════════════════════════════════════════════════
#  Diagnostics
# ═══════════════════════════════════════════════════════════════════════════

def _case_description(ir: CaseIR) -> str:
    """Generate a human-readable description for a case."""
    parts: list[str] = []
    if ir.table_name:
        parts.append(ir.table_name.replace("table_", ""))
    n = len(ir.write_maps)
    if n:
        parts.append(f"{n} maps")
    n = len(ir.write_lists)
    if n:
        parts.append(f"{n} lists")
    if ir.raw_assigns:
        parts.append("raw_assign")
    if ir.filter_maps:
        parts.append("filter+map")
    if ir.array2d_maps:
        parts.append("array2d→map")
    if ir.ds_map_sets:
        total = sum(len(g.entries) for g in ir.ds_map_sets)
        parts.append(f"ds_map_set({total})")
    if ir.ds_list_adds:
        total = sum(len(g.items) + len(g.ref_vars) for g in ir.ds_list_adds)
        parts.append(f"ds_list_add({total})")
    if ir.atr_percent:
        parts.append(f"atr_percent({len(ir.atr_percent.args)})")
    if ir.recipe_block:
        parts.append("recipes")
    if ir.spawn_block:
        parts.append("spawns")
    flags = []
    if ir.has_voice_column:
        flags.append("voice")
    if ir.has_hash_replace:
        flags.append("hash")
    if ir.has_speech_real_convert:
        flags.append("real")
    if ir.has_backer_logic:
        flags.append("backer")
    if flags:
        parts.append("[" + ",".join(flags) + "]")
    return " | ".join(parts) if parts else "empty"


# ═══════════════════════════════════════════════════════════════════════════
#  Main interface
# ═══════════════════════════════════════════════════════════════════════════

def extract_all(
    *,
    cases: list[int] | None = None,
    output_dir: Path | None = None,
    gml_path: Path | None = None,
) -> dict[str, Any]:
    """Parse GML → IR → execute → per-variable JSON files.

    Output structure::

        textloader/
        ├── attributes/               # auto-derived from table/var
        │   ├── attribute.json
        │   ├── attribute_negative.json
        │   └── ...
        ├── equipment/
        │   ├── weapon_name.json
        │   ├── weapons_stat.json     # merged from case 32+33
        │   └── ...
        ├── consumables/
        │   ├── consum_name.json
        │   └── ...
        ├── ...
        ├── _variable_index.json      # variable → file + kind + provenance
        ├── _ir_summary.json          # parsed IR diagnostics
        └── _manifest.json            # extraction stats + file list

    Returns the global store: ``{"var_name": data, ...}``.
    """
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    # Phase 1: Parse
    log.info("Parsing textLoader GML...")
    all_ir = parse_textloader_gml(gml_path)
    log.info("  Parsed %d cases", len(all_ir))

    # Phase 2: Execute sequentially into a shared global store
    target_cases = cases if cases is not None else sorted(all_ir.keys())
    store: dict[str, Any] = {}
    provenance: dict[str, _VarProvenance] = {}
    stats = {"success": 0, "failed": 0, "skipped": 0}

    for case_num in target_cases:
        if case_num not in all_ir:
            log.warning("Case %d not found in GML, skipping", case_num)
            stats["skipped"] += 1
            continue

        ir = all_ir[case_num]
        desc = _case_description(ir)
        log.info("  Case %d (%s): %s", case_num,
                 CASE_SEMANTIC_NAMES.get(case_num, "?"), desc)

        try:
            produced = execute_case(ir, store, provenance)
            stats["success"] += 1
            log.info("    → %d variables", len(produced))
        except Exception:
            log.exception("    ✗ Case %d failed", case_num)
            stats["failed"] += 1

    # Phase 3: Write per-variable JSON files into auto-derived folders
    log.info("Writing %d variable files...", len(store))
    var_index: dict[str, Any] = {}
    folders_used: set[str] = set()

    for var_name, value in sorted(store.items()):
        prov = provenance.get(var_name, _VarProvenance())
        folder = _derive_folder(var_name, prov)
        folders_used.add(folder)

        folder_path = out / folder
        folder_path.mkdir(parents=True, exist_ok=True)

        json_path = folder_path / f"{var_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)

        kind = _infer_kind(value)
        rel_path = f"{folder}/{var_name}.json"
        entry: dict[str, Any] = {
            "file": rel_path,
            "folder": folder,
            "kind": kind,
            "cases": prov.cases,
            "table": prov.table or None,
        }
        if prov.merged:
            entry["merged"] = True
        var_index[var_name] = entry

    with open(out / "_variable_index.json", "w", encoding="utf-8") as f:
        json.dump(var_index, f, ensure_ascii=False, indent=2)
    log.info("  Variable index: %d entries", len(var_index))

    # Write IR summary (unchanged — still useful for GML traceability)
    ir_summary: dict[str, Any] = {}
    for case_num, ir in sorted(all_ir.items()):
        entry_ir: dict[str, Any] = {
            "semantic_name": CASE_SEMANTIC_NAMES.get(case_num, ""),
            "description": _case_description(ir),
        }
        if ir.table_name:
            entry_ir["table"] = ir.table_name
        if ir.write_maps:
            entry_ir["write_maps"] = [
                {"var": wm.global_var, "tag": wm.tag, "clear": wm.clear}
                for wm in ir.write_maps
            ]
        if ir.write_lists:
            entry_ir["write_lists"] = [
                {"var": wl.global_var, "tag": wl.tag}
                for wl in ir.write_lists
            ]
        if ir.raw_assigns:
            entry_ir["raw_assigns"] = [
                {"var": ra.global_var, "table": ra.table_name}
                for ra in ir.raw_assigns
            ]
        if ir.ds_map_sets:
            entry_ir["ds_map_sets"] = [
                {"var": g.global_var, "count": len(g.entries)}
                for g in ir.ds_map_sets
            ]
        if ir.ds_list_adds:
            entry_ir["ds_list_adds"] = [
                {"var": g.global_var, "items": len(g.items),
                 "refs": len(g.ref_vars)}
                for g in ir.ds_list_adds
            ]
        if ir.atr_percent:
            entry_ir["atr_percent_count"] = len(ir.atr_percent.args)
        if ir.filter_maps:
            entry_ir["filter_maps"] = [
                {"csv": fm.csv_var, "map": fm.map_var,
                 "table": fm.table_name}
                for fm in ir.filter_maps
            ]
        if ir.array2d_maps:
            entry_ir["array2d_maps"] = [
                {"map": am.map_var, "table": am.table_name}
                for am in ir.array2d_maps
            ]
        if ir.recipe_block:
            entry_ir["recipe_tables"] = [
                t[0] for t in ir.recipe_block.entries
            ]
        if ir.slot_lists:
            entry_ir["slot_lists"] = [
                {"var": sl.global_var, "items": sl.items}
                for sl in ir.slot_lists
            ]
        flags = []
        if ir.has_voice_column:
            flags.append("voice_column")
        if ir.has_hash_replace:
            flags.append("hash_replace")
        if ir.has_speech_real_convert:
            flags.append("speech_real_convert")
        if ir.has_backer_logic:
            flags.append("backer_logic")
        if ir.spawn_block:
            flags.append("spawn_block")
        if flags:
            entry_ir["special_flags"] = flags
        ir_summary[f"case_{case_num:02d}"] = entry_ir

    with open(out / "_ir_summary.json", "w", encoding="utf-8") as f:
        json.dump(ir_summary, f, ensure_ascii=False, indent=2)

    # Write manifest
    all_files = sorted(
        str(p.relative_to(out)).replace("\\", "/")
        for p in out.rglob("*.json")
        if not p.name.startswith("_")
    )
    manifest = {
        "total_cases_in_gml": len(all_ir),
        "extracted_cases": stats["success"],
        "failed_cases": stats["failed"],
        "skipped_cases": stats["skipped"],
        "total_variables": len(store),
        "folders": sorted(folders_used),
        "files": all_files,
    }
    with open(out / "_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    log.info(
        "Done: %d cases (%d ok, %d fail, %d skip) → %d variables in %d folders",
        len(target_cases), stats["success"], stats["failed"],
        stats["skipped"], len(store), len(folders_used),
    )
    return store


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract data from o_textLoader (auto-parsed from GML).",
    )
    parser.add_argument(
        "--cases", type=int, nargs="*", default=None,
        help="Case numbers to extract (default: all)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help=f"Output dir (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--gml", type=Path, default=None,
        help="Path to textLoader GML file",
    )
    parser.add_argument(
        "--ir-only", action="store_true",
        help="Only parse and print IR (no extraction)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.ir_only:
        all_ir = parse_textloader_gml(args.gml)
        for case_num, ir in sorted(all_ir.items()):
            desc = _case_description(ir)
            print(f"Case {case_num:2d}: {desc}")
            for wm in ir.write_maps:
                print(f"  WriteMap: {wm.global_var} ← \"{wm.tag}\""
                      f" (clear={wm.clear})")
            for wl in ir.write_lists:
                print(f"  WriteList: {wl.global_var} ← \"{wl.tag}\"")
            for g in ir.ds_map_sets:
                print(f"  DsMapSet: {g.global_var}"
                      f" ({len(g.entries)} entries)")
            for g in ir.ds_list_adds:
                n = len(g.items) + len(g.ref_vars)
                print(f"  DsListAdd: {g.global_var} ({n} items)")
            if ir.atr_percent:
                print(f"  AddAtrPercent:"
                      f" {len(ir.atr_percent.args)} attrs")
            for ra in ir.raw_assigns:
                print(f"  RawAssign: {ra.global_var}"
                      f" = tableLoad({ra.table_name})")
            for fm in ir.filter_maps:
                print(f"  FilterMap: {fm.csv_var} → {fm.map_var}"
                      f" from {fm.table_name}")
            for am in ir.array2d_maps:
                print(f"  Array2dMap: {am.csv_source} → {am.map_var}"
                      f" from {am.table_name}")
            if ir.recipe_block:
                for t in ir.recipe_block.entries:
                    print(f"  Recipe: {t[0]} → {t[1]}")
            for sl in ir.slot_lists:
                print(f"  SlotList: {sl.global_var} = {sl.items}")
        return

    t0 = time.perf_counter()
    extract_all(cases=args.cases, output_dir=args.output, gml_path=args.gml)
    elapsed = time.perf_counter() - t0
    log.info("Total time: %.1fs", elapsed)


if __name__ == "__main__":
    main()
