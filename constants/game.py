# -*- coding: utf-8 -*-
"""
游戏引擎/渲染/精灵/角色模型相关常量
"""

# ============== 渲染与动画常量 ==============

# 游戏实际帧率 (Stoneshard 运行在约 40fps)
GAME_FPS = 40

# 预览动画帧率 (游戏帧率的 1/4，手持贴图在游戏中默认以此速度播放)
PREVIEW_ANIMATION_FPS = GAME_FPS // 4  # = 10 fps

# ============== 精灵 Origin 常量 ==============
# 角色模型 Origin (游戏资源硬编码，所有 s_*_male/female 精灵均使用此值)
# 这是唯一真相来源 (Single Source of Truth)
# 详见: references/docs/doc_sprite_rendering_system.md
CHAR_MODEL_ORIGIN: tuple[int, int] = (22, 34)

# 兼容性别名 (旧代码可能使用这些名称)
GML_ANCHOR_X = CHAR_MODEL_ORIGIN[0]  # 游戏内默认原点 X
GML_ANCHOR_Y = CHAR_MODEL_ORIGIN[1]  # 游戏内默认原点 Y
CHAR_IMG_W = 48  # 人物贴图宽
CHAR_IMG_H = 40  # 人物贴图高

# 护甲穿戴贴图预览区域尺寸 (与人物贴图相同)
ARMOR_PREVIEW_WIDTH = CHAR_IMG_W  # 48
ARMOR_PREVIEW_HEIGHT = CHAR_IMG_H  # 40
CHAR_CENTER_X = CHAR_IMG_W // 2  # 人物中心 X (24)
CHAR_CENTER_Y = CHAR_IMG_H // 2  # 人物中心 Y (20)
VALID_AREA_SIZE = 64  # 有效显示区域边长 (64x64)

# 有效区域相对于人物贴图左上角的坐标
VALID_MIN_X = CHAR_CENTER_X - VALID_AREA_SIZE // 2  # -8
VALID_MAX_X = CHAR_CENTER_X + VALID_AREA_SIZE // 2  # 56
VALID_MIN_Y = CHAR_CENTER_Y - VALID_AREA_SIZE // 2  # -12
VALID_MAX_Y = CHAR_CENTER_Y + VALID_AREA_SIZE // 2  # 52

# 视口绘制时人物相对于64x64框左上角的偏移
VIEWPORT_CHAR_OFFSET_X = VALID_AREA_SIZE // 2 - CHAR_CENTER_X  # = 8
VIEWPORT_CHAR_OFFSET_Y = VALID_AREA_SIZE // 2 - CHAR_CENTER_Y  # = 12

# ============== 角色模型 ==============

# 角色模型 - 每个模型有3个姿势: 0=单手, 1=双手, 2=护甲专用
CHARACTER_MODELS = {
    "Human Male": ["s_human_male_0.png", "s_human_male_1.png", "s_human_male_2.png"],
    "Human Female": [
        "s_human_female_0.png",
        "s_human_female_1.png",
        "s_human_female_2.png",
    ],
    "Dwarf Male": ["s_dwarf_male_0.png", "s_dwarf_male_1.png", "s_dwarf_male_2.png"],
    "Dwarf Female": [
        "s_dwarf_female_0.png",
        "s_dwarf_female_1.png",
        "s_dwarf_female_2.png",
    ],
    "Elf Male": ["s_elf_male_0.png", "s_elf_male_1.png", "s_elf_male_2.png"],
    "Elf Female": [
        "s_elf_female_0.png",
        "s_elf_female_1.png",
        "s_elf_female_2.png",
    ],
}

CHARACTER_MODEL_LABELS = {
    "Human Male": "人类男性",
    "Human Female": "人类女性",
    "Dwarf Male": "矮人男性",
    "Dwarf Female": "矮人女性",
    "Elf Male": "精灵男性",
    "Elf Female": "精灵女性",
}

# 人种列表（用于多姿势装备编辑器中的模特选择）
CHARACTER_RACES = ["Human", "Dwarf", "Elf"]
CHARACTER_RACE_LABELS = {
    "Human": "人类",
    "Dwarf": "矮人",
    "Elf": "精灵",
}


# 根据人种和性别获取模型键名
def get_model_key(race: str, is_female: bool) -> str:
    """根据人种和性别获取角色模型键名"""
    gender = "Female" if is_female else "Male"
    return f"{race} {gender}"
