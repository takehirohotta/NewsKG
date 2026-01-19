"""
Statement抽出モジュール

パターンマッチングでテキストからStatementを抽出します。
"""

import hashlib
from typing import List, Optional
from .base import Entity, Statement
from .entity_extractor import EntityExtractor
from .patterns import ElectionPatterns, DisasterPatterns, PolicyPatterns


class StatementExtractor:
    """Statementを抽出するクラス"""

    def __init__(self, entity_extractor: Optional[EntityExtractor] = None):
        """
        Args:
            entity_extractor: エンティティ抽出器
        """
        self.entity_extractor = entity_extractor or EntityExtractor()

        # パターン抽出器を初期化
        self.election_patterns = ElectionPatterns()
        self.disaster_patterns = DisasterPatterns()
        self.policy_patterns = PolicyPatterns()

    def extract(self, text: str, article_id: str = None) -> List[Statement]:
        """
        テキストからStatementを抽出

        Args:
            text: 検索対象テキスト
            article_id: 記事ID（オプション）

        Returns:
            抽出されたStatementのリスト
        """
        statements = []

        # 各パターンから抽出
        election_matches = self.election_patterns.extract(text)
        disaster_matches = self.disaster_patterns.extract(text)
        policy_matches = self.policy_patterns.extract(text)

        all_matches = election_matches + disaster_matches + policy_matches

        # テキスト全体からエンティティを抽出
        entities = self.entity_extractor.extract(text)

        for i, match in enumerate(all_matches):
            # ユニークIDを生成
            stmt_id = self._generate_statement_id(article_id, match.pattern_type, i)

            # マッチしたテキスト周辺のエンティティを関連付け（マッチ位置に基づく）
            related_entities = self._find_related_entities_by_span(
                match.start, match.end, entities
            )

            statement = Statement(
                id=stmt_id,
                statement_type=match.pattern_type,
                matched_text=match.matched_text,
                confidence=match.confidence,
                extracted_data=match.extracted_data,
                entities=related_entities,
                source_article_id=article_id
            )
            statements.append(statement)

        return statements

    def extract_from_article(self, article: dict) -> List[Statement]:
        """
        記事データからStatementを抽出

        Args:
            article: 記事辞書（id, title, content, summaryを含む）

        Returns:
            抽出されたStatementのリスト
        """
        article_id = article.get("id", "unknown")

        # タイトルと本文を結合
        text_parts = [
            article.get("title", ""),
            article.get("summary", ""),
            article.get("content", ""),
        ]
        combined_text = " ".join(filter(None, text_parts))

        return self.extract(combined_text, article_id)

    def _generate_statement_id(
        self, article_id: Optional[str], stmt_type: str, index: int
    ) -> str:
        """Statement用のユニークIDを生成"""
        base = f"{article_id or 'unknown'}_{stmt_type}_{index}"
        hash_suffix = hashlib.md5(base.encode()).hexdigest()[:8]
        return f"{stmt_type.lower()}_{hash_suffix}"

    def _find_related_entities_by_span(
        self, match_start: int, match_end: int, entities: List[Entity]
    ) -> List[Entity]:
        """
        マッチ範囲に基づいて関連エンティティを取得

        マッチしたテキストの前後50文字以内に位置するエンティティを関連付けます。
        """
        related = []

        search_start = max(0, match_start - 50)
        search_end = match_end + 50

        for entity in entities:
            entity_start, entity_end = entity.position
            if entity_start >= search_start and entity_end <= search_end:
                related.append(entity)

        return related
