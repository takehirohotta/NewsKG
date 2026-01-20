"""
エンティティ解決モジュール

LLMが抽出したエンティティを既存辞書とマッチングし、
新規エンティティの処理を行います。
"""

import re
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from dictionaries import DictionaryLoader, get_loader, DictionaryEntry


@dataclass
class ResolvedEntity:
    """解決されたエンティティ"""
    id: str                    # URI用ID
    label: str                 # 表示ラベル
    entity_type: str           # person, organization, place, other
    original_text: str         # 元のテキスト
    is_known: bool             # 辞書に存在したか
    confidence: float = 1.0    # マッチング信頼度
    
    def to_uri(self, base_ns: str = "http://example.org/newskg#") -> str:
        """RDF URIを生成"""
        return f"{base_ns}{self.entity_type}_{self.id}"


class EntityResolver:
    """エンティティ解決クラス"""
    
    def __init__(self, loader: Optional[DictionaryLoader] = None):
        """
        Args:
            loader: 辞書ローダー。未指定の場合はシングルトンを使用
        """
        self.loader = loader or get_loader()
        self.logger = logging.getLogger(__name__)
        
        # 新規エンティティのキャッシュ
        self.new_entities: Dict[str, ResolvedEntity] = {}
    
    def resolve(self, text: str, entity_type: str = "other") -> ResolvedEntity:
        """
        エンティティテキストを解決
        
        Args:
            text: エンティティテキスト
            entity_type: エンティティタイプのヒント
        
        Returns:
            ResolvedEntity
        """
        # 空文字チェック
        if not text or not text.strip():
            return ResolvedEntity(
                id="unknown",
                label="不明",
                entity_type="other",
                original_text=text,
                is_known=False,
                confidence=0.0
            )
        
        text = text.strip()
        
        # 辞書から検索
        entry = self.loader.find_entity(text)
        
        if entry:
            return ResolvedEntity(
                id=entry.id,
                label=entry.label,
                entity_type=entry.entity_type,
                original_text=text,
                is_known=True,
                confidence=1.0
            )
        
        # 部分一致を試みる
        partial_match = self._find_partial_match(text)
        if partial_match:
            entry, confidence = partial_match
            return ResolvedEntity(
                id=entry.id,
                label=entry.label,
                entity_type=entry.entity_type,
                original_text=text,
                is_known=True,
                confidence=confidence
            )
        
        # 新規エンティティとして処理
        return self._create_new_entity(text, entity_type)
    
    def _find_partial_match(self, text: str) -> Optional[Tuple[DictionaryEntry, float]]:
        """部分一致でエンティティを検索"""
        # 敬称や役職を除去してマッチング
        cleaned = self._clean_entity_text(text)
        
        if cleaned != text:
            entry = self.loader.find_entity(cleaned)
            if entry:
                return entry, 0.9
        
        # テキストが辞書エントリに含まれているか
        all_entries = self.loader.get_all_entries()
        for entry in all_entries:
            # ラベルがテキストに含まれている
            if entry.label in text:
                return entry, 0.8
            # テキストがラベルに含まれている
            if text in entry.label:
                return entry, 0.7
            # エイリアスチェック
            for alias in entry.aliases:
                if alias in text or text in alias:
                    return entry, 0.75
        
        return None
    
    def _clean_entity_text(self, text: str) -> str:
        """エンティティテキストから敬称・役職を除去"""
        # 敬称パターン
        honorifics = [
            r'氏$', r'さん$', r'様$', r'君$',
            r'大統領$', r'首相$', r'総理$', r'総裁$', r'代表$',
            r'議員$', r'知事$', r'市長$', r'社長$', r'会長$',
            r'大臣$', r'長官$', r'委員長$'
        ]
        
        cleaned = text
        for pattern in honorifics:
            cleaned = re.sub(pattern, '', cleaned)
        
        return cleaned.strip()
    
    def _create_new_entity(self, text: str, entity_type: str) -> ResolvedEntity:
        """新規エンティティを作成"""
        # IDを生成（テキストのハッシュ）
        entity_id = self._generate_id(text)
        
        # タイプを推定
        if entity_type == "other":
            entity_type = self._infer_entity_type(text)
        
        entity = ResolvedEntity(
            id=entity_id,
            label=text,
            entity_type=entity_type,
            original_text=text,
            is_known=False,
            confidence=0.5
        )
        
        # キャッシュに追加
        self.new_entities[entity_id] = entity
        
        return entity
    
    def _generate_id(self, text: str) -> str:
        """テキストからIDを生成"""
        # 日本語をローマ字風に変換するのは複雑なので、ハッシュを使用
        hash_val = hashlib.md5(text.encode()).hexdigest()[:8]
        
        # 英数字のみの場合はそのまま使用
        if re.match(r'^[a-zA-Z0-9_]+$', text):
            return text.lower().replace(' ', '_')
        
        # 日本語の場合はハッシュベース
        return f"entity_{hash_val}"
    
    def _infer_entity_type(self, text: str) -> str:
        """テキストからエンティティタイプを推定"""
        # 組織パターン
        org_patterns = [
            r'党$', r'省$', r'庁$', r'社$', r'銀行$', r'大学$',
            r'会$', r'機構$', r'協会$', r'連盟$', r'委員会$'
        ]
        for pattern in org_patterns:
            if re.search(pattern, text):
                return "organization"
        
        # 場所パターン
        place_patterns = [
            r'県$', r'市$', r'区$', r'町$', r'村$', r'国$',
            r'州$', r'島$', r'山$', r'川$', r'湖$'
        ]
        for pattern in place_patterns:
            if re.search(pattern, text):
                return "place"
        
        # 人物パターン（敬称があれば人物の可能性が高い）
        person_indicators = ['氏', 'さん', '大統領', '首相', '議員']
        for ind in person_indicators:
            if ind in text:
                return "person"
        
        return "other"
    
    def resolve_triple(self, triple: Dict) -> Dict:
        """
        トリプル内のエンティティを解決
        
        Args:
            triple: トリプル辞書 {subject, subject_type, predicate, object, object_type, ...}
        
        Returns:
            エンティティが解決されたトリプル辞書
        """
        # 主語を解決
        subject_resolved = self.resolve(
            triple.get("subject", ""),
            triple.get("subject_type", "other")
        )
        
        # 目的語を解決
        object_resolved = self.resolve(
            triple.get("object", ""),
            triple.get("object_type", "other")
        )
        
        return {
            **triple,
            "subject_id": subject_resolved.id,
            "subject_label": subject_resolved.label,
            "subject_type_resolved": subject_resolved.entity_type,
            "subject_uri": subject_resolved.to_uri(),
            "subject_is_known": subject_resolved.is_known,
            "object_id": object_resolved.id,
            "object_label": object_resolved.label,
            "object_type_resolved": object_resolved.entity_type,
            "object_uri": object_resolved.to_uri(),
            "object_is_known": object_resolved.is_known,
        }
    
    def get_new_entities(self) -> List[ResolvedEntity]:
        """新規エンティティのリストを取得"""
        return list(self.new_entities.values())
    
    def clear_cache(self):
        """新規エンティティのキャッシュをクリア"""
        self.new_entities.clear()


# シングルトンインスタンス
_resolver: Optional[EntityResolver] = None


def get_resolver() -> EntityResolver:
    """シングルトンの解決器を取得"""
    global _resolver
    if _resolver is None:
        _resolver = EntityResolver()
    return _resolver
