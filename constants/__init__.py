# -*- coding: utf-8 -*-
"""
常量定义包

包含所有枚举、标签、属性描述、配置映射等静态数据。
通过 re-export 保持 `from constants import X` 兼容。
"""

# ruff: noqa: F401, F403 — wildcard re-exports for backward compatibility

from constants.items import *
from constants.attributes import *
from constants.game import *
from constants.hybrid import *
from constants.i18n import *
