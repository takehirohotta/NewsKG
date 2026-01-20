"""
パイプラインモジュール

RSSデータからRDFへの変換パイプラインを提供します。
"""

# 既存のパイプライン（後方互換性のため維持）
from .processor import PipelineProcessor
from .rdf_generator import RDFGenerator
from .validator import SHACLValidator

# 新しいトリプルベースパイプライン
from .processor_v2 import TriplePipelineProcessor
from .rdf_generator_v2 import TripleBasedRDFGenerator

__all__ = [
    # 既存
    "PipelineProcessor",
    "RDFGenerator",
    "SHACLValidator",
    # 新規
    "TriplePipelineProcessor",
    "TripleBasedRDFGenerator",
]
