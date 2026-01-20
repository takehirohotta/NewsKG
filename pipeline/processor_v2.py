"""
パイプライン処理オーケストレーター v2（トリプルベース）

LLMを使ったトリプル抽出パイプラインを制御します。
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from extractors.llm_extractor import LLMTripleExtractor, ExtractionResult, get_extractor
from extractors.predicate_normalizer import PredicateBatchNormalizer, get_normalizer
from extractors.entity_resolver import EntityResolver, get_resolver
from .rdf_generator_v2 import TripleBasedRDFGenerator


class TriplePipelineProcessor:
    """トリプルベースのパイプライン処理を行うクラス"""

    def __init__(
        self,
        extractor: LLMTripleExtractor = None,
        normalize_predicates: bool = True,
        reasoning: bool = True
    ):
        self.extractor = extractor or LLMTripleExtractor(reasoning=reasoning)
        self.entity_resolver = get_resolver()
        self.predicate_normalizer = get_normalizer()
        self.rdf_generator = TripleBasedRDFGenerator(
            entity_resolver=self.entity_resolver,
            predicate_normalizer=self.predicate_normalizer
        )
        self.normalize_predicates = normalize_predicates

        # 処理統計
        self.stats = {
            "total_articles": 0,
            "articles_with_triples": 0,
            "total_triples": 0,
            "unique_predicates": set(),
            "entity_types": {"person": 0, "organization": 0, "place": 0, "other": 0},
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
        return self.extractor.extract_from_article(article)

    def process_all(
        self,
        articles: List[Dict],
        progress_callback: Optional[callable] = None,
        max_articles: Optional[int] = None
    ) -> List[ExtractionResult]:
        """
        全記事を処理

        Args:
            articles: 記事リスト
            progress_callback: 進捗コールバック関数 (current, total, result)
            max_articles: 処理する最大記事数（デバッグ用）

        Returns:
            ExtractionResultのリスト
        """
        results = []
        
        if max_articles:
            articles = articles[:max_articles]
        
        total = len(articles)

        for i, article in enumerate(articles):
            try:
                result = self.process_article(article)
                results.append(result)

                # 統計更新
                self._update_stats(result)

                # RDFグラフに追加
                self.rdf_generator.add_extraction_result(result, article)

                # 進捗通知
                if progress_callback:
                    progress_callback(i + 1, total, result)

                self.logger.info(
                    f"[{i+1}/{total}] {article.get('title', '')[:40]}... -> {len(result.triples)} triples"
                )
                
            except Exception as e:
                self.logger.error(f"記事処理エラー [{article.get('id')}]: {e}")
                continue

        self.stats["total_articles"] = total
        return results

    def _update_stats(self, result: ExtractionResult):
        """統計情報を更新"""
        if result.triples:
            self.stats["articles_with_triples"] += 1

        self.stats["total_triples"] += len(result.triples)

        # 述語を収集
        for triple in result.triples:
            self.stats["unique_predicates"].add(triple.predicate)
            
            # エンティティタイプ別カウント
            for entity_type in [triple.subject_type, triple.object_type]:
                if entity_type in self.stats["entity_types"]:
                    self.stats["entity_types"][entity_type] += 1

    def normalize_all_predicates(self, results: List[ExtractionResult]):
        """
        全ての述語をバッチで正規化

        Args:
            results: 抽出結果のリスト
        """
        if not self.normalize_predicates:
            return

        # 全述語を収集
        all_predicates = []
        for result in results:
            for triple in result.triples:
                all_predicates.append(triple.predicate)

        if not all_predicates:
            return

        self.logger.info(f"述語の正規化を開始: {len(set(all_predicates))}種類")

        # バッチ正規化
        batch_normalizer = PredicateBatchNormalizer(normalizer=self.predicate_normalizer)
        mapping = batch_normalizer.normalize_batch(all_predicates)

        self.logger.info(f"述語の正規化完了: {len(mapping)}件のマッピング")

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
        rdf_path = output_dir / f"knowledge_graph_v2_{timestamp}.ttl"
        self.rdf_generator.save(str(rdf_path), format="turtle")
        self.logger.info(f"RDFを保存: {rdf_path}")

        # 最新版としてもコピー
        latest_path = output_dir / "knowledge_graph_v2.ttl"
        self.rdf_generator.save(str(latest_path), format="turtle")

        # 統計情報を保存
        stats_to_save = {
            **self.stats,
            "unique_predicates": list(self.stats["unique_predicates"]),
            "rdf_stats": self.rdf_generator.get_statistics()
        }
        stats_path = output_dir / f"stats_v2_{timestamp}.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats_to_save, f, ensure_ascii=False, indent=2)
        self.logger.info(f"統計情報を保存: {stats_path}")

        return {
            "rdf": str(rdf_path),
            "rdf_latest": str(latest_path),
            "stats": str(stats_path),
        }

    def run(
        self,
        input_path: str,
        output_dir: str,
        verbose: bool = False,
        max_articles: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        パイプライン全体を実行

        Args:
            input_path: articles.jsonのパス
            output_dir: 出力ディレクトリ
            verbose: 詳細出力
            max_articles: 処理する最大記事数（デバッグ用）

        Returns:
            実行結果の辞書
        """
        # ロギング設定
        if verbose:
            logging.basicConfig(
                level=logging.INFO,
                format='[%(asctime)s] %(levelname)s: %(message)s'
            )

        self.logger.info("トリプル抽出パイプライン開始")
        start_time = datetime.now()

        # 記事読み込み
        articles = self.load_articles(input_path)

        # 処理実行
        def progress_callback(current, total, result):
            if verbose and current % 10 == 0:
                self.logger.info(f"処理中: {current}/{total}")

        results = self.process_all(articles, progress_callback, max_articles)

        # 述語の正規化（バッチ）
        self.normalize_all_predicates(results)

        # 出力保存
        output_files = self.save_output(output_dir)

        # 実行時間
        elapsed = (datetime.now() - start_time).total_seconds()

        self.logger.info(f"パイプライン完了 ({elapsed:.2f}秒)")
        self.logger.info(f"  記事数: {self.stats['total_articles']}")
        self.logger.info(f"  トリプル抽出記事: {self.stats['articles_with_triples']}")
        self.logger.info(f"  総トリプル数: {self.stats['total_triples']}")
        self.logger.info(f"  ユニーク述語数: {len(self.stats['unique_predicates'])}")

        return {
            "success": True,
            "elapsed_seconds": elapsed,
            "stats": {
                **self.stats,
                "unique_predicates": list(self.stats["unique_predicates"])
            },
            "output_files": output_files,
        }
