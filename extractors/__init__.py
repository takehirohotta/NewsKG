"""
NewsKG 抽出モジュール

エンティティ抽出とStatement抽出の機能を提供します。
"""

from .base import Entity, Statement, ExtractionResult
from .entity_extractor import EntityExtractor
from .statement_extractor import StatementExtractor

__all__ = [
    "Entity", "Statement", "ExtractionResult",
    "EntityExtractor", "StatementExtractor"
]
