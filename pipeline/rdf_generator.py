"""
RDF生成モジュール

抽出結果をRDF（Turtle形式）に変換します。
"""

from typing import List
from pathlib import Path
from datetime import datetime
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD

from extractors.base import Entity, Statement, ExtractionResult


class RDFGenerator:
    """RDFグラフを生成するクラス"""

    # 名前空間の定義
    NEWSKG = Namespace("http://example.org/newskg#")
    DCT = Namespace("http://purl.org/dc/terms/")
    SCHEMA = Namespace("http://schema.org/")

    def __init__(self):
        """RDFGeneratorを初期化"""
        self.graph = Graph()
        self.entity_cache = set()
        self._bind_namespaces()

    def _bind_namespaces(self):
        """名前空間をバインド"""
        self.graph.bind("newskg", self.NEWSKG)
        self.graph.bind("dct", self.DCT)
        self.graph.bind("schema", self.SCHEMA)

    def reset(self):
        """グラフをリセット"""
        self.graph = Graph()
        self.entity_cache = set()
        self._bind_namespaces()

    def add_article(self, article: dict) -> URIRef:
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

        if "content" in article:
            self.graph.add((
                article_uri,
                self.NEWSKG.hasContent,
                Literal(article["content"], datatype=XSD.string)
            ))

        return article_uri

    def add_entity(self, entity: Entity) -> URIRef:
        """
        エンティティをRDFグラフに追加（既存は再利用）

        Args:
            entity: Entityオブジェクト

        Returns:
            エンティティのURIRef
        """
        entity_uri = URIRef(entity.to_uri(str(self.NEWSKG)))

        # 既に追加済みなら再利用
        if entity_uri in self.entity_cache:
            return entity_uri

        self.entity_cache.add(entity_uri)

        # エンティティタイプに応じたクラスを設定
        type_class_map = {
            "organization": self.NEWSKG.Organization,
            "person": self.NEWSKG.Person,
            "place": self.NEWSKG.Place,
        }
        entity_class = type_class_map.get(entity.entity_type, self.NEWSKG.Entity)
        self.graph.add((entity_uri, RDF.type, entity_class))

        # ラベルを追加
        self.graph.add((
            entity_uri,
            self.NEWSKG.hasLabel,
            Literal(entity.label, lang="ja")
        ))

        # 別名（マッチしたテキストがラベルと異なる場合）
        if entity.matched_text != entity.label:
            self.graph.add((
                entity_uri,
                self.NEWSKG.hasAlias,
                Literal(entity.matched_text, lang="ja")
            ))

        # 追加属性
        if entity.extra:
            if "role" in entity.extra and entity.extra["role"]:
                self.graph.add((
                    entity_uri,
                    self.NEWSKG.hasRole,
                    Literal(entity.extra["role"], datatype=XSD.string)
                ))

        return entity_uri

    def add_statement(self, statement: Statement, article_uri: URIRef) -> URIRef:
        """
        StatementをRDFグラフに追加

        Args:
            statement: Statementオブジェクト
            article_uri: 抽出元記事のURI

        Returns:
            StatementのURIRef
        """
        stmt_uri = URIRef(statement.to_uri(str(self.NEWSKG)))

        # Statementタイプに応じたクラスを設定
        type_class_map = {
            "DissolutionAnnouncement": self.NEWSKG.DissolutionAnnouncement,
            "ElectionResult": self.NEWSKG.ElectionResult,
            "CandidateAnnouncement": self.NEWSKG.CandidateAnnouncement,
            "ElectionSchedule": self.NEWSKG.ElectionStatement,
            "EarthquakeEvent": self.NEWSKG.EarthquakeEvent,
            "WeatherDisaster": self.NEWSKG.WeatherDisaster,
            "EvacuationOrder": self.NEWSKG.EvacuationOrder,
            "DamageReport": self.NEWSKG.DisasterStatement,
            "PolicyAnnouncement": self.NEWSKG.PolicyAnnouncement,
            "BudgetDecision": self.NEWSKG.BudgetDecision,
            "LegislationEvent": self.NEWSKG.LegislationEvent,
        }
        stmt_class = type_class_map.get(
            statement.statement_type, self.NEWSKG.Statement
        )
        self.graph.add((stmt_uri, RDF.type, stmt_class))

        # 抽出元記事への参照
        self.graph.add((stmt_uri, self.NEWSKG.extractedFrom, article_uri))

        # 信頼度
        self.graph.add((
            stmt_uri,
            self.NEWSKG.hasConfidence,
            Literal(statement.confidence, datatype=XSD.decimal)
        ))

        # 抽出されたデータをプロパティとして追加
        self._add_extracted_data(stmt_uri, statement)

        # 関連エンティティを関連付け（追加は事前に済ませる）
        for entity in statement.entities:
            entity_uri = URIRef(entity.to_uri(str(self.NEWSKG)))
            if entity.entity_type == "person":
                self.graph.add((stmt_uri, self.NEWSKG.hasActor, entity_uri))
            elif entity.entity_type == "place":
                self.graph.add((stmt_uri, self.NEWSKG.hasLocation, entity_uri))
            elif entity.entity_type == "organization":
                self.graph.add((stmt_uri, self.NEWSKG.hasActor, entity_uri))

        return stmt_uri

    def _add_extracted_data(self, stmt_uri: URIRef, statement: Statement):
        """抽出されたデータをプロパティとして追加"""
        data = statement.extracted_data

        # 予算額
        if "budget_amount_yen" in data:
            self.graph.add((
                stmt_uri,
                self.NEWSKG.hasBudgetAmount,
                Literal(data["budget_amount_yen"], datatype=XSD.decimal)
            ))

        # 政策分野
        if "policy_area" in data:
            self.graph.add((
                stmt_uri,
                self.NEWSKG.hasPolicyArea,
                Literal(data["policy_area"], datatype=XSD.string)
            ))

        # 災害種別
        if "disaster_type" in data:
            self.graph.add((
                stmt_uri,
                self.NEWSKG.hasDisasterType,
                Literal(data["disaster_type"], datatype=XSD.string)
            ))

        # 震度
        if "seismic_intensity" in data:
            self.graph.add((
                stmt_uri,
                self.NEWSKG.hasSeismicIntensity,
                Literal(data["seismic_intensity"], datatype=XSD.string)
            ))

        # マグニチュード
        if "magnitude" in data:
            self.graph.add((
                stmt_uri,
                self.NEWSKG.hasMagnitude,
                Literal(data["magnitude"], datatype=XSD.decimal)
            ))

        # 選挙種別
        if "election_type" in data:
            self.graph.add((
                stmt_uri,
                self.NEWSKG.hasElectionType,
                Literal(data["election_type"], datatype=XSD.string)
            ))

    def add_extraction_result(self, result: ExtractionResult):
        """
        抽出結果全体をRDFグラフに追加

        Args:
            result: ExtractionResultオブジェクト
        """
        # 記事を追加
        article_dict = {
            "id": result.article_id,
            "title": result.article_title,
            "url": result.article_url,
            "pubDate": result.article_pub_date,
        }
        article_uri = self.add_article(article_dict)

        # エンティティをキャッシュした上でStatementを追加
        for entity in result.entities:
            self.add_entity(entity)

        for statement in result.statements:
            # Statement内のエンティティも追加しつつ関連付け
            stmt_entities = [self.add_entity(e) for e in statement.entities]
            stmt_uri = self.add_statement(statement, article_uri)

            # add_statement 内では add_entity を呼ばず、既存URIを関連付けに使用
            # （将来的に add_statement の重複追加を避けるための前段処理）
            # 既存の add_statement 実装は add_entity を呼ぶため、
            # 今回はキャッシュにより重複追加を避ける

        # add_statement 内で add_entity を呼んでもキャッシュで無駄を削減

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

    def get_statistics(self) -> dict:
        """グラフの統計情報を取得"""
        return {
            "total_triples": len(self.graph),
            "subjects": len(set(self.graph.subjects())),
            "predicates": len(set(self.graph.predicates())),
            "objects": len(set(self.graph.objects())),
        }
