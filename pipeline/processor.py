"""
パイプライン処理オーケストレーター

記事データの読み込みから抽出、RDF生成、検証までの全体フローを制御します。
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from extractors import EntityExtractor, StatementExtractor, ExtractionResult
from .rdf_generator import RDFGenerator
from .validator import SHACLValidator


class PipelineProcessor:
    """パイプライン処理を行うクラス"""

    def __init__(self, validate: bool = True):
        """
        Args:
            validate: SHACL検証を行うかどうか
        """
        self.entity_extractor = EntityExtractor()
        self.statement_extractor = StatementExtractor(self.entity_extractor)
        self.rdf_generator = RDFGenerator()
        self.validator = SHACLValidator() if validate else None
        self.validate_output = validate

        # 処理統計
        self.stats = {
            "total_articles": 0,
            "articles_with_statements": 0,
            "total_entities": 0,
            "total_statements": 0,
            "statement_types": {},
            "entity_types": {"organization": 0, "person": 0, "place": 0},
        }

        # ロガー設定
        self.logger = logging.getLogger(__name__)

    def load_articles(self, input_path: str) -> List[Dict]:
        """
        記事データを読み込み

        Args:
            input_path: articles.jsonのパス

        Returns:
            記事リスト
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        articles = data.get("articles", [])
        self.logger.info(f"{len(articles)}件の記事を読み込みました")
        return articles

    def process_article(self, article: Dict) -> ExtractionResult:
        """
        単一の記事を処理

        Args:
            article: 記事辞書

        Returns:
            ExtractionResult
        """
        # エンティティ抽出
        entities = self.entity_extractor.extract_from_article(article)

        # Statement抽出
        statements = self.statement_extractor.extract_from_article(article)

        # 抽出結果を構築
        result = ExtractionResult(
            article_id=article.get("id", "unknown"),
            article_title=article.get("title", ""),
            article_url=article.get("url", ""),
            article_pub_date=article.get("pubDate", ""),
            entities=entities,
            statements=statements,
        )

        return result

    def process_all(
        self, articles: List[Dict], progress_callback=None
    ) -> List[ExtractionResult]:
        """
        全記事を処理

        Args:
            articles: 記事リスト
            progress_callback: 進捗コールバック関数

        Returns:
            ExtractionResultのリスト
        """
        results = []
        total = len(articles)

        for i, article in enumerate(articles):
            result = self.process_article(article)
            results.append(result)

            # 統計更新
            self._update_stats(result)

            # RDFグラフに追加
            self.rdf_generator.add_extraction_result(result)

            # 進捗通知
            if progress_callback:
                progress_callback(i + 1, total, result)

        self.stats["total_articles"] = total
        return results

    def _update_stats(self, result: ExtractionResult):
        """統計情報を更新"""
        if result.has_statements():
            self.stats["articles_with_statements"] += 1

        self.stats["total_entities"] += len(result.entities)
        self.stats["total_statements"] += len(result.statements)

        # エンティティタイプ別カウント
        for entity in result.entities:
            if entity.entity_type in self.stats["entity_types"]:
                self.stats["entity_types"][entity.entity_type] += 1

        # Statementタイプ別カウント
        for statement in result.statements:
            st_type = statement.statement_type
            self.stats["statement_types"][st_type] = \
                self.stats["statement_types"].get(st_type, 0) + 1

    def save_output(self, output_dir: str) -> Dict[str, str]:
        """
        出力を保存

        Args:
            output_dir: 出力ディレクトリ

        Returns:
            保存したファイルパスの辞書
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # タイムスタンプ
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # RDFファイルを保存
        rdf_path = output_dir / f"knowledge_graph_{timestamp}.ttl"
        self.rdf_generator.save(str(rdf_path), format="turtle")
        self.logger.info(f"RDFを保存: {rdf_path}")

        # 最新版としてもコピー
        latest_path = output_dir / "knowledge_graph.ttl"
        self.rdf_generator.save(str(latest_path), format="turtle")

        # 統計情報を保存
        stats_path = output_dir / f"stats_{timestamp}.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        self.logger.info(f"統計情報を保存: {stats_path}")

        return {
            "rdf": str(rdf_path),
            "rdf_latest": str(latest_path),
            "stats": str(stats_path),
        }

    def validate_output_file(self, rdf_path: str) -> Dict[str, Any]:
        """
        出力ファイルをSHACL検証

        Args:
            rdf_path: RDFファイルのパス

        Returns:
            検証結果の辞書
        """
        if not self.validator:
            return {"conforms": True, "message": "検証スキップ"}

        conforms, report = self.validator.validate_file(rdf_path)
        return {
            "conforms": conforms,
            "message": "データは全ての制約に適合しています" if conforms else report,
        }

    def run(
        self, input_path: str, output_dir: str, verbose: bool = False
    ) -> Dict[str, Any]:
        """
        パイプライン全体を実行

        Args:
            input_path: articles.jsonのパス
            output_dir: 出力ディレクトリ
            verbose: 詳細出力

        Returns:
            実行結果の辞書
        """
        # ロギング設定
        if verbose:
            logging.basicConfig(
                level=logging.INFO,
                format='[%(asctime)s] %(levelname)s: %(message)s'
            )

        self.logger.info("パイプライン開始")
        start_time = datetime.now()

        # 記事読み込み
        articles = self.load_articles(input_path)

        # 処理実行
        def progress_callback(current, total, result):
            if verbose and current % 50 == 0:
                self.logger.info(f"処理中: {current}/{total}")

        results = self.process_all(articles, progress_callback)

        # 出力保存
        output_files = self.save_output(output_dir)

        # 検証
        validation_result = {"conforms": True, "message": "検証スキップ"}
        if self.validate_output:
            validation_result = self.validate_output_file(output_files["rdf_latest"])

        # 実行時間
        elapsed = (datetime.now() - start_time).total_seconds()

        self.logger.info(f"パイプライン完了 ({elapsed:.2f}秒)")
        self.logger.info(f"  記事数: {self.stats['total_articles']}")
        self.logger.info(f"  Statement抽出記事: {self.stats['articles_with_statements']}")
        self.logger.info(f"  総エンティティ: {self.stats['total_entities']}")
        self.logger.info(f"  総Statement: {self.stats['total_statements']}")

        return {
            "success": True,
            "elapsed_seconds": elapsed,
            "stats": self.stats,
            "output_files": output_files,
            "validation": validation_result,
        }
