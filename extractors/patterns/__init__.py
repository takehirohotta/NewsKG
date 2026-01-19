"""
NewsKG 抽出パターンモジュール

選挙・災害・政策パターンの抽出ロジックを提供します。
"""

from .election import ElectionPatterns
from .disaster import DisasterPatterns
from .policy import PolicyPatterns

__all__ = ["ElectionPatterns", "DisasterPatterns", "PolicyPatterns"]
