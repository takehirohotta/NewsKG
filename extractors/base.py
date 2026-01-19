"""
抽出エンジンの基底クラス・データ型

Entity, Statement, ExtractionResult などの共通データ構造を定義します。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class Entity:
    """抽出されたエンティティを表すデータクラス"""
    id: str  # 辞書のID (例: "takaichi_sanae")
    label: str  # 表示ラベル (例: "高市早苗")
    entity_type: str  # organization, person, place
    matched_text: str  # 実際にマッチしたテキスト (例: "高市首相")
    position: tuple  # テキスト内の位置 (start, end)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_uri(self, base_ns: str = "http://example.org/newskg#") -> str:
        """RDF URIを生成"""
        return f"{base_ns}{self.entity_type}_{self.id}"


@dataclass
class Statement:
    """抽出されたStatementを表すデータクラス"""
    id: str  # 一意識別子
    statement_type: str  # DissolutionAnnouncement, WeatherDisaster, etc.
    matched_text: str  # マッチしたテキスト
    confidence: float  # 信頼度 (0.0-1.0)
    extracted_data: Dict[str, Any]  # 抽出された詳細データ
    entities: List[Entity] = field(default_factory=list)  # 関連エンティティ
    source_article_id: Optional[str] = None  # 抽出元記事ID
    extraction_timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_uri(self, base_ns: str = "http://example.org/newskg#") -> str:
        """RDF URIを生成"""
        return f"{base_ns}statement_{self.id}"

    def get_primary_entity(self) -> Optional[Entity]:
        """主要エンティティを取得（存在する場合）"""
        if self.entities:
            return self.entities[0]
        return None


@dataclass
class ExtractionResult:
    """記事からの抽出結果全体を表すデータクラス"""
    article_id: str
    article_title: str
    article_url: str
    article_pub_date: str
    entities: List[Entity] = field(default_factory=list)
    statements: List[Statement] = field(default_factory=list)

    def get_entity_count(self) -> Dict[str, int]:
        """エンティティタイプ別のカウント"""
        counts = {"organization": 0, "person": 0, "place": 0}
        for entity in self.entities:
            if entity.entity_type in counts:
                counts[entity.entity_type] += 1
        return counts

    def get_statement_count(self) -> Dict[str, int]:
        """Statementタイプ別のカウント"""
        counts = {}
        for statement in self.statements:
            st_type = statement.statement_type
            counts[st_type] = counts.get(st_type, 0) + 1
        return counts

    def has_statements(self) -> bool:
        """Statementが抽出されたかどうか"""
        return len(self.statements) > 0

    def to_summary(self) -> Dict[str, Any]:
        """サマリー情報を生成"""
        return {
            "article_id": self.article_id,
            "article_title": self.article_title,
            "entity_counts": self.get_entity_count(),
            "statement_counts": self.get_statement_count(),
            "total_entities": len(self.entities),
            "total_statements": len(self.statements),
        }
