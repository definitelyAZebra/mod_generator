# -*- coding: utf-8 -*-
"""
包级基础设施 — 无其他 constants 子模块依赖，可安全被任意子模块导入。
"""

import sys
from pathlib import Path

# PyInstaller --onefile 解压到临时目录，数据文件在 exe 旁边
PROJECT_ROOT = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent.parent
)
