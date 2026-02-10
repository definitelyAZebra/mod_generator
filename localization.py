# -*- coding: utf-8 -*-
"""
本地化数据模型

独立模块，避免循环导入。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from constants import PRIMARY_LANGUAGE


@dataclass
class ItemLocalization:
    """物品本地化数据，格式: {"Chinese": {"name": "...", "description": "..."}, ...}"""

    languages: dict[str, dict[str, str]] = field(default_factory=lambda: {})

    def _ensure_lang(self, lang: str) -> dict[str, str]:
        return self.languages.setdefault(lang, {"name": "", "description": ""})

    def get_name(self, lang: str) -> str:
        return self.languages.get(lang, {}).get("name", "")

    def set_name(self, lang: str, value: str) -> None:
        self._ensure_lang(lang)["name"] = value

    def get_description(self, lang: str) -> str:
        return self.languages.get(lang, {}).get("description", "")

    def set_description(self, lang: str, value: str) -> None:
        self._ensure_lang(lang)["description"] = value

    def has_language(self, lang: str) -> bool:
        return lang in self.languages

    def get_display_name(self) -> str:
        """获取用于显示的名称（优先主语言，其次英语）"""
        return self.get_name(PRIMARY_LANGUAGE) or self.get_name("English") or "未命名"
