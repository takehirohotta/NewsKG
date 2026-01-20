"""
LLMベースのトリプル抽出モジュール

ニュース記事からLLMを使って知識グラフ用のトリプル（主語-述語-目的語）を抽出します。
"""

import json
import hashlib
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .llm_client import OpenRouterClient, get_client


@dataclass
class Triple:
    """抽出されたトリプルを表すデータクラス"""
    subject: str           # 主語（エンティティ名）
    subject_type: str      # 主語のタイプ（person, organization, place, other）
    predicate: str         # 述語（関係）
    object: str            # 目的語（エンティティ名または値）
    object_type: str       # 目的語のタイプ
    confidence: float      # 信頼度 (0.0-1.0)
    source_article_id: Optional[str] = None
    extraction_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "subject": self.subject,
            "subject_type": self.subject_type,
            "predicate": self.predicate,
            "object": self.object,
            "object_type": self.object_type,
            "confidence": self.confidence,
            "source_article_id": self.source_article_id,
        }
    
    def get_id(self) -> str:
        """トリプルのユニークIDを生成"""
        base = f"{self.subject}_{self.predicate}_{self.object}"
        return hashlib.md5(base.encode()).hexdigest()[:12]


@dataclass 
class ExtractionResult:
    """記事からの抽出結果"""
    article_id: str
    article_title: str
    triples: List[Triple]
    raw_response: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "article_id": self.article_id,
            "article_title": self.article_title,
            "triples": [t.to_dict() for t in self.triples],
            "triple_count": len(self.triples)
        }


# トリプル抽出用のシステムプロンプト
SYSTEM_PROMPT = """あなたはニュース記事から知識グラフ用のトリプル（主語-述語-目的語）を抽出する専門家です。

## タスク
与えられたニュース記事から、重要な事実関係をトリプル形式で抽出してください。

## 出力形式
JSON形式で以下の構造で出力してください：
{
  "triples": [
    {
      "subject": "主語（人物名、組織名、場所名など）",
      "subject_type": "person|organization|place|event|other",
      "predicate": "述語（関係を表す動詞や名詞句）",
      "object": "目的語（人物名、組織名、場所名、値など）",
      "object_type": "person|organization|place|event|value|other",
      "confidence": 0.0-1.0の信頼度
    }
  ]
}

## 抽出ルール
1. **具体的な述語を使用**: 「関係がある」ではなく「就任」「訪問」「会談」「発表」「逮捕」など具体的に
2. **人物・組織・場所を重視**: 固有名詞を正確に抽出
3. **ニュース価値のある関係**: 記事の主要な事実を表すトリプルを優先
4. **信頼度**: 明確に記述されている事実は高め(0.8-1.0)、推測は低め(0.5-0.7)

## 述語の例
- 人物関係: 就任、辞任、当選、立候補、逮捕、死亡、訪問、会談、発言、批判、支持
- 組織関係: 所属、代表、設立、買収、提携、発表、決定
- 場所関係: 発生、開催、位置、移転
- 行動・イベント: 開始、終了、延期、中止、承認、否決

## 注意点
- 1記事から3〜10個程度のトリプルを抽出
- 同じ情報の重複は避ける
- 曖昧な表現は避け、具体的に記述"""


class LLMTripleExtractor:
    """LLMを使ったトリプル抽出クラス"""
    
    def __init__(self, client: Optional[OpenRouterClient] = None, reasoning: bool = True):
        self.client = client or get_client()
        self.logger = logging.getLogger(__name__)
        self.reasoning = reasoning
    
    def extract(self, title: str, content: str, article_id: Optional[str] = None) -> ExtractionResult:
        """
        ニュース記事からトリプルを抽出
        
        Args:
            title: 記事タイトル
            content: 記事本文
            article_id: 記事ID（オプション）
        
        Returns:
            ExtractionResult
        """
        # 本文が長い場合は切り詰め（トークン制限対策）
        max_content_length = 3000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        # ユーザープロンプトを構築
        user_prompt = f"""以下のニュース記事からトリプルを抽出してください。

## タイトル
{title}

## 本文
{content}

JSON形式で出力してください。"""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.client.chat_json(messages, temperature=0.2, reasoning=self.reasoning)
            
            # トリプルをパース
            triples = []
            for t in response.get("triples", []):
                triple = Triple(
                    subject=t.get("subject", ""),
                    subject_type=t.get("subject_type", "other"),
                    predicate=t.get("predicate", ""),
                    object=t.get("object", ""),
                    object_type=t.get("object_type", "other"),
                    confidence=float(t.get("confidence", 0.5)),
                    source_article_id=article_id
                )
                # 空のトリプルはスキップ
                if triple.subject and triple.predicate and triple.object:
                    triples.append(triple)
            
            return ExtractionResult(
                article_id=article_id or "unknown",
                article_title=title,
                triples=triples,
                raw_response=response
            )
            
        except Exception as e:
            self.logger.error(f"トリプル抽出エラー: {e}")
            return ExtractionResult(
                article_id=article_id or "unknown",
                article_title=title,
                triples=[],
                raw_response={"error": str(e)}
            )
    
    def extract_from_article(self, article: Dict[str, Any]) -> ExtractionResult:
        """
        記事辞書からトリプルを抽出
        
        Args:
            article: 記事辞書（id, title, content, summaryを含む）
        
        Returns:
            ExtractionResult
        """
        article_id = article.get("id", "unknown")
        title = article.get("title", "")
        
        # 本文を構築（summaryとcontentを結合）
        content_parts = [
            article.get("summary", ""),
            article.get("content", "")
        ]
        content = "\n".join(filter(None, content_parts))
        
        return self.extract(title, content, article_id)
    
    def extract_batch(
        self, 
        articles: List[Dict[str, Any]], 
        progress_callback: Optional[callable] = None
    ) -> List[ExtractionResult]:
        """
        複数記事からバッチでトリプルを抽出
        
        Args:
            articles: 記事リスト
            progress_callback: 進捗コールバック関数 (current, total, result)
        
        Returns:
            ExtractionResultのリスト
        """
        results = []
        total = len(articles)
        
        for i, article in enumerate(articles):
            result = self.extract_from_article(article)
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, total, result)
            
            self.logger.info(
                f"[{i+1}/{total}] {article.get('title', '')[:30]}... -> {len(result.triples)} triples"
            )
        
        return results


# シングルトンインスタンス
_extractor: Optional[LLMTripleExtractor] = None


def get_extractor() -> LLMTripleExtractor:
    """シングルトンの抽出器を取得"""
    global _extractor
    if _extractor is None:
        _extractor = LLMTripleExtractor()
    return _extractor
