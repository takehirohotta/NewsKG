"""
エンティティ正規化モジュール

LLMを使って類似エンティティをグループ化し、標準化します。
"""

import json
import logging
from typing import Dict, List, Optional, Set
from collections import Counter
from dataclasses import dataclass

from .llm_client import OpenRouterClient, get_client


@dataclass
class EntityGroup:
    canonical: str
    members: List[str]
    entity_type: str
    confidence: float = 1.0


class EntityBatchNormalizer:
    
    SYSTEM_PROMPT = """あなたは日本語のエンティティ（人名、組織名、地名など）を正規化する専門家です。

## タスク
与えられたエンティティリストを分析し、同一の実体を指す異なる表記をグループ化して正規化してください。

## 出力形式
JSON形式で以下の構造で出力してください：
{
  "groups": [
    {
      "canonical": "正規化された名称（代表形）",
      "members": ["表記1", "表記2", ...],
      "entity_type": "person|organization|place|other"
    }
  ]
}

## ルール
1. 同一人物・同一組織・同一場所の異なる表記は1つのグループにまとめる
2. 代表形は最も正式で完全な表記を選ぶ
3. 敬称の有無は無視する（例: 「高市首相」「高市早苗」→「高市早苗」）
4. 組織名の略称と正式名称は統合する（例: 「自民」「自民党」→「自由民主党」）
5. 役職付きの名前と名前のみは統合する（例: 「木原官房長官」「木原誠二」→「木原誠二」）
6. 出現回数が多く、より詳細な表記を代表形にする

## 例
入力:
- 高市首相 (50回)
- 高市早苗 (30回)
- 高市総理 (10回)

出力:
{
  "canonical": "高市早苗",
  "members": ["高市首相", "高市早苗", "高市総理"],
  "entity_type": "person"
}"""

    def __init__(self, client: Optional[OpenRouterClient] = None):
        self.client = client or get_client()
        self.logger = logging.getLogger(__name__)
    
    def normalize_entities(
        self,
        entities: List[str],
        entity_type: str = "person"
    ) -> Dict[str, str]:
        if not entities:
            return {}
        
        entity_counts = Counter(entities)
        unique_entities = list(entity_counts.keys())
        
        if len(unique_entities) < 3:
            return {e: e for e in unique_entities}
        
        try:
            result = self._llm_normalize(unique_entities, entity_counts, entity_type)
            return result
        except Exception as e:
            self.logger.error(f"エンティティ正規化エラー: {e}")
            return {e: e for e in unique_entities}
    
    def _llm_normalize(
        self,
        entities: List[str],
        counts: Counter,
        entity_type: str
    ) -> Dict[str, str]:
        entity_list = [f"- {e} ({counts[e]}回)" for e in entities]
        
        user_prompt = f"""以下の{entity_type}エンティティリストを正規化してください。括弧内は出現回数です。

{chr(10).join(entity_list)}

JSON形式で出力してください。"""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.client.chat_json(messages, temperature=0.1)
        
        mapping = {}
        for group in response.get("groups", []):
            canonical = group.get("canonical", "")
            members = group.get("members", [])
            
            for member in members:
                mapping[member] = canonical
        
        return mapping
    
    def normalize_entities_by_type(
        self,
        entities_by_type: Dict[str, List[str]]
    ) -> Dict[str, Dict[str, str]]:
        result = {}
        
        for entity_type, entities in entities_by_type.items():
            self.logger.info(f"{entity_type}タイプのエンティティを正規化中: {len(entities)}件")
            mapping = self.normalize_entities(entities, entity_type)
            result[entity_type] = mapping
        
        return result


def get_entity_normalizer() -> EntityBatchNormalizer:
    return EntityBatchNormalizer()
