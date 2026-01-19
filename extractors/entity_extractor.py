"""
エンティティ抽出モジュール

辞書ベースでテキストからエンティティを抽出します。
"""

from typing import List, Optional
from .base import Entity
from dictionaries import DictionaryLoader, get_loader


class EntityExtractor:
    """辞書ベースのエンティティ抽出クラス"""

    def __init__(self, loader: Optional[DictionaryLoader] = None):
        """
        Args:
            loader: 辞書ローダー。指定しない場合はシングルトンを使用
        """
        self.loader = loader or get_loader()

    def extract(self, text: str) -> List[Entity]:
        """
        テキストからエンティティを抽出

        Args:
            text: 検索対象テキスト

        Returns:
            抽出されたEntityのリスト
        """
        entities = []

        # 辞書ローダーを使ってエンティティを検索
        matches = self.loader.find_entities_in_text(text)

        for start, end, entry in matches:
            entity = Entity(
                id=entry.id,
                label=entry.label,
                entity_type=entry.entity_type,
                matched_text=text[start:end],
                position=(start, end),
                extra=entry.extra
            )
            entities.append(entity)

        return entities

    def extract_from_article(self, article: dict) -> List[Entity]:
        """
        記事データからエンティティを抽出

        Args:
            article: 記事辞書（title, content, summaryを含む）

        Returns:
            抽出されたEntityのリスト（重複排除済み）
        """
        # タイトルと本文を結合して検索
        text_parts = [
            article.get("title", ""),
            article.get("summary", ""),
            article.get("content", ""),
        ]
        combined_text = " ".join(filter(None, text_parts))

        entities = self.extract(combined_text)

        # IDで重複排除
        seen_ids = set()
        unique_entities = []
        for entity in entities:
            if entity.id not in seen_ids:
                seen_ids.add(entity.id)
                unique_entities.append(entity)

        return unique_entities

    def find_entity_by_text(self, text: str) -> Optional[Entity]:
        """
        テキストに完全一致するエンティティを検索

        Args:
            text: 検索するテキスト

        Returns:
            マッチしたEntity、見つからない場合はNone
        """
        entry = self.loader.find_entity(text)
        if entry:
            return Entity(
                id=entry.id,
                label=entry.label,
                entity_type=entry.entity_type,
                matched_text=text,
                position=(0, len(text)),
                extra=entry.extra
            )
        return None
