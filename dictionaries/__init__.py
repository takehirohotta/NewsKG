"""
NewsKG 辞書モジュール

エンティティ辞書の読み込みと検索機能を提供します。
"""

from .loader import DictionaryLoader, DictionaryEntry, get_loader

__all__ = ["DictionaryLoader", "DictionaryEntry", "get_loader"]
