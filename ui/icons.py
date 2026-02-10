# -*- coding: utf-8 -*-
"""Font Awesome 图标常量

手动维护的图标常量文件。

使用方法:
    from ui.icons import FA_CHECK, FA_GEAR
    imgui.text(f"{FA_CHECK} 保存成功")
    imgui.button(f"{FA_GEAR} 设置")

图标字体路径: fonts/icons/fa-solid-900.ttf

添加新图标:
    1. 访问 https://fontawesome.com/v6/icons?s=solid
    2. 找到图标，点击查看 Unicode 码点
    3. 在下方添加常量: FA_NAME = "\\u{码点}"
"""

# ==================== 图标常量 ====================

# 状态/反馈
FA_CHECK = "\uf00c"  # check
FA_XMARK = "\uf00d"  # xmark
FA_CIRCLE_CHECK = "\uf058"  # circle-check
FA_CIRCLE_XMARK = "\uf057"  # circle-xmark
FA_CIRCLE_INFO = "\uf05a"  # circle-info
FA_CIRCLE_EXCLAMATION = "\uf06a"  # circle-exclamation
FA_TRIANGLE_EXCLAMATION = "\uf071"  # triangle-exclamation

# 箭头/方向
FA_ARROW_UP = "\uf062"  # arrow-up
FA_ARROW_DOWN = "\uf063"  # arrow-down
FA_ARROW_LEFT = "\uf060"  # arrow-left
FA_ARROW_RIGHT = "\uf061"  # arrow-right
FA_CHEVRON_UP = "\uf077"  # chevron-up
FA_CHEVRON_DOWN = "\uf078"  # chevron-down
FA_CHEVRON_LEFT = "\uf053"  # chevron-left
FA_CHEVRON_RIGHT = "\uf054"  # chevron-right
FA_ANGLES_UP = "\uf102"  # angles-up
FA_ANGLES_DOWN = "\uf103"  # angles-down
FA_CARET_UP = "\uf0d8"  # caret-up
FA_CARET_DOWN = "\uf0d7"  # caret-down
FA_CARET_LEFT = "\uf0d9"  # caret-left
FA_CARET_RIGHT = "\uf0da"  # caret-right
FA_PLAY = "\uf04b"  # play
FA_PAUSE = "\uf04c"  # pause
FA_BACKWARD_STEP = "\uf048"  # backward-step
FA_FORWARD_STEP = "\uf051"  # forward-step

# 文件操作
FA_FILE = "\uf15b"  # file
FA_FILE_LINES = "\uf15c"  # file-lines
FA_FOLDER = "\uf07b"  # folder
FA_FOLDER_OPEN = "\uf07c"  # folder-open
FA_FLOPPY_DISK = "\uf0c7"  # floppy-disk
FA_DOWNLOAD = "\uf019"  # download
FA_UPLOAD = "\uf093"  # upload
FA_TRASH = "\uf1f8"  # trash
FA_TRASH_CAN = "\uf2ed"  # trash-can
FA_COPY = "\uf0c5"  # copy
FA_PASTE = "\uf0ea"  # paste

# 编辑
FA_PEN = "\uf304"  # pen
FA_PENCIL = "\uf303"  # pencil
FA_PLUS = "\u002b"  # plus
FA_MINUS = "\uf068"  # minus
FA_GEAR = "\uf013"  # gear
FA_SLIDERS = "\uf1de"  # sliders
FA_ROTATE = "\uf2f1"  # rotate
FA_ROTATE_LEFT = "\uf2ea"  # rotate-left
FA_MAGNIFYING_GLASS = "\uf002"  # magnifying-glass

# UI 元素
FA_BARS = "\uf0c9"  # bars
FA_ELLIPSIS = "\uf141"  # ellipsis
FA_ELLIPSIS_VERTICAL = "\uf142"  # ellipsis-vertical
FA_GRIP = "\uf58d"  # grip
FA_GRIP_VERTICAL = "\uf58e"  # grip-vertical
FA_SPINNER = "\uf110"  # spinner
FA_CIRCLE_NOTCH = "\uf1ce"  # circle-notch

# 窗口/布局
FA_WINDOW_MAXIMIZE = "\uf2d0"  # window-maximize
FA_WINDOW_MINIMIZE = "\uf2d1"  # window-minimize
FA_WINDOW_RESTORE = "\uf2d2"  # window-restore
FA_EXPAND = "\uf065"  # expand
FA_COMPRESS = "\uf066"  # compress
FA_UP_RIGHT_AND_DOWN_LEFT = "\uf424"  # up-right-and-down-left-from-center

# 游戏相关
FA_SWORD = "\uf66d"  # khanda
FA_SHIELD = "\uf132"  # shield
FA_SHIELD_HALVED = "\uf3ed"  # shield-halved
FA_HELMET_SAFETY = "\uf807"  # helmet-safety
FA_HAND_FIST = "\uf6de"  # hand-fist
FA_BOLT = "\uf0e7"  # bolt
FA_FIRE = "\uf06d"  # fire
FA_DROPLET = "\uf043"  # droplet
FA_HEART = "\uf004"  # heart
FA_SKULL = "\uf54c"  # skull
FA_COINS = "\uf51e"  # coins
FA_GEM = "\uf3a5"  # gem
FA_SCROLL = "\uf70e"  # scroll
FA_BOOK = "\uf02d"  # book
FA_WAND_MAGIC = "\ue2ca"  # wand-magic-sparkles
FA_FLASK = "\uf0c3"  # flask

# 其他常用
FA_EYE = "\uf06e"  # eye
FA_EYE_SLASH = "\uf070"  # eye-slash
FA_LOCK = "\uf023"  # lock
FA_UNLOCK = "\uf09c"  # unlock
FA_LINK = "\uf0c1"  # link
FA_UNLINK = "\uf127"  # link-slash
FA_IMAGE = "\uf03e"  # image
FA_PALETTE = "\uf53f"  # palette
FA_LAYER_GROUP = "\uf5fd"  # layer-group
FA_CLONE = "\uf24d"  # clone
FA_FILTER = "\uf0b0"  # filter
FA_SORT = "\uf0dc"  # sort
FA_LIST = "\uf03a"  # list
FA_TABLE = "\uf0ce"  # table
FA_QUESTION = "\u003f"  # question
FA_INFO = "\uf129"  # info
FA_LIGHTBULB = "\uf0eb"  # lightbulb
FA_STAR = "\uf005"  # star
FA_CERTIFICATE = "\uf0a3"  # certificate


# ==================== 辅助函数 ====================


def icon_text(icon: str, text: str) -> str:
    """组合图标和文字"""
    return f"{icon} {text}"


def icon_button_label(icon: str, text: str = "") -> str:
    """生成图标按钮标签"""
    return f"{icon} {text}".strip() if text else icon
