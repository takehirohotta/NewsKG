"""
RDF生成モジュール v2（トリプルベース）

LLMが抽出したトリプルをRDF（Turtle形式）に変換します。
Statementを廃止し、エンティティ間の直接関係を表現します。
"""

import re
import hashlib
from typing import List, Dict, Any, Set
from pathlib import Path
from datetime import datetime
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from extractors.llm_extractor import Triple, ExtractionResult as TripleExtractionResult
from extractors.entity_resolver import EntityResolver, ResolvedEntity, get_resolver
from extractors.predicate_normalizer import PredicateNormalizer, get_normalizer


class TripleBasedRDFGenerator:
    """トリプルベースのRDFグラフを生成するクラス"""

    # 名前空間の定義
    NEWSKG = Namespace("http://example.org/newskg#")
    DCT = Namespace("http://purl.org/dc/terms/")
    SCHEMA = Namespace("http://schema.org/")

    def __init__(
        self,
        entity_resolver: EntityResolver = None,
        predicate_normalizer: PredicateNormalizer = None
    ):
        """
        Args:
            entity_resolver: エンティティ解決器
            predicate_normalizer: 述語正規化器
        """
        self.graph = Graph()
        self.entity_resolver = entity_resolver or get_resolver()
        self.predicate_normalizer = predicate_normalizer or get_normalizer()
        
        # キャッシュ
        self.entity_cache: Set[str] = set()
        self.triple_cache: Set[str] = set()
        self.predicate_uris: Dict[str, URIRef] = {}
        
        self._bind_namespaces()

    def _bind_namespaces(self):
        """名前空間をバインド"""
        self.graph.bind("newskg", self.NEWSKG)
        self.graph.bind("dct", self.DCT)
        self.graph.bind("schema", self.SCHEMA)

    def reset(self):
        """グラフをリセット"""
        self.graph = Graph()
        self.entity_cache.clear()
        self.triple_cache.clear()
        self._bind_namespaces()

    def add_article(self, article: Dict[str, Any]) -> URIRef:
        """
        ニュース記事をRDFグラフに追加

        Args:
            article: 記事辞書

        Returns:
            記事のURIRef
        """
        article_id = article.get("id", "unknown")
        article_uri = URIRef(f"{self.NEWSKG}article_{article_id}")

        # 型を追加
        self.graph.add((article_uri, RDF.type, self.NEWSKG.NewsArticle))

        # プロパティを追加
        if "title" in article:
            self.graph.add((
                article_uri,
                self.NEWSKG.hasTitle,
                Literal(article["title"], datatype=XSD.string)
            ))

        if "url" in article:
            self.graph.add((
                article_uri,
                self.NEWSKG.hasUrl,
                Literal(article["url"], datatype=XSD.anyURI)
            ))

        if "pubDate" in article:
            self.graph.add((
                article_uri,
                self.NEWSKG.hasPubDate,
                Literal(article["pubDate"], datatype=XSD.dateTime)
            ))

        return article_uri

    def add_entity(self, entity: ResolvedEntity) -> URIRef:
        """
        エンティティをRDFグラフに追加

        Args:
            entity: ResolvedEntityオブジェクト

        Returns:
            エンティティのURIRef
        """
        entity_uri = URIRef(entity.to_uri(str(self.NEWSKG)))

        # 既に追加済みなら再利用
        if str(entity_uri) in self.entity_cache:
            return entity_uri

        self.entity_cache.add(str(entity_uri))

        # エンティティタイプに応じたクラスを設定
        type_class_map = {
            "organization": self.NEWSKG.Organization,
            "person": self.NEWSKG.Person,
            "place": self.NEWSKG.Place,
            "event": self.NEWSKG.Event,
            "other": self.NEWSKG.Entity,
        }
        entity_class = type_class_map.get(entity.entity_type, self.NEWSKG.Entity)
        self.graph.add((entity_uri, RDF.type, entity_class))

        # ラベルを追加
        self.graph.add((
            entity_uri,
            self.NEWSKG.hasLabel,
            Literal(entity.label, lang="ja")
        ))

        # 元のテキストが異なる場合は別名として追加
        if entity.original_text != entity.label:
            self.graph.add((
                entity_uri,
                self.NEWSKG.hasAlias,
                Literal(entity.original_text, lang="ja")
            ))

        return entity_uri

    def _get_predicate_uri(self, predicate: str) -> URIRef:
        """述語のURIを取得（正規化を適用）"""
        # 正規化
        pred_id, pred_label = self.predicate_normalizer.normalize(predicate)
        
        # キャッシュ確認
        if pred_id in self.predicate_uris:
            return self.predicate_uris[pred_id]
        
        # 安全なURI用IDを生成
        safe_id = self._make_safe_uri_part(pred_id)
        pred_uri = URIRef(f"{self.NEWSKG}rel_{safe_id}")
        
        # 述語自体の定義を追加
        self.graph.add((pred_uri, RDF.type, RDF.Property))
        self.graph.add((pred_uri, RDFS.label, Literal(pred_label, lang="ja")))
        
        self.predicate_uris[pred_id] = pred_uri
        return pred_uri

    def _make_safe_uri_part(self, text: str) -> str:
        """URI安全な文字列に変換"""
        # 英数字とアンダースコアのみ残す
        if re.match(r'^[a-zA-Z0-9_]+$', text):
            return text.lower()
        
        # 日本語などはハッシュに変換
        hash_val = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"pred_{hash_val}"

    def add_triple(
        self,
        triple: Triple,
        article_uri: URIRef = None
    ) -> URIRef:
        """
        トリプルをRDFグラフに追加

        Args:
            triple: Tripleオブジェクト
            article_uri: 抽出元記事のURI（オプション）

        Returns:
            トリプルのreification URIRef
        """
        # エンティティを解決
        subject_entity = self.entity_resolver.resolve(triple.subject, triple.subject_type)
        object_entity = self.entity_resolver.resolve(triple.object, triple.object_type)

        # エンティティをグラフに追加
        subject_uri = self.add_entity(subject_entity)
        object_uri = self.add_entity(object_entity)

        # 述語のURIを取得
        predicate_uri = self._get_predicate_uri(triple.predicate)

        # 直接関係を追加
        self.graph.add((subject_uri, predicate_uri, object_uri))

        # Reification（メタ情報の付与）
        triple_id = triple.get_id()
        
        # 同じトリプルの重複を避ける
        if triple_id in self.triple_cache:
            return URIRef(f"{self.NEWSKG}triple_{triple_id}")
        
        self.triple_cache.add(triple_id)
        
        triple_uri = URIRef(f"{self.NEWSKG}triple_{triple_id}")
        self.graph.add((triple_uri, RDF.type, self.NEWSKG.NewsTriple))
        self.graph.add((triple_uri, RDF.subject, subject_uri))
        self.graph.add((triple_uri, RDF.predicate, predicate_uri))
        self.graph.add((triple_uri, RDF.object, object_uri))

        # 信頼度
        self.graph.add((
            triple_uri,
            self.NEWSKG.hasConfidence,
            Literal(triple.confidence, datatype=XSD.decimal)
        ))

        # 抽出元記事
        if article_uri:
            self.graph.add((triple_uri, self.NEWSKG.extractedFrom, article_uri))

        # 抽出時刻
        self.graph.add((
            triple_uri,
            self.NEWSKG.extractedAt,
            Literal(triple.extraction_timestamp.isoformat(), datatype=XSD.dateTime)
        ))

        return triple_uri

    def add_extraction_result(self, result: TripleExtractionResult, article: Dict[str, Any] = None):
        """
        抽出結果全体をRDFグラフに追加

        Args:
            result: TripleExtractionResultオブジェクト
            article: 記事辞書（オプション）
        """
        # 記事を追加
        article_uri = None
        if article:
            article_uri = self.add_article(article)
        elif result.article_id:
            # 記事情報がない場合は最小限の情報で追加
            article_uri = self.add_article({
                "id": result.article_id,
                "title": result.article_title
            })

        # トリプルを追加
        for triple in result.triples:
            self.add_triple(triple, article_uri)

    def serialize(self, format: str = "turtle") -> str:
        """
        RDFグラフをシリアライズ

        Args:
            format: 出力フォーマット (turtle, xml, n3, nt, etc.)

        Returns:
            シリアライズされた文字列
        """
        return self.graph.serialize(format=format)

    def save(self, output_path: str, format: str = "turtle"):
        """
        RDFグラフをファイルに保存

        Args:
            output_path: 出力ファイルパス
            format: 出力フォーマット
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph.serialize(destination=str(output_path), format=format)

    def get_statistics(self) -> Dict[str, Any]:
        """グラフの統計情報を取得"""
        # エンティティタイプ別カウント
        entity_counts = {
            "person": 0,
            "organization": 0,
            "place": 0,
            "other": 0
        }
        
        for entity_type, newskg_class in [
            ("person", self.NEWSKG.Person),
            ("organization", self.NEWSKG.Organization),
            ("place", self.NEWSKG.Place),
        ]:
            entity_counts[entity_type] = len(list(
                self.graph.subjects(RDF.type, newskg_class)
            ))
        
        # 記事数
        article_count = len(list(
            self.graph.subjects(RDF.type, self.NEWSKG.NewsArticle)
        ))
        
        # トリプル数
        triple_count = len(list(
            self.graph.subjects(RDF.type, self.NEWSKG.NewsTriple)
        ))
        
        # 述語数
        predicate_count = len(self.predicate_uris)
        
        return {
            "total_rdf_triples": len(self.graph),
            "articles": article_count,
            "news_triples": triple_count,
            "unique_predicates": predicate_count,
            "entities": entity_counts,
            "total_entities": sum(entity_counts.values()),
        }
