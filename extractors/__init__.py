"""
抽出モジュール

エンティティ抽出、Statement抽出、LLMトリプル抽出を提供します。
"""

# 既存の抽出器（後方互換性のため維持）
from .base import Entity, Statement, ExtractionResult
from .entity_extractor import EntityExtractor
from .statement_extractor import StatementExtractor

# 新しいLLMベースの抽出器
from .llm_client import OpenRouterClient, get_client
from .llm_extractor import (
    Triple,
    ExtractionResult as TripleExtractionResult,
    LLMTripleExtractor,
    get_extractor
)
from .predicate_normalizer import (
    PredicateNormalizer,
    PredicateBatchNormalizer,
    get_normalizer
)
from .entity_resolver import (
    ResolvedEntity,
    EntityResolver,
    get_resolver
)

__all__ = [
    # 既存
    "Entity",
    "Statement",
    "ExtractionResult",
    "EntityExtractor",
    "StatementExtractor",
    # 新規 - LLMクライアント
    "OpenRouterClient",
    "get_client",
    # 新規 - トリプル抽出
    "Triple",
    "TripleExtractionResult",
    "LLMTripleExtractor",
    "get_extractor",
    # 新規 - 述語正規化
    "PredicateNormalizer",
    "PredicateBatchNormalizer",
    "get_normalizer",
    # 新規 - エンティティ解決
    "ResolvedEntity",
    "EntityResolver",
    "get_resolver",
]
