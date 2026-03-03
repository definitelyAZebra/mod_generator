# -*- coding: utf-8 -*-
"""生成字体配置文件

自动测定字体 metrics 并生成 ui/font_config.py。
使用缓存机制避免重复测定未变化的字体。

使用方法:
    python scripts/generate_font_config.py

工作流程:
    1. 读取下方 FONT_PATHS 配置
    2. 检查字体文件 mtime，对比缓存
    3. 对变化的字体重新测定 metrics
    4. 计算 baseline offset 和 icon scale
    5. 生成 ui/font_config.py

依赖:
    pip install fonttools
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import random
import re
import sys
import tokenize
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    from fontTools.ttLib import TTFont
    from fontTools.pens.boundsPen import BoundsPen
except ImportError:
    print("错误: 需要安装 fonttools")
    print("运行: pip install fonttools")
    sys.exit(1)


# ==================== 字体路径配置 ====================
# 修改这里来切换字体，然后运行此脚本重新生成配置

FONT_PATHS = {
    # 英文字体 (主字体，决定 baseline)
    "english": "fonts/english/Handlee-Regular.ttf",

    # 中文字体 (合并到英文字体)
    "chinese": "fonts/chinese/HanyiSentyYongleEncyclopedia-2020.ttf",

    # 图标字体 (FA Solid 完整字体)
    "icon": "fonts/icons/fa-solid-900.ttf",
}

# ==================== 图标缩放 (设计参数) ====================
# 图标相对于文字的视觉大小，1.0 = 原始大小
# 调整此值后，glyph_offset 会自动重新计算
ICON_SCALE = 1.0


# ==================== 输出配置 ====================

OUTPUT_FILE = "ui/font_config.py"
CACHE_FILE = ".font_metrics_cache.json"
BASE_FONT_SIZE = 16.0  # 测定时使用的基准字号


# ==================== 样本集策略 ====================

# 中文样本: 从项目真实 UI 文案中提取高频字符 + core/stress 兜底
CHINESE_TOP_N = 400
CHINESE_CORE_WORDS = [
    "项目", "打开", "保存", "生成", "目录", "文件", "模组", "成功", "失败", "错误", "提示", "警告",
    "武器", "护甲", "道具", "标签", "分类", "品质", "等级", "价格", "重量", "材质", "删除", "复制",
]
CHINESE_STRESS_CHARS = "，。！？；：、“”‘’（）《》【】·—"

# 图标样本: 从项目真实 FA_* 使用中提取高频图标
ICON_TOP_N = 32
MAX_WEIGHT_REPEAT = 5


# ==================== 缓存管理 ====================


def get_file_hash(path: str) -> str:
    """计算文件 MD5 hash (前 64KB)"""
    try:
        with open(path, "rb") as f:
            # 只读取前 64KB，足够区分不同字体
            return hashlib.md5(f.read(65536)).hexdigest()
    except Exception:
        return ""


def load_cache() -> dict:
    """加载缓存文件"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_cache(cache: dict) -> None:
    """保存缓存文件"""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def is_cache_valid(path: str, cache: dict) -> bool:
    """检查缓存是否有效"""
    if path not in cache:
        return False

    entry = cache[path]

    # 检查 mtime
    try:
        current_mtime = os.path.getmtime(path)
        if abs(current_mtime - entry.get("mtime", 0)) > 1:
            return False
    except Exception:
        return False

    # 检查 hash (可选，更可靠)
    if "hash" in entry:
        current_hash = get_file_hash(path)
        if current_hash != entry["hash"]:
            return False

    return True


# ==================== 字体度量测定 ====================


def get_font_metrics(font_path: str) -> dict | None:
    """读取字体的关键 metrics"""
    if not os.path.exists(font_path):
        return None

    try:
        font = TTFont(font_path)
    except Exception as e:
        print(f"  ❌ 无法读取字体: {e}")
        return None

    head = font["head"]
    upm = head.unitsPerEm
    scale = BASE_FONT_SIZE / upm

    metrics = {
        "units_per_em": upm,
    }

    # hhea 表 (ImGui 使用)
    if "hhea" in font:
        hhea = font["hhea"]
        metrics["hhea_ascent"] = round(hhea.ascent * scale, 2)
        metrics["hhea_descent"] = round(hhea.descent * scale, 2)
        metrics["hhea_line_gap"] = round(hhea.lineGap * scale, 2)

    # OS/2 表 (补充)
    if "OS/2" in font:
        os2 = font["OS/2"]
        metrics["typo_ascent"] = round(os2.sTypoAscender * scale, 2)
        metrics["typo_descent"] = round(os2.sTypoDescender * scale, 2)
        metrics["cap_height"] = round(getattr(os2, "sCapHeight", 0) * scale, 2)
        metrics["x_height"] = round(getattr(os2, "sxHeight", 0) * scale, 2)

    return metrics


def sample_glyph_heights(font_path: str, codepoints: list[int], sample_count: int = 0) -> dict | None:
    """采样字形的实际渲染高度

    Args:
        font_path: 字体文件路径
        codepoints: 要采样的码点列表
        sample_count: 采样数量，0 = 全量采样
    """
    if not os.path.exists(font_path):
        return None

    try:
        font = TTFont(font_path)
    except Exception:
        return None

    cmap = font.getBestCmap()
    if not cmap:
        return None

    upm = font["head"].unitsPerEm
    scale = BASE_FONT_SIZE / upm

    # 筛选存在的码点
    valid_codepoints = [cp for cp in codepoints if cp in cmap]
    if not valid_codepoints:
        return None

    # 随机采样 (如果指定了数量且小于总数)
    if sample_count > 0 and len(valid_codepoints) > sample_count:
        valid_codepoints = random.sample(valid_codepoints, sample_count)

    heights = []
    centers = []

    for cp in valid_codepoints:
        glyph_name = cmap[cp]
        try:
            pen = BoundsPen(font.getGlyphSet())
            font.getGlyphSet()[glyph_name].draw(pen)
            if pen.bounds:
                x_min, y_min, x_max, y_max = pen.bounds
                height = (y_max - y_min) * scale
                center = ((y_min + y_max) / 2) * scale
                heights.append(height)
                centers.append(center)
        except Exception:
            pass

    if not heights:
        return None

    return {
        "sample_count": len(heights),
        "avg_height": round(sum(heights) / len(heights), 2),
        "avg_center": round(sum(centers) / len(centers), 2),
        "max_height": round(max(heights), 2),
    }


def get_gb2312_codepoints() -> list[int]:
    """获取 GB2312 字符集码点"""
    codepoints = []
    for area in range(16, 88):
        for position in range(1, 95):
            try:
                code = bytes([area + 0xA0, position + 0xA0])
                char = code.decode("gb2312")
                codepoints.append(ord(char))
            except Exception:
                continue
    return codepoints


def get_icon_codepoints() -> list[int]:
    """获取图标样本码点

    优先使用项目中真实出现的 FA_* 常量（按频次加权）。
    若提取失败，回退到 Font Awesome PUA 全范围。
    """
    icon_map = load_icon_constant_map()
    usage = collect_project_icon_usage()

    if icon_map and usage:
        weighted_codepoints: list[int] = []
        for icon_name, count in usage.most_common(ICON_TOP_N):
            cp = icon_map.get(icon_name)
            if cp is None:
                continue
            repeat = min(MAX_WEIGHT_REPEAT, 1 + count // 2)
            weighted_codepoints.extend([cp] * repeat)

        if weighted_codepoints:
            return weighted_codepoints

    return list(range(0xE000, 0xF8FF + 1))


def get_english_codepoints() -> list[int]:
    """获取英文对齐参照字符码点

    使用大小写字母、数字和常见 UI 符号，覆盖更真实的混排场景。
    """
    codepoints = []

    # 大写字母 A-Z
    codepoints.extend(range(ord('A'), ord('Z') + 1))

    # 小写字母 a-z
    codepoints.extend(range(ord('a'), ord('z') + 1))

    # 数字 0-9
    codepoints.extend(range(ord('0'), ord('9') + 1))

    # 常见 UI 符号
    for ch in "_%+-/.:()[]":
        codepoints.append(ord(ch))

    return codepoints


def iter_project_python_files() -> list[Path]:
    """枚举用于样本提取的项目 Python 文件"""
    files: list[Path] = []

    ui_dir = Path("ui")
    if ui_dir.exists():
        files.extend(sorted(ui_dir.rglob("*.py")))

    root_entry = Path("mod_generator.py")
    if root_entry.exists():
        files.append(root_entry)

    return files


def extract_python_string_literals(file_path: Path) -> list[str]:
    """提取 Python 文件中的字符串字面量（解码后）"""
    literals: list[str] = []

    try:
        with tokenize.open(file_path) as f:
            tokens = tokenize.generate_tokens(f.readline)
            for token in tokens:
                if token.type != tokenize.STRING:
                    continue
                try:
                    value = ast.literal_eval(token.string)
                except Exception:
                    continue
                if isinstance(value, str) and value:
                    literals.append(value)
    except Exception:
        return []

    return literals


def collect_project_chinese_char_freq() -> Counter[str]:
    """统计项目 UI 文案中的中文字符频次"""
    freq: Counter[str] = Counter()

    for file_path in iter_project_python_files():
        for text in extract_python_string_literals(file_path):
            for ch in text:
                if "\u4e00" <= ch <= "\u9fff":
                    freq[ch] += 1

    return freq


def get_chinese_codepoints() -> list[int]:
    """获取中文样本码点（频次加权）

    策略:
    1. 项目真实文案高频字（主权重）
    2. 核心领域词（稳定兜底）
    3. 压力标点（防回归）
    """
    freq = collect_project_chinese_char_freq()
    weighted: list[int] = []

    for ch, count in freq.most_common(CHINESE_TOP_N):
        repeat = min(MAX_WEIGHT_REPEAT, 1 + count // 5)
        weighted.extend([ord(ch)] * repeat)

    for word in CHINESE_CORE_WORDS:
        for ch in word:
            if "\u4e00" <= ch <= "\u9fff":
                weighted.extend([ord(ch)] * 3)

    for ch in CHINESE_STRESS_CHARS:
        weighted.append(ord(ch))

    if weighted:
        return weighted

    # 极端情况下提取失败，回退到 GB2312 全量
    return get_gb2312_codepoints()


def load_icon_constant_map() -> dict[str, int]:
    """从 ui/icons.py 读取 FA_* 常量映射 (常量名 -> 码点)"""
    icons_file = Path("ui/icons.py")
    if not icons_file.exists():
        return {}

    try:
        source = icons_file.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return {}

    icon_map: dict[str, int] = {}

    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue

        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if not target.id.startswith("FA_"):
            continue

        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and node.value.value:
            icon_map[target.id] = ord(node.value.value[0])

    return icon_map


def collect_project_icon_usage() -> Counter[str]:
    """统计项目中 FA_* 常量的使用频次"""
    pattern = re.compile(r"\bFA_[A-Z0-9_]+\b")
    usage: Counter[str] = Counter()

    for file_path in iter_project_python_files():
        try:
            source = file_path.read_text(encoding="utf-8")
        except Exception:
            continue
        usage.update(pattern.findall(source))

    return usage


# ==================== 主流程 ====================


def measure_font(
    font_key: str,
    font_path: str,
    cache: dict,
    sample_codepoints: list[int] | None = None,
) -> dict | None:
    """测定字体 metrics（使用缓存）"""
    if not font_path or not os.path.exists(font_path):
        print(f"  ⚠️ {font_key}: 文件不存在 - {font_path}")
        return None

    # 检查缓存
    if is_cache_valid(font_path, cache):
        print(f"  ✓ {font_key}: 使用缓存 - {os.path.basename(font_path)}")
        return cache[font_path]["metrics"]

    # 重新测定
    print(f"  → {font_key}: 测定中 - {os.path.basename(font_path)}")

    metrics = get_font_metrics(font_path)
    if not metrics:
        return None

    # 采样字形高度
    if sample_codepoints:
        glyph_stats = sample_glyph_heights(font_path, sample_codepoints)
        if glyph_stats:
            metrics["glyph_stats"] = glyph_stats

    # 更新缓存
    cache[font_path] = {
        "mtime": os.path.getmtime(font_path),
        "hash": get_file_hash(font_path),
        "metrics": metrics,
    }

    return metrics


def calculate_offsets(english_metrics: dict, chinese_metrics: dict, icon_metrics: dict) -> dict:
    """计算合并字体需要的 offset

    基于字形视觉中心计算。

    原理：
    - glyph_offset_y 正值 = 字形向下移动
    - 如果字形视觉上偏上，需要正值向下移动

    字形中心 (avg_center) 是相对于 baseline 的 Y 坐标（字体坐标系，向上为正）
    但 ImGui 渲染时 Y 轴向下，所以需要反转
    """
    result = {
        "chinese_offset_y": 0.0,
        "icon_offset_y": 0.0,
    }

    # 获取英文字形的视觉中心（大写+数字）
    en_center = 0.0
    if "glyph_stats" in english_metrics:
        en_center = english_metrics["glyph_stats"].get("avg_center", 0)

    # 中文 offset: 让中文字形中心对齐英文字形中心
    # en_center > cn_center 说明中文在屏幕上偏上，需要正值向下移动
    if chinese_metrics and "glyph_stats" in chinese_metrics:
        cn_center = chinese_metrics["glyph_stats"].get("avg_center", 0)
        result["chinese_offset_y"] = round(en_center - cn_center, 1)

    # 图标 offset
    if icon_metrics and "glyph_stats" in icon_metrics:
        icon_center = icon_metrics["glyph_stats"].get("avg_center", 0)
        scaled_icon_center = icon_center * ICON_SCALE
        result["icon_offset_y"] = round(en_center - scaled_icon_center, 1)

    return result


def generate_python_file(
    font_paths: dict[str, str],
    english_metrics: dict,
    chinese_metrics: dict | None,
    icon_metrics: dict | None,
    offsets: dict,
) -> str:
    """生成 Python 配置文件内容"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# -*- coding: utf-8 -*-",
        '"""字体配置 (自动生成)',
        "",
        "由 scripts/generate_font_config.py 自动生成，请勿手动编辑。",
        f"生成时间: {timestamp}",
        "",
        "修改字体配置请编辑 scripts/generate_font_config.py 中的 FONT_PATHS 和 ICON_SCALE。",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "# ==================== 字体路径 ====================",
        "",
        f'ENGLISH_FONT = "{font_paths["english"]}"',
        f'CHINESE_FONT = "{font_paths["chinese"]}"',
        f'ICON_FONT = "{font_paths["icon"]}"',
        "",
        "# ==================== 基准字号 ====================",
        "",
        f"BASE_FONT_SIZE = {BASE_FONT_SIZE}  # 下方所有度量值基于此字号",
        "",
        "# ==================== 主字体 Metrics ====================",
        f"# {os.path.basename(font_paths['english'])}",
        "",
        f"ENGLISH_HHEA_ASCENT = {english_metrics.get('hhea_ascent', 0)}",
        f"ENGLISH_HHEA_DESCENT = {english_metrics.get('hhea_descent', 0)}",
        "",
        "# ==================== Baseline 偏移补偿 ====================",
        "# ImGui 合并字体时，后续字体沿用主字体的 metrics",
        "# 如果 ascent 不同，会产生垂直偏移，需要用 glyph_offset 补偿",
        "#",
        "# 公式: actual_offset = BASE_OFFSET * (font_size / BASE_FONT_SIZE)",
        "",
    ]

    # 中文偏移
    if chinese_metrics:
        cn_name = os.path.basename(font_paths["chinese"])
        lines.extend([
            f"# 中文字体: {cn_name}",
            f"# hhea_ascent = {chinese_metrics.get('hhea_ascent', 0)} (主字体 = {english_metrics.get('hhea_ascent', 0)})",
            f"CHINESE_GLYPH_OFFSET_Y = {offsets['chinese_offset_y']}",
            "",
        ])
    else:
        lines.extend([
            "# 中文字体: 未配置",
            "CHINESE_GLYPH_OFFSET_Y = 0.0",
            "",
        ])

    # 图标偏移和缩放
    if icon_metrics:
        icon_name = os.path.basename(font_paths["icon"])
        scaled_ascent = icon_metrics.get('hhea_ascent', 0) * ICON_SCALE
        lines.extend([
            f"# 图标字体: {icon_name}",
            f"# hhea_ascent = {icon_metrics.get('hhea_ascent', 0)} × ICON_SCALE = {scaled_ascent:.2f} (主字体 = {english_metrics.get('hhea_ascent', 0)})",
            f"ICON_GLYPH_OFFSET_Y = {offsets['icon_offset_y']}",
            "",
            "# 图标缩放 (设计参数，从 codegen 复制)",
            f"ICON_SCALE = {ICON_SCALE}",
        ])
    else:
        lines.extend([
            "# 图标字体: 未配置",
            "ICON_GLYPH_OFFSET_Y = 0.0",
            "ICON_SCALE = 1.0",
        ])

    return "\n".join(lines) + "\n"


def main():
    print("=" * 60)
    print("📝 生成字体配置")
    print("=" * 60)

    # 检查字体文件
    print("\n字体路径:")
    all_exist = True
    for key, path in FONT_PATHS.items():
        exists = os.path.exists(path)
        status = "✓" if exists else "✗"
        print(f"  {status} {key}: {path}")
        if not exists:
            all_exist = False

    if not all_exist:
        print("\n❌ 部分字体文件不存在，请检查路径！")
        sys.exit(1)

    print(f"\n图标缩放: ICON_SCALE = {ICON_SCALE}")

    # 加载缓存
    cache = load_cache()
    print(f"\n缓存条目: {len(cache)}")

    # 测定各字体 (包括字形中心采样)
    print("\n测定 metrics:")

    # 样本集 (方法论核心): 优先项目真实文案/图标，减少手工拍脑袋
    english_samples = get_english_codepoints()
    chinese_samples = get_chinese_codepoints()
    icon_samples = get_icon_codepoints()

    print("\n样本集:")
    print(f"  english: {len(english_samples)} 码点")
    print(f"  chinese: {len(chinese_samples)} 码点 (去重后 {len(set(chinese_samples))})")
    print(f"  icon: {len(icon_samples)} 码点 (去重后 {len(set(icon_samples))})")

    english_metrics = measure_font(
        "english",
        FONT_PATHS["english"],
        cache,
        sample_codepoints=english_samples,
    )
    chinese_metrics = measure_font(
        "chinese",
        FONT_PATHS["chinese"],
        cache,
        sample_codepoints=chinese_samples,
    )
    icon_metrics = measure_font(
        "icon",
        FONT_PATHS["icon"],
        cache,
        sample_codepoints=icon_samples,
    )

    # 保存缓存
    save_cache(cache)

    # 打印详细的字形统计
    print("\n字形统计:")
    for name, metrics in [("english", english_metrics), ("chinese", chinese_metrics), ("icon", icon_metrics)]:
        if metrics and "glyph_stats" in metrics:
            stats = metrics["glyph_stats"]
            print(f"  {name}:")
            print(f"    采样数: {stats['sample_count']}")
            print(f"    平均高度: {stats['avg_height']}px")
            print(f"    平均中心: {stats['avg_center']}px (相对baseline)")

    # 计算偏移
    offsets = calculate_offsets(english_metrics, chinese_metrics or {}, icon_metrics or {})

    print("\n计算结果:")
    print(f"  中文 glyph_offset_y = {offsets['chinese_offset_y']}px")
    print(f"  图标 glyph_offset_y = {offsets['icon_offset_y']}px (基于 ICON_SCALE={ICON_SCALE})")

    # 生成 Python 文件
    content = generate_python_file(
        FONT_PATHS,
        english_metrics,
        chinese_metrics,
        icon_metrics,
        offsets,
    )

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n✅ 已生成: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
