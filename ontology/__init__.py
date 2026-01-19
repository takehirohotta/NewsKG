"""
NewsKG オントロジーモジュール

Turtle形式のオントロジー定義とSHACL制約を提供します。
"""

from pathlib import Path

ONTOLOGY_DIR = Path(__file__).parent
NEWSKG_TTL = ONTOLOGY_DIR / "newskg.ttl"
SHAPES_TTL = ONTOLOGY_DIR / "shapes.ttl"

# 名前空間定義
NEWSKG_NS = "http://example.org/newskg#"
